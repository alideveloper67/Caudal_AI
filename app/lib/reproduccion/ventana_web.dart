// Lo que solo hay en el navegador: pantalla completa y la ventanita del mini
// reproductor (siempre encima). Fuera de la web no hace nada.
export 'ventana_web_io.dart' if (dart.library.js_interop) 'ventana_web_js.dart';
