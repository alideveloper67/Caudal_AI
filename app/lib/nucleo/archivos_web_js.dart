import 'dart:async';
import 'dart:js_interop';
import 'dart:js_interop_unsafe';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

/// Los archivos de música guardados en el navegador (IndexedDB).
class ArchivosWeb {
  ArchivosWeb._();

  static const _base = 'caudal_archivos';
  static const _audio = 'audio';
  static const _portada = 'portadas';

  static bool esRef(String ref) => ref.startsWith('web:');
  static String _id(String ref) => ref.substring(4);

  static Future<web.IDBDatabase>? _abriendo;

  static Future<web.IDBDatabase> _bd() async {
    try {
      return await (_abriendo ??= _abrir());
    } catch (_) {
      _abriendo = null; // que se pueda reintentar
      rethrow;
    }
  }

  static Future<web.IDBDatabase> _abrir() {
    final c = Completer<web.IDBDatabase>();
    final r = web.window.indexedDB.open(_base, 1);
    r.onupgradeneeded = ((web.Event _) {
      final db = r.result as web.IDBDatabase;
      db.createObjectStore(_audio);
      db.createObjectStore(_portada);
    }).toJS;
    r.onsuccess = ((web.Event _) {
      if (!c.isCompleted) c.complete(r.result as web.IDBDatabase);
    }).toJS;
    r.onerror = ((web.Event _) {
      if (!c.isCompleted) c.completeError(StateError('No se pudo abrir el almacén del navegador'));
    }).toJS;
    return c.future;
  }

  static Future<JSAny?> _pedir(web.IDBRequest r) {
    final c = Completer<JSAny?>();
    r.onsuccess = ((web.Event _) => c.complete(r.result)).toJS;
    r.onerror = ((web.Event _) => c.completeError(StateError(r.error?.name ?? 'Fallo del almacén'))).toJS;
    return c.future;
  }

  static Future<void> _fin(web.IDBTransaction t) {
    final c = Completer<void>();
    void falla(web.Event _) {
      if (!c.isCompleted) c.completeError(StateError(t.error?.name ?? 'Fallo del almacén'));
    }

    t.oncomplete = ((web.Event _) {
      if (!c.isCompleted) c.complete();
    }).toJS;
    t.onerror = falla.toJS;
    t.onabort = falla.toJS;
    return c.future;
  }

  static web.Blob _blob(Uint8List b, String tipo) => web.Blob([b.toJS].toJS, web.BlobPropertyBag(type: tipo));

  /// Guarda un audio (y su carátula) y devuelve su referencia `web:<id>`.
  static Future<String> guardar(Uint8List bytes, {String tipo = 'audio/mpeg', Uint8List? portada}) async {
    final id = '${DateTime.now().microsecondsSinceEpoch}-${bytes.length}';
    final db = await _bd();
    final t = db.transaction([_audio.toJS, _portada.toJS].toJS, 'readwrite');
    final fin = _fin(t);
    t.objectStore(_audio).put(_blob(bytes, tipo), id.toJS);
    if (portada != null) t.objectStore(_portada).put(portada.toJS, id.toJS);
    await fin;
    return 'web:$id';
  }

  static final Map<String, String> _urls = {};

  /// Una dirección que el reproductor puede abrir (null: ya no está guardado).
  static Future<String?> url(String ref) async {
    final ya = _urls[ref];
    if (ya != null) return ya;
    final db = await _bd();
    final r = await _pedir(db.transaction(_audio.toJS, 'readonly').objectStore(_audio).get(_id(ref).toJS));
    if (r == null || !r.isA<web.Blob>()) return null;
    return _urls[ref] = web.URL.createObjectURL(r as web.Blob);
  }

  static Future<void> borrar(String ref) async {
    final u = _urls.remove(ref);
    if (u != null) web.URL.revokeObjectURL(u);
    final db = await _bd();
    final t = db.transaction([_audio.toJS, _portada.toJS].toJS, 'readwrite');
    final fin = _fin(t);
    t.objectStore(_audio).delete(_id(ref).toJS);
    t.objectStore(_portada).delete(_id(ref).toJS);
    await fin;
  }

