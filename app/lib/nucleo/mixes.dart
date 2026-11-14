import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'catalogo.dart';
import 'coleccion.dart';

/// Tus mixes diarios y tu resumen de escuchas.
///
/// Todo sale de la tabla `reproducciones` de la coleccion (lo que de verdad
/// escuchaste, contado a los 30 s). La logica pesada es pura —recibe una lista
/// de [Escucha]— para poder probarla sin base ni red; las funciones que leen la
/// coleccion o llaman a YouTube Music son una capa fina por encima.

// ============================================================ historial

/// Una escucha: la pista, cuando sono y desde donde (el contexto, si lo hubo).
class Escucha {
  const Escucha(this.pista, this.fecha, {this.contexto});

  final Json pista;
  final DateTime fecha;
  final Json? contexto;

  String get clave => '${pista['clave'] ?? ''}';

  String get videoId => '${pista['video_id'] ?? ''}';

  /// Segundos que cuenta para el resumen. Si no se sabe la duracion se
  /// supone una cancion normal; los videos larguisimos (sesiones de una hora)
  /// se cortan a 15 min para no inflar los minutos.
  int get segundos {
    final d = pista['duracion'];
    final n = d is num ? d.toInt() : int.tryParse('${d ?? ''}') ?? 0;
    if (n <= 0) return 210;
    return min(n, 900);
  }

  /// Artistas de la pista con su clave estable (id si lo hay, si no el nombre).
  List<({String clave, String nombre})> get artistas => artistasDe(pista);
}

/// Artistas de una pista: `artistas` [{id, nombre}] o, si falta, el texto de
/// `artista` partido por comas.
List<({String clave, String nombre})> artistasDe(Json pista) {
  final salida = <({String clave, String nombre})>[];
  final vistos = <String>{};
  void poner(String id, String nombre) {
    nombre = nombre.trim();
    if (nombre.isEmpty) return;
    final clave = id.trim().isNotEmpty ? 'id:${id.trim()}' : 'n:${nombre.toLowerCase()}';
    if (vistos.add(clave)) salida.add((clave: clave, nombre: nombre));
  }

  final lista = pista['artistas'];
  if (lista is List) {
    for (final a in lista) {
      if (a is Map) poner('${a['id'] ?? ''}', '${a['nombre'] ?? ''}');
    }
  }
  if (salida.isEmpty) {
    for (final n in '${pista['artista'] ?? ''}'.split(RegExp(r',|&| feat\.? | ft\.? ', caseSensitive: false))) {
      poner('', n);
    }
  }
  return salida;
}

DateTime _dia(DateTime f) => DateTime(f.year, f.month, f.day);

String claveDia(DateTime f) =>
    '${f.year}-${f.month.toString().padLeft(2, '0')}-${f.day.toString().padLeft(2, '0')}';

/// Lee el historial de la coleccion como [Escucha] en orden cronologico.
class Historial {
  Historial._();

  static Future<List<Escucha>> leer(Coleccion c, {DateTime? desde, int limite = 40000}) async {
    final filas = await c.db.rawQuery(
        'SELECT clave, fecha, contexto FROM reproducciones WHERE fecha >= ? '
        'ORDER BY fecha DESC LIMIT ?',
        [desde == null ? 0 : desde.millisecondsSinceEpoch / 1000.0, limite]);
    if (filas.isEmpty) return [];
    final claves = <String>{for (final f in filas) '${f['clave']}'}.toList();
    final pistas = {for (final p in await c.pistas(claves)) '${p['clave']}': p};
    final salida = <Escucha>[];
    for (final f in filas.reversed) {
      final pista = pistas['${f['clave']}'];
      final segundos = f['fecha'];
      if (pista == null || segundos is! num) continue;
      Json? contexto;
      final texto = '${f['contexto'] ?? ''}';
      if (texto.isNotEmpty) {
        try {
          final d = jsonDecode(texto);
          if (d is Map) contexto = Map<String, dynamic>.from(d);
        } catch (_) {}
      }
      salida.add(Escucha(pista,
          DateTime.fromMillisecondsSinceEpoch((segundos * 1000).round()), contexto: contexto));
    }
    return salida;
  }
}

