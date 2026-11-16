import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'nube.dart';
import 'social.dart';

/// «Fondo de Caudal»: una imagen que se ve tenue detrás de toda la app.
/// Es exclusivo de las cuentas «Donador de Caudal» y «Fundador de Caudal»: lo
/// decide el servidor (`puede_poner_fondo`), aquí solo se pregunta.
///
/// Es una sola instancia para toda la app ([FondoApp.i]): lo que cambia aquí se
/// repinta al momento (los deslizadores se ven en vivo) y se guarda en el
/// teléfono, para que al abrir la app el fondo ya esté, y en la nube, para que
/// la misma cuenta lo tenga en todos sus dispositivos.
class FondoApp extends ChangeNotifier {
  FondoApp._();
  static final FondoApp i = FondoApp._();

  static const visibleMin = 5, visibleMax = 60, visibleBase = 22;
  static const desenfoqueMax = 20;

  /// Ruta guardada en la nube (`<mi id>/fondo.jpg`), vacía si no hay fondo.
  String ruta = '';
  int visible = visibleBase;
  int desenfoque = 0;
  bool puede = false;
  String titulo = '';

  /// Cambia cada vez que se sube una imagen nueva, para saltar la caché.
  int version = 0;

  String _cuenta = '';

  bool get activo => puede && ruta.isNotEmpty;

  /// La dirección completa de la imagen (con la marca de versión).
  String get url => ruta.isEmpty ? '' : '${Social.urlPublica('avatares', ruta)}?v=$version';

  static const _columnas = 'fondo_url,fondo_visible,fondo_desenfoque';

  /// Al entrar a una cuenta: primero lo guardado en el teléfono (instantáneo) y
  /// después lo de la nube.
  Future<void> iniciar(String cuentaId, Social? social) async {
    _cuenta = cuentaId;
    await _leerLocal();
    if (social == null) return;
    try {
      final puedeNube = await social.sesion.rpc('puede_poner_fondo') == true;
      var r = ruta, v = visible, d = desenfoque, ver = version;
      if (puedeNube) {
        final filas = await social.sesion.pedir('GET', 'perfiles?select=$_columnas&id=eq.${social.yo}');
        final l = filas is List && filas.isNotEmpty && filas.first is Map ? filas.first as Map : const {};
        final nueva = '${l['fondo_url'] ?? ''}';
        if (nueva != ruta) ver = DateTime.now().millisecondsSinceEpoch;
        r = nueva;
        v = (l['fondo_visible'] is num ? (l['fondo_visible'] as num).toInt() : visibleBase)
            .clamp(visibleMin, visibleMax);
        d = (l['fondo_desenfoque'] is num ? (l['fondo_desenfoque'] as num).toInt() : 0).clamp(0, desenfoqueMax);
      } else {
        r = '';
      }
      final t = puedeNube ? await _tituloDe(social) : '';
      if (puedeNube != puede || r != ruta || v != visible || d != desenfoque || t != titulo) {
        puede = puedeNube;
        ruta = r;
        visible = v;
        desenfoque = d;
        titulo = t;
        version = ver;
        await _guardarLocal();
        notifyListeners();
      }
    } catch (_) {
      // sin conexión se queda lo guardado en el teléfono
    }
  }

  Future<String> _tituloDe(Social social) async {
    try {
      final usuario = await _usuarioDe(social);
      if (usuario.isEmpty) return '';
      final p = await social.verPerfil(usuario);
      final nombres = [for (final t in p?.titulos ?? const <TituloEspecial>[]) t.nombre];
      return nombres.firstWhere((n) => n.contains('Donador') || n.contains('Fundador'), orElse: () => '');
    } catch (_) {
      return '';
    }
  }

  Future<String> _usuarioDe(Social social) async {
    final filas = await social.sesion.pedir('GET', 'perfiles?select=usuario&id=eq.${social.yo}');
    return filas is List && filas.isNotEmpty && filas.first is Map ? '${(filas.first as Map)['usuario'] ?? ''}' : '';
  }

