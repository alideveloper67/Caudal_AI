// Los estilos de la portada del reproductor grande (donadores): Casete, Neón y Flotante.
// (El Clásico es la portada deslizable de siempre y el Vinilo vive en vinilo.dart.)
//
// Pensados para no gastar nada de más:
//  - lo que se mueve va en su propia capa (RepaintBoundary) y se anima con transformaciones
//    u opacidad, nunca repintando sombras difuminadas a cada fotograma;
//  - los relojes solo corren mientras suena y se ven;
//  - con «quitar animaciones» o el modo ligero (MediaQuery.disableAnimations) todo queda
//    quieto, sin dejar de verse bien.

import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../../nucleo/ritmo.dart';
import '../../reproduccion/reproductor.dart';
import '../comunes.dart';
import 'mascota_vida.dart';

bool _sinAnimar(BuildContext c) => MediaQuery.maybeDisableAnimationsOf(c) ?? false;

/// Aclara un color hasta que brille sobre fondo oscuro (para luces de neón).
Color brillante(Color c, {double minimo = 0.85}) {
  final h = HSVColor.fromColor(c);
  return h.withValue(max(h.value, minimo)).withSaturation(max(h.saturation, 0.45)).toColor();
}

// ---------------------------------------------------------------- Casete

/// Un casete: la carátula en su etiqueta y dos carretes que giran mientras suena. La cinta pasa
/// de un carrete al otro según avanza la canción.
class CaseteVista extends StatefulWidget {
  const CaseteVista({
    super.key,
    required this.url,
    required this.color,
    required this.r,
    required this.sonando,
    required this.lado,
  });

  final String url;
  final Color color;
  final Reproductor r;
  final bool sonando;

  /// Ancho del casete (el alto es 0,64 de eso).
  final double lado;

  @override
  State<CaseteVista> createState() => _CaseteVistaState();
}

class _CaseteVistaState extends State<CaseteVista> with SingleTickerProviderStateMixin {
  static const _segundosPorVuelta = 2.6;
  late final Ticker _reloj = createTicker(_cuadro);
  Duration _antes = Duration.zero;
  final _angulo = ValueNotifier<double>(0);
  double _vel = 0;
  bool _quieto = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _quieto = _sinAnimar(context);
    _revisar();
  }

  @override
  void didUpdateWidget(covariant CaseteVista old) {
    super.didUpdateWidget(old);
    _revisar();
  }

  /// Enciende el reloj al sonar; se apaga solo cuando los carretes ya se pararon.
  void _revisar() {
    if (widget.sonando && !_quieto && !_reloj.isActive) {
      _antes = Duration.zero;
      _reloj.start();
    }
    if (_quieto && _reloj.isActive) _reloj.stop();
  }

  void _cuadro(Duration t) {
    final dt = _antes == Duration.zero ? 0.016 : (t - _antes).inMicroseconds / 1e6;
    _antes = t;
    final objetivo = widget.sonando ? 1.0 : 0.0;
    _vel += (objetivo - _vel) * min(1.0, dt * (widget.sonando ? 3.0 : 2.0));
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

  /// 0..1 de lo que lleva sonado (para repartir la cinta entre los dos carretes).
  double _avance() {
    final d = widget.r.duracion.value.inMilliseconds;
    if (d <= 0) return 0;
    return (widget.r.posicion.value.inMilliseconds / d).clamp(0.0, 1.0);
  }

  @override
  Widget build(BuildContext context) {
    final w = widget.lado, h = w * 0.64;
    final plastico = Color.lerp(widget.color, const Color(0xFF15171C), 0.62)!;
    final reel = w * 0.1;
    return Semantics(
      label: 'Casete',
      child: SizedBox(
        width: w,
        height: h,
        child: Stack(clipBehavior: Clip.none, children: [
          // el cuerpo, la etiqueta y la ventanilla (fijos: se pintan una vez)
          Positioned.fill(
            child: RepaintBoundary(child: CustomPaint(painter: _CasetePintor(plastico, widget.color))),
          ),
          // la carátula, pegada en la etiqueta
          Positioned(
            left: w * 0.095,
            top: h * 0.115,
            width: h * 0.40,
            height: h * 0.40,
            child: Portada(url: widget.url, lado: h * 0.40, radio: 3),
          ),
          // los carretes: cada uno gira como una capa ya pintada; la cinta cambia de grosor
          // solo cuando cambia de verdad (cada 1/32 de la canción)
          for (final izq in const [true, false])
            Positioned(
              left: (izq ? w * 0.315 : w * 0.685) - reel,
              top: h * 0.60 - reel,
              width: reel * 2,
              height: reel * 2,
              child: ValueListenableBuilder<Duration>(
                valueListenable: widget.r.posicion,
                builder: (_, _, _) {
                  final a = _avance();
                  // al principio casi toda la cinta está a la izquierda; al final, a la derecha
                  final llena = izq ? 1 - a : a;
                  final cuarto = (llena * 32).round() / 32;
                  return RepaintBoundary(
                    child: AnimatedBuilder(
                      animation: _angulo,
                      builder: (_, hijo) => Transform.rotate(angle: _angulo.value * 2 * pi, child: hijo),
                      child: RepaintBoundary(child: CustomPaint(painter: _CarretePintor(cuarto))),
                    ),
                  );
                },
              ),
            ),
        ]),
      ),
    );
  }
}

