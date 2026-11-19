// Imágenes del barrido del karaoke en una línea de 3 filas (solo con CAPTURAS definida).
import 'dart:io';
import 'dart:ui' as ui;

import 'package:caudal/ui/reproductor/linea_karaoke.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _fuente() async {
  final f = FontLoader('Seg')..addFont(File('C:/Windows/Fonts/segoeuib.ttf').readAsBytes().then((b) => ByteData.view(b.buffer)));
  await f.load();
}

void main() {
  final carpeta = Platform.environment['CAPTURAS'];
  testWidgets('el relleno recorre las filas una tras otra', (t) async {
    if (carpeta != null) {
      await t.runAsync(_fuente);
      Directory(carpeta).createSync(recursive: true);
    }
    const texto = 'Caperuza, ¿donde estas?, porfa no te escondas mas, soy tu lobo, animal de monte y de noche';
    const estilo = TextStyle(fontSize: 26, fontWeight: FontWeight.w800, height: 1.3, fontFamily: 'Seg');
    for (final f in [0.1, 0.4, 0.7, 0.95]) {
      final llave = GlobalKey();
      final reloj = AlwaysStoppedAnimation<double>(f);
      await t.pumpWidget(Directionality(
        textDirection: TextDirection.ltr,
        child: Align(alignment: Alignment.topLeft, child: RepaintBoundary(
          key: llave,
          child: Container(
            color: const Color(0xFF8A3A3A),
            width: 320,
            padding: const EdgeInsets.all(16),
            child: LayoutBuilder(builder: (_, c) {
              final resto = TextPainter(
                text: TextSpan(text: texto, style: estilo.copyWith(color: const Color(0x99000000))),
                textDirection: TextDirection.ltr,
                textWidthBasis: TextWidthBasis.longestLine,
              )..layout(maxWidth: c.maxWidth);
              final cantada = TextPainter(
                text: TextSpan(text: texto, style: estilo.copyWith(color: Colors.white)),
                textDirection: TextDirection.ltr,
                textWidthBasis: TextWidthBasis.longestLine,
              )..layout(maxWidth: c.maxWidth);
              final filas = resto.computeLineMetrics();
              debugPrint('filas=${filas.length} ancho=${c.maxWidth} anchos=${filas.map((m) => m.width.round()).toList()}'); expect(filas.length, greaterThanOrEqualTo(3));
              return CustomPaint(size: Size(resto.width, resto.height), painter: PintorKaraoke(reloj, resto, cantada, filas));
            }),
          ),
        )),
      ));
      await t.pump();
      expect(t.takeException(), isNull);
      if (carpeta != null) {
        await t.runAsync(() async {
          final ro = llave.currentContext!.findRenderObject() as RenderRepaintBoundary;
          final img = await ro.toImage(pixelRatio: 1.5);
          final bytes = await img.toByteData(format: ui.ImageByteFormat.png);
          File('$carpeta/k_${(f * 100).round()}.png').writeAsBytesSync(bytes!.buffer.asUint8List());
        });
      }
    }
  });
}
