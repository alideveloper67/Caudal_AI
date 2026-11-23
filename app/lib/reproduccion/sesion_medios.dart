// Los controles de la música en la pantalla bloqueada (versión web) y lo que la
// web sabe del teléfono: si está en reposo y si se puede dejar la pantalla
// encendida. Fuera de la web no hace nada (allí está servicio_audio.dart).
export 'sesion_medios_io.dart' if (dart.library.js_interop) 'sesion_medios_web.dart';
