import 'dart:async';
import 'dart:ui' as ui;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:media_kit_video/media_kit_video.dart';

import '../../nucleo/ajustes.dart';
import '../../nucleo/catalogo.dart';
import '../../nucleo/calidad_sonido.dart';
import '../../nucleo/coleccion.dart';
import '../../nucleo/estilo_reproductor.dart';
import '../../nucleo/fondo_app.dart';
import '../../nucleo/mascota_app.dart';
import '../../nucleo/premium.dart';
import '../../nucleo/premium_letras.dart';
import '../../nucleo/ritmo.dart';
import '../../nucleo/ritmo_fondo.dart';
import '../../nucleo/letras_cache.dart';
import '../../nucleo/pantalla.dart';
import '../../nucleo/traductor.dart';
import '../../reproduccion/frenos.dart';
import '../../reproduccion/jugador.dart';
import '../../reproduccion/reproductor.dart';
import '../comunes.dart';
import '../escenarios/catalogo.dart';
import '../escenarios/escenario_fondo.dart';
import '../plataforma.dart';
import '../reproductor/animaciones.dart';
import '../reproductor/barra_progreso.dart';
import '../reproductor/compartir_cancion.dart';
import '../reproductor/estilos_portada.dart';
import '../reproductor/fondo_ambiente.dart';
import '../reproductor/insignia_calidad.dart';
import '../reproductor/paleta_portada.dart';
import '../reproductor/personalizar_hoja.dart';
import '../reproductor/letra_aspecto.dart';
import '../reproductor/portada_deslizable.dart';
import '../reproductor/tarjetas_compartir.dart';
import '../reproductor/vinilo.dart';
import '../premium/tarjetas_del_dia.dart' show MenuMasEscucha;
import '../servicios.dart';
import '../cast_boton.dart';
import '../tema.dart';
import 'cola_hoja.dart';
import 'compartir_letra.dart';
import 'karaoke_pagina.dart';
import 'mezclador_ajustes.dart';
import 'mezclador_pagina.dart';
import 'sonido.dart';

class ReproductorPagina extends StatefulWidget {
  const ReproductorPagina({super.key});

  @override
  State<ReproductorPagina> createState() => _ReproductorPaginaState();
}

class _ReproductorPaginaState extends State<ReproductorPagina> with SingleTickerProviderStateMixin {
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

  // el estilo de la pantalla (Clasico, Vinilo, Casete, Neon, Flotante) y los colores de la
  // caratula; con el vinilo la pantalla se queda encendida mientras suena (en pausa el
  // sistema puede apagarla como siempre)
  final _prefs = PreferenciasReproductor.i;
  bool get _vinilo => _prefs.estiloEfectivo == EstiloReproductor.vinilo;
  Reproductor? _rPantalla;
  bool? _pantallaPedida;

