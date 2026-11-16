import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:ui' as ui;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/mixes.dart';
import '../comunes.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';

// ======================================================================
// Tu resumen: historias a pantalla completa (semana, mes o año)
// ======================================================================

/// "Tu resumen": como el Wrapped, pero cuando quieras. Se abre con
/// [ResumenPagina.abrir] (encima de todo, sin barra de abajo).
class ResumenPagina extends StatefulWidget {
  const ResumenPagina({super.key, this.periodo = PeriodoResumen.mes, this.historial});

  final PeriodoResumen periodo;

  /// Para pruebas o vistas previas: si se da, no se lee la coleccion.
  final List<Escucha>? historial;

  static Future<void> abrir(BuildContext context, {PeriodoResumen periodo = PeriodoResumen.mes}) {
    Haptico.toque();
    return Navigator.of(context, rootNavigator: true).push(PageRouteBuilder<void>(
      transitionDuration: const Duration(milliseconds: 420),
      reverseTransitionDuration: const Duration(milliseconds: 280),
      pageBuilder: (_, _, _) => ResumenPagina(periodo: periodo),
      transitionsBuilder: (_, a, _, hijo) {
        final c = CurvedAnimation(parent: a, curve: Curves.easeOutCubic);
        return FadeTransition(
          opacity: c,
          child: ScaleTransition(scale: Tween(begin: 0.94, end: 1.0).animate(c), child: hijo),
        );
      },
    ));
  }

  @override
  State<ResumenPagina> createState() => _ResumenPaginaState();
}

/// Una historia: sus colores y lo que pinta (con la animacion de entrada).
class _Historia {
  const _Historia(this.colores, this.pintar, {this.pista});
  final List<Color> colores;
  final Widget Function(Animation<double> entrada) pintar;

  /// Si la historia es de una cancion, se puede poner desde aqui.
  final Json? pista;
}

class _ResumenPaginaState extends State<ResumenPagina> with TickerProviderStateMixin {
  /// En el navegador (con ratón y pantalla grande) se lee con más calma.
  static Duration get _duracion => Duration(milliseconds: kIsWeb ? 20000 : 6500);

  late PeriodoResumen _periodo = widget.periodo;
  List<Escucha>? _historial;
  Resumen? _resumen;
  String? _error;
  List<_Historia> _historias = [];
  int _indice = 0;
  bool _pausado = false;
  bool _compartiendo = false;
  double _arrastre = 0;

