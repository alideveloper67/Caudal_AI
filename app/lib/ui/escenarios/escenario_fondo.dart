import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';

import 'catalogo.dart';
import 'efectos.dart';

/// Fondo animado con la ilustración de un escenario (cover, centrada) y sus efectos encima.
///
/// [bandas]: 32 valores 0..1 del espectro; si es null, una respiración suave simulada.
/// [interactivo]: arrastrar suelta partículas; tocar, una ráfaga; en los épicos, una sacudida corta.
/// La imagen solo se mueve con la sacudida de los épicos. A 30 FPS; se pausa con TickerMode y fuera de pantalla.
class EscenarioFondo extends StatefulWidget {
  const EscenarioFondo({super.key, required this.clave, this.bandas, this.interactivo = true});

  final String clave;
  final ValueListenable<List<double>>? bandas;
  final bool interactivo;

  // Se guarda la imagen ya decodificada (no el Future): un Future pendiente de otra zona nunca se resuelve.
  static final Map<String, ui.Image> _listas = <String, ui.Image>{};

  static Future<ui.Image> _cargarImagen(EscenarioDef def) async {
    final lista = _listas[def.asset];
    if (lista != null) return lista;
    final datos = await rootBundle.load('assets/escenarios/${def.asset}');
    final codec = await ui.instantiateImageCodec(datos.buffer.asUint8List());
    try {
      final cuadro = await codec.getNextFrame();
      return _listas[def.asset] = cuadro.image;
    } finally {
      codec.dispose();
    }
  }

  /// Imagen con un cuadro de los efectos en t = 6 s (sin interacción ni sacudida), para tarjetas para compartir.
  static Future<ui.Image> capturar(String clave, Size tamano) async {
    final def = escenarioPorClave(clave);
    if (def == null) {
      throw ArgumentError.value(clave, 'clave', 'No existe ese escenario');
    }
    final imagen = await _cargarImagen(def);
    final motor = _Motor(def, imagen)..fijarEspectro(null);
    motor.fijarTiempo(6.0);
    final grabador = ui.PictureRecorder();
    motor.pintar(ui.Canvas(grabador, ui.Offset.zero & tamano), tamano);
    final cuadro = grabador.endRecording();
    final salida = await cuadro.toImage(tamano.width.round(), tamano.height.round());
    cuadro.dispose();
    return salida;
  }

  @override
  State<EscenarioFondo> createState() => _EscenarioFondoState();
}

class _EscenarioFondoState extends State<EscenarioFondo> with SingleTickerProviderStateMixin {
  late final Ticker _reloj = createTicker(_alTicar);
  final ValueNotifier<int> _repinta = ValueNotifier<int>(0);
  _Motor? _motor;
  Size? _pantalla;
  double _ultimo = -1;
  int _version = 0;

  @override
  void initState() {
    super.initState();
    widget.bandas?.addListener(_alEspectro);
    _cargar();
  }

  @override
  void didUpdateWidget(EscenarioFondo anterior) {
    super.didUpdateWidget(anterior);
    if (anterior.bandas != widget.bandas) {
      anterior.bandas?.removeListener(_alEspectro);
      widget.bandas?.addListener(_alEspectro);
      _alEspectro();
    }
    if (anterior.clave != widget.clave) _cargar();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _pantalla = MediaQuery.maybeSizeOf(context);
  }

  @override
  void dispose() {
    widget.bandas?.removeListener(_alEspectro);
    _reloj.dispose();
    _repinta.dispose();
    super.dispose();
  }

  void _alEspectro() => _motor?.fijarEspectro(widget.bandas?.value);

  Future<void> _cargar() async {
    final version = ++_version;
    final def = escenarioPorClave(widget.clave);
    if (def == null) {
      if (_motor != null) setState(() => _motor = null);
      return;
    }
    final imagen = await EscenarioFondo._cargarImagen(def);
    if (!mounted || version != _version) return;
    final motor = _Motor(def, imagen)..fijarEspectro(widget.bandas?.value);
    setState(() => _motor = motor);
    if (!_reloj.isActive) _reloj.start();
  }

  bool _estaEnPantalla() {
    final ro = context.findRenderObject();
    if (ro is! RenderBox || !ro.attached || !ro.hasSize) return false;
    final pantalla = _pantalla;
    if (pantalla == null) return true;
    final caja = ro.localToGlobal(Offset.zero) & ro.size;
    return caja.overlaps(Offset.zero & pantalla);
  }

  void _alTicar(Duration transcurrido) {
    final motor = _motor;
    if (motor == null) return;
    final t = transcurrido.inMicroseconds / 1e6;
    // 30 FPS: no hace falta más cuadros en pantallas de 60 o 120 Hz
    if (_ultimo >= 0 && t - _ultimo < 1 / 30 - 0.004) return;
    if (!_estaEnPantalla()) return;
    _ultimo = t;
    motor.avanzar(t);
    _repinta.value++;
  }