  // la paleta que se ve (animada) y de donde sale
  late final AnimationController _anim =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 700))..addListener(_pasoPaleta);
  final _vista = ValueNotifier<PaletaPortada>(PaletaPortada.neutra);
  PaletaPortada _desde = PaletaPortada.neutra, _hasta = PaletaPortada.neutra;
  PaletaPortada? _paleta;
  String _urlPaleta = '';
  bool _vistaLista = false;

  @override
  void initState() {
    super.initState();
    _prefs.addListener(_alCambiarPrefs);
    _prefs.cargar();
  }

  void _alCambiarPrefs() {
    if (!mounted) return;
    setState(() {});
    _revisarPantalla();
  }

  void _pasoPaleta() =>
      _vista.value = PaletaPortada.lerp(_desde, _hasta, Curves.easeInOut.transform(_anim.value));

  /// La paleta que toca mostrar: la de la caratula (donadores) o el color de siempre.
  PaletaPortada _objetivo() {
    final p = _paleta;
    if (_prefs.coloresActivos && p != null) return p;
    return PaletaPortada(fondo: _color, acento: C.acento, contraste: Color.lerp(_color, C.fondo, 0.5)!);
  }

  /// Lleva la paleta que se ve hacia la que toca, con una transicion suave (sin ella con
  /// "quitar animaciones" o el modo ligero). Nunca se llama durante un build.
  void _irA(PaletaPortada p) {
    if (!mounted || (_vistaLista && p == _hasta)) return;
    final animar = _vistaLista && !(MediaQuery.maybeDisableAnimationsOf(context) ?? false);
    _vistaLista = true;
    _desde = _vista.value;
    _hasta = p;
    if (animar) {
      _anim.forward(from: 0);
    } else {
      _anim.stop();
      _vista.value = p;
    }
  }

  /// En cada build: si lo que toca mostrar cambio, se lleva hacia alli despues del fotograma.
  void _sincronizarPaleta(String url) {
    if (url != _urlPaleta) {
      _urlPaleta = url;
      _paleta = paletaEnCache(url);
      if (_prefs.coloresActivos && _paleta == null) {
        paletaDe(url).then((p) {
          if (mounted && _urlPaleta == url) {
            _paleta = p;
            _irA(_objetivo());
          }
        });
      }
    } else if (_prefs.coloresActivos && _paleta == null) {
      // se encendieron los colores con esta cancion ya puesta
      paletaDe(url).then((p) {
        if (mounted && _urlPaleta == url) {
          _paleta = p;
          _irA(_objetivo());
        }
      });
    }
    final obj = _objetivo();
    if (!_vistaLista) {
      _vistaLista = true;
      _desde = _hasta = obj;
      _vista.value = obj;
    } else if (obj != _hasta) {
      scheduleMicrotask(() => _irA(_objetivo()));
    }
  }

  /// Pantalla encendida solo con el vinilo puesto y la musica sonando (o
  /// cargando la siguiente, para no soltarla entre canciones).
  void _revisarPantalla() {
    final e = _rPantalla?.estado;
    final quiere = _vinilo && (e == EstadoRepro.sonando || e == EstadoRepro.cargando);
    if (quiere == _pantallaPedida) return;
    _pantallaPedida = quiere;
    PantallaEncendida.mantener(quiere);
  }

  // el contenido aparece un poco despues de que la portada empieza a volar
  Animation<double>? _ruta;
  Animation<double> _entrada = kAlwaysCompleteAnimation;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final r = Caudal.of(context).reproductor;
    if (!identical(r, _rPantalla)) {
      _rPantalla?.removeListener(_revisarPantalla);
      _rPantalla = r..addListener(_revisarPantalla);
      _revisarPantalla();
    }
    final ruta = ModalRoute.of(context)?.animation;
    if (ruta != null && !identical(ruta, _ruta)) {
      _ruta = ruta;
      _entrada = ruta.drive(CurveTween(curve: const Interval(0.25, 1, curve: Curves.easeOut)));
    }
  }

  @override
  void dispose() {
    _rPantalla?.removeListener(_revisarPantalla);
    _prefs.removeListener(_alCambiarPrefs);
    _anim.dispose();
    _vista.dispose();
    PantallaEncendida.mantener(false); // al salir de la pantalla del reproductor, el sistema vuelve a apagarla
    _arrastre.dispose();
    super.dispose();
  }

  /// El escenario elegido para el fondo del reproductor. Solo con beneficios (si no, null: fondo normal).
  EscenarioDef? _escenarioDelReproductor(Ajustes a) {
    final clave = a.texto('escenario_reproductor');
    if (clave.isEmpty || !Premium.i.activo) return null;
    return escenarioPorClave(clave);
  }

  /// El ritmo de la cancion si Caudal ya lo conoce (sin analizar nada ni gastar datos).
  AnalisisRitmo? _ritmoDe(Servicios s, String clave) {
    try {
      return RitmoFondo.para(s.coleccion).de(clave);
    } catch (_) {
      return null;
    }
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
          listenable: Listenable.merge([r, s.coleccion, s.ajustes, Premium.i]),
          builder: (context, _) {
            final p = r.actual;
            if (p == null) {
              // se detuvo la musica: no hay nada que mostrar
              WidgetsBinding.instance.addPostFrameCallback((_) => _cerrar());
              return const SizedBox.shrink();
            }
            final url = '${p['miniatura'] ?? ''}';
            _colorDe(url);
            _sincronizarPaleta(url);
            final estilo = _prefs.estiloEfectivo;
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
            final escenario = _escenarioDelReproductor(s.ajustes);
            return Stack(children: [
              // ---- modo ambiente: la portada desenfocada, moviendose despacio (o un escenario elegido)
              Positioned.fill(
                child: ValueListenableBuilder<PaletaPortada>(
                  valueListenable: _vista,
                  builder: (_, pal, _) => Stack(fit: StackFit.expand, children: [
                    if (escenario != null) ...[
                      // sin espectro de audio en la app: el escenario respira solo (bandas: null)
                      EscenarioFondo(clave: escenario.clave, bandas: null),
                      // velo oscuro suave abajo para que se lean los controles
                      IgnorePointer(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [Colors.black.withValues(alpha: 0), Colors.black.withValues(alpha: 0.55)],
                              stops: const [0.45, 1],
                            ),
                          ),
                        ),
                      ),
                    ] else
                      FondoAmbiente(url: url, color: pal.fondo, enMovimiento: !video && r.estado == EstadoRepro.sonando),
                    // con los colores de la caratula, el fondo se funde hacia su segundo tono
                    if (escenario == null && _prefs.coloresActivos)
                      IgnorePointer(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [pal.contraste.withValues(alpha: 0), pal.contraste.withValues(alpha: 0.38)],
                            ),
                          ),
                        ),
                      ),
                  ]),
                ),
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
                        // enviar a una tele o altavoz (no aparece si no hay Cast)
                        CastBoton(control: r.cast),
                        // una imagen bonita de lo que suena para estados, historias y chats
                        IconButton(
                          tooltip: 'Compartir',
                          icon: const Icon(Icons.ios_share_rounded),
                          onPressed: () => _compartirCancion(context, r, p),
                        ),
                        if (!Jugador.esWeb)
                          IconButton(
                            tooltip: 'Personalizar el reproductor',
                            icon: Icon(Icons.style_rounded,
                                color: estilo != EstiloReproductor.clasico || _prefs.coloresActivos ? C.acento : null),
                            onPressed: () => mostrarPersonalizarReproductor(context),
                          ),
                        IconButton(icon: const Icon(Icons.more_vert_rounded), onPressed: () => s.hojaPista(context, p)),
                      ]),
                    ),
                    const SizedBox(height: 14),
                    // ---- portada o video
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 22),
                      child: Jugador.esWeb
                          // web: aqui va el video de YouTube (el recuadro se coloca encima)
                          ? const _HuecoVideoWeb()
                          : video
                          ? _VideoEnLinea(r: r)
                          : estilo != EstiloReproductor.clasico
                          ? _PortadaDeEstilo(
                              estilo: estilo,
                              url: url,
                              r: r,
                              vista: _vista,
                              lado: ladoPortadaGrande(ancho),
                              ritmoDe: () => _ritmoDe(s, clave),
                              alDobleToque: () => _meGustaDobleToque(s, p),
                              alSiguiente: () => _siguiente(r),
                              alAnterior: () => _anterior(r),
                            )
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
                                  child: Row(children: [
                                    Flexible(
                                      child: Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(fontSize: 15, color: Color(0xCCFFFFFF))),
                                    ),
                                    // la calidad de lo que suena: codec y tasa, discreta y para todos
                                    if (calidadDe(r.fuente, enVideo: video) case final cal?) ...[
                                      const SizedBox(width: 8),
                                      ValueListenableBuilder<PaletaPortada>(
                                        valueListenable: _vista,
                                        builder: (_, pal, _) => InsigniaCalidad(calidad: cal, color: pal.acento),
                                      ),
                                    ],
                                  ]),
                                ),
                              ]),
                            ),
                          ),
                        ),
                        CorazonAnimado(gusta: gusta, tamano: 28, alPulsar: () => s.alternarMeGusta(p)),
                        const MenuMasEscucha(), // Modo auto, modos de escucha, ¿qué canción era?, ecualizador adaptable
                      ]),
                    ),
                    const SizedBox(height: 4),
                    // ---- progreso
                    Padding(padding: const EdgeInsets.symmetric(horizontal: 10),
                        child: RepaintBoundary(child: BarraProgreso(r: r))),
                    // ---- controles
                    ValueListenableBuilder<PaletaPortada>(
                      valueListenable: _vista,
                      builder: (_, pal, _) => Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                        IconButton(
                          icon: Icon(Icons.shuffle_rounded, color: r.aleatorio ? pal.acento : C.texto),
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
                              color: r.repetir == 'no' ? C.texto : pal.acento),
                          onPressed: () async {
                            Haptico.seleccion();
                            final m = await r.ciclarRepetir();
                            s.avisar({'no': 'Repetir desactivado', 'todo': 'Repetir toda la cola',
                              'una': 'Repetir esta canción'}[m]!);
                          },
                        ),
                      ]),
                    ),
                    ),
                    // ---- extras
                    ValueListenableBuilder<PaletaPortada>(
                      valueListenable: _vista,
                      builder: (_, pal, _) => Padding(
                      padding: const EdgeInsets.fromLTRB(14, 4, 14, 0),
                      child: Row(children: [
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
                          icon: Icon(Icons.bedtime_outlined, color: r.restanteApagado != null ? pal.acento : C.texto),
                          onPressed: () => _temporizador(context, r),
                        ),
                        ListenableBuilder(
                          listenable: s.ajustes,
                          builder: (_, _) => IconButton(
                            tooltip: 'Mezcla DJ',
                            icon: Icon(Icons.album_rounded, color: s.ajustes.sino('mezcla_dj') ? pal.acento : C.texto),
                            onPressed: () => mostrarMezclaDj(context, alAbrirMezclador: () {
                              // la mesa se abre en la pestaña: antes se cierra el reproductor grande
                              Navigator.of(context, rootNavigator: true).maybePop();
                              s.abrirEnPestana?.call(const MezcladorPagina());
                            }),
                          ),
                        ),
                        IconButton(
                          tooltip: 'Sonido',
                          icon: Icon(Icons.graphic_eq_rounded,
                              color: s.ajustes.entero('super_volumen') > 0 || s.ajustes.sino('ecualizador') ? pal.acento : C.texto),
                          onPressed: () => mostrarSonido(context),
                        ),
                        IconButton(
                          tooltip: 'Cola',
                          icon: const Icon(Icons.queue_music_rounded),
                          onPressed: () => _cola(context),
                        ),
                      ]),
                    ),
                    ),
                    const SizedBox(height: 16),
                    // ---- letra
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      child: ValueListenableBuilder<PaletaPortada>(
                        valueListenable: _vista,
                        builder: (_, pal, _) => _TarjetaLetra(pista: p, color: pal.fondo),
                      ),
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

  /// Abre «Compartir» con lo que suena ahora: el momento, la calidad, el verso que se canta,
  /// los colores de la carátula (aunque el reproductor no los use) y la mascota elegida.
  void _compartirCancion(BuildContext context, Reproductor r, Json p) {
    final url = '${p['miniatura'] ?? ''}';
    final ctx = r.contexto;
    final calidad = calidadDe(r.fuente, enVideo: r.modo == 'video')?.etiqueta;
    final posicion = r.posicion.value;
    var duracion = r.duracion.value;
    if (duracion <= Duration.zero) duracion = Duration(seconds: (p['duracion'] as num?)?.toInt() ?? 0);
    final mascota = MascotaApp.i.activa ? MascotaApp.i.actual : null;
    // el sello de los diseños exclusivos (solo se lee el estado de siempre)
    final sello = Premium.i.estado.tipo == 'fundador' || FondoApp.i.titulo.contains('Fundador') ? 'Fundador' : 'Donador';

    Future<DatosCompartir> preparar() async {
      final (paleta, (verso, siguiente), caratula) = await (
        (paletaEnCache(url) != null ? Future.value(paletaEnCache(url)!) : paletaDe(url))
            .timeout(const Duration(seconds: 4), onTimeout: () => _vista.value),
        _versoQueSuena(p, posicion),
        _caratulaGrande(context, url),
      ).wait;
      // la tarjeta «Escenario»: el escenario elegido, o el samurai (solo con beneficios)
      ui.Image? escenarioImg;
      if (Premium.i.activo) {
        final elegido = Caudal.leer(context).ajustes.texto('escenario_reproductor');
        final clave = escenarioPorClave(elegido) != null ? elegido : 'samurai';
        try {
          escenarioImg = await EscenarioFondo.capturar(clave, const Size(1080, 1920));
        } catch (_) {
          escenarioImg = null;
        }
      }
      return DatosCompartir(
        escenario: escenarioImg,
        titulo: '${p['titulo'] ?? ''}',
        artista: '${p['artista'] ?? ''}'.trim(),
        caratula: caratula,
        paleta: paleta,
        posicion: posicion,
        duracion: duracion,
        calidad: calidad,
        verso: verso,
        versoSiguiente: siguiente,
        contexto: ctx == null ? null : '${ctx['titulo'] ?? ''}',
        mascota: mascota,
        sello: sello,
      );
    }

    mostrarCompartirCancion(context, datos: preparar());
  }

  /// La línea de la letra que se canta en [posicion] y la siguiente. Sin tiempos, las dos
  /// primeras con texto. Sin letra (o si no llega), nada.
  Future<(String?, String?)> _versoQueSuena(Json p, Duration posicion) async {
    try {
      final l = await _letraDe(p).timeout(const Duration(seconds: 4));
      bool util(String x) => x.trim().isNotEmpty && x.trim() != '♪';
      final con = _lineas(l);
      final textos = con.isNotEmpty ? [for (final x in con) x.$2] : '${l['texto'] ?? ''}'.split('\n');
      var i = 0;
      if (con.isNotEmpty) {
        final ms = posicion.inMilliseconds + 250 + _desfaseDe('${p['clave']}');
        for (var k = 0; k < con.length; k++) {
          if (con[k].$1 <= ms) i = k;
        }
      }
      while (i < textos.length && !util(textos[i])) {
        i++;
      }
      if (i >= textos.length) return (null, null);
      var j = i + 1;
      while (j < textos.length && !util(textos[j])) {
        j++;
      }
      return (textos[i].trim(), j < textos.length ? textos[j].trim() : null);
    } catch (_) {
      return (null, null);
    }
  }

  /// La carátula en grande (las de YouTube Music se pueden pedir a más resolución). Si la
  /// grande no llega pronto, se usa la de siempre.
  Future<String> _caratulaGrande(BuildContext context, String url) async {
    final grande = Catalogo.agrandarMiniatura(url, 1200);
    if (grande == url || !grande.startsWith('http')) return url;
    var bien = true;
    try {
      await precacheImage(CachedNetworkImageProvider(grande), context, onError: (_, _) => bien = false)
          .timeout(const Duration(seconds: 4));
    } catch (_) {
      bien = false;
    }
    return bien ? grande : url;
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
            leading: Icon(Icons.timer_off_outlined, color: C.acento),
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
        builder: (_) => const HojaCola(),
      );
}

