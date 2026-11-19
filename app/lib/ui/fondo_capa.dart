import 'dart:math' as math;
import 'dart:math' show min;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;

import '../nucleo/fondo_app.dart';
import '../nucleo/cumpleanos.dart';
import 'cumpleanos.dart';
import 'horneado.dart';
import '../nucleo/ritmo.dart';
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
    final opacidad = (visible / 100).clamp(0.0, 1.0);
    // sin desenfoque: la imagen con su opacidad en la pintura (sin capa aparte);
    // con desenfoque: horneada una vez (desenfoque y opacidad) en una copia
    // reducida, en vez de un ImageFiltered de pantalla completa en cada fotograma
    final Widget imagen = sigma <= 0
        ? CachedNetworkImage(
            imageUrl: url,
            cacheKey: url,
            fit: BoxFit.cover,
            alignment: Alignment.center,
            memCacheWidth: ancho,
            fadeInDuration: const Duration(milliseconds: 420),
            color: Color.fromRGBO(255, 255, 255, opacidad),
            colorBlendMode: BlendMode.dstIn,
            placeholder: (_, _) => const SizedBox.shrink(),
            errorWidget: (_, _, _) => const SizedBox.shrink(),
          )
        : ImagenDesenfocada(
            key: ValueKey(url),
            clave: url,
            imagen: (w) => ResizeImage.resizeIfNeeded(min(w, ancho), null, CachedNetworkImageProvider(url, cacheKey: url)),
            sigma: sigma,
            opacidad: opacidad,
            modo: TileMode.decal,
            aparecer: const Duration(milliseconds: 420),
          );
    return RepaintBoundary(
      child: Stack(fit: StackFit.expand, children: [
        ColoredBox(color: C.fondo),
        imagen,
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
  const PersonajeFondo({super.key, required this.asset, this.alto = 160, this.gorro = false});
  final String asset;
  final double alto;

  /// Cumpleaños: gorrito de fiesta sobre la cabeza.
  final bool gorro;

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
          if (gorro) Positioned(top: alto * 0.02, child: GorroFiesta(ancho: alto * 0.26)),
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

/// El personaje del fondo con personaje, encima de las pantallas (sobre el mini reproductor).
///
/// - Se ARRASTRA a donde se quiera (un dedo sobre él) y se queda ahí; doble toque lo devuelve a su
///   esquina. La posición se guarda como fracción del espacio libre, así que cae bien en cualquier
///   pantalla y nunca se sale.
/// - BAILA con la música: mientras suena, rebota y se mece; en pausa se queda quieto. Con el modo
///   ligero (o «quitar animaciones» del sistema) se queda quieto siempre.
/// - No estorba: lo que no es él deja pasar los toques. Para cambiarle el tamaño, se mantiene
///   pulsado (vibra y se marca) y se pellizca o se desliza hacia arriba/abajo; se suelta tocando
///   fuera. El tamaño se recuerda.
class PersonajeEncima extends StatefulWidget {
  const PersonajeEncima({
    super.key,
    required this.alto,
    required this.alCambiar,
    this.reproductor,
    this.suena,
    this.x = -1,
    this.y = -1,
    this.alMover,
    this.baila = true,
    this.posicion,
    this.ritmo,
  });

  /// Por dónde va la canción (para que el baile caiga en los tiempos).
  final ValueListenable<Duration>? posicion;

  /// El ritmo de la canción que suena, si Caudal ya lo conoce (tempo y dónde cae el primer tiempo).
  final AnalisisRitmo? Function()? ritmo;

  /// Alto guardado del personaje.
  final double alto;

  /// Se llama al soltar con el tamaño nuevo, para recordarlo.
  final ValueChanged<double> alCambiar;

  /// Lo que avisa cuando cambia la música (el reproductor) y la pregunta de si suena ahora. Sin ellos, no baila.
  final Listenable? reproductor;
  final bool Function()? suena;

  /// Dónde está, de 0 a 1 en cada eje del espacio libre (0 = izquierda/arriba). Negativo = en su esquina de siempre.
  final double x, y;

  /// Se llama al soltarlo en un sitio nuevo (o con -1, -1 al devolverlo a su esquina).
  final void Function(double x, double y)? alMover;

  /// ¿Baila con la música?
  final bool baila;

  static const minimo = 80.0, maximo = 300.0;

  @override
  State<PersonajeEncima> createState() => _PersonajeEncimaState();
}

class _PersonajeEncimaState extends State<PersonajeEncima> with TickerProviderStateMixin {
  late double _alto = widget.alto.clamp(PersonajeEncima.minimo, PersonajeEncima.maximo);
  late double _x = widget.x, _y = widget.y;
  bool _editando = false;
  bool _arrastrando = false;
  double _alInicio = 0;

  final _llaveArea = GlobalKey();
  final _llaveDibujo = GlobalKey();

  /// El reloj del baile (solo marca los fotogramas; el paso sale de la posición de la canción).
  late final AnimationController _baile = AnimationController(vsync: this, duration: const Duration(seconds: 1));

  /// Cuánto baila (0 quieto, 1 bailando): entra y sale suave, nunca de golpe.
  late final AnimationController _fuerza = AnimationController(vsync: this, duration: const Duration(milliseconds: 350));

  // la posición de la canción, interpolada entre avisos del reproductor
  Duration _posBase = Duration.zero;
  final Stopwatch _desdePos = Stopwatch()..start();
  bool _suena = false;
  ValueListenable<TickerModeData>? _tickers;

  @override
  void initState() {
    super.initState();
    widget.reproductor?.addListener(_alCambiarMusica);
    widget.posicion?.addListener(_alAvanzar);
    _alAvanzar();
  }

  void _alAvanzar() {
    _posBase = widget.posicion?.value ?? _posBase;
    _desdePos
      ..reset()
      ..start();
  }

  /// Segundo de la canción ahora mismo (sin posición, un reloj propio).
  double get _segundo => (_posBase + _desdePos.elapsed).inMicroseconds / 1e6;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // con la pantalla tapada no baila (no gasta nada)
    final n = TickerMode.getValuesNotifier(context);
    if (!identical(n, _tickers)) {
      _tickers?.removeListener(_alCambiarMusica);
      _tickers = n..addListener(_alCambiarMusica);
    }
    _alCambiarMusica();
  }

  @override
  void didUpdateWidget(covariant PersonajeEncima old) {
    super.didUpdateWidget(old);
    if (!_editando && old.alto != widget.alto) {
      _alto = widget.alto.clamp(PersonajeEncima.minimo, PersonajeEncima.maximo);
    }
    if (!_arrastrando && (old.x != widget.x || old.y != widget.y)) {
      _x = widget.x;
      _y = widget.y;
    }
    if (!identical(old.posicion, widget.posicion)) {
      old.posicion?.removeListener(_alAvanzar);
      widget.posicion?.addListener(_alAvanzar);
    }
    if (!identical(old.reproductor, widget.reproductor)) {
      old.reproductor?.removeListener(_alCambiarMusica);
      widget.reproductor?.addListener(_alCambiarMusica);
    }
    _alCambiarMusica();
  }

  @override
  void dispose() {
    widget.reproductor?.removeListener(_alCambiarMusica);
    _tickers?.removeListener(_alCambiarMusica);
    widget.posicion?.removeListener(_alAvanzar);
    _baile.dispose();
    _fuerza.dispose();
    super.dispose();
  }

  void _alCambiarMusica() {
    final r = widget.reproductor;
    final suena = widget.baila &&
        r != null &&
        (widget.suena?.call() ?? false) &&
        (_tickers?.value.enabled ?? true) &&
        !(mounted && MediaQuery.maybeDisableAnimationsOf(context) == true);
    if (suena == _suena) return;
    _suena = suena;
    if (suena) {
      if (!_baile.isAnimating) _baile.repeat();
      _fuerza.forward();
    } else if (_baile.isAnimating) {
      // se va calmando hasta quedarse quieto, sin cortarse de golpe
      _fuerza.reverse().whenComplete(() {
        if (!_suena && mounted) _baile.stop();
      });
    }
  }

  void _terminar() {
    setState(() => _editando = false);
    widget.alCambiar(_alto);
  }

  // ---------------------------------------------------------------- mover

  /// Tamaño del espacio libre y del dibujo, y dónde está ahora el dibujo dentro de ese espacio.
  ({Size area, Size dibujo, Offset sitio})? _medir() {
    final a = _llaveArea.currentContext?.findRenderObject();
    final d = _llaveDibujo.currentContext?.findRenderObject();
    if (a is! RenderBox || d is! RenderBox || !a.hasSize || !d.hasSize) return null;
    return (area: a.size, dibujo: d.size, sitio: a.globalToLocal(d.localToGlobal(Offset.zero)));
  }

  void _empezarArrastre(DragStartDetails _) {
    final m = _medir();
    if (m == null) return;
    final libreX = m.area.width - m.dibujo.width, libreY = m.area.height - m.dibujo.height;
    setState(() {
      _arrastrando = true;
      // desde su esquina de siempre: sigue justo donde está, sin saltos
      if (_x < 0 || _y < 0) {
        _x = libreX <= 0 ? 0 : (m.sitio.dx / libreX).clamp(0.0, 1.0);
        _y = libreY <= 0 ? 0 : (m.sitio.dy / libreY).clamp(0.0, 1.0);
      }
    });
    HapticFeedback.selectionClick();
  }

  void _arrastrar(DragUpdateDetails d) {
    final m = _medir();
    if (m == null) return;
    final libreX = m.area.width - m.dibujo.width, libreY = m.area.height - m.dibujo.height;
    setState(() {
      if (libreX > 0) _x = (_x + d.delta.dx / libreX).clamp(0.0, 1.0);
      if (libreY > 0) _y = (_y + d.delta.dy / libreY).clamp(0.0, 1.0);
    });
  }

  void _soltar([DragEndDetails? _]) {
    if (!_arrastrando) return;
    setState(() => _arrastrando = false);
    widget.alMover?.call(_x, _y);
  }

  void _alEsquina() {
    HapticFeedback.lightImpact();
    setState(() {
      _x = -1;
      _y = -1;
    });
    widget.alMover?.call(-1, -1);
  }

  // ---------------------------------------------------------------- dibujo

  /// Un vaivén suave, como el de las mascotas del reproductor: sube un poquito entre tiempo y
  /// tiempo, baja justo en cada tiempo y se mece de lado cada dos. Si Caudal conoce el ritmo de la
  /// canción, los pasos caen en sus tiempos; si no, va a un paso tranquilo. Nada brusco.
  Widget _bailando(Widget hijo) => AnimatedBuilder(
        animation: Listenable.merge([_baile, _fuerza]),
        child: hijo,
        builder: (_, hijo) {
          final f = Curves.easeInOut.transform(_fuerza.value);
          if (f == 0) return hijo!;
          final r = widget.ritmo?.call();
          final conRitmo = r != null && r.valido;
          var bpm = conRitmo ? r.bpm : 96.0;
          // los tempos rápidos se bailan a la mitad: más bonito y menos movimiento
          while (bpm > 130) {
            bpm /= 2;
          }
          final tiempos = (_segundo - (conRitmo ? r.primerTiempo : 0)) * bpm / 60;
          final enTiempo = tiempos - tiempos.floorToDouble(); // 0 justo en cada tiempo
          final sube = math.sin(math.pi * enTiempo); // abajo en el tiempo, arriba entre medio
          final mece = math.sin(math.pi * tiempos); // de un lado a otro cada dos tiempos
          return Transform(
            alignment: Alignment.bottomCenter,
            transform: Matrix4.translationValues(mece * _alto * 0.012 * f, -sube * _alto * 0.028 * f, 0) *
                Matrix4.rotationZ(mece * 0.03 * f) *
                Matrix4.diagonal3Values(1 - sube * 0.008 * f, 1 + sube * 0.012 * f, 1),
            child: hijo,
          );
        },
      );

  @override
  Widget build(BuildContext context) {
    final personaje = Aspecto.patron;
    if (personaje == null) return const SizedBox.shrink();
    final moviendo = _arrastrando;
    final dibujo = AnimatedScale(
      scale: moviendo ? 1.08 : 1,
      duration: const Duration(milliseconds: 140),
      curve: Curves.easeOut,
      child: _bailando(
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 450),
          switchInCurve: Curves.easeOutBack,
          transitionBuilder: (hijo, a) =>
              FadeTransition(opacity: a, child: ScaleTransition(scale: Tween(begin: 0.85, end: 1.0).animate(a), child: hijo)),
          child: Semantics(
            key: ValueKey(personaje),
            label: 'Personaje del fondo. Arrástralo para moverlo; toca dos veces para devolverlo a su esquina.',
            child: GestureDetector(
              // opaco: lo que toca el personaje es del personaje, y el resto de la pantalla sigue normal
              behavior: HitTestBehavior.opaque,
              onPanStart: _empezarArrastre,
              onPanUpdate: _arrastrar,
              onPanEnd: _soltar,
              onPanCancel: _soltar,
              onDoubleTap: _alEsquina,
              onLongPress: () {
                HapticFeedback.mediumImpact();
                setState(() => _editando = true);
              },
              child: DecoratedBox(
                key: _llaveDibujo,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(
                      color: _editando || moviendo ? C.acento.withValues(alpha: 0.9) : Colors.transparent, width: 2),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(4),
                  child: ListenableBuilder(
                    listenable: Cumpleanos.i,
                    builder: (_, _) => PersonajeFondo(asset: personaje, alto: _alto, gorro: Cumpleanos.i.esMiCumple),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );

    final enSuEsquina = _x < 0 || _y < 0;
    final pad = MediaQuery.paddingOf(context);
    final Widget colocado = enSuEsquina
        // donde estaba de siempre: abajo a la derecha, sobre el mini reproductor
        ? Align(alignment: Alignment.bottomRight, child: Padding(padding: const EdgeInsets.only(right: 10, bottom: 168), child: dibujo))
        : Align(alignment: Alignment(_x.clamp(0.0, 1.0) * 2 - 1, _y.clamp(0.0, 1.0) * 2 - 1), child: dibujo);

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
      // el espacio por el que puede andar: dentro de los bordes seguros, para que nunca quede tapado por la barra de estado o la de gestos
      Padding(
        padding: EdgeInsets.fromLTRB(pad.left, pad.top, pad.right, pad.bottom),
        child: SizedBox.expand(key: _llaveArea, child: colocado),
      ),
    ]);
  }
}