  late final AnimationController _avance = AnimationController(vsync: this, duration: _duracion)
    ..addStatusListener((s) {
      if (s == AnimationStatus.completed) _ir(1, auto: true);
    });
  late final AnimationController _entrada =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1500));
  late final AnimationController _fondo =
      AnimationController(vsync: this, duration: const Duration(seconds: 22))..repeat();
  final _claveTarjeta = GlobalKey();
  final _claveCompartir = GlobalKey();

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _avance.dispose();
    _entrada.dispose();
    _fondo.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    try {
      _historial ??= widget.historial ?? await Historial.leer(Caudal.leer(context).coleccion);
      if (!mounted) return;
      final r = Resumen.calcular(_historial!, _periodo);
      setState(() {
        _resumen = r;
        _error = null;
        _historias = _armar(r);
        _indice = 0;
      });
      _precargar(r);
      _empezar();
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  void _precargar(Resumen r) {
    final urls = <String>{
      for (final c in r.topCanciones) '${c.pista['miniatura'] ?? ''}',
      for (final a in r.topArtistas) a.miniatura,
      if (r.cancionDelMes != null) '${r.cancionDelMes!.pista['miniatura'] ?? ''}',
    }.where((u) => u.startsWith('http'));
    for (final u in urls) {
      precacheImage(CachedNetworkImageProvider(u), context).catchError((_) {});
    }
  }

  void _empezar() {
    _entrada.forward(from: 0);
    _avance.forward(from: 0);
    if (_pausado) _avance.stop();
  }

  void _ir(int paso, {bool auto = false}) {
    final nuevo = _indice + paso;
    if (nuevo < 0) {
      _empezar();
      return;
    }
    if (nuevo >= _historias.length) {
      // en la ultima se queda quieta; tocar de nuevo cierra
      if (!auto) Navigator.of(context).maybePop();
      return;
    }
    if (!auto) Haptico.seleccion();
    setState(() => _indice = nuevo);
    _empezar();
  }

  void _pausar(bool si) {
    _pausado = si;
    if (si) {
      _avance.stop();
    } else if (!_compartiendo) {
      _avance.forward();
    }
  }

  void _cambiarPeriodo(PeriodoResumen nuevo) {
    if (nuevo == _periodo) return;
    Haptico.seleccion();
    setState(() => _periodo = nuevo);
    _cargar();
  }

  // ------------------------------------------------------------ compartir

  Future<void> _compartir() async {
    if (_compartiendo) return;
    final caja = _claveCompartir.currentContext?.findRenderObject() as RenderBox?;
    final origen = caja == null ? null : caja.localToGlobal(Offset.zero) & caja.size;
    setState(() => _compartiendo = true);
    _avance.stop();
    Haptico.toque();
    try {
      await WidgetsBinding.instance.endOfFrame;
      final ro = _claveTarjeta.currentContext?.findRenderObject();
      if (ro is! RenderRepaintBoundary) throw StateError('la tarjeta aun no se pinto');
      if (!mounted) return;
      final escala = min(3.0, max(2.0, MediaQuery.devicePixelRatioOf(context)));
      final imagen = await ro.toImage(pixelRatio: escala);
      final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
      imagen.dispose();
      if (datos == null) throw StateError('no se pudo dibujar la imagen');
      final bytes = datos.buffer.asUint8List();
      final nombre = 'caudal_resumen_${DateTime.now().millisecondsSinceEpoch}.png';
      XFile adjunto;
      if (kIsWeb) {
        adjunto = XFile.fromData(bytes, mimeType: 'image/png', name: nombre);
      } else {
        final dir = await getTemporaryDirectory();
        final archivo = File(p.join(dir.path, nombre));
        await archivo.writeAsBytes(bytes, flush: true);
        adjunto = XFile(archivo.path, mimeType: 'image/png');
      }
      await SharePlus.instance.share(ShareParams(
        files: [adjunto],
        text: 'Mi resumen de ${_periodo.rango} en Caudal',
        sharePositionOrigin: origen,
      ));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.maybeOf(context)
            ?.showSnackBar(SnackBar(content: Text('No se pudo compartir: $e')));
      }
    } finally {
      if (mounted) {
        setState(() => _compartiendo = false);
        if (!_pausado) _avance.forward();
      }
    }
  }

  void _escuchar(Json pista) {
    final s = Caudal.leer(context);
    _pausar(true);
    s.reproducirPista(context, pista, contexto: {'tipo': 'resumen', 'id': _periodo.name, 'titulo': 'Tu resumen'});
  }

  // ------------------------------------------------------------ historias

  List<_Historia> _armar(Resumen r) {
    if (r.vacio) {
      return [
        _Historia(const [Color(0xFF1B1F27), Color(0xFF7C5CFF), Color(0xFF22D3EE)],
            (a) => _HistoriaVacia(periodo: r.periodo, entrada: a)),
      ];
    }
    final top = r.topCanciones.isEmpty ? null : r.topCanciones.first;
    final delMes = r.cancionDelMes;
    return [
      _Historia(const [Color(0xFF0B1B3A), Color(0xFF7C5CFF), Color(0xFF22D3EE)],
          (a) => _HistoriaPortada(r: r, entrada: a, fondo: _fondo)),
      _Historia(const [Color(0xFF051B22), Color(0xFF22D3EE), Color(0xFF2BD576)],
          (a) => _HistoriaMinutos(r: r, entrada: a)),
      if (top != null)
        _Historia(const [Color(0xFF2A0A1C), Color(0xFFFF5C8A), Color(0xFFFFB443)],
            (a) => _HistoriaCancion(
                  entrada: a, fondo: _fondo, puesto: top,
                  antetitulo: 'Tu canción número uno',
                  pie: 'La pusiste ${_veces(top.veces)} en ${r.periodo.rango}.',
                ),
            pista: top.pista),
      if (r.topCanciones.length > 1)
        _Historia(const [Color(0xFF140B33), Color(0xFF7C5CFF), Color(0xFFFF5C8A)],
            (a) => _HistoriaTopCanciones(r: r, entrada: a)),
      if (r.topArtistas.isNotEmpty)
        _Historia(const [Color(0xFF241405), Color(0xFFFFB443), Color(0xFFFF7A45)],
            (a) => _HistoriaArtistas(r: r, entrada: a)),
      _Historia(const [Color(0xFF07121F), Color(0xFF3B82F6), Color(0xFF7C5CFF)],
          (a) => _HistoriaHoras(r: r, entrada: a)),
      _Historia(const [Color(0xFF260A05), Color(0xFFFF7A45), Color(0xFFFFB443)],
          (a) => _HistoriaRacha(r: r, entrada: a, fondo: _fondo)),
      if (delMes != null && (top == null || delMes.pista['clave'] != top.pista['clave'] || r.periodo != PeriodoResumen.mes))
        _Historia(const [Color(0xFF05201A), Color(0xFF2BD576), Color(0xFF22D3EE)],
            (a) => _HistoriaCancion(
                  entrada: a, fondo: _fondo, puesto: delMes,
                  antetitulo: 'Tu canción de ${r.nombreMes}',
                  pie: 'Sonó ${_veces(delMes.veces)} este mes. Es oficialmente tuya.',
                ),
            pista: delMes.pista),
      if (r.descubrimientos.isNotEmpty)
        _Historia(const [Color(0xFF1F0A2E), Color(0xFFE879F9), Color(0xFF7C5CFF)],
            (a) => _HistoriaDescubrimientos(r: r, entrada: a)),
      _Historia(const [Color(0xFF06070A), Color(0xFF22D3EE), Color(0xFF7C5CFF)],
          (a) => _HistoriaFinal(r: r, entrada: a)),
    ];
  }

  // ------------------------------------------------------------ pintar

  @override
  Widget build(BuildContext context) {
    final r = _resumen;
    final relleno = MediaQuery.paddingOf(context);
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Focus(
        autofocus: true,
        onKeyEvent: (_, e) {
          if (e is! KeyDownEvent || r == null) return KeyEventResult.ignored;
          final k = e.logicalKey;
          if (k == LogicalKeyboardKey.arrowRight) {
            _ir(1);
          } else if (k == LogicalKeyboardKey.arrowLeft) {
            _ir(-1);
          } else if (k == LogicalKeyboardKey.space) {
            setState(() => _pausar(!_pausado));
          } else if (k == LogicalKeyboardKey.escape) {
            Navigator.of(context).maybePop();
          } else {
            return KeyEventResult.ignored;
          }
          return KeyEventResult.handled;
        },
        child: Scaffold(
        backgroundColor: Colors.black,
        body: _error != null
            ? _Aviso(texto: 'No se pudo armar tu resumen.\n$_error', alCerrar: () => Navigator.of(context).pop())
            : r == null || _historias.isEmpty
                ? const _Cargando()
                : GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTapUp: (d) {
                      final ancho = MediaQuery.sizeOf(context).width;
                      _ir(d.globalPosition.dx < ancho * 0.3 ? -1 : 1);
                    },
                    onLongPressStart: (_) => _pausar(true),
                    onLongPressEnd: (_) => _pausar(false),
                    onVerticalDragUpdate: (d) => setState(() => _arrastre = max(0, _arrastre + d.delta.dy)),
                    onVerticalDragEnd: (d) {
                      if (_arrastre > 140 || (d.primaryVelocity ?? 0) > 900) {
                        Navigator.of(context).maybePop();
                      } else {
                        setState(() => _arrastre = 0);
                      }
                    },
                    child: AnimatedContainer(
                      duration: Duration(milliseconds: _arrastre == 0 ? 220 : 0),
                      curve: Curves.easeOutCubic,
                      transform: Matrix4.translationValues(0, _arrastre, 0)
                        ..scaleByDouble(1 - min(_arrastre, 300) / 1800, 1 - min(_arrastre, 300) / 1800, 1, 1),
                      transformAlignment: Alignment.center,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(_arrastre > 0 ? 28 : 0),
                        child: Stack(fit: StackFit.expand, children: [
                          _tarjeta(r, relleno),
                          _controles(relleno),
                        ]),
                      ),
                    ),
                  ),
        ),
      ),
    );
  }

  /// La tarjeta que se comparte: fondo, contenido y la firma de Caudal.
  Widget _tarjeta(Resumen r, EdgeInsets relleno) {
    final h = _historias[_indice];
    return RepaintBoundary(
      key: _claveTarjeta,
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 480),
        switchInCurve: Curves.easeOutCubic,
        switchOutCurve: Curves.easeInCubic,
        transitionBuilder: (hijo, a) => FadeTransition(
          opacity: a,
          child: ScaleTransition(scale: Tween(begin: 1.06, end: 1.0).animate(a), child: hijo),
        ),
        child: Stack(key: ValueKey('${_periodo.name}-$_indice'), fit: StackFit.expand, children: [
          RepaintBoundary(child: _Aurora(colores: h.colores, tiempo: _fondo)),
          Padding(
            padding: EdgeInsets.fromLTRB(24, relleno.top + 92, 24, relleno.bottom + 96),
            // en pantallas bajas (teléfono pequeño o en horizontal) la historia
            // se encoge entera en vez de desbordar
            child: LayoutBuilder(builder: (_, c) {
              const alturaDiseno = 700.0;
              if (!c.hasBoundedHeight || c.maxHeight >= alturaDiseno) return h.pintar(_entrada);
              final k = c.maxHeight / alturaDiseno;
              return FittedBox(
                fit: BoxFit.contain,
                alignment: Alignment.topLeft,
                child: SizedBox(width: c.maxWidth / k, height: alturaDiseno, child: h.pintar(_entrada)),
              );
            }),
          ),
          Positioned(
            left: 0, right: 0, bottom: relleno.bottom + 34,
            child: const _Firma(),
          ),
        ]),
      ),
    );
  }

  Widget _controles(EdgeInsets relleno) {
    final h = _historias[_indice];
    return Stack(children: [
      // arriba: el avance de cada historia, el periodo y cerrar
      Positioned(
        left: 10, right: 10, top: relleno.top + 8,
        child: Column(children: [
          AnimatedBuilder(
            animation: _avance,
            builder: (_, _) => Row(children: [
              for (var i = 0; i < _historias.length; i++)
                Expanded(
                  child: Container(
                    height: 3,
                    margin: const EdgeInsets.symmetric(horizontal: 2),
                    decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.28), borderRadius: BorderRadius.circular(2)),
                    alignment: Alignment.centerLeft,
                    child: FractionallySizedBox(
                      widthFactor: i < _indice ? 1 : (i == _indice ? _avance.value : 0),
                      child: Container(
                        decoration:
                            BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(2)),
                      ),
                    ),
                  ),
                ),
            ]),
          ),
          const SizedBox(height: 12),
          Row(children: [
            const SizedBox(width: 6),
            Expanded(
              child: Align(
                alignment: Alignment.centerLeft,
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: _SelectorPeriodo(actual: _periodo, alCambiar: _cambiarPeriodo),
                ),
              ),
            ),
            IconButton(
              tooltip: _pausado ? 'Seguir' : 'Pausar',
              onPressed: () => setState(() => _pausar(!_pausado)),
              icon: Icon(_pausado ? Icons.play_arrow_rounded : Icons.pause_rounded, color: Colors.white),
            ),
            IconButton(
              tooltip: 'Cerrar',
              onPressed: () => Navigator.of(context).maybePop(),
              icon: const Icon(Icons.close_rounded, color: Colors.white, size: 28),
            ),
          ]),
        ]),
      ),
      // con ratón no hay "tocar el borde": flechas visibles para ir atrás y adelante
      if (kIsWeb || MediaQuery.sizeOf(context).width >= 700) ...[
        if (_indice > 0)
          Positioned(left: 12, top: 0, bottom: 0, child: Center(child: _Flecha(Icons.chevron_left_rounded, 'Anterior', () => _ir(-1)))),
        if (_indice < _historias.length - 1)
          Positioned(right: 12, top: 0, bottom: 0, child: Center(child: _Flecha(Icons.chevron_right_rounded, 'Siguiente', () => _ir(1)))),
      ],
      // abajo: escuchar (si es una cancion) y compartir
      Positioned(
        left: 20, right: 20, bottom: relleno.bottom + 22,
        child: Row(children: [
          if (h.pista != null)
            Flexible(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: _Pastilla(
                  icono: Icons.play_arrow_rounded,
                  texto: 'Escuchar',
                  claro: false,
                  alPulsar: () => _escuchar(h.pista!),
                ),
              ),
            ),
          const Spacer(),
          Flexible(
            child: FittedBox(
              fit: BoxFit.scaleDown,
              child: _Pastilla(
                key: _claveCompartir,
                icono: _compartiendo ? null : Icons.ios_share_rounded,
                texto: _compartiendo ? 'Preparando…' : 'Compartir',
                claro: true,
                alPulsar: _compartir,
              ),
            ),
          ),
        ]),
      ),
    ]);
  }
}

