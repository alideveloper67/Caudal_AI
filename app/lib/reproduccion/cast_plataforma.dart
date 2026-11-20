// Cast solo existe en el teléfono (Android e iPhone). En la web no se importa
// nada de dart:io ni del SDK de Google: allí el botón no aparece.
export 'cast_plataforma_io.dart' if (dart.library.js_interop) 'cast_plataforma_web.dart';
