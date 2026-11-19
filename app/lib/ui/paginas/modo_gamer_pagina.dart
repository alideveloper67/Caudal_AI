// «Modo gamer»: interruptor, ahorro al jugar, sonido por tipo de juego, listas
// por situación, nivel/XP/misiones/racha y un borde RGB neón.
//
// Ligero a propósito: un solo reloj (el del borde) y solo mientras la pantalla
// se ve; con «quitar animaciones» o el modo ligero el borde se queda quieto.

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../nucleo/gamer.dart';
import '../../nucleo/gamer_control.dart';
import '../../nucleo/gamer_xp.dart';
import '../tema.dart';

const _neon = [
  Color(0xFF00F5FF),
  Color(0xFF7C5CFF),
  Color(0xFFFF2E93),
  Color(0xFFFFD60A),
  Color(0xFF00FF9C),
  Color(0xFF00F5FF),
];

class _PintorRgb extends CustomPainter {
  _PintorRgb(this.fase, this.radio, this.grosor, this.vivo) : super(repaint: fase);
  final Animation<double> fase;
  final double radio, grosor;
  final bool vivo;

  @override
  void paint(Canvas canvas, Size size) {
    final r = Offset.zero & size;
    final rr = RRect.fromRectAndRadius(r.deflate(grosor / 2), Radius.circular(radio));
    final sombra = SweepGradient(colors: _neon, transform: GradientRotation(fase.value * 2 * math.pi)).createShader(r);
    // el resplandor: un trazo más ancho y tenue (sin desenfoque, que pesa en equipos viejos)
    canvas.drawRRect(
        rr,
        Paint()
          ..shader = sombra
          ..style = PaintingStyle.stroke
          ..strokeWidth = grosor * 2.6
          ..color = const Color(0x33FFFFFF)
          ..colorFilter = const ColorFilter.mode(Color(0x38FFFFFF), BlendMode.modulate));
    canvas.drawRRect(
        rr,
        Paint()
          ..shader = sombra
          ..style = PaintingStyle.stroke
          ..strokeWidth = grosor);
  }

  @override
  bool shouldRepaint(_PintorRgb o) => o.radio != radio || o.grosor != grosor || o.vivo != vivo;
}

/// Contenedor con borde RGB que gira. Quieto si hay «quitar animaciones» o [animado] es falso.
class BordeRgb extends StatefulWidget {
  const BordeRgb({super.key, required this.child, this.radio = 20, this.grosor = 2, this.animado = true});
  final Widget child;
  final double radio, grosor;
  final bool animado;

  @override
  State<BordeRgb> createState() => _BordeRgbState();
}

class _BordeRgbState extends State<BordeRgb> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(seconds: 7));

  bool _corre = false;

  void _ajustar(bool quiere) {
    if (quiere == _corre) return;
    _corre = quiere;
    if (quiere) {
      _c.repeat();
    } else {
      _c.stop();
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _ajustar(widget.animado && !MediaQuery.disableAnimationsOf(context));
  }

  @override
  void didUpdateWidget(BordeRgb old) {
    super.didUpdateWidget(old);
    _ajustar(widget.animado && !MediaQuery.disableAnimationsOf(context));
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => RepaintBoundary(
        child: CustomPaint(
          foregroundPainter: _PintorRgb(_c, widget.radio, widget.grosor, widget.animado),
          child: Padding(
            padding: EdgeInsets.all(widget.grosor),
            child: ClipRRect(borderRadius: BorderRadius.circular(math.max(0, widget.radio - widget.grosor)), child: widget.child),
          ),
        ),
      );
}

const _iconosSituacion = {
  Situacion.lobby: Icons.sports_esports_rounded,
  Situacion.concentracion: Icons.center_focus_strong_rounded,
  Situacion.clutch: Icons.bolt_rounded,
  Situacion.victoria: Icons.emoji_events_rounded,
  Situacion.derrota: Icons.nightlight_round,
};

class ModoGamerPagina extends StatelessWidget {
  const ModoGamerPagina({super.key, required this.control});
  final ModoGamerControl control;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: C.fondoVivo,
        appBar: AppBar(title: const Text('Modo gamer')),
        body: ListenableBuilder(
          listenable: control,
          builder: (context, _) => ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              _Principal(control: control),
              const SizedBox(height: 14),
              _TarjetaNivel(control: control),
              const SizedBox(height: 18),
              // todo lo demás espera al interruptor
              Opacity(
                opacity: control.activo ? 1 : 0.45,
                child: AbsorbPointer(
                  absorbing: !control.activo,
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    _Misiones(control: control),
                    const SizedBox(height: 18),
                    _Ahorro(control: control),
                    const SizedBox(height: 18),
                    _Sonido(control: control),
                    const SizedBox(height: 18),
                    _Situaciones(control: control),
                  ]),
                ),
              ),
            ],
          ),
        ),
      );
}

