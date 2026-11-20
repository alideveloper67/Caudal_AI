import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter/widgets.dart' show AppLifecycleListener;
import 'package:media_kit/media_kit.dart' show Media, Player, PlaylistMode;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../reproduccion/reproductor.dart';
import 'coleccion.dart';
import 'despertador.dart';
import 'despertador_nativo.dart';
import 'mixes.dart';
import 'red.dart';
import 'streams.dart';

/// Lo que el despertador necesita de Caudal (la biblioteca y el reproductor). Las pruebas pasan uno
/// de mentira; la app usa [PuertoCaudal].
abstract class PuertoDespertador {
  /// Las pistas de lo elegido (la canción, la lista, el mix de hoy o tus «me gusta»).
  Future<List<Json>> candidatas(FuenteAlarma f);

  /// Pistas descargadas para cuando no hay internet (primero las de «me gusta»).
  Future<List<Json>> respaldo();

  bool descargada(Json pista);

  /// El archivo en el teléfono de una pista descargada, o null.
  String? archivoDe(Json pista);

  bool get hayRed;

  /// Suena la lista en el reproductor de Caudal.
  Future<void> sonar(List<Json> pistas, {required String titulo});
  Future<void> fijarVolumen(double v);
  double get volumen;
  Future<void> detener();

  /// Baja el audio de un video a [destino] (sin extensión); devuelve la ruta final o null.
  Future<String?> bajarAudio(String videoId, String destino);

  /// Carpeta donde se dejan listas las canciones de las alarmas.
  Future<String?> carpeta();
}

class PuertoCaudal implements PuertoDespertador {
  PuertoCaudal(this.coleccion, this.reproductor, this.streams);

  final Coleccion coleccion;
  final Reproductor reproductor;
  final Streams streams;

  @override
  Future<List<Json>> candidatas(FuenteAlarma f) async {
    try {
      switch (f.tipo) {
        case TipoFuente.cancion:
          final pista = f.pista;
          if (pista == null) return [];
          final guardada = (await coleccion.pistas(['${pista['clave'] ?? f.id}'])).firstOrNull;
          return [guardada ?? pista];
        case TipoFuente.lista:
          final id = int.tryParse(f.id);
          return id == null ? [] : await coleccion.pistasDeLista(id);
        case TipoFuente.mix:
          // sin red no se arma ninguno nuevo: vale el de hoy si ya estaba guardado
          final mixes = await Mixes.delDia(coleccion).timeout(const Duration(seconds: 25), onTimeout: () => []);
          final mix = mixes.where((m) => '${m['id']}' == f.id).firstOrNull ?? mixes.firstOrNull;
          return [for (final x in (mix?['pistas'] as List? ?? const [])) if (x is Map) Map<String, dynamic>.from(x)];
        case TipoFuente.meGusta:
          return await coleccion.meGustaRecientes(400);
        case TipoFuente.tono:
          return [];
      }
    } catch (_) {
      return [];
    }
  }

  @override
  Future<List<Json>> respaldo() async {
    try {
      final locales = await coleccion.descargadas(soloAudio: true);
      final gustan = locales.where((x) => coleccion.meGusta('${x['clave']}')).toList();
      return gustan.isNotEmpty ? gustan : locales;
    } catch (_) {
      return [];
    }
  }

  @override
  bool descargada(Json pista) => coleccion.estaDescargada(pista);

  @override
  String? archivoDe(Json pista) {
    final a = '${pista['archivo'] ?? ''}';
    if (a.isNotEmpty && !a.startsWith('http') && coleccion.estaDescargada(pista)) return a;
    final c = coleccion.copiaLocal(pista['video_id'] as String?);
    final r = '${c?['archivo'] ?? ''}';
    return r.isEmpty || r.startsWith('http') ? null : r;
  }

  @override
  bool get hayRed => !Red.sinRed;

  @override
  Future<void> sonar(List<Json> pistas, {required String titulo}) => reproductor.reproducirLista(pistas,
      contexto: {'tipo': 'seleccion', 'id': titulo, 'titulo': titulo}, modo: 'audio');

  @override
  Future<void> fijarVolumen(double v) => reproductor.fijarVolumen(v);

  @override
  double get volumen => reproductor.volumen;

  @override
  Future<void> detener() => reproductor.detener();

