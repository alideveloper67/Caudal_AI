import 'dart:async';

import 'package:flutter/material.dart';

import '../../reproduccion/reproductor.dart';
import '../../reproduccion/sesion_medios.dart';
import '../reproductor/hueco_video_web.dart';
import '../servicios.dart';

/// «Modo reposo» (versión web en el teléfono): la pantalla queda encendida pero
/// casi toda negra, con la hora y lo que suena. Así no se corta lo de YouTube,
/// que el navegador calla al bloquear el teléfono y que pide que su video se vea.
class ModoReposoPagina extends StatefulWidget {
  const ModoReposoPagina({super.key});

  static Future<void> abrir(BuildContext context) => Navigator.of(context, rootNavigator: true)
      .push(MaterialPageRoute<void>(fullscreenDialog: true, builder: (_) => const ModoReposoPagina()));

  @override
  State<ModoReposoPagina> createState() => _ModoReposoPaginaState();
}

class _ModoReposoPaginaState extends State<ModoReposoPagina> {
  Timer? _reloj;
  bool? _encendida;

  @override
  void initState() {
    super.initState();
    _reloj = Timer.periodic(const Duration(seconds: 10), (_) {
      if (mounted) setState(() {});
    });
    unawaited(() async {
      final si = await SesionMedios.pantallaEncendida(true);
      if (mounted) setState(() => _encendida = si);
    }());
  }

  @override
  void dispose() {
    _reloj?.cancel();
    unawaited(SesionMedios.pantallaEncendida(false));
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final r = Caudal.of(context).reproductor;
    const tenue = Color(0xFF6B7280);
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: ListenableBuilder(
          listenable: r,
          builder: (context, _) {
            final p = r.actual;
            final ahora = DateTime.now();
            final youtube = r.fuente?.esYouTubeWeb ?? false;
            return LayoutBuilder(
              builder: (context, c) => SingleChildScrollView(
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: c.maxHeight, minWidth: c.maxWidth),
                  child: Column(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                    Align(
                      alignment: Alignment.centerRight,
                      child: IconButton(
                        tooltip: 'Salir del modo reposo',
                        icon: const Icon(Icons.close_rounded, color: tenue),
                        onPressed: () => Navigator.of(context).pop(),
                      ),
                    ),
                    Column(children: [
                      Text('${ahora.hour.toString().padLeft(2, '0')}:${ahora.minute.toString().padLeft(2, '0')}',
                          style: const TextStyle(fontSize: 72, fontWeight: FontWeight.w300, color: Color(0xFF9CA3AF))),
                      const SizedBox(height: 18),
                      // YouTube pide un recuadro de al menos 200 px de alto
                      if (youtube) const SizedBox(width: 356, child: HuecoVideoWeb()),
                      const SizedBox(height: 18),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 28),
                        child: Column(children: [
                          Text('${p?['titulo'] ?? 'Nada sonando'}', textAlign: TextAlign.center, maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 17, color: Color(0xFF9CA3AF))),
                          const SizedBox(height: 4),
                          Text('${p?['artista'] ?? ''}', textAlign: TextAlign.center, maxLines: 1,
                              overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14, color: tenue)),
                        ]),
                      ),
                      const SizedBox(height: 14),
                      Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                        IconButton(tooltip: 'Anterior', iconSize: 34, color: tenue,
                            icon: const Icon(Icons.skip_previous_rounded), onPressed: r.anterior),
                        const SizedBox(width: 18),
                        IconButton(
                          tooltip: r.estado == EstadoRepro.sonando ? 'Pausar' : 'Reproducir',
                          iconSize: 52, color: const Color(0xFF9CA3AF),
                          icon: Icon(r.estado == EstadoRepro.sonando
                              ? Icons.pause_circle_outline_rounded
                              : Icons.play_circle_outline_rounded),
                          onPressed: r.alternar,
                        ),
                        const SizedBox(width: 18),
                        IconButton(tooltip: 'Siguiente', iconSize: 34, color: tenue,
                            icon: const Icon(Icons.skip_next_rounded), onPressed: () => r.siguiente()),
                      ]),
                    ]),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(28, 12, 28, 20),
                      child: Text(
                        switch (_encendida) {
                          null => '',
                          true => 'No bloquees el teléfono: la pantalla se queda encendida mientras estés aquí. '
                              'Baja el brillo para gastar menos batería.',
                          false => 'Este navegador no deja mantener la pantalla encendida (puede ser el ahorro de '
                              'batería). Sube el tiempo de apagado de pantalla en los ajustes del teléfono.',
                        },
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 12.5, color: tenue),
                      ),
                    ),
                  ]),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