/// La portada del reproductor en un estilo de donadores (Vinilo, Casete, Neon o Flotante), con los
/// mismos gestos que la clasica: doble toque para me gusta y deslizar para cambiar de cancion.
class _PortadaDeEstilo extends StatelessWidget {
  const _PortadaDeEstilo({
    required this.estilo,
    required this.url,
    required this.r,
    required this.vista,
    required this.lado,
    required this.ritmoDe,
    required this.alDobleToque,
    required this.alSiguiente,
    required this.alAnterior,
  });

  final EstiloReproductor estilo;
  final String url;
  final Reproductor r;
  final ValueListenable<PaletaPortada> vista;
  final double lado;
  final AnalisisRitmo? Function() ritmoDe;
  final VoidCallback alDobleToque, alSiguiente, alAnterior;

  @override
  Widget build(BuildContext context) {
    final sonando = r.estado == EstadoRepro.sonando;
    final Widget c = ValueListenableBuilder<PaletaPortada>(
      valueListenable: vista,
      builder: (_, pal, _) => switch (estilo) {
        EstiloReproductor.vinilo => VinilVista(url: url, color: pal.fondo, sonando: sonando, lado: lado),
        EstiloReproductor.casete => CaseteVista(url: url, color: pal.fondo, r: r, sonando: sonando, lado: lado),
        EstiloReproductor.neon => NeonVista(
            url: url,
            luz: brillante(pal.acento),
            luz2: colorSecundarioNeon(pal.acento, pal.contraste),
            sonando: sonando,
            lado: lado,
            ritmo: ritmoDe()),
        EstiloReproductor.flotante =>
          FlotanteVista(url: url, color: pal.acento, r: r, sonando: sonando, lado: lado, ritmoDe: ritmoDe),
        EstiloReproductor.clasico => const SizedBox.shrink(),
      },
    );
    return Center(
      child: GestureDetector(
        onDoubleTap: alDobleToque,
        onHorizontalDragEnd: (d) {
          final v = d.primaryVelocity ?? 0;
          if (v < -300) alSiguiente();
          if (v > 300) alAnterior();
        },
        child: c,
      ),
    );
  }
}

