// La vitrina de logros del perfil: los (hasta 3) que la persona eligió lucir. En el perfil propio
// se lee del dispositivo y lleva «Ver todos»; en el de otra persona se pide a la nube (con las
// mismas reglas que su perfil) y, si no hay nada que enseñar, no ocupa lugar.

import 'package:flutter/material.dart';

import '../nucleo/logros.dart';
import '../nucleo/nube.dart';
import 'logros_insignia.dart';
import 'paginas/logros_pagina.dart';
import 'tema.dart';

class VitrinaLogros extends StatefulWidget {
  const VitrinaLogros({super.key, required this.usuario, required this.propio, this.sesion, this.logros,
      this.alCambiarVitrina, this.cargar});

  final String usuario;
  final bool propio;
  final Sesion? sesion;

  /// Los del dispositivo (perfil propio).
  final Logros? logros;
  final VoidCallback? alCambiarVitrina;

  /// Para las pruebas: cómo se pide la vitrina de otra persona.
  final Future<({List<String> vitrina, int total, Map<String, int> fechas})?> Function(Sesion?, String)? cargar;

  @override
  State<VitrinaLogros> createState() => _VitrinaLogrosState();
}

class _VitrinaLogrosState extends State<VitrinaLogros> {
  Future<({List<String> vitrina, int total, Map<String, int> fechas})?>? _otra;

  @override
  void initState() {
    super.initState();
    if (!widget.propio) _otra = (widget.cargar ?? vitrinaDe)(widget.sesion, widget.usuario);
  }

  @override
  Widget build(BuildContext context) {
    final lg = widget.logros;
    if (widget.propio && lg != null) {
      return ListenableBuilder(
        listenable: lg,
        builder: (context, _) => _caja(lg.vitrina, lg.desbloqueados.length, lg.desbloqueados),
      );
    }
    return FutureBuilder(
      future: _otra,
      builder: (context, f) {
        final d = f.data;
        if (d == null || d.vitrina.isEmpty) return const SizedBox.shrink();
        return _caja(d.vitrina, d.total, d.fechas);
      },
    );
  }

  Widget _caja(List<String> vitrina, int total, Map<String, int> fechas) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.lado, 18, Esp.lado, 4),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Expanded(child: Text('Logros', style: estiloTituloSeccion)),
          Text('$total de ${catalogoLogros.length}', style: estiloSecundario),
          if (widget.propio && widget.logros != null)
            TextButton(
              onPressed: () => LogrosPagina.abrir(context, widget.logros!, alCambiarVitrina: widget.alCambiarVitrina),
              child: const Text('Ver todos'),
            ),
        ]),
        const SizedBox(height: 8),
        if (vitrina.isEmpty)
          const Text('Elige hasta 3 logros en «Ver todos» para lucirlos aquí.', style: estiloDetalle)
        else
          Wrap(spacing: 14, runSpacing: 10, children: [
            for (final id in vitrina)
              if (logroPorId[id] != null)
                Tooltip(
                  message: logroPorId[id]!.descripcion,
                  child: SizedBox(
                    width: 96,
                    child: Column(children: [
                      InsigniaLogro(clave: id, lado: 48, halo: oroLogros),
                      const SizedBox(height: 6),
                      Text(logroPorId[id]!.nombre, textAlign: TextAlign.center, maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                    ]),
                  ),
                ),
          ]),
      ]),
    );
  }
}
