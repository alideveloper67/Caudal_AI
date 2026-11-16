// Recomendador afinado (parecidas, gustos, diversidad) y la pantalla
// «¿Qué artistas te gustan?».
import 'package:caudal/nucleo/gustos.dart';
import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/recomendador.dart';
import 'package:caudal/ui/paginas/gustos_pagina.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Map<String, dynamic> p(String vid, String artista, {String? titulo}) => {
      'tipo': 'pista', 'clave': 'yt:$vid', 'video_id': vid, 'titulo': titulo ?? 'Tema $vid',
      'artista': artista, 'artistas': [{'nombre': artista, 'id': 'id_$artista'}], 'duracion': 200,
      'miniatura': 'm$vid',
    };

List<String> ids(List<Map<String, dynamic>> l) => [for (final x in l) '${x['video_id']}'];

class _Sesion extends Sesion {
  _Sesion() : super('yo', 'token', 'r', DateTime.now().add(const Duration(hours: 1)));
  final enviados = <(String, String, Object?)>[];
  bool falla = false;
  dynamic filaPerfil;

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    if (metodo == 'GET') return filaPerfil;
    if (falla) throw const ErrorNube('Sin conexión.');
    enviados.add((metodo, ruta, cuerpo));
    return null;
  }
}

void main() {
  final hoy = DateTime(2026, 11, 14, 12);

  group('recomendador', () {
    // quien escucha cumbia
    final historial = [
      for (var i = 0; i < 6; i++) Escucha(p('cum0000000$i', 'Grupo Cumbia'), hoy.subtract(Duration(days: i + 1))),
    ];
    final g = Gusto.desde(historial, {}, ahora: hoy);
    final semilla = p('semilla0001', 'Grupo Cumbia', titulo: 'Amor de mi vida');

    List<(Map<String, dynamic>, double)> radio() => Recomendador.combinar([
          [
            p('rock0000001', 'Metallica', titulo: 'Master of Puppets'),
            for (var i = 0; i < 6; i++) p('cumb000000$i', i.isEven ? 'Cumbia Uno' : 'Cumbia Dos', titulo: 'Baila mi amor $i'),
            for (var i = 0; i < 4; i++) p('cumb100000$i', 'Cumbia Tres', titulo: 'Fiesta de la noche $i'),
          ],
        ]);

    test('una cumbia no trae rock: lo ajeno queda al final', () {
      final r = ids(Recomendador.ordenarSimilares(semilla, radio(), g, afines: {'id:id_Cumbia Uno'}));
      expect(r, contains('rock0000001'));
      expect(r.last, 'rock0000001');
    });

    test('lo saltado hoy y lo muy saltado se excluyen', () {
      final gs = Gusto.desde(historial, {
        'canciones': {'cumb0000001': 2},
        'hoy': {'dia': claveDia(hoy), 'ids': ['cumb0000002']},
      }, ahora: hoy);
      final r = ids(Recomendador.ordenarSimilares(semilla, radio(), gs));
      expect(r, isNot(contains('cumb0000001')));
      expect(r, isNot(contains('cumb0000002')));
      // otro día, lo saltado «hoy» ya no cuenta
      final manana = Gusto.desde(historial, {
        'hoy': {'dia': '2020-01-01', 'ids': ['cumb0000002']},
      }, ahora: hoy);
      expect(manana.saltadasHoy, isEmpty);
    });

    test('lo oído en las últimas 50 sale al final (o no sale si sobra)', () {
      final h = [
        ...historial,
        for (var i = 0; i < 3; i++) Escucha(p('cumb000000$i', 'Cumbia Uno'), hoy.subtract(Duration(hours: i + 1))),
      ];
      final gr = Gusto.desde(h, {}, ahora: hoy);
      final r = ids(Recomendador.ordenarSimilares(semilla, radio(), gr, minimoFrescas: 4));
      expect(r.take(3), isNot(contains('cumb0000000')));
      final pocas = ids(Recomendador.ordenarSimilares(semilla, radio(), gr, minimoFrescas: 100));
      expect(pocas.indexOf('cumb0000000'), greaterThanOrEqualTo(pocas.length - 5));
    });

    test('los gustos elegidos suben el puntaje', () {
      final neutro = Gusto.desde(const [], {}, ahora: hoy);
      final conGustos = Gusto.desde(const [], {},
          ahora: hoy, elegidos: const [ArtistaGusto(nombre: 'Cumbia Tres', id: 'id_Cumbia Tres')]);
      final lista = Recomendador.combinar([
        [for (var i = 0; i < 4; i++) p('base000000$i', 'Otro$i'), p('favorita0001', 'Cumbia Tres')],
      ]);
      final sin = ids(Recomendador.ordenarSimilares(semilla, lista, neutro, descubrimiento: 0));
      final con = ids(Recomendador.ordenarSimilares(semilla, lista, conGustos, descubrimiento: 0));
      expect(con.indexOf('favorita0001'), lessThan(sin.indexOf('favorita0001')));
      expect(con.first, 'favorita0001');
      expect(conGustos.afinidad(p('x', 'Cumbia Tres')), greaterThan(0.5));
    });

    test('los me gusta suben el artista', () {
      final gl = Gusto.desde(const [], {}, ahora: hoy, megusta: [p('liked000001', 'Cumbia Dos')]);
      expect(gl.afinidad(p('x', 'Cumbia Dos')), greaterThan(0.3));
      expect(gl.afinidad(p('x', 'Cumbia Uno')), 0);
    });

    test('diversidad: nunca más de 2 seguidas del mismo artista', () {
      final lista = Recomendador.combinar([
        [for (var i = 0; i < 8; i++) p('mismo00000$i', 'Cumbia Uno'), for (var i = 0; i < 5; i++) p('otro000000$i', 'Cumbia Dos'),
          for (var i = 0; i < 3; i++) p('terc000000$i', 'Cumbia Tres')],
      ]);
      final r = Recomendador.ordenarSimilares(semilla, lista, g, largo: 16);
      var racha = 1;
      for (var i = 1; i < r.length; i++) {
        final igual = r[i]['artista'] == r[i - 1]['artista'];
        racha = igual ? racha + 1 : 1;
        if (i < r.length - 4) expect(racha, lessThanOrEqualTo(2), reason: 'posición $i');
      }
    });

    test('intercalar rompe las rachas', () {
      final r = Recomendador.intercalar([p('a1', 'A'), p('a2', 'A'), p('a3', 'A'), p('b1', 'B')]);
      expect(ids(r), ['a1', 'a2', 'b1', 'a3']);
    });

    test('descubrimiento: una de cada cinco es un artista nuevo afín', () {
      final lista = Recomendador.combinar([
        [
          for (var i = 0; i < 10; i++) p('conoc00000$i', 'Grupo Cumbia'),
          for (var i = 0; i < 4; i++) p('nuevo00000$i', 'Nuevo$i'),
        ],
        [for (var i = 0; i < 4; i++) p('nuevo00000$i', 'Nuevo$i')], // salen en dos listas: son del círculo
      ]);
      final r = ids(Recomendador.ordenarSimilares(semilla, lista, g, largo: 10, minimoFrescas: 2));
      expect(r.where((x) => x.startsWith('nuevo')).length, greaterThanOrEqualTo(2));
      expect(r.indexOf(r.firstWhere((x) => x.startsWith('nuevo'))), lessThan(5));
    });

    test('determinista con la misma semilla', () {
      final a = ids(Recomendador.ordenarSimilares(semilla, radio(), g, azar: 42));
      final b = ids(Recomendador.ordenarSimilares(semilla, radio(), g, azar: 42));
      expect(a, b);
    });

    test('prepararRadio quita lo ya en cola', () {
      final r = ids(Recomendador.prepararRadio(semilla,
          [p('cumb0000000', 'Cumbia Uno'), p('cumb0000001', 'Cumbia Dos')], g, vistos: {'cumb0000000'}));
      expect(r, ['cumb0000001']);
    });

    test('rasgos: escritura e idioma', () {
      expect(Rasgos.de(p('a', 'BTS', titulo: '봄날')), contains('esc:coreana'));
      expect(Rasgos.de(p('a', 'X', titulo: 'Mi amor de la noche')), contains('idioma:es'));
      expect(Rasgos.similitud(Rasgos.de(p('a', 'BTS', titulo: '봄날')), Rasgos.de(p('b', 'Y', titulo: 'Baila mi amor'))),
          lessThan(0));
    });
  });

  group('gustos (guardado)', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
      Gustos.actuales = [];
    });

    const a = ArtistaGusto(nombre: 'Karol G', id: 'UC1', portada: 'x');
    const b = ArtistaGusto(nombre: 'Feid', id: 'UC2');

    test('guardar hace PATCH con gustos y gustos_elegidos', () async {
      final s = _Sesion();
      final ok = await Gustos.guardar(s, 'cta', [a, b]);
      expect(ok, isTrue);
      final (m, ruta, cuerpo) = s.enviados.single;
      expect(m, 'PATCH');
      expect(ruta, 'perfiles?id=eq.yo');
      final c = cuerpo as Map;
      expect(c['gustos_elegidos'], true);
      expect((c['gustos'] as List).first, {'nombre': 'Karol G', 'id': 'UC1', 'portada': 'x'});
      expect(Gustos.actuales, [a, b]);
    });

    test('sin red queda copia local pendiente y se reintenta', () async {
      final s = _Sesion()..falla = true;
      expect(await Gustos.guardar(s, 'cta', [a]), isFalse);
      var l = await Gustos.local('cta');
      expect(l.listo, isTrue);
      expect(l.pendiente, isTrue);
      s.falla = false;
      expect(await Gustos.reintentar(s, 'cta'), isTrue);
      expect(s.enviados.single.$3, isA<Map>());
      l = await Gustos.local('cta');
      expect(l.pendiente, isFalse);
    });

    test('máximo 30 y sin repetidos', () {
      final muchos = [for (var i = 0; i < 40; i++) {'nombre': 'A$i', 'id': 'i$i'}, {'nombre': 'A0', 'id': 'i0'}];
      expect(Gustos.leerLista(muchos).length, 30);
      expect(Gustos.leerLista([{'nombre': 'X', 'id': '1'}, {'nombre': 'X', 'id': '1'}, 5, {'id': 'sin nombre'}]).length, 1);
    });

    test('prepararSesion: pregunta solo si gustos_elegidos es false', () async {
      final s = _Sesion()..filaPerfil = [{'gustos': [], 'gustos_elegidos': false}];
      expect(await Gustos.prepararSesion(s, 'nueva'), isTrue);
      s.filaPerfil = [{'gustos': [{'nombre': 'Feid', 'id': 'UC2'}], 'gustos_elegidos': true}];
      expect(await Gustos.prepararSesion(s, 'vieja'), isFalse);
      expect(Gustos.actuales.single.nombre, 'Feid');
      // sin red no se bloquea la entrada
      s.filaPerfil = null;
      expect(await Gustos.prepararSesion(s, 'otra'), isFalse);
    });

    test('omitir marca gustos_elegidos con lista vacía', () async {
      final s = _Sesion();
      await Gustos.guardar(s, 'cta', const []);
      final c = s.enviados.single.$3 as Map;
      expect(c['gustos'], isEmpty);
      expect(c['gustos_elegidos'], true);
    });
  });

  group('pantalla', () {
    final catalogo = {
      for (var i = 0; i < 40; i++) 'Artista $i': ArtistaGusto(nombre: 'Artista $i con un nombre muy largo para probar', id: 'UC$i'),
    };

    Future<List<ArtistaGusto>> buscador(String t) async {
      if (t.startsWith('Artista')) {
        final a = catalogo[t];
        if (a != null) return [a];
      }
      if (t == 'zzz') return [];
      return [for (var i = 0; i < 4; i++) ArtistaGusto(nombre: '$t $i', id: 'r$t$i')];
    }

    final tamanos = [
      const Size(320, 568), const Size(360, 640), const Size(768, 1024), const Size(1024, 768), const Size(1440, 900),
    ];

    Future<void> montar(WidgetTester t, Size tam, _Sesion s, VoidCallback fin,
        {BuscadorArtistas? bus, double texto = 1.0}) async {
      SharedPreferences.setMockInitialValues({});
      t.view.physicalSize = tam;
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(
        theme: ThemeData(brightness: Brightness.dark, splashFactory: InkRipple.splashFactory),
        builder: (c, h) => MediaQuery(data: MediaQuery.of(c).copyWith(textScaler: TextScaler.linear(texto)), child: h!),
        home: GustosPagina(
          sesion: s, cuentaId: 'cta', alTerminar: fin,
          buscador: bus ?? buscador,
          sugeridos: [for (var i = 0; i < 24; i++) 'Artista $i'],
        ),
      ));
      await t.pump(const Duration(milliseconds: 100));
      await t.pump(const Duration(seconds: 1));
    }

    // con la tipografia de pruebas (Ahem) los textos salen enormes y la rejilla queda
    // muy baja: se pulsa por codigo para no depender de que el hit-test llegue
    Future<void> toca(WidgetTester t, String k) async {
      t.widget<InkWell>(find.byKey(ValueKey(k))).onTap!();
      await t.pump(const Duration(milliseconds: 300));
    }

    for (final tam in tamanos) {
      testWidgets('sin desbordes a ${tam.width.toInt()}x${tam.height.toInt()} (letra grande y elegidos)', (t) async {
        await montar(t, tam, _Sesion(), () {}, texto: 1.2);
        expect(find.text('¿Qué artistas te gustan?'), findsOneWidget);
        expect(find.text('Omitir por ahora'), findsOneWidget);
        for (var i = 0; i < 3; i++) {
          await toca(t, 'artista_id:UC$i');
        }
        await t.pump(const Duration(seconds: 1));
        expect(find.text('3 elegidos'), findsOneWidget);
        expect(find.text('Omitir por ahora'), findsOneWidget);
        expect(t.takeException(), isNull);
      });
    }

    testWidgets('Omitir guarda gustos_elegidos y termina', (t) async {
      final s = _Sesion();
      var fin = 0;
      await montar(t, const Size(390, 800), s, () => fin++);
      await t.tap(find.text('Omitir por ahora'));
      await t.pump(const Duration(milliseconds: 300));
      expect(fin, 1);
      final c = s.enviados.single.$3 as Map;
      expect(c['gustos_elegidos'], true);
      expect(c['gustos'], isEmpty);
    });

    testWidgets('Continuar guarda los elegidos', (t) async {
      final s = _Sesion();
      var fin = 0;
      await montar(t, const Size(390, 800), s, () => fin++);
      await toca(t, 'artista_id:UC0');
      await toca(t, 'artista_id:UC1');
      await t.tap(find.text('Continuar'));
      await t.pump(const Duration(milliseconds: 300));
      expect(fin, 1);
      expect(((s.enviados.single.$3 as Map)['gustos'] as List).length, 2);
    });

    testWidgets('máximo 30 elegidos', (t) async {
      final todos = [for (var i = 0; i < 34; i++) ArtistaGusto(nombre: 'Solista $i', id: 'S$i')];
      SharedPreferences.setMockInitialValues({});
      t.view.physicalSize = const Size(1440, 900);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(
        theme: ThemeData(brightness: Brightness.dark, splashFactory: InkRipple.splashFactory),
        home: Scaffold(
          body: GustosPagina(
              sesion: null, cuentaId: 'cta', alTerminar: () {}, buscador: (_) async => [], sugeridos: const [],
              inicial: todos.take(30).toList()),
        ),
      ));
      await t.pump(const Duration(seconds: 1));
      expect(find.textContaining('30 elegidos'), findsOneWidget);
      // la búsqueda ofrece otros: ya no caben
      await t.enterText(find.byKey(const ValueKey('buscador_artistas')), 'x');
      await t.pump(const Duration(milliseconds: 400));
      expect(t.takeException(), isNull);
    });

    testWidgets('la búsqueda espera 350 ms y solo busca lo último escrito', (t) async {
      final pedidos = <String>[];
      await montar(t, const Size(390, 800), _Sesion(), () {}, bus: (q) async {
        if (q.startsWith('Artista')) return [catalogo[q]!];
        pedidos.add(q);
        return [ArtistaGusto(nombre: 'Resultado $q', id: 'res$q')];
      });
      final campo = find.byKey(const ValueKey('buscador_artistas'));
      await t.enterText(campo, 'ka');
      await t.pump(const Duration(milliseconds: 200));
      await t.enterText(campo, 'karol');
      await t.pump(const Duration(milliseconds: 200));
      expect(pedidos, isEmpty); // todavía dentro del retraso
      await t.pump(const Duration(milliseconds: 200));
      await t.pump(const Duration(milliseconds: 400));
      expect(pedidos, ['karol']);
      expect(find.text('Resultado karol'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('sin resultados muestra un estado vacío claro', (t) async {
      await montar(t, const Size(320, 568), _Sesion(), () {});
      await t.enterText(find.byKey(const ValueKey('buscador_artistas')), 'zzz');
      await t.pump(const Duration(milliseconds: 500));
      await t.pump(const Duration(milliseconds: 500));
      expect(find.textContaining('No encontramos'), findsOneWidget);
      expect(find.text('Omitir por ahora'), findsOneWidget);
      expect(t.takeException(), isNull);
    });

    testWidgets('si las sugerencias fallan se puede omitir igual', (t) async {
      final s = _Sesion();
      var fin = 0;
      await montar(t, const Size(360, 640), s, () => fin++, bus: (_) async => throw Exception('sin red'));
      await t.pump(const Duration(seconds: 1));
      expect(find.textContaining('No pudimos cargar'), findsOneWidget);
      await t.tap(find.text('Omitir por ahora'));
      await t.pump(const Duration(milliseconds: 300));
      expect(fin, 1);
    });
  });
}
