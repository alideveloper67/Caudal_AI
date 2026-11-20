// «Feliz cumpleaños»: el gorrito, la pantalla de celebración, el banner de Inicio y el aviso de amigos.
//
// Todo es ligero: el gorrito es un dibujo vectorial sin imágenes, el confeti es UN reloj que repinta un
// solo CustomPaint (en un RepaintBoundary) y con «quitar animaciones» o el modo ligero se queda quieto.

import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:flutter/material.dart';

import '../nucleo/chat.dart';
import '../nucleo/cumpleanos.dart';
import '../nucleo/mascota_app.dart';
import '../nucleo/nube.dart';
import '../nucleo/social.dart';
import 'paginas/mensajes_pagina.dart';
import 'servicios.dart';
import 'tema.dart';

const _rosa = Color(0xFFFF4FA3);
const _violeta = Color(0xFF7C5CFF);
const _oro = Color(0xFFFFC857);
const _cian = Color(0xFF3DDCFF);

// ============================================================ el gorrito

/// Dibuja el gorrito con la base centrada en [base] y [ancho] de ancho. Inclinado un poco, con rayas y pompón.
void pintarGorroCumple(Canvas canvas, Offset base, double ancho, {double inclinacion = -0.2}) {
  if (ancho < 4) return;
  canvas.save();
  canvas.translate(base.dx, base.dy);
  canvas.rotate(inclinacion);
  final mitad = ancho / 2;
  final alto = ancho * 1.1;
  final cono = Path()
    ..moveTo(-mitad, 0)
    ..lineTo(mitad, 0)
    ..lineTo(ancho * 0.03, -alto)
    ..close();
  final caja = Rect.fromLTRB(-mitad, -alto, mitad, 0);
  canvas.drawPath(
      cono,
      Paint()
        ..shader = const LinearGradient(colors: [_rosa, _violeta], begin: Alignment.topLeft, end: Alignment.bottomRight)
            .createShader(caja));
  // rayas amarillas (recortadas al cono)
  canvas.save();
  canvas.clipPath(cono);
  final raya = Paint()..color = _oro..style = PaintingStyle.stroke..strokeWidth = math.max(1.2, ancho * 0.11);
  for (final f in const [0.28, 0.58]) {
    canvas.drawLine(Offset(-mitad, -alto * f + ancho * 0.12), Offset(mitad, -alto * f - ancho * 0.12), raya);
  }
  canvas.restore();
  // borde de abajo y pompón
  canvas.drawRRect(
      RRect.fromRectAndRadius(Rect.fromLTRB(-mitad - ancho * 0.03, -ancho * 0.07, mitad + ancho * 0.03, ancho * 0.05),
          Radius.circular(ancho * 0.05)),
      Paint()..color = _cian);
  canvas.drawCircle(Offset(ancho * 0.03, -alto), ancho * 0.12, Paint()..color = _oro);
  canvas.restore();
}

class _PintorGorro extends CustomPainter {
  const _PintorGorro();
  @override
  void paint(Canvas canvas, Size size) => pintarGorroCumple(canvas, Offset(size.width / 2, size.height), size.width * 0.86);
  @override
  bool shouldRepaint(covariant CustomPainter old) => false;
}

/// El gorrito solo (cabe en [ancho] x [ancho]*1.3).
class GorroFiesta extends StatelessWidget {
  const GorroFiesta({super.key, required this.ancho});
  final double ancho;

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
        child: SizedBox(width: ancho, height: ancho * 1.3, child: const CustomPaint(painter: _PintorGorro())),
      );
}

/// Pone el gorrito sobre [child] (un avatar redondo de [radio]) si esa persona cumple hoy.
/// Sin [userId] solo se pone con [activo]. No cambia el tamaño del avatar: el gorro sobresale por arriba.
class ConGorro extends StatelessWidget {
  const ConGorro({super.key, required this.radio, required this.child, this.userId, this.activo = false});
  final double radio;
  final Widget child;
  final String? userId;
  final bool activo;

  @override
  Widget build(BuildContext context) {
    final id = userId;
    if (id == null) return _poner(activo);
    return ListenableBuilder(listenable: Cumpleanos.i, builder: (_, _) => _poner(activo || Cumpleanos.i.esDe(id)));
  }

