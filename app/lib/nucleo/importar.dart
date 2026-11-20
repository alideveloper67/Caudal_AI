import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

import 'catalogo.dart';
import 'servicios_externos.dart';

/// Traer a Caudal listas de Spotify, Apple Music, YouTube Music y SoundCloud (lo
/// mismo que hace listas.py en el escritorio).
///
/// Se leen los datos públicos de la lista (qué canciones tiene) y cada canción se
/// busca en YouTube Music para poder sonar. Sin topes propios de Caudal: se pagina
/// hasta que el servicio dice que no hay más.
///  * YouTube / YouTube Music: la lista entera.
///  * Spotify: con su API oficial, tus listas enteras (si conectas tu cuenta) y los
///    álbumes; las listas de otras personas solo si la app de Caudal tiene «cuota
///    ampliada» (reglas de Spotify desde 2026). Si no, las 50 de su página pública.
///  * SoundCloud: con su API oficial (app registrada), listas y me gusta enteros. Sin
///    eso, lo poco que enseña su página pública.
///  * Apple Music: lo que trae su página (unas 100).
class ErrorImportar implements Exception {
  const ErrorImportar(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

/// El servicio pide credenciales oficiales que aún no están configuradas.
class SinCredenciales implements Exception {
  const SinCredenciales();
}

class _ListaAjena implements Exception {
  const _ListaAjena();
}

class CancionExterna {
  CancionExterna({required this.titulo, this.artista = '', this.duracion = 0, this.pista});
  final String titulo;
  final String artista;
  final int duracion;

  /// Ya resuelta (las listas de YouTube traen la pista tal cual).
  Map<String, dynamic>? pista;

  String get busqueda => [artista, titulo].where((x) => x.isNotEmpty).join(' ');
  String get nombre => artista.isNotEmpty && titulo.isNotEmpty ? '$artista - $titulo' : (titulo.isEmpty ? artista : titulo);

  Map<String, dynamic> aJson() => {
        't': titulo,
        if (artista.isNotEmpty) 'a': artista,
        if (duracion > 0) 'd': duracion,
        if (pista != null) 'p': pista,
      };

  static CancionExterna deJson(Map m) => CancionExterna(
      titulo: '${m['t'] ?? ''}',
      artista: '${m['a'] ?? ''}',
      duracion: (m['d'] as num?)?.toInt() ?? 0,
      pista: m['p'] is Map ? Map<String, dynamic>.from(m['p'] as Map) : null);
}

class ListaExterna {
  ListaExterna({required this.plataforma, required this.titulo, required this.canciones,
      this.autor = '', this.aviso = '', this.completa = true, this.meGusta = false});
  final String plataforma;
  final String titulo;
  final String autor;
  final List<CancionExterna> canciones;
  final String aviso;

  /// false si el servicio solo dejó ver una parte (el aviso dice qué falta).
  final bool completa;

  /// Son los me gusta de alguien (SoundCloud, tu Spotify).
  final bool meGusta;
}

/// Lo que va quedando al emparejar.
class ResumenEmparejado {
  ResumenEmparejado(this.hechas, this.encontradas, this.noEncontradas, {this.cancelado = false});
  final int hechas;
  final int encontradas;
  final List<String> noEncontradas;
  final bool cancelado;
}

/// «1240» -> «1 240», como se escriben los miles en español.
String miles(int n) {
  final s = n.abs().toString();
  final b = StringBuffer(n < 0 ? '-' : '');
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write(' ');
    b.write(s[i]);
  }
  return b.toString();
}

String textoAvance(int hechas, int total) => '${miles(hechas)} de ${miles(total)}';

class Importar {
  static const _agente = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

  /// Guarda de cordura: solo evita girar para siempre si un servicio repitiera su cursor.
  static const guardaPaginas = 100000;

  /// La red, cambiable en las pruebas: (url, cabeceras) -> respuesta.
  static Future<http.Response> Function(Uri url, Map<String, String> cabeceras) red =
      (u, c) => http.get(u, headers: c).timeout(const Duration(seconds: 40));

  /// Las esperas entre reintentos (en las pruebas, sin esperar).
  static Future<void> Function(Duration) dormir = (d) => Future<void>.delayed(d);

  /// spotify, apple, youtube, soundcloud o '' si el enlace no es de ninguna.
  static String plataforma(String url) {
    final u = Uri.tryParse(url.trim());
    final host = (u?.host ?? '').toLowerCase();
    if (host.contains('spotify')) return 'spotify';
    if (host.contains('music.apple') || host.contains('itunes.apple')) return 'apple';
    if (host.contains('youtube') || host.contains('youtu.be')) return 'youtube';
    if (host == 'soundcloud.com' || host.endsWith('.soundcloud.com')) return 'soundcloud';
    return '';
  }

  /// Saca el primer enlace de un texto compartido ("Escucha esto en Spotify: https://...").
  static String enlaceDe(String texto) {
    final m = RegExp(r'https?://\S+').firstMatch(texto);
    return (m?.group(0) ?? texto).trim();
  }

