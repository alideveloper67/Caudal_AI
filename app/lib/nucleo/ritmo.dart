import 'dart:math';

/// Ritmo de una cancion: tempo (BPM), donde cae el primer tiempo, energia y una
/// silueta de energia para dibujarla. Logica pura (sin ffmpeg ni pantallas)
/// para poder probarla con audio sintetico.
class AnalisisRitmo {
  const AnalisisRitmo({
    required this.bpm,
    this.primerTiempo = 0,
    this.energia = 0.5,
    this.barras = const [],
    this.confianza = 0,
    this.manual = false,
    this.inicioAnalizado = 0,
    this.duracionAnalizada = 0,
  });

  /// Pulsos por minuto (0 si no se pudo saber).
  final double bpm;

  /// Segundo (de la cancion) en que cae un tiempo fuerte; sirve de ancla del compas.
  final double primerTiempo;

  /// 0 a 1: lo "intensa" que suena.
  final double energia;

  /// Energia por tramos (0 a 1) de lo analizado, para dibujar las barras.
  final List<double> barras;

  /// 0 a 1: lo claro que era el pulso (bajo = poco fiable).
  final double confianza;

  /// Lo escribio o lo toco la persona (no se recalcula).
  final bool manual;

  /// Desde que segundo de la cancion y cuanto se analizo (para ubicar las barras).
  final double inicioAnalizado;
  final double duracionAnalizada;

  bool get valido => bpm >= 40 && bpm <= 240;

  /// Segundos entre dos tiempos.
  double get tiempo => valido ? 60 / bpm : 0;

  /// Segundos de un compas de [tiempos] tiempos (4 por defecto).
  double compas([int tiempos = 4]) => tiempo * tiempos;

  AnalisisRitmo copiaCon({double? bpm, double? primerTiempo, bool? manual}) => AnalisisRitmo(
        bpm: bpm ?? this.bpm,
        primerTiempo: primerTiempo ?? this.primerTiempo,
        energia: energia,
        barras: barras,
        confianza: confianza,
        manual: manual ?? this.manual,
        inicioAnalizado: inicioAnalizado,
        duracionAnalizada: duracionAnalizada,
      );

  Map<String, dynamic> aJson() => {
        'bpm': double.parse(bpm.toStringAsFixed(2)),
        'primer': double.parse(primerTiempo.toStringAsFixed(3)),
        'energia': double.parse(energia.toStringAsFixed(3)),
        'barras': [for (final b in barras) double.parse(b.toStringAsFixed(3))],
        'conf': double.parse(confianza.toStringAsFixed(3)),
        'manual': manual,
        'ini': inicioAnalizado,
        'dur': duracionAnalizada,
      };

  static AnalisisRitmo? deJson(Object? d) {
    if (d is! Map) return null;
    double n(Object? v, [double def = 0]) => v is num ? v.toDouble() : def;
    return AnalisisRitmo(
      bpm: n(d['bpm']),
      primerTiempo: n(d['primer']),
      energia: n(d['energia'], 0.5).clamp(0.0, 1.0),
      barras: [for (final b in (d['barras'] is List ? d['barras'] as List : const [])) n(b).clamp(0.0, 1.0)],
      confianza: n(d['conf']).clamp(0.0, 1.0),
      manual: d['manual'] == true,
      inicioAnalizado: n(d['ini']),
      duracionAnalizada: n(d['dur']),
    );
  }
}

