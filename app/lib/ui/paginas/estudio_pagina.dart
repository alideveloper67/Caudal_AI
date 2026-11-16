import 'package:flutter/material.dart';

import '../../nucleo/estudio.dart';
import '../../reproduccion/estudio_control.dart';
import '../servicios.dart';
import '../tema.dart';
import 'estudio_comunes.dart';
import 'estudio_enfoque.dart';

/// «Modo estudio»: eliges tu tarea, tu ritmo y tus sonidos, y empiezas.
class EstudioPagina extends StatefulWidget {
  const EstudioPagina({super.key, this.estudio, this.musica});

  /// Solo para pruebas: el estado y el reproductor falsos.
  final Estudio? estudio;
  final ControlMusica? musica;

  /// Abre la pantalla encima de todo (la usa también el atajo caudal://estudio).
  static Future<void> abrir(BuildContext context) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => const EstudioPagina()));

  @override
  State<EstudioPagina> createState() => _EstudioPaginaState();
}

class _EstudioPaginaState extends State<EstudioPagina> {
  late final Estudio _e = widget.estudio ?? Estudio.i;
  final _paleta = PaletaEstudio.normal();
  bool _conectado = false;

  @override
  void initState() {
    super.initState();
    _e.cargar();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_conectado) return;
    _conectado = true;
    if (widget.musica != null) {
      _e.conectarMusica(widget.musica);
    } else {
      try {
        _e.conectarMusica(ControlReproductor(Caudal.leer(context).reproductor));
      } catch (_) {}
    }
  }

  Future<void> _empezar() async {
    final nav = Navigator.of(context, rootNavigator: true);
    if (!_e.sesionActiva) {
      // el inicio no espera a la música: la vista de enfoque cuenta desde ya
      _e.iniciar();
    }
    await nav.push(PageRouteBuilder<void>(
      opaque: true,
      transitionDuration: const Duration(milliseconds: 420),
      reverseTransitionDuration: const Duration(milliseconds: 300),
      pageBuilder: (_, _, _) => EstudioEnfoque(estudio: _e),
      transitionsBuilder: (_, a, _, hijo) => FadeTransition(
          opacity: CurvedAnimation(parent: a, curve: Curves.easeOut), child: hijo),
    ));
  }

  Future<void> _salir() async {
    if (_e.hayBloqueEnCurso) {
      final ok = await confirmarSalidaEstudio(context, _e, _paleta);
      if (!ok) return;
      await _e.terminar();
    }
    if (mounted) Navigator.of(context).maybePop();
  }

  @override
  Widget build(BuildContext context) {
    final p = _paleta;
    return ListenableBuilder(
      listenable: _e,
      builder: (context, _) => PopScope(
      canPop: !_e.hayBloqueEnCurso,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _salir();
      },
      child: Scaffold(
        backgroundColor: p.fondo,
        body: SafeArea(
          bottom: false,
          child: ListenableBuilder(
            listenable: _e,
            builder: (context, _) {
              if (!_e.cargado) {
                return Center(child: CircularProgressIndicator(color: p.acento, strokeWidth: 2.5));
              }
              return Column(children: [
                Expanded(
                  child: LayoutBuilder(builder: (context, c) {
                    final ancho = c.maxWidth;
                    final dos = ancho >= 960;
                    final lado = ancho >= 600 ? 28.0 : 16.0;
                    final izq = <Widget>[
                      if (_e.sesionActiva) _BannerSesion(estudio: _e, paleta: p, alVolver: _empezar),
                      _SeccionPerfiles(estudio: _e, paleta: p),
                      _SeccionEstilos(estudio: _e, paleta: p),
                      _SeccionRitmo(estudio: _e, paleta: p),
                    ];
                    final der = <Widget>[
                      PanelEstudio(paleta: p, child: MezcladorEstudio(estudio: _e, paleta: p)),
                      _SeccionFin(estudio: _e, paleta: p),
                      _SeccionConstancia(estudio: _e, paleta: p),
                    ];
                    Widget columna(List<Widget> l) => Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [for (final w in l) Padding(padding: const EdgeInsets.only(bottom: 16), child: w)],
                        );
                    return SingleChildScrollView(
                      padding: EdgeInsets.fromLTRB(lado, 0, lado, 24),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: BoxConstraints(maxWidth: dos ? 1100 : 640),
                          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                            _Cabecera(paleta: p, alVolver: _salir),
                            if (dos)
                              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Expanded(child: columna(izq)),
                                const SizedBox(width: 20),
                                Expanded(child: columna(der)),
                              ])
                            else
                              columna([...izq, ...der]),
                          ]),
                        ),
                      ),
                    );
                  }),
                ),
                _BarraInicio(estudio: _e, paleta: p, alEmpezar: _empezar),
              ]);
            },
          ),
        ),
      ),
      ),
    );
  }
}

