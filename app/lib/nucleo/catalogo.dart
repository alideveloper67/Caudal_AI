// Catalogo en linea: YouTube Music para buscar y explorar.
//
// Es el port a Dart de escritorio/descargador/catalogo.py. Como en Dart no
// existe ytmusicapi, aqui se habla directamente con la API interna de YouTube
// Music (innertube): POST https://music.youtube.com/youtubei/v1/<metodo>.
//
// Las piezas que devuelve son mapas simples, con LAS MISMAS claves que en
// Python, porque las pistas se sincronizan como JSON entre la app de Windows y
// la de Android:
//
//   pista    {tipo: "pista", clave: "yt:<id>", video_id, titulo,
//             artistas: [{nombre, id}], artista, album: {nombre, id} o {},
//             duracion (segundos), miniatura, es_video, explicito, subtitulo?}
//   album    {tipo: "album", id, titulo, subtitulo, miniatura, anio?, lista_id?}
//   lista    {tipo: "lista", id (sin VL), titulo, subtitulo, miniatura}
//   artista  {tipo: "artista", id, titulo, subtitulo, miniatura, radio_id?}
//   radio    {tipo: "radio", id (playlistId), titulo, subtitulo, miniatura}
//   genero   {tipo: "genero", id, params, titulo, color: "#RRGGBB"}
//   pagina   {tipo: "pagina", id, params, titulo, subtitulo, miniatura}
//
// Secciones: {titulo, estribillo: "", estilo: carrusel|filas|rejilla|texto,
//             elementos: [...], mas: {id, params} o null, texto?}
//
// Los datos se piden en ingles (hl=en) porque asi las secciones llegan con
// nombres fijos; los titulos se traducen aqui con TRADUCCIONES.

import 'dart:async';
import 'dart:convert';
import 'dart:io' show SocketException, HttpException;

import 'package:flutter/foundation.dart' show kIsWeb, visibleForTesting;
import 'package:http/http.dart' as http;
import 'json_aparte.dart';

/// Error del catalogo, con un texto en espanol listo para ensenar al usuario.
class CatalogoError implements Exception {
  final String mensaje;
  CatalogoError(this.mensaje);

  @override
  String toString() => mensaje;
}

// ---------------------------------------------------------------- traducciones

/// Titulos de secciones y palabras sueltas de YouTube Music, en espanol.
/// Copia exacta de la tabla de Python (sin las claves repetidas).
const Map<String, String> traducciones = {
  'quick picks': 'Selección rápida',
  'song mixes': 'Mixes para ti',
  'mixed for you': 'Mezclas para ti',
  'listen again': 'Volver a escuchar',
  'new releases': 'Novedades',
  'new albums & singles': 'Álbumes y sencillos nuevos',
  'throwback jams': 'Clásicos que vuelven',
  'all-time essentials': 'Imprescindibles de siempre',
  'happy melodies': 'Melodías alegres',
  'trending community playlists': 'Listas en tendencia',
  'trending songs for you': 'Canciones en tendencia',
  'trending': 'En tendencia',
  'recommended music videos': 'Videos musicales recomendados',
  'music videos for you': 'Videos musicales para ti',
  'forgotten favorites': 'Favoritos olvidados',
  'from the community': 'De la comunidad',
  'top songs': 'Canciones más escuchadas',
  'top music videos': 'Videos musicales más vistos',
  'top artists': 'Artistas más escuchados',
  'songs': 'Canciones',
  'albums': 'Álbumes',
  'singles': 'Sencillos',
  'singles & eps': 'Sencillos y EP',
  'videos': 'Videos',
  'featured on': 'Aparece en',
  'fans might also like': 'A sus fans también les gusta',
  'playlists': 'Listas',
  'playlists by': 'Listas de',
  'live performances': 'En vivo',
  'latest episodes': 'Episodios recientes',
  'moods & moments': 'Momentos y estados de ánimo',
  'genres': 'Géneros',
  'popular': 'Popular',
  'relaxing': 'Para relajarse',
  'energizing': 'Con energía',
  'workout': 'Para entrenar',
  'commute': 'De camino',
  'focus': 'Concentración',
  'party': 'Fiesta',
  'romance': 'Romance',
  'sleep': 'Para dormir',
  'feel good': 'Buen rollo',
  'sad': 'Melancolía',
  'chill': 'Tranquilo',
  'featured playlists': 'Listas destacadas',
  'albums & singles': 'Álbumes y sencillos',
  'music videos': 'Videos musicales',
  'new music videos': 'Videos musicales nuevos',
  'romantic moods': 'Para el romance',
  'your favorites': 'Tus favoritos',
  'covers and remixes': 'Versiones y remixes',
  'long listening': 'Para escuchar largo rato',
  'mixes': 'Mixes',
  'decades': 'Décadas',
  'family': 'En familia',
  'christian & gospel': 'Cristiana y gospel',
  'country & americana': 'Country',
  'dance & electronic': 'Dance y electrónica',
  'folk & acoustic': 'Folk y acústica',
  'hip-hop en español': 'Hip-hop en español',
  'indie & alternative': 'Indie y alternativa',
  'classical': 'Clásica',
  'brazilian funk': 'Funk brasileño',
  'african': 'Africana',
  'arabic': 'Árabe',
  'blues': 'Blues',
  'metal': 'Metal',
  'pop': 'Pop',
  'r&b & soul': 'R&B y soul',
  'reggae & caribbean': 'Reggae y caribeña',
  'rock': 'Rock',
  'soundtracks & musicals': 'Bandas sonoras',
  'latin': 'Latina',
  'salsa': 'Salsa',
  'bachata': 'Bachata',
  'regional mexican': 'Regional mexicana',
  'reggaeton': 'Reguetón',
  'kids': 'Infantil',
  'holiday': 'Navidad',
  'korean hip-hop': 'Hip-hop coreano',
  'j-pop': 'J-Pop',
  'k-pop': 'K-Pop',
  'jazz': 'Jazz',
  'cumbia': 'Cumbia',
  '1980s': 'Años 80',
  '1990s': 'Años 90',
  '2000s': 'Años 2000',
  '2010s': 'Años 2010',
  '1970s': 'Años 70',
  '1960s': 'Años 60',
  'energy boosters': 'Para cargar energía',
  'gaming': 'Para jugar',
  'community playlists': 'Listas de la comunidad',
  'album': 'Álbum',
  'single': 'Sencillo',
  'ep': 'EP',
  'song': 'Canción',
  'video': 'Video',
  'playlist': 'Lista',
  'artist': 'Artista',
  'station': 'Radio',
  'views': 'reproducciones',
  'subscribers': 'suscriptores',
  'monthly audience': 'oyentes al mes',
};

final RegExp _reParecido = RegExp(r'^similar to (.+)$', caseSensitive: false);
final RegExp _reListasDe = RegExp(r'^playlists by (.+)$', caseSensitive: false);
final RegExp _reMasDe = RegExp(r'^more from (.+)$', caseSensitive: false);
final RegExp _reRadioDe = RegExp(r'^(.+) radio$', caseSensitive: false);
final RegExp _reCifra = RegExp(
    r'^([\d.,]+[KMB]?) (views|subscribers|monthly audience|plays)$',
    caseSensitive: false);
final RegExp _reDuracion = RegExp(r'^\d+:\d{2}(:\d{2})?$');
final RegExp _reDuracionLarga = RegExp(r'^(\d+:)*\d+:\d+$');
final RegExp _reAnio = RegExp(r'^\d{4}$');
final RegExp _reVistas = RegExp(r'(views|plays)', caseSensitive: false);

/// Traduce el titulo de una seccion ("Quick picks" -> "Selección rápida").
String traducir(String? texto) {
  if (texto == null || texto.isEmpty) return '';
  final limpio = texto.trim();
  final t = traducciones[limpio.toLowerCase()];
  if (t != null && t.isNotEmpty) return t;
  var m = _reParecido.firstMatch(limpio);
  if (m != null) return 'Parecido a ${m.group(1)}';
  m = _reListasDe.firstMatch(limpio);
  if (m != null) return 'Listas de ${m.group(1)}';
  m = _reMasDe.firstMatch(limpio);
  if (m != null) return 'Más de ${m.group(1)}';
  m = _reRadioDe.firstMatch(limpio);
  if (m != null && texto.length < 60) return 'Radio de ${m.group(1)}';
  return texto;
}

/// 'Album • 2021' -> 'Álbum • 2021', '1.2M views' -> '1.2M reproducciones'.
String traducirSubtitulo(String? texto) {
  if (texto == null || texto.isEmpty) return '';
  const sufijos = {
    'views': 'reproducciones',
    'plays': 'reproducciones',
    'subscribers': 'suscriptores',
    'monthly audience': 'oyentes al mes',
  };
  final salida = <String>[];
  for (final parte in texto.split('•')) {
    final p = parte.trim();
    final t = traducciones[p.toLowerCase()];
    if (t != null && t.isNotEmpty) {
      salida.add(t);
      continue;
    }
    final m = _reCifra.firstMatch(p);
    if (m != null) {
      salida.add('${m.group(1)} ${sufijos[m.group(2)!.toLowerCase()]}');
      continue;
    }
    salida.add(p);
  }
  return salida.join(' • ');
}

// ---------------------------------------------------------------- utilidades JSON

/// Recorre un JSON por claves (String) e indices (int); null si algo falta.
dynamic _nav(dynamic obj, List<Object> ruta) {
  dynamic actual = obj;
  for (final k in ruta) {
    if (actual == null) return null;
    if (k is String) {
      if (actual is! Map) return null;
      actual = actual[k];
    } else if (k is int) {
      if (actual is! List) return null;
      final i = k < 0 ? actual.length + k : k;
      if (i < 0 || i >= actual.length) return null;
      actual = actual[i];
    } else {
      return null;
    }
  }
  return actual;
}

List<dynamic> _lista(dynamic x) => x is List ? x : const [];

Map<String, dynamic> _mapa(dynamic x) =>
    x is Map ? Map<String, dynamic>.from(x) : <String, dynamic>{};

String _cadena(dynamic x) => x == null ? '' : x.toString();

List<dynamic> _runs(dynamic obj) => obj is Map ? _lista(obj['runs']) : const [];

/// Texto de un objeto de YouTube: runs, simpleText o content (view models).
String _texto(dynamic obj) {
  if (obj is! Map) return obj is String ? obj : '';
  if (obj['runs'] is List) {
    return _runs(obj).map((r) => _cadena(r is Map ? r['text'] : '')).join();
  }
  if (obj['simpleText'] != null) return _cadena(obj['simpleText']);
  if (obj['content'] != null) return _cadena(obj['content']);
  return '';
}

String _tipoPagina(dynamic browseEndpoint) => _cadena(_nav(browseEndpoint, [
      'browseEndpointContextSupportedConfigs',
      'browseEndpointContextMusicConfig',
      'pageType'
    ]));

bool _esPaginaArtista(String pt) =>
    pt == 'MUSIC_PAGE_TYPE_ARTIST' || pt == 'MUSIC_PAGE_TYPE_USER_CHANNEL';

String _sinVL(String id) => id.startsWith('VL') ? id.substring(2) : id;

String _sinTopic(String autor) =>
    autor.replaceAll(RegExp(r'\s*-\s*Topic$'), '');

// ---------------------------------------------------------------- catalogo

/// Puerta unica al catalogo de YouTube Music. Todo es estatico y asincrono.
class Catalogo {
  Catalogo._();

  static const String _dominio = 'https://music.youtube.com';
  static const String _agente =
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
  static const Duration _espera = Duration(seconds: 15);

  static String _region = 'PE';
  static http.Client? _clienteHttp;
  static final Map<String, List<dynamic>> _portadasGenero = {};

  /// Pais de los resultados (codigo de dos letras: PE, MX, ES...).
  static void fijarRegion(String codigo) {
    final c = codigo.trim().toUpperCase();
    if (c.length == 2) _region = c;
  }

  /// Region actual (solo lectura).
  static String get region => _region;

  static http.Client get _http => _clienteHttp ??= http.Client();