  @override
  Widget build(BuildContext context) {
    final motor = _motor;
    final lienzo = RepaintBoundary(
      child: ColoredBox(
        color: const Color(0xFF0B0A12),
        child: SizedBox.expand(
          child: CustomPaint(
            painter: motor == null ? null : _Pintor(motor, _repinta),
            isComplex: motor != null,
            willChange: motor != null,
          ),
        ),
      ),
    );
    if (!widget.interactivo || motor == null) return lienzo;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: (d) => motor.alTocar(d.localPosition),
      onPanUpdate: (d) => motor.alArrastrar(d.localPosition),
      onPanEnd: (_) => motor.finArrastre(),
      onPanCancel: motor.finArrastre,
      child: lienzo,
    );
  }
}

class _Pintor extends CustomPainter {
  _Pintor(this.motor, Listenable repinta) : super(repaint: repinta);

  final _Motor motor;

  @override
  void paint(ui.Canvas canvas, Size size) => motor.pintar(canvas, size);

  @override
  bool shouldRepaint(covariant _Pintor antiguo) => antiguo.motor != motor;
}

class _Trazo {
  _Trazo({
    required this.x,
    required this.y,
    required this.vx,
    required this.vy,
    required this.t0,
    required this.vida,
    required this.ci,
    required this.rot,
  });

  double x, y, vx, vy, t0, vida, rot;
  int ci;
}

/// Estado de la simulación de un escenario y su dibujo. No conoce el widget.
class _Motor {
  _Motor(this.def, this.imagen)
      : escena = Escena(iw: def.ancho.toDouble(), ih: def.alto.toDouble()),
        efectos = def.efectos(),
        sprites = [for (final h in def.coloresInteraccion) Sprites.forma(def.interaccion, colorHex(h))];

  final EscenarioDef def;
  final ui.Image imagen;
  final Escena escena;
  final List<Efecto> efectos;
  final List<ui.Image> sprites;
  final List<_Trazo> _trazos = [];
  final List<double> _objetivo = List<double>.filled(32, 0);
  final math.Random _azar = math.Random();

  bool simulado = true;
  double tiempo = 0;
  double dt = 1 / 30;
  double margen = 0;
  double _ultimoGolpe = -10;
  double _mediaGraves = 0;
  double _sacT0 = -10, _sacFuerza = 0, _sacX = 0, _sacY = 0;
  double _flashT0 = -10, _flashFuerza = 0;
  ui.Offset? _prevArrastre;

  void fijarEspectro(List<double>? valores) {
    if (valores == null) {
      simulado = true;
      return;
    }
    simulado = false;
    final v = [for (final x in valores) if (!x.isNaN) _c(x)];
    if (v.isEmpty) {
      _objetivo.fillRange(0, _objetivo.length, 0);
      return;
    }
    final n = v.length;
    for (var i = 0; i < _objetivo.length; i++) {
      _objetivo[i] = v[math.min(n - 1, i * n ~/ _objetivo.length)];
    }
  }

  /// Fija el tiempo sin suavizar (para capturas): el espectro queda en su valor de ese instante.
  void fijarTiempo(double t) {
    tiempo = t;
    dt = 1 / 30;
    if (simulado) _calcularSimulado(t);
    for (var i = 0; i < _objetivo.length; i++) {
      escena.bandas[i] = _objetivo[i];
    }
    escena.actualizarNivel();
  }

  void avanzar(double t) {
    dt = math.min(0.1, math.max(0.0, t - tiempo));
    tiempo = t;
    if (simulado) _calcularSimulado(t);
    for (var i = 0; i < escena.bandas.length; i++) {
      final v = escena.bandas[i], o = _objetivo[i];
      escena.bandas[i] = v + (o - v) * (o > v ? 0.45 : 0.08);
    }
    escena.actualizarNivel();
    if (def.epico) {
      final g = escena.graves();
      _mediaGraves += (g - _mediaGraves) * 0.05;
      if (g > 0.55 && g - _mediaGraves > 0.18 && t - _ultimoGolpe > 0.25) {
        _ultimoGolpe = t;
        golpe(math.min(1.0, g));
      }
    }
    _moverTrazos();
  }

  void alTocar(ui.Offset local) {
    soltar(local.dx + margen, local.dy + margen, 16, 260.0 * math.max(0.6, escena.escala));
    if (def.epico) golpe(0.8);
  }

  void alArrastrar(ui.Offset local) {
    final previo = _prevArrastre;
    _prevArrastre = local;
    if (previo == null) return;
    final dx = local.dx - previo.dx, dy = local.dy - previo.dy;
    if (dx * dx + dy * dy > 64) {
      soltar(local.dx + margen, local.dy + margen, 1, 40.0 * math.max(0.6, escena.escala));
    }
  }

  void finArrastre() => _prevArrastre = null;

  void golpe(double fuerza) {
    _sacFuerza = fuerza;
    _sacT0 = tiempo;
    final a = _azar.nextDouble() * 2 * math.pi;
    _sacX = math.cos(a);
    _sacY = math.sin(a);
    _flashFuerza = fuerza * 0.6;
    _flashT0 = tiempo;
  }

