import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../nucleo/importar.dart';
import '../nucleo/legal.dart';
import '../reproduccion/reproductor.dart';
import 'comunes.dart';
import 'paginas/acceso.dart';
import 'paginas/biblioteca.dart';
import 'paginas/buscar.dart';
import 'paginas/descargas_pagina.dart';
import 'paginas/importar_pagina.dart';
import 'paginas/inicio.dart';
import 'paginas/juntos_pagina.dart';
import 'paginas/legal_pagina.dart';
import 'plataforma.dart';
import 'reproductor/animaciones.dart';
import 'servicios.dart';
import 'tema.dart';

/// Las cuatro pestanas (cada una con su propia navegacion, que se conserva al
/// cambiar), el mini reproductor y la barra de abajo.
class Armazon extends StatefulWidget {
  const Armazon({super.key});

  @override
  State<Armazon> createState() => _ArmazonState();
}

class _ArmazonState extends State<Armazon> {
  int _pestana = 0;
  final _navegadores = List.generate(4, (_) => GlobalKey<NavigatorState>());
  StreamSubscription<String>? _avisos;
  static const _canal = MethodChannel('caudal/compartido');

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final s = Caudal.leer(context);
    s.irAPestana = _ir;
    s.abrirEnPestana = (pagina) =>
        _navegadores[_pestana].currentState?.push(MaterialPageRoute(builder: (_) => pagina));
    s.abrirEnlace = (texto) {
      // caudal://juntos?sala=XXXXXX entra directo a la sala de "Escuchar juntos"
      if (texto.trim().toLowerCase().startsWith('caudal://juntos')) {
        _navegadores[_pestana].currentState
            ?.push(MaterialPageRoute(builder: (_) => JuntosPagina(codigoInicial: texto.trim())));
        return;
      }
      // una lista de Spotify o Apple Music compartida: se trae a la biblioteca
      final enlace = Importar.enlaceDe(texto);
      final p = Importar.plataforma(enlace);
      if (p == 'spotify' || p == 'apple' ||
          (p == 'youtube' && enlace.contains('list=') && !enlace.contains('watch?'))) {
        _navegadores[_pestana].currentState
            ?.push(MaterialPageRoute(builder: (_) => ImportarPagina(enlace: enlace)));
        return;
      }
      _ir(3);
      DescargasPagina.pegar(texto);
    };
    _avisos ??= s.reproductor.avisos.listen(s.avisar);
  }

  @override
  void initState() {
    super.initState();
    // lo que se comparte desde otras apps ("Compartir -> Caudal")
    _canal.setMethodCallHandler((llamada) async {
      if (llamada.method == 'compartido' && mounted) {
        Caudal.leer(context).abrirEnlace?.call('${llamada.arguments}');
      }
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => _revisarTerminos());
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      try {
        final inicial = AccesoPagina.enlacePendiente ?? await _canal.invokeMethod<String>('inicial');
        AccesoPagina.enlacePendiente = null;
        if (inicial != null && mounted) Caudal.leer(context).abrirEnlace?.call(inicial);
      } catch (_) {}
    });
  }

  /// Cuentas de antes de los términos (o con una versión vieja, o sin los
  /// datos básicos): se les pide aceptar y completar antes de seguir.
  Future<void> _revisarTerminos() async {
    final s = Caudal.leer(context);
    final sesion = s.cuenta.sesion;
    if (sesion == null || sesion.acceso.isEmpty) return;
    PerfilLegal perfil;
    try {
      perfil = await PerfilLegal.de(sesion);
    } catch (_) {
      return; // sin red: se pregunta la próxima vez
    }
    if ((perfil.aceptado && perfil.completo) || !mounted) return;
    await Navigator.of(context, rootNavigator: true).push(MaterialPageRoute(
      fullscreenDialog: true,
      builder: (ctx) => AceptarTerminosPagina(
        sesion: sesion,
        perfil: perfil,
        alSalir: () {
          Navigator.of(ctx).pop();
          s.cerrarSesion();
        },
      ),
    ));
  }

  @override
  void dispose() {
    _avisos?.cancel();
    super.dispose();
  }

  void _ir(int i) {
    if (i == _pestana) {
      if (i == 1) BuscarPagina.enfocar();     // tocar Buscar otra vez enfoca el campo
      // tocar la pestana en la que estas vuelve a su inicio, como en Spotify
      _navegadores[i].currentState?.popUntil((r) => r.isFirst);
      return;
    }
    HapticFeedback.selectionClick();
    setState(() => _pestana = i);
  }

  @override
  Widget build(BuildContext context) {
    final paginas = [const InicioPagina(), const BuscarPagina(), const BibliotecaPagina(),
      const DescargasPagina()];
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (hecho, _) async {
        if (hecho) return;
        final nav = _navegadores[_pestana].currentState;
        if (nav != null && nav.canPop()) {
          nav.pop();
        } else if (_pestana != 0) {
          setState(() => _pestana = 0);
        } else {
          SystemNavigator.pop();
        }
      },
      child: Scaffold(
        body: Stack(children: [
          IndexedStack(
            index: _pestana,
            children: [
              for (var i = 0; i < 4; i++)
                TickerMode(
                  enabled: i == _pestana,
                  child: Navigator(
                    key: _navegadores[i],
                    onGenerateRoute: (_) => MaterialPageRoute(builder: (_) => paginas[i]),
                  ),
                ),
            ],
          ),
          // capa propia: lo que cambia en el mini reproductor no repinta la pagina de debajo
          const Positioned(left: 8, right: 8, bottom: 6, child: RepaintBoundary(child: MiniReproductor())),
        ]),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _pestana,
          onDestinationSelected: _ir,
          labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
          destinations: const [
            NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'Inicio'),
            NavigationDestination(icon: Icon(Icons.search_rounded), selectedIcon: Icon(Icons.manage_search_rounded), label: 'Buscar'),
            NavigationDestination(icon: Icon(Icons.library_music_outlined), selectedIcon: Icon(Icons.library_music_rounded), label: 'Tu biblioteca'),
            NavigationDestination(icon: Icon(Icons.download_outlined), selectedIcon: Icon(Icons.download_rounded), label: 'Descargar'),
          ],
        ),
      ),
    );
  }
}

