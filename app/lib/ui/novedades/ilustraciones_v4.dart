// Ilustraciones de la tercera actualización grande. Es parte de ilustraciones.dart
// para usar sus utilidades (lienzo, ondas, estrellas...) y su reloj de 12 s.
part of 'ilustraciones.dart';

// ---------------------------------------------------------------- utilidades

/// Solo para las pruebas: la tipografía con la que se pintan los textos del lienzo.
@visibleForTesting
String? familiaIlustraciones;

void _txt(Canvas cv, String t, Offset centro, double tam, Color color,
    {FontWeight peso = FontWeight.w800, double espacio = 0, double? ancho, double resplandor = 0}) {
  final tp = TextPainter(
    text: TextSpan(
      text: t,
      style: TextStyle(
        fontSize: tam,
        // con resplandor el texto se pinta difuminado (un halo), sin agrandarlo
        color: resplandor > 0 ? null : color,
        foreground: resplandor > 0 ? (Paint()..color = color..maskFilter = MaskFilter.blur(BlurStyle.normal, resplandor)) : null,
        fontWeight: peso,
        letterSpacing: espacio,
        height: 1.1,
        fontFamily: familiaIlustraciones,
      ),
    ),
    textDirection: TextDirection.ltr,
    maxLines: 1,
    ellipsis: '…',
  )..layout(maxWidth: ancho ?? double.infinity);
  tp.paint(cv, centro - Offset(tp.width / 2, tp.height / 2));
}

RRect _caja(Rect r, double radio) => RRect.fromRectAndRadius(r, Radius.circular(radio));

Paint _relleno(Color c) => Paint()..color = c;

Paint _degradado(Rect r, List<Color> colores, {Alignment ini = Alignment.topLeft, Alignment fin = Alignment.bottomRight}) =>
    Paint()..shader = LinearGradient(begin: ini, end: fin, colors: colores).createShader(r);

/// Una persona recortada en un círculo (la «foto» de un avatar de ejemplo).
void _avatar(Canvas cv, Offset ctr, double R, Color a, Color b) {
  final caja = Rect.fromCircle(center: ctr, radius: R);
  cv.drawCircle(ctr, R, _degradado(caja, [a, b]));
  cv.save();
  cv.clipPath(Path()..addOval(caja));
  _persona(cv, ctr + Offset(0, R * 0.14), R * 1.3, Colors.white.withValues(alpha: 0.88));
  cv.restore();
}

/// Un anillo de colores que gira alrededor de un avatar.
void _anillo(Canvas cv, Offset ctr, double R, double grosor, List<Color> colores, double giro) {
  final caja = Rect.fromCircle(center: ctr, radius: R);
  cv.drawCircle(
    ctr,
    R,
    Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = grosor
      ..shader = SweepGradient(colors: [...colores, colores.first], transform: GradientRotation(giro)).createShader(caja),
  );
}

/// Un teléfono de lado L*ancho con la pantalla ya recortada; devuelve la pantalla.
Rect _telefono(Canvas cv, Offset ctr, double ancho, double alto, {Color marco = const Color(0xFF1B1F27)}) {
  final cuerpo = Rect.fromCenter(center: ctr, width: ancho, height: alto);
  final rr = _caja(cuerpo, ancho * 0.14);
  cv.drawRRect(rr.shift(Offset(0, ancho * 0.05)),
      Paint()..color = Colors.black.withValues(alpha: 0.45)..maskFilter = MaskFilter.blur(BlurStyle.normal, ancho * 0.08));
  cv.drawRRect(rr, _degradado(cuerpo, [marco, const Color(0xFF0B0D12)]));
  cv.drawRRect(rr, _trazo(Colors.white.withValues(alpha: 0.22), 1.3));
  return cuerpo.deflate(ancho * 0.04);
}

// ------------------------------------------------------ marcos y nombres

