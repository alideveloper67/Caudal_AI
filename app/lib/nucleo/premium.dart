import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'cosmeticos.dart';
import 'nube.dart';
import 'social.dart';

/// Lo que dice el servidor sobre los beneficios de la cuenta (`mi_premium`).
class EstadoPremium {
  const EstadoPremium({this.premium = false, this.tipo = '', this.vence});

  /// ¿Tiene los beneficios de donador ahora mismo?
  final bool premium;

  /// donador, fundador o prueba ('' si no tiene).
  final String tipo;

  /// Cuándo se acaban (solo las pruebas vencen; null = sin fecha).
  final DateTime? vence;

  static const ninguno = EstadoPremium();

  bool get esPrueba => tipo == 'prueba';

  /// Vigente a [ahora]: el servidor lo dice, pero una prueba guardada en el teléfono
  /// también se corta sola cuando pasa su fecha, aunque no haya internet.
  bool vigente([DateTime? ahora]) {
    if (!premium) return false;
    final v = vence;
    return v == null || v.isAfter(ahora ?? DateTime.now());
  }

  /// Días que quedan (se redondea hacia arriba: «hoy vence» es 1). Null sin fecha.
  int? diasRestantes([DateTime? ahora]) {
    final v = vence;
    if (v == null) return null;
    final ms = v.difference(ahora ?? DateTime.now()).inMilliseconds;
    return ms <= 0 ? 0 : (ms / Duration.millisecondsPerDay).ceil();
  }

  /// Una prueba a punto de acabarse (quedan [dias] días o menos).
  bool pocaPrueba({int dias = 2, DateTime? ahora}) {
    if (!esPrueba || !vigente(ahora)) return false;
    final d = diasRestantes(ahora);
    return d != null && d <= dias;
  }

  static EstadoPremium desde(Object? v) {
    final m = v is List && v.isNotEmpty ? v.first : v;
    if (m is! Map) return ninguno;
    final premium = m['premium'] == true;
    final tipo = '${m['tipo'] ?? ''}'.trim().toLowerCase();
    return EstadoPremium(
      premium: premium,
      tipo: premium ? tipo : '',
      vence: m['vence'] == null ? null : DateTime.tryParse('${m['vence']}')?.toLocal(),
    );
  }

  Map<String, Object?> aJson() =>
      {'premium': premium, 'tipo': tipo, 'vence': vence?.toUtc().toIso8601String()};

  @override
  bool operator ==(Object other) =>
      other is EstadoPremium &&
      other.premium == premium &&
      other.tipo == tipo &&
      // el mismo instante, venga en UTC o en hora local
      other.vence?.millisecondsSinceEpoch == vence?.millisecondsSinceEpoch;

  @override
  int get hashCode => Object.hash(premium, tipo, vence?.millisecondsSinceEpoch);
}

/// La respuesta de `canjear_pase`.
class ResultadoPase {
  const ResultadoPase({required this.ok, required this.mensaje, this.dias = 0, this.vence});
  final bool ok;
  final String mensaje;
  final int dias;
  final DateTime? vence;

  static ResultadoPase desde(Object? v) {
    final m = v is List && v.isNotEmpty ? v.first : v;
    if (m is! Map) return const ResultadoPase(ok: false, mensaje: 'No se pudo canjear el código. Inténtalo otra vez.');
    final dias = m['dias'];
    return ResultadoPase(
      ok: m['ok'] == true,
      mensaje: '${m['mensaje'] ?? ''}'.trim(),
      dias: dias is num ? dias.toInt() : int.tryParse('${dias ?? ''}') ?? 0,
      vence: m['vence'] == null ? null : DateTime.tryParse('${m['vence']}')?.toLocal(),
    );
  }
}

/// Los beneficios de donador de esta cuenta y lo que personalizó con ellos: marco del
/// avatar, efecto del nombre y tema de color. Una sola instancia ([Premium.i]); al cambiar
/// repinta lo que escucha.
///
/// El servidor manda (`mi_premium`, `canjear_pase`); aquí solo se pregunta y se recuerda en
/// el teléfono para que, sin internet, lo último que se supo siga valiendo (una prueba se
/// corta sola cuando pasa su fecha).
class Premium extends ChangeNotifier {
  Premium._();
  static final Premium i = Premium._();

  EstadoPremium estado = EstadoPremium.ninguno;

  /// Lo elegido, tal cual está guardado (puede haber elecciones de cuando era premium).
  String marco = Cosmeticos.ninguno;
  String efectoNombre = Cosmeticos.ninguno;
  String tema = Cosmeticos.ninguno;

  String _cuenta = '';

  bool get activo => estado.vigente();

  /// Lo que de verdad se ve: sin beneficios, todo vuelve a lo normal (sin borrar la elección).
  String get marcoEfectivo => activo ? marco : Cosmeticos.ninguno;
  String get efectoNombreEfectivo => activo ? efectoNombre : Cosmeticos.ninguno;
  String get temaEfectivo => activo ? tema : Cosmeticos.ninguno;

