// Logros en pantalla: la página con todas las insignias y la vitrina, el aviso que baja al
// conseguir uno, la vitrina del perfil (propia y de otra persona) y la casilla del aviso de errores.
// Con CAPTURAS=<carpeta> guarda imágenes para revisarlas a ojo.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:caudal/nucleo/aviso_errores.dart';
import 'package:caudal/nucleo/logros.dart';
import 'package:caudal/ui/logros_aviso.dart';
import 'package:caudal/ui/logros_insignia.dart';
import 'package:caudal/ui/logros_vitrina.dart';
import 'package:caudal/ui/paginas/ajuste_aviso_errores.dart';
import 'package:caudal/ui/paginas/logros_pagina.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

final _carpeta = Platform.environment['CAPTURAS'];

Future<void> _fuentes(WidgetTester t) async {
  if (_carpeta == null) return;
  final f = FontLoader('Seg')
    ..addFont(File('C:/Windows/Fonts/segoeui.ttf').readAsBytes().then((b) => ByteData.view(b.buffer)))
    ..addFont(File('C:/Windows/Fonts/segoeuib.ttf').readAsBytes().then((b) => ByteData.view(b.buffer)));
  await t.runAsync(f.load);
  final i = FontLoader('MaterialIcons')
    ..addFont(File('C:/Users/USER/FlutterSDK/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf')
        .readAsBytes()
        .then((b) => ByteData.view(b.buffer)));
  await t.runAsync(i.load);
  Directory(_carpeta!).createSync(recursive: true);
}

Future<void> _captura(WidgetTester t, GlobalKey llave, String nombre) async {
  if (_carpeta == null) return;
  await t.runAsync(() async {
    final ro = llave.currentContext!.findRenderObject() as RenderRepaintBoundary;
    final img = await ro.toImage(pixelRatio: 1.0);
    final bytes = await img.toByteData(format: ui.ImageByteFormat.png);
    File('$_carpeta/$nombre.png').writeAsBytesSync(bytes!.buffer.asUint8List());
  });
}

Widget _app(Widget home, GlobalKey llave) => RepaintBoundary(
      key: llave,
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: temaCaudal().copyWith(textTheme: temaCaudal().textTheme.apply(fontFamily: 'Seg')),
        home: home,
      ),
    );

