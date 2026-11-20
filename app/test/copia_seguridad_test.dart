// Copia de seguridad (.caudal): ida y vuelta, juntar sin duplicar, reemplazar,
// archivos dañados, versión futura, la copia de la PC leída en el teléfono y la
// del teléfono guardada en test/datos para que la lea la prueba de Python.
@Timeout(Duration(minutes: 4))
library;

import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/copia_seguridad.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

const _copiaPc = 'test/datos/copia_escritorio.caudal';
const _copiaMovil = 'test/datos/copia_movil.caudal';

Uint8List _foto() {
  final im = img.Image(width: 300, height: 200);
  img.fill(im, color: img.ColorRgb8(40, 120, 200));
  return Uint8List.fromList(img.encodePng(im));
}

Map<String, dynamic> _pista(String vid, String titulo, [String artista = 'Artista']) => {
      'tipo': 'pista', 'clave': 'yt:$vid', 'video_id': vid, 'titulo': titulo, 'artista': artista,
      'artistas': [{'nombre': artista, 'id': 'UC$artista'}], 'duracion': 210,
      'miniatura': 'https://i.ytimg.com/vi/$vid/hqdefault.jpg',
    };

/// Una colección del teléfono con de todo un poco.
Future<void> _poblar(Coleccion c, Directory tmp) async {
  final audio = File('${tmp.path}/descarga.m4a')..writeAsBytesSync([1, 2, 3]);
  final idDesc = await c.agregarDescarga(
      videoId: 'movildesc01', url: 'https://www.youtube.com/watch?v=movildesc01', titulo: 'Descargada en el teléfono',
      artista: 'Grupo Móvil', archivo: audio.path, esAudio: true, tamano: 3, duracion: 190, calidad: '160');
  final local = (await c.pistas(['local:$idDesc'])).first;
  final p1 = _pista('movil000001', 'Hecha en el teléfono', 'Karol G');
  final p2 = _pista('movil000002', 'Otra del teléfono', 'Feid');
  await c.alternarMeGusta(p1);
  await c.alternarMeGusta(p2);
  await c.alternarMeGusta(local);
  final l1 = await c.crearLista('Del teléfono', descripcion: 'para el bus');
  await c.agregarALista(l1, [p1, p2]);
  await c.ponerPortadaLista(l1, _foto());
  final l2 = await c.crearLista('Gimnasio');
  await c.agregarALista(l2, [local]);
  await c.registrarEscucha(p1, {'tipo': 'mi_lista', 'id': l1, 'titulo': 'Del teléfono'});
  await Future<void>.delayed(const Duration(milliseconds: 1100));
  await c.registrarEscucha(p2, null);
  await c.guardar({'tipo': 'artista', 'id': 'UCKarol', 'titulo': 'Karol G'});
  await c.anotarBusqueda('karol g');
  await c.guardarEstado('saltos', {'canciones': {'movil000002': 3}, 'artistas': {}, 'hoy': {}});
}

Future<void> _prefsDelTelefono() async {
  final p = await SharedPreferences.getInstance();
  await p.setString('estudio.notas',
      jsonEncode([{'id': 1731830400000000, 'texto': 'Nota hecha en el teléfono', 'fecha': '2026-11-17T08:00:00.000'}]));
  await p.setString('estudio.dias', jsonEncode({'2026-11-17': 1200000}));
  await p.setString('estudio.perfil', 'leer');
  await p.setString('gustos.lista.yo', jsonEncode([{'nombre': 'Karol G', 'id': 'UCKarol', 'portada': ''}]));
  await p.setBool('gustos.listo.yo', true);
}

