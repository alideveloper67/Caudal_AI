import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'nube.dart';
import 'premium.dart';
import 'social.dart';

/// La portada del perfil (solo donadores): la canción del momento, un fragmento de letra y la mascota.
/// La ven la propia persona y sus amigos. El servidor manda (`portada_perfil` y las columnas
/// `portada_*` de supabase/perfil_portada.sql); aquí solo se pregunta, se escribe y se recuerda en el
/// teléfono para que la propia portada se vea al instante.
class PortadaPerfil {
  const PortadaPerfil({this.cancion, this.letra = '', this.mascota = ''});

  /// Letras que admite el fragmento (el servidor corta en el mismo número).
  static const maxLetra = 160;

  /// Líneas que se enseñan como mucho, aunque el texto traiga más.
  static const maxLineas = 4;

  final CancionFav? cancion;
  final String letra;

  /// Clave de la mascota del catálogo ('' = ninguna).
  final String mascota;

  static const vacio = PortadaPerfil();

  bool get vacia => cancion == null && letra.isEmpty && mascota.isEmpty;

  /// El fragmento ya limpio: sin espacios de más, con a lo sumo [maxLineas] líneas y [maxLetra] letras.
  static String limpiarLetra(String t) {
    final lineas = [
      for (final l in t.replaceAll('\r', '').split('\n'))
        if (l.trim().isNotEmpty) l.trim().replaceAll(RegExp(r'[ \t]+'), ' '),
    ].take(maxLineas).join('\n');
    return lineas.length <= maxLetra ? lineas : lineas.substring(0, maxLetra).trimRight();
  }

  static String _clave(Object? v) {
    final t = '${v ?? ''}'.trim().toLowerCase();
    return RegExp(r'^[a-z0-9_]{1,40}$').hasMatch(t) ? t : '';
  }

  /// Nulo si no llegó nada que enseñar (la base responde `null` sin portada).
  static PortadaPerfil? desde(Object? v) {
    final d = v is List && v.isNotEmpty ? v.first : v;
    if (d is! Map) return null;
    final c = CancionFav.desde(d['cancion']);
    final p = PortadaPerfil(
      cancion: c != null && c.videoId.isNotEmpty ? c : null,
      letra: limpiarLetra('${d['letra'] ?? ''}'),
      mascota: _clave(d['mascota']),
    );
    return p.vacia ? null : p;
  }

  /// Lo que se escribe en las columnas del perfil (vacío = null, para borrar).
  Map<String, Object?> aColumnas() => {
        'portada_cancion': cancion?.toJson(),
        'portada_letra': letra.isEmpty ? null : letra,
        'portada_mascota': mascota.isEmpty ? null : mascota,
      };

  Map<String, Object?> aJson() => {'cancion': cancion?.toJson(), 'letra': letra, 'mascota': mascota};

  PortadaPerfil copiar({Object? cancion = _igual, String? letra, String? mascota}) => PortadaPerfil(
        cancion: identical(cancion, _igual) ? this.cancion : cancion as CancionFav?,
        letra: letra ?? this.letra,
        mascota: mascota ?? this.mascota,
      );

  static const Object _igual = Object();

  @override
  bool operator ==(Object other) =>
      other is PortadaPerfil &&
      other.letra == letra &&
      other.mascota == mascota &&
      mapEquals(other.cancion?.toJson(), cancion?.toJson());

  @override
  int get hashCode => Object.hash(letra, mascota, cancion?.videoId);
}

/// Pregunta, guarda y recuerda la portada. Una sola instancia ([PortadasPerfil.i]).
class PortadasPerfil extends ChangeNotifier {
  PortadasPerfil._();
  static final PortadasPerfil i = PortadasPerfil._();

  /// La portada propia tal como se sabe en este teléfono (se repinta al cambiar).
  PortadaPerfil mia = PortadaPerfil.vacio;

  String _cuenta = '';

  /// ¿Se puede ver/usar ahora? Solo con los beneficios de donador vigentes.
  bool get puede => Premium.i.activo;

  String _llave(String cuenta) => 'portada_perfil_$cuenta';

  /// Al entrar en una pantalla de esta cuenta: lo último guardado en el teléfono.
  Future<void> cargarLocal(String cuenta) async {
    if (cuenta.isEmpty) return;
    if (_cuenta != cuenta) {
      _cuenta = cuenta;
      mia = PortadaPerfil.vacio;
    }
    try {
      final p = await SharedPreferences.getInstance();
      final t = p.getString(_llave(cuenta));
      if (t == null) return;
      final leida = PortadaPerfil.desde(jsonDecode(t)) ?? PortadaPerfil.vacio;
      if (leida != mia) {
        mia = leida;
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<void> _guardarLocal() async {
    if (_cuenta.isEmpty) return;
    try {
      final p = await SharedPreferences.getInstance();
      if (mia.vacia) {
        await p.remove(_llave(_cuenta));
      } else {
        await p.setString(_llave(_cuenta), jsonEncode(mia.aJson()));
      }
    } catch (_) {}
  }

  /// La portada de [usuario] tal como la ve esta cuenta. Nulo si no hay nada que ver (no es amigo, no es
  /// donador, no tiene portada…). Con la función aún sin aplicar en el servidor también es nulo: la
  /// pantalla sigue como siempre. Un fallo de red sí se lanza, para que la pantalla decida.
  Future<PortadaPerfil?> ver(Social social, String usuario, {bool esMia = false}) async {
    Object? r;
    try {
      r = await social.sesion.rpc('portada_perfil', {'p_usuario': usuario});
    } on SinConexion {
      rethrow;
    } on ErrorNube {
      return null;
    }
    final p = PortadaPerfil.desde(r);
    if (esMia) {
      if (_cuenta.isEmpty) _cuenta = social.yo;
      final nueva = p ?? PortadaPerfil.vacio;
      if (nueva != mia) {
        mia = nueva;
        notifyListeners();
        await _guardarLocal();
      }
    }
    return p;
  }

  /// Guarda la portada propia: se ve al momento y se sube; si falla se deshace y se avisa con el error.
  Future<void> guardar(Social social, PortadaPerfil nueva) async {
    final antes = mia;
    final limpia = PortadaPerfil(cancion: nueva.cancion, letra: PortadaPerfil.limpiarLetra(nueva.letra), mascota: nueva.mascota);
    mia = limpia;
    notifyListeners();
    try {
      await social.sesion.pedir('PATCH', 'perfiles?id=eq.${social.yo}', cuerpo: limpia.aColumnas());
    } catch (_) {
      mia = antes;
      notifyListeners();
      rethrow;
    }
    await _guardarLocal();
  }

  /// Al cerrar sesión: nada de la cuenta anterior se queda a la vista.
  void reiniciar() {
    _cuenta = '';
    mia = PortadaPerfil.vacio;
    notifyListeners();
  }
}
