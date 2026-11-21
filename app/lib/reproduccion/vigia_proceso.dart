// El vigía del proceso (Android): mientras suena música mira cada 20 s cuántos mapas de memoria,
// hilos y memoria lleva Caudal (Salidas.kt lee /proc/self). Si algo crece sin freno —lo que pasó
// en la 2.7.5 en un Honor: «Scudo… internal map failure (NO MEMORY)» con 3 GB libres, es decir,
// se acabaron los mapas del proceso— Android mataría la app. Antes de eso:
//
// 1. [AccionVigia.renovar]: se cierran los dos motores y se crean nuevos (lo que se acumuló se
//    libera con ellos) y la canción sigue donde iba.
// 2. [AccionVigia.respaldo]: si ya se renovó hace poco y vuelve a pasar, el problema es del motor
//    en este teléfono: se pasa al de Android (ExoPlayer) hasta la próxima versión.
//
// Es lógica pura: el reproductor le da muestras y obedece.

import 'package:flutter/foundation.dart' show visibleForTesting;

enum AccionVigia { nada, renovar, respaldo }

class MuestraProceso {
  const MuestraProceso({required this.mapas, required this.hilos, required this.rssKb});
  final int mapas;
  final int hilos;
  final int rssKb;

  static MuestraProceso? de(Object? v) {
    if (v is! Map) return null;
    int n(Object? x) => (x as num?)?.toInt() ?? -1;
    final m = MuestraProceso(mapas: n(v['mapas']), hilos: n(v['hilos']), rssKb: n(v['rss_kb']));
    return m.mapas < 0 && m.hilos < 0 && m.rssKb < 0 ? null : m;
  }

  @override
  String toString() => 'mapas=$mapas hilos=$hilos rss=${rssKb ~/ 1024}MB';
}

class VigiaProceso {
  VigiaProceso({DateTime Function()? reloj}) : _reloj = reloj ?? DateTime.now;

  final DateTime Function() _reloj;

  /// Android corta en 65 530 mapas (vm.max_map_count): se actúa mucho antes.
  static const topeMapas = 40000;

  /// Una app de música normal anda por 100-250 hilos.
  static const topeHilos = 900;

  /// Más de 1,5 GB residentes es un escape seguro (la app anda por 200-400 MB).
  static const topeRssKb = 1536 * 1024;

  /// Crecer más que esto en [ventanaCrecimiento] sonando también es un escape.
  static const crecimientoMapas = 12000;
  static const crecimientoHilos = 300;
  static const ventanaCrecimiento = Duration(minutes: 3);

  /// Si tras renovar vuelve a pasar antes de esto, el motor no sirve en este teléfono.
  static const reincidencia = Duration(minutes: 10);

  final List<(DateTime, MuestraProceso)> _muestras = [];
  DateTime? _renovadoEn;

  /// Qué hacer con una muestra nueva (y por qué, para el registro).
  (AccionVigia, String) mirar(MuestraProceso m) {
    final ahora = _reloj();
    _muestras.add((ahora, m));
    _muestras.removeWhere((x) => ahora.difference(x.$1) > ventanaCrecimiento);
    String? por;
    if (m.mapas >= topeMapas) por = 'mapas de memoria: ${m.mapas}';
    if (m.hilos >= topeHilos) por ??= 'hilos: ${m.hilos}';
    if (m.rssKb >= topeRssKb) por ??= 'memoria: ${m.rssKb ~/ 1024} MB';
    if (por == null && _muestras.length >= 2) {
      final primera = _muestras.first.$2;
      if (primera.mapas >= 0 && m.mapas - primera.mapas >= crecimientoMapas) {
        por = 'los mapas crecen sin parar (${primera.mapas} → ${m.mapas})';
      } else if (primera.hilos >= 0 && m.hilos - primera.hilos >= crecimientoHilos) {
        por = 'los hilos crecen sin parar (${primera.hilos} → ${m.hilos})';
      }
    }
    if (por == null) return (AccionVigia.nada, '');
    final antes = _renovadoEn;
    _renovadoEn = ahora;
    // tras actuar se empieza a medir de cero (los motores nuevos parten limpios)
    _muestras.clear();
    if (antes != null && ahora.difference(antes) < reincidencia) return (AccionVigia.respaldo, por);
    return (AccionVigia.renovar, por);
  }

  @visibleForTesting
  int get muestras => _muestras.length;
}