  static Future<ListaExterna> leer(String texto) async {
    final url = enlaceDe(texto);
    switch (plataforma(url)) {
      case 'spotify':
        return _spotify(url);
      case 'apple':
        return _apple(url);
      case 'youtube':
        return _youtube(url);
      case 'soundcloud':
        return _soundcloud(url);
    }
    throw const ErrorImportar('Pega el enlace de una lista de Spotify, Apple Music, YouTube Music o SoundCloud.');
  }

  /// Junta todas las páginas: `pedir(cursor) -> (elementos, siguiente)`. Sin tope de
  /// cantidad: sigue mientras haya `siguiente`; solo se corta si un cursor se repite.
  static Future<List<T>> paginar<T>(Future<(List<T>, Object?)> Function(Object? cursor) pedir,
      {void Function(int llevadas)? alAvanzar}) async {
    final todos = <T>[];
    final vistos = <Object>{};
    Object? cursor;
    for (var i = 0; i < guardaPaginas; i++) {
      final (elementos, siguiente) = await pedir(cursor);
      todos.addAll(elementos);
      alAvanzar?.call(todos.length);
      if (siguiente == null || siguiente == '' || vistos.contains(siguiente)) break;
      vistos.add(siguiente);
      cursor = siguiente;
    }
    return todos;
  }

  /// Una petición que respeta los «espera un poco» (429) y reintenta los fallos.
  static Future<http.Response> _pedir(Uri u, {Map<String, String> cabeceras = const {}, int reintentos = 5}) async {
    Object? ultimo;
    for (var intento = 0; intento < reintentos; intento++) {
      try {
        final r = await red(u, cabeceras);
        if (r.statusCode == 429 || r.statusCode >= 500) {
          final espera = int.tryParse(r.headers['retry-after'] ?? '') ?? 0;
          ultimo = r;
          await dormir(Duration(seconds: (espera > 0 ? espera : 1 << intento).clamp(1, 30)));
          continue;
        }
        return r;
      } catch (e) {
        ultimo = e;
        await dormir(Duration(seconds: (1 << intento).clamp(1, 20)));
      }
    }
    if (ultimo is http.Response) return ultimo;
    throw const ErrorImportar('No se pudo conectar. Revisa tu internet y vuelve a probar.');
  }

  /// Una función de Caudal en Netlify. Sin publicar o sin credenciales: SinCredenciales.
  static Future<Map> _funcion(String ruta, Map<String, String> q) async {
    http.Response r;
    try {
      r = await _pedir(ServiciosExternos.funcion(ruta, q), reintentos: 3);
    } on ErrorImportar {
      throw const SinCredenciales();
    }
    Object? d;
    try {
      d = jsonDecode(utf8.decode(r.bodyBytes, allowMalformed: true));
    } catch (_) {
      throw const SinCredenciales(); // la función no existe todavía (página 404)
    }
    if (d is! Map || d['error'] == 'sin_credenciales') throw const SinCredenciales();
    return d;
  }

  // ------------------------------------------------------------ Snaptube y otras apps

  /// Las carpetas donde Snaptube guarda lo que baja (audio y video), por si se
  /// quieren abrir directamente.
  static const carpetasSnaptube = [
    '/storage/emulated/0/snaptube/download/SnapTube Audio',
    '/storage/emulated/0/Snaptube/Download/SnapTube Audio',
    '/storage/emulated/0/SnapTube Audio',
    '/storage/emulated/0/Download/SnapTube Audio',
  ];

  static const _extAudio = {'mp3', 'm4a', 'aac', 'flac', 'wav', 'ogg', 'opus', 'webm', 'wma', 'alac', 'aiff', 'mp4'};

  /// De un nombre de archivo o una línea de texto a «artista - título»: se quita
  /// el número de lista, la extensión y los adornos típicos ("(Official Video)").
  static CancionExterna? cancionDeLinea(String linea) {
    var t = linea.trim();
    if (t.isEmpty) return null;
    t = t.replaceFirst(RegExp(r'^\s*\d{1,5}\s*[.)\-–:]\s+'), '');
    final m = RegExp(r'\.([A-Za-z0-9]{2,5})$').firstMatch(t);
    if (m != null && _extAudio.contains(m.group(1)!.toLowerCase())) t = t.substring(0, m.start);
    t = t
        .replaceAll(RegExp(r'[\(\[]\s*(official|oficial|video|vídeo|lyrics?|letra|audio|hd|hq|4k|mv|music video|visualizer)[^\)\]]*[\)\]]',
            caseSensitive: false), '')
        .replaceAll('_', ' ')
        .replaceAll(RegExp(r'\s{2,}'), ' ')
        .trim();
    if (t.length < 2) return null;
    final corte = RegExp(r'\s[-–—]\s').firstMatch(t);
    if (corte != null && corte.start > 0 && corte.end < t.length) {
      return CancionExterna(titulo: t.substring(corte.end).trim(), artista: t.substring(0, corte.start).trim());
    }
    return CancionExterna(titulo: t);
  }

