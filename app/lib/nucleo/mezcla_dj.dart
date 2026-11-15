import 'dart:convert';
import 'dart:math';

import 'coleccion.dart';

/// Logica pura de la «Mezcla DJ» y de la mesa del Mezclador (sin motores ni
/// pantallas), para poder probarla: cuando entra la siguiente cancion, cuanto
/// dura el cambio y como se hace el cambio de graves.
///
/// Un set es una lista de [PasoMezcla]. El paso `i` describe como se pasa de la
/// cancion `i` a la `i + 1` (el ultimo paso no pasa a nada y no se usa).

/// Lo que dura el cambio de la «Mezcla DJ» automatica, en segundos.
const int djMin = 4;
const int djMax = 16;
const int djPorDefecto = 8;

/// El valor del ajuste, siempre dentro de 4-16 s (puede venir de otra version).
int segundosDj(Object? valor) {
  final n = valor is num ? valor.round() : int.tryParse('${valor ?? ''}') ?? djPorDefecto;
  return n.clamp(djMin, djMax);
}

/// Limites de lo que se puede ajustar en cada paso de la mesa.
const double entraMin = 2;
const double entraMax = 30;
const double fundidoMin = 2;
const double fundidoMax = 16;

/// Un paso del set: una cancion y como se pasa de ella a la siguiente.
class PasoMezcla {
  PasoMezcla({
    required this.pista,
    this.entraAntes = 8,
    this.fundido = 8,
    this.graves = true,
  });

  /// La cancion (el mismo mapa que usa todo el reproductor).
  final Map<String, dynamic> pista;

  /// La siguiente entra cuando a esta le faltan tantos segundos.
  final double entraAntes;

  /// Lo que dura el cambio (los dos suenan a la vez), en segundos.
  final double fundido;

  /// Si en el cambio se intercambian los graves (el de la que se va baja y el
  /// de la que llega sube), como hace un DJ con el ecualizador.
  final bool graves;

  /// Duracion de la cancion en segundos (0 si no se sabe).
  double get duracionPista {
    final d = pista['duracion'];
    final n = d is num ? d.toDouble() : double.tryParse('${d ?? ''}') ?? 0;
    return n > 0 ? n : 0;
  }

  /// Cuando entra de verdad la siguiente: dentro de los limites y sin comerse
  /// mas de la mitad de esta cancion.
  double get entraEfectivo {
    final e = entraAntes.clamp(entraMin, entraMax);
    final d = duracionPista;
    return d > 0 ? min(e, d * 0.5) : e;
  }

  /// Lo que dura el cambio de verdad: nunca mas que lo que queda desde que
  /// entra la siguiente.
  double get fundidoEfectivo => min(fundido.clamp(fundidoMin, fundidoMax), entraEfectivo);

  /// Segundo de esta cancion en el que empieza el cambio (0 si no se sabe el largo).
  double get inicioDelCambio {
    final d = duracionPista;
    return d > 0 ? max(0, d - entraEfectivo) : 0;
  }

  PasoMezcla copiaCon({Map<String, dynamic>? pista, double? entraAntes, double? fundido, bool? graves}) =>
      PasoMezcla(
        pista: pista ?? this.pista,
        entraAntes: entraAntes ?? this.entraAntes,
        fundido: fundido ?? this.fundido,
        graves: graves ?? this.graves,
      );

  Map<String, dynamic> aJson() => {
        'pista': pista,
        'entra_antes': entraAntes,
        'fundido': fundido,
        'graves': graves,
      };

  static PasoMezcla? deJson(Object? d) {
    if (d is! Map || d['pista'] is! Map) return null;
    double num_(Object? v, double defecto) => v is num ? v.toDouble() : defecto;
    return PasoMezcla(
      pista: Map<String, dynamic>.from(d['pista'] as Map),
      entraAntes: num_(d['entra_antes'], 8).clamp(entraMin, entraMax),
      fundido: num_(d['fundido'], 8).clamp(fundidoMin, fundidoMax),
      graves: d['graves'] is bool ? d['graves'] as bool : true,
    );
  }
}

/// Un set guardado con nombre.
class Mezcla {
  Mezcla({required this.id, required this.nombre, required this.pasos, DateTime? creada})
      : creada = creada ?? DateTime.now();

  final String id;
  final String nombre;
  final List<PasoMezcla> pasos;
  final DateTime creada;

  Map<String, dynamic> aJson() => {
        'id': id,
        'nombre': nombre,
        'creada': creada.millisecondsSinceEpoch,
        'pasos': [for (final p in pasos) p.aJson()],
      };

  static Mezcla? deJson(Object? d) {
    if (d is! Map) return null;
    final pasos = <PasoMezcla>[
      for (final p in (d['pasos'] is List ? d['pasos'] as List : const []))
        if (PasoMezcla.deJson(p) != null) PasoMezcla.deJson(p)!
    ];
    final nombre = '${d['nombre'] ?? ''}'.trim();
    if (pasos.isEmpty || nombre.isEmpty) return null;
    final c = d['creada'];
    return Mezcla(
      id: '${d['id'] ?? nombre}',
      nombre: nombre,
      pasos: pasos,
      creada: c is num ? DateTime.fromMillisecondsSinceEpoch(c.toInt()) : null,
    );
  }
}

