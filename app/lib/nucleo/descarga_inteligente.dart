import 'dart:async';

import 'ajustes.dart';
import 'coleccion.dart';
import 'descargas.dart';
import 'modelos.dart';
import 'red.dart';


/// Clave en `Coleccion.estado` con lo que ha bajado (o descartado) ella sola.
const _claveEstado = 'descarga_inteligente';

/// Cuantas canciones tiene en la cola a la vez: va poco a poco, sin
/// llenarle la lista de descargas a nadie.
const _enCurso = 2;

/// Kbit/s aproximados de cada formato, para calcular cuanto ocupara algo
/// antes de bajarlo.
int kbpsDeFormato(String formato, String bitrateMp3) => switch (formato) {
      'mp3' => int.tryParse(bitrateMp3) ?? 320,
      'm4a' => 160,
      'opus' => 160,
      'flac' => 1000,
      'wav' => 1411,
      _ => 256,
    };

/// Bytes que ocupara una cancion (si no se sabe la duracion, 4 minutos).
int tamanoEstimado(Json pista, int kbps) {
  final s = (pista['duracion'] as num?)?.toInt() ?? 0;
  final segundos = s > 0 ? s : 240;
  return segundos * kbps * 1000 ~/ 8;
}

/// GB del ajuste a bytes (lo de abajo de 0 no deja bajar nada).
int bytesDeGb(num gb) => gb <= 0 ? 0 : (gb * 1024 * 1024 * 1024).round();

/// Si puede bajar ahora mismo: ajuste encendido, con wifi (nunca con datos) y
/// con internet.
bool puedeDescargarSola({required bool activa, required bool conDatos, required bool sinRed}) =>
    activa && !conDatos && !sinRed;

/// Que bajar ahora, en orden: alterna tus me gusta (los mas recientes primero)
/// con lo que mas escuchas, sin repetir, sin lo que ya esta o se descarto, y
/// solo mientras quepa en el limite contando lo que ya ocupa.
List<Json> planDescargaInteligente({
  required List<Json> meGusta,
  required List<Json> masEscuchadas,
  required Set<String> excluir,
  required int bytesUsados,
  required int limiteBytes,
  required int kbps,
  int maximo = _enCurso,
}) {
  final salida = <Json>[];
  if (maximo <= 0) return salida;
  final vistos = <String>{...excluir};
  var usado = bytesUsados;
  final largo = meGusta.length > masEscuchadas.length ? meGusta.length : masEscuchadas.length;
  for (var i = 0; i < largo && salida.length < maximo; i++) {
    for (final lista in [meGusta, masEscuchadas]) {
      if (i >= lista.length || salida.length >= maximo) continue;
      final p = lista[i];
      final vid = '${p['video_id'] ?? ''}';
      if (vid.isEmpty || !vistos.add(vid)) continue;
      final peso = tamanoEstimado(p, kbps);
      // lo que no cabe se salta: quiza una mas corta si
      if (usado + peso > limiteBytes) continue;
      usado += peso;
      salida.add(p);
    }
  }
  return salida;
}

/// Descarga inteligente: con wifi, y si el ajuste esta activo, baja sola en
/// segundo plano tus me gusta y lo que mas escuchas, hasta el limite de GB
/// que elijas. Si pasas a datos moviles, pone en pausa lo suyo y sigue al
/// volver el wifi.
class DescargaInteligente {
  DescargaInteligente(this.coleccion, this.descargas, this.ajustes);

  final Coleccion coleccion;
  final GestorDescargas descargas;
  final Ajustes ajustes;

  /// Lo que esta bajando ahora (video_id -> descarga).
  final Map<String, Descarga> _mias = {};

  /// video_id que ya bajo ella sola (lo que cuenta para el limite).
  final Set<String> _bajadas = {};

  /// Lo que fallo o cancelaste: no se vuelve a intentar.
  final Set<String> _descartadas = {};

  bool _iniciada = false;
  bool _cargado = false;
  bool _revisando = false;
  bool _pausadaPorRed = false;
  Timer? _reloj;
  Timer? _espera;
  StreamSubscription<Descarga>? _terminadas;

  bool get _activa => ajustes.sino('descarga_inteligente');

  bool get puedeAhora =>
      puedeDescargarSola(activa: _activa, conDatos: Red.conDatos, sinRed: Red.sinRed);

  /// Bytes que ocupa lo que bajo ella sola (lo que sigue en el telefono).
  int get bytesUsados {
    var total = 0;
    for (final vid in _bajadas) {
      final d = coleccion.copiaLocal(vid);
      if (d != null) total += (d['tamano'] as num?)?.toInt() ?? 0;
    }
    return total;
  }

  void iniciar() {
    if (_iniciada) return;
    _iniciada = true;
    Red.cambios.addListener(_alCambiar);
    ajustes.addListener(_alCambiar);
    descargas.addListener(_alCambiarDescargas);
    _terminadas = descargas.alTerminar.listen(_alTerminar);
    // espera a que la app arranque del todo antes de ponerse a bajar
    _espera = Timer(const Duration(seconds: 20), _revisar);
    _reloj = Timer.periodic(const Duration(minutes: 20), (_) => _revisar());
  }

