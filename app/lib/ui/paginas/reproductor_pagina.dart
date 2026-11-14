import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:media_kit_video/media_kit_video.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/coleccion.dart';
import '../../reproduccion/reproductor.dart';
import '../comunes.dart';
import '../plataforma.dart';
import '../reproductor/animaciones.dart';
import '../reproductor/barra_progreso.dart';
import '../reproductor/fondo_ambiente.dart';
import '../reproductor/linea_karaoke.dart';
import '../reproductor/portada_deslizable.dart';
import '../servicios.dart';
import '../tema.dart';
import 'sonido.dart';

class ReproductorPagina extends StatefulWidget {
  const ReproductorPagina({super.key});

  @override
  State<ReproductorPagina> createState() => _ReproductorPaginaState();
}

class _ReproductorPaginaState extends State<ReproductorPagina> {
  Color _color = C.superficie3;
  String _url = '';
  // cuanto se ha bajado la pantalla con el dedo (sin reconstruir la pagina)
  final _arrastre = ValueNotifier<double>(0);
  bool _cerrando = false;

  // hacia donde se pidio el ultimo cambio de cancion (1 siguiente, -1 anterior)
  int _pedido = 1;
  // con el que entro la cancion que suena; las que llegan solas vienen de la derecha
  int _direccion = 1;
  String _claveVista = '';

