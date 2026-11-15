import 'dart:convert';
import 'dart:math';

import 'coleccion.dart';
import 'ritmo.dart';

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

/// Como se pasa de una cancion a la siguiente.
enum TipoTransicion {
  fundido('Fundido', 'Una baja mientras la otra sube.'),
  corte('Corte en el compás', 'La siguiente entra de golpe al empezar un compás.'),
  filtro('Filtro', 'La que se va pierde los graves y la que llega abre desde los graves, como un barrido.'),
  eco('Eco de salida', 'La que se va se apaga con un eco.'),
  graves('Cambio de graves', 'Los graves pasan de una canción a la otra.');

  const TipoTransicion(this.nombre, this.ayuda);
  final String nombre;
  final String ayuda;

  static TipoTransicion deNombre(Object? n) =>
      TipoTransicion.values.where((t) => t.name == n).firstOrNull ?? TipoTransicion.fundido;
}

/// La forma en que sube y baja el volumen durante el cambio.
enum CurvaFader {
  suave('Suave'),
  lineal('Lineal'),
  corte('Corte rápido');

  const CurvaFader(this.nombre);
  final String nombre;

  static CurvaFader deNombre(Object? n) =>
      CurvaFader.values.where((t) => t.name == n).firstOrNull ?? CurvaFader.suave;
}

/// Volumen (0 a 1) de la que sale o la que entra cuando el cambio va por [avance] (0 a 1).
double ganancia(CurvaFader curva, double avance, {required bool entrante}) {
  final a = avance.clamp(0.0, 1.0);
  switch (curva) {
    case CurvaFader.suave: // potencia constante: no se nota un bache al cruzarse
      return entrante ? sin(a * pi / 2) : cos(a * pi / 2);
    case CurvaFader.lineal:
      return entrante ? a : 1 - a;
    case CurvaFader.corte: // la que sale aguanta y cae de golpe; la que entra llega rapido
      return entrante ? _suave((a - 0.42) / 0.16) : 1 - _suave((a - 0.5) / 0.16);
  }
}

/// Un paso del set: una cancion y como se pasa de ella a la siguiente.
class PasoMezcla {
  PasoMezcla({
    required this.pista,
    this.entraAntes = 8,
    this.fundido = 8,
    this.graves = true,
    this.tipo = TipoTransicion.graves,
    this.curva = CurvaFader.suave,
    this.eq = const [0, 0, 0],
    this.igualarTempo = true,
    this.alCompas = true,
    this.entrada,
    this.salida,
  });

  /// La cancion (el mismo mapa que usa todo el reproductor).
  final Map<String, dynamic> pista;

  /// La siguiente entra cuando a esta le faltan tantos segundos.
  final double entraAntes;

  /// Lo que dura el cambio (los dos suenan a la vez), en segundos.
  final double fundido;

  /// Si en el cambio se intercambian los graves (guardado de antes; hoy lo
  /// manda [tipo], pero se conserva para las mezclas viejas).
  final bool graves;

  /// Que tipo de cambio es (hacia la siguiente).
  final TipoTransicion tipo;

  /// La curva del volumen en el cambio.
  final CurvaFader curva;

  /// Ecualizador de tres bandas (graves, medios, agudos) en dB, de -12 a 12,
  /// que lleva ESTA cancion mientras suena dentro de la mezcla.
  final List<int> eq;

  /// Acercar el tempo de la siguiente al de esta durante el cambio (si hay tempos).
  final bool igualarTempo;

  /// Hacer que la siguiente entre justo al empezar un compas de esta (si hay tempo).
  final bool alCompas;

  /// Segundo de ESTA cancion por el que empieza cuando entra en la mezcla (null: automatico).
  final double? entrada;

  /// Segundo de ESTA cancion en que empieza el cambio hacia la siguiente
  /// (null: el que mande [entraAntes]).
  final double? salida;

  bool get tieneEq => eq.any((e) => e != 0);

  /// Duracion de la cancion en segundos (0 si no se sabe).
  double get duracionPista {
    final d = pista['duracion'];
    final n = d is num ? d.toDouble() : double.tryParse('${d ?? ''}') ?? 0;
    return n > 0 ? n : 0;
  }

