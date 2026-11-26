// La cola inteligente: reordenar arrastrando, quitar deslizando, «Guardar la
// cola como lista» y «Tocar después de esta». Lógica (cola_ops) y pantalla
// (HojaCola) sin media_kit: el reproductor y la colección son dobles que
// usan las mismas funciones de cola_ops que el reproductor de verdad.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/cola_ops.dart' as cola;
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/paginas/cola_hoja.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Json _p(int i, {bool auto = false}) => {
      'tipo': 'pista', 'clave': 'yt:id$i', 'video_id': 'id$i', 'titulo': 'Canción $i',
      'artista': 'Artista $i', 'miniatura': '', if (auto) '_auto': true,
    };

List<String> _claves(List<Json> l) => [for (final p in l) '${p['clave']}'.replaceFirst('yt:id', '')];

class _ReproductorFalso extends ChangeNotifier implements Reproductor {
  @override
  Json? actual = _p(0);
  @override
  Json? contexto = {'tipo': 'lista', 'id': '1', 'titulo': 'Mi mix'};
  @override
  EstadoRepro estado = EstadoRepro.sonando;
  @override
  int pos = 0;
  @override
  List<Json> proximas = [];
  @override
  List<Json> secuencia = [];
  @override
  List<Json> original = [];

  @override
  List<Json> get siguientesDeContexto => secuencia.sublist(pos + 1);

  final tocadasDespues = <String>[];

  @override
  Future<void> alternar() async {}
  @override
  void moverProxima(int de, int a) {
    cola.moverEnLista(proximas, de, a);
    notifyListeners();
  }

  @override
  void quitarProxima(int i) {
    proximas.removeAt(i);
    notifyListeners();
  }

  @override
  void insertarProxima(int i, Json p) {
    proximas.insert(i.clamp(0, proximas.length), p);
    notifyListeners();
  }

  @override
  void vaciarProximas() {
    proximas.clear();
    notifyListeners();
  }

  @override
  Future<void> saltarAProxima(int i) async {}
  @override
  Future<void> saltarA(int absoluto) async {}

  @override
  void moverEnSecuencia(int de, int a) {
    if (cola.moverEnSecuencia(secuencia, pos, de, a)) notifyListeners();
  }

  @override
  void quitarDeSecuencia(int absoluto) {
    secuencia.removeAt(absoluto);
    notifyListeners();
  }

  @override
  void insertarEnSecuencia(int absoluto, Json p) {
    secuencia.insert(absoluto.clamp(pos + 1, secuencia.length), p);
    notifyListeners();
  }

  @override
  void tocarDespues(Json p) {
    tocadasDespues.add('${p['clave']}');
    cola.tocarDespues(proximas, secuencia, original, pos, p);
    notifyListeners();
  }