/// El botoncito del modo karaoke (donadores). Sin los beneficios avisa de que es de donadores.
class BotonKaraoke extends StatelessWidget {
  const BotonKaraoke({super.key, required this.pista, required this.letra, this.grande = false});

  final Json pista;
  final Map<String, dynamic>? letra;
  final bool grande;

  @override
  Widget build(BuildContext context) {
    void abrir() {
      if (!esPremiumLetras()) {
        Caudal.leer(context).avisar('El modo karaoke es para donadores de Caudal');
        return;
      }
      KaraokePagina.abrir(context, pista, letra: letra);
    }

    if (grande) {
      return IconButton(tooltip: 'Modo karaoke', icon: const Icon(Icons.mic_external_on_rounded), onPressed: abrir);
    }
    return Semantics(
      button: true,
      label: 'Modo karaoke',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: abrir,
        child: const Padding(padding: EdgeInsets.all(4), child: Icon(Icons.mic_external_on_rounded, size: 20)),
      ),
    );
  }
}

/// Lo que usa el modo karaoke: la letra (con su cache), sus lineas con tiempos y el desfase
/// que dejo el boton «Sincronia».
Future<Map<String, dynamic>> letraDeCancion(Json p) => _letraDe(p);
List<(int, String)> lineasDeLetra(Map<String, dynamic> l) => _lineas(l);
int desfaseDeLetra(String clave) => _desfaseDe(clave);
Listenable get avisoDesfaseLetra => _desfaseCambio;

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
                  ? Padding(key: ValueKey('cargando'), padding: EdgeInsets.all(22),
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
  Widget build(BuildContext context) => r.pantalla == null
      // web: el video es el recuadro de YouTube de la esquina
      ? const _VideoWeb()
      : ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: AspectRatio(
          aspectRatio: 16 / 9,
          child: ColoredBox(
            color: Colors.black,
            child: MaterialVideoControlsTheme(
              normal: MaterialVideoControlsThemeData(
                seekBarThumbColor: C.acento, seekBarPositionColor: C.acento,
                buttonBarButtonColor: Colors.white, topButtonBar: [],
              ),
              fullscreen: MaterialVideoControlsThemeData(
                seekBarThumbColor: C.acento, seekBarPositionColor: C.acento,
              ),
              // al salir de la app no se pausa: pasa a audio (Reproductor.segundoPlano)
              child: Video(controller: r.pantalla!, controls: MaterialVideoControls,
                  fill: Colors.black, pauseUponEnteringBackgroundMode: false),
            ),
          ),
        ),
      );
}