  Widget _poner(bool si) {
    if (!si || radio < 8) return child;
    final gw = radio * 0.95, gh = gw * 1.3;
    return Stack(clipBehavior: Clip.none, children: [
      child,
      Positioned(
        top: radio * 0.2 - gh,
        left: radio * 0.62,
        width: gw,
        height: gh,
        child: const IgnorePointer(child: CustomPaint(painter: _PintorGorro())),
      ),
    ]);
  }
}

// ============================================================ la mascota con gorro

/// La mascota de la persona (o su personaje del fondo, o una tarta) con el gorrito puesto.
class _FiguraCumple extends StatelessWidget {
  const _FiguraCumple({required this.lado});
  final double lado;

  @override
  Widget build(BuildContext context) {
    final m = MascotaApp.i.activa ? MascotaApp.i.actual : null;
    final personaje = Aspecto.patron;
    if (m != null) {
      return FutureBuilder<ui.Image?>(
        future: MascotaApp.i.imagen(m.clave),
        builder: (_, f) {
          final im = f.data;
          return SizedBox(
            width: lado,
            height: lado,
            child: im == null
                ? const SizedBox.shrink()
                : CustomPaint(painter: _PintorMascotaGorro(im, m.ancho, m.alto, m.densidad)),
          );
        },
      );
    }
    if (personaje != null) {
      return SizedBox(
        width: lado,
        height: lado,
        child: Stack(alignment: Alignment.bottomCenter, clipBehavior: Clip.none, children: [
          Image.asset(personaje,
              height: lado * 0.8, filterQuality: FilterQuality.medium, excludeFromSemantics: true,
              errorBuilder: (_, _, _) => const SizedBox.shrink()),
          Positioned(top: 0, child: GorroFiesta(ancho: lado * 0.3)),
        ]),
      );
    }
    return SizedBox(
      width: lado,
      height: lado,
      child: Stack(alignment: Alignment.center, clipBehavior: Clip.none, children: [
        Container(
          width: lado * 0.62,
          height: lado * 0.62,
          decoration: const BoxDecoration(
              shape: BoxShape.circle, gradient: LinearGradient(colors: [_rosa, _violeta])),
          child: Icon(Icons.cake_rounded, size: lado * 0.34, color: Colors.white),
        ),
        Positioned(top: lado * 0.02, right: lado * 0.2, child: GorroFiesta(ancho: lado * 0.3)),
      ]),
    );
  }
}

class _PintorMascotaGorro extends CustomPainter {
  _PintorMascotaGorro(this.hoja, this.ancho, this.alto, this.densidad);
  final ui.Image hoja;
  final int ancho, alto, densidad;

  @override
  void paint(Canvas canvas, Size size) {
    // el primer cuadro de la hoja, lo más grande que quepa dejando sitio arriba para el gorro
    final escala = math.min(size.width / ancho, size.height * 0.82 / alto);
    final w = ancho * escala, h = alto * escala;
    final destino = Rect.fromLTWH((size.width - w) / 2, size.height - h, w, h);
    final fw = (ancho * densidad).toDouble(), fh = (alto * densidad).toDouble();
    canvas.drawImageRect(hoja, Rect.fromLTWH(0, 0, fw, fh), destino, Paint()..filterQuality = filtroMascota(densidad));
    pintarGorroCumple(canvas, Offset(size.width / 2 + w * 0.04, destino.top + h * 0.08), w * 0.34);
  }

  @override
  bool shouldRepaint(covariant _PintorMascotaGorro old) => old.hoja != hoja;
}

// ============================================================ la pantalla de celebración

/// «¡Feliz cumpleaños, X!»: pantalla completa con confeti, la edad y la mascota con gorro.
class PantallaCumple extends StatefulWidget {
  const PantallaCumple({super.key, required this.nombre, this.edad});
  final String nombre;
  final int? edad;

  /// La enseña sobre todo (una sola vez; el que llama decide cuándo, con [Cumpleanos.tocaCelebrar]).
  static Future<void> mostrar(BuildContext context, {required String nombre, int? edad}) =>
      Navigator.of(context, rootNavigator: true).push(PageRouteBuilder<void>(
        opaque: true,
        transitionDuration: const Duration(milliseconds: 450),
        reverseTransitionDuration: const Duration(milliseconds: 250),
        pageBuilder: (_, _, _) => PantallaCumple(nombre: nombre, edad: edad),
        transitionsBuilder: (_, a, _, hijo) => FadeTransition(opacity: a, child: hijo),
      ));

