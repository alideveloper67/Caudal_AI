// La presentación de la versión 2.3.2 del móvil: «Mascotitas y fondos con
// personaje». Sale una sola vez al abrir Caudal tras actualizar (ver
// [tocaPresentacionMascotas]) y se puede abrir a mano con
// [abrirPresentacionMascotas]. No toca la música: es solo una pantalla encima.
//
// Las mascotitas se dibujan igual que en la barra de verdad
// (reproductor/mascota_barra.dart): la hoja de cuadros con FilterQuality.none,
// su estela o, en Nyan Cat, su arcoíris. Las exclusivas de una cuenta no salen.

import 'dart:math';
import 'dart:ui' as ui;
import 'dart:ui' show PointerDeviceKind;

import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../nucleo/mascota_app.dart';
import '../../nucleo/version.dart';
import '../paginas/aspecto_pagina.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';

/// Desde qué versión existe esta presentación.
const String versionPresentacionMascotas = '2.3.2';

/// Donde se guarda la versión en la que ya se enseñó (vacío: nunca).
const String clavePresentacionMascotasVista = 'presentacion_mascotas_vista';

/// ¿Toca enseñar la presentación de las mascotitas? Una sola vez, a quien abre
/// la [versionPresentacionMascotas] o una posterior y aún no la vio ([vista]
/// vacía). Si en ese arranque ya salen las novedades grandes, espera al
/// siguiente para no encimarse.
bool tocaPresentacionMascotas(String? vista, String actual,
    {bool salenNovedadesGrandes = false, String desde = versionPresentacionMascotas}) {
  if (salenNovedadesGrandes) return false;
  if (hayNovedad(actual, desde)) return false; // aún no es la 2.3.2
  return vista == null || vista.trim().isEmpty;
}

/// Las mascotitas que se enseñan: nunca las exclusivas de una cuenta. Las más
/// conocidas van primero.
List<Mascota> mascotasDeLaPresentacion(List<Mascota> catalogo) {
  const primero = ['pikachu', 'nyan', 'kirby', 'hellokitty', 'cinnamoroll', 'charmander', 'totoro', 'kuromi',
    'gato_negro', 'squirtle', 'capibara', 'bulbasaur', 'mymelody', 'purin', 'snoopy', 'doraemon', 'pochacco', 'olaf'];
  final libres = [for (final m in catalogo) if (!m.esExclusiva) m];
  int orden(Mascota m) {
    final i = primero.indexOf(m.clave);
    return i < 0 ? primero.length : i;
  }

  final conIndice = libres.indexed.toList()
    ..sort((a, b) {
      final d = orden(a.$2) - orden(b.$2);
      return d != 0 ? d : a.$1 - b.$1;
    });
  return [for (final e in conIndice) e.$2];
}

/// Abre la presentación a pantalla completa (por ejemplo, desde un botón).
Future<void> abrirPresentacionMascotas(BuildContext context) => PresentacionMascotas.mostrar(context);

/// Segundos de una vuelta del reloj de las ilustraciones (múltiplo de todos
/// los ciclos que se usan, para que al dar la vuelta nada salte).
const double _vuelta = 144;

class PresentacionMascotas extends StatefulWidget {
  const PresentacionMascotas({
    super.key,
    this.alCerrar,
    this.alEmpezar,
    this.alIrAAspecto,
    this.paginaInicial = 0,
    this.catalogo,
  });

  /// Para las pruebas o para quien la monte sin ruta propia.
  final VoidCallback? alCerrar;
  final VoidCallback? alEmpezar;
  final VoidCallback? alIrAAspecto;
  final int paginaInicial;

  /// El catálogo de mascotas (si falta, el de la app).
  final List<Mascota>? catalogo;

  static int get totalDiapositivas => 5;

  /// La abre a pantalla completa con una entrada suave. Termina al cerrarse.
  static Future<void> mostrar(BuildContext context) => Navigator.of(context, rootNavigator: true).push(PageRouteBuilder<void>(
        transitionDuration: const Duration(milliseconds: 520),
        reverseTransitionDuration: const Duration(milliseconds: 320),
        pageBuilder: (_, _, _) => const PresentacionMascotas(),
        transitionsBuilder: (_, a, _, hijo) => FadeTransition(
          opacity: CurvedAnimation(parent: a, curve: Curves.easeOut),
          child: ScaleTransition(
            scale: Tween(begin: 1.04, end: 1.0).animate(CurvedAnimation(parent: a, curve: Curves.easeOutCubic)),
            child: hijo,
          ),
        ),
      ));

  @override
  State<PresentacionMascotas> createState() => _PresentacionMascotasState();
}

// --------------------------------------------------------------- diapositivas

class _Diapo {
  const _Diapo({required this.titulo, required this.texto, required this.color, required this.ilustracion, this.insignia, this.iconoInsignia});
  final String titulo;
  final String texto;
  final Color color;
  final String? insignia;
  final IconData? iconoInsignia;
  final Widget Function(_Escena e) ilustracion;
}

List<_Diapo> _diapositivas(int cuantas) => [
      _Diapo(
        titulo: 'Mascotitas y fondos con personaje',
        texto: 'Caudal $versionPresentacionMascotas trae amiguitos en pixel art que caminan por tu barra '
            'y fondos con tus personajes favoritos.',
        color: const Color(0xFFFF77B7),
        ilustracion: (e) => _IlusPortada(e: e),
      ),
      _Diapo(
        titulo: 'Un amiguito en tu barra',
        texto: 'Tu mascotita camina sobre la barra de la canción mientras suena y deja su estela: corazones, '
            'estrellas, hojas… y Nyan Cat, su arcoíris. '
            '${cuantas > 0 ? 'Hay $cuantas para elegir' : 'Hay muchas para elegir'} en Ajustes › Mascotita del reproductor.',
        color: const Color(0xFFF5C542),
        insignia: 'Para donadores y fundadores de Caudal',
        iconoInsignia: Icons.favorite_rounded,
        ilustracion: (e) => _IlusDesfile(e: e),
      ),
      _Diapo(
        titulo: 'Fondos con personaje',
        texto: 'Caudal se pinta con los colores de tu personaje y él te acompaña, chiquito, en una esquina. '
            'Son ${Aspecto.temas.length}, en Ajustes › Aspecto › Con personajes.',
        color: const Color(0xFF7FB8FF),
        insignia: 'Para todas las cuentas',
        iconoInsignia: Icons.palette_rounded,
        ilustracion: (e) => _IlusFondos(e: e),
      ),
      _Diapo(
        titulo: 'Tu fondo y tu personaje van juntos',
        texto: 'Al elegir un fondo con personaje, su mascotita también se pone a caminar por tu barra '
            '(si tu cuenta tiene mascotas). Y si usas tu imagen de «Fondo de Caudal», se sigue viendo: '
            'el personaje se queda encima, en su esquina.',
        color: const Color(0xFFB4A1FF),
        ilustracion: (e) => _IlusJuntos(e: e),
      ),
      _Diapo(
        titulo: 'Gracias por estar en Caudal',
        texto: 'Disfruta lo nuevo. Cuando quieras, elige tu fondo con personaje en Ajustes › Aspecto.',
        color: const Color(0xFFFF8FB8),
        ilustracion: (e) => _IlusCierre(e: e),
      ),
    ];