/// La colección sin ids internos, para comparar dos equipos.
Future<Map<String, Object>> _huella(Coleccion c) async {
  String sinLocal(Object? k) => '$k'.startsWith('local:') ? 'local' : '$k';
  final db = c.db;
  final listas = <String>[];
  for (final l in await db.query('listas', orderBy: 'nombre')) {
    final items = await db.query('lista_items', where: 'lista_id = ?', whereArgs: [l['id']], orderBy: 'orden');
    listas.add('${l['nombre']}|${l['uuid']}|${l['descripcion']}|${l['fijada']}|'
        '${items.map((i) => sinLocal(i['clave'])).join(',')}');
  }
  return {
    'me_gusta': [for (final f in await db.query('me_gusta')) sinLocal(f['clave'])]..sort(),
    'listas': listas,
    'escuchas': [for (final f in await db.query('reproducciones')) '${sinLocal(f['clave'])}|${(f['fecha'] as num).round()}']..sort(),
    'guardados': [for (final f in await db.query('guardados')) '${f['tipo']}|${f['id']}']..sort(),
    'busquedas': [for (final f in await db.query('busquedas')) '${f['texto']}']..sort(),
    'descargas': [for (final f in await db.query('descargas')) '${f['titulo']}|${f['archivo']}']..sort(),
  };
}

