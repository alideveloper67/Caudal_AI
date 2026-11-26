import 'dart:async';
import 'dart:math' show min;
import 'dart:ui' as ui;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/foundation.dart' show ValueListenable, kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:media_kit_video/media_kit_video.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../nucleo/ajustes.dart';
import '../../nucleo/catalogo.dart';
import '../../nucleo/calidad_sonido.dart';
import '../../nucleo/coleccion.dart';
import '../../nucleo/estilo_reproductor.dart';
import '../../nucleo/fondo_app.dart';
import '../../nucleo/mascota_app.dart';
import '../../nucleo/musica_libre.dart';
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
import '../../reproduccion/sesion_medios.dart';
import '../comunes.dart';
import '../escenarios/catalogo.dart';
import '../escenarios/escenario_fondo.dart';
import '../menu_hoja.dart';
import '../plataforma.dart';
import '../reproductor/a_continuacion.dart';
import '../reproductor/animaciones.dart';
import '../reproductor/barra_progreso.dart';
import '../reproductor/compartir_cancion.dart';
import '../reproductor/despliegue.dart';
import '../reproductor/estilos_portada.dart';
import '../reproductor/fondo_ambiente.dart';
import '../reproductor/hueco_video_web.dart';
import '../reproductor/insignia_calidad.dart';
import '../reproductor/paleta_portada.dart';
import '../reproductor/personalizar_hoja.dart';
import '../reproductor/letra_aspecto.dart';
import '../reproductor/letra_correccion.dart';
import '../reproductor/selector_letra.dart';
import '../reproductor/portada_deslizable.dart';
import '../reproductor/tarjetas_compartir.dart';
import '../reproductor/vinilo.dart';
import '../premium/tarjetas_del_dia.dart' show MenuMasEscucha;
import '../servicios.dart';
import '../cast_boton.dart';
import '../tema.dart';
import 'compartir_letra.dart';
import 'karaoke_pagina.dart';
import 'mezclador_ajustes.dart';
import 'mezclador_pagina.dart';
import 'segundo_plano_hoja.dart';
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

  // el despliegue de lo que sigue: un solo desplazamiento, con dos paradas
  final _scroll = ScrollController();
  final _llaveArriba = GlobalKey(), _llaveControles = GlobalKey();
  double _altoCabecera = CabeceraCompacta.alto;
  // donde empezo el gesto: solo cierra el reproductor si empezo con todo recogido
  double _inicioGesto = 0;

  double _altoDe(GlobalKey k) {
    final caja = k.currentContext?.findRenderObject();
    return caja is RenderBox && caja.hasSize ? caja.size.height : 0;
  }

  // lo que miden la carátula y los controles se mira después de cada fotograma que los rehace
  double _valorPliegue = 0;
  double _pliegue() => _valorPliegue;

  void _medirPliegue() => WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        final a = _altoDe(_llaveArriba), b = _altoDe(_llaveControles);
        // recogidos fuera de la vista no se miden: vale lo último
        if (a > 0 && b > 0) _valorPliegue = (a + b - _altoCabecera).clamp(0.0, double.infinity);
      });

  void _desplegar(bool si) {
    if (!_scroll.hasClients) return;
    final destino = si ? _pliegue().clamp(0.0, _scroll.position.maxScrollExtent) : 0.0;
    if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) {
      _scroll.jumpTo(destino);
    } else {
      _scroll.animateTo(destino, duration: const Duration(milliseconds: 380), curve: Curves.easeOutCubic);
    }
  }

  // debajo de los controles: lo que sigue (false) o la letra (true); se recuerda
  static const _claveAbajo = 'reproductor_abajo_letra';
  static bool _letraAbajo = false;

  void _ponerAbajo(bool letra) {
    setState(() => _letraAbajo = letra);
    unawaited(SharedPreferences.getInstance().then((p) => p.setBool(_claveAbajo, letra)).catchError((_) => false));
  }

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
    SharedPreferences.getInstance().then((p) {
      final letra = p.getBool(_claveAbajo) ?? false;
      if (mounted && letra != _letraAbajo) setState(() => _letraAbajo = letra);
    }).catchError((_) {});
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
    _scroll.dispose();
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
    if (n.depth != 0 || n.metrics.axis != Axis.vertical) return false;
    if (n is ScrollStartNotification && n.dragDetails != null) _inicioGesto = n.metrics.pixels;
    // recoger la lista no cierra el reproductor en el mismo gesto
    if (_inicioGesto > 4 && _arrastre.value == 0) return false;
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
    final pantalla = MediaQuery.sizeOf(context);
    final ancho = pantalla.width;
    // en el navegador (PC o teléfono de lado) no cabe una portada tan ancha como la ventana
    // (y las tablets de lado, también en la app)
    final horizontal = ancho >= (kIsWeb ? 600 : 840) && ancho > pantalla.height;
    final altoLibre = pantalla.height - MediaQuery.paddingOf(context).vertical - 84;
    final lado = horizontal
        ? min(ladoPortadaGrande(ancho / 2), altoLibre).clamp(120.0, 620.0)
        : kIsWeb || ancho > 700 ? min(ladoPortadaGrande(ancho), 620.0) : ladoPortadaGrande(ancho);
    final anchoVideo = min(ladoPortadaGrande(ancho / 2), altoLibre * 16 / 9).clamp(200.0, 900.0);
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
            final video = r.modo == 'video';
            final conRecuadro = _conRecuadro(r);
            final escenario = _escenarioDelReproductor(s.ajustes);
            // en el teléfono, con la portada clásica, la carátula ocupa todo el ancho y se funde
            // con el fondo; los demás estilos, el video y las pantallas anchas la llevan en su marco
            final inmersivo = !horizontal && !conRecuadro && !video && estilo == EstiloReproductor.clasico &&
                escenario == null;
            // la carátula deja sitio a los controles y a las primeras canciones de lo que sigue
            final altoPortada = min(ancho, pantalla.height * (ancho > 600 ? 0.46 : 0.345)).clamp(170.0, 640.0);
            final arribaCompacta = inmersivo ? MediaQuery.paddingOf(context).top : 0.0;
            _altoCabecera = arribaCompacta + CabeceraCompacta.alto;
            final desplegable = !horizontal && !conRecuadro;
            _medirPliegue();
            // ---- cabecera
            final hayVideo = !kIsWeb && ('${p['video_id'] ?? ''}'.isNotEmpty || (p['archivo'] != null && p['es_audio'] != true));
            final cabecera = Padding(
                      padding: const EdgeInsets.fromLTRB(4, 4, 4, 0),
                      child: Row(children: [
                        IconButton(tooltip: 'Cerrar', icon: const Icon(Icons.keyboard_arrow_down_rounded, size: 32),
                            onPressed: _cerrar),
                        Expanded(
                          child: hayVideo
                              ? Center(child: FittedBox(fit: BoxFit.scaleDown, child: _CancionOVideo(r: r)))
                              : Text('${r.contexto?['titulo'] ?? ''}', textAlign: TextAlign.center, maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
                        ),
                        // enviar a una tele o altavoz (no aparece si no hay Cast)
                        CastBoton(control: r.cast),
                        if (!conRecuadro)
                          IconButton(
                            tooltip: 'Personalizar el reproductor',
                            icon: Icon(Icons.style_rounded,
                                color: estilo != EstiloReproductor.clasico || _prefs.coloresActivos ? C.acento : null),
                            onPressed: () => mostrarPersonalizarReproductor(context),
                          ),
                        IconButton(tooltip: 'Opciones', icon: const Icon(Icons.more_vert_rounded),
                            onPressed: () => s.hojaPista(context, p)),
                      ]),
                    );
            // ---- portada o video
            final portada = Padding(
                      padding: EdgeInsets.symmetric(horizontal: inmersivo ? 0 : 22),
                      child: conRecuadro
                          // web: aqui va el video de YouTube (el recuadro se coloca encima)
                          ? const HuecoVideoWeb()
                          : video
                          ? _VideoEnLinea(r: r)
                          : estilo != EstiloReproductor.clasico
                          ? _PortadaDeEstilo(
                              estilo: estilo,
                              url: url,
                              r: r,
                              vista: _vista,
                              lado: lado,
                              ritmoDe: () => _ritmoDe(s, clave),
                              alDobleToque: () => _meGustaDobleToque(s, p),
                              alSiguiente: () => _siguiente(r),
                              alAnterior: () => _anterior(r),
                            )
                          : PortadaDeslizable(
                              pista: p,
                              lado: inmersivo ? ancho : lado,
                              alto: inmersivo ? altoPortada : null,
                              direccion: _direccion,
                              alSiguiente: () => _siguiente(r),
                              alAnterior: () => _anterior(r),
                              alDobleToque: () => _meGustaDobleToque(s, p),
                            ),
                    );
            final tituloYCorazon =
                    // ---- titulo
                    Padding(
                      padding: const EdgeInsets.only(left: 22, right: 12),
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
                                    style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w800, letterSpacing: -0.5, height: 1.15)),
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
                                        builder: (_, pal, _) => GestureDetector(
                                          onTap: MusicaLibre.es(p) ? () => launchUrl(Uri.parse('${p['enlace']}')) : null,
                                          child: InsigniaCalidad(calidad: cal, color: pal.acento),
                                        ),
                                      ),
                                    ],
                                  ]),
                                ),
                              ]),
                            ),
                          ),
                        ),
                        CorazonAnimado(gusta: gusta, tamano: 30, alPulsar: () => s.alternarMeGusta(p)),
                      ]),
                    );
            final resto = <Widget>[
                    if (!inmersivo) tituloYCorazon,
                    const SizedBox(height: 6),
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
                          child: IconButton(iconSize: 46, icon: const Icon(Icons.skip_previous_rounded), onPressed: () {
                            Haptico.seleccion();
                            _anterior(r);
                          }),
                        ),
                        _BotonGrande(r: r, lado: ancho < 360 ? 68 : 82),
                        Hundible(
                          escala: 0.86,
                          child: IconButton(iconSize: 46, icon: const Icon(Icons.skip_next_rounded), onPressed: () {
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
                    // ---- acciones: en una fila que se pasa de lado
                    const SizedBox(height: 4),
                    ValueListenableBuilder<PaletaPortada>(
                      valueListenable: _vista,
                      builder: (_, pal, _) => SizedBox(
                        height: 46,
                        child: ListView(
                          scrollDirection: Axis.horizontal,
                          padding: const EdgeInsets.symmetric(horizontal: 20),
                          children: [
                            // una imagen bonita de lo que suena para estados, historias y chats
                            _Accion(icono: Icons.ios_share_rounded, texto: 'Compartir',
                                alPulsar: () => _compartirCancion(context, r, p)),
                            _Accion(icono: Icons.bedtime_outlined, texto: 'Temporizador',
                                color: r.restanteApagado != null ? pal.acento : null,
                                alPulsar: () => _temporizador(context, r)),
                            _Accion(icono: Icons.graphic_eq_rounded, texto: 'Sonido',
                                color: s.ajustes.entero('super_volumen') > 0 || s.ajustes.sino('ecualizador') ? pal.acento : null,
                                alPulsar: () => mostrarSonido(context)),
                            _Accion(icono: Icons.album_rounded, texto: 'Mezcla DJ',
                                color: s.ajustes.sino('mezcla_dj') ? pal.acento : null,
                                alPulsar: () => mostrarMezclaDj(context, alAbrirMezclador: () {
                                      // la mesa se abre en la pestaña: antes se cierra el reproductor grande
                                      Navigator.of(context, rootNavigator: true).maybePop();
                                      s.abrirEnPestana?.call(const MezcladorPagina());
                                    })),
                            if (Jugador.esWeb && SesionMedios.esTelefono)
                              _Accion(icono: Icons.phonelink_lock_rounded, texto: 'Segundo plano',
                                  alPulsar: () => mostrarSegundoPlano(context, p)),
                            const MenuMasEscucha(), // Modo auto, modos de escucha, ¿qué canción era?, ecualizador adaptable
                          ],
                        ),
                      ),
                    ),
                    if (desplegable)
                      AsaDespliegue(alPulsar: () => _desplegar(true))
                    else
                      const SizedBox(height: 12),
            ];
            final pestanas = PestanasReproductor(
                letra: _letraAbajo, detalle: '${r.contexto?['titulo'] ?? ''}', alCambiar: _ponerAbajo);
            // ---- lo que sigue o la letra
            final abajo = <Widget>[
              SliverToBoxAdapter(child: pestanas),
              if (_letraAbajo)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 8, 14, 0),
                    child: ValueListenableBuilder<PaletaPortada>(
                      valueListenable: _vista,
                      builder: (_, pal, _) => _TarjetaLetra(pista: p, color: pal.fondo,
                          alto: (pantalla.height * 0.5).clamp(280.0, 520.0)),
                    ),
                  ),
                )
              else
                ...sliversAContinuacion(context, s),
              SliverToBoxAdapter(child: SizedBox(height: 28 + MediaQuery.paddingOf(context).bottom)),
              // con pocas canciones también se puede desplegar entera
              if (desplegable) const SliverFillRemaining(hasScrollBody: false, child: SizedBox.shrink()),
            ];
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
                      FondoAmbiente(url: url, color: pal.fondo,
                          // con la carátula fundida encima se queda quieto: nada que recomponer en cada fotograma
                          enMovimiento: !inmersivo && !video && r.estado == EstadoRepro.sonando),
                    // lo que sigue se lee siempre, sea cual sea la carátula
                    if (escenario == null)
                      const IgnorePointer(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter,
                                colors: [Color(0x00000000), Color(0x99000000)], stops: [0.3, 0.85]),
                          ),
                        ),
                      ),
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
              // desplegada, la lista se lee sobre un fondo más oscuro
              if (desplegable)
                Positioned.fill(
                  child: IgnorePointer(
                    child: ListenableBuilder(
                      listenable: _scroll,
                      builder: (_, _) {
                        final p = _pliegue();
                        final t = !_scroll.hasClients || p < 40 ? 0.0 : (_scroll.offset / p).clamp(0.0, 1.0);
                        return t == 0 ? const SizedBox.shrink() : ColoredBox(color: Color.fromRGBO(0, 0, 0, 0.5 * t));
                      },
                    ),
                  ),
                ),
              Scaffold(
                backgroundColor: Colors.transparent,
                body: FadeTransition(
                  opacity: _entrada,
                  child: SafeArea(
                  top: !inmersivo,
                  bottom: false,
                  // en iOS rebota abajo, pero arriba el tiron llega a "bajar para cerrar"
                  child: horizontal
                      // ventana ancha o teléfono de lado: la portada a la izquierda y lo demás al lado
                      ? Column(children: [
                          cabecera,
                          Expanded(
                            child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                              Expanded(
                                child: Center(child: SizedBox(width: (conRecuadro ? anchoVideo : lado) + 44, child: portada)),
                              ),
                              Expanded(
                                child: CustomScrollView(slivers: [
                                  SliverToBoxAdapter(child: SizedBox(height: pantalla.height < 520 ? 0 : 24)),
                                  SliverToBoxAdapter(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: resto)),
                                  ...abajo,
                                ]),
                              ),
                            ]),
                          ),
                        ])
                      : conRecuadro
                          // web: el video de YouTube se queda a la vista mientras se mira lo que sigue
                          ? Column(children: [
                              cabecera,
                              const SizedBox(height: 10),
                              portada,
                              Expanded(
                                child: CustomScrollView(slivers: [
                                  SliverToBoxAdapter(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch,
                                      children: [const SizedBox(height: 16), ...resto])),
                                  ...abajo,
                                ]),
                              ),
                            ])
                          : Stack(children: [
                              CustomScrollView(
                              controller: _scroll,
                              physics: FisicaDespliegue(pliegue: _pliegue, parent: esIOS ? const RebotaSoloAbajo() : null),
                              slivers: [
                              SliverToBoxAdapter(
                                key: const ValueKey('arriba'),
                                child: KeyedSubtree(key: _llaveArriba, child: inmersivo
                                    ? Stack(children: [
                                        _Fundida(child: portada),
                                        // velo arriba para que se vean los botones sobre cualquier carátula
                                        const Positioned(left: 0, right: 0, top: 0, height: 120, child: IgnorePointer(
                                          child: DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
                                              begin: Alignment.topCenter, end: Alignment.bottomCenter,
                                              colors: [Color(0x8C000000), Color(0x00000000)]))),
                                        )),
                                        Positioned(left: 0, right: 0, top: MediaQuery.paddingOf(context).top, child: cabecera),
                                        Positioned(left: 0, right: 0, bottom: 6, child: tituloYCorazon),
                                      ])
                                    : Column(children: [cabecera, const SizedBox(height: 14), portada, const SizedBox(height: 26)])),
                              ),
                              SliverToBoxAdapter(child: Column(key: _llaveControles,
                                  crossAxisAlignment: CrossAxisAlignment.stretch, children: resto)),
                              ...abajo,
                            ]),
                              Positioned(
                                left: 0, right: 0, top: 0,
                                child: ListenableBuilder(
                                  listenable: _scroll,
                                  builder: (_, hijo) {
                                    final p = _pliegue();
                                    final t = !_scroll.hasClients || p < 40
                                        ? 0.0
                                        : ((_scroll.offset - (p - 90)) / 70).clamp(0.0, 1.0);
                                    if (t == 0) return const SizedBox.shrink();
                                    return IgnorePointer(
                                      ignoring: t < 0.6,
                                      child: Opacity(opacity: t, child: Transform.translate(
                                          offset: Offset(0, -14 * (1 - t)), child: hijo)),
                                    );
                                  },
                                  child: ValueListenableBuilder<PaletaPortada>(
                                    valueListenable: _vista,
                                    builder: (_, pal, _) => CabeceraCompacta(
                                      r: r,
                                      pista: p,
                                      color: Color.lerp(pal.fondo, Colors.black, 0.55)!,
                                      arriba: arribaCompacta,
                                      alBajar: () => _desplegar(false),
                                      alSiguiente: () => _siguiente(r),
                                    ),
                                  ),
                                ),
                              ),
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
    await mostrarMenuHoja(
      context,
      portada: Container(
        width: 52, height: 52,
        decoration: BoxDecoration(shape: BoxShape.circle, color: C.acento),
        child: Icon(Icons.bedtime_rounded, color: C.acentoTexto),
      ),
      titulo: 'Temporizador para dormir',
      subtitulo: restante == null
          ? 'La música se apaga sola'
          : restante == -1
              ? 'Activo: al terminar la canción'
              : 'Activo: quedan ${restante ~/ 60} min ${restante % 60} s',
      grupos: [
        if (restante != null)
          [OpcionMenu(Icons.timer_off_outlined, 'Desactivar', () => r.programarApagado(), color: C.acento)],
        [
          OpcionMenu(Icons.music_off_rounded, 'Al terminar esta canción', () => r.programarApagado(alTerminar: true)),
          for (final m in const [5, 15, 30, 45, 60, 90])
            OpcionMenu(Icons.timer_outlined, '$m minutos', () => r.programarApagado(minutos: m)),
        ],
      ],
    );
  }
}

