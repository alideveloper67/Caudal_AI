// La presentación «Somos 100»: se monta, se recorre hasta la última diapositiva
// sin excepciones (en un teléfono y en uno pequeño), muestra su texto clave y la
// decisión de cuándo salir (debeMostrar) es la del guion.
import 'package:caudal/ui/novedades/presentacion_100.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _montar(WidgetTester t, Size tamano) async {
  t.view.physicalSize = tamano * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(theme: temaCaudal(), home: const Presentacion100()));
  await t.pump(const Duration(milliseconds: 100));
}

/// Deja correr la animación del paso de página: el reloj del test necesita varios bombeos pequeños.
Future<void> _esperaPagina(WidgetTester t) async {
  for (var k = 0; k < 25; k++) {
    await t.pump(const Duration(milliseconds: 100));
  }
}

void main() {
  test('debeMostrar: solo con 100 o más y si aún no se vio', () {
    expect(debeMostrar(99, false), isFalse);
    expect(debeMostrar(null, false), isFalse);
    expect(debeMostrar(100, true), isFalse);
    expect(debeMostrar(100, false), isTrue);
    expect(debeMostrar(250, false), isTrue);
  });

  testWidgets('se recorre hasta la última diapositiva sin excepciones (teléfono)', (t) async {
    await _montar(t, const Size(390, 844));

    // diapositiva 1: el contador llega a 100 y sale la explosión
    expect(find.text('Somos 100'), findsOneWidget);
    await t.pump(const Duration(milliseconds: 2500));
    expect(find.text('100'), findsOneWidget);
    expect(t.takeException(), isNull);

    const titulos = {
      1: 'Escenarios vivos',
      2: 'Letras que se cantan contigo',
      3: 'Escuchen juntos',
      4: 'Música que te conoce',
      5: 'Tus mascotas',
      6: 'Modo gamer',
      7: 'Modo estudio',
    };
    for (var i = 0; i < 12; i++) {
      await t.tap(find.text('Siguiente'));
      await _esperaPagina(t);
      expect(t.takeException(), isNull);
      final titulo = titulos[i];
      if (titulo != null) expect(find.text(titulo), findsWidgets, reason: 'diapositiva ${i + 2}');
      if (i == 8) {
        // diapositiva 3: «Todo lo que Caudal te ofrece»
        expect(find.text('Todo lo que Caudal te ofrece'), findsOneWidget);
        expect(find.text('Escucha'), findsOneWidget);
      }
    }

    // diapositiva 13: enlace y botones
    expect(find.text('caudal-musica.netlify.app'), findsOneWidget);
    expect(find.text('Copiar enlace'), findsOneWidget);
    expect(find.text('Compartir Caudal'), findsOneWidget);
    expect(find.text('Seguir escuchando'), findsOneWidget);
    expect(find.text('Siguiente'), findsNothing);
    expect(t.takeException(), isNull);

    await t.pumpWidget(const SizedBox());
  });

  testWidgets('se recorre también en una pantalla pequeña sin desbordes', (t) async {
    await _montar(t, const Size(320, 568));

    for (var i = 0; i < 12; i++) {
      await _esperaPagina(t);
      expect(t.takeException(), isNull);
      await t.tap(find.text('Siguiente'));
    }
    await _esperaPagina(t);
    expect(find.text('caudal-musica.netlify.app'), findsOneWidget);
    expect(t.takeException(), isNull);

    await t.pumpWidget(const SizedBox());
  });
}
