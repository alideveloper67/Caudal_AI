import 'ritmo.dart';

/// La «vida» de las mascotas del reproductor: cuándo se duermen, a qué paso caminan según el
/// ritmo de la canción y qué gorrito llevan en las fechas especiales. Solo lógica (sin pantallas)
/// para poder probarla sin esperar dos minutos ni cambiar el reloj del teléfono.

/// Cuánto tiempo en pausa hasta que la mascota se duerme.
const Duration dormirTras = Duration(minutes: 2);

/// Lo que dura cada cuadro de caminar cuando no se conoce el ritmo (el paso de siempre).
const Duration pasoNormal = Duration(milliseconds: 180);

/// Los extremos del paso: ni frenética ni en cámara lenta, y ligera para equipos viejos
/// (como mucho ~9 cambios de cuadro por segundo).
const Duration pasoMasRapido = Duration(milliseconds: 110);
const Duration pasoMasLento = Duration(milliseconds: 240);

/// Cuánto tarda cada cuadro de caminar.
///
/// Sin ritmo conocido (o dudoso) el paso es el de siempre. Con él, una canción a 110 BPM va al
/// paso normal; más rápida, camina más rápido; más lenta, más despacio. [velocidad] es la
/// velocidad de reproducción (1 = normal).
Duration pasoDeMascota(AnalisisRitmo? ritmo, {double velocidad = 1}) {
  final v = velocidad <= 0 ? 1.0 : velocidad;
  if (ritmo == null || !ritmo.valido) return _acotar(pasoNormal.inMicroseconds / v);
  final factor = (110 / ritmo.bpm).clamp(0.55, 1.6);
  return _acotar(pasoNormal.inMicroseconds * factor / v);
}

Duration _acotar(double us) {
  final c = us.clamp(pasoMasRapido.inMicroseconds.toDouble(), pasoMasLento.inMicroseconds.toDouble());
  return Duration(microseconds: c.round());
}

/// ¿Debe estar dormida? Lleva en pausa desde [pausadaDesde] (null = no está en pausa).
bool estaDormida(DateTime? pausadaDesde, DateTime ahora) =>
    pausadaDesde != null && ahora.difference(pausadaDesde) >= dormirTras;

/// Las fechas especiales con gorrito.
enum Fiesta { ninguna, navidad, anioNuevo }

/// La fiesta de [dia]: Navidad del 20 al 26 de diciembre y Año Nuevo del 27 de diciembre al 2 de enero.
Fiesta fiestaDe(DateTime dia) {
  final m = dia.month, d = dia.day;
  if (m == 12) {
    if (d >= 27) return Fiesta.anioNuevo;
    if (d >= 20) return Fiesta.navidad;
  }
  if (m == 1 && d <= 2) return Fiesta.anioNuevo;
  return Fiesta.ninguna;
}
