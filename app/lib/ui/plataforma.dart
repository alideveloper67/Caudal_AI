// Lo que cambia entre iPhone y Android en la interfaz. Todo lo de aqui deja
// Android exactamente como estaba: solo actua cuando la app corre en iOS.
//
// Se mira defaultTargetPlatform (y no dart:io) para que las pruebas puedan
// fingir un iPhone con debugDefaultTargetPlatformOverride.

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';

import '../nucleo/plataforma.dart';

/// Manda lo que diga el nucleo (que las pruebas pueden fingir); fuera de un
/// telefono, lo que diga Flutter (las pruebas de widgets fingen el iPhone asi).
bool get esIOS =>
    Plataforma.esIOS || (!Plataforma.esAndroid && defaultTargetPlatform == TargetPlatform.iOS);

/// Vibraciones cortas al estilo del iPhone. En Android no hacen nada: alli ya
/// estaban las de siempre y no se tocan.
class Haptico {
  Haptico._();

  /// Un toque leve: me gusta, play, abrir un menu.
  static void toque() {
    if (esIOS) HapticFeedback.lightImpact();
  }

  /// El "clic" de elegir algo: cambiar de modo, de cancion, una opcion.
  static void seleccion() {
    if (esIOS) HapticFeedback.selectionClick();
  }

  /// Algo mas firme: mantener pulsado, empezar a recargar, cerrar con el dedo.
  static void firme() {
    if (esIOS) HapticFeedback.mediumImpact();
  }

  /// Salio bien (una descarga puesta en marcha, algo guardado).
  static void exito() {
    if (esIOS) HapticFeedback.successNotification();
  }

  /// Algo no se pudo hacer.
  static void error() {
    if (esIOS) HapticFeedback.errorNotification();
  }
}

/// Abre una pagina web en Safari (o el navegador del sistema). Se puede
/// reemplazar en las pruebas.
Future<void> Function(String url) abrirEnNavegador =
    (url) => InAppBrowser.openWithSystemBrowser(url: WebUri(url));

/// Desplazamiento que en iOS rebota abajo pero no arriba: deja que el gesto de
/// "tirar hacia abajo para cerrar" reciba el sobrante como en Android, en vez
/// de que la lista se lo coma con el rebote.
class RebotaSoloAbajo extends BouncingScrollPhysics {
  const RebotaSoloAbajo({super.parent});

  @override
  RebotaSoloAbajo applyTo(ScrollPhysics? ancestor) => RebotaSoloAbajo(parent: buildParent(ancestor));

  @override
  double applyBoundaryConditions(ScrollMetrics position, double value) {
    // pasarse por arriba: se devuelve el sobrante (como ClampingScrollPhysics)
    if (value < position.pixels && position.pixels <= position.minScrollExtent) {
      return value - position.pixels;
    }
    if (value < position.minScrollExtent && position.minScrollExtent < position.pixels) {
      return value - position.minScrollExtent;
    }
    return super.applyBoundaryConditions(position, value);
  }
}

/// En iPhone, deslizar el dedo desde el borde izquierdo hacia la derecha cierra
/// lo que envuelve (el reproductor, la hoja de sonido...), siguiendo al dedo
/// como el gesto de volver del sistema. En Android devuelve [child] tal cual.
class BordeVolver extends StatefulWidget {
  const BordeVolver({super.key, required this.alVolver, required this.child, this.seguirDedo = true});

  final VoidCallback alVolver;
  final Widget child;

  /// Si la pantalla se desplaza con el dedo mientras se arrastra.
  final bool seguirDedo;

  /// Ancho de la franja del borde que atiende el gesto.
  static const franja = 22.0;

  @override
  State<BordeVolver> createState() => _BordeVolverState();
}

class _BordeVolverState extends State<BordeVolver> with SingleTickerProviderStateMixin {
  final _dx = ValueNotifier<double>(0);
  late final AnimationController _vuelta = AnimationController(vsync: this, duration: const Duration(milliseconds: 220))
    ..addListener(() => _dx.value = _desde * (1 - Curves.easeOutCubic.transform(_vuelta.value)));
  double _desde = 0;

  @override
  void dispose() {
    _vuelta.dispose();
    _dx.dispose();
    super.dispose();
  }

  void _soltar(DragEndDetails d) {
    final ancho = MediaQuery.sizeOf(context).width;
    final v = d.primaryVelocity ?? 0;
    if (_dx.value > ancho * 0.33 || v > 600) {
      Haptico.toque();
      widget.alVolver();
      // si lo envuelto se queda (p. ej. pregunta antes de cerrar), vuelve a su sitio
    }
    _desde = _dx.value;
    _vuelta.forward(from: 0);
  }

  @override
  Widget build(BuildContext context) {
    if (!esIOS) return widget.child;
    final contenido = widget.seguirDedo
        ? ValueListenableBuilder<double>(
            valueListenable: _dx,
            builder: (_, dx, hijo) => Transform.translate(offset: Offset(dx, 0), child: hijo),
            child: widget.child,
          )
        : widget.child;
    // el contenido manda en el tamano; la franja va encima, pegada al borde
    return Stack(children: [
      RepaintBoundary(child: contenido),
      Positioned(
        left: 0, top: 0, bottom: 0, width: BordeVolver.franja,
        child: GestureDetector(
          behavior: HitTestBehavior.translucent,
          onHorizontalDragStart: (_) => _vuelta.stop(),
          onHorizontalDragUpdate: (d) => _dx.value = (_dx.value + d.delta.dx).clamp(0.0, double.infinity),
          onHorizontalDragEnd: _soltar,
          onHorizontalDragCancel: () {
            _desde = _dx.value;
            _vuelta.forward(from: 0);
          },
        ),
      ),
    ]);
  }
}
