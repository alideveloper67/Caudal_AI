import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../nucleo/fondo_app.dart';
import 'plataforma.dart';

/// La paleta de Caudal (la misma que el escritorio): oscuro profundo y un solo
/// acento. El acento y el fondo se pueden cambiar en Ajustes → Aspecto
/// ([Aspecto.aplicar]); por eso no son constantes.
class C {
  static Color fondo = const Color(0xFF06070A);

  /// El fondo de las pantallas: transparente cuando hay una imagen de fondo detrás.
  static Color get fondoVivo => FondoApp.i.activo ? Colors.transparent : fondo;

  static Color panel = const Color(0xFF101217);
  static Color superficie = const Color(0xFF14171D);
  static Color superficie2 = const Color(0xFF1B1F27);
  static Color superficie3 = const Color(0xFF252A35);
  static Color borde = const Color(0xFF222731);
  static const texto = Color(0xFFF3F5F9);
  static const texto2 = Color(0xFFA9B1C0);
  static const texto3 = Color(0xFF6F788A);
  static Color acento = const Color(0xFF22D3EE);
  static Color acentoAlto = const Color(0xFF67E8F9);
  static Color acentoTexto = const Color(0xFF03222B);
  static const violeta = Color(0xFF7C5CFF);
  static const error = Color(0xFFF2555A);
  static const exito = Color(0xFF2BD576);

  /// El degradado de arriba del Inicio (sale del acento).
  static Color get cabecera => Color.lerp(acento, fondo, 0.78)!;
}

/// Los colores y fondos que se pueden elegir.
class Aspecto {
  Aspecto._();

  /// nombre -> (acento, alto, texto sobre el acento)
  static const acentos = <String, (String, Color, Color, Color)>{
    'cian': ('Cian', Color(0xFF22D3EE), Color(0xFF67E8F9), Color(0xFF03222B)),
    'violeta': ('Violeta', Color(0xFF8B6CFF), Color(0xFFB4A1FF), Color(0xFF14093D)),
    'rosa': ('Rosa', Color(0xFFFF5C8A), Color(0xFFFF93B1), Color(0xFF3D0716)),
    'verde': ('Verde', Color(0xFF2BD576), Color(0xFF6EE7A3), Color(0xFF032412)),
    'naranja': ('Naranja', Color(0xFFFF8A3D), Color(0xFFFFB27F), Color(0xFF3A1600)),
    'rojo': ('Rojo', Color(0xFFF2555A), Color(0xFFF78A8D), Color(0xFF3B0608)),
    'azul': ('Azul', Color(0xFF4C8DFF), Color(0xFF8DB5FF), Color(0xFF051A40)),
    'dorado': ('Dorado', Color(0xFFF5C542), Color(0xFFF9DB85), Color(0xFF332400)),
  };

  /// nombre -> (fondo, panel, superficie, superficie2, superficie3, borde)
  static const fondos = <String, (String, List<Color>)>{
    'oscuro': ('Oscuro', [Color(0xFF06070A), Color(0xFF101217), Color(0xFF14171D), Color(0xFF1B1F27),
      Color(0xFF252A35), Color(0xFF222731)]),
    'negro': ('Negro puro', [Color(0xFF000000), Color(0xFF0A0A0A), Color(0xFF101010), Color(0xFF171717),
      Color(0xFF222222), Color(0xFF1C1C1C)]),
    'noche': ('Azul noche', [Color(0xFF070B18), Color(0xFF0E1426), Color(0xFF131A30), Color(0xFF1A2340),
      Color(0xFF243052), Color(0xFF1F2946)]),
    'uva': ('Morado', [Color(0xFF0D0716), Color(0xFF160E24), Color(0xFF1C122E), Color(0xFF251A3B),
      Color(0xFF32244E), Color(0xFF2B2042)]),
    'bosque': ('Bosque', [Color(0xFF050D0A), Color(0xFF0C1813), Color(0xFF111F19), Color(0xFF172A22),
      Color(0xFF20372D), Color(0xFF1C3027)]),
    'grafito': ('Grafito', [Color(0xFF121316), Color(0xFF1A1C20), Color(0xFF202227), Color(0xFF282B31),
      Color(0xFF33373E), Color(0xFF2E3138)]),
  };

