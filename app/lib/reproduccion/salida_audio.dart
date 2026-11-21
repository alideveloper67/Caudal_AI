import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// El lado nativo del sonido (canal "caudal/sonido", ver Sonido.kt y AppDelegate.swift):
///
/// * Android: una sesión de audio por motor con el limitador del sistema y la ganancia de cada
///   canción (`sesion`, `ganancia`).
/// * Android e iPhone: por dónde sale el sonido (`salida`) y el aviso cuando cambia.
///
/// En la web y en la PC no hay nada de esto: todo devuelve null y la app sigue como siempre.
class SalidaAudio {
  SalidaAudio._();

  static const _canal = MethodChannel('caudal/sonido');
  static final ValueNotifier<String?> tipo = ValueNotifier<String?>(null);
  static bool _escuchando = false;

  static bool get _android => !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
  static bool get _movil =>
      !kIsWeb && (defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS);

  /// Sesión de audio nueva con su limitador (solo Android), o null.
  static Future<int?> nuevaSesion() async {
    if (!_android) return null;
    try {
      final v = await _canal.invokeMethod<Object?>('sesion');
      return v is int && v > 0 ? v : null;
    } catch (_) {
      return null;
    }
  }

  /// Libera el limitador de una sesión que ya no se usa (al cambiar un motor por otro nuevo).
  static Future<void> soltar(int sesion) async {
    if (!_android) return;
    try {
      await _canal.invokeMethod<Object?>('soltar', {'sesion': sesion});
    } catch (_) {}
  }

  /// Pone la ganancia (dB) de la sesión. Devuelve 'dp' (toda, con limitador), 'realce' (solo la
  /// parte positiva) o 'ninguno'.
  static Future<String> ganancia(int sesion, double db) async {
    if (!_android) return 'ninguno';
    try {
      final v = await _canal.invokeMethod<Object?>('ganancia', {'sesion': sesion, 'db': db});
      return v is String ? v : 'ninguno';
    } catch (_) {
      return 'ninguno';
    }
  }

  /// Empieza a escuchar los cambios de salida; [alCambiar] recibe (antes, ahora).
  static Future<void> escuchar(void Function(String? antes, String ahora) alCambiar) async {
    if (!_movil || _escuchando) return;
    _escuchando = true;
    _canal.setMethodCallHandler((llamada) async {
      if (llamada.method == 'salida' && llamada.arguments is String) {
        _poner(llamada.arguments as String, alCambiar);
      }
      return null;
    });
    try {
      final v = await _canal.invokeMethod<Object?>('salida');
      if (v is String) _poner(v, alCambiar);
    } catch (_) {}
  }

  static void _poner(String ahora, void Function(String? antes, String ahora) alCambiar) {
    final antes = tipo.value;
    if (antes == ahora) return;
    tipo.value = ahora;
    alCambiar(antes, ahora);
  }
}
