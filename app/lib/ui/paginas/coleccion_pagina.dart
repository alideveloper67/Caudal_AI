import 'package:flutter/material.dart';

import '../../nucleo/recomendador.dart';
import '../../nucleo/catalogo.dart';
import '../../nucleo/coleccion.dart';
import '../../nucleo/listas_compartidas.dart';
import '../comunes.dart';
import '../hoja_portada.dart';
import '../servicios.dart';
import '../tema.dart';
import 'enriquecer_hoja.dart';
import 'inicio.dart';
import 'lista_compartir.dart';
import 'lista_privacidad_hoja.dart';

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
  Coleccion? _col;
  bool _salido = false;
  int _vuelta = 0;

  String get _tipo => '${widget.elemento['tipo']}';
  int? get _idLista => Servicios.idLista(widget.elemento['id']);
  bool get _local => const ['mi_lista', 'me_gusta', 'descargados', 'mix'].contains(_tipo);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _col = Caudal.leer(context).coleccion;
      if (_local) _col!.addListener(_cargar);
      _cargar();
      if (_tipo == 'mi_lista') _refrescarSiCompartida();
    });
  }

  @override
  void dispose() {
    _col?.removeListener(_cargar);
    super.dispose();
  }

  /// Si esta lista propia ya se compartio, otras personas pudieron anadir
  /// canciones: se baja lo de la nube al abrirla.
  Future<void> _refrescarSiCompartida() async {
    final s = Caudal.leer(context);
    final id = _idLista;
    final sinc = s.sincronizador;
    if (id == null || sinc == null) return;
    try {
      final l = await s.coleccion.lista(id);
      final uuid = '${l?['uuid'] ?? ''}';
      if (uuid.isEmpty) return;
      final r = await ListasQueComparto.cargar(s.cuenta.id);
      if (r.estaCompartida(uuid)) await sinc.refrescarAhora();
    } catch (_) {}
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
        case 'mix':
          // un mix diario ya trae sus canciones: no se pide nada a internet
          d = Map<String, dynamic>.from(widget.elemento);
        case 'similares':
          final pista = widget.elemento['pista'] is Map
              ? Map<String, dynamic>.from(widget.elemento['pista'] as Map)
              : <String, dynamic>{};
          final clave = 'similares|${widget.elemento['id']}';
          d = _cache[clave] ?? await Recomendador.similares(col, pista);
          _cache[clave] = d;
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
      // Nada cambió en esta pantalla (otro «me gusta», una descarga que avanza...): no se rehace.
      // Si solo se añadieron canciones, aparecen al final sin mover la vista.
      if (_datos != null && _error == null && mismaColeccion(_datos!, d)) return;
      final miniAntes = '${_datos?['miniatura'] ?? ''}';
      setState(() {
        _datos = d;
        _pistas = [
          for (final e in (d['pistas'] is List ? d['pistas'] as List : const []))
            if (e is Map) Map<String, dynamic>.from(e)
        ];
        _error = null;
      });
      final mini = '${d['miniatura'] ?? ''}';
      if (mini.isNotEmpty && mini == miniAntes) {
        // la misma portada: el color de la cabecera ya está (no vuelve a parpadear)
      } else if (mini.isNotEmpty) {
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
    final d = _datos;
    final Widget pagina;
    final String estado;
    if (_error != null) {
      estado = 'error';
      pagina = Scaffold(appBar: AppBar(), body: Vacio(icono: Icons.wifi_off_rounded, titulo: 'No se pudo abrir',
          error: true, texto: explicarError(_error), alAccion: _cargar));
    } else if (d == null) {
      estado = 'cargando';
      // con la misma forma que la pagina: portada, titulo, botones y canciones
      pagina = Scaffold(extendBodyBehindAppBar: true,
          appBar: AppBar(backgroundColor: Colors.transparent),
          body: const Esqueleto(forma: FormaEsqueleto.coleccion));
    } else {
      estado = 'listo';
      pagina = _pagina(context, d);
    }
    return AnimatedSwitcher(duration: Mov.normal, child: KeyedSubtree(key: ValueKey(estado), child: pagina));
  }

  Widget _pagina(BuildContext context, Map<String, dynamic> d) {
    final s = Caudal.of(context);
    final visibles = _visibles;
    final ancho = MediaQuery.sizeOf(context).width;
    final lado = ancho * 0.58;
    final artistas = [
      for (final e in (d['artistas'] is List ? d['artistas'] as List : const []))
        if (e is Map) Map<String, dynamic>.from(e)
    ];

    return Scaffold(
      body: Escalonado(
        child: CustomScrollView(
        cacheExtent: 900,
        slivers: [
          CabeceraPlegable(
            titulo: '${d['titulo']}',
            color: _color,
            degradado: true,
            alto: kToolbarHeight + 8 + lado + 8,
            acciones: [
              if (_tipo == 'mi_lista')
                IconButton(tooltip: 'Cambiar el nombre', icon: const Icon(Icons.edit_outlined), onPressed: _editar),
            ],
            fondo: Align(
              alignment: Alignment.bottomCenter,
              child: Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: PortadaPlegable(
                  child: Container(
                    decoration: const BoxDecoration(boxShadow: [
                      BoxShadow(color: Color(0x88000000), blurRadius: 30, offset: Offset(0, 10)),
                    ]),
                    child: _tipo == 'me_gusta'
                        ? PortadaMeGusta(lado: lado, radio: 4)
                        : _tipo == 'mi_lista'
                            ? Stack(children: [
                                Portada(url: '${d['miniatura'] ?? ''}', lado: lado, radio: 4,
                                    icono: Icons.queue_music_rounded),
                                Positioned(right: 6, bottom: 6, child: Material(
                                  color: const Color(0xB3000000),
                                  shape: const CircleBorder(),
                                  child: IconButton(
                                    tooltip: 'Cambiar portada',
                                    visualDensity: VisualDensity.compact,
                                    icon: const Icon(Icons.photo_camera_outlined, size: 18, color: Colors.white),
                                    onPressed: _cambiarPortada,
                                  ),
                                )),
                              ])
                            : Portada(url: '${d['miniatura'] ?? ''}', lado: lado, radio: 4,
                                icono: _tipo == 'descargados' ? Icons.download_for_offline_rounded : Icons.queue_music_rounded),
                  ),
                ),
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: AnimatedContainer(
              duration: Mov.color,
              curve: Mov.curva,
              decoration: BoxDecoration(gradient: LinearGradient(
                  colors: [CabeceraPlegable.colorMedio(_color), C.fondo],
                  begin: Alignment.topCenter, end: Alignment.bottomCenter)),
              padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, 6),
              child: Entrada(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${d['titulo']}', style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w900, height: 1.1,
                    letterSpacing: -0.4)),
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
                  builder: (_, _) {
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
                      if (_tipo == 'mi_lista')
                        IconButton(
                          tooltip: 'Enriquecer',
                          icon: const Icon(Icons.auto_awesome_rounded, color: C.texto2, size: 26),
                          onPressed: _enriquecer,
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
              ])),
            ),
          ),
          if (_pistas.length > 12)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
                child: TextField(
                  onChanged: (t) => setState(() => _filtro = t),
                  decoration: InputDecoration(hintText: 'Buscar en la lista', isDense: true,
                      prefixIcon: const Icon(Icons.search_rounded, color: C.texto3),
                      suffixIcon: _filtro.isEmpty ? null : Icon(Icons.filter_list_rounded, color: C.acento)),
                ),
              ),
            ),
          if (_pistas.isNotEmpty && visibles.isEmpty)
            SliverToBoxAdapter(
              child: Vacio(icono: Icons.search_off_rounded, titulo: 'Nada con «${_filtro.trim()}»',
                  texto: 'Ninguna canción de aquí coincide con lo que escribiste.'),
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
                textoAccion: switch (_tipo) {
                  'descargados' => 'Descargar un enlace',
                  'me_gusta' || 'mi_lista' => 'Buscar canciones',
                  _ => null,
                },
                iconoAccion: _tipo == 'descargados' ? Icons.link_rounded : Icons.search_rounded,
                alAccion: switch (_tipo) {
                  'descargados' => () => s.irAPestana?.call(3),
                  'me_gusta' || 'mi_lista' => () => s.irAPestana?.call(1),
                  _ => null,
                },
              ),
            ),
          SliverList.builder(
            itemCount: visibles.length,
            itemBuilder: (_, i) {
              final p = visibles[i];
              return Entrada(indice: 1 + i, desplazamiento: 10, child: FilaPista(
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
              ));
            },
          ),
          const SliverToBoxAdapter(child: SizedBox(height: espacioInferior + 16)),
        ],
      ),
      ),
    );
  }

  void _enriquecer() {
    final id = _idLista;
    if (id == null) return;
    if (_pistas.isEmpty) {
      Caudal.leer(context).avisar('Añade primero algunas canciones y así sabré qué sugerirte');
      return;
    }
    mostrarHojaEnriquecer(context, listaId: id, nombre: '${_datos?['titulo'] ?? 'tu lista'}',
        pistas: List.of(_pistas));
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

  Future<void> _cambiarPortada() async {
    final id = _idLista;
    if (id == null) return;
    final s = Caudal.leer(context);
    final jpeg = await mostrarHojaPortada(context, actual: '${_datos?['miniatura'] ?? ''}');
    if (jpeg == null) return;
    try {
      await s.coleccion.ponerPortadaLista(id, jpeg);
      s.avisar('Portada actualizada');
      if (mounted) _cargar();
    } catch (_) {
      s.avisar('No se pudo guardar la portada. Prueba con otra imagen.');
    }
  }

  Future<void> _quitarPortada() async {
    final id = _idLista;
    if (id == null) return;
    final s = Caudal.leer(context);
    await s.coleccion.quitarPortadaLista(id);
    s.avisar('Portada quitada');
    if (mounted) _cargar();
  }

  Future<void> _menu() async {
    final s = Caudal.leer(context);
    final idPropia = _tipo == 'mi_lista' ? _idLista : null;
    final tienePropia = idPropia != null && (await s.coleccion.portadaPersonalizada(idPropia)).isNotEmpty;
    if (!mounted) return;
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
          ListTile(leading: const Icon(Icons.auto_awesome_rounded, color: C.texto2), title: const Text('Enriquecer'),
              subtitle: const Text('Sugiere canciones nuevas parecidas a las de esta lista'),
              onTap: () {
                Navigator.pop(ctx);
                _enriquecer();
              }),
          ListTile(leading: const Icon(Icons.push_pin_outlined, color: C.texto2), title: const Text('Fijar arriba / desfijar'),
              onTap: () async {
                Navigator.pop(ctx);
                final id = _idLista;
                if (id == null) return;
                final l = await s.coleccion.lista(id);
                await s.coleccion.editarLista(id, fijada: (l?['fijada'] ?? 0) != 1);
              }),
          ListTile(leading: const Icon(Icons.ios_share_rounded, color: C.texto2), title: const Text('Compartir lista'),
              onTap: () {
                Navigator.pop(ctx);
                final id = _idLista;
                if (id != null) hojaCompartirLista(context, id: id);
              }),
          ListTile(leading: const Icon(Icons.public_rounded, color: C.texto2), title: const Text('Quién puede verla'),
              subtitle: const Text('Pública o privada, y mostrarla en tu perfil'),
              onTap: () {
                Navigator.pop(ctx);
                final id = _idLista;
                if (id != null) mostrarHojaPrivacidadLista(context, id);
              }),
          ListTile(leading: const Icon(Icons.edit_outlined, color: C.texto2), title: const Text('Cambiar el nombre'),
              onTap: () {
                Navigator.pop(ctx);
                _editar();
              }),
          ListTile(leading: const Icon(Icons.photo_camera_outlined, color: C.texto2), title: const Text('Cambiar portada'),
              onTap: () {
                Navigator.pop(ctx);
                _cambiarPortada();
              }),
          if (tienePropia)
            ListTile(leading: const Icon(Icons.hide_image_outlined, color: C.texto2),
                title: const Text('Quitar portada personalizada'),
                onTap: () {
                  Navigator.pop(ctx);
                  _quitarPortada();
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

/// ¿Los datos nuevos de una colección enseñan lo mismo que los que ya se ven? (mismo título,
/// descripción, portada y las mismas canciones en el mismo orden)
bool mismaColeccion(Map<String, dynamic> a, Map<String, dynamic> b) {
  for (final k in const ['titulo', 'descripcion', 'miniatura']) {
    if ('${a[k] ?? ''}' != '${b[k] ?? ''}') return false;
  }
  List<String> claves(Map<String, dynamic> d) => [
        for (final e in (d['pistas'] is List ? d['pistas'] as List : const []))
          if (e is Map) '${e['clave'] ?? e['video_id'] ?? e['archivo'] ?? ''}|${e['titulo'] ?? ''}'
      ];
  final x = claves(a), y = claves(b);
  if (x.length != y.length) return false;
  for (var i = 0; i < x.length; i++) {
    if (x[i] != y[i]) return false;
  }
  return true;
}
