// El motor de respaldo de Android: ExoPlayer (el reproductor del sistema) a través de just_audio,
// con la misma cara que el de mpv ([Jugador]) para que el reproductor no note la diferencia.
//
// Solo sonido: sin ecualizador, sin filtros ni video (setProperty/command no hacen nada y [video]
// es null). A cambio no carga ninguna de nuestras librerías nativas (mpv, ffmpeg): si en un
// teléfono esas tumban la app, con este la música sigue. Lo elige motor_eleccion.dart.

import 'dart:async';

import 'package:just_audio/just_audio.dart';
import 'package:media_kit/media_kit.dart' show PlayerLog;
import 'package:media_kit_video/media_kit_video.dart' show VideoController;

import '../nucleo/streams.dart';
import 'jugador.dart';

class JugadorExo implements Jugador {
  JugadorExo() {
    // los errores de ExoPlayer (red, formato) llegan por aquí, como los de mpv
    _eventos = p.playbackEventStream.listen((_) {}, onError: (Object e, StackTrace _) => _error.add(_texto(e)));
  }

  /// El foco de audio, los auriculares y las llamadas los lleva ServicioAudio (como con mpv).
  final AudioPlayer p = AudioPlayer(handleInterruptions: false, handleAudioSessionActivation: false);

  final _error = StreamController<String>.broadcast();
  late final StreamSubscription<PlaybackEvent> _eventos;
  bool _cerrado = false;

  static String _texto(Object e) {
    if (e is PlayerException) return 'exoplayer ${e.code}: ${e.message ?? ''}';
    if (e is PlayerInterruptedException) return 'exoplayer interrumpido: ${e.message ?? ''}';
    return 'exoplayer: $e';
  }

  @override
  late final FlujosJugador stream = FlujosJugador(
    position: p.positionStream,
    duration: p.durationStream.where((d) => d != null).map((d) => d!),
    playing: p.playingStream,
    buffering: p.processingStateStream
        .map((s) => s == ProcessingState.loading || s == ProcessingState.buffering)
        .distinct(),
    completed: p.processingStateStream.map((s) => s == ProcessingState.completed).distinct(),
    error: _error.stream,
    log: const Stream<PlayerLog>.empty(),
  );

  @override
  late final EstadoJugador state = _EstadoExo(p);

  @override
  Future<void> open(Fuente f, {Duration? inicio, bool play = true}) async {
    if (_cerrado) return;
    // un video con el sonido aparte: aquí solo se oye, se abre la pista de sonido
    final url = f.audioUrl ?? f.url;
    final uri = f.local ? Uri.file(f.archivo) : Uri.parse(url);
    try {
      await p.setAudioSource(AudioSource.uri(uri), initialPosition: inicio, preload: true);
      // play() de just_audio termina cuando se para: no se espera
      if (play) unawaited(p.play().catchError((Object e) => _error.add(_texto(e))));
    } catch (e) {
      // el enlace no abrió: al reproductor como un error del motor (lo resuelve el freno)
      if (e is! PlayerInterruptedException) _error.add(_texto(e));
    }
  }

  @override
  Future<void> play() async {
    unawaited(p.play().catchError((Object e) => _error.add(_texto(e))));
  }

  @override
  Future<void> pause() => p.pause();

  @override
  Future<void> playOrPause() => p.playing ? pause() : play();

  @override
  Future<void> seek(Duration d) => p.seek(d);

  /// mpv va de 0 a 100 (y más con «Volumen máximo»); ExoPlayer de 0 a 1.
  @override
  Future<void> setVolume(double v) => p.setVolume((v / 100).clamp(0.0, 1.0));

  @override
  Future<void> setRate(double v) => p.setSpeed(v.clamp(0.25, 3.0));

  @override
  Future<void> stop() => p.stop();

  @override
  Future<void> dispose() async {
    if (_cerrado) return;
    _cerrado = true;
    await _eventos.cancel();
    await p.dispose();
    await _error.close();
  }

  // sin filtros ni propiedades de mpv
  @override
  Future<void> setProperty(String clave, String valor) async {}
  @override
  Future<String?> getProperty(String clave) async => null;
  @override
  Future<void> command(List<String> orden) async {}

  @override
  VideoController? get video => null;
}

class _EstadoExo implements EstadoJugador {
  _EstadoExo(this.p);
  final AudioPlayer p;
  @override
  Duration get position => p.position;
  @override
  bool get playing => p.playing;
  @override
  bool get buffering =>
      p.processingState == ProcessingState.loading || p.processingState == ProcessingState.buffering;
}
