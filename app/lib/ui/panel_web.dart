import 'package:flutter/material.dart';

import '../nucleo/calidad_sonido.dart';
import '../nucleo/catalogo.dart';
import '../nucleo/coleccion.dart' show Json;
import '../nucleo/musica_libre.dart';
import 'comunes.dart';
import 'paginas/cola_hoja.dart';
import 'reproductor/hueco_video_web.dart';
import 'reproductor/letra_corrida.dart';
import 'servicios.dart';
import 'tema.dart';

/// El panel de la derecha de Caudal Escritorio, en el navegador con ventana
/// ancha: Sonando, Cola o Letra. Recuerda cuál estaba abierto.
class PanelWeb extends StatelessWidget {
  const PanelWeb({super.key});

  static const clave = 'panel_derecho';
  static const anchoMinimo = 1180.0;
  static const ancho = 330.0;
  static const vistas = {'sonando': 'Sonando', 'cola': 'Cola', 'letras': 'Letra'};

  static String abierto(Servicios s) {
    final v = s.ajustes.texto(clave);
    return vistas.containsKey(v) ? v : '';
  }

  /// Abre [vista], o cierra el panel si ya era la que se veía.
  static void alternar(Servicios s, String vista) =>
      s.ajustes.poner(clave, abierto(s) == vista ? 'oculto' : vista);

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    return ListenableBuilder(
      listenable: s.ajustes,
      builder: (context, _) {
        final v = abierto(s);
        if (v.isEmpty) return const SizedBox.shrink();
        return Container(
          width: ancho,
          decoration: BoxDecoration(color: C.panel, border: Border(left: BorderSide(color: C.borde))),
          child: Material(
            type: MaterialType.transparency,
            child: Column(children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 10, 4, 4),
                child: Row(children: [
                  for (final e in vistas.entries)
                    TextButton(
                      onPressed: () => s.ajustes.poner(clave, e.key),
                      style: TextButton.styleFrom(
                          foregroundColor: e.key == v ? C.texto : C.texto2,
                          padding: const EdgeInsets.symmetric(horizontal: 10)),
                      child: Text(e.value, style: TextStyle(fontWeight: e.key == v ? FontWeight.w900 : FontWeight.w600)),
                    ),
                  const Spacer(),
                  IconButton(
                    tooltip: 'Cerrar el panel',
                    iconSize: 20,
                    icon: const Icon(Icons.close_rounded, color: C.texto2),
                    onPressed: () => s.ajustes.poner(clave, 'oculto'),
                  ),
                ]),
              ),
              Expanded(
                child: switch (v) {
                  'cola' => const ColaLista(),
                  'letras' => const LetraCorrida(tamano: 21),
                  _ => const _Sonando(),
                },
              ),
            ]),
          ),
        );
      },
    );
  }
}

