// «Compartir canción»: cada diseño se pinta sin desbordes (en historia y en cuadrado, con y
// sin mascota y letra, con textos largos), la imagen sale a 1080 px de ancho y la hoja deja
// elegir diseños, recuerda la elección y pone candado a los exclusivos.
//
// Con CAUDAL_COMPARTIR_SALIDA=<carpeta> además deja un PNG de cada diseño en esa carpeta
// (con la letra de verdad: Roboto e iconos de Material), para revisarlos a ojo:
//   $env:CAUDAL_COMPARTIR_SALIDA='C:\ruta'; flutter test test/compartir_cancion_test.dart
// La carátula de ejemplo sale de CAUDAL_COMPARTIR_CARATULA (un PNG) o, si no, se dibuja aquí.
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/mascota_app.dart';
import 'package:caudal/ui/reproductor/compartir_cancion.dart';
import 'package:caudal/ui/reproductor/paleta_portada.dart';
import 'package:caudal/ui/reproductor/tarjetas_compartir.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show debugDisableShadows;
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _fuentes = r'C:\Users\USER\FlutterSDK\flutter\bin\cache\artifacts\material_fonts';
const _caratula = 'mem:compartir_prueba';

Future<void> _cargarFuente(String familia, List<String> archivos) async {
  final f = FontLoader(familia);
  for (final a in archivos) {
    final archivo = File('$_fuentes\\$a');
    if (!archivo.existsSync()) return;
    f.addFont(Future.value(ByteData.view(Uint8List.fromList(archivo.readAsBytesSync()).buffer)));
  }
  await f.load();
}

/// Una carátula de ejemplo: la de la variable de entorno o un degradado violeta con formas.
Future<Uint8List> _bytesCaratula() async {
  final ruta = Platform.environment['CAUDAL_COMPARTIR_CARATULA'];
  if (ruta != null && File(ruta).existsSync()) return File(ruta).readAsBytesSync();
  final grabadora = ui.PictureRecorder();
  final c = Canvas(grabadora);
  const lado = 512.0;
  c.drawRect(
    const Rect.fromLTWH(0, 0, lado, lado),
    Paint()
      ..shader = const LinearGradient(colors: [Color(0xFF6A1B9A), Color(0xFFE040FB), Color(0xFF00BCD4)])
          .createShader(const Rect.fromLTWH(0, 0, lado, lado)),
  );
  c.drawCircle(const Offset(256, 220), 120, Paint()..color = const Color(0xFF1A0B2E));
  c.drawRect(const Rect.fromLTWH(0, 380, lado, 132), Paint()..color = const Color(0xFF26C6DA));
  final img = await grabadora.endRecording().toImage(512, 512);
  final datos = await img.toByteData(format: ui.ImageByteFormat.png);
  return datos!.buffer.asUint8List();
}

late PaletaPortada _paleta;
Mascota? _mascota;
ui.Image? _hoja;

DatosCompartir _datos({bool mascota = true, bool letra = true, bool largo = false}) => DatosCompartir(
      titulo: largo ? 'Una canción con un título larguísimo que no cabe en ninguna parte (versión extendida)' : 'Riri',
      artista: largo ? 'Young Miko, Bad Bunny, Feid y muchos artistas invitados más' : 'Young Miko',
      caratula: _caratula,
      paleta: _paleta,
      posicion: const Duration(seconds: 9),
      duracion: const Duration(minutes: 2, seconds: 14),
      calidad: 'Opus · 138 kbps',
      verso: letra
          ? (largo
              ? 'Dame contacto, le digo «mi diabla», y ella me dice que no, que todavía no, que espere un poquito más'
              : 'Dame contacto, le digo, «mi diabla»')
          : null,
      versoSiguiente: letra ? 'Que esta noche no se acaba' : null,
      contexto: 'Radio de Young Miko',
      mascota: mascota ? _mascota : null,
      hojaMascota: mascota ? _hoja : null,
      fecha: DateTime(2026, 11, 19, 16, 31),
      sello: 'Fundador',
    );