/// Pasos con los mismos ajustes para todas las canciones (el punto de partida
/// al armar un set).
List<PasoMezcla> pasosPorDefecto(List<Map<String, dynamic>> pistas,
        {double segundos = 8, bool graves = true}) =>
    [
      for (final p in pistas)
        PasoMezcla(pista: p, entraAntes: segundos, fundido: segundos, graves: graves),
    ];

/// Cuanto dura el set entero, en segundos: cada cancion se solapa con la
/// siguiente (la siguiente entra cuando a la actual le faltan `entraAntes`).
double duracionDelSet(List<PasoMezcla> pasos) {
  var total = 0.0;
  for (final (i, p) in pasos.indexed) {
    final d = p.duracionPista > 0 ? p.duracionPista : 210.0; // sin dato: una cancion normal
    total += i == pasos.length - 1 ? d : max(0.0, d - p.entraEfectivo);
  }
  return total;
}

// ------------------------------------------------------------ cambio de graves

/// Lo que se baja el grave, en dB, cuando esta del todo cortado.
const int dbGravesCortados = -18;

double _suave(double t) {
  final x = t.clamp(0.0, 1.0);
  return x * x * (3 - 2 * x);
}

/// Cuanto grave (en dB, multiplo de 6 entre -18 y 0) tiene una cancion cuando
/// el cambio va por [avance] (0 al empezar, 1 al terminar).
///
/// Es el cambio de graves de un DJ: la que se va los pierde hacia el 35-60 %
/// del cambio, y la que llega entra sin ellos y los recupera hacia el 40-65 %,
/// asi nunca suenan dos graves a la vez. Va en saltos de 6 dB para no tener
/// que reajustar el filtro del motor a cada fotograma.
int dbGraves(double avance, {required bool entrante}) {
  final a = avance.clamp(0.0, 1.0);
  final corte = entrante ? 1 - _suave((a - 0.40) / 0.25) : _suave((a - 0.35) / 0.25);
  final db = dbGravesCortados * corte;
  return (db / 6).round() * 6;
}

/// El filtro de mpv (`af`) que baja los graves [db] dB, o '' si no hay que
/// bajar nada. Solo usa `equalizer`, que es lo unico que traen los motores del
/// telefono.
String filtroGraves(int db) {
  if (db >= 0) return '';
  final suave = (db * 2 / 3).round();
  return 'lavfi=[equalizer=f=60:t=o:w=2:g=$db,equalizer=f=140:t=o:w=2:g=$suave]';
}

/// Suma [extra] a una cadena de filtros de mpv que ya existe ([base]).
String sumarFiltro(String base, String extra) {
  if (extra.isEmpty) return base;
  if (base.isEmpty) return extra;
  return '$base,$extra';
}

// ------------------------------------------------------------ mezclas guardadas

/// Guarda y lee los sets con nombre (en el estado de la coleccion: viajan con
/// la copia de seguridad del telefono, sin tocar la base).
class Mezclas {
  Mezclas._();

  static const _clave = 'mezclas_dj';

  static Future<List<Mezcla>> leer(Coleccion c) async {
    final d = await c.estado(_clave);
    final lista = d is Map ? d['mezclas'] : (d is String ? _decodificar(d) : null);
    return [
      for (final m in (lista is List ? lista : const []))
        if (Mezcla.deJson(m) != null) Mezcla.deJson(m)!
    ];
  }

  static dynamic _decodificar(String s) {
    try {
      final r = jsonDecode(s);
      return r is Map ? r['mezclas'] : null;
    } catch (_) {
      return null;
    }
  }

  static Future<void> _escribir(Coleccion c, List<Mezcla> todas) =>
      c.guardarEstado(_clave, {'mezclas': [for (final m in todas) m.aJson()]});

  /// Guarda un set con ese nombre; si ya hay uno con el mismo nombre lo reemplaza.
  static Future<Mezcla> guardar(Coleccion c, String nombre, List<PasoMezcla> pasos) async {
    nombre = nombre.trim();
    if (nombre.isEmpty) throw const FormatException('La mezcla necesita un nombre.');
    if (pasos.length < 2) throw const FormatException('Una mezcla necesita al menos dos canciones.');
    final todas = await leer(c);
    final id = todas.where((m) => m.nombre.toLowerCase() == nombre.toLowerCase()).firstOrNull?.id ??
        'mezcla_${DateTime.now().millisecondsSinceEpoch}';
    final nueva = Mezcla(id: id, nombre: nombre, pasos: List.of(pasos));
    await _escribir(c, [nueva, ...todas.where((m) => m.id != id)]);
    return nueva;
  }

  static Future<void> borrar(Coleccion c, String id) async =>
      _escribir(c, [for (final m in await leer(c)) if (m.id != id) m]);
}