/// La carátula a todo el ancho, que se desvanece por abajo hacia el fondo.
class _Fundida extends StatelessWidget {
  const _Fundida({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => RepaintBoundary(
        child: ShaderMask(
          blendMode: BlendMode.dstIn,
          shaderCallback: (r) => const LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFFFFFFFF), Color(0xFFFFFFFF), Color(0x00FFFFFF)],
            stops: [0, 0.5, 1],
          ).createShader(r),
          child: child,
        ),
      );
}

/// Canción o video, en la cabecera.
class _CancionOVideo extends StatelessWidget {
  const _CancionOVideo({required this.r});
  final Reproductor r;

  @override
  Widget build(BuildContext context) {
    Widget uno(String modo, IconData icono, String texto) {
      final activo = r.modo == modo;
      return Semantics(
        button: true,
        selected: activo,
        label: texto,
        excludeSemantics: true,
        child: Tooltip(
          message: texto,
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () {
              if (activo) return;
              Haptico.seleccion();
              r.cambiarModo(modo);
            },
            child: AnimatedContainer(
              duration: Mov.normal,
              width: 62,
              height: 38,
              decoration: BoxDecoration(
                color: activo ? const Color(0x40FFFFFF) : Colors.transparent,
                borderRadius: BorderRadius.circular(19),
              ),
              child: Icon(icono, size: 21, color: activo ? Colors.white : const Color(0xB3FFFFFF)),
            ),
          ),
        ),
      );
    }

