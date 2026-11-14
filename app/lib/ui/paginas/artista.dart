import 'package:flutter/material.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/coleccion.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'inicio.dart';

class ArtistaPagina extends StatefulWidget {
  const ArtistaPagina({super.key, required this.id});
  final String id;

  @override
  State<ArtistaPagina> createState() => _ArtistaPaginaState();
}

class _ArtistaPaginaState extends State<ArtistaPagina> {
  static final Map<String, Map<String, dynamic>> _cache = {};
  Map<String, dynamic>? _a;
  String? _error;
  Color _color = C.superficie3;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    final hecho = _cache[widget.id];
    if (hecho != null) return _poner(hecho);
    try {
      final a = Map<String, dynamic>.from(await Catalogo.artista(widget.id));
      _cache[widget.id] = a;
      _poner(a);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  void _poner(Map<String, dynamic> a) {
    if (!mounted) return;
    setState(() => _a = a);
    colorDominante('${a['foto'] ?? ''}').then((c) {
      if (mounted) setState(() => _color = c);
    });
  }

  Json get _elemento => {'tipo': 'artista', 'id': widget.id, 'titulo': _a?['titulo'] ?? '',
    'miniatura': _a?['foto'] ?? '', 'subtitulo': 'Artista'};

  /// La primera seccion en filas con canciones (las "Populares").
  Map? get _seccionPopulares {
    for (final sec in (_a?['secciones'] is List ? _a!['secciones'] as List : const [])) {
      if (sec is Map && sec['estilo'] == 'filas' &&
          (sec['elementos'] is List) && (sec['elementos'] as List).any((e) => e is Map && e['tipo'] == 'pista')) {
        return sec;
      }
    }
    return null;
  }

  List<Json> get _populares => [
        for (final e in (_seccionPopulares?['elementos'] as List? ?? const []))
          if (e is Map && e['tipo'] == 'pista') Map<String, dynamic>.from(e)
      ];

  /// El primer id de la lista que no este vacio (el catalogo da '' y no null).
  static String _primero(List<Object?> ids) =>
      ids.map((x) => '${x ?? ''}').firstWhere((x) => x.isNotEmpty, orElse: () => '');

  @override
  Widget build(BuildContext context) {
    final a = _a;
    final Widget pagina;
    final String estado;
    if (_error != null) {
      estado = 'error';
      pagina = Scaffold(appBar: AppBar(), body: Vacio(icono: Icons.wifi_off_rounded, error: true,
          titulo: 'No se pudo abrir el artista', texto: explicarError(_error),
          alAccion: () {
            setState(() => _error = null);
            _cargar();
          }));
    } else if (a == null) {
      estado = 'cargando';
      // el esqueleto ocupa lo mismo que la pagina, foto incluida
      pagina = Scaffold(extendBodyBehindAppBar: true,
          appBar: AppBar(backgroundColor: Colors.transparent),
          body: const Esqueleto(forma: FormaEsqueleto.artista));
    } else {
      estado = 'listo';
      pagina = _pagina(context, a);
    }
    return AnimatedSwitcher(duration: Mov.normal, child: KeyedSubtree(key: ValueKey(estado), child: pagina));
  }

  Widget _pagina(BuildContext context, Map<String, dynamic> a) {
    final s = Caudal.of(context);
    final populares = _populares;
    final secPopulares = _seccionPopulares;
    // el resto, tal cual (si hubiera otras secciones en filas tambien se ven)
    final resto = [
      for (final x in (a['secciones'] is List ? a['secciones'] as List : const []))
        if (x is Map && !identical(x, secPopulares)) x
    ];
    final ancho = MediaQuery.sizeOf(context).width;
    final arriba = MediaQuery.paddingOf(context).top;
    final contexto = {'tipo': 'artista', 'id': widget.id, 'titulo': a['titulo']};
    return Scaffold(
      body: Escalonado(
        child: CustomScrollView(
          cacheExtent: 900,
          slivers: [
            CabeceraPlegable(
              titulo: '${a['titulo']}',
              color: _color,
              alto: ancho * 0.82,
              fondo: Stack(fit: StackFit.expand, children: [
                Portada(url: '${a['foto'] ?? ''}', lado: ancho, alto: ancho * 0.82 + arriba, radio: 0,
                    icono: Icons.person_rounded),
                const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
                    colors: [Colors.transparent, Color(0xCC000000)], begin: Alignment.center,
                    end: Alignment.bottomCenter))),
                Positioned(
                  left: Esp.lado, right: Esp.lado, bottom: 14,
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${a['titulo']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 42, fontWeight: FontWeight.w900, height: 1.0,
                            letterSpacing: -1, shadows: [Shadow(color: Color(0x66000000), blurRadius: 12)])),
                    if ('${a['subtitulo'] ?? ''}'.isNotEmpty)
                      Padding(padding: const EdgeInsets.only(top: 6),
                          child: Text('${a['subtitulo']}', style: const TextStyle(fontWeight: FontWeight.w600))),
                  ]),
                ),
              ]),
            ),
            SliverToBoxAdapter(
              child: Entrada(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(Esp.lado, 14, Esp.lado, Esp.s),
                  child: ListenableBuilder(
                    listenable: s.coleccion,
                    builder: (_, _) {
                      final seguido = s.coleccion.guardado('artista', widget.id);
                      return Row(children: [
                        Pulsable(
                          escala: 0.94,
                          child: OutlinedButton(
                            onPressed: () => s.alternarGuardado(_elemento),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: seguido ? C.acento : C.texto,
                              side: BorderSide(color: seguido ? C.acento : C.texto3),
                              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                            ),
                            child: AnimatedSwitcher(
                              duration: Mov.rapido,
                              child: Text(seguido ? 'Siguiendo' : 'Seguir', key: ValueKey(seguido)),
                            ),
                          ),
                        ),
                        IconButton(
                          tooltip: 'Radio del artista',
                          icon: const Icon(Icons.radio_rounded, color: C.texto2),
                          onPressed: () {
                            final rid = _primero([a['radio_id'], a['aleatorio_id']]);
                            if (rid.isNotEmpty) {
                              s.reproductor.reproducirRadioId(rid, 'Radio de ${a['titulo']}');
                            } else if (populares.isNotEmpty) {
                              s.reproductor.iniciarRadio(populares.first);
                            }
                          },
                        ),
                        const Spacer(),
                        IconButton(
                          tooltip: 'Aleatorio',
                          icon: const Icon(Icons.shuffle_rounded, color: C.texto2, size: 28),
                          onPressed: () {
                            final rid = _primero([a['aleatorio_id']]);
                            if (rid.isNotEmpty) {
                              s.reproductor.reproducirRadioId(rid, '${a['titulo']}');
                            } else {
                              s.reproducirLista(context, populares, aleatorio: true, contexto: contexto);
                            }
                          },
                        ),
                        const SizedBox(width: 6),
                        BotonPlay(alPulsar: () => s.reproducirLista(context, populares, contexto: contexto)),
                      ]);
                    },
                  ),
                ),
              ),
            ),
            if (populares.isNotEmpty) ...[
              const SliverToBoxAdapter(child: Entrada(indice: 1,
                  child: Padding(padding: EdgeInsets.only(top: Esp.s), child: TituloSeccion('Populares')))),
              SliverList.builder(
                itemCount: populares.length,
                itemBuilder: (_, i) => Entrada(
                  indice: 2 + i,
                  child: FilaPista(
                    pista: populares[i],
                    numero: i + 1,
                    alPulsar: () => s.reproducirLista(context, populares, inicio: i, contexto: contexto),
                  ),
                ),
              ),
            ],
            SliverList(delegate: SliverChildListDelegate([
              const SizedBox(height: Esp.xl),
              ...pintarSecciones(context, resto, desde: 4),
              if ('${a['descripcion'] ?? ''}'.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.all(Esp.lado),
                  child: Container(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(12)),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      const Text('Información', style: estiloTituloSeccion),
                      const SizedBox(height: 10),
                      Text('${a['descripcion']}', style: const TextStyle(color: C.texto2, height: 1.45)),
                    ]),
                  ),
                ),
              const SizedBox(height: espacioInferior),
            ])),
          ],
        ),
      ),
    );
  }
}