// --------------------------------------------------------------------- estado

class _PresentacionMascotasState extends State<PresentacionMascotas> with SingleTickerProviderStateMixin {
  late final int _inicial = widget.paginaInicial.clamp(0, PresentacionMascotas.totalDiapositivas - 1);
  late final PageController _pc = PageController(initialPage: _inicial);
  late final AnimationController _reloj =
      AnimationController(vsync: this, duration: Duration(milliseconds: (_vuelta * 1000).round()));
  late final ValueNotifier<double> _pos = ValueNotifier(_inicial.toDouble());
  late int _actual = _inicial;
  bool _reducir = false;
  bool _iniciado = false;

  List<Mascota> _mascotas = const [];
  final Map<String, _Hoja> _hojas = {};

  int get _total => PresentacionMascotas.totalDiapositivas;
  bool get _ultima => _actual >= _total - 1;

  @override
  void initState() {
    super.initState();
    _pc.addListener(() {
      if (_pc.hasClients && _pc.position.haveDimensions) _pos.value = _pc.page ?? _pos.value;
    });
    final dado = widget.catalogo;
    if (dado != null) {
      _usar(dado);
    } else if (MascotaApp.i.catalogo.isNotEmpty) {
      _usar(MascotaApp.i.catalogo);
    } else {
      MascotaApp.i.cargarCatalogo().then((_) {
        if (mounted) setState(() => _usar(MascotaApp.i.catalogo));
      });
    }
  }

  void _usar(List<Mascota> catalogo) {
    _mascotas = mascotasDeLaPresentacion(catalogo);
    for (final m in _mascotas) {
      final h = _hojas[m.clave] = _Hoja(m);
      MascotaApp.i.imagen(m.clave).then((im) {
        if (mounted && im != null) setState(() => h.hoja = im);
      });
      if (m.tieneEstela) {
        MascotaApp.i.imagenEstela(m.clave).then((im) {
          if (mounted && im != null) setState(() => h.estela = im);
        });
      }
    }
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
      _reloj.value = 3.3 / _vuelta;
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

  /// Cierra la presentación y abre Ajustes › Aspecto (en la pestaña de
  /// siempre, con el mini reproductor a la vista).
  void _irAAspecto() {
    Haptico.toque();
    final f = widget.alIrAAspecto;
    if (f != null) {
      f();
      return;
    }
    final nav = Navigator.of(context);
    void Function(Widget)? enPestana;
    try {
      enPestana = Caudal.leer(context).abrirEnPestana;
    } catch (_) {}
    nav.maybePop();
    if (enPestana != null) {
      enPestana(const AspectoPagina());
    } else {
      nav.push(MaterialPageRoute(builder: (_) => const AspectoPagina()));
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

  @override
  Widget build(BuildContext context) {
    final diapos = _diapositivas(_mascotas.length);
    final escena = _Escena(_reloj, [for (final m in _mascotas) _hojas[m.clave]!]);
    Color colorEn(double p) {
      final a = p.floor().clamp(0, _total - 1);
      final b = (a + 1).clamp(0, _total - 1);
      return Color.lerp(diapos[a].color, diapos[b].color, (p - a).clamp(0.0, 1.0))!;
    }

    return Semantics(
      scopesRoute: true,
      explicitChildNodes: true,
      label: 'Novedades de Caudal $versionPresentacionMascotas',
      child: Focus(
        autofocus: true,
        onKeyEvent: _tecla,
        child: Material(
          color: C.fondo,
          child: Stack(children: [
            Positioned.fill(
              child: IgnorePointer(
                child: RepaintBoundary(
                  child: AnimatedBuilder(
                    animation: Listenable.merge([_reloj, _pos]),
                    builder: (_, _) => CustomPaint(painter: _FondoPixel(_reloj.value * _vuelta, colorEn(_pos.value))),
                  ),
                ),
              ),
            ),
            SafeArea(
              child: Column(children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(Esp.l + 4, Esp.xs, Esp.s, 0),
                  child: SizedBox(
                    height: 48,
                    child: Row(children: [
                      Expanded(
                        child: Text('Caudal $versionPresentacionMascotas',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                                fontSize: 13, fontWeight: FontWeight.w800, letterSpacing: 0.4, color: Colors.white.withValues(alpha: 0.6))),
                      ),
                      TextButton(
                        onPressed: _cerrar,
                        style: TextButton.styleFrom(
                          minimumSize: const Size(64, 44),
                          foregroundColor: Colors.white.withValues(alpha: 0.85),
                          textStyle: Theme.of(context).textTheme.labelLarge?.copyWith(fontSize: 14.5, fontWeight: FontWeight.w700),
                        ),
                        child: const Text('Saltar'),
                      ),
                    ]),
                  ),
                ),
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
                      itemBuilder: (_, i) => _Pagina(d: diapos[i], indice: i, pos: _pos, escena: escena),
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
                  alIrAAspecto: _irAAspecto,
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
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
    required this.alIrAAspecto,
  });

  final ValueListenable<double> pos;
  final int total;
  final int actual;
  final VoidCallback alAnterior;
  final VoidCallback alSiguiente;
  final VoidCallback alEmpezar;
  final VoidCallback alIrAAspecto;

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
                        padding: const EdgeInsets.symmetric(vertical: 15),
                        textStyle: Theme.of(context).textTheme.labelLarge?.copyWith(fontSize: 16.5, fontWeight: FontWeight.w800),
                      ),
                      icon: const Icon(Icons.arrow_forward_rounded),
                      iconAlignment: IconAlignment.end,
                      label: const Text('Empezar'),
                    ),
                  ),
                  const SizedBox(height: Esp.xs),
                  TextButton.icon(
                    onPressed: alIrAAspecto,
                    style: TextButton.styleFrom(
                      minimumSize: const Size(48, 44),
                      foregroundColor: Colors.white.withValues(alpha: 0.9),
                      textStyle: Theme.of(context).textTheme.labelLarge?.copyWith(fontSize: 14.5, fontWeight: FontWeight.w700),
                    ),
                    icon: const Icon(Icons.palette_outlined, size: 20),
                    label: const Text('Elegir mi fondo ahora'),
                  ),
                  const SizedBox(height: Esp.s),
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
  const _Pagina({required this.d, required this.indice, required this.pos, required this.escena});
  final _Diapo d;
  final int indice;
  final ValueListenable<double> pos;
  final _Escena escena;

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
            // cada ilustración se diseña en 360x360 y se ajusta al hueco: nunca se desborda
            return Center(
              child: SizedBox.square(
                dimension: lado,
                child: ExcludeSemantics(
                  child: FittedBox(child: SizedBox.square(dimension: _lienzo, child: d.ilustracion(escena))),
                ),
              ),
            );
          }),
        );
        final textos = _Parallax(
          pos: pos,
          indice: indice,
          factor: 0.22,
          child: _Textos(d: d, ancha: ancha, compacto: compacto, primera: indice == 0),
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
            constraints: BoxConstraints(maxHeight: alto * 0.48),
            child: SingleChildScrollView(child: textos),
          ),
          const SizedBox(height: Esp.xs),
        ]);
      });
}

