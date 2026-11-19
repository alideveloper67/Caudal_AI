import 'dart:math';

import 'package:flutter/material.dart';

import '../reproductor/vinilo.dart';
import '../tema.dart';

part 'ilustraciones_v4.dart';
part 'ilustraciones_v5.dart';

/// Lo que comparten todas las ilustraciones: un reloj que da vueltas de 12 s
/// (todo movimiento dura un divisor de 12 s, así el bucle no tiene saltos) y
/// si hay que dejarlo todo quieto (quien pide menos movimiento).
class Ctx {
  const Ctx(this.reloj, this.acento, this.reducir);
  final Animation<double> reloj;
  final Color acento;
  final bool reducir;

  /// Segundos dentro de la vuelta, de 0 a 12.
  double get s => reloj.value * 12;
}

const double segundosVuelta = 12;

// ---------------------------------------------------------------- utilidades

double _onda(double s, double periodo, [double fase = 0]) => 0.5 + 0.5 * sin(2 * pi * (s / periodo + fase));
double _tramo(double s, double a, double b) => ((s - a) / (b - a)).clamp(0.0, 1.0);
double _suave(double x) => Curves.easeInOut.transform(x.clamp(0.0, 1.0));
double _lerp(double a, double b, double t) => a + (b - a) * t;

const _oro = Color(0xFFF5C542);
const _oroClaro = Color(0xFFFFE08A);
const _panel = Color(0xFF101217);

typedef _Dibuja = void Function(Canvas c, Size z, double s);

class _Dibujo extends CustomPainter {
  _Dibujo(this.s, this.f);
  final double s;
  final _Dibuja f;
  @override
  void paint(Canvas canvas, Size size) => f(canvas, size, s);
  @override
  bool shouldRepaint(covariant _Dibujo old) => true;
}

Widget _lienzo(Ctx c, double lado, _Dibuja f) => RepaintBoundary(
      child: AnimatedBuilder(
        animation: c.reloj,
        builder: (_, _) => CustomPaint(size: Size(lado, lado), painter: _Dibujo(c.s, f)),
      ),
    );

Paint _trazo(Color color, double ancho) => Paint()
  ..style = PaintingStyle.stroke
  ..strokeWidth = ancho
  ..strokeCap = StrokeCap.round
  ..color = color;

void _estrella(Canvas c, Offset o, double r, Color color) {
  if (r <= 0) return;
  final p = Path()
    ..moveTo(o.dx, o.dy - r)
    ..quadraticBezierTo(o.dx, o.dy, o.dx + r, o.dy)
    ..quadraticBezierTo(o.dx, o.dy, o.dx, o.dy + r)
    ..quadraticBezierTo(o.dx, o.dy, o.dx - r, o.dy)
    ..quadraticBezierTo(o.dx, o.dy, o.dx, o.dy - r);
  c.drawPath(p, Paint()..color = color);
}

void _nota(Canvas c, Offset o, double r, Color color) {
  if (r <= 0) return;
  final p = Paint()..color = color;
  c.save();
  c.translate(o.dx, o.dy);
  c.rotate(-0.35);
  c.drawOval(Rect.fromCenter(center: Offset.zero, width: r * 1.5, height: r * 1.1), p);
  c.restore();
  final x = o.dx + r * 0.62;
  final alto = o.dy - r * 2.4;
  c.drawLine(Offset(x, o.dy - r * 0.1), Offset(x, alto), _trazo(color, max(1.0, r * 0.26)));
  final bandera = Path()
    ..moveTo(x, alto)
    ..cubicTo(x + r * 1.2, alto + r * 0.5, x + r * 1.0, alto + r * 1.2, x + r * 0.9, alto + r * 1.6);
  c.drawPath(bandera, _trazo(color, max(1.0, r * 0.26)));
}

void _persona(Canvas c, Offset o, double r, Color color) {
  if (r <= 0) return;
  final p = Paint()..color = color;
  c.drawCircle(o + Offset(0, -r * 0.22), r * 0.30, p);
  c.drawOval(Rect.fromCenter(center: o + Offset(0, r * 0.62), width: r * 1.05, height: r * 0.8), p);
}

/// Una escena de paisaje (cielo, sol y montañas) hecha con degradados.
void _escena(Canvas c, Rect r, Color color) {
  c.drawRect(
    r,
    Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color.lerp(color, const Color(0xFF1B1F27), 0.35)!, Color.lerp(color, const Color(0xFFFF8A3D), 0.6)!],
      ).createShader(r),
  );
  c.drawCircle(Offset(r.left + r.width * 0.68, r.top + r.height * 0.40), r.width * 0.15, Paint()..color = _oroClaro);
  final m1 = Path()
    ..moveTo(r.left, r.bottom)
    ..lineTo(r.left, r.top + r.height * 0.70)
    ..lineTo(r.left + r.width * 0.30, r.top + r.height * 0.52)
    ..lineTo(r.left + r.width * 0.58, r.top + r.height * 0.74)
    ..lineTo(r.right, r.top + r.height * 0.60)
    ..lineTo(r.right, r.bottom)
    ..close();
  c.drawPath(m1, Paint()..color = const Color(0xFF2A2140).withValues(alpha: 0.9));
  final m2 = Path()
    ..moveTo(r.left, r.bottom)
    ..lineTo(r.left, r.top + r.height * 0.86)
    ..lineTo(r.left + r.width * 0.42, r.top + r.height * 0.70)
    ..lineTo(r.right, r.top + r.height * 0.90)
    ..lineTo(r.right, r.bottom)
    ..close();
  c.drawPath(m2, Paint()..color = const Color(0xFF14101F));
}

