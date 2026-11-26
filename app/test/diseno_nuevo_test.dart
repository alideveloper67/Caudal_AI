// El Inicio y el reproductor nuevos: que la rejilla, las fichas de la cola y las pestañas hagan
// lo suyo y que nada se desborde en teléfonos pequeños y pantallas anchas.
// Con CAPTURAS=<carpeta> deja además una imagen de cada pantalla.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/estilo_reproductor.dart';
import 'package:caudal/nucleo/letras_cache.dart';
import 'package:caudal/nucleo/premium_letras.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/cast.dart';
import 'package:caudal/reproduccion/cola_ops.dart' as cola;
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/armazon.dart';
import 'package:caudal/ui/inicio_rejilla.dart';
import 'package:caudal/ui/paginas/inicio.dart';
import 'package:caudal/ui/paginas/reproductor_pagina.dart';
import 'package:caudal/nucleo/catalogo.dart';
import 'package:caudal/nucleo/recomendador.dart';
import 'package:caudal/ui/comunes.dart';
import 'package:caudal/ui/menu_hoja.dart';
import 'package:caudal/ui/paginas/biblioteca.dart';
import 'package:caudal/ui/paginas/buscar.dart';
import 'package:caudal/ui/reproductor/a_continuacion.dart';
import 'package:caudal/ui/reproductor/despliegue.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

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
  @override
  bool get puedeBajarVoz => false;
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(const Duration(seconds: 103));
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(const Duration(seconds: 269));
  @override
  List<Json> secuencia = [];
  @override
  List<Json> original = [];
  @override
  List<Json> proximas = [];
  @override
  int pos = 0;
  @override
  List<Json> get siguientesDeContexto => secuencia.skip(pos + 1).toList();
  @override
  int ordenarSiguientes(bool Function(Json)? cual) {
    final n = cual == null ? 0 : cola.adelantar(secuencia, pos, cual);
    if (cual == null) secuencia = List.of(original);
    notifyListeners();
    return n;
  }

  @override
  void quitarDeSecuencia(int i) {
    secuencia.removeAt(i);
    notifyListeners();
  }

  Json? adelantada;
  @override
  void tocarDespues(Json p) => adelantada = p;
  List<Json>? encoladas;
  @override
  void agregarACola(List<Json> pistas) => encoladas = pistas;
  int alternadas = 0, siguientes = 0;
  @override
  Future<void> alternar() async => alternadas++;
  @override
  Future<void> siguiente({bool automatico = false, bool porFallo = false}) async => siguientes++;
  int? saltado;
  @override
  Future<void> saltarA(int i) async => saltado = i;
  Json? pedida;
  @override
  Future<void> reproducirPista(Json pista, {Json? contexto, String? modo, bool conRadio = true}) async => pedida = pista;
  @override
  Future<void> buscar(Duration d) async {}
  @override
  Stream<String> get avisos => const Stream.empty();
  @override
  Future<void> dispose() async => super.dispose();
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

const _titulos = ['Oye Morena', 'Sugar On My Tongue', 'Házmelo', 'Lakenoshi', 'Orgasmo', 'Perdóname Yeyo', 'Tú vas sin (fav)',
  'Amor Sin Contrato', 'Chichabeba', 'Esta Noche (con Portavoz y más gente)', 'Cuatro Babys (con Trap Capos, Noriel, Bryant Myers y Juhn)',
  'Bésame Sin Sentir', 'Alas Rotas', 'Bendecido', '666', 'Las Noches'];

Json _p(int i) => {
      'tipo': 'pista',
      'clave': 'yt:video${'$i'.padLeft(6, '0')}',
      'video_id': 'video${'$i'.padLeft(6, '0')}',
      'titulo': _titulos[i % _titulos.length],
      'artista': i.isEven ? 'Cidtronyck, Niel Brown' : 'Maluma',
      'artistas': [{'nombre': i.isEven ? 'Cidtronyck' : 'Maluma', 'id': 'a${i % 2}'}],
      'duracion': 137 + i * 13,
      'explicito': i % 3 == 0,
      'miniatura': 'mem:prueba:${i % 8}',
    };