  @override
  State<PantallaCumple> createState() => _PantallaCumpleState();
}

class _PantallaCumpleState extends State<PantallaCumple> with SingleTickerProviderStateMixin {
  late final AnimationController _reloj = AnimationController(vsync: this, duration: const Duration(seconds: 9));
  bool _quieto = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _quieto = MediaQuery.disableAnimationsOf(context);
    if (_quieto) {
      _reloj.stop();
    } else if (!_reloj.isAnimating) {
      _reloj.repeat();
    }
  }

  @override
  void dispose() {
    _reloj.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final nombre = widget.nombre.trim();
    final titulo = nombre.isEmpty ? '¡Feliz cumpleaños!' : '¡Feliz cumpleaños, $nombre!';
    final alto = MediaQuery.sizeOf(context).height;
    final lado = (alto * 0.3).clamp(120.0, 230.0);
    return Scaffold(
      backgroundColor: const Color(0xFF1B1140),
      body: Stack(fit: StackFit.expand, children: [
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
                begin: Alignment.topCenter, end: Alignment.bottomCenter,
                colors: [Color(0xFF3A1D78), Color(0xFF1B1140)]),
          ),
        ),
        RepaintBoundary(
          child: IgnorePointer(
            child: CustomPaint(painter: _PintorConfeti(_reloj, quieto: _quieto), size: Size.infinite),
          ),
        ),
        SafeArea(
          child: LayoutBuilder(
            builder: (_, caja) => SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: caja.maxHeight),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    _FiguraCumple(lado: lado),
                    const SizedBox(height: 16),
                    Semantics(
                      header: true,
                      child: Text(titulo,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                              fontSize: 30, height: 1.15, fontWeight: FontWeight.w900, color: Colors.white)),
                    ),
                    if (widget.edad != null) ...[
                      const SizedBox(height: 10),
                      Text('Hoy cumples ${widget.edad}',
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700, color: _oro)),
                    ],
                    const SizedBox(height: 8),
                    const Text('Que la música no pare.',
                        textAlign: TextAlign.center, style: TextStyle(fontSize: 14.5, color: Color(0xFFD5CCF5))),
                    const SizedBox(height: 28),
                    SizedBox(
                      width: 220,
                      height: 50,
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                            backgroundColor: _rosa,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26))),
                        onPressed: () => Navigator.of(context).maybePop(),
                        child: const Text('¡Gracias!', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                      ),
                    ),
                  ]),
                ),
              ),
            ),
          ),
        ),
      ]),
    );
  }
}

/// Confeti: unas 56 piezas que caen con un vaivén. Todo sale de la posición del reloj; no guarda estado.
class _PintorConfeti extends CustomPainter {
  _PintorConfeti(this.reloj, {required this.quieto}) : super(repaint: reloj);
  final Animation<double> reloj;
  final bool quieto;

  static const _colores = [_rosa, _oro, _cian, _violeta, Color(0xFF7CFFB2), Colors.white];
  static const _n = 56;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;
    final t = quieto ? 0.35 : reloj.value;
    final p = Paint();
    for (var i = 0; i < _n; i++) {
      // «aleatorio» fijo por pieza
      final a = ((i * 7919) % 1000) / 1000.0, b = ((i * 104729) % 997) / 997.0, c = ((i * 15485863) % 991) / 991.0;
      final vueltas = 1 + (i % 3); // cuántas veces cruza la pantalla en un ciclo
      final y = ((t * vueltas + b) % 1.0) * (size.height + 40) - 20;
      final x = a * size.width + math.sin((t * vueltas + c) * math.pi * 2 * 2) * 14;
      final tam = 5.0 + c * 5;
      p.color = _colores[i % _colores.length].withValues(alpha: 0.9);
      canvas.save();
      canvas.translate(x, y);
      canvas.rotate((t * vueltas * 6 + a * 6) * (i.isEven ? 1 : -1));
      if (i % 4 == 0) {
        canvas.drawCircle(Offset.zero, tam * 0.45, p);
      } else {
        canvas.drawRect(Rect.fromCenter(center: Offset.zero, width: tam, height: tam * 0.5), p);
      }
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(covariant _PintorConfeti old) => old.quieto != quieto;
}

// ============================================================ en Inicio

/// El banner «Hoy es tu cumple» y los avisos de amigos que cumplen. No ocupa nada si no hay nada que decir.
class CumpleInicio extends StatefulWidget {
  const CumpleInicio({super.key, this.amigosDePrueba});