Widget _logo(double lado) => Image.asset(
      'assets/logo/caudal.png',
      width: lado,
      height: lado,
      filterQuality: FilterQuality.high,
      errorBuilder: (_, _, _) => Icon(Icons.water_drop_rounded, size: lado * 0.7, color: Colors.white),
    );

/// Un destello que cruza el hijo de lado a lado cada 4 s.
class _Destello extends StatelessWidget {
  const _Destello({required this.c, required this.child, this.intensidad = 0.8});
  final Ctx c;
  final Widget child;
  final double intensidad;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: c.reloj,
        child: child,
        builder: (_, h) {
          final fase = (c.s % 4) / 4;
          final q = _suave(fase / 0.5);
          return ShaderMask(
            blendMode: BlendMode.srcATop,
            shaderCallback: (r) => LinearGradient(
              begin: const Alignment(-1, -0.4),
              end: const Alignment(1, 0.4),
              colors: [
                const Color(0x00FFFFFF),
                Colors.white.withValues(alpha: intensidad),
                const Color(0x00FFFFFF),
              ],
              stops: const [0.30, 0.5, 0.70],
              transform: _Desliza(_lerp(-1.2, 1.2, q)),
            ).createShader(r),
            child: h,
          );
        },
      );
}

class _Desliza extends GradientTransform {
  const _Desliza(this.fraccion);
  final double fraccion;
  @override
  Matrix4? transform(Rect bounds, {TextDirection? textDirection}) =>
      Matrix4.translationValues(bounds.width * fraccion, 0, 0);
}

// ------------------------------------------------------------------ 1. portada

Widget ilusPortada(Ctx c, double L) {
  final col = c.acento;
  return Stack(alignment: Alignment.center, children: [
    Positioned.fill(
      child: _lienzo(c, L, (cv, z, s) {
        final w = z.width, h = z.height;
        for (var i = 0; i < 3; i++) {
          final p = ((s / 4) + i / 3) % 1;
          cv.drawCircle(Offset(w / 2, h * 0.46), w * (0.18 + 0.36 * p), _trazo(col.withValues(alpha: (1 - p) * 0.35), 1.6));
        }
        for (var i = 0; i < 5; i++) {
          final path = Path();
          final m = (i % 3) + 1;
          final amp = h * (0.030 + 0.008 * i);
          final base = h * (0.72 + 0.045 * i);
          for (var k = 0; k <= 48; k++) {
            final x = w * k / 48;
            final y = base + sin((k / 48) * 2 * pi * (1.2 + 0.35 * i) + 2 * pi * s * m / 12) * amp;
            k == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
          }
          cv.drawPath(
            path,
            Paint()
              ..style = PaintingStyle.stroke
              ..strokeWidth = 2.4 - i * 0.28
              ..strokeCap = StrokeCap.round
              ..shader = LinearGradient(colors: [
                col.withValues(alpha: 0),
                Color.lerp(col, Colors.white, 0.35)!.withValues(alpha: 0.8 - i * 0.12),
                col.withValues(alpha: 0),
              ]).createShader(Rect.fromLTWH(0, 0, w, h)),
          );
        }
      }),
    ),
    Align(
      alignment: const Alignment(0, -0.08),
      child: AnimatedBuilder(
        animation: c.reloj,
        builder: (_, _) {
          final latido = 1 + 0.03 * _onda(c.s, 4);
          return Transform.scale(
            scale: latido,
            child: Container(
              width: L * 0.40,
              height: L * 0.40,
              decoration: BoxDecoration(shape: BoxShape.circle, boxShadow: [
                BoxShadow(color: col.withValues(alpha: 0.45), blurRadius: L * 0.14, spreadRadius: L * 0.01),
              ]),
              child: _Destello(c: c, child: _logo(L * 0.40)),
            ),
          );
        },
      ),
    ),
  ]);
}

/// El logo con su destello (para otras pantallas).
Widget logoConDestello(Ctx c, double lado) => _Destello(c: c, child: _logo(lado));

// ------------------------------------------------------------------- 2. fondo

