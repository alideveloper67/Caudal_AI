import 'dart:io';
import 'dart:typed_data';

import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/ui/comunes.dart';
import 'package:caudal/ui/hoja_portada.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

Uint8List _foto(int w, int h) {
  final im = img.Image(width: w, height: h);
  img.fill(im, color: img.ColorRgb8(200, 40, 40));
  return Uint8List.fromList(img.encodePng(im));
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Directory tmp;
  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('portada_lista_');
    Coleccion.carpetaPortadasPrueba = '${tmp.path}/portadas_listas';
    Coleccion.portadaEnBytes = false;
    PortadasMem.limpiar();
  });
  tearDown(() async {
    try {
      await tmp.delete(recursive: true);
    } catch (_) {}
  });

  test('migra una base sin la columna sin perder listas', () async {
    final ruta = '${tmp.path}/vieja.db';
    // se crea con el esquema actual y se deja como estaba en la version 1
    final nueva = await Coleccion.abrirEn(ruta);
    await nueva.crearLista('Vieja');
    await nueva.cerrar();
    final vieja = await databaseFactoryFfi.openDatabase(ruta);
    await vieja.execute('ALTER TABLE listas DROP COLUMN portada');
    await vieja.execute('ALTER TABLE listas DROP COLUMN portada_datos');
    await vieja.execute('PRAGMA user_version = 1');
    await vieja.close();

    final c = await Coleccion.abrirEn(ruta);
    final ls = await c.listas();
    expect(ls.length, 1);
    expect(ls.first['nombre'], 'Vieja');
    expect(ls.first['portada'], isNull);
    expect(await c.portadaPersonalizada(ls.first['id'] as int), '');
    await c.cerrar();
  });

  test('archivo: poner, mostrar primero, quitar y borrar limpian el disco', () async {
    final c = await Coleccion.abrirEn('${tmp.path}/a.db');
    final id = await c.crearLista('Mi lista');
    await c.recordar({'clave': 'yt:1', 'titulo': 'Uno', 'miniatura': 'https://x/1.jpg'});
    await c.agregarALista(id, [{'clave': 'yt:1', 'titulo': 'Uno', 'miniatura': 'https://x/1.jpg'}]);
    expect(await c.portadasDeLista(id), ['https://x/1.jpg']);

    await c.ponerPortadaLista(id, _foto(300, 120));
    final r1 = (await c.portadasDeLista(id)).single;
    expect(r1.endsWith('.jpg'), isTrue);
    final dec = img.decodeJpg(await File(r1).readAsBytes())!;
    expect(dec.width, dec.height); // recortada en cuadrado
    expect(await c.portadasDeLista(id, 1), [r1]);

    await Future<void>.delayed(const Duration(milliseconds: 5));
    await c.ponerPortadaLista(id, _foto(100, 100));
    final r2 = (await c.portadasDeLista(id)).single;
    expect(r2, isNot(r1));
    expect(File(r1).existsSync(), isFalse, reason: 'borra la anterior al reemplazar');
    expect(File(r2).existsSync(), isTrue);

    await c.quitarPortadaLista(id);
    expect(File(r2).existsSync(), isFalse);
    expect(await c.portadasDeLista(id), ['https://x/1.jpg']);

    await c.ponerPortadaLista(id, _foto(50, 80));
    final r3 = (await c.portadasDeLista(id)).single;
    await c.borrarLista(id);
    expect(File(r3).existsSync(), isFalse, reason: 'al borrar la lista se borra la portada');
    await c.cerrar();
  });

  test('bytes (web): se guarda en la base, sobrevive al reabrir y se limpia', () async {
    Coleccion.portadaEnBytes = true;
    final ruta = '${tmp.path}/b.db';
    var c = await Coleccion.abrirEn(ruta);
    final id = await c.crearLista('Web');
    await c.ponerPortadaLista(id, _foto(200, 100));
    final ref = (await c.portadasDeLista(id)).single;
    expect(ref.startsWith('mem:$id:'), isTrue);
    expect(PortadasMem.bytes(ref), isNotNull);
    expect(Directory('${tmp.path}/portadas_listas').existsSync(), isFalse);
    await c.cerrar();

    PortadasMem.limpiar();
    c = await Coleccion.abrirEn(ruta);
    expect((await c.portadasDeLista(id)).single, ref);
    final b = PortadasMem.bytes(ref);
    expect(b, isNotNull, reason: 'se vuelve a cargar al abrir la base');
    expect(img.decodeJpg(b!)!.width, img.decodeJpg(b)!.height);

    await c.quitarPortadaLista(id);
    expect(PortadasMem.bytes(ref), isNull);
    expect(await c.portadasDeLista(id), isEmpty);
    await c.cerrar();
  });

  test('mosaico: solo lee las primeras canciones, en orden, sin repetir ni vacías', () async {
    final c = await Coleccion.abrirEn('${tmp.path}/m.db');
    final id = await c.crearLista('Larga');
    final pistas = [
      {'clave': 'yt:0', 'titulo': '0', 'miniatura': ''},
      {'clave': 'yt:1', 'titulo': '1', 'miniatura': 'https://x/a.jpg'},
      {'clave': 'yt:2', 'titulo': '2', 'miniatura': 'https://x/a.jpg'},
      for (var i = 3; i < 500; i++) {'clave': 'yt:$i', 'titulo': '$i', 'miniatura': 'https://x/$i.jpg'},
    ];
    await c.agregarALista(id, pistas); // guarda tambien las pistas, en una transaccion
    // una que falta en `pistas` (p. ej. borrada) no corta el mosaico
    await c.db.delete('pistas', where: 'clave = ?', whereArgs: ['yt:3']);
    expect(await c.portadasDeLista(id), ['https://x/a.jpg', 'https://x/4.jpg', 'https://x/5.jpg', 'https://x/6.jpg']);
    expect(await c.portadasDeLista(id, 1), ['https://x/a.jpg']);
    // ya no hace falta leer las 500: las consultas llevan LIMIT
    final sinMiniaturas = await c.crearLista('Sin fotos');
    await c.agregarALista(sinMiniaturas, [for (var i = 0; i < 60; i++) {'clave': 'yt:s$i', 'titulo': 's$i'}]);
    expect(await c.portadasDeLista(sinMiniaturas), isEmpty, reason: 'mira como mucho 40 y para');
    await c.cerrar();
  });

  test('una imagen que no es imagen lanza error y no toca la portada', () async {
    final c = await Coleccion.abrirEn('${tmp.path}/c.db');
    final id = await c.crearLista('X');
    await expectLater(c.ponerPortadaLista(id, Uint8List.fromList([1, 2, 3])), throwsA(anything));
    expect(await c.portadaPersonalizada(id), '');
    await c.cerrar();
  });

  group('hoja de portada', () {
    for (final t in const [(320.0, 568.0), (412.0, 915.0), (1440.0, 900.0)]) {
      testWidgets('sin desbordes en ${t.$1.toInt()}x${t.$2.toInt()}', (tester) async {
        tester.view.physicalSize = Size(t.$1, t.$2);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.reset);
        Uint8List? resultado;
        final foto = _foto(64, 32);
        await tester.pumpWidget(MaterialApp(
          theme: ThemeData(splashFactory: InkRipple.splashFactory),
          home: Builder(builder: (ctx) => Scaffold(
            body: Center(child: TextButton(
              onPressed: () async => resultado = await mostrarHojaPortada(ctx,
                  elegir: () async => foto, preparar: (b) async => b),
              child: const Text('abrir'),
            )),
          )),
        ));
        await tester.tap(find.text('abrir'));
        await tester.pumpAndSettle();
        expect(find.text('Elegir de la galería'), findsOneWidget);
        expect(find.text('Cancelar'), findsOneWidget);
        expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Guardar')).onPressed, isNull);

        await tester.tap(find.text('Elegir de la galería'));
        await tester.pumpAndSettle();
        expect(find.text('Elegir otra'), findsOneWidget);
        final caja = tester.getSize(find.byKey(const ValueKey('vista_previa_portada')));
        expect(caja.width, caja.height);
        expect(caja.width, lessThanOrEqualTo(240));
        expect(tester.takeException(), isNull);

        await tester.tap(find.text('Guardar'));
        await tester.pumpAndSettle();
        expect(resultado, foto);
      });
    }

    testWidgets('Cancelar no devuelve nada', (tester) async {
      Uint8List? resultado = Uint8List(1);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData(splashFactory: InkRipple.splashFactory),
        home: Builder(builder: (ctx) => Scaffold(body: TextButton(
          onPressed: () async => resultado = await mostrarHojaPortada(ctx, elegir: () async => null),
          child: const Text('abrir'),
        ))),
      ));
      await tester.tap(find.text('abrir'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Cancelar'));
      await tester.pumpAndSettle();
      expect(resultado, isNull);
    });
  });

  testWidgets('Portada pinta la referencia mem: con Image.memory', (tester) async {
    PortadasMem.poner('mem:1:1', Uint8List.fromList(img.encodePng(img.Image(width: 4, height: 4))));
    await tester.pumpWidget(const MaterialApp(home: Portada(url: 'mem:1:1', lado: 60)));
    expect(find.byType(Image), findsOneWidget);
    expect(tester.widget<Image>(find.byType(Image)).image, isA<ResizeImage>());
  });
}
