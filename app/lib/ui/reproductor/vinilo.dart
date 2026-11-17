import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../comunes.dart';

/// Un tocadiscos: la carátula es la etiqueta del disco, que gira a 33⅓ rpm solo
/// mientras suena (con inercia al arrancar y al frenar), y el brazo baja la
/// aguja al sonar y la levanta al pausar.
class VinilVista extends StatefulWidget {
  const VinilVista({super.key, required this.url, required this.color, required this.sonando, required this.lado});

  /// Carátula (URL o ruta local).
  final String url;

  /// Color dominante de la carátula: da el tono a la luz y a la sombra.
  final Color color;
  final bool sonando;

  /// Ancho del tocadiscos (el alto es algo menor).
  final double lado;

  @override
  State<VinilVista> createState() => _VinilVistaState();
}

class _VinilVistaState extends State<VinilVista> with SingleTickerProviderStateMixin {
  static const _segundosPorVuelta = 1.8; // 33⅓ rpm
  late final Ticker _reloj;
  Duration _antes = Duration.zero;

  /// El giro en vueltas: solo lo escucha la etiqueta (sin reconstruir el
  /// tocadiscos ni repintar el disco y el brillo, que son fijos).
  final _angulo = ValueNotifier<double>(0);
  double _vel = 0; // 0 parado · 1 velocidad de reproducción

  @override
  void initState() {
    super.initState();
    _reloj = createTicker(_cuadro);
    if (widget.sonando) _reloj.start();
  }

  @override
  void didUpdateWidget(covariant VinilVista old) {
    super.didUpdateWidget(old);
    // se enciende el reloj al sonar y se apaga solo cuando el disco ya se paró: no gasta nada oculto o pausado
    if (widget.sonando && !_reloj.isActive) {
      _antes = Duration.zero;
      _reloj.start();
    }
  }

  void _cuadro(Duration t) {
    final dt = _antes == Duration.zero ? 0.016 : (t - _antes).inMicroseconds / 1e6;
    _antes = t;
    final objetivo = widget.sonando ? 1.0 : 0.0;
    // inercia: arranca despacio y frena despacio
    _vel += (objetivo - _vel) * min(1.0, dt * (widget.sonando ? 2.2 : 1.6));
    if (!widget.sonando && _vel < 0.004) {
      _vel = 0;
      _reloj.stop();
      return;
    }
    _angulo.value = (_angulo.value + _vel * dt / _segundosPorVuelta) % 1.0;
  }

  @override
  void dispose() {
    _reloj.dispose();
    _angulo.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final w = widget.lado;
    final disco = w * 0.80;
    return SizedBox(
      width: w,
      height: w * 0.92,
      child: Stack(clipBehavior: Clip.none, children: [
        // la base del tocadiscos
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(w * 0.05),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color.lerp(widget.color, const Color(0xFF14161B), 0.82)!,
                  Color.lerp(widget.color, Colors.black, 0.92)!,
                ],
              ),
              border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
              boxShadow: [
                BoxShadow(color: Colors.black.withValues(alpha: 0.55), blurRadius: w * 0.09, offset: Offset(0, w * 0.04)),
                BoxShadow(color: widget.color.withValues(alpha: 0.18), blurRadius: w * 0.12),
              ],
            ),
          ),
        ),
        // el disco
        Positioned(
          left: w * 0.05,
          top: (w * 0.92 - disco) / 2,
          width: disco,
          height: disco,
          child: Stack(fit: StackFit.expand, children: [
            // el disco con sus surcos: fijo, se pinta una vez
            RepaintBoundary(child: CustomPaint(painter: _DiscoPintor())),
            // la etiqueta (la carátula) gira con el disco: solo se recompone
            // su capa (la imagen de la etiqueta va en su propia capa y no se repinta)
            Center(
              child: RepaintBoundary(
                child: AnimatedBuilder(
                  animation: _angulo,
                  child: RepaintBoundary(
                    child: SizedBox(
                      width: disco * 0.36,
                      height: disco * 0.36,
                      child: Stack(fit: StackFit.expand, children: [
                        ClipOval(child: Portada(url: widget.url, lado: disco * 0.36, circulo: true)),
                        // una marca en la etiqueta para que se note el giro
                        Align(
                          alignment: const Alignment(0, -0.82),
                          child: Container(
                            width: disco * 0.018,
                            height: disco * 0.018,
                            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.85), shape: BoxShape.circle),
                          ),
                        ),
                      ]),
                    ),
                  ),
                  builder: (_, etiqueta) => Transform.rotate(angle: _angulo.value * 2 * pi, child: etiqueta),
                ),
              ),
            ),
            // el agujero central y el brillo de la luz (fijos: no giran con el disco)
            RepaintBoundary(
              child: Stack(fit: StackFit.expand, children: [
                Center(
                  child: Container(
                    width: disco * 0.035,
                    height: disco * 0.035,
                    decoration: const BoxDecoration(color: Color(0xFF0B0D12), shape: BoxShape.circle),
                  ),
                ),
                CustomPaint(painter: _BrilloPintor(widget.color)),
              ]),
            ),
          ]),
        ),
        // el brazo
        Positioned.fill(
          child: TweenAnimationBuilder<double>(
            tween: Tween(end: widget.sonando ? 1.0 : 0.0),
            duration: const Duration(milliseconds: 900),
            curve: Curves.easeInOutCubic,
            builder: (_, posada, _) => CustomPaint(painter: _BrazoPintor(posada: posada)),
          ),
        ),
      ]),
    );
  }
}

