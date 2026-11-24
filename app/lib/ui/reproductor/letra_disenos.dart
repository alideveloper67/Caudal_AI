// Los diseños de la letra que se pintan en capas: Degradado, Contorno, Relieve, Marcador, Oro y Retro
// (VHS). Cada uno tiene dos aspectos: lo que falta por cantar y lo ya cantado; lo cantado se recorta por
// filas con el mismo avance que el karaoke. Sin desenfoques: solo texto, trazos y degradados.

import 'package:flutter/foundation.dart' show listEquals;
import 'package:flutter/material.dart';

import '../../reproduccion/reproductor.dart';
import 'linea_karaoke.dart' show rellenoPorFila;

/// Las claves de estos diseños (las mismas en el escritorio).
const disenosEnCapas = {'degradado', 'contorno', 'relieve', 'marcador', 'oro', 'vhs'};

const _oro = [Color(0xFFFFF7D6), Color(0xFFFFD45E), Color(0xFFC98A1B), Color(0xFFFFE9A6), Color(0xFFDFA02F)];
const _oroPasos = [0.0, 0.32, 0.52, 0.66, 1.0];
const _cian = Color(0xFF21F3FF);
const _magenta = Color(0xFFFF2D95);

/// Un color siempre luminoso y vivo, para que se lea encima de cualquier fondo.
Color colorVivo(Color? c) {
  final h = HSVColor.fromColor(c ?? const Color(0xFF22D3EE));
  if (h.saturation < 0.12) return const Color(0xFF7FE7FF);
  return h.withValue(1).withSaturation(h.saturation.clamp(0.45, 0.75)).toColor();
}

/// El compañero del degradado: el mismo color, girado.
Color colorPareja(Color? c) {
  final h = HSVColor.fromColor(colorVivo(c));
  return h.withHue((h.hue + 62) % 360).withSaturation(0.5).toColor();
}

/// Texto oscuro que se lee encima de [fondo] (el resaltador).
Color _tintaSobre(Color fondo) => Color.lerp(fondo, Colors.black, 0.86)!;

/// El estilo sin color ni sombras (un trazo no puede llevar color a la vez).
TextStyle _limpio(TextStyle e) => TextStyle(
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
      fontFeatures: e.fontFeatures,
      fontVariations: e.fontVariations,
    );

/// Una línea en uno de los [disenosEnCapas]. [progreso] va de 0 (nada cantado) a 1 (todo). Con [activa]
/// en falso se pinta sobria, con [colorReposo].
class TextoDiseno extends StatelessWidget {
  const TextoDiseno({
    super.key,
    required this.diseno,
    required this.texto,
    required this.estilo,
    this.activa = true,
    this.progreso = 1,
    this.acento,
    this.alinear = TextAlign.start,
    this.colorReposo,
  });

  final String diseno;
  final String texto;
  final TextStyle estilo;
  final bool activa;
  final double progreso;
  final Color? acento;
  final TextAlign alinear;
  final Color? colorReposo;

  @override
  Widget build(BuildContext context) => Semantics(
        label: texto,
        excludeSemantics: true,
        child: LayoutBuilder(builder: (context, c) {
          final base = _limpio(DefaultTextStyle.of(context).style.merge(estilo));
          final tam = estilo.fontSize ?? 20;
          final reposo = colorReposo ?? estilo.color ?? Colors.white;
          if (!activa) return _reposo(base, tam, reposo);
          final tp = TextPainter(
            text: TextSpan(text: texto, style: base),
            textAlign: alinear,
            textDirection: Directionality.of(context),
            textScaler: MediaQuery.textScalerOf(context),
          )..layout(maxWidth: c.maxWidth);
          final filas = tp.computeLineMetrics();
          final lleno = rellenoPorFila([for (final m in filas) m.width], progreso.clamp(0.0, 1.0));
          // el ancho real de la caja del texto: con él se colocan las filas centradas
          final margen = tam * 0.2;
          final rects = <Rect>[
            for (var i = 0; i < filas.length; i++)
              if (lleno[i] > 0)
                Rect.fromLTWH(filas[i].left - margen, filas[i].baseline - filas[i].ascent,
                    (filas[i].width + margen * 2) * lleno[i], filas[i].height),
          ];
          tp.dispose();
          return _cantandose(base, tam, rects);
        }),
      );

  Text _t(TextStyle s) => Text(texto, textAlign: alinear, style: s);

