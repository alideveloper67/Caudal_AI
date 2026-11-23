import 'dart:async';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/listas_compartidas.dart';
import '../../nucleo/vida_app.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'ajustes_pagina.dart';
import 'importar_archivos_hoja.dart';
import 'inicio.dart';
import 'lista_compartida_pagina.dart';
import 'lista_compartir.dart';

class BibliotecaPagina extends StatefulWidget {
  const BibliotecaPagina({super.key});

  @override
  State<BibliotecaPagina> createState() => _BibliotecaPaginaState();
}

class _BibliotecaPaginaState extends State<BibliotecaPagina> with AutomaticKeepAliveClientMixin {
  String? _filtro;
  List<Json> _elementos = [];
  bool _cargado = false;
  Coleccion? _col;
  int _vuelta = 0;

  /// Las listas de otras personas donde soy miembro (se traen de la nube, aparte).
  List<ListaCompartida> _compartidas = ListasCompartidasVistas.lista.value;

  /// Las compartidas se miran cada minuto, solo con la app y esta pestaña a la
  /// vista; al volver a ellas se miran en el acto.
  late final Sondeo _sondeo = Sondeo(const Duration(seconds: 60), _traerCompartidas);

  /// Varios avisos seguidos de la colección (sincronizar, importar...) se
  /// juntan en una sola recarga.
  Timer? _espera;

