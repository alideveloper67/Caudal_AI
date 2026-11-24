import 'dart:async';

import 'package:flutter/foundation.dart' show defaultTargetPlatform;
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/musica_libre.dart';
import '../servicios.dart';
import '../tema.dart';
import 'modo_reposo_pagina.dart';
import 'musica_libre_pagina.dart';

const _descargarApp = 'https://caudal-musica.netlify.app/#descargar';

/// Abre la canción en la app de Caudal de Android; si no está instalada, el
/// navegador va a la página de descarga.
String enlaceAppCaudal(Json pista) {
  final q = Uri.encodeComponent('${pista['titulo'] ?? ''} ${pista['artista'] ?? ''}'.trim());
  return 'intent://sonar?q=$q#Intent;scheme=caudal;package=com.kevinrr.caudal;'
      'S.browser_fallback_url=${Uri.encodeComponent(_descargarApp)};end';
}

/// La canción en YouTube Music, desde donde iba.
String enlaceYouTubeMusic(String videoId, Duration desde) =>
    'https://music.youtube.com/watch?v=$videoId${desde.inSeconds > 5 ? '&t=${desde.inSeconds}' : ''}';

/// «Segundo plano» (versión web en el teléfono): qué se puede hacer con una
/// canción para salir de Caudal o apagar la pantalla, según de dónde venga.
Future<void> mostrarSegundoPlano(BuildContext context, Json? pista) {
  final s = Caudal.leer(context);
  final r = s.reproductor;
  final p = pista ?? const <String, dynamic>{};
  final vid = '${p['video_id'] ?? ''}';
  final esLaQueSuena = r.actual != null && '${r.actual!['clave']}' == '${p['clave']}';
  final android = defaultTargetPlatform == TargetPlatform.android;
  final bloqueada = pista != null && suenaBloqueada(p);

  Future<void> fuera(String url, {bool aqui = false}) async {
    // que no suenen las dos a la vez
    if (esLaQueSuena) await r.pausar();
    final ok = await launchUrl(Uri.parse(url), webOnlyWindowName: aqui ? '_self' : '_blank');
    if (!ok) s.avisar('El navegador no dejó abrirlo.');
  }

  return showModalBottomSheet<void>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    showDragHandle: true,
    backgroundColor: C.superficie2,
    constraints: const BoxConstraints(maxWidth: 560),
    builder: (ctx) {
      void hacer(VoidCallback f) {
        Navigator.pop(ctx);
        f();
      }

      Widget opcion(IconData icono, String titulo, String texto, VoidCallback alPulsar) => ListTile(
            leading: Icon(icono, color: C.acento),
            title: Text(titulo, style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text(texto, style: estiloSecundario),
            onTap: () => hacer(alPulsar),
          );

      return SafeArea(
        child: ConstrainedBox(
          // deja libre la parte de arriba, donde va el video
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * .56),
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 0, 20, 4),
                child: Text('Segundo plano', style: estiloTituloSeccion),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
                child: Text(
                    bloqueada
                        ? 'Esta canción ya sigue sonando al salir o bloquear. No tienes que hacer nada.'
                        : 'Esta canción es de YouTube y se pausa al salir. Elige cómo seguir:',
                    style: estiloSecundario),
              ),
              if (!bloqueada && vid.isNotEmpty) ...[
                if (android)
                  opcion(Icons.smartphone_rounded, 'Seguir en la app de Caudal',
                      'Suena con la pantalla apagada. Se abre con esta canción; si no la tienes, te lleva a descargarla.',
                      () => unawaited(fuera(enlaceAppCaudal(p), aqui: true))),
                opcion(Icons.open_in_new_rounded, 'Seguir en YouTube Music',
                    'Con YouTube Premium o Music Premium suena con la pantalla apagada.',
                    () => unawaited(fuera(enlaceYouTubeMusic(vid, esLaQueSuena ? r.posicion.value : Duration.zero)))),
                if (esLaQueSuena)
                  opcion(Icons.picture_in_picture_alt_rounded, 'Ventana flotante',
                      'Para usar otras apps con la pantalla encendida.', () => unawaited(_pasosFlotante(context, android))),
              ],
              if (!bloqueada)
                opcion(Icons.screen_lock_portrait_rounded, 'Modo reposo',
                    'Pantalla encendida y casi negra, sin salir de Caudal.',
                    () => unawaited(ModoReposoPagina.abrir(context))),
              opcion(Icons.phonelink_lock_rounded, bloqueada ? 'Más música que suena bloqueada' : 'Buscar una versión que suene bloqueada',
                  'Canciones libres: siguen con la pantalla apagada.',
                  () => unawaited(MusicaLibrePagina.abrir(context,
                      busqueda: bloqueada ? '' : '${p['titulo'] ?? ''} ${p['artista'] ?? ''}'.trim()))),
              const SizedBox(height: 10),
            ]),
          ),
        ),
      );
    },
  );
}

/// El botón de pantalla completa es del recuadro de YouTube: solo lo puede tocar la persona.
Future<void> _pasosFlotante(BuildContext context, bool android) => showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      showDragHandle: true,
      backgroundColor: C.superficie2,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (_) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Ventana flotante', style: estiloTituloSeccion),
            const SizedBox(height: 10),
            const Text('1. Toca el video y pulsa su botón de pantalla completa.'),
            const SizedBox(height: 6),
            Text(android
                ? '2. Con el video en grande, ve al inicio del teléfono.'
                : '2. Pulsa el botón de ventana flotante del video, o ve al inicio del teléfono.'),
            const SizedBox(height: 6),
            const Text('3. El video queda flotando y sigue sonando.'),
            const SizedBox(height: 12),
            const Text('Depende de tu navegador: algunos no lo dejan. Si bloqueas el teléfono, se pausa.',
                style: estiloSecundario),
          ]),
        ),
      ),
    );