// ---------------------------------------------------------------- letra

final Map<String, Map<String, dynamic>> _cacheLetras = {};

/// Cuánto se adelanta (+) o se atrasa (-) la letra de cada canción, en ms. Lo mueve
/// el botón «Sincronía» cuando una letra llega corrida; vale mientras la app está abierta.
final Map<String, int> _desfasesLetra = {};
class _AvisoDesfase extends ChangeNotifier {
  void avisar() => notifyListeners();
}

final _AvisoDesfase _desfaseCambio = _AvisoDesfase();
int _desfaseDe(String clave) => _desfasesLetra[clave] ?? 0;

Future<Map<String, dynamic>> _letraDe(Json p) async {
  final clave = '${p['clave']}';
  final hecho = _cacheLetras[clave];
  if (hecho != null) return hecho;
  final l = Map<String, dynamic>.from(await Catalogo.letras(p));
  final vacia = (l['lineas'] as List? ?? const []).isEmpty && '${l['texto'] ?? ''}'.isEmpty;
  // una letra vacía puede ser un fallo de red: no se guarda, se vuelve a intentar
  if (!vacia) {
    _cacheLetras[clave] = l;
    LetrasCache.i.guardar(clave, l); // también queda en el teléfono (búsqueda y pantalla de bloqueo)
  }
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
            if (hay) ...[
              BotonSincronia(clave: '${widget.pista['clave']}', compacto: true),
              const SizedBox(width: 6),
              const BotonTraducir(compacto: true),
              const SizedBox(width: 4),
              BotonKaraoke(pista: widget.pista, letra: l),
            ],
            if (hay) const SizedBox(width: 10),
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
                          _VistaLetra(letra: l, compacta: true, clave: '${widget.pista['clave']}'),
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

/// La letra a pantalla completa. Sigue a la canción que suena: si cambia de
/// canción con esta pantalla abierta, pasa a la letra de la nueva.
class LetraCompleta extends StatefulWidget {
  const LetraCompleta({super.key, required this.pista, required this.letra, required this.color});
  final Json pista;
  final Map<String, dynamic>? letra;
  final Color color;

  @override
  State<LetraCompleta> createState() => _LetraCompletaState();
}

class _LetraCompletaState extends State<LetraCompleta> {
  late Json _pista = widget.pista;
  Map<String, dynamic>? _letra;
  Reproductor? _r;

  @override
  void initState() {
    super.initState();
    _letra = widget.letra;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _r ??= Caudal.leer(context).reproductor..addListener(_cambioDeCancion);
  }

  @override
  void dispose() {
    _r?.removeListener(_cambioDeCancion);
    super.dispose();
  }

  void _cambioDeCancion() {
    final nueva = _r?.actual;
    if (nueva == null || '${nueva['clave']}' == '${_pista['clave']}') return;
    final clave = '${nueva['clave']}';
    setState(() {
      _pista = nueva;
      _letra = null; // cargando la letra de la canción nueva
    });
    _letraDe(nueva).then((l) {
      if (mounted && '${_pista['clave']}' == clave) setState(() => _letra = l);
    }).catchError((_) {
      if (mounted && '${_pista['clave']}' == clave) setState(() => _letra = const {'texto': '', 'lineas': []});
    });
  }

  /// Abre la hoja para elegir líneas y compartirlas como imagen (con la carátula) o como texto.
  void _compartir() {
    final l = _letra;
    if (l == null) return;
    final con = _lineas(l);
    final lineas = con.isNotEmpty ? [for (final x in con) x.$2] : '${l['texto'] ?? ''}'.split('\n');
    if (lineas.every((x) => x.trim().isEmpty)) return;
    // la línea que suena ahora, para que la tarjeta empiece por ella
    var actual = 0;
    if (con.isNotEmpty && _r != null) {
      final ms = _r!.posicion.value.inMilliseconds + 250;
      for (var k = 0; k < con.length; k++) {
        if (con[k].$1 <= ms) actual = k;
      }
    }
    compartirLetra(context, pista: _pista, lineas: lineas, color: widget.color, lineaActual: actual);
  }

  @override
  Widget build(BuildContext context) {
    final l = _letra;
    final hayLineas = l != null && (l['lineas'] as List? ?? const []).isNotEmpty;
    final hayTexto = l != null && '${l['texto'] ?? ''}'.isNotEmpty;
    return Scaffold(
      backgroundColor: widget.color,
      appBar: AppBar(
        backgroundColor: widget.color,
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${_pista['titulo']}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
          Text('${_pista['artista'] ?? ''}', style: const TextStyle(fontSize: 13, color: Color(0xCCFFFFFF))),
        ]),
        actions: [
          if (hayLineas || hayTexto)
            IconButton(
              tooltip: 'Compartir letra',
              onPressed: _compartir,
              icon: const Icon(Icons.ios_share_rounded),
            ),
          if (hayLineas) BotonKaraoke(pista: _pista, letra: l, grande: true),
          BotonSincronia(clave: '${_pista['clave']}'),
          const SizedBox(width: 8),
          const BotonTraducir(),
          const SizedBox(width: 12),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 22),
        child: l == null
            ? const Center(child: CircularProgressIndicator(color: Colors.white))
            : !hayLineas && !hayTexto
                ? const Center(
                    child: Text('No hay letra para esta canción.',
                        style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18)))
                : Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    if (!hayLineas)
                      const Padding(
                        padding: EdgeInsets.only(bottom: 8),
                        child: Text('Esta letra no trae tiempos, por eso no avanza sola.',
                            style: TextStyle(fontSize: 13, color: Color(0xCCFFFFFF))),
                      ),
                    Expanded(
                      child: _VistaLetra(
                          key: ValueKey('${_pista['clave']}'), letra: l, compacta: false, clave: '${_pista['clave']}',
                          acento: Color.lerp(widget.color, Colors.white, 0.4)),
                    ),
                  ]),
      ),
    );
  }
}

