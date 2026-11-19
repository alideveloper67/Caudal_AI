import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../premium/canje_pase.dart';
import '../servicios.dart';
import '../tema.dart';

/// Donar a Caudal con Yape. Se abre desde Ajustes y desde las funciones exclusivas
/// de donadores (fondo, mascotita, GIF): un botón discreto que muestra el QR y
/// explica cómo mandar la captura del pago para que se compruebe.
///
/// El QR es la imagen `assets/donar/yape_qr.png`: para cambiarlo basta reemplazar ese archivo.
const numeroComprobante = '902464984';
const _qrAsset = 'assets/donar/yape_qr.png';
const _oro = Color(0xFFFFC857);

/// Abre el QR de Yape con las instrucciones.
Future<void> mostrarDonar(BuildContext context) => showDialog<void>(
      context: context,
      builder: (_) => const _DonarDialogo(),
    );

/// Aviso corto para las pantallas exclusivas: «Exclusivo para donadores · Donar aquí».
class AvisoDonar extends StatelessWidget {
  const AvisoDonar({super.key, this.texto = 'Exclusivo para donadores'});
  final String texto;

  @override
  Widget build(BuildContext context) => Wrap(
        crossAxisAlignment: WrapCrossAlignment.center,
        alignment: WrapAlignment.center,
        spacing: 6,
        children: [
          Text(texto, style: estiloSecundario),
          TextButton.icon(
            onPressed: () => mostrarDonar(context),
            icon: const Icon(Icons.favorite_rounded, size: 16, color: _oro),
            label: const Text('Donar aquí'),
            style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
          ),
        ],
      );
}

class _DonarDialogo extends StatelessWidget {
  const _DonarDialogo();

  Future<void> _copiar(BuildContext context) async {
    await Clipboard.setData(const ClipboardData(text: numeroComprobante));
    if (context.mounted) Caudal.leer(context).avisar('Número copiado');
  }

  Future<void> _whatsapp(BuildContext context) async {
    final ok = await launchUrl(Uri.parse('https://wa.me/51$numeroComprobante'), mode: LaunchMode.externalApplication)
        .catchError((_) => false);
    if (!ok && context.mounted) Caudal.leer(context).avisar('No pude abrir WhatsApp. Escribe al $numeroComprobante.');
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: C.panel,
      insetPadding: const EdgeInsets.all(20),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: C.borde)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 400),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(22, 22, 22, 14),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.favorite_rounded, size: 40, color: _oro),
            const SizedBox(height: 10),
            const Text('Apoya a Caudal con Yape',
                textAlign: TextAlign.center, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            const Text(
              'Caudal es gratis. Si lo apoyas, tu cuenta pasa a ser «Donador de Caudal»: fondo propio en toda la app, '
              'GIF en tu perfil y una mascotita en la barra de la canción.',
              textAlign: TextAlign.center,
              style: estiloSecundario,
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
              child: Image.asset(_qrAsset,
                  width: 260,
                  fit: BoxFit.contain,
                  errorBuilder: (_, _, _) => const SizedBox(
                      width: 260,
                      height: 230,
                      child: Center(
                          child: Text('El QR de Yape aún no está disponible.',
                              textAlign: TextAlign.center, style: TextStyle(color: Colors.black54))))),
            ),
            const SizedBox(height: 16),
            const Text('Escanea el QR o yapea al $numeroComprobante',
                textAlign: TextAlign.center, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            const Text(
              'Después envía la captura del pago por WhatsApp a ese mismo número, con tu usuario de Caudal. '
              'La comprobamos y activamos tus beneficios.',
              textAlign: TextAlign.center,
              style: estiloSecundario,
            ),
            const SizedBox(height: 12),
            Wrap(alignment: WrapAlignment.center, spacing: 8, runSpacing: 4, children: [
              FilledButton.icon(
                onPressed: () => _whatsapp(context),
                icon: const Icon(Icons.chat_rounded, size: 18),
                label: const Text('Enviar captura'),
              ),
              OutlinedButton.icon(
                onPressed: () => _copiar(context),
                icon: const Icon(Icons.copy_rounded, size: 18),
                label: const Text(numeroComprobante),
              ),
            ]),
            const SizedBox(height: 6),
            TextButton.icon(
              onPressed: () {
                final nav = Navigator.of(context);
                final ctx = nav.context;
                nav.pop();
                mostrarCanjePase(ctx);
              },
              icon: const Icon(Icons.confirmation_number_outlined, size: 18),
              label: const Text('Tengo un código de prueba'),
            ),
            TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cerrar')),
          ]),
        ),
      ),
    );
  }
}