/// Deja que las imágenes (carátula, logo) se decodifiquen de verdad.
Future<void> _esperarImagenes(WidgetTester t) async {
  for (var i = 0; i < 3; i++) {
    await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 120)));
    await t.pump();
  }
}

Widget _app(Widget hijo) => MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: temaCaudal(),
      home: Scaffold(body: Center(child: hijo)),
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    await _cargarFuente('Roboto', [
      'roboto-regular.ttf',
      'roboto-medium.ttf',
      'roboto-bold.ttf',
      'roboto-black.ttf',
      'roboto-italic.ttf',
      'roboto-mediumitalic.ttf',
      'roboto-bolditalic.ttf',
    ]);
    await _cargarFuente('MaterialIcons', ['materialicons-regular.otf']);
    PortadasMem.poner(_caratula, await _bytesCaratula());
    _paleta = await paletaDe(_caratula);
    await MascotaApp.i.cargarCatalogo(texto: File('assets/mascotas/catalogo.json').readAsStringSync());
    _mascota = MascotaApp.i.catalogo.where((m) => m.clave == 'kuromi').firstOrNull ?? MascotaApp.i.catalogo.firstOrNull;
    if (_mascota != null) _hoja = await MascotaApp.i.imagen(_mascota!.clave);
  });

  test('la paleta sale de la carátula de ejemplo', () {
    expect(_paleta, isNot(PaletaPortada.neutra));
    expect(_hoja, isNotNull, reason: 'la hoja de la mascota debe poder leerse de los assets');
  });

  test('tiempos con minutos y horas', () {
    expect(tiempoCompartir(const Duration(seconds: 9)), '0:09');
    expect(tiempoCompartir(const Duration(minutes: 2, seconds: 14)), '2:14');
    expect(tiempoCompartir(const Duration(hours: 1, minutes: 2, seconds: 3)), '1:02:03');
  });

  // cada diseño, en cada forma y tamaño, con todas las combinaciones: nada se desborda
  const tamanos = <(String, double)>[('360', 360), ('pequeña', 230), ('grande', 520)];
  for (final diseno in DisenoCompartir.values) {
    for (final formato in FormatoCompartir.values) {
      testWidgets('«${diseno.nombre}» en ${formato.nombre} se pinta sin desbordes', (t) async {
        t.view.physicalSize = const Size(1200, 2000);
        t.view.devicePixelRatio = 1;
        addTearDown(t.view.reset);
        for (final (_, ancho) in tamanos) {
          for (final largo in [false, true]) {
            for (final (mascota, letra) in [(true, true), (false, false), (true, false), (false, true)]) {
              await t.pumpWidget(_app(SizedBox(
                width: ancho,
                height: ancho / formato.proporcion,
                child: TarjetaCancion(
                  diseno: diseno,
                  datos: _datos(largo: largo),
                  mostrarMascota: mascota,
                  mostrarLetra: letra,
                  fase: 0.6,
                ),
              )));
              expect(t.takeException(), isNull, reason: '${diseno.name} ${formato.name} $ancho largo=$largo m=$mascota l=$letra');
            }
          }
        }
        // sin mascota elegida ni letra en los datos, tampoco
        await t.pumpWidget(_app(SizedBox(
          width: 360,
          height: 360 / formato.proporcion,
          child: TarjetaCancion(diseno: diseno, datos: _datos(mascota: false, letra: false)),
        )));
        expect(t.takeException(), isNull);
      });
    }
  }

  testWidgets('la imagen sale a 1080 px de ancho (1080x1920 en historia, 1080x1080 en cuadrado)', (t) async {
    t.view.physicalSize = const Size(1200, 2000);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    for (final formato in FormatoCompartir.values) {
      final clave = GlobalKey();
      await t.pumpWidget(_app(SizedBox(
        width: 300,
        height: 300 / formato.proporcion,
        child: RepaintBoundary(key: clave, child: TarjetaCancion(diseno: DisenoCompartir.historia, datos: _datos())),
      )));
      await _esperarImagenes(t);
      final bytes = (await t.runAsync(() => imagenDeTarjeta(clave, anchoPx: formato.anchoPx, altoPx: formato.altoPx)))!;
      // el ancho y el alto vienen en la cabecera IHDR del PNG
      final cabecera = ByteData.sublistView(bytes, 16, 24);
      expect(cabecera.getUint32(0), formato.anchoPx);
      expect(cabecera.getUint32(4), formato.altoPx);
    }
  });

  group('la hoja', () {
    setUp(() => SharedPreferences.setMockInitialValues({}));

    Future<void> abrir(WidgetTester t, {required bool donador, DatosCompartir? datos}) async {
      t.view.physicalSize = const Size(412, 915) * 2.6;
      t.view.devicePixelRatio = 2.6;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(
        theme: temaCaudal(),
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: TextButton(
                onPressed: () =>
                    mostrarCompartirCancion(context, datos: Future.value(datos ?? _datos()), esDonador: () => donador),
                child: const Text('abrir'),
              ),
            ),
          ),
        ),
      ));
      await t.tap(find.text('abrir'));
      await t.pump();
      await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 200)));
      await t.pump(const Duration(milliseconds: 400));
      await t.pump(const Duration(milliseconds: 400));
    }

    testWidgets('muestra los diseños, las opciones y los botones', (t) async {
      await abrir(t, donador: true);
      expect(t.takeException(), isNull);
      expect(find.text('Compartir canción'), findsOneWidget);
      expect(find.text('Compartir'), findsOneWidget);
      expect(find.text('Guardar'), findsOneWidget);
      expect(find.text('Mascota'), findsOneWidget);
      expect(find.text('Letra'), findsWidgets);
      expect(find.text('Cuadrado'), findsOneWidget);
      // deslizar la vista previa cambia de diseño y se recuerda
      await t.drag(find.byType(PageView), const Offset(-300, 0));
      await t.pump(const Duration(milliseconds: 600));
      await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('compartir_cancion_diseno'), DisenoCompartir.vinilo.name);
      // cuadrado y sin mascota, también recordado
      await t.tap(find.text('Cuadrado'));
      await t.pump(const Duration(milliseconds: 300));
      await t.tap(find.text('Mascota'));
      await t.pump(const Duration(milliseconds: 300));
      await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
      expect(prefs.getString('compartir_cancion_formato'), FormatoCompartir.cuadrado.name);
      expect(prefs.getBool('compartir_cancion_mascota'), isFalse);
      expect(t.takeException(), isNull);
      // cerrar la hoja para que los relojes se paren
      await t.tap(find.byTooltip('Cerrar'));
      await t.pump(const Duration(milliseconds: 600));
    });

    testWidgets('sin letra no hay diseño «Letra» ni opción de letra', (t) async {
      await abrir(t, donador: true, datos: _datos(letra: false));
      expect(find.widgetWithText(ChoiceChip, 'Letra'), findsNothing);
      expect(find.widgetWithText(FilterChip, 'Letra'), findsNothing);
      expect(find.widgetWithText(ChoiceChip, 'Vinilo'), findsOneWidget);
      await t.tap(find.byTooltip('Cerrar'));
      await t.pump(const Duration(milliseconds: 600));
    });

    testWidgets('sin beneficios los exclusivos llevan candado y explican cómo conseguirlos', (t) async {
      await abrir(t, donador: false);
      await t.scrollUntilVisible(find.widgetWithText(ChoiceChip, 'Oro'), 120,
          scrollable: find.descendant(of: find.byType(ListView).last, matching: find.byType(Scrollable)).first);
      await t.ensureVisible(find.widgetWithText(ChoiceChip, 'Oro'));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.descendant(of: find.widgetWithText(ChoiceChip, 'Oro'), matching: find.byIcon(Icons.lock_rounded)), findsOneWidget);
      await t.tap(find.widgetWithText(ChoiceChip, 'Oro'));
      await t.pump(const Duration(milliseconds: 600));
      expect(find.text('Cómo conseguirlo'), findsOneWidget);
      expect(find.text('Compartir'), findsNothing);
      expect(find.textContaining('exclusivo para donadores'), findsWidgets);
      // no se recuerda un diseño que no se puede usar
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('compartir_cancion_diseno'), isNot(DisenoCompartir.oro.name));
      expect(t.takeException(), isNull);
      await t.tap(find.byTooltip('Cerrar'));
      await t.pump(const Duration(milliseconds: 600));
    });

    testWidgets('con beneficios los exclusivos se pueden compartir', (t) async {
      await abrir(t, donador: true);
      await t.scrollUntilVisible(find.widgetWithText(ChoiceChip, 'Neón'), 120,
          scrollable: find.descendant(of: find.byType(ListView).last, matching: find.byType(Scrollable)).first);
      await t.ensureVisible(find.widgetWithText(ChoiceChip, 'Neón'));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.byIcon(Icons.lock_rounded), findsNothing);
      await t.tap(find.widgetWithText(ChoiceChip, 'Neón'));
      await t.pump(const Duration(milliseconds: 600));
      expect(find.text('Compartir'), findsOneWidget);
      expect(find.text('Cómo conseguirlo'), findsNothing);
      expect(t.takeException(), isNull);
      await t.tap(find.byTooltip('Cerrar'));
      await t.pump(const Duration(milliseconds: 600));
    });
  });

  // ---------------------------------------------------------------- exportar a PNG (a mano)
  final salida = Platform.environment['CAUDAL_COMPARTIR_SALIDA'];
  testWidgets('exporta un PNG de cada diseño', skip: salida == null, (t) async {
    final dir = Directory(salida!)..createSync(recursive: true);
    // las pruebas apagan las sombras difuminadas; para mirar las imágenes hacen falta
    debugDisableShadows = false;
    t.view.physicalSize = const Size(1200, 2000);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final casos = <(DisenoCompartir, FormatoCompartir, bool, bool, String)>[
      for (final d in DisenoCompartir.values) (d, FormatoCompartir.historia, true, true, ''),
      for (final d in DisenoCompartir.values) (d, FormatoCompartir.cuadrado, true, false, '_cuadrado'),
      (DisenoCompartir.historia, FormatoCompartir.historia, false, false, '_sin_mascota_ni_letra'),
    ];
    for (final (diseno, formato, mascota, letra, sufijo) in casos) {
      final clave = GlobalKey();
      const ancho = 360.0;
      await t.pumpWidget(MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: temaCaudal(),
        home: Scaffold(
          body: Align(
            alignment: Alignment.topLeft,
            child: MediaQuery(
              data: MediaQueryData(devicePixelRatio: formato.anchoPx / ancho, size: const Size(1200, 2000)),
              child: SizedBox(
                width: ancho,
                height: ancho / formato.proporcion,
                child: RepaintBoundary(
                  key: clave,
                  child: TarjetaCancion(
                    diseno: diseno,
                    datos: _datos(),
                    mostrarMascota: mascota,
                    mostrarLetra: letra,
                    fase: 0.42,
                  ),
                ),
              ),
            ),
          ),
        ),
      ));
      await _esperarImagenes(t);
      final bytes = (await t.runAsync(() => imagenDeTarjeta(clave, anchoPx: formato.anchoPx)))!;
      File('${dir.path}${Platform.pathSeparator}${diseno.name}$sufijo.png').writeAsBytesSync(bytes);
    }
    debugDisableShadows = true;
  });
}
