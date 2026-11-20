// Aviso de errores (nucleo/aviso_errores.dart): sin datos personales, casilla para apagarlo, cola
// sin red, freno contra inundaciones, ganchos de Flutter y de la zona sin quitar los que ya había,
// y el nombre de la pantalla abierta. Sin internet: el envío se sustituye.
import 'dart:async';

import 'package:caudal/nucleo/aviso_errores.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

StackTrace _pila() {
  try {
    throw StateError('x');
  } catch (_, p) {
    return p;
  }
}

class _Envio {
  _Envio([this.codigo = 201]);
  int codigo;
  final filas = <Map<String, dynamic>>[];
  Future<int> call(Map<String, dynamic> f) async {
    filas.add(f);
    return codigo;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late DateTime ahora;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    AvisoErrores.reiniciarParaPruebas();
    ahora = DateTime(2026, 11, 19, 12);
    AvisoErrores.reloj = () => ahora;
  });

  group('privacidad', () {
    test('limpiar quita rutas de usuario, correos, tokens, datos de enlaces y claves', () {
      final t = AvisoErrores.limpiar(r'C:\Users\María José\AppData\x.dart ana@usuarios.caudal.app '
          'https://sitio.com/ruta?token=abc#x eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.firma '
          '/home/pedro/caudal /Users/luisa/Library ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ab');
      for (final no in ['María', 'José', 'ana@', 'token=abc', 'eyJhbGci', 'pedro', 'luisa', 'ABCDEFGHIJ']) {
        expect(t.contains(no), isFalse, reason: no);
      }
      expect(t, contains(r'C:\Users\~\AppData'));
      expect(t, contains('https://sitio.com/ruta?…'));
    });

    test('el informe lleva lo justo y ninguna cuenta', () {
      final inf = AvisoErrores.informe(StateError('no se abrió /Users/ana/x.mp3'), _pila(),
          origen: 'zona', pantallaActual: 'LogrosPagina', version: '2.6.1', sistema: 'android 14', plataforma: 'android');
      expect(inf.keys.toSet(), {
        'plataforma', 'version', 'sistema', 'pantalla', 'origen', 'tipo', 'mensaje', 'traza', 'huella', 'veces',
        'primera_vez', 'ultima_vez',
      });
      expect(inf['tipo'], 'StateError');
      expect(inf['plataforma'], 'android');
      expect(inf['pantalla'], 'LogrosPagina');
      expect('${inf['mensaje']}'.contains('ana'), isFalse);
      expect('${inf['huella']}'.length, 20);
      expect(inf.containsKey('usuario'), isFalse);
    });

    test('la huella no cambia con los números de línea, sí con las funciones', () {
      const a = '#0      Foo.bar (package:caudal/x.dart:10:5)\n#1      main (package:caudal/y.dart:3:1)';
      const b = '#0      Foo.bar (package:caudal/x.dart:99:7)\n#1      main (package:caudal/y.dart:8:2)';
      const c = '#0      Foo.otra (package:caudal/x.dart:10:5)\n#1      main (package:caudal/y.dart:3:1)';
      expect(AvisoErrores.huella('E', a), AvisoErrores.huella('E', b));
      expect(AvisoErrores.huella('E', a), isNot(AvisoErrores.huella('E', c)));
      expect(AvisoErrores.huella('E', a), isNot(AvisoErrores.huella('F', a)));
    });
  });

  group('casilla y cola', () {
    test('apagado no guarda nada y vacía lo que esperaba', () async {
      await AvisoErrores.encolar(AvisoErrores.informe(StateError('a'), _pila()));
      expect(await AvisoErrores.cola(), hasLength(1));
      await AvisoErrores.ponerActivo(false);
      expect(await AvisoErrores.activo(), isFalse);
      expect(await AvisoErrores.cola(), isEmpty);
      expect(await AvisoErrores.encolar(AvisoErrores.informe(StateError('a'), _pila())), isFalse);
      await AvisoErrores.ponerActivo(true);
      expect(await AvisoErrores.activo(), isTrue);
    });

    test('los repetidos se juntan y la cola tiene tope', () async {
      final inf = AvisoErrores.informe(StateError('a'), _pila());
      for (var i = 0; i < 5; i++) {
        await AvisoErrores.encolar(inf);
      }
      final c = await AvisoErrores.cola();
      expect(c, hasLength(1));
      expect(c.first['veces'], 5);
      for (var i = 0; i < AvisoErrores.topeCola + 10; i++) {
        await AvisoErrores.encolar({...inf, 'huella': i.toRadixString(16).padLeft(20, '0'), 'ultima_vez': 1000 + i});
      }
      expect(await AvisoErrores.cola(), hasLength(AvisoErrores.topeCola));
    });

    test('sin red queda en cola y sale después', () async {
      await AvisoErrores.encolar(AvisoErrores.informe(StateError('a'), _pila()));
      AvisoErrores.enviarParaPruebas = _Envio(0).call;
      expect(await AvisoErrores.enviarPendientes(), 0);
      expect(await AvisoErrores.cola(), hasLength(1));
      final e = _Envio();
      AvisoErrores.enviarParaPruebas = e.call;
      expect(await AvisoErrores.enviarPendientes(), 1);
      expect(await AvisoErrores.cola(), isEmpty);
      expect(e.filas.single['primera_vez'], endsWith('Z'));
      expect(e.filas.single.containsKey('user_id'), isFalse);
    });

    test('el mismo error no sale dos veces en 6 horas', () async {
      final inf = AvisoErrores.informe(StateError('a'), _pila());
      AvisoErrores.enviarParaPruebas = _Envio().call;
      await AvisoErrores.encolar(inf);
      expect(await AvisoErrores.enviarPendientes(), 1);
      await AvisoErrores.encolar(inf);
      ahora = ahora.add(const Duration(minutes: 5));
      expect(await AvisoErrores.enviarPendientes(), 0);
      ahora = ahora.add(const Duration(hours: 6));
      expect(await AvisoErrores.enviarPendientes(), 1);
    });

    test('tope diario y pausa si el servidor aún no tiene la tabla', () async {
      final inf = AvisoErrores.informe(StateError('a'), _pila());
      for (var i = 0; i < AvisoErrores.topeDia + 5; i++) {
        await AvisoErrores.encolar({...inf, 'huella': i.toRadixString(16).padLeft(20, '0')});
      }
      AvisoErrores.enviarParaPruebas = _Envio().call;
      expect(await AvisoErrores.enviarPendientes(), AvisoErrores.topeDia);
      expect(await AvisoErrores.enviarPendientes(), 0);

      SharedPreferences.setMockInitialValues({});
      await AvisoErrores.encolar(inf);
      final e = _Envio(404);
      AvisoErrores.enviarParaPruebas = e.call;
      expect(await AvisoErrores.enviarPendientes(), 0);
      AvisoErrores.enviarParaPruebas = _Envio().call;
      expect(await AvisoErrores.enviarPendientes(), 0); // en pausa
      ahora = ahora.add(const Duration(hours: 25));
      expect(await AvisoErrores.enviarPendientes(), 1);
    });

    test('lo que el servidor rechaza no se reintenta', () async {
      await AvisoErrores.encolar(AvisoErrores.informe(StateError('a'), _pila()));
      AvisoErrores.enviarParaPruebas = _Envio(400).call;
      await AvisoErrores.enviarPendientes();
      expect(await AvisoErrores.cola(), isEmpty);
    });
  });

  group('ganchos', () {
    test('FlutterError y la plataforma se capturan sin quitar los ganchos de antes', () async {
      final previoFlutter = FlutterError.onError;
      final previoPlataforma = PlatformDispatcher.instance.onError;
      addTearDown(() {
        FlutterError.onError = previoFlutter;
        PlatformDispatcher.instance.onError = previoPlataforma;
      });
      final vistos = <String>[];
      FlutterError.onError = (d) => vistos.add('flutter');
      PlatformDispatcher.instance.onError = (e, p) {
        vistos.add('plataforma');
        return true;
      };
      AvisoErrores.instalar();
      AvisoErrores.pantalla = 'ReproductorPagina';
      FlutterError.onError!(FlutterErrorDetails(exception: ArgumentError('mal'), stack: _pila()));
      FlutterError.onError!(FlutterErrorDetails(exception: Exception('imagen'), silent: true));
      expect(PlatformDispatcher.instance.onError!(const FormatException('raro'), _pila()), isTrue);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(vistos, ['flutter', 'flutter', 'plataforma']);
      final c = {for (final x in await AvisoErrores.cola()) x['tipo']: x};
      expect(c.keys.toSet(), {'ArgumentError', 'FormatException'}); // el silencioso no cuenta
      expect(c['ArgumentError']!['origen'], 'flutter');
      expect(c['ArgumentError']!['pantalla'], 'ReproductorPagina');
      expect(c['FormatException']!['origen'], 'plataforma');
    });

    test('la zona atrapa los errores asíncronos que nadie atrapó', () async {
      final previoFlutter = FlutterError.onError;
      final previoPlataforma = PlatformDispatcher.instance.onError;
      addTearDown(() {
        FlutterError.onError = previoFlutter;
        PlatformDispatcher.instance.onError = previoPlataforma;
      });
      await AvisoErrores.enZona(() async {
        unawaited(Future<void>(() => throw const FileSystemExceptionFalsa()));
      });
      await Future<void>.delayed(const Duration(milliseconds: 50));
      final c = await AvisoErrores.cola();
      expect(c.single['tipo'], 'FileSystemExceptionFalsa');
      expect(c.single['origen'], 'zona');
    });

    test('tope por sesión', () async {
      for (var i = 0; i < AvisoErrores.topeSesion + 20; i++) {
        AvisoErrores.capturar(StateError('$i'), _pila());
      }
      await Future<void>.delayed(const Duration(milliseconds: 100));
      expect((await AvisoErrores.cola()).single['veces'], AvisoErrores.topeSesion);
    });
  });

  testWidgets('el observador sabe qué pantalla está arriba', (t) async {
    await t.pumpWidget(MaterialApp(navigatorObservers: [AvisoErrores.observador], home: const _InicioPagina()));
    expect(AvisoErrores.pantalla, '');
    t.state<NavigatorState>(find.byType(Navigator))
        .push(MaterialPageRoute<void>(builder: (_) => const _AjustesHoja()));
    await t.pumpAndSettle();
    final inf = AvisoErrores.informe(StateError('x'), null, pantallaActual: null);
    expect(inf['pantalla'], ''); // sin pantalla fijada a mano, el informe usa la del observador al capturar
    // la cola escribe en SharedPreferences (E/S real): dentro de runAsync, fuera de la zona falsa
    await t.runAsync(() async {
      AvisoErrores.capturar(StateError('x'), null);
      await Future<void>.delayed(const Duration(milliseconds: 50));
    });
    final c = await t.runAsync(AvisoErrores.cola);
    expect(c!.single['pantalla'], '_AjustesHoja');
    t.state<NavigatorState>(find.byType(Navigator)).pop();
    await t.pumpAndSettle();
    await t.runAsync(() async {
      AvisoErrores.capturar(ArgumentError('y'), null);
      await Future<void>.delayed(const Duration(milliseconds: 50));
    });
    final c2 = await t.runAsync(AvisoErrores.cola);
    expect({for (final x in c2!) x['tipo']: x['pantalla']}['ArgumentError'], '_InicioPagina');
  });
}

class FileSystemExceptionFalsa implements Exception {
  const FileSystemExceptionFalsa();
}

class _InicioPagina extends StatelessWidget {
  const _InicioPagina();
  @override
  Widget build(BuildContext context) => const Scaffold(body: Text('inicio'));
}

class _AjustesHoja extends StatelessWidget {
  const _AjustesHoja();
  @override
  Widget build(BuildContext context) => const Scaffold(body: Text('ajustes'));
}
