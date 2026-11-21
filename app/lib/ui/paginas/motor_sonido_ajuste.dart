// Ajustes › Motor de sonido (solo Android): automático, el de Caudal o el de Android.
// Ver reproduccion/motor_eleccion.dart.

import 'package:flutter/material.dart';

import '../../nucleo/version.dart' show versionApp;
import '../../reproduccion/motor_eleccion.dart';
import '../servicios.dart';
import '../tema.dart';

class MotorSonidoAjuste extends StatelessWidget {
  const MotorSonidoAjuste({super.key});

  static const opciones = [
    ('automatico', 'Automático', 'El de Caudal; si en tu teléfono se cierra, pasa solo al de Android.'),
    ('caudal', 'Caudal', 'Con ecualizador, transiciones DJ, video y volumen máximo.'),
    ('android', 'Android', 'El reproductor del teléfono: el más estable, solo música (sin ecualizador ni video).'),
  ];

  static String resumen(String ajuste) {
    final ahora = EleccionMotor.actual == MotorSonido.android ? 'suena con el de Android' : 'suena con el de Caudal';
    final nombre = opciones.firstWhere((o) => o.$1 == ajuste, orElse: () => opciones.first).$2;
    final por = EleccionMotor.motivo.isEmpty || ajuste != 'automatico' ? '' : ' · ${EleccionMotor.motivo}';
    return '$nombre · $ahora$por';
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    return ListenableBuilder(
      listenable: s.ajustes,
      builder: (context, _) {
        final actual = s.ajustes.texto(EleccionMotor.claveAjuste);
        return ListTile(
          leading: Icon(Icons.graphic_eq_rounded, color: C.acento),
          title: const Text('Motor de sonido'),
          subtitle: Text(resumen(actual), style: estiloSecundario),
          trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
          onTap: () => _elegir(context, actual),
        );
      },
    );
  }

  Future<void> _elegir(BuildContext context, String actual) async {
    final s = Caudal.leer(context);
    final elegido = await showModalBottomSheet<String>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 18, 20, 6),
            child: Text('Motor de sonido', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          ),
          for (final o in opciones)
            ListTile(
              leading: Icon(o.$1 == actual ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded,
                  color: o.$1 == actual ? C.acento : C.texto3),
              title: Text(o.$2, style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text(o.$3, style: estiloSecundario),
              onTap: () => Navigator.of(ctx).pop(o.$1),
            ),
          const SizedBox(height: 8),
        ]),
      ),
    );
    if (elegido == null || elegido == actual) return;
    await s.ajustes.poner(EleccionMotor.claveAjuste, elegido);
    // se cambia ya, sin reiniciar la app, y la canción sigue donde iba
    await EleccionMotor.preparar(ajuste: elegido, version: versionApp);
    await s.reproductor.renovarMotores('elegido en Ajustes: $elegido');
  }
}
