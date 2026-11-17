// Pruebas de los frenos de rendimiento del teléfono: la posición del
// reproductor, la notificación de música, los sondeos pausables, el
// historial compartido y el gusto con saltos en memoria.

import 'dart:convert';
import 'dart:io';

import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/json_aparte.dart';
import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/nucleo/recomendador.dart';
import 'package:caudal/nucleo/vida_app.dart';
import 'package:caudal/reproduccion/frenos.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

Duration ms(int n) => Duration(milliseconds: n);

void main() {
  group('freno de la posición', () {
    test('a la vista: solo cada ~200 ms, y los saltos pasan siempre', () {
      expect(publicarPosicion(ms(1050), ms(1000)), isFalse);
      expect(publicarPosicion(ms(1199), ms(1000)), isFalse);
      expect(publicarPosicion(ms(1200), ms(1000)), isTrue);
      expect(publicarPosicion(ms(90000), ms(1000)), isTrue, reason: 'buscar adelante');
      expect(publicarPosicion(ms(0), ms(60000)), isTrue, reason: 'otra canción o buscar atrás');
      expect(publicarPosicion(ms(950), ms(1000)), isFalse, reason: 'un temblor hacia atrás no repinta');
    });

    test('en segundo plano: una vez por segundo', () {
      expect(publicarPosicion(ms(1500), ms(1000), fondo: true), isFalse);
      expect(publicarPosicion(ms(2000), ms(1000), fondo: true), isTrue);
    });

    test('con avisos de mpv cada 20 ms, la barra se entera ~5 veces por segundo', () {
      var publicada = Duration.zero;
      var avisos = 0;
      for (var t = 0; t <= 10000; t += 20) {
        if (publicarPosicion(ms(t), publicada)) {
          publicada = ms(t);
          avisos++;
        }
      }
      expect(avisos, inInclusiveRange(48, 52), reason: '10 s a ~5 avisos por segundo (antes 500)');
      expect((ms(10000) - publicada).inMilliseconds, lessThan(200), reason: 'nunca se queda atrás un paso entero');
    });
  });

  group('notificación de música solo con cambios', () {
    test('sonando sin saltos: no se vuelve a publicar cada segundo', () {
      final f = FrenoNotificacion();
      final t0 = DateTime(2026, 1, 1, 12);
      expect(f.deja(firma: 'sonando|1', posicion: ms(0), sonando: true, velocidad: 1, ahora: t0), isTrue);
      var veces = 0;
      for (var s = 1; s <= 60; s++) {
        if (f.deja(firma: 'sonando|1', posicion: Duration(seconds: s), sonando: true, velocidad: 1,
            ahora: t0.add(Duration(seconds: s)))) {
          veces++;
        }
      }
      expect(veces, 0, reason: 'el sistema avanza la barra solo');
    });

    test('se publica al cambiar el estado, la velocidad o la canción', () {
      final f = FrenoNotificacion();
      final t0 = DateTime(2026, 1, 1, 12);
      f.deja(firma: 'sonando|1|a', posicion: ms(0), sonando: true, velocidad: 1, ahora: t0);
      expect(f.deja(firma: 'pausa|1|a', posicion: ms(3000), sonando: false, velocidad: 1, ahora: t0.add(ms(3000))),
          isTrue);
      expect(f.deja(firma: 'pausa|1|a', posicion: ms(3000), sonando: false, velocidad: 1, ahora: t0.add(ms(9000))),
          isFalse, reason: 'en pausa la posición no corre');
      expect(f.deja(firma: 'sonando|1.5|a', posicion: ms(3000), sonando: true, velocidad: 1.5, ahora: t0.add(ms(9000))),
          isTrue);
      expect(f.deja(firma: 'sonando|1.5|b', posicion: ms(0), sonando: true, velocidad: 1.5, ahora: t0.add(ms(9100))),
          isTrue);
    });

    test('un salto de más de 1,5 s respecto a lo esperado se publica (con la velocidad)', () {
      final f = FrenoNotificacion();
      final t0 = DateTime(2026, 1, 1, 12);
      f.deja(firma: 'x', posicion: ms(10000), sonando: true, velocidad: 2, ahora: t0);
      // a velocidad 2, 4 s después lo esperado son 18 s
      expect(f.deja(firma: 'x', posicion: ms(18500), sonando: true, velocidad: 2, ahora: t0.add(ms(4000))), isFalse);
      expect(f.deja(firma: 'x', posicion: ms(40000), sonando: true, velocidad: 2, ahora: t0.add(ms(4000))), isTrue,
          reason: 'buscó adelante');
      expect(f.deja(firma: 'x', posicion: ms(5000), sonando: true, velocidad: 2, ahora: t0.add(ms(4100))), isTrue,
          reason: 'buscó atrás');
    });

    test('reiniciar obliga a publicar la próxima vez', () {
      final f = FrenoNotificacion();
      final t0 = DateTime(2026);
      f.deja(firma: 'x', posicion: ms(0), sonando: false, velocidad: 1, ahora: t0);
      f.reiniciar();
      expect(f.deja(firma: 'x', posicion: ms(0), sonando: false, velocidad: 1, ahora: t0), isTrue);
    });
  });

  group('sondeos pausables', () {
    tearDown(() => VidaApp.primerPlano.value = true);

    testWidgets('se paran en segundo plano y al volver consultan en el acto', (t) async {
      var veces = 0;
      final s = Sondeo(const Duration(seconds: 3), () => veces++)..iniciar();
      await t.pump(const Duration(seconds: 9));
      expect(veces, 3);
      VidaApp.primerPlano.value = false; // pantalla apagada u otra app
      expect(s.corriendo, isFalse);
      await t.pump(const Duration(seconds: 60));
      expect(veces, 3, reason: 'en segundo plano no se consulta');
      VidaApp.primerPlano.value = true;
      expect(veces, 4, reason: 'al volver, una consulta inmediata');
      await t.pump(const Duration(seconds: 3));
      expect(veces, 5, reason: 'y sigue con su ritmo');
      s.detener();
      await t.pump(const Duration(seconds: 30));
      expect(veces, 5);
    });

    testWidgets('con la pantalla tapada por otra ruta tampoco consulta', (t) async {
      var veces = 0;
      final nav = GlobalKey<NavigatorState>();
      await t.pumpWidget(MaterialApp(navigatorKey: nav, home: _ConSondeo(alConsultar: () => veces++)));
      await t.pump(const Duration(seconds: 4));
      expect(veces, 2);
      nav.currentState!.push(MaterialPageRoute<void>(builder: (_) => const Scaffold(body: Text('otra'))));
      await t.pumpAndSettle();
      final antes = veces;
      await t.pump(const Duration(seconds: 20));
      expect(veces, antes, reason: 'tapada: sin consultas');
      nav.currentState!.pop();
      await t.pumpAndSettle();
      expect(veces, antes + 1, reason: 'al volver a verse, consulta en el acto');
      await t.pump(const Duration(seconds: 2));
      expect(veces, antes + 2);
    });

    testWidgets('en una pestaña oculta (TickerMode apagado) no consulta', (t) async {
      var veces = 0;
      final visible = ValueNotifier(true);
      await t.pumpWidget(MaterialApp(
        home: ValueListenableBuilder<bool>(
          valueListenable: visible,
          builder: (_, v, _) => TickerMode(enabled: v, child: _ConSondeo(alConsultar: () => veces++)),
        ),
      ));
      await t.pump(const Duration(seconds: 2));
      expect(veces, 1);
      visible.value = false;
      await t.pump();
      await t.pump(const Duration(seconds: 10));
      expect(veces, 1);
      visible.value = true;
      await t.pump();
      expect(veces, 2);
    });

    test('una consulta lenta no se apila con la siguiente', () async {
      var enCurso = 0, maximo = 0;
      final s = Sondeo(const Duration(milliseconds: 10), () async {
        enCurso++;
        maximo = enCurso > maximo ? enCurso : maximo;
        await Future<void>.delayed(const Duration(milliseconds: 60));
        enCurso--;
      })..iniciar();
      await Future<void>.delayed(const Duration(milliseconds: 200));
      s.detener();
      expect(maximo, 1);
    });
  });

  group('JSON grande aparte', () {
    test('decodifica igual, pequeño o grande', () async {
      expect(await jsonDecodeAparte('{"a":[1,2]}'), {'a': [1, 2]});
      final grande = '[${List.filled(20000, '{"titulo":"canción","n":1}').join(',')}]';
      expect(grande.length, greaterThan(umbralJsonAparte));
      final d = await jsonDecodeAparte(grande) as List;
      expect(d.length, 20000);
      expect(d.first, {'titulo': 'canción', 'n': 1});
      final b = await jsonDecodeBytesAparte(utf8.encode(grande)) as List;
      expect(b.length, 20000);
    });
  });

  group('historial compartido', () {
    late Directory tmp;
    setUpAll(() {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    });
    setUp(() async {
      tmp = await Directory.systemTemp.createTemp('historial_');
      Historial.olvidar();
    });
    tearDown(() async {
      Historial.olvidar();
      try {
        await tmp.delete(recursive: true);
      } catch (_) {}
    });

    /// Escuchas de golpe, en una sola transaccion (escribir fila a fila es lento en disco).
    Future<void> escuchar(Coleccion c, List<(String, DateTime)> escuchas) async {
      final b = c.db.batch();
      for (final (clave, fecha) in escuchas) {
        b.insert('pistas', {'clave': clave, 'datos': jsonEncode({'clave': clave, 'video_id': clave.substring(3),
          'titulo': clave, 'artistas': [{'id': 'A', 'nombre': 'A'}]}), 'actualizada': 0},
            conflictAlgorithm: ConflictAlgorithm.replace);
        b.insert('reproducciones', {'clave': clave, 'fecha': fecha.millisecondsSinceEpoch / 1000.0,
          'contexto': '{"tipo":"album","id":"x"}'});
      }
      await b.commit(noResult: true);
    }

    test('una lectura amplia sirve a las más cortas, igual que leerlas aparte', () async {
      final c = await Coleccion.abrirEn('${tmp.path}/h.db');
      final hoy = DateTime.now();
      await escuchar(c, [for (var i = 0; i < 40; i++) ('yt:v$i', hoy.subtract(Duration(days: i * 10)))]);
      final amplia = await Historial.leer(c, desde: hoy.subtract(const Duration(days: 380)), limite: 40000);
      expect(amplia.length, 39, reason: 'de 0 a 380 días');
      final corta = await Historial.leer(c, desde: hoy.subtract(const Duration(days: 95)), limite: 5);
      Historial.olvidar();
      final directa = await Historial.leer(c, desde: hoy.subtract(const Duration(days: 95)), limite: 5);
      expect([for (final e in corta) e.clave], [for (final e in directa) e.clave]);
      expect(corta.length, 5);
      expect(corta.last.clave, 'yt:v0', reason: 'en orden cronológico, la más reciente al final');
      expect(corta.first.contexto, {'tipo': 'album', 'id': 'x'});
      await c.cerrar();
    });

    test('una escucha nueva invalida la lectura compartida', () async {
      final c = await Coleccion.abrirEn('${tmp.path}/h2.db');
      final hoy = DateTime.now();
      await escuchar(c, [('yt:a', hoy.subtract(const Duration(hours: 2)))]);
      expect((await Historial.leer(c)).length, 1);
      await escuchar(c, [('yt:b', hoy.subtract(const Duration(hours: 1)))]);
      expect((await Historial.leer(c)).map((e) => e.clave), ['yt:a', 'yt:b']);
      await c.cerrar();
    });

    test('la copia que se entrega se puede cambiar sin tocar la compartida', () async {
      final c = await Coleccion.abrirEn('${tmp.path}/h3.db');
      await escuchar(c, [('yt:a', DateTime.now().subtract(const Duration(hours: 1)))]);
      final a = await Historial.leer(c);
      a.clear();
      expect((await Historial.leer(c)).length, 1);
      await c.cerrar();
    });

    test('decodificar (lo que corre en otro isolate) arma las escuchas y omite las rotas', () {
      final e = Historial.decodificar((
        claves: ['yt:a', 'yt:roto', 'local:1', 'yt:a'],
        fechas: [1000.0, 1001.0, 1002.0, 1003.0],
        contextos: ['', '', '{"tipo":"lista"}', 'no es json'],
        pistas: {'yt:a': '{"clave":"yt:a","titulo":"A"}', 'yt:roto': '{roto'},
        locales: {'local:1': {'clave': 'local:1', 'titulo': 'L'}},
      ));
      expect(e.map((x) => x.clave), ['yt:a', 'local:1', 'yt:a']);
      expect(identical(e[0].pista, e[2].pista), isTrue, reason: 'cada pista se decodifica una vez');
      expect(e[1].contexto, {'tipo': 'lista'});
      expect(e[2].contexto, isNull);
      expect(e[0].fecha, DateTime.fromMillisecondsSinceEpoch(1000000));
    });
  });

  test('el gusto aprende un salto en memoria, igual que en la base', () {
    final g = Gusto(saltos: const {'v1': 1}, saltosArtista: const {}, saltadasHoy: const {});
    final p = {'video_id': 'v1', 'artistas': [{'id': 'X', 'nombre': 'Equis'}]};
    final g2 = g.conSalto(p);
    expect(g2.saltos['v1'], 2);
    expect(g2.saltosArtista['id:X'], 1);
    expect(g2.saltadasHoy, contains('v1'));
    expect(g2.descartada(p), isTrue, reason: 'saltada dos veces: fuera de la radio');
    expect(g.saltos['v1'], 1, reason: 'el original no cambia');
    expect(identical(g.conSalto({'titulo': 'sin id'}), g), isTrue);
  });
}

class _ConSondeo extends StatefulWidget {
  const _ConSondeo({required this.alConsultar});
  final VoidCallback alConsultar;

  @override
  State<_ConSondeo> createState() => _ConSondeoState();
}

class _ConSondeoState extends State<_ConSondeo> {
  late final Sondeo _s = Sondeo(const Duration(seconds: 2), () => widget.alConsultar());

  @override
  void initState() {
    super.initState();
    _s.iniciar();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _s.seguirPantalla(context);
  }

  @override
  void dispose() {
    _s.detener();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => const Scaffold(body: Text('con sondeo'));
}