Widget ilusFondo(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final marco = RRect.fromRectAndRadius(
          Rect.fromCenter(center: Offset(L / 2, L / 2), width: L * 0.64, height: L * 0.82), Radius.circular(L * 0.06));
      cv.drawRRect(marco.shift(Offset(0, L * 0.02)),
          Paint()..color = Colors.black.withValues(alpha: 0.4)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.04));
      cv.drawRRect(marco, Paint()..color = _panel);
      final r = marco.outerRect;
      final v1 = _onda(s, 6);
      final a = 0.16 + 0.62 * v1;
      cv.save();
      cv.clipRRect(marco);
      cv.saveLayer(r, Paint()..color = Colors.white.withValues(alpha: a));
      _escena(cv, r, c.acento);
      cv.restore();
      // la parte de abajo se oscurece para que se lean los deslizadores
      cv.drawRect(
        Rect.fromLTRB(r.left, r.top + r.height * 0.62, r.right, r.bottom),
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [_panel.withValues(alpha: 0), _panel.withValues(alpha: 0.92)],
          ).createShader(Rect.fromLTRB(r.left, r.top + r.height * 0.62, r.right, r.bottom)),
      );
      // la app por delante: filas de una lista
      for (var i = 0; i < 4; i++) {
        final y = r.top + r.height * (0.09 + i * 0.085);
        cv.drawCircle(Offset(r.left + r.width * 0.11, y + r.height * 0.02), r.width * 0.045, Paint()..color = Colors.white.withValues(alpha: 0.16));
        cv.drawRRect(
          RRect.fromRectAndRadius(
              Rect.fromLTWH(r.left + r.width * 0.21, y, r.width * (0.58 - i * 0.07), r.height * 0.03), Radius.circular(L * 0.01)),
          Paint()..color = Colors.white.withValues(alpha: 0.2),
        );
      }
      // dos deslizadores
      void desliza(double y, double v) {
        final x0 = r.left + r.width * 0.14, x1 = r.right - r.width * 0.14;
        cv.drawLine(Offset(x0, y), Offset(x1, y), _trazo(Colors.white.withValues(alpha: 0.2), L * 0.014));
        final xk = _lerp(x0, x1, v);
        cv.drawLine(Offset(x0, y), Offset(xk, y), _trazo(c.acento, L * 0.014));
        cv.drawCircle(Offset(xk, y), L * 0.026, Paint()..color = Colors.white);
        cv.drawCircle(Offset(xk, y), L * 0.026, _trazo(c.acento, 1.6));
      }

      desliza(r.top + r.height * 0.80, v1);
      desliza(r.top + r.height * 0.90, _onda(s, 4, 0.25));
      cv.restore();
      cv.drawRRect(marco, _trazo(Colors.white.withValues(alpha: 0.14), 1.2));
    });

// ---------------------------------------------------------------- 3. donadores

Widget ilusDonadores(Ctx c, double L) {
  final texto = max(10.0, L * 0.052);
  return Stack(alignment: Alignment.center, children: [
    Positioned.fill(
      child: _lienzo(c, L, (cv, z, s) {
        final ctr = Offset(L / 2, L * 0.43);
        final R = L * 0.24;
        cv.drawCircle(
          ctr,
          R * 2.1,
          Paint()..shader = RadialGradient(colors: [_oro.withValues(alpha: 0.30), _oro.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: ctr, radius: R * 2.1)),
        );
        final caja = Rect.fromCircle(center: ctr, radius: R);
        cv.drawCircle(
          ctr,
          R,
          Paint()
            ..shader = LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color.lerp(c.acento, Colors.white, 0.1)!, Color.lerp(c.acento, Colors.black, 0.55)!],
            ).createShader(caja),
        );
        cv.save();
        cv.clipPath(Path()..addOval(caja));
        _persona(cv, ctr + Offset(0, R * 0.12), R * 1.3, Colors.white.withValues(alpha: 0.85));
        cv.restore();
        final anillo = Rect.fromCircle(center: ctr, radius: R + L * 0.03);
        cv.drawCircle(
          ctr,
          R + L * 0.03,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = L * 0.03
            ..shader = SweepGradient(
              colors: const [Color(0xFFB8860B), _oroClaro, _oro, Color(0xFF9A6B06), Color(0xFFB8860B)],
              transform: GradientRotation(2 * pi * s / 6),
            ).createShader(anillo),
        );
        for (var i = 0; i < 6; i++) {
          final ang = 2 * pi * (i / 6 + s / 12);
          final rr = L * (0.37 + 0.02 * sin(i * 2.0));
          final o = ctr + Offset(cos(ang) * rr * 1.1, sin(ang) * rr * 0.95);
          _estrella(cv, o, L * (0.010 + 0.026 * _onda(s, 3, i / 6)), _oroClaro);
        }
      }),
    ),
    // la etiqueta GIF que rebota
    Positioned(
      right: L * 0.10,
      top: L * 0.12,
      child: AnimatedBuilder(
        animation: c.reloj,
        builder: (_, _) => Transform.translate(
          offset: Offset(0, -L * 0.012 * _onda(c.s, 2)),
          child: Container(
            padding: EdgeInsets.symmetric(horizontal: L * 0.03, vertical: L * 0.012),
            decoration: BoxDecoration(
              color: const Color(0xFF14171D),
              borderRadius: BorderRadius.circular(L * 0.03),
              border: Border.all(color: _oro.withValues(alpha: 0.7)),
            ),
            child: Text('GIF', style: TextStyle(fontSize: texto * 0.8, fontWeight: FontWeight.w900, color: _oroClaro, letterSpacing: 1)),
          ),
        ),
      ),
    ),
    // la insignia dorada
    Align(
      alignment: const Alignment(0, 0.84),
      child: _Destello(
        c: c,
        intensidad: 0.9,
        child: Container(
          padding: EdgeInsets.symmetric(horizontal: L * 0.05, vertical: L * 0.018),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(L * 0.06),
            gradient: const LinearGradient(colors: [Color(0xFFFFE08A), Color(0xFFF5C542), Color(0xFFD99A12)]),
            boxShadow: [BoxShadow(color: _oro.withValues(alpha: 0.35), blurRadius: L * 0.05)],
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.workspace_premium_rounded, size: texto * 1.3, color: const Color(0xFF3A2800)),
            SizedBox(width: L * 0.015),
            Text('DONADOR', style: TextStyle(fontSize: texto, fontWeight: FontWeight.w900, letterSpacing: 1.4, color: const Color(0xFF3A2800))),
          ]),
        ),
      ),
    ),
  ]);
}