class _Flecha extends StatelessWidget {
  const _Flecha(this.icono, this.texto, this.alPulsar);
  final IconData icono;
  final String texto;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) => IconButton(
        tooltip: texto,
        onPressed: alPulsar,
        style: IconButton.styleFrom(backgroundColor: Colors.black38, foregroundColor: Colors.white),
        icon: Icon(icono, size: 32),
      );
}

String _veces(int n) => n == 1 ? 'una vez' : '$n veces';

String _miles(int n) {
  final s = '$n';
  final b = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write('.');
    b.write(s[i]);
  }
  return b.toString();
}

const _mesesCortos = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

String _fechaCorta(DateTime f) => '${f.day} ${_mesesCortos[f.month - 1]}';

String _hora(int h) => '${h.toString().padLeft(2, '0')}:00';

// ======================================================================
// Piezas de las historias
// ======================================================================

/// Animacion de entrada escalonada: [desde]..[hasta] dentro de 0..1.
Animation<double> _tramo(Animation<double> a, double desde, double hasta, [Curve curva = Curves.easeOutCubic]) =>
    CurvedAnimation(parent: a, curve: Interval(desde, hasta, curve: curva));

/// Sube y aparece.
class _Entra extends StatelessWidget {
  const _Entra({required this.a, required this.desde, required this.child, this.hasta, this.dy = 28});
  final Animation<double> a;
  final double desde;
  final double? hasta;
  final double dy;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final t = _tramo(a, desde, hasta ?? min(1.0, desde + 0.45));
    return AnimatedBuilder(
      animation: t,
      builder: (_, hijo) => Opacity(
        opacity: t.value.clamp(0.0, 1.0),
        child: Transform.translate(offset: Offset(0, (1 - t.value) * dy), child: hijo),
      ),
      child: child,
    );
  }
}

/// Numero que cuenta desde cero.
class _Contador extends StatelessWidget {
  const _Contador({required this.a, required this.valor, required this.estilo, this.desde = 0.1});
  final Animation<double> a;
  final int valor;
  final TextStyle estilo;
  final double desde;

  @override
  Widget build(BuildContext context) {
    final t = _tramo(a, desde, min(1.0, desde + 0.7), Curves.easeOutExpo);
    return AnimatedBuilder(
      animation: t,
      builder: (_, _) => FittedBox(
        fit: BoxFit.scaleDown,
        child: Text(_miles((valor * t.value).round()), maxLines: 1, style: estilo),
      ),
    );
  }
}

const _antetitulo = TextStyle(
    fontSize: 15, fontWeight: FontWeight.w800, letterSpacing: 1.6, color: Colors.white70, height: 1.2);
const _titular = TextStyle(
    fontSize: 38, fontWeight: FontWeight.w900, letterSpacing: -1.2, color: Colors.white, height: 1.02);
const _cuerpo = TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: Colors.white, height: 1.35);

/// Texto con degradado (para los numeros grandes).
class _Degradado extends StatelessWidget {
  const _Degradado({required this.child, required this.colores});
  final Widget child;
  final List<Color> colores;

  @override
  Widget build(BuildContext context) => ShaderMask(
        blendMode: BlendMode.srcIn,
        shaderCallback: (r) => LinearGradient(colors: colores, begin: Alignment.topLeft, end: Alignment.bottomRight)
            .createShader(r),
        child: child,
      );
}

class _HistoriaPortada extends StatelessWidget {
  const _HistoriaPortada({required this.r, required this.entrada, required this.fondo});
  final Resumen r;
  final Animation<double> entrada;
  final Animation<double> fondo;

  @override
  Widget build(BuildContext context) {
    final portadas = [
      for (final c in r.topCanciones) '${c.pista['miniatura'] ?? ''}',
    ].where((u) => u.isNotEmpty).toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Expanded(
        child: _Entra(
          a: entrada, desde: 0.0, hasta: 0.6, dy: 60,
          child: Center(child: _Orbita(portadas: portadas, tiempo: fondo)),
        ),
      ),
      _Entra(a: entrada, desde: 0.2, child: Text(r.periodo.nombre.toUpperCase(), style: _antetitulo)),
      const SizedBox(height: 10),
      _Entra(
        a: entrada, desde: 0.28,
        child: const _Degradado(
          colores: [Colors.white, Color(0xFF67E8F9), Color(0xFFC4B5FD)],
          child: Text('Tu resumen', style: TextStyle(
              fontSize: 64, fontWeight: FontWeight.w900, letterSpacing: -2.5, height: 0.95)),
        ),
      ),
      const SizedBox(height: 14),
      _Entra(
        a: entrada, desde: 0.4,
        child: Text('${_fechaCorta(r.desde)} – ${_fechaCorta(r.hasta)}  ·  ${_miles(r.escuchas)} escuchas',
            style: _cuerpo.copyWith(color: Colors.white70)),
      ),
      const SizedBox(height: 6),
      _Entra(
        a: entrada, desde: 0.5,
        child: Text('Toca para empezar. Mantén pulsado para pausar.',
            style: _cuerpo.copyWith(fontSize: 14, color: Colors.white54)),
      ),
    ]);
  }
}

