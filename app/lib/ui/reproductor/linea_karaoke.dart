// La linea que se esta cantando: se va llenando de izquierda a derecha, como
// en un karaoke. Un controlador propio interpola entre los avisos de posicion
// del reproductor (que llegan pocas veces por segundo), asi el barrido es
// suave sin reconstruir la letra: solo se repinta esta linea.

import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:flutter/material.dart';

import '../../reproduccion/reproductor.dart';

class LineaKaraoke extends StatefulWidget {
  const LineaKaraoke({
    super.key,
    required this.texto,
    required this.estilo,
    required this.inicio,
    required this.fin,
    required this.r,
    required this.hecho,
    required this.falta,
    this.adelanto = 250,
  });

  final String texto;
  final TextStyle estilo;

  /// Milisegundos en que empieza y termina de cantarse.
  final int inicio, fin;
  final Reproductor r;

  /// Color de lo ya cantado y de lo que falta.
  final Color hecho, falta;

  /// Lo mismo que adelanta la letra al cambiar de linea.
  final int adelanto;

  @override
  State<LineaKaraoke> createState() => _LineaKaraokeState();
}

class _LineaKaraokeState extends State<LineaKaraoke> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this);

  @override
  void initState() {
    super.initState();
    widget.r.posicion.addListener(_sincronizar);
    widget.r.addListener(_sincronizar);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _sincronizar();
    });
  }

  @override
  void didUpdateWidget(covariant LineaKaraoke old) {
    super.didUpdateWidget(old);
    if (old.inicio != widget.inicio || old.fin != widget.fin) {
      _c.stop();
      _c.value = 0;
      _sincronizar();
    }
  }

  @override
  void dispose() {
    widget.r.posicion.removeListener(_sincronizar);
    widget.r.removeListener(_sincronizar);
    _c.dispose();
    super.dispose();
  }

  void _sincronizar() {
    if (!mounted) return;
    final largo = (widget.fin - widget.inicio).clamp(1, 1 << 30);
    final ms = widget.r.posicion.value.inMilliseconds + widget.adelanto;
    final f = ((ms - widget.inicio) / largo).clamp(0.0, 1.0);
    final sonando = widget.r.estado == EstadoRepro.sonando;
    if (!sonando) {
      _c.stop();
      _c.value = f;
      return;
    }
    // si va al compas no se toca: reiniciar a cada aviso daria tirones
    if (_c.isAnimating && (_c.value - f).abs() < 0.04) return;
    _c.value = f;
    final velocidad = widget.r.velocidad <= 0 ? 1.0 : widget.r.velocidad;
    final restante = ((1 - f) * largo / velocidad).round();
    if (restante > 0) _c.animateTo(1, duration: Duration(milliseconds: restante), curve: Curves.linear);
  }

  @override
  Widget build(BuildContext context) => RepaintBoundary(
        child: LayoutBuilder(
          builder: (context, c) {
            // sin ancho conocido no se puede medir fila por fila: el barrido de siempre
            if (!c.maxWidth.isFinite) return _barridoSimple();
            final direccion = Directionality.of(context);
            final resto = TextPainter(
              text: TextSpan(text: widget.texto, style: widget.estilo.copyWith(color: widget.falta)),
              textDirection: direccion,
              textWidthBasis: TextWidthBasis.longestLine,
            )..layout(maxWidth: c.maxWidth);
            final cantada = TextPainter(
              text: TextSpan(text: widget.texto, style: widget.estilo.copyWith(color: widget.hecho)),
              textDirection: direccion,
              textWidthBasis: TextWidthBasis.longestLine,
            )..layout(maxWidth: c.maxWidth);
            final filas = resto.computeLineMetrics();
            return Semantics(
              label: widget.texto,
              excludeSemantics: true,
              child: CustomPaint(
                size: Size(resto.width, resto.height),
                painter: PintorKaraoke(_c, resto, cantada, filas),
              ),
            );
          },
        ),
      );

  /// El barrido de una sola pieza (solo si no hay ancho para medir las filas).
  Widget _barridoSimple() => AnimatedBuilder(
        animation: _c,
        child: Text(widget.texto, style: widget.estilo.copyWith(color: Colors.white),
            textWidthBasis: TextWidthBasis.longestLine),
        builder: (_, hijo) {
          final f = _c.value;
          final a = (f * 1.06 - 0.03).clamp(0.0, 1.0);
          final b = (a + 0.06).clamp(0.0, 1.0);
          return ShaderMask(
            blendMode: BlendMode.srcIn,
            shaderCallback: (rect) => LinearGradient(
              colors: [widget.hecho, widget.hecho, widget.falta, widget.falta],
              stops: [0, a, b, 1],
            ).createShader(rect),
            child: hijo,
          );
        },
      );
}

/// Cuánto de cada fila está cantado cuando el avance total es [f] (0 a 1): las filas se llenan
/// una tras otra, cada una en proporción a lo que mide, no todas a la vez.
List<double> rellenoPorFila(List<double> anchos, double f) {
  final total = anchos.fold<double>(0, (a, b) => a + b);
  if (total <= 0) return List.filled(anchos.length, 0);
  var gastado = f.clamp(0.0, 1.0) * total;
  final salida = <double>[];
  for (final w in anchos) {
    if (w <= 0) {
      salida.add(gastado > 0 ? 1.0 : 0.0);
      continue;
    }
    final cuanto = gastado.clamp(0.0, w);
    salida.add(cuanto / w);
    gastado -= cuanto;
  }
  return salida;
}

@visibleForTesting
class PintorKaraoke extends CustomPainter {
  PintorKaraoke(this.reloj, this.resto, this.cantada, this.filas) : super(repaint: reloj);

  final Animation<double> reloj;
  final TextPainter resto;
  final TextPainter cantada;
  final List<ui.LineMetrics> filas;

  @override
  void paint(Canvas canvas, Size size) {
    resto.paint(canvas, Offset.zero);
    final f = reloj.value;
    if (f <= 0) return;
    final relleno = rellenoPorFila([for (final m in filas) m.width], f);
    for (var i = 0; i < filas.length; i++) {
      if (relleno[i] <= 0) continue;
      final m = filas[i];
      final arriba = m.baseline - m.ascent;
      canvas.save();
      canvas.clipRect(Rect.fromLTWH(m.left - 2, arriba, (m.width + 4) * relleno[i], m.height));
      cantada.paint(canvas, Offset.zero);
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(covariant PintorKaraoke old) =>
      old.resto != resto || old.cantada != cantada || old.filas != filas;
}