class _Cabecera extends StatelessWidget {
  const _Cabecera({required this.paleta, required this.alVolver});
  final PaletaEstudio paleta;
  final VoidCallback alVolver;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 4, bottom: 18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            IconButton(
              tooltip: 'Volver',
              onPressed: alVolver,
              icon: const Icon(Icons.arrow_back_rounded),
              color: paleta.texto,
              style: IconButton.styleFrom(padding: const EdgeInsets.all(12)),
            ),
          ]),
          const SizedBox(height: 4),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Text('Modo estudio',
                style: TextStyle(color: paleta.texto, fontSize: 32, fontWeight: FontWeight.w800, letterSpacing: -0.8)),
          ),
          const SizedBox(height: 6),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Text('Un rincón tranquilo para concentrarte, sin distracciones.',
                style: TextStyle(color: paleta.texto2, fontSize: 15.5, height: 1.4)),
          ),
        ]),
      );
}

class _Titulo extends StatelessWidget {
  const _Titulo(this.paleta, this.texto, [this.sub]);
  final PaletaEstudio paleta;
  final String texto;
  final String? sub;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 0, 4, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(texto, style: TextStyle(color: paleta.texto, fontSize: 18, fontWeight: FontWeight.w800)),
          if (sub != null) ...[
            const SizedBox(height: 3),
            Text(sub!, style: TextStyle(color: paleta.texto3, fontSize: 13, height: 1.35)),
          ],
        ]),
      );
}

// ---------------------------------------------------------------- sesión en curso

class _BannerSesion extends StatelessWidget {
  const _BannerSesion({required this.estudio, required this.paleta, required this.alVolver});
  final Estudio estudio;
  final PaletaEstudio paleta;
  final VoidCallback alVolver;

  @override
  Widget build(BuildContext context) {
    final t = estudio.temporizador;
    final termino = t.fase == FaseEstudio.fin;
    return PanelEstudio(
      paleta: paleta,
      borde: paleta.acento.withValues(alpha: 0.5),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(termino ? Icons.check_circle_outline_rounded : Icons.self_improvement_rounded, color: paleta.acento),
          const SizedBox(width: 12),
          Expanded(
            child: Text(termino ? 'Terminaste tu sesión' : 'Tu sesión sigue en curso',
                style: TextStyle(color: paleta.texto, fontSize: 16, fontWeight: FontWeight.w800)),
          ),
        ]),
        const SizedBox(height: 12),
        Wrap(spacing: 10, runSpacing: 8, children: [
          FilledButton(
            onPressed: alVolver,
            style: FilledButton.styleFrom(
                backgroundColor: paleta.acento, foregroundColor: paleta.sobreAcento, minimumSize: const Size(0, 44)),
            child: Text(termino ? 'Ver el cierre' : 'Volver al enfoque'),
          ),
          TextButton(
            onPressed: () => estudio.terminar(),
            style: TextButton.styleFrom(foregroundColor: paleta.texto2, minimumSize: const Size(0, 44)),
            child: const Text('Terminar sesión'),
          ),
        ]),
      ]),
    );
  }
}

// ---------------------------------------------------------------- perfiles

class _SeccionPerfiles extends StatelessWidget {
  const _SeccionPerfiles({required this.estudio, required this.paleta});
  final Estudio estudio;
  final PaletaEstudio paleta;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        _Titulo(paleta, '¿Qué vas a hacer?', 'Cada tarea trae su música y sus sonidos.'),
        LayoutBuilder(builder: (context, c) {
          final dos = c.maxWidth >= 480;
          final ancho = dos ? (c.maxWidth - 12) / 2 : c.maxWidth;
          return Wrap(spacing: 12, runSpacing: 12, children: [
            for (final p in PerfilEstudio.todos)
              SizedBox(
                width: ancho,
                child: _TarjetaPerfil(
                  perfil: p,
                  paleta: paleta,
                  elegido: estudio.perfilId == p.id,
                  alPulsar: () => estudio.elegirPerfil(p.id),
                ),
              ),
          ]);
        }),
      ]);
}

