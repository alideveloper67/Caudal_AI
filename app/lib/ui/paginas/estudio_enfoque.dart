import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../nucleo/estudio.dart';
import '../../nucleo/pantalla.dart';
import 'estudio_comunes.dart';

/// La vista «Cero distracciones»: solo el temporizador, la música, el volumen,
/// el mezclador y las notas, en un modo oscuro cálido de bajo brillo.
class EstudioEnfoque extends StatefulWidget {
  const EstudioEnfoque({super.key, required this.estudio});
  final Estudio estudio;

  @override
  State<EstudioEnfoque> createState() => _EstudioEnfoqueState();
}

class _EstudioEnfoqueState extends State<EstudioEnfoque> {
  Estudio get _e => widget.estudio;
  bool _saliendo = false;
  bool? _pantalla;

  PaletaEstudio get _paleta => _e.calido ? PaletaEstudio.calida(_e.brillo) : PaletaEstudio.normal();

  @override
  void initState() {
    super.initState();
    _e.addListener(_alCambiar);
    _alCambiar();
  }

  /// La pantalla se mantiene encendida mientras el interruptor lo pida.
  void _alCambiar() {
    if (_pantalla == _e.pantallaEncendida) return;
    _pantalla = _e.pantallaEncendida;
    PantallaEncendida.mantener(_pantalla!);
  }

  @override
  void dispose() {
    _e.removeListener(_alCambiar);
    PantallaEncendida.mantener(false);
    super.dispose();
  }

  Future<void> _salir() async {
    if (_saliendo) return;
    if (_e.hayBloqueEnCurso) {
      final ok = await confirmarSalidaEstudio(context, _e, _paleta);
      if (!ok || !mounted) return;
    }
    _salirYa();
  }

  void _salirYa() {
    if (_saliendo) return;
    _saliendo = true;
    final fin = _e.terminar();
    if (mounted) Navigator.of(context).pop();
    fin.catchError((_) {});
  }

