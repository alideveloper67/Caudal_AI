// La interfaz en iPhone: lo que cambia respecto de Android y que Android sigue
// igual. Se finge la plataforma con TargetPlatformVariant (defaultTargetPlatform).
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/plataforma.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/nucleo/version.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/paginas/ajustes_pagina.dart';
import 'package:caudal/ui/paginas/descargas_pagina.dart';
import 'package:caudal/ui/paginas/sonido.dart';
import 'package:caudal/ui/plataforma.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _ReproductorFalso extends ChangeNotifier implements Reproductor {
  @override
  Json? actual;
  @override
  EstadoRepro estado = EstadoRepro.parado;
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(Duration.zero);
  @override
  double get velocidad => 1;
  @override
  bool get sonidoLimitado => Plataforma.esIOS;
  @override
  Future<void> dispose() async => super.dispose();
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ColeccionFalsa extends ChangeNotifier implements Coleccion {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StreamsFalsos implements Streams {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _DescargasFalsas extends ChangeNotifier implements GestorDescargas {
  @override
  List<Descarga> get lista => const [];
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

final _ios = TargetPlatformVariant.only(TargetPlatform.iOS);
final _android = TargetPlatformVariant.only(TargetPlatform.android);

Future<void> _montar(WidgetTester t, Widget pagina) async {
  // el nucleo (Novedad, Ajustes) tambien cree estar en la plataforma de la prueba
  Plataforma.forzada = defaultTargetPlatform;
  addTearDown(() => Plataforma.forzada = null);
  SharedPreferences.setMockInitialValues({});
  final ajustes = await Ajustes.cargar('prueba');
  final s = Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
    ajustes: ajustes,
    coleccion: _ColeccionFalsa(),
    reproductor: _ReproductorFalso(),
    streams: _StreamsFalsos(),
    descargas: _DescargasFalsas(),
    cerrarSesion: () async {},
  );
  // pantalla alta: que toda la lista de ajustes quede construida
  t.view.physicalSize = const Size(1179, 9000);
  t.view.devicePixelRatio = 3;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(s: s, child: MaterialApp(theme: temaCaudal(), home: pagina)));
  await t.pump(const Duration(milliseconds: 300));
}

const _novedad = Novedad(version: '9.9.9', notas: 'Cosas nuevas', apk: 'https://x/caudal.apk',
    pagina: 'https://github.com/a/b/releases/tag/movil-v9.9.9', peso: 1000);

/// Las llamadas de vibracion que la app manda al sistema.
List<String> _escucharVibraciones(WidgetTester t) {
  final hechas = <String>[];
  t.binding.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, (c) async {
    if (c.method == 'HapticFeedback.vibrate') hechas.add('${c.arguments}');
    return null;
  });
  addTearDown(() => t.binding.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, null));
  return hechas;
}

