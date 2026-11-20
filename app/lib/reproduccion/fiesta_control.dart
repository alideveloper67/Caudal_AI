import 'package:flutter/foundation.dart';

import '../nucleo/fiesta.dart';
import 'reproductor.dart';

/// La Fiesta manejando el reproductor de siempre (sin tocarlo por dentro): mira qué suena,
/// cuánto falta y pone las canciones pedidas detrás de la actual.
class ControlFiestaReproductor implements ControlFiesta {
  ControlFiestaReproductor(this.r);
  final Reproductor r;

  @override
  Json? get actual => r.actual;
  @override
  List<Json> get proximas => r.proximas;
  @override
  bool get parado => r.estado == EstadoRepro.parado;
  @override
  bool get enPausa => r.estado == EstadoRepro.pausa;
  @override
  int get posicionMs => r.posicion.value.inMilliseconds;
  @override
  int get duracionMs {
    final d = r.duracion.value.inMilliseconds;
    if (d > 0) return d;
    final s = r.actual?['duracion'];
    return s is num ? (s * 1000).toInt() : 0;
  }

  @override
  void ponerDespues(Json pista) => r.reproducirDespues([pista]);

  /// Suena ya, sin perder lo que venía después.
  @override
  Future<void> ponerAhora(Json pista) async {
    if (r.actual == null || parado) {
      await r.reproducirPista(pista);
      return;
    }
    r.reproducirDespues([pista]);
    await r.siguiente();
  }

  @override
  void addListener(VoidCallback l) => r.addListener(l);
  @override
  void removeListener(VoidCallback l) => r.removeListener(l);
}
