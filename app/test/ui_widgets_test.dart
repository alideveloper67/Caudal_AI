// Pruebas de los widgets sueltos de la interfaz, sin red y sin media_kit:
// el reproductor, la coleccion, los streams y las descargas son dobles.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/comunes.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _ReproductorFalso extends ChangeNotifier implements Reproductor {
  @override
  Json? actual;
  @override
  Json? contexto;
  @override
  EstadoRepro estado = EstadoRepro.parado;
  @override
  bool aleatorio = false;
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(Duration.zero);

  void sonar(Json p) {
    actual = p;
    estado = EstadoRepro.sonando;
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
  int get totalMeGusta => gustan.length;
  @override
  bool estaDescargada(Json pista) => false;
  @override
  bool guardado(String tipo, String id) => false;

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

Json _pista(int i, {bool video = false}) => {
      'tipo': 'pista',
      'clave': 'yt:id$i',
      'video_id': 'id$i',
      'titulo': 'Canción número $i con un título bastante largo para probar el corte',
      'artista': 'Artista $i',
      'artistas': [
        {'nombre': 'Artista $i', 'id': 'UC$i'}
      ],
      'miniatura': '',
      'es_video': video,
      'duracion': 200,
    };

late _ReproductorFalso _r;
late _ColeccionFalsa _col;

Future<void> _montar(WidgetTester t, Widget hijo, {double letra = 1.0, Size tam = const Size(1080, 2400)}) async {
  SharedPreferences.setMockInitialValues({});
  final ajustes = await Ajustes.cargar('prueba');
  _r = _ReproductorFalso();
  _col = _ColeccionFalsa();
  final s = Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
    ajustes: ajustes,
    coleccion: _col,
    reproductor: _r,
    streams: _StreamsFalsos(),
    descargas: _DescargasFalsas(),
    cerrarSesion: () async {},
  );
  t.view.physicalSize = tam;
  t.view.devicePixelRatio = 2.75;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(
    s: s,
    child: MaterialApp(
      theme: temaCaudal(),
      home: MediaQuery(
        data: MediaQueryData(size: tam / 2.75, textScaler: TextScaler.linear(letra)),
        child: Scaffold(body: ListView(children: [hijo])),
      ),
    ),
  ));
  await t.pump(const Duration(milliseconds: 300));
}

