import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/descargas.dart';
import '../../nucleo/formato.dart';
import '../../nucleo/modelos.dart';
import '../comunes.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';
import 'inicio.dart';

/// Descargar cualquier video de cualquier enlace: se pega, se ve y se baja.
class DescargasPagina extends StatefulWidget {
  const DescargasPagina({super.key});

  /// Lo que llega de "Compartir con Caudal" o de pegar un enlace en Buscar.
  static final ValueNotifier<String?> _entrante = ValueNotifier(null);
  static void pegar(String texto) => _entrante.value = texto;

  @override
  State<DescargasPagina> createState() => _DescargasPaginaState();
}

class _DescargasPaginaState extends State<DescargasPagina> with AutomaticKeepAliveClientMixin {
  final _campo = TextEditingController();
  String _url = '';
  Ficha? _ficha;
  bool _consultando = false;
  String? _errorFicha;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    DescargasPagina._entrante.addListener(_llegoEnlace);
    WidgetsBinding.instance.addPostFrameCallback((_) => _llegoEnlace());
  }

  @override
  void dispose() {
    DescargasPagina._entrante.removeListener(_llegoEnlace);
    _campo.dispose();
    super.dispose();
  }

  void _llegoEnlace() {
    final t = DescargasPagina._entrante.value;
    if (t == null) return;
    DescargasPagina._entrante.value = null;
    _campo.text = t;
    _analizar(t);
  }

  String? _extraerUrl(String texto) => RegExp(r'https?://\S+').firstMatch(texto)?.group(0);

  Future<void> _pegar() async {
    final s = Caudal.leer(context);
    final datos = await Clipboard.getData(Clipboard.kTextPlain);
    final t = datos?.text ?? '';
    if (t.isEmpty) return s.avisar('No hay nada copiado.');
    _campo.text = t;
    _analizar(t);
  }

  Future<void> _analizar(String texto) async {
    if (!mounted) return;
    final url = _extraerUrl(texto);
    // escribir despues del enlace no vuelve a consultarlo
    if (url != null && url == _url && (_ficha != null || _consultando)) return;
    setState(() {
      _url = url ?? '';
      _ficha = null;
      _errorFicha = url == null && texto.trim().isNotEmpty ? 'Eso no parece un enlace.' : null;
    });
    if (url == null) return;
    setState(() => _consultando = true);
    try {
      final f = await Caudal.leer(context).descargas.resolverSiPuede(url);
      if (mounted && _url == url) setState(() => _ficha = f);
    } catch (_) {
    } finally {
      // solo la consulta del enlace vigente apaga el "consultando"
      if (mounted && _url == url) setState(() => _consultando = false);
    }
  }

  Future<void> _descargar() async {
    final s = Caudal.leer(context);
    final o = await elegirFormato(context, titulo: _ficha?.titulo ?? 'Descargar este enlace');
    if (o == null || !mounted) return;
    final tipo = switch (o['tipo']) {
      'completo' => TipoMedio.completo, 'video' => TipoMedio.video, _ => TipoMedio.audio,
    };
    final vid = Catalogo.videoIdDe(_url);
    s.descargas.encolar(
      url: _url,
      tipo: tipo,
      calidad: o['calidad'] ?? 'mejor',
      formatoAudio: o['formato_audio'],
      titulo: _ficha?.titulo ?? '',
      autor: _ficha?.autor ?? '',
      miniatura: _ficha?.miniatura ?? '',
      meta: vid.isEmpty ? null : {'video_id': vid, 'titulo': _ficha?.titulo, 'artista': _ficha?.autor,
        'miniatura': _ficha?.miniatura, 'duracion': _ficha?.duracion, 'clave': 'yt:$vid', 'tipo': 'pista',
        'es_video': true},
    );
    if (!mounted) return;
    setState(() {
      _campo.clear();
      _url = '';
      _ficha = null;
      _consultando = false;
    });
    FocusScope.of(context).unfocus();
  }

  void _escuchar(bool video) {
    final s = Caudal.leer(context);
    final vid = Catalogo.videoIdDe(_url);
    if (vid.isEmpty) return s.avisar('Solo los enlaces de YouTube se pueden reproducir sin descargar.');
    final p = Catalogo.nuevaPista(vid, titulo: _ficha?.titulo ?? '', miniatura: _ficha?.miniatura ?? '',
        duracion: _ficha?.duracion ?? 0, esVideo: video,
        artistas: [if ((_ficha?.autor ?? '').isNotEmpty) {'nombre': _ficha!.autor, 'id': ''}]);
    s.reproducirPista(context, p);
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final s = Caudal.of(context);
    return Scaffold(
      body: ListenableBuilder(
        listenable: s.descargas,
        builder: (_, _) {
          final lista = s.descargas.lista;
          return CustomScrollView(key: const PageStorageKey('descargas'), slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: EdgeInsets.fromLTRB(Esp.lado, MediaQuery.paddingOf(context).top + 14, Esp.lado, 6),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Descargar', style: estiloTituloPagina),
                  const SizedBox(height: 4),
                  Text(
                      esIOS
                          ? 'Copia el enlace de cualquier video (YouTube, TikTok, Instagram, Facebook, X…) '
                              'y pégalo aquí.'
                          : 'Pega el enlace de cualquier video: YouTube, TikTok, Instagram, Facebook, X… '
                              'o compártelo con Caudal desde la otra app.',
                      style: estiloSecundario),
                  if (esIOS) const _DondeQuedaIOS(),
                  const SizedBox(height: 14),
                  TextField(
                    controller: _campo,
                    onSubmitted: _analizar,
                    onChanged: (t) {
                      if (t.contains('http')) _analizar(t);
                    },
                    decoration: InputDecoration(
                      hintText: 'https://…',
                      prefixIcon: const Icon(Icons.link_rounded, color: C.texto2),
                      suffixIcon: IconButton(
                        tooltip: 'Pegar',
                        icon: const Icon(Icons.content_paste_rounded, color: C.acento),
                        onPressed: _pegar,
                      ),
                    ),
                  ),
                  if (_errorFicha != null)
                    Aparecer(child: Padding(padding: const EdgeInsets.only(top: 8),
                        child: Row(children: [
                          const Icon(Icons.error_outline_rounded, color: C.error, size: 18),
                          const SizedBox(width: 6),
                          Expanded(child: Text(_errorFicha!, style: const TextStyle(color: C.error))),
                        ]))),
                  // la ficha del enlace se abre con suavidad, sin empujar de golpe la lista
                  AnimatedSize(
                    duration: Mov.normal,
                    curve: Mov.curva,
                    alignment: Alignment.topCenter,
                    child: _url.isEmpty
                        ? const SizedBox(width: double.infinity)
                        : Padding(
                            padding: const EdgeInsets.only(top: 14),
                            child: Aparecer(child: _Previa(url: _url, ficha: _ficha, consultando: _consultando,
                                alDescargar: _descargar, alEscuchar: () => _escuchar(false), alVer: () => _escuchar(true))),
                          ),
                  ),
                ]),
              ),
            ),
            if (lista.isNotEmpty)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 18, 8, 4),
                  child: Row(children: [
                    const Expanded(child: Text('Tus descargas', style: estiloTituloSeccion)),
                    if (lista.any((d) => d.terminada))
                      TextButton(onPressed: s.descargas.limpiarTerminadas,
                          child: const Text('Limpiar', style: TextStyle(color: C.texto2))),
                  ]),
                ),
              ),
            if (lista.isEmpty && _url.isEmpty)
              SliverToBoxAdapter(child: Vacio(icono: Icons.download_for_offline_outlined,
                  titulo: 'Nada descargándose',
                  texto: 'También puedes descargar desde el menú ⋮ de cualquier canción, álbum o lista.',
                  textoAccion: 'Pegar un enlace', iconoAccion: Icons.content_paste_rounded, alAccion: _pegar)),
            SliverList.builder(itemCount: lista.length,
                itemBuilder: (_, i) => Entrada(indice: i, desplazamiento: 10, child: _FilaDescarga(d: lista[i]))),
            const SliverToBoxAdapter(child: SizedBox(height: espacioInferior + 10)),
          ]);
        },
      ),
    );
  }
}

