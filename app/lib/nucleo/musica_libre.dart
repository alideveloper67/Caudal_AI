// «Música libre»: el catálogo abierto de Audius. Son canciones completas que sus artistas
// dejan sonar en otras apps (Open Music License), así que en la web suenan con el audio del
// navegador: también con el teléfono bloqueado, que es lo que YouTube no deja.
//
// Lo que pide Audius y se cumple aquí: citar al artista, enlazar la canción, no guardar el
// audio y respetar lo que el artista restringió (ver [permitida]).
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'coleccion.dart' show Json;

class MusicaLibre {
  MusicaLibre._();

  static const _base = 'https://api.audius.co/v1';
  static const _app = 'app_name=Caudal';

  static const enlaceLicencia = 'https://openaudiofoundation.org/open-music-license.pdf';
  static const enlaceTerminos = 'https://audius.co/legal/api-terms';
  static const enlacePrivacidad = 'https://audius.co/legal/privacy-policy';

  /// (cómo lo llama Audius, cómo se enseña); '' = lo más escuchado.
  static const generos = [
    ('', 'Lo más escuchado'), ('Latin', 'Latina'), ('Lo-Fi', 'Lo-Fi'), ('Electronic', 'Electrónica'),
    ('Hip-Hop/Rap', 'Hip-hop y rap'), ('Pop', 'Pop'), ('R&B/Soul', 'R&B y soul'), ('Rock', 'Rock'),
    ('House', 'House'), ('Techno', 'Techno'), ('Trap', 'Trap'), ('Ambient', 'Ambiental'),
    ('Alternative', 'Alternativa'), ('Reggae', 'Reggae'), ('Jazz', 'Jazz'), ('Classical', 'Clásica'),
  ];

  /// Para las pruebas.
  static Future<String> Function(Uri u) pedir = (u) async {
    final r = await http.get(u).timeout(const Duration(seconds: 15));
    if (r.statusCode != 200) throw Exception('Audius respondió ${r.statusCode}');
    return utf8.decode(r.bodyBytes);
  };

  static Future<List<Json>> _lista(String ruta, [Map<String, String> q = const {}]) async {
    final consulta = [for (final e in q.entries) '${e.key}=${Uri.encodeQueryComponent(e.value)}', _app].join('&');
    final d = jsonDecode(await pedir(Uri.parse('$_base/$ruta?$consulta')));
    final datos = d is Map ? d['data'] : null;
    return [
      for (final t in (datos is List ? datos : const []))
        if (t is Map && permitida(t)) comoPista(t),
    ];
  }

  /// ¿La puede poner otra app? Ni de pago, ni con permiso aparte, ni oculta, ni borrada.
  static bool permitida(Map t) {
    final acceso = t['access'];
    bool vacio(Object? v) => v == null || (v is List && v.isEmpty);
    return '${t['id'] ?? ''}'.isNotEmpty &&
        t['is_streamable'] == true &&
        t['is_stream_gated'] != true &&
        t['is_delete'] != true &&
        t['is_unlisted'] != true &&
        t['is_available'] != false &&
        vacio(t['allowed_api_keys']) &&
        vacio(t['access_authorities']) &&
        !(acceso is Map && acceso['stream'] == false);
  }

  /// Como las demás pistas sin YouTube: suena desde `archivo`, y `url_directa` por si se
  /// guarda en una lista (la nube no conserva `archivo`).
  static Json comoPista(Map t) {
    final id = '${t['id']}';
    final usuario = t['user'] is Map ? t['user'] as Map : const {};
    final fotos = t['artwork'] is Map ? t['artwork'] as Map : const {};
    final url = '$_base/tracks/$id/stream?$_app';
    final camino = '${t['permalink'] ?? ''}';
    return {
      'tipo': 'pista',
      'clave': 'aud:$id',
      'video_id': '',
      'titulo': '${t['title'] ?? ''}'.trim(),
      'artista': '${usuario['name'] ?? ''}'.trim(),
      'duracion': (t['duration'] as num?)?.toInt() ?? 0,
      'miniatura': '${fotos['480x480'] ?? fotos['150x150'] ?? ''}',
      'archivo': url,
      'url_directa': url,
      'es_audio': true,
      'audius_id': id,
      'audius_usuario': '${usuario['id'] ?? t['user_id'] ?? ''}',
      'audius_genero': '${t['genre'] ?? ''}',
      'enlace': camino.startsWith('/') ? 'https://audius.co$camino' : 'https://audius.co',
    };
  }

  static bool es(Json? p) => '${p?['audius_id'] ?? ''}'.isNotEmpty;

  static Future<List<Json>> buscar(String texto, {int limite = 30}) async =>
      texto.trim().isEmpty ? [] : _lista('tracks/search', {'query': texto.trim(), 'limit': '$limite'});

  static final Map<String, (DateTime, List<Json>)> _tendencias = {};

  /// Lo más escuchado de la semana, entero o de un género (se recuerda media hora mientras
  /// la app está abierta).
  static Future<List<Json>> tendencias({String genero = ''}) async {
    final g = _tendencias[genero];
    if (g != null && DateTime.now().difference(g.$1) < const Duration(minutes: 30)) return g.$2;
    final l = await _lista('tracks/trending', {if (genero.isNotEmpty) 'genre': genero, 'time': 'week'});
    if (l.isNotEmpty) _tendencias[genero] = (DateTime.now(), l);
    return l;
  }

  /// Para que la música siga: más de ese artista mezclado con lo mejor de su género.
  static Future<List<Json>> parecidas(Json p, {Set<String> sin = const {}, int limite = 25}) async {
    Future<List<Json>> seguro(Future<List<Json>> f) => f.catchError((_) => <Json>[]);
    final usuario = '${p['audius_usuario'] ?? ''}';
    final (suyas, genero) = await (
      usuario.isEmpty ? Future.value(<Json>[]) : seguro(_lista('users/$usuario/tracks', {'limit': '20'})),
      seguro(tendencias(genero: '${p['audius_genero'] ?? ''}')),
    ).wait;
    var resto = genero;
    if (resto.length < 5) resto = [...resto, ...await seguro(tendencias())];
    final vistas = {...sin, '${p['clave']}'};
    final salida = <Json>[];
    // una del artista cada cuatro
    final a = suyas.take(8).toList(), b = List.of(resto)..shuffle();
    var i = 0, j = 0;
    while (salida.length < limite && (i < a.length || j < b.length)) {
      final x = (salida.length % 4 == 0 && i < a.length) || j >= b.length ? a[i++] : b[j++];
      if (vistas.add('${x['clave']}')) salida.add(x);
    }
    return salida;
  }
}

/// ¿Suena en el navegador con el teléfono bloqueado? (todo lo que no es de YouTube)
bool suenaBloqueada(Json p) =>
    '${p['archivo'] ?? ''}'.isNotEmpty || '${p['url_directa'] ?? ''}'.startsWith('http');