  /// Un color propio guardado como «#RRGGBB» (en vez de un nombre de la lista).
  static bool esPropio(String valor) => colorDe(valor) != null;

  static Color? colorDe(String valor) {
    final h = valor.trim();
    if (!h.startsWith('#') || h.length != 7) return null;
    final n = int.tryParse(h.substring(1), radix: 16);
    return n == null ? null : Color(0xFF000000 | n);
  }

  static String hexDe(Color c) =>
      '#${(c.toARGB32() & 0xFFFFFF).toRadixString(16).padLeft(6, '0').toUpperCase()}';

  /// (etiqueta, acento, alto, texto encima) de un acento de la lista o de un
  /// color propio. Los mismos cálculos que el escritorio (estilos.acento_de),
  /// para que un mismo color se vea igual en las dos apps.
  static (String, Color, Color, Color) acentoDe(String valor) {
    final lista = acentos[valor];
    if (lista != null) return lista;
    var c = colorDe(valor);
    if (c == null) return acentos['cian']!;
    // demasiado oscuro no se ve sobre el fondo: se aclara lo justo
    var vueltas = 0;
    while (c!.computeLuminance() < 0.10 && vueltas++ < 30) {
      c = Color.lerp(c, Colors.white, 0.12);
    }
    final alto = Color.lerp(c, Colors.white, 0.35)!;
    final texto = c.computeLuminance() > 0.22 ? Color.lerp(c, Colors.black, 0.85)! : Colors.white;
    return ('Tu color', c, alto, texto);
  }

  /// (etiqueta, [fondo, panel, superficie, superficie2, superficie3, borde]).
  static (String, List<Color>) fondoDe(String valor) {
    final lista = fondos[valor];
    if (lista != null) return lista;
    var c = colorDe(valor);
    if (c == null) return fondos['oscuro']!;
    // el fondo siempre oscuro (el texto de la app es claro)
    var vueltas = 0;
    while (c!.computeLuminance() > 0.035 && vueltas++ < 40) {
      c = Color.lerp(c, Colors.black, 0.15);
    }
    final base = c;
    return ('Tu fondo', [for (final t in [0.0, 0.035, 0.06, 0.09, 0.14, 0.12]) Color.lerp(base, Colors.white, t)!]);
  }

  static void aplicar(String acento, String fondo) {
    final a = acentoDe(acento);
    C.acento = a.$2;
    C.acentoAlto = a.$3;
    C.acentoTexto = a.$4;
    final f = fondoDe(fondo).$2;
    C.fondo = f[0];
    C.panel = f[1];
    C.superficie = f[2];
    C.superficie2 = f[3];
    C.superficie3 = f[4];
    C.borde = f[5];
  }
}

