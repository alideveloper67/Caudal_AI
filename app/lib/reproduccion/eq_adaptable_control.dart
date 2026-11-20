// ignore_for_file: experimental_member_use

import 'dart:async';
import 'dart:convert';

import 'package:audio_session/audio_session.dart';
import 'package:flutter/foundation.dart';

import '../nucleo/ajustes.dart';
import '../nucleo/coleccion.dart';
import '../nucleo/eq_adaptable.dart';
import '../nucleo/premium.dart';
import '../nucleo/premium_letras.dart';
import 'reproductor.dart';

/// De los dispositivos de salida que dice el sistema, por dónde suena ahora (null si no se sabe).
SalidaAudio? salidaDeDispositivos(Iterable<AudioDeviceType> tipos) {
  var bocina = false, audifonos = false, bluetooth = false;
  for (final t in tipos) {
    switch (t) {
      case AudioDeviceType.bluetoothA2dp || AudioDeviceType.bluetoothSco || AudioDeviceType.bluetoothLe:
        bluetooth = true;
      case AudioDeviceType.wiredHeadphones || AudioDeviceType.wiredHeadset || AudioDeviceType.usbAudio:
        audifonos = true;
      case AudioDeviceType.builtInSpeaker ||
            AudioDeviceType.lineAnalog ||
            AudioDeviceType.lineDigital ||
            AudioDeviceType.hdmi ||
            AudioDeviceType.hdmiArc:
        bocina = true;
      default:
        break;
    }
  }
  // lo que está conectado le gana a la bocina del propio teléfono
  if (bluetooth) return SalidaAudio.bluetooth;
  if (audifonos) return SalidaAudio.audifonos;
  if (bocina) return SalidaAudio.bocina;
  return null;
}

/// Pone el ecualizador que toca según la salida (audífonos, bocina, Bluetooth), el género o el
/// artista (donadores). Cuando ninguna regla aplica devuelve el ecualizador a como lo dejó la
/// persona. Una sola instancia ([ControlEqAdaptable.i]) enlazada al reproductor de la cuenta.
class ControlEqAdaptable extends ChangeNotifier {
  ControlEqAdaptable._();
  static final ControlEqAdaptable i = ControlEqAdaptable._();

  /// Para pruebas: una instancia suelta, sin sistema de audio.
  @visibleForTesting
  ControlEqAdaptable.prueba({bool Function()? donador}) : _donador = donador;

  static const _clave = 'eq_adaptable';
  static const _claveBase = 'eq_adaptable_base';

  bool Function()? _donador;
  bool get donador => (_donador ?? esPremiumLetras)();

  Reproductor? _r;
  Ajustes? _a;
  Coleccion? _c;
  StreamSubscription<Set<AudioDevice>>? _sub;
  String _ultimaClave = '';
  String? _aplicado; // el ajuste que pusimos (null = no hemos tocado nada)
  Map<String, Object?>? _base; // cómo estaba el ecualizador antes de tocarlo
  bool _ocupado = false;
  bool _otraVez = false;

  PerfilesEq perfiles = PerfilesEq();

  /// Por dónde suena ahora según el sistema (null si no se puede saber en este equipo).
  SalidaAudio? detectada;

  /// ¿El sistema deja detectar la salida? Si no, la persona elige el perfil a mano.
  bool get puedeDetectar => detectada != null;

  /// El ajuste puesto ahora por esta función (null = ninguno).
  String? get aplicado => _aplicado;

  /// La canción que suena y de dónde viene (para recordarle un ajuste a su artista o género).
  Json? get pistaActual => _r?.actual;
  Json? get contextoActual => _r?.contexto;

  SalidaAudio? get salidaActual => perfiles.salidaEfectiva(detectada);

  // ------------------------------------------------------------ enlace

  /// Lo engancha al reproductor y a los ajustes de la cuenta (se llama al cambiar de cuenta).
  ///
  /// [escuchar] en falso no se suscribe a los dispositivos (solo para pruebas de pantalla, donde
  /// un flujo abierto deja colgado el reloj falso del banco de pruebas).
  Future<void> enlazar(Reproductor r, {Stream<Set<AudioDevice>>? dispositivos, bool escuchar = true}) async {
    if (identical(_r, r)) return;
    _r?.removeListener(_alReproductor);
    Premium.i.removeListener(_alReproductor);
    _r = r;
    _a = r.ajustes;
    _c = r.coleccion;
    _aplicado = null;
    _base = null;
    _ultimaClave = '';
    r.addListener(_alReproductor);
    Premium.i.addListener(_alReproductor);
    await _leer();
    if (escuchar) _escucharSalida(dispositivos);
    await reaplicar();
  }

  void _escucharSalida(Stream<Set<AudioDevice>>? inyectado) {
    unawaited(_sub?.cancel());
    _sub = null;
    try {
      final flujo = inyectado ?? _flujoSistema();
      _sub = flujo.listen((ds) {
        final nueva = salidaDeDispositivos([for (final d in ds) if (d.isOutput) d.type]);
        if (nueva == detectada) return;
        detectada = nueva;
        notifyListeners();
        unawaited(reaplicar());
      }, onError: (_) {});
    } catch (_) {
      // en este equipo no se puede saber: se elige el perfil a mano
    }
  }

  Stream<Set<AudioDevice>> _flujoSistema() async* {
    final s = await AudioSession.instance;
    yield await s.getDevices();
    yield* s.devicesStream;
  }