class _Sonando extends StatelessWidget {
  const _Sonando();

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final r = s.reproductor;
    return ListenableBuilder(
      listenable: Listenable.merge([r, s.coleccion]),
      builder: (context, _) {
        final p = r.actual;
        if (p == null) {
          return const Center(child: Text('Aquí verás lo que suena.', style: estiloSecundario));
        }
        final gusta = s.coleccion.meGusta('${p['clave']}');
        final calidad = calidadDe(r.fuente, enVideo: r.modo == 'video');
        final artistas = p['artistas'];
        final idArtista = artistas is List && artistas.isNotEmpty && artistas.first is Map
            ? '${(artistas.first as Map)['id'] ?? ''}'
            : '';
        final siguiente = r.proximas.isNotEmpty
            ? r.proximas.first
            : (r.siguientesDeContexto.isEmpty ? null : r.siguientesDeContexto.first);
        const lado = PanelWeb.ancho - 33;
        final youtube = r.fuente?.esYouTubeWeb ?? false;
        final lista = ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 20), children: [
          if (!youtube)
            InkWell(
              onTap: () => s.abrirReproductor(context),
              child: Portada(url: '${p['miniatura'] ?? ''}', lado: lado, radio: 10),
            ),
          const SizedBox(height: 14),
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${p['titulo'] ?? ''}', style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900)),
                const SizedBox(height: 2),
                Text('${p['artista'] ?? ''}', style: estiloSecundario),
              ]),
            ),
            IconButton(
              tooltip: gusta ? 'Quitar de Tus me gusta' : 'Me gusta',
              icon: Icon(gusta ? Icons.favorite_rounded : Icons.favorite_border_rounded, color: gusta ? C.acento : C.texto2),
              onPressed: () => s.alternarMeGusta(p),
            ),
            IconButton(
              tooltip: 'Más opciones',
              icon: const Icon(Icons.more_horiz_rounded, color: C.texto2),
              onPressed: () => s.hojaPista(context, p),
            ),
          ]),
          if (calidad != null)
            _Tarjeta('Cómo suena', [
              Text(
                (r.fuente?.esYouTubeWeb ?? false)
                    ? 'Con el reproductor de YouTube, que elige la calidad.'
                    : MusicaLibre.es(p)
                        ? 'Música libre de Audius. Los derechos son de ${p['artista']}.'
                        : '${calidad.etiqueta} · ${(r.fuente?.url ?? '').startsWith('web:') ? 'guardada en este navegador' : 'música de la comunidad'}',
                style: estiloSecundario,
              ),
            ]),
          if (idArtista.isNotEmpty) _Artista(key: ValueKey(idArtista), id: idArtista),
          if (siguiente != null)
            _Tarjeta('Siguiente en la cola', [FilaPista(pista: siguiente, alPulsar: () => r.siguiente())], lados: 0),
        ]);
        if (!youtube) return lista;
        // el video de YouTube va fijo: si se desplazara con la lista taparía lo de arriba
        return Column(children: [
          const Padding(padding: EdgeInsets.fromLTRB(16, 4, 16, 8), child: HuecoVideoWeb()),
          Expanded(child: lista),
        ]);
      },
    );
  }
}

class _Tarjeta extends StatelessWidget {
  const _Tarjeta(this.titulo, this.hijos, {this.lados = 14});
  final String titulo;
  final List<Widget> hijos;
  final double lados;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(top: 14),
        padding: EdgeInsets.fromLTRB(lados, 12, lados, 12),
        decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(12)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
            padding: EdgeInsets.only(left: 14 - lados, bottom: 8),
            child: Text(titulo, style: const TextStyle(fontWeight: FontWeight.w800)),
          ),
          ...hijos,
        ]),
      );
}

class _Artista extends StatefulWidget {
  const _Artista({super.key, required this.id});
  final String id;

  @override
  State<_Artista> createState() => _ArtistaState();
}

class _ArtistaState extends State<_Artista> {
  static final Map<String, Json> _cache = {};
  Json? _a;

  @override
  void initState() {
    super.initState();
    _a = _cache[widget.id];
    if (_a == null) {
      Catalogo.artista(widget.id).then((a) {
        if (_cache.length > 60) _cache.clear();
        _cache[widget.id] = a;
        if (mounted) setState(() => _a = a);
      }, onError: (_) {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final a = _a;
    if (a == null) return const SizedBox.shrink();
    var bio = '${a['descripcion'] ?? ''}'.trim();
    if (bio.length > 320) bio = '${bio.substring(0, 317).trimRight()}…';
    return _Tarjeta('Acerca del artista', [
      if ('${a['foto'] ?? ''}'.isNotEmpty)
        Portada(url: '${a['foto']}', lado: PanelWeb.ancho - 61, alto: 165, radio: 8, icono: Icons.person_rounded),
      const SizedBox(height: 10),
      InkWell(
        onTap: () => Caudal.leer(context).irAArtista(context, widget.id),
        child: Text('${a['titulo'] ?? ''}',
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, decoration: TextDecoration.underline)),
      ),
      if ('${a['subtitulo'] ?? ''}'.isNotEmpty) Text('${a['subtitulo']}', style: estiloSecundario),
      if (bio.isNotEmpty) ...[const SizedBox(height: 6), Text(bio, style: estiloSecundario)],
    ]);
  }
}