  @override
  Future<String?> bajarAudio(String videoId, String destino) async {
    final f = await streams.resolver(videoId, video: false, calidad: Red.conDatos ? 'ahorro' : 'normal');
    final codec = f.audioCodec.toLowerCase();
    final ext = codec.contains('opus') ? 'webm' : (codec.contains('mp4a') || codec.contains('aac') ? 'm4a' : 'audio');
    final ruta = '$destino.$ext';
    final parcial = '$ruta.parte';
    await Dio().download(f.url, parcial,
        options: Options(receiveTimeout: const Duration(minutes: 3)));
    await File(parcial).rename(ruta);
    return ruta;
  }

  @override
  Future<String?> carpeta() async {
    if (kIsWeb) return null;
    final base = await getApplicationSupportDirectory();
    final d = Directory(p.join(base.path, 'despertador'));
    await d.create(recursive: true);
    return d.path;
  }
}

/// Lo que suena ahora en la app (iPhone y lo que no es Android: allí no hay alarma del sistema).
class SonandoAhora {
  const SonandoAhora(this.alarma, this.titulo, {this.prueba = false, this.tono = false});
  final Alarma alarma;
  final String titulo;
  final bool prueba;
  final bool tono;
}

/// El despertador: guarda las alarmas, deja lista su música en el teléfono y se las pasa a Android
/// (que las hace sonar con la app cerrada). En iPhone y otros, suenan con la app abierta.
class ControlDespertador extends ChangeNotifier {
  ControlDespertador({CanalDespertador canal = const CanalDespertador(), DateTime Function()? reloj})
      : _canal = canal,
        _reloj = reloj ?? DateTime.now;

  static final ControlDespertador i = ControlDespertador();

  final CanalDespertador _canal;
  final DateTime Function() _reloj;
  PuertoDespertador? _puerto;

  List<Alarma> alarmas = [];
  bool cargadas = false;

  /// Lo que suena con la app abierta (no Android). La pantalla de «Posponer / Apagar» lo vigila.
  final ValueNotifier<SonandoAhora?> sonando = ValueNotifier(null);

  /// Mientras se preparan las canciones (para enseñar «Preparando…»).
  final ValueNotifier<bool> preparando = ValueNotifier(false);

  Timer? _vigia;
  Timer? _subida;
  DateTime _ultima = DateTime.now();
  AppLifecycleListener? _vida;
  final _azar = Random();

  bool get _nativo => _canal.disponible;

  // ------------------------------------------------------------ arranque

  Future<void> iniciar(PuertoDespertador puerto) async {
    _puerto = puerto;
    await cargar();
    _ultima = _reloj();
    _vigia?.cancel();
    if (!_nativo) {
      _vigia = Timer.periodic(const Duration(seconds: 15), (_) => mirar());
    }
    _vida?.dispose();
    try {
      _vida = AppLifecycleListener(onResume: () {
        unawaited(_alVolver());
      });
    } catch (_) {} // en pruebas sin motor de Flutter no hay ciclo de vida
    // ya se cargó arriba: al arrancar solo falta ver si se pidió «seguir escuchando»
    unawaited(_mirarSeguir());
    unawaited(sincronizar());
  }

  /// Al salir de la cuenta: el reproductor ya no es el mismo (las alarmas de Android siguen).
  void soltar() {
    _vigia?.cancel();
    _vigia = null;
    _vida?.dispose();
    _vida = null;
    _puerto = null;
  }

  /// Sube con cada cambio hecho aquí: una lectura que empezó antes no pisa lo recién cambiado.
  int _version = 0;

  Future<void> cargar() async {
    final v = _version;
    final leidas = await AlmacenAlarmas.leer();
    if (v != _version) return;
    alarmas = leidas;
    await _mezclarConNativo();
    cargadas = true;
    notifyListeners();
  }

  /// Android apaga las de «una vez» y anota las pospuestas aunque la app esté cerrada: se adopta.
  Future<void> _mezclarConNativo() async {
    final v = _version;
    final d = await _canal.leer();
    final lista = d?['alarmas'];
    if (lista is! List || v != _version) return;
    final nativas = {for (final a in lista) if (a is Map) '${a['id']}': a};
    var cambio = false;
    alarmas = [
      for (final a in alarmas)
        if (nativas[a.id] case final n?)
          () {
            final activa = n['activa'] != false;
            final pos = n['pospuesta_hasta'] is num ? (n['pospuesta_hasta'] as num).round() : 0;
            if (activa == a.activa && pos == a.pospuestaHasta) return a;
            cambio = true;
            return a.copia(activa: activa, pospuestaHasta: pos);
          }()
        else
          a,
    ];
    if (cambio) await AlmacenAlarmas.guardar(alarmas);
  }

