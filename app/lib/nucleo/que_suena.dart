import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'catalogo.dart';
import 'coleccion.dart' show Json;

export 'coleccion.dart' show Json;

/// «¿Qué suena?»: se graban unos segundos con el micrófono, la función de Netlify
/// /api/reconocer (netlify/functions/reconocer.mjs) se los pasa al servicio de reconocimiento
/// (AudD o ACRCloud, con su clave guardada solo en el servidor) y la canción se busca en Caudal.


const urlReconocer = 'https://caudal-musica.netlify.app/api/reconocer';
const segundosEscucha = 10;
const textoNoDisponible = '«¿Qué suena?» todavía no está disponible: falta activarlo en el servidor de Caudal.';

class ErrorQueSuena implements Exception {
  const ErrorQueSuena(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

/// Lo que devuelve /api/reconocer.
class ResultadoQueSuena {
  const ResultadoQueSuena({required this.encontrada, this.titulo = '', this.artista = '', this.album = '',
      this.anio = '', this.portada = '', this.videoId = '', this.consulta = ''});

  final bool encontrada;
  final String titulo, artista, album, anio, portada, videoId, consulta;

  static const nada = ResultadoQueSuena(encontrada: false);

  static ResultadoQueSuena desde(Object? d) {
    if (d is! Map || d['encontrada'] != true) return nada;
    String t(String k) => d[k] == null ? '' : '${d[k]}'.trim();
    final titulo = t('titulo');
    if (titulo.isEmpty) return nada;
    final portada = t('portada');
    final vid = t('video_id');
    return ResultadoQueSuena(
      encontrada: true, titulo: titulo, artista: t('artista'), album: t('album'), anio: t('anio'),
      portada: RegExp(r'''^https://[^\s"'<>]+$''').hasMatch(portada) ? portada : '',
      videoId: RegExp(r'^[A-Za-z0-9_-]{11}$').hasMatch(vid) ? vid : '',
      consulta: t('consulta').isNotEmpty ? t('consulta') : [t('artista'), titulo].where((s) => s.isNotEmpty).join(' '),
    );
  }
}

String _mensaje(String cuerpo, String porDefecto) {
  try {
    final d = jsonDecode(cuerpo);
    if (d is Map && '${d['mensaje'] ?? ''}'.isNotEmpty) return '${d['mensaje']}';
  } catch (_) {}
  return porDefecto;
}

/// Habla con /api/reconocer. [cliente] se cambia en las pruebas.
class ServicioQueSuena {
  ServicioQueSuena({http.Client? cliente, this.url = urlReconocer}) : _http = cliente ?? http.Client();
  final http.Client _http;
  final String url;

  static bool? _disponibleCache;
  static DateTime _cuando = DateTime(2000);

  /// Olvida lo que se sabía (para las pruebas).
  static void olvidar() => _disponibleCache = null;

  /// ¿Está activada en el servidor? Sin conexión, se responde que sí y el fallo se cuenta al grabar.
  Future<bool> disponible() async {
    if (_disponibleCache != null && DateTime.now().difference(_cuando) < const Duration(minutes: 10)) {
      return _disponibleCache!;
    }
    try {
      final r = await _http.get(Uri.parse(url)).timeout(const Duration(seconds: 10));
      if (r.statusCode != 200) return true;
      final d = jsonDecode(utf8.decode(r.bodyBytes));
      _disponibleCache = d is Map && d['disponible'] == true;
      _cuando = DateTime.now();
      return _disponibleCache!;
    } catch (_) {
      return true;
    }
  }

  Future<ResultadoQueSuena> reconocer(Uint8List audio, {String tipo = 'audio/wav'}) async {
    http.Response r;
    try {
      r = await _http
          .post(Uri.parse(url), headers: {'content-type': tipo}, body: audio)
          .timeout(const Duration(seconds: 30));
    } catch (_) {
      throw const ErrorQueSuena('No se pudo reconocer ahora. Revisa tu internet y vuelve a probar.');
    }
    final cuerpo = utf8.decode(r.bodyBytes);
    if (r.statusCode == 503) {
      try {
        final d = jsonDecode(cuerpo);
        if (d is Map && d['disponible'] == false) {
          _disponibleCache = false;
          _cuando = DateTime.now();
          throw const ErrorQueSuena(textoNoDisponible);
        }
      } on ErrorQueSuena {
        rethrow;
      } catch (_) {}
    }
    if (r.statusCode != 200) {
      throw ErrorQueSuena(_mensaje(cuerpo, 'No se pudo reconocer ahora. Vuelve a probar en un momento.'));
    }
    try {
      return ResultadoQueSuena.desde(jsonDecode(cuerpo));
    } catch (_) {
      return ResultadoQueSuena.nada;
    }
  }
}

// ---------------------------------------------------------------- buscarla en Caudal

String _plano(String s) {
  const de = 'áàäâãéèëêíìïîóòöôõúùüûñç';
  const a = 'aaaaaeeeeiiiiooooouuuunc';
  final b = StringBuffer();
  for (final ch in s.toLowerCase().split('')) {
    final i = de.indexOf(ch);
    b.write(i >= 0 ? a[i] : ch);
  }
  return b.toString().replaceAll(RegExp(r'\(.*?\)|\[.*?\]'), ' ').replaceAll(RegExp(r'[^a-z0-9 ]'), ' ')
      .replaceAll(RegExp(r'\s+'), ' ').trim();
}

/// Cuánto se parece una pista del catálogo a lo reconocido (más es mejor).
int parecido(Json pista, String titulo, String artista) {
  final t = _plano(titulo), a = _plano(artista);
  final pt = _plano('${pista['titulo'] ?? ''}'), pa = _plano('${pista['artista'] ?? ''}');
  var p = 0;
  if (pt == t) {
    p += 6;
  } else if (t.isNotEmpty && (pt.contains(t) || t.contains(pt))) {
    p += 4;
  }
  if (a.isNotEmpty) {
    final primero = a.split(RegExp(r',| & | feat | ft | y ')).first.trim();
    if (pa == a) {
      p += 4;
    } else if (primero.isNotEmpty && pa.contains(primero)) {
      p += 3;
    }
  }
  if (pista['es_video'] == true) p -= 1; // mejor la canción que el videoclip
  return p;
}

/// Los resultados de la búsqueda ordenados: el primero es el que más se parece.
List<Json> ordenarParecidos(List<Json> pistas, String titulo, String artista) {
  final con = [for (final (i, p) in pistas.indexed) (p, parecido(p, titulo, artista), i)];
  con.sort((x, y) => y.$2 != x.$2 ? y.$2 - x.$2 : x.$3 - y.$3);
  return [for (final c in con) c.$1];
}

/// La canción reconocida en el catálogo de Caudal (las mejores primero). [buscar] se cambia en
/// las pruebas. Si el servicio dio el video de YouTube, va primero.
Future<List<Json>> pistasDeResultado(ResultadoQueSuena r,
    {Future<List<Json>> Function(String texto)? buscar}) async {
  if (!r.encontrada) return const [];
  final b = buscar ?? (t) => Catalogo.buscar(t, filtro: 'canciones', limite: 6);
  var lista = <Json>[];
  try {
    lista = ordenarParecidos(
        [for (final p in await b(r.consulta)) if ('${p['video_id'] ?? ''}'.isNotEmpty) p], r.titulo, r.artista);
  } catch (_) {
    lista = [];
  }
  if (r.videoId.isNotEmpty && !lista.any((p) => p['video_id'] == r.videoId)) {
    lista.insert(0, Catalogo.nuevaPista(r.videoId,
        titulo: r.titulo, artistas: r.artista.isEmpty ? const [] : [{'nombre': r.artista, 'id': ''}],
        miniatura: r.portada));
  } else if (r.videoId.isNotEmpty) {
    final i = lista.indexWhere((p) => p['video_id'] == r.videoId);
    lista.insert(0, lista.removeAt(i));
  }
  return lista;
}

// ---------------------------------------------------------------- micrófono

/// Lo que se necesita del micrófono (en la app, [GrabadorMicrofono]; en las pruebas, uno falso).
abstract class Grabador {
  /// false si el usuario no dio permiso.
  Future<bool> permiso();
  Future<void> empezar();

  /// El audio grabado y su tipo (p. ej. 'audio/wav'), o null si no salió nada.
  Future<(Uint8List, String)?> parar();
  Future<void> soltar();
}
