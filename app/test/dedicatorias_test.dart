// Dedicatorias (donadores): la tarjeta que viaja dentro de un mensaje con canción, el fragmento que suena al
// abrirla, la hoja para crearla y cómo se ve y se manda en el chat. Sin red ni audio: dobles de todo.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/chat.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/dedicatorias.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/premium.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/paginas/mensajes_pagina.dart';
import 'package:caudal/ui/premium/dedicatoria_ui.dart';
import 'package:caudal/ui/premium/temas_premium.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Json _pista([String id = 'abc12345678']) => {
      'tipo': 'pista',
      'clave': 'yt:$id',
      'video_id': id,
      'titulo': 'Una canción con un título bastante largo para probar el recorte de la tarjeta',
      'artista': 'Una artista con un nombre también largo',
      'miniatura': '',
    };

// ------------------------------------------------------------ dobles

class _Reproductor extends ChangeNotifier implements Reproductor {
  @override
  Json? actual;
  @override
  EstadoRepro estado = EstadoRepro.parado;
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(const Duration(minutes: 3));
  final llamadas = <String>[];
  Json? ultimaConRadio;

  @override
  Future<void> reproducirPista(Json pista, {Json? contexto, String? modo, bool conRadio = true}) async {
    llamadas.add('reproducir:${pista['video_id']}:radio=$conRadio');
    actual = pista;
    estado = EstadoRepro.sonando;
    notifyListeners();
  }

  @override
  Future<void> buscar(Duration p) async {
    llamadas.add('buscar:${p.inSeconds}');
    posicion.value = p;
  }

  @override
  Future<void> pausar() async {
    llamadas.add('pausar');
    estado = EstadoRepro.pausa;
    notifyListeners();
  }