  /// Cuando entra de verdad la siguiente: dentro de los limites y sin comerse
  /// mas de la mitad de esta cancion. Si hay un punto de salida marcado, manda ese.
  double get entraEfectivo {
    final d = duracionPista;
    var e = entraAntes;
    if (salida != null && d > 0) e = d - salida!;
    e = e.clamp(entraMin, entraMax);
    return d > 0 ? min(e, d * 0.5) : e;
  }

  /// Lo que dura el cambio de verdad: nunca mas que lo que queda desde que
  /// entra la siguiente (y el corte es casi instantaneo).
  double get fundidoEfectivo {
    if (tipo == TipoTransicion.corte) return 0.3;
    return min(fundido.clamp(fundidoMin, fundidoMax), entraEfectivo);
  }

  /// Segundo de esta cancion en el que empieza el cambio (0 si no se sabe el largo).
  double get inicioDelCambio {
    final d = duracionPista;
    return d > 0 ? max(0, d - entraEfectivo) : 0;
  }

  PasoMezcla copiaCon({
    Map<String, dynamic>? pista,
    double? entraAntes,
    double? fundido,
    bool? graves,
    TipoTransicion? tipo,
    CurvaFader? curva,
    List<int>? eq,
    bool? igualarTempo,
    bool? alCompas,
    double? entrada,
    double? salida,
    bool quitarEntrada = false,
    bool quitarSalida = false,
  }) =>
      PasoMezcla(
        pista: pista ?? this.pista,
        entraAntes: entraAntes ?? this.entraAntes,
        fundido: fundido ?? this.fundido,
        graves: graves ?? this.graves,
        tipo: tipo ?? this.tipo,
        curva: curva ?? this.curva,
        eq: eq ?? this.eq,
        igualarTempo: igualarTempo ?? this.igualarTempo,
        alCompas: alCompas ?? this.alCompas,
        entrada: quitarEntrada ? null : (entrada ?? this.entrada),
        salida: quitarSalida ? null : (salida ?? this.salida),
      );

  Map<String, dynamic> aJson() => {
        'pista': pista,
        'entra_antes': entraAntes,
        'fundido': fundido,
        'graves': graves,
        'tipo': tipo.name,
        'curva': curva.name,
        'eq': eq,
        'tempo': igualarTempo,
        'compas': alCompas,
        if (entrada != null) 'entrada': entrada,
        if (salida != null) 'salida': salida,
      };

