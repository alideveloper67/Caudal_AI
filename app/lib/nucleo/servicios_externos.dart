import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart' show ValueNotifier, kIsWeb;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Conexiones oficiales con otros servicios de música.
///
/// Un solo sitio de configuración para las dos apps: las variables de entorno del
/// sitio de Netlify. `/api/servicios` entrega lo público (el client_id de Spotify, que
/// en el flujo PKCE no es secreto) y dice si `/api/spotify` y `/api/soundcloud` tienen
/// sus credenciales. Los secretos nunca están en la app ni en el APK.
class ServiciosExternos {
  static const base = 'https://caudal-musica.netlify.app';

  /// La dirección de una función de Caudal (en la web, la del propio sitio).
  static Uri funcion(String ruta, [Map<String, String>? q]) =>
      (kIsWeb ? Uri.parse(ruta) : Uri.parse('$base$ruta')).replace(queryParameters: q);

  /// Se puede cambiar en las pruebas.
  static Future<http.Response> Function(Uri url) pedir =
      (u) => http.get(u).timeout(const Duration(seconds: 40));

  static ConfigServicios? _config;
  static DateTime _cuando = DateTime(2000);

  static Future<ConfigServicios> config({bool forzar = false}) async {
    final c = _config;
    if (!forzar && c != null && DateTime.now().difference(_cuando).inMinutes < 10) return c;
    var nueva = const ConfigServicios();
    try {
      final r = await pedir(funcion('/api/servicios'));
      final d = r.statusCode == 200 ? jsonDecode(r.body) : null;
      if (d is Map) {
        nueva = ConfigServicios(
          spotifyClientId: '${d['spotify_client_id'] ?? ''}'.trim(),
          spotify: d['spotify'] == true,
          soundcloud: d['soundcloud'] == true,
          soundcloudClientId: '${d['soundcloud_client_id'] ?? ''}'.trim(),
          youtubeClientId: '${d['youtube_client_id'] ?? ''}'.trim(),
        );
      }
    } catch (_) {/* sin internet o sin publicar: nada activado */}
    _config = nueva;
    _cuando = DateTime.now();
    return nueva;
  }

  /// Solo para pruebas.
  static void olvidarConfig() => _config = null;
}

class ConfigServicios {
  const ConfigServicios({this.spotifyClientId = '', this.spotify = false, this.soundcloud = false,
      this.soundcloudClientId = '', this.youtubeClientId = ''});
  final String spotifyClientId;
  final bool spotify;
  final bool soundcloud;
  final String soundcloudClientId;
  final String youtubeClientId;

  /// El identificador de Caudal en ese servicio ('' = la conexión no está activada).
  String clientId(ServicioMusica s) => switch (s) {
        ServicioMusica.spotify => spotifyClientId,
        ServicioMusica.youtube => youtubeClientId,
        ServicioMusica.soundcloud => soundcloudClientId,
      };
}

enum ServicioMusica {
  spotify('Spotify', 0xFF1DB954),
  youtube('YouTube Music', 0xFFFF3B30),
  soundcloud('SoundCloud', 0xFFFF5500);

  const ServicioMusica(this.nombre, this.color);
  final String nombre;
  final int color;

  static ServicioMusica? de(String? clave) {
    for (final s in values) {
      if (s.name == clave) return s;
    }
    return null;
  }
}

