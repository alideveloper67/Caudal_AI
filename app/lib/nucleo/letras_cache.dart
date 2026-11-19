import 'dart:async';

import 'catalogo.dart';
import 'coleccion.dart';

/// Las líneas con tiempo de una letra: `[[ms, texto], ...]` -> `(ms, texto)`.
List<(int, String)> lineasConTiempo(Map<String, dynamic>? l) => [
      for (final x in (l?['lineas'] is List ? l!['lineas'] as List : const []))
        if (x is List && x.length >= 2)
          (x[0] is num ? (x[0] as num).toInt() : int.tryParse('${x[0]}') ?? 0, '${x[1]}')
    ];

/// Las letras que ya se vieron, guardadas en el teléfono (hasta [tope], las más recientes).
///
/// Sirven para tres cosas sin gastar red: buscar en las letras de lo que escuchaste
/// («¿Qué canción era?»), mostrar la línea actual en la pantalla de bloqueo y que la
/// pantalla de la letra abra al instante. Una sola instancia ([LetrasCache.i]).
class LetrasCache {
  LetrasCache._();
  static final LetrasCache i = LetrasCache._();

  /// Para pruebas: una instancia suelta (sin compartir estado con la de la app).
  LetrasCache.prueba();

  static const tope = 250;
  static const _clave = 'letras_cache';

  Coleccion? _col;
  // en orden de uso: la primera es la más antigua
  final Map<String, Map<String, dynamic>> _mem = {};
  Future<void>? _cargando;
  Timer? _guardando;
  final Map<String, Future<Map<String, dynamic>?>> _enVuelo = {};

  /// De dónde salen las letras que faltan (se cambia en las pruebas).
  Future<Map<String, dynamic>> Function(Map<String, dynamic>) cargador = Catalogo.letras;

  int get cuantas => _mem.length;

  /// Enlaza el almacén con la colección de la cuenta activa (al cambiar de cuenta se vacía).
  void vincular(Coleccion? c) {
    if (identical(_col, c)) return;
    _guardando?.cancel();
    _guardando = null;
    _col = c;
    _mem.clear();
    _enVuelo.clear();
    _cargando = null;
    if (c != null) _cargando = _leer(c);
  }

  Future<void> _leer(Coleccion c) async {
    try {
      final d = await c.estado(_clave);
      if (!identical(_col, c) || d is! Map) return;
      for (final e in d.entries) {
        final v = e.value;
        if (v is Map && !_mem.containsKey('${e.key}')) _mem['${e.key}'] = Map<String, dynamic>.from(v);
      }
      while (_mem.length > tope) {
        _mem.remove(_mem.keys.first);
      }
    } catch (_) {}
  }

  /// Espera a que se lea lo guardado (para buscar con todo a la vista).
  Future<void> listo() => _cargando ?? Future.value();

  /// Lo que se sabe de una canción, sin pedir nada a la red.
  Map<String, dynamic>? de(String clave) {
    final l = _mem.remove(clave);
    if (l == null) return null;
    _mem[clave] = l; // pasa a ser la más reciente
    return l;
  }

  /// Todas las letras guardadas (clave -> letra), sin cambiar su orden de uso.
  Map<String, Map<String, dynamic>> get todas => Map.unmodifiable(_mem);

  static bool _vacia(Map<String, dynamic> l) =>
      lineasConTiempo(l).isEmpty && '${l['texto'] ?? ''}'.trim().isEmpty;

  /// Guarda una letra (las vacías no: pueden ser un fallo de red y se volverían a intentar).
  void guardar(String clave, Map<String, dynamic> letra) {
    if (clave.isEmpty || _vacia(letra)) return;
    // solo lo que se usa: líneas con tiempo y texto plano
    final lineas = [for (final x in lineasConTiempo(letra)) [x.$1, x.$2]];
    final texto = '${letra['texto'] ?? ''}';
    _mem.remove(clave);
    _mem[clave] = {'lineas': lineas, 'texto': texto.isNotEmpty ? texto : [for (final x in lineas) x[1]].join('\n')};
    while (_mem.length > tope) {
      _mem.remove(_mem.keys.first);
    }
    _programarGuardado();
  }

  void _programarGuardado() {
    final c = _col;
    if (c == null) return;
    _guardando?.cancel();
    // se junta lo de varios minutos de escucha en una sola escritura
    _guardando = Timer(const Duration(seconds: 4), () {
      _guardando = null;
      if (!identical(_col, c)) return;
      c.guardarEstado(_clave, Map<String, dynamic>.from(_mem)).catchError((_) {});
    });
  }

  /// La letra de [pista]: de lo guardado y, si no está y [red], de internet.
  /// Devuelve null si no hay (o no se pudo pedir).
  Future<Map<String, dynamic>?> obtener(Map<String, dynamic> pista, {bool red = true}) async {
    final clave = '${pista['clave'] ?? ''}';
    if (clave.isEmpty) return null;
    await listo();
    final hecha = de(clave);
    if (hecha != null) return hecha;
    if (!red) return null;
    return _enVuelo[clave] ??= () async {
      try {
        final l = Map<String, dynamic>.from(await cargador(pista));
        if (_vacia(l)) return null;
        guardar(clave, l);
        return de(clave);
      } catch (_) {
        return null;
      } finally {
        _enVuelo.remove(clave);
      }
    }();
  }
}