  static String _fechaVersion() {
    final h = DateTime.now().toUtc();
    String dos(int n) => n.toString().padLeft(2, '0');
    return '${h.year}${dos(h.month)}${dos(h.day)}';
  }

  // ------------------------------------------------------------ red

  /// POST a innertube. [cliente]: "remix" (YouTube Music web), "web"
  /// (youtube.com, para leer listas) o "movil" (letras con tiempos).
  static Future<Map<String, dynamic>> _post(
    String metodo,
    Map<String, dynamic> cuerpo, {
    String cliente = 'remix',
    String extra = '',
    String visitante = '',
  }) async {
    final Map<String, dynamic> contexto;
    String dominio = _dominio;
    if (cliente == 'web') {
      dominio = 'https://www.youtube.com';
      contexto = {
        'clientName': 'WEB',
        'clientVersion': '2.${_fechaVersion()}.00.00',
        'hl': 'en',
        'gl': _region,
      };
    } else if (cliente == 'movil') {
      contexto = {
        'clientName': 'ANDROID_MUSIC',
        'clientVersion': '7.21.50',
        'hl': 'en',
        'gl': _region,
      };
    } else {
      contexto = {
        'clientName': 'WEB_REMIX',
        'clientVersion': '1.${_fechaVersion()}.01.00',
        'hl': 'en',
        'gl': _region,
      };
    }
    final datos = <String, dynamic>{
      'context': {'client': contexto, 'user': <String, dynamic>{}},
      ...cuerpo,
    };
    // en el navegador YouTube Music no contesta a otras webs: se pasa por la
    // funcion de la propia web de Caudal (netlify/functions/yt.mjs)
    final uri = kIsWeb
        ? Uri.parse('/api/yt').replace(queryParameters: {
            'm': metodo,
            'd': dominio.contains('music.') ? 'music' : 'www',
            if (extra.isNotEmpty) 'extra': extra,
          })
        : Uri.parse('$dominio/youtubei/v1/$metodo?prettyPrint=false$extra');
    final cabeceras = kIsWeb
        ? <String, String>{'content-type': 'application/json'}
        : <String, String>{
      'user-agent': _agente,
      'accept': '*/*',
      'accept-language': 'en-US,en;q=0.9',
      'content-type': 'application/json',
      'origin': dominio,
      'x-origin': dominio,
      'referer': '$dominio/',
    };
    // x-goog-visitor-id solo se manda en las continuaciones (el token va
    // atado al visitante de la primera respuesta). Sin el, cada peticion es
    // la de un visitante nuevo y YouTube entrega la portada estandar (con
    // "Selección rápida"), sin personalizar segun lo buscado antes.
    if (visitante.isNotEmpty) cabeceras['x-goog-visitor-id'] = visitante;
    if (kIsWeb) cabeceras.remove('user-agent');
    http.Response r;
    try {
      r = await _http
          .post(uri, headers: cabeceras, body: jsonEncode(datos))
          .timeout(_espera);
    } on TimeoutException {
      throw CatalogoError(
          'YouTube Music no respondió a tiempo. Revisa tu conexión e inténtalo de nuevo.');
    } on SocketException {
      throw CatalogoError(
          'No hay conexión a internet (no se pudo llegar a YouTube Music).');
    } on HttpException catch (e) {
      throw CatalogoError('Falló la conexión con YouTube Music: ${e.message}');
    } on http.ClientException catch (e) {
      throw CatalogoError('Falló la conexión con YouTube Music: ${e.message}');
    }
    Map<String, dynamic> json;
    try {
      // las paginas de YouTube Music pesan cientos de KB: se decodifican aparte
      json = _mapa(await jsonDecodeBytesAparte(r.bodyBytes));
    } catch (_) {
      throw CatalogoError(
          'YouTube Music devolvió una respuesta que no se entiende (código ${r.statusCode}).');
    }
    if (r.statusCode >= 400) {
      final detalle = _cadena(_nav(json, ['error', 'message']));
      throw CatalogoError('YouTube Music rechazó la petición (código ${r.statusCode})'
          '${detalle.isEmpty ? '' : ': $detalle'}.');
    }
    return json;
  }

  /// El visitante que YouTube asigno a una respuesta (para continuarla).
  static String _visitanteDe(Map<String, dynamic> r) =>
      _cadena(_nav(r, ['responseContext', 'visitorData']));

  static Future<dynamic> _getJson(Uri uri, {Map<String, String>? cabeceras}) async {
    final r = await _http.get(uri, headers: cabeceras).timeout(_espera);
    if (r.statusCode != 200) return null;
    return jsonDecodeBytesAparte(r.bodyBytes);
  }

  // ------------------------------------------------------------ utilidades

  /// La URL mas grande de una lista de miniaturas, agrandada si se puede.
  static String mejorMiniatura(dynamic thumbs, [int lado = 544]) {
    if (thumbs is Map) thumbs = thumbs['thumbnails'] ?? thumbs['sources'];
    final lista = _lista(thumbs).whereType<Map>().toList();
    if (lista.isEmpty) return '';
    var mejor = lista.first;
    for (final t in lista) {
      final w = (t['width'] is num) ? t['width'] as num : 0;
      final wm = (mejor['width'] is num) ? mejor['width'] as num : 0;
      if (w > wm) mejor = t;
    }
    return agrandarMiniatura(_cadena(mejor['url']), lado);
  }

  /// Pide a googleusercontent la imagen al tamano deseado (=w544-h544-l90-rj).
  static String agrandarMiniatura(String? url, [int lado = 544]) {
    if (url == null || url.isEmpty) return '';
    var u = url;
    if (u.startsWith('//')) u = 'https:$u';
    if (u.contains('googleusercontent.com') || u.contains('ggpht.com')) {
      u = u.replaceFirst(RegExp(r'=w\d+-h\d+[^&?]*$'), '=w$lado-h$lado-l90-rj');
      u = u.replaceFirst(RegExp(r'=s\d+[^&?]*$'), '=w$lado-h$lado-l90-rj');
    }
    return u;
  }

  /// Miniatura estandar de un video de YouTube.
  static String miniaturaVideo(String? videoId) =>
      (videoId == null || videoId.isEmpty)
          ? ''
          : 'https://i.ytimg.com/vi/$videoId/hqdefault.jpg';

  /// '3:25' -> 205, '1:02:03' -> 3723. Acepta tambien numeros.
  static int segundos(dynamic texto) {
    if (texto == null) return 0;
    if (texto is num) return texto.toInt();
    final s = texto.toString().trim();
    if (s.isEmpty) return 0;
    var total = 0;
    for (final p in s.split(':')) {
      final n = int.tryParse(p.trim());
      if (n == null) return 0;
      total = total * 60 + n;
    }
    return total;
  }

  /// Saca el id de un enlace de YouTube / YouTube Music, o '' si no lo es.
  static String videoIdDe(String? url) {
    if (url == null || url.isEmpty) return '';
    final m = RegExp(r'(?:v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})')
        .firstMatch(url);
    return m?.group(1) ?? '';
  }

  /// Crea una pista con la forma comun a todas las apps.
  static Map<String, dynamic> nuevaPista(
    String videoId, {
    String titulo = '',
    List<dynamic>? artistas,
    Map<String, dynamic>? album,
    dynamic duracion = 0,
    String miniatura = '',
    bool esVideo = false,
    bool explicito = false,
  }) {
    final arts = <Map<String, dynamic>>[];
    for (final a in artistas ?? const []) {
      if (a is Map && _cadena(a['nombre']).isNotEmpty) {
        arts.add({'nombre': _cadena(a['nombre']), 'id': _cadena(a['id'])});
      }
    }
    return {
      'tipo': 'pista',
      'clave': 'yt:$videoId',
      'video_id': videoId,
      'titulo': titulo.isEmpty ? 'Sin título' : titulo,
      'artistas': arts,
      'artista': arts.map((a) => a['nombre']).join(', '),
      'album': album ?? <String, dynamic>{},
      'duracion': segundos(duracion),
      'miniatura': miniatura.isNotEmpty ? miniatura : miniaturaVideo(videoId),
      'es_video': esVideo,
      'explicito': explicito,
    };
  }

  /// Convierte un texto LRC ("[01:02.30] hola") en [[ms, texto], ...] ordenado.
  static List<List<dynamic>> lrcALineas(String? texto) {
    final reMarca = RegExp(r'\[(\d+):(\d+(?:\.\d+)?)\]');
    final filas = <List<dynamic>>[];
    for (final fila in (texto ?? '').split(RegExp(r'\r?\n'))) {
      final marcas = reMarca.allMatches(fila).toList();
      if (marcas.isEmpty) continue;
      final contenido = fila.replaceAll(reMarca, '').trim();
      for (final m in marcas) {
        final mm = int.parse(m.group(1)!);
        final ss = double.parse(m.group(2)!);
        filas.add([((mm * 60 + ss) * 1000).round(), contenido]);
      }
    }
    // orden estable por tiempo (como sorted() de Python)
    final indices = List<int>.generate(filas.length, (i) => i);
    indices.sort((a, b) {
      final c = (filas[a][0] as int).compareTo(filas[b][0] as int);
      return c != 0 ? c : a.compareTo(b);
    });
    return [for (final i in indices) filas[i]];
  }

  // ------------------------------------------------------------ analisis comun

  /// Lee una fila de texto de YouTube ("KAROL G & X • KG0516 • 3:22") como
  /// lo hace ytmusicapi: artistas, album, duracion, vistas y anio.
  static Map<String, dynamic> _leerRuns(List<dynamic> runs, {bool saltarTipo = false}) {
    const tipos = {
      'song', 'video', 'album', 'single', 'ep', 'playlist', 'artist', 'episode',
      'podcast', 'profile', 'station', 'audiobook'
    };
    var r = runs.whereType<Map>().toList();
    if (saltarTipo &&
        r.length > 2 &&
        r[0]['navigationEndpoint'] == null &&
        tipos.contains(_cadena(r[0]['text']).trim().toLowerCase()) &&
        _cadena(r[1]['text']).trim() == '•') {
      r = r.sublist(2);
    }
    final salida = <String, dynamic>{'artistas': <Map<String, dynamic>>[]};
    for (final run in r) {
      final texto = _cadena(run['text']);
      final limpio = texto.trim();
      if (limpio.isEmpty || limpio == '•' || limpio == '&' || limpio == ',') continue;
      final be = _nav(run, ['navigationEndpoint', 'browseEndpoint']);
      if (run['navigationEndpoint'] != null) {
        final id = _cadena(_nav(be, ['browseId']));
        final pt = _tipoPagina(be);
        if (pt == 'MUSIC_PAGE_TYPE_ALBUM' || id.startsWith('MPRE') || id.contains('release_detail')) {
          salida['album'] = {'nombre': texto, 'id': id};
        } else if (be != null) {
          (salida['artistas'] as List).add({'nombre': texto, 'id': id});
        }
        continue;
      }
      if (_reDuracionLarga.hasMatch(limpio)) {
        salida['duracion'] = segundos(limpio);
      } else if (_reAnio.hasMatch(limpio)) {
        salida['anio'] = limpio;
      } else if (RegExp(r'^\d').hasMatch(limpio) && limpio.contains(' ')) {
        salida['vistas'] = limpio;
      } else {
        (salida['artistas'] as List).add({'nombre': limpio, 'id': ''});
      }
    }
    return salida;
  }

  static List<Map<String, dynamic>> _artistasLimpios(List<dynamic> lista) {
    const fuera = {'song', 'video', 'album', 'single', 'ep'};
    final salida = <Map<String, dynamic>>[];
    for (final a in lista) {
      if (a is! Map) continue;
      final nombre = _cadena(a['nombre']);
      if (nombre.isEmpty || fuera.contains(nombre.toLowerCase())) continue;
      salida.add({'nombre': nombre, 'id': _cadena(a['id'])});
    }
    return salida;
  }

