import 'dart:async';
import 'dart:math';

import 'catalogo.dart';
import 'coleccion.dart';
import 'mixes.dart';

/// Recomendaciones que aprenden de ti: canciones parecidas a una dada,
/// "Descubre para ti" (canciones que aún no has oído) y la radio automática.
///
/// Mezcla varias señales:
///  * lo que escuchas (y cuánto hace: lo reciente pesa más),
///  * lo que saltas antes de 30 s (esa canción y, si se repite, ese artista),
///  * la radio y los "relacionados" de YouTube Music de varias canciones a la
///    vez, combinados por posición (una canción que sale en varias listas sube).
///
/// La lógica de puntuar es pura (recibe un [Gusto]) para poder probarla.
class Gusto {
  Gusto({this.artistas = const {}, this.oidas = const {}, this.recientes = const {},
      this.saltos = const {}, this.saltosArtista = const {}});

  /// Afinidad 0..1 con cada artista (clave de [artistasDe]).
  final Map<String, double> artistas;

  /// Canciones que ya escuchaste alguna vez (video id).
  final Set<String> oidas;

  /// Las de los últimos días (para no repetirlas en la radio).
  final Set<String> recientes;

  /// Veces que saltaste cada canción.
  final Map<String, int> saltos;

  /// Veces que saltaste canciones de cada artista.
  final Map<String, int> saltosArtista;

  static Gusto desde(List<Escucha> historial, Map<String, dynamic> saltosGuardados, {DateTime? ahora}) {
    final hoy = ahora ?? DateTime.now();
    final peso = <String, double>{};
    final oidas = <String>{};
    final recientes = <String>{};
    for (final e in historial) {
      final vid = e.videoId;
      if (vid.isNotEmpty) {
        oidas.add(vid);
        if (hoy.difference(e.fecha).inDays < 4) recientes.add(vid);
      }
      final edad = max(0.0, hoy.difference(e.fecha).inHours / 24.0);
      final w = pow(0.5, edad / 30).toDouble();
      for (final (i, a) in e.artistas.indexed) {
        peso[a.clave] = (peso[a.clave] ?? 0) + (i == 0 ? w : w * 0.5);
      }
    }
    final maximo = peso.values.fold<double>(0, max);
    final artistas = {for (final e in peso.entries) e.key: maximo > 0 ? e.value / maximo : 0.0};
    final saltos = <String, int>{};
    final saltosArtista = <String, int>{};
    final s = saltosGuardados['canciones'];
    if (s is Map) {
      for (final e in s.entries) {
        final n = e.value is num ? (e.value as num).toInt() : 0;
        if (n > 0) saltos['${e.key}'] = n;
      }
    }
    final sa = saltosGuardados['artistas'];
    if (sa is Map) {
      for (final e in sa.entries) {
        final n = e.value is num ? (e.value as num).toInt() : 0;
        if (n > 0) saltosArtista['${e.key}'] = n;
      }
    }
    return Gusto(artistas: artistas, oidas: oidas, recientes: recientes, saltos: saltos,
        saltosArtista: saltosArtista);
  }

  /// ¿La quitamos? Saltada dos veces, o de un artista que saltas siempre
  /// (al menos 4 saltos y casi no lo escuchas).
  bool descartada(Json p) {
    final vid = '${p['video_id'] ?? ''}';
    if ((saltos[vid] ?? 0) >= 2) return true;
    for (final a in artistasDe(p)) {
      if ((saltosArtista[a.clave] ?? 0) >= 4 && (artistas[a.clave] ?? 0) < 0.15) return true;
    }
    return false;
  }

  /// Afinidad con el artista principal de la pista (0..1).
  double afinidad(Json p) {
    var m = 0.0;
    for (final a in artistasDe(p)) {
      m = max(m, artistas[a.clave] ?? 0);
    }
    return m;
  }
}

class Recomendador {
  Recomendador._();

  static const _claveSaltos = 'saltos';
  static const _claveDescubre = 'descubre_dia';

  // ------------------------------------------------------------ señales