class _VistaLetra extends StatefulWidget {
  const _VistaLetra({super.key, required this.letra, required this.compacta, required this.clave, this.acento});
  final Map<String, dynamic> letra;
  final bool compacta;

  /// La cancion (para guardar su traduccion).
  final String clave;

  /// Color de brillo de la línea que suena (null = sin brillo de acento).
  final Color? acento;

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
  Ajustes? _ajustes;

  /// Traduccion de cada linea (de [_ls] o, sin tiempos, del texto plano).
  List<String> _trad = const [];
  String _pedida = '';

  List<String> get _textos => _ls.isNotEmpty
      ? [for (final l in _ls) l.$2]
      : '${widget.letra['texto'] ?? ''}'.split('\n');

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_r == null) {
      final s = Caudal.leer(context);
      _r = s.reproductor;
      _r!.posicion.addListener(_alAvanzar);
      _desfaseCambio.addListener(_alAvanzar);
      _ajustes = s.ajustes..addListener(_traducirSiToca);
      _traducirSiToca();
    }
  }

  void _traducirSiToca() {
    if (!mounted) return;
    final quiere = _ajustes?.sino('traducir_letra') ?? false;
    if (!quiere) {
      if (_trad.isNotEmpty) setState(() => _trad = const []);
      _pedida = '';
      return;
    }
    final clave = '${widget.clave}|${_ls.length}|${'${widget.letra['texto'] ?? ''}'.length}';
    if (clave == _pedida) return;
    _pedida = clave;
    Traductor.traducir(clave, _textos).then((t) {
      if (!mounted || _pedida != clave) return;
      setState(() => _trad = t == null || t.mismoIdioma ? const [] : t.lineas);
    });
  }

  String _traduccionDe(int i) => i < _trad.length ? _trad[i] : '';

  /// La traduccion bajo la linea, mas pequena y del mismo tono.
  Widget _conTraduccion(Widget linea, int i, Color color) {
    final t = _traduccionDe(i);
    if (t.isEmpty) return linea;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
      linea,
      const SizedBox(height: 2),
      AnimatedDefaultTextStyle(
        duration: const Duration(milliseconds: 260),
        style: TextStyle(fontSize: widget.compacta ? 14 : 17, fontWeight: FontWeight.w600, height: 1.25,
            color: color.withValues(alpha: color.a * 0.78)),
        child: Text(t),
      ),
    ]);
  }

  @override
  void didUpdateWidget(covariant _VistaLetra old) {
    super.didUpdateWidget(old);
    if (!identical(old.letra, widget.letra)) {
      _ls = _lineas(widget.letra);
      _llaves = List.generate(_ls.length, (_) => GlobalKey());
      _actual = -1;
      _trad = const [];
      _traducirSiToca();
    }
  }

  @override
  void dispose() {
    _r?.posicion.removeListener(_alAvanzar);
    _desfaseCambio.removeListener(_alAvanzar);
    _ajustes?.removeListener(_traducirSiToca);
    _scroll.dispose();
    super.dispose();
  }

  void _alAvanzar() {
    if (_ls.isEmpty) return;
    // la posicion llega cada ~200 ms: medio paso mas de adelanto para que la
    // linea cambie, de media, en el mismo instante que antes
    final ms = _r!.posicion.value.inMilliseconds + 250 + pasoPosicion.inMilliseconds ~/ 2 + _desfaseDe(widget.clave);
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
  Widget build(BuildContext context) => ValueListenableBuilder<LetraAspecto>(
        valueListenable: LetraAspecto.actual,
        builder: (context, aspecto, _) => _construir(context, aspecto),
      );

  Widget _construir(BuildContext context, LetraAspecto aspecto) {
    if (_ls.isEmpty) {
      final estilo = TextStyle(fontSize: widget.compacta ? 18 : 22, fontWeight: FontWeight.w800, height: 1.5);
      if (_trad.isEmpty) {
        return SingleChildScrollView(
            child: TextoLetraPlano(aspecto: aspecto, texto: '${widget.letra['texto'] ?? ''}', estilo: estilo));
      }
      final textos = _textos;
      return SingleChildScrollView(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          for (var i = 0; i < textos.length; i++)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: _conTraduccion(
                  TextoLetraPlano(aspecto: aspecto, texto: textos[i], estilo: estilo), i, Colors.white),
            ),
        ]),
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
            linea = LineaLetraActiva(aspecto: aspecto, texto: texto, estilo: estilo, inicio: inicio, fin: fin,
                r: _r!, porVenir: _porVenir, acento: widget.acento);
          } else {
            // el color de cada estado (cantada / por venir / activa) se anima como antes, 260 ms
            linea = LineaLetra(aspecto: aspecto, texto: texto, estilo: estilo, activa: estado == 0,
                acento: widget.acento);
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
                  child: _conTraduccion(linea, i, estilo.color ?? Colors.white),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

/// «Sincronía»: si la letra llega adelantada o atrasada, se corrige a mano de medio en medio segundo.
class BotonSincronia extends StatelessWidget {
  const BotonSincronia({super.key, required this.clave, this.compacto = false});
  final String clave;
  final bool compacto;

  void _abrir(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => ListenableBuilder(
        listenable: _desfaseCambio,
        builder: (ctx, _) {
          final ms = _desfaseDe(clave);
          void mover(int d) {
            final n = (ms + d).clamp(-10000, 10000);
            if (n == 0) {
              _desfasesLetra.remove(clave);
            } else {
              _desfasesLetra[clave] = n;
            }
            _desfaseCambio.avisar();
          }

          return SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 18),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Sincronía de la letra', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
                const SizedBox(height: 4),
                const Text('Si la letra va por delante de la voz, atrásala. Si va por detrás, adelántala.',
                    style: estiloSecundario),
                const SizedBox(height: 14),
                Row(children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => mover(500),
                      icon: const Icon(Icons.fast_rewind_rounded),
                      label: const Text('Atrasar 0,5 s'),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    child: Text(ms == 0 ? 'Normal' : '${ms > 0 ? '+' : ''}${(ms / 1000).toStringAsFixed(1)} s',
                        style: const TextStyle(fontWeight: FontWeight.w900)),
                  ),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => mover(-500),
                      icon: const Icon(Icons.fast_forward_rounded),
                      label: const Text('Adelantar 0,5 s'),
                    ),
                  ),
                ]),
                if (ms != 0)
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(onPressed: () => mover(-ms), child: const Text('Volver a lo normal')),
                  ),
              ]),
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: _desfaseCambio,
        builder: (context, _) {
          final activo = _desfaseDe(clave) != 0;
          return Tooltip(
            message: 'Ajustar la sincronía de la letra',
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => _abrir(context),
              child: Container(
                padding: EdgeInsets.symmetric(horizontal: compacto ? 8 : 12, vertical: compacto ? 4 : 6),
                decoration: BoxDecoration(
                  color: activo ? Colors.white : Colors.white.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.av_timer_rounded, size: compacto ? 15 : 18,
                      color: activo ? const Color(0xFF06070A) : Colors.white),
                  const SizedBox(width: 5),
                  Text('Sincronía', style: TextStyle(fontSize: compacto ? 12 : 14, fontWeight: FontWeight.w800,
                      color: activo ? const Color(0xFF06070A) : Colors.white)),
                ]),
              ),
            ),
          );
        },
      );
}

