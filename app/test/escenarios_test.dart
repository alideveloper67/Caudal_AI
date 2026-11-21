import 'dart:io';
import 'dart:ui' as ui;

import 'package:caudal/ui/escenarios/catalogo.dart';
import 'package:caudal/ui/escenarios/escenario_fondo.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _montar(WidgetTester tester, String clave) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Center(
          child: SizedBox(width: 400, height: 225, child: EscenarioFondo(clave: clave)),
        ),
      ),
    ),
  );
  // la imagen se decodifica con el motor real: dejamos correr el reloj real un momento
  await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
  await tester.pump();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  for (final def in escenarios) {
    testWidgets('escenario ${def.clave}: 10 cuadros e interaccion sin excepciones', (tester) async {
      await _montar(tester, def.clave);
      for (var i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 33));
      }
      final centro = tester.getCenter(find.byType(EscenarioFondo));
      final gesto = await tester.startGesture(centro);
      for (var i = 0; i < 4; i++) {
        await gesto.moveBy(const Offset(20, 6));
        await tester.pump(const Duration(milliseconds: 33));
      }
      await gesto.up();
      await tester.tapAt(centro);
      await tester.pump(const Duration(milliseconds: 33));
      expect(tester.takeException(), isNull);
    });
  }

  test('escenarioPorClave devuelve null para una clave que no existe', () {
    expect(escenarioPorClave('no_existe'), isNull);
    expect(escenarioPorClave('goku')?.clave, 'goku');
  });

  test('todas las rutas de asset existen en assets/escenarios', () {
    for (final def in escenarios) {
      expect(File('assets/escenarios/${def.asset}').existsSync(), isTrue, reason: def.asset);
    }
  });

  testWidgets('las dimensiones de cada imagen coinciden con el catalogo', (tester) async {
    for (final def in escenarios) {
      final bytes = File('assets/escenarios/${def.asset}').readAsBytesSync();
      final dims = await tester.runAsync(() async {
        final codec = await ui.instantiateImageCodec(bytes);
        final cuadro = await codec.getNextFrame();
        final res = (cuadro.image.width, cuadro.image.height);
        cuadro.image.dispose();
        codec.dispose();
        return res;
      });
      expect(dims, (def.ancho, def.alto), reason: def.clave);
    }
  });

  testWidgets('capturar devuelve una imagen del tamano pedido', (tester) async {
    final img = await tester.runAsync(() => EscenarioFondo.capturar('goku', const Size(320, 180)));
    expect(img, isNotNull);
    expect((img!.width, img.height), (320, 180));
  });
}
