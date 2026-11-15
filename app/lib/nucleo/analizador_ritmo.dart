import 'dart:io';

import 'package:ffmpeg_kit_flutter_new/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new/return_code.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

import 'coleccion.dart';
import 'ritmo.dart';

AnalisisRitmo _calcular(({Float64List muestras, int hz, double inicio}) a) =>
    estimarRitmo(a.muestras, a.hz, inicio: a.inicio);

/// Saca el ritmo de las canciones con el ffmpeg que ya trae la app y guarda el
/// resultado para no repetirlo (en el estado de la coleccion, por clave de pista).
class AnalizadorRitmo extends ChangeNotifier {
  AnalizadorRitmo(this.coleccion);

  final Coleccion coleccion;
  static const _clave = 'ritmo_cache';
  static const _tope = 800;
  static const _hz = 11025;
  static const _segundos = 45;

  final Map<String, AnalisisRitmo> _datos = {};
  bool _cargado = false;

  /// Lo ya sabido de una pista (null si aun no se analizo).
  AnalisisRitmo? de(String clave) => _datos[clave];

  Map<String, AnalisisRitmo> get todo => Map.unmodifiable(_datos);

  Future<void> cargar() async {
    if (_cargado) return;
    _cargado = true;
    try {
      final d = await coleccion.estado(_clave);
      if (d is Map) {
        for (final e in d.entries) {
          final a = AnalisisRitmo.deJson(e.value);
          if (a != null) _datos['${e.key}'] = a;
        }
      }
    } catch (_) {}
    notifyListeners();
  }

  Future<void> _guardar() async {
    while (_datos.length > _tope) {
      _datos.remove(_datos.keys.first);
    }
    try {
      await coleccion.guardarEstado(_clave, {for (final e in _datos.entries) e.key: e.value.aJson()});
    } catch (_) {}
  }

  /// Escribir el tempo a mano (o tocando el ritmo): manda sobre lo detectado.
  Future<void> ponerManual(String clave, double bpm, {double? primerTiempo}) async {
    final antes = _datos[clave];
    _datos[clave] = (antes ?? const AnalisisRitmo(bpm: 0)).copiaCon(
        bpm: bpm, primerTiempo: primerTiempo ?? antes?.primerTiempo ?? 0, manual: true);
    notifyListeners();
    await _guardar();
  }

  /// Analiza una cancion a partir de un archivo o un enlace que ffmpeg pueda leer.
  /// Devuelve null si no se pudo (sin red, formato raro...). Lo manual no se pisa.
  Future<AnalisisRitmo?> analizar(String clave, String origen, {double duracion = 0}) async {
    final previo = _datos[clave];
    if (previo != null && (previo.manual || previo.valido)) return previo;
    final inicio = duracion > 120 ? 40.0 : (duracion > 60 ? duracion * 0.25 : 0.0);
    File? salida;
    try {
      final tmp = await getTemporaryDirectory();
      salida = File('${tmp.path}/ritmo_${clave.hashCode.abs()}.raw');
      final sesion = await FFmpegKit.executeWithArguments([
        '-y', '-v', 'error', '-ss', '$inicio', '-t', '$_segundos', '-i', origen,
        '-vn', '-ac', '1', '-ar', '$_hz', '-f', 's16le', salida.path,
      ]);
      if (!ReturnCode.isSuccess(await sesion.getReturnCode()) || !await salida.exists()) return null;
      final bytes = await salida.readAsBytes();
      final n = bytes.length ~/ 2;
      if (n < _hz * 8) return null;
      final datos = ByteData.sublistView(bytes);
      final muestras = Float64List(n);
      for (var i = 0; i < n; i++) {
        muestras[i] = datos.getInt16(i * 2, Endian.little) / 32768.0;
      }
      final r = await compute(_calcular, (muestras: muestras, hz: _hz, inicio: inicio));
      _datos[clave] = r;
      notifyListeners();
      await _guardar();
      return r;
    } catch (_) {
      return null;
    } finally {
      try {
        await salida?.delete();
      } catch (_) {}
    }
  }
}
