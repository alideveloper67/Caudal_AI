// Pases de regalo: modelo y llamadas (crear, listar, anular), la tarjeta de «Personalizar» y el aviso
// de una sola vez. Sin red: la sesión de la nube es un doble que contesta lo que contestaría la base.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/pases_regalo.dart';
import 'package:caudal/nucleo/premium.dart';
import 'package:caudal/nucleo/social.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/premium/personalizar_pagina.dart';
import 'package:caudal/ui/premium/regalo_pases.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _Sesion extends Sesion {
  _Sesion() : super('yo', 'token', 'r', DateTime.now().add(const Duration(hours: 1)));

  Object? premium = {'premium': true, 'tipo': 'donador', 'vence': null};
  List<Map<String, Object?>> pases = [];
  Object? respuestaCrear;
  String? errorCrear;
  String? errorLista;
  bool anularDice = true;
  int _n = 0;
  final enviados = <(String, String, Object?)>[];

  int llamadas(String ruta) => enviados.where((e) => e.$2 == 'rpc/$ruta').length;

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    enviados.add((metodo, ruta, cuerpo));
    switch (ruta) {
      case 'rpc/mi_premium':
        return premium;
      case 'rpc/mis_pases_regalo':
        if (errorLista != null) throw ErrorNube(errorLista!);
        return pases;
      case 'rpc/crear_pase_regalo':
        if (errorCrear != null) throw ErrorNube(errorCrear!);
        if (respuestaCrear != null) return respuestaCrear;
        if (pases.where((p) => p['vigente'] == true && p['usado'] != true).length >= 3) {
          return {'ok': false, 'mensaje': 'Ya tienes 3 códigos sin usar. Cuando un amigo canjee uno, puedes crear otro.'};
        }
        final cod = 'NEW${++_n}A-BCDE';
        pases.insert(0, {
          'codigo': cod, 'dias': 7, 'usado': false, 'caduca': '2099-12-18T10:00:00Z', 'vigente': true,
        });
        return {'ok': true, 'codigo': cod, 'dias': 7, 'caduca': '2099-12-18T10:00:00Z'};
      case 'rpc/anular_pase_regalo':
        if (!anularDice) return false;
        pases.removeWhere((p) => p['codigo'] == (cuerpo as Map)['p_codigo']);
        return true;
    }
    return null;
  }
}

Map<String, Object?> _fila(String cod, {bool usado = false, bool vigente = true, String? caduca = '2099-12-18T10:00:00Z'}) =>
    {'codigo': cod, 'dias': 7, 'usado': usado, 'caduca': caduca, 'vigente': vigente};

class _Reproductor extends ChangeNotifier implements Reproductor {
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

Future<void> _montar(WidgetTester t, Servicios s, Widget hijo, {Size tam = const Size(411, 1800)}) async {
  t.view.physicalSize = tam * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(s: s, child: MaterialApp(theme: temaCaudal(), home: hijo)));
  await t.pump(const Duration(milliseconds: 200));
}

