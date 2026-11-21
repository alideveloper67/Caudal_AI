// Demostraciones vivas para las presentaciones «Somos 100» y «Gracias, donador».
//
// Cada demo enseña de verdad lo que Caudal da: los escenarios reales con sus efectos, la letra
// cantándose palabra a palabra, los marcos y nombres animados reales, las mascotas reales… Todas
// van dentro de [MarcoDemo] (una pantallita con borde de luz) y se animan solas en bucle.
// Con «Quitar animaciones» del teléfono se quedan en un cuadro bonito y quieto.

import 'dart:math' as math;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../../nucleo/mascota_app.dart';
import '../escenarios/catalogo.dart';
import '../escenarios/escenario_fondo.dart';
import '../premium/marcos.dart';
import '../premium/mascota_sprite.dart';
import '../reproductor/letra_estilo.dart';

Color _hex(String h) {
  final t = h.replaceAll('#', '');
  final v = int.tryParse(t.length == 6 ? 'FF$t' : t, radix: 16);
  return v == null ? Colors.white : Color(v);
}

// ------------------------------------------------------------------ marco

/// Una pantallita con esquinas redondas, borde de luz del [acento] y sombra, donde vive una demo.
class MarcoDemo extends StatelessWidget {
  const MarcoDemo({super.key, required this.child, required this.acento, this.proporcion = 4 / 3});

  final Widget child;
  final Color acento;
  final double proporcion;

  /// El ancho al que se diseña cada demo.
  static const double anchoDiseno = 340;

  @override
  Widget build(BuildContext context) => AspectRatio(
        aspectRatio: proporcion,
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: acento.withValues(alpha: 0.75), width: 1.6),
            boxShadow: [
              BoxShadow(color: acento.withValues(alpha: 0.35), blurRadius: 28, spreadRadius: 1),
              const BoxShadow(color: Color(0x99000000), blurRadius: 18, offset: Offset(0, 10)),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(22.5),
            // se dibuja siempre a 340 px de ancho y se escala: igual en un teléfono pequeño que en uno grande
            child: ColoredBox(
              color: const Color(0xFF07060C),
              child: FittedBox(
                fit: BoxFit.fill,
                child: SizedBox(width: anchoDiseno, height: anchoDiseno / proporcion, child: child),
              ),
            ),
          ),
        ),
      );
}

/// Etiqueta pequeña con fondo oscuro (para nombrar lo que se ve en la demo).
class _Etiqueta extends StatelessWidget {
  const _Etiqueta(this.texto, {super.key, this.icono, this.color = Colors.white});
  final String texto;
  final IconData? icono;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: const Color(0xB0000000),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withValues(alpha: 0.35)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          if (icono != null) ...[Icon(icono, size: 13, color: color), const SizedBox(width: 5)],
          Text(texto, style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: color, letterSpacing: 0.2)),
        ]),
      );
}

// ------------------------------------------------------------------ reloj común

/// Estado con un reloj continuo en segundos ([t]) que redibuja a ~30 FPS y se para con
/// «Quitar animaciones» (entonces [t] vale [tQuieto]).
abstract class _EstadoReloj<T extends StatefulWidget> extends State<T> with SingleTickerProviderStateMixin {
  late final Ticker _ticker = createTicker(_tic);
  double t = 0;
  Duration _ultimo = Duration.zero;
  bool quieto = false;

  double get tQuieto => 2.5;

  void _tic(Duration d) {
    if ((d - _ultimo).inMilliseconds < 32) return;
    _ultimo = d;
    setState(() => t = d.inMicroseconds / 1e6);
    alTic();
  }

  void alTic() {}

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    quieto = MediaQuery.disableAnimationsOf(context);
    if (quieto) {
      if (_ticker.isActive) _ticker.stop();
      t = tQuieto;
    } else if (!_ticker.isActive) {
      _ticker.start();
    }
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }
}

/// Un espectro simulado (32 bandas) con golpes de graves cada ~0,5 s, para que los escenarios
/// «bailen» como si sonara música.
class _EspectroSimulado extends ValueNotifier<List<double>> {
  _EspectroSimulado() : super(List<double>.filled(32, 0.2));

  void avanzar(double t) {
    final golpe = math.pow(math.max(0.0, math.cos(t * math.pi * 2 / 0.52)), 6).toDouble();
    value = [
      for (var i = 0; i < 32; i++)
        (i < 6 ? 0.25 + 0.75 * golpe : 0.25 + 0.35 * (0.5 + 0.5 * math.sin(t * 3.1 + i * 0.7)) * (1 - i / 48))
            .clamp(0.0, 1.0),
    ];
  }
}

// ------------------------------------------------------------------ escenarios

/// Los escenarios reales, pasando uno tras otro con fundido y reaccionando a un ritmo simulado.
class DemoEscenarios extends StatefulWidget {
  const DemoEscenarios({super.key, this.claves = const ['cyberpunk', 'samurai', 'goku', 'kuromi', 'lofi', 'cinnamoroll', 'kaneki', 'ippo'], this.acento = const Color(0xFFB66DFF)});
  final List<String> claves;
  final Color acento;

  @override
  State<DemoEscenarios> createState() => _DemoEscenariosState();
}

class _DemoEscenariosState extends _EstadoReloj<DemoEscenarios> {
  final _espectro = _EspectroSimulado();
  int _i = 0;
  double _cambio = 0;

  @override
  void alTic() {
    _espectro.avanzar(t);
    if (t - _cambio > 3.4) {
      _cambio = t;
      _i = (_i + 1) % widget.claves.length;
    }
  }

