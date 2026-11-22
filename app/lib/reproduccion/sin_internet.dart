import 'dart:async';
import 'dart:io' show HandshakeException, SocketException;

import '../nucleo/nube.dart' show SinConexion;
import '../nucleo/red.dart';

/// ¿Ese error es por no tener internet (o por una red que no responde)?
bool esFalloDeRed(Object e) {
  if (e is SocketException || e is TimeoutException || e is HandshakeException || e is SinConexion) {
    return true;
  }
  final t = '$e'.toLowerCase();
  return RegExp(r'socket|timed? ?out|timeout|connection (closed|refused|reset|failed|abort)|'
          r'failed host lookup|host lookup|network is unreachable|no address associated|'
          r'clientexception|handshake|sin conexi[oó]n|no hay conexi[oó]n|sin internet|revisa tu (conexi[oó]n|internet)')
      .hasMatch(t);
}

/// Si ahora se puede contar con internet. Sin ninguna red (lo dice el sistema) o tras un fallo de
/// red reciente se da por perdido; vuelve con el siguiente éxito o en cuanto cambia la red.
/// Así el reproductor no se queda probando una por una las canciones que no están descargadas.
class EstadoInternet {
  EstadoInternet({bool Function()? sinRed, DateTime Function()? ahora,
      this.vigencia = const Duration(minutes: 2)})
      : _sinRed = sinRed ?? (() => Red.sinRed),
        _ahora = ahora ?? DateTime.now {
    Red.cambios.addListener(_alCambiarRed);
  }

  final bool Function() _sinRed;
  final DateTime Function() _ahora;

  /// Cuánto se cree en un fallo de red sin otra noticia.
  final Duration vigencia;

  DateTime? _fallo;

  bool get sinInternet {
    if (_sinRed()) return true;
    final f = _fallo;
    return f != null && _ahora().difference(f) < vigencia;
  }

  void fallo() => _fallo = _ahora();
  void exito() => _fallo = null;

  void _alCambiarRed() => _fallo = null;

  void cerrar() => Red.cambios.removeListener(_alCambiarRed);
}