  Future<void> _ajustes() => showModalBottomSheet<void>(
        context: context,
        useRootNavigator: true,
        isScrollControlled: true,
        showDragHandle: true,
        backgroundColor: _paleta.fondo,
        constraints: const BoxConstraints(maxWidth: 640),
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
        builder: (ctx) => ListenableBuilder(
          listenable: _e,
          builder: (ctx, _) {
            final p = _paleta;
            return ConstrainedBox(
              constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * 0.86),
              child: SingleChildScrollView(
                padding: EdgeInsets.fromLTRB(20, 0, 20, 20 + MediaQuery.paddingOf(ctx).bottom),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Text('Ajustes de la vista',
                      style: TextStyle(color: p.texto, fontSize: 20, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 12),
                  FilaInterruptor(
                    paleta: p,
                    titulo: 'Modo oscuro cálido',
                    ayuda: 'Tinte ámbar y colores suaves para cansar menos la vista.',
                    valor: _e.calido,
                    alCambiar: _e.ponerCalido,
                    icono: Icons.wb_twilight_rounded,
                  ),
                  AnimatedSize(
                    duration: const Duration(milliseconds: 220),
                    alignment: Alignment.topCenter,
                    child: _e.calido
                        ? Padding(
                            padding: const EdgeInsets.fromLTRB(32, 0, 0, 6),
                            child: Row(children: [
                              Text('Brillo cálido', style: TextStyle(color: p.texto2, fontSize: 13.5)),
                              Expanded(
                                child: SliderTheme(
                                  data: temaDeslizador(ctx, p),
                                  child: Slider(
                                    value: _e.brillo,
                                    onChanged: _e.ponerBrillo,
                                    label: 'Brillo cálido',
                                  ),
                                ),
                              ),
                            ]),
                          )
                        : const SizedBox(width: double.infinity),
                  ),
                  FilaInterruptor(
                    paleta: p,
                    titulo: 'Mantener la pantalla encendida',
                    ayuda: 'Para que no se apague mientras estudias.',
                    valor: _e.pantallaEncendida,
                    alCambiar: _e.ponerPantallaEncendida,
                    icono: Icons.brightness_medium_rounded,
                  ),
                  FilaInterruptor(
                    paleta: p,
                    titulo: 'Candado contra salidas por error',
                    ayuda: 'Salir exige mantener pulsado 2 segundos.',
                    valor: _e.candado,
                    alCambiar: _e.ponerCandado,
                    icono: Icons.lock_outline_rounded,
                  ),
                  Divider(color: p.borde, height: 28),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: () {
                        Navigator.of(ctx).pop();
                        _salir();
                      },
                      icon: const Icon(Icons.logout_rounded, size: 18),
                      label: const Text('Terminar la sesión'),
                      style: TextButton.styleFrom(foregroundColor: p.texto2, minimumSize: const Size(0, 44)),
                    ),
                  ),
                ]),
              ),
            );
          },
        ),
      );

  @override
  Widget build(BuildContext context) {
    final musica = _e.musica;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _salir();
      },
      child: ListenableBuilder(
        listenable: Listenable.merge([_e, ?musica?.cambios]),
        builder: (context, _) {
          final p = _paleta;
          return Scaffold(
            backgroundColor: p.fondo,
            body: AnimatedContainer(
              duration: const Duration(milliseconds: 250),
              color: p.fondo,
              child: SafeArea(
                child: Column(children: [
                  _BarraSuperior(estudio: _e, paleta: p, alSalir: _salir, alSalirYa: _salirYa, alAjustes: _ajustes),
                  _Aviso(estudio: _e, paleta: p),
                  Expanded(child: _Cuerpo(estudio: _e, paleta: p, alSalirYa: _salirYa)),
                ]),
              ),
            ),
          );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------- barra de arriba y aviso

class _BarraSuperior extends StatelessWidget {
  const _BarraSuperior(
      {required this.estudio, required this.paleta, required this.alSalir, required this.alSalirYa, required this.alAjustes});
  final Estudio estudio;
  final PaletaEstudio paleta;
  final VoidCallback alSalir;
  final VoidCallback alSalirYa;
  final VoidCallback alAjustes;

  @override
  Widget build(BuildContext context) {
    final p = paleta;
    final bloqueado = estudio.candado && estudio.hayBloqueEnCurso;
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
      child: Row(children: [
        SizedBox(
          width: 48,
          height: 48,
          child: bloqueado
              ? MantenerPulsado(
                  etiquetaSemantica: 'Mantén pulsado para salir de la sesión',
                  alConfirmar: alSalirYa,
                  // sin Tooltip: su pulsación larga le quitaría el gesto al candado
                  constructor: (_, avance) => Stack(alignment: Alignment.center, children: [
                      SizedBox(
                        width: 38,
                        height: 38,
                        child: CircularProgressIndicator(
                            value: avance, strokeWidth: 2.5, color: p.acento, backgroundColor: p.borde),
                      ),
                      Icon(Icons.lock_outline_rounded, color: p.texto2, size: 20),
                    ]),
                )
              : IconButton(
                  tooltip: 'Salir',
                  onPressed: alSalir,
                  icon: const Icon(Icons.close_rounded),
                  color: p.texto2,
                ),
        ),
        Expanded(
          child: Center(
            child: Text(estudio.perfil.nombre,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: p.texto3, fontSize: 13.5, fontWeight: FontWeight.w600, letterSpacing: 0.3)),
          ),
        ),
        SizedBox(
          width: 48,
          height: 48,
          child: IconButton(
            tooltip: 'Ajustes de la vista',
            onPressed: alAjustes,
            icon: const Icon(Icons.tune_rounded),
            color: p.texto2,
          ),
        ),
      ]),
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.estudio, required this.paleta});
  final Estudio estudio;
  final PaletaEstudio paleta;

  @override
  Widget build(BuildContext context) {
    final p = paleta;
    final texto = estudio.aviso;
    return AnimatedSize(
      duration: const Duration(milliseconds: 320),
      curve: Curves.easeOutCubic,
      alignment: Alignment.topCenter,
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 450),
        transitionBuilder: (c, a) => FadeTransition(opacity: a, child: c),
        child: texto == null
            ? const SizedBox(width: double.infinity, key: ValueKey('sin_aviso'))
            : Padding(
                key: ValueKey(texto),
                padding: const EdgeInsets.fromLTRB(20, 4, 20, 0),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 520),
                    child: Material(
                      color: p.acento.withValues(alpha: 0.13),
                      borderRadius: BorderRadius.circular(18),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(18),
                        onTap: estudio.cerrarAviso,
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          child: Row(mainAxisSize: MainAxisSize.min, children: [
                            Icon(Icons.spa_rounded, color: p.acento, size: 20),
                            const SizedBox(width: 12),
                            Flexible(
                              child: Text(texto, style: TextStyle(color: p.texto, fontSize: 14, height: 1.35)),
                            ),
                          ]),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
      ),
    );
  }
}

