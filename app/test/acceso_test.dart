import 'package:caudal/ui/paginas/acceso.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<void> _montar(WidgetTester t, Size tam) async {
  t.view.physicalSize = tam;
  t.view.devicePixelRatio = 2.75;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(theme: temaCaudal(), home: AccesoPagina(alEntrar: (_, _) async {})));
  await t.pump(const Duration(milliseconds: 400));
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('sin cuentas abre en Crear cuenta y cabe en un telefono pequeno', (t) async {
    await _montar(t, const Size(720 * 1.5, 1280 * 1.5));
    expect(find.text('Crear mi cuenta'), findsOneWidget);
    expect(find.text('Mantener la sesión iniciada'), findsOneWidget);
    expect(t.takeException(), isNull);
  });

  testWidgets('con un usuario anterior abre en Entrar y lo rellena', (t) async {
    SharedPreferences.setMockInitialValues({'cuenta.ultimo': 'kevin'});
    await _montar(t, const Size(1080, 2400));
    await t.pump(const Duration(milliseconds: 400));
    expect(find.widgetWithText(FilledButton, 'Entrar'), findsOneWidget);
    expect(find.text('kevin'), findsOneWidget);
  });

  testWidgets('avisa si las contrasenas no coinciden, sin llamar a la nube', (t) async {
    await _montar(t, const Size(1080, 2400));
    final campos = find.byType(TextField);
    await t.enterText(campos.at(1), 'kevin');
    await t.enterText(campos.at(2), 'secreto1');
    await t.enterText(campos.at(3), 'secreto2');
    await t.ensureVisible(find.text('Crear mi cuenta'));
    await t.tap(find.text('Crear mi cuenta'));
    await t.pump(const Duration(milliseconds: 300));
    expect(find.text('Las dos contraseñas no coinciden.'), findsOneWidget);
  });

  testWidgets('sin fecha de nacimiento ni términos no deja crear la cuenta', (t) async {
    await _montar(t, const Size(1080, 2400));
    final campos = find.byType(TextField);
    await t.enterText(campos.at(0), 'Kevin Pérez');
    await t.enterText(campos.at(1), 'kevin');
    await t.enterText(campos.at(2), 'secreto1');
    await t.enterText(campos.at(3), 'secreto1');
    await t.ensureVisible(find.text('Crear mi cuenta'));
    await t.tap(find.text('Crear mi cuenta'));
    await t.pump(const Duration(milliseconds: 300));
    expect(find.text('Elige tu fecha de nacimiento.'), findsOneWidget);
    expect(find.textContaining('Política de privacidad', findRichText: true), findsWidgets);
    expect(find.text('Compartir mis datos de uso anónimos (opcional)'), findsOneWidget);
  });
}
