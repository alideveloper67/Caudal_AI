// Cómo se ve la letra de las canciones: el estilo (Clásica, Nítida, Neón, Simple) y el tipo de letra
// (la tipografía), los dos a elegir en Ajustes › Letra. Clásica con la tipografía predeterminada es la
// letra de siempre (la de antes de la 2.7.4); Nítida es la de borde y brillo de la 2.7.4.
//
// El aspecto elegido vive en [LetraAspecto.actual] (lo pone main.dart al leer los ajustes), así las
// piezas de letra que no tienen los ajustes a mano (la escena, el contorno) lo consultan igual.

import 'package:flutter/material.dart';

import '../../nucleo/ajustes.dart';
import '../../reproduccion/reproductor.dart';
import 'letra_estilo.dart';
import 'linea_karaoke.dart';

/// Un estilo de letra.
class EstiloLetraDef {
  const EstiloLetraDef(this.clave, this.nombre, this.frase);
  final String clave, nombre, frase;
}

/// Una tipografía para la letra. [familia] null = la del sistema (la de siempre).
class FuenteLetraDef {
  const FuenteLetraDef(this.clave, this.nombre, this.familia, {this.peso, this.alto = 1.0, this.espacio});
  final String clave, nombre;
  final String? familia;

  /// Peso fijo: las fuentes de un solo grosor se ven mal con negrita inventada.
  final FontWeight? peso;

  /// Cuánto se multiplica el alto de línea (las manuscritas necesitan más aire).
  final double alto;

  /// Espaciado entre letras propio (las condensadas en mayúsculas respiran mejor con algo más).
  final double? espacio;
}

class LetraAspecto {
  const LetraAspecto({this.estilo = 'clasica', this.fuente = 'predeterminada'});

  final String estilo;
  final String fuente;

  static const estilos = [
    EstiloLetraDef('clasica', 'Clásica', 'La de siempre'),
    EstiloLetraDef('nitida', 'Nítida', 'Con borde y sombra: se lee sobre cualquier fondo'),
    EstiloLetraDef('neon', 'Neón', 'Brilla con el color de la app'),
    EstiloLetraDef('simple', 'Simple', 'Limpia y ligera, ideal para teléfonos sencillos'),
  ];

  static const fuentes = [
    FuenteLetraDef('predeterminada', 'Predeterminada', null),
    FuenteLetraDef('poppins', 'Poppins', 'Poppins'),
    FuenteLetraDef('bebas', 'Bebas Neue', 'BebasNeue', peso: FontWeight.w400, espacio: 0.8),
    FuenteLetraDef('anton', 'Anton', 'Anton', peso: FontWeight.w400, espacio: 0.4),
    FuenteLetraDef('righteous', 'Righteous', 'Righteous', peso: FontWeight.w400),
    FuenteLetraDef('serif', 'DM Serif', 'DMSerifDisplay', peso: FontWeight.w400),
    FuenteLetraDef('pacifico', 'Pacifico', 'Pacifico', peso: FontWeight.w400, alto: 1.12),
    FuenteLetraDef('lobster', 'Lobster', 'Lobster', peso: FontWeight.w400, alto: 1.06),
    FuenteLetraDef('bangers', 'Bangers', 'Bangers', peso: FontWeight.w400, espacio: 1.0),
  ];

  /// El aspecto que se está usando (lo actualiza [escuchar]).
  static final ValueNotifier<LetraAspecto> actual = ValueNotifier(const LetraAspecto());

  static LetraAspecto deAjustes(Ajustes a) {
    String leer(String clave, String porDefecto) {
      try {
        final v = a.texto(clave);
        return v.isEmpty ? porDefecto : v;
      } catch (_) {
        return porDefecto;
      }
    }

    final e = leer('estilo_letra', 'clasica');
    final f = leer('fuente_letra', 'predeterminada');
    return LetraAspecto(
      estilo: estilos.any((x) => x.clave == e) ? e : 'clasica',
      fuente: fuentes.any((x) => x.clave == f) ? f : 'predeterminada',
    );
  }

  /// Mantiene [actual] al día con los ajustes.
  static void escuchar(Ajustes a) {
    // otra cuenta, otros ajustes: se deja de escuchar los anteriores
    final antes = _escuchados;
    if (antes != null && _oyente != null) antes.removeListener(_oyente!);
    void leer() {
      final n = deAjustes(a);
      if (n != actual.value) actual.value = n;
    }

    _escuchados = a;
    _oyente = leer;
    leer();
    a.addListener(leer);
  }

  static Ajustes? _escuchados;
  static VoidCallback? _oyente;

  FuenteLetraDef get fuenteDef => fuentes.firstWhere((x) => x.clave == fuente, orElse: () => fuentes.first);