Widget ilusMarcos(Ctx c, double L) {
  final tam = max(12.0, L * 0.075);
  return Stack(alignment: Alignment.center, children: [
    Positioned.fill(
      child: _lienzo(c, L, (cv, z, s) {
        final ctr = Offset(L / 2, L * 0.40);
        final R = L * 0.19;
        cv.drawCircle(
          ctr,
          R * 2.1,
          Paint()..shader = RadialGradient(colors: [c.acento.withValues(alpha: 0.30), c.acento.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: ctr, radius: R * 2.1)),
        );
        _avatar(cv, ctr, R, Color.lerp(c.acento, Colors.white, 0.12)!, Color.lerp(c.acento, Colors.black, 0.6)!);
        // aurora: gira entera cada 6 s
        _anillo(cv, ctr, R + L * 0.028, L * 0.034,
            const [Color(0xFF22D3EE), Color(0xFF8B6CFF), Color(0xFFFF5C8A), Color(0xFF22D3EE)], 2 * pi * s / 6);
        // los otros marcos, más pequeños, orbitando despacio
        const otros = [
          [Color(0xFFB8860B), Color(0xFFFFE08A), Color(0xFFF5C542), Color(0xFF9A6B06)],
          [Color(0xFFFF3D00), Color(0xFFFFB000), Color(0xFFFF6A00), Color(0xFFD50000)],
          [Color(0xFFB3E5FC), Color(0xFFFFFFFF), Color(0xFF4FC3F7), Color(0xFF81D4FA)],
        ];
        const fondos = [Color(0xFF5B4A1A), Color(0xFF5A2A1A), Color(0xFF1A4A66)];
        for (var i = 0; i < 3; i++) {
          final ang = 2 * pi * (i / 3 + s / 24) - pi / 2 + 0.6;
          final o = ctr + Offset(cos(ang) * L * 0.36, sin(ang) * L * 0.20);
          final r = L * 0.07;
          _avatar(cv, o, r, fondos[i], const Color(0xFF14101F));
          _anillo(cv, o, r + L * 0.011, L * 0.015, otros[i], 2 * pi * (s / 4 + i * 0.3));
        }
        _estrella(cv, ctr + Offset(R * 1.0, -R * 0.95), L * (0.012 + 0.022 * _onda(s, 3)), Colors.white);
        _estrella(cv, ctr + Offset(-R * 1.05, R * 0.5), L * (0.010 + 0.020 * _onda(s, 4, 0.4)), Colors.white);
      }),
    ),
    // el nombre con efecto: brillo que lo cruza
    Align(
      alignment: const Alignment(0, 0.80),
      child: AnimatedBuilder(
        animation: c.reloj,
        builder: (_, _) {
          final q = (c.s % 3) / 3;
          return ShaderMask(
            blendMode: BlendMode.srcIn,
            shaderCallback: (r) => LinearGradient(
              colors: const [Color(0xFF22D3EE), Color(0xFF8B6CFF), Color(0xFFFF5C8A), Color(0xFFF5C542), Color(0xFF22D3EE)],
              transform: _Desliza(_lerp(-1, 1, q)),
            ).createShader(r),
            child: Text('Valentina', style: TextStyle(fontSize: tam * 1.5, fontWeight: FontWeight.w900, color: Colors.white, letterSpacing: 0.4)),
          );
        },
      ),
    ),
    Align(
      alignment: const Alignment(0, 0.97),
      child: Text('marcos animados · nombres con efecto',
          style: TextStyle(fontSize: tam * 0.62, fontWeight: FontWeight.w700, color: Colors.white.withValues(alpha: 0.6), letterSpacing: 0.6)),
    ),
  ]);
}

// ---------------------------------------------------------------- temas

class _PaletaIlus {
  const _PaletaIlus(this.nombre, this.fondo, this.superficie, this.acento);
  final String nombre;
  final Color fondo;
  final Color superficie;
  final Color acento;
}

const _paletasIlus = [
  _PaletaIlus('Atardecer', Color(0xFF2B1224), Color(0xFF3F1B33), Color(0xFFFF8A3D)),
  _PaletaIlus('Bosque', Color(0xFF0E2218), Color(0xFF16352A), Color(0xFF4ADE80)),
  _PaletaIlus('Sakura', Color(0xFF2A1621), Color(0xFF3B1F2E), Color(0xFFFF9EC4)),
  _PaletaIlus('Océano', Color(0xFF0A1F33), Color(0xFF10304D), Color(0xFF38BDF8)),
  _PaletaIlus('Medianoche', Color(0xFF0E1030), Color(0xFF181B49), Color(0xFF8B6CFF)),
  _PaletaIlus('Ámbar', Color(0xFF241A06), Color(0xFF38280A), Color(0xFFF5C542)),
];

Widget ilusTemas(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      // cada tema dura 2 s y se mezcla con el siguiente en el último medio segundo
      final i = (s ~/ 2) % 6;
      final t = _suave(((s % 2) - 1.5) / 0.5);
      final a = _paletasIlus[i], b = _paletasIlus[(i + 1) % 6];
      final fondo = Color.lerp(a.fondo, b.fondo, t)!;
      final sup = Color.lerp(a.superficie, b.superficie, t)!;
      final ac = Color.lerp(a.acento, b.acento, t)!;
      final pant = _telefono(cv, Offset(L / 2, L * 0.46), L * 0.40, L * 0.70);
      cv.drawRRect(_caja(pant, L * 0.05), _relleno(fondo));
      cv.save();
      cv.clipRRect(_caja(pant, L * 0.05));
      // cabecera
      cv.drawRect(Rect.fromLTWH(pant.left, pant.top, pant.width, pant.height * 0.14), _relleno(sup));
      cv.drawRRect(_caja(Rect.fromLTWH(pant.left + pant.width * 0.08, pant.top + pant.height * 0.05, pant.width * 0.34, pant.height * 0.035), 99),
          _relleno(ac));
      // tarjeta grande
      final gr = Rect.fromLTWH(pant.left + pant.width * 0.08, pant.top + pant.height * 0.19, pant.width * 0.84, pant.height * 0.26);
      cv.drawRRect(_caja(gr, L * 0.03), _degradado(gr, [ac, Color.lerp(ac, fondo, 0.7)!]));
      // filas
      for (var k = 0; k < 3; k++) {
        final y = pant.top + pant.height * (0.50 + k * 0.10);
        final f = Rect.fromLTWH(pant.left + pant.width * 0.08, y, pant.width * 0.84, pant.height * 0.08);
        cv.drawRRect(_caja(f, L * 0.02), _relleno(sup));
        cv.drawRRect(_caja(Rect.fromLTWH(f.left + f.width * 0.05, f.top + f.height * 0.18, f.height * 0.64, f.height * 0.64), L * 0.012),
            _relleno(ac.withValues(alpha: 0.85 - k * 0.2)));
        cv.drawRRect(_caja(Rect.fromLTWH(f.left + f.width * 0.30, f.top + f.height * 0.30, f.width * (0.42 - k * 0.06), f.height * 0.16), 99),
            _relleno(Colors.white.withValues(alpha: 0.75)));
        cv.drawRRect(_caja(Rect.fromLTWH(f.left + f.width * 0.30, f.top + f.height * 0.58, f.width * 0.26, f.height * 0.12), 99),
            _relleno(Colors.white.withValues(alpha: 0.35)));
      }
      // barra de reproducción
      final bar = Rect.fromLTWH(pant.left, pant.bottom - pant.height * 0.10, pant.width, pant.height * 0.10);
      cv.drawRect(bar, _relleno(sup));
      cv.drawCircle(Offset(bar.center.dx, bar.center.dy), bar.height * 0.30, _relleno(ac));
      cv.restore();
      // las seis paletas debajo; la activa crece
      for (var k = 0; k < 6; k++) {
        final activo = k == i ? 1 - t : (k == (i + 1) % 6 ? t : 0.0);
        final x = L * (0.5 + (k - 2.5) * 0.105);
        final r = L * (0.022 + 0.014 * activo);
        cv.drawCircle(Offset(x, L * 0.885), r, _relleno(_paletasIlus[k].acento));
        if (activo > 0.5) cv.drawCircle(Offset(x, L * 0.885), r + L * 0.012, _trazo(Colors.white.withValues(alpha: 0.9), 1.6));
      }
      _txt(cv, (t > 0.5 ? b : a).nombre, Offset(L / 2, L * 0.955), L * 0.040, Colors.white.withValues(alpha: 0.85), peso: FontWeight.w800);
    });

