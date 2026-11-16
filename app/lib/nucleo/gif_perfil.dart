import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show compute, kIsWeb;
import 'package:http/http.dart' as http;
import 'package:image/image.dart' as img;

import 'nube.dart';

/// GIF animados en la foto y el fondo del perfil (solo donadores y fundadores).
/// Aquí vive lo que no depende de la pantalla: reconocer un GIF, reducirlo para
/// que quepa en el límite y hablar con el buscador de GIF de Caudal.
class GifPerfil {
  GifPerfil._();

  /// Lo máximo que se sube al servidor (el cubo admite 5 MB; se deja margen).
  static const tope = 4500000;

  static const sinPermiso = 'Los GIF animados son exclusivos de los donadores de Caudal.';
  static const demasiadoPesado = 'Ese GIF pesa demasiado. Prueba con uno más corto.';
  static const ilegible = 'No se pudo leer ese GIF. Prueba con otro.';

  /// Lado mayor de la foto y tamaño del fondo cuando hay que reducir.
  static const ladoFoto = 480;
  static const anchoFondo = 960, altoFondo = 360;

  /// ¿Son los bytes (o el nombre del archivo) de un GIF?
  static bool esGif(Uint8List b, {String nombre = ''}) {
    if (b.length >= 6) {
      final c = String.fromCharCodes(b.sublist(0, 6));
      if (c == 'GIF87a' || c == 'GIF89a') return true;
    }
    return nombre.toLowerCase().endsWith('.gif');
  }

  static bool _cabeceraGif(Uint8List b) {
    if (b.length < 6) return false;
    final c = String.fromCharCodes(b.sublist(0, 6));
    return c == 'GIF87a' || c == 'GIF89a';
  }

  /// Ancho y alto declarados en la cabecera (sin decodificar).
  static (int, int)? tamano(Uint8List b) {
    if (b.length < 10) return null;
    return (b[6] | (b[7] << 8), b[8] | (b[9] << 8));
  }

  /// Deja el GIF listo para subir. Si pesa menos del tope y no es enorme se
  /// devuelve tal cual (la animación queda intacta); si no, se reducen los
  /// cuadros. Lanza [ErrorNube] con un mensaje amable si no se puede.
  static Future<Uint8List> preparar(Uint8List bytes, {required bool foto}) async {
    if (!_cabeceraGif(bytes)) throw const ErrorNube(ilegible);
    final t = tamano(bytes);
    final grande = t != null && max(t.$1, t.$2) > (foto ? 1000 : 1600);
    if (bytes.length <= tope && !grande) return bytes;
    final r = await compute(_reducirIsolate, _Pedido(bytes, foto, tope));
    if (r == null) throw const ErrorNube(demasiadoPesado);
    if (r.isEmpty) throw const ErrorNube(ilegible);
    return r;
  }

  /// Versión síncrona de la reducción (la usan las pruebas y el isolate).
  /// Devuelve null si ni reduciendo cabe en [maxBytes]; vacío si no se pudo leer.
  static Uint8List? reducir(Uint8List bytes, {required bool foto, int maxBytes = tope}) =>
      _reducir(bytes, foto, maxBytes);
}

class _Pedido {
  const _Pedido(this.bytes, this.foto, this.max);
  final Uint8List bytes;
  final bool foto;
  final int max;
}

Uint8List? _reducirIsolate(_Pedido p) => _reducir(p.bytes, p.foto, p.max);

Uint8List? _reducir(Uint8List bytes, bool foto, int maxBytes) {
  img.Image? origen;
  try {
    origen = img.GifDecoder().decode(bytes);
  } catch (_) {}
  if (origen == null || origen.width == 0 || origen.height == 0) return Uint8List(0);

  // Cada intento: (escala del tamaño objetivo, de cuántos en cuántos cuadros).
  const intentos = <(double, int)>[(1.0, 1), (0.75, 1), (0.75, 2), (0.55, 2), (0.4, 2), (0.4, 3)];
  Uint8List? ultimo;
  for (final (escala, salto) in intentos) {
    final salida = _recodificar(origen, foto, escala, salto);
    ultimo = salida;
    if (salida.length <= maxBytes) return salida;
  }
  return ultimo != null && ultimo.length <= maxBytes ? ultimo : null;
}

