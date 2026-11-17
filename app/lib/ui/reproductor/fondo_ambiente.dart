// Modo ambiente: la portada, muy desenfocada, se mueve despacio detras del
// reproductor (como el modo ambiente de YouTube o el Canvas de Spotify).
//
// Pensado para no gastar GPU:
//  - la imagen se decodifica diminuta (64 px de ancho): el desenfoque la
//    estira sin que se note y apenas ocupa memoria;
//  - el desenfoque se hornea una vez por portada en una imagen pequena
//    (ver ImagenDesenfocada): lo que se anima es la transformacion de esa
//    capa, no su contenido, y la GPU no recalcula ningun desenfoque;
//  - con la musica en pausa (o con "reducir movimiento") se queda quieto.

import 'dart:io';
import 'dart:math';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../horneado.dart';
import '../tema.dart';

class FondoAmbiente extends StatefulWidget {
  const FondoAmbiente({super.key, required this.url, required this.color, this.enMovimiento = true});

  final String url;

  /// Color dominante de la portada: tine el velo y sirve mientras no hay imagen.
  final Color color;

  /// Si la portada flota. Se apaga en pausa y con el video.
  final bool enMovimiento;

  @override
  State<FondoAmbiente> createState() => _FondoAmbienteState();
}

class _FondoAmbienteState extends State<FondoAmbiente> with SingleTickerProviderStateMixin {
  // una vuelta completa tarda casi medio minuto: se nota que vive, no que se mueve
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(seconds: 26));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sincronizar();
  }

  @override
  void didUpdateWidget(covariant FondoAmbiente old) {
    super.didUpdateWidget(old);
    if (old.enMovimiento != widget.enMovimiento) _sincronizar();
  }

  void _sincronizar() {
    final quieto = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    if (widget.enMovimiento && !quieto) {
      if (!_c.isAnimating) _c.repeat();
    } else {
      _c.stop();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  Widget _imagen() {
    final url = widget.url;
    if (url.isEmpty) return SizedBox.expand(key: const ValueKey(''), child: ColoredBox(color: widget.color));
    final ImageProvider base = url.startsWith('http') ? CachedNetworkImageProvider(url) : FileImage(File(url));
    // desenfocada una sola vez, en una copia diminuta (ver [ImagenDesenfocada]):
    // el mismo sigma 38 de antes, sin recalcularlo en cada fotograma
    return ImagenDesenfocada(
      key: ValueKey(url),
      clave: url,
      imagen: (_) => ResizeImage(base, width: 64, policy: ResizeImagePolicy.fit),
      sigma: 38,
      modo: TileMode.clamp,
      alFallar: ColoredBox(color: widget.color),
    );
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.color;
    // la capa desenfocada: se hornea una vez por portada y luego solo se mueve
    final capa = RepaintBoundary(
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 700),
        switchInCurve: Curves.easeOut,
        layoutBuilder: (actual, previos) =>
            Stack(fit: StackFit.expand, children: [...previos, ?actual]),
        child: _imagen(),
      ),
    );
    return RepaintBoundary(
      child: ClipRect(
        child: ColoredBox(
          color: C.fondo,
          child: Stack(fit: StackFit.expand, children: [
            AnimatedBuilder(
              animation: _c,
              child: capa,
              builder: (_, hijo) {
                final t = _c.value * 2 * pi;
                // un ocho lento: deriva, giro leve y respiracion de la escala
                final m = Matrix4.identity()
                  ..translateByDouble(sin(t) * 26, sin(2 * t) * 18, 0, 1)
                  ..rotateZ(sin(t) * 0.07)
                  ..scaleByDouble(1.45 + sin(t + 1.3) * 0.08, 1.45 + sin(t + 1.3) * 0.08, 1, 1);
                return Transform(transform: m, alignment: Alignment.center, child: hijo);
              },
            ),
            // el velo: deja leer el texto y tine con el color de la portada
            AnimatedContainer(
              duration: const Duration(milliseconds: 600),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Color.lerp(color, C.fondo, 0.35)!.withValues(alpha: 0.38),
                    C.fondo.withValues(alpha: 0.52),
                    C.fondo.withValues(alpha: 0.86),
                    C.fondo.withValues(alpha: 0.96),
                  ],
                  stops: const [0, 0.42, 0.78, 1],
                ),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}