// ------------------------------------------------------------ pase de prueba

Widget ilusPase(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final ctr = Offset(L / 2, L * 0.44);
      final flota = sin(2 * pi * s / 6) * L * 0.012;
      cv.save();
      cv.translate(ctr.dx, ctr.dy + flota);
      cv.rotate(-0.07 + 0.02 * sin(2 * pi * s / 6));
      final w = L * 0.74, h = L * 0.40;
      final r = Rect.fromCenter(center: Offset.zero, width: w, height: h);
      // boleto con muescas a los lados
      final ruta = Path()..addRRect(_caja(r, L * 0.05));
      final muesca = Path()
        ..addOval(Rect.fromCircle(center: Offset(r.left, 0), radius: h * 0.10))
        ..addOval(Rect.fromCircle(center: Offset(r.right, 0), radius: h * 0.10));
      final boleto = Path.combine(PathOperation.difference, ruta, muesca);
      cv.drawPath(boleto.shift(Offset(0, L * 0.02)), Paint()..color = Colors.black.withValues(alpha: 0.4)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.03));
      cv.drawPath(boleto, _degradado(r, const [Color(0xFFFFE08A), Color(0xFFF5C542), Color(0xFFD99A12)]));
      // línea punteada que separa la parte del código
      final x0 = r.left + w * 0.355;
      for (var y = r.top + h * 0.10; y < r.bottom - h * 0.08; y += h * 0.085) {
        cv.drawLine(Offset(x0, y), Offset(x0, y + h * 0.04), _trazo(const Color(0xFF3A2800).withValues(alpha: 0.5), 1.6));
      }
      // los días, en un anillo que se llena
      final cd = Offset(r.left + w * 0.185, 0);
      cv.drawCircle(cd, h * 0.24, _trazo(const Color(0xFF3A2800).withValues(alpha: 0.18), L * 0.018));
      final llena = _suave((s % 6) / 5);
      cv.drawArc(Rect.fromCircle(center: cd, radius: h * 0.24), -pi / 2, 2 * pi * llena, false, _trazo(const Color(0xFF3A2800), L * 0.018));
      _txt(cv, '7', cd + Offset(0, -h * 0.03), L * 0.095, const Color(0xFF3A2800), peso: FontWeight.w900);
      _txt(cv, 'DÍAS', cd + Offset(0, h * 0.14), L * 0.026, const Color(0xFF3A2800), espacio: 1.0);
      // el código
      final centro = Offset(r.left + w * 0.68, 0);
      _txt(cv, 'PASE DE PRUEBA', centro + Offset(0, -h * 0.28), L * 0.034, const Color(0xFF3A2800), espacio: 1.4);
      _txt(cv, 'K7QM-3XPD', centro + Offset(0, h * 0.02), L * 0.062, const Color(0xFF3A2800), espacio: 1.4, ancho: w * 0.60);
      _txt(cv, 'beneficios de donador', centro + Offset(0, h * 0.30), L * 0.028, const Color(0xFF3A2800).withValues(alpha: 0.75), peso: FontWeight.w700, ancho: w * 0.58);
      cv.restore();
      // chispas
      for (var i = 0; i < 6; i++) {
        final ang = 2 * pi * (i / 6 + s / 12);
        final o = Offset(L / 2 + cos(ang) * L * 0.43, L * 0.44 + sin(ang) * L * 0.27);
        _estrella(cv, o, L * (0.008 + 0.022 * _onda(s, 3, i / 6)), const Color(0xFFFFE08A));
      }
      // «invita a un amigo»
      final pill = Rect.fromCenter(center: Offset(L / 2, L * 0.86), width: L * 0.62, height: L * 0.10);
      cv.drawRRect(_caja(pill, 99), _relleno(Colors.white.withValues(alpha: 0.10)));
      cv.drawRRect(_caja(pill, 99), _trazo(Colors.white.withValues(alpha: 0.28), 1.2));
      _txt(cv, 'Canjéalo y disfruta 7 días', pill.center, L * 0.040, Colors.white, peso: FontWeight.w800);
    });

// ------------------------------------------------- letras y tarjetas especiales