Uint8List _recodificar(img.Image origen, bool foto, double escala, int salto) {
  // recorte al centro
  late int x, y, w, h, destW, destH;
  if (foto) {
    final m = min(origen.width, origen.height);
    x = (origen.width - m) ~/ 2;
    y = (origen.height - m) ~/ 2;
    w = h = m;
    destW = destH = max(32, min((GifPerfil.ladoFoto * escala).round(), (m * escala).round()));
  } else {
    const prop = GifPerfil.anchoFondo / GifPerfil.altoFondo;
    w = origen.width;
    h = (w / prop).round();
    if (h > origen.height) {
      h = origen.height;
      w = (h * prop).round();
    }
    x = (origen.width - w) ~/ 2;
    y = (origen.height - h) ~/ 2;
    destW = max(64, min((GifPerfil.anchoFondo * escala).round(), (w * escala).round()));
    destH = (destW / prop).round();
  }

  final cuadros = origen.frames;
  img.Image? salida;
  var acumulado = 0; // duración de los cuadros saltados, para no acelerar el GIF
  for (var i = 0; i < cuadros.length; i++) {
    final dur = cuadros[i].frameDuration;
    acumulado += dur;
    final ultimoDelGrupo = (i % salto == salto - 1) || i == cuadros.length - 1;
    if (!ultimoDelGrupo) continue;
    var c = cuadros[i].clone(noAnimation: true); // sin arrastrar los demás cuadros
    if (c.hasPalette || c.numChannels != 4) c = c.convert(numChannels: 4);
    var n = img.copyCrop(c, x: x, y: y, width: w, height: h);
    if (n.width != destW) n = img.copyResize(n, width: destW, height: destH, interpolation: img.Interpolation.average);
    n.frameDuration = acumulado;
    acumulado = 0;
    if (salida == null) {
      salida = n;
      salida.loopCount = origen.loopCount;
    } else {
      salida.addFrame(n);
    }
  }
  return Uint8List.fromList(img.encodeGif(salida!));
}

// ============================================================ buscador de GIF

/// Un GIF de la lista del buscador.
class GifItem {
  const GifItem({required this.id, required this.titulo, required this.vista, required this.gif, this.ancho = 0, this.alto = 0, this.peso = 0});
  final String id, titulo, vista, gif;
  final int ancho, alto, peso;

  static GifItem? desde(Object? o) {
    if (o is! Map) return null;
    final vista = '${o['vista'] ?? ''}', gif = '${o['gif'] ?? ''}';
    if (!vista.startsWith('http') || !gif.startsWith('http')) return null;
    int n(Object? v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
    return GifItem(
      id: '${o['id'] ?? gif}',
      titulo: '${o['titulo'] ?? ''}',
      vista: vista,
      gif: gif,
      ancho: n(o['ancho']),
      alto: n(o['alto']),
      peso: n(o['peso']),
    );
  }
}

/// Una página de resultados.
class PaginaGifs {
  const PaginaGifs({this.items = const [], this.siguiente = '', this.aviso = '', this.error = ''});
  final List<GifItem> items;
  final String siguiente, aviso, error;

  bool get sinClave => error == 'sin_clave';
  bool get hayMas => siguiente.isNotEmpty;
}

/// Habla solo con el servicio de GIF de Caudal. No acepta enlaces de fuera:
/// lo único que se descarga es lo que ese servicio devuelve.
class GifBuscador {
  GifBuscador({http.Client? cliente, String? base}) : _http = cliente ?? http.Client(), _base = base ?? _baseDe();
  final http.Client _http;
  final String _base;

  static const maxBajada = 6 * 1024 * 1024;
  static String _baseDe() => kIsWeb ? '/api/gifs' : 'https://caudal-musica.netlify.app/api/gifs';

  Future<PaginaGifs> buscar(String texto, {String pos = ''}) async {
    final q = texto.trim();
    final uri = Uri.parse(_base).replace(queryParameters: {
      if (q.isNotEmpty) 'q': q,
      if (pos.isNotEmpty) 'pos': pos,
    });
    http.Response r;
    try {
      r = await _http.get(uri).timeout(const Duration(seconds: 15));
    } on TimeoutException {
      throw const SinConexion();
    } on http.ClientException {
      throw const SinConexion();
    }
    Object? d;
    try {
      d = jsonDecode(utf8.decode(r.bodyBytes));
    } catch (_) {}
    if (d is! Map) return const PaginaGifs(error: 'fallo');
    final error = '${d['error'] ?? ''}';
    final aviso = '${d['aviso'] ?? ''}';
    final lista = d['items'];
    final items = <GifItem>[
      if (lista is List)
        for (final o in lista)
          if (GifItem.desde(o) != null) GifItem.desde(o)!,
    ];
    if (error.isEmpty && r.statusCode >= 400) return const PaginaGifs(error: 'fallo');
    return PaginaGifs(items: items, siguiente: '${d['siguiente'] ?? ''}', aviso: aviso, error: error);
  }

  /// Descarga el GIF elegido pasando por el servicio (nunca directo).
  Future<Uint8List> bajar(GifItem g) async {
    final uri = Uri.parse(_base).replace(queryParameters: {'bajar': g.gif});
    http.Response r;
    try {
      r = await _http.get(uri).timeout(const Duration(seconds: 40));
    } on TimeoutException {
      throw const SinConexion();
    } on http.ClientException {
      throw const SinConexion();
    }
    if (r.statusCode >= 300 || r.bodyBytes.isEmpty) {
      throw const ErrorNube('No se pudo descargar ese GIF. Prueba con otro.');
    }
    if (r.bodyBytes.length > maxBajada) throw const ErrorNube(GifPerfil.demasiadoPesado);
    if (!GifPerfil.esGif(r.bodyBytes)) throw const ErrorNube('No se pudo descargar ese GIF. Prueba con otro.');
    return r.bodyBytes;
  }

  void cerrar() => _http.close();
}
