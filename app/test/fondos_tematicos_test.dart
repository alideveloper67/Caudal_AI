import 'dart:io';

import 'package:caudal/ui/fondo_capa.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Fondos con personaje: los mismos 19 que el escritorio, con su mosaico y su acento.
void main() {
  const personajes = {
    'hellokitty', 'kuromi', 'pikachu', 'charmander', 'squirtle', 'bulbasaur', 'snoopy', 'totoro',
    'mymelody', 'purin', 'cinnamoroll', 'kirby', 'doraemon', 'olaf', 'nyan', 'gato_negro', 'capibara', 'pochacco', 'nailong',
  };

  test('están los 19 con 6 capas oscuras y su mosaico', () {
    expect(Aspecto.temas.keys.toSet(), personajes);
    for (final e in Aspecto.temas.entries) {
      expect(e.value.$3.length, 6, reason: e.key);
      expect(e.value.$3.first.computeLuminance(), lessThanOrEqualTo(0.04), reason: e.key);
      expect(File(Aspecto.patronDe(e.key)!).existsSync(), isTrue, reason: e.key);
    }
    // los de siempre siguen y no traen mosaico
    for (final k in ['oscuro', 'negro', 'noche', 'uva', 'bosque', 'grafito']) {
      expect(Aspecto.fondos.containsKey(k), isTrue);
      expect(Aspecto.patronDe(k), isNull);
    }
  });

  test('las capas son las mismas que en el escritorio', () {
    final py = File('../escritorio/descargador/ui/estilos.py').readAsStringSync();
    for (final e in Aspecto.temas.entries) {
      final linea = py.split('\n').firstWhere((l) => l.trimLeft().startsWith('"${e.key}": ("'));
      expect(linea, contains(Aspecto.hexDe(e.value.$2)), reason: '${e.key}: acento');
      expect(linea, contains(Aspecto.hexDe(e.value.$3.first)), reason: '${e.key}: fondo');
    }
  });

  test('aplicar un tema pinta la app con sus colores y enciende el mosaico', () {
    Aspecto.aplicar('#FF77B7', 'kuromi');
    expect(C.fondo, Aspecto.temas['kuromi']!.$3.first);
    expect(Aspecto.patron, 'assets/fondos/kuromi.png');
    expect(C.hayFondo, isTrue);
    Aspecto.aplicar('cian', 'oscuro');
    expect(Aspecto.patron, isNull);
    expect(C.hayFondo, isFalse);
  });

  testWidgets('el personaje se agranda manteniéndolo pulsado y deslizando', (t) async {
    Aspecto.aplicar('#FF77B7', 'kuromi');
    double? guardado;
    await t.pumpWidget(MaterialApp(
      home: Scaffold(
        body: SizedBox(
          width: 412,
          height: 915,
          child: Stack(children: [
            Positioned.fill(child: PersonajeEncima(alto: 160, alCambiar: (v) => guardado = v)),
          ]),
        ),
      ),
    ));
    await t.pump();
    final personaje = find.byType(PersonajeFondo);
    expect(personaje, findsOneWidget);
    expect(t.widget<PersonajeFondo>(personaje).alto, 160);
    // un toque normal no lo cambia (pasa a lo de debajo)
    await t.tap(personaje, warnIfMissed: false);
    await t.pump();
    expect(find.textContaining('Pellizca'), findsNothing);
    // mantener pulsado: entra a cambiar el tamaño
    await t.longPress(personaje);
    await t.pump();
    expect(find.textContaining('Pellizca'), findsOneWidget);
    await t.dragFrom(const Offset(200, 500), const Offset(0, -60));
    await t.pump();
    expect(t.widget<PersonajeFondo>(personaje).alto, greaterThan(160));
    expect(guardado, isNotNull);
    // tocar fuera: termina y lo recuerda
    await t.tapAt(const Offset(40, 80));
    await t.pump();
    expect(find.textContaining('Pellizca'), findsNothing);
    expect(t.takeException(), isNull);
    Aspecto.aplicar('cian', 'oscuro');
  });
}