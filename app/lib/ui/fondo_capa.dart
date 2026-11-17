import 'dart:ui' as ui;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;

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

/// El fondo de un tema con personaje cuando no hay imagen: su color con el
/// destello del acento y el velo de abajo (el personaje va aparte, en su esquina).
class FondoPatron extends StatelessWidget {
  const FondoPatron({super.key});

  @override
  Widget build(BuildContext context) => RepaintBoundary(
        child: Stack(fit: StackFit.expand, children: [
          ColoredBox(color: C.fondo),
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: const Alignment(0.75, -1.05),
                radius: 1.1,
                colors: [C.acento.withValues(alpha: 0.10), Colors.transparent],
              ),
            ),
          ),
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [C.fondo.withValues(alpha: 0.0), C.fondo.withValues(alpha: 0.0), C.fondo.withValues(alpha: 0.5)],
                stops: const [0, 0.55, 1],
              ),
            ),
          ),
        ]),
      );
}

/// El personaje del fondo, chico, a un costado (abajo a la derecha, sobre el
/// mini reproductor), con una sombra suave bajo los pies. Va encima de la
/// imagen de «Fondo de Caudal» si la hay, sin taparla.
class PersonajeFondo extends StatelessWidget {
  const PersonajeFondo({super.key, required this.asset, this.alto = 160});
  final String asset;
  final double alto;

  @override
  Widget build(BuildContext context) => Stack(alignment: Alignment.bottomCenter, clipBehavior: Clip.none, children: [
          // halo suave del color del tema detrás: se nota sobre cualquier fondo, también sobre una foto
          Positioned(
            bottom: alto * 0.05,
            child: Container(
              width: alto * 1.25,
              height: alto * 1.1,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(colors: [
                  C.acento.withValues(alpha: 0.36),
                  C.acento.withValues(alpha: 0.14),
                  Colors.transparent,
                ], stops: const [0, 0.55, 1]),
              ),
            ),
          ),
          Positioned(
            bottom: -4,
            child: Container(
              width: alto * 0.62,
              height: 14,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.all(Radius.elliptical(alto * 0.31, 7)),
                gradient: RadialGradient(colors: [Colors.black.withValues(alpha: 0.5), Colors.transparent]),
              ),
            ),
          ),
          Image.asset(asset, height: alto, filterQuality: FilterQuality.none, excludeFromSemantics: true),
        ]);
}

/// El fondo de toda la app: se pone detrás de las pantallas y aparece y
/// desaparece con un fundido suave: la imagen de «Fondo de Caudal» o el color
/// del tema. El personaje del tema va aparte, encima ([PersonajeEncima]).
class CapaFondoApp extends StatelessWidget {
  const CapaFondoApp({super.key});

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: FondoApp.i,
        builder: (context, _) {
          final f = FondoApp.i;
          final dpr = MediaQuery.devicePixelRatioOf(context);
          final ancho = (MediaQuery.sizeOf(context).width * dpr).round().clamp(480, 1600);
          final personaje = Aspecto.patron;
          return Positioned.fill(
            child: IgnorePointer(
              child: Stack(fit: StackFit.expand, children: [
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 450),
                  switchInCurve: Curves.easeOut,
                  child: f.activo
                      ? FondoImagen(key: ValueKey(f.url), url: f.url, visible: f.visible, desenfoque: f.desenfoque, ancho: ancho)
                      : personaje != null
                          ? FondoPatron(key: ValueKey('tema_$personaje'))
                          : const SizedBox.shrink(key: ValueKey('sin_fondo')),
                ),
              ]),
            ),
          );
        },
      );
}

/// El personaje del fondo con personaje, en la esquina de abajo a la derecha,
/// encima de las pantallas (sobre el mini reproductor). No estorba: los toques
/// normales pasan a lo que hay debajo. Para cambiarle el tamaño, se mantiene
/// pulsado (vibra y se marca) y se pellizca o se desliza hacia arriba/abajo;
/// se suelta tocando fuera. El tamaño se recuerda.
class PersonajeEncima extends StatefulWidget {
  const PersonajeEncima({super.key, required this.alto, required this.alCambiar});

  /// Alto guardado del personaje.
  final double alto;

  /// Se llama al soltar con el tamaño nuevo, para recordarlo.
  final ValueChanged<double> alCambiar;

  static const minimo = 80.0, maximo = 300.0;

  @override
  State<PersonajeEncima> createState() => _PersonajeEncimaState();
}

class _PersonajeEncimaState extends State<PersonajeEncima> {
  late double _alto = widget.alto.clamp(PersonajeEncima.minimo, PersonajeEncima.maximo);
  bool _editando = false;
  double _alInicio = 0;

  @override
  void didUpdateWidget(covariant PersonajeEncima old) {
    super.didUpdateWidget(old);
    if (!_editando && old.alto != widget.alto) {
      _alto = widget.alto.clamp(PersonajeEncima.minimo, PersonajeEncima.maximo);
    }
  }

  void _terminar() {
    setState(() => _editando = false);
    widget.alCambiar(_alto);
  }

  @override
  Widget build(BuildContext context) {
    final personaje = Aspecto.patron;
    if (personaje == null) return const SizedBox.shrink();
    final dibujo = Padding(
      padding: const EdgeInsets.only(right: 10, bottom: 168),
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 450),
        switchInCurve: Curves.easeOutBack,
        transitionBuilder: (hijo, a) =>
            FadeTransition(opacity: a, child: ScaleTransition(scale: Tween(begin: 0.85, end: 1.0).animate(a), child: hijo)),
        child: GestureDetector(
          key: ValueKey(personaje),
          behavior: HitTestBehavior.translucent,
          onLongPress: () {
            HapticFeedback.mediumImpact();
            setState(() => _editando = true);
          },
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: _editando ? C.acento.withValues(alpha: 0.9) : Colors.transparent, width: 2),
            ),
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: PersonajeFondo(asset: personaje, alto: _alto),
            ),
          ),
        ),
      ),
    );
    return Stack(fit: StackFit.expand, children: [
      // mientras se ajusta: una capa que recoge el pellizco/deslizado en toda la pantalla y se va al tocar fuera
      if (_editando)
        GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: _terminar,
          onScaleStart: (_) => _alInicio = _alto,
          onScaleUpdate: (d) => setState(() {
            // dos dedos: pellizco; un dedo: deslizar hacia arriba agranda, hacia abajo achica
            final nuevo = d.pointerCount > 1 ? _alInicio * d.scale : _alto - d.focalPointDelta.dy;
            _alto = nuevo.clamp(PersonajeEncima.minimo, PersonajeEncima.maximo);
          }),
          onScaleEnd: (_) => widget.alCambiar(_alto),
          child: ColoredBox(
            color: Colors.black.withValues(alpha: 0.25),
            child: Align(
              alignment: const Alignment(0, -0.2),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                decoration: BoxDecoration(color: C.panel, borderRadius: BorderRadius.circular(14)),
                child: const Text('Pellizca o desliza para cambiar su tamaño.\nToca fuera para terminar.',
                    textAlign: TextAlign.center, style: TextStyle(fontSize: 13.5, color: C.texto)),
              ),
            ),
          ),
        ),
      Align(alignment: Alignment.bottomRight, child: dibujo),
    ]);
  }
}
