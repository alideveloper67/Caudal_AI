import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import 'base_datos_io.dart' if (dart.library.js_interop) 'base_datos_web.dart';
import 'huella_cancion.dart';
import 'plataforma.dart';
import 'social.dart' show ImagenSocial;

typedef Json = Map<String, dynamic>;

/// Portadas personalizadas de listas que viven en memoria (en el navegador no
/// hay carpetas: los bytes van en la base y se suben aqui al abrirla).
/// La referencia que se guarda en la columna `portada` es `mem:<id>:<marca>`.
class PortadasMem {
  PortadasMem._();
  static final Map<String, Uint8List> _datos = {};
  static bool esRef(String ref) => ref.startsWith('mem:');
  static Uint8List? bytes(String ref) => _datos[ref];
  static void poner(String ref, Uint8List b) => _datos[ref] = b;
  static void quitar(String ref) => _datos.remove(ref);
  static void limpiar() => _datos.clear();
}

/// Tu coleccion: me gusta, listas, escuchas, guardados y lo descargado.
///
/// Igual que en Caudal Escritorio (coleccion.py): la base local es la que usa
/// la interfaz (rapida y sin internet) y cada cambio deja una orden en
/// `pendientes` para la nube. Lo que se consulta al pintar cada fila (me
/// gusta, descargada) vive en memoria para que las listas no se traben.
class Coleccion extends ChangeNotifier {
  Coleccion._(this.db, this.ruta);

  final Database db;
  final String ruta;

  /// Lo pone la app al entrar con cuenta; avisa de que hay algo que enviar.
  void Function()? alHaberPendientes;

  final Set<String> _gustan = {};
  final Set<String> _guardados = {};
  final Map<String, List<Json>> _porVideo = {};

  static Future<Coleccion> abrir(String cuentaId) async {
    if (kIsWeb) {
      // navegador: la base en su almacenamiento; sin carpetas ni archivos
      await prepararBaseDeDatos();
      final db = await openDatabase('caudal_$cuentaId.db', version: _versionBase,
          onCreate: (db, _) => _crear(db), onUpgrade: _migrar);
      final c = Coleccion._(db, 'caudal_$cuentaId.db');
      await c._cargarMemoria();
      return c;
    }
    // En iPhone, Documentos es lo que el usuario ve en la app Archivos: ahi
    // van solo las descargas. La base va aparte, donde no se vea ni se borre
    // por error. En Android se queda donde siempre estuvo.
    final dir = Plataforma.esIOS
        ? await getApplicationSupportDirectory()
        : await getApplicationDocumentsDirectory();
    if (!await dir.exists()) await dir.create(recursive: true);
    final ruta = p.join(dir.path, 'caudal_$cuentaId.db');
    if (Plataforma.esIOS) {
      _documentosIOS = (await getApplicationDocumentsDirectory()).path;
    }
    final db = await openDatabase(ruta, version: _versionBase, onCreate: (db, _) => _crear(db),
        onUpgrade: _migrar, onOpen: (db) async {
      await db.rawQuery('PRAGMA journal_mode=WAL');
    });
    final c = Coleccion._(db, ruta);
    await c._cargarMemoria();
    return c;
  }

  /// Version de la base: 2 = listas con `portada` y `portada_datos`; 3 = listas con `publica` y `en_perfil`.
  static const _versionBase = 3;

  /// Para las pruebas: abre (y migra) una base en una ruta concreta.
  @visibleForTesting
  static Future<Coleccion> abrirEn(String ruta) async {
    final db = await openDatabase(ruta, version: _versionBase,
        onCreate: (db, _) => _crear(db), onUpgrade: _migrar);
    final c = Coleccion._(db, ruta);
    await c._cargarMemoria();
    return c;
  }

  /// Cierra la base (pruebas).
  @visibleForTesting
  Future<void> cerrar() {
    _cerrada = true;
    _relojListas?.cancel();
    return db.close();
  }

  static Future<void> _migrar(Database db, int desde, int hasta) async {
    if (desde < 2) {
      final cols = [for (final c in await db.rawQuery('PRAGMA table_info(listas)')) '${c['name']}'];
      if (!cols.contains('portada')) await db.execute('ALTER TABLE listas ADD COLUMN portada TEXT');
      if (!cols.contains('portada_datos')) await db.execute('ALTER TABLE listas ADD COLUMN portada_datos BLOB');
    }
    if (desde < 3) {
      final cols = [for (final c in await db.rawQuery('PRAGMA table_info(listas)')) '${c['name']}'];
      if (!cols.contains('publica')) await db.execute('ALTER TABLE listas ADD COLUMN publica INTEGER DEFAULT 0');
      if (!cols.contains('en_perfil')) await db.execute('ALTER TABLE listas ADD COLUMN en_perfil INTEGER DEFAULT 0');
    }
  }

  /// En el navegador (o si se fuerza) la portada va en la base; si no, en un archivo.
  @visibleForTesting
  static bool portadaEnBytes = kIsWeb;

  /// Carpeta de las portadas (las pruebas la cambian).
  @visibleForTesting
  static String? carpetaPortadasPrueba;

