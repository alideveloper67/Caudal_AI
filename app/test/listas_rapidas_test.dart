// Guardar canciones en una lista y sincronizar sin que la app se trabe.
// Pruebas de la base local (Coleccion) y de la descarga de la nube (Sincronizador)
// con una nube falsa que cuenta las peticiones. Las bases son de memoria para
// medir el codigo y no el disco (en esta PC cada escritura a disco tarda mucho).
@Timeout(Duration(minutes: 5))
library;

import 'dart:convert';
import 'dart:io';

import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/sincronizacion.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite/sqflite.dart' show Sqflite;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

Json _pista(int n) => {
      'clave': 'yt:vid$n', 'tipo': 'pista', 'video_id': 'vid$n', 'titulo': 'Canción $n',
      'artista': 'Artista', 'miniatura': 'https://i.ytimg.com/vi/vid$n/hq.jpg',
    };

/// Una nube de mentira: guarda filas en memoria y cuenta cada peticion.
class NubeFalsa extends Sesion {
  NubeFalsa() : super('u1', 'a', 'r', DateTime.now().add(const Duration(hours: 1)));

  final peticiones = <String>[];
  final tablas = <String, List<Map<String, dynamic>>>{
    'me_gusta': [], 'listas': [], 'lista_items': [], 'guardados': [], 'escuchas': [],
  };

  int cuantas(String metodo, String tabla) =>
      peticiones.where((p) => p.startsWith('$metodo $tabla')).length;

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    peticiones.add('$metodo $ruta');
    final tabla = ruta.split('?').first;
    if (metodo == 'GET') {
      final q = Uri.splitQueryString(ruta.contains('?') ? ruta.split('?')[1] : '');
      final todas = tablas[tabla] ?? [];
      final limite = int.tryParse(q['limit'] ?? '') ?? 1000;
      final desde = int.tryParse(q['offset'] ?? '') ?? 0;
      // como PostgREST: nunca mas de 1000 filas por respuesta
      final n = limite > 1000 ? 1000 : limite;
      return todas.skip(desde).take(n).toList();
    }
    return null;
  }
}

/// Llena la nube con [listas] listas de [porLista] canciones.
void _llenar(NubeFalsa n, {int listas = 20, int porLista = 300}) {
  var c = 0;
  for (var l = 0; l < listas; l++) {
    final id = '00000000-0000-4000-8000-${l.toString().padLeft(12, '0')}';
    n.tablas['listas']!.add({
      'id': id, 'nombre': 'Lista $l', 'descripcion': '', 'fijada': false,
      'creada': '2026-01-01T00:00:${(l % 60).toString().padLeft(2, '0')}Z',
    });
    for (var i = 0; i < porLista; i++) {
      c++;
      n.tablas['lista_items']!.add({
        'lista_id': id, 'clave': 'yt:vid$c', 'orden': i + 1,
        'datos': {'clave': 'yt:vid$c', 'titulo': 'Canción $c'},
      });
    }
  }
  n.tablas['me_gusta']!.addAll([
    for (var i = 0; i < 50; i++)
      {'clave': 'yt:gusta$i', 'datos': {'titulo': 'G$i'}, 'fecha': '2026-02-01T00:00:00Z'}
  ]);
}

