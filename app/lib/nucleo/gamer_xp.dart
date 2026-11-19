// Nivel, XP, misiones diarias y racha del «Modo gamer». Lógica pura (sin Flutter
// ni reproductor): se alimenta con [ProgresoGamer.registrar] y devuelve el
// progreso nuevo; así se prueba sin nada más.

import 'dart:convert';
import 'dart:math' as math;

const int nivelMaximo = 99;

/// XP total necesaria para LLEGAR al nivel [n] (el 1 es el de partida: 0 XP).
/// Curva suave: 40 · (n-1)^1.5 → nivel 2 a los 40 min, 5 a las 5 h, 10 a las 18 h.
int xpParaNivel(int n) {
  if (n <= 1) return 0;
  return (40 * math.pow(n - 1, 1.5)).round();
}

int nivelDeXp(int xp) {
  if (xp <= 0) return 1;
  var n = (math.pow(xp / 40, 2 / 3)).floor() + 1;
  while (n < nivelMaximo && xpParaNivel(n + 1) <= xp) {
    n++;
  }
  while (n > 1 && xpParaNivel(n) > xp) {
    n--;
  }
  return n.clamp(1, nivelMaximo);
}

/// 0..1: lo que lleva del nivel actual al siguiente (1 en el nivel máximo).
double fraccionNivel(int xp) {
  final n = nivelDeXp(xp);
  if (n >= nivelMaximo) return 1;
  final a = xpParaNivel(n), b = xpParaNivel(n + 1);
  return ((xp - a) / (b - a)).clamp(0.0, 1.0);
}