Widget ilusLetras(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final ctr = Offset(L * 0.43, L * 0.50);
      final w = L * 0.36, h = w * 16 / 9;
      cv.save();
      cv.translate(ctr.dx, ctr.dy);
      cv.rotate(-0.06);
      final r = Rect.fromCenter(center: Offset.zero, width: w, height: h);
      final rr = _caja(r, L * 0.04);
      cv.drawRRect(rr.shift(Offset(0, L * 0.02)), Paint()..color = Colors.black.withValues(alpha: 0.5)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.035));
      cv.save();
      cv.clipRRect(rr);
      // fondo: la carátula difuminada (manchas de color) con el tinte oscuro encima
      cv.drawRect(r, _degradado(r, const [Color(0xFF3B1E54), Color(0xFF0E1030)], ini: Alignment.topLeft, fin: Alignment.bottomRight));
      cv.drawCircle(Offset(r.left + w * 0.2, r.top + h * 0.22), w * 0.55,
          Paint()..shader = RadialGradient(colors: [const Color(0xFFFF5C8A).withValues(alpha: 0.65), const Color(0x00FF5C8A)]).createShader(Rect.fromCircle(center: Offset(r.left + w * 0.2, r.top + h * 0.22), radius: w * 0.55)));
      cv.drawCircle(Offset(r.right - w * 0.1, r.bottom - h * 0.25), w * 0.6,
          Paint()..shader = RadialGradient(colors: [const Color(0xFF22D3EE).withValues(alpha: 0.55), const Color(0x0022D3EE)]).createShader(Rect.fromCircle(center: Offset(r.right - w * 0.1, r.bottom - h * 0.25), radius: w * 0.6)));
      // carátula + título
      final car = Rect.fromCenter(center: Offset(0, r.top + h * 0.25), width: w * 0.52, height: w * 0.52);
      cv.drawRRect(_caja(car, w * 0.05), _degradado(car, const [Color(0xFFFF8A3D), Color(0xFF8B6CFF)]));
      _nota(cv, car.center + Offset(-w * 0.02, w * 0.07), w * 0.10, Colors.white.withValues(alpha: 0.9));
      _txt(cv, 'Tu canción', Offset(0, r.top + h * 0.50), w * 0.085, Colors.white, ancho: w * 0.8);
      _txt(cv, 'Tu artista favorito', Offset(0, r.top + h * 0.545), w * 0.058, Colors.white.withValues(alpha: 0.7), peso: FontWeight.w600, ancho: w * 0.8);
      // la letra: una línea se enciende cada 3 s
      const lineas = ['Cada verso brilla', 'cuando lo compartes', 'en tu estado'];
      final activa = (s ~/ 3) % 3;
      for (var i = 0; i < 3; i++) {
        final on = i == activa ? 1.0 : 0.0;
        final y = r.top + h * (0.64 + i * 0.075);
        final col = Colors.white.withValues(alpha: 0.38 + 0.62 * on);
        if (on > 0) {
          _txt(cv, lineas[i], Offset(0, y), w * 0.075, Colors.white.withValues(alpha: 0.9), peso: FontWeight.w900, ancho: w * 0.86, resplandor: w * 0.035);
        }
        _txt(cv, lineas[i], Offset(0, y), w * 0.075, col, peso: FontWeight.w900, ancho: w * 0.86);
      }
      _txt(cv, 'Caudal', Offset(0, r.bottom - h * 0.04), w * 0.06, Colors.white.withValues(alpha: 0.8), peso: FontWeight.w800);
      cv.restore();
      cv.drawRRect(rr, _trazo(Colors.white.withValues(alpha: 0.25), 1.3));
      cv.restore();

      // a la derecha, las formas de compartir
      final base = L * 0.80;
      for (var i = 0; i < 3; i++) {
        final y = L * (0.24 + i * 0.235) + L * 0.012 * sin(2 * pi * (s / 6 + i / 3));
        final o = Offset(base, y);
        final rad = L * 0.07;
        final colores = switch (i) {
          0 => const [Color(0xFF25D366), Color(0xFF128C7E)],
          1 => const [Color(0xFFF58529), Color(0xFFDD2A7B)],
          _ => const [Color(0xFFFFE08A), Color(0xFFD99A12)],
        };
        cv.drawCircle(o + Offset(0, L * 0.008), rad, Paint()..color = Colors.black.withValues(alpha: 0.35)..maskFilter = MaskFilter.blur(BlurStyle.normal, L * 0.015));
        cv.drawCircle(o, rad, _degradado(Rect.fromCircle(center: o, radius: rad), colores));
        final icono = switch (i) { 0 => Icons.chat_bubble_rounded, 1 => Icons.photo_camera_rounded, _ => Icons.movie_rounded };
        final tp = TextPainter(
          text: TextSpan(text: String.fromCharCode(icono.codePoint), style: TextStyle(fontSize: rad * 1.0, fontFamily: icono.fontFamily, package: icono.fontPackage, color: Colors.white)),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(cv, o - Offset(tp.width / 2, tp.height / 2));
      }
      const etiquetas = ['Estado', 'Historia', 'Video'];
      for (var i = 0; i < 3; i++) {
        _txt(cv, etiquetas[i], Offset(base, L * (0.24 + i * 0.235) + L * 0.108), L * 0.030, Colors.white.withValues(alpha: 0.78), peso: FontWeight.w800);
      }
    });

// ------------------------------------------------------------ tu año en Caudal