class _Textos extends StatelessWidget {
  const _Textos({required this.d, required this.ancha, required this.compacto, required this.primera});
  final _Diapo d;
  final bool ancha;
  final bool compacto;
  final bool primera;

  @override
  Widget build(BuildContext context) {
    final alinea = ancha ? CrossAxisAlignment.start : CrossAxisAlignment.center;
    final texto = ancha ? TextAlign.start : TextAlign.center;
    final tam = ancha ? 40.0 : (compacto ? 24.0 : 29.0);
    final estilo = TextStyle(
      fontSize: tam,
      fontWeight: primera ? FontWeight.w900 : FontWeight.w800,
      letterSpacing: -0.6,
      height: 1.1,
      color: Colors.white,
    );
    final insignia = d.insignia;
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: ancha ? 0 : Esp.xl),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: alinea, children: [
        if (insignia != null) ...[
          _Insignia(texto: insignia, icono: d.iconoInsignia ?? Icons.auto_awesome_rounded, color: d.color),
          SizedBox(height: compacto ? Esp.s : Esp.m),
        ],
        _Titulo(texto: d.titulo, estilo: estilo, align: texto),
        SizedBox(height: compacto ? Esp.s : Esp.m),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: Text(
            d.texto,
            textAlign: texto,
            style: TextStyle(fontSize: compacto ? 14.5 : 16, color: Colors.white.withValues(alpha: 0.82), height: 1.45),
          ),
        ),
        const SizedBox(height: Esp.m),
      ]),
    );
  }
}

class _Insignia extends StatelessWidget {
  const _Insignia({required this.texto, required this.icono, required this.color});
  final String texto;
  final IconData icono;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.16),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: color.withValues(alpha: 0.45)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icono, size: 15, color: Color.lerp(color, Colors.white, 0.35)),
          const SizedBox(width: 6),
          Flexible(
            child: Text(texto,
                maxLines: 2,
                textAlign: TextAlign.center,
                style: TextStyle(
                    fontSize: 12.5, fontWeight: FontWeight.w800, letterSpacing: 0.2, color: Color.lerp(color, Colors.white, 0.55))),
          ),
        ]),
      );
}

/// El título, con la letra reducida si su palabra más larga no cabe.
class _Titulo extends StatelessWidget {
  const _Titulo({required this.texto, required this.estilo, required this.align});
  final String texto;
  final TextStyle estilo;
  final TextAlign align;

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, c) {
        var estiloFinal = estilo;
        if (c.maxWidth.isFinite) {
          final larga = texto.split(' ').reduce((a, b) => a.length >= b.length ? a : b);
          final tp = TextPainter(
            text: TextSpan(text: larga, style: estilo),
            textDirection: TextDirection.ltr,
            textScaler: MediaQuery.textScalerOf(context),
          )..layout();
          if (tp.width > c.maxWidth) {
            estiloFinal = estilo.copyWith(fontSize: max(12.0, estilo.fontSize! * c.maxWidth / tp.width * 0.96));
          }
        }
        return Semantics(header: true, child: Text(texto, textAlign: align, style: estiloFinal));
      });
}

// ------------------------------------------------------------- las escenas

/// Lado del lienzo en el que se diseña cada ilustración.
const double _lienzo = 360;

/// Una mascotita con sus imágenes (llegan cuando se decodifican).
class _Hoja {
  _Hoja(this.m);
  final Mascota m;
  ui.Image? hoja;
  ui.Image? estela;
}

class _Escena {
  _Escena(this.reloj, this.mascotas);
  final Animation<double> reloj;
  final List<_Hoja> mascotas;

  /// Segundos del reloj (0 a [_vuelta]).
  double get s => reloj.value * _vuelta;

  _Hoja? de(String clave) {
    for (final h in mascotas) {
      if (h.m.clave == clave) return h;
    }
    return null;
  }

  _Hoja? enPosicion(int i) => mascotas.isEmpty ? null : mascotas[i % mascotas.length];
}

/// Dibuja una mascotita con sus pies en [yBarra], centrada en [x], a [escala]
/// (1 = el tamaño de la barra de verdad). Detrás, su estela o el arcoíris de
/// Nyan Cat, que empieza en [inicio]. Misma lógica que mascota_barra.dart.
void _pintarMascota(Canvas canvas, _Hoja h, double x, double yBarra, double escala, double s,
    {double inicio = 0, double opacidad = 1}) {
  final hoja = h.hoja;
  if (hoja == null) return;
  final m = h.m;
  final w = m.ancho * escala, alto = m.alto * escala;
  final arriba = yBarra - 2 * escala - alto;
  final tic = (s * 1000 / 180).floor();
  final cuadro = tic % m.cuadros;
  final fase = tic * 0.9;

  if (m.arcoiris) {
    final fino = 3 * escala;
    final base = arriba + alto * 0.30;
    final fin = x - w / 2 + w * 0.25;
    final p = Paint();
    for (var xi = inicio; xi < fin; xi += 2 * escala) {
      final onda = escala * (((xi - inicio) / (5 * escala) + fase).floor() % 2 == 0 ? 0 : 1);
      final ancho = min(2 * escala, fin - xi) + 0.5;
      for (var i = 0; i < _franjas.length; i++) {
        p.color = _franjas[i].withValues(alpha: opacidad);
        canvas.drawRect(Rect.fromLTWH(xi, base + i * fino + onda, ancho, fino), p);
      }
    }
  } else if (m.tieneEstela && h.estela != null) {
    const n = 7;
    final paso = 21 * escala;
    final centro = x - w * 0.32;
    final pies = arriba + alto;
    final ea = m.estelaAncho.toDouble(), eh = m.estelaAlto.toDouble();
    for (var i = 0; i < n; i++) {
      final px = centro - (i + 1) * paso;
      if (px < inicio) break;
      final vida = 1.0 - i / n;
      final tam = (18 * escala) * (0.6 + 0.4 * vida);
      final vaiven = sin(fase * 0.9 + i * 1.3) * 3 * escala;
      final py = pies - alto * 0.42 + vaiven - (1 - vida) * 3 * escala;
      final variante = (i + fase.toInt()) % 2;
      canvas.drawImageRect(
        h.estela!,
        Rect.fromLTWH(variante * ea, 0, ea, eh),
        Rect.fromLTWH(px - tam / 2, py - tam / 2, tam, tam),
        Paint()
          ..filterQuality = FilterQuality.none
          ..color = Color.fromRGBO(255, 255, 255, (0.25 + 0.75 * vida) * opacidad),
      );
    }
  }

  final fw = (m.ancho * m.densidad).toDouble(), fh = (m.alto * m.densidad).toDouble();
  canvas.drawImageRect(
    hoja,
    Rect.fromLTWH(cuadro * fw, 0, fw, fh),
    Rect.fromLTWH(x - w / 2, arriba, w, alto),
    Paint()
      ..filterQuality = filtroMascota(m.densidad)
      ..color = Color.fromRGBO(255, 255, 255, opacidad),
  );
}

