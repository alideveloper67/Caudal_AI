// Play y pausa suaves: al pausar el volumen baja en ~180 ms y despues se
// pausa; al reanudar arranca en silencio y sube en ~220 ms. Evita el "clic" de
// cortar o soltar la onda de golpe.
//
// Aqui solo vive la logica (sin motor de sonido): el reproductor le da tres
// funciones y esta multiplica su volumen por [factor]. El volumen guardado del
// usuario no se toca nunca: [factor] es un multiplicador aparte (como el del
// temporizador para dormir).
import 'dart:async';

const bajadaPausa = Duration(milliseconds: 180);
const subidaPausa = Duration(milliseconds: 220);

/// Curva suave (empieza y acaba sin tirones): 0 -> 0, 1 -> 1.
double suavizar(double t) {
  final x = t.clamp(0.0, 1.0);
  return x * x * (3 - 2 * x);
}

/// Cuantos pasos de [paso] caben en [total] (siempre al menos uno).
int pasosDeRampa(Duration total, Duration paso) =>
    (total.inMicroseconds / paso.inMicroseconds).ceil().clamp(1, 1000);

class PausaSuave {
  PausaSuave({
    required this.aplicar,
    required this.pausarMotor,
    required this.reanudarMotor,
    this.bajada = bajadaPausa,
    this.subida = subidaPausa,
    this.paso = const Duration(milliseconds: 20),
  });

  /// Pone el volumen del motor (lee [factor]).
  final Future<void> Function() aplicar;
  final Future<void> Function() pausarMotor;
  final Future<void> Function() reanudarMotor;
  final Duration bajada;
  final Duration subida;
  final Duration paso;

  /// 1 = volumen normal, 0 = silencio.
  double factor = 1;
  int _gen = 0;

  /// ¿Hay una bajada o una subida a medias?
  bool get enCurso => _enCurso > 0;
  int _enCurso = 0;

  /// Baja el volumen y pausa. Si mientras baja se pide otra cosa, esta orden se
  /// deja (no llega a pausar).
  Future<void> pausar() async {
    final g = ++_gen;
    await _rampa(0, bajada, g);
    if (g != _gen) return;
    await pausarMotor();
  }

  /// Reanuda. [sonaba]: el motor seguia sonando (se interrumpio una bajada),
  /// asi que se sube desde donde iba; si estaba pausado se arranca en silencio.
  Future<void> reanudar({required bool sonaba}) async {
    final g = ++_gen;
    if (!sonaba) {
      factor = 0;
      await aplicar();
      if (g != _gen) return;
      await reanudarMotor();
      if (g != _gen) return;
    }
    await _rampa(1, subida, g);
  }

  /// Corta cualquier rampa y deja el volumen entero (otra cancion, fundido...).
  void cancelar() {
    _gen++;
    factor = 1;
  }

  Future<void> _rampa(double hasta, Duration total, int g) async {
    final desde = factor;
    if ((hasta - desde).abs() < 0.001) {
      factor = hasta;
      return;
    }
    _enCurso++;
    try {
      // lo que ya se bajo cuenta: desde la mitad no hace falta la rampa entera
      final n = pasosDeRampa(total * ((hasta - desde).abs()), paso);
      for (var i = 1; i <= n; i++) {
        await Future<void>.delayed(paso);
        if (g != _gen) return;
        factor = desde + (hasta - desde) * suavizar(i / n);
        await aplicar();
        if (g != _gen) return;
      }
      factor = hasta;
    } finally {
      _enCurso--;
    }
  }
}
