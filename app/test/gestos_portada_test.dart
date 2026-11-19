// Gestos en la caratula del reproductor grande: doble toque = me gusta (con el
// corazon que aparece y se desvanece) y deslizar de lado = siguiente/anterior,
// con umbral y la caratula que sigue al dedo. Prueba el widget solo, sin media_kit.
import 'package:caudal/ui/reproductor/animaciones.dart';
import 'package:caudal/ui/reproductor/portada_deslizable.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class _Cuentas {
  int siguiente = 0, anterior = 0, doble = 0;
}

Future<_Cuentas> _montar(WidgetTester t, {double lado = 300}) async {
  final c = _Cuentas();
  t.view.physicalSize = const Size(1080, 2000);
  t.view.devicePixelRatio = 2.75;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(
    theme: temaCaudal(),
    home: Scaffold(
      body: Center(
        child: PortadaDeslizable(
          pista: {'clave': 'yt:a', 'miniatura': ''},
          lado: lado,
          direccion: 1,
          alSiguiente: () => c.siguiente++,
          alAnterior: () => c.anterior++,
          alDobleToque: () => c.doble++,
        ),
      ),
    ),
  ));
  await t.pump(const Duration(milliseconds: 400));
  return c;
}

double _dx(WidgetTester t) => t.getCenter(find.byType(Hero)).dx;

void main() {
  testWidgets('doble toque marca me gusta una sola vez y el corazon aparece y se desvanece', (t) async {
    final c = await _montar(t);
    expect(find.byIcon(Icons.favorite_rounded), findsNothing);
    final portada = find.byType(Hero);
    await t.tap(portada);
    await t.pump(const Duration(milliseconds: 60));
    await t.tap(portada);
    await t.pump(); // arranca la animacion
    await t.pump(const Duration(milliseconds: 250));
    expect(c.doble, 1);
    expect(find.descendant(of: find.byType(CorazonEmergente), matching: find.byIcon(Icons.favorite_rounded)),
        findsOneWidget);
    // a media animacion se ve; al acabar ya no hay nada
    final op = t.widget<Opacity>(find.descendant(of: find.byType(CorazonEmergente), matching: find.byType(Opacity)));
    expect(op.opacity, greaterThan(0.5));
    await t.pump(const Duration(milliseconds: 1000));
    expect(find.byIcon(Icons.favorite_rounded), findsNothing);
    expect(t.takeException(), isNull);
  });

  testWidgets('un toque solo no hace nada', (t) async {
    final c = await _montar(t);
    await t.tap(find.byType(Hero));
    await t.pump(const Duration(seconds: 1));
    expect([c.doble, c.siguiente, c.anterior], [0, 0, 0]);
  });

  testWidgets('deslizar rapido a la izquierda = siguiente; a la derecha = anterior', (t) async {
    final c = await _montar(t);
    await t.fling(find.byType(Hero), const Offset(-250, 0), 1500);
    await t.pumpAndSettle();
    expect([c.siguiente, c.anterior], [1, 0]);
    await t.fling(find.byType(Hero), const Offset(250, 0), 1500);
    await t.pumpAndSettle();
    expect([c.siguiente, c.anterior], [1, 1]);
  });

  testWidgets('un arrastre corto y lento no cambia de cancion y la caratula vuelve a su sitio', (t) async {
    final c = await _montar(t);
    final centro = _dx(t);
    final g = await t.startGesture(t.getCenter(find.byType(Hero)));
    await g.moveBy(const Offset(-30, 0));
    await t.pump(const Duration(milliseconds: 100));
    await g.moveBy(const Offset(-20, 0));
    await t.pump(const Duration(milliseconds: 400)); // frena: velocidad cero al soltar
    // sigue al dedo (con algo de resistencia)
    expect(_dx(t), lessThan(centro - 8));
    expect(_dx(t), greaterThan(centro - 50));
    await g.up();
    await t.pumpAndSettle();
    expect([c.siguiente, c.anterior], [0, 0]);
    expect(_dx(t), closeTo(centro, 0.5));
  });

  testWidgets('un arrastre lento que pasa del umbral (30 % de la caratula) si cambia', (t) async {
    final c = await _montar(t, lado: 300);
    final g = await t.startGesture(t.getCenter(find.byType(Hero)));
    for (var i = 0; i < 8; i++) {
      await g.moveBy(const Offset(18, 0));
      await t.pump(const Duration(milliseconds: 80));
    }
    await t.pump(const Duration(milliseconds: 400));
    await g.up();
    await t.pumpAndSettle();
    expect([c.siguiente, c.anterior], [0, 1]);
  });

  testWidgets('un gesto vertical no se confunde con cambiar de cancion', (t) async {
    final c = await _montar(t);
    await t.fling(find.byType(Hero), const Offset(0, 300), 1500);
    await t.pumpAndSettle();
    expect([c.siguiente, c.anterior, c.doble], [0, 0, 0]);
    expect(t.takeException(), isNull);
  });

  testWidgets('doble toque seguido de deslizar no dispara los dos', (t) async {
    final c = await _montar(t);
    await t.tap(find.byType(Hero));
    await t.pump(const Duration(milliseconds: 50));
    await t.tap(find.byType(Hero));
    await t.pump(const Duration(milliseconds: 100));
    await t.fling(find.byType(Hero), const Offset(-250, 0), 1500);
    await t.pumpAndSettle();
    expect([c.doble, c.siguiente], [1, 1]);
  });
}