  // el contenido aparece un poco despues de que la portada empieza a volar
  Animation<double>? _ruta;
  Animation<double> _entrada = kAlwaysCompleteAnimation;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final ruta = ModalRoute.of(context)?.animation;
    if (ruta != null && !identical(ruta, _ruta)) {
      _ruta = ruta;
      _entrada = ruta.drive(CurveTween(curve: const Interval(0.25, 1, curve: Curves.easeOut)));
    }
  }

  @override
  void dispose() {
    _arrastre.dispose();
    super.dispose();
  }

  void _colorDe(String url) {
    if (url == _url) return;
    _url = url;
    colorDominante(url).then((c) {
      if (mounted) setState(() => _color = c);
    });
  }

  /// Cierra esta pantalla una sola vez: si se pidiera dos veces, el segundo
  /// pop le llegaria al armazon (que con nada detras cierra la app).
  void _cerrar() {
    if (_cerrando || !mounted) return;
    final ruta = ModalRoute.of(context);
    if (ruta == null || !ruta.isActive) return;
    _cerrando = true;
    if (ruta.isCurrent) {
      Navigator.of(context).pop();
    } else {
      // hay algo encima (la cola, un menu): se quita esta sin tocar lo demas
      Navigator.of(context).removeRoute(ruta);
    }
  }

  void _soltar(double velocidad) {
    if (_arrastre.value > 140 || velocidad > 700) {
      Haptico.toque();
      _cerrar();
    } else {
      _arrastre.value = 0;
    }
  }

  /// Deslizar hacia abajo cierra, como en Spotify. La pagina es una lista, asi
  /// que el gesto se lee del desplazamiento: tirar hacia abajo estando arriba.
  bool _alDesplazar(ScrollNotification n) {
    if (n.depth != 0) return false;
    if (n is OverscrollNotification && n.dragDetails != null && n.overscroll < 0) {
      _arrastre.value = (_arrastre.value - n.overscroll).clamp(0.0, 600.0);
    } else if (n is ScrollUpdateNotification && n.dragDetails != null && _arrastre.value > 0) {
      // volver a subir el dedo deshace el arrastre antes de mover la lista
      _arrastre.value = (_arrastre.value - (n.scrollDelta ?? 0)).clamp(0.0, 600.0);
    } else if (n is ScrollEndNotification && _arrastre.value > 0) {
      _soltar(n.dragDetails?.primaryVelocity ?? 0);
    }
    return false;
  }

  void _siguiente(Reproductor r) {
    _pedido = 1;
    r.siguiente();
  }

  void _anterior(Reproductor r) {
    _pedido = -1;
    r.anterior();
  }

  /// Doble toque en la portada: marca me gusta (nunca lo quita, como en las
  /// redes); si ya estaba, solo se ve el corazon.
  void _meGustaDobleToque(Servicios s, Json p) {
    if (s.coleccion.meGusta('${p['clave']}')) {
      Haptico.toque();
      return;
    }
    s.alternarMeGusta(p);
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final r = s.reproductor;
    final ancho = MediaQuery.sizeOf(context).width;
    return ValueListenableBuilder<double>(
      valueListenable: _arrastre,
      builder: (_, bajada, hijo) => Transform.translate(offset: Offset(0, bajada), child: hijo),
      // en iPhone tambien se cierra deslizando desde el borde izquierdo
      child: BordeVolver(
        alVolver: _cerrar,
        child: NotificationListener<ScrollNotification>(
        onNotification: _alDesplazar,
        child: ListenableBuilder(
          listenable: Listenable.merge([r, s.coleccion]),
          builder: (context, _) {
            final p = r.actual;
            if (p == null) {
              // se detuvo la musica: no hay nada que mostrar
              WidgetsBinding.instance.addPostFrameCallback((_) => _cerrar());
              return const SizedBox.shrink();
            }
            final url = '${p['miniatura'] ?? ''}';
            _colorDe(url);
            final clave = '${p['clave']}';
            if (clave != _claveVista) {
              // la primera vez no hay de donde venir; luego, de donde se pidio
              _direccion = _claveVista.isEmpty ? 1 : _pedido;
              _pedido = 1;
              _claveVista = clave;
            }
            final gusta = s.coleccion.meGusta(clave);
            final ctx = r.contexto;
            final video = r.modo == 'video';
            return Stack(children: [
              // ---- modo ambiente: la portada desenfocada, moviendose despacio
              Positioned.fill(
                child: FondoAmbiente(url: url, color: _color,
                    enMovimiento: !video && r.estado == EstadoRepro.sonando),
              ),
              Scaffold(
                backgroundColor: Colors.transparent,
                body: FadeTransition(
                  opacity: _entrada,
                  child: SafeArea(
                  // en iOS rebota abajo, pero arriba el tiron llega a "bajar para cerrar"
                  child: ListView(padding: EdgeInsets.zero, physics: esIOS ? const RebotaSoloAbajo() : null,
                      children: [
                    // ---- cabecera
                    Padding(
                      padding: const EdgeInsets.fromLTRB(4, 4, 4, 0),
                      child: Row(children: [
                        IconButton(icon: const Icon(Icons.keyboard_arrow_down_rounded, size: 32),
                            onPressed: _cerrar),
                        Expanded(child: Column(children: [
                          Text(ctx == null ? 'Reproduciendo' : 'Reproduciendo desde',
                              style: const TextStyle(fontSize: 11, color: Color(0xCCFFFFFF), letterSpacing: 0.4)),
                          Text('${ctx?['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
                        ])),
                        IconButton(icon: const Icon(Icons.more_vert_rounded), onPressed: () => s.hojaPista(context, p)),
                      ]),
                    ),
                    const SizedBox(height: 14),
                    // ---- portada o video
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 22),
                      child: video
                          ? _VideoEnLinea(r: r)
                          : PortadaDeslizable(
                              pista: p,
                              lado: ladoPortadaGrande(ancho),
                              direccion: _direccion,
                              alSiguiente: () => _siguiente(r),
                              alAnterior: () => _anterior(r),
                              alDobleToque: () => _meGustaDobleToque(s, p),
                            ),
                    ),
                    const SizedBox(height: 26),
                    // ---- titulo
                    Padding(
                      padding: const EdgeInsets.only(left: 22, right: 10),
                      child: Row(children: [
                        Expanded(
                          // el titulo tambien entra por el lado del gesto
                          child: ClipRect(
                            child: AnimatedSwitcher(
                              duration: const Duration(milliseconds: 340),
                              transitionBuilder: deslizarEn(_direccion, ValueKey(clave), distancia: 0.35),
                              layoutBuilder: (a, previos) => Stack(alignment: Alignment.centerLeft,
                                  children: [...previos, ?a]),
                              child: Column(key: ValueKey(clave), crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: -0.3)),
                                const SizedBox(height: 3),
                                GestureDetector(
                                  onTap: () {
                                    final arts = [
                                      for (final a in (p['artistas'] is List ? p['artistas'] as List : const []))
                                        if (a is Map && '${a['id'] ?? ''}'.isNotEmpty) '${a['id']}'
                                    ];
                                    if (arts.isEmpty) return;
                                    // cierra el reproductor y abre al artista en la pestana visible
                                    _cerrando = true;
                                    s.irAArtista(context, arts.first);
                                  },
                                  child: Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(fontSize: 15, color: Color(0xCCFFFFFF))),
                                ),
                              ]),
                            ),
                          ),
                        ),
                        CorazonAnimado(gusta: gusta, tamano: 28, alPulsar: () => s.alternarMeGusta(p)),
                      ]),
                    ),
                    const SizedBox(height: 4),
                    // ---- progreso
                    Padding(padding: const EdgeInsets.symmetric(horizontal: 10),
                        child: RepaintBoundary(child: BarraProgreso(r: r))),
                    // ---- controles
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                        IconButton(
                          icon: Icon(Icons.shuffle_rounded, color: r.aleatorio ? C.acento : C.texto),
                          onPressed: () async {
                            Haptico.seleccion();
                            s.avisar(await r.alternarAleatorio() ? 'Aleatorio activado' : 'Aleatorio desactivado');
                          },
                        ),
                        Hundible(
                          escala: 0.86,
                          child: IconButton(iconSize: 42, icon: const Icon(Icons.skip_previous_rounded), onPressed: () {
                            Haptico.seleccion();
                            _anterior(r);
                          }),
                        ),
                        _BotonGrande(r: r),
                        Hundible(
                          escala: 0.86,
                          child: IconButton(iconSize: 42, icon: const Icon(Icons.skip_next_rounded), onPressed: () {
                            Haptico.seleccion();
                            _siguiente(r);
                          }),
                        ),
                        IconButton(
                          icon: Icon(r.repetir == 'una' ? Icons.repeat_one_rounded : Icons.repeat_rounded,
                              color: r.repetir == 'no' ? C.texto : C.acento),
                          onPressed: () async {
                            Haptico.seleccion();
                            final m = await r.ciclarRepetir();
                            s.avisar({'no': 'Repetir desactivado', 'todo': 'Repetir toda la cola',
                              'una': 'Repetir esta canción'}[m]!);
                          },
                        ),
                      ]),
                    ),
                    // ---- extras
                    Padding(
                      padding: const EdgeInsets.fromLTRB(14, 4, 14, 0),
                      child: Row(children: [
                        if (r.fuente != null)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                            decoration: BoxDecoration(
                              border: Border.all(color: C.acento.withValues(alpha: 0.5)),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(r.fuente!.insignia,
                                style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: C.acento)),
                          ),
                        const Spacer(),
                        if ('${p['video_id'] ?? ''}'.isNotEmpty || (p['archivo'] != null && p['es_audio'] != true))
                          // en un telefono estrecho se encoge en vez de desbordar la fila
                          Flexible(child: FittedBox(fit: BoxFit.scaleDown, child: SegmentedButton<String>(
                            showSelectedIcon: false,
                            style: SegmentedButton.styleFrom(
                              visualDensity: VisualDensity.compact,
                              selectedBackgroundColor: C.texto,
                              selectedForegroundColor: C.fondo,
                              side: const BorderSide(color: Color(0x55FFFFFF)),
                            ),
                            segments: const [
                              ButtonSegment(value: 'audio', label: Text('Canción')),
                              ButtonSegment(value: 'video', label: Text('Video')),
                            ],
                            selected: {r.modo},
                            onSelectionChanged: (sel) {
                              Haptico.seleccion();
                              r.cambiarModo(sel.first);
                            },
                          ))),
                        const Spacer(),
                        IconButton(
                          tooltip: 'Temporizador',
                          icon: Icon(Icons.bedtime_outlined, color: r.restanteApagado != null ? C.acento : C.texto),
                          onPressed: () => _temporizador(context, r),
                        ),
                        IconButton(
                          tooltip: 'Sonido',
                          icon: Icon(Icons.graphic_eq_rounded,
                              color: s.ajustes.entero('super_volumen') > 0 || s.ajustes.sino('ecualizador') ? C.acento : C.texto),
                          onPressed: () => mostrarSonido(context),
                        ),
                        IconButton(
                          tooltip: 'Cola',
                          icon: const Icon(Icons.queue_music_rounded),
                          onPressed: () => _cola(context),
                        ),
                      ]),
                    ),
                    const SizedBox(height: 16),
                    // ---- letra
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      child: _TarjetaLetra(pista: p, color: _color),
                    ),
                    const SizedBox(height: 24),
                  ]),
                ),
                ),
              ),
            ]);
          },
        ),
      ),
      ),
    );
  }

  Future<void> _temporizador(BuildContext context, Reproductor r) async {
    final restante = r.restanteApagado;
    await showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Padding(padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
            child: Text('Temporizador para dormir', style: estiloTituloSeccion)),
        if (restante != null)
          ListTile(
            leading: const Icon(Icons.timer_off_outlined, color: C.acento),
            title: Text(restante == -1 ? 'Activo: al terminar la canción'
                : 'Activo: quedan ${restante ~/ 60} min ${restante % 60} s'),
            subtitle: const Text('Tocar para desactivar', style: estiloSecundario),
            onTap: () {
              Navigator.pop(ctx);
              r.programarApagado();
            },
          ),
        for (final m in const [5, 15, 30, 45, 60, 90])
          ListTile(title: Text('$m minutos'), onTap: () {
            Navigator.pop(ctx);
            r.programarApagado(minutos: m);
          }),
        ListTile(title: const Text('Al terminar esta canción'), onTap: () {
          Navigator.pop(ctx);
          r.programarApagado(alTerminar: true);
        }),
      ])),
    );
  }

  Future<void> _cola(BuildContext context) => showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (_) => const _HojaCola(),
      );
}

