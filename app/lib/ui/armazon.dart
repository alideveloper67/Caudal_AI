import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../nucleo/importar.dart';
import '../nucleo/legal.dart';
import '../nucleo/pases_regalo.dart';
import '../nucleo/capsula_tiempo.dart';
import '../nucleo/premium.dart';
import '../nucleo/resumen_anual.dart' show esTemporadaDelResumen;
import '../nucleo/tarjeta_lista.dart';
import '../nucleo/version.dart';
import '../reproduccion/reproductor.dart';
import '../reproduccion/retomar.dart' show avisoRetomado;
import '../nucleo/cumpleanos.dart';
import 'comunes.dart';
import 'cumpleanos.dart';
import 'menu_comunidad.dart';
import 'novedades/presentacion_mascotas.dart';
import 'novedades_grandes.dart';
import 'paginas/acceso.dart';
import 'paginas/mensajes_pagina.dart';
import 'paginas/resumen.dart';
import 'paginas/resumen_anual_pagina.dart';
import 'paginas/ajustes_pagina.dart';
import 'premium/personalizar_pagina.dart';
import 'premium/capsula_ui.dart';
import 'premium/regalo_pases.dart';
import 'paginas/biblioteca.dart';
import 'paginas/buscar.dart';
import 'paginas/descargas_pagina.dart';
import 'paginas/estudio_pagina.dart';
import 'paginas/importar_pagina.dart';
import 'paginas/inicio.dart';
import 'paginas/juntos_pagina.dart';
import 'paginas/lista_compartida_pagina.dart';
import 'paginas/lista_compartir.dart';
import 'paginas/legal_pagina.dart';
import 'plataforma.dart';
import 'reproductor/animaciones.dart';
import 'servicios.dart';
import 'tema.dart';

/// Las cuatro pestanas (cada una con su propia navegacion, que se conserva al
/// cambiar), el mini reproductor y la barra de abajo.
class Armazon extends StatefulWidget {
  const Armazon({super.key, @visibleForTesting this.paginas, @visibleForTesting this.versionActual});

  /// Solo para pruebas: las cuatro paginas de las pestañas.
  final List<Widget>? paginas;

  /// Solo para pruebas: la version que cree estar corriendo.
  final String? versionActual;

  @override
  State<Armazon> createState() => _ArmazonState();
}

class _ArmazonState extends State<Armazon> {
  int _pestana = 0;

