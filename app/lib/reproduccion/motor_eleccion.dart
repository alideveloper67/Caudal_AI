// Qué motor de sonido usa este teléfono.
//
// * «caudal»: libmpv (media_kit). Trae ecualizador, transiciones DJ, video y el limitador de
//   «Volumen máximo». Es el de siempre.
// * «android»: el reproductor del propio Android (ExoPlayer, vía just_audio). Sin ecualizador ni
//   video, pero no depende de nuestras librerías nativas: si mpv tumba la app en un teléfono
//   (fallo nativo, p. ej. el Honor de Android 14 de la 2.7.5), aquí la música sigue.
//
// En «automático» (lo normal) se usa el de Caudal salvo que la app se haya cerrado por un fallo
// nativo del motor hace poco: entonces este teléfono pasa al de Android hasta que llegue otra
// versión de Caudal (que puede traer el arreglo), y entonces se vuelve a probar el de Caudal.
// También pasa al de Android a mitad de una sesión si el vigía del proceso ve que mpv se come la
// memoria (vigia_proceso.dart).
//
// La decisión es lógica pura ([decidir]); [preparar] la toma al abrir con lo que diga Android.

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show MethodChannel;
import 'package:shared_preferences/shared_preferences.dart';

enum MotorSonido { caudal, android }

/// Un cierre de la app por un fallo nativo (lo que cuenta Salidas.kt).
class FalloNativo {
  const FalloNativo(this.cuando, this.texto);
  final DateTime cuando;

  /// Lo legible de la traza: hilo, mensaje de aborto, librerías.
  final String texto;

  /// ¿Fue el motor de sonido? mpv, ffmpeg, el decodificador de Android, la salida de audio o
  /// el asignador de memoria (Scudo) sin memoria: todo lo que se ve cuando cae mientras suena.
  bool get delMotor => RegExp(
        r'libmpv|libav(codec|format|util|filter)|libswresample|CodecLooper|MediaCodec|AudioTrack|'
        r'libaudioclient|Scudo|NO MEMORY|mpv/|ao/|demux',
        caseSensitive: false,
      ).hasMatch(texto);
}

class EleccionMotor {
  EleccionMotor._();

  /// El motor de esta sesión (lo lee Jugador.crear). Sin [preparar], el de Caudal.
  static MotorSonido actual = MotorSonido.caudal;

  /// Por qué se eligió (para Ajustes): '' si es el normal.
  static String motivo = '';

  static const claveAjuste = 'motor_sonido'; // automatico | caudal | android
  static const _claveRespaldo = 'motor_respaldo_version'; // versión en que se pasó a Android
  static const _canal = MethodChannel('caudal/salidas');

  /// Cuánto hacia atrás cuenta un fallo nativo.
  static const ventana = Duration(days: 3);

  /// La elección. [ajuste]: lo que eligió la persona. [respaldoEn]: la versión de Caudal en que
  /// este teléfono pasó al de Android (null si nunca). [fallos]: los cierres nativos recientes.
  @visibleForTesting
  static (MotorSonido, String, String?) decidir({
    required String ajuste,
    required String version,
    required String? respaldoEn,
    required List<FalloNativo> fallos,
    required DateTime ahora,
    bool android = true,
  }) {
    if (!android) return (MotorSonido.caudal, '', null);
    if (ajuste == 'caudal') return (MotorSonido.caudal, '', null);
    if (ajuste == 'android') return (MotorSonido.android, 'Elegido en Ajustes', respaldoEn);
    // automático
    final recientes = fallos.where((f) => f.delMotor && ahora.difference(f.cuando) < ventana).toList();
    if (respaldoEn != null && respaldoEn == version) {
      return (MotorSonido.android, 'El motor de Caudal se cerró en este teléfono', respaldoEn);
    }
    if (recientes.isNotEmpty) {
      // un fallo del motor con esta versión: al de Android hasta la próxima versión
      return (MotorSonido.android, 'El motor de Caudal se cerró en este teléfono', version);
    }
    // otra versión (o nunca falló): se vuelve a probar el de Caudal y se olvida el respaldo
    return (MotorSonido.caudal, '', null);
  }

  /// Al abrir la app, antes de crear el reproductor. Nunca lanza ni tarda más de ~2 s.
  static Future<void> preparar({required String ajuste, required String version}) async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    try {
      final p = await SharedPreferences.getInstance();
      final fallos = <FalloNativo>[];
      try {
        final lista = await _canal.invokeMethod<List>('fallosNativos').timeout(const Duration(seconds: 2));
        for (final x in lista ?? const []) {
          if (x is! Map) continue;
          final ms = (x['cuando'] as num?)?.toInt() ?? 0;
          fallos.add(FalloNativo(DateTime.fromMillisecondsSinceEpoch(ms), '${x['texto'] ?? ''}'));
        }
      } catch (_) {}
      final (motor, por, respaldo) = decidir(
        ajuste: ajuste,
        version: version,
        respaldoEn: p.getString(_claveRespaldo),
        fallos: fallos,
        ahora: DateTime.now(),
      );
      actual = motor;
      motivo = por;
      if (ajuste == 'automatico' || ajuste.isEmpty) {
        if (respaldo == null) {
          await p.remove(_claveRespaldo);
        } else {
          await p.setString(_claveRespaldo, respaldo);
        }
      }
      debugPrint('Caudal: motor de sonido = ${motor.name}${por.isEmpty ? '' : ' ($por)'}');
    } catch (e) {
      debugPrint('Caudal: no se pudo elegir el motor ($e); va el de Caudal');
    }
  }

  /// El vigía vio que mpv se come la memoria: lo que queda de sesión y hasta la próxima versión,
  /// el de Android (solo en automático).
  static Future<void> pasarARespaldo({required String version, required String por}) async {
    actual = MotorSonido.android;
    motivo = por;
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_claveRespaldo, version);
    } catch (_) {}
  }
}