  void pintar(ui.Canvas c, Size tam) {
    final w = tam.width, h = tam.height;
    if (w <= 0 || h <= 0) return;
    final m = (0.015 * math.max(w, h)).roundToDouble();
    margen = m;
    final ancho = w + 2 * m, alto = h + 2 * m;
    escena.geometria(ancho, alto);
    final s = escena.escala;

    final amp = _caida(_sacT0, _sacFuerza) * m * 0.8;
    final vaiven = math.sin(tiempo * 60);

    c.save();
    c.clipRect(ui.Rect.fromLTWH(0, 0, w, h));
    c.translate(-m + _sacX * amp * vaiven, -m + _sacY * amp * vaiven);

    c.drawImageRect(
      imagen,
      ui.Rect.fromLTWH(0, 0, imagen.width.toDouble(), imagen.height.toDouble()),
      ui.Rect.fromLTWH(escena.ox, escena.oy, escena.iw * s, escena.ih * s),
      ui.Paint()..filterQuality = ui.FilterQuality.high,
    );
    final vineta = _vinetaPara(ancho, alto);
    c.drawRect(ui.Rect.fromLTWH(0, 0, ancho, alto), ui.Paint()..shader = vineta);

    for (final ef in efectos) {
      ef.pintar(c, escena, tiempo, dt);
    }

    final ladoTrazo = 18.0 * math.max(0.6, s);
    for (final q in _trazos) {
      final u = (tiempo - q.t0) / q.vida;
      final esc = 1 - 0.4 * u;
      c.save();
      c.translate(q.x, q.y);
      c.rotate((q.rot + u * 120) * math.pi / 180);
      c.scale(esc, esc);
      c.drawImageRect(
        sprites[q.ci],
        Sprites.src,
        ui.Rect.fromCenter(center: ui.Offset.zero, width: ladoTrazo, height: ladoTrazo),
        ui.Paint()
          ..color = const ui.Color(0xFFFFFFFF).withValues(alpha: _c(1 - u))
          ..filterQuality = ui.FilterQuality.medium,
      );
      c.restore();
    }

    final flash = _caida(_flashT0, _flashFuerza);
    if (def.epico && flash > 0.01) {
      c.drawRect(
        ui.Rect.fromLTWH(0, 0, ancho, alto),
        ui.Paint()..color = const ui.Color(0xFFFFFFFF).withValues(alpha: _c(70 * flash / 255)),
      );
    }
    c.restore();
  }

  ui.Shader _vinetaPara(double ancho, double alto) {
    final previo = _vinetaCache;
    if (previo != null && _vinetaW == ancho && _vinetaH == alto) return previo;
    final sombra = _negroCon(def.vineta / 255);
    final v = ui.Gradient.radial(
      ui.Offset(ancho / 2, alto / 2),
      math.sqrt(ancho * ancho + alto * alto) / 2,
      [const ui.Color(0x00000000), sombra],
      [0.6, 1.0],
    );
    _vinetaCache = v;
    _vinetaW = ancho;
    _vinetaH = alto;
    return v;
  }

  ui.Shader? _vinetaCache;
  double _vinetaW = 0, _vinetaH = 0;

  static ui.Color _negroCon(double a01) => const ui.Color(0xFF000000).withValues(alpha: _c(a01));

  void soltar(double x, double y, int n, double fuerza) {
    for (var i = 0; i < n; i++) {
      final a = _azar.nextDouble() * 2 * math.pi;
      final v = (0.3 + 0.7 * _azar.nextDouble()) * fuerza;
      _trazos.add(_Trazo(
        x: x,
        y: y,
        vx: math.cos(a) * v,
        vy: math.sin(a) * v - fuerza * 0.4,
        t0: tiempo,
        vida: 0.7 + 0.7 * _azar.nextDouble(),
        ci: _azar.nextInt(sprites.length),
        rot: 360 * _azar.nextDouble(),
      ));
    }
    // tope de 60 partículas de interacción
    if (_trazos.length > 60) _trazos.removeRange(0, _trazos.length - 60);
  }

  void _moverTrazos() {
    final esc = escena.escala;
    for (final q in _trazos) {
      q.x += q.vx * dt;
      q.y += q.vy * dt;
      q.vy += 60.0 * esc * dt; // gravedad suave
    }
    _trazos.removeWhere((q) => (tiempo - q.t0) / q.vida >= 1);
  }

  void _calcularSimulado(double t) {
    for (var i = 0; i < _objetivo.length; i++) {
      _objetivo[i] = 0.12 + 0.08 * math.sin(t * 0.8 + i * 0.35);
    }
  }

  /// Sacudida o destello: decae en 0,25 s.
  double _caida(double t0, double fuerza) {
    final k = 1 - (tiempo - t0) / 0.25;
    return k <= 0 ? 0 : fuerza * k;
  }

  static double _c(double x) => x < 0 ? 0 : (x > 1 ? 1 : x);
}
