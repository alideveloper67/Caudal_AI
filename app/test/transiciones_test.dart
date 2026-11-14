import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/descarga_inteligente.dart';
import 'package:caudal/nucleo/transiciones.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> _p(String vid, [int dur = 200]) => {'video_id': vid, 'duracion': dur};

void main() {
  group('transiciones DJ', () {
    test('sin tramos la musica dura toda la cancion', () {
      expect(finDeMusica([], 200), 200);
      expect(inicioDeMusica([], 200), 0);
    });

    test('un tramo sin musica pegado al final adelanta el final', () {
      expect(finDeMusica([(185.0, 199.5, 'music_offtopic')], 200), 185);
    });

    test('tramos que no tocan el final o se comen media cancion no cuentan', () {
      expect(finDeMusica([(100.0, 120.0, 'music_offtopic')], 200), 200);
      expect(finDeMusica([(60.0, 200.0, 'music_offtopic')], 200), 200);
      expect(finDeMusica([(185.0, 200.0, 'sponsor')], 200), 200);
    });

    test('una intro sin musica se salta al entrar', () {
      expect(inicioDeMusica([(0.0, 12.5, 'music_offtopic')], 200), 12.5);
      expect(inicioDeMusica([(0.8, 9.0, 'music_offtopic')], 200), 9);
    });

    test('la intro no puede ser media cancion ni empezar tarde', () {
      expect(inicioDeMusica([(0.0, 120.0, 'music_offtopic')], 200), 0);
      expect(inicioDeMusica([(5.0, 20.0, 'music_offtopic')], 200), 0);
    });

    test('duracion del fundido DJ', () {
      expect(duracionFundidoDj(0), 2);
      expect(duracionFundidoDj(6), 6);
    });

    test('lee el nivel de astats de los metadatos de mpv', () {
      expect(nivelDeMetadatos('{"lavfi.astats.Overall.RMS_level":"-23.51","x":"1"}'), closeTo(-23.51, 1e-9));
      expect(nivelDeMetadatos('{"lavfi.astats.Overall.RMS_level":"-inf"}'), double.negativeInfinity);
      expect(nivelDeMetadatos('lavfi.astats.Overall.RMS_level=-61.2'), closeTo(-61.2, 1e-9));
      expect(nivelDeMetadatos(''), isNull);
      expect(nivelDeMetadatos('{"otra":"1"}'), isNull);
    });

    test('el detector pide silencio seguido', () {
      final d = DetectorSilencio(umbralDb: -55, minimo: const Duration(milliseconds: 1500));
      final t0 = DateTime(2026);
      expect(d.medir(-70, t0), isFalse);
      expect(d.medir(-70, t0.add(const Duration(milliseconds: 800))), isFalse);
      // un golpe de sonido reinicia la cuenta
      expect(d.medir(-20, t0.add(const Duration(milliseconds: 1000))), isFalse);
      expect(d.medir(-70, t0.add(const Duration(milliseconds: 1200))), isFalse);
      expect(d.medir(double.negativeInfinity, t0.add(const Duration(milliseconds: 2800))), isTrue);
      // sin medida no decide nada
      expect(d.medir(null, t0.add(const Duration(seconds: 9))), isFalse);
    });
  });

  group('temporizador para dormir', () {
    test('el volumen baja poco a poco los ultimos 30 s', () {
      expect(factorApagado(null), 1);
      expect(factorApagado(600), 1);
      expect(factorApagado(30), 1);
      expect(factorApagado(15), closeTo(0.5, 1e-9));
      expect(factorApagado(3), closeTo(0.1, 1e-9));
      expect(factorApagado(0), 0);
      expect(factorApagado(-2), 0);
    });

    test('nunca sube mientras se acerca la hora', () {
      var antes = 1.0;
      for (var s = 40.0; s >= 0; s -= 0.5) {
        final f = factorApagado(s);
        expect(f, lessThanOrEqualTo(antes));
        antes = f;
      }
    });
  });

  group('descarga inteligente', () {
    test('solo con wifi y el ajuste encendido', () {
      expect(puedeDescargarSola(activa: true, conDatos: false, sinRed: false), isTrue);
      expect(puedeDescargarSola(activa: true, conDatos: true, sinRed: false), isFalse);
      expect(puedeDescargarSola(activa: true, conDatos: false, sinRed: true), isFalse);
      expect(puedeDescargarSola(activa: false, conDatos: false, sinRed: false), isFalse);
    });

    test('estima el tamano por duracion y formato', () {
      expect(tamanoEstimado(_p('a', 100), 320), 100 * 40000);
      expect(tamanoEstimado({'video_id': 'a'}, 320), 240 * 40000);
      expect(kbpsDeFormato('mp3', '192'), 192);
      expect(kbpsDeFormato('flac', ''), 1000);
      expect(bytesDeGb(5), 5 * 1024 * 1024 * 1024);
      expect(bytesDeGb(0), 0);
    });

    test('alterna me gusta y mas escuchadas sin repetir ni excluidas', () {
      final plan = planDescargaInteligente(
        meGusta: [_p('g1'), _p('g2'), _p('x')],
        masEscuchadas: [_p('g1'), _p('t1'), _p('t2')],
        excluir: {'x'},
        bytesUsados: 0,
        limiteBytes: bytesDeGb(5),
        kbps: 320,
        maximo: 10,
      );
      expect(plan.map((p) => p['video_id']), ['g1', 'g2', 't1', 't2']);
    });

    test('respeta el limite de espacio y el maximo', () {
      final peso = tamanoEstimado(_p('a'), 320); // 8 MB
      final plan = planDescargaInteligente(
        meGusta: [_p('a'), _p('b'), _p('c', 20)],
        masEscuchadas: [],
        excluir: {},
        bytesUsados: 0,
        limiteBytes: peso + tamanoEstimado(_p('c', 20), 320),
        kbps: 320,
        maximo: 10,
      );
      // b no cabe, pero la corta si
      expect(plan.map((p) => p['video_id']), ['a', 'c']);
      expect(planDescargaInteligente(meGusta: [_p('a'), _p('b')], masEscuchadas: [], excluir: {},
          bytesUsados: 0, limiteBytes: bytesDeGb(5), kbps: 320, maximo: 1).length, 1);
      expect(planDescargaInteligente(meGusta: [_p('a')], masEscuchadas: [], excluir: {},
          bytesUsados: bytesDeGb(5), limiteBytes: bytesDeGb(5), kbps: 320), isEmpty);
    });

    test('ignora pistas sin video', () {
      expect(planDescargaInteligente(meGusta: [{'titulo': 'local'}], masEscuchadas: [], excluir: {},
          bytesUsados: 0, limiteBytes: bytesDeGb(1), kbps: 320), isEmpty);
    });
  });

  test('ajustes nuevos con sus defectos y compartidos', () {
    expect(Ajustes.defectos['descarga_inteligente'], false);
    expect(Ajustes.defectos['descarga_inteligente_gb'], 5);
    expect(Ajustes.defectos['transicion_dj'], true);
    expect(Ajustes.defectos['apagado_suave'], true);
    for (final k in ['descarga_inteligente', 'descarga_inteligente_gb', 'transicion_dj', 'apagado_suave']) {
      expect(Ajustes.compartidos, contains(k));
    }
  });
}
