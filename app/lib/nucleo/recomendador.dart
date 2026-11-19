import 'dart:async';
import 'dart:math';

import 'catalogo.dart';
import 'coleccion.dart';
import 'gustos.dart';
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
      this.saltos = const {}, this.saltosArtista = const {}, this.elegidos = const {},
      this.megusta = const {}, this.ultimas = const {}, this.saltadasHoy = const {},
      this.rasgos = const {}});

  /// Artistas que la persona eligió al crear su cuenta (claves `id:` y `n:`).
  final Set<String> elegidos;

  /// Artistas de las canciones con me gusta (clave de [artistasDe]).
  final Set<String> megusta;

  /// Las últimas ~50 reproducciones (video id): no se repiten en la radio.
  final Set<String> ultimas;

  /// Lo que se saltó hoy: no vuelve a salir hoy.
  final Set<String> saltadasHoy;

  /// Cuánto de lo que escuchas es de cada escritura, idioma y época (0..1).
  final Map<String, double> rasgos;

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

  static Gusto desde(List<Escucha> historial, Map<String, dynamic> saltosGuardados,
      {DateTime? ahora, List<ArtistaGusto> elegidos = const [], List<Json> megusta = const []}) {
    final hoy = ahora ?? DateTime.now();
    final peso = <String, double>{};
    final oidas = <String>{};
    final recientes = <String>{};
    final rasgos = <String, double>{};
    for (final e in historial) {
      // una escucha (contada a los 30 s) pesa más cuanto más reciente es
      final wr = pow(0.5, max(0.0, hoy.difference(e.fecha).inHours / 24.0) / 45).toDouble();
      for (final r in Rasgos.de(e.pista)) {
        rasgos[r] = (rasgos[r] ?? 0) + wr;
      }
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
    // el ánimo de lo último que sonó pesa más: si vienes oyendo tristes, la radio sigue ahí
    for (final e in historial.reversed.take(8)) {
      for (final r in Rasgos.de(e.pista)) {
        if (r.startsWith('animo:')) rasgos[r] = (rasgos[r] ?? 0) + 1.5;
      }
    }
    final topeRasgo = rasgos.values.fold<double>(0, max);
    if (topeRasgo > 0) {
      for (final k in rasgos.keys.toList()) {
        rasgos[k] = rasgos[k]! / topeRasgo;
      }
    }
    final ultimas = <String>{
      for (final e in historial.reversed.take(50))
        if (e.videoId.isNotEmpty) e.videoId
    };
    final saltadasHoy = <String>{};
    final h = saltosGuardados['hoy'];
    if (h is Map && h['dia'] == claveDia(hoy) && h['ids'] is List) {
      for (final v in h['ids'] as List) {
        saltadasHoy.add('$v');
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
    final claves = <String>{};
    for (final a in elegidos) {
      claves.addAll(a.claves);
    }
    final gustan = <String>{
      for (final p in megusta)
        for (final a in artistasDe(p)) a.clave
    };
    return Gusto(artistas: artistas, oidas: oidas, recientes: recientes, saltos: saltos,
        saltosArtista: saltosArtista, elegidos: claves, megusta: gustan, ultimas: ultimas,
        saltadasHoy: saltadasHoy, rasgos: rasgos);
  }

  static String _nombreClave(String n) => 'n:${n.trim().toLowerCase()}';

  /// El mismo gusto con un salto mas de [pista], como lo deja
  /// [Recomendador.anotarSalto] en la base: asi no hay que releer todo el
  /// historial cada vez que se salta una canción.
  Gusto conSalto(Json pista) {
    final vid = '${pista['video_id'] ?? ''}';
    if (vid.isEmpty) return this;
    final s = Map<String, int>.of(saltos);
    s[vid] = (s[vid] ?? 0) + 1;
    final sa = Map<String, int>.of(saltosArtista);
    for (final a in artistasDe(pista).take(1)) {
      sa[a.clave] = (sa[a.clave] ?? 0) + 1;
    }
    return Gusto(artistas: artistas, oidas: oidas, recientes: recientes, saltos: s, saltosArtista: sa,
        elegidos: elegidos, megusta: megusta, ultimas: ultimas, saltadasHoy: {...saltadasHoy, vid},
        rasgos: rasgos);
  }

  /// 1 si algún artista de la pista está entre los que elegiste; si no, 0.
  double elegida(Json p) {
    for (final a in artistasDe(p)) {
      if (elegidos.contains(a.clave) || elegidos.contains(_nombreClave(a.nombre))) return 1;
    }
    return 0;
  }

  /// 1 si algún artista de la pista tiene canciones con me gusta tuyas.
  double conMeGusta(Json p) {
    for (final a in artistasDe(p)) {
      if (megusta.contains(a.clave)) return 1;
    }
    return 0;
  }

  /// ¿La quitamos? Saltada dos veces, o de un artista que saltas siempre
  /// (al menos 4 saltos y casi no lo escuchas).
  bool descartada(Json p) {
    final vid = '${p['video_id'] ?? ''}';
    if ((saltos[vid] ?? 0) >= 2) return true;
    if (elegida(p) > 0) return false; // a un artista elegido se le perdona
    for (final a in artistasDe(p)) {
      if ((saltosArtista[a.clave] ?? 0) >= 4 && (artistas[a.clave] ?? 0) < 0.15) return true;
    }
    return false;
  }

  /// Afinidad con los artistas de la pista (0..1): lo que escuchas, lo que
  /// elegiste y tus me gusta suman; los saltos restan.
  ///
  /// Las señales se combinan como pruebas independientes (1 − Π(1 − señal)):
  /// con una sola señal da lo mismo que antes, pero un artista que además de
  /// escucharlo lo marcaste con me gusta pesa más que otro con solo una de las dos.
  double afinidad(Json p) {
    var hist = 0.0;
    var salto = 0;
    for (final a in artistasDe(p)) {
      hist = max(hist, artistas[a.clave] ?? 0);
      salto = max(salto, saltosArtista[a.clave] ?? 0);
    }
    final bruta = 1 - (1 - hist) * (1 - 0.9 * elegida(p)) * (1 - 0.6 * conMeGusta(p));
    return (bruta - min(0.5, 0.12 * salto)).clamp(0.0, 1.0);
  }

  /// Cuánto encaja la pista con lo que sueles oír (escritura, idioma, época).
  double encaje(Json p) {
    final r = Rasgos.de(p);
    if (r.isEmpty || rasgos.isEmpty) return 0;
    var s = 0.0;
    for (final x in r) {
      s += rasgos[x] ?? 0;
    }
    return s / r.length;
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
    // lo saltado hoy no vuelve a salir hoy
    final dia = claveDia(DateTime.now());
    final h = datos['hoy'];
    final idsHoy = <String>[
      if (h is Map && h['dia'] == dia && h['ids'] is List) for (final v in h['ids'] as List) '$v'
    ];
    if (!idsHoy.contains(vid)) idsHoy.add(vid);
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
    await c.guardarEstado(_claveSaltos, {
      'canciones': canciones,
      'artistas': artistas,
      'hoy': {'dia': dia, 'ids': idsHoy.length > 200 ? idsHoy.sublist(idsHoy.length - 200) : idsHoy},
    });
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
    var gustan = <Json>[];
    try {
      gustan = await c.meGustaRecientes(300);
    } catch (_) {}
    return Gusto.desde(historial, s is Map ? Map<String, dynamic>.from(s) : {},
        elegidos: Gustos.actuales, megusta: gustan);
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

  /// Ordena candidatas parecidas a una canción (ver [ordenarSimilares]).
  static List<Json> puntuarSimilares(Json semilla, List<(Json, double)> candidatas, Gusto g,
          {int largo = 30, Set<String> afines = const {}}) =>
      ordenarSimilares(semilla, candidatas, g, largo: largo, afines: afines);

  /// El corazón del algoritmo de «parecidas»: puro, determinista con [azar].
  ///
  /// [candidatas] trae (pista, puntaje base) con el puntaje que dan las
  /// «siguientes» de YouTube Music y las demás fuentes (ver [combinar]);
  /// [afines] son las claves de artistas relacionados con la semilla.
  ///
  ///  * suben: mismo artista, artistas relacionados, lo que escuchas, los
  ///    artistas que elegiste, tus me gusta y lo que comparte escritura,
  ///    idioma o época con la semilla;
  ///  * bajan mucho las «ajenas» (artista sin relación con la semilla ni
  ///    contigo): así una cumbia no trae rock;
  ///  * se quitan la propia, lo saltado (hoy o varias veces) y lo oído en las
  ///    últimas ~50 reproducciones (esto último vuelve, al final, solo si falta);
  ///  * una de cada 5 (20 %) es un artista nuevo afín;
  ///  * nunca más de [maxSeguidas] del mismo artista seguidas.
  static List<Json> ordenarSimilares(Json semilla, List<(Json, double)> candidatas, Gusto g,
      {int largo = 30, Set<String> afines = const {}, int azar = 7, double descubrimiento = 0.2,
      int minimoFrescas = 8, int maxSeguidas = 2, Set<String> excluir = const {}}) {
    final propia = '${semilla['video_id'] ?? ''}';
    final claveSemilla = {for (final a in artistasDe(semilla)) a.clave};
    final nombresSemilla = {for (final a in artistasDe(semilla)) a.nombre.toLowerCase()};
    final lista = <(Json, double)>[
      for (final (p, base) in candidatas)
        if ('${p['video_id']}' != propia &&
            !excluir.contains('${p['video_id']}') &&
            !g.saltadasHoy.contains('${p['video_id']}') &&
            !g.descartada(p))
          (p, base),
    ];
    if (lista.isEmpty) return [];
    final tope = lista.map((e) => e.$2).fold<double>(0, max);
    // lo que sale mucho en la radio es del mismo círculo
    final frecuencia = <String, int>{};
    for (final (p, _) in lista) {
      for (final a in artistasDe(p).take(1)) {
        frecuencia[a.clave] = (frecuencia[a.clave] ?? 0) + 1;
      }
    }
    final rasgosSemilla = Rasgos.de(semilla);
    final rnd = Random(azar);
    final nuevoDe = <String, bool>{};
    final ajenas = <String>{};
    final puntuadas = <(Json, double)>[];
    for (final (p, base) in lista) {
      final arts = artistasDe(p);
      final mismo = arts.any((a) => claveSemilla.contains(a.clave) || nombresSemilla.contains(a.nombre.toLowerCase()));
      final relacionado = arts.any((a) => afines.contains(a.clave));
      final circulo = !relacionado && (frecuencia[arts.firstOrNull?.clave] ?? 0) >= 2;
      final hist = g.afinidad(p);
      final elegida = g.elegida(p);
      final like = g.conMeGusta(p);
      final sim = Rasgos.similitud(rasgosSemilla, Rasgos.de(p));
      final conocido = hist > 0.05 || elegida > 0 || like > 0;
      // «ajena» solo se sabe si hay con qué comparar (artistas relacionados de la semilla)
      final ajena = afines.isNotEmpty && !mismo && !relacionado && !circulo && !conocido;
      var puntos = (tope > 0 ? base / tope : 1.0) *
          (1 + 0.8 * (mismo ? 1 : 0) + 0.6 * (relacionado ? 1 : (circulo ? 0.5 : 0)) + 0.9 * hist +
              1.0 * elegida + 0.5 * like + 0.4 * sim + 0.2 * g.encaje(p));
      if (ajena) puntos *= 0.35;
      // un desajuste fuerte de escritura (latina frente a asiática) con la semilla casi la descarta
      if (sim < -0.5 && !mismo) puntos *= 0.5;
      puntos *= 1 + (rnd.nextDouble() - 0.5) * 0.04;
      puntuadas.add((p, max(0.01, puntos)));
      nuevoDe['${p['video_id']}'] = !mismo && !conocido && !ajena;
      if (ajena) ajenas.add('${p['video_id']}');
    }
    puntuadas.sort((a, b) {
      final c = b.$2.compareTo(a.$2);
      return c != 0 ? c : '${a.$1['video_id']}'.compareTo('${b.$1['video_id']}');
    });
    final ordenadas = [
      for (final (p, _) in puntuadas) if (!ajenas.contains('${p['video_id']}')) p,
    ];
    // lo ajeno (sin relacion con la semilla ni contigo) va despues de todo lo demas
    final ajenasOrdenadas = [
      for (final (p, _) in puntuadas) if (ajenas.contains('${p['video_id']}') && !g.ultimas.contains('${p['video_id']}')) p,
    ];
    final frescas = [for (final p in ordenadas) if (!g.ultimas.contains('${p['video_id']}')) p];
    final usadas = [for (final p in ordenadas) if (g.ultimas.contains('${p['video_id']}')) p];
    final todas = frescas;

    // descubrimiento: artistas nuevos afines repartidos entre las conocidas
    final nuevos = [for (final p in todas) if (nuevoDe['${p['video_id']}'] == true) p];
    final resto = [for (final p in todas) if (nuevoDe['${p['video_id']}'] != true) p];
    final cada = descubrimiento <= 0 ? 0 : max(2, (1 / descubrimiento).round());
    final mezcla = <Json>[];
    var ni = 0, ri = 0;
    while (ni < nuevos.length || ri < resto.length) {
      final toca = cada > 0 && (mezcla.length + 1) % cada == 0;
      if ((toca && ni < nuevos.length) || ri >= resto.length) {
        mezcla.add(nuevos[ni++]);
      } else {
        mezcla.add(resto[ri++]);
      }
    }
    // lo muy oido solo vuelve (al final) si no hay con que llenar
    final conRelleno = [
      ...mezcla,
      if (frescas.length < minimoFrescas) ...usadas,
    ];
    final repartidas = diversificar(conRelleno, porArtista: 5, largo: largo + 10);
    final salida = intercalar(repartidas, maxSeguidas: maxSeguidas, largo: largo);
    // lo ajeno, solo si falta para llenar y siempre al final
    for (final p in ajenasOrdenadas) {
      if (salida.length >= largo) break;
      salida.add(p);
    }
    return salida;
  }

  /// Reordena sin quitar nada para que no haya más de [maxSeguidas] canciones
  /// seguidas del mismo artista (respeta el orden de arriba en lo posible).
  static List<Json> intercalar(List<Json> pistas, {int maxSeguidas = 2, int largo = 1000}) {
    final pendientes = List<Json>.from(pistas);
    final salida = <Json>[];
    String? ultimo;
    var racha = 0;
    while (pendientes.isNotEmpty && salida.length < largo) {
      var k = pendientes.indexWhere((p) {
        final a = artistasDe(p).firstOrNull?.clave ?? '?';
        return !(a == ultimo && racha >= maxSeguidas);
      });
      if (k < 0) k = 0; // no queda otro artista: no hay remedio
      final p = pendientes.removeAt(k);
      final a = artistasDe(p).firstOrNull?.clave ?? '?';
      racha = a == ultimo ? racha + 1 : 1;
      ultimo = a;
      salida.add(p);
    }
    return salida;
  }

  /// La radio automática (la cola que sigue sonando) a partir de las
  /// «siguientes» de YouTube Music: afinada con tu gusto, sin repetir lo de
  /// las últimas ~50 reproducciones ni lo saltado, con artistas nuevos afines.
  static List<Json> prepararRadio(Json semilla, List<Json> siguientes, Gusto g,
          {Set<String> vistos = const {}, int largo = 40, int azar = 7, Set<String> afines = const {}}) =>
      ordenarSimilares(semilla, combinar([siguientes]), g,
          largo: largo, azar: azar, excluir: vistos, afines: afines);

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

  /// Canciones y artistas de las secciones «relacionado» de YouTube Music.
  static ({List<Json> pistas, Set<String> artistas}) _separarRelacionados(List<Json> elementos) => (
        pistas: [for (final e in elementos) if (e['tipo'] == 'pista') e],
        artistas: {
          for (final e in elementos)
            if (e['tipo'] == 'artista' && '${e['id'] ?? ''}'.isNotEmpty) 'id:${e['id']}'
        },
      );

  static Future<List<Json>> _elementosRelacionados(String videoId) async {
    try {
      final secciones = await Catalogo.relacionados(videoId).timeout(const Duration(seconds: 20));
      return [
        for (final s in secciones)
          for (final e in (s['elementos'] is List ? s['elementos'] as List : const []))
            if (e is Map) Map<String, dynamic>.from(e)
      ];
    } catch (_) {
      return [];
    }
  }

  /// Otras canciones del mismo artista.
  static Future<List<Json>> _delArtista(Json pista) async {
    final a = artistasDe(pista).firstOrNull;
    if (a == null) return [];
    try {
      final r = await Catalogo.buscar(a.nombre, filtro: 'canciones', limite: 12)
          .timeout(const Duration(seconds: 15));
      return [
        for (final e in r)
          if (e['tipo'] == 'pista' &&
              artistasDe(e).any((x) => x.clave == a.clave || x.nombre.toLowerCase() == a.nombre.toLowerCase()))
            e
      ];
    } catch (_) {
      return [];
    }
  }

  /// "Canciones similares" a una canción: las «siguientes» de YouTube Music,
  /// otras del mismo artista y de artistas relacionados, afinadas con tu gusto.
  static Future<Json> similares(Coleccion c, Json pista) async {
    final vid = '${pista['video_id'] ?? ''}';
    final resultados = await Future.wait<Object>([_radio(vid), _elementosRelacionados(vid), gusto(c), _delArtista(pista)]);
    final radio = resultados[0] as List<Json>;
    final rel = _separarRelacionados(resultados[1] as List<Json>);
    final g = resultados[2] as Gusto;
    final delArtista = resultados[3] as List<Json>;
    // la radio de la radio: dos canciones de arriba aportan su propia lista
    final segundas = await Future.wait([
      for (final p in radio.skip(1).take(2)) _radio('${p['video_id']}'),
    ]);
    final afines = {
      ...rel.artistas,
      for (final p in rel.pistas) for (final a in artistasDe(p).take(1)) a.clave,
    };
    final pistas = ordenarSimilares(
        pista, combinar([radio, rel.pistas, rel.pistas, delArtista, ...segundas]), g,
        afines: afines, azar: vid.hashCode);
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
    var gustan = <Json>[];
    try {
      gustan = await c.meGustaRecientes(300);
    } catch (_) {}
    final g = Gusto.desde(historial, s is Map ? Map<String, dynamic>.from(s) : {},
        ahora: hoy, elegidos: Gustos.actuales, megusta: gustan);
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

  static const _claveMaquina = 'maquina_tiempo_dia';

  /// Se arma una vez al dia (sus ventanas acaban hace mas de 3 semanas: lo de
  /// hoy no la cambia). Se rehace si cambia el dia o llegan escuchas viejas
  /// (de otro dispositivo, o si se borran).
  static Future<List<Json>> maquinaDelTiempoDe(Coleccion c) async {
    final hoy = DateTime.now();
    final corte = hoy.subtract(const Duration(days: 22)).millisecondsSinceEpoch / 1000.0;
    final f = (await c.db.rawQuery('SELECT COUNT(*) n FROM reproducciones WHERE fecha < ?', [corte])).first;
    final firma = '${claveDia(hoy)}|${f['n']}';
    try {
      final g = await c.estado(_claveMaquina);
      if (g is Map && g['firma'] == firma && g['mixes'] is List) {
        return [for (final m in g['mixes'] as List) if (m is Map) Map<String, dynamic>.from(m)];
      }
    } catch (_) {}
    final historial = await Historial.leer(c,
        desde: hoy.subtract(const Duration(days: 380)), limite: 40000);
    final mixes = maquinaDelTiempo(historial, ahora: hoy);
    try {
      await c.guardarEstado(_claveMaquina, {'firma': firma, 'mixes': mixes});
    } catch (_) {}
    return mixes;
  }

  // ------------------------------------------------------------ tu mes pasado

  static const _nombresMes = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
    'septiembre', 'octubre', 'noviembre', 'diciembre'];

  /// El nombre del mes en español (1 = enero).
  static String nombreDelMes(int mes) => _nombresMes[(mes - 1).clamp(0, 11)];

  /// Desde cuándo hay que leer el historial para armar «Tu mes pasado»: el
  /// primer día del mes calendario anterior (o, si cae más cerca, 30 días atrás).
  static DateTime desdeMesPasado({DateTime? ahora}) {
    final hoy = ahora ?? DateTime.now();
    final inicioAnterior = DateTime(hoy.year, hoy.month - 1);
    final hace30 = hoy.subtract(const Duration(days: 30));
    return inicioAnterior.isBefore(hace30) ? inicioAnterior : hace30;
  }

  /// «Tu mes pasado»: lo que más escuchaste el mes calendario anterior. Si ese
  /// mes tiene pocas canciones distintas (menos de [minimo]), se usan los
  /// últimos 30 días. Devuelve null si tampoco hay datos para eso.
  ///
  /// El resultado es un «mix» como los demás, con `nombre_lista` (el nombre con
  /// el que se guarda como lista real, p. ej. «Lo más escuchado en octubre»).
  static Json? mesPasado(List<Escucha> historial, {DateTime? ahora, int minimo = 5, int largo = 30}) {
    final hoy = ahora ?? DateTime.now();
    final inicio = DateTime(hoy.year, hoy.month - 1);
    final fin = DateTime(hoy.year, hoy.month);

    List<(Json, int)> contar(bool Function(Escucha) cuenta) {
      final veces = <String, int>{};
      final ultima = <String, DateTime>{};
      final pistas = <String, Json>{};
      for (final e in historial) {
        if (e.clave.isEmpty || !cuenta(e)) continue;
        veces[e.clave] = (veces[e.clave] ?? 0) + 1;
        if (ultima[e.clave] == null || e.fecha.isAfter(ultima[e.clave]!)) ultima[e.clave] = e.fecha;
        pistas.putIfAbsent(e.clave, () => e.pista);
      }
      // las más escuchadas primero; a igualdad, la más reciente
      final orden = veces.keys.toList()
        ..sort((a, b) {
          final c = veces[b]!.compareTo(veces[a]!);
          return c != 0 ? c : ultima[b]!.compareTo(ultima[a]!);
        });
      return [for (final k in orden) (pistas[k]!, veces[k]!)];
    }

    var lista = contar((e) => !e.fecha.isBefore(inicio) && e.fecha.isBefore(fin));
    var ultimos30 = false;
    if (lista.length < minimo) {
      final desde = hoy.subtract(const Duration(days: 30));
      lista = contar((e) => !e.fecha.isBefore(desde) && !e.fecha.isAfter(hoy));
      ultimos30 = true;
    }
    if (lista.length < minimo) return null;
    final pistas = [for (final (p, _) in lista.take(largo)) p];
    final nombre = ultimos30
        ? 'Lo más escuchado en los últimos 30 días'
        : 'Lo más escuchado en ${nombreDelMes(inicio.month)}';
    return {
      'tipo': 'mix',
      'id': ultimos30 ? 'mes_pasado_30d' : 'mes_pasado_${inicio.year}_${inicio.month}',
      'titulo': 'Tu mes pasado',
      'subtitulo': ultimos30
          ? 'Lo que más escuchaste en los últimos 30 días'
          : 'Lo que más escuchaste en ${nombreDelMes(inicio.month)}',
      'nombre_lista': nombre,
      'ultimos_30_dias': ultimos30,
      'miniatura': '${pistas.first['miniatura'] ?? ''}',
      'miniaturas': {
        for (final p in pistas) if ('${p['miniatura'] ?? ''}'.isNotEmpty) '${p['miniatura']}'
      }.take(4).toList(),
      'color': 0xFFE8795A,
      'pistas': [for (final p in pistas) Coleccion.paraNube(p)],
      'total': pistas.length,
    };
  }

  static Future<Json?> mesPasadoDe(Coleccion c, {DateTime? ahora}) async {
    final hoy = ahora ?? DateTime.now();
    final historial = await Historial.leer(c, desde: desdeMesPasado(ahora: hoy), limite: 20000);
    return mesPasado(historial, ahora: hoy);
  }

  /// Guarda «Tu mes pasado» como una lista real (con su portada de mosaico, que
  /// sale de las primeras canciones). Si ya existe una con ese nombre, no se
  /// duplica: se le añaden las canciones que falten y se devuelve su id.
  static Future<int> guardarMesPasado(Coleccion c, Json mix) async {
    final nombre = '${mix['nombre_lista'] ?? mix['titulo'] ?? 'Tu mes pasado'}';
    final pistas = [
      for (final e in (mix['pistas'] is List ? mix['pistas'] as List : const []))
        if (e is Map) Map<String, dynamic>.from(e)
    ];
    final existente = (await c.listas()).where((l) => '${l['nombre']}' == nombre).firstOrNull;
    final id = existente == null
        ? await c.crearLista(nombre, descripcion: '${mix['subtitulo'] ?? ''}')
        : (existente['id'] is int ? existente['id'] as int : int.parse('${existente['id']}'));
    await c.agregarALista(id, pistas);
    return id;
  }
}

/// Rasgos baratos de una pista que se deducen de los datos que ya hay (título,
/// artista y año): la escritura (latina, coreana, japonesa...), el idioma
/// (español sí/no) y la década. Sirven para que una cumbia no traiga k-pop.
class Rasgos {
  Rasgos._();

  static const _palabrasEs = {
    'el', 'la', 'los', 'las', 'de', 'del', 'que', 'y', 'mi', 'tu', 'te', 'me', 'un', 'una', 'por', 'con',
    'amor', 'corazon', 'corazón', 'vida', 'noche', 'baila', 'bailando', 'quiero', 'eres', 'sin', 'para',
    'no', 'si', 'sí', 'ya', 'yo', 'tú', 'cariño', 'besos', 'fiesta', 'loca', 'loco',
  };

  static String escritura(String t) {
    var latin = 0, cjk = 0, hangul = 0, kana = 0, cirilico = 0, arabe = 0;
    for (final r in t.runes) {
      if ((r >= 0xAC00 && r <= 0xD7AF) || (r >= 0x1100 && r <= 0x11FF)) {
        hangul++;
      } else if (r >= 0x3040 && r <= 0x30FF) {
        kana++;
      } else if (r >= 0x4E00 && r <= 0x9FFF) {
        cjk++;
      } else if (r >= 0x0400 && r <= 0x04FF) {
        cirilico++;
      } else if (r >= 0x0600 && r <= 0x06FF) {
        arabe++;
      } else if ((r >= 0x41 && r <= 0x5A) || (r >= 0x61 && r <= 0x7A) || (r >= 0xC0 && r <= 0x24F)) {
        latin++;
      }
    }
    final m = {'latina': latin, 'coreana': hangul, 'japonesa': kana, 'china': cjk, 'cirilica': cirilico, 'arabe': arabe};
    final mejor = m.entries.reduce((a, b) => b.value > a.value ? b : a);
    return mejor.value == 0 ? '' : mejor.key;
  }

  /// Los rasgos como etiquetas: `esc:latina`, `idioma:es`, `dec:2010`.
  static List<String> de(Json p) {
    final texto = '${p['titulo'] ?? ''} ${p['artista'] ?? ''}';
    final salida = <String>[];
    // manda el titulo; el artista solo si el titulo no dice nada
    final esc = escritura('${p['titulo'] ?? ''}').isNotEmpty ? escritura('${p['titulo'] ?? ''}') : escritura(texto);
    if (esc.isNotEmpty) salida.add('esc:$esc');
    if (esc == 'latina') {
      final minus = texto.toLowerCase();
      final palabras = minus.split(RegExp(r'[^a-záéíóúñü]+')).where((x) => x.isNotEmpty);
      final n = palabras.where(_palabrasEs.contains).length;
      if (n >= 2 || (n >= 1 && RegExp('[ñ¿¡áéíóú]').hasMatch(minus)) || minus.contains('ñ')) {
        salida.add('idioma:es');
      }
    }
    final crudo = p['anio'] ?? (p['album'] is Map ? (p['album'] as Map)['anio'] : null);
    final anio = int.tryParse('${crudo ?? ''}'.trim());
    if (anio != null && anio > 1900 && anio < 2100) salida.add('dec:${anio ~/ 10 * 10}');
    final animo = animoDe(texto);
    if (animo.isNotEmpty) salida.add('animo:$animo');
    return salida;
  }

  // Palabras que delatan el ánimo de una canción en su título (español e inglés).
  static final RegExp _triste = RegExp(
      r'(?<![a-záéíóúñü])(triste|tristeza|llor\w*|lágrimas|lagrimas|dolor|duele\w*|soledad|adiós|adios|olvid\w*|'
      r'extraño|extrano|perdón|perdon|ausencia|herid\w*|roto|rota|desamor|despedida|muerte|nostalgia|'
      r'sad|cry\w*|tears?|lonely|alone|heartbreak\w*|broken|goodbye|hurt\w*|miss(ing)? you|without you|'
      r'sin ti|pain|sorry|farewell|depress\w*|grief|memories)(?![a-záéíóúñü])',
      caseSensitive: false);
  static final RegExp _fiesta = RegExp(
      r'(?<![a-záéíóúñü])(fiesta|baila\w*|bailar|perreo|party|dance|dancing|goza\w*|rumba|prende|booty|twerk|'
      r'sandungueo|energy|energía|summer|verano|bounce|turn up|pop off)(?![a-záéíóúñü])',
      caseSensitive: false);
  static final RegExp _romantica = RegExp(
      r'(?<![a-záéíóúñü])(amor|love|te quiero|te amo|besos?|beso|corazón|corazon|heart|mi vida|cariño|'
      r'enamorad\w*|romance|romántic\w*|forever|eres mi|contigo)(?![a-záéíóúñü])',
      caseSensitive: false);

  /// `triste`, `fiesta`, `romantica` o '' si el título no lo dice.
  /// Manda la tristeza: «Sin ti» es triste aunque hable de amor.
  static String animoDe(String texto) {
    if (_triste.hasMatch(texto)) return 'triste';
    if (_fiesta.hasMatch(texto)) return 'fiesta';
    if (_romantica.hasMatch(texto)) return 'romantica';
    return '';
  }

  /// -1..1: cuánto se parecen dos pistas por sus rasgos. Sin datos: 0.
  static double similitud(List<String> a, List<String> b) {
    if (a.isEmpty || b.isEmpty) return 0;
    String? v(List<String> l, String pref) => l.where((x) => x.startsWith(pref)).firstOrNull;
    var s = 0.0;
    final ea = v(a, 'esc:'), eb = v(b, 'esc:');
    if (ea != null && eb != null) s += ea == eb ? 0.5 : -0.9;
    final ia = a.contains('idioma:es'), ib = b.contains('idioma:es');
    if (ea == 'esc:latina' && eb == 'esc:latina') s += ia == ib ? (ia ? 0.4 : 0.1) : -0.2;
    final da = int.tryParse((v(a, 'dec:') ?? '').replaceFirst('dec:', ''));
    final db = int.tryParse((v(b, 'dec:') ?? '').replaceFirst('dec:', ''));
    if (da != null && db != null) s += (da - db).abs() <= 10 ? 0.2 : -0.1;
    // mismo ánimo (triste con triste...) sube; ánimos opuestos (triste con fiesta) bajan
    final na = v(a, 'animo:'), nb = v(b, 'animo:');
    if (na != null && nb != null) {
      if (na == nb) {
        s += 0.5;
      } else {
        final par = {na, nb};
        s += par.containsAll({'animo:triste', 'animo:fiesta'})
            ? -0.6
            : par.containsAll({'animo:romantica', 'animo:triste'})
                ? 0.15
                : -0.25;
      }
    }
    return s.clamp(-1.0, 1.0);
  }
}