// ----------------------------------------------------------------- 4. vinilo

Widget ilusVinilo(Ctx c, double L) {
  final lado = L * 0.88;
  return Stack(alignment: Alignment.center, children: [
    Align(
      alignment: const Alignment(0, -0.35),
      child: VinilVista(url: '', color: c.acento, sonando: !c.reducir, lado: lado),
    ),
    Align(
      alignment: const Alignment(0, 0.96),
      child: AnimatedBuilder(
        animation: c.reloj,
        builder: (_, _) => Container(
          padding: EdgeInsets.symmetric(horizontal: L * 0.04, vertical: L * 0.014),
          decoration: BoxDecoration(
            color: const Color(0xFF14171D).withValues(alpha: 0.9),
            borderRadius: BorderRadius.circular(L * 0.05),
            border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: L * 0.022,
              height: L * 0.022,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _oroClaro,
                boxShadow: [BoxShadow(color: _oro.withValues(alpha: 0.4 + 0.5 * _onda(c.s, 2)), blurRadius: L * 0.03)],
              ),
            ),
            SizedBox(width: L * 0.02),
            Text('Pantalla encendida',
                style: TextStyle(fontSize: max(10.0, L * 0.042), fontWeight: FontWeight.w700, color: Colors.white.withValues(alpha: 0.85))),
          ]),
        ),
      ),
    ),
  ]);
}

// ---------------------------------------------------------------- 5. estudio

Widget ilusEstudio(Ctx c, double L) {
  final col = c.acento;
  return Stack(alignment: Alignment.center, children: [
    Positioned.fill(
      child: _lienzo(c, L, (cv, z, s) {
        final lluvia = Color.lerp(col, Colors.white, 0.5)!.withValues(alpha: 0.30);
        for (var i = 0; i < 22; i++) {
          final x = L * (0.05 + 0.9 * ((i * 0.6180339) % 1));
          final k = 3 + (i % 3);
          final y = ((s / 12 * k + (i * 0.37) % 1) % 1) * L * 1.1 - L * 0.05;
          final largo = L * (0.04 + 0.03 * (i % 3));
          cv.drawLine(Offset(x, y), Offset(x - L * 0.006, y + largo), _trazo(lluvia, 1.4));
        }
        final ctr = Offset(L / 2, L * 0.40);
        final R = L * 0.27;
        final caja = Rect.fromCircle(center: ctr, radius: R);
        cv.drawCircle(ctr, R, _trazo(Colors.white.withValues(alpha: 0.10), L * 0.04));
        final p = s / 12;
        cv.drawArc(
          caja,
          -pi / 2,
          2 * pi * p,
          false,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = L * 0.04
            ..strokeCap = StrokeCap.round
            ..shader = SweepGradient(
              colors: [col, Color.lerp(col, Colors.white, 0.5)!],
              transform: const GradientRotation(-pi / 2),
              endAngle: 2 * pi,
            ).createShader(caja),
        );
        final fin = ctr + Offset(cos(-pi / 2 + 2 * pi * p), sin(-pi / 2 + 2 * pi * p)) * R;
        cv.drawCircle(fin, L * 0.014, Paint()..color = Colors.white);
        // pomodoro: cuatro puntos
        final llenos = (s / 3).floor() + 1;
        for (var i = 0; i < 4; i++) {
          cv.drawCircle(ctr + Offset((i - 1.5) * L * 0.05, R * 0.52), L * 0.014,
              Paint()..color = i < llenos ? col : Colors.white.withValues(alpha: 0.2));
        }
        // mezclador: tres deslizadores verticales
        const periodos = [4.0, 6.0, 3.0];
        for (var i = 0; i < 3; i++) {
          final x = L * (0.34 + i * 0.16);
          final top = L * 0.78, bot = L * 0.94;
          cv.drawLine(Offset(x, top), Offset(x, bot), _trazo(Colors.white.withValues(alpha: 0.16), L * 0.012));
          final y = _lerp(bot, top, _onda(s, periodos[i], i / 3));
          cv.drawLine(Offset(x, bot), Offset(x, y), _trazo(col, L * 0.012));
          cv.drawRRect(RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(x, y), width: L * 0.06, height: L * 0.026), Radius.circular(L * 0.01)),
              Paint()..color = Colors.white);
        }
      }),
    ),
    Align(
      alignment: const Alignment(0, -0.2),
      child: AnimatedBuilder(
        animation: c.reloj,
        builder: (_, _) {
          final resta = (25 * 60 * (1 - c.s / 12)).round().clamp(0, 25 * 60);
          final t = '${(resta ~/ 60).toString().padLeft(2, '0')}:${(resta % 60).toString().padLeft(2, '0')}';
          return Text(t,
              style: TextStyle(
                  fontSize: max(14.0, L * 0.115),
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1,
                  color: Colors.white,
                  fontFeatures: const [FontFeature.tabularFigures()]));
        },
      ),
    ),
    Align(
      alignment: const Alignment(0, -0.97),
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: L * 0.035, vertical: L * 0.012),
        decoration: BoxDecoration(
          color: const Color(0xFF14171D).withValues(alpha: 0.85),
          borderRadius: BorderRadius.circular(L * 0.05),
          border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.local_fire_department_rounded, size: max(12.0, L * 0.05), color: const Color(0xFFFF8A3D)),
          SizedBox(width: L * 0.012),
          Text('Racha de 7 días', style: TextStyle(fontSize: max(10.0, L * 0.040), fontWeight: FontWeight.w700, color: Colors.white.withValues(alpha: 0.9))),
        ]),
      ),
    ),
  ]);
}

