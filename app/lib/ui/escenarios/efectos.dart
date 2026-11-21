import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

// Efectos de los escenarios con ilustración: port de imagen_motor.py (escritorio) a Flutter.
// Las coordenadas de cada efecto son píxeles de la imagen original; Escena las lleva a pantalla.
// Los sprites (pétalo, halo, estrella...) se pintan UNA vez en ui.Image y luego se copian con drawImageRect.

const ui.Color _blanco = ui.Color(0xFFFFFFFF);
const ui.Color _negro = ui.Color(0xFF000000);

double _c01(double x) => x < 0 ? 0 : (x > 1 ? 1 : x);

/// Color "#RRGGBB" o "#AARRGGBB".
ui.Color colorHex(String hex) {
  var h = hex.replaceFirst('#', '');
  if (h.length == 6) h = 'FF$h';
  return ui.Color(int.parse(h, radix: 16));
}

/// Mismo color con opacidad 0..1.
ui.Color _op(ui.Color c, double a01) => c.withValues(alpha: _c01(a01));

/// Mismo color con alfa 0..255 (como en el escritorio).
ui.Color _alfa(ui.Color c, double a255) => _op(c, a255 / 255);

/// Mezcla lineal de dos colores (f de 0 a 1).
ui.Color mezclar(ui.Color a, ui.Color b, double f) {
  final k = _c01(f);
  return ui.Color.from(
    alpha: a.a + (b.a - a.a) * k,
    red: a.r + (b.r - a.r) * k,
    green: a.g + (b.g - a.g) * k,
    blue: a.b + (b.b - a.b) * k,
  );
}

/// Mitad de la cantidad de escritorio (como pide el rendimiento móvil), nunca menos de 1.
int mitad(int n) => math.max(1, n ~/ 2);

double _u(math.Random r, double a, double b) => a + r.nextDouble() * (b - a);

/// Geometría de la escena: convierte coordenadas de la imagen a píxeles de pantalla (cover, centrada)
/// y guarda el espectro suavizado (32 bandas) y su nivel.
class Escena {
  Escena({required this.iw, required this.ih});

  /// Tamaño de la imagen original (coordenadas de los efectos).
  final double iw;
  final double ih;
  double escala = 1;
  double ox = 0;
  double oy = 0;
  double nivel = 0;
  final List<double> bandas = List<double>.filled(32, 0);

  /// Cover: la imagen llena el área y se recorta centrada.
  void geometria(double ancho, double alto) {
    escala = math.max(ancho / iw, alto / ih);
    ox = (ancho - iw * escala) / 2;
    oy = (alto - ih * escala) / 2;
  }

  ui.Offset P(double x, double y) => ui.Offset(ox + x * escala, oy + y * escala);

  ui.Rect R(ui.Rect r) => ui.Rect.fromLTWH(
        ox + r.left * escala,
        oy + r.top * escala,
        r.width * escala,
        r.height * escala,
      );

  double banda(int i) => _c01(bandas[i % bandas.length]);

  double graves() => (bandas[0] + bandas[1] + bandas[2] + bandas[3]) / 4;

  void actualizarNivel() {
    var s = 0.0;
    for (final v in bandas) {
      s += v;
    }
    nivel = s / bandas.length;
  }
}

/// Sprites pre-pintados una vez (ui.Image). Son de 64 px y se escalan al dibujar.
class Sprites {
  Sprites._();

  static const int lado = 64;
  static final ui.Rect src = ui.Rect.fromLTWH(0, 0, lado.toDouble(), lado.toDouble());
  static final Map<String, ui.Image> _cache = <String, ui.Image>{};

  /// Halo radial: centro opaco, cae a transparente. `dureza` es la posición de la parada intermedia.
  static ui.Image halo(ui.Color color, {double dureza = 0.5}) {
    return _generar('h${color.toARGB32()}_$dureza', (c) {
      final g = ui.Gradient.radial(
        const ui.Offset(32, 32),
        32,
        [_alfa(color, 255), _alfa(color, 95), _alfa(color, 0)],
        [0.0, dureza, 1.0],
      );
      c.drawRect(src, ui.Paint()..shader = g);
    });
  }

