// Desenfoques "horneados": la imagen se desenfoca UNA vez, a poca resolucion,
// y despues se pinta como una imagen cualquiera.
//
// Un ImageFiltered de pantalla completa se recalcula en la GPU en cada
// fotograma que algo de la pantalla cambia (Impeller no guarda capas en
// cache), aunque la imagen no cambie. Un desenfoque fuerte ademas borra todo
// el detalle fino: hacerlo sobre una copia pequena y estirarla despues con
// filtrado suave se ve igual y cuesta una fraccion.

import 'dart:async';
import 'dart:math';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

/// Espera a que [proveedor] tenga la imagen decodificada. El que la recibe es
/// su dueno y debe llamar a `dispose()` cuando ya no la use.
Future<ui.Image> resolverImagen(ImageProvider proveedor, {ImageConfiguration config = ImageConfiguration.empty}) {
  final listo = Completer<ui.Image>();
  final flujo = proveedor.resolve(config);
  late final ImageStreamListener oyente;
  oyente = ImageStreamListener((info, _) {
    flujo.removeListener(oyente);
    if (listo.isCompleted) {
      info.dispose();
    } else {
      listo.complete(info.image);
    }
  }, onError: (e, pila) {
    flujo.removeListener(oyente);
    if (!listo.isCompleted) listo.completeError(e, pila);
  });
  flujo.addListener(oyente);
  return listo.future;
}

/// Cuanto se reduce la copia segun el desenfoque (en pixeles reales): la
/// separacion entre muestras queda muy por debajo del desenfoque, asi que al
/// estirarla no se nota ningun pixel. Sin desenfoque no se reduce.
double escalaHorneado(double sigmaFisico) =>
    sigmaFisico <= 0 ? 1.0 : (3 / sigmaFisico).clamp(1 / 24, 1.0);

/// Pinta [fuente] (como BoxFit.cover) en una imagen de [ancho]x[alto] con un
/// desenfoque de [sigma] pixeles de esa imagen y la opacidad dada.
Future<ui.Image> hornearImagen(
  ui.Image fuente, {
  required int ancho,
  required int alto,
  required double sigma,
  double opacidad = 1,
  TileMode modo = TileMode.clamp,
}) async {
  final grabadora = ui.PictureRecorder();
  final lienzo = Canvas(grabadora);
  final rect = Offset.zero & Size(ancho.toDouble(), alto.toDouble());
  final capa = Paint()..color = Color.fromRGBO(0, 0, 0, opacidad.clamp(0.0, 1.0));
  if (sigma > 0) capa.imageFilter = ui.ImageFilter.blur(sigmaX: sigma, sigmaY: sigma, tileMode: modo);
  lienzo.saveLayer(rect, capa);
  paintImage(canvas: lienzo, rect: rect, image: fuente, fit: BoxFit.cover, filterQuality: FilterQuality.medium);
  lienzo.restore();
  final dibujo = grabadora.endRecording();
  try {
    return await dibujo.toImage(ancho, alto);
  } finally {
    dibujo.dispose();
  }
}

/// Una imagen a todo el espacio que le dan, desenfocada [sigma] (en puntos,
/// como `ImageFilter.blur` en un `ImageFiltered`) y con [opacidad], horneada una
/// vez por tamano y ajustes. Mientras se prepara no pinta nada.
class ImagenDesenfocada extends StatefulWidget {
  const ImagenDesenfocada({
    super.key,
    required this.clave,
    required this.imagen,
    required this.sigma,
    this.opacidad = 1,
    this.modo = TileMode.clamp,
    this.alFallar,
    this.aparecer = Duration.zero,
  });

  /// Identifica la imagen (la URL): si cambia, se vuelve a leer.
  final String clave;

  /// La imagen a usar, para un ancho de decodificacion sugerido (pixeles).
  final ImageProvider Function(int ancho) imagen;
  final double sigma;
  final double opacidad;
  final TileMode modo;

  /// Lo que se ve si la imagen no se puede leer.
  final Widget? alFallar;

  /// Fundido de entrada la primera vez que aparece.
  final Duration aparecer;

  @override
  State<ImagenDesenfocada> createState() => _ImagenDesenfocadaState();
}

class _ImagenDesenfocadaState extends State<ImagenDesenfocada> {
  ui.Image? _hecha;
  ui.Image? _fuente;
  String? _claveFuente;
  int _anchoFuente = 0;
  String _pedido = '';
  bool _fallo = false;
  int _turno = 0;

  @override
  void didUpdateWidget(covariant ImagenDesenfocada old) {
    super.didUpdateWidget(old);
    if (old.clave != widget.clave) _fallo = false;
  }

  @override
  void dispose() {
    _turno++;
    _hecha?.dispose();
    _fuente?.dispose();
    super.dispose();
  }

  Future<void> _hornear(Size tam, double dpr) async {
    final sigmaFis = widget.sigma * dpr;
    final f = escalaHorneado(sigmaFis);
    final ancho = max(1, (tam.width * dpr * f).round());
    final alto = max(1, (tam.height * dpr * f).round());
    final pedido = '${widget.clave}|$ancho|$alto|${widget.sigma}|${widget.opacidad}|${widget.modo}';
    if (pedido == _pedido) return;
    _pedido = pedido;
    final turno = ++_turno;
    try {
      // la fuente: con desenfoque basta el doble de la copia (se reduce con suavidad)
      final anchoFuente = sigmaFis > 0 ? ancho * 2 : ancho;
      if (_fuente == null || _claveFuente != widget.clave || _anchoFuente < anchoFuente) {
        final nueva = await resolverImagen(widget.imagen(anchoFuente));
        if (turno != _turno || !mounted) {
          nueva.dispose();
          return;
        }
        _fuente?.dispose();
        _fuente = nueva;
        _claveFuente = widget.clave;
        _anchoFuente = anchoFuente;
      }
      final hecha = await hornearImagen(_fuente!,
          ancho: ancho, alto: alto, sigma: sigmaFis * f, opacidad: widget.opacidad, modo: widget.modo);
      if (turno != _turno || !mounted) {
        hecha.dispose();
        return;
      }
      setState(() {
        _hecha?.dispose();
        _hecha = hecha;
        _fallo = false;
      });
    } catch (_) {
      if (turno != _turno || !mounted) return;
      _pedido = ''; // que se pueda reintentar si cambia algo
      setState(() => _fallo = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dpr = MediaQuery.maybeDevicePixelRatioOf(context) ?? 1.0;
    return LayoutBuilder(builder: (context, lim) {
      final tam = lim.biggest;
      if (tam.isFinite && !tam.isEmpty) unawaited(_hornear(tam, dpr));
      final hecha = _hecha;
      if (hecha == null) {
        return _fallo ? (widget.alFallar ?? const SizedBox.expand()) : const SizedBox.expand();
      }
      final imagen = RawImage(
        image: hecha,
        width: tam.width,
        height: tam.height,
        fit: BoxFit.fill,
        filterQuality: FilterQuality.medium,
      );
      if (widget.aparecer == Duration.zero) return imagen;
      return TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: 1),
        duration: widget.aparecer,
        child: imagen,
        builder: (_, a, hijo) => a >= 1 ? hijo! : Opacity(opacity: a, child: hijo),
      );
    });
  }
}