    return DecoratedBox(
      decoration: BoxDecoration(color: const Color(0x59000000), borderRadius: BorderRadius.circular(19)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        uno('audio', Icons.headphones_rounded, 'Canción'),
        uno('video', Icons.ondemand_video_rounded, 'Video'),
      ]),
    );
  }
}

/// Una acción del reproductor: icono y nombre, en una pastilla.
class _Accion extends StatelessWidget {
  const _Accion({required this.icono, required this.texto, required this.alPulsar, this.color});
  final IconData icono;
  final String texto;
  final VoidCallback alPulsar;
  final Color? color;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(right: 8, top: 4, bottom: 4),
        child: Material(
          color: const Color(0x24FFFFFF),
          borderRadius: BorderRadius.circular(20),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () {
              Haptico.toque();
              alPulsar();
            },
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: Row(children: [
                Icon(icono, size: 19, color: color ?? C.texto),
                const SizedBox(width: 7),
                Text(texto, style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600, color: color ?? C.texto)),
              ]),
            ),
          ),
        ),
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

/// Dónde está en la canción el verso de [ms], con la letra ya puesta a tiempo.
Duration momentoDeVerso(int ms, String clave) =>
    Duration(milliseconds: (ms - _desfaseDe(clave)).clamp(0, 1 << 31));