  @override
  Future<void> dispose() async => super.dispose();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ColeccionFalsa extends ChangeNotifier implements Coleccion {
  final guardadas = <String, List<Json>>{};
  bool nombreOcupado = false;

  @override
  bool meGusta(String? clave) => false;
  @override
  bool estaDescargada(Json pista) => false;

  @override
  Future<int> crearLista(String nombre, {String descripcion = ''}) async {
    if (nombreOcupado || guardadas.containsKey(nombre)) {
      nombreOcupado = false;
      throw const FormatException('Ya tienes una lista con ese nombre.');
    }
    guardadas[nombre] = [];
    return guardadas.length;
  }

  @override
  Future<String> nombreLibre([String base = 'Mi lista']) async => '$base n.º 1';

  @override
  Future<int> agregarALista(int id, List<Json> nuevas) async {
    guardadas.values.elementAt(id - 1).addAll(nuevas);
    return nuevas.length;
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

late _ReproductorFalso _r;
late _ColeccionFalsa _col;
late Servicios _s;

/// Una cola de prueba: suena la 0; tuyas (manuales): 1, 2, 3; del contexto: 4, 5, 6;
/// automaticas: 7, 8.
Future<void> _montar(WidgetTester t) async {
  SharedPreferences.setMockInitialValues({});
  final ajustes = await Ajustes.cargar('prueba');
  _r = _ReproductorFalso()
    ..secuencia = [_p(0), _p(4), _p(5), _p(6), _p(7, auto: true), _p(8, auto: true)]
    ..proximas = [_p(1), _p(2), _p(3)];
  _r.original = List.of(_r.secuencia);
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
  t.view.physicalSize = const Size(1080, 2600);
  t.view.devicePixelRatio = 2.75;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(
    s: _s,
    child: MaterialApp(
      // sin salpicadura: su shader depende de como se compilaron los assets de prueba
      theme: temaCaudal().copyWith(splashFactory: NoSplash.splashFactory),
      scaffoldMessengerKey: _s.mensajero,
      home: const Scaffold(body: HojaCola()),
    ),
  ));
  await t.pump(const Duration(milliseconds: 300));
}

/// Arrastra el asa de la fila [de] (por su titulo) [dy] puntos hacia abajo.
Future<void> _arrastrar(WidgetTester t, String titulo, double dy) async {
  final fila = find.ancestor(of: find.text(titulo), matching: find.byType(Row)).first;
  final asa = find.descendant(
      of: find.ancestor(of: fila, matching: find.byType(Row)).first, matching: find.byIcon(Icons.drag_handle_rounded));
  final g = await t.startGesture(t.getCenter(asa.first));
  await t.pump(const Duration(milliseconds: 60));
  for (var i = 0; i < 6; i++) {
    await g.moveBy(Offset(0, dy / 6));
    await t.pump(const Duration(milliseconds: 30));
  }
  await g.up();
  await t.pump(const Duration(milliseconds: 100));
  await t.pumpAndSettle();
}

void main() {
  group('cola_ops (logica)', () {
    test('moverEnLista deja el elemento en la posicion final pedida', () {
      final l = [_p(1), _p(2), _p(3), _p(4)];
      cola.moverEnLista(l, 0, 2);
      expect(_claves(l), ['2', '3', '1', '4']);
      cola.moverEnLista(l, 3, 0);
      expect(_claves(l), ['4', '2', '3', '1']);
      expect(cola.moverEnLista(l, 9, 0), isFalse);
    });

    test('moverEnSecuencia no toca lo que ya sono ni lo que suena', () {
      final s = [_p(0), _p(1), _p(2), _p(3), _p(4)];
      expect(cola.moverEnSecuencia(s, 1, 1, 3), isFalse); // la que suena
      expect(cola.moverEnSecuencia(s, 1, 0, 3), isFalse); // ya sono
      expect(cola.moverEnSecuencia(s, 1, 2, 4), isTrue);
      expect(_claves(s), ['0', '1', '3', '4', '2']);
      // no se puede colar por delante de la que suena
      expect(cola.moverEnSecuencia(s, 1, 4, 0), isTrue);
      expect(_claves(s), ['0', '1', '2', '3', '4']);
    });

    test('tocarDespues pone la cancion justo detras de la que suena', () {
      final prox = [_p(1), _p(2)];
      final sec = [_p(0), _p(4), _p(5)];
      final orig = List.of(sec);
      cola.tocarDespues(prox, sec, orig, 0, _p(9));
      expect(_claves(prox), ['9', '1', '2']);
    });

    test('tocarDespues de una que ya esta en la cola la mueve, no la repite', () {
      final prox = [_p(1), _p(2)];
      final sec = [_p(0), _p(4), _p(5)];
      final orig = List.of(sec);
      cola.tocarDespues(prox, sec, orig, 0, prox[1]);
      expect(_claves(prox), ['2', '1']);
      cola.tocarDespues(prox, sec, orig, 0, _p(5));
      expect(_claves(prox), ['5', '2', '1']);
      expect(_claves(sec), ['0', '4']);
      expect(_claves(orig), ['0', '4']);
    });

    test('pistasDeLaCola: lo que suena, lo tuyo y el contexto; sin repetidas ni automaticas', () {
      final r = cola.pistasDeLaCola(_p(0), [_p(1), _p(2)], [_p(2), _p(4), _p(7, auto: true)]);
      expect(_claves(r), ['0', '1', '2', '4']);
    });

    test('guardarColaComoLista crea la lista y mete las canciones', () async {
      final c = _ColeccionFalsa();
      final (nombre, n) = await cola.guardarColaComoLista(c, [_p(1), _p(2)], '  Viernes ');
      expect(nombre, 'Viernes');
      expect(n, 2);
      expect(_claves(c.guardadas['Viernes']!), ['1', '2']);
    });

    test('si el nombre ya existe busca uno libre y no pierde la cola', () async {
      final c = _ColeccionFalsa()..guardadas['Viernes'] = [];
      final (nombre, n) = await cola.guardarColaComoLista(c, [_p(1)], 'Viernes');
      expect(nombre, 'Viernes n.º 1');
      expect(n, 1);
    });

    test('un nombre vacio se llama «Mi cola»', () async {
      final c = _ColeccionFalsa();
      final (nombre, _) = await cola.guardarColaComoLista(c, [_p(1)], '   ');
      expect(nombre, 'Mi cola');
    });
  });

  group('pantalla de la cola', () {
    testWidgets('muestra lo que suena, lo tuyo, el contexto y la reproduccion automatica', (t) async {
      await _montar(t);
      expect(find.text('Sonando ahora'), findsOneWidget);
      expect(find.text('Siguiente en tu cola'), findsOneWidget);
      expect(find.text('Siguiente de: Mi mix'), findsOneWidget);
      expect(find.text('Guardar como lista'), findsOneWidget);
      expect(find.text('Canción 1'), findsOneWidget);
      expect(find.text('Canción 4'), findsOneWidget);
      // tres asas para lo tuyo y tres para el contexto; la automatica no se reordena
      expect(find.byIcon(Icons.drag_handle_rounded), findsNWidgets(6));
      expect(t.takeException(), isNull);
    });

    testWidgets('arrastrar el asa reordena la cola manual', (t) async {
      await _montar(t);
      await _arrastrar(t, 'Canción 1', 130);
      expect(_r.proximas.first['clave'], isNot('yt:id1'));
      expect(_claves(_r.proximas).toSet(), {'1', '2', '3'});
      expect(_claves(_r.proximas).indexOf('1'), greaterThan(0));
      expect(t.takeException(), isNull);
    });

    testWidgets('arrastrar el asa reordena tambien lo que viene del contexto', (t) async {
      await _montar(t);
      await _arrastrar(t, 'Canción 4', 130);
      final orden = _claves(_r.secuencia);
      expect(orden.first, '0');
      expect(orden.indexOf('4'), greaterThan(1));
      expect(orden.toSet(), {'0', '4', '5', '6', '7', '8'});
      // las automaticas siguen al final
      expect(orden.sublist(orden.length - 2), ['7', '8']);
      expect(t.takeException(), isNull);
    });

    testWidgets('deslizar quita de la cola manual y «Deshacer» la devuelve', (t) async {
      await _montar(t);
      await t.fling(find.text('Canción 2'), const Offset(-600, 0), 2000);
      await t.pumpAndSettle();
      expect(_claves(_r.proximas), ['1', '3']);
      expect(find.text('Canción 2'), findsNothing);
      expect(find.text('Quitada de la cola'), findsOneWidget);
      await t.tap(find.text('Deshacer'));
      await t.pumpAndSettle();
      expect(_claves(_r.proximas), ['1', '2', '3']);
      expect(find.text('Canción 2'), findsOneWidget);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });

    testWidgets('deslizar quita una del contexto y «Deshacer» la pone en su sitio', (t) async {
      await _montar(t);
      await t.fling(find.text('Canción 5'), const Offset(-600, 0), 2000);
      await t.pumpAndSettle();
      expect(_claves(_r.secuencia), ['0', '4', '6', '7', '8']);
      await t.tap(find.text('Deshacer'));
      await t.pumpAndSettle();
      expect(_claves(_r.secuencia), ['0', '4', '5', '6', '7', '8']);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });

    testWidgets('«Guardar como lista» pregunta el nombre y guarda lo que suena y lo que viene', (t) async {
      await _montar(t);
      await t.tap(find.byKey(const ValueKey('guardar-cola')));
      await t.pumpAndSettle();
      expect(find.text('Guardar la cola como lista'), findsOneWidget);
      // viene con el nombre del contexto
      expect(find.widgetWithText(TextField, 'Mi mix'), findsOneWidget);
      await t.enterText(find.byKey(const ValueKey('nombre-cola')), 'Para el viernes');
      await t.tap(find.text('Guardar'));
      await t.pumpAndSettle();
      expect(_col.guardadas.keys, ['Para el viernes']);
      // la que suena, lo tuyo y el contexto: sin las automaticas
      expect(_claves(_col.guardadas['Para el viernes']!), ['0', '1', '2', '3', '4', '5', '6']);
      expect(find.textContaining('Cola guardada como «Para el viernes»'), findsOneWidget);
      await t.pump(const Duration(seconds: 4));
      expect(t.takeException(), isNull);
    });

    testWidgets('«Cancelar» no crea ninguna lista', (t) async {
      await _montar(t);
      await t.tap(find.byKey(const ValueKey('guardar-cola')));
      await t.pumpAndSettle();
      await t.tap(find.text('Cancelar'));
      await t.pumpAndSettle();
      expect(_col.guardadas, isEmpty);
    });

    testWidgets('con la cola vacia avisa en vez de guardar una lista vacia', (t) async {
      await _montar(t);
      _r.actual = null;
      _r.proximas.clear();
      _r.secuencia = [_p(0)];
      _r.notifyListeners();
      await t.pump();
      await t.tap(find.byKey(const ValueKey('guardar-cola')));
      await t.pumpAndSettle();
      expect(find.text('La cola está vacía.'), findsOneWidget);
      expect(_col.guardadas, isEmpty);
      await t.pump(const Duration(seconds: 4));
    });

    testWidgets('en el menu de una cancion de la cola esta «Tocar después de esta»', (t) async {
      await _montar(t);
      final fila = find.ancestor(of: find.text('Canción 5'), matching: find.byType(InkWell)).first;
      final menu = find.descendant(of: fila, matching: find.byIcon(Icons.more_vert_rounded));
      await t.tap(menu);
      await t.pumpAndSettle();
      expect(find.bySemanticsLabel('Tocar después de esta'), findsOneWidget);
      await t.tap(find.text('Después'));
      await t.pumpAndSettle();
      expect(_r.tocadasDespues, ['yt:id5']);
      // la 5 pasa a lo primero de lo tuyo y sale del contexto
      expect(_claves(_r.proximas), ['5', '1', '2', '3']);
      expect(_claves(_r.secuencia), ['0', '4', '6', '7', '8']);
      expect(t.takeException(), isNull);
    });
  });
}
