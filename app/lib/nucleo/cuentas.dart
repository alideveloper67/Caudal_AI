import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'nube.dart';

/// Una cuenta con la que se entro. [sesion] es nula si se entro sin internet
/// con la sesion guardada (la biblioteca local funciona igual).
class Cuenta {
  Cuenta({required this.id, required this.usuario, required this.nombre, this.sesion,
      this.sinConexion = false, this.google = false});

  final String id;
  final String usuario;
  final String nombre;
  final Sesion? sesion;
  final bool sinConexion;

  /// Entro con Google: no tiene contraseña de Caudal que cambiar.
  final bool google;

  String get inicial => (nombre.isNotEmpty ? nombre : usuario).substring(0, 1).toUpperCase();
}

class ErrorCuenta implements Exception {
  const ErrorCuenta(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

/// Las mismas cuentas que Caudal para Windows (Supabase).
class Cuentas {
  static const _claveSesion = 'cuenta.sesion';
  static const _claveUltimo = 'cuenta.ultimo';

  static final _patron = RegExp(r'^[a-z0-9._-]{3,30}$');

  static Future<Cuenta> crear(String usuario, String clave, String nombre,
      {Map<String, dynamic> extra = const {}}) async {
    usuario = usuario.trim().toLowerCase();
    if (!_patron.hasMatch(usuario)) {
      throw const ErrorCuenta('El usuario debe tener de 3 a 30 letras o números '
          '(también . _ -), sin espacios ni tildes.');
    }
    if (clave.length < 6) {
      throw const ErrorCuenta('La contraseña necesita al menos 6 caracteres.');
    }
    final nombreFinal = nombre.trim().isEmpty ? usuario : nombre.trim();
    try {
      if (!await Nube.usuarioLibre(usuario)) {
        throw const ErrorCuenta('Ese usuario ya existe. Inicia sesión o elige otro.');
      }
      final s = await Nube.registrar(usuario, clave, nombreFinal, extra: extra);
      return Cuenta(id: s.userId, usuario: usuario, nombre: nombreFinal, sesion: s);
    } on ErrorNube catch (e) {
      throw ErrorCuenta(e.mensaje);
    }
  }

  static Future<Cuenta> entrar(String usuario, String clave) async {
    usuario = usuario.trim().toLowerCase();
    if (usuario.isEmpty) throw const ErrorCuenta('Escribe tu usuario.');
    try {
      final s = await Nube.entrar(usuario, clave);
      final perfil = await s.perfil();
      return Cuenta(
        id: s.userId,
        usuario: '${perfil['usuario'] ?? usuario}',
        nombre: '${perfil['nombre'] ?? usuario}',
        sesion: s,
      );
    } on ErrorNube catch (e) {
      throw ErrorCuenta(e.mensaje);
    }
  }

  /// Entrar (o registrarse, es lo mismo) con la cuenta de Google. [enlace]
  /// es el caudal://acceso?... con el que vuelve el navegador.
  static Future<Cuenta> conGoogle(String enlace, String verificador) async {
    final u = Uri.tryParse(enlace);
    final q = {...?u?.queryParameters, ...Uri.splitQueryString(u?.fragment ?? '')};
    final codigo = q['code'] ?? '';
    if (codigo.isEmpty) {
      final motivo = (q['error_description'] ?? q['error'] ?? '').toLowerCase();
      if (motivo.contains('denied') || motivo.contains('cancel')) {
        throw const ErrorCuenta('Cancelaste la entrada con Google.');
      }
      throw const ErrorCuenta('Google no dejó entrar. Vuelve a intentarlo.');
    }
    try {
      final s = await Nube.canjearGoogle(codigo, verificador);
      final perfil = await s.perfil();
      final usuario = '${perfil['usuario'] ?? ''}';
      final nombre = '${perfil['nombre'] ?? ''}'.trim();
      return Cuenta(id: s.userId, usuario: usuario, nombre: nombre.isEmpty ? usuario : nombre,
          sesion: s, google: true);
    } on ErrorNube catch (e) {
      throw ErrorCuenta(e.mensaje);
    }
  }

  static Future<void> cambiarContrasena(Cuenta c, String actual, String nueva) async {
    if (nueva.length < 6) {
      throw const ErrorCuenta('La contraseña nueva necesita al menos 6 caracteres.');
    }
    try {
      await Nube.entrar(c.usuario, actual);
    } on ErrorNube {
      throw const ErrorCuenta('La contraseña actual no es correcta.');
    }
    try {
      await c.sesion!.cambiarContrasena(nueva);
    } on ErrorNube catch (e) {
      throw ErrorCuenta(e.mensaje);
    }
  }

  // ------------------------------------------------------------ sesion guardada

  static Future<void> recordar(Cuenta c) async {
    if (c.sesion == null) return;
    final p = await SharedPreferences.getInstance();
    await p.setString(_claveSesion, jsonEncode({
      'id': c.id, 'usuario': c.usuario, 'nombre': c.nombre, 'refresh': c.sesion!.refresh,
      if (c.google) 'google': true,
    }));
  }

  /// El token de renovacion cambia al usarse: hay que guardar el nuevo.
  static Future<void> actualizarRecordada(Cuenta c) async {
    final p = await SharedPreferences.getInstance();
    if (p.containsKey(_claveSesion)) await recordar(c);
  }

  static Future<void> olvidar([Cuenta? c]) async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_claveSesion);
    await c?.sesion?.salir();
  }

  static Future<Cuenta?> recordada() async {
    final p = await SharedPreferences.getInstance();
    final texto = p.getString(_claveSesion);
    if (texto == null) return null;
    final g = jsonDecode(texto) as Map<String, dynamic>;
    try {
      final s = await Nube.renovar('${g['refresh']}');
      final c = Cuenta(id: '${g['id']}', usuario: '${g['usuario']}', nombre: '${g['nombre']}',
          sesion: s, google: g['google'] == true);
      await recordar(c);
      return c;
    } on SinConexion {
      // sin internet se entra igual: se sincroniza cuando vuelva la red
      final s = Sesion('${g['id']}', '', '${g['refresh']}', DateTime(2000));
      return Cuenta(id: '${g['id']}', usuario: '${g['usuario']}', nombre: '${g['nombre']}',
          sesion: s, sinConexion: true, google: g['google'] == true);
    } on ErrorNube {
      await olvidar();
      return null;
    }
  }

  static Future<String> ultimoUsuario() async =>
      (await SharedPreferences.getInstance()).getString(_claveUltimo) ?? '';

  static Future<void> anotarUltimo(String usuario) async =>
      (await SharedPreferences.getInstance()).setString(_claveUltimo, usuario);

  static Future<bool> hayCuentas() async => (await ultimoUsuario()).isNotEmpty;
}
