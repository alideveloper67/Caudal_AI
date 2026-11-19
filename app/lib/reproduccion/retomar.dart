// «Recordar dónde quedaste»: en canciones largas (sets, mixes, podcasts de
// más de 20 minutos) se guarda por dónde ibas para retomar desde ahí.
//
// Sin motor de sonido: el reproductor le da dos funciones para leer y escribir
// (la tabla `estado` de la colección) y esta decide qué vale la pena guardar.
import 'dart:math';

/// Desde cuánto dura una canción se le recuerda el punto.
const duracionMinimaRetomar = Duration(minutes: 20);

/// Cada cuánto se guarda el punto mientras suena.
const cadaGuardarRetomar = Duration(seconds: 15);

/// Si ibas por los primeros segundos, o ya casi acaba, no hay nada que retomar.
const margenInicioRetomar = Duration(seconds: 15);
const margenFinalRetomar = Duration(seconds: 30);

/// Cuántas canciones largas se recuerdan a la vez (las más recientes).
const maximoPuntosRetomar = 40;

/// El aviso que sale al retomar (el armazón le pone el botón «Desde el inicio»).
const avisoRetomado = 'Seguimos donde lo dejaste';

bool pideRetomar(Duration duracion) => duracion >= duracionMinimaRetomar;

/// [pos] si vale la pena guardarlo para una canción de [dur]; null si no.
Duration? puntoValido(Duration pos, Duration dur) {
  if (!pideRetomar(dur)) return null;
  if (pos < margenInicioRetomar) return null;
  if (pos > dur - margenFinalRetomar) return null;
  return pos;
}

class MemoriaRetomar {
  MemoriaRetomar({required this.leer, required this.escribir, DateTime Function()? ahora})
      : _ahora = ahora ?? DateTime.now;

  final Future<dynamic> Function() leer;
  final Future<void> Function(Map<String, dynamic>) escribir;
  final DateTime Function() _ahora;

  Map<String, dynamic>? _cache;

  Future<Map<String, dynamic>> _mapa() async {
    final c = _cache;
    if (c != null) return c;
    Map<String, dynamic> m = {};
    try {
      final d = await leer();
      if (d is Map) m = Map<String, dynamic>.from(d);
    } catch (_) {}
    return _cache = m;
  }

  /// Donde ibas en [clave], si todavía vale la pena retomarlo.
  Future<Duration?> punto(String clave, Duration dur) async {
    final e = (await _mapa())[clave];
    if (e is! Map || e['ms'] is! num) return null;
    return puntoValido(Duration(milliseconds: (e['ms'] as num).toInt()), dur);
  }

  /// Guarda [pos]. Si ya no vale (casi al final o al inicio), olvida el punto.
  Future<void> guardar(String clave, Duration pos, Duration dur) async {
    if (clave.isEmpty || !pideRetomar(dur)) return;
    final m = await _mapa();
    if (puntoValido(pos, dur) == null) return olvidar(clave);
    final previo = m[clave];
    if (previo is Map && previo['ms'] == pos.inMilliseconds) return;
    m[clave] = {'ms': pos.inMilliseconds, 'en': _ahora().millisecondsSinceEpoch};
    if (m.length > maximoPuntosRetomar) {
      final claves = m.keys.toList()
        ..sort((a, b) => _en(m[a]).compareTo(_en(m[b])));
      for (final k in claves.take(m.length - maximoPuntosRetomar)) {
        m.remove(k);
      }
    }
    await escribir(m);
  }

  Future<void> olvidar(String clave) async {
    final m = await _mapa();
    if (m.remove(clave) != null) await escribir(m);
  }

  static int _en(dynamic e) => e is Map && e['en'] is num ? max(0, (e['en'] as num).toInt()) : 0;
}
