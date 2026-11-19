// La mesa del Mezclador y la tarjeta «Tu mes pasado»: sin red ni media_kit
// (el reproductor y la coleccion son dobles).
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/mezcla_dj.dart';
import 'package:caudal/nucleo/ritmo.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/comunes.dart';
import 'package:caudal/ui/paginas/mezclador_ajustes.dart';
import 'package:caudal/ui/paginas/mezclador_pagina.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:caudal/ui/tu_mes_pasado.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Json pista(int i, {int dur = 200}) => {
      'tipo': 'pista', 'clave': 'yt:id$i', 'video_id': 'id$i', 'titulo': 'Canción $i',
      'artista': 'Artista $i', 'miniatura': '', 'duracion': dur,
    };

class _ReproductorFalso extends ChangeNotifier implements Reproductor {
  @override
  Json? actual;
  @override
  List<Json> proximas = [];
  @override
  List<Json> get siguientesDeContexto => [];

  List<PasoMezcla>? setReproducido;
  String? tituloSet;
  (PasoMezcla, Json)? probado;

  @override
  bool get puedeEstirarTiempo => true;
  @override
  bool get puedeFiltrar => true;
  @override
  bool get puedeEco => false;

  @override
  Future<void> reproducirSet(List<PasoMezcla> pasos, {String titulo = 'Tu mezcla', Duration desde = Duration.zero,
      Map<String, AnalisisRitmo> ritmo = const {}}) async {
    setReproducido = pasos;
    tituloSet = titulo;
  }

  @override
  Future<void> probarPaso(PasoMezcla paso, Json siguiente, {Map<String, AnalisisRitmo> ritmo = const {}}) async =>
      probado = (paso, siguiente);

  @override
  Future<void> dispose() async => super.dispose();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ColeccionFalsa extends ChangeNotifier implements Coleccion {
  final estados = <String, Object?>{};
  final listasCreadas = <String, List<Json>>{};
  List<Json> gustan = [];

  @override
  Future<dynamic> estado(String clave) async => estados[clave];

  @override
  Future<void> guardarEstado(String clave, Object? valor) async => estados[clave] = valor;

  @override
  Future<List<Json>> listaMeGusta() async => gustan;

  @override
  Future<List<Json>> listas() async => [
        for (final (i, e) in listasCreadas.entries.indexed)
          {'id': i + 1, 'nombre': e.key, 'n': e.value.length}
      ];

  @override
  Future<int> crearLista(String nombre, {String descripcion = ''}) async {
    listasCreadas[nombre] = [];
    return listasCreadas.length;
  }

  @override
  Future<int> agregarALista(int id, List<Json> nuevas) async {
    listasCreadas.values.elementAt(id - 1).addAll(nuevas);
    return nuevas.length;
  }

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

late _ReproductorFalso _r;
late _ColeccionFalsa _col;
late Servicios _s;

Future<void> _montar(WidgetTester t, Widget hijo, {Size tamano = const Size(411, 891)}) async {
  SharedPreferences.setMockInitialValues({});
  _r = _ReproductorFalso();
  _col = _ColeccionFalsa();
  _s = Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
    ajustes: await Ajustes.cargar('prueba'),
    coleccion: _col,
    reproductor: _r,
    streams: _StreamsFalsos(),
    descargas: _DescargasFalsas(),
    cerrarSesion: () async {},
  );
  t.view.physicalSize = tamano * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(
    s: _s,
    child: MaterialApp(
      theme: temaCaudal().copyWith(splashFactory: NoSplash.splashFactory),
      scaffoldMessengerKey: _s.mensajero,
      home: hijo,
    ),
  ));
  await t.pump(const Duration(milliseconds: 300));
}

