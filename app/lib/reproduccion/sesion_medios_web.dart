import 'dart:async';
import 'dart:js_interop';
import 'dart:js_interop_unsafe';

import 'package:flutter/foundation.dart';
import 'package:web/web.dart' as web;

import '../nucleo/archivos_web.dart';
import '../nucleo/coleccion.dart';
import 'reproductor.dart';

/// Media Session: título, carátula y botones en la pantalla bloqueada.
///
/// Solo se publica lo que suena con el motor propio del navegador (la música de
/// la Comunidad y la de cada persona). Lo de YouTube lo lleva su reproductor.
class SesionMedios {
  SesionMedios._();

  static Reproductor? _r;
  static String _clave = '';
  static int _segundo = -10;
  static String _caratulaTemporal = '';

  static bool get oculta => web.document.hidden;

  static bool get esTelefono =>
      defaultTargetPlatform == TargetPlatform.android ||
      defaultTargetPlatform == TargetPlatform.iOS ||
      // los iPad se presentan como Mac, pero con pantalla táctil
      (defaultTargetPlatform == TargetPlatform.macOS && web.window.navigator.maxTouchPoints > 1);

  static web.MediaSession? get _sesion =>
      (web.window.navigator as JSObject).has('mediaSession') ? web.window.navigator.mediaSession : null;

  /// Una cuenta nueva trae otro reproductor: se suelta el anterior.
  static void enganchar(Reproductor r) {
    final viejo = _r;
    if (viejo != null) {
      viejo.removeListener(_publicar);
      viejo.posicion.removeListener(_publicarPosicion);
    }
    _r = r;
    _clave = '';
    r.addListener(_publicar);
    r.posicion.addListener(_publicarPosicion);
    _botones();
    _publicar();
  }

  static void _boton(String accion, void Function(JSObject) hacer) {
    try {
      _sesion?.setActionHandler(accion, ((JSObject d) => hacer(d)).toJS);
    } catch (_) {} // este navegador no conoce ese botón
  }

  static void _hacer(Future<void>? f) => unawaited(f ?? Future<void>.value());

  static void _botones() {
    _boton('play', (_) => _hacer(_r?.reanudar()));
    _boton('pause', (_) => _hacer(_r?.pausar()));
    _boton('stop', (_) => _hacer(_r?.pausar()));
    _boton('nexttrack', (_) => _hacer(_r?.siguiente()));
    _boton('previoustrack', (_) => _hacer(_r?.anterior()));
    _boton('seekto', (d) {
      final v = d['seekTime'];
      if (!v.isA<JSNumber>()) return;
      _hacer(_r?.buscar(Duration(milliseconds: ((v as JSNumber).toDartDouble * 1000).round())));
    });
  }

  static bool get _propio {
    final u = _r?.fuente?.url ?? '';
    return u.isNotEmpty && !u.startsWith('yt:');
  }

  static void _publicar() {
    final s = _sesion;
    final r = _r;
    if (s == null || r == null) return;
    final p = r.actual;
    if (p == null || !_propio) {
      if (_clave.isNotEmpty) {
        _clave = '';
        s.metadata = null;
        s.playbackState = 'none';
      }
      return;
    }
    s.playbackState = switch (r.estado) {
      EstadoRepro.sonando || EstadoRepro.cargando => 'playing',
      EstadoRepro.pausa => 'paused',
      EstadoRepro.parado => 'none',
    };
    final clave = '${p['clave']}|${p['titulo']}|${p['miniatura']}';
    if (clave != _clave) {
      _clave = clave;
      _segundo = -10;
      final m = '${p['miniatura'] ?? ''}';
      if (_caratulaTemporal.isNotEmpty) ArchivosWeb.soltarTemporal(_caratulaTemporal);
      _caratulaTemporal = '';
      var caratula = m.startsWith('http') ? m : '';
      final bytes = PortadasMem.bytes(m);
      if (bytes != null) caratula = _caratulaTemporal = ArchivosWeb.urlTemporal(bytes, 'image/jpeg');
      final album = p['album'];
      s.metadata = web.MediaMetadata(web.MediaMetadataInit(
        title: '${p['titulo'] ?? ''}',
        artist: '${p['artista'] ?? ''}',
        album: album is Map ? '${album['nombre'] ?? ''}' : '${album ?? ''}',
        artwork: [if (caratula.isNotEmpty) web.MediaImage(src: caratula)].toJS,
      ));
    }
    _publicarPosicion(forzar: true);
  }

  static void _publicarPosicion({bool forzar = false}) {
    final r = _r;
    if (r == null || !_propio) return;
    final seg = r.posicion.value.inSeconds;
    if (!forzar && (seg - _segundo).abs() < 5) return;
    _segundo = seg;
    final dur = r.duracion.value.inMilliseconds / 1000;
    if (dur <= 0) return;
    try {
      _sesion?.setPositionState(web.MediaPositionState(
          duration: dur,
          playbackRate: r.velocidad,
          position: (r.posicion.value.inMilliseconds / 1000).clamp(0.0, dur)));
    } catch (_) {}
  }

  // ------------------------------------------------------------ pantalla encendida

  static web.WakeLockSentinel? _bloqueo;
  static bool _quiere = false;
  static bool _escuchando = false;

  static bool get puedeDejarEncendida => (web.window.navigator as JSObject).has('wakeLock');

  /// Deja la pantalla encendida (Modo reposo). El navegador la suelta al salir
  /// de la página: al volver se pide otra vez.
  static Future<bool> pantallaEncendida(bool si) async {
    _quiere = si;
    if (!si) {
      final b = _bloqueo;
      _bloqueo = null;
      try {
        await b?.release().toDart;
      } catch (_) {}
      return false;
    }
    if (!puedeDejarEncendida) return false;
    if (!_escuchando) {
      _escuchando = true;
      web.document.addEventListener('visibilitychange', ((web.Event _) {
        if (_quiere && !oculta) unawaited(_pedir());
      }).toJS);
    }
    return _pedir();
  }

  static Future<bool> _pedir() async {
    try {
      final b = await web.window.navigator.wakeLock.request('screen').toDart;
      if (!_quiere) {
        await b.release().toDart;
        return false;
      }
      _bloqueo = b;
      return true;
    } catch (_) {
      return false; // batería baja, o el navegador no lo permite
    }
  }
}