// ============================================================ mixes

/// Un grupo de artistas que sueles escuchar juntos: la semilla de un mix.
class GrupoMix {
  GrupoMix(this.artistas);

  /// Claves de artista, la de mas peso primero.
  final List<String> artistas;
  final Map<String, String> nombres = {};

  /// Tus pistas del grupo, la mas escuchada primero.
  final List<Json> pistas = [];

  /// Genero o estado de animo desde el que mas sonaron, si destaca.
  String? estilo;
  double peso = 0;
}

typedef BuscarRadio = Future<List<Json>> Function(String videoId);

class Mixes {
  Mixes._();

  static const _claveCache = 'mixes_del_dia';

  /// Colores de los mixes (como los de Spotify, uno por mix).
  static const colores = <int>[
    0xFF22D3EE, 0xFFFF5C8A, 0xFFFFB443, 0xFF7C5CFF, 0xFF2BD576, 0xFFFF7A45,
  ];

  /// Los mixes de hoy. Se arman una vez al dia y se guardan en la coleccion;
  /// si hoy no hubo internet para la radio, se vuelve a intentar la proxima vez.
  static Future<List<Json>> delDia(Coleccion c,
      {BuscarRadio? radio, DateTime? ahora, int maximo = 6}) async {
    final hoy = ahora ?? DateTime.now();
    final dia = claveDia(hoy);
    final guardado = await c.estado(_claveCache);
    List<Json>? anteriores;
    if (guardado is Map && guardado['dia'] == dia && guardado['mixes'] is List) {
      anteriores = [
        for (final m in guardado['mixes'] as List)
          if (m is Map) Map<String, dynamic>.from(m)
      ];
      if (guardado['completo'] == true && anteriores.isNotEmpty) return anteriores;
    }
    final historial =
        await Historial.leer(c, desde: hoy.subtract(const Duration(days: 90)), limite: 6000);
    final mixes = await construir(historial, radio: radio ?? _radioCatalogo, ahora: hoy, maximo: maximo);
    if (mixes.isEmpty) return anteriores ?? [];
    final completo = mixes.every((m) => m['con_radio'] == true);
    // un armado sin radio no pisa uno de hoy que si la tenia
    if (!completo && anteriores != null && anteriores.any((m) => m['con_radio'] == true)) {
      return anteriores;
    }
    await c.guardarEstado(_claveCache, {'dia': dia, 'completo': completo, 'mixes': mixes});
    return mixes;
  }

  /// Borra los mixes guardados (p. ej. al borrar el historial).
  static Future<void> olvidar(Coleccion c) => c.guardarEstado(_claveCache, null);

  static Future<List<Json>> _radioCatalogo(String videoId) async {
    final r = await Catalogo.radio(videoId: videoId, limite: 40);
    return [
      for (final e in (r['pistas'] is List ? r['pistas'] as List : const []))
        if (e is Map) Map<String, dynamic>.from(e)
    ];
  }

