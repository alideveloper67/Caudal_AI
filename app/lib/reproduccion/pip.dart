import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';

import 'reproductor.dart';

/// Video en ventana flotante al salir de la app (como YouTube Premium), y el
/// paso a modo audio cuando no hay ventanita.
///
/// Android decide cuando entrar en la ventanita; aqui solo se le dice si esta
/// permitido (hay un video sonando) y se sabe cuando la app esta en ella.
/// Si la app pasa a segundo plano SIN ventanita (pantalla apagada, ventanita
/// cerrada o desactivada, o iPhone), el video pasa a audio y la musica sigue;
/// al volver, regresa al video (ver [Reproductor.segundoPlano]).
class Pip {
  static const _canal = MethodChannel('caudal/pip');
  static final enVentana = ValueNotifier<bool>(false);
  static Reproductor? _r;
  static bool? _ultimo;
  static _Vigia? _vigia;

  static bool get _android => defaultTargetPlatform == TargetPlatform.android;

  static void iniciar(Reproductor r) {
    _r?.removeListener(_revisar);
    _r = r;
    _ultimo = null;
    if (!kIsWeb && _vigia == null) {
      WidgetsBinding.instance.addObserver(_vigia = _Vigia());
    }
    if (!_android) return;
    r.addListener(_revisar);
    _canal.setMethodCallHandler((llamada) async {
      if (llamada.method != 'cambio') return;
      enVentana.value = llamada.arguments == true;
      if (enVentana.value) return;
      // se cerró la ventanita: si no fue para volver a la app (deslizarla
      // fuera), la música sigue en modo audio
      Future<void>.delayed(const Duration(milliseconds: 400), () {
        final ciclo = WidgetsBinding.instance.lifecycleState;
        if (!enVentana.value && ciclo != AppLifecycleState.resumed) _r?.segundoPlano(true);
      });
    });
    _revisar();
  }

  static void _revisar() {
    final r = _r;
    if (r == null) return;
    // tras pasar a audio por salir, la ventanita sigue permitida: asi al
    // volver a salir (con el video ya de vuelta) entra igual
    final permitir = (r.modo == 'video' || r.volverAVideo) && r.estado == EstadoRepro.sonando;
    if (permitir == _ultimo) return;
    _ultimo = permitir;
    _canal.invokeMethod('permitir', permitir).catchError((_) => null);
  }
}

/// Avisa al reproductor cuando la app deja de verse y cuando vuelve.
///
/// En Android, con la ventanita flotante la app queda en «inactive» (se sigue
/// viendo); apagar la pantalla o cerrar la ventanita la lleva a «hidden» y
/// «paused». Por eso se espera a esos dos y no a «inactive», que también
/// salta al bajar la cortina de notificaciones.
class _Vigia with WidgetsBindingObserver {
  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    final r = Pip._r;
    if (r == null) return;
    if (estado == AppLifecycleState.hidden || estado == AppLifecycleState.paused) {
      if (!Pip.enVentana.value) r.segundoPlano(true);
    } else if (estado == AppLifecycleState.resumed) {
      r.segundoPlano(false);
    }
  }
}