  Future<void> _alVolver() async {
    if (_nativo) await cargar();
    await _mirarSeguir();
  }

  Future<void> _mirarSeguir() async {
    if (_nativo) {
      final id = await _canal.consumirSeguir();
      if (id != null) await seguirEscuchando(id);
    } else {
      mirar();
    }
  }

  // ------------------------------------------------------------ cambios

  Alarma? alarma(String id) => alarmas.where((a) => a.id == id).firstOrNull;

  Future<void> poner(Alarma a) async {
    final i = alarmas.indexWhere((x) => x.id == a.id);
    alarmas = [...alarmas];
    if (i < 0) {
      alarmas.add(a);
    } else {
      alarmas[i] = a;
    }
    await _guardarYProgramar();
  }

  Future<void> quitar(String id) async {
    alarmas = alarmas.where((a) => a.id != id).toList();
    await _guardarYProgramar();
  }

  Future<void> activar(String id, bool si) async {
    final a = alarma(id);
    if (a == null) return;
    await poner(a.copia(activa: si, pospuestaHasta: 0));
  }

  Future<void> _guardarYProgramar() async {
    _version++;
    await AlmacenAlarmas.guardar(alarmas);
    notifyListeners();
    await sincronizar();
  }

  /// (alarma, cuándo) de la próxima que suena.
  (Alarma, DateTime)? proxima() {
    final ahora = _reloj();
    (Alarma, DateTime)? mejor;
    for (final a in alarmas) {
      final p = proximaVez(a, ahora);
      if (p != null && (mejor == null || p.isBefore(mejor.$2))) mejor = (a, p);
    }
    return mejor;
  }

  // ------------------------------------------------------------ preparar la música (Android)

  int _gen = 0;

  /// Deja en el teléfono la canción de cada alarma (si no estaba descargada y hay internet) y le pasa
  /// todo a Android. Primero se programa con lo que ya hay, para que nunca quede una alarma sin sonar
  /// por estar bajando su canción.
  Future<void> sincronizar() async {
    if (!_nativo) return;
    final gen = ++_gen;
    await _canal.programar(await datosNativos(preparar: false));
    if (gen != _gen) return;
    preparando.value = true;
    try {
      final datos = await datosNativos(preparar: true);
      if (gen != _gen) return;
      await _canal.programar(datos);
    } finally {
      if (gen == _gen) preparando.value = false;
    }
  }

  /// Lo que se le pasa a Android: cada alarma con los `archivos` que puede tocar (el primero que
  /// exista; en «me gusta», uno al azar) y un `respaldo` de música descargada.
  @visibleForTesting
  Future<Map<String, dynamic>> datosNativos({required bool preparar}) async {
    final puerto = _puerto;
    final carpeta = puerto == null ? null : await puerto.carpeta();
    final usados = <String>{};
    final salida = <Map<String, dynamic>>[];
    for (final a in alarmas) {
      final j = a.toJson();
      final archivos = <Map<String, String>>[];
      if (puerto != null && a.activa && a.fuente.tipo != TipoFuente.tono) {
        final cands = await puerto.candidatas(a.fuente);
        if (a.fuente.tipo == TipoFuente.meGusta) {
          for (final x in cands.where(puerto.descargada).take(40)) {
            final r = puerto.archivoDe(x);
            if (r != null) archivos.add({'archivo': r, 'titulo': _titulo(x)});
          }
        }
        if (archivos.isEmpty) {
          final elegida = pistaParaPreparar(a, cands, puerto.descargada, azar: _azar);
          if (elegida != null) {
            final local = puerto.archivoDe(elegida);
            if (local != null) {
              archivos.add({'archivo': local, 'titulo': _titulo(elegida)});
            } else if (carpeta != null) {
              final vid = '${elegida['video_id'] ?? ''}';
              final previo = _preparado(carpeta, vid);
              if (previo != null) {
                archivos.add({'archivo': previo, 'titulo': _titulo(elegida)});
              } else if (preparar && vid.isNotEmpty && puerto.hayRed) {
                try {
                  final r = await puerto.bajarAudio(vid, p.join(carpeta, 'cancion_$vid'));
                  if (r != null) archivos.add({'archivo': r, 'titulo': _titulo(elegida)});
                } catch (e) {
                  debugPrint('Despertador: no se pudo dejar lista la canción ($e)');
                }
              }
            }
          }
        }
      }
      usados.addAll(archivos.map((x) => x['archivo']!));
      j['archivos'] = archivos;
      salida.add(j);
    }
    final respaldo = <Map<String, String>>[];
    if (puerto != null) {
      for (final x in (await puerto.respaldo()).take(40)) {
        final r = puerto.archivoDe(x);
        if (r != null) respaldo.add({'archivo': r, 'titulo': _titulo(x)});
      }
    }
    if (preparar && carpeta != null) _limpiar(carpeta, usados);
    return {'version': 1, 'alarmas': salida, 'respaldo': respaldo};
  }

