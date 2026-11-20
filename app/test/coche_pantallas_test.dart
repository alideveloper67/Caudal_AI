import 'dart:async';

import 'package:caudal/coche/abrir_modo_coche.dart';
import 'package:caudal/coche/coche_bluetooth.dart';
import 'package:caudal/coche/modo_coche_ajustes_pagina.dart';
import 'package:caudal/coche/vigia_coche.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _coche = DispositivoBt(direccion: 'AA:BB:CC:00:11:22', nombre: 'Radio del coche', esCoche: true, esAudio: true);
const _bocina = DispositivoBt(direccion: '11:22:33:44:55:66', nombre: 'Bocina de la cocina', esAudio: true);
const _reloj = DispositivoBt(direccion: '99:88:77:66:55:44', nombre: '');

class _Bt implements FuenteBluetooth {
  _Bt({this.permiso = true, this.dejaPermiso = true, this.lista = const [_bocina, _reloj, _coche]});
  bool permiso;
  bool dejaPermiso;
  List<DispositivoBt> lista;
  List<DispositivoBt> ahora = [];
  int pedidos = 0, ajustesAbiertos = 0;
  final _eventos = StreamController<EventoBt>.broadcast();

  void conectar(DispositivoBt d) {
    ahora = [...ahora, d];
    _eventos.add(EventoBt(conectado: true, dispositivo: d));
  }

  void desconectar(DispositivoBt d) {
    ahora = [for (final x in ahora) if (x != d) x];
    _eventos.add(EventoBt(conectado: false, dispositivo: d));
  }

  @override
  bool get disponible => true;
  @override
  Future<bool> hayPermiso() async => permiso;
  @override
  Future<bool> pedirPermiso() async {
    pedidos++;
    if (dejaPermiso) permiso = true;
    return permiso;
  }

  @override
  Future<void> abrirAjustesDeLaApp() async => ajustesAbiertos++;
  @override
  Future<List<DispositivoBt>> emparejados() async => permiso ? List.of(lista) : const [];
  @override
  Future<List<DispositivoBt>> conectados() async => permiso ? ahora : const [];
  @override
  Stream<EventoBt> get cambios => _eventos.stream;
}