  bool get nitida => estilo == 'nitida';
  bool get neon => estilo == 'neon';
  bool get simple => estilo == 'simple';

  /// El estilo con la tipografía elegida.
  TextStyle conFuente(TextStyle s) {
    final f = fuenteDef;
    if (f.familia == null) return s;
    return s.copyWith(
      fontFamily: f.familia,
      fontWeight: f.peso ?? s.fontWeight,
      height: s.height == null ? null : s.height! * f.alto,
      letterSpacing: f.espacio ?? s.letterSpacing,
    );
  }

  /// Brillo de neón alrededor del texto.
  static List<Shadow> brilloNeon(Color c, {double fuerza = 1}) => [
        Shadow(color: c.withValues(alpha: 0.95 * fuerza), blurRadius: 10),
        Shadow(color: c.withValues(alpha: 0.6 * fuerza), blurRadius: 26),
      ];

  @override
  bool operator ==(Object other) => other is LetraAspecto && other.estilo == estilo && other.fuente == fuente;
  @override
  int get hashCode => Object.hash(estilo, fuente);
}

/// Una línea que no está sonando (cantada o por venir), en el estilo elegido. [estilo] ya trae el
/// color de su estado; el cambio de color se anima 260 ms, como siempre.
class LineaLetra extends StatelessWidget {
  const LineaLetra({
    super.key,
    required this.aspecto,
    required this.texto,
    required this.estilo,
    this.activa = false,
    this.acento,
  });

  final LetraAspecto aspecto;
  final String texto;
  final TextStyle estilo;
  final bool activa;
  final Color? acento;

  @override
  Widget build(BuildContext context) {
    final s = aspecto.conFuente(estilo);
    if (aspecto.nitida) {
      return TweenAnimationBuilder<Color?>(
        tween: ColorTween(end: s.color),
        duration: const Duration(milliseconds: 260),
        builder: (_, color, _) => TextoLetraResaltado(
          texto: texto,
          estilo: s,
          activo: activa,
          acento: acento,
          colorReposo: color,
        ),
      );
    }
    var final_ = s;
    if (aspecto.simple && !activa) {
      final_ = s.copyWith(color: (s.color ?? Colors.white).withValues(alpha: ((s.color?.a ?? 1) * 0.65).clamp(0.0, 1.0)));
    } else if (aspecto.neon && activa) {
      final_ = s.copyWith(shadows: LetraAspecto.brilloNeon(acento ?? Colors.white));
    }
    return AnimatedDefaultTextStyle(
      duration: const Duration(milliseconds: 260),
      style: final_,
      child: Text(texto),
    );
  }
}

/// La línea que suena, en el estilo elegido (con el barrido de karaoke salvo en Simple).
class LineaLetraActiva extends StatelessWidget {
  const LineaLetraActiva({
    super.key,
    required this.aspecto,
    required this.texto,
    required this.estilo,
    required this.inicio,
    required this.fin,
    required this.r,
    required this.porVenir,
    this.acento,
  });

  final LetraAspecto aspecto;
  final String texto;
  final TextStyle estilo;
  final int inicio, fin;
  final Reproductor r;

  /// Color de lo que falta por cantar (Clásica y Neón).
  final Color porVenir;
  final Color? acento;

  @override
  Widget build(BuildContext context) {
    final s = aspecto.conFuente(estilo);
    switch (aspecto.estilo) {
      case 'nitida':
        return LineaActivaKaraoke(texto: texto, estilo: s, inicio: inicio, fin: fin, r: r, acento: acento);
      case 'simple':
        return Text(texto, style: s.copyWith(color: Colors.white));
      case 'neon':
        return LineaKaraoke(
          texto: texto,
          estilo: s.copyWith(shadows: LetraAspecto.brilloNeon(acento ?? Colors.white)),
          inicio: inicio,
          fin: fin,
          r: r,
          hecho: Colors.white,
          falta: porVenir,
        );
      default:
        return LineaKaraoke(texto: texto, estilo: s, inicio: inicio, fin: fin, r: r, hecho: Colors.white, falta: porVenir);
    }
  }
}

/// Letra sin tiempos (un bloque de texto), en el estilo elegido.
class TextoLetraPlano extends StatelessWidget {
  const TextoLetraPlano({super.key, required this.aspecto, required this.texto, required this.estilo});
  final LetraAspecto aspecto;
  final String texto;
  final TextStyle estilo;

  @override
  Widget build(BuildContext context) {
    final s = aspecto.conFuente(estilo);
    if (aspecto.nitida) return TextoLetraResaltado(texto: texto, estilo: s, colorReposo: Colors.white);
    return Text(texto, style: s);
  }
}