  @override
  void dispose() {
    _espectro.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final clave = widget.claves[_i];
    final nombre = escenarioPorClave(clave)?.nombre ?? clave;
    return MarcoDemo(
      acento: widget.acento,
      child: Stack(fit: StackFit.expand, children: [
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 700),
          child: KeyedSubtree(
            key: ValueKey(clave),
            child: EscenarioFondo(clave: clave, bandas: _espectro, interactivo: true),
          ),
        ),
        Positioned(
          left: 10,
          bottom: 10,
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 400),
            child: _Etiqueta(nombre, key: ValueKey(nombre), icono: Icons.landscape_rounded),
          ),
        ),
        Positioned(
          right: 10,
          top: 10,
          child: _Etiqueta('Tócalo', icono: Icons.touch_app_rounded, color: widget.acento),
        ),
      ]),
    );
  }
}

// ------------------------------------------------------------------ letra

const _versos = [
  'Bajo la lluvia sigo tu voz',
  'cada latido marca el compás',
  'y aunque la noche quiera callar',
  'esta canción nos vuelve a encontrar',
];

/// La letra de la escena cantándose palabra a palabra sobre un escenario real.
class DemoLetra extends StatefulWidget {
  const DemoLetra({super.key, this.escenario = 'samurai', this.acento = const Color(0xFFFF6E9A)});
  final String escenario;
  final Color acento;

  @override
  State<DemoLetra> createState() => _DemoLetraState();
}

class _DemoLetraState extends _EstadoReloj<DemoLetra> {
  static const _porVerso = 2.6;
  final _espectro = _EspectroSimulado();

  @override
  double get tQuieto => _porVerso * 0.6;

  @override
  void alTic() => _espectro.avanzar(t);

  @override
  void dispose() {
    _espectro.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final n = (t / _porVerso).floor();
    final verso = _versos[n % _versos.length];
    final siguiente = _versos[(n + 1) % _versos.length];
    final prog = ((t % _porVerso) / (_porVerso * 0.85)).clamp(0.0, 1.0);
    return MarcoDemo(
      acento: widget.acento,
      child: Stack(fit: StackFit.expand, children: [
        EscenarioFondo(clave: widget.escenario, bandas: _espectro, interactivo: false),
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Color(0x00000000), Color(0x22000000), Color(0xAA000000)],
            ),
          ),
        ),
        Positioned(
          left: 14,
          right: 14,
          bottom: 16,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 280),
              transitionBuilder: (h, a) => FadeTransition(
                opacity: a,
                child: ScaleTransition(scale: Tween(begin: 0.92, end: 1.0).animate(a), child: h),
              ),
              child: TextoLetraResaltado(
                key: ValueKey(verso),
                texto: verso,
                estilo: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900, height: 1.2, color: Colors.white),
                activo: true,
                acento: widget.acento,
                progreso: prog,
                alinear: TextAlign.center,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              siguiente,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: Colors.white.withValues(alpha: 0.55)),
            ),
          ]),
        ),
        const Positioned(left: 10, top: 10, child: _Etiqueta('Letra sincronizada', icono: Icons.lyrics_rounded)),
      ]),
    );
  }
}

// ------------------------------------------------------------------ escuchen juntos

/// Dos personas con la misma canción, un chat que va apareciendo y reacciones que flotan.
class DemoJuntos extends StatefulWidget {
  const DemoJuntos({super.key, this.acento = const Color(0xFF22D3EE)});
  final Color acento;

  @override
  State<DemoJuntos> createState() => _DemoJuntosState();
}

class _DemoJuntosState extends _EstadoReloj<DemoJuntos> {
  static const _ciclo = 9.0;
  static const _chat = <(bool, String)>[
    (false, '¡esta parte me encanta! 🎶'),
    (true, 'súbele 🔊🔊'),
    (false, 'la ponemos otra vez?'),
    (true, 'siii 💜'),
  ];

  @override
  double get tQuieto => 7.5;

  @override
  Widget build(BuildContext context) {
    final c = t % _ciclo;
    final ac = widget.acento;
    Widget avatar(String l, Color col) => Container(
          width: 34,
          height: 34,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(colors: [col, Color.lerp(col, Colors.black, 0.35)!]),
            border: Border.all(color: Colors.white, width: 2),
          ),
          child: Text(l, style: const TextStyle(fontWeight: FontWeight.w900, color: Colors.white)),
        );
    return MarcoDemo(
      acento: ac,
      child: LayoutBuilder(builder: (context, k) {
        return Stack(children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [const Color(0xFF101A2E), Color.lerp(const Color(0xFF2A1240), ac, 0.15)!],
                ),
              ),
            ),
          ),
          // la canción compartida
          Positioned(
            left: 12,
            right: 12,
            top: 12,
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: const Color(0x22FFFFFF), borderRadius: BorderRadius.circular(16)),
              child: Row(children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    gradient: const LinearGradient(colors: [Color(0xFFFF6EC7), Color(0xFF6A5CFF)]),
                  ),
                  child: const Icon(Icons.music_note_rounded, color: Colors.white),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('Sonando para los dos',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Colors.white)),
                    const SizedBox(height: 6),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(3),
                      child: LinearProgressIndicator(
                        value: (c / _ciclo).clamp(0.0, 1.0),
                        minHeight: 4,
                        color: ac,
                        backgroundColor: const Color(0x33FFFFFF),
                      ),
                    ),
                  ]),
                ),
                const SizedBox(width: 8),
                SizedBox(
                  width: 54,
                  height: 34,
                  child: Stack(children: [
                    Positioned(left: 0, child: avatar('A', const Color(0xFFFF6E9A))),
                    Positioned(left: 20, child: avatar('M', const Color(0xFF4DA8FF))),
                  ]),
                ),
              ]),
            ),
          ),
          // el chat
          Positioned(
            left: 12,
            right: 12,
            bottom: 12,
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              for (var i = 0; i < _chat.length; i++)
                Builder(builder: (_) {
                  final a = ((c - 0.8 - i * 1.4) / 0.35).clamp(0.0, 1.0);
                  if (a <= 0) return const SizedBox.shrink();
                  final mio = _chat[i].$1;
                  return Opacity(
                    opacity: a,
                    child: Transform.translate(
                      offset: Offset(0, (1 - a) * 10),
                      child: Align(
                        alignment: mio ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.only(top: 5),
                          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
                          decoration: BoxDecoration(
                            color: mio ? ac.withValues(alpha: 0.85) : const Color(0x33FFFFFF),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Text(_chat[i].$2,
                              style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700,
                                  color: mio ? const Color(0xFF06121A) : Colors.white)),
                        ),
                      ),
                    ),
                  );
                }),
            ]),
          ),
          // reacciones que suben
          for (var i = 0; i < 6; i++)
            Builder(builder: (_) {
              final p = ((t * 0.45 + i / 6) % 1);
              final x = k.maxWidth * (0.55 + 0.35 * ((i * 0.618) % 1)) + math.sin(t * 2 + i) * 8;
              final y = k.maxHeight * (0.95 - 0.75 * p);
              return Positioned(
                left: x,
                top: y,
                child: Opacity(
                  opacity: (math.sin(p * math.pi)).clamp(0.0, 1.0),
                  child: Text(['❤️', '🔥', '🎶', '💜', '✨', '😍'][i], style: TextStyle(fontSize: 16 + 6 * p)),
                ),
              );
            }),
        ]);
      }),
    );
  }
}

