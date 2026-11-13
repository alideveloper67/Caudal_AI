import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import 'plataforma.dart';

/// La paleta de Caudal (la misma que el escritorio): oscuro profundo y un solo
/// acento, el cian del icono.
class C {
  static const fondo = Color(0xFF06070A);
  static const panel = Color(0xFF101217);
  static const superficie = Color(0xFF14171D);
  static const superficie2 = Color(0xFF1B1F27);
  static const superficie3 = Color(0xFF252A35);
  static const borde = Color(0xFF222731);
  static const texto = Color(0xFFF3F5F9);
  static const texto2 = Color(0xFFA9B1C0);
  static const texto3 = Color(0xFF6F788A);
  static const acento = Color(0xFF22D3EE);
  static const acentoAlto = Color(0xFF67E8F9);
  static const acentoTexto = Color(0xFF03222B);
  static const violeta = Color(0xFF7C5CFF);
  static const error = Color(0xFFF2555A);
  static const exito = Color(0xFF2BD576);
}

ThemeData temaCaudal() {
  const esquema = ColorScheme.dark(
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
    scaffoldBackgroundColor: C.fondo,
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
    bottomSheetTheme: const BottomSheetThemeData(
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
          borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: C.acento, width: 2)),
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
    dividerTheme: const DividerThemeData(color: C.borde, thickness: 1, space: 1),
  );
}

const estiloTituloPagina = TextStyle(fontSize: 28, fontWeight: FontWeight.w900, letterSpacing: -0.5);
const estiloTituloSeccion = TextStyle(fontSize: 21, fontWeight: FontWeight.w800, letterSpacing: -0.3);
const estiloSecundario = TextStyle(fontSize: 13, color: C.texto2);