  @override
  Future<void> dispose() async => super.dispose();
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Coleccion extends ChangeNotifier implements Coleccion {
  @override
  Future<List<Json>> meGustaRecientes(int n) async => [_pista('fav00000001')];
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

class _Sesion extends Sesion {
  _Sesion() : super('yo', 'token', 'r', DateTime.now().add(const Duration(hours: 1)));
  final enviados = <Map>[];
  List<Map> mensajes = [];

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    if (ruta.startsWith('mensajes?')) return mensajes;
    if (ruta == 'rpc/marcar_leido') return null;
    if (ruta == 'mensajes' && metodo == 'POST') {
      final c = Map<String, dynamic>.from(cuerpo as Map);
      final fila = {
        'id': 100 + enviados.length,
        'autor': 'yo',
        'texto': c['texto'],
        'pista': c['pista'],
        'creado': DateTime.now().toUtc().toIso8601String()
      };
      enviados.add(fila);
      return [fila];
    }
    return null;
  }
}

late _Reproductor _r;
late _Sesion _nube;

Future<Servicios> _servicios() async {
  _r = _Reproductor();
  _nube = _Sesion();
  return Servicios(
    cuenta: Cuenta(id: 'yo', usuario: 'yo', nombre: 'Yo', sesion: _nube),
    ajustes: await Ajustes.cargar('prueba'),
    coleccion: _Coleccion(),
    reproductor: _r,
    streams: _Streams(),
    descargas: _Descargas(),
    cerrarSesion: () async {},
  );
}

Future<Servicios> _montar(WidgetTester t, Widget hijo,
    {Size tam = const Size(411, 900), double letra = 1, Servicios? s}) async {
  s ??= await _servicios();
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

/// Un control de reproductor falso que anota lo que le piden.
class _Control {
  final pasos = <String>[];
  Json? actual;
  bool sonando = false;
  Duration duracion = const Duration(minutes: 3);
  bool fallaAlReproducir = false;

  /// Al reproducir, ¿empieza a sonar solo?
  bool arrancaSolo = true;

  ControlFragmento get control => ControlFragmento(
        actual: () => actual,
        sonando: () => sonando,
        duracion: () => duracion,
        reproducir: (p) async {
          pasos.add('reproducir');
          if (fallaAlReproducir) throw StateError('no suena');
          actual = p;
          sonando = arrancaSolo;
        },
        buscar: (d) async => pasos.add('buscar:${d.inSeconds}'),
        pausar: () async {
          pasos.add('pausar');
          sonando = false;
        },
      );
}

SonarFragmento _sonador(_Control c, {int largoMs = 60, int esperaMs = 80}) => SonarFragmento(c.control,
    paso: const Duration(milliseconds: 5),
    largo: Duration(milliseconds: largoMs),
    esperaMaxima: Duration(milliseconds: esperaMs));

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    Premium.i.reiniciar();
  });

  group('Dedicatoria (modelo)', () {
    test('viaja dentro de la pista y se lee de vuelta', () {
      final p = Dedicatoria.conDedicatoria(_pista(), const Dedicatoria(mensaje: '  Para ti  ', estilo: 'sakura', inicio: 45));
      expect(Dedicatoria.esDedicatoria(p), isTrue);
      final d = Dedicatoria.de(p)!;
      expect((d.mensaje, d.estilo, d.inicio), ('Para ti', 'sakura', 45));
      expect(d.inicioTexto, '0:45');
      expect(p['video_id'], 'abc12345678'); // la canción sigue siendo reproducible
    });

    test('lo raro se arregla: estilo desconocido, inicio fuera de rango, mensaje larguísimo', () {
      final d = Dedicatoria.de(Dedicatoria.conDedicatoria(
          _pista(), Dedicatoria(mensaje: 'x' * 500, estilo: 'inventado', inicio: 99999)))!;
      expect(d.estilo, 'aurora');
      expect(d.inicio, Dedicatoria.maxInicio);
      expect(d.mensaje.length, Dedicatoria.maxMensaje);
      // y lo que llega crudo de la red también
      final crudo = Dedicatoria.de({'dedicatoria': {'mensaje': 5, 'estilo': null, 'inicio': 'abc'}})!;
      expect((crudo.mensaje, crudo.estilo, crudo.inicio), ('5', 'aurora', 0));
      expect(Dedicatoria.de({'titulo': 'sin tarjeta'}), isNull);
      expect(Dedicatoria.de(null), isNull);
    });

    test('pistaLimpia quita la tarjeta y deja la canción', () {
      final p = Dedicatoria.conDedicatoria(_pista(), const Dedicatoria(mensaje: 'hola'));
      final l = Dedicatoria.pistaLimpia(p);
      expect(Dedicatoria.esDedicatoria(l), isFalse);
      expect(l['video_id'], 'abc12345678');
      // dedicar dos veces la misma pista no acumula nada
      final otra = Dedicatoria.conDedicatoria(p, const Dedicatoria(mensaje: 'segunda'));
      expect(Dedicatoria.de(otra)!.mensaje, 'segunda');
    });

    test('tiempo y quién puede dedicar qué', () {
      expect(Dedicatoria.tiempo(0), '0:00');
      expect(Dedicatoria.tiempo(65), '1:05');
      expect(Dedicatoria.tiempo(600), '10:00');
      expect(Dedicatoria.tiempo(-5), '0:00');
      expect(Dedicatoria.sePuedeDedicar(_pista()), isTrue);
      expect(Dedicatoria.sePuedeDedicar({'titulo': 'archivo del teléfono'}), isFalse);
      expect(Dedicatoria.sePuedeDedicar(null), isFalse);
      expect(Dedicatoria.puedeEnviar(), isFalse);
      _donador();
      expect(Dedicatoria.puedeEnviar(), isTrue);
    });

    test('en la lista de chats se ve como dedicatoria, no como canción suelta', () {
      final p = Dedicatoria.conDedicatoria(_pista(), const Dedicatoria(mensaje: 'x'));
      final r = ResumenChat.desde({
        'id': 'c', 'otro': 'o', 'usuario': 'luis', 'nombre': 'Luis', 'ultimo': '2026-11-14T10:00:00Z',
        'ultimo_pista': p, 'ultimo_autor': 'yo',
      }, 'yo');
      expect(r.vistaPrevia, startsWith('Tú: 💌 Dedicatoria · Una canción'));
      final normal = ResumenChat.desde({
        'id': 'c', 'otro': 'o', 'usuario': 'luis', 'nombre': 'Luis', 'ultimo': '2026-11-14T10:00:00Z',
        'ultimo_pista': _pista(), 'ultimo_autor': 'o',
      }, 'yo');
      expect(normal.vistaPrevia, startsWith('♪ '));
    });

    test('el mensaje del servidor conserva la tarjeta', () {
      final p = Dedicatoria.conDedicatoria(_pista(), const Dedicatoria(mensaje: 'hola', estilo: 'bosque', inicio: 30));
      final m = Mensaje.desde({'id': 1, 'autor': 'o', 'texto': '', 'pista': p, 'creado': '2026-11-14T10:00:00Z'});
      expect(Dedicatoria.de(m.pista)!.estilo, 'bosque');
      expect(m.pista!['video_id'], 'abc12345678');
    });

    test('al enviarla, el cuerpo del mensaje lleva la tarjeta (sin nada nuevo en el servidor)', () async {
      final ses = _Sesion();
      final p = Dedicatoria.conDedicatoria(_pista(), const Dedicatoria(mensaje: 'hola', inicio: 20));
      await Chat(ses).enviar('c1', pista: p);
      final pista = ses.enviados.single['pista'] as Map;
      expect((pista['dedicatoria'] as Map)['inicio'], 20);
      expect(pista['video_id'], 'abc12345678');
    });
  });

  group('SonarFragmento', () {
    test('suena, salta al inicio elegido y se calla solo', () async {
      final c = _Control();
      final ok = await _sonador(c).iniciar(
          Dedicatoria.conDedicatoria(_pista(), const Dedicatoria(mensaje: 'x', inicio: 45)), const Dedicatoria(mensaje: 'x', inicio: 45));
      expect(ok, isTrue);
      expect(c.pasos, ['reproducir', 'buscar:45', 'pausar']);
      // la tarjeta no se cuela en lo que suena
      expect(Dedicatoria.esDedicatoria(c.actual), isFalse);
    });

    test('inicio 0: no hace falta saltar', () async {
      final c = _Control();
      await _sonador(c).iniciar(_pista(), const Dedicatoria(mensaje: ''));
      expect(c.pasos, ['reproducir', 'pausar']);
    });

    test('si la canción es más corta que el inicio, suena desde el principio', () async {
      final c = _Control()..duracion = const Duration(seconds: 40);
      await _sonador(c).iniciar(_pista(), const Dedicatoria(mensaje: '', inicio: 120));
      expect(c.pasos, ['reproducir', 'pausar']);
    });

    test('si la persona cambia de canción, no se mete ni pausa lo suyo', () async {
      final c = _Control();
      final f = _sonador(c, largoMs: 200).iniciar(_pista(), const Dedicatoria(mensaje: ''));
      await Future<void>.delayed(const Duration(milliseconds: 40));
      c.actual = _pista('otra0000000');
      expect(await f, isTrue);
      expect(c.pasos, ['reproducir']);
    });

    test('si la persona pausa a mano, tampoco', () async {
      final c = _Control();
      final f = _sonador(c, largoMs: 200).iniciar(_pista(), const Dedicatoria(mensaje: ''));
      await Future<void>.delayed(const Duration(milliseconds: 40));
      c.sonando = false;
      await f;
      expect(c.pasos, ['reproducir']);
    });

    test('«Escuchar completa» (cancelar) deja seguir la música', () async {
      final c = _Control();
      final s = _sonador(c, largoMs: 200);
      final f = s.iniciar(_pista(), const Dedicatoria(mensaje: ''));
      await Future<void>.delayed(const Duration(milliseconds: 30));
      s.cancelar();
      await f;
      expect(c.pasos, ['reproducir']);
      expect(c.sonando, isTrue);
    });

    test('si nunca llega a sonar, devuelve false sin colgarse', () async {
      final c = _Control()..arrancaSolo = false;
      expect(await _sonador(c).iniciar(_pista(), const Dedicatoria(mensaje: '')), isFalse);
      expect(c.pasos, ['reproducir']);
    });

    test('si el reproductor falla, no lanza: simplemente no suena', () async {
      final c = _Control()..fallaAlReproducir = true;
      expect(await _sonador(c).iniciar(_pista(), const Dedicatoria(mensaje: '')), isFalse);
    });

    test('no arranca dos veces a la vez', () async {
      final c = _Control();
      final s = _sonador(c, largoMs: 80);
      final a = s.iniciar(_pista(), const Dedicatoria(mensaje: ''));
      expect(await s.iniciar(_pista(), const Dedicatoria(mensaje: '')), isFalse);
      await a;
      expect(c.pasos.where((e) => e == 'reproducir').length, 1);
    });
  });

  group('La tarjeta', () {
    test('cada estilo lleva texto blanco legible (AA) en sus tres tonos', () {
      expect({for (final e in estilosDedicatoria) e.clave}, Dedicatoria.estilos.toSet());
      for (final e in estilosDedicatoria) {
        for (final f in e.fondo) {
          expect(TemasPremium.contraste(Colors.white, f), greaterThanOrEqualTo(4.5), reason: '${e.clave} $f');
        }
      }
    });

    for (final tam in const [Size(320, 568), Size(411, 800)]) {
      for (final letra in const [1.0, 1.8]) {
        testWidgets('compacta y grande, cada estilo, sin desbordes a ${tam.width.toInt()}x${tam.height.toInt()} letra x$letra', (t) async {
          for (final e in Dedicatoria.estilos) {
            final d = Dedicatoria(mensaje: 'Un mensaje largo para ti, que ocupa varias líneas y sigue y sigue ' * 3, estilo: e, inicio: 30);
            await _montar(
                t,
                SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: Column(children: [
                      TarjetaDedicatoria(pista: _pista(), dedicatoria: d, etiqueta: 'Dedicatoria de Alguien con un nombre muy largo para probar'),
                      const SizedBox(height: 16),
                      TarjetaDedicatoria(pista: _pista(), dedicatoria: d, etiqueta: 'Dedicatoria para Ana', grande: true),
                    ])),
                tam: tam,
                letra: letra);
            expect(t.takeException(), isNull, reason: e);
          }
        });
      }
    }

    testWidgets('sin mensaje también se ve bien', (t) async {
      await _montar(t, Scaffold(body: TarjetaDedicatoria(pista: _pista(), dedicatoria: const Dedicatoria(mensaje: ''), etiqueta: 'x')),
          tam: const Size(320, 568));
      expect(t.takeException(), isNull);
    });
  });

  group('Abrirla', () {
    Future<Servicios> abrir(WidgetTester t, {required bool mia, SonarFragmento? sonador, Size tam = const Size(411, 900)}) async {
      final p = Dedicatoria.conDedicatoria(_pista(), const Dedicatoria(mensaje: 'Esta me recuerda a ti', estilo: 'oceano', inicio: 30));
      final s = await _montar(
          t,
          Builder(
              builder: (ctx) => Scaffold(
                  body: Center(
                      child: TextButton(
                          onPressed: () => abrirDedicatoria(ctx, pista: p, otro: 'Luis', mia: mia, sonador: sonador),
                          child: const Text('abrir'))))),
          tam: tam);
      await t.tap(find.text('abrir'));
      await t.pump(const Duration(milliseconds: 600));
      return s;
    }

    testWidgets('una dedicatoria recibida: se ve la tarjeta y suena un fragmento', (t) async {
      final c = _Control();
      await abrir(t, mia: false, sonador: _sonador(c, largoMs: 400, esperaMs: 400));
      expect(find.text('Dedicatoria de Luis'), findsOneWidget);
      expect(find.text('Esta me recuerda a ti'), findsOneWidget);
      expect(find.textContaining('Una canción con un título'), findsOneWidget);
      await t.pump(const Duration(milliseconds: 800));
      expect(c.pasos, ['reproducir', 'buscar:30', 'pausar']);
      expect(find.text('El fragmento terminó'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('con el reproductor de Caudal: la canción sin radio y el corte a los 20 s', (t) async {
      final s = await abrir(t, mia: false);
      expect(_r.llamadas.first, 'reproducir:abc12345678:radio=false');
      await t.pump(const Duration(seconds: 1));
      expect(_r.llamadas, contains('buscar:30'));
      expect(find.textContaining('Suena un fragmento de 20 segundos'), findsOneWidget);
      await t.pump(const Duration(seconds: 25));
      expect(_r.llamadas.last, 'pausar');
      expect(s.reproductor.actual!.containsKey('dedicatoria'), isFalse);
    });

    testWidgets('la mía: se ve pero no suena sola', (t) async {
      final c = _Control();
      await abrir(t, mia: true, sonador: _sonador(c));
      expect(find.text('Tu dedicatoria para Luis'), findsOneWidget);
      await t.pump(const Duration(milliseconds: 300));
      expect(c.pasos, isEmpty);
    });

    testWidgets('«Escuchar la canción» deja la música sonando y cierra', (t) async {
      final c = _Control();
      await abrir(t, mia: false, sonador: _sonador(c, largoMs: 3000, esperaMs: 3000));
      await t.pump(const Duration(milliseconds: 100));
      await t.tap(find.text('Escuchar la canción'));
      await t.pumpAndSettle();
      expect(find.text('Dedicatoria de Luis'), findsNothing);
      expect(c.pasos.contains('pausar'), isFalse);
    });

    testWidgets('si no se pudo sonar, avisa pero la tarjeta se lee igual', (t) async {
      final c = _Control()..fallaAlReproducir = true;
      await abrir(t, mia: false, sonador: _sonador(c));
      await t.pump(const Duration(milliseconds: 100));
      expect(find.text('Esta me recuerda a ti'), findsOneWidget);
      expect(find.textContaining('No se pudo reproducir el fragmento'), findsOneWidget);
    });

    testWidgets('en 320x568 con letra grande no hay desbordes', (t) async {
      final c = _Control();
      await abrir(t, mia: false, sonador: _sonador(c, largoMs: 50, esperaMs: 50), tam: const Size(320, 568));
      await t.pump(const Duration(milliseconds: 100));
      expect(t.takeException(), isNull);
    });
  });

  group('Crearla', () {
    Future<void> abrir(WidgetTester t, void Function(Json?) alTerminar,
        {Json? sonando, Size tam = const Size(411, 900), double letra = 1}) async {
      await _montar(
          t,
          Builder(
              builder: (ctx) => Scaffold(
                  body: Center(
                      child: TextButton(
                          onPressed: () async => alTerminar(await hojaDedicar(ctx,
                              para: 'Luis',
                              sonando: sonando,
                              buscador: (q) async => [_pista('busc0000001')],
                              favoritas: () async => [_pista('fav00000001')])),
                          child: const Text('dedicar'))))),
          tam: tam,
          letra: letra);
      await t.tap(find.text('dedicar'));
      await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
    }

    testWidgets('un donador: elige estilo, mensaje y fragmento y devuelve la pista con la tarjeta', (t) async {
      _donador();
      Json? salida;
      await abrir(t, (p) => salida = p, sonando: _pista());
      expect(find.text('Dedicar una canción a Luis'), findsOneWidget);
      expect(find.text('Dedicatoria para Luis'), findsOneWidget); // vista previa con lo que suena
      await t.enterText(find.byType(TextField), 'Escucha esta');
      await t.pump();
      expect(find.text('Escucha esta'), findsWidgets);
      await t.ensureVisible(find.byKey(const ValueKey('estilo-sakura')));
      await t.pump();
      await t.tap(find.byKey(const ValueKey('estilo-sakura')));
      await t.pump(const Duration(milliseconds: 200));
      await t.drag(find.byType(Slider), const Offset(60, 0));
      await t.pump();
      await t.ensureVisible(find.text('Enviar dedicatoria'));
      await t.pump();
      await t.tap(find.text('Enviar dedicatoria'));
      await t.pumpAndSettle();
      final d = Dedicatoria.de(salida)!;
      expect((d.mensaje, d.estilo), ('Escucha esta', 'sakura'));
      expect(d.inicio, greaterThan(0));
      expect(salida!['video_id'], 'abc12345678');
    });

    testWidgets('sin nada sonando: hay que elegir la canción antes de poder enviar', (t) async {
      _donador();
      Json? salida;
      await abrir(t, (p) => salida = p);
      expect(t.widget<FilledButton>(find.widgetWithText(FilledButton, 'Enviar dedicatoria')).onPressed, isNull);
      await t.ensureVisible(find.text('Elegir la canción'));
      await t.pump();
      await t.tap(find.text('Elegir la canción'));
      await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
      expect(find.text('Tus «me gusta»'), findsOneWidget);
      await t.tap(find.byKey(const ValueKey('cancion-fav00000001')));
      await t.pumpAndSettle();
      await t.ensureVisible(find.text('Enviar dedicatoria'));
      await t.pump();
      await t.tap(find.text('Enviar dedicatoria'));
      await t.pumpAndSettle();
      expect(salida!['video_id'], 'fav00000001');
    });

    testWidgets('una canción de archivo del teléfono no se ofrece como la que suena', (t) async {
      _donador();
      await abrir(t, (_) {}, sonando: {'titulo': 'local', 'archivo': '/x.mp3'});
      expect(t.widget<FilledButton>(find.widgetWithText(FilledButton, 'Enviar dedicatoria')).onPressed, isNull);
    });

    testWidgets('quien no dona ve el aviso, no la hoja', (t) async {
      Json? salida = {'x': 1};
      await abrir(t, (p) => salida = p, sonando: _pista());
      expect(find.text('Las dedicatorias son para donadores'), findsOneWidget);
      expect(find.text('Enviar dedicatoria'), findsNothing);
      expect(find.text('Donar aquí'), findsOneWidget);
      expect(salida, isNotNull); // todavía no se cerró nada
    });

    testWidgets('sin desbordes en 320x568 con letra grande', (t) async {
      _donador();
      await abrir(t, (_) {}, sonando: _pista(), tam: const Size(320, 568), letra: 1.6);
      await t.enterText(find.byType(TextField), 'Un mensaje que ocupa un par de líneas en pantalla chica');
      await t.pump(const Duration(milliseconds: 300));
      expect(t.takeException(), isNull);
    });
  });

  group('En el chat', () {
    final chat = ResumenChat.desde(
        {'id': 'c1', 'otro': 'o', 'usuario': 'luis', 'nombre': 'Luis', 'ultimo': '2026-11-14T10:00:00Z'}, 'yo');

    testWidgets('mandar una dedicatoria: sale por el chat de siempre y se ve la tarjeta', (t) async {
      _donador();
      final s = await _servicios();
      s.reproductor.actual = _pista();
      await _montar(t, ConversacionPagina(chat: chat), s: s);
      await t.tap(find.byTooltip('Dedicar una canción'));
      await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
      await t.enterText(find.byType(TextField).last, 'Va con cariño');
      await t.pump();
      await t.ensureVisible(find.text('Enviar dedicatoria'));
      await t.pump();
      await t.tap(find.text('Enviar dedicatoria'));
      await t.pump();
      await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
      expect(_nube.enviados.length, 1);
      final pista = _nube.enviados.single['pista'] as Map;
      expect((pista['dedicatoria'] as Map)['mensaje'], 'Va con cariño');
      expect(pista['video_id'], 'abc12345678');
      expect(find.text('Dedicatoria para Luis'), findsOneWidget);
      expect(find.text('Toca para verla'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('quien no dona toca el sobre y recibe el aviso; nada se envía', (t) async {
      await _montar(t, ConversacionPagina(chat: chat));
      await t.tap(find.byTooltip('Dedicar una canción'));
      await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
      expect(find.text('Las dedicatorias son para donadores'), findsOneWidget);
      expect(_nube.enviados, isEmpty);
    });

    testWidgets('una dedicatoria recibida se muestra como tarjeta y al tocarla se abre y suena', (t) async {
      final s = await _servicios();
      _nube.mensajes = [
        {
          'id': 5,
          'autor': 'o',
          'texto': '',
          'pista': Dedicatoria.conDedicatoria(_pista(), const Dedicatoria(mensaje: 'Para ti, Yo', estilo: 'bosque', inicio: 15)),
          'creado': DateTime.now().toUtc().toIso8601String(),
        }
      ];
      await _montar(t, ConversacionPagina(chat: chat), s: s);
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Dedicatoria de Luis'), findsOneWidget);
      expect(find.text('Toca para abrir y escuchar'), findsOneWidget);
      expect(find.text('Para ti, Yo'), findsOneWidget);
      await t.tap(find.text('Toca para abrir y escuchar'));
      await t.pump(const Duration(milliseconds: 700));
      expect(find.text('Escuchar la canción'), findsOneWidget);
      expect(_r.llamadas.first, startsWith('reproducir:abc12345678'));
      await t.pump(const Duration(seconds: 1));
      expect(_r.llamadas, contains('buscar:15'));
      await t.pump(const Duration(seconds: 25)); // el fragmento termina solo
      await t.tap(find.text('Cerrar'));
      await t.pumpAndSettle();
      expect(find.text('Escuchar la canción'), findsNothing);
      expect(t.takeException(), isNull);
    });

    testWidgets('los mensajes de siempre (texto y canción suelta) siguen igual', (t) async {
      final s = await _servicios();
      _nube.mensajes = [
        {'id': 1, 'autor': 'o', 'texto': 'hola', 'pista': null, 'creado': DateTime.now().toUtc().toIso8601String()},
        {'id': 2, 'autor': 'o', 'texto': '', 'pista': _pista('suelta00000'), 'creado': DateTime.now().toUtc().toIso8601String()},
      ];
      await _montar(t, ConversacionPagina(chat: chat), s: s);
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('hola'), findsOneWidget);
      expect(find.byIcon(Icons.play_circle_fill_rounded), findsOneWidget);
      expect(find.textContaining('Dedicatoria de'), findsNothing);
    });

    for (final tam in const [Size(320, 568), Size(360, 640)]) {
      testWidgets('el chat con dedicatorias no desborda a ${tam.width.toInt()}x${tam.height.toInt()}', (t) async {
        final s = await _servicios();
        _nube.mensajes = [
          for (var i = 0; i < 2; i++)
            {
              'id': i + 1,
              'autor': i == 0 ? 'o' : 'yo',
              'texto': '',
              'pista': Dedicatoria.conDedicatoria(
                  _pista(), Dedicatoria(mensaje: 'Un mensaje largo que ocupa varias líneas ' * 4, estilo: Dedicatoria.estilos[i])),
              'creado': DateTime.now().toUtc().toIso8601String(),
            }
        ];
        await _montar(t, ConversacionPagina(chat: chat), s: s, tam: tam);
        await t.pump(const Duration(milliseconds: 400));
        expect(t.takeException(), isNull);
        expect(find.byTooltip('Dedicar una canción'), findsOneWidget);
        expect(find.byTooltip('Mezcla'), findsOneWidget); // en angosto, solo el icono
      });
    }
  });
}
