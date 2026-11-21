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
    expect(marca().readAsStringSync(), '$versionApp|inicio|0|0');
  });

  test('si la vez anterior no se dibujo: modo seguro y aviso con el paso', () async {
    marca().writeAsStringSync('$versionApp|reproductor|0');
    await Diagnostico.iniciarEn(dir);
    expect(Diagnostico.modoSeguro, isTrue);
    expect(Diagnostico.detalle, contains('reproductor'));
    Diagnostico.pintado();
    expect(marca().readAsStringSync(), '$versionApp|pintado|1|${Diagnostico.arranquesSeguros}');
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

  test('el modo seguro se acaba tras 3 arranques buenos (antes duraba toda la versión)', () async {
    marca().writeAsStringSync('$versionApp|reproductor|0');
    await Diagnostico.iniciarEn(dir); // la traba: modo seguro
    expect(Diagnostico.modoSeguro, isTrue);
    final seguros = <bool>[];
    for (var i = 0; i < Diagnostico.arranquesSeguros; i++) {
      Diagnostico.pintado();
      await Diagnostico.iniciarEn(dir);
      seguros.add(Diagnostico.modoSeguro);
    }
    // dos arranques más en modo seguro y el tercero ya normal
    expect(seguros, [true, true, false]);
    expect(Diagnostico.detalle, isNull);
  });

  test('una traba durante el modo seguro lo vuelve a empezar', () async {
    marca().writeAsStringSync('$versionApp|pintado|1|1');
    await Diagnostico.iniciarEn(dir);
    expect(Diagnostico.modoSeguro, isFalse); // le quedaba 1: este ya va normal
    marca().writeAsStringSync('$versionApp|notificacion|1|1');
    await Diagnostico.iniciarEn(dir);
    expect(Diagnostico.modoSeguro, isTrue);
    expect(Diagnostico.detalle, contains('notificacion'));
  });

  test('una version nueva vuelve al modo normal', () async {
    marca().writeAsStringSync('1.0.0|reproductor|1');
    await Diagnostico.iniciarEn(dir);
    expect(Diagnostico.modoSeguro, isFalse);
    expect(Diagnostico.detalle, isNull);
  });
}