  /// Forma de partícula: pétalo, hoja, corazon, estrella, gota, flor o chispa (por defecto).
  static ui.Image forma(String tipo, ui.Color color) {
    return _generar('f${tipo}_${color.toARGB32()}', (c) {
      c.translate(lado / 2, lado / 2);
      c.scale(lado.toDouble());
      switch (tipo) {
        case 'petalo':
          {
            final p = ui.Path()
              ..moveTo(0, 0.45)
              ..cubicTo(0.5, 0.2, 0.45, -0.4, 0.1, -0.48)
              ..cubicTo(0.04, -0.3, -0.04, -0.3, -0.1, -0.48)
              ..cubicTo(-0.45, -0.4, -0.5, 0.2, 0, 0.45);
            final g = ui.Gradient.linear(
              const ui.Offset(0, -0.5),
              const ui.Offset(0, 0.5),
              [mezclar(color, _blanco, 0.45), color],
            );
            c.drawPath(p, ui.Paint()..shader = g);
          }
        case 'hoja':
          {
            final p = ui.Path()
              ..moveTo(0, -0.48)
              ..quadraticBezierTo(0.42, 0, 0, 0.48)
              ..quadraticBezierTo(-0.42, 0, 0, -0.48);
            c.drawPath(p, ui.Paint()..color = color);
            c.drawLine(
              const ui.Offset(0, -0.42),
              const ui.Offset(0, 0.42),
              ui.Paint()
                ..color = mezclar(color, _negro, 0.35)
                ..strokeWidth = 0.05
                ..style = ui.PaintingStyle.stroke,
            );
          }
        case 'corazon':
          {
            final p = ui.Path()
              ..moveTo(0, 0.42)
              ..cubicTo(-0.6, 0, -0.35, -0.55, 0, -0.18)
              ..cubicTo(0.35, -0.55, 0.6, 0, 0, 0.42);
            c.drawPath(p, ui.Paint()..color = color);
            c.drawOval(
              ui.Rect.fromCenter(center: const ui.Offset(-0.18, -0.12), width: 0.16, height: 0.12),
              ui.Paint()..color = _op(_blanco, 150 / 255),
            );
          }
        case 'estrella':
          {
            final g = ui.Gradient.radial(
              ui.Offset.zero,
              0.5,
              [_blanco, _op(color, 200 / 255), _op(color, 0)],
              [0.0, 0.25, 1.0],
            );
            c.drawCircle(ui.Offset.zero, 0.5, ui.Paint()..shader = g);
            // estrella de cuatro puntas (el escritorio trazaba un contorno con un vértice repetido)
            final punta = ui.Path()
              ..moveTo(0, -0.5)
              ..lineTo(0.07, -0.07)
              ..lineTo(0.5, 0)
              ..lineTo(0.07, 0.07)
              ..lineTo(0, 0.5)
              ..lineTo(-0.07, 0.07)
              ..lineTo(-0.5, 0)
              ..lineTo(-0.07, -0.07)
              ..close();
            c.drawPath(punta, ui.Paint()..color = _op(_blanco, 235 / 255));
          }
        case 'gota':
          {
            final g = ui.Gradient.linear(
              const ui.Offset(0, -0.5),
              const ui.Offset(0, 0.5),
              [_op(color, 60 / 255), _op(color, 230 / 255)],
            );
            final p = ui.Path()
              ..moveTo(0, -0.5)
              ..quadraticBezierTo(0.22, 0.15, 0, 0.45)
              ..quadraticBezierTo(-0.22, 0.15, 0, -0.5);
            c.drawPath(p, ui.Paint()..shader = g);
          }
        case 'flor':
          {
            for (var k = 0; k < 5; k++) {
              c.save();
              c.rotate(k * 2 * math.pi / 5);
              c.drawOval(
                ui.Rect.fromCenter(center: const ui.Offset(0, -0.24), width: 0.32, height: 0.48),
                ui.Paint()..color = color,
              );
              c.restore();
            }
            c.drawCircle(ui.Offset.zero, 0.12, ui.Paint()..color = const ui.Color(0xFFFFE08A));
          }
        default:
          {
            final g = ui.Gradient.radial(
              ui.Offset.zero,
              0.5,
              [_blanco, _op(color, 220 / 255), _op(color, 0)],
              [0.0, 0.3, 1.0],
            );
            c.drawCircle(ui.Offset.zero, 0.5, ui.Paint()..shader = g);
          }
      }
    });
  }

  static ui.Image _generar(String clave, void Function(ui.Canvas c) dibujar) {
    final previa = _cache[clave];
    if (previa != null) return previa;
    final grabador = ui.PictureRecorder();
    dibujar(ui.Canvas(grabador, src));
    final cuadro = grabador.endRecording();
    final img = cuadro.toImageSync(lado, lado);
    cuadro.dispose();
    return _cache[clave] = img;
  }
}

/// Efecto base. Cada uno pinta sobre el canvas con la geometría de [Escena].
abstract class Efecto {
  Efecto({required int semilla}) : r = math.Random(semilla);

  final math.Random r;
  final ui.Paint _p = ui.Paint();

  /// Se suma como luz (BlendMode.screen) en vez de taparse.
  bool get aditivo => false;

  void pintar(ui.Canvas c, Escena e, double t, double dt);

  /// Pincel reutilizado: cada llamada lo reconfigura por completo.
  ui.Paint _pincel(ui.Color color, {bool trazo = false, double ancho = 1}) {
    return _p
      ..color = color
      ..style = trazo ? ui.PaintingStyle.stroke : ui.PaintingStyle.fill
      ..strokeWidth = ancho
      ..strokeCap = ui.StrokeCap.round
      ..strokeJoin = ui.StrokeJoin.round
      ..blendMode = aditivo ? ui.BlendMode.screen : ui.BlendMode.srcOver
      ..shader = null
      ..filterQuality = ui.FilterQuality.medium;
  }

  /// Sprite centrado; `alfa01` es la opacidad.
  void _sprite(ui.Canvas c, ui.Image img, ui.Offset centro, double ancho, double alto, double alfa01) {
    c.drawImageRect(
      img,
      Sprites.src,
      ui.Rect.fromCenter(center: centro, width: ancho, height: alto),
      _pincel(_op(_blanco, alfa01)),
    );
  }
}