/// Las portadas de tus canciones girando despacio.
class _Orbita extends StatelessWidget {
  const _Orbita({required this.portadas, required this.tiempo});
  final List<String> portadas;
  final Animation<double> tiempo;

  @override
  Widget build(BuildContext context) {
    if (portadas.isEmpty) {
      return const Icon(Icons.graphic_eq_rounded, size: 120, color: Colors.white);
    }
    return LayoutBuilder(builder: (_, c) {
      final lado = min(c.maxWidth, c.maxHeight);
      final radio = lado * 0.32;
      final tam = lado * 0.3;
      return SizedBox(
        width: lado,
        height: lado,
        child: AnimatedBuilder(
          animation: tiempo,
          builder: (_, _) {
            final giro = tiempo.value * 2 * pi;
            final n = portadas.length;
            final piezas = <(double, Widget)>[];
            for (var i = 0; i < n; i++) {
              final ang = giro + i * 2 * pi / n;
              final z = (sin(ang) + 1) / 2; // 0 detras, 1 delante
              final escala = 0.7 + 0.45 * z;
              piezas.add((
                z,
                Positioned(
                  left: lado / 2 + cos(ang) * radio - tam / 2,
                  top: lado / 2 + sin(ang) * radio * 0.45 - tam / 2,
                  child: Transform.scale(
                    scale: escala,
                    child: Opacity(
                      opacity: 0.55 + 0.45 * z,
                      child: DecoratedBox(
                        decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), boxShadow: [
                          BoxShadow(color: Colors.black.withValues(alpha: 0.45), blurRadius: 24, offset: const Offset(0, 10)),
                        ]),
                        child: Portada(url: portadas[i], lado: tam, radio: 10),
                      ),
                    ),
                  ),
                ),
              ));
            }
            piezas.sort((a, b) => a.$1.compareTo(b.$1));
            return Stack(clipBehavior: Clip.none, children: [for (final x in piezas) x.$2]);
          },
        ),
      );
    });
  }
}

class _HistoriaMinutos extends StatelessWidget {
  const _HistoriaMinutos({required this.r, required this.entrada});
  final Resumen r;
  final Animation<double> entrada;

  @override
  Widget build(BuildContext context) {
    final horas = r.minutos / 60;
    final equivale = horas >= 48
        ? 'Eso son ${(horas / 24).toStringAsFixed(1).replaceAll('.', ',')} días enteros de música.'
        : horas >= 2
            ? 'Eso son ${horas.round()} horas: ${(horas / 1.5).floor()} películas.'
            : 'Una buena banda sonora para empezar.';
    final cambio = r.cambio;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
      _Entra(a: entrada, desde: 0, child: Text('EN ${r.periodo.rango.toUpperCase()} ESCUCHASTE', style: _antetitulo)),
      const SizedBox(height: 8),
      _Degradado(
        colores: const [Colors.white, Color(0xFF67E8F9), Color(0xFF86EFAC)],
        child: _Contador(a: entrada, valor: r.minutos, desde: 0.05, estilo: const TextStyle(
            fontSize: 120, fontWeight: FontWeight.w900, letterSpacing: -6, height: 1)),
      ),
      _Entra(a: entrada, desde: 0.25, child: const Text('minutos de música', style: _titular)),
      const SizedBox(height: 18),
      _Entra(a: entrada, desde: 0.4, child: Text(equivale, style: _cuerpo)),
      if (cambio != null) ...[
        const SizedBox(height: 14),
        _Entra(
          a: entrada, desde: 0.5,
          child: _Chip(
            icono: cambio >= 0 ? Icons.trending_up_rounded : Icons.trending_down_rounded,
            texto: cambio == 0
                ? 'Igual que el período anterior'
                : '${cambio > 0 ? '+' : '−'}${cambio.abs()} % frente al período anterior',
          ),
        ),
      ],
      const SizedBox(height: 28),
      Row(children: [
        Expanded(child: _Entra(a: entrada, desde: 0.55, child: _Dato(valor: r.escuchas, texto: 'escuchas', a: entrada))),
        Expanded(child: _Entra(a: entrada, desde: 0.62, child: _Dato(valor: r.cancionesDistintas, texto: 'canciones', a: entrada))),
        Expanded(child: _Entra(a: entrada, desde: 0.69, child: _Dato(valor: r.artistasDistintos, texto: 'artistas', a: entrada))),
      ]),
    ]);
  }
}

class _Dato extends StatelessWidget {
  const _Dato({required this.valor, required this.texto, required this.a});
  final int valor;
  final String texto;
  final Animation<double> a;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _Contador(a: a, valor: valor, desde: 0.55, estilo: const TextStyle(
            fontSize: 34, fontWeight: FontWeight.w900, color: Colors.white, letterSpacing: -1)),
        Text(texto, style: const TextStyle(fontSize: 14, color: Colors.white70, fontWeight: FontWeight.w600)),
      ]);
}

class _Chip extends StatelessWidget {
  const _Chip({required this.icono, required this.texto});
  final IconData icono;
  final String texto;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(40),
          border: Border.all(color: Colors.white.withValues(alpha: 0.22)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icono, color: Colors.white, size: 18),
          const SizedBox(width: 8),
          Flexible(child: Text(texto, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700))),
        ]),
      );
}

/// Una cancion protagonista: su portada con brillo y un vinilo que asoma.
class _HistoriaCancion extends StatelessWidget {
  const _HistoriaCancion({
    required this.entrada, required this.fondo, required this.puesto,
    required this.antetitulo, required this.pie,
  });
  final Animation<double> entrada;
  final Animation<double> fondo;
  final PuestoCancion puesto;
  final String antetitulo;
  final String pie;

  @override
  Widget build(BuildContext context) {
    final pista = puesto.pista;
    final url = '${pista['miniatura'] ?? ''}';
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _Entra(a: entrada, desde: 0, child: Text(antetitulo.toUpperCase(), style: _antetitulo)),
      const SizedBox(height: 18),
      Expanded(
        child: LayoutBuilder(builder: (_, c) {
          final lado = min(c.maxWidth * 0.78, c.maxHeight * 0.92);
          final vinilo = _tramo(entrada, 0.3, 0.85, Curves.easeOutBack);
          final portada = _tramo(entrada, 0.05, 0.55, Curves.easeOutBack);
          return Center(
            child: SizedBox(
              width: lado * 1.28,
              height: lado,
              child: Stack(clipBehavior: Clip.none, alignment: Alignment.centerLeft, children: [
                AnimatedBuilder(
                  animation: Listenable.merge([vinilo, fondo]),
                  builder: (_, hijo) => Positioned(
                    left: lado * 0.02 + vinilo.value * lado * 0.28,
                    child: Transform.rotate(angle: fondo.value * 2 * pi * 6, child: hijo),
                  ),
                  child: _Vinilo(lado: lado * 0.96, centro: url),
                ),
                AnimatedBuilder(
                  animation: portada,
                  builder: (_, hijo) => Transform.scale(
                    scale: 0.6 + 0.4 * portada.value,
                    child: Opacity(opacity: portada.value.clamp(0.0, 1.0), child: hijo),
                  ),
                  child: DecoratedBox(
                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), boxShadow: [
                      BoxShadow(color: Colors.black.withValues(alpha: 0.55), blurRadius: 40, offset: const Offset(0, 18)),
                    ]),
                    child: Portada(url: url, lado: lado, radio: 14),
                  ),
                ),
              ]),
            ),
          );
        }),
      ),
      const SizedBox(height: 22),
      _Entra(
        a: entrada, desde: 0.45,
        child: Text('${pista['titulo'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis, style: _titular),
      ),
      const SizedBox(height: 6),
      _Entra(
        a: entrada, desde: 0.52,
        child: Text('${pista['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
            style: _cuerpo.copyWith(fontSize: 19, color: Colors.white70)),
      ),
      const SizedBox(height: 14),
      _Entra(a: entrada, desde: 0.62, child: Text(pie, style: _cuerpo)),
    ]);
  }
}

