// Listas públicas o privadas y «mostrar en mi perfil»: base local, sincronización con una nube de
// mentira, lectura de las listas de un perfil y la hoja de ajustes.
import 'dart:convert';
import 'dart:io';

import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/sincronizacion.dart';
import 'package:caudal/nucleo/social.dart';
import 'package:caudal/ui/paginas/lista_privacidad_hoja.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Una nube de mentira que guarda lo que se le manda y puede rechazar las columnas nuevas.
class NubeFalsa extends Sesion {
  NubeFalsa({this.rechazaAjustes = false})
      : super('u1', 'a', 'r', DateTime.now().add(const Duration(hours: 1)));

  final bool rechazaAjustes;
  final posts = <Map<String, dynamic>>[];
  final listas = <Map<String, dynamic>>[];

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    final tabla = ruta.split('?').first;
    if (metodo == 'POST' && tabla == 'listas') {
      final filas = (cuerpo as List).cast<Map<String, dynamic>>();
      if (rechazaAjustes && filas.any((f) => f.containsKey('publica'))) {
        throw const ErrorNube('column listas.publica does not exist');
      }
      posts.addAll(filas);
      return null;
    }
    if (metodo == 'GET' && tabla == 'listas') {
      if (rechazaAjustes && ruta.contains('publica')) throw const ErrorNube('column listas.publica does not exist');
      final q = Uri.splitQueryString(ruta.split('?')[1]);
      final desde = int.tryParse(q['offset'] ?? '') ?? 0;
      return listas.skip(desde).take(1000).toList();
    }
    if (metodo == 'GET') return [];
    return null;
  }
}

