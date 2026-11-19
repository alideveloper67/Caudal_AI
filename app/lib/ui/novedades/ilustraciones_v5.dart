// Ilustraciones de la cuarta actualización grande (2.5.0). Es parte de
// ilustraciones.dart para usar sus utilidades (lienzo, ondas, estrellas...) y su
// reloj de 12 s: todo movimiento dura un divisor de 12 s y el bucle no salta.
part of 'ilustraciones.dart';

// ---------------------------------------------------------------- utilidades

double _medir(String t, double tam, {FontWeight peso = FontWeight.w800, double espacio = 0}) {
  final tp = TextPainter(
    text: TextSpan(
      text: t,
      style: TextStyle(fontSize: tam, fontWeight: peso, letterSpacing: espacio, height: 1.1, fontFamily: familiaIlustraciones),
    ),
    textDirection: TextDirection.ltr,
    maxLines: 1,
  )..layout();
  return tp.width;
}

/// Texto alineado a la izquierda, centrado en vertical sobre [izq].
void _txtIzq(Canvas cv, String t, Offset izq, double tam, Color color, {FontWeight peso = FontWeight.w800, double? ancho}) {
  final tp = TextPainter(
    text: TextSpan(text: t, style: TextStyle(fontSize: tam, color: color, fontWeight: peso, height: 1.1, fontFamily: familiaIlustraciones)),
    textDirection: TextDirection.ltr,
    maxLines: 1,
    ellipsis: '…',
  )..layout(maxWidth: ancho ?? double.infinity);
  tp.paint(cv, izq - Offset(0, tp.height / 2));
}

void _icono(Canvas cv, IconData icono, Offset o, double tam, Color color) {
  final tp = TextPainter(
    text: TextSpan(
      text: String.fromCharCode(icono.codePoint),
      style: TextStyle(fontSize: tam, fontFamily: icono.fontFamily, package: icono.fontPackage, color: color),
    ),
    textDirection: TextDirection.ltr,
  )..layout();
  tp.paint(cv, o - Offset(tp.width / 2, tp.height / 2));
}

/// Una píldora con texto; [activo] (0 a 1) la enciende con su color.
Rect _chip(Canvas cv, String t, Offset ctr, double tam, Color color, {double activo = 0, double? ancho}) {
  final w = ancho ?? _medir(t, tam) + tam * 1.7;
  final r = Rect.fromCenter(center: ctr, width: w, height: tam * 2.1);
  if (activo > 0) {
    cv.drawRRect(_caja(r.inflate(1), 99),
        Paint()..color = color.withValues(alpha: 0.55 * activo)..maskFilter = MaskFilter.blur(BlurStyle.normal, tam * 0.7));
  }
  cv.drawRRect(_caja(r, 99), _relleno(Color.lerp(color.withValues(alpha: 0.14), color, activo * 0.92)!));
  cv.drawRRect(_caja(r, 99), _trazo(color.withValues(alpha: 0.55 + 0.45 * activo), 1.3));
  _txt(cv, t, r.center, tam, Color.lerp(Colors.white.withValues(alpha: 0.88), const Color(0xFF0B0D12), activo)!, ancho: w - 4);
  return r;
}

/// Una fila de píldoras centrada en x = L/2; la [activa] (si hay) se enciende.
void _filaChips(Canvas cv, double L, List<String> textos, double y, double tam, List<Color> colores, int activa,
    [double sep = 0.022]) {
  final ws = [for (final t in textos) _medir(t, tam) + tam * 1.7];
  final total = ws.fold<double>(0, (a, b) => a + b) + L * sep * (textos.length - 1);
  var x = L / 2 - total / 2;
  for (var i = 0; i < textos.length; i++) {
    _chip(cv, textos[i], Offset(x + ws[i] / 2, y), tam, colores[i % colores.length], activo: i == activa ? 1 : 0, ancho: ws[i]);
    x += ws[i] + L * sep;
  }
}

Color _neon(double grados, [double sat = 0.78]) => HSVColor.fromAHSV(1, grados % 360, sat, 1).toColor();

