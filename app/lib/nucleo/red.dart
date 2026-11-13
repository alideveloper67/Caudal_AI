import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

/// Que tipo de conexion hay: para gastar menos con datos moviles.
class Red {
  static bool _conDatos = false;
  static bool _sinRed = false;
  static StreamSubscription<List<ConnectivityResult>>? _oyente;

  /// Avisa cada vez que cambia la conexion.
  static final cambios = ChangeNotifier();

  /// Con datos moviles y sin wifi ni cable.
  static bool get conDatos => _conDatos;
  static bool get sinRed => _sinRed;

  static Future<void> iniciar() async {
    if (_oyente != null) return;
    try {
      _poner(await Connectivity().checkConnectivity());
      _oyente = Connectivity().onConnectivityChanged.listen(_poner);
    } catch (_) {
      // sin el plugin (pruebas) se asume wifi
    }
  }

  static void _poner(List<ConnectivityResult> r) {
    final datos = r.contains(ConnectivityResult.mobile) &&
        !r.contains(ConnectivityResult.wifi) &&
        !r.contains(ConnectivityResult.ethernet);
    final sin = r.isEmpty || (r.length == 1 && r.first == ConnectivityResult.none);
    if (datos == _conDatos && sin == _sinRed) return;
    _conDatos = datos;
    _sinRed = sin;
    // ignore: invalid_use_of_protected_member, invalid_use_of_visible_for_testing_member
    cambios.notifyListeners();
  }
}
