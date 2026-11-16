import 'package:flutter/foundation.dart';

import '../nucleo/estudio.dart';
import 'reproductor.dart';

/// Une el modo estudio con el reproductor de siempre (modo audio).
class ControlReproductor implements ControlMusica {
  ControlReproductor(this.r);
  final Reproductor r;

  @override
  bool get sonando => r.estado == EstadoRepro.sonando;

  @override
  bool get hayMusica => r.actual != null;

  @override
  String get titulo => '${r.actual?['titulo'] ?? ''}';

  @override
  double get volumen => r.volumen;

  @override
  Listenable get cambios => r;

  @override
  Future<void> fijarVolumen(double v) => r.fijarVolumen(v);

  @override
  Future<void> fijarFactor(double f) => r.fijarFactorEstudio(f);

  @override
  Future<void> pausar() => r.pausar();

  @override
  Future<void> reanudar() => r.reanudar();

  @override
  Future<void> alternar() => r.alternar();

  @override
  Future<void> siguiente() => r.siguiente();

  @override
  Future<void> iniciarCola(List<Map<String, dynamic>> pistas, String titulo) =>
      r.iniciarEstudio(pistas, titulo: titulo);

  @override
  Future<void> salir() => r.salirEstudio();
}
