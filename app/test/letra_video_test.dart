import 'dart:io';

import 'package:caudal/nucleo/letra_video.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:path/path.dart' as p;

void main() {
  group('GuionVideoLetra', () {
    test('dura entre 8 y 12 segundos con cualquier número de líneas', () {
      for (var n = 1; n <= 8; n++) {
        final g = GuionVideoLetra.paraLineas(n);
        expect(g.pasos, n);
        expect(g.total, inInclusiveRange(GuionVideoLetra.minimo, GuionVideoLetra.maximo), reason: '$n líneas');
        expect(g.duraciones.every((d) => d > 0), isTrue);
      }
    });

    test('pide como mucho 8 pasos aunque lleguen más líneas', () {
      expect(GuionVideoLetra.paraLineas(20).pasos, 8);
      expect(GuionVideoLetra.paraLineas(0).pasos, 1);
    });

    test('la primera y la última línea se quedan un poco más', () {
      final g = GuionVideoLetra.paraLineas(4);
      expect(g.duraciones.first, greaterThan(g.duraciones[1]));
      expect(g.duraciones.last, greaterThan(g.duraciones[1]));
    });

    test('la lista de concat repite la última imagen y escapa las comillas', () {
      final g = GuionVideoLetra.paraLineas(2);
      final t = g.listaConcat([r"C:\tmp\paso_0.png", "/tmp/it's.png"]);
      final lineas = t.trim().split('\n');
      expect(lineas.first, 'ffconcat version 1.0');
      expect(lineas[1], "file 'C:/tmp/paso_0.png'");
      expect(lineas[2], startsWith('duration '));
      expect(lineas[3], r"file '/tmp/it'\''s.png'");
      expect(lineas.last, r"file '/tmp/it'\''s.png'");
      expect(lineas.where((l) => l.startsWith('file ')).length, 3);
    });

    test('los argumentos de ffmpeg piden 1080x1920, H.264, CRF 23 y 30 cuadros', () {
      final g = GuionVideoLetra.paraLineas(3);
      final a = g.argumentos(lista: 'lista.txt', salida: 'salida.mp4');
      final texto = a.join(' ');
      expect(a.first, '-y');
      expect(texto, contains('-f concat'));
      expect(texto, contains('-c:v libx264'));
      expect(texto, contains('-crf 23'));
      expect(texto, contains('1080x1920'));
      expect(texto, contains('zoompan'));
      expect(texto, contains('format=yuv420p'));
      expect(a.last, 'salida.mp4');
      expect(a[a.indexOf('-t') + 1], g.total.toStringAsFixed(3));
      expect(cuadrosDelVideo(g), (g.total * 30).round());
    });
  });

  // Prueba real del guion con el ffmpeg de escritorio (mismos filtros que ffmpeg_kit en el
  // teléfono): crea las imágenes, corre el comando y mira que salga un mp4 vertical de la
  // duración y el peso esperados. Si no hay ffmpeg en esta máquina, se salta.
  group('el comando corre de verdad', () {
    final ffmpeg = [
      r'C:\Users\USER\Caudal\escritorio\bin\ffmpeg.exe',
      r'C:\Users\USER\Caudal\escritorio\bin\ffmpeg',
    ].where((r) => File(r).existsSync()).firstOrNull;
    final ffprobe = ffmpeg == null ? null : p.join(p.dirname(ffmpeg), 'ffprobe.exe');

    test('crea un mp4 vertical de la duración del guion', () async {
      final dir = await Directory.systemTemp.createTemp('letra_video_prueba');
      addTearDown(() => dir.delete(recursive: true));
      final g = GuionVideoLetra.paraLineas(3);
      final rutas = <String>[];
      for (var i = 0; i < g.pasos; i++) {
        final im = img.Image(width: 1080, height: 1920);
        img.fill(im, color: img.ColorRgb8(20 + i * 60, 30, 90));
        img.fillRect(im, x1: 100, y1: 800 + i * 150, x2: 980, y2: 900 + i * 150, color: img.ColorRgb8(255, 255, 255));
        final f = File(p.join(dir.path, 'paso_$i.png'));
        await f.writeAsBytes(img.encodePng(im));
        rutas.add(f.path);
      }
      final lista = File(p.join(dir.path, 'lista.txt'));
      await lista.writeAsString(g.listaConcat(rutas));
      final salida = p.join(dir.path, 'letra.mp4');
      final r = await Process.run(ffmpeg!, g.argumentos(lista: lista.path, salida: salida));
      expect(r.exitCode, 0, reason: '${r.stderr}');
      final mp4 = File(salida);
      expect(mp4.existsSync(), isTrue);
      expect(mp4.lengthSync(), lessThan(15 * 1024 * 1024));
      final sonda = await Process.run(ffprobe!, [
        '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,codec_name,pix_fmt',
        '-show_entries', 'format=duration', '-of', 'default=nw=1', salida,
      ]);
      final t = '${sonda.stdout}';
      expect(t, contains('codec_name=h264'));
      expect(t, contains('width=1080'));
      expect(t, contains('height=1920'));
      expect(t, contains('pix_fmt=yuv420p'));
      final dur = double.parse(RegExp(r'duration=([\d.]+)').firstMatch(t)!.group(1)!);
      expect(dur, closeTo(g.total, 0.6));
    }, skip: ffmpeg == null ? 'no hay ffmpeg en esta máquina' : false, timeout: const Timeout(Duration(minutes: 3)));
  });
}