class ErrorServicio implements Exception {
  const ErrorServicio(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

/// El permiso ya no vale (se quitó desde el servicio o caducó): hay que vincular otra vez.
class PermisoCaducado extends ErrorServicio {
  const PermisoCaducado(super.mensaje);
}

/// Una cuenta de otro servicio vinculada a Caudal, con el permiso oficial de ese servicio
/// (OAuth con PKCE) y solo para leer. El navegador vuelve a `/api/vincular`, que devuelve a la
/// app con `caudal://vincular?...`. Los permisos viven solo en este dispositivo y son de la
/// cuenta de Caudal con la que se vinculó: no van a la nube ni a la copia de seguridad.
class CuentaExterna {
  const CuentaExterna(this.servicio);
  final ServicioMusica servicio;

  static const vuelta = '${ServiciosExternos.base}/api/vincular';

  /// La cuenta de Caudal abierta (la pone el armazón).
  static String deCaudal = '';

  /// Avisa a las pantallas cuando se vincula o desvincula algo.
  static final cambios = ValueNotifier<int>(0);

  String get _clave => 'vinculada.$deCaudal.${servicio.name}';
  static const _claveEspera = 'vinculada.espera';

  static Future<http.Response> Function(Uri url, Map<String, String> cuerpo) canjear =
      (u, c) => http.post(u, body: c).timeout(const Duration(seconds: 25));
  static Future<http.Response> Function(Uri url, String json) canjearEnCaudal = (u, j) =>
      http.post(u, body: j, headers: {'content-type': 'application/json'}).timeout(const Duration(seconds: 25));

  static String azar([int n = 96, Random? r]) {
    const letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    final a = r ?? Random.secure();
    return List.generate(n, (_) => letras[a.nextInt(letras.length)]).join();
  }

  static String huella(String verificador) =>
      base64Url.encode(sha256.convert(ascii.encode(verificador)).bytes).replaceAll('=', '');

  Uri urlAutorizar(String clientId, String verificador, String estado) {
    final q = {
      'client_id': clientId,
      'response_type': 'code',
      'redirect_uri': vuelta,
      'code_challenge_method': 'S256',
      'code_challenge': huella(verificador),
      'state': estado,
    };
    return switch (servicio) {
      ServicioMusica.spotify => Uri.https('accounts.spotify.com', '/authorize',
          {...q, 'scope': 'user-library-read playlist-read-private playlist-read-collaborative'}),
      ServicioMusica.youtube => Uri.https('accounts.google.com', '/o/oauth2/v2/auth', {
          ...q,
          'scope': 'https://www.googleapis.com/auth/youtube.readonly',
          'access_type': 'offline',
          'prompt': 'consent',
        }),
      ServicioMusica.soundcloud => Uri.https('secure.soundcloud.com', '/authorize', q),
    };
  }

  /// Prepara la entrada y devuelve la dirección que hay que abrir en el navegador.
  Future<Uri> empezar() async {
    final id = (await ServiciosExternos.config(forzar: true)).clientId(servicio);
    if (id.isEmpty) throw ErrorServicio('La conexión con ${servicio.nombre} aún no está activada en Caudal.');
    final verificador = azar();
    final estado = '${kIsWeb ? 'w' : 'a'}-${servicio.name}-${azar(32)}';
    final p = await SharedPreferences.getInstance();
    await p.setString(
        _claveEspera,
        jsonEncode({
          'servicio': servicio.name,
          'verificador': verificador,
          'estado': estado,
          'client_id': id,
          'cuenta': deCaudal,
        }));
    return urlAutorizar(id, verificador, estado);
  }

  static bool esVuelta(String enlace) => enlace.trim().toLowerCase().startsWith('caudal://vincular');

  /// En la web el navegador vuelve a `/app/?vincular=1&...`: eso mismo como `caudal://vincular?...`.
  static String? vueltaWeb(Uri pagina) {
    if (pagina.queryParameters['vincular'] != '1') return null;
    final q = {...pagina.queryParameters}..remove('vincular');
    return Uri(scheme: 'caudal', host: 'vincular', queryParameters: q).toString();
  }

  /// El navegador volvió. Devuelve el servicio vinculado, o null si no se estaba esperando
  /// nada (por ejemplo, al recargar la página de vuelta).
  static Future<ServicioMusica?> volvio(String enlace) async {
    final q = Uri.tryParse(enlace.trim())?.queryParameters ?? const <String, String>{};
    final p = await SharedPreferences.getInstance();
    final espera = jsonDecode(p.getString(_claveEspera) ?? '{}') as Map;
    final servicio = ServicioMusica.de('${espera['servicio']}');
    if (servicio == null) return null;
    if (q['state'] != espera['estado']) {
      throw ErrorServicio('${servicio.nombre} no dejó vincular tu cuenta. Vuelve a intentarlo.');
    }
    await p.remove(_claveEspera);
    if ('${espera['cuenta'] ?? ''}' != deCaudal) {
      throw const ErrorServicio('Cambiaste de cuenta de Caudal mientras vinculabas. Vuelve a intentarlo.');
    }
    if (q['error'] == 'access_denied') throw ErrorServicio('Cancelaste la conexión con ${servicio.nombre}.');
    final codigo = q['code'] ?? '';
    if (codigo.isEmpty) throw ErrorServicio('${servicio.nombre} no dejó vincular tu cuenta. Vuelve a intentarlo.');
    final c = CuentaExterna(servicio);
    final s = await c._pedirToken('${espera['client_id']}', codigo: codigo, verificador: '${espera['verificador']}');
    s['client_id'] = '${espera['client_id']}';
    await p.setString(c._clave, jsonEncode(s));
    cambios.value++;
    return servicio;
  }

  Future<Map<String, dynamic>> _pedirToken(String clientId,
      {String codigo = '', String verificador = '', String refresh = ''}) async {
    final nombre = servicio.nombre;
    final conCodigo = codigo.isNotEmpty;
    http.Response r;
    try {
      r = servicio == ServicioMusica.spotify
          ? await canjear(Uri.parse('https://accounts.spotify.com/api/token'), {
              'client_id': clientId,
              'grant_type': conCodigo ? 'authorization_code' : 'refresh_token',
              if (conCodigo) ...{'code': codigo, 'redirect_uri': vuelta, 'code_verifier': verificador},
              if (!conCodigo) 'refresh_token': refresh,
            })
          : await canjearEnCaudal(
              ServiciosExternos.funcion('/api/vincular'),
              jsonEncode({
                'servicio': servicio.name,
                if (conCodigo) ...{'code': codigo, 'verificador': verificador},
                if (!conCodigo) 'refresh': refresh,
              }));
    } catch (_) {
      throw ErrorServicio('No se pudo conectar con $nombre. Revisa tu internet.');
    }
    Map d;
    try {
      d = jsonDecode(utf8.decode(r.bodyBytes, allowMalformed: true)) as Map;
    } catch (_) {
      d = const {};
    }
    final access = '${d['access_token'] ?? d['access'] ?? ''}';
    if (r.statusCode == 200 && access.isNotEmpty) {
      final dura = ((d['expires_in'] ?? d['caduca_en']) as num?)?.toInt() ?? 3600;
      return {
        'access': access,
        'refresh': '${d['refresh_token'] ?? d['refresh'] ?? ''}',
        'caduca': DateTime.now().millisecondsSinceEpoch + (dura - 60) * 1000,
      };
    }
    if (d['error'] == 'caducado' || d['error'] == 'invalid_grant') {
      throw PermisoCaducado('$nombre pide que vuelvas a vincular tu cuenta.');
    }
    throw ErrorServicio('${d['mensaje'] ?? '$nombre no contestó bien. Prueba otra vez en un rato.'}');
  }

  Future<Map<String, dynamic>> _sesion() async {
    final p = await SharedPreferences.getInstance();
    try {
      final s = jsonDecode(p.getString(_clave) ?? '{}');
      return s is Map ? Map<String, dynamic>.from(s) : {};
    } catch (_) {
      return {};
    }
  }

  static bool _vale(Map s) => '${s['refresh'] ?? ''}'.isNotEmpty || '${s['access'] ?? ''}'.isNotEmpty;

  Future<bool> vinculada() async => _vale(await _sesion());

  /// Quita el permiso de este dispositivo (en Google, además, se lo devuelve).
  Future<void> desvincular() async {
    final s = await _sesion();
    await (await SharedPreferences.getInstance()).remove(_clave);
    cambios.value++;
    if (servicio == ServicioMusica.youtube && _vale(s)) {
      final t = '${s['refresh'] ?? ''}';
      try {
        await canjear(Uri.parse('https://oauth2.googleapis.com/revoke'), {'token': t.isEmpty ? '${s['access']}' : t});
      } catch (_) {/* sin internet: queda fuera de este dispositivo igualmente */}
    }
  }

  static final Map<String, Future<String>> _renovando = {};

  /// El permiso para leer, renovado si hace falta ('' si la cuenta no está vinculada).
  /// Con el permiso retirado lanza [PermisoCaducado]; sin red, [ErrorServicio].
  Future<String> token() {
    final clave = _clave;
    // dos lecturas a la vez no gastan dos veces el permiso de renovar (SoundCloud: un solo uso)
    return _renovando[clave] ??= _token(clave).whenComplete(() {
      _renovando.remove(clave); // sin devolverlo: se esperaría a sí mismo
    });
  }

  Future<String> _token(String clave) async {
    final s = await _sesion();
    if (!_vale(s)) return '';
    if ('${s['access'] ?? ''}'.isNotEmpty && DateTime.now().millisecondsSinceEpoch < ((s['caduca'] as num?) ?? 0)) {
      return '${s['access']}';
    }
    final p = await SharedPreferences.getInstance();
    try {
      if ('${s['refresh'] ?? ''}'.isEmpty) {
        throw PermisoCaducado('${servicio.nombre} pide que vuelvas a vincular tu cuenta.');
      }
      final nueva = await _pedirToken('${s['client_id'] ?? ''}', refresh: '${s['refresh']}');
      if ('${nueva['refresh']}'.isEmpty) nueva['refresh'] = s['refresh']; // a veces no lo cambia
      nueva['client_id'] = s['client_id'];
      // solo si mientras tanto no se desvinculó
      if (p.getString(clave) != null) await p.setString(clave, jsonEncode(nueva));
      return '${nueva['access']}';
    } on PermisoCaducado {
      await p.remove(clave);
      cambios.value++;
      rethrow;
    }
  }
}
