// Micro-animaciones del reproductor y del mini reproductor: el corazon que
// rebota, el play que se transforma en pausa, el vuelo de la portada y el
// corazon que aparece al dar doble toque. Todas son widgets pequenos con su
// propio controlador: nada obliga a reconstruir la pantalla entera.

import 'dart:io';
import 'dart:ui' show lerpDouble;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../comunes.dart';
import '../tema.dart';

/// Etiqueta del Hero que une la portada del mini con la del reproductor.
const etiquetaPortada = 'portada-actual';

/// Lado de la portada grande del reproductor para un ancho de pantalla.
double ladoPortadaGrande(double ancho) => ancho - 44;

/// El vuelo de la portada entre el mini y el reproductor grande: las esquinas
/// y la sombra cambian a la vez que el tamano, y se pinta ya con la imagen
/// grande (la que el mini deja decodificada de antemano) para que no parpadee.
HeroFlightShuttleBuilder vueloPortada(String url, double ladoGrande) =>
    (_, animacion, _, _, _) => AnimatedBuilder(
          animation: animacion,
          builder: (_, _) {
            final t = Curves.easeOut.transform(animacion.value.clamp(0.0, 1.0));
            final radio = lerpDouble(5, 8, t)!;
            return DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(radio),
                boxShadow: [
                  BoxShadow(color: Color.fromRGBO(0, 0, 0, 0.4 * t), blurRadius: 26 * t, offset: Offset(0, 12 * t)),
                ],
              ),
              child: Portada(url: url, lado: ladoGrande, radio: radio),
            );
          },
        );

/// Deja decodificada la portada grande (la misma clave de cache que usa
/// [Portada]) para que al abrir el reproductor el vuelo no muestre un hueco.
void precargarPortadaGrande(BuildContext context, String url, double lado) {
  if (url.isEmpty) return;
  final ancho = (lado * MediaQuery.devicePixelRatioOf(context)).round();
  final ImageProvider base = url.startsWith('http') ? CachedNetworkImageProvider(url) : FileImage(File(url));
  precacheImage(ResizeImage.resizeIfNeeded(ancho, null, base), context, onError: (_, _) {});
}

/// Boton de me gusta con rebote: al marcar crece y vuelve con un muelle; al
/// desmarcar se encoge un instante.
class CorazonAnimado extends StatefulWidget {
  const CorazonAnimado({super.key, required this.gusta, required this.alPulsar, this.tamano = 24});

  final bool gusta;
  final VoidCallback alPulsar;
  final double tamano;

  @override
  State<CorazonAnimado> createState() => _CorazonAnimadoState();
}

class _CorazonAnimadoState extends State<CorazonAnimado> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 520));
  Animation<double> _escala = const AlwaysStoppedAnimation(1);

  static final _alMarcar = TweenSequence<double>([
    TweenSequenceItem(tween: Tween(begin: 1.0, end: 1.38).chain(CurveTween(curve: Curves.easeOutCubic)), weight: 30),
    TweenSequenceItem(tween: Tween(begin: 1.38, end: 0.9).chain(CurveTween(curve: Curves.easeInOut)), weight: 30),
    TweenSequenceItem(tween: Tween(begin: 0.9, end: 1.0).chain(CurveTween(curve: Curves.easeOutBack)), weight: 40),
  ]);
  static final _alQuitar = TweenSequence<double>([
    TweenSequenceItem(tween: Tween(begin: 1.0, end: 0.78).chain(CurveTween(curve: Curves.easeOut)), weight: 40),
    TweenSequenceItem(tween: Tween(begin: 0.78, end: 1.0).chain(CurveTween(curve: Curves.easeOutBack)), weight: 60),
  ]);

  @override
  void didUpdateWidget(covariant CorazonAnimado old) {
    super.didUpdateWidget(old);
    if (old.gusta == widget.gusta) return;
    _escala = (widget.gusta ? _alMarcar : _alQuitar).animate(_c);
    _c.forward(from: 0);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => IconButton(
        tooltip: widget.gusta ? 'Quitar de Tus me gusta' : 'Añadir a Tus me gusta',
        onPressed: widget.alPulsar,
        icon: ScaleTransition(
          scale: _escala,
          child: Icon(widget.gusta ? Icons.favorite_rounded : Icons.favorite_border_rounded,
              color: widget.gusta ? C.acento : C.texto, size: widget.tamano),
        ),
      );
}

/// El icono de play que se transforma en pausa (y al reves).
class IconoPlayPausa extends StatefulWidget {
  const IconoPlayPausa({super.key, required this.sonando, this.tamano = 30, this.color = C.texto});

  final bool sonando;
  final double tamano;
  final Color color;

  @override
  State<IconoPlayPausa> createState() => _IconoPlayPausaState();
}