const _franjas = [Color(0xFFFF0000), Color(0xFFFF9900), Color(0xFFFFFF00), Color(0xFF33FF00), Color(0xFF0099FF), Color(0xFF6633FF)];

/// La barra de progreso de la canción: el carril, lo ya sonado y el puntito.
void _pintarBarra(Canvas canvas, double x0, double x1, double y, double fraccion, Color relleno, {double grosor = 4}) {
  final r = Radius.circular(grosor / 2);
  canvas.drawRRect(RRect.fromRectAndRadius(Rect.fromLTRB(x0, y - grosor / 2, x1, y + grosor / 2), r),
      Paint()..color = Colors.white.withValues(alpha: 0.18));
  final xf = x0 + (x1 - x0) * fraccion.clamp(0.0, 1.0);
  canvas.drawRRect(RRect.fromRectAndRadius(Rect.fromLTRB(x0, y - grosor / 2, xf, y + grosor / 2), r), Paint()..color = relleno);
  canvas.drawCircle(Offset(xf, y), grosor * 1.35, Paint()..color = Colors.white);
}

/// Un corazoncito o una estrellita en pixel art (para adornar).
void _pintarPixel(Canvas canvas, List<String> dibujo, Offset centro, double px, Color color) {
  final p = Paint()..color = color;
  final alto = dibujo.length, ancho = dibujo.first.length;
  final o = centro - Offset(ancho * px / 2, alto * px / 2);
  for (var f = 0; f < alto; f++) {
    for (var c = 0; c < ancho; c++) {
      if (dibujo[f][c] == '#') canvas.drawRect(Rect.fromLTWH(o.dx + c * px, o.dy + f * px, px + 0.3, px + 0.3), p);
    }
  }
}

const _corazon = [
  '.##.##.',
  '#######',
  '#######',
  '.#####.',
  '..###..',
  '...#...',
];

const _estrella = [
  '..#..',
  '..#..',
  '#####',
  '..#..',
  '..#..',
];

const _nota = [
  '..####',
  '..#..#',
  '..#..#',
  '###.##',
  '###.##',
];

/// Pinta adornos que flotan y titilan en el lienzo.
class _Adornos extends CustomPainter {
  _Adornos(this.s, this.color, {this.cuantos = 9, this.semilla = 0});
  final double s;
  final Color color;
  final int cuantos;
  final int semilla;

  @override
  void paint(Canvas canvas, Size z) {
    for (var i = 0; i < cuantos; i++) {
      final k = i + semilla * 7;
      final x = z.width * ((k * 0.618034 + 0.07) % 1);
      final y = z.height * ((k * 0.381966 + 0.11) % 1) + sin(2 * pi * (s / 6 + k * 0.17)) * 5;
      final brillo = 0.35 + 0.65 * (0.5 + 0.5 * sin(2 * pi * (s / 3 + k * 0.23)));
      final dibujo = [_corazon, _estrella, _nota][k % 3];
      final col = Color.lerp(color, Colors.white, (k % 2) * 0.45)!.withValues(alpha: 0.5 * brillo);
      _pintarPixel(canvas, dibujo, Offset(x, y), 2.2 + (k % 2) * 0.8, col);
    }
  }

  @override
  bool shouldRepaint(covariant _Adornos old) => old.s != s || old.color != color;
}

/// Un panel de cristal oscuro (la tarjeta del reproductor, los carriles).
BoxDecoration _cristal({double radio = 22}) => BoxDecoration(
      borderRadius: BorderRadius.circular(radio),
      color: Colors.black.withValues(alpha: 0.5),
      border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      boxShadow: const [BoxShadow(color: Color(0x26000000), blurRadius: 28, offset: Offset(0, 4))],
    );

// ------------------------------------------------------------------ portada

/// La tarjeta del reproductor con una mascotita caminando por la barra al
/// ritmo de la canción (cambia de mascotita en cada vuelta) y tres amiguitos
/// saltando encima.
class _IlusPortada extends StatelessWidget {
  const _IlusPortada({required this.e});
  final _Escena e;

  static const _cancion = 9.0; // segundos que dura la "canción"

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: e.reloj,
        builder: (_, _) {
          final s = e.s;
          final vuelta = (s / _cancion).floor();
          final fraccion = 0.03 + 0.94 * ((s % _cancion) / _cancion);
          final caminante = e.enPosicion(vuelta);
          final arriba = [e.de('nyan'), e.de('pikachu'), e.de('kirby')];
          return Stack(clipBehavior: Clip.none, children: [
            Positioned.fill(child: CustomPaint(painter: _Adornos(s, const Color(0xFFFF77B7), cuantos: 10))),
            // los tres de arriba, caminando en su sitio y dando saltitos
            Positioned(
              left: 0,
              right: 0,
              top: 22,
              height: 120,
              child: CustomPaint(
                key: ValueKey('mascotas-${arriba.whereType<_Hoja>().map((h) => h.m.clave).join(',')}'),
                painter: _PintorTrio(arriba, s),
              ),
            ),
            // la tarjeta del reproductor
            Positioned(
              left: 14,
              right: 14,
              top: 150,
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
                decoration: _cristal(),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  Row(children: [
                    Container(
                      width: 54,
                      height: 54,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12),
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [Color(0xFFFF77B7), Color(0xFF8B6CFF)],
                        ),
                      ),
                      child: const Icon(Icons.music_note_rounded, color: Colors.white, size: 28),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        const Text('Tu canción favorita',
                            maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                        const SizedBox(height: 3),
                        Text(caminante == null ? 'Suena en Caudal' : 'Con ${caminante.m.nombre}',
                            maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, color: C.texto2)),
                      ]),
                    ),
                    const Icon(Icons.favorite_rounded, color: Color(0xFFFF77B7), size: 22),
                  ]),
                  SizedBox(
                    height: 84,
                    child: CustomPaint(
                      key: ValueKey('mascota-${caminante?.m.clave ?? ''}'),
                      size: Size.infinite,
                      painter: _PintorCarril(caminante, fraccion, s, escala: 1.15, relleno: const Color(0xFFFF77B7)),
                    ),
                  ),
                  Row(children: [
                    Text(_tiempo(fraccion * 214), style: const TextStyle(fontSize: 11.5, color: C.texto2)),
                    const Spacer(),
                    const Text('3:34', style: TextStyle(fontSize: 11.5, color: C.texto2)),
                  ]),
                ]),
              ),
            ),
          ]);
        },
      );
}

