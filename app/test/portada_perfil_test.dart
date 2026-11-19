// Portada del perfil (donadores): el modelo, el servicio (preguntar, guardar, recordar), la tarjeta del banner,
// el editor y cómo se ve en el perfil de uno mismo y de un amigo. Sin red: la nube es un doble.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/mascota_app.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/portada_perfil.dart';
import 'package:caudal/nucleo/premium.dart';
import 'package:caudal/nucleo/social.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/premium/mascota_sprite.dart';
import 'package:caudal/ui/premium/portada_perfil_ui.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _Sesion extends Sesion {
  _Sesion() : super('yo', 'token', 'r', DateTime.now().add(const Duration(hours: 1)));

  Object? portada;
  bool sinFuncion = false;
  bool sinRed = false;
  bool fallaPatch = false;
  final enviados = <(String, String, Object?)>[];

  Iterable<(String, String, Object?)> get patches => enviados.where((e) => e.$1 == 'PATCH');
  Iterable<(String, String, Object?)> get preguntas => enviados.where((e) => e.$2 == 'rpc/portada_perfil');

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    enviados.add((metodo, ruta, cuerpo));
    if (ruta == 'rpc/portada_perfil') {
      if (sinRed) throw const SinConexion();
      if (sinFuncion) throw const ErrorNube('function public.portada_perfil(p_usuario) does not exist');
      return portada;
    }
    if (metodo == 'PATCH') {
      if (fallaPatch) throw const ErrorNube('Sin conexión.');
      return null;
    }
    return null;
  }
}

class _Reproductor extends ChangeNotifier implements Reproductor {
  @override
  Json? actual;
  @override
  Future<void> dispose() async => super.dispose();
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Coleccion extends ChangeNotifier implements Coleccion {
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

Future<Servicios> _servicios(_Sesion sesion) async => Servicios(
      cuenta: Cuenta(id: 'yo', usuario: 'ana', nombre: 'Ana', sesion: sesion),
      ajustes: await Ajustes.cargar('prueba'),
      coleccion: _Coleccion(),
      reproductor: _Reproductor(),
      streams: _Streams(),
      descargas: _Descargas(),
      cerrarSesion: () async {},
    );

Future<void> _montar(WidgetTester t, Servicios s, Widget hijo,
    {Size tam = const Size(411, 1800), double letra = 1}) async {
  t.view.physicalSize = tam * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(
    s: s,
    child: MaterialApp(
      scaffoldMessengerKey: s.mensajero,
      theme: temaCaudal(),
      builder: (context, hijo) =>
          MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(letra)), child: hijo!),
      home: hijo,
    ),
  ));
  await t.pump(const Duration(milliseconds: 200));
}

const _catalogo = '''[
 {"clave":"nyan","nombre":"Nyan Cat","origen":"x","ancho":64,"alto":40,"arcoiris":true,"cuadros":4,"densidad":2},
 {"clave":"nailong","nombre":"Nailong","origen":"x","ancho":48,"alto":50,"arcoiris":false,"cuadros":4,"densidad":2}
]''';