// ------------------------------------------------------------------ descubre

/// Un carrusel de mezclas hechas para ti que pasa solo.
class DemoDescubre extends StatefulWidget {
  const DemoDescubre({super.key, this.acento = const Color(0xFF7CFFCB)});
  final Color acento;

  @override
  State<DemoDescubre> createState() => _DemoDescubreState();
}

class _DemoDescubreState extends _EstadoReloj<DemoDescubre> {
  static const _mezclas = <(String, String, List<Color>, IconData)>[
    ('Tu mezcla diaria', 'Lo que más escuchas', [Color(0xFFFF6EC7), Color(0xFF6A5CFF)], Icons.auto_awesome_rounded),
    ('Descubrimiento', 'Nuevo para ti', [Color(0xFF22D3EE), Color(0xFF1E3A8A)], Icons.explore_rounded),
    ('Lo-fi para estudiar', 'Concentración', [Color(0xFFFFB86B), Color(0xFF7C3AED)], Icons.menu_book_rounded),
    ('Energía', 'Para entrenar', [Color(0xFFFF3D00), Color(0xFFFFC53B)], Icons.bolt_rounded),
    ('Radio de tu artista', 'Sin fin', [Color(0xFF4BE06B), Color(0xFF0F766E)], Icons.radio_rounded),
    ('Para la noche', 'Calma', [Color(0xFF8A5CFF), Color(0xFF0B1026)], Icons.nightlight_round),
  ];

  @override
  Widget build(BuildContext context) {
    final ac = widget.acento;
    return MarcoDemo(
      acento: ac,
      child: LayoutBuilder(builder: (context, k) {
        final ancho = k.maxWidth * 0.42;
        final paso = ancho + 12;
        final total = paso * _mezclas.length;
        final desplaz = (t * 38) % total;
        return Stack(children: [
          const Positioned.fill(child: ColoredBox(color: Color(0xFF0D0B16))),
          Positioned(
            left: 14,
            top: 12,
            right: 14,
            child: Row(children: [
              Icon(Icons.favorite_rounded, color: ac, size: 16),
              const SizedBox(width: 6),
              const Expanded(
                child: Text('Hecho para ti',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: Colors.white)),
              ),
            ]),
          ),
          for (var vuelta = 0; vuelta < 2; vuelta++)
            for (var i = 0; i < _mezclas.length; i++)
              Builder(builder: (_) {
                final x = 14 + i * paso + vuelta * total - desplaz;
                if (x > k.maxWidth || x + ancho < 0) return const SizedBox.shrink();
                final centro = (x + ancho / 2 - k.maxWidth / 2).abs() / k.maxWidth;
                final esc = 1.0 - 0.12 * centro.clamp(0.0, 1.0);
                final m = _mezclas[i];
                return Positioned(
                  left: x,
                  top: 42,
                  width: ancho,
                  child: Transform.scale(
                    scale: esc,
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      AspectRatio(
                        aspectRatio: 1,
                        child: Container(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(14),
                            gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: m.$3),
                            boxShadow: [BoxShadow(color: m.$3.first.withValues(alpha: 0.4), blurRadius: 14)],
                          ),
                          child: Stack(children: [
                            Center(child: Icon(m.$4, size: ancho * 0.32, color: Colors.white.withValues(alpha: 0.9))),
                            Positioned(
                              right: 8,
                              bottom: 8,
                              child: Container(
                                width: 26,
                                height: 26,
                                decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                                child: const Icon(Icons.play_arrow_rounded, size: 18, color: Colors.black),
                              ),
                            ),
                          ]),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(m.$1, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: Colors.white)),
                      Text(m.$2, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 11, color: Color(0xAAFFFFFF))),
                    ]),
                  ),
                );
              }),
        ]);
      }),
    );
  }
}

// ------------------------------------------------------------------ mascotas

/// Las mascotas reales de Caudal paseando por un prado al atardecer.
class DemoMascotas extends StatefulWidget {
  const DemoMascotas({super.key, this.acento = const Color(0xFFFFC857)});
  final Color acento;

  @override
  State<DemoMascotas> createState() => _DemoMascotasState();
}