/// El boton redondo de play/pausa: el icono se transforma y el boton se
/// hunde un poco bajo el dedo.
class _BotonGrande extends StatelessWidget {
  const _BotonGrande({required this.r});
  final Reproductor r;

  @override
  Widget build(BuildContext context) {
    final cargando = r.estado == EstadoRepro.cargando;
    return Hundible(
      escala: 0.9,
      child: Material(
        color: C.texto,
        shape: const CircleBorder(),
        elevation: 6,
        shadowColor: const Color(0x66000000),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: () {
            HapticFeedback.lightImpact();
            r.alternar();
          },
          child: SizedBox(
            width: 70, height: 70,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              transitionBuilder: (hijo, a) => ScaleTransition(scale: a, child: FadeTransition(opacity: a, child: hijo)),
              child: cargando
                  ? const Padding(key: ValueKey('cargando'), padding: EdgeInsets.all(22),
                      child: CircularProgressIndicator(strokeWidth: 3, color: C.fondo))
                  : Center(key: const ValueKey('icono'),
                      child: IconoPlayPausa(sonando: r.estado == EstadoRepro.sonando, tamano: 42, color: C.fondo)),
            ),
          ),
        ),
      ),
    );
  }
}

/// El video dentro de la pantalla del reproductor (con pantalla completa).
class _VideoEnLinea extends StatelessWidget {
  const _VideoEnLinea({required this.r});
  final Reproductor r;

