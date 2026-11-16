import 'dart:math';
import 'dart:ui' show PointerDeviceKind;

import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../nucleo/version.dart';
import '../plataforma.dart';
import '../tema.dart';
import 'diapositivas.dart';
import 'ilustraciones.dart';

/// La presentación a pantalla completa de la actualización grande: una
/// diapositiva por novedad, con fondo de aurora, ilustración animada y
/// parallax. Se pasa deslizando, con las flechas, con el teclado o con los
/// botones; «Saltar» está siempre a la vista y «Empezar» la cierra al final.
class PresentacionNovedades extends StatefulWidget {
  const PresentacionNovedades({super.key, this.alCerrar, this.alEmpezar, this.paginaInicial = 0});

  /// Para las pruebas o para quien la monte sin ruta propia.
  final VoidCallback? alCerrar;
  final VoidCallback? alEmpezar;
  final int paginaInicial;

  @override
  State<PresentacionNovedades> createState() => _PresentacionNovedadesState();
}

class _PresentacionNovedadesState extends State<PresentacionNovedades> with SingleTickerProviderStateMixin {
  late final PageController _pc = PageController(initialPage: widget.paginaInicial.clamp(0, diapositivas.length - 1));
  late final AnimationController _reloj =
      AnimationController(vsync: this, duration: const Duration(seconds: 12));
  late final ValueNotifier<double> _pos = ValueNotifier(widget.paginaInicial.clamp(0, diapositivas.length - 1).toDouble());
  late int _actual = widget.paginaInicial.clamp(0, diapositivas.length - 1);
  bool _reducir = false;
  bool _iniciado = false;

  int get _total => diapositivas.length;
  bool get _ultima => _actual >= _total - 1;