class _DemoMascotasState extends _EstadoReloj<DemoMascotas> {
  List<Mascota> _lista = const [];

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      await MascotaApp.i.cargarCatalogo();
    } catch (_) {}
    if (!mounted) return;
    setState(() => _lista = [for (final m in MascotaApp.i.catalogo) if (!m.esExclusiva) m].take(5).toList());
  }

  @override
  Widget build(BuildContext context) {
    return MarcoDemo(
      acento: widget.acento,
      child: LayoutBuilder(builder: (context, k) {
        final suelo = k.maxHeight * 0.78;
        return Stack(children: [
          Positioned.fill(child: CustomPaint(painter: _PradoPainter(t))),
          for (var i = 0; i < _lista.length; i++)
            Builder(builder: (_) {
              final m = _lista[i];
              final esc = (k.maxHeight * 0.2 / m.alto).clamp(1.5, 4.0);
              final w = m.ancho * esc;
              final h = m.alto * esc;
              final vel = 0.06 + 0.02 * (i % 3);
              final recorrido = k.maxWidth + w * 2;
              final p = (t * vel + i / _lista.length) % 1;
              final izqADer = i.isEven;
              final x = izqADer ? -w + p * recorrido : k.maxWidth - p * recorrido;
              final salto = (math.sin(t * 9 + i) .abs()) * 3;
              return Positioned(
                left: x,
                top: suelo - h + (i % 2) * 8 - salto,
                child: Transform(
                  alignment: Alignment.center,
                  transform: Matrix4.diagonal3Values(izqADer ? 1.0 : -1.0, 1.0, 1.0),
                  child: MascotaSprite(mascota: m, escala: esc, animar: !quieto),
                ),
              );
            }),
          const Positioned(left: 10, top: 10, child: _Etiqueta('Te acompañan mientras escuchas', icono: Icons.pets_rounded)),
        ]);
      }),
    );
  }
}

class _PradoPainter extends CustomPainter {
  _PradoPainter(this.t);
  final double t;

  @override
  void paint(Canvas canvas, Size z) {
    final cielo = Rect.fromLTWH(0, 0, z.width, z.height);
    canvas.drawRect(
      cielo,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF2B1B6B), Color(0xFFFF6E9A), Color(0xFFFFB86B)],
          stops: [0, 0.55, 0.8],
        ).createShader(cielo),
    );
    // sol
    final sol = Offset(z.width * 0.72, z.height * 0.6);
    canvas.drawCircle(sol, z.height * 0.32, Paint()..color = const Color(0x33FFE6A0));
    canvas.drawCircle(sol, z.height * 0.17, Paint()..color = const Color(0xFFFFE6A0));
    // colinas
    final colina = Path()..moveTo(0, z.height * 0.72);
    for (var x = 0.0; x <= z.width; x += 8) {
      colina.lineTo(x, z.height * 0.70 + math.sin(x / z.width * 5 + 1) * z.height * 0.04);
    }
    colina
      ..lineTo(z.width, z.height)
      ..lineTo(0, z.height)
      ..close();
    canvas.drawPath(colina, Paint()..color = const Color(0xFF3B7D4F));
    canvas.drawRect(Rect.fromLTWH(0, z.height * 0.78, z.width, z.height * 0.22), Paint()..color = const Color(0xFF2E6B40));
    // briznas que se mecen
    final hierba = Paint()
      ..color = const Color(0xFF5DBB63)
      ..strokeWidth = 1.6
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < 46; i++) {
      final x = z.width * ((i * 0.618034) % 1);
      final y = z.height * (0.8 + 0.18 * ((i * 0.37) % 1));
      final m = math.sin(t * 2 + i) * 3;
      canvas.drawLine(Offset(x, y), Offset(x + m, y - 7), hierba);
    }
    // luciérnagas
    for (var i = 0; i < 10; i++) {
      final x = z.width * ((i * 0.31 + t * 0.02) % 1);
      final y = z.height * (0.25 + 0.4 * ((i * 0.53) % 1)) + math.sin(t + i) * 6;
      final a = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * 3 + i * 2));
      canvas.drawCircle(Offset(x, y), 2, Paint()..color = const Color(0xFFFFF3B0).withValues(alpha: a));
    }
  }

  @override
  bool shouldRepaint(covariant _PradoPainter old) => old.t != t;
}

// ------------------------------------------------------------------ gamer

/// La barra de experiencia se llena, las misiones se tachan y sube de nivel.
class DemoGamer extends StatefulWidget {
  const DemoGamer({super.key, this.acento = const Color(0xFF7CFF6B)});
  final Color acento;

  @override
  State<DemoGamer> createState() => _DemoGamerState();
}

class _DemoGamerState extends _EstadoReloj<DemoGamer> {
  static const _ciclo = 7.0;
  static const _misiones = ['Escucha 3 canciones nuevas', 'Comparte una canción', 'Escucha 20 minutos'];

  @override
  double get tQuieto => 5.5;

