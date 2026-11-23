// La música propia en la versión web: los archivos que la persona elige quedan
// guardados en su navegador (IndexedDB) y suenan desde ahí, sin internet y con
// la pantalla bloqueada. Fuera de la web no hace nada.
//
// La referencia que se guarda en la colección es `web:<id>`.
export 'archivos_web_io.dart' if (dart.library.js_interop) 'archivos_web_js.dart';
