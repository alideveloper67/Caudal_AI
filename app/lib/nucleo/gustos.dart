import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'nube.dart';

/// Un artista que la persona eligió como favorito (al crear la cuenta o en
/// Ajustes → «Mis artistas favoritos»).
class ArtistaGusto {
  const ArtistaGusto({required this.nombre, this.id = '', this.portada = ''});

  final String nombre;
  final String id;
  final String portada;

  /// Con qué se reconoce: el id si lo hay, si no el nombre.
  String get clave => id.isNotEmpty ? 'id:$id' : 'n:${nombre.trim().toLowerCase()}';

  /// Las claves con las que casa con [artistasDe]: por id y por nombre.
  Set<String> get claves => {
        if (id.isNotEmpty) 'id:$id',
        'n:${nombre.trim().toLowerCase()}',
      };

  Map<String, dynamic> toJson() => {'nombre': nombre, 'id': id, 'portada': portada};

  static ArtistaGusto? desde(dynamic d) {
    if (d is! Map) return null;
    final nombre = '${d['nombre'] ?? ''}'.trim();
    if (nombre.isEmpty) return null;
    return ArtistaGusto(nombre: nombre, id: '${d['id'] ?? ''}', portada: '${d['portada'] ?? ''}');
  }

  @override
  bool operator ==(Object other) => other is ArtistaGusto && other.clave == clave;

  @override
  int get hashCode => clave.hashCode;
}

/// Los artistas favoritos de la cuenta: se guardan en la nube
/// (`perfiles.gustos` y `perfiles.gustos_elegidos`) con copia en este equipo
/// por si no hay red (se reintenta al volver).
class Gustos {
  Gustos._();

  /// Lo sugerido: al menos tres; el tope son 30.
  static const sugeridos = 3;
  static const maximo = 30;

  /// Los gustos de la cuenta abierta; el recomendador y el Inicio los leen de aquí.
  static List<ArtistaGusto> actuales = [];

  static String _kLista(String cuenta) => 'gustos.lista.$cuenta';
  static String _kListo(String cuenta) => 'gustos.listo.$cuenta';
  static String _kPendiente(String cuenta) => 'gustos.pendiente.$cuenta';

  /// De lo que llega de la base (`jsonb`) a una lista limpia, sin repetidos y con tope.
  static List<ArtistaGusto> leerLista(dynamic crudo) {
    dynamic d = crudo;
    if (d is String) {
      try {
        d = jsonDecode(d);
      } catch (_) {
        d = null;
      }
    }
    final salida = <ArtistaGusto>[];
    if (d is List) {
      for (final e in d) {
        final a = ArtistaGusto.desde(e);
        if (a != null && !salida.contains(a)) salida.add(a);
        if (salida.length >= maximo) break;
      }
    }
    return salida;
  }

  static Future<List<ArtistaGusto>> _localLista(String cuenta) async {
    try {
      final p = await SharedPreferences.getInstance();
      return leerLista(p.getString(_kLista(cuenta)));
    } catch (_) {
      return [];
    }
  }

  /// La copia de este equipo: ¿ya se eligió (o se omitió)?, ¿falta subirlo?
  static Future<({bool listo, bool pendiente})> local(String cuenta) async {
    try {
      final p = await SharedPreferences.getInstance();
      return (listo: p.getBool(_kListo(cuenta)) ?? false, pendiente: p.getBool(_kPendiente(cuenta)) ?? false);
    } catch (_) {
      return (listo: false, pendiente: false);
    }
  }

  /// Carga los gustos de la cuenta en [actuales] y dice si hay que preguntarlos.
  ///
  /// Pregunta solo si la base dice `gustos_elegidos = false` y aquí tampoco se
  /// eligió. Sin red o con cualquier fallo NO pregunta (nunca se bloquea la entrada).
  static Future<bool> prepararSesion(Sesion? s, String cuenta,
      {Duration espera = const Duration(seconds: 5)}) async {
    final l = await local(cuenta);
    if (l.listo) {
      actuales = await _localLista(cuenta);
      if (l.pendiente && s != null) {
        // lo elegido sin red se sube ahora
        await reintentar(s, cuenta);
      }
      return false;
    }
    if (s == null) return false;
    try {
      final filas = await s.pedir('GET', 'perfiles?select=gustos,gustos_elegidos&id=eq.${s.userId}').timeout(espera);
      if (filas is! List || filas.isEmpty || filas.first is! Map) return false;
      final f = filas.first as Map;
      final lista = leerLista(f['gustos']);
      if (f['gustos_elegidos'] == true) {
        actuales = lista;
        await _guardarLocal(cuenta, lista, pendiente: false);
        return false;
      }
      actuales = lista;
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Lo que hay ahora para editarlo (primero la copia local, si no, la base).
  static Future<List<ArtistaGusto>> actualesDe(Sesion? s, String cuenta) async {
    if (actuales.isNotEmpty) return List.of(actuales);
    final l = await _localLista(cuenta);
    if (l.isNotEmpty) return l;
    if (s == null) return [];
    try {
      final filas = await s.pedir('GET', 'perfiles?select=gustos&id=eq.${s.userId}').timeout(const Duration(seconds: 5));
      if (filas is List && filas.isNotEmpty && filas.first is Map) {
        return leerLista((filas.first as Map)['gustos']);
      }
    } catch (_) {}
    return [];
  }

  static Future<void> _guardarLocal(String cuenta, List<ArtistaGusto> lista, {required bool pendiente}) async {
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_kLista(cuenta), jsonEncode([for (final a in lista) a.toJson()]));
      await p.setBool(_kListo(cuenta), true);
      await p.setBool(_kPendiente(cuenta), pendiente);
    } catch (_) {}
  }

  /// Guarda los gustos (lista vacía = «omitir»). Siempre queda la copia local;
  /// devuelve `true` si también se subió a la nube y `false` si quedó pendiente.
  static Future<bool> guardar(Sesion? s, String cuenta, List<ArtistaGusto> lista) async {
    final limpia = leerLista([for (final a in lista) a.toJson()]);
    actuales = limpia;
    await _guardarLocal(cuenta, limpia, pendiente: s != null);
    if (s == null) return false;
    return _subir(s, cuenta, limpia);
  }

  static Future<bool> _subir(Sesion s, String cuenta, List<ArtistaGusto> lista) async {
    try {
      await s.pedir('PATCH', 'perfiles?id=eq.${s.userId}',
          cuerpo: {'gustos': [for (final a in lista) a.toJson()], 'gustos_elegidos': true});
      await _guardarLocal(cuenta, lista, pendiente: false);
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Si quedó algo sin subir, lo intenta de nuevo (se llama al volver la red).
  static Future<bool> reintentar(Sesion s, String cuenta) async {
    final l = await local(cuenta);
    if (!l.pendiente) return true;
    return _subir(s, cuenta, await _localLista(cuenta));
  }
}
