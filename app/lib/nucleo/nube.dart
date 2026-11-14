import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;

/// Conexion con Supabase: las cuentas y la biblioteca compartidas con Caudal
/// para Windows (misma base de datos y mismas reglas que nube.py).
///
/// La clave de aqui es la PUBLICA del proyecto: esta hecha para ir dentro de
/// las apps. La seguridad la ponen las reglas de la base de datos (cada usuario
/// solo ve y toca lo suyo).
class Nube {
  static const url = 'https://nztirmwqykbxadidpzzt.supabase.co';
  static const clavePublica = 'sb_publishable_ga4gKRk0czj044G-xPptSQ_BZ_sTZLl';
  static const dominio = 'usuarios.caudal.app';
  static const _espera = Duration(seconds: 15);

  static String correoDe(String usuario) => '${usuario.trim().toLowerCase()}@$dominio';

  static Future<http.Response> _peticion(String metodo, String ruta,
      {String? token, Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    final cab = {
      'apikey': clavePublica,
      'Content-Type': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      ...cabeceras,
    };
    final req = http.Request(metodo, Uri.parse(url + ruta))..headers.addAll(cab);
    if (cuerpo != null) req.body = jsonEncode(cuerpo);
    try {
      final resp = await http.Response.fromStream(await req.send().timeout(_espera))
          .timeout(_espera);
      return resp;
    } on SocketException {
      throw const SinConexion();
    } on TimeoutException {
      throw const SinConexion();
    } on http.ClientException {
      throw const SinConexion();
    }
  }

  static ErrorNube _traducir(http.Response r) {
    var texto = '';
    try {
      final d = jsonDecode(r.body);
      if (d is Map) {
        texto = ['msg', 'message', 'error_description', 'error', 'code']
            .map((k) => '${d[k] ?? ''}')
            .join(' ')
            .toLowerCase();
      }
    } catch (_) {}
    if (texto.contains('invalid login') || texto.contains('invalid_grant') ||
        texto.contains('invalid_credentials')) {
      return const ErrorNube('Usuario o contraseña incorrectos.');
    }
    if (texto.contains('already registered') || texto.contains('already exists') ||
        texto.contains('user_already_exists')) {
      return const ErrorNube('Ese usuario ya existe. Inicia sesión o elige otro.');
    }
    if (texto.contains('password') && (texto.contains('short') || texto.contains('least'))) {
      return const ErrorNube('La contraseña es demasiado corta (mínimo 6 caracteres).');
    }
    if (r.statusCode == 429 || texto.contains('rate limit')) {
      return const ErrorNube('Demasiados intentos seguidos. Espera un minuto.');
    }
    if (texto.contains('refresh') && (texto.contains('not found') || texto.contains('invalid'))) {
      return const ErrorNube('La sesión guardada caducó. Vuelve a iniciar sesión.');
    }
    return ErrorNube('El servidor de cuentas respondió un error (${r.statusCode}).');
  }

  static Future<bool> usuarioLibre(String usuario) async {
    final r = await _peticion('POST', '/rest/v1/rpc/usuario_libre', cuerpo: {'p_usuario': usuario});
    if (r.statusCode != 200) throw _traducir(r);
    return jsonDecode(r.body) == true;
  }

  /// [extra]: aceptación de los términos y datos básicos (fecha de
  /// nacimiento, país, género); el perfil los guarda al crearse.
  static Future<Sesion> registrar(String usuario, String clave, String nombre,
      {Map<String, dynamic> extra = const {}}) async {
    final r = await _peticion('POST', '/auth/v1/signup', cuerpo: {
      'email': correoDe(usuario),
      'password': clave,
      'data': {...extra, 'usuario': usuario.trim().toLowerCase(), 'nombre': nombre},
    });
    if (r.statusCode >= 300) throw _traducir(r);
    final d = jsonDecode(r.body) as Map<String, dynamic>;
    if (d['access_token'] == null) {
      throw const ErrorNube('La cuenta se creó pero no se pudo entrar. Inicia sesión.');
    }
    return Sesion.desde(d);
  }

  static Future<Sesion> entrar(String usuario, String clave) async {
    final r = await _peticion('POST', '/auth/v1/token?grant_type=password',
        cuerpo: {'email': correoDe(usuario), 'password': clave});
    if (r.statusCode >= 300) throw _traducir(r);
    return Sesion.desde(jsonDecode(r.body) as Map<String, dynamic>);
  }

  // ------------------------------------------------------------ Google

  /// A donde vuelve el navegador despues de elegir la cuenta de Google.
  static const vueltaGoogle = 'caudal://acceso';

  /// Codigo secreto de un solo uso (PKCE): el navegador se lleva su huella y
  /// la app lo presenta al canjear; asi nadie mas puede usar el codigo.
  static String nuevoVerificador() {
    final r = Random.secure();
    const letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    return List.generate(64, (_) => letras[r.nextInt(letras.length)]).join();
  }

  static Uri urlGoogle(String verificador) {
    final huella = base64Url.encode(sha256.convert(ascii.encode(verificador)).bytes).replaceAll('=', '');
    return Uri.parse('$url/auth/v1/authorize').replace(queryParameters: {
      'provider': 'google',
      'redirect_to': vueltaGoogle,
      'code_challenge': huella,
      'code_challenge_method': 's256',
      'prompt': 'select_account',
    });
  }

  /// Cambia el codigo que trae caudal://acceso?code=... por una sesion.
  static Future<Sesion> canjearGoogle(String codigo, String verificador) async {
    final r = await _peticion('POST', '/auth/v1/token?grant_type=pkce',
        cuerpo: {'auth_code': codigo, 'code_verifier': verificador});
    if (r.statusCode >= 300) {
      final e = _traducir(r);
      if (e.mensaje.contains('(4')) {
        throw const ErrorNube('No se pudo terminar de entrar con Google. Vuelve a intentarlo.');
      }
      throw e;
    }
    return Sesion.desde(jsonDecode(r.body) as Map<String, dynamic>);
  }

  static Future<Sesion> renovar(String refresh) async {
    final r = await _peticion('POST', '/auth/v1/token?grant_type=refresh_token',
        cuerpo: {'refresh_token': refresh});
    if (r.statusCode >= 300) throw _traducir(r);
    return Sesion.desde(jsonDecode(r.body) as Map<String, dynamic>);
  }
}

class Sesion {
  Sesion(this.userId, this.acceso, this.refresh, this.expira, [this.metadatos = const {}]);

