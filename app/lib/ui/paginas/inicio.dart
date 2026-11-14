import 'package:flutter/material.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/coleccion.dart';
import '../comunes.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';
import 'ajustes_pagina.dart';
import 'juntos_pagina.dart';
import 'resumen.dart';

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
  // hasta que llega lo de este telefono se ve su esqueleto (y nada salta luego)
  bool _localListo = false;
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
      _localListo = true;
      _recientes = recientes;
      _atajos = atajos.take(8).toList();
      _mixes = mixes;
      _enTelefono = enTelefono;
    });
    if (forzar || _catalogo == null || DateTime.now().difference(_cuando) > const Duration(minutes: 15)) {
      try {
        Json datos;
        try {
          datos = await Catalogo.inicio();
        } catch (_) {
          await Future<void>.delayed(const Duration(seconds: 3));
          if (!mounted) return;
          datos = await Catalogo.inicio();
        }
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

    final verAtajos = _filtro != 'telefono' && _filtro != 'videos';
    // turnos de entrada: lo de arriba primero, el catalogo despues
    var turno = 0;
    return Scaffold(
      body: RefreshIndicator.adaptive(
        color: C.acento,
        onRefresh: () {
          Haptico.firme();
          return _cargar(forzar: true);
        },
        child: Escalonado(
          clave: '$_localListo|${_catalogo != null}|$_sinRed|$_filtro',
          child: CustomScrollView(
            key: const PageStorageKey('inicio'),
            cacheExtent: 800,
            slivers: [
              SliverToBoxAdapter(child: _Cabecera(saludo: nombre.isEmpty ? _saludo() : '${_saludo()}, $nombre',
                  inicial: s.cuenta.inicial, filtro: _filtro, alFiltrar: (f) => setState(() => _filtro = f))),
              if (!_localListo && verAtajos)
                const SliverToBoxAdapter(child: Esqueleto(forma: FormaEsqueleto.atajos))
              else if (verAtajos && _atajos.length > 1)
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(Esp.lado, 6, Esp.lado, 20),
                  sliver: SliverGrid(
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2, mainAxisSpacing: 8, crossAxisSpacing: 8, mainAxisExtent: 56),
                    delegate: SliverChildBuilderDelegate(
                      // en diagonal: de dos en dos, muy seguido
                      (_, i) => Entrada(indice: i ~/ 2, desplazamiento: 10, child: _Atajo(el: _atajos[i])),
                      childCount: _atajos.length,
                    ),
                  ),
                ),
              SliverList(
                // otro filtro: todo vuelve a entrar en su turno
                key: ValueKey(_filtro),
                delegate: SliverChildListDelegate([
                  if (_filtro == 'telefono') ...[
                    if (_localListo && _enTelefono.isEmpty)
                      Vacio(icono: Icons.download_for_offline_outlined, titulo: 'Aún no hay nada en tu teléfono',
                          texto: 'Descarga canciones, álbumes o videos y suenan sin internet.',
                          textoAccion: 'Descargar un enlace', iconoAccion: Icons.link_rounded,
                          alAccion: () => s.irAPestana?.call(3))
                    else ...[
                      // sin titulos de carruseles vacios (solo musica o solo videos)
                      for (final (titulo, audio) in const [('Tu música descargada', true), ('Tus videos descargados', false)])
                        if (_enTelefono.any((p) => (p['es_audio'] == true) == audio)) ...[
                          Entrada(indice: turno++, child: Carrusel(titulo: titulo,
                              elementos: _enTelefono.where((p) => (p['es_audio'] == true) == audio).toList())),
                          const SizedBox(height: Esp.entreSecciones),
                        ],
                    ],
                  ] else ...[
                    if (_filtro != 'videos' && _recientes.isNotEmpty) ...[
                      Entrada(indice: ++turno, child: Carrusel(titulo: 'Volver a escuchar', elementos: _recientes)),
                      const SizedBox(height: Esp.entreSecciones),
                    ],
                    if (_filtro == 'todo')
                      // hechos con tu historial; se oculta sola si aun no hay nada
                      SeccionMixes(alAbrir: (m) => Caudal.leer(context).abrirElemento(context, m)),
                    if (_filtro == 'todo' && _mixes.isNotEmpty) ...[
                      Entrada(indice: ++turno,
                          child: Carrusel(titulo: 'Mixes de tus artistas', elementos: _mixes)),
                      const SizedBox(height: Esp.entreSecciones),
                    ],
                    if (_catalogo == null && !_sinRed) const Esqueleto(),
                    if (_sinRed)
                      Vacio(icono: Icons.wifi_off_rounded, titulo: 'Sin conexión', error: true,
                          texto: 'Mientras vuelve, tienes lo descargado en «En tu teléfono».',
                          alAccion: () => _cargar(forzar: true)),
                    ...pintarSecciones(context, secciones, desde: turno + 1),
                  ],
                  const SizedBox(height: espacioInferior),
                ]),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// El saludo, el acceso a los ajustes y los filtros, sobre un degradado.
class _Cabecera extends StatelessWidget {
  const _Cabecera({required this.saludo, required this.inicial, required this.filtro, required this.alFiltrar});
  final String saludo;
  final String inicial;
  final String filtro;
  final ValueChanged<String> alFiltrar;

  void _ajustes(BuildContext context) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AjustesPagina()));

  @override
  Widget build(BuildContext context) => Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(colors: [Color(0xFF16324A), C.fondo],
              begin: Alignment.topCenter, end: Alignment.bottomCenter),
        ),
        padding: EdgeInsets.fromLTRB(Esp.lado, MediaQuery.paddingOf(context).top + Esp.m, Esp.lado, Esp.s),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Pulsable(
              escala: 0.9,
              child: GestureDetector(
                onTap: () => _ajustes(context),
                child: CircleAvatar(
                  radius: 17, backgroundColor: C.acento,
                  child: Text(inicial, style: const TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900)),
                ),
              ),
            ),
            const SizedBox(width: Esp.m),
            Expanded(child: Text(saludo, style: estiloTituloBarra, maxLines: 1, overflow: TextOverflow.ellipsis)),
            IconButton(
              tooltip: 'Escuchar juntos',
              icon: const Icon(Icons.groups_2_outlined),
              onPressed: () => Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => const JuntosPagina())),
            ),
            IconButton(
              tooltip: 'Tu resumen',
              icon: const Icon(Icons.insights_rounded),
              onPressed: () => ResumenPagina.abrir(context),
            ),
            IconButton(
              tooltip: 'Ajustes',
              icon: const Icon(Icons.settings_outlined),
              onPressed: () => _ajustes(context),
            ),
          ]),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              for (final (clave, texto) in const [('todo', 'Todo'), ('musica', 'Música'),
                ('videos', 'Videos'), ('telefono', 'En tu teléfono')])
                Pildora(texto: texto, activa: filtro == clave, alPulsar: () => alFiltrar(clave)),
            ]),
          ),
        ]),
      );
}

class _Atajo extends StatelessWidget {
  const _Atajo({required this.el});
  final Json el;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    return Pulsable(escala: 0.97, child: Material(
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
    ));
  }
}