String claveDia(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

int _diasEntre(String a, String b) {
  DateTime? leer(String s) {
    final p = s.split('-');
    if (p.length != 3) return null;
    final y = int.tryParse(p[0]), m = int.tryParse(p[1]), d = int.tryParse(p[2]);
    if (y == null || m == null || d == null) return null;
    return DateTime.utc(y, m, d);
  }

  final x = leer(a), y = leer(b);
  if (x == null || y == null) return 999999;
  return y.difference(x).inDays;
}

enum TipoMision { minutos, artistas, nuevas }

class MisionGamer {
  const MisionGamer({required this.id, required this.tipo, required this.meta, required this.xp});
  final String id; // «2026-11-19:minutos»
  final TipoMision tipo;
  final int meta;

  /// XP extra al completarla.
  final int xp;

  String get titulo => switch (tipo) {
        TipoMision.minutos => 'Escucha $meta min',
        TipoMision.artistas => '$meta artistas distintos',
        TipoMision.nuevas => '$meta canciones nuevas',
      };

  String get unidad => switch (tipo) {
        TipoMision.minutos => 'min',
        TipoMision.artistas => 'artistas',
        TipoMision.nuevas => 'canciones',
      };
}

const _metasMinutos = [10, 15, 20, 30, 45];
const _metasArtistas = [3, 4, 5, 6, 8];
const _metasNuevas = [3, 4, 5, 7, 10];

int _mezcla(int semilla, int k) {
  final h = ((semilla + k * 7919) * 40503) % 1000003;
  return (h ~/ 7 + k * 13) ;
}

/// Las 3 misiones de un día: siempre las mismas para esa fecha (y para todos).
List<MisionGamer> misionesDelDia(DateTime dia) {
  final semilla = dia.year * 10000 + dia.month * 100 + dia.day;
  final k = claveDia(dia);
  final m = _metasMinutos[_mezcla(semilla, 1) % _metasMinutos.length];
  final a = _metasArtistas[_mezcla(semilla, 2) % _metasArtistas.length];
  final n = _metasNuevas[_mezcla(semilla, 3) % _metasNuevas.length];
  return [
    MisionGamer(id: '$k:minutos', tipo: TipoMision.minutos, meta: m, xp: m),
    MisionGamer(id: '$k:artistas', tipo: TipoMision.artistas, meta: a, xp: a * 4),
    MisionGamer(id: '$k:nuevas', tipo: TipoMision.nuevas, meta: n, xp: n * 3),
  ];
}

/// Qué pasó al registrar una escucha.
class ResultadoXp {
  const ResultadoXp({required this.progreso, required this.nivelAntes, required this.xpGanado, required this.misiones});
  final ProgresoGamer progreso;
  final int nivelAntes;
  final int xpGanado;

  /// Misiones que se completaron con esta escucha.
  final List<MisionGamer> misiones;

  int get nivelAhora => progreso.nivel;
  bool get subioNivel => nivelAhora > nivelAntes;
}

class ProgresoGamer {
  const ProgresoGamer({
    this.xp = 0,
    this.segPendientes = 0,
    this.segTotales = 0,
    this.racha = 0,
    this.mejorRacha = 0,
    this.ultimoDia = '',
    this.dia = '',
    this.segHoy = 0,
    this.artistasHoy = const [],
    this.nuevasHoy = const [],
    this.completadas = const [],
    this.vistas = const [],
  });

  final int xp;

  /// Segundos que aún no suman un minuto entero (1 XP por minuto).
  final int segPendientes;
  final int segTotales;
  final int racha, mejorRacha;

  /// Último día con escucha contada (para la racha).
  final String ultimoDia;

  /// Día al que pertenece lo «de hoy».
  final String dia;
  final int segHoy;
  final List<String> artistasHoy, nuevasHoy;

  /// Ids de las misiones ya cobradas.
  final List<String> completadas;

  /// Canciones ya oídas (las últimas [_tope]); lo que no esté aquí cuenta como nueva.
  final List<String> vistas;

  static const _tope = 400;

  int get nivel => nivelDeXp(xp);
  double get fraccion => fraccionNivel(xp);
  int get xpNivelActual => xpParaNivel(nivel);
  int get xpSiguiente => xpParaNivel(math.min(nivel + 1, nivelMaximo));
  int get minutosHoy => segHoy ~/ 60;

  /// La racha que se enseña: si ayer no escuchó, ya se perdió.
  int rachaVigente(DateTime ahora) {
    final hoy = claveDia(ahora);
    if (ultimoDia.isEmpty) return 0;
    final d = _diasEntre(ultimoDia, hoy);
    return d <= 1 ? racha : 0;
  }

  /// Lo de hoy tal cual está (si el día guardado es otro, todo en cero).
  ProgresoGamer alDia(DateTime ahora) {
    final hoy = claveDia(ahora);
    if (dia == hoy) return this;
    return _copiar(dia: hoy, segHoy: 0, artistasHoy: const [], nuevasHoy: const [], completadas: const []);
  }

  int valorMision(MisionGamer m) => switch (m.tipo) {
        TipoMision.minutos => minutosHoy,
        TipoMision.artistas => artistasHoy.length,
        TipoMision.nuevas => nuevasHoy.length,
      };

  bool misionHecha(MisionGamer m) => completadas.contains(m.id);

  /// Suma una escucha: [segundos] oídos y, si ya cuenta como oída, la
  /// [cancion] con sus [artistas]. Devuelve el progreso nuevo y qué pasó.
  ResultadoXp registrar(DateTime ahora, {int segundos = 0, String? cancion, List<String> artistas = const []}) {
    var p = alDia(ahora);
    final antes = p.nivel;
    final seg = segundos < 0 ? 0 : segundos;

    final pend = p.segPendientes + seg;
    var xpNuevo = p.xp + pend ~/ 60;
    var ganado = pend ~/ 60;

    var art = p.artistasHoy, nue = p.nuevasHoy, vis = p.vistas;
    for (final a in artistas) {
      final n = a.trim().toLowerCase();
      if (n.isNotEmpty && !art.contains(n)) art = [...art, n];
    }
    if (cancion != null && cancion.isNotEmpty && !vis.contains(cancion)) {
      nue = [...nue, cancion];
      vis = [...vis, cancion];
      if (vis.length > _tope) vis = vis.sublist(vis.length - _tope);
    }

    var q = p._copiar(
      xp: xpNuevo,
      segPendientes: pend % 60,
      segTotales: p.segTotales + seg,
      segHoy: p.segHoy + seg,
      artistasHoy: art,
      nuevasHoy: nue,
      vistas: vis,
    );

    // la racha cuenta el día en cuanto lleva un minuto escuchado
    if (q.segHoy >= 60 && q.ultimoDia != q.dia) {
      final d = q.ultimoDia.isEmpty ? 999999 : _diasEntre(q.ultimoDia, q.dia);
      final r = d == 1 ? q.racha + 1 : 1;
      q = q._copiar(racha: r, mejorRacha: math.max(q.mejorRacha, r), ultimoDia: q.dia);
    }

    // misiones recién cumplidas: su XP extra se cobra una sola vez
    final hechas = <MisionGamer>[];
    var cobradas = q.completadas;
    for (final m in misionesDelDia(ahora)) {
      if (!cobradas.contains(m.id) && q.valorMision(m) >= m.meta) {
        hechas.add(m);
        cobradas = [...cobradas, m.id];
        xpNuevo += m.xp;
        ganado += m.xp;
      }
    }
    if (hechas.isNotEmpty) q = q._copiar(xp: xpNuevo, completadas: cobradas);

    return ResultadoXp(progreso: q, nivelAntes: antes, xpGanado: ganado, misiones: hechas);
  }

  ProgresoGamer _copiar({
    int? xp,
    int? segPendientes,
    int? segTotales,
    int? racha,
    int? mejorRacha,
    String? ultimoDia,
    String? dia,
    int? segHoy,
    List<String>? artistasHoy,
    List<String>? nuevasHoy,
    List<String>? completadas,
    List<String>? vistas,
  }) =>
      ProgresoGamer(
        xp: xp ?? this.xp,
        segPendientes: segPendientes ?? this.segPendientes,
        segTotales: segTotales ?? this.segTotales,
        racha: racha ?? this.racha,
        mejorRacha: mejorRacha ?? this.mejorRacha,
        ultimoDia: ultimoDia ?? this.ultimoDia,
        dia: dia ?? this.dia,
        segHoy: segHoy ?? this.segHoy,
        artistasHoy: artistasHoy ?? this.artistasHoy,
        nuevasHoy: nuevasHoy ?? this.nuevasHoy,
        completadas: completadas ?? this.completadas,
        vistas: vistas ?? this.vistas,
      );

  String aTexto() => jsonEncode({
        'xp': xp,
        'sp': segPendientes,
        'st': segTotales,
        'r': racha,
        'mr': mejorRacha,
        'ud': ultimoDia,
        'd': dia,
        'sh': segHoy,
        'ah': artistasHoy,
        'nh': nuevasHoy,
        'c': completadas,
        'v': vistas,
      });

  /// Tolera texto vacío o roto: arranca de cero en vez de fallar.
  factory ProgresoGamer.deTexto(String? texto) {
    if (texto == null || texto.isEmpty) return const ProgresoGamer();
    try {
      final j = jsonDecode(texto);
      if (j is! Map) return const ProgresoGamer();
      int n(String k) => (j[k] is num) ? (j[k] as num).toInt().clamp(0, 1 << 40) : 0;
      String s(String k) => j[k] is String ? j[k] as String : '';
      List<String> l(String k) => j[k] is List ? [for (final e in j[k] as List) '$e'] : const [];
      return ProgresoGamer(
        xp: n('xp'),
        segPendientes: n('sp') % 60,
        segTotales: n('st'),
        racha: n('r'),
        mejorRacha: n('mr'),
        ultimoDia: s('ud'),
        dia: s('d'),
        segHoy: n('sh'),
        artistasHoy: l('ah'),
        nuevasHoy: l('nh'),
        completadas: l('c'),
        vistas: l('v'),
      );
    } catch (_) {
      return const ProgresoGamer();
    }
  }
}
