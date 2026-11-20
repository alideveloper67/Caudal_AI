import 'dart:async';

import 'package:flutter/foundation.dart';

import 'cosmeticos.dart';
import 'nube.dart';
import 'social.dart';

/// Los colores del nombre de los demás (donadores que eligieron uno), para el chat, «Juntos» y los
/// perfiles. Se piden solos y en lote: cada nombre que aparece en pantalla apunta su usuario y, a los
/// ~60 ms, sale UNA sola pregunta al servidor (`colores_nombre`) con todos los pendientes.
///
/// El servidor manda: solo devuelve colores de cuentas con beneficios vigentes y nunca de alguien
/// bloqueado. Se recuerda también quién NO tiene color, para no volver a preguntar. Si la base todavía
/// no tiene la función (o falla), simplemente no hay colores: nada se rompe.
class ColoresNombre extends ChangeNotifier {
  ColoresNombre._();
  static final ColoresNombre i = ColoresNombre._();

  /// Lo que se espera para juntar los usuarios de una pantalla en una sola pregunta.
  @visibleForTesting
  static Duration espera = const Duration(milliseconds: 60);

  /// Tope de usuarios por pregunta (el mismo que acepta el servidor).
  static const porLote = 200;

  /// Para las pruebas: en vez de llamar al servidor, esta función recibe el lote.
  @visibleForTesting
  static Future<dynamic> Function(List<String> usuarios)? llamadaPrueba;

  final Map<String, String?> _conocidos = {};
  final Set<String> _pendientes = {};
  Timer? _reloj;
  Social? _social;

  static String _norm(String u) => u.trim().replaceFirst('@', '').toLowerCase();

  /// El color de [usuario] ya sabido («#RRGGBB») o null (sin color o todavía no se sabe).
  String? de(String usuario) => _conocidos[_norm(usuario)];

  bool conoce(String usuario) => _conocidos.containsKey(_norm(usuario));

  /// Apunta [usuario] para preguntar su color (si no se sabe ya). Sin sesión no hace nada.
  void pedir(Social? social, String usuario) {
    final u = _norm(usuario);
    if (u.isEmpty || _conocidos.containsKey(u) || _pendientes.contains(u)) return;
    if (social == null && llamadaPrueba == null) return;
    if (social != null) _social = social;
    _pendientes.add(u);
    _reloj ??= Timer(espera, () => unawaited(_lanzar()));
  }

  Future<void> _lanzar() async {
    _reloj = null;
    final lote = _pendientes.take(porLote).toList();
    _pendientes.removeAll(lote);
    if (_pendientes.isNotEmpty) _reloj = Timer(espera, () => unawaited(_lanzar()));
    if (lote.isEmpty) return;
    final social = _social;
    try {
      final r = llamadaPrueba != null
          ? await llamadaPrueba!(lote)
          : await social!.sesion.rpc('colores_nombre', {'p_usuarios': lote});
      final mapa = leer(r);
      for (final u in lote) {
        _conocidos[u] = mapa[u];
      }
      notifyListeners();
    } on SinConexion {
      // sin internet: se vuelve a preguntar la próxima vez que se vean
    } catch (_) {
      // la base aún no tiene la función (o respondió otra cosa): sin colores, sin volver a preguntar
      for (final u in lote) {
        _conocidos[u] = null;
      }
    }
  }

  /// La respuesta del servidor ({usuario: color}) ya limpia: solo colores válidos.
  static Map<String, String> leer(Object? v) {
    final m = v is List && v.isNotEmpty ? v.first : v;
    if (m is! Map) return const {};
    final salida = <String, String>{};
    m.forEach((k, c) {
      final color = Cosmeticos.colorNombre(c);
      final u = _norm('$k');
      if (color != null && u.isNotEmpty) salida[u] = color;
    });
    return salida;
  }

  /// Al cerrar sesión (o para las pruebas): se olvida todo.
  void reiniciar() {
    _reloj?.cancel();
    _reloj = null;
    _pendientes.clear();
    _conocidos.clear();
    _social = null;
    notifyListeners();
  }
}
