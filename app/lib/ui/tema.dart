import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../nucleo/fondo_app.dart';
import '../nucleo/premium.dart';
import 'plataforma.dart';
import 'premium/temas_premium.dart';

/// La paleta de Caudal (la misma que el escritorio): oscuro profundo y un solo
/// acento. El acento y el fondo se pueden cambiar en Ajustes → Aspecto
/// ([Aspecto.aplicar]); por eso no son constantes.
class C {
  static Color fondo = const Color(0xFF06070A);

  /// Hay algo detrás de las pantallas: la imagen de «Fondo de Caudal» o el
  /// mosaico de un fondo con personaje.
  static bool get hayFondo => FondoApp.i.activo || Aspecto.patron != null;

  /// El fondo de las pantallas: transparente cuando hay algo detrás.
  static Color get fondoVivo => hayFondo ? Colors.transparent : fondo;

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

  /// Fondos con personaje: nombre, su acento (se pone al elegirlo) y sus capas
  /// [fondo, panel, superficie, superficie2, superficie3, borde]. Detrás de toda
  /// la app va su mosaico (`assets/fondos/<clave>.png`, densidad 2). Los mismos
  /// que el escritorio (herramientas/mascotas/fondos_tematicos.py).
  static const temas = <String, (String, Color, List<Color>)>{
    'hellokitty': ('Hello Kitty', Color(0xFFFF4D6D), [Color(0xFF1C0A10), Color(0xFF241318), Color(0xFF2A191E), Color(0xFF302026), Color(0xFF3C2C31), Color(0xFF37272D)]),
    'kuromi': ('Kuromi', Color(0xFFFF77B7), [Color(0xFF120A1C), Color(0xFF1A1324), Color(0xFF20192A), Color(0xFF272030), Color(0xFF332C3C), Color(0xFF2E2737)]),
    'pikachu': ('Pikachu', Color(0xFFF5D142), [Color(0xFF17130A), Color(0xFF1F1B13), Color(0xFF252119), Color(0xFF2C2820), Color(0xFF37342C), Color(0xFF332F27)]),
    'charmander': ('Charmander', Color(0xFFFF8A3D), [Color(0xFF1A0D07), Color(0xFF221510), Color(0xFF281C16), Color(0xFF2F231D), Color(0xFF3A2F2A), Color(0xFF352A25)]),
    'squirtle': ('Squirtle', Color(0xFF5EC8E5), [Color(0xFF071420), Color(0xFF101C28), Color(0xFF16222D), Color(0xFF1D2934), Color(0xFF2A353F), Color(0xFF25303B)]),
    'bulbasaur': ('Bulbasaur', Color(0xFF5FD3A0), [Color(0xFF061712), Color(0xFF0F1F1A), Color(0xFF152520), Color(0xFF1C2C27), Color(0xFF293733), Color(0xFF24332E)]),
    'snoopy': ('Snoopy', Color(0xFFE8403F), [Color(0xFF111215), Color(0xFF191A1D), Color(0xFF1F2023), Color(0xFF26272A), Color(0xFF323336), Color(0xFF2E2E31)]),
    'totoro': ('Totoro', Color(0xFF8CCB6E), [Color(0xFF0E1210), Color(0xFF161A18), Color(0xFF1C201E), Color(0xFF242726), Color(0xFF303331), Color(0xFF2B2E2D)]),
    'mymelody': ('My Melody', Color(0xFFFF6FA5), [Color(0xFF1C0A16), Color(0xFF24131E), Color(0xFF2A1924), Color(0xFF30202B), Color(0xFF3C2C37), Color(0xFF372732)]),
    'purin': ('Pompompurin', Color(0xFFF7C948), [Color(0xFF181306), Color(0xFF201B0F), Color(0xFF262115), Color(0xFF2D281C), Color(0xFF383429), Color(0xFF342F24)]),
    'cinnamoroll': ('Cinnamoroll', Color(0xFF7FB8FF), [Color(0xFF0A1324), Color(0xFF131B2C), Color(0xFF192131), Color(0xFF202838), Color(0xFF2C3443), Color(0xFF272F3E)]),
    'kirby': ('Kirby', Color(0xFFFF8FB8), [Color(0xFF1C0B16), Color(0xFF24141E), Color(0xFF2A1A24), Color(0xFF30212B), Color(0xFF3C2D37), Color(0xFF372832)]),
    'doraemon': ('Doraemon', Color(0xFF2E8BFF), [Color(0xFF06111F), Color(0xFF0F1927), Color(0xFF151F2C), Color(0xFF1C2633), Color(0xFF29323E), Color(0xFF242E3A)]),
    'olaf': ('Olaf', Color(0xFF8ECDF5), [Color(0xFF0A1520), Color(0xFF131D28), Color(0xFF19232D), Color(0xFF202A34), Color(0xFF2C363F), Color(0xFF27313B)]),
    'nyan': ('Nyan Cat', Color(0xFFFF7AC8), [Color(0xFF0B0E2C), Color(0xFF141633), Color(0xFF1A1C39), Color(0xFF21243F), Color(0xFF2D304A), Color(0xFF282B45)]),
    'capibara': ('Capibara', Color(0xFFFFA53D), [Color(0xFF1A1008), Color(0xFF221811), Color(0xFF281E17), Color(0xFF2F261E), Color(0xFF3A312B), Color(0xFF352D26)]),
    'pochacco': ('Pochacco', Color(0xFFFF3D86), [Color(0xFF1A0A12), Color(0xFF22131A), Color(0xFF281920), Color(0xFF2F2027), Color(0xFF3A2C33), Color(0xFF35272E)]),
    'nailong': ('Nailong', Color(0xFFFFD23F), [Color(0xFF181406), Color(0xFF201C0F), Color(0xFF262215), Color(0xFF2D291C), Color(0xFF383529), Color(0xFF343024)]),
    'messi': ('Messi', Color(0xFFE8395F), [Color(0xFF0E0A1E), Color(0xFF161326), Color(0xFF1C192C), Color(0xFF242032), Color(0xFF302C3E), Color(0xFF2B2739)]),
    'wos': ('WOS', Color(0xFF3D8BFF), [Color(0xFF060C24), Color(0xFF0F152C), Color(0xFF151B31), Color(0xFF1C2238), Color(0xFF292E43), Color(0xFF24293E)]),
    'nightwing': ('Nightwing', Color(0xFF2E9BFF), [Color(0xFF070B16), Color(0xFF10141E), Color(0xFF161A24), Color(0xFF1D212B), Color(0xFF2A2D37), Color(0xFF252832)]),
    'goku_ultra': ('Goku Ultra Instinto', Color(0xFFC9D3E6), [Color(0xFF0E1118), Color(0xFF161920), Color(0xFF1C1F26), Color(0xFF24262D), Color(0xFF303238), Color(0xFF2B2E34)]),
    'goku_blue': ('Goku Super Saiyajin Blue', Color(0xFF32C5FF), [Color(0xFF061226), Color(0xFF0F1A2E), Color(0xFF152033), Color(0xFF1C273A), Color(0xFF293344), Color(0xFF242E40)]),
    'wanda': ('Wanda', Color(0xFFFF2D45), [Color(0xFF1E0609), Color(0xFF260F12), Color(0xFF2C1518), Color(0xFF321C1F), Color(0xFF3E292B), Color(0xFF392427)]),
    'loki': ('Loki', Color(0xFFE8B23A), [Color(0xFF06150B), Color(0xFF0F1D14), Color(0xFF15231A), Color(0xFF1C2A21), Color(0xFF29362D), Color(0xFF243128)]),
    'jake': ('Jake el Perro', Color(0xFFFFC21F), [Color(0xFF1A1204), Color(0xFF221A0D), Color(0xFF282013), Color(0xFF2F271B), Color(0xFF3A3327), Color(0xFF352E22)]),
    'finn': ('Finn el Humano', Color(0xFF4FB3FF), [Color(0xFF06121F), Color(0xFF0F1A27), Color(0xFF15202C), Color(0xFF1C2733), Color(0xFF29333E), Color(0xFF242E3A)]),
    'marceline': ('Marceline', Color(0xFFE5303F), [Color(0xFF130A1E), Color(0xFF1B1326), Color(0xFF21192C), Color(0xFF282032), Color(0xFF342C3E), Color(0xFF2F2739)]),
    'pan_canela': ('Pan de Canela', Color(0xFFE08A3C), [Color(0xFF1A0E06), Color(0xFF22160F), Color(0xFF281C15), Color(0xFF2F241C), Color(0xFF3A3029), Color(0xFF352B24)]),
    'rigby': ('Rigby', Color(0xFFC89A5E), [Color(0xFF150F09), Color(0xFF1D1712), Color(0xFF231D18), Color(0xFF2A251F), Color(0xFF36312B), Color(0xFF312C27)]),
    'steven': ('Steven', Color(0xFFFFD447), [Color(0xFF1E080D), Color(0xFF261115), Color(0xFF2C171C), Color(0xFF321E23), Color(0xFF3E2B2F), Color(0xFF39262A)]),
    'perla': ('Perla', Color(0xFF5EE6D8), [Color(0xFF061716), Color(0xFF0F1F1E), Color(0xFF152524), Color(0xFF1C2C2B), Color(0xFF293737), Color(0xFF243332)]),
    'lapislazuli': ('Lapislázuli', Color(0xFF3D7BFF), [Color(0xFF060E22), Color(0xFF0F162A), Color(0xFF151C2F), Color(0xFF1C2436), Color(0xFF293041), Color(0xFF242B3D)]),
    'jaspe': ('Jaspe', Color(0xFFFF8A2B), [Color(0xFF1C0D05), Color(0xFF24150E), Color(0xFF2A1C14), Color(0xFF30231C), Color(0xFF3C2F28), Color(0xFF372A23)]),
    'garnet': ('Garnet', Color(0xFFFF3D8B), [Color(0xFF1C0510), Color(0xFF240E18), Color(0xFF2A141E), Color(0xFF301C26), Color(0xFF3C2831), Color(0xFF37232D)]),
    'peridot': ('Peridot', Color(0xFFB6F03C), [Color(0xFF0A1606), Color(0xFF131E0F), Color(0xFF192415), Color(0xFF202B1C), Color(0xFF2C3729), Color(0xFF273224)]),
    'amatista': ('Amatista', Color(0xFFC08CFF), [Color(0xFF150A1E), Color(0xFF1D1326), Color(0xFF23192C), Color(0xFF2A2032), Color(0xFF362C3E), Color(0xFF312739)]),
    'leon': ('León', Color(0xFFFF8FC4), [Color(0xFF1E0A14), Color(0xFF26131C), Color(0xFF2C1922), Color(0xFF322029), Color(0xFF3E2C35), Color(0xFF392730)]),
    'richard': ('Richard', Color(0xFFFF7FB6), [Color(0xFF1E0912), Color(0xFF26121A), Color(0xFF2C1820), Color(0xFF321F27), Color(0xFF3E2B33), Color(0xFF39272E)]),
    'mordecai': ('Mordecai', Color(0xFFA9C8FF), [Color(0xFF1A3160), Color(0xFF223865), Color(0xFF273E69), Color(0xFF2E446E), Color(0xFF3A4E76), Color(0xFF354A73)]),
    'gumball': ('Gumball', Color(0xFF4FC8FF), [Color(0xFF061424), Color(0xFF0F1C2C), Color(0xFF152231), Color(0xFF1C2938), Color(0xFF293543), Color(0xFF24303E)]),
    'darwin': ('Darwin', Color(0xFFFF8C1A), [Color(0xFF1C0D04), Color(0xFF24150D), Color(0xFF2A1C13), Color(0xFF30231B), Color(0xFF3C2F27), Color(0xFF372A22)]),
    'gato_negro': ('Gato negro', Color(0xFF7BD88F), [Color(0xFF0F0F12), Color(0xFF17171A), Color(0xFF1D1D20), Color(0xFF252527), Color(0xFF313133), Color(0xFF2C2C2E)]),
  };

  /// El mosaico del fondo elegido (null si no es un fondo con personaje).
  static String? patron;

  static String? patronDe(String fondo) => temas.containsKey(fondo) ? 'assets/fondos/$fondo.png' : null;

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
    final tema = temas[valor];
    if (tema != null) return (tema.$1, tema.$3);
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
    // un tema exclusivo (solo con los beneficios vigentes) manda sobre el acento y el fondo elegidos
    final premium = TemasPremium.de(Premium.i.temaEfectivo);
    if (premium != null) {
      C.acento = premium.acento;
      C.acentoAlto = premium.acentoAlto;
      C.acentoTexto = premium.acentoTexto;
      // el personaje del fondo elegido se queda: solo se quita si la persona elige un fondo sin él
      patron = patronDe(fondo);
      C.fondo = premium.capas[0];
      C.panel = premium.capas[1];
      C.superficie = premium.capas[2];
      C.superficie2 = premium.capas[3];
      C.superficie3 = premium.capas[4];
      C.borde = premium.capas[5];
      return;
    }
    final a = acentoDe(acento);
    C.acento = a.$2;
    C.acentoAlto = a.$3;
    C.acentoTexto = a.$4;
    patron = patronDe(fondo);
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