const _cancion = CancionFav(videoId: 'abc12345678', titulo: 'Una canción con un título bastante largo para probar el recorte',
    artista: 'Una artista con un nombre largo también', miniatura: '');

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    Premium.i.reiniciar();
    PortadasPerfil.i.reiniciar();
    await MascotaApp.i.cargarCatalogo(texto: _catalogo);
    await MascotaApp.i.iniciar('yo');
  });

  group('PortadaPerfil (modelo)', () {
    test('la letra se limpia: espacios, líneas vacías, 4 líneas y 160 letras', () {
      expect(PortadaPerfil.limpiarLetra('  hola   mundo  \r\n\n\n  segunda '), 'hola mundo\nsegunda');
      expect(PortadaPerfil.limpiarLetra('a\nb\nc\nd\ne\nf').split('\n'), ['a', 'b', 'c', 'd']);
      expect(PortadaPerfil.limpiarLetra('x' * 500).length, PortadaPerfil.maxLetra);
      expect(PortadaPerfil.limpiarLetra('   '), '');
    });

    test('lee lo que manda el servidor y descarta lo raro', () {
      final p = PortadaPerfil.desde({
        'cancion': {'video_id': 'abc12345678', 'titulo': 'T', 'artista': 'A', 'miniatura': 'https://x/y.jpg'},
        'letra': ' Hola ',
        'mascota': 'Nyan',
      })!;
      expect((p.cancion!.titulo, p.letra, p.mascota), ('T', 'Hola', 'nyan'));
      expect(PortadaPerfil.desde(null), isNull);
      expect(PortadaPerfil.desde('basura'), isNull);
      expect(PortadaPerfil.desde({'cancion': null, 'letra': '', 'mascota': null}), isNull);
      // una mascota con caracteres raros no entra; una canción sin video_id tampoco
      final r = PortadaPerfil.desde({'cancion': {'titulo': 'sin id'}, 'letra': 'a', 'mascota': 'Mi Mascota!'})!;
      expect((r.cancion, r.mascota), (null, ''));
      expect(PortadaPerfil.desde([{'letra': 'en lista'}])!.letra, 'en lista');
    });

    test('a columnas: lo vacío se manda como null para borrar', () {
      expect(PortadaPerfil.vacio.aColumnas(), {'portada_cancion': null, 'portada_letra': null, 'portada_mascota': null});
      final c = const PortadaPerfil(cancion: _cancion, letra: 'x', mascota: 'nyan').aColumnas();
      expect((c['portada_cancion'] as Map)['video_id'], 'abc12345678');
      expect((c['portada_letra'], c['portada_mascota']), ('x', 'nyan'));
    });

    test('igualdad por contenido y copiar', () {
      const a = PortadaPerfil(cancion: _cancion, letra: 'x', mascota: 'nyan');
      expect(a, const PortadaPerfil(cancion: _cancion, letra: 'x', mascota: 'nyan'));
      expect(a == a.copiar(letra: 'y'), isFalse);
      expect(a.copiar(cancion: null).cancion, isNull);
      expect(a.copiar().cancion, isNotNull);
    });
  });

  group('PortadasPerfil (servicio)', () {
    test('ver: trae la portada y, si es la mía, la recuerda en el teléfono', () async {
      final ses = _Sesion()
        ..portada = {
          'cancion': {'video_id': 'abc12345678', 'titulo': 'T', 'artista': 'A', 'miniatura': ''},
          'letra': 'Mi letra',
          'mascota': 'nyan',
        };
      final r = await PortadasPerfil.i.ver(Social(ses), 'ana', esMia: true);
      expect(r!.letra, 'Mi letra');
      expect(ses.preguntas.single.$3, {'p_usuario': 'ana'});
      expect(PortadasPerfil.i.mia.mascota, 'nyan');
      // sin internet más tarde: se sigue viendo lo recordado
      PortadasPerfil.i.reiniciar();
      expect(PortadasPerfil.i.mia.vacia, isTrue);
      await PortadasPerfil.i.cargarLocal('yo');
      expect(PortadasPerfil.i.mia.letra, 'Mi letra');
    });

    test('ver la de otra persona no toca la mía', () async {
      final ses = _Sesion()..portada = {'letra': 'de otra'};
      final r = await PortadasPerfil.i.ver(Social(ses), 'beto');
      expect(r!.letra, 'de otra');
      expect(PortadasPerfil.i.mia.vacia, isTrue);
    });

    test('un servidor sin la función todavía: nada que ver y sin errores', () async {
      final ses = _Sesion()..sinFuncion = true;
      expect(await PortadasPerfil.i.ver(Social(ses), 'beto'), isNull);
    });

    test('sin internet el error sube, para que la pantalla decida', () async {
      final ses = _Sesion()..sinRed = true;
      await expectLater(PortadasPerfil.i.ver(Social(ses), 'beto'), throwsA(isA<SinConexion>()));
    });

    test('si el servidor ya no devuelve nada, lo mío se vacía', () async {
      final ses = _Sesion()..portada = {'letra': 'hola'};
      await PortadasPerfil.i.ver(Social(ses), 'ana', esMia: true);
      expect(PortadasPerfil.i.mia.letra, 'hola');
      ses.portada = null;
      await PortadasPerfil.i.ver(Social(ses), 'ana', esMia: true);
      expect(PortadasPerfil.i.mia.vacia, isTrue);
    });

    test('guardar manda el PATCH con las tres columnas y lo recuerda', () async {
      final ses = _Sesion();
      await PortadasPerfil.i.cargarLocal('yo');
      await PortadasPerfil.i.guardar(Social(ses), const PortadaPerfil(cancion: _cancion, letra: '  hola  ', mascota: 'nyan'));
      final p = ses.patches.single;
      expect(p.$2, 'perfiles?id=eq.yo');
      final c = p.$3 as Map;
      expect((c['portada_letra'], c['portada_mascota']), ('hola', 'nyan'));
      expect((c['portada_cancion'] as Map)['titulo'], _cancion.titulo);
      expect(PortadasPerfil.i.mia.letra, 'hola');
      PortadasPerfil.i.reiniciar();
      await PortadasPerfil.i.cargarLocal('yo');
      expect(PortadasPerfil.i.mia.mascota, 'nyan');
    });

    test('guardar con fallo: se deshace y el error sube', () async {
      final ses = _Sesion()..fallaPatch = true;
      await PortadasPerfil.i.cargarLocal('yo');
      await expectLater(PortadasPerfil.i.guardar(Social(ses), const PortadaPerfil(letra: 'x')), throwsA(isA<ErrorNube>()));
      expect(PortadasPerfil.i.mia.vacia, isTrue);
    });

    test('quitar la portada guarda todo en null y la borra del teléfono', () async {
      final ses = _Sesion();
      await PortadasPerfil.i.cargarLocal('yo');
      await PortadasPerfil.i.guardar(Social(ses), const PortadaPerfil(letra: 'x'));
      await PortadasPerfil.i.guardar(Social(ses), PortadaPerfil.vacio);
      expect(ses.patches.last.$3, {'portada_cancion': null, 'portada_letra': null, 'portada_mascota': null});
      PortadasPerfil.i.reiniciar();
      await PortadasPerfil.i.cargarLocal('yo');
      expect(PortadasPerfil.i.mia.vacia, isTrue);
    });

    test('«puede» sigue a los beneficios de donador', () {
      expect(PortadasPerfil.i.puede, isFalse);
      Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');
      expect(PortadasPerfil.i.puede, isTrue);
    });
  });

  group('La tarjeta del banner', () {
    const completa = PortadaPerfil(
        cancion: _cancion, letra: 'Una letra que ocupa varias líneas\ny sigue en otra más para probar\nlas cuatro líneas como mucho\ny esta es la cuarta', mascota: 'nyan');

    for (final tam in const [Size(320, 568), Size(411, 800), Size(1000, 700)]) {
      for (final letra in const [1.0, 1.8]) {
        testWidgets('completa: sin desbordes a ${tam.width.toInt()}x${tam.height.toInt()} con letra x$letra', (t) async {
          final ses = _Sesion();
          await _montar(
              t,
              await _servicios(ses),
              Scaffold(
                  body: SingleChildScrollView(
                      padding: const EdgeInsets.all(16),
                      child: PortadaTarjeta(portada: completa, color: Colors.teal, alReproducir: () {}, alEditar: () {}, propia: true))),
              tam: tam,
              letra: letra);
          await t.pump(const Duration(milliseconds: 600));
          expect(t.takeException(), isNull);
          expect(find.text('Tu canción del momento'), findsOneWidget);
          expect(find.textContaining('Una letra que ocupa'), findsOneWidget);
          expect(find.byType(MascotaSprite), findsOneWidget);
        });
      }
    }

    testWidgets('solo letra, solo mascota y solo canción también montan', (t) async {
      final ses = _Sesion();
      for (final p in const [
        PortadaPerfil(letra: 'solo letra'),
        PortadaPerfil(mascota: 'nailong'),
        PortadaPerfil(cancion: _cancion),
      ]) {
        await _montar(t, await _servicios(ses), Scaffold(body: SingleChildScrollView(child: PortadaTarjeta(portada: p, color: Colors.pink))),
            tam: const Size(320, 568));
        expect(t.takeException(), isNull, reason: '$p');
      }
    });

    testWidgets('una mascota desconocida no rompe nada', (t) async {
      await _montar(t, await _servicios(_Sesion()),
          const Scaffold(body: PortadaTarjeta(portada: PortadaPerfil(letra: 'hola', mascota: 'inventada'), color: Colors.blue)));
      expect(t.takeException(), isNull);
      expect(find.textContaining('hola'), findsOneWidget);
    });

    testWidgets('la mascota anima por cuadros y se detiene con «Quitar animaciones»', (t) async {
      final ses = _Sesion();
      Future<void> montar({required bool animar, bool reducido = false}) async {
        t.view.physicalSize = const Size(800, 1200);
        t.view.devicePixelRatio = 2;
        addTearDown(t.view.reset);
        await t.pumpWidget(Caudal(
          s: await _servicios(ses),
          child: MaterialApp(
            theme: temaCaudal(),
            builder: (context, h) =>
                MediaQuery(data: MediaQuery.of(context).copyWith(disableAnimations: reducido), child: h!),
            home: Scaffold(body: PortadaTarjeta(portada: const PortadaPerfil(mascota: 'nyan'), color: Colors.teal, animar: animar)),
          ),
        ));
        await t.pump(const Duration(milliseconds: 300));
      }

      await montar(animar: true);
      expect(t.binding.transientCallbackCount, greaterThan(0));
      await montar(animar: false);
      await t.pump(const Duration(milliseconds: 300));
      expect(t.binding.transientCallbackCount, 0);
      await montar(animar: true, reducido: true);
      await t.pump(const Duration(milliseconds: 300));
      expect(t.binding.transientCallbackCount, 0);
      await t.pumpWidget(const MaterialApp(home: SizedBox()));
      expect(t.takeException(), isNull);
    });

    testWidgets('tocar la canción llama a reproducir', (t) async {
      var veces = 0;
      await _montar(t, await _servicios(_Sesion()),
          Scaffold(body: PortadaTarjeta(portada: const PortadaPerfil(cancion: _cancion), color: Colors.teal, alReproducir: () => veces++)));
      await t.tap(find.textContaining('Una canción con un título'));
      expect(veces, 1);
    });
  });

  group('El editor', () {
    Future<Json?> elegir(BuildContext _) async => _cancion.comoPista();

    testWidgets('con beneficios: arma la portada y la guarda con un PATCH', (t) async {
      Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');
      final ses = _Sesion();
      await _montar(t, await _servicios(ses), PortadaPagina(elegirCancionPropia: elegir));
      expect(find.text('Elige una canción, una letra o una mascota y la verás aquí.'), findsOneWidget);
      expect(t.widget<FilledButton>(find.widgetWithText(FilledButton, 'Guardar portada')).onPressed, isNull);

      await t.tap(find.text('Elegir una canción'));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.textContaining('Una canción con un título'), findsWidgets);
      await t.enterText(find.byType(TextField), 'Mi frase de la semana');
      await t.pump();
      await t.tap(find.byKey(const ValueKey('mascota-nailong')));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Tu canción del momento'), findsOneWidget); // la vista previa en vivo

      await t.ensureVisible(find.text('Guardar portada'));
      await t.tap(find.text('Guardar portada'));
      await t.pumpAndSettle();
      final c = ses.patches.single.$3 as Map;
      expect((c['portada_letra'], c['portada_mascota']), ('Mi frase de la semana', 'nailong'));
      expect((c['portada_cancion'] as Map)['video_id'], 'abc12345678');
      expect(t.takeException(), isNull);
    });

    testWidgets('sin beneficios: se puede probar pero no guarda y avisa', (t) async {
      final ses = _Sesion();
      await _montar(t, await _servicios(ses), PortadaPagina(elegirCancionPropia: elegir));
      expect(find.text('Exclusivo para donadores'), findsOneWidget);
      expect(find.text('Donar aquí'), findsOneWidget);
      await t.enterText(find.byType(TextField), 'Probando');
      await t.pump();
      await t.ensureVisible(find.text('Guardar portada'));
      await t.tap(find.text('Guardar portada'));
      await t.pump(const Duration(milliseconds: 300));
      expect(ses.patches, isEmpty);
      expect(find.textContaining('Es exclusivo de donadores'), findsOneWidget);
    });

    testWidgets('si no se puede guardar avisa y se queda en la pantalla', (t) async {
      Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');
      final ses = _Sesion()..fallaPatch = true;
      await _montar(t, await _servicios(ses), PortadaPagina(elegirCancionPropia: elegir));
      await t.enterText(find.byType(TextField), 'Algo');
      await t.pump();
      await t.ensureVisible(find.text('Guardar portada'));
      await t.tap(find.text('Guardar portada'));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Sin conexión.'), findsOneWidget);
      expect(find.text('Portada del perfil'), findsOneWidget);
      expect(PortadasPerfil.i.mia.vacia, isTrue);
      // y se puede volver a intentar
      expect(t.widget<FilledButton>(find.widgetWithText(FilledButton, 'Guardar portada')).onPressed, isNotNull);
    });

    testWidgets('con una portada ya guardada: aparece «Quitar mi portada» y la borra', (t) async {
      Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');
      final ses = _Sesion()..portada = {'letra': 'Guardada'};
      await _montar(t, await _servicios(ses), const PortadaPagina());
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Guardada'), findsOneWidget); // en el campo de letra
      await t.ensureVisible(find.text('Quitar mi portada'));
      await t.tap(find.text('Quitar mi portada'));
      await t.pumpAndSettle();
      expect(ses.patches.single.$3, {'portada_cancion': null, 'portada_letra': null, 'portada_mascota': null});
    });

    testWidgets('sin desbordes en 320x568 con letra grande', (t) async {
      Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');
      await _montar(t, await _servicios(_Sesion()), PortadaPagina(elegirCancionPropia: elegir), tam: const Size(320, 568), letra: 1.6);
      await t.drag(find.byType(ListView), const Offset(0, -250));
      await t.pump();
      await t.tap(find.text('Elegir una canción'));
      await t.pump(const Duration(milliseconds: 300));
      await t.enterText(find.byType(TextField), 'Una frase\nen dos líneas');
      await t.pump(const Duration(milliseconds: 400));
      expect(t.takeException(), isNull);
    });
  });

  group('En el perfil', () {
    Future<void> perfil(WidgetTester t, _Sesion ses,
        {bool propia = false, bool amiga = false, Size tam = const Size(320, 800)}) async {
      await _montar(
          t,
          await _servicios(ses),
          Scaffold(
              body: SingleChildScrollView(
                  child: PortadaDePerfil(
                      usuario: propia ? 'ana' : 'beto',
                      propia: propia,
                      esAmiga: amiga,
                      color: Colors.teal,
                      social: Social(ses),
                      alReproducir: (_) {}))),
          tam: tam);
      await t.pump(const Duration(milliseconds: 300));
    }

    testWidgets('un amigo: se pregunta y se ve la portada', (t) async {
      final ses = _Sesion()
        ..portada = {
          'cancion': {'video_id': 'abc12345678', 'titulo': 'Su canción', 'artista': 'Su artista', 'miniatura': ''},
          'letra': 'Su letra',
          'mascota': 'nailong',
        };
      await perfil(t, ses, amiga: true);
      expect(ses.preguntas.single.$3, {'p_usuario': 'beto'});
      expect(find.text('Su canción del momento'), findsOneWidget);
      expect(find.text('Su canción'), findsOneWidget);
      expect(find.textContaining('Su letra'), findsOneWidget);
      expect(find.byIcon(Icons.edit_rounded), findsNothing); // no es mía: sin botón de editar
      expect(t.takeException(), isNull);
    });

    testWidgets('quien no es amigo: ni se pregunta ni ocupa lugar', (t) async {
      final ses = _Sesion()..portada = {'letra': 'secreta'};
      await perfil(t, ses);
      expect(ses.preguntas, isEmpty);
      expect(find.textContaining('secreta'), findsNothing);
      expect(t.getSize(find.byType(PortadaDePerfil)).height, 0);
    });

    testWidgets('un amigo sin portada: no ocupa lugar', (t) async {
      final ses = _Sesion();
      await perfil(t, ses, amiga: true);
      expect(t.getSize(find.byType(PortadaDePerfil)).height, 0);
    });

    testWidgets('sin internet no se rompe y no se ve nada', (t) async {
      final ses = _Sesion()..sinRed = true;
      await perfil(t, ses, amiga: true);
      expect(t.takeException(), isNull);
      expect(t.getSize(find.byType(PortadaDePerfil)).height, 0);
    });

    testWidgets('lo mío con beneficios: la portada con botón de editar', (t) async {
      Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');
      final ses = _Sesion()..portada = {'letra': 'Mi letra', 'mascota': 'nyan'};
      await perfil(t, ses, propia: true);
      expect(find.text('Portada'), findsOneWidget);
      expect(find.textContaining('Mi letra'), findsOneWidget);
      expect(find.byIcon(Icons.edit_rounded), findsOneWidget);
    });

    testWidgets('lo mío con beneficios y sin portada: invitación a crearla', (t) async {
      Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');
      await perfil(t, _Sesion(), propia: true);
      expect(find.text('Crea tu portada'), findsOneWidget);
      await t.tap(find.text('Crea tu portada'));
      await t.pumpAndSettle();
      expect(find.text('Portada del perfil'), findsOneWidget); // abrió el editor
    });

    testWidgets('lo mío sin beneficios: invitación bloqueada que lleva al editor para probar', (t) async {
      await perfil(t, _Sesion(), propia: true);
      expect(find.text('Portada del perfil'), findsOneWidget);
      expect(find.textContaining('Exclusiva para donadores'), findsOneWidget);
      expect(find.byIcon(Icons.lock_outline_rounded), findsOneWidget);
    });

    testWidgets('si se acaba el premium, mi portada guardada deja de verse', (t) async {
      Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');
      final ses = _Sesion()..portada = {'letra': 'Mi letra'};
      await perfil(t, ses, propia: true);
      expect(find.textContaining('Mi letra'), findsOneWidget);
      Premium.i.estado = const EstadoPremium();
      Premium.i.notifyListeners();
      await t.pump();
      expect(find.textContaining('Mi letra'), findsNothing);
      expect(find.byIcon(Icons.lock_outline_rounded), findsOneWidget);
    });
  });
}