  @override
  Widget build(BuildContext context) => ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: AspectRatio(
          aspectRatio: 16 / 9,
          child: ColoredBox(
            color: Colors.black,
            child: MaterialVideoControlsTheme(
              normal: const MaterialVideoControlsThemeData(
                seekBarThumbColor: C.acento, seekBarPositionColor: C.acento,
                buttonBarButtonColor: Colors.white, topButtonBar: [],
              ),
              fullscreen: const MaterialVideoControlsThemeData(
                seekBarThumbColor: C.acento, seekBarPositionColor: C.acento,
              ),
              child: Video(controller: r.pantalla, controls: MaterialVideoControls,
                  fill: Colors.black),
            ),
          ),
        ),
      );
}

// ---------------------------------------------------------------- cola

class _HojaCola extends StatelessWidget {
  const _HojaCola();

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final r = s.reproductor;
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.75,
      maxChildSize: 0.95,
      builder: (_, scroll) => ListenableBuilder(
        listenable: r,
        builder: (context, _) {
          final siguientes = r.siguientesDeContexto;
          final normales = [for (var i = 0; i < siguientes.length; i++) if (siguientes[i]['_auto'] != true) i];
          final auto = [for (var i = 0; i < siguientes.length; i++) if (siguientes[i]['_auto'] == true) i];
          return CustomScrollView(controller: scroll, slivers: [
            const SliverToBoxAdapter(child: Padding(padding: EdgeInsets.fromLTRB(20, 0, 20, 4),
                child: Text('Sonando ahora', style: estiloTituloSeccion))),
            if (r.actual != null)
              SliverToBoxAdapter(child: FilaPista(pista: r.actual!, alPulsar: r.alternar)),
            if (r.proximas.isNotEmpty) ...[
              SliverToBoxAdapter(child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 14, 8, 4),
                child: Row(children: [
                  const Expanded(child: Text('Siguiente en tu cola', style: estiloTituloSeccion)),
                  TextButton(onPressed: r.vaciarProximas, child: const Text('Vaciar', style: TextStyle(color: C.texto2))),
                ]),
              )),
              SliverReorderableList(
                itemCount: r.proximas.length,
                onReorderItem: r.moverProxima,
                onReorderStart: (_) => Haptico.firme(),
                itemBuilder: (_, i) {
                  final p = r.proximas[i];
                  return ReorderableDelayedDragStartListener(
                    key: ValueKey('prox-$i-${p['clave']}'),
                    index: i,
                    child: Dismissible(
                      key: ValueKey('dis-$i-${p['clave']}'),
                      direction: DismissDirection.endToStart,
                      background: Container(color: C.error, alignment: Alignment.centerRight,
                          padding: const EdgeInsets.only(right: 20), child: const Icon(Icons.delete_outline_rounded)),
                      onDismissed: (_) {
                        Haptico.toque();
                        r.quitarProxima(i);
                        s.avisar('Quitada de la cola', deshacer: () => r.insertarProxima(i, p));
                      },
                      child: FilaPista(pista: p, alPulsar: () => r.saltarAProxima(i)),
                    ),
                  );
                },
              ),
            ],
            if (normales.isNotEmpty) ...[
              SliverToBoxAdapter(child: Padding(padding: const EdgeInsets.fromLTRB(20, 14, 20, 4),
                  child: Text('Siguiente de: ${r.contexto?['titulo'] ?? 'la cola'}', style: estiloTituloSeccion,
                      maxLines: 2))),
              SliverList.builder(itemCount: normales.length, itemBuilder: (_, k) {
                final i = normales[k];
                return FilaPista(pista: siguientes[i], alPulsar: () => r.saltarA(r.pos + 1 + i));
              }),
            ],
            if (auto.isNotEmpty) ...[
              const SliverToBoxAdapter(child: Padding(padding: EdgeInsets.fromLTRB(20, 14, 20, 0),
                  child: Text('Reproducción automática', style: estiloTituloSeccion))),
              const SliverToBoxAdapter(child: Padding(padding: EdgeInsets.fromLTRB(20, 2, 20, 6),
                  child: Text('Canciones parecidas para que la música no pare.', style: estiloSecundario))),
              SliverList.builder(itemCount: auto.length, itemBuilder: (_, k) {
                final i = auto[k];
                return FilaPista(pista: siguientes[i], alPulsar: () => r.saltarA(r.pos + 1 + i));
              }),
            ],
            // por encima del indicador de inicio del iPhone
            SliverToBoxAdapter(child: SizedBox(height: 30 + MediaQuery.paddingOf(context).bottom)),
          ]);
        },
      ),
    );
  }
}

