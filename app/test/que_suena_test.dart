import 'dart:convert';
import 'dart:typed_data';

import 'package:caudal/nucleo/que_suena.dart';
import 'package:caudal/ui/paginas/que_suena_pagina.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class GrabadorFalso implements Grabador {
  GrabadorFalso({this.dejar = true, this.audio});
  final bool dejar;
  final Uint8List? audio;
  bool empezo = false, solto = false;
  @override
  Future<bool> permiso() async => dejar;
  @override
  Future<void> empezar() async => empezo = true;
  @override
  Future<(Uint8List, String)?> parar() async => audio == null ? null : (audio!, 'audio/wav');
  @override
  Future<void> soltar() async => solto = true;
}

http.Response _json(Object d, [int s = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(d)), s, headers: {'content-type': 'application/json'});

Json _pista(String vid, String titulo, String artista, {bool video = false}) =>
    {'video_id': vid, 'titulo': titulo, 'artista': artista, 'es_video': video, 'miniatura': ''};

void main() {
  setUp(ServicioQueSuena.olvidar);

  group('lógica', () {
    test('lee la respuesta de /api/reconocer', () {
      final r = ResultadoQueSuena.desde({'encontrada': true, 'titulo': 'Zoo', 'artista': 'Shakira', 'anio': '2025',
          'portada': 'javascript:1', 'video_id': 'WTRm-Yr5Foo'});
      expect(r.encontrada, isTrue);
      expect(r.consulta, 'Shakira Zoo');
      expect(r.portada, '');
      expect(r.videoId, 'WTRm-Yr5Foo');
      expect(ResultadoQueSuena.desde({'encontrada': false}).encontrada, isFalse);
      expect(ResultadoQueSuena.desde({'encontrada': true, 'titulo': ''}).encontrada, isFalse);
      expect(ResultadoQueSuena.desde('x').encontrada, isFalse);
    });

    test('elige la versión que más se parece (canción antes que videoclip)', () {
      final l = ordenarParecidos([
        _pista('a', 'Despacito (Official Video)', 'Luis Fonsi', video: true),
        _pista('b', 'Otra cosa', 'Alguien'),
        _pista('c', 'Despacito', 'Luis Fonsi, Daddy Yankee'),
      ], 'Despacito', 'Luis Fonsi, Daddy Yankee');
      expect(l.map((p) => p['video_id']), ['c', 'a', 'b']);
      expect(parecido(_pista('x', 'Canción', 'Rosalía'), 'cancion', 'ROSALIA'), greaterThan(8));
    });

    test('pistas: busca en Caudal y pone primero el video que dio el servicio', () async {
      final r = ResultadoQueSuena.desde({'encontrada': true, 'titulo': 'Despacito', 'artista': 'Luis Fonsi', 'video_id': 'kJQP7kiw5Fk'});
      var buscado = '';
      var l = await pistasDeResultado(r, buscar: (t) async {
        buscado = t;
        return [_pista('zzzzzzzzzzz', 'Despacito', 'Luis Fonsi'), _pista('kJQP7kiw5Fk', 'Despacito (Video)', 'Luis Fonsi', video: true)];
      });
      expect(buscado, 'Luis Fonsi Despacito');
      expect(l.first['video_id'], 'kJQP7kiw5Fk');
      expect(l.length, 2);
      l = await pistasDeResultado(r, buscar: (_) async => throw Exception('sin red'));
      expect(l.single['video_id'], 'kJQP7kiw5Fk', reason: 'sin búsqueda, el del servicio');
      expect(l.single['titulo'], 'Despacito');
      expect(await pistasDeResultado(ResultadoQueSuena.nada, buscar: (_) async => []), isEmpty);
    });

    test('servicio: disponible, reconocer y errores', () async {
      late http.Request ultima;
      var respuesta = _json({'disponible': true, 'servicio': 'audd'});
      final s = ServicioQueSuena(cliente: MockClient((req) async {
        ultima = req;
        return respuesta;
      }));
      expect(await s.disponible(), isTrue);
      respuesta = _json({'encontrada': true, 'titulo': 'Zoo', 'artista': 'Shakira'});
      final r = await s.reconocer(Uint8List(9000));
      expect(r.titulo, 'Zoo');
      expect(ultima.method, 'POST');
      expect(ultima.headers['content-type'], startsWith('audio/wav'));
      expect(ultima.bodyBytes.length, 9000);
      respuesta = _json({'mensaje': 'Ya probaste muchas veces seguidas.'}, 429);
      await expectLater(() => s.reconocer(Uint8List(9000)),
          throwsA(isA<ErrorQueSuena>().having((e) => e.mensaje, 'mensaje', 'Ya probaste muchas veces seguidas.')));
      respuesta = _json({'disponible': false, 'mensaje': 'x'}, 503);
      await expectLater(s.reconocer(Uint8List(9000)),
          throwsA(isA<ErrorQueSuena>().having((e) => e.mensaje, 'mensaje', textoNoDisponible)));
      expect(await s.disponible(), isFalse, reason: 'se acuerda de que no está');
    });

    test('sin clave en el servidor: no disponible', () async {
      final s = ServicioQueSuena(cliente: MockClient((_) async => _json({'disponible': false, 'servicio': ''})));
      expect(await s.disponible(), isFalse);
    });
  });

  group('pantalla', () {
    Future<void> montar(WidgetTester t, Widget w) async {
      await t.pumpWidget(MaterialApp(home: w));
      await t.pump();
      await t.pump();
    }

    testWidgets('sin clave explica en una frase que aún no está', (t) async {
      final s = ServicioQueSuena(cliente: MockClient((_) async => _json({'disponible': false})));
      await montar(t, QueSuenaPagina(servicio: s, grabador: GrabadorFalso.new));
      expect(find.text(textoNoDisponible), findsOneWidget);
      await t.tap(find.byIcon(Icons.mic_rounded));
      await t.pump();
      expect(find.text('Escuchando…'), findsNothing);
    });

    testWidgets('escucha, reconoce y deja reproducirla o ponerla en la cola', (t) async {
      final s = ServicioQueSuena(cliente: MockClient((req) async => req.method == 'GET'
          ? _json({'disponible': true})
          : _json({'encontrada': true, 'titulo': 'Zoo', 'artista': 'Shakira', 'album': 'Zootopia 2', 'anio': '2025'})));
      final g = GrabadorFalso(audio: Uint8List(20000));
      final sonadas = <String>[], encoladas = <String>[];
      await montar(
          t,
          QueSuenaPagina(
            servicio: s, grabador: () => g, segundos: 2,
            buscar: (_) async => [_pista('WTRm-Yr5Foo', 'Zoo', 'Shakira'), _pista('otraotraotr', 'Zoo (Live)', 'Shakira')],
            alReproducir: (p) => sonadas.add('${p['video_id']}'),
            alACola: (p) => encoladas.add('${p['video_id']}'),
          ));
      expect(find.text('Toca para escuchar'), findsOneWidget);
      await t.tap(find.byIcon(Icons.mic_rounded));
      await t.pump();
      expect(g.empezo, isTrue);
      expect(find.text('Escuchando…'), findsOneWidget);
      await t.pump(const Duration(seconds: 1));
      await t.pump(const Duration(seconds: 1));
      await t.pumpAndSettle();
      expect(find.text('¡La encontramos!'), findsOneWidget);
      expect(find.text('Zoo'), findsOneWidget);
      expect(find.text('Otras versiones'), findsOneWidget);
      expect(g.solto, isTrue);
      await t.tap(find.text('Reproducir').first);
      await t.tap(find.text('Añadir a la cola'));
      expect(sonadas, ['WTRm-Yr5Foo']);
      expect(encoladas, ['WTRm-Yr5Foo']);
    });

    testWidgets('sin permiso del micrófono lo explica', (t) async {
      final s = ServicioQueSuena(cliente: MockClient((_) async => _json({'disponible': true})));
      await montar(t, QueSuenaPagina(servicio: s, grabador: () => GrabadorFalso(dejar: false)));
      await t.tap(find.byIcon(Icons.mic_rounded));
      await t.pump();
      await t.pump();
      expect(find.textContaining('permiso para usar el micrófono'), findsOneWidget);
    });

    testWidgets('no la reconoce', (t) async {
      final s = ServicioQueSuena(cliente: MockClient((req) async =>
          req.method == 'GET' ? _json({'disponible': true}) : _json({'encontrada': false})));
      await montar(t, QueSuenaPagina(servicio: s, grabador: () => GrabadorFalso(audio: Uint8List(20000)), segundos: 1));
      await t.tap(find.byIcon(Icons.mic_rounded));
      await t.pump();
      await t.pump(const Duration(seconds: 1));
      await t.pumpAndSettle();
      expect(find.textContaining('No la reconocimos'), findsOneWidget);
    });
  });
}
