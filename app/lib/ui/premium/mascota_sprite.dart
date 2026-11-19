import 'package:flutter/material.dart';

import '../../nucleo/mascota_app.dart';

/// Una mascotita del catálogo, en pixel art nítido y con sus cuadros animados (a ritmo tranquilo, para no
/// gastar batería). Sin animar —o con «Quitar animaciones» del sistema— se queda en el primer cuadro.
///
/// El tamaño es el de un cuadro de la hoja por [escala]; el widget mide justo eso.
class MascotaSprite extends StatefulWidget {
  const MascotaSprite({super.key, required this.mascota, this.escala = 3, this.animar = true});

  final Mascota mascota;
  final double escala;
  final bool animar;

  @override
  State<MascotaSprite> createState() => _MascotaSpriteState();
}

class _MascotaSpriteState extends State<MascotaSprite> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this);

  /// Cuánto dura cada cuadro.
  static const _porCuadro = Duration(milliseconds: 260);

  bool _corre = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _ajustar();
  }

  @override
  void didUpdateWidget(MascotaSprite old) {
    super.didUpdateWidget(old);
    if (old.mascota.clave != widget.mascota.clave || old.animar != widget.animar) _ajustar();
  }

  void _ajustar() {
    final quieta = !widget.animar || MediaQuery.maybeDisableAnimationsOf(context) == true;
    final n = widget.mascota.cuadros;
    if (quieta || n < 2) {
      if (_corre) _c.stop();
      _corre = false;
      _c.value = 0;
      return;
    }
    _c.duration = _porCuadro * n;
    if (!_corre) {
      _corre = true;
      _c.repeat();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.mascota;
    final w = m.ancho * widget.escala;
    final h = m.alto * widget.escala;
    final hoja = Image.asset(
      m.imagen,
      width: w * m.cuadros,
      height: h,
      fit: BoxFit.fill,
      filterQuality: FilterQuality.none,
      excludeFromSemantics: true,
      gaplessPlayback: true,
      errorBuilder: (_, _, _) => SizedBox(width: w * m.cuadros, height: h),
    );
    return Semantics(
      label: m.nombre,
      image: true,
      child: RepaintBoundary(
        child: SizedBox(
          width: w,
          height: h,
          child: ClipRect(
            child: AnimatedBuilder(
              animation: _c,
              child: hoja,
              builder: (_, hijo) {
                final cuadro = (_c.value * m.cuadros).floor().clamp(0, m.cuadros - 1);
                return OverflowBox(
                  alignment: Alignment.topLeft,
                  minWidth: 0,
                  maxWidth: double.infinity,
                  child: Transform.translate(offset: Offset(-cuadro * w, 0), child: hijo),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}
