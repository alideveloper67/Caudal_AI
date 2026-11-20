import 'cast_tipos.dart';

PuenteCast crearPuenteCast() => PuenteNulo();
ServidorCast crearServidorCast() => ServidorNulo();

String tipoPorExtension(String ruta) {
  final e = ruta.split('.').last.toLowerCase();
  return switch (e) {
    'mp3' => 'audio/mpeg',
    'webm' => 'audio/webm',
    'flac' => 'audio/flac',
    _ => 'audio/mp4',
  };
}
