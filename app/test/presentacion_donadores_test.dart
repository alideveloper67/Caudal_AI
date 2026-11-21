// La presentación «Gracias, donador»: se monta, se recorre hasta la última diapositiva
// sin excepciones (en un teléfono y en uno pequeño) y muestra sus textos clave. La decisión
// de cuándo salir (debeMostrarDonador) es la del guion.
import 'package:caudal/ui/novedades/presentacion_donadores.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _montar(WidgetTester t, Size tamano) async {
  t.view.physicalSize = tamano * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(
    theme: temaCaudal(),
    home: const PresentacionDonadores(nombre: 'Ana'),
  ));
  await t.pump(const Duration(milliseconds: 100));
}

/// Pulsa «Siguiente» y deja que la transición de la página termine.
Future<void> _siguiente(WidgetTester t) async {
  await t.tap(find.text('Siguiente'));
  await t.pump(const Duration(milliseconds: 100));
  await t.pump(const Duration(milliseconds: 2500));
  await t.pump(const Duration(milliseconds: 500));
}

void main() {
  test('debeMostrarDonador: solo donador o fundador, y si aún no se vio', () {
    expect(debeMostrarDonador(vista: false, tipo: 'prueba'), isFalse);
    expect(debeMostrarDonador(vista: false, tipo: null), isFalse);
    expect(debeMostrarDonador(vista: true, tipo: 'donador'), isFalse);
    expect(debeMostrarDonador(vista: true, tipo: 'fundador'), isFalse);
    expect(debeMostrarDonador(vista: false, tipo: 'donador'), isTrue);
    expect(debeMostrarDonador(vista: false, tipo: 'fundador'), isTrue);
  });

  testWidgets('se recorre las 11 diapositivas sin excepciones (teléfono)', (t) async {
    await _montar(t, const Size(390, 844));

    // diapositiva 1: la medalla y el saludo con el nombre
    expect(find.text('Gracias, Ana'), findsOneWidget);
    await t.pump(const Duration(seconds: 2));
    expect(t.takeException(), isNull);

    const titulos = {
      0: 'Ayudaste a que Caudal crezca',
      1: 'Tu perfil de donador',
      2: 'Escenarios vivos, solo para ti',
      3: 'Marcos y nombres que brillan',
      4: 'Estéticas exclusivas',
      5: 'Sonido a tu medida',
      6: 'Letras con estilo',
      7: 'Tus exclusivas',
      8: 'Y esto sigue',
    };
    for (var i = 0; i < 10; i++) {
      await _siguiente(t);
      expect(t.takeException(), isNull);
      final titulo = titulos[i];
      if (titulo != null) expect(find.text(titulo), findsOneWidget, reason: 'diapositiva ${i + 2}');
      // en el perfil se ven el nombre y la insignia de donador
      if (i == 1) {
        expect(find.text('Ana'), findsWidgets);
        expect(find.text('Donador'), findsOneWidget);
      }
    }

    // diapositiva 11: el corazón y los dos botones finales
    expect(find.text('Gracias por creer en Caudal.'), findsOneWidget);
    expect(find.text('Descubrir mis exclusivas'), findsOneWidget);
    expect(find.text('Seguir escuchando'), findsOneWidget);
    expect(find.text('Siguiente'), findsNothing);
    await t.pump(const Duration(seconds: 2));
    expect(t.takeException(), isNull);
  });

  testWidgets('se recorre en una pantalla pequeña sin excepciones ni desbordes', (t) async {
    await _montar(t, const Size(320, 568));
    for (var i = 0; i < 10; i++) {
      await _siguiente(t);
      expect(t.takeException(), isNull);
    }
    expect(find.text('Descubrir mis exclusivas'), findsOneWidget);
  });
}
