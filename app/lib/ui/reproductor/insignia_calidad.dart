import 'package:flutter/material.dart';

import '../../nucleo/calidad_sonido.dart';

/// La insignia discreta con el códec y la tasa de lo que suena (p. ej. «Opus · 160 kbps»).
/// Se encoge en vez de desbordar en pantallas estrechas y la lee entera el lector de pantalla.
class InsigniaCalidad extends StatelessWidget {
  const InsigniaCalidad({super.key, required this.calidad, required this.color});

  final CalidadSonido calidad;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Calidad: ${calidad.detalle}',
      excludeSemantics: true,
      child: Tooltip(
        message: calidad.detalle,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 112),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(
                border: Border.all(color: color.withValues(alpha: 0.45)),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(calidad.etiqueta,
                  maxLines: 1,
                  style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: color.withValues(alpha: 0.95))),
            ),
          ),
        ),
      ),
    );
  }
}
