import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/nucleo/recomendador.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> p(String vid, String artista, {int dur = 200}) => {
      'tipo': 'pista', 'clave': 'yt:$vid', 'video_id': vid, 'titulo': 'T$vid',
      'artista': artista, 'artistas': [{'nombre': artista, 'id': 'id_$artista'}], 'duracion': dur,
      'miniatura': 'm$vid',
    };

void main() {
  final hoy = DateTime(2026, 11, 14, 12);

  test('combinar premia a la que sale en varias listas', () {
    final r = Recomendador.combinar([
      [p('aaaaaaaaaa1', 'A'), p('bbbbbbbbbb1', 'B')],
      [p('cccccccccc1', 'C'), p('bbbbbbbbbb1', 'B')],
    ]);
    expect(r.first.$1['video_id'], 'bbbbbbbbbb1');
  });

  test('diversificar deja dos por artista y rellena al final', () {
    final l = [for (var i = 0; i < 5; i++) p('a$i', 'A'), p('b0', 'B')];
    final d = Recomendador.diversificar(l, porArtista: 2, largo: 4);
    expect(d.map((x) => x['video_id']), ['a0', 'a1', 'b0', 'a2']);
  });

  group('gusto', () {
    final historial = [
      for (var i = 0; i < 6; i++) Escucha(p('oida0000001', 'Querido'), hoy.subtract(Duration(days: i))),
      Escucha(p('vieja000001', 'Viejo'), hoy.subtract(const Duration(days: 150))),
    ];
    final g = Gusto.desde(historial, {
      'canciones': {'saltada0001': 2},
      'artistas': {'id:id_Odiado': 5},
    }, ahora: hoy);

    test('afinidad: lo reciente pesa más que lo de hace meses', () {
      expect(g.afinidad(p('x', 'Querido')), 1.0);
      expect(g.afinidad(p('x', 'Viejo')), lessThan(0.1));
      expect(g.afinidad(p('x', 'Nadie')), 0.0);
    });

    test('descarta lo que saltas', () {
      expect(g.descartada(p('saltada0001', 'X')), isTrue);
      expect(g.descartada(p('otra0000001', 'Odiado')), isTrue);
      expect(g.descartada(p('otra0000001', 'Querido')), isFalse);
    });

    test('Descubre no repite lo que ya oíste ni lo que saltas', () {
      final cand = Recomendador.combinar([
        [p('oida0000001', 'Querido'), p('nueva000001', 'Nuevo'), p('saltada0001', 'X'),
          p('conocida001', 'Querido'), p('otra0000002', 'Odiado')],
      ]);
      final r = Recomendador.puntuarDescubre(cand, g);
      final ids = r.map((x) => x['video_id']).toList();
      expect(ids, containsAll(['nueva000001', 'conocida001']));
      expect(ids, isNot(contains('oida0000001')));
      expect(ids, isNot(contains('saltada0001')));
      expect(ids, isNot(contains('otra0000002')));
    });

    test('similares quita la propia canción', () {
      final semilla = p('semilla0001', 'A');
      final r = Recomendador.puntuarSimilares(semilla,
          Recomendador.combinar([[semilla, p('parecida001', 'B')]]), g);
      expect(r.map((x) => x['video_id']), ['parecida001']);
    });

    test('la radio no repite lo de estos días si quedan suficientes', () {
      final radio = [p('oida0000001', 'Querido'), for (var i = 0; i < 9; i++) p('r$i', 'R$i')];
      expect(Recomendador.limpiarRadio(radio, g).map((x) => x['video_id']), isNot(contains('oida0000001')));
      expect(Recomendador.limpiarRadio(radio.take(3).toList(), g).length, 3);
    });
  });

  test('semillas: una por artista, las más escuchadas primero', () {
    final h = [
      for (var i = 0; i < 4; i++) Escucha(p('top00000001', 'A'), hoy.subtract(Duration(days: i))),
      for (var i = 0; i < 3; i++) Escucha(p('top00000002', 'A'), hoy.subtract(Duration(days: i))),
      Escucha(p('top00000003', 'B'), hoy),
    ];
    expect(Recomendador.semillas(h, ahora: hoy), ['top00000001', 'top00000003']);
  });

  test('máquina del tiempo: hace un año, con lo que más sonó', () {
    final haceUnAno = hoy.subtract(const Duration(days: 366));
    final h = [
      for (var i = 0; i < 6; i++) Escucha(p('ano0000000$i', 'A'), haceUnAno),
      Escucha(p('ano00000000', 'A'), haceUnAno),
      Escucha(p('hoy00000001', 'B'), hoy),
    ];
    final m = Recomendador.maquinaDelTiempo(h, ahora: hoy);
    expect(m.length, 1);
    expect(m.single['titulo'], 'Hace un año');
    expect((m.single['pistas'] as List).first['video_id'], 'ano00000000');
    expect(m.single['subtitulo'], contains('2025'));
  });
}
