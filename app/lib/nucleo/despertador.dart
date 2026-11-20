import 'dart:convert';
import 'dart:math';

import 'package:shared_preferences/shared_preferences.dart';

/// Despertador con música: la lógica pura (se prueba sola).
///
/// Mismas claves que Caudal Escritorio (escritorio/descargador/despertador.py) y que el lado nativo de
/// Android (Despertador.kt), que la recibe en JSON y la hace sonar con la app cerrada.
///
/// Días: lunes = 1 … domingo = 7 (como [DateTime.weekday]). Sin días, suena una sola vez.
typedef _J = Map<String, dynamic>;

/// Qué suena.
enum TipoFuente { cancion, lista, mix, meGusta, tono }

extension TipoFuenteTexto on TipoFuente {
  String get clave => switch (this) {
        TipoFuente.cancion => 'cancion',
        TipoFuente.lista => 'lista',
        TipoFuente.mix => 'mix',
        TipoFuente.meGusta => 'me_gusta',
        TipoFuente.tono => 'tono',
      };

  String get nombre => switch (this) {
        TipoFuente.cancion => 'Una canción',
        TipoFuente.lista => 'Una de tus listas',
        TipoFuente.mix => 'Un mix del día',
        TipoFuente.meGusta => 'Al azar de tus «me gusta»',
        TipoFuente.tono => 'Sonido suave de Caudal',
      };

  static TipoFuente de(String? c) =>
      TipoFuente.values.firstWhere((t) => t.clave == c, orElse: () => TipoFuente.tono);
}

class FuenteAlarma {
  const FuenteAlarma({required this.tipo, this.id = '', this.titulo = '', this.pista});

  final TipoFuente tipo;
  final String id;
  final String titulo;

  /// Solo para [TipoFuente.cancion]: lo justo de la pista para volver a sonarla.
  final _J? pista;

  static const tono = FuenteAlarma(tipo: TipoFuente.tono, id: 'tono', titulo: 'Sonido suave de Caudal');
  static const meGusta = FuenteAlarma(tipo: TipoFuente.meGusta, id: 'me_gusta', titulo: 'Tus «me gusta»');

  _J toJson() => {
        'tipo': tipo.clave,
        'id': id,
        'titulo': titulo.isEmpty ? tipo.nombre : titulo,
        if (pista != null) 'pista': pista,
      };

  factory FuenteAlarma.fromJson(Object? j) {
    if (j is! Map) return tono;
    final tipo = TipoFuenteTexto.de('${j['tipo']}');
    final p = j['pista'];
    return FuenteAlarma(
      tipo: tipo,
      id: '${j['id'] ?? ''}',
      titulo: '${j['titulo'] ?? tipo.nombre}',
      pista: p is Map ? Map<String, dynamic>.from(p) : null,
    );
  }
}

/// Lo justo de una pista para que la alarma la vuelva a sonar (sin portadas grandes ni extras).
_J pistaMinima(_J p) => {
      for (final k in const [
        'tipo', 'clave', 'video_id', 'titulo', 'artista', 'artistas', 'album', 'duracion',
        'miniatura', 'archivo', 'es_audio', 'es_video', 'descarga_id',
      ])
        if (p.containsKey(k)) k: p[k],
    };

int _acotar(Object? v, int defecto, int minimo, int maximo) {
  final n = v is num ? v.round() : (num.tryParse('$v')?.round() ?? defecto);
  return n.clamp(minimo, maximo);
}

class Alarma {
  const Alarma({
    required this.id,
    this.hora = 7,
    this.minuto = 0,
    this.dias = const {1, 2, 3, 4, 5},
    this.activa = true,
    this.etiqueta = '',
    this.fuente = FuenteAlarma.meGusta,
    this.volumen = 80,
    this.subida = 60,
    this.posponer = 9,
    this.vibrar = true,
    this.pospuestaHasta = 0,
  });

  final String id;
  final int hora;
  final int minuto;
  final Set<int> dias;
  final bool activa;
  final String etiqueta;
  final FuenteAlarma fuente;

  /// Hasta dónde sube (porcentaje del volumen de alarma del teléfono / del reproductor).
  final int volumen;

  /// Segundos que tarda en llegar a [volumen] (0 = de golpe).
  final int subida;

  /// Minutos al posponer.
  final int posponer;
  final bool vibrar;

  /// Milisegundos (época) hasta los que está pospuesta; 0 si no.
  final int pospuestaHasta;

  factory Alarma.nueva({int hora = 7, int minuto = 0, DateTime? ahora}) =>
      Alarma(id: 'a${(ahora ?? DateTime.now()).millisecondsSinceEpoch}', hora: hora, minuto: minuto);

