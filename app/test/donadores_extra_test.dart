// Más para donadores: color del nombre (paleta, servicio, caché en lote y pintura), pared de
// agradecimiento, mascota propia por WhatsApp y letra con efectos. Sin red: la sesión es un doble.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/colores_nombre.dart';
import 'package:caudal/nucleo/cosmeticos.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/donadores_extra.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/premium.dart';
import 'package:caudal/nucleo/social.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/premium/letra_escena.dart';
import 'package:caudal/ui/premium/marcos.dart';
import 'package:caudal/ui/premium/mas_donadores.dart';
import 'package:caudal/ui/premium/nombre_color.dart';
import 'package:caudal/ui/premium/pared_pagina.dart';
import 'package:caudal/ui/premium/personalizar_pagina.dart';
import 'package:caudal/ui/reproductor/paleta_portada.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _Sesion extends Sesion {
  _Sesion() : super('yo', 'token', 'r', DateTime.now().add(const Duration(hours: 1)));

  Object? premium = {'premium': true, 'tipo': 'donador', 'vence': null};
  Object? filaPerfil = [
    {'marco': 'oro', 'efecto_nombre': 'neon', 'tema_premium': 'oceano'}
  ];
  Object? filaExtra = [
    {'color_nombre': '#ff5c8a', 'en_pared': true}
  ];

  /// La base aún sin las columnas nuevas (falta aplicar donadores_extra.sql).
  bool sinColumnas = false;
  bool fallaPatch = false;
  final enviados = <(String, String, Object?)>[];

  Iterable<(String, String, Object?)> get patches => enviados.where((e) => e.$1 == 'PATCH');

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    enviados.add((metodo, ruta, cuerpo));
    if (ruta == 'rpc/mi_premium') return premium;
    if (metodo == 'GET' && ruta.contains('color_nombre')) {
      if (sinColumnas) throw const ErrorNube('El servidor de cuentas respondió un error (400).');
      return filaExtra;
    }
    if (metodo == 'GET') return filaPerfil;
    if (metodo == 'PATCH') {
      final c = cuerpo is Map ? cuerpo : const {};
      if (sinColumnas && (c.containsKey('color_nombre') || c.containsKey('en_pared'))) {
        throw const ErrorNube('El servidor de cuentas respondió un error (400).');
      }
      if (fallaPatch) throw const SinConexion();
      return null;
    }
    return null;
  }
}

class _Reproductor extends ChangeNotifier implements Reproductor {
  @override
  Future<void> dispose() async => super.dispose();
  @override
  Json? get actual => null;
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

Future<void> _montar(WidgetTester t, Servicios s, Widget hijo, {Size tam = const Size(411, 2600)}) async {
  t.view.physicalSize = tam * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(s: s, child: MaterialApp(theme: temaCaudal(), home: hijo)));
  await t.pump(const Duration(milliseconds: 200));
}

