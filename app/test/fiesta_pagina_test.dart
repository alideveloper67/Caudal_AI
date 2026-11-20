import 'package:caudal/nucleo/fiesta.dart';
import 'package:caudal/ui/paginas/fiesta_pagina.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fiesta_test.dart' show BaseFalsa, ReproductorFalso;

void main() {
  tearDown(() => FiestaAnfitrion.activa.value = null);

  testWidgets('crear la fiesta, ver QR, código y cola, quitar y cerrar', (t) async {
    final base = BaseFalsa();
    final rep = ReproductorFalso();
    late FiestaAnfitrion f;
    int? limitePedido;
    await t.pumpWidget(MaterialApp(
      home: FiestaPagina(crear: (nombre, limite) async {
        limitePedido = limite;
        f = await FiestaAnfitrion.crear(control: rep, nombre: nombre, limite: limite, llamar: base.llamar, conTiempoReal: false);
        return f;
      }),
    ));
    expect(find.text('Empezar la fiesta'), findsOneWidget);
    await t.tap(find.text('10'));
    await t.pump();
    await t.runAsync(() async {
      await t.tap(find.text('Empezar la fiesta'));
      await Future<void>.delayed(const Duration(milliseconds: 50));
    });
    await t.pump();
    expect(limitePedido, 10);
    expect(find.byType(QrDibujo), findsOneWidget);
    expect(find.text('ABC 234'), findsOneWidget);
    // la lista es perezosa: la cola vacía está al final, hay que bajar hasta ella
    await t.scrollUntilVisible(find.textContaining('Todavía nadie pidió'), 300,
        scrollable: find.descendant(of: find.byType(ListView), matching: find.byType(Scrollable)).first);
    expect(find.textContaining('Todavía nadie pidió'), findsOneWidget);

    // llegan pedidos (sin carátula para no ir a la red)
    f.fijarAutomatico(false);
    base.pedir('AAAAAAAAAAA', nombre: 'Ana');
    base.pedir('BBBBBBBBBBB', nombre: 'Beto', votos: 2);
    for (final c in base.cola) {
      c['miniatura'] = '';
    }
    await t.runAsync(f.refrescar);
    await t.pump();
    expect(find.text('Canción BBBBBBBBBBB'), findsOneWidget);
    expect(find.textContaining('pedida por Beto · 2 votos'), findsOneWidget);
    final y1 = t.getTopLeft(find.text('Canción BBBBBBBBBBB')).dy;
    final y2 = t.getTopLeft(find.text('Canción AAAAAAAAAAA')).dy;
    expect(y1 < y2, isTrue, reason: 'la más votada arriba');

    await t.runAsync(() async {
      await t.tap(find.byTooltip('Quitar de la cola').first);
      await Future<void>.delayed(const Duration(milliseconds: 50));
    });
    await t.pump();
    expect(find.text('Canción BBBBBBBBBBB'), findsNothing);

    // cerrar con confirmación
    await t.scrollUntilVisible(find.text('Cerrar la fiesta'), 300,
        scrollable: find.descendant(of: find.byType(ListView), matching: find.byType(Scrollable)).first);
    await t.tap(find.text('Cerrar la fiesta'));
    await t.pumpAndSettle();
    await t.runAsync(() async {
      await t.tap(find.widgetWithText(FilledButton, 'Cerrar la fiesta'));
      await Future<void>.delayed(const Duration(milliseconds: 50));
    });
    await t.pumpAndSettle();
    expect(base.abierta, isFalse);
    expect(find.text('Empezar la fiesta'), findsOneWidget, reason: 'vuelve a la pantalla de crear');
  });

  testWidgets('un error al crear se enseña', (t) async {
    await t.pumpWidget(MaterialApp(
      home: FiestaPagina(crear: (_, _) async => throw const ErrorFiesta('Ahora mismo hay demasiadas fiestas nuevas.')),
    ));
    await t.tap(find.text('Empezar la fiesta'));
    await t.pump();
    await t.pump();
    expect(find.text('Ahora mismo hay demasiadas fiestas nuevas.'), findsOneWidget);
  });
}
