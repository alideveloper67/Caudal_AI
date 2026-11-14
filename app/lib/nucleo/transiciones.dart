import 'dart:math';

/// Logica pura de las transiciones del reproductor (sin motores ni red), para
/// poder probarla: el fundido DJ, la deteccion de silencio y el apagado suave
/// del temporizador para dormir.

/// Un tramo que SponsorBlock marca: (inicio, fin, categoria), en segundos.
typedef Tramo = (double, double, String);

/// Hasta donde hay musica de verdad en una cancion de [duracion] segundos.
///
/// Si SponsorBlock marca un tramo "sin musica" pegado al final (aplausos,
/// silencio, una escena del videoclip...), la musica acaba donde ese tramo
/// empieza. Si no, acaba con la cancion.
double finDeMusica(List<Tramo> tramos, double duracion) {
  if (duracion <= 0) return duracion;
  var fin = duracion;
  for (final t in tramos) {
    if (t.$3 != 'music_offtopic') continue;
    // tiene que llegar al final y no comerse mas de la mitad de la cancion
    if (t.$2 >= duracion - 3 && t.$1 >= duracion * 0.5 && t.$1 < fin) fin = t.$1;
  }
  return fin;
}

/// Donde empieza la musica de verdad: tras un tramo "sin musica" que arranca
/// con la cancion (una intro hablada, un silencio largo...). Si no hay, 0.
double inicioDeMusica(List<Tramo> tramos, double duracion) {
  var inicio = 0.0;
  final tope = duracion > 0 ? min(60.0, duracion * 0.4) : 60.0;
  for (final t in tramos) {
    if (t.$3 != 'music_offtopic') continue;
    if (t.$1 <= 1.5 && t.$2 > inicio && t.$2 <= tope) inicio = t.$2;
  }
  return inicio;
}

/// Cuantos segundos dura el fundido DJ: el del ajuste de fundido si lo hay;
/// si no, una mezcla corta para que no se note el corte.
double duracionFundidoDj(int crossfade) => crossfade > 0 ? crossfade.toDouble() : 2.0;

/// Nivel RMS (dB) que deja el filtro `astats` de mpv en sus metadatos.
///
/// mpv devuelve `af-metadata/<etiqueta>` como texto (JSON); aqui solo se busca
/// la clave, sin depender del formato exacto. `-inf` es silencio total.
double? nivelDeMetadatos(String? texto) {
  if (texto == null || texto.isEmpty) return null;
  final m = RegExp(r'lavfi\.astats\.Overall\.RMS_level"?\s*[:=]\s*"?(-?inf|-?[0-9.]+(?:e-?[0-9]+)?)',
          caseSensitive: false)
      .firstMatch(texto);
  if (m == null) return null;
  final v = m.group(1)!.toLowerCase();
  if (v.endsWith('inf')) return v.startsWith('-') ? double.negativeInfinity : double.infinity;
  return double.tryParse(v);
}

/// Decide si lo que suena lleva un rato callado (de verdad, no un pasaje suave).
class DetectorSilencio {
  DetectorSilencio({this.umbralDb = -55, this.minimo = const Duration(milliseconds: 1500)});

  final double umbralDb;
  final Duration minimo;
  DateTime? _desde;

  /// Da una medida; devuelve si ya hay [minimo] seguido por debajo del umbral.
  bool medir(double? db, DateTime ahora) {
    if (db == null) return false;
    if (db > umbralDb) {
      _desde = null;
      return false;
    }
    _desde ??= ahora;
    return ahora.difference(_desde!) >= minimo;
  }

  bool get callado => _desde != null;

  void reiniciar() => _desde = null;
}

/// Segundos del final del temporizador en los que el volumen va bajando.
const segundosApagadoSuave = 30.0;

/// Cuanto del volumen queda cuando faltan [restante] segundos para apagar:
/// 1 hasta los ultimos 30 s y de ahi baja poco a poco hasta 0.
///
/// El volumen de mpv ya es cubico (suena parejo al oido), asi que una recta
/// sobre el se oye como una bajada suave y constante.
double factorApagado(double? restante) {
  if (restante == null) return 1;
  if (restante >= segundosApagadoSuave) return 1;
  if (restante <= 0) return 0;
  return restante / segundosApagadoSuave;
}
