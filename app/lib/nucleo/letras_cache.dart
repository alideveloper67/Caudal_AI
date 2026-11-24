import 'dart:async';

import 'package:flutter/foundation.dart' show ChangeNotifier;

import 'catalogo.dart';
import 'coleccion.dart';
import 'cotejo_audio.dart';

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
  // v2: las de antes podían ser de otra canción (se elegían sin comprobar); se vuelven a pedir
  static const _clave = 'letras_cache_2';
  static const _claveAntes = 'letras_cache';
  static const _claveDesfases = 'letra_desfases';

  Coleccion? _col;
  // en orden de uso: la primera es la más antigua
  final Map<String, Map<String, dynamic>> _mem = {};

  /// Las de antes de la v2: solo se usan si no hay internet para volver a pedirlas.
  final Map<String, Map<String, dynamic>> _antes = {};

  /// Cuánto adelantó (+) o atrasó (-) la persona la letra de cada canción, en ms.
  final Map<String, int> _desfases = {};

  /// La duración de verdad de lo que suena (la pone el reproductor), para no fiarse de la anunciada.
  Duration? Function(String clave)? duracionReal;

  /// Avisa cuando la letra o el desfase de una canción cambian a mano.
  final CambiosDeLetra cambios = CambiosDeLetra();
  Future<void>? _cargando;
  Timer? _guardando;
  final Map<String, Future<Map<String, dynamic>?>> _enVuelo = {};

  /// De dónde salen las letras que faltan (se cambia en las pruebas).
  Future<Map<String, dynamic>> Function(Map<String, dynamic>)? cargador;

  Future<Map<String, dynamic>> _pedir(Map<String, dynamic> p) async {
    final propio = cargador;
    if (propio != null) return propio(p);
    final clave = '${p['clave'] ?? ''}';
    var d = duracionReal?.call(clave);
    // sin duración anunciada (un archivo propio): se espera un momento a saber la de verdad
    for (var i = 0; i < 8 && d == Duration.zero; i++) {
      await Future<void>.delayed(const Duration(milliseconds: 400));
      d = duracionReal?.call(clave);
    }
    return Catalogo.letras(p, duracion: d);
  }

  int get cuantas => _mem.length;

  /// Enlaza el almacén con la colección de la cuenta activa (al cambiar de cuenta se vacía).
  void vincular(Coleccion? c) {
    if (identical(_col, c)) return;
    _guardando?.cancel();
    _guardando = null;
    _col = c;
    _mem.clear();
    _antes.clear();
    _desfases.clear();
    _cotejadas.clear();
    _enVuelo.clear();
    _cargando = null;
    if (c != null) _cargando = _leer(c);
  }

  Future<void> _leer(Coleccion c) async {
    try {
      final x = await c.estado(_claveDesfases);
      if (identical(_col, c) && x is Map) {
        for (final e in x.entries) {
          if (e.value is num) _desfases.putIfAbsent('${e.key}', () => (e.value as num).toInt());
        }
        if (_desfases.isNotEmpty) cambios.avisar();
      }
    } catch (_) {}
    try {
      final v = await c.estado(_claveAntes);
      if (identical(_col, c) && v is Map) {
        for (final e in v.entries) {
          if (e.value is Map) _antes['${e.key}'] = Map<String, dynamic>.from(e.value as Map);
        }
      }
    } catch (_) {}
    try {
      final d = await c.estado(_clave);
      if (!identical(_col, c) || d is! Map) return;
      for (final e in d.entries) {
        final v = e.value;
        if (v is Map && !_mem.containsKey('${e.key}')) _mem['${e.key}'] = Map<String, dynamic>.from(v);
      }
    } catch (_) {}
    try {
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
  Map<String, Map<String, dynamic>> get todas => Map.unmodifiable({..._antes, ..._mem});

  static bool _vacia(Map<String, dynamic> l) =>
      lineasConTiempo(l).isEmpty && '${l['texto'] ?? ''}'.trim().isEmpty;

  /// Guarda una letra (las vacías no: pueden ser un fallo de red y se volverían a intentar).
  void guardar(String clave, Map<String, dynamic> letra) {
    if (clave.isEmpty || _vacia(letra)) return;
    // solo lo que se usa: líneas con tiempo y texto plano
    final lineas = [for (final x in lineasConTiempo(letra)) [x.$1, x.$2]];
    final texto = '${letra['texto'] ?? ''}';
    final ajustables = [for (final x in lineasConTiempo({'lineas': letra['ajustables']})) [x.$1, x.$2]];
    _mem.remove(clave);
    _antes.remove(clave);
    _mem[clave] = {
      'lineas': lineas,
      'texto': texto.isNotEmpty ? texto : [for (final x in lineas) x[1]].join('\n'),
      if (ajustables.isNotEmpty) 'ajustables': ajustables,
      if (letra['elegida'] == true) 'elegida': true,
      // pendiente de comparar el sonido con la canción oficial
      if ('${letra['ref'] ?? ''}'.isNotEmpty && letra['elegida'] != true) 'ref': '${letra['ref']}',
    };
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
    if (hecha != null) {
      if (red) unawaited(_cotejar(pista));
      return hecha;
    }
    if (!red) return null;
    return _enVuelo[clave] ??= () async {
      try {
        final l = Map<String, dynamic>.from(await _pedir(pista));
        if (_vacia(l)) return l['sin_red'] == true ? _antes[clave] : null;
        // mientras se pedía, la persona pudo elegir otra
        final elegida = de(clave);
        if (elegida != null) return elegida;
        guardar(clave, l);
        unawaited(_cotejar(pista));
        return de(clave);
      } catch (_) {
        return _antes[clave];
      } finally {
        _enVuelo.remove(clave);
      }
    }();
  }

  // ------------------------------------------------------------ ponerla a tiempo por el sonido

  /// Compara el sonido de lo que suena con el de la canción oficial (lo pone el reproductor; null donde no
  /// se puede, como en la web).
  Future<List<TramoCotejo>?> Function(Map<String, dynamic> pista, String ref)? cotejador;

  final Set<String> _cotejadas = {};
  final Set<String> _midiendo = {};

  /// ¿Se está poniendo a tiempo la letra de [clave]?
  bool midiendo(String clave) => _midiendo.contains(clave);

  Future<void> _cotejar(Map<String, dynamic> pista) async {
    final clave = '${pista['clave'] ?? ''}';
    final c = cotejador;
    final l = _mem[clave];
    final ref = '${l?['ref'] ?? ''}';
    final suyas = lineasConTiempo({'lineas': l?['ajustables']});
    if (c == null || l == null || ref.isEmpty || suyas.isEmpty || !_cotejadas.add(clave)) return;
    final col = _col;
    _midiendo.add(clave);
    cambios.avisar();
    try {
      final tramos = await c(pista, ref);
      // mientras tanto pudo cambiar la cuenta o elegirse otra letra
      if (tramos == null || tramos.isEmpty || !identical(col, _col) || !identical(_mem[clave], l)) return;
      guardar(clave, {
        'lineas': [for (final x in CotejoAudio.colocar(suyas, tramos)) [x.$1, x.$2]],
        'texto': l['texto'],
      });
    } catch (_) {
      // no se pudo comparar: se queda como estaba
    } finally {
      _midiendo.remove(clave);
      cambios.avisar();
    }
  }

  // ------------------------------------------------------------ a mano

  /// La letra que eligió la persona para [clave]: manda sobre cualquier otra.
  void elegir(String clave, Map<String, dynamic> letra) {
    guardar(clave, {...letra, 'elegida': true});
    cambios.avisar();
  }

  /// Olvida la letra de [clave]: la próxima vez se vuelve a buscar.
  void olvidar(String clave) {
    _mem.remove(clave);
    _cotejadas.remove(clave);
    _antes.remove(clave);
    if (_desfases.remove(clave) != null) _guardarDesfases();
    _programarGuardado();
    cambios.avisar();
  }

  /// Lo que hay que mover el reloj de la letra de [clave]: lo suyo y lo general.
  int desfase(String clave) => desfasePropio(clave) + desfaseGeneral;

  int desfasePropio(String clave) => _desfases[clave] ?? 0;

  /// Lo que se mueve la letra de todas las canciones (auriculares que suenan con retraso).
  int get desfaseGeneral => _desfases[_todas] ?? 0;
  void ponerDesfaseGeneral(int ms) => ponerDesfase(_todas, ms.clamp(-3000, 3000));
  static const _todas = '*';

  /// Adelanta (+) o atrasa (-) la letra de [clave] y lo recuerda.
  void ponerDesfase(String clave, int ms) {
    if (clave.isEmpty) return;
    _desfases.remove(clave);
    final n = ms.clamp(-topeDesfase, topeDesfase);
    if (n != 0) _desfases[clave] = n;
    while (_desfases.length > 500) {
      _desfases.remove(_desfases.keys.firstWhere((k) => k != _todas));
    }
    _guardarDesfases();
    cambios.avisar();
  }

  /// Hasta cuánto se puede mover (un videoclip puede empezar minutos después).
  static const topeDesfase = 180000;

  Timer? _guardandoDesfases;
  void _guardarDesfases() {
    final c = _col;
    if (c == null) return;
    _guardandoDesfases?.cancel();
    _guardandoDesfases = Timer(const Duration(milliseconds: 800), () {
      if (!identical(_col, c)) return;
      c.guardarEstado(_claveDesfases, Map<String, int>.from(_desfases)).catchError((_) {});
    });
  }
}

class CambiosDeLetra extends ChangeNotifier {
  void avisar() => notifyListeners();
}