  /// musicTwoRowItemRenderer: tarjetas de albumes, listas, artistas, videos.
  static Map<String, dynamic>? _itemDosFilas(Map r) {
    final titulo = _texto(r['title']);
    final subtituloCrudo = _texto(r['subtitle']);
    final subtitulo = traducirSubtitulo(subtituloCrudo);
    final thumbs = _nav(r, ['thumbnailRenderer', 'musicThumbnailRenderer', 'thumbnail', 'thumbnails']) ??
        _nav(r, ['thumbnailRenderer', 'croppedSquareThumbnailRenderer', 'thumbnail', 'thumbnails']) ??
        const [];
    final mini = mejorMiniatura(thumbs);
    final nav = _mapa(r['navigationEndpoint']);
    if (nav.containsKey('watchEndpoint')) {
      final we = _mapa(nav['watchEndpoint']);
      final vid = _cadena(we['videoId']);
      if (vid.isEmpty) return null;
      final artistas = <Map<String, dynamic>>[];
      for (final run in _runs(r['subtitle'])) {
        final be = _nav(run, ['navigationEndpoint', 'browseEndpoint']);
        if (_esPaginaArtista(_tipoPagina(be))) {
          artistas.add({'nombre': _cadena(run['text']), 'id': _cadena(_nav(be, ['browseId']))});
        }
      }
      final tipoVideo = _cadena(_nav(we, [
        'watchEndpointMusicSupportedConfigs',
        'watchEndpointMusicConfig',
        'musicVideoType'
      ]));
      final esVideo = tipoVideo != 'MUSIC_VIDEO_TYPE_ATV';
      if (artistas.isEmpty) {
        final partes = subtituloCrudo.split('•').map((p) => p.trim()).toList();
        final nombre = (partes.length > 1 && (partes[0].toLowerCase() == 'song' || partes[0].toLowerCase() == 'video'))
            ? partes[1]
            : partes[0];
        if (nombre.isNotEmpty &&
            !RegExp(r'\d.*(views|plays)', caseSensitive: false).hasMatch(nombre)) {
          artistas.add({'nombre': nombre, 'id': ''});
        }
      }
      final p = nuevaPista(vid,
          titulo: titulo,
          artistas: artistas,
          miniatura: !esVideo ? mini : (mini.isNotEmpty ? mini : miniaturaVideo(vid)),
          esVideo: esVideo);
      p['subtitulo'] = subtitulo;
      return p;
    }
    if (nav.containsKey('watchPlaylistEndpoint')) {
      return {
        'tipo': 'radio',
        'id': _cadena(_nav(nav, ['watchPlaylistEndpoint', 'playlistId'])),
        'titulo': titulo,
        'subtitulo': subtitulo,
        'miniatura': mini,
      };
    }
    final be = _mapa(nav['browseEndpoint']);
    final bid = _cadena(be['browseId']);
    final tipoPag = _tipoPagina(be);
    if (tipoPag == 'MUSIC_PAGE_TYPE_ALBUM') {
      return {'tipo': 'album', 'id': bid, 'titulo': titulo, 'subtitulo': subtitulo, 'miniatura': mini};
    }
    if (_esPaginaArtista(tipoPag)) {
      return {
        'tipo': 'artista',
        'id': bid,
        'titulo': titulo,
        'subtitulo': subtitulo.isEmpty ? 'Artista' : subtitulo,
        'miniatura': mini,
      };
    }
    if (tipoPag == 'MUSIC_PAGE_TYPE_PLAYLIST' || bid.startsWith('VL')) {
      return {'tipo': 'lista', 'id': _sinVL(bid), 'titulo': titulo, 'subtitulo': subtitulo, 'miniatura': mini};
    }
    if (bid.isNotEmpty) {
      return {
        'tipo': 'pagina',
        'id': bid,
        'params': be['params'],
        'titulo': titulo,
        'subtitulo': subtitulo,
        'miniatura': mini,
      };
    }
    return null;
  }

  /// musicResponsiveListItemRenderer: filas de canciones (o albumes/artistas).
  static Map<String, dynamic>? _itemLista(Map r) {
    final columnas = [
      for (final c in _lista(r['flexColumns']))
        _mapa(_nav(c, ['musicResponsiveListItemFlexColumnRenderer', 'text']))
    ];
    if (columnas.isEmpty) return null;
    final titulo = _texto(columnas[0]);
    final vid = _cadena(_nav(r, ['playlistItemData', 'videoId']) ??
        _nav(columnas[0], ['runs', 0, 'navigationEndpoint', 'watchEndpoint', 'videoId']) ??
        _nav(r, [
          'overlay',
          'musicItemThumbnailOverlayRenderer',
          'content',
          'musicPlayButtonRenderer',
          'playNavigationEndpoint',
          'watchEndpoint',
          'videoId'
        ]));
    final thumbs = _nav(r, ['thumbnail', 'musicThumbnailRenderer', 'thumbnail', 'thumbnails']) ?? const [];
    if (vid.isEmpty) {
      // una fila que apunta a un album, artista o lista
      final be = _mapa(_nav(r, ['navigationEndpoint', 'browseEndpoint']));
      final bid = _cadena(be['browseId']);
      final tipoPag = _tipoPagina(be);
      final sub = traducirSubtitulo(columnas
          .skip(1)
          .map(_texto)
          .where((t) => t.isNotEmpty)
          .join(' • '));
      if (tipoPag == 'MUSIC_PAGE_TYPE_ALBUM') {
        return {'tipo': 'album', 'id': bid, 'titulo': titulo, 'subtitulo': sub, 'miniatura': mejorMiniatura(thumbs)};
      }
      if (_esPaginaArtista(tipoPag)) {
        return {'tipo': 'artista', 'id': bid, 'titulo': titulo, 'subtitulo': sub, 'miniatura': mejorMiniatura(thumbs)};
      }
      if (tipoPag == 'MUSIC_PAGE_TYPE_PLAYLIST') {
        return {'tipo': 'lista', 'id': _sinVL(bid), 'titulo': titulo, 'subtitulo': sub, 'miniatura': mejorMiniatura(thumbs)};
      }
      return null;
    }

    final artistas = <Map<String, dynamic>>[];
    Map<String, dynamic> album = {};
    final extra = <String>[];
    for (final col in columnas.skip(1)) {
      for (final run in _runs(col)) {
        final be = _mapa(_nav(run, ['navigationEndpoint', 'browseEndpoint']));
        final pt = _tipoPagina(be);
        final texto = _cadena(run['text']);
        if (_esPaginaArtista(pt)) {
          artistas.add({'nombre': texto, 'id': _cadena(be['browseId'])});
        } else if (pt == 'MUSIC_PAGE_TYPE_ALBUM') {
          album = {'nombre': texto, 'id': _cadena(be['browseId'])};
        } else if (!['', '•', '&', ','].contains(texto.trim())) {
          extra.add(texto.trim());
        }
      }
    }
    if (artistas.isEmpty && extra.isNotEmpty) {
      final candidato = extra.first;
      if (!['song', 'video'].contains(candidato.toLowerCase()) &&
          !RegExp(r'\d').hasMatch(candidato)) {
        artistas.add({'nombre': candidato, 'id': ''});
      }
    }
    var duracion = 0;
    for (final fc in _lista(r['fixedColumns'])) {
      final t = _texto(_nav(fc, ['musicResponsiveListItemFixedColumnRenderer', 'text'])).trim();
      if (_reDuracion.hasMatch(t)) duracion = segundos(t);
    }
    if (duracion == 0) {
      for (final e in extra) {
        if (_reDuracion.hasMatch(e)) duracion = segundos(e);
      }
    }
    final mini = mejorMiniatura(thumbs);
    // las filas son canciones (Seleccion rapida, populares...): nunca video
    final p = nuevaPista(vid,
        titulo: titulo,
        artistas: artistas,
        album: album,
        duracion: duracion,
        miniatura: mini.isNotEmpty ? mini : miniaturaVideo(vid),
        esVideo: false,
        explicito: _lista(r['badges']).isNotEmpty);
    final vistas = extra.where((e) => _reVistas.hasMatch(e)).toList();
    if (vistas.isNotEmpty) p['subtitulo'] = traducirSubtitulo(vistas.first);
    return p;
  }

  static Map<String, dynamic>? _mas(dynamic be) {
    if (be is! Map) return null;
    return {'id': be['browseId'], 'params': be['params']};
  }

  /// Convierte una seccion de YouTube Music en {titulo, estilo, elementos, mas}.
  static Map<String, dynamic>? _analizarSeccion(Map s) {
    if (s['musicCarouselShelfRenderer'] is Map) {
      final c = s['musicCarouselShelfRenderer'] as Map;
      final cab = _mapa(_nav(c, ['header', 'musicCarouselShelfBasicHeaderRenderer']));
      final titulo = _texto(cab['title']);
      final mas = _nav(cab, ['moreContentButton', 'buttonRenderer', 'navigationEndpoint', 'browseEndpoint']) ??
          _nav(cab, ['title', 'runs', 0, 'navigationEndpoint', 'browseEndpoint']);
      final elementos = <Map<String, dynamic>>[];
      var hayFilas = false;
      for (final it in _lista(c['contents'])) {
        if (it is! Map) continue;
        Map<String, dynamic>? el;
        if (it['musicTwoRowItemRenderer'] is Map) {
          el = _itemDosFilas(it['musicTwoRowItemRenderer']);
        } else if (it['musicResponsiveListItemRenderer'] is Map) {
          hayFilas = true;
          el = _itemLista(it['musicResponsiveListItemRenderer']);
        }
        if (el != null) elementos.add(el);
      }
      final todasPistas = elementos.isNotEmpty &&
          elementos.every((e) => e['tipo'] == 'pista' && e['es_video'] != true);
      return {
        'titulo': traducir(titulo),
        'estribillo': '',
        'estilo': (todasPistas && hayFilas) ? 'filas' : 'carrusel',
        'elementos': elementos,
        'mas': _mas(mas),
      };
    }
    if (s['musicShelfRenderer'] is Map) {
      final c = s['musicShelfRenderer'] as Map;
      final elementos = <Map<String, dynamic>>[];
      for (final it in _lista(c['contents'])) {
        if (it is Map && it['musicResponsiveListItemRenderer'] is Map) {
          final el = _itemLista(it['musicResponsiveListItemRenderer']);
          if (el != null) elementos.add(el);
        }
      }
      final mas = _nav(c, ['bottomEndpoint', 'browseEndpoint']) ??
          _nav(c, ['title', 'runs', 0, 'navigationEndpoint', 'browseEndpoint']);
      return {
        'titulo': traducir(_texto(c['title'])),
        'estribillo': '',
        'estilo': 'filas',
        'elementos': elementos,
        'mas': _mas(mas),
      };
    }
    if (s['gridRenderer'] is Map) {
      final c = s['gridRenderer'] as Map;
      final titulo = _texto(_nav(c, ['header', 'gridHeaderRenderer', 'title']));
      final elementos = <Map<String, dynamic>>[];
      for (final it in _lista(c['items'])) {
        if (it is! Map) continue;
        if (it['musicTwoRowItemRenderer'] is Map) {
          final el = _itemDosFilas(it['musicTwoRowItemRenderer']);
          if (el != null) elementos.add(el);
        } else if (it['musicNavigationButtonRenderer'] is Map) {
          final b = it['musicNavigationButtonRenderer'] as Map;
          final be = _mapa(_nav(b, ['clickCommand', 'browseEndpoint']));
          final crudo = _nav(b, ['solid', 'leftStripeColor']);
          final color = crudo is num ? crudo.toInt() : int.tryParse(_cadena(crudo)) ?? 0;
          elementos.add({
            'tipo': 'genero',
            'id': be['browseId'],
            'params': be['params'],
            'titulo': traducir(_texto(b['buttonText'])),
            'color': '#${(color & 0xFFFFFF).toRadixString(16).toUpperCase().padLeft(6, '0')}',
          });
        }
      }
      return {
        'titulo': traducir(titulo),
        'estribillo': '',
        'estilo': 'rejilla',
        'elementos': elementos,
        'mas': null,
      };
    }
    if (s['musicDescriptionShelfRenderer'] is Map) {
      final c = s['musicDescriptionShelfRenderer'] as Map;
      return {
        'titulo': traducir(_texto(c['header'])),
        'estribillo': '',
        'estilo': 'texto',
        'texto': _texto(c['description']),
        'elementos': <Map<String, dynamic>>[],
        'mas': null,
      };
    }
    return null;
  }