  // la equis del mini reproductor: lo oculta hasta que se toque una cancion
  bool _miniOculto = false;
  bool _vioParado = false;
  String _claveOculta = '';

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
    // las listas compartidas donde soy colaborador salen en «Añadir a una lista»
    s.destinosExtraLista ??= () => destinosListasCompartidas(s);
    s.abrirEnlace = (texto) {
      // caudal://lista?codigo=XXXX-XXXX o https://caudal-musica.netlify.app/l/XXXX-XXXX: vista previa y «Unirme»
      if (esEnlaceDeLista(texto)) {
        final ctx = _navegadores[_pestana].currentContext;
        if (ctx != null) hojaTengoCodigo(ctx, codigoInicial: texto.trim());
        return;
      }
      // caudal://juntos?sala=XXXXXX entra directo a la sala de "Escuchar juntos"
      if (texto.trim().toLowerCase().startsWith('caudal://juntos')) {
        _navegadores[_pestana].currentState
            ?.push(MaterialPageRoute(builder: (_) => JuntosPagina(codigoInicial: texto.trim())));
        return;
      }
      // caudal://estudio abre el Modo estudio (atajo de la app en Android)
      if (texto.trim().toLowerCase().startsWith('caudal://estudio')) {
        _navegadores[_pestana].currentState?.push(MaterialPageRoute(builder: (_) => const EstudioPagina()));
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
    _avisos ??= s.reproductor.avisos.listen((t) {
      // al retomar una cancion larga, el aviso lleva el boton «Desde el inicio»
      if (t == avisoRetomado) {
        s.avisar(t, etiqueta: 'Desde el inicio', deshacer: () => s.reproductor.desdeElInicio());
      } else {
        s.avisar(t);
      }
    });
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
    // primero los terminos (si faltan) y despues, una sola vez por version, las novedades
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await _revisarTerminos();
      await _novedadesDeLaVersion();
      await _capsulasDelTiempo();
      await _avisoPasesRegalo();
      await _celebrarCumple();
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => _avisoWebEnTelefono());
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      try {
        final inicial = AccesoPagina.enlacePendiente ?? await _canal.invokeMethod<String>('inicial');
        AccesoPagina.enlacePendiente = null;
        if (inicial != null && mounted) Caudal.leer(context).abrirEnlace?.call(inicial);
      } catch (_) {}
    });
  }

  /// La primera vez que se abre una version con novedades grandes sale su
  /// pantalla (sobre la app, sin tocar la musica). La version vista se guarda
  /// antes de enseñarla: si la cierran o la app se cae, no vuelve a salir.
  ///
  /// Después, la presentación de las mascotitas (2.3.2): una sola vez, y nunca
  /// en el mismo arranque que las novedades grandes (espera al siguiente).
  Future<void> _novedadesDeLaVersion() async {
    try {
      final p = await SharedPreferences.getInstance();
      final actual = widget.versionActual ?? versionApp;
      final grandes = tocaNovedades(p.getString(claveNovedadesVistas), actual);
      if (grandes) {
        if (!mounted) return;
        await p.setString(claveNovedadesVistas, actual);
        if (!mounted) return;
        await NovedadesGrandes.mostrar(context);
        return;
      }
      if (!tocaPresentacionMascotas(p.getString(clavePresentacionMascotasVista), actual) || !mounted) return;
      await p.setString(clavePresentacionMascotasVista, actual);
      if (!mounted) return;
      await PresentacionMascotas.mostrar(context);
    } catch (_) {}
  }

  /// Cápsulas del tiempo (guardadas en este teléfono, por cuenta): las que ya llegaron a su día se enseñan
  /// al abrir la app, una vez cada una. Se abren aunque el premium ya no esté vigente.
  Future<void> _capsulasDelTiempo() async {
    try {
      final cuenta = Caudal.leer(context).cuenta.id;
      if (CapsulasTiempo.i.cuenta != cuenta) await CapsulasTiempo.i.iniciar(cuenta);
      if (!mounted) return;
      await mostrarCapsulasPendientes(context);
    } catch (_) {}
  }

  /// Una sola vez, a donadores y fundadores: ya pueden regalar códigos de prueba. Espera a que
  /// el servidor diga qué tipo de cuenta es; si no llega o se cierra la app, no se marca y sale otro día.
  Future<void> _avisoPasesRegalo() async {
    try {
      if (!await _esperarDonador() || !mounted) return;
      if (!await AvisoPasesRegalo.toca(Premium.i.estado) || !mounted) return;
      // se marca antes de enseñarlo: si la cierran o la app se cae, no vuelve a salir
      await AvisoPasesRegalo.marcarVisto();
      if (!mounted) return;
      final ver = await mostrarAvisoPasesRegalo(context);
      if (ver && mounted) {
        await Navigator.of(context, rootNavigator: true)
            .push(MaterialPageRoute<void>(builder: (_) => const PersonalizarPagina()));
      }
    } catch (_) {}
  }

  /// El día de su cumpleaños, una sola vez: la pantalla de celebración. Se marca antes de enseñarla.
  Future<void> _celebrarCumple() async {
    try {
      if (!await Cumpleanos.i.esperarPerfil() || !mounted) return;
      if (!await Cumpleanos.i.tocaCelebrar() || !mounted) return;
      await Cumpleanos.i.marcarCelebrado();
      if (!mounted) return;
      await PantallaCumple.mostrar(context, nombre: Cumpleanos.i.nombre, edad: Cumpleanos.i.edad);
    } catch (_) {}
  }

  Completer<bool>? _esperaDonador;

  Future<bool> _esperarDonador() async {
    if (PasesRegalo.puedeRegalar(Premium.i.estado)) return true;
    final c = _esperaDonador = Completer<bool>();
    void escuchar() {
      if (!c.isCompleted && PasesRegalo.puedeRegalar(Premium.i.estado)) c.complete(true);
    }

    Premium.i.addListener(escuchar);
    try {
      return await c.future;
    } finally {
      Premium.i.removeListener(escuchar);
    }
  }

  /// En el navegador de un teléfono, YouTube pausa la música al bloquearlo:
  /// se avisa una vez y se ofrece la app, que sí sigue sonando.
  Future<void> _avisoWebEnTelefono() async {
    final telefono = defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS;
    if (!kIsWeb || !telefono) return;
    final p = await SharedPreferences.getInstance();
    if (p.getBool('aviso_web_telefono') == true || !mounted) return;
    await p.setBool('aviso_web_telefono', true);
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Estás en el navegador'),
        content: const Text('Aquí la música se pausa si bloqueas el teléfono o cambias de app: así lo hace '
            'el reproductor de YouTube en los navegadores. Para escuchar con la pantalla bloqueada, '
            'instala la app de Caudal (entras con esta misma cuenta).'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Seguir en el navegador')),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              launchUrl(Uri.parse('https://caudal-musica.netlify.app/#descargar'));
            },
            child: const Text('Instalar la app'),
          ),
        ],
      ),
    );
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
    if (_esperaDonador case final c? when !c.isCompleted) c.complete(false);
    _avisos?.cancel();
    super.dispose();
  }

  /// Detiene la musica y esconde el mini reproductor. Vuelve solo al empezar
  /// cualquier cancion (otra, o la misma con el boton de play).
  void _quitarMini() {
    final r = Caudal.leer(context).reproductor;
    Haptico.toque();
    _claveOculta = '${r.actual?['clave'] ?? ''}';
    _vioParado = false;
    setState(() => _miniOculto = true);
    r.detener();
  }

  /// ¿Sigue oculto? Se muestra de nuevo en cuanto algo empieza a sonar.
  bool _sigueOculto(Reproductor r) {
    if (!_miniOculto) return false;
    if (r.estado == EstadoRepro.parado) {
      _vioParado = true;
      return true;
    }
    if (_vioParado || '${r.actual?['clave'] ?? ''}' != _claveOculta) {
      _miniOculto = false;
      return false;
    }
    return true;
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
    final paginas = widget.paginas ??
        [const InicioPagina(), const BuscarPagina(), const BibliotecaPagina(), const DescargasPagina()];
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
      child: LayoutBuilder(builder: (context, medidas) {
        // pantallas anchas (navegador en la PC, tablets): el menu va a la izquierda
        final ancho = medidas.maxWidth >= 900;
        final contenido = Stack(children: [
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
          ListenableBuilder(
            listenable: Caudal.of(context).reproductor,
            builder: (context, _) {
              final r = Caudal.of(context).reproductor;
              if (r.actual == null || _sigueOculto(r)) return const SizedBox.shrink();
              return Stack(children: [
                Positioned(left: 8, right: 8, bottom: 6,
                    child: RepaintBoundary(child: MiniReproductor(alQuitar: _quitarMini))),
                // la equis: en la esquina de arriba a la derecha, a caballo del borde para no
                // tapar los botones; 32x32 de zona de toque y un icono de 17 px
                Positioned(
                  right: 8 + 6,
                  bottom: 6 + 60 - 16,
                  child: _EquisMini(alPulsar: _quitarMini),
                ),
              ]);
            },
          ),
        ]);
        if (ancho) {
          return Scaffold(
            body: Row(children: [
              _BarraLateral(pestana: _pestana, alIr: _ir, alAbrir: _abrirEnPestana),
              VerticalDivider(width: 1, thickness: 1, color: C.borde),
              Expanded(child: contenido),
            ]),
          );
        }
        return Scaffold(
        // la version, en una franja chiquita bajo todo el contenido (y sobre la barra):
        // asi nunca tapa una pagina ni el mini reproductor
        body: Column(children: [Expanded(child: contenido), const FranjaVersion()]),
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
      );
      }),
    );
  }

  void _abrirEnPestana(Widget pagina) =>
      _navegadores[_pestana].currentState?.push(MaterialPageRoute(builder: (_) => pagina));
}