Widget ilusAnio(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      _txt(cv, 'TU AÑO EN CAUDAL', Offset(L / 2, L * 0.075), L * 0.036, Colors.white.withValues(alpha: 0.7), espacio: 2);
      // el número que cuenta
      final cuenta = (12480 * _suave(_tramo(s % 12, 0.3, 3.5))).round();
      final miles = cuenta >= 1000 ? '${cuenta ~/ 1000} ${(cuenta % 1000).toString().padLeft(3, '0')}' : '$cuenta';
      _txt(cv, miles, Offset(L / 2, L * 0.19), L * 0.15, Colors.white, peso: FontWeight.w900);
      _txt(cv, 'minutos de música', Offset(L / 2, L * 0.285), L * 0.040, c.acento, peso: FontWeight.w800);
      // doce meses
      const alturas = [0.30, 0.42, 0.36, 0.55, 0.48, 0.62, 0.58, 0.72, 0.66, 0.86, 0.78, 1.0];
      final base = L * 0.68, ancho = L * 0.052, sep = L * 0.074;
      final x0 = L / 2 - sep * 5.5;
      for (var i = 0; i < 12; i++) {
        final p = _suave(_tramo(s % 12, 0.5 + i * 0.15, 1.6 + i * 0.15));
        final h = L * 0.26 * alturas[i] * p;
        final r = Rect.fromLTWH(x0 + i * sep - ancho / 2, base - h, ancho, h);
        final destacado = i == 11;
        cv.drawRRect(_caja(r, ancho * 0.4), _degradado(r, [destacado ? const Color(0xFFFFE08A) : Color.lerp(c.acento, Colors.white, 0.25)!, destacado ? const Color(0xFFD99A12) : Color.lerp(c.acento, const Color(0xFF8B6CFF), 0.6)!], ini: Alignment.topCenter, fin: Alignment.bottomCenter));
      }
      cv.drawLine(Offset(x0 - sep * 0.5, base + 2), Offset(x0 + sep * 11.5, base + 2), _trazo(Colors.white.withValues(alpha: 0.2), 1.4));
      // podio de artistas
      const nombres = ['2', '1', '3'];
      const alt = [0.10, 0.15, 0.07];
      for (var i = 0; i < 3; i++) {
        final x = L * (0.5 + (i - 1) * 0.22);
        final aparece = _suave(_tramo(s % 12, 3.6 + i * 0.3, 4.6 + i * 0.3));
        final cy = L * 0.80 + (1 - aparece) * L * 0.06;
        final R = L * (i == 1 ? 0.052 : 0.042);
        cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: aparece));
        _avatar(cv, Offset(x, cy), R, Color.lerp(c.acento, const Color(0xFFFF5C8A), i / 2)!, const Color(0xFF14101F));
        final pod = Rect.fromCenter(center: Offset(x, L * 0.905 + L * alt[i] / 2 - L * 0.07), width: L * 0.17, height: L * alt[i]);
        cv.drawRRect(_caja(pod, L * 0.015), _relleno(Colors.white.withValues(alpha: 0.12)));
        _txt(cv, nombres[i], pod.center, L * 0.045, Colors.white.withValues(alpha: 0.85), peso: FontWeight.w900);
        cv.restore();
      }
      _estrella(cv, Offset(L * 0.5, L * 0.725), L * (0.012 + 0.018 * _onda(s, 3)), const Color(0xFFFFE08A));
    });

// ------------------------------------------------------------------ mezclador

Widget ilusMezclador(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final panel = Rect.fromCenter(center: Offset(L / 2, L * 0.48), width: L * 0.88, height: L * 0.74);
      cv.drawRRect(_caja(panel, L * 0.05), _degradado(panel, const [Color(0xFF1B1F27), Color(0xFF0B0D12)]));
      cv.drawRRect(_caja(panel, L * 0.05), _trazo(Colors.white.withValues(alpha: 0.16), 1.3));
      // dos pistas con su forma de onda
      final colores = [const Color(0xFF8B6CFF), const Color(0xFFFF5C8A)];
      for (var k = 0; k < 2; k++) {
        final y = panel.top + panel.height * (0.20 + k * 0.28);
        final h = panel.height * 0.18;
        final caja = Rect.fromLTWH(panel.left + panel.width * 0.06, y - h / 2, panel.width * 0.88, h);
        cv.drawRRect(_caja(caja, L * 0.02), _relleno(Colors.black.withValues(alpha: 0.35)));
        final n = 44;
        for (var i = 0; i < n; i++) {
          final x = caja.left + caja.width * (i + 0.5) / n;
          final f = i / n;
          // la pista de arriba se apaga hacia la derecha; la de abajo se enciende
          final vol = k == 0 ? (1 - _suave(_tramo(f, 0.45, 0.8))) : _suave(_tramo(f, 0.2, 0.6));
          final amp = (0.25 + 0.75 * _onda(i * 0.7 + s * 2, 3.1, k * 0.3)) * vol;
          final a = max(h * 0.06, h * 0.9 * amp);
          cv.drawRRect(_caja(Rect.fromCenter(center: Offset(x, y), width: caja.width / n * 0.56, height: a), 2), _relleno(colores[k].withValues(alpha: 0.92)));
        }
      }
      // las curvas del cambio
      final zona = Rect.fromLTWH(panel.left + panel.width * 0.06, panel.top + panel.height * 0.58, panel.width * 0.88, panel.height * 0.22);
      final baja = Path()..moveTo(zona.left, zona.top);
      final sube = Path()..moveTo(zona.left, zona.bottom);
      for (var i = 0; i <= 40; i++) {
        final t = i / 40;
        final q = _suave(_tramo(t, 0.30, 0.75));
        baja.lineTo(zona.left + zona.width * t, zona.top + zona.height * q);
        sube.lineTo(zona.left + zona.width * t, zona.bottom - zona.height * q);
      }
      cv.drawPath(baja, _trazo(colores[0], 3));
      cv.drawPath(sube, _trazo(colores[1], 3));
      // el cursor recorre todo
      final px = panel.left + panel.width * (0.06 + 0.88 * ((s % 6) / 6));
      cv.drawLine(Offset(px, panel.top + panel.height * 0.06), Offset(px, zona.bottom), _trazo(Colors.white.withValues(alpha: 0.9), 2));
      // perillas y BPM
      for (var i = 0; i < 3; i++) {
        final o = Offset(panel.left + panel.width * (0.20 + i * 0.30), panel.bottom - panel.height * 0.085);
        final r = L * 0.040;
        cv.drawCircle(o, r, _degradado(Rect.fromCircle(center: o, radius: r), const [Color(0xFF3A404C), Color(0xFF14171D)]));
        final ang = -2.2 + 2.6 * (0.5 + 0.5 * sin(2 * pi * (s / 6 + i / 3)));
        cv.drawLine(o, o + Offset(cos(ang), sin(ang)) * r * 0.8, _trazo(c.acento, 2.4));
      }
      _txt(cv, '124 BPM', Offset(panel.right - L * 0.13, panel.top + panel.height * 0.050), L * 0.032, Colors.white.withValues(alpha: 0.75));
      _txt(cv, 'MEZCLA SUAVE', Offset(panel.left + L * 0.20, panel.top + panel.height * 0.050), L * 0.028, Colors.white.withValues(alpha: 0.55), espacio: 1.0);
    });

