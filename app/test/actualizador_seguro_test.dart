import 'dart:io';

import 'package:crypto/crypto.dart' show sha256;
import 'package:flutter_test/flutter_test.dart';

import 'package:caudal/nucleo/version.dart';

Map _rel(String v, {bool draft = false}) => {
      'tag_name': 'movil-v$v',
      'draft': draft,
      'published_at': '2026-11-1${v.length % 9}T10:00:00Z',
      'assets': [
        {'name': 'Caudal-$v-arm64-v8a.apk', 'browser_download_url': 'https://x/$v-arm64.apk'},
        {'name': 'Caudal-$v-armeabi-v7a.apk', 'browser_download_url': 'https://x/$v-v7a.apk'},
      ],
    };

void main() {
  test('huellaDe solo acepta sha256 bien formado', () {
    final h = 'a' * 64;
    expect(huellaDe('sha256:$h'), h);
    expect(huellaDe('SHA256:${h.toUpperCase()}'), h);
    expect(huellaDe('sha256:abc'), '');
    expect(huellaDe(null), '');
    expect(huellaDe('md5:$h'), '');
  });

  test('apkCompleto exige tamaño, cabecera PK y huella', () async {
    final dir = await Directory.systemTemp.createTemp('apk');
    final f = File('${dir.path}/a.apk');
    final bytes = [0x50, 0x4B, ...List.filled(4000, 7)];
    await f.writeAsBytes(bytes);
    final buena = sha256.convert(bytes).toString();
    expect(await apkCompleto(f, bytes.length, huella: buena), isTrue);
    expect(await apkCompleto(f, bytes.length), isTrue);
    expect(await apkCompleto(f, bytes.length + 1, huella: buena), isFalse);
    expect(await apkCompleto(f, bytes.length, huella: 'b' * 64), isFalse);
    // mismo tamaño pero un byte cambiado: la huella lo caza
    final mala = [...bytes]..[100] = 9;
    await f.writeAsBytes(mala);
    expect(await apkCompleto(f, mala.length, huella: buena), isFalse);
    await f.writeAsBytes([0x00, 0x00, ...List.filled(4000, 7)]);
    expect(await apkCompleto(f, 4002), isFalse);
    await dir.delete(recursive: true);
  });

  test('anterioresDe da solo las más viejas, de la más nueva a la más vieja, con su APK', () {
    final l = anterioresDe([_rel('2.7.2'), _rel('2.6.1'), _rel('2.7.1'), _rel('2.7.0', draft: true),
      _rel('2.10.0'), {'tag_name': 'escritorio-v2.5.0', 'assets': []}],
        abi: 'arm64', actual: '2.7.2');
    expect(l.map((v) => v.version).toList(), ['2.7.1', '2.6.1']);
    expect(l.first.apk, 'https://x/2.7.1-arm64.apk');
    final v7 = anterioresDe([_rel('2.6.1')], abi: 'arm', actual: '2.7.2');
    expect(v7.single.apk, 'https://x/2.6.1-v7a.apk');
  });
}