  /// Una lista armada con nombres de archivo o con líneas de texto (una canción
  /// por línea). Sin tope de canciones; las repetidas se quitan.
  static ListaExterna deLineas(Iterable<String> lineas, {required String titulo, String plataforma = 'Snaptube'}) {
    final vistas = <String>{};
    final canciones = <CancionExterna>[];
    for (final l in lineas) {
      final c = cancionDeLinea(l);
      if (c == null) continue;
      if (vistas.add(c.busqueda.toLowerCase())) canciones.add(c);
    }
    if (canciones.isEmpty) throw const ErrorImportar('No se encontró ninguna canción que leer.');
    return ListaExterna(plataforma: plataforma, titulo: titulo, canciones: canciones);
  }

  static Future<String> _pagina(String url, String sitio) async {
    http.Response r;
    // en el navegador esas webs no contestan a otras: se lee por la funcion de Caudal
    final uri = kIsWeb ? Uri.parse('/api/pagina').replace(queryParameters: {'url': url}) : Uri.parse(url);
    try {
      r = await red(uri, {
        'User-Agent': _agente,
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
      });
    } catch (_) {
      throw ErrorImportar('No se pudo conectar con $sitio. Revisa tu internet.');
    }
    if (r.statusCode != 200) {
      throw ErrorImportar('$sitio no mostró esa lista. Comprueba que sea pública.');
    }
    return utf8.decode(r.bodyBytes, allowMalformed: true);
  }

  // ------------------------------------------------------------ Spotify

  static const avisoSpotifySinConexion = 'Spotify solo deja ver 50 canciones sin su conexión oficial. '
      'Si la lista es tuya, conecta tu cuenta de Spotify en «Pasar tus me gusta» y vuelve a traerla.';
  static const avisoSpotifyAjena = 'Spotify ya no deja a otras apps leer listas de otras personas: llegaron '
      'las 50 que muestra su página. Copia la lista a una tuya en Spotify, conecta tu cuenta y tráela otra vez.';

  static const _apiSpotify = 'https://api.spotify.com/v1';

  static Future<ListaExterna> _spotify(String url) async {
    final m = RegExp(r'/(playlist|album|track)/([A-Za-z0-9]+)').firstMatch(url);
    if (m == null) {
      throw const ErrorImportar('Ese enlace de Spotify no es de una lista, un álbum ni una canción.');
    }
    final tipo = m.group(1)!;
    final id = m.group(2)!;
    var ajena = false;
    // 1. tu cuenta de Spotify: tus listas y las colaborativas, enteras
    String tuyo = '';
    try {
      tuyo = await CuentaSpotify.token();
    } catch (_) {}
    if (tuyo.isNotEmpty) {
      try {
        return await spotifyApi(tipo, id, tuyo);
      } on _ListaAjena {
        ajena = true;
      } on ErrorImportar {
        rethrow;
      } catch (_) {}
    }
    // 2. la función de Caudal (las credenciales del dueño viven en Netlify)
    if (!ajena) {
      try {
        return await _spotifyPorFuncion(tipo, id);
      } on _ListaAjena {
        ajena = true;
      } on SinCredenciales {
        // se sigue con la página pública
      }
    }
    // 3. la página pública: las 50 primeras
    final html = await _pagina('https://open.spotify.com/embed/$tipo/$id', 'Spotify');
    return leerSpotify(html, aviso: ajena ? avisoSpotifyAjena : avisoSpotifySinConexion);
  }

  static List<CancionExterna> _pistasSpotify(Map pagina) {
    final salida = <CancionExterna>[];
    for (final f in (pagina['items'] as List? ?? const []).whereType<Map>()) {
      final p = f['item'] is Map ? f['item'] as Map : (f['track'] is Map ? f['track'] as Map : f);
      if (p['type'] != null && p['type'] != 'track') continue; // episodios de podcast
      final t = _limpiar(p['name']);
      if (t.isEmpty) continue;
      salida.add(CancionExterna(
          titulo: t,
          artista: (p['artists'] as List? ?? const []).whereType<Map>().map((a) => _limpiar(a['name'])).join(', '),
          duracion: ((p['duration_ms'] as num?) ?? 0) ~/ 1000));
    }
    return salida;
  }

  /// Todas las canciones desde [primera], siguiendo `next` sin tope.
  static Future<List<CancionExterna>> spotifyPaginado(String primera, String token,
      {void Function(int)? alAvanzar}) {
    return paginar<CancionExterna>((cursor) async {
      final r = await _pedir(Uri.parse('${cursor ?? primera}'), cabeceras: {'Authorization': 'Bearer $token'});
      if (r.statusCode == 401 || r.statusCode == 403) throw const _ListaAjena();
      if (r.statusCode == 404) throw const ErrorImportar('Esa lista no existe o es privada.');
      if (r.statusCode != 200) throw const ErrorImportar('Spotify no contestó bien. Prueba otra vez en un rato.');
      final d = jsonDecode(utf8.decode(r.bodyBytes)) as Map;
      final sig = d['next'];
      return (_pistasSpotify(d), sig is String && sig.isNotEmpty ? sig : null);
    }, alAvanzar: alAvanzar);
  }