  @override
  void initState() {
    super.initState();
    _pc.addListener(() {
      if (_pc.hasClients && _pc.position.haveDimensions) _pos.value = _pc.page ?? _pos.value;
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final reducir = MediaQuery.disableAnimationsOf(context);
    if (_iniciado && reducir == _reducir) return;
    _iniciado = true;
    _reducir = reducir;
    if (reducir) {
      // quien pide menos movimiento ve una imagen fija, ya compuesta
      _reloj.stop();
      _reloj.value = 8 / segundosVuelta;
    } else if (!_reloj.isAnimating) {
      _reloj.repeat();
    }
  }

  @override
  void dispose() {
    _pc.dispose();
    _reloj.dispose();
    _pos.dispose();
    super.dispose();
  }

  void _ir(int i) {
    final destino = i.clamp(0, _total - 1);
    if (destino == _actual || !_pc.hasClients) return;
    Haptico.toque();
    if (_reducir) {
      _pc.jumpToPage(destino);
    } else {
      _pc.animateToPage(destino, duration: const Duration(milliseconds: 560), curve: Curves.easeOutCubic);
    }
  }

  void _cerrar() {
    final f = widget.alCerrar;
    if (f != null) {
      f();
    } else {
      Navigator.of(context).maybePop();
    }
  }

  void _empezar() {
    Haptico.toque();
    final f = widget.alEmpezar;
    if (f != null) {
      f();
    } else {
      _cerrar();
    }
  }

  KeyEventResult _tecla(FocusNode nodo, KeyEvent e) {
    if (e is KeyUpEvent) return KeyEventResult.ignored;
    final k = e.logicalKey;
    if (k == LogicalKeyboardKey.arrowRight || k == LogicalKeyboardKey.arrowDown || k == LogicalKeyboardKey.pageDown) {
      _ir(_actual + 1);
      return KeyEventResult.handled;
    }
    if (k == LogicalKeyboardKey.arrowLeft || k == LogicalKeyboardKey.arrowUp || k == LogicalKeyboardKey.pageUp) {
      _ir(_actual - 1);
      return KeyEventResult.handled;
    }
    if (k == LogicalKeyboardKey.home) {
      _ir(0);
      return KeyEventResult.handled;
    }
    if (k == LogicalKeyboardKey.end) {
      _ir(_total - 1);
      return KeyEventResult.handled;
    }
    if (k == LogicalKeyboardKey.space || k == LogicalKeyboardKey.enter || k == LogicalKeyboardKey.numpadEnter) {
      if (_ultima) {
        _empezar();
      } else {
        _ir(_actual + 1);
      }
      return KeyEventResult.handled;
    }
    if (k == LogicalKeyboardKey.escape) {
      _cerrar();
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  /// Color de la diapositiva en [pos] (se mezcla entre dos al deslizar).
  Color _colorEn(double pos) {
    final a = pos.floor().clamp(0, _total - 1);
    final b = (a + 1).clamp(0, _total - 1);
    return mezclaAcento(Color.lerp(diapositivas[a].color, diapositivas[b].color, (pos - a).clamp(0.0, 1.0))!);
  }

  @override
  Widget build(BuildContext context) {
    final ctx = Ctx(_reloj, C.acento, _reducir);
    return Semantics(
      scopesRoute: true,
      explicitChildNodes: true,
      label: 'Novedades de Caudal',
      child: Focus(
        autofocus: true,
        onKeyEvent: _tecla,
        child: Material(
          color: C.fondo,
          child: Stack(children: [
            // ---- fondo: aurora que cambia de color con cada diapositiva
            Positioned.fill(
              child: IgnorePointer(
                child: RepaintBoundary(
                  child: AnimatedBuilder(
                    animation: Listenable.merge([_reloj, _pos]),
                    builder: (_, _) => CustomPaint(painter: _Aurora(_reloj.value * segundosVuelta, _pos.value, _colorEn(_pos.value))),
                  ),
                ),
              ),
            ),
            SafeArea(
              child: Column(children: [
                // ---- barra de arriba: edición a la izquierda, «Saltar» siempre a la derecha
                Padding(
                  padding: const EdgeInsets.fromLTRB(Esp.l + 4, Esp.xs, Esp.s, 0),
                  child: SizedBox(
                    height: 48,
                    child: Row(children: [
                      Expanded(
                        child: Text('Caudal ${_mayorMenor(edicionNovedades)}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, letterSpacing: 0.4, color: Colors.white.withValues(alpha: 0.6))),
                      ),
                      TextButton(
                        onPressed: _cerrar,
                        style: TextButton.styleFrom(
                          minimumSize: const Size(64, 44),
                          foregroundColor: Colors.white.withValues(alpha: 0.85),
                          textStyle: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700),
                        ),
                        child: const Text('Saltar'),
                      ),
                    ]),
                  ),
                ),
                // ---- las diapositivas
                Expanded(
                  child: ScrollConfiguration(
                    behavior: ScrollConfiguration.of(context).copyWith(dragDevices: {
                      PointerDeviceKind.touch,
                      PointerDeviceKind.mouse,
                      PointerDeviceKind.trackpad,
                      PointerDeviceKind.stylus,
                    }),
                    child: PageView.builder(
                      controller: _pc,
                      itemCount: _total,
                      onPageChanged: (i) => setState(() => _actual = i),
                      itemBuilder: (_, i) => _Pagina(d: diapositivas[i], indice: i, pos: _pos, ctx: ctx),
                    ),
                  ),
                ),
                _Controles(
                  pos: _pos,
                  total: _total,
                  actual: _actual,
                  alAnterior: () => _ir(_actual - 1),
                  alSiguiente: () => _ir(_actual + 1),
                  alEmpezar: _empezar,
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

String _mayorMenor(String v) {
  final p = v.split('.');
  return p.length >= 2 ? '${p[0]}.${p[1]}' : v;
}

// ------------------------------------------------------------------ controles

class _Controles extends StatelessWidget {
  const _Controles({
    required this.pos,
    required this.total,
    required this.actual,
    required this.alAnterior,
    required this.alSiguiente,
    required this.alEmpezar,
  });

  final ValueListenable<double> pos;
  final int total;
  final int actual;
  final VoidCallback alAnterior;
  final VoidCallback alSiguiente;
  final VoidCallback alEmpezar;

  @override
  Widget build(BuildContext context) {
    final ultima = actual >= total - 1;
    final puntos = Semantics(
      label: 'Diapositiva ${actual + 1} de $total',
      child: ExcludeSemantics(
        child: ValueListenableBuilder<double>(
          valueListenable: pos,
          builder: (_, p, _) => Row(mainAxisSize: MainAxisSize.min, children: [
            for (var i = 0; i < total; i++)
              Container(
                width: 6 + 16 * (1 - (i - p).abs()).clamp(0.0, 1.0),
                height: 6,
                margin: const EdgeInsets.symmetric(horizontal: 2.5),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(3),
                  color: Color.lerp(Colors.white.withValues(alpha: 0.28), Colors.white, (1 - (i - p).abs()).clamp(0.0, 1.0)),
                ),
              ),
          ]),
        ),
      ),
    );
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.m, Esp.xs, Esp.m, Esp.m),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: ultima
              ? Column(mainAxisSize: MainAxisSize.min, children: [
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: alEmpezar,
                      style: FilledButton.styleFrom(
                        shape: const StadiumBorder(),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        textStyle: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w800),
                      ),
                      icon: const Icon(Icons.arrow_forward_rounded),
                      iconAlignment: IconAlignment.end,
                      label: const Text('Empezar'),
                    ),
                  ),
                  const SizedBox(height: Esp.m),
                  puntos,
                ])
              : Row(children: [
                  SizedBox(
                    width: 48,
                    child: actual > 0
                        ? IconButton(
                            tooltip: 'Anterior',
                            onPressed: alAnterior,
                            style: IconButton.styleFrom(backgroundColor: const Color(0x22FFFFFF), minimumSize: const Size(48, 48)),
                            icon: const Icon(Icons.arrow_back_rounded),
                          )
                        : null,
                  ),
                  Expanded(child: Center(child: FittedBox(fit: BoxFit.scaleDown, child: puntos))),
                  IconButton(
                    tooltip: 'Siguiente',
                    onPressed: alSiguiente,
                    style: IconButton.styleFrom(
                      backgroundColor: C.acento,
                      foregroundColor: C.acentoTexto,
                      minimumSize: const Size(48, 48),
                    ),
                    icon: const Icon(Icons.arrow_forward_rounded),
                  ),
                ]),
        ),
      ),
    );
  }
}

// -------------------------------------------------------------------- páginas

/// Una capa que se desplaza un poco más (o menos) que la página al deslizar:
/// eso da la sensación de profundidad.
class _Parallax extends StatelessWidget {
  const _Parallax({required this.pos, required this.indice, required this.factor, required this.child, this.fade = 1.2});
  final ValueListenable<double> pos;
  final int indice;
  final double factor;
  final double fade;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final ancho = MediaQuery.sizeOf(context).width;
    return ValueListenableBuilder<double>(
      valueListenable: pos,
      child: child,
      builder: (_, p, h) {
        final d = (indice - p).clamp(-1.0, 1.0);
        return Opacity(
          opacity: (1 - d.abs() * fade).clamp(0.0, 1.0),
          child: Transform.translate(offset: Offset(d * ancho * factor, 0), child: h),
        );
      },
    );
  }
}

class _Pagina extends StatelessWidget {
  const _Pagina({required this.d, required this.indice, required this.pos, required this.ctx});
  final Diapo d;
  final int indice;
  final ValueListenable<double> pos;
  final Ctx ctx;

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, c) {
        final ancho = c.maxWidth, alto = c.maxHeight;
        final ancha = ancho >= 600 && ancho > alto * 1.15;
        final compacto = alto < 520 || ancho < 340;
        final ilus = _Parallax(
          pos: pos,
          indice: indice,
          factor: -0.35,
          fade: 1.0,
          child: LayoutBuilder(builder: (_, cc) {
            final lado = min(min(cc.maxWidth, cc.maxHeight), 560.0);
            if (!lado.isFinite || lado < 48) return const SizedBox.shrink();
            return Center(child: SizedBox.square(dimension: lado, child: d.ilustracion(ctx, lado)));
          }),
        );
        final textos = _Parallax(
          pos: pos,
          indice: indice,
          factor: 0.22,
          child: _Textos(d: d, ancha: ancha, compacto: compacto, ctx: ctx, primera: indice == 0),
        );
        if (ancha) {
          return Padding(
            padding: EdgeInsets.symmetric(horizontal: ancho * 0.05),
            child: Row(children: [
              Expanded(flex: 11, child: ilus),
              const SizedBox(width: Esp.xl),
              Expanded(flex: 9, child: Center(child: SingleChildScrollView(child: textos))),
            ]),
          );
        }
        return Column(children: [
          Expanded(child: ilus),
          ConstrainedBox(
            constraints: BoxConstraints(maxHeight: alto * 0.46),
            child: SingleChildScrollView(child: textos),
          ),
          const SizedBox(height: Esp.s),
        ]);
      });
}

class _Textos extends StatelessWidget {
  const _Textos({required this.d, required this.ancha, required this.compacto, required this.ctx, required this.primera});
  final Diapo d;
  final bool ancha;
  final bool compacto;
  final Ctx ctx;
  final bool primera;

  @override
  Widget build(BuildContext context) {
    final alinea = ancha ? CrossAxisAlignment.start : CrossAxisAlignment.center;
    final texto = ancha ? TextAlign.start : TextAlign.center;
    final tam = primera
        ? (ancha ? 38.0 : (compacto ? 24.0 : 30.0))
        : (ancha ? 40.0 : (compacto ? 25.0 : 31.0));
    final estilo = TextStyle(
      fontSize: tam,
      fontWeight: primera ? FontWeight.w900 : FontWeight.w800,
      letterSpacing: primera ? 2.2 : -0.6,
      height: 1.1,
      color: Colors.white,
    );
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: ancha ? 0 : Esp.xl + 4),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: alinea, children: [
        _Titulo(texto: d.titulo, estilo: estilo, align: texto, ctx: primera ? ctx : null),
        SizedBox(height: compacto ? Esp.s : Esp.m),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: Text(
            d.texto,
            textAlign: texto,
            style: TextStyle(fontSize: compacto ? 15 : 16.5, color: Colors.white.withValues(alpha: 0.82), height: 1.45),
          ),
        ),
        const SizedBox(height: Esp.m),
      ]),
    );
  }
}