  static List<Map<String, dynamic>> _analizarSecciones(List<dynamic> contenido) {
    final salida = <Map<String, dynamic>>[];
    for (final s in contenido) {
      if (s is! Map) continue;
      final x = _analizarSeccion(s);
      if (x != null) salida.add(x);
    }
    return salida;
  }

  static bool _seccionConDatos(Map<String, dynamic> s) =>
      _lista(s['elementos']).isNotEmpty || _cadena(s['texto']).isNotEmpty;

  /// Devuelve (secciones crudas, token de continuacion) de una respuesta browse.
  static (List<dynamic>, String?) _seccionesDe(Map<String, dynamic> respuesta) {
    var contenido = _nav(respuesta, [
      'contents', 'singleColumnBrowseResultsRenderer', 'tabs', 0, 'tabRenderer', 'content', 'sectionListRenderer'
    ]);
    contenido ??= _nav(respuesta, [
      'contents', 'twoColumnBrowseResultsRenderer', 'secondaryContents', 'sectionListRenderer'
    ]);
    contenido ??= _nav(respuesta, ['contents', 'sectionListRenderer']);
    if (contenido is! Map) return (const [], null);
    final token = _nav(contenido, ['continuations', 0, 'nextContinuationData', 'continuation']);
    return (_lista(contenido['contents']), token?.toString());
  }

  static Future<Map<String, dynamic>> _browse(String browseId, [String? params]) {
    final cuerpo = <String, dynamic>{'browseId': browseId};
    if (params != null && params.isNotEmpty) cuerpo['params'] = params;
    return _post('browse', cuerpo);
  }

  static String _continuacion(String token) {
    final t = Uri.encodeQueryComponent(token);
    return '&ctoken=$t&continuation=$t&type=next';
  }

  // ------------------------------------------------------------ busqueda

  static const Map<String, String> _paramsFiltro = {
    // los mismos que calcula get_search_params() de ytmusicapi
    'canciones': 'EgWKAQIIAWoMEA4QChADEAQQCRAF',
    'videos': 'EgWKAQIQAWoMEA4QChADEAQQCRAF',
    'albumes': 'EgWKAQIYAWoMEA4QChADEAQQCRAF',
    'artistas': 'EgWKAQIgAWoMEA4QChADEAQQCRAF',
    'listas': 'Eg-KAQwIABAAGAAgACgBMABqChAEEAMQCRAFEAo%3D',
  };

  static const Map<String, String> _tipoFiltro = {
    'canciones': 'song',
    'videos': 'video',
    'albumes': 'album',
    'artistas': 'artist',
    'listas': 'playlist',
  };

  /// Sugerencias mientras se escribe (hasta 8).
  static Future<List<String>> sugerencias(String texto) async {
    final t = texto.trim();
    if (t.isEmpty) return [];
    try {
      final r = await _post('music/get_search_suggestions', {'input': t});
      final salida = <String>[];
      for (final c in _lista(_nav(r, ['contents', 0, 'searchSuggestionsSectionRenderer', 'contents']))) {
        final s = (c is Map) ? (c['searchSuggestionRenderer'] ?? c['historySuggestionRenderer']) : null;
        final q = _nav(s, ['navigationEndpoint', 'searchEndpoint', 'query']);
        if (q is String && q.isNotEmpty) salida.add(q);
      }
      return salida.take(8).toList();
    } catch (_) {
      return [];
    }
  }

  /// Busca en YouTube Music. [filtro]: null (todo), canciones, videos,
  /// albumes, artistas o listas. Con filtro se devuelven como mucho [limite].
  static Future<List<Map<String, dynamic>>> buscar(String texto,
      {String? filtro, int limite = 20}) async {
    final crudo = await _buscarCrudo(texto, filtro: filtro, limite: limite);
    final salida = <Map<String, dynamic>>[];
    for (final x in crudo) {
      final el = _elementoBusqueda(x);
      if (el != null) {
        if (x['category'] == 'Top result') el['destacado'] = true;
        salida.add(el);
      }
    }
    if (filtro != null) {
      final n = limite < 1 ? 1 : limite;
      return salida.length > n ? salida.sublist(0, n) : salida;
    }
    return salida;
  }

  /// Resultados intermedios (al estilo de ytmusicapi) antes de convertirlos.
  static Future<List<Map<String, dynamic>>> _buscarCrudo(String texto,
      {String? filtro, int limite = 20}) async {
    final t = texto.trim();
    if (t.isEmpty) return [];
    if (filtro != null && !_paramsFiltro.containsKey(filtro)) {
      throw CatalogoError('Filtro de búsqueda desconocido: $filtro');
    }
    final cuerpo = <String, dynamic>{'query': t};
    if (filtro != null) cuerpo['params'] = _paramsFiltro[filtro];
    Map<String, dynamic> r;
    try {
      r = await _post('search', cuerpo);
    } on CatalogoError catch (e) {
      throw CatalogoError('No se pudo buscar en YouTube Music. ${e.mensaje}');
    }
    final tipoForzado = filtro == null ? null : _tipoFiltro[filtro];
    var secciones = _nav(r, [
      'contents', 'tabbedSearchResultsRenderer', 'tabs', 0, 'tabRenderer', 'content', 'sectionListRenderer', 'contents'
    ]);
    secciones ??= _nav(r, ['contents', 'sectionListRenderer', 'contents']);
    final salida = <Map<String, dynamic>>[];
    for (final res in _lista(secciones)) {
      if (res is! Map) continue;
      if (res['musicCardShelfRenderer'] is Map) {
        final card = res['musicCardShelfRenderer'] as Map;
        final top = _resultadoPrincipal(card);
        if (top != null) salida.add(top);
        for (final c in _lista(card['contents'])) {
          if (c is Map && c['musicResponsiveListItemRenderer'] is Map) {
            final x = _filaBusqueda(c['musicResponsiveListItemRenderer'], null);
            if (x != null) salida.add(x);
          }
        }
        continue;
      }
      Map? estante;
      List<dynamic> filas;
      if (res['musicShelfRenderer'] is Map) {
        estante = res['musicShelfRenderer'] as Map;
        filas = _lista(estante['contents']);
        final categoria = _texto(estante['title']).toLowerCase();
        // YouTube a veces rellena con un estante de otro tipo: se salta
        if (filtro != null && categoria.isNotEmpty) {
          final esperado = {
            'canciones': 'song',
            'videos': 'video',
            'albumes': 'album',
            'artistas': 'artist',
            'listas': 'playlist',
          }[filtro]!;
          if (!categoria.contains(esperado)) continue;
        }
      } else if (res['itemSectionRenderer'] is Map) {
        filas = _lista((res['itemSectionRenderer'] as Map)['contents']);
      } else {
        continue;
      }
      for (final f in filas) {
        if (f is Map && f['musicResponsiveListItemRenderer'] is Map) {
          final x = _filaBusqueda(f['musicResponsiveListItemRenderer'], tipoForzado);
          if (x != null) salida.add(x);
        }
      }
      // mas paginas cuando se pidieron mas de las que llegan de una vez
      if (filtro != null && estante != null) {
        var token = _cadena(_nav(estante, ['continuations', 0, 'nextContinuationData', 'continuation']));
        var vueltas = 0;
        while (token.isNotEmpty && salida.length < limite && vueltas < 10) {
          vueltas++;
          Map<String, dynamic> mas;
          try {
            mas = await _post('search', cuerpo,
                extra: _continuacion(token), visitante: _visitanteDe(r));
          } catch (_) {
            break;
          }
          final cont = _mapa(_nav(mas, ['continuationContents', 'musicShelfContinuation']));
          final nuevas = _lista(cont['contents']);
          if (nuevas.isEmpty) break;
          for (final f in nuevas) {
            if (f is Map && f['musicResponsiveListItemRenderer'] is Map) {
              final x = _filaBusqueda(f['musicResponsiveListItemRenderer'], tipoForzado);
              if (x != null) salida.add(x);
            }
          }
          token = _cadena(_nav(cont, ['continuations', 0, 'nextContinuationData', 'continuation']));
        }
      }
    }
    return salida;
  }

  /// El "resultado principal" (musicCardShelfRenderer) de la busqueda sin filtro.
  static Map<String, dynamic>? _resultadoPrincipal(Map d) {
    final subRuns = _runs(d['subtitle']);
    final tipoTexto = _cadena(_nav(subRuns, [0, 'text'])).trim().toLowerCase();
    const mapa = {
      'song': 'song',
      'video': 'video',
      'artist': 'artist',
      'playlist': 'playlist',
      'station': 'station',
      'profile': 'profile',
      'podcast': 'podcast',
      'episode': 'episode',
    };
    final tipo = mapa[tipoTexto] ?? (tipoTexto.isEmpty ? null : 'album');
    if (tipo == null) return null;
    final x = <String, dynamic>{
      'category': 'Top result',
      'resultType': tipo,
      'thumbnails': _nav(d, ['thumbnail', 'musicThumbnailRenderer', 'thumbnail', 'thumbnails']),
      'title': _texto(d['title']),
    };
    final tituloBe = _nav(d, ['title', 'runs', 0, 'navigationEndpoint', 'browseEndpoint']);
    if (tipo == 'artist') {
      x['artist'] = _texto(d['title']);
      x['browseId'] = _cadena(_nav(tituloBe, ['browseId'])).isNotEmpty
          ? _cadena(_nav(tituloBe, ['browseId']))
          : _cadena(_nav(d, ['onTap', 'browseEndpoint', 'browseId']));
    }
    if (tipo == 'song' || tipo == 'video') {
      x['videoId'] = _cadena(_nav(d, ['onTap', 'watchEndpoint', 'videoId']));
      final info = _leerRuns(subRuns.length > 2 ? subRuns.sublist(2) : const []);
      x.addAll(info);
      x['explicito'] = _lista(d['subtitleBadges']).isNotEmpty;
    }
    if (tipo == 'album') {
      x['type'] = _cadena(_nav(subRuns, [0, 'text']));
      x['browseId'] = _cadena(_nav(tituloBe, ['browseId']));
      final info = _leerRuns(subRuns.length > 2 ? subRuns.sublist(2) : const []);
      x['artistas'] = info['artistas'];
      x['anio'] = info['anio'];
    }
    if (tipo == 'playlist') {
      x['browseId'] = _cadena(_nav(tituloBe, ['browseId']));
      final info = _leerRuns(subRuns.length > 2 ? subRuns.sublist(2) : const []);
      x['author'] = _lista(info['artistas']).map((a) => a['nombre']).join(', ');
    }
    return x;
  }

