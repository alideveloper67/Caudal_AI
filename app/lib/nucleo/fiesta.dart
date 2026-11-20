import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'catalogo.dart';
import 'coleccion.dart' show Json;
import 'juntos.dart' show CanalRealtime;
import 'nube.dart';

export 'coleccion.dart' show Json;

/// «Fiesta por QR»: el anfitrión abre una fiesta, enseña un QR y los invitados piden canciones
/// y votan desde la página web /fiesta/<CODIGO> (web/fiesta.html), sin instalar nada.
///
/// Envuelve las funciones de supabase/fiesta.sql. El anfitrión se identifica con la «clave»
/// secreta que devuelve fiesta_crear; la cola vive en la base y cada cambio avisa por Realtime
/// (canal público `fiesta-<CODIGO>`, evento «cambio»). Además se pregunta cada 20 s.

typedef LlamadaFiesta = Future<dynamic> Function(String nombre, Map<String, dynamic> parametros);

const sitioCaudal = 'https://caudal-musica.netlify.app';
const alfabetoFiesta = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

/// El enlace que va en el QR.
String enlaceFiesta(String codigo) => '$sitioCaudal/fiesta/$codigo';

/// El código con un espacio en medio para leerlo de lejos: «ABC 234».
String codigoVisible(String codigo) => codigo.length == 6 ? '${codigo.substring(0, 3)} ${codigo.substring(3)}' : codigo;

