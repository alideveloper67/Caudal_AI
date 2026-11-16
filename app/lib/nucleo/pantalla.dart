import 'package:flutter/services.dart' show MethodChannel;

import 'plataforma.dart';

/// Mantiene la pantalla encendida (por ejemplo, con el modo vinilo a la vista).
/// En Android se pide a la ventana (FLAG_KEEP_SCREEN_ON); en el navegador y en
/// otros sistemas no hace nada: no hay un permiso equivalente sin conexión nativa.
class PantallaEncendida {
  PantallaEncendida._();

  static const _canal = MethodChannel('caudal/pantalla');
  static bool _puesta = false;

  static Future<void> mantener(bool si) async {
    if (_puesta == si) return;
    _puesta = si;
    if (!Plataforma.esAndroid) return;
    try {
      await _canal.invokeMethod('mantener', si);
    } catch (_) {
      _puesta = !si; // no se pudo: se reintenta la próxima vez
    }
  }
}
