// Logros: insignias por rachas de escucha, horas, canciones descubiertas, listas, escuchar con
// amigos... (igual que escritorio/descargador/logros.py: mismas claves, mismas metas, mismo guardado).
//
// Todo se cuenta en el dispositivo (preferencias, una entrada por cuenta) y se junta con la nube
// (supabase/logros.sql) para que el teléfono y la computadora tengan los mismos. Al juntar nunca se
// pierde nada: cada contador se queda con el mayor, los días se suman y cada logro conserva la
// fecha más antigua en que se consiguió.
//
// Quien cuenta (logros_vigia.dart) avisa de lo que pasa con anotarSegundos, anotarPista,
// anotarListas/anotarMeGusta/anotarDescargas y anotarSala; `revisar()` devuelve los recién
// conseguidos (para el aviso).

import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'avisos.dart';
import 'nube.dart';

class Logro {
  const Logro(this.id, this.nombre, this.descripcion, this.categoria, this.metrica, this.meta);
  final String id;
  final String nombre;
  final String descripcion;
  final String categoria;
  final String metrica;
  final int meta;
}

const categoriasLogros = <(String, String)>[
  ('rachas', 'Rachas'),
  ('horas', 'Horas de música'),
  ('descubrir', 'Descubrir'),
  ('listas', 'Listas y me gusta'),
  ('amigos', 'Con amigos'),
  ('especiales', 'Especiales'),
];

const catalogoLogros = <Logro>[
  Logro('primera_nota', 'Primera nota', 'Escucha tu primera canción en Caudal.', 'descubrir', 'canciones', 1),
  Logro('racha_3', 'Encendido', 'Escucha música 3 días seguidos.', 'rachas', 'racha', 3),
  Logro('racha_7', 'Semana en llamas', 'Escucha música 7 días seguidos.', 'rachas', 'racha', 7),
  Logro('racha_30', 'Mes imparable', 'Escucha música 30 días seguidos.', 'rachas', 'racha', 30),
  Logro('racha_100', 'Leyenda del ritmo', 'Escucha música 100 días seguidos.', 'rachas', 'racha', 100),
  Logro('horas_1', 'Primera hora', 'Acumula 1 hora de música.', 'horas', 'horas', 1),
  Logro('horas_10', 'Diez horas', 'Acumula 10 horas de música.', 'horas', 'horas', 10),
  Logro('horas_100', 'Cien horas', 'Acumula 100 horas de música.', 'horas', 'horas', 100),
  Logro('horas_500', 'Disco de oro', 'Acumula 500 horas de música.', 'horas', 'horas', 500),
  Logro('descubre_50', 'Brújula musical', 'Escucha 50 canciones distintas.', 'descubrir', 'canciones', 50),
  Logro('descubre_250', 'Oído curioso', 'Escucha 250 canciones distintas.', 'descubrir', 'canciones', 250),
  Logro('descubre_1000', 'Planeta música', 'Escucha 1000 canciones distintas.', 'descubrir', 'canciones', 1000),
  Logro('artistas_25', 'Abanico de artistas', 'Escucha a 25 artistas distintos.', 'descubrir', 'artistas', 25),
  Logro('lista_1', 'Mi primera lista', 'Crea tu primera lista.', 'listas', 'listas', 1),
  Logro('lista_5', 'Mixtape', 'Crea 5 listas.', 'listas', 'listas', 5),
  Logro('lista_15', 'Cofre de listas', 'Crea 15 listas.', 'listas', 'listas', 15),
  Logro('gusta_25', 'Flechazo', 'Dale me gusta a 25 canciones.', 'listas', 'me_gusta', 25),
  Logro('gusta_200', 'Corazón grande', 'Dale me gusta a 200 canciones.', 'listas', 'me_gusta', 200),
  Logro('juntos_1', 'Mejor en compañía', 'Escucha música con amigos en «Escuchar juntos».', 'amigos', 'juntos', 1),
  Logro('juntos_10', 'Alma de la fiesta', 'Comparte 10 salas de «Escuchar juntos».', 'amigos', 'juntos', 10),
  Logro('anfitrion', 'La sala es tuya', 'Abre una sala de «Escuchar juntos» y que alguien se una.', 'amigos',
      'anfitrion', 1),
  Logro('noctambulo', 'Búho nocturno', 'Escucha 10 canciones entre la medianoche y las 5 a. m.', 'especiales',
      'noche', 10),
  Logro('madrugador', 'Al alba', 'Escucha 10 canciones entre las 5 y las 8 de la mañana.', 'especiales',
      'manana', 10),
  Logro('maraton', 'Maratón', 'Escucha 4 horas de música en un mismo día.', 'especiales', 'dia_horas', 4),
  Logro('descargas_25', 'Sin internet, sin problema', 'Guarda 25 canciones o videos para escucharlos sin internet.', 'especiales',
      'descargas', 25),
  Logro('dos_mundos', 'Dos mundos', 'Usa Caudal en la computadora y en el teléfono con tu cuenta.', 'especiales',
      'dispositivos', 2),
  Logro('coleccionista', 'Vitrina llena', 'Consigue 15 logros.', 'especiales', 'logros', 15),
];