class _CasetePintor extends CustomPainter {
  _CasetePintor(this.plastico, this.color);
  final Color plastico, color;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    final cuerpo = RRect.fromRectAndRadius(Rect.fromLTWH(0, 0, w, h), Radius.circular(w * 0.045));
    canvas.drawRRect(
        cuerpo.shift(Offset(0, h * 0.03)), Paint()..color = Colors.black.withValues(alpha: 0.45)..maskFilter = MaskFilter.blur(BlurStyle.normal, w * 0.03));
    canvas.drawRRect(
        cuerpo,
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color.lerp(plastico, Colors.white, 0.10)!, plastico, Color.lerp(plastico, Colors.black, 0.35)!],
          ).createShader(Rect.fromLTWH(0, 0, w, h)));
    canvas.drawRRect(cuerpo, Paint()..style = PaintingStyle.stroke..strokeWidth = 1..color = Colors.white.withValues(alpha: 0.10));

    // la etiqueta de papel
    final papel = RRect.fromRectAndRadius(Rect.fromLTWH(w * 0.07, h * 0.09, w * 0.86, h * 0.46), Radius.circular(w * 0.02));
    canvas.drawRRect(papel, Paint()..color = const Color(0xFFF2EAD8));
    // franjas de colores del tono de la carátula y renglones a mano
    final franja = Paint()..color = Color.lerp(color, Colors.white, 0.15)!;
    canvas.drawRect(Rect.fromLTWH(w * 0.07, h * 0.09, w * 0.86, h * 0.045), franja);
    canvas.drawRect(Rect.fromLTWH(w * 0.07, h * 0.505, w * 0.86, h * 0.045), franja..color = Color.lerp(color, Colors.black, 0.2)!);
    final linea = Paint()..color = const Color(0x33000000)..strokeWidth = max(1, w * 0.004);
    for (var i = 0; i < 3; i++) {
      final y = h * (0.25 + i * 0.075);
      canvas.drawLine(Offset(w * 0.55, y), Offset(w * 0.90, y), linea);
    }

    // la ventanilla de la cinta
    final ventana = RRect.fromRectAndRadius(Rect.fromLTWH(w * 0.17, h * 0.43, w * 0.66, h * 0.34), Radius.circular(h * 0.17));
    canvas.drawRRect(ventana, Paint()..color = const Color(0xFF0C0D10));
    canvas.drawRRect(ventana, Paint()..style = PaintingStyle.stroke..strokeWidth = max(1, w * 0.006)..color = Colors.white.withValues(alpha: 0.14));
    // la tira de cinta que cruza por debajo
    canvas.drawRect(Rect.fromLTWH(w * 0.30, h * 0.725, w * 0.40, h * 0.012), Paint()..color = const Color(0xFF3A2A1C));

    // la base trapezoidal con sus agujeros
    final base = Path()
      ..moveTo(w * 0.20, h)
      ..lineTo(w * 0.27, h * 0.82)
      ..lineTo(w * 0.73, h * 0.82)
      ..lineTo(w * 0.80, h)
      ..close();
    canvas.drawPath(base, Paint()..color = Colors.black.withValues(alpha: 0.35));
    final agujero = Paint()..color = const Color(0xFF0C0D10);
    for (final x in const [0.34, 0.42, 0.58, 0.66]) {
      canvas.drawCircle(Offset(w * x, h * 0.92), w * 0.013, agujero);
    }
    // los tornillos de las esquinas
    final tornillo = Paint()..color = Color.lerp(plastico, Colors.white, 0.35)!;
    for (final o in [Offset(w * 0.035, h * 0.06), Offset(w * 0.965, h * 0.06), Offset(w * 0.035, h * 0.94), Offset(w * 0.965, h * 0.94)]) {
      canvas.drawCircle(o, w * 0.012, tornillo);
    }
  }

  @override
  bool shouldRepaint(covariant _CasetePintor old) => old.plastico != plastico || old.color != color;
}

