// Los estilos del reproductor grande, el selector, los colores de la carátula, la insignia de
// calidad, las mascotas y el modo karaoke, todo a 320x568 (sin desbordes ni excepciones).
import 'dart:io';
import 'dart:typed_data';

import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/estilo_reproductor.dart';
import 'package:caudal/nucleo/fondo_app.dart';
import 'package:caudal/nucleo/mascota_app.dart';
import 'package:caudal/nucleo/premium_letras.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/cast.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/paginas/karaoke_pagina.dart';
import 'package:caudal/ui/paginas/reproductor_pagina.dart';
import 'package:caudal/ui/reproductor/estilos_portada.dart';
import 'package:caudal/ui/reproductor/fondo_ambiente.dart';
import 'package:caudal/ui/reproductor/insignia_calidad.dart';
import 'package:caudal/ui/reproductor/linea_karaoke.dart';
import 'package:caudal/ui/reproductor/mascota_vida.dart';
import 'package:caudal/ui/reproductor/paleta_portada.dart';
import 'package:caudal/ui/reproductor/portada_deslizable.dart';
import 'package:caudal/ui/reproductor/vinilo.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'apoyo/cast_falso.dart';

class _R extends ChangeNotifier implements Reproductor {
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
  Fuente? fuente;
  @override
  bool bajarVoz = false;
  bool puedeVoz = true;
  @override
  bool get puedeBajarVoz => puedeVoz;
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(const Duration(minutes: 3));

  final pedidos = <String>[];

  @override
  Future<void> ponerBajarVoz(bool v) async {
    bajarVoz = v;
    pedidos.add('voz:$v');
  }

  @override
  Future<void> buscar(Duration d) async {
    posicion.value = d;
  }

  @override
  Future<void> siguiente({bool automatico = false}) async => pedidos.add('siguiente');

  @override
  Future<void> anterior() async => pedidos.add('anterior');

  @override
  Future<void> alternar() async {
    estado = estado == EstadoRepro.sonando ? EstadoRepro.pausa : EstadoRepro.sonando;
    notifyListeners();
  }

  void poner(EstadoRepro e) {
    estado = e;
    notifyListeners();
  }

  @override
  Future<void> dispose() async => super.dispose();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Col extends ChangeNotifier implements Coleccion {
  @override
  bool meGusta(String? clave) => false;
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Str implements Streams {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Desc extends ChangeNotifier implements GestorDescargas {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Json _pista({String miniatura = '', bool video = true}) => {
      'tipo': 'pista',
      'clave': 'yt:id1',
      if (video) 'video_id': 'id1',
      'titulo': 'Canción de prueba con un título bien largo para el ancho',
      'artista': 'Artista de prueba',
      'miniatura': miniatura,
    };

late _R _r;
late Servicios _s;

Future<void> _montar(WidgetTester t, Widget hijo,
    {Json? pista, bool sinAnimar = false, bool donador = true, Fuente? fuente}) async {
  SharedPreferences.setMockInitialValues({});
  esPremiumLetras = () => donador;
  final ajustes = await Ajustes.cargar('prueba');
  _r = _R()
    ..actual = pista ?? _pista()
    ..fuente = fuente;
  _s = Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
    ajustes: ajustes,
    coleccion: _Col(),
    reproductor: _r,
    streams: _Str(),
    descargas: _Desc(),
    cerrarSesion: () async {},
  );
  t.view.physicalSize = const Size(320, 568);
  t.view.devicePixelRatio = 1;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(
    s: _s,
    child: MaterialApp(
      theme: temaCaudal(),
      scaffoldMessengerKey: _s.mensajero,
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context).copyWith(disableAnimations: sinAnimar),
        child: child!,
      ),
      home: hijo,
    ),
  ));
  await t.pump(const Duration(milliseconds: 300));
}

/// La hoja de la mascota se decodifica en el hilo real: se le da un respiro y se pinta.
Future<void> _esperarHoja(WidgetTester t) async {
  await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 120)));
  await t.pump();
  await t.pump(const Duration(milliseconds: 50));
}