// ---------------------------------------------------------------- cuerpo

class _Cuerpo extends StatelessWidget {
  const _Cuerpo({required this.estudio, required this.paleta, required this.alSalirYa});
  final Estudio estudio;
  final PaletaEstudio paleta;
  final VoidCallback alSalirYa;

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, c) {
        final horizontal = c.maxWidth >= 560 && c.maxWidth > c.maxHeight * 1.15;
        final reloj = _Reloj(estudio: estudio, paleta: paleta, alSalirYa: alSalirYa);
        final controles = _Controles(estudio: estudio, paleta: paleta);
        if (horizontal) {
          return Row(children: [
            Expanded(flex: 5, child: reloj),
            Expanded(
              flex: 4,
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.only(right: 24, left: 8),
                  child: controles,
                ),
              ),
            ),
          ]);
        }
        return Column(children: [
          Expanded(child: reloj),
          Padding(
            padding: EdgeInsets.fromLTRB(20, 4, 20, 16 + math.min(MediaQuery.paddingOf(context).bottom, 8)),
            child: controles,
          ),
        ]);
      });
}

String _dosDigitos(int n) => n.toString().padLeft(2, '0');

String _tiempo(Duration d) {
  // redondea hacia arriba: «00:00» solo cuando ya terminó
  final s = (d.inMilliseconds / 1000).ceil();
  final h = s ~/ 3600, m = (s % 3600) ~/ 60, seg = s % 60;
  return h > 0 ? '$h:${_dosDigitos(m)}:${_dosDigitos(seg)}' : '${_dosDigitos(m)}:${_dosDigitos(seg)}';
}

String _tiempoHablado(Duration d) {
  final s = (d.inMilliseconds / 1000).ceil();
  final m = s ~/ 60, seg = s % 60;
  return '${m > 0 ? '$m ${m == 1 ? 'minuto' : 'minutos'} ' : ''}$seg ${seg == 1 ? 'segundo' : 'segundos'}';
}

class _Reloj extends StatelessWidget {
  const _Reloj({required this.estudio, required this.paleta, required this.alSalirYa});
  final Estudio estudio;
  final PaletaEstudio paleta;
  final VoidCallback alSalirYa;

  String _etiqueta(FaseEstudio f, bool pausado) {
    if (pausado) return 'EN PAUSA';
    return switch (f) {
      FaseEstudio.enfoque => 'ENFOQUE',
      FaseEstudio.descanso => 'DESCANSO',
      FaseEstudio.descansoLargo => 'DESCANSO LARGO',
      FaseEstudio.fin => 'SESIÓN COMPLETA',
      _ => '',
    };
  }

