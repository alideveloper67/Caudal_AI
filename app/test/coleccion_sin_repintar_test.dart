import 'package:caudal/ui/paginas/coleccion_pagina.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> _lista(List<int> ids, {String titulo = 'Viaje', String mini = ''}) => {
      'titulo': titulo, 'descripcion': '', 'miniatura': mini,
      'pistas': [for (final i in ids) {'clave': 'yt:$i', 'titulo': 'Canción $i'}],
    };

void main() {
  test('lo mismo: no se rehace la pantalla', () {
    expect(mismaColeccion(_lista([1, 2, 3]), _lista([1, 2, 3])), isTrue);
  });
  test('una canción añadida, quitada o movida: sí', () {
    expect(mismaColeccion(_lista([1, 2]), _lista([1, 2, 3])), isFalse);
    expect(mismaColeccion(_lista([1, 2, 3]), _lista([1, 3])), isFalse);
    expect(mismaColeccion(_lista([1, 2, 3]), _lista([2, 1, 3])), isFalse);
  });
  test('otro nombre o portada: sí', () {
    expect(mismaColeccion(_lista([1]), _lista([1], titulo: 'Otra')), isFalse);
    expect(mismaColeccion(_lista([1]), _lista([1], mini: 'https://x/1.jpg')), isFalse);
  });
}
