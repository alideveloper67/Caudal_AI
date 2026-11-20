import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import 'que_suena.dart';

/// El micrófono de verdad (paquete `record`): WAV mono a 16 kHz, lo justo para reconocer
/// (10 s ≈ 320 KB). En la web el navegador pide permiso y devuelve el audio como blob.
class GrabadorMicrofono implements Grabador {
  final _rec = AudioRecorder();
  String? _ruta;

  @override
  Future<bool> permiso() => _rec.hasPermission();

  @override
  Future<void> empezar() async {
    String ruta = '';
    if (!kIsWeb) {
      final dir = await getTemporaryDirectory();
      ruta = p.join(dir.path, 'que_suena_${DateTime.now().millisecondsSinceEpoch}.wav');
    }
    _ruta = ruta;
    await _rec.start(const RecordConfig(encoder: AudioEncoder.wav, sampleRate: 16000, numChannels: 1), path: ruta);
  }

  @override
  Future<(Uint8List, String)?> parar() async {
    final salida = await _rec.stop();
    if (salida == null || salida.isEmpty) return null;
    if (kIsWeb) {
      final r = await http.get(Uri.parse(salida)); // blob: del navegador
      return r.bodyBytes.isEmpty ? null : (r.bodyBytes, 'audio/wav');
    }
    final f = File(salida);
    if (!await f.exists()) return null;
    final bytes = await f.readAsBytes();
    try {
      await f.delete();
    } catch (_) {}
    return bytes.isEmpty ? null : (bytes, 'audio/wav');
  }

  @override
  Future<void> soltar() async {
    try {
      if (await _rec.isRecording()) await _rec.stop();
    } catch (_) {}
    await _rec.dispose();
    final r = _ruta;
    if (r != null && r.isNotEmpty && !kIsWeb) {
      try {
        final f = File(r);
        if (await f.exists()) await f.delete();
      } catch (_) {}
    }
  }
}