  /// Se llama al saltar una canción antes de que cuente como escuchada.
  static Future<void> anotarSalto(Coleccion c, Json pista) async {
    final vid = '${pista['video_id'] ?? ''}';
    if (vid.isEmpty) return;
    final g = await c.estado(_claveSaltos);
    final datos = g is Map ? Map<String, dynamic>.from(g) : <String, dynamic>{};
    final canciones = Map<String, dynamic>.from((datos['canciones'] as Map?) ?? {});
    final artistas = Map<String, dynamic>.from((datos['artistas'] as Map?) ?? {});
    canciones[vid] = ((canciones[vid] as num?) ?? 0) + 1;
    for (final a in artistasDe(pista).take(1)) {
      artistas[a.clave] = ((artistas[a.clave] as num?) ?? 0) + 1;
    }
    // que no crezca sin fin: se quedan los 400 últimos
    while (canciones.length > 400) {
      canciones.remove(canciones.keys.first);
    }
    while (artistas.length > 300) {
      artistas.remove(artistas.keys.first);
    }
    await c.guardarEstado(_claveSaltos, {'canciones': canciones, 'artistas': artistas});
  }

  /// Si una canción saltada antes se escucha entera, se le perdona un salto.
  static Future<void> perdonar(Coleccion c, Json pista) async {
    final vid = '${pista['video_id'] ?? ''}';
    final g = await c.estado(_claveSaltos);
    if (g is! Map || vid.isEmpty) return;
    final canciones = Map<String, dynamic>.from((g['canciones'] as Map?) ?? {});
    final n = (canciones[vid] as num?) ?? 0;
    if (n <= 0) return;
    if (n <= 1) {
      canciones.remove(vid);
    } else {
      canciones[vid] = n - 1;
    }
    await c.guardarEstado(_claveSaltos, {...Map<String, dynamic>.from(g), 'canciones': canciones});
  }

  static Future<Gusto> gusto(Coleccion c) async {
    final historial = await Historial.leer(c,
        desde: DateTime.now().subtract(const Duration(days: 180)), limite: 8000);
    final s = await c.estado(_claveSaltos);
    return Gusto.desde(historial, s is Map ? Map<String, dynamic>.from(s) : {});
  }

  // ------------------------------------------------------------ lógica pura

  /// Junta varias listas ordenadas en una: cada canción suma más cuanto más
  /// arriba sale en cada lista (una que sale en tres listas gana a una que
  /// sale primera en una sola).
  static List<(Json, double)> combinar(List<List<Json>> listas) {
    final puntos = <String, double>{};
    final pistas = <String, Json>{};
    for (final l in listas) {
      final vistos = <String>{};
      for (final (i, p) in l.indexed) {
        final vid = '${p['video_id'] ?? ''}';
        if (vid.isEmpty || !vistos.add(vid)) continue;
        puntos[vid] = (puntos[vid] ?? 0) + 1 / (i + 3);
        pistas.putIfAbsent(vid, () => p);
      }
    }
    final orden = puntos.keys.toList()..sort((a, b) => puntos[b]!.compareTo(puntos[a]!));
    return [for (final k in orden) (pistas[k]!, puntos[k]!)];
  }

  /// Como mucho [porArtista] canciones de cada artista, sin perder el orden.
  static List<Json> diversificar(List<Json> pistas, {int porArtista = 2, int largo = 30}) {
    final cuenta = <String, int>{};
    final salida = <Json>[];
    final resto = <Json>[];
    for (final p in pistas) {
      final a = artistasDe(p).firstOrNull?.clave ?? '?';
      if ((cuenta[a] ?? 0) >= porArtista) {
        resto.add(p);
        continue;
      }
      cuenta[a] = (cuenta[a] ?? 0) + 1;
      salida.add(p);
      if (salida.length >= largo) return salida;
    }
    // si faltan, se rellena con las apartadas
    for (final p in resto) {
      if (salida.length >= largo) break;
      salida.add(p);
    }
    return salida;
  }

  /// Ordena candidatas para "Descubre": nada que ya oíste ni que saltas; los
  /// artistas que te gustan suben, pero se deja sitio a artistas nuevos.
  static List<Json> puntuarDescubre(List<(Json, double)> candidatas, Gusto g, {int largo = 30}) {
    final puntuadas = <(Json, double)>[];
    for (final (p, base) in candidatas) {
      final vid = '${p['video_id'] ?? ''}';
      if (g.oidas.contains(vid) || g.descartada(p)) continue;
      if (p['es_video'] == true && '${p['artista'] ?? ''}'.isEmpty) continue;
      final af = g.afinidad(p);
      // un artista conocido suma, pero no tanto como para tapar lo nuevo
      puntuadas.add((p, base * (1 + 0.6 * af)));
    }
    puntuadas.sort((a, b) => b.$2.compareTo(a.$2));
    final conocidas = <Json>[];
    final nuevas = <Json>[];
    for (final (p, _) in puntuadas) {
      (g.afinidad(p) > 0.05 ? conocidas : nuevas).add(p);
    }
    // mitad y mitad, alternando: descubrir sin que suene a desconocido
    final mezcla = <Json>[];
    for (var i = 0; i < max(conocidas.length, nuevas.length); i++) {
      if (i < nuevas.length) mezcla.add(nuevas[i]);
      if (i < conocidas.length) mezcla.add(conocidas[i]);
    }
    return diversificar(mezcla, porArtista: 2, largo: largo);
  }

