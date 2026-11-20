// Las insignias de los logros en pixel art (nucleo/logros_dibujos.dart), nítidas a cualquier
// tamaño (sin suavizar) y en grises mientras no se consiguen.

import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../nucleo/logros_dibujos.dart';
import 'tema.dart';

class ImagenesInsignia {
  ImagenesInsignia._();

  static final Map<String, ui.Image> _cache = {};

  /// Color de cada pixel (null = transparente) de una insignia; `apagado`: en grises.
  static List<List<Color?>> pixeles(String clave, {bool apagado = false}) {
    final (paleta, filas) = dibujosLogros[clave] ?? dibujosLogros['primera_nota']!;
    return [
      for (final f in filas)
        [
          for (final s in f.split(''))
            if (s == '.') null else _color(paleta[s]!, apagado),
        ],
    ];
  }

  static Color _color(int argb, bool apagado) {
    final c = Color(argb);
    if (!apagado) return c;
    final r = (c.r * 255).round(), g = (c.g * 255).round(), b = (c.b * 255).round();
    final l = (0.30 * r + 0.59 * g + 0.11 * b);
    final v = (40 + l * 0.42).round();
    return Color.fromARGB(235, v, v, (v + 10).clamp(0, 255));
  }

  /// La insignia como imagen de 24x24 (se guarda: se dibuja una sola vez por clave).
  static ui.Image imagen(String clave, {bool apagado = false}) {
    final k = '$clave|$apagado';
    final hecha = _cache[k];
    if (hecha != null) return hecha;
    final grabadora = ui.PictureRecorder();
    final lienzo = Canvas(grabadora);
    final pincel = Paint()..isAntiAlias = false;
    final px = pixeles(clave, apagado: apagado);
    for (var y = 0; y < px.length; y++) {
      for (var x = 0; x < px[y].length; x++) {
        final c = px[y][x];
        if (c == null) continue;
        pincel.color = c;
        lienzo.drawRect(Rect.fromLTWH(x.toDouble(), y.toDouble(), 1, 1), pincel);
      }
    }
    final img = grabadora.endRecording().toImageSync(ladoDibujoLogro, ladoDibujoLogro);
    _cache[k] = img;
    return img;
  }
}

/// Una insignia con su círculo: con halo si está conseguida, apagada y punteada si no.
class InsigniaLogro extends StatelessWidget {
  const InsigniaLogro({super.key, required this.clave, this.lado = 64, this.conseguida = true, this.halo});

  final String clave;
  final double lado;
  final bool conseguida;
  final Color? halo;

  @override
  Widget build(BuildContext context) {
    final borde = lado + 14;
    return Semantics(
      label: conseguida ? 'Insignia conseguida' : 'Insignia aún no conseguida',
      image: true,
      child: Container(
        width: borde,
        height: borde,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: conseguida ? (halo ?? C.acento).withValues(alpha: 0.16) : C.superficie2,
          border: conseguida ? null : Border.all(color: C.borde, width: 1.2),
        ),
        alignment: Alignment.center,
        child: RawImage(
          image: ImagenesInsignia.imagen(clave, apagado: !conseguida),
          width: lado,
          height: lado,
          filterQuality: FilterQuality.none,
        ),
      ),
    );
  }
}
