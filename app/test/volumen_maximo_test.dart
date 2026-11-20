// Volumen máximo sin distorsión: ganancia por canción según su sonoridad, tope del limitador,
// compatibilidad con el súper volumen antiguo, sonoridad de YouTube, pista DRC y elección de formato.
import 'package:caudal/nucleo/innertube.dart';
import 'package:caudal/nucleo/sonoridad.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http_parser/http_parser.dart';
import 'package:youtube_explode_dart/youtube_explode_dart.dart';

AudioOnlyStreamInfo _audio(int itag, String codec, int bps) => AudioOnlyStreamInfo(
    VideoId('dQw4w9WgXcQ'), itag, Uri.parse('https://x/$itag'),
    StreamContainer.parse(codec == 'opus' ? 'webm' : 'mp4'), FileSize(1000), Bitrate(bps), codec, '',
    const [], MediaType('audio', codec == 'opus' ? 'webm' : 'mp4'), null);

void main() {
  group('nivel', () {
    test('lo guardado manda; apagado con igualar = Normal', () {
      expect(nivelEfectivo(guardado: 'maximo'), 'maximo');
      expect(nivelEfectivo(guardado: 'no', normalizar: true), 'normal');
      expect(nivelEfectivo(guardado: 'no', normalizar: false), isNull);
    });

    test('ajustes de antes: el súper volumen se respeta y si no, Alto', () {
      expect(nivelEfectivo(superVolumen: 4), 'maximo');
      expect(nivelEfectivo(superVolumen: 1), 'alto');
      expect(nivelEfectivo(), 'alto');
      // quien apagó a propósito el igualar volumen no lo recibe sin pedirlo
      expect(nivelEfectivo(normalizar: false, normalizarGuardado: true), isNull);
    });
  });

  group('ganancia', () {
    test('una canción baja sube y una fuerte baja', () {
      expect(gananciaDb('alto', lufs: -16, pico: -6), closeTo(6, 1e-9));
      expect(gananciaDb('alto', lufs: -7, pico: -0.1), closeTo(-3, 1e-9));
    });

    test('el limitador solo puede recortar su presupuesto', () {
      expect(gananciaDb('maximo', lufs: -20, pico: -1), closeTo(6, 1e-9));
      expect(gananciaDb('alto', lufs: -20, pico: -1), closeTo(3, 1e-9));
      expect(gananciaDb('normal', lufs: -20, pico: -1), closeTo(0, 1e-9));
      expect(gananciaDb('maximo', lufs: -20, pico: -1, extra: 2), closeTo(4, 1e-9));
    });

    test('sin limitador (iPhone) sube poco', () {
      expect(gananciaDb('maximo', lufs: -20, conLimitador: false), closeTo(3, 1e-9));
      expect(gananciaDb('alto', lufs: -20, conLimitador: false), closeTo(2, 1e-9));
      expect(gananciaDb('normal', lufs: -20, conLimitador: false), closeTo(0, 1e-9));
      // pero bajar las fuertes sí, igual que con limitador
      expect(gananciaDb('alto', lufs: -6, conLimitador: false), closeTo(-4, 1e-9));
    });

    test('sin dato supone un master típico; apagado no toca nada', () {
      expect(gananciaDb('alto'), closeTo(-1, 1e-9));
      expect(gananciaDb(null, lufs: -30), 0);
      expect(gananciaDb('maximo', lufs: -70, pico: -40), gananciaMaxima);
    });

    test('el volumen de mpv es cúbico', () {
      expect(factorVolumenMpv(0), 1);
      expect(factorVolumenMpv(6), closeTo(1.2589, 1e-3)); // (1,2589)^3 = +6 dB
    });

    test('en la PC: ganancia delante y limitador con sobremuestreo', () {
      final p = partesGananciaYLimitador(3);
      expect(p.first, 'volume=3.00dB');
      expect(p.where((x) => x.startsWith('alimiter')).length, 1);
      expect(partesGananciaYLimitador(0).first, 'aresample=192000');
    });
  });

  group('sonoridad de YouTube', () {
    test('loudnessDb respecto de -14 LUFS', () {
      expect(lufsDeYoutube(5.5), -8.5);
      expect(lufsDeYoutube(-3), -17);
      expect(lufsDeYoutube(null), isNull);
      expect(lufsDeYoutube(99), isNull);
    });

    test('de la respuesta del reproductor, la general o la de la pista original', () {
      expect(Innertube.lufsDe({'playerConfig': {'audioConfig': {'loudnessDb': 4.0}}}), -10);
      expect(
          Innertube.lufsDe({
            'streamingData': {
              'adaptiveFormats': [
                {'mimeType': 'audio/webm', 'isDrc': true, 'loudnessDb': 1.0},
                {'mimeType': 'audio/webm', 'loudnessDb': 2.0},
              ]
            }
          }),
          -12);
      expect(Innertube.lufsDe({}), isNull);
    });

    test('registro: recuerda y respeta el tope', () {
      final r = RegistroSonoridad(maximo: 2);
      r.recordar('a', -9);
      r.recordar('b', -10);
      r.recordar('c', -11);
      expect(r.lufs('a'), isNull);
      expect(r.lufs('c'), -11);
      expect(r.lufs(''), isNull);
    });
  });

  group('mejor fuente', () {
    test('la pista DRC se salta si hay otra', () {
      Map<String, dynamic> f(int itag, {bool drc = false}) => {
            'itag': itag, 'url': 'https://x/$itag', 'mimeType': 'audio/webm; codecs="opus"',
            'contentLength': '1000', 'bitrate': 150000, if (drc) 'isDrc': true,
          };
      final m = Innertube.armarManifiesto(VideoId('dQw4w9WgXcQ'), {
        'streamingData': {'adaptiveFormats': [f(251, drc: true), f(250)]}
      });
      expect(m.audioOnly.map((a) => a.tag), [250]);
      final solo = Innertube.armarManifiesto(VideoId('dQw4w9WgXcQ'), {
        'streamingData': {'adaptiveFormats': [f(251, drc: true)]}
      });
      expect(solo.audioOnly.length, 1); // si es la única, sirve
    });

    test('Opus gana al AAC de tasa parecida; los topes de datos se respetan', () {
      final opus = _audio(251, 'opus', 135000);
      final aac = _audio(140, 'mp4a.40.2', 130000);
      final bajo = _audio(249, 'opus', 55000);
      expect(Streams.elegirAudio([aac, opus, bajo])!.tag, 251);
      expect(Streams.elegirAudio([aac, _audio(251, 'opus', 120000)])!.tag, 251); // 120*1,15 > 130
      expect(Streams.elegirAudio([aac, _audio(251, 'opus', 100000)])!.tag, 140);
      expect(Streams.elegirAudio([aac, opus, bajo], calidad: 'ahorro')!.tag, 249);
      expect(Streams.elegirAudio([aac, opus, bajo], calidad: 'normal')!.tag, 251);
      expect(Streams.elegirAudio([]), isNull);
    });
  });
}