class ErrorFiesta implements Exception {
  const ErrorFiesta(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

/// El texto para la persona cuando una función de la base falla.
String mensajeErrorFiesta(int estado, String cuerpo) {
  Object? d;
  try {
    d = jsonDecode(cuerpo);
  } catch (_) {}
  final m = d is Map ? '${d['message'] ?? ''}' : '';
  final codigo = d is Map ? '${d['code'] ?? ''}' : '';
  if (codigo == 'P0001' && m.isNotEmpty) return m; // las frases de fiesta.sql, tal cual
  if (codigo == 'PGRST202' || m.toLowerCase().contains('could not find the function')) {
    return 'La fiesta todavía no está activa en el servidor de Caudal.';
  }
  if (estado == 429) return 'Demasiados intentos seguidos. Espera un momento.';
  if (estado >= 500 || estado == 0) return 'No pudimos hablar con Caudal. Revisa tu internet y vuelve a probar.';
  return 'Algo falló. Vuelve a intentarlo.';
}

/// La llamada de verdad: POST /rest/v1/rpc/<nombre> con la clave pública (sin sesión).
Future<dynamic> llamarFiesta(String nombre, Map<String, dynamic> parametros, {http.Client? cliente}) async {
  final c = cliente ?? http.Client();
  try {
    final r = await c
        .post(Uri.parse('${Nube.url}/rest/v1/rpc/$nombre'),
            headers: {'apikey': Nube.clavePublica, 'Content-Type': 'application/json'}, body: jsonEncode(parametros))
        .timeout(const Duration(seconds: 15));
    final cuerpo = utf8.decode(r.bodyBytes);
    if (r.statusCode >= 400) throw ErrorFiesta(mensajeErrorFiesta(r.statusCode, cuerpo));
    return cuerpo.isEmpty ? null : jsonDecode(cuerpo);
  } on ErrorFiesta {
    rethrow;
  } catch (_) {
    throw ErrorFiesta(mensajeErrorFiesta(0, ''));
  } finally {
    if (cliente == null) c.close();
  }
}

// ============================================================== modelos

int _n(Object? v) => v is num ? v.toInt() : int.tryParse('${v ?? ''}') ?? 0;
String _t(Object? v) => v == null ? '' : '$v';
String _https(Object? v) {
  final s = _t(v);
  return RegExp(r'''^https://[^\s"'<>]+$''').hasMatch(s) && s.length <= 500 ? s : '';
}

class CancionFiesta {
  const CancionFiesta({required this.id, required this.videoId, this.titulo = '', this.artista = '',
      this.miniatura = '', this.duracion = 0, this.nombre = '', this.votos = 0, this.estado = 'cola',
      this.deAnfitrion = false});

  final int id;
  final String videoId;
  final String titulo;
  final String artista;
  final String miniatura;
  final int duracion;
  final String nombre; // quién la pidió
  final int votos;
  final String estado; // cola | sonando | sonada
  final bool deAnfitrion;

  String get quien => nombre.isNotEmpty ? nombre : (deAnfitrion ? 'el anfitrión' : 'un invitado');

  static CancionFiesta? desde(Object? d) {
    if (d is! Map) return null;
    final vid = _t(d['video_id']);
    if (!RegExp(r'^[A-Za-z0-9_-]{11}$').hasMatch(vid)) return null;
    return CancionFiesta(
      id: _n(d['id']), videoId: vid, titulo: _t(d['titulo']).isEmpty ? 'Sin título' : _t(d['titulo']),
      artista: _t(d['artista']), miniatura: _https(d['miniatura']), duracion: _n(d['duracion']),
      nombre: _t(d['nombre']), votos: _n(d['votos']), estado: _t(d['estado']).isEmpty ? 'cola' : _t(d['estado']),
      deAnfitrion: d['de_anfitrion'] == true,
    );
  }

  /// La pista para el reproductor, con `fiesta_id` para reconocerla al sonar.
  Json comoPista() {
    final p = Catalogo.nuevaPista(videoId,
        titulo: titulo, artistas: artista.isEmpty ? const [] : [{'nombre': artista, 'id': ''}],
        duracion: duracion, miniatura: miniatura);
    p['fiesta_id'] = id;
    p['fiesta_quien'] = nombre;
    return p;
  }
}

class SonandoFiesta {
  const SonandoFiesta({this.videoId = '', this.titulo = '', this.artista = '', this.miniatura = '',
      this.duracion = 0, this.posMs = 0, this.pausa = false, this.t = 0, this.fiestaId, this.nombre = ''});
  final String videoId, titulo, artista, miniatura, nombre;
  final int duracion, posMs, t;
  final bool pausa;
  final int? fiestaId;

  static SonandoFiesta? desde(Object? d) {
    if (d is! Map) return null;
    return SonandoFiesta(
      videoId: _t(d['video_id']), titulo: _t(d['titulo']), artista: _t(d['artista']),
      miniatura: _https(d['miniatura']), duracion: _n(d['duracion']), posMs: _n(d['pos_ms']),
      pausa: d['pausa'] == true, t: _n(d['t']), fiestaId: d['fiesta_id'] == null ? null : _n(d['fiesta_id']),
      nombre: _t(d['nombre']),
    );
  }
}

/// Lo que devuelve fiesta_ver.
class EstadoFiesta {
  const EstadoFiesta({required this.codigo, this.nombre = 'Fiesta', this.abierta = true, this.limite = 0,
      this.version = 0, this.invitados = 0, this.sonando, this.cola = const [], this.sonadas = const []});

  final String codigo;
  final String nombre;
  final bool abierta;
  final int limite; // 0 = sin límite
  final int version;
  final int invitados;
  final SonandoFiesta? sonando;
  final List<CancionFiesta> cola; // en el orden en que sonarán
  final List<CancionFiesta> sonadas;

  CancionFiesta? get siguiente => cola.isEmpty ? null : cola.first;

  static EstadoFiesta? desde(Object? d) {
    if (d is! Map) return null;
    List<CancionFiesta> lista(Object? v) =>
        [for (final c in (v is List ? v : const [])) ?CancionFiesta.desde(c)];
    return EstadoFiesta(
      codigo: _t(d['codigo']), nombre: _t(d['nombre']).isEmpty ? 'Fiesta' : _t(d['nombre']),
      abierta: d['abierta'] != false, limite: _n(d['limite']), version: _n(d['version']),
      invitados: _n(d['invitados']), sonando: SonandoFiesta.desde(d['sonando']),
      cola: ordenarCola(lista(d['cola'])),
      sonadas: lista(d['sonadas']).where((c) => c.estado == 'sonada').toList(),
    );
  }
}

/// Más votos primero; a igualdad, la que llegó antes (id menor). Igual que la base.
List<CancionFiesta> ordenarCola(List<CancionFiesta> cola) {
  final c = [...cola];
  c.sort((a, b) => b.votos != a.votos ? b.votos - a.votos : a.id - b.id);
  return c;
}

/// Texto del límite para el anfitrión.
String textoLimite(int limite) => limite <= 0
    ? 'Cada invitado puede pedir todas las que quiera'
    : (limite == 1 ? 'Cada invitado puede pedir 1 canción' : 'Cada invitado puede pedir $limite canciones');

// ============================================================== decidir

/// Segundos antes del final en que se pide la siguiente: así los votos cuentan hasta el último
/// momento y hay tiempo para el fundido entre canciones.
const segundosAntesDelFinal = 25;

/// ¿Hay que poner ya la siguiente canción de la fiesta en el reproductor?
/// - nada suena (o se paró) y no hay ninguna de la fiesta esperando → sí;
/// - quedan ≤25 s de la actual y no hay ya una de la fiesta esperando detrás → sí.
bool debeTomarSiguiente({required bool hayActual, required bool parado, required int? restanteMs,
    required bool hayPendiente}) {
  if (hayPendiente) return false;
  if (!hayActual || parado) return true;
  if (restanteMs == null) return false;
  return restanteMs <= segundosAntesDelFinal * 1000;
}

/// ¿Hay alguna canción de la fiesta ya puesta en la cola del reproductor?
bool hayDeFiestaEnCola(List<Json> proximas) => proximas.any((p) => p['fiesta_id'] != null);

/// Lo que se manda a fiesta_sonando.
Json? pistaParaSonando(Json? pista, {int posMs = 0, bool pausa = false}) {
  if (pista == null) return null;
  return {
    'video_id': _t(pista['video_id']),
    'titulo': _t(pista['titulo']),
    'artista': _t(pista['artista']),
    'miniatura': _https(pista['miniatura']),
    'duracion': _n(pista['duracion']),
    'pos_ms': posMs < 0 ? 0 : posMs,
    'pausa': pausa,
    if (pista['fiesta_id'] != null) 'fiesta_id': pista['fiesta_id'],
  };
}

/// Identidad de una pista para saber si cambió.
String clavePistaFiesta(Json? p) => p == null ? '' : '${p['video_id'] ?? p['clave'] ?? p['titulo'] ?? ''}';

// ============================================================== reproductor

/// Lo que la fiesta necesita del reproductor (se prueba con uno falso).
abstract class ControlFiesta implements Listenable {
  Json? get actual;
  List<Json> get proximas;
  bool get parado;
  bool get enPausa;
  int get posicionMs;
  int get duracionMs;
  void ponerDespues(Json pista);
  Future<void> ponerAhora(Json pista);
}

// ============================================================== la fiesta del anfitrión

class FiestaAnfitrion extends ChangeNotifier {
  FiestaAnfitrion._(this.codigo, this.clave, this.control, this._llamar, {this.conTiempoReal = true});

  /// La fiesta abierta en este aparato (una a la vez). Sigue aunque se cierre la pantalla.
  static final ValueNotifier<FiestaAnfitrion?> activa = ValueNotifier(null);

  final String codigo;
  final String clave;
  final ControlFiesta control;
  final LlamadaFiesta _llamar;
  final bool conTiempoReal;

  EstadoFiesta? estado;
  String? error;
  bool cerrada = false;
  bool conectado = false;

  /// Poner sola la siguiente canción de la fiesta cuando toque.
  bool automatico = true;

  CanalRealtime? _canal;
  Timer? _sondeo;
  Timer? _tic;
  bool _pidiendo = false;
  bool _otraVez = false;
  bool _tomando = false;
  String _ultimaClave = '';
  bool? _ultimaPausa;
  Timer? _avisoSonando;

  /// Crea la fiesta en la base y empieza a escuchar el reproductor.
  static Future<FiestaAnfitrion> crear({required ControlFiesta control, String nombre = '', int limite = 5,
      LlamadaFiesta? llamar, bool conTiempoReal = true}) async {
    final l = llamar ?? llamarFiesta;
    final r = await l('fiesta_crear', {'p_nombre': nombre.trim(), 'p_limite': limite});
    if (r is! Map || '${r['codigo'] ?? ''}'.length != 6 || '${r['clave'] ?? ''}'.isEmpty) {
      throw const ErrorFiesta('No se pudo crear la fiesta. Vuelve a intentarlo.');
    }
    final f = FiestaAnfitrion._('${r['codigo']}', '${r['clave']}', control, l, conTiempoReal: conTiempoReal);
    await f._empezar();
    return f;
  }

  String get enlace => enlaceFiesta(codigo);

  Future<void> _empezar() async {
    control.addListener(_alReproductor);
    await refrescar();
    _ultimaClave = '';
    _alReproductor(); // cuenta lo que ya suena
    _sondeo = Timer.periodic(const Duration(seconds: 20), (_) => refrescar());
    _tic = Timer.periodic(const Duration(seconds: 2), (_) => revisarSiguiente());
    if (conTiempoReal) {
      final canal = CanalRealtime('realtime:fiesta-$codigo',
          clavePresencia: 'anfitrion-$codigo',
          alMensaje: (evento, datos) {
            if (evento == 'cambio' && _n(datos['version']) > (estado?.version ?? 0)) refrescar();
          },
          alEstadoConexion: (si) {
            conectado = si;
            if (si) refrescar();
            notifyListeners();
          });
      _canal = canal;
      unawaited(canal.abrir().then((_) {
        conectado = true;
        notifyListeners();
      }, onError: (_) {})); // sin tiempo real sigue funcionando con el sondeo
    }
  }

  void _aplicar(Object? d) {
    final e = EstadoFiesta.desde(d);
    if (e == null) return;
    if (estado != null && e.version < estado!.version) return;
    estado = e;
    if (!e.abierta) cerrada = true;
    notifyListeners();
  }

  Future<T?> _hacer<T>(Future<T> Function() que) async {
    try {
      final r = await que();
      error = null;
      return r;
    } on ErrorFiesta catch (e) {
      error = e.mensaje;
      notifyListeners();
      return null;
    }
  }

  /// Vuelve a pedir la cola (se llama solo con cada aviso y cada 20 s).
  Future<void> refrescar() async {
    if (_pidiendo) {
      _otraVez = true;
      return;
    }
    _pidiendo = true;
    try {
      _aplicar(await _llamar('fiesta_ver', {'p_codigo': codigo}));
    } catch (_) {
      // se reintenta con el siguiente aviso
    } finally {
      _pidiendo = false;
    }
    if (_otraVez) {
      _otraVez = false;
      await refrescar();
    }
  }

  Future<void> quitar(CancionFiesta c) => _hacer(() async =>
      _aplicar(await _llamar('fiesta_quitar', {'p_codigo': codigo, 'p_clave': clave, 'p_cancion': c.id})));

  Future<void> fijarLimite(int limite) => _hacer(() async =>
      _aplicar(await _llamar('fiesta_limite', {'p_codigo': codigo, 'p_clave': clave, 'p_limite': limite.clamp(0, 50)})));

  Future<void> renombrar(String nombre) => _hacer(() async =>
      _aplicar(await _llamar('fiesta_renombrar', {'p_codigo': codigo, 'p_clave': clave, 'p_nombre': nombre})));

  void fijarAutomatico(bool si) {
    automatico = si;
    notifyListeners();
    if (si) revisarSiguiente();
  }

  /// Suena ya esta canción de la cola (sale de la cola).
  Future<void> ponerAhora(CancionFiesta c) async {
    await control.ponerAhora(c.comoPista());
    // el aviso de «suena» lo manda _alReproductor al cambiar la pista
  }

  /// Pone la siguiente de la cola detrás de lo que suena (o la hace sonar si no suena nada).
  Future<bool> tomarSiguiente() async {
    if (_tomando || cerrada) return false;
    _tomando = true;
    try {
      final r = await _hacer(() => _llamar('fiesta_tomar', {'p_codigo': codigo, 'p_clave': clave}));
      final c = CancionFiesta.desde(r);
      if (c == null) return false;
      final pista = c.comoPista();
      if (control.actual == null || control.parado) {
        await control.ponerAhora(pista);
      } else {
        control.ponerDespues(pista);
      }
      unawaited(refrescar());
      return true;
    } finally {
      _tomando = false;
    }
  }

  /// Mira si toca poner la siguiente (modo automático).
  Future<void> revisarSiguiente() async {
    final e = estado;
    if (!automatico || cerrada || e == null || e.cola.isEmpty) return;
    final dur = control.duracionMs;
    final ok = debeTomarSiguiente(
      hayActual: control.actual != null,
      parado: control.parado,
      restanteMs: dur > 0 ? dur - control.posicionMs : null,
      hayPendiente: hayDeFiestaEnCola(control.proximas),
    );
    if (ok) await tomarSiguiente();
  }

  void _alReproductor() {
    if (cerrada) return;
    final actual = control.actual;
    final clavePista = clavePistaFiesta(actual);
    final pausa = control.enPausa;
    final cambio = clavePista != _ultimaClave;
    if (!cambio && pausa == _ultimaPausa) return;
    _ultimaClave = clavePista;
    _ultimaPausa = pausa;
    // al cambiar de pista se avisa enseguida; una pausa, con un respiro para no repetir
    _avisoSonando?.cancel();
    _avisoSonando = Timer(cambio ? const Duration(milliseconds: 300) : const Duration(milliseconds: 800), () {
      _hacer(() async => _aplicar(await _llamar('fiesta_sonando', {
            'p_codigo': codigo,
            'p_clave': clave,
            'p_pista': control.parado ? null : pistaParaSonando(control.actual, posMs: control.posicionMs, pausa: control.enPausa),
          })));
    });
    if (cambio) unawaited(revisarSiguiente());
  }

  /// Cierra la fiesta para todos.
  Future<void> cerrar() async {
    await _hacer(() async => _aplicar(await _llamar('fiesta_cerrar', {'p_codigo': codigo, 'p_clave': clave})));
    cerrada = true;
    await _soltar();
    if (activa.value == this) activa.value = null;
    notifyListeners();
  }

  Future<void> _soltar() async {
    control.removeListener(_alReproductor);
    _sondeo?.cancel();
    _tic?.cancel();
    _avisoSonando?.cancel();
    final c = _canal;
    _canal = null;
    if (c != null) await c.cerrar();
  }

  @override
  void dispose() {
    unawaited(_soltar());
    super.dispose();
  }
}
