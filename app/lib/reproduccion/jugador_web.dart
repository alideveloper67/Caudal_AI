import 'dart:async';
import 'dart:js_interop';
import 'dart:js_interop_unsafe';

import 'package:media_kit/media_kit.dart' show PlayerLog;
import 'package:media_kit_video/media_kit_video.dart' show VideoController;
import 'package:web/web.dart' as web;

import '../nucleo/streams.dart';
import 'jugador.dart';

/// El reproductor oficial de YouTube incrustado (versión web de Caudal).
///
/// Es la única forma permitida de que suenen canciones de YouTube desde una
/// web. Se ve en un recuadro en la esquina (YouTube exige que el video se vea)
/// que se puede agrandar. En la PC sigue sonando con la pantalla bloqueada o en
/// otra pestaña; en el navegador del teléfono YouTube lo pausa al bloquearlo.

bool get esJugadorWeb => true;

Jugador crearJugador() => _JugadorYouTube();

// ------------------------------------------------------------ el recuadro

web.HTMLDivElement? _caja;
bool _grande = false;

web.HTMLDivElement _contenedor() {
  final ya = _caja;
  if (ya != null) return ya;
  final c = web.document.createElement('div') as web.HTMLDivElement;
  c.id = 'caudal-video';
  _estiloCaja(c);
  web.document.body!.append(c);
  _caja = c;
  return c;
}

void _estiloCaja(web.HTMLDivElement c) {
  final s = c.style;
  s.position = 'fixed';
  s.zIndex = '20';
  s.overflow = 'hidden';
  s.background = '#000';
  s.borderRadius = '14px';
  s.boxShadow = '0 18px 40px rgba(0,0,0,.55)';
  final h = _hueco;
  if (h != null && !_grande) {
    s.transition = 'none';
    s.left = '${h.$1}px';
    s.top = '${h.$2}px';
    s.width = '${h.$3}px';
    s.height = '${h.$4}px';
    s.right = 'auto';
    s.bottom = 'auto';
    s.transform = 'none';
    s.borderRadius = '10px';
    return;
  }
  s.borderRadius = '14px';
  s.transition = 'all .25s ease';
  if (_grande) {
    s.left = '50%';
    s.right = 'auto';
    s.top = '72px';
    s.bottom = 'auto';
    s.width = 'min(92vw, 960px)';
    s.height = 'calc(min(92vw, 960px) * 0.5625)';
    s.transform = 'translateX(-50%)';
  } else {
    s.left = 'auto';
    s.right = '16px';
    s.top = 'auto';
    s.bottom = '148px';
    s.width = '224px';
    s.height = '126px';
    s.transform = 'none';
  }
}

/// Pone el recuadro justo encima de un hueco de la pantalla (la portada del
/// reproductor); null lo devuelve a la esquina.
(double, double, double, double)? _hueco;

void colocarVideo(double? x, double? y, double? ancho, double? alto) {
  _hueco = x == null ? null : (x, y!, ancho!, alto!);
  final c = _caja;
  if (c != null) _estiloCaja(c);
}

void mostrarVideoGrande(bool grande) {
  _grande = grande;
  final c = _caja;
  if (c != null) _estiloCaja(c);
}

void ocultarVideo(bool oculto) {
  final c = _caja;
  if (c != null) c.style.visibility = oculto ? 'hidden' : 'visible';
}

// ------------------------------------------------------------ la API de YouTube

Completer<void>? _cargando;

Future<void> _api() {
  final ya = _cargando;
  if (ya != null) return ya.future;
  final c = Completer<void>();
  _cargando = c;
  if (globalContext.has('YT') && (globalContext['YT'] as JSObject).has('Player')) {
    c.complete();
    return c.future;
  }
  globalContext['onYouTubeIframeAPIReady'] = (() {
    if (!c.isCompleted) c.complete();
  }).toJS;
  final s = web.document.createElement('script') as web.HTMLScriptElement;
  s.src = 'https://www.youtube.com/iframe_api';
  web.document.head!.append(s);
  return c.future;
}

int _contador = 0;

class _JugadorYouTube implements Jugador {
  _JugadorYouTube();

  final _pos = StreamController<Duration>.broadcast();
  final _dur = StreamController<Duration>.broadcast();
  final _sonando = StreamController<bool>.broadcast();
  final _esperando = StreamController<bool>.broadcast();
  final _fin = StreamController<bool>.broadcast();
  final _error = StreamController<String>.broadcast();
  final _log = StreamController<PlayerLog>.broadcast();

  JSObject? _yt;
  web.HTMLDivElement? _div;
  Completer<void>? _listo;
  Timer? _reloj;
  final _estado = _EstadoYouTube();
  double _volumen = 100;
  double _velocidad = 1;
  String _id = '';

  @override
  late final FlujosJugador stream = FlujosJugador(
    position: _pos.stream, duration: _dur.stream, playing: _sonando.stream, buffering: _esperando.stream,
    completed: _fin.stream, error: _error.stream, log: _log.stream,
  );

  @override
  EstadoJugador get state => _estado;

  @override
  VideoController? get video => null;

