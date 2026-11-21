import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'nube.dart';
import 'plataforma.dart';

/// Token de este teléfono para que el servidor pueda avisar con la app cerrada
/// (mensajes y solicitudes). Solo Android: en otros sistemas no hace nada.
///
/// El token es un UUID v4 que se crea una vez y se guarda en el teléfono; el
/// servidor guarda solo ese identificador, nunca datos personales.
class AvisosDispositivo {
  AvisosDispositivo._();

  static const _clave = 'caudal_token_aviso';

  /// Un UUID v4 (8-4-4-4-12 en hexadecimal, versión 4 y variante RFC 4122).
  static String nuevoToken() {
    final r = Random.secure();
    final b = List<int>.generate(16, (_) => r.nextInt(256));
    b[6] = (b[6] & 0x0f) | 0x40; // versión 4
    b[8] = (b[8] & 0x3f) | 0x80; // variante 10xx
    final h = b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
    return '${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-'
        '${h.substring(16, 20)}-${h.substring(20)}';
  }

  /// Registra el token de este teléfono en el servidor con la sesión de la cuenta.
  /// Errores silenciosos: un fallo aquí no debe afectar a la app.
  static Future<void> registrar(Sesion sesion) async {
    if (!Plataforma.esAndroid) return;
    try {
      final p = await SharedPreferences.getInstance();
      var token = p.getString(_clave);
      if (token == null || token.isEmpty) {
        token = nuevoToken();
        await p.setString(_clave, token);
      }
      await sesion.pedir('POST', 'rpc/registrar_dispositivo_aviso', cuerpo: {'p_token': token});
    } catch (_) {}
  }

  /// Quita el token de este teléfono del servidor (al cerrar sesión) y lo borra
  /// del teléfono. Va sin sesión, con la clave pública. Si el servidor no
  /// responde bien, la clave se conserva para poder reintentar.
  static Future<void> olvidar() async {
    try {
      final p = await SharedPreferences.getInstance();
      final token = p.getString(_clave);
      if (token == null || token.isEmpty) return;
      final r = await http.post(
        Uri.parse('${Nube.url}/rest/v1/rpc/borrar_dispositivo_aviso'),
        headers: {
          'apikey': Nube.clavePublica,
          'Authorization': 'Bearer ${Nube.clavePublica}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'p_token': token}),
      );
      if (r.statusCode < 300) await p.remove(_clave);
    } catch (_) {}
  }
}