/// Lluvia en diagonal en dos capas (lejos fina y lenta, cerca más larga y rápida), en un solo trazo.
class Lluvia extends Efecto {
  Lluvia({
    required super.semilla,
    required this.rect,
    int n = 240,
    this.angulo = 12,
    this.vel = 0.9,
    this.alfa = 70,
    this.largo = 0.035,
    String color = '#B9D8FF',
  })  : color = colorHex(color),
        cantidad = math.min(120, mitad(n)) {
    for (var i = 0; i < cantidad; i++) {
      _gotas.add((x0: r.nextDouble(), y0: r.nextDouble(), v: _u(r, 0.6, 1.0), cerca: r.nextDouble() < 0.35));
    }
  }

  final ui.Rect rect;
  final double angulo;
  final double vel;
  final double alfa;
  final double largo;
  final ui.Color color;
  final int cantidad;
  final List<({double x0, double y0, double v, bool cerca})> _gotas = [];

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final rad = angulo * math.pi / 180;
    final dx = math.sin(rad), dy = math.cos(rad);
    final lejos = Float32List(cantidad * 4);
    final cerca = Float32List(cantidad * 4);
    var nl = 0, nc = 0;
    for (final g in _gotas) {
      final f = (g.y0 + t * vel * g.v * (g.cerca ? 1.35 : 1.0)) % 1.0;
      final y = area.top + f * area.height;
      final x = area.left + ((g.x0 + f * dx * 0.12) % 1.0) * area.width;
      final l = largo * area.height * (g.cerca ? 1.5 : 0.9) * g.v;
      if (g.cerca) {
        cerca[nc++] = x;
        cerca[nc++] = y;
        cerca[nc++] = x + dx * l;
        cerca[nc++] = y + dy * l;
      } else {
        lejos[nl++] = x;
        lejos[nl++] = y;
        lejos[nl++] = x + dx * l;
        lejos[nl++] = y + dy * l;
      }
    }
    final s = e.escala;
    c.drawRawPoints(ui.PointMode.lines, lejos.sublist(0, nl),
        _pincel(_alfa(color, alfa), trazo: true, ancho: math.max(1, 0.9 * s)));
    c.drawRawPoints(ui.PointMode.lines, cerca.sublist(0, nc),
        _pincel(_alfa(color, math.min(255, alfa * 1.6)), trazo: true, ancho: math.max(1, 1.4 * s)));
  }
}

/// Anillos que se abren en el suelo mojado donde cae la lluvia.
class Salpicaduras extends Efecto {
  Salpicaduras({
    required super.semilla,
    required this.rect,
    int n = 18,
    this.radio = 14,
    String color = '#CFE6FF',
  })  : color = colorHex(color),
        cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _puntos.add((x0: r.nextDouble(), y0: r.nextDouble(), fase: r.nextDouble(), vel: _u(r, 0.7, 1.3)));
    }
  }

  final ui.Rect rect;
  final double radio;
  final ui.Color color;
  final int cantidad;
  final List<({double x0, double y0, double fase, double vel})> _puntos = [];

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final s = e.escala;
    final rmax = radio * s;
    for (final p in _puntos) {
      final ciclo = t * 1.4 * p.vel + p.fase;
      final u = ciclo % 1.0;
      final k = ciclo.floor();
      final x = area.left + ((p.x0 + k * 0.618) % 1.0) * area.width;
      final y = area.top + ((p.y0 + k * 0.381) % 1.0) * area.height;
      final prof = 0.6 + 0.8 * (y - area.top) / math.max(1.0, area.height);
      final rr = rmax * u * prof;
      c.drawOval(
        ui.Rect.fromCenter(center: ui.Offset(x, y), width: 2 * rr, height: 2 * rr * 0.32),
        _pincel(_alfa(color, 150 * (1 - u)), trazo: true, ancho: math.max(1, 1.1 * s)),
      );
    }
  }
}

/// Destellos horizontales sobre suelo mojado o agua: rayitas de luz que respiran y se deslizan despacio.
class Reflejos extends Efecto {
  Reflejos({
    required super.semilla,
    required this.rect,
    int n = 60,
    this.largo = 28,
    this.alfa = 90,
    List<String> colores = const ['#FFFFFF'],
  })  : colores = [for (final h in colores) colorHex(h)],
        cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _rayas.add((
        x0: r.nextDouble(),
        y0: r.nextDouble(),
        longitud: _u(r, 0.3, 1.0),
        fase: _u(r, 0, 6.28),
        frec: _u(r, 0.6, 1.8),
        ci: r.nextInt(colores.length),
      ));
    }
  }

  final ui.Rect rect;
  final double largo;
  final double alfa;
  final List<ui.Color> colores;
  final int cantidad;
  final List<({double x0, double y0, double longitud, double fase, double frec, int ci})> _rayas = [];

  @override
  bool get aditivo => true;

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final s = e.escala;
    for (final ray in _rayas) {
      final q = 0.5 + 0.5 * math.sin(t * ray.frec + ray.fase);
      final a = q * q * alfa * (0.8 + 0.5 * e.nivel);
      if (a < 6) continue;
      final x = area.left + ((ray.x0 + math.sin(t * 0.15 + ray.fase) * 0.01) % 1.0) * area.width;
      final y = area.top + ray.y0 * area.height;
      final l = largo * s * ray.longitud * (0.6 + 0.8 * ray.y0);
      c.drawLine(
        ui.Offset(x - l / 2, y),
        ui.Offset(x + l / 2, y),
        _pincel(_alfa(colores[ray.ci % colores.length], a), trazo: true, ancho: math.max(1, 1.4 * s)),
      );
    }
  }
}