// ---------------------------------------------------------------- letra

final Map<String, Map<String, dynamic>> _cacheLetras = {};

Future<Map<String, dynamic>> _letraDe(Json p) async {
  final clave = '${p['clave']}';
  final hecho = _cacheLetras[clave];
  if (hecho != null) return hecho;
  final l = Map<String, dynamic>.from(await Catalogo.letras(p));
  _cacheLetras[clave] = l;
  return l;
}

List<(int, String)> _lineas(Map<String, dynamic> l) => [
      for (final x in (l['lineas'] is List ? l['lineas'] as List : const []))
        if (x is List && x.length >= 2)
          (x[0] is num ? (x[0] as num).toInt() : int.tryParse('${x[0]}') ?? 0, '${x[1]}')
    ];

class _TarjetaLetra extends StatefulWidget {
  const _TarjetaLetra({required this.pista, required this.color});
  final Json pista;
  final Color color;

  @override
  State<_TarjetaLetra> createState() => _TarjetaLetraState();
}

class _TarjetaLetraState extends State<_TarjetaLetra> {
  Map<String, dynamic>? _l;
  String _clave = '';

  void _cargar() {
    final clave = '${widget.pista['clave']}';
    if (clave == _clave) return;
    _clave = clave;
    _l = null;
    _letraDe(widget.pista).then((l) {
      if (mounted && _clave == clave) setState(() => _l = l);
    }).catchError((_) {
      if (mounted && _clave == clave) setState(() => _l = {'texto': '', 'lineas': []});
    });
  }