// ------------------------------------------------------------ 6. música sigue

Widget ilusSigue(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final col = c.acento;
      final cuerpo = Rect.fromCenter(center: Offset(L / 2, L * 0.52), width: L * 0.34, height: L * 0.62);
      final rad = L * 0.06;
      for (var i = 0; i < 3; i++) {
        final p = ((s / 4) + i / 3) % 1;
        final d = L * 0.30 * p;
        cv.drawRRect(RRect.fromRectAndRadius(cuerpo.inflate(d), Radius.circular(rad + d)), _trazo(col.withValues(alpha: (1 - p) * 0.45), 1.6));
      }
      final rr = RRect.fromRectAndRadius(cuerpo, Radius.circular(rad));
      cv.drawRRect(rr.shift(Offset(0, L * 0.02)), Paint()..color = Colors.black.withValues(alpha: 0.45)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.03));
      cv.drawRRect(
        rr,
        Paint()
          ..shader = const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Color(0xFF1B1F27), Color(0xFF0B0D12)])
              .createShader(cuerpo),
      );
      cv.drawRRect(rr, _trazo(Colors.white.withValues(alpha: 0.22), 1.4));
      final pantalla = RRect.fromRectAndRadius(cuerpo.deflate(L * 0.016), Radius.circular(rad * 0.7));
      cv.drawRRect(pantalla, Paint()..color = const Color(0xFF05060A));
      // la pantalla apagada: una lunita
      final luna = Offset(L / 2, L * 0.52);
      final r = L * 0.045;
      cv.drawPath(
        Path.combine(PathOperation.difference, Path()..addOval(Rect.fromCircle(center: luna, radius: r)),
            Path()..addOval(Rect.fromCircle(center: luna + Offset(r * 0.55, -r * 0.3), radius: r * 0.85))),
        Paint()..color = Colors.white.withValues(alpha: 0.5),
      );
      // ecualizador a los lados
      const periodos = [3.0, 4.0, 6.0, 2.0];
      for (final lado in const [-1, 1]) {
        for (var i = 0; i < 4; i++) {
          final x = L / 2 + lado * (L * 0.17 + L * 0.07 + i * L * 0.048);
          final h = L * (0.05 + 0.17 * _onda(s, periodos[i], i * 0.23 + (lado > 0 ? 0.1 : 0)));
          cv.drawRRect(
            RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(x, L * 0.52), width: L * 0.026, height: h), Radius.circular(L * 0.013)),
            Paint()..color = Color.lerp(col, Colors.white, 0.3)!.withValues(alpha: 0.95 - i * 0.17),
          );
        }
      }
      // notas que suben
      for (var i = 0; i < 3; i++) {
        final p = ((s / 6) + i / 3) % 1;
        final x = L * (0.5 + (i - 1) * 0.19) + L * 0.025 * sin(2 * pi * (p * 2 + i));
        final y = L * (0.17 - 0.12 * p);
        _nota(cv, Offset(x, y + L * 0.06), L * 0.026, Colors.white.withValues(alpha: sin(pi * p).clamp(0.0, 1.0) * 0.9));
      }
    });

// ------------------------------------------------------------- 7. compartir

