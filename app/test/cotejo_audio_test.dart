// Poner la letra a tiempo comparando el sonido del video con el de la canción oficial.

import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:caudal/nucleo/cotejo_audio.dart';
import 'package:caudal/nucleo/elegir_letra.dart';
import 'package:caudal/nucleo/letras_cache.dart';
import 'package:flutter_test/flutter_test.dart';

const hz = CotejoAudio.hz;

/// Una «canción» inventada: golpes y notas al azar, siempre los mismos para la misma semilla.
Float64List cancion(int semilla, int segundos) {
  final r = Random(semilla);
  final x = Float64List(segundos * hz);
  for (var t = 0.0; t < segundos - 1; t += 0.18 + r.nextDouble() * 0.35) {
    final f = 180 * pow(2, r.nextDouble() * 4), dur = 0.1 + r.nextDouble() * 0.3, fuerza = 0.2 + r.nextDouble() * 0.5;
    final i0 = (t * hz).round();
    for (var i = 0; i < dur * hz; i++) {
      x[i0 + i] += fuerza * exp(-i / (hz * dur * 0.4)) * sin(2 * pi * f * i / hz);
    }
  }
  return x;
}

Float64List ruido(double segundos, [double fuerza = 0.05]) {
  final r = Random(99);
  return Float64List.fromList([for (var i = 0; i < segundos * hz; i++) (r.nextDouble() - 0.5) * fuerza]);
}

Float64List junto(List<Float64List> p) => Float64List.fromList([for (final x in p) ...x]);

