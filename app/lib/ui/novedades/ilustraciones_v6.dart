// Ilustraciones de la quinta actualización grande (2.6.0). Es parte de
// ilustraciones.dart para usar sus utilidades (lienzo, ondas, estrellas...) y su
// reloj de 12 s: todo movimiento dura un divisor de 12 s y el bucle no salta.
part of 'ilustraciones.dart';

// ---------------------------------------------------------------- utilidades

/// Tamaño de letra que hace caber [t] en [ancho] sin pasar de [base].
double _ajusta6(String t, double base, double ancho) => min(base, ancho / _medir(t, 100) * 100);

/// Cuánto se ve una etapa de [dur] segundos en su segundo [t]: entra y sale suave.
double _entra6(double t, double dur) => _suave(_tramo(t, 0, 0.4)) * (1 - _suave(_tramo(t, dur - 0.35, dur)));

/// Pinta [f] como una etapa de un ciclo: aparece, se asienta y se desvanece.
void _etapa6(Canvas cv, Size z, Offset ctr, double t, double dur, void Function() f) {
  final a = _entra6(t, dur);
  if (a <= 0.001) return;
  cv.saveLayer(Offset.zero & z, Paint()..color = Colors.white.withValues(alpha: a));
  cv.translate(ctr.dx, ctr.dy);
  cv.scale(0.94 + 0.06 * _suave(_tramo(t, 0, 0.5)));
  cv.translate(-ctr.dx, -ctr.dy);
  f();
  cv.restore();
}

/// Una fila de botones redondos (uno por modo o ventaja); la [activa] se enciende.
void _pestanas6(Canvas cv, double L, List<IconData> iconos, List<Color> colores, int activa, double y, double s) {
  final n = iconos.length;
  final rad = L * 0.060, sep = L * 0.032;
  final total = n * 2 * rad + (n - 1) * sep;
  var x = L / 2 - total / 2 + rad;
  for (var i = 0; i < n; i++, x += 2 * rad + sep) {
    final o = Offset(x, y);
    final on = i == activa;
    final r = rad * (on ? 1.06 + 0.04 * _onda(s, 1.2) : 1);
    if (on) {
      cv.drawCircle(o, r * 1.45, Paint()..color = colores[i].withValues(alpha: 0.42)..maskFilter = MaskFilter.blur(BlurStyle.normal, r * 0.5));
    }
    cv.drawCircle(
        o,
        r,
        on
            ? _degradado(Rect.fromCircle(center: o, radius: r), [Color.lerp(colores[i], Colors.white, 0.25)!, colores[i]])
            : _relleno(Colors.white.withValues(alpha: 0.07)));
    cv.drawCircle(o, r, _trazo(Colors.white.withValues(alpha: on ? 0.5 : 0.2), 1.3));
    _icono(cv, iconos[i], o, r * 1.1, on ? const Color(0xFF0B0D12) : Colors.white.withValues(alpha: 0.62));
  }
}

/// El título y la frase de debajo de una etapa.
void _etiqueta6(Canvas cv, double L, String titulo, String frase, Color color, double a) {
  if (a <= 0.001) return;
  cv.saveLayer(Offset.zero & Size(L, L), Paint()..color = Colors.white.withValues(alpha: a));
  _txt(cv, titulo, Offset(L / 2, L * 0.815), _ajusta6(titulo, L * 0.062, L * 0.9), Colors.white, ancho: L * 0.92);
  _txt(cv, frase, Offset(L / 2, L * 0.885), _ajusta6(frase, L * 0.034, L * 0.9), Color.lerp(color, Colors.white, 0.35)!,
      peso: FontWeight.w700, ancho: L * 0.92);
  cv.restore();
}

/// Una insignia con un punto de color y su texto (la calidad real del audio).
Rect _insignia6(Canvas cv, String t, Offset ctr, double tam, Color color, {Color punto = const Color(0xFF2BD576)}) {
  final w = _medir(t, tam) + tam * 3.2;
  final r = Rect.fromCenter(center: ctr, width: w, height: tam * 2.3);
  cv.drawRRect(_caja(r, 99), _relleno(color.withValues(alpha: 0.16)));
  cv.drawRRect(_caja(r, 99), _trazo(color.withValues(alpha: 0.85), 1.3));
  cv.drawCircle(Offset(r.left + tam * 1.15, r.center.dy), tam * 0.34, _relleno(punto));
  _txtIzq(cv, t, Offset(r.left + tam * 2.0, r.center.dy), tam, Colors.white, ancho: w - tam * 2.4);
  return r;
}

/// Una carátula de ejemplo: degradado, sol y montañas, recortada con esquinas.
void _caratula6(Canvas cv, Rect r, List<Color> col, double radio) {
  cv.save();
  cv.clipRRect(_caja(r, radio));
  cv.drawRect(r, _degradado(r, col, ini: Alignment.topLeft, fin: Alignment.bottomRight));
  cv.drawCircle(Offset(r.left + r.width * 0.68, r.top + r.height * 0.34), r.width * 0.14, _relleno(Colors.white.withValues(alpha: 0.85)));
  final m = Path()
    ..moveTo(r.left, r.bottom)
    ..lineTo(r.left, r.top + r.height * 0.78)
    ..lineTo(r.left + r.width * 0.32, r.top + r.height * 0.56)
    ..lineTo(r.left + r.width * 0.60, r.top + r.height * 0.80)
    ..lineTo(r.right, r.top + r.height * 0.64)
    ..lineTo(r.right, r.bottom)
    ..close();
  cv.drawPath(m, _relleno(Colors.black.withValues(alpha: 0.30)));
  cv.restore();
  cv.drawRRect(_caja(r, radio), _trazo(Colors.white.withValues(alpha: 0.25), 1.2));
}

/// Confeti que cae: [n] trocitos de colores, un ciclo exacto cada 12 s.
void _confeti6(Canvas cv, double L, double s, int n, {double alfa = 0.9}) {
  const paleta = [Color(0xFFFFE08A), Color(0xFFFF5C8A), Color(0xFF8B6CFF), Color(0xFF2BD576), Color(0xFF67E8F9), Color(0xFFFF8A3D)];
  for (var i = 0; i < n; i++) {
    final x0 = L * (0.04 + ((i * 0.381966) % 1) * 0.92);
    final p = ((s / 12) * (1 + i % 2) + (i * 0.173) % 1) % 1;
    final y = _lerp(-L * 0.04, L * 1.04, p);
    final x = x0 + sin(2 * pi * (s / 6 * (1 + i % 2) + i * 0.1)) * L * 0.03;
    final giro = 2 * pi * (s / 3 * (1 + i % 3) + i * 0.17);
    cv.save();
    cv.translate(x, y);
    cv.rotate(giro);
    cv.scale(1, 0.35 + 0.65 * cos(giro * 0.7).abs());
    cv.drawRRect(_caja(Rect.fromCenter(center: Offset.zero, width: L * 0.022, height: L * 0.012), 1.5),
        _relleno(paleta[i % paleta.length].withValues(alpha: alfa)));
    cv.restore();
  }
}

