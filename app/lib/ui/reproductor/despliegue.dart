// El despliegue del reproductor: lo que sigue se jala hacia arriba y ocupa la pantalla, con una cabecera
// pequeña fija arriba para no perder de vista lo que suena. Todo es el mismo desplazamiento (no hay dos
// listas peleando por el dedo): la física solo decide dónde se queda al soltar.
import 'package:flutter/gestures.dart' show kTouchSlop;
import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';
import '../../reproduccion/reproductor.dart';
import '../comunes.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';
import 'animaciones.dart';

/// Al soltar a medio camino se queda recogido (0) o desplegado ([pliegue]), nunca en medio. Un impulso
/// desde lo hondo de la lista se para en el principio de la lista, no cae hasta la carátula.
class FisicaDespliegue extends ScrollPhysics {
  const FisicaDespliegue({required this.pliegue, super.parent});

  /// Dónde queda desplegado (0: no se sabe todavía).
  final double Function() pliegue;

  @override
  FisicaDespliegue applyTo(ScrollPhysics? ancestor) => FisicaDespliegue(pliegue: pliegue, parent: buildParent(ancestor));

  @override
  Simulation? createBallisticSimulation(ScrollMetrics position, double velocity) {
    final p = pliegue().clamp(0.0, position.maxScrollExtent);
    final x = position.pixels;
    if (p < 40 || x <= 0 || position.outOfRange) return super.createBallisticSimulation(position, velocity);
    Simulation a(double destino) => ScrollSpringSimulation(spring, x, destino, velocity, tolerance: toleranceFor(position));
    if (x < p - 0.5) {
      if (velocity.abs() > 220) return a(velocity > 0 ? p : 0);
      return a(x > p / 2 ? p : 0);
    }
    if (velocity < 0) {
      final libre = super.createBallisticSimulation(position, velocity);
      final fin = libre?.x(double.infinity) ?? x;
      if (fin < p) return a(p);
      return libre;
    }
    return super.createBallisticSimulation(position, velocity);
  }
}

/// El asa: se toca o se jala.
class AsaDespliegue extends StatelessWidget {
  const AsaDespliegue({super.key, required this.alPulsar});
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: 'Desplegar lo que sigue',
        excludeSemantics: true,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () {
            Haptico.seleccion();
            alPulsar();
          },
          child: SizedBox(
            height: 22,
            child: Center(
              child: Container(
                width: 40,
                height: 4.5,
                decoration: BoxDecoration(color: const Color(0x66FFFFFF), borderRadius: BorderRadius.circular(3)),
              ),
            ),
          ),
        ),
      );
}

/// Lo que suena, en pequeño y fijo arriba mientras se mira la lista.
class CabeceraCompacta extends StatelessWidget {
  const CabeceraCompacta({
    super.key,
    required this.r,
    required this.pista,
    required this.color,
    required this.arriba,
    required this.alBajar,
    required this.alSiguiente,
  });

  /// Sin contar la barra de estado.
  static const alto = 68.0;

  final Reproductor r;
  final Json pista;
  final Color color;

  /// Lo que ocupa la barra de estado.
  final double arriba;
  final VoidCallback alBajar, alSiguiente;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final clave = '${pista['clave']}';
    var bajado = 0.0;
    return Semantics(
      container: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: alBajar,
        onVerticalDragStart: (_) => bajado = 0,
        onVerticalDragUpdate: (d) => bajado += d.delta.dy,
        onVerticalDragEnd: (d) {
          if (bajado > kTouchSlop || (d.primaryVelocity ?? 0) > 200) alBajar();
        },
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: color,
            boxShadow: const [BoxShadow(color: Color(0x66000000), blurRadius: 14, offset: Offset(0, 3))],
          ),
          child: SizedBox(
            height: arriba + alto,
            child: Stack(children: [
              Padding(
                padding: EdgeInsets.only(top: arriba, left: 16, right: 4),
                child: Row(children: [
                  Portada(url: '${pista['miniatura'] ?? ''}', lado: 48, radio: 6),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${pista['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, height: 1.2)),
                        Text('${pista['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 13, color: Color(0xCCFFFFFF), height: 1.3)),
                      ],
                    ),
                  ),
                  CorazonAnimado(gusta: s.coleccion.meGusta(clave), alPulsar: () => s.alternarMeGusta(pista)),
                  SizedBox(
                    width: 48,
                    height: 48,
                    child: r.estado == EstadoRepro.cargando
                        ? const Padding(padding: EdgeInsets.all(13), child: CircularProgressIndicator(strokeWidth: 2.4, color: C.texto))
                        : IconButton(
                            tooltip: 'Reproducir o pausar',
                            icon: IconoPlayPausa(sonando: r.estado == EstadoRepro.sonando, tamano: 30),
                            onPressed: () {
                              Haptico.toque();
                              r.alternar();
                            },
                          ),
                  ),
                  IconButton(
                    tooltip: 'Siguiente',
                    iconSize: 30,
                    icon: const Icon(Icons.skip_next_rounded),
                    onPressed: () {
                      Haptico.seleccion();
                      alSiguiente();
                    },
                  ),
                ]),
              ),
              Positioned(
                left: 0,
                right: 0,
                bottom: 0,
                child: RepaintBoundary(
                  child: ValueListenableBuilder<Duration>(
                    valueListenable: r.posicion,
                    builder: (_, pos, _) {
                      final d = r.duracion.value.inMilliseconds;
                      return LinearProgressIndicator(
                        value: d > 0 ? (pos.inMilliseconds / d).clamp(0.0, 1.0) : 0,
                        minHeight: 2.5,
                        backgroundColor: const Color(0x33FFFFFF),
                        valueColor: const AlwaysStoppedAnimation(C.texto),
                      );
                    },
                  ),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}
