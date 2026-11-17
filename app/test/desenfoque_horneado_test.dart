// El desenfoque horneado (una vez, en pequeño) debe verse como el
// ImageFiltered de antes (en cada fotograma, a pantalla completa).

import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:caudal/ui/horneado.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;

/// Una portada con mucho contraste: cuadrantes de colores y rayas.
Uint8List _portada() {
  final im = img.Image(width: 64, height: 64);
  for (var y = 0; y < 64; y++) {
    for (var x = 0; x < 64; x++) {
      final raya = (x ~/ 4) % 2 == 0;
      final c = x < 32
          ? (y < 32 ? img.ColorRgb8(230, 40, 40) : img.ColorRgb8(40, 200, 60))
          : (y < 32 ? img.ColorRgb8(30, 60, 230) : img.ColorRgb8(250, 220, 30));
      im.setPixel(x, y, raya ? c : img.ColorRgb8(c.r ~/ 3, c.g ~/ 3, c.b ~/ 3));
    }
  }
  return Uint8List.fromList(img.encodePng(im));
}

Future<ByteData> _pixeles(WidgetTester t, GlobalKey llave) async {
  final caja = llave.currentContext!.findRenderObject()! as RenderRepaintBoundary;
  late ByteData datos;
  await t.runAsync(() async {
    final im = await caja.toImage(pixelRatio: 1);
    datos = (await im.toByteData(format: ui.ImageByteFormat.rawRgba))!;
    im.dispose();
  });
  return datos;
}

/// Diferencia media por canal (0..255) entre dos capturas del mismo tamaño.
double _diferencia(ByteData a, ByteData b) {
  var suma = 0;
  for (var i = 0; i < a.lengthInBytes; i++) {
    suma += (a.getUint8(i) - b.getUint8(i)).abs();
  }
  return suma / a.lengthInBytes;
}

void main() {
  final bytes = _portada();

  Future<double> comparar(WidgetTester t, {required double sigma, required TileMode modo, double opacidad = 1}) async {
    t.view.physicalSize = const Size(600, 1200);
    t.view.devicePixelRatio = 3;
    addTearDown(t.view.reset);
    final proveedor = MemoryImage(bytes);
    final antes = GlobalKey(), ahora = GlobalKey();
    Widget caja(Key k, Widget hijo) => RepaintBoundary(
        key: k, child: SizedBox(width: 200, height: 200, child: ColoredBox(color: Colors.black, child: hijo)));
    // primero se decodifica la portada (fuera del reloj falso de la prueba)
    await t.runAsync(() => resolverImagen(proveedor).then((i) => i.dispose()));
    await t.pumpWidget(Directionality(
      textDirection: TextDirection.ltr,
      child: Column(children: [
        caja(antes, Opacity(
          opacity: opacidad,
          child: ImageFiltered(
            imageFilter: ui.ImageFilter.blur(sigmaX: sigma, sigmaY: sigma, tileMode: modo),
            child: Image(image: proveedor, fit: BoxFit.cover, width: double.infinity, height: double.infinity),
          ),
        )),
        caja(ahora, ImagenDesenfocada(clave: 'p', imagen: (_) => proveedor, sigma: sigma, opacidad: opacidad, modo: modo)),
      ]),
    ));
    for (var i = 0; i < 5; i++) {
      await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await t.pump();
    }
    expect(find.descendant(of: find.byKey(ahora), matching: find.byType(RawImage)), findsOneWidget,
        reason: 'la horneada ya esta lista');
    final a = await _pixeles(t, antes), b = await _pixeles(t, ahora);
    return _diferencia(a, b);
  }

  testWidgets('modo ambiente (sigma 38, bordes estirados): igual que antes', (t) async {
    final d = await comparar(t, sigma: 38, modo: TileMode.clamp);
    expect(d, lessThan(3.0), reason: 'diferencia media por canal: $d');
  });

  testWidgets('Fondo de Caudal (desenfoque medio, bordes que se desvanecen, opacidad)', (t) async {
    final d = await comparar(t, sigma: 9, modo: TileMode.decal, opacidad: 0.4);
    expect(d, lessThan(3.0), reason: 'diferencia media por canal: $d');
  });

  testWidgets('Fondo de Caudal con poco desenfoque: sin pixelar', (t) async {
    final d = await comparar(t, sigma: 1.8, modo: TileMode.decal, opacidad: 0.6);
    expect(d, lessThan(3.0), reason: 'diferencia media por canal: $d');
  });

  testWidgets('se hornea en pequeño: con sigma 38 la copia es diminuta', (t) async {
    t.view.physicalSize = const Size(1200, 2400);
    t.view.devicePixelRatio = 3;
    addTearDown(t.view.reset);
    final proveedor = MemoryImage(bytes);
    await t.runAsync(() => resolverImagen(proveedor).then((i) => i.dispose()));
    await t.pumpWidget(Directionality(
      textDirection: TextDirection.ltr,
      child: SizedBox(width: 400, height: 800, child: ImagenDesenfocada(clave: 'p', imagen: (_) => proveedor, sigma: 38)),
    ));
    for (var i = 0; i < 5; i++) {
      await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      await t.pump();
    }
    final raw = t.widget<RawImage>(find.byType(RawImage));
    expect(raw.image!.width, 50, reason: '400 pt x 3 / 24');
    expect(raw.image!.height, 100);
    expect(escalaHorneado(0), 1, reason: 'sin desenfoque no se reduce');
  });
}
