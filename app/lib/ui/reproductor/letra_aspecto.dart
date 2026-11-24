// Cómo se ve la letra de las canciones: el estilo (Clásica, Nítida, Neón, Oro, Relieve…) y el tipo de letra
// (la tipografía), los dos a elegir en Ajustes › Letra. Clásica con la tipografía predeterminada es la
// letra de siempre (la de antes de la 2.7.4); Nítida es la de borde y brillo de la 2.7.4.
//
// El aspecto elegido vive en [LetraAspecto.actual] (lo pone main.dart al leer los ajustes), así las
// piezas de letra que no tienen los ajustes a mano (la escena, el contorno) lo consultan igual.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show FontLoader, rootBundle;

import '../../nucleo/ajustes.dart';
import '../../reproduccion/reproductor.dart';
import 'letra_disenos.dart';
import 'letra_estilo.dart';
import 'linea_karaoke.dart';

/// Un estilo de letra.
class EstiloLetraDef {
  const EstiloLetraDef(this.clave, this.nombre, this.frase);
  final String clave, nombre, frase;
}

/// Una tipografía para la letra. [familia] null = la del sistema (la de siempre).
class FuenteLetraDef {
  const FuenteLetraDef(this.clave, this.nombre, this.familia,
      {this.peso, this.alto = 1.0, this.espacio, this.archivo, this.tamano = 1.0});
  final String clave, nombre;
  final String? familia;

  /// Peso fijo: las fuentes de un solo grosor se ven mal con negrita inventada.
  final FontWeight? peso;

  /// Cuánto se multiplica el alto de línea (las manuscritas necesitan más aire).
  final double alto;

  /// El archivo en assets/fuentes_extra (se carga al usarla); null = va con la app.
  final String? archivo;