class _Vinilo extends StatelessWidget {
  const _Vinilo({required this.lado, required this.centro});
  final double lado;
  final String centro;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: lado,
        height: lado,
        child: Stack(alignment: Alignment.center, children: [
          CustomPaint(size: Size.square(lado), painter: _PintorVinilo()),
          Portada(url: centro, lado: lado * 0.34, circulo: true),
          Container(
            width: lado * 0.04, height: lado * 0.04,
            decoration: const BoxDecoration(color: Colors.black, shape: BoxShape.circle),
          ),
        ]),
      );
}

class _PintorVinilo extends CustomPainter {
  @override
  void paint(Canvas canvas, Size s) {
    final c = s.center(Offset.zero);
    final r = s.width / 2;
    canvas.drawCircle(c, r, Paint()..color = const Color(0xFF0C0C0E));
    final surco = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8
      ..color = Colors.white.withValues(alpha: 0.06);
    for (var x = r * 0.4; x < r * 0.97; x += r * 0.035) {
      canvas.drawCircle(c, x, surco);
    }
    // el reflejo que hace que se note el giro
    canvas.drawArc(Rect.fromCircle(center: c, radius: r * 0.8), -pi / 3, pi / 5, false,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = r * 0.5
          ..color = Colors.white.withValues(alpha: 0.05));
  }

  @override
  bool shouldRepaint(_PintorVinilo oldDelegate) => false;
}

class _HistoriaTopCanciones extends StatelessWidget {
  const _HistoriaTopCanciones({required this.r, required this.entrada});
  final Resumen r;
  final Animation<double> entrada;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _Entra(a: entrada, desde: 0, child: const Text('LAS QUE NO PARASTE DE PONER', style: _antetitulo)),
        const SizedBox(height: 8),
        _Entra(a: entrada, desde: 0.05, child: const Text('Tus canciones top', style: _titular)),
        const SizedBox(height: 12),
        Expanded(
          child: LayoutBuilder(
            builder: (_, c) => FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: SizedBox(
                width: c.maxWidth,
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                for (final (i, p) in r.topCanciones.indexed)
                  _Entra(
                    a: entrada, desde: 0.15 + i * 0.09, dy: 40,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Row(children: [
                        SizedBox(
                          width: 44,
                          child: Text('${i + 1}', style: TextStyle(
                              fontSize: 34, fontWeight: FontWeight.w900, letterSpacing: -1,
                              color: i == 0 ? Colors.white : Colors.white.withValues(alpha: 0.55))),
                        ),
                        DecoratedBox(
                          decoration: BoxDecoration(borderRadius: BorderRadius.circular(8), boxShadow: [
                            BoxShadow(color: Colors.black.withValues(alpha: 0.35), blurRadius: 14, offset: const Offset(0, 6)),
                          ]),
                          child: Portada(url: '${p.pista['miniatura'] ?? ''}', lado: i == 0 ? 72 : 60, radio: 8),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('${p.pista['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                                style: TextStyle(fontSize: i == 0 ? 19 : 17, fontWeight: FontWeight.w800, color: Colors.white)),
                            const SizedBox(height: 2),
                            Text('${p.pista['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 14, color: Colors.white70, fontWeight: FontWeight.w600)),
                          ]),
                        ),
                        const SizedBox(width: 8),
                        Text('${p.veces}×', style: const TextStyle(
                            fontSize: 15, color: Colors.white, fontWeight: FontWeight.w800)),
                      ]),
                    ),
                  ),
                ]),
              ),
            ),
          ),
        ),
      ]);
}

class _HistoriaArtistas extends StatelessWidget {
  const _HistoriaArtistas({required this.r, required this.entrada});
  final Resumen r;
  final Animation<double> entrada;

  @override
  Widget build(BuildContext context) {
    final uno = r.topArtistas.first;
    final resto = r.topArtistas.skip(1).toList();
    final anillo = _tramo(entrada, 0.1, 0.8, Curves.easeOutCubic);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _Entra(a: entrada, desde: 0, child: const Text('TU ARTISTA MÁS ESCUCHADO', style: _antetitulo)),
      Expanded(
        child: LayoutBuilder(builder: (_, c) {
          final lado = min(c.maxWidth * 0.66, c.maxHeight * 0.8);
          return Center(
            child: AnimatedBuilder(
              animation: anillo,
              builder: (_, hijo) => CustomPaint(
                painter: _PintorAnillo(anillo.value),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Transform.scale(scale: 0.75 + 0.25 * anillo.value, child: hijo),
                ),
              ),
              child: Portada(url: uno.miniatura, lado: lado, circulo: true, icono: Icons.person_rounded),
            ),
          );
        }),
      ),
      _Entra(
        a: entrada, desde: 0.35,
        child: Text(uno.nombre, maxLines: 2, overflow: TextOverflow.ellipsis,
            style: _titular.copyWith(fontSize: 44)),
      ),
      const SizedBox(height: 4),
      _Entra(
        a: entrada, desde: 0.42,
        child: Text('${_miles(uno.minutos)} minutos · ${_veces(uno.veces)}', style: _cuerpo.copyWith(color: Colors.white70)),
      ),
      if (resto.isNotEmpty) ...[
        const SizedBox(height: 22),
        Row(children: [
          for (final (i, a) in resto.indexed)
            Expanded(
              child: _Entra(
                a: entrada, desde: 0.5 + i * 0.08,
                child: Column(children: [
                  Portada(url: a.miniatura, lado: 58, circulo: true, icono: Icons.person_rounded),
                  const SizedBox(height: 6),
                  Text('${i + 2}. ${a.nombre}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 12.5, color: Colors.white, fontWeight: FontWeight.w700)),
                ]),
              ),
            ),
        ]),
      ],
    ]);
  }
}

class _PintorAnillo extends CustomPainter {
  _PintorAnillo(this.t);
  final double t;

  @override
  void paint(Canvas canvas, Size s) {
    final rect = Offset.zero & s;
    final r = rect.deflate(3);
    canvas.drawArc(r, -pi / 2, 2 * pi * t, false, Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 5
      ..strokeCap = StrokeCap.round
      ..shader = const SweepGradient(colors: [Color(0xFFFFB443), Color(0xFFFF5C8A), Color(0xFFFFB443)])
          .createShader(rect));
  }

  @override
  bool shouldRepaint(_PintorAnillo old) => old.t != t;
}

class _HistoriaHoras extends StatelessWidget {
  const _HistoriaHoras({required this.r, required this.entrada});
  final Resumen r;
  final Animation<double> entrada;