// ------------------------------------------------------ importar sin límite

Widget ilusImportar(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      // origen: cuatro etiquetas a la izquierda
      const fuentes = [
        ('YouTube', Color(0xFFFF3B30)),
        ('Spotify', Color(0xFF1DB954)),
        ('Snaptube', Color(0xFFFFB000)),
        ('Texto', Color(0xFF38BDF8)),
      ];
      final destino = Rect.fromLTWH(L * 0.52, L * 0.16, L * 0.40, L * 0.62);
      cv.drawRRect(_caja(destino, L * 0.04), _degradado(destino, const [Color(0xFF1B1F27), Color(0xFF0B0D12)]));
      cv.drawRRect(_caja(destino, L * 0.04), _trazo(Colors.white.withValues(alpha: 0.2), 1.3));
      _txt(cv, 'Tu lista', Offset(destino.center.dx, destino.top + L * 0.045), L * 0.040, Colors.white, ancho: destino.width * 0.9);
      // filas que se van llenando
      final filas = 6;
      for (var i = 0; i < filas; i++) {
        final f = Rect.fromLTWH(destino.left + destino.width * 0.08, destino.top + L * 0.10 + i * L * 0.070, destino.width * 0.84, L * 0.052);
        final p = _suave(_tramo(s % 6, 0.4 + i * 0.35, 0.9 + i * 0.35));
        cv.drawRRect(_caja(f, L * 0.014), _relleno(Colors.white.withValues(alpha: 0.07 + 0.08 * p)));
        cv.drawRRect(_caja(Rect.fromLTWH(f.left + L * 0.01, f.top + L * 0.008, L * 0.036, L * 0.036), L * 0.008), _relleno(Color.lerp(const Color(0xFF3A404C), fuentes[i % 4].$2, p)!));
        cv.drawRRect(_caja(Rect.fromLTWH(f.left + L * 0.06, f.top + L * 0.014, f.width * (0.40 + 0.12 * (i % 3)) * p, L * 0.012), 99), _relleno(Colors.white.withValues(alpha: 0.85 * p)));
        cv.drawRRect(_caja(Rect.fromLTWH(f.left + L * 0.06, f.top + L * 0.032, f.width * 0.24 * p, L * 0.009), 99), _relleno(Colors.white.withValues(alpha: 0.4 * p)));
      }
      // el contador
      final n = (12480 * _suave(_tramo(s % 6, 0.2, 5.2))).round();
      final miles = n >= 1000 ? '${n ~/ 1000} ${(n % 1000).toString().padLeft(3, '0')}' : '$n';
      _txt(cv, '$miles canciones', Offset(destino.center.dx, destino.bottom - L * 0.055), L * 0.040, c.acento, ancho: destino.width * 0.92);
      // etiquetas de origen y flechas que viajan
      for (var i = 0; i < 4; i++) {
        final y = L * (0.22 + i * 0.15);
        final r = Rect.fromLTWH(L * 0.06, y - L * 0.045, L * 0.30, L * 0.09);
        cv.drawRRect(_caja(r, 99), _relleno(fuentes[i].$2.withValues(alpha: 0.18)));
        cv.drawRRect(_caja(r, 99), _trazo(fuentes[i].$2.withValues(alpha: 0.9), 1.4));
        _txt(cv, fuentes[i].$1, r.center, L * 0.036, Colors.white, ancho: r.width * 0.86);
        // puntos que fluyen hacia la lista
        for (var k = 0; k < 4; k++) {
          final p = ((s / 2.0) + k / 4 + i * 0.13) % 1;
          final x = _lerp(r.right + L * 0.012, destino.left - L * 0.012, p);
          final yy = _lerp(y, destino.center.dy, _suave(p));
          cv.drawCircle(Offset(x, yy), L * 0.009, _relleno(fuentes[i].$2.withValues(alpha: sin(pi * p).clamp(0.0, 1.0))));
        }
      }
      // el infinito
      _txt(cv, '∞  sin límite', Offset(L / 2, L * 0.90), L * 0.062, Colors.white, peso: FontWeight.w900);
    });

// --------------------------------------------------------- letra sincronizada