  @override
  Widget build(BuildContext context) {
    final c = t % _ciclo;
    final ac = widget.acento;
    final xp = Curves.easeInOut.transform((c / 4.2).clamp(0.0, 1.0));
    final sube = ((c - 4.3) / 0.5).clamp(0.0, 1.0);
    final nivel = sube > 0 ? 12 : 11;
    return MarcoDemo(
      acento: ac,
      child: Stack(children: [
        const Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFF0B1A10), Color(0xFF050A07)],
              ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(color: ac, borderRadius: BorderRadius.circular(8)),
                child: Text('NV $nivel',
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: Color(0xFF06120A))),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Text('Modo gamer',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: Colors.white)),
              ),
              Text('${(xp * 500).round()}/500 XP',
                  style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: ac)),
            ]),
            const SizedBox(height: 10),
            Container(
              height: 12,
              decoration: BoxDecoration(color: const Color(0x22FFFFFF), borderRadius: BorderRadius.circular(6)),
              child: FractionallySizedBox(
                alignment: Alignment.centerLeft,
                widthFactor: sube > 0 ? 1 : xp,
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(6),
                    gradient: LinearGradient(colors: [ac, Colors.white]),
                    boxShadow: [BoxShadow(color: ac.withValues(alpha: 0.7), blurRadius: 10)],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            for (var i = 0; i < _misiones.length; i++)
              Builder(builder: (_) {
                final hecha = c > 1.0 + i * 1.2;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(children: [
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 250),
                      width: 20,
                      height: 20,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: hecha ? ac : Colors.transparent,
                        border: Border.all(color: ac, width: 2),
                      ),
                      child: hecha ? const Icon(Icons.check_rounded, size: 14, color: Color(0xFF06120A)) : null,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(_misiones[i],
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w700,
                            color: hecha ? const Color(0x88FFFFFF) : Colors.white,
                            decoration: hecha ? TextDecoration.lineThrough : null,
                          )),
                    ),
                    Text('+150', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: ac)),
                  ]),
                );
              }),
          ]),
        ),
        if (sube > 0)
          Positioned.fill(
            child: ColoredBox(
              color: Color.fromRGBO(0, 0, 0, 0.6 * sube),
              child: Center(
                child: Transform.scale(
                  scale: Curves.easeOutBack.transform(sube),
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.emoji_events_rounded, size: 52, color: ac),
                    const SizedBox(height: 4),
                    Text('¡Subiste al nivel 12!',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w900,
                          color: Colors.white,
                          shadows: [Shadow(color: ac, blurRadius: 18)],
                        )),
                  ]),
                ),
              ),
            ),
          ),
      ]),
    );
  }
}

// ------------------------------------------------------------------ estudio

/// El reloj de enfoque con un lo-fi de fondo.
class DemoEstudio extends StatefulWidget {
  const DemoEstudio({super.key, this.acento = const Color(0xFFFFB86B)});
  final Color acento;

  @override
  State<DemoEstudio> createState() => _DemoEstudioState();
}

class _DemoEstudioState extends _EstadoReloj<DemoEstudio> {
  @override
  Widget build(BuildContext context) {
    final ac = widget.acento;
    // 25 minutos que «pasan» en 10 s de demo
    final resta = 1 - ((t % 10) / 10);
    final seg = (resta * 25 * 60).round();
    final mm = (seg ~/ 60).toString().padLeft(2, '0');
    final ss = (seg % 60).toString().padLeft(2, '0');
    return MarcoDemo(
      acento: ac,
      child: Stack(fit: StackFit.expand, children: [
        const EscenarioFondo(clave: 'lofi', interactivo: false),
        const ColoredBox(color: Color(0x88000000)),
        Center(
          child: SizedBox(
            width: 150,
            height: 150,
            child: Stack(fit: StackFit.expand, children: [
              CircularProgressIndicator(
                value: resta,
                strokeWidth: 8,
                color: ac,
                backgroundColor: const Color(0x33FFFFFF),
                strokeCap: StrokeCap.round,
              ),
              Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Text('$mm:$ss',
                    style: const TextStyle(
                      fontSize: 34,
                      fontWeight: FontWeight.w900,
                      color: Colors.white,
                      fontFeatures: [FontFeature.tabularFigures()],
                    )),
                Text('Enfoque', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: ac)),
              ]),
            ]),
          ),
        ),
        const Positioned(left: 10, top: 10, child: _Etiqueta('Modo estudio', icono: Icons.menu_book_rounded)),
        const Positioned(right: 10, bottom: 10, child: _Etiqueta('Lo-fi sonando', icono: Icons.headphones_rounded)),
      ]),
    );
  }
}

// ------------------------------------------------------------------ donadores: mi perfil

/// Los datos del perfil del donador para [DemoMiPerfil].
@immutable
class PerfilDonadorDemo {
  const PerfilDonadorDemo({
    required this.nombre,
    this.fotoUrl = '',
    this.marco = 'oro',
    this.efecto = 'brillo',
    this.colorNombre,
    this.fundador = false,
    this.tema = 'ninguno',
    this.enPared = false,
  });

  final String nombre, fotoUrl, marco, efecto, tema;
  final String? colorNombre;
  final bool fundador, enPared;

  /// Las insignias que se le enseñan (lo que ya tiene).
  List<(IconData, String)> get insignias => [
        (Icons.workspace_premium_rounded, fundador ? 'Fundador' : 'Donador'),
        if (AvatarMarco.tiene(marco)) (Icons.filter_frames_rounded, 'Marco ${marcosAvatar[marco]!.nombre}'),
        if (efecto != 'ninguno') (Icons.text_fields_rounded, 'Nombre ${_nombreEfecto(efecto)}'),
        if (tema != 'ninguno') (Icons.palette_rounded, 'Estética propia'),
        if (enPared) (Icons.groups_rounded, 'En el muro'),
        (Icons.landscape_rounded, 'Escenarios vivos'),
      ];

  static String _nombreEfecto(String e) => switch (e) {
        'brillo' => 'con brillo',
        'degradado' => 'degradado',
        'arcoiris' => 'arcoíris',
        'neon' => 'neón',
        _ => e,
      };
}

/// El perfil real del donador: su foto (o inicial), su marco animado, su nombre con su efecto y sus insignias.
class DemoMiPerfil extends StatefulWidget {
  const DemoMiPerfil({super.key, required this.perfil, this.acento = const Color(0xFFF5C04A)});
  final PerfilDonadorDemo perfil;
  final Color acento;

