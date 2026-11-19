// Genera una imagen de cada estilo de la tarjeta de letra para revisarla a ojo.
// Solo escribe archivos si se define CAPTURAS (carpeta); sin eso solo comprueba que no hay errores.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:caudal/nucleo/premium_letras.dart';
import 'package:caudal/ui/paginas/compartir_letra.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _fuentes() async {
  final texto = FontLoader('Seg')..addFont(File('C:/Windows/Fonts/segoeuib.ttf').readAsBytes().then((b) => ByteData.view(b.buffer)));
  await texto.load();
  final iconos = FontLoader('MaterialIcons')
    ..addFont(File('C:/Users/USER/FlutterSDK/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf')
        .readAsBytes()
        .then((b) => ByteData.view(b.buffer)));
  await iconos.load();
}

void main() {
  final carpeta = Platform.environment['CAPTURAS'];

  testWidgets('cada estilo de la tarjeta de letra se ve bien', (t) async {
    if (carpeta != null) {
      await t.runAsync(_fuentes);
      Directory(carpeta).createSync(recursive: true);
    }
    esPremiumLetras = () => true;
    addTearDown(() => esPremiumLetras = () => false);
    t.view.physicalSize = const Size(390, 1500) * 2;
    t.view.devicePixelRatio = 2;
    addTearDown(t.view.reset);
    final llave = GlobalKey();
    await t.pumpWidget(RepaintBoundary(
      key: llave,
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: ThemeData(fontFamily: 'Seg', brightness: Brightness.dark, scaffoldBackgroundColor: const Color(0xFF0B0D12)),
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: TextButton(
                onPressed: () => compartirLetra(
                  context,
                  pista: {'titulo': 'Jeremías 17-5', 'artista': 'Canserbero', 'miniatura': ''},
                  lineas: [
                    'Que tu risita venía con la fecha ya vencía',
                    'Esta canción no es para nadie',
                    'Que no tenga ganas de matar a alguien por falso',
                    'y tenga fe en que el camino se abre',
                  ],
                  color: const Color(0xFF3B1E54),
                ),
                child: const Text('abrir'),
              ),
            ),
          ),
        ),
      ),
    ));
    await t.tap(find.text('abrir'));
    await t.pump(const Duration(milliseconds: 600));
    for (final estilo in ['Estado', 'Neón', 'Cristal', 'Papel', 'Aurora', 'Color', 'Oscuro', 'Claro']) {
      final f = find.text(estilo);
      await t.tap(f.first, warnIfMissed: false);
      await t.pump(const Duration(milliseconds: 400));
      expect(t.takeException(), isNull, reason: 'estilo $estilo');
      if (carpeta != null) {
        await t.runAsync(() async {
          final ro = llave.currentContext!.findRenderObject() as RenderRepaintBoundary;
          final img = await ro.toImage(pixelRatio: 1.0);
          final bytes = await img.toByteData(format: ui.ImageByteFormat.png);
          File('$carpeta/${estilo.toLowerCase()}.png').writeAsBytesSync(bytes!.buffer.asUint8List());
        });
      }
    }
  });
}
