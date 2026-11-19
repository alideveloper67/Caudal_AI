// La insignia de calidad: códec y tasa de lo que suena, sin inventar lo que no se sabe.
import 'package:caudal/nucleo/calidad_sonido.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('sin fuente no hay insignia', () {
    expect(calidadDe(null), isNull);
  });

  test('audio de YouTube: códec bonito y tasa', () {
    final c = calidadDe(Fuente(url: 'https://x/a', audioCodec: 'opus', abr: 160));
    expect(c!.etiqueta, 'Opus · 160 kbps');
    expect(c.detalle, contains('160 kilobits'));
    expect(calidadDe(Fuente(url: 'u', audioCodec: 'mp4a', abr: 128))!.etiqueta, 'AAC · 128 kbps');
    expect(calidadDe(Fuente(url: 'u', audioCodec: 'mp4a.40.2', abr: 128))!.etiqueta, 'AAC · 128 kbps');
  });

  test('si no se conoce la tasa se dice solo el códec, y si no se sabe nada no se muestra', () {
    expect(calidadDe(Fuente(url: 'u', audioCodec: 'opus'))!.etiqueta, 'Opus');
    expect(calidadDe(Fuente(url: 'u', abr: 96))!.etiqueta, '96 kbps');
    expect(calidadDe(Fuente(url: 'u')), isNull);
  });

  test('video: resolución, cuadros y códec; con la pantalla en audio, el audio', () {
    final v = Fuente(url: 'u', audioUrl: 'a', alto: 1080, fps: 60, videoCodec: 'avc1.640028', audioCodec: 'opus', abr: 160);
    expect(calidadDe(v, enVideo: true)!.etiqueta, '1080p60 · H.264');
    expect(calidadDe(v)!.etiqueta, 'Opus · 160 kbps');
    expect(calidadDe(Fuente(url: 'u', alto: 2160, fps: 30, videoCodec: 'vp09.00'), enVideo: true)!.etiqueta, '4K · VP9');
    expect(calidadDe(Fuente(url: 'u', alto: 720, fps: 30), enVideo: true)!.etiqueta, '720p');
  });

  test('archivos del teléfono: el códec sale de la extensión', () {
    expect(calidadDe(Fuente.archivo('/m/cancion.FLAC'))!.etiqueta, 'FLAC · local');
    expect(calidadDe(Fuente.archivo('/m/cancion.m4a'))!.etiqueta, 'AAC · local');
    expect(calidadDe(Fuente.archivo('/m/cancion.xyz'))!.etiqueta, 'Local');
  });

  test('el reproductor de YouTube del navegador no da más datos', () {
    expect(calidadDe(Fuente(url: 'yt:abc', audioCodec: 'YouTube'))!.etiqueta, 'YouTube');
  });
}
