import 'dart:async';
import 'dart:js_interop';
import 'dart:js_interop_unsafe';
import 'dart:math' show pow;

import 'package:flutter/foundation.dart';
import 'package:media_kit/media_kit.dart' show PlayerLog;
import 'package:media_kit_video/media_kit_video.dart' show VideoController;
import 'package:web/web.dart' as web;

import '../nucleo/archivos_web.dart';
import '../nucleo/streams.dart';
import 'jugador.dart';

/// El motor propio del navegador (`<audio>`): la música de la Comunidad, la que
/// cada persona guardó en su navegador y los sonidos de ambiente.
///
/// A diferencia del recuadro de YouTube, sigue sonando con el teléfono
/// bloqueado y lleva sus controles a la pantalla de bloqueo (sesion_medios.dart).
class JugadorAudio implements Jugador {
  /// [secundario]: ambiente o soniditos; no es «la música» de la página.
  JugadorAudio({this.secundario = false}) {
    _a.preload = 'auto';
    if (_conEcualizador) _a.crossOrigin = 'anonymous';
    _oir('timeupdate', _alAvanzar);
    _oir('durationchange', () {
      final d = _a.duration;
      if (_vale && d.isFinite && d > 0) _dur.add(Duration(milliseconds: (d * 1000).round()));
    });
    _oir('loadedmetadata', () {
      final i = _inicio;
      _inicio = null;
      if (_vale && i != null) _a.currentTime = i.inMilliseconds / 1000;
      _a.playbackRate = _velocidad;
    });
    _oir('playing', () {
      if (!_vale) return;
      _fijarEspera(false);
      _fijarSonando(true);
    });
    _oir('pause', () {
      // al terminar también llega «pause»: de eso avisa «ended»
      if (_vale && !_a.ended) _fijarSonando(false);
    });
    _oir('waiting', () {
      if (_vale && !_a.paused) _fijarEspera(true);
    });
    _oir('canplay', () {
      if (_vale) _fijarEspera(false);
    });
    _oir('ended', () {
      if (!_vale) return;
      _estado.playing = false;
      _fin.add(true);
    });
    _oir('error', () {
      if (!_vale) return;
      _fijarEspera(false);
      _error.add(switch (_a.error?.code) {
        2 => 'Se cortó la conexión',
        3 => 'El archivo está dañado',
        4 => 'El navegador no puede abrir este audio',
        _ => 'No se pudo reproducir',
      });
    });
    _porDesbloquear.add(this);
    if (!secundario) _vivos.add(this);
    _vigilarPrimerToque();
  }

  final bool secundario;
  final web.HTMLAudioElement _a = web.HTMLAudioElement();

  final _pos = StreamController<Duration>.broadcast();
  final _dur = StreamController<Duration>.broadcast();
  final _sonando = StreamController<bool>.broadcast();
  final _esperando = StreamController<bool>.broadcast();
  final _fin = StreamController<bool>.broadcast();
  final _error = StreamController<String>.broadcast();
  final _log = StreamController<PlayerLog>.broadcast();
  final _estado = _EstadoAudio();

  Duration? _inicio;
  double _velocidad = 1;
  int _vuelta = 0;
  bool _cerrado = false;

  /// ¿Tiene una canción puesta? (lo que pasa al desbloquear no cuenta)
  bool _puesta = false;
  bool get _vale => _puesta && !_cerrado;

  @override
  late final FlujosJugador stream = FlujosJugador(
    position: _pos.stream, duration: _dur.stream, playing: _sonando.stream, buffering: _esperando.stream,
    completed: _fin.stream, error: _error.stream, log: _log.stream,
  );

  @override
  EstadoJugador get state => _estado;

  @override
  VideoController? get video => null;

  void _oir(String evento, void Function() hacer) =>
      _a.addEventListener(evento, ((web.Event _) => hacer()).toJS);

  void _alAvanzar() {
    if (!_vale || _inicio != null) return;
    final p = Duration(milliseconds: (_a.currentTime * 1000).round());
    _estado.position = p;
    _pos.add(p);
  }

  void _fijarSonando(bool v) {
    if (_estado.playing == v) return;
    _estado.playing = v;
    _sonando.add(v);
  }

  void _fijarEspera(bool v) {
    if (_estado.buffering == v) return;
    _estado.buffering = v;
    _esperando.add(v);
  }

  // ------------------------------------------------------------ el primer toque

  // Los navegadores de teléfono solo dejan sonar lo que arrancó con un toque.
  // Con el primero se «estrenan» todos los motores con un silencio, y desde ahí
  // pueden pasar de canción solos, también con la pantalla apagada.
  static final Set<JugadorAudio> _porDesbloquear = {};
  static bool _vigilando = false;
  static String _silencio = '';