/// El boton redondo de play/pausa: el icono se transforma y el boton se
/// hunde un poco bajo el dedo.
class _BotonGrande extends StatelessWidget {
  const _BotonGrande({required this.r, this.lado = 82});
  final Reproductor r;
  final double lado;

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
            width: lado, height: lado,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              transitionBuilder: (hijo, a) => ScaleTransition(scale: a, child: FadeTransition(opacity: a, child: hijo)),
              child: cargando
                  ? Padding(key: ValueKey('cargando'), padding: EdgeInsets.all(lado * 0.32),
                      child: CircularProgressIndicator(strokeWidth: 3, color: C.fondo))
                  : Center(key: const ValueKey('icono'),
                      child: IconoPlayPausa(sonando: r.estado == EstadoRepro.sonando, tamano: lado * 0.58, color: C.fondo)),
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

int _desfaseDe(String clave) => LetrasCache.i.desfase(clave);
Listenable get _desfaseCambio => LetrasCache.i.cambios;

const _sinLetra = <String, dynamic>{'texto': '', 'lineas': <dynamic>[]};

/// La letra de [p]: la ya guardada en el teléfono (sale al instante y sin internet) o la de internet.
Future<Map<String, dynamic>> _letraDe(Json p) async {
  try {
    await LetrasCache.i.listo().timeout(const Duration(seconds: 2));
  } catch (_) {}
  // una letra vacía puede ser un fallo de red: no se guarda, se vuelve a intentar
  return await LetrasCache.i.obtener(p) ?? _sinLetra;
}

/// La letra de [clave] si ya no es la que se está viendo (la persona eligió otra).
Map<String, dynamic>? letraCambiada(String clave, Map<String, dynamic>? vista) {
  final l = LetrasCache.i.de(clave);
  return l == null || identical(l, vista) ? null : l;
}

List<(int, String)> _lineas(Map<String, dynamic> l) => [
      for (final x in (l['lineas'] is List ? l['lineas'] as List : const []))
        if (x is List && x.length >= 2)
          (x[0] is num ? (x[0] as num).toInt() : int.tryParse('${x[0]}') ?? 0, '${x[1]}')
    ];

class _TarjetaLetra extends StatefulWidget {
  const _TarjetaLetra({required this.pista, required this.color, this.alto = 280});
  final Json pista;
  final Color color;
  final double alto;

