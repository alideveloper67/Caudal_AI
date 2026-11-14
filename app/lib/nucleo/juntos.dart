import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/foundation.dart';

import 'coleccion.dart';
import 'nube.dart';

/// "Escuchar juntos": salas sin tablas sobre Supabase Realtime (Broadcast +
/// Presence) por websocket, con el protocolo de Phoenix.
///
/// - Presence dice quien esta en la sala (cada aparato es un miembro, aunque
///   dos usen la misma cuenta o cada uno la suya).
/// - El anfitrion manda por Broadcast lo que suena (pista, posicion, pausa)
///   cada pocos segundos y al instante si cambia algo; los demas lo siguen.
/// - La posicion va con la hora del reloj del anfitrion: cada invitado mide
///   la diferencia entre su reloj y el del anfitrion con ping/pong y corrige
///   con un salto si se aleja mas de [desfaseMaximo].
/// - Si el anfitrion se va, lo es el miembro que lleva mas tiempo en la sala.

/// Mas de esto de diferencia con el anfitrion y se salta a su posicion.
const desfaseMaximo = Duration(milliseconds: 1500);

const emojisJuntos = ['❤️', '🔥', '😂', '😍', '👏', '🎉', '😮', '🕺'];

const _alfabeto = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // sin 0/O ni 1/I
final _azar = Random.secure();

int _ahora() => DateTime.now().millisecondsSinceEpoch;

/// Codigo corto de sala: 6 caracteres faciles de dictar.
String nuevoCodigoSala() => List.generate(6, (_) => _alfabeto[_azar.nextInt(_alfabeto.length)]).join();

String enlaceSala(String codigo) => 'caudal://juntos?sala=$codigo';

/// Saca el codigo de un enlace (caudal://juntos?sala=…, o https://…?sala=…)
/// o de lo que se escribio a mano. Nulo si no parece un codigo.
String? codigoDeTexto(String texto) {
  var t = texto.trim();
  final uri = Uri.tryParse(t);
  if (uri != null && uri.queryParameters['sala'] != null) t = uri.queryParameters['sala']!;
  t = t.toUpperCase().replaceAll(RegExp(r'[\s-]'), '');
  return RegExp('^[$_alfabeto]{6}\$').hasMatch(t) ? t : null;
}

/// Lo que se manda de una pista: solo datos sencillos, nunca rutas de archivos
/// de este aparato (al otro no le sirven).
Json pistaParaCompartir(Json p) => {
      for (final e in p.entries)
        if (e.key != 'archivo' && (e.value is String || e.value is num || e.value is bool)) e.key: e.value,
    };

String clavePista(Json? p) {
  if (p == null) return '';
  final v = '${p['video_id'] ?? ''}';
  if (v.isNotEmpty) return 'v:$v';
  final c = '${p['clave'] ?? ''}';
  if (c.isNotEmpty) return 'c:$c';
  return 't:${p['titulo'] ?? ''}|${p['artista'] ?? ''}';
}

/// Donde deberia ir la cancion del anfitrion AHORA en este aparato.
/// [diferencia] = reloj del anfitrion - reloj local (ms).
Duration posicionEsperada({required int posMs, required bool sonando, required int enviadoMs,
    required int diferencia, int? ahoraLocal, double velocidad = 1}) {
  if (!sonando) return Duration(milliseconds: posMs);
  final transcurrido = max(0, (ahoraLocal ?? _ahora()) + diferencia - enviadoMs);
  return Duration(milliseconds: posMs + (transcurrido * velocidad).round());
}

// ====================================================================== canal

/// Un canal de Supabase Realtime (protocolo Phoenix 1.0.0) con latido y
/// reconexion. Sin tablas: solo Broadcast y Presence.
class CanalRealtime {
  CanalRealtime(this.tema, {required this.clavePresencia, this.alMensaje, this.alPresencia,
      this.alEstadoConexion, String? urlBase, String? clave})
      : _urlBase = urlBase ?? Nube.url,
        _clave = clave ?? Nube.clavePublica;