  /// Una fila de resultados de busqueda, en el formato intermedio.
  static Map<String, dynamic>? _filaBusqueda(Map d, String? tipo) {
    final columnas = [
      for (final c in _lista(d['flexColumns']))
        _mapa(_nav(c, ['musicResponsiveListItemFlexColumnRenderer', 'text']))
    ];
    if (columnas.isEmpty) return null;
    final juego = _mapa(_nav(d, [
      'overlay', 'musicItemThumbnailOverlayRenderer', 'content', 'musicPlayButtonRenderer', 'playNavigationEndpoint'
    ]));
    final tipoVideo = _cadena(_nav(juego, [
      'watchEndpoint', 'watchEndpointMusicSupportedConfigs', 'watchEndpointMusicConfig', 'musicVideoType'
    ]));
    final browseId = _cadena(_nav(d, ['navigationEndpoint', 'browseEndpoint', 'browseId']));
    var t = tipo;
    if (t == null) {
      if (browseId.isNotEmpty) {
        const prefijos = {
          'VM': 'playlist',
          'RD': 'playlist',
          'VL': 'playlist',
          'MPLA': 'artist',
          'MPRE': 'album',
          'MPSP': 'podcast',
          'MPED': 'episode',
          'UC': 'artist',
        };
        for (final e in prefijos.entries) {
          if (browseId.startsWith(e.key)) {
            t = e.value;
            break;
          }
        }
      } else {
        t = {
              'MUSIC_VIDEO_TYPE_ATV': 'song',
              'MUSIC_VIDEO_TYPE_PODCAST_EPISODE': 'episode',
            }[tipoVideo] ??
            'video';
      }
    }
    if (t == null) return null;
    final x = <String, dynamic>{
      'resultType': t,
      'thumbnails': _nav(d, ['thumbnail', 'musicThumbnailRenderer', 'thumbnail', 'thumbnails']),
      'title': _texto(columnas[0]),
    };
    final runs1 = <dynamic>[..._runs(columnas.length > 1 ? columnas[1] : null)];
    if (t == 'song' || t == 'video' || t == 'episode') {
      x['videoId'] = _cadena(_nav(juego, ['watchEndpoint', 'videoId'])).isNotEmpty
          ? _cadena(_nav(juego, ['watchEndpoint', 'videoId']))
          : _cadena(_nav(d, ['playlistItemData', 'videoId']) ??
              _nav(columnas[0], ['runs', 0, 'navigationEndpoint', 'watchEndpoint', 'videoId']) ??
              _nav(d, ['navigationEndpoint', 'watchEndpoint', 'videoId']));
      final runs = [...runs1];
      if (columnas.length > 2) {
        runs.add({'text': ''});
        runs.addAll(_runs(columnas[2]));
      }
      x.addAll(_leerRuns(runs, saltarTipo: true));
      x['explicito'] = _lista(d['badges']).isNotEmpty;
    } else if (t == 'album') {
      x['type'] = _cadena(_nav(runs1, [0, 'text']));
      x['browseId'] = browseId;
      final info = _leerRuns(runs1, saltarTipo: true);
      x['artistas'] = info['artistas'];
      x['anio'] = info['anio'];
      x['playlistId'] = _cadena(_nav(juego, ['watchPlaylistEndpoint', 'playlistId']) ??
          _nav(juego, ['watchEndpoint', 'playlistId']));
    } else if (t == 'artist') {
      x['artist'] = _texto(columnas[0]);
      x['browseId'] = browseId;
      for (final m in _lista(_nav(d, ['menu', 'menuRenderer', 'items']))) {
        final item = _nav(m, ['menuNavigationItemRenderer']);
        final pid = _nav(item, ['navigationEndpoint', 'watchPlaylistEndpoint', 'playlistId']);
        if (pid == null) continue;
        final icono = _cadena(_nav(item, ['icon', 'iconType']));
        if (icono == 'MIX') x['radioId'] = _cadena(pid);
        if (icono == 'MUSIC_SHUFFLE') x['shuffleId'] = _cadena(pid);
      }
    } else if (t == 'playlist') {
      x['browseId'] = browseId;
      var partes = runs1.whereType<Map>().map((r) => _cadena(r['text']).trim()).where((s) => s.isNotEmpty && s != '•').toList();
      if (partes.isNotEmpty && ['playlist', 'station'].contains(partes.first.toLowerCase())) {
        partes = partes.sublist(1);
      }
      String autor = '';
      String cuenta = '';
      for (final p in partes) {
        final m = RegExp(r'^([\d,.]+) (songs?|tracks?)$', caseSensitive: false).firstMatch(p);
        if (m != null) {
          cuenta = m.group(1)!.replaceAll(RegExp(r'[,.]'), '');
        } else if (autor.isEmpty && !RegExp(r'^\d').hasMatch(p)) {
          autor = p;
        }
      }
      x['author'] = autor;
      x['itemCount'] = cuenta;
    } else {
      return null;
    }
    return x;
  }

  /// Convierte un resultado intermedio a pista / album / artista / lista.
  static Map<String, dynamic>? _elementoBusqueda(Map<String, dynamic> x) {
    final tipo = x['resultType'];
    if (tipo == 'song' || tipo == 'video') {
      final vid = _cadena(x['videoId']);
      if (vid.isEmpty) return null;
      return nuevaPista(vid,
          titulo: _cadena(x['title']),
          artistas: _artistasLimpios(_lista(x['artistas'])),
          album: x['album'] is Map ? _mapa(x['album']) : <String, dynamic>{},
          duracion: x['duracion'] ?? 0,
          miniatura: mejorMiniatura(x['thumbnails']),
          esVideo: tipo == 'video',
          explicito: x['explicito'] == true);
    }
    if (tipo == 'album') {
      final artistas = _lista(x['artistas']).map((a) => _cadena(a['nombre'])).join(', ');
      final tipoAlbum = traducir(_cadena(x['type']).isEmpty ? 'Album' : _cadena(x['type']));
      final anio = _cadena(x['anio']);
      final sub = [tipoAlbum, artistas, anio].where((p) => p.isNotEmpty).join(' • ');
      return {
        'tipo': 'album',
        'id': _cadena(x['browseId']),
        'titulo': _cadena(x['title']),
        'subtitulo': sub,
        'miniatura': mejorMiniatura(x['thumbnails']),
        'anio': anio,
        'lista_id': _cadena(x['playlistId']),
      };
    }
    if (tipo == 'artist') {
      final nombre = _cadena(x['artist']).isNotEmpty ? _cadena(x['artist']) : _cadena(x['title']);
      return {
        'tipo': 'artista',
        'id': _cadena(x['browseId']),
        'titulo': nombre,
        'subtitulo': 'Artista',
        'miniatura': mejorMiniatura(x['thumbnails']),
        'radio_id': _cadena(x['radioId']),
      };
    }
    if (tipo == 'playlist') {
      final bid = _cadena(x['browseId']);
      return {
        'tipo': 'lista',
        'id': _sinVL(bid),
        'titulo': _cadena(x['title']),
        'subtitulo': ['Lista', _cadena(x['author']), _cadena(x['itemCount'])]
            .where((p) => p.isNotEmpty)
            .join(' • '),
        'miniatura': mejorMiniatura(x['thumbnails']),
      };
    }
    return null;
  }

  /// La pagina "Todo" de la busqueda, como en Spotify: resultado principal y
  /// una seccion por tipo. Cada seccion se pide filtrada y en paralelo, porque
  /// la busqueda sin filtro de YouTube Music llega sin artistas en las canciones.
  static Future<Map<String, dynamic>> buscarTodo(String texto) async {
    final t = texto.trim();
    if (t.isEmpty) return {'principal': null, 'secciones': <Map<String, dynamic>>[]};
    const pedidos = [
      ['canciones', 8],
      ['artistas', 8],
      ['albumes', 10],
      ['listas', 10],
      ['videos', 10],
    ];
    Future<List<Map<String, dynamic>>> uno(String filtro, int n) async {
      try {
        return await buscar(t, filtro: filtro, limite: n);
      } catch (_) {
        return [];
      }
    }

    Future<Map<String, dynamic>?> principal() async {
      try {
        final crudo = await _buscarCrudo(t, limite: 5);
        for (final x in crudo) {
          if (x['category'] == 'Top result') return x;
        }
      } catch (_) {}
      return null;
    }

    final futuros = [for (final p in pedidos) uno(p[0] as String, p[1] as int)];
    final todo = await Future.wait<dynamic>([...futuros, principal()]);
    final resultados = <String, List<Map<String, dynamic>>>{};
    for (var i = 0; i < pedidos.length; i++) {
      resultados[pedidos[i][0] as String] = todo[i] as List<Map<String, dynamic>>;
    }
    final crudoPrincipal = todo.last as Map<String, dynamic>?;

    Map<String, dynamic>? destacado;
    if (crudoPrincipal != null) {
      final tipo = crudoPrincipal['resultType'];
      final vid = _cadena(crudoPrincipal['videoId']);
      if ((tipo == 'song' || tipo == 'video') && vid.isNotEmpty) {
        // el mismo elemento, pero con los datos completos de la busqueda filtrada
        for (final lista in [resultados['canciones']!, resultados['videos']!]) {
          for (final p in lista) {
            if (p['video_id'] == vid) {
              destacado = p;
              break;
            }
          }
          if (destacado != null) break;
        }
      }
      destacado ??= _elementoBusqueda(crudoPrincipal);
    }
    if (destacado == null) {
      for (final f in ['artistas', 'canciones', 'albumes']) {
        if (resultados[f]!.isNotEmpty) {
          destacado = resultados[f]!.first;
          break;
        }
      }
    }
    const nombres = {
      'canciones': 'Canciones',
      'artistas': 'Artistas',
      'albumes': 'Álbumes',
      'listas': 'Listas',
      'videos': 'Videos',
    };
    final secciones = <Map<String, dynamic>>[];
    for (final p in pedidos) {
      final filtro = p[0] as String;
      final elementos = resultados[filtro]!;
      if (elementos.isNotEmpty) {
        secciones.add({
          'titulo': nombres[filtro],
          'filtro': filtro,
          'estribillo': '',
          'estilo': filtro == 'canciones' ? 'filas' : 'carrusel',
          'elementos': elementos,
          'mas': null,
        });
      }
    }
    return {'principal': destacado, 'secciones': secciones};
  }

  // ------------------------------------------------------------ paginas

  /// Cualquier pagina de YouTube Music (inicio, generos, novedades...) en
  /// secciones. [continuar]: cuantas tandas extra pedir si hay mas.
  static Future<Map<String, dynamic>> pagina(String browseId,
      {String? params, int continuar = 1}) async {
    final respuesta = await _browse(browseId, params);
    final (contenido, tokenInicial) = _seccionesDe(respuesta);
    final secciones = _analizarSecciones(contenido);
    var token = tokenInicial;
    var vueltas = 0;
    while (token != null && token.isNotEmpty && vueltas < continuar) {
      vueltas++;
      Map<String, dynamic> mas;
      try {
        mas = await _post('browse', {},
            extra: _continuacion(token), visitante: _visitanteDe(respuesta));
      } catch (_) {
        break;
      }
      final cont = _mapa(_nav(mas, ['continuationContents', 'sectionListContinuation']));
      secciones.addAll(_analizarSecciones(_lista(cont['contents'])));
      token = _nav(cont, ['continuations', 0, 'nextContinuationData', 'continuation'])?.toString();
    }
    var titulo = _texto(_nav(respuesta, ['header', 'musicHeaderRenderer', 'title']));
    if (titulo.isEmpty) {
      titulo = _texto(_nav(respuesta, ['header', 'musicImmersiveHeaderRenderer', 'title']));
    }
    return {
      'titulo': traducir(titulo),
      'secciones': secciones.where(_seccionConDatos).toList(),
    };
  }

  /// La portada de YouTube Music (con dos tandas de continuacion).
  static Future<Map<String, dynamic>> inicio() => pagina('FEmusic_home', continuar: 2);

  /// Novedades + generos y estados de animo.
  static Future<Map<String, dynamic>> explorar() async {
    final partes = await Future.wait([
      pagina('FEmusic_new_releases').then<Map<String, dynamic>?>((v) => v).catchError((_) => null),
      pagina('FEmusic_moods_and_genres').then<Map<String, dynamic>?>((v) => v).catchError((_) => null),
    ]);
    final salida = <Map<String, dynamic>>[];
    final nuevos = partes[0];
    if (nuevos != null) {
      salida.addAll(_lista(nuevos['secciones'])
          .cast<Map<String, dynamic>>()
          .where((s) => _cadena(s['titulo']).isNotEmpty)
          .take(3));
    }
    final generos = partes[1];
    if (generos != null) {
      salida.addAll(_lista(generos['secciones'])
          .cast<Map<String, dynamic>>()
          .where((s) => _cadena(s['titulo']).isNotEmpty));
    }
    if (nuevos == null && generos == null) {
      throw CatalogoError('No se pudo cargar Explorar: YouTube Music no respondió.');
    }
    return {'titulo': 'Explorar', 'secciones': salida};
  }

