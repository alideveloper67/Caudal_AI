import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:flutter/foundation.dart';

import 'cast_tipos.dart';

/// El pequeño servidor http del teléfono para la tele (solo en el teléfono:
/// la web no lo importa, ver cast_plataforma.dart).
///
/// * `/a/<clave>`: un archivo del teléfono (descargas, música importada,
///   carátulas guardadas). Solo los que se publicaron: la clave es al azar y
///   no deja leer nada más del teléfono.
/// * `/p/<clave>`: repite un stream de YouTube a través del teléfono, por si
///   la tele no puede abrirlo directamente (p. ej. si el enlace quedó atado a
///   la dirección IPv6 del teléfono).
///
/// Las dos respetan la cabecera Range: la tele lee a saltos y sin eso no se
/// podría mover la barra.
class ServidorCastIo implements ServidorCast {
  /// [ip] fija la dirección que se anuncia (las pruebas usan 127.0.0.1); si no,
  /// se usa la de la wifi.
  ServidorCastIo({this.ip, HttpClient? cliente}) : _cliente = cliente ?? HttpClient();

  final String? ip;
  final HttpClient _cliente;
  HttpServer? _servidor;
  Future<HttpServer>? _abriendo;
  final Map<String, (String, String)> _archivos = {}; // clave -> (ruta, tipo)
  final Map<String, (String, String)> _remotos = {}; // clave -> (url, tipo)
  final _azar = Random.secure();

  /// Puerto en el que escucha (0 si aún no se abrió).
  int get puerto => _servidor?.port ?? 0;

  String _clave() => List.generate(16, (_) => _azar.nextInt(256).toRadixString(16).padLeft(2, '0')).join();

  Future<HttpServer> _abrir() {
    final s = _servidor;
    if (s != null) return Future.value(s);
    return _abriendo ??= () async {
      final nuevo = await HttpServer.bind(InternetAddress.anyIPv4, 0, shared: true);
      nuevo.autoCompress = false;
      nuevo.listen(_atender, onError: (_) {});
      _servidor = nuevo;
      _abriendo = null;
      return nuevo;
    }();
  }

  Future<String?> _base() async {
    final dir = ip ?? await ipLocal();
    if (dir == null) return null;
    final s = await _abrir();
    return 'http://$dir:${s.port}';
  }

  @override
  Future<String?> publicarArchivo(String ruta, {String? tipo}) async {
    if (!File(ruta).existsSync()) return null;
    final base = await _base();
    if (base == null) return null;
    // la misma ruta, la misma clave (la tele puede volver a pedirla)
    final ya = _archivos.entries.where((e) => e.value.$1 == ruta).firstOrNull;
    final clave = ya?.key ?? _clave();
    _limitar(_archivos);
    _archivos[clave] = (ruta, tipo ?? tipoPorExtension(ruta));
    return '$base/a/$clave${_extension(ruta)}';
  }

  @override
  Future<String?> publicarRemoto(String url, {String? tipo}) async {
    final base = await _base();
    if (base == null) return null;
    final ya = _remotos.entries.where((e) => e.value.$1 == url).firstOrNull;
    final clave = ya?.key ?? _clave();
    _limitar(_remotos);
    _remotos[clave] = (url, tipo ?? '');
    return '$base/p/$clave';
  }

  void _limitar(Map<String, (String, String)> m) {
    while (m.length >= 300) {
      m.remove(m.keys.first);
    }
  }

  static String _extension(String ruta) {
    final i = ruta.lastIndexOf('.');
    if (i < 0 || i < ruta.lastIndexOf(Platform.pathSeparator)) return '';
    final e = ruta.substring(i).toLowerCase();
    return RegExp(r'^\.[a-z0-9]{1,5}$').hasMatch(e) ? e : '';
  }

  Future<void> _atender(HttpRequest pet) async {
    final res = pet.response;
    try {
      res.headers.set('Access-Control-Allow-Origin', '*');
      res.headers.set('Access-Control-Allow-Headers', 'Range');
      res.headers.set('Access-Control-Expose-Headers', 'Content-Length, Content-Range, Accept-Ranges');
      if (pet.method == 'OPTIONS') {
        res.statusCode = HttpStatus.noContent;
        await res.close();
        return;
      }
      if (pet.method != 'GET' && pet.method != 'HEAD') {
        res.statusCode = HttpStatus.methodNotAllowed;
        await res.close();
        return;
      }
      final partes = pet.uri.pathSegments;
      if (partes.length == 2 && partes[0] == 'a') {
        final clave = partes[1].split('.').first;
        final a = _archivos[clave];
        if (a != null) return await _servirArchivo(pet, a.$1, a.$2);
      } else if (partes.length == 2 && partes[0] == 'p') {
        final r = _remotos[partes[1]];
        if (r != null) return await _repetir(pet, r.$1, r.$2);
      }
      res.statusCode = HttpStatus.notFound;
      await res.close();
    } catch (e) {
      debugPrint('cast servidor: $e');
      try {
        await res.close();
      } catch (_) {}
    }
  }