  Future<void> _preparar(String id, Duration? inicio, bool play) async {
    await _api();
    if (_yt != null) return;
    final caja = _contenedor();
    final div = web.document.createElement('div') as web.HTMLDivElement;
    div.id = 'caudal-yt-${_contador++}';
    div.style.position = 'absolute';
    div.style.inset = '0';
    caja.append(div);
    _div = div;
    final listo = Completer<void>();
    _listo = listo;
    final opciones = JSObject();
    opciones['width'] = '100%'.toJS;
    opciones['height'] = '100%'.toJS;
    opciones['videoId'] = id.toJS;
    final vars = JSObject();
    vars['playsinline'] = 1.toJS;
    vars['rel'] = 0.toJS;
    vars['autoplay'] = (play ? 1 : 0).toJS;
    if (inicio != null) vars['start'] = inicio.inSeconds.toJS;
    opciones['playerVars'] = vars;
    final eventos = JSObject();
    eventos['onReady'] = ((JSObject _) {
      if (!listo.isCompleted) listo.complete();
    }).toJS;
    eventos['onStateChange'] = ((JSObject e) => _alCambiar((e['data'] as JSNumber).toDartInt)).toJS;
    eventos['onError'] = ((JSObject e) => _alFallar((e['data'] as JSNumber).toDartInt)).toJS;
    opciones['events'] = eventos;
    final clase = (globalContext['YT'] as JSObject)['Player'] as JSFunction;
    _yt = clase.callAsConstructor<JSObject>(div.id.toJS, opciones);
    _id = id;
    await listo.future.timeout(const Duration(seconds: 20), onTimeout: () {});
    _llamar('setVolume', [_volumen.round().toJS]);
    _llamar('setPlaybackRate', [_velocidad.toJS]);
  }

  JSAny? _llamar(String metodo, [List<JSAny?> args = const []]) {
    final yt = _yt;
    if (yt == null || !(_listo?.isCompleted ?? false)) return null;
    try {
      return yt.callMethodVarArgs(metodo.toJS, args);
    } catch (_) {
      return null;
    }
  }

  double _numero(String metodo) {
    final r = _llamar(metodo);
    return r != null && r.isA<JSNumber>() ? (r as JSNumber).toDartDouble : 0;
  }

  void _alCambiar(int estado) {
    // -1 sin empezar, 0 terminó, 1 sonando, 2 en pausa, 3 cargando, 5 listo
    final sonando = estado == 1;
    if (_estado.playing != sonando) {
      _estado.playing = sonando;
      _sonando.add(sonando);
    }
    final esperando = estado == 3;
    if (_estado.buffering != esperando) {
      _estado.buffering = esperando;
      _esperando.add(esperando);
    }
    if (sonando) {
      _mostrarme();
      final d = _numero('getDuration');
      if (d > 0) _dur.add(Duration(milliseconds: (d * 1000).round()));
      _reloj ??= Timer.periodic(const Duration(milliseconds: 250), (_) => _tic());
    }
    if (estado == 0) {
      _reloj?.cancel();
      _reloj = null;
      _fin.add(true);
    }
  }

  void _tic() {
    final t = _numero('getCurrentTime');
    final p = Duration(milliseconds: (t * 1000).round());
    _estado.position = p;
    _pos.add(p);
  }

  void _alFallar(int codigo) {
    final texto = switch (codigo) {
      2 => 'Video no válido',
      5 => 'El navegador no puede reproducir este video',
      100 => 'El video ya no existe o es privado',
      101 || 150 => 'El dueño no deja reproducir este video fuera de YouTube',
      _ => 'Error de YouTube ($codigo)',
    };
    _error.add(texto);
  }

  /// Solo se ve el que suena (hay dos motores para las transiciones).
  void _mostrarme() {
    final caja = _caja;
    if (caja == null) return;
    for (var i = 0; i < caja.children.length; i++) {
      (caja.children.item(i) as web.HTMLElement?)?.style.visibility = 'hidden';
    }
    _div?.style.visibility = 'visible';
    caja.style.display = 'block';
  }

  @override
  Future<void> open(Fuente f, {Duration? inicio, bool play = true}) async {
    final id = f.url.startsWith('yt:') ? f.url.substring(3) : '';
    if (id.isEmpty) {
      _error.add('En la web solo suenan canciones de YouTube (no archivos del equipo).');
      return;
    }
    _estado.position = inicio ?? Duration.zero;
    if (_yt == null) {
      await _preparar(id, inicio, play);
      if (!play) _llamar('pauseVideo');
      return;
    }
    final arg = JSObject();
    arg['videoId'] = id.toJS;
    arg['startSeconds'] = ((inicio?.inMilliseconds ?? 0) / 1000).toJS;
    _id = id;
    _llamar(play ? 'loadVideoById' : 'cueVideoById', [arg]);
  }

  @override
  Future<void> play() async => _llamar('playVideo');
  @override
  Future<void> pause() async => _llamar('pauseVideo');
  @override
  Future<void> playOrPause() async => _estado.playing ? pause() : play();
  @override
  Future<void> seek(Duration d) async {
    _estado.position = d;
    _llamar('seekTo', [(d.inMilliseconds / 1000).toJS, true.toJS]);
  }

  @override
  Future<void> setVolume(double v) async {
    _volumen = v.clamp(0, 100).toDouble();
    _llamar('setVolume', [_volumen.round().toJS]);
  }

  @override
  Future<void> setRate(double v) async {
    _velocidad = v;
    _llamar('setPlaybackRate', [v.toJS]);
  }

  @override
  Future<void> stop() async {
    _reloj?.cancel();
    _reloj = null;
    _llamar('stopVideo');
    _id = '';
  }

  @override
  Future<void> dispose() async {
    await stop();
    _llamar('destroy');
    _div?.remove();
    for (final c in [_pos, _dur, _sonando, _esperando, _fin, _error, _log]) {
      await c.close();
    }
  }

  @override
  Future<void> setProperty(String clave, String valor) async {}
  @override
  Future<String?> getProperty(String clave) async => null;
  @override
  Future<void> command(List<String> orden) async {}

  String get idActual => _id;
}

class _EstadoYouTube implements EstadoJugador {
  @override
  Duration position = Duration.zero;
  @override
  bool playing = false;
  @override
  bool buffering = false;
}