  final String tema; // p. ej. realtime:juntos-ABC123
  final String clavePresencia;
  final void Function(String evento, Map<String, dynamic> datos)? alMensaje;
  final void Function()? alPresencia;
  final void Function(bool conectado)? alEstadoConexion;
  final String _urlBase;
  final String _clave;

  WebSocket? _ws;
  Timer? _latido;
  Timer? _reintento;
  int _ref = 0;
  String? _refUnion;
  String? _latidoPendiente;
  int _intentos = 0;
  bool _cerrado = false;
  bool unido = false;
  Map<String, dynamic>? _miPresencia;
  Completer<void>? _union;

  /// clave de presencia -> datos (la primera meta de cada una).
  final Map<String, Map<String, dynamic>> presentes = {};

  String _siguienteRef() => '${++_ref}';

  Uri get _uri {
    final base = Uri.parse(_urlBase);
    return Uri(scheme: base.scheme == 'http' ? 'ws' : 'wss', host: base.host, port: base.hasPort ? base.port : null,
        path: '/realtime/v1/websocket', queryParameters: {'apikey': _clave, 'vsn': '1.0.0'});
  }

  /// Conecta y entra en el tema. Falla con [ErrorJuntos] si no se puede.
  Future<void> abrir({Duration espera = const Duration(seconds: 12)}) async {
    _cerrado = false;
    _union = Completer<void>();
    await _conectar();
    await _union!.future.timeout(espera, onTimeout: () {
      throw const ErrorJuntos('La sala no respondió. Revisa tu conexión a internet.');
    });
  }

  Future<void> _conectar() async {
    try {
      final ws = await WebSocket.connect(_uri.toString()).timeout(const Duration(seconds: 10));
      if (_cerrado) {
        await ws.close();
        return;
      }
      _ws = ws;
      _intentos = 0;
      ws.listen(_recibir, onDone: _caido, onError: (_) => _caido(), cancelOnError: true);
      _refUnion = _siguienteRef();
      _enviarCrudo('phx_join', {
        'config': {
          'broadcast': {'self': false, 'ack': false},
          'presence': {'key': clavePresencia, 'enabled': true},
          'postgres_changes': [],
          'private': false,
        },
      }, ref: _refUnion);
      _latidoPendiente = null;
      _latido?.cancel();
      _latido = Timer.periodic(const Duration(seconds: 25), (_) => _latir());
    } on WebSocketException catch (e) {
      _fallo(ErrorJuntos(e.message.contains('404') || e.message.contains('403')
          ? 'El servicio de salas (Supabase Realtime) no está habilitado en el proyecto.'
          : 'No se pudo abrir la sala: ${e.message}'));
    } catch (_) {
      _fallo(const ErrorJuntos('Sin conexión con el servicio de salas.'));
    }
  }

  void _fallo(ErrorJuntos e) {
    final u = _union;
    if (u != null && !u.isCompleted) {
      u.completeError(e);
      return;
    }
    _programarReintento();
  }

  void _latir() {
    if (_latidoPendiente != null) {
      // el anterior no volvio: la conexion esta muerta aunque no lo parezca
      _ws?.close();
      return;
    }
    _latidoPendiente = _siguienteRef();
    _ws?.add(jsonEncode({'topic': 'phoenix', 'event': 'heartbeat', 'payload': {}, 'ref': _latidoPendiente}));
  }

  void _enviarCrudo(String evento, Map<String, dynamic> datos, {String? ref}) {
    final ws = _ws;
    if (ws == null || ws.readyState != WebSocket.open) return;
    ws.add(jsonEncode({
      'topic': tema, 'event': evento, 'payload': datos, 'ref': ref ?? _siguienteRef(), 'join_ref': _refUnion,
    }));
  }

