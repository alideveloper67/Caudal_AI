import 'coleccion.dart';
import 'ritmo.dart';

/// El ritmo de la canción que suena, para que el personaje del fondo baile en sus tiempos.
///
/// No analiza nada (no gasta datos ni batería): solo mira lo que Caudal ya sabe de cada canción
/// (lo que midió el mezclador, guardado en la colección). Lo busca una vez por canción.
class RitmoFondo {
  RitmoFondo._(this.coleccion);

  static RitmoFondo? _actual;

  /// El de esta colección (al cambiar de cuenta, se empieza de nuevo).
  static RitmoFondo para(Coleccion c) {
    final a = _actual;
    if (a != null && identical(a.coleccion, c)) return a;
    return _actual = RitmoFondo._(c);
  }

  final Coleccion coleccion;
  String _clave = '';
  AnalisisRitmo? _ritmo;

  /// El ritmo de [clave] si ya se conoce (null mientras se busca o si no se sabe).
  AnalisisRitmo? de(String clave) {
    if (clave != _clave) {
      _clave = clave;
      _ritmo = null;
      if (clave.isNotEmpty) _buscar(clave);
    }
    return _ritmo;
  }

  Future<void> _buscar(String clave) async {
    try {
      final d = await coleccion.estado('ritmo_cache');
      if (clave != _clave || d is! Map) return;
      final a = AnalisisRitmo.deJson(d[clave]);
      if (a != null && a.valido) _ritmo = a;
    } catch (_) {}
  }
}