  @override
  Widget build(BuildContext context) {
    _cargar();
    final l = _l;
    final fondo = HSVColor.fromColor(widget.color).withValue(0.62).withSaturation(0.55).toColor();
    final abajo = Color.lerp(fondo, Colors.black, 0.22)!;
    // el color de la tarjeta justo donde empieza la letra (34 de 280 px)
    final arriba = Color.lerp(fondo, abajo, 34 / 280)!;
    final hay = l != null && ((l['lineas'] as List? ?? []).isNotEmpty || '${l['texto'] ?? ''}'.isNotEmpty);
    return GestureDetector(
      onTap: hay ? () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => LetraCompleta(pista: widget.pista, letra: l, color: fondo))) : null,
      child: Container(
        height: 280,
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 0),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [fondo, abajo],
          ),
          boxShadow: const [BoxShadow(color: Color(0x40000000), blurRadius: 18, offset: Offset(0, 8))],
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Text('Letra', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            const Spacer(),
            if (hay) const Icon(Icons.open_in_full_rounded, size: 18),
          ]),
          const SizedBox(height: 10),
          Expanded(
            child: l == null
                ? const Center(child: CircularProgressIndicator(color: Colors.white))
                : !hay
                    ? const Center(child: Text('No hay letra para esta canción.',
                        style: TextStyle(fontWeight: FontWeight.w700)))
                    : IgnorePointer(
                        // la letra se desvanece por arriba y por abajo en vez de cortarse
                        // (dos velos del color de la tarjeta: sin capas extra que componer)
                        child: Stack(fit: StackFit.expand, children: [
                          _VistaLetra(letra: l, compacta: true),
                          Positioned(left: 0, right: 0, top: 0, height: 14,
                              child: DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
                                  begin: Alignment.topCenter, end: Alignment.bottomCenter,
                                  colors: [arriba, arriba.withValues(alpha: 0)])))),
                          Positioned(left: 0, right: 0, bottom: 0, height: 46,
                              child: DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
                                  begin: Alignment.topCenter, end: Alignment.bottomCenter,
                                  colors: [abajo.withValues(alpha: 0), abajo])))),
                        ]),
                      ),
          ),
        ]),
      ),
    );
  }
}

class LetraCompleta extends StatelessWidget {
  const LetraCompleta({super.key, required this.pista, required this.letra, required this.color});
  final Json pista;
  final Map<String, dynamic>? letra;
  final Color color;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: color,
        appBar: AppBar(
          backgroundColor: color,
          title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${pista['titulo']}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
            Text('${pista['artista'] ?? ''}', style: const TextStyle(fontSize: 13, color: Color(0xCCFFFFFF))),
          ]),
        ),
        body: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 22),
          child: _VistaLetra(letra: letra ?? const {}, compacta: false),
        ),
      );
}

class _VistaLetra extends StatefulWidget {
  const _VistaLetra({required this.letra, required this.compacta});
  final Map<String, dynamic> letra;
  final bool compacta;

  @override
  State<_VistaLetra> createState() => _VistaLetraState();
}