Widget _titulo(String t, [String? sub]) => Padding(
      padding: const EdgeInsets.only(bottom: 8, left: 2),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(t, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
        if (sub != null) Text(sub, style: estiloSecundario),
      ]),
    );

class _Principal extends StatelessWidget {
  const _Principal({required this.control});
  final ModoGamerControl control;

  @override
  Widget build(BuildContext context) {
    return BordeRgb(
      animado: control.activo,
      child: Material(
        color: C.superficie,
        child: SwitchListTile.adaptive(
          contentPadding: const EdgeInsets.fromLTRB(16, 6, 12, 6),
          secondary: Icon(Icons.sports_esports_rounded, color: control.activo ? _neon[0] : C.texto2, size: 30),
          title: const Text('Modo gamer', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
          subtitle: Text(
              control.activo
                  ? 'Activo: sumas XP al escuchar y tienes tus ajustes de juego.'
                  : 'Actívalo para jugar con ahorro, sonido a medida, listas y niveles.',
              style: estiloSecundario),
          value: control.activo,
          onChanged: control.activar,
        ),
      ),
    );
  }
}

class _TarjetaNivel extends StatelessWidget {
  const _TarjetaNivel({required this.control});
  final ModoGamerControl control;

  @override
  Widget build(BuildContext context) {
    final p = control.progreso.alDia(control.ahora);
    final racha = p.rachaVigente(control.ahora);
    final tope = p.nivel >= nivelMaximo;
    return BordeRgb(
      animado: control.activo,
      child: Container(
        color: C.superficie,
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              width: 58,
              height: 58,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: C.superficie2,
                border: Border.all(color: _neon[2], width: 2),
              ),
              child: Text('${p.nivel}', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Nivel ${p.nivel}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                const SizedBox(height: 2),
                Text(
                  tope ? 'Nivel máximo' : '${p.xp - p.xpNivelActual} / ${p.xpSiguiente - p.xpNivelActual} XP para el ${p.nivel + 1}',
                  style: estiloSecundario,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ]),
            ),
          ]),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
                value: p.fraccion, minHeight: 8, color: _neon[0], backgroundColor: C.superficie3),
          ),
          const SizedBox(height: 14),
          Wrap(spacing: 8, runSpacing: 8, children: [
            _Dato(Icons.local_fire_department_rounded, racha == 1 ? '1 día de racha' : '$racha días de racha', _neon[3]),
            _Dato(Icons.timer_outlined, '${p.minutosHoy} min hoy', _neon[4]),
            _Dato(Icons.bolt_rounded, '${p.xp} XP', _neon[1]),
          ]),
        ]),
      ),
    );
  }
}

class _Dato extends StatelessWidget {
  const _Dato(this.icono, this.texto, this.color);
  final IconData icono;
  final String texto;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(20)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icono, size: 16, color: color),
          const SizedBox(width: 6),
          Flexible(child: Text(texto, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600), overflow: TextOverflow.ellipsis)),
        ]),
      );
}

class _Misiones extends StatelessWidget {
  const _Misiones({required this.control});
  final ModoGamerControl control;