  /// Ordena candidatas parecidas a una canción: se quita la propia y lo que
  /// saltas; lo que encaja con tu gusto sube un poco.
  static List<Json> puntuarSimilares(Json semilla, List<(Json, double)> candidatas, Gusto g,
      {int largo = 30}) {
    final propia = '${semilla['video_id'] ?? ''}';
    final lista = <(Json, double)>[
      for (final (p, base) in candidatas)
        if ('${p['video_id']}' != propia && !g.descartada(p)) (p, base * (1 + 0.3 * g.afinidad(p))),
    ]..sort((a, b) => b.$2.compareTo(a.$2));
    return diversificar([for (final (p, _) in lista) p], porArtista: 2, largo: largo);
  }

  /// Las canciones de la radio automática, sin las que saltas ni las que
  /// sonaron estos días (si quedan suficientes).
  static List<Json> limpiarRadio(List<Json> pistas, Gusto g) {
    final sinSaltos = [for (final p in pistas) if (!g.descartada(p)) p];
    final frescas = [for (final p in sinSaltos) if (!g.recientes.contains('${p['video_id']}')) p];
    return frescas.length >= 8 ? frescas : sinSaltos;
  }

  /// Tus canciones más tuyas de estos meses, de artistas distintos.
  static List<String> semillas(List<Escucha> historial, {int n = 6, DateTime? ahora}) {
    final hoy = ahora ?? DateTime.now();
    final peso = <String, double>{};
    final artista = <String, String>{};
    for (final e in historial) {
      final vid = e.videoId;
      if (vid.length != 11) continue;
      final edad = max(0.0, hoy.difference(e.fecha).inHours / 24.0);
      peso[vid] = (peso[vid] ?? 0) + pow(0.5, edad / 21).toDouble();
      artista.putIfAbsent(vid, () => e.artistas.firstOrNull?.clave ?? vid);
    }
    final orden = peso.keys.toList()..sort((a, b) => peso[b]!.compareTo(peso[a]!));
    final usados = <String>{};
    final salida = <String>[];
    for (final vid in orden) {
      if (!usados.add(artista[vid]!)) continue;
      salida.add(vid);
      if (salida.length == n) break;
    }
    return salida;
  }

  // ------------------------------------------------------------ con red

  static Future<List<Json>> _radio(String videoId) async {
    try {
      final r = await Catalogo.radio(videoId: videoId, limite: 40).timeout(const Duration(seconds: 20));
      return [
        for (final e in (r['pistas'] is List ? r['pistas'] as List : const []))
          if (e is Map && e['tipo'] == 'pista') Map<String, dynamic>.from(e)
      ];
    } catch (_) {
      return [];
    }
  }

  static Future<List<Json>> _relacionados(String videoId) async {
    try {
      final secciones = await Catalogo.relacionados(videoId).timeout(const Duration(seconds: 20));
      return [
        for (final s in secciones)
          for (final e in (s['elementos'] is List ? s['elementos'] as List : const []))
            if (e is Map && e['tipo'] == 'pista') Map<String, dynamic>.from(e)
      ];
    } catch (_) {
      return [];
    }
  }

