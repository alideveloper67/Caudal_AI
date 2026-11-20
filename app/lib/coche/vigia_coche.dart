import 'dart:async';

import 'package:flutter/widgets.dart';

import 'abrir_modo_coche.dart';
import 'coche_bluetooth.dart';

/// Envuelve la pantalla principal y abre el modo coche solo al conectar el
/// Bluetooth del coche (si la persona lo pidió en Ajustes > Modo coche).
///
/// Tiene que ir debajo del navegador principal: el Armazon es el sitio.
class VigiaCoche extends StatefulWidget {
  const VigiaCoche({super.key, required this.child, this.fuente, this.abrir, this.decisor});

  final Widget child;

  /// El Bluetooth (en las pruebas, uno de mentira).
  final FuenteBluetooth? fuente;

  /// Qué hacer para abrirlo (por defecto, [AbrirModoCoche.abrir]).
  final Future<void> Function(BuildContext context)? abrir;

  final DecisorCoche? decisor;

  @override
  State<VigiaCoche> createState() => _VigiaCocheState();
}

class _VigiaCocheState extends State<VigiaCoche> with WidgetsBindingObserver {
  late final FuenteBluetooth _bt = widget.fuente ?? const BluetoothNativo();
  late final DecisorCoche _decisor = widget.decisor ?? DecisorCoche();
  PreferenciasCoche _prefs = PreferenciasCoche();
  StreamSubscription<EventoBt>? _sub;
  bool _aLaVista = true;

  @override
  void initState() {
    super.initState();
    if (!_bt.disponible) return;
    final estado = WidgetsBinding.instance.lifecycleState;
    _aLaVista = estado == null || estado == AppLifecycleState.resumed;
    WidgetsBinding.instance.addObserver(this);
    PreferenciasCoche.cambios.addListener(_recargar);
    _sub = _bt.cambios.listen(_alEvento);
    unawaited(_arrancar());
  }

  Future<void> _arrancar() async {
    _prefs = await PreferenciasCoche.cargar();
    if (!mounted || !_prefs.abrirSolo || _prefs.dispositivos.isEmpty) return;
    // el coche ya estaba conectado al abrir Caudal (o se abrió desde el aviso)
    for (final d in await _bt.conectados()) {
      if (!mounted) return;
      _alEvento(EventoBt(conectado: true, dispositivo: d));
    }
  }

  Future<void> _recargar() async {
    final antes = _prefs.abrirSolo;
    _prefs = await PreferenciasCoche.cargar();
    // recién activado con el coche ya conectado: que cuente para la próxima conexión,
    // no abrir de golpe encima de la pantalla de ajustes
    if (!antes && _prefs.abrirSolo) {
      for (final d in await _bt.conectados()) {
        _decisor.marcarAbierto(d.direccion);
      }
    }
  }

  void _alEvento(EventoBt e) {
    if (!mounted) return;
    if (!e.conectado) {
      _decisor.alDesconectar(e.dispositivo.direccion);
      return;
    }
    final d = _decisor.alConectar(e.dispositivo.direccion, _prefs, aLaVista: _aLaVista);
    if (d == DecisionCoche.abrirYa) _abrir();
  }

  void _abrir() {
    if (!mounted || AbrirModoCoche.abierto) return;
    final abrir = widget.abrir ?? AbrirModoCoche.abrir;
    unawaited(abrir(context));
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _aLaVista = state == AppLifecycleState.resumed;
    if (_aLaVista && _decisor.alVolver(_prefs)) _abrir();
  }

  @override
  void dispose() {
    _sub?.cancel();
    PreferenciasCoche.cambios.removeListener(_recargar);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
