// Saber si la app se esta viendo, y sondeos que se paran cuando no.
//
// Los sondeos (mensajes, listas compartidas, la sincronizacion...) gastaban
// bateria y datos aunque la app estuviera en segundo plano o la pantalla que
// los pedia estuviera tapada por otra. Aqui se juntan las dos cosas: la app
// en primer plano ([VidaApp.primerPlano]) y la pantalla a la vista
// ([Sondeo.visible], normalmente con el TickerMode de la ruta o la pestana).

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

/// ¿Se esta viendo la app? Con la ventanita flotante o la cortina de
/// notificaciones bajada la app queda «inactive» y cuenta como vista; con la
/// pantalla apagada o en otra app pasa a «hidden»/«paused» y deja de contar.
class VidaApp {
  VidaApp._();

  /// true mientras la app se ve. Arranca en true (las pruebas no lo tocan).
  static final ValueNotifier<bool> primerPlano = ValueNotifier<bool>(true);

  static _Vigia? _vigia;

  /// Empieza a seguir el ciclo de vida de la app (una sola vez).
  static void iniciar() {
    if (_vigia != null) return;
    final b = WidgetsBinding.instance;
    b.addObserver(_vigia = _Vigia());
    final s = b.lifecycleState;
    if (s != null) primerPlano.value = seVe(s);
  }

  /// Si con ese estado la app cuenta como vista.
  static bool seVe(AppLifecycleState s) =>
      s == AppLifecycleState.resumed || s == AppLifecycleState.inactive;
}

class _Vigia with WidgetsBindingObserver {
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    VidaApp.primerPlano.value = VidaApp.seVe(state);
  }
}

/// Un sondeo cada [cada] que solo corre con la app en primer plano y la
/// pantalla que lo pidio a la vista. Al volver a verse consulta en el acto
/// (si se paro alguna vez) y sigue con su ritmo.
class Sondeo {
  Sondeo(this.cada, this.accion);

  final Duration cada;
  final FutureOr<void> Function() accion;

  Timer? _reloj;
  bool _encendido = false;
  bool _visible = true;
  bool _seParo = false;
  bool _enMarcha = false;
  ValueListenable<TickerModeData>? _tickers;

  /// ¿Esta corriendo ahora el reloj del sondeo?
  bool get corriendo => _reloj != null;

  /// Empieza a sondear (sin consultar en el acto: eso lo hace quien lo crea).
  void iniciar() {
    if (_encendido) return;
    _encendido = true;
    VidaApp.primerPlano.addListener(_revisar);
    _revisar();
  }

  /// Si la pantalla que lo usa esta a la vista.
  bool get visible => _visible;
  set visible(bool v) {
    if (v == _visible) return;
    _visible = v;
    _revisar();
  }

  /// Sigue la visibilidad del [TickerMode] de [context] (la ruta tapada por
  /// otra o la pestana oculta lo apagan). Se llama en didChangeDependencies.
  void seguirPantalla(BuildContext context) {
    final n = TickerMode.getValuesNotifier(context);
    if (identical(n, _tickers)) return;
    _tickers?.removeListener(_alCambiarTickers);
    _tickers = n..addListener(_alCambiarTickers);
    _alCambiarTickers();
  }

  void _alCambiarTickers() => visible = _tickers?.value.enabled ?? true;

  void _revisar() {
    final debe = _encendido && _visible && VidaApp.primerPlano.value;
    if (debe && _reloj == null) {
      _reloj = Timer.periodic(cada, (_) => _disparar());
      if (_seParo) {
        _seParo = false;
        _disparar();
      }
    } else if (!debe) {
      _reloj?.cancel();
      _reloj = null;
      if (_encendido) _seParo = true;
    }
  }

  Future<void> _disparar() async {
    if (_enMarcha) return; // una consulta lenta no se apila con la siguiente
    _enMarcha = true;
    try {
      await accion();
    } catch (_) {
      // un fallo de red no para el sondeo
    } finally {
      _enMarcha = false;
    }
  }

  /// Lo para del todo (al cerrar la pantalla).
  void detener() {
    _encendido = false;
    VidaApp.primerPlano.removeListener(_revisar);
    _tickers?.removeListener(_alCambiarTickers);
    _tickers = null;
    _reloj?.cancel();
    _reloj = null;
  }
}
