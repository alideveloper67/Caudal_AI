// La presentación de la 2.3.2 («Mascotitas y fondos con personaje"): cuándo
// sale y cuándo no, que se vea sin desbordes en pantallas distintas, que no
// enseñe mascotas exclusivas de una cuenta y que «Saltar» la cierre. También
// se monta el Armazon de verdad para ver que no se encima con las novedades
// grandes.
import 'dart:io';

import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/mascota_app.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/armazon.dart';
import 'package:caudal/ui/novedades/presentacion_mascotas.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _titulos = [
  'Mascotitas y fondos con personaje',
  'Un amiguito en tu barra',
  'Fondos con personaje',
  'Tu fondo y tu personaje van juntos',
  'Gracias por estar en Caudal',
];

final _catalogo = leerCatalogoMascotas(File('assets/mascotas/catalogo.json').readAsStringSync());

Future<void> _montar(WidgetTester t, Size tamano, Widget hijo, {double texto = 1, bool sinAnimar = false}) async {
  t.view.physicalSize = tamano * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(
    theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory),
    builder: (ctx, h) => MediaQuery(
      data: MediaQuery.of(ctx).copyWith(textScaler: TextScaler.linear(texto), disableAnimations: sinAnimar),
      child: h!,
    ),
    home: hijo,
  ));
}

Future<void> _avanza(WidgetTester t, [int segundos = 1]) async {
  await t.pump();
  for (var i = 0; i < segundos; i++) {
    await t.pump(const Duration(seconds: 1));
  }
}

/// Las claves de las mascotas que hay ahora mismo en los lienzos.
Set<String> _mascotasALaVista() {
  final claves = <String>{};
  for (final e in find.byWidgetPredicate((w) => w.key is ValueKey<String>).evaluate()) {
    final k = (e.widget.key! as ValueKey<String>).value;
    if (k.startsWith('mascota-')) claves.add(k.substring(8));
    if (k.startsWith('mascotas-')) claves.addAll(k.substring(9).split(','));
  }
  return claves..remove('');
}

