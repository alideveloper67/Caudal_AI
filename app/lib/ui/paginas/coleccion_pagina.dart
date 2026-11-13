import 'package:flutter/material.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/coleccion.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'inicio.dart';

/// Album, lista de YouTube, tu lista, Tus me gusta o lo descargado.
class ColeccionPagina extends StatefulWidget {
  const ColeccionPagina({super.key, required this.elemento});
  final Json elemento;

  @override
  State<ColeccionPagina> createState() => _ColeccionPaginaState();
}

class _ColeccionPaginaState extends State<ColeccionPagina> {
  static final Map<String, Map<String, dynamic>> _cache = {};
  Map<String, dynamic>? _datos;
  List<Json> _pistas = [];
  String? _error;
  Color _color = C.superficie3;
  String _filtro = '';
  final _scroll = ScrollController();
  bool _mostrarTitulo = false;
  Coleccion? _col;
  bool _salido = false;
  int _vuelta = 0;

  String get _tipo => '${widget.elemento['tipo']}';
  int? get _idLista => Servicios.idLista(widget.elemento['id']);
  bool get _local => const ['mi_lista', 'me_gusta', 'descargados'].contains(_tipo);

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      final m = _scroll.offset > 230;
      if (m != _mostrarTitulo) setState(() => _mostrarTitulo = m);
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _col = Caudal.leer(context).coleccion;
      if (_local) _col!.addListener(_cargar);
      _cargar();
    });
  }

  @override
  void dispose() {
    _col?.removeListener(_cargar);
    _scroll.dispose();
    super.dispose();
  }

  /// Sale de la pagina una sola vez (borrar la lista la cierra por dos lados).
  void _salir() {
    if (_salido || !mounted) return;
    _salido = true;
    Navigator.of(context).maybePop();
  }

  Future<void> _cargar() async {
    if (!mounted || _salido) return;
    final col = _col ?? Caudal.leer(context).coleccion;
    // si llegan dos recargas seguidas, solo cuenta la ultima
    final vuelta = ++_vuelta;
    try {
      Map<String, dynamic> d;
      switch (_tipo) {
        case 'me_gusta':
          final p = await col.listaMeGusta();
          d = {'titulo': 'Tus me gusta', 'pistas': p, 'especial': true};
        case 'descargados':
          final solo = widget.elemento['solo'] is bool ? widget.elemento['solo'] as bool : null;
          final p = await col.descargadas(soloAudio: solo);
          d = {'titulo': solo == false ? 'Videos descargados' : 'Música descargada', 'pistas': p,
            'especial': true};
        case 'mi_lista':
          final id = _idLista;
          final l = id == null ? null : await col.lista(id);
          if (id == null || l == null) {
            if (vuelta == _vuelta) _salir();
            return;
          }
          final p = await col.pistasDeLista(id);
          final portadas = await col.portadasDeLista(id, 1);
          d = {'titulo': l['nombre'], 'descripcion': l['descripcion'] ?? '', 'pistas': p,
            'miniatura': portadas.isEmpty ? '' : portadas.first};
        default:
          final clave = '$_tipo|${widget.elemento['id']}';
          d = _cache[clave] ?? Map<String, dynamic>.from(_tipo == 'album'
              ? await Catalogo.album('${widget.elemento['id']}')
              : await Catalogo.lista('${widget.elemento['id']}'));
          _cache[clave] = d;
      }
      if (!mounted || vuelta != _vuelta) return;
      setState(() {
        _datos = d;
        _pistas = [
          for (final e in (d['pistas'] is List ? d['pistas'] as List : const []))
            if (e is Map) Map<String, dynamic>.from(e)
        ];
        _error = null;
      });
      final mini = '${d['miniatura'] ?? ''}';
      if (mini.isNotEmpty) {
        colorDominante(mini).then((c) {
          if (mounted) setState(() => _color = c);
        });
      } else if (d['especial'] == true) {
        setState(() => _color = _tipo == 'me_gusta' ? const Color(0xFF3F2CB8) : const Color(0xFF0E5E73));
      }
    } catch (e) {
      if (mounted && vuelta == _vuelta) setState(() => _error = '$e');
    }
  }

  Json get _contexto => {
        'tipo': _tipo, 'id': widget.elemento['id'] ?? _tipo, 'titulo': _datos?['titulo'],
        'miniatura': _datos?['miniatura'],
      };

  List<Json> get _visibles {
    final f = _filtro.trim().toLowerCase();
    if (f.isEmpty) return _pistas;
    return _pistas.where((p) => '${p['titulo']} ${p['artista']}'.toLowerCase().contains(f)).toList();
  }

  String _duracionTotal() {
    final s = _pistas.fold<int>(0, (a, p) => a + ((p['duracion'] as num?)?.toInt() ?? 0));
    final h = s ~/ 3600, m = (s % 3600) ~/ 60;
    return h > 0 ? '$h h $m min' : '$m min';
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    if (_error != null) {
      return Scaffold(appBar: AppBar(), body: Vacio(icono: Icons.wifi_off_rounded, titulo: 'No se pudo abrir',
          texto: _error!, accion: OutlinedButton(onPressed: _cargar, child: const Text('Reintentar'))));
    }
    final d = _datos;
    if (d == null) return Scaffold(appBar: AppBar(), body: const Esqueleto(filas: true));
    final visibles = _visibles;
    final ancho = MediaQuery.sizeOf(context).width;
    final lado = ancho * 0.58;
    final artistas = [
      for (final e in (d['artistas'] is List ? d['artistas'] as List : const []))
        if (e is Map) Map<String, dynamic>.from(e)
    ];

    return Scaffold(
      body: CustomScrollView(
        controller: _scroll,
        cacheExtent: 900,
        slivers: [
          SliverAppBar(
            pinned: true,
            backgroundColor: Color.lerp(_color, Colors.black, _mostrarTitulo ? 0.4 : 1),
            title: AnimatedOpacity(opacity: _mostrarTitulo ? 1 : 0, duration: const Duration(milliseconds: 180),
                child: Text('${d['titulo']}', maxLines: 1, overflow: TextOverflow.ellipsis)),
            actions: [
              if (_tipo == 'mi_lista')
                IconButton(icon: const Icon(Icons.edit_outlined), onPressed: _editar),
            ],
          ),
          SliverToBoxAdapter(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 500),
              decoration: BoxDecoration(gradient: LinearGradient(
                  colors: [_color, C.fondo], begin: Alignment.topCenter, end: Alignment.bottomCenter)),
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 6),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Center(
                  child: Container(
                    decoration: const BoxDecoration(boxShadow: [
                      BoxShadow(color: Color(0x88000000), blurRadius: 30, offset: Offset(0, 10)),
                    ]),
                    child: _tipo == 'me_gusta'
                        ? PortadaMeGusta(lado: lado, radio: 4)
                        : Portada(url: '${d['miniatura'] ?? ''}', lado: lado, radio: 4,
                            icono: _tipo == 'descargados' ? Icons.download_for_offline_rounded : Icons.queue_music_rounded),
                  ),
                ),
                const SizedBox(height: 18),
                Text('${d['titulo']}', style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w900, height: 1.1)),
                if ('${d['descripcion'] ?? ''}'.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text('${d['descripcion']}', maxLines: 3, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                ],
                const SizedBox(height: 8),
                Wrap(crossAxisAlignment: WrapCrossAlignment.center, spacing: 6, children: [
                  for (final a in artistas)
                    GestureDetector(
                      onTap: '${a['id'] ?? ''}'.isEmpty ? null : () => s.irAArtista(context, '${a['id']}'),
                      child: Text('${a['nombre']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    ),
                  if ('${d['autor'] ?? ''}'.isNotEmpty)
                    Text('${d['autor']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text([
                    if ('${d['tipo_album'] ?? ''}'.isNotEmpty) '${d['tipo_album']}',
                    if ('${d['anio'] ?? ''}'.isNotEmpty) '${d['anio']}',
                    '${_pistas.length} ${_pistas.length == 1 ? 'canción' : 'canciones'}',
                    if (_pistas.isNotEmpty) _duracionTotal(),
                  ].join(' • '), style: estiloSecundario),
                ]),
                const SizedBox(height: 8),
                ListenableBuilder(
                  listenable: Listenable.merge([s.coleccion, s.reproductor]),
                  builder: (_, __) {
                    // dentro del builder: cambia en cuanto termina una descarga
                    final todoDescargado = _pistas.isNotEmpty && _pistas.take(200).every(s.coleccion.estaDescargada);
                    final guardado = !_local && s.coleccion.guardado(_tipo, '${widget.elemento['id']}');
                    final sonandoAqui = s.reproductor.contexto?['tipo'] == _tipo &&
                        '${s.reproductor.contexto?['id']}' == '${widget.elemento['id'] ?? _tipo}' &&
                        s.reproductor.estado.name == 'sonando';
                    return Row(children: [
                      if (!_local)
                        IconButton(
                          icon: Icon(guardado ? Icons.check_circle_rounded : Icons.add_circle_outline_rounded,
                              color: guardado ? C.acento : C.texto2, size: 28),
                          onPressed: () => s.alternarGuardado({
                            'tipo': _tipo, 'id': widget.elemento['id'], 'titulo': d['titulo'],
                            'miniatura': d['miniatura'],
                            'subtitulo': _tipo == 'album'
                                ? '${d['tipo_album'] ?? 'Álbum'} • ${artistas.map((a) => a['nombre']).join(', ')}'
                                : 'Lista${'${d['autor'] ?? ''}'.isEmpty ? '' : ' • ${d['autor']}'}',
                          }),
                        ),
                      IconButton(
                        icon: Icon(todoDescargado ? Icons.download_done_rounded : Icons.download_for_offline_outlined,
                            color: todoDescargado ? C.acento : C.texto2, size: 28),
                        onPressed: _pistas.isEmpty || _tipo == 'descargados' ? null : () {
                          final faltan = _pistas.where((p) => !s.coleccion.estaDescargada(p)).toList();
                          if (faltan.isEmpty) return s.avisar('Ya está todo en tu teléfono');
                          s.hojaDescargar(context, faltan);
                        },
                      ),
                      IconButton(
                        icon: const Icon(Icons.more_vert_rounded, color: C.texto2),
                        onPressed: _menu,
                      ),
                      const Spacer(),
                      IconButton(
                        icon: Icon(Icons.shuffle_rounded, size: 28, color: s.reproductor.aleatorio ? C.acento : C.texto2),
                        onPressed: _pistas.isEmpty ? null
                            : () => s.reproducirLista(context, _pistas, aleatorio: true, contexto: _contexto),
                      ),
                      const SizedBox(width: 4),
                      BotonPlay(
                        sonando: sonandoAqui,
                        alPulsar: () {
                          if (sonandoAqui) {
                            s.reproductor.alternar();
                          } else if (_pistas.isNotEmpty) {
                            s.reproducirLista(context, _pistas, contexto: _contexto, aleatorio: false);
                          }
                        },
                      ),
                    ]);
                  },
                ),
              ]),
            ),
          ),
          if (_pistas.length > 12)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
                child: TextField(
                  onChanged: (t) => setState(() => _filtro = t),
                  decoration: const InputDecoration(hintText: 'Buscar en la lista', isDense: true,
                      prefixIcon: Icon(Icons.search_rounded, color: C.texto3)),
                ),
              ),
            ),
          if (_pistas.isEmpty)
            SliverToBoxAdapter(
              child: Vacio(
                icono: _tipo == 'me_gusta' ? Icons.favorite_border_rounded : Icons.queue_music_rounded,
                titulo: switch (_tipo) {
                  'me_gusta' => 'Las canciones que te gustan aparecen aquí',
                  'descargados' => 'Aún no hay nada descargado',
                  'mi_lista' => 'Tu lista está vacía',
                  _ => 'No hay canciones',
                },
                texto: switch (_tipo) {
                  'me_gusta' => 'Guárdalas tocando el corazón.',
                  'descargados' => 'Descarga canciones o videos y suenan sin internet.',
                  'mi_lista' => 'Busca una canción y, en su menú, «Añadir a una lista».',
                  _ => '',
                },
              ),
            ),
          SliverList.builder(
            itemCount: visibles.length,
            itemBuilder: (_, i) {
              final p = visibles[i];
              return FilaPista(
                pista: p,
                numero: _tipo == 'album' ? i + 1 : null,
                mostrarPortada: _tipo != 'album',
                alPulsar: () => s.reproducirLista(context, visibles, inicio: i, contexto: _contexto),
                extraMenu: [
                  if (_tipo == 'mi_lista')
                    ListTile(
                      leading: const Icon(Icons.remove_circle_outline_rounded, color: C.texto2),
                      title: const Text('Quitar de esta lista'),
                      onTap: () {
                        // el menu esta en el navegador raiz; el de esta pagina es el de la pestana
                        Navigator.of(context, rootNavigator: true).pop();
                        final id = _idLista;
                        if (id != null) s.quitarDeLista(id, p);
                      },
                    ),
                ],
              );
            },
          ),
          const SliverToBoxAdapter(child: SizedBox(height: espacioInferior + 16)),
        ],
      ),
    );
  }

  Future<void> _editar() async {
    final s = Caudal.leer(context);
    final id = _idLista;
    if (id == null) return;
    final nombre = await pedirTexto(context, 'Cambiar el nombre', '${_datos?['titulo'] ?? ''}');
    if (nombre == null) return;
    try {
      await s.coleccion.editarLista(id, nombre: nombre);
    } on FormatException catch (e) {
      s.avisar(e.message);
    }
  }

  Future<void> _menu() async {
    final s = Caudal.leer(context);
    await showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        ListTile(leading: const Icon(Icons.queue_music_rounded, color: C.texto2), title: const Text('Añadir todo a la cola'),
            onTap: () {
              Navigator.pop(ctx);
              s.reproductor.agregarACola(_pistas);
            }),
        if (_tipo != 'mi_lista')
          ListTile(leading: const Icon(Icons.playlist_add_rounded, color: C.texto2), title: const Text('Añadir a una lista'),
              onTap: () {
                Navigator.pop(ctx);
                s.anadirALista(context, _pistas);
              }),
        if (_tipo == 'album' && '${_datos?['lista_id'] ?? ''}'.isNotEmpty)
          ListTile(leading: const Icon(Icons.radio_rounded, color: C.texto2), title: const Text('Radio del álbum'),
              onTap: () {
                Navigator.pop(ctx);
                s.reproductor.reproducirRadioId('RDAMPL${_datos!['lista_id']}', 'Radio de ${_datos!['titulo']}');
              }),
        if (_tipo == 'mi_lista') ...[
          ListTile(leading: const Icon(Icons.push_pin_outlined, color: C.texto2), title: const Text('Fijar arriba / desfijar'),
              onTap: () async {
                Navigator.pop(ctx);
                final id = _idLista;
                if (id == null) return;
                final l = await s.coleccion.lista(id);
                await s.coleccion.editarLista(id, fijada: (l?['fijada'] ?? 0) != 1);
              }),
          ListTile(leading: const Icon(Icons.edit_outlined, color: C.texto2), title: const Text('Cambiar el nombre'),
              onTap: () {
                Navigator.pop(ctx);
                _editar();
              }),
          ListTile(leading: const Icon(Icons.delete_outline_rounded, color: C.error),
              title: const Text('Borrar la lista', style: TextStyle(color: C.error)),
              onTap: () async {
                Navigator.pop(ctx);
                final ok = await confirmar(context, 'Borrar la lista',
                    '¿Borrar «${_datos?['titulo']}»? Las canciones no se borran del teléfono.');
                final id = _idLista;
                if (ok && id != null) {
                  await s.coleccion.borrarLista(id);
                  _salir();
                }
              }),
        ],
        const SizedBox(height: 8),
      ])),
    );
  }
}