  /// Cuánto se agranda o achica para que todas se vean de un tamaño parecido.
  final double tamano;

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
    EstiloLetraDef('degradado', 'Degradado', 'Se llena con los colores de la carátula'),
    EstiloLetraDef('contorno', 'Contorno', 'Letras huecas que se rellenan al cantarse'),
    EstiloLetraDef('relieve', 'Relieve', 'Letras gruesas en 3D'),
    EstiloLetraDef('marcador', 'Marcador', 'Lo que suena, subrayado con resaltador'),
    EstiloLetraDef('oro', 'Oro', 'Dorada y brillante'),
    EstiloLetraDef('vhs', 'VHS', 'Como una cinta de video antigua'),
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
    FuenteLetraDef('lilita', 'Lilita One', 'LilitaOne', peso: FontWeight.w400, espacio: 0.2, archivo: 'LilitaOne-Regular.ttf'),
    FuenteLetraDef('titan', 'Titan One', 'TitanOne', peso: FontWeight.w400, espacio: 0.2, archivo: 'TitanOne-Regular.ttf', tamano: 0.92, alto: 1.04),
    FuenteLetraDef('bungee', 'Bungee', 'Bungee', peso: FontWeight.w400, espacio: 0.0, archivo: 'Bungee-Regular.ttf', tamano: 0.8, alto: 1.06),
    FuenteLetraDef('russo', 'Russo One', 'RussoOne', peso: FontWeight.w400, espacio: 0.0, archivo: 'RussoOne-Regular.ttf', tamano: 0.93),
    FuenteLetraDef('audiowide', 'Audiowide', 'Audiowide', peso: FontWeight.w400, espacio: 0.0, archivo: 'Audiowide-Regular.ttf', tamano: 0.88, alto: 1.04),
    FuenteLetraDef('monoton', 'Monoton', 'Monoton', peso: FontWeight.w400, espacio: 0.5, archivo: 'Monoton-Regular.ttf', tamano: 0.82, alto: 1.12),
    FuenteLetraDef('abril', 'Abril Fatface', 'AbrilFatface', peso: FontWeight.w400, espacio: 0.0, archivo: 'AbrilFatface-Regular.ttf', alto: 1.04),
    FuenteLetraDef('shrikhand', 'Shrikhand', 'Shrikhand', peso: FontWeight.w400, espacio: 0.0, archivo: 'Shrikhand-Regular.ttf', tamano: 0.92, alto: 1.06),
    FuenteLetraDef('staatliches', 'Staatliches', 'Staatliches', peso: FontWeight.w400, espacio: 0.8, archivo: 'Staatliches-Regular.ttf', tamano: 1.12),
    FuenteLetraDef('marker', 'Permanent Marker', 'PermanentMarker', peso: FontWeight.w400, espacio: 0.0, archivo: 'PermanentMarker-Regular.ttf', tamano: 0.92, alto: 1.1),
    FuenteLetraDef('kaushan', 'Kaushan Script', 'KaushanScript', peso: FontWeight.w400, espacio: 0.0, archivo: 'KaushanScript-Regular.ttf', tamano: 1.06, alto: 1.12),
    FuenteLetraDef('vibes', 'Great Vibes', 'GreatVibes', peso: FontWeight.w400, espacio: 0.0, archivo: 'GreatVibes-Regular.ttf', tamano: 1.22, alto: 1.06),
    FuenteLetraDef('elite', 'Special Elite', 'SpecialElite', peso: FontWeight.w400, espacio: 0.0, archivo: 'SpecialElite-Regular.ttf', tamano: 0.94, alto: 1.06),
    FuenteLetraDef('pixel', 'Press Start 2P', 'PressStart2P', peso: FontWeight.w400, espacio: 0.0, archivo: 'PressStart2P-Regular.ttf', tamano: 0.62, alto: 1.35),
    FuenteLetraDef('limelight', 'Limelight', 'Limelight', peso: FontWeight.w400, espacio: 0.0, archivo: 'Limelight-Regular.ttf', tamano: 0.9, alto: 1.04),
    FuenteLetraDef('caveat', 'Caveat Brush', 'CaveatBrush', peso: FontWeight.w400, espacio: 0.0, archivo: 'CaveatBrush-Regular.ttf', tamano: 1.18),
    FuenteLetraDef('ops', 'Black Ops One', 'BlackOpsOne', peso: FontWeight.w400, espacio: 0.3, archivo: 'BlackOpsOne-Regular.ttf', tamano: 0.88, alto: 1.04),
    FuenteLetraDef('courgette', 'Courgette', 'Courgette', peso: FontWeight.w400, espacio: 0.0, archivo: 'Courgette-Regular.ttf', alto: 1.12),
  ];

  // ------------------------------------------------------------ las tipografías que se cargan al usarlas

  static final Map<String, Future<void>> _cargas = {};

  /// Carga la tipografía [clave] si hace falta y, al llegar, repinta las letras.
  static Future<void> cargarFuente(String clave) {
    final f = fuentes.firstWhere((x) => x.clave == clave, orElse: () => fuentes.first);
    final archivo = f.archivo;
    if (archivo == null) return Future.value();
    return _cargas[clave] ??= () async {
      try {
        await (FontLoader(f.familia!)..addFont(rootBundle.load('assets/fuentes_extra/$archivo'))).load();
        actual.avisar();
      } catch (_) {
        _cargas.remove(clave)?.ignore(); // se verá la de siempre y se volverá a intentar
      }
    }();
  }

  static void cargarTodas() {
    for (final f in fuentes) {
      unawaited(cargarFuente(f.clave));
    }
  }

  /// El aspecto que se está usando (lo actualiza [escuchar]).
  static final AvisoAspecto actual = AvisoAspecto(const LetraAspecto());

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
      unawaited(cargarFuente(n.fuente));
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

  /// Se pinta en capas (letra_disenos.dart).
  bool get enCapas => disenosEnCapas.contains(estilo);

  /// El estilo con la tipografía elegida.
  TextStyle conFuente(TextStyle s) {
    final f = fuenteDef;
    if (f.familia == null) return s;
    return s.copyWith(
      fontFamily: f.familia,
      fontSize: s.fontSize == null ? null : s.fontSize! * f.tamano,
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

/// El aspecto que se usa, y un aviso cuando llega una tipografía que faltaba.
class AvisoAspecto extends ValueNotifier<LetraAspecto> {
  AvisoAspecto(super.value);
  void avisar() => notifyListeners();
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
    this.alinear = TextAlign.start,
  });

  final LetraAspecto aspecto;
  final String texto;
  final TextStyle estilo;
  final bool activa;
  final Color? acento;
  final TextAlign alinear;

  @override
  Widget build(BuildContext context) {
    final s = aspecto.conFuente(estilo);
    if (aspecto.enCapas) {
      return TweenAnimationBuilder<Color?>(
        tween: ColorTween(end: s.color),
        duration: const Duration(milliseconds: 260),
        builder: (_, color, _) => TextoDiseno(
            diseno: aspecto.estilo, texto: texto, estilo: s, activa: activa, acento: acento, alinear: alinear, colorReposo: color),
      );
    }
    if (aspecto.nitida) {
      return TweenAnimationBuilder<Color?>(
        tween: ColorTween(end: s.color),
        duration: const Duration(milliseconds: 260),
        builder: (_, color, _) => TextoLetraResaltado(
          texto: texto,
          estilo: s,
          activo: activa,
          acento: acento,
          alinear: alinear,
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
      textAlign: alinear,
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
    this.adelanto = 250,
    this.alinear = TextAlign.start,
    this.hecho = Colors.white,
  });

  final LetraAspecto aspecto;
  final String texto;
  final TextStyle estilo;
  final int inicio, fin;
  final Reproductor r;

  /// Color de lo que falta por cantar (Clásica y Neón).
  final Color porVenir;
  final Color? acento;

  /// Lo que se adelanta la letra al cambiar de línea, con lo que la movió la persona.
  final int adelanto;
  final TextAlign alinear;

  /// Color de lo ya cantado (Clásica y Neón).
  final Color hecho;

  @override
  Widget build(BuildContext context) {
    final s = aspecto.conFuente(estilo);
    if (aspecto.enCapas) {
      return AvanceKaraoke(
        inicio: inicio,
        fin: fin,
        r: r,
        adelanto: adelanto,
        hacer: (p) => TextoDiseno(
            diseno: aspecto.estilo, texto: texto, estilo: s, progreso: p, acento: acento, alinear: alinear),
      );
    }
    switch (aspecto.estilo) {
      case 'nitida':
        return LineaActivaKaraoke(
            texto: texto, estilo: s, inicio: inicio, fin: fin, r: r, acento: acento, adelanto: adelanto, alinear: alinear);
      case 'simple':
        return Text(texto, textAlign: alinear, style: s.copyWith(color: Colors.white));
      case 'neon':
        return LineaKaraoke(
          texto: texto,
          estilo: s.copyWith(shadows: LetraAspecto.brilloNeon(acento ?? Colors.white)),
          inicio: inicio,
          fin: fin,
          r: r,
          hecho: hecho,
          falta: porVenir,
          adelanto: adelanto,
          alineacion: alinear,
        );
      default:
        return LineaKaraoke(
            texto: texto, estilo: s, inicio: inicio, fin: fin, r: r, hecho: hecho, falta: porVenir,
            adelanto: adelanto, alineacion: alinear);
    }
  }
}

/// Una línea quieta con un avance fijo: las muestras y las vistas previas.
class LineaLetraFija extends StatelessWidget {
  const LineaLetraFija({
    super.key,
    required this.aspecto,
    required this.texto,
    required this.estilo,
    this.progreso = 1,
    this.acento,
    this.alinear = TextAlign.start,
  });

  final LetraAspecto aspecto;
  final String texto;
  final TextStyle estilo;
  final double progreso;
  final Color? acento;
  final TextAlign alinear;

  @override
  Widget build(BuildContext context) {
    final s = aspecto.conFuente(estilo);
    if (aspecto.enCapas) {
      return TextoDiseno(
          diseno: aspecto.estilo, texto: texto, estilo: s, progreso: progreso, acento: acento, alinear: alinear);
    }
    if (aspecto.nitida) {
      return TextoLetraResaltado(
          texto: texto, estilo: s, activo: true, acento: acento, progreso: progreso, alinear: alinear);
    }
    return Text(texto,
        textAlign: alinear,
        style: s.copyWith(
            color: Colors.white, shadows: aspecto.neon ? LetraAspecto.brilloNeon(acento ?? Colors.white) : null));
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
    if (aspecto.enCapas) {
      // un texto largo se pinta sobrio (en relieve, oro…), sin el barrido de la línea que suena
      return TextoDiseno(diseno: aspecto.estilo, texto: texto, estilo: s, activa: false, colorReposo: Colors.white);
    }
    return Text(texto, style: s);
  }
}