  /// Donde se guardan las portadas de genero entre sesiones (la app pone aqui
  /// su colección al abrir la cuenta). Sin esto solo se guardan en memoria.
  static Future<dynamic> Function()? _leerPortadas;
  static Future<void> Function(Map<String, dynamic>)? _guardarPortadas;
  static Future<void>? _portadasLeidas;
  static Timer? _guardarPronto;

  static void guardarPortadasGeneroEn({
    required Future<dynamic> Function() leer,
    required Future<void> Function(Map<String, dynamic>) guardar,
  }) {
    _leerPortadas = leer;
    _guardarPortadas = guardar;
    _portadasLeidas = null;
  }

  static Future<void> _leerPortadasDeDisco() => _portadasLeidas ??= () async {
        final leer = _leerPortadas;
        if (leer == null) return;
        try {
          final d = await leer();
          if (d is! Map) return;
          for (final e in d.entries) {
            final v = e.value;
            if (v is! List || v.length < 2 || v[1] is! num) continue;
            _portadasGenero.putIfAbsent('${e.key}',
                () => ['${v[0]}', DateTime.fromMillisecondsSinceEpoch((v[1] as num).toInt())]);
          }
        } catch (_) {}
      }();

  static void _guardarPortadasEnDisco() {
    final guardar = _guardarPortadas;
    if (guardar == null) return;
    _guardarPronto?.cancel();
    // se juntan las de toda la pantalla en una sola escritura
    _guardarPronto = Timer(const Duration(seconds: 2), () {
      final m = <String, dynamic>{
        for (final e in _portadasGenero.entries)
          e.key: [e.value[0], (e.value[1] as DateTime).millisecondsSinceEpoch]
      };
      guardar(m).catchError((_) {});
    });
  }

  /// Cuantas paginas de genero se piden a la vez (cada tarjeta pedia la suya
  /// a la vez que todas las demas).
  static const maxPortadasALaVez = 3;
  static int _portadasEnVuelo = 0;
  static final List<Completer<void>> _portadasEnCola = [];
  static final Map<String, Future<String>> _portadasPidiendo = {};

  static Future<void> _turnoPortada() async {
    if (_portadasEnVuelo < maxPortadasALaVez) {
      _portadasEnVuelo++;
      return;
    }
    final c = Completer<void>();
    _portadasEnCola.add(c);
    await c.future; // el sitio lo pasa quien termina
  }

  static void _soltarPortada() {
    if (_portadasEnCola.isNotEmpty) {
      _portadasEnCola.removeAt(0).complete();
    } else {
      _portadasEnVuelo--;
    }
  }

  /// La portada de la primera lista de un genero, para ilustrar su tarjeta.
  /// Se guarda una semana, en memoria y en el disco (ver [guardarPortadasGeneroEn]).
  static Future<String> portadaGenero(String browseId, String? params,
      {Future<Map<String, dynamic>> Function(String browseId, String? params)? pedirPagina}) async {
    final clave = '$browseId|$params';
    await _leerPortadasDeDisco();
    final dato = _portadasGenero[clave];
    if (dato != null &&
        DateTime.now().difference(dato[1] as DateTime) < const Duration(days: 7)) {
      return dato[0] as String;
    }
    final enCurso = _portadasPidiendo[clave];
    if (enCurso != null) return enCurso;
    final f = () async {
      await _turnoPortada();
      var url = '';
      try {
        final datos = await (pedirPagina?.call(browseId, params) ??
            pagina(browseId, params: params, continuar: 0));
        for (final sec in _lista(datos['secciones'])) {
          for (final el in _lista(sec['elementos'])) {
            final m = _cadena(el['miniatura']);
            if (m.isNotEmpty) {
              url = agrandarMiniatura(m, 300);
              break;
            }
          }
          if (url.isNotEmpty) break;
        }
      } catch (_) {
        return '';
      } finally {
        _soltarPortada();
      }
      _portadasGenero[clave] = [url, DateTime.now()];
      _guardarPortadasEnDisco();
      return url;
    }();
    _portadasPidiendo[clave] = f;
    try {
      return await f;
    } finally {
      _portadasPidiendo.remove(clave);
    }
  }

  /// Para las pruebas: olvida las portadas de genero y su disco.
  @visibleForTesting
  static void olvidarPortadasGenero() {
    _portadasGenero.clear();
    _portadasPidiendo.clear();
    _leerPortadas = null;
    _guardarPortadas = null;
    _portadasLeidas = null;
    _guardarPronto?.cancel();
  }

  /// Ficha de un artista: foto, oyentes, radio y sus secciones.
  static Future<Map<String, dynamic>> artista(String browseId) async {
    final respuesta = await _browse(browseId);
    final cab = _mapa(_nav(respuesta, ['header', 'musicImmersiveHeaderRenderer']) ??
        _nav(respuesta, ['header', 'musicVisualHeaderRenderer']));
    final nombre = _texto(cab['title']);
    var descripcion = _texto(cab['description']);
    final thumbs = _nav(cab, ['thumbnail', 'musicThumbnailRenderer', 'thumbnail', 'thumbnails']) ?? const [];
    final foto = mejorMiniatura(thumbs, 1200);
    final suscriptores = _texto(_nav(cab, ['subscriptionButton', 'subscribeButtonRenderer', 'subscriberCountText']));
    final oyentes = _texto(cab['monthlyListenerCount']);
    // el boton trae watchPlaylistEndpoint o (ahora) watchEndpoint con playlistId
    String idBoton(String boton) => _cadena(_nav(cab, [
          boton, 'buttonRenderer', 'navigationEndpoint', 'watchPlaylistEndpoint', 'playlistId'
        ]) ??
        _nav(cab, [boton, 'buttonRenderer', 'navigationEndpoint', 'watchEndpoint', 'playlistId']));
    final radio = idBoton('startRadioButton');
    final aleatorio = idBoton('playButton');
    final (contenido, _) = _seccionesDe(respuesta);
    var secciones = _analizarSecciones(contenido);
    for (final s in secciones) {
      if (s['estilo'] == 'texto' && descripcion.isEmpty) descripcion = _cadena(s['texto']);
    }
    secciones = secciones.where((s) => _lista(s['elementos']).isNotEmpty).toList();
    if (nombre.isEmpty && secciones.isEmpty) {
      throw CatalogoError('No se encontró a este artista en YouTube Music.');
    }
    return {
      'tipo': 'artista',
      'id': browseId,
      'titulo': nombre,
      'foto': foto,
      'descripcion': descripcion,
      'subtitulo': traducirSubtitulo(oyentes.isNotEmpty
          ? oyentes
          : (suscriptores.isNotEmpty ? '$suscriptores subscribers' : '')),
      'radio_id': radio,
      'aleatorio_id': aleatorio,
      'secciones': secciones,
    };
  }

  /// Un album con sus canciones (portada del album en cada pista, nunca video).
  static Future<Map<String, dynamic>> album(String browseId) async {
    final r = await _browse(browseId);
    // diseno actual: cabecera en tabs[0] y canciones en secondaryContents
    var cab = _nav(r, [
      'contents', 'twoColumnBrowseResultsRenderer', 'tabs', 0, 'tabRenderer', 'content',
      'sectionListRenderer', 'contents', 0, 'musicResponsiveHeaderRenderer'
    ]);
    List<dynamic> filas = _lista(_nav(r, [
      'contents', 'twoColumnBrowseResultsRenderer', 'secondaryContents', 'sectionListRenderer',
      'contents', 0, 'musicShelfRenderer', 'contents'
    ]));
    // diseno antiguo
    cab ??= _nav(r, ['header', 'musicDetailHeaderRenderer']);
    if (filas.isEmpty) {
      filas = _lista(_nav(r, [
        'contents', 'singleColumnBrowseResultsRenderer', 'tabs', 0, 'tabRenderer', 'content',
        'sectionListRenderer', 'contents', 0, 'musicShelfRenderer', 'contents'
      ]));
    }
    if (cab is! Map) {
      throw CatalogoError('No se pudo abrir este álbum en YouTube Music.');
    }
    final titulo = _texto(cab['title']);
    final subRuns = _runs(cab['subtitle']);
    final tipoAlbum = _cadena(_nav(subRuns, [0, 'text']));
    var anio = '';
    for (final run in subRuns) {
      final t = _cadena(run is Map ? run['text'] : '').trim();
      if (_reAnio.hasMatch(t)) anio = t;
    }
    final thumbs = _nav(cab, ['thumbnail', 'musicThumbnailRenderer', 'thumbnail', 'thumbnails']) ??
        _nav(cab, ['thumbnail', 'croppedSquareThumbnailRenderer', 'thumbnail', 'thumbnails']) ??
        const [];
    final portada = mejorMiniatura(thumbs, 800);
    // artistas: straplineTextOne (nuevo) o los runs del subtitulo (antiguo)
    var artistas = <Map<String, dynamic>>[];
    final strap = _runs(cab['straplineTextOne']);
    final fuenteArtistas = strap.isNotEmpty ? strap : subRuns.skip(2).toList();
    for (final run in fuenteArtistas) {
      if (run is! Map) continue;
      final texto = _cadena(run['text']).trim();
      if (texto.isEmpty || ['•', '&', ','].contains(texto) || _reAnio.hasMatch(texto)) continue;
      final id = _cadena(_nav(run, ['navigationEndpoint', 'browseEndpoint', 'browseId']));
      if (strap.isEmpty && id.isEmpty && run['navigationEndpoint'] == null && artistas.isNotEmpty) continue;
      artistas.add({'nombre': texto, 'id': id});
    }
    artistas = _artistasLimpios(artistas);
    var descripcion = _texto(_nav(cab, ['description', 'musicDescriptionShelfRenderer', 'description']));
    if (descripcion.isEmpty) descripcion = _texto(cab['description']);
    String listaId = '';
    for (final b in _lista(cab['buttons'])) {
      final pid = _nav(b, ['musicPlayButtonRenderer', 'playNavigationEndpoint', 'watchPlaylistEndpoint', 'playlistId']) ??
          _nav(b, ['musicPlayButtonRenderer', 'playNavigationEndpoint', 'watchEndpoint', 'playlistId']);
      if (pid != null) {
        listaId = _cadena(pid);
        break;
      }
    }
    if (listaId.isEmpty) {
      for (final f in filas) {
        final pid = _nav(f, [
          'musicResponsiveListItemRenderer', 'flexColumns', 0, 'musicResponsiveListItemFlexColumnRenderer',
          'text', 'runs', 0, 'navigationEndpoint', 'watchEndpoint', 'playlistId'
        ]);
        if (pid != null) {
          listaId = _cadena(pid);
          break;
        }
      }
    }
    final alb = <String, dynamic>{'nombre': titulo, 'id': browseId};
    final pistas = <Map<String, dynamic>>[];
    for (final f in filas) {
      if (f is! Map || f['musicResponsiveListItemRenderer'] is! Map) continue;
      final p = _itemLista(f['musicResponsiveListItemRenderer']);
      if (p == null || p['tipo'] != 'pista') continue;
      p['miniatura'] = portada.isNotEmpty ? portada : p['miniatura'];
      p['album'] = Map<String, dynamic>.from(alb);
      p['es_video'] = false;
      p.remove('subtitulo');
      if (_lista(p['artistas']).isEmpty) {
        p['artistas'] = [for (final a in artistas) Map<String, dynamic>.from(a)];
        p['artista'] = artistas.map((a) => a['nombre']).join(', ');
      }
      pistas.add(p);
    }
    return {
      'tipo': 'album',
      'id': browseId,
      'titulo': titulo,
      'tipo_album': traducir(tipoAlbum.isEmpty ? 'Album' : tipoAlbum),
      'artistas': artistas,
      'anio': anio,
      'miniatura': portada,
      'descripcion': descripcion,
      'pistas': pistas,
      'duracion': pistas.fold<int>(0, (s, p) => s + (p['duracion'] as int)),
      'lista_id': listaId,
    };
  }