class _VistaLetraState extends State<_VistaLetra> {
  // lo ya cantado queda blanco tenue; lo que viene, oscuro sobre el color
  static const _cantada = Color(0xB3FFFFFF);
  static const _porVenir = Color(0xB306070A);
  final _scroll = ScrollController();
  late List<(int, String)> _ls = _lineas(widget.letra);
  late List<GlobalKey> _llaves = List.generate(_ls.length, (_) => GlobalKey());
  int _actual = -1;
  Reproductor? _r;
  DateTime _toque = DateTime(2000);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_r == null) {
      _r = Caudal.leer(context).reproductor;
      _r!.posicion.addListener(_alAvanzar);
    }
  }

  @override
  void didUpdateWidget(covariant _VistaLetra old) {
    super.didUpdateWidget(old);
    if (!identical(old.letra, widget.letra)) {
      _ls = _lineas(widget.letra);
      _llaves = List.generate(_ls.length, (_) => GlobalKey());
      _actual = -1;
    }
  }

  @override
  void dispose() {
    _r?.posicion.removeListener(_alAvanzar);
    _scroll.dispose();
    super.dispose();
  }

  void _alAvanzar() {
    if (_ls.isEmpty) return;
    final ms = _r!.posicion.value.inMilliseconds + 250;
    var i = -1;
    for (var k = 0; k < _ls.length; k++) {
      if (_ls[k].$1 <= ms) {
        i = k;
      } else {
        break;
      }
    }
    if (i == _actual) return;
    setState(() => _actual = i);
    if (i >= 0 && _scroll.hasClients && DateTime.now().difference(_toque) > const Duration(seconds: 4)) {
      // solo se mueve ESTA lista: Scrollable.ensureVisible tambien moveria la
      // pagina del reproductor que la contiene, a cada linea
      final objeto = _llaves[i].currentContext?.findRenderObject();
      final posicion = _scroll.position;
      if (objeto != null && objeto.attached) {
        posicion.ensureVisible(objeto, alignment: 0.33, duration: const Duration(milliseconds: 420),
            curve: Curves.easeOutCubic);
      } else {
        // la linea aun no esta construida (se salto lejos): ir a ojo
        final destino = (i * (widget.compacta ? 40.0 : 48.0) - posicion.viewportDimension * 0.33)
            .clamp(posicion.minScrollExtent, posicion.maxScrollExtent);
        posicion.animateTo(destino, duration: const Duration(milliseconds: 420), curve: Curves.easeOutCubic);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_ls.isEmpty) {
      return SingleChildScrollView(
        child: Text('${widget.letra['texto'] ?? ''}',
            style: TextStyle(fontSize: widget.compacta ? 18 : 22, fontWeight: FontWeight.w800, height: 1.5)),
      );
    }
    return NotificationListener<UserScrollNotification>(
      onNotification: (_) {
        _toque = DateTime.now();
        return false;
      },
      child: ListView.builder(
        controller: _scroll,
        padding: EdgeInsets.only(bottom: widget.compacta ? 120 : 260),
        itemCount: _ls.length,
        itemBuilder: (_, i) {
          final estado = i == _actual ? 0 : (i < _actual ? -1 : 1);
          final texto = _ls[i].$2.trim().isEmpty ? '♪' : _ls[i].$2;
          final estilo = TextStyle(
            fontSize: widget.compacta ? 20 : 26,
            fontWeight: FontWeight.w800,
            height: 1.28,
            letterSpacing: -0.3,
            color: estado == 0 ? Colors.white : (estado < 0 ? _cantada : _porVenir),
          );
          Widget linea;
          if (estado == 0 && texto != '♪') {
            // la que suena se va llenando de blanco al cantarse
            final inicio = _ls[i].$1;
            final siguiente = i + 1 < _ls.length ? _ls[i + 1].$1 : inicio + 5000;
            final fin = inicio + (siguiente - inicio).clamp(600, 1500 + texto.length * 85);
            linea = LineaKaraoke(texto: texto, estilo: estilo, inicio: inicio, fin: fin, r: _r!,
                hecho: Colors.white, falta: _porVenir);
          } else {
            linea = AnimatedDefaultTextStyle(
              duration: const Duration(milliseconds: 260),
              style: estilo,
              child: Text(texto),
            );
          }
          return GestureDetector(
            key: _llaves[i],
            onTap: () => _r?.buscar(Duration(milliseconds: _ls[i].$1)),
            child: Padding(
              padding: EdgeInsets.symmetric(vertical: widget.compacta ? 6 : 8),
              // la que suena crece apenas; es solo pintura, no mueve las demas
              child: AnimatedScale(
                scale: estado == 0 ? 1 : 0.94,
                alignment: Alignment.centerLeft,
                duration: const Duration(milliseconds: 320),
                curve: Curves.easeOutCubic,
                child: AnimatedOpacity(
                  opacity: estado == 0 ? 1 : (estado < 0 ? 0.72 : 1),
                  duration: const Duration(milliseconds: 320),
                  child: linea,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