Widget ilusSincronia(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final tarjeta = Rect.fromCenter(center: Offset(L / 2, L * 0.40), width: L * 0.80, height: L * 0.56);
      cv.drawRRect(_caja(tarjeta, L * 0.05), _degradado(tarjeta, [Color.lerp(c.acento, Colors.black, 0.45)!, const Color(0xFF0B0D12)]));
      cv.drawRRect(_caja(tarjeta, L * 0.05), _trazo(Colors.white.withValues(alpha: 0.18), 1.3));
      const lineas = ['Esta es la primera línea', 'y esta va con la voz', 'siempre al compás', 'sin ir ni antes ni después'];
      // la línea activa avanza sola cada 2,4 s
      final pos = (s % 9.6) / 2.4;
      final i = pos.floor() % 4;
      final f = _suave((pos - pos.floor()) / 0.3);
      for (var k = 0; k < 4; k++) {
        final dist = (k - i).abs();
        final alfa = k == i ? 1.0 : (0.45 - dist * 0.12).clamp(0.12, 0.45);
        final tam = k == i ? L * 0.058 : L * 0.045;
        // la lista sube suave al pasar de una línea a la siguiente
        final yy = tarjeta.center.dy + (k - i + (1 - f)) * L * 0.09;
        if (k == i) {
          _txt(cv, lineas[k], Offset(L / 2, yy), tam, Colors.white.withValues(alpha: 0.9), peso: FontWeight.w900, ancho: tarjeta.width * 0.9, resplandor: L * 0.018);
        }
        _txt(cv, lineas[k], Offset(L / 2, yy), tam, Colors.white.withValues(alpha: alfa), peso: FontWeight.w900, ancho: tarjeta.width * 0.9);
      }
      // mando de sincronía
      final mando = Rect.fromCenter(center: Offset(L / 2, L * 0.80), width: L * 0.74, height: L * 0.13);
      cv.drawRRect(_caja(mando, 99), _relleno(Colors.white.withValues(alpha: 0.10)));
      cv.drawRRect(_caja(mando, 99), _trazo(Colors.white.withValues(alpha: 0.25), 1.2));
      final desfase = 0.5 * sin(2 * pi * s / 6);
      _txt(cv, '−0,5 s', Offset(mando.left + mando.width * 0.17, mando.center.dy), L * 0.040, Colors.white.withValues(alpha: 0.8));
      _txt(cv, '+0,5 s', Offset(mando.right - mando.width * 0.17, mando.center.dy), L * 0.040, Colors.white.withValues(alpha: 0.8));
      final pista = Rect.fromLTWH(mando.left + mando.width * 0.32, mando.center.dy - 1.5, mando.width * 0.36, 3);
      cv.drawRRect(_caja(pista, 2), _relleno(Colors.white.withValues(alpha: 0.3)));
      final bx = pista.center.dx + pista.width * 0.5 * (desfase / 0.5) * 0.9;
      cv.drawCircle(Offset(bx, mando.center.dy), L * 0.022, _relleno(c.acento));
      _txt(cv, 'Sincronía', Offset(L / 2, L * 0.935), L * 0.040, Colors.white.withValues(alpha: 0.7), peso: FontWeight.w700);
    });

// ------------------------------------------------------------------- ligero

Widget ilusLigero(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final ctr = Offset(L / 2, L * 0.50);
      final R = L * 0.34;
      final arco = Rect.fromCircle(center: ctr, radius: R);
      cv.drawArc(arco, pi * 0.8, pi * 1.4, false, _trazo(Colors.white.withValues(alpha: 0.14), L * 0.050));
      // arco de color hasta casi el máximo
      final fin = 0.92 + 0.02 * sin(2 * pi * s / 3);
      cv.drawArc(
        arco, pi * 0.8, pi * 1.4 * fin, false,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = L * 0.050
          ..strokeCap = StrokeCap.butt
          ..shader = SweepGradient(
            colors: const [Color(0xFFFFB000), Color(0xFF4ADE80), Color(0xFF22D3EE)],
            startAngle: 0,
            endAngle: pi * 1.4,
            transform: GradientRotation(pi * 0.8),
          ).createShader(arco),
      );
      for (var i = 0; i <= 10; i++) {
        final a = pi * 0.8 + pi * 1.4 * i / 10;
        cv.drawLine(ctr + Offset(cos(a), sin(a)) * (R - L * 0.055), ctr + Offset(cos(a), sin(a)) * (R - L * 0.085), _trazo(Colors.white.withValues(alpha: 0.5), 1.6));
      }
      final aguja = pi * 0.8 + pi * 1.4 * fin;
      cv.drawLine(ctr, ctr + Offset(cos(aguja), sin(aguja)) * (R - L * 0.10), _trazo(Colors.white, L * 0.014));
      cv.drawCircle(ctr, L * 0.030, _relleno(Colors.white));
      _txt(cv, '60', ctr + Offset(0, L * 0.17), L * 0.11, Colors.white, peso: FontWeight.w900);
      _txt(cv, 'cuadros por segundo', ctr + Offset(0, L * 0.255), L * 0.034, Colors.white.withValues(alpha: 0.7), peso: FontWeight.w700);
      // batería con hoja
      final bat = Rect.fromCenter(center: Offset(L * 0.5, L * 0.855), width: L * 0.32, height: L * 0.09);
      cv.drawRRect(_caja(bat, L * 0.02), _trazo(Colors.white.withValues(alpha: 0.85), 2));
      cv.drawRRect(_caja(Rect.fromLTWH(bat.right + 2, bat.center.dy - L * 0.02, L * 0.014, L * 0.04), 2), _relleno(Colors.white.withValues(alpha: 0.85)));
      final carga = 0.45 + 0.4 * _onda(s, 6);
      cv.drawRRect(_caja(Rect.fromLTWH(bat.left + 4, bat.top + 4, (bat.width - 8) * carga, bat.height - 8), L * 0.012), _relleno(const Color(0xFF4ADE80)));
      _txt(cv, 'Modo ligero', Offset(L * 0.5, L * 0.945), L * 0.036, Colors.white.withValues(alpha: 0.75), peso: FontWeight.w800);
    });

