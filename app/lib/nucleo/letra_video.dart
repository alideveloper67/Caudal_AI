import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:ffmpeg_kit_flutter_new/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new/return_code.dart';
import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// «Letra animada» para estados: un video vertical de 1080x1920 donde las líneas
/// elegidas se encienden una a una sobre la tarjeta, con un zoom lento.
///
/// Para que corra hasta en teléfonos viejos no se dibuja cuadro a cuadro: la
/// pantalla saca UNA imagen por línea (la tarjeta con esa línea encendida) y
/// ffmpeg las une con su duración y le pone el movimiento. Todo lo que no toca
/// ffmpeg está aquí como funciones puras para poder probarlo.
class GuionVideoLetra {
  const GuionVideoLetra(this.duraciones);

  /// Duración de cada imagen (una por línea), en segundos.
  final List<double> duraciones;

  static const ancho = 1080;
  static const alto = 1920;
  static const fps = 30;
  static const minimo = 8.0;
  static const maximo = 12.0;

  /// Lo que se queda quieta la primera línea antes de empezar y la última al final.
  static const _entrada = 0.8;
  static const _salida = 1.4;

  double get total => duraciones.fold(0.0, (a, b) => a + b);
  int get pasos => duraciones.length;

  /// Reparte entre 8 y 12 segundos según cuántas líneas haya (de 1 a 8).
  factory GuionVideoLetra.paraLineas(int lineas) {
    final n = lineas.clamp(1, 8);
    final total = (_entrada + _salida + n * 2.2).clamp(minimo, maximo);
    final porLinea = (total - _entrada - _salida) / n;
    final d = List<double>.filled(n, porLinea);
    d[0] += _entrada;
    d[n - 1] += _salida;
    return GuionVideoLetra(d);
  }

  /// El archivo que lee el demuxer `concat`: cada imagen con su duración. (Quirk de
  /// ffmpeg: la última se repite sin duración para que no se recorte.)
  String listaConcat(List<String> rutas) {
    assert(rutas.length == duraciones.length);
    String q(String r) => "file '${r.replaceAll('\\', '/').replaceAll("'", "'\\''")}'";
    final b = StringBuffer('ffconcat version 1.0\n');
    for (var i = 0; i < rutas.length; i++) {
      b
        ..writeln(q(rutas[i]))
        ..writeln('duration ${duraciones[i].toStringAsFixed(3)}');
    }
    b.writeln(q(rutas.last));
    return b.toString();
  }

  /// Los argumentos de ffmpeg (sin pasar por una línea de texto, para no depender de comillas).
  /// H.264 con CRF 23 y 30 cuadros: buena calidad y pocos MB; el zoom llega a un 8 %.
  List<String> argumentos({required String lista, required String salida}) => [
        '-y',
        '-f', 'concat', '-safe', '0',
        '-i', lista,
        '-vf',
        'fps=$fps,'
            "zoompan=z='min(1+0.00027*on,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=${ancho}x$alto:fps=$fps,"
            'format=yuv420p',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
        '-profile:v', 'high', '-movflags', '+faststart',
        '-an',
        '-t', total.toStringAsFixed(3),
        salida,
      ];
}

class VideoCancelado implements Exception {
  @override
  String toString() => 'Se canceló el video.';
}

/// Une las imágenes en el video con ffmpeg_kit. [progreso] va de 0 a 1 y [cancelado] se
/// consulta cada rato: si devuelve true se corta ffmpeg. Devuelve la ruta del .mp4.
Future<String> crearVideoDeLetra({
  required List<List<int>> imagenesPng,
  required GuionVideoLetra guion,
  void Function(double)? progreso,
  bool Function()? cancelado,
}) async {
  assert(imagenesPng.length == guion.pasos);
  final base = await getTemporaryDirectory();
  final carpeta = Directory(p.join(base.path, 'letra_video_${DateTime.now().millisecondsSinceEpoch}'));
  await carpeta.create(recursive: true);
  final salida = p.join(base.path, 'caudal_letra_${DateTime.now().millisecondsSinceEpoch}.mp4');
  try {
    final rutas = <String>[];
    for (final (i, png) in imagenesPng.indexed) {
      final f = File(p.join(carpeta.path, 'paso_$i.png'));
      await f.writeAsBytes(png, flush: true);
      rutas.add(f.path);
    }
    final lista = File(p.join(carpeta.path, 'lista.txt'));
    await lista.writeAsString(guion.listaConcat(rutas), flush: true);

    final fin = Completer<bool>();
    var salidaFfmpeg = '';
    final totalMs = guion.total * 1000;
    final sesion = await FFmpegKit.executeWithArgumentsAsync(
      guion.argumentos(lista: lista.path, salida: salida),
      (s) async {
        final ok = ReturnCode.isSuccess(await s.getReturnCode());
        if (!ok) salidaFfmpeg = await s.getOutput() ?? '';
        if (!fin.isCompleted) fin.complete(ok);
      },
      null,
      (e) => progreso?.call((e.getTime() / totalMs).clamp(0.0, 1.0).toDouble()),
    );
    while (!fin.isCompleted) {
      await Future<void>.delayed(const Duration(milliseconds: 300));
      if (cancelado?.call() ?? false) {
        await FFmpegKit.cancel(sesion.getSessionId());
        throw VideoCancelado();
      }
    }
    if (!await fin.future) {
      final lineas = salidaFfmpeg.trim().split('\n').where((x) => x.trim().isNotEmpty).toList();
      throw Exception(lineas.isEmpty ? 'ffmpeg no pudo crear el video' : lineas.last.trim());
    }
    return salida;
  } catch (_) {
    try {
      await File(salida).delete();
    } catch (_) {}
    rethrow;
  } finally {
    try {
      await carpeta.delete(recursive: true);
    } catch (_) {}
  }
}

@visibleForTesting
int cuadrosDelVideo(GuionVideoLetra g) => max(1, (g.total * GuionVideoLetra.fps).round());