/// En iPhone no hay carpeta de Descargas ni de Musica comun: lo bajado vive
/// en la carpeta de Caudal, que la app Archivos muestra.
class _DondeQuedaIOS extends StatelessWidget {
  const _DondeQuedaIOS();

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(top: 10),
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(10)),
        child: const Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(Icons.folder_rounded, size: 20, color: C.acento),
          SizedBox(width: 10),
          Expanded(
            child: Text('Lo que descargues se escucha aquí en Caudal y también aparece en la app Archivos: '
                'En mi iPhone › Caudal › Música o Videos.', style: estiloSecundario),
          ),
        ]),
      );
}

class _Previa extends StatelessWidget {
  const _Previa({required this.url, required this.ficha, required this.consultando, required this.alDescargar,
      required this.alEscuchar, required this.alVer});
  final String url;
  final Ficha? ficha;
  final bool consultando;
  final VoidCallback alDescargar;
  final VoidCallback alEscuchar;
  final VoidCallback alVer;

  @override
  Widget build(BuildContext context) {
    final esYoutube = Catalogo.videoIdDe(url).isNotEmpty;
    final f = ficha;
    final mejor = f == null || f.calidades.isEmpty ? '' : 'hasta ${f.calidades.first.altura}p';
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(12)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Portada(url: f?.miniatura ?? '', lado: 112, alto: 63, radio: 6, icono: Icons.movie_rounded),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(f?.titulo ?? (consultando ? 'Consultando el enlace…' : sitioDe(url)), maxLines: 2,
                overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text([if ((f?.autor ?? '').isNotEmpty) f!.autor, if (mejor.isNotEmpty) mejor,
              if ((f?.duracion ?? 0) > 0) formatoSegundos(f!.duracion)].join(' • '),
                maxLines: 1, style: estiloSecundario),
          ])),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: FilledButton.icon(
            onPressed: alDescargar,
            icon: const Icon(Icons.download_rounded),
            label: const Text('Descargar'),
            style: FilledButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto,
                shape: const StadiumBorder(), padding: const EdgeInsets.symmetric(vertical: 12)),
          )),
          if (esYoutube) ...[
            const SizedBox(width: 8),
            IconButton.filledTonal(onPressed: alEscuchar, icon: const Icon(Icons.headphones_rounded),
                tooltip: 'Escuchar sin descargar'),
            IconButton.filledTonal(onPressed: alVer, icon: const Icon(Icons.smart_display_rounded),
                tooltip: 'Ver sin descargar'),
          ],
        ]),
      ]),
    );
  }
}

