// La cuarta actualizacion grande (2.5.0): cuando toca ensenarla, que cada diapositiva
// se vea bien en pantallas distintas, que se pueda recorrer (tactil, botones,
// teclado), que se cierre con «Saltar» y «Empezar», y que la release marcada
// [grande] use el aviso previo.
import 'package:caudal/nucleo/plataforma.dart';
import 'package:caudal/nucleo/version.dart';
import 'package:caudal/ui/novedades/diapositivas.dart';
import 'package:caudal/ui/novedades_grandes.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _montar(WidgetTester t, Size tamano, Widget aviso,
    {double texto = 1, bool sinAnimar = false}) async {
  t.view.physicalSize = tamano * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(
    theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory),
    builder: (ctx, hijo) => MediaQuery(
      data: MediaQuery.of(ctx).copyWith(textScaler: TextScaler.linear(texto), disableAnimations: sinAnimar),
      child: hijo!,
    ),
    home: aviso,
  ));
}

Future<void> _avanza(WidgetTester t, [int segundos = 1]) async {
  await t.pump();
  await t.pump(Duration(seconds: segundos));
}

void main() {
  group('cuando toca ensenarlo', () {
    test('la edicion es la 2.5.0', () => expect(edicionNovedades, '2.5.0'));

    test('quien ya vio la anterior (2.4.0) ve esta al pasar a la 2.5.0 o a un parche', () {
      expect(tocaNovedades('2.4.0', '2.5.0'), isTrue);
      expect(tocaNovedades('2.4.0', '2.5.1'), isTrue);
      expect(tocaNovedades('2.4.4', '2.5.0'), isTrue);
    });

    test('la primera vez que se abre la edicion (o un parche suyo)', () {
      expect(tocaNovedades(null, '2.5.0'), isTrue);
      expect(tocaNovedades('', '2.5.0'), isTrue);
      expect(tocaNovedades('2.1.3', '2.5.1'), isTrue);
      expect(tocaNovedades('1.9.0', '2.6.0'), isTrue);
    });

    test('una sola vez: si ya se vio no vuelve, ni con un parche', () {
      expect(tocaNovedades('2.5.0', '2.5.0'), isFalse);
      expect(tocaNovedades('2.5.0', '2.5.1'), isFalse);
      expect(tocaNovedades('2.5.1', '2.5.4'), isFalse);
    });

    test('antes de la edicion no sale (la 2.4.x ya no ensena la anterior)', () {
      expect(tocaNovedades(null, '2.4.4'), isFalse);
      expect(tocaNovedades('2.4.0', '2.4.4'), isFalse);
      expect(tocaNovedades('2.0.0', '2.3.9'), isFalse);
    });

    test('la version de la app es la de la edicion', () {
      expect(versionApp, '2.5.0');
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

  group('la presentacion', () {
    const tamanos = [Size(320, 568), Size(412, 915), Size(915, 412), Size(800, 1280), Size(1440, 900)];

    test('tiene siete diapositivas y la portada lleva el titulo de la edicion', () {
      expect(diapositivas.length, 7);
      expect(diapositivas.first.titulo, 'ACTUALIZACIÓN GRANDE DE CAUDAL');
      expect(diapositivas.last.titulo, 'Gracias por escuchar con Caudal');
    });

    test('no anuncia el algoritmo de recomendaciones por animo', () {
      final todo = diapositivas.map((d) => '${d.titulo} ${d.texto}').join(' ').toLowerCase();
      expect(todo.contains('triste'), isFalse);
      expect(todo.contains('estado de'), isFalse);
      expect(todo.contains('animo'), isFalse);
      expect(todo.contains('ánimo'), isFalse);
      expect(todo.contains('mood'), isFalse);
      expect(todo.contains('emocion'), isFalse);
    });

    for (final tam in tamanos) {
      for (var i = 0; i < 7; i++) {
        testWidgets('diapositiva ${i + 1} sin desbordes en ${tam.width.toInt()}x${tam.height.toInt()}', (t) async {
          await _montar(t, tam, NovedadesGrandes(paginaInicial: i));
          // las ilustraciones no paran: el reloj se avanza a mano, varios segundos
          await t.pump();
          for (var k = 0; k < 6; k++) {
            await t.pump(const Duration(seconds: 1));
          }
          expect(find.text(diapositivas[i].titulo), findsOneWidget);
          expect(find.text('Saltar'), findsOneWidget);
          expect(find.text('Empezar'), i == diapositivas.length - 1 ? findsOneWidget : findsNothing);
          expect(t.takeException(), isNull);
        });
      }
    }

    testWidgets('con la letra al 130 % no se desborda ninguna diapositiva en 320x568', (t) async {
      for (var i = 0; i < 7; i++) {
        await _montar(t, const Size(320, 568), NovedadesGrandes(paginaInicial: i), texto: 1.3);
        await _avanza(t, 3);
        expect(find.text('Saltar'), findsOneWidget);
        expect(t.takeException(), isNull, reason: 'diapositiva ${i + 1}');
      }
    });

    testWidgets('quien pide menos movimiento la ve compuesta y el salto es inmediato', (t) async {
      await _montar(t, const Size(360, 640), const NovedadesGrandes(), sinAnimar: true);
      await t.pump();
      expect(find.text('ACTUALIZACIÓN GRANDE DE CAUDAL'), findsOneWidget);
      await t.tap(find.byTooltip('Siguiente'));
      await t.pump();
      expect(find.text(diapositivas[1].titulo), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('los botones Siguiente y Anterior pasan de diapositiva', (t) async {
      await _montar(t, const Size(360, 640), const NovedadesGrandes());
      await _avanza(t);
      expect(find.byTooltip('Anterior'), findsNothing);
      await t.tap(find.byTooltip('Siguiente'));
      await _avanza(t);
      expect(find.text(diapositivas[1].titulo), findsOneWidget);
      expect(find.byTooltip('Anterior'), findsOneWidget);
      await t.tap(find.byTooltip('Anterior'));
      await _avanza(t);
      expect(find.text(diapositivas[0].titulo), findsOneWidget);
    });

    testWidgets('se pasa deslizando', (t) async {
      await _montar(t, const Size(360, 640), const NovedadesGrandes());
      await _avanza(t);
      await t.drag(find.byType(PageView), const Offset(-300, 0));
      await _avanza(t);
      expect(find.text(diapositivas[1].titulo), findsOneWidget);
    });

    testWidgets('el teclado: flechas, espacio, Fin e Inicio', (t) async {
      await _montar(t, const Size(1000, 700), const NovedadesGrandes());
      await _avanza(t);
      await t.sendKeyEvent(LogicalKeyboardKey.arrowRight);
      await _avanza(t);
      expect(find.text(diapositivas[1].titulo), findsOneWidget);
      await t.sendKeyEvent(LogicalKeyboardKey.space);
      await _avanza(t);
      expect(find.text(diapositivas[2].titulo), findsOneWidget);
      await t.sendKeyEvent(LogicalKeyboardKey.arrowLeft);
      await _avanza(t);
      expect(find.text(diapositivas[1].titulo), findsOneWidget);
      await t.sendKeyEvent(LogicalKeyboardKey.end);
      await _avanza(t);
      expect(find.text('Empezar'), findsOneWidget);
      await t.sendKeyEvent(LogicalKeyboardKey.home);
      await _avanza(t);
      expect(find.text(diapositivas[0].titulo), findsOneWidget);
    });

    testWidgets('«Saltar» y Escape la cierran, cada uno avisando', (t) async {
      var cerrado = 0;
      await _montar(t, const Size(360, 640), NovedadesGrandes(alCerrar: () => cerrado++));
      await _avanza(t);
      await t.tap(find.text('Saltar'));
      await t.pump();
      expect(cerrado, 1);
      await t.sendKeyEvent(LogicalKeyboardKey.escape);
      await t.pump();
      expect(cerrado, 2);
    });

    testWidgets('«Saltar» sigue a la vista en la ultima diapositiva', (t) async {
      await _montar(t, const Size(360, 640), NovedadesGrandes(paginaInicial: diapositivas.length - 1));
      await _avanza(t);
      expect(find.text('Saltar'), findsOneWidget);
    });

    testWidgets('«Empezar» y Enter al final avisan a quien la monto', (t) async {
      var empezado = 0, cerrado = 0;
      await _montar(t, const Size(360, 640),
          NovedadesGrandes(paginaInicial: diapositivas.length - 1, alEmpezar: () => empezado++, alCerrar: () => cerrado++));
      await _avanza(t);
      await t.tap(find.text('Empezar'));
      await t.pump();
      expect(empezado, 1);
      await t.sendKeyEvent(LogicalKeyboardKey.enter);
      await t.pump();
      expect(empezado, 2);
      expect(cerrado, 0);
    });

    testWidgets('abierta como ruta, «Saltar» la cierra y no deja nada', (t) async {
      late BuildContext raiz;
      await t.pumpWidget(MaterialApp(
        theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory),
        home: Builder(builder: (ctx) {
          raiz = ctx;
          return const Scaffold(body: Text('la app'));
        }),
      ));
      NovedadesGrandes.mostrar(raiz);
      await _avanza(t);
      expect(find.text('ACTUALIZACIÓN GRANDE DE CAUDAL'), findsOneWidget);
      await t.tap(find.text('Saltar'));
      await t.pump();
      await t.pump(const Duration(seconds: 1));
      expect(find.text('ACTUALIZACIÓN GRANDE DE CAUDAL'), findsNothing);
      expect(find.text('la app'), findsOneWidget);
    });

    testWidgets('en vertical la ilustracion va sobre el texto; en horizontal, al lado', (t) async {
      await _montar(t, const Size(360, 640), const NovedadesGrandes(paginaInicial: 1));
      await _avanza(t);
      expect(t.getRect(find.text(diapositivas[1].titulo)).top, greaterThan(300));
      await _montar(t, const Size(1000, 600), const NovedadesGrandes(paginaInicial: 1));
      await _avanza(t);
      expect(t.getRect(find.text(diapositivas[1].titulo)).left, greaterThan(400));
    });

    testWidgets('se puede leer con lector de pantalla: titulo y botones', (t) async {
      final semantica = t.ensureSemantics();
      await _montar(t, const Size(360, 640), const NovedadesGrandes());
      await _avanza(t);
      expect(t.getSemantics(find.text('ACTUALIZACIÓN GRANDE DE CAUDAL')).flagsCollection.isHeader, isTrue);
      expect(find.bySemanticsLabel(RegExp('Diapositiva 1 de 7')), findsWidgets);
      expect(t.getSemantics(find.byTooltip('Siguiente')).flagsCollection.isButton, isTrue);
      expect(find.bySemanticsLabel('Saltar'), findsWidgets);
      semantica.dispose();
    });
  });

  group('el aviso previo a actualizar ([grande])', () {
    const grande = Novedad(
      version: '2.5.0', notas: '[grande]\nTambién arreglamos los colores del reproductor.',
      apk: 'https://ejemplo/Caudal.apk', pagina: 'https://ejemplo/release', peso: 1000);

    setUp(() => Plataforma.forzada = TargetPlatform.android);
    tearDown(() => Plataforma.forzada = null);

    testWidgets('en iPhone no se instala desde dentro: ofrece ver cómo actualizar', (t) async {
      Plataforma.forzada = TargetPlatform.iOS;
      await _montar(t, const Size(360, 640), const NovedadesGrandes(actualizacion: grande));
      await _avanza(t, 3);
      expect(find.text('Ver cómo actualizar'), findsOneWidget);
      expect(find.text('Actualizar ahora'), findsNothing);
    });

    testWidgets('usa «Actualizar ahora», las tarjetas de novedades y las notas al final', (t) async {
      await _montar(t, const Size(360, 640), const NovedadesGrandes(actualizacion: grande));
      await _avanza(t, 3);
      expect(find.text('La nueva actualización grande de Caudal'), findsOneWidget);
      expect(find.text('Actualizar ahora'), findsOneWidget);
      expect(find.text('Empezar'), findsNothing);
      expect(find.text('Más tarde'), findsOneWidget);
      expect(find.text('Caudal 2.5.0 ya está lista'), findsOneWidget);
      for (final it in novedadesDeEstaEdicion) {
        expect(find.text(it.titular, skipOffstage: false), findsOneWidget, reason: it.titular);
      }
      expect(novedadesDeEstaEdicion.length, 5);
      expect(find.text('Y además', skipOffstage: false), findsOneWidget);
      expect(find.text('También arreglamos los colores del reproductor.', skipOffstage: false), findsOneWidget);
      expect(find.textContaining('[grande]', skipOffstage: false), findsNothing);
      expect(t.takeException(), isNull);
    });

    for (final tam in const [Size(320, 568), Size(915, 412), Size(1440, 900)]) {
      testWidgets('sin desbordes en ${tam.width.toInt()}x${tam.height.toInt()}', (t) async {
        await _montar(t, tam, const NovedadesGrandes(actualizacion: grande));
        await _avanza(t, 3);
        expect(find.text('Actualizar ahora'), findsOneWidget);
        expect(t.takeException(), isNull);
      });
    }

    testWidgets('«Más tarde» cierra', (t) async {
      var cerrado = 0;
      await _montar(t, const Size(360, 640), NovedadesGrandes(actualizacion: grande, alCerrar: () => cerrado++));
      await _avanza(t, 3);
      await t.tap(find.text('Más tarde'));
      await t.pump();
      expect(cerrado, 1);
    });
  });
}
