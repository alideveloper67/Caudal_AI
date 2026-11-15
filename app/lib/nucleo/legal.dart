import 'package:flutter/services.dart' show rootBundle;

import 'nube.dart';

/// Términos, privacidad y datos básicos del perfil (edad, país, género).
///
/// Los textos viven en Caudal/legal (fuente única) y se copian a
/// assets/legal con legal/sincronizar.py. Si cambian de forma importante se
/// sube [version] y a todos se les pide aceptarlos de nuevo.
class Legal {
  Legal._();

  static const version = '2026-11-15.2';

  /// Edad mínima sin permiso de la madre, el padre o un tutor (Ley 29733, Perú).
  static const edadMinima = 14;

  static Future<String> texto(String nombre) => rootBundle.loadString('assets/legal/$nombre.md');

  static const paises = <String, String>{
    'PE': 'Perú', 'AR': 'Argentina', 'BO': 'Bolivia', 'CL': 'Chile', 'CO': 'Colombia', 'CR': 'Costa Rica',
    'CU': 'Cuba', 'EC': 'Ecuador', 'SV': 'El Salvador', 'ES': 'España', 'US': 'Estados Unidos',
    'GT': 'Guatemala', 'HN': 'Honduras', 'MX': 'México', 'NI': 'Nicaragua', 'PA': 'Panamá',
    'PY': 'Paraguay', 'PR': 'Puerto Rico', 'DO': 'República Dominicana', 'UY': 'Uruguay',
    'VE': 'Venezuela', 'OT': 'Otro país',
  };

  static const generos = <String, String>{
    'mujer': 'Mujer', 'hombre': 'Hombre', 'otro': 'Otro', 'no_decir': 'Prefiero no decirlo',
  };

  static int edad(DateTime nacimiento, {DateTime? hoy}) {
    final h = hoy ?? DateTime.now();
    var e = h.year - nacimiento.year;
    if (h.month < nacimiento.month || (h.month == nacimiento.month && h.day < nacimiento.day)) e--;
    return e;
  }

  /// null si está bien; si no, lo que hay que corregir (en palabras).
  static String? revisarPerfil({required String nombre, required DateTime? nacimiento,
      required String? pais, required bool permisoTutor, DateTime? hoy}) {
    if (nombre.trim().length < 2) return 'Escribe tu nombre.';
    if (nacimiento == null) return 'Elige tu fecha de nacimiento.';
    final e = edad(nacimiento, hoy: hoy);
    if (e < 0 || e > 120) return 'Revisa tu fecha de nacimiento.';
    if (e < edadMinima && !permisoTutor) {
      return 'Tienes menos de $edadMinima años: tu madre, padre o tutor debe darte permiso '
          'y marcar la casilla de permiso.';
    }
    if (pais == null || pais.isEmpty) return 'Elige tu país.';
    return null;
  }

  static String fechaIso(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}

/// Lo que la nube sabe del perfil (para pedir lo que falte).
class PerfilLegal {
  PerfilLegal({this.version, this.comparte = false, this.nacimiento, this.pais, this.genero, this.nombre = ''});
  final String? version;
  final bool comparte;
  final DateTime? nacimiento;
  final String? pais;
  final String? genero;
  final String nombre;

  bool get aceptado => version == Legal.version;
  bool get completo => nacimiento != null && (pais ?? '').isNotEmpty;

  static Future<PerfilLegal> de(Sesion s) async {
    final filas = await s.pedir('GET',
        'perfiles?select=nombre,terminos_version,comparte_datos,fecha_nacimiento,pais,genero&id=eq.${s.userId}') as List;
    if (filas.isEmpty) return PerfilLegal();
    final d = filas.first as Map;
    return PerfilLegal(
      version: d['terminos_version'] as String?,
      comparte: d['comparte_datos'] == true,
      nacimiento: DateTime.tryParse('${d['fecha_nacimiento'] ?? ''}'),
      pais: d['pais'] as String?,
      genero: d['genero'] as String?,
      nombre: '${d['nombre'] ?? ''}',
    );
  }

  static Future<void> aceptar(Sesion s, {required bool comparte}) =>
      s.pedir('POST', 'rpc/aceptar_terminos', cuerpo: {'p_version': Legal.version, 'p_comparte': comparte});

  static Future<void> compartir(Sesion s, bool comparte) =>
      s.pedir('POST', 'rpc/compartir_datos', cuerpo: {'p_comparte': comparte});

  static Future<void> completar(Sesion s, {required String nombre, required DateTime nacimiento,
          required String pais, String? genero, bool permisoTutor = false}) =>
      s.pedir('POST', 'rpc/completar_perfil', cuerpo: {
        'p_nombre': nombre.trim(), 'p_nacimiento': Legal.fechaIso(nacimiento), 'p_pais': pais,
        'p_genero': genero ?? '', 'p_permiso_tutor': permisoTutor,
      });

  static Future<void> eliminarCuenta(Sesion s) => s.pedir('POST', 'rpc/eliminar_mi_cuenta', cuerpo: {});
}