void main() {
  group('la mesa del Mezclador', () {
    testWidgets('vacia: explica como funciona y ofrece accesos directos, sin barra de reproducir', (t) async {
      await _montar(t, const MezcladorPagina());
      expect(find.text('Tu mesa está vacía'), findsOneWidget);
      expect(find.text('Cómo funciona'), findsOneWidget);
      expect(find.text('Añade canciones'), findsOneWidget);
      expect(find.text('Desde tu cola', skipOffstage: false), findsOneWidget);
      expect(find.text('Desde Tus me gusta', skipOffstage: false), findsOneWidget);
      expect(find.text('Mezclar una lista como un DJ', skipOffstage: false), findsOneWidget);
      expect(find.text('Reproducir la mezcla'), findsNothing);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });

    testWidgets('con canciones: filas, tiempo total y un cambio entre cada dos', (t) async {
      await _montar(t, MezcladorPagina(inicial: [pista(1), pista(2), pista(3)]));
      expect(find.text('Canción 1'), findsOneWidget);
      expect(find.text('Canción 3', skipOffstage: false), findsOneWidget);
      expect(find.textContaining('3 canciones · '), findsOneWidget);
      expect(find.textContaining('la siguiente entra a 8 s del final'), findsNWidgets(2));
      expect(find.text('Reproducir la mezcla'), findsOneWidget);
      // con un set armado, el «como funciona» queda plegado
      expect(find.text('Cómo funciona'), findsNothing);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });

    testWidgets('abrir un cambio deja ajustarlo; el cambio de graves se refleja en el resumen', (t) async {
      await _montar(t, MezcladorPagina(inicial: [pista(1), pista(2)]));
      expect(find.textContaining('Cambio de graves de 8 s'), findsOneWidget);
      await t.tap(find.textContaining('la siguiente entra a 8 s del final'));
      await t.pumpAndSettle();
      // lo primero: estilos rapidos y probar; lo avanzado esta plegado
      expect(find.text('Elige un estilo'.toUpperCase()), findsOneWidget);
      expect(find.text('Probar este cambio', skipOffstage: false), findsOneWidget);
      expect(find.text('La siguiente empieza cuando falten'), findsNothing);
      await t.ensureVisible(find.text('Ajustes finos', skipOffstage: false));
      await t.pumpAndSettle();
      await t.tap(find.text('Ajustes finos'));
      await t.pumpAndSettle();
      expect(find.text('La siguiente empieza cuando falten', skipOffstage: false), findsOneWidget);
      expect(find.text('Las dos suenan juntas durante', skipOffstage: false), findsOneWidget);
      await t.tap(find.text('Fundido'));
      await t.pumpAndSettle();
      expect(find.textContaining('Cambio de graves de'), findsNothing);
      expect(find.textContaining('Fundido de 8 s'), findsOneWidget);
      // el eco no esta en el motor del telefono: no se puede elegir y se explica
      expect(find.text('El eco no está disponible en el motor de este teléfono.', skipOffstage: false), findsOneWidget);
      // mover el deslizador de "cuando entra" cambia el resumen
      final desliz = find.byType(Slider).first;
      await t.ensureVisible(desliz);
      await t.pumpAndSettle();
      await t.drag(desliz, const Offset(120, 0));
      await t.pumpAndSettle();
      expect(find.textContaining('la siguiente entra a 8 s del final'), findsNothing);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });

    testWidgets('«Reproducir la mezcla» manda el set entero al reproductor', (t) async {
      await _montar(t, MezcladorPagina(inicial: [pista(1), pista(2), pista(3)]));
      await t.tap(find.text('Reproducir la mezcla'));
      await t.pump();
      expect(_r.setReproducido!.length, 3);
      expect(_r.setReproducido!.map((p) => p.pista['clave']), ['yt:id1', 'yt:id2', 'yt:id3']);
      expect(_r.tituloSet, 'Tu mezcla');
    });

    testWidgets('«Probar este cambio» pide probar ese paso con la cancion siguiente', (t) async {
      await _montar(t, MezcladorPagina(inicial: [pista(1), pista(2), pista(3)]));
      await t.tap(find.textContaining('la siguiente entra a 8 s del final').first);
      await t.pumpAndSettle();
      await t.ensureVisible(find.text('Probar este cambio'));
      await t.pumpAndSettle();
      await t.tap(find.text('Probar este cambio'));
      await t.pump();
      expect(_r.probado!.$1.pista['clave'], 'yt:id1');
      expect(_r.probado!.$2['clave'], 'yt:id2');
    });

    testWidgets('quitar una cancion, con deshacer', (t) async {
      await _montar(t, MezcladorPagina(inicial: [pista(1), pista(2), pista(3)]));
      await t.tap(find.byTooltip('Quitar de la mezcla').at(1));
      await t.pumpAndSettle();
      expect(find.text('Canción 2'), findsNothing);
      expect(find.textContaining('2 canciones · '), findsOneWidget);
      await t.tap(find.text('Deshacer'));
      await t.pumpAndSettle();
      expect(find.text('Canción 2'), findsOneWidget);
      expect(find.textContaining('3 canciones · '), findsOneWidget);
    });

    testWidgets('añadir canciones de la cola', (t) async {
      await _montar(t, const MezcladorPagina());
      _r.actual = pista(7);
      _r.proximas = [pista(8), pista(9)];
      await t.tap(find.text('Desde tu cola'));
      await t.pumpAndSettle();
      expect(find.text('Canción 7'), findsOneWidget);
      expect(find.text('Canción 9'), findsOneWidget);
      await t.tap(find.text('Elegir todas'));
      await t.pump();
      await t.tap(find.text('Añadir 3'));
      await t.pumpAndSettle();
      expect(find.textContaining('3 canciones · '), findsOneWidget);
      expect(find.text('Canción 8'), findsOneWidget);
    });

    testWidgets('guardar con nombre y volver a abrirla desde «Mis mezclas»', (t) async {
      await _montar(t, MezcladorPagina(inicial: [pista(1), pista(2)]));
      await t.tap(find.text('Guardar'));
      await t.pumpAndSettle();
      await t.enterText(find.byType(TextField), 'Viernes de fiesta');
      await t.tap(find.text('Guardar').last);
      await t.pumpAndSettle();
      final guardadas = await Mezclas.leer(_col);
      expect(guardadas.map((m) => m.nombre), ['Viernes de fiesta']);
      expect(guardadas.single.pasos.length, 2);

      await t.tap(find.byTooltip('Mis mezclas'));
      await t.pumpAndSettle();
      expect(find.text('Viernes de fiesta'), findsWidgets);
      expect(find.textContaining('2 canciones · '), findsWidgets);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });

    testWidgets('con la letra grande y en pantalla chica no se desborda', (t) async {
      await _montar(t, MezcladorPagina(inicial: [pista(1), pista(2)]), tamano: const Size(320, 568));
      await t.ensureVisible(find.textContaining('la siguiente entra a 8 s del final'));
      await t.pumpAndSettle();
      await t.tap(find.textContaining('la siguiente entra a 8 s del final'));
      await t.pumpAndSettle();
      await t.ensureVisible(find.text('Ajustes finos', skipOffstage: false));
      await t.pumpAndSettle();
      await t.tap(find.text('Ajustes finos'));
      await t.pumpAndSettle();
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });

    testWidgets('el «?» reabre el como funciona y «Entendido» lo pliega', (t) async {
      await _montar(t, MezcladorPagina(inicial: [pista(1), pista(2)]));
      expect(find.text('Cómo funciona'), findsNothing);
      await t.tap(find.byTooltip('Cómo funciona'));
      await t.pumpAndSettle();
      expect(find.text('Cómo funciona'), findsOneWidget);
      expect(find.text('Mézclalas'), findsOneWidget);
      await t.tap(find.text('Entendido'));
      await t.pumpAndSettle();
      expect(find.text('Cómo funciona'), findsNothing);
    });

    testWidgets('un estilo rapido cambia el cambio (Corte rápido: 4 s sin tempo)', (t) async {
      await _montar(t, MezcladorPagina(inicial: [pista(1), pista(2)]));
      await t.tap(find.textContaining('la siguiente entra a 8 s del final'));
      await t.pumpAndSettle();
      await t.tap(find.text('Corte rápido'));
      await t.pumpAndSettle();
      expect(find.textContaining('Fundido de 4 s · la siguiente entra a 4 s del final'), findsOneWidget);
      await t.tap(find.text('Club'));
      await t.pumpAndSettle();
      expect(find.textContaining('Cambio de graves de 14 s'), findsOneWidget);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });

    testWidgets('sin tempo: ofrece «Detectar ritmo» y avisa si no se pudo', (t) async {
      await _montar(t, MezcladorPagina(inicial: [pista(1), pista(2)]));
      expect(find.text('Detectar ritmo'), findsNWidgets(2));
      await t.tap(find.text('Detectar ritmo').first);
      await t.pump(const Duration(milliseconds: 300));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.textContaining('No se pudo saber el ritmo de 1 canción'), findsOneWidget);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });

    testWidgets('una lista enorme (600 canciones) se monta perezosa y sin limite', (t) async {
      await _montar(t, MezcladorPagina(inicial: [for (var i = 1; i <= 600; i++) pista(i)]));
      expect(find.textContaining('600 canciones · '), findsOneWidget);
      expect(find.text('Canción 1'), findsOneWidget);
      // solo se construyen las que se ven
      expect(find.byType(Portada, skipOffstage: false).evaluate().length, lessThan(40));
      await t.tap(find.text('Reproducir la mezcla'));
      await t.pump();
      expect(_r.setReproducido!.length, 600);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });
  });

  group('ajustes de la Mezcla DJ', () {
    testWidgets('encender, cambiar la duracion y los graves se guarda al momento', (t) async {
      await _montar(t, const Scaffold(body: Padding(padding: EdgeInsets.all(16), child: MezclaDjControles())));
      expect(_s.ajustes.sino('mezcla_dj'), isFalse);
      expect(find.text('Duración del cambio'), findsNothing);
      await t.tap(find.text('Mezcla DJ'));
      await t.pumpAndSettle();
      expect(_s.ajustes.sino('mezcla_dj'), isTrue);
      expect(find.text('Duración del cambio'), findsOneWidget);
      expect(find.text('8 s'), findsOneWidget);
      await t.drag(find.byType(Slider), const Offset(400, 0));
      await t.pumpAndSettle();
      expect(_s.ajustes.entero('mezcla_dj_seg'), 16);
      await t.drag(find.byType(Slider), const Offset(-800, 0));
      await t.pumpAndSettle();
      expect(_s.ajustes.entero('mezcla_dj_seg'), 4);
      expect(_s.ajustes.sino('mezcla_dj_graves'), isTrue);
      await t.tap(find.text('Cambio de graves'));
      await t.pumpAndSettle();
      expect(_s.ajustes.sino('mezcla_dj_graves'), isFalse);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });
  });

  group('«Tu mes pasado»', () {
    final mix = <String, dynamic>{
      'tipo': 'mix', 'id': 'mes_pasado_2026_10', 'titulo': 'Tu mes pasado',
      'subtitulo': 'Lo que más escuchaste en octubre', 'nombre_lista': 'Lo más escuchado en octubre',
      'miniaturas': <String>[], 'color': 0xFFE8795A, 'total': 3,
      'pistas': [pista(1), pista(2), pista(3)],
    };

    testWidgets('se ve y se guarda como lista real con un toque', (t) async {
      await _montar(t, Scaffold(body: ListView(children: [TarjetaMesPasado(mix: mix)])));
      expect(find.text('Lo más escuchado en octubre'), findsOneWidget);
      expect(find.text('3 canciones'), findsOneWidget);
      expect(find.text('Guardar como lista'), findsOneWidget);
      await t.tap(find.text('Guardar como lista'));
      await t.pumpAndSettle();
      expect(_col.listasCreadas.keys, ['Lo más escuchado en octubre']);
      expect(_col.listasCreadas.values.single.length, 3);
      expect(find.text('Guardada · ver la lista'), findsOneWidget);
      await t.pump(const Duration(seconds: 6));
      expect(t.takeException(), isNull);
    });

    testWidgets('si ya estaba guardada, el boton lo dice y no la duplica', (t) async {
      SharedPreferences.setMockInitialValues({});
      await _montar(t, Scaffold(body: ListView(children: [TarjetaMesPasado(mix: mix)])));
      _col.listasCreadas['Lo más escuchado en octubre'] = [pista(1)];
      // al montar de nuevo la tarjeta busca la lista por su nombre
      await t.pumpWidget(Caudal(
        s: _s,
        child: MaterialApp(
          theme: temaCaudal().copyWith(splashFactory: NoSplash.splashFactory),
          scaffoldMessengerKey: _s.mensajero,
          home: Scaffold(body: ListView(children: [TarjetaMesPasado(key: UniqueKey(), mix: mix)])),
        ),
      ));
      await t.pumpAndSettle();
      expect(find.text('Guardada · ver la lista'), findsOneWidget);
      expect(_col.listasCreadas.length, 1);
    });
  });
}
