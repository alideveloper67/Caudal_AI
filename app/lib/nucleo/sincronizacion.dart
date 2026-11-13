import 'dart:async';
import 'dart:convert';

import 'package:sqflite/sqflite.dart';

import 'coleccion.dart';
import 'nube.dart';

/// Sincroniza la biblioteca local con Supabase (el mismo protocolo que
/// sincronizacion.py de Caudal Escritorio, para que las dos apps se entiendan).
///
/// 1. La primera vez que una cuenta entra en el telefono, sube lo que haya.
/// 2. Envia las ordenes de `pendientes` en orden (si no hay red, esperan).
/// 3. Trae lo cambiado en otros dispositivos: la nube manda, salvo lo que aun
///    espera para subir.
class Sincronizador {
  Sincronizador(this.coleccion, this.sesion, {this.alRenovar});

  final Coleccion coleccion;
  final Sesion sesion;
  final Future<void> Function()? alRenovar;

  Timer? _reloj;
  Timer? _pronto;
  bool _corriendo = false;
  bool _otraVez = false;
  String estado = '';
  final _estados = StreamController<String>.broadcast();
  Stream<String> get cambios => _estados.stream;

  Database get _db => coleccion.db;

  void iniciar() {
    coleccion.alHaberPendientes = pronto;
    _reloj = Timer.periodic(const Duration(minutes: 3), (_) => ya());
    Timer(const Duration(milliseconds: 800), ya);
  }

  void detener() {
    _reloj?.cancel();
    _pronto?.cancel();
    coleccion.alHaberPendientes = null;
  }

  /// Un cambio local: se envia en un momento (se agrupan los seguidos).
  void pronto() {
    _pronto?.cancel();
    _pronto = Timer(const Duration(milliseconds: 1500), ya);
  }

  Future<void> ya() async {
    if (_corriendo) {
      _otraVez = true;
      return;
    }
    _corriendo = true;
    try {
      final cambio = await _ciclo();
      _fijar('sincronizado');
      if (alRenovar != null) await alRenovar!();
      if (cambio) await coleccion.refrescarMemoria();
    } on SinConexion {
      _fijar('sin_conexion');
    } catch (_) {
      _fijar('error');
    } finally {
      _corriendo = false;
    }
    if (_otraVez) {
      _otraVez = false;
      pronto();
    }
  }

  void _fijar(String e) {
    if (e != estado) {
      estado = e;
      _estados.add(e);
    }
  }

  Future<bool> _ciclo() async {
    final marca = await coleccion.estado('nube_usuario');
    if (marca != sesion.userId) {
      await _subidaInicial();
      await coleccion.guardarEstado('nube_usuario', sesion.userId);
    }
    await _enviarPendientes();
    return _traer();
  }

  Future<void> _upsert(String tabla, List<Map<String, dynamic>> filas, String conflicto) async {
    for (var i = 0; i < filas.length; i += 400) {
      await sesion.pedir('POST', '$tabla?on_conflict=$conflicto',
          cuerpo: filas.sublist(i, i + 400 > filas.length ? filas.length : i + 400),
          cabeceras: {'Prefer': 'resolution=merge-duplicates,return=minimal'});
    }
  }

  Future<Map<String, Map<String, dynamic>>> _datosPistas() async {
    final salida = <String, Map<String, dynamic>>{};
    for (final f in await _db.query('pistas')) {
      try {
        salida['${f['clave']}'] = Map<String, dynamic>.from(jsonDecode('${f['datos']}') as Map);
      } catch (_) {}
    }
    return salida;
  }

  Future<void> _subidaInicial() async {
    final pistas = await _datosPistas();
    await _upsert('me_gusta', [
      for (final f in await _db.query('me_gusta'))
        if ('${f['clave']}'.startsWith('yt:'))
          {'clave': f['clave'], 'datos': pistas['${f['clave']}'] ?? {}, 'fecha': _iso(f['fecha'])}
    ], 'user_id,clave');
    for (final l in await _db.query('listas')) {
      var u = l['uuid'] as String?;
      if (u == null || u.isEmpty) {
        u = nuevoUuid();
        await _db.update('listas', {'uuid': u}, where: 'id = ?', whereArgs: [l['id']]);
      }
      await _upsert('listas', [
        {'id': u, 'nombre': l['nombre'], 'descripcion': l['descripcion'] ?? '',
         'fijada': l['fijada'] == 1}
      ], 'id');
      await _upsert('lista_items', [
        for (final f in await _db.query('lista_items', where: 'lista_id = ?', whereArgs: [l['id']]))
          if ('${f['clave']}'.startsWith('yt:'))
            {'lista_id': u, 'clave': f['clave'], 'datos': pistas['${f['clave']}'] ?? {},
             'orden': f['orden'] ?? 0}
      ], 'lista_id,clave');
    }
    await _upsert('guardados', [
      for (final f in await _db.query('guardados'))
        {'tipo': f['tipo'], 'id': f['id'], 'datos': jsonDecode('${f['datos']}'),
         'fecha': _iso(f['fecha'])}
    ], 'user_id,tipo,id');
    final escuchas = await _db.query('reproducciones',
        where: "nube_id IS NULL AND clave LIKE 'yt:%'", orderBy: 'fecha DESC', limit: 300);
    if (escuchas.isNotEmpty) {
      await sesion.pedir('POST', 'escuchas', cuerpo: [
        for (final f in escuchas)
          {'clave': f['clave'], 'datos': pistas['${f['clave']}'] ?? {},
           'contexto': '${f['contexto'] ?? ''}'.isEmpty ? null : jsonDecode('${f['contexto']}'),
           'fecha': _iso(f['fecha'])}
      ], cabeceras: {'Prefer': 'return=minimal'});
      await _db.update('reproducciones', {'nube_id': -1}, where: 'nube_id IS NULL');
    }
  }