Future<void> _fuentes() async {
  Future<ByteData> f(String r) => File(r).readAsBytes().then((b) => ByteData.view(b.buffer));
  const base = 'C:/Users/USER/FlutterSDK/flutter/bin/cache/artifacts/material_fonts';
  if (!File('$base/roboto-regular.ttf').existsSync()) return;
  final r = FontLoader('Roboto');
  for (final n in ['regular', 'medium', 'bold', 'black']) {
    r.addFont(f('$base/roboto-$n.ttf'));
  }
  await r.load();
  await (FontLoader('MaterialIcons')..addFont(f('$base/materialicons-regular.otf'))).load();
}

void _portadas() {
  for (var i = 0; i < 8; i++) {
    final im = img.Image(width: 240, height: 240);
    for (final px in im) {
      final t = (px.x + px.y) / 480;
      px
        ..r = (40 + 25 * i + 120 * t).clamp(0, 255).toInt()
        ..g = (200 - 24 * i * t).clamp(0, 255).toInt() ~/ (i.isEven ? 1 : 2)
        ..b = (60 + (i * 53) % 190).toInt();
    }
    img.fillCircle(im, x: 120, y: 110, radius: 60 + i * 4, color: img.ColorRgb8(250 - i * 20, 235, 90 + i * 18));
    PortadasMem.poner('mem:prueba:$i', Uint8List.fromList(img.encodePng(im)));
  }
}

final _carpeta = Platform.environment['CAPTURAS'];
final _llave = GlobalKey();

Future<void> _captura(WidgetTester t, String nombre) async {
  final c = _carpeta;
  if (c == null) return;
  for (var i = 0; i < 3; i++) {
    await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 80)));
    await t.pump(const Duration(milliseconds: 60));
  }
  await t.runAsync(() async {
    final ro = _llave.currentContext!.findRenderObject() as RenderRepaintBoundary;
    final im = await ro.toImage(pixelRatio: 1.5);
    final b = await im.toByteData(format: ui.ImageByteFormat.png);
    Directory(c).createSync(recursive: true);
    File('$c/$nombre.png').writeAsBytesSync(b!.buffer.asUint8List());
  });
}

late _R _r;
late Coleccion _col;
late Directory _tmp;
var _n = 0;
late Servicios _s;

Future<void> _montar(WidgetTester t, Widget hijo, {Size tam = const Size(390, 844), Map<String, Object> prefs = const {}}) async {
  SharedPreferences.setMockInitialValues(prefs);
  // cada prueba con su copia: lo que deje a medias no estorba a la siguiente
  final copia = '${_tmp.path}/c${_n++}.db';
  File('${_tmp.path}/c.db').copySync(copia);
  _col = (await t.runAsync(() => Coleccion.abrirEn(copia)))!;
  _portadas();
  final ajustes = await Ajustes.cargar('prueba');
  _r = _R()
    ..actual = _p(9)
    ..contexto = {'tipo': 'radio', 'id': 'x', 'titulo': 'Mix de Amor Sin Contrato'}
    ..secuencia = [_p(9), for (var i = 10; i < 24; i++) _p(i)];
  _r.original = List.of(_r.secuencia);
  _s = Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Aligeri'),
    ajustes: ajustes,
    coleccion: _col,
    reproductor: _r,
    streams: _Str(),
    descargas: _Desc(),
    cerrarSesion: () async {},
  );
  t.view.physicalSize = tam;
  t.view.devicePixelRatio = 1;
  t.view.padding = const FakeViewPadding(top: 40);
  addTearDown(t.view.reset);
  await t.pumpWidget(RepaintBoundary(
    key: _llave,
    child: Caudal(
      s: _s,
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: temaCaudal().copyWith(splashFactory: NoSplash.splashFactory),
        scaffoldMessengerKey: _s.mensajero,
        home: hijo,
      ),
    ),
  ));
  for (var i = 0; i < 6; i++) {
    await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 120)));
    await t.pump(const Duration(milliseconds: 250));
  }
}

