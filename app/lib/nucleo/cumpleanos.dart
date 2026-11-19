import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'legal.dart';
import 'nube.dart';

/// «Feliz cumpleaños»: las reglas (puras, sin red) y lo que la app sabe hoy.
///
/// - El día del cumpleaños se mira con la fecha LOCAL del teléfono. Quien nació un 29 de febrero
///   lo celebra el 28 en los años que no son bisiestos.
/// - La pantalla de celebración sale UNA sola vez por día (se marca antes de enseñarla: si la
///   cierran o la app se cae, no vuelve a salir).
/// - De los amigos solo se sabe QUIÉN cumple hoy (supabase/cumpleanos.sql, función
///   `amigos_cumplen_hoy`): nunca su fecha de nacimiento.
class ReglaCumple {
  ReglaCumple._();

  static bool esBisiesto(int anio) => (anio % 4 == 0 && anio % 100 != 0) || anio % 400 == 0;

  /// ¿[hoy] es el día de cumpleaños de quien nació el [nacimiento]?
  static bool esCumple(DateTime? nacimiento, DateTime hoy) {
    if (nacimiento == null) return false;
    var dia = nacimiento.day;
    if (nacimiento.month == 2 && dia == 29 && !esBisiesto(hoy.year)) dia = 28;
    return hoy.month == nacimiento.month && hoy.day == dia;
  }

  /// La edad que cumple hoy; null si la fecha no tiene sentido (futura o de más de 120 años).
  static int? edadQueCumple(DateTime? nacimiento, DateTime hoy) {
    if (nacimiento == null) return null;
    final e = hoy.year - nacimiento.year;
    return e >= 1 && e <= 120 ? e : null;
  }

  /// El día como texto (`2026-11-19`): lo que se guarda para no repetir la celebración.
  static String claveDia(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}

class Cumpleanos extends ChangeNotifier {
  Cumpleanos._();
  static final Cumpleanos i = Cumpleanos._();

  /// El reloj (las pruebas lo cambian).
  DateTime Function() ahora = DateTime.now;

  String miId = '';
  String nombre = '';
  DateTime? nacimiento;
  final Set<String> _amigos = {};
  String _diaAmigos = '';
  String _cuenta = '';

  /// Ya se intentó leer mi fecha (con o sin éxito): la celebración espera a esto para no llegar tarde ni temprano.
  bool perfilLeido = false;

  static const _llave = 'cumple_celebrado';

  /// ¿Hoy es mi cumpleaños? (se calcula al momento: si pasa la medianoche, se apaga solo)
  bool get esMiCumple => ReglaCumple.esCumple(nacimiento, ahora());

  int? get edad => ReglaCumple.edadQueCumple(nacimiento, ahora());

  /// Los amigos que cumplen hoy (vacío si la lista es de otro día).
  Set<String> get amigosHoy => _diaAmigos == ReglaCumple.claveDia(ahora()) ? Set.unmodifiable(_amigos) : const {};

  /// ¿Esta persona (yo o un amigo) cumple hoy? Con el id vacío, no.
  bool esDe(String id) {
    if (id.isEmpty) return false;
    if (id == miId) return esMiCumple;
    return amigosHoy.contains(id);
  }

  /// Datos a mano (para la app al leer el perfil y para las pruebas).
  void poner({String? cuenta, String? id, String? nombre, DateTime? nacimiento, Iterable<String>? amigos}) {
    if (cuenta != null) _cuenta = cuenta;
    if (id != null) miId = id;
    if (nombre != null) this.nombre = nombre;
    this.nacimiento = nacimiento ?? this.nacimiento;
    if (amigos != null) {
      _amigos
        ..clear()
        ..addAll(amigos.where((a) => a.isNotEmpty && a != miId));
      _diaAmigos = ReglaCumple.claveDia(ahora());
    }
    notifyListeners();
  }

  /// Al entrar a la cuenta: lee mi fecha y los amigos que cumplen hoy. Nunca lanza; sin red, no pasa nada.
  Future<void> iniciar(String cuentaId, Sesion? sesion) async {
    _cuenta = cuentaId;
    miId = sesion?.userId ?? cuentaId;
    perfilLeido = false;
    if (sesion == null || sesion.acceso.isEmpty) {
      perfilLeido = true;
      notifyListeners();
      return;
    }
    try {
      final p = await PerfilLegal.de(sesion);
      if (_cuenta != cuentaId) return; // cambió de cuenta mientras tanto
      nacimiento = p.nacimiento;
      if (p.nombre.trim().isNotEmpty) nombre = p.nombre.trim().split(' ').first;
    } catch (_) {}
    perfilLeido = true;
    notifyListeners();
    await actualizarAmigos(sesion);
  }

  /// Vuelve a pedir quién de mis amigos cumple hoy.
  Future<void> actualizarAmigos(Sesion sesion) async {
    try {
      final r = await sesion.rpc('amigos_cumplen_hoy');
      if (_cuenta.isEmpty && miId.isEmpty) return;
      final ids = <String>[
        if (r is List)
          for (final x in r)
            if (x is String) x else if (x is Map && x.values.isNotEmpty) '${x.values.first}',
      ];
      poner(amigos: ids);
    } catch (_) {}
  }

  /// ¿Toca enseñar la pantalla de celebración? Solo mi cumpleaños y una vez al día.
  Future<bool> tocaCelebrar([SharedPreferences? prefs]) async {
    if (!esMiCumple) return false;
    try {
      final p = prefs ?? await SharedPreferences.getInstance();
      return p.getString('$_llave.$_cuenta') != ReglaCumple.claveDia(ahora());
    } catch (_) {
      return false; // sin poder recordarlo, mejor no repetirla
    }
  }

  Future<void> marcarCelebrado([SharedPreferences? prefs]) async {
    try {
      final p = prefs ?? await SharedPreferences.getInstance();
      await p.setString('$_llave.$_cuenta', ReglaCumple.claveDia(ahora()));
    } catch (_) {}
  }

  /// Al salir de la cuenta.
  void reiniciar() {
    miId = '';
    nombre = '';
    nacimiento = null;
    _amigos.clear();
    _diaAmigos = '';
    _cuenta = '';
    perfilLeido = false;
    notifyListeners();
  }

  /// Espera a que se lea mi fecha de nacimiento (lo hace [iniciar], que siempre termina: con o sin red).
  /// Sin reloj de espera: si nunca se llamó a [iniciar] simplemente no sigue. Devuelve si hoy es mi cumpleaños.
  Future<bool> esperarPerfil() async {
    if (perfilLeido) return esMiCumple;
    final c = Completer<void>();
    void escuchar() {
      if (perfilLeido && !c.isCompleted) c.complete();
    }

    addListener(escuchar);
    try {
      await c.future;
    } finally {
      removeListener(escuchar);
    }
    return esMiCumple;
  }
}