/// El disco negro con sus surcos.
class _DiscoPintor extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2;
    // sombra y borde
    canvas.drawCircle(c + Offset(0, r * 0.03), r, Paint()..color = Colors.black.withValues(alpha: 0.5)..maskFilter = MaskFilter.blur(BlurStyle.normal, r * 0.05));
    canvas.drawCircle(c, r, Paint()..shader = const RadialGradient(colors: [Color(0xFF1A1C22), Color(0xFF0A0B0F)]).createShader(Rect.fromCircle(center: c, radius: r)));
    // surcos finos
    final surco = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = max(0.5, r * 0.004);
    for (var i = 0; i < 46; i++) {
      final t = i / 45;
      final rr = r * (0.40 + 0.57 * t);
      surco.color = Colors.white.withValues(alpha: i % 2 == 0 ? 0.045 : 0.025);
      canvas.drawCircle(c, rr, surco);
    }
    // las separaciones entre canciones, más marcadas
    final pausa = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = max(1.0, r * 0.012)
      ..color = Colors.black.withValues(alpha: 0.7);
    for (final t in const [0.25, 0.52, 0.78]) {
      canvas.drawCircle(c, r * (0.40 + 0.57 * t), pausa);
    }
    // el borde del disco
    canvas.drawCircle(c, r - r * 0.004, Paint()..style = PaintingStyle.stroke..strokeWidth = r * 0.012..color = Colors.white.withValues(alpha: 0.07));
  }

  @override
  bool shouldRepaint(covariant CustomPainter old) => false;
}

/// El reflejo cónico de una lámpara: dos cuñas de luz suaves que no se mueven.
class _BrilloPintor extends CustomPainter {
  _BrilloPintor(this.color);
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2;
    final luz = Color.lerp(Colors.white, color, 0.25)!;
    final sombra = Colors.transparent;
    canvas.save();
    canvas.clipPath(Path()..addOval(Rect.fromCircle(center: c, radius: r)));
    canvas.drawCircle(
      c,
      r,
      Paint()
        ..shader = SweepGradient(
          colors: [sombra, luz.withValues(alpha: 0.13), sombra, sombra, luz.withValues(alpha: 0.10), sombra, sombra],
          stops: const [0.0, 0.07, 0.16, 0.5, 0.57, 0.66, 1.0],
          transform: const GradientRotation(-pi / 5),
        ).createShader(Rect.fromCircle(center: c, radius: r)),
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _BrilloPintor old) => old.color != color;
}

/// El brazo: gira sobre su base (arriba a la derecha) y apoya la aguja sobre el disco.
class _BrazoPintor extends CustomPainter {
  _BrazoPintor({required this.posada});
  final double posada; // 0 levantado, fuera del disco · 1 apoyado

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final base = Offset(w * 0.90, size.height * 0.13);
    // ángulo: de reposo (fuera del disco) a apoyado (sobre los surcos)
    final reposo = 0.05;
    final apoyado = 0.62;
    final ang = reposo + (apoyado - reposo) * posada;
    canvas.save();
    canvas.translate(base.dx, base.dy);
    canvas.rotate(ang);
    final largo = size.height * 0.66;
    final tubo = Paint()
      ..color = const Color(0xFFD9DCE3)
      ..strokeWidth = w * 0.014
      ..strokeCap = StrokeCap.round;
    // sombra del brazo
    canvas.drawLine(Offset(w * 0.012, w * 0.02), Offset(w * 0.012, largo + w * 0.02),
        Paint()..color = Colors.black.withValues(alpha: 0.35 * (0.5 + 0.5 * posada))..strokeWidth = w * 0.016..maskFilter = MaskFilter.blur(BlurStyle.normal, w * 0.01));
    canvas.drawLine(Offset.zero, Offset(0, largo), tubo);
    // el cabezal
    final cab = RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(0, largo + w * 0.02), width: w * 0.05, height: w * 0.075), Radius.circular(w * 0.008));
    canvas.drawRRect(cab, Paint()..color = const Color(0xFF2A2E38));
    canvas.drawRRect(cab, Paint()..style = PaintingStyle.stroke..strokeWidth = 1..color = Colors.white.withValues(alpha: 0.25));
    canvas.restore();
    // el pivote
    canvas.drawCircle(base, w * 0.038, Paint()..color = const Color(0xFF3A3F4B));
    canvas.drawCircle(base, w * 0.022, Paint()..color = const Color(0xFFB9BEC9));
  }

  @override
  bool shouldRepaint(covariant _BrazoPintor old) => old.posada != posada;
}
