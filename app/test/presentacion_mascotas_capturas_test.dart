// Capturas de la presentación de la 2.3.2, una por diapositiva, a 412x915,
// con la letra de verdad (Roboto) y las imágenes cargadas. Solo corre a mano:
//   $env:CAUDAL_CAPTURAS='1'; flutter test test/presentacion_mascotas_capturas_test.dart
// y deja los PNG en ../herramientas/mascotas/vista/presentacion_movil_<n>.png.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:caudal/nucleo/mascota_app.dart';
import 'package:caudal/ui/novedades/presentacion_mascotas.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const _fuentes = r'C:\Users\USER\FlutterSDK\flutter\bin\cache\artifacts\material_fonts';

Future<void> _cargarFuente(String familia, List<String> archivos) async {
  final f = FontLoader(familia);
  for (final a in archivos) {
    final bytes = File('$_fuentes\\$a').readAsBytesSync();
    f.addFont(Future.value(ByteData.view(Uint8List.fromList(bytes).buffer)));
  }
  await f.load();
}

void main() {
  final activas = Platform.environment['CAUDAL_CAPTURAS'] == '1';

  testWidgets('capturas de cada diapositiva', skip: !activas, (t) async {
    final catalogo = File('assets/mascotas/catalogo.json').readAsStringSync();
    await t.runAsync(() async {
      await _cargarFuente('Roboto', ['roboto-regular.ttf', 'roboto-medium.ttf', 'roboto-bold.ttf', 'roboto-black.ttf']);
      await _cargarFuente('MaterialIcons', ['materialicons-regular.otf']);      await MascotaApp.i.cargarCatalogo(texto: catalogo);
      await Future.wait([
        for (final m in MascotaApp.i.catalogo) ...[MascotaApp.i.imagen(m.clave), MascotaApp.i.imagenEstela(m.clave)],
      ]);
    });

    addTearDown(t.view.reset);
    // la de 412x915 es la que se guarda; las otras dos, solo para revisar, van a la carpeta temporal
    final tamanos = <(Size, Directory, String)>[
      (const Size(412, 915), Directory('../herramientas/mascotas/vista'), ''),
      (const Size(320, 568), Directory('${Directory.systemTemp.path}/caudal_capturas'), '_320'),
      (const Size(1440, 900), Directory('${Directory.systemTemp.path}/caudal_capturas'), '_1440'),
    ];
    for (final (tam, salida, sufijo) in tamanos) {
      t.view.physicalSize = tam;
      t.view.devicePixelRatio = 1;
      salida.createSync(recursive: true);
      await _capturar(t, salida, sufijo);
    }
  });
}

Future<void> _capturar(WidgetTester t, Directory salida, String sufijo) async {
  {
    // segundos que se deja correr cada diapositiva antes de la foto
    const momentos = [4.2, 5.0, 5.0, 3.6, 5.4];
    for (var i = 0; i < 5; i++) {
      final borde = GlobalKey();
      await t.pumpWidget(RepaintBoundary(
        key: borde,
        child: MaterialApp(
          key: UniqueKey(),
          debugShowCheckedModeBanner: false,
          theme: temaCaudal(),
          home: PresentacionMascotas(paginaInicial: i, catalogo: MascotaApp.i.catalogo),
        ),
      ));
      await t.pump();
      final ctx = t.element(find.byType(PresentacionMascotas));
      await t.runAsync(() async {
        for (final k in Aspecto.temas.keys) {
          await precacheImage(AssetImage(Aspecto.patronDe(k)!), ctx);
        }
      });
      await t.pump();
      final pasos = (momentos[i] * 10).round();
      for (var k = 0; k < pasos; k++) {
        await t.pump(const Duration(milliseconds: 100));
      }
      expect(t.takeException(), isNull);
      await t.runAsync(() async {
        final r = borde.currentContext!.findRenderObject()! as RenderRepaintBoundary;
        final imagen = await r.toImage(pixelRatio: 1);
        final png = await imagen.toByteData(format: ui.ImageByteFormat.png);
        File('${salida.path}/presentacion_movil_${i + 1}$sufijo.png').writeAsBytesSync(png!.buffer.asUint8List());
      });
    }
  }
}
