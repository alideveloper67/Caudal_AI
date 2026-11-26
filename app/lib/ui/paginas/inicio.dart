import 'dart:async';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../nucleo/vida_app.dart';
import '../../nucleo/recomendador.dart';
import '../../nucleo/catalogo.dart';
import '../../nucleo/coleccion.dart';
import 'musica_libre_pagina.dart';
import '../../nucleo/gustos.dart';
import '../../reproduccion/reproductor.dart';
import '../comunes.dart';
import '../cumpleanos.dart';
import '../inicio_rejilla.dart';
import '../../nucleo/cumpleanos.dart';
import '../menu_comunidad.dart';
import '../menu_hoja.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';
import '../premium/tarjetas_del_dia.dart';
import '../tu_mes_pasado.dart';
import 'ajustes_pagina.dart';
import 'estudio_pagina.dart';
import 'juntos_pagina.dart';
import 'me_gusta_externos_pagina.dart';
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
  List<Json> _rejilla = [];
  List<Json> _animos = [];
  List<Json> _mixes = [];
  List<Json> _enTelefono = [];
  Json? _descubre;
  List<Json> _parecidos = [];
  List<Json> _tiempo = [];
  Json? _mesPasado;

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
    // lo ultimo que se vio sale al instante; lo nuevo llega por detras
    if (_catalogo == null) {
      try {
        final guardado = await col.estado('catalogo_inicio');
        if (guardado is Map && mounted && _catalogo == null) {
          setState(() => _catalogo = Map<String, dynamic>.from(guardado));
        }
      } catch (_) {}
    }
    final recientes = await col.escuchadoHacePoco(40);
    final masUsadas = await col.masEscuchadasAhora(30);
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
    final mixes = <Json>[
      for (final a in await col.artistasFrecuentes(8))
        {'tipo': 'artista', 'id': a['id'], 'titulo': 'Mix de ${a['nombre']}',
         'subtitulo': '${a['nombre']} y artistas parecidos', 'miniatura': a['miniatura']}
    ];
    // los artistas que elegiste al crear la cuenta (o en Ajustes) tambien tienen su mix
    final yaEnMixes = {for (final m in mixes) '${m['id']}'};
    for (final g in Gustos.actuales) {
      if (mixes.length >= 16) break;
      if (g.id.isEmpty || !yaEnMixes.add(g.id)) continue;
      mixes.add({'tipo': 'artista', 'id': g.id, 'titulo': 'Mix de ${g.nombre}',
        'subtitulo': 'Uno de tus artistas favoritos', 'miniatura': g.portada});
    }
    final enTelefono = await col.descargadas();
    final tiempo = await Recomendador.maquinaDelTiempoDe(col);
    Json? mesPasado;
    try {
      mesPasado = await Recomendador.mesPasadoDe(col);
    } catch (_) {}
    if (!mounted) return;
    setState(() {
      _localListo = true;
      _rejilla = elementosDeInicio(atajos.take(9).toList(), [...recientes.take(3), ...masUsadas, ...recientes]);
      final enRejilla = {for (final e in _rejilla) '${e['clave']}'};
      _recientes = [for (final p in recientes) if (!enRejilla.contains('${p['clave']}')) p];
      _mixes = mixes;
      _enTelefono = enTelefono;
      _tiempo = tiempo;
      _mesPasado = mesPasado;
    });
    unawaited(_cargarAnimos(col));
    // "Descubre para ti" pide la radio de varias canciones: va aparte, sin frenar lo demas
    Recomendador.descubrir(col).then((d) {
      if (mounted && d != null) setState(() => _descubre = d);
    }).catchError((_) {});
    Recomendador.artistasParecidos(col).then((l) {
      if (mounted && l.isNotEmpty) setState(() => _parecidos = l);
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
        unawaited(col.guardarEstado('catalogo_inicio', datos).catchError((_) {}));
        if (mounted) setState(() {
          _catalogo = datos;
          _sinRed = false;
        });
      } catch (_) {
        if (mounted) setState(() => _sinRed = _catalogo == null);
      }
    }
  }

  /// Los estados de ánimo del catálogo (Relajación, Entrenamiento...) para las fichas de
  /// arriba: salen los guardados y se renuevan una vez por semana.
  Future<void> _cargarAnimos(Coleccion col) async {
    if (_animos.isNotEmpty) return;
    try {
      final g = await col.estado('fichas_animo');
      final idioma = Localizations.maybeLocaleOf(context)?.languageCode ?? 'es';
      List<Json> leer(Object? l) =>
          [for (final x in (l is List ? l : const []).whereType<Map>()) Map<String, dynamic>.from(x)];
      if (g is Map && g['idioma'] == idioma) {
        final l = leer(g['lista']);
        if (mounted && l.isNotEmpty) setState(() => _animos = l);
        if (DateTime.now().millisecondsSinceEpoch - ((g['cuando'] as num?) ?? 0) < 7 * 86400000) return;
      }
      final d = await Catalogo.pagina('FEmusic_moods_and_genres');
      final primera = (d['secciones'] as List? ?? const []).whereType<Map>().firstOrNull;
      final l = [for (final e in leer(primera?['elementos'])) if (e['tipo'] == 'genero') e].take(12).toList();
      if (l.isEmpty) return;
      await col.guardarEstado('fichas_animo', {'idioma': idioma, 'lista': l, 'cuando': DateTime.now().millisecondsSinceEpoch});
      if (mounted) setState(() => _animos = l);
    } catch (_) {/* sin red: solo los filtros */}
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
    // las canciones sugeridas van justo debajo de la rejilla; lo demás del catálogo, al final
    final rapidas = verAtajos
        ? secciones.where((x) => x['estilo'] == 'filas' && (x['elementos'] as List? ?? const []).isNotEmpty).take(1).toList()
        : const <Map>[];
    final otras = [for (final x in secciones) if (!rapidas.contains(x)) x];
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
                  inicial: s.cuenta.inicial, filtro: _filtro, alFiltrar: (f) => setState(() => _filtro = f), animos: _animos)),
              const SliverToBoxAdapter(child: CumpleInicio()),
              if (!_localListo && verAtajos)
                const SliverToBoxAdapter(child: Esqueleto(forma: FormaEsqueleto.atajos))
              else if (verAtajos && _rejilla.length > 2)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.only(top: 8, bottom: Esp.entreSecciones),
                    child: RejillaInicio(elementos: _rejilla),
                  ),
                ),
              SliverList(
                // otro filtro: todo vuelve a entrar en su turno
                key: ValueKey(_filtro),
                delegate: SliverChildListDelegate([
                  if (_filtro == 'telefono') ...[
                    if (_localListo && _enTelefono.isEmpty)
                      Vacio(icono: Icons.download_for_offline_outlined, titulo: kIsWeb ? 'Aún no hay canciones aquí' : 'Aún no hay nada en tu teléfono',
                          texto: kIsWeb ? 'Agrega las que tengas en este equipo y suenan sin internet.'
                              : 'Descarga canciones, álbumes o videos y suenan sin internet.',
                          textoAccion: kIsWeb ? 'Agregar canciones' : 'Descargar un enlace',
                          iconoAccion: kIsWeb ? Icons.add_rounded : Icons.link_rounded,
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
                    ...pintarSecciones(context, rapidas, desde: ++turno),
                    if (kIsWeb && _filtro != 'videos') const SeccionMusicaLibre(),
                    if (_filtro != 'videos' && _descubre != null) ...[
                      Entrada(indice: ++turno, child: _TarjetaDescubre(mix: _descubre!)),
                      const SizedBox(height: Esp.entreSecciones),
                    ],
                    if (_filtro == 'todo')
                      // hechos con tu historial; se oculta sola si aun no hay nada
                      SeccionMixes(alAbrir: (m) => Caudal.leer(context).abrirElemento(context, m)),
                    if (verAtajos && _parecidos.isNotEmpty) ...[
                      Entrada(indice: ++turno, child: Carrusel(titulo: 'Artistas parecidos a los que escuchas', elementos: _parecidos)),
                      const SizedBox(height: Esp.entreSecciones),
                    ],
                    // lo nuevo para ti, la semana del domingo y los accesos a los modos
                    if (verAtajos) const TarjetasDelDia(),
                    if (verAtajos && _recientes.length > 3) ...[
                      Entrada(indice: ++turno, child: Carrusel(titulo: 'Volver a escuchar', elementos: _recientes)),
                      const SizedBox(height: Esp.entreSecciones),
                    ],
                    if (_filtro == 'todo' && _mesPasado != null) ...[
                      Entrada(indice: ++turno, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        const TituloSeccion('Vuelve en el tiempo'),
                        TarjetaMesPasado(mix: _mesPasado!),
                      ])),
                      const SizedBox(height: Esp.entreSecciones),
                    ],
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
                    // acceso al Modo estudio (música sin letra, sonidos y temporizador)
                    if (verAtajos) const TarjetaEstudio(),
                    if (_catalogo == null && !_sinRed) const Esqueleto(),
                    if (_sinRed)
                      Vacio(icono: Icons.wifi_off_rounded, titulo: 'Sin conexión', error: true,
                          texto: kIsWeb ? 'Mientras vuelve, puedes oír «Tu música».'
                              : 'Mientras vuelve, tienes lo descargado en «En tu teléfono».',
                          alAccion: () => _cargar(forzar: true)),
                    ...pintarSecciones(context, otras, desde: turno + 1),
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

/// La marca, lo de siempre a mano (mensajes, comunidad, tú) y las fichas, sobre un degradado
/// que toma el color de lo que suena.
class _Cabecera extends StatefulWidget {
  const _Cabecera({required this.saludo, required this.inicial, required this.filtro, required this.alFiltrar,
      required this.animos});
  final String saludo;
  final String inicial;
  final String filtro;
  final ValueChanged<String> alFiltrar;
  final List<Json> animos;

  @override
  State<_Cabecera> createState() => _CabeceraState();
}

class _CabeceraState extends State<_Cabecera> {
  Reproductor? _r;
  String _url = '';
  Color? _color;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final r = Caudal.leer(context).reproductor;
    if (!identical(r, _r)) {
      _r?.removeListener(_mirar);
      _r = r..addListener(_mirar);
      _mirar();
    }
  }

  void _mirar() {
    final url = '${_r?.actual?['miniatura'] ?? ''}';
    if (url == _url) return;
    _url = url;
    if (url.isEmpty) {
      if (_color != null && mounted) setState(() => _color = null);
      return;
    }
    colorDominante(url).then((c) {
      if (mounted && _url == url) setState(() => _color = c);
    });
  }

  @override
  void dispose() {
    _r?.removeListener(_mirar);
    super.dispose();
  }

  void _abrir(Widget p) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => p));

  @override
  Widget build(BuildContext context) => AnimatedContainer(
        duration: Mov.color,
        decoration: BoxDecoration(
          gradient: LinearGradient(
              colors: [_color == null ? C.cabecera : Color.lerp(_color, C.fondo, 0.55)!, C.fondoVivo],
              begin: Alignment.topCenter, end: Alignment.bottomCenter),
        ),
        padding: EdgeInsets.only(top: MediaQuery.paddingOf(context).top + Esp.m, bottom: Esp.s),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.s, 0),
            child: Row(children: [
              Image.asset('assets/logo/caudal.png', width: 34, height: 34, filterQuality: FilterQuality.high),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Caudal', style: TextStyle(fontSize: 21, fontWeight: FontWeight.w900, letterSpacing: -0.5, height: 1.1)),
                  Text(widget.saludo, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12, color: Color(0xB3FFFFFF), height: 1.25)),
                ]),
              ),
              const _BotonMensajes(),
              IconButton(
                tooltip: 'Comunidad',
                icon: const Icon(Icons.people_alt_outlined),
                onPressed: () => MenuComunidad.abrir(context),
              ),
              Tooltip(
                message: 'Tú',
                child: InkResponse(
                  radius: 26,
                  onTap: () => mostrarMenuHoja(
                    context,
                    portada: CircleAvatar(
                      radius: 26, backgroundColor: C.acento,
                      child: Text(widget.inicial,
                          style: TextStyle(color: C.acentoTexto, fontSize: 21, fontWeight: FontWeight.w900)),
                    ),
                    titulo: Caudal.leer(context).cuenta.nombre,
                    subtitulo: 'Tu cuenta de Caudal',
                    grupos: [
                      [
                        OpcionMenu(Icons.insights_rounded, 'Tu resumen', () => ResumenPagina.abrir(context)),
                        OpcionMenu(Icons.groups_2_outlined, 'Escuchar juntos', () => _abrir(const JuntosPagina())),
                        OpcionMenu(Icons.link_rounded, 'Vincular cuentas', () => _abrir(const MeGustaExternosPagina()),
                            detalle: 'Trae tus me gusta de Spotify, YouTube o SoundCloud'),
                      ],
                      [OpcionMenu(Icons.settings_outlined, 'Ajustes', () => _abrir(const AjustesPagina()))],
                    ],
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(7),
                    child: ConGorro(
                      radio: 17, userId: Cumpleanos.i.miId.isEmpty ? null : Cumpleanos.i.miId,
                      child: CircleAvatar(
                        radius: 17, backgroundColor: C.acento,
                        child: Text(widget.inicial, style: TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900)),
                      ),
                    ),
                  ),
                ),
              ),
            ]),
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.only(left: Esp.lado, right: Esp.s),
            child: Row(children: [
              for (final (clave, texto) in const [('todo', 'Todo'), ('musica', 'Música'),
                ('videos', 'Videos'), ('telefono', kIsWeb ? 'Tu música' : 'En tu teléfono')])
                Pildora(texto: texto, activa: widget.filtro == clave, alPulsar: () => widget.alFiltrar(clave)),
              for (final g in widget.animos)
                Pildora(texto: '${g['titulo']}', activa: false,
                    alPulsar: () => Caudal.leer(context).abrirElemento(context, g)),
            ]),
          ),
        ]),
      );
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

class _BotonMensajesState extends State<_BotonMensajes> {
  int _sinLeer = 0;

  /// Cada minuto con Inicio a la vista; al volver a la app o a esta pestaña
  /// (por ejemplo, tras leer los mensajes) se mira en el acto.
  late final Sondeo _sondeo = Sondeo(const Duration(seconds: 60), _mirar);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _mirar());
    _sondeo.iniciar();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sondeo.seguirPantalla(context);
  }

  @override
  void dispose() {
    _sondeo.detener();
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
