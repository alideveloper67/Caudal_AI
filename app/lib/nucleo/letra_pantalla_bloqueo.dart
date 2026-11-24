import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../reproduccion/reproductor.dart';
import 'letra_bloqueo.dart';
import 'letras_cache.dart';
import 'plataforma.dart';

/// «Letra en la pantalla bloqueada» (Android): el verso que suena, visible sin desbloquear.
///
/// Va en una notificación propia, pública en el bloqueo (LetraPantallaBloqueo.kt), que se cambia solo
/// cuando cambia el verso; al tocarla se abre una vista grande sobre el bloqueo con el verso y el
/// siguiente. Se activa en Ajustes. Lo de aquí decide QUÉ se enseña y CUÁNDO; Android, cómo.
class LetraEnBloqueo {
  LetraEnBloqueo({PuenteLetraBloqueo? puente, this.cargarLetra = _deLaCache})
      : puente = puente ?? const PuenteLetraBloqueo();

  static final LetraEnBloqueo i = LetraEnBloqueo();

  static const clavePref = 'letra_pantalla_bloqueo';

  final PuenteLetraBloqueo puente;

  /// De dónde sale la letra (la caché de letras de Caudal, que la pide a internet si no la tiene).
  final Future<Map<String, dynamic>?> Function(Map<String, dynamic> pista) cargarLetra;

  static Future<Map<String, dynamic>?> _deLaCache(Map<String, dynamic> p) => LetrasCache.i.obtener(p);

  /// Encendida o no (Ajustes). Por defecto, apagada: es una notificación más en el bloqueo.
  final ValueNotifier<bool> activa = ValueNotifier(false);

  bool _leida = false;

  Future<void> leerAjuste() async {
    try {
      final p = await SharedPreferences.getInstance();
      activa.value = p.getBool(clavePref) ?? false;
    } catch (_) {}
    _leida = true;
  }

  Future<void> poner(bool si) async {
    activa.value = si;
    try {
      final p = await SharedPreferences.getInstance();
      await p.setBool(clavePref, si);
    } catch (_) {}
    if (si) {
      _clave = ''; // se vuelve a pedir la letra de lo que suena
      _actualizar();
    } else {
      _quitar();
    }
  }

  // ------------------------------------------------------------ enganche

  Listenable? _cambios;
  ValueListenable<Duration>? _posicion;
  Map<String, dynamic>? Function()? _actual;
  bool Function()? _sonando;
  bool Function()? _parado;

  /// Engancha al reproductor (se puede llamar otra vez al cambiar de cuenta).
  void enlazar(Reproductor r) => enlazarCon(
        cambios: r,
        posicion: r.posicion,
        actual: () => r.actual,
        sonando: () => r.estado == EstadoRepro.sonando,
        parado: () => r.estado == EstadoRepro.parado,
      );

  void enlazarCon({
    required Listenable cambios,
    required ValueListenable<Duration> posicion,
    required Map<String, dynamic>? Function() actual,
    required bool Function() sonando,
    required bool Function() parado,
  }) {
    soltar();
    _cambios = cambios..addListener(_actualizar);
    _posicion = posicion..addListener(_alMoverse);
    _actual = actual;
    _sonando = sonando;
    _parado = parado;
    activa.addListener(_actualizar);
    if (!_leida) {
      unawaited(leerAjuste().then((_) => _actualizar()));
    } else {
      _actualizar();
    }
  }

  void soltar() {
    _cambios?.removeListener(_actualizar);
    _posicion?.removeListener(_alMoverse);
    activa.removeListener(_actualizar);
    _cambios = null;
    _posicion = null;
    _quitar();
  }

  // ------------------------------------------------------------ estado

  String _clave = '';
  String _pedida = '';
  List<(int, String)> _lineas = const [];
  int _indice = -2;
  bool _ultimoSonando = false;
  bool _puesta = false;

  /// Lo último que se mandó (para las pruebas y para no repetir).
  @visibleForTesting
  Map<String, Object?>? ultimo;

  void _actualizar() {
    final actual = _actual?.call();
    if (!activa.value || actual == null || (_parado?.call() ?? true)) {
      _quitar();
      if (actual == null) _clave = '';
      return;
    }
    final clave = '${actual['clave'] ?? ''}';
    if (clave != _clave) {
      _clave = clave;
      _lineas = const [];
      _indice = -2;
      _quitar();
    }
    if (_pedida != clave && clave.isNotEmpty) {
      _pedida = clave;
      unawaited(_cargar(Map<String, dynamic>.from(actual)));
    }
    final sonando = _sonando?.call() ?? false;
    if (sonando != _ultimoSonando && _puesta) {
      _ultimoSonando = sonando;
      _mandar(forzar: true);
    }
    _ultimoSonando = sonando;
    _alMoverse();
  }

  Future<void> _cargar(Map<String, dynamic> pista) async {
    final clave = '${pista['clave'] ?? ''}';
    try {
      final l = await cargarLetra(pista);
      if (clave != _clave) return;
      _lineas = l == null ? const [] : (lineasConTiempo(l)..sort((a, b) => a.$1.compareTo(b.$1)));
      _indice = -2;
      _alMoverse();
    } catch (_) {
      // sin letra: no se enseña nada
    }
  }

  void _alMoverse() {
    if (!activa.value || _lineas.isEmpty) return;
    final ms = (_posicion?.value.inMilliseconds ?? 0) + LetrasCache.i.desfase(_clave);
    final i = LetraBloqueo.indiceEn(_lineas, ms);
    if (i == _indice && _puesta) return;
    _indice = i;
    _mandar();
  }

  void _mandar({bool forzar = false}) {
    final actual = _actual?.call();
    if (actual == null || _lineas.isEmpty) return;
    final i = _indice;
    final linea = i < 0 ? '' : _lineas[i].$2.trim();
    final siguiente = i + 1 < _lineas.length ? _lineas[i + 1].$2.trim() : '';
    final datos = <String, Object?>{
      'titulo': '${actual['titulo'] ?? ''}',
      'artista': '${actual['artista'] ?? ''}',
      // antes del primer verso se enseña el que viene, para que no quede en blanco
      'linea': linea.isEmpty ? '♪' : linea,
      'siguiente': linea.isEmpty && i < 0 && _lineas.isNotEmpty ? _lineas.first.$2.trim() : siguiente,
      'sonando': _sonando?.call() ?? false,
    };
    if (!forzar && mapEquals(datos, ultimo)) return;
    ultimo = datos;
    _puesta = true;
    unawaited(puente.mostrar(datos));
  }

  void _quitar() {
    if (!_puesta) return;
    _puesta = false;
    ultimo = null;
    unawaited(puente.quitar());
  }
}

/// El puente con LetraPantallaBloqueo.kt (solo Android).
class PuenteLetraBloqueo {
  const PuenteLetraBloqueo();

  static const _canal = MethodChannel('caudal/letra_bloqueo');

  Future<void> mostrar(Map<String, Object?> datos) async {
    if (!Plataforma.esAndroid) return;
    try {
      await _canal.invokeMethod('mostrar', datos);
    } catch (_) {}
  }

  Future<void> quitar() async {
    if (!Plataforma.esAndroid) return;
    try {
      await _canal.invokeMethod('quitar');
    } catch (_) {}
  }
}