  Alarma copia({
    int? hora, int? minuto, Set<int>? dias, bool? activa, String? etiqueta, FuenteAlarma? fuente,
    int? volumen, int? subida, int? posponer, bool? vibrar, int? pospuestaHasta,
  }) =>
      Alarma(
        id: id,
        hora: hora ?? this.hora,
        minuto: minuto ?? this.minuto,
        dias: dias ?? this.dias,
        activa: activa ?? this.activa,
        etiqueta: etiqueta ?? this.etiqueta,
        fuente: fuente ?? this.fuente,
        volumen: volumen ?? this.volumen,
        subida: subida ?? this.subida,
        posponer: posponer ?? this.posponer,
        vibrar: vibrar ?? this.vibrar,
        pospuestaHasta: pospuestaHasta ?? this.pospuestaHasta,
      );

  _J toJson() => {
        'id': id,
        'hora': hora,
        'minuto': minuto,
        'dias': (dias.toList()..sort()),
        'activa': activa,
        'etiqueta': etiqueta,
        'fuente': fuente.toJson(),
        'volumen': volumen,
        'subida': subida,
        'posponer': posponer,
        'vibrar': vibrar,
        'pospuesta_hasta': pospuestaHasta,
      };

  factory Alarma.fromJson(Map j) {
    final dias = <int>{
      for (final d in (j['dias'] is List ? j['dias'] as List : const []))
        if (int.tryParse('$d') case final n? when n >= 1 && n <= 7) n,
    };
    final pos = j['pospuesta_hasta'];
    return Alarma(
      id: '${j['id'] ?? 'a${DateTime.now().millisecondsSinceEpoch}'}',
      hora: _acotar(j['hora'], 7, 0, 23),
      minuto: _acotar(j['minuto'], 0, 0, 59),
      dias: dias,
      activa: j['activa'] != false,
      etiqueta: '${j['etiqueta'] ?? ''}'.trim(),
      fuente: FuenteAlarma.fromJson(j['fuente']),
      volumen: _acotar(j['volumen'], 80, 5, 100),
      subida: _acotar(j['subida'], 60, 0, 600),
      posponer: _acotar(j['posponer'], 9, 1, 60),
      vibrar: j['vibrar'] != false,
      // el escritorio la guarda en segundos (float); aquí y en Android, en milisegundos
      pospuestaHasta: pos is num ? (pos < 1e11 ? (pos * 1000).round() : pos.round()) : 0,
    );
  }

  String get textoHora => '${hora.toString().padLeft(2, '0')}:${minuto.toString().padLeft(2, '0')}';
}

/// La próxima vez que suena, o null si está apagada. Una pospuesta manda sobre lo demás.
DateTime? proximaVez(Alarma a, DateTime ahora) {
  if (!a.activa) return null;
  if (a.pospuestaHasta > ahora.millisecondsSinceEpoch) {
    return DateTime.fromMillisecondsSinceEpoch(a.pospuestaHasta);
  }
  for (var d = 0; d <= 7; d++) {
    // DateTime con día desbordado se recoloca solo (31 + 1 = 1 del mes siguiente) y respeta el horario de verano
    final c = DateTime(ahora.year, ahora.month, ahora.day + d, a.hora, a.minuto);
    if (!c.isAfter(ahora)) continue;
    if (a.dias.isEmpty || a.dias.contains(c.weekday)) return c;
  }
  return null;
}

/// La alarma pospuesta sus minutos desde [ahora].
Alarma posponerAlarma(Alarma a, DateTime ahora) =>
    a.copia(pospuestaHasta: ahora.add(Duration(minutes: a.posponer)).millisecondsSinceEpoch);

/// Al apagarla: se olvida lo pospuesto y la de «una vez» se apaga sola.
Alarma trasSonar(Alarma a) => a.copia(pospuestaHasta: 0, activa: a.dias.isEmpty ? false : a.activa);

/// Las que debían sonar entre [desde] y [ahora], con [margen] por si el teléfono o la app estuvo dormida.
List<Alarma> tocan(List<Alarma> alarmas, DateTime desde, DateTime ahora,
    {Duration margen = const Duration(minutes: 30)}) {
  final inicio = desde.isAfter(ahora.subtract(margen)) ? desde : ahora.subtract(margen);
  return [
    for (final a in alarmas)
      if (proximaVez(a, inicio) case final p? when p.isAfter(inicio) && !p.isAfter(ahora)) a,
  ];
}

