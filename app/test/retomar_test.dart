// «Recordar dónde quedaste» en canciones largas: qué se guarda, cuándo se
// olvida y el aviso «Seguimos donde lo dejaste» con su botón «Desde el inicio».
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/reproduccion/retomar.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _Repro extends ChangeNotifier implements Reproductor {
  @override
  Future<void> dispose() async => super.dispose();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Col extends ChangeNotifier implements Coleccion {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Str implements Streams {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Des extends ChangeNotifier implements GestorDescargas {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Future<Servicios> _servicios() async {
  SharedPreferences.setMockInitialValues({});
  return Servicios(
    cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
    ajustes: await Ajustes.cargar('prueba'),
    coleccion: _Col(), reproductor: _Repro(), streams: _Str(), descargas: _Des(),
    cerrarSesion: () async {},
  );
}

MemoriaRetomar _memoria(Map<String, dynamic> disco, {DateTime Function()? ahora, List<int>? escrituras}) =>
    MemoriaRetomar(
      leer: () async => disco.isEmpty ? null : Map<String, dynamic>.from(disco),
      escribir: (m) async {
        escrituras?.add(m.length);
        disco
          ..clear()
          ..addAll(m);
      },
      ahora: ahora,
    );

void main() {
  const set1h = Duration(hours: 1);

  group('que vale la pena recordar', () {
    test('solo canciones de 20 minutos o más', () {
      expect(pideRetomar(const Duration(minutes: 19, seconds: 59)), isFalse);
      expect(pideRetomar(const Duration(minutes: 20)), isTrue);
      expect(pideRetomar(set1h), isTrue);
      expect(pideRetomar(Duration.zero), isFalse);
    });

    test('no se recuerda el arranque ni el final', () {
      expect(puntoValido(const Duration(seconds: 5), set1h), isNull);
      expect(puntoValido(const Duration(minutes: 30), set1h), const Duration(minutes: 30));
      expect(puntoValido(const Duration(minutes: 59, seconds: 45), set1h), isNull);
      expect(puntoValido(const Duration(minutes: 30), const Duration(minutes: 10)), isNull);
    });

    test('se guarda cada 15 s', () {
      expect(cadaGuardarRetomar, const Duration(seconds: 15));
    });
  });

  group('memoria', () {
    test('guarda y devuelve por donde ibas', () async {
      final disco = <String, dynamic>{};
      final m = _memoria(disco);
      await m.guardar('yt:set', const Duration(minutes: 25, seconds: 10), set1h);
      expect(await m.punto('yt:set', set1h), const Duration(minutes: 25, seconds: 10));
      // otra instancia (otra vez que se abre la app) lo lee del disco
      final otra = _memoria(disco);
      expect(await otra.punto('yt:set', set1h), const Duration(minutes: 25, seconds: 10));
      expect(await otra.punto('yt:otra', set1h), isNull);
    });

    test('canciones cortas no ocupan sitio ni escriben', () async {
      final disco = <String, dynamic>{};
      final esc = <int>[];
      final m = _memoria(disco, escrituras: esc);
      await m.guardar('yt:corta', const Duration(minutes: 2), const Duration(minutes: 3));
      expect(esc, isEmpty);
      expect(disco, isEmpty);
    });

    test('la misma posicion no vuelve a escribir en el disco', () async {
      final esc = <int>[];
      final m = _memoria({}, escrituras: esc);
      await m.guardar('a', const Duration(minutes: 5), set1h);
      await m.guardar('a', const Duration(minutes: 5), set1h);
      expect(esc.length, 1);
      await m.guardar('a', const Duration(minutes: 6), set1h);
      expect(esc.length, 2);
    });

    test('al llegar al final se olvida', () async {
      final disco = <String, dynamic>{};
      final m = _memoria(disco);
      await m.guardar('a', const Duration(minutes: 30), set1h);
      expect(await m.punto('a', set1h), isNotNull);
      await m.guardar('a', const Duration(minutes: 59, seconds: 50), set1h);
      expect(await m.punto('a', set1h), isNull);
      expect(disco.containsKey('a'), isFalse);
    });

    test('«desde el inicio» lo olvida', () async {
      final m = _memoria({});
      await m.guardar('a', const Duration(minutes: 30), set1h);
      await m.olvidar('a');
      expect(await m.punto('a', set1h), isNull);
    });

    test('solo se recuerdan las 40 más recientes', () async {
      var reloj = DateTime(2026, 1, 1);
      final disco = <String, dynamic>{};
      final m = _memoria(disco, ahora: () => reloj = reloj.add(const Duration(seconds: 1)));
      for (var i = 0; i < maximoPuntosRetomar + 5; i++) {
        await m.guardar('c$i', const Duration(minutes: 10), set1h);
      }
      expect(disco.length, maximoPuntosRetomar);
      expect(disco.containsKey('c0'), isFalse);
      expect(disco.containsKey('c4'), isFalse);
      expect(disco.containsKey('c5'), isTrue);
      expect(disco.containsKey('c44'), isTrue);
    });

    test('un disco con basura no rompe nada', () async {
      final m = MemoriaRetomar(leer: () async => 'basura', escribir: (_) async {});
      expect(await m.punto('a', set1h), isNull);
      final m2 = MemoriaRetomar(leer: () async => throw StateError('sin bd'), escribir: (_) async {});
      expect(await m2.punto('a', set1h), isNull);
    });

    test('una entrada rota se ignora', () async {
      final m = _memoria({'a': 'roto', 'b': {'ms': 'x'}});
      expect(await m.punto('a', set1h), isNull);
      expect(await m.punto('b', set1h), isNull);
    });
  });

  group('aviso', () {
    testWidgets('«Seguimos donde lo dejaste» trae el boton «Desde el inicio»', (t) async {
      final s = await _servicios();
      var desdeInicio = 0;
      await t.pumpWidget(MaterialApp(
        scaffoldMessengerKey: s.mensajero,
        home: const Scaffold(body: SizedBox()),
      ));
      s.avisar(avisoRetomado, etiqueta: 'Desde el inicio', deshacer: () => desdeInicio++);
      await t.pump();
      await t.pump(const Duration(milliseconds: 400));
      expect(find.text('Seguimos donde lo dejaste'), findsOneWidget);
      expect(find.text('Desde el inicio'), findsOneWidget);
      await t.tap(find.text('Desde el inicio'));
      await t.pump();
      expect(desdeInicio, 1);
      await t.pump(const Duration(seconds: 6));
    });

    testWidgets('los demas avisos siguen diciendo «Deshacer»', (t) async {
      final s = await _servicios();
      await t.pumpWidget(MaterialApp(
        scaffoldMessengerKey: s.mensajero,
        home: const Scaffold(body: SizedBox()),
      ));
      s.avisar('Quitada de la cola', deshacer: () {});
      await t.pump();
      await t.pump(const Duration(milliseconds: 400));
      expect(find.text('Deshacer'), findsOneWidget);
      await t.pump(const Duration(seconds: 6));
    });
  });
}