  /// Arma los mixes a partir del historial. [radio] trae la radio de una
  /// cancion; si falla, el mix sale solo con tus canciones.
  static Future<List<Json>> construir(List<Escucha> historial,
      {required BuscarRadio radio, DateTime? ahora, int maximo = 6, int largo = 50}) async {
    final hoy = ahora ?? DateTime.now();
    final grupos = agrupar(historial, ahora: hoy, maximo: maximo);
    if (grupos.isEmpty) return [];
    final dia = claveDia(hoy);

    final semillasPorGrupo = [for (final g in grupos) semillas(g)];
    final pedidas = <String, Future<List<Json>?>>{};
    for (final s in semillasPorGrupo.expand((x) => x)) {
      pedidas.putIfAbsent(s, () async {
        try {
          return await radio(s).timeout(const Duration(seconds: 20));
        } catch (_) {
          return null;
        }
      });
    }
    final claves = pedidas.keys.toList();
    final respuestas = await Future.wait(claves.map((k) => pedidas[k]!));
    final radios = {for (var i = 0; i < claves.length; i++) claves[i]: respuestas[i]};

    // Una cancion de radio va a un solo mix: que no se repitan entre ellos.
    final usadas = <String>{for (final g in grupos) for (final p in g.pistas) _id(p)};
    final salida = <Json>[];
    for (var i = 0; i < grupos.length; i++) {
      final g = grupos[i];
      final deRadio = <List<Json>>[];
      var conRadio = semillasPorGrupo[i].isEmpty;
      for (final s in semillasPorGrupo[i]) {
        final r = radios[s];
        if (r == null) continue;
        conRadio = true;
        deRadio.add([for (final p in r) if (!usadas.contains(_id(p))) p]);
      }
      final azar = Random(_hash('$dia|$i|${g.artistas.first}'));
      final pistas = mezclar(g.pistas, deRadio, largo: largo, azar: azar);
      usadas.addAll(pistas.map(_id));
      salida.add(_elemento(g, i, pistas, dia: dia, conRadio: conRadio));
    }
    return salida;
  }

  static Json _elemento(GrupoMix g, int i, List<Json> pistas,
      {required String dia, required bool conRadio}) {
    final nombres = [for (final a in g.artistas) g.nombres[a] ?? ''].where((n) => n.isNotEmpty).toList();
    // portada: una por artista distinto, luego lo que haya
    final miniaturas = <String>[];
    final artistasVistos = <String>{};
    for (final p in [...g.pistas, ...pistas]) {
      final m = '${p['miniatura'] ?? ''}';
      final a = artistasDe(p).firstOrNull?.clave ?? '';
      if (m.isEmpty || miniaturas.contains(m) || !artistasVistos.add(a)) continue;
      miniaturas.add(m);
      if (miniaturas.length == 4) break;
    }
    for (final p in pistas) {
      if (miniaturas.length >= 4) break;
      final m = '${p['miniatura'] ?? ''}';
      if (m.isNotEmpty && !miniaturas.contains(m)) miniaturas.add(m);
    }
    final segundos = pistas.fold<int>(0, (s, p) => s + Escucha(p, DateTime(0)).segundos);
    return {
      'tipo': 'mix',
      'id': 'mix_diario_${i + 1}',
      'titulo': nombreMix(i, g.estilo),
      'subtitulo': subtituloMix(nombres),
      'miniatura': miniaturas.isEmpty ? '' : miniaturas.first,
      'miniaturas': miniaturas,
      'artistas': nombres,
      'color': colores[i % colores.length],
      'estilo': g.estilo,
      'pistas': [for (final p in pistas) Coleccion.paraNube(p)],
      'total': pistas.length,
      'minutos': (segundos / 60).round(),
      'dia': dia,
      'con_radio': conRadio,
    };
  }

  static String nombreMix(int i, String? estilo) =>
      estilo == null || estilo.trim().isEmpty ? 'Mix diario ${i + 1}' : 'Mix de ${estilo.trim()}';

  /// "Bad Bunny, Feid, Karol G y más".
  static String subtituloMix(List<String> nombres) {
    if (nombres.isEmpty) return 'Lo que más escuchas y más';
    return '${nombres.take(3).join(', ')} y más';
  }

  /// Las canciones desde las que se pide la radio: tus dos mas escuchadas del
  /// grupo, de artistas distintos si se puede.
  static List<String> semillas(GrupoMix g, [int n = 2]) {
    final salida = <String>[];
    final artistas = <String>{};
    for (final pasada in [true, false]) {
      for (final p in g.pistas) {
        final vid = _id(p);
        if (vid.length != 11 || salida.contains(vid)) continue;
        final a = artistasDe(p).firstOrNull?.clave ?? '';
        if (pasada && !artistas.add(a)) continue;
        salida.add(vid);
        if (salida.length == n) return salida;
      }
    }
    return salida;
  }

