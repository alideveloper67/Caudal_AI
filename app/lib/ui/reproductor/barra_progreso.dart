// La barra de progreso del reproductor: fina mientras suena, gruesa al
// tocarla, con el tiempo flotando sobre el dedo.
//
// Se pinta con un CustomPainter que escucha la posicion directamente: avanzar
// la cancion o arrastrar el dedo repinta solo la barra, sin reconstruir nada.
// Los textos de tiempo van aparte y solo se rehacen al cambiar de segundo.

import 'dart:async';
import 'dart:ui' show lerpDouble;

import 'package:flutter/material.dart';

import '../../reproduccion/reproductor.dart';
import '../plataforma.dart';
import '../tema.dart';
import 'mascota_barra.dart';

String tiempo(Duration d) {
  final s = d.inSeconds;
  final h = s ~/ 3600, m = (s % 3600) ~/ 60, ss = s % 60;
  return h > 0 ? '$h:${m.toString().padLeft(2, '0')}:${ss.toString().padLeft(2, '0')}' : '$m:${ss.toString().padLeft(2, '0')}';
}

class BarraProgreso extends StatefulWidget {
  const BarraProgreso({super.key, required this.r});
  final Reproductor r;

  @override
  State<BarraProgreso> createState() => _BarraProgresoState();
}

class _BarraProgresoState extends State<BarraProgreso> with SingleTickerProviderStateMixin {
  /// Fraccion bajo el dedo (null = manda la reproduccion).
  final _dedo = ValueNotifier<double?>(null);
  late final AnimationController _activo =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 180), reverseDuration: const Duration(milliseconds: 320));
  late final Listenable _cambios = Listenable.merge([widget.r.posicion, widget.r.duracion, _dedo]);
  double _ancho = 1;
  Timer? _espera;
  int? _destino;

  static const _margen = 14.0; // lo que la barra deja a cada lado (como el Slider de antes)

  /// Los textos de tiempo (segundo actual y duracion): solo cambian una vez
  /// por segundo, asi la columna de debajo no se reconstruye con cada aviso.
  late final ValueNotifier<(int, int)> _textos = ValueNotifier(_segundos());

  (int, int) _segundos() {
    final d = widget.r.duracion.value;
    return ((_fraccion() * d.inMilliseconds).round() ~/ 1000, d.inSeconds);
  }

  void _alCambiar() => _textos.value = _segundos();

  @override
  void initState() {
    super.initState();
    widget.r.posicion.addListener(_alLlegar);
    _cambios.addListener(_alCambiar);
  }

  @override
  void dispose() {
    widget.r.posicion.removeListener(_alLlegar);
    _cambios.removeListener(_alCambiar);
    _textos.dispose();
    _espera?.cancel();
    _activo.dispose();
    _dedo.dispose();
    super.dispose();
  }

  int get _duracion => widget.r.duracion.value.inMilliseconds;

  double _fraccion() {
    final d = _duracion;
    if (_dedo.value != null) return _dedo.value!;
    return d <= 0 ? 0 : (widget.r.posicion.value.inMilliseconds / d).clamp(0.0, 1.0);
  }

  double _deX(double x) => ((x - _margen) / (_ancho - 2 * _margen)).clamp(0.0, 1.0);

  /// Tras soltar, la barra se queda donde la dejo el dedo hasta que la
  /// reproduccion llega alli: sin esto saltaria atras un instante.
  void _alLlegar() {
    final destino = _destino;
    if (destino == null) return;
    if ((widget.r.posicion.value.inMilliseconds - destino).abs() < 1500) _liberar();
  }

  void _liberar() {
    _espera?.cancel();
    _destino = null;
    _dedo.value = null;
  }

  void _empezar(double x) {
    if (_duracion <= 0) return;
    _espera?.cancel();
    _destino = null;
    Haptico.seleccion();
    _activo.forward();
    _dedo.value = _deX(x);
  }

  void _mover(double x) {
    if (_duracion <= 0 || _dedo.value == null || _destino != null) return;
    _dedo.value = _deX(x);
  }

  /// El toque se convirtio en otro gesto (arrastrar o desplazar la pagina):
  /// se suelta sin buscar.
  void _cancelar() {
    if (_destino != null) return;
    _activo.reverse();
    _liberar();
  }

  void _terminar() {
    final f = _dedo.value;
    _activo.reverse();
    if (f == null || _duracion <= 0 || _destino != null) return;
    final ms = (f * _duracion).round();
    _destino = ms;
    widget.r.buscar(Duration(milliseconds: ms));
    _espera = Timer(const Duration(milliseconds: 1200), _liberar);
  }

  void _saltar(int segundos) {
    final d = _duracion;
    if (d <= 0) return;
    final ms = (widget.r.posicion.value.inMilliseconds + segundos * 1000).clamp(0, d);
    widget.r.buscar(Duration(milliseconds: ms));
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.r;
    const estiloTiempo = TextStyle(fontSize: 12, color: Color(0xCCFFFFFF), fontFeatures: [FontFeature.tabularFigures()]);
    final barra = LayoutBuilder(builder: (context, lim) {
      _ancho = lim.maxWidth;
      return GestureDetector(
        behavior: HitTestBehavior.opaque,
        onHorizontalDragStart: (d) => _empezar(d.localPosition.dx),
        onHorizontalDragUpdate: (d) => _mover(d.localPosition.dx),
        onHorizontalDragEnd: (_) => _terminar(),
        onHorizontalDragCancel: _cancelar,
        onTapDown: (d) => _empezar(d.localPosition.dx),
        onTapUp: (_) => _terminar(),
        onTapCancel: _cancelar,
        child: SizedBox(
          height: 40,
          width: double.infinity,
          child: Stack(clipBehavior: Clip.none, children: [
            Positioned.fill(
              child: CustomPaint(
                painter: _Pintor(fraccion: _fraccion, activo: _activo, repintar: Listenable.merge([_cambios, _activo])),
              ),
            ),
            // la mascotita de donadores y fundadores (sin ella, no se crea nada)
            Positioned.fill(
              child: IgnorePointer(
                child: MascotaEnBarra(r: r, fraccion: _fraccion, cambios: _cambios, margen: _margen),
              ),
            ),
            // el tiempo que flota sobre el dedo
            AnimatedBuilder(
              animation: Listenable.merge([_activo, _dedo]),
              builder: (_, _) {
                final a = Curves.easeOut.transform(_activo.value);
                if (a == 0) return const SizedBox.shrink();
                final f = _fraccion();
                final x = _margen + f * (_ancho - 2 * _margen);
                const anchoGlobo = 64.0;
                return Positioned(
                  left: (x - anchoGlobo / 2).clamp(0.0, (_ancho - anchoGlobo).clamp(0.0, double.infinity)),
                  top: -30 + (1 - a) * 8,
                  width: anchoGlobo,
                  child: Opacity(
                    opacity: a,
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: C.texto,
                        borderRadius: BorderRadius.circular(8),
                        boxShadow: const [BoxShadow(color: Color(0x55000000), blurRadius: 10, offset: Offset(0, 3))],
                      ),
                      child: Text(tiempo(Duration(milliseconds: (f * _duracion).round())),
                          style: estiloTiempo.copyWith(color: C.fondo, fontWeight: FontWeight.w800, fontSize: 12.5)),
                    ),
                  ),
                );
              },
            ),
          ]),
        ),
      );
    });
    return ValueListenableBuilder<(int, int)>(
      valueListenable: _textos,
      child: barra,
      builder: (_, segundos, hijo) {
        final d = r.duracion.value;
        final ahora = Duration(seconds: segundos.$1);
        Duration mas(int seg) => Duration(milliseconds: (ahora.inMilliseconds + seg * 1000).clamp(0, d.inMilliseconds));
        return Semantics(
          slider: true,
          label: 'Progreso de la canción',
          value: '${tiempo(ahora)} de ${tiempo(d)}',
          increasedValue: '${tiempo(mas(10))} de ${tiempo(d)}',
          decreasedValue: '${tiempo(mas(-10))} de ${tiempo(d)}',
          onIncrease: () => _saltar(10),
          onDecrease: () => _saltar(-10),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            ExcludeSemantics(child: hijo!),
            ExcludeSemantics(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: _margen),
                child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                  Text(tiempo(ahora), style: estiloTiempo),
                  Text(tiempo(d), style: estiloTiempo),
                ]),
              ),
            ),
          ]),
        );
      },
    );
  }
}

