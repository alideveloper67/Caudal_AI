// Beneficios de donador: estado y servicio Premium, paleta de los temas, marcos y efectos de nombre,
// pantalla «Personalizar» (bloqueada y desbloqueada) y el canje de un pase de prueba.
// Sin red: la sesión de la nube es un doble que contesta lo que contestaría la base de datos.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cosmeticos.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/premium.dart';
import 'package:caudal/nucleo/social.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/paginas/perfil_comun.dart';
import 'package:caudal/ui/premium/canje_pase.dart';
import 'package:caudal/ui/premium/marcos.dart';
import 'package:caudal/ui/premium/personalizar_pagina.dart';
import 'package:caudal/ui/premium/temas_premium.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _Sesion extends Sesion {
  _Sesion() : super('yo', 'token', 'r', DateTime.now().add(const Duration(hours: 1)));

  Object? premium = {'premium': true, 'tipo': 'donador', 'vence': null};
  Object? pase = {'ok': true, 'mensaje': 'Pase canjeado.', 'dias': 7, 'vence': '2026-11-25T15:00:00Z'};
  String? errorPase;
  Object? filaPerfil = [
    {'marco': 'oro', 'efecto_nombre': 'neon', 'tema_premium': 'oceano'}
  ];
  bool sinMiPremium = false;
  bool fallaPatch = false;
  Object? puedeFondo = true;
  final enviados = <(String, String, Object?)>[];

  Iterable<(String, String, Object?)> get patches => enviados.where((e) => e.$1 == 'PATCH');

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    enviados.add((metodo, ruta, cuerpo));
    if (ruta == 'rpc/mi_premium') {
      if (sinMiPremium) throw const ErrorNube('function mi_premium does not exist');
      return premium;
    }
    if (ruta == 'rpc/puede_poner_fondo') return puedeFondo;
    if (ruta == 'rpc/canjear_pase') {
      if (errorPase != null) throw ErrorNube(errorPase!);
      return pase;
    }
    if (metodo == 'GET') return filaPerfil;
    if (metodo == 'PATCH') {
      if (fallaPatch) throw const ErrorNube('Sin conexión.');
      return null;
    }
    return null;
  }
}

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

