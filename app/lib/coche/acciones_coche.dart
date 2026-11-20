import 'package:audio_service/audio_service.dart';

import '../nucleo/coleccion.dart';

/// Botones de más en la pantalla del coche (Android Auto) y en la notificación:
/// «Me gusta» (con el corazón lleno si ya te gusta) y «Aleatorio».
///
/// `ServicioAudio` los añade a sus controles y le pasa aquí lo que llegue por
/// `customAction` (ver el parche de `servicio_audio.dart` en el informe).
class AccionesCoche {
  AccionesCoche._();

  static const meGusta = 'caudal_megusta';
  static const aleatorio = 'caudal_aleatorio';

  /// Iconos en `android/app/src/main/res/drawable/`.
  static const iconoMeGusta = 'drawable/ic_coche_megusta';
  static const iconoMeGustaLleno = 'drawable/ic_coche_megusta_lleno';
  static const iconoAleatorio = 'drawable/ic_coche_aleatorio';
  static const iconoAleatorioPuesto = 'drawable/ic_coche_aleatorio_puesto';

  static List<MediaControl> controles({required bool hayPista, required bool gusta, required bool enAleatorio}) => [
        if (hayPista)
          MediaControl.custom(
            androidIcon: gusta ? iconoMeGustaLleno : iconoMeGusta,
            label: gusta ? 'Quitar de me gusta' : 'Me gusta',
            name: meGusta,
          ),
        MediaControl.custom(
          androidIcon: enAleatorio ? iconoAleatorioPuesto : iconoAleatorio,
          label: enAleatorio ? 'Aleatorio activado' : 'Aleatorio desactivado',
          name: aleatorio,
        ),
      ];

  /// Lo que cambia los botones: va en la firma del freno de la notificación
  /// para que se vuelvan a publicar al tocar el corazón o el aleatorio.
  static String firma({required bool gusta, required bool enAleatorio}) => '${gusta ? 'g' : '-'}${enAleatorio ? 'a' : '-'}';

  /// Atiende un botón propio. Devuelve `false` si [nombre] no es de los de aquí.
  static Future<bool> atender(
    String nombre, {
    required Json? actual,
    required Future<bool> Function(Json pista) alternarMeGusta,
    required Future<bool> Function() alternarAleatorio,
  }) async {
    switch (nombre) {
      case meGusta:
        if (actual != null) await alternarMeGusta(Map<String, dynamic>.from(actual));
        return true;
      case aleatorio:
        await alternarAleatorio();
        return true;
    }
    return false;
  }
}