  /// Un álbum o una lista entera con un token de la API oficial.
  static Future<ListaExterna> spotifyApi(String tipo, String id, String token) async {
    final cab = {'Authorization': 'Bearer $token'};
    final r = await _pedir(Uri.parse('$_apiSpotify/${tipo}s/$id'), cabeceras: cab);
    if (r.statusCode == 404) throw const ErrorImportar('Esa lista no existe o es privada.');
    if (r.statusCode == 401 || r.statusCode == 403) throw const _ListaAjena();
    if (r.statusCode != 200) throw const ErrorImportar('Spotify no contestó bien. Prueba otra vez en un rato.');
    final c = jsonDecode(utf8.decode(r.bodyBytes)) as Map;
    if (tipo == 'track') {
      final l = _pistasSpotify({'items': [c]});
      return ListaExterna(plataforma: 'Spotify', titulo: _limpiar(c['name']), canciones: l);
    }
    List<CancionExterna> canciones;
    String autor;
    if (tipo == 'album') {
      canciones = await spotifyPaginado('$_apiSpotify/albums/$id/tracks?limit=50', token);
      autor = (c['artists'] as List? ?? const []).whereType<Map>().map((a) => _limpiar(a['name'])).join(', ');
    } else {
      try {
        canciones = await spotifyPaginado('$_apiSpotify/playlists/$id/items?limit=50', token);
      } on _ListaAjena {
        // la ruta de siempre: solo contesta a las apps con cuota ampliada
        canciones = await spotifyPaginado('$_apiSpotify/playlists/$id/tracks?limit=100', token);
      }
      autor = _limpiar((c['owner'] as Map?)?['display_name']);
    }
    if (canciones.isEmpty) throw const ErrorImportar('Esa lista de Spotify está vacía.');
    return ListaExterna(plataforma: 'Spotify', titulo: _limpiar(c['name']), autor: autor, canciones: canciones);
  }

  /// La función /api/spotify pagina en el servidor y entrega de a trozos.
  static Future<ListaExterna> _spotifyPorFuncion(String tipo, String id) async {
    var titulo = '';
    var autor = '';
    final canciones = await paginar<CancionExterna>((desde) async {
      final d = await _funcion('/api/spotify', {'tipo': tipo, 'id': id, 'desde': '${desde ?? 0}'});
      if (d['error'] == 'lista_ajena') throw const _ListaAjena();
      if (d['error'] != null) throw ErrorImportar('${d['mensaje'] ?? 'Spotify no devolvió esa lista.'}');
      if (desde == null) {
        titulo = '${d['titulo'] ?? ''}';
        autor = '${d['autor'] ?? ''}';
      }
      final sig = d['siguiente'];
      return (_cancionesSimples(d['canciones']), sig is num ? sig.toInt() : null);
    });
    if (canciones.isEmpty) throw const ErrorImportar('Esa lista de Spotify está vacía.');
    return ListaExterna(plataforma: 'Spotify', titulo: titulo.isEmpty ? 'Lista de Spotify' : titulo,
        autor: autor, canciones: canciones);
  }

  static List<CancionExterna> _cancionesSimples(Object? l) => [
        for (final c in (l is List ? l : const []).whereType<Map>())
          if ('${c['titulo'] ?? ''}'.trim().isNotEmpty)
            CancionExterna(titulo: '${c['titulo']}'.trim(), artista: '${c['artista'] ?? ''}'.trim(),
                duracion: (c['duracion'] as num?)?.toInt() ?? 0)
      ];

  /// Tus «Canciones que te gustan» de Spotify (hace falta tu cuenta conectada).
  static Future<ListaExterna> meGustaSpotify({void Function(int)? alAvanzar}) async {
    final token = await CuentaSpotify.token();
    if (token.isEmpty) throw const ErrorImportar('Conecta tu cuenta de Spotify para traer tus me gusta.');
    try {
      final c = await spotifyPaginado('$_apiSpotify/me/tracks?limit=50', token, alAvanzar: alAvanzar);
      return ListaExterna(plataforma: 'Spotify', titulo: 'Me gusta de Spotify', canciones: c, meGusta: true);
    } on _ListaAjena {
      throw const ErrorImportar('Spotify no dejó leer tus me gusta. Vuelve a conectar tu cuenta; si sigue igual, '
          'pide al dueño de Caudal que te añada como usuario de la app.');
    }
  }

