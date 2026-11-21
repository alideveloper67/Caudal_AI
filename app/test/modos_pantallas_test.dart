import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/eq_adaptable.dart';
import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/nucleo/novedades_para_ti.dart';
import 'package:caudal/nucleo/premium_letras.dart';
import 'package:caudal/nucleo/resumen_semanal.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/eq_adaptable_control.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/paginas/modo_auto_pagina.dart';
import 'package:caudal/ui/paginas/modos_escucha_pagina.dart';
import 'package:caudal/ui/premium/eq_adaptable_pagina.dart';
import 'package:caudal/ui/premium/que_cancion_era_pagina.dart';
import 'package:caudal/ui/premium/resumen_semanal_pagina.dart';
import 'package:caudal/ui/premium/tarjetas_del_dia.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Json _p(String t, String a, {String? genero}) => {
      'clave': 'yt:$t',
      'video_id': 'v$t',
      'titulo': t,
      'artista': a,
      'artistas': [
        {'id': 'id_$a', 'nombre': a}
      ],
      'miniatura': '',
      'duracion': 200,
      'genero': ?genero,
    };

class _Repro extends ChangeNotifier implements Reproductor {
  _Repro(this.ajustes, this.coleccion);
  @override
  final Ajustes ajustes;
  @override
  final Coleccion coleccion;
  @override
  Json? actual;
  @override
  Json? contexto;
  @override
  EstadoRepro estado = EstadoRepro.parado;
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(Duration.zero);
  int alternados = 0, siguientes = 0, anteriores = 0, aplicados = 0;
  int? minutosTemporizador;
  List<Json> sonadas = [];

  @override
  Future<void> alternar() async => alternados++;
  @override
  Future<void> siguiente({bool automatico = false}) async {
    siguientes++;
  }

  @override
  Future<void> anterior() async => anteriores++;
  @override
  Future<void> aplicarSonido() async => aplicados++;
  @override
  int? get restanteApagado => minutosTemporizador == null ? null : minutosTemporizador! * 60;
  @override
  void programarApagado({int? minutos, bool alTerminar = false}) {
    minutosTemporizador = minutos;
    notifyListeners();
  }

  @override
  Future<void> reproducirLista(List<Json> pistas,
      {int inicio = 0, Json? contexto, bool? aleatorio, String? modo, Duration desde = Duration.zero}) async {
    sonadas = pistas;
    actual = pistas[inicio];
    notifyListeners();
  }

  @override
  Future<void> reproducirPista(Json pista, {Json? contexto, String? modo, bool conRadio = true}) async {
    sonadas = [pista];
    actual = pista;
    notifyListeners();
  }

