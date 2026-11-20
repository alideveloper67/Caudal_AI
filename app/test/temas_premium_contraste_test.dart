// Contraste de los 19 temas premium: el texto principal de la app sobre el fondo de cada tema
// (WCAG AA, 4,5) y el acento sobre la capa de superficie (3, para elementos no textuales).
import 'package:caudal/ui/premium/temas_premium.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('hay 19 temas premium (6 de siempre y 13 nuevos)', () {
    expect(TemasPremium.lista, hasLength(19));
    expect(TemasPremium.lista.map((t) => t.clave).toSet(), hasLength(19));
  });

  for (final t in TemasPremium.lista) {
    test('${t.nombre}: texto principal legible sobre el fondo (AA 4,5)', () {
      final razon = TemasPremium.contraste(C.texto, t.capas[0]);
      expect(razon, greaterThanOrEqualTo(4.5), reason: '${t.clave}: ${razon.toStringAsFixed(2)}');
    });

    test('${t.nombre}: acento visible sobre la superficie (3)', () {
      final razon = TemasPremium.contraste(t.acento, t.capas[2]);
      expect(razon, greaterThanOrEqualTo(3.0), reason: '${t.clave}: ${razon.toStringAsFixed(2)}');
    });
  }
}
