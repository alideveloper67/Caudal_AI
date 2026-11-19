import 'dart:async';
import 'dart:math';

import 'catalogo.dart';
import 'coleccion.dart';
import 'mixes.dart' show artistasDe;

/// «Enriquecer» una lista: a partir de sus canciones sugiere otras nuevas,
/// parecidas y de los mismos artistas.
///
/// La logica de elegir semillas, juntar, quitar repetidas y ordenar es pura
/// (recibe y devuelve [Json]) para probarla sin red ni base; las funciones que
/// llaman a YouTube Music van inyectadas en [Enriquecer.sugerir], con limite
/// de peticiones a la vez y de espera para no cargar equipos modestos.

/// Una cancion sugerida y por que sale.
class Sugerencia {
  const Sugerencia(this.pista, {required this.fuentes, required this.propio, required this.puntaje});

  final Json pista;

  /// En cuantas de las peticiones (radios y artistas) aparecio.
  final int fuentes;

  /// Es de un artista que ya esta en la lista.
  final bool propio;
  final double puntaje;

  String get videoId => '${pista['video_id'] ?? ''}';
}

/// Lo que se pide a YouTube Music.
class Semillas {
  const Semillas(this.videoIds, this.artistas, this.pesos);

  /// Canciones de la lista cuya radio se pide.
  final List<String> videoIds;

  /// Artistas mas frecuentes, de los que se piden otras canciones.
  final List<({String clave, String nombre})> artistas;

  /// Cuanto pesa cada artista de la lista (0..1, el mas frecuente = 1).
  final Map<String, double> pesos;
}