  /// Agrupa tus artistas en hasta [maximo] mixes. Dos artistas van juntos si
  /// sueles escucharlos en la misma sesion (o cantan juntos): asi un mix
  /// queda "de un estilo" sin necesitar saber el genero de cada cancion.
  static List<GrupoMix> agrupar(List<Escucha> historial, {DateTime? ahora, int maximo = 6}) {
    if (historial.isEmpty || maximo <= 0) return [];
    final hoy = ahora ?? DateTime.now();
    final orden = [...historial]..sort((a, b) => a.fecha.compareTo(b.fecha));

    final peso = <String, double>{};
    final nombres = <String, String>{};
    final sesiones = <String, int>{};
    final juntos = <String, Map<String, double>>{};
    final pesoPista = <String, double>{};
    final pistas = <String, Json>{};

    void sumarJuntos(String a, String b, double v) {
      if (a == b) return;
      juntos.putIfAbsent(a, () => {})[b] = (juntos[a]![b] ?? 0) + v;
      juntos.putIfAbsent(b, () => {})[a] = (juntos[b]![a] ?? 0) + v;
    }

    var sesion = <String>{};
    DateTime? ultima;
    void cerrarSesion() {
      final l = sesion.toList();
      for (final a in l) {
        sesiones[a] = (sesiones[a] ?? 0) + 1;
      }
      for (var i = 0; i < l.length; i++) {
        for (var j = i + 1; j < l.length; j++) {
          sumarJuntos(l[i], l[j], 1);
        }
      }
      sesion = {};
    }

    for (final e in orden) {
      final artistas = e.artistas;
      if (artistas.isEmpty || e.clave.isEmpty) continue;
      if (ultima != null && e.fecha.difference(ultima).inMinutes > 45) cerrarSesion();
      ultima = e.fecha;
      // lo reciente pesa mas: tu gusto de hoy manda sobre el de hace meses
      final edad = hoy.difference(e.fecha).inHours / 24.0;
      final w = pow(0.5, max(0.0, edad) / 30).toDouble();
      for (final (i, a) in artistas.indexed) {
        peso[a.clave] = (peso[a.clave] ?? 0) + (i == 0 ? w : w * 0.5);
        nombres.putIfAbsent(a.clave, () => a.nombre);
        if (i == 0) sesion.add(a.clave);
      }
      for (var i = 0; i < artistas.length; i++) {
        for (var j = i + 1; j < artistas.length; j++) {
          sumarJuntos(artistas[i].clave, artistas[j].clave, 2);
        }
      }
      pesoPista[e.clave] = (pesoPista[e.clave] ?? 0) + w;
      pistas[e.clave] = e.pista;
    }
    cerrarSesion();
    if (peso.isEmpty) return [];

    final candidatos = peso.keys.toList()..sort((a, b) => peso[b]!.compareTo(peso[a]!));
    final principales = candidatos.take(40).toList();
    final grupos = <GrupoMix>[];
    const maxPorGrupo = 6;

    double afinidad(String a, GrupoMix g) {
      final ja = juntos[a] ?? const {};
      var co = 0.0;
      var ses = 0;
      for (final b in g.artistas) {
        co += ja[b] ?? 0;
        ses += sesiones[b] ?? 1;
      }
      return co / sqrt(max(1, sesiones[a] ?? 1) * max(1, ses));
    }

    for (final a in principales) {
      GrupoMix? mejor;
      var mejorAf = 0.0;
      for (final g in grupos) {
        if (g.artistas.length >= maxPorGrupo) continue;
        final af = afinidad(a, g);
        if (af > mejorAf) {
          mejorAf = af;
          mejor = g;
        }
      }
      if (mejor != null && (mejorAf >= 0.35 || grupos.length >= maximo)) {
        mejor.artistas.add(a);
      } else if (grupos.length < maximo) {
        grupos.add(GrupoMix([a]));
      }
    }

    // Con poco historial todo cae en uno o dos grupos: se separan para que
    // haya al menos tres mixes si hay artistas para ello.
    final minimo = min(3, maximo);
    while (grupos.length < minimo) {
      final grande = grupos.where((g) => g.artistas.length > 1).fold<GrupoMix?>(
          null, (m, g) => m == null || g.artistas.length > m.artistas.length ? g : m);
      if (grande == null) break;
      grupos.add(GrupoMix([grande.artistas.removeAt(1)]));
    }

    // Cada pista va al grupo de su primer artista que tenga grupo.
    final grupoDe = <String, GrupoMix>{};
    for (final g in grupos) {
      for (final a in g.artistas) {
        grupoDe[a] = g;
        g.nombres[a] = nombres[a] ?? '';
        g.peso += peso[a] ?? 0;
      }
    }
    final pistasOrden = pesoPista.keys.toList()..sort((a, b) => pesoPista[b]!.compareTo(pesoPista[a]!));
    for (final clave in pistasOrden) {
      final p = pistas[clave]!;
      for (final a in artistasDe(p)) {
        final g = grupoDe[a.clave];
        if (g != null) {
          g.pistas.add(p);
          break;
        }
      }
    }

    // Estilo: el genero o animo desde el que sono la mayor parte del grupo.
    final porEstilo = <GrupoMix, Map<String, int>>{};
    final totales = <GrupoMix, int>{};
    for (final e in orden) {
      final a = e.artistas.firstOrNull;
      final g = a == null ? null : grupoDe[a.clave];
      if (g == null) continue;
      totales[g] = (totales[g] ?? 0) + 1;
      final ctx = e.contexto;
      final titulo = '${ctx?['titulo'] ?? ''}'.trim();
      if (ctx != null && ctx['tipo'] == 'genero' && titulo.isNotEmpty) {
        final m = porEstilo.putIfAbsent(g, () => {});
        m[titulo] = (m[titulo] ?? 0) + 1;
      }
    }
    final estilosUsados = <String>{};
    for (final g in grupos) {
      final m = porEstilo[g];
      if (m == null || m.isEmpty) continue;
      final top = m.entries.reduce((x, y) => y.value > x.value ? y : x);
      if (top.value >= 3 && top.value / (totales[g] ?? 1) >= 0.4 && estilosUsados.add(top.key)) {
        g.estilo = top.key;
      }
    }

    final salida = grupos.where((g) => g.pistas.isNotEmpty).toList()
      ..sort((a, b) => b.peso.compareTo(a.peso));
    return salida;
  }