Uint8List _zip(Map<String, String> archivos) {
  final a = Archive();
  for (final e in archivos.entries) {
    a.addFile(ArchiveFile.string(e.key, e.value));
  }
  return ZipEncoder().encodeBytes(a);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Directory tmp;
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    tmp = await Directory.systemTemp.createTemp('copia_seguridad_');
    Coleccion.carpetaPortadasPrueba = '${tmp.path}/portadas_listas';
    Coleccion.portadaEnBytes = false;
    PortadasMem.limpiar();
  });
  tearDown(() async {
    try {
      await tmp.delete(recursive: true);
    } catch (_) {}
  });

  test('ida y vuelta en el teléfono da los mismos datos', () async {
    final a = await Coleccion.abrirEn('${tmp.path}/a.db');
    await _poblar(a, tmp);
    await _prefsDelTelefono();
    final aj = await Ajustes.cargar('yo');
    await aj.poner('eq_bandas', [1, 2, 3, 4, 5, 5, 4, 3, 2, 1]);
    await aj.poner('ecualizador', true);
    await aj.poner('modo_ligero', true);
    final bytes = await CopiaSeguridad.crear(a, ajustes: aj, cuenta: 'yo', mascota: 'gatito');
    final copia = CopiaSeguridad.abrir(bytes);
    expect(copia.origen, 'movil');
    final r = copia.resumen();
    expect(r['me_gusta'], 3);
    expect(r['listas'], 2);
    expect(r['canciones_en_listas'], 3);
    expect(r['escuchas'], 2);
    expect(r['notas'], 1);
    expect(copia.textoResumen(), contains('3 canciones en me gusta'));
    expect(copia.textoResumen(), contains('2 listas (3 canciones)'));
    expect(copia.archivos.keys.where((k) => k.startsWith('portadas/')).length, 1);

    final b = await Coleccion.abrirEn('${tmp.path}/b.db');
    final hecho = await CopiaSeguridad.restaurarColeccion(b, copia, modo: 'reemplazar');
    expect(hecho['me_gusta'], 3);
    expect(await _huella(b), await _huella(a));
    final lb = (await b.listas()).firstWhere((l) => l['nombre'] == 'Del teléfono');
    expect(await b.portadaPersonalizada(lb['id'] as int), isNotEmpty);
    expect(b.meGusta('yt:movil000001'), isTrue);

    // los ajustes vuelven en otra cuenta del mismo teléfono
    final otra = await Ajustes.cargar('otra');
    final extras = await CopiaSeguridad.restaurarExtras(copia, modo: 'reemplazar', ajustes: otra, cuenta: 'otra');
    expect(extras, containsAll(['ajustes', 'estudio', 'gustos']));
    expect(otra.bandasEq, [1, 2, 3, 4, 5, 5, 4, 3, 2, 1]);
    expect(otra.sino('modo_ligero'), isTrue);
    final p = await SharedPreferences.getInstance();
    expect(p.getString('mascota_app_otra'), 'gatito');
    await a.cerrar();
    await b.cerrar();
  });

  test('juntar no duplica y respeta lo que ya había', () async {
    final a = await Coleccion.abrirEn('${tmp.path}/a.db');
    await _poblar(a, tmp);
    final copia = CopiaSeguridad.abrir(await CopiaSeguridad.crear(a, mascota: ''));
    final b = await Coleccion.abrirEn('${tmp.path}/b.db');
    await b.alternarMeGusta(_pista('propia00001', 'Mía'));
    final lb = await b.crearLista('Del teléfono');
    await b.agregarALista(lb, [_pista('movil000001', 'Hecha en el teléfono')]);
    final primera = await CopiaSeguridad.restaurarColeccion(b, copia);
    expect(primera['me_gusta'], 3);
    final antes = await _huella(b);
    final segunda = await CopiaSeguridad.restaurarColeccion(b, copia);
    expect(segunda.values.every((v) => v == 0), isTrue, reason: '$segunda');
    expect(await _huella(b), antes);
    expect(b.totalMeGusta, 4);
    final ls = await b.listas();
    expect(ls.length, 2);
    expect(ls.firstWhere((l) => l['nombre'] == 'Del teléfono')['n'], 2);
    await a.cerrar();
    await b.cerrar();
  });

  test('reemplazar quita lo que no está, pero no las descargas', () async {
    final a = await Coleccion.abrirEn('${tmp.path}/a.db');
    await _poblar(a, tmp);
    final copia = CopiaSeguridad.abrir(await CopiaSeguridad.crear(a, mascota: ''));
    final b = await Coleccion.abrirEn('${tmp.path}/b.db');
    await b.alternarMeGusta(_pista('propia00001', 'Mía'));
    await b.crearLista('Solo aquí');
    await b.agregarDescarga(videoId: 'xx', url: 'u', titulo: 'Mía', artista: '', archivo: '${tmp.path}/x.mp3',
        esAudio: true, tamano: 1, duracion: 1, calidad: '');
    await CopiaSeguridad.restaurarColeccion(b, copia, modo: 'reemplazar');
    expect(b.meGusta('yt:propia00001'), isFalse);
    expect((await b.listas()).map((l) => l['nombre']).toSet(), {'Del teléfono', 'Gimnasio'});
    expect((await b.db.query('descargas')).length, 2);
    await a.cerrar();
    await b.cerrar();
  });

  test('con cuenta deja las órdenes para la nube', () async {
    final a = await Coleccion.abrirEn('${tmp.path}/a.db');
    await _poblar(a, tmp);
    final copia = CopiaSeguridad.abrir(await CopiaSeguridad.crear(a, mascota: ''));
    final b = await Coleccion.abrirEn('${tmp.path}/b.db');
    var avisos = 0;
    b.alHaberPendientes = () => avisos++;
    await CopiaSeguridad.restaurarColeccion(b, copia);
    final ops = [for (final f in await b.db.query('pendientes')) '${f['op']}'];
    expect(ops.where((o) => o == 'me_gusta_poner').length, 2);
    expect(ops.where((o) => o == 'lista_poner').length, 2);
    expect(ops, contains('items_poner'));
    expect(avisos, greaterThan(0));
    await a.cerrar();
    await b.cerrar();
  });

  group('errores claros', () {
    const ok = {'formato': 'caudal-copia', 'version': 1, 'lee_desde': 1, 'origen': {'app': 'movil'}};
    final casos = <String, (Uint8List, String)>{
      'vacío': (Uint8List(0), 'vacío'),
      'no es zip': (Uint8List.fromList(utf8.encode('esto no es un zip' * 20)), 'no es una copia de Caudal'),
      'zip ajeno': (_zip({'hola.txt': 'x'}), 'no es una copia de seguridad'),
      'otro formato': (_zip({'manifiesto.json': jsonEncode({'formato': 'otra-cosa'})}), 'no es una copia de seguridad'),
      'manifiesto roto': (_zip({'manifiesto.json': '{roto'}), 'dañada'),
      'sin datos': (_zip({'manifiesto.json': jsonEncode(ok)}), 'incompleta'),
      'datos rotos': (_zip({'manifiesto.json': jsonEncode(ok), 'datos.json': '[1, 2'}), 'dañada'),
      'versión futura': (
        _zip({'manifiesto.json': jsonEncode({...ok, 'version': 3, 'lee_desde': 2}), 'datos.json': '{}'}),
        'versión más nueva'
      ),
    };
    for (final e in casos.entries) {
      test(e.key, () {
        expect(() => CopiaSeguridad.abrir(e.value.$1),
            throwsA(isA<ErrorCopia>().having((x) => x.mensaje, 'mensaje', contains(e.value.$2))));
      });
    }

    test('versión futura compatible se abre', () {
      final c = CopiaSeguridad.abrir(_zip({
        'manifiesto.json': jsonEncode({...ok, 'version': 2, 'lee_desde': 1}),
        'datos.json': jsonEncode({'coleccion': {'me_gusta': [], 'cosa_nueva': 1}}),
      }));
      expect(c.resumen()['me_gusta'], 0);
    });

    test('archivo cortado o alterado', () async {
      final a = await Coleccion.abrirEn('${tmp.path}/a.db');
      await _poblar(a, tmp);
      final bytes = await CopiaSeguridad.crear(a, mascota: '');
      expect(() => CopiaSeguridad.abrir(Uint8List.sublistView(bytes, 0, bytes.length ~/ 2)), throwsA(isA<ErrorCopia>()));
      // un byte cambiado dentro de datos.json: el CRC ya no cuadra
      final roto = Uint8List.fromList(bytes);
      final nombre = utf8.encode('datos.json');
      var i = 0;
      for (; i < roto.length - 4; i++) {
        if (roto[i] == 0x50 && roto[i + 1] == 0x4b && roto[i + 2] == 3 && roto[i + 3] == 4) {
          final n = roto[i + 26] | (roto[i + 27] << 8);
          if (n == nombre.length && utf8.decode(roto.sublist(i + 30, i + 30 + n)) == 'datos.json') break;
        }
      }
      final extra = roto[i + 28] | (roto[i + 29] << 8);
      final tam = roto[i + 18] | (roto[i + 19] << 8) | (roto[i + 20] << 16);
      roto[i + 30 + nombre.length + extra + tam ~/ 2] ^= 0xFF;
      expect(() => CopiaSeguridad.abrir(roto),
          throwsA(isA<ErrorCopia>().having((x) => x.mensaje, 'mensaje', anyOf(contains('dañad'), contains('no es')))));
      await a.cerrar();
    });
  });

  test('copia automática semanal y se quedan las tres últimas', () async {
    final a = await Coleccion.abrirEn('${tmp.path}/a.db');
    await _poblar(a, tmp);
    expect(await CopiaSeguridad.automaticaSiToca(a, cuenta: 'yo', base: tmp.path), isNull); // apagada
    await CopiaSeguridad.ponerAutomatica('yo', true);
    final hechas = <File>[];
    for (var i = 0; i < 5; i++) {
      final dia = DateTime(2026, 1, 1).add(Duration(days: 8 * i));
      final f = await CopiaSeguridad.automaticaSiToca(a, cuenta: 'yo', ahora: dia, base: tmp.path);
      expect(f, isNotNull);
      hechas.add(f!);
      expect(await CopiaSeguridad.automaticaSiToca(a, cuenta: 'yo', ahora: dia.add(const Duration(days: 1)), base: tmp.path),
          isNull);
    }
    final quedan = Directory('${tmp.path}/copias').listSync().whereType<File>().toList();
    expect(quedan.length, 3);
    expect(quedan.map((f) => f.uri.pathSegments.last), contains(hechas.last.uri.pathSegments.last));
    expect(CopiaSeguridad.abrir(await hechas.last.readAsBytes()).resumen()['me_gusta'], 3);
    await a.cerrar();
  });

  test('genera la copia de ejemplo del teléfono (para la prueba de la PC)', () async {
    final a = await Coleccion.abrirEn('${tmp.path}/ejemplo.db');
    await _poblar(a, tmp);
    await _prefsDelTelefono();
    final aj = await Ajustes.cargar('yo');
    await aj.poner('eq_bandas', [1, 2, 3, 4, 5, 5, 4, 3, 2, 1]);
    await aj.poner('ecualizador', true);
    await aj.poner('region', 'CO');
    await aj.poner('crossfade', 3);
    await aj.poner('modo_ligero', true);
    final bytes = await CopiaSeguridad.crear(a, ajustes: aj, cuenta: 'yo', mascota: 'gatito');
    expect(CopiaSeguridad.abrir(bytes).resumen()['me_gusta'], 3);
    final destino = File(_copiaMovil);
    if (Platform.environment['CAUDAL_REGENERAR_COPIAS'] == '1' || !destino.existsSync()) {
      await destino.parent.create(recursive: true);
      await destino.writeAsBytes(bytes);
    }
    expect(CopiaSeguridad.abrir(destino.readAsBytesSync()).origen, 'movil');
    await a.cerrar();
  });

  test('la copia de la PC se lee en el teléfono', () async {
    final archivo = File(_copiaPc);
    expect(archivo.existsSync(), isTrue, reason: 'la genera escritorio/pruebas/test_copia_seguridad.py');
    final copia = CopiaSeguridad.abrir(archivo.readAsBytesSync());
    expect(copia.origen, 'escritorio');
    expect(copia.descripcion(), contains('Caudal Escritorio'));
    final c = await Coleccion.abrirEn('${tmp.path}/tel.db');
    await CopiaSeguridad.restaurarColeccion(c, copia);
    expect(c.totalMeGusta, 4);
    // la canción descargada en la PC no está en el teléfono: suena desde internet
    expect(c.meGusta('yt:LOCAL000001'), isTrue);
    expect((await c.pistas(['yt:LOCAL000001'])).first['titulo'], 'Canción descargada');
    expect((await c.db.query('descargas')), isEmpty);
    final ls = {for (final l in await c.listas()) l['nombre']: l['n']};
    expect(ls, {'Para correr': 3, 'Tranquilas': 1});
    final tranquilas = (await c.listas()).firstWhere((l) => l['nombre'] == 'Tranquilas');
    expect(await c.portadaPersonalizada(tranquilas['id'] as int), isNotEmpty);
    expect((await c.db.query('reproducciones')).length, 3);
    expect((await c.guardados()).length, 2);

    final aj = await Ajustes.cargar('yo');
    final hecho = await CopiaSeguridad.restaurarExtras(copia, ajustes: aj, cuenta: 'yo');
    expect(hecho, containsAll(['ajustes', 'estudio', 'gustos']));
    expect(aj.bandasEq, [4, 3, 2, 1, 0, 0, 1, 2, 3, 4]);
    expect(aj.texto('region'), 'MX');
    expect(aj.decimal('velocidad'), 1.25);
    expect(aj.entero('crossfade'), 4);
    expect(aj.entero('volumen'), 100, reason: 'el volumen de la PC no se copia al teléfono');
    final p = await SharedPreferences.getInstance();
    final notas = jsonDecode(p.getString('estudio.notas')!) as List;
    expect(notas.single['texto'], 'Nota hecha en la PC');
    expect(notas.single['id'], isA<int>());
    expect(jsonDecode(p.getString('estudio.dias')!), {'2026-11-18': 1800000});
    expect(p.getString('mascota_app_yo'), 'gatito');
    await c.cerrar();
  });
}