  /// Solo para pruebas: los amigos que cumplen, ya cargados (sin pedirlos a la nube).
  @visibleForTesting
  final List<Contacto>? amigosDePrueba;

  @override
  State<CumpleInicio> createState() => _CumpleInicioState();
}

class _CumpleInicioState extends State<CumpleInicio> {
  late List<Contacto>? _amigos = widget.amigosDePrueba;
  late String _paraIds = widget.amigosDePrueba == null ? '' : '*';
  bool _cargando = false;

  Future<void> _cargarAmigos(Set<String> ids) async {
    final clave = (ids.toList()..sort()).join(',');
    if (ids.isEmpty || clave == _paraIds || _paraIds == '*' || _cargando) return;
    Sesion? sesion;
    try {
      sesion = Caudal.leer(context).cuenta.sesion;
    } catch (_) {
      return;
    }
    if (sesion == null || sesion.acceso.isEmpty) return;
    _cargando = true;
    try {
      final todos = await Social(sesion).amigos();
      if (!mounted) return;
      setState(() {
        _amigos = [for (final c in todos) if (ids.contains(c.id)) c];
        _paraIds = clave;
      });
    } catch (_) {
      // sin red: no hay aviso, y se reintenta cuando cambie algo
    } finally {
      _cargando = false;
    }
  }

  Future<void> _escribir(Contacto c) async {
    final s = Caudal.leer(context);
    final sesion = s.cuenta.sesion;
    if (sesion == null) return;
    try {
      final id = await Chat(sesion).abrir(c.id);
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute<void>(
          builder: (_) => ConversacionPagina(
              chat: ResumenChat(id: id, otro: c.id, usuario: c.usuario, nombre: c.nombre,
                  ultimo: DateTime.now(), fotoUrl: c.fotoUrl))));
    } catch (e) {
      if (mounted) s.avisar(Social.error(e));
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: Cumpleanos.i,
        builder: (context, _) {
          final cu = Cumpleanos.i;
          final ids = cu.amigosHoy;
          if (ids.isNotEmpty) WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) _cargarAmigos(ids);
          });
          final amigos = [for (final c in _amigos ?? const <Contacto>[]) if (ids.contains(c.id)) c];
          if (!cu.esMiCumple && amigos.isEmpty) return const SizedBox.shrink();
          return Padding(
            padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, Esp.s),
            child: Column(children: [
              if (cu.esMiCumple) const _BannerMiCumple(),
              for (final c in amigos.take(3)) _AvisoAmigo(contacto: c, alEscribir: () => _escribir(c)),
              if (amigos.length > 3)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text('y ${amigos.length - 3} amigos más cumplen hoy',
                      style: TextStyle(fontSize: 12.5, color: C.texto2)),
                ),
            ]),
          );
        },
      );
}

class _BannerMiCumple extends StatelessWidget {
  const _BannerMiCumple();

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          gradient: const LinearGradient(colors: [Color(0xFFFF4FA3), Color(0xFF7C5CFF)]),
        ),
        child: Row(children: [
          const GorroFiesta(ancho: 26),
          const SizedBox(width: 10),
          const Expanded(
            child: Text('Hoy es tu cumple 🎂',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Colors.white)),
          ),
        ]),
      );
}

class _AvisoAmigo extends StatelessWidget {
  const _AvisoAmigo({required this.contacto, required this.alEscribir});
  final Contacto contacto;
  final VoidCallback alEscribir;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(top: 8),
        padding: const EdgeInsets.fromLTRB(14, 8, 8, 8),
        decoration: BoxDecoration(
          color: C.superficie2,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: _rosa.withValues(alpha: 0.5)),
        ),
        child: Row(children: [
          const GorroFiesta(ancho: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Text('Hoy es el cumple de ${contacto.visible}: ¡salúdalo!',
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: C.texto)),
          ),
          const SizedBox(width: 6),
          TextButton(
            onPressed: alEscribir,
            style: TextButton.styleFrom(foregroundColor: _rosa, padding: const EdgeInsets.symmetric(horizontal: 10)),
            child: const Text('Escribirle', style: TextStyle(fontWeight: FontWeight.w800)),
          ),
        ]),
      );
}