class _TarjetaPerfil extends StatelessWidget {
  const _TarjetaPerfil({required this.perfil, required this.paleta, required this.elegido, required this.alPulsar});
  final PerfilEstudio perfil;
  final PaletaEstudio paleta;
  final bool elegido;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) {
    final p = paleta;
    return Semantics(
      button: true,
      selected: elegido,
      label: '${perfil.nombre}. ${perfil.descripcion}',
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 240),
        curve: Curves.easeOutCubic,
        decoration: BoxDecoration(
          color: elegido ? Color.lerp(p.superficie, p.acento, 0.08) : p.superficie,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: elegido ? p.acento.withValues(alpha: 0.8) : p.borde, width: elegido ? 1.6 : 1),
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(22),
          child: InkWell(
            borderRadius: BorderRadius.circular(22),
            onTap: alPulsar,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 240),
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    color: elegido ? p.acento.withValues(alpha: 0.2) : p.superficie2,
                    borderRadius: BorderRadius.circular(15),
                  ),
                  child: Icon(IconosEstudio.perfil(perfil.id), color: elegido ? p.acento : p.texto2, size: 24),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(
                        child: Text(perfil.nombre,
                            style: TextStyle(color: p.texto, fontSize: 16, fontWeight: FontWeight.w800)),
                      ),
                      AnimatedOpacity(
                        duration: const Duration(milliseconds: 200),
                        opacity: elegido ? 1 : 0,
                        child: Icon(Icons.check_circle_rounded, color: p.acento, size: 20),
                      ),
                    ]),
                    const SizedBox(height: 4),
                    Text(perfil.descripcion, style: TextStyle(color: p.texto2, fontSize: 13.5, height: 1.35)),
                    const SizedBox(height: 10),
                    Wrap(spacing: 6, runSpacing: 6, children: [
                      for (final e in perfil.etiquetas)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                              color: p.superficie2, borderRadius: BorderRadius.circular(999)),
                          child: Text(e, style: TextStyle(color: p.texto3, fontSize: 11.5, fontWeight: FontWeight.w600)),
                        ),
                    ]),
                  ]),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- estilos

class _SeccionEstilos extends StatelessWidget {
  const _SeccionEstilos({required this.estudio, required this.paleta});
  final Estudio estudio;
  final PaletaEstudio paleta;

  @override
  Widget build(BuildContext context) => PanelEstudio(
        paleta: paleta,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          _Titulo(paleta, 'Estilo de sonido', 'Sin letra, para que nada compita con tu cabeza.'),
          Wrap(spacing: 8, runSpacing: 8, children: [
            _ChipElegir(paleta: paleta, texto: 'Según tu tarea', elegido: estudio.estiloId == null,
                alPulsar: () => estudio.elegirEstilo(null)),
            for (final s in EstiloEstudio.todos)
              _ChipElegir(paleta: paleta, texto: s.nombre, elegido: estudio.estiloId == s.id,
                  alPulsar: () => estudio.elegirEstilo(s.id)),
          ]),
        ]),
      );
}

class _ChipElegir extends StatelessWidget {
  const _ChipElegir({required this.paleta, required this.texto, required this.elegido, required this.alPulsar});
  final PaletaEstudio paleta;
  final String texto;
  final bool elegido;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        selected: elegido,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          decoration: BoxDecoration(
            color: elegido ? paleta.acento.withValues(alpha: 0.18) : paleta.superficie2,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: elegido ? paleta.acento.withValues(alpha: 0.7) : Colors.transparent),
          ),
          child: InkWell(
            borderRadius: BorderRadius.circular(999),
            onTap: alPulsar,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Text(texto,
                  style: TextStyle(
                      color: elegido ? paleta.texto : paleta.texto2,
                      fontSize: 13.5,
                      fontWeight: elegido ? FontWeight.w700 : FontWeight.w600)),
            ),
          ),
        ),
      );
}

// ---------------------------------------------------------------- ritmo

class _SeccionRitmo extends StatelessWidget {
  const _SeccionRitmo({required this.estudio, required this.paleta});
  final Estudio estudio;
  final PaletaEstudio paleta;

