// Nivel, XP, misiones diarias y racha del Modo gamer: lógica pura.
import 'package:caudal/nucleo/gamer.dart';
import 'package:caudal/nucleo/gamer_xp.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('niveles', () {
    test('la curva es creciente y el inverso cuadra', () {
      var antes = -1;
      for (var n = 1; n <= nivelMaximo; n++) {
        final x = xpParaNivel(n);
        expect(x, greaterThan(antes));
        antes = x;
        expect(nivelDeXp(x), n, reason: 'nivel $n');
        if (n > 1) expect(nivelDeXp(x - 1), n - 1);
      }
      expect(nivelDeXp(0), 1);
      expect(nivelDeXp(-5), 1);
      expect(nivelDeXp(1 << 40), nivelMaximo);
    });

    test('misma fórmula que la PC: 25 · n · (n-1), cada nivel cuesta 50 más que el anterior', () {
      expect(xpParaNivel(1), 0);
      expect(xpParaNivel(2), 50);
      expect(xpParaNivel(3), 150);
      expect(xpParaNivel(4), 300);
      for (var n = 2; n < 40; n++) {
        final a = xpParaNivel(n + 1) - xpParaNivel(n);
        final b = xpParaNivel(n + 2) - xpParaNivel(n + 1);
        expect(b - a, 50);
      }
    });

    test('fracción dentro del nivel', () {
      expect(fraccionNivel(0), 0);
      expect(fraccionNivel(xpParaNivel(3)), 0);
      final medio = (xpParaNivel(3) + xpParaNivel(4)) ~/ 2;
      expect(fraccionNivel(medio), closeTo(0.5, 0.02));
      expect(fraccionNivel(1 << 40), 1);
    });
  });

  group('XP por escuchar', () {
    final t = DateTime(2026, 11, 19, 20, 0);

    test('1 XP por minuto y el resto de segundos se acumula', () {
      var p = const ProgresoGamer();
      p = p.registrar(t, segundos: 45).progreso;
      expect(p.xp, 0);
      p = p.registrar(t, segundos: 45).progreso;
      expect(p.xp, 1);
      expect(p.segPendientes, 30);
      p = p.registrar(t, segundos: 30).progreso;
      expect(p.xp, 2);
      expect(p.segPendientes, 0);
      expect(p.segTotales, 120);
      expect(p.minutosHoy, 2);
    });

    test('segundos negativos no restan', () {
      final p = const ProgresoGamer().registrar(t, segundos: -50).progreso;
      expect(p.xp, 0);
      expect(p.segTotales, 0);
    });

    test('canciones nuevas y artistas distintos, sin repetir', () {
      var p = const ProgresoGamer();
      p = p.registrar(t, cancion: 'a', artistas: ['Ana', 'Beto']).progreso;
      p = p.registrar(t, cancion: 'a', artistas: ['ana']).progreso; // la misma
      p = p.registrar(t, cancion: 'b', artistas: [' ANA ', 'Cleo']).progreso;
      expect(p.nuevasHoy, ['a', 'b']);
      expect(p.artistasHoy.length, 3);
    });

    test('una canción de ayer ya no es nueva hoy', () {
      var p = const ProgresoGamer().registrar(t, cancion: 'a').progreso;
      p = p.registrar(t.add(const Duration(days: 1)), cancion: 'a').progreso;
      expect(p.nuevasHoy, isEmpty);
      expect(p.vistas, ['a']);
    });

    test('subir de nivel se avisa una vez', () {
      final p = ProgresoGamer(xp: xpParaNivel(2) - 1);
      final r = p.registrar(t, segundos: 60);
      expect(r.subioNivel, isTrue);
      expect(r.nivelAntes, 1);
      expect(r.nivelAhora, 2);
      expect(r.progreso.registrar(t, segundos: 5).subioNivel, isFalse);
    });

    test('el historial de canciones tiene tope', () {
      var p = const ProgresoGamer();
      for (var i = 0; i < 600; i++) {
        p = p.registrar(t, cancion: 'c$i').progreso;
      }
      expect(p.vistas.length, lessThanOrEqualTo(400));
      expect(p.vistas.last, 'c599');
    });
  });

  group('misiones', () {
    test('siempre 3, deterministas por fecha y distintas entre días', () {
      final d = DateTime(2026, 11, 19);
      final a = misionesDelDia(d), b = misionesDelDia(DateTime(2026, 11, 19, 23, 59));
      expect(a.length, 3);
      expect({for (final m in a) m.tipo}.length, 3);
      expect([for (final m in a) m.id], [for (final m in b) m.id]);
      expect([for (final m in a) m.meta], [for (final m in b) m.meta]);
      final conjuntos = {
        for (var i = 0; i < 30; i++) [for (final m in misionesDelDia(d.add(Duration(days: i)))) m.meta].join(',')
      };
      expect(conjuntos.length, greaterThan(3));
      for (final m in a) {
        expect(m.meta, greaterThan(0));
        expect(m.xp, greaterThan(0));
        expect(m.titulo, isNotEmpty);
      }
    });

    test('se cumplen, cobran su XP una sola vez y se reinician al día siguiente', () {
      final t = DateTime(2026, 11, 19, 10);
      final minutos = misionesDelDia(t).firstWhere((m) => m.tipo == TipoMision.minutos);
      var r = const ProgresoGamer().registrar(t, segundos: minutos.meta * 60);
      expect(r.misiones.map((m) => m.id), contains(minutos.id));
      expect(r.xpGanado, minutos.meta + minutos.xp);
      expect(r.progreso.misionHecha(minutos), isTrue);
      final xp = r.progreso.xp;
      r = r.progreso.registrar(t, segundos: 60);
      expect(r.misiones.where((m) => m.id == minutos.id), isEmpty);
      expect(r.progreso.xp, xp + 1);
      final manana = t.add(const Duration(days: 1));
      final p2 = r.progreso.alDia(manana);
      expect(p2.segHoy, 0);
      expect(p2.completadas, isEmpty);
    });

    test('las tres juntas', () {
      final t = DateTime(2026, 11, 19, 10);
      final ms = misionesDelDia(t);
      var p = const ProgresoGamer();
      final nuevas = ms.firstWhere((m) => m.tipo == TipoMision.nuevas).meta;
      final arts = ms.firstWhere((m) => m.tipo == TipoMision.artistas).meta;
      final mins = ms.firstWhere((m) => m.tipo == TipoMision.minutos).meta;
      for (var i = 0; i < (nuevas > arts ? nuevas : arts); i++) {
        p = p.registrar(t, cancion: 'c$i', artistas: ['art$i']).progreso;
      }
      p = p.registrar(t, segundos: mins * 60).progreso;
      for (final m in ms) {
        expect(p.misionHecha(m), isTrue, reason: m.titulo);
      }
    });
  });

  group('racha', () {
    final d1 = DateTime(2026, 11, 17, 21);

    test('empieza al llevar un minuto y sube día a día', () {
      var p = const ProgresoGamer().registrar(d1, segundos: 30).progreso;
      expect(p.racha, 0);
      p = p.registrar(d1, segundos: 30).progreso;
      expect(p.racha, 1);
      p = p.registrar(d1, segundos: 600).progreso;
      expect(p.racha, 1, reason: 'el mismo día no suma');
      p = p.registrar(d1.add(const Duration(days: 1)), segundos: 60).progreso;
      expect(p.racha, 2);
      p = p.registrar(d1.add(const Duration(days: 2)), segundos: 60).progreso;
      expect(p.racha, 3);
      expect(p.mejorRacha, 3);
    });

    test('se pierde si falta un día, pero la mejor se recuerda', () {
      var p = const ProgresoGamer().registrar(d1, segundos: 60).progreso;
      p = p.registrar(d1.add(const Duration(days: 1)), segundos: 60).progreso;
      expect(p.racha, 2);
      final tarde = d1.add(const Duration(days: 4));
      expect(p.rachaVigente(d1.add(const Duration(days: 2))), 2, reason: 'ayer cuenta: aún puede seguirla hoy');
      expect(p.rachaVigente(tarde), 0);
      p = p.registrar(tarde, segundos: 60).progreso;
      expect(p.racha, 1);
      expect(p.mejorRacha, 2);
    });

    test('cruza fin de mes y de año', () {
      var p = const ProgresoGamer().registrar(DateTime(2026, 12, 31, 23), segundos: 60).progreso;
      p = p.registrar(DateTime(2027, 1, 1, 8), segundos: 60).progreso;
      expect(p.racha, 2);
    });
  });

  group('guardado', () {
    test('ida y vuelta', () {
      final t = DateTime(2026, 11, 19, 10);
      final p = const ProgresoGamer().registrar(t, segundos: 200, cancion: 'x', artistas: ['Ana']).progreso;
      final q = ProgresoGamer.deTexto(p.aTexto());
      expect(q.aTexto(), p.aTexto());
      expect(q.xp, p.xp);
      expect(q.nuevasHoy, ['x']);
    });

    test('texto vacío, roto o raro no falla', () {
      for (final s in [null, '', 'no json', '[1,2]', '{"xp":"mucho","v":5}', '{"xp":-9}']) {
        final p = ProgresoGamer.deTexto(s);
        expect(p.xp, greaterThanOrEqualTo(0));
        expect(p.nivel, 1);
      }
    });
  });

  group('datos del modo', () {
    test('perfiles: 10 bandas dentro de ±12 y distintos entre sí', () {
      expect(perfilesSonido.length, 4);
      for (final p in perfilesSonido) {
        expect(p.bandas.length, 10);
        expect(p.bandas.every((b) => b >= -12 && b <= 12), isTrue);
      }
      expect({for (final p in perfilesSonido) p.bandas.join(',')}.length, 4);
      // FPS realza medios-agudos (1k-8k) frente a los graves
      final fps = perfilSonidoPorId('fps')!.bandas;
      expect(fps[7], greaterThan(fps[0]));
      // Carreras: graves
      final c = perfilSonidoPorId('carreras')!.bandas;
      expect(c[0], greaterThan(c[9]));
      expect(perfilSonidoPorId('nada'), isNull);
    });

    test('5 situaciones, cada una con consultas', () {
      expect(Situacion.values.length, 5);
      for (final s in Situacion.values) {
        expect(s.consultas, isNotEmpty);
      }
    });

    test('pistasParaSituacion: radio, respaldo y vacío', () async {
      Map<String, dynamic> p(String id) => {'video_id': id, 'titulo': id};
      final r = await pistasParaSituacion(Situacion.lobby,
          buscar: (q) async => [p('a'), p('b')], radio: (v) async => [p('r1-$v'), p('r2')]);
      expect(r.first['video_id'], 'r1-a');
      final f = await pistasParaSituacion(Situacion.clutch,
          buscar: (q) async => [p('a'), p('b')], radio: (v) async => throw Exception('red'));
      expect(f.map((e) => e['video_id']), ['a', 'b']);
      expect(() => pistasParaSituacion(Situacion.victoria, buscar: (q) async => [], radio: (v) async => []),
          throwsA(anything));
    });
  });
}