  /// Junta tus canciones con las de la radio: una tuya, dos nuevas, y asi.
  /// Tus favoritas van mas al principio, pero sin repetir siempre el orden.
  static List<Json> mezclar(List<Json> propias, List<List<Json>> radios,
      {int largo = 50, Random? azar}) {
    final r = azar ?? Random();
    final vistas = <String>{};
    bool nueva(Json p) {
      final id = _id(p);
      return id.isNotEmpty && vistas.add(id);
    }

    final tuyas = <Json>[for (final p in propias.take(25)) if (nueva(p)) p];
    // las 8 mas escuchadas, barajadas entre si, delante del resto barajado
    final cabeza = tuyas.take(8).toList()..shuffle(r);
    final cola = tuyas.skip(8).toList()..shuffle(r);
    final mias = [...cabeza, ...cola];

    final otras = <Json>[];
    final colas = [for (final l in radios) [...l]];
    var quedan = true;
    while (quedan) {
      quedan = false;
      for (final l in colas) {
        while (l.isNotEmpty) {
          final p = l.removeAt(0);
          if (nueva(p)) {
            otras.add(p);
            quedan = true;
            break;
          }
        }
        if (l.isNotEmpty) quedan = true;
      }
    }

    final salida = <Json>[];
    var i = 0, j = 0;
    while (salida.length < largo && (i < mias.length || j < otras.length)) {
      final tocaMia = salida.length % 3 == 0;
      if ((tocaMia && i < mias.length) || j >= otras.length) {
        salida.add(mias[i++]);
      } else {
        salida.add(otras[j++]);
      }
    }
    return salida;
  }

