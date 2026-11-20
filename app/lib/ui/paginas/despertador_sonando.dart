import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/despertador_control.dart';
import '../tema.dart';

/// La pantalla de «está sonando» con la app abierta (iPhone y lo que no es Android; en Android la
/// pone el sistema sobre el bloqueo: DespertadorActivity.kt).
class DespertadorSonandoPagina extends StatefulWidget {
  const DespertadorSonandoPagina({super.key, required this.control});
  final ControlDespertador control;

  @override
  State<DespertadorSonandoPagina> createState() => _DespertadorSonandoPaginaState();
}

class _DespertadorSonandoPaginaState extends State<DespertadorSonandoPagina> {
  Timer? _reloj;

  @override
  void initState() {
    super.initState();
    _reloj = Timer.periodic(const Duration(seconds: 5), (_) {
      if (mounted) setState(() {});
    });
    widget.control.sonando.addListener(_alCambiar);
  }

  @override
  void dispose() {
    _reloj?.cancel();
    widget.control.sonando.removeListener(_alCambiar);
    super.dispose();
  }

  void _alCambiar() {
    // se apagó o pospuso desde otro sitio (o se calló sola): la pantalla se va
    if (widget.control.sonando.value == null && mounted) Navigator.of(context).maybePop();
  }

  String _dos(int n) => n.toString().padLeft(2, '0');

  @override
  Widget build(BuildContext context) {
    final s = widget.control.sonando.value;
    final ahora = DateTime.now();
    return PopScope(
      canPop: s == null,
      child: Scaffold(
        backgroundColor: C.fondo,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(28, 40, 28, 28),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Spacer(),
              Icon(Icons.alarm_rounded, size: 46, color: C.acento),
              const SizedBox(height: 12),
              Text('${_dos(ahora.hour)}:${_dos(ahora.minute)}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 84, fontWeight: FontWeight.w900, letterSpacing: -3)),
              Text(s == null || s.alarma.etiqueta.isEmpty ? 'Buenos días' : s.alarma.etiqueta,
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: C.acento)),
              const SizedBox(height: 8),
              Text(s?.titulo ?? '', textAlign: TextAlign.center, style: estiloSecundario),
              const Spacer(),
              SizedBox(
                height: 54,
                child: OutlinedButton(
                  onPressed: s == null ? null : widget.control.posponer,
                  child: Text('Posponer ${s?.alarma.posponer ?? 9} min', style: const TextStyle(fontSize: 17)),
                ),
              ),
              const SizedBox(height: 10),
              SizedBox(
                height: 54,
                child: FilledButton(
                  onPressed: s == null ? null : () => widget.control.apagar(),
                  child: const Text('Apagar', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                ),
              ),
              if (s != null && !s.tono)
                TextButton(
                  onPressed: () => widget.control.apagar(seguir: true),
                  child: const Text('Apagar y seguir escuchando'),
                ),
            ]),
          ),
        ),
      ),
    );
  }
}

/// Vigila el despertador y, cuando suena con la app abierta, pone su pantalla encima de todo.
class VigiaDespertador {
  VigiaDespertador(this.control, this.navegador) {
    control.sonando.addListener(_alCambiar);
  }

  final ControlDespertador control;
  final GlobalKey<NavigatorState> navegador;
  bool _abierta = false;

  void _alCambiar() {
    if (control.sonando.value == null || _abierta) return;
    final nav = navegador.currentState;
    if (nav == null) return;
    _abierta = true;
    unawaited(nav
        .push(MaterialPageRoute<void>(fullscreenDialog: true, builder: (_) => DespertadorSonandoPagina(control: control)))
        .whenComplete(() => _abierta = false));
  }

  void soltar() => control.sonando.removeListener(_alCambiar);
}
