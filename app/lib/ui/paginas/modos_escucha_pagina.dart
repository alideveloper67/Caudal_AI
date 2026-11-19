import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/estudio.dart';
import '../../nucleo/modos_escucha.dart';
import '../../reproduccion/reproductor.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';
import 'estudio_pagina.dart';

/// «Modos de escucha»: Concentración, Dormir y Ejercicio. Cada uno arma una cola de música
/// pensada para lo que estás haciendo. Para todos. Dormir usa el temporizador del reproductor
/// (con su bajada suave de volumen al final) y Ejercicio ordena tu música por tempo cuando ya
/// la analizaste en el Mezclador; si no, busca música de entrenamiento.
class ModosEscuchaPagina extends StatefulWidget {
  const ModosEscuchaPagina({super.key});

  static Future<void> abrir(BuildContext context) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const ModosEscuchaPagina()));

  @override
  State<ModosEscuchaPagina> createState() => _ModosEscuchaPaginaState();
}

class _ModosEscuchaPaginaState extends State<ModosEscuchaPagina> {
  ModoEscucha? _trabajando;
  int _minutos = 30;
  IntensidadEjercicio _intensidad = IntensidadEjercicio.medio;
  PerfilEstudio _perfil = PerfilEstudio.leer;

  static const _colores = {
    ModoEscucha.concentracion: Color(0xFFE8A33D),
    ModoEscucha.dormir: Color(0xFF7C8CFF),
    ModoEscucha.ejercicio: Color(0xFFFF6B4A),
  };

  Future<void> _empezar(ModoEscucha modo, {bool soloTemporizador = false}) async {
    if (_trabajando != null) return;
    final s = Caudal.leer(context);
    final r = s.reproductor;
    setState(() => _trabajando = modo);
    try {
      if (modo == ModoEscucha.dormir && soloTemporizador) {
        await _temporizador(s, r);
        return;
      }
      List<Map<String, dynamic>> pistas;
      var porTempo = false;
      switch (modo) {
        case ModoEscucha.concentracion:
          pistas = await ModosEscucha.concentracion(perfil: _perfil);
        case ModoEscucha.dormir:
          pistas = await ModosEscucha.dormir();
        case ModoEscucha.ejercicio:
          final e = await ModosEscucha.ejercicio(_intensidad, coleccion: s.coleccion);
          pistas = e.pistas;
          porTempo = e.porTempo;
      }
      if (!mounted) return;
      if (pistas.isEmpty) {
        s.avisar('No encontré música para este modo. Revisa tu conexión e inténtalo otra vez.');
        return;
      }
      final titulo = switch (modo) {
        ModoEscucha.concentracion => 'Concentración',
        ModoEscucha.dormir => 'Dormir',
        ModoEscucha.ejercicio => 'Ejercicio ${_intensidad.nombre.toLowerCase()}',
      };
      await s.reproducirLista(context, pistas,
          // por tempo el orden importa (de menos a más): ahí no se baraja
          aleatorio: porTempo ? false : null, contexto: {'tipo': 'seleccion', 'id': 'modo_${modo.name}', 'titulo': titulo});
      if (modo == ModoEscucha.dormir) await _temporizador(s, r);
      if (modo == ModoEscucha.ejercicio) {
        s.avisar(porTempo ? 'Tu música, de menos a más tempo' : 'Música de entrenamiento, lista para empezar');
      }
    } catch (_) {
      if (mounted) s.avisar('No se pudo empezar. Inténtalo otra vez.');
    } finally {
      if (mounted) setState(() => _trabajando = null);
    }
  }