  @override
  Widget build(BuildContext context) {
    final p = paleta;
    final t = estudio.temporizador;
    final fin = t.fase == FaseEstudio.fin;
    final descanso = t.fase == FaseEstudio.descanso || t.fase == FaseEstudio.descansoLargo;
    final colorAnillo = descanso ? p.texto2 : p.acento;
    return LayoutBuilder(builder: (context, c) {
      final diam = math.max(120.0, math.min(c.maxWidth * 0.86, c.maxHeight - 84)).clamp(120.0, 460.0);
      return Center(
        child: FittedBox(
          fit: BoxFit.scaleDown,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            SizedBox(
              width: diam,
              height: diam,
              child: Stack(alignment: Alignment.center, children: [
                TweenAnimationBuilder<double>(
                  tween: Tween<double>(end: fin ? 1.0 : t.progreso),
                  duration: const Duration(milliseconds: 900),
                  curve: Curves.easeOutCubic,
                  builder: (_, v, _) => CustomPaint(
                    size: Size.square(diam),
                    painter: _AnilloPainter(
                      progreso: v,
                      pista: p.borde,
                      color: colorAnillo,
                      grosor: math.max(3.0, diam * 0.016),
                    ),
                  ),
                ),
                Padding(
                  padding: EdgeInsets.all(diam * 0.14),
                  // si el espacio se achica un momento (aparece un aviso), el reloj se encoge sin desbordar
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 400),
                    child: fin
                        ? Column(
                            key: const ValueKey('fin'),
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.check_rounded, size: diam * 0.2, color: p.acento),
                              SizedBox(height: diam * 0.03),
                              Text('Sesión completa',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(color: p.texto, fontSize: diam * 0.075, fontWeight: FontWeight.w700)),
                              SizedBox(height: diam * 0.015),
                              Text(
                                  'Hoy llevas ${EstadisticasEstudio.texto(estudio.estadisticas.hoy(estudio.ahora))}',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(color: p.texto2, fontSize: diam * 0.05)),
                            ],
                          )
                        : Semantics(
                            key: ValueKey(t.fase),
                            label: '${_etiqueta(t.fase, t.pausado)}. Quedan ${_tiempoHablado(t.restante)}',
                            excludeSemantics: true,
                            child: Column(mainAxisSize: MainAxisSize.min, children: [
                              Text(_etiqueta(t.fase, t.pausado),
                                  style: TextStyle(
                                      color: p.texto3,
                                      fontSize: math.max(11.0, diam * 0.045),
                                      fontWeight: FontWeight.w700,
                                      letterSpacing: 2)),
                              SizedBox(height: diam * 0.02),
                              Opacity(
                                opacity: t.pausado ? 0.55 : 1,
                                child: FittedBox(
                                  fit: BoxFit.scaleDown,
                                  child: Text(_tiempo(t.restante),
                                      style: TextStyle(
                                        color: p.texto,
                                        fontSize: diam * 0.25,
                                        fontWeight: FontWeight.w200,
                                        letterSpacing: -1,
                                        height: 1.05,
                                        fontFeatures: const [FontFeature.tabularFigures()],
                                      )),
                                ),
                              ),
                              SizedBox(height: diam * 0.02),
                              Text('Ronda ${t.ronda} de ${t.ciclo?.rondas ?? 1}',
                                  style: TextStyle(color: p.texto2, fontSize: math.max(12.0, diam * 0.052))),
                            ]),
                          ),
                  ),
                  ),
                ),
              ]),
            ),
            const SizedBox(height: 14),
            SizedBox(
              height: 48,
              child: fin
                  ? FilledButton.tonal(
                      onPressed: alSalirYa,
                      style: FilledButton.styleFrom(
                          backgroundColor: p.superficie2,
                          foregroundColor: p.texto,
                          padding: const EdgeInsets.symmetric(horizontal: 26),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
                      child: const Text('Cerrar'),
                    )
                  : Row(mainAxisSize: MainAxisSize.min, children: [
                      TextButton.icon(
                        onPressed: estudio.alternarTemporizador,
                        icon: Icon(t.pausado ? Icons.play_arrow_rounded : Icons.pause_rounded, size: 20),
                        label: Text(t.pausado ? 'Reanudar' : 'Pausar'),
                        style: TextButton.styleFrom(foregroundColor: p.texto2, minimumSize: const Size(0, 44)),
                      ),
                      const SizedBox(width: 8),
                      TextButton.icon(
                        onPressed: estudio.saltarBloque,
                        icon: const Icon(Icons.skip_next_rounded, size: 20),
                        label: Text(descanso ? 'Saltar descanso' : 'Saltar bloque'),
                        style: TextButton.styleFrom(foregroundColor: p.texto3, minimumSize: const Size(0, 44)),
                      ),
                    ]),
            ),
          ]),
        ),
      );
    });
  }
}

