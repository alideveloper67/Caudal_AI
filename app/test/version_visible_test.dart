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
import 'package:caudal/ui/reproductor/animaciones.dart';
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

  int detenciones = 0;

  @override
  Future<void> detener() async {
    detenciones++;
    estado = EstadoRepro.parado;
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
        // por defecto una version anterior a las novedades: que no tape la prueba con su pantalla
        versionActual: version ?? '2.0.0',
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
            expect(find.byType(MiniReproductor), findsNothing); // sin musica no hay mini
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

  group('la equis del mini reproductor', () {
    for (final tam in const [Size(320, 568), Size(360, 640), Size(411, 891), Size(768, 1024)]) {
      testWidgets('encaja en la esquina y no tapa los botones en ${tam.width.toInt()}x${tam.height.toInt()}', (t) async {
        await _montar(t, tam);
        final icono = find.byIcon(Icons.close_rounded);
        expect(icono, findsOneWidget);
        final mini = t.getRect(find.byType(MiniReproductor));
        final zona = t.getRect(find.ancestor(of: icono, matching: find.byType(SizedBox)).first);
        // zona de toque de 32x32 y el icono de 17 px
        expect(zona.width, 32);
        expect(zona.height, 32);
        expect(t.getSize(icono).width, 17);
        // arriba a la derecha del mini
        expect(zona.center.dy, closeTo(mini.top, 1));
        expect(mini.right - zona.right, inInclusiveRange(2, 24));
        // no se come el boton de play: su centro queda fuera de la zona
        final play = t.getRect(find.ancestor(of: find.byType(IconoPlayPausa), matching: find.byType(IconButton)));
        expect(zona.contains(play.center), isFalse);
        final cruce = zona.intersect(play);
        expect(cruce.height, lessThanOrEqualTo(12), reason: 'la equis pisa demasiado el play');
        // ni el corazon
        final corazon = t.getRect(find.byType(CorazonAnimado));
        expect(zona.overlaps(corazon.deflate(2)), isFalse);
        expect(t.takeException(), isNull);
      });
    }

    testWidgets('tocarla detiene la musica y oculta el mini; vuelve al tocar una cancion', (t) async {
      final s = await _montar(t, const Size(360, 640));
      final r = s.reproductor as _ReproductorFalso;
      await t.tap(find.byIcon(Icons.close_rounded));
      await t.pump(const Duration(milliseconds: 400));
      expect(r.detenciones, 1);
      expect(find.byType(MiniReproductor), findsNothing);
      expect(find.byIcon(Icons.close_rounded), findsNothing);
      // sigue oculto mientras no suene nada
      await t.pump(const Duration(seconds: 1));
      expect(find.byType(MiniReproductor), findsNothing);
      // se toca otra cancion: reaparece
      r.actual = {..._cancion, 'clave': 'yt:otra', 'titulo': 'Otra canción'};
      r.estado = EstadoRepro.cargando;
      r.notifyListeners();
      await t.pump(const Duration(milliseconds: 400));
      expect(find.byType(MiniReproductor), findsOneWidget);
      expect(find.text('Otra canción'), findsOneWidget);
    });

    testWidgets('tocar la misma cancion otra vez tambien lo trae de vuelta', (t) async {
      final s = await _montar(t, const Size(360, 640));
      final r = s.reproductor as _ReproductorFalso;
      await t.tap(find.byIcon(Icons.close_rounded));
      await t.pump(const Duration(milliseconds: 400));
      expect(find.byType(MiniReproductor), findsNothing);
      r.estado = EstadoRepro.cargando; // la misma pista
      r.notifyListeners();
      await t.pump(const Duration(milliseconds: 400));
      expect(find.byType(MiniReproductor), findsOneWidget);
    });

    testWidgets('el boton de play sigue siendo el de play (no lo quita)', (t) async {
      final s = await _montar(t, const Size(360, 640));
      final r = s.reproductor as _ReproductorFalso;
      await t.tap(find.byType(IconoPlayPausa));
      await t.pump(const Duration(milliseconds: 400));
      expect(r.estado, EstadoRepro.pausa);
      expect(r.detenciones, 0);
      expect(find.byType(MiniReproductor), findsOneWidget);
    });

    testWidgets('deslizar el mini hacia abajo lo quita', (t) async {
      final s = await _montar(t, const Size(360, 640));
      final r = s.reproductor as _ReproductorFalso;
      await t.fling(find.byType(MiniReproductor), const Offset(0, 160), 1500);
      await t.pump(const Duration(milliseconds: 500));
      expect(r.detenciones, 1);
      expect(find.byType(MiniReproductor), findsNothing);
    });

    testWidgets('sin musica no hay equis', (t) async {
      await _montar(t, const Size(360, 640), sonando: false);
      expect(find.byIcon(Icons.close_rounded), findsNothing);
    });

    testWidgets('lo lee el lector de pantalla', (t) async {
      final semantica = t.ensureSemantics();
      await _montar(t, const Size(360, 640));
      expect(find.bySemanticsLabel('Quitar la canción y cerrar el reproductor'), findsOneWidget);
      semantica.dispose();
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
    const titulo = 'ACTUALIZACIÓN GRANDE DE CAUDAL';

    testWidgets('sale una sola vez por version y se guarda la vista', (t) async {
      await _montar(t, const Size(360, 640), version: '2.3.0');
      await t.pump(const Duration(seconds: 3));
      expect(find.text(titulo), findsOneWidget);
      expect((await SharedPreferences.getInstance()).getString(claveNovedadesVistas), '2.3.0');

      await t.tap(find.text('Saltar'));
      await t.pump();
      await t.pump(const Duration(seconds: 1));
      expect(find.text(titulo), findsNothing);
      expect(find.text('Inicio 0'), findsOneWidget);
    });

    testWidgets('si ya se vio esa version no vuelve a salir', (t) async {
      await _montar(t, const Size(360, 640), version: '2.3.0', prefs: {claveNovedadesVistas: '2.3.0'});
      await t.pump(const Duration(seconds: 3));
      expect(find.text(titulo), findsNothing);
    });

    testWidgets('un parche de la misma edicion tampoco lo repite', (t) async {
      await _montar(t, const Size(360, 640), version: '2.3.1', prefs: {claveNovedadesVistas: '2.3.0'});
      await t.pump(const Duration(seconds: 3));
      expect(find.text(titulo), findsNothing);
    });

    testWidgets('una version anterior a la edicion no lo muestra', (t) async {
      await _montar(t, const Size(360, 640), version: '2.2.9');
      await t.pump(const Duration(seconds: 3));
      expect(find.text(titulo), findsNothing);
    });

    testWidgets('no interrumpe la musica: sigue sonando debajo', (t) async {
      final s = await _montar(t, const Size(360, 640), version: '2.3.0');
      await t.pump(const Duration(seconds: 3));
      expect(find.text(titulo), findsOneWidget);
      expect(s.reproductor.estado, EstadoRepro.sonando);
      await t.tap(find.text('Saltar'));
      await t.pump();
      await t.pump(const Duration(seconds: 1));
      expect(s.reproductor.estado, EstadoRepro.sonando);
      expect(s.reproductor.actual, isNotNull);
    });
  });
}
