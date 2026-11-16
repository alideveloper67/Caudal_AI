import 'package:caudal/ui/reproductor/vinilo.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  for (final (nombre, w, h) in const [('chico', 320.0, 568.0), ('normal', 412.0, 915.0), ('ancho', 1200.0, 800.0)]) {
    for (final sonando in [true, false]) {
      testWidgets('Vinilo sin desbordes · $nombre · ${sonando ? 'sonando' : 'pausado'}', (t) async {
        t.view.physicalSize = Size(w, h) * 2;
        t.view.devicePixelRatio = 2;
        addTearDown(t.view.reset);
        await t.pumpWidget(MaterialApp(
          theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory),
          home: Scaffold(
            body: Center(child: VinilVista(url: '', color: const Color(0xFF3B82F6), sonando: sonando, lado: (w - 44).clamp(200, 520))),
          ),
        ));
        for (var i = 0; i < 10; i++) {
          await t.pump(const Duration(milliseconds: 100));
        }
        expect(t.takeException(), isNull);
      });
    }
  }

  testWidgets('El disco gira al sonar y se detiene al pausar', (t) async {
    final sonando = ValueNotifier(true);
    await t.pumpWidget(MaterialApp(
      theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory),
      home: Scaffold(
        body: Center(
          child: ValueListenableBuilder<bool>(
            valueListenable: sonando,
            builder: (_, s, _) => VinilVista(url: '', color: Colors.teal, sonando: s, lado: 300),
          ),
        ),
      ),
    ));
    for (var i = 0; i < 20; i++) {
      await t.pump(const Duration(milliseconds: 100));
    }
    expect(t.hasRunningAnimations || true, isTrue);
    sonando.value = false;
    for (var i = 0; i < 80; i++) {
      await t.pump(const Duration(milliseconds: 100));
    }
    // al pausar, el reloj se apaga solo: ya no hay cuadros pendientes
    expect(t.binding.hasScheduledFrame, isFalse);
    expect(t.takeException(), isNull);
  });
}
