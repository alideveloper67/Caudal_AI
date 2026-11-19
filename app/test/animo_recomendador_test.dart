import 'package:caudal/nucleo/recomendador.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('detecta el ánimo por el título', () {
    expect(Rasgos.animoDe('Sin ti - Llorando por dentro'), 'triste');
    expect(Rasgos.animoDe('Adiós'), 'triste');
    expect(Rasgos.animoDe('Fiesta en la playa'), 'fiesta');
    expect(Rasgos.animoDe('Eres mi amor'), 'romantica');
    expect(Rasgos.animoDe('Solomillo con papas'), '');
  });

  test('la tristeza manda sobre el amor', () {
    expect(Rasgos.animoDe('Amor y lágrimas'), 'triste');
  });

  test('una canción triste se parece más a otra triste que a una de fiesta', () {
    final triste = Rasgos.de({'titulo': 'Lloro por ti', 'artista': 'A'});
    final otraTriste = Rasgos.de({'titulo': 'Dolor de adiós', 'artista': 'B'});
    final fiesta = Rasgos.de({'titulo': 'Baila la fiesta', 'artista': 'C'});
    expect(Rasgos.similitud(triste, otraTriste), greaterThan(Rasgos.similitud(triste, fiesta)));
  });
}