Widget ilusCompartir(Ctx c, double L) => AnimatedBuilder(
      animation: c.reloj,
      builder: (_, _) {
        final s = c.s;
        final osc = sin(2 * pi * s / 6);
        final ancho = L * 0.36, alto = L * 0.58;
        Widget tarjeta(Gradient g, Widget hijo, double rot, Offset desp) => Transform.translate(
              offset: desp,
              child: Transform.rotate(
                angle: rot,
                child: Container(
                  width: ancho,
                  height: alto,
                  padding: EdgeInsets.all(L * 0.03),
                  decoration: BoxDecoration(
                    gradient: g,
                    borderRadius: BorderRadius.circular(L * 0.05),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
                    boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.4), blurRadius: L * 0.05, offset: Offset(0, L * 0.02))],
                  ),
                  child: hijo,
                ),
              ),
            );
        Widget barra(double f, {Color? color}) => Container(
              height: L * 0.018,
              width: ancho * f,
              margin: EdgeInsets.only(bottom: L * 0.018),
              decoration: BoxDecoration(color: color ?? Colors.white.withValues(alpha: 0.28), borderRadius: BorderRadius.circular(L * 0.01)),
            );
        final izq = tarjeta(
          LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Color.lerp(c.acento, Colors.black, 0.2)!, const Color(0xFF2A2140)]),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            CircleAvatar(radius: L * 0.045, backgroundColor: Colors.white.withValues(alpha: 0.25)),
            SizedBox(height: L * 0.03),
            barra(0.6),
            barra(0.42),
            const Spacer(),
            barra(0.5, color: Colors.white.withValues(alpha: 0.5)),
          ]),
          -0.20 + 0.02 * osc,
          Offset(-L * 0.20, L * 0.02),
        );
        final der = tarjeta(
          const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Color(0xFF3A2A18), Color(0xFF14171D)]),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.format_quote_rounded, size: L * 0.09, color: _oro),
            barra(0.78),
            barra(0.66),
            barra(0.72, color: c.acento.withValues(alpha: 0.85)),
            barra(0.5),
            barra(0.62),
          ]),
          0.17 - 0.02 * osc,
          Offset(L * 0.20, L * 0.02),
        );
        final centro = tarjeta(
          const LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Color(0xFFFF5C8A), Color(0xFFFF8A3D)]),
          Column(children: [
            SizedBox(height: L * 0.02),
            CircleAvatar(radius: L * 0.075, backgroundColor: Colors.white.withValues(alpha: 0.3), child: Icon(Icons.person_rounded, size: L * 0.1, color: Colors.white)),
            SizedBox(height: L * 0.035),
            barra(0.55, color: Colors.white.withValues(alpha: 0.85)),
            barra(0.38),
            const Spacer(),
            Icon(Icons.music_note_rounded, size: L * 0.07, color: Colors.white.withValues(alpha: 0.9)),
          ]),
          0.02 * osc,
          Offset(0, -L * 0.012 + L * 0.012 * osc),
        );
        return SizedBox(
          width: L,
          height: L,
          child: Stack(alignment: Alignment.center, clipBehavior: Clip.none, children: [
            izq,
            der,
            centro,
            Align(
              alignment: const Alignment(0, 0.92),
              child: Transform.scale(
                scale: 1 + 0.07 * _onda(s, 3),
                child: Container(
                  width: L * 0.13,
                  height: L * 0.13,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFF25D366),
                    boxShadow: [BoxShadow(color: const Color(0xFF25D366).withValues(alpha: 0.45), blurRadius: L * 0.05)],
                  ),
                  child: Icon(Icons.share_rounded, size: L * 0.07, color: Colors.white),
                ),
              ),
            ),
          ]),
        );
      },
    );

// ------------------------------------------------------------- 8. artistas

Widget ilusArtistas(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      const nodos = <(double, double, double)>[
        (0.20, 0.27, 0.078),
        (0.79, 0.24, 0.088),
        (0.14, 0.64, 0.066),
        (0.84, 0.66, 0.072),
        (0.40, 0.87, 0.080),
        (0.62, 0.11, 0.056),
        (0.66, 0.86, 0.058),
      ];
      const paleta = [Color(0xFF8B6CFF), Color(0xFFFF5C8A), Color(0xFF4C8DFF), Color(0xFFFF8A3D), Color(0xFF2BD576), Color(0xFFF5C542), Color(0xFFB4A1FF)];
      final fade = 1 - _tramo(s, 10.6, 11.6);
      final centro = Offset(L / 2, L * 0.5);
      final ap = <double>[];
      final pos = <Offset>[];
      for (var i = 0; i < nodos.length; i++) {
        ap.add(Curves.easeOutBack.transform(_tramo(s, 0.5 + i * 0.45, 1.2 + i * 0.45)));
        final f = Offset(sin(2 * pi * (s / 6 + i / 7)), cos(2 * pi * (s / 6 + i / 7))) * L * 0.009;
        pos.add(Offset(L * nodos[i].$1, L * nodos[i].$2) + f);
      }
      // líneas: todas al centro y algunas entre vecinos
      final enlaces = <(Offset, Offset, double)>[
        for (var i = 0; i < nodos.length; i++) (centro, pos[i], min(ap[i], 1.0)),
        for (final (a, b) in const [(0, 2), (1, 3), (0, 5), (1, 5), (2, 4), (3, 6), (4, 6)])
          (pos[a], pos[b], min(ap[a], ap[b]).clamp(0.0, 1.0)),
      ];
      for (var j = 0; j < enlaces.length; j++) {
        final (a, b, p) = enlaces[j];
        final q = _suave(_tramo(s, 1.4 + j * 0.28, 2.3 + j * 0.28)) * p;
        if (q <= 0) continue;
        cv.drawLine(a, Offset.lerp(a, b, q)!, _trazo(c.acento.withValues(alpha: 0.5 * fade), 1.4));
      }
      void burbuja(Offset o, double r, Color color, double a, bool nota) {
        if (a <= 0.001 || r <= 0) return;
        final rr = r * a.clamp(0.0, 1.15);
        cv.drawCircle(o, rr * 1.9, Paint()..shader = RadialGradient(colors: [color.withValues(alpha: 0.32 * fade), color.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: o, radius: rr * 1.9)));
        cv.drawCircle(
          o,
          rr,
          Paint()
            ..shader = LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color.lerp(color, Colors.white, 0.2)!.withValues(alpha: fade), Color.lerp(color, Colors.black, 0.45)!.withValues(alpha: fade)],
            ).createShader(Rect.fromCircle(center: o, radius: rr)),
        );
        cv.drawCircle(o, rr, _trazo(Colors.white.withValues(alpha: 0.3 * fade), 1.2));
        if (nota) {
          _nota(cv, o + Offset(-rr * 0.12, rr * 0.3), rr * 0.4, Colors.white.withValues(alpha: 0.95 * fade));
        } else {
          _persona(cv, o, rr * 1.15, Colors.white.withValues(alpha: 0.85 * fade));
        }
      }

      burbuja(centro, L * 0.115, c.acento, Curves.easeOutBack.transform(_tramo(s, 0, 0.8)), true);
      for (var i = 0; i < nodos.length; i++) {
        burbuja(pos[i], L * nodos[i].$3, paleta[i], ap[i], false);
      }
    });

