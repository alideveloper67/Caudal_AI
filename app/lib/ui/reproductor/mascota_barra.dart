// La mascotita que camina sobre la barra de progreso (donadores y fundadores).
//
// Solo existe mientras hay una elegida: sin mascota no se crea nada y la barra
// queda como siempre. El reloj de animacion corre unicamente mientras suena
// (y se ve), y solo repinta al cambiar de cuadro o de posicion.

import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../nucleo/gamer_control.dart';
import '../../nucleo/mascota_app.dart';
import '../../reproduccion/reproductor.dart';

class MascotaEnBarra extends StatelessWidget {
  const MascotaEnBarra({super.key, required this.r, required this.fraccion, required this.cambios, required this.margen});

  final Reproductor r;
  final double Function() fraccion;
  final Listenable cambios;
  final double margen;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([MascotaApp.i, ModoGamerControl.mascotasOcultas]),
      builder: (_, _) {
        final m = MascotaApp.i.activa && !ModoGamerControl.mascotasOcultas.value ? MascotaApp.i.actual : null;
        if (m == null) return const SizedBox.shrink();
        return _Caminante(key: ValueKey(m.clave), r: r, mascota: m, fraccion: fraccion, cambios: cambios, margen: margen);
      },
    );
  }
}

class _Caminante extends StatefulWidget {
  const _Caminante(
      {super.key, required this.r, required this.mascota, required this.fraccion, required this.cambios, required this.margen});

  final Reproductor r;
  final Mascota mascota;
  final double Function() fraccion;
  final Listenable cambios;
  final double margen;

  @override
  State<_Caminante> createState() => _CaminanteState();
}

class _CaminanteState extends State<_Caminante> {
  // 180 ms por cuadro (2 cuadros = 360 ms, como antes). Antes un reloj de
  // animación pedía un fotograma entero 60 veces por segundo para cambiar de
  // cuadro 5 veces: ahora se repinta solo al cambiar de cuadro o de posición.
  static const _porCuadro = Duration(milliseconds: 180);
  Timer? _reloj;
  ui.Image? _hoja, _estela;

  /// Avisa de cada cuadro nuevo (lo que hace repintar a la mascota).
  final _avisoCuadro = ValueNotifier<int>(0);
  ValueListenable<TickerModeData>? _tickers;

  // sube 0.9 cada vez que cambia el cuadro de caminar (igual que en el escritorio)
  double _fase = 0;
  int _cuadro = 0;

  @override
  void initState() {
    super.initState();
    MascotaApp.i.imagen(widget.mascota.clave).then((im) {
      if (mounted) setState(() => _hoja = im);
    });
    if (widget.mascota.tieneEstela) {
      MascotaApp.i.imagenEstela(widget.mascota.clave).then((im) {
        if (mounted) setState(() => _estela = im);
      });
    }
    widget.r.addListener(_alCambiarEstado);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // con la pantalla tapada o la pestaña oculta tampoco camina
    final n = TickerMode.getValuesNotifier(context);
    if (!identical(n, _tickers)) {
      _tickers?.removeListener(_alCambiarEstado);
      _tickers = n..addListener(_alCambiarEstado);
    }
    _alCambiarEstado();
  }

  void _paso() {
    _cuadro = (_cuadro + 1) % math.max(1, widget.mascota.cuadros);
    _fase += 0.9;
    _avisoCuadro.value++;
  }

  @override
  void dispose() {
    widget.r.removeListener(_alCambiarEstado);
    _tickers?.removeListener(_alCambiarEstado);
    _reloj?.cancel();
    _avisoCuadro.dispose();
    super.dispose();
  }

