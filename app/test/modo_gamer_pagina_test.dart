// La pantalla «Modo gamer»: que se vea completa, que no desborde en 320x568
// (ni con letra grande), que los controles funcionen y que el borde RGB respete
// «quitar animaciones».
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/gamer.dart';
import 'package:caudal/nucleo/gamer_control.dart';
import 'package:caudal/ui/paginas/modo_gamer_pagina.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Map<String, dynamic> pista(String id) => {'clave': 'yt:$id', 'video_id': id, 'titulo': id, 'artista': 'Ana'};

void main() {
  late Ajustes a;
  late ModoGamerControl g;
  late List<String> lanzadas;
  late List<Situacion> pedidas;

  Future<void> montar(
    WidgetTester t, {
    Size tam = const Size(320, 568),
    double letra = 1.0,
    bool sinAnimaciones = false,
    Map<String, Object> prefs = const {},
    Future<List<Map<String, dynamic>>> Function(Situacion)? buscar,
  }) async {
    SharedPreferences.setMockInitialValues(prefs);
    a = await Ajustes.cargar('t');
    lanzadas = [];
    pedidas = [];
    g = ModoGamerControl(
      ajustes: a,
      aplicarSonido: () async {},
      lanzar: (p, c) async => lanzadas.add('${c['titulo']}'),
      reloj: () => DateTime(2026, 11, 19, 20),
      buscarPistas: buscar ??
          (s) async {
            pedidas.add(s);
            return [pista('x1'), pista('x2')];
          },
    );
    t.view.physicalSize = tam;
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.reset);
    await t.pumpWidget(MaterialApp(
      theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory), // sin el shader de InkSparkle (no corre en pruebas)
      builder: (context, hijo) {
        final mq = MediaQuery.of(context);
        return MediaQuery(
            data: mq.copyWith(textScaler: TextScaler.linear(letra), disableAnimations: sinAnimaciones), child: hijo!);
      },
      home: ModoGamerPagina(control: g),
    ));
    await t.pump();
  }

  // sin pumpAndSettle: el borde RGB anima para siempre
  Future<void> bajarHasta(WidgetTester t, Finder f) async {
    for (var i = 0; i < 20 && f.hitTestable().evaluate().isEmpty; i++) {
      await t.drag(find.byType(Scrollable).first, const Offset(0, -150));
      await t.pump();
    }
  }

  // cierra la pantalla (para el reloj del borde) y libera el control
  Future<void> cerrar(WidgetTester t) async {
    await t.pumpWidget(const SizedBox());
    g.dispose();
  }

  testWidgets('apagado: se ve lo principal y lo demás queda bloqueado', (t) async {
    await montar(t);
    expect(find.text('Modo gamer'), findsWidgets);
    expect(find.text('Nivel 1'), findsOneWidget);
    expect(find.byType(Switch), findsWidgets);
    expect(t.takeException(), isNull);
    // las listas no se pueden pulsar con el modo apagado
    await bajarHasta(t, find.text('Lobby'));
    await t.tap(find.text('Lobby'), warnIfMissed: false);
    await t.pump();
    expect(pedidas, isEmpty);
    await cerrar(t);
  });

  for (final (nombre, tam, letra) in [
    ('320x568', const Size(320, 568), 1.0),
    ('320x568 con letra grande', const Size(320, 568), 1.2),
    ('360x640', const Size(360, 640), 1.0),
    ('tableta 800x1200', const Size(800, 1200), 1.0),
  ]) {
    testWidgets('no desborda en $nombre (activo, de arriba abajo)', (t) async {
      await montar(t, tam: tam, letra: letra, prefs: {'aj.t.gamer_activo': true, 'aj.t.gamer_sonido': 'fps'});
      await g.activar(false);
      await g.activar(true);
      await t.pump();
      final lista = find.byType(Scrollable).first;
      expect(t.takeException(), isNull);
      for (var i = 0; i < 12; i++) {
        await t.drag(lista, const Offset(0, -260));
        await t.pump();
        expect(t.takeException(), isNull, reason: 'al bajar, paso $i');
      }
      expect(find.text('Derrota'), findsOneWidget);
      await cerrar(t);
    });
  }

  testWidgets('el interruptor enciende el modo, el ahorro y esconde mascotas', (t) async {
    await montar(t);
    final sw = find.byType(Switch).first;
    await t.tap(sw);
    await t.pump();
    await t.pump(const Duration(milliseconds: 300));
    expect(g.activo, isTrue);
    expect(a.sino('modo_ligero'), isTrue);
    expect(ModoGamerControl.mascotasOcultas.value, isTrue);
    await t.tap(sw);
    await t.pump();
    await t.pump(const Duration(milliseconds: 300));
    expect(g.activo, isFalse);
    expect(a.sino('modo_ligero'), isFalse);
    expect(ModoGamerControl.mascotasOcultas.value, isFalse);
    await cerrar(t);
  });

  testWidgets('perfil de sonido: se elige y se quita', (t) async {
    await montar(t, prefs: {'aj.t.gamer_activo': true});
    await bajarHasta(t, find.text('Carreras').first);
    await t.tap(find.widgetWithText(ChoiceChip, 'Carreras'));
    await t.pump();
    expect(g.perfil?.id, 'carreras');
    expect(a.sino('ecualizador'), isTrue);
    await t.tap(find.widgetWithText(ChoiceChip, 'Carreras'));
    await t.pump();
    expect(g.perfil, isNull);
    expect(a.sino('ecualizador'), isFalse);
    await cerrar(t);
  });

  testWidgets('una situación arranca su lista', (t) async {
    await montar(t, prefs: {'aj.t.gamer_activo': true});
    await bajarHasta(t, find.text('Clutch'));
    await t.tap(find.text('Clutch'));
    await t.pump();
    await t.pump();
    expect(pedidas, [Situacion.clutch]);
    expect(lanzadas, ['Modo gamer · Clutch']);
    await cerrar(t);
  });

  testWidgets('si falla la lista se avisa con un SnackBar', (t) async {
    await montar(t, prefs: {'aj.t.gamer_activo': true}, buscar: (s) async => throw Exception('sin red'));
    await bajarHasta(t, find.text('Victoria'));
    await t.tap(find.text('Victoria'));
    await t.pump();
    await t.pump();
    expect(find.byType(SnackBar), findsOneWidget);
    expect(find.textContaining('Victoria'), findsWidgets);
    await t.pump(const Duration(seconds: 7));
    await cerrar(t);
  });

  testWidgets('borde RGB: gira activo y se queda quieto con «quitar animaciones»', (t) async {
    await montar(t, prefs: {'aj.t.gamer_activo': true});
    expect(find.byType(BordeRgb), findsNWidgets(2));
    expect(t.hasRunningAnimations, isTrue);
    await cerrar(t);

    await montar(t, prefs: {'aj.t.gamer_activo': true}, sinAnimaciones: true);
    expect(t.hasRunningAnimations, isFalse);
    await cerrar(t);

    // apagado el modo, el borde tampoco gira (ahorra batería)
    await montar(t);
    expect(t.hasRunningAnimations, isFalse);
    await cerrar(t);
  });

  testWidgets('el nivel y las misiones salen del progreso guardado', (t) async {
    await montar(t, prefs: {
      'aj.t.gamer_activo': true,
      'aj.t.gamer_progreso': '{"xp":500,"d":"2026-11-19","sh":600,"r":4,"ud":"2026-11-19",'
          '"ds":["2026-11-16","2026-11-17","2026-11-18","2026-11-19"]}',
    });
    // 500 XP = nivel 5 exacto con la fórmula de la PC (25 · n · (n-1))
    expect(find.text('Nivel 5'), findsOneWidget);
    expect(find.text('4 días de racha'), findsOneWidget);
    expect(find.text('10 min hoy'), findsOneWidget);
    expect(find.text('Misiones de hoy'), findsOneWidget);
    await cerrar(t);
  });
}