/// Un carrete: el disco de cinta (más grueso cuanto más llena [llena]) y el eje con sus dientes.
class _CarretePintor extends CustomPainter {
  _CarretePintor(this.llena);
  final double llena; // 0..1

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2;
    final cinta = r * (0.55 + 0.45 * llena);
    canvas.drawCircle(c, cinta, Paint()..color = const Color(0xFF3A2A1C));
    canvas.drawCircle(c, cinta, Paint()..style = PaintingStyle.stroke..strokeWidth = 1..color = Colors.white.withValues(alpha: 0.08));
    final eje = r * 0.52;
    canvas.drawCircle(c, eje, Paint()..color = const Color(0xFFE9E6DF));
    canvas.drawCircle(c, eje * 0.62, Paint()..color = const Color(0xFF14161B));
    // los seis dientes del eje: se ve que gira
    final diente = Paint()..color = const Color(0xFFE9E6DF)..strokeWidth = max(1.5, r * 0.12)..strokeCap = StrokeCap.round;
    for (var i = 0; i < 6; i++) {
      final a = i * pi / 3;
      canvas.drawLine(c + Offset(cos(a), sin(a)) * (eje * 0.30), c + Offset(cos(a), sin(a)) * (eje * 0.62), diente);
    }
  }

  @override
  bool shouldRepaint(covariant _CarretePintor old) => old.llena != llena;
}

// ---------------------------------------------------------------- Neón

/// La carátula con un borde de luz de neón que late. El resplandor se pinta una vez y solo
/// cambia su opacidad (barato aun en equipos viejos).
class NeonVista extends StatefulWidget {
  const NeonVista({
    super.key,
    required this.url,
    required this.luz,
    required this.luz2,
    required this.sonando,
    required this.lado,
    this.ritmo,
  });

  final String url;

  /// Los dos colores del borde (se mezclan en diagonal).
  final Color luz, luz2;
  final bool sonando;
  final double lado;

  /// El ritmo conocido de la canción (si lo hay, el latido va a su compás).
  final AnalisisRitmo? ritmo;

  @override
  State<NeonVista> createState() => _NeonVistaState();
}