/// Agua en calma: ondas concéntricas aplastadas que se abren y se desvanecen en puntos que cambian.
class Agua extends Efecto {
  Agua({required super.semilla, required this.rect, int n = 6, this.radio = 40, String color = '#FFFFFF'})
      : color = colorHex(color),
        cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _ondas.add((x0: r.nextDouble(), y0: r.nextDouble(), fase: r.nextDouble(), vel: _u(r, 0.6, 1.1)));
    }
  }

  final ui.Rect rect;
  final double radio;
  final ui.Color color;
  final int cantidad;
  final List<({double x0, double y0, double fase, double vel})> _ondas = [];

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final s = e.escala;
    final rmax = radio * s;
    for (final o in _ondas) {
      final ciclo = t * 0.18 * o.vel + o.fase;
      final u = ciclo % 1.0;
      final k = ciclo.floor();
      final x = area.left + ((o.x0 + k * 0.618) % 1.0) * area.width;
      final y = area.top + ((o.y0 + k * 0.381) % 1.0) * area.height;
      for (final j in const [0.0, 0.33]) {
        final uu = u - j;
        if (uu <= 0) continue;
        c.drawOval(
          ui.Rect.fromCenter(center: ui.Offset(x, y), width: 2 * rmax * uu, height: 2 * rmax * uu * 0.28),
          _pincel(_alfa(color, 70 * (1 - uu)), trazo: true, ancho: math.max(1, 1.2 * s)),
        );
      }
    }
  }
}

/// Humo o vapor que sube desde un punto: bocanadas suaves que crecen, se ladean y se desvanecen.
class Humo extends Efecto {
  Humo({
    required super.semilla,
    required this.punto,
    int n = 10,
    this.alto = 120,
    this.ancho = 30,
    this.tam = 26,
    this.alfa = 0.45,
    this.vel = 0.16,
    this.viento = 0.4,
    String color = '#FFFFFF',
  })  : halo = Sprites.halo(colorHex(color), dureza: 0.35),
        cantidad = mitad(n) {
    for (var k = 0; k < cantidad; k++) {
      _bocanadas.add((off: k / cantidad, fase: _u(r, 0, 6.28), v: _u(r, 0.8, 1.2)));
    }
  }

  final ui.Offset punto;
  final double alto;
  final double ancho;
  final double tam;
  final double alfa;
  final double vel;
  final double viento;
  final ui.Image halo;
  final int cantidad;
  final List<({double off, double fase, double v})> _bocanadas = [];

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final base = e.P(punto.dx, punto.dy);
    final s = e.escala;
    final altoP = alto * s, anchoP = ancho * s, tamP = tam * s;
    for (final b in _bocanadas) {
      final u = (t * vel * b.v + b.off) % 1.0;
      final px = base.dx + math.sin(u * 3.2 + b.fase) * anchoP * u + viento * anchoP * u * u;
      final py = base.dy - u * altoP;
      final esc = 0.25 + 0.95 * u;
      final op = alfa * math.pow(math.sin(math.pi * u), 1.3).toDouble();
      final w = 2 * tamP * esc;
      _sprite(c, halo, ui.Offset(px, py), w, w, op);
    }
  }
}

/// Partículas que caen (o suben con vel < 0): pétalos, hojas, corazones, estrellas, chispas, gotas, flores.
/// Se balancean, giran y se voltean.
class Caida extends Efecto {
  Caida({
    required super.semilla,
    required this.rect,
    int n = 30,
    this.tipo = 'petalo',
    this.tam = 16,
    this.vel = 0.06,
    this.deriva = 0.02,
    this.voltea = true,
    List<String> colores = const ['#F7B9CF'],
    this.alfa = 1.0,
    this.recortar = false,
  })  : sprites = [for (final h in colores) Sprites.forma(tipo, colorHex(h))],
        cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _parts.add((
        x0: r.nextDouble(),
        y0: r.nextDouble(),
        v: _u(r, 0.7, 1.3),
        amp: _u(r, 0.01, 0.04),
        frec: _u(r, 0.6, 1.6),
        fase: _u(r, 0, 6.28),
        giro: _u(r, -1.2, 1.2),
        fv: _u(r, 0.8, 2.0),
        ci: r.nextInt(sprites.length),
        esc: _u(r, 0.6, 1.0),
      ));
    }
  }

  final ui.Rect rect;
  final String tipo;
  final double tam;
  final double vel;
  final double deriva;
  final bool voltea;
  final double alfa;
  final bool recortar;
  final List<ui.Image> sprites;
  final int cantidad;
  final List<({double x0, double y0, double v, double amp, double frec, double fase, double giro, double fv, int ci, double esc})>
      _parts = [];

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final tamP = tam * e.escala;
    if (recortar) {
      c.save();
      c.clipRect(area);
    }
    for (final q in _parts) {
      final yf = (q.y0 + t * vel * q.v) % 1.0;
      final xf = (q.x0 + t * deriva * q.v + q.amp * math.sin(q.frec * t + q.fase)) % 1.0;
      final x = area.left + xf * area.width;
      final y = area.top + yf * area.height;
      // aparecen y se van sin cortes
      final op = _c01(math.min(1.0, math.min(yf / 0.08, (1 - yf) / 0.08))) * alfa;
      if (op < 0.01) continue;
      final fl = voltea ? math.max(0.15, math.cos(q.fv * t + q.fase).abs()) : 1.0;
      c.save();
      c.translate(x, y);
      c.rotate(q.giro * t + q.fase);
      c.scale(q.esc * fl, q.esc);
      c.drawImageRect(
        sprites[q.ci],
        Sprites.src,
        ui.Rect.fromCenter(center: ui.Offset.zero, width: tamP, height: tamP),
        _pincel(_op(_blanco, op)),
      );
      c.restore();
    }
    if (recortar) c.restore();
  }
}

