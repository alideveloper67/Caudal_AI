import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'version.dart';

/// Arranque a prueba de trabas.
///
/// Antes de cada paso del arranque se anota cual es (en un archivo, de forma
/// sincrona, para que quede escrito aunque despues se congele todo). Si la
/// vez anterior la pantalla nunca llego a dibujarse, esta vez se arranca en
/// **modo seguro**: sin las piezas nativas que pueden trabar (controles en la
/// notificacion, widget, ventana flotante, navegador oculto). El modo seguro
/// dura hasta que se instala otra version.
///
/// En Android, ademas, un vigilante nativo (Vigilante.kt) anota en que linea
/// estaba trabado el sistema; se le muestra al usuario para que nos lo envie.
class Diagnostico {
  Diagnostico._();

  static const _canal = MethodChannel('caudal/diagnostico');
  static File? _marca;

  /// true: arrancar sin las piezas nativas opcionales.
  static bool modoSeguro = false;

  /// Lo que se le ensena al usuario si la vez anterior se trabo (si no, null).
  static String? detalle;

  static Future<void> iniciar() async {
    Directory dir;
    try {
      dir = await getApplicationSupportDirectory();
    } catch (_) {
      return;
    }
    await iniciarEn(dir);
  }

  @visibleForTesting
  static Future<void> iniciarEn(Directory dir) async {
    modoSeguro = false;
    detalle = null;
    try {
      if (!await dir.exists()) await dir.create(recursive: true);
      _marca = File(p.join(dir.path, 'arranque.txt'));
      var previo = '';
      if (await _marca!.exists()) previo = (await _marca!.readAsString()).trim();
      final partes = previo.split('|');
      final mismaVersion = partes.isNotEmpty && partes[0] == versionApp;
      final paso = partes.length > 1 ? partes[1] : '';
      final seguroAntes = partes.length > 2 && partes[2] == '1';
      final seTrabo = mismaVersion && paso.isNotEmpty && paso != 'pintado' && paso != 'aviso';

      String? traba;
      if (defaultTargetPlatform == TargetPlatform.android) {
        try {
          traba = await _canal.invokeMethod<String>('traba').timeout(const Duration(seconds: 3));
        } catch (_) {}
      }

      modoSeguro = mismaVersion && (seguroAntes || seTrabo);
      if (seTrabo || (traba != null && traba.isNotEmpty)) {
        detalle = [
          if (seTrabo) 'Último paso del arranque: $paso${seguroAntes ? ' (ya en modo seguro)' : ''}',
          if (traba != null && traba.isNotEmpty) traba,
        ].join('\n');
      }
    } catch (_) {}
    marcar('inicio');
  }

  /// Anota el paso en curso. Sincrono a proposito: si el paso congela la app,
  /// lo anotado ya esta en disco.
  static void marcar(String paso) {
    try {
      _marca?.writeAsStringSync('$versionApp|$paso|${modoSeguro ? 1 : 0}', flush: true);
    } catch (_) {}
  }

  /// La pantalla ya se dibujo: este arranque salio bien.
  static void pintado() => marcar('pintado');

  /// Mientras se ensena el aviso de la traba anterior, el arranque aun no
  /// empezo: si la app se cierra ahi, no cuenta como otra traba.
  static void pintadoAviso() => marcar('aviso');
}
