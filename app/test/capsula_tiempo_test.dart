// Cápsula del tiempo (donadores): fechas, límites, guardado por cuenta en el teléfono, tarjeta al abrir la
// app, lista y hoja para crear. Todo local: no hay red de por medio.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/capsula_tiempo.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/premium.dart';
import 'package:caudal/nucleo/social.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/premium/capsula_ui.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _c1 = CancionFav(videoId: 'abc12345678', titulo: 'Canción de hace un año con un título largo para probar el recorte',
    artista: 'Una artista con nombre largo', miniatura: '');
const _c2 = CancionFav(videoId: 'xyz98765432', titulo: 'Otra', artista: 'Otro', miniatura: '');

class _Reproductor extends ChangeNotifier implements Reproductor {
  @override
  Json? actual;
  final reproducidas = <Json>[];

  @override
  Future<void> reproducirPista(Json pista, {Json? contexto, String? modo, bool conRadio = true}) async =>
      reproducidas.add(pista);

  @override
  Future<void> dispose() async => super.dispose();
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Coleccion extends ChangeNotifier implements Coleccion {
  @override
  Future<List<Json>> meGustaRecientes(int n) async => [
        {'tipo': 'pista', 'clave': 'yt:fav00000001', 'video_id': 'fav00000001', 'titulo': 'Mi favorita', 'artista': 'Alguien', 'miniatura': ''}
      ];
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Streams implements Streams {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Descargas extends ChangeNotifier implements GestorDescargas {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

late _Reproductor _r;

Future<Servicios> _montar(WidgetTester t, Widget hijo, {Size tam = const Size(411, 900), double letra = 1}) async {
  _r = _Reproductor();
  final s = Servicios(
    cuenta: Cuenta(id: 'yo', usuario: 'yo', nombre: 'Yo', sesion: null),
    ajustes: await Ajustes.cargar('prueba'),
    coleccion: _Coleccion(),
    reproductor: _r,
    streams: _Streams(),
    descargas: _Descargas(),
    cerrarSesion: () async {},
  );
  t.view.physicalSize = tam * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(
    s: s,
    child: MaterialApp(
      scaffoldMessengerKey: s.mensajero,
      theme: temaCaudal(),
      builder: (context, h) =>
          MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(letra)), child: h!),
      home: hijo,
    ),
  ));
  await t.pump(const Duration(milliseconds: 200));
  return s;
}

void _donador() => Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');

void main() {
  final hoy = DateTime(2026, 11, 19, 10, 30);

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    Premium.i.reiniciar();
    await CapsulasTiempo.i.iniciar('yo');
  });

  group('Fechas', () {
    test('un año después: el mismo día; el 29 de febrero cae en el 28', () {
      expect(CapsulaTiempo.unAnioDespues(DateTime(2026, 11, 19, 23, 59)), DateTime(2027, 11, 19));
      expect(CapsulaTiempo.unAnioDespues(DateTime(2028, 2, 29)), DateTime(2029, 2, 28));
      expect(CapsulaTiempo.unAnioDespues(DateTime(2027, 12, 31)), DateTime(2028, 12, 31));
      expect(CapsulaTiempo.unAnioDespues(DateTime(2023, 2, 28)), DateTime(2024, 2, 28));
    });

    test('meses después: si el mes es más corto, el último día', () {
      expect(CapsulaTiempo.masMeses(DateTime(2026, 1, 31), 1), DateTime(2026, 2, 28));
      expect(CapsulaTiempo.masMeses(DateTime(2026, 11, 19), 3), DateTime(2027, 2, 19));
      expect(CapsulaTiempo.masMeses(DateTime(2026, 11, 19), 60), DateTime(2031, 11, 19));
      expect(CapsulaTiempo.masMeses(DateTime(2026, 12, 15), 1), DateTime(2027, 1, 15));
    });

    test('mañana y el límite de 10 años', () {
      expect(CapsulaTiempo.manana(hoy), DateTime(2026, 11, 20));
      expect(CapsulaTiempo.masLejos(hoy), DateTime(2036, 11, 19));
      expect(CapsulaTiempo.manana(DateTime(2026, 12, 31)), DateTime(2027, 1, 1));
    });

    test('días que faltan se cuentan por fecha, no por horas', () {
      final c = CapsulaTiempo(id: 'a', cancion: _c1, mensaje: '', creada: hoy, abre: DateTime(2026, 11, 20));
      expect(c.diasFaltan(DateTime(2026, 11, 19, 23, 59)), 1);
      expect(c.diasFaltan(DateTime(2026, 11, 20, 0, 1)), 0);
      expect(c.diasFaltan(DateTime(2026, 12, 1)), 0);
      expect(c.lista(DateTime(2026, 11, 19, 23, 59)), isFalse);
      expect(c.lista(DateTime(2026, 11, 20)), isTrue);
    });

    test('«hace cuánto» se dice en palabras', () {
      CapsulaTiempo desde(DateTime creada) => CapsulaTiempo(id: 'a', cancion: _c1, mensaje: '', creada: creada, abre: hoy);
      expect(desde(hoy).haceCuanto(hoy), 'Hoy');
      expect(desde(hoy.subtract(const Duration(days: 1))).haceCuanto(hoy), 'Hace un día');
      expect(desde(hoy.subtract(const Duration(days: 12))).haceCuanto(hoy), 'Hace 12 días');
      expect(desde(hoy.subtract(const Duration(days: 62))).haceCuanto(hoy), 'Hace 2 meses');
      expect(desde(DateTime(2025, 11, 19, 10)).haceCuanto(hoy), 'Hace un año');
      expect(desde(DateTime(2023, 11, 19)).haceCuanto(hoy), 'Hace 3 años');
    });

    test('cuándo se abre, en palabras', () {
      CapsulaTiempo para(DateTime a) => CapsulaTiempo(id: 'a', cancion: _c1, mensaje: '', creada: hoy, abre: a);
      expect(cuandoSeAbre(para(DateTime(2026, 11, 19)), hoy), 'Se abre hoy');
      expect(cuandoSeAbre(para(DateTime(2026, 11, 20)), hoy), 'Se abre mañana');
      expect(cuandoSeAbre(para(DateTime(2026, 12, 1)), hoy), 'Se abre en 12 días · 1 de diciembre de 2026');
      expect(cuandoSeAbre(para(DateTime(2027, 11, 19)), hoy), 'Se abre el 19 de noviembre de 2027');
    });
  });

  group('Guardar y límites', () {
    test('por defecto se abre dentro de un año', () async {
      final r = await CapsulasTiempo.i.crear(cancion: _c1, mensaje: '  Hola yo del futuro  ', ahora: hoy, premium: true);
      expect(r.ok, isTrue);
      expect(r.capsula!.abre, DateTime(2027, 11, 19));
      expect(r.capsula!.mensaje, 'Hola yo del futuro');
      expect(CapsulasTiempo.i.guardadas.length, 1);
    });

    test('exclusivo de donadores', () async {
      final r = await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'x', ahora: hoy);
      expect(r.problema, ProblemaCapsula.sinPremium);
      expect(r.mensaje, contains('donadores'));
      _donador();
      expect((await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'x', ahora: hoy)).ok, isTrue);
    });

    test('hace falta una canción en línea', () async {
      expect((await CapsulasTiempo.i.crear(cancion: null, mensaje: 'x', ahora: hoy, premium: true)).problema, ProblemaCapsula.sinCancion);
      expect((await CapsulasTiempo.i.crear(cancion: const CancionFav(titulo: 'sin id'), mensaje: 'x', ahora: hoy, premium: true)).problema,
          ProblemaCapsula.sinCancion);
    });

    test('la fecha va de mañana a 10 años; hoy y el pasado no valen', () async {
      Future<ProblemaCapsula?> con(DateTime f) async =>
          (await CapsulasTiempo.i.crear(cancion: _c1, mensaje: '', abre: f, ahora: hoy, premium: true)).problema;
      expect(await con(DateTime(2026, 11, 19, 23)), ProblemaCapsula.fechaPasada);
      expect(await con(DateTime(2025, 1, 1)), ProblemaCapsula.fechaPasada);
      expect(await con(DateTime(2036, 11, 20)), ProblemaCapsula.fechaLejana);
      expect(await con(DateTime(2026, 11, 20)), isNull);
      expect(await con(DateTime(2036, 11, 19)), isNull);
    });

    test('hay un máximo de cápsulas guardadas, y las ya vistas no cuentan', () async {
      for (var i = 0; i < CapsulasTiempo.maximo; i++) {
        expect((await CapsulasTiempo.i.crear(cancion: _c1, mensaje: '$i', ahora: hoy, premium: true)).ok, isTrue);
      }
      final r = await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'una más', ahora: hoy, premium: true);
      expect(r.problema, ProblemaCapsula.llena);
      expect(r.mensaje, contains('${CapsulasTiempo.maximo}'));
      await CapsulasTiempo.i.marcarVista(CapsulasTiempo.i.guardadas.first.id, hoy);
      expect((await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'ya cabe', ahora: hoy, premium: true)).ok, isTrue);
    });

    test('un mensaje larguísimo se recorta', () async {
      final r = await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'x' * 2000, ahora: hoy, premium: true);
      expect(r.capsula!.mensaje.length, CapsulaTiempo.maxMensaje);
    });

    test('los id no se repiten aunque se creen en el mismo instante', () async {
      final a = await CapsulasTiempo.i.crear(cancion: _c1, mensaje: '', ahora: hoy, premium: true);
      final b = await CapsulasTiempo.i.crear(cancion: _c1, mensaje: '', ahora: hoy, premium: true);
      expect(a.capsula!.id == b.capsula!.id, isFalse);
    });
  });

  group('En el teléfono, por cuenta', () {
    test('sobrevive a cerrar la app', () async {
      await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'para mí', abre: DateTime(2027, 3, 5), ahora: hoy, premium: true);
      await CapsulasTiempo.i.iniciar('yo'); // «volver a abrir»
      final c = CapsulasTiempo.i.todas.single;
      expect((c.mensaje, c.abre, c.cancion.videoId, c.vista), ('para mí', DateTime(2027, 3, 5), 'abc12345678', null));
    });

    test('cada cuenta ve solo las suyas', () async {
      await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'de yo', ahora: hoy, premium: true);
      await CapsulasTiempo.i.iniciar('otra');
      expect(CapsulasTiempo.i.todas, isEmpty);
      await CapsulasTiempo.i.crear(cancion: _c2, mensaje: 'de otra', ahora: hoy, premium: true);
      await CapsulasTiempo.i.iniciar('yo');
      expect(CapsulasTiempo.i.todas.single.mensaje, 'de yo');
    });

    test('cerrar sesión no deja nada a la vista', () async {
      await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'x', ahora: hoy, premium: true);
      CapsulasTiempo.i.reiniciar();
      expect(CapsulasTiempo.i.todas, isEmpty);
      expect(CapsulasTiempo.i.cuenta, '');
    });

    test('una entrada dañada se descarta sin llevarse las demás', () async {
      await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'buena', ahora: hoy, premium: true);
      final p = await SharedPreferences.getInstance();
      final buena = p.getString('capsulas_tiempo_yo')!;
      await p.setString('capsulas_tiempo_yo', buena.replaceFirst('[', '[{"id":"mala"},"basura",'));
      await CapsulasTiempo.i.iniciar('yo');
      expect(CapsulasTiempo.i.todas.single.mensaje, 'buena');
      await p.setString('capsulas_tiempo_yo', 'esto no es json');
      await CapsulasTiempo.i.iniciar('yo');
      expect(CapsulasTiempo.i.todas, isEmpty);
    });

    test('pendientes: solo las que llegaron a su día y no se han visto; vistas van al final', () async {
      await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'a', abre: DateTime(2026, 11, 22), ahora: hoy, premium: true);
      await CapsulasTiempo.i.crear(cancion: _c2, mensaje: 'b', abre: DateTime(2026, 11, 20), ahora: hoy, premium: true);
      await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'c', abre: DateTime(2027, 5, 1), ahora: hoy, premium: true);
      expect(CapsulasTiempo.i.pendientes(hoy), isEmpty);
      final despues = DateTime(2026, 11, 25);
      expect(CapsulasTiempo.i.pendientes(despues).map((c) => c.mensaje), ['b', 'a']); // la más antigua primero
      await CapsulasTiempo.i.marcarVista(CapsulasTiempo.i.pendientes(despues).first.id, despues);
      expect(CapsulasTiempo.i.pendientes(despues).map((c) => c.mensaje), ['a']);
      expect(CapsulasTiempo.i.vistas.map((c) => c.mensaje), ['b']);
      expect(CapsulasTiempo.i.todas.last.mensaje, 'b');
      // y se acuerda de que ya se vio
      await CapsulasTiempo.i.iniciar('yo');
      expect(CapsulasTiempo.i.vistas.single.vista, isNotNull);
    });

    test('marcar vista dos veces o borrar algo que no existe no hace nada', () async {
      final r = await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'x', ahora: hoy, premium: true);
      await CapsulasTiempo.i.marcarVista(r.capsula!.id, hoy);
      final vista = CapsulasTiempo.i.vistas.single.vista;
      await CapsulasTiempo.i.marcarVista(r.capsula!.id, DateTime(2030));
      expect(CapsulasTiempo.i.vistas.single.vista, vista);
      await CapsulasTiempo.i.borrar('no-existe');
      expect(CapsulasTiempo.i.todas.length, 1);
      await CapsulasTiempo.i.borrar(r.capsula!.id);
      expect(CapsulasTiempo.i.todas, isEmpty);
      await CapsulasTiempo.i.iniciar('yo');
      expect(CapsulasTiempo.i.todas, isEmpty);
    });
  });

  group('La tarjeta al abrir la app', () {
    Future<CapsulaTiempo> guardar(String mensaje, DateTime creada, DateTime abre, {CancionFav c = _c1}) async {
      final r = await CapsulasTiempo.i.crear(cancion: c, mensaje: mensaje, abre: abre, ahora: creada, premium: true);
      return r.capsula!;
    }

    testWidgets('sale la tarjeta de lo que guardaste, una sola vez', (t) async {
      final ahora = DateTime(2027, 11, 19, 9);
      await guardar('Espero que estés bien, yo del futuro', DateTime(2026, 11, 19, 10), DateTime(2027, 11, 19));
      int? vistas;
      await _montar(
          t, Builder(builder: (ctx) => Scaffold(body: Center(child: TextButton(onPressed: () async => vistas = await mostrarCapsulasPendientes(ctx, ahora: ahora), child: const Text('abrir app'))))));
      await t.tap(find.text('abrir app'));
      await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600));
      expect(find.text('CÁPSULA DEL TIEMPO'), findsOneWidget);
      expect(find.text('Hace un año guardaste esto para ti'), findsOneWidget);
      expect(find.text('Espero que estés bien, yo del futuro'), findsOneWidget);
      expect(find.textContaining('Canción de hace un año'), findsOneWidget);
      expect(find.text('Guardada el 19 de noviembre de 2026'), findsOneWidget);
      await t.tap(find.text('Cerrar'));
      await t.pumpAndSettle();
      expect(vistas, 1);
      // ya no vuelve a salir sola
      expect(CapsulasTiempo.i.pendientes(ahora), isEmpty);
      expect(await mostrarCapsulasPendientes(t.element(find.byType(Scaffold)), ahora: ahora), 0);
    });

    testWidgets('sin cápsulas listas no pasa nada', (t) async {
      await guardar('futuro', DateTime(2026, 11, 19), DateTime(2027, 11, 19));
      int? vistas;
      await _montar(
          t, Builder(builder: (ctx) => Scaffold(body: Center(child: TextButton(onPressed: () async => vistas = await mostrarCapsulasPendientes(ctx, ahora: DateTime(2027, 1, 1)), child: const Text('abrir app'))))));
      await t.tap(find.text('abrir app'));
      await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600));
      expect(vistas, 0);
      expect(find.text('CÁPSULA DEL TIEMPO'), findsNothing);
    });

    testWidgets('varias a la vez: una tras otra, la más antigua primero', (t) async {
      final ahora = DateTime(2027, 12, 1);
      await guardar('segunda', DateTime(2026, 11, 29), DateTime(2027, 11, 30), c: _c2);
      await guardar('primera', DateTime(2026, 11, 19), DateTime(2027, 11, 19));
      int? vistas;
      await _montar(
          t, Builder(builder: (ctx) => Scaffold(body: Center(child: TextButton(onPressed: () async => vistas = await mostrarCapsulasPendientes(ctx, ahora: ahora), child: const Text('abrir app'))))));
      await t.tap(find.text('abrir app'));
      await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600));
      expect(find.text('primera'), findsOneWidget);
      await t.tap(find.text('Cerrar'));
      await t.pumpAndSettle();
      expect(find.text('segunda'), findsOneWidget);
      await t.tap(find.text('Cerrar'));
      await t.pumpAndSettle();
      expect(vistas, 2);
    });

    testWidgets('«Escuchar la canción» suena y cierra', (t) async {
      final ahora = DateTime(2027, 11, 19);
      await guardar('hola', DateTime(2026, 11, 19), DateTime(2027, 11, 19));
      await _montar(
          t, Builder(builder: (ctx) => Scaffold(body: Center(child: TextButton(onPressed: () => mostrarCapsulasPendientes(ctx, ahora: ahora), child: const Text('abrir app'))))));
      await t.tap(find.text('abrir app'));
      await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600));
      await t.tap(find.text('Escuchar la canción'));
      await t.pumpAndSettle();
      expect(_r.reproducidas.single['video_id'], 'abc12345678');
      expect(find.text('CÁPSULA DEL TIEMPO'), findsNothing);
    });

    testWidgets('un donador puede guardarla otro año; sin beneficios no se ofrece', (t) async {
      final ahora = DateTime(2027, 11, 19);
      await guardar('hola', DateTime(2026, 11, 19), DateTime(2027, 11, 19));
      await _montar(
          t, Builder(builder: (ctx) => Scaffold(body: Center(child: TextButton(onPressed: () => mostrarCapsulasPendientes(ctx, ahora: ahora), child: const Text('abrir app'))))));
      await t.tap(find.text('abrir app'));
      await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600));
      expect(find.text('Guardarla otro año'), findsNothing);
      await t.tap(find.text('Cerrar'));
      await t.pumpAndSettle();

      _donador();
      await CapsulasTiempo.i.iniciar('yo');
      await guardar('otra vez', DateTime(2026, 11, 19), DateTime(2027, 11, 19));
      await t.tap(find.text('abrir app'));
      await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600));
      await t.tap(find.text('Guardarla otro año'));
      await t.pumpAndSettle();
      final nueva = CapsulasTiempo.i.guardadas.single;
      expect((nueva.mensaje, nueva.abre), ('otra vez', DateTime(2028, 11, 19)));
    });

    testWidgets('sigue abriéndose aunque ya no haya beneficios', (t) async {
      final ahora = DateTime(2027, 11, 19);
      await guardar('de cuando donaba', DateTime(2026, 11, 19), DateTime(2027, 11, 19));
      Premium.i.reiniciar();
      int? vistas;
      await _montar(
          t, Builder(builder: (ctx) => Scaffold(body: Center(child: TextButton(onPressed: () async => vistas = await mostrarCapsulasPendientes(ctx, ahora: ahora), child: const Text('abrir app'))))));
      await t.tap(find.text('abrir app'));
      await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600));
      expect(find.text('de cuando donaba'), findsOneWidget);
      await t.tap(find.text('Cerrar'));
      await t.pumpAndSettle();
      expect(vistas, 1);
    });

    for (final tam in const [Size(320, 568), Size(411, 800)]) {
      testWidgets('sin desbordes a ${tam.width.toInt()}x${tam.height.toInt()} con letra grande', (t) async {
        await guardar('Un mensaje largo ' * 25, DateTime(2026, 11, 19), DateTime(2027, 11, 19));
        await _montar(
            t,
            Builder(builder: (ctx) => Scaffold(body: Center(child: TextButton(onPressed: () => mostrarCapsulasPendientes(ctx, ahora: DateTime(2027, 11, 19)), child: const Text('abrir app'))))),
            tam: tam,
            letra: 1.6);
        await t.tap(find.text('abrir app'));
        await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600));
        expect(t.takeException(), isNull);
      });
    }
  });

  group('La lista y la hoja', () {
    testWidgets('vacía: explica y ofrece crear', (t) async {
      _donador();
      await _montar(t, const CapsulasPagina());
      expect(find.text('Todavía no guardaste ninguna cápsula.'), findsOneWidget);
      expect(find.text('Nueva cápsula'), findsOneWidget);
      expect(find.text('Crear cápsulas es exclusivo de donadores'), findsNothing);
    });

    testWidgets('sin beneficios: avisa que crear es exclusivo y no abre la hoja', (t) async {
      await _montar(t, const CapsulasPagina());
      expect(find.text('Crear cápsulas es exclusivo de donadores'), findsOneWidget);
      await t.tap(find.text('Nueva cápsula'));
      await t.pump(const Duration(milliseconds: 400));
      expect(find.text('Nueva cápsula del tiempo'), findsNothing);
      expect(find.textContaining('Es exclusivo de donadores'), findsOneWidget);
    });

    testWidgets('crear una: por defecto en un año, y aparece en la lista sin contar qué guarda', (t) async {
      _donador();
      final ahora = DateTime(2026, 11, 19);
      final s = await _montar(t, CapsulasPagina(ahora: ahora, favoritas: () async => []));
      s.reproductor.actual = {'tipo': 'pista', 'clave': 'yt:abc12345678', 'video_id': 'abc12345678', 'titulo': 'Suena ahora', 'artista': 'Alguien', 'miniatura': ''};
      await t.tap(find.text('Nueva cápsula'));
      await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
      expect(find.text('Nueva cápsula del tiempo'), findsOneWidget);
      expect(find.text('Suena ahora'), findsOneWidget); // propone lo que suena
      expect(find.text('19 de noviembre de 2027'), findsOneWidget); // un año
      await t.enterText(find.byType(TextField), 'Hoy estoy aprendiendo Flutter');
      await t.pump();
      await t.tap(find.text('Guardar cápsula'));
      await t.pumpAndSettle();
      final c = CapsulasTiempo.i.guardadas.single;
      expect((c.mensaje, c.abre, c.cancion.titulo), ('Hoy estoy aprendiendo Flutter', DateTime(2027, 11, 19), 'Suena ahora'));
      expect(find.text('Guardadas · 1'), findsOneWidget);
      expect(find.text('Cápsula para ti'), findsOneWidget);
      expect(find.text('Suena ahora'), findsNothing); // no se adelanta lo guardado
      expect(find.text('Se abre el 19 de noviembre de 2027'), findsOneWidget);
    });

    testWidgets('los atajos de fecha cambian el día; el calendario también', (t) async {
      _donador();
      final ahora = DateTime(2026, 11, 19);
      final s = await _montar(t, CapsulasPagina(ahora: ahora));
      s.reproductor.actual = {'tipo': 'pista', 'clave': 'yt:abc12345678', 'video_id': 'abc12345678', 'titulo': 'X', 'artista': 'Y', 'miniatura': ''};
      await t.tap(find.text('Nueva cápsula'));
      await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
      await t.ensureVisible(find.text('6 meses'));
      await t.tap(find.text('6 meses'));
      await t.pump();
      expect(find.text('19 de mayo de 2027'), findsOneWidget);
      await t.tap(find.text('5 años'));
      await t.pump();
      expect(find.text('19 de noviembre de 2031'), findsOneWidget);
    });

    testWidgets('sin canción no se puede guardar; elegir una de los «me gusta» lo habilita', (t) async {
      _donador();
      await _montar(t, CapsulasPagina(ahora: DateTime(2026, 11, 19)));
      await t.tap(find.text('Nueva cápsula'));
      await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
      expect(t.widget<FilledButton>(find.widgetWithText(FilledButton, 'Guardar cápsula')).onPressed, isNull);
      await t.tap(find.text('Elegir la canción'));
      await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
      await t.tap(find.text('Mi favorita'));
      await t.pumpAndSettle();
      expect(find.text('Mi favorita'), findsOneWidget);
      expect(t.widget<FilledButton>(find.widgetWithText(FilledButton, 'Guardar cápsula')).onPressed, isNotNull);
    });

    testWidgets('las ya abiertas se pueden volver a ver y borrar con confirmación', (t) async {
      _donador();
      final r = await CapsulasTiempo.i.crear(cancion: _c2, mensaje: 'recuerdo', abre: DateTime(2026, 11, 20), ahora: DateTime(2026, 11, 19), premium: true);
      await CapsulasTiempo.i.marcarVista(r.capsula!.id, DateTime(2026, 11, 21));
      await _montar(t, CapsulasPagina(ahora: DateTime(2026, 11, 22)));
      expect(find.text('Ya abiertas · 1'), findsOneWidget);
      expect(find.text('Otra'), findsOneWidget);
      await t.tap(find.text('Otra'));
      await t.pump(const Duration(milliseconds: 600));
      await t.pump(const Duration(milliseconds: 600));
      expect(find.text('recuerdo'), findsOneWidget);
      await t.tap(find.text('Cerrar'));
      await t.pumpAndSettle();
      await t.tap(find.byTooltip('Borrar la cápsula'));
      await t.pumpAndSettle();
      expect(find.text('¿Borrar esta cápsula?'), findsOneWidget);
      await t.tap(find.text('Cancelar'));
      await t.pumpAndSettle();
      expect(CapsulasTiempo.i.todas.length, 1);
      await t.tap(find.byTooltip('Borrar la cápsula'));
      await t.pumpAndSettle();
      await t.tap(find.text('Borrar'));
      await t.pumpAndSettle();
      expect(CapsulasTiempo.i.todas, isEmpty);
    });

    for (final tam in const [Size(320, 568), Size(411, 800)]) {
      testWidgets('lista y hoja sin desbordes a ${tam.width.toInt()}x${tam.height.toInt()} con letra grande', (t) async {
        _donador();
        for (var i = 0; i < 3; i++) {
          await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'm$i', abre: DateTime(2027, 1 + i, 5), ahora: DateTime(2026, 11, 19), premium: true);
        }
        final r = await CapsulasTiempo.i.crear(cancion: _c1, mensaje: 'vista', abre: DateTime(2026, 11, 20), ahora: DateTime(2026, 11, 19), premium: true);
        await CapsulasTiempo.i.marcarVista(r.capsula!.id, DateTime(2026, 11, 21));
        final s = await _montar(t, CapsulasPagina(ahora: DateTime(2026, 11, 22)), tam: tam, letra: 1.3);
        s.reproductor.actual = {'tipo': 'pista', 'clave': 'yt:abc12345678', 'video_id': 'abc12345678', 'titulo': 'Suena ahora', 'artista': 'Alguien', 'miniatura': ''};
        expect(t.takeException(), isNull);
        await t.dragUntilVisible(find.text('Nueva cápsula'), find.byType(ListView), const Offset(0, -80));
        await t.pump();
        await t.tap(find.text('Nueva cápsula'));
        await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
        await t.enterText(find.byType(TextField), 'Un texto largo ' * 10);
        await t.pump(const Duration(milliseconds: 300));
        expect(t.takeException(), isNull);
      });
    }
  });
}