class SesionPerfil extends Sesion {
  SesionPerfil(this.respuesta) : super('u1', 'a', 'r', DateTime.now().add(const Duration(hours: 1)));
  final dynamic Function(String nombre) respuesta;
  @override
  Future<dynamic> rpc(String nombre, [Map<String, dynamic> parametros = const {}]) async => respuesta(nombre);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Directory tmp;
  late Coleccion col;
  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('listas_privacidad_');
    col = await Coleccion.abrirEn('${tmp.path}/c.db');
  });
  tearDown(() async {
    await col.cerrar();
    try {
      await tmp.delete(recursive: true);
    } catch (_) {}
  });

  group('base local', () {
    test('una lista nueva es privada y no sale en el perfil', () async {
      final id = await col.crearLista('Para correr');
      final l = (await col.lista(id))!;
      expect(l['publica'], 0);
      expect(l['en_perfil'], 0);
    });

    test('hacerla pública y mostrarla', () async {
      final id = await col.crearLista('Para correr');
      await col.editarLista(id, publica: true, enPerfil: true);
      final l = (await col.lista(id))!;
      expect(l['publica'], 1);
      expect(l['en_perfil'], 1);
    });

    test('«en el perfil» solo vale si es pública', () async {
      final id = await col.crearLista('Para correr');
      await col.editarLista(id, publica: false, enPerfil: true);
      expect((await col.lista(id))!['en_perfil'], 0);
      await col.editarLista(id, publica: true, enPerfil: true);
      await col.editarLista(id, publica: false); // volver privada la saca del perfil
      final l = (await col.lista(id))!;
      expect(l['publica'], 0);
      expect(l['en_perfil'], 0);
    });

    test('cambiar solo el nombre no toca los ajustes', () async {
      final id = await col.crearLista('Para correr');
      await col.editarLista(id, publica: true, enPerfil: true);
      await col.editarLista(id, nombre: 'Correr rápido');
      final l = (await col.lista(id))!;
      expect(l['publica'], 1);
      expect(l['en_perfil'], 1);
    });

    test('una base de la versión 2 se actualiza sin perder listas', () async {
      // se crea una base completa y se le quitan las dos columnas nuevas, como la dejaba la versión 2
      final ruta = '${tmp.path}/vieja.db';
      final c0 = await Coleccion.abrirEn(ruta);
      await c0.crearLista('Vieja');
      await c0.db.execute('ALTER TABLE listas DROP COLUMN publica');
      await c0.db.execute('ALTER TABLE listas DROP COLUMN en_perfil');
      await c0.db.execute('PRAGMA user_version = 2');
      await c0.cerrar();
      final c = await Coleccion.abrirEn(ruta);
      final l = (await c.listas()).single;
      expect(l['nombre'], 'Vieja');
      expect(l['publica'], 0);
      expect(l['en_perfil'], 0);
      await c.cerrar();
    });

    test('la orden para la nube lleva los ajustes solo si cambiaron', () async {
      col.alHaberPendientes = () {};
      final id = await col.crearLista('Para correr');
      await col.editarLista(id, descripcion: 'ritmo');
      for (final f in await col.db.query('pendientes')) {
        final d = jsonDecode('${f['datos']}') as Map;
        expect(d.containsKey('publica'), isFalse, reason: 'no debe estorbar si la nube no los conoce');
      }
      await col.db.delete('pendientes');
      await col.editarLista(id, publica: true, enPerfil: true);
      var d = jsonDecode('${(await col.db.query('pendientes')).single['datos']}') as Map;
      expect(d['publica'], isTrue);
      expect(d['en_perfil'], isTrue);
      await col.db.delete('pendientes');
      await col.editarLista(id, publica: false);
      d = jsonDecode('${(await col.db.query('pendientes')).single['datos']}') as Map;
      expect(d['publica'], isFalse);
      expect(d['en_perfil'], isFalse);
    });

    test('idPorUuid encuentra la lista local', () async {
      final id = await col.crearLista('Mía');
      final u = (await col.lista(id))!['uuid'] as String;
      expect(await col.idPorUuid(u), id);
      expect(await col.idPorUuid('no-existe'), isNull);
    });
  });

  group('sincronización', () {
    test('se manda a la nube lo que la persona cambia', () async {
      final nube = NubeFalsa();
      await col.guardarEstado('nube_usuario', 'u1');
      final sinc = Sincronizador(col, nube);
      col.alHaberPendientes = () {};
      final id = await col.crearLista('Para correr');
      await col.editarLista(id, publica: true, enPerfil: true);
      await sinc.cicloParaPruebas(traer: false);
      final ultima = nube.posts.last;
      expect(ultima['publica'], isTrue);
      expect(ultima['en_perfil'], isTrue);
    });

    test('si la nube aún no conoce los ajustes, se guarda lo demás', () async {
      final nube = NubeFalsa(rechazaAjustes: true);
      await col.guardarEstado('nube_usuario', 'u1');
      final sinc = Sincronizador(col, nube);
      col.alHaberPendientes = () {};
      final id = await col.crearLista('Para correr');
      await col.editarLista(id, publica: true, enPerfil: true);
      await sinc.cicloParaPruebas(traer: false);
      expect(nube.posts, isNotEmpty);
      expect(nube.posts.last['nombre'], 'Para correr');
      expect(nube.posts.last.containsKey('publica'), isFalse);
    });

    test('al traer, los ajustes de la nube llegan a la lista', () async {
      final nube = NubeFalsa();
      await col.guardarEstado('nube_usuario', 'u1');
      nube.listas.addAll([
        {'id': 'u-1', 'nombre': 'Nube', 'descripcion': '', 'fijada': false,
         'creada': '2026-01-01T00:00:00Z', 'publica': true, 'en_perfil': true},
        {'id': 'u-2', 'nombre': 'Secreta', 'descripcion': '', 'fijada': false,
         'creada': '2026-01-02T00:00:00Z', 'publica': false, 'en_perfil': true},
      ]);
      await Sincronizador(col, nube).traerParaPruebas();
      final por = {for (final l in await col.listas()) l['nombre']: l};
      expect(por['Nube']!['publica'], 1);
      expect(por['Nube']!['en_perfil'], 1);
      expect(por['Secreta']!['publica'], 0);
      expect(por['Secreta']!['en_perfil'], 0);
    });

    test('al traer, una lista que ya existe cambia sus ajustes', () async {
      final id = await col.crearLista('Mía');
      final u = (await col.lista(id))!['uuid'] as String;
      await col.guardarEstado('nube_usuario', 'u1');
      await col.db.delete('pendientes');
      final nube = NubeFalsa()
        ..listas.add({'id': u, 'nombre': 'Mía', 'descripcion': '', 'fijada': false,
            'creada': '2026-01-01T00:00:00Z', 'publica': true, 'en_perfil': false});
      await Sincronizador(col, nube).traerParaPruebas();
      final l = (await col.lista(id))!;
      expect(l['publica'], 1);
      expect(l['en_perfil'], 0);
    });

    test('al traer, una nube sin las columnas no rompe nada', () async {
      final nube = NubeFalsa(rechazaAjustes: true)
        ..listas.add({'id': 'u-3', 'nombre': 'Sin ajustes', 'descripcion': '', 'fijada': false,
            'creada': '2026-01-01T00:00:00Z'});
      await col.guardarEstado('nube_usuario', 'u1');
      await Sincronizador(col, nube).traerParaPruebas();
      final l = (await col.listas()).firstWhere((x) => x['nombre'] == 'Sin ajustes');
      expect(l['publica'], 0);
    });
  });

  group('perfil', () {
    test('ListaPerfil lee lo que manda el servidor', () {
      final l = ListaPerfil.desde({
        'id': 'u1', 'nombre': 'Pública', 'total': 3, 'publica': true, 'en_perfil': true,
        'canciones': [{'titulo': 'A', 'miniatura': ''}, {'titulo': 'B', 'miniatura': 'https://x/b.jpg'}],
      });
      expect(l.nombre, 'Pública');
      expect(l.total, 3);
      expect(l.enPerfil, isTrue);
      expect(l.miniatura, 'https://x/b.jpg');
      // un dato incoherente no engaña: privada nunca está «en el perfil»
      expect(ListaPerfil.desde({'id': 'x', 'publica': false, 'en_perfil': true}).enPerfil, isFalse);
    });

    test('pistasDe deja solo lo que suena en línea y completa la pista', () {
      final p = ListaPerfil.pistasDe({
        'canciones': [
          {'clave': 'yt:aaaaaaaaaaa', 'datos': {'titulo': 'Uno'}},
          {'clave': 'local:3', 'datos': {'titulo': 'Mía'}},
          {'clave': 'yt:bbbbbbbbbbb', 'datos': <String, dynamic>{}},
        ],
      });
      expect(p.map((x) => x['clave']), ['yt:aaaaaaaaaaa', 'yt:bbbbbbbbbbb']);
      expect(p.first['video_id'], 'aaaaaaaaaaa');
      expect(ListaPerfil.pistasDe(null), isEmpty);
    });

    test('listasDePerfil devuelve vacío si la nube aún no tiene la función', () async {
      final s = Social(SesionPerfil((_) => throw const ErrorNube('function does not exist')));
      expect(await s.listasDePerfil('ana'), isEmpty);
      expect(await s.listasDePerfil(''), isEmpty);
    });

    test('listasDePerfil convierte la respuesta', () async {
      final s = Social(SesionPerfil((_) => [
            {'id': 'u1', 'nombre': 'Una', 'total': 1, 'publica': true, 'en_perfil': true, 'canciones': []},
            'basura',
          ]));
      final l = await s.listasDePerfil('Ana');
      expect(l.length, 1);
      expect(l.single.nombre, 'Una');
    });
  });

  group('hoja de ajustes', () {
    Widget app(Widget hoja) => MaterialApp(theme: ThemeData.dark(), home: Scaffold(body: hoja));

    testWidgets('privada: «Mostrar en mi perfil» está apagado y avisa qué hacer', (t) async {
      await t.pumpWidget(app(const HojaPrivacidadLista(id: 1, publica: false, enPerfil: false)));
      expect(find.textContaining('solo tú la ves'), findsOneWidget);
      expect(find.textContaining('primero hazla pública'), findsOneWidget);
      final interruptores = t.widgetList<SwitchListTile>(find.byType(SwitchListTile)).toList();
      expect(interruptores[0].value, isFalse);
      expect(interruptores[1].onChanged, isNull);
    });

    testWidgets('pública y en el perfil: los dos encendidos', (t) async {
      await t.pumpWidget(app(const HojaPrivacidadLista(id: 1, publica: true, enPerfil: true)));
      final interruptores = t.widgetList<SwitchListTile>(find.byType(SwitchListTile)).toList();
      expect(interruptores[0].value, isTrue);
      expect(interruptores[1].value, isTrue);
      expect(interruptores[1].onChanged, isNotNull);
      expect(find.textContaining('Cualquier persona de Caudal'), findsOneWidget);
    });

    test('Esp existe (la hoja usa el espaciado del tema)', () {
      expect(Esp.lado, greaterThan(0));
    });
  });
}