  Widget _corrido(TextStyle s, double dx, double dy) =>
      Transform.translate(offset: Offset(dx, dy), child: _t(s));

  TextStyle _trazo(TextStyle base, double ancho, Color color) => base.copyWith(
        foreground: Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = ancho
          ..strokeJoin = StrokeJoin.round
          ..color = color,
      );

  Widget _degradado(TextStyle base, Gradient g) => ShaderMask(
        blendMode: BlendMode.srcIn,
        shaderCallback: (r) => g.createShader(r),
        child: _t(base.copyWith(color: Colors.white)),
      );

  Gradient get _gOro => const LinearGradient(
      begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: _oro, stops: _oroPasos, tileMode: TileMode.clamp);

  // ------------------------------------------------------------ líneas que no suenan

  Widget _reposo(TextStyle base, double tam, Color reposo) {
    // las oscuras («por venir» sobre la tarjeta de color) siguen oscuras: solo cambia el dibujo
    final claro = reposo.computeLuminance() > 0.4;
    switch (diseno) {
      case 'contorno':
        return _t(_trazo(base, (tam * 0.034).clamp(0.8, 2.0), reposo));
      case 'relieve':
        return Stack(children: [
          _corrido(base.copyWith(color: Colors.black.withValues(alpha: 0.28 * reposo.a)), tam * 0.05, tam * 0.06),
          _t(base.copyWith(color: reposo)),
        ]);
      case 'oro':
        return _t(base.copyWith(
            color: claro ? Color.lerp(reposo, const Color(0xFFFFD45E), 0.6)!.withValues(alpha: reposo.a * 0.85) : reposo));
      case 'vhs':
        return Stack(children: [
          _corrido(base.copyWith(color: _cian.withValues(alpha: 0.32 * reposo.a)), -tam * 0.03, 0),
          _corrido(base.copyWith(color: _magenta.withValues(alpha: 0.32 * reposo.a)), tam * 0.03, 0),
          _t(base.copyWith(color: reposo)),
        ]);
      default:
        return _t(base.copyWith(color: reposo));
    }
  }

  // ------------------------------------------------------------ la que suena

  Widget _cantandose(TextStyle base, double tam, List<Rect> rects) {
    final vivo = colorVivo(acento);
    Widget recorte(Widget hijo) => rects.isEmpty ? const SizedBox.shrink() : ClipPath(clipper: _Filas(rects), child: hijo);
    const falta = Color(0x99FFFFFF);
    final sombra = _corrido(base.copyWith(color: const Color(0x59000000)), tam * 0.025, tam * 0.05);
    switch (diseno) {
      case 'degradado':
        return Stack(children: [
          sombra,
          _t(base.copyWith(color: falta)),
          recorte(_degradado(
              base,
              LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: [vivo, Color.lerp(vivo, Colors.white, 0.75)!, colorPareja(acento)]))),
        ]);
      case 'contorno':
        final grueso = (tam * 0.034).clamp(0.8, 2.6);
        return Stack(children: [
          _t(_trazo(base, grueso + 1.4, const Color(0x59000000))),
          // el interior, un poco más oscuro que el fondo: así se ve hueca también en pequeño
          _t(base.copyWith(color: const Color(0x66000000))),
          _t(_trazo(base, grueso, const Color(0xE6FFFFFF))),
          recorte(Stack(children: [
            _t(_trazo(base, grueso, Colors.white)),
            _t(base.copyWith(color: Colors.white)),
          ])),
        ]);
      case 'relieve':
        final lado = Color.lerp(vivo, Colors.black, 0.42)!;
        final fondo = Color.lerp(vivo, Colors.black, 0.7)!;
        const capas = 6;
        Widget cuerpo(double alfa) => Stack(children: [
              for (var i = capas; i >= 1; i--)
                _corrido(base.copyWith(color: Color.lerp(lado, fondo, i / capas)!.withValues(alpha: alfa)),
                    tam * 0.016 * i, tam * 0.018 * i),
            ]);
        return Stack(children: [
          cuerpo(0.45),
          _t(base.copyWith(color: falta)),
          recorte(Stack(children: [
            cuerpo(1),
            _degradado(
                base,
                LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [Colors.white, Color.lerp(Colors.white, vivo, 0.38)!])),
          ])),
        ]);
      case 'marcador':
        final tinta = _tintaSobre(vivo);
        return Stack(clipBehavior: Clip.none, children: [
          Positioned.fill(child: IgnorePointer(child: CustomPaint(painter: _Resaltador(rects, vivo, tam)))),
          sombra,
          _t(base.copyWith(color: const Color(0xD9FFFFFF))),
          recorte(Stack(children: [
            Positioned.fill(child: CustomPaint(painter: _Resaltador(rects, vivo, tam))),
            _t(base.copyWith(color: tinta)),
          ])),
        ]);
      case 'oro':
        return Stack(children: [
          _corrido(base.copyWith(color: const Color(0x8C2A1600)), tam * 0.03, tam * 0.05),
          _t(_trazo(base, tam * 0.06, const Color(0x8C3A2100))),
          _t(base.copyWith(color: const Color(0x99FFE7B0))),
          recorte(Stack(children: [
            _t(_trazo(base, tam * 0.06, const Color(0xFF5A3600))),
            _degradado(base, _gOro),
          ])),
        ]);
      case 'vhs':
        final d = (tam * 0.045).clamp(1.2, 4.5);
        Widget capas(double alfa, Color cara) => Stack(children: [
              _corrido(base.copyWith(color: _cian.withValues(alpha: alfa)), -d, 0),
              _corrido(base.copyWith(color: _magenta.withValues(alpha: alfa)), d, 0),
              _t(base.copyWith(color: cara)),
            ]);
        return Stack(children: [sombra, capas(0.35, const Color(0xB3FFFFFF)), recorte(capas(0.95, Colors.white))]);
      default:
        return _t(base.copyWith(color: Colors.white));
    }
  }
}