  static void _vigilarPrimerToque() {
    if (_vigilando) return;
    _vigilando = true;
    for (final e in ['pointerup', 'touchend', 'keydown']) {
      web.document.addEventListener(e, ((web.Event _) {
        for (final j in _porDesbloquear.toList()) {
          j._estrenar();
        }
        _reanudarMezcla();
      }).toJS, true.toJS);
    }
  }

  void _estrenar() {
    _porDesbloquear.remove(this);
    if (_puesta || _cerrado) return;
    if (_silencio.isEmpty) _silencio = ArchivosWeb.urlTemporal(_wavMudo(), 'audio/wav');
    _a.src = _silencio;
    unawaited(_a.play().toDart.then((_) {}, onError: (Object _) {}));
  }

  static Uint8List _wavMudo() {
    const hz = 8000, n = 400;
    final d = ByteData(44 + n);
    void texto(int i, String s) {
      for (var k = 0; k < s.length; k++) {
        d.setUint8(i + k, s.codeUnitAt(k));
      }
    }

    texto(0, 'RIFF');
    d.setUint32(4, 36 + n, Endian.little);
    texto(8, 'WAVEfmt ');
    d.setUint32(16, 16, Endian.little);
    d.setUint16(20, 1, Endian.little);
    d.setUint16(22, 1, Endian.little);
    d.setUint32(24, hz, Endian.little);
    d.setUint32(28, hz, Endian.little);
    d.setUint16(32, 1, Endian.little);
    d.setUint16(34, 8, Endian.little);
    texto(36, 'data');
    d.setUint32(40, n, Endian.little);
    for (var i = 0; i < n; i++) {
      d.setUint8(44 + i, 128);
    }
    return d.buffer.asUint8List();
  }

  // ------------------------------------------------------------ órdenes

  Future<void> _tocar() async {
    _prepararMezcla();
    try {
      await _a.play().toDart;
    } catch (e) {
      // se cambió de canción mientras arrancaba: no es un fallo
      if (!_vale || '$e'.contains('AbortError')) return;
      if ('$e'.contains('NotAllowed')) {
        _fijarEspera(false);
        _estado.playing = false;
        _sonando.add(false); // queda en pausa: hace falta un toque
      }
    }
  }

  @override
  Future<void> open(Fuente f, {Duration? inicio, bool play = true}) async {
    final v = ++_vuelta;
    _puesta = true;
    _inicio = inicio;
    _estado.position = inicio ?? Duration.zero;
    _estado.playing = false;
    _estado.buffering = false;
    _fijarEspera(true);
    var url = f.url;
    if (ArchivosWeb.esRef(url)) {
      String? u;
      try {
        u = await ArchivosWeb.url(url);
      } catch (_) {}
      if (v != _vuelta || _cerrado) return;
      if (u == null) {
        _fijarEspera(false);
        _error.add('Esta canción ya no está en el navegador');
        return;
      }
      url = u;
    }
    if (!secundario) _sesionDeMusica();
    _a.src = url;
    _a.playbackRate = _velocidad;
    if (play) unawaited(_tocar());
  }

  /// iPhone: que cuente como música (suena con el interruptor en silencio y de fondo).
  static void _sesionDeMusica() {
    try {
      final n = web.window.navigator as JSObject;
      if (n.has('audioSession')) (n['audioSession'] as JSObject)['type'] = 'playback'.toJS;
    } catch (_) {}
  }

  @override
  Future<void> play() async {
    if (_puesta) await _tocar();
  }

  @override
  Future<void> pause() async => _a.pause();
  @override
  Future<void> playOrPause() async => _a.paused ? play() : pause();

  @override
  Future<void> seek(Duration d) async {
    _estado.position = d;
    if (_a.readyState == 0) {
      _inicio = d; // aún no sabe cuánto dura: se pone al cargar
    } else {
      _a.currentTime = d.inMilliseconds / 1000;
    }
  }

  @override
  Future<void> setVolume(double v) async => _a.volume = (v / 100).clamp(0.0, 1.0);

  @override
  Future<void> setRate(double v) async {
    _velocidad = v;
    _a.defaultPlaybackRate = v;
    _a.playbackRate = v;
  }

  @override
  Future<void> stop() async {
    _vuelta++;
    _puesta = false;
    _inicio = null;
    _estado
      ..playing = false
      ..buffering = false
      ..position = Duration.zero;
    _a.pause();
    _a.removeAttribute('src');
    _a.load();
  }

  @override
  Future<void> dispose() async {
    if (_cerrado) return;
    await stop();
    _cerrado = true;
    _porDesbloquear.remove(this);
    _vivos.remove(this);
    for (final c in [_pos, _dur, _sonando, _esperando, _fin, _error, _log]) {
      await c.close();
    }
  }