  @override
  State<DemoMiPerfil> createState() => _DemoMiPerfilState();
}

class _DemoMiPerfilState extends _EstadoReloj<DemoMiPerfil> {
  @override
  Widget build(BuildContext context) {
    final p = widget.perfil;
    final ac = widget.acento;
    // si aún no eligió marco o efecto se le enseña cómo se vería con Oro y Brillo
    final marco = AvatarMarco.tiene(p.marco) ? p.marco : 'oro';
    final efecto = p.efecto == 'ninguno' ? 'brillo' : p.efecto;
    final color = p.colorNombre == null ? null : _hex(p.colorNombre!);
    final nombre = p.nombre.isEmpty ? 'Tú' : p.nombre;
    const radio = 46.0;
    final interno = AvatarMarco.radioInterno(marco, radio);
    final inicial = nombre.characters.first.toUpperCase();
    Widget avatarSinFoto() => Container(
          alignment: Alignment.center,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(colors: [ac, Color.lerp(ac, const Color(0xFF7A3B00), 0.6)!]),
          ),
          child: Text(inicial, style: TextStyle(fontSize: interno, fontWeight: FontWeight.w900, color: Colors.white)),
        );
    final avatar = SizedBox(
      width: interno * 2,
      height: interno * 2,
      child: ClipOval(
        child: p.fotoUrl.isEmpty
            ? avatarSinFoto()
            : CachedNetworkImage(
                imageUrl: p.fotoUrl,
                fit: BoxFit.cover,
                placeholder: (_, _) => avatarSinFoto(),
                errorWidget: (_, _, _) => avatarSinFoto(),
              ),
      ),
    );
    final brillo = 0.5 + 0.5 * math.sin(t * 2.2);
    return MarcoDemo(
      acento: ac,
      proporcion: 1.0,
      child: Stack(children: [
        // portada
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color.lerp(const Color(0xFF3A2405), ac, 0.25 + 0.1 * brillo)!, const Color(0xFF0E0A06)],
                stops: const [0, 0.55],
              ),
            ),
          ),
        ),
        Positioned.fill(child: CustomPaint(painter: _DestellosPainter(t, ac))),
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 18, 14, 14),
          child: Column(children: [
            AvatarMarco(marco: marco, radio: radio, animar: !quieto, child: avatar),
            const SizedBox(height: 10),
            NombreEfecto(
              nombre,
              efecto: efecto,
              color: color,
              animar: !quieto,
              textAlign: TextAlign.center,
              estilo: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900, letterSpacing: -0.3),
            ),
            const SizedBox(height: 4),
            Text(p.fundador ? 'Fundador de Caudal' : 'Donador de Caudal',
                style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: ac)),
            const Spacer(),
            Wrap(
              alignment: WrapAlignment.center,
              spacing: 6,
              runSpacing: 6,
              children: [
                for (var i = 0; i < p.insignias.length; i++)
                  Builder(builder: (_) {
                    final a = quieto ? 1.0 : ((t - 0.3 - i * 0.18) / 0.4).clamp(0.0, 1.0);
                    final ins = p.insignias[i];
                    return Opacity(
                      opacity: a,
                      child: Transform.scale(
                        scale: 0.7 + 0.3 * Curves.easeOutBack.transform(a),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                          decoration: BoxDecoration(
                            color: ac.withValues(alpha: 0.14),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: ac.withValues(alpha: 0.55)),
                          ),
                          child: Row(mainAxisSize: MainAxisSize.min, children: [
                            Icon(ins.$1, size: 13, color: ac),
                            const SizedBox(width: 4),
                            Text(ins.$2,
                                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFFFFF6E0))),
                          ]),
                        ),
                      ),
                    );
                  }),
              ],
            ),
          ]),
        ),
      ]),
    );
  }
}

class _DestellosPainter extends CustomPainter {
  _DestellosPainter(this.t, this.color);
  final double t;
  final Color color;

  @override
  void paint(Canvas canvas, Size z) {
    for (var i = 0; i < 18; i++) {
      final x = z.width * ((i * 0.618034) % 1);
      final y = z.height * (0.05 + 0.5 * ((i * 0.377) % 1));
      final a = math.pow(0.5 + 0.5 * math.sin(t * 2.4 + i * 1.7), 4).toDouble();
      final r = 1.5 + 2.5 * a;
      final pintura = Paint()..color = color.withValues(alpha: 0.85 * a);
      canvas.drawCircle(Offset(x, y), r * 0.5, pintura);
      final rayo = Paint()
        ..color = color.withValues(alpha: 0.6 * a)
        ..strokeWidth = 1;
      canvas.drawLine(Offset(x - r * 2, y), Offset(x + r * 2, y), rayo);
      canvas.drawLine(Offset(x, y - r * 2), Offset(x, y + r * 2), rayo);
    }
  }

  @override
  bool shouldRepaint(covariant _DestellosPainter old) => old.t != t;
}

// ------------------------------------------------------------------ donadores: marcos y nombres

/// Los marcos reales pasando uno tras otro, con los efectos de nombre reales.
class DemoMarcos extends StatefulWidget {
  const DemoMarcos({super.key, required this.nombre, this.acento = const Color(0xFFF5C04A)});
  final String nombre;
  final Color acento;

  @override
  State<DemoMarcos> createState() => _DemoMarcosState();
}

class _DemoMarcosState extends _EstadoReloj<DemoMarcos> {
  static final _marcos = marcosAvatar.keys.toList();
  static const _efectos = ['brillo', 'degradado', 'arcoiris', 'neon'];