  static String _id(Json p) {
    final v = '${p['video_id'] ?? ''}';
    return v.isNotEmpty ? v : '${p['clave'] ?? ''}';
  }

  static int _hash(String s) {
    var h = 0x811c9dc5;
    for (final c in s.codeUnits) {
      h = ((h ^ c) * 0x01000193) & 0x7fffffff;
    }
    return h;
  }
}

// ============================================================ resumen

enum PeriodoResumen {
  semana(7, 'Semana', 'tu semana', 'los últimos 7 días'),
  mes(30, 'Mes', 'tu mes', 'los últimos 30 días'),
  anio(365, 'Año', 'tu año', 'los últimos 12 meses');

  const PeriodoResumen(this.dias, this.etiqueta, this.nombre, this.rango);
  final int dias;
  final String etiqueta;
  final String nombre;
  final String rango;
}

class PuestoCancion {
  PuestoCancion(this.pista);
  final Json pista;
  int veces = 0;
  int segundos = 0;
  int get minutos => (segundos / 60).round();
}

class PuestoArtista {
  PuestoArtista(this.clave, this.nombre);
  final String clave;
  final String nombre;
  String miniatura = '';
  int veces = 0;
  int segundos = 0;
  int get minutos => (segundos / 60).round();

  /// Id de YouTube Music para abrir su pagina ('' si solo se sabe el nombre).
  String get id => clave.startsWith('id:') ? clave.substring(3) : '';
}

const _meses = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
  'octubre', 'noviembre', 'diciembre'
];

class Resumen {
  Resumen._(this.periodo, this.desde, this.hasta);

  final PeriodoResumen periodo;
  final DateTime desde;
  final DateTime hasta;

  int segundos = 0;
  int escuchas = 0;
  int get minutos => (segundos / 60).round();
  List<PuestoCancion> topCanciones = [];
  List<PuestoArtista> topArtistas = [];
  int cancionesDistintas = 0;
  int artistasDistintos = 0;

  /// Minutos por hora del dia (0..23).
  List<int> porHora = List.filled(24, 0);
  int horaPico = 0;

  /// Minutos por dia del periodo, del mas antiguo a hoy.
  List<int> porDia = [];
  int diasConMusica = 0;

  int rachaMasLarga = 0;
  int rachaActual = 0;

  /// La mas escuchada del mes en curso (la del calendario, no del periodo).
  PuestoCancion? cancionDelMes;
  String nombreMes = '';

  /// Minutos del periodo anterior de igual largo, para comparar.
  int minutosAntes = 0;

  /// Artistas que sonaron por primera vez en el periodo.
  List<PuestoArtista> descubrimientos = [];

  bool get vacio => escuchas == 0;

  /// Cambio frente al periodo anterior en %, o null si antes no hubo nada.
  int? get cambio => minutosAntes == 0 ? null : ((minutos - minutosAntes) * 100 / minutosAntes).round();

  /// Momento del dia en que mas escuchas.
  String get franja => switch (horaPico) {
        < 6 => 'madrugada',
        < 12 => 'mañana',
        < 19 => 'tarde',
        _ => 'noche',
      };

  static Future<Resumen> deColeccion(Coleccion c, PeriodoResumen periodo, {DateTime? ahora}) async {
    // todo el historial: hace falta para las rachas, el mes y los descubrimientos
    final historial = await Historial.leer(c);
    return calcular(historial, periodo, ahora: ahora);
  }

