import 'dart:io';

import 'package:caudal/nucleo/fondo_app.dart';
import 'package:caudal/nucleo/mascota_app.dart';
import 'package:caudal/ui/paginas/mascota_pagina.dart';
import 'package:caudal/ui/reproductor/mascota_barra.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  final texto = File('assets/mascotas/catalogo.json').readAsStringSync();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FondoApp.i.puede = false;
    MascotaApp.i.reiniciar();
  });

  test('el catálogo trae las 66 mascotas y sus hojas existen', () {
    final c = leerCatalogoMascotas(texto);
    expect(c.length, 66);
    expect(c.map((m) => m.clave).toSet().length, 66);
    expect(c.where((m) => m.arcoiris).map((m) => m.clave), ['nyan']);
    expect(c.map((m) => m.clave), containsAll(['nyan', 'nailong', 'pikachu', 'charmander', 'bulbasaur', 'squirtle', 'kirby', 'gato_negro', 'capibara', 'pochacco', 'caniche', 'zorro_aviador', 'robot', 'dragon', 'ajolote']));
    // personajes de noviembre
    expect(c.map((m) => m.clave), containsAll(['messi', 'wos', 'nightwing', 'goku_ultra', 'goku_blue', 'wanda', 'loki', 'jake', 'finn', 'marceline', 'pan_canela', 'rigby', 'steven', 'perla', 'lapislazuli', 'jaspe', 'garnet', 'peridot', 'amatista', 'leon', 'richard', 'gumball', 'darwin']));
    for (final quitada in ['stitch', 'minion', 'pooh', 'mickey', 'bob', 'patrick', 'pusheen', 'rilakkuma', 'toothless']) {
      expect(c.map((m) => m.clave), isNot(contains(quitada)));
    }
    for (final m in c) {
      expect(File(m.imagen).existsSync(), isTrue, reason: m.imagen);
    }
  });

  test('Nyan trae su arcoíris y las demás su estela, con dibujo', () {
    final c = leerCatalogoMascotas(texto);
    final nyan = c.firstWhere((m) => m.clave == 'nyan');
    expect(nyan.arcoiris, isTrue);
    expect(nyan.tieneEstela, isFalse);
    for (final m in c.where((m) => !m.arcoiris)) {
      expect(m.estela, isNotEmpty, reason: m.clave);
      expect(m.tieneEstela, isTrue, reason: m.clave);
      expect(m.estelaAncho, 11);
      expect(m.estelaAlto, 11);
      expect(File(m.imagenEstela).existsSync(), isTrue, reason: m.imagenEstela);
    }
  });

  test('cada hoja trae los cuadros que dice el catálogo (2 por defecto)', () {
    final c = leerCatalogoMascotas(texto);
    for (final m in c) {
      expect(m.cuadros, greaterThanOrEqualTo(2), reason: m.clave);
      final png = File(m.imagen).readAsBytesSync();
      // ancho del PNG: bytes 16..19 (big endian) de la cabecera IHDR
      final ancho = (png[16] << 24) | (png[17] << 16) | (png[18] << 8) | png[19];
      expect(ancho, m.ancho * m.cuadros * m.densidad, reason: m.clave);
    }
    final sinCampo = leerCatalogoMascotas('[{"clave":"x","nombre":"X","origen":"X","ancho":48,"alto":44}]');
    expect(sinCampo.single.cuadros, 2);
    expect(sinCampo.single.densidad, 1);
  });

  test('la vuelta de la animación se reparte en partes iguales entre los cuadros', () {
    expect([0.0, 0.49, 0.5, 0.99, 1.0].map((v) => cuadroDeMascota(v, 2)).toList(), [0, 0, 1, 1, 1]);
    expect([0.0, 0.17, 0.34, 0.5, 0.67, 0.84, 1.0].map((v) => cuadroDeMascota(v, 6)).toList(), [0, 1, 2, 3, 4, 5, 5]);
  });

  test('sin permiso no se muestra, aunque haya una elegida', () async {
    await MascotaApp.i.cargarCatalogo(texto: texto);
    await MascotaApp.i.iniciar('cuenta-a');
    await MascotaApp.i.elegir('pikachu'); // sin permiso no deja elegir
    expect(MascotaApp.i.clave, '');
    FondoApp.i.puede = true;
    await MascotaApp.i.elegir('pikachu');
    expect(MascotaApp.i.activa, isTrue);
    FondoApp.i.puede = false; // deja de ser donadora
    expect(MascotaApp.i.activa, isFalse);
  });

  test('la elección se guarda por cuenta y se limpia al cerrar sesión', () async {
    FondoApp.i.puede = true;
    await MascotaApp.i.cargarCatalogo(texto: texto);
    await MascotaApp.i.iniciar('cuenta-a');
    await MascotaApp.i.elegir('robot');
    await MascotaApp.i.iniciar('cuenta-b');
    expect(MascotaApp.i.clave, '');
    await MascotaApp.i.elegir('kirby');
    MascotaApp.i.reiniciar();
    expect(MascotaApp.i.clave, '');
    await MascotaApp.i.iniciar('cuenta-a');
    expect(MascotaApp.i.clave, 'robot');
    await MascotaApp.i.elegir('');
    await MascotaApp.i.iniciar('cuenta-a');
    expect(MascotaApp.i.clave, '');
    await MascotaApp.i.iniciar('cuenta-b');
    expect(MascotaApp.i.clave, 'kirby');
  });

  for (final (nombre, tam, dpr) in const <(String, Size, double)>[
    ('telefono chico', Size(320, 568), 2.0),
    ('telefono', Size(412, 915), 2.6),
    ('escritorio', Size(1440, 900), 1.0),
  ]) {
    testWidgets('pantalla de mascotas · $nombre', (t) async {
      t.view.physicalSize = tam * dpr;
      t.view.devicePixelRatio = dpr;
      addTearDown(t.view.reset);
      await MascotaApp.i.cargarCatalogo(texto: texto);
      FondoApp.i.puede = true;
      FondoApp.i.titulo = 'Donador de Caudal';
      await t.pumpWidget(MaterialApp(theme: temaCaudal(), home: const MascotaPagina()));
      await t.pump();
      expect(find.text('Mascotita del reproductor'), findsOneWidget);
      expect(find.text('Pikachu', skipOffstage: false), findsOneWidget);
      expect(t.takeException(), isNull);

      FondoApp.i.puede = false;
      await t.pumpWidget(MaterialApp(key: UniqueKey(), theme: temaCaudal(), home: const MascotaPagina()));
      await t.pump();
      expect(find.textContaining('Exclusiva para donadores y fundadores de Caudal'), findsOneWidget);
      expect(t.takeException(), isNull);
    });
  }

  test('una mascota exclusiva solo la ve y la elige su cuenta', () async {
    await MascotaApp.i.cargarCatalogo(texto: texto);
    final exclusiva = MascotaApp.i.catalogo.where((m) => m.esExclusiva).toList();
    expect(exclusiva.map((m) => m.clave), ['caniche']);
    expect(exclusiva.single.soloCuentas.length, 3); // cochayuyo y las dos cuentas fundadoras
    final duena = exclusiva.single.soloCuentas.first;

    FondoApp.i.puede = false;
    await MascotaApp.i.iniciar(duena);
    expect(MascotaApp.i.disponibles.map((m) => m.clave), contains('caniche'));
    expect(MascotaApp.i.tieneExclusivas, isTrue);
    await MascotaApp.i.elegir('kirby');
    expect(MascotaApp.i.clave, isNot('kirby'));
    await MascotaApp.i.elegir('caniche');
    expect(MascotaApp.i.activa, isTrue);
    await MascotaApp.i.elegir('');

    FondoApp.i.puede = true;
    await MascotaApp.i.iniciar('otra-cuenta');
    expect(MascotaApp.i.disponibles.map((m) => m.clave), isNot(contains('caniche')));
    await MascotaApp.i.elegir('caniche');
    expect(MascotaApp.i.clave, isNot('caniche'));
    MascotaApp.i.reiniciar();
  });
}
