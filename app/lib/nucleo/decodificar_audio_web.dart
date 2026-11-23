import 'dart:js_interop';
import 'dart:math';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

import 'archivos_web.dart';

/// [segundos] de [origen] desde [inicio], en mono a [hz] Hz (null si no se pudo).
Future<Float64List?> decodificarAudio(String origen, {required int hz, double inicio = 0, double segundos = 45}) async {
  final url = ArchivosWeb.esRef(origen) ? await ArchivosWeb.url(origen) : origen;
  if (url == null) return null;
  final r = await web.window.fetch(url.toJS).toDart;
  if (!r.ok) return null;
  final datos = await r.arrayBuffer().toDart;
  final ctx = web.OfflineAudioContext(1.toJS, 1, hz.toDouble());
  final b = await ctx.decodeAudioData(datos).toDart;
  final desde = min(b.length, (inicio * b.sampleRate).round());
  final hasta = min(b.length, desde + (segundos * b.sampleRate).round());
  if (hasta <= desde) return null;
  final salida = Float64List(hasta - desde);
  for (var c = 0; c < b.numberOfChannels; c++) {
    final canal = b.getChannelData(c).toDart;
    for (var i = desde; i < hasta; i++) {
      salida[i - desde] += canal[i] / b.numberOfChannels;
    }
  }
  return salida;
}
