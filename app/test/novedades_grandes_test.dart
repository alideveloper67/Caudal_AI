// El aviso de novedades grande: cuando toca, que se vea bien en pantallas
// distintas, que se pueda cerrar y que la release marcada [grande] lo use.
import 'package:caudal/nucleo/plataforma.dart';
import 'package:caudal/nucleo/version.dart';
import 'package:caudal/ui/novedades_grandes.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _montar(WidgetTester t, Size tamano, Widget aviso,
    {double texto = 1, bool sinAnimar = false}) async {
  t.view.physicalSize = tamano * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(
    theme: temaCaudal().copyWith(splashFactory: NoSplash.splashFactory),
    builder: (ctx, hijo) => MediaQuery(
      data: MediaQuery.of(ctx).copyWith(textScaler: TextScaler.linear(texto), disableAnimations: sinAnimar),
      child: hijo!,
    ),
    home: aviso,
  ));
}

void main() {
  group('cuando toca enseñarlo', () {
    test('la primera vez que se abre la edicion (o un parche suyo)', () {
      expect(tocaNovedades(null, '2.2.0'), isTrue);
      expect(tocaNovedades('', '2.2.0'), isTrue);
      expect(tocaNovedades('2.1.3', '2.2.0'), isTrue);
      expect(tocaNovedades('2.1.3', '2.2.1'), isTrue);
      expect(tocaNovedades('1.9.0', '2.3.0'), isTrue);
    });

    test('una sola vez: si ya se vio no vuelve, ni con un parche', () {
      expect(tocaNovedades('2.2.0', '2.2.0'), isFalse);
      expect(tocaNovedades('2.2.0', '2.2.1'), isFalse);
      expect(tocaNovedades('2.2.1', '2.2.4'), isFalse);
      expect(tocaNovedades('2.3.0', '2.3.0'), isFalse);
    });

    test('antes de la edicion no sale', () {
      expect(tocaNovedades(null, '2.1.3'), isFalse);
      expect(tocaNovedades('2.0.0', '2.1.9'), isFalse);
    });
  });

  group('release marcada [grande]', () {
    test('se reconoce la marca al principio de las notas', () {
      expect(notasGrandes('[grande]\nPerfiles y amigos'), isTrue);
      expect(notasGrandes('  [Grande] \nHola'), isTrue);
      expect(notasGrandes('Hola\n[grande]'), isFalse);
      expect(notasGrandes(''), isFalse);
      expect(quitarMarcaGrande('[grande]\nPerfiles y amigos'), 'Perfiles y amigos');
      expect(quitarMarcaGrande('[grande]'), '');
      expect(quitarMarcaGrande('Sin marca'), 'Sin marca');
    });

    test('novedadDe la propaga a la novedad', () {
      final n = novedadDe([
        {
          'tag_name': 'movil-v9.0.0',
          'body': '[grande]\nCambios enormes',
          'assets': [{'name': 'Caudal-arm64-v8a.apk', 'browser_download_url': 'u', 'size': 5}],
        },
      ], ios: false, abi: 'arm64')!;
      expect(n.esGrande, isTrue);
      expect(n.notasVisibles, 'Cambios enormes');

      final normal = novedadDe([
        {
          'tag_name': 'movil-v9.0.0',
          'body': 'Arreglos pequeños',
          'assets': [{'name': 'Caudal-arm64-v8a.apk', 'browser_download_url': 'u', 'size': 5}],
        },
      ], ios: false, abi: 'arm64')!;
      expect(normal.esGrande, isFalse);
      expect(normal.notasVisibles, 'Arreglos pequeños');
    });
  });

  group('la pantalla', () {
    const tamanos = [Size(320, 568), Size(360, 640), Size(411, 891), Size(768, 1024), Size(1280, 800)];

    for (final tam in tamanos) {
      testWidgets('se ve entera y sin desbordes en ${tam.width.toInt()}x${tam.height.toInt()}', (t) async {
        await _montar(t, tam, const NovedadesGrandes());
        // la entrada dura 2,4 s: se avanza el reloj a mano (hay luces que no paran)
        await t.pump();
        await t.pump(const Duration(milliseconds: 600));
        await t.pump(const Duration(seconds: 3));
        expect(find.text('La actualización más grande de Caudal'), findsOneWidget);
        expect(find.text('Perfiles, amigos, tu propia música y un DJ dentro de la app'), findsOneWidget);
        for (final it in novedadesDeEstaEdicion) {
          expect(find.text(it.titular, skipOffstage: false), findsOneWidget, reason: it.titular);
        }
        expect(find.text('Empezar'), findsOneWidget);
        expect(find.byTooltip('Cerrar'), findsOneWidget);
        expect(t.takeException(), isNull);
      });
    }

    testWidgets('con la letra al 130 % tampoco se desborda', (t) async {
      await _montar(t, const Size(320, 568), const NovedadesGrandes(), texto: 1.3);
      await t.pump();
      await t.pump(const Duration(seconds: 3));
      expect(find.text('Empezar'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('en una pantalla ancha las tarjetas van en dos columnas', (t) async {
      await _montar(t, const Size(1000, 800), const NovedadesGrandes());
      await t.pump();
      await t.pump(const Duration(seconds: 3));
      final a = t.getRect(find.text('Perfiles de verdad'));
      final b = t.getRect(find.text('Amigos con solicitud'));
      expect(b.left, greaterThan(a.right), reason: 'la segunda tarjeta va al lado');
      expect((a.top - b.top).abs(), lessThan(8));
    });

    testWidgets('en un telefono van en una sola columna, una bajo otra', (t) async {
      await _montar(t, const Size(360, 640), const NovedadesGrandes());
      await t.pump();
      await t.pump(const Duration(seconds: 3));
      final a = t.getRect(find.text('Perfiles de verdad'));
      final b = t.getRect(find.text('Amigos con solicitud'));
      expect(b.top, greaterThan(a.bottom));
    });

    testWidgets('las tarjetas entran una a una', (t) async {
      await _montar(t, const Size(360, 640), const NovedadesGrandes());
      await t.pump();
      await t.pump(const Duration(milliseconds: 500));
      double opacidadDe(String texto) {
        final o = find.ancestor(of: find.text(texto), matching: find.byType(Opacity)).first;
        return t.widget<Opacity>(o).opacity;
      }
      final primera = opacidadDe('Perfiles de verdad');
      final cuarta = opacidadDe('Sube tu música');
      expect(primera, greaterThan(cuarta), reason: 'la primera sale antes que la cuarta');
      await t.pump(const Duration(seconds: 3));
      expect(opacidadDe('Logo nuevo'), 1);
      expect(opacidadDe('Sube tu música'), 1);
    });

    testWidgets('quien pide menos movimiento lo ve todo ya puesto', (t) async {
      await _montar(t, const Size(360, 640), const NovedadesGrandes(), sinAnimar: true);
      await t.pump();
      final o = find.ancestor(of: find.text('Logo nuevo'), matching: find.byType(Opacity)).first;
      expect(t.widget<Opacity>(o).opacity, 1);
    });

    testWidgets('«Empezar» y la X cierran, cada uno avisando', (t) async {
      var empezado = 0, cerrado = 0;
      await _montar(t, const Size(360, 640),
          NovedadesGrandes(alEmpezar: () => empezado++, alCerrar: () => cerrado++));
      await t.pump();
      await t.pump(const Duration(seconds: 3));
      await t.tap(find.text('Empezar'));
      await t.pump();
      expect(empezado, 1);
      await t.tap(find.byTooltip('Cerrar'));
      await t.pump();
      expect(cerrado, 1);
    });

    testWidgets('abierto como ruta se cierra solo con la X y no deja nada', (t) async {
      late BuildContext raiz;
      await t.pumpWidget(MaterialApp(
        theme: temaCaudal().copyWith(splashFactory: NoSplash.splashFactory),
        home: Builder(builder: (ctx) {
          raiz = ctx;
          return const Scaffold(body: Text('la app'));
        }),
      ));
      NovedadesGrandes.mostrar(raiz);
      await t.pump();
      await t.pump(const Duration(seconds: 3));
      expect(find.text('La actualización más grande de Caudal'), findsOneWidget);
      await t.tap(find.byTooltip('Cerrar'));
      await t.pump();
      await t.pump(const Duration(seconds: 1));
      expect(find.text('La actualización más grande de Caudal'), findsNothing);
      expect(find.text('la app'), findsOneWidget);
    });

    testWidgets('se puede leer con lector de pantalla: titulo, tarjetas y botones', (t) async {
      final semantica = t.ensureSemantics();
      await _montar(t, const Size(360, 640), const NovedadesGrandes());
      await t.pump();
      await t.pump(const Duration(seconds: 3));
      expect(find.bySemanticsLabel(RegExp('Perfiles de verdad. Foto, descripción')), findsOneWidget);
      expect(find.bySemanticsLabel(RegExp('Mezclador. Un DJ automático')), findsOneWidget);
      expect(t.getSemantics(find.byTooltip('Cerrar')).getSemanticsData().tooltip, 'Cerrar');
      expect(t.getSemantics(find.byTooltip('Cerrar')).flagsCollection.isButton, isTrue);
      expect(find.bySemanticsLabel('Empezar'), findsWidgets);
      expect(t.getSemantics(find.text('La actualización más grande de Caudal')).flagsCollection.isHeader, isTrue);
      semantica.dispose();
    });
  });

  group('el aviso previo a actualizar ([grande])', () {
    const grande = Novedad(
      version: '2.2.0', notas: '[grande]\nTambién arreglamos los colores del reproductor.',
      apk: 'https://ejemplo/Caudal.apk', pagina: 'https://ejemplo/release', peso: 1000);

    setUp(() => Plataforma.forzada = TargetPlatform.android);
    tearDown(() => Plataforma.forzada = null);

    testWidgets('en iPhone no se instala desde dentro: ofrece ver cómo actualizar', (t) async {
      Plataforma.forzada = TargetPlatform.iOS;
      await _montar(t, const Size(360, 640), const NovedadesGrandes(actualizacion: grande));
      await t.pump();
      await t.pump(const Duration(seconds: 3));
      expect(find.text('Ver cómo actualizar'), findsOneWidget);
      expect(find.text('Actualizar ahora'), findsNothing);
    });

    testWidgets('usa el mismo diseño con «Actualizar ahora» y las notas al final', (t) async {
      await _montar(t, const Size(360, 640), const NovedadesGrandes(actualizacion: grande));
      await t.pump();
      await t.pump(const Duration(seconds: 3));
      expect(find.text('La actualización más grande de Caudal'), findsOneWidget);
      expect(find.text('Actualizar ahora'), findsOneWidget);
      expect(find.text('Empezar'), findsNothing);
      expect(find.text('Más tarde'), findsOneWidget);
      expect(find.text('Caudal 2.2.0 ya está lista'), findsOneWidget);
      expect(find.text('Y además', skipOffstage: false), findsOneWidget);
      expect(find.text('También arreglamos los colores del reproductor.', skipOffstage: false), findsOneWidget);
      expect(find.textContaining('[grande]', skipOffstage: false), findsNothing);
      expect(t.takeException(), isNull);
    });

    testWidgets('«Más tarde» cierra', (t) async {
      var cerrado = 0;
      await _montar(t, const Size(360, 640), NovedadesGrandes(actualizacion: grande, alCerrar: () => cerrado++));
      await t.pump();
      await t.pump(const Duration(seconds: 3));
      await t.tap(find.text('Más tarde'));
      await t.pump();
      expect(cerrado, 1);
    });
  });
}