/// El título, con la letra reducida si su palabra más larga no cabe (en
/// pantallas estrechas o con letra grande). Con [ctx], lleva un destello.
class _Titulo extends StatelessWidget {
  const _Titulo({required this.texto, required this.estilo, required this.align, this.ctx});
  final String texto;
  final TextStyle estilo;
  final TextAlign align;
  final Ctx? ctx;

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, c) {
        var estiloFinal = estilo;
        final escala = MediaQuery.textScalerOf(context);
        if (c.maxWidth.isFinite) {
          final larga = texto.split(' ').reduce((a, b) => a.length >= b.length ? a : b);
          final tp = TextPainter(
            text: TextSpan(text: larga, style: estilo),
            textDirection: TextDirection.ltr,
            textScaler: escala,
          )..layout();
          if (tp.width > c.maxWidth) {
            estiloFinal = estilo.copyWith(fontSize: max(12.0, estilo.fontSize! * c.maxWidth / tp.width * 0.96));
          }
        }
        Widget t = Semantics(
          header: true,
          child: Text(texto, textAlign: align, style: estiloFinal),
        );
        final x = ctx;
        if (x != null) {
          t = AnimatedBuilder(
            animation: x.reloj,
            child: t,
            builder: (_, h) {
              final q = Curves.easeInOut.transform(((x.s % 4) / 4 / 0.5).clamp(0.0, 1.0));
              return ShaderMask(
                blendMode: BlendMode.srcIn,
                shaderCallback: (r) => LinearGradient(
                  colors: [Colors.white.withValues(alpha: 0.82), Color.lerp(C.acentoAlto, Colors.white, 0.6)!, Colors.white.withValues(alpha: 0.82)],
                  stops: const [0.35, 0.5, 0.65],
                  transform: _Desliza(-1.2 + 2.4 * q),
                ).createShader(r),
                child: h,
              );
            },
          );
        }
        return t;
      });
}

