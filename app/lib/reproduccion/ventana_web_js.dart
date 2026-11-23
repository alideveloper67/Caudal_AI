import 'dart:async';
import 'dart:js_interop';
import 'dart:js_interop_unsafe';

import 'package:flutter/foundation.dart';
import 'package:web/web.dart' as web;

import '../nucleo/archivos_web.dart';
import '../nucleo/coleccion.dart';
import 'reproductor.dart';

class VentanaWeb {
  VentanaWeb._();

  // ------------------------------------------------------------ pantalla completa

  static bool get puedePantallaCompleta => web.document.fullscreenEnabled;

  /// Sigue al navegador (que también la quita con Esc).
  static final ValueNotifier<bool> completa = () {
    final v = ValueNotifier(web.document.fullscreenElement != null);
    web.document.addEventListener('fullscreenchange',
        ((web.Event _) => v.value = web.document.fullscreenElement != null).toJS);
    return v;
  }();

  static Future<void> pantallaCompleta(bool si) async {
    try {
      if (si) {
        if (web.document.fullscreenElement == null) await web.document.documentElement!.requestFullscreen().toDart;
      } else if (web.document.fullscreenElement != null) {
        await web.document.exitFullscreen().toDart;
      }
    } catch (_) {} // iPhone no deja: la vista ocupa la página y ya
  }

  // ------------------------------------------------------------ mini reproductor

  static JSObject? get _pip {
    final w = web.window as JSObject;
    return w.has('documentPictureInPicture') ? w['documentPictureInPicture'] as JSObject : null;
  }

  static bool get puedeMini => _pip != null;

  static final ValueNotifier<bool> miniAbierto = ValueNotifier(false);
  static web.Window? _ventana;
  static Reproductor? _r;
  static String _urlPortada = '';
  static String _refPortada = '-';
  static final Map<String, web.HTMLElement> _e = {};

  /// Abre o cierra la ventanita. Devuelve el motivo si no se puede.
  static Future<String?> alternarMini(Reproductor r) async {
    final abierta = _ventana;
    if (abierta != null) {
      _cerrado();
      abierta.close();
      return null;
    }
    final pip = _pip;
    if (pip == null) return 'El mini reproductor necesita Chrome o Edge en la computadora.';
    if (r.actual == null) return 'Pon algo a sonar para abrir el mini reproductor.';
    if (r.fuente?.esYouTubeWeb ?? false) {
      return 'Con YouTube no se puede: su video tiene que verse. Funciona con tu música y la de la comunidad.';
    }
    try {
      final op = JSObject();
      op['width'] = 360.toJS;
      op['height'] = 132.toJS;
      final w = await pip.callMethod<JSPromise<JSObject>>('requestWindow'.toJS, op).toDart as web.Window;
      _ventana = w;
      _r = r;
      _refPortada = '-';
      _montar(w);
      r.addListener(_pintar);
      r.posicion.addListener(_avance);
      w.addEventListener('pagehide', ((web.Event _) => _cerrado()).toJS);
      miniAbierto.value = true;
      _pintar();
      return null;
    } catch (_) {
      return 'El navegador no dejó abrir el mini reproductor.';
    }
  }

  static void _cerrado() {
    if (_ventana == null) return;
    _r?.removeListener(_pintar);
    _r?.posicion.removeListener(_avance);
    _r = null;
    _ventana = null;
    _e.clear();
    if (_urlPortada.startsWith('blob:')) ArchivosWeb.soltarTemporal(_urlPortada);
    _urlPortada = '';
    miniAbierto.value = false;
  }

  static web.HTMLElement _crear(web.Document d, String etiqueta, String clase, [web.Node? padre]) {
    final e = d.createElement(etiqueta) as web.HTMLElement;
    e.className = clase;
    padre?.appendChild(e);
    return e;
  }

  static const _svg = {
    'ant': 'M6 6h2v12H6zm3.5 6 8.5 6V6z',
    'play': 'M8 5v14l11-7z',
    'pausa': 'M6 19h4V5H6zm8-14v14h4V5z',
    'sig': 'M6 18l8.5-6L6 6zM16 6v12h2V6z',
  };

  static web.SVGElement _icono(web.Document d, String cual) {
    const ns = 'http://www.w3.org/2000/svg';
    final s = d.createElementNS(ns, 'svg') as web.SVGElement;
    s.setAttribute('viewBox', '0 0 24 24');
    final p = d.createElementNS(ns, 'path');
    p.setAttribute('d', _svg[cual]!);
    s.appendChild(p);
    return s;
  }

