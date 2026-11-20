import 'package:flutter/material.dart';

import '../ui/paginas/modo_auto_pagina.dart';

/// Abre el modo coche (la pantalla de botones enormes, `ModoAutoPagina`) una sola
/// vez aunque lo pidan a la vez el Bluetooth del coche, el aviso y un acceso
/// directo: el segundo pedido no apila otra pantalla igual encima.
class AbrirModoCoche {
  AbrirModoCoche._();

  static bool _abierto = false;

  /// Si ahora mismo hay un modo coche abierto desde aquí.
  static bool get abierto => _abierto;

  /// Solo para las pruebas: qué pantalla se abre.
  @visibleForTesting
  static Widget Function() pantalla = () => const ModoAutoPagina();

  static Future<void> abrir(BuildContext context) async {
    if (_abierto) return;
    _abierto = true;
    try {
      await Navigator.of(context, rootNavigator: true).push(MaterialPageRoute<void>(
        fullscreenDialog: true,
        settings: const RouteSettings(name: 'modo_coche'),
        builder: (_) => pantalla(),
      ));
    } finally {
      _abierto = false;
    }
  }

  @visibleForTesting
  static void reiniciar() => _abierto = false;
}
