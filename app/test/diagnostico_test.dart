import 'dart:io';

import 'package:caudal/nucleo/diagnostico.dart';
import 'package:caudal/nucleo/version.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  late Directory dir;
  File marca() => File('${dir.path}/arranque.txt');

  setUp(() => dir = Directory.systemTemp.createTempSync('caudal_diag'));
  tearDown(() => dir.deleteSync(recursive: true));

  test('primer arranque: normal y sin aviso', () async {
    await Diagnostico.iniciarEn(dir);
    expect(Diagnostico.modoSeguro, isFalse);
    expect(Diagnostico.detalle, isNull);
    expect(marca().readAsStringSync(), '$versionApp|inicio|0');
  });

  test('si la vez anterior no se dibujo: modo seguro y aviso con el paso', () async {
    marca().writeAsStringSync('$versionApp|reproductor|0');
    await Diagnostico.iniciarEn(dir);
    expect(Diagnostico.modoSeguro, isTrue);
    expect(Diagnostico.detalle, contains('reproductor'));
    Diagnostico.pintado();
    expect(marca().readAsStringSync(), '$versionApp|pintado|1');
  });

  test('el modo seguro sigue tras un arranque bueno, sin repetir el aviso', () async {
    marca().writeAsStringSync('$versionApp|pintado|1');
    await Diagnostico.iniciarEn(dir);
    expect(Diagnostico.modoSeguro, isTrue);
    expect(Diagnostico.detalle, isNull);
  });

  test('cerrar la app en el aviso no cuenta como otra traba', () async {
    marca().writeAsStringSync('$versionApp|aviso|1');
    await Diagnostico.iniciarEn(dir);
    expect(Diagnostico.modoSeguro, isTrue);
    expect(Diagnostico.detalle, isNull);
  });

  test('una version nueva vuelve al modo normal', () async {
    marca().writeAsStringSync('1.0.0|reproductor|1');
    await Diagnostico.iniciarEn(dir);
    expect(Diagnostico.modoSeguro, isFalse);
    expect(Diagnostico.detalle, isNull);
  });
}