  static const _personajes = {
    'madrugada': ('Alma de madrugada', 'Cuando todos duermen, tú le das al play.'),
    'mañana': ('Madrugador del ritmo', 'Empiezas el día con banda sonora.'),
    'tarde': ('Tarde sonora', 'Tus tardes suenan mejor que las de nadie.'),
    'noche': ('Criatura nocturna', 'La noche es tuya y suena a tu música.'),
  };

  @override
  Widget build(BuildContext context) {
    final (nombre, frase) = _personajes[r.franja]!;
    final barras = _tramo(entrada, 0.25, 1.0, Curves.easeOutCubic);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _Entra(a: entrada, desde: 0, child: const Text('TU HORA DE MÚSICA', style: _antetitulo)),
      const SizedBox(height: 6),
      _Entra(
        a: entrada, desde: 0.05,
        child: _Degradado(
          colores: const [Colors.white, Color(0xFF93C5FD), Color(0xFFC4B5FD)],
          child: Text(_hora(r.horaPico), style: const TextStyle(
              fontSize: 96, fontWeight: FontWeight.w900, letterSpacing: -4, height: 1)),
        ),
      ),
      _Entra(a: entrada, desde: 0.15, child: Text(nombre, style: _titular)),
      const SizedBox(height: 8),
      _Entra(a: entrada, desde: 0.22, child: Text(frase, style: _cuerpo.copyWith(color: Colors.white70))),
      const SizedBox(height: 26),
      Expanded(
        child: AnimatedBuilder(
          animation: barras,
          builder: (_, _) => CustomPaint(
            size: Size.infinite,
            painter: _PintorHoras(r.porHora, r.horaPico, barras.value),
          ),
        ),
      ),
      const SizedBox(height: 8),
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        for (final h in const ['00', '06', '12', '18', '23'])
          Text(h, style: const TextStyle(color: Colors.white54, fontSize: 12, fontWeight: FontWeight.w700)),
      ]),
    ]);
  }
}

class _PintorHoras extends CustomPainter {
  _PintorHoras(this.horas, this.pico, this.t);
  final List<int> horas;
  final int pico;
  final double t;

  @override
  void paint(Canvas canvas, Size s) {
    final maximo = max(1, horas.reduce(max));
    final ancho = s.width / 24;
    for (var h = 0; h < 24; h++) {
      // cada barra arranca un poco despues que la anterior
      final local = ((t * 1.6) - h / 24 * 0.6).clamp(0.0, 1.0);
      final alto = max(4.0, s.height * horas[h] / maximo * Curves.easeOutBack.transform(local).clamp(0.0, 1.2));
      final rect = RRect.fromRectAndRadius(
        Rect.fromLTWH(h * ancho + ancho * 0.16, s.height - alto, ancho * 0.68, alto),
        Radius.circular(ancho * 0.3),
      );
      final paint = Paint();
      if (h == pico) {
        paint.shader = const LinearGradient(
          colors: [Color(0xFF67E8F9), Color(0xFF7C5CFF)],
          begin: Alignment.topCenter, end: Alignment.bottomCenter,
        ).createShader(rect.outerRect);
      } else {
        paint.color = Colors.white.withValues(alpha: horas[h] == 0 ? 0.14 : 0.42);
      }
      canvas.drawRRect(rect, paint);
    }
  }

  @override
  bool shouldRepaint(_PintorHoras old) => old.t != t || old.horas != horas;
}

class _HistoriaRacha extends StatelessWidget {
  const _HistoriaRacha({required this.r, required this.entrada, required this.fondo});
  final Resumen r;
  final Animation<double> entrada;
  final Animation<double> fondo;

  @override
  Widget build(BuildContext context) {
    final viva = r.rachaActual > 0;
    final dias = viva ? r.rachaActual : r.rachaMasLarga;
    final mapa = _tramo(entrada, 0.35, 1.0, Curves.easeOut);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _Entra(a: entrada, desde: 0, child: Text(viva ? 'TU RACHA' : 'TU MEJOR RACHA', style: _antetitulo)),
      const SizedBox(height: 14),
      Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
        AnimatedBuilder(
          animation: fondo,
          builder: (_, hijo) => Transform.scale(scale: 1 + 0.08 * sin(fondo.value * 2 * pi * 14), child: hijo),
          child: const _Degradado(
            colores: [Color(0xFFFFE08A), Color(0xFFFF7A45), Color(0xFFFF3D6E)],
            child: Icon(Icons.local_fire_department_rounded, size: 104),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _Contador(a: entrada, valor: dias, desde: 0.08, estilo: const TextStyle(
              fontSize: 112, fontWeight: FontWeight.w900, letterSpacing: -5, color: Colors.white, height: 1)),
        ),
      ]),
      _Entra(a: entrada, desde: 0.2, child: Text(dias == 1 ? 'día con música' : 'días seguidos con música', style: _titular)),
      const SizedBox(height: 10),
      _Entra(
        a: entrada, desde: 0.28,
        child: Text(
          viva
              ? (r.rachaMasLarga > r.rachaActual
                  ? 'Tu mejor racha en ${r.periodo.rango}: ${r.rachaMasLarga} días. ¡A por ella!'
                  : 'No la rompas: mañana también toca.')
              : 'Hoy es buen día para empezar otra.',
          style: _cuerpo.copyWith(color: Colors.white70),
        ),
      ),
      const SizedBox(height: 26),
      _Entra(
        a: entrada, desde: 0.32,
        child: Text('${r.diasConMusica} de ${r.porDia.length} días con música',
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15)),
      ),
      const SizedBox(height: 12),
      Expanded(
        child: AnimatedBuilder(
          animation: mapa,
          builder: (_, _) => CustomPaint(size: Size.infinite, painter: _PintorDias(r.porDia, mapa.value)),
        ),
      ),
    ]);
  }
}

/// Un cuadrito por dia, como el mapa de contribuciones de GitHub.
class _PintorDias extends CustomPainter {
  _PintorDias(this.dias, this.t);
  final List<int> dias;
  final double t;

  @override
  void paint(Canvas canvas, Size s) {
    final n = dias.length;
    if (n == 0) return;
    final columnas = n <= 7 ? 7 : (n <= 31 ? 10 : 27);
    final filas = (n / columnas).ceil();
    final lado = min(s.width / columnas, s.height / max(filas, 1));
    final hueco = lado * (n > 31 ? 0.18 : 0.14);
    final maximo = max(1, dias.reduce(max));
    final visibles = (n * t).ceil();
    for (var i = 0; i < min(visibles, n); i++) {
      final x = (i % columnas) * lado;
      final y = (i ~/ columnas) * lado;
      final v = dias[i] / maximo;
      final color = dias[i] == 0
          ? Colors.white.withValues(alpha: 0.10)
          : Color.lerp(const Color(0xFFFFB443), const Color(0xFFFF3D6E), v)!.withValues(alpha: 0.45 + 0.55 * v);
      canvas.drawRRect(
        RRect.fromRectAndRadius(Rect.fromLTWH(x, y, lado - hueco, lado - hueco), Radius.circular(lado * 0.22)),
        Paint()..color = color,
      );
    }
  }

  @override
  bool shouldRepaint(_PintorDias old) => old.t != t || old.dias != dias;
}

