// El aviso al conseguir un logro: una tarjeta que baja desde arriba con la insignia que «salta»,
// rayos dorados que giran y destellos en pixel. Se van mostrando de uno en uno; si llegan muchos
// de golpe (al contar lo escuchado antes), sale uno solo con «+N más».

import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../nucleo/logros.dart';
import 'logros_insignia.dart';
import 'paginas/logros_pagina.dart' show oroLogros;
import 'tema.dart';

class AvisosLogros {
  AvisosLogros._();

  static final List<(Logro, int)> _cola = [];
  static OverlayEntry? _actual;
  static OverlayState? _overlay;
  static VoidCallback? _alPulsar;

  /// ¿Hay un aviso a la vista? (para las pruebas)
  static bool get visible => _actual != null;

  static void mostrar(OverlayState? overlay, List<Logro> nuevos, {VoidCallback? alPulsar}) {
    if (overlay == null || nuevos.isEmpty) return;
    _overlay = overlay;
    _alPulsar = alPulsar;
    if (nuevos.length > 2) {
      _cola.add((nuevos.last, nuevos.length - 1));
    } else {
      _cola.addAll([for (final n in nuevos) (n, 0)]);
    }
    if (_actual == null) _siguiente();
  }

  static void _siguiente() {
    final o = _overlay;
    if (_cola.isEmpty || o == null || !o.mounted) {
      _actual = null;
      return;
    }
    final (logro, extra) = _cola.removeAt(0);
    late OverlayEntry entrada;
    entrada = OverlayEntry(
      builder: (_) => AvisoLogro(
        logro: logro,
        extra: extra,
        alPulsar: _alPulsar,
        alTerminar: () {
          entrada.remove();
          _actual = null;
          _siguiente();
        },
      ),
    );
    _actual = entrada;
    o.insert(entrada);
  }

  @visibleForTesting
  static void reiniciar() {
    _cola.clear();
    _actual?.remove();
    _actual = null;
  }
}

class AvisoLogro extends StatefulWidget {
  const AvisoLogro(
      {super.key, required this.logro, this.extra = 0, this.alPulsar, required this.alTerminar,
      this.duracion = const Duration(milliseconds: 4800)});

  final Logro logro;
  final int extra;
  final VoidCallback? alPulsar;
  final VoidCallback alTerminar;
  final Duration duracion;

  @override
  State<AvisoLogro> createState() => _AvisoLogroState();
}

class _AvisoLogroState extends State<AvisoLogro> with TickerProviderStateMixin {
  late final AnimationController _entrada =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 650))..forward();
  late final AnimationController _giro =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 2400))..repeat();
  Timer? _reloj;
  bool _saliendo = false;

  @override
  void initState() {
    super.initState();
    _reloj = Timer(widget.duracion, _cerrar);
  }

  Future<void> _cerrar() async {
    if (_saliendo) return;
    _saliendo = true;
    _reloj?.cancel();
    await _entrada.reverse();
    if (mounted) widget.alTerminar();
  }

  @override
  void dispose() {
    _reloj?.cancel();
    _entrada.dispose();
    _giro.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final quieto = MediaQuery.of(context).disableAnimations;
    final ancho = math.min(420.0, MediaQuery.of(context).size.width - 24);
    final bajada = CurvedAnimation(parent: _entrada, curve: Curves.easeOutBack, reverseCurve: Curves.easeInCubic);
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: SafeArea(
        child: Center(
          child: AnimatedBuilder(
            animation: Listenable.merge([_entrada, _giro]),
            builder: (context, _) {
              final t = bajada.value;
              return Transform.translate(
                offset: Offset(0, -130 * (1 - t) + 10),
                child: Opacity(
                  opacity: _entrada.value.clamp(0.0, 1.0),
                  child: Material(
                    color: Colors.transparent,
                    child: Semantics(
                      liveRegion: true,
                      label: 'Logro conseguido: ${widget.logro.nombre}',
                      child: GestureDetector(
                        onTap: () {
                          widget.alPulsar?.call();
                          _cerrar();
                        },
                        onVerticalDragEnd: (_) => _cerrar(),
                        child: _tarjeta(ancho, t, quieto ? 0 : _giro.value),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _tarjeta(double ancho, double t, double giro) {
    final escala = math.pow((t * 1.25).clamp(0.0, 1.0), 0.6).toDouble();
    return Container(
      width: ancho,
      padding: const EdgeInsets.fromLTRB(10, 10, 16, 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(colors: [C.superficie2, C.panel], begin: Alignment.topLeft, end: Alignment.bottomRight),
        border: Border.all(color: oroLogros, width: 1.6),
        boxShadow: const [BoxShadow(color: Color(0x66000000), blurRadius: 18, offset: Offset(0, 6))],
      ),
      child: Row(children: [
        SizedBox(
          width: 92,
          height: 92,
          child: CustomPaint(
            painter: _Rayos(giro: giro, escala: escala),
            child: Center(
              child: Transform.scale(
                scale: escala,
                child: InsigniaLogro(clave: widget.logro.id, lado: 56, halo: oroLogros),
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(widget.extra > 0 ? '¡LOGRO CONSEGUIDO! (+${widget.extra} más)' : '¡LOGRO CONSEGUIDO!',
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: oroLogros, letterSpacing: 1.2)),
            const SizedBox(height: 3),
            Text(widget.logro.nombre, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
            const SizedBox(height: 2),
            Text(widget.logro.descripcion, style: estiloSubTarjeta, maxLines: 2, overflow: TextOverflow.ellipsis),
          ]),
        ),
      ]),
    );
  }
}

class _Rayos extends CustomPainter {
  _Rayos({required this.giro, required this.escala});
  final double giro;
  final double escala;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final p = Paint()
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 3;
    for (var k = 0; k < 10; k++) {
      final a = giro * 2 * math.pi + k * math.pi / 5;
      p.color = oroLogros.withValues(alpha: k.isOdd ? 0.28 : 0.5);
      final r1 = 32 * escala, r2 = (42 + 4 * math.sin(giro * 2 * math.pi + k)) * escala;
      canvas.drawLine(c + Offset(math.cos(a), math.sin(a)) * r1, c + Offset(math.cos(a), math.sin(a)) * r2, p);
    }
    // destellos en pixel (crucecitas)
    final d = Paint();
    for (var k = 0; k < 4; k++) {
      final a = -giro * 2 * math.pi + k * math.pi / 2 + 0.6;
      final s = c + Offset(math.cos(a), math.sin(a)) * 40 * escala;
      d.color = const Color(0xFFFFF6B0).withValues(alpha: (0.55 + 0.45 * math.sin(giro * 12 + k)).clamp(0.0, 1.0));
      canvas.drawRect(Rect.fromCenter(center: s, width: 2, height: 8), d);
      canvas.drawRect(Rect.fromCenter(center: s, width: 8, height: 2), d);
    }
  }

  @override
  bool shouldRepaint(_Rayos old) => old.giro != giro || old.escala != escala;
}
