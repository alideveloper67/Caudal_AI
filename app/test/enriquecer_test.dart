// Pruebas de «Enriquecer» una lista: semillas, orden y filtros, limite de
// peticiones y fallos de red. Sin red ni base: las peticiones son falsas.

import 'dart:async';

import 'package:caudal/nucleo/enriquecer.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> pista(String titulo, String artista, {int duracion = 180, bool video = false}) {
  final vid = 'v${titulo.hashCode.toRadixString(16)}'.padRight(11, 'x').substring(0, 11);
  return {
    'tipo': 'pista',
    'clave': 'yt:$vid',
    'video_id': vid,
    'titulo': titulo,
    'artistas': [
      {'nombre': artista, 'id': 'UC$artista'}
    ],
    'artista': artista,
    'duracion': duracion,
    'es_video': video,
    'miniatura': 'https://img/$vid.jpg',
  };
}

void main() {
  // A suena 3 veces, B 2, C 1
  final lista = [
    pista('a1', 'A'), pista('a2', 'A'), pista('a3', 'A'),
    pista('b1', 'B'), pista('b2', 'B'),
    pista('c1', 'C'),
  ];

  group('semillas', () {
    test('toma los artistas mas frecuentes y una cancion de cada uno', () {
      final s = Enriquecer.semillas(lista);
      expect(s.artistas.map((a) => a.nombre).toList(), ['A', 'B', 'C']);
      expect(s.pesos['id:UCA'], 1.0);
      expect(s.pesos['id:UCB'], closeTo(2 / 3, 1e-9));
      // la primera ronda: a1, b1, c1; luego completa con otras de la lista
      expect(s.videoIds.take(3).toList(),
          [lista[0]['video_id'], lista[3]['video_id'], lista[5]['video_id']]);
      expect(s.videoIds.length, 5);
      expect(s.videoIds.toSet().length, 5);
    });

    test('es estable y no revienta con listas pequenas o vacias', () {
      expect(Enriquecer.semillas(lista).videoIds, Enriquecer.semillas(lista).videoIds);
      final una = Enriquecer.semillas([pista('x', 'X')]);
      expect(una.videoIds.length, 1);
      final vacia = Enriquecer.semillas([]);
      expect(vacia.videoIds, isEmpty);
      expect(vacia.artistas, isEmpty);
    });
  });

  group('ordenar', () {
    final sem = Enriquecer.semillas(lista);

    test('quita lo que ya esta en la lista, repetidas, videos y sesiones largas', () {
      final fuentes = [
        [
          lista[0], // ya esta
          pista('nueva', 'N'),
          pista('nueva', 'N'), // repetida dentro de la misma fuente
          pista('video', 'V', video: true),
          pista('sesion', 'S', duracion: 3600),
          {...pista('sin id', 'Q'), 'video_id': ''},
        ],
      ];
      final r = Enriquecer.ordenar(lista, fuentes, sem);
      expect(r.map((e) => e.pista['titulo']).toList(), ['nueva']);
    });

    test('una version con otro id de una cancion que ya tienes tambien se quita', () {
      final otra = {...pista('a1', 'A'), 'video_id': 'otroIdDistin', 'clave': 'yt:otroIdDistin'};
      final r = Enriquecer.ordenar(lista, [[otra]], sem);
      expect(r, isEmpty);
    });

    test('las que se repiten entre fuentes van primero', () {
      final comun = pista('comun', 'Z');
      final fuentes = [
        [pista('solo1', 'P'), pista('solo2', 'Q'), comun],
        [pista('solo3', 'R'), comun],
      ];
      final r = Enriquecer.ordenar(lista, fuentes, sem);
      expect(r.first.pista['titulo'], 'comun');
      expect(r.first.fuentes, 2);
      expect(r.length, 4);
    });

    test('mezcla parecidas y de artistas de la lista, alternadas', () {
      final fuentes = [
        [for (var i = 0; i < 4; i++) pista('otra$i', 'X$i')],
        [for (var i = 0; i < 4; i++) pista('delA$i', i < 2 ? 'A' : 'B')],
      ];
      final r = Enriquecer.ordenar(lista, fuentes, sem);
      expect(r.length, 8);
      final patron = r.take(6).map((e) => e.propio).toList();
      expect(patron, [false, true, false, true, false, true]);
    });

    test('ningun artista domina: tope por artista, con relleno si falta', () {
      final muchas = [for (var i = 0; i < 10; i++) pista('b-$i', 'B')];
      final otras = [for (var i = 0; i < 3; i++) pista('o$i', 'O$i')];
      final r = Enriquecer.ordenar(lista, [muchas, otras], sem, limite: 8);
      final deB = r.where((e) => e.pista['artista'] == 'B').length;
      expect(r.length, 8);
      expect(deB, 5); // 4 con tope + 1 de relleno al faltar otras
      // con suficientes otras, B no pasa del tope
      final masOtras = [for (var i = 0; i < 12; i++) pista('p$i', 'P$i')];
      final r2 = Enriquecer.ordenar(lista, [muchas, masOtras], sem, limite: 12);
      expect(r2.where((e) => e.pista['artista'] == 'B').length, Enriquecer.maxPorArtista);
    });

    test('respeta el limite y es determinista', () {
      final fuentes = [
        [for (var i = 0; i < 80; i++) pista('t$i', 'T${i % 30}')],
      ];
      final r = Enriquecer.ordenar(lista, fuentes, sem);
      expect(r.length, Enriquecer.topeFinal);
      expect(Enriquecer.ordenar(lista, fuentes, sem).map((e) => e.videoId).toList(),
          r.map((e) => e.videoId).toList());
      expect(r.map((e) => e.videoId).toSet().length, r.length);
    });

    test('sin fuentes o sin candidatas devuelve vacio', () {
      expect(Enriquecer.ordenar(lista, [], sem), isEmpty);
      expect(Enriquecer.ordenar([], [[]], Enriquecer.semillas([])), isEmpty);
    });
  });

  group('peticiones', () {
    test('correrConLimite nunca pasa de 3 a la vez y las hace todas', () async {
      var activas = 0, maximo = 0, hechas = 0;
      final tareas = [
        for (var i = 0; i < 10; i++)
          () async {
            activas++;
            if (activas > maximo) maximo = activas;
            await Future<void>.delayed(const Duration(milliseconds: 5));
            activas--;
            hechas++;
          }
      ];
      await Enriquecer.correrConLimite(tareas, 3);
      expect(hechas, 10);
      expect(maximo, 3);
    });

    test('sugerir: pide radios y artistas, avisa del progreso y ordena', () async {
      final pedidas = <String>[];
      var activas = 0, maximo = 0;
      final avances = <int>[];
      Future<List<Map<String, dynamic>>> radio(String v) async {
        pedidas.add('r:$v');
        activas++;
        if (activas > maximo) maximo = activas;
        await Future<void>.delayed(const Duration(milliseconds: 3));
        activas--;
        return [pista('comun', 'Z'), pista('r$v', 'R$v')];
      }

      Future<List<Map<String, dynamic>>> artista(String n, String c) async {
        pedidas.add('a:$n');
        return [pista('comun', 'Z'), pista('de$n', n)];
      }

      final r = await Enriquecer.sugerir(lista,
          radio: radio, delArtista: artista, progreso: (h, t) => avances.add(h));
      expect(pedidas.where((x) => x.startsWith('r:')).length, 5);
      expect(pedidas.where((x) => x.startsWith('a:')).toList(), ['a:A', 'a:B', 'a:C']);
      expect(maximo, lessThanOrEqualTo(Enriquecer.concurrencia));
      expect(avances.first, 0);
      expect(avances.last, 8);
      expect(r.first.pista['titulo'], 'comun');
      expect(r.first.fuentes, 8);
    });

    test('si solo fallan algunas peticiones, sigue con lo que llego', () async {
      var n = 0;
      final r = await Enriquecer.sugerir(lista,
          radio: (v) async {
            if (n++ == 0) throw Exception('Socket');
            return [pista('ok$n', 'O$n')];
          },
          delArtista: (a, c) async => <Map<String, dynamic>>[]);
      expect(r, isNotEmpty);
    });

    test('si todo falla por red lanza EnriquecerError (reintentable)', () async {
      expect(
        () => Enriquecer.sugerir(lista,
            radio: (v) async => throw Exception('Socket'),
            delArtista: (a, c) async => throw Exception('Socket')),
        throwsA(isA<EnriquecerError>()),
      );
    });

    test('una peticion colgada se corta por tiempo', () async {
      final r = Enriquecer.sugerir(lista,
          radio: (v) => Completer<List<Map<String, dynamic>>>().future,
          delArtista: (a, c) => Completer<List<Map<String, dynamic>>>().future,
          espera: const Duration(milliseconds: 20));
      await expectLater(r, throwsA(isA<EnriquecerError>()));
    });

    test('cancelar detiene las peticiones y devuelve vacio', () async {
      var pidio = 0;
      var cancelar = false;
      final r = await Enriquecer.sugerir(lista,
          radio: (v) async {
            pidio++;
            cancelar = true;
            return [pista('x$pidio', 'X')];
          },
          delArtista: (a, c) async => [pista('y', 'Y')],
          cancelado: () => cancelar);
      expect(r, isEmpty);
      expect(pidio, lessThanOrEqualTo(Enriquecer.concurrencia));
    });

    test('lista vacia: nada que pedir', () async {
      expect(await Enriquecer.sugerir([], radio: (v) async => throw Exception('no')), isEmpty);
    });
  });
}