  static const _columnas = 'marco,efecto_nombre,tema_premium';

  /// Al entrar a una cuenta: primero lo guardado en el teléfono (instantáneo) y después lo de la nube.
  Future<void> iniciar(String cuentaId, Social? social) async {
    _cuenta = cuentaId;
    await _leerLocal();
    if (social == null) return;
    await refrescar(social);
  }

  /// Vuelve a preguntar al servidor (al entrar y tras canjear un pase).
  Future<void> refrescar(Social social) async {
    try {
      EstadoPremium nuevo;
      try {
        nuevo = EstadoPremium.desde(await social.sesion.rpc('mi_premium'));
      } on SinConexion {
        rethrow;
      } on ErrorNube {
        // un servidor sin `mi_premium` todavía: se usa la pregunta de siempre
        final puede = await social.sesion.rpc('puede_poner_fondo') == true;
        nuevo = EstadoPremium(premium: puede, tipo: puede ? 'donador' : '');
      }
      var m = marco, e = efectoNombre, t = tema;
      if (nuevo.premium) {
        final filas = await social.sesion.pedir('GET', 'perfiles?select=$_columnas&id=eq.${social.yo}');
        final f = filas is List && filas.isNotEmpty && filas.first is Map ? filas.first as Map : const {};
        m = Cosmeticos.marco(f['marco']);
        e = Cosmeticos.efectoNombre(f['efecto_nombre']);
        t = Cosmeticos.tema(f['tema_premium']);
      }
      if (nuevo != estado || m != marco || e != efectoNombre || t != tema) {
        estado = nuevo;
        marco = m;
        efectoNombre = e;
        tema = t;
        await _guardarLocal();
        notifyListeners();
      }
    } catch (_) {
      // sin conexión se queda lo guardado en el teléfono
    }
  }

  /// Canjea un código de prueba. Los mensajes del servidor se devuelven tal cual.
  Future<ResultadoPase> canjear(Social social, String codigo) async {
    final limpio = codigo.trim().toUpperCase();
    if (limpio.isEmpty) return const ResultadoPase(ok: false, mensaje: 'Escribe el código que te dieron.');
    ResultadoPase r;
    try {
      r = ResultadoPase.desde(await social.sesion.rpc('canjear_pase', {'p_codigo': limpio}));
    } on ErrorNube catch (e) {
      return ResultadoPase(ok: false, mensaje: e.mensaje);
    } catch (_) {
      return const ResultadoPase(ok: false, mensaje: 'No se pudo canjear el código. Revisa tu internet.');
    }
    if (r.ok) await refrescar(social);
    return r;
  }

  /// Guarda lo elegido: se ve al momento y se sube; si falla la nube se avisa con un [ErrorNube].
  Future<void> guardar(Social social, {String? marco, String? efectoNombre, String? tema}) async {
    final antes = (this.marco, this.efectoNombre, this.tema);
    if (marco != null) this.marco = Cosmeticos.marco(marco);
    if (efectoNombre != null) this.efectoNombre = Cosmeticos.efectoNombre(efectoNombre);
    if (tema != null) this.tema = Cosmeticos.tema(tema);
    notifyListeners();
    await _guardarLocal();
    try {
      await social.sesion.pedir('PATCH', 'perfiles?id=eq.${social.yo}', cuerpo: {
        if (marco != null) 'marco': this.marco,
        if (efectoNombre != null) 'efecto_nombre': this.efectoNombre,
        if (tema != null) 'tema_premium': this.tema,
      });
    } catch (_) {
      // no se pudo guardar: se deshace para no mostrar algo que los demás no ven
      this.marco = antes.$1;
      this.efectoNombre = antes.$2;
      this.tema = antes.$3;
      notifyListeners();
      await _guardarLocal();
      rethrow;
    }
  }

  /// Al cerrar sesión: nada de la cuenta anterior se queda a la vista.
  void reiniciar() {
    _cuenta = '';
    estado = EstadoPremium.ninguno;
    marco = efectoNombre = tema = Cosmeticos.ninguno;
    notifyListeners();
  }

  // ------------------------------------------------------------ en el teléfono

  String get _clave => 'premium_$_cuenta';

  Future<void> _leerLocal() async {
    try {
      final p = await SharedPreferences.getInstance();
      final texto = p.getString(_clave);
      if (texto == null) return;
      final d = jsonDecode(texto) as Map;
      estado = EstadoPremium.desde(d['estado']);
      marco = Cosmeticos.marco(d['marco']);
      efectoNombre = Cosmeticos.efectoNombre(d['efecto_nombre']);
      tema = Cosmeticos.tema(d['tema']);
      notifyListeners();
    } catch (_) {}
  }

  Future<void> _guardarLocal() async {
    if (_cuenta.isEmpty) return;
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_clave, jsonEncode({
        'estado': estado.aJson(), 'marco': marco, 'efecto_nombre': efectoNombre, 'tema': tema,
      }));
    } catch (_) {}
  }
}