  static String _titulo(Json x) {
    final t = '${x['titulo'] ?? ''}'.trim();
    final a = '${x['artista'] ?? ''}'.trim();
    return [t, a].where((s) => s.isNotEmpty).join(' · ');
  }

  String? _preparado(String carpeta, String vid) {
    if (vid.isEmpty || kIsWeb) return null;
    for (final ext in const ['m4a', 'webm', 'audio']) {
      final f = File(p.join(carpeta, 'cancion_$vid.$ext'));
      if (f.existsSync() && f.lengthSync() > 10000) return f.path;
    }
    return null;
  }

  /// Borra las canciones preparadas que ya no usa ninguna alarma (y los restos a medio bajar).
  void _limpiar(String carpeta, Set<String> usados) {
    try {
      for (final f in Directory(carpeta).listSync().whereType<File>()) {
        if (!usados.contains(f.path) && p.basename(f.path).startsWith('cancion_')) f.deleteSync();
      }
    } catch (_) {}
  }

  // ------------------------------------------------------------ permisos y prueba

  Future<PermisosDespertador> permisos() => _canal.permisos();
  Future<void> abrirAjuste(String cual) => _canal.abrirAjuste(cual);

  /// Suena ya, como sonará. En Android, por el mismo camino que con la app cerrada.
  Future<void> probar(Alarma a) async {
    if (_nativo) {
      // tal como está en el editor (aunque aún no se haya guardado), con la música que ya haya
      final datos = await datosNativos(preparar: false);
      final misma = (datos['alarmas'] as List).cast<Map<String, dynamic>>().where((x) => x['id'] == a.id).firstOrNull;
      await _canal.programar({
        ...datos,
        'prueba': {...a.toJson(), 'archivos': misma?['archivos'] ?? const []},
      });
      await _canal.probar(a.id);
      return;
    }
    await sonarEnApp(a, prueba: true);
  }

  // ------------------------------------------------------------ «Seguir escuchando» (Android)

  /// Tras apagar la alarma en Android con «Apagar y seguir escuchando»: la música de la alarma sigue
  /// en Caudal, al volumen de siempre.
  Future<void> seguirEscuchando(String id) async {
    final a = alarma(id);
    final puerto = _puerto;
    if (a == null || puerto == null) return;
    final plan = planear(a,
        hayRed: puerto.hayRed,
        candidatas: await puerto.candidatas(a.fuente),
        descargada: puerto.descargada,
        respaldo: await puerto.respaldo(),
        azar: _azar);
    if (plan.esTono) return;
    await puerto.sonar(plan.pistas, titulo: a.etiqueta.isEmpty ? 'Despertador' : a.etiqueta);
  }

  // ------------------------------------------------------------ sonar con la app abierta (no Android)

  /// Mira si toca alguna (cada 15 s y al volver a la app).
  void mirar() {
    if (_nativo || sonando.value != null) {
      _ultima = _reloj();
      return;
    }
    final ahora = _reloj();
    final salen = tocan(alarmas, _ultima, ahora);
    _ultima = ahora;
    if (salen.isNotEmpty) unawaited(sonarEnApp(salen.first));
  }

  double? _volumenAntes;
  DateTime? _empezo;
  _TonoSuave? _tono;

