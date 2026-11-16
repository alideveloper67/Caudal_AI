import 'dart:ui' as ui;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../nucleo/fondo_app.dart';
import 'tema.dart';

/// La imagen de fondo ya compuesta: color base, la imagen tenue (con su
/// desenfoque), una viñeta que oscurece los bordes y un velo que baja la imagen
/// hacia el pie, para que el texto siempre se lea y no se vea "pegada".
class FondoImagen extends StatelessWidget {
  const FondoImagen({super.key, required this.url, required this.visible, required this.desenfoque, this.ancho = 1080});

  final String url;

  /// Porcentaje de imagen que se ve (5 a 60).
  final int visible;

  /// Cuánto se desenfoca (0 a 20).
  final int desenfoque;

  /// Ancho aproximado en píxeles reales (para no decodificar de más).
  final int ancho;

  @override
  Widget build(BuildContext context) {
    final sigma = desenfoque * 0.9;
    final imagen = CachedNetworkImage(
      imageUrl: url,
      cacheKey: url,
      fit: BoxFit.cover,
      alignment: Alignment.center,
      memCacheWidth: ancho,
      fadeInDuration: const Duration(milliseconds: 420),
      placeholder: (_, _) => const SizedBox.shrink(),
      errorWidget: (_, _, _) => const SizedBox.shrink(),
    );
    return RepaintBoundary(
      child: Stack(fit: StackFit.expand, children: [
        ColoredBox(color: C.fondo),
        Opacity(
          opacity: (visible / 100).clamp(0.0, 1.0),
          child: sigma <= 0
              ? imagen
              : ImageFiltered(
                  imageFilter: ui.ImageFilter.blur(sigmaX: sigma, sigmaY: sigma, tileMode: TileMode.decal),
                  child: imagen,
                ),
        ),
        // un destello del color de acento arriba: une la imagen con el resto de la app
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: const Alignment(0.75, -1.05),
              radius: 1.1,
              colors: [C.acento.withValues(alpha: 0.10), Colors.transparent],
            ),
          ),
        ),
        // viñeta: los bordes se oscurecen, el centro respira
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: const Alignment(0, -0.15),
              radius: 1.2,
              colors: [Colors.transparent, C.fondo.withValues(alpha: 0.62)],
              stops: const [0.5, 1],
            ),
          ),
        ),
        // velo vertical: más suave arriba, más oscuro hacia el pie (reproductor y menú)
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [C.fondo.withValues(alpha: 0.12), C.fondo.withValues(alpha: 0.0), C.fondo.withValues(alpha: 0.58)],
              stops: const [0, 0.45, 1],
            ),
          ),
        ),
      ]),
    );
  }
}

/// El fondo de toda la app: se pone detrás de las pantallas y aparece y
/// desaparece con un fundido suave.
class CapaFondoApp extends StatelessWidget {
  const CapaFondoApp({super.key});

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: FondoApp.i,
        builder: (context, _) {
          final f = FondoApp.i;
          final dpr = MediaQuery.devicePixelRatioOf(context);
          final ancho = (MediaQuery.sizeOf(context).width * dpr).round().clamp(480, 1600);
          return Positioned.fill(
            child: IgnorePointer(
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 450),
                switchInCurve: Curves.easeOut,
                child: f.activo
                    ? FondoImagen(key: ValueKey(f.url), url: f.url, visible: f.visible, desenfoque: f.desenfoque, ancho: ancho)
                    : const SizedBox.shrink(key: ValueKey('sin_fondo')),
              ),
            ),
          );
        },
      );
}
