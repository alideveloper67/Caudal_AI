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
  final _scroll = ScrollController();
  bool _mostrarTitulo = false;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      final m = _scroll.offset > 260;
      if (m != _mostrarTitulo) setState(() => _mostrarTitulo = m);
    });
    _cargar();
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
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
    final s = Caudal.of(context);
    if (_error != null) {
      return Scaffold(appBar: AppBar(), body: Vacio(icono: Icons.wifi_off_rounded,
          titulo: 'No se pudo abrir el artista', texto: _error!,
          accion: OutlinedButton(onPressed: () {
            setState(() => _error = null);
            _cargar();
          }, child: const Text('Reintentar'))));
    }
    final a = _a;
    if (a == null) return Scaffold(appBar: AppBar(), body: const Esqueleto(filas: true));
    final populares = _populares;
    final secPopulares = _seccionPopulares;
    // el resto, tal cual (si hubiera otras secciones en filas tambien se ven)
    final resto = [
      for (final x in (a['secciones'] is List ? a['secciones'] as List : const []))
        if (x is Map && !identical(x, secPopulares)) x
    ];
    final ancho = MediaQuery.sizeOf(context).width;
    return Scaffold(
      body: CustomScrollView(
        controller: _scroll,
        slivers: [
          SliverAppBar(
            pinned: true,
            stretch: true,
            expandedHeight: ancho * 0.82,
            backgroundColor: Color.lerp(_color, Colors.black, 0.45),
            title: AnimatedOpacity(opacity: _mostrarTitulo ? 1 : 0, duration: const Duration(milliseconds: 180),
                child: Text('${a['titulo']}', maxLines: 1, overflow: TextOverflow.ellipsis)),
            flexibleSpace: FlexibleSpaceBar(
              stretchModes: const [StretchMode.zoomBackground],
              background: Stack(fit: StackFit.expand, children: [
                Portada(url: '${a['foto'] ?? ''}', lado: ancho, alto: ancho * 0.82, radio: 0,
                    icono: Icons.person_rounded),
                const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
                    colors: [Colors.transparent, Color(0xCC000000)], begin: Alignment.center,
                    end: Alignment.bottomCenter))),
                Positioned(
                  left: 16, right: 16, bottom: 14,
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${a['titulo']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 42, fontWeight: FontWeight.w900, height: 1.0,
                            letterSpacing: -1)),
                    if ('${a['subtitulo'] ?? ''}'.isNotEmpty)
                      Padding(padding: const EdgeInsets.only(top: 6),
                          child: Text('${a['subtitulo']}', style: const TextStyle(fontWeight: FontWeight.w600))),
                  ]),
                ),
              ]),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
              child: ListenableBuilder(
                listenable: s.coleccion,
                builder: (_, __) {
                  final seguido = s.coleccion.guardado('artista', widget.id);
                  return Row(children: [
                    OutlinedButton(
                      onPressed: () => s.alternarGuardado(_elemento),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: seguido ? C.acento : C.texto,
                        side: BorderSide(color: seguido ? C.acento : C.texto3),
                        shape: const StadiumBorder(),
                      ),
                      child: Text(seguido ? 'Siguiendo' : 'Seguir'),
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
                      icon: const Icon(Icons.shuffle_rounded, color: C.texto2, size: 28),
                      onPressed: () {
                        final rid = _primero([a['aleatorio_id']]);
                        if (rid.isNotEmpty) {
                          s.reproductor.reproducirRadioId(rid, '${a['titulo']}');
                        } else {
                          s.reproducirLista(context, populares, aleatorio: true,
                              contexto: {'tipo': 'artista', 'id': widget.id, 'titulo': a['titulo']});
                        }
                      },
                    ),
                    const SizedBox(width: 6),
                    BotonPlay(alPulsar: () => s.reproducirLista(context, populares,
                        contexto: {'tipo': 'artista', 'id': widget.id, 'titulo': a['titulo']})),
                  ]);
                },
              ),
            ),
          ),
          if (populares.isNotEmpty) ...[
            const SliverToBoxAdapter(child: Padding(padding: EdgeInsets.only(top: 8), child: TituloSeccion('Populares'))),
            SliverList.builder(
              itemCount: populares.length,
              itemBuilder: (_, i) => FilaPista(
                pista: populares[i],
                numero: i + 1,
                alPulsar: () => s.reproducirLista(context, populares, inicio: i,
                    contexto: {'tipo': 'artista', 'id': widget.id, 'titulo': a['titulo']}),
              ),
            ),
          ],
          SliverList(delegate: SliverChildListDelegate([
            const SizedBox(height: 24),
            ...pintarSecciones(context, resto),
            if ('${a['descripcion'] ?? ''}'.isNotEmpty)
              Padding(
                padding: const EdgeInsets.all(16),
                child: Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(10)),
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
    );
  }
}
