import 'coleccion.dart';
import 'gamer_xp.dart' show claveDia;
import 'mixes.dart' show Escucha;
import 'resumen_anual.dart' show PuestoAnual;

/// Lo más escuchado de una semana (de lunes a domingo), para la tarjeta que se comparte los
/// domingos. Todo sale de las escuchas guardadas en el teléfono, sin red. La cuenta es pura.
class ResumenSemanal {
  const ResumenSemanal({
    required this.lunes,
    required this.escuchas,
    required this.minutos,
    required this.diasConMusica,
    this.topCanciones = const [],
    this.topArtistas = const [],
    this.minutosPorDia = const [0, 0, 0, 0, 0, 0, 0],
    this.diaTop,
    this.artistasDistintos = 0,
    this.cancionesDistintas = 0,
  });

  /// Con menos que esto la tarjeta no dice nada interesante.
  static const escuchasMinimas = 5;

  /// El lunes (a las 00:00) con que empieza la semana.
  final DateTime lunes;
  final int escuchas;
  final int minutos;
  final int diasConMusica;
  final List<PuestoAnual> topCanciones;
  final List<PuestoAnual> topArtistas;

  /// Minutos de música de lunes (0) a domingo (6).
  final List<int> minutosPorDia;

  /// El día de la semana con más música (1 = lunes ... 7 = domingo), null si no hubo.
  final int? diaTop;
  final int artistasDistintos;
  final int cancionesDistintas;

  DateTime get domingo => DateTime(lunes.year, lunes.month, lunes.day + 6);
  bool get vacio => escuchas == 0;
  bool get suficiente => escuchas >= escuchasMinimas;
  int get horas => minutos ~/ 60;
  PuestoAnual? get cancionTop => topCanciones.isEmpty ? null : topCanciones.first;
  PuestoAnual? get artistaTop => topArtistas.isEmpty ? null : topArtistas.first;

  static const nombresDia = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
  static const _meses = [
    'ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'
  ];

  /// «18 – 24 nov».
  String get rango {
    final a = lunes, b = domingo;
    return a.month == b.month
        ? '${a.day} – ${b.day} ${_meses[b.month - 1]}'
        : '${a.day} ${_meses[a.month - 1]} – ${b.day} ${_meses[b.month - 1]}';
  }

  String get diaTopNombre => diaTop == null ? '' : nombresDia[diaTop! - 1];

  /// El lunes de la semana que contiene a [f].
  static DateTime lunesDe(DateTime f) => DateTime(f.year, f.month, f.day - (f.weekday - 1));

  static bool esDomingo(DateTime f) => f.weekday == DateTime.sunday;

  /// «2026-11-16»: identifica la semana por su lunes.
  static String claveSemana(DateTime lunes) => claveDia(lunes);

  /// Calcula la semana que contiene a [ahora] (si es domingo, la que acaba hoy).
  static ResumenSemanal calcular(List<Escucha> historial, {DateTime? ahora}) {
    final lunes = lunesDe(ahora ?? DateTime.now());
    final fin = DateTime(lunes.year, lunes.month, lunes.day + 7);
    final del = [
      for (final e in historial)
        if (!e.fecha.isBefore(lunes) && e.fecha.isBefore(fin)) e
    ];
    if (del.isEmpty) return ResumenSemanal(lunes: lunes, escuchas: 0, minutos: 0, diasConMusica: 0);

    var segundos = 0;
    final porCancion = <String, _Cuenta>{};
    final porArtista = <String, _Cuenta>{};
    final segPorDia = List<int>.filled(7, 0);
    for (final e in del) {
      final s = e.segundos;
      segundos += s;
      final c = porCancion.putIfAbsent(e.clave, () => _Cuenta(e.pista));
      c.escuchas++;
      c.segundos += s;
      final arts = e.artistas;
      if (arts.isNotEmpty) {
        final a = arts.first;
        final x = porArtista.putIfAbsent(a.clave, () => _Cuenta(e.pista, nombre: a.nombre));
        x.escuchas++;
        x.segundos += s;
      }
      segPorDia[e.fecha.weekday - 1] += s;
    }

    int porVeces(_Cuenta a, _Cuenta b) {
      final d = b.escuchas - a.escuchas;
      return d != 0 ? d : b.segundos - a.segundos;
    }

    PuestoAnual puesto(_Cuenta c, {required bool cancion}) {
      final p = c.pista;
      return PuestoAnual(
        nombre: cancion ? '${p['titulo'] ?? ''}' : c.nombre,
        detalle: cancion ? '${p['artista'] ?? ''}' : '',
        miniatura: '${p['miniatura'] ?? ''}',
        escuchas: c.escuchas,
        minutos: (c.segundos / 60).round(),
      );
    }

    final canciones = porCancion.values.toList()..sort(porVeces);
    final artistas = porArtista.values.toList()..sort(porVeces);
    var mejor = 0;
    for (var i = 1; i < 7; i++) {
      if (segPorDia[i] > segPorDia[mejor]) mejor = i;
    }
    return ResumenSemanal(
      lunes: lunes,
      escuchas: del.length,
      minutos: (segundos / 60).round(),
      diasConMusica: segPorDia.where((s) => s > 0).length,
      topCanciones: [for (final c in canciones.take(5)) puesto(c, cancion: true)],
      topArtistas: [for (final a in artistas.take(3)) puesto(a, cancion: false)],
      minutosPorDia: [for (final s in segPorDia) (s / 60).round()],
      diaTop: segPorDia[mejor] > 0 ? mejor + 1 : null,
      artistasDistintos: porArtista.length,
      cancionesDistintas: porCancion.length,
    );
  }

  static const _clave = 'resumen_semanal';

  /// ¿Toca mostrar la tarjeta? Solo los domingos y una vez por semana si se cerró.
  static Future<bool> toca(Coleccion c, {DateTime? ahora}) async {
    final hoy = ahora ?? DateTime.now();
    if (!esDomingo(hoy)) return false;
    try {
      final g = await c.estado(_clave);
      if (g is Map && g['cerrada'] == claveSemana(lunesDe(hoy))) return false;
    } catch (_) {}
    return true;
  }

  /// Cierra la tarjeta de esta semana (vuelve el próximo domingo).
  static Future<void> cerrar(Coleccion c, {DateTime? ahora}) async {
    try {
      await c.guardarEstado(_clave, {'cerrada': claveSemana(lunesDe(ahora ?? DateTime.now()))});
    } catch (_) {}
  }
}

class _Cuenta {
  _Cuenta(this.pista, {this.nombre = ''});
  final Json pista;
  final String nombre;
  int escuchas = 0;
  int segundos = 0;
}