Future<void> _desmontar(WidgetTester t) async {
  // suelta los relojes de las pantallas antes de que acabe la prueba
  await t.pumpWidget(const SizedBox.shrink());
  await t.pump(const Duration(milliseconds: 50));
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final antes = esPremiumLetras;
  final catalogo = File('assets/mascotas/catalogo.json').readAsStringSync();

  setUp(() {
    PreferenciasReproductor.i.reiniciarParaPruebas();
    FondoApp.i.puede = false;
    MascotaApp.i.reiniciar();
  });
  tearDown(() => esPremiumLetras = antes);

  Future<void> conMascota(WidgetTester t, String clave) async {
    FondoApp.i.puede = true;
    await MascotaApp.i.cargarCatalogo(texto: catalogo);
    await MascotaApp.i.elegir(clave);
    expect(await t.runAsync(() => MascotaApp.i.imagen(clave)), isNotNull, reason: 'la hoja de $clave no se pudo leer');
  }

  group('estilos de la portada', () {
    const casos = <EstiloReproductor, Type>{
      EstiloReproductor.clasico: PortadaDeslizable,
      EstiloReproductor.vinilo: VinilVista,
      EstiloReproductor.casete: CaseteVista,
      EstiloReproductor.neon: NeonVista,
      EstiloReproductor.flotante: FlotanteVista,
    };
    casos.forEach((estilo, tipo) {
      testWidgets('${estilo.nombre}: se pinta a 320x568 sin desbordes y responde a pausa', (t) async {
        SharedPreferences.setMockInitialValues({});
        await _montar(t, const ReproductorPagina());
        PreferenciasReproductor.i.estilo = estilo;
        PreferenciasReproductor.i.notifyListeners();
        await t.pump(const Duration(milliseconds: 400));
        expect(find.byType(tipo), findsWidgets);
        expect(find.text('Artista de prueba'), findsOneWidget);
        _r.poner(EstadoRepro.pausa);
        await t.pump(const Duration(milliseconds: 600));
        _r.poner(EstadoRepro.sonando);
        await t.pump(const Duration(milliseconds: 600));
        expect(t.takeException(), isNull);
        await _desmontar(t);
      });
    });

    testWidgets('sin ser donador, Neón, Casete y Flotante se ven como el Clásico (el Vinilo sigue libre)', (t) async {
      await _montar(t, const ReproductorPagina(), donador: false);
      PreferenciasReproductor.i.estilo = EstiloReproductor.neon;
      PreferenciasReproductor.i.notifyListeners();
      await t.pump(const Duration(milliseconds: 400));
      expect(find.byType(NeonVista), findsNothing);
      expect(find.byType(PortadaDeslizable), findsOneWidget);
      PreferenciasReproductor.i.estilo = EstiloReproductor.vinilo;
      PreferenciasReproductor.i.notifyListeners();
      await t.pump(const Duration(milliseconds: 400));
      expect(find.byType(VinilVista), findsOneWidget);
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('el doble toque en cualquier estilo marca me gusta (mismo gesto que el clásico)', (t) async {
      await _montar(t, const ReproductorPagina());
      PreferenciasReproductor.i.estilo = EstiloReproductor.casete;
      PreferenciasReproductor.i.notifyListeners();
      await t.pump(const Duration(milliseconds: 400));
      await t.fling(find.byType(CaseteVista), const Offset(-300, 0), 1500);
      await t.pump(const Duration(milliseconds: 100));
      expect(_r.pedidos, ['siguiente']);
      await _desmontar(t);
    });

    for (final e in [EstiloReproductor.casete, EstiloReproductor.neon, EstiloReproductor.flotante]) {
      testWidgets('${e.nombre}: con «quitar animaciones» y en pausa no queda ninguna animación corriendo', (t) async {
        await _montar(t, const ReproductorPagina(), sinAnimar: true);
        _r.estado = EstadoRepro.pausa;
        PreferenciasReproductor.i.estilo = e;
        PreferenciasReproductor.i.notifyListeners();
        await t.pump(const Duration(milliseconds: 1500));
        await t.pump(const Duration(milliseconds: 1500));
        expect(t.binding.hasScheduledFrame, isFalse);
        expect(t.takeException(), isNull);
        await _desmontar(t);
      });
    }

    testWidgets('con «quitar animaciones» y sonando, el Casete tampoco gira (ningún fotograma pendiente)', (t) async {
      await _montar(t, const ReproductorPagina(), sinAnimar: true);
      PreferenciasReproductor.i.estilo = EstiloReproductor.casete;
      PreferenciasReproductor.i.notifyListeners();
      await t.pump(const Duration(milliseconds: 1500));
      await t.pump(const Duration(milliseconds: 1500));
      expect(t.binding.hasScheduledFrame, isFalse);
      await _desmontar(t);
    });
  });

  group('selector del reproductor', () {
    testWidgets('un donador abre el menú, elige Casete y se recuerda', (t) async {
      await _montar(t, const ReproductorPagina());
      await t.tap(find.byTooltip('Personalizar el reproductor'));
      await t.pump();
      await t.pump(const Duration(milliseconds: 500));
      for (final e in EstiloReproductor.values) {
        expect(find.text(e.nombre), findsOneWidget, reason: e.nombre);
      }
      expect(find.byIcon(Icons.lock_outline_rounded), findsNothing);
      await t.ensureVisible(find.text('Casete'));
      await t.tap(find.text('Casete'));
      await t.pump(const Duration(milliseconds: 600));
      expect(PreferenciasReproductor.i.estilo, EstiloReproductor.casete);
      expect(find.byType(CaseteVista), findsOneWidget);
      // se guardó en el teléfono
      final p = await t.runAsync(SharedPreferences.getInstance);
      expect(p!.getString('rep_estilo'), 'casete');
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('sin ser donador los estilos de donadores tienen candado y no se aplican', (t) async {
      await _montar(t, const ReproductorPagina(), donador: false);
      await t.tap(find.byTooltip('Personalizar el reproductor'));
      await t.pump();
      await t.pump(const Duration(milliseconds: 500));
      expect(find.byIcon(Icons.lock_outline_rounded), findsNWidgets(3));
      await t.ensureVisible(find.text('Neón'));
      await t.tap(find.text('Neón'));
      await t.pump(const Duration(milliseconds: 400));
      expect(PreferenciasReproductor.i.estilo, EstiloReproductor.clasico);
      expect(find.text('Esto es para donadores de Caudal'), findsOneWidget);
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('los colores y los sonidos se pueden apagar y encender (donadores)', (t) async {
      await _montar(t, const ReproductorPagina());
      await t.tap(find.byTooltip('Personalizar el reproductor'));
      await t.pump();
      await t.pump(const Duration(milliseconds: 500));
      await t.ensureVisible(find.text('Al dar me gusta'));
      await t.pump(const Duration(milliseconds: 300));
      await t.tap(find.text('Al dar me gusta'));
      await t.pump();
      expect(PreferenciasReproductor.i.sonidoMeGusta, isTrue);
      await t.ensureVisible(find.text('Colores de la carátula'));
      await t.tap(find.text('Colores de la carátula'));
      await t.pump();
      expect(PreferenciasReproductor.i.coloresDePortada, isFalse);
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });
  });

  group('colores de la carátula', () {
    late Directory dir;

    setUp(() {
      dir = Directory.systemTemp.createTempSync('portada');
      olvidarPaletas();
    });
    tearDown(() {
      PortadasMem.limpiar();
      dir.deleteSync(recursive: true);
    });

    Future<String> hacerPortada(WidgetTester t, String id, img.Color color) async {
      final bytes = img.encodePng(img.Image(width: 4, height: 4)..clear(color));
      final ref = 'mem:prueba:$id';
      PortadasMem.poner(ref, Uint8List.fromList(bytes));
      await t.runAsync(() => paletaDe(ref));
      return ref;
    }

    testWidgets('un donador ve el fondo con el tono de la carátula, con transición suave al cambiar', (t) async {
      final roja = await hacerPortada(t, 'roja', img.ColorRgb8(211, 47, 47));
      final azul = await hacerPortada(t, 'azul', img.ColorRgb8(25, 118, 210));
      await _montar(t, const ReproductorPagina(), pista: _pista(miniatura: roja));
      await t.pump(const Duration(milliseconds: 100));
      expect(t.widget<FondoAmbiente>(find.byType(FondoAmbiente)).color, paletaEnCache(roja)!.fondo);
      // cambia la canción: el color viaja de uno al otro, sin saltos
      _r.actual = _pista(miniatura: azul)..['clave'] = 'yt:id2';
      _r.notifyListeners();
      await t.pump(const Duration(milliseconds: 50));
      await t.pump(const Duration(milliseconds: 50)); // aqui arranca el reloj de la transicion
      await t.pump(const Duration(milliseconds: 250));
      final medio = t.widget<FondoAmbiente>(find.byType(FondoAmbiente)).color;
      expect(medio, isNot(paletaEnCache(roja)!.fondo));
      expect(medio, isNot(paletaEnCache(azul)!.fondo));
      await t.pump(const Duration(milliseconds: 900));
      expect(t.widget<FondoAmbiente>(find.byType(FondoAmbiente)).color, paletaEnCache(azul)!.fondo);
      await t.pump(const Duration(seconds: 9)); // el color de portada de siempre espera hasta 8 s
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('con «quitar animaciones» el cambio de paleta es inmediato', (t) async {
      final roja = await hacerPortada(t, 'roja', img.ColorRgb8(211, 47, 47));
      final azul = await hacerPortada(t, 'azul', img.ColorRgb8(25, 118, 210));
      await _montar(t, const ReproductorPagina(), pista: _pista(miniatura: roja), sinAnimar: true);
      await t.pump(const Duration(milliseconds: 100));
      _r.actual = _pista(miniatura: azul)..['clave'] = 'yt:id2';
      _r.notifyListeners();
      await t.pump(const Duration(milliseconds: 50));
      await t.pump(const Duration(milliseconds: 50));
      expect(t.widget<FondoAmbiente>(find.byType(FondoAmbiente)).color, paletaEnCache(azul)!.fondo);
      await t.pump(const Duration(seconds: 9));
      await _desmontar(t);
    });

    testWidgets('el acento de los botones sigue a la carátula y, si apaga los colores, vuelve al de siempre', (t) async {
      final roja = await hacerPortada(t, 'roja', img.ColorRgb8(211, 47, 47));
      await _montar(t, const ReproductorPagina(),
          pista: _pista(miniatura: roja), sinAnimar: true, fuente: Fuente(url: 'https://x', audioCodec: 'opus', abr: 160));
      await t.pump(const Duration(milliseconds: 100));
      expect(t.widget<InsigniaCalidad>(find.byType(InsigniaCalidad)).color, paletaEnCache(roja)!.acento);
      await t.runAsync(() => PreferenciasReproductor.i.ponerColores(false));
      await t.pump(const Duration(milliseconds: 100));
      await t.pump(const Duration(milliseconds: 100));
      expect(t.widget<InsigniaCalidad>(find.byType(InsigniaCalidad)).color, C.acento);
      await t.pump(const Duration(seconds: 9));
      await _desmontar(t);
    });
  });

  group('insignia de calidad', () {
    testWidgets('muestra códec y tasa a 320 px sin desbordar, para quien no es donador también', (t) async {
      await _montar(t, const ReproductorPagina(),
          donador: false, fuente: Fuente(url: 'https://x', audioCodec: 'opus', abr: 160));
      expect(find.byType(InsigniaCalidad), findsOneWidget);
      expect(find.text('Opus · 160 kbps'), findsOneWidget);
      expect(t.widget<InsigniaCalidad>(find.byType(InsigniaCalidad)).calidad.detalle, 'Audio Opus a 160 kilobits por segundo');
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('sin datos de la fuente no aparece nada', (t) async {
      await _montar(t, const ReproductorPagina());
      expect(find.byType(InsigniaCalidad), findsNothing);
      await _desmontar(t);
    });
  });

  group('mascotas', () {
    testWidgets('Flotante: la mascota elegida acompaña a la carátula, sin desbordes', (t) async {
      await _montar(t, const ReproductorPagina());
      await conMascota(t, 'pikachu');
      PreferenciasReproductor.i.estilo = EstiloReproductor.flotante;
      PreferenciasReproductor.i.notifyListeners();
      await t.pump(const Duration(milliseconds: 600));
      await _esperarHoja(t);
      expect(find.byType(MascotaSuelta), findsOneWidget);
      final nombre = MascotaApp.i.actual!.nombre;
      expect(find.byWidgetPredicate((w) => w is Semantics && w.properties.label == nombre), findsOneWidget);
      await t.pump(const Duration(seconds: 2));
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('Flotante sin mascota elegida: solo flota la carátula', (t) async {
      await _montar(t, const ReproductorPagina());
      PreferenciasReproductor.i.estilo = EstiloReproductor.flotante;
      PreferenciasReproductor.i.notifyListeners();
      await t.pump(const Duration(milliseconds: 600));
      expect(find.byType(FlotanteVista), findsOneWidget);
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('la mascota suelta se duerme a los 2 minutos en pausa y despierta al sonar', (t) async {
      await _montar(t, const ReproductorPagina());
      await conMascota(t, 'pikachu');
      PreferenciasReproductor.i.estilo = EstiloReproductor.flotante;
      PreferenciasReproductor.i.notifyListeners();
      await t.pump(const Duration(milliseconds: 600));
      await _esperarHoja(t);
      _r.poner(EstadoRepro.pausa);
      await t.pump(const Duration(minutes: 2, seconds: 1));
      await t.pump(const Duration(milliseconds: 800)); // las «z» se mueven
      expect(t.takeException(), isNull);
      _r.poner(EstadoRepro.sonando);
      await t.pump(const Duration(seconds: 1));
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });
  });

  group('modo karaoke', () {
    final letra = <String, dynamic>{
      'texto': '',
      'lineas': [
        [0, 'Primera línea de la canción'],
        [4000, 'Segunda línea más larga'],
        [9000, 'Tercera'],
        [14000, 'Cuarta línea bastante más larga que cabe en dos filas del teléfono'],
      ],
    };

    Future<void> abrir(WidgetTester t, {bool sinAnimar = false, bool puedeVoz = true}) async {
      await _montar(t, KaraokePagina(pista: _pista(), letra: letra), sinAnimar: sinAnimar);
      _r.puedeVoz = puedeVoz;
      await t.pump(const Duration(milliseconds: 400));
    }

    testWidgets('muestra la letra grande, sigue a la canción y no se desborda a 320x568', (t) async {
      await abrir(t);
      expect(find.byType(FondoAmbiente), findsOneWidget);
      expect(find.text('Canción de prueba con un título bien largo para el ancho'), findsOneWidget);
      // al empezar suena la primera línea: la usa LineaKaraoke
      _r.posicion.value = const Duration(milliseconds: 500);
      await t.pump(const Duration(milliseconds: 600));
      expect(t.widget<LineaKaraoke>(find.byType(LineaKaraoke)).texto, 'Primera línea de la canción');
      _r.posicion.value = const Duration(milliseconds: 5000);
      await t.pump(const Duration(milliseconds: 700));
      expect(t.widget<LineaKaraoke>(find.byType(LineaKaraoke)).texto, startsWith('Segunda línea'));
      expect(find.text('Primera línea de la canción'), findsOneWidget); // la anterior, tenue
      expect(find.text('Tercera'), findsOneWidget);
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('tocar una línea lleva la canción a ese momento', (t) async {
      await abrir(t);
      _r.posicion.value = const Duration(milliseconds: 500);
      await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600)); // el desplazamiento automático ya terminó
      await t.tap(find.text('Segunda línea más larga'));
      await t.pump(const Duration(milliseconds: 300));
      expect(_r.posicion.value, const Duration(milliseconds: 4000));
      await _desmontar(t);
    });

    testWidgets('«Bajar la voz» aparece si el motor puede, se activa y se apaga sola al salir', (t) async {
      await abrir(t);
      expect(find.text('Bajar la voz'), findsOneWidget);
      await t.tap(find.text('Bajar la voz'));
      await t.pump(const Duration(milliseconds: 200));
      expect(_r.bajarVoz, isTrue);
      await _desmontar(t);
      expect(_r.bajarVoz, isFalse);
      expect(_r.pedidos, ['voz:true', 'voz:false']);
    });

    testWidgets('si el motor no puede, la opción de voz ni aparece', (t) async {
      await abrir(t, puedeVoz: false);
      await t.pump(const Duration(milliseconds: 100));
      // el chip se decide al construir: se vuelve a pintar con el reproductor ya sin voz
      _r.notifyListeners();
      await t.pump(const Duration(milliseconds: 100));
      expect(find.text('Bajar la voz'), findsNothing);
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('la mascota canta a su lado, también con «quitar animaciones»', (t) async {
      await _montar(t, KaraokePagina(pista: _pista(), letra: letra), sinAnimar: true);
      await conMascota(t, 'kirby');
      _r.notifyListeners();
      await t.pump(const Duration(milliseconds: 600));
      await _esperarHoja(t);
      expect(find.byType(MascotaSuelta), findsOneWidget);
      expect(find.descendant(of: find.byType(MascotaSuelta), matching: find.byType(CustomPaint)), findsOneWidget);
      await t.pump(const Duration(seconds: 2));
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('una letra sin tiempos se muestra como texto y avisa', (t) async {
      await _montar(t, KaraokePagina(pista: _pista(), letra: const {'texto': 'Solo texto\nsin tiempos', 'lineas': []}));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.textContaining('no trae tiempos'), findsOneWidget);
      expect(find.textContaining('Solo texto'), findsOneWidget);
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('desde la letra del reproductor: un donador entra al karaoke y un no donador recibe un aviso', (t) async {
      // el botón del karaoke vive en la tarjeta de letra: se abre con una letra ya cargada
      await _montar(t, Scaffold(body: BotonKaraoke(pista: _pista(), letra: letra)));
      await t.tap(find.byType(BotonKaraoke));
      await t.pump();
      await t.pump(const Duration(milliseconds: 500));
      expect(find.byType(KaraokePagina), findsOneWidget);
      await _desmontar(t);

      await _montar(t, Scaffold(body: BotonKaraoke(pista: _pista(), letra: letra)), donador: false);
      await t.tap(find.byType(BotonKaraoke));
      await t.pump();
      await t.pump(const Duration(milliseconds: 400));
      expect(find.byType(KaraokePagina), findsNothing);
      expect(find.text('El modo karaoke es para donadores de Caudal'), findsOneWidget);
      await _desmontar(t);
    });
  });
}
