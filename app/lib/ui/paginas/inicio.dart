import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/recomendador.dart';
import '../../nucleo/catalogo.dart';
import '../../nucleo/coleccion.dart';
import '../comunes.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';
import 'ajustes_pagina.dart';
import 'juntos_pagina.dart';
import 'mensajes_pagina.dart';
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
  Json? _descubre;
  List<Json> _tiempo = [];

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
    final tiempo = await Recomendador.maquinaDelTiempoDe(col);
    if (!mounted) return;
    setState(() {
      _localListo = true;
      _recientes = recientes;
      _atajos = atajos.take(8).toList();
      _mixes = mixes;
      _enTelefono = enTelefono;
      _tiempo = tiempo;
    });
    // "Descubre para ti" pide la radio de varias canciones: va aparte, sin frenar lo demas
    Recomendador.descubrir(col).then((d) {
      if (mounted && d != null) setState(() => _descubre = d);
    }).catchError((_) {});
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
                    if (_filtro != 'videos' && _descubre != null) ...[
                      Entrada(indice: ++turno, child: _TarjetaDescubre(mix: _descubre!)),
                      const SizedBox(height: Esp.entreSecciones),
                    ],
                    if (_filtro == 'todo')
                      // hechos con tu historial; se oculta sola si aun no hay nada
                      SeccionMixes(alAbrir: (m) => Caudal.leer(context).abrirElemento(context, m)),
                    if (_filtro == 'todo' && _tiempo.isNotEmpty) ...[
                      Entrada(indice: ++turno,
                          child: Carrusel(titulo: 'Máquina del tiempo', elementos: _tiempo)),
                      const SizedBox(height: Esp.entreSecciones),
                    ],
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
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [C.cabecera, C.fondo],
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
                  child: Text(inicial, style: TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900)),
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
            const _BotonMensajes(),
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

/// "Descubre para ti": una tarjeta grande, como la de Spotify.
class _TarjetaDescubre extends StatelessWidget {
  const _TarjetaDescubre({required this.mix});
  final Json mix;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final portadas = [for (final m in (mix['miniaturas'] as List? ?? const [])) '$m']
        .where((m) => m.isNotEmpty).take(3).toList();
    final pistas = [
      for (final p in (mix['pistas'] as List? ?? const []))
        if (p is Map) Map<String, dynamic>.from(p)
    ];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
      child: Pulsable(
        escala: 0.98,
        child: GestureDetector(
          onTap: () => s.abrirElemento(context, mix),
          child: Container(
            padding: const EdgeInsets.all(Esp.l),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              gradient: const LinearGradient(colors: [Color(0xFF5B3FD6), Color(0xFF1C2A5E)],
                  begin: Alignment.topLeft, end: Alignment.bottomRight),
            ),
            child: Row(children: [
              SizedBox(
                width: 96, height: 96,
                child: Stack(children: [
                  for (final (i, url) in portadas.reversed.indexed)
                    Positioned(
                      left: (portadas.length - 1 - i) * 12.0, top: (portadas.length - 1 - i) * 6.0,
                      child: Portada(url: url, lado: 72, radio: 8),
                    ),
                ]),
              ),
              const SizedBox(width: Esp.m),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Row(children: [
                    Icon(Icons.auto_awesome_rounded, size: 16, color: Color(0xFFFFD66B)),
                    SizedBox(width: 6),
                    Text('HECHO PARA TI', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800,
                        letterSpacing: 1, color: Color(0xFFFFD66B))),
                  ]),
                  const SizedBox(height: 4),
                  Text('${mix['titulo']}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 2),
                  Text('${mix['subtitulo']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12.5, color: Color(0xCCFFFFFF))),
                ]),
              ),
              IconButton.filled(
                tooltip: 'Reproducir',
                style: IconButton.styleFrom(backgroundColor: Colors.white, foregroundColor: const Color(0xFF1C2A5E)),
                onPressed: pistas.isEmpty ? null : () => s.reproductor.reproducirLista(pistas,
                    contexto: {'tipo': 'mix', 'id': mix['id'], 'titulo': mix['titulo']}),
                icon: const Icon(Icons.play_arrow_rounded),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

/// El sobre de los mensajes, con cuántos hay sin leer (se mira cada minuto).
class _BotonMensajes extends StatefulWidget {
  const _BotonMensajes();

  @override
  State<_BotonMensajes> createState() => _BotonMensajesState();
}

class _BotonMensajesState extends State<_BotonMensajes> with WidgetsBindingObserver {
  int _sinLeer = 0;
  Timer? _reloj;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _mirar());
    _reloj = Timer.periodic(const Duration(seconds: 60), (_) => _mirar());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    if (estado == AppLifecycleState.resumed) _mirar();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _reloj?.cancel();
    super.dispose();
  }

  Future<void> _mirar() async {
    if (!mounted) return;
    final chat = chatDe(context);
    if (chat == null) return;
    try {
      final n = await chat.sinLeer();
      if (mounted && n != _sinLeer) setState(() => _sinLeer = n);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) => IconButton(
        tooltip: _sinLeer > 0 ? 'Mensajes ($_sinLeer sin leer)' : 'Mensajes',
        icon: Badge(
          isLabelVisible: _sinLeer > 0,
          label: Text('$_sinLeer'),
          backgroundColor: C.acento,
          textColor: C.acentoTexto,
          child: const Icon(Icons.forum_outlined),
        ),
        onPressed: () async {
          await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const MensajesPagina()));
          _mirar();
        },
      );
}