void main() {
  final ahora = DateTime(2026, 11, 18, 12);

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    Premium.i.reiniciar();
  });

  group('EstadoPremium', () {
    test('una prueba vigente: días que quedan, aviso cuando falta poco', () {
      final e = EstadoPremium.desde({
        'premium': true, 'tipo': 'prueba', 'vence': ahora.add(const Duration(days: 2)).toUtc().toIso8601String()
      });
      expect(e.esPrueba, isTrue);
      expect(e.vigente(ahora), isTrue);
      expect(e.diasRestantes(ahora), 2);
      expect(e.pocaPrueba(ahora: ahora), isTrue);
    });

    test('los días se redondean hacia arriba: faltando horas queda 1', () {
      final e = EstadoPremium(premium: true, tipo: 'prueba', vence: ahora.add(const Duration(hours: 5)));
      expect(e.diasRestantes(ahora), 1);
      expect(AvisoPrueba.texto(e, ahora: ahora), 'Tu prueba vence hoy');
    });

    test('una prueba con tiempo de sobra no avisa', () {
      final e = EstadoPremium(premium: true, tipo: 'prueba', vence: ahora.add(const Duration(days: 6)));
      expect(e.pocaPrueba(ahora: ahora), isFalse);
    });

    test('vencida: ya no vale aunque el servidor lo dijera hace un rato', () {
      final e = EstadoPremium(premium: true, tipo: 'prueba', vence: ahora.subtract(const Duration(hours: 1)));
      expect(e.vigente(ahora), isFalse);
      expect(e.diasRestantes(ahora), 0);
      expect(e.pocaPrueba(ahora: ahora), isFalse);
    });

    test('donador sin fecha: siempre vigente y sin aviso', () {
      final e = EstadoPremium.desde({'premium': true, 'tipo': 'donador', 'vence': null});
      expect(e.vigente(ahora), isTrue);
      expect(e.diasRestantes(ahora), isNull);
      expect(e.pocaPrueba(ahora: ahora), isFalse);
    });

    test('sin beneficios: el tipo se descarta; respuestas raras no rompen', () {
      expect(EstadoPremium.desde({'premium': false, 'tipo': 'donador'}).tipo, '');
      expect(EstadoPremium.desde(null), EstadoPremium.ninguno);
      expect(EstadoPremium.desde('basura'), EstadoPremium.ninguno);
      expect(EstadoPremium.desde([{'premium': true, 'tipo': 'fundador'}]).tipo, 'fundador');
    });

    test('ida y vuelta por JSON', () {
      final e = EstadoPremium(premium: true, tipo: 'prueba', vence: DateTime.utc(2026, 11, 25, 15));
      expect(EstadoPremium.desde(e.aJson()), e);
    });
  });

  group('ResultadoPase y claves', () {
    test('lee la respuesta del servidor', () {
      final r = ResultadoPase.desde({'ok': true, 'mensaje': 'Listo', 'dias': 7, 'vence': '2026-11-25T15:00:00Z'});
      expect((r.ok, r.dias, r.mensaje), (true, 7, 'Listo'));
      expect(r.vence, isNotNull);
      expect(ResultadoPase.desde(null).ok, isFalse);
      expect(ResultadoPase.desde({'ok': false, 'mensaje': 'Ese código ya se usó.'}).mensaje, 'Ese código ya se usó.');
    });

    test('lo desconocido es «ninguno»', () {
      expect(Cosmeticos.marco('oro'), 'oro');
      expect(Cosmeticos.marco('ORO'), 'oro');
      expect(Cosmeticos.marco('dragon'), 'ninguno');
      expect(Cosmeticos.efectoNombre(null), 'ninguno');
      expect(Cosmeticos.tema('sakura'), 'sakura');
    });

    test('los modelos sociales leen marco y efecto; si faltan, «ninguno»', () {
      final c = Contacto.amigo({'id': 'a', 'usuario': 'x', 'marco': 'fuego', 'efecto_nombre': 'brillo'});
      expect((c.marco, c.efectoNombre), ('fuego', 'brillo'));
      final sin = Contacto.amigo({'id': 'a', 'usuario': 'x'});
      expect((sin.marco, sin.efectoNombre), ('ninguno', 'ninguno'));
      final t = PerfilTarjeta.desde({'id': 'a', 'usuario': 'x', 'marco': 'raro'});
      expect(t.marco, 'ninguno');
      expect(t.conLike(true, 3).marco, 'ninguno');
    });

    test('el código se formatea como XXXX-XXXX', () {
      expect(FormatoCodigoPase.normalizar('ab12cd34'), 'AB12-CD34');
      expect(FormatoCodigoPase.normalizar('ab12-cd34'), 'AB12-CD34');
      expect(FormatoCodigoPase.normalizar(' ab 12 '), 'AB12');
      expect(FormatoCodigoPase.normalizar('abcdefghijklmnop').replaceAll('-', '').length, 12);
    });

    test('textoPrueba', () {
      expect(textoPrueba(7, DateTime(2026, 11, 25), ahora: ahora), 'Tienes 7 días de prueba (vence el 25 de noviembre)');
      expect(textoPrueba(1, null), 'Tienes 1 día de prueba');
    });
  });

  group('Premium (servicio)', () {
    test('al iniciar trae el estado y lo elegido', () async {
      final ses = _Sesion();
      await Premium.i.iniciar('yo', Social(ses));
      expect(Premium.i.activo, isTrue);
      expect((Premium.i.marcoEfectivo, Premium.i.efectoNombreEfectivo, Premium.i.temaEfectivo), ('oro', 'neon', 'oceano'));
    });

    test('sin beneficios nada se aplica, aunque haya elecciones guardadas', () async {
      final ses = _Sesion()..premium = {'premium': false, 'tipo': null, 'vence': null};
      await Premium.i.iniciar('yo', Social(ses));
      expect(Premium.i.activo, isFalse);
      expect((Premium.i.marcoEfectivo, Premium.i.efectoNombreEfectivo, Premium.i.temaEfectivo),
          ('ninguno', 'ninguno', 'ninguno'));
    });

    test('un servidor sin mi_premium se resuelve con puede_poner_fondo', () async {
      final ses = _Sesion()..sinMiPremium = true;
      await Premium.i.iniciar('yo', Social(ses));
      expect(Premium.i.activo, isTrue);
      expect(Premium.i.estado.tipo, 'donador');
    });

    test('se recuerda en el teléfono para cuando no hay internet', () async {
      await Premium.i.iniciar('yo', Social(_Sesion()));
      Premium.i.reiniciar();
      expect(Premium.i.activo, isFalse);
      await Premium.i.iniciar('yo', null);
      expect(Premium.i.activo, isTrue);
      expect(Premium.i.marco, 'oro');
    });

    test('una prueba guardada que ya venció no se aplica sin conexión', () async {
      final ses = _Sesion()
        ..premium = {
          'premium': true, 'tipo': 'prueba',
          'vence': DateTime.now().subtract(const Duration(hours: 2)).toUtc().toIso8601String()
        };
      await Premium.i.iniciar('yo', Social(ses));
      Premium.i.reiniciar();
      await Premium.i.iniciar('yo', null);
      expect(Premium.i.activo, isFalse);
      expect(Premium.i.temaEfectivo, 'ninguno');
    });

    test('canjear: éxito refresca el estado', () async {
      final ses = _Sesion()..premium = {'premium': false, 'tipo': null, 'vence': null};
      final social = Social(ses);
      await Premium.i.iniciar('yo', social);
      expect(Premium.i.activo, isFalse);
      ses.premium = {
        'premium': true, 'tipo': 'prueba',
        'vence': DateTime.now().add(const Duration(days: 7)).toUtc().toIso8601String()
      };
      final r = await Premium.i.canjear(social, ' ab12-cd34 ');
      expect(r.ok, isTrue);
      expect(r.dias, 7);
      expect(Premium.i.activo, isTrue);
      expect(Premium.i.estado.esPrueba, isTrue);
      final llamada = ses.enviados.lastWhere((e) => e.$2 == 'rpc/canjear_pase');
      expect(llamada.$3, {'p_codigo': 'AB12-CD34'});
    });

    test('canjear: el mensaje del servidor llega tal cual', () async {
      final ses = _Sesion()..errorPase = 'Ese código ya se usó.';
      final r = await Premium.i.canjear(Social(ses), 'ABCD-EFGH');
      expect(r.ok, isFalse);
      expect(r.mensaje, 'Ese código ya se usó.');
      expect((await Premium.i.canjear(Social(ses), '  ')).ok, isFalse);
    });

    test('guardar manda el PATCH; si falla se deshace y avisa', () async {
      final ses = _Sesion();
      final social = Social(ses);
      await Premium.i.iniciar('yo', social);
      await Premium.i.guardar(social, marco: 'aurora', tema: 'sakura');
      expect((Premium.i.marco, Premium.i.tema), ('aurora', 'sakura'));
      expect(ses.patches.last.$3, {'marco': 'aurora', 'tema_premium': 'sakura'});

      ses.fallaPatch = true;
      await expectLater(Premium.i.guardar(social, marco: 'fuego'), throwsA(isA<ErrorNube>()));
      expect(Premium.i.marco, 'aurora');
    });
  });

  group('Paleta de los temas', () {
    for (final t in TemasPremium.lista) {
      test('${t.nombre}: texto legible (AA) sobre sus capas y botón del acento', () {
        for (var i = 0; i < 5; i++) {
          expect(TemasPremium.contraste(C.texto, t.capas[i]), greaterThanOrEqualTo(4.5), reason: 'texto sobre la capa $i');
        }
        for (var i = 0; i < 4; i++) {
          expect(TemasPremium.contraste(C.texto2, t.capas[i]), greaterThanOrEqualTo(4.5), reason: 'texto2 sobre la capa $i');
        }
        expect(TemasPremium.contraste(t.acentoTexto, t.acento), greaterThanOrEqualTo(4.5), reason: 'texto del botón');
        expect(TemasPremium.contraste(t.acento, t.capas[0]), greaterThanOrEqualTo(3.0), reason: 'acento sobre el fondo');
        // las capas suben de claridad: fondo < panel < superficie < superficie2 < superficie3
        for (var i = 0; i < 4; i++) {
          expect(TemasPremium.luminancia(t.capas[i + 1]), greaterThan(TemasPremium.luminancia(t.capas[i])),
              reason: 'capa ${i + 1} más clara que la $i');
        }
      });
    }

    test('hay un tema por cada clave del contrato y ninguno de más', () {
      expect({for (final t in TemasPremium.lista) t.clave}, Cosmeticos.temas.where((c) => c != 'ninguno').toSet());
    });

    test('Aspecto.aplicar usa el tema premium vigente y vuelve a lo normal al perderlo', () async {
      Aspecto.aplicar('cian', 'oscuro');
      final normal = C.fondo;
      Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');
      Premium.i.tema = 'oceano';
      Aspecto.aplicar('cian', 'oscuro');
      final oceano = TemasPremium.de('oceano')!;
      expect((C.fondo, C.acento, C.superficie2), (oceano.capas[0], oceano.acento, oceano.capas[3]));
      expect(Aspecto.patron, isNull);
      // se acaba la prueba: todo vuelve a lo elegido
      Premium.i.estado = EstadoPremium(premium: true, tipo: 'prueba', vence: DateTime.now().subtract(const Duration(minutes: 1)));
      Aspecto.aplicar('cian', 'oscuro');
      expect(C.fondo, normal);
      Premium.i.reiniciar();
    });
  });

  group('Marcos y efectos', () {
    for (final tam in const [Size(320, 568), Size(1440, 900)]) {
      testWidgets('cada marco y cada efecto montan sin desbordes a ${tam.width.toInt()}x${tam.height.toInt()}', (t) async {
        t.view.physicalSize = tam;
        t.view.devicePixelRatio = 1;
        addTearDown(t.view.reset);
        for (final marco in Cosmeticos.marcos) {
          await t.pumpWidget(MaterialApp(
            theme: temaCaudal(),
            home: Scaffold(
              body: Column(children: [
                for (final r in const [10.0, 24.0, 54.0])
                  AvatarPerfil(nombre: 'Ana', radio: r, marco: marco, animar: true),
                ListTile(
                  leading: AvatarPerfil(nombre: 'Ana', radio: 20, marco: marco),
                  title: const Text('Una fila de lista'),
                  subtitle: const Text('@ana'),
                ),
              ]),
            ),
          ));
          await t.pump(const Duration(milliseconds: 300));
          await t.pump(const Duration(milliseconds: 300));
          expect(t.takeException(), isNull, reason: 'marco $marco');
          // el marco no mueve nada: mide lo mismo que sin marco
          expect(t.getSize(find.byType(AvatarPerfil).at(1)), const Size(48, 48), reason: 'marco $marco');
        }
        for (final efecto in Cosmeticos.efectosNombre) {
          await t.pumpWidget(MaterialApp(
            theme: temaCaudal(),
            home: Scaffold(
              body: Column(children: [
                SizedBox(
                  width: 120,
                  child: NombreEfecto('Un nombre larguísimo para probar el recorte', efecto: efecto, animar: true,
                      estilo: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
                ),
                ListTile(title: NombreEfecto('Ana', efecto: efecto), subtitle: const Text('@ana')),
              ]),
            ),
          ));
          await t.pump(const Duration(milliseconds: 400));
          await t.pump(const Duration(milliseconds: 400));
          expect(t.takeException(), isNull, reason: 'efecto $efecto');
        }
      });
    }

    testWidgets('quieto donde no se anima: sin animar o con «Quitar animaciones» no hay cuadros pendientes', (t) async {
      Future<void> montar({required bool animar, bool reducido = false}) => t.pumpWidget(MaterialApp(
            theme: temaCaudal(),
            builder: (context, hijo) =>
                MediaQuery(data: MediaQuery.of(context).copyWith(disableAnimations: reducido), child: hijo!),
            home: Scaffold(
              body: Column(children: [
                AvatarPerfil(nombre: 'Ana', radio: 40, marco: 'arcoiris', animar: animar),
                NombreEfecto('Ana', efecto: 'arcoiris', animar: animar),
              ]),
            ),
          ));
      await montar(animar: false);
      await t.pump(const Duration(milliseconds: 300));
      expect(t.binding.transientCallbackCount, 0, reason: 'en listas no se anima');
      await montar(animar: true, reducido: true);
      await t.pump(const Duration(milliseconds: 300));
      expect(t.binding.transientCallbackCount, 0, reason: 'con «Quitar animaciones» tampoco');
      await montar(animar: true);
      await t.pump(const Duration(milliseconds: 300));
      expect(t.binding.transientCallbackCount, greaterThan(0), reason: 'el perfil sí se anima');
      // al salir de pantalla se detiene (los controladores se liberan sin errores)
      await t.pumpWidget(const MaterialApp(home: SizedBox()));
      expect(t.takeException(), isNull);
    });
  });

  group('Personalizar', () {
    testWidgets('bloqueada: todo con candado, vista previa sí, nada se guarda', (t) async {
      final ses = _Sesion()..premium = {'premium': false, 'tipo': null, 'vence': null};
      await Premium.i.iniciar('yo', Social(ses));
      await _montar(t, await _servicios(ses), const PersonalizarPagina());
      expect(find.text('Exclusivo para donadores'), findsOneWidget);
      expect(find.text('Donar aquí'), findsOneWidget);
      expect(find.text('Tengo un código'), findsOneWidget);
      // 7 marcos + 4 efectos + 6 temas con candado (las opciones «Ninguno» y «Normal» no lo llevan)
      expect(find.byIcon(Icons.lock_rounded), findsNWidgets(17));
      await t.tap(find.text('Aurora'));
      await t.pump(const Duration(milliseconds: 300));
      expect(ses.patches, isEmpty);
      expect(Premium.i.marco, 'ninguno');
      expect(t.takeException(), isNull);
    });

    testWidgets('desbloqueada: sin candados y al tocar se aplica y se guarda', (t) async {
      final ses = _Sesion()..filaPerfil = [<String, dynamic>{}];
      await Premium.i.iniciar('yo', Social(ses));
      await _montar(t, await _servicios(ses), const PersonalizarPagina());
      expect(find.byIcon(Icons.lock_rounded), findsNothing);
      expect(find.text('Exclusivo para donadores'), findsNothing);
      expect(find.textContaining('todo está desbloqueado'), findsOneWidget);
      await t.tap(find.text('Aurora'));
      await t.pump(const Duration(milliseconds: 300));
      await t.tap(find.text('Degradado'));
      await t.pump(const Duration(milliseconds: 300));
      await t.tap(find.text('Océano'));
      await t.pump(const Duration(milliseconds: 300));
      expect((Premium.i.marco, Premium.i.efectoNombre, Premium.i.tema), ('aurora', 'degradado', 'oceano'));
      expect(ses.patches.map((e) => e.$3).toList(), [
        {'marco': 'aurora'}, {'efecto_nombre': 'degradado'}, {'tema_premium': 'oceano'},
      ]);
      expect(t.takeException(), isNull);
    });

    testWidgets('si no se puede guardar, la elección se deshace con un aviso', (t) async {
      final ses = _Sesion()
        ..filaPerfil = [<String, dynamic>{}]
        ..fallaPatch = true;
      await Premium.i.iniciar('yo', Social(ses));
      await _montar(t, await _servicios(ses), const PersonalizarPagina());
      await t.tap(find.text('Fuego'));
      await t.pump(const Duration(milliseconds: 300));
      expect(Premium.i.marco, 'ninguno');
      expect(t.takeException(), isNull);
    });

    testWidgets('una prueba muestra sus días y la opción de otro código', (t) async {
      final ses = _Sesion()
        ..filaPerfil = [<String, dynamic>{}]
        ..premium = {
          'premium': true, 'tipo': 'prueba',
          'vence': DateTime.now().add(const Duration(days: 5, hours: 3)).toUtc().toIso8601String()
        };
      await Premium.i.iniciar('yo', Social(ses));
      await _montar(t, await _servicios(ses), const PersonalizarPagina());
      expect(find.textContaining('Tienes 6 días de prueba'), findsOneWidget);
      expect(find.text('Tengo un código de prueba'), findsOneWidget);
    });

    testWidgets('a punto de vencer: aviso discreto', (t) async {
      final ses = _Sesion()
        ..filaPerfil = [<String, dynamic>{}]
        ..premium = {
          'premium': true, 'tipo': 'prueba',
          'vence': DateTime.now().add(const Duration(hours: 30)).toUtc().toIso8601String()
        };
      await Premium.i.iniciar('yo', Social(ses));
      await _montar(t, await _servicios(ses), const PersonalizarPagina());
      expect(find.text('Tu prueba vence en 2 días'), findsOneWidget);
    });

    testWidgets('sin candados ni desbordes en 320x568', (t) async {
      final ses = _Sesion()..filaPerfil = [<String, dynamic>{}];
      await Premium.i.iniciar('yo', Social(ses));
      await _montar(t, await _servicios(ses), const PersonalizarPagina(), tam: const Size(320, 568));
      expect(t.takeException(), isNull);
    });
  });

  group('Canje del pase', () {
    Future<void> abrir(WidgetTester t, _Sesion ses) async {
      await _montar(
        t,
        await _servicios(ses),
        Builder(builder: (context) => Scaffold(body: Center(child: TextButton(
            onPressed: () => mostrarCanjePase(context), child: const Text('abrir'))))),
        tam: const Size(411, 800),
      );
      await t.tap(find.text('abrir'));
      await t.pump(const Duration(milliseconds: 400));
    }

    testWidgets('escribir, canjear y ver los días de prueba', (t) async {
      final ses = _Sesion()
        ..premium = {
          'premium': true, 'tipo': 'prueba',
          'vence': DateTime.utc(2026, 11, 25, 15).toIso8601String()
        };
      await abrir(t, ses);
      await t.enterText(find.byType(TextField), 'ab12cd34');
      await t.pump();
      expect(find.text('AB12-CD34'), findsOneWidget);
      await t.tap(find.text('Canjear'));
      await t.pump(const Duration(milliseconds: 400));
      expect(find.textContaining('Tienes 7 días de prueba'), findsOneWidget);
      expect(find.textContaining('vence el'), findsOneWidget);
      expect(Premium.i.estado.esPrueba, isTrue);
      expect(ses.enviados.where((e) => e.$2 == 'rpc/canjear_pase').single.$3, {'p_codigo': 'AB12-CD34'});
      await t.tap(find.widgetWithText(FilledButton, 'Listo'));
      await t.pumpAndSettle();
      expect(find.text('Listo'), findsNothing);
    });

    testWidgets('un código malo muestra el mensaje del servidor y deja reintentar', (t) async {
      final ses = _Sesion()..errorPase = 'Ese código no existe o ya venció.';
      await abrir(t, ses);
      await t.enterText(find.byType(TextField), 'zzzz9999');
      await t.pump();
      await t.tap(find.text('Canjear'));
      await t.pump(const Duration(milliseconds: 400));
      expect(find.text('Ese código no existe o ya venció.'), findsOneWidget);
      // se puede corregir y volver a intentar
      expect(find.text('Canjear'), findsOneWidget);
      expect(Premium.i.activo, isFalse);
    });

    testWidgets('el botón espera a que haya un código', (t) async {
      await abrir(t, _Sesion());
      final boton = t.widget<FilledButton>(find.widgetWithText(FilledButton, 'Canjear'));
      expect(boton.onPressed, isNull);
      await t.enterText(find.byType(TextField), 'ab12');
      await t.pump();
      expect(t.widget<FilledButton>(find.widgetWithText(FilledButton, 'Canjear')).onPressed, isNotNull);
    });
  });
}