class _FilaDescarga extends StatelessWidget {
  const _FilaDescarga({required this.d});
  final Descarga d;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final activa = d.estado.activa;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 6),
      child: Row(children: [
        Portada(url: d.miniatura, lado: 52, radio: 6,
            icono: d.esAudio ? Icons.music_note_rounded : Icons.movie_rounded),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(d.titulo, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 3),
          Text(
            d.estado == EstadoDescarga.error ? d.error : (activa ? d.detalle : d.estado.titulo),
            maxLines: 2, overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 12.5,
                color: d.estado == EstadoDescarga.error ? C.error
                    : d.estado == EstadoDescarga.completada ? C.exito : C.texto2),
          ),
          if (activa) ...[
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              // el avance llega a saltos: la barra se desliza entre uno y otro
              child: d.progreso > 0
                  ? TweenAnimationBuilder<double>(
                      tween: Tween(end: d.progreso / 100),
                      duration: const Duration(milliseconds: 350),
                      curve: Curves.easeOut,
                      builder: (_, v, _) => LinearProgressIndicator(
                        value: v,
                        minHeight: 4,
                        backgroundColor: C.superficie3,
                        valueColor: const AlwaysStoppedAnimation(C.acento),
                      ),
                    )
                  : const LinearProgressIndicator(
                      minHeight: 4,
                      backgroundColor: C.superficie3,
                      valueColor: AlwaysStoppedAnimation(C.acento),
                    ),
            ),
          ],
        ])),
        if (activa)
          IconButton(icon: const Icon(Icons.close_rounded, color: C.texto2), tooltip: 'Cancelar',
              onPressed: () => s.descargas.cancelar(d.id))
        else if (d.estado == EstadoDescarga.error || d.estado == EstadoDescarga.cancelada ||
            d.estado == EstadoDescarga.pausada)
          IconButton(icon: const Icon(Icons.refresh_rounded, color: C.texto2), tooltip: 'Reintentar',
              onPressed: () => s.descargas.reanudar(d.id))
        else if (d.estado == EstadoDescarga.completada)
          IconButton(icon: const Icon(Icons.play_circle_fill_rounded, color: C.acento, size: 30),
              onPressed: () async {
                final todas = await s.coleccion.descargadas();
                final p = todas.where((x) => x['archivo'] == d.archivo).firstOrNull;
                if (p != null && context.mounted) s.reproducirPista(context, p);
              }),
      ]),
    );
  }
}
