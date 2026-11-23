import 'dart:typed_data';

/// Fuera del navegador no existe: las canciones son archivos de verdad.
class ArchivosWeb {
  ArchivosWeb._();

  static bool esRef(String ref) => ref.startsWith('web:');
  static Future<String> guardar(Uint8List bytes, {String tipo = 'audio/mpeg', Uint8List? portada}) =>
      throw UnsupportedError('Solo en el navegador');
  static Future<String?> url(String ref) async => null;
  static Future<void> borrar(String ref) async {}
  static Future<Map<String, Uint8List>> portadas() async => const {};
  static Future<double> duracion(Uint8List bytes, String tipo) async => 0;
  static Future<Uint8List?> reducirPortada(Uint8List bytes) async => null;
  static Future<bool> pedirPermanencia() async => false;
  static Future<(int, int)> espacio() async => (0, 0);
  static String urlTemporal(Uint8List bytes, String tipo) => '';
  static void soltarTemporal(String url) {}
}