// ------------------------------------------------------------------ 9. listas

Widget ilusListas(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final p = s / 12;
      double m;
      if (p < 0.30) {
        m = 0;
      } else if (p < 0.50) {
        m = _suave(_tramo(p, 0.30, 0.50));
      } else if (p < 0.82) {
        m = 1;
      } else if (p < 0.97) {
        m = 1 - _suave(_tramo(p, 0.82, 0.97));
      } else {
        m = 0;
      }
      const paleta = [
        Color(0xFF8B6CFF), Color(0xFFFF5C8A), Color(0xFF4C8DFF),
        Color(0xFFFF8A3D), Color(0xFF2BD576), Color(0xFFF5C542),
        Color(0xFFB4A1FF), Color(0xFF22D3EE), Color(0xFFEC4899),
      ];
      final lado = L * 0.62 * (1 + 0.03 * m);
      final g = Rect.fromCenter(center: Offset(L / 2, L * 0.48), width: lado, height: lado);
      final hueco = _lerp(L * 0.022, 0, m);
      final t = (lado - hueco * 2) / 3;
      final radio = _lerp(L * 0.03, 0, m);
      for (var i = 0; i < 9; i++) {
        final f = i ~/ 3, k = i % 3;
        final r = Rect.fromLTWH(g.left + k * (t + hueco), g.top + f * (t + hueco), t, t);
        // al juntarse, las esquinas redondeadas solo quedan en las del conjunto
        final rr = RRect.fromRectAndCorners(
          r,
          topLeft: Radius.circular(i == 0 ? max(radio, L * 0.05 * m) : radio),
          topRight: Radius.circular(i == 2 ? max(radio, L * 0.05 * m) : radio),
          bottomLeft: Radius.circular(i == 6 ? max(radio, L * 0.05 * m) : radio),
          bottomRight: Radius.circular(i == 8 ? max(radio, L * 0.05 * m) : radio),
        );
        cv.drawRRect(rr, Paint()..color = paleta[i].withValues(alpha: 0.9));
        cv.drawCircle(r.center, t * 0.16, Paint()..color = Colors.white.withValues(alpha: 0.25 * (1 - m)));
      }
      if (m > 0) {
        final rr = RRect.fromRectAndRadius(g, Radius.circular(L * 0.05));
        cv.save();
        cv.clipRRect(rr);
        cv.saveLayer(g, Paint()..color = Colors.white.withValues(alpha: m));
        _escena(cv, g, c.acento);
        cv.restore();
        cv.restore();
        cv.drawRRect(rr, _trazo(Colors.white.withValues(alpha: 0.25 * m), 1.4));
        // la insignia de «tu imagen»
        final a = _tramo(m, 0.7, 1);
        final o = Offset(g.right - L * 0.01, g.bottom - L * 0.01);
        cv.drawCircle(o, L * 0.065 * a, Paint()..color = c.acento);
        final b = L * 0.03 * a;
        cv.drawLine(o + Offset(-b, 0), o + Offset(b, 0), _trazo(Colors.white, L * 0.014));
        cv.drawLine(o + Offset(0, -b), o + Offset(0, b), _trazo(Colors.white, L * 0.014));
      }
    });

// ------------------------------------------------------------ 10. pantallas