/// Resplandor en un punto (farol, letrero, ojo...). Modos: respira, musica, neon, latido.
class Brillo extends Efecto {
  Brillo({
    required super.semilla,
    required this.punto,
    this.radio = 60,
    String color = '#FFC080',
    this.modo = 'respira',
    this.alfa = 0.6,
    this.frec = 1.1,
    this.banda = 0,
    this.dureza = 0.4,
  }) : halo = Sprites.halo(colorHex(color), dureza: dureza) {
    fase = _u(r, 0, 6.28);
  }

  final ui.Offset punto;
  final double radio;
  final String modo;
  final double alfa;
  final double frec;
  final int banda;
  final double dureza;
  final ui.Image halo;
  double fase = 0;

  @override
  bool get aditivo => true;

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final centro = e.P(punto.dx, punto.dy);
    final d = 2 * radio * e.escala;
    final a = switch (modo) {
      'musica' => alfa * (0.35 + 0.9 * e.banda(banda)),
      'latido' => alfa * math.min(1.0, 0.15 + 1.4 * e.graves()),
      'neon' => alfa *
          (((t * 0.21 + fase) % 1.0) < 0.025
              ? 0.15
              : (0.85 + 0.08 * (math.sin(t * 13.1 + fase) + math.sin(t * 7.3 + 2 * fase)) / 2)) *
          (0.9 + 0.25 * e.nivel),
      _ => alfa * (0.7 + 0.3 * math.sin(t * frec + fase)) * (0.9 + 0.3 * e.nivel),
    };
    final op = _c01(a);
    if (op <= 0) return;
    _sprite(c, halo, centro, d, d, op);
  }
}

/// Estrellitas de cuatro puntas que titilan (cielo, cristales, purpurina).
class Destellos extends Efecto {
  Destellos({required super.semilla, required this.rect, int n = 15, this.tam = 18, String color = '#FFFFFF'})
      : estrella = Sprites.forma('estrella', colorHex(color)),
        cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _pts.add((
        x0: r.nextDouble(),
        y0: r.nextDouble(),
        fase: _u(r, 0, 6.28),
        frec: _u(r, 0.5, 1.4),
        esc: _u(r, 0.5, 1.0),
      ));
    }
  }

  final ui.Rect rect;
  final double tam;
  final ui.Image estrella;
  final int cantidad;
  final List<({double x0, double y0, double fase, double frec, double esc})> _pts = [];

  @override
  bool get aditivo => true;

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final tamP = tam * e.escala;
    for (final p in _pts) {
      final q = math.max(0.0, math.sin(t * p.frec + p.fase));
      final a = q * q * q * q;
      if (a < 0.04) continue;
      final x = area.left + p.x0 * area.width;
      final y = area.top + p.y0 * area.height;
      final w = tamP * p.esc * (0.6 + 0.4 * a);
      _sprite(c, estrella, ui.Offset(x, y), w, w, math.min(1.0, a * (0.9 + 0.3 * e.nivel)));
    }
  }
}

/// Puntos de luz que flotan con deriva lenta y se encienden y apagan (luciérnagas, polvo en un rayo).
class Luciernagas extends Efecto {
  Luciernagas({
    required super.semilla,
    required this.rect,
    int n = 16,
    this.radio = 7,
    String color = '#D6FF96',
    this.parpadeo = 3,
    this.alfa = 0.9,
    this.sube = 0,
  })  : halo = Sprites.halo(colorHex(color), dureza: 0.3),
        cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _pts.add((
        x0: r.nextDouble(),
        y0: r.nextDouble(),
        dr: _u(r, 0.01, 0.05),
        vel: _u(r, 0.1, 0.35),
        fase: _u(r, 0, 6.28),
        frec: _u(r, 0.3, 0.9),
      ));
    }
  }

  final ui.Rect rect;
  final double radio;
  final double parpadeo;
  final double alfa;
  final double sube;
  final ui.Image halo;
  final int cantidad;
  final List<({double x0, double y0, double dr, double vel, double fase, double frec})> _pts = [];

  @override
  bool get aditivo => true;

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final d = 2 * radio * e.escala;
    for (final p in _pts) {
      final x = area.left + ((p.x0 + math.sin(t * p.vel + p.fase) * p.dr) % 1.0) * area.width;
      final y = area.top +
          ((p.y0 - t * sube * p.vel + math.sin(t * p.vel * 1.3 + 2 * p.fase) * p.dr * 0.6) % 1.0) * area.height;
      final b = math.pow(math.max(0.0, math.sin(t * p.frec + p.fase)), parpadeo).toDouble();
      if (b < 0.03) continue;
      _sprite(c, halo, ui.Offset(x, y), d, d, math.min(1.0, b * alfa * (0.8 + 0.4 * e.nivel)));
    }
  }
}