Color? _colorDelTexto(WidgetTester t, String texto) => t.widget<Text>(find.text(texto).first).style?.color;

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    Premium.i.reiniciar();
    ColoresNombre.i.reiniciar();
    ColoresNombre.llamadaPrueba = null;
    ColoresNombre.espera = const Duration(milliseconds: 60);
  });

  group('Color del nombre: datos', () {
    test('se normaliza a #RRGGBB en mayúsculas; lo que no es un color se descarta', () {
      expect(Cosmeticos.colorNombre('#ff5c8a'), '#FF5C8A');
      expect(Cosmeticos.colorNombre(' ff5c8a '), '#FF5C8A');
      expect(Cosmeticos.colorNombre('#FF5C8'), isNull);
      expect(Cosmeticos.colorNombre('rojo'), isNull);
      expect(Cosmeticos.colorNombre(''), isNull);
      expect(Cosmeticos.colorNombre(null), isNull);
    });

    test('la paleta es la del escritorio y los nombres se reconocen', () {
      expect(Cosmeticos.paletaNombre.map((c) => c.$2).toList(), [
        '#FF5C8A', '#FF7A45', '#FFC857', '#7CFFB2', '#22D3EE', '#4DA8FF', '#A78BFA', '#FF4DD2', '#F5F5F5'
      ]);
      expect(Cosmeticos.nombreDeColor('#ffc857'), 'Oro');
      expect(Cosmeticos.nombreDeColor('#123456'), 'Personalizado');
      expect(Cosmeticos.nombreDeColor(null), 'Sin color');
    });

    test('estilos de la letra: claves del escritorio y un valor por defecto', () {
      expect(Cosmeticos.estilosLetra, ['resplandor', 'ola', 'neon', 'cine']);
      expect(Cosmeticos.estiloLetra('NEON'), 'neon');
      expect(Cosmeticos.estiloLetra('raro'), 'resplandor');
    });
  });

  group('Premium: color y pared', () {
    test('se leen aparte de marco/efecto/tema y se recuerdan en el teléfono', () async {
      final ses = _Sesion();
      await Premium.i.iniciar('yo', Social(ses));
      expect(Premium.i.marco, 'oro');
      expect(Premium.i.colorNombre, '#FF5C8A');
      expect(Premium.i.colorNombreEfectivo, '#FF5C8A');
      expect(Premium.i.enPared, isTrue);
      final p = await SharedPreferences.getInstance();
      expect(p.getString('premium_yo'), contains('"color_nombre":"#FF5C8A"'));
      Premium.i.reiniciar();
      expect(Premium.i.colorNombre, isNull);
      expect(Premium.i.enPared, isFalse);
      await Premium.i.iniciar('yo', null);
      expect(Premium.i.colorNombre, '#FF5C8A', reason: 'lo guardado en el teléfono vuelve sin red');
    });

    test('sin las columnas nuevas en la base, lo de siempre se sigue leyendo', () async {
      final ses = _Sesion()..sinColumnas = true;
      await Premium.i.iniciar('yo', Social(ses));
      expect(Premium.i.activo, isTrue);
      expect(Premium.i.marco, 'oro');
      expect(Premium.i.efectoNombre, 'neon');
      expect(Premium.i.colorNombre, isNull);
      expect(Premium.i.fallosSeguidos, 0, reason: 'no cuenta como un fallo: no se reintenta en bucle');
    });

    test('sin beneficios el color no se ve aunque esté guardado; la prueba no es «donar de verdad»', () async {
      final ses = _Sesion()..premium = {'premium': false, 'tipo': null, 'vence': null};
      Premium.i.colorNombre = '#22D3EE';
      await Premium.i.iniciar('yo', Social(ses));
      expect(Premium.i.colorNombreEfectivo, isNull);
      expect(Premium.i.donaDeVerdad, isFalse);
      final vence = DateTime.now().add(const Duration(days: 3)).toUtc().toIso8601String();
      final prueba = EstadoPremium.desde({'premium': true, 'tipo': 'prueba', 'vence': vence});
      expect(Premium.esDonadorDeVerdad(prueba), isFalse);
      expect(Premium.esDonadorDeVerdad(const EstadoPremium(premium: true, tipo: 'fundador')), isTrue);
    });

    test('guardar el color y la casilla manda un PATCH; quitar el color manda null', () async {
      final ses = _Sesion();
      final social = Social(ses);
      await Premium.i.iniciar('yo', social);
      await Premium.i.guardarColorNombre(social, '#a78bfa');
      expect(ses.patches.last.$3, {'color_nombre': '#A78BFA'});
      expect(Premium.i.colorNombre, '#A78BFA');
      await Premium.i.guardarColorNombre(social, null);
      expect(ses.patches.last.$3, {'color_nombre': null});
      await Premium.i.guardarEnPared(social, false);
      expect(ses.patches.last.$3, {'en_pared': false});
      expect(Premium.i.enPared, isFalse);
    });

    test('si la base aún no lo tiene, se deshace y se explica sin jerga', () async {
      final ses = _Sesion();
      final social = Social(ses);
      await Premium.i.iniciar('yo', social);
      ses.sinColumnas = true;
      await expectLater(Premium.i.guardarColorNombre(social, '#FFC857'),
          throwsA(isA<ErrorNube>().having((e) => e.mensaje, 'mensaje', contains('todavía no está disponible'))));
      expect(Premium.i.colorNombre, '#FF5C8A');
      ses
        ..sinColumnas = false
        ..fallaPatch = true;
      await expectLater(Premium.i.guardarEnPared(social, false),
          throwsA(isA<ErrorNube>().having((e) => e.mensaje, 'mensaje', contains('Sin internet'))));
      expect(Premium.i.enPared, isTrue);
    });
  });

  group('Colores de los demás (en lote)', () {
    test('la respuesta se limpia', () {
      expect(ColoresNombre.leer({'Bea': '#ff7a45', 'x': 'rojo', '': '#FFFFFF'}), {'bea': '#FF7A45'});
      expect(ColoresNombre.leer(null), isEmpty);
    });

    test('varios nombres a la vez salen en UNA pregunta; se recuerda quién no tiene color', () async {
      final lotes = <List<String>>[];
      ColoresNombre.llamadaPrueba = (u) async {
        lotes.add(u);
        return {'bea': '#7CFFB2'};
      };
      for (final u in ['bea', '@Carlos', 'bea', 'dani']) {
        ColoresNombre.i.pedir(null, u);
      }
      await Future<void>.delayed(const Duration(milliseconds: 120));
      expect(lotes, [
        ['bea', 'carlos', 'dani']
      ]);
      expect(ColoresNombre.i.de('BEA'), '#7CFFB2');
      expect(ColoresNombre.i.de('carlos'), isNull);
      expect(ColoresNombre.i.conoce('carlos'), isTrue);
      ColoresNombre.i.pedir(null, 'carlos');
      await Future<void>.delayed(const Duration(milliseconds: 120));
      expect(lotes, hasLength(1), reason: 'no se vuelve a preguntar');
    });

    test('sin internet se vuelve a preguntar; si la base no tiene la función, no', () async {
      var veces = 0;
      ColoresNombre.llamadaPrueba = (u) async {
        veces++;
        throw const SinConexion();
      };
      ColoresNombre.i.pedir(null, 'eva');
      await Future<void>.delayed(const Duration(milliseconds: 120));
      expect(ColoresNombre.i.conoce('eva'), isFalse);
      ColoresNombre.llamadaPrueba = (u) async {
        veces++;
        throw const ErrorNube('El servidor de cuentas respondió un error (404).');
      };
      ColoresNombre.i.pedir(null, 'eva');
      await Future<void>.delayed(const Duration(milliseconds: 120));
      expect(veces, 2);
      expect(ColoresNombre.i.conoce('eva'), isTrue);
      expect(ColoresNombre.i.de('eva'), isNull);
    });

    test('nunca más de 200 por pregunta', () async {
      final lotes = <int>[];
      ColoresNombre.llamadaPrueba = (u) async {
        lotes.add(u.length);
        return const {};
      };
      for (var k = 0; k < 450; k++) {
        ColoresNombre.i.pedir(null, 'u$k');
      }
      await Future<void>.delayed(const Duration(milliseconds: 400));
      expect(lotes, [200, 200, 50]);
    });
  });

  group('Pintar el color', () {
    testWidgets('sin efecto tiñe el texto; con efecto que no lo usa, se ignora', (t) async {
      await t.pumpWidget(const MaterialApp(
        home: Column(children: [
          NombreEfecto('Ana', efecto: 'ninguno', color: Color(0xFFFF5C8A)),
          NombreEfecto('Bea', efecto: 'neon', color: Color(0xFFFF5C8A)),
          NombreEfecto('Cris', efecto: 'brillo', color: Color(0xFFFF5C8A)),
        ]),
      ));
      expect(_colorDelTexto(t, 'Ana'), const Color(0xFFFF5C8A));
      expect(_colorDelTexto(t, 'Bea'), const Color(0xFFD6F7FF));
      expect(t.takeException(), isNull);
    });

    testWidgets('el nombre de otra persona toma su color en cuanto llega', (t) async {
      ColoresNombre.llamadaPrueba = (u) async => {'bea': '#22D3EE'};
      ColoresNombre.espera = Duration.zero;
      final s = await _servicios(_Sesion());
      await _montar(t, s, const Scaffold(body: NombreConColor('Bea', usuario: 'bea')));
      await t.pump(const Duration(milliseconds: 50));
      await t.pump();
      expect(_colorDelTexto(t, 'Bea'), const Color(0xFF22D3EE));
    });

    testWidgets('el mío sale de Premium al instante (y desaparece sin beneficios)', (t) async {
      final ses = _Sesion()..filaPerfil = [{'marco': 'oro', 'efecto_nombre': 'ninguno', 'tema_premium': 'ninguno'}];
      await t.runAsync(() => Premium.i.iniciar('yo', Social(ses)));
      final s = await _servicios(ses);
      await _montar(t, s, const Scaffold(body: NombreConColor('Ana', usuario: 'ana')));
      expect(_colorDelTexto(t, 'Ana'), const Color(0xFFFF5C8A));
      Premium.i.estado = EstadoPremium.ninguno;
      Premium.i.notifyListeners();
      await t.pump();
      expect(_colorDelTexto(t, 'Ana'), isNull);
    });
  });

  group('Personalizar', () {
    testWidgets('con beneficios: elegir un color lo guarda y se ve en la vista previa', (t) async {
      final ses = _Sesion()..filaPerfil = [{'marco': 'oro', 'efecto_nombre': 'ninguno', 'tema_premium': 'ninguno'}];
      await t.runAsync(() => Premium.i.iniciar('yo', Social(ses)));
      await _montar(t, await _servicios(ses), const PersonalizarPagina());
      expect(find.text('Color del nombre'), findsOneWidget);
      expect(find.text('Más para quienes donan'), findsOneWidget);
      await t.tap(find.text('Menta'));
      await t.pump(const Duration(milliseconds: 200));
      expect(ses.patches.last.$3, {'color_nombre': '#7CFFB2'});
      expect(_colorDelTexto(t, 'Ana'), const Color(0xFF7CFFB2));
      await t.tap(find.text('Sin color'));
      await t.pump(const Duration(milliseconds: 200));
      expect(ses.patches.last.$3, {'color_nombre': null});
      expect(t.takeException(), isNull);
    });

    testWidgets('sin beneficios: candados, solo vista previa y un toque explica cómo conseguirlo', (t) async {
      final ses = _Sesion()..premium = {'premium': false, 'tipo': null, 'vence': null};
      await t.runAsync(() => Premium.i.iniciar('yo', Social(ses)));
      await _montar(t, await _servicios(ses), const PersonalizarPagina());
      await t.tap(find.text('Rosa'));
      await t.pump(const Duration(milliseconds: 200));
      expect(ses.patches, isEmpty);
      expect(_colorDelTexto(t, 'Ana'), const Color(0xFFFF5C8A), reason: 'se ve en la vista previa');
      expect(find.byIcon(Icons.lock_rounded), findsWidgets);
      await t.tap(find.text('Aparecer en la pared de agradecimiento'));
      await t.pump(const Duration(milliseconds: 400));
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.textContaining('el código de prueba no cuenta'), findsOneWidget);
      expect(find.text('Donar aquí'), findsWidgets);
      await t.tap(find.text('Entendido'));
      await t.pump(const Duration(milliseconds: 400));
      await t.tap(find.text('Letra con efectos'));
      await t.pump(const Duration(milliseconds: 400));
      expect(find.textContaining('Es para donadores'), findsOneWidget);
    });
  });

  group('Más para donadores', () {
    testWidgets('donador: la casilla guarda y la mascota abre WhatsApp con el mensaje escrito', (t) async {
      final ses = _Sesion()..filaExtra = [{'color_nombre': null, 'en_pared': false}];
      await t.runAsync(() => Premium.i.iniciar('yo', Social(ses)));
      Uri? abierto;
      await _montar(t, await _servicios(ses), Scaffold(body: SingleChildScrollView(
        child: MasParaDonadores(abrirEnlace: (u) async {
          abierto = u;
          return true;
        }),
      )));
      expect(find.byType(Switch), findsOneWidget);
      await t.tap(find.byType(Switch));
      await t.pump(const Duration(milliseconds: 200));
      expect(ses.patches.last.$3, {'en_pared': true});
      expect(find.text(MascotaPropia.explicacion), findsOneWidget);
      await t.tap(find.text('Quiero mi propia mascota'));
      await t.pump();
      expect(abierto.toString(), startsWith('https://wa.me/51902464984?text='));
      expect(abierto!.queryParameters['text'], 'Hola, soy @ana en Caudal. Quiero mi mascota personalizada.');
    });

    testWidgets('con un código de prueba: la pared y la mascota siguen con candado', (t) async {
      final vence = DateTime.now().add(const Duration(days: 3)).toUtc().toIso8601String();
      final ses = _Sesion()..premium = {'premium': true, 'tipo': 'prueba', 'vence': vence};
      await t.runAsync(() => Premium.i.iniciar('yo', Social(ses)));
      Uri? abierto;
      await _montar(t, await _servicios(ses), Scaffold(body: SingleChildScrollView(
        child: MasParaDonadores(abrirEnlace: (u) async {
          abierto = u;
          return true;
        }),
      )));
      expect(find.byType(Switch), findsNothing);
      await t.tap(find.text('Quiero mi propia mascota'));
      await t.pump(const Duration(milliseconds: 400));
      expect(abierto, isNull);
      expect(find.text('Tu propia mascota'), findsOneWidget);
    });
  });

  group('Mascota propia', () {
    test('el mensaje lleva el usuario y el enlace va codificado', () {
      expect(MascotaPropia.mensaje('@luz'), 'Hola, soy @luz en Caudal. Quiero mi mascota personalizada.');
      final u = MascotaPropia.enlace('luz');
      expect(u.host, 'wa.me');
      expect(u.path, '/51902464984');
      expect(u.toString(), contains('Hola%2C%20soy%20%40luz'));
      expect(MascotaPropia.mensaje(''), contains('Quiero mi mascota personalizada'));
    });
  });

  group('Pared de agradecimiento', () {
    test('se limpia y van primero los fundadores', () {
      final l = ParedAgradecimiento.leer([
        {'usuario': 'dona', 'nombre': 'Doña', 'tipo': 'donador', 'color': '#22d3ee', 'desde': '2026-03-01T00:00:00Z'},
        {'usuario': 'funda', 'nombre': '', 'tipo': 'fundador', 'color': null},
        {'usuario': 'raro', 'tipo': 'prueba'},
        {'nombre': 'sin usuario', 'tipo': 'donador'},
        'basura',
        {'usuario': 'otra', 'nombre': 'Otra', 'tipo': 'donador'},
      ]);
      expect(l.map((d) => d.usuario).toList(), ['funda', 'dona', 'otra']);
      expect(l.first.nombre, 'funda');
      expect(l.first.etiqueta, 'Fundador');
      expect(l[1].color, '#22D3EE');
      expect(l[1].desde, isNotNull);
      expect(ParedAgradecimiento.leer(null), isEmpty);
    });

    testWidgets('la pantalla: lista, vacía y sin conexión', (t) async {
      final s = await _servicios(_Sesion());
      await _montar(t, s, ParedPagina(cargar: () async => [
            const DonadorPared(usuario: 'funda', nombre: 'Funda', tipo: 'fundador', color: '#FFC857'),
            const DonadorPared(usuario: 'dona', nombre: 'Dona', tipo: 'donador'),
          ]));
      await t.pump();
      expect(find.text('Funda'), findsOneWidget);
      expect(find.text('Fundador'), findsOneWidget);
      expect(_colorDelTexto(t, 'Funda'), const Color(0xFFFFC857));
      await _montar(t, s, ParedPagina(key: UniqueKey(), cargar: () async => const []));
      await t.pump();
      expect(find.textContaining('Todavía no hay nadie'), findsOneWidget);
      await _montar(t, s, ParedPagina(key: UniqueKey(), cargar: () async => throw const SinConexion()));
      await t.pump();
      expect(find.textContaining('No hay conexión'), findsOneWidget);
      expect(find.text('Reintentar'), findsOneWidget);
    });
  });

  group('Letra con efectos', () {
    const lineas = [(0, 'Primera línea'), (3000, 'Segunda línea que suena'), (6000, ''), (9000, 'Última')];

    test('qué verso suena y cómo entran sus piezas', () {
      expect(EscenaLetra.indice(lineas, -10), -1);
      expect(EscenaLetra.indice(lineas, 3500), 1);
      expect(EscenaLetra.indice(lineas, 99999), 3);
      expect(EscenaLetra.pieza(0, 0, 4), 0);
      expect(EscenaLetra.pieza(1, 3, 4), 1);
      expect(EscenaLetra.pieza(0.3, 0, 4), greaterThan(EscenaLetra.pieza(0.3, 3, 4)));
      expect(EscenaLetra.neon(1), 1);
      expect(EscenaLetra.neon(0), 0);
      expect(EscenaLetra.entrada('ola', 'a b c d').inMilliseconds, greaterThan(EscenaLetra.entrada('resplandor', 'a').inMilliseconds));
      expect(EscenaLetra.palabras('  hola   mundo '), ['hola', 'mundo']);
    });

    test('el estilo elegido se recuerda', () async {
      expect(await EscenaLetra.estiloGuardado(), 'resplandor');
      await EscenaLetra.guardarEstilo('cine');
      expect(await EscenaLetra.estiloGuardado(), 'cine');
    });

    for (final estilo in Cosmeticos.estilosLetra) {
      testWidgets('estilo $estilo: el verso actual grande, el anterior y el siguiente a la vista', (t) async {
        await t.pumpWidget(MaterialApp(
          home: Scaffold(
            body: EscenaLetraVista(lineas: lineas, actual: 1, estilo: estilo, paleta: PaletaPortada.neutra),
          ),
        ));
        await t.pump(const Duration(milliseconds: 100));
        await t.pump(const Duration(seconds: 2));
        expect(t.takeException(), isNull);
        expect(find.bySemanticsLabel('Segunda línea que suena'), findsOneWidget);
        // el texto aparece dos veces: el relleno y su contorno oscuro debajo (este va sin semántica)
        expect(find.text('Primera línea'), findsWidgets);
        expect(find.text('♪'), findsWidgets, reason: 'el siguiente es un tramo sin letra');
        // cambia de verso: la entrada vuelve a empezar sin errores
        await t.pumpWidget(MaterialApp(
          home: Scaffold(
            body: EscenaLetraVista(lineas: lineas, actual: 3, estilo: estilo, paleta: PaletaPortada.neutra),
          ),
        ));
        await t.pump(const Duration(milliseconds: 60));
        await t.pump(const Duration(seconds: 2));
        expect(find.bySemanticsLabel('Última'), findsOneWidget);
        expect(t.takeException(), isNull);
      });
    }

    testWidgets('con «Quitar animaciones» el verso sale ya puesto', (t) async {
      await t.pumpWidget(const MaterialApp(
        home: MediaQuery(
          data: MediaQueryData(disableAnimations: true),
          child: Scaffold(
            body: VersoEscena(texto: 'Quieto', estilo: 'resplandor', paleta: PaletaPortada.neutra, tamano: 40),
          ),
        ),
      ));
      await t.pump();
      final op = t.widget<Opacity>(find.ancestor(of: find.text('Quieto'), matching: find.byType(Opacity)).first);
      expect(op.opacity, 1);
      expect(t.hasRunningAnimations, isFalse);
    });

    testWidgets('el selector de estilo cambia al tocar', (t) async {
      var elegido = '';
      await t.pumpWidget(MaterialApp(
        home: Scaffold(body: SelectorEstiloLetra(estilo: 'resplandor', alElegir: (e) => elegido = e)),
      ));
      for (final n in ['Resplandor', 'Ola', 'Neón', 'Cine']) {
        expect(find.text(n), findsOneWidget);
      }
      await t.tap(find.text('Neón'));
      expect(elegido, 'neon');
    });
  });
}