String _tiempo(double segundos) {
  final t = segundos.floor();
  return '${t ~/ 60}:${(t % 60).toString().padLeft(2, '0')}';
}

/// Tres mascotitas caminando en su sitio, con un saltito cada una a su turno.
class _PintorTrio extends CustomPainter {
  _PintorTrio(this.trio, this.s);
  final List<_Hoja?> trio;
  final double s;

  @override
  void paint(Canvas canvas, Size z) {
    const escala = 1.55;
    for (var i = 0; i < trio.length; i++) {
      final h = trio[i];
      if (h == null) continue;
      final x = z.width * (0.22 + 0.28 * i);
      final ciclo = (s / 2.4 + i / 3) % 1;
      final salto = ciclo < 0.28 ? sin(pi * ciclo / 0.28) * 14 : 0.0;
      final suelo = z.height - 6;
      // sombra en el suelo (se achica al saltar)
      final ancho = h.m.ancho * escala * 0.7 * (1 - salto / 40);
      canvas.drawOval(Rect.fromCenter(center: Offset(x, suelo), width: ancho, height: 7),
          Paint()..color = Colors.black.withValues(alpha: 0.32));
      // sin estela: aquí no avanzan
      final quieta = _Hoja(h.m)..hoja = h.hoja;
      _pintarMascota(canvas, quieta, x, suelo - salto, escala, s + i * 0.3);
    }
  }

  @override
  bool shouldRepaint(covariant _PintorTrio old) => true;
}

/// Un carril con la barra de la canción y una mascotita encima, en [fraccion].
class _PintorCarril extends CustomPainter {
  _PintorCarril(this.h, this.fraccion, this.s, {required this.escala, required this.relleno, this.margen = 6, this.grosor = 4});
  final _Hoja? h;
  final double fraccion;
  final double s;
  final double escala;
  final Color relleno;
  final double margen;
  final double grosor;

  @override
  void paint(Canvas canvas, Size z) {
    final y = z.height - 12;
    final x0 = margen, x1 = z.width - margen;
    final x = x0 + (x1 - x0) * fraccion;
    _pintarBarra(canvas, x0, x1, y, fraccion, relleno, grosor: grosor);
    final m = h;
    if (m != null) _pintarMascota(canvas, m, x, y, escala, s, inicio: x0);
  }

  @override
  bool shouldRepaint(covariant _PintorCarril old) => true;
}

// ------------------------------------------------------------------ desfile

/// Cuatro carriles, cada uno con una mascotita que camina a su ritmo y deja su
/// estela; en cada vuelta sale otra, así pasan todas.
class _IlusDesfile extends StatelessWidget {
  const _IlusDesfile({required this.e});
  final _Escena e;

  static const _carriles = 4;
  static const _colores = [Color(0xFFF5C542), Color(0xFFFF77B7), Color(0xFF7FB8FF), Color(0xFF6EE7A3)];
  // múltiplos de _vuelta para que nada salte al dar la vuelta el reloj
  static const _periodos = [8.0, 9.0, 7.2, 9.6];

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: e.reloj,
        builder: (_, _) {
          final s = e.s;
          return Container(
            padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
            decoration: _cristal(radio: 26),
            child: Column(children: [
              for (var i = 0; i < _carriles; i++)
                Expanded(child: _carril(i, s)),
            ]),
          );
        },
      );

  Widget _carril(int i, double s) {
    final t = s / _periodos[i] + i * 0.31;
    final vuelta = t.floor();
    final avance = t - vuelta;
    final h = e.enPosicion(i + _carriles * vuelta);
    // entra despacio desde la izquierda y sale por la derecha
    final fraccion = 0.06 + 0.9 * avance;
    final aparece = (min(avance, 1 - avance) / 0.06).clamp(0.0, 1.0);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SizedBox(
        height: 16,
        child: Row(children: [
          Container(width: 6, height: 6, decoration: BoxDecoration(color: _colores[i], shape: BoxShape.circle)),
          const SizedBox(width: 6),
          Expanded(
            child: Text(h?.m.nombre ?? '',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: Colors.white.withValues(alpha: 0.75))),
          ),
        ]),
      ),
      Expanded(
        child: Opacity(
          opacity: aparece,
          child: CustomPaint(
            key: ValueKey('mascota-${h?.m.clave ?? ''}'),
            size: Size.infinite,
            painter: _PintorCarril(h, fraccion, s + i * 0.21, escala: 1.0, relleno: _colores[i], margen: 4, grosor: 3.5),
          ),
        ),
      ),
    ]);
  }
}

// ------------------------------------------------------------------ teléfono

/// Una Caudal de juguete con los colores de [tema], su personaje en la
/// esquina y, si se da, una mascotita caminando por la barra del mini
/// reproductor.
class _Telefono extends StatelessWidget {
  const _Telefono({super.key, required this.tema, this.mascota, this.fraccion = 0.4, this.s = 0, this.alto = 330});
  final String tema;
  final _Hoja? mascota;
  final double fraccion;
  final double s;
  final double alto;

  static const proporcion = 0.49;

  @override
  Widget build(BuildContext context) {
    final t = Aspecto.temas[tema]!;
    final ancho = alto * proporcion;
    final g = _GeoTelefono(Size(ancho, alto));
    final personaje = Aspecto.patronDe(tema)!;
    return SizedBox(
      width: ancho,
      height: alto,
      child: Stack(clipBehavior: Clip.none, children: [
        Positioned.fill(child: CustomPaint(painter: _PintorTelefono(t.$3, t.$2, g))),
        // el personaje, chico, sobre el mini reproductor (como en la app)
        Positioned(
          right: ancho - g.pantalla.right + ancho * 0.05,
          bottom: alto - g.mini.top + alto * 0.012,
          child: Image.asset(personaje,
              height: alto * 0.17, filterQuality: FilterQuality.medium, excludeFromSemantics: true, gaplessPlayback: true),
        ),
        Positioned.fill(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(g.radioPantalla),
            child: CustomPaint(
              key: ValueKey('mascota-${mascota?.m.clave ?? ''}'),
              painter: _PintorMiniBarra(g, mascota, fraccion, s, t.$2),
            ),
          ),
        ),
      ]),
    );
  }
}

