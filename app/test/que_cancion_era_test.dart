import 'package:caudal/nucleo/letras_cache.dart';
import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/nucleo/premium.dart';
import 'package:flutter_test/flutter_test.dart';

// «hoy» en las pruebas: jueves 19 de noviembre de 2026
final _hoy = DateTime(2026, 11, 19, 15);

Escucha _e(String titulo, String artista, DateTime f, {String? album}) => Escucha({
      'clave': 'yt:$titulo',
      'video_id': 'v$titulo',
      'titulo': titulo,
      'artista': artista,
      'artistas': [
        {'id': 'id_$artista', 'nombre': artista}
      ],
      if (album != null) 'album': {'nombre': album},
      'duracion': 200,
    }, f);

void main() {
  group('interpretar fechas', () {
    DateTime d(int m, int dia) => DateTime(2026, m, dia);

    test('ayer, anteayer y hoy', () {
      var q = QueCancionEra.interpretar('ayer', ahora: _hoy);
      expect((q.desde, q.hasta), (d(11, 18), d(11, 19)));
      q = QueCancionEra.interpretar('la de anteayer', ahora: _hoy);
      expect(q.desde, d(11, 17));
      q = QueCancionEra.interpretar('hoy', ahora: _hoy);
      expect((q.desde, q.hasta), (d(11, 19), d(11, 20)));
      expect(q.terminos, isEmpty);
    });

    test('«el martes» es el último martes; si hoy es martes, el de la semana pasada', () {
      var q = QueCancionEra.interpretar('la canción que escuché el martes', ahora: _hoy);
      expect(q.desde, d(11, 17));
      expect(q.etiqueta, contains('martes'));
      expect(q.terminos, isEmpty, reason: 'las palabras de relleno no cuentan');
      // hoy es jueves: «el jueves» es el de hace una semana, no hoy
      q = QueCancionEra.interpretar('el jueves', ahora: _hoy);
      expect(q.desde, d(11, 12));
      q = QueCancionEra.interpretar('el sábado pasado', ahora: _hoy);
      expect(q.desde, d(11, 14));
      q = QueCancionEra.interpretar('el miércoles', ahora: _hoy);
      expect(q.desde, d(11, 18));
    });

    test('hace N días, semanas y meses', () {
      expect(QueCancionEra.interpretar('hace 3 días', ahora: _hoy).desde, d(11, 16));
      expect(QueCancionEra.interpretar('hace tres dias', ahora: _hoy).desde, d(11, 16));
      final s = QueCancionEra.interpretar('hace dos semanas', ahora: _hoy);
      expect(s.desde!.isBefore(d(11, 5)) && s.hasta!.isAfter(d(11, 5)), isTrue);
      final m = QueCancionEra.interpretar('hace un mes', ahora: _hoy);
      expect(m.desde!.isBefore(d(10, 19)) && m.hasta!.isAfter(d(10, 19)), isTrue);
    });

    test('semana pasada, esta semana y mes pasado', () {
      var q = QueCancionEra.interpretar('la semana pasada', ahora: _hoy);
      expect((q.desde, q.hasta), (d(11, 9), d(11, 16)));
      q = QueCancionEra.interpretar('esta semana', ahora: _hoy);
      expect((q.desde, q.hasta), (d(11, 16), d(11, 20)));
      q = QueCancionEra.interpretar('el mes pasado', ahora: _hoy);
      expect((q.desde, q.hasta), (d(10, 1), d(11, 1)));
    });

    test('rangos y fechas con mes', () {
      var q = QueCancionEra.interpretar('del 3 al 5 de noviembre', ahora: _hoy);
      expect((q.desde, q.hasta), (d(11, 3), d(11, 6)));
      q = QueCancionEra.interpretar('entre el 10 y el 12 de octubre', ahora: _hoy);
      expect((q.desde, q.hasta), (d(10, 10), d(10, 13)));
      q = QueCancionEra.interpretar('el 12 de octubre', ahora: _hoy);
      expect((q.desde, q.hasta), (d(10, 12), d(10, 13)));
      // un día que todavía no llega este año es del año pasado
      q = QueCancionEra.interpretar('el 25 de diciembre', ahora: _hoy);
      expect(q.desde, DateTime(2025, 12, 25));
      // el 31 de febrero no existe: no inventa una fecha
      expect(QueCancionEra.interpretar('el 31 de febrero', ahora: _hoy).tieneFecha, isFalse);
      q = QueCancionEra.interpretar('en octubre', ahora: _hoy);
      expect((q.desde, q.hasta), (d(10, 1), d(11, 1)));
      q = QueCancionEra.interpretar('en diciembre', ahora: _hoy);
      expect(q.desde, DateTime(2025, 12, 1));
    });

    test('franjas del día', () {
      var q = QueCancionEra.interpretar('el martes por la noche', ahora: _hoy);
      expect(q.franja, 2);
      expect(q.desde, d(11, 17));
      q = QueCancionEra.interpretar('anoche', ahora: _hoy);
      expect((q.desde, q.franja), (d(11, 18), 2));
      q = QueCancionEra.interpretar('ayer en la mañana', ahora: _hoy);
      expect(q.franja, 0);
    });

    test('texto, comillas y letra', () {
      var q = QueCancionEra.interpretar('Rosalía ayer', ahora: _hoy);
      expect(q.terminos, ['rosalia']);
      q = QueCancionEra.interpretar('una que decía quiero bailar contigo', ahora: _hoy);
      expect(q.frase, 'quiero bailar contigo');
      expect(q.terminos, isEmpty);
      q = QueCancionEra.interpretar('el martes "ojos de cielo"', ahora: _hoy);
      expect(q.frase, 'ojos de cielo');
      expect(q.tieneFecha, isTrue);
      expect(QueCancionEra.interpretar('   ', ahora: _hoy).sinCriterios, isTrue);
    });
  });

  group('buscar', () {
    final historial = [
      _e('Corazón Partío', 'Alejandro Sanz', DateTime(2026, 11, 17, 21), album: 'Más'),
      _e('Corazón Partío', 'Alejandro Sanz', DateTime(2026, 11, 17, 22)),
      _e('Despechá', 'Rosalía', DateTime(2026, 11, 17, 9)),
      _e('Bzrp Session 53', 'Shakira', DateTime(2026, 11, 18, 18)),
      _e('Vieja canción', 'Alguien', DateTime(2026, 5, 2, 12)),
      _e('Despechá', 'Rosalía', DateTime(2026, 11, 19, 8)),
    ];

    test('por fecha: lo del martes, agrupado y contado', () {
      final r = QueCancionEra.buscar(historial, 'el martes', ahora: _hoy);
      expect(r.resultados.map((h) => h.pista['titulo']).toSet(), {'Corazón Partío', 'Despechá'});
      final cp = r.resultados.firstWhere((h) => h.pista['titulo'] == 'Corazón Partío');
      expect(cp.veces, 2);
      expect(cp.ultima, DateTime(2026, 11, 17, 22));
      // lo más reciente primero
      expect(r.resultados.first.pista['titulo'], 'Corazón Partío');
    });

    test('por franja del día', () {
      final r = QueCancionEra.buscar(historial, 'el martes por la mañana', ahora: _hoy);
      expect(r.resultados.map((h) => h.pista['titulo']), ['Despechá']);
    });

    test('por texto: sin tildes ni mayúsculas, en título, artista y álbum', () {
      expect(QueCancionEra.buscar(historial, 'corazon', ahora: _hoy).resultados.single.donde, 'titulo');
      expect(QueCancionEra.buscar(historial, 'rosalia', ahora: _hoy).resultados.single.donde, 'artista');
      expect(QueCancionEra.buscar(historial, 'alejandro', ahora: _hoy).resultados.single.donde, 'artista');
      expect(QueCancionEra.buscar(historial, 'mas', ahora: _hoy).resultados, isNotEmpty);
    });

    test('fecha + texto se combinan; fuera del rango no sale', () {
      final r = QueCancionEra.buscar(historial, 'ayer shakira', ahora: _hoy);
      expect(r.resultados.single.pista['titulo'], 'Bzrp Session 53');
      expect(QueCancionEra.buscar(historial, 'ayer rosalia', ahora: _hoy).resultados, isEmpty);
      expect(QueCancionEra.buscar(historial, 'vieja canción en mayo', ahora: _hoy).resultados.single.pista['titulo'],
          'Vieja canción');
    });

    test('por letra, solo si está en la caché local', () {
      final letras = {
        'yt:Despechá': {
          'lineas': [
            [1000, 'Quiero bailar contigo'],
            [4000, 'Toda la noche'],
          ],
          'texto': 'Quiero bailar contigo\nToda la noche',
        },
      };
      var r = QueCancionEra.buscar(historial, 'decía quiero bailar contigo', ahora: _hoy, letras: letras);
      expect(r.resultados.single.pista['titulo'], 'Despechá');
      expect(r.resultados.single.donde, 'letra');
      expect(r.resultados.single.fragmento, 'Quiero bailar contigo');
      // sin la letra guardada no aparece (no se inventa)
      r = QueCancionEra.buscar(historial, 'decía quiero bailar contigo', ahora: _hoy);
      expect(r.resultados, isEmpty);
      // las palabras sueltas también pueden estar en la letra
      r = QueCancionEra.buscar(historial, 'toda noche', ahora: _hoy, letras: letras);
      expect(r.resultados.single.donde, 'letra');
      // y con fecha
      r = QueCancionEra.buscar(historial, 'el martes decía "bailar contigo"', ahora: _hoy, letras: letras);
      expect(r.resultados.single.pista['titulo'], 'Despechá');
    });

    test('un título gana a una letra; sin criterios no devuelve nada', () {
      final letras = {
        'yt:Despechá': {'lineas': const [], 'texto': 'el corazon late'}
      };
      final r = QueCancionEra.buscar(historial, 'corazon', ahora: _hoy, letras: letras);
      expect(r.resultados.first.pista['titulo'], 'Corazón Partío');
      expect(r.resultados.map((h) => h.donde), ['titulo', 'letra']);
      expect(QueCancionEra.buscar(historial, '', ahora: _hoy).resultados, isEmpty);
    });

    test('con un historial grande es rápido', () {
      final grande = [
        for (var i = 0; i < 40000; i++) _e('Tema ${i % 900}', 'Artista ${i % 50}', DateTime(2026, 1 + i % 11, 1 + i % 27, i % 24)),
      ];
      final t = Stopwatch()..start();
      final r = QueCancionEra.buscar(grande, 'el martes tema 7', ahora: _hoy);
      t.stop();
      expect(r.resultados.length, lessThanOrEqualTo(40));
      expect(t.elapsedMilliseconds, lessThan(1500));
    });
  });

  group('LetrasCache', () {
    test('guarda lo compacto, ignora las vacías y tiene tope', () {
      final c = LetrasCache.prueba();
      c.guardar('a', {'lineas': const [], 'texto': ''});
      expect(c.cuantas, 0);
      c.guardar('a', {
        'lineas': [
          [0, 'hola'],
          [1000, 'mundo']
        ],
        'fuente': 'x',
        'sincronizada': true,
      });
      expect(c.de('a')!.containsKey('fuente'), isFalse);
      expect(lineasConTiempo(c.de('a')).length, 2);
      expect(c.de('a')!['texto'], 'hola\nmundo');
      for (var i = 0; i < LetrasCache.tope + 20; i++) {
        c.guardar('k$i', {'texto': 'letra $i'});
      }
      expect(c.cuantas, LetrasCache.tope);
      expect(c.de('a'), isNull, reason: 'la más antigua salió');
    });

    test('obtener usa la caché y pide una sola vez', () async {
      final c = LetrasCache.prueba();
      var pedidas = 0;
      c.cargador = (p) async {
        pedidas++;
        return {'texto': 'hola', 'lineas': const []};
      };
      final p = {'clave': 'z', 'titulo': 'Z'};
      final r = await Future.wait([c.obtener(p), c.obtener(p)]);
      expect(r.every((x) => x != null), isTrue);
      await c.obtener(p);
      expect(pedidas, 1);
      expect(await c.obtener({'clave': 'otra'}, red: false), isNull);
      // un fallo de red no rompe ni deja nada guardado
      c.cargador = (p) async => throw Exception('sin red');
      expect(await c.obtener({'clave': 'w'}), isNull);
      expect(c.de('w'), isNull);
    });
  });
}
