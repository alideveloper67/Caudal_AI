// Imágenes de «Tu año en Caudal» para revisarlas a ojo (solo con CAPTURAS definida).
import 'dart:io';
import 'dart:ui' as ui;

import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/nucleo/premium_letras.dart';
import 'package:caudal/ui/paginas/resumen_anual_pagina.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

Escucha _e(String titulo, String artista, DateTime f) => Escucha({
      'clave': 'yt:$titulo',
      'video_id': 'v$titulo',
      'titulo': titulo,
      'artista': artista,
      'artistas': [
        {'id': 'id_$artista', 'nombre': artista}
      ],
      'duracion': 200,
      'miniatura': '',
    }, f);

void main() {
  final carpeta = Platform.environment['CAPTURAS'];
  testWidgets('las tarjetas de Tu año se ven bien', (t) async {
    if (carpeta != null) {
      final f = FontLoader('Seg')..addFont(File('C:/Windows/Fonts/segoeuib.ttf').readAsBytes().then((b) => ByteData.view(b.buffer)));
      await t.runAsync(f.load);
      final i = FontLoader('MaterialIcons')
        ..addFont(File('C:/Users/USER/FlutterSDK/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf')
            .readAsBytes()
            .then((b) => ByteData.view(b.buffer)));
      await t.runAsync(i.load);
      Directory(carpeta).createSync(recursive: true);
    }
    esPremiumLetras = () => true;
    addTearDown(() => esPremiumLetras = () => false);
    t.view.physicalSize = const Size(390, 844) * 2;
    t.view.devicePixelRatio = 2;
    addTearDown(t.view.reset);
    final historial = [
      for (var k = 0; k < 120; k++)
        _e(k % 3 == 0 ? 'Llorando por ti $k' : 'Tema número ${k % 9}', 'Artista ${k % 6}', DateTime(2026, 1 + k % 11, 1 + k % 27, 9 + k % 12)),
    ];
    final llave = GlobalKey();
    await t.pumpWidget(RepaintBoundary(
      key: llave,
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: temaCaudal().copyWith(textTheme: temaCaudal().textTheme.apply(fontFamily: 'Seg')),
        home: ResumenAnualPagina(historial: historial, ahora: DateTime(2026, 12, 10)),
      ),
    ));
    await t.pump(const Duration(milliseconds: 600));
    for (var i = 0; i < 5; i++) {
      expect(t.takeException(), isNull, reason: 'tarjeta ${i + 1}');
      if (carpeta != null) {
        await t.runAsync(() async {
          final ro = llave.currentContext!.findRenderObject() as RenderRepaintBoundary;
          final img = await ro.toImage(pixelRatio: 1.0);
          final bytes = await img.toByteData(format: ui.ImageByteFormat.png);
          File('$carpeta/anio_$i.png').writeAsBytesSync(bytes!.buffer.asUint8List());
        });
      }
      await t.fling(find.byType(PageView), const Offset(-400, 0), 2000);
      await t.pump(const Duration(milliseconds: 700));
    }
  });
}
