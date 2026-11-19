import 'dart:math';

import 'catalogo.dart';
import 'coleccion.dart';
import 'estudio.dart';
import 'mixes.dart';
import 'ritmo.dart';

/// Los modos de escucha: una forma de oír música según lo que estás haciendo.
enum ModoEscucha { concentracion, dormir, ejercicio }

/// Qué tan fuerte es el ejercicio: decide el tempo (pulsos por minuto) de la música.
enum IntensidadEjercicio {
  suave('Suave', 'Caminar o estirar', 95, 125),
  medio('Medio', 'Trotar o bailar', 120, 150),
  intenso('Intenso', 'Correr o pesas', 140, 185);

  const IntensidadEjercicio(this.nombre, this.detalle, this.bpmMin, this.bpmMax);
  final String nombre;
  final String detalle;
  final int bpmMin;
  final int bpmMax;

  List<String> get consultas => switch (this) {
        suave => ['upbeat walking playlist', 'feel good morning workout', 'música para caminar y animarse'],
        medio => ['workout music mix', 'cardio workout playlist', 'música para hacer ejercicio animada'],
        intenso => ['gym workout motivation music', 'running playlist 160 bpm', 'música para entrenar fuerte gym'],
      };
}

/// La música de cada modo. La parte de armar la lista es pura (recibe lo que haya y devuelve
/// la cola) para poder probarla sin red.
class ModosEscucha {
  ModosEscucha._();

  /// Cuánto puede durar el temporizador del modo Dormir.
  static const minutosDormir = [15, 30, 45, 60, 90];

  /// La clave de la colección donde se guardan los ritmos ya analizados (la misma del Mezclador).
  static const claveRitmos = 'ritmo_cache';

  /// Con menos canciones propias que esto, se completan con búsquedas.
  static const minimoPropias = 8;
  static const largoCola = 40;

  static List<String> consultasConcentracion({PerfilEstudio perfil = PerfilEstudio.leer}) => perfil.consultas;

  static const consultasDormir = [
    'música para dormir relajante sin letra',
    'sleep music calm piano ambient',
    'sonidos suaves para dormir profundamente',
  ];

  /// Canciones instrumentales y calmadas primero (reutiliza el filtro del Modo estudio).
  static List<Json> soloCalma(List<Json> pistas, {int largo = largoCola}) =>
      CuraduriaEstudio.filtrar(pistas).take(largo).toList();

  /// De [candidatas] se quedan las que tienen un tempo conocido entre [min] y [max], de menos a
  /// más (el calentamiento primero). Las de ritmo manual valen aunque la confianza sea baja.
  static List<Json> porTempo(List<Json> candidatas, Map<String, AnalisisRitmo> ritmo,
      {required int min, required int max, int largo = largoCola}) {
    final vistos = <String>{};
    final con = <(Json, double)>[];
    for (final p in candidatas) {
      final k = '${p['clave'] ?? ''}';
      if (k.isEmpty || !vistos.add(k)) continue;
      final a = ritmo[k];
      if (a == null || !a.valido) continue;
      if (!a.manual && a.confianza < 0.2) continue;
      if (a.bpm < min || a.bpm > max) continue;
      con.add((p, a.bpm));
    }
    con.sort((x, y) => x.$2.compareTo(y.$2));
    if (con.length <= largo) return [for (final c in con) c.$1];
    // más de las que caben: se reparten parejo a lo largo del recorrido de menos a más
    final paso = con.length / largo;
    return [for (var i = 0; i < largo; i++) con[_menor((i * paso).floor(), con.length - 1)].$1];
  }

  static int _menor(int a, int b) => a < b ? a : b;

  /// Los ritmos ya analizados que guarda la app (clave de canción -> ritmo).
  static Future<Map<String, AnalisisRitmo>> ritmosGuardados(Coleccion c) async {
    final salida = <String, AnalisisRitmo>{};
    try {
      final d = await c.estado(claveRitmos);
      if (d is Map) {
        for (final e in d.entries) {
          final a = AnalisisRitmo.deJson(e.value);
          if (a != null) salida['${e.key}'] = a;
        }
      }
    } catch (_) {}
    return salida;
  }