Future<int> _cambios(Coleccion c) async =>
    (await c.db.rawQuery('SELECT total_changes() t')).first['t'] as int;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Directory tmp;
  late Coleccion col;
  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('listas_rapidas_');
    col = await Coleccion.abrirEn(inMemoryDatabasePath);
  });
  tearDown(() async {
    await col.cerrar();
    try {
      await tmp.delete(recursive: true);
    } catch (_) {}
  });

  group('agregarALista', () {
    test('devuelve cuantas entraron, ignora repetidas y respeta el orden', () async {
      final id = await col.crearLista('Mi lista');
      expect(await col.agregarALista(id, [_pista(1), _pista(2), _pista(3)]), 3);
      // 2 y 3 ya estaban; 4 es nueva; 4 repetida dentro del mismo grupo
      expect(await col.agregarALista(id, [_pista(2), _pista(4), _pista(3), _pista(4)]), 1);
      final claves = (await col.pistasDeLista(id)).map((p) => p['clave']).toList();
      expect(claves, ['yt:vid1', 'yt:vid2', 'yt:vid3', 'yt:vid4']);
      final ordenes = (await col.db.query('lista_items', orderBy: 'orden')).map((f) => f['orden']).toList();
      expect(ordenes, [1.0, 2.0, 3.0, 5.0]); // la repetida gasta un numero, como siempre
    });

    test('una pista sin clave se ignora y las no yt: se guardan sin ir a la nube', () async {
      col.alHaberPendientes = () {};
      final id = await col.crearLista('Mixta');
      await col.db.delete('pendientes');
      final n = await col.agregarALista(id, [
        {'titulo': 'sin clave'}, {'clave': 'local:7', 'titulo': 'Mía'}, _pista(1),
      ]);
      expect(n, 2);
      final op = (await col.db.query('pendientes')).single;
      expect(op['op'], 'items_poner');
      final datos = jsonDecode('${op['datos']}') as Map;
      expect([for (final i in datos['items'] as List) i['clave']], ['yt:vid1']);
    });

    test('anota una sola orden pendiente con todo lo que entro', () async {
      col.alHaberPendientes = () {};
      final id = await col.crearLista('Con nube');
      await col.db.delete('pendientes');
      await col.agregarALista(id, [for (var i = 1; i <= 10; i++) _pista(i)]);
      await col.agregarALista(id, [_pista(5)]); // nada nuevo: no anota nada
      final ops = await col.db.query('pendientes');
      expect(ops.length, 1);
      final items = (jsonDecode('${ops.single['datos']}') as Map)['items'] as List;
      expect(items.length, 10);
      expect(items.map((i) => i['orden']).toList(), [for (var i = 1; i <= 10; i++) i.toDouble()]);
    });

    test('anadir 500 canciones tarda poco y todo queda guardado', () async {
      final id = await col.crearLista('Grande');
      final pistas = [for (var i = 0; i < 500; i++) _pista(i)];
      final reloj = Stopwatch()..start();
      final n = await col.agregarALista(id, pistas);
      reloj.stop();
      // ignore: avoid_print
      print('agregarALista(500 canciones): ${reloj.elapsedMilliseconds} ms');
      expect(n, 500);
      expect(reloj.elapsedMilliseconds, lessThan(4000));
      expect((await col.pistasDeLista(id)).length, 500);
      expect(Sqflite.firstIntValue(await col.db.rawQuery('SELECT COUNT(*) FROM pistas')), 500);
    });

    test('agregarAListaDetalle y quitarVariasDeLista: se puede deshacer de verdad', () async {
      col.alHaberPendientes = () {};
      final id = await col.crearLista('Deshacer');
      await col.agregarALista(id, [_pista(1)]);
      await col.db.delete('pendientes');
      final entraron = await col.agregarAListaDetalle(id, [_pista(1), _pista(2), _pista(3)]);
      expect(entraron, ['yt:vid2', 'yt:vid3']);
      await col.quitarVariasDeLista(id, entraron);
      expect((await col.pistasDeLista(id)).map((p) => p['clave']).toList(), ['yt:vid1']);
      final ops = await col.db.query('pendientes', orderBy: 'id');
      expect(ops.map((o) => o['op']).toList(), ['items_poner', 'items_quitar']);
      expect(((jsonDecode('${ops.last['datos']}') as Map)['claves'] as List).length, 2);
    });
  });

  group('listas en memoria', () {
    test('la hoja las tiene al instante y se rehacen al cambiar algo', () async {
      expect(col.listasEnMemoria, isNotNull);
      expect(col.listasEnMemoria, isEmpty);
      final id = await col.crearLista('Nueva');
      await Future<void>.delayed(const Duration(milliseconds: 500));
      expect(col.listasEnMemoria!.map((l) => l['nombre']), ['Nueva']);
      await col.marcarListaUsada(id);
      expect(col.ultimaLista, id);
    });

    test('la ultima lista usada se recuerda al reabrir', () async {
      await col.cerrar();
      col = await Coleccion.abrirEn('${tmp.path}/recordada.db');
      final id = await col.crearLista('Recordada');
      await col.marcarListaUsada(id);
      await col.cerrar();
      col = await Coleccion.abrirEn('${tmp.path}/recordada.db');
      expect(col.ultimaLista, id);
    });
  });

  test('textoAvisoAnadido', () {
    expect(textoAvisoAnadido([('Rock', 3)]), 'Añadido a «Rock»');
    expect(textoAvisoAnadido([('Rock', 0)]), 'Ya estaba en «Rock»');
    expect(textoAvisoAnadido([('A', 1), ('B', 2), ('C', 1)]), 'Añadido a 3 listas');
    expect(textoAvisoAnadido([('A', 1), ('B', 0)]), 'Añadido a «A»');
    expect(textoAvisoAnadido([('A', 0), ('B', 0)]), 'Ya estaba en esas 2 listas');
  });

  group('Sincronizador', () {
    late NubeFalsa nube;
    late Sincronizador sinc;
    setUp(() async {
      nube = NubeFalsa();
      await col.guardarEstado('nube_usuario', 'u1'); // sin subida inicial
      sinc = Sincronizador(col, nube);
    });

    test('20 listas de 300 canciones: pocas peticiones y cero escrituras si nada cambio', () async {
      _llenar(nube);
      var antes = await _cambios(col);
      expect(await sinc.traerParaPruebas(), isTrue);
      final primera = await _cambios(col) - antes;
      final peticiones = nube.peticiones.length;
      // ignore: avoid_print
      print('1.ª descarga: $peticiones peticiones, $primera filas escritas');
      expect(nube.cuantas('GET', 'lista_items'), 7, reason: '6000 filas = 6 paginas llenas + 1 vacia');
      expect(nube.cuantas('GET', 'listas'), 1);
      expect((await col.listas()).length, 20);
      expect(Sqflite.firstIntValue(await col.db.rawQuery('SELECT COUNT(*) FROM lista_items')), 6000);

      nube.peticiones.clear();
      antes = await _cambios(col);
      final reloj = Stopwatch()..start();
      expect(await sinc.traerParaPruebas(), isFalse, reason: 'sin cambios no se repinta nada');
      reloj.stop();
      final repetida = await _cambios(col) - antes;
      // ignore: avoid_print
      print('2.ª descarga sin cambios: ${nube.peticiones.length} peticiones, $repetida filas escritas, '
          '${reloj.elapsedMilliseconds} ms');
      expect(repetida, 0);
    });

    test('un cambio en la nube toca solo esa fila', () async {
      _llenar(nube, listas: 3, porLista: 50);
      await sinc.traerParaPruebas();
      final id = nube.tablas['listas']!.first['id'];
      nube.tablas['lista_items']!.add({
        'lista_id': id, 'clave': 'yt:nueva', 'orden': 99, 'datos': {'clave': 'yt:nueva', 'titulo': 'N'},
      });
      nube.tablas['lista_items']!.removeAt(1);
      final antes = await _cambios(col);
      expect(await sinc.traerParaPruebas(), isTrue);
      // una cancion nueva (+ su ficha) y una quitada
      expect(await _cambios(col) - antes, lessThanOrEqualTo(3));
      final l = (await col.listas()).firstWhere((l) => l['uuid'] == id);
      expect(l['n'], 50);
    });

    test('mas de 1000 canciones en una lista: llegan todas (antes se cortaba)', () async {
      _llenar(nube, listas: 1, porLista: 2500);
      await sinc.traerParaPruebas();
      expect(Sqflite.firstIntValue(await col.db.rawQuery('SELECT COUNT(*) FROM lista_items')), 2500);
      expect(nube.cuantas('GET', 'lista_items'), 3);
    });

    test('lo que se borro o renombro en la nube se refleja', () async {
      _llenar(nube, listas: 2, porLista: 5);
      await sinc.traerParaPruebas();
      nube.tablas['listas']!.first['nombre'] = 'Otro nombre';
      nube.tablas['listas']!.removeLast();
      expect(await sinc.traerParaPruebas(), isTrue);
      expect((await col.listas()).map((l) => l['nombre']).toList(), ['Otro nombre']);
    });

    test('con ordenes pendientes no se descarga nada', () async {
      _llenar(nube, listas: 2, porLista: 5);
      await col.db.insert('pendientes', {'op': 'me_gusta_quitar', 'datos': '{"clave":"yt:x"}', 'creada': 1});
      expect(await sinc.traerParaPruebas(), isFalse);
      expect(nube.cuantas('GET', 'lista_items'), 0);
    });

    test('tras un cambio local solo se ENVIA: nada de descargar las listas', () async {
      _llenar(nube, listas: 5, porLista: 20);
      col.alHaberPendientes = () {};
      final id = await col.crearLista('Mia');
      await col.agregarALista(id, [_pista(1), _pista(2)]);
      nube.peticiones.clear();
      await sinc.ya(); // lo que dispara pronto() tras 1,5 s
      expect(nube.cuantas('POST', 'listas'), 1);
      expect(nube.cuantas('POST', 'lista_items'), 1);
      expect(nube.cuantas('GET', 'lista_items'), 0);
      expect(nube.cuantas('GET', 'me_gusta'), 0);
      expect(nube.cuantas('GET', 'listas'), 0);
      expect(Sqflite.firstIntValue(await col.db.rawQuery('SELECT COUNT(*) FROM pendientes')), 0);
    });

    test('la descarga completa (arranque, 3 min, volver, tirar) si descarga', () async {
      _llenar(nube, listas: 2, porLista: 5);
      await sinc.ya(traer: true);
      expect(nube.cuantas('GET', 'lista_items'), 1);
      expect((await col.listas()).length, 2);
      nube.peticiones.clear();
      await sinc.refrescarAhora();
      expect(nube.cuantas('GET', 'lista_items'), 1);
    });

    test('antes: una peticion por lista; ahora: una para todas', () async {
      _llenar(nube, listas: 20, porLista: 10);
      await sinc.traerParaPruebas();
      final deItems = nube.cuantas('GET', 'lista_items');
      // ignore: avoid_print
      print('20 listas de 10 canciones: $deItems peticion(es) de canciones (antes: 20)');
      expect(deItems, 1);
    });
  });
}