  /// Pone el temporizador con la bajada suave del volumen al final (si estaba apagada, la enciende).
  Future<void> _temporizador(Servicios s, Reproductor r) async {
    if (!s.ajustes.sino('apagado_suave')) await s.ajustes.poner('apagado_suave', true);
    r.programarApagado(minutos: _minutos);
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Modos de escucha')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, 32),
        children: [
          const Padding(
            padding: EdgeInsets.only(bottom: Esp.l),
            child: Text('Elige qué vas a hacer y Caudal arma la música.', style: estiloSecundario),
          ),
          _Modo(
            icono: Icons.center_focus_strong_rounded,
            color: _colores[ModoEscucha.concentracion]!,
            titulo: 'Concentración',
            texto: 'Instrumental y sin voz que distraiga, para trabajar o estudiar.',
            cargando: _trabajando == ModoEscucha.concentracion,
            bloqueado: _trabajando != null,
            etiquetaBoton: 'Empezar a concentrarme',
            alEmpezar: () => _empezar(ModoEscucha.concentracion),
            opciones: Wrap(spacing: 8, runSpacing: 8, children: [
              for (final p in PerfilEstudio.todos)
                ChoiceChip(
                  label: Text(p.nombre),
                  selected: _perfil.id == p.id,
                  onSelected: (_) => setState(() {
                    Haptico.seleccion();
                    _perfil = p;
                  }),
                ),
            ]),
            pie: TextButton.icon(
              onPressed: () => s.abrirEnPestana != null ? s.abrirEnPestana!(const EstudioPagina()) : EstudioPagina.abrir(context),
              icon: const Icon(Icons.timer_outlined, size: 18),
              label: const Text('Con sonidos y temporizador: Modo estudio'),
              style: TextButton.styleFrom(foregroundColor: C.texto2, alignment: Alignment.centerLeft),
            ),
          ),
          _Modo(
            icono: Icons.bedtime_rounded,
            color: _colores[ModoEscucha.dormir]!,
            titulo: 'Dormir',
            texto: 'Música tranquila que se apaga sola: el volumen baja poco a poco al final.',
            cargando: _trabajando == ModoEscucha.dormir,
            bloqueado: _trabajando != null,
            etiquetaBoton: 'Dormir con música',
            alEmpezar: () => _empezar(ModoEscucha.dormir),
            opciones: Wrap(spacing: 8, runSpacing: 8, children: [
              for (final m in ModosEscucha.minutosDormir)
                ChoiceChip(
                  label: Text(ModosEscucha.textoMinutos(m)),
                  selected: _minutos == m,
                  onSelected: (_) => setState(() {
                    Haptico.seleccion();
                    _minutos = m;
                  }),
                ),
            ]),
            pie: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              ListenableBuilder(
                listenable: s.reproductor,
                builder: (context, _) => s.reproductor.restanteApagado == null
                    ? (s.reproductor.actual == null
                        ? const SizedBox.shrink()
                        : TextButton.icon(
                            onPressed: _trabajando != null ? null : () => _empezar(ModoEscucha.dormir, soloTemporizador: true),
                            icon: const Icon(Icons.timer_outlined, size: 18),
                            label: const Text('Solo poner el temporizador a lo que suena'),
                            style: TextButton.styleFrom(foregroundColor: C.texto2, alignment: Alignment.centerLeft),
                          ))
                    : _TemporizadorActivo(r: s.reproductor),
              ),
            ]),
          ),
          _Modo(
            icono: Icons.directions_run_rounded,
            color: _colores[ModoEscucha.ejercicio]!,
            titulo: 'Ejercicio',
            texto: 'Música con el ritmo justo. Si ya analizaste tus canciones, se eligen por tempo.',
            cargando: _trabajando == ModoEscucha.ejercicio,
            bloqueado: _trabajando != null,
            etiquetaBoton: 'Empezar a entrenar',
            alEmpezar: () => _empezar(ModoEscucha.ejercicio),
            opciones: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final i in IntensidadEjercicio.values)
                  ChoiceChip(
                    label: Text(i.nombre),
                    selected: _intensidad == i,
                    onSelected: (_) => setState(() {
                      Haptico.seleccion();
                      _intensidad = i;
                    }),
                  ),
              ]),
              const SizedBox(height: 6),
              Text('${_intensidad.detalle} · ${_intensidad.bpmMin} a ${_intensidad.bpmMax} pulsos por minuto',
                  style: estiloSecundario),
            ]),
          ),
        ],
      ),
    );
  }
}

/// Lo que falta del temporizador (se actualiza cada segundo solo mientras está a la vista) y cómo quitarlo.
class _TemporizadorActivo extends StatefulWidget {
  const _TemporizadorActivo({required this.r});
  final Reproductor r;

  @override
  State<_TemporizadorActivo> createState() => _TemporizadorActivoState();
}

class _TemporizadorActivoState extends State<_TemporizadorActivo> {
  Timer? _reloj;

  @override
  void initState() {
    super.initState();
    _reloj = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _reloj?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final f = widget.r.restanteApagado;
    final texto = f == null
        ? 'Temporizador apagado'
        : f < 0
            ? 'Se apaga al terminar la canción'
            : 'Se apaga en ${ModosEscucha.reloj(f)}';
    return Row(children: [
      Icon(Icons.timer_rounded, size: 18, color: C.acento),
      const SizedBox(width: 8),
      Expanded(child: Text(texto, style: const TextStyle(fontWeight: FontWeight.w700))),
      TextButton(onPressed: () => widget.r.programarApagado(), child: const Text('Quitar')),
    ]);
  }
}

class _Modo extends StatelessWidget {
  const _Modo({
    required this.icono,
    required this.color,
    required this.titulo,
    required this.texto,
    required this.opciones,
    required this.etiquetaBoton,
    required this.alEmpezar,
    required this.cargando,
    required this.bloqueado,
    this.pie,
  });

  final IconData icono;
  final Color color;
  final String titulo;
  final String texto;
  final Widget opciones;
  final String etiquetaBoton;
  final VoidCallback alEmpezar;
  final bool cargando;
  final bool bloqueado;
  final Widget? pie;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: Esp.l),
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [color.withValues(alpha: 0.20), C.superficie],
            ),
            border: Border.all(color: color.withValues(alpha: 0.32)),
          ),
          child: Padding(
            padding: const EdgeInsets.all(Esp.l),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(color: color.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(15)),
                  child: Icon(icono, color: color, size: 26),
                ),
                const SizedBox(width: Esp.m),
                Expanded(
                    child: Text(titulo,
                        style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900), maxLines: 1, overflow: TextOverflow.ellipsis)),
              ]),
              const SizedBox(height: Esp.m),
              Text(texto, style: estiloSecundario),
              const SizedBox(height: Esp.m),
              opciones,
              const SizedBox(height: Esp.m),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: bloqueado ? null : alEmpezar,
                  style: FilledButton.styleFrom(
                    backgroundColor: color,
                    foregroundColor: const Color(0xFF111111),
                    minimumSize: const Size.fromHeight(48),
                    shape: const StadiumBorder(),
                  ),
                  child: cargando
                      ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 3, color: Color(0xFF111111)))
                      : FittedBox(fit: BoxFit.scaleDown, child: Text(etiquetaBoton, style: const TextStyle(fontWeight: FontWeight.w800))),
                ),
              ),
              if (pie != null) ...[const SizedBox(height: 4), pie!],
            ]),
          ),
        ),
      );
}