// ------------------------------------------------------------------ búsquedas

Widget ilusBuscar(Ctx c, double L) => _lienzo(c, L, (cv, z, s) {
      final barra = Rect.fromCenter(center: Offset(L / 2, L * 0.17), width: L * 0.80, height: L * 0.12);
      cv.drawRRect(_caja(barra, 99), _relleno(Colors.white.withValues(alpha: 0.10)));
      cv.drawRRect(_caja(barra, 99), _trazo(c.acento.withValues(alpha: 0.9), 1.8));
      cv.drawCircle(Offset(barra.left + L * 0.075, barra.center.dy - L * 0.006), L * 0.022, _trazo(Colors.white.withValues(alpha: 0.8), 2));
      cv.drawLine(Offset(barra.left + L * 0.09, barra.center.dy + L * 0.010), Offset(barra.left + L * 0.105, barra.center.dy + L * 0.026), _trazo(Colors.white.withValues(alpha: 0.8), 2));
      // el texto se escribe solo
      const texto = 'tus canciones favoritas';
      final n = (texto.length * _tramo(s % 6, 0.3, 2.6)).floor();
      final tp = TextPainter(
        text: TextSpan(text: texto.substring(0, n), style: TextStyle(fontSize: L * 0.045, color: Colors.white, fontWeight: FontWeight.w700, fontFamily: familiaIlustraciones)),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: barra.width * 0.7);
      tp.paint(cv, Offset(barra.left + L * 0.13, barra.center.dy - tp.height / 2));
      if ((s * 2).floor() % 2 == 0) {
        cv.drawLine(Offset(barra.left + L * 0.13 + tp.width + 2, barra.center.dy - L * 0.025), Offset(barra.left + L * 0.13 + tp.width + 2, barra.center.dy + L * 0.025), _trazo(c.acento, 2));
      }
      // la lista de recientes
      final lista = Rect.fromLTWH(L * 0.10, L * 0.30, L * 0.80, L * 0.60);
      cv.drawRRect(_caja(lista, L * 0.04), _relleno(Colors.white.withValues(alpha: 0.06)));
      _txt(cv, 'Búsquedas recientes', Offset(lista.left + L * 0.22, lista.top + L * 0.045), L * 0.036, Colors.white.withValues(alpha: 0.8), ancho: lista.width * 0.7);
      const recientes = ['Bad Bunny', 'Música para estudiar', 'Rock en español', 'Salsa clásica', 'Lo-fi'];
      for (var i = 0; i < recientes.length; i++) {
        final aparece = _suave(_tramo(s % 6, 0.4 + i * 0.28, 0.9 + i * 0.28));
        final y = lista.top + L * (0.115 + i * 0.092);
        final fila = Rect.fromLTWH(lista.left + L * 0.02, y, lista.width - L * 0.04, L * 0.08);
        cv.save();
        cv.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: aparece));
        cv.translate(L * 0.03 * (1 - aparece), 0);
        cv.drawRRect(_caja(fila, L * 0.02), _relleno(Colors.white.withValues(alpha: 0.05)));
        // reloj
        final o = Offset(fila.left + L * 0.05, fila.center.dy);
        cv.drawCircle(o, L * 0.018, _trazo(Colors.white.withValues(alpha: 0.6), 1.6));
        cv.drawLine(o, o + Offset(0, -L * 0.011), _trazo(Colors.white.withValues(alpha: 0.6), 1.6));
        cv.drawLine(o, o + Offset(L * 0.008, 0), _trazo(Colors.white.withValues(alpha: 0.6), 1.6));
        final tp2 = TextPainter(
          text: TextSpan(text: recientes[i], style: TextStyle(fontSize: L * 0.040, color: Colors.white, fontWeight: FontWeight.w700, fontFamily: familiaIlustraciones)),
          textDirection: TextDirection.ltr,
          maxLines: 1,
        )..layout(maxWidth: fila.width * 0.6);
        tp2.paint(cv, Offset(fila.left + L * 0.10, fila.center.dy - tp2.height / 2));
        // flecha y X
        final gris = _trazo(Colors.white.withValues(alpha: 0.55), 1.8);
        final fa = Offset(fila.right - L * 0.115, fila.center.dy);
        cv.drawLine(fa + Offset(L * 0.014, L * 0.014), fa + Offset(-L * 0.014, -L * 0.014), gris);
        cv.drawLine(fa + Offset(-L * 0.014, -L * 0.014), fa + Offset(-L * 0.014, L * 0.002), gris);
        cv.drawLine(fa + Offset(-L * 0.014, -L * 0.014), fa + Offset(L * 0.002, -L * 0.014), gris);
        final fx = Offset(fila.right - L * 0.045, fila.center.dy);
        cv.drawLine(fx + Offset(-L * 0.012, -L * 0.012), fx + Offset(L * 0.012, L * 0.012), gris);
        cv.drawLine(fx + Offset(-L * 0.012, L * 0.012), fx + Offset(L * 0.012, -L * 0.012), gris);
        cv.restore();
        cv.restore();
      }
    });
