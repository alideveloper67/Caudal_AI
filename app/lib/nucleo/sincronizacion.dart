import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:flutter/widgets.dart' show AppLifecycleState, WidgetsBinding, WidgetsBindingObserver;
import 'package:sqflite/sqflite.dart';

import 'ajustes.dart';
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
  Sincronizador(this.coleccion, this.sesion, {this.alRenovar, this.ajustes, this.alCambiarAjustes});

  final Coleccion coleccion;

  /// Los ajustes comunes (ecualizador, calidad...) viajan entre dispositivos.
  final Ajustes? ajustes;
  final void Function(Set<String> cambiados)? alCambiarAjustes;
  final Sesion sesion;
  final Future<void> Function()? alRenovar;

  Timer? _reloj;
  Timer? _pronto;
  bool _corriendo = false;
  bool _otraVez = false;
  bool _traerPendiente = false;
  DateTime? _ultimaDescarga;
  _VidaApp? _vida;
  String estado = '';
  final _estados = StreamController<String>.broadcast();
  Stream<String> get cambios => _estados.stream;

  /// Cuanto se espera, como minimo, entre dos descargas completas cuando la
  /// app vuelve a primer plano.
  static const esperaAlVolver = Duration(seconds: 45);

  Database get _db => coleccion.db;

  void iniciar() {
    coleccion.alHaberPendientes = pronto;
    // la descarga completa: al arrancar y cada 3 minutos
    _reloj = Timer.periodic(const Duration(minutes: 3), (_) => ya(traer: true));
    Timer(const Duration(milliseconds: 800), () => ya(traer: true));
    // y al volver la app a primer plano (si ya paso un rato)
    try {
      _vida = _VidaApp(() {
        final u = _ultimaDescarga;
        if (u == null || DateTime.now().difference(u) > esperaAlVolver) ya(traer: true);
      });
      WidgetsBinding.instance.addObserver(_vida!);
    } catch (_) {
      _vida = null; // sin motor de pantalla (pruebas de consola)
    }
  }

  void detener() {
    _reloj?.cancel();
    _pronto?.cancel();
    final v = _vida;
    if (v != null) {
      try {
        WidgetsBinding.instance.removeObserver(v);
      } catch (_) {}
    }
    coleccion.alHaberPendientes = null;
  }

  /// Un cambio local: en un momento se ENVIA lo pendiente (se agrupan los
  /// seguidos). No se descarga nada: lo de la nube se trae en otros momentos.
  void pronto() {
    _pronto?.cancel();
    _pronto = Timer(const Duration(milliseconds: 1500), () => ya());
  }

  /// «Refrescar ahora» (tirar para refrescar): envia lo pendiente y baja todo.
  Future<void> refrescarAhora() => ya(traer: true);

  /// Un ciclo. Con [traer] tambien se descarga lo de la nube; sin eso solo se
  /// envian las ordenes pendientes (lo que sigue a cada cambio local).
  Future<void> ya({bool traer = false}) async {
    if (_corriendo) {
      _otraVez = true;
      _traerPendiente = _traerPendiente || traer;
      return;
    }
    _corriendo = true;
    traer = traer || _traerPendiente;
    _traerPendiente = false;
    try {
      final cambio = await _ciclo(traer: traer);
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

  Future<bool> _ciclo({bool traer = true}) async {
    final marca = await coleccion.estado('nube_usuario');
    if (marca != sesion.userId) {
      await _subidaInicial();
      await coleccion.guardarEstado('nube_usuario', sesion.userId);
    }
    await _enviarPendientes();
    var cambio = false;
    if (traer) {
      cambio = await _traer();
      _ultimaDescarga = DateTime.now();
    }
    // los ajustes: en una descarga completa siempre; si no, solo si cambiaron aqui
    if (traer || await _ajustesCambiaron()) await _sincronizarAjustes();
    return cambio;
  }

  Future<bool> _ajustesCambiaron() async {
    final a = ajustes;
    if (a == null) return false;
    final huella = huellaAjustes(ajustesParaNube(a.paraNube()));
    return huella != await coleccion.estado('ajustes_huella');
  }

  /// Para las pruebas: un ciclo completo o solo de envio, sin temporizadores.
  @visibleForTesting
  Future<bool> cicloParaPruebas({required bool traer}) => _ciclo(traer: traer);

  /// Para las pruebas: solo la descarga.
  @visibleForTesting
  Future<bool> traerParaPruebas() => _traer();

  /// Los ajustes comunes como van a la nube (eq_bandas siempre como lista).
  static Map<String, Object?> ajustesParaNube(Map<String, Object?> crudos) {
    final salida = <String, Object?>{};
    crudos.forEach((k, v) {
      if (v == null) return;
      if (k == 'eq_bandas' && v is String) {
        try {
          salida[k] = jsonDecode(v);
        } catch (_) {}
        return;
      }
      salida[k] = v;
    });
    return salida;
  }

  /// Misma huella que huella_ajustes() del escritorio: claves ordenadas.
  static String huellaAjustes(Map<String, Object?> datos) {
    final claves = datos.keys.toList()..sort();
    return jsonEncode({for (final k in claves) k: datos[k]});
  }

  /// Si solo cambiaron en otro dispositivo, se aplican aqui; si cambiaron
  /// aqui, se suben (gana el ultimo). Igual que en sincronizacion.py.
  Future<void> _sincronizarAjustes() async {
    final a = ajustes;
    if (a == null) return;
    final locales = ajustesParaNube(a.paraNube());
    final huella = huellaAjustes(locales);
    final sincronizada = await coleccion.estado('ajustes_huella');
    final fechaVista = await coleccion.estado('ajustes_fecha');
    final filas = await sesion.pedir('GET', 'ajustes?select=datos,actualizado') as List;
    final remoto = filas.isEmpty ? null : Map<String, dynamic>.from(filas.first as Map);
    // un telefono nuevo en la cuenta toma los de la nube, no los sube
    final primeraVez = sincronizada == null;
    if (remoto != null && remoto['actualizado'] != fechaVista && (huella == sincronizada || primeraVez)) {
      final datos = <String, Object?>{
        for (final e in Map<String, dynamic>.from((remoto['datos'] as Map?) ?? {}).entries)
          if (Ajustes.compartidos.contains(e.key)) e.key: e.value,
      };
      final cambiados = <String>{};
      for (final e in datos.entries) {
        if (e.value == null || jsonEncode(locales[e.key]) == jsonEncode(e.value)) continue;
        await a.poner(e.key, e.value is num && Ajustes.defectos[e.key] is double
            ? (e.value as num).toDouble() : e.value!, avisar: false);
        cambiados.add(e.key);
      }
      await coleccion.guardarEstado('ajustes_huella', huellaAjustes({...locales, ...datos}));
      await coleccion.guardarEstado('ajustes_fecha', remoto['actualizado']);
      if (cambiados.isNotEmpty) alCambiarAjustes?.call(cambiados);
    } else if (remoto == null || huella != sincronizada) {
      await _upsert('ajustes', [{'datos': locales, 'actualizado': _iso(null)}], 'user_id');
      final nueva = await sesion.pedir('GET', 'ajustes?select=actualizado') as List;
      await coleccion.guardarEstado('ajustes_huella', huella);
      await coleccion.guardarEstado('ajustes_fecha',
          nueva.isEmpty ? null : (nueva.first as Map)['actualizado']);
    }
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
         'fijada': l['fijada'] == 1,
         // solo si la usa: asi la subida no se rompe mientras la nube no conozca estas columnas
         if (l['publica'] == 1) ...{'publica': true, 'en_perfil': l['en_perfil'] == 1}}
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
        final fila = {'id': d['uuid'], 'nombre': d['nombre'], 'descripcion': d['descripcion'] ?? '',
           'fijada': d['fijada'] == true, 'actualizada': _iso(null)};
        if (d['publica'] != null) {
          try {
            await _upsert('listas', [
              {...fila, 'publica': d['publica'] == true, 'en_perfil': d['publica'] == true && d['en_perfil'] == true}
            ], 'id');
            return;
          } on ErrorNube {
            // la nube aun no conoce estos ajustes: al menos se guarda lo demas
          }
        }
        await _upsert('listas', [fila], 'id');
      case 'lista_borrar':
        await sesion.pedir('DELETE', 'listas?id=eq.${_q(d['uuid'])}');
      case 'items_poner':
        await _upsert('lista_items', [
          for (final i in (d['items'] as List))
            {'lista_id': d['uuid'], 'clave': i['clave'], 'datos': i['datos'] ?? {},
             'orden': i['orden'] ?? 0}
        ], 'lista_id,clave');
      case 'items_quitar':
        final claves = [for (final c in (d['claves'] as List)) '$c'];
        for (var i = 0; i < claves.length; i += 50) {
          final lote = claves.sublist(i, i + 50 > claves.length ? claves.length : i + 50);
          final lista = lote.map((c) => '"${c.replaceAll('"', '')}"').join(',');
          await sesion.pedir('DELETE',
              'lista_items?lista_id=eq.${_q(d['uuid'])}&clave=in.(${Uri.encodeQueryComponent(lista)})');
        }
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

  /// PostgREST devuelve como mucho 1000 filas por respuesta: se pide por paginas
  /// hasta que una venga incompleta (antes, `limit=5000` se cortaba en silencio).
  static const tamanoPagina = 1000;

  Future<List> _todas(String ruta) async {
    final salida = <dynamic>[];
    for (var desde = 0;; desde += tamanoPagina) {
      final r = await sesion.pedir('GET', '$ruta&limit=$tamanoPagina&offset=$desde') as List;
      salida.addAll(r);
      if (r.length < tamanoPagina) break;
    }
    return salida;
  }

  /// Dos valores de la nube iguales, sin importar el orden de las claves.
  static String _canonico(Object? v) {
    if (v is Map) {
      final k = v.keys.map((e) => '$e').toList()..sort();
      return '{${k.map((e) => '${jsonEncode(e)}:${_canonico(v[e])}').join(',')}}';
    }
    if (v is List) return '[${v.map(_canonico).join(',')}]';
    return jsonEncode(v);
  }

  /// Baja lo de la nube y lo deja en la base local **solo donde cambio**.
  /// Devuelve si hubo un cambio que la pantalla deba notar.
  Future<bool> _traer() async {
    final n = Sqflite.firstIntValue(await _db.rawQuery('SELECT COUNT(*) FROM pendientes')) ?? 0;
    if (n > 0) return false;

    // una peticion por tabla (los items de TODAS las listas en una sola)
    final gustan = await _todas('me_gusta?select=clave,datos,fecha&order=fecha.desc,clave');
    List listas;
    try {
      listas = await _todas('listas?select=id,nombre,descripcion,fijada,creada,publica,en_perfil&order=creada,id');
    } on ErrorNube {
      // la nube aun no conoce publica / en_perfil
      listas = await _todas('listas?select=id,nombre,descripcion,fijada,creada&order=creada,id');
    }
    final itemsNube = await _todas('lista_items?select=lista_id,clave,datos,orden&order=lista_id,orden,clave');
    final guardados = await _todas('guardados?select=tipo,id,datos,fecha&order=tipo,id');
    final escuchas = await sesion.pedir('GET',
        'escuchas?select=id,clave,datos,contexto,fecha&order=fecha.desc&limit=300') as List;

    var cambio = false;
    await _db.transaction((t) async {
      final conocidas = {
        for (final f in await t.query('pistas', columns: ['clave'])) '${f['clave']}'
      };
      final b = t.batch();
      void recordar(String clave, dynamic datos) {
        if (datos is Map && datos.isNotEmpty && !conocidas.contains(clave)) {
          conocidas.add(clave);
          b.insert('pistas', {'clave': clave, 'datos': jsonEncode(datos), 'actualizada': _epoch(null)},
              conflictAlgorithm: ConflictAlgorithm.replace);
        }
      }

      // ---- me gusta
      final gLocal = {
        for (final f in await t.query('me_gusta', where: "clave LIKE 'yt:%'")) '${f['clave']}': f['fecha']
      };
      final gNube = <String>{};
      for (final f in gustan) {
        final clave = '${f['clave']}';
        gNube.add(clave);
        final fecha = _epoch(f['fecha']);
        if (!gLocal.containsKey(clave)) {
          recordar(clave, f['datos']);
          b.insert('me_gusta', {'clave': clave, 'fecha': fecha}, conflictAlgorithm: ConflictAlgorithm.replace);
          cambio = true;
        } else {
          final l = gLocal[clave];
          if (l is! num || (l - fecha).abs() > 2) {
            b.update('me_gusta', {'fecha': fecha}, where: 'clave = ?', whereArgs: [clave]);
          }
        }
      }
      for (final clave in gLocal.keys) {
        if (!gNube.contains(clave)) {
          b.delete('me_gusta', where: 'clave = ?', whereArgs: [clave]);
          cambio = true;
        }
      }

      // ---- listas y sus canciones
      final itemsPorLista = <String, List<dynamic>>{};
      for (final i in itemsNube) {
        itemsPorLista.putIfAbsent('${i['lista_id']}', () => []).add(i);
      }
      final locales = {
        for (final l in await t.query('listas', where: 'uuid IS NOT NULL')) '${l['uuid']}': l
      };
      final nombres = {for (final f in await t.query('listas', columns: ['nombre'])) '${f['nombre']}'};
      final itemsLocal = <int, Map<String, double>>{};
      for (final f in await t.query('lista_items', where: "clave LIKE 'yt:%'")) {
        (itemsLocal[f['lista_id'] as int] ??= {})['${f['clave']}'] = (f['orden'] as num?)?.toDouble() ?? 0;
      }
      final uuids = <String>{};
      for (final l in listas) {
        final u = '${l['id']}';
        uuids.add(u);
        final fijada = l['fijada'] == true ? 1 : 0;
        final publica = l['publica'] == true ? 1 : 0;
        final enPerfil = publica == 1 && l['en_perfil'] == true ? 1 : 0;
        final tieneAjustes = (l as Map).containsKey('publica');
        final descripcion = '${l['descripcion'] ?? ''}';
        final local = locales[u];
        int lid;
        if (local != null) {
          lid = local['id'] as int;
          if (local['nombre'] != l['nombre'] || '${local['descripcion'] ?? ''}' != descripcion ||
              (local['fijada'] ?? 0) != fijada ||
              (tieneAjustes && ((local['publica'] ?? 0) != publica || (local['en_perfil'] ?? 0) != enPerfil))) {
            b.update('listas', {
              'nombre': l['nombre'], 'descripcion': descripcion, 'fijada': fijada,
              if (tieneAjustes) ...{'publica': publica, 'en_perfil': enPerfil},
            }, where: 'id = ?', whereArgs: [lid]);
            cambio = true;
          }
        } else {
          var nombre = '${l['nombre']}';
          if (nombres.contains(nombre)) nombre = '$nombre (${u.substring(0, 4)})';
          nombres.add(nombre);
          lid = await t.insert('listas', {
            'nombre': nombre, 'creada': _epoch(l['creada']), 'descripcion': descripcion,
            'fijada': fijada, 'uuid': u, 'tocada': _epoch(l['creada']),
            if (tieneAjustes) ...{'publica': publica, 'en_perfil': enPerfil},
          });
          cambio = true;
        }
        final propios = itemsLocal[lid] ?? const <String, double>{};
        final nube = <String>{};
        for (final i in itemsPorLista[u] ?? const []) {
          final clave = '${i['clave']}';
          if (!nube.add(clave)) continue;
          final orden = (i['orden'] as num?)?.toDouble() ?? 0;
          if (!propios.containsKey(clave)) {
            recordar(clave, i['datos']);
            b.insert('lista_items', {'lista_id': lid, 'clave': clave, 'orden': orden,
                'agregada': _epoch(null)}, conflictAlgorithm: ConflictAlgorithm.replace);
            cambio = true;
          } else if ((propios[clave]! - orden).abs() > 1e-9) {
            b.update('lista_items', {'orden': orden}, where: 'lista_id = ? AND clave = ?',
                whereArgs: [lid, clave]);
            cambio = true;
          }
        }
        for (final clave in propios.keys) {
          if (!nube.contains(clave)) {
            b.delete('lista_items', where: 'lista_id = ? AND clave = ?', whereArgs: [lid, clave]);
            cambio = true;
          }
        }
      }
      for (final e in locales.entries) {
        if (!uuids.contains(e.key)) {
          b.delete('lista_items', where: 'lista_id = ?', whereArgs: [e.value['id']]);
          b.delete('listas', where: 'id = ?', whereArgs: [e.value['id']]);
          cambio = true;
        }
      }

      // ---- guardados
      final sLocal = {
        for (final f in await t.query('guardados')) '${f['tipo']}|${f['id']}': f
      };
      final sNube = <String>{};
      for (final g in guardados) {
        final k = '${g['tipo']}|${g['id']}';
        sNube.add(k);
        final fecha = _epoch(g['fecha']);
        final l = sLocal[k];
        if (l == null) {
          b.insert('guardados', {'tipo': g['tipo'], 'id': g['id'], 'datos': jsonEncode(g['datos']),
              'fecha': fecha}, conflictAlgorithm: ConflictAlgorithm.replace);
          cambio = true;
          continue;
        }
        var igual = false;
        try {
          igual = _canonico(jsonDecode('${l['datos']}')) == _canonico(g['datos']);
        } catch (_) {}
        final lf = l['fecha'];
        final fechaIgual = lf is num && (lf - fecha).abs() <= 2;
        if (!igual) {
          b.insert('guardados', {'tipo': g['tipo'], 'id': g['id'], 'datos': jsonEncode(g['datos']),
              'fecha': fecha}, conflictAlgorithm: ConflictAlgorithm.replace);
          cambio = true;
        } else if (!fechaIgual) {
          b.update('guardados', {'fecha': fecha}, where: 'tipo = ? AND id = ?', whereArgs: [g['tipo'], g['id']]);
        }
      }
      for (final e in sLocal.entries) {
        if (!sNube.contains(e.key)) {
          b.delete('guardados', where: 'tipo = ? AND id = ?', whereArgs: [e.value['tipo'], e.value['id']]);
          cambio = true;
        }
      }
      await b.commit(noResult: true);

      // ---- escuchas (solo las que aun no estan)
      final vistas = {
        for (final f in await t.rawQuery('SELECT nube_id FROM reproducciones WHERE nube_id IS NOT NULL'))
          f['nube_id']
      };
      for (final e in escuchas) {
        if (vistas.contains(e['id'])) continue;
        final ya = await t.rawQuery(
            'SELECT id FROM reproducciones WHERE clave = ? AND nube_id = -1 AND ABS(fecha - ?) < 5',
            [e['clave'], _epoch(e['fecha'])]);
        if (ya.isNotEmpty) {
          await t.update('reproducciones', {'nube_id': e['id']}, where: 'id = ?', whereArgs: [ya.first['id']]);
          continue;
        }
        final clave = '${e['clave']}';
        if (e['datos'] is Map && (e['datos'] as Map).isNotEmpty && !conocidas.contains(clave)) {
          conocidas.add(clave);
          await t.insert('pistas', {'clave': clave, 'datos': jsonEncode(e['datos']),
              'actualizada': _epoch(null)}, conflictAlgorithm: ConflictAlgorithm.replace);
        }
        await t.insert('reproducciones', {
          'clave': e['clave'], 'fecha': _epoch(e['fecha']),
          'contexto': e['contexto'] == null ? '' : jsonEncode(e['contexto']), 'nube_id': e['id'],
        });
        cambio = true;
      }
    });
    return cambio;
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

/// Avisa cuando la app vuelve a primer plano.
class _VidaApp with WidgetsBindingObserver {
  _VidaApp(this.alVolver);
  final void Function() alVolver;

  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    if (estado == AppLifecycleState.resumed) alVolver();
  }
}
