// Play y pausa suaves: la bajada de ~180 ms antes de pausar y la subida de
// ~220 ms al reanudar. Sin motor de sonido: el volumen que se aplica se anota
// y se mira que sea una rampa sin saltos y que el volumen del usuario no cambie.
import 'package:caudal/reproduccion/pausa_suave.dart';
import 'package:caudal/ui/reproductor/animaciones.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Un motor de mentira: anota el volumen y si esta sonando.
class _Motor {
  _Motor() {
    suave = PausaSuave(
      aplicar: () async => volumenes.add(volumenUsuario * suave.factor),
      pausarMotor: () async {
        sonando = false;
        eventos.add('pausa@${volumenes.isEmpty ? 'x' : volumenes.last.toStringAsFixed(2)}');
      },
      reanudarMotor: () async {
        sonando = true;
        eventos.add('play@${volumenes.isEmpty ? 'x' : volumenes.last.toStringAsFixed(2)}');
      },
    );
  }

  late final PausaSuave suave;
  final double volumenUsuario = 80;
  final volumenes = <double>[];
  final eventos = <String>[];
  bool sonando = true;
}

void main() {
  test('la curva suave empieza y acaba en 0 y 1 y nunca baja', () {
    expect(suavizar(0), 0);
    expect(suavizar(1), 1);
    expect(suavizar(-3), 0);
    expect(suavizar(4), 1);
    var antes = -1.0;
    for (var i = 0; i <= 20; i++) {
      final v = suavizar(i / 20);
      expect(v, greaterThanOrEqualTo(antes));
      antes = v;
    }
  });

  test('los pasos cubren el tiempo pedido', () {
    expect(pasosDeRampa(bajadaPausa, const Duration(milliseconds: 20)), 9);
    expect(pasosDeRampa(subidaPausa, const Duration(milliseconds: 20)), 11);
    expect(pasosDeRampa(Duration.zero, const Duration(milliseconds: 20)), 1);
  });

  test('pausar baja el volumen en ~180 ms y solo entonces pausa', () async {
    final m = _Motor();
    final t0 = DateTime.now();
    await m.suave.pausar();
    final ms = DateTime.now().difference(t0).inMilliseconds;
    expect(ms, greaterThanOrEqualTo(150));
    expect(ms, lessThan(600));
    expect(m.sonando, isFalse);
    // lo ultimo que se oyo fue silencio y la pausa cayo ahi, sin clic
    expect(m.volumenes.last, 0);
    expect(m.eventos.single, 'pausa@0.00');
    // bajada en rampa: nunca sube y ningun escalon pasa de un tercio del total
    for (var i = 1; i < m.volumenes.length; i++) {
      expect(m.volumenes[i], lessThanOrEqualTo(m.volumenes[i - 1]));
      expect(m.volumenes[i - 1] - m.volumenes[i], lessThan(80 / 3));
    }
    expect(m.volumenes.length, greaterThan(4));
    // el volumen del usuario no se toco: solo cambio el multiplicador
    expect(m.volumenUsuario, 80);
  });

  test('reanudar arranca en silencio y sube en ~220 ms hasta el volumen entero', () async {
    final m = _Motor();
    await m.suave.pausar();
    m.volumenes.clear();
    final t0 = DateTime.now();
    await m.suave.reanudar(sonaba: false);
    final ms = DateTime.now().difference(t0).inMilliseconds;
    expect(ms, greaterThanOrEqualTo(180));
    expect(ms, lessThan(700));
    expect(m.sonando, isTrue);
    // el motor arranca con el volumen a 0 (sin clic) y acaba al 100 % del del usuario
    expect(m.volumenes.first, 0);
    expect(m.eventos.last, 'play@0.00');
    expect(m.volumenes.last, 80);
    expect(m.suave.factor, 1);
    for (var i = 1; i < m.volumenes.length; i++) {
      expect(m.volumenes[i], greaterThanOrEqualTo(m.volumenes[i - 1]));
    }
  });

  test('si se reanuda a mitad de la bajada no llega a pausar y sube desde donde iba', () async {
    final m = _Motor();
    final bajando = m.suave.pausar();
    await Future<void>.delayed(const Duration(milliseconds: 70));
    expect(m.suave.enCurso, isTrue);
    final mitad = m.suave.factor;
    expect(mitad, inExclusiveRange(0.0, 1.0));
    await m.suave.reanudar(sonaba: true);
    await bajando;
    expect(m.sonando, isTrue);
    expect(m.eventos, isEmpty); // ni pausa ni play: el motor no se enteró
    expect(m.suave.factor, 1);
    expect(m.suave.enCurso, isFalse);
  });

  test('dos pausas seguidas pausan una sola vez', () async {
    final m = _Motor();
    final a = m.suave.pausar();
    final b = m.suave.pausar();
    await Future.wait([a, b]);
    expect(m.eventos, ['pausa@0.00']);
  });

  test('cancelar deja el volumen entero (otra cancion, fundido)', () async {
    final m = _Motor();
    final bajando = m.suave.pausar();
    await Future<void>.delayed(const Duration(milliseconds: 60));
    m.suave.cancelar();
    await bajando;
    expect(m.suave.factor, 1);
    expect(m.eventos, isEmpty);
    expect(m.sonando, isTrue);
  });

  test('pausar y reanudar sin esperar deja el motor sonando y al volumen entero', () async {
    final m = _Motor();
    await m.suave.pausar();
    final subiendo = m.suave.reanudar(sonaba: false);
    await Future<void>.delayed(const Duration(milliseconds: 50));
    final p = m.suave.pausar(); // cambia de idea a mitad de la subida
    await Future.wait([subiendo, p]);
    expect(m.sonando, isFalse);
    expect(m.suave.factor, 0);
    await m.suave.reanudar(sonaba: false);
    expect(m.sonando, isTrue);
    expect(m.suave.factor, 1);
  });

  // ---------------------------------------------------------------- widget

  testWidgets('el boton de play/pausa cambia de icono al instante y la musica lo sigue suave', (t) async {
    // el boton va a la orden suave: pausa -> icono de play enseguida; el motor se pausa despues
    final m = _Motor();
    var sonando = true;
    await t.pumpWidget(MaterialApp(
      home: StatefulBuilder(builder: (context, set) => Scaffold(
        body: Center(
          child: GestureDetector(
            onTap: () async {
              sonando = !sonando;
              set(() {});
              if (sonando) {
                await m.suave.reanudar(sonaba: false);
              } else {
                await m.suave.pausar();
              }
            },
            child: IconoPlayPausa(sonando: sonando, color: Colors.white, tamano: 40),
          ),
        ),
      )),
    ));
    await t.pump(const Duration(milliseconds: 400));
    await t.tap(find.byType(IconoPlayPausa));
    await t.pump(const Duration(milliseconds: 50));
    expect(t.widget<IconoPlayPausa>(find.byType(IconoPlayPausa)).sonando, isFalse);
    // aun no se ha pausado el motor: la bajada tarda ~180 ms
    expect(m.sonando, isTrue);
    await t.pump(const Duration(milliseconds: 400));
    expect(m.sonando, isFalse);
    expect(m.volumenes.last, 0);
    expect(t.takeException(), isNull);
  });
}
