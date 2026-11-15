// «Tu mes pasado»: lo mas escuchado el mes calendario anterior (o los ultimos
// 30 dias si hay pocos datos).
import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/nucleo/recomendador.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> p(String id) => {
      'tipo': 'pista', 'clave': 'yt:$id', 'video_id': id, 'titulo': 'T$id', 'artista': 'A$id',
      'miniatura': 'm$id', 'duracion': 200,
    };

List<Escucha> veces(String id, DateTime dia, int n) =>
    [for (var i = 0; i < n; i++) Escucha(p(id), dia.add(Duration(minutes: i)))];

void main() {
  final hoy = DateTime(2026, 11, 15, 12);

  test('el mes pasado es el mes calendario anterior, de lo mas oido a lo menos', () {
    final h = [
      ...veces('a', DateTime(2026, 10, 3), 5),
      ...veces('b', DateTime(2026, 10, 9), 9),
      ...veces('c', DateTime(2026, 10, 20), 2),
      ...veces('d', DateTime(2026, 10, 21), 1),
      ...veces('e', DateTime(2026, 10, 30, 23), 1),
      ...veces('f', DateTime(2026, 10, 1, 0, 0), 3),
      // fuera: septiembre y noviembre
      ...veces('x', DateTime(2026, 9, 30, 23), 20),
      ...veces('y', DateTime(2026, 11, 1), 20),
    ];
    final m = Recomendador.mesPasado(h, ahora: hoy)!;
    expect(m['nombre_lista'], 'Lo más escuchado en octubre');
    expect(m['ultimos_30_dias'], isFalse);
    expect(m['tipo'], 'mix');
    expect(m['id'], 'mes_pasado_2026_10');
    final ids = [for (final x in m['pistas'] as List) (x as Map)['video_id']];
    expect(ids.take(3), ['b', 'a', 'f']);
    expect(ids, unorderedEquals(['a', 'b', 'c', 'd', 'e', 'f']));
    expect(ids, isNot(contains('x')));
    expect(ids, isNot(contains('y')));
    expect(m['total'], 6);
    expect((m['miniaturas'] as List).length, 4);
  });

  test('a igualdad de veces, gana la mas reciente', () {
    final h = [
      ...veces('a', DateTime(2026, 10, 2), 2),
      ...veces('b', DateTime(2026, 10, 25), 2),
      ...veces('c', DateTime(2026, 10, 10), 2),
      ...veces('d', DateTime(2026, 10, 11), 2),
      ...veces('e', DateTime(2026, 10, 12), 2),
    ];
    final ids = [for (final x in Recomendador.mesPasado(h, ahora: hoy)!['pistas'] as List) (x as Map)['video_id']];
    expect(ids, ['b', 'e', 'd', 'c', 'a']);
  });

  test('con pocos datos del mes pasado usa los ultimos 30 dias', () {
    final h = [
      // octubre: solo 3 canciones distintas (menos de 5)
      ...veces('a', DateTime(2026, 10, 20), 2),
      ...veces('b', DateTime(2026, 10, 21), 2),
      ...veces('c', DateTime(2026, 10, 22), 2),
      // ultimos 30 dias (desde el 16 de octubre): hay 6
      ...veces('d', DateTime(2026, 11, 2), 4),
      ...veces('e', DateTime(2026, 11, 5), 3),
      ...veces('f', DateTime(2026, 11, 9), 2),
    ];
    final m = Recomendador.mesPasado(h, ahora: hoy)!;
    expect(m['ultimos_30_dias'], isTrue);
    expect(m['nombre_lista'], 'Lo más escuchado en los últimos 30 días');
    expect(m['id'], 'mes_pasado_30d');
    final ids = [for (final x in m['pistas'] as List) (x as Map)['video_id']];
    expect(ids.first, 'd');
    expect(ids, containsAll(['a', 'b', 'c', 'd', 'e', 'f']));
  });

  test('sin datos suficientes en ninguno de los dos, no hay lista', () {
    expect(Recomendador.mesPasado([], ahora: hoy), isNull);
    final poco = [...veces('a', DateTime(2026, 10, 20), 5), ...veces('b', DateTime(2026, 11, 1), 5)];
    expect(Recomendador.mesPasado(poco, ahora: hoy), isNull);
  });

  test('en enero el mes pasado es diciembre del año anterior', () {
    final h = [for (final id in ['a', 'b', 'c', 'd', 'e']) ...veces(id, DateTime(2026, 12, 15), 2)];
    final m = Recomendador.mesPasado(h, ahora: DateTime(2027, 1, 10))!;
    expect(m['nombre_lista'], 'Lo más escuchado en diciembre');
    expect(m['id'], 'mes_pasado_2026_12');
  });

  test('la lista que se guarda lleva como mucho 30 canciones', () {
    final h = [for (var i = 0; i < 45; i++) ...veces('c$i', DateTime(2026, 10, 5), 1 + i % 3)];
    final m = Recomendador.mesPasado(h, ahora: hoy)!;
    expect((m['pistas'] as List).length, 30);
  });

  test('desde cuando leer el historial', () {
    // el 15 de noviembre: 1 de octubre es anterior a hace 30 dias (16 de octubre)
    expect(Recomendador.desdeMesPasado(ahora: hoy), DateTime(2026, 10, 1));
    // el 31 de octubre... el mes pasado empezo el 1 de septiembre y hace 30 dias es el 1 de octubre
    expect(Recomendador.desdeMesPasado(ahora: DateTime(2026, 10, 31)), DateTime(2026, 9, 1));
  });

  test('los nombres de los meses', () {
    expect(Recomendador.nombreDelMes(1), 'enero');
    expect(Recomendador.nombreDelMes(12), 'diciembre');
    expect(Recomendador.nombreDelMes(13), 'diciembre');
  });
}
