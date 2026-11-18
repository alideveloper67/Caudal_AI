import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../nucleo/avisos.dart';
import '../tema.dart';

/// Muestra un aviso de Caudal (ver nucleo/avisos.dart) y lo da por visto al cerrarlo.
Future<void> mostrarAviso(BuildContext context, AvisoCaudal a) async {
  await showDialog<void>(
    context: context,
    builder: (_) => _AvisoDialogo(a),
  );
  await Avisos.marcarVisto(a.id);
}

class _AvisoDialogo extends StatelessWidget {
  const _AvisoDialogo(this.a);
  final AvisoCaudal a;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: C.panel,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: C.borde)),
      icon: Icon(Icons.campaign_rounded, color: C.acento, size: 34),
      title: Text(a.titulo, textAlign: TextAlign.center, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
      content: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 380),
        child: SingleChildScrollView(
          child: Text(a.texto, textAlign: TextAlign.center, style: estiloSecundario.copyWith(fontSize: 14.5, height: 1.45)),
        ),
      ),
      actionsAlignment: MainAxisAlignment.center,
      actionsOverflowAlignment: OverflowBarAlignment.center,
      actions: [
        if (a.enlace != null)
          FilledButton(
            onPressed: () async {
              try {
                await launchUrl(Uri.parse(a.enlace!), mode: LaunchMode.externalApplication);
              } catch (_) {}
            },
            child: Text(a.etiquetaEnlace ?? 'Abrir'),
          ),
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Entendido')),
      ],
    );
  }
}
