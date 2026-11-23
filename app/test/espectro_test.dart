import 'package:caudal/nucleo/espectro.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('el pulso es 1 en el golpe y cae antes del siguiente', () {
    expect(pulsoDeRitmo(0, 120), 1);
    expect(pulsoDeRitmo(0.5, 120), closeTo(1, 1e-9));
    expect(pulsoDeRitmo(0.45, 120), lessThan(0.01));
    expect(pulsoDeRitmo(1, 0), inInclusiveRange(0, 1)); // sin tempo no lanza
  });

  test('un grave solo mueve las bandas de la izquierda y un agudo las de la derecha', () {
    final g = List.filled(1024, 0)..[4] = 255; // ~86 Hz
    final a = List.filled(1024, 0)..[420] = 255; // ~9 kHz
    final bg = agruparBandas(g, 48), ba = agruparBandas(a, 48);
    expect(bg.indexWhere((x) => x > 0.5), lessThan(12));
    expect(bg.skip(24).every((x) => x == 0), isTrue);
    expect(ba.indexWhere((x) => x > 0.5), greaterThan(40));
    expect(agruparBandas(const [], 48), List.filled(48, 0.0));
  });

  test('sube al sonar, queda entre 0 y 1 y acaba quieto en pausa', () {
    final m = ModeloAudio();
    for (var i = 0; i < 60; i++) {
      m.avanzar(0.033, pos: i * 0.033, bpm: 120);
    }
    expect(m.energia, greaterThan(0.2));
    expect(m.medida, isFalse);
    expect(m.bandas.every((x) => x >= 0 && x <= 1), isTrue);
    m.avanzar(0.033, reales: List.filled(48, 0.8));
    expect(m.medida, isTrue);
    for (var i = 0; i < 200; i++) {
      m.avanzar(0.033, sonando: false);
    }
    expect(m.quieto, isTrue);
  });
}