  @override
  Future<void> dispose() async => super.dispose();
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Col extends ChangeNotifier implements Coleccion {
  final datos = <String, Object?>{};
  List<Json> gustan = [];
  @override
  Future<dynamic> estado(String clave) async => datos[clave];
  @override
  Future<void> guardarEstado(String clave, Object? valor) async => datos[clave] = valor;
  @override
  bool meGusta(String? clave) => false;
  @override
  Future<List<Json>> listaMeGusta() async => gustan;
  @override
  Future<List<Json>> meGustaRecientes(int n) async => [];
  @override
  Future<List<Json>> listas() async => [];
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Streams implements Streams {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Descargas extends ChangeNotifier implements GestorDescargas {
  @override
  List<Descarga> get lista => const [];
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Mundo {
  late Ajustes ajustes;
  late _Col col;
  late _Repro r;
  late Servicios s;
}

Future<_Mundo> _mundo() async {
  SharedPreferences.setMockInitialValues({});
  final m = _Mundo();
  m.ajustes = await Ajustes.cargar('prueba');
  m.col = _Col();
  m.r = _Repro(m.ajustes, m.col);
  m.s = Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
    ajustes: m.ajustes,
    coleccion: m.col,
    reproductor: m.r,
    streams: _Streams(),
    descargas: _Descargas(),
    cerrarSesion: () async {},
  );
  return m;
}

/// Monta [pagina] a [tam] con el texto a [escala] y devuelve lo que se rompió (desbordes incluidos).
Future<List<String>> _montar(WidgetTester t, _Mundo m, Widget pagina,
    {Size tam = const Size(320, 568), double escala = 1.0, Future<void> Function(WidgetTester)? despues}) async {
  final errores = <String>[];
  final anterior = FlutterError.onError;
  FlutterError.onError = (d) => errores.add(d.exceptionAsString().split('\n').first);
  t.view.physicalSize = tam * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(
    s: m.s,
    child: MaterialApp(
      theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory),
      builder: (ctx, hijo) => MediaQuery(
        data: MediaQuery.of(ctx).copyWith(textScaler: TextScaler.linear(escala)),
        child: hijo!,
      ),
      home: pagina,
    ),
  ));
  await t.pump(const Duration(milliseconds: 500));
  try {
    if (despues != null) await despues(t);
  } catch (_) {
    FlutterError.onError = anterior; // que un expect() fallido no deje el binding a medias
    rethrow;
  }
  await t.pump(const Duration(milliseconds: 500));
  final ex = t.takeException();
  if (ex != null) errores.add('$ex'.split('\n').first);
  await t.pumpWidget(const SizedBox());
  await t.pump(const Duration(seconds: 1));
  t.takeException();
  FlutterError.onError = anterior;
  return errores;
}

void main() {
  setUp(() => esPremiumLetras = () => true);
  tearDown(() => esPremiumLetras = () => false);

  group('Modo auto', () {
    testWidgets('botones grandes: pausa, siguiente y anterior responden', (t) async {
      final m = await _mundo();
      m.r.actual = _p('Una canción con un título bastante largo para probar', 'Un artista con nombre largo');
      m.r.estado = EstadoRepro.sonando;
      m.r.duracion.value = const Duration(minutes: 3);
      m.r.posicion.value = const Duration(seconds: 65);
      final e = await _montar(t, m, const ModoAutoPagina(), despues: (t) async {
        expect(find.text('Pausa'), findsOneWidget);
        expect(find.text('Faltan 1:55'), findsOneWidget);
        // los botones son enormes: al menos 96 px de alto para el principal
        final play = tester(t, 'Pausa');
        expect(play.height, greaterThanOrEqualTo(96));
        await t.tap(find.text('Pausa'));
        await t.tap(find.text('Siguiente'));
        await t.tap(find.text('Anterior'));
        await t.pump();
      });
      expect(e, isEmpty);
      expect((m.r.alternados, m.r.siguientes, m.r.anteriores), (1, 1, 1));
    });

    testWidgets('sin nada sonando ofrece poner los me gusta', (t) async {
      final m = await _mundo();
      m.col.gustan = [_p('a', 'x'), _p('b', 'y')];
      final e = await _montar(t, m, const ModoAutoPagina(), despues: (t) async {
        expect(find.text('No hay nada sonando'), findsOneWidget);
        await t.tap(find.text('Poner mis me gusta'));
        await t.pump(const Duration(milliseconds: 200));
      });
      expect(e, isEmpty);
      expect(m.r.sonadas.length, 2);
    });

    for (final (nombre, tam, escala) in [
      ('320x568', const Size(320, 568), 1.0),
      ('320x568 con letra al 160 %', const Size(320, 568), 1.6),
      ('horizontal 568x320', const Size(568, 320), 1.0),
      ('tableta 800x1200', const Size(800, 1200), 1.0),
    ]) {
      testWidgets('sin desbordes: $nombre', (t) async {
        final m = await _mundo();
        m.r.actual = _p('Título larguísimo que ocupa varias líneas en una pantalla muy pequeña', 'Artista Con Nombre Largo Y Más');
        m.r.estado = EstadoRepro.pausa;
        final e = await _montar(t, m, const ModoAutoPagina(), tam: tam, escala: escala);
        expect(e, isEmpty);
      });
    }
  });

  group('Modos de escucha', () {
    for (final escala in [1.0, 1.4]) {
      testWidgets('320x568 sin desbordes (letra x$escala)', (t) async {
        final m = await _mundo();
        final e = await _montar(t, m, const ModosEscuchaPagina(), escala: escala, despues: (t) async {
          expect(find.text('Concentración'), findsOneWidget);
          await t.drag(find.byType(ListView), const Offset(0, -400));
          await t.pump();
          expect(find.text('Dormir'), findsOneWidget);
          await t.drag(find.byType(ListView), const Offset(0, -1200));
          await t.pump();
          expect(find.text('Ejercicio'), findsOneWidget);
          await t.tap(find.text('Intenso'));
          await t.pump();
          expect(find.textContaining('140 a 185'), findsOneWidget);
        });
        expect(e, isEmpty);
      });
    }

    testWidgets('Dormir: solo el temporizador a lo que suena, con la bajada suave encendida', (t) async {
      final m = await _mundo();
      await m.ajustes.poner('apagado_suave', false);
      m.r.actual = _p('a', 'b');
      final e = await _montar(t, m, const ModosEscuchaPagina(), despues: (t) async {
        await t.scrollUntilVisible(find.text('1 h'), 200, scrollable: find.byType(Scrollable).first);
        await t.ensureVisible(find.text('1 h'));
        await t.pump();
        await t.tap(find.text('1 h'));
        await t.pump();
        await t.scrollUntilVisible(find.text('Solo poner el temporizador a lo que suena'), 200,
            scrollable: find.byType(Scrollable).first);
        await t.ensureVisible(find.text('Solo poner el temporizador a lo que suena'));
        await t.pump();
        await t.tap(find.text('Solo poner el temporizador a lo que suena'));
        await t.pump(const Duration(milliseconds: 300));
        expect(find.textContaining('Se apaga en'), findsOneWidget);
      });
      expect(e, isEmpty);
      expect(m.r.minutosTemporizador, 60);
      expect(m.ajustes.sino('apagado_suave'), isTrue);
    });
  });

  group('¿Qué canción era?', () {
    final hoy = DateTime(2026, 11, 19, 15);
    final h = [
      Escucha(_p('Despechá', 'Rosalía'), DateTime(2026, 11, 18, 21, 5)),
      Escucha(_p('Corazón', 'Alguien'), DateTime(2026, 11, 17, 9)),
    ];

    testWidgets('busca por día y por texto y se puede reproducir', (t) async {
      final m = await _mundo();
      final e = await _montar(t, m, QueCancionEraPagina(historial: h, ahora: hoy), despues: (t) async {
        expect(find.text('Escribe lo que recuerdas'), findsOneWidget);
        await t.enterText(find.byType(TextField), 'ayer');
        await t.pump(const Duration(milliseconds: 400));
        expect(find.text('Despechá'), findsOneWidget);
        expect(find.text('Corazón'), findsNothing);
        expect(find.textContaining('9:05 p. m.'), findsOneWidget);
        await t.enterText(find.byType(TextField), 'el martes corazon');
        await t.pump(const Duration(milliseconds: 400));
        expect(find.text('Corazón'), findsOneWidget);
        await t.enterText(find.byType(TextField), 'nada de esto');
        await t.pump(const Duration(milliseconds: 400));
        expect(find.text('No encontré nada'), findsOneWidget);
        // un atajo
        await t.tap(find.text('Ayer'));
        await t.pump(const Duration(milliseconds: 100));
        expect(find.text('Despechá'), findsOneWidget);
        await t.tap(find.text('Despechá'));
        await t.pump(const Duration(milliseconds: 200));
      });
      expect(e, isEmpty);
    });

    testWidgets('por letra con la letra guardada', (t) async {
      final m = await _mundo();
      final letras = {
        'yt:Despechá': {'lineas': const [], 'texto': 'Quiero bailar contigo toda la noche'}
      };
      final e = await _montar(t, m, QueCancionEraPagina(historial: h, letras: letras, ahora: hoy), despues: (t) async {
        await t.enterText(find.byType(TextField), 'decía quiero bailar');
        await t.pump(const Duration(milliseconds: 400));
        expect(find.text('Despechá'), findsOneWidget);
        expect(find.textContaining('Letra: «Quiero bailar contigo'), findsOneWidget);
      });
      expect(e, isEmpty);
    });

    for (final escala in [1.0, 1.5]) {
      testWidgets('320x568 sin desbordes (letra x$escala)', (t) async {
        final m = await _mundo();
        final e = await _montar(t, m, QueCancionEraPagina(historial: h, ahora: hoy), escala: escala, despues: (t) async {
          await t.enterText(find.byType(TextField), 'ayer');
          await t.pump(const Duration(milliseconds: 400));
        });
        expect(e, isEmpty);
      });
    }

    testWidgets('quien no es donador ve el candado y no puede buscar', (t) async {
      esPremiumLetras = () => false;
      final m = await _mundo();
      final e = await _montar(t, m, QueCancionEraPagina(historial: h, ahora: hoy), despues: (t) async {
        expect(find.byType(TextField), findsNothing);
        expect(find.text('Donar aquí'), findsOneWidget);
      });
      expect(e, isEmpty);
    });
  });

  group('Ecualizador adaptable', () {
    testWidgets('elige el perfil a mano si no se detecta, y se guarda', (t) async {
      final m = await _mundo();
      m.r.actual = _p('Despechá', 'Rosalía', genero: 'pop');
      final c = ControlEqAdaptable.prueba(donador: () => true);
      await c.enlazar(m.r, escuchar: false);
      final e = await _montar(t, m, EqAdaptablePagina(control: c), despues: (t) async {
        expect(find.textContaining('no dice por dónde sale'), findsOneWidget);
        expect(find.text('Perfil activo:'), findsOneWidget);
        await t.ensureVisible(find.text('Bluetooth').first);
        await t.pump();
        await t.tap(find.text('Bluetooth').first);
        await t.pump();
        expect(c.perfiles.manual, SalidaAudio.bluetooth);
        // un ajuste para esa salida
        // el desplegable de Bluetooth (el tercero): se elige un ajuste
        t.widget<DropdownButton<String>>(find.byType(DropdownButton<String>).at(2)).onChanged!('Graves potentes');
        await t.pump(const Duration(milliseconds: 400));
        expect(c.perfiles.salidas['bluetooth'], 'Graves potentes');
        await t.drag(find.byType(Scrollable).first, const Offset(0, 2000)); // de vuelta arriba
        await t.pump(const Duration(milliseconds: 300));
        expect(find.textContaining('Suena con «Graves potentes»'), findsOneWidget);
        expect(m.ajustes.texto('eq_preset'), 'Graves potentes');
      });
      expect(e, isEmpty);
      await c.soltar();
    });

    for (final escala in [1.0, 1.4]) {
      testWidgets('320x568 sin desbordes (letra x$escala)', (t) async {
        final m = await _mundo();
        m.r.actual = _p('Tema muy largo con un nombre que no cabe en una sola línea', 'Un artista con nombre largo', genero: 'rock');
        final c = ControlEqAdaptable.prueba(donador: () => true);
        await c.enlazar(m.r, escuchar: false);
        await c.cambiar((p) {
          p.ponerArtista('id:id_Un artista con nombre largo', 'Un artista con nombre largo', 'Voces');
          p.ponerGenero('rock', 'Rock');
        });
        final e = await _montar(t, m, EqAdaptablePagina(control: c), escala: escala, despues: (t) async {
          await t.drag(find.byType(ListView), const Offset(0, -600));
          await t.pump();
        });
        expect(e, isEmpty);
        await c.soltar();
      });
    }

    testWidgets('sin ser donador, candado', (t) async {
      esPremiumLetras = () => false;
      final m = await _mundo();
      final e = await _montar(t, m, EqAdaptablePagina(control: ControlEqAdaptable.prueba()), despues: (t) async {
        expect(find.text('Donar aquí'), findsOneWidget);
      });
      expect(e, isEmpty);
    });
  });

  group('Tarjeta del resumen semanal', () {
    final domingo = DateTime(2026, 11, 22, 20);
    List<Escucha> historial() => [
          for (var i = 0; i < 14; i++)
            Escucha({..._p('Tema ${i % 6} con título largo', 'Artista ${i % 3}'), 'duracion': 200}, DateTime(2026, 11, 16 + i % 7, 8 + i)),
        ];

    for (final (tam, escala) in [(const Size(320, 568), 1.0), (const Size(320, 568), 1.5), (const Size(412, 915), 1.0)]) {
      testWidgets('página ${tam.width.toInt()}x${tam.height.toInt()} (letra x$escala) sin desbordes', (t) async {
        final m = await _mundo();
        final e = await _montar(t, m, ResumenSemanalPagina(historial: historial(), ahora: domingo), tam: tam, escala: escala,
            despues: (t) async {
          expect(find.text('Mi semana en Caudal'.toUpperCase()), findsOneWidget);
          expect(find.text('Compartir'), findsOneWidget);
          expect(find.text('Guardar'), findsOneWidget);
          expect(find.textContaining('16 – 22 nov'), findsOneWidget);
        });
        expect(e, isEmpty);
      });
    }

    testWidgets('con muy pocas escuchas lo explica; sin ser donador, candado', (t) async {
      final m = await _mundo();
      var e = await _montar(t, m, ResumenSemanalPagina(historial: const [], ahora: domingo), despues: (t) async {
        expect(find.text('Todavía es pronto para tu semana'), findsOneWidget);
      });
      expect(e, isEmpty);
      esPremiumLetras = () => false;
      e = await _montar(t, m, ResumenSemanalPagina(historial: historial(), ahora: domingo), despues: (t) async {
        expect(find.text('Donar aquí'), findsOneWidget);
        expect(find.text('Compartir'), findsNothing);
      });
      expect(e, isEmpty);
    });
  });

  group('Tarjetas del día en Inicio', () {
    final novedades = NovedadesDelDia(dia: '2026-11-19', pistas: [for (var i = 0; i < 8; i++) _p('Nueva $i con título largo', 'Artista $i')]);
    final semana = ResumenSemanal(lunes: DateTime(2026, 11, 16), escuchas: 12, minutos: 95, diasConMusica: 4);

    testWidgets('donador: novedades y semana, cerrables; los accesos se deslizan', (t) async {
      final m = await _mundo();
      final e = await _montar(
          t,
          m,
          Scaffold(
              body: SingleChildScrollView(
                  child: TarjetasDelDia(cargarNovedades: (_) async => novedades, cargarSemana: (_) async => semana))),
          despues: (t) async {
        await t.pump(const Duration(milliseconds: 400)); // termina de crecer la tarjeta
        expect(find.text('Lo nuevo para ti'), findsOneWidget);
        expect(find.textContaining('8 canciones para hoy'), findsOneWidget);
        expect(find.text('Tu semana en Caudal'), findsOneWidget);
        expect(find.text('Modo auto'), findsOneWidget);
        // escuchar reproduce las 8
        await t.tap(find.text('Escuchar'));
        await t.pump(const Duration(milliseconds: 200));
        expect(m.r.sonadas.length, 8);
        // ver la lista completa
        await t.tap(find.text('Ver las 8'));
        await t.pump(const Duration(milliseconds: 500));
        expect(find.text('Lo nuevo para ti hoy'), findsOneWidget);
        await t.tapAt(const Offset(10, 10)); // cierra la hoja
        await t.pump(const Duration(milliseconds: 500));
        // cerrar hasta mañana
        await t.tap(find.byTooltip('Cerrar hasta mañana'));
        await t.pump(const Duration(milliseconds: 500));
        expect(find.text('Lo nuevo para ti'), findsNothing);
        expect(m.col.datos['novedades_para_ti'], isNotNull);
        await t.tap(find.byTooltip('Cerrar'));
        await t.pump(const Duration(milliseconds: 500));
        expect(find.text('Tu semana en Caudal'), findsNothing);
        expect(m.col.datos['resumen_semanal'], isNotNull);
      });
      expect(e, isEmpty);
    });

    for (final escala in [1.0, 1.5]) {
      testWidgets('320x568 sin desbordes (letra x$escala)', (t) async {
        final m = await _mundo();
        final e = await _montar(
            t,
            m,
            Scaffold(
                body: SingleChildScrollView(
                    child: TarjetasDelDia(cargarNovedades: (_) async => novedades, cargarSemana: (_) async => semana))),
            escala: escala);
        expect(e, isEmpty);
      });
    }

    testWidgets('sin ser donador no hay tarjetas, pero sí los accesos (con candado en lo exclusivo)', (t) async {
      esPremiumLetras = () => false;
      final m = await _mundo();
      var pidio = false;
      final e = await _montar(
          t,
          m,
          Scaffold(
              body: TarjetasDelDia(cargarNovedades: (_) async {
            pidio = true;
            return novedades;
          }, cargarSemana: (_) async => semana)),
          despues: (t) async {
        expect(find.text('Lo nuevo para ti'), findsNothing);
        expect(find.text('Modo auto'), findsOneWidget);
        // los accesos exclusivos están más allá: se desliza para verlos
        await t.drag(find.byType(ListView), const Offset(-400, 0));
        await t.pump(const Duration(milliseconds: 300));
        expect(find.byIcon(Icons.lock_outline_rounded), findsWidgets);
      });
      expect(e, isEmpty);
      expect(pidio, isFalse, reason: 'ni se pregunta si no hay beneficio');
    });

    testWidgets('si falla una carga, la otra se ve igual', (t) async {
      final m = await _mundo();
      final e = await _montar(
          t,
          m,
          Scaffold(
              body: TarjetasDelDia(cargarNovedades: (_) async => throw Exception('sin red'), cargarSemana: (_) async => semana)),
          despues: (t) async {
        expect(find.text('Tu semana en Caudal'), findsOneWidget);
        expect(find.text('Lo nuevo para ti'), findsNothing);
      });
      expect(e, isEmpty);
    });
  });
}

/// El tamaño que ocupa el botón que contiene [texto].
Size tester(WidgetTester t, String texto) {
  final boton = find.ancestor(of: find.text(texto), matching: find.byType(Material)).first;
  return t.getSize(boton);
}