  /// Una lista de YouTube / YouTube Music, con sus canciones en orden.
  ///
  /// YouTube Music ya no entrega las listas a quien no inicio sesion
  /// (el browse de `VL<id>` llega vacio), asi que se leen con el cliente web de
  /// YouTube, igual que hace yt-dlp en la app de escritorio. Si eso falla, se
  /// recurre a la cola de reproduccion de YouTube Music.
  static Future<Map<String, dynamic>> lista(String playlistId, {int limite = 300}) async {
    final pid = _sinVL(playlistId.trim());
    if (pid.isEmpty) throw CatalogoError('Falta el identificador de la lista.');
    Map<String, dynamic>? r;
    try {
      r = await _post('browse', {'browseId': 'VL$pid'}, cliente: 'web');
    } on CatalogoError {
      r = null;
    }
    final pistas = <Map<String, dynamic>>[];
    var titulo = '';
    var autor = '';
    var descripcion = '';
    var portada = '';
    if (r != null) {
      final cab = _mapa(_nav(r, ['header', 'playlistHeaderRenderer']));
      titulo = _texto(cab['title']);
      if (titulo.isEmpty) titulo = _cadena(_nav(r, ['metadata', 'playlistMetadataRenderer', 'title']));
      if (titulo.isEmpty) {
        titulo = _texto(_nav(r, ['header', 'pageHeaderRenderer', 'pageTitle']));
      }
      autor = _sinTopic(_texto(cab['ownerText']));
      descripcion = _texto(cab['descriptionText']);
      if (descripcion.isEmpty) {
        descripcion = _cadena(_nav(r, ['metadata', 'playlistMetadataRenderer', 'description']));
      }
      portada = mejorMiniatura(
          _nav(cab, ['playlistHeaderBanner', 'heroPlaylistThumbnailRenderer', 'thumbnail', 'thumbnails']) ??
              _nav(r, ['microformat', 'microformatDataRenderer', 'thumbnail', 'thumbnails']),
          800);
      var items = _lista(_nav(r, [
        'contents', 'twoColumnBrowseResultsRenderer', 'tabs', 0, 'tabRenderer', 'content',
        'sectionListRenderer', 'contents', 0, 'itemSectionRenderer', 'contents'
      ]));
      // diseno clasico: playlistVideoListRenderer dentro del itemSection
      if (items.length == 1 && _nav(items, [0, 'playlistVideoListRenderer']) != null) {
        items = _lista(_nav(items, [0, 'playlistVideoListRenderer', 'contents']));
      }
      // el token puede estar al final de la lista o como seccion aparte
      var token = _tokenWeb(items) ??
          _tokenWeb(_lista(_nav(r, [
            'contents', 'twoColumnBrowseResultsRenderer', 'tabs', 0, 'tabRenderer', 'content',
            'sectionListRenderer', 'contents'
          ])));
      _pistasWeb(items, pistas, limite);
      var vueltas = 0;
      while (token != null && pistas.length < limite && vueltas < 30) {
        vueltas++;
        Map<String, dynamic> mas;
        try {
          mas = await _post('browse', {'continuation': token},
              cliente: 'web', visitante: _visitanteDe(r));
        } catch (_) {
          break;
        }
        var nuevos = <dynamic>[];
        for (final a in _lista(mas['onResponseReceivedActions'])) {
          final c = _nav(a, ['appendContinuationItemsAction', 'continuationItems']) ??
              _nav(a, ['reloadContinuationItemsCommand', 'continuationItems']);
          nuevos.addAll(_lista(c));
        }
        if (nuevos.isEmpty) break;
        final antes = pistas.length;
        _pistasWeb(nuevos, pistas, limite);
        token = _tokenWeb(nuevos);
        if (pistas.length == antes && token == null) break;
      }
    }
    if (pistas.isEmpty) {
      // respaldo: la cola de YouTube Music para esa lista
      try {
        final cola = await _cola(playlistId: pid, limite: limite, radio: false);
        pistas.addAll(cola.pistas);
        if (titulo.isEmpty) titulo = cola.tituloLista;
      } catch (_) {}
    }
    if (pistas.isEmpty && titulo.isEmpty) {
      throw CatalogoError('No se pudo abrir esta lista: es privada, se borró o YouTube no la entrega.');
    }
    if (portada.isEmpty && pistas.isNotEmpty) portada = _cadena(pistas.first['miniatura']);
    return {
      'tipo': 'lista',
      'id': pid,
      'titulo': titulo.isEmpty ? 'Lista' : titulo,
      'autor': autor,
      'descripcion': descripcion,
      'miniatura': portada,
      'pistas': pistas,
      'duracion': pistas.fold<int>(0, (s, p) => s + (p['duracion'] as int)),
    };
  }

  static String? _tokenWeb(List<dynamic> items) {
    for (final it in items.reversed) {
      final t = _nav(it, [
            'continuationItemViewModel', 'continuationCommand', 'innertubeCommand', 'continuationCommand', 'token'
          ]) ??
          _nav(it, ['continuationItemRenderer', 'continuationEndpoint', 'continuationCommand', 'token']) ??
          _nav(it, [
            'continuationItemRenderer', 'continuationEndpoint', 'commandExecutorCommand', 'commands', -1,
            'continuationCommand', 'token'
          ]);
      if (t is String && t.isNotEmpty) return t;
    }
    return null;
  }

  /// Convierte los elementos de una lista del cliente web en pistas.
  static void _pistasWeb(List<dynamic> items, List<Map<String, dynamic>> pistas, int limite) {
    for (final it in items) {
      if (pistas.length >= limite) return;
      if (it is! Map) continue;
      if (it['playlistVideoRenderer'] is Map) {
        final v = it['playlistVideoRenderer'] as Map;
        final vid = _cadena(v['videoId']);
        if (vid.length != 11) continue;
        final autor = _sinTopic(_texto(v['shortBylineText']));
        final idAutor = _cadena(_nav(v, ['shortBylineText', 'runs', 0, 'navigationEndpoint', 'browseEndpoint', 'browseId']));
        final mini = mejorMiniatura(_nav(v, ['thumbnail', 'thumbnails']));
        pistas.add(nuevaPista(vid,
            titulo: _texto(v['title']),
            artistas: autor.isEmpty ? [] : [{'nombre': autor, 'id': idAutor}],
            duracion: v['lengthSeconds'] != null
                ? int.tryParse(_cadena(v['lengthSeconds'])) ?? 0
                : segundos(_texto(v['lengthText'])),
            miniatura: mini.isNotEmpty ? mini : miniaturaVideo(vid),
            esVideo: false));
      } else if (it['lockupViewModel'] is Map) {
        final l = it['lockupViewModel'] as Map;
        if (_cadena(l['contentType']) != 'LOCKUP_CONTENT_TYPE_VIDEO') continue;
        final vid = _cadena(l['contentId']);
        if (vid.length != 11) continue;
        final meta = _mapa(_nav(l, ['metadata', 'lockupMetadataViewModel']));
        final titulo = _texto(meta['title']);
        final parte = _nav(meta, [
          'metadata', 'contentMetadataViewModel', 'metadataRows', 0, 'metadataParts', 0, 'text'
        ]);
        final autor = _sinTopic(_texto(parte));
        final idAutor = _cadena(_nav(parte, ['commandRuns', 0, 'onTap', 'innertubeCommand', 'browseEndpoint', 'browseId']));
        var duracion = 0;
        for (final o in _lista(_nav(l, ['contentImage', 'thumbnailViewModel', 'overlays']))) {
          for (final b in _lista(_nav(o, ['thumbnailBottomOverlayViewModel', 'badges']))) {
            final t = _cadena(_nav(b, ['thumbnailBadgeViewModel', 'text'])).trim();
            if (_reDuracionLarga.hasMatch(t)) duracion = segundos(t);
          }
          final t2 = _cadena(_nav(o, ['thumbnailOverlayBadgeViewModel', 'thumbnailBadges', 0, 'thumbnailBadgeViewModel', 'text'])).trim();
          if (duracion == 0 && _reDuracionLarga.hasMatch(t2)) duracion = segundos(t2);
        }
        final mini = mejorMiniatura(_nav(l, ['contentImage', 'thumbnailViewModel', 'image', 'sources']));
        pistas.add(nuevaPista(vid,
            titulo: titulo,
            artistas: autor.isEmpty ? [] : [{'nombre': autor, 'id': idAutor}],
            duracion: duracion,
            miniatura: mini.isNotEmpty ? mini : miniaturaVideo(vid),
            esVideo: false));
      }
    }
  }

  // ------------------------------------------------------------ radio

  /// Pide la cola de reproduccion (endpoint next) y sigue sus continuaciones.
  static Future<_Cola> _cola({String? videoId, String? playlistId, int limite = 50, bool radio = false}) async {
    if ((videoId == null || videoId.isEmpty) && (playlistId == null || playlistId.isEmpty)) {
      throw CatalogoError('Hace falta una canción o una lista para crear la radio.');
    }
    final cuerpo = <String, dynamic>{
      'enablePersistentPlaylistPanel': true,
      'isAudioOnly': true,
      'tunerSettingValue': 'AUTOMIX_SETTING_NORMAL',
    };
    var pid = playlistId;
    if (videoId != null && videoId.isNotEmpty) {
      cuerpo['videoId'] = videoId;
      if (pid == null || pid.isEmpty) pid = 'RDAMVM$videoId';
      if (!radio) {
        cuerpo['watchEndpointMusicSupportedConfigs'] = {
          'watchEndpointMusicConfig': {
            'hasPersistentPlaylistPanel': true,
            'musicVideoType': 'MUSIC_VIDEO_TYPE_ATV',
          }
        };
      }
    }
    cuerpo['playlistId'] = _sinVL(pid!);
    if (radio) cuerpo['params'] = 'wAEB';
    final r = await _post('next', cuerpo);
    final w = _mapa(_nav(r, [
      'contents', 'singleColumnMusicWatchNextResultsRenderer', 'tabbedRenderer', 'watchNextTabbedResultsRenderer'
    ]));
    String letrasId = '';
    String relacionadosId = '';
    for (final t in _lista(w['tabs'])) {
      final be = _nav(t, ['tabRenderer', 'endpoint', 'browseEndpoint']);
      final pt = _tipoPagina(be);
      if (pt == 'MUSIC_PAGE_TYPE_TRACK_LYRICS') letrasId = _cadena(_nav(be, ['browseId']));
      if (pt == 'MUSIC_PAGE_TYPE_TRACK_RELATED') relacionadosId = _cadena(_nav(be, ['browseId']));
    }
    final panel = _nav(w, [
      'tabs', 0, 'tabRenderer', 'content', 'musicQueueRenderer', 'content', 'playlistPanelRenderer'
    ]);
    if (panel is! Map) {
      throw CatalogoError('YouTube Music no devolvió ninguna cola para esto (¿lista privada?).');
    }
    final pistas = <Map<String, dynamic>>[];
    final vistos = <String>{};
    void anadir(List<dynamic> contenido) {
      for (final c in contenido) {
        if (pistas.length >= limite) return;
        var v = _nav(c, ['playlistPanelVideoRenderer']) ??
            _nav(c, ['playlistPanelVideoWrapperRenderer', 'primaryRenderer', 'playlistPanelVideoRenderer']);
        if (v is! Map) continue;
        final p = _pistaCola(v);
        if (p != null && vistos.add(p['video_id'] as String)) pistas.add(p);
      }
    }

    anadir(_lista(panel['contents']));
    String? token(dynamic contenedor) {
      final t = _nav(contenedor, ['continuations', 0, 'nextRadioContinuationData', 'continuation']) ??
          _nav(contenedor, ['continuations', 0, 'nextContinuationData', 'continuation']);
      return t is String && t.isNotEmpty ? t : null;
    }

    var tk = token(panel);
    var vueltas = 0;
    // las continuaciones no pueden alargar la espera sin fin: con una conexión lenta
    // la cola se entrega con lo que ya hay
    final reloj = Stopwatch()..start();
    while (tk != null && pistas.length < limite && vueltas < 15 && reloj.elapsed < const Duration(seconds: 12)) {
      vueltas++;
      Map<String, dynamic> mas;
      try {
        mas = await _post('next', cuerpo, extra: _continuacion(tk), visitante: _visitanteDe(r));
      } catch (_) {
        break;
      }
      final cont = _nav(mas, ['continuationContents', 'playlistPanelContinuation']);
      if (cont is! Map) break;
      final antes = pistas.length;
      anadir(_lista(cont['contents']));
      tk = token(cont);
      if (pistas.length == antes) break;
    }
    return _Cola(pistas, letrasId, relacionadosId, _texto(panel['title']));
  }