/// Enciende o apaga la traduccion bajo la letra (se recuerda).
class BotonTraducir extends StatelessWidget {
  const BotonTraducir({super.key, this.compacto = false});
  final bool compacto;

  @override
  Widget build(BuildContext context) {
    final a = Caudal.of(context).ajustes;
    return ListenableBuilder(
      listenable: a,
      builder: (context, _) {
        final on = a.sino('traducir_letra');
        return Tooltip(
          message: on ? 'Quitar la traducción' : 'Traducir la letra',
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => a.poner('traducir_letra', !on),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: EdgeInsets.symmetric(horizontal: compacto ? 8 : 12, vertical: compacto ? 4 : 6),
              decoration: BoxDecoration(
                color: on ? Colors.white : Colors.white.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.translate_rounded, size: compacto ? 15 : 18,
                    color: on ? const Color(0xFF06070A) : Colors.white),
                const SizedBox(width: 5),
                Text('Traducir', style: TextStyle(fontSize: compacto ? 12 : 14, fontWeight: FontWeight.w800,
                    color: on ? const Color(0xFF06070A) : Colors.white)),
              ]),
            ),
          ),
        );
      },
    );
  }
}


/// En la web el video es el del reproductor de YouTube (el recuadro de la
/// esquina): aquí se agranda o se achica.
class _VideoWeb extends StatefulWidget {
  const _VideoWeb();