const nombresDia = {1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb', 7: 'Dom'};
const inicialesDia = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'};

String textoDias(Set<int> dias) {
  final l = dias.toList()..sort();
  if (l.isEmpty) return 'Una vez';
  if (l.length == 7) return 'Todos los días';
  if (l.join(',') == '1,2,3,4,5') return 'Entre semana';
  if (l.join(',') == '6,7') return 'Fines de semana';
  return l.map((d) => nombresDia[d]).join(', ');
}

/// «Suena en 7 h 20 min».
String textoFalta(Duration falta) {
  final minutos = (falta.inSeconds / 60).ceil();
  if (minutos < 1) return 'Suena en menos de un minuto';
  final dias = minutos ~/ (24 * 60);
  final horas = (minutos % (24 * 60)) ~/ 60;
  final mins = minutos % 60;
  final partes = [
    if (dias > 0) '$dias ${dias == 1 ? 'día' : 'días'}',
    if (horas > 0) '$horas h',
    if (mins > 0 && dias == 0) '$mins min',
  ];
  return 'Suena en ${partes.join(' ')}';
}

/// Empieza casi en silencio (3 %).
const volumenInicial = 0.03;

/// De casi nada al volumen elegido en [subida] segundos, con curva cuadrática (al principio sube muy
/// despacio, que es cuando más asusta un salto). Igual en Kotlin y en Python.
double factorVolumen(double segundo, int subida) {
  if (subida <= 0) return 1;
  final p = (segundo / subida).clamp(0.0, 1.0);
  return volumenInicial + (1 - volumenInicial) * p * p;
}

/// Si nadie la apaga, se calla sola.
const maxSonando = Duration(minutes: 10);

// ------------------------------------------------------------ qué suena

enum MotivoPlan { elegido, descargado, respaldo, sinMusica }

class PlanSonido {
  const PlanSonido(this.pistas, this.motivo);
  final List<_J> pistas;
  final MotivoPlan motivo;
  bool get esTono => pistas.isEmpty;
}

/// Qué suena: con internet, lo elegido; sin internet, lo descargado de lo elegido; si no hay, otra
/// descargada ([respaldo], mejor primero tus «me gusta»); si tampoco, el sonido suave (pistas vacías).
PlanSonido planear(Alarma a,
    {required bool hayRed,
    required List<_J> candidatas,
    required bool Function(_J) descargada,
    List<_J> respaldo = const [],
    Random? azar}) {
  azar ??= Random();
  if (a.fuente.tipo == TipoFuente.tono) return const PlanSonido([], MotivoPlan.elegido);
  var pistas = List<_J>.of(candidatas);
  if (a.fuente.tipo == TipoFuente.meGusta) pistas.shuffle(azar);
  if (hayRed && pistas.isNotEmpty) return PlanSonido(pistas, MotivoPlan.elegido);
  final locales = pistas.where(descargada).toList();
  if (locales.isNotEmpty) return PlanSonido(locales, hayRed ? MotivoPlan.elegido : MotivoPlan.descargado);
  final reserva = respaldo.where(descargada).toList()..shuffle(azar);
  if (reserva.isNotEmpty) return PlanSonido(reserva, MotivoPlan.respaldo);
  return const PlanSonido([], MotivoPlan.sinMusica);
}

/// La pista que conviene dejar lista en el teléfono para que suene con la app cerrada (y sin
/// internet): la primera ya descargada de la fuente, si no la primera de todas. Para «me gusta», una
/// al azar (mejor de las descargadas).
_J? pistaParaPreparar(Alarma a, List<_J> candidatas, bool Function(_J) descargada, {Random? azar}) {
  if (a.fuente.tipo == TipoFuente.tono || candidatas.isEmpty) return null;
  azar ??= Random();
  final locales = candidatas.where(descargada).toList();
  if (a.fuente.tipo == TipoFuente.meGusta) {
    final de = locales.isNotEmpty ? locales : candidatas;
    return de[azar.nextInt(de.length)];
  }
  if (descargada(candidatas.first)) return candidatas.first;
  return candidatas.first;
}

// ------------------------------------------------------------ guardado

/// Las alarmas del teléfono (no van con la cuenta: suenan en este aparato).
class AlmacenAlarmas {
  static const clave = 'despertador.alarmas';

  static Future<List<Alarma>> leer() async {
    try {
      final p = await SharedPreferences.getInstance();
      return decodificar(p.getString(clave));
    } catch (_) {
      return [];
    }
  }

  static List<Alarma> decodificar(String? texto) {
    if (texto == null || texto.isEmpty) return [];
    try {
      final d = jsonDecode(texto);
      final l = d is Map ? d['alarmas'] : d;
      return [for (final a in (l is List ? l : const [])) if (a is Map) Alarma.fromJson(a)];
    } catch (_) {
      return [];
    }
  }

  static String codificar(List<Alarma> alarmas) =>
      jsonEncode({'version': 1, 'alarmas': [for (final a in alarmas) a.toJson()]});

  static Future<void> guardar(List<Alarma> alarmas) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(clave, codificar(alarmas));
  }
}