  @override
  Widget build(BuildContext context) {
    final e = estudio, p = paleta;
    final custom = e.cicloId == 'custom';
    final c = e.ciclo;
    final total = EstadisticasEstudio.texto(c.totalEnfoque);
    return PanelEstudio(
      paleta: p,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        _Titulo(p, 'Tu ritmo', 'Bloques de enfoque con pausas para respirar.'),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final pre in CicloEstudio.presets)
            _ChipElegir(paleta: p, texto: pre.nombre, elegido: e.cicloId == pre.id, alPulsar: () => e.elegirCiclo(pre.id)),
          _ChipElegir(paleta: p, texto: 'A mi manera', elegido: custom, alPulsar: e.ponerCicloPersonalizado),
        ]),
        const SizedBox(height: 14),
        AnimatedSize(
          duration: const Duration(milliseconds: 240),
          curve: Curves.easeOutCubic,
          alignment: Alignment.topCenter,
          child: Column(children: [
            if (custom) ...[
              PasoNumerico(
                  paleta: p, titulo: 'Enfoque', valor: e.enfoqueMin, texto: '${e.enfoqueMin} min',
                  minimo: 5, maximo: 180, salto: 5, alCambiar: (v) => e.ajustarCiclo(enfoque: v)),
              PasoNumerico(
                  paleta: p, titulo: 'Descanso', valor: e.descansoMin, texto: '${e.descansoMin} min',
                  minimo: 1, maximo: 60, alCambiar: (v) => e.ajustarCiclo(descanso: v)),
            ],
            PasoNumerico(
                paleta: p, titulo: 'Rondas', valor: e.rondas, texto: '${e.rondas}',
                minimo: 1, maximo: 12, alCambiar: (v) => e.ajustarCiclo(rondasNuevas: v)),
            PasoNumerico(
                paleta: p, titulo: 'Descanso largo', valor: e.descansoLargoMin,
                texto: e.descansoLargoMin == 0 ? 'Sin él' : '${e.descansoLargoMin} min',
                minimo: 0, maximo: 45, salto: 5, alCambiar: (v) => e.ajustarCiclo(largo: v)),
          ]),
        ),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: p.superficie2, borderRadius: BorderRadius.circular(14)),
          child: Row(children: [
            Icon(Icons.schedule_rounded, size: 18, color: p.texto3),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                  '${e.rondas} ${e.rondas == 1 ? 'ronda' : 'rondas'} de ${e.enfoqueMin} min, '
                  'con descansos de ${e.descansoMin} min'
                  '${e.descansoLargoMin > 0 ? ' y uno largo de ${e.descansoLargoMin} min cada 4 rondas' : ''}. '
                  'En total, $total de enfoque.',
                  style: TextStyle(color: p.texto2, fontSize: 13, height: 1.4)),
            ),
          ]),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- al terminar un bloque

class _SeccionFin extends StatelessWidget {
  const _SeccionFin({required this.estudio, required this.paleta});
  final Estudio estudio;
  final PaletaEstudio paleta;

  @override
  Widget build(BuildContext context) {
    final e = estudio, p = paleta;
    return PanelEstudio(
      paleta: p,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        _Titulo(p, 'Al terminar un bloque', 'Suena una campana suave y la música hace esto en el descanso.'),
        SegmentedButton<AccionFinBloque>(
          showSelectedIcon: false,
          style: SegmentedButton.styleFrom(
            backgroundColor: p.superficie2,
            foregroundColor: p.texto2,
            selectedBackgroundColor: p.acento.withValues(alpha: 0.2),
            selectedForegroundColor: p.texto,
            side: BorderSide(color: p.borde),
            visualDensity: VisualDensity.standard,
            padding: const EdgeInsets.symmetric(horizontal: 6),
            textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
          ),
          segments: const [
            ButtonSegment(value: AccionFinBloque.bajar, label: Text('Bajar')),
            ButtonSegment(value: AccionFinBloque.pausar, label: Text('Pausar')),
            ButtonSegment(value: AccionFinBloque.seguir, label: Text('Seguir')),
          ],
          selected: {e.accion},
          onSelectionChanged: (s) => e.ponerAccion(s.first),
        ),
        const SizedBox(height: 14),
        FilaInterruptor(
          paleta: p,
          titulo: 'Candado contra salidas por error',
          ayuda: 'Para salir de la vista de enfoque hay que mantener pulsado 2 segundos.',
          valor: e.candado,
          alCambiar: e.ponerCandado,
          icono: Icons.lock_outline_rounded,
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- constancia

class _SeccionConstancia extends StatelessWidget {
  const _SeccionConstancia({required this.estudio, required this.paleta});
  final Estudio estudio;
  final PaletaEstudio paleta;

  @override
  Widget build(BuildContext context) {
    final e = estudio, p = paleta;
    final ahora = e.ahora;
    final s = e.estadisticas;
    final racha = s.racha(ahora);
    Widget dato(String etiqueta, String valor, IconData icono) => Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 14),
            decoration: BoxDecoration(color: p.superficie2, borderRadius: BorderRadius.circular(16)),
            child: Column(children: [
              Icon(icono, size: 18, color: p.acento),
              const SizedBox(height: 8),
              FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(valor, style: TextStyle(color: p.texto, fontSize: 18, fontWeight: FontWeight.w800)),
              ),
              const SizedBox(height: 2),
              Text(etiqueta,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  style: TextStyle(color: p.texto3, fontSize: 11.5, height: 1.2)),
            ]),
          ),
        );
    return PanelEstudio(
      paleta: p,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        _Titulo(p, 'Tu constancia'),
        IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          dato('Hoy', EstadisticasEstudio.texto(s.hoy(ahora)), Icons.today_rounded),
          const SizedBox(width: 8),
          dato('Esta semana', EstadisticasEstudio.texto(s.semana(ahora)), Icons.date_range_rounded),
          const SizedBox(width: 8),
          dato(racha == 1 ? 'Día de racha' : 'Días de racha', '$racha', Icons.local_fire_department_rounded),
        ])),
        const SizedBox(height: 12),
        Text(s.frase(ahora), style: TextStyle(color: p.texto2, fontSize: 13.5, height: 1.4)),
        const SizedBox(height: 6),
        Divider(color: p.borde, height: 20),
        InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => HojaNotas.mostrar(context, e, p),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(children: [
              Icon(Icons.lightbulb_outline_rounded, color: p.texto2, size: 22),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                    e.notas.lista.isEmpty
                        ? 'Captura de ideas'
                        : 'Captura de ideas · ${e.notas.lista.length} ${e.notas.lista.length == 1 ? 'nota' : 'notas'}',
                    style: TextStyle(color: p.texto, fontSize: 15, fontWeight: FontWeight.w600)),
              ),
              Icon(Icons.chevron_right_rounded, color: p.texto3),
            ]),
          ),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- botón inferior