/// Una llama que parpadea (la racha).
void _llama(Canvas cv, Offset o, double r, double s) {
  final k = 1 + 0.06 * sin(2 * pi * s * 2);
  Path forma(double e, double dy) => Path()
    ..moveTo(o.dx, o.dy + dy - r * 1.25 * k * e)
    ..cubicTo(o.dx + r * 0.95 * e, o.dy + dy - r * 0.3 * e, o.dx + r * 0.95 * e, o.dy + dy + r * 0.9 * e, o.dx, o.dy + dy + r * 0.9 * e)
    ..cubicTo(o.dx - r * 0.95 * e, o.dy + dy + r * 0.9 * e, o.dx - r * 0.95 * e, o.dy + dy - r * 0.3 * e, o.dx, o.dy + dy - r * 1.25 * k * e);
  final caja = Rect.fromCircle(center: o, radius: r * 1.2);
  cv.drawPath(forma(1.25, 0), Paint()..color = const Color(0xFFFF6A00).withValues(alpha: 0.35)..maskFilter = MaskFilter.blur(BlurStyle.normal, r * 0.5));
  cv.drawPath(forma(1, 0), _degradado(caja, const [Color(0xFFFFB000), Color(0xFFFF3D00)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
  cv.drawPath(forma(0.55, r * 0.28), _relleno(const Color(0xFFFFE08A)));
}

/// El personaje de Caudal: una mascota redonda con orejas. [fase] anima los brazos.
void _chibi(Canvas cv, Offset o, double r, Color color, double fase) {
  final oscuro = Color.lerp(color, Colors.black, 0.45)!;
  final claro = Color.lerp(color, Colors.white, 0.35)!;
  cv.drawOval(Rect.fromCenter(center: o + Offset(0, r * 1.28), width: r * 1.5, height: r * 0.26),
      Paint()..color = Colors.black.withValues(alpha: 0.35)..maskFilter = MaskFilter.blur(BlurStyle.normal, r * 0.12));
  final brazo = _trazo(oscuro, r * 0.2);
  cv.drawLine(o + Offset(-r * 0.7, r * 0.55), o + Offset(-r * 1.0, r * (0.2 + 0.35 * sin(fase))), brazo);
  cv.drawLine(o + Offset(r * 0.7, r * 0.55), o + Offset(r * 1.0, r * (0.2 + 0.35 * sin(fase + pi))), brazo);
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
    cv.drawPath(dentro, _relleno(const Color(0xFFFF9EC4)));
  }
  final cab = Rect.fromCircle(center: o, radius: r);
  cv.drawCircle(o, r, _degradado(cab, [claro, color], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
  for (final lado in const [-1.0, 1.0]) {
    final ojo = o + Offset(lado * r * 0.38, r * 0.05);
    cv.drawOval(Rect.fromCenter(center: ojo, width: r * 0.26, height: r * 0.34), _relleno(const Color(0xFF1B1030)));
    cv.drawCircle(ojo + Offset(-r * 0.04, -r * 0.07), r * 0.06, _relleno(Colors.white));
    cv.drawCircle(o + Offset(lado * r * 0.62, r * 0.36), r * 0.12, _relleno(const Color(0xFFFF9EC4).withValues(alpha: 0.7)));
  }
  cv.drawArc(Rect.fromCenter(center: o + Offset(0, r * 0.30), width: r * 0.34, height: r * 0.24), 0.2, pi - 0.4, false,
      _trazo(const Color(0xFF1B1030), r * 0.06));
}

/// Anillos que se abren desde un punto (un toque).
void _toque(Canvas cv, Offset o, double r, double p, Color color) {
  if (p <= 0 || p >= 1) return;
  cv.drawCircle(o, r * (0.25 + 0.9 * p), _trazo(color.withValues(alpha: (1 - p) * 0.9), 2.2));
}

/// Un dedo que toca o arrastra; [a] es su opacidad.
void _dedo(Canvas cv, Offset o, double tam, double a) {
  if (a <= 0) return;
  cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: a));
  _icono(cv, Icons.touch_app_rounded, o, tam, Colors.white);
  cv.restore();
}

// ------------------------------------------------------------------ portada

Widget ilusPortada5(Ctx c, double L) {
  return Stack(alignment: Alignment.center, children: [
    Positioned.fill(
      child: _lienzo(c, L, (cv, z, s) {
        final ctr = Offset(L / 2, L * 0.46);
        for (var i = 0; i < 3; i++) {
          final p = ((s / 4) + i / 3) % 1;
          cv.drawCircle(ctr, L * (0.20 + 0.34 * p), _trazo(c.acento.withValues(alpha: (1 - p) * 0.35), 1.6));
        }
        // aurora neón que gira
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
        // las tres novedades orbitan: videojuego, personaje y regalo
        const iconos = [Icons.sports_esports_rounded, Icons.pets_rounded, Icons.card_giftcard_rounded];
        const colores = [
          [Color(0xFF22D3EE), Color(0xFF8B6CFF)],
          [Color(0xFFFF9EC4), Color(0xFFFF5C8A)],
          [Color(0xFFFFE08A), Color(0xFFD99A12)],
        ];
        for (var i = 0; i < 3; i++) {
          final ang = 2 * pi * (i / 3 + s / 12) - pi / 2;
          final o = ctr + Offset(cos(ang) * L * 0.37, sin(ang) * L * 0.30);
          final rad = L * 0.075;
          cv.drawCircle(o + Offset(0, L * 0.01), rad, Paint()..color = Colors.black.withValues(alpha: 0.35)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.016));
          cv.drawCircle(o, rad, _degradado(Rect.fromCircle(center: o, radius: rad), colores[i]));
          _icono(cv, iconos[i], o, rad * 1.1, Colors.white);
        }
        for (var i = 0; i < 6; i++) {
          final ang = 2 * pi * (i / 6 + s / 12) + 0.4;
          final o = ctr + Offset(cos(ang) * L * 0.44, sin(ang) * L * 0.40);
          _estrella(cv, o, L * (0.008 + 0.020 * _onda(s, 3, i / 6)), const Color(0xFFFFE08A));
        }
        _chip(cv, 'VERSIÓN 2.5.0', Offset(L / 2, L * 0.90), L * 0.036, c.acento, activo: 0.15 + 0.15 * _onda(s, 4));
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

// ---------------------------------------------------------------- modo gamer

Widget ilusGamer(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final panel = Rect.fromLTWH(L * 0.05, L * 0.03, L * 0.90, L * 0.94);
      cv.drawRRect(_caja(panel, L * 0.05), _degradado(panel, const [Color(0xFF150B2B), Color(0xFF06050E)]));
      // borde RGB neón: el arcoíris gira entero cada 12 s
      final giro = 360 * s / 12;
      final arco = SweepGradient(
        colors: [for (var i = 0; i <= 6; i++) _neon(giro + i * 60)],
        transform: GradientRotation(2 * pi * s / 12),
      ).createShader(panel);
      cv.drawRRect(_caja(panel, L * 0.05), Paint()..style = PaintingStyle.stroke..strokeWidth = L * 0.012..shader = arco..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.014));
      cv.drawRRect(_caja(panel, L * 0.05), Paint()..style = PaintingStyle.stroke..strokeWidth = L * 0.006..shader = arco);
      final n1 = _neon(giro), n2 = _neon(giro + 120), n3 = _neon(giro + 240);

      // nivel y barra de XP
      final cn = Offset(L * 0.175, L * 0.135);
      cv.drawCircle(cn, L * 0.068, Paint()..color = n1.withValues(alpha: 0.45)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.02));
      cv.drawCircle(cn, L * 0.062, _degradado(Rect.fromCircle(center: cn, radius: L * 0.062), [n1, n2]));
      _txt(cv, '12', cn, L * 0.068, const Color(0xFF0B0D12), peso: FontWeight.w900);
      _txt(cv, 'NIVEL', cn + Offset(0, -L * 0.082), L * 0.026, Colors.white.withValues(alpha: 0.7), espacio: 1.2);
      final barra = Rect.fromLTWH(L * 0.28, L * 0.138, L * 0.60, L * 0.032);
      cv.drawRRect(_caja(barra, 99), _relleno(Colors.white.withValues(alpha: 0.10)));
      final llena = 0.30 + 0.62 * _onda(s, 12, -0.25);
      final lleno = Rect.fromLTWH(barra.left, barra.top, barra.width * llena, barra.height);
      cv.drawRRect(_caja(lleno, 99), _degradado(lleno, [n1, n2], ini: Alignment.centerLeft, fin: Alignment.centerRight));
      _txt(cv, 'XP  ${(2340 + 900 * llena).round()}', Offset(barra.center.dx, L * 0.102), L * 0.030, Colors.white.withValues(alpha: 0.85), ancho: barra.width);
      final q = (s % 3) / 3;
      _txt(cv, '+50 XP', Offset(barra.right - L * 0.06, L * 0.192 - L * 0.012 * q), L * 0.028, n3.withValues(alpha: sin(pi * q).clamp(0.0, 1.0)));

      // misiones diarias
      final mis = Rect.fromLTWH(L * 0.09, L * 0.225, L * 0.47, L * 0.215);
      cv.drawRRect(_caja(mis, L * 0.03), _relleno(Colors.white.withValues(alpha: 0.06)));
      cv.drawRRect(_caja(mis, L * 0.03), _trazo(n2.withValues(alpha: 0.5), 1.2));
      _txt(cv, 'MISIONES DIARIAS', Offset(mis.center.dx, mis.top + L * 0.030), L * 0.027, Colors.white.withValues(alpha: 0.7), espacio: 0.8, ancho: mis.width * 0.92);
      const tareas = ['Escucha 30 min', '3 artistas distintos', '5 canciones nuevas'];
      for (var i = 0; i < 3; i++) {
        final y = mis.top + L * (0.080 + i * 0.048);
        final p = _suave(_tramo(s, 1.5 + i * 2, 2.3 + i * 2)) * (1 - _tramo(s, 11, 12));
        final cc = Offset(mis.left + L * 0.035, y);
        cv.drawCircle(cc, L * 0.015, _trazo(Colors.white.withValues(alpha: 0.5), 1.5));
        if (p > 0) {
          cv.drawCircle(cc, L * 0.015 * p, _relleno(const Color(0xFF4ADE80)));
          cv.drawLine(cc + Offset(-L * 0.006, 0), cc + Offset(-L * 0.001, L * 0.005), _trazo(const Color(0xFF0B0D12).withValues(alpha: p), 1.8));
          cv.drawLine(cc + Offset(-L * 0.001, L * 0.005), cc + Offset(L * 0.008, -L * 0.006), _trazo(const Color(0xFF0B0D12).withValues(alpha: p), 1.8));
        }
        _txtIzq(cv, tareas[i], Offset(mis.left + L * 0.07, y), L * 0.031, Colors.white.withValues(alpha: 0.6 + 0.35 * p), peso: FontWeight.w700, ancho: mis.width - L * 0.09);
      }

      // racha
      final rac = Rect.fromLTWH(L * 0.59, L * 0.225, L * 0.32, L * 0.215);
      cv.drawRRect(_caja(rac, L * 0.03), _relleno(Colors.white.withValues(alpha: 0.06)));
      cv.drawRRect(_caja(rac, L * 0.03), _trazo(const Color(0xFFFF8A3D).withValues(alpha: 0.6), 1.2));
      _txt(cv, 'RACHA', Offset(rac.center.dx, rac.top + L * 0.030), L * 0.027, Colors.white.withValues(alpha: 0.7), espacio: 1.2);
      _llama(cv, Offset(rac.left + rac.width * 0.30, rac.center.dy + L * 0.010), L * 0.040, s);
      _txt(cv, '7', Offset(rac.left + rac.width * 0.70, rac.center.dy - L * 0.004), L * 0.085, const Color(0xFFFFB000), peso: FontWeight.w900);
      _txt(cv, 'días seguidos', Offset(rac.center.dx, rac.bottom - L * 0.030), L * 0.027, Colors.white.withValues(alpha: 0.75), peso: FontWeight.w700, ancho: rac.width * 0.92);

      // sonido por tipo de juego
      _txt(cv, 'SONIDO POR TIPO DE JUEGO', Offset(L / 2, L * 0.492), L * 0.028, Colors.white.withValues(alpha: 0.65), espacio: 1.0, ancho: L * 0.8);
      _filaChips(cv, L, const ['FPS', 'RPG', 'Carreras', 'Chill'], L * 0.558, L * 0.034,
          const [Color(0xFFFF5C8A), Color(0xFF8B6CFF), Color(0xFFF5C542), Color(0xFF22D3EE)], (s ~/ 3) % 4);

      // listas por situación
      _txt(cv, 'LISTAS POR SITUACIÓN', Offset(L / 2, L * 0.635), L * 0.028, Colors.white.withValues(alpha: 0.65), espacio: 1.0, ancho: L * 0.8);
      final sit = (s ~/ 2.4) % 5;
      _filaChips(cv, L, const ['Lobby', 'Concentración', 'Clutch'], L * 0.702, L * 0.034,
          const [Color(0xFF38BDF8), Color(0xFF4ADE80), Color(0xFFFF8A3D)], sit < 3 ? sit : -1);
      _filaChips(cv, L, const ['Victoria', 'Derrota'], L * 0.778, L * 0.034,
          const [Color(0xFFF5C542), Color(0xFFB4A1FF)], sit >= 3 ? sit - 3 : -1);

      // ahorro y tema RGB
      final ahorro = Rect.fromCenter(center: Offset(L * 0.30, L * 0.885), width: L * 0.38, height: L * 0.075);
      cv.drawRRect(_caja(ahorro, 99), _relleno(const Color(0xFF4ADE80).withValues(alpha: 0.14)));
      cv.drawRRect(_caja(ahorro, 99), _trazo(const Color(0xFF4ADE80).withValues(alpha: 0.8), 1.3));
      _icono(cv, Icons.battery_charging_full_rounded, Offset(ahorro.left + L * 0.040, ahorro.center.dy), L * 0.046, const Color(0xFF4ADE80));
      _txt(cv, 'Ahorro al jugar', Offset(ahorro.center.dx + L * 0.030, ahorro.center.dy), L * 0.030, Colors.white, ancho: ahorro.width - L * 0.10);
      final rgb = Rect.fromCenter(center: Offset(L * 0.70, L * 0.885), width: L * 0.38, height: L * 0.075);
      cv.drawRRect(_caja(rgb, 99), _degradado(rgb, [n1.withValues(alpha: 0.30), n2.withValues(alpha: 0.30), n3.withValues(alpha: 0.30)], ini: Alignment.centerLeft, fin: Alignment.centerRight));
      cv.drawRRect(_caja(rgb, 99), _trazo(n2, 1.4));
      _txt(cv, 'Tema RGB neón', rgb.center, L * 0.030, Colors.white, ancho: rgb.width - L * 0.05);
    });

// ------------------------------------------------------ tu personaje cobra vida

Widget ilusPersonaje(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      // la pantalla de fondo: una lista atenuada
      final pant = Rect.fromLTWH(L * 0.06, L * 0.04, L * 0.88, L * 0.78);
      cv.drawRRect(_caja(pant, L * 0.05), _degradado(pant, const [Color(0xFF1B1F27), Color(0xFF0B0D12)]));
      cv.drawRRect(_caja(pant, L * 0.05), _trazo(Colors.white.withValues(alpha: 0.16), 1.3));
      for (var i = 0; i < 5; i++) {
        final f = Rect.fromLTWH(pant.left + L * 0.04, pant.top + L * (0.04 + i * 0.138), pant.width - L * 0.08, L * 0.105);
        cv.drawRRect(_caja(f, L * 0.02), _relleno(Colors.white.withValues(alpha: 0.05)));
        cv.drawRRect(_caja(Rect.fromLTWH(f.left + L * 0.02, f.top + L * 0.018, L * 0.069, L * 0.069), L * 0.012), _relleno(Color.lerp(c.acento, const Color(0xFF8B6CFF), i / 4)!.withValues(alpha: 0.35)));
        cv.drawRRect(_caja(Rect.fromLTWH(f.left + L * 0.12, f.top + L * 0.025, f.width * (0.5 - 0.05 * (i % 3)), L * 0.014), 99), _relleno(Colors.white.withValues(alpha: 0.22)));
        cv.drawRRect(_caja(Rect.fromLTWH(f.left + L * 0.12, f.top + L * 0.056, f.width * 0.28, L * 0.011), 99), _relleno(Colors.white.withValues(alpha: 0.12)));
      }
      // ruta del personaje: esquina, destino, esquina
      final rincon = Offset(L * 0.76, L * 0.60);
      final meta = Offset(L * 0.30, L * 0.34);
      final ida = _suave(_tramo(s, 2.6, 6.0));
      final vuelta = _suave(_tramo(s, 9.0, 10.4));
      final pos = Offset.lerp(rincon, meta, ida - vuelta)!;
      final cogido = s > 2.4 && s < 6.2;
      final r = L * 0.075;
      final latido = (s % 1.5) / 1.5;
      if (!cogido) {
        cv.drawCircle(pos + Offset(0, r * 1.28), r * (0.7 + 1.1 * latido), _trazo(c.acento.withValues(alpha: (1 - latido) * 0.5), 1.6));
      }
      for (var i = 0; i < 3; i++) {
        final p = ((s / 3) + i / 3) % 1;
        _nota(cv, pos + Offset((i - 1) * r * 1.1 + sin(2 * pi * (s / 3 + i * 0.2)) * r * 0.3, -r * 1.5 - p * r * 2.2), L * 0.017,
            Color.lerp(c.acento, Colors.white, 0.4)!.withValues(alpha: sin(pi * p).clamp(0.0, 1.0) * 0.85));
      }
      // baile suave: salta, se estira y se inclina al compás (cada 1,5 s)
      final beat = sin(pi * (s % 1.5) / 1.5).abs();
      final tilt = cogido ? 0.10 * sin(2 * pi * s / 1.5) : 0.13 * sin(2 * pi * s / 3);
      cv.save();
      cv.translate(pos.dx, pos.dy - (cogido ? r * 0.25 : r * 0.28 * beat));
      cv.rotate(tilt);
      cv.scale(cogido ? 1.10 : 1 - 0.03 * beat, cogido ? 1.10 : 1 + 0.07 * beat);
      _chibi(cv, Offset.zero, r, Color.lerp(c.acento, const Color(0xFFB4A1FF), 0.5)!, 2 * pi * s / 1.5);
      cv.restore();
      // el dedo arrastra y luego toca dos veces
      final d = Offset(L * 0.035, L * 0.075);
      _dedo(cv, pos + d, L * 0.085, _suave(_tramo(s, 2.0, 2.5)) * (1 - _suave(_tramo(s, 6.0, 6.6))));
      _dedo(cv, pos + d, L * 0.085, _suave(_tramo(s, 7.6, 8.0)) * (1 - _suave(_tramo(s, 9.0, 9.4))));
      _toque(cv, pos, L * 0.09, _tramo(s, 8.2, 8.7), Colors.white);
      _toque(cv, pos, L * 0.09, _tramo(s, 8.6, 9.1), Colors.white);
      for (var i = 0; i < 4; i++) {
        _estrella(cv, Offset(L * (0.20 + i * 0.20), L * (0.12 + 0.05 * sin(i * 2.0))), L * (0.008 + 0.014 * _onda(s, 3, i / 4)), Colors.white.withValues(alpha: 0.7));
      }
      // la explicación, abajo
      void leyenda(String t, Color color, double a) {
        if (a <= 0) return;
        cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: a));
        _chip(cv, t, Offset(L / 2, L * 0.905), L * 0.036, color, activo: 0.15);
        cv.restore();
      }

      leyenda('Arrástralo a donde quieras', c.acento, ((1 - _suave(_tramo(s, 6.4, 7.0))) + _suave(_tramo(s, 11.4, 12))).clamp(0.0, 1.0));
      leyenda('Toca dos veces y vuelve a su esquina', const Color(0xFFFFE08A),
          _suave(_tramo(s, 7.4, 8.0)) * (1 - _suave(_tramo(s, 10.8, 11.4))));
    });

// ------------------------------------------------------ enriquece tus listas

Widget ilusEnriquece(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final panel = Rect.fromLTWH(L * 0.06, L * 0.03, L * 0.88, L * 0.94);
      cv.drawRRect(_caja(panel, L * 0.05), _degradado(panel, const [Color(0xFF1B1F27), Color(0xFF0B0D12)]));
      cv.drawRRect(_caja(panel, L * 0.05), _trazo(Colors.white.withValues(alpha: 0.16), 1.3));
      final x0 = L * 0.11, ancho = L * 0.78;

      void cancion(double top, int k, String titulo, String sub, double a,
          {double prev = 0, double anadida = 0, bool acciones = true, double dx = 0}) {
        if (a <= 0) return;
        cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: a));
        cv.translate(dx * (1 - a), 0);
        final f = Rect.fromLTWH(x0, top, ancho, L * 0.082);
        cv.drawRRect(_caja(f, L * 0.02), _relleno(Colors.white.withValues(alpha: 0.06 + 0.06 * anadida)));
        if (anadida > 0) cv.drawRRect(_caja(f, L * 0.02), _trazo(const Color(0xFF4ADE80).withValues(alpha: 0.7 * anadida), 1.3));
        final cov = Rect.fromLTWH(f.left + L * 0.014, f.top + L * 0.013, L * 0.056, L * 0.056);
        cv.drawRRect(_caja(cov, L * 0.012),
            _degradado(cov, [Color.lerp(c.acento, const Color(0xFFFF5C8A), (k % 4) / 3)!, Color.lerp(const Color(0xFF8B6CFF), const Color(0xFF0B0D12), 0.4 + 0.1 * (k % 3))!]));
        _nota(cv, cov.center + Offset(-L * 0.004, L * 0.010), L * 0.011, Colors.white.withValues(alpha: 0.9));
        final lim = acciones ? ancho - L * 0.35 : ancho - L * 0.12;
        _txtIzq(cv, titulo, Offset(f.left + L * 0.085, f.top + L * 0.027), L * 0.036, Colors.white, ancho: lim);
        _txtIzq(cv, sub, Offset(f.left + L * 0.085, f.top + L * 0.057), L * 0.027, Colors.white.withValues(alpha: 0.55), peso: FontWeight.w600, ancho: lim);
        if (acciones) {
          // escuchar un momento
          final pl = Offset(f.right - L * 0.115, f.center.dy);
          cv.drawCircle(pl, L * 0.027, _relleno(Colors.white.withValues(alpha: 0.12)));
          if (prev > 0) {
            cv.drawArc(Rect.fromCircle(center: pl, radius: L * 0.027), -pi / 2, 2 * pi * prev, false, _trazo(c.acento, 2.4));
            cv.drawLine(pl + Offset(-L * 0.006, -L * 0.009), pl + Offset(-L * 0.006, L * 0.009), _trazo(Colors.white, 2.4));
            cv.drawLine(pl + Offset(L * 0.006, -L * 0.009), pl + Offset(L * 0.006, L * 0.009), _trazo(Colors.white, 2.4));
          } else {
            final tri = Path()
              ..moveTo(pl.dx - L * 0.007, pl.dy - L * 0.011)
              ..lineTo(pl.dx + L * 0.011, pl.dy)
              ..lineTo(pl.dx - L * 0.007, pl.dy + L * 0.011)
              ..close();
            cv.drawPath(tri, _relleno(Colors.white.withValues(alpha: 0.9)));
          }
          // añadir
          final mas = Offset(f.right - L * 0.048, f.center.dy);
          final rr = L * 0.027 * (1 + 0.25 * sin(pi * _tramo(anadida, 0, 0.5)));
          cv.drawCircle(mas, rr, _relleno(Color.lerp(c.acento.withValues(alpha: 0.9), const Color(0xFF4ADE80), anadida)!));
          const tinta = Color(0xFF0B0D12);
          if (anadida < 0.5) {
            cv.drawLine(mas + Offset(-L * 0.011, 0), mas + Offset(L * 0.011, 0), _trazo(tinta, 2.4));
            cv.drawLine(mas + Offset(0, -L * 0.011), mas + Offset(0, L * 0.011), _trazo(tinta, 2.4));
          } else {
            cv.drawLine(mas + Offset(-L * 0.010, 0), mas + Offset(-L * 0.002, L * 0.009), _trazo(tinta, 2.6));
            cv.drawLine(mas + Offset(-L * 0.002, L * 0.009), mas + Offset(L * 0.011, -L * 0.009), _trazo(tinta, 2.6));
          }
        }
        cv.restore();
      }

      // cabecera con el botón de las estrellas
      _txtIzq(cv, 'Mi lista', Offset(x0 + L * 0.01, L * 0.105), L * 0.050, Colors.white, ancho: L * 0.5);
      final bt = Offset(L * 0.82, L * 0.105);
      final pulso = 1 + 0.10 * _onda(s, 1.5) * (s < 2 ? 1 : 0);
      cv.drawCircle(bt, L * 0.060 * pulso, Paint()..color = c.acento.withValues(alpha: 0.45)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.022));
      cv.drawCircle(bt, L * 0.048 * pulso, _degradado(Rect.fromCircle(center: bt, radius: L * 0.048), [Color.lerp(c.acento, Colors.white, 0.2)!, const Color(0xFF8B6CFF)]));
      _estrella(cv, bt + Offset(-L * 0.004, L * 0.003), L * 0.030, Colors.white);
      _estrella(cv, bt + Offset(L * 0.022, -L * 0.020), L * 0.014, Colors.white);
      _estrella(cv, bt + Offset(L * 0.020, L * 0.022), L * 0.010, Colors.white.withValues(alpha: 0.85));
      _toque(cv, bt, L * 0.10, _tramo(s, 1.6, 2.3), Colors.white);
      _dedo(cv, bt + Offset(L * 0.03, L * 0.06), L * 0.075, _suave(_tramo(s, 1.2, 1.5)) * (1 - _suave(_tramo(s, 2.0, 2.4))));

      cancion(L * 0.175, 0, 'Noche de verano', 'Tu lista', 1, acciones: false);
      cancion(L * 0.265, 1, 'Cielo abierto', 'Tu lista', 1, acciones: false);

      // sugerencias
      final fin = 1 - _suave(_tramo(s, 11.2, 12));
      final sec = _suave(_tramo(s, 2.0, 2.6)) * fin;
      if (sec > 0) {
        cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: sec));
        cv.drawLine(Offset(x0, L * 0.395), Offset(x0 + ancho, L * 0.395), _trazo(Colors.white.withValues(alpha: 0.14), 1.2));
        cv.drawRect(Rect.fromLTWH(x0 + L * 0.005, L * 0.375, L * 0.50, L * 0.04), _relleno(const Color(0xFF14171D)));
        _estrella(cv, Offset(x0 + L * 0.02, L * 0.395), L * 0.016, c.acento);
        _txtIzq(cv, 'SUGERENCIAS PARA TI', Offset(x0 + L * 0.05, L * 0.395), L * 0.028, c.acento, ancho: L * 0.45);
        cv.restore();
      }
      const titulos = ['Camino al sol', 'Luces de ciudad', 'Eco de ayer', 'Sin frenos'];
      const subs = ['Parecida a tu lista', 'Mismo artista', 'Parecida a tu lista', 'Mismo artista'];
      final anadidas = [0.0, _suave(_tramo(s, 6.4, 6.9)), 0.0, _suave(_tramo(s, 10.4, 10.9))];
      final prevs = [0.0, _tramo(s, 4.2, 6.2), 0.0, _tramo(s, 8.2, 10.2)];
      for (var i = 0; i < 4; i++) {
        final a = _suave(_tramo(s, 2.4 + i * 0.35, 3.1 + i * 0.35)) * fin;
        final enPrev = prevs[i] > 0 && prevs[i] < 1;
        cancion(L * (0.425 + i * 0.100), i + 2, titulos[i], subs[i], a, prev: enPrev ? prevs[i] : 0, anadida: anadidas[i], dx: L * 0.06);
      }
      // los dedos que escuchan y añaden
      void toca(int fila, double t0, double t1, double dx) {
        final a = _suave(_tramo(s, t0, t0 + 0.3)) * (1 - _suave(_tramo(s, t1 - 0.3, t1)));
        _dedo(cv, Offset(x0 + ancho - dx + L * 0.03, L * (0.425 + fila * 0.100) + L * 0.041 + L * 0.05), L * 0.075, a);
      }

      toca(1, 3.8, 4.4, L * 0.115);
      toca(1, 6.2, 6.9, L * 0.048);
      toca(3, 7.8, 8.4, L * 0.115);
      toca(3, 10.2, 10.9, L * 0.048);
      _txt(cv, 'Escúchalas un momento y añade las que quieras', Offset(L / 2, L * 0.915), L * 0.029, Colors.white.withValues(alpha: 0.7), peso: FontWeight.w700, ancho: L * 0.80);
    });