  @override
  State<_TarjetaLetra> createState() => _TarjetaLetraState();
}

class _TarjetaLetraState extends State<_TarjetaLetra> {
  Map<String, dynamic>? _l;
  String _clave = '';

  @override
  void initState() {
    super.initState();
    LetrasCache.i.cambios.addListener(_otraLetra);
  }

  @override
  void dispose() {
    LetrasCache.i.cambios.removeListener(_otraLetra);
    super.dispose();
  }

  void _otraLetra() {
    final l = letraCambiada(_clave, _l);
    if (l != null && _l != null && mounted) setState(() => _l = l);
  }

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
    // el color de la tarjeta justo donde empieza la letra (a 34 px)
    final arriba = Color.lerp(fondo, abajo, 34 / widget.alto)!;
    final hay = l != null && ((l['lineas'] as List? ?? []).isNotEmpty || '${l['texto'] ?? ''}'.isNotEmpty);
    return GestureDetector(
      onTap: hay ? () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => LetraCompleta(pista: widget.pista, letra: l, color: fondo))) : null,
      child: Container(
        height: widget.alto,
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
            const SizedBox(width: 10),
            Expanded(
              child: !hay ? const SizedBox.shrink() : Align(
                alignment: Alignment.centerRight,
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    BotonSincronia(pista: widget.pista, letra: l, compacto: true),
                    const SizedBox(width: 6),
                    const BotonTraducir(compacto: true),
                    const SizedBox(width: 6),
                    const BotonDisenoLetra(compacto: true),
                    const SizedBox(width: 4),
                    BotonKaraoke(pista: widget.pista, letra: l),
                  ]),
                ),
              ),
            ),
            if (hay) const SizedBox(width: 10),
            if (hay) const Icon(Icons.open_in_full_rounded, size: 18),
          ]),
          const SizedBox(height: 10),
          Expanded(
            child: l == null
                ? const Center(child: CircularProgressIndicator(color: Colors.white))
                : !hay
                    ? _BuscarLetra(pista: widget.pista)
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
    LetrasCache.i.cambios.addListener(_otraLetra);
  }

  void _otraLetra() {
    final l = letraCambiada('${_pista['clave']}', _letra);
    if (l != null && _letra != null && mounted) setState(() => _letra = l);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _r ??= Caudal.leer(context).reproductor..addListener(_cambioDeCancion);
  }

  @override
  void dispose() {
    LetrasCache.i.cambios.removeListener(_otraLetra);
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
      final ms = _r!.posicion.value.inMilliseconds + 250 + _desfaseDe('${_pista['clave']}');
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
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 22),
        child: l == null
            ? const Center(child: CircularProgressIndicator(color: Colors.white))
            : !hayLineas && !hayTexto
                ? _BuscarLetra(pista: _pista)
                : Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(children: [
                        BotonSincronia(pista: _pista, letra: l),
                        const SizedBox(width: 8),
                        const BotonTraducir(),
                        const SizedBox(width: 8),
                        const BotonDisenoLetra(),
                      ]),
                    ),
                    const SizedBox(height: 10),
                    if (!hayLineas)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: _AvisoSinTiempos(clave: '${_pista['clave']}'),
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
                r: _r!, porVenir: _porVenir, acento: widget.acento, adelanto: 250 + _desfaseDe(widget.clave));
          } else {
            // el color de cada estado (cantada / por venir / activa) se anima como antes, 260 ms
            linea = LineaLetra(aspecto: aspecto, texto: texto, estilo: estilo, activa: estado == 0,
                acento: widget.acento);
          }
          return GestureDetector(
            key: _llaves[i],
            onTap: () => _r?.buscar(momentoDeVerso(_ls[i].$1, widget.clave)),
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

/// «Corregir»: si la letra va corrida o es de otra canción, aquí se arregla.
class BotonSincronia extends StatelessWidget {
  const BotonSincronia({super.key, required this.pista, required this.letra, this.compacto = false});
  final Json pista;
  final Map<String, dynamic>? letra;
  final bool compacto;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: _desfaseCambio,
        builder: (context, _) {
          final activo = LetrasCache.i.desfasePropio('${pista['clave']}') != 0;
          final tinta = activo ? const Color(0xFF06070A) : Colors.white;
          return Tooltip(
            message: 'Corregir la letra o su sincronía',
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => mostrarCorregirLetra(context, pista, letra),
              child: Container(
                padding: EdgeInsets.symmetric(horizontal: compacto ? 8 : 12, vertical: compacto ? 4 : 6),
                decoration: BoxDecoration(
                  color: activo ? Colors.white : Colors.white.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.av_timer_rounded, size: compacto ? 15 : 18, color: tinta),
                  const SizedBox(width: 5),
                  Text('Corregir', style: TextStyle(fontSize: compacto ? 12 : 14, fontWeight: FontWeight.w800, color: tinta)),
                ]),
              ),
            ),
          );
        },
      );
}

