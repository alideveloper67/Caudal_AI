// Mezclador avanzado: tempo por analisis de audio sintetico, orden como DJ,
// perfiles, alineacion al compas, curvas, filtros y compatibilidad con lo guardado.
import 'dart:math';

import 'package:caudal/nucleo/mezcla_dj.dart';
import 'package:caudal/nucleo/ritmo.dart';
import 'package:flutter_test/flutter_test.dart';

const hz = 11025;

/// Un bombo en cada tiempo (seno grave que se apaga) a [bpm], empezando en [desfase] s,
/// con un hi-hat suave a contratiempo si [contratiempo]. Dura [segundos] s.
List<double> pistaSintetica(double bpm, {double desfase = 0.13, int segundos = 40, bool contratiempo = true,
    double ruido = 0}) {
  final n = hz * segundos;
  final x = List<double>.filled(n, 0);
  final rnd = Random(7);
  final periodo = 60 / bpm;
  void golpe(double t, double fuerza, double f) {
    final i0 = (t * hz).round();
    for (var k = 0; k < hz * 0.12 && i0 + k < n; k++) {
      final env = exp(-k / (hz * 0.03));
      x[i0 + k] += fuerza * env * sin(2 * pi * f * k / hz);
    }
  }

  for (var t = desfase; t < segundos - 0.2; t += periodo) {
    golpe(t, 0.9, 70);
    if (contratiempo) golpe(t + periodo / 2, 0.25, 3000);
  }
  if (ruido > 0) {
    for (var i = 0; i < n; i++) {
      x[i] += (rnd.nextDouble() - 0.5) * ruido;
    }
  }
  return x;
}

Map<String, dynamic> p(String id, {int dur = 200}) =>
    {'tipo': 'pista', 'clave': 'yt:$id', 'video_id': id, 'titulo': 'T$id', 'artista': 'A', 'duracion': dur};

AnalisisRitmo r(double bpm, double energia) => AnalisisRitmo(bpm: bpm, energia: energia, primerTiempo: 0.1);

