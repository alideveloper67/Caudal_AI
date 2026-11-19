// Genera una imagen de cada ilustración de la presentación para revisarla a ojo.
// Solo escribe archivos si se define CAPTURAS (ruta de una carpeta); sin eso no hace nada.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:caudal/ui/novedades/diapositivas.dart';
import 'package:caudal/ui/novedades/ilustraciones.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _cargarFuentes() async {
  final texto = FontLoader('Seg');
  texto.addFont(File('C:/Windows/Fonts/segoeuib.ttf').readAsBytes().then((b) => ByteData.view(b.buffer)));
  await texto.load();
  final iconos = FontLoader('MaterialIcons');
  iconos.addFont(File('C:/Users/USER/FlutterSDK/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf')
      .readAsBytes()
      .then((b) => ByteData.view(b.buffer)));
  await iconos.load();
}

void main() {
  final carpeta = Platform.environment['CAPTURAS'];

  testWidgets('cada ilustración se pinta sin errores en varios instantes', (t) async {
    if (carpeta != null) {
      await t.runAsync(_cargarFuentes);
      familiaIlustraciones = 'Seg';
      Directory(carpeta).createSync(recursive: true);
    }
    for (final (i, d) in diapositivas.indexed) {
      for (final seg in const [1.5, 4.2, 8.0, 11.5]) {
        final llave = GlobalKey();
        await t.pumpWidget(MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: ThemeData(fontFamily: 'Seg', brightness: Brightness.dark),
          home: Scaffold(
            backgroundColor: const Color(0xFF0B0D12),
            body: Center(
              child: RepaintBoundary(
                key: llave,
                child: SizedBox(
                  width: 420,
                  height: 420,
                  child: ColoredBox(
                    color: const Color(0xFF0B0D12),
                    child: d.ilustracion(Ctx(AlwaysStoppedAnimation<double>(seg / segundosVuelta), d.color, false), 420),
                  ),
                ),
              ),
            ),
          ),
        ));
        await t.pump();
        expect(t.takeException(), isNull, reason: 'diapositiva $i (${d.titulo}) a los $seg s');
        if (carpeta != null) {
          await t.runAsync(() async {
            final ro = llave.currentContext!.findRenderObject() as RenderRepaintBoundary;
            final img = await ro.toImage(pixelRatio: 1.5);
            final bytes = await img.toByteData(format: ui.ImageByteFormat.png);
            File('$carpeta/d${i.toString().padLeft(2, '0')}_${(seg * 10).round()}.png').writeAsBytesSync(bytes!.buffer.asUint8List());
          });
        }
      }
    }
  });
}
