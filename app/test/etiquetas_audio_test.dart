import 'dart:convert';
import 'dart:typed_data';

import 'package:caudal/nucleo/etiquetas_audio.dart';
import 'package:flutter_test/flutter_test.dart';

List<int> _be(int n, [int bytes = 4]) => [for (var i = bytes - 1; i >= 0; i--) n >> (8 * i) & 0xFF];
List<int> _le(int n) => _be(n).reversed.toList();
List<int> _segura(int n) => [n >> 21 & 0x7F, n >> 14 & 0x7F, n >> 7 & 0x7F, n & 0x7F];
List<int> _utf16(String s) => [0xFF, 0xFE, for (final c in s.codeUnits) ...[c & 0xFF, c >> 8]];

Uint8List _id3(int version, List<int> marcos) =>
    Uint8List.fromList([...ascii.encode('ID3'), version, 0, 0, ..._segura(marcos.length + 20), ...marcos,
      ...List.filled(20, 0), ...List.filled(64, 0xFF)]);

List<int> _marco(int version, String id, List<int> c) =>
    [...ascii.encode(id), ...(version == 4 ? _segura(c.length) : _be(c.length)), 0, 0, ...c];

List<int> _atomo(String n, List<int> c) => [..._be(c.length + 8), ...latin1.encode(n), ...c];

void main() {
  test('ID3v2.3 con UTF-16 y carátula', () {
    final e = EtiquetasAudio.leer(_id3(3, [
      ..._marco(3, 'TIT2', [1, ..._utf16('Canción ñandú')]),
      ..._marco(3, 'TPE1', [0, ...latin1.encode('José')]),
      ..._marco(3, 'APIC', [0, ...ascii.encode('image/jpeg'), 0, 3, 0, 9, 8, 7]),
    ]));
    expect(e.titulo, 'Canción ñandú');
    expect(e.artista, 'José');
    expect(e.portada, [9, 8, 7]);
  });

  test('ID3v2.4 con UTF-8: cuenta el primer artista', () {
    final e = EtiquetasAudio.leer(_id3(4, [
      ..._marco(4, 'TIT2', [3, ...utf8.encode('Título')]),
      ..._marco(4, 'TPE1', [3, ...utf8.encode('Ana'), 0, ...utf8.encode('Luis')]),
      ..._marco(4, 'TALB', [3, ...utf8.encode('Álbum')]),
    ]));
    expect((e.titulo, e.artista, e.album), ('Título', 'Ana', 'Álbum'));
  });

  test('FLAC', () {
    List<int> c(String s) => [..._le(utf8.encode(s).length), ...utf8.encode(s)];
    final v = [...c('libFLAC'), ..._le(3), ...c('TITLE=Uno'), ...c('artist=Dos'), ...c('ALBUM=Trés')];
    final img = [..._be(3), ..._be(9), ...ascii.encode('image/png'), ..._be(0), ...List.filled(16, 0), ..._be(2), 5, 6];
    final e = EtiquetasAudio.leer(Uint8List.fromList([...ascii.encode('fLaC'), 4, ..._be(v.length, 3), ...v,
      0x86, ..._be(img.length, 3), ...img]));
    expect((e.titulo, e.artista, e.album), ('Uno', 'Dos', 'Trés'));
    expect(e.portada, [5, 6]);
  });

  test('M4A', () {
    List<int> dato(String n, List<int> c) => _atomo(n, _atomo('data', [..._be(1), ..._be(0), ...c]));
    final ilst = _atomo('ilst', [
      ...dato('©nam', utf8.encode('Así')), ...dato('©ART', utf8.encode('Él')),
      ...dato('©alb', utf8.encode('Disco')), ...dato('covr', [1, 2, 3]),
    ]);
    final e = EtiquetasAudio.leer(Uint8List.fromList([
      ..._atomo('ftyp', ascii.encode('M4A isom')),
      ..._atomo('moov', _atomo('udta', _atomo('meta', [0, 0, 0, 0, ...ilst]))),
    ]));
    expect((e.titulo, e.artista, e.album), ('Así', 'Él', 'Disco'));
    expect(e.portada, [1, 2, 3]);
  });

  test('lo roto o desconocido sale vacío, sin lanzar', () {
    expect(EtiquetasAudio.leer(Uint8List(0)).titulo, '');
    expect(EtiquetasAudio.leer(Uint8List.fromList(List.filled(200, 0xFF))).titulo, '');
    final m = _id3(3, _marco(3, 'TIT2', [1, ..._utf16('Hola')]));
    for (var i = 0; i < m.length; i++) {
      EtiquetasAudio.leer(m.sublist(0, i)); // cortado en cualquier punto
    }
  });
}