/// La mascota de Caudal con vida: [ojos] (1 abiertos, 0 cerrados), [boca]
/// (0 sonrisa, 1 cantando) y [gorro] (0 sin gorrito, 1 puesto).
void _mascota6(Canvas cv, Offset o, double r, Color color,
    {double fase = 0, double ojos = 1, double boca = 0, double gorro = 0, double alzar = 0.35}) {
  final oscuro = Color.lerp(color, Colors.black, 0.45)!;
  final claro = Color.lerp(color, Colors.white, 0.35)!;
  const tinta = Color(0xFF1B1030);
  const rosa = Color(0xFFFF9EC4);
  cv.drawOval(Rect.fromCenter(center: o + Offset(0, r * 1.28), width: r * 1.5, height: r * 0.26),
      Paint()..color = Colors.black.withValues(alpha: 0.35)..maskFilter = MaskFilter.blur(BlurStyle.normal, r * 0.12));
  final brazo = _trazo(oscuro, r * 0.2);
  cv.drawLine(o + Offset(-r * 0.7, r * 0.55), o + Offset(-r * 1.0, r * (0.2 + alzar * sin(fase))), brazo);
  cv.drawLine(o + Offset(r * 0.7, r * 0.55), o + Offset(r * 1.0, r * (0.2 + alzar * sin(fase + pi))), brazo);
  final cuerpo = Rect.fromCenter(center: o + Offset(0, r * 0.85), width: r * 1.4, height: r * 0.95);
  cv.drawOval(cuerpo, _degradado(cuerpo, [color, oscuro], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
  for (final lado in const [-1.0, 1.0]) {
    final oreja = Path()
      ..moveTo(o.dx + lado * r * 0.30, o.dy - r * 0.82)
      ..lineTo(o.dx + lado * r * 0.78, o.dy - r * 1.28)
      ..lineTo(o.dx + lado * r * 0.98, o.dy - r * 0.38)
      ..close();
    cv.drawPath(oreja, _relleno(color));
    final dentro = Path()
      ..moveTo(o.dx + lado * r * 0.45, o.dy - r * 0.78)
      ..lineTo(o.dx + lado * r * 0.77, o.dy - r * 1.06)
      ..lineTo(o.dx + lado * r * 0.88, o.dy - r * 0.52)
      ..close();
    cv.drawPath(dentro, _relleno(rosa));
  }
  final cab = Rect.fromCircle(center: o, radius: r);
  cv.drawCircle(o, r, _degradado(cab, [claro, color], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
  for (final lado in const [-1.0, 1.0]) {
    final ojo = o + Offset(lado * r * 0.38, r * 0.05);
    if (ojos > 0.2) {
      cv.drawOval(Rect.fromCenter(center: ojo, width: r * 0.26, height: r * 0.34 * ojos), _relleno(tinta));
      if (ojos > 0.6) cv.drawCircle(ojo + Offset(-r * 0.04, -r * 0.07), r * 0.06, _relleno(Colors.white));
    } else {
      cv.drawArc(Rect.fromCenter(center: ojo + Offset(0, -r * 0.03), width: r * 0.30, height: r * 0.20), 0.2, pi - 0.4, false,
          _trazo(tinta, r * 0.07));
    }
    cv.drawCircle(o + Offset(lado * r * 0.62, r * 0.36), r * 0.12, _relleno(rosa.withValues(alpha: 0.7)));
  }
  if (boca > 0.15) {
    final b = Rect.fromCenter(center: o + Offset(0, r * 0.36), width: r * 0.30, height: r * (0.10 + 0.26 * boca));
    cv.drawOval(b, _relleno(tinta));
    cv.drawOval(Rect.fromCenter(center: b.center + Offset(0, b.height * 0.22), width: b.width * 0.6, height: b.height * 0.4),
        _relleno(const Color(0xFFFF6F9C)));
  } else {
    cv.drawArc(Rect.fromCenter(center: o + Offset(0, r * 0.30), width: r * 0.34, height: r * 0.24), 0.2, pi - 0.4, false, _trazo(tinta, r * 0.06));
  }
  if (gorro > 0.01) {
    cv.save();
    cv.translate(o.dx + r * 0.05, o.dy - r * 0.84 - (1 - gorro) * r * 0.9);
    cv.rotate(0.14);
    cv.scale(gorro);
    final cono = Path()
      ..moveTo(-r * 0.36, 0)
      ..lineTo(r * 0.02, -r * 0.95)
      ..lineTo(r * 0.36, 0)
      ..close();
    cv.drawPath(cono, _degradado(Rect.fromLTRB(-r * 0.36, -r * 0.95, r * 0.36, 0), const [Color(0xFFFF5C8A), Color(0xFF8B6CFF)],
        ini: Alignment.topCenter, fin: Alignment.bottomCenter));
    for (final (dx, dy) in [(-0.14, -0.18), (0.10, -0.34), (-0.02, -0.58)]) {
      cv.drawCircle(Offset(r * dx, r * dy), r * 0.045, _relleno(const Color(0xFFFFE08A)));
    }
    cv.drawRRect(_caja(Rect.fromCenter(center: Offset(0, 0), width: r * 0.76, height: r * 0.09), r * 0.045), _relleno(const Color(0xFFFFE08A)));
    cv.drawCircle(Offset(r * 0.02, -r * 0.95), r * 0.10, _relleno(const Color(0xFFFFE08A)));
    cv.restore();
  }
}

// ------------------------------------------------------------------ portada

Widget ilusPortada6(Ctx c, double L) {
  return Stack(alignment: Alignment.center, children: [
    Positioned.fill(
      child: _lienzo(c, L, (cv, z, s) {
        final ctr = Offset(L / 2, L * 0.46);
        for (var i = 0; i < 3; i++) {
          final p = ((s / 4) + i / 3) % 1;
          cv.drawCircle(ctr, L * (0.20 + 0.34 * p), _trazo(c.acento.withValues(alpha: (1 - p) * 0.35), 1.6));
        }
        _confeti6(cv, L, s, 16, alfa: 0.7);
        final caja = Rect.fromCircle(center: ctr, radius: L * 0.30);
        cv.drawCircle(
          ctr,
          L * 0.30,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = L * 0.012
            ..shader = SweepGradient(
              colors: const [Color(0xFF22D3EE), Color(0xFF8B6CFF), Color(0xFFFF5C8A), Color(0xFF22D3EE)],
              transform: GradientRotation(2 * pi * s / 12),
            ).createShader(caja),
        );
        // las tres novedades orbitan: reproductor, perfil y celebración
        const iconos = [Icons.album_rounded, Icons.account_circle_rounded, Icons.cake_rounded];
        const colores = [
          [Color(0xFF22D3EE), Color(0xFF8B6CFF)],
          [Color(0xFFFF9EC4), Color(0xFFFF5C8A)],
          [Color(0xFFFFE08A), Color(0xFFD99A12)],
        ];
        for (var i = 0; i < 3; i++) {
          final ang = 2 * pi * (i / 3 + s / 12) - pi / 2;
          final o = ctr + Offset(cos(ang) * L * 0.37, sin(ang) * L * 0.30);
          final rad = L * 0.075;
          cv.drawCircle(o + Offset(0, L * 0.01), rad,
              Paint()..color = Colors.black.withValues(alpha: 0.35)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.016));
          cv.drawCircle(o, rad, _degradado(Rect.fromCircle(center: o, radius: rad), colores[i]));
          _icono(cv, iconos[i], o, rad * 1.15, i == 2 ? const Color(0xFF3A2800) : Colors.white);
        }
        for (var i = 0; i < 6; i++) {
          final ang = 2 * pi * (i / 6 + s / 12) + 0.4;
          final o = ctr + Offset(cos(ang) * L * 0.44, sin(ang) * L * 0.40);
          _estrella(cv, o, L * (0.008 + 0.020 * _onda(s, 3, i / 6)), const Color(0xFFFFE08A));
        }
        _chip(cv, 'CAUDAL 2.6.0', Offset(L / 2, L * 0.90), L * 0.036, c.acento, activo: 0.15 + 0.15 * _onda(s, 4));
      }),
    ),
    Align(
      alignment: const Alignment(0, -0.08),
      child: AnimatedBuilder(
        animation: c.reloj,
        builder: (_, _) => Transform.scale(
          scale: 1 + 0.03 * _onda(c.s, 4),
          child: Container(
            width: L * 0.36,
            height: L * 0.36,
            decoration: BoxDecoration(shape: BoxShape.circle, boxShadow: [
              BoxShadow(color: c.acento.withValues(alpha: 0.45), blurRadius: L * 0.14, spreadRadius: L * 0.01),
            ]),
            child: _Destello(c: c, child: _logo(L * 0.36)),
          ),
        ),
      ),
    ),
  ]);
}

// ------------------------------------------------- tu reproductor, a tu estilo

void _vinilo6(Canvas cv, Offset o, double R, List<Color> col, double s) {
  cv.drawCircle(o + Offset(0, R * 0.08), R, Paint()..color = Colors.black.withValues(alpha: 0.5)..maskFilter = MaskFilter.blur(BlurStyle.normal, R * 0.12));
  final disco = Rect.fromCircle(center: o, radius: R);
  cv.drawCircle(o, R, _degradado(disco, const [Color(0xFF23252E), Color(0xFF08090C)]));
  for (var k = 0; k < 6; k++) {
    cv.drawCircle(o, R * (0.50 + 0.085 * k), _trazo(Colors.white.withValues(alpha: 0.06), 1));
  }
  cv.drawArc(Rect.fromCircle(center: o, radius: R * 0.82), -1.0, 0.55, false, _trazo(Colors.white.withValues(alpha: 0.16), R * 0.05));
  cv.drawArc(Rect.fromCircle(center: o, radius: R * 0.82), 2.14, 0.55, false, _trazo(Colors.white.withValues(alpha: 0.16), R * 0.05));
  // la etiqueta gira entera cada 3 s
  cv.save();
  cv.translate(o.dx, o.dy);
  cv.rotate(2 * pi * s / 3);
  final et = Rect.fromCircle(center: Offset.zero, radius: R * 0.38);
  cv.drawCircle(Offset.zero, R * 0.38, _degradado(et, col));
  cv.drawCircle(Offset(R * 0.22, 0), R * 0.045, _relleno(Colors.white.withValues(alpha: 0.9)));
  _nota(cv, Offset(-R * 0.14, R * 0.06), R * 0.12, Colors.white.withValues(alpha: 0.9));
  cv.restore();
  cv.drawCircle(o, R * 0.04, _relleno(const Color(0xFF0B0D12)));
  // el brazo con la aguja
  final pivote = o + Offset(R * 1.02, -R * 0.92);
  cv.drawCircle(pivote, R * 0.13, _relleno(const Color(0xFF4A4F5E)));
  cv.drawCircle(pivote, R * 0.13, _trazo(Colors.white.withValues(alpha: 0.3), 1.2));
  final punta = o + Offset(R * 0.46, R * 0.14);
  cv.drawLine(pivote, punta, _trazo(const Color(0xFFC9CEDB), R * 0.06));
  cv.drawCircle(punta, R * 0.055, _relleno(const Color(0xFFF5C542)));
}

void _casete6(Canvas cv, Offset o, double W, List<Color> col, double s) {
  final H = W * 0.64;
  final cuerpo = Rect.fromCenter(center: o, width: W, height: H);
  cv.drawRRect(_caja(cuerpo, W * 0.06).shift(Offset(0, W * 0.04)),
      Paint()..color = Colors.black.withValues(alpha: 0.45)..maskFilter = MaskFilter.blur(BlurStyle.normal, W * 0.05));
  cv.drawRRect(_caja(cuerpo, W * 0.06),
      _degradado(cuerpo, const [Color(0xFF3C404E), Color(0xFF171920)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
  cv.drawRRect(_caja(cuerpo, W * 0.06), _trazo(Colors.white.withValues(alpha: 0.22), 1.3));
  final et = Rect.fromLTWH(cuerpo.left + W * 0.05, cuerpo.top + H * 0.07, W * 0.90, H * 0.50);
  cv.drawRRect(_caja(et, W * 0.03), _degradado(et, col));
  _txtIzq(cv, 'MI MEZCLA', Offset(et.left + W * 0.05, et.top + H * 0.12), W * 0.075, Colors.white, ancho: W * 0.6);
  cv.drawLine(Offset(et.left + W * 0.05, et.top + H * 0.23), Offset(et.right - W * 0.05, et.top + H * 0.23),
      _trazo(Colors.white.withValues(alpha: 0.55), 1.2));
  // la ventanita con los dos carretes
  final ven = Rect.fromCenter(center: Offset(o.dx, et.bottom - H * 0.07), width: W * 0.60, height: H * 0.30);
  cv.drawRRect(_caja(ven, ven.height * 0.5), _relleno(const Color(0xFF0B0D12)));
  cv.drawRRect(_caja(ven, ven.height * 0.5), _trazo(Colors.white.withValues(alpha: 0.25), 1.2));
  for (final lado in const [-1.0, 1.0]) {
    final ctr = Offset(ven.center.dx + lado * W * 0.19, ven.center.dy);
    final cinta = ven.height * (lado < 0 ? 0.46 : 0.36);
    cv.drawCircle(ctr, cinta, _relleno(const Color(0xFF3B2A1E)));
    cv.drawCircle(ctr, ven.height * 0.27, _relleno(const Color(0xFFE8E9EE)));
    cv.drawCircle(ctr, ven.height * 0.11, _relleno(const Color(0xFF0B0D12)));
    for (var k = 0; k < 6; k++) {
      final a = 2 * pi * (k / 6 + s / 3);
      cv.drawLine(ctr + Offset(cos(a), sin(a)) * ven.height * 0.11, ctr + Offset(cos(a), sin(a)) * ven.height * 0.26,
          _trazo(const Color(0xFF0B0D12), 2));
    }
  }
  final base = Path()
    ..moveTo(cuerpo.center.dx - W * 0.30, cuerpo.bottom)
    ..lineTo(cuerpo.center.dx - W * 0.21, cuerpo.bottom - H * 0.20)
    ..lineTo(cuerpo.center.dx + W * 0.21, cuerpo.bottom - H * 0.20)
    ..lineTo(cuerpo.center.dx + W * 0.30, cuerpo.bottom)
    ..close();
  cv.drawPath(base, _relleno(const Color(0xFF0B0D12).withValues(alpha: 0.7)));
  for (final lado in const [-1.0, 1.0]) {
    cv.drawCircle(Offset(cuerpo.center.dx + lado * W * 0.12, cuerpo.bottom - H * 0.10), W * 0.014, _relleno(Colors.white.withValues(alpha: 0.35)));
    cv.drawCircle(Offset(cuerpo.center.dx + lado * W * 0.43, cuerpo.bottom - H * 0.09), W * 0.016, _relleno(Colors.white.withValues(alpha: 0.28)));
  }
}

void _neon6(Canvas cv, Offset o, double R, List<Color> col, double s) {
  final anillo = Rect.fromCircle(center: o, radius: R);
  cv.drawCircle(o, R, _relleno(const Color(0xFF0B0D12)));
  final barrido = SweepGradient(colors: [col[0], col[1], const Color(0xFFFF5C8A), col[0]], transform: GradientRotation(2 * pi * s / 3)).createShader(anillo);
  cv.drawCircle(o, R, Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = R * 0.14
    ..shader = barrido
    ..maskFilter = MaskFilter.blur(BlurStyle.normal, R * 0.12));
  cv.drawCircle(o, R, Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = R * 0.07
    ..shader = barrido);
  const n = 40;
  for (var i = 0; i < n; i++) {
    final ang = 2 * pi * i / n - pi / 2;
    final amp = 0.2 + 0.8 * _onda(s, 1.5, i * 0.071);
    final r0 = R * 1.12, r1 = r0 + R * 0.32 * amp;
    cv.drawLine(o + Offset(cos(ang), sin(ang)) * r0, o + Offset(cos(ang), sin(ang)) * r1,
        _trazo(Color.lerp(col[0], col[1], i / n)!.withValues(alpha: 0.95), R * 0.06));
  }
  final centro = Rect.fromCircle(center: o, radius: R * 0.78);
  cv.drawCircle(o, R * 0.78, _degradado(centro, col));
  cv.drawCircle(o, R * 0.78, _trazo(Colors.white.withValues(alpha: 0.35), 1.2));
  _nota(cv, o + Offset(-R * 0.08, R * 0.16), R * 0.26, Colors.white.withValues(alpha: 0.92));
}

void _flotante6(Canvas cv, Offset o, double lado, List<Color> col, double s) {
  final bob = lado * 0.045 * sin(2 * pi * s / 3);
  final cuadro = Rect.fromCenter(center: o + Offset(0, -bob), width: lado, height: lado);
  final sombra = Rect.fromCenter(center: Offset(o.dx, o.dy + lado * 0.64), width: lado * (0.78 - 0.06 * sin(2 * pi * s / 3)), height: lado * 0.12);
  cv.drawOval(sombra, Paint()..color = Colors.black.withValues(alpha: 0.4)..maskFilter = MaskFilter.blur(BlurStyle.normal, lado * 0.05));
  cv.drawRRect(_caja(cuadro, lado * 0.09).shift(Offset(0, lado * 0.03)),
      Paint()..color = col[0].withValues(alpha: 0.45)..maskFilter = MaskFilter.blur(BlurStyle.normal, lado * 0.10));
  _caratula6(cv, cuadro, col, lado * 0.09);
  // la mascota se sienta en la esquina y mueve los bracitos
  final r = lado * 0.20;
  _mascota6(cv, Offset(cuadro.right - r * 1.35, cuadro.top - r * 0.95), r, const Color(0xFFB4A1FF),
      fase: 2 * pi * s / 1.5);
}

Widget ilusReproductor(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      const cols = [
        [Color(0xFFFF7BAC), Color(0xFFFF8A3D)],
        [Color(0xFF22D3EE), Color(0xFF8B6CFF)],
        [Color(0xFF34D399), Color(0xFF22D3EE)],
        [Color(0xFFF5C542), Color(0xFFFF5C8A)],
      ];
      const nombres = ['Vinilo', 'Casete', 'Neón', 'Carátula'];
      const calidad = ['FLAC 24-bit · 96 kHz', 'MP3 320 kbps', 'AAC 256 kbps', 'FLAC 16-bit · 44,1 kHz'];
      final idx = (s ~/ 3) % 4;
      final t = s - (s ~/ 3) * 3;
      final tinte = Color.lerp(cols[(idx + 3) % 4][0], cols[idx][0], _suave(_tramo(t, 0, 0.6)))!;
      final ctr = Offset(L / 2, L * 0.50);
      cv.drawCircle(ctr, L * 0.44,
          Paint()..shader = RadialGradient(colors: [tinte.withValues(alpha: 0.40), tinte.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: ctr, radius: L * 0.44)));
      _filaChips(cv, L, nombres, L * 0.075, L * 0.031, [for (final k in cols) k[0]], idx);
      _etapa6(cv, z, ctr, t, 3, () {
        switch (idx) {
          case 0:
            _vinilo6(cv, ctr, L * 0.23, cols[0], s);
          case 1:
            _casete6(cv, ctr, L * 0.64, cols[1], s);
          case 2:
            _neon6(cv, ctr, L * 0.20, cols[2], s);
          default:
            _flotante6(cv, ctr + Offset(0, L * 0.01), L * 0.36, cols[3], s);
        }
      });
      // la insignia con la calidad real de la canción
      final a = _entra6(t, 3);
      if (a > 0.001) {
        cv.saveLayer(Offset.zero & z, Paint()..color = Colors.white.withValues(alpha: a));
        _insignia6(cv, calidad[idx], Offset(L / 2, L * 0.905), L * 0.032, cols[idx][0]);
        cv.restore();
      }
    });

// ------------------------------------------------------------ modo karaoke

Widget ilusKaraoke(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      const frases = ['Canta conmigo', 'Hasta el amanecer', 'Una vez más'];
      final panel = Rect.fromLTWH(L * 0.07, L * 0.04, L * 0.86, L * 0.68);
      cv.drawRRect(_caja(panel, L * 0.05), _degradado(panel, [Color.lerp(c.acento, const Color(0xFF1B1F27), 0.78)!, const Color(0xFF0B0D12)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
      cv.drawRRect(_caja(panel, L * 0.05), _trazo(c.acento.withValues(alpha: 0.45), 1.4));
      _icono(cv, Icons.mic_rounded, Offset(panel.left + L * 0.065, panel.top + L * 0.058), L * 0.05, c.acento);
      _txtIzq(cv, 'MODO KARAOKE', Offset(panel.left + L * 0.115, panel.top + L * 0.058), L * 0.032, Color.lerp(c.acento, Colors.white, 0.3)!, ancho: L * 0.5);

      // la letra se desplaza: cada frase se llena de izquierda a derecha en 4 s
      final k = (s ~/ 4) % 3;
      final local = s - (s ~/ 4) * 4;
      final pos = k + _suave(_tramo(local, 3.5, 4));
      final progreso = _tramo(local, 0.3, 3.3);
      final cy = panel.top + L * 0.31;
      cv.save();
      cv.clipRRect(_caja(panel.deflate(2), L * 0.05));
      for (var j = k - 1; j <= k + 1; j++) {
        final d = j - pos;
        final ad = d.abs().clamp(0.0, 1.0);
        final t = frases[(j % 3 + 3) % 3];
        final tam = _lerp(_ajusta6(t, L * 0.10, L * 0.74), _ajusta6(t, L * 0.052, L * 0.74), ad);
        final p = j < k ? 1.0 : (j == k ? progreso : 0.0);
        final o = Offset(L / 2, cy + d * L * 0.17);
        _txtRelleno6(cv, t, o, tam, p, Colors.white.withValues(alpha: _lerp(0.62, 0.30, ad)), c.acento);
      }
      cv.restore();
      // la barra de la canción
      final pista = Rect.fromLTWH(L * 0.13, panel.bottom - L * 0.055, L * 0.74, L * 0.012);
      cv.drawRRect(_caja(pista, 99), _relleno(Colors.white.withValues(alpha: 0.18)));
      final llena = Rect.fromLTWH(pista.left, pista.top, pista.width * (s / 12), pista.height);
      cv.drawRRect(_caja(llena, 99), _relleno(c.acento));
      cv.drawCircle(Offset(llena.right, pista.center.dy), L * 0.012, _relleno(Colors.white));

      // la mascota canta con el micrófono
      final ctr = Offset(L * 0.50, L * 0.855);
      final r = L * 0.066;
      final abre = _onda(s, 0.75);
      for (var i = 0; i < 3; i++) {
        final p = ((s / 3) + i / 3) % 1;
        _nota(cv, ctr + Offset(r * (1.5 + i * 0.9) + sin(2 * pi * (s / 3 + i * 0.2)) * r * 0.3, -r * 0.4 - p * r * 1.35), L * 0.019,
            Color.lerp(c.acento, Colors.white, 0.4)!.withValues(alpha: sin(pi * p).clamp(0.0, 1.0) * 0.9));
        _nota(cv, ctr + Offset(-r * (1.5 + i * 0.9) - sin(2 * pi * (s / 3 + i * 0.3)) * r * 0.3, -r * 0.2 - ((p + 0.5) % 1) * r * 1.35), L * 0.016,
            Color.lerp(c.acento, Colors.white, 0.4)!.withValues(alpha: sin(pi * ((p + 0.5) % 1)).clamp(0.0, 1.0) * 0.8));
      }
      cv.save();
      cv.translate(ctr.dx, ctr.dy - r * 0.15 * abre);
      cv.rotate(0.06 * sin(2 * pi * s / 1.5));
      _mascota6(cv, Offset.zero, r, Color.lerp(c.acento, const Color(0xFFB4A1FF), 0.5)!, fase: 2 * pi * s / 1.5, boca: abre, alzar: 0.15);
      cv.restore();
      _icono(cv, Icons.mic_rounded, ctr + Offset(r * 0.85, r * 0.72), L * 0.062, Colors.white);
    });

/// Texto que se llena con [color] de izquierda a derecha hasta [p] (0 a 1).
void _txtRelleno6(Canvas cv, String t, Offset ctr, double tam, double p, Color tenue, Color color) {
  final w = _medir(t, tam);
  _txt(cv, t, ctr, tam, tenue, ancho: w + 4);
  if (p <= 0) return;
  cv.save();
  cv.clipRect(Rect.fromLTRB(ctr.dx - w / 2 - 3, ctr.dy - tam * 1.2, ctr.dx - w / 2 - 3 + (w + 6) * p, ctr.dy + tam * 1.2));
  _txt(cv, t, ctr, tam, color.withValues(alpha: 0.6), ancho: w + 4, resplandor: tam * 0.25);
  _txt(cv, t, ctr, tam, Color.lerp(color, Colors.white, 0.35)!, ancho: w + 4);
  cv.restore();
}

// ------------------------------------------------------ mascotas con vida

Widget ilusMascotasVida(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      // 0 canción movida, 1 canción tranquila, 2 en pausa (se duerme), 3 fiesta
      final idx = (s ~/ 3) % 4;
      final t = s - (s ~/ 3) * 3;
      const tintes = [Color(0xFFFF7BAC), Color(0xFF38BDF8), Color(0xFF6D5BD0), Color(0xFFF5C542)];
      const estados = ['Canción movida', 'Canción tranquila', 'En pausa: a dormir', '¡Fiesta!'];
      const bpm = ['120 BPM', '60 BPM', 'En pausa', '120 BPM'];
      final tinte = Color.lerp(tintes[(idx + 3) % 4], tintes[idx], _suave(_tramo(t, 0, 0.6)))!;
      final ctr = Offset(L / 2, L * 0.46);
      final r = L * 0.135;
      cv.drawCircle(ctr, L * 0.42,
          Paint()..shader = RadialGradient(colors: [tinte.withValues(alpha: 0.42), tinte.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: ctr, radius: L * 0.42)));
      if (idx == 3) _confeti6(cv, L, s, 18, alfa: 0.85);
      // el estado de la canción
      _chip(cv, estados[idx], Offset(L / 2, L * 0.085), L * 0.034, tinte, activo: 0.2);
      // el suelo
      cv.drawOval(Rect.fromCenter(center: Offset(L / 2, ctr.dy + r * 1.32), width: r * 2.6, height: r * 0.40),
          Paint()..color = Colors.black.withValues(alpha: 0.30)..maskFilter = MaskFilter.blur(BlurStyle.normal, r * 0.1));

      final per = (idx == 1) ? 1.0 : 0.5;
      final latido = ((s % per) / per);
      final beat = sin(pi * latido).abs();
      if (idx == 0 || idx == 3) {
        // un anillo por cada compás
        cv.drawOval(Rect.fromCenter(center: Offset(L / 2, ctr.dy + r * 1.30), width: r * (1.6 + 2.4 * latido), height: r * (0.30 + 0.45 * latido)), _trazo(tinte.withValues(alpha: (1 - latido) * 0.6), 2));
        for (var i = 0; i < 3; i++) {
          final p = ((s / 1.5) + i / 3) % 1;
          _nota(cv, ctr + Offset((i - 1) * r * 1.7, -r * 1.30 - p * r * 0.75), L * 0.018,
              Color.lerp(tinte, Colors.white, 0.45)!.withValues(alpha: sin(pi * p).clamp(0.0, 1.0) * 0.85));
        }
      }
      final ojos = idx == 2 ? 1 - _suave(_tramo(t, 0.15, 0.6)) : (idx == 3 ? _suave(_tramo(t, 0.0, 0.3)) : 1.0);
      final gorro = idx == 3 ? _suave(_tramo(t, 0.2, 0.7)) : 0.0;
      cv.save();
      if (idx == 2) {
        final resp = 1 + 0.022 * sin(2 * pi * s / 3);
        cv.translate(ctr.dx, ctr.dy + r * 1.3);
        cv.scale(1, resp);
        cv.rotate(0.05);
        cv.translate(-ctr.dx, -(ctr.dy + r * 1.3));
        _mascota6(cv, ctr, r, const Color(0xFFB4A1FF), ojos: ojos, alzar: 0.04);
      } else if (idx == 1) {
        cv.translate(ctr.dx, ctr.dy + r * 1.3);
        cv.rotate(0.13 * sin(2 * pi * s / 2));
        cv.translate(-ctr.dx, -(ctr.dy + r * 1.3));
        _mascota6(cv, ctr + Offset(0, -r * 0.06 * beat), r, const Color(0xFFB4A1FF), fase: 2 * pi * s / 2, alzar: 0.3);
      } else {
        cv.translate(ctr.dx, ctr.dy + r * 1.3 - r * 0.30 * beat);
        cv.scale(1 - 0.03 * beat, 1 + 0.07 * beat);
        cv.translate(-ctr.dx, -(ctr.dy + r * 1.3));
        _mascota6(cv, ctr, r, const Color(0xFFB4A1FF),
            fase: 2 * pi * s / per, ojos: ojos, gorro: gorro, boca: idx == 3 ? 0.5 * beat : 0, alzar: 0.45);
      }
      cv.restore();
      if (idx == 2) {
        final fade = _entra6(t, 3);
        _icono(cv, Icons.bedtime_rounded, Offset(L * 0.82, L * 0.22), L * 0.095, const Color(0xFFFFE08A).withValues(alpha: fade));
        for (var i = 0; i < 3; i++) {
          final p = ((s / 3) + i / 3) % 1;
          _txt(cv, 'z', ctr + Offset(r * 1.0 + p * r * 0.9, -r * 0.2 - p * r * 1.0), L * (0.036 + 0.018 * i), Colors.white.withValues(alpha: sin(pi * p).clamp(0.0, 1.0) * 0.9 * fade));
        }
        for (var i = 0; i < 5; i++) {
          _estrella(cv, Offset(L * (0.14 + 0.15 * i), L * (0.16 + 0.07 * ((i * 3) % 4))), L * (0.008 + 0.012 * _onda(s, 1.5, i * 0.2)), const Color(0xFFFFE08A).withValues(alpha: 0.9 * fade));
        }
      }
      // el reproductor de abajo
      final barra = Rect.fromCenter(center: Offset(L / 2, L * 0.835), width: L * 0.76, height: L * 0.105);
      cv.drawRRect(_caja(barra, 99), _relleno(Colors.white.withValues(alpha: 0.07)));
      cv.drawRRect(_caja(barra, 99), _trazo(tinte.withValues(alpha: 0.6), 1.3));
      final boton = Offset(barra.left + L * 0.062, barra.center.dy);
      cv.drawCircle(boton, L * 0.036, _relleno(tinte));
      _icono(cv, idx == 2 ? Icons.play_arrow_rounded : Icons.pause_rounded, boton, L * 0.05, const Color(0xFF0B0D12));
      const n = 14;
      for (var i = 0; i < n; i++) {
        final h = idx == 2 ? 0.10 : 0.22 + 0.78 * _onda(s, per, i * 0.09);
        final x = barra.left + L * 0.145 + i * L * 0.0305;
        cv.drawLine(Offset(x, barra.center.dy - L * 0.032 * h), Offset(x, barra.center.dy + L * 0.032 * h),
            _trazo(Color.lerp(tinte, Colors.white, 0.3)!.withValues(alpha: idx == 2 ? 0.4 : 0.95), L * 0.009));
      }
      _txtIzq(cv, bpm[idx], Offset(barra.right - L * 0.19, barra.center.dy), _ajusta6(bpm[idx], L * 0.034, L * 0.165), Colors.white, ancho: L * 0.17);
    });

// ------------------------------------------------------------ cumpleaños

Widget ilusCumple(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      _confeti6(cv, L, s, 22);
      // banderines
      const bandera = [Color(0xFFFF5C8A), Color(0xFFFFE08A), Color(0xFF22D3EE), Color(0xFF8B6CFF), Color(0xFF2BD576)];
      final cuerda = Path()..moveTo(-L * 0.02, L * 0.030)..quadraticBezierTo(L / 2, L * 0.115, L * 1.02, L * 0.030);
      cv.drawPath(cuerda, _trazo(Colors.white.withValues(alpha: 0.45), 1.4));
      for (var i = 0; i < 11; i++) {
        final u = (i + 0.5) / 11;
        final x = L * (-0.02 + 1.04 * u);
        final y = L * 0.030 + (L * 0.085 * 2 * u * (1 - u)) * 1.0;
        final b = Path()..moveTo(x - L * 0.022, y)..lineTo(x + L * 0.022, y)..lineTo(x, y + L * 0.055 + 0.004 * L * sin(2 * pi * (s / 3 + i * 0.1)))..close();
        cv.drawPath(b, _relleno(bandera[i % bandera.length]));
      }
      // el saludo
      const saludo = '¡Feliz cumpleaños!';
      final tam = _ajusta6(saludo, L * 0.082, L * 0.88);
      _txt(cv, saludo, Offset(L / 2, L * 0.215), tam, const Color(0xFFF5C542).withValues(alpha: 0.6), ancho: L * 0.9, resplandor: tam * 0.3);
      _txt(cv, saludo, Offset(L / 2, L * 0.215), tam, const Color(0xFFFFE08A), ancho: L * 0.9);

      // la tarta
      final cx = L * 0.34;
      cv.drawOval(Rect.fromCenter(center: Offset(cx, L * 0.755), width: L * 0.46, height: L * 0.07), _relleno(const Color(0xFFDCE0EA)));
      cv.drawOval(Rect.fromCenter(center: Offset(cx, L * 0.745), width: L * 0.46, height: L * 0.07), _relleno(const Color(0xFFF5F6FA)));
      final base = Rect.fromCenter(center: Offset(cx, L * 0.675), width: L * 0.36, height: L * 0.115);
      cv.drawRRect(_caja(base, L * 0.025), _degradado(base, const [Color(0xFFFF7BAC), Color(0xFFD83A78)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
      final medio = Rect.fromCenter(center: Offset(cx, L * 0.575), width: L * 0.26, height: L * 0.095);
      cv.drawRRect(_caja(medio, L * 0.022), _degradado(medio, const [Color(0xFFFFE08A), Color(0xFFE8A93A)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
      // el glaseado con gotas
      for (final (caja, color) in [(base, const Color(0xFFFFF4F8)), (medio, const Color(0xFFFFF4F8))]) {
        cv.drawRRect(_caja(Rect.fromLTWH(caja.left, caja.top, caja.width, caja.height * 0.26), L * 0.018), _relleno(color));
        for (var i = 0; i < 5; i++) {
          final gx = caja.left + caja.width * (0.12 + i * 0.19);
          cv.drawRRect(_caja(Rect.fromLTWH(gx - L * 0.012, caja.top, L * 0.024, caja.height * (0.40 + 0.10 * (i % 2))), L * 0.012), _relleno(color));
        }
      }
      for (var i = 0; i < 6; i++) {
        cv.drawCircle(Offset(base.left + base.width * (0.12 + i * 0.152), base.bottom - base.height * 0.28), L * 0.009, _relleno(const Color(0xFFFFE08A)));
      }
      // las velas
      for (var i = 0; i < 3; i++) {
        final vx = cx + (i - 1) * L * 0.075;
        final vela = Rect.fromLTRB(vx - L * 0.008, medio.top - L * 0.075, vx + L * 0.008, medio.top + L * 0.004);
        cv.drawRRect(_caja(vela, 2), _degradado(vela, [i == 1 ? const Color(0xFF67E8F9) : const Color(0xFFFFFFFF), const Color(0xFFFF5C8A)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
        _llama(cv, Offset(vx, vela.top - L * 0.022), L * 0.016, s + i * 0.13);
      }

      // la mascota con su gorrito
      final r = L * 0.095;
      final mc = Offset(L * 0.745, L * 0.615);
      final salto = sin(pi * ((s % 1.5) / 1.5)).abs();
      cv.drawOval(Rect.fromCenter(center: Offset(mc.dx, L * 0.755), width: r * 1.7, height: r * 0.26), Paint()..color = Colors.black.withValues(alpha: 0.3)..maskFilter = MaskFilter.blur(BlurStyle.normal, r * 0.12));
      cv.save();
      cv.translate(mc.dx, mc.dy + r * 1.3 - r * 0.22 * salto);
      cv.scale(1 - 0.02 * salto, 1 + 0.05 * salto);
      cv.translate(-mc.dx, -(mc.dy + r * 1.3));
      _mascota6(cv, mc, r, const Color(0xFFB4A1FF), fase: 2 * pi * s / 1.5, gorro: 1, boca: 0.45, alzar: 0.5);
      cv.restore();
      for (var i = 0; i < 4; i++) {
        _estrella(cv, Offset(L * (0.50 + 0.14 * i), L * (0.36 + 0.05 * ((i * 2) % 3))), L * (0.008 + 0.014 * _onda(s, 1.5, i * 0.25)), const Color(0xFFFFE08A));
      }

      // el aviso a los amigos: sube, se queda y se va
      final a = _suave(_tramo(s, 4.2, 5.2)) * (1 - _suave(_tramo(s, 10.6, 11.6)));
      if (a > 0.001) {
        final tarjeta = Rect.fromLTWH(L * 0.07, L * 0.835 + (1 - a) * L * 0.06, L * 0.86, L * 0.13);
        cv.saveLayer(Offset.zero & z, Paint()..color = Colors.white.withValues(alpha: a));
        cv.drawRRect(_caja(tarjeta, L * 0.04).shift(Offset(0, L * 0.012)), Paint()..color = Colors.black.withValues(alpha: 0.45)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.02));
        cv.drawRRect(_caja(tarjeta, L * 0.04), _degradado(tarjeta, const [Color(0xFF232634), Color(0xFF14161F)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
        cv.drawRRect(_caja(tarjeta, L * 0.04), _trazo(const Color(0xFFFF5C8A).withValues(alpha: 0.7), 1.4));
        final av = Offset(tarjeta.left + L * 0.085, tarjeta.center.dy);
        _avatar(cv, av, L * 0.045, const Color(0xFFFF9EC4), const Color(0xFF8B3A66));
        cv.drawCircle(av + Offset(L * 0.035, L * 0.032), L * 0.022, _relleno(const Color(0xFFFFE08A)));
        _icono(cv, Icons.cake_rounded, av + Offset(L * 0.035, L * 0.032), L * 0.03, const Color(0xFF5A3A00));
        _txtIzq(cv, 'Hoy cumple Camila', Offset(tarjeta.left + L * 0.16, tarjeta.center.dy - L * 0.026), L * 0.038, Colors.white, ancho: L * 0.42);
        _txtIzq(cv, 'Salúdala y alégrale el día', Offset(tarjeta.left + L * 0.16, tarjeta.center.dy + L * 0.030), L * 0.028, Colors.white.withValues(alpha: 0.7), peso: FontWeight.w700, ancho: L * 0.42);
        _chip(cv, 'Saludar', Offset(tarjeta.right - L * 0.115, tarjeta.center.dy), L * 0.031, const Color(0xFFFF5C8A), activo: 0.6 + 0.4 * _onda(s, 1.5), ancho: L * 0.17);
        cv.restore();
      }
    });

// ------------------------------------------------------------ tu perfil

Widget ilusPerfil(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final foco = (s ~/ 4) % 3; // 0 portada, 1 dedicatoria, 2 cápsula
      final cover = Rect.fromLTWH(L * 0.06, L * 0.04, L * 0.88, L * 0.32);
      final fondo = RRect.fromRectAndRadius(Rect.fromLTWH(L * 0.06, L * 0.04, L * 0.88, L * 0.45), Radius.circular(L * 0.045));
      cv.drawRRect(fondo, _degradado(fondo.outerRect, const [Color(0xFF1B1F27), Color(0xFF0F1118)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
      cv.drawRRect(fondo, _trazo(Colors.white.withValues(alpha: 0.16), 1.3));
      if (foco == 0) {
        cv.drawRRect(fondo.inflate(2), _trazo(c.acento.withValues(alpha: 0.35 + 0.35 * _onda(s, 2)), 2));
      }
      // la portada: paisaje con su frase
      cv.save();
      cv.clipPath(Path()..addRRect(RRect.fromRectAndCorners(cover, topLeft: Radius.circular(L * 0.045), topRight: Radius.circular(L * 0.045))));
      _escena(cv, cover, Color.lerp(c.acento, const Color(0xFF8B6CFF), 0.5)!);
      cv.restore();
      const frase = 'Mi música, mi mundo';
      final n = (frase.length * _tramo(s % 4, 0.3, 2.6)).round().clamp(0, frase.length);
      cv.drawRRect(_caja(Rect.fromLTWH(L * 0.085, L * 0.075, _medir(frase, L * 0.046) + L * 0.05, L * 0.08), 99), _relleno(Colors.black.withValues(alpha: 0.38)));
      _txtIzq(cv, frase.substring(0, foco == 0 ? n : frase.length), Offset(L * 0.11, L * 0.115), L * 0.046, Colors.white, ancho: L * 0.8);
      // la canción de la portada
      final pill = Rect.fromCenter(center: Offset(L * 0.68, L * 0.29), width: L * 0.40, height: L * 0.066);
      cv.drawRRect(_caja(pill, 99), _relleno(Colors.black.withValues(alpha: 0.55)));
      cv.drawRRect(_caja(pill, 99), _trazo(Colors.white.withValues(alpha: 0.4), 1.2));
      for (var i = 0; i < 4; i++) {
        final h = 0.25 + 0.75 * _onda(s, 1.5, i * 0.21);
        final x = pill.left + L * 0.035 + i * L * 0.014;
        cv.drawLine(Offset(x, pill.center.dy + L * 0.016 * h), Offset(x, pill.center.dy - L * 0.016 * h), _trazo(const Color(0xFF2BD576), L * 0.008));
      }
      _txtIzq(cv, 'Tu canción favorita', Offset(pill.left + L * 0.10, pill.center.dy), L * 0.028, Colors.white, ancho: L * 0.28);
      // el avatar y el nombre
      final av = Offset(L * 0.19, L * 0.355);
      cv.drawCircle(av, L * 0.082, _relleno(const Color(0xFF0F1118)));
      _avatar(cv, av, L * 0.07, Color.lerp(c.acento, Colors.white, 0.15)!, Color.lerp(c.acento, Colors.black, 0.6)!);
      _anillo(cv, av, L * 0.078, L * 0.011, const [Color(0xFF22D3EE), Color(0xFF8B6CFF), Color(0xFFFF5C8A), Color(0xFF22D3EE)], 2 * pi * s / 6);
      _txtIzq(cv, 'Ali', Offset(L * 0.30, L * 0.40), L * 0.046, Colors.white);
      _txtIzq(cv, 'Portada con tu canción', Offset(L * 0.30, L * 0.45), L * 0.026, Colors.white.withValues(alpha: 0.6), peso: FontWeight.w700, ancho: L * 0.6);

      // las dos tarjetas de abajo
      final izq = Rect.fromLTWH(L * 0.06, L * 0.53, L * 0.43, L * 0.38);
      final der = Rect.fromLTWH(L * 0.51, L * 0.53, L * 0.43, L * 0.38);
      for (final (i, r, titulo, color) in [(1, izq, 'Dedicatoria', const Color(0xFFFF5C8A)), (2, der, 'Cápsula del tiempo', const Color(0xFF67E8F9))]) {
        final on = foco == i;
        cv.drawRRect(_caja(r, L * 0.04), _degradado(r, [Color.lerp(const Color(0xFF1B1F27), color, on ? 0.22 : 0.06)!, const Color(0xFF0F1118)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
        cv.drawRRect(_caja(r, L * 0.04), _trazo(on ? color.withValues(alpha: 0.5 + 0.4 * _onda(s, 2)) : Colors.white.withValues(alpha: 0.16), on ? 2 : 1.3));
        _txt(cv, titulo, Offset(r.center.dx, r.top + L * 0.045), _ajusta6(titulo, L * 0.036, r.width - L * 0.05), Colors.white, ancho: r.width - L * 0.04);
      }
      // dedicatoria: una tarjeta con corazón que se inclina
      cv.save();
      cv.translate(izq.center.dx, izq.center.dy + L * 0.012);
      cv.rotate(-0.10 + 0.05 * sin(2 * pi * s / 3));
      final tarj = Rect.fromCenter(center: Offset.zero, width: L * 0.30, height: L * 0.185);
      cv.drawRRect(_caja(tarj, L * 0.02).shift(Offset(0, L * 0.01)), Paint()..color = Colors.black.withValues(alpha: 0.4)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.012));
      cv.drawRRect(_caja(tarj, L * 0.02), _degradado(tarj, const [Color(0xFFFF9EC4), Color(0xFFFF5C8A)]));
      _txtIzq(cv, 'Para: Sofi', Offset(tarj.left + L * 0.02, tarj.top + L * 0.035), L * 0.03, Colors.white, ancho: L * 0.2);
      cv.drawRRect(_caja(Rect.fromLTWH(tarj.left + L * 0.02, tarj.top + L * 0.075, L * 0.22, L * 0.009), 99), _relleno(Colors.white.withValues(alpha: 0.7)));
      cv.drawRRect(_caja(Rect.fromLTWH(tarj.left + L * 0.02, tarj.top + L * 0.100, L * 0.15, L * 0.009), 99), _relleno(Colors.white.withValues(alpha: 0.5)));
      _icono(cv, Icons.favorite_rounded, Offset(tarj.right - L * 0.04, tarj.bottom - L * 0.04), L * 0.05 * (foco == 1 ? 1 + 0.25 * sin(pi * (s % 1)).abs() : 1), Colors.white);
      cv.restore();
      _txt(cv, 'Dedica con tarjeta', Offset(izq.center.dx, izq.bottom - L * 0.036), _ajusta6('Dedica con tarjeta', L * 0.027, izq.width - L * 0.05), Colors.white.withValues(alpha: 0.7), peso: FontWeight.w700, ancho: izq.width - L * 0.04);
      // cápsula del tiempo: una cápsula que flota con candado
      final cc = Offset(der.center.dx, der.center.dy + L * 0.005);
      cv.save();
      cv.translate(cc.dx, cc.dy + L * 0.008 * sin(2 * pi * s / 3));
      cv.rotate(-0.5 + 0.08 * sin(2 * pi * s / 3));
      final cap = Rect.fromCenter(center: Offset.zero, width: L * 0.22, height: L * 0.095);
      cv.save();
      cv.clipRRect(_caja(cap, L * 0.0475));
      cv.drawRect(Rect.fromLTRB(cap.left, cap.top, cap.center.dx, cap.bottom), _degradado(cap, const [Color(0xFF67E8F9), Color(0xFF2B8FB0)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
      cv.drawRect(Rect.fromLTRB(cap.center.dx, cap.top, cap.right, cap.bottom), _degradado(cap, const [Color(0xFFFFFFFF), Color(0xFFC3C8D6)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
      cv.drawRect(Rect.fromLTWH(cap.left, cap.top + cap.height * 0.14, cap.width, cap.height * 0.12), _relleno(Colors.white.withValues(alpha: 0.35)));
      cv.restore();
      cv.drawRRect(_caja(cap, L * 0.0475), _trazo(Colors.white.withValues(alpha: 0.5), 1.3));
      cv.restore();
      _icono(cv, Icons.lock_rounded, cc + Offset(L * 0.085, L * 0.065), L * 0.045, const Color(0xFFFFE08A));
      if (foco == 2) {
        for (var i = 0; i < 4; i++) {
          _estrella(cv, cc + Offset(cos(2 * pi * (i / 4 + s / 6)) * L * 0.15, sin(2 * pi * (i / 4 + s / 6)) * L * 0.09), L * (0.008 + 0.012 * _onda(s, 1.5, i * 0.25)), const Color(0xFFFFE08A));
        }
      }
      _txt(cv, 'Se abre en 2027', Offset(der.center.dx, der.bottom - L * 0.036), _ajusta6('Se abre en 2027', L * 0.027, der.width - L * 0.05), Colors.white.withValues(alpha: 0.7), peso: FontWeight.w700, ancho: der.width - L * 0.04);
    });

// ------------------------------------------------ escucha a tu manera

Widget ilusModos(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      const iconos = [Icons.directions_car_rounded, Icons.center_focus_strong_rounded, Icons.bedtime_rounded, Icons.fitness_center_rounded, Icons.groups_rounded];
      const colores = [Color(0xFF34D399), Color(0xFF38BDF8), Color(0xFF8B6CFF), Color(0xFFFF8A3D), Color(0xFFFF5C8A)];
      const titulos = ['Modo auto', 'Concentración', 'Dormir', 'Ejercicio', 'Listas colaborativas'];
      const frases = ['Botones gigantes para manejar', 'Música para trabajar sin distraerte', 'La música baja sola hasta apagarse', 'Ritmo para acompañar tu entrenamiento', 'Hasta 50 personas, gratis'];
      final idx = (s / 2.4).floor().clamp(0, 4);
      final t = s - idx * 2.4;
      final col = colores[idx];
      final ctr = Offset(L / 2, L * 0.47);
      cv.drawCircle(ctr, L * 0.42, Paint()..shader = RadialGradient(colors: [col.withValues(alpha: 0.30), col.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: ctr, radius: L * 0.42)));
      _pestanas6(cv, L, iconos, colores, idx, L * 0.085, s);
      _etapa6(cv, z, ctr, t, 2.4, () {
        switch (idx) {
          case 0:
            _modoAuto6(cv, L, ctr, t, col);
          case 1:
            _modoConcentra6(cv, L, ctr, t, col);
          case 2:
            _modoDormir6(cv, L, ctr, t, col);
          case 3:
            _modoEjercicio6(cv, L, ctr, t, col);
          default:
            _modoColabora6(cv, L, ctr, t, col);
        }
      });
      _etiqueta6(cv, L, titulos[idx], frases[idx], col, _entra6(t, 2.4));
    });

void _modoAuto6(Canvas cv, double L, Offset ctr, double t, Color col) {
  final panel = Rect.fromCenter(center: ctr, width: L * 0.84, height: L * 0.46);
  cv.drawRRect(_caja(panel, L * 0.05), _degradado(panel, const [Color(0xFF1B1F27), Color(0xFF0B0D12)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
  cv.drawRRect(_caja(panel, L * 0.05), _trazo(col.withValues(alpha: 0.5), 1.5));
  // la carretera pasa por debajo
  cv.save();
  cv.clipRRect(_caja(panel.deflate(2), L * 0.05));
  for (var i = 0; i < 6; i++) {
    final x = panel.left + ((i * 0.2 - t * 0.5) % 1.2) * panel.width - panel.width * 0.1;
    cv.drawRRect(_caja(Rect.fromLTWH(x, panel.bottom - L * 0.045, L * 0.07, L * 0.012), 99), _relleno(Colors.white.withValues(alpha: 0.22)));
  }
  cv.restore();
  _icono(cv, Icons.directions_car_rounded, Offset(panel.center.dx, panel.top + L * 0.065), L * 0.07, col);
  final y = ctr.dy + L * 0.025;
  final push = _suave(_tramo(t, 0.9, 1.1)) * (1 - _suave(_tramo(t, 1.2, 1.5)));
  for (final (dx, rad, ico, plano) in [(-0.27, 0.085, Icons.skip_previous_rounded, true), (0.0, 0.115, Icons.play_arrow_rounded, false), (0.27, 0.085, Icons.skip_next_rounded, true)]) {
    final o = Offset(L / 2 + L * dx, y);
    final r = L * rad * (!plano ? 1 - 0.06 * push : 1);
    cv.drawCircle(o, r, plano ? _relleno(Colors.white.withValues(alpha: 0.12)) : _degradado(Rect.fromCircle(center: o, radius: r), [Color.lerp(col, Colors.white, 0.3)!, col]));
    cv.drawCircle(o, r, _trazo(Colors.white.withValues(alpha: 0.35), 1.3));
    _icono(cv, ico, o, r * 1.25, plano ? Colors.white : const Color(0xFF0B0D12));
  }
  _toque(cv, Offset(L / 2, y), L * 0.115, _tramo(t, 1.0, 1.9), col);
  _dedo(cv, Offset(L / 2 + L * 0.03, y + L * 0.075), L * 0.085, _suave(_tramo(t, 0.4, 0.8)) * (1 - _suave(_tramo(t, 1.7, 2.1))));
}

void _modoConcentra6(Canvas cv, double L, Offset ctr, double t, Color col) {
  for (var i = 0; i < 3; i++) {
    final p = ((t / 2.4) + i / 3) % 1;
    cv.drawCircle(ctr, L * (0.30 - 0.12 * p), _trazo(col.withValues(alpha: p * 0.35), 1.5));
  }
  final R = L * 0.20;
  cv.drawCircle(ctr, R, _trazo(Colors.white.withValues(alpha: 0.12), L * 0.028));
  cv.drawArc(Rect.fromCircle(center: ctr, radius: R), -pi / 2, 2 * pi * _suave(_tramo(t, 0, 2.4)) * 0.72 + 0.4, false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeWidth = L * 0.028
        ..shader = SweepGradient(colors: [col, Color.lerp(col, Colors.white, 0.5)!], startAngle: -pi / 2, endAngle: 3 * pi / 2).createShader(Rect.fromCircle(center: ctr, radius: R)));
  _icono(cv, Icons.center_focus_strong_rounded, ctr + Offset(0, -L * 0.065), L * 0.07, col);
  _txt(cv, '25:00', ctr + Offset(0, L * 0.045), L * 0.085, Colors.white, ancho: R * 1.6);
  // las distracciones se quedan fuera
  for (var i = 0; i < 6; i++) {
    final ang = 2 * pi * i / 6 + 0.3;
    final p = ((t / 1.2) + i * 0.17) % 1;
    final o = ctr + Offset(cos(ang) * L * (0.38 - 0.10 * p), sin(ang) * L * (0.30 - 0.08 * p));
    cv.drawCircle(o, L * 0.016 * (1 - p * 0.5), _relleno(Colors.white.withValues(alpha: 0.35 * (1 - p))));
  }
}

void _modoDormir6(Canvas cv, double L, Offset ctr, double t, Color col) {
  final luna = ctr + Offset(-L * 0.04, -L * 0.07);
  final R = L * 0.15;
  final media = Path.combine(PathOperation.difference, Path()..addOval(Rect.fromCircle(center: luna, radius: R)), Path()..addOval(Rect.fromCircle(center: luna + Offset(R * 0.55, -R * 0.25), radius: R * 0.86)));
  cv.drawPath(media, Paint()..color = const Color(0xFFFFE08A).withValues(alpha: 0.5)..maskFilter = MaskFilter.blur(BlurStyle.normal, R * 0.3));
  cv.drawPath(media, _degradado(Rect.fromCircle(center: luna, radius: R), const [Color(0xFFFFF4C2), Color(0xFFF5C542)]));
  for (var i = 0; i < 6; i++) {
    final o = ctr + Offset(L * (-0.30 + 0.12 * i) + (i.isOdd ? L * 0.04 : 0), -L * (0.19 - 0.04 * ((i * 5) % 4)));
    _estrella(cv, o, L * (0.008 + 0.016 * _onda(t * 2.5, 2, i * 0.2)), Colors.white.withValues(alpha: 0.9));
  }
  for (var i = 0; i < 3; i++) {
    final p = ((t / 2.4) + i / 3) % 1;
    _txt(cv, 'z', ctr + Offset(L * 0.17 + p * L * 0.09, -L * 0.03 - p * L * 0.12), L * (0.038 + 0.016 * i), Colors.white.withValues(alpha: sin(pi * p).clamp(0.0, 1.0) * 0.9));
  }
  // el volumen baja solo
  final pista = Rect.fromCenter(center: ctr + Offset(L * 0.04, L * 0.19), width: L * 0.50, height: L * 0.022);
  cv.drawRRect(_caja(pista, 99), _relleno(Colors.white.withValues(alpha: 0.18)));
  final v = 1 - 0.85 * _suave(_tramo(t, 0.2, 2.2));
  cv.drawRRect(_caja(Rect.fromLTWH(pista.left, pista.top, pista.width * v, pista.height), 99), _relleno(col));
  cv.drawCircle(Offset(pista.left + pista.width * v, pista.center.dy), L * 0.016, _relleno(Colors.white));
  _icono(cv, v > 0.5 ? Icons.volume_up_rounded : Icons.volume_down_rounded, Offset(pista.left - L * 0.06, pista.center.dy), L * 0.06, Colors.white);
}

void _modoEjercicio6(Canvas cv, double L, Offset ctr, double t, Color col) {
  final rebote = sin(pi * ((t % 0.6) / 0.6)).abs();
  _icono(cv, Icons.directions_run_rounded, ctr + Offset(-L * 0.17, -L * 0.075 - L * 0.018 * rebote), L * 0.22, col);
  final lat = 1 + 0.16 * sin(pi * ((t % 0.6) / 0.6)).abs();
  final cora = ctr + Offset(L * 0.17, -L * 0.14);
  _icono(cv, Icons.favorite_rounded, cora, L * 0.07 * lat, const Color(0xFFFF5C8A));
  _txt(cv, '150', ctr + Offset(L * 0.17, -L * 0.05), L * 0.095, Colors.white, ancho: L * 0.22);
  _txt(cv, 'BPM', ctr + Offset(L * 0.17, L * 0.012), L * 0.034, Colors.white.withValues(alpha: 0.7), ancho: L * 0.2);
  // el pulso va pasando
  final ancho = L * 0.80;
  final base = ctr.dy + L * 0.17;
  final ruta = Path();
  for (var i = 0; i <= 90; i++) {
    final u = i / 90;
    final f = (((u * 2.0 - t * 0.9) % 1) + 1) % 1;
    final p = Offset(ctr.dx - ancho / 2 + ancho * u, base - _ecg6(f) * L * 0.085);
    if (i == 0) {
      ruta.moveTo(p.dx, p.dy);
    } else {
      ruta.lineTo(p.dx, p.dy);
    }
  }
  cv.drawPath(ruta, Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = L * 0.03
    ..color = col.withValues(alpha: 0.4)
    ..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.015));
  cv.drawPath(ruta, _trazo(Color.lerp(col, Colors.white, 0.25)!, L * 0.011));
}

double _ecg6(double u) {
  if (u < 0.12) return 0;
  if (u < 0.22) return 0.15 * sin(pi * (u - 0.12) / 0.10);
  if (u < 0.34) return 0;
  if (u < 0.38) return -0.2 * sin(pi * (u - 0.34) / 0.04);
  if (u < 0.46) return sin(pi * (u - 0.38) / 0.08);
  if (u < 0.52) return -0.35 * sin(pi * (u - 0.46) / 0.06);
  if (u < 0.62) return 0;
  if (u < 0.80) return 0.25 * sin(pi * (u - 0.62) / 0.18);
  return 0;
}

void _modoColabora6(Canvas cv, double L, Offset ctr, double t, Color col) {
  const paleta = [Color(0xFF22D3EE), Color(0xFF8B6CFF), Color(0xFFF5C542), Color(0xFF2BD576), Color(0xFFFF8A3D), Color(0xFFFF9EC4)];
  final cuantos = _lerp(2, 50, _suave(_tramo(t, 0.2, 1.8)));
  const n = 14;
  final R = L * 0.225;
  for (var i = 0; i < n; i++) {
    final vis = _suave(((cuantos - 2) / 48 * n - i + 1).clamp(0.0, 1.0));
    if (vis <= 0) continue;
    final ang = 2 * pi * i / n - pi / 2;
    final o = ctr + Offset(cos(ang), sin(ang)) * R * (0.7 + 0.3 * vis);
    final rad = L * 0.036 * vis;
    cv.drawLine(o, ctr, _trazo(col.withValues(alpha: 0.12 * vis), 1));
    _avatar(cv, o, rad, paleta[i % paleta.length], Color.lerp(paleta[i % paleta.length], Colors.black, 0.55)!);
    cv.drawCircle(o, rad, _trazo(Colors.white.withValues(alpha: 0.5 * vis), 1));
  }
  final centro = Rect.fromCircle(center: ctr, radius: L * 0.115);
  cv.drawCircle(ctr, L * 0.115, _degradado(centro, [Color.lerp(col, Colors.white, 0.2)!, Color.lerp(col, Colors.black, 0.35)!]));
  cv.drawCircle(ctr, L * 0.115, _trazo(Colors.white.withValues(alpha: 0.5), 1.3));
  _txt(cv, '${cuantos.round()}', ctr + Offset(0, -L * 0.012), L * 0.075, Colors.white, ancho: L * 0.16);
  _txt(cv, 'personas', ctr + Offset(0, L * 0.050), L * 0.027, Colors.white.withValues(alpha: 0.9), peso: FontWeight.w700, ancho: L * 0.18);
  // las canciones que van sumando
  for (var i = 0; i < 3; i++) {
    final p = ((t / 1.2) + i / 3) % 1;
    final ang = 2 * pi * (i / 3) + 0.5;
    _nota(cv, ctr + Offset(cos(ang), sin(ang)) * R * (1.1 - 0.7 * p), L * 0.016, Colors.white.withValues(alpha: sin(pi * p).clamp(0.0, 1.0) * 0.9));
  }
}

// ----------------------------------------------------- para donadores

Widget ilusDonadores6(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      const iconos = [Icons.hearing_rounded, Icons.auto_awesome_rounded, Icons.insert_chart_rounded, Icons.headphones_rounded, Icons.lock_rounded];
      const colores = [Color(0xFF22D3EE), Color(0xFFF5C542), Color(0xFFFF5C8A), Color(0xFF34D399), Color(0xFF8B6CFF)];
      const titulos = ['¿Qué canción era?', 'Nuevo para ti cada día', 'Tu semana en una tarjeta', 'Ecualizador inteligente', 'Letra en el bloqueo'];
      const frases = ['Reconoce lo que suena y la guarda', 'Música fresca elegida para ti', 'Lo que más escuchaste, para compartir', 'Se adapta a tus audífonos', 'Sigue la letra sin desbloquear'];
      final idx = (s / 2.4).floor().clamp(0, 4);
      final t = s - idx * 2.4;
      final col = colores[idx];
      final ctr = Offset(L / 2, L * 0.47);
      cv.drawCircle(ctr, L * 0.42, Paint()..shader = RadialGradient(colors: [col.withValues(alpha: 0.30), col.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: ctr, radius: L * 0.42)));
      _pestanas6(cv, L, iconos, colores, idx, L * 0.085, s);
      _etapa6(cv, z, ctr, t, 2.4, () {
        switch (idx) {
          case 0:
            _donaQue6(cv, L, ctr, t, col);
          case 1:
            _donaDiario6(cv, L, ctr, t, col);
          case 2:
            _donaSemana6(cv, L, ctr, t, col);
          case 3:
            _donaEcualiza6(cv, L, ctr, t, col);
          default:
            _donaBloqueo6(cv, L, ctr, t, col);
        }
      });
      _etiqueta6(cv, L, titulos[idx], frases[idx], col, _entra6(t, 2.4));
    });

void _donaQue6(Canvas cv, double L, Offset ctr, double t, Color col) {
  final mic = ctr + Offset(0, -L * 0.10);
  for (var i = 0; i < 3; i++) {
    final p = ((t / 1.2) + i / 3) % 1;
    cv.drawCircle(mic, L * (0.09 + 0.16 * p), _trazo(col.withValues(alpha: (1 - p) * 0.6), 2));
  }
  cv.drawCircle(mic, L * 0.095, Paint()..color = col.withValues(alpha: 0.4)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.03));
  cv.drawCircle(mic, L * 0.095, _degradado(Rect.fromCircle(center: mic, radius: L * 0.095), [Color.lerp(col, Colors.white, 0.3)!, col]));
  _icono(cv, Icons.mic_rounded, mic, L * 0.11, const Color(0xFF0B0D12));
  // aparece la canción encontrada
  final k = _suave(_tramo(t, 1.0, 1.5));
  if (k > 0) {
    final tarjeta = Rect.fromCenter(center: ctr + Offset(0, L * 0.165), width: L * 0.66 * k, height: L * 0.135);
    cv.drawRRect(_caja(tarjeta, L * 0.035), _relleno(const Color(0xFF1B1F27)));
    cv.drawRRect(_caja(tarjeta, L * 0.035), _trazo(col.withValues(alpha: 0.7), 1.4));
    if (k > 0.8) {
      _caratula6(cv, Rect.fromLTWH(tarjeta.left + L * 0.02, tarjeta.top + L * 0.02, L * 0.095, L * 0.095), const [Color(0xFFFF7BAC), Color(0xFF8B6CFF)], L * 0.02);
      _txtIzq(cv, 'Tu canción', Offset(tarjeta.left + L * 0.14, tarjeta.center.dy - L * 0.022), L * 0.04, Colors.white, ancho: L * 0.36);
      _txtIzq(cv, 'Encontrada al instante', Offset(tarjeta.left + L * 0.14, tarjeta.center.dy + L * 0.030), L * 0.027, col, peso: FontWeight.w700, ancho: L * 0.36);
      _icono(cv, Icons.check_circle_rounded, Offset(tarjeta.right - L * 0.045, tarjeta.center.dy), L * 0.06, const Color(0xFF2BD576));
    }
  }
}

void _donaDiario6(Canvas cv, double L, Offset ctr, double t, Color col) {
  final y = ctr.dy + L * 0.01;
  _chip(cv, 'HOY', ctr + Offset(0, -L * 0.17), L * 0.036, col);
  _icono(cv, Icons.today_rounded, ctr + Offset(-L * 0.115, -L * 0.17), L * 0.055, col);
  const cols = [
    [Color(0xFFFF7BAC), Color(0xFFFF8A3D)],
    [Color(0xFF22D3EE), Color(0xFF8B6CFF)],
    [Color(0xFF34D399), Color(0xFF22D3EE)],
  ];
  for (var i = 0; i < 3; i++) {
    final k = _suave(_tramo(t, 0.3 + i * 0.25, 0.8 + i * 0.25));
    if (k <= 0) continue;
    final o = Offset(L / 2 + (i - 1) * L * 0.235, y + (1 - k) * L * 0.05);
    final lado = L * 0.20 * k;
    final r = Rect.fromCenter(center: o, width: lado, height: lado);
    cv.drawRRect(_caja(r, L * 0.03).shift(Offset(0, L * 0.012)), Paint()..color = cols[i][0].withValues(alpha: 0.4)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.02));
    _caratula6(cv, r, cols[i], L * 0.03);
    _icono(cv, Icons.play_circle_fill_rounded, o + Offset(lado * 0.28, lado * 0.28), lado * 0.28, Colors.white.withValues(alpha: 0.95));
    if (k > 0.95) _estrella(cv, o + Offset(lado * 0.46, -lado * 0.46), L * (0.012 + 0.014 * _onda(t * 2, 1.2, i * 0.3)), const Color(0xFFFFE08A));
  }
  _chip(cv, 'Nuevo cada día', ctr + Offset(0, L * 0.165), L * 0.033, col);
}

void _donaSemana6(Canvas cv, double L, Offset ctr, double t, Color col) {
  final tarjeta = Rect.fromCenter(center: ctr + Offset(0, L * 0.01), width: L * 0.68, height: L * 0.46);
  cv.drawRRect(_caja(tarjeta, L * 0.05).shift(Offset(0, L * 0.015)), Paint()..color = Colors.black.withValues(alpha: 0.45)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.025));
  cv.drawRRect(_caja(tarjeta, L * 0.05), _degradado(tarjeta, const [Color(0xFF8B6CFF), Color(0xFFFF5C8A)]));
  cv.drawRRect(_caja(tarjeta, L * 0.05), _trazo(Colors.white.withValues(alpha: 0.4), 1.3));
  _txtIzq(cv, 'TU SEMANA', Offset(tarjeta.left + L * 0.04, tarjeta.top + L * 0.055), L * 0.04, Colors.white, ancho: L * 0.4);
  _icono(cv, Icons.ios_share_rounded, Offset(tarjeta.right - L * 0.055, tarjeta.top + L * 0.055), L * 0.05, Colors.white);
  const dias = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
  const altos = [0.35, 0.55, 0.40, 0.70, 0.60, 1.0, 0.80];
  final ancho = tarjeta.width - L * 0.10;
  for (var i = 0; i < 7; i++) {
    final x = tarjeta.left + L * 0.05 + ancho * (i + 0.5) / 7;
    final k = _suave(_tramo(t, 0.3 + i * 0.1, 0.9 + i * 0.1));
    final alto = L * 0.22 * altos[i] * k;
    final b = Rect.fromLTWH(x - L * 0.018, tarjeta.bottom - L * 0.075 - alto, L * 0.036, alto);
    cv.drawRRect(_caja(b, L * 0.012), _relleno(Colors.white.withValues(alpha: i == 5 ? 0.98 : 0.6)));
    _txt(cv, dias[i], Offset(x, tarjeta.bottom - L * 0.04), L * 0.029, Colors.white.withValues(alpha: 0.9), ancho: L * 0.05);
  }
}

void _donaEcualiza6(Canvas cv, double L, Offset ctr, double t, Color col) {
  _icono(cv, Icons.headphones_rounded, ctr + Offset(0, -L * 0.17), L * 0.10, col);
  const objetivos = [0.35, 0.75, 0.50, 0.85, 0.40];
  const marcas = ['60', '250', '1k', '4k', '12k'];
  final ancho = L * 0.66;
  final alto = L * 0.25;
  final top = ctr.dy - L * 0.09;
  final puntos = <Offset>[];
  for (var i = 0; i < 5; i++) {
    final x = ctr.dx - ancho / 2 + ancho * i / 4;
    final k = _suave(_tramo(t, 0.15 + i * 0.08, 1.4 + i * 0.08));
    final v = _lerp(0.5, objetivos[i], k);
    cv.drawRRect(_caja(Rect.fromLTWH(x - L * 0.006, top, L * 0.012, alto), 99), _relleno(Colors.white.withValues(alpha: 0.18)));
    final y = top + alto * (1 - v);
    cv.drawRRect(_caja(Rect.fromLTWH(x - L * 0.006, y, L * 0.012, top + alto - y), 99), _relleno(col));
    puntos.add(Offset(x, y));
    cv.drawCircle(Offset(x, y), L * 0.026, Paint()..color = col.withValues(alpha: 0.4)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.012));
    cv.drawCircle(Offset(x, y), L * 0.021, _relleno(Colors.white));
    _txt(cv, marcas[i], Offset(x, top + alto + L * 0.04), L * 0.028, Colors.white.withValues(alpha: 0.7), ancho: L * 0.1);
  }
  final curva = Path()..moveTo(puntos.first.dx, puntos.first.dy);
  for (var i = 1; i < puntos.length; i++) {
    final a = puntos[i - 1], b = puntos[i];
    curva.cubicTo(a.dx + (b.dx - a.dx) / 2, a.dy, a.dx + (b.dx - a.dx) / 2, b.dy, b.dx, b.dy);
  }
  cv.drawPath(curva, _trazo(Color.lerp(col, Colors.white, 0.4)!.withValues(alpha: 0.85), L * 0.008));
}

void _donaBloqueo6(Canvas cv, double L, Offset ctr, double t, Color col) {
  final pant = _telefono(cv, ctr + Offset(0, L * 0.005), L * 0.36, L * 0.54);
  cv.save();
  cv.clipRRect(_caja(pant, L * 0.04));
  cv.drawRect(pant, _degradado(pant, [Color.lerp(col, const Color(0xFF1B1F27), 0.55)!, const Color(0xFF0B0D12)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
  _icono(cv, Icons.lock_rounded, Offset(pant.center.dx, pant.top + L * 0.045), L * 0.036, Colors.white.withValues(alpha: 0.85));
  _txt(cv, '9:41', Offset(pant.center.dx, pant.top + L * 0.11), L * 0.085, Colors.white, ancho: pant.width * 0.9);
  const frases = ['Bajo la luz de la noche', 'Cantemos hasta el final', 'Una vez más'];
  final k = (t / 0.8).floor().clamp(0, 2);
  for (var i = 0; i < 3; i++) {
    final on = i == k;
    final y = pant.top + L * (0.21 + 0.062 * i);
    final tam = L * (on ? 0.031 : 0.026);
    _txt(cv, frases[i], Offset(pant.center.dx, y), _ajusta6(frases[i], tam, pant.width * 0.88), on ? Color.lerp(col, Colors.white, 0.35)! : Colors.white.withValues(alpha: 0.45), ancho: pant.width * 0.92);
  }
  // los controles pequeñitos de la pantalla de bloqueo
  final by = pant.bottom - L * 0.075;
  cv.drawRRect(_caja(Rect.fromCenter(center: Offset(pant.center.dx, by), width: pant.width * 0.84, height: L * 0.075), L * 0.025), _relleno(Colors.white.withValues(alpha: 0.12)));
  _icono(cv, Icons.skip_previous_rounded, Offset(pant.center.dx - pant.width * 0.25, by), L * 0.045, Colors.white);
  _icono(cv, Icons.pause_rounded, Offset(pant.center.dx, by), L * 0.05, Colors.white);
  _icono(cv, Icons.skip_next_rounded, Offset(pant.center.dx + pant.width * 0.25, by), L * 0.045, Colors.white);
  cv.restore();
}

// ------------------------------------------------------------------ gracias

Widget ilusGracias6(Ctx c, double L) => Stack(alignment: Alignment.center, children: [
      Positioned.fill(
        child: _lienzo(c, L, (cv, z, s) {
          final ctr = Offset(L / 2, L * 0.44);
          final rad = L * (0.36 + 0.03 * _onda(s, 4));
          cv.drawCircle(ctr, rad, Paint()..shader = RadialGradient(colors: [c.acento.withValues(alpha: 0.38), c.acento.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: ctr, radius: rad)));
          const n = 40;
          for (var i = 0; i < n; i++) {
            final ang = 2 * pi * i / n - pi / 2;
            final amp = 0.25 + 0.75 * _onda(s * 2 + i * 0.35, 3, (i % 5) * 0.13);
            final r0 = L * 0.235, r1 = r0 + L * 0.075 * amp;
            final col = Color.lerp(c.acento, const Color(0xFFFF5C8A), 0.5 + 0.5 * sin(ang + 2 * pi * s / 12))!;
            cv.drawLine(ctr + Offset(cos(ang), sin(ang)) * r0, ctr + Offset(cos(ang), sin(ang)) * r1, _trazo(col.withValues(alpha: 0.9), L * 0.011));
          }
          const paleta = [Color(0xFFFFE08A), Color(0xFFFF5C8A), Color(0xFF8B6CFF), Color(0xFF2BD576), Color(0xFF67E8F9), Color(0xFFFF8A3D)];
          for (var i = 0; i < 16; i++) {
            final x0 = L * (0.08 + ((i * 0.381966) % 1) * 0.84);
            final p = ((s / 12) * (1 + i % 2) + (i * 0.173) % 1) % 1;
            final y = _lerp(L * 1.02, -L * 0.04, p);
            final x = x0 + sin(2 * pi * (s / 6 * (1 + i % 2) + i * 0.1)) * L * 0.025;
            final a = pow(sin(pi * p), 0.6).toDouble() * 0.8;
            final col = paleta[i % paleta.length].withValues(alpha: a);
            if (i % 2 == 0) {
              _icono(cv, Icons.favorite_rounded, Offset(x, y), L * (0.030 + 0.008 * (i % 3)), col);
            } else {
              _nota(cv, Offset(x, y), L * 0.020, col);
            }
          }
          // dos mascotas saludan, una con gorrito
          final r = L * 0.055;
          for (final (i, lado) in const [(0, -1.0), (1, 1.0)]) {
            final o = Offset(L / 2 + lado * L * 0.36, L * 0.775);
            final b = sin(pi * (((s + i * 0.75) % 1.5) / 1.5)).abs();
            cv.save();
            cv.translate(o.dx, o.dy + r * 1.3 - r * 0.16 * b);
            cv.scale(1, 1 + 0.04 * b);
            cv.translate(-o.dx, -(o.dy + r * 1.3));
            _mascota6(cv, o, r, i == 0 ? const Color(0xFFB4A1FF) : const Color(0xFFFF9EC4), fase: 2 * pi * (s + i * 0.75) / 1.5, gorro: i == 1 ? 1 : 0, boca: 0.3, alzar: 0.5);
            cv.restore();
          }
          _chip(cv, 'CAUDAL 2.6.0', Offset(L / 2, L * 0.915), L * 0.034, c.acento, activo: 0.15 + 0.15 * _onda(s, 4));
        }),
      ),
      Align(
        alignment: const Alignment(0, -0.12),
        child: AnimatedBuilder(
          animation: c.reloj,
          builder: (_, _) => Transform.scale(
            scale: 1 + 0.04 * _onda(c.s, 4),
            child: SizedBox(width: L * 0.30, height: L * 0.30, child: logoConDestello(c, L * 0.30)),
          ),
        ),
      ),
    ]);
