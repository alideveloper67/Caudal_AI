import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/reproduccion/sin_internet.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  group('esFalloDeRed', () {
    test('lo que es de red', () {
      expect(esFalloDeRed(const SocketException('Failed host lookup: music.youtube.com')), isTrue);
      expect(esFalloDeRed(TimeoutException('x')), isTrue);
      expect(esFalloDeRed(Exception('Connection closed before full header was received')), isTrue);
      expect(esFalloDeRed(Exception('ClientException with SocketException: Network is unreachable')), isTrue);
      expect(esFalloDeRed(const SinConexion()), isTrue);
    });
    test('lo que no es de red', () {
      expect(esFalloDeRed(Exception('Video unavailable')), isFalse);
      expect(esFalloDeRed(Exception('ninguna pista de audio')), isFalse);
    });
  });

  group('EstadoInternet', () {
    test('sin red del sistema: sin internet', () {
      final e = EstadoInternet(sinRed: () => true);
      expect(e.sinInternet, isTrue);
      e.cerrar();
    });
    test('un fallo de red vale un rato; un éxito lo borra', () {
      var t = DateTime(2026, 11, 21, 12);
      final e = EstadoInternet(sinRed: () => false, ahora: () => t);
      expect(e.sinInternet, isFalse);
      e.fallo();
      expect(e.sinInternet, isTrue);
      t = t.add(const Duration(minutes: 1));
      expect(e.sinInternet, isTrue);
      e.exito();
      expect(e.sinInternet, isFalse);
      e.fallo();
      t = t.add(const Duration(minutes: 3));
      expect(e.sinInternet, isFalse, reason: 'pasada la vigencia se vuelve a probar internet');
      e.cerrar();
    });
  });

  group('Nube.sesionInvalida (lo único que cierra la sesión)', () {
    test('sesión caducada o borrada', () {
      expect(Nube.sesionInvalida(400,
          '{"error":"invalid_grant","error_description":"Invalid Refresh Token: Refresh Token Not Found"}'), isTrue);
      expect(Nube.sesionInvalida(400, '{"code":"refresh_token_not_found"}'), isTrue);
      expect(Nube.sesionInvalida(403, '{"error_code":"session_not_found"}'), isTrue);
    });
    test('Supabase caído, demasiadas peticiones o un portal wifi: NO', () {
      expect(Nube.sesionInvalida(503, '{"message":"Service Unavailable"}'), isFalse);
      expect(Nube.sesionInvalida(502, '<html>Bad gateway</html>'), isFalse);
      expect(Nube.sesionInvalida(429, '{"message":"rate limit"}'), isFalse);
      expect(Nube.sesionInvalida(302, '<html>Inicia sesión en el wifi del hotel</html>'), isFalse);
      expect(Nube.sesionInvalida(400, '{"message":"algo raro"}'), isFalse);
    });
  });

  group('Cuentas.recordada sin internet', () {
    final guardada = jsonEncode({'id': 'u1', 'usuario': 'ana', 'nombre': 'Ana', 'refresh': 'r1'});

    setUp(() {
      SharedPreferences.setMockInitialValues({'cuenta.sesion': guardada});
    });

    Future<Cuenta?> recordada({required bool sinRed, required Future<Sesion> Function(String) renovar,
        Duration espera = const Duration(seconds: 6)}) =>
        Cuentas.recordada(sinRed: () async => sinRed, renovar: renovar, espera: espera);

    test('sin ninguna red entra al momento, sin preguntar a la nube', () async {
      var pregunto = false;
      final reloj = Stopwatch()..start();
      final c = await recordada(sinRed: true, renovar: (_) async {
        pregunto = true;
        throw const SinConexion();
      });
      expect(reloj.elapsedMilliseconds, lessThan(1000));
      expect(pregunto, isFalse);
      expect(c, isNotNull);
      expect(c!.sinConexion, isTrue);
      expect(c.id, 'u1');
      expect(c.usuario, 'ana');
    });

    test('red que no responde: como mucho la espera, y entra sin conexión', () async {
      final reloj = Stopwatch()..start();
      final c = await recordada(sinRed: false, espera: const Duration(milliseconds: 300),
          renovar: (_) => Completer<Sesion>().future);
      expect(reloj.elapsedMilliseconds, lessThan(2000));
      expect(c!.sinConexion, isTrue);
    });

    test('Supabase responde un error que no es de sesión: NO cierra la sesión', () async {
      final c = await recordada(sinRed: false, renovar: (_) async => throw const SinConexion());
      expect(c!.sinConexion, isTrue);
      final p = await SharedPreferences.getInstance();
      expect(p.getString('cuenta.sesion'), isNotNull, reason: 'la sesión guardada sigue ahí');
    });

    test('la nube dice que la sesión ya no vale: se olvida', () async {
      final c = await recordada(sinRed: false,
          renovar: (_) async => throw const ErrorNube('La sesión guardada caducó.'));
      expect(c, isNull);
      final p = await SharedPreferences.getInstance();
      expect(p.getString('cuenta.sesion'), isNull);
    });
  });
}