/// Rayos eléctricos que nacen en una zona, quebrados y ramificados; salen más con los graves.
class Rayos extends Efecto {
  Rayos({
    required super.semilla,
    required this.rects,
    int n = 3,
    List<String> colores = const ['#7FD8FF', '#C38BFF'],
  })  : colores = [for (final h in colores) colorHex(h)],
        cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _slots.add(_Rayo(prox: _u(r, 0, 1.5)));
    }
  }

  final List<ui.Rect> rects;
  final List<ui.Color> colores;
  final int cantidad;
  final List<_Rayo> _slots = [];

  @override
  bool get aditivo => true;

  ui.Path _nuevo(ui.Rect area) {
    var x = area.left + r.nextDouble() * area.width;
    var y = area.top + _u(r, 0, 0.3) * area.height;
    final largo = area.height * _u(r, 0.35, 0.8);
    const pasos = 10;
    final puntos = <ui.Offset>[ui.Offset(x, y)];
    for (var k = 0; k < pasos; k++) {
      x += _u(r, -0.06, 0.06) * area.width;
      y += largo / pasos;
      puntos.add(ui.Offset(x, y));
    }
    final camino = ui.Path()..moveTo(puntos.first.dx, puntos.first.dy);
    for (final q in puntos.skip(1)) {
      camino.lineTo(q.dx, q.dy);
    }
    // una rama
    final i = 2 + r.nextInt(pasos - 4);
    var bx = puntos[i].dx, by = puntos[i].dy;
    final rama = ui.Path()..moveTo(bx, by);
    for (var k = 0; k < 4; k++) {
      bx += _u(r, -0.07, 0.07) * area.width;
      by += largo / pasos * 0.8;
      rama.lineTo(bx, by);
    }
    camino.addPath(rama, ui.Offset.zero);
    return camino;
  }

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final areas = [for (final rc in rects) e.R(rc)];
    final s = e.escala;
    final g = e.graves();
    for (var k = 0; k < _slots.length; k++) {
      final sl = _slots[k];
      if (t >= sl.prox) {
        sl.camino = _nuevo(areas[k % areas.length]);
        sl.fin = t + _u(r, 0.08, 0.18);
        sl.prox = t + _u(r, 0.6, 2.0) / (1 + 2.5 * g);
        sl.col = r.nextInt(colores.length);
      }
      final camino = sl.camino;
      if (t < sl.fin && camino != null) {
        final col = colores[sl.col];
        final vida = (sl.fin - t) / 0.18;
        c.drawPath(camino, _pincel(_alfa(col, 70 * vida + 20), trazo: true, ancho: 9 * s));
        c.drawPath(camino, _pincel(_alfa(col, 180 * vida + 60), trazo: true, ancho: 3 * s));
        c.drawPath(camino, _pincel(_alfa(_blanco, 200 * vida + 40), trazo: true, ancho: 1.2 * s));
      }
    }
  }
}

class _Rayo {
  _Rayo({required this.prox});
  double fin = -1;
  double prox;
  ui.Path? camino;
  int col = 0;
}

/// Aura de energía: chispas alargadas que suben rápido desde una zona, más intensas con la música.
class Aura extends Efecto {
  Aura({
    required super.semilla,
    required this.rect,
    int n = 40,
    this.tam = 26,
    this.vel = 0.45,
    List<String> colores = const ['#9CE8FF', '#C79BFF', '#FFFFFF'],
  })  : halos = [for (final h in colores) Sprites.halo(colorHex(h), dureza: 0.25)],
        cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _pts.add((
        x0: r.nextDouble(),
        y0: r.nextDouble(),
        v: _u(r, 0.6, 1.4),
        ci: r.nextInt(halos.length),
        fase: _u(r, 0, 6.28),
      ));
    }
  }

  final ui.Rect rect;
  final double tam;
  final double vel;
  final List<ui.Image> halos;
  final int cantidad;
  final List<({double x0, double y0, double v, int ci, double fase})> _pts = [];

  @override
  bool get aditivo => true;

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final w = tam * e.escala;
    final velocidad = vel * (1 + 0.8 * e.nivel);
    for (final p in _pts) {
      final u = (p.y0 + t * velocidad * p.v) % 1.0;
      final x = area.left + (p.x0 + 0.01 * math.sin(t * 3 + p.fase)) * area.width;
      final y = area.bottom - u * area.height;
      final op = math.min(1.0, math.sin(math.pi * u) * (0.45 + 0.7 * e.nivel));
      if (op < 0.01) continue;
      c.drawImageRect(
        halos[p.ci],
        Sprites.src,
        ui.Rect.fromLTWH(x - w * 0.18, y - w, w * 0.36, w * 2),
        _pincel(_op(_blanco, op)),
      );
    }
  }
}

