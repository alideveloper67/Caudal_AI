import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// Traduce la letra de una canción línea a línea (como la traducción de letras
/// de YouTube Music Premium).
///
/// Dos caminos sin clave, por si uno falla: el traductor público de Google y,
/// de respaldo, MyMemory (API gratuita y documentada). La letra se manda por
/// trozos con sus saltos de línea, y cada línea traducida vuelve a su sitio.
class Traductor {
  Traductor._();

  static final Map<String, Future<Traduccion?>> _cache = {};

  /// Las líneas traducidas a [destino] (misma cantidad que [lineas]). Si la
  /// letra ya está en ese idioma, [Traduccion.mismoIdioma]. Null si no se pudo.
  static Future<Traduccion?> traducir(String clave, List<String> lineas, {String destino = 'es'}) {
    final k = '$clave|$destino';
    final f = _cache[k] ??= _traducir(lineas, destino);
    // un fallo de red no se queda guardado: se reintenta la próxima vez
    f.then((t) {
      if (t == null) _cache.remove(k);
    });
    return f;
  }

  static Future<Traduccion?> _traducir(List<String> lineas, String destino) async {
    if (lineas.every((l) => l.trim().isEmpty)) return Traduccion.mismo();
    for (final motor in [_google, _myMemory]) {
      try {
        final t = await _porTrozos(lineas, destino, motor);
        if (t != null) return t;
      } on _MismoIdioma {
        return Traduccion.mismo();
      } catch (_) {
        // al siguiente camino
      }
    }
    return null;
  }

  /// Junta las líneas en trozos que quepan en una petición, traduce cada uno y
  /// reparte el resultado de vuelta por líneas.
  static Future<Traduccion?> _porTrozos(List<String> lineas, String destino,
      Future<(String, String)> Function(String texto, String destino, int max) motor) async {
    final max = identical(motor, _myMemory) ? 380 : 1400;
    final trozos = <List<int>>[]; // índices de las líneas con texto de cada trozo
    var actual = <int>[];
    var largo = 0;
    for (var i = 0; i < lineas.length; i++) {
      final l = lineas[i].trim();
      if (l.isEmpty) continue;
      if (actual.isNotEmpty && largo + l.length + 1 > max) {
        trozos.add(actual);
        actual = [];
        largo = 0;
      }
      actual.add(i);
      largo += l.length + 1;
    }
    if (actual.isNotEmpty) trozos.add(actual);

    final salida = List<String>.filled(lineas.length, '');
    var idioma = '';
    for (final t in trozos) {
      final texto = t.map((i) => lineas[i].trim()).join('\n');
      final (traducido, origen) = await motor(texto, destino, max);
      if (idioma.isEmpty) idioma = origen;
      if (origen.isNotEmpty && origen.split('-').first == destino) {
        // ya está en el idioma de destino
        throw _MismoIdioma();
      }
      final partes = traducido.split('\n');
      if (partes.length == t.length) {
        for (var k = 0; k < t.length; k++) {
          salida[t[k]] = partes[k].trim();
        }
      } else {
        // el traductor juntó o partió líneas: se traduce línea a línea
        for (final i in t) {
          final (una, _) = await motor(lineas[i].trim(), destino, max);
          salida[i] = una.replaceAll('\n', ' ').trim();
        }
      }
    }
    // las líneas que ya estaban en el idioma de destino no repiten la traducción
    for (var i = 0; i < lineas.length; i++) {
      if (_igual(salida[i], lineas[i])) salida[i] = '';
    }
    if (salida.every((s) => s.isEmpty)) throw _MismoIdioma();
    return Traduccion(salida, idioma);
  }

  static bool _igual(String a, String b) {
    String n(String s) => s.toLowerCase().replaceAll(RegExp(r'[^\p{L}\p{N}]', unicode: true), '');
    return n(a) == n(b);
  }

  /// Google (traductor web público, sin clave).
  static Future<(String, String)> _google(String texto, String destino, int _) async {
    final r = await http.post(
      Uri.parse('https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=$destino&dt=t'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
      body: {'q': texto},
    ).timeout(const Duration(seconds: 15));
    if (r.statusCode != 200) throw Exception('google ${r.statusCode}');
    return leerGoogle(utf8.decode(r.bodyBytes));
  }

  /// Separado para probarlo: [[["trad","orig",...],...],null,"en",...]
  static (String, String) leerGoogle(String cuerpo) {
    final d = jsonDecode(cuerpo);
    if (d is! List || d.isEmpty || d[0] is! List) throw const FormatException('respuesta rara');
    final b = StringBuffer();
    for (final seg in d[0] as List) {
      if (seg is List && seg.isNotEmpty && seg[0] is String) b.write(seg[0]);
    }
    final idioma = d.length > 2 && d[2] is String ? d[2] as String : '';
    return (b.toString(), idioma);
  }

  /// MyMemory: gratis, hasta ~5000 caracteres al día por teléfono.
  static Future<(String, String)> _myMemory(String texto, String destino, int _) async {
    final r = await http.get(Uri.https('api.mymemory.translated.net', '/get',
        {'q': texto, 'langpair': 'autodetect|$destino'})).timeout(const Duration(seconds: 15));
    final d = jsonDecode(utf8.decode(r.bodyBytes));
    if (d is! Map) throw const FormatException('respuesta rara');
    final detalle = '${d['responseDetails'] ?? ''}'.toUpperCase();
    if (detalle.contains('DISTINCT LANGUAGES')) throw _MismoIdioma();
    if ('${d['responseStatus']}' != '200' || d['quotaFinished'] == true) {
      throw Exception('mymemory ${d['responseStatus']}');
    }
    final traducido = '${(d['responseData'] as Map?)?['translatedText'] ?? ''}';
    final idioma = '${(d['responseData'] as Map?)?['detectedLanguage'] ?? ''}';
    return (traducido, idioma);
  }
}

class Traduccion {
  Traduccion(this.lineas, this.idioma) : mismoIdioma = false;
  Traduccion.mismo()
      : lineas = const [],
        idioma = '',
        mismoIdioma = true;

  /// La letra ya estaba en el idioma de destino: no hay nada que enseñar.
  final bool mismoIdioma;

  /// Una por cada línea de la letra; vacía si esa línea no necesita traducción.
  final List<String> lineas;
  final String idioma;
}

class _MismoIdioma implements Exception {}