class _AnilloPainter extends CustomPainter {
  _AnilloPainter({required this.progreso, required this.pista, required this.color, required this.grosor});
  final double progreso;
  final Color pista;
  final Color color;
  final double grosor;

  @override
  void paint(Canvas canvas, Size size) {
    final r = (size.shortestSide - grosor) / 2;
    final centro = size.center(Offset.zero);
    final base = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = grosor
      ..color = pista;
    canvas.drawCircle(centro, r, base);
    if (progreso <= 0) return;
    final arco = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = grosor
      ..strokeCap = StrokeCap.round
      ..color = color;
    canvas.drawArc(Rect.fromCircle(center: centro, radius: r), -math.pi / 2, 2 * math.pi * progreso.clamp(0.0, 1.0),
        false, arco);
  }

  @override
  bool shouldRepaint(_AnilloPainter o) =>
      o.progreso != progreso || o.color != color || o.pista != pista || o.grosor != grosor;
}

// ---------------------------------------------------------------- controles

class _Controles extends StatelessWidget {
  const _Controles({required this.estudio, required this.paleta});
  final Estudio estudio;
  final PaletaEstudio paleta;

  @override
  Widget build(BuildContext context) {
    final p = paleta;
    final m = estudio.musica;
    String linea;
    if (estudio.cargandoCola) {
      linea = 'Preparando tu música…';
    } else if (estudio.errorCola != null) {
      linea = estudio.errorCola!;
    } else if (m == null) {
      linea = 'Los sonidos y el temporizador te acompañan.';
    } else if (!m.hayMusica) {
      linea = 'Sin música por ahora';
    } else {
      linea = m.titulo;
    }
    Widget redondo(IconData i, String tip, VoidCallback? f) => IconButton(
          tooltip: tip,
          onPressed: f,
          icon: Icon(i, size: 24),
          color: p.texto2,
          style: IconButton.styleFrom(minimumSize: const Size(52, 52)),
        );
    final sonando = m?.sonando ?? false;
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 420),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          child: Row(
            key: ValueKey(linea),
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (m != null && m.hayMusica && estudio.errorCola == null && !estudio.cargandoCola) ...[
                Icon(Icons.music_note_rounded, size: 15, color: p.texto3),
                const SizedBox(width: 6),
              ],
              Flexible(
                child: Text(linea,
                    maxLines: 2,
                    textAlign: TextAlign.center,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: p.texto3, fontSize: 13.5, height: 1.3)),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          redondo(Icons.equalizer_rounded, 'Mezclador de sonidos', () => mostrarMezclador(context, estudio, p)),
          Semantics(
            button: true,
            label: sonando ? 'Pausar la música' : 'Reproducir la música',
            child: GestureDetector(
              onTap: m == null ? null : () => m.alternar(),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                width: 68,
                height: 68,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: p.acento.withValues(alpha: m == null ? 0.35 : 1),
                ),
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 200),
                  child: Icon(sonando ? Icons.pause_rounded : Icons.play_arrow_rounded,
                      key: ValueKey(sonando), size: 34, color: p.sobreAcento),
                ),
              ),
            ),
          ),
          redondo(Icons.skip_next_rounded, 'Siguiente canción', m == null || !m.hayMusica ? null : () => m.siguiente()),
          redondo(Icons.lightbulb_outline_rounded, 'Captura de ideas', () => HojaNotas.mostrar(context, estudio, p)),
        ]),
        const SizedBox(height: 6),
        Row(children: [
          Icon(Icons.volume_mute_rounded, size: 19, color: p.texto3),
          Expanded(
            child: SliderTheme(
              data: temaDeslizador(context, p),
              child: Slider(
                value: ((m?.volumen ?? 100) / 100).clamp(0.0, 1.0),
                onChanged: m == null ? null : (v) => estudio.ponerVolumenBase(v * 100),
                label: 'Volumen',
                semanticFormatterCallback: (v) => 'Volumen ${(v * 100).round()} %',
              ),
            ),
          ),
          Icon(Icons.volume_up_rounded, size: 19, color: p.texto3),
        ]),
      ]),
    );
  }
}