class _GeoTelefono {
  _GeoTelefono(this.z)
      : pantalla = Rect.fromLTWH(z.width * 0.045, z.width * 0.045, z.width * 0.91, z.height - z.width * 0.09),
        radioPantalla = z.width * 0.11 {
    final p = pantalla;
    mini = Rect.fromLTWH(p.left + p.width * 0.04, p.top + p.height * 0.76, p.width * 0.92, p.height * 0.10);
    barraMini = mini.bottom - mini.height * 0.16;
  }
  final Size z;
  final Rect pantalla;
  final double radioPantalla;
  late final Rect mini;
  late final double barraMini;
}

class _PintorTelefono extends CustomPainter {
  _PintorTelefono(this.capas, this.acento, this.g);
  final List<Color> capas;
  final Color acento;
  final _GeoTelefono g;

  @override
  void paint(Canvas canvas, Size z) {
    final fondo = capas[0], panel = capas[1], sup2 = capas[3], sup3 = capas[4];
    // el cuerpo del teléfono
    final cuerpo = RRect.fromRectAndRadius(Offset.zero & z, Radius.circular(z.width * 0.15));
    canvas.drawShadow(Path()..addRRect(cuerpo), Colors.black, 14, false);
    canvas.drawRRect(cuerpo, Paint()..color = const Color(0xFF0B0C10));
    canvas.drawRRect(cuerpo.deflate(1), Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5
      ..color = Colors.white.withValues(alpha: 0.14));
    final p = g.pantalla;
    final pr = RRect.fromRectAndRadius(p, Radius.circular(g.radioPantalla));
    canvas.save();
    canvas.clipRRect(pr);
    canvas.drawRect(p, Paint()..color = fondo);
    // el degradado del Inicio, que sale del acento
    canvas.drawRect(
        Rect.fromLTWH(p.left, p.top, p.width, p.height * 0.42),
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color.lerp(acento, fondo, 0.55)!, fondo.withValues(alpha: 0)],
          ).createShader(Rect.fromLTWH(p.left, p.top, p.width, p.height * 0.42)));
    canvas.drawRect(
        p,
        Paint()
          ..shader = RadialGradient(
            center: const Alignment(0.75, -1.05),
            radius: 1.1,
            colors: [acento.withValues(alpha: 0.12), Colors.transparent],
          ).createShader(p));
    final u = p.width / 100; // una "unidad" de la pantalla
    RRect caja(double x, double y, double w, double h, double r) =>
        RRect.fromRectAndRadius(Rect.fromLTWH(p.left + x * u, p.top + y * u, w * u, h * u), Radius.circular(r * u));
    final claro = Paint()..color = Colors.white.withValues(alpha: 0.88);
    final tenue = Paint()..color = Colors.white.withValues(alpha: 0.30);
    // la isla de la cámara y la hora
    canvas.drawRRect(caja(38, 3, 24, 5, 2.5), Paint()..color = Colors.black);
    canvas.drawRRect(caja(8, 4, 10, 3, 1.5), tenue);
    // el saludo
    canvas.drawRRect(caja(8, 15, 50, 6, 3), claro);
    canvas.drawRRect(caja(8, 24, 32, 3.5, 1.75), tenue);
    canvas.drawCircle(Offset(p.left + 88 * u, p.top + 18 * u), 5 * u, Paint()..color = acento);
    // filtros
    canvas.drawRRect(caja(8, 32, 20, 7, 3.5), Paint()..color = acento);
    canvas.drawRRect(caja(31, 32, 22, 7, 3.5), Paint()..color = sup3);
    canvas.drawRRect(caja(56, 32, 18, 7, 3.5), Paint()..color = sup3);
    // un carrusel de portadas
    canvas.drawRRect(caja(8, 46, 40, 3.5, 1.75), claro);
    for (var i = 0; i < 3; i++) {
      final r = caja(8 + i * 31, 53, 27, 27, 4);
      canvas.drawRRect(
          r,
          Paint()
            ..shader = LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color.lerp(acento, sup2, 0.2 + i * 0.25)!, Color.lerp(acento, fondo, 0.7 + i * 0.08)!],
            ).createShader(r.outerRect));
      canvas.drawRRect(caja(8 + i * 31, 82, 22, 3, 1.5), tenue);
    }
    // filas de canciones
    for (var i = 0; i < 3; i++) {
      final y = 93.0 + i * 15;
      canvas.drawRRect(caja(8, y, 11, 11, 2.5), Paint()..color = sup3);
      canvas.drawRRect(caja(23, y + 1.5, 42 - i * 6, 3.5, 1.75), claro);
      canvas.drawRRect(caja(23, y + 7, 26, 2.8, 1.4), tenue);
    }
    // el mini reproductor
    final mini = RRect.fromRectAndRadius(g.mini, Radius.circular(3 * u));
    canvas.drawRRect(mini, Paint()..color = Color.lerp(sup2, acento, 0.10)!);
    final mu = g.mini.height / 10;
    canvas.drawRRect(
        RRect.fromRectAndRadius(Rect.fromLTWH(g.mini.left + 1.4 * mu, g.mini.top + 1.4 * mu, 5.4 * mu, 5.4 * mu),
            Radius.circular(mu)),
        Paint()..color = acento);
    canvas.drawRRect(
        RRect.fromRectAndRadius(Rect.fromLTWH(g.mini.left + 8.5 * mu, g.mini.top + 2 * mu, g.mini.width * 0.42, 1.8 * mu),
            Radius.circular(mu)),
        claro);
    canvas.drawRRect(
        RRect.fromRectAndRadius(Rect.fromLTWH(g.mini.left + 8.5 * mu, g.mini.top + 4.8 * mu, g.mini.width * 0.26, 1.4 * mu),
            Radius.circular(mu)),
        tenue);
    canvas.drawCircle(Offset(g.mini.right - 4 * mu, g.mini.top + 4 * mu), 2.6 * mu, claro);
    // la barra de abajo
    final nav = Rect.fromLTWH(p.left, p.bottom - p.height * 0.105, p.width, p.height * 0.105);
    canvas.drawRect(nav, Paint()..color = panel);
    for (var i = 0; i < 4; i++) {
      final c = Offset(nav.left + nav.width * (0.125 + 0.25 * i), nav.top + nav.height * 0.42);
      canvas.drawCircle(c, 3.2 * u, Paint()..color = i == 0 ? Colors.white : Colors.white.withValues(alpha: 0.35));
      canvas.drawRRect(
          RRect.fromRectAndRadius(Rect.fromCenter(center: c + Offset(0, 7 * u), width: 10 * u, height: 2 * u), Radius.circular(u)),
          Paint()..color = Colors.white.withValues(alpha: i == 0 ? 0.6 : 0.2));
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _PintorTelefono old) => old.capas != capas || old.acento != acento || old.g.z != g.z;
}