  Future<void> _enviarPendientes() async {
    for (final f in await _db.query('pendientes', orderBy: 'id')) {
      final d = jsonDecode('${f['datos']}');
      try {
        await _enviar('${f['op']}', d);
      } on SinConexion {
        rethrow;
      } on ErrorNube {
        // una orden que la nube rechaza no debe bloquear las demas
      }
      await _db.delete('pendientes', where: 'id = ?', whereArgs: [f['id']]);
    }
  }

  static String _q(Object? v) => Uri.encodeQueryComponent('$v');

  Future<void> _enviar(String op, dynamic d) async {
    switch (op) {
      case 'me_gusta_poner':
        await _upsert('me_gusta', [{'clave': d['clave'], 'datos': d['datos'] ?? {}}], 'user_id,clave');
      case 'me_gusta_quitar':
        await sesion.pedir('DELETE', 'me_gusta?clave=eq.${_q(d['clave'])}');
      case 'lista_poner':
        await _upsert('listas', [
          {'id': d['uuid'], 'nombre': d['nombre'], 'descripcion': d['descripcion'] ?? '',
           'fijada': d['fijada'] == true, 'actualizada': _iso(null)}
        ], 'id');
      case 'lista_borrar':
        await sesion.pedir('DELETE', 'listas?id=eq.${_q(d['uuid'])}');
      case 'items_poner':
        await _upsert('lista_items', [
          for (final i in (d['items'] as List))
            {'lista_id': d['uuid'], 'clave': i['clave'], 'datos': i['datos'] ?? {},
             'orden': i['orden'] ?? 0}
        ], 'lista_id,clave');
      case 'item_quitar':
        await sesion.pedir('DELETE',
            'lista_items?lista_id=eq.${_q(d['uuid'])}&clave=eq.${_q(d['clave'])}');
      case 'guardado_poner':
        await _upsert('guardados', [{'tipo': d['tipo'], 'id': d['id'], 'datos': d['datos'] ?? {}}],
            'user_id,tipo,id');
      case 'guardado_quitar':
        await sesion.pedir('DELETE', 'guardados?tipo=eq.${_q(d['tipo'])}&id=eq.${_q(d['id'])}');
      case 'escucha':
        await sesion.pedir('POST', 'escuchas', cuerpo: [
          {'clave': d['clave'], 'datos': d['datos'] ?? {}, 'contexto': d['contexto'],
           'fecha': _iso(d['fecha'])}
        ], cabeceras: {'Prefer': 'return=minimal'});
      case 'ajustes':
        await _upsert('ajustes', [{'datos': d, 'actualizado': _iso(null)}], 'user_id');
    }
  }