class _HistoriaDescubrimientos extends StatelessWidget {
  const _HistoriaDescubrimientos({required this.r, required this.entrada});
  final Resumen r;
  final Animation<double> entrada;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _Entra(a: entrada, desde: 0, child: const Text('DESCUBRIMIENTOS', style: _antetitulo)),
        const SizedBox(height: 8),
        _Entra(a: entrada, desde: 0.05, child: const Text('Te enamoraste de alguien nuevo', style: _titular)),
        const Spacer(),
        for (final (i, a) in r.descubrimientos.indexed)
          _Entra(
            a: entrada, desde: 0.2 + i * 0.12, dy: 50,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Row(children: [
                Portada(url: a.miniatura, lado: 84, circulo: true, icono: Icons.person_rounded),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(a.nombre, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900, color: Colors.white)),
                    Text('Nuevo para ti · ${_miles(a.minutos)} min',
                        style: const TextStyle(fontSize: 14, color: Colors.white70, fontWeight: FontWeight.w600)),
                  ]),
                ),
              ]),
            ),
          ),
        const Spacer(),
      ]);
}

/// La tarjeta resumen para compartir: todo de un vistazo.
class _HistoriaFinal extends StatelessWidget {
  const _HistoriaFinal({required this.r, required this.entrada});
  final Resumen r;
  final Animation<double> entrada;

  @override
  Widget build(BuildContext context) {
    final uno = r.topArtistas.isEmpty ? null : r.topArtistas.first;
    Widget columna(String titulo, List<String> filas, double desde) => Expanded(
          child: _Entra(
            a: entrada, desde: desde,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(titulo, style: const TextStyle(color: Colors.white60, fontSize: 13, fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              for (final (i, f) in filas.indexed)
                Padding(
                  padding: const EdgeInsets.only(bottom: 5),
                  child: Text('${i + 1}  $f', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700)),
                ),
            ]),
          ),
        );
    Widget cifra(String valor, String texto, double desde) => Expanded(
          child: _Entra(
            a: entrada, desde: desde,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(texto, style: const TextStyle(color: Colors.white60, fontSize: 13, fontWeight: FontWeight.w800)),
              FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(valor, style: const TextStyle(
                    color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900, letterSpacing: -1)),
              ),
            ]),
          ),
        );
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _Entra(
        a: entrada, desde: 0,
        child: Row(children: [
          if (uno != null)
            Container(
              padding: const EdgeInsets.all(3),
              decoration: const BoxDecoration(shape: BoxShape.circle,
                  gradient: LinearGradient(colors: [Color(0xFF22D3EE), Color(0xFF7C5CFF)])),
              child: Portada(url: uno.miniatura, lado: 96, circulo: true, icono: Icons.person_rounded),
            ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(r.periodo.nombre.toUpperCase(), style: _antetitulo),
              const SizedBox(height: 4),
              const Text('en Caudal', style: _titular),
            ]),
          ),
        ]),
      ),
      const SizedBox(height: 28),
      Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        columna('Artistas top', [for (final a in r.topArtistas) a.nombre], 0.12),
        const SizedBox(width: 14),
        columna('Canciones top', [for (final c in r.topCanciones) '${c.pista['titulo'] ?? ''}'], 0.2),
      ]),
      const Spacer(),
      Row(children: [
        cifra(_miles(r.minutos), 'Minutos', 0.3),
        cifra(_hora(r.horaPico), 'Tu hora', 0.36),
        cifra('${max(r.rachaActual, r.rachaMasLarga)} d', 'Racha', 0.42),
      ]),
      const SizedBox(height: 18),
      if (r.cancionDelMes != null)
        _Entra(
          a: entrada, desde: 0.5,
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
            ),
            child: Row(children: [
              Portada(url: '${r.cancionDelMes!.pista['miniatura'] ?? ''}', lado: 52, radio: 8),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Canción de ${r.nombreMes}',
                      style: const TextStyle(color: Colors.white60, fontSize: 12.5, fontWeight: FontWeight.w800)),
                  Text('${r.cancionDelMes!.pista['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w800)),
                ]),
              ),
            ]),
          ),
        ),
      const SizedBox(height: 8),
    ]);
  }
}

class _HistoriaVacia extends StatelessWidget {
  const _HistoriaVacia({required this.periodo, required this.entrada});
  final PeriodoResumen periodo;
  final Animation<double> entrada;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _Entra(a: entrada, desde: 0, child: const Icon(Icons.headphones_rounded, size: 84, color: Colors.white)),
          const SizedBox(height: 20),
          _Entra(a: entrada, desde: 0.1, child: const Text('Tu resumen está por escribirse', style: _titular)),
          const SizedBox(height: 12),
          _Entra(
            a: entrada, desde: 0.2,
            child: Text(
              'Aún no hay escuchas en ${periodo.rango}. Pon música y vuelve: '
              'tu resumen se arma solo con lo que escuches. Prueba también otro período arriba.',
              style: _cuerpo.copyWith(color: Colors.white70),
            ),
          ),
        ],
      );
}

// ======================================================================
// Fondo, controles y estados
// ======================================================================

/// Fondo vivo: manchas de color que se mueven despacio. Solo degradados
/// radiales (nada de desenfoques), para que vaya fluido en cualquier telefono.
class _Aurora extends StatelessWidget {
  const _Aurora({required this.colores, required this.tiempo});
  final List<Color> colores;
  final Animation<double> tiempo;

  @override
  Widget build(BuildContext context) => CustomPaint(painter: _PintorAurora(colores, tiempo));
}

class _PintorAurora extends CustomPainter {
  _PintorAurora(this.colores, this.tiempo) : super(repaint: tiempo);
  final List<Color> colores;
  final Animation<double> tiempo;

  @override
  void paint(Canvas canvas, Size s) {
    final t = tiempo.value * 2 * pi;
    final rect = Offset.zero & s;
    canvas.drawRect(rect, Paint()
      ..shader = LinearGradient(
        colors: [colores[0], Color.lerp(colores[0], Colors.black, 0.6)!],
        begin: Alignment.topCenter, end: Alignment.bottomCenter,
      ).createShader(rect));
    final d = max(s.width, s.height);
    void mancha(Color c, double cx, double cy, double r, double alfa) {
      final centro = Offset(cx * s.width, cy * s.height);
      canvas.drawCircle(centro, r * d, Paint()
        ..shader = RadialGradient(colors: [c.withValues(alpha: alfa), c.withValues(alpha: 0)])
            .createShader(Rect.fromCircle(center: centro, radius: r * d)));
    }

    mancha(colores[1], 0.2 + 0.25 * sin(t), 0.18 + 0.12 * cos(t * 2), 0.55, 0.75);
    mancha(colores[2], 0.85 + 0.2 * cos(t + 1), 0.55 + 0.18 * sin(t * 3 + 2), 0.5, 0.6);
    mancha(colores.length > 3 ? colores[3] : colores[1], 0.4 + 0.3 * sin(t * 2 + 4),
        0.95 + 0.08 * cos(t), 0.45, 0.45);
    // velo oscuro abajo para que el texto se lea siempre
    canvas.drawRect(rect, Paint()
      ..shader = LinearGradient(
        colors: [Colors.black.withValues(alpha: 0.05), Colors.black.withValues(alpha: 0.5)],
        begin: Alignment.topCenter, end: Alignment.bottomCenter,
      ).createShader(rect));
  }

  @override
  bool shouldRepaint(_PintorAurora old) => old.colores != colores;
}

