import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';

import 'reproductor.dart';

/// Video en ventana flotante al salir de la app (como YouTube Premium).
///
/// Android decide cuando entrar; aqui solo se le dice si esta permitido (hay
/// un video sonando) y se sabe cuando la app esta en la ventanita.
/// En iPhone no hay canal nativo: el video se apaga al salir de la app y
/// sigue el sonido (ver [Reproductor.segundoPlano]).
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
    if (defaultTargetPlatform == TargetPlatform.iOS && _vigia == null) {
      WidgetsBinding.instance.addObserver(_vigia = _Vigia());
    }
    if (!_android) return;
    r.addListener(_revisar);
    _canal.setMethodCallHandler((llamada) async {
      if (llamada.method == 'cambio') enVentana.value = llamada.arguments == true;
    });
    _revisar();
  }

  static void _revisar() {
    final r = _r;
    if (r == null) return;
    final permitir = r.modo == 'video' && r.estado == EstadoRepro.sonando;
    if (permitir == _ultimo) return;
    _ultimo = permitir;
    _canal.invokeMethod('permitir', permitir).catchError((_) => null);
  }
}

/// iPhone: avisa al reproductor cuando la app pasa a segundo plano y vuelve.
class _Vigia with WidgetsBindingObserver {
  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    final r = Pip._r;
    if (r == null) return;
    if (estado == AppLifecycleState.paused) r.segundoPlano(true);
    if (estado == AppLifecycleState.resumed) r.segundoPlano(false);
  }
}