Widget ilusPantallas(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final k = 0.5 - 0.5 * cos(2 * pi * s / 12); // 0 teléfono · 1 escritorio
      final w = L * _lerp(0.34, 0.86, k), h = L * _lerp(0.66, 0.52, k);
      final marco = Rect.fromCenter(center: Offset(L / 2, L * 0.45), width: w, height: h);
      final rr = RRect.fromRectAndRadius(marco, Radius.circular(_lerp(L * 0.07, L * 0.025, k)));
      cv.drawRRect(rr.shift(Offset(0, L * 0.02)), Paint()..color = Colors.black.withValues(alpha: 0.4)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.035));
      cv.drawRRect(rr, Paint()..color = _panel);
      cv.drawRRect(rr, _trazo(Colors.white.withValues(alpha: 0.2), 1.8));
      // el soporte del monitor aparece al ensancharse
      final soporte = ((k - 0.5) * 2).clamp(0.0, 1.0);
      if (soporte > 0) {
        final a = Colors.white.withValues(alpha: 0.2 * soporte);
        cv.drawLine(Offset(L / 2, marco.bottom), Offset(L / 2, marco.bottom + L * 0.07 * soporte), _trazo(a, L * 0.02));
        cv.drawLine(Offset(L / 2 - L * 0.09 * soporte, marco.bottom + L * 0.07 * soporte), Offset(L / 2 + L * 0.09 * soporte, marco.bottom + L * 0.07 * soporte), _trazo(a, L * 0.014));
      }
      final dentro = marco.deflate(w * 0.07);
      // la portada: arriba en vertical, a la izquierda en horizontal
      final q0 = dentro.width * 0.78, q1 = dentro.height * 0.74;
      final c0 = Rect.fromLTWH(dentro.center.dx - q0 / 2, dentro.top, q0, q0);
      final c1 = Rect.fromLTWH(dentro.left, dentro.center.dy - q1 / 2, q1, q1);
      final portada = Rect.lerp(c0, c1, k)!;
      cv.drawRRect(
        RRect.fromRectAndRadius(portada, Radius.circular(L * 0.02)),
        Paint()..shader = LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [c.acento, const Color(0xFF8B6CFF)]).createShader(portada),
      );
      _nota(cv, portada.center + Offset(-portada.width * 0.04, portada.height * 0.12), portada.width * 0.12, Colors.white.withValues(alpha: 0.9));
      // las filas: debajo en vertical, a la derecha en horizontal
      for (var i = 0; i < 3; i++) {
        final fv = Rect.fromLTWH(dentro.left, c0.bottom + dentro.height * 0.045 + i * dentro.height * 0.095, dentro.width * (1 - i * 0.18), dentro.height * 0.05);
        final x0 = c1.right + dentro.width * 0.04;
        final fh = Rect.fromLTWH(x0, dentro.center.dy - dentro.height * 0.22 + i * dentro.height * 0.17, (dentro.right - x0) * (1 - i * 0.2), dentro.height * 0.09);
        final f = Rect.lerp(fv, fh, k)!;
        cv.drawRRect(RRect.fromRectAndRadius(f, Radius.circular(L * 0.01)), Paint()..color = Colors.white.withValues(alpha: i == 0 ? 0.42 : 0.2));
      }
      // el ratón, que solo aparece en pantalla grande
      final vis = ((k - 0.55) * 2.2).clamp(0.0, 1.0);
      if (vis > 0) {
        final o = Offset(dentro.center.dx + dentro.width * 0.12 + sin(2 * pi * s / 6) * dentro.width * 0.12, dentro.bottom - dentro.height * 0.05);
        final flecha = Path()
          ..moveTo(o.dx, o.dy)
          ..lineTo(o.dx, o.dy + L * 0.07)
          ..lineTo(o.dx + L * 0.02, o.dy + L * 0.055)
          ..lineTo(o.dx + L * 0.04, o.dy + L * 0.085)
          ..lineTo(o.dx + L * 0.052, o.dy + L * 0.078)
          ..lineTo(o.dx + L * 0.034, o.dy + L * 0.05)
          ..lineTo(o.dx + L * 0.058, o.dy + L * 0.045)
          ..close();
        cv.drawPath(flecha, Paint()..color = Colors.white.withValues(alpha: vis));
        cv.drawPath(flecha, _trazo(Colors.black.withValues(alpha: 0.6 * vis), 1.2));
      }
    });

// ------------------------------------------------------------------- 11. final

Widget ilusFinal(Ctx c, double L) => Stack(alignment: Alignment.center, children: [
      Positioned.fill(
        child: _lienzo(c, L, (cv, z, s) {
          final ctr = Offset(L / 2, L * 0.5);
          final rad = L * (0.34 + 0.03 * _onda(s, 4));
          cv.drawCircle(ctr, rad, Paint()..shader = RadialGradient(colors: [c.acento.withValues(alpha: 0.38), c.acento.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: ctr, radius: rad)));
          const paleta = [Color(0xFFFFE08A), Color(0xFFFF5C8A), Color(0xFF8B6CFF), Color(0xFF2BD576), Color(0xFF67E8F9), Color(0xFFFF8A3D)];
          for (var i = 0; i < 24; i++) {
            final x0 = L * ((i * 0.381966) % 1);
            final p = ((s / 12) * (1 + i % 2) + (i * 0.173) % 1) % 1;
            final y = _lerp(-L * 0.05, L * 1.05, p);
            final x = x0 + sin(2 * pi * (s / 6 * (1 + i % 2) + i * 0.1)) * L * 0.03;
            final a = pow(sin(pi * p), 0.6).toDouble() * 0.7;
            final color = paleta[i % paleta.length].withValues(alpha: a);
            final giro = 2 * pi * (s / 12 * (1 + i % 3) + i * 0.1);
            if (i % 3 == 0) {
              _nota(cv, Offset(x, y), L * 0.022, color);
            } else {
              cv.save();
              cv.translate(x, y);
              cv.rotate(giro);
              cv.drawRRect(
                RRect.fromRectAndRadius(Rect.fromCenter(center: Offset.zero, width: L * 0.022, height: L * 0.011), Radius.circular(L * 0.004)),
                Paint()..color = color,
              );
              cv.restore();
            }
          }
        }),
      ),
      AnimatedBuilder(
        animation: c.reloj,
        builder: (_, _) => Transform.scale(
          scale: 1 + 0.04 * _onda(c.s, 4),
          child: SizedBox(width: L * 0.32, height: L * 0.32, child: logoConDestello(c, L * 0.32)),
        ),
      ),
    ]);

/// El color de cada diapositiva suele mezclarse con el acento: aquí un atajo.
Color mezclaAcento(Color c) => Color.lerp(c, C.acento, 0.35)!;