/// Fallo de red que impide sugerir nada (se puede reintentar).
class EnriquecerError implements Exception {
  const EnriquecerError(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

typedef RadioDeCancion = Future<List<Json>> Function(String videoId);
typedef CancionesDeArtista = Future<List<Json>> Function(String nombre, String clave);

class Enriquecer {
  Enriquecer._();

  static const maxCancionesSemilla = 5;
  static const maxArtistasSemilla = 3;
  static const topeFinal = 40;
  static const concurrencia = 3;
  static const maxPorArtista = 4;
  static const duracionMaxima = 900; // lo mas largo son sesiones, no canciones

  // ------------------------------------------------------------ catalogo real

  static Future<List<Json>> radioCatalogo(String videoId) async {
    final r = await Catalogo.radio(videoId: videoId, limite: 25);
    return [
      for (final e in (r['pistas'] is List ? r['pistas'] as List : const []))
        if (e is Map) Map<String, dynamic>.from(e)
    ];
  }

  /// Otras canciones del artista (busqueda de canciones, solo las suyas).
  static Future<List<Json>> delArtistaCatalogo(String nombre, String clave) async {
    final r = await Catalogo.buscar(nombre, filtro: 'canciones', limite: 15);
    final bajo = nombre.toLowerCase();
    return [
      for (final e in r)
        if (e['tipo'] == 'pista' &&
            artistasDe(e).any((x) => x.clave == clave || x.nombre.toLowerCase() == bajo))
          e
    ];
  }

  // ------------------------------------------------------------ semillas

  /// Los artistas y canciones mas representativos de la lista. Sin azar: la
  /// misma lista da siempre las mismas semillas.
  static Semillas semillas(List<Json> lista,
      {int canciones = maxCancionesSemilla, int artistas = maxArtistasSemilla}) {
    final cuenta = <String, int>{};
    final nombres = <String, String>{};
    final porArtista = <String, List<Json>>{};
    for (final p in lista) {
      for (final a in artistasDe(p)) {
        cuenta[a.clave] = (cuenta[a.clave] ?? 0) + 1;
        nombres.putIfAbsent(a.clave, () => a.nombre);
        (porArtista[a.clave] ??= []).add(p);
      }
    }
    final orden = cuenta.keys.toList()
      ..sort((x, y) {
        final c = cuenta[y]!.compareTo(cuenta[x]!);
        return c != 0 ? c : nombres[x]!.toLowerCase().compareTo(nombres[y]!.toLowerCase());
      });
    final mayor = orden.isEmpty ? 1 : cuenta[orden.first]!;
    final pesos = {for (final k in orden) k: cuenta[k]! / mayor};
    final top = [for (final k in orden.take(artistas)) (clave: k, nombre: nombres[k]!)];

    // una cancion por artista de arriba, dando vueltas, y luego el resto repartido
    final ids = <String>[];
    String id(Json p) => '${p['video_id'] ?? ''}';
    void poner(Json p) {
      final v = id(p);
      if (v.isNotEmpty && !ids.contains(v) && ids.length < canciones) ids.add(v);
    }

    for (var ronda = 0; ids.length < canciones; ronda++) {
      var algo = false;
      for (final a in top) {
        final l = porArtista[a.clave]!;
        if (ronda < l.length) {
          algo = true;
          poner(l[ronda]);
        }
      }
      if (!algo) break;
    }
    if (ids.length < canciones && lista.isNotEmpty) {
      final paso = max(1, lista.length ~/ canciones);
      for (var i = 0; i < lista.length && ids.length < canciones; i += paso) {
        poner(lista[i]);
      }
      for (var i = 0; i < lista.length && ids.length < canciones; i++) {
        poner(lista[i]);
      }
    }
    return Semillas(ids, top, pesos);
  }

  // ------------------------------------------------------------ ordenar

  static String _id(Json p) => '${p['video_id'] ?? ''}';

  static String _titulo(String s) => s
      .toLowerCase()
      .replaceAll(RegExp(r'\(.*?\)|\[.*?\]'), '')
      .replaceAll(RegExp(r'[^a-z0-9áéíóúñü ]'), '')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();

  /// Misma cancion aunque venga con otro id (version, video...).
  static String _huella(Json p) {
    final a = artistasDe(p).firstOrNull?.nombre.toLowerCase() ?? '';
    return '${_titulo('${p['titulo'] ?? ''}')}|$a';
  }

  /// Junta lo que trajo cada peticion, quita repetidas y lo que ya esta en
  /// [lista], y ordena por afinidad: primero las que salen en varias
  /// peticiones; despues se alternan las de artistas de la lista y las
  /// parecidas. Ningun artista pasa de [maxPorArtista] salvo que falte relleno.
  static List<Sugerencia> ordenar(List<Json> lista, List<List<Json>> fuentes, Semillas semillas,
      {int limite = topeFinal}) {
    final yaIds = <String>{};
    final yaHuellas = <String>{};
    for (final p in lista) {
      if (_id(p).isNotEmpty) yaIds.add(_id(p));
      final c = '${p['clave'] ?? ''}';
      if (c.startsWith('yt:')) yaIds.add(c.substring(3));
      yaHuellas.add(_huella(p));
    }

    final candidatas = <String, _Candidata>{};
    final huellas = <String, String>{}; // huella -> id con el que se guardo
    for (var f = 0; f < fuentes.length; f++) {
      final vistasAqui = <String>{};
      for (var i = 0; i < fuentes[f].length; i++) {
        final p = fuentes[f][i];
        final v = _id(p);
        if (v.isEmpty || yaIds.contains(v) || p['es_video'] == true) continue;
        final d = p['duracion'];
        final dur = d is num ? d.toInt() : 0;
        if (dur > duracionMaxima) continue;
        final h = _huella(p);
        if (yaHuellas.contains(h)) continue;
        final dueno = huellas.putIfAbsent(h, () => v);
        final c = candidatas.putIfAbsent(dueno, () => _Candidata(p));
        if (!vistasAqui.add(dueno)) continue;
        c.fuentes++;
        c.mejor = min(c.mejor, i);
      }
    }

    final salida = <Sugerencia>[];
    for (final c in candidatas.values) {
      var peso = 0.0;
      for (final a in artistasDe(c.pista)) {
        peso = max(peso, semillas.pesos[a.clave] ?? 0);
      }
      final puntaje = (c.fuentes - 1) * 10 + peso * 3 + 2 / (1 + c.mejor);
      salida.add(Sugerencia(c.pista, fuentes: c.fuentes, propio: peso > 0, puntaje: puntaje));
    }
    int porPuntaje(Sugerencia a, Sugerencia b) {
      final c = b.puntaje.compareTo(a.puntaje);
      return c != 0 ? c : a.videoId.compareTo(b.videoId);
    }

    final repetidas = salida.where((s) => s.fuentes >= 2).toList()..sort(porPuntaje);
    final propias = salida.where((s) => s.fuentes < 2 && s.propio).toList()..sort(porPuntaje);
    final otras = salida.where((s) => s.fuentes < 2 && !s.propio).toList()..sort(porPuntaje);
    // alternadas: una parecida, una de artista de la lista, y asi
    final mezcla = <Sugerencia>[];
    var i = 0, j = 0;
    while (i < otras.length || j < propias.length) {
      if (i < otras.length) mezcla.add(otras[i++]);
      if (j < propias.length) mezcla.add(propias[j++]);
    }
    final ordenadas = [...repetidas, ...mezcla];

    final elegidas = <Sugerencia>[];
    final sobrantes = <Sugerencia>[];
    final porArtista = <String, int>{};
    for (final s in ordenadas) {
      if (elegidas.length >= limite) break;
      final k = artistasDe(s.pista).firstOrNull?.clave ?? '';
      final n = porArtista[k] ?? 0;
      if (k.isNotEmpty && n >= maxPorArtista) {
        sobrantes.add(s);
        continue;
      }
      porArtista[k] = n + 1;
      elegidas.add(s);
    }
    for (final s in sobrantes) {
      if (elegidas.length >= limite) break;
      elegidas.add(s);
    }
    return elegidas;
  }

  // ------------------------------------------------------------ peticiones

  /// Corre [tareas] con a lo sumo [limite] a la vez. Una tarea que falla no
  /// debe tirar a las demas: que cada una atrape lo suyo.
  static Future<void> correrConLimite(List<Future<void> Function()> tareas, int limite,
      {bool Function()? parar}) async {
    var siguiente = 0;
    Future<void> obrero() async {
      while (siguiente < tareas.length && parar?.call() != true) {
        await tareas[siguiente++]();
      }
    }

    await Future.wait([for (var k = 0; k < min(max(1, limite), tareas.length); k++) obrero()]);
  }

  /// Pide a YouTube Music (con [radio] y [delArtista]) y devuelve las
  /// sugerencias ordenadas. [progreso] avisa (hechas, total). Si todas las
  /// peticiones fallan lanza [EnriquecerError]; si solo fallan algunas, sigue con
  /// lo que llego. Si [cancelado] se enciende, deja de pedir y devuelve [].
  static Future<List<Sugerencia>> sugerir(List<Json> lista,
      {RadioDeCancion radio = radioCatalogo,
      CancionesDeArtista delArtista = delArtistaCatalogo,
      int limite = topeFinal,
      int paralelas = concurrencia,
      Duration espera = const Duration(seconds: 20),
      void Function(int hechas, int total)? progreso,
      bool Function()? cancelado}) async {
    final s = semillas(lista);
    final total = s.videoIds.length + s.artistas.length;
    if (total == 0) return [];
    final resultados = List<List<Json>?>.filled(total, null);
    var hechas = 0;
    var fallos = 0;
    progreso?.call(0, total);

    Future<void> Function() tarea(int n, Future<List<Json>> Function() pedir) => () async {
          try {
            resultados[n] = await pedir().timeout(espera);
          } catch (_) {
            fallos++;
          }
          hechas++;
          progreso?.call(hechas, total);
        };

    final tareas = <Future<void> Function()>[
      for (var i = 0; i < s.videoIds.length; i++) tarea(i, () => radio(s.videoIds[i])),
      for (var i = 0; i < s.artistas.length; i++)
        tarea(s.videoIds.length + i, () => delArtista(s.artistas[i].nombre, s.artistas[i].clave)),
    ];
    await correrConLimite(tareas, paralelas, parar: cancelado);
    if (cancelado?.call() == true) return [];
    if (fallos == total) {
      throw const EnriquecerError(
          'No se pudieron buscar canciones. Revisa tu conexión y vuelve a intentarlo.');
    }
    return ordenar(lista, [for (final r in resultados) if (r != null) r], s, limite: limite);
  }
}

class _Candidata {
  _Candidata(this.pista);
  final Json pista;
  int fuentes = 0;
  int mejor = 1 << 30;
}