  static Future<void> _crear(Database db) async {
    final b = db.batch();
    b.execute('CREATE TABLE pistas (clave TEXT PRIMARY KEY, datos TEXT NOT NULL, actualizada REAL)');
    b.execute('CREATE TABLE me_gusta (clave TEXT PRIMARY KEY, fecha REAL)');
    b.execute('CREATE TABLE listas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, '
        "creada REAL, descripcion TEXT DEFAULT '', fijada INTEGER DEFAULT 0, tocada REAL DEFAULT 0, "
        'uuid TEXT, portada TEXT, portada_datos BLOB, publica INTEGER DEFAULT 0, en_perfil INTEGER DEFAULT 0)');
    b.execute('CREATE TABLE lista_items (lista_id INTEGER NOT NULL, clave TEXT NOT NULL, '
        'orden REAL DEFAULT 0, agregada REAL, PRIMARY KEY (lista_id, clave))');
    b.execute('CREATE TABLE reproducciones (id INTEGER PRIMARY KEY AUTOINCREMENT, clave TEXT NOT NULL, '
        "fecha REAL, contexto TEXT DEFAULT '', nube_id INTEGER)");
    b.execute('CREATE INDEX idx_repro_fecha ON reproducciones(fecha DESC)');
    b.execute('CREATE TABLE guardados (tipo TEXT NOT NULL, id TEXT NOT NULL, datos TEXT NOT NULL, '
        'fecha REAL, PRIMARY KEY (tipo, id))');
    b.execute('CREATE TABLE contextos_recientes (tipo TEXT NOT NULL, id TEXT NOT NULL, '
        'datos TEXT NOT NULL, fecha REAL, PRIMARY KEY (tipo, id))');
    b.execute('CREATE TABLE busquedas (texto TEXT PRIMARY KEY, fecha REAL)');
    b.execute('CREATE TABLE estado (clave TEXT PRIMARY KEY, valor TEXT)');
    b.execute('CREATE TABLE pendientes (id INTEGER PRIMARY KEY AUTOINCREMENT, op TEXT NOT NULL, '
        'datos TEXT NOT NULL, creada REAL)');
    b.execute('CREATE TABLE descargas (id INTEGER PRIMARY KEY AUTOINCREMENT, video_id TEXT, url TEXT, '
        'titulo TEXT, artista TEXT, archivo TEXT, es_audio INTEGER, tamano INTEGER, duracion INTEGER, '
        'calidad TEXT, caratula TEXT, datos TEXT, fecha REAL)');
    await b.commit(noResult: true);
  }

  static double get _ahora => DateTime.now().millisecondsSinceEpoch / 1000.0;

  Future<void> _cargarMemoria() async {
    for (final f in await db.rawQuery(
        'SELECT portada, portada_datos FROM listas WHERE portada_datos IS NOT NULL')) {
      final ref = '${f['portada'] ?? ''}';
      final d = f['portada_datos'];
      if (ref.isNotEmpty && d is List<int>) {
        PortadasMem.poner(ref, d is Uint8List ? d : Uint8List.fromList(d));
      }
    }
    _gustan
      ..clear()
      ..addAll((await db.query('me_gusta', columns: ['clave'])).map((f) => '${f['clave']}'));
    _guardados
      ..clear()
      ..addAll((await db.query('guardados', columns: ['tipo', 'id']))
          .map((f) => '${f['tipo']}|${f['id']}'));
    await _refrescarListasEnMemoria();
    _porVideo.clear();
    await _recolocarRutasIOS();
    for (final f in await db.query('descargas', orderBy: 'fecha DESC')) {
      final vid = '${f['video_id'] ?? ''}';
      if (vid.isNotEmpty) _porVideo.putIfAbsent(vid, () => []).add(Map<String, dynamic>.from(f));
    }
  }

  /// Documentos de la app en este arranque (solo iPhone).
  static String? _documentosIOS;

  /// En iPhone la carpeta de la app cambia de sitio al actualizarla o
  /// restaurar una copia: las rutas guardadas apuntan a una carpeta que ya no
  /// existe aunque el archivo siga ahi. Se recolocan sobre la de ahora.
  Future<void> _recolocarRutasIOS() async {
    final documentos = _documentosIOS;
    if (documentos == null) return;
    final filas = await db.query('descargas', columns: ['id', 'archivo']);
    for (final f in filas) {
      final antes = '${f['archivo'] ?? ''}';
      final ahora = recolocarRuta(antes, documentos);
      if (ahora != antes) {
        await db.update('descargas', {'archivo': ahora}, where: 'id = ?', whereArgs: [f['id']]);
      }
    }
  }

  // ---------------------------------------------- listas en memoria
  //
  // La hoja «Añadir a una lista» necesita las listas al instante: se guardan
  // en memoria y se rehacen en segundo plano cada vez que algo cambia.

  List<Json>? _listasMem;
  int? _ultimaLista;
  Timer? _relojListas;
  bool _cerrada = false;

  /// Las listas tal como estaban la ultima vez que se miraron (null si aun no).
  /// Se pueden pintar sin esperar a la base.
  List<Json>? get listasEnMemoria => _listasMem;

  /// La ultima lista donde se anadio algo (para ponerla arriba).
  int? get ultimaLista => _ultimaLista;

  Future<void> _refrescarListasEnMemoria() async {
    if (_cerrada) return;
    _listasMem = await listas();
    final u = await estado('ultima_lista');
    _ultimaLista = u is int ? u : int.tryParse('${u ?? ''}');
  }

  void _programarListasEnMemoria() {
    if (_cerrada) return;
    _relojListas?.cancel();
    _relojListas = Timer(const Duration(milliseconds: 150), () async {
      try {
        await _refrescarListasEnMemoria();
      } catch (_) {}
    });
  }