class _BarraInicio extends StatelessWidget {
  const _BarraInicio({required this.estudio, required this.paleta, required this.alEmpezar});
  final Estudio estudio;
  final PaletaEstudio paleta;
  final VoidCallback alEmpezar;

  @override
  Widget build(BuildContext context) {
    final p = paleta;
    final activa = estudio.sesionActiva;
    return Container(
      decoration: BoxDecoration(
        color: p.fondo,
        border: Border(top: BorderSide(color: p.borde.withValues(alpha: 0.7))),
      ),
      padding: EdgeInsets.fromLTRB(16, 12, 16, 12 + MediaQuery.paddingOf(context).bottom),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: SizedBox(
            width: double.infinity,
            height: 54,
            child: FilledButton.icon(
              onPressed: alEmpezar,
              icon: Icon(activa ? Icons.self_improvement_rounded : Icons.play_arrow_rounded),
              label: Text(activa ? 'Volver al enfoque' : 'Empezar a estudiar'),
              style: FilledButton.styleFrom(
                backgroundColor: p.acento,
                foregroundColor: p.sobreAcento,
                textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- la entrada de Inicio

/// La tarjeta elegante de «Modo estudio» para la pantalla de Inicio.
class TarjetaEstudio extends StatelessWidget {
  const TarjetaEstudio({super.key});

  @override
  Widget build(BuildContext context) {
    final p = PaletaEstudio.calida(0.8);
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, 20),
      child: Semantics(
        button: true,
        label: 'Modo estudio. Música y sonidos para concentrarte.',
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(22),
          child: Ink(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [const Color(0xFF2A1F14), Color.lerp(const Color(0xFF2A1F14), C.fondo, 0.5)!],
              ),
              border: Border.all(color: p.acento.withValues(alpha: 0.28)),
            ),
            child: InkWell(
              borderRadius: BorderRadius.circular(22),
              onTap: () {
                final s = Caudal.leer(context);
                if (s.abrirEnPestana != null) {
                  s.abrirEnPestana!(const EstudioPagina());
                } else {
                  EstudioPagina.abrir(context);
                }
              },
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                        color: p.acento.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(16)),
                    child: Icon(Icons.self_improvement_rounded, color: p.acento, size: 26),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('Modo estudio',
                          style: TextStyle(color: p.texto, fontSize: 16.5, fontWeight: FontWeight.w800)),
                      const SizedBox(height: 3),
                      Text('Música sin letra, sonidos y un temporizador para concentrarte.',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(color: p.texto2, fontSize: 13, height: 1.3)),
                    ]),
                  ),
                  const SizedBox(width: 8),
                  Icon(Icons.arrow_forward_rounded, color: p.acento, size: 20),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
