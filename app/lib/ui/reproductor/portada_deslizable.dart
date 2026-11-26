// La portada grande del reproductor: sigue al dedo de lado para cambiar de
// cancion, se desliza en la direccion del gesto al cambiar y con doble toque
// marca me gusta con un corazon que aparece encima.

import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';
import '../comunes.dart';
import '../plataforma.dart';
import 'animaciones.dart';

class PortadaDeslizable extends StatefulWidget {
  const PortadaDeslizable({
    super.key,
    required this.pista,
    required this.lado,
    required this.direccion,
    required this.alSiguiente,
    required this.alAnterior,
    required this.alDobleToque,
    this.alto,
  });

  final Json pista;
  final double lado;

  /// Si se da, la carátula va a sangre: con ese alto, sin esquinas ni sombra.
  final double? alto;

  /// Por donde entra la portada nueva: 1 desde la derecha (siguiente), -1 desde
  /// la izquierda (anterior).
  final int direccion;
  final VoidCallback alSiguiente;
  final VoidCallback alAnterior;
  final VoidCallback alDobleToque;

  @override
  State<PortadaDeslizable> createState() => _PortadaDeslizableState();
}

class _PortadaDeslizableState extends State<PortadaDeslizable> with SingleTickerProviderStateMixin {
  // el desplazamiento con el dedo va aparte: moverlo no reconstruye la portada
  final _dx = ValueNotifier<double>(0);
  late final AnimationController _vuelta = AnimationController(vsync: this, duration: const Duration(milliseconds: 300))
    ..addListener(() => _dx.value = _desde * (1 - Curves.easeOutCubic.transform(_vuelta.value)));
  double _desde = 0;
  final _corazon = GlobalKey<CorazonEmergenteState>();

  @override
  void dispose() {
    _vuelta.dispose();
    _dx.dispose();
    super.dispose();
  }

  void _volver() {
    _desde = _dx.value;
    if (_desde == 0) return;
    _vuelta.forward(from: 0);
  }

  void _soltar(DragEndDetails d) {
    final v = d.primaryVelocity ?? 0;
    final umbral = widget.lado * 0.3;
    if (v < -300 || (_dx.value < -umbral && v <= 300)) {
      Haptico.seleccion();
      widget.alSiguiente();
    } else if (v > 300 || (_dx.value > umbral && v >= -300)) {
      Haptico.seleccion();
      widget.alAnterior();
    }
    _volver();
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.pista;
    final url = '${p['miniatura'] ?? ''}';
    final clave = ValueKey(p['clave']);
    return GestureDetector(
      onHorizontalDragStart: (_) => _vuelta.stop(),
      // un poco de resistencia: la portada va algo por detras del dedo
      onHorizontalDragUpdate: (d) => _dx.value += d.delta.dx * 0.85,
      onHorizontalDragEnd: _soltar,
      onHorizontalDragCancel: _volver,
      onDoubleTap: () {
        _corazon.currentState?.lanzar();
        widget.alDobleToque();
      },
      child: Stack(alignment: Alignment.center, children: [
        ValueListenableBuilder<double>(
          valueListenable: _dx,
          builder: (_, dx, hijo) => Transform.translate(
            offset: Offset(dx, 0),
            // al arrastrar se inclina apenas, como una carta
            child: Transform.rotate(angle: dx / widget.lado * 0.06, child: hijo),
          ),
          // el Hero va por fuera: durante el cambio de cancion conviven dos
          // portadas y dos Hero con la misma etiqueta romperian el vuelo
          child: Hero(
            tag: etiquetaPortada,
            flightShuttleBuilder: vueloPortada(url, widget.lado),
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 380),
              transitionBuilder: deslizarEn(widget.direccion, clave),
              layoutBuilder: apilar,
              child: Container(
                key: clave,
                decoration: widget.alto != null ? null : const BoxDecoration(
                  borderRadius: BorderRadius.all(Radius.circular(8)),
                  boxShadow: [BoxShadow(color: Color(0x66000000), blurRadius: 26, offset: Offset(0, 12))],
                ),
                child: Portada(url: url, lado: widget.lado, alto: widget.alto, radio: widget.alto != null ? 0 : 8),
              ),
            ),
          ),
        ),
        CorazonEmergente(key: _corazon, tamano: widget.lado * 0.32),
      ]),
    );
  }
}