  @override
  Widget build(BuildContext context) {
    final i = (t / 2.2).floor();
    final clave = _marcos[i % _marcos.length];
    final efecto = _efectos[i % _efectos.length];
    final estilo = marcosAvatar[clave]!;
    final nombre = widget.nombre.isEmpty ? 'Tu nombre' : widget.nombre;
    const radio = 50.0;
    final interno = AvatarMarco.radioInterno(clave, radio);
    return MarcoDemo(
      acento: estilo.colores.first,
      child: Stack(children: [
        Positioned.fill(
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 600),
            decoration: BoxDecoration(
              gradient: RadialGradient(
                radius: 1.0,
                colors: [estilo.colores.first.withValues(alpha: 0.35), const Color(0xFF07060C)],
              ),
            ),
          ),
        ),
        Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 450),
              transitionBuilder: (h, a) => ScaleTransition(scale: a, child: FadeTransition(opacity: a, child: h)),
              child: AvatarMarco(
                key: ValueKey(clave),
                marco: clave,
                radio: radio,
                animar: !quieto,
                child: Container(
                  width: interno * 2,
                  height: interno * 2,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(colors: [Color(0xFF3A3550), Color(0xFF1B1828)]),
                  ),
                  child: Icon(Icons.person_rounded, size: interno * 1.2, color: const Color(0xCCFFFFFF)),
                ),
              ),
            ),
            const SizedBox(height: 12),
            NombreEfecto(
              nombre,
              key: ValueKey(efecto),
              efecto: efecto,
              animar: !quieto,
              textAlign: TextAlign.center,
              estilo: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            _Etiqueta('Marco ${estilo.nombre}', icono: Icons.filter_frames_rounded, color: estilo.colores.first),
          ]),
        ),
      ]),
    );
  }
}

// ------------------------------------------------------------------ donadores: estéticas

/// Una maqueta de Caudal que va cambiando de estética.
class DemoTemas extends StatefulWidget {
  const DemoTemas({super.key});

  @override
  State<DemoTemas> createState() => _DemoTemasState();
}

class _DemoTemasState extends _EstadoReloj<DemoTemas> {
  static const _temas = <(String, Color, Color, Color)>[
    // nombre, fondo, superficie, acento
    ('Cyberpunk', Color(0xFF0A0618), Color(0xFF1C0F35), Color(0xFFFF2DAA)),
    ('Kuromi', Color(0xFF15101C), Color(0xFF2A1F38), Color(0xFFB98CFF)),
    ('Japón samurái', Color(0xFF1A0B0B), Color(0xFF341614), Color(0xFFFF5A4E)),
    ('Cinnamoroll', Color(0xFF0E1A2A), Color(0xFF1C3250), Color(0xFF8FD3FF)),
    ('Lo-fi', Color(0xFF1B1410), Color(0xFF33261C), Color(0xFFFFB86B)),
    ('Hello Kitty', Color(0xFF220C14), Color(0xFF3D1626), Color(0xFFFF6E9A)),
    ('Retro', Color(0xFF0D1020), Color(0xFF1E2440), Color(0xFF35F0C0)),
  ];

  @override
  Widget build(BuildContext context) {
    final i = (t / 2.0).floor() % _temas.length;
    final (nombre, fondo, sup, ac) = _temas[i];
    const d = Duration(milliseconds: 650);
    Widget fila(double ancho) => Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(children: [
            AnimatedContainer(
              duration: d,
              width: 34,
              height: 34,
              decoration: BoxDecoration(color: ac.withValues(alpha: 0.75), borderRadius: BorderRadius.circular(8)),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                FractionallySizedBox(
                  widthFactor: ancho,
                  child: Container(height: 8, decoration: BoxDecoration(color: const Color(0xCCFFFFFF), borderRadius: BorderRadius.circular(4))),
                ),
                const SizedBox(height: 5),
                FractionallySizedBox(
                  widthFactor: ancho * 0.6,
                  child: Container(height: 6, decoration: BoxDecoration(color: const Color(0x66FFFFFF), borderRadius: BorderRadius.circular(3))),
                ),
              ]),
            ),
          ]),
        );
    return MarcoDemo(
      acento: ac,
      child: AnimatedContainer(
        duration: d,
        color: fondo,
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            AnimatedDefaultTextStyle(
              duration: d,
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: ac),
              child: const Text('Caudal'),
            ),
            const Spacer(),
            Flexible(
              flex: 3,
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 350),
                child: FittedBox(
                  key: ValueKey(nombre),
                  fit: BoxFit.scaleDown,
                  child: _Etiqueta(nombre, icono: Icons.palette_rounded, color: ac),
                ),
              ),
            ),
          ]),
          const SizedBox(height: 12),
          fila(0.8),
          fila(0.6),
          fila(0.7),
          const Spacer(),
          AnimatedContainer(
            duration: d,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: sup,
              borderRadius: BorderRadius.circular(14),
              boxShadow: [BoxShadow(color: ac.withValues(alpha: 0.35), blurRadius: 16)],
            ),
            child: Row(children: [
              AnimatedContainer(
                duration: d,
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  gradient: LinearGradient(colors: [ac, Color.lerp(ac, Colors.black, 0.5)!]),
                ),
                child: const Icon(Icons.music_note_rounded, color: Colors.white, size: 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(3),
                  child: LinearProgressIndicator(
                    value: (t % 6) / 6,
                    minHeight: 4,
                    color: ac,
                    backgroundColor: const Color(0x33FFFFFF),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Icon(Icons.pause_circle_filled_rounded, color: ac, size: 32),
            ]),
          ),
        ]),
      ),
    );
  }
}

// ------------------------------------------------------------------ donadores: ecualizador

/// El ecualizador avanzado moviendo sus bandas entre preajustes.
class DemoEcualizador extends StatefulWidget {
  const DemoEcualizador({super.key, this.acento = const Color(0xFFF5C04A)});
  final Color acento;