/// Bancos de bruma o nube muy suaves que se desplazan despacio de lado a lado.
class Nubes extends Efecto {
  Nubes({
    required super.semilla,
    required this.rect,
    int n = 3,
    this.tam = 260,
    this.alfa = 0.25,
    String color = '#FFFFFF',
    this.vel = 0.006,
  })  : halo = Sprites.halo(colorHex(color), dureza: 0.45),
        cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _nubes.add((x0: r.nextDouble(), y0: r.nextDouble(), esc: _u(r, 0.6, 1.0), v: _u(r, 0.5, 1.0)));
    }
  }

  final ui.Rect rect;
  final double tam;
  final double alfa;
  final double vel;
  final ui.Image halo;
  final int cantidad;
  final List<({double x0, double y0, double esc, double v})> _nubes = [];

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final tamP = tam * e.escala;
    for (final n in _nubes) {
      final xf = (n.x0 + t * vel * n.v) % 1.2 - 0.1;
      final x = area.left + xf * area.width;
      final y = area.top + n.y0 * area.height;
      final w = tamP * n.esc;
      final op = alfa * math.min(1.0, math.min((xf + 0.1) / 0.15, (1.1 - xf) / 0.15));
      if (op < 0.01) continue;
      c.drawImageRect(
        halo,
        Sprites.src,
        ui.Rect.fromLTWH(x - w, y - w * 0.22, w * 2, w * 0.44),
        _pincel(_op(_blanco, op)),
      );
    }
  }
}

/// Mariposas o murciélagos que cruzan siguiendo una curva suave y aletean.
class Voladores extends Efecto {
  Voladores({
    required super.semilla,
    required this.rect,
    int n = 2,
    this.tipo = 'mariposa',
    this.tam = 16,
    String color = '#FFD1E8',
  })  : color = colorHex(color),
        cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _vs.add((x0: r.nextDouble(), vel: _u(r, 0.04, 0.08), fase: _u(r, 0, 6.28), esc: _u(r, 0.7, 1.2)));
    }
  }

  final ui.Rect rect;
  final String tipo;
  final double tam;
  final ui.Color color;
  final int cantidad;
  final List<({double x0, double vel, double fase, double esc})> _vs = [];

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final murcielago = tipo == 'murcielago';
    final tamP = tam * e.escala;
    for (final v in _vs) {
      final u = (v.x0 + t * v.vel) % 1.0;
      final x = area.left + u * area.width;
      final y = area.top + (0.5 + 0.35 * math.sin(u * 9 + v.fase)) * area.height;
      final ala = math.sin(t * (murcielago ? 14 : 9) + v.fase);
      final sz = tamP * v.esc;
      final op = _c01(math.min(u / 0.06, (1 - u) / 0.06));
      if (op < 0.01) continue;
      final col = _op(color, op);
      if (murcielago) {
        for (final lado in const [-1.0, 1.0]) {
          final f = ui.Path()
            ..moveTo(x, y)
            ..quadraticBezierTo(x + lado * sz * 0.5, y - sz * 0.5 * ala, x + lado * sz, y - sz * 0.15 * ala)
            ..quadraticBezierTo(x + lado * sz * 0.6, y + sz * 0.15, x, y + sz * 0.12);
          c.drawPath(f, _pincel(col));
        }
        c.drawOval(ui.Rect.fromCenter(center: ui.Offset(x, y), width: sz * 0.28, height: sz * 0.36), _pincel(col));
      } else {
        final abre = 0.25 + 0.75 * ala.abs();
        for (final lado in const [-1.0, 1.0]) {
          c.drawOval(
            ui.Rect.fromCenter(
              center: ui.Offset(x + lado * sz * 0.32 * abre, y - sz * 0.12),
              width: 2 * sz * 0.34 * abre,
              height: 2 * sz * 0.30,
            ),
            _pincel(col),
          );
          c.drawOval(
            ui.Rect.fromCenter(
              center: ui.Offset(x + lado * sz * 0.22 * abre, y + sz * 0.18),
              width: 2 * sz * 0.22 * abre,
              height: 2 * sz * 0.20,
            ),
            _pincel(col),
          );
        }
        c.drawRRect(
          ui.RRect.fromRectXY(
            ui.Rect.fromLTWH(x - sz * 0.04, y - sz * 0.25, sz * 0.08, sz * 0.5),
            sz * 0.04,
            sz * 0.04,
          ),
          _pincel(_op(mezclar(color, _negro, 0.5), op)),
        );
      }
    }
  }
}

/// Flashes de cámaras entre el público: destellos blancos cortísimos en puntos al azar (más con la música).
class Flashes extends Efecto {
  Flashes({required super.semilla, required this.rect, this.frec = 2.0, this.radio = 22})
      : halo = Sprites.halo(_blanco, dureza: 0.2);

  final ui.Rect rect;
  final double frec;
  final double radio;
  final ui.Image halo;
  double _acum = 0;
  final List<({double x, double y, double t0})> _activos = [];

  @override
  bool get aditivo => true;

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final d = 2 * radio * e.escala;
    _acum += dt * frec * (1 + 3 * e.graves());
    while (_acum >= 1) {
      _acum -= 1;
      _activos.add((
        x: area.left + r.nextDouble() * area.width,
        y: area.top + r.nextDouble() * area.height,
        t0: t,
      ));
    }
    _activos.removeWhere((a) => (t - a.t0) / 0.16 >= 1);
    if (_activos.length > 20) _activos.removeRange(0, _activos.length - 20);
    for (final a in _activos) {
      final u = (t - a.t0) / 0.16;
      _sprite(c, halo, ui.Offset(a.x, a.y), d, d, 1 - u);
    }
  }
}