class _Firma extends StatelessWidget {
  const _Firma();

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(Icons.graphic_eq_rounded, size: 16, color: Colors.white.withValues(alpha: 0.6)),
          const SizedBox(width: 6),
          Flexible(
            child: Text('Caudal · Tu resumen', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(
                color: Colors.white.withValues(alpha: 0.6), fontSize: 12.5, fontWeight: FontWeight.w800,
                letterSpacing: 0.4)),
          ),
        ]),
      );
}

class _SelectorPeriodo extends StatelessWidget {
  const _SelectorPeriodo({required this.actual, required this.alCambiar});
  final PeriodoResumen actual;
  final ValueChanged<PeriodoResumen> alCambiar;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(3),
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.3),
          borderRadius: BorderRadius.circular(30),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          for (final per in PeriodoResumen.values)
            GestureDetector(
              onTap: () => alCambiar(per),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 220),
                curve: Curves.easeOutCubic,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                decoration: BoxDecoration(
                  color: per == actual ? Colors.white : Colors.transparent,
                  borderRadius: BorderRadius.circular(30),
                ),
                child: Text(per.etiqueta, style: TextStyle(
                    fontSize: 13.5, fontWeight: FontWeight.w800,
                    color: per == actual ? Colors.black : Colors.white)),
              ),
            ),
        ]),
      );
}

class _Pastilla extends StatelessWidget {
  const _Pastilla({super.key, required this.icono, required this.texto, required this.claro, required this.alPulsar});
  final IconData? icono;
  final String texto;
  final bool claro;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) {
    final color = claro ? Colors.black : Colors.white;
    return Material(
      color: claro ? Colors.white : Colors.white.withValues(alpha: 0.16),
      shape: const StadiumBorder(),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: alPulsar,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            if (icono == null)
              SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.2, color: color))
            else
              Icon(icono, color: color, size: 20),
            const SizedBox(width: 8),
            Text(texto, style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 15)),
          ]),
        ),
      ),
    );
  }
}

class _Cargando extends StatelessWidget {
  const _Cargando();

  @override
  Widget build(BuildContext context) => Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          SizedBox(width: 36, height: 36, child: CircularProgressIndicator(strokeWidth: 3, color: C.acento)),
          SizedBox(height: 16),
          Text('Contando tus canciones…', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w700)),
        ]),
      );
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.texto, required this.alCerrar});
  final String texto;
  final VoidCallback alCerrar;

  @override
  Widget build(BuildContext context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text(texto, textAlign: TextAlign.center, style: _cuerpo),
            const SizedBox(height: 20),
            FilledButton(onPressed: alCerrar, child: const Text('Cerrar')),
          ]),
        ),
      );
}

// ======================================================================
// Tus mixes diarios: portada en mosaico y la fila para Inicio
// ======================================================================

/// Portada de un mix: cuatro portadas en mosaico, un velo de su color y el
/// nombre encima, como los Daily Mix.
class PortadaMix extends StatelessWidget {
  const PortadaMix({super.key, required this.mix, this.lado = 150, this.radio = 8});
  final Json mix;
  final double lado;
  final double radio;

  @override
  Widget build(BuildContext context) {
    final urls = [for (final u in (mix['miniaturas'] as List? ?? const [])) '$u'];
    if (urls.isEmpty && '${mix['miniatura'] ?? ''}'.isNotEmpty) urls.add('${mix['miniatura']}');
    final color = Color(mix['color'] is int ? mix['color'] as int : 0xFF22D3EE);
    final mitad = lado / 2;
    Widget celda(int i) => Portada(url: urls.isEmpty ? '' : urls[i % urls.length], lado: mitad, radio: 0);
    return ClipRRect(
      borderRadius: BorderRadius.circular(radio),
      child: SizedBox(
        width: lado,
        height: lado,
        child: Stack(children: [
          if (urls.length >= 4)
            Column(children: [
              Row(children: [celda(0), celda(1)]),
              Row(children: [celda(2), celda(3)]),
            ])
          else
            Portada(url: urls.isEmpty ? '' : urls.first, lado: lado, radio: 0),
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [color.withValues(alpha: 0.05), color.withValues(alpha: 0.85)],
                begin: Alignment.topCenter, end: Alignment.bottomCenter,
                stops: const [0.35, 1],
              ),
            ),
            child: const SizedBox.expand(),
          ),
          Positioned(
            left: lado * 0.07, top: lado * 0.07,
            child: Icon(Icons.graphic_eq_rounded, color: Colors.white, size: lado * 0.13),
          ),
          Positioned(
            left: lado * 0.07, right: lado * 0.07, bottom: lado * 0.06,
            child: Text('${mix['titulo'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: lado * 0.115,
                    height: 1.05, letterSpacing: -0.3,
                    shadows: const [Shadow(color: Colors.black45, blurRadius: 8)])),
          ),
          Positioned(left: 0, right: 0, bottom: 0, child: Container(height: lado * 0.03, color: color)),
        ]),
      ),
    );
  }
}

/// Una tarjeta de mix. Por defecto, tocarla lo pone a sonar; [alAbrir] permite
/// abrir su pagina en su lugar.
class TarjetaMix extends StatelessWidget {
  const TarjetaMix({super.key, required this.mix, this.ancho = 150, this.alAbrir});
  final Json mix;
  final double ancho;
  final void Function(Json mix)? alAbrir;

  static Future<void> reproducir(BuildContext context, Json mix, {bool? aleatorio}) {
    final s = Caudal.leer(context);
    final pistas = [
      for (final e in (mix['pistas'] as List? ?? const []))
        if (e is Map) Map<String, dynamic>.from(e)
    ];
    if (pistas.isEmpty) {
      s.avisar('Este mix aún no tiene canciones.');
      return Future.value();
    }
    return s.reproducirLista(context, pistas, aleatorio: aleatorio, contexto: {
      'tipo': 'mix', 'id': mix['id'], 'titulo': mix['titulo'], 'miniatura': mix['miniatura'],
    });
  }

  @override
  Widget build(BuildContext context) => RepaintBoundary(
        child: SizedBox(
          width: ancho,
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: () => alAbrir != null ? alAbrir!(mix) : reproducir(context, mix),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              PortadaMix(mix: mix, lado: ancho),
              const SizedBox(height: 8),
              Text('${mix['subtitulo'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12.5, color: C.texto2, height: 1.25)),
            ]),
          ),
        ),
      );
}

/// La fila "Tus mixes diarios" lista para poner en Inicio. Se oculta sola si
/// aun no hay historial. [alAbrir] igual que en [TarjetaMix].
class SeccionMixes extends StatefulWidget {
  const SeccionMixes({super.key, this.titulo = 'Tus mixes diarios', this.alAbrir});
  final String titulo;
  final void Function(Json mix)? alAbrir;

  @override
  State<SeccionMixes> createState() => _SeccionMixesState();
}

class _SeccionMixesState extends State<SeccionMixes> {
  List<Json>? _mixes;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      try {
        final m = await Mixes.delDia(Caudal.leer(context).coleccion);
        if (mounted) setState(() => _mixes = m);
      } catch (_) {
        if (mounted) setState(() => _mixes = const []);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final m = _mixes;
    if (m == null || m.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      TituloSeccion(widget.titulo),
      SizedBox(
        height: 212,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          itemCount: m.length,
          separatorBuilder: (_, _) => const SizedBox(width: 14),
          itemBuilder: (_, i) => TarjetaMix(mix: m[i], alAbrir: widget.alAbrir),
        ),
      ),
      const SizedBox(height: 24),
    ]);
  }
}