  @override
  Widget build(BuildContext context) {
    final p = control.progreso.alDia(control.ahora);
    final misiones = misionesDelDia(control.ahora);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _titulo('Misiones de hoy', 'Se renuevan cada día y dan XP extra'),
      for (final m in misiones)
        Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(14)),
          child: Row(children: [
            Icon(p.misionHecha(m) ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                color: p.misionHecha(m) ? C.exito : C.texto3),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(m.titulo, style: const TextStyle(fontWeight: FontWeight.w700), maxLines: 2, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                      value: (p.valorMision(m) / m.meta).clamp(0.0, 1.0),
                      minHeight: 5,
                      color: p.misionHecha(m) ? C.exito : C.acento,
                      backgroundColor: C.superficie3),
                ),
                const SizedBox(height: 4),
                Text('${math.min(p.valorMision(m), m.meta)} / ${m.meta} ${m.unidad}', style: estiloSecundario),
              ]),
            ),
            const SizedBox(width: 10),
            Text('+${m.xp} XP', style: TextStyle(fontWeight: FontWeight.w800, color: C.acento, fontSize: 13)),
          ]),
        ),
    ]);
  }
}

class _Ahorro extends StatelessWidget {
  const _Ahorro({required this.control});
  final ModoGamerControl control;

  @override
  Widget build(BuildContext context) => Material(
        color: C.superficie,
        borderRadius: BorderRadius.circular(14),
        clipBehavior: Clip.antiAlias,
        child: SwitchListTile.adaptive(
          secondary: Icon(Icons.battery_saver_rounded, color: C.acento),
          title: const Text('Ahorro al jugar', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text(
              'Activa el modo ligero y esconde la mascota y el personaje del fondo. '
              'Al apagar el modo gamer, todo vuelve a como estaba.',
              style: estiloSecundario),
          value: control.ahorro,
          onChanged: control.ponerAhorro,
        ),
      );
}

class _Sonido extends StatelessWidget {
  const _Sonido({required this.control});
  final ModoGamerControl control;

  @override
  Widget build(BuildContext context) {
    final actual = control.perfil;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _titulo('Sonido por tipo de juego', 'Usa tu ecualizador; la calidad no cambia'),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final pf in perfilesSonido)
          ChoiceChip(
            label: Text(pf.nombre.replaceFirst('Gamer · ', '')),
            selected: actual?.id == pf.id,
            onSelected: (v) => control.elegirPerfil(v ? pf : null),
          ),
      ]),
      Padding(
        padding: const EdgeInsets.only(top: 8, left: 2),
        child: Text(actual?.detalle ?? 'Sin perfil: tu ecualizador queda como lo tenías.', style: estiloSecundario),
      ),
    ]);
  }
}

class _Situaciones extends StatelessWidget {
  const _Situaciones({required this.control});
  final ModoGamerControl control;

  Future<void> _pulsar(BuildContext context, Situacion s) async {
    final messenger = ScaffoldMessenger.maybeOf(context);
    final error = await control.ponerSituacion(s);
    if (error != null) {
      messenger?.hideCurrentSnackBar();
      messenger?.showSnackBar(SnackBar(content: Text(error)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _titulo('Listas por situación', 'Cada una arranca una radio en YouTube Music'),
      ValueListenableBuilder<Situacion?>(
        valueListenable: control.cargando,
        builder: (_, cargando, __) => Column(children: [
          for (final s in Situacion.values)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Material(
                color: C.superficie,
                borderRadius: BorderRadius.circular(14),
                clipBehavior: Clip.antiAlias,
                child: ListTile(
                enabled: cargando == null,
                leading: Icon(_iconosSituacion[s], color: _neon[Situacion.values.indexOf(s) % 5]),
                title: Text(s.nombre, style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text(s.detalle, style: estiloSecundario),
                trailing: cargando == s
                    ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
                    : const Icon(Icons.play_arrow_rounded),
                onTap: () => _pulsar(context, s),
              ),
              ),
            ),
        ]),
      ),
    ]);
  }
}
