import 'package:caudal/coche/atajos_caudal.dart';
import 'package:caudal/ui/paginas/segundo_plano_hoja.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('el enlace a la app lo entiende la app, con signos raros', () {
    for (final (titulo, artista) in [('Día & Noche #1; fin', 'Ñandú'), ('100% real?', 'A/B+C')]) {
      final e = enlaceAppCaudal({'titulo': titulo, 'artista': artista});
      final partes = e.split('#Intent;');
      expect(partes, hasLength(2));
      expect(partes[1], startsWith('scheme=caudal;package=com.kevinrr.caudal;'));
      expect(partes[1], endsWith(';end'));
      // lo que recibe Android: el mismo enlace con el esquema caudal
      final llega = partes[0].replaceFirst('intent://', 'caudal://');
      expect(leerAtajo(llega), AtajoCaudal(TipoAtajo.sonar, texto: '$titulo $artista'));
      expect(Uri.parse(e).toString(), e);
    }
  });

  test('YouTube Music sigue desde donde iba', () {
    expect(enlaceYouTubeMusic('abc', Duration.zero), 'https://music.youtube.com/watch?v=abc');
    expect(enlaceYouTubeMusic('abc', const Duration(seconds: 73)), 'https://music.youtube.com/watch?v=abc&t=73');
  });
}
