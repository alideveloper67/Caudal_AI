import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/nucleo/premium_letras.dart';
import 'package:caudal/nucleo/resumen_anual.dart';
import 'package:caudal/ui/paginas/resumen_anual_pagina.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Escucha _e(String titulo, String artista, DateTime f, {int dur = 200, String clave = ''}) => Escucha({
      'clave': clave.isEmpty ? 'yt:$titulo' : clave,
      'video_id': 'v$titulo',
      'titulo': titulo,
      'artista': artista,
      'artistas': [
        {'id': 'id_$artista', 'nombre': artista}
      ],
      'duracion': dur,
      'miniatura': '',
    }, f);

void main() {
  group('ResumenAnual.calcular', () {
    test('un historial vacío da un resumen vacío', () {
      final r = ResumenAnual.calcular(const [], anio: 2026);
      expect(r.vacio, isTrue);
      expect(r.suficiente, isFalse);
      expect(r.minutos, 0);
      expect(r.cancionTop, isNull);
    });

    test('solo cuenta las escuchas del año pedido', () {
      final h = [
        _e('Vieja', 'A', DateTime(2025, 12, 31, 23)),
        _e('Nueva', 'B', DateTime(2026, 1, 1, 8)),
        _e('Nueva', 'B', DateTime(2026, 1, 2, 8)),
      ];
      final r = ResumenAnual.calcular(h, anio: 2026);
      expect(r.escuchas, 2);
      expect(r.cancionTop!.nombre, 'Nueva');
      expect(ResumenAnual.calcular(h, anio: 2025).escuchas, 1);
      // un año distinto del actual
      expect(ResumenAnual.calcular(h, anio: 2024).vacio, isTrue);
    });

    test('canción y artista más oídos, minutos y top 5', () {
      final h = <Escucha>[];
      var dia = 1;
      // A: 6 veces de "Uno"; B: 4; C: 3; D: 2; E: 2; F: 1
      void poner(String art, String tit, int veces) {
        for (var i = 0; i < veces; i++) {
          h.add(_e(tit, art, DateTime(2026, 3, dia, 10 + (i % 8))));
        }
        dia++;
      }

      poner('A', 'Uno', 6);
      poner('B', 'Dos', 4);
      poner('C', 'Tres', 3);
      poner('D', 'Cuatro', 2);
      poner('E', 'Cinco', 2);
      poner('F', 'Seis', 1);
      final r = ResumenAnual.calcular(h, anio: 2026);
      expect(r.escuchas, 18);
      expect(r.minutos, (18 * 200 / 60).round());
      expect(r.cancionTop!.nombre, 'Uno');
      expect(r.cancionTop!.escuchas, 6);
      expect(r.artistaTop!.nombre, 'A');
      expect(r.topArtistas.map((a) => a.nombre).toList(), ['A', 'B', 'C', 'D', 'E']);
      expect(r.artistasDistintos, 6);
      expect(r.cancionesDistintas, 6);
    });

    test('racha más larga y día de más escucha', () {
      final h = [
        // 3 días seguidos (1, 2, 3 de abril) y luego 2 (10, 11)
        for (final d in [1, 2, 3, 10, 11]) _e('T$d', 'A', DateTime(2026, 4, d, 9)),
        // el 2 de abril suena mucho más
        for (var i = 0; i < 5; i++) _e('Extra$i', 'A', DateTime(2026, 4, 2, 12 + i)),
      ];
      final r = ResumenAnual.calcular(h, anio: 2026);
      expect(r.rachaMasLarga, 3);
      expect(r.diasConMusica, 5);
      expect(r.diaTop, DateTime(2026, 4, 2));
      expect(r.minutosDiaTop, (6 * 200 / 60).round());
    });

    test('el cambio de mes o de año no parte la racha', () {
      final h = [
        _e('a', 'A', DateTime(2026, 1, 30, 23, 50)),
        _e('b', 'A', DateTime(2026, 1, 31, 0, 10)),
        _e('c', 'A', DateTime(2026, 2, 1, 7)),
        _e('d', 'A', DateTime(2026, 2, 2, 7)),
      ];
      expect(ResumenAnual.calcular(h, anio: 2026).rachaMasLarga, 4);
    });

    test('el ánimo dominante sale de los títulos', () {
      final h = [
        for (var i = 0; i < 8; i++) _e('Llorando por ti $i', 'A', DateTime(2026, 5, 1 + i, 20)),
        for (var i = 0; i < 2; i++) _e('Fiesta total $i', 'B', DateTime(2026, 5, 20 + i, 20)),
        _e('Sin pista', 'C', DateTime(2026, 5, 25, 20)),
      ];
      final r = ResumenAnual.calcular(h, anio: 2026);
      expect(r.animoDominante, 'triste');
      expect(r.animoPorcentaje, 80);
      expect(r.animoTexto, 'melancólico');
      expect(r.animos['fiesta'], 2);
    });

    test('con muy pocos títulos con ánimo no se dice nada', () {
      final h = [for (var i = 0; i < 4; i++) _e('Tema $i', 'A', DateTime(2026, 5, 1 + i)), _e('Adiós', 'A', DateTime(2026, 5, 9))];
      expect(ResumenAnual.calcular(h, anio: 2026).animoDominante, '');
    });

    test('«suficiente» pide escuchas y días distintos', () {
      final pocas = [for (var i = 0; i < 25; i++) _e('T', 'A', DateTime(2026, 6, 1, 8 + i % 10))];
      expect(ResumenAnual.calcular(pocas, anio: 2026).suficiente, isFalse); // un solo día
      final bien = [for (var i = 0; i < 25; i++) _e('T$i', 'A', DateTime(2026, 6, 1 + i % 5, 9))];
      expect(ResumenAnual.calcular(bien, anio: 2026).suficiente, isTrue);
    });
  });

  group('temporada', () {
    test('diciembre y la primera quincena de enero', () {
      expect(esTemporadaDelResumen(DateTime(2026, 12, 1)), isTrue);
      expect(esTemporadaDelResumen(DateTime(2027, 1, 15)), isTrue);
      expect(esTemporadaDelResumen(DateTime(2027, 1, 16)), isFalse);
      expect(esTemporadaDelResumen(DateTime(2026, 7, 4)), isFalse);
    });

    test('en enero todavía se resume el año que acaba de terminar', () {
      expect(anioDelResumen(DateTime(2027, 1, 5)), 2026);
      expect(anioDelResumen(DateTime(2027, 1, 16)), 2027);
      expect(anioDelResumen(DateTime(2026, 12, 20)), 2026);
    });
  });

  group('pantalla', () {
    const tamanos = <(String, Size, double)>[
      ('telefono chico 320x568', Size(320, 568), 2.0),
      ('telefono 360x640', Size(360, 640), 2.0),
      ('escritorio 1440x900', Size(1440, 900), 1.0),
    ];
    final ahora = DateTime(2026, 12, 10);
    final historial = [
      for (var i = 0; i < 40; i++)
        _e(i % 3 == 0 ? 'Llorando $i' : 'Tema $i', 'Artista ${i % 6}', DateTime(2026, 3, 1 + i % 20, 9 + i % 10)),
    ];

    tearDown(() => esPremiumLetras = () => false);

    for (final (nombre, tam, dpr) in tamanos) {
      testWidgets('donador: las 5 tarjetas sin desbordes · $nombre', (t) async {
        esPremiumLetras = () => true;
        t.view.physicalSize = tam * dpr;
        t.view.devicePixelRatio = dpr;
        addTearDown(t.view.reset);
        await t.pumpWidget(MaterialApp(theme: temaCaudal(), home: ResumenAnualPagina(historial: historial, ahora: ahora)));
        await t.pump(const Duration(milliseconds: 300));
        expect(find.text('Compartir'), findsOneWidget);
        expect(find.text('Guardar'), findsOneWidget);
        for (var i = 0; i < 5; i++) {
          expect(t.takeException(), isNull, reason: 'tarjeta ${i + 1}');
          await t.fling(find.byType(PageView), const Offset(-400, 0), 2000);
          await t.pump(const Duration(milliseconds: 500));
        }
        expect(t.takeException(), isNull);
      });
    }

    testWidgets('quien no dona ve la vista previa con candado y sin botón de compartir', (t) async {
      esPremiumLetras = () => false;
      t.view.physicalSize = const Size(360, 640) * 2;
      t.view.devicePixelRatio = 2;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(theme: temaCaudal(), home: ResumenAnualPagina(historial: historial, ahora: ahora)));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Donar aquí'), findsOneWidget);
      expect(find.text('Compartir'), findsNothing);
      expect(t.takeException(), isNull);
    });

    testWidgets('con pocas escuchas un donador ve un mensaje amable', (t) async {
      esPremiumLetras = () => true;
      t.view.physicalSize = const Size(360, 640) * 2;
      t.view.devicePixelRatio = 2;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(
          theme: temaCaudal(),
          home: ResumenAnualPagina(historial: [_e('Una', 'A', DateTime(2026, 5, 5))], ahora: ahora)));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Todavía es pronto para tu resumen'), findsOneWidget);
      expect(find.text('Compartir'), findsNothing);
      expect(t.takeException(), isNull);
    });

    testWidgets('sin ninguna escucha también se explica', (t) async {
      esPremiumLetras = () => true;
      await t.pumpWidget(MaterialApp(theme: temaCaudal(), home: ResumenAnualPagina(historial: const [], ahora: ahora)));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Todavía es pronto para tu resumen'), findsOneWidget);
    });
  });
}
