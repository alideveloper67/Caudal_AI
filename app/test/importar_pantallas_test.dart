// Las pantallas de «Traer una lista» y «Pasar tus me gusta»: dicen qué pasa y qué
// hacer, enseñan el avance «1 240 de 5 300» y no se desbordan en un teléfono chico.
import 'dart:convert';

import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/importacion.dart';
import 'package:caudal/nucleo/servicios_externos.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/paginas/importar_pagina.dart';
import 'package:caudal/ui/paginas/me_gusta_externos_pagina.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class _ReproductorFalso extends ChangeNotifier implements Reproductor {
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(Duration.zero);
  @override
  Future<void> dispose() async => super.dispose();
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StreamsFalsos implements Streams {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _DescargasFalsas extends ChangeNotifier implements GestorDescargas {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ColeccionFalsa extends ChangeNotifier implements Coleccion {
  final estados = <String, Object?>{};
  @override
  Future<dynamic> estado(String clave) async => estados[clave];
  @override
  Future<void> guardarEstado(String clave, Object? valor) async => estados[clave] = valor;
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

late _ColeccionFalsa _col;

// 320 px de ancho (lo que se comprueba) y alto suficiente para que las pantallas
// entren enteras: las listas son perezosas y lo que queda debajo no existe en el árbol
Future<void> _montar(WidgetTester t, Widget pagina, {Size tam = const Size(880, 3600)}) async {
  SharedPreferences.setMockInitialValues(_prefs);
  final ajustes = await Ajustes.cargar('prueba');
  _col = _ColeccionFalsa();
  final s = Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
    ajustes: ajustes,
    coleccion: _col,
    reproductor: _ReproductorFalso(),
    streams: _StreamsFalsos(),
    descargas: _DescargasFalsas(),
    cerrarSesion: () async {},
  );
  t.view.physicalSize = tam;
  t.view.devicePixelRatio = 2.75;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(s: s, child: MaterialApp(theme: temaCaudal(), home: pagina)));
  await t.pump(const Duration(milliseconds: 300));
}

Map<String, Object> _prefs = {};

void main() {
  setUp(() {
    // el portapapeles vacío
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, (c) async => null);
    ServiciosExternos.olvidarConfig();
  });

  testWidgets('Traer una lista: SoundCloud, elegir Me gusta y sin desbordes en 320 px', (t) async {
    await _montar(t, const ImportarPagina());
    expect(find.text('SoundCloud'), findsOneWidget);
    expect(find.text('Una lista nueva'), findsOneWidget);
    await t.tap(find.text('Mis Me gusta'));
    await t.pump();
    expect(find.text('Pasar a Me gusta'), findsOneWidget);
    expect(find.text('Vincular Spotify, YouTube Music o SoundCloud'), findsOneWidget);
    expect(t.takeException(), isNull);
  });

  testWidgets('enseña el avance de una importación grande con los miles separados', (t) async {
    final tr = TrabajoImportacion.i
      ..enMarcha = true
      ..aMeGusta = false
      ..titulo = 'Enorme'
      ..hechas = 1240
      ..total = 5300
      ..encontradas = 1198;
    await _montar(t, const ImportarPagina());
    expect(find.text('Pasando canciones a la lista «Enorme»'), findsOneWidget);
    expect(find.textContaining('1 240 de 5 300 canciones'), findsOneWidget);
    expect(find.textContaining('Puedes salir de aquí'), findsOneWidget);
    expect(find.text('Pausar'), findsOneWidget);
    tr.enMarcha = false;
    tr.olvidarTerminado();
  });

  testWidgets('Vincular cuentas sin activar: cada servicio dice cómo traerlos ya, sin desbordes', (t) async {
    ServiciosExternos.pedir = (u) async => http.Response('<html>no existe</html>', 404);
    await _montar(t, const MeGustaExternosPagina());
    await t.pump(const Duration(milliseconds: 300));
    expect(find.text('Pedirlo a Spotify'), findsOneWidget);
    expect(find.text('Vincular Spotify'), findsNothing);
    await t.scrollUntilVisible(find.text('Abrir Google Takeout'), 200, scrollable: find.byType(Scrollable).first);
    await t.scrollUntilVisible(find.text('Otro archivo o una lista de nombres'), 200, scrollable: find.byType(Scrollable).first);
    expect(t.takeException(), isNull);
  });

  testWidgets('con las conexiones activadas ofrece vincular los tres', (t) async {
    ServiciosExternos.pedir = (u) async => http.Response(
        jsonEncode({'spotify_client_id': 'a', 'youtube_client_id': 'b', 'soundcloud_client_id': 'c', 'soundcloud': true}), 200);
    await _montar(t, const MeGustaExternosPagina());
    await t.pump(const Duration(milliseconds: 300));
    for (final s in ['Spotify', 'YouTube Music', 'SoundCloud']) {
      await t.scrollUntilVisible(find.text('Vincular $s'), 200, scrollable: find.byType(Scrollable).first);
    }
    await t.scrollUntilVisible(find.text('Traer sus me gusta'), 200, scrollable: find.byType(Scrollable).first);
    expect(t.takeException(), isNull);
  });

  testWidgets('una cuenta vinculada enseña su estado, mantener al día y desvincular', (t) async {
    ServiciosExternos.pedir = (u) async => http.Response(jsonEncode({'spotify_client_id': 'a'}), 200);
    _prefs = {'vinculada.${CuentaExterna.deCaudal}.spotify': jsonEncode({'access': 'A', 'refresh': 'R', 'caduca': 0})};
    await _montar(t, const MeGustaExternosPagina());
    await t.pump(const Duration(milliseconds: 300));
    expect(find.textContaining('Vinculada'), findsOneWidget);
    expect(find.text('Mantener al día'), findsOneWidget);
    expect(find.text('Sincronizar ahora'), findsOneWidget);
    await t.tap(find.text('Desvincular'));
    await t.pumpAndSettle();
    expect(find.textContaining('se quedan'), findsOneWidget);
    await t.tap(find.widgetWithText(FilledButton, 'Desvincular'));
    await t.pumpAndSettle();
    expect(find.text('Vincular Spotify'), findsOneWidget);
    _prefs = {};
    expect(t.takeException(), isNull);
  });
}