  Future<bool> _traer() async {
    final n = Sqflite.firstIntValue(await _db.rawQuery('SELECT COUNT(*) FROM pendientes')) ?? 0;
    if (n > 0) return false;
    final antes = await _huella();

    final gustan = await sesion.pedir('GET', 'me_gusta?select=clave,datos,fecha&order=fecha.desc&limit=5000') as List;
    final listas = await sesion.pedir('GET', 'listas?select=id,nombre,descripcion,fijada,creada&order=creada') as List;
    final items = <String, List>{};
    for (final l in listas) {
      items['${l['id']}'] = await sesion.pedir('GET',
          'lista_items?select=clave,datos,orden&lista_id=eq.${l['id']}&order=orden&limit=5000') as List;
    }
    final guardados = await sesion.pedir('GET', 'guardados?select=tipo,id,datos,fecha') as List;
    final escuchas = await sesion.pedir('GET',
        'escuchas?select=id,clave,datos,contexto,fecha&order=fecha.desc&limit=300') as List;

    await _db.transaction((t) async {
      Future<void> recordar(String clave, dynamic datos) async {
        if (datos is Map && datos.isNotEmpty) {
          await t.insert('pistas', {'clave': clave, 'datos': jsonEncode(datos),
              'actualizada': _epoch(null)}, conflictAlgorithm: ConflictAlgorithm.replace);
        }
      }

      await t.delete('me_gusta', where: "clave LIKE 'yt:%'");
      for (final f in gustan) {
        await recordar('${f['clave']}', f['datos']);
        await t.insert('me_gusta', {'clave': f['clave'], 'fecha': _epoch(f['fecha'])},
            conflictAlgorithm: ConflictAlgorithm.replace);
      }

      final uuids = <String>{};
      for (final l in listas) {
        final u = '${l['id']}';
        uuids.add(u);
        final fila = await t.query('listas', columns: ['id'], where: 'uuid = ?', whereArgs: [u]);
        int lid;
        if (fila.isNotEmpty) {
          lid = fila.first['id'] as int;
          await t.update('listas', {'nombre': l['nombre'], 'descripcion': l['descripcion'] ?? '',
              'fijada': l['fijada'] == true ? 1 : 0}, where: 'id = ?', whereArgs: [lid]);
        } else {
          var nombre = '${l['nombre']}';
          if ((await t.query('listas', where: 'nombre = ?', whereArgs: [nombre])).isNotEmpty) {
            nombre = '$nombre (${u.substring(0, 4)})';
          }
          lid = await t.insert('listas', {
            'nombre': nombre, 'creada': _epoch(l['creada']), 'descripcion': l['descripcion'] ?? '',
            'fijada': l['fijada'] == true ? 1 : 0, 'uuid': u, 'tocada': _epoch(l['creada']),
          });
        }
        await t.delete('lista_items', where: "lista_id = ? AND clave LIKE 'yt:%'", whereArgs: [lid]);
        for (final i in items[u] ?? []) {
          await recordar('${i['clave']}', i['datos']);
          await t.insert('lista_items', {'lista_id': lid, 'clave': i['clave'], 'orden': i['orden'],
              'agregada': _epoch(null)}, conflictAlgorithm: ConflictAlgorithm.replace);
        }
      }
      for (final l in await t.query('listas', where: 'uuid IS NOT NULL')) {
        if (!uuids.contains(l['uuid'])) {
          await t.delete('lista_items', where: 'lista_id = ?', whereArgs: [l['id']]);
          await t.delete('listas', where: 'id = ?', whereArgs: [l['id']]);
        }
      }

      await t.delete('guardados');
      for (final g in guardados) {
        await t.insert('guardados', {'tipo': g['tipo'], 'id': g['id'], 'datos': jsonEncode(g['datos']),
            'fecha': _epoch(g['fecha'])}, conflictAlgorithm: ConflictAlgorithm.replace);
      }

      for (final e in escuchas) {
        if ((await t.query('reproducciones', where: 'nube_id = ?', whereArgs: [e['id']])).isNotEmpty) {
          continue;
        }
        final ya = await t.rawQuery(
            'SELECT id FROM reproducciones WHERE clave = ? AND nube_id = -1 AND ABS(fecha - ?) < 5',
            [e['clave'], _epoch(e['fecha'])]);
        if (ya.isNotEmpty) {
          await t.update('reproducciones', {'nube_id': e['id']}, where: 'id = ?', whereArgs: [ya.first['id']]);
          continue;
        }
        await recordar('${e['clave']}', e['datos']);
        await t.insert('reproducciones', {
          'clave': e['clave'], 'fecha': _epoch(e['fecha']),
          'contexto': e['contexto'] == null ? '' : jsonEncode(e['contexto']), 'nube_id': e['id'],
        });
      }
    });
    return await _huella() != antes;
  }

  Future<String> _huella() async {
    final partes = <String>[];
    for (final sql in [
      'SELECT group_concat(clave) FROM (SELECT clave FROM me_gusta ORDER BY clave)',
      "SELECT group_concat(uuid || nombre || descripcion || fijada) FROM listas",
      'SELECT group_concat(lista_id || clave || orden) FROM lista_items',
      'SELECT group_concat(tipo || id) FROM guardados',
      'SELECT COUNT(*) FROM reproducciones',
    ]) {
      final f = await _db.rawQuery(sql);
      partes.add('${f.first.values.first}');
    }
    return partes.join('|');
  }

  static String _iso(Object? epoch) {
    final ms = epoch is num ? (epoch * 1000).round() : DateTime.now().millisecondsSinceEpoch;
    return DateTime.fromMillisecondsSinceEpoch(ms, isUtc: true).toIso8601String();
  }

  static double _epoch(Object? iso) {
    if (iso == null) return DateTime.now().millisecondsSinceEpoch / 1000.0;
    return (DateTime.tryParse('$iso') ?? DateTime.now()).millisecondsSinceEpoch / 1000.0;
  }
}
