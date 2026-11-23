import 'package:flutter/widgets.dart';
import 'package:media_kit/media_kit.dart' show PlayerLog;
import 'package:media_kit_video/media_kit_video.dart' show VideoController;

import '../nucleo/streams.dart';
import 'jugador_io.dart' if (dart.library.js_interop) 'jugador_web.dart' as plataforma;

/// Lo que el reproductor necesita de un motor de sonido, sea cual sea.
///
/// * En el teléfono y la PC: libmpv (media_kit), con ecualizador y demás.
/// * En el navegador: el reproductor oficial de YouTube incrustado (lo único que
///   deja sonar canciones de YouTube desde una web) y, para lo que no es de
///   YouTube, el audio del navegador, que sigue con la pantalla bloqueada.
///
/// Los nombres imitan a los de media_kit para que el reproductor no cambie.
abstract class Jugador {
  static Jugador crear() => plataforma.crearJugador();

  /// Un motor aparte del de la música (ambiente, soniditos de la interfaz).
  static Jugador crearAparte() => plataforma.crearJugadorAparte();

  /// ¿Es el reproductor de YouTube del navegador? (sin filtros ni descargas)
  static bool get esWeb => plataforma.esJugadorWeb;

  FlujosJugador get stream;
  EstadoJugador get state;

  Future<void> open(Fuente f, {Duration? inicio, bool play = true});
  Future<void> play();
  Future<void> pause();
  Future<void> playOrPause();
  Future<void> seek(Duration d);
  Future<void> setVolume(double v);
  Future<void> setRate(double v);
  Future<void> stop();
  Future<void> dispose();

  /// Propiedades y órdenes de mpv (filtros, pistas...). En la web no hacen nada.
  Future<void> setProperty(String clave, String valor);
  Future<String?> getProperty(String clave);
  Future<void> command(List<String> orden);

  /// La pantalla del video de mpv (null en la web: allí el video es el de YouTube).
  VideoController? get video;
}

class FlujosJugador {
  FlujosJugador({required this.position, required this.duration, required this.playing,
      required this.buffering, required this.completed, required this.error, required this.log});
  final Stream<Duration> position;
  final Stream<Duration> duration;
  final Stream<bool> playing;
  final Stream<bool> buffering;
  final Stream<bool> completed;
  final Stream<String> error;
  final Stream<PlayerLog> log;
}

abstract class EstadoJugador {
  Duration get position;
  bool get playing;
  bool get buffering;
}

/// El espectro de lo que suena en la web (visualizador). Null donde no se puede medir.
abstract class EspectroWeb {
  static void medir(bool si) => plataforma.medirEspectro(si);
  static (List<int>, double)? leer() => plataforma.leerEspectro();
}

/// Dónde se ve el video de YouTube en la web (el reproductor lo coloca).
abstract class LienzoVideoWeb {
  static void mostrarGrande(bool grande) => plataforma.mostrarVideoGrande(grande);
  static void ocultar(bool oculto) => plataforma.ocultarVideo(oculto);

  /// Encima de [r] (coordenadas de la ventana), o a la esquina con null.
  static void colocar(Rect? r) =>
      plataforma.colocarVideo(r?.left, r?.top, r?.width, r?.height);
}

/// Para que el analizador no se queje de un import sin usar en io.
// ignore: unused_element
Widget _nada() => const SizedBox.shrink();