/// La barra del mini reproductor del teléfono de juguete (con su mascotita).
class _PintorMiniBarra extends CustomPainter {
  _PintorMiniBarra(this.g, this.h, this.fraccion, this.s, this.acento);
  final _GeoTelefono g;
  final _Hoja? h;
  final double fraccion;
  final double s;
  final Color acento;

  @override
  void paint(Canvas canvas, Size z) {
    final x0 = g.mini.left + g.mini.width * 0.05, x1 = g.mini.right - g.mini.width * 0.05;
    final y = g.barraMini;
    _pintarBarra(canvas, x0, x1, y, fraccion, acento, grosor: max(2.0, g.z.width * 0.014));
    final m = h;
    if (m != null) {
      // la mascotita a escala del teléfono, algo más grande para que se luzca
      final escala = g.z.width / 412 * 2.1;
      _pintarMascota(canvas, m, x0 + (x1 - x0) * fraccion, y, escala, s, inicio: x0);
    }
  }

  @override
  bool shouldRepaint(covariant _PintorMiniBarra old) => true;
}

/// Una muestra redonda de un tema: su color y su personaje dentro.
class _Muestra extends StatelessWidget {
  const _Muestra({required this.tema, required this.lado});
  final String tema;
  final double lado;

  @override
  Widget build(BuildContext context) {
    final t = Aspecto.temas[tema]!;
    return Container(
      width: lado,
      height: lado,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: t.$3[2],
        border: Border.all(color: t.$2.withValues(alpha: 0.5), width: 1.5),
      ),
      padding: EdgeInsets.all(lado * 0.16),
      child: Image.asset(Aspecto.patronDe(tema)!, filterQuality: FilterQuality.medium, excludeFromSemantics: true),
    );
  }
}

// ------------------------------------------------------------------- fondos

/// El teléfono cambia de tema cada 2 segundos; a los lados, los temas que
/// vienen y los que ya pasaron.
class _IlusFondos extends StatelessWidget {
  const _IlusFondos({required this.e});
  final _Escena e;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: e.reloj,
        builder: (_, _) {
          final claves = Aspecto.temas.keys.toList();
          final n = claves.length;
          final i = (e.s / 2).floor() % n;
          final tema = claves[i];
          final t = Aspecto.temas[tema]!;
          String vecino(int d) => claves[(i + d + n) % n];
          return Stack(clipBehavior: Clip.none, alignment: Alignment.center, children: [
            Positioned.fill(child: CustomPaint(painter: _Adornos(e.s, t.$2, cuantos: 8, semilla: 2))),
            // a los lados: los temas de antes y los que siguen
            for (var k = 0; k < 3; k++) ...[
              Positioned(left: 14 + (k == 1 ? 0 : 14), top: 60 + k * 86.0, child: _Muestra(tema: vecino(-(k + 1)), lado: 58)),
              Positioned(right: 14 + (k == 1 ? 0 : 14), top: 60 + k * 86.0, child: _Muestra(tema: vecino(k + 1), lado: 58)),
            ],
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 520),
              switchInCurve: Curves.easeOutCubic,
              switchOutCurve: Curves.easeIn,
              transitionBuilder: (hijo, a) => FadeTransition(
                  opacity: a, child: ScaleTransition(scale: Tween(begin: 0.96, end: 1.0).animate(a), child: hijo)),
              child: _Telefono(key: ValueKey(tema), tema: tema, alto: 318, fraccion: 0.35),
            ),
            Positioned(
              bottom: 0,
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 300),
                child: Container(
                  key: ValueKey(tema),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                  decoration: BoxDecoration(
                    color: Color.lerp(t.$3[0], Colors.black, 0.2),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: t.$2.withValues(alpha: 0.7)),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Container(width: 8, height: 8, decoration: BoxDecoration(color: t.$2, shape: BoxShape.circle)),
                    const SizedBox(width: 6),
                    Text(t.$1, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
                  ]),
                ),
              ),
            ),
          ]);
        },
      );
}

// ------------------------------------------------------------------- juntos

/// El mismo personaje en el fondo y caminando por la barra del mini
/// reproductor; cambia de pareja cada 6 segundos.
class _IlusJuntos extends StatelessWidget {
  const _IlusJuntos({required this.e});
  final _Escena e;

  static const _parejas = ['kuromi', 'pikachu', 'cinnamoroll', 'nyan', 'totoro', 'hellokitty', 'kirby', 'capibara'];
  static const _periodo = 6.0;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: e.reloj,
        builder: (_, _) {
          final s = e.s;
          final k = (s / _periodo).floor();
          final tema = _parejas[k % _parejas.length];
          final t = Aspecto.temas[tema]!;
          final fraccion = 0.05 + 0.9 * ((s % _periodo) / _periodo);
          final h = e.de(tema);
          return Stack(clipBehavior: Clip.none, alignment: Alignment.center, children: [
            Positioned.fill(child: CustomPaint(painter: _Adornos(s, t.$2, cuantos: 8, semilla: 5))),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 450),
              transitionBuilder: (hijo, a) => FadeTransition(opacity: a, child: hijo),
              layoutBuilder: (actual, previos) => Stack(alignment: Alignment.center, children: [...previos, ?actual]),
              child: _Telefono(key: ValueKey(tema), tema: tema, alto: 336, mascota: h, fraccion: fraccion, s: s),
            ),
            // las dos etiquetas: el fondo arriba, la barra abajo
            Positioned(
              right: 8,
              top: 150,
              child: _Etiqueta(icono: Icons.wallpaper_rounded, texto: 'Su fondo', color: t.$2),
            ),
            Positioned(
              left: 8,
              bottom: 40,
              child: _Etiqueta(icono: Icons.pets_rounded, texto: 'Su mascotita', color: t.$2),
            ),
            Positioned(
              bottom: 2,
              child: Text(t.$1,
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Color.lerp(t.$2, Colors.white, 0.4))),
            ),
          ]);
        },
      );
}

class _Etiqueta extends StatelessWidget {
  const _Etiqueta({required this.icono, required this.texto, required this.color});
  final IconData icono;
  final String texto;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.55),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withValues(alpha: 0.8), width: 1.5),
          boxShadow: const [BoxShadow(color: Color(0x50000000), blurRadius: 10, offset: Offset(0, 4))],
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icono, size: 15, color: color),
          const SizedBox(width: 5),
          Text(texto, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
        ]),
      );
}