void main() {
  group('Ajustes', () {
    testWidgets('en iPhone no ofrece guardar en la música del teléfono', (t) async {
      await _montar(t, const AjustesPagina());
      expect(find.text('Guardar en la música del teléfono'), findsNothing);
      expect(find.text('Descargar solo con wifi'), findsOneWidget);
      expect(t.takeException(), isNull);
    }, variant: _ios);

    testWidgets('en Android sigue estando', (t) async {
      await _montar(t, const AjustesPagina());
      expect(find.text('Guardar en la música del teléfono'), findsOneWidget);
    }, variant: _android);
  });

  group('actualización', () {
    testWidgets('en iPhone el botón es "Ver cómo actualizar" y abre la página', (t) async {
      final abiertas = <String>[];
      final antes = abrirEnNavegador;
      abrirEnNavegador = (u) async => abiertas.add(u);
      addTearDown(() => abrirEnNavegador = antes);

      await _montar(t, Builder(builder: (ctx) => Scaffold(
          body: TextButton(onPressed: () => mostrarActualizacion(ctx, _novedad), child: const Text('abrir')))));
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle();

      expect(find.text('Instalar ahora'), findsNothing);
      expect(find.text('Ver cómo actualizar'), findsOneWidget);
      await t.tap(find.text('Ver cómo actualizar'));
      await t.pumpAndSettle();
      expect(abiertas, [_novedad.pagina]);
      expect(find.text('Ver cómo actualizar'), findsNothing, reason: 'la hoja se cierra');
    }, variant: _ios);

    testWidgets('en Android sigue siendo "Instalar ahora"', (t) async {
      await _montar(t, Builder(builder: (ctx) => Scaffold(
          body: TextButton(onPressed: () => mostrarActualizacion(ctx, _novedad), child: const Text('abrir')))));
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle();
      expect(find.text('Instalar ahora'), findsOneWidget);
      expect(find.text('Ver cómo actualizar'), findsNothing);
    }, variant: _android);
  });

  group('Sonido', () {
    Future<void> abrirSonido(WidgetTester t) async {
      await _montar(t, Builder(builder: (ctx) => Scaffold(
          body: TextButton(onPressed: () => mostrarSonido(ctx), child: const Text('abrir')))));
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle();
    }

    testWidgets('en iPhone no ofrece igualar el volumen y avisa de la distorsión', (t) async {
      await abrirSonido(t);
      expect(find.text('Igualar el volumen entre canciones'), findsNothing);
      expect(find.textContaining('pueden distorsionar'), findsOneWidget);
    }, variant: _ios);

    testWidgets('en Android sigue igual', (t) async {
      await abrirSonido(t);
      expect(find.text('Igualar el volumen entre canciones'), findsOneWidget);
      expect(find.textContaining('pueden distorsionar'), findsNothing);
    }, variant: _android);
  });

  group('Descargar', () {
    testWidgets('en iPhone explica que lo descargado está en Archivos > Caudal', (t) async {
      await _montar(t, const DescargasPagina());
      expect(find.textContaining('app Archivos'), findsOneWidget);
      expect(find.textContaining('Caudal › Música o Videos'), findsOneWidget);
    }, variant: _ios);

    testWidgets('en Android no aparece ese aviso', (t) async {
      await _montar(t, const DescargasPagina());
      expect(find.textContaining('app Archivos'), findsNothing);
    }, variant: _android);
  });

  group('volver desde el borde', () {
    Future<List<int>> montarBorde(WidgetTester t) async {
      final vueltas = <int>[];
      await t.pumpWidget(MaterialApp(
        home: BordeVolver(
          alVolver: () => vueltas.add(1),
          child: const ColoredBox(color: Colors.black, child: SizedBox.expand()),
        ),
      ));
      return vueltas;
    }

    testWidgets('en iPhone deslizar desde el borde izquierdo cierra', (t) async {
      final vueltas = await montarBorde(t);
      await t.dragFrom(const Offset(4, 300), const Offset(300, 0));
      await t.pumpAndSettle();
      expect(vueltas, hasLength(1));
    }, variant: _ios);

    testWidgets('en iPhone un arrastre corto vuelve a su sitio sin cerrar', (t) async {
      final vueltas = await montarBorde(t);
      final gesto = await t.startGesture(const Offset(4, 300));
      await gesto.moveBy(const Offset(20, 0));
      await t.pump(const Duration(milliseconds: 500));
      await gesto.moveBy(const Offset(20, 0));
      await t.pump(const Duration(milliseconds: 500));
      await gesto.up();
      await t.pumpAndSettle();
      expect(vueltas, isEmpty);
      final caja = t.getTopLeft(find.byType(ColoredBox).first);
      expect(caja.dx, 0);
    }, variant: _ios);

    testWidgets('en Android no añade nada', (t) async {
      final vueltas = await montarBorde(t);
      await t.dragFrom(const Offset(4, 300), const Offset(300, 0));
      await t.pumpAndSettle();
      expect(vueltas, isEmpty);
    }, variant: _android);

    testWidgets('las páginas usan la transición de iOS (la que se cierra con el dedo)', (t) async {
      final tema = temaCaudal();
      expect(tema.pageTransitionsTheme.builders[TargetPlatform.iOS], isA<CupertinoPageTransitionsBuilder>());
    });

    testWidgets('una página empujada en iPhone se cierra deslizando desde el borde', (t) async {
      final nav = GlobalKey<NavigatorState>();
      await t.pumpWidget(MaterialApp(theme: temaCaudal(), navigatorKey: nav, home: const Scaffold(body: Text('raíz'))));
      nav.currentState!.push(MaterialPageRoute(builder: (_) => const Scaffold(body: Center(child: Text('hija')))));
      await t.pumpAndSettle();
      expect(find.text('hija'), findsOneWidget);
      await t.dragFrom(const Offset(5, 300), const Offset(500, 0));
      await t.pumpAndSettle();
      expect(find.text('hija'), findsNothing);
      expect(find.text('raíz'), findsOneWidget);
    }, variant: _ios);
  });

  group('rebote', () {
    test('arriba no rebota (el sobrante llega a "bajar para cerrar"), abajo sí', () {
      const f = RebotaSoloAbajo();
      final m = FixedScrollMetrics(minScrollExtent: 0, maxScrollExtent: 500, pixels: 0, viewportDimension: 800,
          axisDirection: AxisDirection.down, devicePixelRatio: 3);
      expect(f.applyBoundaryConditions(m, -30), -30);
      final abajo = m.copyWith(pixels: 500);
      expect(f.applyBoundaryConditions(abajo, 530), 0);
    });

    testWidgets('las listas normales rebotan en iPhone', (t) async {
      late ScrollPhysics fisica;
      await t.pumpWidget(MaterialApp(theme: temaCaudal(), home: Builder(builder: (ctx) {
        fisica = ScrollConfiguration.of(ctx).getScrollPhysics(ctx);
        return const SizedBox();
      })));
      expect(fisica, isA<BouncingScrollPhysics>());
    }, variant: _ios);
  });

  group('vibraciones', () {
    testWidgets('en iPhone vibran', (t) async {
      final hechas = _escucharVibraciones(t);
      Haptico.toque();
      Haptico.seleccion();
      Haptico.exito();
      expect(hechas, hasLength(3));
    }, variant: _ios);

    testWidgets('en Android no añaden nada a lo de siempre', (t) async {
      final hechas = _escucharVibraciones(t);
      Haptico.toque();
      Haptico.seleccion();
      Haptico.firme();
      expect(hechas, isEmpty);
    }, variant: _android);
  });
}
