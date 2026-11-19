import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../nucleo/cosmeticos.dart';

/// Cómo se ve un marco de avatar.
class EstiloMarco {
  const EstiloMarco(this.nombre, this.colores, {this.segundos = 6, this.pulso = false});

  final String nombre;

  /// Los colores del aro (se unen en círculo; el último repite el primero).
  final List<Color> colores;

  /// Lo que tarda en dar una vuelta.
  final double segundos;

  /// Además del giro, el aro «respira» (se aclara y se oscurece).
  final bool pulso;
}

/// Los marcos que puede elegir un donador. Las claves son las de [Cosmeticos.marcos].
const Map<String, EstiloMarco> marcosAvatar = {
  'aurora': EstiloMarco('Aurora', [Color(0xFF7CFFCB), Color(0xFF4DA8FF), Color(0xFFB66DFF), Color(0xFF7CFFCB)], segundos: 7),
  'fuego': EstiloMarco('Fuego', [Color(0xFFFF3D00), Color(0xFFFF9100), Color(0xFFFFD54F), Color(0xFFFF3D00)], segundos: 4, pulso: true),
  'oro': EstiloMarco('Oro', [Color(0xFFF5C542), Color(0xFFFFF1B0), Color(0xFFC98F12), Color(0xFFF5C542)], segundos: 9),
  'neon': EstiloMarco('Neón', [Color(0xFF22D3EE), Color(0xFFFF2DAA), Color(0xFF22D3EE)], segundos: 5, pulso: true),
  'hielo': EstiloMarco('Hielo', [Color(0xFFBFEFFF), Color(0xFF6EC6FF), Color(0xFFFFFFFF), Color(0xFFBFEFFF)], segundos: 8),
  'arcoiris': EstiloMarco('Arcoíris', [
    Color(0xFFFF3B3B), Color(0xFFFFC53B), Color(0xFF4BE06B), Color(0xFF35D0FF), Color(0xFF6A5CFF), Color(0xFFFF4DD2), Color(0xFFFF3B3B)
  ], segundos: 4),
  'galaxia': EstiloMarco('Galaxia', [Color(0xFF2B1B6B), Color(0xFF8A5CFF), Color(0xFFFF6EC7), Color(0xFF2B1B6B)], segundos: 10),
};

/// Un aro de color alrededor de un avatar.
///
/// El tamaño total es siempre `radio * 2`: el avatar de dentro se hace un poco más pequeño
/// ([radioInterno]), así que poner un marco no mueve nada de lo que tiene alrededor. Sin marco
/// (o con «ninguno») devuelve el avatar tal cual.
///
/// Es barato a propósito: un solo controlador, un solo trazo con degradado por cuadro, sin
/// `saveLayer` ni desenfoques. [animar] solo se activa donde hay UN avatar a la vista (el perfil);
/// en listas se deja quieto. Tampoco se anima con «Quitar animaciones» del teléfono, ni cuando
/// la pestaña no se ve (lo corta `TickerMode`).
class AvatarMarco extends StatefulWidget {
  const AvatarMarco({
    super.key,
    required this.marco,
    required this.radio,
    required this.child,
    this.animar = false,
  });

  final String marco;

  /// El radio total, aro incluido.
  final double radio;

  /// El avatar, ya hecho con [radioInterno] de radio.
  final Widget child;
  final bool animar;

  /// ¿Esta clave dibuja algo?
  static bool tiene(String marco) => marcosAvatar.containsKey(marco);

  static double grosorDe(double radio) => math.max(2.0, radio * 0.09);
  static double huecoDe(double radio) => math.max(1.5, radio * 0.05);

  /// El radio que debe tener el avatar de dentro para que todo mida [radio].
  static double radioInterno(String marco, double radio) =>
      tiene(marco) ? math.max(4.0, radio - grosorDe(radio) - huecoDe(radio)) : radio;

  @override
  State<AvatarMarco> createState() => _AvatarMarcoState();
}

class _AvatarMarcoState extends State<AvatarMarco> with SingleTickerProviderStateMixin {
  AnimationController? _c;

  EstiloMarco? get _estilo => marcosAvatar[widget.marco];

  void _ajustarAnimacion() {
    final e = _estilo;
    final quiere = widget.animar && e != null && !MediaQuery.disableAnimationsOf(context);
    if (quiere) {
      _c ??= AnimationController(vsync: this, duration: Duration(milliseconds: (e.segundos * 1000).round()));
      _c!.duration = Duration(milliseconds: (e.segundos * 1000).round());
      if (!_c!.isAnimating) _c!.repeat();
    } else {
      _c?.stop();
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _ajustarAnimacion();
  }

  @override
  void didUpdateWidget(covariant AvatarMarco old) {
    super.didUpdateWidget(old);
    if (old.animar != widget.animar || old.marco != widget.marco) _ajustarAnimacion();
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final e = _estilo;
    if (e == null) return widget.child;
    final lado = widget.radio * 2;
    final grosor = AvatarMarco.grosorDe(widget.radio);
    final aro = CustomPaint(
      size: Size.square(lado),
      painter: _PintorAro(e, grosor, _c),
    );
    return Semantics(
      label: 'Marco ${e.nombre}',
      child: SizedBox(
        width: lado,
        height: lado,
        child: Stack(alignment: Alignment.center, children: [
          // el aro se repinta solo (RepaintBoundary): el avatar de dentro no se toca
          Positioned.fill(child: RepaintBoundary(child: aro)),
          widget.child,
        ]),
      ),
    );
  }
}

class _PintorAro extends CustomPainter {
  _PintorAro(this.estilo, this.grosor, this.anim) : super(repaint: anim);

  final EstiloMarco estilo;
  final double grosor;
  final Animation<double>? anim;

