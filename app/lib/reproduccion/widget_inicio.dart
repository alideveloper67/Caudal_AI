import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../nucleo/plataforma.dart';

/// El widget de la pantalla de inicio de Android (CaudalWidget.kt): carátula,
/// título, play/pausa y siguiente. Dart le cuenta lo que suena por el canal
/// `caudal/widget` y el widget devuelve los toques por el mismo canal.
/// En iPhone no hace nada.
class WidgetInicio {
  WidgetInicio._();

  static const _canal = MethodChannel('caudal/widget');
  static String _ultimo = '';
  static Map<String, Object?>? _datos;

  /// [alternar] y [siguiente] se llaman al tocar los botones del widget.
  static void iniciar({required Future<void> Function() alternar, required Future<void> Function() siguiente}) {
    if (!Plataforma.esAndroid) return;
    _canal.setMethodCallHandler((llamada) async {
      switch (llamada.method) {
        case 'alternar':
          await alternar();
        case 'siguiente':
          await siguiente();
        case 'pedir':
          // el lado nativo acaba de conectarse: repetir lo ultimo
          _ultimo = '';
          final d = _datos;
          if (d != null) await _enviar(d);
      }
      return null;
    });
  }

  static Future<void> publicar({
    required bool hay,
    required String titulo,
    required String artista,
    required String arte,
    required bool sonando,
  }) async {
    if (!Plataforma.esAndroid) return;
    final d = <String, Object?>{
      'hay': hay,
      'titulo': titulo,
      'artista': artista,
      'arte': arte,
      'sonando': sonando,
    };
    _datos = d;
    await _enviar(d);
  }

  static Future<void> _enviar(Map<String, Object?> d) async {
    final clave = '${d['hay']}|${d['titulo']}|${d['artista']}|${d['arte']}|${d['sonando']}';
    if (clave == _ultimo) return;
    _ultimo = clave;
    try {
      await _canal.invokeMethod('publicar', d);
    } on MissingPluginException {
      // la actividad aun no conecto el canal: lo pedira con 'pedir'
      _ultimo = '';
    } catch (e) {
      _ultimo = '';
      debugPrint('widget: $e');
    }
  }
}