void main() {
  group('carruseles', () {
    testWidgets('tarjetas normales con la letra del sistema al 120 % no desbordan', (t) async {
      await _montar(
        t,
        Carrusel(titulo: 'Álbumes', elementos: [
          for (var i = 0; i < 4; i++)
            {'tipo': 'album', 'id': 'MPRE$i', 'titulo': 'Un álbum $i con nombre largo',
             'subtitulo': 'Álbum • Alguien muy conocido y otro artista invitado', 'miniatura': ''},
        ]),
        letra: 1.2,
      );
      expect(t.takeException(), isNull);
      expect(find.byType(Tarjeta), findsWidgets);
    });

    testWidgets('videos mezclados con canciones no desbordan', (t) async {
      await _montar(
        t,
        Carrusel(titulo: 'Mezcla', elementos: [
          _pista(1, video: true),
          _pista(2),
          {'tipo': 'lista', 'id': 'PL1', 'titulo': 'Lista', 'subtitulo': 'Lista • Alguien', 'miniatura': ''},
        ]),
        letra: 1.2,
      );
      expect(t.takeException(), isNull);
    });

    testWidgets('géneros mezclados con otras tarjetas usan la franja alta', (t) async {
      await _montar(
        t,
        Carrusel(titulo: 'Géneros', elementos: [
          {'tipo': 'genero', 'id': 'FEmusic_moods', 'params': 'x', 'titulo': 'Para sentirse bien', 'color': '#FF0000'},
          {'tipo': 'album', 'id': 'MPRE1', 'titulo': 'Álbum', 'subtitulo': 'Álbum • Alguien', 'miniatura': ''},
        ]),
      );
      expect(t.takeException(), isNull);
      expect(find.byType(TarjetaGenero), findsOneWidget);
    });

    testWidgets('la tarjeta de Tus me gusta se ajusta al ancho pedido', (t) async {
      await _montar(t, const Center(child: Tarjeta(el: {'tipo': 'me_gusta', 'titulo': 'Tus me gusta'}, ancho: 120)));
      expect(t.takeException(), isNull);
      expect(t.getSize(find.byType(PortadaMeGusta)).width, 120);
    });
  });

  group('secciones del catálogo', () {
    testWidgets('las vacías y las de solo texto no se pintan; las filas de canciones van en rejilla', (t) async {
      late List<Widget> pintadas;
      await _montar(
        t,
        Builder(builder: (context) {
          pintadas = pintarSecciones(context, [
            {'titulo': 'Vacía', 'estilo': 'carrusel', 'elementos': <Map<String, dynamic>>[], 'mas': null},
            {'titulo': 'Info', 'estilo': 'texto', 'texto': 'bla', 'elementos': <Map<String, dynamic>>[], 'mas': null},
            {'titulo': 'Rápida', 'estilo': 'filas', 'elementos': [for (var i = 0; i < 6; i++) _pista(i)], 'mas': null},
            {'titulo': 'Carrusel', 'estilo': 'carrusel', 'elementos': [_pista(9)],
             'mas': {'id': 'FEmusic_x', 'params': null}},
          ]);
          return Column(children: pintadas);
        }),
      );
      expect(t.takeException(), isNull);
      expect(find.byType(RejillaRapida), findsOneWidget);
      expect(find.byType(Carrusel), findsOneWidget);
      expect(find.text('Vacía'), findsNothing);
      expect(find.text('Info'), findsNothing);
      // "Ver todo" solo donde hay a donde ir
      expect(find.text('Ver todo'), findsOneWidget);
    });

    testWidgets('una sección en filas con algo que no es canción va como carrusel', (t) async {
      await _montar(
        t,
        Builder(builder: (context) => Column(children: pintarSecciones(context, [
              {'titulo': 'Mixta', 'estilo': 'filas', 'elementos': [
                _pista(1),
                {'tipo': 'album', 'id': 'MPRE1', 'titulo': 'Álbum', 'miniatura': ''},
              ], 'mas': null},
            ]))),
      );
      expect(t.takeException(), isNull);
      expect(find.byType(RejillaRapida), findsNothing);
      expect(find.byType(Carrusel), findsOneWidget);
    });
  });

  group('fila de canción', () {
    testWidgets('marca la que suena y el corazón cuando cambia la colección', (t) async {
      final p = _pista(1);
      await _montar(t, FilaPista(pista: p, alPulsar: () {}, numero: 1));
      expect(find.byIcon(Icons.favorite_rounded), findsNothing);
      expect(find.text('1'), findsOneWidget);

      _r.sonar(Map<String, dynamic>.from(p));
      _col.gustan.add('yt:id1');
      _col.notifyListeners();
      await t.pump();
      expect(find.byIcon(Icons.graphic_eq_rounded), findsOneWidget);
      expect(find.byIcon(Icons.favorite_rounded), findsOneWidget);
      final titulo = t.widget<Text>(find.textContaining('Canción número 1'));
      expect(titulo.style?.color, C.acento);
      expect(t.takeException(), isNull);
    });

    testWidgets('una pista sin artista ni datos raros no rompe la fila', (t) async {
      await _montar(t, FilaPista(pista: const {'tipo': 'pista', 'titulo': 'Sola'}, alPulsar: () {}));
      expect(find.text('Sola'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('la selección rápida cabe en un teléfono pequeño', (t) async {
      await _montar(t, RejillaRapida(titulo: 'Selección rápida', pistas: [for (var i = 0; i < 9; i++) _pista(i)]),
          tam: const Size(720, 1280), letra: 1.2);
      expect(t.takeException(), isNull);
      expect(find.byType(FilaPista), findsWidgets);
    });
  });

  group('navegación', () {
    testWidgets('ir al artista desde encima de todo (el reproductor) abre en la pestaña', (t) async {
      late BuildContext ctx;
      await _montar(t, Builder(builder: (c) {
        ctx = c;
        return const SizedBox();
      }));
      final s = Caudal.leer(ctx);
      Widget? abierta;
      s.abrirEnPestana = (w) => abierta = w;
      // el contexto de prueba esta en el navegador raiz, como el del reproductor
      s.irAArtista(ctx, 'UC123');
      expect(abierta, isNotNull);
      expect(abierta.runtimeType.toString(), 'ArtistaPagina');
    });
  });

  group('ids de listas', () {
    test('acepta enteros y textos, y no revienta con basura', () {
      expect(Servicios.idLista(7), 7);
      expect(Servicios.idLista('12'), 12);
      expect(Servicios.idLista(null), isNull);
      expect(Servicios.idLista('mi_lista'), isNull);
    });
  });

  group('pulido', () {
    testWidgets('lo que se pulsa se hunde un poco y vuelve a su tamaño', (t) async {
      var tocado = 0;
      await _montar(t, Center(child: Pulsable(escala: 0.9,
          child: GestureDetector(onTap: () => tocado++,
              child: const ColoredBox(color: Colors.red, child: SizedBox(width: 100, height: 100))))));
      double escala() => t.widget<ScaleTransition>(
          find.descendant(of: find.byType(Pulsable), matching: find.byType(ScaleTransition)).first).scale.value;
      final gesto = await t.startGesture(t.getCenter(find.byType(Pulsable)));
      await t.pump();
      await t.pump(const Duration(milliseconds: 200));
      expect(escala(), closeTo(0.9, 0.001));
      await gesto.up();
      await t.pumpAndSettle();
      expect(escala(), 1);
      expect(tocado, 1, reason: 'el toque sigue llegando al de dentro');
    });

    testWidgets('al desplazar con el dedo la escala se suelta', (t) async {
      await _montar(t, Center(child: Pulsable(escala: 0.9,
          child: GestureDetector(onTap: () {},
              child: const ColoredBox(color: Colors.red, child: SizedBox(width: 100, height: 100))))));
      final gesto = await t.startGesture(t.getCenter(find.byType(Pulsable)));
      await t.pump();
      await t.pump(const Duration(milliseconds: 200));
      await gesto.moveBy(const Offset(0, 40));
      await t.pumpAndSettle();
      expect(t.widget<ScaleTransition>(
          find.descendant(of: find.byType(Pulsable), matching: find.byType(ScaleTransition)).first).scale.value, 1);
      await gesto.up();
    });

    testWidgets('la entrada escalonada termina quieta y opaca, sin temporizadores colgando', (t) async {
      await _montar(t, const Escalonado(child: Column(children: [
        Entrada(indice: 0, child: Text('uno')),
        Entrada(indice: 5, child: Text('seis')),
      ])));
      await t.pumpAndSettle();
      for (final f in t.widgetList<FadeTransition>(find.byType(FadeTransition))) {
        expect(f.opacity.value, 1);
      }
      expect(find.text('seis'), findsOneWidget);
    });

    testWidgets('lo que se monta mucho después de llegar el contenido ya no se anima', (t) async {
      final mostrar = ValueNotifier(false);
      await _montar(t, Escalonado(child: ValueListenableBuilder<bool>(
        valueListenable: mostrar,
        builder: (_, v, _) => v ? const Entrada(child: Text('tarde')) : const SizedBox(),
      )));
      // la ventana se mide con el reloj de verdad
      await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: Entrada.ventana + 100)));
      mostrar.value = true;
      await t.pump();
      expect(find.descendant(of: find.byType(Entrada), matching: find.byType(FadeTransition)), findsNothing);
    });

    testWidgets('los esqueletos de cada forma caben sin desbordar', (t) async {
      for (final forma in FormaEsqueleto.values) {
        await _montar(t, Esqueleto(forma: forma), tam: const Size(720, 1280));
        expect(t.takeException(), isNull, reason: '$forma');
      }
    });

    testWidgets('un estado vacío con acción la ejecuta al tocar', (t) async {
      var veces = 0;
      await _montar(t, Vacio(icono: Icons.wifi_off_rounded, titulo: 'Sin conexión', texto: 'Vuelve a intentarlo',
          error: true, alAccion: () => veces++));
      await t.pumpAndSettle();
      await t.tap(find.text('Reintentar'));
      expect(veces, 1);
      expect(t.takeException(), isNull);
    });

    test('los errores técnicos se explican sin jerga', () {
      expect(explicarError('No se encontró a este artista en YouTube Music.'),
          'No se encontró a este artista en YouTube Music.');
      expect(explicarError('SocketException: Failed host lookup'), contains('conexión'));
      expect(explicarError("Null check operator used on a null value #0"), isNot(contains('Null')));
    });

    testWidgets('la cabecera plegable muestra el título pequeño solo al plegarse', (t) async {
      final scroll = ScrollController();
      addTearDown(scroll.dispose);
      await t.pumpWidget(MaterialApp(
        theme: temaCaudal(),
        home: Scaffold(
          body: CustomScrollView(controller: scroll, slivers: [
            const CabeceraPlegable(titulo: 'Un artista', color: Color(0xFF884422), alto: 320,
                fondo: ColoredBox(color: Colors.red)),
            SliverList.list(children: [for (var i = 0; i < 40; i++) SizedBox(height: 60, child: Text('fila $i'))]),
          ]),
        ),
      ));
      double opacidad() => t.widget<Opacity>(find.ancestor(of: find.text('Un artista'),
          matching: find.byType(Opacity)).first).opacity;
      expect(opacidad(), 0);
      scroll.jumpTo(600);
      await t.pump();
      expect(opacidad(), 1);
      expect(t.takeException(), isNull);
    });

    testWidgets('las pastillas de filtro avisan al tocarlas', (t) async {
      String? elegido;
      await _montar(t, Row(children: [
        Pildora(texto: 'Música', activa: false, alPulsar: () => elegido = 'musica'),
        const Pildora(texto: 'Videos', activa: true, alPulsar: _nada),
      ]));
      await t.tap(find.text('Música'));
      await t.pumpAndSettle();
      expect(elegido, 'musica');
    });
  });
}

void _nada() {}