  @override
  void paint(Canvas canvas, Size size) {
    final t = anim?.value ?? 0.12;
    final rect = Offset.zero & size;
    final radio = (size.shortestSide - grosor) / 2;
    final p = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = grosor
      ..isAntiAlias = true
      ..shader = SweepGradient(colors: estilo.colores, transform: GradientRotation(t * 2 * math.pi))
          .createShader(rect);
    if (estilo.pulso) {
      // «respira»: entre 70 % y 100 % de opacidad
      final a = 0.85 + 0.15 * math.sin(t * 2 * math.pi * 2);
      p.color = Color.fromRGBO(0, 0, 0, a.clamp(0.0, 1.0));
    }
    canvas.drawCircle(rect.center, radio, p);
  }

  @override
  bool shouldRepaint(_PintorAro o) => o.estilo != estilo || o.grosor != grosor;
}

// ============================================================ nombre con efecto

/// Los efectos del nombre. Las claves son las de [Cosmeticos.efectosNombre].
const Map<String, String> efectosNombreEtiquetas = {
  'brillo': 'Brillo',
  'degradado': 'Degradado',
  'arcoiris': 'Arcoíris',
  'neon': 'Neón',
};

/// Un nombre con efecto: brillo que pasa, degradado, arcoíris o neón. Sin efecto es un `Text` normal.
///
/// Igual que el marco, solo se mueve con [animar] (un nombre a la vista, no en listas), nunca con
/// «Quitar animaciones» y se detiene cuando la pantalla no se ve.
class NombreEfecto extends StatefulWidget {
  const NombreEfecto(
    this.texto, {
    super.key,
    required this.efecto,
    this.estilo,
    this.maxLines = 1,
    this.overflow = TextOverflow.ellipsis,
    this.textAlign,
    this.animar = false,
  });

  final String texto;
  final String efecto;
  final TextStyle? estilo;
  final int? maxLines;
  final TextOverflow overflow;
  final TextAlign? textAlign;
  final bool animar;

  @override
  State<NombreEfecto> createState() => _NombreEfectoState();
}

class _DeslizaDegradado extends GradientTransform {
  const _DeslizaDegradado(this.t);
  final double t;

  @override
  Matrix4? transform(Rect bounds, {TextDirection? textDirection}) =>
      Matrix4.translationValues(bounds.width * (t * 2 - 1), 0, 0);
}

class _NombreEfectoState extends State<NombreEfecto> with SingleTickerProviderStateMixin {
  AnimationController? _c;

  bool get _seMueve => widget.animar && (widget.efecto == 'brillo' || widget.efecto == 'arcoiris');

  void _ajustar() {
    if (_seMueve && !MediaQuery.disableAnimationsOf(context)) {
      _c ??= AnimationController(vsync: this, duration: const Duration(milliseconds: 3200));
      if (!_c!.isAnimating) _c!.repeat();
    } else {
      _c?.stop();
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _ajustar();
  }

  @override
  void didUpdateWidget(covariant NombreEfecto old) {
    super.didUpdateWidget(old);
    if (old.animar != widget.animar || old.efecto != widget.efecto) _ajustar();
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  Text _texto(TextStyle? estilo) => Text(widget.texto,
      maxLines: widget.maxLines, overflow: widget.overflow, textAlign: widget.textAlign, style: estilo);

  Gradient _degradado(double t) {
    switch (widget.efecto) {
      case 'brillo':
        // un destello claro que cruza el nombre
        return LinearGradient(
          colors: const [Color(0xFFE6ECF7), Color(0xFFFFFFFF), Color(0xFFFFE08A), Color(0xFFFFFFFF), Color(0xFFE6ECF7)],
          stops: const [0.0, 0.35, 0.5, 0.65, 1.0],
          transform: _DeslizaDegradado(t),
        );
      case 'arcoiris':
        return LinearGradient(
          colors: const [
            Color(0xFFFF6B6B), Color(0xFFFFD166), Color(0xFF6BE675), Color(0xFF4CC9F0), Color(0xFFA78BFA), Color(0xFFFF6B6B)
          ],
          tileMode: TileMode.repeated,
          transform: GradientRotation(0),
        );
      default:
        return const LinearGradient(colors: [Color(0xFF22D3EE), Color(0xFF8B6CFF), Color(0xFFFF5C8A)]);
    }
  }

  @override
  Widget build(BuildContext context) {
    final base = widget.estilo;
    switch (widget.efecto) {
      case 'neon':
        return _texto((base ?? const TextStyle()).copyWith(
          color: const Color(0xFFD6F7FF),
          shadows: const [
            Shadow(color: Color(0xFF22D3EE), blurRadius: 6),
            Shadow(color: Color(0x8022D3EE), blurRadius: 14),
          ],
        ));
      case 'brillo':
      case 'degradado':
      case 'arcoiris':
        final blanco = (base ?? const TextStyle()).copyWith(color: Colors.white);
        Widget mascara(double t) => ShaderMask(
              blendMode: BlendMode.srcIn,
              shaderCallback: (r) {
                final g = _degradado(t);
                if (widget.efecto == 'arcoiris') {
                  // el arcoíris se desplaza: el gradiente se ensancha al doble y se corre
                  final ancho = math.max(r.width, 1.0);
                  return g.createShader(Rect.fromLTWH(-t * ancho, r.top, ancho, r.height));
                }
                return g.createShader(r);
              },
              child: _texto(blanco),
            );
        final c = _c;
        if (c == null || !c.isAnimating) return mascara(0.5);
        return AnimatedBuilder(animation: c, builder: (_, _) => mascara(c.value));
      default:
        return _texto(base);
    }
  }
}