/// Monta [pagina] a [tam] con la letra a [escala]. Cualquier error de Flutter (un
/// desborde incluido) hace fallar la prueba por sí solo; al final se mira además
/// que no quede ninguna excepción pendiente.
Future<void> _montar(WidgetTester t, Widget pagina,
    {Size tam = const Size(320, 568), double escala = 1.0}) async {
  t.view.physicalSize = tam * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(
    theme: temaCaudal(),
    builder: (ctx, hijo) => MediaQuery(
      data: MediaQuery.of(ctx).copyWith(textScaler: TextScaler.linear(escala)),
      child: hijo!,
    ),
    home: pagina,
  ));
  await t.pump(const Duration(milliseconds: 300));
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    AbrirModoCoche.reiniciar();
    AbrirModoCoche.pantalla = () => const Scaffold(body: Center(child: Text('PANTALLA MODO COCHE')));
  });

  group('Ajustes > Modo coche', () {
    testWidgets('abre el modo coche a mano', (t) async {
      await _montar(t, ModoCocheAjustesPagina(fuente: _Bt()));
      await t.tap(find.text('Abrir el modo coche'));
      await t.pumpAndSettle();
      expect(find.text('PANTALLA MODO COCHE'), findsOneWidget);
      expect(AbrirModoCoche.abierto, isTrue);
      // otro pedido (el Bluetooth, un acceso directo) no apila otra pantalla
      await AbrirModoCoche.abrir(t.element(find.text('PANTALLA MODO COCHE')));
      await t.pumpAndSettle();
      expect(find.text('PANTALLA MODO COCHE'), findsOneWidget);
      Navigator.of(t.element(find.text('PANTALLA MODO COCHE'))).pop();
      await t.pumpAndSettle();
      expect(AbrirModoCoche.abierto, isFalse);
      expect(t.takeException(), isNull);
    });

    testWidgets('activar: pide permiso, enseña los aparatos (el coche primero y ya marcado) y lo guarda', (t) async {
      final bt = _Bt(permiso: false);
      await _montar(t, ModoCocheAjustesPagina(fuente: bt), tam: const Size(400, 1000));
      expect(find.text('Falta el permiso de dispositivos cercanos'), findsOneWidget);
      await t.tap(find.byType(Switch));
      await t.pumpAndSettle();
      expect(bt.pedidos, 1);
      expect(find.text('Radio del coche'), findsOneWidget);
      expect(find.text('Bocina de la cocina'), findsOneWidget);
      expect(find.text('Aparato sin nombre'), findsOneWidget);
      // el que parece de coche va arriba
      final yCoche = t.getTopLeft(find.text('Radio del coche')).dy;
      expect(yCoche, lessThan(t.getTopLeft(find.text('Bocina de la cocina')).dy));
      final p = await PreferenciasCoche.cargar();
      expect(p.abrirSolo, isTrue);
      expect(p.dispositivos.keys, [_coche.direccion]);

      // marcar también la bocina
      await t.tap(find.text('Bocina de la cocina'));
      await t.pumpAndSettle();
      expect((await PreferenciasCoche.cargar()).dispositivos.keys.toSet(), {_coche.direccion, _bocina.direccion});
      expect(t.takeException(), isNull);
    });

    testWidgets('sin permiso no se activa y «Dar permiso» lleva a los ajustes del teléfono', (t) async {
      final bt = _Bt(permiso: false, dejaPermiso: false);
      await _montar(t, ModoCocheAjustesPagina(fuente: bt));
      await t.tap(find.byType(Switch));
      await t.pumpAndSettle();
      expect((await PreferenciasCoche.cargar()).abrirSolo, isFalse);
      // en la pantalla chica «Dar permiso» queda debajo: la lista es perezosa, hay que bajar hasta él
      await t.dragUntilVisible(find.text('Dar permiso'), find.byType(ListView), const Offset(0, -100));
      await t.ensureVisible(find.text('Dar permiso'));
      await t.pumpAndSettle();
      await t.tap(find.text('Dar permiso'));
      await t.pumpAndSettle();
      expect(bt.ajustesAbiertos, 1);
      expect(t.takeException(), isNull);
    });

    testWidgets('sin aparatos emparejados lo explica', (t) async {
      SharedPreferences.setMockInitialValues({'coche_abrir_solo': true});
      await _montar(t, ModoCocheAjustesPagina(fuente: _Bt(lista: const [])));
      await t.pumpAndSettle();
      // el aviso queda debajo del interruptor: bajar hasta él como lo haría la persona
      await t.dragUntilVisible(find.textContaining('No hay aparatos emparejados'), find.byType(ListView), const Offset(0, -100));
      expect(find.textContaining('No hay aparatos emparejados'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    for (final (nombre, tam, escala) in [
      ('320x568', const Size(320, 568), 1.0),
      ('320x568 con letra grande', const Size(320, 568), 1.3),
      ('horizontal 640x360', const Size(640, 360), 1.0),
    ]) {
      testWidgets('sin desbordes: $nombre', (t) async {
        SharedPreferences.setMockInitialValues({'coche_abrir_solo': true, 'coche_dispositivos': '${_coche.direccion}|x'});
        await _montar(t, ModoCocheAjustesPagina(fuente: _Bt()), tam: tam, escala: escala);
        await t.pumpAndSettle();
        await t.drag(find.byType(ListView), const Offset(0, -2000));
        await t.pumpAndSettle();
        expect(find.textContaining('Fuentes desconocidas'), findsOneWidget);
        expect(t.takeException(), isNull);
      });
    }
  });

  group('VigiaCoche', () {
    Future<(int Function(), _Bt)> montarVigia(WidgetTester t, {bool activado = true, _Bt? bt}) async {
      SharedPreferences.setMockInitialValues(
          activado ? {'coche_abrir_solo': true, 'coche_dispositivos': '${_coche.direccion}|Radio'} : {});
      final b = bt ?? _Bt();
      var abiertos = 0;
      await t.pumpWidget(MaterialApp(
        home: VigiaCoche(
          fuente: b,
          abrir: (_) async => abiertos++,
          child: const Text('principal'),
        ),
      ));
      await t.pump();
      await t.pump();
      return (() => abiertos, b);
    }

    testWidgets('al conectar el coche con Caudal a la vista se abre', (t) async {
      final (abiertos, bt) = await montarVigia(t);
      bt.conectar(_bocina);
      await t.pump();
      expect(abiertos(), 0, reason: 'la bocina no es el coche');
      bt.conectar(_coche);
      await t.pump();
      expect(abiertos(), 1);
      // el aviso repetido de la misma conexión no lo reabre
      bt.conectar(_coche);
      await t.pump();
      expect(abiertos(), 1);
      bt.desconectar(_coche);
      bt.conectar(_coche);
      await t.pump();
      expect(abiertos(), 2);
    });

    testWidgets('con Caudal de fondo espera a que vuelvas', (t) async {
      final (abiertos, bt) = await montarVigia(t);
      t.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
      t.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
      t.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      bt.conectar(_coche);
      await t.pump();
      expect(abiertos(), 0);
      t.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
      t.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
      t.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await t.pump();
      expect(abiertos(), 1);
    });

    testWidgets('si el coche ya estaba conectado al abrir Caudal, se abre', (t) async {
      final bt = _Bt()..ahora = [_coche];
      final (abiertos, _) = await montarVigia(t, bt: bt);
      expect(abiertos(), 1);
    });

    testWidgets('apagado en ajustes: nunca se abre solo', (t) async {
      final (abiertos, bt) = await montarVigia(t, activado: false);
      bt.conectar(_coche);
      await t.pump();
      expect(abiertos(), 0);
      expect(find.text('principal'), findsOneWidget);
    });

    testWidgets('recién activado con el coche ya conectado: no salta encima de los ajustes', (t) async {
      final bt = _Bt()..ahora = [_coche];
      final (abiertos, _) = await montarVigia(t, activado: false, bt: bt);
      await (PreferenciasCoche(abrirSolo: true)..alternar(_coche, true)).guardar();
      await t.pump();
      await t.pump();
      bt.conectar(_coche); // el mismo coche que ya estaba
      await t.pump();
      expect(abiertos(), 0);
      bt.desconectar(_coche);
      bt.conectar(_coche);
      await t.pump();
      expect(abiertos(), 1, reason: 'la próxima conexión sí');
    });
  });
}
