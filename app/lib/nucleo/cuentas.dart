import 'dart:async';
import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'nube.dart';
import 'red.dart';

/// Una cuenta con la que se entro. [sesion] es nula si se entro sin internet
/// con la sesion guardada (la biblioteca local funciona igual).
class Cuenta {
  Cuenta({required this.id, required this.usuario, required this.nombre, this.sesion,
      this.sinConexion = false, this.google = false}) {
    // el token de renovación cambia al usarse y el viejo deja de valer: se guarda en ese mismo momento
    // (antes, en la siguiente sincronización; si Android cerraba la app antes, pedía iniciar sesión)
    sesion?.alRenovar = () => Cuentas.actualizarRecordada(this);
  }

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

  static Future<Map<String, dynamic>?> _guardada() async {
    final p = await SharedPreferences.getInstance();
    final texto = p.getString(_claveSesion);
    if (texto == null) return null;
    try {
      final g = jsonDecode(texto);
      return g is Map ? Map<String, dynamic>.from(g) : null;
    } catch (_) {
      return null;
    }
  }

  static Cuenta _sinConexion(Map<String, dynamic> g) {
    // sin internet se entra igual: la sesión se renueva sola cuando vuelva la red
    final s = Sesion('${g['id']}', '', '${g['refresh']}', DateTime(2000));
    return Cuenta(id: '${g['id']}', usuario: '${g['usuario']}', nombre: '${g['nombre']}',
        sesion: s, sinConexion: true, google: g['google'] == true);
  }

  /// La cuenta guardada sin preguntar a la nube (para cuando el arranque se alarga).
  static Future<Cuenta?> guardadaSinConexion() async {
    final g = await _guardada();
    return g == null ? null : _sinConexion(g);
  }

  /// La cuenta guardada, con la sesión renovada si hay internet. Sin red entra al momento y con
  /// una red que no responde espera como mucho [espera]: Caudal siempre abre sin internet.
  /// Solo se olvida la sesión si la nube dice que ya no vale (nunca por un fallo de red).
  static Future<Cuenta?> recordada({Duration espera = const Duration(seconds: 6),
      Future<bool> Function()? sinRed, Future<Sesion> Function(String refresh)? renovar}) async {
    final g = await _guardada();
    if (g == null) return null;
    try {
      if (await (sinRed ?? Red.comprobarSinRed)()) return _sinConexion(g);
    } catch (_) {}
    final pedido = (renovar ?? Nube.renovar)('${g['refresh']}');
    try {
      final s = await pedido.timeout(espera);
      final c = Cuenta(id: '${g['id']}', usuario: '${g['usuario']}', nombre: '${g['nombre']}',
          sesion: s, google: g['google'] == true);
      await recordar(c);
      return c;
    } on TimeoutException {
      // se entra ya, pero la renovación sigue en marcha: si llega, su token se guarda (el viejo ya no vale)
      final c = _sinConexion(g);
      unawaited(pedido.then((s) async {
        final mia = c.sesion!;
        if (mia.refresh != '${g['refresh']}') return;      // ya se renovó por otro lado
        mia.acceso = s.acceso;
        mia.refresh = s.refresh;
        mia.expira = s.expira;
        await actualizarRecordada(c);
      }).catchError((Object _) {}));
      return c;
    } on SinConexion {
      // OJO: SinConexion es un ErrorNube; va antes para que la falta de red nunca cierre la sesión
      return _sinConexion(g);
    } on ErrorNube {
      // solo llega aquí lo que la nube dijo de verdad: esta sesión ya no vale… salvo que otra copia de
      // Caudal la haya renovado mientras tanto: se prueba con lo último guardado antes de rendirse
      final p = await SharedPreferences.getInstance();
      try {
        await p.reload();
      } catch (_) {}
      final otra = await _guardada();
      if (otra != null && '${otra['refresh']}' != '${g['refresh']}') {
        try {
          final s = await (renovar ?? Nube.renovar)('${otra['refresh']}').timeout(espera);
          final c = Cuenta(id: '${otra['id']}', usuario: '${otra['usuario']}', nombre: '${otra['nombre']}',
              sesion: s, google: otra['google'] == true);
          await recordar(c);
          return c;
        } on SinConexion {
          return _sinConexion(otra);
        } on ErrorNube {
          // de verdad ya no vale
        } catch (_) {
          return _sinConexion(otra);
        }
      }
      await olvidar();
      return null;
    } catch (_) {
      // cualquier otra cosa rara: se entra sin conexión
      return _sinConexion(g);
    }
  }

  static Future<String> ultimoUsuario() async =>
      (await SharedPreferences.getInstance()).getString(_claveUltimo) ?? '';

  static Future<void> anotarUltimo(String usuario) async =>
      (await SharedPreferences.getInstance()).setString(_claveUltimo, usuario);

  static Future<bool> hayCuentas() async => (await ultimoUsuario()).isNotEmpty;
}
