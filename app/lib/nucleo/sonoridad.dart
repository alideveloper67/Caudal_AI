import 'dart:async';
import 'dart:math';

/// Volumen máximo sin distorsión (las mismas reglas que Caudal Escritorio, `sonoridad.py`).
///
/// * Cada canción trae su sonoridad: YouTube la dice en `loudnessDb` (cuánto más fuerte o más
///   floja es que su referencia de -14 LUFS). Con eso se calcula una ganancia FIJA para toda la
///   canción (nada de subir y bajar dentro de ella: eso se oye como un «bombeo»).
/// * La ganancia lleva la canción al objetivo del nivel (Normal, Alto, Máximo) con un tope: el
///   limitador solo puede «comerse» unos pocos dB de picos (0, 3 o 6). Así las grabadas bajas suben
///   hasta sonar como las fuertes sin aplastarse.
/// * Detrás va un limitador de picos (en Android el del propio sistema, `DynamicsProcessing`; en la
///   PC el de ffmpeg con sobremuestreo). En iPhone el motor no trae limitador: la subida es menor.
class NivelVolumen {
  const NivelVolumen(this.clave, this.nombre, this.objetivo, this.presupuesto, this.subidaSinLimitador);

  final String clave;
  final String nombre;

  /// LUFS integrados a los que se lleva cada canción.
  final double objetivo;

  /// dB que el limitador puede recortar como mucho.
  final double presupuesto;

  /// Lo más que se sube donde no hay limitador (iPhone): sin él, subir más recortaría.
  final double subidaSinLimitador;
}

const nivelesVolumen = <String, NivelVolumen>{
  'normal': NivelVolumen('normal', 'Normal', -14, 0, 0),
  'alto': NivelVolumen('alto', 'Alto', -10, 3, 2),
  'maximo': NivelVolumen('maximo', 'Máximo', -8, 6, 3),
};
const nivelVolumenPorDefecto = 'alto';
const techoDbtp = -1.0;
const gananciaMaxima = 12.0;
const gananciaMinima = -12.0;

/// Sin dato de la canción: lo típico de la música publicada hoy (master fuerte, picos casi a 0).
const lufsSupuesto = -9.0;
const picoSupuesto = -0.5;

/// Referencia de YouTube para `loudnessDb` (0 = suena como -14 LUFS).
const referenciaYoutube = -14.0;

/// El súper volumen antiguo (0..4) a su nivel nuevo, y al revés (se sigue escribiendo).
const desdeSuperVolumen = {1: 'alto', 2: 'alto', 3: 'maximo', 4: 'maximo'};
const aSuperVolumen = {'no': 0, 'normal': 1, 'alto': 2, 'maximo': 4};

/// El nivel que suena, o null si no se toca el volumen de las canciones.
///
/// [guardado] es `volumen_maximo` tal como está guardado (null si nunca se eligió: ajustes de
/// una versión anterior). Apagado («no») con «Igualar el volumen» encendido equivale a Normal.
String? nivelEfectivo({String? guardado, int superVolumen = 0, bool normalizar = true,
    bool normalizarGuardado = false}) {
  if (guardado != null && nivelesVolumen.containsKey(guardado)) return guardado;
  if (guardado == null) {
    final antiguo = desdeSuperVolumen[superVolumen];
    if (antiguo != null) return antiguo;
    // quien apagó a propósito el igualar volumen no recibe el nuevo sin pedirlo
    if (normalizarGuardado && !normalizar) return null;
    return nivelVolumenPorDefecto;
  }
  return normalizar ? 'normal' : null;
}

/// LUFS integrados a partir del `loudnessDb` de YouTube.
double? lufsDeYoutube(num? loudnessDb) {
  if (loudnessDb == null) return null;
  final v = loudnessDb.toDouble();
  if (!v.isFinite || v.abs() > 40) return null;
  return referenciaYoutube + v;
}

/// dB que se le aplican a una canción (ver la explicación de arriba).
///
/// [extra]: lo que ya suman otros ajustes antes del limitador (preamplificador, margen del
/// ecualizador). [conLimitador]: false en iPhone, donde la subida queda en `subidaSinLimitador`.
double gananciaDb(String? nivel, {double? lufs, double? pico, double extra = 0, bool conLimitador = true}) {
  final n = nivelesVolumen[nivel];
  if (n == null) return 0;
  final l = (lufs == null || !lufs.isFinite) ? lufsSupuesto : lufs;
  final p = (pico == null || !pico.isFinite) ? picoSupuesto : pico;
  var g = n.objetivo - l;
  final tope = conLimitador ? (techoDbtp - p) + n.presupuesto - extra : n.subidaSinLimitador - max(0.0, extra);
  g = min(g, tope);
  return (g.clamp(gananciaMinima, gananciaMaxima) * 100).roundToDouble() / 100;
}

/// Multiplicador del volumen de mpv para [db] (su volumen es cúbico: (v/100)^3 es la ganancia).
double factorVolumenMpv(double db) => pow(10, db / 60).toDouble();

/// Filtros de ffmpeg (solo donde el motor los trae, como en la PC): ganancia fija y limitador
/// de picos verdaderos con sobremuestreo x4.
List<String> partesGananciaYLimitador(double db) => [
      if (db.abs() >= 0.05) 'volume=${db.toStringAsFixed(2)}dB',
      'aresample=192000',
      'alimiter=limit=0.871:attack=5:release=60:level=disabled',
      'aresample=48000',
    ];

/// La sonoridad de cada video ya visto (por su id), para cuando vuelva a sonar (también desde
/// el disco, donde no hay YouTube que la diga). Se guarda poco a poco con [escribir].
class RegistroSonoridad {
  RegistroSonoridad({this.leer, this.escribir, this.maximo = 3000});

  final Future<Object?> Function()? leer;
  final Future<void> Function(Map<String, double>)? escribir;
  final int maximo;

  final Map<String, double> _lufs = {};
  bool _cargado = false;
  Timer? _pronto;

  /// El que usa la app (lo conecta el reproductor con la colección).
  static RegistroSonoridad i = RegistroSonoridad();

  Future<void> cargar() async {
    if (_cargado || leer == null) return;
    _cargado = true;
    try {
      final d = await leer!();
      if (d is Map) {
        for (final e in d.entries) {
          final v = e.value;
          if (v is num && v.isFinite) _lufs.putIfAbsent('${e.key}', () => v.toDouble());
        }
      }
    } catch (_) {}
  }

  double? lufs(String? videoId) => (videoId == null || videoId.isEmpty) ? null : _lufs[videoId];

  void recordar(String videoId, double? lufs) {
    if (videoId.isEmpty || lufs == null || !lufs.isFinite) return;
    if (_lufs[videoId] == lufs) return;
    _lufs.remove(videoId);
    _lufs[videoId] = lufs;
    while (_lufs.length > maximo) {
      _lufs.remove(_lufs.keys.first);
    }
    if (escribir == null) return;
    _pronto?.cancel();
    _pronto = Timer(const Duration(seconds: 5), () {
      escribir!(Map.of(_lufs)).catchError((_) {});
    });
  }
}