  @override
  State<_VideoWeb> createState() => _VideoWebState();
}

class _VideoWebState extends State<_VideoWeb> {
  bool _grande = false;

  @override
  void dispose() {
    LienzoVideoWeb.mostrarGrande(false);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AspectRatio(
        aspectRatio: 16 / 9,
        child: DecoratedBox(
          decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(12)),
          child: Center(
            child: FilledButton.icon(
              onPressed: () {
                setState(() => _grande = !_grande);
                LienzoVideoWeb.mostrarGrande(_grande);
              },
              icon: Icon(_grande ? Icons.close_fullscreen_rounded : Icons.open_in_full_rounded),
              label: Text(_grande ? 'Achicar el video' : 'Ver el video en grande'),
            ),
          ),
        ),
      );
}


/// El hueco donde se coloca el reproductor de YouTube en la web. Se mide cada
/// vez que se pinta (y al desplazar) para que el recuadro lo siga.
class _HuecoVideoWeb extends StatefulWidget {
  const _HuecoVideoWeb();

  @override
  State<_HuecoVideoWeb> createState() => _HuecoVideoWebState();
}

class _HuecoVideoWebState extends State<_HuecoVideoWeb> {
  final _llave = GlobalKey();
  ScrollPosition? _scroll;

  void _medir() {
    if (!mounted) return;
    final caja = _llave.currentContext?.findRenderObject() as RenderBox?;
    if (caja == null || !caja.attached) return;
    final o = caja.localToGlobal(Offset.zero);
    LienzoVideoWeb.colocar(o & caja.size);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _scroll?.removeListener(_medir);
    _scroll = Scrollable.maybeOf(context)?.position;
    _scroll?.addListener(_medir);
  }

  @override
  void dispose() {
    _scroll?.removeListener(_medir);
    LienzoVideoWeb.colocar(null);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) => _medir());
    return AspectRatio(
      key: _llave,
      aspectRatio: 16 / 9,
      child: DecoratedBox(
        decoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(10)),
      ),
    );
  }
}