  /// Lo que has oído y te gusta, sin repetir: de donde salen las canciones de «Ejercicio por tempo».
  static Future<List<Json>> _propias(Coleccion c) async {
    final salida = <String, Json>{};
    try {
      for (final p in await c.meGustaRecientes(400)) {
        salida.putIfAbsent('${p['clave'] ?? ''}', () => p);
      }
    } catch (_) {}
    try {
      final h = await Historial.leer(c, desde: DateTime.now().subtract(const Duration(days: 365)), limite: 8000);
      for (final e in h) {
        salida.putIfAbsent(e.clave, () => e.pista);
      }
    } catch (_) {}
    salida.remove('');
    return salida.values.toList();
  }

  static Future<List<Json>> _buscarVarias(List<String> consultas, BuscarCatalogo buscar, {int limite = 20}) async {
    Future<List<Json>> segura(String q) async {
      try {
        return await buscar(q, filtro: 'canciones', limite: limite);
      } catch (_) {
        return <Json>[]; // una búsqueda que falla no tumba el modo
      }
    }

    final listas = await Future.wait([for (final q in consultas) segura(q)]);
    // intercaladas: una de cada búsqueda, para que no sea todo de un mismo estilo
    final salida = <Json>[];
    final vistos = <String>{};
    for (var i = 0; i < limite; i++) {
      for (final l in listas) {
        if (i >= l.length) continue;
        final id = '${l[i]['video_id'] ?? l[i]['clave'] ?? ''}';
        if (id.isNotEmpty && vistos.add(id)) salida.add(l[i]);
      }
    }
    return salida;
  }

  /// La cola de «Concentración»: instrumental, sin voz que distraiga.
  static Future<List<Json>> concentracion({BuscarCatalogo? buscar, PerfilEstudio perfil = PerfilEstudio.leer}) async {
    final b = buscar ?? _buscarCatalogo;
    return soloCalma(await _buscarVarias(consultasConcentracion(perfil: perfil), b));
  }

  /// La cola de «Dormir»: calma y nada que sobresalte.
  static Future<List<Json>> dormir({BuscarCatalogo? buscar}) async {
    final b = buscar ?? _buscarCatalogo;
    return soloCalma(await _buscarVarias(consultasDormir, b));
  }

  /// La cola de «Ejercicio»: tu música con el tempo de la intensidad elegida, si hay ritmos
  /// conocidos de sobra; si no, completa (o arma) con búsquedas tipo «workout».
  static Future<({List<Json> pistas, bool porTempo})> ejercicio(
    IntensidadEjercicio intensidad, {
    Coleccion? coleccion,
    BuscarCatalogo? buscar,
    Map<String, AnalisisRitmo>? ritmos,
    List<Json>? propias,
  }) async {
    final b = buscar ?? _buscarCatalogo;
    var mias = <Json>[];
    if (coleccion != null || (ritmos != null && propias != null)) {
      final r = ritmos ?? await ritmosGuardados(coleccion!);
      if (r.isNotEmpty) {
        mias = porTempo(propias ?? await _propias(coleccion!), r, min: intensidad.bpmMin, max: intensidad.bpmMax);
      }
    }
    if (mias.length >= minimoPropias) return (pistas: mias, porTempo: true);
    final buscadas = await _buscarVarias(intensidad.consultas, b);
    final vistos = {for (final p in mias) '${p['clave'] ?? p['video_id']}'};
    final todas = [
      ...mias,
      for (final p in buscadas)
        if (vistos.add('${p['clave'] ?? p['video_id']}')) p,
    ];
    return (pistas: todas.take(largoCola).toList(), porTempo: mias.isNotEmpty);
  }

  static Future<List<Map<String, dynamic>>> _buscarCatalogo(String texto, {String? filtro, int limite = 20}) =>
      Catalogo.buscar(texto, filtro: filtro, limite: limite);

  /// «1 h 30 min», «45 min».
  static String textoMinutos(int m) {
    if (m < 60) return '$m min';
    final h = m ~/ 60, r = m % 60;
    return r == 0 ? '$h h' : '$h h $r min';
  }

  /// Segundos para escribirlos como reloj: 95 -> «1:35».
  static String reloj(int segundos) {
    final s = max(0, segundos);
    final m = s ~/ 60;
    return '$m:${(s % 60).toString().padLeft(2, '0')}';
  }
}