  static Resumen calcular(List<Escucha> historial, PeriodoResumen periodo, {DateTime? ahora}) {
    final hoy = ahora ?? DateTime.now();
    final inicioHoy = _dia(hoy);
    final desde = DateTime(inicioHoy.year, inicioHoy.month, inicioHoy.day - (periodo.dias - 1));
    final antesDesde = DateTime(desde.year, desde.month, desde.day - periodo.dias);
    final inicioMes = DateTime(hoy.year, hoy.month);
    final r = Resumen._(periodo, desde, hoy)
      ..nombreMes = _meses[hoy.month - 1]
      ..porDia = List.filled(periodo.dias, 0);

    final canciones = <String, PuestoCancion>{};
    final artistas = <String, PuestoArtista>{};
    final delMes = <String, PuestoCancion>{};
    final artistasAntes = <String>{};
    final dias = <String>{};

    for (final e in historial) {
      if (e.fecha.isAfter(hoy) || e.clave.isEmpty) continue;
      dias.add(claveDia(e.fecha));
      final seg = e.segundos;
      if (e.fecha.isBefore(desde)) {
        for (final a in e.artistas) {
          artistasAntes.add(a.clave);
        }
        if (!e.fecha.isBefore(antesDesde)) r.minutosAntes += seg;
      }
      if (!e.fecha.isBefore(inicioMes)) {
        final m = delMes.putIfAbsent(e.clave, () => PuestoCancion(e.pista));
        m.veces++;
        m.segundos += seg;
      }
      if (e.fecha.isBefore(desde)) continue;

      r.escuchas++;
      r.segundos += seg;
      final c = canciones.putIfAbsent(e.clave, () => PuestoCancion(e.pista));
      c.veces++;
      c.segundos += seg;
      for (final (i, a) in e.artistas.indexed) {
        final p = artistas.putIfAbsent(a.clave, () => PuestoArtista(a.clave, a.nombre));
        if (p.miniatura.isEmpty) p.miniatura = '${e.pista['miniatura'] ?? ''}';
        p.veces++;
        // los minutos cuentan para el artista principal; los invitados suman la escucha
        if (i == 0) p.segundos += seg;
      }
      r.porHora[e.fecha.hour] += seg;
      // en minutos y redondeado: los dias de cambio de horario duran 23 o 25 h
      final d = (_dia(e.fecha).difference(desde).inMinutes / 1440).round();
      if (d >= 0 && d < periodo.dias) r.porDia[d] += seg;
    }
    r.minutosAntes = (r.minutosAntes / 60).round();
    r.porHora = [for (final s in r.porHora) (s / 60).round()];
    r.porDia = [for (final s in r.porDia) (s / 60).round()];
    r.diasConMusica = r.porDia.where((m) => m > 0).length;

    int orden(PuestoCancion a, PuestoCancion b) => b.veces != a.veces ? b.veces.compareTo(a.veces) : b.segundos.compareTo(a.segundos);
    r.topCanciones = (canciones.values.toList()..sort(orden)).take(5).toList();
    final arts = artistas.values.toList()
      ..sort((a, b) => b.segundos != a.segundos ? b.segundos.compareTo(a.segundos) : b.veces.compareTo(a.veces));
    r.topArtistas = arts.take(5).toList();
    r.cancionesDistintas = canciones.length;
    r.artistasDistintos = artistas.length;
    r.descubrimientos =
        arts.where((a) => !artistasAntes.contains(a.clave)).take(3).toList();
    if (artistasAntes.isEmpty) r.descubrimientos = []; // sin historial previo todo seria "nuevo"

    var pico = 0;
    for (var h = 1; h < 24; h++) {
      if (r.porHora[h] > r.porHora[pico]) pico = h;
    }
    r.horaPico = pico;

    final mes = delMes.values.toList()..sort(orden);
    r.cancionDelMes = mes.isEmpty ? null : mes.first;

    // racha mas larga dentro del periodo
    var actual = 0;
    for (final m in r.porDia) {
      actual = m > 0 ? actual + 1 : 0;
      r.rachaMasLarga = max(r.rachaMasLarga, actual);
    }
    // racha de hoy: dias seguidos hasta hoy (o hasta ayer, si hoy aun no)
    var dia = inicioHoy;
    if (!dias.contains(claveDia(dia))) dia = DateTime(dia.year, dia.month, dia.day - 1);
    while (dias.contains(claveDia(dia))) {
      r.rachaActual++;
      dia = DateTime(dia.year, dia.month, dia.day - 1);
    }
    return r;
  }
}
