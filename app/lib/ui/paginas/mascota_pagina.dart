import 'package:flutter/material.dart';

import '../../nucleo/fondo_app.dart';
import '../../nucleo/mascota_app.dart';
import '../tema.dart';

const _oro = Color(0xFFFFC857);

/// «Mascotita del reproductor»: se elige el personaje que camina sobre la barra
/// de la canción. Exclusivo para donadores y fundadores de Caudal.
class MascotaPagina extends StatefulWidget {
  const MascotaPagina({super.key});

  @override
  State<MascotaPagina> createState() => _MascotaPaginaState();
}

class _MascotaPaginaState extends State<MascotaPagina> {
  @override
  void initState() {
    super.initState();
    MascotaApp.i.cargarCatalogo();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([MascotaApp.i, FondoApp.i]),
      builder: (context, _) {
        final m = MascotaApp.i;
        final puede = m.puede;
        final suyas = m.tieneExclusivas;
        return Scaffold(
          appBar: AppBar(title: const Text('Mascotita del reproductor')),
          body: ListView(
            padding: const EdgeInsets.all(Esp.l),
            children: [
              _Aviso(puede: puede, titulo: FondoApp.i.titulo, suyas: suyas),
              const SizedBox(height: Esp.l),
              Opacity(
                opacity: puede || suyas ? 1 : 0.45,
                child: IgnorePointer(
                  ignoring: !puede && !suyas,
                  child: GridView.count(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisCount: MediaQuery.sizeOf(context).width > 600 ? 5 : 3,
                    mainAxisSpacing: Esp.s,
                    crossAxisSpacing: Esp.s,
                    childAspectRatio: 0.88,
                    children: [
                      _Casilla(
                        nombre: 'Ninguna',
                        elegida: m.clave.isEmpty,
                        icono: const Icon(Icons.block_rounded, size: 34, color: C.texto3),
                        alTocar: () => m.elegir(''),
                      ),
                      for (final x in m.disponibles)
                        Opacity(
                          opacity: m.puedeElegir(x) ? 1 : 0.4,
                          child: IgnorePointer(
                            ignoring: !m.puedeElegir(x),
                            child: _Casilla(
                              nombre: x.nombre,
                              elegida: m.clave == x.clave,
                              icono: _Miniatura(mascota: x),
                              alTocar: () => m.elegir(x.clave),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.puede, required this.titulo, this.suyas = false});
  final bool puede;
  final String titulo;

  /// La cuenta tiene una mascota solo suya (aunque no sea donadora).
  final bool suyas;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(Esp.l),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        gradient: LinearGradient(colors: [_oro.withValues(alpha: 0.24), C.violeta.withValues(alpha: 0.22)]),
        border: Border.all(color: C.borde),
      ),
      child: Row(children: [
        Icon(puede || suyas ? Icons.pets_rounded : Icons.lock_outline_rounded, color: puede || suyas ? _oro : C.texto2, size: 26),
        const SizedBox(width: Esp.m),
        Expanded(
          child: Text(
            puede
                ? '${titulo.isEmpty ? 'Tu mascotita' : titulo}: elige quién camina por la barra de la canción mientras suena la música.'
                : suyas
                    ? 'Tienes una mascotita solo tuya: elígela y caminará por la barra de la canción. Las demás son para donadores y fundadores de Caudal.'
                    : 'Exclusiva para donadores y fundadores de Caudal. Con tu apoyo, un amiguito camina por la barra de la canción.',
            style: TextStyle(fontSize: 14, height: 1.4, color: C.texto2),
          ),
        ),
      ]),
    );
  }
}

class _Casilla extends StatelessWidget {
  const _Casilla({required this.nombre, required this.elegida, required this.icono, required this.alTocar});
  final String nombre;
  final bool elegida;
  final Widget icono;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: elegida,
      label: nombre,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: alTocar,
        child: Container(
          padding: const EdgeInsets.all(Esp.s),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            color: elegida ? C.acento.withValues(alpha: 0.16) : C.superficie2.withValues(alpha: 0.6),
            border: Border.all(color: elegida ? C.acento : C.borde, width: elegida ? 2 : 1),
          ),
          child: Column(children: [
            Expanded(child: Center(child: icono)),
            const SizedBox(height: Esp.xs),
            Text(nombre,
                maxLines: 2,
                textAlign: TextAlign.center,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 12, fontWeight: elegida ? FontWeight.w900 : FontWeight.w700, color: C.texto)),
          ]),
        ),
      ),
    );
  }
}

/// El primer cuadro de la hoja (la hoja trae [Mascota.cuadros] lado a lado), en pixel art nítido.
class _Miniatura extends StatelessWidget {
  const _Miniatura({required this.mascota});
  final Mascota mascota;

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: FittedBox(
        fit: BoxFit.contain,
        child: SizedBox(
          width: mascota.ancho * 3.0,
          height: mascota.alto * 3.0,
          child: OverflowBox(
            alignment: Alignment.centerLeft,
            minWidth: 0,
            maxWidth: double.infinity,
            child: Image.asset(
              mascota.imagen,
              width: mascota.ancho * mascota.cuadros * 3.0,
              height: mascota.alto * 3.0,
              fit: BoxFit.fill,
              filterQuality: FilterQuality.none,
              excludeFromSemantics: true,
            ),
          ),
        ),
      ),
    );
  }
}