  static void _montar(web.Window w) {
    final d = w.document;
    d.title = 'Caudal';
    final st = d.createElement('style');
    st.textContent = '''
*{box-sizing:border-box;margin:0}
body{background:#0B0D12;color:#F3F5F9;font-family:system-ui,sans-serif;height:100vh;overflow:hidden;display:flex;flex-direction:column}
.fila{flex:1;display:flex;gap:12px;align-items:center;padding:10px 12px;min-height:0}
.foto{height:100%;max-height:96px;aspect-ratio:1;border-radius:10px;background:#1B1F27 center/cover}
.datos{flex:1;min-width:0}
.t{font-weight:800;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.a{color:#A9B1C0;font-size:12.5px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.b{display:flex;gap:4px;margin-top:6px}
button{width:36px;height:36px;border:0;border-radius:50%;background:transparent;cursor:pointer}
button:hover{background:#1B1F27}button:focus-visible{outline:2px solid #22D3EE}
button.p{background:#F3F5F9}button.p svg{fill:#06070A}
svg{width:22px;height:22px;fill:#F3F5F9;display:block;margin:auto}
.barra{height:12px;display:flex;align-items:flex-end;cursor:pointer}
.linea{height:4px;width:100%;background:#1B1F27}.linea i{display:block;height:100%;width:0;background:#22D3EE}
''';
    d.head!.appendChild(st);
    final fila = _crear(d, 'div', 'fila', d.body);
    _e['foto'] = _crear(d, 'div', 'foto', fila);
    final datos = _crear(d, 'div', 'datos', fila);
    _e['t'] = _crear(d, 'div', 't', datos);
    _e['a'] = _crear(d, 'div', 'a', datos);
    final b = _crear(d, 'div', 'b', datos);
    void boton(String clave, String nombre, void Function(Reproductor) hacer) {
      final x = _crear(d, 'button', clave == 'play' ? 'p' : '', b);
      x.setAttribute('aria-label', nombre);
      x.title = nombre;
      x.appendChild(_icono(d, clave));
      x.addEventListener('click', ((web.Event _) {
        final r = _r;
        if (r != null) hacer(r);
      }).toJS);
      _e[clave] = x;
    }

    boton('ant', 'Anterior', (r) => unawaited(r.anterior()));
    boton('play', 'Reproducir o pausar', (r) => unawaited(r.alternar()));
    boton('sig', 'Siguiente', (r) => unawaited(r.siguiente()));
    final barra = _crear(d, 'div', 'barra', d.body);
    final linea = _crear(d, 'div', 'linea', barra);
    _e['i'] = _crear(d, 'i', '', linea);
    barra.addEventListener('click', ((web.MouseEvent ev) {
      final r = _r;
      if (r == null || barra.clientWidth == 0) return;
      final f = (ev.clientX / barra.clientWidth).clamp(0.0, 1.0);
      unawaited(r.buscar(r.duracion.value * f));
    }).toJS);
  }

  static void _pintar() {
    final w = _ventana;
    final r = _r;
    if (w == null || r == null) return;
    final p = r.actual;
    if (p == null || (r.fuente?.esYouTubeWeb ?? false)) {
      // pasó a YouTube (o no suena nada): la ventanita ya no puede seguir
      _cerrado();
      w.close();
      return;
    }
    _e['t']?.textContent = '${p['titulo'] ?? ''}';
    _e['a']?.textContent = '${p['artista'] ?? ''}';
    final ref = '${p['miniatura'] ?? ''}';
    if (ref != _refPortada) {
      _refPortada = ref;
      if (_urlPortada.startsWith('blob:')) ArchivosWeb.soltarTemporal(_urlPortada);
      final bytes = PortadasMem.bytes(ref);
      _urlPortada = bytes != null ? ArchivosWeb.urlTemporal(bytes, 'image/jpeg') : (ref.startsWith('http') ? ref : '');
      _e['foto']?.style.backgroundImage = _urlPortada.isEmpty ? 'none' : 'url("${_urlPortada.replaceAll('"', '%22')}")';
    }
    final play = _e['play'];
    if (play != null) {
      play.replaceChildren(_icono(w.document, r.estado == EstadoRepro.sonando || r.estado == EstadoRepro.cargando ? 'pausa' : 'play'));
    }
    _avance();
  }

  static void _avance() {
    final r = _r;
    if (r == null) return;
    final d = r.duracion.value.inMilliseconds;
    final f = d <= 0 ? 0.0 : (r.posicion.value.inMilliseconds / d).clamp(0.0, 1.0);
    _e['i']?.style.width = '${(f * 100).toStringAsFixed(2)}%';
  }
}
