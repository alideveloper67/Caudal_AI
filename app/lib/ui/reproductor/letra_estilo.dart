// Estilo de la letra: cada línea se pinta en capas con el mismo TextStyle (sombra difusa, contorno
// oscuro fino y relleno), para que se lea sobre cualquier fondo, también sobre ilustraciones muy
// coloridas. La línea que suena lleva degradado con el acento, brillo y el barrido de karaoke.

import 'package:flutter/foundation.dart' show listEquals;
import 'package:flutter/material.dart';

import '../../reproduccion/reproductor.dart';
import 'letra_aspecto.dart';
import 'linea_karaoke.dart' show rellenoPorFila;

const _blancoReposo = Color(0x9EFFFFFF); // blanco al 62%
const _blancoFalta = Color(0x8CFFFFFF); // blanco al 55%: lo que aún no se canta
const _contorno = Color(0xCC0A0810);

const _sombraDifusa = [
  Shadow(color: Color(0x8C000000), blurRadius: 14, offset: Offset(0, 3)),
  Shadow(color: Color(0x59000000), blurRadius: 28, offset: Offset(0, 6)),
];

/// El mismo estilo sin color ni sombras (para dibujar capas aparte: un contorno no puede llevar color).
TextStyle _sinColor(TextStyle e) => TextStyle(
      inherit: e.inherit,
      fontFamily: e.fontFamily,
      fontFamilyFallback: e.fontFamilyFallback,
      fontSize: e.fontSize,
      fontWeight: e.fontWeight,
      fontStyle: e.fontStyle,
      letterSpacing: e.letterSpacing,
      wordSpacing: e.wordSpacing,
      textBaseline: e.textBaseline,
      height: e.height,
      leadingDistribution: e.leadingDistribution,
      locale: e.locale,
      decoration: e.decoration,
      decorationColor: e.decorationColor,
      decorationStyle: e.decorationStyle,
      decorationThickness: e.decorationThickness,
      fontFeatures: e.fontFeatures,
      fontVariations: e.fontVariations,
      overflow: e.overflow,
    );

/// Contorno oscuro fino detrás del texto (grosor 9 % del tamaño de letra).
class ContornoLetra extends StatelessWidget {
  const ContornoLetra({
    super.key,
    required this.texto,
    required this.estilo,
    this.alinear = TextAlign.start,
    this.maxLines,
    this.overflow,
  });

  final String texto;
  final TextStyle estilo;
  final TextAlign alinear;

  /// Igual que el texto de encima, para que el contorno se corte donde él.
  final int? maxLines;
  final TextOverflow? overflow;

  @override
  Widget build(BuildContext context) => ValueListenableBuilder<LetraAspecto>(
        valueListenable: LetraAspecto.actual,
        // el borde solo va con el estilo Nítida (Ajustes › Letra)
        builder: (_, a, _) => a.nitida ? _borde() : const SizedBox.shrink(),
      );

  Widget _borde() => ExcludeSemantics(
        child: Text(
          texto,
          textAlign: alinear,
          maxLines: maxLines,
          overflow: overflow,
          style: _sinColor(estilo).copyWith(
            foreground: Paint()
              ..style = PaintingStyle.stroke
              ..strokeWidth = (estilo.fontSize ?? 14) * 0.09
              ..strokeJoin = StrokeJoin.round
              ..color = _contorno,
          ),
        ),
      );
}

/// Una línea de letra en capas: sombra difusa, brillo del acento, contorno y relleno.
///
/// Si [activo], el relleno lleva degradado vertical (blanco arriba, 35 % del acento abajo) y brillo
/// del acento. Con [progreso] menor que 1 (karaoke), la parte cantada lleva el degradado y lo que
/// falta queda blanco al 55 %. Si no está activo, blanco al 62 % y sin brillo.
class TextoLetraResaltado extends StatelessWidget {
  const TextoLetraResaltado({
    super.key,
    required this.texto,
    required this.estilo,
    this.activo = false,
    this.acento,
    this.progreso = 1.0,
    this.alinear = TextAlign.start,
    this.colorReposo,
  });

  final String texto;
  final TextStyle estilo;
  final bool activo;
  final Color? acento;
  final double progreso;
  final TextAlign alinear;

  /// Color del relleno cuando no está activa (por defecto blanco al 62 %). Así cada línea conserva
  /// el tono que ya tenía; el contorno y la sombra solo añaden legibilidad.
  final Color? colorReposo;

