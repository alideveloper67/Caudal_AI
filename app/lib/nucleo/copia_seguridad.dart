// Copia de seguridad de Caudal: todos tus datos en un archivo `.caudal`.
//
// El archivo es un ZIP con dos JSON (y las imágenes que hagan falta):
//
//   manifiesto.json   qué es, de qué versión, de qué app y un resumen
//   datos.json        la colección, los ajustes y lo demás
//   portadas/N.jpg    portadas propias de tus listas
//   fondo/fondo.jpg   la imagen de fondo (solo la lleva una copia hecha en la PC)
//
// Es el MISMO formato que escribe y lee Caudal Escritorio
// (escritorio/descargador/copia_seguridad.py): una copia del teléfono se abre
// en la PC y al revés.
//
// Lo que NO va nunca: la sesión, tokens, contraseñas ni los audios
// descargados (solo su registro).
//
// Versiones: `version` es la del formato con que se escribió y `lee_desde` la
// versión mínima de lector que la entiende. Si una versión futura añade cosas
// sin romper nada, sube `version` y deja `lee_desde` en 1.

import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';

import 'ajustes.dart';
import 'coleccion.dart';
import 'fondo_app.dart';
import 'gustos.dart';
import 'mascota_app.dart';
import 'version.dart';

/// Un problema con la copia, explicado para la persona.
class ErrorCopia implements Exception {
  const ErrorCopia(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

/// Una copia ya abierta y revisada.
class Copia {
  Copia(this.manifiesto, this.datos, this.archivos);
  final Map<String, dynamic> manifiesto;
  final Map<String, dynamic> datos;
  final Map<String, Uint8List> archivos;

  String get origen => '${(manifiesto['origen'] as Map?)?['app'] ?? ''}';
  String get creada => '${manifiesto['creada'] ?? ''}';

  Map<String, Object> resumen() => CopiaSeguridad.resumen(datos);
  String textoResumen() => CopiaSeguridad.textoResumen(resumen());

  /// «Hecha el 19/11/2026 a las 10:20 en Caudal Escritorio 2.6.1».
  String descripcion() {
    final app = switch (origen) {
      'escritorio' => 'Caudal Escritorio',
      'movil' => 'Caudal para teléfono',
      _ => 'Caudal',
    };
    final ver = '${(manifiesto['origen'] as Map?)?['version_app'] ?? ''}';
    final f = DateTime.tryParse(creada)?.toLocal();
    String dos(int n) => n.toString().padLeft(2, '0');
    final cuando = f == null
        ? 'Hecha en '
        : 'Hecha el ${dos(f.day)}/${dos(f.month)}/${f.year} a las ${dos(f.hour)}:${dos(f.minute)} en ';
    return '$cuando$app $ver'.trim();
  }
}

class CopiaSeguridad {
  CopiaSeguridad._();

  static const formato = 'caudal-copia';
  static const versionFormato = 1;
  static const leeHasta = 1;
  static const extension = '.caudal';
  static const app = 'movil';
  static const maxArchivo = 400 * 1024 * 1024;

  /// Ajustes que significan lo mismo en el teléfono y en la PC (misma lista que en el .py).
  static const ajustesComunes = [
    'region', 'calidad_audio', 'calidad_video', 'codec_video', 'crossfade', 'normalizar',
    'traducir_letra', 'acento', 'fondo', 'personaje_baila', 'super_volumen', 'ecualizador',
    'eq_bandas', 'eq_preset', 'velocidad', 'autoplay', 'sponsorblock', 'sponsorblock_videos',
    'preferir_descargado', 'aleatorio', 'repetir', 'formato_audio', 'bitrate_mp3', 'tipo_descarga',
    'letras_auto', 'descarga_inteligente', 'descarga_inteligente_gb', 'transicion_dj', 'mezcla_dj',
    'mezcla_dj_seg', 'mezcla_dj_graves', 'apagado_suave',
  ];

  /// Estados internos de paso (no son ajustes de la persona).
  static const ajustesFuera = {'gamer_ligero_previo', 'gamer_eq_previo'};

  /// Lo del «estado» de la colección que vale la pena llevarse.
  static const estadoCopiable = ['saltos', 'mezclas_dj'];

  /// Las claves del modo estudio en el teléfono (`estudio.<clave>`).
  static const _estudioConfig = [
    'perfil', 'estilo', 'ciclo', 'enf', 'desc', 'rondas', 'largo', 'accion', 'atenuar', 'candado',
    'calido', 'brillo', 'pantalla', 'capas',
  ];

  static const _tablasReemplazables = [
    'me_gusta', 'lista_items', 'listas', 'reproducciones', 'contextos_recientes', 'guardados', 'busquedas',
  ];

  static dynamic _json(Object? texto, [dynamic defecto]) {
    if (texto == null || '$texto'.isEmpty) return defecto;
    try {
      return jsonDecode('$texto');
    } catch (_) {
      return defecto;
    }
  }

  static double _num(Object? v, [double defecto = 0]) =>
      v is num ? v.toDouble() : (double.tryParse('${v ?? ''}') ?? defecto);

  static String nombreSugerido({bool automatica = false, DateTime? ahora}) {
    final f = ahora ?? DateTime.now();
    String dos(int n) => n.toString().padLeft(2, '0');
    return '${automatica ? 'Caudal-auto' : 'Caudal-copia'}-${f.year}-${dos(f.month)}-${dos(f.day)}-'
        '${dos(f.hour)}${dos(f.minute)}$extension';
  }

  // ==================================================================== exportar

  static Future<(Map<String, dynamic>, Map<String, Uint8List>)> _datosColeccion(Coleccion col) async {
    final db = col.db;
    final meGusta = [
      for (final f in await db.rawQuery('SELECT clave, fecha FROM me_gusta ORDER BY fecha DESC'))
        {'clave': f['clave'], 'fecha': f['fecha']}
    ];
    final listas = <Map<String, dynamic>>[];
    final portadas = <String, Uint8List>{};
    var i = 0;
    for (final l in await db.rawQuery('SELECT * FROM listas ORDER BY id')) {
      i++;
      final id = l['id'] as int;
      var uuid = '${l['uuid'] ?? ''}';
      if (uuid.isEmpty) {
        uuid = nuevoUuid();
        await db.update('listas', {'uuid': uuid}, where: 'id = ?', whereArgs: [id]);
      }
      final items = [
        for (final f in await db.rawQuery(
            'SELECT clave, orden, agregada FROM lista_items WHERE lista_id = ? ORDER BY orden', [id]))
          {'clave': f['clave'], 'orden': f['orden'], 'agregada': f['agregada']}
      ];
      String? portada;
      final ref = '${l['portada'] ?? ''}';
      Uint8List? bytes;
      final blob = l['portada_datos'];
      if (blob is List<int>) {
        bytes = blob is Uint8List ? blob : Uint8List.fromList(blob);
      } else if (ref.isNotEmpty && PortadasMem.esRef(ref)) {
        bytes = PortadasMem.bytes(ref);
      } else if (ref.isNotEmpty && !kIsWeb) {
        try {
          final a = File(ref);
          if (await a.exists()) bytes = await a.readAsBytes();
        } catch (_) {}
      }
      if (bytes != null && bytes.isNotEmpty) {
        portada = 'portadas/$i.jpg';
        portadas[portada] = bytes;
      }
      listas.add({
        'uuid': uuid, 'nombre': l['nombre'], 'descripcion': l['descripcion'] ?? '',
        'fijada': (l['fijada'] ?? 0) == 1, 'color': '', 'creada': l['creada'], 'tocada': l['tocada'] ?? 0,
        'publica': (l['publica'] ?? 0) == 1, 'en_perfil': (l['en_perfil'] ?? 0) == 1,
        'portada': portada, 'items': items,
      });
    }
    final escuchas = [
      for (final f in await db.rawQuery('SELECT clave, fecha, contexto FROM reproducciones ORDER BY fecha'))
        {'clave': f['clave'], 'fecha': f['fecha'], 'contexto': _json(f['contexto'])}
    ];
    final contextos = [
      for (final f in await db.rawQuery('SELECT * FROM contextos_recientes ORDER BY fecha DESC'))
        {'tipo': f['tipo'], 'id': f['id'], 'datos': _json(f['datos'], {}), 'fecha': f['fecha']}
    ];
    final guardados = [
      for (final f in await db.rawQuery('SELECT * FROM guardados ORDER BY fecha DESC'))
        {'tipo': f['tipo'], 'id': f['id'], 'datos': _json(f['datos'], {}), 'fecha': f['fecha']}
    ];
    final busquedas = [
      for (final f in await db.rawQuery('SELECT texto, fecha FROM busquedas ORDER BY fecha DESC'))
        {'texto': f['texto'], 'fecha': f['fecha']}
    ];
    final descargas = <Map<String, dynamic>>[];
    for (final f in await db.rawQuery('SELECT * FROM descargas ORDER BY id')) {
      final extra = _json(f['datos'], {});
      final d = extra is Map ? Map<String, dynamic>.from(extra) : <String, dynamic>{};
      d.remove('archivo');
      descargas.add({
        'ref': 'local:${f['id']}', 'video_id': f['video_id'] ?? '', 'url': f['url'] ?? '',
        'titulo': f['titulo'] ?? '', 'artista': f['artista'] ?? '', 'plataforma': '',
        'archivo': f['archivo'] ?? '', 'es_audio': f['es_audio'] == 1, 'tamano': f['tamano'] ?? 0,
        'duracion': f['duracion'] ?? 0, 'calidad': f['calidad'] ?? '', 'caratula': f['caratula'] ?? '',
        'estado': 'completada', 'fecha': f['fecha'] ?? 0, 'datos': d,
      });
    }
    final usadas = <String>{
      for (final g in meGusta) '${g['clave']}',
      for (final e in escuchas) '${e['clave']}',
      for (final l in listas)
        for (final it in l['items'] as List) '${(it as Map)['clave']}',
    }..removeWhere((c) => c.isEmpty || c.startsWith('local:'));
    final enLinea = usadas.toList()..sort();
    final pistas = <String, dynamic>{};
    for (var k = 0; k < enLinea.length; k += 400) {
      final tanda = enLinea.sublist(k, min(k + 400, enLinea.length));
      final filas = await db.query('pistas', columns: ['clave', 'datos'],
          where: 'clave IN (${List.filled(tanda.length, '?').join(',')})', whereArgs: tanda);
      for (final f in filas) {
        final d = _json(f['datos']);
        if (d is Map) pistas['${f['clave']}'] = Map<String, dynamic>.from(d)..remove('archivo');
      }
    }
    final estado = <String, dynamic>{};
    for (final k in estadoCopiable) {
      final v = await col.estado(k);
      if (v != null) estado[k] = v;
    }
    return (
      {
        'pistas': pistas, 'me_gusta': meGusta, 'listas': listas, 'escuchas': escuchas,
        'contextos': contextos, 'guardados': guardados, 'busquedas': busquedas,
        'descargas': descargas, 'estado': estado,
      },
      portadas,
    );
  }

  static Map<String, dynamic> _datosAjustes(Ajustes a) {
    final comunes = <String, dynamic>{}, propios = <String, dynamic>{};
    for (final e in Ajustes.defectos.entries) {
      final k = e.key;
      if (ajustesFuera.contains(k)) continue;
      final Object v = k == 'eq_bandas'
          ? a.bandasEq
          : switch (e.value) {
              bool() => a.sino(k),
              int() => a.entero(k),
              double() => a.decimal(k),
              _ => a.texto(k),
            };
      (ajustesComunes.contains(k) ? comunes : propios)[k] = v;
    }
    return {'comunes': comunes, 'movil': propios};
  }

  static Map<String, dynamic>? _datosEstudio(SharedPreferences prefs) {
    final notas = <Map<String, dynamic>>[];
    final l = _json(prefs.getString('estudio.notas'), []);
    if (l is List) {
      for (final n in l) {
        if (n is Map && '${n['texto'] ?? ''}'.isNotEmpty) {
          notas.add({'id': '${n['id'] ?? ''}', 'texto': '${n['texto']}', 'fecha': '${n['fecha'] ?? ''}'});
        }
      }
    }
    final dias = <String, int>{};
    final d = _json(prefs.getString('estudio.dias'), {});
    if (d is Map) {
      for (final e in d.entries) {
        if (e.value is num) dias['${e.key}'] = ((e.value as num) / 1000).round();
      }
    }
    final cfg = <String, Object>{
      for (final k in _estudioConfig)
        if (prefs.get('estudio.$k') != null) k: prefs.get('estudio.$k')!,
    };
    if (notas.isEmpty && dias.isEmpty && cfg.isEmpty) return null;
    return {'notas': notas, 'dias': dias, 'config_movil': cfg};
  }

  static Map<String, dynamic>? _datosGustos(SharedPreferences prefs, String cuenta) {
    final lista = Gustos.leerLista(prefs.getString('gustos.lista.$cuenta'));
    final elegidos = prefs.getBool('gustos.listo.$cuenta') ?? false;
    if (lista.isEmpty && !elegidos) return null;
    return {'artistas': [for (final a in lista) a.toJson()], 'elegidos': elegidos};
  }

  /// Cuántas cosas trae una copia (sale de los datos, no del manifiesto).
  static Map<String, Object> resumen(Map<String, dynamic> datos) {
    final col = (datos['coleccion'] as Map?) ?? const {};
    List l(Object? x) => x is List ? x : const [];
    final listas = l(col['listas']);
    final estudio = (datos['estudio'] as Map?) ?? const {};
    final ajustes = (datos['ajustes'] as Map?) ?? const {};
    var nAjustes = 0;
    for (final v in ajustes.values) {
      if (v is Map) nAjustes += v.length;
    }
    return {
      'me_gusta': l(col['me_gusta']).length,
      'listas': listas.length,
      'canciones_en_listas': listas.fold<int>(0, (s, x) => s + l((x as Map)['items']).length),
      'escuchas': l(col['escuchas']).length,
      'guardados': l(col['guardados']).length,
      'descargas': l(col['descargas']).length,
      'busquedas': l(col['busquedas']).length,
      'notas': l(estudio['notas']).length,
      'dias_estudio': (estudio['dias'] as Map?)?.length ?? 0,
      'ajustes': nAjustes,
      'ecualizador': ((ajustes['comunes'] as Map?) ?? const {}).containsKey('eq_bandas'),
      'mascota': '${datos['mascota'] ?? ''}'.isNotEmpty,
      'fondo': '${(datos['fondo'] as Map?)?['imagen'] ?? ''}'.isNotEmpty,
      'gustos': l((datos['gustos'] as Map?)?['artistas']).length,
    };
  }

  static String _miles(int n) {
    final s = '$n';
    final b = StringBuffer();
    for (var i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) b.write('.');
      b.write(s[i]);
    }
    return '$b';
  }

  /// «142 canciones en me gusta · 12 listas (310 canciones) · …».
  static String textoResumen(Map<String, Object> r) {
    final partes = <String>[];
    void poner(String k, String uno, String varios) {
      final n = r[k] as int? ?? 0;
      if (n > 0) partes.add('${_miles(n)} ${n == 1 ? uno : varios}');
    }

    poner('me_gusta', 'canción en me gusta', 'canciones en me gusta');
    final nl = r['listas'] as int? ?? 0;
    if (nl > 0) {
      final c = r['canciones_en_listas'] as int? ?? 0;
      partes.add('${_miles(nl)} ${nl == 1 ? 'lista' : 'listas'} (${_miles(c)} ${c == 1 ? 'canción' : 'canciones'})');
    }
    poner('escuchas', 'escucha en tu historial', 'escuchas en tu historial');
    poner('guardados', 'álbum, lista o artista guardado', 'álbumes, listas y artistas guardados');
    poner('descargas', 'descarga registrada', 'descargas registradas');
    poner('busquedas', 'búsqueda reciente', 'búsquedas recientes');
    poner('notas', 'nota del modo estudio', 'notas del modo estudio');
    poner('dias_estudio', 'día de estudio', 'días de estudio');
    poner('gustos', 'artista favorito', 'artistas favoritos');
    if ((r['ajustes'] as int? ?? 0) > 0) {
      partes.add('tus ajustes${r['ecualizador'] == true ? ' y el ecualizador' : ''}');
    }
    if (r['mascota'] == true) partes.add('tu mascota');
    if (r['fondo'] == true) partes.add('tu imagen de fondo');
    return partes.isEmpty ? 'La copia está vacía.' : partes.join(' · ');
  }

  /// Arma la copia y devuelve los bytes del `.caudal`. [mascota] y [fondo]
  /// por defecto salen de lo que tiene la app abierta.
  static Future<Uint8List> crear(Coleccion col,
      {Ajustes? ajustes, String cuenta = '', String? mascota, Map<String, Object?>? fondo}) async {
    final prefs = await SharedPreferences.getInstance();
    final (coleccion, portadas) = await _datosColeccion(col);
    mascota ??= MascotaApp.i.clave;
    if (fondo == null && FondoApp.i.activo) {
      fondo = {'visible': FondoApp.i.visible, 'desenfoque': FondoApp.i.desenfoque, 'imagen': null};
    }
    final datos = <String, dynamic>{
      'coleccion': coleccion,
      'ajustes': ajustes == null ? <String, dynamic>{} : _datosAjustes(ajustes),
      'mascota': mascota.isEmpty ? null : mascota,
      'fondo': fondo,
      'estudio': _datosEstudio(prefs),
      'gustos': _datosGustos(prefs, cuenta),
    };
    final manifiesto = {
      'formato': formato,
      'version': versionFormato,
      'lee_desde': 1,
      'creada': '${DateTime.now().toUtc().toIso8601String().split('.').first}Z',
      'origen': {'app': app, 'version_app': versionApp, 'sistema': kIsWeb ? 'web' : Platform.operatingSystem},
      'resumen': resumen(datos),
    };
    final zip = Archive()
      ..addFile(ArchiveFile.string('manifiesto.json', const JsonEncoder.withIndent(' ').convert(manifiesto)))
      ..addFile(ArchiveFile.string('datos.json', jsonEncode(datos)));
    for (final e in portadas.entries) {
      zip.addFile(ArchiveFile.bytes(e.key, e.value));
    }
    return ZipEncoder().encodeBytes(zip);
  }

  // ==================================================================== leer

  static const _danada = 'La copia está dañada (puede que no se terminara de copiar). Prueba con otra copia.';
  static const _noEsCopia = 'Este archivo no es una copia de seguridad de Caudal.';

  /// Lee y revisa una copia. Lanza [ErrorCopia] con un mensaje claro.
  static Copia abrir(Uint8List contenido) {
    if (contenido.isEmpty) throw const ErrorCopia('El archivo está vacío: la copia no se terminó de guardar.');
    if (contenido.length > maxArchivo) {
      throw const ErrorCopia('Ese archivo es demasiado grande para ser una copia de Caudal.');
    }
    Archive zip;
    try {
      zip = ZipDecoder().decodeBytes(contenido, verify: true);
    } catch (_) {
      throw const ErrorCopia('Este archivo no es una copia de Caudal, o está dañado.');
    }
    Uint8List? leer(String nombre) {
      final f = zip.findFile(nombre);
      if (f == null) return null;
      try {
        return f.readBytes();
      } catch (_) {
        throw const ErrorCopia(_danada);
      }
    }

    if (zip.findFile('manifiesto.json') == null) {
      if (zip.isEmpty) throw const ErrorCopia('Este archivo no es una copia de Caudal, o está dañado.');
      throw const ErrorCopia(_noEsCopia);
    }
    dynamic manifiesto;
    try {
      manifiesto = jsonDecode(utf8.decode(leer('manifiesto.json')!));
    } on ErrorCopia {
      rethrow;
    } catch (_) {
      throw const ErrorCopia(_danada);
    }
    if (manifiesto is! Map || manifiesto['formato'] != formato) throw const ErrorCopia(_noEsCopia);
    final leeDesde = int.tryParse('${manifiesto['lee_desde'] ?? manifiesto['version'] ?? 1}') ?? 999;
    if (leeDesde > leeHasta) {
      throw const ErrorCopia('Esta copia se hizo con una versión más nueva de Caudal. '
          'Actualiza Caudal en este teléfono y vuelve a intentarlo.');
    }
    final crudo = leer('datos.json');
    if (crudo == null) {
      throw const ErrorCopia('La copia está incompleta: le falta lo más importante. Prueba con otra copia.');
    }
    dynamic datos;
    try {
      datos = jsonDecode(utf8.decode(crudo));
    } catch (_) {
      throw const ErrorCopia(_danada);
    }
    if (datos is! Map) throw const ErrorCopia(_danada);
    final archivos = <String, Uint8List>{};
    for (final f in zip.files) {
      if (f.isFile && (f.name.startsWith('portadas/') || f.name.startsWith('fondo/'))) {
        final b = leer(f.name);
        if (b != null) archivos[f.name] = b;
      }
    }
    return Copia(Map<String, dynamic>.from(manifiesto), Map<String, dynamic>.from(datos), archivos);
  }

  // ==================================================================== restaurar la colección

  static bool _existeArchivo(String ruta) {
    if (kIsWeb || ruta.isEmpty) return false;
    if (ruta.startsWith('http')) return true;
    try {
      return File(ruta).existsSync();
    } catch (_) {
      return false;
    }
  }

  static Map<String, dynamic> _pistaDeDescarga(Map d, String clave) {
    final base = d['datos'] is Map ? Map<String, dynamic>.from(d['datos'] as Map) : <String, dynamic>{};
    final artista = '${d['artista'] ?? ''}';
    base.addAll({
      'tipo': 'pista',
      'clave': clave,
      'video_id': '${d['video_id'] ?? ''}',
      'titulo': '${d['titulo'] ?? ''}'.isNotEmpty ? d['titulo'] : (base['titulo'] ?? 'Sin título'),
      'artista': artista.isNotEmpty ? artista : (base['artista'] ?? ''),
      'artistas': base['artistas'] ?? [if (artista.isNotEmpty) {'nombre': artista, 'id': ''}],
      'duracion': (d['duracion'] as num?)?.toInt() ?? 0,
      'miniatura': '${d['caratula'] ?? ''}'.isNotEmpty ? d['caratula'] : (base['miniatura'] ?? ''),
    });
    for (final k in ['archivo', 'descarga_id', 'es_audio', 'tamano', 'calidad', 'fecha', 'url']) {
      base.remove(k);
    }
    return base;
  }

  /// Mete la colección de la copia. [modo]: 'juntar' (sin duplicar) o
  /// 'reemplazar'. Devuelve lo que entró de nuevo. Las descargas nunca se borran.
  static Future<Map<String, int>> restaurarColeccion(Coleccion col, Copia copia,
      {String modo = 'juntar', bool Function(String ruta)? existe, bool? anotar}) async {
    if (modo != 'juntar' && modo != 'reemplazar') throw ArgumentError(modo);
    existe ??= _existeArchivo;
    anotar ??= col.alHaberPendientes != null;
    final datos = (copia.datos['coleccion'] as Map?) ?? const {};
    List lista(Object? x) => x is List ? x : const [];
    final cuenta = {
      'me_gusta': 0, 'listas': 0, 'canciones_en_listas': 0, 'escuchas': 0, 'guardados': 0,
      'descargas': 0, 'busquedas': 0,
    };
    final portadasPendientes = <(int, Uint8List)>[];
    final portadasViejas = <String>[];
    final ahora = DateTime.now().millisecondsSinceEpoch / 1000.0;

    await col.db.transaction((t) async {
      Future<void> nota(String op, Object d) async {
        if (anotar!) await t.insert('pendientes', {'op': op, 'datos': jsonEncode(d), 'creada': ahora});
      }

      // ---- descargas: el registro que falte; ref de la copia -> clave aquí
      final mapa = <String, String>{};
      final pistasDesc = <String, Map<String, dynamic>>{};
      for (final x in lista(datos['descargas'])) {
        if (x is! Map || '${x['ref'] ?? ''}'.isEmpty) continue;
        final archivo = '${x['archivo'] ?? ''}';
        final url = '${x['url'] ?? ''}';
        final vid = '${x['video_id'] ?? ''}';
        final esAudio = x['es_audio'] == true ? 1 : 0;
        List<Map<String, Object?>> f = const [];
        if (archivo.isNotEmpty) f = await t.query('descargas', columns: ['id'], where: 'archivo = ?', whereArgs: [archivo]);
        if (f.isEmpty && url.isNotEmpty) {
          f = await t.query('descargas', columns: ['id'],
              where: "url = ? AND es_audio = ? AND COALESCE(titulo,'') = ?", whereArgs: [url, esAudio, '${x['titulo'] ?? ''}']);
        }
        final ref = '${x['ref']}';
        final estaAqui = archivo.isNotEmpty && existe!(archivo);
        if (f.isEmpty && copia.origen != app && !estaAqui) {
          // una descarga de la PC cuyo archivo no está aquí: no se apunta (sería una
          // fila fantasma), pero la canción sigue en tus listas y me gusta desde internet
          if (vid.isNotEmpty) {
            mapa[ref] = 'yt:$vid';
            pistasDesc['yt:$vid'] = _pistaDeDescarga(x, 'yt:$vid');
          }
          continue;
        }
        int id;
        if (f.isEmpty) {
          if ('${x['estado'] ?? 'completada'}' != 'completada') continue;
          id = await t.insert('descargas', {
            'video_id': vid, 'url': url, 'titulo': '${x['titulo'] ?? ''}', 'artista': '${x['artista'] ?? ''}',
            'archivo': archivo, 'es_audio': esAudio, 'tamano': (x['tamano'] as num?)?.toInt() ?? 0,
            'duracion': (x['duracion'] as num?)?.toInt() ?? 0, 'calidad': '${x['calidad'] ?? ''}',
            'caratula': '${x['caratula'] ?? ''}', 'datos': jsonEncode(x['datos'] is Map ? x['datos'] : {}),
            'fecha': _num(x['fecha'], ahora),
          });
          cuenta['descargas'] = cuenta['descargas']! + 1;
        } else {
          id = f.first['id'] as int;
        }
        if (estaAqui) {
          mapa[ref] = 'local:$id';
        } else if (vid.isNotEmpty) {
          final clave = 'yt:$vid';
          mapa[ref] = clave;
          pistasDesc[clave] = _pistaDeDescarga(x, clave);
        } else {
          mapa[ref] = 'local:$id';
        }
      }
      String? claveAqui(Object? c) {
        if (c is! String || c.isEmpty) return null;
        if (c.startsWith('local:')) return mapa[c]; // una descarga que no vino en la copia: no se inventa
        return c;
      }

      // ---- reemplazar: se vacía lo de antes (y se avisa a la cuenta)
      if (modo == 'reemplazar') {
        if (anotar!) {
          for (final f in await t.rawQuery("SELECT clave FROM me_gusta WHERE clave LIKE 'yt:%'")) {
            await nota('me_gusta_quitar', {'clave': f['clave']});
          }
          for (final f in await t.rawQuery("SELECT uuid FROM listas WHERE uuid IS NOT NULL AND uuid != ''")) {
            await nota('lista_borrar', {'uuid': f['uuid']});
          }
          for (final f in await t.rawQuery('SELECT tipo, id FROM guardados')) {
            await nota('guardado_quitar', {'tipo': f['tipo'], 'id': f['id']});
          }
        }
        for (final f in await t.rawQuery('SELECT portada FROM listas WHERE portada IS NOT NULL')) {
          portadasViejas.add('${f['portada']}');
        }
        for (final tabla in _tablasReemplazables) {
          await t.delete(tabla);
        }
      }

      // ---- canciones
      final pistas = <String, dynamic>{...?(datos['pistas'] as Map?)?.cast<String, dynamic>()};
      for (final e in pistasDesc.entries) {
        pistas.putIfAbsent(e.key, () => e.value);
      }
      final conflicto = modo == 'reemplazar' ? ConflictAlgorithm.replace : ConflictAlgorithm.ignore;
      for (final e in pistas.entries) {
        if (e.value is! Map || e.key.isEmpty || e.key.startsWith('local:')) continue;
        final d = Map<String, dynamic>.from(e.value as Map)
          ..remove('archivo')
          ..['clave'] = e.key;
        await t.insert('pistas', {'clave': e.key, 'datos': jsonEncode(d), 'actualizada': ahora},
            conflictAlgorithm: conflicto);
      }
      Map<String, dynamic> datosPista(String c) {
        final d = pistas[c];
        return d is Map ? Coleccion.paraNube(Map<String, dynamic>.from(d)) : {'clave': c};
      }

      // ---- me gusta
      for (final g in lista(datos['me_gusta'])) {
        final c = claveAqui(g is Map ? g['clave'] : null);
        if (c == null) continue;
        final n = await t.insert('me_gusta', {'clave': c, 'fecha': _num((g as Map)['fecha'], ahora)},
            conflictAlgorithm: ConflictAlgorithm.ignore);
        if (n > 0) {
          cuenta['me_gusta'] = cuenta['me_gusta']! + 1;
          if (c.startsWith('yt:')) await nota('me_gusta_poner', {'clave': c, 'datos': datosPista(c)});
        }
      }

      // ---- listas (la misma por uuid o, si no, por nombre)
      for (final x in lista(datos['listas'])) {
        if (x is! Map || '${x['nombre'] ?? ''}'.trim().isEmpty) continue;
        final nombre = '${x['nombre']}'.trim();
        var uuid = '${x['uuid'] ?? ''}';
        if (uuid.isEmpty) uuid = nuevoUuid();
        var f = await t.query('listas', columns: ['id', 'uuid', 'portada', 'portada_datos'],
            where: 'uuid = ?', whereArgs: [uuid]);
        if (f.isEmpty) {
          f = await t.query('listas', columns: ['id', 'uuid', 'portada', 'portada_datos'],
              where: 'nombre = ?', whereArgs: [nombre]);
        }
        int id;
        bool teniaPortada;
        if (f.isEmpty) {
          final publica = x['publica'] == true;
          id = await t.insert('listas', {
            'nombre': nombre, 'creada': _num(x['creada'], ahora), 'descripcion': '${x['descripcion'] ?? ''}',
            'fijada': x['fijada'] == true ? 1 : 0, 'tocada': _num(x['tocada']), 'uuid': uuid,
            'publica': publica ? 1 : 0, 'en_perfil': publica && x['en_perfil'] == true ? 1 : 0,
          });
          teniaPortada = false;
          cuenta['listas'] = cuenta['listas']! + 1;
          await nota('lista_poner', {
            'uuid': uuid, 'nombre': nombre, 'descripcion': '${x['descripcion'] ?? ''}',
            'fijada': x['fijada'] == true,
          });
        } else {
          id = f.first['id'] as int;
          final u = '${f.first['uuid'] ?? ''}';
          if (u.isNotEmpty) uuid = u;
          teniaPortada = '${f.first['portada'] ?? ''}'.isNotEmpty;
        }
        final ya = {
          for (final r in await t.query('lista_items', columns: ['clave'], where: 'lista_id = ?', whereArgs: [id]))
            '${r['clave']}'
        };
        final m = await t.rawQuery('SELECT COALESCE(MAX(orden), 0) m FROM lista_items WHERE lista_id = ?', [id]);
        var orden = (m.first['m'] as num).toDouble();
        final items = [for (final it in lista(x['items'])) if (it is Map) it]
          ..sort((a, b) => _num(a['orden']).compareTo(_num(b['orden'])));
        final subir = <Map<String, dynamic>>[];
        for (final it in items) {
          final c = claveAqui(it['clave']);
          if (c == null || !ya.add(c)) continue;
          orden += 1;
          await t.insert('lista_items', {'lista_id': id, 'clave': c, 'orden': orden, 'agregada': _num(it['agregada'], ahora)},
              conflictAlgorithm: ConflictAlgorithm.ignore);
          cuenta['canciones_en_listas'] = cuenta['canciones_en_listas']! + 1;
          if (c.startsWith('yt:')) subir.add({'clave': c, 'datos': datosPista(c), 'orden': orden});
        }
        if (subir.isNotEmpty) await nota('items_poner', {'uuid': uuid, 'items': subir});
        final portada = '${x['portada'] ?? ''}';
        if (portada.isNotEmpty && copia.archivos.containsKey(portada) && !teniaPortada) {
          portadasPendientes.add((id, copia.archivos[portada]!));
        }
      }

      // ---- escuchas (misma canción a la misma hora = la misma escucha)
      final vistas = <String>{};
      if (modo == 'juntar') {
        for (final f in await t.rawQuery('SELECT clave, fecha FROM reproducciones')) {
          vistas.add('${f['clave']}|${_num(f['fecha']).round()}');
        }
      }
      for (final e in lista(datos['escuchas'])) {
        if (e is! Map) continue;
        final c = claveAqui(e['clave']);
        final fecha = _num(e['fecha']);
        if (c == null || fecha == 0 || !vistas.add('$c|${fecha.round()}')) continue;
        final ctx = e['contexto'];
        // nube_id -1: no se vuelve a subir a la cuenta
        await t.insert('reproducciones', {
          'clave': c, 'fecha': fecha, 'contexto': ctx == null ? '' : jsonEncode(ctx), 'nube_id': -1,
        });
        cuenta['escuchas'] = cuenta['escuchas']! + 1;
      }

      for (final x in lista(datos['contextos'])) {
        if (x is! Map || x['tipo'] == null || x['id'] == null) continue;
        final previo = await t.query('contextos_recientes', columns: ['fecha'],
            where: 'tipo = ? AND id = ?', whereArgs: ['${x['tipo']}', '${x['id']}']);
        if (previo.isEmpty || _num(previo.first['fecha']) < _num(x['fecha'])) {
          await t.insert('contextos_recientes', {
            'tipo': '${x['tipo']}', 'id': '${x['id']}', 'datos': jsonEncode(x['datos'] ?? {}),
            'fecha': _num(x['fecha'], ahora),
          }, conflictAlgorithm: ConflictAlgorithm.replace);
        }
      }

      for (final g in lista(datos['guardados'])) {
        if (g is! Map || '${g['tipo'] ?? ''}'.isEmpty || '${g['id'] ?? ''}'.isEmpty) continue;
        final el = g['datos'] ?? {};
        final n = await t.insert('guardados', {
          'tipo': '${g['tipo']}', 'id': '${g['id']}', 'datos': jsonEncode(el), 'fecha': _num(g['fecha'], ahora),
        }, conflictAlgorithm: ConflictAlgorithm.ignore);
        if (n > 0) {
          cuenta['guardados'] = cuenta['guardados']! + 1;
          await nota('guardado_poner', {'tipo': '${g['tipo']}', 'id': '${g['id']}', 'datos': el});
        }
      }

      for (final b in lista(datos['busquedas'])) {
        final texto = b is Map ? '${b['texto'] ?? ''}'.trim() : '';
        if (texto.isEmpty) continue;
        final n = await t.insert('busquedas', {'texto': texto, 'fecha': _num((b as Map)['fecha'], ahora)},
            conflictAlgorithm: ConflictAlgorithm.ignore);
        if (n > 0) cuenta['busquedas'] = cuenta['busquedas']! + 1;
      }
      await t.rawDelete('DELETE FROM busquedas WHERE texto NOT IN '
          '(SELECT texto FROM busquedas ORDER BY fecha DESC LIMIT 30)');

      await _restaurarEstado(t, (datos['estado'] as Map?) ?? const {}, copia.origen, modo);
    });

    for (final ruta in portadasViejas) {
      if (ruta.isEmpty || PortadasMem.esRef(ruta) || kIsWeb) continue;
      try {
        final a = File(ruta);
        if (await a.exists()) await a.delete();
      } catch (_) {}
    }
    for (final (id, bytes) in portadasPendientes) {
      try {
        await col.ponerPortadaLista(id, bytes);
      } catch (_) {
        // una portada que no se abre no frena lo demás
      }
    }
    await col.refrescarMemoria();
    if (anotar) col.alHaberPendientes?.call();
    return cuenta;
  }

  static Future<void> _restaurarEstado(Transaction t, Map estado, String origen, String modo) async {
    Future<dynamic> leer(String k) async {
      final f = await t.query('estado', where: 'clave = ?', whereArgs: [k]);
      return f.isEmpty ? null : _json(f.first['valor']);
    }

    Future<void> poner(String k, Object? v) => t.insert('estado', {'clave': k, 'valor': jsonEncode(v)},
        conflictAlgorithm: ConflictAlgorithm.replace);

    for (final k in estadoCopiable) {
      if (!estado.containsKey(k)) continue;
      final v = estado[k];
      if (k == 'saltos') {
        if (v is! Map) continue;
        final previo = modo == 'juntar' ? await leer(k) : null;
        final actual = previo is Map ? Map<String, dynamic>.from(previo) : <String, dynamic>{};
        if (origen == app && actual.isEmpty) {
          await poner(k, v);
          continue;
        }
        // de otro equipo solo sirven los saltos por canción
        final canciones = Map<String, dynamic>.from((actual['canciones'] as Map?) ?? {});
        for (final e in ((v['canciones'] as Map?) ?? {}).entries) {
          canciones['${e.key}'] = max(_num(canciones['${e.key}']).toInt(), _num(e.value).toInt());
        }
        actual['canciones'] = canciones;
        actual.putIfAbsent('artistas', () => <String, dynamic>{});
        await poner(k, actual);
      } else if (origen == app && (modo == 'reemplazar' || await leer(k) == null)) {
        await poner(k, v);
      }
    }
  }

  // ==================================================================== restaurar lo demás

  /// Ajustes, ecualizador, modo estudio, gustos, mascota y fondo. Devuelve lo
  /// que se aplicó. [conCuenta]: los gustos quedan para subirse a la cuenta.
  static Future<List<String>> restaurarExtras(Copia copia,
      {String modo = 'juntar', Ajustes? ajustes, String cuenta = '', bool conAjustes = true,
      bool conCuenta = false}) async {
    final prefs = await SharedPreferences.getInstance();
    final datos = copia.datos;
    final hecho = <String>[];
    if (conAjustes && ajustes != null && await _restaurarAjustes(ajustes, (datos['ajustes'] as Map?) ?? const {}, copia.origen)) {
      hecho.add('ajustes');
    }
    if (await _restaurarEstudio(prefs, datos['estudio'], modo)) hecho.add('estudio');
    if (await _restaurarGustos(prefs, datos['gustos'], modo, cuenta, conCuenta)) hecho.add('gustos');
    if (conAjustes) {
      final m = datos['mascota'];
      if (m is String && cuenta.isNotEmpty) {
        // elegir() respeta los permisos de la cuenta; aquí se deja guardada por si se puede
        await MascotaApp.i.elegir(m);
        if (MascotaApp.i.clave == m) {
          hecho.add('mascota');
        } else {
          await prefs.setString('mascota_app_$cuenta', m);
        }
      }
      final f = datos['fondo'];
      if (f is Map && FondoApp.i.activo && (f['visible'] != null || f['desenfoque'] != null)) {
        await FondoApp.i.ajustar(null,
            visible: (f['visible'] as num?)?.toInt(), desenfoque: (f['desenfoque'] as num?)?.toInt(), guardar: true);
        hecho.add('fondo');
      }
    }
    return hecho;
  }

  static Future<bool> _restaurarAjustes(Ajustes a, Map bloque, String origen) async {
    final valores = <String, dynamic>{...?(bloque['comunes'] as Map?)?.cast<String, dynamic>()};
    if (origen == app) valores.addAll({...?(bloque['movil'] as Map?)?.cast<String, dynamic>()});
    final aplicar = <String, Object>{};
    for (final e in valores.entries) {
      final k = e.key;
      final defecto = Ajustes.defectos[k];
      if (defecto == null || ajustesFuera.contains(k)) continue;
      var v = e.value;
      if (k == 'eq_bandas') {
        if (v is String) v = _json(v);
        if (v is! List) continue;
        aplicar[k] = [for (final x in v.take(10)) _num(x).round()];
        continue;
      }
      if (k == 'calidad_video' && v == '4320') v = '2160'; // el teléfono llega hasta 4K
      switch (defecto) {
        case bool():
          if (v is bool) aplicar[k] = v;
        case int():
          if (v is num) aplicar[k] = v.round();
        case double():
          if (v is num) aplicar[k] = v.toDouble();
        default:
          if (v is String || v is num) aplicar[k] = '$v';
      }
    }
    var i = 0;
    for (final e in aplicar.entries) {
      i++;
      await a.poner(e.key, e.value, avisar: i == aplicar.length);
    }
    return aplicar.isNotEmpty;
  }

  static Future<bool> _restaurarEstudio(SharedPreferences prefs, Object? bloque, String modo) async {
    if (bloque is! Map) return false;
    final previas = modo == 'juntar' ? _json(prefs.getString('estudio.notas'), []) : [];
    final lista = <Map<String, dynamic>>[
      for (final n in (previas is List ? previas : const []))
        if (n is Map) Map<String, dynamic>.from(n)
    ];
    final vistas = {for (final n in lista) '${'${n['texto']}'.trim()}|${_corta('${n['fecha']}')}'};
    final ids = {for (final n in lista) n['id']};
    for (final n in (bloque['notas'] is List ? bloque['notas'] as List : const [])) {
      if (n is! Map || '${n['texto'] ?? ''}'.isEmpty) continue;
      final texto = '${n['texto']}';
      final fecha = DateTime.tryParse('${n['fecha'] ?? ''}') ?? DateTime.now();
      if (!vistas.add('${texto.trim()}|${_corta(fecha.toIso8601String())}')) continue;
      // en el teléfono el id es un número
      var id = int.tryParse('${n['id'] ?? ''}') ?? fecha.microsecondsSinceEpoch;
      while (ids.contains(id)) {
        id++;
      }
      ids.add(id);
      lista.add({'id': id, 'texto': texto.length > 4000 ? texto.substring(0, 4000) : texto,
          'fecha': fecha.toIso8601String()});
    }
    lista.sort((a, b) => '${b['fecha']}'.compareTo('${a['fecha']}'));
    await prefs.setString('estudio.notas', jsonEncode(lista.take(300).toList()));
    final previos = modo == 'juntar' ? _json(prefs.getString('estudio.dias'), {}) : {};
    final dias = <String, int>{
      for (final e in (previos is Map ? previos : const {}).entries)
        if (e.value is num) '${e.key}': (e.value as num).toInt()
    };
    for (final e in ((bloque['dias'] as Map?) ?? const {}).entries) {
      if (e.value is! num) continue;
      final ms = ((e.value as num) * 1000).round();
      dias['${e.key}'] = max(dias['${e.key}'] ?? 0, ms);
    }
    await prefs.setString('estudio.dias', jsonEncode(dias));
    final cfg = bloque['config_movil'];
    if (cfg is Map) {
      for (final e in cfg.entries) {
        if (!_estudioConfig.contains(e.key)) continue;
        final k = 'estudio.${e.key}', v = e.value;
        if (v is String) {
          await prefs.setString(k, v);
        } else if (v is bool) {
          await prefs.setBool(k, v);
        } else if (v is int) {
          await prefs.setInt(k, v);
        } else if (v is double) {
          await prefs.setDouble(k, v);
        }
      }
    }
    return true;
  }

  static String _corta(String iso) => iso.length >= 16 ? iso.substring(0, 16) : iso;

  static Future<bool> _restaurarGustos(
      SharedPreferences prefs, Object? bloque, String modo, String cuenta, bool conCuenta) async {
    if (bloque is! Map || cuenta.isEmpty) return false;
    final previos = modo == 'juntar' ? Gustos.leerLista(prefs.getString('gustos.lista.$cuenta')) : <ArtistaGusto>[];
    final lista = Gustos.leerLista([
      for (final a in previos) a.toJson(),
      ...(bloque['artistas'] is List ? bloque['artistas'] as List : const []),
    ]);
    await prefs.setString('gustos.lista.$cuenta', jsonEncode([for (final a in lista) a.toJson()]));
    await prefs.setBool('gustos.listo.$cuenta', bloque['elegidos'] == true || (prefs.getBool('gustos.listo.$cuenta') ?? false));
    await prefs.setBool('gustos.pendiente.$cuenta', conCuenta);
    Gustos.actuales = lista;
    return true;
  }

  // ==================================================================== copia automática

  static String _k(String cuenta, String c) => 'copia.$cuenta.$c';

  static Future<bool> automaticaActiva(String cuenta) async =>
      (await SharedPreferences.getInstance()).getBool(_k(cuenta, 'automatica')) ?? false;

  static Future<void> ponerAutomatica(String cuenta, bool si) async =>
      (await SharedPreferences.getInstance()).setBool(_k(cuenta, 'automatica'), si);

  static Future<DateTime?> ultimaAutomatica(String cuenta) async {
    final ms = (await SharedPreferences.getInstance()).getInt(_k(cuenta, 'ultima'));
    return ms == null ? null : DateTime.fromMillisecondsSinceEpoch(ms);
  }

  /// Carpeta de la app donde quedan las copias automáticas (las tres últimas).
  static Future<Directory> carpetaAutomaticas({String? base}) async {
    final raiz = base ?? (await getApplicationDocumentsDirectory()).path;
    final d = Directory(p.join(raiz, 'copias'));
    if (!await d.exists()) await d.create(recursive: true);
    return d;
  }

  /// Si toca (una vez por semana y si está activada), deja una copia en la
  /// carpeta de la app. Devuelve el archivo hecho o null.
  static Future<File?> automaticaSiToca(Coleccion col,
      {Ajustes? ajustes, required String cuenta, DateTime? ahora, String? base, int conservar = 3}) async {
    if (kIsWeb) return null;
    final prefs = await SharedPreferences.getInstance();
    if (!(prefs.getBool(_k(cuenta, 'automatica')) ?? false)) return null;
    final hoy = ahora ?? DateTime.now();
    final ultima = prefs.getInt(_k(cuenta, 'ultima'));
    if (ultima != null && hoy.difference(DateTime.fromMillisecondsSinceEpoch(ultima)).inDays < 7) return null;
    final bytes = await crear(col, ajustes: ajustes, cuenta: cuenta);
    final dir = await carpetaAutomaticas(base: base);
    final archivo = File(p.join(dir.path, nombreSugerido(automatica: true, ahora: hoy)));
    final tmp = File('${archivo.path}.tmp');
    await tmp.writeAsBytes(bytes, flush: true);
    await tmp.rename(archivo.path);
    await prefs.setInt(_k(cuenta, 'ultima'), hoy.millisecondsSinceEpoch);
    final autos = [
      for (final f in dir.listSync())
        if (f is File && p.basename(f.path).startsWith('Caudal-auto-') && f.path.endsWith(extension)) f
    ]..sort((a, b) => p.basename(b.path).compareTo(p.basename(a.path)));
    for (final viejo in autos.skip(max(1, conservar))) {
      try {
        await viejo.delete();
      } catch (_) {}
    }
    return archivo;
  }
}
