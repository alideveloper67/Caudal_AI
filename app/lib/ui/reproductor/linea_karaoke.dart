// La linea que se esta cantando: se va llenando de izquierda a derecha, como
// en un karaoke. Un controlador propio interpola entre los avisos de posicion
// del reproductor (que llegan pocas veces por segundo), asi el barrido es
// suave sin reconstruir la letra: solo se repinta esta linea.

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
        child: AnimatedBuilder(
          animation: _c,
          // el ancho de la linea mas larga: asi el barrido recorre el texto y no el hueco
          child: Text(widget.texto, style: widget.estilo.copyWith(color: Colors.white),
              textWidthBasis: TextWidthBasis.longestLine),
          builder: (_, hijo) {
            final f = _c.value;
            // un borde algo difuminado entre lo cantado y lo que falta
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
        ),
      );
}
