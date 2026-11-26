import 'dart:async';
import 'dart:convert';

import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Que Caudal no pida iniciar sesión a cada rato: el token nuevo se guarda en el momento en que llega.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Map<String, Object> guardada(String refresh) => {
        'cuenta.sesion': jsonEncode({'id': 'u1', 'usuario': 'ana', 'nombre': 'Ana', 'refresh': refresh}),
      };

  Sesion nueva(String refresh) =>
      Sesion('u1', 'acceso-$refresh', refresh, DateTime.now().add(const Duration(hours: 1)));

  Future<String> refreshGuardado() async {
    final p = await SharedPreferences.getInstance();
    return '${(jsonDecode(p.getString('cuenta.sesion')!) as Map)['refresh']}';
  }

  test('al crear la cuenta queda enganchado el guardado del token', () async {
    SharedPreferences.setMockInitialValues(guardada('r1'));
    final s = nueva('r1');
    final c = Cuenta(id: 'u1', usuario: 'ana', nombre: 'Ana', sesion: s);
    s.refresh = 'r2';
    await s.alRenovar!();
    expect(await refreshGuardado(), 'r2');
    expect(c.sesion, same(s));
  });

  test('si no se quiso mantener la sesión, renovar no la guarda', () async {
    SharedPreferences.setMockInitialValues({});
    final s = nueva('r1');
    Cuenta(id: 'u1', usuario: 'ana', nombre: 'Ana', sesion: s);
    await s.alRenovar!();
    expect((await SharedPreferences.getInstance()).containsKey('cuenta.sesion'), isFalse);
  });

  test('una renovación que llega tarde también se guarda', () async {
    SharedPreferences.setMockInitialValues(guardada('r1'));
    final llega = Completer<Sesion>();
    final c = await Cuentas.recordada(
        espera: const Duration(milliseconds: 20), sinRed: () async => false, renovar: (_) => llega.future);
    expect(c, isNotNull);
    expect(c!.sinConexion, isTrue);
    llega.complete(nueva('r2'));
    await Future<void>.delayed(const Duration(milliseconds: 30));
    expect(c.sesion!.refresh, 'r2');
    expect(await refreshGuardado(), 'r2');
  });

  test('si la nube dice que ya no vale pero hay un token más nuevo guardado, se usa ese', () async {
    SharedPreferences.setMockInitialValues(guardada('r1'));
    var veces = 0;
    final c = await Cuentas.recordada(
        sinRed: () async => false,
        renovar: (r) async {
          veces++;
          if (r == 'r1') {
            final p = await SharedPreferences.getInstance();
            await p.setString('cuenta.sesion', guardada('r5')['cuenta.sesion']! as String);
            throw const ErrorNube('La sesión guardada caducó. Vuelve a iniciar sesión.');
          }
          return nueva('r6');
        });
    expect(veces, 2);
    expect(c!.sesion!.refresh, 'r6');
    expect(await refreshGuardado(), 'r6');
  });

  test('un fallo del servidor nunca cierra la sesión; una sesión inválida sí', () async {
    SharedPreferences.setMockInitialValues(guardada('r1'));
    var c = await Cuentas.recordada(sinRed: () async => false, renovar: (_) async => throw const SinConexion());
    expect(c, isNotNull);
    expect(await refreshGuardado(), 'r1');
    c = await Cuentas.recordada(
        sinRed: () async => false,
        renovar: (_) async => throw const ErrorNube('La sesión guardada caducó. Vuelve a iniciar sesión.'));
    expect(c, isNull);
    expect((await SharedPreferences.getInstance()).containsKey('cuenta.sesion'), isFalse);
  });
}