// -------------------------------------------------------- regala una prueba

Widget ilusRegalo(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final centro = Offset(L / 2, L * 0.62);
      final cw = L * 0.34, ch = L * 0.20, tapa = L * 0.075;
      // tiempos: espera, abre, sube el boleto, aguanta, baja, cierra
      final abre = _suave(_tramo(s, 1.5, 2.3)) - _suave(_tramo(s, 11.2, 12));
      final sube = _suave(_tramo(s, 2.2, 4.0)) - _suave(_tramo(s, 10.0, 11.2));
      final meneo = s < 1.5 ? sin(2 * pi * s * 2) * 0.05 * _suave(_tramo(s, 0.2, 0.6)) : 0.0;

      // luz que sale de la caja
      final luz = centro + Offset(0, -ch * 0.3);
      cv.drawCircle(luz, L * 0.30 * abre + 0.1,
          Paint()..shader = RadialGradient(colors: [const Color(0xFFFFE08A).withValues(alpha: 0.5 * abre), const Color(0x00FFE08A)]).createShader(Rect.fromCircle(center: luz, radius: L * 0.30 * abre + 0.1)));

      // el boleto sale de la caja
      final bw = L * 0.66, bh = L * 0.20;
      final by = _lerp(centro.dy - ch * 0.2, L * 0.20, sube);
      if (sube > 0.01) {
        cv.save();
        cv.translate(L / 2, by);
        cv.rotate(-0.04 * sube);
        final r = Rect.fromCenter(center: Offset.zero, width: bw, height: bh);
        final ruta = Path()..addRRect(_caja(r, L * 0.04));
        final muesca = Path()
          ..addOval(Rect.fromCircle(center: Offset(r.left, 0), radius: bh * 0.12))
          ..addOval(Rect.fromCircle(center: Offset(r.right, 0), radius: bh * 0.12));
        final boleto = Path.combine(PathOperation.difference, ruta, muesca);
        cv.drawPath(boleto.shift(Offset(0, L * 0.015)), Paint()..color = Colors.black.withValues(alpha: 0.4)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.025));
        cv.drawPath(boleto, _degradado(r, const [Color(0xFFFFE08A), Color(0xFFF5C542), Color(0xFFD99A12)]));
        const tinta = Color(0xFF3A2800);
        final x0 = r.left + bw * 0.31;
        for (var y = r.top + bh * 0.12; y < r.bottom - bh * 0.1; y += bh * 0.10) {
          cv.drawLine(Offset(x0, y), Offset(x0, y + bh * 0.05), _trazo(tinta.withValues(alpha: 0.5), 1.5));
        }
        _txt(cv, '7', Offset(r.left + bw * 0.155, -bh * 0.06), L * 0.105, tinta, peso: FontWeight.w900);
        _txt(cv, 'DÍAS', Offset(r.left + bw * 0.155, bh * 0.26), L * 0.030, tinta, espacio: 1.2);
        final cc = Offset(r.left + bw * 0.655, 0);
        _txt(cv, 'REGALO DE PRUEBA', cc + Offset(0, -bh * 0.27), L * 0.028, tinta, espacio: 0.8, ancho: bw * 0.64);
        _txt(cv, 'R7K2-9QMD', cc + Offset(0, bh * 0.04), L * 0.062, tinta, espacio: 1.2, ancho: bw * 0.64);
        _txt(cv, 'beneficios de donador', cc + Offset(0, bh * 0.31), L * 0.027, tinta.withValues(alpha: 0.75), peso: FontWeight.w700, ancho: bw * 0.64);
        cv.restore();
      }

      // la caja
      cv.save();
      cv.translate(centro.dx, centro.dy + ch / 2);
      cv.rotate(meneo);
      cv.translate(0, -ch / 2);
      final cuerpo = Rect.fromCenter(center: Offset.zero, width: cw, height: ch);
      cv.drawRRect(_caja(cuerpo, L * 0.02).shift(Offset(0, L * 0.02)), Paint()..color = Colors.black.withValues(alpha: 0.4)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.03));
      cv.drawRRect(_caja(cuerpo, L * 0.02), _degradado(cuerpo, const [Color(0xFFFF5C8A), Color(0xFFB0285A)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
      cv.drawRect(Rect.fromCenter(center: Offset.zero, width: cw * 0.16, height: ch), _relleno(const Color(0xFFFFE08A)));
      // tapa: se levanta y se inclina al abrir
      cv.save();
      cv.translate(cw * 0.36 * abre, -ch / 2 - tapa / 2 - L * 0.035 * abre);
      cv.rotate(0.75 * abre);
      final tp = Rect.fromCenter(center: Offset.zero, width: cw * 1.1, height: tapa);
      cv.drawRRect(_caja(tp, L * 0.015), _degradado(tp, const [Color(0xFFFF8AB0), Color(0xFFD23B72)], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
      cv.drawRect(Rect.fromCenter(center: Offset.zero, width: cw * 0.16, height: tapa), _relleno(const Color(0xFFFFE08A)));
      for (final lado in const [-1.0, 1.0]) {
        final lazo = Path()
          ..moveTo(0, -tapa / 2)
          ..cubicTo(lado * cw * 0.20, -tapa * 2.1, lado * cw * 0.36, -tapa * 0.6, 0, -tapa / 2);
        cv.drawPath(lazo, _relleno(const Color(0xFFFFE08A)));
        cv.drawPath(lazo, _trazo(const Color(0xFFD99A12), 1.4));
      }
      cv.restore();
      cv.restore();

      // confeti cuando se abre
      const paleta = [Color(0xFFFFE08A), Color(0xFFFF5C8A), Color(0xFF8B6CFF), Color(0xFF22D3EE), Color(0xFF4ADE80)];
      final q = _tramo(s, 2.0, 5.5);
      if (q > 0 && q < 1) {
        for (var i = 0; i < 22; i++) {
          final ang = -pi / 2 + (i / 22 - 0.5) * 2.4;
          final v = L * (0.25 + 0.30 * ((i * 0.618) % 1));
          final px = centro.dx + cos(ang) * v * q;
          final py = centro.dy - ch / 2 + sin(ang) * v * q + L * 0.25 * q * q;
          cv.save();
          cv.translate(px, py);
          cv.rotate(i + 6 * q);
          cv.drawRRect(_caja(Rect.fromCenter(center: Offset.zero, width: L * 0.022, height: L * 0.011), 2), _relleno(paleta[i % 5].withValues(alpha: 1 - q)));
          cv.restore();
        }
      }
      for (var i = 0; i < 5; i++) {
        _estrella(cv, Offset(L * (0.12 + i * 0.19), L * (0.045 + 0.02 * sin(i * 1.7))), L * (0.008 + 0.018 * _onda(s, 3, i / 5)), const Color(0xFFFFE08A).withValues(alpha: 0.8));
      }

      // tres amigos lo reciben
      const nombres = ['Ana', 'Leo', 'Sol'];
      for (var i = 0; i < 3; i++) {
        final x = L * (0.5 + (i - 1) * 0.28);
        final ap = _suave(_tramo(s, 4.4 + i * 0.7, 5.2 + i * 0.7)) * (1 - _suave(_tramo(s, 11.2, 12)));
        cv.drawLine(Offset(L / 2, L * 0.745), Offset(x, L * 0.835), _trazo(_oro.withValues(alpha: 0.35 * ap), 1.4));
        _avatar(cv, Offset(x, L * 0.875), L * 0.045, Color.lerp(c.acento, const Color(0xFFFF5C8A), i / 2)!, const Color(0xFF14101F));
        final ins = Rect.fromCenter(center: Offset(x, L * 0.955), width: L * 0.17, height: L * 0.042);
        _txt(cv, nombres[i], ins.center, L * 0.026, Colors.white.withValues(alpha: 0.6 * (1 - ap)), peso: FontWeight.w700);
        if (ap > 0) {
          cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: ap));
          cv.drawRRect(_caja(ins, 99), _relleno(_oro));
          _txt(cv, '+7 días', ins.center, L * 0.026, const Color(0xFF3A2800), ancho: ins.width - 6);
          cv.restore();
        }
      }
    });

// ------------------------------------------------------- escuchar más cómodo

Widget ilusComodo(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final panel = Rect.fromLTWH(L * 0.06, L * 0.03, L * 0.88, L * 0.94);
      cv.drawRRect(_caja(panel, L * 0.05), _degradado(panel, const [Color(0xFF1B1F27), Color(0xFF0B0D12)]));
      cv.drawRRect(_caja(panel, L * 0.05), _trazo(Colors.white.withValues(alpha: 0.16), 1.3));

      // carátulas: se desliza una a otra (dos pasadas por vuelta, siempre hacia la izquierda)
      final q = _suave(_tramo(s, 3.5, 4.5)) + _suave(_tramo(s, 9.5, 10.5));
      const lado = 0.34;
      final cy = L * 0.235;
      cv.save();
      cv.clipRRect(_caja(panel.deflate(2), L * 0.05));
      for (var n = 0; n < 3; n++) {
        final cx = L / 2 + (n - q) * L * 0.56;
        if ((cx - L / 2).abs() > L * 0.6) continue;
        final r = Rect.fromCenter(center: Offset(cx, cy), width: L * lado, height: L * lado);
        final a = n % 2 == 0 ? const [Color(0xFFFF8A3D), Color(0xFF8B6CFF)] : const [Color(0xFF22D3EE), Color(0xFFFF5C8A)];
        cv.drawRRect(_caja(r, L * 0.04).shift(Offset(0, L * 0.015)), Paint()..color = Colors.black.withValues(alpha: 0.45)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.025));
        cv.drawRRect(_caja(r, L * 0.04), _degradado(r, a));
        for (var k = 0; k < 3; k++) {
          cv.drawCircle(r.center, L * (0.06 + k * 0.045), _trazo(Colors.white.withValues(alpha: 0.10), 1.2));
        }
        _nota(cv, r.center + Offset(-L * 0.015, L * 0.035), L * 0.045, Colors.white.withValues(alpha: 0.9));
      }
      cv.restore();

      // doble toque = me gusta
      final centroCar = Offset(L / 2, cy);
      _toque(cv, centroCar, L * 0.10, _tramo(s, 1.4, 1.9), Colors.white);
      _toque(cv, centroCar, L * 0.10, _tramo(s, 1.75, 2.25), Colors.white);
      final h = _tramo(s, 1.75, 3.0);
      if (h > 0 && h < 1) {
        final esc = L * 0.055 * (0.4 + 0.9 * sin(pi * min(1.0, h * 2.2)).clamp(0.0, 1.0) + 0.4 * h);
        cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: 1 - _suave(_tramo(h, 0.6, 1))));
        _icono(cv, Icons.favorite_rounded, centroCar + Offset(0, -L * 0.05 * h), esc * 2, const Color(0xFFFF5C8A));
        cv.restore();
      }
      // dedos: doble toque y deslizar
      _dedo(cv, centroCar + Offset(L * 0.04, L * 0.08), L * 0.08, _suave(_tramo(s, 1.0, 1.3)) * (1 - _suave(_tramo(s, 2.3, 2.7))));
      for (final t0 in const [3.2, 9.2]) {
        final p = _suave(_tramo(s, t0 + 0.3, t0 + 1.3));
        _dedo(cv, Offset(_lerp(L * 0.68, L * 0.34, p), cy + L * 0.10), L * 0.08,
            _suave(_tramo(s, t0, t0 + 0.3)) * (1 - _suave(_tramo(s, t0 + 1.2, t0 + 1.6))));
      }
      // aviso «tocar después de esta»
      final toast = _suave(_tramo(s, 5.2, 5.6)) * (1 - _suave(_tramo(s, 6.5, 6.9)));
      if (toast > 0) {
        cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: toast));
        _chip(cv, 'Sonará después de esta', Offset(L / 2, L * 0.395), L * 0.032, const Color(0xFF4ADE80), activo: 0.9);
        cv.restore();
      }

      // barra de progreso: los sets largos retoman donde se dejaron
      final barra = Rect.fromLTWH(L * 0.14, L * 0.485, L * 0.72, L * 0.012);
      cv.drawRRect(_caja(barra, 99), _relleno(Colors.white.withValues(alpha: 0.14)));
      final f = 0.56 + 0.04 * s / 12;
      cv.drawRRect(_caja(Rect.fromLTWH(barra.left, barra.top, barra.width * f, barra.height), 99), _relleno(c.acento));
      cv.drawCircle(Offset(barra.left + barra.width * f, barra.center.dy), L * 0.017, _relleno(Colors.white));
      _txtIzq(cv, '1:12:40', Offset(barra.left, L * 0.520), L * 0.026, Colors.white.withValues(alpha: 0.6), peso: FontWeight.w700);
      _txt(cv, 'retoma aquí', Offset(barra.left + barra.width * f, L * 0.520), L * 0.026, c.acento, peso: FontWeight.w800);
      final tp = TextPainter(
        text: TextSpan(text: '2:05:00', style: TextStyle(fontSize: L * 0.026, color: Colors.white.withValues(alpha: 0.6), fontWeight: FontWeight.w700, fontFamily: familiaIlustraciones)),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(cv, Offset(barra.right - tp.width, L * 0.520 - tp.height / 2));

      // controles: anterior, play y pausa suaves, siguiente
      final cc = Offset(L / 2, L * 0.592);
      final pausa = _suave(_tramo(s, 6.0, 6.4)) - _suave(_tramo(s, 8.0, 8.4));
      cv.drawCircle(cc, L * 0.050, _degradado(Rect.fromCircle(center: cc, radius: L * 0.05), [Color.lerp(c.acento, Colors.white, 0.15)!, c.acento]));
      final bar = _trazo(const Color(0xFF0B0D12), L * 0.012);
      cv.save();
      cv.translate(cc.dx, cc.dy);
      cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: 1 - pausa));
      cv.scale(1 - 0.4 * pausa);
      cv.drawLine(Offset(-L * 0.011, -L * 0.017), Offset(-L * 0.011, L * 0.017), bar);
      cv.drawLine(Offset(L * 0.011, -L * 0.017), Offset(L * 0.011, L * 0.017), bar);
      cv.restore();
      cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: pausa));
      cv.scale(0.6 + 0.4 * pausa);
      cv.drawPath(Path()..moveTo(-L * 0.010, -L * 0.019)..lineTo(L * 0.018, 0)..lineTo(-L * 0.010, L * 0.019)..close(), _relleno(const Color(0xFF0B0D12)));
      cv.restore();
      cv.restore();
      for (final lado in const [-1.0, 1.0]) {
        final o = Offset(L / 2 + lado * L * 0.18, cc.dy);
        final d = -lado; // a la izquierda anterior, a la derecha siguiente
        final t = Path()
          ..moveTo(o.dx + d * L * 0.012, o.dy - L * 0.017)
          ..lineTo(o.dx - d * L * 0.012, o.dy)
          ..lineTo(o.dx + d * L * 0.012, o.dy + L * 0.017)
          ..close();
        cv.drawPath(t, _relleno(Colors.white.withValues(alpha: 0.8)));
        cv.drawLine(Offset(o.dx - d * L * 0.018, o.dy - L * 0.017), Offset(o.dx - d * L * 0.018, o.dy + L * 0.017), _trazo(Colors.white.withValues(alpha: 0.8), 2));
      }

      // la cola: se reordena y se guarda como lista
      final cola = Rect.fromLTWH(L * 0.11, L * 0.665, L * 0.78, L * 0.285);
      cv.drawRRect(_caja(cola, L * 0.03), _relleno(Colors.white.withValues(alpha: 0.04)));
      _txtIzq(cv, 'COLA', Offset(cola.left + L * 0.025, cola.top + L * 0.032), L * 0.028, Colors.white.withValues(alpha: 0.6));
      final press = _suave(_tramo(s, 8.4, 8.8)) * (1 - _suave(_tramo(s, 9.2, 9.6)));
      _chip(cv, 'Guardar como lista', Offset(cola.right - L * 0.165, cola.top + L * 0.034), L * 0.024, c.acento, activo: press);
      final swap = _suave(_tramo(s, 7.0, 7.8)) - _suave(_tramo(s, 11.0, 11.8));
      const titulos = ['Noche de verano', 'Cielo abierto', 'Luces de ciudad'];
      for (var i = 0; i < 3; i++) {
        var pos = i.toDouble();
        if (i == 1) pos += swap;
        if (i == 2) pos -= swap;
        final levanta = (i == 1 || i == 2) ? sin(pi * swap.clamp(0.0, 1.0)) : 0.0;
        final y = cola.top + L * 0.062 + pos * L * 0.070;
        final fila = Rect.fromLTWH(cola.left + L * 0.02, y, cola.width - L * 0.04, L * 0.058);
        cv.drawRRect(_caja(fila, L * 0.016), _relleno(Colors.white.withValues(alpha: 0.07 + 0.08 * (i == 1 ? levanta : 0))));
        final cov = Rect.fromLTWH(fila.left + L * 0.010, fila.top + L * 0.009, L * 0.040, L * 0.040);
        cv.drawRRect(_caja(cov, L * 0.008), _degradado(cov, [Color.lerp(c.acento, const Color(0xFFFF5C8A), i / 2)!, const Color(0xFF2A2140)]));
        _txtIzq(cv, titulos[i], Offset(fila.left + L * 0.065, fila.center.dy), L * 0.032, Colors.white, ancho: fila.width - L * 0.17);
        for (var k = 0; k < 3; k++) {
          cv.drawLine(Offset(fila.right - L * 0.050, fila.center.dy + (k - 1) * L * 0.011), Offset(fila.right - L * 0.020, fila.center.dy + (k - 1) * L * 0.011), _trazo(Colors.white.withValues(alpha: 0.5), 1.6));
        }
      }
    });