  void _alReproductor() {
    final p = _r?.actual;
    final clave = p == null ? '' : '${p['clave']}';
    if (clave == _ultimaClave) return;
    _ultimaClave = clave;
    unawaited(reaplicar());
  }

  // ------------------------------------------------------------ guardado

  Future<void> _leer() async {
    perfiles = PerfilesEq();
    final c = _c;
    if (c == null) return;
    try {
      perfiles = PerfilesEq.desde(await c.estado(_clave));
      final b = await c.estado(_claveBase);
      if (b is Map && b['b'] is List) {
        _base = Map<String, Object?>.from(b);
        _aplicado = '${b['aplicado'] ?? ''}'.isEmpty ? null : '${b['aplicado']}';
      }
    } catch (_) {}
  }

  Future<void> _guardar() async {
    try {
      await _c?.guardarEstado(_clave, perfiles.aJson());
    } catch (_) {}
  }

  Future<void> _guardarBase() async {
    try {
      await _c?.guardarEstado(_claveBase, _base == null ? null : {..._base!, 'aplicado': _aplicado ?? ''});
    } catch (_) {}
  }

  /// Cambia las reglas desde la pantalla: se guardan y se aplican enseguida.
  Future<void> cambiar(void Function(PerfilesEq p) cambio) async {
    cambio(perfiles);
    notifyListeners();
    await _guardar();
    await reaplicar();
  }

  // ------------------------------------------------------------ aplicar

  /// El ajuste que tocaría ahora mismo (null si ninguno).
  String? get perfilDeAhora {
    final p = _r?.actual;
    if (p == null) return null;
    return perfiles.perfilPara(p, detectada, contexto: _r?.contexto);
  }

  String? get motivoDeAhora {
    final p = _r?.actual;
    return p == null ? null : perfiles.motivoPara(p, detectada, contexto: _r?.contexto);
  }

  /// Pone (o quita) el ecualizador que toca. Si llega otro cambio mientras trabaja, lo repite al terminar.
  Future<void> reaplicar() async {
    if (_ocupado) {
      _otraVez = true;
      return;
    }
    _ocupado = true;
    try {
      do {
        _otraVez = false;
        await _aplicarAhora();
      } while (_otraVez);
    } finally {
      _ocupado = false;
    }
  }

  List<int>? _bandasDe(String nombre) => presetsEq[nombre];

  Future<void> _aplicarAhora() async {
    final a = _a, r = _r;
    if (a == null || r == null) return;
    // el «Modo gamer» tiene su propio sonido: no se pisa
    if (a.sino('gamer_activo')) return;
    final quiere = donador ? perfilDeAhora : null;
    final bandas = quiere == null ? null : _bandasDe(quiere);
    if (quiere == null || bandas == null) {
      await _devolver(a);
      return;
    }
    if (_aplicado == quiere && _sigueIgual(a, bandas, quiere)) return;
    if (_aplicado != null && !_sigueIgual(a, _bandasDe(_aplicado!) ?? const [], _aplicado!)) {
      // la persona tocó el ecualizador a mano mientras estaba puesto: eso manda y lo suyo es lo "base"
      _base = null;
      _aplicado = null;
    }
    _base ??= {'e': a.sino('ecualizador'), 'b': a.bandasEq, 'p': a.texto('eq_preset')};
    _aplicado = quiere;
    await a.poner('ecualizador', true, avisar: false);
    await a.poner('eq_bandas', bandas, avisar: false);
    await _guardarBase();
    await _sonar(r);
    await a.poner('eq_preset', quiere); // al final: avisa a las pantallas de que cambió el sonido
    notifyListeners();
  }

  bool _sigueIgual(Ajustes a, List<int> bandas, String nombre) =>
      a.sino('ecualizador') && a.texto('eq_preset') == nombre && listEquals(a.bandasEq, bandas);

  /// Devuelve el ecualizador a como estaba, si lo habíamos tocado y la persona no lo cambió después.
  Future<void> _devolver(Ajustes a) async {
    final aplicado = _aplicado, base = _base;
    if (aplicado == null || base == null) {
      if (_aplicado != null || _base != null) {
        _aplicado = null;
        _base = null;
        await _guardarBase();
      }
      return;
    }
    final intacto = _sigueIgual(a, _bandasDe(aplicado) ?? const [], aplicado);
    _aplicado = null;
    _base = null;
    if (intacto) {
      await a.poner('ecualizador', base['e'] == true, avisar: false);
      await a.poner('eq_bandas', [for (final b in (base['b'] as List)) (b as num).toInt()], avisar: false);
      final r = _r;
      if (r != null) await _sonar(r);
      await a.poner('eq_preset', '${base['p'] ?? 'Plano'}');
    }
    await _guardarBase();
    notifyListeners();
  }

  Future<void> _sonar(Reproductor r) async {
    try {
      await r.aplicarSonido();
    } catch (_) {/* sin el filtro en este teléfono, suena igual */}
  }

  /// Para pruebas: suelta lo enlazado.
  @visibleForTesting
  Future<void> soltar() async {
    _r?.removeListener(_alReproductor);
    Premium.i.removeListener(_alReproductor);
    await _sub?.cancel();
    _sub = null;
    _r = null;
    _a = null;
    _c = null;
  }

  @override
  void dispose() {
    unawaited(soltar());
    super.dispose();
  }

  /// El texto de lo guardado (para ver qué hay en pruebas).
  @visibleForTesting
  String get guardadoComoTexto => jsonEncode(perfiles.aJson());
}