  Future<void> _servirArchivo(HttpRequest pet, String ruta, String tipo) async {
    final res = pet.response;
    final f = File(ruta);
    if (!await f.exists()) {
      res.statusCode = HttpStatus.notFound;
      return res.close();
    }
    final largo = await f.length();
    res.headers.set(HttpHeaders.acceptRangesHeader, 'bytes');
    res.headers.contentType = ContentType.parse(tipo);
    final cabecera = pet.headers.value(HttpHeaders.rangeHeader);
    final rango = rangoPedido(cabecera, largo);
    if (rango == null) {
      res.statusCode = HttpStatus.requestedRangeNotSatisfiable;
      res.headers.set(HttpHeaders.contentRangeHeader, 'bytes */$largo');
      return res.close();
    }
    final (desde, hasta) = rango;
    final parcial = cabecera != null && cabecera.trim().isNotEmpty;
    res.statusCode = parcial ? HttpStatus.partialContent : HttpStatus.ok;
    if (parcial) res.headers.set(HttpHeaders.contentRangeHeader, 'bytes $desde-$hasta/$largo');
    res.contentLength = largo == 0 ? 0 : hasta - desde + 1;
    if (pet.method == 'HEAD' || largo == 0) return res.close();
    await res.addStream(f.openRead(desde, hasta + 1));
    await res.close();
  }

  Future<void> _repetir(HttpRequest pet, String url, String tipo) async {
    final res = pet.response;
    final salida = await _cliente.openUrl(pet.method, Uri.parse(url));
    final rango = pet.headers.value(HttpHeaders.rangeHeader);
    if (rango != null) salida.headers.set(HttpHeaders.rangeHeader, rango);
    salida.followRedirects = true;
    final llega = await salida.close();
    res.statusCode = llega.statusCode;
    for (final c in [HttpHeaders.contentRangeHeader, HttpHeaders.acceptRangesHeader]) {
      final v = llega.headers.value(c);
      if (v != null) res.headers.set(c, v);
    }
    final t = tipo.isNotEmpty ? tipo : llega.headers.contentType?.toString();
    if (t != null) res.headers.contentType = ContentType.parse(t);
    if (llega.contentLength >= 0) res.contentLength = llega.contentLength;
    if (pet.method == 'HEAD') {
      await llega.drain<void>();
      return res.close();
    }
    await res.addStream(llega);
    await res.close();
  }

  @override
  Future<void> cerrar() async {
    final s = _servidor;
    _servidor = null;
    _archivos.clear();
    _remotos.clear();
    await s?.close(force: true);
  }

  /// La dirección IPv4 del teléfono en la red de casa (la wifi), o null.
  static Future<String?> ipLocal() async {
    try {
      final interfaces = await NetworkInterface.list(type: InternetAddressType.IPv4);
      String? cualquiera;
      for (final i in interfaces) {
        final wifi = RegExp(r'wlan|wifi|en0|eth|ap|swlan', caseSensitive: false).hasMatch(i.name);
        for (final a in i.addresses) {
          if (a.isLoopback || !esPrivada(a.address)) continue;
          if (wifi) return a.address;
          cualquiera ??= a.address;
        }
      }
      return cualquiera;
    } catch (_) {
      return null;
    }
  }

  /// ¿Es de una red de casa? (las de los datos móviles no llegan a la tele)
  static bool esPrivada(String ip) {
    final p = ip.split('.').map(int.tryParse).toList();
    if (p.length != 4 || p.any((x) => x == null)) return false;
    final a = p[0]!, b = p[1]!;
    return a == 10 || (a == 192 && b == 168) || (a == 172 && b >= 16 && b <= 31);
  }
}

/// El trozo que pide una cabecera `Range: bytes=...` de un archivo de [largo]
/// bytes, como (primero, último) incluidos. Sin cabecera: todo. Null si el
/// trozo no existe (respuesta 416). Con varios trozos se atiende el primero.
(int, int)? rangoPedido(String? cabecera, int largo) {
  if (cabecera == null || cabecera.trim().isEmpty) return (0, max(0, largo - 1));
  final m = RegExp(r'^\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)').firstMatch(cabecera);
  if (m == null) return (0, max(0, largo - 1));
  final a = m.group(1)!, b = m.group(2)!;
  if (a.isEmpty && b.isEmpty) return null;
  if (largo == 0) return null;
  if (a.isEmpty) {
    // los últimos N bytes
    final n = int.parse(b);
    if (n == 0) return null;
    return (max(0, largo - n), largo - 1);
  }
  final desde = int.parse(a);
  if (desde >= largo) return null;
  final hasta = b.isEmpty ? largo - 1 : min(int.parse(b), largo - 1);
  if (hasta < desde) return null;
  return (desde, hasta);
}

/// El tipo que entiende la tele según la extensión del archivo.
String tipoPorExtension(String ruta) {
  final i = ruta.lastIndexOf('.');
  final e = i < 0 ? '' : ruta.substring(i + 1).toLowerCase();
  return switch (e) {
    'mp3' => 'audio/mpeg',
    'm4a' || 'aac' || 'mp4a' => 'audio/mp4',
    'opus' || 'ogg' || 'oga' => 'audio/ogg',
    'webm' || 'weba' => 'audio/webm',
    'flac' => 'audio/flac',
    'wav' => 'audio/wav',
    'mp4' || 'm4v' => 'video/mp4',
    'mkv' => 'video/x-matroska',
    'jpg' || 'jpeg' => 'image/jpeg',
    'png' => 'image/png',
    'webp' => 'image/webp',
    'gif' => 'image/gif',
    _ => 'application/octet-stream',
  };
}