  @override
  void notifyListeners() {
    super.notifyListeners();
    _programarListasEnMemoria();
  }

  /// Recuerda la lista elegida para ponerla arriba la proxima vez.
  Future<void> marcarListaUsada(int id) async {
    _ultimaLista = id;
    await guardarEstado('ultima_lista', id);
  }

  /// Tras traer cambios de otros dispositivos.
  Future<void> refrescarMemoria() async {
    await _cargarMemoria();
    notifyListeners();
  }

  // ------------------------------------------------------------ nube

  Future<void> _anotar(String op, Object datos) async {
    if (alHaberPendientes == null) return;
    await db.insert('pendientes', {'op': op, 'datos': jsonEncode(datos), 'creada': _ahora});
    alHaberPendientes!();
  }

  static Json paraNube(Json pista) {
    const fuera = {'archivo', 'descarga_id', 'es_audio', 'tamano', 'calidad', 'fecha', 'url'};
    return {
      for (final e in pista.entries)
        if (!fuera.contains(e.key) && !e.key.startsWith('_')) e.key: e.value
    };
  }

  /// El id local de la lista con ese uuid de la nube (o null si no esta en este dispositivo).
  Future<int?> idPorUuid(String uuid) async {
    final f = await db.query('listas', columns: ['id'], where: 'uuid = ?', whereArgs: [uuid]);
    return f.isEmpty ? null : f.first['id'] as int;
  }

  Future<String> _uuidLista(int id) async {
    final f = await db.query('listas', columns: ['uuid'], where: 'id = ?', whereArgs: [id]);
    if (f.isEmpty) return '';
    final u = f.first['uuid'] as String?;
    if (u != null && u.isNotEmpty) return u;
    final nuevo = nuevoUuid();
    await db.update('listas', {'uuid': nuevo}, where: 'id = ?', whereArgs: [id]);
    return nuevo;
  }

  Future<void> _anotarLista(int id, {bool privacidad = false}) async {
    final l = await lista(id);
    if (l == null) return;
    final publica = (l['publica'] ?? 0) == 1;
    await _anotar('lista_poner', {
      'uuid': await _uuidLista(id),
      'nombre': l['nombre'],
      'descripcion': l['descripcion'] ?? '',
      'fijada': (l['fijada'] ?? 0) == 1,
      // solo viajan cuando la persona los cambia: asi no estorban si la nube aun no los conoce
      if (privacidad) ...{'publica': publica, 'en_perfil': publica && (l['en_perfil'] ?? 0) == 1},
    });
  }

  // ------------------------------------------------------------ pistas

