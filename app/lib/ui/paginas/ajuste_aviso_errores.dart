// Filas de Ajustes para lo nuevo: la casilla del aviso de errores y la entrada a los logros.
//
//   const AjusteAvisoErrores(),
//   if (VigiaLogros.vigente != null) EntradaLogros(vigia: VigiaLogros.vigente!),

import 'package:flutter/material.dart';

import '../../nucleo/aviso_errores.dart';
import '../../nucleo/logros_vigia.dart';
import '../logros_insignia.dart';
import '../tema.dart';
import 'logros_pagina.dart';

class AjusteAvisoErrores extends StatefulWidget {
  const AjusteAvisoErrores({super.key});

  @override
  State<AjusteAvisoErrores> createState() => _AjusteAvisoErroresState();
}

class _AjusteAvisoErroresState extends State<AjusteAvisoErrores> {
  bool? _activo;

  @override
  void initState() {
    super.initState();
    AvisoErrores.activo().then((v) {
      if (mounted) setState(() => _activo = v);
    });
  }

  @override
  Widget build(BuildContext context) => SwitchListTile.adaptive(
        secondary: const Icon(Icons.bug_report_outlined, color: C.texto2),
        title: const Text('Enviar informes de errores'),
        subtitle: const Text(
            'Si Caudal se cierra o falla, manda un informe sin datos personales (versión, sistema, pantalla y '
            'dónde falló) para poder arreglarlo. Va solo a Caudal, sin servicios de terceros.',
            style: estiloSecundario),
        value: _activo ?? true,
        onChanged: _activo == null
            ? null
            : (v) {
                setState(() => _activo = v);
                AvisoErrores.ponerActivo(v);
              },
      );
}

class EntradaLogros extends StatelessWidget {
  const EntradaLogros({super.key, required this.vigia});
  final VigiaLogros vigia;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: vigia.logros,
        builder: (context, _) {
          final r = vigia.logros.resumen;
          return ListTile(
            leading: const InsigniaLogro(clave: 'coleccionista', lado: 24, halo: oroLogros),
            title: const Text('Tus logros'),
            subtitle: Text('${r.conseguidos} de ${r.total} insignias · elige cuáles lucir en tu perfil',
                style: estiloSecundario),
            trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
            onTap: () => LogrosPagina.abrir(context, vigia.logros, alCambiarVitrina: vigia.pronto),
          );
        },
      );
}
