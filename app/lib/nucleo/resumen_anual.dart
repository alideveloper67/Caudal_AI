import 'dart:math';

import 'coleccion.dart';
import 'mixes.dart';
import 'recomendador.dart';

/// Un puesto del resumen: una canción o un artista con lo que sonó.
class PuestoAnual {
  const PuestoAnual({
    required this.nombre,
    this.detalle = '',
    this.miniatura = '',
    this.escuchas = 0,
    this.minutos = 0,
  });

  final String nombre;

  /// El artista, si el puesto es una canción.
  final String detalle;
  final String miniatura;
  final int escuchas;
  final int minutos;
}

/// «Tu año en Caudal»: todo sale de las escuchas guardadas en el teléfono, sin red.
/// La cuenta es pura (recibe la lista y devuelve un modelo) para poder probarla.
class ResumenAnual {
  const ResumenAnual({
    required this.anio,
    required this.escuchas,
    required this.minutos,
    required this.diasConMusica,
    required this.rachaMasLarga,
    this.cancionTop,
    this.artistaTop,
    this.topArtistas = const [],
    this.animos = const {},
    this.animoDominante = '',
    this.animoPorcentaje = 0,
    this.diaTop,
    this.minutosDiaTop = 0,
    this.artistasDistintos = 0,
    this.cancionesDistintas = 0,
  });

  /// Con menos que esto el resumen no dice nada interesante: se avisa con cariño.
  static const escuchasMinimas = 20;
  static const diasMinimos = 3;

  final int anio;
  final int escuchas;
  final int minutos;
  final int diasConMusica;
  final int rachaMasLarga;
  final PuestoAnual? cancionTop;
  final PuestoAnual? artistaTop;
  final List<PuestoAnual> topArtistas;

  /// Escuchas por ánimo (`triste`, `fiesta`, `romantica`).
  final Map<String, int> animos;

  /// El ánimo que más se repite ('' si el título casi nunca lo dice).
  final String animoDominante;
  final int animoPorcentaje;
  final DateTime? diaTop;
  final int minutosDiaTop;
  final int artistasDistintos;
  final int cancionesDistintas;

  bool get vacio => escuchas == 0;
  bool get suficiente => escuchas >= escuchasMinimas && diasConMusica >= diasMinimos;

  int get horas => (minutos / 60).floor();

  /// El ánimo en palabras.
  String get animoTexto => switch (animoDominante) {
        'triste' => 'melancólico',
        'fiesta' => 'fiestero',
        'romantica' => 'romántico',
        _ => '',
      };

  /// Una frase para la tarjeta del ánimo.
  String get animoFrase => switch (animoDominante) {
        'triste' => 'Este año le diste mucho espacio a las canciones tristes. A veces la música acompaña más que nadie.',
        'fiesta' => 'Tu año sonó a fiesta: ritmo, baile y buena energía.',
        'romantica' => 'Tu año fue de canciones de amor y corazón.',
        _ => 'Tu música de este año no se deja encasillar: escuchaste de todo.',
      };

  /// Calcula el resumen del año [anio] (por defecto el de [ahora]).
  static ResumenAnual calcular(List<Escucha> historial, {int? anio, DateTime? ahora}) {
    final hoy = ahora ?? DateTime.now();
    final y = anio ?? anioDelResumen(hoy);
    final del = [for (final e in historial) if (e.fecha.year == y) e];
    if (del.isEmpty) {
      return ResumenAnual(anio: y, escuchas: 0, minutos: 0, diasConMusica: 0, rachaMasLarga: 0);
    }

    var segundos = 0;
    final porCancion = <String, _Cuenta>{};
    final porArtista = <String, _Cuenta>{};
    final minutosPorDia = <int, int>{};
    final animos = <String, int>{};
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
      final dia = _numeroDeDia(e.fecha);
      minutosPorDia[dia] = (minutosPorDia[dia] ?? 0) + s;
      final animo = Rasgos.animoDe('${e.pista['titulo'] ?? ''} ${e.pista['artista'] ?? ''}');
      if (animo.isNotEmpty) animos[animo] = (animos[animo] ?? 0) + 1;
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

    int porVeces(_Cuenta a, _Cuenta b) {
      final d = b.escuchas - a.escuchas;
      return d != 0 ? d : b.segundos - a.segundos;
    }

    final canciones = porCancion.values.toList()..sort(porVeces);
    final artistas = porArtista.values.toList()..sort(porVeces);

    // el día de más escucha
    var diaMax = -1, segMax = -1;
    minutosPorDia.forEach((d, s) {
      if (s > segMax || (s == segMax && d < diaMax)) {
        diaMax = d;
        segMax = s;
      }
    });

    // el ánimo dominante, si hay suficientes títulos que lo digan
    final conAnimo = animos.values.fold<int>(0, (a, b) => a + b);
    var dominante = '';
    var pct = 0;
    if (conAnimo >= 5) {
      final mejor = animos.entries.reduce((a, b) => b.value > a.value ? b : a);
      dominante = mejor.key;
      pct = (mejor.value * 100 / conAnimo).round();
    }

    return ResumenAnual(
      anio: y,
      escuchas: del.length,
      minutos: (segundos / 60).round(),
      diasConMusica: minutosPorDia.length,
      rachaMasLarga: _rachaMasLarga(minutosPorDia.keys),
      cancionTop: canciones.isEmpty ? null : puesto(canciones.first, cancion: true),
      artistaTop: artistas.isEmpty ? null : puesto(artistas.first, cancion: false),
      topArtistas: [for (final a in artistas.take(5)) puesto(a, cancion: false)],
      animos: animos,
      animoDominante: dominante,
      animoPorcentaje: pct,
      diaTop: diaMax < 0 ? null : _deNumero(diaMax),
      minutosDiaTop: segMax < 0 ? 0 : (segMax / 60).round(),
      artistasDistintos: porArtista.length,
      cancionesDistintas: porCancion.length,
    );
  }

  // Los días se cuentan con el calendario local (no con 24 h) para que el cambio de
  // hora no parta una racha.
  static int _numeroDeDia(DateTime f) => DateTime.utc(f.year, f.month, f.day).millisecondsSinceEpoch ~/ 86400000;

  static DateTime _deNumero(int n) {
    final d = DateTime.fromMillisecondsSinceEpoch(n * 86400000, isUtc: true);
    return DateTime(d.year, d.month, d.day);
  }

  static int _rachaMasLarga(Iterable<int> dias) {
    final orden = dias.toList()..sort();
    var mejor = 0, actual = 0;
    int? previo;
    for (final d in orden) {
      actual = previo != null && d == previo + 1 ? actual + 1 : 1;
      mejor = max(mejor, actual);
      previo = d;
    }
    return mejor;
  }
}

class _Cuenta {
  _Cuenta(this.pista, {this.nombre = ''});
  final Json pista;
  final String nombre;
  int escuchas = 0;
  int segundos = 0;
}

/// El año que se resume: el de hoy, salvo en la primera quincena de enero, que todavía
/// es el resumen del año que acaba de terminar.
int anioDelResumen(DateTime ahora) => ahora.month == 1 && ahora.day <= 15 ? ahora.year - 1 : ahora.year;

/// ¿Es la época del resumen (diciembre y la primera quincena de enero)? Entonces
/// se destaca el acceso; el resto del año sigue disponible, sin avisos.
bool esTemporadaDelResumen(DateTime ahora) => ahora.month == 12 || (ahora.month == 1 && ahora.day <= 15);