  void _alCambiarEstado() {
    final suena = widget.r.estado == EstadoRepro.sonando && (_tickers?.value.enabled ?? true);
    if (suena && _reloj == null) {
      _reloj = Timer.periodic(_porCuadro, (_) => _paso());
    } else if (!suena && _reloj != null) {
      _reloj!.cancel();
      _reloj = null;
      if (widget.r.estado != EstadoRepro.sonando && _cuadro != 0) {
        _cuadro = 0; // en pausa se queda quieta, en el primer cuadro
        _avisoCuadro.value++;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final hoja = _hoja;
    if (hoja == null) return const SizedBox.shrink();
    return RepaintBoundary(
      child: CustomPaint(
        painter: _PintorMascota(
          hoja: hoja,
          estela: _estela,
          fase: () => _fase,
          cuadro: () => _cuadro,
          mascota: widget.mascota,
          fraccion: widget.fraccion,
          margen: widget.margen,
          repintar: Listenable.merge([widget.cambios, _avisoCuadro]),
        ),
      ),
    );
  }
}

/// Qué cuadro de la animación toca según el avance de la vuelta (0..1): reparte la vuelta en partes iguales.
@visibleForTesting
int cuadroDeMascota(double avance, int cuadros) => math.min(cuadros - 1, math.max(0, (avance * cuadros).floor()));

const _franjas = [Color(0xFFFF0000), Color(0xFFFF9900), Color(0xFFFFFF00), Color(0xFF33FF00), Color(0xFF0099FF), Color(0xFF6633FF)];

class _PintorMascota extends CustomPainter {
  _PintorMascota({
    required this.hoja,
    required this.estela,
    required this.fase,
    required this.cuadro,
    required this.mascota,
    required this.fraccion,
    required this.margen,
    required Listenable repintar,
  }) : super(repaint: repintar);

  final ui.Image hoja;
  final ui.Image? estela;
  final double Function() fase;
  final Mascota mascota;
  final double Function() fraccion;
  final double margen;
  final int Function() cuadro;

  // los dibujos ya vienen a su tamaño final (48x44): se pintan 1 a 1
  static const _escala = 1.0;

  @override
  void paint(Canvas canvas, Size size) {
    final w = mascota.ancho * _escala, h = mascota.alto * _escala;
    final ancho = size.width - 2 * margen;
    final x = margen + ancho * fraccion();
    final y = size.height / 2;
    // los pies quedan apoyados justo encima de la barra
    final arriba = y - 2 - h;
    final cuadro = math.min(mascota.cuadros - 1, math.max(0, this.cuadro()));

    if (mascota.arcoiris) {
      _arcoiris(canvas, x, arriba, w, h);
    } else if (mascota.tieneEstela && estela != null) {
      _detalles(canvas, estela!, x, arriba + h, w, h);
    }

    final fw = (mascota.ancho * mascota.densidad).toDouble(), fh = (mascota.alto * mascota.densidad).toDouble();
    final origen = Rect.fromLTWH(cuadro * fw, 0, fw, fh);
    final destino = Rect.fromLTWH(x - w / 2, arriba, w, h);
    canvas.drawImageRect(hoja, origen, destino, Paint()..filterQuality = FilterQuality.none);
  }

  /// El arcoíris de Nyan Cat: seis franjas con un vaivén suave, desde el inicio de la barra.
  void _arcoiris(Canvas canvas, double x, double arriba, double w, double h) {
    final fino = 3 * _escala;
    final base = arriba + h * 0.30;
    final fin = x - w / 2 + w * 0.25;
    final f = fase();
    final p = Paint();
    for (var xi = margen; xi < fin; xi += 2 * _escala) {
      final onda = _escala * (((xi - margen) / (5 * _escala) + f).floor() % 2 == 0 ? 0 : 1);
      final ancho = math.min(2 * _escala, fin - xi) + 0.5;
      for (var i = 0; i < _franjas.length; i++) {
        p.color = _franjas[i];
        canvas.drawRect(Rect.fromLTWH(xi, base + i * fino + onda, ancho, fino), p);
      }
    }
  }

  /// El detallito de cada mascota (corazones, estrellas, hojas...) que va quedando atrás y se
  /// desvanece. No guarda nada: se calcula de la posición (misma lógica que el escritorio).
  void _detalles(Canvas canvas, ui.Image hojaEstela, double x, double pies, double w, double h) {
    const n = 7;
    final paso = 21 * _escala;
    final centro = x - w * 0.32;
    final f = fase();
    final ancho = mascota.estelaAncho.toDouble(), alto = mascota.estelaAlto.toDouble();
    for (var i = 0; i < n; i++) {
      final px = centro - (i + 1) * paso;
      if (px < margen) break;
      final vida = 1.0 - i / n;
      final tam = (18 * _escala) * (0.6 + 0.4 * vida);
      final vaiven = math.sin(f * 0.9 + i * 1.3) * 3 * _escala;
      final py = pies - h * 0.42 + vaiven - (1 - vida) * 3 * _escala;
      final variante = (i + f.toInt()) % 2;
      final paint = Paint()
        ..filterQuality = FilterQuality.none
        ..color = Color.fromRGBO(255, 255, 255, 0.25 + 0.75 * vida);
      canvas.drawImageRect(hojaEstela, Rect.fromLTWH(variante * ancho, 0, ancho, alto),
          Rect.fromLTWH(px - tam / 2, py - tam / 2, tam, tam), paint);
    }
  }

  @override
  bool shouldRepaint(covariant _PintorMascota old) => old.hoja != hoja || old.mascota != mascota || old.estela != estela;
}