ThemeData temaCaudal() {
  final esquema = ColorScheme.dark(
    primary: C.acento,
    onPrimary: C.acentoTexto,
    secondary: C.acento,
    surface: C.panel,
    onSurface: C.texto,
    error: C.error,
  );
  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: esquema,
    scaffoldBackgroundColor: C.fondoVivo,
    canvasColor: C.fondo,
    // en iPhone no hay ondas al tocar: solo el resaltado, como en las apps del sistema
    splashFactory: esIOS ? NoSplash.splashFactory : InkSparkle.splashFactory,
    visualDensity: VisualDensity.standard,
  );
  return base.copyWith(
    textTheme: base.textTheme.apply(bodyColor: C.texto, displayColor: C.texto),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: C.texto),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: C.fondo.withValues(alpha: 0.96),
      indicatorColor: Colors.transparent,
      height: 62,
      labelTextStyle: WidgetStateProperty.resolveWith((s) => TextStyle(
            fontSize: 11.5,
            fontWeight: FontWeight.w600,
            color: s.contains(WidgetState.selected) ? C.texto : C.texto3,
          )),
      iconTheme: WidgetStateProperty.resolveWith((s) => IconThemeData(
            color: s.contains(WidgetState.selected) ? C.texto : C.texto3,
            size: 26,
          )),
    ),
    bottomSheetTheme: BottomSheetThemeData(
      backgroundColor: C.superficie2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      showDragHandle: true,
      dragHandleColor: C.texto3,
    ),
    snackBarTheme: const SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: C.texto,
      contentTextStyle: TextStyle(color: Color(0xFF0A0B0E), fontWeight: FontWeight.w600),
      actionTextColor: Color(0xFF0B6E82),
      insetPadding: EdgeInsets.fromLTRB(12, 0, 12, 140),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: C.superficie2,
      hintStyle: const TextStyle(color: C.texto3),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
      focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: C.acento, width: 2)),
    ),
    sliderTheme: const SliderThemeData(
      trackHeight: 3.5,
      activeTrackColor: C.texto,
      inactiveTrackColor: Color(0x33FFFFFF),
      thumbColor: C.texto,
      overlayShape: RoundSliderOverlayShape(overlayRadius: 14),
      thumbShape: RoundSliderThumbShape(enabledThumbRadius: 6),
    ),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? C.acentoTexto : C.texto2),
      trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? C.acento : C.superficie3),
      trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
    ),
    pageTransitionsTheme: const PageTransitionsTheme(builders: {
      TargetPlatform.android: PredictiveBackPageTransitionsBuilder(),
      TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
    }),
    dividerTheme: DividerThemeData(color: C.borde, thickness: 1, space: 1),
    listTileTheme: const ListTileThemeData(
      iconColor: C.texto2,
      subtitleTextStyle: estiloSecundario,
      contentPadding: EdgeInsets.symmetric(horizontal: Esp.lado),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: C.texto,
        side: const BorderSide(color: C.texto3),
        shape: const StadiumBorder(),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        textStyle: const TextStyle(fontWeight: FontWeight.w700),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(textStyle: const TextStyle(fontWeight: FontWeight.w700)),
    ),
  );
}

// ---------------------------------------------------------------- jerarquia
//
// Una sola escala para toda la app: titulo de pagina > titulo de barra >
// seccion > fila > secundario > detalle. Las paginas no inventan tamanos.

/// "Buscar", "Descargar", "Sonido": lo primero que se lee en una pagina.
const estiloTituloPagina = TextStyle(fontSize: 28, fontWeight: FontWeight.w900, letterSpacing: -0.6, height: 1.1);

/// El saludo de Inicio y "Tu biblioteca", al lado del avatar.
const estiloTituloBarra = TextStyle(fontSize: 23, fontWeight: FontWeight.w900, letterSpacing: -0.4, height: 1.15);

/// "Volver a escuchar", "Populares"...
const estiloTituloSeccion = TextStyle(fontSize: 21, fontWeight: FontWeight.w800, letterSpacing: -0.3, height: 1.2);

/// El nombre en una fila o una tarjeta.
const estiloTituloFila = TextStyle(fontSize: 15.5, fontWeight: FontWeight.w600, height: 1.25);
const estiloTituloTarjeta = TextStyle(fontSize: 14, fontWeight: FontWeight.w600, height: 1.25);

/// Lo que acompana: artista, numero de canciones, ayudas.
const estiloSecundario = TextStyle(fontSize: 13, color: C.texto2, height: 1.3);
const estiloSubTarjeta = TextStyle(fontSize: 12.5, color: C.texto2, height: 1.25);

/// Notas al pie y avisos pequenos.
const estiloDetalle = TextStyle(fontSize: 12, color: C.texto3, height: 1.35);

/// Los espacios de siempre (multiplos de 4).
class Esp {
  Esp._();
  static const xs = 4.0;
  static const s = 8.0;
  static const m = 12.0;
  static const l = 16.0;
  static const xl = 24.0;
  static const xxl = 32.0;

  /// El margen lateral de todas las paginas.
  static const lado = 16.0;

  /// Entre un carrusel y el siguiente.
  static const entreSecciones = 28.0;
}

/// Las duraciones y curvas de la app: rapidas y sin rebote exagerado.
class Mov {
  Mov._();
  static const rapido = Duration(milliseconds: 140);
  static const normal = Duration(milliseconds: 260);
  static const entrada = Duration(milliseconds: 420);
  static const color = Duration(milliseconds: 520);
  static const curva = Curves.easeOutCubic;
  static const curvaEntrada = Cubic(0.2, 0.8, 0.2, 1);
}
