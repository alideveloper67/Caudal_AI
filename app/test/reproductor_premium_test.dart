// El reproductor grande y el mini: modo ambiente, doble toque para me gusta,
// barra de progreso arrastrable y cambio de cancion por gesto. Sin red ni
// media_kit: el reproductor y la coleccion son dobles.
//
// El fondo ambiente se mueve sin fin mientras suena, asi que aqui no se usa
// pumpAndSettle: se avanza el reloj a mano.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/cast.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/armazon.dart';
import 'package:caudal/ui/paginas/reproductor_pagina.dart';
import 'package:caudal/ui/reproductor/animaciones.dart';
import 'package:caudal/ui/reproductor/barra_progreso.dart';
import 'package:caudal/ui/reproductor/fondo_ambiente.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'apoyo/cast_falso.dart';

class _ReproductorFalso extends ChangeNotifier implements Reproductor {
  @override
  late final ControlCast cast = castFalso();
  @override
  Json? actual;
  @override
  Json? contexto;
  @override
  EstadoRepro estado = EstadoRepro.sonando;
  @override
  bool aleatorio = false;
  @override
  String repetir = 'no';
  @override
  String modo = 'audio';
  @override
  double velocidad = 1;
  @override
  int? get restanteApagado => null;
  @override
  get fuente => null;
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(const Duration(minutes: 3));

  final buscadas = <Duration>[];
  final pedidos = <String>[];

  @override
  Future<void> buscar(Duration d) async {
    buscadas.add(d);
    posicion.value = d;
  }

  @override
  Future<void> siguiente({bool automatico = false, bool porFallo = false}) async {
    pedidos.add('siguiente');
    actual = _pista(2);
    notifyListeners();
  }

  @override
  Future<void> anterior() async {
    pedidos.add('anterior');
    actual = _pista(0);
    notifyListeners();
  }

  @override
  Future<void> alternar() async {
    estado = estado == EstadoRepro.sonando ? EstadoRepro.pausa : EstadoRepro.sonando;
    notifyListeners();
  }

  @override
  Future<void> dispose() async => super.dispose();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ColeccionFalsa extends ChangeNotifier implements Coleccion {
  final Set<String> gustan = {};

  @override
  bool meGusta(String? clave) => gustan.contains(clave);

  @override
  Future<bool> alternarMeGusta(Json pista) async {
    final c = '${pista['clave']}';
    final ahora = !gustan.remove(c);
    if (ahora) gustan.add(c);
    notifyListeners();
    return ahora;
  }

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

Json _pista(int i) => {
      'tipo': 'pista',
      'clave': 'yt:id$i',
      'video_id': 'id$i',
      'titulo': 'Canción $i',
      'artista': 'Artista $i',
      'miniatura': '',
    };

late _ReproductorFalso _r;
late _ColeccionFalsa _col;
late Servicios _s;

Future<void> _montar(WidgetTester t, Widget hijo) async {
  SharedPreferences.setMockInitialValues({});
  final ajustes = await Ajustes.cargar('prueba');
  _r = _ReproductorFalso()..actual = _pista(1);
  _col = _ColeccionFalsa();
  _s = Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
    ajustes: ajustes,
    coleccion: _col,
    reproductor: _r,
    streams: _StreamsFalsos(),
    descargas: _DescargasFalsas(),
    cerrarSesion: () async {},
  );
  t.view.physicalSize = const Size(1080, 2400);
  t.view.devicePixelRatio = 2.75;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(s: _s, child: MaterialApp(theme: temaCaudal(), home: hijo)));
  await t.pump(const Duration(milliseconds: 300));
}

void main() {
  group('reproductor grande', () {
    testWidgets('se pinta con el modo ambiente y se mueve solo mientras suena', (t) async {
      await _montar(t, const ReproductorPagina());
      expect(find.byType(FondoAmbiente), findsOneWidget);
      expect(find.text('Canción 1'), findsOneWidget);
      expect(t.widget<FondoAmbiente>(find.byType(FondoAmbiente)).enMovimiento, isTrue);

      // pausa: el boton grande cambia de icono y el fondo se queda quieto
      await t.tap(find.byType(IconoPlayPausa));
      await t.pump(const Duration(milliseconds: 400));
      expect(_r.estado, EstadoRepro.pausa);
      expect(t.widget<FondoAmbiente>(find.byType(FondoAmbiente)).enMovimiento, isFalse);
      expect(t.takeException(), isNull);
    });

    testWidgets('doble toque en la portada marca me gusta y no lo quita', (t) async {
      await _montar(t, const ReproductorPagina());
      final portada = find.byType(Hero);
      await t.tap(portada);
      await t.pump(const Duration(milliseconds: 60));
      await t.tap(portada);
      await t.pump(); // el primer fotograma arranca la animacion
      await t.pump(const Duration(milliseconds: 200));
      expect(_col.gustan, contains('yt:id1'));
      // el corazon grande aparece encima
      expect(find.descendant(of: find.byType(CorazonEmergente), matching: find.byIcon(Icons.favorite_rounded)),
          findsOneWidget);
      await t.pump(const Duration(seconds: 1));

      // otro doble toque no lo desmarca
      await t.tap(portada);
      await t.pump(const Duration(milliseconds: 60));
      await t.tap(portada);
      await t.pump(const Duration(milliseconds: 400));
      expect(_col.gustan, contains('yt:id1'));
      await t.pump(const Duration(seconds: 3)); // que se vaya el aviso
      expect(t.takeException(), isNull);
    });

    testWidgets('deslizar la portada a la izquierda pasa a la siguiente', (t) async {
      await _montar(t, const ReproductorPagina());
      await t.fling(find.byType(Hero), const Offset(-300, 0), 1500);
      await t.pump(const Duration(milliseconds: 100));
      expect(_r.pedidos, ['siguiente']);
      await t.pump(const Duration(milliseconds: 500));
      expect(find.text('Canción 2'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('la barra de progreso busca donde se suelta y muestra el tiempo flotante', (t) async {
      await _montar(t, const ReproductorPagina());
      final barra = find.byType(BarraProgreso);
      final caja = t.getRect(barra);
      final g = await t.startGesture(Offset(caja.left + 40, caja.top + 20));
      await t.pump(const Duration(milliseconds: 50));
      await g.moveBy(const Offset(60, 0));
      await t.pump();
      await g.moveTo(Offset(caja.center.dx, caja.top + 20));
      await t.pump(const Duration(milliseconds: 200));
      // el globo con el tiempo: aparece en el centro de una cancion de 3 min
      expect(find.text('1:30'), findsWidgets);
      await g.up();
      await t.pump(const Duration(milliseconds: 400));
      expect(_r.buscadas, isNotEmpty);
      final ms = _r.buscadas.last.inMilliseconds;
      expect(ms, inInclusiveRange(80000, 100000));
      expect(t.takeException(), isNull);
    });
  });

  group('mini reproductor', () {
    testWidgets('corazón y play animados sin romperse', (t) async {
      await _montar(t, const Scaffold(body: Align(alignment: Alignment.bottomCenter, child: MiniReproductor())));
      expect(find.text('Canción 1'), findsOneWidget);
      await t.tap(find.byType(CorazonAnimado));
      await t.pump(const Duration(milliseconds: 600));
      expect(_col.gustan, contains('yt:id1'));
      await t.tap(find.byType(IconoPlayPausa));
      await t.pump(const Duration(milliseconds: 400));
      expect(_r.estado, EstadoRepro.pausa);
      await t.pump(const Duration(seconds: 3));
      expect(t.takeException(), isNull);
    });
  });
}
