import 'dart:async';

import 'package:caudal/nucleo/capturador_oculto.dart';
import 'package:flutter_test/flutter_test.dart';

/// Un capturador que no abre ningun navegador de verdad: solo cuenta.
class _CapturadorContado extends CapturadorOculto {
  _CapturadorContado() : super(soltarTras: const Duration(seconds: 90));
  int abiertos = 0, cerrados = 0;
  bool vivo = false;

  @override
  Future<void> abrirNavegador() async {
    if (vivo) return;
    vivo = true;
    abiertos++;
  }

  @override
  Future<void> cerrarNavegador() async {
    if (!vivo) return;
    vivo = false;
    cerrados++;
  }
}

void main() {
  group('navegador oculto bajo demanda', () {
    testWidgets('no se monta al crearse: solo con la primera captura', (t) async {
      final c = _CapturadorContado();
      await t.pump(const Duration(seconds: 30));
      expect(c.abiertos, 0);
      unawaited(c.capturar('https://x.com/v'));
      await t.pump();
      expect(c.abiertos, 1);
      expect(c.vivo, isTrue);
      await c.cerrar();
    });

    testWidgets('se libera tras ~90 s sin uso, y una captura nueva aplaza el cierre', (t) async {
      final c = _CapturadorContado();
      unawaited(c.capturar('https://x.com/1'));
      await t.pump();
      await t.pump(const Duration(seconds: 60));
      expect(c.vivo, isTrue, reason: 'aun no pasaron 90 s');
      unawaited(c.capturar('https://x.com/2'));
      await t.pump();
      await t.pump(const Duration(seconds: 60));
      expect(c.vivo, isTrue, reason: 'la segunda captura reinicia la cuenta');
      expect(c.abiertos, 1, reason: 'se reutiliza el mismo navegador');
      await t.pump(const Duration(seconds: 31));
      expect(c.vivo, isFalse);
      expect(c.cerrados, 1);
      unawaited(c.capturar('https://x.com/3'));
      await t.pump();
      expect(c.abiertos, 2, reason: 'tras soltarlo se vuelve a montar al hacer falta');
      await c.cerrar();
    });

    test('las capturas van de una en una, sin sondeo', () async {
      final c = _CapturadorContado();
      final orden = <String>[];
      final a = c.capturar('https://x.com/a').then((_) => orden.add('a'));
      final b = c.capturar('https://x.com/b').then((_) => orden.add('b'));
      await Future.wait([a, b]);
      expect(orden, ['a', 'b']);
      expect(c.trabajando, isFalse);
      await c.cerrar();
    });
  });

  test('el capturador nace en reposo', () {
    final c = CapturadorOculto();
    expect(c.trabajando, isFalse, reason: 'no hay ninguna captura en marcha');
  });

  test('una captura vacia no vale', () {
    expect(const CapturaOculta().vale, isFalse);
    expect(const CapturaOculta(url: 'https://x.com/v.mp4').vale, isTrue);
  });

  test('la captura guarda titulo y cookies para la descarga', () {
    const c = CapturaOculta(
      url: 'https://cdn.com/v.mp4',
      titulo: 'Un video',
      cookies: 'sesion=abc',
    );
    expect(c.url, 'https://cdn.com/v.mp4');
    expect(c.titulo, 'Un video');
    expect(c.cookies, 'sesion=abc');
  });

  test('la captura guarda las demas direcciones por si la primera falla', () {
    const c = CapturaOculta(
      url: 'https://cdn.com/bueno.mp4',
      candidatas: ['https://cdn.com/bueno.mp4', 'https://cdn.com/otro.mp4'],
    );
    expect(c.candidatas.length, 2);
  });
}