Logros _conAlgo() {
  final lg = Logros.enMemoria();
  lg.anotarListas(6);
  lg.anotarMeGusta(30);
  lg.anotarSegundos(4000);
  lg.revisar();
  return lg;
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('las insignias apagadas son grises y las encendidas tienen color', () {
    final px = ImagenesInsignia.pixeles('gusta_25');
    final gris = ImagenesInsignia.pixeles('gusta_25', apagado: true);
    final c = px[10][12]!, g = gris[10][12]!;
    expect(c.r > c.b + 0.2, isTrue); // el corazón es rojo
    expect((g.r - g.g).abs() < 0.02, isTrue);
    expect(px[0][0], isNull); // fondo transparente
  });

  testWidgets('la página enseña todos los logros y deja lucir hasta 3', (t) async {
    await _fuentes(t);
    t.view.physicalSize = const Size(900, 2600);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    final lg = _conAlgo();
    var cambios = 0;
    final llave = GlobalKey();
    await t.pumpWidget(_app(LogrosPagina(logros: lg, alCambiarVitrina: () => cambios++), llave));
    await t.pumpAndSettle();
    expect(find.text('${lg.desbloqueados.length} de ${catalogoLogros.length}'), findsOneWidget);
    expect(find.text('Lucir'), findsNWidgets(lg.desbloqueados.length));
    await _captura(t, llave, 'logros_pagina');
    for (var i = 0; i < 3; i++) {
      await t.tap(find.text('Lucir').first);
      await t.pumpAndSettle();
    }
    expect(lg.vitrina, hasLength(3));
    expect(cambios, 3);
    expect(find.text('En tu perfil'), findsNWidgets(3));
    await t.tap(find.text('Lucir').first);
    await t.pumpAndSettle();
    expect(find.textContaining('ya tiene 3'), findsOneWidget);
    expect(lg.vitrina, hasLength(3));
    // en el teléfono (estrecho) va en una columna y se puede bajar hasta el final
    t.view.physicalSize = const Size(390, 844);
    await t.pumpAndSettle();
    await t.scrollUntilVisible(find.text('Vitrina llena'), 300);
    expect(t.takeException(), isNull);
  });

  testWidgets('el aviso baja, se ve y se va solo', (t) async {
    await _fuentes(t);
    t.view.physicalSize = const Size(390, 300);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    addTearDown(AvisosLogros.reiniciar);
    final llave = GlobalKey();
    await t.pumpWidget(_app(const Scaffold(body: SizedBox.expand()), llave));
    final overlay = t.state<NavigatorState>(find.byType(Navigator)).overlay;
    AvisosLogros.mostrar(overlay, [logroPorId['racha_7']!]);
    await t.pump();
    await t.pump(const Duration(milliseconds: 700));
    expect(find.text('Semana en llamas'), findsOneWidget);
    expect(find.text('¡LOGRO CONSEGUIDO!'), findsOneWidget);
    await _captura(t, llave, 'logros_aviso');
    await t.pump(const Duration(seconds: 5));
    // a los 4,8 s arranca la salida; su animación (650 ms) empieza en el cuadro siguiente
    await t.pump(const Duration(milliseconds: 700));
    expect(find.text('Semana en llamas'), findsNothing);
    expect(AvisosLogros.visible, isFalse);

    // muchos de golpe: uno solo con «+N más»; tocarlo lo cierra
    var pulsado = false;
    AvisosLogros.mostrar(overlay, catalogoLogros.take(6).toList(), alPulsar: () => pulsado = true);
    await t.pump();
    await t.pump(const Duration(milliseconds: 700));
    expect(find.textContaining('+5 más'), findsOneWidget);
    await t.tap(find.textContaining('+5 más'));
    // al tocar también sale con la animación de 650 ms: un cuadro para arrancarla y otro después
    await t.pump();
    await t.pump(const Duration(milliseconds: 700));
    expect(pulsado, isTrue);
    expect(AvisosLogros.visible, isFalse);
  });

  testWidgets('vitrina del perfil: la propia y la de otra persona', (t) async {
    await _fuentes(t);
    final lg = _conAlgo();
    final llave = GlobalKey();
    await t.pumpWidget(_app(
        Scaffold(body: ListView(children: [
          VitrinaLogros(usuario: 'yo', propio: true, logros: lg),
          VitrinaLogros(
              usuario: 'luis', propio: false,
              cargar: (s, u) async => (vitrina: ['racha_7', 'lista_1'], total: 9, fechas: const <String, int>{})),
          VitrinaLogros(
              usuario: 'nadie', propio: false,
              cargar: (s, u) async => (vitrina: <String>[], total: 0, fechas: const <String, int>{})),
        ])),
        llave));
    await t.pumpAndSettle();
    expect(find.textContaining('Elige hasta 3'), findsOneWidget);
    lg.alternarVitrina('lista_1');
    await t.pumpAndSettle();
    expect(find.text('Mi primera lista'), findsNWidgets(2)); // la mía y la de luis
    expect(find.text('9 de ${catalogoLogros.length}'), findsOneWidget);
    expect(find.text('Logros'), findsNWidgets(2)); // la de «nadie» no ocupa lugar
    await _captura(t, llave, 'logros_vitrina');
    await t.tap(find.text('Ver todos'));
    await t.pumpAndSettle();
    expect(find.byType(LogrosPagina), findsOneWidget);
  });

  testWidgets('la casilla del aviso de errores se guarda', (t) async {
    await t.pumpWidget(_app(const Scaffold(body: AjusteAvisoErrores()), GlobalKey()));
    await t.pumpAndSettle();
    final s = t.widget<SwitchListTile>(find.byType(SwitchListTile));
    expect(s.value, isTrue);
    await t.tap(find.byType(SwitchListTile));
    await t.pumpAndSettle();
    expect(await t.runAsync(AvisoErrores.activo), isFalse);
  });
}
