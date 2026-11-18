import 'dart:convert';

import 'package:caudal/nucleo/avisos.dart';
import 'package:caudal/ui/paginas/aviso_dialogo.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));

  http.Client servidor(Object cuerpo, {int codigo = 200}) => MockClient((_) async =>
      http.Response(jsonEncode(cuerpo), codigo, headers: {'content-type': 'application/json; charset=utf-8'}));

  final filas = [
    {'id': 1, 'titulo': 'Para todos', 'texto': 'Hola a todos', 'plataformas': ['todas']},
    {
      'id': 2,
      'titulo': 'Solo web',
      'texto': 'La web no está tan optimizada',
      'plataformas': ['web'],
      'enlace': 'https://caudal-musica.netlify.app',
      'etiqueta_enlace': 'Descargar'
    },
    {'id': 3, 'titulo': 'Solo Windows', 'texto': 'Actualiza', 'plataformas': ['windows']},
    {'id': 4, 'titulo': '', 'texto': 'sin título no sirve', 'plataformas': ['todas']},
    {'id': 5, 'titulo': 'Enlace raro', 'texto': 'no es https', 'plataformas': ['todas'], 'enlace': 'javascript:alert(1)'},
  ];

  test('cada plataforma recibe solo lo suyo y lo que no sirve se descarta', () async {
    final web = await Avisos.pendientes(plat: 'web', cliente: servidor(filas));
    expect(web.map((a) => a.id), [1, 2, 5]);
    final win = await Avisos.pendientes(plat: 'windows', cliente: servidor(filas));
    expect(win.map((a) => a.id), [1, 3, 5]);
    final android = await Avisos.pendientes(plat: 'android', cliente: servidor(filas));
    expect(android.map((a) => a.id), [1, 5]);
  });

  test('el enlace solo vale si es https', () async {
    final web = await Avisos.pendientes(plat: 'web', cliente: servidor(filas));
    expect(web.firstWhere((a) => a.id == 2).enlace, 'https://caudal-musica.netlify.app');
    expect(web.firstWhere((a) => a.id == 2).etiquetaEnlace, 'Descargar');
    expect(web.firstWhere((a) => a.id == 5).enlace, isNull);
  });

  test('un aviso visto no vuelve a salir', () async {
    await Avisos.marcarVisto(2);
    final web = await Avisos.pendientes(plat: 'web', cliente: servidor(filas));
    expect(web.map((a) => a.id), [1, 5]);
  });

  test('sin conexión o con un fallo del servidor no sale nada y no se rompe', () async {
    expect(await Avisos.pendientes(plat: 'web', cliente: MockClient((_) async => throw Exception('sin red'))), isEmpty);
    expect(await Avisos.pendientes(plat: 'web', cliente: servidor({'error': 'x'}, codigo: 500)), isEmpty);
    expect(await Avisos.pendientes(plat: 'web', cliente: servidor({'no': 'es lista'})), isEmpty);
  });

  testWidgets('el diálogo muestra el aviso y al cerrarlo queda como visto', (t) async {
    const a = AvisoCaudal(
        id: 9,
        titulo: 'Estás en la web',
        texto: 'Menos optimizada que las apps',
        plataformas: ['web'],
        enlace: 'https://x.pe',
        etiquetaEnlace: 'Descargar');
    await t.pumpWidget(MaterialApp(
        home: Builder(builder: (c) => TextButton(onPressed: () => mostrarAviso(c, a), child: const Text('abrir')))));
    await t.tap(find.text('abrir'));
    await t.pumpAndSettle();
    expect(find.text('Estás en la web'), findsOneWidget);
    expect(find.text('Menos optimizada que las apps'), findsOneWidget);
    expect(find.text('Descargar'), findsOneWidget);
    await t.tap(find.text('Entendido'));
    await t.pumpAndSettle();
    expect(find.text('Estás en la web'), findsNothing);
    final otra = await Avisos.pendientes(
        plat: 'web',
        cliente: servidor([
          {'id': 9, 'titulo': 'Estás en la web', 'texto': 'x', 'plataformas': ['web']}
        ]));
    expect(otra, isEmpty);
  });
}