/// «Aa»: el tipo de letra y el diseño, sin salir de la canción.
class BotonDisenoLetra extends StatelessWidget {
  const BotonDisenoLetra({super.key, this.compacto = false});
  final bool compacto;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: 'Diseño de la letra',
        excludeSemantics: true,
        child: Tooltip(
          message: 'Diseño de la letra',
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => mostrarDisenoLetra(context),
            child: Container(
              padding: EdgeInsets.symmetric(horizontal: compacto ? 9 : 12, vertical: compacto ? 4 : 6),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
              child: Text('Aa', style: TextStyle(fontSize: compacto ? 12 : 14, fontWeight: FontWeight.w900)),
            ),
          ),
        ),
      );
}

/// Por qué esta letra no avanza sola (o que se está arreglando).
class _AvisoSinTiempos extends StatelessWidget {
  const _AvisoSinTiempos({required this.clave});
  final String clave;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: _desfaseCambio,
        builder: (_, _) => Text(
            LetrasCache.i.midiendo(clave)
                ? 'Poniendo la letra a tiempo…'
                : lineasConTiempo({'lineas': LetrasCache.i.de(clave)?['ajustables']}).isNotEmpty
                    ? 'Sus tiempos son de otra versión: toca «Corregir» para ajustarla.'
                    : 'Esta letra no trae tiempos, por eso no avanza sola.',
            style: const TextStyle(fontSize: 13, color: Color(0xCCFFFFFF))),
      );
}

/// Sin letra: se puede buscar a mano.
class _BuscarLetra extends StatelessWidget {
  const _BuscarLetra({required this.pista});
  final Json pista;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Text('No hay letra para esta canción.', style: TextStyle(fontWeight: FontWeight.w700)),
          TextButton(
            onPressed: () => elegirOtraLetra(context, pista),
            style: TextButton.styleFrom(foregroundColor: Colors.white),
            child: const Text('Buscarla', style: TextStyle(decoration: TextDecoration.underline)),
          ),
        ]),
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


/// Web: ¿lo que suena va en el recuadro de YouTube? (la música propia y la de la
/// comunidad enseñan su portada, como en la app)
bool _conRecuadro(Reproductor r) =>
    Jugador.esWeb && (r.fuente?.esYouTubeWeb ?? '${r.actual?['video_id'] ?? ''}'.isNotEmpty);

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
