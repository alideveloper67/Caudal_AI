import 'package:caudal/ui/paginas/aspecto_pagina.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // La hoja de "Tu color" no cabe entera en pantallas bajas: lo de arriba se
  // desplaza y los botones Cancelar / Usar este quedan siempre a la vista.
  for (final alto in [520.0, 700.0, 900.0]) {
    testWidgets('Usar este se ve y se pulsa con $alto de alto', (t) async {
      t.view.physicalSize = Size(411 * 2.625, alto * 2.625);
      t.view.devicePixelRatio = 2.625;
      addTearDown(t.view.reset);
      Color? elegido;
      await t.pumpWidget(MaterialApp(
        home: Builder(
          builder: (c) => Scaffold(
            body: Center(
              child: TextButton(
                onPressed: () async {
                  elegido = await showModalBottomSheet<Color>(
                    context: c,
                    useRootNavigator: true,
                    isScrollControlled: true,
                    useSafeArea: true,
                    showDragHandle: true,
                    builder: (_) => const SelectorColor(inicial: Color(0xFF40C4FF), fondo: false),
                  );
                },
                child: const Text('abrir'),
              ),
            ),
          ),
        ),
      ));
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle();
      expect(testerSinExcepciones(t), isNull);
      final boton = find.text('Usar este');
      expect(boton, findsOneWidget);
      final y = t.getCenter(boton).dy;
      expect(y, lessThan(alto), reason: 'el boton queda dentro de la pantalla');
      await t.tap(boton);
      await t.pumpAndSettle();
      expect(elegido, isNotNull);
    });
  }
}

Object? testerSinExcepciones(WidgetTester t) => t.takeException();