class _Filas extends CustomClipper<Path> {
  _Filas(this.rects);
  final List<Rect> rects;

  @override
  Path getClip(Size size) {
    final p = Path();
    for (final r in rects) {
      p.addRect(Rect.fromLTRB(r.left, r.top - r.height * 0.12, r.right, r.bottom + r.height * 0.12));
    }
    return p;
  }

  @override
  bool shouldReclip(_Filas old) => !listEquals(old.rects, rects);
}

class _Resaltador extends CustomPainter {
  _Resaltador(this.rects, this.color, this.tam);
  final List<Rect> rects;
  final Color color;
  final double tam;

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()..color = color;
    for (final r in rects) {
      canvas.drawRRect(
          RRect.fromRectAndRadius(Rect.fromLTRB(r.left, r.top + r.height * 0.04, r.right, r.bottom - r.height * 0.02),
              Radius.circular(tam * 0.16)),
          p);
    }
  }

  @override
  bool shouldRepaint(_Resaltador old) => old.color != color || !listEquals(old.rects, rects);
}

/// El avance de una línea que se canta (0..1), interpolado entre los avisos de posición del reproductor.
class AvanceKaraoke extends StatefulWidget {
  const AvanceKaraoke({
    super.key,
    required this.inicio,
    required this.fin,
    required this.r,
    required this.hacer,
    this.adelanto = 250,
  });

  /// Milisegundos en que empieza y termina de cantarse.
  final int inicio, fin;
  final Reproductor r;
  final Widget Function(double progreso) hacer;
  final int adelanto;

  @override
  State<AvanceKaraoke> createState() => _AvanceKaraokeState();
}

class _AvanceKaraokeState extends State<AvanceKaraoke> with SingleTickerProviderStateMixin {
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
  void didUpdateWidget(covariant AvanceKaraoke old) {
    super.didUpdateWidget(old);
    if (old.inicio != widget.inicio || old.fin != widget.fin || old.adelanto != widget.adelanto) {
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
    final f = ((widget.r.posicion.value.inMilliseconds + widget.adelanto - widget.inicio) / largo).clamp(0.0, 1.0);
    if (widget.r.estado != EstadoRepro.sonando) {
      _c.stop();
      _c.value = f;
      return;
    }
    // si va al compás no se toca: reiniciar a cada aviso daría tirones
    if (_c.isAnimating && (_c.value - f).abs() < 0.04) return;
    _c.value = f;
    final v = widget.r.velocidad <= 0 ? 1.0 : widget.r.velocidad;
    final restante = ((1 - f) * largo / v).round();
    if (restante > 0) _c.animateTo(1, duration: Duration(milliseconds: restante), curve: Curves.linear);
  }

  @override
  Widget build(BuildContext context) =>
      RepaintBoundary(child: AnimatedBuilder(animation: _c, builder: (_, _) => widget.hacer(_c.value)));
}
