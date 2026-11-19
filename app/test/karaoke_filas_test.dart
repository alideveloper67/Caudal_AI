import 'package:caudal/ui/reproductor/linea_karaoke.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('rellenoPorFila: las filas de una línea larga se llenan una tras otra', () {
    test('al empezar no hay nada cantado', () {
      expect(rellenoPorFila([100, 100, 50], 0), [0, 0, 0]);
    });

    test('a la mitad la primera ya está llena y la segunda va por la cuarta parte', () {
      final r = rellenoPorFila([100, 100, 50], 0.5);
      expect(r[0], 1.0);
      expect(r[1], closeTo(0.25, 1e-9));
      expect(r[2], 0.0);
    });

    test('nunca avanzan dos filas a la vez', () {
      for (var i = 0; i <= 100; i++) {
        final r = rellenoPorFila([120, 90, 60], i / 100);
        final abiertas = r.where((x) => x > 0 && x < 1).length;
        expect(abiertas <= 1, isTrue, reason: 'avance $i %: $r');
        // si una fila va a medias, las anteriores están llenas y las siguientes vacías
        final k = r.indexWhere((x) => x < 1);
        if (k >= 0) {
          for (var j = k + 1; j < r.length; j++) {
            expect(r[j], 0.0, reason: 'avance $i %: $r');
          }
        }
      }
    });

    test('al terminar todo está cantado', () {
      expect(rellenoPorFila([100, 100, 50], 1), [1, 1, 1]);
      expect(rellenoPorFila([100, 100, 50], 1.7), [1, 1, 1]);
    });

    test('una sola fila funciona como el barrido de siempre', () {
      expect(rellenoPorFila([200], 0.25), [0.25]);
    });

    test('sin filas o con filas vacías no falla', () {
      expect(rellenoPorFila([], 0.5), isEmpty);
      expect(rellenoPorFila([0, 0], 0.5), [0, 0]);
    });
  });
}