  @override
  bool get wantKeepAlive => true;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_col == null) {
      _col = Caudal.leer(context).coleccion..addListener(_alCambiarColeccion);
      _cargar();
      _traerCompartidas();
      _sondeo.iniciar();
    }
    _sondeo.seguirPantalla(context);
  }

  @override
  void dispose() {
    _sondeo.detener();
    _espera?.cancel();
    _col?.removeListener(_alCambiarColeccion);
    super.dispose();
  }

  void _alCambiarColeccion() {
    _espera?.cancel();
    _espera = Timer(const Duration(milliseconds: 250), () {
      if (mounted) _cargar();
    });
  }

  /// Lo que se ve de una compartida (para no recargar si no cambio nada).
  static String _huella(List<ListaCompartida> ls) => [
        for (final c in ls)
          '${c.id}|${c.nombre}|${c.descripcion}|${c.rol}|${c.total}|${c.actualizada}|${c.dueno.visible}'
      ].join('\n');

  /// Sin internet o sin cuenta, la sección simplemente no aparece.
  Future<void> _traerCompartidas() async {
    if (!mounted) return;
    final base = listasDe(context);
    if (base == null) return;
    try {
      final l = await base.misListasCompartidas();
      ListasCompartidasVistas.lista.value = l;
      if (!mounted) return;
      final cambio = _huella(l) != _huella(_compartidas);
      _compartidas = l;
      if (cambio) _cargar();
    } catch (_) {}
  }

  Future<void> _tengoCodigo() async {
    await hojaTengoCodigo(context);
    if (mounted) _traerCompartidas();
  }

  Future<void> _cargar() async {
    final col = _col!;
    final f = _filtro;
    // si se cambia de filtro mientras carga, la respuesta vieja no pisa la nueva
    final vuelta = ++_vuelta;
    final salida = <Json>[];
    if (f == null || f == 'listas') {
      salida.add({'tipo': 'me_gusta', 'titulo': 'Tus me gusta',
        'subtitulo': 'Lista • ${col.totalMeGusta} canciones', 'fijada': true});
    }
    if (f == null || f == 'telefono') {
      final m = (await col.descargadas(soloAudio: true)).length;
      final v = (await col.descargadas(soloAudio: false)).length;
      salida.add({'tipo': 'descargados', 'id': 'musica', 'solo': true, 'titulo': kIsWeb ? 'Tu música' : 'Música descargada',
        'subtitulo': '${kIsWeb ? 'En este navegador' : 'En tu teléfono'} • $m canciones', 'icono': 'musica'});
      if (!kIsWeb) salida.add({'tipo': 'descargados', 'id': 'videos', 'solo': false, 'titulo': 'Videos descargados',
        'subtitulo': 'En tu teléfono • $v videos', 'icono': 'video'});
    }
    if (f == null || f == 'listas') {
      for (final l in await col.listas()) {
        salida.add({'tipo': 'mi_lista', 'id': l['id'], 'titulo': l['nombre'],
          'subtitulo': 'Lista • ${l['n']} canciones',
          'mosaico': await col.portadasDeLista(Servicios.idLista(l['id']) ?? -1),
          'fijada': l['fijada'] == 1});
      }
      salida.addAll((await col.guardados('lista')).map((g) => {...g, 'subtitulo': g['subtitulo'] ?? 'Lista'}));
      if (_compartidas.isNotEmpty) {
        salida.add({'tipo': 'cabecera', 'titulo': 'Listas compartidas'});
        for (final c in _compartidas) {
          salida.add({'tipo': 'lista_compartida', 'id': c.id, 'titulo': c.nombre, 'insignia': true,
            'subtitulo': 'Compartida · ${c.dueno.visible}', 'compartida': c});
        }
      }
    }
    if (f == null || f == 'albumes') {
      salida.addAll((await col.guardados('album')).map((g) => {...g, 'subtitulo': g['subtitulo'] ?? 'Álbum'}));
    }
    if (f == null || f == 'artistas') {
      salida.addAll((await col.guardados('artista')).map((g) => {...g, 'subtitulo': 'Artista'}));
    }
    if (mounted && vuelta == _vuelta) {
      setState(() {
        _elementos = salida;
        _cargado = true;
      });
    }
  }

  Future<void> _nuevaLista() async {
    final s = Caudal.leer(context);
    final libre = await s.coleccion.nombreLibre();
    if (!mounted) return;
    final nombre = await pedirTexto(context, 'Nueva lista', libre);
    if (nombre == null) return;
    try {
      final id = await s.coleccion.crearLista(nombre);
      if (mounted) s.abrirElemento(context, {'tipo': 'mi_lista', 'id': id, 'titulo': nombre});
    } on FormatException catch (e) {
      s.avisar(e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final s = Caudal.of(context);
    final vacio = _cargado && _filtro != null && _elementos.isEmpty;
    return Scaffold(
      body: Escalonado(
        clave: '$_cargado|$_filtro',
        child: CustomScrollView(key: const PageStorageKey('biblioteca'), slivers: [
          SliverAppBar(
            pinned: true,
            backgroundColor: C.fondoVivo,
            surfaceTintColor: Colors.transparent,
            titleSpacing: Esp.lado,
            title: Row(children: [
              Pulsable(
                escala: 0.9,
                child: GestureDetector(
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AjustesPagina())),
                  child: CircleAvatar(radius: 16, backgroundColor: C.acento,
                      child: Text(s.cuenta.inicial, style: TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900))),
                ),
              ),
              const SizedBox(width: Esp.m),
              const Text('Tu biblioteca', style: estiloTituloBarra),
            ]),
            actions: [
              IconButton(
                tooltip: 'Tengo un código',
                icon: const Icon(Icons.pin_outlined, size: 26),
                onPressed: _tengoCodigo,
              ),
              IconButton(
                tooltip: 'Traer música de otra app o de tu teléfono',
                icon: const Icon(Icons.playlist_add_rounded, size: 28),
                onPressed: () => hojaTraer(context),
              ),
              IconButton(tooltip: 'Nueva lista', icon: const Icon(Icons.add_rounded, size: 28), onPressed: _nuevaLista),
            ],
            bottom: PreferredSize(
              preferredSize: const Size.fromHeight(50),
              child: SizedBox(
                height: 50,
                child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.fromLTRB(Esp.lado, 2, Esp.lado, 6),
                    children: [
                  if (_filtro != null)
                    Pildora(icono: Icons.close_rounded, tooltip: 'Quitar el filtro', activa: false, alPulsar: () {
                      setState(() => _filtro = null);
                      _cargar();
                    }),
                  for (final (clave, texto) in const [('listas', 'Listas'), ('albumes', 'Álbumes'),
                    ('artistas', 'Artistas'), ('telefono', kIsWeb ? 'Tu música' : 'En tu teléfono')])
                    if (_filtro == null || _filtro == clave)
                      Pildora(texto: texto, activa: _filtro == clave, alPulsar: () {
                        setState(() => _filtro = _filtro == clave ? null : clave);
                        _cargar();
                      }),
                ]),
              ),
            ),
          ),
          if (!_cargado)
            const SliverToBoxAdapter(child: Esqueleto(filas: true))
          else if (vacio)
            SliverToBoxAdapter(
              child: Vacio(
                icono: switch (_filtro) {
                  'albumes' => Icons.album_outlined,
                  'artistas' => Icons.person_outline_rounded,
                  _ => Icons.library_music_outlined,
                },
                titulo: switch (_filtro) {
                  'albumes' => 'Aún no guardaste álbumes',
                  'artistas' => 'Aún no sigues a ningún artista',
                  _ => 'Aquí no hay nada todavía',
                },
                texto: switch (_filtro) {
                  'albumes' => 'En un álbum, toca ⊕ y aparece aquí.',
                  'artistas' => 'En la página de un artista, toca «Seguir».',
                  _ => 'Lo que guardes aparece en tu biblioteca.',
                },
                textoAccion: 'Buscar',
                iconoAccion: Icons.search_rounded,
                alAccion: () => s.irAPestana?.call(1),
              ),
            )
          else
            SliverList.builder(
              itemCount: _elementos.length,
              itemBuilder: (_, i) => Entrada(indice: i, desplazamiento: 10, child: _Item(el: _elementos[i])),
            ),
          const SliverToBoxAdapter(child: SizedBox(height: espacioInferior + 10)),
        ]),
      ),
    );
  }
}