  void detener() {
    if (!_iniciada) return;
    _iniciada = false;
    Red.cambios.removeListener(_alCambiar);
    ajustes.removeListener(_alCambiar);
    descargas.removeListener(_alCambiarDescargas);
    _terminadas?.cancel();
    _reloj?.cancel();
    _espera?.cancel();
  }

  Future<void> _cargar() async {
    if (_cargado) return;
    _cargado = true;
    try {
      final d = await coleccion.estado(_claveEstado);
      if (d is Map) {
        _bajadas.addAll([for (final v in (d['bajadas'] as List? ?? [])) '$v']);
        _descartadas.addAll([for (final v in (d['descartadas'] as List? ?? [])) '$v']);
      }
    } catch (_) {}
  }

  Future<void> _guardar() => coleccion.guardarEstado(_claveEstado, {
        'bajadas': _bajadas.toList(),
        'descartadas': _descartadas.toList(),
      });

  void _alCambiar() {
    if (!_iniciada) return;
    if (!_activa) {
      // la apagaste: se quita lo suyo que no habia terminado
      for (final d in _mias.values.toList()) {
        descargas.quitar(d.id);
      }
      _mias.clear();
      _pausadaPorRed = false;
      return;
    }
    if (!puedeAhora) {
      // paso a datos (o se fue internet): en pausa lo suyo
      if (!_pausadaPorRed) {
        _pausadaPorRed = true;
        for (final d in _mias.values) {
          if (d.estado.activa) descargas.pausar(d.id);
        }
      }
      return;
    }
    if (_pausadaPorRed) {
      _pausadaPorRed = false;
      for (final d in _mias.values) {
        if (d.estado == EstadoDescarga.pausada) descargas.reanudar(d.id);
      }
    }
    _revisar();
  }

  void _alCambiarDescargas() {
    var cambio = false;
    for (final e in _mias.entries.toList()) {
      final d = e.value;
      final enCola = descargas.lista.any((x) => identical(x, d));
      if (d.estado == EstadoDescarga.error || d.estado == EstadoDescarga.cancelada || !enCola) {
        if (d.estado != EstadoDescarga.completada) _descartadas.add(e.key);
        _mias.remove(e.key);
        cambio = true;
      }
    }
    if (cambio) {
      _guardar();
      _revisar();
    }
  }

  void _alTerminar(Descarga d) {
    final vid = _mias.entries.where((e) => identical(e.value, d)).map((e) => e.key).firstOrNull;
    if (vid == null) return;
    _mias.remove(vid);
    _bajadas.add(vid);
    _guardar().whenComplete(_revisar);
  }

  /// Lo que mas suena (al menos dos veces), de mas a menos.
  Future<List<Json>> _masEscuchadas() async {
    final filas = await coleccion.db.rawQuery(
        'SELECT clave, COUNT(*) n FROM reproducciones GROUP BY clave HAVING n >= 2 '
        'ORDER BY n DESC, MAX(fecha) DESC LIMIT 150');
    return coleccion.pistas([for (final f in filas) '${f['clave']}']);
  }

  Future<void> _revisar() async {
    if (!_iniciada || _revisando || !puedeAhora) return;
    final hueco = _enCurso - _mias.length;
    if (hueco <= 0) return;
    _revisando = true;
    try {
      await _cargar();
      final kbps = kbpsDeFormato(ajustes.formatoAudio, ajustes.texto('bitrate_mp3'));
      // lo que ya esta en el telefono o en la cola (tambien lo que pediste tu)
      final excluir = <String>{..._descartadas, ..._mias.keys};
      for (final d in descargas.lista) {
        final v = '${d.meta?['video_id'] ?? ''}';
        if (v.isNotEmpty && !d.terminada) excluir.add(v);
      }
      bool yaEsta(Json p) => coleccion.estaDescargada(p);
      final meGusta = (await coleccion.listaMeGusta()).where((p) => !yaEsta(p)).toList();
      final top = (await _masEscuchadas()).where((p) => !yaEsta(p)).toList();
      // lo que esta bajando cuenta como ya ocupado
      var ocupado = bytesUsados;
      for (final d in _mias.values) {
        ocupado += tamanoEstimado(d.meta ?? const {}, kbps);
      }
      final plan = planDescargaInteligente(
        meGusta: meGusta,
        masEscuchadas: top,
        excluir: excluir,
        bytesUsados: ocupado,
        limiteBytes: bytesDeGb(ajustes.entero('descarga_inteligente_gb')),
        kbps: kbps,
        maximo: hueco,
      );
      if (!puedeAhora) return;
      for (final p in plan) {
        final vid = '${p['video_id']}';
        _mias[vid] = descargas.encolar(
          url: p['es_video'] == true
              ? 'https://www.youtube.com/watch?v=$vid'
              : 'https://music.youtube.com/watch?v=$vid',
          tipo: TipoMedio.audio,
          calidad: ajustes.texto('calidad_descarga'),
          titulo: '${p['titulo'] ?? ''}',
          autor: '${p['artista'] ?? ''}',
          miniatura: '${p['miniatura'] ?? ''}',
          meta: p,
          bitrateMp3: ajustes.texto('bitrate_mp3'),
        );
      }
    } catch (_) {
      // se reintenta en la siguiente vuelta
    } finally {
      _revisando = false;
    }
  }
}