  Future<void> recordar(Json pista) async {
    final clave = pista['clave'] as String?;
    if (clave == null || !clave.startsWith('yt:')) return;
    await db.insert('pistas',
        {'clave': clave, 'datos': jsonEncode(paraNube(pista)), 'actualizada': _ahora},
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Json>> pistas(List<String> claves) async {
    if (claves.isEmpty) return [];
    final salida = <Json>[];
    final mapa = <String, Json>{};
    for (var i = 0; i < claves.length; i += 400) {
      final trozo = claves.sublist(i, min(i + 400, claves.length));
      final filas = await db.query('pistas',
          where: 'clave IN (${List.filled(trozo.length, '?').join(',')})', whereArgs: trozo);
      for (final f in filas) {
        try {
          mapa['${f['clave']}'] = Map<String, dynamic>.from(jsonDecode('${f['datos']}') as Map);
        } catch (_) {}
      }
    }
    for (final c in claves) {
      final pista = mapa[c] ?? await _pistaDescargada(c);
      if (pista != null) salida.add(pista);
    }
    return salida;
  }

  Future<Json?> _pistaDescargada(String clave) async {
    if (!clave.startsWith('local:')) return null;
    final f = await db.query('descargas', where: 'id = ?', whereArgs: [int.tryParse(clave.substring(6))]);
    return f.isEmpty ? null : pistaDeDescarga(f.first);
  }

  // ------------------------------------------------------------ me gusta

  bool meGusta(String? clave) => clave != null && _gustan.contains(clave);
  int get totalMeGusta => _gustan.length;

  Future<bool> alternarMeGusta(Json pista) async {
    final clave = pista['clave'] as String?;
    if (clave == null) return false;
    if (_gustan.contains(clave)) {
      await db.delete('me_gusta', where: 'clave = ?', whereArgs: [clave]);
      _gustan.remove(clave);
      if (clave.startsWith('yt:')) await _anotar('me_gusta_quitar', {'clave': clave});
      notifyListeners();
      return false;
    }
    await recordar(pista);
    await db.insert('me_gusta', {'clave': clave, 'fecha': _ahora},
        conflictAlgorithm: ConflictAlgorithm.replace);
    _gustan.add(clave);
    if (clave.startsWith('yt:')) {
      await _anotar('me_gusta_poner', {'clave': clave, 'datos': paraNube(pista)});
    }
    notifyListeners();
    return true;
  }

  Future<List<Json>> listaMeGusta() async {
    final claves = (await db.query('me_gusta', orderBy: 'fecha DESC')).map((f) => '${f['clave']}');
    return pistas(claves.toList());
  }

  /// Pone «me gusta» a muchas canciones de una vez (las traídas de otra app).
  /// No repite: fuera las que ya están (misma clave o la misma canción con otro
  /// video). Quedan en el orden dado, la primera arriba. Devuelve (añadidas, repetidas).
  Future<(int, int)> agregarMeGustaVarios(List<Json> pistas) async {
    final actuales = [for (final f in await db.query('me_gusta', columns: ['clave'])) '${f['clave']}'];
    final huellas = [for (final p in await this.pistas(actuales)) huellaPista(p)];
    final (nuevas, repetidas) = separarNuevas(pistas, actuales, huellas);
    if (nuevas.isEmpty) return (0, repetidas);
    final ahora = _ahora;
    final subir = <Json>[];
    final b = db.batch();
    for (var i = 0; i < nuevas.length; i++) {
      final p = nuevas[i];
      final clave = p['clave'] as String;
      // un segundo entre una y otra: la nube guarda segundos y así se respeta el orden
      final fecha = ahora - i;
      if (clave.startsWith('yt:')) {
        b.insert('pistas', {'clave': clave, 'datos': jsonEncode(paraNube(p)), 'actualizada': ahora},
            conflictAlgorithm: ConflictAlgorithm.replace);
        subir.add({'clave': clave, 'datos': paraNube(p), 'fecha': fecha});
      }
      b.insert('me_gusta', {'clave': clave, 'fecha': fecha}, conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await b.commit(noResult: true);
    _gustan.addAll(nuevas.map((p) => p['clave'] as String));
    // a la nube de 400 en 400: si algo se corta, lo ya subido no se repite
    for (var i = 0; i < subir.length; i += 400) {
      await _anotar('me_gusta_varios', {'items': subir.sublist(i, min(i + 400, subir.length))});
    }
    notifyListeners();
    return (nuevas.length, repetidas);
  }

  /// Los [n] me gusta mas recientes, sin leer ni decodificar los demas.
  Future<List<Json>> meGustaRecientes(int n) async {
    final claves = (await db.query('me_gusta', orderBy: 'fecha DESC', limit: n)).map((f) => '${f['clave']}');
    return pistas(claves.toList());
  }

  /// Las filas tal cual de [claves] en `pistas` (clave -> JSON sin decodificar),
  /// para decodificarlas fuera del hilo de la pantalla. Las que no estan ahi
  /// (descargas locales) van ya decodificadas en `locales`.
  Future<({Map<String, String> datos, Map<String, Json> locales})> pistasCrudas(List<String> claves) async {
    final datos = <String, String>{};
    for (var i = 0; i < claves.length; i += 400) {
      final trozo = claves.sublist(i, min(i + 400, claves.length));
      final filas = await db.query('pistas',
          columns: ['clave', 'datos'],
          where: 'clave IN (${List.filled(trozo.length, '?').join(',')})', whereArgs: trozo);
      for (final f in filas) {
        datos['${f['clave']}'] = '${f['datos']}';
      }
    }
    final locales = <String, Json>{};
    for (final c in claves) {
      if (datos.containsKey(c) || !c.startsWith('local:')) continue;
      final pista = await _pistaDescargada(c);
      if (pista != null) locales[c] = pista;
    }
    return (datos: datos, locales: locales);
  }

  // ------------------------------------------------------------ listas

  Future<List<Json>> listas() async {
    final filas = await db.rawQuery('SELECT l.*, COUNT(i.clave) n FROM listas l '
        'LEFT JOIN lista_items i ON i.lista_id = l.id GROUP BY l.id '
        'ORDER BY l.fijada DESC, l.tocada DESC, l.nombre COLLATE NOCASE');
    return filas.map((f) => Map<String, dynamic>.from(f)).toList();
  }

  Future<Json?> lista(int id) async {
    final f = await db.query('listas', where: 'id = ?', whereArgs: [id]);
    return f.isEmpty ? null : Map<String, dynamic>.from(f.first);
  }

  Future<String> nombreLibre([String base = 'Mi lista']) async {
    var n = 1;
    while (true) {
      final nombre = '$base n.º $n';
      final f = await db.query('listas', where: 'nombre = ?', whereArgs: [nombre]);
      if (f.isEmpty) return nombre;
      n++;
    }
  }

  Future<int> crearLista(String nombre, {String descripcion = ''}) async {
    nombre = nombre.trim();
    if (nombre.isEmpty) throw const FormatException('La lista necesita un nombre.');
    if ((await db.query('listas', where: 'nombre = ?', whereArgs: [nombre])).isNotEmpty) {
      throw const FormatException('Ya tienes una lista con ese nombre.');
    }
    final id = await db.insert('listas', {
      'nombre': nombre, 'creada': _ahora, 'descripcion': descripcion, 'tocada': _ahora,
      'uuid': nuevoUuid(),
    });
    await _anotarLista(id);
    notifyListeners();
    return id;
  }

  Future<void> editarLista(int id,
      {String? nombre, String? descripcion, bool? fijada, bool? publica, bool? enPerfil}) async {
    final cambios = <String, Object?>{};
    if (nombre != null) {
      nombre = nombre.trim();
      if (nombre.isEmpty) throw const FormatException('La lista necesita un nombre.');
      final otra = await db.query('listas', where: 'nombre = ? AND id != ?', whereArgs: [nombre, id]);
      if (otra.isNotEmpty) throw const FormatException('Ya tienes una lista con ese nombre.');
      cambios['nombre'] = nombre;
    }
    if (descripcion != null) cambios['descripcion'] = descripcion;
    if (fijada != null) cambios['fijada'] = fijada ? 1 : 0;
    final cambiaPrivacidad = publica != null || enPerfil != null;
    if (cambiaPrivacidad) {
      final actual = await lista(id);
      final pub = publica ?? (actual?['publica'] ?? 0) == 1;
      final perfil = enPerfil ?? (actual?['en_perfil'] ?? 0) == 1;
      cambios['publica'] = pub ? 1 : 0;
      // «en el perfil» solo existe en una lista publica (igual que en el servidor)
      cambios['en_perfil'] = pub && perfil ? 1 : 0;
    }
    if (cambios.isEmpty) return;
    await db.update('listas', cambios, where: 'id = ?', whereArgs: [id]);
    await _anotarLista(id, privacidad: cambiaPrivacidad);
    notifyListeners();
  }

  Future<void> borrarLista(int id) async {
    final u = await _uuidLista(id);
    if (u.isNotEmpty) await _anotar('lista_borrar', {'uuid': u});
    await _borrarArchivoPortada(await _portadaActual(id));
    await db.delete('lista_items', where: 'lista_id = ?', whereArgs: [id]);
    await db.delete('listas', where: 'id = ?', whereArgs: [id]);
    notifyListeners();
  }

  /// Anade canciones al final de la lista; devuelve cuantas entraron de verdad
  /// (las que ya estaban no cuentan).
  Future<int> agregarALista(int id, List<Json> nuevas) async =>
      (await agregarAListaDetalle(id, nuevas)).length;

  /// Igual que [agregarALista], pero devuelve las claves que entraron (para
  /// poder deshacer). Todo en una sola transaccion, sin esperar fila por fila.
  Future<List<String>> agregarAListaDetalle(int id, List<Json> nuevas) async {
    final f = await db.rawQuery('SELECT COALESCE(MAX(orden), 0) m FROM lista_items WHERE lista_id = ?', [id]);
    var orden = (f.first['m'] as num).toDouble();
    final candidatas = <String>{
      for (final pista in nuevas)
        if (pista['clave'] is String) pista['clave'] as String
    }.toList();
    final vistas = <String>{};
    for (var i = 0; i < candidatas.length; i += 400) {
      final trozo = candidatas.sublist(i, min(i + 400, candidatas.length));
      final filas = await db.query('lista_items', columns: ['clave'],
          where: 'lista_id = ? AND clave IN (${List.filled(trozo.length, '?').join(',')})',
          whereArgs: [id, ...trozo]);
      for (final r in filas) {
        vistas.add('${r['clave']}');
      }
    }
    final entraron = <String>[];
    final subir = <Json>[];
    final ahora = _ahora;
    final b = db.batch();
    for (final pista in nuevas) {
      final clave = pista['clave'] as String?;
      if (clave == null) continue;
      if (clave.startsWith('yt:')) {
        b.insert('pistas', {'clave': clave, 'datos': jsonEncode(paraNube(pista)), 'actualizada': ahora},
            conflictAlgorithm: ConflictAlgorithm.replace);
      }
      orden += 1;
      if (!vistas.add(clave)) continue;
      b.insert('lista_items', {'lista_id': id, 'clave': clave, 'orden': orden, 'agregada': ahora},
          conflictAlgorithm: ConflictAlgorithm.ignore);
      entraron.add(clave);
      if (clave.startsWith('yt:')) subir.add({'clave': clave, 'datos': paraNube(pista), 'orden': orden});
    }
    b.update('listas', {'tocada': ahora}, where: 'id = ?', whereArgs: [id]);
    await b.commit(noResult: true);
    if (subir.isNotEmpty) {
      // de 400 en 400: una lista de 5 000 no queda como una sola orden enorme que, si la
      // nube rechaza un trozo, se perdería entera
      final uuid = await _uuidLista(id);
      for (var i = 0; i < subir.length; i += 400) {
        await _anotar('items_poner', {'uuid': uuid, 'items': subir.sublist(i, min(i + 400, subir.length))});
      }
    }
    notifyListeners();
    return entraron;
  }

  Future<void> quitarDeLista(int id, String clave) async {
    await db.delete('lista_items', where: 'lista_id = ? AND clave = ?', whereArgs: [id, clave]);
    if (clave.startsWith('yt:')) {
      await _anotar('item_quitar', {'uuid': await _uuidLista(id), 'clave': clave});
    }
    notifyListeners();
  }

  /// Quita varias canciones de una lista de una vez (una sola orden para la nube).
  Future<void> quitarVariasDeLista(int id, List<String> claves) async {
    if (claves.isEmpty) return;
    final b = db.batch();
    for (final c in claves) {
      b.delete('lista_items', where: 'lista_id = ? AND clave = ?', whereArgs: [id, c]);
    }
    await b.commit(noResult: true);
    final nube = [for (final c in claves) if (c.startsWith('yt:')) c];
    if (nube.isNotEmpty) await _anotar('items_quitar', {'uuid': await _uuidLista(id), 'claves': nube});
    notifyListeners();
  }

  Future<void> moverEnLista(int id, List<String> claves) async {
    final b = db.batch();
    for (var i = 0; i < claves.length; i++) {
      b.update('lista_items', {'orden': i + 1}, where: 'lista_id = ? AND clave = ?',
          whereArgs: [id, claves[i]]);
    }
    await b.commit(noResult: true);
    final datos = await pistas(claves);
    final items = <Json>[
      for (var i = 0; i < datos.length; i++)
        if ('${datos[i]['clave']}'.startsWith('yt:'))
          {'clave': datos[i]['clave'], 'datos': paraNube(datos[i]), 'orden': i + 1}
    ];
    if (items.isNotEmpty) await _anotar('items_poner', {'uuid': await _uuidLista(id), 'items': items});
    notifyListeners();
  }

  Future<List<Json>> pistasDeLista(int id) async {
    final claves = (await db.query('lista_items', where: 'lista_id = ?', whereArgs: [id],
            orderBy: 'orden'))
        .map((f) => '${f['clave']}')
        .toList();
    return pistas(claves);
  }

  Future<String> _portadaActual(int id) async {
    final f = await db.query('listas', columns: ['portada'], where: 'id = ?', whereArgs: [id]);
    return f.isEmpty ? '' : '${f.first['portada'] ?? ''}';
  }

  Future<void> _borrarArchivoPortada(String ref) async {
    if (ref.isEmpty) return;
    if (PortadasMem.esRef(ref)) {
      PortadasMem.quitar(ref);
      return;
    }
    try {
      final a = File(ref);
      if (await a.exists()) await a.delete();
    } catch (_) {}
  }

  /// Ruta o referencia de la portada personalizada ('' si no hay).
  Future<String> portadaPersonalizada(int id) => _portadaActual(id);

  /// Pone la imagen elegida como portada de la lista. [imagen] es cualquier
  /// foto: se recorta al centro en cuadrado, se reduce a 800 px y queda en JPEG.
  Future<void> ponerPortadaLista(int id, Uint8List imagen) async {
    final jpeg = await ImagenSocial.cuadrada(imagen);
    final marca = DateTime.now().microsecondsSinceEpoch;
    final anterior = await _portadaActual(id);
    String ref;
    if (portadaEnBytes) {
      ref = 'mem:$id:$marca';
      PortadasMem.poner(ref, jpeg);
      await db.update('listas', {'portada': ref, 'portada_datos': jpeg}, where: 'id = ?', whereArgs: [id]);
    } else {
      final dir = Directory(carpetaPortadasPrueba ??
          p.join((await getApplicationDocumentsDirectory()).path, 'portadas_listas'));
      if (!await dir.exists()) await dir.create(recursive: true);
      final uuid = await _uuidLista(id);
      final clave = uuid.isNotEmpty ? uuid : '$id';
      ref = p.join(dir.path, '${clave}_$marca.jpg');
      await File(ref).writeAsBytes(jpeg, flush: true);
      await db.update('listas', {'portada': ref, 'portada_datos': null}, where: 'id = ?', whereArgs: [id]);
    }
    if (anterior.isNotEmpty && anterior != ref) await _borrarArchivoPortada(anterior);
    notifyListeners();
  }

  /// Vuelve al mosaico de carátulas.
  Future<void> quitarPortadaLista(int id) async {
    final anterior = await _portadaActual(id);
    await db.update('listas', {'portada': null, 'portada_datos': null}, where: 'id = ?', whereArgs: [id]);
    await _borrarArchivoPortada(anterior);
    notifyListeners();
  }

  Future<List<String>> portadasDeLista(int id, [int n = 4]) async {
    final propia = await _portadaActual(id);
    if (propia.isNotEmpty) return [propia];
    // solo las primeras canciones, de 8 en 8 y decodificando solo esas: antes se
    // leia y decodificaba la lista entera para sacar cuatro miniaturas
    const tanda = 8, tope = 40;
    final salida = <String>[];
    for (var desde = 0; desde < tope && salida.length < n; desde += tanda) {
      final filas = await db.rawQuery(
          'SELECT i.clave, p.datos FROM lista_items i LEFT JOIN pistas p ON p.clave = i.clave '
          'WHERE i.lista_id = ? ORDER BY i.orden LIMIT ? OFFSET ?',
          [id, tanda, desde]);
      for (final f in filas) {
        Json? pista;
        final datos = f['datos'];
        if (datos != null) {
          try {
            pista = Map<String, dynamic>.from(jsonDecode('$datos') as Map);
          } catch (_) {}
        } else {
          pista = await _pistaDescargada('${f['clave']}');
        }
        final m = '${pista?['miniatura'] ?? ''}';
        if (m.isNotEmpty && !salida.contains(m)) salida.add(m);
        if (salida.length >= n) break;
      }
      if (filas.length < tanda) break;
    }
    return salida;
  }

  // ------------------------------------------------------------ guardados

  bool guardado(String tipo, String id) => _guardados.contains('$tipo|$id');

  Future<void> guardar(Json el) async {
    final tipo = el['tipo'] as String?;
    final id = el['id'] as String?;
    if (tipo == null || id == null) return;
    final datos = {for (final e in el.entries) if (e.key != 'pistas' && e.key != 'secciones') e.key: e.value};
    await db.insert('guardados', {'tipo': tipo, 'id': id, 'datos': jsonEncode(datos), 'fecha': _ahora},
        conflictAlgorithm: ConflictAlgorithm.replace);
    _guardados.add('$tipo|$id');
    await _anotar('guardado_poner', {'tipo': tipo, 'id': id, 'datos': datos});
    notifyListeners();
  }

  Future<void> olvidar(String tipo, String id) async {
    await db.delete('guardados', where: 'tipo = ? AND id = ?', whereArgs: [tipo, id]);
    _guardados.remove('$tipo|$id');
    await _anotar('guardado_quitar', {'tipo': tipo, 'id': id});
    notifyListeners();
  }

  Future<List<Json>> guardados([String? tipo]) async {
    final filas = await db.query('guardados',
        where: tipo == null ? null : 'tipo = ?', whereArgs: tipo == null ? null : [tipo],
        orderBy: 'fecha DESC');
    return [
      for (final f in filas) Map<String, dynamic>.from(jsonDecode('${f['datos']}') as Map)
    ];
  }

  // ------------------------------------------------------------ escuchas

  Future<void> registrarEscucha(Json pista, Json? contexto) async {
    final clave = pista['clave'] as String?;
    if (clave == null) return;
    await recordar(pista);
    final enNube = alHaberPendientes != null && clave.startsWith('yt:');
    await db.insert('reproducciones', {
      'clave': clave, 'fecha': _ahora, 'contexto': contexto == null ? '' : jsonEncode(contexto),
      'nube_id': enNube ? -1 : null,
    });
    if (contexto != null && contexto['tipo'] != null && contexto['id'] != null) {
      await db.insert('contextos_recientes', {
        'tipo': '${contexto['tipo']}', 'id': '${contexto['id']}', 'datos': jsonEncode(contexto),
        'fecha': _ahora,
      }, conflictAlgorithm: ConflictAlgorithm.replace);
    }
    if (enNube) {
      await _anotar('escucha', {'clave': clave, 'datos': paraNube(pista), 'contexto': contexto,
          'fecha': _ahora});
    }
  }

  Future<List<Json>> escuchadoHacePoco([int n = 30]) async {
    final filas = await db.rawQuery(
        'SELECT clave, MAX(fecha) f FROM reproducciones GROUP BY clave ORDER BY f DESC LIMIT ?', [n]);
    return pistas(filas.map((f) => '${f['clave']}').toList());
  }

  Future<List<Json>> contextosRecientes([int n = 12]) async {
    final filas = await db.query('contextos_recientes', orderBy: 'fecha DESC', limit: n);
    return [
      for (final f in filas)
        conPortadaDeRadio(Map<String, dynamic>.from(jsonDecode('${f['datos']}') as Map))
    ];
  }

  Future<List<Json>> artistasFrecuentes([int n = 8]) async {
    final cuenta = <String, int>{};
    final nombres = <String, String>{};
    final portadas = <String, String>{};
    // solo los 100 me gusta mas recientes (antes se decodificaban todos)
    final base = [...await escuchadoHacePoco(150), ...await meGustaRecientes(100)];
    for (final pista in base) {
      for (final a in (pista['artistas'] as List? ?? [])) {
        final id = '${(a as Map)['id'] ?? ''}';
        if (id.isEmpty) continue;
        cuenta[id] = (cuenta[id] ?? 0) + 1;
        nombres[id] = '${a['nombre']}';
        portadas.putIfAbsent(id, () => '${pista['miniatura'] ?? ''}');
      }
    }
    final orden = cuenta.keys.toList()..sort((a, b) => cuenta[b]!.compareTo(cuenta[a]!));
    return [
      for (final id in orden.take(n)) {'id': id, 'nombre': nombres[id], 'miniatura': portadas[id]}
    ];
  }

  Future<void> borrarEscuchas() async {
    await db.delete('reproducciones');
    await db.delete('contextos_recientes');
    notifyListeners();
  }

  // ------------------------------------------------------------ busquedas

  Future<void> anotarBusqueda(String texto) async {
    texto = texto.trim();
    if (texto.isEmpty) return;
    await db.insert('busquedas', {'texto': texto, 'fecha': _ahora},
        conflictAlgorithm: ConflictAlgorithm.replace);
    await db.rawDelete('DELETE FROM busquedas WHERE texto NOT IN '
        '(SELECT texto FROM busquedas ORDER BY fecha DESC LIMIT 30)');
  }

  Future<List<String>> busquedasRecientes([int n = 12]) async =>
      (await db.query('busquedas', orderBy: 'fecha DESC', limit: n)).map((f) => '${f['texto']}').toList();

  Future<void> borrarBusquedas() async => db.delete('busquedas');

  /// Quita una sola búsqueda de las recientes.
  Future<void> borrarBusqueda(String texto) async =>
      db.delete('busquedas', where: 'texto = ?', whereArgs: [texto]);

  // ------------------------------------------------------------ estado

  Future<void> guardarEstado(String clave, Object? valor) async => db.insert(
      'estado', {'clave': clave, 'valor': jsonEncode(valor)},
      conflictAlgorithm: ConflictAlgorithm.replace);

  Future<dynamic> estado(String clave) async {
    final f = await db.query('estado', where: 'clave = ?', whereArgs: [clave]);
    if (f.isEmpty) return null;
    try {
      return jsonDecode('${f.first['valor']}');
    } catch (_) {
      return null;
    }
  }

  // ------------------------------------------------------------ descargas

  /// Archivo ya descargado de un video, si lo hay: asi suena sin internet.
  Json? copiaLocal(String? videoId, {bool conVideo = false}) {
    if (videoId == null || videoId.isEmpty) return null;
    final candidatas = (_porVideo[videoId] ?? []).where((d) => _existe('${d['archivo']}'));
    if (conVideo) {
      final v = candidatas.where((d) => d['es_audio'] != 1);
      return v.isEmpty ? null : v.first;
    }
    final a = candidatas.where((d) => d['es_audio'] == 1);
    return a.isNotEmpty ? a.first : (candidatas.isEmpty ? null : candidatas.first);
  }

  final Map<String, (bool, int)> _existeCache = {};

  bool _existe(String ruta) {
    // la música de la comunidad es una dirección de internet, no un archivo
    if (ruta.startsWith('http')) return true;
    final ahora = DateTime.now().millisecondsSinceEpoch;
    final dato = _existeCache[ruta];
    if (dato != null && ahora - dato.$2 < 20000) return dato.$1;
    final existe = !kIsWeb && ruta.isNotEmpty && File(ruta).existsSync();
    _existeCache[ruta] = (existe, ahora);
    return existe;
  }

  bool estaDescargada(Json pista) {
    final archivo = pista['archivo'] as String?;
    if (archivo != null && archivo.isNotEmpty) return _existe(archivo);
    return copiaLocal(pista['video_id'] as String?) != null;
  }

  Future<int> agregarDescarga({
    required String videoId, required String url, required String titulo,
    required String artista, required String archivo, required bool esAudio,
    required int tamano, required int duracion, required String calidad,
    String caratula = '', Json? datos,
  }) async {
    final id = await db.insert('descargas', {
      'video_id': videoId, 'url': url, 'titulo': titulo, 'artista': artista,
      'archivo': archivo, 'es_audio': esAudio ? 1 : 0, 'tamano': tamano, 'duracion': duracion,
      'calidad': calidad, 'caratula': caratula, 'datos': jsonEncode(datos ?? {}), 'fecha': _ahora,
    });
    _existeCache.remove(archivo);
    await _cargarMemoria();
    notifyListeners();
    return id;
  }

  Future<List<Json>> descargadas({bool? soloAudio}) async {
    final filas = await db.query('descargas',
        where: soloAudio == null ? null : 'es_audio = ?',
        whereArgs: soloAudio == null ? null : [soloAudio ? 1 : 0], orderBy: 'fecha DESC');
    return [for (final f in filas) if (_existe('${f['archivo']}')) pistaDeDescarga(f)];
  }

  Future<void> borrarDescarga(int id) async {
    final f = await db.query('descargas', where: 'id = ?', whereArgs: [id]);
    if (f.isNotEmpty) {
      final archivo = File('${f.first['archivo']}');
      if (await archivo.exists()) await archivo.delete();
      _existeCache.remove(archivo.path);
    }
    await db.delete('descargas', where: 'id = ?', whereArgs: [id]);
    await _cargarMemoria();
    notifyListeners();
  }

  static Json pistaDeDescarga(Map<String, Object?> f) {
    Json datos = {};
    try {
      datos = Map<String, dynamic>.from(jsonDecode('${f['datos'] ?? '{}'}') as Map);
    } catch (_) {}
    final esAudio = f['es_audio'] == 1;
    return {
      ...datos,
      'tipo': 'pista',
      'clave': datos['clave'] ?? 'local:${f['id']}',
      'descarga_id': f['id'],
      'video_id': f['video_id'] ?? datos['video_id'] ?? '',
      'titulo': f['titulo'] ?? datos['titulo'] ?? '',
      'artista': f['artista'] ?? datos['artista'] ?? '',
      'artistas': datos['artistas'] ?? [if ('${f['artista'] ?? ''}'.isNotEmpty) {'nombre': f['artista'], 'id': ''}],
      'duracion': f['duracion'] ?? datos['duracion'] ?? 0,
      'miniatura': (f['caratula'] as String?)?.isNotEmpty == true ? f['caratula'] : (datos['miniatura'] ?? ''),
      'archivo': f['archivo'],
      'es_audio': esAudio,
      'es_video': !esAudio,
      'calidad': f['calidad'] ?? '',
      'tamano': f['tamano'] ?? 0,
    };
  }
}

/// Pone [ruta] dentro de [documentos] si apuntaba a los Documentos de otra
/// instalacion (`.../Application/<otro id>/Documents/...`). Lo demas, igual.
String recolocarRuta(String ruta, String documentos) {
  const marca = '/Documents/';
  final i = ruta.indexOf(marca);
  if (i < 0) return ruta;
  final base = documentos.endsWith('/') ? documentos.substring(0, documentos.length - 1) : documentos;
  if (ruta.startsWith('$base/')) return ruta;
  return '$base/${ruta.substring(i + marca.length)}';
}

String nuevoUuid() {
  final r = Random.secure();
  final b = List<int>.generate(16, (_) => r.nextInt(256));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  String h(int i) => b[i].toRadixString(16).padLeft(2, '0');
  final s = List.generate(16, h).join();
  return '${s.substring(0, 8)}-${s.substring(8, 12)}-${s.substring(12, 16)}-'
      '${s.substring(16, 20)}-${s.substring(20)}';
}


/// Las radios guardadas antes no traían imagen: se saca de su canción semilla (el id de la
/// radio es el del video, o «RDAMVM» + el del video). Lo demás se devuelve tal cual.
Map<String, dynamic> conPortadaDeRadio(Map<String, dynamic> c) {
  if (c['tipo'] != 'radio' || '${c['miniatura'] ?? ''}'.isNotEmpty) return c;
  final id = '${c['id'] ?? ''}';
  final m = RegExp(r'^(?:RDAMVM|RDAO|RD)?([A-Za-z0-9_-]{11})$').firstMatch(id);
  if (m == null) return c;
  return {...c, 'miniatura': 'https://i.ytimg.com/vi/${m.group(1)}/hqdefault.jpg'};
}