  @override
  Widget build(BuildContext context) {
    final base = _sinColor(estilo);
    final ac = acento;
    final brillo = activo && ac != null;
    return Semantics(
      label: texto,
      child: ExcludeSemantics(
        child: LayoutBuilder(builder: (context, c) {
          final ancho = c.maxWidth.isFinite ? c.maxWidth : double.infinity;
          final capas = <Widget>[
            // 1) sombra difusa: solo las sombras, el texto va transparente
            Text(texto,
                textAlign: alinear,
                style: base.copyWith(color: Colors.transparent, shadows: _sombraDifusa)),
            // 2) brillo del acento (solo la línea activa)
            if (brillo)
              Text(texto,
                  textAlign: alinear,
                  style: base.copyWith(
                      color: Colors.transparent,
                      shadows: [Shadow(color: ac.withValues(alpha: 0.7), blurRadius: 18)])),
            // 3) contorno oscuro fino
            ContornoLetra(texto: texto, estilo: base, alinear: alinear),
          ];

          if (!activo) {
            // 4) relleno en reposo
            capas.add(Text(texto, textAlign: alinear, style: base.copyWith(color: colorReposo ?? _blancoReposo)));
          } else {
            // 4) relleno de lo que falta
            capas.add(Text(texto, textAlign: alinear, style: base.copyWith(color: _blancoFalta)));
            // 5) lo cantado: degradado, recortado por filas como el karaoke de siempre
            final tp = TextPainter(
              text: TextSpan(text: texto, style: base),
              textAlign: alinear,
              textDirection: Directionality.of(context),
              textScaler: MediaQuery.textScalerOf(context),
            )..layout(maxWidth: ancho);
            final filas = tp.computeLineMetrics();
            final relleno = rellenoPorFila([for (final m in filas) m.width], progreso);
            final rects = <Rect>[
              for (var i = 0; i < filas.length; i++)
                if (relleno[i] > 0)
                  Rect.fromLTWH(filas[i].left - 2, filas[i].baseline - filas[i].ascent,
                      (filas[i].width + 4) * relleno[i], filas[i].height),
            ];
            final degradado = [Colors.white, Color.lerp(Colors.white, ac ?? Colors.white, 0.35)!];
            capas.add(ClipPath(
              clipper: _RecorteFilas(rects),
              child: ShaderMask(
                blendMode: BlendMode.srcIn,
                shaderCallback: (rect) => LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: degradado,
                ).createShader(rect),
                child: Text(texto, textAlign: alinear, style: base.copyWith(color: Colors.white)),
              ),
            ));
          }
          return Stack(children: capas);
        }),
      ),
    );
  }
}

class _RecorteFilas extends CustomClipper<Path> {
  _RecorteFilas(this.rects);

  final List<Rect> rects;

  @override
  Path getClip(Size size) {
    final p = Path();
    for (final r in rects) {
      p.addRect(r);
    }
    return p;
  }

  @override
  bool shouldReclip(_RecorteFilas old) => !listEquals(old.rects, rects);
}

/// La línea que suena en karaoke: el mismo avance que [LineaKaraoke] (interpola entre los avisos
/// de posición), pintado con [TextoLetraResaltado].
class LineaActivaKaraoke extends StatefulWidget {
  const LineaActivaKaraoke({
    super.key,
    required this.texto,
    required this.estilo,
    required this.inicio,
    required this.fin,
    required this.r,
    this.acento,
    this.adelanto = 250,
    this.alinear = TextAlign.start,
  });

  final String texto;
  final TextStyle estilo;

  /// Milisegundos en que empieza y termina de cantarse.
  final int inicio, fin;
  final Reproductor r;
  final Color? acento;

  /// Lo mismo que adelanta la letra al cambiar de línea.
  final int adelanto;
  final TextAlign alinear;

  @override
  State<LineaActivaKaraoke> createState() => _LineaActivaKaraokeState();
}

class _LineaActivaKaraokeState extends State<LineaActivaKaraoke> with SingleTickerProviderStateMixin {
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
  void didUpdateWidget(covariant LineaActivaKaraoke old) {
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
    // si va al compás no se toca: reiniciar a cada aviso daría tirones
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
          builder: (context, _) => TextoLetraResaltado(
            texto: widget.texto,
            estilo: widget.estilo,
            activo: true,
            acento: widget.acento,
            progreso: _c.value,
            alinear: widget.alinear,
          ),
        ),
      );
}
