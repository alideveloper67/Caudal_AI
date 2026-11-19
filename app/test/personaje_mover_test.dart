import 'package:caudal/ui/fondo_capa.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class _Musica extends ChangeNotifier {
  bool suena = false;
  void poner(bool v) {
    suena = v;
    notifyListeners();
  }
}

Future<void> _montar(WidgetTester t, {required _Musica m, double x = -1, double y = -1, bool baila = true,
    void Function(double, double)? alMover, bool sinAnimaciones = false}) async {
  Aspecto.aplicar('#FF77B7', 'kuromi');
  t.view.physicalSize = const Size(412, 915);
  t.view.devicePixelRatio = 1;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(
    builder: (context, hijo) => MediaQuery(
      data: MediaQuery.of(context).copyWith(disableAnimations: sinAnimaciones),
      child: hijo!,
    ),
    home: Material(
      child: Scaffold(
        body: SizedBox(
          width: 412,
          height: 915,
          child: Stack(children: [
            Positioned.fill(
              child: PersonajeEncima(
                alto: 160,
                alCambiar: (_) {},
                reproductor: m,
                suena: () => m.suena,
                x: x,
                y: y,
                alMover: alMover,
                baila: baila,
              ),
            ),
          ]),
        ),
      ),
    ),
  ));
  await t.pump();
}

void main() {
  tearDown(() => Aspecto.aplicar('cian', 'oscuro'));

  testWidgets('se arrastra a donde se quiera y avisa dónde quedó', (t) async {
    double? gx, gy;
    await _montar(t, m: _Musica(), alMover: (x, y) {
      gx = x;
      gy = y;
    });
    final antes = t.getCenter(find.byType(PersonajeFondo));
    // empieza en la esquina de abajo a la derecha
    expect(antes.dx, greaterThan(300));
    expect(antes.dy, greaterThan(600));
    await t.drag(find.byType(PersonajeFondo), const Offset(-250, -400));
    await t.pump(const Duration(milliseconds: 300));
    final despues = t.getCenter(find.byType(PersonajeFondo));
    expect(despues.dx, closeTo(antes.dx - 250, 25));
    expect(despues.dy, closeTo(antes.dy - 400, 25));
    expect(gx, isNotNull);
    expect(gx!, inInclusiveRange(0.0, 1.0));
    expect(gy!, inInclusiveRange(0.0, 1.0));
  });

  testWidgets('nunca se sale de la pantalla aunque se tire muy lejos', (t) async {
    await _montar(t, m: _Musica());
    await t.drag(find.byType(PersonajeFondo), const Offset(900, 1500));
    await t.pump(const Duration(milliseconds: 300));
    var r = t.getRect(find.byType(PersonajeFondo));
    expect(r.right, lessThanOrEqualTo(412 + 0.5));
    expect(r.bottom, lessThanOrEqualTo(915 + 0.5));
    await t.drag(find.byType(PersonajeFondo), const Offset(-1500, -2500));
    await t.pump(const Duration(milliseconds: 300));
    r = t.getRect(find.byType(PersonajeFondo));
    expect(r.left, greaterThanOrEqualTo(-0.5));
    expect(r.top, greaterThanOrEqualTo(-0.5));
  });

  testWidgets('la posición guardada se respeta al abrir y doble toque lo devuelve a su esquina', (t) async {
    double? gx, gy;
    await _montar(t, m: _Musica(), x: 0.0, y: 0.0, alMover: (x, y) {
      gx = x;
      gy = y;
    });
    final c = t.getRect(find.byType(PersonajeFondo));
    expect(c.left, lessThan(30));
    expect(c.top, lessThan(80));
    await t.tap(find.byType(PersonajeFondo));
    await t.pump(const Duration(milliseconds: 60));
    await t.tap(find.byType(PersonajeFondo));
    await t.pump(const Duration(milliseconds: 300));
    expect(gx, -1);
    expect(gy, -1);
    expect(t.getCenter(find.byType(PersonajeFondo)).dx, greaterThan(300));
  });

  testWidgets('baila solo mientras suena y se queda quieto en pausa', (t) async {
    final m = _Musica();
    await _montar(t, m: m);
    expect(find.byType(Transform), findsWidgets);
    expect(t.hasRunningAnimations, isFalse);
    m.poner(true);
    await t.pump();
    await t.pump(const Duration(milliseconds: 200));
    expect(t.hasRunningAnimations, isTrue);
    m.poner(false);
    await t.pump();
    await t.pump(const Duration(milliseconds: 400));
    await t.pump(const Duration(milliseconds: 400));
    expect(t.hasRunningAnimations, isFalse);
  });

  testWidgets('con el modo ligero o sin baile no anima nada', (t) async {
    final m = _Musica()..suena = true;
    await _montar(t, m: m, baila: false);
    await t.pump(const Duration(milliseconds: 300));
    expect(t.hasRunningAnimations, isFalse);
    await _montar(t, m: m, sinAnimaciones: true);
    await t.pump(const Duration(milliseconds: 300));
    expect(t.hasRunningAnimations, isFalse);
  });
}