/// El menu de la izquierda en pantallas anchas (como en las webs de musica).
class _BarraLateral extends StatelessWidget {
  const _BarraLateral({required this.pestana, required this.alIr, required this.alAbrir});
  final int pestana;
  final ValueChanged<int> alIr;
  final ValueChanged<Widget> alAbrir;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    Widget item(IconData icono, IconData activo, String texto, bool elegido, VoidCallback alPulsar) => Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
          child: Material(
            color: elegido ? C.superficie2 : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            child: InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: alPulsar,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                child: Row(children: [
                  Icon(elegido ? activo : icono, size: 22, color: elegido ? C.texto : C.texto2),
                  const SizedBox(width: 14),
                  Text(texto, style: TextStyle(fontSize: 14.5, fontWeight: elegido ? FontWeight.w800 : FontWeight.w600,
                      color: elegido ? C.texto : C.texto2)),
                ]),
              ),
            ),
          ),
        );
    return SizedBox(
      width: 232,
      child: SafeArea(
        // el menu se desplaza si la ventana es baja; la version queda fija abajo
        child: Column(children: [
          Expanded(child: LayoutBuilder(builder: (context, c) => SingleChildScrollView(
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: c.maxHeight),
              child: IntrinsicHeight(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(22, 20, 16, 22),
            child: Row(children: [
              Image.asset('assets/logo/caudal.png', width: 34, height: 34, filterQuality: FilterQuality.high),
              const SizedBox(width: 10),
              const Text('Caudal', style: TextStyle(fontSize: 21, fontWeight: FontWeight.w900, letterSpacing: -0.5)),
            ]),
          ),
          item(Icons.home_outlined, Icons.home_rounded, 'Inicio', pestana == 0, () => alIr(0)),
          item(Icons.search_rounded, Icons.manage_search_rounded, 'Buscar', pestana == 1, () => alIr(1)),
          item(Icons.library_music_outlined, Icons.library_music_rounded, 'Tu biblioteca', pestana == 2, () => alIr(2)),
          item(Icons.download_outlined, Icons.download_rounded, 'Descargar', pestana == 3, () => alIr(3)),
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 18, 16, 6),
            child: Text('TÚ Y TUS AMIGOS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800,
                letterSpacing: 1, color: C.texto3)),
          ),
          item(Icons.forum_outlined, Icons.forum_rounded, 'Mensajes', false, () => alAbrir(const MensajesPagina())),
          item(Icons.account_circle_outlined, Icons.account_circle_rounded, 'Mi perfil', false,
              () => alAbrir(MenuComunidad.pantalla(0, context))),
          item(Icons.explore_outlined, Icons.explore_rounded, 'Perfiles de Caudal', false,
              () => alAbrir(MenuComunidad.pantalla(1, context))),
          item(Icons.library_music_outlined, Icons.library_music_rounded, 'Música de la comunidad', false,
              () => alAbrir(MenuComunidad.pantalla(3, context))),
          item(Icons.album_outlined, Icons.album_rounded, 'Mezclador', false,
              () => alAbrir(MenuComunidad.pantalla(5, context))),
          item(Icons.groups_2_outlined, Icons.groups_2_rounded, 'Escuchar juntos', false,
              () => alAbrir(const JuntosPagina())),
          item(Icons.insights_rounded, Icons.insights_rounded, 'Tu resumen', false, () => ResumenPagina.abrir(context)),
          // «Tu año en Caudal»: siempre ahí; en diciembre (y la primera quincena de enero) con «nuevo»
          item(Icons.auto_awesome_outlined, Icons.auto_awesome_rounded,
              esTemporadaDelResumen(DateTime.now()) ? 'Tu año en Caudal · nuevo' : 'Tu año en Caudal', false,
              () => alAbrir(const ResumenAnualPagina())),
          item(Icons.self_improvement_outlined, Icons.self_improvement_rounded, 'Modo estudio', false,
              () => alAbrir(const EstudioPagina())),
          const Spacer(),
          item(Icons.settings_outlined, Icons.settings_rounded, 'Ajustes', false, () => alAbrir(const AjustesPagina())),
          Padding(
            padding: const EdgeInsets.fromLTRB(22, 10, 16, 8),
            child: Row(children: [
              ConGorro(radio: 15, userId: Cumpleanos.i.miId.isEmpty ? s.cuenta.id : Cumpleanos.i.miId,
                  child: CircleAvatar(radius: 15, backgroundColor: C.acento,
                      child: Text(s.cuenta.inicial, style: TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900)))),
              const SizedBox(width: 10),
              Expanded(child: Text(s.cuenta.nombre, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w700))),
            ]),
          ),
              ])),
            ),
          ))),
          const Padding(padding: EdgeInsets.only(left: 8, bottom: 6), child: FranjaVersion()),
        ]),
      ),
    );
  }
}

