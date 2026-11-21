// El freno de las recargas del motor: decide si una canción que falló (enlace vencido, red caída,
// atasco esperando datos, corte antes del final) se vuelve a abrir o se deja.
//
// Antes cada camino recargaba por su cuenta y el contador volvía a cero con solo sonar 20 s, así
// que una canción que fallaba siempre en el mismo punto podía recargarse sin fin (cada recarga
// abre otra conexión, otro decodificador y otra salida de audio). Aquí hay tres topes que no se
// pueden saltar:
//
// 1. Por tanda: como mucho [porTanda] reintentos seguidos, con esperas que crecen (0,7 s, 1,4 s,
//    2,8 s...). Si después suena bien [sanaTras] seguidos, la tanda vuelve a empezar.
// 2. Por canción: nunca más de [porCancion] recargas de la misma canción, pase lo que pase.
// 3. Global: nunca más de [porMinuto] recargas en un minuto entre todas las canciones. Si se pasa,
//    el motor se da por «en apuros»: no se recarga nada más hasta que pase el minuto.
//
// Es lógica pura (sin temporizadores ni motor): el reproductor pregunta [decidir] y obedece.

import 'package:flutter/foundation.dart' show visibleForTesting;

/// Lo que se hace con un fallo.
enum Recarga {
  /// Volver a abrir la canción donde iba, tras [DecisionRecarga.espera].
  reintentar,

  /// Rendirse con esta canción: avisar y pasar a la siguiente.
  saltar,

  /// Demasiadas recargas en poco tiempo, en cualquier canción: parar y no insistir.
  frenar,
}

class DecisionRecarga {
  const DecisionRecarga(this.accion, {this.espera = Duration.zero, this.intento = 0});
  final Recarga accion;
  final Duration espera;

  /// Número del reintento (1, 2, 3...) para pedir otro enlace con otro cliente.
  final int intento;

  @override
  String toString() => 'DecisionRecarga($accion, ${espera.inMilliseconds} ms, intento $intento)';
}

class GuardaRecargas {
  GuardaRecargas({
    this.porTanda = 3,
    this.porCancion = 6,
    this.porMinuto = 8,
    this.sanaTras = const Duration(seconds: 45),
    this.esperaBase = const Duration(milliseconds: 700),
    DateTime Function()? reloj,
  }) : _reloj = reloj ?? DateTime.now;

  final int porTanda;
  final int porCancion;
  final int porMinuto;
  final Duration sanaTras;
  final Duration esperaBase;
  final DateTime Function() _reloj;

  String _clave = '';
  int _tanda = 0;
  int _cancion = 0;
  Duration? _sonoDesde; // posición en que volvió a sonar tras la última recarga
  final List<DateTime> _recientes = [];

  /// Recargas de la canción actual (para el informe y las pruebas).
  int get recargasCancion => _cancion;

  /// Reintentos de la tanda actual.
  int get tanda => _tanda;

  /// Una canción nueva (no una recarga de la misma): sus contadores empiezan de cero. El tope
  /// global no se toca: es justo el que frena los bucles que saltan de canción en canción.
  /// [forzar]: la persona eligió otra vez la misma canción (tocarla de nuevo): también empieza
  /// de cero.
  void nuevaCancion(String clave, {bool forzar = false}) {
    if (clave == _clave && !forzar) return;
    _clave = clave;
    _tanda = 0;
    _cancion = 0;
    _sonoDesde = null;
  }

  /// Avisa por dónde va lo que suena. Si sonó bien [sanaTras] desde la última recarga, la tanda
  /// vuelve a empezar (pero el tope por canción sigue contando).
  void sonando(Duration posicion) {
    if (_tanda == 0) return;
    final desde = _sonoDesde;
    if (desde == null) {
      _sonoDesde = posicion;
      return;
    }
    if (posicion < desde) {
      // se buscó hacia atrás: se cuenta desde aquí
      _sonoDesde = posicion;
      return;
    }
    if (posicion - desde >= sanaTras) {
      _tanda = 0;
      _sonoDesde = null;
    }
  }

  /// Qué hacer con un fallo de [clave].
  DecisionRecarga decidir(String clave) {
    nuevaCancion(clave);
    final ahora = _reloj();
    _recientes.removeWhere((t) => ahora.difference(t) >= const Duration(minutes: 1));
    if (_recientes.length >= porMinuto) return const DecisionRecarga(Recarga.frenar);
    if (_cancion >= porCancion || _tanda >= porTanda) return const DecisionRecarga(Recarga.saltar);
    _tanda++;
    _cancion++;
    _sonoDesde = null;
    _recientes.add(ahora);
    return DecisionRecarga(Recarga.reintentar, espera: esperaBase * (1 << (_tanda - 1)), intento: _tanda);
  }

  /// Las recargas del último minuto (para las pruebas).
  @visibleForTesting
  int get ultimoMinuto {
    final ahora = _reloj();
    return _recientes.where((t) => ahora.difference(t) < const Duration(minutes: 1)).length;
  }
}