class _Item extends StatelessWidget {
  const _Item({required this.el});
  final Json el;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final tipo = el['tipo'];
    if (tipo == 'cabecera') {
      return Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, 18, Esp.lado, 4),
        child: Text('${el['titulo']}', style: estiloTituloSeccion.copyWith(fontSize: 18)),
      );
    }
    final compartida = tipo == 'lista_compartida';
    Widget portada;
    if (compartida) {
      portada = Container(
        width: 60, height: 60,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(4),
          gradient: const LinearGradient(colors: [Color(0xFF4C1D95), Color(0xFF7C5CFF)]),
        ),
        child: const Icon(Icons.group_rounded, color: Colors.white),
      );
    } else if (tipo == 'me_gusta') {
      portada = const PortadaMeGusta(lado: 60, radio: 4);
    } else if (tipo == 'descargados') {
      portada = Container(
        width: 60, height: 60,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(4),
          gradient: LinearGradient(colors: el['icono'] == 'video'
              ? const [Color(0xFF7C2D12), Color(0xFFF97316)] : const [Color(0xFF0E7490), Color(0xFF22D3EE)]),
        ),
        child: Icon(el['icono'] == 'video' ? Icons.videocam_rounded : Icons.download_for_offline_rounded,
            color: Colors.white),
      );
    } else if ((el['mosaico'] as List?)?.length == 4) {
      final m = [for (final u in el['mosaico'] as List) '$u'];
      portada = ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: SizedBox(width: 60, height: 60, child: Wrap(children: [
          for (final u in m) Portada(url: u, lado: 30, radio: 0),
        ])),
      );
    } else {
      final mini = (el['mosaico'] as List?)?.isNotEmpty == true ? '${(el['mosaico'] as List).first}' : '${el['miniatura'] ?? ''}';
      portada = Portada(url: mini, lado: 60, radio: tipo == 'artista' ? 0 : 4, circulo: tipo == 'artista',
          icono: tipo == 'artista' ? Icons.person_rounded : Icons.queue_music_rounded);
    }
    return Pulsable(escala: 0.985, child: ListenableBuilder(
      listenable: s.reproductor,
      builder: (_, _) {
        final ctx = s.reproductor.contexto;
        final sonando = ctx != null && ctx['tipo'] == tipo && '${ctx['id']}' == '${el['id'] ?? tipo}' &&
            s.reproductor.estado.name != 'parado';
        return InkWell(
          onTap: () => compartida
              ? abrirListaCompartida(context, el['compartida'] as ListaCompartida)
              : s.abrirElemento(context, el),
          onLongPress: compartida ? null : () => s.reproducirElemento(context, el),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 7),
            child: Row(children: [
              portada,
              const SizedBox(width: 13),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${el['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: estiloTituloFila.copyWith(color: sonando ? C.acento : C.texto)),
                const SizedBox(height: 3),
                Row(children: [
                  if (el['insignia'] == true) Padding(
                    padding: const EdgeInsets.only(right: 5),
                    child: Icon(Icons.group_rounded, size: 14, color: C.acento),
                  ),
                  if (el['fijada'] == true) Padding(
                    padding: EdgeInsets.only(right: 5),
                    child: Icon(Icons.push_pin_rounded, size: 13, color: C.acento),
                  ),
                  Expanded(child: Text('${el['subtitulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: estiloSecundario)),
                ]),
              ])),
              if (sonando) Icon(Icons.volume_up_rounded, color: C.acento, size: 20),
            ]),
          ),
        );
      },
    ));
  }
}
