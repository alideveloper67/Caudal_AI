import 'package:caudal/nucleo/importar.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('un nombre de archivo de Snaptube se separa en artista y título', () {
    final c = Importar.cancionDeLinea('Bad Bunny - Monaco (Official Video).mp3')!;
    expect(c.artista, 'Bad Bunny');
    expect(c.titulo, 'Monaco');
  });

  test('quita el número de lista y los guiones bajos', () {
    final c = Importar.cancionDeLinea('12. Karol_G - Tusa')!;
    expect(c.artista, 'Karol G');
    expect(c.titulo, 'Tusa');
  });

  test('sin guion queda solo el título; líneas vacías se ignoran', () {
    expect(Importar.cancionDeLinea('Una canción sola.m4a')!.titulo, 'Una canción sola');
    expect(Importar.cancionDeLinea('   '), isNull);
  });

  test('no hay tope de canciones y se quitan las repetidas', () {
    final lineas = [for (var i = 0; i < 3000; i++) 'Artista $i - Tema $i.mp3', 'Artista 1 - Tema 1.mp3'];
    final l = Importar.deLineas(lineas, titulo: 'Grande');
    expect(l.canciones.length, 3000);
  });

  test('sin canciones legibles avisa', () {
    expect(() => Importar.deLineas(['', ' '], titulo: 'x'), throwsA(isA<ErrorImportar>()));
  });
}
