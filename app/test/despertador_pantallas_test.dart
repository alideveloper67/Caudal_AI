import 'package:caudal/nucleo/despertador.dart';
import 'package:caudal/nucleo/despertador_control.dart';
import 'package:caudal/nucleo/despertador_nativo.dart';
import 'package:caudal/nucleo/letra_pantalla_bloqueo.dart';
import 'package:caudal/nucleo/plataforma.dart';
import 'package:caudal/ui/paginas/despertador_ajuste.dart';
import 'package:caudal/ui/paginas/despertador_pagina.dart';
import 'package:caudal/ui/paginas/despertador_sonando.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _Canal extends CanalDespertador {
  _Canal(this.p);
  final PermisosDespertador p;
  final abiertos = <String>[];

  @override
  bool get disponible => true;
  @override
  Future<void> programar(Map<String, dynamic> datos) async {}
  @override
  Future<Map<String, dynamic>?> leer() async => null;
  @override
  Future<PermisosDespertador> permisos() async => p;
  @override
  Future<void> abrirAjuste(String cual) async => abiertos.add(cual);
}

class _Puente extends PuenteLetraBloqueo {
  @override
  Future<void> mostrar(Map<String, Object?> datos) async {}
  @override
  Future<void> quitar() async {}
}

Widget _app(Widget w) => MaterialApp(home: w);

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));
  tearDown(() => Plataforma.forzada = null);

  testWidgets('la lista enseña las alarmas, cuánto falta y lo que falta permitir', (t) async {
    Plataforma.forzada = TargetPlatform.android;
    final canal = _Canal(const PermisosDespertador(exactas: false));
    final c = ControlDespertador(canal: canal)
      ..alarmas = [
        const Alarma(id: 'a', hora: 7, minuto: 5, dias: {1, 2, 3, 4, 5}),
        const Alarma(id: 'b', hora: 6, minuto: 0, dias: {}, activa: false, fuente: FuenteAlarma.tono),
      ]
      ..cargadas = true;
    await t.pumpWidget(_app(DespertadorPagina(control: c)));
    await t.pump();
    expect(find.text('07:05'), findsOneWidget);
    expect(find.text('06:00'), findsOneWidget);
    expect(find.textContaining('Entre semana'), findsOneWidget);
    expect(find.textContaining('Una vez · Sonido suave de Caudal'), findsOneWidget);
    expect(find.textContaining('Suena en'), findsOneWidget);
    expect(find.text('Permite «Alarmas y recordatorios»'), findsOneWidget);
    await t.tap(find.text('Permite «Alarmas y recordatorios»'));
    expect(canal.abiertos, ['exactas']);
    // la de las 06:00 va primero (orden por hora) y se puede encender
    await t.tap(find.byType(Switch).first);
    await t.pump();
    expect(c.alarma('b')!.activa, isTrue);
  });

  testWidgets('sin alarmas invita a crear una; el editor arma la alarma', (t) async {
    final c = ControlDespertador(canal: _Canal(const PermisosDespertador()))..cargadas = true;
    await t.pumpWidget(_app(DespertadorPagina(control: c)));
    await t.pump();
    expect(find.text('Despierta con tu música'), findsOneWidget);
    await t.tap(find.text('Nueva alarma'));
    await t.pumpAndSettle();
    expect(find.text('07:00'), findsOneWidget);
    expect(find.text('Al azar de tus «me gusta»'), findsNothing); // muestra el título de la fuente
    expect(find.text('Tus «me gusta»'), findsOneWidget);
    await t.tap(find.widgetWithText(FilterChip, 'S'));
    await t.pump();
    expect(find.text('Lun, Mar, Mié, Jue, Vie, Sáb'), findsOneWidget);
    // el editor es una lista: los chips de «Posponer» quedan bajo la línea de la prueba (800x600)
    await t.dragUntilVisible(
      find.widgetWithText(ChoiceChip, '15 min'),
      find.byType(Scrollable).last,
      const Offset(0, -200),
    );
    await t.tap(find.widgetWithText(ChoiceChip, '15 min'));
    await t.pump();
    await t.dragUntilVisible(find.text('Guardar'), find.byType(Scrollable).last, const Offset(0, -200));
    await t.tap(find.text('Guardar'));
    await t.pumpAndSettle();
    expect(c.alarmas.single.dias, {1, 2, 3, 4, 5, 6});
    expect(c.alarmas.single.posponer, 15);
  });

  testWidgets('Ajustes: entrada del despertador y el interruptor de la letra (Android)', (t) async {
    Plataforma.forzada = TargetPlatform.android;
    final c = ControlDespertador(canal: _Canal(const PermisosDespertador()))
      ..alarmas = [const Alarma(id: 'a', hora: 7, minuto: 30, dias: {1, 2, 3, 4, 5, 6, 7})]
      ..cargadas = true;
    final l = LetraEnBloqueo(puente: _Puente());
    await t.pumpWidget(_app(Scaffold(body: ListView(children: [AjustesDespertador(control: c, letra: l)]))));
    await t.pump();
    expect(find.text('Despertador'), findsOneWidget);
    expect(find.textContaining('07:30 · Suena en'), findsOneWidget);
    expect(find.text('Letra en la pantalla bloqueada'), findsOneWidget);
    await t.tap(find.text('Letra en la pantalla bloqueada'));
    await t.pump();
    expect(l.activa.value, isTrue);
  });

  testWidgets('en iPhone no hay interruptor de letra en el bloqueo', (t) async {
    Plataforma.forzada = TargetPlatform.iOS;
    final c = ControlDespertador(canal: _Canal(const PermisosDespertador()))..cargadas = true;
    await t.pumpWidget(_app(Scaffold(body: AjustesDespertador(control: c, letra: LetraEnBloqueo(puente: _Puente())))));
    await t.pump();
    expect(find.text('Letra en la pantalla bloqueada'), findsNothing);
  });

  testWidgets('pantalla de «está sonando»: apagar la cierra', (t) async {
    Plataforma.forzada = TargetPlatform.iOS;
    final c = ControlDespertador(canal: const CanalDespertador());
    const a = Alarma(id: 'x', etiqueta: 'Trabajo', posponer: 10);
    c.alarmas = [a];
    c.sonando.value = const SonandoAhora(a, 'Uno · A');
    await t.pumpWidget(_app(DespertadorSonandoPagina(control: c)));
    expect(find.text('Trabajo'), findsOneWidget);
    expect(find.text('Uno · A'), findsOneWidget);
    expect(find.text('Posponer 10 min'), findsOneWidget);
    expect(find.text('Apagar y seguir escuchando'), findsOneWidget);
    await t.tap(find.text('Apagar'));
    await t.pump();
    expect(c.sonando.value, isNull);
  });
}