Future<void> _tarjeta(WidgetTester t, _Sesion ses, {List<String>? compartidos, Size? tam}) async {
  await Premium.i.iniciar('yo', Social(ses));
  await _montar(
    t,
    await _servicios(ses),
    Scaffold(
      body: ListView(padding: const EdgeInsets.all(16), children: [
        TarjetaRegalo(compartir: (x) async => compartidos?.add(x)),
      ]),
    ),
    tam: tam ?? const Size(411, 1800),
  );
  await t.pump(const Duration(milliseconds: 200));
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    Premium.i.reiniciar();
  });

  group('Modelo', () {
    test('estado: usado gana sobre caducado; vigente = sin usar', () {
      expect(PaseRegalo.desde(_fila('AAAA-BBBB'))!.estado, EstadoPase.sinUsar);
      expect(PaseRegalo.desde(_fila('AAAA-BBBB', usado: true, vigente: false))!.estado, EstadoPase.usado);
      expect(PaseRegalo.desde(_fila('AAAA-BBBB', vigente: false))!.estado, EstadoPase.caducado);
      expect(PaseRegalo.desde(_fila('AAAA-BBBB', usado: true))!.sePuedeAnular, isFalse);
      expect(PaseRegalo.desde(_fila('AAAA-BBBB', vigente: false))!.sePuedeAnular, isTrue);
      expect(EstadoPase.sinUsar.etiqueta, 'Sin usar');
    });

    test('lee la lista y descarta basura', () {
      final l = PaseRegalo.lista([_fila('abcd-efgh'), 'x', null, {'codigo': ''}, _fila('JJJJ-KKKK', usado: true)]);
      expect(l.map((p) => p.codigo), ['ABCD-EFGH', 'JJJJ-KKKK']);
      expect(l.first.caduca, isNotNull);
      expect(PaseRegalo.lista(null), isEmpty);
      expect(PaseRegalo.lista('basura'), isEmpty);
      expect(PasesRegalo.sinUsar(l), 1);
    });

    test('crear: respuesta buena, mala y rara', () {
      final ok = ResultadoCrearPase.desde({'ok': true, 'codigo': 'ab12-cd34', 'dias': 7, 'caduca': '2026-12-18T10:00:00Z'});
      expect((ok.ok, ok.pase!.codigo, ok.pase!.dias), (true, 'AB12-CD34', 7));
      final no = ResultadoCrearPase.desde({'ok': false, 'mensaje': 'Ya tienes 3 códigos sin usar.'});
      expect((no.ok, no.mensaje, no.pase), (false, 'Ya tienes 3 códigos sin usar.', null));
      expect(ResultadoCrearPase.desde(null).ok, isFalse);
      expect(ResultadoCrearPase.desde({'ok': true}).ok, isFalse);
    });

    test('solo donadores y fundadores vigentes pueden regalar', () {
      bool puede(String tipo, {bool premium = true}) =>
          PasesRegalo.puedeRegalar(EstadoPremium(premium: premium, tipo: tipo));
      expect(puede('donador'), isTrue);
      expect(puede('fundador'), isTrue);
      expect(puede('prueba'), isFalse);
      expect(puede(''), isFalse);
      expect(puede('donador', premium: false), isFalse);
      expect(PasesRegalo.puedeRegalar(EstadoPremium.ninguno), isFalse);
    });

    test('el texto para compartir lleva el código, los 7 días y el enlace', () {
      final t = PasesRegalo.textoCompartir('AB12-CD34');
      expect(t, contains('AB12-CD34'));
      expect(t, contains('7 días'));
      expect(t, contains('beneficios de donador'));
      expect(t, contains('https://caudal-musica.netlify.app'));
      expect(t.toLowerCase(), isNot(contains('ánimo')));
    });
  });

  group('Llamadas al servidor', () {
    test('crear, listar y anular hablan con las funciones del servidor', () async {
      final ses = _Sesion();
      final social = Social(ses);
      final r = await PasesRegalo.crear(social);
      expect(r.ok, isTrue);
      expect(ses.llamadas('crear_pase_regalo'), 1);
      final l = await PasesRegalo.listar(social);
      expect(l.single.codigo, r.pase!.codigo);
      final a = await PasesRegalo.anular(social, ' ${r.pase!.codigo.toLowerCase()} ');
      expect(a.ok, isTrue);
      expect(ses.enviados.last.$3, {'p_codigo': r.pase!.codigo});
      expect(await PasesRegalo.listar(social), isEmpty);
    });

    test('el tope de 3 llega con el mensaje del servidor', () async {
      final ses = _Sesion();
      final social = Social(ses);
      for (var i = 0; i < 3; i++) {
        expect((await PasesRegalo.crear(social)).ok, isTrue);
      }
      final r = await PasesRegalo.crear(social);
      expect(r.ok, isFalse);
      expect(r.mensaje, startsWith('Ya tienes 3 códigos sin usar'));
    });

    test('un error de red no lanza: vuelve como mensaje', () async {
      final ses = _Sesion()..errorCrear = 'Sin conexión.';
      final r = await PasesRegalo.crear(Social(ses));
      expect((r.ok, r.mensaje), (false, 'Sin conexión.'));
      ses.errorLista = 'Sin conexión.';
      await expectLater(PasesRegalo.listar(Social(ses)), throwsA(isA<ErrorNube>()));
    });

    test('anular uno que ya se usó: el servidor dice false', () async {
      final ses = _Sesion()..anularDice = false;
      final r = await PasesRegalo.anular(Social(ses), 'AAAA-BBBB');
      expect(r.ok, isFalse);
      expect(r.mensaje, contains('ya no se puede anular'));
    });
  });

  group('Aviso de una sola vez', () {
    test('toca a donadores y fundadores, una sola vez', () async {
      const donador = EstadoPremium(premium: true, tipo: 'donador');
      const fundador = EstadoPremium(premium: true, tipo: 'fundador');
      const prueba = EstadoPremium(premium: true, tipo: 'prueba');
      expect(await AvisoPasesRegalo.toca(prueba), isFalse);
      expect(await AvisoPasesRegalo.toca(EstadoPremium.ninguno), isFalse);
      expect(await AvisoPasesRegalo.toca(fundador), isTrue);
      expect(await AvisoPasesRegalo.toca(donador), isTrue);
      await AvisoPasesRegalo.marcarVisto();
      expect(await AvisoPasesRegalo.toca(donador), isFalse);
      expect(await AvisoPasesRegalo.toca(fundador), isFalse);
    });

    testWidgets('la hoja: «Ver mis códigos» devuelve true, «Ahora no» false', (t) async {
      bool? r;
      await t.pumpWidget(MaterialApp(
        theme: temaCaudal(),
        home: Builder(
          builder: (c) => Scaffold(
            body: Center(
              child: FilledButton(onPressed: () async => r = await mostrarAvisoPasesRegalo(c), child: const Text('abrir')),
            ),
          ),
        ),
      ));
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle();
      expect(find.text('Ahora puedes regalar códigos de prueba a tus amigos'), findsOneWidget);
      await t.tap(find.text('Ver mis códigos'));
      await t.pumpAndSettle();
      expect(r, isTrue);
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle();
      await t.tap(find.text('Ahora no'));
      await t.pumpAndSettle();
      expect(r, isFalse);
    });

    testWidgets('sin desbordes en 320x568', (t) async {
      t.view.physicalSize = const Size(640, 1136);
      t.view.devicePixelRatio = 2;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(
        theme: temaCaudal(),
        home: Builder(
          builder: (c) => Scaffold(body: TextButton(onPressed: () => mostrarAvisoPasesRegalo(c), child: const Text('abrir'))),
        ),
      ));
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle();
      expect(t.takeException(), isNull);
    });
  });

  group('Tarjeta «Regala una prueba»', () {
    testWidgets('un donador la ve y sus códigos salen con su estado', (t) async {
      final ses = _Sesion()
        ..pases = [
          _fila('AAAA-BBBB'),
          _fila('CCCC-DDDD', usado: true, vigente: false),
          _fila('EEEE-FFFF', vigente: false),
        ];
      await _tarjeta(t, ses);
      expect(find.text('Regala una prueba a tus amigos'), findsOneWidget);
      expect(find.text('Crear código'), findsOneWidget);
      expect(find.text('Sin usar'), findsOneWidget);
      expect(find.text('Usado'), findsOneWidget);
      expect(find.text('Caducado'), findsOneWidget);
      expect(find.text('AAAA-BBBB'), findsOneWidget);
      // copiar y compartir solo en el que se puede usar; anular en los que nadie usó
      expect(find.byTooltip('Copiar código AAAA-BBBB'), findsOneWidget);
      expect(find.byTooltip('Compartir código CCCC-DDDD'), findsNothing);
      expect(find.byTooltip('Anular código AAAA-BBBB'), findsOneWidget);
      expect(find.byTooltip('Anular código CCCC-DDDD'), findsNothing);
      expect(find.byTooltip('Anular código EEEE-FFFF'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('un fundador también', (t) async {
      final ses = _Sesion()..premium = {'premium': true, 'tipo': 'fundador', 'vence': null};
      await _tarjeta(t, ses);
      expect(find.text('Crear código'), findsOneWidget);
    });

    testWidgets('una prueba o quien no dona no la ven ni piden nada al servidor', (t) async {
      for (final p in [
        {'premium': true, 'tipo': 'prueba', 'vence': DateTime.now().add(const Duration(days: 3)).toUtc().toIso8601String()},
        {'premium': false, 'tipo': null, 'vence': null},
      ]) {
        Premium.i.reiniciar();
        final ses = _Sesion()..premium = p;
        await _tarjeta(t, ses);
        expect(find.text('Crear código'), findsNothing);
        expect(ses.llamadas('mis_pases_regalo'), 0);
      }
    });

    testWidgets('crear: el código nuevo aparece arriba', (t) async {
      final ses = _Sesion();
      await _tarjeta(t, ses);
      await t.tap(find.text('Crear código'));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('NEW1A-BCDE'), findsOneWidget);
      expect(find.text('Sin usar'), findsOneWidget);
      expect(ses.llamadas('crear_pase_regalo'), 1);
      expect(t.takeException(), isNull);
    });

    testWidgets('el cuarto código muestra el mensaje del servidor', (t) async {
      final ses = _Sesion()..pases = [_fila('AAAA-BBBB'), _fila('CCCC-DDDD'), _fila('EEEE-FFFF')];
      await _tarjeta(t, ses);
      await t.tap(find.text('Crear código'));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.textContaining('Ya tienes 3 códigos sin usar'), findsOneWidget);
      expect(find.text('Sin usar'), findsNWidgets(3));
    });

    testWidgets('copiar deja el código en el portapapeles', (t) async {
      String? copiado;
      t.binding.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, (c) async {
        if (c.method == 'Clipboard.setData') copiado = (c.arguments as Map)['text'] as String?;
        return null;
      });
      addTearDown(() => t.binding.defaultBinaryMessenger.setMockMethodCallHandler(SystemChannels.platform, null));
      final ses = _Sesion()..pases = [_fila('AAAA-BBBB')];
      await _tarjeta(t, ses);
      await t.tap(find.byTooltip('Copiar código AAAA-BBBB'));
      await t.pump();
      expect(copiado, 'AAAA-BBBB');
    });

    testWidgets('compartir manda el texto con el código y el enlace', (t) async {
      final enviados = <String>[];
      final ses = _Sesion()..pases = [_fila('AAAA-BBBB')];
      await _tarjeta(t, ses, compartidos: enviados);
      await t.tap(find.byTooltip('Compartir código AAAA-BBBB'));
      await t.pump();
      expect(enviados.single, PasesRegalo.textoCompartir('AAAA-BBBB'));
      expect(enviados.single, contains('https://caudal-musica.netlify.app'));
    });

    testWidgets('anular pide confirmación y quita el código', (t) async {
      final ses = _Sesion()..pases = [_fila('AAAA-BBBB'), _fila('CCCC-DDDD')];
      await _tarjeta(t, ses);
      await t.tap(find.byTooltip('Anular código AAAA-BBBB'));
      await t.pumpAndSettle();
      expect(find.text('¿Anular este código?'), findsOneWidget);
      await t.tap(find.text('Cancelar'));
      await t.pumpAndSettle();
      expect(ses.llamadas('anular_pase_regalo'), 0);
      expect(find.text('AAAA-BBBB'), findsOneWidget);
      await t.tap(find.byTooltip('Anular código AAAA-BBBB'));
      await t.pumpAndSettle();
      await t.tap(find.text('Anular'));
      await t.pumpAndSettle();
      expect(ses.llamadas('anular_pase_regalo'), 1);
      expect(find.text('AAAA-BBBB'), findsNothing);
      expect(find.text('CCCC-DDDD'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('si no carga la lista: mensaje y «Reintentar»', (t) async {
      final ses = _Sesion()..errorLista = 'Sin conexión.';
      await _tarjeta(t, ses);
      expect(find.textContaining('No se pudieron cargar tus códigos'), findsOneWidget);
      ses
        ..errorLista = null
        ..pases = [_fila('AAAA-BBBB')];
      await t.tap(find.text('Reintentar'));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('AAAA-BBBB'), findsOneWidget);
    });

    testWidgets('dentro de Personalizar: solo para donadores', (t) async {
      final ses = _Sesion()..pases = [_fila('AAAA-BBBB')];
      await Premium.i.iniciar('yo', Social(ses));
      await _montar(t, await _servicios(ses), const PersonalizarPagina());
      await t.pump(const Duration(milliseconds: 300));
      // la tarjeta va al final de la lista (tras las secciones nuevas): hay que bajar hasta ella
      await t.scrollUntilVisible(find.text('Regala una prueba a tus amigos'), 300,
          scrollable: find.byType(Scrollable).first);
      expect(find.text('Regala una prueba a tus amigos'), findsOneWidget);
      expect(find.text('AAAA-BBBB'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('sin desbordes en 320x568 con códigos largos', (t) async {
      final ses = _Sesion()
        ..pases = [_fila('AAAA-BBBB'), _fila('CCCC-DDDD', usado: true, vigente: false), _fila('EEEE-FFFF', vigente: false)];
      await _tarjeta(t, ses, tam: const Size(320, 568));
      expect(t.takeException(), isNull);
    });
  });
}
