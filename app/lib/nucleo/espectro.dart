// De dónde sale la «energía» que mueve el visualizador (lógica pura). El mismo modelo que
// Caudal Escritorio (espectro.py), y además, si el motor da el espectro de verdad, lo usa.
import 'dart:math';

double pulsoDeRitmo(double pos, double bpm, [double fase = 0]) {
  final b = bpm > 0 ? bpm : 100.0;
  final ciclo = ((pos - fase) * b / 60) % 1.0;
  return pow(1 - ciclo, 3).toDouble();
}

double acercar(double actual, double objetivo, double dt, double subida, double bajada) {
  final k = objetivo > actual ? subida : bajada;
  return actual + (objetivo - actual) * (1 - exp(-dt * k));
}

/// Junta las [bins] (0..255, de graves a agudos, a [hz] Hz) en [n] bandas 0..1, repartidas como oye el
/// oído: las graves, finas; las agudas, anchas.
List<double> agruparBandas(List<int> bins, int n, {double hz = 44100}) {
  if (bins.isEmpty) return List.filled(n, 0);
  final porBin = hz / 2 / bins.length;
  final salida = <double>[];
  for (var i = 0; i < n; i++) {
    final f0 = 40 * pow(12000 / 40, i / n);
    final f1 = 40 * pow(12000 / 40, (i + 1) / n);
    final desde = min(bins.length - 1, (f0 / porBin).floor());
    final hasta = max(desde + 1, min(bins.length, (f1 / porBin).ceil()));
    var maximo = 0;
    for (var k = desde; k < hasta; k++) {
      maximo = max(maximo, bins[k]);
    }
    // los agudos traen menos energía: se realzan un poco para que también se vean
    salida.add((pow(maximo / 255, 1.5) * (0.85 + 0.4 * i / n)).clamp(0.0, 1.0).toDouble());
  }
  return salida;
}

/// Energía, golpe y bandas suavizadas, listas para dibujar.
class ModeloAudio {
  ModeloAudio([this.n = 48])
      : bandas = List.filled(n, 0.0),
        picos = List.filled(n, 0.0);

  final int n;
  final List<double> bandas;

  /// La «tapita» de cada barra, que cae despacio.
  final List<double> picos;
  double energia = 0, golpe = 0;

  /// ¿Las bandas vienen del sonido de verdad? (si no, siguen el ritmo)
  bool medida = false;
  double _media = 0, _t = 0;

  bool get quieto =>
      energia < 0.004 && golpe < 0.004 && bandas.every((x) => x < 0.004) && picos.every((x) => x < 0.004);

  void avanzar(double dt, {List<double>? reales, bool sonando = true, double pos = 0, double bpm = 0, double fase = 0}) {
    dt = dt.clamp(0.0, 0.25);
    _t += dt;
    var objetivo = 0.0, golpeObj = 0.0;
    final usar = sonando && reales != null && reales.length == n;
    if (sonando) medida = usar;
    if (usar) {
      final graves = reales.take(max(1, n ~/ 6)).reduce(max);
      objetivo = 0.5 * reales.reduce((a, b) => a + b) / n + 0.5 * graves;
      golpeObj = ((graves - _media) * 2.2).clamp(0.0, 1.0);
      _media = acercar(_media, graves, dt, 1.2, 1.2);
    } else if (sonando) {
      final p = pulsoDeRitmo(pos, bpm, fase);
      objetivo = 0.30 + 0.45 * p;
      golpeObj = p;
    }
    energia = acercar(energia, objetivo, dt, 20, 5);
    golpe = acercar(golpe, golpeObj, dt, 35, 7);
    for (var i = 0; i < n; i++) {
      final double obj;
      if (usar) {
        obj = reales[i];
      } else {
        final x = i / max(1, n - 1);
        final peso = 0.30 + 0.70 * pow(1 - x, 0.7);
        final vaiven = 0.55 + 0.45 * sin(_t * (1.1 + 0.37 * i) + i * 1.7).abs();
        obj = (energia * peso * vaiven + golpe * 0.40 * pow(1 - x, 2)).clamp(0.0, 1.0).toDouble();
      }
      bandas[i] = acercar(bandas[i], obj, dt, 28, 7);
      picos[i] = max(bandas[i], picos[i] - dt * 0.35);
    }
  }
}