// ------------------------------------------------------------------- cierre

/// Un desfile de mascotitas sobre dos barras, con corazones que suben.
class _IlusCierre extends StatelessWidget {
  const _IlusCierre({required this.e});
  final _Escena e;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: e.reloj,
        builder: (_, _) {
          final s = e.s;
          final claves = [
            for (var fila = 0; fila < 2; fila++)
              for (var k = 0; k < 5; k++) e.enPosicion(_PintorDesfile.indice(fila, k, s))?.m.clave ?? '',
          ];
          return Stack(children: [
            Positioned.fill(child: CustomPaint(painter: _CorazonesQueSuben(s))),
            Positioned(
              left: 0,
              right: 0,
              top: 70,
              child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: _cristal(radio: 30),
                  child: const Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.favorite_rounded, color: Color(0xFFFF77B7), size: 20),
                    SizedBox(width: 8),
                    Flexible(
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text('¡Disfruta lo nuevo!', maxLines: 1, style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
                      ),
                    ),
                  ]),
                ),
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              top: 140,
              height: 210,
              child: ClipRect(
                child: CustomPaint(
                  key: ValueKey('mascotas-${claves.join(',')}'),
                  size: Size.infinite,
                  painter: _PintorDesfile(e, s),
                ),
              ),
            ),
          ]);
        },
      );
}

/// Dos filas de cinco mascotitas que cruzan de izquierda a derecha; al salir
/// por la derecha vuelven a entrar como otra mascotita.
class _PintorDesfile extends CustomPainter {
  _PintorDesfile(this.e, this.s);
  final _Escena e;
  final double s;

  static const _paso = 88.0;
  static const _largo = _paso * 5; // el lienzo y un margen a cada lado: entran y salen sin verse
  // px por segundo: una pasada entera en 14,4 s y en 18 s (dividen la vuelta del reloj)
  static const _velocidad = [_largo / 14.4, _largo / 18];

  static double _recorrido(int fila, double s) => s * _velocidad[fila] + fila * 40;

  static int indice(int fila, int k, double s) {
    final d = _recorrido(fila, s) + k * _paso;
    return fila * 5 + k + 10 * (d / _largo).floor();
  }

  @override
  void paint(Canvas canvas, Size z) {
    const colores = [Color(0xFFFF8FB8), Color(0xFFB4A1FF)];
    for (var fila = 0; fila < 2; fila++) {
      final y = 82.0 + fila * 104;
      _pintarBarra(canvas, 8, z.width - 8, y, 1, colores[fila].withValues(alpha: 0.55), grosor: 3.5);
      for (var k = 0; k < 5; k++) {
        final d = _recorrido(fila, s) + k * _paso;
        final x = (d % _largo) - 40;
        final h = e.enPosicion(indice(fila, k, s));
        // sin estela y con el arcoíris corto: van en fila y se taparían unas a otras
        if (h != null) {
          _pintarMascota(canvas, _Hoja(h.m)..hoja = h.hoja, x, y, 1.25, s + k * 0.37 + fila * 0.11,
              inicio: max(0.0, x - _paso * 0.62));
        }
      }
    }
  }

  @override
  bool shouldRepaint(covariant _PintorDesfile old) => true;
}

class _CorazonesQueSuben extends CustomPainter {
  _CorazonesQueSuben(this.s);
  final double s;

  @override
  void paint(Canvas canvas, Size z) {
    const colores = [Color(0xFFFF77B7), Color(0xFFFF8FB8), Color(0xFFB4A1FF), Color(0xFFF5C542)];
    for (var i = 0; i < 14; i++) {
      final x = z.width * ((i * 0.618034 + 0.05) % 1) + sin(2 * pi * (s / 5 + i * 0.13)) * 8;
      final p = ((s / 9) * (1 + (i % 3) * 0.25) + i * 0.29) % 1;
      final y = z.height * (1.02 - 1.05 * p);
      final a = pow(sin(pi * p), 1.3).toDouble() * 0.75;
      _pintarPixel(canvas, i % 4 == 3 ? _estrella : _corazon, Offset(x, y), 2.4 + (i % 3) * 0.5,
          colores[i % colores.length].withValues(alpha: a));
    }
  }

  @override
  bool shouldRepaint(covariant _CorazonesQueSuben old) => old.s != s;
}

// --------------------------------------------------------------------- fondo

/// El fondo de toda la presentación: un degradado del color de la diapositiva,
/// dos luces suaves que se mueven despacio y estrellitas en pixel art.
class _FondoPixel extends CustomPainter {
  _FondoPixel(this.s, this.color);
  final double s;
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
          colors: [Color.lerp(color, C.fondo, 0.62)!, Color.lerp(color, C.fondo, 0.87)!, C.fondo],
          stops: const [0, 0.5, 0.97],
        ).createShader(r),
    );
    final grande = max(z.width, z.height);
    final luces = <(double, double, Color, double, double)>[
      (0.2 + 0.5 * _onda(16), 0.14 + 0.1 * _onda(8, 0.2), Color.lerp(color, Colors.white, 0.3)!, 0.26, 0.5),
      (0.85 - 0.4 * _onda(18, 0.3), 0.55 + 0.12 * _onda(9, 0.5), Color.lerp(color, const Color(0xFF8B6CFF), 0.5)!, 0.18, 0.55),
    ];
    for (final (x, y, col, a, rad) in luces) {
      final o = Offset(z.width * x, z.height * y);
      final rr = grande * rad;
      canvas.drawCircle(o, rr,
          Paint()..shader = RadialGradient(colors: [col.withValues(alpha: a), col.withValues(alpha: 0)]).createShader(Rect.fromCircle(center: o, radius: rr)));
    }
    // estrellitas que titilan (cuadraditos, como en un juego viejo)
    final p = Paint();
    for (var i = 0; i < 26; i++) {
      final x = z.width * ((i * 0.618034 + 0.03) % 1);
      final y = z.height * ((i * 0.7548776 + 0.09) % 1);
      final b = pow(0.5 + 0.5 * sin(2 * pi * (s / (3 + i % 4) + i * 0.37)), 3).toDouble();
      final t = 2.0 + (i % 3);
      p.color = Colors.white.withValues(alpha: 0.08 + 0.4 * b);
      canvas.drawRect(Rect.fromCenter(center: Offset(x, y), width: t, height: t), p);
      if (i % 4 == 0 && b > 0.5) {
        p.color = Colors.white.withValues(alpha: 0.25 * b);
        canvas.drawRect(Rect.fromCenter(center: Offset(x, y), width: t * 3, height: t / 2), p);
        canvas.drawRect(Rect.fromCenter(center: Offset(x, y), width: t / 2, height: t * 3), p);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _FondoPixel old) => old.s != s || old.color != color;
}