// ------------------------------------------------------------------- gracias

Widget ilusGracias(Ctx c, double L) => Stack(alignment: Alignment.center, children: [
      Positioned.fill(
        child: _lienzo(c, L, (cv, z, s) {
          final ctr = Offset(L / 2, L * 0.46);
          final rad = L * (0.36 + 0.03 * _onda(s, 4));
          cv.drawCircle(ctr, rad, Paint()..shader = RadialGradient(colors: [c.acento.withValues(alpha: 0.38), c.acento.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: ctr, radius: rad)));
          // un ecualizador en círculo, como si el logo escuchara
          const n = 40;
          for (var i = 0; i < n; i++) {
            final ang = 2 * pi * i / n - pi / 2;
            final amp = 0.25 + 0.75 * _onda(s * 2 + i * 0.35, 3, (i % 5) * 0.13);
            final r0 = L * 0.235, r1 = r0 + L * 0.075 * amp;
            final col = Color.lerp(c.acento, const Color(0xFFFF5C8A), 0.5 + 0.5 * sin(ang + 2 * pi * s / 12))!;
            cv.drawLine(ctr + Offset(cos(ang), sin(ang)) * r0, ctr + Offset(cos(ang), sin(ang)) * r1, _trazo(col.withValues(alpha: 0.9), L * 0.011));
          }
          // corazones y notas que suben
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
          _chip(cv, 'CAUDAL 2.5.0', Offset(L / 2, L * 0.90), L * 0.034, c.acento, activo: 0.15 + 0.15 * _onda(s, 4));
        }),
      ),
      Align(
        alignment: const Alignment(0, -0.08),
        child: AnimatedBuilder(
          animation: c.reloj,
          builder: (_, _) => Transform.scale(
            scale: 1 + 0.04 * _onda(c.s, 4),
            child: SizedBox(width: L * 0.30, height: L * 0.30, child: logoConDestello(c, L * 0.30)),
          ),
        ),
      ),
    ]);