/// Donde se guarda la ultima version cuyas novedades ya se enseñaron.
const String claveNovedadesVistas = 'novedades_version_vista';

/// «Caudal 2.2.0», chiquito y tenue, abajo a la izquierda. No capta toques
/// (no tapa nada de lo que haya debajo): ocupa su propia franja.
class FranjaVersion extends StatelessWidget {
  const FranjaVersion({super.key});

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Semantics(
        label: 'Versión de Caudal $versionApp',
        excludeSemantics: true,
        child: Align(
          alignment: Alignment.centerLeft,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 2, 12, 3),
            child: Text(
              'Caudal $versionApp',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 10.5, height: 1.1, letterSpacing: 0.2, color: C.texto3.withValues(alpha: 0.8)),
            ),
          ),
        ),
      ),
    );
  }
}

/// La equis pequeña que quita el mini reproductor.
class _EquisMini extends StatelessWidget {
  const _EquisMini({required this.alPulsar});
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: 'Quitar la canción y cerrar el reproductor',
        excludeSemantics: true,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: alPulsar,
          child: SizedBox(
            width: 32,
            height: 32,
            child: Center(
              child: Container(
                width: 22,
                height: 22,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: C.fondo,
                  border: Border.all(color: C.borde),
                ),
                child: const Center(child: Icon(Icons.close_rounded, size: 17, color: C.texto2)),
              ),
            ),
          ),
        ),
      );
}

/// Lo que suena, siempre a mano encima de la barra.
class MiniReproductor extends StatefulWidget {
  const MiniReproductor({super.key, this.alQuitar});

  /// Si se da, deslizar el mini hacia abajo lo quita (y la equis hace lo mismo).
  final VoidCallback? alQuitar;

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
            if ((d.primaryVelocity ?? 0) > 300) widget.alQuitar?.call();
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
