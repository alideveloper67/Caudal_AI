import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:caudal/nucleo/avisos_dispositivo.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/plataforma.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Sesión que falla al llamar al servidor (sin tocar la red).
class _SesionRota extends Sesion {
  _SesionRota() : super('u', 'acceso', 'refresh', DateTime.now().add(const Duration(hours: 1)));

  @override
  Future<dynamic> pedir(String metodo, String ruta, {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    throw Exception('sin red');
  }
}

void main() {
  test('nuevoToken: 100 tokens distintos con formato UUID v4', () {
    final tokens = List.generate(100, (_) => AvisosDispositivo.nuevoToken());
    expect(tokens.toSet().length, 100);
    final formato = RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$');
    for (final t in tokens) {
      expect(t.length, 36);
      expect(t[14], '4');
      expect('89ab'.contains(t[19]), isTrue);
      expect(formato.hasMatch(t), isTrue, reason: t);
    }
  });

  test('registrar guarda el token y no rompe si la llamada falla', () async {
    SharedPreferences.setMockInitialValues({});
    Plataforma.forzada = TargetPlatform.android;
    addTearDown(() => Plataforma.forzada = null);

    await AvisosDispositivo.registrar(_SesionRota());

    final p = await SharedPreferences.getInstance();
    final guardado = p.getString('caudal_token_aviso');
    expect(guardado, isNotNull);
    expect(guardado!.length, 36);
  });

  test('registrar no hace nada fuera de Android', () async {
    SharedPreferences.setMockInitialValues({});
    Plataforma.forzada = TargetPlatform.iOS;
    addTearDown(() => Plataforma.forzada = null);

    await AvisosDispositivo.registrar(_SesionRota());

    final p = await SharedPreferences.getInstance();
    expect(p.getString('caudal_token_aviso'), isNull);
  });
}