  /// Separado para probarlo con una página guardada.
  static ListaExterna leerSpotify(String html, {String aviso = avisoSpotifySinConexion}) {
    final bloque = RegExp(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', dotAll: true).firstMatch(html);
    if (bloque == null) throw const ErrorImportar('No se pudieron leer las canciones de Spotify.');
    final Object? datos;
    try {
      datos = jsonDecode(bloque.group(1)!);
    } catch (_) {
      throw const ErrorImportar('No se pudieron leer las canciones de Spotify.');
    }
    final entidad = _buscar(datos, 'entity');
    final pistas = (entidad is Map ? entidad['trackList'] : null) ?? _buscar(datos, 'trackList');
    final canciones = <CancionExterna>[];
    if (pistas is List) {
      for (final p in pistas.whereType<Map>()) {
        final t = _limpiar(p['title']);
        if (t.isEmpty) continue;
        canciones.add(CancionExterna(titulo: t, artista: _limpiar(p['subtitle']),
            duracion: ((p['duration'] as num?) ?? 0) ~/ 1000));
      }
    }
    if (canciones.isEmpty) throw const ErrorImportar('Esa lista de Spotify está vacía o es privada.');
    final nombre = entidad is Map ? _limpiar(entidad['name']) : '';
    final parcial = canciones.length >= 50;
    return ListaExterna(
      plataforma: 'Spotify',
      titulo: nombre.isEmpty ? 'Lista de Spotify' : nombre,
      autor: entidad is Map ? _limpiar(entidad['subtitle']) : '',
      canciones: canciones,
      completa: !parcial,
      aviso: parcial ? aviso : '',
    );
  }

  // ------------------------------------------------------------ SoundCloud

  static const mensajeSoundcloudSinConexion = 'Para leer los me gusta de SoundCloud hace falta su conexión '
      'oficial, y el dueño de Caudal aún no la activó. Mientras tanto, pasa esas canciones a una lista pública de SoundCloud.';

  /// ('lista' | 'me_gusta' | 'perfil' | 'cancion' | 'corto' | '', ruta)
  static (String, String) tipoSoundcloud(String url) {
    final u = Uri.tryParse(url.trim());
    if (u == null) return ('', '');
    final p = u.pathSegments.where((x) => x.isNotEmpty).toList();
    if (p.isEmpty) return ('', '');
    if (u.host.toLowerCase().startsWith('on.')) return ('corto', u.path);
    const reservadas = {'discover', 'search', 'stream', 'you', 'charts', 'upload', 'settings', 'pages'};
    if (reservadas.contains(p[0])) return ('', '');
    if (p.length >= 3 && p[1] == 'sets') return ('lista', p.take(3).join('/'));
    if (p.length >= 2 && p[1] == 'likes') return ('me_gusta', p[0]);
    if (p.length == 1) return ('perfil', p[0]);
    const no = {'sets', 'tracks', 'albums', 'reposts', 'followers', 'following', 'popular-tracks', 'comments'};
    if (p.length == 2 && !no.contains(p[1])) return ('cancion', p.join('/'));
    return ('', '');
  }

  static CancionExterna cancionSoundcloud(Map t) {
    final meta = t['publisher_metadata'] is Map ? t['publisher_metadata'] as Map : const {};
    var artista = _limpiar(meta['artist']);
    if (artista.isEmpty) artista = _limpiar((t['user'] as Map?)?['username']);
    var titulo = _limpiar(t['title']);
    final m = RegExp(r'^(.+?)\s+[-–—]\s+(.+)$').firstMatch(titulo);
    if (m != null && _limpiar(meta['artist']).isEmpty) {
      artista = m.group(1)!.trim();
      titulo = m.group(2)!.trim();
    }
    return CancionExterna(titulo: titulo, artista: artista,
        duracion: (((t['duration'] ?? t['full_duration']) as num?) ?? 0) ~/ 1000);
  }

  static Future<ListaExterna> _soundcloud(String url) async {
    var (tipo, ruta) = tipoSoundcloud(url);
    if (tipo == '') {
      throw const ErrorImportar('Pega el enlace de una lista, una canción o un perfil de SoundCloud.');
    }
    var limpio = tipo == 'me_gusta' ? 'https://soundcloud.com/$ruta' : url.split('?').first;
    // 1. la función de Caudal (credenciales del dueño en Netlify); resuelve también los enlaces cortos
    try {
      var titulo = '';
      var autor = '';
      var meGusta = false;
      final canciones = await paginar<CancionExterna>((cursor) async {
        final d = await _funcion('/api/soundcloud', {'url': limpio, if (cursor != null) 'cursor': '$cursor'});
        if (d['error'] != null) throw ErrorImportar('${d['mensaje'] ?? 'SoundCloud no devolvió eso.'}');
        if (cursor == null) {
          titulo = '${d['titulo'] ?? ''}';
          autor = '${d['autor'] ?? ''}';
          meGusta = d['me_gusta'] == true;
        }
        final sig = d['siguiente'];
        return (_cancionesSimples(d['canciones']), sig is String && sig.isNotEmpty ? sig : null);
      });
      if (canciones.isEmpty) throw const ErrorImportar('Eso está vacío en SoundCloud o es privado.');
      return ListaExterna(plataforma: 'SoundCloud', titulo: titulo.isEmpty ? 'SoundCloud' : titulo,
          autor: autor, canciones: canciones, meGusta: meGusta);
    } on SinCredenciales {
      // 2. sin credenciales: la página pública
    }
    if (tipo == 'me_gusta' || tipo == 'perfil') throw const ErrorImportar(mensajeSoundcloudSinConexion);
    if (tipo == 'corto') {
      throw const ErrorImportar('Abre ese enlace corto en el navegador y pega aquí la dirección larga de la lista.');
    }
    final html = await _pagina(limpio, 'SoundCloud');
    final (lista, total) = leerSoundcloudPagina(html);
    return lista.canciones.length >= total
        ? lista
        : ListaExterna(plataforma: 'SoundCloud', titulo: lista.titulo, autor: lista.autor, canciones: lista.canciones,
            completa: false,
            aviso: 'SoundCloud solo muestra completas ${lista.canciones.length} de sus $total canciones sin su '
                'conexión oficial, que el dueño de Caudal aún no activó.');
  }

  /// Lo que trae la página pública de una lista: las primeras canciones completas y
  /// cuántas tiene en total. No se usa la clave interna de la web de SoundCloud.
  static (ListaExterna, int) leerSoundcloudPagina(String html) {
    final m = RegExp(r'window\.__sc_hydration\s*=\s*(\[.*?\]);\s*</script>', dotAll: true).firstMatch(html);
    if (m == null) throw const ErrorImportar('SoundCloud cambió su página y no se pudo leer.');
    Object? h;
    try {
      h = jsonDecode(m.group(1)!);
    } catch (_) {
      throw const ErrorImportar('La página de SoundCloud no se entendió.');
    }
    Map? lista;
    for (final x in (h is List ? h : const []).whereType<Map>()) {
      if (x['hydratable'] == 'playlist' && x['data'] is Map) lista = x['data'] as Map;
    }
    if (lista == null) throw const ErrorImportar(mensajeSoundcloudSinConexion);
    final canciones = [
      for (final t in (lista['tracks'] as List? ?? const []).whereType<Map>())
        if (_limpiar(t['title']).isNotEmpty) cancionSoundcloud(t)
    ];
    if (canciones.isEmpty) throw const ErrorImportar('Esa lista de SoundCloud está vacía o es privada.');
    final total = (lista['track_count'] as num?)?.toInt() ?? canciones.length;
    final titulo = _limpiar(lista['title']);
    return (
      ListaExterna(plataforma: 'SoundCloud', titulo: titulo.isEmpty ? 'Lista de SoundCloud' : titulo,
          autor: _limpiar((lista['user'] as Map?)?['username']), canciones: canciones),
      total
    );
  }

  // ------------------------------------------------------------ Apple Music

  static Future<ListaExterna> _apple(String url) async => leerApple(await _pagina(url, 'Apple Music'));

  static ListaExterna leerApple(String html) {
    var titulo = _meta(html, 'og:title');
    for (final c in [' on Apple Music', ' - Apple Music', ' en Apple Music']) {
      if (titulo.endsWith(c)) titulo = titulo.substring(0, titulo.length - c.length);
    }
    var canciones = <CancionExterna>[];
    final bloque = RegExp(r'<script[^>]*id="serialized-server-data"[^>]*>(.*?)</script>', dotAll: true)
        .firstMatch(html);
    if (bloque != null) {
      try {
        final vistas = <String>{};
        void recorrer(Object? o, int prof) {
          if (prof > 18) return;
          if (o is Map) {
            if (o['kind'] == 'song' || (o.containsKey('title') && o.containsKey('subtitleLinks'))) {
              final t = _limpiar(o['title'] ?? o['name']);
              final enlaces = o['subtitleLinks'];
              final artista = enlaces is List
                  ? enlaces.whereType<Map>().map((a) => _limpiar(a['title'])).where((x) => x.isNotEmpty).join(', ')
                  : '';
              final cabecera = titulo.isNotEmpty && t.toLowerCase() == titulo.toLowerCase();
              if (t.isNotEmpty && artista.isNotEmpty && !cabecera && vistas.add('$t|$artista')) {
                canciones.add(CancionExterna(titulo: t, artista: artista));
              }
            }
            for (final v in o.values) {
              recorrer(v, prof + 1);
            }
          } else if (o is List) {
            for (final v in o) {
              recorrer(v, prof + 1);
            }
          }
        }

        recorrer(jsonDecode(bloque.group(1)!), 0);
      } catch (_) {
        canciones = [];
      }
    }
    if (canciones.isEmpty) {
      // los datos para buscadores (JSON-LD), mas cortos pero estables
      for (final b in RegExp(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', dotAll: true)
          .allMatches(html)) {
        try {
          final d = jsonDecode(b.group(1)!);
          if (d is! Map || !['MusicPlaylist', 'MusicAlbum'].contains(d['@type'])) continue;
          final delAlbum = _artistaLd(d['byArtist']);
          final lista = d['track'] ?? d['tracks'];
          if (lista is List) {
            for (final p in lista.whereType<Map>()) {
              final t = _limpiar(p['name']);
              if (t.isEmpty) continue;
              final a = _artistaLd(p['byArtist']);
              canciones.add(CancionExterna(titulo: t, artista: a.isEmpty ? delAlbum : a,
                  duracion: _duracionIso('${p['duration'] ?? ''}')));
            }
          }
          if (titulo.isEmpty) titulo = _limpiar(d['name']);
          if (canciones.isNotEmpty) break;
        } catch (_) {}
      }
    }
    if (canciones.isEmpty) throw const ErrorImportar('Esa página de Apple Music no tiene canciones que leer.');
    final parcial = canciones.length >= 100;
    return ListaExterna(
      plataforma: 'Apple Music',
      titulo: titulo.isEmpty ? 'Lista de Apple Music' : titulo,
      canciones: canciones,
      completa: !parcial,
      aviso: parcial ? 'Apple Music solo publica una parte de las listas largas: puede que falten las últimas.' : '',
    );
  }

  // ------------------------------------------------------------ YouTube

  static const mensajeMeGustaYouTube = 'Tus «Me gusta» de YouTube Music son privados y Caudal no tiene permiso '
      'para leerlos. En YouTube Music abre «Música que te gusta», toca ⋮ › «Agregar a playlist», crea una lista '
      'pública o no listada y pega aquí su enlace.';

  static Future<ListaExterna> _youtube(String url) async {
    final u = Uri.tryParse(url);
    final lista = u?.queryParameters['list'] ?? '';
    if (lista.isEmpty) {
      throw const ErrorImportar('Ese enlace de YouTube es de un video, no de una lista. '
          'Abre la lista y comparte su enlace.');
    }
    if (const {'LM', 'LL', 'WL'}.contains(lista)) throw const ErrorImportar(mensajeMeGustaYouTube);
    Map<String, dynamic> d;
    try {
      d = await Catalogo.lista(lista, limite: 1 << 30);
    } catch (_) {
      throw const ErrorImportar('YouTube no mostró esa lista. Comprueba que sea pública.');
    }
    final pistas = (d['pistas'] as List?) ?? const [];
    final canciones = [
      for (final p in pistas.whereType<Map>())
        CancionExterna(titulo: '${p['titulo'] ?? ''}', artista: '${p['artista'] ?? ''}',
            duracion: (p['duracion'] as num?)?.toInt() ?? 0, pista: Map<String, dynamic>.from(p)),
    ];
    if (canciones.isEmpty) throw const ErrorImportar('Esa lista de YouTube está vacía o es privada.');
    final titulo = '${d['titulo'] ?? ''}'.trim();
    final incompleta = d['incompleta'] == true;
    return ListaExterna(plataforma: 'YouTube Music', titulo: titulo.isEmpty ? 'Lista de YouTube' : titulo,
        autor: '${d['autor'] ?? ''}', canciones: canciones, completa: !incompleta,
        aviso: incompleta ? 'Se cortó la conexión con YouTube antes del final: vuelve a traerla para completar lo que falta.' : '');
  }

  // ------------------------------------------------------------ buscar (emparejar)

  /// Busca una canción en YouTube Music. Devuelve la pista o null si de verdad no
  /// está; un fallo de red se reintenta con esperas crecientes.
  static Future<Map<String, dynamic>?> resolverUna(CancionExterna c,
      {Future<List<Map<String, dynamic>>> Function(String consulta)? buscar, int reintentos = 3}) async {
    if (c.pista != null) return c.pista;
    final consulta = c.busqueda.trim();
    if (consulta.isEmpty) return null;
    final b = buscar ??
        (q) => Catalogo.buscar(q, filtro: 'canciones', limite: 3).timeout(const Duration(seconds: 20));
    for (var intento = 0; intento < reintentos; intento++) {
      try {
        return elegir(c, await b(consulta));
      } catch (_) {
        if (intento + 1 < reintentos) await dormir(Duration(milliseconds: 800 * (1 << intento)));
      }
    }
    return null;
  }

  /// Empareja `canciones[desde:]` de lote en lote, con [hilos] búsquedas a la vez.
  /// Tras cada lote llama a [alLote] (fin, pistas encontradas en orden, nombres de las
  /// que no) para guardar lo hecho y el punto donde se va: así se puede reanudar.
  static Future<ResumenEmparejado> emparejar(List<CancionExterna> canciones,
      {int desde = 0,
      int lote = 50,
      int hilos = 4,
      Future<Map<String, dynamic>?> Function(CancionExterna c)? buscarPista,
      void Function(int hechas, int total)? alAvanzar,
      Future<void> Function(int fin, List<Map<String, dynamic>> pistas, List<String> sin)? alLote,
      bool Function()? cancelado}) async {
    final total = canciones.length;
    final buscar = buscarPista ?? (c) => resolverUna(c);
    var hechas = desde;
    var encontradas = 0;
    final faltan = <String>[];
    for (var inicio = desde; inicio < total; inicio += lote) {
      if (cancelado?.call() ?? false) {
        return ResumenEmparejado(hechas, encontradas, faltan, cancelado: true);
      }
      final trozo = canciones.sublist(inicio, inicio + lote > total ? total : inicio + lote);
      final resultados = List<Map<String, dynamic>?>.filled(trozo.length, null);
      var siguiente = 0;
      Future<void> trabajador() async {
        while (true) {
          final i = siguiente++;
          if (i >= trozo.length) return;
          try {
            resultados[i] = await buscar(trozo[i]);
          } catch (_) {
            resultados[i] = null;
          }
          hechas++;
          alAvanzar?.call(hechas, total);
        }
      }

      await Future.wait([for (var i = 0; i < hilos; i++) trabajador()]);
      final pistas = <Map<String, dynamic>>[];
      final sin = <String>[];
      for (var i = 0; i < trozo.length; i++) {
        final p = resultados[i];
        if (p != null) {
          trozo[i].pista = p;
          pistas.add(p);
        } else {
          sin.add(trozo[i].nombre);
        }
      }
      encontradas += pistas.length;
      faltan.addAll(sin);
      if (alLote != null) await alLote(inicio + trozo.length, pistas, sin);
    }
    return ResumenEmparejado(hechas, encontradas, faltan);
  }

  /// Busca en YouTube Music las canciones que aún no tienen pista. Avisa del
  /// avance con [alAvanzar] (hechas, total). Devuelve las pistas encontradas
  /// en el orden de la lista.
  static Future<List<Map<String, dynamic>>> resolver(ListaExterna l,
      {void Function(int hechas, int total)? alAvanzar, bool Function()? cancelado}) async {
    await emparejar(l.canciones, alAvanzar: alAvanzar, cancelado: cancelado);
    return [for (final c in l.canciones) if (c.pista != null) c.pista!];
  }

  /// De los resultados, el que mejor casa en título y duración.
  static Map<String, dynamic>? elegir(CancionExterna c, List<Map<String, dynamic>> r) {
    final pistas = r.where((x) => x['tipo'] == 'pista' && '${x['video_id'] ?? ''}'.isNotEmpty).toList();
    if (pistas.isEmpty) return null;
    if (c.duracion <= 0) return pistas.first;
    pistas.sort((a, b) {
      final da = ((a['duracion'] as num?) ?? 0).toInt();
      final db = ((b['duracion'] as num?) ?? 0).toInt();
      return (da - c.duracion).abs().compareTo((db - c.duracion).abs());
    });
    // el primero de la busqueda, salvo que otro case mucho mejor en duracion
    final primero = r.firstWhere((x) => pistas.contains(x));
    final dp = (((primero['duracion'] as num?) ?? 0).toInt() - c.duracion).abs();
    final dm = (((pistas.first['duracion'] as num?) ?? 0).toInt() - c.duracion).abs();
    return dp > 15 && dm + 10 < dp ? pistas.first : primero;
  }

  // ------------------------------------------------------------ ayudas

  static Object? _buscar(Object? o, String clave, [int prof = 0]) {
    if (prof > 14) return null;
    if (o is Map) {
      if (o.containsKey(clave)) return o[clave];
      for (final v in o.values) {
        final h = _buscar(v, clave, prof + 1);
        if (h != null) return h;
      }
    } else if (o is List) {
      for (final v in o.take(60)) {
        final h = _buscar(v, clave, prof + 1);
        if (h != null) return h;
      }
    }
    return null;
  }

  static String _limpiar(Object? t) => _desescapar('${t ?? ''}'.replaceAll(RegExp(r'\s+'), ' ').trim());

  static String _desescapar(String s) => s
      .replaceAll('&amp;', '&')
      .replaceAll('&quot;', '"')
      .replaceAll('&#39;', "'")
      .replaceAll('&#x27;', "'")
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>');

  static String _meta(String html, String propiedad) {
    final m = RegExp('<meta property="$propiedad" content="([^"]+)"').firstMatch(html);
    return m == null ? '' : _desescapar(m.group(1)!);
  }

  static String _artistaLd(Object? v) {
    if (v is List) return v.whereType<Map>().map((a) => _limpiar(a['name'])).join(', ');
    if (v is Map) return _limpiar(v['name']);
    return v == null ? '' : _limpiar(v);
  }

  static int _duracionIso(String t) {
    final m = RegExp(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?').firstMatch(t);
    if (m == null) return 0;
    int n(int i) => int.tryParse(m.group(i) ?? '') ?? 0;
    return n(1) * 3600 + n(2) * 60 + n(3);
  }
}