  @override
  Future<void> setProperty(String clave, String valor) async {
    if (clave == 'loop-file') _a.loop = valor == 'inf';
    if (clave == 'af') {
      _filtros = filtrosDeMpv(valor);
      _prepararMezcla();
      _aplicarFiltros();
    }
  }

  @override
  Future<String?> getProperty(String clave) async => null;
  @override
  Future<void> command(List<String> orden) async {}

  // ------------------------------------------------------------ ecualizador

  // Solo en la PC: en los teléfonos, pasar el sonido por Web Audio hace que se
  // calle al bloquear la pantalla, que es justo lo que este motor evita.
  static bool get _conEcualizador =>
      defaultTargetPlatform == TargetPlatform.windows || defaultTargetPlatform == TargetPlatform.linux ||
      (defaultTargetPlatform == TargetPlatform.macOS && web.window.navigator.maxTouchPoints <= 1);

  static web.AudioContext? _mezcla;
  List<(double, double)> _filtros = const [];
  web.MediaElementAudioSourceNode? _entrada;
  web.GainNode? _margen;
  List<web.BiquadFilterNode> _nodos = [];

  static void _reanudarMezcla() {
    final m = _mezcla;
    if (m != null && m.state == 'suspended') unawaited(m.resume().toDart.then((_) {}, onError: (Object _) {}));
  }

  /// La cadena se monta la primera vez que hay ecualizador (y ya no se quita).
  void _prepararMezcla() {
    if (secundario || !_conEcualizador || _entrada != null || !_puesta) return;
    if (_filtros.isEmpty && !_midiendo) return;
    try {
      final m = _mezcla ??= web.AudioContext();
      _entrada = m.createMediaElementSource(_a);
      _margen = m.createGain();
      _aplicarFiltros();
      _reanudarMezcla();
    } catch (e) {
      debugPrint('ecualizador web: $e');
    }
  }

  void _aplicarFiltros() {
    final e = _entrada;
    final g = _margen;
    final m = _mezcla;
    if (e == null || g == null || m == null) return;
    e.disconnect();
    g.disconnect();
    for (final n in _nodos) {
      n.disconnect();
    }
    _nodos = [
      for (final (hz, db) in _filtros)
        m.createBiquadFilter()
          ..type = 'peaking'
          ..frequency.value = hz
          ..Q.value = 1.41
          ..gain.value = db,
    ];
    // margen para que al subir bandas no sature
    final maximo = _filtros.fold<double>(0, (a, x) => x.$2 > a ? x.$2 : a);
    g.gain.value = pow(10, -maximo * 0.6 / 20).toDouble();
    web.AudioNode ultimo = e;
    ultimo.connect(g);
    ultimo = g;
    for (final n in _nodos) {
      ultimo.connect(n);
      ultimo = n;
    }
    ultimo.connect(m.destination);
    if (_midiendo) ultimo.connect(_analizador(m));
  }

  // ------------------------------------------------------------ espectro (visualizador)

  static bool _midiendo = false;
  static web.AnalyserNode? _medidor;
  static final Set<JugadorAudio> _vivos = {};

  static web.AnalyserNode _analizador(web.AudioContext m) => _medidor ??= m.createAnalyser()
    ..fftSize = 2048
    ..smoothingTimeConstant = 0.6;

  /// Mide el sonido que sale (solo en la PC; ver [_conEcualizador]).
  static void medir(bool si) {
    _midiendo = si;
    for (final j in _vivos) {
      if (j._entrada == null) {
        j._prepararMezcla();
      } else {
        j._aplicarFiltros();
      }
    }
  }

  /// (bandas 0..255 de graves a agudos, frecuencia de muestreo), o null si no se mide.
  static (List<int>, double)? espectro() {
    final a = _medidor;
    final m = _mezcla;
    if (!_midiendo || a == null || m == null || m.state != 'running') return null;
    final d = JSUint8Array.withLength(a.frequencyBinCount);
    a.getByteFrequencyData(d);
    return (d.toDart, m.sampleRate.toDouble());
  }
}

/// (frecuencia, dB) de cada `equalizer=f=…:g=…` de una cadena de filtros de mpv.
List<(double, double)> filtrosDeMpv(String cadena) => [
      for (final m in RegExp(r'equalizer=f=([\d.]+)[^,\]]*?:g=(-?[\d.]+)').allMatches(cadena))
        (double.parse(m.group(1)!), double.parse(m.group(2)!)),
    ];

class _EstadoAudio implements EstadoJugador {
  @override
  Duration position = Duration.zero;
  @override
  bool playing = false;
  @override
  bool buffering = false;
}
