import 'package:flutter/material.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/coleccion.dart';
import '../comunes.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';
import 'ajustes_pagina.dart';

const espacioInferior = 84.0;

class InicioPagina extends StatefulWidget {
  const InicioPagina({super.key});

  @override
  State<InicioPagina> createState() => _InicioPaginaState();
}

class _InicioPaginaState extends State<InicioPagina> with AutomaticKeepAliveClientMixin {
  static Map<String, dynamic>? _cacheCatalogo;
  static DateTime _cuando = DateTime(2000);

  String _filtro = 'todo';
  Map<String, dynamic>? _catalogo = _cacheCatalogo;
  bool _sinRed = false;
  List<Json> _recientes = [];
  List<Json> _atajos = [];
  List<Json> _mixes = [];
  List<Json> _enTelefono = [];

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
  }

  Future<void> _cargar({bool forzar = false}) async {
    if (!mounted) return;
    final s = Caudal.leer(context);
    final col = s.coleccion;
    final recientes = await col.escuchadoHacePoco(24);
    final atajos = <Json>[{'tipo': 'me_gusta', 'titulo': 'Tus me gusta'}];
    final vistos = <String>{};
    for (final c in await col.contextosRecientes(14)) {
      final clave = '${c['tipo']}|${c['id']}';
      if (vistos.contains(clave) || !const ['album', 'lista', 'mi_lista', 'radio', 'artista'].contains(c['tipo'])) {
        continue;
      }
      vistos.add(clave);
      atajos.add(Map<String, dynamic>.from(c));
    }
    for (final l in await col.listas()) {
      if (atajos.length >= 8) break;
      final id = Servicios.idLista(l['id']);
      if (id != null && vistos.add('mi_lista|$id')) {
        final portadas = await col.portadasDeLista(id, 1);
        atajos.add({'tipo': 'mi_lista', 'id': l['id'], 'titulo': l['nombre'],
          'miniatura': portadas.isEmpty ? '' : portadas.first});
      }
    }
    final mixes = [
      for (final a in await col.artistasFrecuentes(8))
        {'tipo': 'artista', 'id': a['id'], 'titulo': 'Mix de ${a['nombre']}',
         'subtitulo': '${a['nombre']} y artistas parecidos', 'miniatura': a['miniatura']}
    ];
    final enTelefono = await col.descargadas();
    if (!mounted) return;
    setState(() {
      _recientes = recientes;
      _atajos = atajos.take(8).toList();
      _mixes = mixes;
      _enTelefono = enTelefono;
    });
    if (forzar || _catalogo == null || DateTime.now().difference(_cuando) > const Duration(minutes: 15)) {
      try {
        final datos = await Catalogo.inicio();
        _cacheCatalogo = datos;
        _cuando = DateTime.now();
        if (mounted) setState(() {
          _catalogo = datos;
          _sinRed = false;
        });
      } catch (_) {
        if (mounted) setState(() => _sinRed = _catalogo == null);
      }
    }
  }

  String _saludo() {
    final h = DateTime.now().hour;
    if (h >= 5 && h < 12) return 'Buenos días';
    if (h >= 12 && h < 19) return 'Buenas tardes';
    return 'Buenas noches';
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final s = Caudal.of(context);
    final nombre = s.cuenta.nombre.split(' ').first;
    final secciones = (_catalogo?['secciones'] as List? ?? const []).whereType<Map>().where((sec) {
      final els = sec['elementos'] as List? ?? [];
      final todosVideo = els.isNotEmpty && els.every((e) => (e as Map)['tipo'] == 'pista' && e['es_video'] == true);
      return switch (_filtro) {
        'musica' => !todosVideo,
        'videos' => els.any((e) => (e as Map)['es_video'] == true),
        _ => true,
      };
    }).toList();
    if (_filtro == 'videos') {
      for (var i = 0; i < secciones.length; i++) {
        final sec = Map<String, dynamic>.from(secciones[i]);
        sec['elementos'] = (sec['elementos'] as List).where((e) => (e as Map)['es_video'] == true).toList();
        sec['estilo'] = 'carrusel';
        secciones[i] = sec;
      }
    }

    return Scaffold(
      body: RefreshIndicator.adaptive(
        color: C.acento,
        onRefresh: () {
          Haptico.firme();
          return _cargar(forzar: true);
        },
        child: CustomScrollView(
          cacheExtent: 800,
          slivers: [
            SliverToBoxAdapter(
              child: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(colors: [Color(0xFF16324A), C.fondo],
                      begin: Alignment.topCenter, end: Alignment.bottomCenter),
                ),
                padding: EdgeInsets.fromLTRB(16, MediaQuery.paddingOf(context).top + 12, 16, 8),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    GestureDetector(
                      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AjustesPagina())),
                      child: CircleAvatar(
                        radius: 17, backgroundColor: C.acento,
                        child: Text(s.cuenta.inicial,
                            style: const TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900)),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(child: Text(nombre.isEmpty ? _saludo() : '${_saludo()}, $nombre',
                        style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w900), maxLines: 1,
                        overflow: TextOverflow.ellipsis)),
                    IconButton(
                      icon: const Icon(Icons.settings_outlined),
                      onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AjustesPagina())),
                    ),
                  ]),
                  const SizedBox(height: 14),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(children: [
                      for (final (clave, texto) in const [('todo', 'Todo'), ('musica', 'Música'),
                        ('videos', 'Videos'), ('telefono', 'En tu teléfono')])
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: ChoiceChip(
                            label: Text(texto),
                            selected: _filtro == clave,
                            onSelected: (_) => setState(() => _filtro = clave),
                            showCheckmark: false,
                            selectedColor: C.acento,
                            labelStyle: TextStyle(fontWeight: FontWeight.w600,
                                color: _filtro == clave ? C.acentoTexto : C.texto),
                            backgroundColor: C.superficie2,
                            side: BorderSide.none,
                            shape: const StadiumBorder(),
                          ),
                        ),
                    ]),
                  ),
                ]),
              ),
            ),
            if (_filtro != 'telefono' && _filtro != 'videos' && _atajos.length > 1)
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 6, 16, 20),
                sliver: SliverGrid(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2, mainAxisSpacing: 8, crossAxisSpacing: 8, mainAxisExtent: 56),
                  delegate: SliverChildBuilderDelegate(
                    (_, i) => _Atajo(el: _atajos[i]),
                    childCount: _atajos.length,
                  ),
                ),
              ),
            SliverList(
              delegate: SliverChildListDelegate([
                if (_filtro == 'telefono') ...[
                  if (_enTelefono.isEmpty)
                    const Vacio(icono: Icons.download_for_offline_outlined, titulo: 'Aún no hay nada en tu teléfono',
                        texto: 'Descarga canciones, álbumes o videos y suenan sin internet.')
                  else ...[
                    // sin titulos de carruseles vacios (solo musica o solo videos)
                    for (final (titulo, audio) in const [('Tu música descargada', true), ('Tus videos descargados', false)])
                      if (_enTelefono.any((p) => (p['es_audio'] == true) == audio)) ...[
                        Carrusel(titulo: titulo,
                            elementos: _enTelefono.where((p) => (p['es_audio'] == true) == audio).toList()),
                        const SizedBox(height: 26),
                      ],
                  ],
                ] else ...[
                  if (_filtro != 'videos' && _recientes.isNotEmpty) ...[
                    Carrusel(titulo: 'Volver a escuchar', elementos: _recientes),
                    const SizedBox(height: 26),
                  ],
                  if (_filtro == 'todo' && _mixes.isNotEmpty) ...[
                    Carrusel(titulo: 'Tus mixes', elementos: _mixes),
                    const SizedBox(height: 26),
                  ],
                  if (_catalogo == null && !_sinRed) const Esqueleto(),
                  if (_sinRed)
                    Vacio(icono: Icons.wifi_off_rounded, titulo: 'Sin conexión',
                        texto: 'Mientras vuelve, tienes lo descargado en «En tu teléfono».',
                        accion: OutlinedButton(onPressed: () => _cargar(forzar: true), child: const Text('Reintentar'))),
                  ...pintarSecciones(context, secciones),
                ],
                const SizedBox(height: espacioInferior),
              ]),
            ),
          ],
        ),
      ),
    );
  }
}

class _Atajo extends StatelessWidget {
  const _Atajo({required this.el});
  final Json el;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    return Material(
      color: C.superficie2,
      borderRadius: BorderRadius.circular(6),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => el['tipo'] == 'radio'
            ? s.reproductor.reproducirRadioId('${el['id']}', '${el['titulo']}')
            : s.abrirElemento(context, el),
        onLongPress: () => s.reproducirElemento(context, el),
        child: Row(children: [
          el['tipo'] == 'me_gusta'
              ? const PortadaMeGusta(lado: 56, radio: 0)
              : Portada(url: '${el['miniatura'] ?? ''}', lado: 56, radio: 0),
          const SizedBox(width: 10),
          Expanded(
            child: Text('${el['titulo'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
          ),
          const SizedBox(width: 6),
        ]),
      ),
    );
  }
}
