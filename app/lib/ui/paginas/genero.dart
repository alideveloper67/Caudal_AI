import 'package:flutter/material.dart';

import '../../nucleo/catalogo.dart';
import '../comunes.dart';
import '../tema.dart';
import 'inicio.dart';

/// Cualquier pagina de YouTube Music: un genero, un estado de animo o un "Ver todo".
class GeneroPagina extends StatefulWidget {
  const GeneroPagina({super.key, required this.id, this.params, this.titulo = ''});
  final String id;
  final String? params;
  final String titulo;

  @override
  State<GeneroPagina> createState() => _GeneroPaginaState();
}

class _GeneroPaginaState extends State<GeneroPagina> {
  static final Map<String, Map<String, dynamic>> _cache = {};
  Map<String, dynamic>? _datos;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    final clave = '${widget.id}|${widget.params}';
    if (_error != null) setState(() => _error = null);
    try {
      final d = _cache[clave] ?? Map<String, dynamic>.from(await Catalogo.pagina(widget.id, params: widget.params));
      _cache[clave] = d;
      if (mounted) setState(() => _datos = d);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = _datos;
    final titulo = '${d?['titulo'] ?? ''}'.isNotEmpty ? '${d!['titulo']}' : widget.titulo;
    var secciones = (d?['secciones'] is List ? d!['secciones'] as List : const []).whereType<Map>().toList();
    if (secciones.length == 1 && secciones.first['estilo'] == 'carrusel') {
      secciones = [{...Map<String, dynamic>.from(secciones.first), 'estilo': 'rejilla'}];
    }
    return Scaffold(
      appBar: AppBar(title: Text(titulo, maxLines: 1, overflow: TextOverflow.ellipsis)),
      body: AnimatedSwitcher(
        duration: Mov.normal,
        layoutBuilder: (actual, previos) => Stack(alignment: Alignment.topCenter, children: [...previos, ?actual]),
        child: _error != null
            ? Vacio(key: const ValueKey('error'), icono: Icons.wifi_off_rounded, titulo: 'No se pudo abrir',
                error: true, texto: explicarError(_error), alAccion: _cargar)
            : d == null
                ? const Padding(key: ValueKey('cargando'), padding: EdgeInsets.only(top: 8), child: Esqueleto())
                : secciones.isEmpty
                    ? Vacio(key: const ValueKey('vacio'), icono: Icons.library_music_outlined,
                        titulo: 'Aquí no hay nada por ahora',
                        texto: 'YouTube Music no tiene contenido para esta sección en tu país.',
                        textoAccion: 'Volver', iconoAccion: Icons.arrow_back_rounded,
                        alAccion: () => Navigator.of(context).maybePop())
                    : Escalonado(
                    key: const ValueKey('listo'),
                    child: ListView(
                      key: PageStorageKey('genero|${widget.id}|${widget.params}'),
                      cacheExtent: 800,
                      padding: const EdgeInsets.only(top: 8, bottom: espacioInferior),
                      children: pintarSecciones(context, secciones),
                    ),
                  ),
      ),
      backgroundColor: C.fondoVivo,
    );
  }
}
