import 'package:caudal/nucleo/fondo_app.dart';
import 'package:caudal/ui/paginas/compartir_letra.dart';
import 'package:caudal/ui/paginas/fondo_pagina.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const _tamanos = <(String, Size, double)>[
  ('telefono chico', Size(320, 568), 2.0),
  ('telefono', Size(412, 915), 2.6),
  ('horizontal', Size(915, 412), 2.6),
  ('tablet', Size(800, 1280), 2.0),
  ('escritorio', Size(1440, 900), 1.0),
];

ThemeData _tema() => temaCaudal().copyWith(splashFactory: InkRipple.splashFactory);

void main() {
  for (final (nombre, tam, dpr) in _tamanos) {
    testWidgets('Fondo de Caudal sin desbordes · $nombre', (t) async {
      t.view.physicalSize = tam * dpr;
      t.view.devicePixelRatio = dpr;
      addTearDown(t.view.reset);
      FondoApp.i.puede = true;
      FondoApp.i.titulo = 'Donador de Caudal';
      FondoApp.i.ruta = '';
      await t.pumpWidget(MaterialApp(theme: _tema(), home: const FondoPagina()));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Fondo de Caudal'), findsOneWidget);
      expect(find.text('Donador de Caudal'), findsOneWidget);
      expect(find.text('Elegir imagen', skipOffstage: false), findsOneWidget);
      expect(t.takeException(), isNull);
      FondoApp.i.puede = false;
    });

    testWidgets('Compartir letra sin desbordes · $nombre', (t) async {
      t.view.physicalSize = tam * dpr;
      t.view.devicePixelRatio = dpr;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(
        theme: _tema(),
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: TextButton(
                onPressed: () => compartirLetra(
                  context,
                  pista: {'titulo': 'Una canción con un título bastante largo para probar', 'artista': 'Artista de prueba', 'miniatura': ''},
                  lineas: ['Primera línea de la letra', 'Segunda línea un poco más larga que la primera', '', 'Tercera línea', 'Cuarta línea final'],
                  color: const Color(0xFF3B82F6),
                ),
                child: const Text('abrir'),
              ),
            ),
          ),
        ),
      ));
      await t.tap(find.text('abrir'));
      await t.pump(const Duration(milliseconds: 500));
      expect(find.text('Compartir letra'), findsOneWidget);
      expect(find.text('Compartir en estados y chats'), findsOneWidget);
      expect(t.takeException(), isNull, reason: 'al abrir la hoja');
      // los estilos y formatos que se alcanzan a ver se prueban; no debe haber desbordes en ninguno
      for (final x in ['Estado', 'Oscuro', 'Claro', 'Historia', 'Cuadrada', 'Vertical', 'Color']) {
        if (find.text(x).evaluate().isEmpty) continue;
        await t.tap(find.text(x), warnIfMissed: false);
        await t.pump(const Duration(milliseconds: 300));
        expect(t.takeException(), isNull, reason: 'al elegir $x');
      }
    });
  }
}