class _IconoPlayPausaState extends State<IconoPlayPausa> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 260), value: widget.sonando ? 1 : 0);
  late final Animation<double> _curva = _c.drive(CurveTween(curve: Curves.easeInOutCubic));

  @override
  void didUpdateWidget(covariant IconoPlayPausa old) {
    super.didUpdateWidget(old);
    if (old.sonando != widget.sonando) {
      widget.sonando ? _c.forward() : _c.reverse();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedIcon(
        icon: AnimatedIcons.play_pause,
        progress: _curva,
        size: widget.tamano,
        color: widget.color,
        semanticLabel: widget.sonando ? 'Pausar' : 'Reproducir',
      );
}

/// Encoge un poco lo que envuelve mientras el dedo lo aprieta.
class Hundible extends StatefulWidget {
  const Hundible({super.key, required this.child, this.escala = 0.92});

  final Widget child;
  final double escala;

  @override
  State<Hundible> createState() => _HundibleState();
}

class _HundibleState extends State<Hundible> {
  bool _abajo = false;

  void _poner(bool v) {
    if (_abajo != v) setState(() => _abajo = v);
  }

  @override
  Widget build(BuildContext context) => Listener(
        onPointerDown: (_) => _poner(true),
        onPointerUp: (_) => _poner(false),
        onPointerCancel: (_) => _poner(false),
        child: AnimatedScale(
          scale: _abajo ? widget.escala : 1,
          duration: Duration(milliseconds: _abajo ? 90 : 260),
          curve: _abajo ? Curves.easeOut : Curves.easeOutBack,
          child: widget.child,
        ),
      );
}

/// El corazon grande que aparece sobre la portada al dar doble toque.
/// Se dispara con [CorazonEmergenteState.lanzar].
class CorazonEmergente extends StatefulWidget {
  const CorazonEmergente({super.key, this.tamano = 110});
  final double tamano;

  @override
  State<CorazonEmergente> createState() => CorazonEmergenteState();
}

class CorazonEmergenteState extends State<CorazonEmergente> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 900));

  static final _escala = TweenSequence<double>([
    TweenSequenceItem(tween: Tween(begin: 0.2, end: 1.18).chain(CurveTween(curve: Curves.easeOutCubic)), weight: 26),
    TweenSequenceItem(tween: Tween(begin: 1.18, end: 0.96).chain(CurveTween(curve: Curves.easeInOut)), weight: 14),
    TweenSequenceItem(tween: Tween(begin: 0.96, end: 1.0), weight: 34),
    TweenSequenceItem(tween: Tween(begin: 1.0, end: 1.35).chain(CurveTween(curve: Curves.easeIn)), weight: 26),
  ]);
  static final _opacidad = TweenSequence<double>([
    TweenSequenceItem(tween: Tween(begin: 0.0, end: 1.0), weight: 16),
    TweenSequenceItem(tween: ConstantTween(1.0), weight: 58),
    TweenSequenceItem(tween: Tween(begin: 1.0, end: 0.0), weight: 26),
  ]);

  void lanzar() => _c.forward(from: 0);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: AnimatedBuilder(
          animation: _c,
          builder: (_, hijo) {
            final v = _c.value;
            if (v == 0 || v == 1) return const SizedBox.shrink();
            return Opacity(
              opacity: _opacidad.transform(v),
              child: Transform.scale(scale: _escala.transform(v), child: hijo),
            );
          },
          child: Icon(Icons.favorite_rounded, size: widget.tamano, color: Colors.white,
              shadows: const [Shadow(color: Color(0x88000000), blurRadius: 24, offset: Offset(0, 6))]),
        ),
      );
}

/// Transicion de [AnimatedSwitcher] que desliza lo nuevo desde el lado del
/// gesto ([direccion] 1 = siguiente, entra por la derecha; -1 = anterior) y
/// saca lo viejo por el otro lado.
AnimatedSwitcherTransitionBuilder deslizarEn(int direccion, Key? claveActual, {double distancia = 1.1}) =>
    (hijo, animacion) {
      final entra = hijo.key == claveActual;
      // drive y no CurvedAnimation: esto se llama en cada reconstruccion y
      // CurvedAnimation dejaria un oyente colgado en el controlador cada vez
      final curva = animacion.drive(CurveTween(curve: Curves.easeOutCubic));
      final desplazamiento = Tween<Offset>(
        begin: Offset((entra ? direccion : -direccion) * distancia, 0),
        end: Offset.zero,
      ).animate(curva);
      return SlideTransition(position: desplazamiento, child: FadeTransition(opacity: animacion, child: hijo));
    };

/// Para [AnimatedSwitcher]: apila lo que entra y lo que sale sin recortar.
Widget apilar(Widget? actual, List<Widget> previos) =>
    Stack(alignment: Alignment.center, clipBehavior: Clip.none, children: [...previos, ?actual]);
