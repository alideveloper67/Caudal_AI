// La hoja «Personalizar el reproductor»: el estilo de la pantalla, los colores de la carátula y
// los soniditos. Todo lo de aquí es de donadores salvo el Clásico y el Vinilo; lo que no
// se puede elegir se ve con su candadito y explica por qué.

import 'package:flutter/material.dart';

import '../../nucleo/estilo_reproductor.dart';
import '../../nucleo/fondo_app.dart';
import '../../nucleo/premium.dart';
import '../../nucleo/premium_letras.dart';
import '../../nucleo/sonidos_interfaz.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';

IconData iconoDeEstilo(EstiloReproductor e) => switch (e) {
      EstiloReproductor.clasico => Icons.image_rounded,
      EstiloReproductor.vinilo => Icons.album_rounded,
      EstiloReproductor.casete => Icons.radio_rounded,
      EstiloReproductor.neon => Icons.bolt_rounded,
      EstiloReproductor.flotante => Icons.pets_rounded,
    };

Future<void> mostrarPersonalizarReproductor(BuildContext context) => showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      showDragHandle: true,
      builder: (_) => const HojaPersonalizarReproductor(),
    );

class HojaPersonalizarReproductor extends StatelessWidget {
  const HojaPersonalizarReproductor({super.key});

  void _soloDonadores(BuildContext context) {
    Haptico.seleccion();
    Caudal.leer(context).avisar('Esto es para donadores de Caudal');
  }

  @override
  Widget build(BuildContext context) {
    final p = PreferenciasReproductor.i;
    return ListenableBuilder(
      listenable: Listenable.merge([p, Premium.i, FondoApp.i]),
      builder: (context, _) {
        final donador = esPremiumLetras();
        return SingleChildScrollView(
          padding: const EdgeInsets.only(bottom: 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 0, 20, 4),
              child: Text('Personalizar el reproductor', style: estiloTituloSeccion),
            ),
            const _Seccion('Estilo de la pantalla'),
            for (final e in EstiloReproductor.values)
              Builder(builder: (context) {
                final bloqueado = e.soloDonadores && !donador;
                final elegido = p.estilo == e && !bloqueado;
                return ListTile(
                  enabled: true,
                  selected: elegido,
                  selectedColor: C.acento,
                  leading: Icon(iconoDeEstilo(e), color: bloqueado ? C.texto.withValues(alpha: 0.4) : null),
                  title: Text(e.nombre, style: TextStyle(color: bloqueado ? C.texto.withValues(alpha: 0.55) : null)),
                  subtitle: Text(bloqueado ? 'Para donadores · ${e.descripcion}' : e.descripcion, style: estiloSecundario),
                  trailing: bloqueado
                      ? const Icon(Icons.lock_outline_rounded, size: 20)
                      : elegido
                          ? Icon(Icons.check_circle_rounded, color: C.acento)
                          : null,
                  onTap: () async {
                    if (bloqueado) return _soloDonadores(context);
                    Haptico.seleccion();
                    final ok = await p.elegirEstilo(e);
                    if (ok && context.mounted) Navigator.of(context).maybePop();
                  },
                );
              }),
            const _Seccion('Colores'),
            SwitchListTile(
              title: const Text('Colores de la carátula'),
              subtitle: Text(
                  donador ? 'El reproductor toma los colores de la carátula que suena' : 'Para donadores · el reproductor toma los colores de la carátula',
                  style: estiloSecundario),
              secondary: const Icon(Icons.palette_rounded),
              value: donador && p.coloresDePortada,
              onChanged: donador ? p.ponerColores : (_) => _soloDonadores(context),
            ),
            const _Seccion('Sonidos'),
            SwitchListTile(
              title: const Text('Al dar me gusta'),
              secondary: const Icon(Icons.favorite_rounded),
              subtitle: donador ? null : const Text('Para donadores', style: estiloSecundario),
              value: donador && p.sonidoMeGusta,
              onChanged: donador ? p.ponerSonidoMeGusta : (_) => _soloDonadores(context),
            ),
            SwitchListTile(
              title: const Text('Al abrir la app'),
              secondary: const Icon(Icons.waving_hand_rounded),
              subtitle: donador ? null : const Text('Para donadores', style: estiloSecundario),
              value: donador && p.sonidoAlAbrir,
              onChanged: donador ? p.ponerSonidoAlAbrir : (_) => _soloDonadores(context),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
              child: Wrap(spacing: 8, runSpacing: 6, children: [
                for (final s in SonidoUi.values)
                  ChoiceChip(
                    label: Text(s.nombre),
                    selected: p.sonido == s,
                    onSelected: donador
                        ? (_) async {
                            await p.elegirSonido(s);
                            await SonidosInterfaz.i.reproducir(s, vistaPrevia: true);
                          }
                        : (_) => _soloDonadores(context),
                  ),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 12, 0),
              child: Row(children: [
                const Icon(Icons.volume_down_rounded, size: 20),
                Expanded(
                  child: Slider(
                    value: p.volumenSonido,
                    min: 0.05,
                    max: 0.6,
                    onChanged: donador ? (v) => p.ponerVolumenSonido(v, guardar: false) : null,
                    onChangeEnd: donador
                        ? (v) async {
                            await p.ponerVolumenSonido(v);
                            await SonidosInterfaz.i.reproducir(p.sonido, vistaPrevia: true);
                          }
                        : null,
                  ),
                ),
                const Icon(Icons.volume_up_rounded, size: 20),
              ]),
            ),
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 0, 20, 4),
              child: Text('Los sonidos son cortitos y bajos a propósito: no tapan tu música.', style: estiloSecundario),
            ),
          ]),
        );
      },
    );
  }
}

class _Seccion extends StatelessWidget {
  const _Seccion(this.texto);
  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 2),
        child: Text(texto.toUpperCase(),
            style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, letterSpacing: 0.8, color: C.acento)),
      );
}
