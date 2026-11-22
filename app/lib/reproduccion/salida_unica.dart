/// Una sola salida AudioTrack de mpv a la vez (Android).
///
/// El libmpv de Android (media_kit_libs_android_audio) guarda los métodos de `android.media.AudioTrack`
/// que usa por JNI en variables GLOBALES del proceso, compartidas por todos los mpv. Cuando un motor
/// cierra su salida `audiotrack` las borra (`uninit_jni` → `mp_jni_reset_jfields`), y el otro motor,
/// que sigue sonando, llama a un método borrado: Android aborta la app con
/// «JNI DETECTED ERROR IN APPLICATION: mid == null in call to CallIntMethod» en el hilo
/// `mpv/audiotrack`. Pasaba en cada fundido entre canciones: la primera sonaba bien y la segunda
/// se cortaba a los pocos segundos, justo al apagarse la que salía (2.7.5-2.7.6, Galaxy A56,
/// OnePlus CPH2781, ZTE…).
///
/// La regla: un motor solo abre `audiotrack` si ningún otro motor la tiene abierta ni la va a
/// abrir; si no, suena por `opensles`, que no usa JNI (sin el limitador del sistema mientras
/// tanto: su volumen va por mpv, como en iPhone). Así nunca hay dos AudioTrack de mpv a la vez y
/// cerrar una no puede romper otra.
library;

/// Lo que la regla necesita saber de un motor.
abstract class SalidaMotor {
  /// ¿Tiene algo cargado (sonando, en pausa o abriéndose)?
  bool get tieneSonido;

  /// ¿Tiene puesto `ao=audiotrack`? (la abrirá al sonar)
  bool get pideAudiotrack;

  /// La salida que mpv tiene abierta ahora (`current-ao`): '' si ninguna, null si no se supo.
  Future<String?> salidaAbierta();
}

/// ¿Puede [yo] abrir su salida `audiotrack` sin poner en peligro a los [otros]?
///
/// Si un motor está parado pero mpv aún no soltó su AudioTrack (el cierre va por detrás), se
/// espera hasta [espera]; pasado ese tiempo, o si no se puede saber, se responde que no (lo
/// prudente: opensles siempre funciona).
Future<bool> puedeUsarAudiotrack(SalidaMotor yo, Iterable<SalidaMotor> otros,
    {Duration espera = const Duration(milliseconds: 1500),
    Duration paso = const Duration(milliseconds: 50)}) async {
  final resto = [for (final o in otros) if (!identical(o, yo)) o];
  // alguien suena (o va a sonar) por audiotrack: no
  for (final o in resto) {
    if (o.tieneSonido && o.pideAudiotrack) return false;
  }
  final hasta = DateTime.now().add(espera);
  for (final o in resto) {
    while (true) {
      String? ao;
      try {
        ao = await o.salidaAbierta();
      } catch (_) {
        ao = null;
      }
      if (ao == null) {
        // no se pudo preguntar: solo es seguro si ese motor nunca pide audiotrack
        if (o.pideAudiotrack) return false;
        break;
      }
      if (ao != 'audiotrack') break;
      if (!DateTime.now().isBefore(hasta)) return false;
      await Future<void>.delayed(paso);
    }
  }
  return true;
}