  /// "Canciones similares" a una canción.
  static Future<Json> similares(Coleccion c, Json pista) async {
    final vid = '${pista['video_id'] ?? ''}';
    final resultados = await Future.wait([_radio(vid), _relacionados(vid), gusto(c)]);
    final radio = resultados[0] as List<Json>;
    final rel = resultados[1] as List<Json>;
    final g = resultados[2] as Gusto;
    // la radio de la radio: dos canciones de arriba aportan su propia lista
    final segundas = await Future.wait([
      for (final p in radio.skip(1).take(2)) _radio('${p['video_id']}'),
    ]);
    final pistas = puntuarSimilares(pista, combinar([radio, rel, rel, ...segundas]), g);
    final titulo = '${pista['titulo'] ?? ''}';
    return {
      'tipo': 'mix',
      'id': 'similares_$vid',
      'titulo': 'Similares a «$titulo»',
      'subtitulo': 'Elegidas por cómo suena y por lo que escuchas',
      'miniatura': '${pista['miniatura'] ?? ''}',
      'pistas': pistas,
      'total': pistas.length,
    };
  }

  /// "Descubre para ti": se arma una vez al día.
  static Future<Json?> descubrir(Coleccion c, {DateTime? ahora}) async {
    final hoy = ahora ?? DateTime.now();
    final dia = claveDia(hoy);
    final guardado = await c.estado(_claveDescubre);
    if (guardado is Map && guardado['dia'] == dia && guardado['mix'] is Map) {
      return Map<String, dynamic>.from(guardado['mix'] as Map);
    }
    final historial = await Historial.leer(c, desde: hoy.subtract(const Duration(days: 180)), limite: 8000);
    if (historial.length < 5) return null;
    final s = await c.estado(_claveSaltos);
    final g = Gusto.desde(historial, s is Map ? Map<String, dynamic>.from(s) : {}, ahora: hoy);
    final sem = semillas(historial, ahora: hoy);
    if (sem.isEmpty) return null;
    final listas = await Future.wait([for (final v in sem) _radio(v)]);
    if (listas.every((l) => l.isEmpty)) return null; // sin red: se intenta luego
    final pistas = puntuarDescubre(combinar(listas), g);
    if (pistas.length < 5) return null;
    final mix = {
      'tipo': 'mix',
      'id': 'descubre_para_ti',
      'titulo': 'Descubre para ti',
      'subtitulo': 'Canciones que aún no has oído, elegidas por lo que escuchas',
      'miniatura': '${pistas.first['miniatura'] ?? ''}',
      'miniaturas': [for (final p in pistas.take(4)) '${p['miniatura'] ?? ''}'],
      'color': 0xFF7C5CFF,
      'pistas': [for (final p in pistas) Coleccion.paraNube(p)],
      'total': pistas.length,
      'dia': dia,
    };
    await c.guardarEstado(_claveDescubre, {'dia': dia, 'mix': mix});
    return mix;
  }

  // ------------------------------------------------------------ máquina del tiempo

  /// "Máquina del tiempo": lo que escuchabas hace un mes, tres, seis, un año.
  static List<Json> maquinaDelTiempo(List<Escucha> historial, {DateTime? ahora}) {
    final hoy = ahora ?? DateTime.now();
    const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
      'septiembre', 'octubre', 'noviembre', 'diciembre'];
    final salida = <Json>[];
    for (final (dias, titulo) in const [(365, 'Hace un año'), (182, 'Hace seis meses'),
      (91, 'Hace tres meses'), (30, 'Hace un mes')]) {
      final centro = hoy.subtract(Duration(days: dias));
      final cuenta = <String, int>{};
      final pistas = <String, Json>{};
      for (final e in historial) {
        if (e.fecha.difference(centro).inDays.abs() > 7 || e.clave.isEmpty) continue;
        cuenta[e.clave] = (cuenta[e.clave] ?? 0) + 1;
        pistas.putIfAbsent(e.clave, () => e.pista);
      }
      if (pistas.length < 5) continue;
      final orden = cuenta.keys.toList()..sort((a, b) => cuenta[b]!.compareTo(cuenta[a]!));
      final lista = [for (final k in orden.take(40)) pistas[k]!];
      salida.add({
        'tipo': 'mix',
        'id': 'tiempo_$dias',
        'titulo': titulo,
        'subtitulo': 'Lo que sonaba a mediados de ${meses[centro.month - 1]} de ${centro.year}',
        'miniatura': '${lista.first['miniatura'] ?? ''}',
        'pistas': [for (final p in lista) Coleccion.paraNube(p)],
        'total': lista.length,
      });
    }
    return salida;
  }

  static Future<List<Json>> maquinaDelTiempoDe(Coleccion c) async {
    final historial = await Historial.leer(c,
        desde: DateTime.now().subtract(const Duration(days: 380)), limite: 40000);
    return maquinaDelTiempo(historial);
  }
}
