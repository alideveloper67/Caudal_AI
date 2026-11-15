import 'package:flutter/material.dart';

import '../../nucleo/mezcla_dj.dart';
import '../servicios.dart';
import '../tema.dart';

/// Los ajustes de la «Mezcla DJ» automatica: encenderla, cuanto dura el cambio
/// (4 a 16 s) y si cambian los graves. Se guardan al momento. Sirve igual
/// dentro de Ajustes, de la hoja de Sonido o de la hoja del reproductor.
class MezclaDjControles extends StatefulWidget {
  const MezclaDjControles({super.key, this.alAbrirMezclador});

  /// Si se da, sale un acceso a la mesa del Mezclador.
  final VoidCallback? alAbrirMezclador;

  @override
  State<MezclaDjControles> createState() => _MezclaDjControlesState();
}

class _MezclaDjControlesState extends State<MezclaDjControles> {
  Future<void> _poner(String clave, Object valor) async {
    final s = Caudal.leer(context);
    await s.ajustes.poner(clave, valor);
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final a = Caudal.leer(context).ajustes;
    final activa = a.sino('mezcla_dj');
    final seg = segundosDj(a.entero('mezcla_dj_seg'));
    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
      SwitchListTile.adaptive(
        contentPadding: EdgeInsets.zero,
        title: const Text('Mezcla DJ', style: TextStyle(fontWeight: FontWeight.w700)),
        subtitle: const Text('Une las canciones como un DJ: la siguiente entra antes de que acabe la actual, sin cortes',
            style: estiloSecundario),
        value: activa,
        onChanged: (v) => _poner('mezcla_dj', v),
      ),
      AnimatedSize(
        duration: Mov.normal,
        curve: Mov.curva,
        alignment: Alignment.topCenter,
        child: activa
            ? Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  const Expanded(child: Text('Duración del cambio')),
                  Text('$seg s', style: const TextStyle(fontWeight: FontWeight.w800)),
                ]),
                Slider(
                  value: seg.toDouble(),
                  min: djMin.toDouble(),
                  max: djMax.toDouble(),
                  divisions: djMax - djMin,
                  label: '$seg s',
                  onChanged: (v) => _poner('mezcla_dj_seg', v.round()),
                ),
                SwitchListTile.adaptive(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Cambio de graves'),
                  subtitle: const Text('Mientras una se va y la otra llega, los graves pasan de una a otra',
                      style: estiloSecundario),
                  value: a.sino('mezcla_dj_graves'),
                  onChanged: (v) => _poner('mezcla_dj_graves', v),
                ),
                if (widget.alAbrirMezclador != null)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      onPressed: widget.alAbrirMezclador,
                      icon: const Icon(Icons.album_rounded),
                      label: const Text('Armar mi propia mezcla'),
                    ),
                  ),
              ])
            : const SizedBox(width: double.infinity),
      ),
    ]);
  }
}

/// La hoja que abre el reproductor con los ajustes de la «Mezcla DJ».
Future<void> mostrarMezclaDj(BuildContext context, {VoidCallback? alAbrirMezclador}) =>
    showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Mezcla DJ', style: estiloTituloSeccion),
              const SizedBox(height: 6),
              MezclaDjControles(alAbrirMezclador: alAbrirMezclador == null
                  ? null
                  : () {
                      Navigator.pop(ctx);
                      alAbrirMezclador();
                    }),
            ]),
          ),
        ),
      ),
    );