void main() {
  test('un video con intro: dice cuánto, al centésimo', () {
    final a = cancion(1, 100);
    final t = CotejoAudio.desfases(junto([ruido(4.22), a]), a)!;
    expect(t, hasLength(1));
    expect(t.single.$2, closeTo(4.22, 0.05));
  });

  test('un video que empieza más tarde que la canción', () {
    final a = cancion(2, 100);
    final t = CotejoAudio.desfases(Float64List.sublistView(a, (7.5 * hz).round()), a)!;
    expect(t.single.$2, closeTo(-7.5, 0.05));
  });

  test('con ruido encima y otro volumen sigue acertando', () {
    // como en la vida real, ninguna de las dos tiene silencio absoluto
    final n = ruido(100, 0.004), r = Random(3);
    final a = cancion(3, 100);
    final con = Float64List.fromList([for (var i = 0; i < a.length; i++) a[i] + n[i]]);
    final v = Float64List.fromList([for (var i = 0; i < a.length; i++) a[i] * 0.4 + (r.nextDouble() - 0.5) * 0.003]);
    expect(CotejoAudio.desfases(junto([ruido(2), v]), con)!.single.$2, closeTo(2, 0.05));
  });

  test('cortado por una escena: un corrimiento antes y otro después', () {
    final a = cancion(4, 140);
    final medio = 60 * hz;
    final v = junto([Float64List.sublistView(a, 0, medio), ruido(15), Float64List.sublistView(a, medio)]);
    final t = CotejoAudio.desfases(v, a)!;
    expect(t.first.$2, closeTo(0, 0.05));
    expect(t.last.$2, closeTo(15, 0.1));
    final l = CotejoAudio.colocar(const [(10000, 'antes'), (100000, 'después')], t);
    expect(l[0].$1, closeTo(10000, 60));
    expect(l[1].$1, closeTo(115000, 120));
  });

  test('otra canción: no se toca nada', () {
    expect(CotejoAudio.desfases(cancion(5, 100), cancion(6, 100)), isNull);
    expect(CotejoAudio.desfases(ruido(100), cancion(6, 100)), isNull);
    expect(CotejoAudio.desfases(Float64List(hz), cancion(6, 100)), isNull);
  });

  test('audio de verdad, igual que el escritorio (solo si están las muestras)', () {
    final carpeta = Platform.environment['CAUDAL_PCM'] ?? '';
    final lista = File('$carpeta/lista.txt');
    if (carpeta.isEmpty || !lista.existsSync()) return;
    Float64List leer(String f) {
      final b = File('$carpeta/$f.raw').readAsBytesSync();
      final d = ByteData.sublistView(b);
      return Float64List.fromList([for (var i = 0; i < b.length ~/ 2; i++) d.getInt16(i * 2, Endian.little) / 32768]);
    }

    var n = 0;
    for (final l in lista.readAsLinesSync()) {
      final p = l.split('|');
      final reloj = Stopwatch()..start();
      final t = CotejoAudio.desfases(leer(p[0]), leer(p[1]));
      // ignore: avoid_print
      print('${p[3]}: $t (escritorio ${p[2]}) ${reloj.elapsedMilliseconds} ms');
      expect(t, isNotNull, reason: p[3]);
      expect(t!.single.$2, closeTo(double.parse(p[2]), 0.045), reason: p[3]);
      n++;
    }
    expect(n, greaterThan(10));
  }, timeout: const Timeout(Duration(minutes: 5)));

  group('en la memoria de letras', () {
    Map<String, dynamic> letra() => {
          'lineas': [], 'texto': 'hola mundo', 'ref': 'oficial', 'ajustables': [[5000, 'hola mundo']],
        };

    test('la del video se pone a tiempo sola y queda guardada', () async {
      final c = LetrasCache.prueba();
      var veces = 0;
      c.cargador = (_) async => letra();
      c.cotejador = (p, ref) async {
        veces++;
        expect(ref, 'oficial');
        return [(0.0, 4.22)];
      };
      expect(lineasConTiempo(await c.obtener({'clave': 'k'})), isEmpty, reason: 'hasta medirla no se enseña corrida');
      await Future<void>.delayed(Duration.zero);
      expect(lineasConTiempo(await c.obtener({'clave': 'k'})), [(9220, 'hola mundo')]);
      await c.obtener({'clave': 'k'});
      expect(veces, 1);
      expect(c.midiendo('k'), isFalse);
    });

    test('si no es la misma grabación se queda en texto, y se puede ajustar a mano', () async {
      final c = LetrasCache.prueba();
      c.cargador = (_) async => letra();
      c.cotejador = (_, _) async => null;
      await c.obtener({'clave': 'k'});
      await Future<void>.delayed(Duration.zero);
      final l = (await c.obtener({'clave': 'k'}))!;
      expect(lineasConTiempo(l), isEmpty);
      expect(l['texto'], 'hola mundo');
      expect(lineasConTiempo({'lineas': l['ajustables']}), [(5000, 'hola mundo')]);
    });

    test('si la persona elige otra mientras se mide, gana la suya', () async {
      final c = LetrasCache.prueba();
      c.cargador = (_) async => letra();
      c.cotejador = (_, _) async {
        await Future<void>.delayed(const Duration(milliseconds: 30));
        return [(0.0, 4.0)];
      };
      await c.obtener({'clave': 'k'});
      c.elegir('k', {'lineas': [[1, 'la mía']], 'texto': 'la mía'});
      await Future<void>.delayed(const Duration(milliseconds: 80));
      expect(c.de('k')!['texto'], 'la mía');
    });

    test('un fallo al medir no rompe nada', () async {
      final c = LetrasCache.prueba();
      c.cargador = (_) async => letra();
      c.cotejador = (_, _) async => throw Exception('sin red');
      await c.obtener({'clave': 'k'});
      await Future<void>.delayed(Duration.zero);
      expect(c.midiendo('k'), isFalse);
      expect((await c.obtener({'clave': 'k'}))!['texto'], 'hola mundo');
    });
  });

  test('una ficha con los tiempos del disco se reconoce', () {
    const disco = [(1000, 'uno dos tres'), (2000, 'cuatro cinco seis'), (3000, 'siete ocho nueve'), (4000, 'diez once doce')];
    final video = [for (final (ms, t) in disco) (ms + 70000, t)];
    expect(ElegirLetra.corrimiento(disco, disco), 0);
    expect(ElegirLetra.corrimiento(video, disco), 70);
    expect(ElegirLetra.corrimiento(const [(1, 'otra cosa distinta')], disco), isNull);
  });

  test('«X Ft. Y - Canción»: se quita el invitado, no la canción', () {
    expect(ElegirLetra.tituloLimpio('Junior H Ft. Jose Mejia - Suena (Audio Oficial)'), 'Junior H - Suena');
    expect(ElegirLetra.tituloLimpio('Gasolina ft. Glory'), 'Gasolina');
  });
}
