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
  const ConfigServicios({this.spotifyClientId = '', this.spotify = false, this.soundcloud = false});
  final String spotifyClientId;
  final bool spotify;
  final bool soundcloud;
}

class ErrorServicio implements Exception {
  const ErrorServicio(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

/// Tu cuenta de Spotify, con el flujo oficial «Authorization Code con PKCE» (sin
/// secreto). El navegador vuelve a `caudal://spotify`, que tiene que estar en las
/// «Redirect URIs» de la app de Spotify del dueño de Caudal.
class CuentaSpotify {
  static const vuelta = 'caudal://spotify';
  static const permisos = 'user-library-read playlist-read-private playlist-read-collaborative';
  static const _clave = 'spotify.sesion';
  static const _claveEspera = 'spotify.espera';

  /// Avisa a las pantallas cuando se conecta o desconecta la cuenta.
  static final cambios = ValueNotifier<int>(0);

  static Future<http.Response> Function(Uri url, Map<String, String> cuerpo) canjear =
      (u, c) => http.post(u, body: c).timeout(const Duration(seconds: 20));

  static String nuevoVerificador([Random? r]) {
    const letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    final azar = r ?? Random.secure();
    return List.generate(96, (_) => letras[azar.nextInt(letras.length)]).join();
  }

  static String huella(String verificador) =>
      base64Url.encode(sha256.convert(ascii.encode(verificador)).bytes).replaceAll('=', '');

  static Uri urlAutorizar(String clientId, String verificador, String estado) =>
      Uri.https('accounts.spotify.com', '/authorize', {
        'client_id': clientId,
        'response_type': 'code',
        'redirect_uri': vuelta,
        'code_challenge_method': 'S256',
        'code_challenge': huella(verificador),
        'scope': permisos,
        'state': estado,
      });

  /// Prepara la entrada y devuelve la dirección que hay que abrir en el navegador.
  static Future<Uri> empezar() async {
    final conf = await ServiciosExternos.config(forzar: true);
    if (conf.spotifyClientId.isEmpty) {
      throw const ErrorServicio('La conexión con Spotify aún no está activada en Caudal.');
    }
    final verificador = nuevoVerificador();
    final estado = nuevoVerificador().substring(0, 24);
    final p = await SharedPreferences.getInstance();
    await p.setString(_claveEspera,
        jsonEncode({'verificador': verificador, 'estado': estado, 'client_id': conf.spotifyClientId}));
    return urlAutorizar(conf.spotifyClientId, verificador, estado);
  }

  static bool esVuelta(String enlace) => enlace.trim().toLowerCase().startsWith(vuelta);

  /// El navegador volvió con `caudal://spotify?code=...&state=...`.
  static Future<void> volvio(String enlace) async {
    final u = Uri.tryParse(enlace.trim());
    final q = u?.queryParameters ?? const {};
    final p = await SharedPreferences.getInstance();
    final espera = jsonDecode(p.getString(_claveEspera) ?? '{}') as Map;
    await p.remove(_claveEspera);
    if (q['error'] == 'access_denied') throw const ErrorServicio('Cancelaste la conexión con Spotify.');
    final codigo = q['code'] ?? '';
    if (codigo.isEmpty || q['state'] != espera['estado']) {
      throw const ErrorServicio('Spotify no dejó conectar tu cuenta. Vuelve a intentarlo.');
    }
    final s = await _pedirToken({
      'grant_type': 'authorization_code',
      'code': codigo,
      'redirect_uri': vuelta,
      'client_id': '${espera['client_id']}',
      'code_verifier': '${espera['verificador']}',
    });
    s['client_id'] = '${espera['client_id']}';
    await p.setString(_clave, jsonEncode(s));
    cambios.value++;
  }

  static Future<Map<String, dynamic>> _pedirToken(Map<String, String> cuerpo) async {
    http.Response r;
    try {
      r = await canjear(Uri.parse('https://accounts.spotify.com/api/token'), cuerpo);
    } catch (_) {
      throw const ErrorServicio('No se pudo conectar con Spotify. Revisa tu internet.');
    }
    if (r.statusCode != 200) {
      throw const ErrorServicio('Spotify no aceptó la conexión. Vuelve a conectar tu cuenta.');
    }
    final d = jsonDecode(r.body) as Map;
    return {
      'access': '${d['access_token'] ?? ''}',
      'refresh': '${d['refresh_token'] ?? ''}',
      'caduca': DateTime.now().millisecondsSinceEpoch + (((d['expires_in'] as num?) ?? 3600).toInt() - 60) * 1000,
    };
  }

  static Future<bool> conectada() async {
    final p = await SharedPreferences.getInstance();
    final s = jsonDecode(p.getString(_clave) ?? '{}');
    return s is Map && '${s['refresh'] ?? ''}'.isNotEmpty;
  }

  static Future<void> desconectar() async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_clave);
    cambios.value++;
  }

  /// El token de tu cuenta, renovado si hace falta ('' si no está conectada).
  static Future<String> token() async {
    final p = await SharedPreferences.getInstance();
    final s = jsonDecode(p.getString(_clave) ?? '{}');
    if (s is! Map || '${s['refresh'] ?? ''}'.isEmpty) return '';
    if ('${s['access'] ?? ''}'.isNotEmpty && DateTime.now().millisecondsSinceEpoch < ((s['caduca'] as num?) ?? 0)) {
      return '${s['access']}';
    }
    try {
      final nueva = await _pedirToken({
        'grant_type': 'refresh_token',
        'refresh_token': '${s['refresh']}',
        'client_id': '${s['client_id'] ?? ''}',
      });
      if ('${nueva['refresh']}'.isEmpty) nueva['refresh'] = s['refresh']; // a veces no lo cambia
      nueva['client_id'] = s['client_id'];
      await p.setString(_clave, jsonEncode(nueva));
      return '${nueva['access']}';
    } on ErrorServicio {
      return '';
    }
  }
}