  /// playlistPanelVideoRenderer -> pista (las de radio nunca son video).
  static Map<String, dynamic>? _pistaCola(Map v) {
    final vid = _cadena(v['videoId']).isNotEmpty
        ? _cadena(v['videoId'])
        : _cadena(_nav(v, ['navigationEndpoint', 'watchEndpoint', 'videoId']));
    if (vid.isEmpty) return null;
    final info = _leerRuns(_runs(v['longBylineText']));
    final album = info['album'] is Map ? _mapa(info['album']) : <String, dynamic>{};
    final mini = mejorMiniatura(_nav(v, ['thumbnail', 'thumbnails']));
    return nuevaPista(vid,
        titulo: _texto(v['title']),
        artistas: _artistasLimpios(_lista(info['artistas'])),
        album: album,
        duracion: segundos(_texto(v['lengthText'])),
        miniatura: mini,
        esVideo: false,
        explicito: _lista(v['badges']).isNotEmpty);
  }

  /// ¿El fallo fue de red o de tiempo (vale la pena reintentar)?
  static bool _fallaPorRed(String m) =>
      m.contains('no respondió a tiempo') || m.contains('No hay conexión') || m.contains('Falló la conexión');

  /// La radio infinita de YouTube Music a partir de una cancion o emisora.
  /// Devuelve {pistas, letras_id, relacionados_id}.
  ///
  /// No se rinde a la primera: un fallo de red se reintenta, la radio de una
  /// canción prueba también la petición sin parámetros especiales y, si lo que
  /// falla es una emisora (la «radio del artista»), se arma con su primera
  /// canción o, como último recurso, con las canciones de la propia lista.
  static Future<Map<String, dynamic>> radio(
      {String? videoId, String? playlistId, int limite = 50}) async {
    final conVideo = videoId != null && videoId.isNotEmpty;
    final conLista = playlistId != null && playlistId.isNotEmpty;
    final soloVideo = conVideo && !conLista;
    Map<String, dynamic> hecha(_Cola c) =>
        {'pistas': c.pistas, 'letras_id': c.letrasId, 'relacionados_id': c.relacionadosId};

    CatalogoError? ultimo;
    Future<_Cola?> intentar({String? v, String? l, bool radio = false}) async {
      try {
        final c = await _cola(videoId: v, playlistId: l, limite: limite, radio: radio);
        return c.pistas.isEmpty ? null : c;
      } on CatalogoError catch (e) {
        ultimo = e;
        if (_fallaPorRed(e.mensaje)) rethrow;
        return null;
      } catch (e) {
        ultimo = CatalogoError('$e');
        return null;
      }
    }

    // 1) la petición normal; si fue la red, un segundo intento
    for (var vez = 0; vez < 2; vez++) {
      try {
        final c = await intentar(v: videoId, l: playlistId, radio: soloVideo);
        if (c != null) return hecha(c);
        break;
      } on CatalogoError {
        if (vez == 1) break;
        await Future<void>.delayed(const Duration(milliseconds: 700));
      }
    }
    // 2) la radio de una canción, sin los parámetros especiales de "radio"
    if (soloVideo) {
      try {
        final c = await intentar(v: videoId);
        if (c != null) return hecha(c);
      } on CatalogoError {/* se sigue con el mensaje del primer fallo */}
    }
    // 3) una emisora: con su primera canción, o con la propia lista
    if (conLista) {
      try {
        final l = await lista(playlistId, limite: 60);
        final deLista = [
          for (final m in _lista(l['pistas']))
            if (m is Map && '${m['video_id'] ?? ''}'.isNotEmpty) Map<String, dynamic>.from(m)
        ];
        if (deLista.isNotEmpty) {
          final c = await intentar(v: '${deLista.first['video_id']}', radio: true);
          if (c != null) return hecha(c);
          return {'pistas': deLista.take(limite).toList(), 'letras_id': '', 'relacionados_id': ''};
        }
      } on CatalogoError catch (e) {
        ultimo ??= e;
      } catch (e) {
        ultimo ??= CatalogoError('$e');
      }
    }
    throw CatalogoError('No se pudo crear la radio: ${ultimo?.mensaje ?? 'YouTube Music no devolvió canciones'}');
  }

  /// Secciones "Relacionado" de una cancion (para el panel lateral).
  static Future<List<Map<String, dynamic>>> relacionados(String videoId) async {
    final c = await _cola(videoId: videoId, limite: 1);
    if (c.relacionadosId.isEmpty) return [];
    final r = await _browse(c.relacionadosId);
    final contenido = _lista(_nav(r, ['contents', 'sectionListRenderer', 'contents']));
    return _analizarSecciones(contenido).where((s) => _lista(s['elementos']).isNotEmpty).toList();
  }

  // ------------------------------------------------------------ letras

  /// Letra de una pista: {sincronizada, lineas: [[ms, texto]...], texto, fuente}.
  /// Primero LRCLIB (sincronizadas, gratis); si no, YouTube Music.
  static Future<Map<String, dynamic>> letras(Map<String, dynamic> pista) async {
    final titulo = _cadena(pista['titulo'])
        .replaceAll(
            RegExp(r'\s*[\(\[](official|video|audio|lyric|visualizer|letra)[^\)\]]*[\)\]]',
                caseSensitive: false),
            '')
        .trim();
    var artista = '';
    final arts = _lista(pista['artistas']);
    if (arts.isNotEmpty && arts.first is Map) artista = _cadena(arts.first['nombre']);
    if (artista.isEmpty) artista = _cadena(pista['artista']);
    final dur = segundos(pista['duracion']);
    const cab = {'User-Agent': 'Caudal (reproductor)'};

    // 1) LRCLIB: letras sincronizadas, gratis y sin clave
    if (titulo.isNotEmpty && artista.isNotEmpty) {
      try {
        final params = {'track_name': titulo, 'artist_name': artista};
        if (dur > 0) params['duration'] = '$dur';
        dynamic datos = await _getJson(Uri.https('lrclib.net', '/api/get', params), cabeceras: cab);
        if (datos is! Map || datos.isEmpty) {
          final crudo = await _getJson(Uri.https('lrclib.net', '/api/search', {'q': '$artista $titulo'}),
              cabeceras: cab);
          final candidatos = _lista(crudo).whereType<Map>().toList();
          if (dur > 0) {
            candidatos.sort((a, b) {
              final da = ((a['duration'] is num ? a['duration'] as num : 0) - dur).abs();
              final db = ((b['duration'] is num ? b['duration'] as num : 0) - dur).abs();
              return da.compareTo(db);
            });
          }
          datos = null;
          for (final c in candidatos) {
            if (_cadena(c['syncedLyrics']).isNotEmpty) {
              datos = c;
              break;
            }
          }
          datos ??= candidatos.isNotEmpty ? candidatos.first : null;
        }
        if (datos is Map) {
          if (_cadena(datos['syncedLyrics']).isNotEmpty) {
            return {
              'sincronizada': true,
              'lineas': lrcALineas(_cadena(datos['syncedLyrics'])),
              'texto': _cadena(datos['plainLyrics']),
              'fuente': 'LRCLIB',
            };
          }
          if (_cadena(datos['plainLyrics']).isNotEmpty) {
            // solo texto: antes de rendirse, ver si hay otra versión con tiempos
            try {
              final crudo = await _getJson(Uri.https('lrclib.net', '/api/search', {'q': '$artista $titulo'}),
                  cabeceras: cab);
              num durDe(Map c) => c['duration'] is num ? c['duration'] as num : 0;
              final con = _lista(crudo).whereType<Map>().where((c) => _cadena(c['syncedLyrics']).isNotEmpty).toList();
              if (dur > 0) con.sort((a, b) => (durDe(a) - dur).abs().compareTo((durDe(b) - dur).abs()));
              if (con.isNotEmpty && (dur <= 0 || (durDe(con.first) - dur).abs() <= 6)) {
                return {
                  'sincronizada': true,
                  'lineas': lrcALineas(_cadena(con.first['syncedLyrics'])),
                  'texto': _cadena(con.first['plainLyrics']),
                  'fuente': 'LRCLIB',
                };
              }
            } catch (_) {}
            return {
              'sincronizada': false,
              'lineas': <List<dynamic>>[],
              'texto': _cadena(datos['plainLyrics']),
              'fuente': 'LRCLIB',
            };
          }
        }
      } catch (_) {}
    }

    // 2) YouTube Music: con tiempos (cliente movil) o en texto plano
    final vid = _cadena(pista['video_id']);
    if (vid.isNotEmpty) {
      try {
        final c = await _cola(videoId: vid, limite: 1);
        final lid = c.letrasId;
        if (lid.isNotEmpty) {
          try {
            final m = await _post('browse', {'browseId': lid}, cliente: 'movil');
            final datos = _nav(m, [
              'contents', 'elementRenderer', 'newElement', 'type', 'componentType', 'model',
              'timedLyricsModel', 'lyricsData'
            ]);
            final crudas = _lista(_nav(datos, ['timedLyricsData']));
            if (crudas.isNotEmpty && crudas.every((x) => x is Map && x['cueRange'] != null)) {
              final lineas = <List<dynamic>>[
                for (final x in crudas)
                  [
                    int.tryParse(_cadena(_nav(x, ['cueRange', 'startTimeMilliseconds']))) ?? 0,
                    _cadena(x['lyricLine'])
                  ]
              ];
              final fuente = _cadena(_nav(datos, ['sourceMessage']));
              return {
                'sincronizada': true,
                'lineas': lineas,
                'texto': '',
                'fuente': fuente.isEmpty ? 'YouTube Music' : fuente,
              };
            }
          } catch (_) {}
          final w = await _browse(lid);
          final estante = _nav(w, [
            'contents', 'sectionListRenderer', 'contents', 0, 'musicDescriptionShelfRenderer'
          ]);
          final texto = _texto(_nav(estante, ['description']));
          if (texto.isNotEmpty) {
            final fuente = _texto(_nav(estante, ['footer']));
            return {
              'sincronizada': false,
              'lineas': <List<dynamic>>[],
              'texto': texto,
              'fuente': fuente.isEmpty ? 'YouTube Music' : fuente,
            };
          }
        }
      } catch (_) {}
    }
    return {'sincronizada': false, 'lineas': <List<dynamic>>[], 'texto': '', 'fuente': ''};
  }

  // ------------------------------------------------------------ SponsorBlock

  /// Tramos que no son musica / patrocinios, de la base publica de
  /// SponsorBlock: [[inicio_s, fin_s, categoria], ...].
  static Future<List<List<dynamic>>> segmentosASaltar(String videoId, List<String> categorias) async {
    if (videoId.isEmpty || categorias.isEmpty) return [];
    try {
      final datos = await _getJson(Uri.https('sponsor.ajay.app', '/api/skipSegments', {
        'videoID': videoId,
        'categories': jsonEncode(categorias),
      }));
      final salida = <List<dynamic>>[];
      for (final s in _lista(datos)) {
        if (s is! Map) continue;
        if ((s['actionType'] ?? 'skip') != 'skip') continue;
        final seg = _lista(s['segment']);
        if (seg.length < 2) continue;
        salida.add([(seg[0] as num).toDouble(), (seg[1] as num).toDouble(), _cadena(s['category'])]);
      }
      return salida;
    } catch (_) {
      return [];
    }
  }
}

/// Resultado interno del endpoint next.
class _Cola {
  final List<Map<String, dynamic>> pistas;
  final String letrasId;
  final String relacionadosId;
  final String tituloLista;
  _Cola(this.pistas, this.letrasId, this.relacionadosId, this.tituloLista);
}
