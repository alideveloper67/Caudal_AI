import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../nucleo/archivos_web.dart';
import '../../nucleo/coleccion.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'importar_archivos_hoja.dart';
import 'musica_libre_pagina.dart';

/// La pestaña «Descargar» en el navegador: la música propia que se guarda aquí
/// (suena sin internet y con el teléfono bloqueado) y el camino a la app.
class TuMusicaWeb extends StatefulWidget {
  const TuMusicaWeb({super.key});

  @override
  State<TuMusicaWeb> createState() => _TuMusicaWebState();
}

class _TuMusicaWebState extends State<TuMusicaWeb> {
  List<Json>? _lista;
  (int, int) _espacio = (0, 0);
  Coleccion? _col;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final c = Caudal.of(context).coleccion;
    if (identical(c, _col)) return;
    _col?.removeListener(_cargar);
    _col = c..addListener(_cargar);
    _cargar();
  }

  @override
  void dispose() {
    _col?.removeListener(_cargar);
    super.dispose();
  }

  Future<void> _cargar() async {
    final l = await _col!.descargadas(soloAudio: true);
    final e = await ArchivosWeb.espacio();
    if (!mounted) return;
    setState(() {
      _lista = [for (final p in l) if (ArchivosWeb.esRef('${p['archivo'] ?? ''}')) p];
      _espacio = e;
    });
  }

  static String _tamano(int b) => b >= 1 << 30
      ? '${(b / (1 << 30)).toStringAsFixed(1)} GB'
      : '${(b / (1 << 20)).toStringAsFixed(b < 10 << 20 ? 1 : 0)} MB';

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final lista = _lista;
    return Scaffold(
      body: CustomScrollView(key: const PageStorageKey('tu_musica_web'), slivers: [
        SliverPadding(
          padding: EdgeInsets.fromLTRB(Esp.lado, MediaQuery.paddingOf(context).top + 14, Esp.lado, 6),
          sliver: SliverList.list(children: [
            const Text('Tu música', style: estiloTituloPagina),
            const SizedBox(height: 4),
            const Text('Pon aquí tus canciones (MP3, M4A, FLAC…). Se guardan en este navegador y suenan sin '
                'internet y con el teléfono bloqueado.', style: estiloSecundario),
            const SizedBox(height: 16),
            Wrap(spacing: 10, runSpacing: 10, children: [
              FilledButton.icon(
                onPressed: () => importarDelTelefono(context),
                icon: const Icon(Icons.add_rounded),
                label: const Text('Agregar canciones'),
              ),
              if (lista != null && lista.isNotEmpty)
                OutlinedButton.icon(
                  onPressed: () => s.reproductor.reproducirLista(lista,
                      contexto: {'tipo': 'descargados', 'titulo': 'Tu música'}),
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: const Text('Escuchar todo'),
                ),
            ]),
            if (_espacio.$2 > 0) ...[
              const SizedBox(height: 10),
              Text('Caudal ocupa ${_tamano(_espacio.$1)} en este navegador. Si borras sus datos, se borran también.',
                  style: estiloSecundario),
            ],
            const SizedBox(height: 14),
          ]),
        ),
        if (lista != null && lista.isEmpty)
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.symmetric(vertical: 30),
              child: Vacio(icono: Icons.library_music_outlined, titulo: 'Aún no hay canciones aquí',
                  texto: 'Elige las que tengas en este equipo.'),
            ),
          ),
        if (lista != null)
          SliverList.builder(
            itemCount: lista.length,
            itemBuilder: (context, i) => FilaPista(
              pista: lista[i],
              alPulsar: () => s.reproductor.reproducirLista(lista, inicio: i,
                  contexto: {'tipo': 'descargados', 'titulo': 'Tu música'}),
            ),
          ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 26, Esp.lado, 110),
          sliver: SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(14)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('¿No tienes archivos?', style: estiloTituloSeccion),
                const SizedBox(height: 6),
                const Text('Hay miles de canciones libres que también suenan con el celular bloqueado.', style: estiloSecundario),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: () => MusicaLibrePagina.abrir(context),
                  icon: const Icon(Icons.phonelink_lock_rounded),
                  label: const Text('Ver música que suena bloqueada'),
                ),
                const SizedBox(height: 22),
                const Text('¿Quieres bajar canciones y videos de un enlace?', style: estiloTituloSeccion),
                const SizedBox(height: 6),
                const Text('El navegador no puede: eso lo hace la app de Caudal, con esta misma cuenta.',
                    style: estiloSecundario),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: () => launchUrl(Uri.parse('https://caudal-musica.netlify.app/#descargar')),
                  icon: const Icon(Icons.open_in_new_rounded),
                  label: const Text('Descargar la app'),
                ),
              ]),
            ),
          ),
        ),
      ]),
    );
  }
}
