import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

import 'catalogo.dart';

/// Traer a Caudal listas de Spotify, Apple Music y YouTube Music (lo mismo que
/// hace listas.py en el escritorio).
///
/// Se leen los datos públicos de la lista (qué canciones tiene) y cada canción
/// se busca en YouTube Music para poder sonar. Cuántas se pueden leer:
///  * YouTube / YouTube Music: la lista entera.
///  * Spotify: las 50 primeras (lo que enseña su página pública).
///  * Apple Music: lo que trae su página (unas 100).
class ErrorImportar implements Exception {
  const ErrorImportar(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

class CancionExterna {
  CancionExterna({required this.titulo, this.artista = '', this.duracion = 0, this.pista});
  final String titulo;
  final String artista;
  final int duracion;

  /// Ya resuelta (las listas de YouTube traen la pista tal cual).
  Map<String, dynamic>? pista;

  String get busqueda => [artista, titulo].where((x) => x.isNotEmpty).join(' ');
}

class ListaExterna {
  ListaExterna({required this.plataforma, required this.titulo, required this.canciones,
      this.autor = '', this.aviso = ''});
  final String plataforma;
  final String titulo;
  final String autor;
  final List<CancionExterna> canciones;
  final String aviso;
}

class Importar {
  static const _agente = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

  /// spotify, apple, youtube o '' si el enlace no es de ninguna.
  static String plataforma(String url) {
    final u = Uri.tryParse(url.trim());
    final host = (u?.host ?? '').toLowerCase();
    if (host.contains('spotify')) return 'spotify';
    if (host.contains('music.apple') || host.contains('itunes.apple')) return 'apple';
    if (host.contains('youtube') || host.contains('youtu.be')) return 'youtube';
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
    }
    throw const ErrorImportar('Pega el enlace de una lista de Spotify, Apple Music o YouTube Music.');
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
      r = await http.get(uri, headers: {
        'User-Agent': _agente,
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
      }).timeout(const Duration(seconds: 25));
    } catch (_) {
      throw ErrorImportar('No se pudo conectar con $sitio. Revisa tu internet.');
    }
    if (r.statusCode != 200) {
      throw ErrorImportar('$sitio no mostró esa lista. Comprueba que sea pública.');
    }
    return utf8.decode(r.bodyBytes, allowMalformed: true);
  }

  // ------------------------------------------------------------ Spotify

  static Future<ListaExterna> _spotify(String url) async {
    final m = RegExp(r'/(playlist|album|track)/([A-Za-z0-9]+)').firstMatch(url);
    if (m == null) {
      throw const ErrorImportar('Ese enlace de Spotify no es de una lista, un álbum ni una canción.');
    }
    final html = await _pagina('https://open.spotify.com/embed/${m.group(1)}/${m.group(2)}', 'Spotify');
    return leerSpotify(html);
  }

  /// Separado para probarlo con una página guardada.
  static ListaExterna leerSpotify(String html) {
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
    return ListaExterna(
      plataforma: 'Spotify',
      titulo: nombre.isEmpty ? 'Lista de Spotify' : nombre,
      autor: entidad is Map ? _limpiar(entidad['subtitle']) : '',
      canciones: canciones,
      aviso: canciones.length >= 50
          ? 'Spotify solo deja ver las 50 primeras canciones de una lista desde fuera de su app.'
          : '',
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
    return ListaExterna(
      plataforma: 'Apple Music',
      titulo: titulo.isEmpty ? 'Lista de Apple Music' : titulo,
      canciones: canciones,
      aviso: canciones.length >= 100
          ? 'Apple Music solo publica una parte de las listas largas: puede que falten las últimas.'
          : '',
    );
  }

  // ------------------------------------------------------------ YouTube

  static Future<ListaExterna> _youtube(String url) async {
    final u = Uri.tryParse(url);
    final lista = u?.queryParameters['list'] ?? '';
    if (lista.isEmpty) {
      throw const ErrorImportar('Ese enlace de YouTube es de un video, no de una lista. '
          'Abre la lista y comparte su enlace.');
    }
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
            pista: Map<String, dynamic>.from(p)),
    ];
    if (canciones.isEmpty) throw const ErrorImportar('Esa lista de YouTube está vacía o es privada.');
    final titulo = '${d['titulo'] ?? ''}'.trim();
    return ListaExterna(plataforma: 'YouTube Music', titulo: titulo.isEmpty ? 'Lista de YouTube' : titulo,
        autor: '${d['autor'] ?? ''}', canciones: canciones);
  }

  // ------------------------------------------------------------ buscar

  /// Busca en YouTube Music las canciones que aún no tienen pista. Avisa del
  /// avance con [alAvanzar] (hechas, total). Devuelve las pistas encontradas
  /// en el orden de la lista.
  static Future<List<Map<String, dynamic>>> resolver(ListaExterna l,
      {void Function(int hechas, int total)? alAvanzar, bool Function()? cancelado}) async {
    final total = l.canciones.length;
    var hechas = 0;
    var siguiente = 0;
    Future<void> trabajador() async {
      while (true) {
        if (cancelado?.call() ?? false) return;
        final i = siguiente++;
        if (i >= total) return;
        final c = l.canciones[i];
        if (c.pista == null) {
          for (var intento = 0; intento < 2 && c.pista == null; intento++) {
            try {
              final r = await Catalogo.buscar(c.busqueda, filtro: 'canciones', limite: 3)
                  .timeout(const Duration(seconds: 20));
              c.pista = elegir(c, r);
            } catch (_) {
              await Future<void>.delayed(const Duration(milliseconds: 600));
            }
          }
        }
        hechas++;
        alAvanzar?.call(hechas, total);
      }
    }

    await Future.wait([for (var i = 0; i < 4; i++) trabajador()]);
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