  /// Manda un aviso a todos los demas de la sala (no vuelve a uno mismo).
  void difundir(String evento, Map<String, dynamic> datos) {
    if (!unido) return;
    _enviarCrudo('broadcast', {'type': 'broadcast', 'event': evento, 'payload': datos});
  }

  /// Anuncia (o actualiza) quien soy en la lista de la sala.
  void presentarme(Map<String, dynamic> datos) {
    _miPresencia = datos;
    if (unido) _enviarCrudo('presence', {'type': 'presence', 'event': 'track', 'payload': datos});
  }

  void _recibir(dynamic crudo) {
    Map<String, dynamic> m;
    try {
      m = (jsonDecode('$crudo') as Map).cast<String, dynamic>();
    } catch (_) {
      return;
    }
    final evento = '${m['event']}';
    final datos = (m['payload'] is Map) ? (m['payload'] as Map).cast<String, dynamic>() : <String, dynamic>{};
    if (m['topic'] == 'phoenix') {
      if (evento == 'phx_reply' && m['ref'] == _latidoPendiente) _latidoPendiente = null;
      return;
    }
    if (m['topic'] != tema) return;
    switch (evento) {
      case 'phx_reply':
        if (m['ref'] == _refUnion) {
          if (datos['status'] == 'ok') {
            unido = true;
            alEstadoConexion?.call(true);
            if (_miPresencia != null) presentarme(_miPresencia!);
            final u = _union;
            if (u != null && !u.isCompleted) u.complete();
          } else {
            final r = '${(datos['response'] as Map?)?['reason'] ?? datos['response'] ?? ''}';
            _fallo(ErrorJuntos('La sala rechazó la entrada${r.isEmpty ? '' : ': $r'}.'));
          }
        }
      case 'presence_state':
        presentes.clear();
        _sumar(datos);
        alPresencia?.call();
      case 'presence_diff':
        final fuera = (datos['leaves'] as Map?)?.cast<String, dynamic>() ?? {};
        for (final k in fuera.keys) {
          presentes.remove(k);
        }
        _sumar((datos['joins'] as Map?)?.cast<String, dynamic>() ?? {});
        alPresencia?.call();
      case 'broadcast':
        final ev = '${datos['event'] ?? ''}';
        final p = (datos['payload'] is Map) ? (datos['payload'] as Map).cast<String, dynamic>() : <String, dynamic>{};
        alMensaje?.call(ev, p);
      case 'phx_error':
      case 'phx_close':
        if (!_cerrado) _ws?.close();
      case 'system':
        if (datos['status'] == 'error') {
          final u = _union;
          if (u != null && !u.isCompleted) {
            u.completeError(ErrorJuntos('El servicio de salas falló: ${datos['message'] ?? ''}'));
          }
        }
    }
  }

  void _sumar(Map<String, dynamic> entradas) {
    entradas.forEach((clave, v) {
      final metas = (v is Map ? v['metas'] : null) as List?;
      if (metas == null || metas.isEmpty) return;
      presentes[clave] = (metas.last as Map).cast<String, dynamic>();
    });
  }

  void _caido() {
    _latido?.cancel();
    _ws = null;
    if (unido) alEstadoConexion?.call(false);
    unido = false;
    if (_cerrado) return;
    final u = _union;
    if (u != null && !u.isCompleted) {
      u.completeError(const ErrorJuntos('Se cortó la conexión con la sala.'));
      return;
    }
    _programarReintento();
  }

  void _programarReintento() {
    if (_cerrado) return;
    _reintento?.cancel();
    final s = min(30, [1, 2, 4, 8, 15][min(_intentos, 4)]);
    _intentos++;
    _reintento = Timer(Duration(seconds: s), () {
      if (!_cerrado) _conectar();
    });
  }

  Future<void> cerrar() async {
    _cerrado = true;
    _reintento?.cancel();
    _latido?.cancel();
    final ws = _ws;
    if (ws != null && unido) {
      _enviarCrudo('phx_leave', {});
    }
    unido = false;
    _ws = null;
    try {
      await ws?.close(1000);
    } catch (_) {}
  }
}