/// Lo que suena, siempre a mano encima de la barra.
class MiniReproductor extends StatefulWidget {
  const MiniReproductor({super.key});

  @override
  State<MiniReproductor> createState() => _MiniReproductorState();
}

class _MiniReproductorState extends State<MiniReproductor> {
  Color _color = C.superficie3;
  String _url = '';
  // hacia donde se pidio el cambio de cancion, para que el texto entre por ahi
  int _pedido = 1;
  int _direccion = 1;
  String _claveVista = '';
  bool _abajo = false;

  void _colorDe(String url) {
    if (url == _url) return;
    _url = url;
    colorDominante(url).then((c) {
      if (mounted) setState(() => _color = c);
    });
    // la portada grande queda lista: al abrir, el vuelo ya la tiene
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) precargarPortadaGrande(context, url, ladoPortadaGrande(MediaQuery.sizeOf(context).width));
    });
  }

  void _apretar(bool v) {
    if (_abajo != v) setState(() => _abajo = v);
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final r = s.reproductor;
    final ladoGrande = ladoPortadaGrande(MediaQuery.sizeOf(context).width);
    return ListenableBuilder(
      listenable: Listenable.merge([r, s.coleccion]),
      builder: (context, _) {
        final p = r.actual;
        if (p == null) return const SizedBox.shrink();
        final url = '${p['miniatura'] ?? ''}';
        _colorDe(url);
        final clave = '${p['clave']}';
        if (clave != _claveVista) {
          _direccion = _claveVista.isEmpty ? 1 : _pedido;
          _pedido = 1;
          _claveVista = clave;
        }
        final gusta = s.coleccion.meGusta(clave);
        return GestureDetector(
          onTapDown: (_) => _apretar(true),
          onTapUp: (_) => _apretar(false),
          onTapCancel: () => _apretar(false),
          onTap: () => s.abrirReproductor(context),
          onVerticalDragEnd: (d) {
            if ((d.primaryVelocity ?? 0) < -200) s.abrirReproductor(context);
          },
          onHorizontalDragEnd: (d) {
            // deslizar de lado salta de cancion, como en Spotify
            final v = d.primaryVelocity ?? 0;
            if (v.abs() > 300) Haptico.seleccion();
            if (v < -300) {
              _pedido = 1;
              r.siguiente();
            }
            if (v > 300) {
              _pedido = -1;
              r.anterior();
            }
          },
          // se hunde apenas bajo el dedo antes de abrirse
          child: AnimatedScale(
            scale: _abajo ? 0.975 : 1,
            duration: Duration(milliseconds: _abajo ? 90 : 220),
            curve: Curves.easeOut,
            child: AnimatedContainer(
            duration: const Duration(milliseconds: 400),
            height: 60,
            decoration: BoxDecoration(
              color: Color.lerp(_color, Colors.black, 0.35),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Stack(children: [
              Row(children: [
                Padding(
                  padding: const EdgeInsets.all(7),
                  child: Hero(
                    tag: etiquetaPortada,
                    flightShuttleBuilder: vueloPortada(url, ladoGrande),
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 260),
                      child: Portada(key: ValueKey(clave), url: url, lado: 46, radio: 5),
                    ),
                  ),
                ),
                Expanded(
                  child: ClipRect(
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 300),
                      transitionBuilder: deslizarEn(_direccion, ValueKey(clave), distancia: 0.4),
                      layoutBuilder: (a, previos) =>
                          Stack(alignment: Alignment.centerLeft, children: [...previos, ?a]),
                      child: Column(
                          key: ValueKey(clave),
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                        Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                        Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 12.5, color: Color(0xCCFFFFFF))),
                      ]),
                    ),
                  ),
                ),
                CorazonAnimado(gusta: gusta, alPulsar: () => s.alternarMeGusta(p)),
                SizedBox(
                  width: 48,
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 180),
                    child: r.estado == EstadoRepro.cargando
                        ? const Center(key: ValueKey('cargando'), child: SizedBox(width: 22, height: 22,
                            child: CircularProgressIndicator(strokeWidth: 2.4, color: C.texto)))
                        : IconButton(
                            key: const ValueKey('boton'),
                            icon: IconoPlayPausa(sonando: r.estado == EstadoRepro.sonando, tamano: 30),
                            onPressed: () {
                              Haptico.toque();
                              r.alternar();
                            },
                          ),
                  ),
                ),
                const SizedBox(width: 4),
              ]),
              Positioned(
                left: 8, right: 8, bottom: 0,
                // la barrita avanza varias veces por segundo: que repinte sola
                child: RepaintBoundary(child: ValueListenableBuilder<Duration>(
                  valueListenable: r.posicion,
                  builder: (_, pos, _) {
                    final d = r.duracion.value.inMilliseconds;
                    return ClipRRect(
                      borderRadius: BorderRadius.circular(2),
                      child: LinearProgressIndicator(
                        value: d > 0 ? (pos.inMilliseconds / d).clamp(0.0, 1.0) : 0,
                        minHeight: 2,
                        backgroundColor: const Color(0x33FFFFFF),
                        valueColor: const AlwaysStoppedAnimation(C.texto),
                      ),
                    );
                  },
                )),
              ),
            ]),
          ),
          ),
        );
      },
    );
  }
}