class _Pintor extends CustomPainter {
  _Pintor({required this.fraccion, required this.activo, required Listenable repintar}) : super(repaint: repintar);

  final double Function() fraccion;
  final Animation<double> activo;

  @override
  void paint(Canvas canvas, Size size) {
    final a = Curves.easeOutCubic.transform(activo.value);
    final alto = lerpDouble(4, 9, a)!;
    const margen = _BarraProgresoState._margen;
    final y = size.height / 2;
    final ancho = size.width - 2 * margen;
    final f = fraccion();
    final pista = RRect.fromRectAndRadius(
        Rect.fromLTWH(margen, y - alto / 2, ancho, alto), Radius.circular(alto / 2));
    canvas.drawRRect(pista, Paint()..color = Color.lerp(const Color(0x40FFFFFF), const Color(0x55FFFFFF), a)!);
    if (f > 0) {
      canvas.save();
      canvas.clipRRect(pista);
      canvas.drawRect(Rect.fromLTWH(margen, y - alto / 2, ancho * f, alto), Paint()..color = C.texto);
      canvas.restore();
    }
    // la bolita: pequena mientras suena, mas grande al arrastrar
    final x = margen + ancho * f;
    final radio = lerpDouble(6, 9, a)!;
    if (a > 0) {
      canvas.drawCircle(Offset(x, y), radio + 7 * a, Paint()..color = Color.fromRGBO(255, 255, 255, 0.16 * a));
    }
    canvas.drawCircle(Offset(x, y), radio, Paint()..color = C.texto);
  }

  @override
  bool shouldRepaint(covariant _Pintor old) => old.activo != activo;
}