final Map<String, Logro> logroPorId = {for (final l in catalogoLogros) l.id: l};

const contadoresLogros = <String>[
  'segundos', 'canciones', 'artistas', 'listas', 'me_gusta', 'juntos', 'anfitrion', 'noche', 'manana',
  'descargas', 'dia_max', 'racha_max',
];
const vitrinaMax = 3;
const _diasGuardados = 400;
const segundosParaDia = 60; // un día cuenta para la racha con al menos un minuto de música
const _maxClaves = 20000;
const _escritorio = {'windows', 'macos', 'linux'};
const _movil = {'android', 'ios'};

String fechaTexto(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

DateTime? _fecha(Object? t) {
  final m = RegExp(r'^(\d{4})-(\d{2})-(\d{2})$').firstMatch('$t');
  if (m == null) return null;
  final d = DateTime(int.parse(m[1]!), int.parse(m[2]!), int.parse(m[3]!));
  return fechaTexto(d) == '$t' ? d : null;
}

int _entero(Object? v) {
  if (v is bool) return 0;
  if (v is num) return v.isFinite && v > 0 ? v.floor() : 0;
  final n = num.tryParse('$v');
  return n == null || !n.isFinite || n < 0 ? 0 : n.floor();
}

/// Días seguidos más largos en una lista de fechas aaaa-mm-dd (en cualquier orden).
int rachaMasLarga(Iterable<String> dias) {
  final fechas = {for (final d in dias) _fecha(d)}.whereType<DateTime>().toList()..sort();
  var mejor = 0, actual = 0;
  DateTime? anterior;
  for (final f in fechas) {
    actual = anterior != null && _esSiguiente(anterior, f) ? actual + 1 : 1;
    if (actual > mejor) mejor = actual;
    anterior = f;
  }
  return mejor;
}

bool _esSiguiente(DateTime a, DateTime b) {
  final s = DateTime(a.year, a.month, a.day + 1);
  return s.year == b.year && s.month == b.month && s.day == b.day;
}

/// Días seguidos que terminan hoy (o ayer: la racha sigue viva hasta que acabe el día).
int rachaEnCurso(Iterable<String> dias, DateTime hoy) {
  final fechas = dias.toSet();
  var dia = DateTime(hoy.year, hoy.month, hoy.day);
  if (!fechas.contains(fechaTexto(dia))) dia = DateTime(dia.year, dia.month, dia.day - 1);
  var n = 0;
  while (fechas.contains(fechaTexto(dia))) {
    n++;
    dia = DateTime(dia.year, dia.month, dia.day - 1);
  }
  return n;
}

/// Nombres de los artistas de una pista (en minúsculas), como los guarda la colección.
List<String> artistasDe(Map? pista) {
  final nombres = <String>[];
  final lista = pista?['artistas'];
  if (lista is List) {
    for (final a in lista) {
      final n = a is Map ? a['nombre'] : a;
      if (n != null && '$n'.trim().isNotEmpty) nombres.add('$n'.trim().toLowerCase());
    }
  }
  if (nombres.isEmpty && pista?['artista'] != null) {
    for (final p in '${pista!['artista']}'.split(',')) {
      if (p.trim().isNotEmpty) nombres.add(p.trim().toLowerCase());
    }
  }
  return nombres;
}

class Logros extends ChangeNotifier {
  Logros._(this._clave, this.plataforma, DateTime Function()? reloj) : _reloj = reloj ?? DateTime.now {
    _vaciar();
  }

  /// Sin disco (pruebas y web sin preferencias).
  factory Logros.enMemoria({String plataforma = 'android', DateTime Function()? reloj}) =>
      Logros._(null, plataforma, reloj)..plataformas.add(plataforma);

  /// Los de una cuenta, guardados en las preferencias del dispositivo.
  static Future<Logros> abrir(String cuentaId, {String? plataforma, DateTime Function()? reloj}) async {
    final l = Logros._('logros_$cuentaId', plataforma ?? Avisos.plataforma, reloj);
    try {
      final p = await SharedPreferences.getInstance();
      final t = p.getString(l._clave!);
      if (t != null) l.cargarDe(jsonDecode(t));
    } catch (_) {}
    l.plataformas.add(l.plataforma);
    return l;
  }

  final String? _clave;
  final String plataforma;
  final DateTime Function() _reloj;
  DateTime get ahora => _reloj();

  late Map<String, int> contadores;
  late Set<String> dias;
  late Set<String> plataformas;
  late Set<String> claves;
  late Set<String> artistasVistos;
  late List<String> salas;
  late String hoyFecha;
  late int hoySegundos;
  late Map<String, int> desbloqueados;
  late List<String> vitrina;
  bool importado = false;
  bool pendienteNube = false;

  void _vaciar() {
    contadores = {for (final k in contadoresLogros) k: 0};
    dias = {};
    plataformas = {};
    claves = {};
    artistasVistos = {};
    salas = [];
    hoyFecha = '';
    hoySegundos = 0;
    desbloqueados = {};
    vitrina = [];
    importado = false;
    pendienteNube = false;
  }

  // ------------------------------------------------------------ guardado

  void cargarDe(Object? d) {
    if (d is! Map) return;
    final c = d['contadores'];
    for (final k in contadoresLogros) {
      contadores[k] = _entero(c is Map ? c[k] : null);
    }
    List<String> lista(Object? x) => x is List ? [for (final e in x) '$e'] : <String>[];
    dias = lista(d['dias']).where((x) => _fecha(x) != null).toSet();
    plataformas = lista(d['plataformas']).toSet();
    claves = lista(d['claves']).toSet();
    artistasVistos = lista(d['artistas_vistos']).toSet();
    final s = lista(d['salas']);
    salas = s.length > 50 ? s.sublist(s.length - 50) : s;
    final hoy = d['hoy'];
    hoyFecha = hoy is Map ? '${hoy['fecha'] ?? ''}' : '';
    hoySegundos = hoy is Map ? _entero(hoy['segundos']) : 0;
    final desb = d['desbloqueados'];
    desbloqueados = {
      if (desb is Map)
        for (final e in desb.entries)
          if (logroPorId.containsKey('${e.key}')) '${e.key}': _entero(e.value),
    };
    vitrina = lista(d['vitrina']).where(desbloqueados.containsKey).take(vitrinaMax).toList();
    importado = d['importado'] == true;
    pendienteNube = d['pendiente_nube'] == true;
  }

  Map<String, Object?> datos() {
    final d = dias.toList()..sort();
    final cl = claves.toList()..sort();
    final ar = artistasVistos.toList()..sort();
    return {
      'version': 1,
      'contadores': Map.of(contadores),
      'dias': d.length > _diasGuardados ? d.sublist(d.length - _diasGuardados) : d,
      'plataformas': plataformas.toList()..sort(),
      'claves': cl.take(_maxClaves).toList(),
      'artistas_vistos': ar.take(_maxClaves).toList(),
      'salas': salas,
      'hoy': {'fecha': hoyFecha, 'segundos': hoySegundos},
      'desbloqueados': Map.of(desbloqueados),
      'vitrina': List.of(vitrina),
      'importado': importado,
      'pendiente_nube': pendienteNube,
    };
  }

  Timer? _guardando;

  /// Guarda en un momento (los cambios seguidos se juntan en una sola escritura).
  void guardar({bool ya = false}) {
    if (_clave == null) return;
    _guardando?.cancel();
    if (ya) {
      unawaited(_escribir());
    } else {
      _guardando = Timer(const Duration(seconds: 2), () => unawaited(_escribir()));
    }
  }

  Future<void> _escribir() async {
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_clave!, jsonEncode(datos()));
    } catch (_) {}
  }

  // ------------------------------------------------------------ lo que pasa

  void anotarSegundos(num segundos, {DateTime? cuando}) {
    final s = _entero(segundos);
    if (s <= 0) return;
    final fecha = fechaTexto(cuando ?? ahora);
    contadores['segundos'] = contadores['segundos']! + s;
    if (hoyFecha != fecha) {
      hoyFecha = fecha;
      hoySegundos = 0;
    }
    hoySegundos += s;
    if (hoySegundos > contadores['dia_max']!) contadores['dia_max'] = hoySegundos;
    if (hoySegundos >= segundosParaDia && dias.add(fecha)) {
      final r = rachaMasLarga(dias);
      if (r > contadores['racha_max']!) contadores['racha_max'] = r;
    }
    pendienteNube = true;
  }

  void anotarCancion(String? clave, Iterable<String> artistas, {DateTime? cuando}) {
    if (clave == null || clave.isEmpty) return;
    final hora = (cuando ?? ahora).hour;
    if (claves.add(clave)) contadores['canciones'] = contadores['canciones']! + 1;
    for (final a in artistas) {
      final n = a.trim().toLowerCase();
      if (n.isNotEmpty && artistasVistos.add(n)) contadores['artistas'] = contadores['artistas']! + 1;
    }
    if (hora < 5) {
      contadores['noche'] = contadores['noche']! + 1;
    } else if (hora < 8) {
      contadores['manana'] = contadores['manana']! + 1;
    }
    pendienteNube = true;
  }

  /// Atajo: una pista de la app (mapa con clave y artistas).
  void anotarPista(Map? pista, {DateTime? cuando}) {
    if (pista == null) return;
    anotarCancion(pista['clave'] as String?, artistasDe(pista), cuando: cuando);
  }

  void _total(String clave, int n) {
    if (n > contadores[clave]!) {
      contadores[clave] = n;
      pendienteNube = true;
    }
  }

  void anotarListas(int total) => _total('listas', total);
  void anotarMeGusta(int total) => _total('me_gusta', total);
  void anotarDescargas(int total) => _total('descargas', total);

  /// Una sala de «Escuchar juntos». Cuenta una vez por sala y solo si había alguien más.
  void anotarSala(String ident, {required bool conAmigos, bool soyAnfitrion = false}) {
    if (ident.isEmpty || !conAmigos || salas.contains(ident)) return;
    salas = [...salas, ident];
    if (salas.length > 50) salas = salas.sublist(salas.length - 50);
    contadores['juntos'] = contadores['juntos']! + 1;
    if (soyAnfitrion) contadores['anfitrion'] = contadores['anfitrion']! + 1;
    pendienteNube = true;
  }

  /// Lo ya escuchado antes de existir los logros (una sola vez): (clave, fecha en segundos, pista?).
  /// Cuenta canciones, artistas, días y horarios; las horas empiezan a contar desde ahora.
  void importar(Iterable<(String, num, Map?)> reproducciones) {
    if (importado) return;
    for (final (clave, fecha, pista) in reproducciones) {
      final cuando = DateTime.fromMillisecondsSinceEpoch((fecha * 1000).round());
      anotarCancion(clave, artistasDe(pista), cuando: cuando);
      dias.add(fechaTexto(cuando));
    }
    final r = rachaMasLarga(dias);
    if (r > contadores['racha_max']!) contadores['racha_max'] = r;
    importado = true;
    pendienteNube = true;
  }

  // ------------------------------------------------------------ cuentas

  int rachaActual([DateTime? hoy]) => rachaEnCurso(dias, hoy ?? ahora);

  int valor(String metrica) {
    final c = contadores;
    switch (metrica) {
      case 'racha':
        final r = rachaMasLarga(dias);
        return r > c['racha_max']! ? r : c['racha_max']!;
      case 'horas':
        return c['segundos']! ~/ 3600;
      case 'dia_horas':
        return c['dia_max']! ~/ 3600;
      case 'dispositivos':
        return (plataformas.any(_escritorio.contains) ? 1 : 0) + (plataformas.any(_movil.contains) ? 1 : 0);
      case 'logros':
        return desbloqueados.length;
    }
    return c[metrica] ?? 0;
  }

  /// (valor, meta, fracción 0..1) de un logro.
  (int, int, double) progreso(Logro l) {
    final v = valor(l.metrica);
    return (v, l.meta, l.meta == 0 ? 1.0 : (v / l.meta).clamp(0.0, 1.0).toDouble());
  }

  bool conseguido(String id) => desbloqueados.containsKey(id);

  /// Desbloquea lo que ya se cumplió y lo devuelve (en el orden del catálogo).
  List<Logro> revisar() {
    final nuevos = <Logro>[];
    final t = ahora.millisecondsSinceEpoch ~/ 1000;
    // dos vueltas: «Vitrina llena» depende de cuántos hay
    for (var vuelta = 0; vuelta < 2; vuelta++) {
      for (final l in catalogoLogros) {
        if (!desbloqueados.containsKey(l.id) && valor(l.metrica) >= l.meta) {
          desbloqueados[l.id] = t;
          nuevos.add(l);
        }
      }
    }
    if (nuevos.isNotEmpty) {
      pendienteNube = true;
      notifyListeners();
    }
    guardar();
    return nuevos;
  }

  ({int conseguidos, int total, int racha, int horas}) get resumen => (
        conseguidos: desbloqueados.length,
        total: catalogoLogros.length,
        racha: rachaActual(),
        horas: contadores['segundos']! ~/ 3600,
      );

  // ------------------------------------------------------------ vitrina

  List<String> ponerVitrina(Iterable<String> ids) {
    final limpio = <String>[];
    for (final i in ids) {
      if (desbloqueados.containsKey(i) && !limpio.contains(i)) limpio.add(i);
    }
    vitrina = limpio.take(vitrinaMax).toList();
    pendienteNube = true;
    guardar();
    notifyListeners();
    return List.of(vitrina);
  }

  /// Pone o quita un logro de la vitrina. false si no se pudo (no conseguido o llena).
  bool alternarVitrina(String id) {
    if (!desbloqueados.containsKey(id)) return false;
    if (vitrina.contains(id)) {
      ponerVitrina(vitrina.where((x) => x != id));
      return true;
    }
    if (vitrina.length >= vitrinaMax) return false;
    ponerVitrina([...vitrina, id]);
    return true;
  }

  // ------------------------------------------------------------ nube

  Map<String, dynamic> paraNube() {
    final d = dias.toList()..sort();
    return {
      'p_contadores': Map.of(contadores),
      'p_dias': d.length > _diasGuardados ? d.sublist(d.length - _diasGuardados) : d,
      'p_plataformas': plataformas.toList()..sort(),
      'p_desbloqueados': Map.of(desbloqueados),
      'p_vitrina': List.of(vitrina),
    };
  }

  /// Junta lo que devolvió la nube (logros_guardar / logros_mios). Nunca baja nada.
  void mezclar(Object? remoto) {
    if (remoto is! Map) return;
    final c = remoto['contadores'];
    if (c is Map) {
      for (final e in c.entries) {
        final k = '${e.key}';
        if (contadores.containsKey(k)) {
          final v = _entero(e.value);
          if (v > contadores[k]!) contadores[k] = v;
        }
      }
    }
    final d = remoto['dias'];
    if (d is List) dias.addAll([for (final x in d) '$x'].where((x) => _fecha(x) != null));
    final p = remoto['plataformas'];
    if (p is List) plataformas.addAll([for (final x in p) '$x']);
    final desb = remoto['desbloqueados'];
    if (desb is Map) {
      for (final e in desb.entries) {
        final k = '${e.key}';
        if (!logroPorId.containsKey(k)) continue;
        final v = _entero(e.value);
        final mio = desbloqueados[k];
        if (mio == null || (v > 0 && v < mio)) desbloqueados[k] = v;
      }
    }
    final vit = remoto['vitrina'];
    if (vit is List) vitrina = [for (final x in vit) '$x'].where(desbloqueados.containsKey).take(vitrinaMax).toList();
    final r = rachaMasLarga(dias);
    if (r > contadores['racha_max']!) contadores['racha_max'] = r;
    guardar();
    notifyListeners();
  }

  /// Sube lo de este dispositivo y se queda con lo juntado. true si se pudo (sin red o sin la
  /// tabla en el servidor no pasa nada: se intenta más tarde).
  Future<bool> sincronizar(Sesion? sesion) async {
    if (sesion == null || sesion.acceso.isEmpty) return false;
    try {
      final r = await sesion.rpc('logros_guardar', paraNube());
      if (r is! Map) return false;
      pendienteNube = false;
      mezclar(r);
      return true;
    } catch (_) {
      return false;
    }
  }

  @override
  void dispose() {
    if (_guardando?.isActive ?? false) {
      _guardando!.cancel();
      unawaited(_escribir());
    }
    super.dispose();
  }
}

/// La vitrina de otra persona: (ids, total, fechas), o null si no se puede ver.
Future<({List<String> vitrina, int total, Map<String, int> fechas})?> vitrinaDe(Sesion? sesion, String usuario) async {
  if (sesion == null || usuario.isEmpty) return null;
  try {
    final r = await sesion.rpc('logros_de', {'p_usuario': usuario});
    if (r is! Map) return null;
    final v = r['vitrina'];
    final f = r['fechas'];
    return (
      vitrina: v is List ? [for (final x in v) '$x'].where(logroPorId.containsKey).take(vitrinaMax).toList() : <String>[],
      total: _entero(r['total']),
      fechas: {if (f is Map) for (final e in f.entries) '${e.key}': _entero(e.value)},
    );
  } catch (_) {
    return null;
  }
}
