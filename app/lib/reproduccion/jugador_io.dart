import 'package:media_kit/media_kit.dart';
import 'package:media_kit_video/media_kit_video.dart';

import '../nucleo/streams.dart';
import 'jugador.dart';

bool get esJugadorWeb => false;

Jugador crearJugador() => _JugadorMpv();

void mostrarVideoGrande(bool grande) {}
void ocultarVideo(bool oculto) {}
void colocarVideo(double? x, double? y, double? ancho, double? alto) {}

/// libmpv a través de media_kit (teléfono y PC).
class _JugadorMpv implements Jugador {
  _JugadorMpv()
      : player = Player(configuration: const PlayerConfiguration(
          title: 'Caudal',
          bufferSize: 48 * 1024 * 1024,
          logLevel: MPVLogLevel.warn,
        ));

  final Player player;

  NativePlayer? get _nativo => player.platform is NativePlayer ? player.platform as NativePlayer : null;

  @override
  late final FlujosJugador stream = FlujosJugador(
    position: player.stream.position,
    duration: player.stream.duration,
    playing: player.stream.playing,
    buffering: player.stream.buffering,
    completed: player.stream.completed,
    error: player.stream.error,
    log: player.stream.log,
  );

  @override
  late final EstadoJugador state = _EstadoMpv(player);

  @override
  late final VideoController video = VideoController(player,
      configuration: const VideoControllerConfiguration(enableHardwareAcceleration: true));

  @override
  Future<void> open(Fuente f, {Duration? inicio, bool play = true}) async {
    final aparte = f.audioUrl != null;
    // con el sonido aparte se abre en pausa y se arranca cuando ya estan las
    // dos pistas: si no, el video corre un instante mudo y luego da un salto
    await player.open(Media(f.url, start: inicio), play: play && !aparte);
    if (aparte) {
      await player.setAudioTrack(AudioTrack.uri(f.audioUrl!));
      if (play) await player.play();
    }
  }

  @override
  Future<void> play() => player.play();
  @override
  Future<void> pause() => player.pause();
  @override
  Future<void> playOrPause() => player.playOrPause();
  @override
  Future<void> seek(Duration d) => player.seek(d);
  @override
  Future<void> setVolume(double v) => player.setVolume(v);
  @override
  Future<void> setRate(double v) => player.setRate(v);
  @override
  Future<void> stop() => player.stop();
  @override
  Future<void> dispose() => player.dispose();

  @override
  Future<void> setProperty(String clave, String valor) async => _nativo?.setProperty(clave, valor);
  @override
  Future<String?> getProperty(String clave) async => _nativo?.getProperty(clave);
  @override
  Future<void> command(List<String> orden) async => _nativo?.command(orden);
}

class _EstadoMpv implements EstadoJugador {
  _EstadoMpv(this.p);
  final Player p;
  @override
  Duration get position => p.state.position;
  @override
  bool get playing => p.state.playing;
  @override
  bool get buffering => p.state.buffering;
}
