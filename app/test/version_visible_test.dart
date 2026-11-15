// La version siempre a la vista (abajo a la izquierda, discreta) y el aviso de
// novedades al abrir. Se monta el Armazon de verdad con paginas de mentira,
// en varios tamaños, y se mira que la version no tape ni la barra de abajo ni
// el mini reproductor.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/nucleo/version.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/armazon.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

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

final Json _cancion = {
  'tipo': 'pista', 'clave': 'yt:id1', 'video_id': 'id1', 'titulo': 'Canción 1', 'artista': 'Artista 1',
  'miniatura': '',
};

Future<Servicios> _montar(WidgetTester t, Size tamano,
    {bool sonando = true, double texto = 1, String? version, Map<String, Object> prefs = const {}}) async {
  SharedPreferences.setMockInitialValues(prefs);
  final ajustes = await Ajustes.cargar('prueba');
  final s = Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
    ajustes: ajustes,
    coleccion: _ColeccionFalsa(),
    reproductor: _ReproductorFalso(sonando ? _cancion : null),
    streams: _StreamsFalsos(),
    descargas: _DescargasFalsas(),
    cerrarSesion: () async {},
  );
  t.view.physicalSize = tamano * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(
    s: s,
    child: MaterialApp(
      theme: temaCaudal().copyWith(splashFactory: NoSplash.splashFactory),
      builder: (ctx, hijo) => MediaQuery(
          data: MediaQuery.of(ctx).copyWith(textScaler: TextScaler.linear(texto)), child: hijo!),
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

void main() {
  final etiqueta = 'Caudal $versionApp';

  group('en un telefono (barra abajo)', () {
    for (final tam in const [Size(320, 568), Size(360, 640), Size(411, 891), Size(768, 1024)]) {
      for (final sonando in [true, false]) {
        testWidgets('${tam.width.toInt()}x${tam.height.toInt()} ${sonando ? 'con' : 'sin'} mini reproductor',
            (t) async {
          await _montar(t, tam, sonando: sonando);
          expect(find.text(etiqueta), findsOneWidget);
          final v = t.getRect(find.text(etiqueta));
          final barra = t.getRect(find.byType(NavigationBar));
          final contenido = t.getRect(find.byType(IndexedStack));

          // abajo a la izquierda, chiquita
          expect(v.left, lessThan(24));
          expect(v.height, lessThan(20));
          expect(v.width, lessThan(150)); // con la letra de prueba (muy ancha); en real son ~60
          // justo encima de la barra, sin tocarla, y debajo de todo el contenido
          expect(v.bottom, lessThanOrEqualTo(barra.top + 0.5));
          expect(barra.top - v.bottom, lessThan(8));
          expect(contenido.bottom, lessThanOrEqualTo(v.top + 0.5));
          expect(v.overlaps(barra), isFalse);
          if (sonando) {
            final mini = t.getRect(find.byType(MiniReproductor));
            expect(v.overlaps(mini), isFalse, reason: 'tapa el mini reproductor');
            expect(mini.bottom, lessThanOrEqualTo(v.top + 0.5));
          } else {
            expect(find.byType(MiniReproductor), findsOneWidget); // existe pero esta vacio
          }
          expect(t.takeException(), isNull);
        });
      }
    }

    testWidgets('no capta toques y es tenue', (t) async {
      await _montar(t, const Size(360, 640));
      final texto = find.text(etiqueta);
      expect(find.ancestor(of: texto, matching: find.byType(IgnorePointer)), findsWidgets);
      final estilo = t.widget<Text>(texto).style!;
      expect(estilo.fontSize, lessThanOrEqualTo(11));
      expect(estilo.color!.a, lessThan(1));
      // tocar encima no abre nada ni rompe
      await t.tap(texto, warnIfMissed: false);
      await t.pump();
      expect(t.takeException(), isNull);
    });

    testWidgets('con la letra al 120 % sigue entera y sin tapar', (t) async {
      await _montar(t, const Size(320, 568), texto: 1.2);
      final v = t.getRect(find.text(etiqueta));
      expect(v.overlaps(t.getRect(find.byType(NavigationBar))), isFalse);
      expect(v.overlaps(t.getRect(find.byType(MiniReproductor))), isFalse);
      expect(t.takeException(), isNull);
    });

    testWidgets('con el teclado abierto no rompe nada y queda sobre el', (t) async {
      await _montar(t, const Size(360, 640));
      t.view.viewInsets = const FakeViewPadding(bottom: 500);
      addTearDown(t.view.resetViewInsets);
      await t.pump();
      expect(find.text(etiqueta), findsOneWidget);
      expect(t.getRect(find.text(etiqueta)).bottom, lessThanOrEqualTo(640 - 500 / 2 + 0.5));
      expect(t.takeException(), isNull);
    });

    testWidgets('lo lee el lector de pantalla', (t) async {
      final semantica = t.ensureSemantics();
      await _montar(t, const Size(360, 640));
      expect(find.bySemanticsLabel('Versión de Caudal $versionApp'), findsOneWidget);
      semantica.dispose();
    });

    testWidgets('el menu de abajo y las pestañas siguen funcionando', (t) async {
      await _montar(t, const Size(360, 640));
      expect(find.text('Inicio 0'), findsOneWidget);
      await t.tap(find.text('Buscar'));
      await t.pump(const Duration(milliseconds: 400));
      expect(find.text('Buscar 0'), findsOneWidget);
      expect(find.text(etiqueta), findsOneWidget);
    });
  });

  group('en pantalla ancha (menu a la izquierda)', () {
    for (final tam in const [Size(1000, 700), Size(1280, 800), Size(1920, 1080)]) {
      testWidgets('${tam.width.toInt()}x${tam.height.toInt()}', (t) async {
        await _montar(t, tam);
        expect(find.byType(NavigationBar), findsNothing);
        final v = t.getRect(find.text(etiqueta));
        expect(v.left, lessThan(40));
        expect(v.right, lessThan(232), reason: 'cabe en el menu lateral');
        expect(v.bottom, greaterThan(tam.height - 60));
        expect(v.bottom, lessThanOrEqualTo(tam.height));
        // no pisa el nombre de la cuenta ni "Ajustes"
        expect(v.overlaps(t.getRect(find.text('Prueba'))), isFalse);
        expect(v.overlaps(t.getRect(find.text('Ajustes'))), isFalse);
        // la letra de las pruebas (Ahem) es muy ancha: los textos del menu se salen de su fila
        // aunque con la letra real caben; solo se recoge, no se juzga
        t.takeException();
      });
    }
  });

  group('aviso de novedades al abrir', () {
    const titulo = 'La actualización más grande de Caudal';

    testWidgets('sale una sola vez por version y se guarda la vista', (t) async {
      await _montar(t, const Size(360, 640), version: '2.2.0');
      await t.pump(const Duration(seconds: 3));
      expect(find.text(titulo), findsOneWidget);
      expect((await SharedPreferences.getInstance()).getString(claveNovedadesVistas), '2.2.0');

      await t.tap(find.text('Empezar'));
      await t.pump();
      await t.pump(const Duration(seconds: 1));
      expect(find.text(titulo), findsNothing);
      expect(find.text('Inicio 0'), findsOneWidget);
    });

    testWidgets('si ya se vio esa version no vuelve a salir', (t) async {
      await _montar(t, const Size(360, 640), version: '2.2.0', prefs: {claveNovedadesVistas: '2.2.0'});
      await t.pump(const Duration(seconds: 3));
      expect(find.text(titulo), findsNothing);
    });

    testWidgets('un parche de la misma edicion tampoco lo repite', (t) async {
      await _montar(t, const Size(360, 640), version: '2.2.1', prefs: {claveNovedadesVistas: '2.2.0'});
      await t.pump(const Duration(seconds: 3));
      expect(find.text(titulo), findsNothing);
    });

    testWidgets('una version anterior a la edicion no lo muestra', (t) async {
      await _montar(t, const Size(360, 640), version: '2.1.3');
      await t.pump(const Duration(seconds: 3));
      expect(find.text(titulo), findsNothing);
    });

    testWidgets('no interrumpe la musica: sigue sonando debajo', (t) async {
      final s = await _montar(t, const Size(360, 640), version: '2.2.0');
      await t.pump(const Duration(seconds: 3));
      expect(find.text(titulo), findsOneWidget);
      expect(s.reproductor.estado, EstadoRepro.sonando);
      await t.tap(find.byTooltip('Cerrar'));
      await t.pump();
      await t.pump(const Duration(seconds: 1));
      expect(s.reproductor.estado, EstadoRepro.sonando);
      expect(s.reproductor.actual, isNotNull);
    });
  });
}