/// Estima el ritmo de [x] (audio mono, muestras de -1 a 1, a [hz] Hz).
///
/// Saca la envolvente de energia (cada 5 ms), se queda con los golpes (subidas
/// de energia) y busca el periodo que mas se repite por autocorrelacion,
/// mirando tambien sus multiplos (asi un bombo en cada tiempo no se confunde
/// con la mitad del tempo). Devuelve bpm 0 si no hay pulso claro.
AnalisisRitmo estimarRitmo(List<double> x, int hz,
    {double inicio = 0, double minBpm = 70, double maxBpm = 180, int barrasN = 48}) {
  final hop = max(1, hz ~/ 200); // 5 ms
  final fps = hz / hop;
  final n = x.length ~/ hop;
  if (n < fps * 6) return const AnalisisRitmo(bpm: 0);

  // envolvente: energia media por trozo
  final env = List<double>.filled(n, 0);
  var maximo = 0.0;
  var suma = 0.0;
  for (var i = 0; i < n; i++) {
    var s = 0.0;
    for (var j = i * hop; j < (i + 1) * hop; j++) {
      s += x[j] * x[j];
    }
    env[i] = sqrt(s / hop);
    suma += env[i];
    maximo = max(maximo, env[i]);
  }
  if (maximo < 1e-4) return const AnalisisRitmo(bpm: 0);

  // golpes: subida de la energia (comprimida para que los suaves tambien cuenten)
  final comp = [for (final e in env) pow(e / maximo, 0.6).toDouble()];
  final on = List<double>.filled(n, 0);
  for (var i = 1; i < n; i++) {
    on[i] = max(0.0, comp[i] - comp[i - 1]);
  }
  // quitar el fondo (media movil de ~1 s) para que solo queden los picos
  final v = (fps).round();
  final limpio = List<double>.filled(n, 0);
  var acc = 0.0;
  for (var i = 0; i < n; i++) {
    acc += on[i];
    if (i >= 2 * v + 1) acc -= on[i - 2 * v - 1];
    final cnt = min(i + 1, 2 * v + 1);
    limpio[i] = max(0.0, on[i] - acc / cnt);
  }

  double auto(int lag) {
    if (lag >= n - 1) return 0;
    var s = 0.0;
    for (var i = 0; i + lag < n; i++) {
      s += limpio[i] * limpio[i + lag];
    }
    return s / (n - lag);
  }

  final lagMin = (fps * 60 / maxBpm).floor();
  final lagMax = (fps * 60 / minBpm).ceil();
  final r = <int, double>{};
  for (var lag = lagMin - 1; lag <= lagMax + 1; lag++) {
    r[lag] = auto(lag);
  }
  final r0 = auto(0);
  if (r0 < 1e-9) return const AnalisisRitmo(bpm: 0); // no hay golpes: una nota continua, silencio...

  // peine de multiplos: el periodo verdadero suma con el doble y el triple
  var mejor = lagMin;
  var mejorV = -1.0;
  for (var lag = lagMin; lag <= lagMax; lag++) {
    final p = r[lag]! + 0.5 * auto(2 * lag) + 0.25 * auto(3 * lag);
    // los mas rapidos del rango pesan un poco menos (suelen ser subdivisiones)
    if (p > mejorV) {
      mejorV = p;
      mejor = lag;
    }
  }
  // un tempo muy rapido suele ser la subdivision (corcheas) de uno a la mitad: si ese
  // tambien suena igual de fuerte, se prefiere el lento. Para mezclar da igual (el doble
  // y la mitad cuentan como el mismo tempo).
  if (60 * fps / mejor > 160 && 2 * mejor <= lagMax + 1) {
    final l2 = 2 * mejor;
    final mayor = [for (var d = -1; d <= 1; d++) auto(l2 + d)].reduce(max);
    if (mayor >= 0.9 * r[mejor]!) {
      mejor = l2;
      for (var d = -1; d <= 1; d++) {
        r[l2 + d] ??= auto(l2 + d);
      }
      mejor += [for (var d = -1; d <= 1; d++) (auto(l2 + d), d)].reduce((a, b) => a.$1 >= b.$1 ? a : b).$2;
    }
  }
  // afinado entre muestras (parabola)
  var lagFino = mejor.toDouble();
  final a = r[mejor - 1] ?? auto(mejor - 1), b = r[mejor] ?? auto(mejor), c = r[mejor + 1] ?? auto(mejor + 1);
  final den = a - 2 * b + c;
  if (den.abs() > 1e-12) lagFino += (0.5 * (a - c) / den).clamp(-1.0, 1.0);
  final bpm = 60 * fps / lagFino;

  // donde cae el pulso: la fase con mas golpes
  final periodo = lagFino;
  var mejorFase = 0.0;
  var mejorS = -1.0;
  for (var f = 0.0; f < periodo; f += 1) {
    var s = 0.0;
    for (var t = f; t < n; t += periodo) {
      final i = t.round();
      if (i < n) s += limpio[i];
    }
    if (s > mejorS) {
      mejorS = s;
      mejorFase = f;
    }
  }

  final barras = <double>[];
  final por = n / barrasN;
  var mb = 0.0;
  for (var k = 0; k < barrasN; k++) {
    var s = 0.0;
    final d = (k * por).floor(), h = max(d + 1, ((k + 1) * por).floor());
    for (var i = d; i < h && i < n; i++) {
      s += env[i];
    }
    final m = s / (h - d);
    barras.add(m);
    mb = max(mb, m);
  }
  final energiaMedia = suma / n;
  return AnalisisRitmo(
    bpm: bpm,
    primerTiempo: inicio + mejorFase / fps,
    energia: (energiaMedia * 4).clamp(0.0, 1.0),
    barras: [for (final m in barras) mb > 0 ? m / mb : 0.0],
    confianza: (b / r0).clamp(0.0, 1.0),
    inicioAnalizado: inicio,
    duracionAnalizada: x.length / hz,
  );
}