  @override
  State<DemoEcualizador> createState() => _DemoEcualizadorState();
}

class _DemoEcualizadorState extends _EstadoReloj<DemoEcualizador> {
  static const _presets = <(String, List<double>)>[
    ('Graves potentes', [0.9, 0.85, 0.7, 0.55, 0.5, 0.48, 0.5, 0.55, 0.6, 0.62]),
    ('Voz clara', [0.4, 0.42, 0.48, 0.6, 0.78, 0.82, 0.7, 0.58, 0.52, 0.5]),
    ('Se adapta a la canción', [0.62, 0.7, 0.58, 0.5, 0.6, 0.66, 0.58, 0.7, 0.8, 0.74]),
    ('Brillo', [0.45, 0.45, 0.5, 0.5, 0.55, 0.6, 0.7, 0.82, 0.9, 0.92]),
  ];

  @override
  Widget build(BuildContext context) {
    final ac = widget.acento;
    final n = (t / 2.6).floor();
    final a = _presets[n % _presets.length];
    final b = _presets[(n + 1) % _presets.length];
    final f = Curves.easeInOutCubic.transform(((t % 2.6) - 1.8).clamp(0.0, 0.8) / 0.8);
    final valores = [for (var i = 0; i < 10; i++) a.$2[i] + (b.$2[i] - a.$2[i]) * f];
    final nombre = f < 0.5 ? a.$1 : b.$1;
    return MarcoDemo(
      acento: ac,
      child: Stack(children: [
        const Positioned.fill(child: ColoredBox(color: Color(0xFF0E0A06))),
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          child: Column(children: [
            Row(children: [
              Icon(Icons.equalizer_rounded, color: ac, size: 18),
              const SizedBox(width: 6),
              const Expanded(
                child: Text('Ecualizador',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: Colors.white)),
              ),
              Flexible(
                flex: 2,
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 300),
                  child: FittedBox(
                    key: ValueKey(nombre),
                    fit: BoxFit.scaleDown,
                    child: _Etiqueta(nombre, color: ac),
                  ),
                ),
              ),
            ]),
            const SizedBox(height: 10),
            Expanded(child: CustomPaint(painter: _EqPainter(valores, ac, t), size: Size.infinite)),
            const SizedBox(height: 6),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                for (final h in ['32', '64', '125', '250', '500', '1k', '2k', '4k', '8k', '16k'])
                  Text(h, style: const TextStyle(fontSize: 9, color: Color(0x99FFFFFF))),
              ],
            ),
          ]),
        ),
      ]),
    );
  }
}

class _EqPainter extends CustomPainter {
  _EqPainter(this.v, this.color, this.t);
  final List<double> v;
  final Color color;
  final double t;

  @override
  void paint(Canvas canvas, Size z) {
    final n = v.length;
    final paso = z.width / (n - 1);
    final pts = [for (var i = 0; i < n; i++) Offset(i * paso, z.height * (1 - v[i]))];
    // rejilla
    final rej = Paint()
      ..color = const Color(0x18FFFFFF)
      ..strokeWidth = 1;
    for (var i = 1; i < 4; i++) {
      canvas.drawLine(Offset(0, z.height * i / 4), Offset(z.width, z.height * i / 4), rej);
    }
    final curva = Path()..moveTo(pts.first.dx, pts.first.dy);
    for (var i = 0; i < n - 1; i++) {
      final m = Offset((pts[i].dx + pts[i + 1].dx) / 2, (pts[i].dy + pts[i + 1].dy) / 2);
      curva.quadraticBezierTo(pts[i].dx, pts[i].dy, m.dx, m.dy);
    }
    curva.lineTo(pts.last.dx, pts.last.dy);
    final relleno = Path.from(curva)
      ..lineTo(z.width, z.height)
      ..lineTo(0, z.height)
      ..close();
    canvas.drawPath(
      relleno,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [color.withValues(alpha: 0.45), color.withValues(alpha: 0.0)],
        ).createShader(Offset.zero & z),
    );
    canvas.drawPath(
      curva,
      Paint()
        ..color = color.withValues(alpha: 0.5)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 7
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5),
    );
    canvas.drawPath(
      curva,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.6,
    );
    for (final p in pts) {
      canvas.drawCircle(p, 5.5, Paint()..color = const Color(0xFF0E0A06));
      canvas.drawCircle(p, 4, Paint()..color = Colors.white);
    }
    // barras de espectro bajo la curva
    final barra = Paint()..color = const Color(0x22FFFFFF);
    for (var i = 0; i < 28; i++) {
      final h = z.height * 0.3 * (0.3 + 0.7 * (0.5 + 0.5 * math.sin(t * 6 + i * 0.9)).abs());
      final x = z.width * i / 28;
      canvas.drawRRect(
        RRect.fromRectAndRadius(Rect.fromLTWH(x + 1, z.height - h, z.width / 28 - 2, h), const Radius.circular(2)),
        barra,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _EqPainter old) => true;
}

/// Para las pruebas: una demo de cada tipo.
@visibleForTesting
final List<Widget Function()> todasLasDemos = [
  () => const DemoEscenarios(),
  () => const DemoLetra(),
  () => const DemoJuntos(),
  () => const DemoDescubre(),
  () => const DemoMascotas(),
  () => const DemoGamer(),
  () => const DemoEstudio(),
  () => const DemoMiPerfil(perfil: PerfilDonadorDemo(nombre: 'Aligeri', marco: 'galaxia', efecto: 'arcoiris', enPared: true, fundador: true)),
  () => const DemoMarcos(nombre: 'Aligeri'),
  () => const DemoTemas(),
  () => const DemoEcualizador(),
];