  @visibleForTesting
  Future<void> sonarEnApp(Alarma a, {bool prueba = false}) async {
    final puerto = _puerto;
    if (sonando.value != null) await _pararSonido();
    final plan = puerto == null
        ? const PlanSonido([], MotivoPlan.sinMusica)
        : planear(a,
            hayRed: puerto.hayRed,
            candidatas: await puerto.candidatas(a.fuente),
            descargada: puerto.descargada,
            respaldo: await puerto.respaldo(),
            azar: _azar);
    _empezo = _reloj();
    final inicial = a.volumen * factorVolumen(0, a.subida);
    var titulo = 'Sonido suave de Caudal';
    if (plan.esTono || puerto == null) {
      _tono = _TonoSuave();
      await _tono!.empezar(inicial);
    } else {
      _volumenAntes ??= puerto.volumen;
      await puerto.fijarVolumen(max(1, inicial));
      await puerto.sonar(plan.pistas, titulo: a.etiqueta.isEmpty ? 'Despertador' : a.etiqueta);
      titulo = _titulo(plan.pistas.first);
    }
    sonando.value = SonandoAhora(a, titulo, prueba: prueba, tono: plan.esTono || puerto == null);
    _subida?.cancel();
    _subida = Timer.periodic(const Duration(milliseconds: 250), (_) => pasoVolumen());
  }

  @visibleForTesting
  Future<void> pasoVolumen() async {
    final s = sonando.value;
    final empezo = _empezo;
    if (s == null || empezo == null) return;
    final t = _reloj().difference(empezo);
    if (t >= maxSonando) {
      await apagar();
      return;
    }
    final v = max(1.0, s.alarma.volumen * factorVolumen(t.inMilliseconds / 1000, s.alarma.subida));
    if (_tono != null) {
      await _tono!.volumen(v);
    } else if (_puerto != null && (_puerto!.volumen - v).abs() >= 0.5) {
      await _puerto!.fijarVolumen(v);
    }
  }

  Future<void> _pararSonido({bool seguir = false}) async {
    _subida?.cancel();
    _subida = null;
    final tono = _tono;
    _tono = null;
    await tono?.parar();
    final puerto = _puerto;
    if (puerto != null && tono == null && !seguir) await puerto.detener();
    if (puerto != null && _volumenAntes != null) await puerto.fijarVolumen(_volumenAntes!);
    _volumenAntes = null;
  }

  Future<void> posponer() async {
    final s = sonando.value;
    if (s == null) return;
    await _pararSonido();
    sonando.value = null;
    if (!s.prueba) await poner(posponerAlarma(s.alarma, _reloj()));
  }

  Future<void> apagar({bool seguir = false}) async {
    final s = sonando.value;
    if (s == null) return;
    await _pararSonido(seguir: seguir);
    sonando.value = null;
    if (!s.prueba) await poner(trasSonar(alarma(s.alarma.id) ?? s.alarma));
  }
}

/// El sonido suave de Caudal en un reproductor aparte (no entra en tu historial ni en la cola).
class _TonoSuave {
  dynamic _player;

  Future<void> empezar(double volumen) async {
    try {
      final dir = await getTemporaryDirectory();
      final f = File(p.join(dir.path, 'caudal_despertador_amanecer.wav'));
      if (!f.existsSync()) {
        final b = await rootBundle.load('assets/despertador/amanecer.wav');
        await f.writeAsBytes(b.buffer.asUint8List(), flush: true);
      }
      _player = await crearReproductorTono(f.path, volumen);
    } catch (e) {
      debugPrint('Despertador: el sonido suave no pudo sonar ($e)');
    }
  }

  Future<void> volumen(double v) async {
    try {
      await _player?.setVolume(v);
    } catch (_) {}
  }

  Future<void> parar() async {
    try {
      await _player?.dispose();
    } catch (_) {}
    _player = null;
  }
}

/// Crea el reproductor del tono (media_kit, en bucle). Se cambia en las pruebas.
@visibleForTesting
Future<dynamic> Function(String ruta, double volumen) crearReproductorTono = (ruta, volumen) async {
  final pl = Player();
  await pl.setPlaylistMode(PlaylistMode.single);
  await pl.setVolume(volumen);
  await pl.open(Media(ruta));
  return pl;
};
