// Caudal móvil 2.1.2: colores propios (como el escritorio) y el chat que
// envía al momento, con reintento y «Enviar lo que suena».
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/chat.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/paginas/aspecto_pagina.dart';
import 'package:caudal/ui/paginas/mensajes_pagina.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _Reproductor extends ChangeNotifier implements Reproductor {
  @override
  Json? actual;
  @override
  EstadoRepro estado = EstadoRepro.parado;
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(Duration.zero);
  @override
  Future<void> dispose() async => super.dispose();
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Coleccion extends ChangeNotifier implements Coleccion {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Streams implements Streams {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Descargas extends ChangeNotifier implements GestorDescargas {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// La nube en memoria: guarda lo enviado y puede fallar a voluntad.
class _Sesion extends Sesion {
  _Sesion() : super('yo', 'token', 'r', DateTime.now().add(const Duration(hours: 1)));
  final enviados = <Map>[];
  bool falla = false;

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    if (ruta.startsWith('mensajes?')) return [];
    if (ruta == 'rpc/marcar_leido') return null;
    if (ruta == 'mensajes' && metodo == 'POST') {
      if (falla) throw const ErrorNube('Sin conexión. Revisa tu internet.');
      final c = Map<String, dynamic>.from(cuerpo as Map);
      final fila = {'id': enviados.length + 1, 'autor': 'yo', 'texto': c['texto'], 'pista': c['pista'],
        'creado': DateTime.now().toUtc().toIso8601String()};
      enviados.add(fila);
      return [fila];
    }
    return null;
  }
}

late _Reproductor _r;
late _Sesion _nube;
late Ajustes _ajustes;

Future<void> _montar(WidgetTester t, Widget pagina) async {
  SharedPreferences.setMockInitialValues({});
  _ajustes = await Ajustes.cargar('prueba');
  _r = _Reproductor();
  _nube = _Sesion();
  final s = Servicios(
    cuenta: Cuenta(id: 'yo', usuario: 'yo', nombre: 'Yo', sesion: _nube),
    ajustes: _ajustes,
    coleccion: _Coleccion(),
    reproductor: _r,
    streams: _Streams(),
    descargas: _Descargas(),
    cerrarSesion: () async {},
  );
  t.view.physicalSize = const Size(1080, 2400);
  t.view.devicePixelRatio = 2.75;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(s: s, child: MaterialApp(theme: temaCaudal(), home: pagina)));
  await t.pump(const Duration(milliseconds: 300));
}

final _chat = ResumenChat.desde({'id': 'c1', 'otro': 'o', 'usuario': 'luis', 'nombre': 'Luis',
  'ultimo': '2026-11-14T10:00:00Z'}, 'yo');

void main() {
  group('colores propios', () {
    test('un color propio se calcula igual que en el escritorio', () {
      final a = Aspecto.acentoDe('#A3E635');
      expect(a.$1, 'Tu color');
      expect(a.$2, const Color(0xFFA3E635));
      expect(a.$4.computeLuminance(), lessThan(0.05)); // texto oscuro sobre un acento claro
      expect(Aspecto.acentoDe('#1E3A8A').$4, Colors.white); // y blanco sobre uno oscuro
      // muy oscuro: se aclara para que se vea
      expect(Aspecto.acentoDe('#050505').$2.computeLuminance(), greaterThanOrEqualTo(0.10));
      final f = Aspecto.fondoDe('#FFFFFF');
      expect(f.$1, 'Tu fondo');
      expect(f.$2.first.computeLuminance(), lessThanOrEqualTo(0.035)); // el fondo siempre oscuro
      expect(f.$2.length, 6);
      expect(Aspecto.hexDe(const Color(0xFF12AB9C)), '#12AB9C');
      expect(Aspecto.esPropio('rosa'), isFalse);
      expect(Aspecto.esPropio('#12AB9C'), isTrue);
      Aspecto.aplicar('#A3E635', '#3B1F0F');
      expect(C.acento, const Color(0xFFA3E635));
      Aspecto.aplicar('cian', 'oscuro');
      expect(C.acento, const Color(0xFF22D3EE));
    });

    testWidgets('elegir tu propio color desde Aspecto', (t) async {
      await _montar(t, const AspectoPagina());
      expect(find.text('Elegir…'), findsNWidgets(2)); // color y fondo
      await t.tap(find.text('Elegir…').first);
      await t.pumpAndSettle();
      expect(find.byType(SelectorColor), findsOneWidget);
      await t.tap(find.text('Usar este'));
      await t.pumpAndSettle();
      expect(Aspecto.esPropio(_ajustes.texto('acento')), isTrue);
      expect(find.text('Tu color'), findsWidgets);
      await t.scrollUntilVisible(find.text('Volver al aspecto de siempre'), 200,
          scrollable: find.byType(Scrollable).first);
      await t.ensureVisible(find.text('Volver al aspecto de siempre'));
      await t.pumpAndSettle();
      await t.tap(find.text('Volver al aspecto de siempre'));
      await t.pumpAndSettle();
      expect(_ajustes.texto('acento'), 'cian');
    });
  });

  group('chat', () {
    testWidgets('el mensaje se ve al momento y se confirma', (t) async {
      await _montar(t, ConversacionPagina(chat: _chat));
      await t.pump(const Duration(milliseconds: 100));
      expect(find.textContaining('Aquí empieza tu conversación con Luis'), findsOneWidget);
      await t.enterText(find.byType(TextField), 'hola');
      await t.pump();
      await t.tap(find.byTooltip('Enviar'));
      await t.pump();
      expect(find.text('hola'), findsOneWidget);
      await t.pump(const Duration(milliseconds: 50));
      expect(_nube.enviados.map((e) => e['texto']), ['hola']);
      expect(find.text('Enviando…'), findsNothing);
    });

    testWidgets('sin red ofrece reintentar y luego se envía', (t) async {
      await _montar(t, ConversacionPagina(chat: _chat));
      _nube.falla = true;
      await t.enterText(find.byType(TextField), 'sin red');
      await t.pump();
      await t.tap(find.byTooltip('Enviar'));
      await t.pump(const Duration(milliseconds: 50));
      expect(find.textContaining('Toca para reintentar'), findsOneWidget);
      _nube.falla = false;
      await t.tap(find.textContaining('Toca para reintentar'));
      await t.pump(const Duration(milliseconds: 50));
      expect(find.textContaining('Toca para reintentar'), findsNothing);
      expect(_nube.enviados.map((e) => e['texto']), ['sin red']);
    });

    testWidgets('«Enviar lo que suena» siempre a mano y explica si no puede', (t) async {
      await _montar(t, ConversacionPagina(chat: _chat));
      final boton = find.byIcon(Icons.music_note_rounded);
      expect(boton, findsOneWidget); // visible aunque no suene nada
      await t.tap(boton);
      await t.pump();
      expect(_nube.enviados, isEmpty);
      _r.actual = {'tipo': 'pista', 'video_id': 'abc12345678', 'titulo': 'Canción X', 'artista': 'Y',
        'clave': 'yt:abc12345678', 'miniatura': ''};
      _r.notifyListeners();
      await t.pump();
      await t.tap(boton);
      await t.pump(const Duration(milliseconds: 50));
      expect(_nube.enviados.length, 1);
      expect((_nube.enviados.first['pista'] as Map)['video_id'], 'abc12345678');
    });
  });
}
