// GIF animados en el perfil: detección, reducción conservando cuadros, mensaje
// sin permiso y hoja de búsqueda (sin desbordes en 5 tamaños, con cliente falso).
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:caudal/nucleo/gif_perfil.dart';
import 'package:caudal/ui/paginas/gif_buscador.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:image/image.dart' as img;

/// GIF sintético: [n] cuadros de ruido de [w]×[h] con 80 ms cada uno.
Uint8List _gif({int n = 10, int w = 500, int h = 300}) {
  final r = Random(7);
  img.Image? base;
  for (var i = 0; i < n; i++) {
    final f = img.Image(width: w, height: h, numChannels: 4);
    for (final p in f) {
      // degradado que se mueve con un poco de ruido: pesa como un GIF real
      p.setRgba((p.x * 3 + i * 25) % 256, (p.y * 2 + i * 9) % 256, ((p.x + p.y) * (i + 1) + r.nextInt(40)) % 256, 255);
    }
    f.frameDuration = 80;
    if (base == null) {
      base = f;
    } else {
      base.addFrame(f);
    }
  }
  return Uint8List.fromList(img.encodeGif(base!));
}

final _chico = _gif(n: 3, w: 40, h: 30);

void main() {
  group('detección', () {
    test('cabecera GIF87a / GIF89a y extensión', () {
      expect(GifPerfil.esGif(Uint8List.fromList(utf8.encode('GIF89a....'))), isTrue);
      expect(GifPerfil.esGif(Uint8List.fromList(utf8.encode('GIF87a....'))), isTrue);
      expect(GifPerfil.esGif(Uint8List.fromList([0xFF, 0xD8, 0xFF, 0xE0, 0, 0, 0, 0])), isFalse);
      expect(GifPerfil.esGif(Uint8List.fromList([1, 2, 3]), nombre: 'Mi Foto.GIF'), isTrue);
      expect(GifPerfil.esGif(Uint8List.fromList([1, 2, 3]), nombre: 'foto.png'), isFalse);
      expect(GifPerfil.esGif(_chico), isTrue);
    });
  });

  group('reducción', () {
    test('tamaños de referencia', () {
      final g = _gif();
      final a = GifPerfil.reducir(g, foto: true, maxBytes: 1 << 30)!;
      final b = GifPerfil.reducir(_gif(n: 16), foto: false, maxBytes: 1 << 30)!;
      // ignore: avoid_print
      print('original ${g.length} foto ${a.length} fondo ${b.length}');
    });

    test('conserva los cuadros y la duración cuando basta con achicar', () {
      final g = _gif();
      final r = GifPerfil.reducir(g, foto: true, maxBytes: 900000);
      expect(r, isNotNull);
      expect(r!.length, lessThanOrEqualTo(900000));
      final d = img.decodeGif(r)!;
      expect(d.numFrames, 10);
      expect(d.frames.first.frameDuration, 80);
      expect(d.width, d.height, reason: 'la foto sale cuadrada');
      expect(d.width, lessThanOrEqualTo(GifPerfil.ladoFoto));
    });

    test('el fondo sale 8:3 y respeta el tope quitando cuadros si hace falta', () {
      final g = _gif(n: 16);
      const tope = 700000;
      final r = GifPerfil.reducir(g, foto: false, maxBytes: tope);
      expect(r, isNotNull);
      expect(r!.length, lessThanOrEqualTo(tope));
      final d = img.decodeGif(r)!;
      expect(d.numFrames, greaterThan(1));
      expect(d.numFrames, lessThanOrEqualTo(16));
      expect((d.width / d.height - 8 / 3).abs(), lessThan(0.05));
      expect(d.width, lessThanOrEqualTo(GifPerfil.anchoFondo));
      // al quitar cuadros, los que quedan duran más: el GIF no se acelera
      final total = d.frames.fold<int>(0, (s, f) => s + f.frameDuration);
      expect(total, 16 * 80);
    });

    test('si ni así cabe, devuelve null; si no es un GIF, vacío', () {
      expect(GifPerfil.reducir(_gif(n: 6), foto: true, maxBytes: 500), isNull);
      expect(GifPerfil.reducir(Uint8List.fromList(utf8.encode('GIF89a-roto')), foto: true), isEmpty);
    });

    test('preparar deja intacto un GIF liviano y avisa con amabilidad si no es GIF', () async {
      expect(await GifPerfil.preparar(_chico, foto: true), same(_chico));
      expect(() => GifPerfil.preparar(Uint8List.fromList([1, 2, 3, 4, 5, 6, 7]), foto: true), throwsA(anything));
    });

    test('mensajes', () {
      expect(GifPerfil.sinPermiso, 'Los GIF animados son exclusivos de los donadores de Caudal.');
      expect(GifPerfil.demasiadoPesado, 'Ese GIF pesa demasiado. Prueba con uno más corto.');
    });
  });

  group('hoja de búsqueda', () {
    final tamanos = <Size>[const Size(320, 568), const Size(390, 844), const Size(768, 1024), const Size(1280, 800), const Size(1440, 900)];

    Map<String, dynamic> pagina(int desde, {int n = 12, String siguiente = 'p2', String? aviso}) => {
          'items': [
            for (var i = desde; i < desde + n; i++)
              {'id': 'g$i', 'titulo': 'Gato número $i', 'vista': 'https://media.test/v$i.gif', 'gif': 'https://media.test/g$i.gif', 'ancho': 320, 'alto': 240, 'peso': 90000}
          ],
          'siguiente': siguiente,
          if (aviso != null) 'aviso': aviso,
        };

    GifBuscador falso(List<Uri> pedidos, {Map<String, dynamic> Function(Uri u)? alBuscar, int estado = 200}) => GifBuscador(
          base: 'https://caudal.test/api/gifs',
          cliente: MockClient((req) async {
            pedidos.add(req.url);
            if (req.url.queryParameters.containsKey('bajar')) return http.Response.bytes(_chico, 200);
            final cuerpo = alBuscar != null ? alBuscar(req.url) : pagina(0);
            return http.Response(jsonEncode(cuerpo), estado, headers: {'content-type': 'application/json; charset=utf-8'});
          }),
        );

    Future<void> montar(WidgetTester t, GifBuscador b, Size tam, {bool foto = true}) async {
      t.view.physicalSize = tam;
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(
        theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory),
        home: Scaffold(body: HojaBuscarGif(buscador: b, esFoto: foto)),
      ));
      await t.pump();
      await t.pump(const Duration(milliseconds: 50));
    }

    testWidgets('muestra los GIF del momento sin desbordes en 5 tamaños', (t) async {
      for (final tam in tamanos) {
        final pedidos = <Uri>[];
        await montar(t, falso(pedidos), tam);
        expect(find.byType(GridView), findsOneWidget, reason: '$tam'); expect(find.text('Powered by GIPHY'), findsOneWidget, reason: '$tam');
        expect(pedidos.first.queryParameters.containsKey('q'), isFalse, reason: 'sin texto pide los del momento');
        expect(t.takeException(), isNull, reason: '$tam');
        await t.pumpWidget(const SizedBox());
      }
    });

    testWidgets('escribir espera 350 ms y busca una sola vez', (t) async {
      final pedidos = <Uri>[];
      await montar(t, falso(pedidos), const Size(390, 844));
      pedidos.clear();
      await t.enterText(find.byType(TextField), 'gat');
      await t.pump(const Duration(milliseconds: 100));
      await t.enterText(find.byType(TextField), 'gatos');
      await t.pump(const Duration(milliseconds: 300));
      expect(pedidos, isEmpty);
      await t.pump(const Duration(milliseconds: 100));
      expect(pedidos.length, 1);
      expect(pedidos.single.queryParameters['q'], 'gatos');
      expect(t.takeException(), isNull);
    });

    testWidgets('no deja escribir enlaces', (t) async {
      await montar(t, falso([]), const Size(390, 844));
      await t.enterText(find.byType(TextField), 'https://malo.com/x.gif');
      final campo = t.widget<TextField>(find.byType(TextField));
      expect(campo.controller!.text.contains('/'), isFalse);
      expect(campo.controller!.text.contains(':'), isFalse);
      await t.pump(const Duration(milliseconds: 400));
    });

    testWidgets('paginación: al llegar al final pide la siguiente con pos', (t) async {
      final pedidos = <Uri>[];
      final b = falso(pedidos, alBuscar: (u) => u.queryParameters['pos'] == 'p2' ? pagina(100, siguiente: '') : pagina(0));
      await montar(t, b, const Size(390, 844));
      await t.drag(find.byType(GridView), const Offset(0, -3000));
      await t.pump();
      await t.pump(const Duration(milliseconds: 50));
      expect(pedidos.where((u) => u.queryParameters['pos'] == 'p2'), hasLength(1));
      expect(t.takeException(), isNull);
    });

    testWidgets('el aviso del servicio siempre se muestra', (t) async {
      await montar(t, falso([], alBuscar: (_) => pagina(0, aviso: 'Se ocultaron algunos resultados.')), const Size(320, 568));
      expect(find.text('Se ocultaron algunos resultados.'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('sin_clave: mensaje de que llegará pronto', (t) async {
      await montar(t, falso([], alBuscar: (_) => {'error': 'sin_clave', 'items': []}, estado: 503), const Size(320, 568));
      expect(find.textContaining('llegará muy pronto'), findsOneWidget);
      expect(find.byType(GridView), findsNothing);
      expect(t.takeException(), isNull);
    });

    testWidgets('sin resultados: estado vacío amable', (t) async {
      await montar(t, falso([], alBuscar: (_) => {'items': [], 'siguiente': ''}), const Size(320, 568));
      expect(find.byIcon(Icons.search_off_rounded).evaluate().length + find.textContaining('no hay GIF').evaluate().length, greaterThan(0));
      expect(t.takeException(), isNull);
    });

    testWidgets('elegir un GIF lo descarga por el servicio y muestra la vista previa', (t) async {
      for (final foto in [true, false]) {
        final pedidos = <Uri>[];
        await montar(t, falso(pedidos), const Size(320, 568), foto: foto);
        await t.tap(find.byType(InkWell).first);
        await t.pump();
        await t.pump(const Duration(milliseconds: 50));
        final bajada = pedidos.where((u) => u.queryParameters.containsKey('bajar')).single;
        expect(bajada.host, 'caudal.test');
        expect(bajada.queryParameters['bajar'], 'https://media.test/g0.gif');
        expect(find.text('Usar este GIF'), findsOneWidget);
        expect(find.text('Elegir otro'), findsOneWidget);
        expect(find.byType(VistaPreviaGif), findsOneWidget);
        expect(t.takeException(), isNull);
        await t.tap(find.text('Elegir otro'));
        await t.pump();
        expect(find.byType(GridView), findsOneWidget);
        await t.pumpWidget(const SizedBox());
      }
    });

    testWidgets('la insignia «GIF · Donador» cabe en 320 px junto al botón', (t) async {
      t.view.physicalSize = const Size(320, 568);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(
        theme: temaCaudal(),
        home: const Scaffold(body: Center(child: SizedBox(width: 280, child: Row(children: [Expanded(child: Text('Buscar GIF (fondo)')), InsigniaGifDonador()])))),
      ));
      expect(find.text('GIF · Donador'), findsOneWidget);
      expect(t.takeException(), isNull);
    });
  });
}
