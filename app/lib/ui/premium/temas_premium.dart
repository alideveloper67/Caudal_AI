import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Un tema de color exclusivo para donadores: acento y las seis capas del fondo
/// ([fondo, panel, superficie, superficie2, superficie3, borde]), las mismas que usa
/// `Aspecto.fondos`, para que se aplique con el sistema de tema que ya existe.
class TemaPremium {
  const TemaPremium(this.clave, this.nombre, this.acento, this.capas);

  final String clave;
  final String nombre;
  final Color acento;
  final List<Color> capas;

  Color get fondo => capas[0];

  /// El acento aclarado (para textos y detalles sobre el fondo).
  Color get acentoAlto => Color.lerp(acento, Colors.white, 0.35)!;

  /// El texto que va sobre el acento (botones): el más oscuro o el más claro, el que más contraste dé.
  Color get acentoTexto => TemasPremium.textoSobre(acento);
}

class TemasPremium {
  TemasPremium._();

  static const lista = <TemaPremium>[
    TemaPremium('atardecer', 'Atardecer', Color(0xFFFF7A59), [
      Color(0xFF14090F), Color(0xFF1D0F17), Color(0xFF24141D), Color(0xFF2E1B26), Color(0xFF3B2531), Color(0xFF33202B)]),
    TemaPremium('bosque', 'Bosque', Color(0xFF5FD38D), [
      Color(0xFF06100B), Color(0xFF0D1913), Color(0xFF12211A), Color(0xFF192C23), Color(0xFF23392F), Color(0xFF1E3228)]),
    TemaPremium('sakura', 'Sakura', Color(0xFFFF8FB8), [
      Color(0xFF160A12), Color(0xFF1F1119), Color(0xFF261720), Color(0xFF301E29), Color(0xFF3E2A36), Color(0xFF36232F)]),
    TemaPremium('oceano', 'Océano', Color(0xFF38BDF8), [
      Color(0xFF04101A), Color(0xFF0A1A28), Color(0xFF0F2133), Color(0xFF162B41), Color(0xFF20384F), Color(0xFF1B3248)]),
    TemaPremium('medianoche', 'Medianoche', Color(0xFFA78BFA), [
      Color(0xFF05050F), Color(0xFF0C0C1D), Color(0xFF11112A), Color(0xFF181837), Color(0xFF232348), Color(0xFF1D1D3F)]),
    TemaPremium('ambar', 'Ámbar', Color(0xFFFBBF24), [
      Color(0xFF100B04), Color(0xFF19120A), Color(0xFF20180D), Color(0xFF2A2012), Color(0xFF372B1A), Color(0xFF30251A)]),
  ];

  static TemaPremium? de(String clave) {
    for (final t in lista) {
      if (t.clave == clave) return t;
    }
    return null;
  }

  static double _canal(double v) => v <= 0.03928 ? v / 12.92 : math.pow((v + 0.055) / 1.055, 2.4).toDouble();

  /// Luminancia relativa (WCAG).
  static double luminancia(Color c) => 0.2126 * _canal(c.r) + 0.7152 * _canal(c.g) + 0.0722 * _canal(c.b);

  /// Razón de contraste entre dos colores (1 a 21). AA pide 4,5 para texto normal.
  static double contraste(Color a, Color b) {
    final la = luminancia(a), lb = luminancia(b);
    final alto = math.max(la, lb), bajo = math.min(la, lb);
    return (alto + 0.05) / (bajo + 0.05);
  }

  static const _oscuro = Color(0xFF05070A);

  /// Negro suave o blanco, según con cuál se lea mejor sobre [fondo].
  static Color textoSobre(Color fondo) =>
      contraste(_oscuro, fondo) >= contraste(Colors.white, fondo) ? _oscuro : Colors.white;
}
