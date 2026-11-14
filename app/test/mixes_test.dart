// Pruebas de "Tus mixes diarios" y "Tu resumen". Todo sin red ni base: se
// arma un historial a mano y la radio es una funcion falsa.

import 'dart:math';

import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/ui/paginas/resumen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Pista con la forma comun; el video_id tiene 11 caracteres como los reales.
Map<String, dynamic> pista(String titulo, String artista, {String? id, int duracion = 180, String? con}) {
  final vid = 'v${titulo.hashCode.toRadixString(16)}'.padRight(11, 'x').substring(0, 11);
  return {
    'tipo': 'pista',
    'clave': 'yt:$vid',
    'video_id': vid,
    'titulo': titulo,
    'artistas': [
      {'nombre': artista, 'id': id ?? 'UC$artista'},
      if (con != null) {'nombre': con, 'id': 'UC$con'},
    ],
    'artista': con == null ? artista : '$artista, $con',
    'duracion': duracion,
    'miniatura': 'https://img/$vid.jpg',
  };
}

Map<String, dynamic> radioDe(String semilla, int n) => {
      'pistas': [for (var i = 0; i < n; i++) pista('R$semilla$i', 'Radio$semilla${i % 3}')]
    };

void main() {
  final ahora = DateTime(2026, 11, 13, 23, 30);

  // Dos "estilos": reggaeton (A, B, C) por las noches y rock (X, Y) por las
  // mananas, nunca en la misma sesion. Mas un artista suelto (Z).
  List<Escucha> historial() {
    final salida = <Escucha>[];
    final regg = [pista('ra1', 'A'), pista('ra2', 'A'), pista('rb1', 'B'), pista('rc1', 'C')];
    final rock = [pista('xx1', 'X'), pista('xx2', 'X'), pista('yy1', 'Y')];
    final suelto = pista('zz1', 'Z');
    for (var d = 0; d < 20; d++) {
      final noche = DateTime(2026, 11, 13 - d, 22);
      for (final (i, p) in regg.indexed) {
        salida.add(Escucha(p, noche.add(Duration(minutes: 4 * i)),
            contexto: {'tipo': 'genero', 'id': 'g1', 'titulo': 'Reggaetón'}));
      }
      final manana = DateTime(2026, 11, 13 - d, 8);
      for (final (i, p) in rock.indexed) {
        salida.add(Escucha(p, manana.add(Duration(minutes: 4 * i))));
      }
      if (d % 5 == 0) salida.add(Escucha(suelto, DateTime(2026, 11, 13 - d, 15)));
    }
    return salida;
  }

  group('mixes: agrupar', () {
    test('junta a quien escuchas en la misma sesion y separa lo distinto', () {
      final grupos = Mixes.agrupar(historial(), ahora: ahora);
      expect(grupos.length, greaterThanOrEqualTo(3));
      expect(grupos.length, lessThanOrEqualTo(6));
      Set<String> de(String a) => grupos.firstWhere((g) => g.artistas.contains('id:UC$a')).artistas.toSet();
      expect(de('A').containsAll(['id:UCB', 'id:UCC']), isTrue, reason: 'el reggaeton va junto');
      expect(de('X').contains('id:UCY'), isTrue, reason: 'el rock va junto');
      expect(de('A').contains('id:UCX'), isFalse, reason: 'reggaeton y rock no se mezclan');
      // el de mas peso primero
      expect(grupos.first.artistas.first, 'id:UCA');
      // la mas escuchada del grupo, primero
      expect(grupos.first.pistas.first['titulo'], anyOf('ra1', 'ra2'));
    });

    test('el estilo sale del genero desde el que sonaba', () {
      final grupos = Mixes.agrupar(historial(), ahora: ahora);
      final regg = grupos.firstWhere((g) => g.artistas.contains('id:UCA'));
      final rock = grupos.firstWhere((g) => g.artistas.contains('id:UCX'));
      expect(regg.estilo, 'Reggaetón');
      expect(rock.estilo, isNull);
      expect(Mixes.nombreMix(0, regg.estilo), 'Mix de Reggaetón');
      expect(Mixes.nombreMix(1, null), 'Mix diario 2');
    });

    test('con poco historial igual salen tres mixes', () {
      final h = [
        for (var i = 0; i < 6; i++) ...[
          Escucha(pista('p1', 'A'), ahora.subtract(Duration(hours: i * 24, minutes: 9))),
          Escucha(pista('p2', 'B'), ahora.subtract(Duration(hours: i * 24, minutes: 6))),
          Escucha(pista('p3', 'C'), ahora.subtract(Duration(hours: i * 24, minutes: 3))),
        ]
      ];
      expect(Mixes.agrupar(h, ahora: ahora).length, 3);
    });

    test('respeta el maximo y no falla sin historial', () {
      expect(Mixes.agrupar([], ahora: ahora), isEmpty);
      final muchos = [
        for (var i = 0; i < 12; i++)
          Escucha(pista('s$i', 'Art$i'), ahora.subtract(Duration(days: i * 2)))
      ];
      expect(Mixes.agrupar(muchos, ahora: ahora, maximo: 4).length, lessThanOrEqualTo(4));
    });

    test('artistas sin id: se agrupan por nombre', () {
      final p = {
        'tipo': 'pista', 'clave': 'local:3', 'video_id': '', 'titulo': 'Mia',
        'artista': 'Ana & Beto', 'duracion': 200,
      };
      expect(artistasDe(p).map((a) => a.nombre), ['Ana', 'Beto']);
      expect(artistasDe(p).first.clave, 'n:ana');
    });
  });

  group('mixes: mezclar', () {
    test('una tuya y dos nuevas, sin repetir y con el largo pedido', () {
      final mias = [for (var i = 0; i < 10; i++) pista('m$i', 'A')];
      final radio = [
        [...mias.take(3), for (var i = 0; i < 30; i++) pista('n$i', 'B')],
        [for (var i = 0; i < 30; i++) pista('o$i', 'C')],
      ];
      final r = Mixes.mezclar(mias, radio, largo: 30, azar: Random(1));
      expect(r.length, 30);
      expect(r.map((p) => p['video_id']).toSet().length, 30, reason: 'sin repetidas');
      final ids = {for (final p in mias) p['video_id']};
      for (var i = 0; i < r.length; i++) {
        expect(ids.contains(r[i]['video_id']), i % 3 == 0, reason: 'posicion $i');
      }
      // las dos radios se turnan
      expect(r[1]['artista'], isNot(r[2]['artista']));
    });

    test('sin radio quedan solo las tuyas', () {
      final mias = [for (var i = 0; i < 5; i++) pista('m$i', 'A')];
      final r = Mixes.mezclar(mias, [], azar: Random(2));
      expect(r.length, 5);
      expect(r.map((p) => p['video_id']).toSet(), {for (final p in mias) p['video_id']});
    });

    test('las semillas son de artistas distintos', () {
      final g = Mixes.agrupar(historial(), ahora: ahora).first;
      final s = Mixes.semillas(g);
      expect(s.length, 2);
      expect(s.every((v) => v.length == 11), isTrue);
    });
  });

  group('mixes: construir', () {
    test('arma elementos de tipo mix con radio, portada y sin repetir entre mixes', () async {
      final pedidas = <String>[];
      final mixes = await Mixes.construir(historial(), ahora: ahora, radio: (vid) async {
        pedidas.add(vid);
        return [for (final e in radioDe(vid, 25)['pistas'] as List) Map<String, dynamic>.from(e as Map)];
      });
      expect(mixes.length, inInclusiveRange(3, 6));
      expect(pedidas.toSet().length, pedidas.length, reason: 'cada semilla se pide una vez');
      final todas = <String>{};
      for (final m in mixes) {
        expect(m['tipo'], 'mix');
        expect('${m['id']}', startsWith('mix_diario_'));
        expect('${m['titulo']}', isNotEmpty);
        expect('${m['subtitulo']}', endsWith('y más'));
        expect(m['con_radio'], isTrue);
        expect((m['miniaturas'] as List), isNotEmpty);
        expect(m['miniatura'], (m['miniaturas'] as List).first);
        final pistas = (m['pistas'] as List).cast<Map>();
        expect(pistas, isNotEmpty);
        for (final p in pistas) {
          expect(todas.add('${p['video_id']}'), isTrue, reason: '${p['titulo']} esta en dos mixes');
        }
      }
      final regg = mixes.firstWhere((m) => (m['artistas'] as List).contains('A'));
      expect(regg['titulo'], 'Mix de Reggaetón');
      expect((regg['pistas'] as List).length, 50);
      expect((regg['miniaturas'] as List).length, 4);
    });

    test('sin internet salen igual, solo con tus canciones', () async {
      final mixes = await Mixes.construir(historial(), ahora: ahora,
          radio: (_) async => throw Exception('sin red'));
      expect(mixes, isNotEmpty);
      for (final m in mixes) {
        expect(m['con_radio'], isFalse);
        expect((m['pistas'] as List), isNotEmpty);
      }
    });

    test('el mismo dia da el mismo orden', () async {
      Future<List<String>> orden() async => [
            for (final p in (await Mixes.construir(historial(), ahora: ahora,
                    radio: (v) async => [
                          for (final e in radioDe(v, 20)['pistas'] as List) Map<String, dynamic>.from(e as Map)
                        ]))
                .first['pistas'] as List)
              '${(p as Map)['video_id']}'
          ];
      expect(await orden(), await orden());
    });
  });

  group('resumen', () {
    test('minutos, tops y hora pico de la semana', () {
      final r = Resumen.calcular(historial(), PeriodoResumen.semana, ahora: ahora);
      // 7 dias x (4 + 3) pistas de 3 min, mas Z el dia 0 y el 5
      expect(r.escuchas, 7 * 7 + 2);
      expect(r.minutos, (7 * 7 + 2) * 3);
      expect(r.topArtistas.first.nombre, 'A');
      expect(r.topArtistas.first.minutos, 7 * 2 * 3);
      expect(r.topCanciones.length, 5);
      expect(r.cancionesDistintas, 8);
      expect(r.artistasDistintos, 6);
      expect(r.horaPico, 22);
      expect(r.franja, 'noche');
      expect(r.porHora[8], 7 * 3 * 3);
      expect(r.porDia.length, 7);
      expect(r.diasConMusica, 7);
    });

    test('rachas, cancion del mes y comparacion con el periodo anterior', () {
      final r = Resumen.calcular(historial(), PeriodoResumen.semana, ahora: ahora);
      expect(r.rachaActual, 20);
      expect(r.rachaMasLarga, 7);
      expect(r.nombreMes, 'noviembre');
      expect(r.cancionDelMes, isNotNull);
      expect(r.cancionDelMes!.veces, 13); // del 1 al 13 de noviembre
      // la semana anterior: lo mismo, pero con una sola escucha de Z
      expect(r.minutosAntes, 7 * 7 * 3 + 3);
      expect(r.cambio, isNotNull);
    });

    test('la racha de hoy cuenta desde ayer si hoy aun no escuchaste', () {
      final h = [
        for (var d = 1; d <= 4; d++) Escucha(pista('q1', 'A'), DateTime(2026, 11, 13 - d, 12)),
        Escucha(pista('q1', 'A'), DateTime(2026, 11, 3, 12)),
      ];
      final r = Resumen.calcular(h, PeriodoResumen.mes, ahora: ahora);
      expect(r.rachaActual, 4);
      expect(r.rachaMasLarga, 4);
      expect(r.porDia.length, 30);
      expect(r.porDia.last, 0, reason: 'hoy no hubo musica');
      expect(r.porDia[r.porDia.length - 2], 3);
    });

    test('descubrimientos: artistas que no habias escuchado antes', () {
      final h = [
        Escucha(pista('v1', 'Viejo'), DateTime(2026, 9, 1, 10)),
        Escucha(pista('v1', 'Viejo'), DateTime(2026, 11, 12, 10)),
        Escucha(pista('n1', 'Nuevo'), DateTime(2026, 11, 12, 11)),
        Escucha(pista('n1', 'Nuevo'), DateTime(2026, 11, 13, 11)),
      ];
      final r = Resumen.calcular(h, PeriodoResumen.semana, ahora: ahora);
      expect(r.descubrimientos.map((a) => a.nombre), ['Nuevo']);
      expect(r.minutosAntes, 0);
      expect(r.cambio, isNull);
    });

    test('duraciones raras: sin duracion cuenta 3:30, un video de una hora cuenta 15 min', () {
      final h = [
        Escucha(pista('d0', 'A', duracion: 0), ahora.subtract(const Duration(hours: 1))),
        Escucha(pista('d1', 'A', duracion: 3600), ahora.subtract(const Duration(hours: 2))),
      ];
      final r = Resumen.calcular(h, PeriodoResumen.semana, ahora: ahora);
      expect(r.segundos, 210 + 900);
    });

    test('vacio sin escuchas y el año abarca 365 dias', () {
      final r = Resumen.calcular([], PeriodoResumen.anio, ahora: ahora);
      expect(r.vacio, isTrue);
      expect(r.porDia.length, 365);
      expect(r.cancionDelMes, isNull);
      expect(r.rachaActual, 0);
      final lejos = Resumen.calcular(
          [Escucha(pista('a1', 'A'), DateTime(2025, 11, 20))], PeriodoResumen.anio, ahora: ahora);
      expect(lejos.escuchas, 1);
      expect(Resumen.calcular(
              [Escucha(pista('a1', 'A'), DateTime(2025, 11, 10))], PeriodoResumen.anio, ahora: ahora)
          .escuchas, 0);
    });

    test('los invitados suman escuchas pero los minutos son del principal', () {
      final h = [Escucha(pista('f1', 'A', con: 'B'), ahora.subtract(const Duration(hours: 1)))];
      final r = Resumen.calcular(h, PeriodoResumen.semana, ahora: ahora);
      final b = r.topArtistas.firstWhere((a) => a.nombre == 'B');
      expect(b.veces, 1);
      expect(b.minutos, 0);
      expect(r.topArtistas.first.nombre, 'A');
      expect(r.topArtistas.first.id, 'UCA');
    });
  });

  group('resumen: pantalla', () {
    // sin portadas de internet: la prueba no toca la red
    // y llevado a hoy: la pantalla calcula con el reloj de verdad
    List<Escucha> sinFotos() {
      final hoy = DateTime.now();
      final corrimiento = DateTime(hoy.year, hoy.month, hoy.day).difference(DateTime(2026, 11, 13));
      return [
        for (final e in historial())
          if (e.fecha.add(corrimiento).isBefore(hoy))
            Escucha({...e.pista, 'miniatura': ''}, e.fecha.add(corrimiento), contexto: e.contexto)
      ];
    }

    for (final periodo in PeriodoResumen.values) {
      testWidgets('se recorren todas las historias (${periodo.etiqueta}) sin errores', (t) async {
        await t.binding.setSurfaceSize(const Size(360, 740));
        addTearDown(() => t.binding.setSurfaceSize(null));
        await t.pumpWidget(MaterialApp(home: ResumenPagina(periodo: periodo, historial: sinFotos())));
        await t.pump();
        await t.pump(const Duration(milliseconds: 1600));
        expect(find.text('Tu resumen'), findsOneWidget);
        for (var i = 0; i < 12; i++) {
          await t.tapAt(const Offset(300, 380));
          await t.pump();
          await t.pump(const Duration(milliseconds: 1600));
        }
        // al final, la tarjeta para compartir
        expect(find.text('en Caudal'), findsOneWidget);
        expect(find.text('Compartir'), findsOneWidget);
      });
    }

    testWidgets('sin escuchas muestra la historia vacia', (t) async {
      await t.pumpWidget(const MaterialApp(home: ResumenPagina(historial: [])));
      await t.pump();
      await t.pump(const Duration(milliseconds: 1600));
      expect(find.text('Tu resumen está por escribirse'), findsOneWidget);
    });

    testWidgets('portada de mix en mosaico', (t) async {
      final mix = {
        'tipo': 'mix', 'id': 'mix_diario_1', 'titulo': 'Mix diario 1', 'subtitulo': 'A, B y más',
        'miniaturas': ['', '', '', ''], 'color': Mixes.colores[1], 'pistas': [],
      };
      await t.pumpWidget(MaterialApp(home: Scaffold(body: Center(child: PortadaMix(mix: mix)))));
      expect(find.text('Mix diario 1'), findsOneWidget);
    });
  });
}