/// Pasa el tempo al rango habitual (70 a 180) doblando o partiendo a la mitad.
double plegarBpm(double bpm, {double min = 70, double max = 180}) {
  if (bpm <= 0) return 0;
  var b = bpm;
  while (b < min) {
    b *= 2;
  }
  while (b > max) {
    b /= 2;
  }
  return b;
}

/// El tempo que sale de unos toques (en milisegundos): la mediana de los
/// intervalos, sin contar los cortes largos. Null si hay menos de 4 toques.
double? bpmDeToques(List<int> toquesMs) {
  if (toquesMs.length < 4) return null;
  final d = <int>[for (var i = 1; i < toquesMs.length; i++) toquesMs[i] - toquesMs[i - 1]]..sort();
  final med = d[d.length ~/ 2];
  if (med <= 0) return null;
  final buenos = [for (final x in d) if (x > med * 0.7 && x < med * 1.4) x];
  final media = buenos.reduce((a, b) => a + b) / buenos.length;
  final bpm = 60000 / media;
  return bpm >= 40 && bpm <= 240 ? bpm : null;
}

/// Que tan bien encajan dos tempos para mezclarlos.
enum Encaje { bueno, regular, choca, desconocido }

/// Cuanto hay que acelerar (>1) o frenar (<1) a la que entra para igualar el
/// tempo de la que sale. Considera tambien el doble y la mitad. Si la
/// diferencia pasa de [maximo] (8 %), devuelve 1: no se estira, se mezcla tal cual.
double razonDeTempo(double bpmSale, double bpmEntra, {double maximo = 0.08}) {
  if (bpmSale < 40 || bpmEntra < 40) return 1;
  var mejor = 1.0;
  var menor = double.infinity;
  for (final m in const [0.5, 1.0, 2.0]) {
    final r = bpmSale / (bpmEntra * m);
    if ((r - 1).abs() < menor) {
      menor = (r - 1).abs();
      mejor = r;
    }
  }
  return menor <= maximo ? mejor : 1;
}

/// Lo parecidos que son dos tempos (contando doble y mitad como iguales).
double diferenciaDeTempo(double a, double b) {
  if (a < 40 || b < 40) return double.nan;
  var m = double.infinity;
  for (final k in const [0.5, 1.0, 2.0]) {
    m = min(m, (a / (b * k) - 1).abs());
  }
  return m;
}

Encaje encajeDe(double? bpmA, double? bpmB) {
  if (bpmA == null || bpmB == null) return Encaje.desconocido;
  final d = diferenciaDeTempo(bpmA, bpmB);
  if (d.isNaN) return Encaje.desconocido;
  if (d <= 0.06) return Encaje.bueno;
  if (d <= 0.12) return Encaje.regular;
  return Encaje.choca;
}

/// El primer inicio de compas de una cancion en o despues de [t] segundos.
/// [primerTiempo] es un tiempo fuerte conocido; el compas dura [tiempos] tiempos.
double alinearAlCompas(double t, double bpm, double primerTiempo, {int tiempos = 4, bool haciaAtras = false}) {
  if (bpm < 40) return t;
  final c = 60 / bpm * tiempos;
  final k = (t - primerTiempo) / c;
  final n = haciaAtras ? k.floor() : k.ceil();
  return primerTiempo + n * c;
}
