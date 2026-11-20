import 'package:flutter/material.dart';

import '../../nucleo/despertador.dart';
import '../../nucleo/despertador_control.dart';
import '../../nucleo/letra_pantalla_bloqueo.dart';
import '../../nucleo/plataforma.dart';
import '../tema.dart';
import 'despertador_pagina.dart';

/// Las dos entradas de Ajustes: «Despertador» (con la próxima alarma) y, en Android, «Letra en la
/// pantalla bloqueada». Se pone tal cual en la lista de Ajustes (`const AjustesDespertador()`).
class AjustesDespertador extends StatefulWidget {
  const AjustesDespertador({super.key, this.control, this.letra});

  /// Para las pruebas; por defecto, los de la app.
  final ControlDespertador? control;
  final LetraEnBloqueo? letra;

  @override
  State<AjustesDespertador> createState() => _AjustesDespertadorState();
}

class _AjustesDespertadorState extends State<AjustesDespertador> {
  ControlDespertador get _c => widget.control ?? ControlDespertador.i;
  LetraEnBloqueo get _l => widget.letra ?? LetraEnBloqueo.i;

  @override
  void initState() {
    super.initState();
    _c.addListener(_repintar);
    if (!_c.cargadas) _c.cargar();
    _l.leerAjuste().then((_) => _repintar());
  }

  @override
  void dispose() {
    _c.removeListener(_repintar);
    super.dispose();
  }

  void _repintar() {
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final p = _c.proxima();
    return Column(mainAxisSize: MainAxisSize.min, children: [
      ListTile(
        leading: const Icon(Icons.alarm_rounded, color: C.texto2),
        title: const Text('Despertador'),
        subtitle: Text(
          p == null
              ? 'Despierta con una canción, una lista, un mix o tus «me gusta»'
              : '${p.$1.textoHora} · ${textoFalta(p.$2.difference(DateTime.now()))}',
          style: estiloSecundario,
        ),
        trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => DespertadorPagina(control: _c))),
      ),
      if (Plataforma.esAndroid)
        ValueListenableBuilder<bool>(
          valueListenable: _l.activa,
          builder: (_, si, __) => SwitchListTile.adaptive(
            secondary: const Icon(Icons.lyrics_rounded, color: C.texto2),
            title: const Text('Letra en la pantalla bloqueada'),
            subtitle: const Text('El verso que suena, visible sin desbloquear. Tócalo para verlo en grande.',
                style: estiloSecundario),
            value: si,
            onChanged: _l.poner,
          ),
        ),
    ]);
  }
}