class ErrorJuntos implements Exception {
  const ErrorJuntos(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

// ================================================================ reproductor

/// Lo que la sala necesita del reproductor (asi se prueba sin libmpv). El
/// adaptador del `Reproductor` de la app es `ControlReproductor`, en la pagina.
abstract class ControlJuntos implements Listenable {
  Json? get pista;
  Duration get posicion;
  bool get sonando;

  /// Cargando una pista (no tiene sentido corregir la posicion todavia).
  bool get cargando;
  Future<void> cargar(Json pista, {Duration inicio = Duration.zero, bool pausado = false});
  Future<void> buscar(Duration p);
  Future<void> pausar();
  Future<void> reanudar();
}

// ======================================================================= sala

class MiembroJuntos {
  const MiembroJuntos({required this.id, required this.nombre, required this.usuario, required this.entro});
  final String id;
  final String nombre;
  final String usuario;
  final int entro;

  factory MiembroJuntos.desde(String clave, Map<String, dynamic> d) => MiembroJuntos(
        id: clave,
        nombre: '${d['nombre'] ?? 'Alguien'}',
        usuario: '${d['usuario'] ?? ''}',
        entro: (d['entro'] as num?)?.toInt() ?? 0,
      );
}

class ReaccionJuntos {
  const ReaccionJuntos(this.emoji, this.nombre, this.deMi);
  final String emoji;
  final String nombre;
  final bool deMi;
}

/// Una sala de "Escuchar juntos". Se crea con [SalaJuntos.crear] o
/// [SalaJuntos.unirse]; sigue viva aunque se cierre la pantalla, hasta [salir].
class SalaJuntos extends ChangeNotifier {
  SalaJuntos._(this.codigo, this.control, {required this.nombre, required this.usuario,
      required bool anfitrion, String? urlBase, String? clave})
      : miId = List.generate(12, (_) => _alfabeto[_azar.nextInt(_alfabeto.length)]).join(),
        _soyAnfitrionInicial = anfitrion {
    canal = CanalRealtime('realtime:juntos-$codigo',
        clavePresencia: miId,
        alMensaje: _alMensaje,
        alPresencia: _alPresencia,
        alEstadoConexion: (c) {
          conectado = c;
          if (c) _alReconectar();
          notifyListeners();
        },
        urlBase: urlBase,
        clave: clave);
  }

  /// La sala abierta en la app (una a la vez). La pantalla la mira.
  static final ValueNotifier<SalaJuntos?> activa = ValueNotifier(null);

  final String codigo;
  final ControlJuntos control;
  final String nombre;
  final String usuario;
  final String miId;
  final bool _soyAnfitrionInicial;
  late final CanalRealtime canal;

  String get enlace => enlaceSala(codigo);
  bool conectado = false;
  bool cerrada = false;
  String? anfitrionId;
  int _rangoAnfitrion = 0; // "entro" del anfitrion, para desempatar
  late int _entro;
  bool get soyAnfitrion => anfitrionId == miId;

  /// Reloj del anfitrion - reloj local, y lo que tardo la mejor medida.
  int diferenciaReloj = 0;
  int? _mejorIda;
  final List<(int, int)> _medidas = []; // (ida y vuelta, diferencia)

  Map<String, dynamic>? ultimoEstado;
  int _recibidoEn = 0;
  String? aviso;

  final _reacciones = StreamController<ReaccionJuntos>.broadcast();
  Stream<ReaccionJuntos> get reacciones => _reacciones.stream;

  Timer? _tic;
  Timer? _ping;
  Timer? _esperaAnfitrion;
  int _seq = 0;
  int _ultimoSalto = 0;
  bool _aplicando = false;
  String _cargandoClave = '';
  // lo ultimo que mando el anfitrion (para notar saltos y cambios)
  String _envClave = '';
  bool _envSonando = false;
  int _envPos = 0;
  int _envEn = 0;
  int _envForzado = 0;

  List<MiembroJuntos> get miembros {
    final l = canal.presentes.entries.map((e) => MiembroJuntos.desde(e.key, e.value)).toList()
      ..sort((a, b) => a.entro != b.entro ? a.entro.compareTo(b.entro) : a.id.compareTo(b.id));
    return l;
  }

  MiembroJuntos? get anfitrion {
    for (final m in miembros) {
      if (m.id == anfitrionId) return m;
    }
    return null;
  }

  /// Pista que suena en la sala (la del ultimo estado del anfitrion).
  Json? get pistaSala {
    if (soyAnfitrion) return control.pista;
    final p = ultimoEstado?['pista'];
    return p is Map ? p.cast<String, dynamic>() : null;
  }

  static Future<SalaJuntos> crear({required ControlJuntos control, required String nombre,
      String usuario = '', String? urlBase, String? clave}) async {
    final s = SalaJuntos._(nuevoCodigoSala(), control,
        nombre: nombre, usuario: usuario, anfitrion: true, urlBase: urlBase, clave: clave);
    await s._abrir();
    return s;
  }

  static Future<SalaJuntos> unirse(String codigoOEnlace, {required ControlJuntos control,
      required String nombre, String usuario = '', String? urlBase, String? clave}) async {
    final c = codigoDeTexto(codigoOEnlace);
    if (c == null) throw const ErrorJuntos('Ese código no es válido: son 6 letras o números.');
    final s = SalaJuntos._(c, control, nombre: nombre, usuario: usuario, anfitrion: false,
        urlBase: urlBase, clave: clave);
    await s._abrir();
    return s;
  }

  Future<void> _abrir() async {
    _entro = _ahora();
    if (_soyAnfitrionInicial) {
      anfitrionId = miId;
      _rangoAnfitrion = _entro;
    }
    canal.presentarme(_miPresencia());
    await canal.abrir();
    conectado = true;
    control.addListener(_alCambiarReproductor);
    _tic = Timer.periodic(const Duration(milliseconds: 500), (_) => _cadaMedioSegundo());
    _ping = Timer.periodic(const Duration(seconds: 4), (_) => _medirReloj());
    if (soyAnfitrion) {
      _mandarEstado();
    } else {
      canal.difundir('hola', {'de': miId});
      _medirReloj();
      // si nadie responde (sala vacia), uno mismo pasa a ser el anfitrion
      _esperaAnfitrion = Timer(const Duration(seconds: 5), () {
        if (anfitrionId == null) _elegirAnfitrion();
      });
    }
    notifyListeners();
  }

  Map<String, dynamic> _miPresencia() => {'nombre': nombre, 'usuario': usuario, 'entro': _entro};

  void _alReconectar() {
    if (soyAnfitrion) {
      _mandarEstado();
    } else {
      canal.difundir('hola', {'de': miId});
    }
  }

  // ------------------------------------------------------------- anfitrion

  void _alPresencia() {
    if (anfitrionId != null && !canal.presentes.containsKey(anfitrionId) && anfitrionId != miId) {
      // el anfitrion se fue: le toca al que lleva mas tiempo
      anfitrionId = null;
      _elegirAnfitrion();
    }
    notifyListeners();
  }

  void _elegirAnfitrion() {
    final ms = miembros;
    final yo = MiembroJuntos(id: miId, nombre: nombre, usuario: usuario, entro: _entro);
    if (!ms.any((m) => m.id == miId)) ms.add(yo);
    ms.sort((a, b) => a.entro != b.entro ? a.entro.compareTo(b.entro) : a.id.compareTo(b.id));
    final nuevo = ms.first;
    anfitrionId = nuevo.id;
    _rangoAnfitrion = nuevo.entro;
    _reiniciarReloj();
    if (nuevo.id == miId) {
      aviso = 'Ahora eres quien pone la música.';
      _mandarEstado();
    }
    notifyListeners();
  }

  void _reiniciarReloj() {
    _medidas.clear();
    _mejorIda = null;
    diferenciaReloj = 0;
  }

  /// El anfitrion le pasa el mando a otro miembro.
  void cederAnfitrion(String id) {
    if (!soyAnfitrion || id == miId || !canal.presentes.containsKey(id)) return;
    canal.difundir('ceder', {'a': id, 'de': miId});
    anfitrionId = id;
    _rangoAnfitrion = MiembroJuntos.desde(id, canal.presentes[id]!).entro;
    _reiniciarReloj();
    notifyListeners();
  }

  void _alCambiarReproductor() {
    if (!soyAnfitrion) return;
    final c = clavePista(control.pista);
    if (c != _envClave || control.sonando != _envSonando) _mandarEstado();
  }

  void _mandarEstado() {
    if (!soyAnfitrion || cerrada) return;
    final p = control.pista;
    final ahora = _ahora();
    _envClave = clavePista(p);
    _envSonando = control.sonando;
    _envPos = control.posicion.inMilliseconds;
    _envEn = ahora;
    canal.difundir('estado', {
      'de': miId,
      'rango': _rangoAnfitrion,
      'seq': ++_seq,
      'pista': p == null ? null : pistaParaCompartir(p),
      'pos': _envPos,
      'sonando': _envSonando,
      't': ahora,
    });
  }

  void _cadaMedioSegundo() {
    if (cerrada) return;
    if (soyAnfitrion) {
      final ahora = _ahora();
      final esperada = _envSonando ? _envPos + (ahora - _envEn) : _envPos;
      final salto = (control.posicion.inMilliseconds - esperada).abs() > desfaseMaximo.inMilliseconds;
      if ((salto && !control.cargando) || ahora - _envEn > 2500 || (_envForzado > 0 && ahora > _envForzado)) {
        _envForzado = 0;
        _mandarEstado();
      }
    } else {
      _seguir();
    }
  }

  // ------------------------------------------------------------- invitados

  void _alMensaje(String ev, Map<String, dynamic> d) {
    if (cerrada) return;
    switch (ev) {
      case 'estado':
        _alEstado(d);
      case 'hola':
        // alguien entro: que reciba ya lo que suena
        if (soyAnfitrion) _envForzado = _ahora() + 150;
      case 'ping':
        if (soyAnfitrion && d['a'] == miId) {
          canal.difundir('pong', {'para': d['de'], 't0': d['t0'], 'th': _ahora()});
        }
      case 'pong':
        if (d['para'] == miId) _alPong(d);
      case 'ceder':
        anfitrionId = '${d['a']}';
        final m = canal.presentes[anfitrionId];
        if (m != null) _rangoAnfitrion = MiembroJuntos.desde(anfitrionId!, m).entro;
        _reiniciarReloj();
        if (soyAnfitrion) {
          aviso = 'Te pasaron el mando: ahora pones la música.';
          _mandarEstado();
        }
        notifyListeners();
      case 'reaccion':
        final e = '${d['emoji'] ?? ''}';
        if (e.isNotEmpty && e.runes.length <= 8) {
          _reacciones.add(ReaccionJuntos(e, '${d['nombre'] ?? ''}', false));
        }
    }
  }

  void _alEstado(Map<String, dynamic> d) {
    final de = '${d['de'] ?? ''}';
    final rango = (d['rango'] as num?)?.toInt() ?? 0;
    if (soyAnfitrion && de != miId) {
      // dos anfitriones a la vez (p. ej. tras un corte): se queda el mas antiguo
      final ganaEl = rango < _rangoAnfitrion || (rango == _rangoAnfitrion && de.compareTo(miId) < 0);
      if (!ganaEl) {
        _mandarEstado();
        return;
      }
    }
    if (anfitrionId != de) {
      anfitrionId = de;
      _rangoAnfitrion = rango;
      _reiniciarReloj();
      _medirReloj();
    }
    _esperaAnfitrion?.cancel();
    ultimoEstado = d;
    _recibidoEn = _ahora();
    _seguir();
    notifyListeners();
  }

  void _medirReloj() {
    if (soyAnfitrion || anfitrionId == null || cerrada) return;
    canal.difundir('ping', {'de': miId, 'a': anfitrionId, 't0': _ahora()});
  }

  void _alPong(Map<String, dynamic> d) {
    final t0 = (d['t0'] as num?)?.toInt();
    final th = (d['th'] as num?)?.toInt();
    if (t0 == null || th == null) return;
    final t1 = _ahora();
    final ida = t1 - t0;
    if (ida < 0 || ida > 10000) return;
    _medidas.add((ida, th - (t0 + t1) ~/ 2));
    if (_medidas.length > 10) _medidas.removeAt(0);
    // la medida con menos demora es la mas fiable
    final mejor = _medidas.reduce((a, b) => a.$1 <= b.$1 ? a : b);
    _mejorIda = mejor.$1;
    diferenciaReloj = mejor.$2;
  }

  /// Lleva el reproductor local a lo que dice el anfitrion.
  Future<void> _seguir() async {
    final e = ultimoEstado;
    if (e == null || soyAnfitrion || _aplicando || cerrada) return;
    _aplicando = true;
    try {
      final pista = e['pista'] is Map ? (e['pista'] as Map).cast<String, dynamic>() : null;
      final sonando = e['sonando'] == true;
      final esperada = posicionEsperada(
        posMs: (e['pos'] as num?)?.toInt() ?? 0,
        sonando: sonando,
        enviadoMs: (e['t'] as num?)?.toInt() ?? _recibidoEn,
        // sin medida del reloj todavia: se asume que el aviso tardo poco
        diferencia: _mejorIda == null ? ((e['t'] as num?)?.toInt() ?? _recibidoEn) - _recibidoEn : diferenciaReloj,
      );
      if (pista == null) {
        if (control.sonando) await control.pausar();
        return;
      }
      final clave = clavePista(pista);
      if (clavePista(control.pista) != clave) {
        if (_cargandoClave == clave) return;
        if ('${pista['video_id'] ?? ''}'.isEmpty) {
          aviso = 'Quien pone la música está oyendo un archivo suyo que no está en internet.';
          notifyListeners();
          return;
        }
        _cargandoClave = clave;
        await control.cargar(pista, inicio: esperada, pausado: !sonando);
        _cargandoClave = '';
        _ultimoSalto = 0;
        return;
      }
      if (control.cargando) return;
      if (sonando && !control.sonando) {
        await control.reanudar();
      } else if (!sonando && control.sonando) {
        await control.pausar();
      }
      final desfase = (control.posicion - esperada).inMilliseconds.abs();
      final ahora = _ahora();
      if (desfase > desfaseMaximo.inMilliseconds && ahora - _ultimoSalto > 2000) {
        _ultimoSalto = ahora;
        // un poco por delante: el salto tarda en hacerse
        await control.buscar(esperada + (sonando ? const Duration(milliseconds: 150) : Duration.zero));
      }
    } catch (_) {
      _cargandoClave = '';
    } finally {
      _aplicando = false;
    }
  }

  // ------------------------------------------------------------- reacciones

  void reaccionar(String emoji) {
    if (cerrada) return;
    canal.difundir('reaccion', {'emoji': emoji, 'nombre': nombre, 'de': miId});
    _reacciones.add(ReaccionJuntos(emoji, nombre, true));
  }

  Future<void> salir() async {
    if (cerrada) return;
    cerrada = true;
    _tic?.cancel();
    _ping?.cancel();
    _esperaAnfitrion?.cancel();
    control.removeListener(_alCambiarReproductor);
    await canal.cerrar();
    if (identical(activa.value, this)) activa.value = null;
    await _reacciones.close();
    notifyListeners();
  }
}