  /// Todas las carátulas guardadas, por referencia `web:<id>`.
  static Future<Map<String, Uint8List>> portadas() async {
    final db = await _bd();
    final s = db.transaction(_portada.toJS, 'readonly').objectStore(_portada);
    final r = await Future.wait([_pedir(s.getAllKeys()), _pedir(s.getAll())]);
    final claves = (r[0] as JSArray<JSAny?>).toDart;
    final datos = (r[1] as JSArray<JSAny?>).toDart;
    final salida = <String, Uint8List>{};
    for (var i = 0; i < claves.length && i < datos.length; i++) {
      final d = datos[i];
      if (d != null && d.isA<JSUint8Array>()) {
        salida['web:${(claves[i] as JSString).toDart}'] = (d as JSUint8Array).toDart;
      }
    }
    return salida;
  }

  /// Segundos que dura un audio: 0 si no se sabe, -1 si el navegador no lo puede abrir.
  static Future<double> duracion(Uint8List bytes, String tipo) async {
    final u = web.URL.createObjectURL(_blob(bytes, tipo));
    final a = web.HTMLAudioElement();
    final c = Completer<double>();
    a.preload = 'metadata';
    a.addEventListener('loadedmetadata', ((web.Event _) {
      if (!c.isCompleted) c.complete(a.duration.isFinite ? a.duration : 0);
    }).toJS);
    a.addEventListener('error', ((web.Event _) {
      if (!c.isCompleted) c.complete(-1);
    }).toJS);
    a.src = u;
    try {
      return await c.future.timeout(const Duration(seconds: 8), onTimeout: () => 0);
    } finally {
      a.removeAttribute('src');
      web.URL.revokeObjectURL(u);
    }
  }

  /// La carátula en 320×320 como mucho (JPEG), para no llenar la memoria.
  static Future<Uint8List?> reducirPortada(Uint8List bytes) async {
    try {
      final bmp = await web.window.createImageBitmap(web.Blob([bytes.toJS].toJS)).toDart;
      final mayor = bmp.width > bmp.height ? bmp.width : bmp.height;
      final f = mayor > 320 ? 320 / mayor : 1.0;
      final lienzo = web.HTMLCanvasElement()
        ..width = (bmp.width * f).round()
        ..height = (bmp.height * f).round();
      final ctx = lienzo.getContext('2d') as web.CanvasRenderingContext2D;
      ctx.drawImage(bmp, 0, 0, lienzo.width, lienzo.height);
      bmp.close();
      final c = Completer<web.Blob?>();
      lienzo.toBlob(((web.Blob? b) => c.complete(b)).toJS, 'image/jpeg', 0.85.toJS);
      final b = await c.future;
      if (b == null) return null;
      return (await b.arrayBuffer().toDart).toDart.asUint8List();
    } catch (_) {
      return null;
    }
  }

  /// Pide al navegador que no borre lo guardado cuando le falte espacio.
  static Future<bool> pedirPermanencia() async {
    try {
      return (await web.window.navigator.storage.persist().toDart).toDart;
    } catch (_) {
      return false;
    }
  }

  /// (bytes usados, bytes que deja usar el navegador).
  static Future<(int, int)> espacio() async {
    try {
      final o = await web.window.navigator.storage.estimate().toDart as JSObject;
      int n(String k) {
        final v = o[k];
        return v.isA<JSNumber>() ? (v as JSNumber).toDartDouble.round() : 0;
      }

      return (n('usage'), n('quota'));
    } catch (_) {
      return (0, 0);
    }
  }

  static String urlTemporal(Uint8List bytes, String tipo) => web.URL.createObjectURL(_blob(bytes, tipo));
  static void soltarTemporal(String url) => web.URL.revokeObjectURL(url);
}