  static PasoMezcla? deJson(Object? d) {
    if (d is! Map || d['pista'] is! Map) return null;
    double num_(Object? v, double defecto) => v is num ? v.toDouble() : defecto;
    final graves = d['graves'] is bool ? d['graves'] as bool : true;
    // las mezclas de antes no tienen tipo: eran un fundido, con o sin cambio de graves
    final tipo = d['tipo'] == null
        ? (graves ? TipoTransicion.graves : TipoTransicion.fundido)
        : TipoTransicion.deNombre(d['tipo']);
    final eqCrudo = d['eq'] is List ? d['eq'] as List : const [];
    return PasoMezcla(
      pista: Map<String, dynamic>.from(d['pista'] as Map),
      entraAntes: num_(d['entra_antes'], 8).clamp(entraMin, entraMax),
      fundido: num_(d['fundido'], 8).clamp(fundidoMin, fundidoMax),
      graves: graves,
      tipo: tipo,
      curva: CurvaFader.deNombre(d['curva']),
      eq: [for (var i = 0; i < 3; i++) i < eqCrudo.length && eqCrudo[i] is num ? (eqCrudo[i] as num).round().clamp(-12, 12) : 0],
      igualarTempo: d['tempo'] is bool ? d['tempo'] as bool : false,
      alCompas: d['compas'] is bool ? d['compas'] as bool : false,
      entrada: d['entrada'] is num ? (d['entrada'] as num).toDouble() : null,
      salida: d['salida'] is num ? (d['salida'] as num).toDouble() : null,
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

// ------------------------------------------------------------ ecualizador y filtro

/// El filtro de mpv (`af`) del ecualizador de 3 bandas (graves 100 Hz, medios
/// 1 kHz, agudos 8 kHz), o '' si todo esta a cero. Solo usa `equalizer`.
String filtroEq3(List<int> eq) {
  const f = [100, 1000, 8000];
  final partes = <String>[
    for (var i = 0; i < 3 && i < eq.length; i++)
      if (eq[i] != 0) 'equalizer=f=${f[i]}:t=o:w=2:g=${eq[i].clamp(-12, 12)}',
  ];
  return partes.isEmpty ? '' : 'lavfi=[${partes.join(',')}]';
}

/// Cuanto se recorta (dB, multiplo de 6 entre -18 y 0) en el barrido de filtro:
/// la que sale pierde los graves poco a poco; la que llega empieza sin agudos y los abre.
int dbFiltro(double avance, {required bool entrante}) {
  final a = avance.clamp(0.0, 1.0);
  final t = entrante ? 1 - _suave((a - 0.1) / 0.75) : _suave((a - 0.1) / 0.75);
  return ((dbGravesCortados * t) / 6).round() * 6;
}

/// El filtro del barrido: recorta [db] dB los graves (de la que sale) o los
/// agudos (de la que entra), con tres cortes escalonados.
String filtroBarrido(int db, {required bool agudos}) {
  if (db >= 0) return '';
  final fs = agudos ? const [3000, 6000, 12000] : const [60, 140, 300];
  final gs = [db, (db * 0.8).round(), (db * 0.5).round()];
  return 'lavfi=[${[for (var i = 0; i < 3; i++) 'equalizer=f=${fs[i]}:t=o:w=2:g=${gs[i]}'].join(',')}]';
}

// ------------------------------------------------------------ mezclar como un DJ

/// Ajustes sencillos de la mezcla automatica.
enum PerfilMezcla {
  suave('Suave', 'Cambios largos y discretos, casi sin notarse.'),
  club('Club', 'Cambios con graves, alineados al compás, como en una pista de baile.'),
  rapida('Rápida', 'Cambios cortos y directos: la lista avanza deprisa.');

  const PerfilMezcla(this.nombre, this.ayuda);
  final String nombre;
  final String ayuda;
}

/// Cuantos segundos duran [compases] compases a [bpm] (o [porDefecto] si no se sabe el tempo).
double compasesASegundos(double compases, double? bpm, double porDefecto) =>
    bpm == null || bpm < 40 ? porDefecto : (60 / bpm * 4 * compases);

/// El paso que le toca a una cancion segun el perfil, mirando su ritmo y el de la siguiente.
PasoMezcla pasoParaPerfil(PerfilMezcla perfil, Map<String, dynamic> pista,
    {AnalisisRitmo? ritmo, AnalisisRitmo? siguiente}) {
  final bpm = ritmo != null && ritmo.valido ? ritmo.bpm : null;
  final bpmSig = siguiente != null && siguiente.valido ? siguiente.bpm : null;
  final encaje = encajeDe(bpm, bpmSig);
  switch (perfil) {
    case PerfilMezcla.suave:
      final s = compasesASegundos(4, bpm, 12).clamp(8.0, 14.0);
      return PasoMezcla(pista: pista, entraAntes: s, fundido: s, tipo: TipoTransicion.fundido,
          graves: false, curva: CurvaFader.suave, igualarTempo: true, alCompas: true);
    case PerfilMezcla.club:
      final s = compasesASegundos(8, bpm, 14).clamp(8.0, 16.0);
      // si los tempos chocan, un barrido de filtro disimula mejor que mezclar graves
      return PasoMezcla(pista: pista, entraAntes: s, fundido: s,
          tipo: encaje == Encaje.choca ? TipoTransicion.filtro : TipoTransicion.graves,
          graves: encaje != Encaje.choca, curva: CurvaFader.suave, igualarTempo: true, alCompas: true);
    case PerfilMezcla.rapida:
      final s = compasesASegundos(1, bpm, 4).clamp(2.0, 6.0);
      final corte = encaje == Encaje.bueno;
      return PasoMezcla(pista: pista, entraAntes: s, fundido: s,
          tipo: corte ? TipoTransicion.corte : TipoTransicion.fundido, graves: false,
          curva: corte ? CurvaFader.corte : CurvaFader.suave, igualarTempo: true, alCompas: true);
  }
}

/// Reordena el set para que el paso entre canciones sea suave: empieza por la
/// mas tranquila y va a la que tiene el tempo mas parecido (y la energia mas
/// cercana, subiendo mas que bajando). Lo que no tiene ritmo analizado va al
/// final, en su orden. [ritmo] da el analisis de cada pista por su clave.
List<PasoMezcla> ordenarComoDj(List<PasoMezcla> pasos, Map<String, AnalisisRitmo> ritmo) {
  AnalisisRitmo? de(PasoMezcla p) {
    final r = ritmo['${p.pista['clave']}'];
    return r != null && r.valido ? r : null;
  }

  final con = [for (final p in pasos) if (de(p) != null) p];
  final sin = [for (final p in pasos) if (de(p) == null) p];
  if (con.length < 2) return List.of(pasos);
  final resto = List.of(con);
  resto.sort((a, b) => de(a)!.energia.compareTo(de(b)!.energia));
  final salida = <PasoMezcla>[resto.removeAt(0)];
  while (resto.isNotEmpty) {
    final a = de(salida.last)!;
    var mejor = 0;
    var mejorC = double.infinity;
    for (var i = 0; i < resto.length; i++) {
      final b = de(resto[i])!;
      final dt = diferenciaDeTempo(a.bpm, b.bpm);
      final dE = b.energia - a.energia;
      final c = dt * 10 + (dE >= 0 ? dE * 0.5 : -dE * 0.9);
      if (c < mejorC) {
        mejorC = c;
        mejor = i;
      }
    }
    salida.add(resto.removeAt(mejor));
  }
  return [...salida, ...sin];
}

/// Que tal encaja cada paso con el siguiente (uno menos que canciones).
List<Encaje> encajesDelSet(List<PasoMezcla> pasos, Map<String, AnalisisRitmo> ritmo) {
  double? bpm(PasoMezcla p) {
    final r = ritmo['${p.pista['clave']}'];
    return r != null && r.valido ? r.bpm : null;
  }

  return [for (var i = 0; i + 1 < pasos.length; i++) encajeDe(bpm(pasos[i]), bpm(pasos[i + 1]))];
}

/// «Mezclar esta lista como un DJ»: la ordena y pone a cada paso lo del perfil.
List<PasoMezcla> mezclaAutomatica(List<Map<String, dynamic>> pistas, PerfilMezcla perfil,
    Map<String, AnalisisRitmo> ritmo, {bool ordenar = true}) {
  var pasos = [for (final p in pistas) PasoMezcla(pista: p)];
  if (ordenar) pasos = ordenarComoDj(pasos, ritmo);
  AnalisisRitmo? r(int i) => i < pasos.length ? ritmo['${pasos[i].pista['clave']}'] : null;
  return [
    for (var i = 0; i < pasos.length; i++)
      pasoParaPerfil(perfil, pasos[i].pista, ritmo: r(i), siguiente: r(i + 1)),
  ];
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

// ------------------------------------------------------------ cuando entra la siguiente

/// En que segundo de la cancion que suena debe empezar el cambio: [fin] es
/// donde acaba su musica. Sin tempo, es `fin - lo que pide el paso`. Con
/// tempo y `alCompas`, se ajusta al inicio de compas mas cercano (sin pasarse
/// de la mitad del cambio), para que la siguiente entre "en el uno".
double momentoDeEntrada(PasoMezcla paso, double fin, AnalisisRitmo? ritmo) {
  var t = fin - paso.entraEfectivo;
  if (paso.alCompas && ritmo != null && ritmo.valido) {
    final alante = alinearAlCompas(t, ritmo.bpm, ritmo.primerTiempo);
    final atras = alinearAlCompas(t, ritmo.bpm, ritmo.primerTiempo, haciaAtras: true);
    // lo bastante antes del final como para que el cambio quepa
    final limite = fin - paso.fundidoEfectivo;
    t = alante <= limite ? (alante - t <= t - atras ? alante : atras) : atras;
  }
  return max(0, t);
}

/// Desde que segundo de la cancion que entra conviene empezarla: el punto de
/// entrada marcado; si no, el inicio de compas siguiente al inicio de la musica.
double inicioDeEntrante(PasoMezcla paso, double inicioMusica, AnalisisRitmo? ritmo) {
  if (paso.entrada != null) return max(0, paso.entrada!);
  if (paso.alCompas && ritmo != null && ritmo.valido) {
    return max(0, alinearAlCompas(inicioMusica, ritmo.bpm, ritmo.primerTiempo));
  }
  return inicioMusica;
}