void main() {
  group('detectar el tempo en audio sintetico', () {
    for (final bpm in [80.0, 90.0, 100.0, 120.0, 128.0, 140.0, 150.0]) {
      test('$bpm BPM', () {
        final a = estimarRitmo(pistaSintetica(bpm), hz);
        expect(a.valido, isTrue);
        expect(a.bpm, closeTo(bpm, 1.5), reason: 'salio ${a.bpm}');
        expect(a.barras.length, 48);
        expect(a.barras.every((b) => b >= 0 && b <= 1), isTrue);
        expect(a.duracionAnalizada, closeTo(40, 0.01));
      });
    }

    test('sin hi-hat y con ruido de fondo sigue acertando', () {
      final a = estimarRitmo(pistaSintetica(124, contratiempo: false, ruido: 0.15), hz);
      expect(a.bpm, closeTo(124, 2));
    });

    test('encuentra donde cae el pulso (el desfase)', () {
      const bpm = 120.0;
      for (final desfase in [0.0, 0.13, 0.3]) {
        final a = estimarRitmo(pistaSintetica(bpm, desfase: desfase), hz);
        final periodo = 60 / bpm;
        // distancia al golpe mas cercano, en segundos
        var d = ((a.primerTiempo - desfase) % periodo + periodo) % periodo;
        d = min(d, periodo - d);
        expect(d, lessThan(0.04), reason: 'desfase $desfase -> ${a.primerTiempo}');
      }
    });

    test('con el tramo analizado desde otro punto, el primer tiempo se mide en la cancion', () {
      final a = estimarRitmo(pistaSintetica(120, desfase: 0.1), hz, inicio: 40);
      // el pulso cae a 0,5 s * k: 40 + fase sigue siendo multiplo de 0,5 mas el desfase
      final f = (a.primerTiempo - 0.1) % 0.5;
      expect(min(f, 0.5 - f), lessThan(0.04));
    });

    test('el silencio y lo muy corto no inventan un tempo', () {
      expect(estimarRitmo(List.filled(hz * 20, 0.0), hz).bpm, 0);
      expect(estimarRitmo(List.filled(hz * 2, 0.5), hz).bpm, 0);
      expect(estimarRitmo(const [], hz).valido, isFalse);
    });

    test('el ruido sin pulso es mucho menos fiable que un ritmo claro', () {
      final rnd = Random(3);
      final ruido = [for (var i = 0; i < hz * 30; i++) (rnd.nextDouble() - 0.5) * 0.6];
      final claro = estimarRitmo(pistaSintetica(120), hz).confianza;
      expect(estimarRitmo(ruido, hz).confianza, lessThan(claro * 0.6));
    });

    test('guardado y vuelto a leer', () {
      final a = estimarRitmo(pistaSintetica(110), hz);
      final b = AnalisisRitmo.deJson(a.aJson())!;
      expect(b.bpm, closeTo(a.bpm, 0.01));
      expect(b.barras.length, 48);
      expect(b.manual, isFalse);
      expect(AnalisisRitmo.deJson('basura'), isNull);
      expect(a.copiaCon(bpm: 100, manual: true).manual, isTrue);
    });
  });

  group('tempo a mano', () {
    test('de unos toques', () {
      final toques = [for (var i = 0; i < 8; i++) 1000 + i * 500]; // 120 BPM
      expect(bpmDeToques(toques), closeTo(120, 0.5));
      // un toque flojo o tarde no estropea la mediana
      expect(bpmDeToques([0, 500, 1000, 1700, 2000, 2500, 3000]), closeTo(120, 1));
    });

    test('con pocos toques o muy raros, nada', () {
      expect(bpmDeToques([0, 500, 1000]), isNull);
      expect(bpmDeToques([0, 5000, 10000, 15000]), isNull);
    });

    test('plegar al rango normal', () {
      expect(plegarBpm(60), 120);
      expect(plegarBpm(240), 120);
      expect(plegarBpm(100), 100);
      expect(plegarBpm(0), 0);
    });
  });

  group('encajar tempos', () {
    test('razon: hasta 8 % se estira, mas no', () {
      expect(razonDeTempo(120, 116), closeTo(120 / 116, 1e-9));
      expect(razonDeTempo(120, 128), closeTo(120 / 128, 1e-9));
      expect(razonDeTempo(120, 140), 1);
      expect(razonDeTempo(0, 120), 1);
    });

    test('el doble y la mitad cuentan como iguales', () {
      expect(razonDeTempo(128, 64), closeTo(1, 1e-9));
      expect(razonDeTempo(130, 64), closeTo(130 / 128, 1e-9));
      expect(encajeDe(128, 64), Encaje.bueno);
    });

    test('bueno, regular, choca, desconocido', () {
      expect(encajeDe(120, 123), Encaje.bueno);
      expect(encajeDe(120, 130), Encaje.regular);
      expect(encajeDe(120, 150), Encaje.choca);
      expect(encajeDe(null, 120), Encaje.desconocido);
      expect(encajeDe(0, 120), Encaje.desconocido);
    });

    test('alinear al compas', () {
      // 120 BPM: un compas de 4 tiempos dura 2 s; el tiempo fuerte cae en 0,5
      expect(alinearAlCompas(10.1, 120, 0.5), closeTo(10.5, 1e-9));
      expect(alinearAlCompas(10.1, 120, 0.5, haciaAtras: true), closeTo(8.5, 1e-9));
      expect(alinearAlCompas(10.5, 120, 0.5), closeTo(10.5, 1e-9));
      expect(alinearAlCompas(7, 0, 0), 7);
    });
  });

  group('orden como un DJ', () {
    final ritmo = {
      'yt:a': r(128, 0.9),
      'yt:b': r(90, 0.2),
      'yt:c': r(126, 0.8),
      'yt:d': r(95, 0.3),
      'yt:e': r(110, 0.5),
    };

    test('empieza por lo mas tranquilo y encadena tempos cercanos', () {
      final pasos = [for (final k in ['a', 'b', 'c', 'd', 'e']) PasoMezcla(pista: p(k))];
      final o = ordenarComoDj(pasos, ritmo).map((x) => x.pista['video_id']).toList();
      expect(o.first, 'b');
      expect(o, hasLength(5));
      expect(o.toSet(), {'a', 'b', 'c', 'd', 'e'});
      // la de 90 va junto a la de 95 y la de 128 junto a la de 126
      expect((o.indexOf('b') - o.indexOf('d')).abs(), 1);
      expect((o.indexOf('a') - o.indexOf('c')).abs(), 1);
    });

    test('lo que no tiene ritmo va al final, en su orden', () {
      final pasos = [for (final k in ['x', 'a', 'y', 'b']) PasoMezcla(pista: p(k))];
      final o = ordenarComoDj(pasos, ritmo).map((x) => x.pista['video_id']).toList();
      expect(o.sublist(2), ['x', 'y']);
    });

    test('con menos de dos canciones analizadas no cambia nada', () {
      final pasos = [for (final k in ['x', 'a', 'y']) PasoMezcla(pista: p(k))];
      expect(ordenarComoDj(pasos, ritmo).map((x) => x.pista['video_id']), ['x', 'a', 'y']);
    });

    test('marca los pasos que encajan', () {
      final pasos = [for (final k in ['a', 'c', 'b', 'x']) PasoMezcla(pista: p(k))];
      expect(encajesDelSet(pasos, ritmo), [Encaje.bueno, Encaje.choca, Encaje.desconocido]);
    });
  });

  group('mezcla automatica con perfiles', () {
    final ritmo = {'yt:a': r(120, 0.4), 'yt:b': r(124, 0.5), 'yt:c': r(150, 0.8)};
    final pistas = [p('a'), p('b'), p('c')];

    test('Suave: fundidos largos y sin cortes', () {
      final m = mezclaAutomatica(pistas, PerfilMezcla.suave, ritmo);
      expect(m, hasLength(3));
      expect(m.every((x) => x.tipo == TipoTransicion.fundido && x.fundido >= 8 && x.fundido <= 14), isTrue);
    });

    test('Club: graves, y filtro si los tempos chocan', () {
      final m = mezclaAutomatica(pistas, PerfilMezcla.club, ritmo);
      final a = m.firstWhere((x) => x.pista['video_id'] == 'a');
      expect(a.tipo, TipoTransicion.graves);
      expect(a.fundido, inInclusiveRange(8, 16));
      final b = m.firstWhere((x) => x.pista['video_id'] == 'b'); // b -> c choca (124 vs 150)
      expect(b.tipo, TipoTransicion.filtro);
    });

    test('Rapida: corto, y corte solo si encajan', () {
      final m = mezclaAutomatica(pistas, PerfilMezcla.rapida, ritmo);
      expect(m.every((x) => x.fundido <= 6), isTrue);
      final a = m.firstWhere((x) => x.pista['video_id'] == 'a');
      expect(a.tipo, TipoTransicion.corte);
      expect(a.curva, CurvaFader.corte);
      final b = m.firstWhere((x) => x.pista['video_id'] == 'b');
      expect(b.tipo, TipoTransicion.fundido);
    });

    test('sin ritmo conocido tambien arma una mezcla por duracion', () {
      final m = mezclaAutomatica([p('x'), p('y')], PerfilMezcla.club, const {});
      expect(m, hasLength(2));
      expect(m.first.fundido, closeTo(14, 1e-9));
    });

    test('los compases se pasan a segundos', () {
      expect(compasesASegundos(8, 120, 0), 16);
      expect(compasesASegundos(8, null, 14), 14);
    });
  });

  group('cuando entra la siguiente', () {
    test('sin tempo: lo que pide el paso', () {
      final paso = PasoMezcla(pista: p('a', dur: 200), entraAntes: 10);
      expect(momentoDeEntrada(paso, 200, null), 190);
    });

    test('con tempo cae en un inicio de compas y cabe el cambio', () {
      // 120 BPM: compas de 2 s con el uno en 0,5
      final paso = PasoMezcla(pista: p('a', dur: 200), entraAntes: 10, fundido: 8);
      final ritmo = AnalisisRitmo(bpm: 120, primerTiempo: 0.5);
      final t = momentoDeEntrada(paso, 200, ritmo);
      final k = (t - 0.5) / 2;
      expect((k - k.round()).abs(), lessThan(1e-9), reason: 'no es inicio de compas: $t');
      expect((t - 190).abs(), lessThanOrEqualTo(1.0));
      expect(t, lessThanOrEqualTo(200 - paso.fundidoEfectivo));
    });

    test('sin alinear no se mueve', () {
      final paso = PasoMezcla(pista: p('a', dur: 200), entraAntes: 10, alCompas: false);
      expect(momentoDeEntrada(paso, 200, AnalisisRitmo(bpm: 120, primerTiempo: 0.5)), 190);
    });

    test('un punto de salida marcado manda sobre "cuando falten"', () {
      final paso = PasoMezcla(pista: p('a', dur: 200), entraAntes: 10, salida: 170, alCompas: false);
      expect(paso.entraEfectivo, 30);
      expect(momentoDeEntrada(paso, 200, null), 170);
    });

    test('la entrada de la siguiente: la marcada, o el compas siguiente', () {
      final sig = PasoMezcla(pista: p('b'));
      expect(inicioDeEntrante(sig, 1.2, null), 1.2);
      expect(inicioDeEntrante(sig, 1.2, AnalisisRitmo(bpm: 120, primerTiempo: 0.5)), closeTo(2.5, 1e-9));
      expect(inicioDeEntrante(sig.copiaCon(entrada: 33), 1.2, AnalisisRitmo(bpm: 120, primerTiempo: 0.5)), 33);
    });

    test('el corte es casi instantaneo', () {
      expect(PasoMezcla(pista: p('a'), tipo: TipoTransicion.corte).fundidoEfectivo, 0.3);
    });
  });

  group('volumen, graves, filtro y ecualizador', () {
    test('las tres curvas empiezan y acaban bien', () {
      for (final c in CurvaFader.values) {
        expect(ganancia(c, 0, entrante: true), closeTo(0, 1e-9), reason: c.name);
        expect(ganancia(c, 1, entrante: true), closeTo(1, 1e-9), reason: c.name);
        expect(ganancia(c, 0, entrante: false), closeTo(1, 1e-9), reason: c.name);
        expect(ganancia(c, 1, entrante: false), closeTo(0, 1e-9), reason: c.name);
      }
    });

    test('la suave mantiene la potencia; la lineal, la suma; el corte aguanta y cae', () {
      final s = ganancia(CurvaFader.suave, 0.5, entrante: true);
      expect(2 * s * s, closeTo(1, 1e-9));
      expect(ganancia(CurvaFader.lineal, 0.3, entrante: true) + ganancia(CurvaFader.lineal, 0.3, entrante: false),
          closeTo(1, 1e-9));
      expect(ganancia(CurvaFader.corte, 0.3, entrante: false), 1);
      expect(ganancia(CurvaFader.corte, 0.3, entrante: true), 0);
    });

    test('el filtro de barrido sube y baja en saltos de 6 dB', () {
      expect(dbFiltro(0, entrante: false), 0);
      expect(dbFiltro(1, entrante: false), -18);
      expect(dbFiltro(0, entrante: true), -18);
      expect(dbFiltro(1, entrante: true), 0);
      for (var i = 0; i <= 20; i++) {
        expect(dbFiltro(i / 20, entrante: false) % 6, 0);
      }
      expect(filtroBarrido(0, agudos: false), '');
      expect(filtroBarrido(-12, agudos: false), allOf(contains('equalizer=f=60'), contains('g=-12')));
      expect(filtroBarrido(-12, agudos: true), contains('equalizer=f=12000'));
      expect(filtroBarrido(-12, agudos: true), isNot(contains('loudnorm')));
    });

    test('ecualizador de 3 bandas: solo las que se tocan', () {
      expect(filtroEq3(const [0, 0, 0]), '');
      expect(filtroEq3(const [6, 0, -3]), 'lavfi=[equalizer=f=100:t=o:w=2:g=6,equalizer=f=8000:t=o:w=2:g=-3]');
      expect(filtroEq3(const [99, 0, 0]), contains('g=12'));
    });
  });

  group('guardado compatible con lo anterior', () {
    test('una mezcla vieja (sin tipo ni ecualizador) se abre como antes', () {
      final vieja = {
        'id': 'm1', 'nombre': 'Antigua', 'creada': 1,
        'pasos': [
          {'pista': p('a'), 'entra_antes': 12, 'fundido': 6, 'graves': false},
          {'pista': p('b'), 'entra_antes': 8, 'fundido': 8, 'graves': true},
        ],
      };
      final m = Mezcla.deJson(vieja)!;
      expect(m.pasos[0].tipo, TipoTransicion.fundido);
      expect(m.pasos[1].tipo, TipoTransicion.graves);
      expect(m.pasos[0].entraAntes, 12);
      expect(m.pasos[0].eq, [0, 0, 0]);
      expect(m.pasos[0].igualarTempo, isFalse); // lo viejo no estira nada: suena igual que antes
      expect(m.pasos[0].alCompas, isFalse);
      expect(m.pasos[0].entrada, isNull);
    });

    test('los parametros nuevos vuelven iguales', () {
      final paso = PasoMezcla(
        pista: p('a'), entraAntes: 14, fundido: 9, tipo: TipoTransicion.filtro, curva: CurvaFader.lineal,
        eq: const [3, -2, 6], igualarTempo: false, alCompas: true, entrada: 12.5, salida: 150,
      );
      final r2 = PasoMezcla.deJson(Mezcla(id: 'x', nombre: 'n', pasos: [paso, PasoMezcla(pista: p('b'))]).aJson()['pasos'][0])!;
      expect(r2.tipo, TipoTransicion.filtro);
      expect(r2.curva, CurvaFader.lineal);
      expect(r2.eq, [3, -2, 6]);
      expect(r2.igualarTempo, isFalse);
      expect(r2.alCompas, isTrue);
      expect(r2.entrada, 12.5);
      expect(r2.salida, 150);
    });

    test('valores rotos se acotan', () {
      final r2 = PasoMezcla.deJson({'pista': p('a'), 'eq': [99, -99], 'tipo': 'inventado', 'curva': 3})!;
      expect(r2.eq, [12, -12, 0]);
      expect(r2.tipo, TipoTransicion.fundido); // un tipo que no existe se queda en fundido
      expect(r2.curva, CurvaFader.suave);
    });
  });
}