void main() {
  group('cuándo sale', () {
    test('es la presentación de la 2.3.2', () => expect(versionPresentacionMascotas, '2.3.2'));

    test('sale al abrir la 2.3.2 o una posterior si aún no se vio', () {
      expect(tocaPresentacionMascotas(null, '2.3.2'), isTrue);
      expect(tocaPresentacionMascotas('', '2.3.2'), isTrue);
      expect(tocaPresentacionMascotas(null, '2.3.5'), isTrue);
      expect(tocaPresentacionMascotas(null, '2.4.0'), isTrue);
      expect(tocaPresentacionMascotas('  ', '3.0.0'), isTrue);
    });

    test('una sola vez: si ya se vio no vuelve, ni con versiones nuevas', () {
      expect(tocaPresentacionMascotas('2.3.2', '2.3.2'), isFalse);
      expect(tocaPresentacionMascotas('2.3.2', '2.3.3'), isFalse);
      expect(tocaPresentacionMascotas('2.3.4', '2.6.0'), isFalse);
    });

    test('antes de la 2.3.2 no sale', () {
      expect(tocaPresentacionMascotas(null, '2.3.1'), isFalse);
      expect(tocaPresentacionMascotas(null, '2.3.0'), isFalse);
      expect(tocaPresentacionMascotas(null, '2.2.9'), isFalse);
    });

    test('si en ese arranque salen las novedades grandes, espera', () {
      expect(tocaPresentacionMascotas(null, '2.3.2', salenNovedadesGrandes: true), isFalse);
      expect(tocaPresentacionMascotas(null, '2.3.2', salenNovedadesGrandes: false), isTrue);
    });
  });

  group('las mascotas que enseña', () {
    test('nunca las exclusivas de una cuenta, y todas las demás', () {
      final m = mascotasDeLaPresentacion(_catalogo);
      expect(_catalogo.any((x) => x.esExclusiva), isTrue, reason: 'el catálogo trae alguna exclusiva');
      expect(m.where((x) => x.esExclusiva), isEmpty);
      expect(m.map((x) => x.clave), isNot(contains('caniche')));
      expect(m.length, _catalogo.where((x) => !x.esExclusiva).length);
      expect(m.first.clave, 'pikachu');
    });

    test('las parejas de «Tu fondo y tu personaje van juntos» tienen fondo y mascotita', () {
      final claves = mascotasDeLaPresentacion(_catalogo).map((m) => m.clave).toSet();
      for (final k in ['kuromi', 'pikachu', 'cinnamoroll', 'nyan', 'totoro', 'hellokitty', 'kirby', 'capibara']) {
        expect(claves, contains(k), reason: k);
        expect(Aspecto.temas.containsKey(k), isTrue, reason: k);
      }
    });
  });

  group('la presentación', () {
    for (final tam in const [Size(320, 568), Size(412, 915), Size(1440, 900)]) {
      testWidgets('se recorre entera sin desbordes en ${tam.width.toInt()}x${tam.height.toInt()}', (t) async {
        await _montar(t, tam, PresentacionMascotas(catalogo: _catalogo, alCerrar: () {}));
        await _avanza(t, 2);
        final vistas = <String>{};
        for (var i = 0; i < _titulos.length; i++) {
          expect(find.text(_titulos[i]), findsOneWidget, reason: 'diapositiva ${i + 1}');
          expect(find.text('Saltar'), findsOneWidget);
          // varios segundos: rotan los temas y las mascotitas
          for (var k = 0; k < 6; k++) {
            await t.pump(const Duration(milliseconds: 1500));
            vistas.addAll(_mascotasALaVista());
            expect(t.takeException(), isNull, reason: 'diapositiva ${i + 1}');
          }
          if (i < _titulos.length - 1) {
            await t.tap(find.byTooltip('Siguiente'));
            await _avanza(t);
          }
        }
        expect(find.text('Empezar'), findsOneWidget);
        expect(find.text('Elegir mi fondo ahora'), findsOneWidget);
        expect(vistas, isNotEmpty);
        expect(vistas.where((c) => _catalogo.firstWhere((m) => m.clave == c).esExclusiva), isEmpty);
        expect(vistas, isNot(contains('caniche')));
        expect(t.takeException(), isNull);
      });
    }

    testWidgets('con la letra al 130 % no se desborda ninguna diapositiva en 320x568', (t) async {
      for (var i = 0; i < _titulos.length; i++) {
        await _montar(t, const Size(320, 568), PresentacionMascotas(catalogo: _catalogo, paginaInicial: i), texto: 1.3);
        await _avanza(t, 3);
        expect(find.text('Saltar'), findsOneWidget);
        expect(t.takeException(), isNull, reason: 'diapositiva ${i + 1}');
      }
    });

    testWidgets('en el desfile van pasando muchas mascotitas y ninguna exclusiva', (t) async {
      await _montar(t, const Size(412, 915), PresentacionMascotas(catalogo: _catalogo, paginaInicial: 1));
      final vistas = <String>{};
      await t.pump();
      for (var k = 0; k < 150; k++) {
        await t.pump(const Duration(seconds: 1));
        vistas.addAll(_mascotasALaVista());
      }
      expect(vistas.length, greaterThan(20));
      expect(vistas, isNot(contains('caniche')));
      expect(t.takeException(), isNull);
    });

    testWidgets('quien pide menos movimiento la ve quieta y el salto es inmediato', (t) async {
      await _montar(t, const Size(360, 640), PresentacionMascotas(catalogo: _catalogo), sinAnimar: true);
      await t.pump();
      await t.tap(find.byTooltip('Siguiente'));
      await t.pump();
      expect(find.text(_titulos[1]), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('se pasa deslizando', (t) async {
      await _montar(t, const Size(360, 640), PresentacionMascotas(catalogo: _catalogo));
      await _avanza(t);
      await t.drag(find.byType(PageView), const Offset(-300, 0));
      await _avanza(t);
      expect(find.text(_titulos[1]), findsOneWidget);
    });

    testWidgets('con el teclado: flechas, Fin y Escape', (t) async {
      var cerrado = 0;
      await _montar(t, const Size(1000, 700), PresentacionMascotas(catalogo: _catalogo, alCerrar: () => cerrado++));
      await _avanza(t);
      await t.sendKeyEvent(LogicalKeyboardKey.arrowRight);
      await _avanza(t);
      expect(find.text(_titulos[1]), findsOneWidget);
      await t.sendKeyEvent(LogicalKeyboardKey.end);
      await _avanza(t);
      expect(find.text('Empezar'), findsOneWidget);
      await t.sendKeyEvent(LogicalKeyboardKey.escape);
      await t.pump();
      expect(cerrado, 1);
    });

    testWidgets('«Saltar» la cierra (avisa a quien la montó)', (t) async {
      var cerrado = 0;
      await _montar(t, const Size(412, 915), PresentacionMascotas(catalogo: _catalogo, alCerrar: () => cerrado++));
      await _avanza(t);
      await t.tap(find.text('Saltar'));
      await t.pump();
      expect(cerrado, 1);
    });

    testWidgets('«Saltar» sigue a la vista en la última y «Empezar» y «Elegir mi fondo ahora» avisan', (t) async {
      var empezado = 0, aspecto = 0, cerrado = 0;
      await _montar(
          t,
          const Size(412, 915),
          PresentacionMascotas(
            catalogo: _catalogo,
            paginaInicial: 4,
            alEmpezar: () => empezado++,
            alIrAAspecto: () => aspecto++,
            alCerrar: () => cerrado++,
          ));
      await _avanza(t);
      expect(find.text('Saltar'), findsOneWidget);
      await t.tap(find.text('Empezar'));
      await t.pump();
      await t.tap(find.text('Elegir mi fondo ahora'));
      await t.pump();
      expect((empezado, aspecto, cerrado), (1, 1, 0));
    });

    testWidgets('abierta como ruta, «Saltar» la cierra y no deja nada', (t) async {
      late BuildContext raiz;
      await MascotaApp.i.cargarCatalogo(texto: File('assets/mascotas/catalogo.json').readAsStringSync());
      await t.pumpWidget(MaterialApp(
        theme: temaCaudal(),
        home: Builder(builder: (ctx) {
          raiz = ctx;
          return const Scaffold(body: Text('la app'));
        }),
      ));
      abrirPresentacionMascotas(raiz);
      await _avanza(t);
      expect(find.text(_titulos[0]), findsOneWidget);
      await t.tap(find.text('Saltar'));
      await t.pump();
      await t.pump(const Duration(seconds: 1));
      expect(find.text(_titulos[0]), findsNothing);
      expect(find.text('la app'), findsOneWidget);
    });
  });

  group('al abrir la app', () {
    // desde la 2.7.5 no sale al abrir (las únicas presentaciones son «Somos 100» y «Gracias, donador»)
    testWidgets('ya no sale al abrir, se anota como vista y la música sigue', (t) async {
      final s = await _montarApp(t, version: '2.3.2', prefs: {claveNovedadesVistas: '2.3.0'});
      await t.pump(const Duration(seconds: 3));
      expect(find.text(_titulos[0]), findsNothing);
      expect(find.text('ACTUALIZACIÓN GRANDE DE CAUDAL'), findsNothing);
      expect((await SharedPreferences.getInstance()).getString(clavePresentacionMascotasVista), '2.3.2');
      expect(find.text('Inicio 0'), findsOneWidget);
      expect(s.reproductor.estado, EstadoRepro.sonando);
    });

    testWidgets('si ya se vio no vuelve a salir', (t) async {
      await _montarApp(t,
          version: '2.3.4', prefs: {claveNovedadesVistas: '2.3.0', clavePresentacionMascotasVista: '2.3.2'});
      await t.pump(const Duration(seconds: 3));
      expect(find.text(_titulos[0]), findsNothing);
    });

    testWidgets('en la 2.3.1 no sale', (t) async {
      await _montarApp(t, version: '2.3.1', prefs: {claveNovedadesVistas: '2.3.0'});
      await t.pump(const Duration(seconds: 3));
      expect(find.text(_titulos[0]), findsNothing);
    });

    testWidgets('tampoco salen las novedades grandes, ni en el arranque siguiente', (t) async {
      await _montarApp(t, version: '2.6.2');
      await t.pump(const Duration(seconds: 3));
      expect(find.text('ACTUALIZACIÓN GRANDE DE CAUDAL'), findsNothing);
      expect(find.text(_titulos[0]), findsNothing);
      final p = await SharedPreferences.getInstance();
      expect(p.getString(claveNovedadesVistas), '2.6.2');

      await _montarApp(t, version: '2.6.2', prefs: {claveNovedadesVistas: p.getString(claveNovedadesVistas)!});
      await t.pump(const Duration(seconds: 3));
      expect(find.text('ACTUALIZACIÓN GRANDE DE CAUDAL'), findsNothing);
      expect(find.text(_titulos[0]), findsNothing);
    });
  });
}

// ------------------------------------------------- el Armazon de verdad, con servicios de mentira

class _ReproductorFalso extends ChangeNotifier implements Reproductor {
  _ReproductorFalso(this.actual);
  @override
  Json? actual;
  @override
  EstadoRepro estado = EstadoRepro.sonando;
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(const Duration(minutes: 3));
  @override
  Stream<String> get avisos => const Stream.empty();

  @override
  Future<void> dispose() async => super.dispose();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ColeccionFalsa extends ChangeNotifier implements Coleccion {
  @override
  bool meGusta(String? clave) => false;

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

Future<Servicios> _montarApp(WidgetTester t, {required String version, Map<String, Object> prefs = const {}}) async {
  SharedPreferences.setMockInitialValues(prefs);
  final ajustes = await Ajustes.cargar('prueba');
  final s = Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
    ajustes: ajustes,
    coleccion: _ColeccionFalsa(),
    reproductor: _ReproductorFalso({
      'tipo': 'pista', 'clave': 'yt:id1', 'video_id': 'id1', 'titulo': 'Canción 1', 'artista': 'Artista 1',
      'miniatura': '',
    }),
    streams: _StreamsFalsos(),
    descargas: _DescargasFalsas(),
    cerrarSesion: () async {},
  );
  t.view.physicalSize = const Size(360, 640) * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(
    key: UniqueKey(),
    s: s,
    child: MaterialApp(
      theme: temaCaudal().copyWith(splashFactory: NoSplash.splashFactory),
      home: Armazon(
        versionActual: version,
        paginas: [
          for (final n in ['Inicio', 'Buscar', 'Biblioteca', 'Descargar'])
            Scaffold(body: ListView(children: [for (var i = 0; i < 40; i++) ListTile(title: Text('$n $i'))])),
        ],
      ),
    ),
  ));
  await t.pump(const Duration(milliseconds: 400));
  return s;
}
