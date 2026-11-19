import 'package:flutter/material.dart';

import '../../nucleo/capsula_tiempo.dart';
import '../../nucleo/premium.dart';
import '../tema.dart';
import 'capsula_ui.dart';
import 'portada_perfil_ui.dart';

const _oro = Color(0xFFFFC857);

/// Las novedades de donador que no son un marco ni un tema: la portada del perfil, la cápsula del tiempo y
/// las dedicatorias (que se mandan desde el chat). Se ve en «Personalizar», con y sin beneficios: sin ellos
/// se puede mirar y probar, pero no guardar.
class AtajosDonador extends StatelessWidget {
  const AtajosDonador({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([Premium.i, CapsulasTiempo.i]),
      builder: (context, _) {
        final activo = Premium.i.activo;
        final n = CapsulasTiempo.i.guardadas.length;
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
            padding: const EdgeInsets.only(bottom: Esp.s),
            child: Text('Más para donadores', style: estiloTituloSeccion.copyWith(fontSize: 18)),
          ),
          Container(
            decoration: BoxDecoration(
              color: C.superficie2,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: C.borde),
            ),
            clipBehavior: Clip.antiAlias,
            // el Material deja que las ListTile pinten su toque sobre el fondo de la caja
            child: Material(type: MaterialType.transparency, child: Column(children: [
              _Atajo(
                icono: Icons.photo_size_select_actual_rounded,
                titulo: 'Portada del perfil',
                texto: activo
                    ? 'Tu canción del momento, una letra y tu mascota arriba del perfil'
                    : 'Tu canción del momento, una letra y tu mascota · exclusivo',
                alTocar: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const PortadaPagina())),
              ),
              Divider(height: 1, color: C.borde),
              _Atajo(
                icono: Icons.hourglass_top_rounded,
                titulo: 'Cápsula del tiempo',
                texto: n > 0
                    ? '$n ${n == 1 ? 'guardada' : 'guardadas'} · se abren en su fecha'
                    : 'Una canción y un mensaje que Caudal te devuelve en un año · exclusivo',
                alTocar: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const CapsulasPagina())),
              ),
              Divider(height: 1, color: C.borde),
              const _Atajo(
                icono: Icons.mail_outline_rounded,
                titulo: 'Dedicatorias',
                texto: 'Mándale una canción a un amigo con tarjeta y mensaje desde su chat, con el icono del sobre',
              ),
            ])),
          ),
        ]);
      },
    );
  }
}

class _Atajo extends StatelessWidget {
  const _Atajo({required this.icono, required this.titulo, required this.texto, this.alTocar});
  final IconData icono;
  final String titulo;
  final String texto;
  final VoidCallback? alTocar;

  @override
  Widget build(BuildContext context) => ListTile(
        onTap: alTocar,
        leading: Icon(icono, color: _oro),
        title: Text(titulo, style: const TextStyle(fontWeight: FontWeight.w800)),
        subtitle: Text(texto, style: estiloSecundario),
        trailing: alTocar == null ? null : const Icon(Icons.chevron_right_rounded, color: C.texto3),
      );
}