  /// Al cerrar sesión: nada de la cuenta anterior se queda a la vista.
  void reiniciar() {
    _cuenta = '';
    ruta = '';
    visible = visibleBase;
    desenfoque = 0;
    puede = false;
    titulo = '';
    notifyListeners();
  }

  /// Sube una imagen nueva (ya reducida y en JPEG) y la deja como fondo.
  Future<void> poner(Social social, Uint8List jpeg) async {
    final nueva = '${social.yo}/fondo.jpg';
    try {
      await social.sesion.subir('avatares', nueva, jpeg, 'image/jpeg', reemplazar: true);
    } on SinConexion {
      rethrow;
    } on ErrorNube catch (e) {
      throw ErrorNube('No se pudo guardar tu fondo. ${e.mensaje} Vuelve a intentarlo.');
    }
    await social.sesion.pedir('PATCH', 'perfiles?id=eq.${social.yo}',
        cuerpo: {'fondo_url': nueva, 'fondo_visible': visible, 'fondo_desenfoque': desenfoque});
    ruta = nueva;
    version = DateTime.now().millisecondsSinceEpoch;
    await _guardarLocal();
    notifyListeners();
  }

  /// Los deslizadores: se ve al instante; con [guardar] también se sube y se recuerda.
  Future<void> ajustar(Social? social, {int? visible, int? desenfoque, bool guardar = false}) async {
    if (visible != null) this.visible = visible.clamp(visibleMin, visibleMax);
    if (desenfoque != null) this.desenfoque = desenfoque.clamp(0, desenfoqueMax);
    notifyListeners();
    if (!guardar) return;
    await _guardarLocal();
    if (social == null || ruta.isEmpty) return;
    try {
      await social.sesion.pedir('PATCH', 'perfiles?id=eq.${social.yo}',
          cuerpo: {'fondo_visible': this.visible, 'fondo_desenfoque': this.desenfoque});
    } catch (_) {
      // se queda en el teléfono; la próxima vez que se guarde, sube
    }
  }

  Future<void> quitar(Social? social) async {
    final antes = ruta;
    ruta = '';
    notifyListeners();
    await _guardarLocal();
    if (social == null || antes.isEmpty) return;
    await social.sesion.pedir('PATCH', 'perfiles?id=eq.${social.yo}', cuerpo: {'fondo_url': null});
  }

  // ------------------------------------------------------------ en el teléfono

  String get _clave => 'fondo_app_$_cuenta';

  Future<void> _leerLocal() async {
    try {
      final p = await SharedPreferences.getInstance();
      final texto = p.getString(_clave);
      if (texto == null) return;
      final d = jsonDecode(texto) as Map;
      ruta = '${d['ruta'] ?? ''}';
      visible = ((d['visible'] as num?)?.toInt() ?? visibleBase).clamp(visibleMin, visibleMax);
      desenfoque = ((d['desenfoque'] as num?)?.toInt() ?? 0).clamp(0, desenfoqueMax);
      puede = d['puede'] == true;
      titulo = '${d['titulo'] ?? ''}';
      version = (d['version'] as num?)?.toInt() ?? 0;
      notifyListeners();
    } catch (_) {}
  }

  Future<void> _guardarLocal() async {
    if (_cuenta.isEmpty) return;
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_clave, jsonEncode({
        'ruta': ruta, 'visible': visible, 'desenfoque': desenfoque,
        'puede': puede, 'titulo': titulo, 'version': version,
      }));
    } catch (_) {}
  }
}

/// Imagen de fondo: se reduce a 1920 px de lado largo y se comprime (JPEG < 4,5 MB).
Future<Uint8List> prepararFondo(Uint8List original) => compute(_fondoApp, original);

Uint8List _fondoApp(Uint8List b) => cuadrarYComprimir(b, 1920, recortar: false, maxBytes: 4500000);