class _Desliza extends GradientTransform {
  const _Desliza(this.fraccion);
  final double fraccion;
  @override
  Matrix4? transform(Rect bounds, {TextDirection? textDirection}) => Matrix4.translationValues(bounds.width * fraccion, 0, 0);
}

// --------------------------------------------------------------------- fondo

/// El fondo: un degradado del color de la diapositiva con cuatro luces que
/// se mueven despacio (como una aurora) y motas que suben.
class _Aurora extends CustomPainter {
  _Aurora(this.s, this.pos, this.color);
  final double s;
  final double pos;
  final Color color;

  double _onda(double periodo, [double fase = 0]) => 0.5 + 0.5 * sin(2 * pi * (s / periodo + fase));

  @override
  void paint(Canvas canvas, Size z) {
    final r = Offset.zero & z;
    canvas.drawRect(
      r,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color.lerp(color, C.fondo, 0.60)!, Color.lerp(color, C.fondo, 0.86)!, C.fondo],
          stops: const [0, 0.45, 0.95],
        ).createShader(r),
    );
    final grande = max(z.width, z.height);
    final luces = <(double, double, Color, double, double)>[
      (0.15 + 0.5 * _onda(12), 0.12 + 0.12 * _onda(6, 0.2), C.acentoAlto, 0.30, 0.55),
      (0.85 - 0.45 * _onda(12, 0.3), 0.30 + 0.12 * _onda(4, 0.5), color, 0.30, 0.50),
      (0.20 + 0.3 * _onda(6, 0.6), 0.62 + 0.10 * _onda(12, 0.1), Color.lerp(color, const Color(0xFFFF5C8A), 0.5)!, 0.18, 0.55),
      (0.75 - 0.3 * _onda(4, 0.1), 0.85 - 0.08 * _onda(6, 0.7), Color.lerp(color, const Color(0xFF8B6CFF), 0.5)!, 0.16, 0.50),
    ];
    for (var i = 0; i < luces.length; i++) {
      final (x, y, col, a, rad) = luces[i];
      final o = Offset(z.width * (x - pos * 0.035 * (i + 1) % 0.4 + 0.0), z.height * y);
      final rr = grande * rad;
      canvas.drawCircle(o, rr, Paint()..shader = RadialGradient(colors: [col.withValues(alpha: a), col.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: o, radius: rr)));
    }
    // motas de luz que suben muy despacio
    for (var i = 0; i < 18; i++) {
      final x = z.width * ((i * 0.618034) % 1);
      final p = ((s / 12) * (1 + i % 2) + (i * 0.29) % 1) % 1;
      final y = z.height * (1.05 - 1.1 * p);
      final a = pow(sin(pi * p), 1.2).toDouble() * 0.28;
      canvas.drawCircle(Offset(x + sin(2 * pi * (s / 6 + i * 0.1)) * 6, y), 0.9 + (i % 3) * 0.6, Paint()..color = Colors.white.withValues(alpha: a));
    }
  }

  @override
  bool shouldRepaint(covariant _Aurora old) => true;
}