/// Luz que cruza el cielo (coche volador, dron) con su estela, cada cierto tiempo.
class Vehiculo extends Efecto {
  Vehiculo({
    required super.semilla,
    required this.de,
    required this.a,
    this.periodo = 16,
    this.dur = 7,
    this.desfase = 0,
    String color = '#7FF5FF',
  }) : color = colorHex(color);

  final ui.Offset de;
  final ui.Offset a;
  final double periodo;
  final double dur;
  final double desfase;
  final ui.Color color;

  @override
  bool get aditivo => true;

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final u = ((t + desfase) % periodo) / dur;
    if (u >= 1) return;
    final dx = a.dx - de.dx, dy = a.dy - de.dy;
    final ub = math.max(0.0, u - 0.06);
    final cabeza = e.P(de.dx + dx * u, de.dy + dy * u);
    final cola = e.P(de.dx + dx * ub, de.dy + dy * ub);
    final s = e.escala;
    final estela = _pincel(_blanco, trazo: true, ancho: 3 * s)
      ..shader = ui.Gradient.linear(cola, cabeza, [_op(color, 0), _op(color, 200 / 255)]);
    c.drawLine(cola, cabeza, estela);
    c.drawCircle(cabeza, 2.2 * s, _pincel(_op(_blanco, 230 / 255)));
  }
}

/// Agua que cae: rayitas verticales claras que bajan dentro de una franja estrecha.
class Cascada extends Efecto {
  Cascada({required super.semilla, required this.rect, int n = 8}) : cantidad = mitad(n) {
    for (var i = 0; i < cantidad; i++) {
      _rayas.add((x0: r.nextDouble(), y0: r.nextDouble(), v: _u(r, 0.6, 1.2)));
    }
  }

  final ui.Rect rect;
  final int cantidad;
  final List<({double x0, double y0, double v})> _rayas = [];

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final area = e.R(rect);
    final s = e.escala;
    final pincel = _pincel(_op(_blanco, 150 / 255), trazo: true, ancho: math.max(1, 1.2 * s));
    for (final ra in _rayas) {
      final f = (ra.y0 + t * 0.8 * ra.v) % 1.0;
      final x = area.left + ra.x0 * area.width;
      final y = area.top + f * area.height;
      c.drawLine(ui.Offset(x, y), ui.Offset(x, math.min(area.bottom, y + area.height * 0.22)), pincel);
    }
  }
}

/// Las frecuencias de la música como línea de ondas suave en un sitio de la ilustración.
/// Curva suave simétrica, relleno que se desvanece hacia abajo y reflejo opcional.
class Ondas extends Efecto {
  Ondas({
    required super.semilla,
    required this.x0,
    required this.y,
    required this.ancho,
    this.alto = 70,
    String color = '#FFFFFF',
    this.reflejo = false,
  }) : color = colorHex(color);

  final double x0;
  final double y;
  final double ancho;
  final double alto;
  final ui.Color color;
  final bool reflejo;

  @override
  void pintar(ui.Canvas c, Escena e, double t, double dt) {
    final base = e.P(x0, y);
    final s = e.escala;
    final anchoP = ancho * s, altoP = alto * s;
    final grosor = 1.4 * math.max(1.0, s);
    final vals = [...e.bandas.reversed, ...e.bandas];
    final n = vals.length;
    final pts = <ui.Offset>[];
    for (var i = 0; i < n; i++) {
      final x = base.dx + anchoP * i / (n - 1);
      final reposo = 0.04 + 0.025 * math.sin(t * 1.3 + i * 0.45);
      final borde = math.pow(math.sin(math.pi * i / (n - 1)), 0.6).toDouble();
      pts.add(ui.Offset(x, base.dy - altoP * math.max(reposo, vals[i]) * borde));
    }
    final camino = ui.Path()
      ..moveTo(base.dx, base.dy)
      ..lineTo(pts.first.dx, pts.first.dy);
    final linea = ui.Path()..moveTo(pts.first.dx, pts.first.dy);
    for (var i = 1; i < n; i++) {
      final a = pts[i - 1], b = pts[i];
      final medio = (a.dx + b.dx) / 2;
      camino.cubicTo(medio, a.dy, medio, b.dy, b.dx, b.dy);
      linea.cubicTo(medio, a.dy, medio, b.dy, b.dx, b.dy);
    }
    camino.lineTo(base.dx + anchoP, base.dy);

    final cima = base.dy - altoP;
    final g = ui.Gradient.linear(ui.Offset(0, cima), ui.Offset(0, base.dy), [_op(color, 110 / 255), _op(color, 0)]);
    c.drawPath(camino, _pincel(_blanco)..shader = g);
    c.drawPath(linea, _pincel(_op(color, 70 / 255), trazo: true, ancho: grosor * 4));
    c.drawPath(
      linea,
      _pincel(_op(mezclar(color, _blanco, 0.55), 230 / 255), trazo: true, ancho: grosor),
    );
    if (reflejo) {
      final gr = ui.Gradient.linear(
        ui.Offset(0, cima),
        ui.Offset(0, base.dy),
        [_op(color, 110 / 255 * 0.22), _op(color, 0)],
      );
      c.save();
      c.translate(0, 2 * base.dy);
      c.scale(1, -1);
      c.drawPath(camino, _pincel(_blanco)..shader = gr);
      c.restore();
    }
  }
}