  final String userId;
  String acceso;
  String refresh;
  DateTime expira;
  final Map<String, dynamic> metadatos;
  Future<void>? _renovando;

  factory Sesion.desde(Map<String, dynamic> d) {
    final u = (d['user'] as Map?) ?? {};
    return Sesion(
      '${u['id']}',
      '${d['access_token']}',
      '${d['refresh_token']}',
      DateTime.now().add(Duration(seconds: (d['expires_in'] as num?)?.toInt() ?? 3600)),
      Map<String, dynamic>.from((u['user_metadata'] as Map?) ?? {}),
    );
  }

  /// El token vigente; se renueva solo cuando esta por caducar.
  Future<String> token() async {
    if (DateTime.now().isAfter(expira.subtract(const Duration(minutes: 2)))) {
      _renovando ??= () async {
        try {
          final nueva = await Nube.renovar(refresh);
          acceso = nueva.acceso;
          refresh = nueva.refresh;
          expira = nueva.expira;
        } finally {
          _renovando = null;
        }
      }();
      await _renovando;
    }
    return acceso;
  }

  /// Peticion a la API de datos (PostgREST).
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    final r = await Nube._peticion(metodo, '/rest/v1/$ruta',
        token: await token(), cuerpo: cuerpo, cabeceras: cabeceras);
    if (r.statusCode >= 300) throw Nube._traducir(r);
    return r.body.trim().isEmpty ? null : jsonDecode(r.body);
  }

  Future<Map<String, dynamic>> perfil() async {
    final filas = await pedir('GET', 'perfiles?select=usuario,nombre&id=eq.$userId') as List;
    if (filas.isNotEmpty) return Map<String, dynamic>.from(filas.first as Map);
    return {'usuario': metadatos['usuario'] ?? '', 'nombre': metadatos['nombre'] ?? ''};
  }

  Future<void> cambiarContrasena(String nueva) async {
    final r = await Nube._peticion('PUT', '/auth/v1/user',
        token: await token(), cuerpo: {'password': nueva});
    if (r.statusCode >= 300) throw Nube._traducir(r);
  }

  Future<void> salir() async {
    try {
      await Nube._peticion('POST', '/auth/v1/logout', token: acceso);
    } catch (_) {}
  }
}

class ErrorNube implements Exception {
  const ErrorNube(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

class SinConexion extends ErrorNube {
  const SinConexion() : super('No hay conexión. Revisa tu internet y vuelve a probar.');
}