Future<void> _desmontar(WidgetTester t) async {
  await t.pumpWidget(const SizedBox.shrink());
  // lo que Inicio dejó pidiendo a la base acaba antes de cerrar la prueba
  for (var i = 0; i < 60; i++) {
    await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 4)));
    await t.pump(const Duration(milliseconds: 200));
  }
  await t.pump(const Duration(minutes: 3)); // lo que el historial guarda un rato en memoria
}

void main() {
  final antes = esPremiumLetras;

  setUpAll(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfiNoIsolate;
    _tmp = Directory.systemTemp.createTempSync('diseno');
    _col = await Coleccion.abrirEn('${_tmp.path}/c.db');
    for (var i = 0; i < 16; i++) {
      await _col.recordar(_p(i));
      for (var k = 0; k <= i % 4; k++) {
        await _col.db.insert('reproducciones',
            {'clave': _p(i)['clave'], 'fecha': DateTime.now().millisecondsSinceEpoch / 1000 - i * 4000 - k * 90000});
      }
    }
    await _col.guardarEstado('catalogo_inicio', {
      'secciones': [
        {'titulo': 'Mixes de canciones', 'estilo': 'filas', 'elementos': [for (var i = 0; i < 12; i++) _p(i + 3)]},
        {'titulo': 'Álbumes para ti', 'estilo': 'carrusel', 'elementos': [
          for (var i = 0; i < 6; i++) {'tipo': 'album', 'id': 'al$i', 'titulo': 'Álbum $i', 'subtitulo': 'Maluma', 'miniatura': 'mem:prueba:$i'}]},
      ],
    });
    await _col.guardarEstado('fichas_animo', {
      'idioma': 'en', 'cuando': DateTime.now().millisecondsSinceEpoch,
      'lista': [for (final x in ['Podcasts', 'Relajación', 'Entrenamiento', 'Actívate']) {'tipo': 'genero', 'id': x, 'titulo': x}],
    });
    final hoy = DateTime.now();
    await _col.guardarEstado(Recomendador.claveParecidos, {
      'dia': '${hoy.year}-${hoy.month}-${hoy.day}',
      'lista': [for (final (i, n) in ['Ape Drums', 'Randy Nota Loca', 'Micro TDH', 'Deyco', 'Gonzalo Genek'].indexed)
        {'tipo': 'artista', 'id': 'ap$i', 'titulo': n, 'subtitulo': 'Parecido a Maluma', 'miniatura': 'mem:prueba:$i'}],
    });
    await _fuentes(); // con la letra de verdad: la de las pruebas es el doble de ancha
    await _col.db.close();
  });
  tearDownAll(() async {
    try {
      _tmp.deleteSync(recursive: true);
    } catch (_) {}
  });
  setUp(() {
    PreferenciasReproductor.i.reiniciarParaPruebas();
    esPremiumLetras = () => false;
    LetrasCache.i.cargador = (_) async => {'texto': 'Esta noche te quiero ver\nBailando lento\nSin pensar en el ayer', 'lineas': []};
  });
  tearDown(() => esPremiumLetras = antes);

  group('rejilla de Inicio', () {
    test('mezcla atajos y canciones sin repetir', () {
      final l = elementosDeInicio(
          [{'tipo': 'me_gusta', 'titulo': 'Tus me gusta'}, {'tipo': 'album', 'id': '1', 'titulo': 'A'}, {'tipo': 'album', 'id': '1', 'titulo': 'A'}],
          [_p(0), _p(1), _p(0), _p(16)]);
      // _p(16) es otro video de la misma canción y artista que _p(0)
      expect([for (final e in l) e['titulo']], ['Tus me gusta', 'Oye Morena', 'Sugar On My Tongue', 'A']);
      expect(elementosDeInicio([], [for (var i = 0; i < 16; i++) _p(i)], maximo: 9), hasLength(9));
      expect(elementosDeInicio([], []), isEmpty);
    });

    test('tres por tres en el teléfono; más columnas en pantallas anchas', () {
      expect(RejillaInicio.forma(390), (3, 3));
      expect(RejillaInicio.forma(1000).$2, 2);
      expect(RejillaInicio.forma(3000).$1, 9);
    });

    test('lo que más escuchas ahora pesa más que lo viejo', () async {
      File('${_tmp.path}/c.db').copySync('${_tmp.path}/suelta.db');
      _col = await Coleccion.abrirEn('${_tmp.path}/suelta.db');
      final l = await _col.masEscuchadasAhora(5);
      expect(l, hasLength(5));
      expect(await _col.clavesConocidas(), contains(_p(3)['clave']));
    });
  });

  for (final tam in const [Size(320, 568), Size(390, 844), Size(820, 1180), Size(1280, 800)]) {
    testWidgets('Inicio a ${tam.width.toInt()}x${tam.height.toInt()}: rejilla, fichas y filas sin desbordes', (t) async {
      await _montar(t, const InicioPagina(), tam: tam);
      expect(find.byType(RejillaInicio), findsOneWidget);
      expect(find.text('Relajación'), findsOneWidget);
      await _captura(t, 'inicio_${tam.width.toInt()}');
      await t.drag(find.byType(CustomScrollView).first, const Offset(0, -520));
      await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600));
      await _captura(t, 'inicio_${tam.width.toInt()}_abajo');
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });

    testWidgets('reproductor a ${tam.width.toInt()}x${tam.height.toInt()}: carátula, controles y lo que sigue', (t) async {
      await _montar(t, const ReproductorPagina(), tam: tam);
      expect(find.byType(PestanasReproductor), findsOneWidget);
      await _captura(t, 'reproductor_${tam.width.toInt()}');
      expect(find.text('Mix de Amor Sin Contrato', skipOffstage: false), findsWidgets);
      await t.drag(find.byType(CustomScrollView).first, const Offset(0, -420));
      await t.pump(const Duration(milliseconds: 600));
      await _captura(t, 'reproductor_${tam.width.toInt()}_abajo');
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });
  }

  testWidgets('la que suena se marca en la rejilla, y tocar otra la pone', (t) async {
    await _montar(t, const InicioPagina());
    final celdas = find.byType(CeldaInicio);
    expect(celdas, findsWidgets);
    final otra = t.widgetList<CeldaInicio>(celdas).firstWhere((c) => c.el['tipo'] == 'pista' && c.el['clave'] != _p(9)['clave']);
    await t.tap(find.byWidget(otra));
    await t.pump(const Duration(milliseconds: 300));
    expect(_r.pedida?['clave'], otra.el['clave']);
    expect(find.descendant(of: find.byWidget(otra), matching: find.byIcon(Icons.graphic_eq_rounded)), findsNothing);
    _r.actual = otra.el;
    _r.notifyListeners();
    await t.pump(const Duration(milliseconds: 100));
    expect(find.descendant(of: find.byWidget(otra), matching: find.byIcon(Icons.graphic_eq_rounded)), findsOneWidget);
    await _desmontar(t);
  });

  testWidgets('las fichas ponen delante lo elegido sin quitar nada, y «Todo» lo deja como estaba', (t) async {
    await _montar(t, const ReproductorPagina(), tam: const Size(390, 1600));
    final antes = [for (final p in _r.secuencia) '${p['clave']}'];
    await t.drag(find.byType(FichasCola), const Offset(-600, 0));
    await t.pump(const Duration(milliseconds: 500));
    await t.tap(find.text('De Maluma'));
    await t.pump(const Duration(milliseconds: 300));
    expect(_r.secuencia.skip(1).take(7).every((p) => p['artista'] == 'Maluma'), isTrue);
    expect({for (final p in _r.secuencia) '${p['clave']}'}, antes.toSet());
    await t.drag(find.byType(FichasCola), const Offset(900, 0));
    await t.pump(const Duration(milliseconds: 500));
    await t.tap(find.text('Todo'));
    await t.pump(const Duration(milliseconds: 300));
    expect([for (final p in _r.secuencia) '${p['clave']}'], antes);
    await _desmontar(t);
  });

  testWidgets('tocar una fila salta a ella; «Letra» se recuerda', (t) async {
    await _montar(t, const ReproductorPagina(), tam: const Size(390, 1600));
    await t.tap(find.text('Bésame Sin Sentir').first);
    expect(_r.saltado, 2);
    await t.tap(find.text('Letra'));
    await t.pump(const Duration(milliseconds: 500));
    await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 100)));
    await t.pump(const Duration(milliseconds: 300));
    expect(find.byType(FilaCola), findsNothing);
    expect((await SharedPreferences.getInstance()).getBool('reproductor_abajo_letra'), isTrue);
    await _captura(t, 'reproductor_letra');
    await t.tap(find.text('A continuación'));
    await t.pump(const Duration(milliseconds: 300));
    expect(find.byType(FilaCola), findsWidgets);
    expect(t.takeException(), isNull);
    await _desmontar(t);
  });

  testWidgets('en reposo se ven los controles, el asa y tres canciones; jalando, la lista con su cabecera fija', (t) async {
    await _montar(t, const ReproductorPagina());
    expect(find.byType(AsaDespliegue), findsOneWidget);
    final enteras = [
      for (final e in find.byType(FilaCola).evaluate())
        if (t.getRect(find.byWidget(e.widget)).bottom <= 844) e
    ];
    expect(enteras.length, greaterThanOrEqualTo(3));
    expect(t.getSize(find.byType(FilaCola).first).height, greaterThanOrEqualTo(48));
    expect(find.byType(CabeceraCompacta), findsNothing);
    await _captura(t, 'reproductor_reposo');
    // un tirón corto y rápido la despliega entera
    await t.fling(find.byType(FilaCola).first, const Offset(0, -120), 900);
    await t.pump();
    await t.pump(const Duration(seconds: 2));
    await t.pump(const Duration(milliseconds: 300));
    expect(find.byType(CabeceraCompacta), findsOneWidget);
    final cab = t.getRect(find.byType(CabeceraCompacta));
    expect(cab.top, 0);
    expect(t.getRect(find.byType(PestanasReproductor)).top, closeTo(cab.bottom, 2));
    expect(find.byType(FilaCola).evaluate().length, greaterThan(6));
    await _captura(t, 'reproductor_desplegado');
    // se sigue mandando desde ahí
    await t.tap(find.byTooltip('Reproducir o pausar'));
    await t.tap(find.byTooltip('Siguiente').last);
    expect((_r.alternadas, _r.siguientes), (1, 1));
    // bien dentro de la lista, un impulso hacia abajo se queda en su principio (no cae a la carátula)
    await t.drag(find.byType(FilaCola).at(3), const Offset(0, -300));
    await t.pump(const Duration(seconds: 1));
    await t.fling(find.byType(FilaCola).at(4), const Offset(0, 200), 3000);
    await t.pump();
    await t.pump(const Duration(seconds: 2));
    expect(find.byType(CabeceraCompacta), findsOneWidget);
    expect(t.getRect(find.byType(PestanasReproductor)).top, closeTo(cab.bottom, 3));
    // y tocar la cabecera la recoge, sin cerrar el reproductor
    await t.tapAt(Offset(cab.left + 120, cab.bottom - 34));
    await t.pump();
    await t.pump(const Duration(seconds: 1));
    expect(find.byType(CabeceraCompacta), findsNothing);
    expect(find.byType(ReproductorPagina), findsOneWidget);
    expect(t.takeException(), isNull);
    await _desmontar(t);
  });

  testWidgets('recoger la lista de un tirón largo no cierra el reproductor; tirando desde arriba, sí', (t) async {
    await _montar(t, Builder(builder: (c) => Scaffold(body: Center(child: FilledButton(
        onPressed: () => _s.abrirReproductor(c), child: const Text('abrir'))))));
    await t.tap(find.text('abrir'));
    await t.pump();
    await t.pump(const Duration(seconds: 1));
    await t.fling(find.byType(FilaCola).first, const Offset(0, -150), 1200);
    await t.pump();
    await t.pump(const Duration(seconds: 2));
    expect(find.byType(CabeceraCompacta), findsOneWidget);
    await t.dragFrom(const Offset(195, 300), const Offset(0, 520));
    await t.pump();
    await t.pump(const Duration(seconds: 2));
    expect(find.byType(ReproductorPagina), findsOneWidget);
    expect(find.byType(CabeceraCompacta), findsNothing);
    await t.dragFrom(const Offset(195, 200), const Offset(0, 400));
    await t.pump();
    await t.pump(const Duration(seconds: 1));
    await t.pump(const Duration(seconds: 1));
    expect(find.byType(ReproductorPagina), findsNothing);
    expect(t.takeException(), isNull);
    await _desmontar(t);
  });

  testWidgets('deslizar una fila: a la derecha suena después, a la izquierda se quita', (t) async {
    await _montar(t, const ReproductorPagina());
    final fila = find.byType(FilaCola).at(1);
    final p = t.widget<FilaCola>(fila).pista;
    final antes = _r.secuencia.length;
    await t.drag(fila, const Offset(220, 0));
    for (var i = 0; i < 8; i++) {
      await t.pump(const Duration(milliseconds: 120));
    }
    expect(_r.adelantada?['clave'], p['clave']);
    expect(_r.secuencia.length, antes);
    await t.drag(find.byType(FilaCola).at(1), const Offset(-260, 0));
    for (var i = 0; i < 8; i++) {
      await t.pump(const Duration(milliseconds: 120));
    }
    expect(_r.secuencia.length, antes - 1);
    expect(_r.secuencia.any((x) => x['clave'] == p['clave']), isFalse);
    await t.pump(const Duration(seconds: 6));
    expect(t.takeException(), isNull);
    await _desmontar(t);
  });

  for (final tam in const [Size(320, 568), Size(390, 844), Size(820, 1180), Size(1280, 800)]) {
    testWidgets('el menú de una canción a ${tam.width.toInt()}: acciones grandes y filas cómodas', (t) async {
      await _montar(t, Builder(builder: (c) => Scaffold(body: Center(child: FilledButton(
          onPressed: () => _s.hojaPista(c, _p(10)), child: const Text('abrir'))))), tam: tam);
      await t.tap(find.text('abrir'));
      await t.pump();
      await t.pump(const Duration(milliseconds: 600));
      await _captura(t, 'menu_${tam.width.toInt()}');
      for (final x in ['Me gusta', 'Después', 'A la cola', 'Descargar', 'Compartir', 'Añadir a una lista']) {
        expect(find.text(x), findsOneWidget, reason: x);
      }
      final fila = find.ancestor(of: find.text('Añadir a una lista'), matching: find.byType(InkWell)).first;
      expect(t.getSize(fila).height, greaterThanOrEqualTo(52));
      expect(t.getSize(find.ancestor(of: find.text('A la cola'), matching: find.byType(InkWell)).first).height,
          greaterThanOrEqualTo(64));
      await t.tap(find.text('A la cola'));
      await t.pump(const Duration(milliseconds: 600));
      expect(_r.encoladas?.single['clave'], _p(10)['clave']);
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });
  }

  testWidgets('mantener un artista (o una lista, un álbum) abre su menú, con Seguir', (t) async {
    await _montar(t, const InicioPagina());
    await t.scrollUntilVisible(find.text('Artistas parecidos a los que escuchas'), 300,
        scrollable: find.byType(Scrollable).first);
    await t.pump(const Duration(seconds: 1));
    await t.drag(find.byType(CustomScrollView).first, const Offset(0, -200));
    await t.pump(const Duration(seconds: 1));
    await _captura(t, 'inicio_parecidos');
    expect(find.text('Parecido a Maluma'), findsWidgets);
    await t.longPress(find.text('Randy Nota Loca'));
    await t.pump(const Duration(milliseconds: 700));
    await _captura(t, 'menu_artista');
    expect(find.text('Seguir'), findsOneWidget);
    await t.runAsync(() async {
      await t.tap(find.text('Seguir'));
      await Future<void>.delayed(const Duration(milliseconds: 200));
    });
    await t.pump(const Duration(milliseconds: 700));
    expect(_col.guardado('artista', 'ap1'), isTrue);
    expect(t.takeException(), isNull);
    await _desmontar(t);
  });

  for (final ancho in const [320.0, 390.0, 820.0]) {
    testWidgets('Buscar y Biblioteca a ${ancho.toInt()} sin desbordes', (t) async {
      await _montar(t, const BuscarPagina(), tam: Size(ancho, 844));
      await _captura(t, 'buscar_${ancho.toInt()}');
      expect(t.takeException(), isNull);
      await _desmontar(t);
      await _montar(t, const BibliotecaPagina(), tam: Size(ancho, 844));
      await _captura(t, 'biblioteca_${ancho.toInt()}');
      expect(t.takeException(), isNull);
      await _desmontar(t);
    });
  }

  group('artistas parecidos', () {
    Json a(String id, [String? n]) => {'tipo': 'artista', 'id': id, 'titulo': n ?? 'Art $id', 'miniatura': 'm$id'};
    final semillas = [
      {'id': 's1', 'nombre': 'Uno', 'veces': 30},
      {'id': 's2', 'nombre': 'Dos', 'veces': 10},
    ];

    test('gana el que señalan varios; fuera los tuyos y los repetidos; tope por semilla', () {
      final l = Recomendador.ordenarParecidos(semillas, {
        's1': [a('x1'), a('x2'), a('x3'), a('x4'), a('x5'), a('comun'), a('s2'), a('mio'), a('x1')],
        's2': [a('comun'), a('y1'), a('z', 'Art x1')],
      }, {'s1', 's2', 'mio'});
      final ids = [for (final e in l) e['id']];
      expect(ids.first, 'comun');
      expect(l.first['subtitulo'], 'Parecido a Uno');
      expect(ids.where((x) => '$x'.startsWith('x')).length, 4, reason: 'tope 4 de una sola semilla');
      expect(ids, isNot(contains('mio')));
      expect(ids, isNot(contains('s2')));
      expect(ids, isNot(contains('z')), reason: 'mismo nombre que otro');
      expect(ids.toSet().length, ids.length);
    });

    test('veinte como mucho, y nada si no hay de quién partir', () {
      final muchas = [for (var i = 0; i < 8; i++) {'id': 'm$i', 'nombre': 'M$i', 'veces': 1}];
      final l = Recomendador.ordenarParecidos(
          muchas, {for (var i = 0; i < 8; i++) 'm$i': [for (var k = 0; k < 9; k++) a('p$i-$k')]}, {});
      expect(l, hasLength(20));
      expect(Recomendador.ordenarParecidos([], {}, {}), isEmpty);
    });

    test('una vez al día, guardado; sin red no sale', () async {
      File('${_tmp.path}/c.db').copySync('${_tmp.path}/par.db');
      final c = await Coleccion.abrirEn('${_tmp.path}/par.db');
      await c.guardarEstado(Recomendador.claveParecidos, null);
      var pedidas = 0;
      Recomendador.paginaArtista = (_) async => throw Exception('sin red');
      expect(await Recomendador.artistasParecidos(c), isEmpty);
      Recomendador.paginaArtista = (id) async {
        pedidas++;
        return {'secciones': [{'titulo': 'También les gusta', 'elementos': [a('n1'), a('n2'), a('n3'), a('a0', 'Cidtronyck')]}]};
      };
      final l = await Recomendador.artistasParecidos(c);
      expect([for (final e in l) e['id']], ['n1', 'n2', 'n3']);
      final n = pedidas;
      expect(await Recomendador.artistasParecidos(c), hasLength(3));
      expect(pedidas, n, reason: 'lo del día ya estaba guardado');
      Recomendador.paginaArtista = Catalogo.artista;
    });
  });

  testWidgets('el mini va pegado a la barra y de lado a lado', (t) async {
    await _montar(t, const Scaffold(body: Align(alignment: Alignment.bottomCenter, child: MiniReproductor())));
    final r = t.getRect(find.byType(MiniReproductor));
    expect(r.width, 390);
    await _captura(t, 'mini');
    expect(t.takeException(), isNull);
    await _desmontar(t);
  });

  test('adelantar conserva el orden y no toca lo que ya sonó', () {
    final s = [for (var i = 0; i < 6; i++) _p(i)];
    expect(cola.adelantar(s, 1, (p) => p['artista'] == 'Maluma'), 2);
    expect([for (final p in s) p['titulo']], [_titulos[0], _titulos[1], _titulos[3], _titulos[5], _titulos[2], _titulos[4]]);
    expect(cola.adelantar(s, 5, (_) => true), 0);
    expect(cola.adelantar(s, 1, (_) => false), 0);
  });
}