class _NeonVistaState extends State<NeonVista> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: _duracion());
  bool _quieto = false;

  Duration _duracion() {
    final r = widget.ritmo;
    // un latido cada dos tiempos; sin ritmo conocido, un latido tranquilo
    final ms = r != null && r.valido ? (r.tiempo * 2000).clamp(700, 2400) : 1500;
    return Duration(milliseconds: ms.round());
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _quieto = _sinAnimar(context);
    _sincronizar();
  }

  @override
  void didUpdateWidget(covariant NeonVista old) {
    super.didUpdateWidget(old);
    final d = _duracion();
    if ((d - _c.duration!).abs() > const Duration(milliseconds: 120)) {
      _c.duration = d;
      if (_c.isAnimating) _c.repeat(reverse: true);
    }
    _sincronizar();
  }

  void _sincronizar() {
    if (widget.sonando && !_quieto) {
      if (!_c.isAnimating) _c.repeat(reverse: true);
    } else {
      _c.stop();
      _c.value = 0.5;
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final lado = widget.lado * 0.86;
    final radio = lado * 0.07;
    final borde = max(3.0, lado * 0.014);
    final brillo = Curves.easeInOut;
    return Center(
      child: SizedBox(
        width: lado + 60,
        height: lado + 60,
        child: Stack(alignment: Alignment.center, clipBehavior: Clip.none, children: [
          // el resplandor: una capa fija que solo late en opacidad
          RepaintBoundary(
            child: FadeTransition(
              opacity: _c.drive(CurveTween(curve: brillo)).drive(Tween(begin: 0.55, end: 1.0)),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(radio + 3),
                  boxShadow: [
                    BoxShadow(color: widget.luz.withValues(alpha: 0.55), blurRadius: lado * 0.10, spreadRadius: lado * 0.004),
                    BoxShadow(color: widget.luz2.withValues(alpha: 0.35), blurRadius: lado * 0.22, spreadRadius: lado * 0.01),
                  ],
                ),
                child: SizedBox(width: lado, height: lado),
              ),
            ),
          ),
          // el tubo de neón y la carátula
          Container(
            width: lado,
            height: lado,
            padding: EdgeInsets.all(borde),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(radio + 3),
              gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [widget.luz, widget.luz2]),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(radio),
              child: Portada(url: widget.url, lado: lado - borde * 2, radio: 0),
            ),
          ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- Flotante

/// La carátula flota con un vaivén suave sobre su sombra, y la mascota elegida se queda a su
/// lado «cantando». Sin mascota elegida, solo flota la carátula.
class FlotanteVista extends StatefulWidget {
  const FlotanteVista({
    super.key,
    required this.url,
    required this.color,
    required this.r,
    required this.sonando,
    required this.lado,
    this.ritmoDe,
  });

  final String url;
  final Color color;
  final Reproductor r;
  final bool sonando;
  final double lado;
  final AnalisisRitmo? Function()? ritmoDe;

  @override
  State<FlotanteVista> createState() => _FlotanteVistaState();
}

class _FlotanteVistaState extends State<FlotanteVista> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 3600));
  bool _quieto = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _quieto = _sinAnimar(context);
    _sincronizar();
  }

  @override
  void didUpdateWidget(covariant FlotanteVista old) {
    super.didUpdateWidget(old);
    _sincronizar();
  }

  void _sincronizar() {
    if (widget.sonando && !_quieto) {
      if (!_c.isAnimating) _c.repeat(reverse: true);
    } else {
      _c.stop();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final lado = widget.lado * 0.78;
    final alturaMascota = lado * 0.34;
    final subida = lado * 0.035;
    final curva = CurvedAnimation(parent: _c, curve: Curves.easeInOutSine);
    return SizedBox(
      width: widget.lado,
      height: lado + lado * 0.16,
      child: Stack(clipBehavior: Clip.none, children: [
        // la sombra en el suelo: se achica cuando la carátula sube
        Positioned(
          left: widget.lado * 0.12,
          width: lado * 0.8,
          bottom: 0,
          height: lado * 0.07,
          child: RepaintBoundary(
            child: AnimatedBuilder(
              animation: curva,
              builder: (_, hijo) => Transform.scale(scale: 1 - 0.12 * curva.value, child: hijo),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(lado),
                  gradient: RadialGradient(colors: [Colors.black.withValues(alpha: 0.5), Colors.black.withValues(alpha: 0)]),
                ),
              ),
            ),
          ),
        ),
        // la carátula, subiendo y bajando
        Positioned(
          left: widget.lado * 0.04,
          top: 0,
          width: lado,
          height: lado,
          child: RepaintBoundary(
            child: AnimatedBuilder(
              animation: curva,
              builder: (_, hijo) => Transform.translate(offset: Offset(0, -subida * curva.value), child: hijo),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(lado * 0.06),
                  boxShadow: [BoxShadow(color: widget.color.withValues(alpha: 0.45), blurRadius: lado * 0.10)],
                ),
                child: Portada(url: widget.url, lado: lado, radio: lado * 0.06),
              ),
            ),
          ),
        ),
        // la mascota, al lado y cantando
        Positioned(
          right: 0,
          bottom: lado * 0.03,
          child: MascotaSuelta(r: widget.r, alto: alturaMascota, animo: AnimoMascota.cantar, ritmoDe: widget.ritmoDe),
        ),
      ]),
    );
  }
}

/// El segundo color del tubo de neón: el de contraste de la carátula si es de otro matiz; si
/// no, el mismo acento girado 45 grados (para que el borde tenga degradado y no sea plano).
Color colorSecundarioNeon(Color acento, Color contraste) {
  final a = HSVColor.fromColor(acento), c = HSVColor.fromColor(contraste);
  final d = (a.hue - c.hue).abs();
  final lejos = min(d, 360 - d) > 30 && c.saturation > 0.2;
  return lejos ? brillante(contraste) : brillante(a.withHue((a.hue + 45) % 360).toColor());
}
