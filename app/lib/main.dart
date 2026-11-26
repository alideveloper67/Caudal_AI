import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart' show PointerDeviceKind;
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter/services.dart';
import 'package:media_kit/media_kit.dart';
import 'package:media_kit_video/media_kit_video.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:share_plus/share_plus.dart';

import 'nucleo/ajustes.dart';
import 'nucleo/aviso_errores.dart';
import 'nucleo/salidas_android.dart';
import 'nucleo/avisos_dispositivo.dart';
import 'nucleo/cumpleanos.dart';
import 'nucleo/avisos.dart';
import 'nucleo/capturador_oculto.dart';
import 'nucleo/catalogo.dart';
import 'nucleo/coleccion.dart';
import 'nucleo/descarga_inteligente.dart';
import 'nucleo/diagnostico.dart';
import 'nucleo/cuentas.dart';
import 'nucleo/descargas.dart';
import 'nucleo/gustos.dart';
import 'nucleo/logros.dart';
import 'nucleo/logros_vigia.dart';
import 'nucleo/motor_local.dart';
import 'nucleo/red.dart';
import 'nucleo/sincronizacion.dart';
import 'nucleo/sonidos_interfaz.dart';
import 'nucleo/streams.dart';
import 'nucleo/version.dart';
import 'nucleo/vida_app.dart';
import 'reproduccion/motor_eleccion.dart';
import 'reproduccion/pip.dart';
import 'reproduccion/reproductor.dart';
import 'reproduccion/servicio_audio.dart';
import 'reproduccion/sesion_medios.dart';
import 'ui/armazon.dart';
import 'ui/comunes.dart';
import 'nucleo/fondo_app.dart';
import 'nucleo/colores_nombre.dart';
import 'nucleo/premium.dart';
import 'nucleo/ritmo_fondo.dart';
import 'nucleo/mascota_app.dart';
import 'nucleo/gamer_control.dart';
import 'nucleo/social.dart';
import 'ui/despertador_enganche.dart';
import 'ui/aviso_bateria.dart';
import 'ui/fondo_capa.dart';
import 'ui/logros_aviso.dart';
import 'ui/reproductor/letra_aspecto.dart';
import 'ui/novedades/presentacion_100.dart';
import 'ui/novedades/presentacion_donadores.dart';
import 'ui/paginas/acceso.dart';
import 'ui/paginas/ajustes_pagina.dart';
import 'ui/paginas/aviso_dialogo.dart';
import 'ui/paginas/gustos_pagina.dart';
import 'ui/servicios.dart';
import 'ui/tema.dart';

// Todo el arranque corre dentro del aviso de errores: lo que nadie atrapa se manda a la nube
Future<void> main() => AvisoErrores.enZona(() async {
  WidgetsFlutterBinding.ensureInitialized();
  // cualquier error queda escrito (registro del sistema + detalle de la traba)
  FlutterError.onError = (d) {
    FlutterError.presentError(d);
    Diagnostico.anotarError(d.exceptionAsString(), d.stack);
  };
  PlatformDispatcher.instance.onError = (e, pila) {
    Diagnostico.anotarError(e, pila);
    return true;
  };
  // el aviso de errores encadena los ganchos de arriba (no los quita)
  AvisoErrores.instalar();
  // por qué se cerró Caudal la vez anterior (fallo nativo, memoria, ahorro de batería...): al informe
  unawaited(Future.delayed(const Duration(seconds: 12), SalidasAndroid.revisar));
  MediaKit.ensureInitialized();
  // primer plano / segundo plano: los sondeos y la posicion se frenan al salir
  VidaApp.iniciar();
  SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    // iOS no mira statusBarIconBrightness: con fondo "oscuro" pone la hora y la
    // bateria en blanco, sobre el notch y la Dynamic Island
    statusBarBrightness: Brightness.dark,
    systemNavigationBarColor: C.fondo,
    systemNavigationBarIconBrightness: Brightness.light,
  ));
  await SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  final vista = WidgetsBinding.instance.platformDispatcher.views.first;
  final lados = vista.physicalSize;
  Streams.altoPantalla = (lados.width < lados.height ? lados.width : lados.height).round();
  unawaited(Red.iniciar());
  portadaGeneroAsync = (el) => Catalogo.portadaGenero('${el['id']}', el['params'] as String?);
  runApp(const CaudalApp());
});

class CaudalApp extends StatefulWidget {
  const CaudalApp({super.key});

  @override
  State<CaudalApp> createState() => _CaudalAppState();
}

class _CaudalAppState extends State<CaudalApp> {
  Servicios? _s;
  bool _comprobando = true;
  final _navegador = GlobalKey<NavigatorState>();
  // fija para toda la vida de la app: si cambiara al entrar, Flutter rehace
  // el arbol y el navegador se queda con la pantalla vieja (el logo)
  final _mensajero = GlobalKey<ScaffoldMessengerState>();
  CapturadorOculto? _capturador;
  DescargaInteligente? _inteligente;
  // vigía de logros de la cuenta abierta (uno por cuenta)
  VigiaLogros? _vigia;

  void _alCambiarFondo() {
    if (mounted) setState(() {}); // el tema cambia (pantallas transparentes) cuando hay fondo
  }

  String _temaPremium = Premium.i.temaEfectivo;

  /// Un tema exclusivo que se pone, se quita o se pierde (la prueba venció): se repinta toda la app.
  void _alCambiarPremium() {
    // quien se vuelve donador con la app abierta ve «Gracias, donador» en cuanto se confirma
    if (_inicioListo && !_revisandoDonador && Premium.i.donaDeVerdad) unawaited(_revisarDonador());
    final nuevo = Premium.i.temaEfectivo;
    if (nuevo == _temaPremium) return;
    _temaPremium = nuevo;
    final a = _s?.ajustes;
    if (a == null) return;
    Aspecto.aplicar(a.texto('acento'), a.texto('fondo'));
    if (mounted) setState(() {});
    _rehacerTodo();
  }

  bool _rehaciendo = false;

  /// Repinta toda la app con el tema nuevo. Hacerlo en mitad de un cuadro (o del arranque) reconstruía
  /// pantallas que se estaban quitando: «Null check» en Inicio y en la entrada, y a veces todo negro.
  void _rehacerTodo() {
    if (_rehaciendo) return;
    _rehaciendo = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Future<void>.delayed(const Duration(milliseconds: 60), () async {
        try {
          if (mounted) await WidgetsBinding.instance.reassembleApplication();
        } catch (_) {
        } finally {
          _rehaciendo = false;
        }
      });
    });
    WidgetsBinding.instance.scheduleFrame();
  }

  @override
  void initState() {
    super.initState();
    FondoApp.i.addListener(_alCambiarFondo);
    Premium.i.addListener(_alCambiarPremium);
    ModoGamerControl.mascotasOcultas.addListener(_alCambiarFondo); // «Modo gamer»: esconde mascota y personaje
    _arrancar();
  }

  @override
  void dispose() {
    FondoApp.i.removeListener(_alCambiarFondo);
    ModoGamerControl.mascotasOcultas.removeListener(_alCambiarFondo);
    Premium.i.removeListener(_alCambiarPremium);
    super.dispose();
  }

  Future<void> _arrancar() async {
    await Diagnostico.iniciar();
    final d = Diagnostico.detalle;
    if (d != null && mounted) {
      // la vez anterior se trabo: primero se ensena el detalle (por si vuelve a pasar)
      final seguir = Completer<void>();
      setState(() => _aviso = (d, seguir));
      Diagnostico.pintadoAviso();
      await seguir.future;
      Diagnostico.detalle = null;
      if (mounted) setState(() => _aviso = null);
    }
    Diagnostico.marcar('cuenta');
    Cuenta? c;
    try {
      c = await Cuentas.recordada().timeout(const Duration(seconds: 12));
    } catch (_) {
      // nunca a la pantalla de acceso por un fallo de red: se entra con la cuenta guardada
      try {
        c = await Cuentas.guardadaSinConexion();
      } catch (_) {
        c = null;
      }
    }
    if (c != null) {
      try {
        await _abrir(c, true);
      } catch (e) {
        // nunca quedarse en el logo: se avisa y se puede reintentar
        if (mounted) {
          setState(() {
            _fallo = e;
            _cuentaFallida = c;
          });
          _alDibujar();
        }
      }
    } else if (mounted) {
      setState(() => _comprobando = false);
      _alDibujar();
    }
  }

  /// Cuando la pantalla ya se ve: el arranque salio bien y, si la vez
  /// anterior se trabo, se le cuenta al usuario.
  void _alDibujar() {
    WidgetsBinding.instance.addPostFrameCallback((_) => Diagnostico.pintado());
  }

  (String, Completer<void>)? _aviso;

  /// Falta elegir los artistas favoritos (pantalla antes de la principal).
  bool _gustosPendientes = false;

  Object? _fallo;
  Cuenta? _cuentaFallida;

  Future<void> _reintentar() async {
    final c = _cuentaFallida;
    setState(() => _fallo = null);
    if (c == null) return _arrancar();
    try {
      await _abrir(c, true);
    } catch (e) {
      if (mounted) setState(() => _fallo = e);
    }
  }

  Future<void> _salirDeFallo() async {
    await Cuentas.olvidar(_cuentaFallida).catchError((_) {});
    if (!mounted) return;
    setState(() {
      _fallo = null;
      _cuentaFallida = null;
      _comprobando = false;
    });
  }

  /// Un paso del arranque con tiempo maximo: si se pasa, se sabe cual fue.
  static Future<T> _paso<T>(String nombre, Future<T> f, {int segundos = 15}) =>
      f.timeout(Duration(seconds: segundos), onTimeout: () => throw ErrorArranque(nombre));

  /// Monta todo lo de una cuenta: su biblioteca, sus ajustes y el reproductor.
  Future<void> _abrir(Cuenta c, bool recordar) async {
    await Cuentas.anotarUltimo(c.usuario);
    if (recordar) {
      await Cuentas.recordar(c);
    } else {
      await Cuentas.olvidar();
    }
    Diagnostico.marcar('ajustes');
    final ajustes = await _paso('ajustes', Ajustes.cargar(c.id));
    Catalogo.fijarRegion(ajustes.texto('region'));
    MotorLocal.bitrateMp3 = ajustes.texto('bitrate_mp3');
    ajustes.addListener(() => MotorLocal.bitrateMp3 = ajustes.texto('bitrate_mp3'));
    // el aspecto elegido (color y fondo); al cambiarlo se repinta toda la app
    var aspecto = '${ajustes.texto('acento')}|${ajustes.texto('fondo')}';
    Aspecto.aplicar(ajustes.texto('acento'), ajustes.texto('fondo'));
    ajustes.addListener(() {
      final nuevo = '${ajustes.texto('acento')}|${ajustes.texto('fondo')}';
      if (nuevo == aspecto) return;
      aspecto = nuevo;
      Aspecto.aplicar(ajustes.texto('acento'), ajustes.texto('fondo'));
      if (mounted) setState(() {});
      // los widgets que leen los colores directamente se vuelven a construir (también si llega de la nube
      // al arrancar: por eso fuera del cuadro en curso)
      _rehacerTodo();
    });
    // modo ligero: sin animaciones ni adornos y con menos memoria para imagenes
    void aplicarLigero() {
      final cache = PaintingBinding.instance.imageCache;
      final ligero = ajustes.sino('modo_ligero');
      cache.maximumSizeBytes = ligero ? 48 << 20 : 100 << 20;
      cache.maximumSize = ligero ? 400 : 1000;
    }

    var ligeroAntes = ajustes.sino('modo_ligero');
    aplicarLigero();
    // el estilo y el tipo de letra de la letra de las canciones (Ajustes › Letra)
    LetraAspecto.escuchar(ajustes);
    ajustes.addListener(() {
      final ahora = ajustes.sino('modo_ligero');
      if (ahora == ligeroAntes) return;
      ligeroAntes = ahora;
      aplicarLigero();
      if (mounted) setState(() {});
    });
    Diagnostico.marcar('biblioteca');
    final coleccion = await _paso('biblioteca', Coleccion.abrir(c.id));
    // las portadas de las tarjetas de género se recuerdan entre sesiones
    Catalogo.guardarPortadasGeneroEn(
      leer: () => coleccion.estado('portadas_genero'),
      guardar: (m) => coleccion.guardarEstado('portadas_genero', m),
    );
    Diagnostico.marcar('motor');
    // qué motor de sonido usa este teléfono: el de Caudal, o el de Android si el de Caudal
    // tumbó la app aquí hace poco (reproduccion/motor_eleccion.dart)
    await EleccionMotor.preparar(ajuste: ajustes.texto(EleccionMotor.claveAjuste), version: versionApp)
        .timeout(const Duration(seconds: 3), onTimeout: () {});
    Diagnostico.marcar('reproductor');
    final streams = Streams(MotorLocal());
    final reproductor = Reproductor(ajustes, coleccion, streams);
    Diagnostico.marcar('sesion');
    try {
      await reproductor.restaurarSesion().timeout(const Duration(seconds: 5));
    } catch (_) {} // si la ultima sesion no se puede leer, se empieza de cero
    // con tiempo maximo dentro: si Android tarda, la musica de fondo se engancha despues
    // modo seguro (la vez anterior se trabo): sin las piezas nativas opcionales
    // en el navegador no hay ventana flotante ni descargas; los controles de la pantalla
    // bloqueada los lleva la propia web (sesion_medios.dart)
    SesionMedios.enganchar(reproductor);
    final seguro = Diagnostico.modoSeguro || kIsWeb;
    if (!seguro) {
      Diagnostico.marcar('notificacion');
      await ServicioAudio.para(reproductor);
      Diagnostico.marcar('ventana_flotante');
      Pip.iniciar(reproductor);
    }
    Diagnostico.marcar('descargas');
    // el navegador oculto ya no se monta al arrancar: se crea en la primera
    // captura y se cierra solo tras un rato sin usarse (memoria y bateria)
    _capturador ??= CapturadorOculto();
    final descargas = GestorDescargas(coleccion: coleccion, ajustes: ajustes, capturador: _capturador!);
    // con wifi baja sola tus favoritas (si el ajuste esta activo)
    _inteligente?.detener();
    _inteligente = kIsWeb ? null : (DescargaInteligente(coleccion, descargas, ajustes)..iniciar());
    Sincronizador? sinc;
    if (c.sesion != null) {
      sinc = Sincronizador(coleccion, c.sesion!, alRenovar: () => Cuentas.actualizarRecordada(c),
          ajustes: ajustes,
          alCambiarAjustes: (cambiados) {
            // lo cambiado en otro dispositivo se nota al momento
            reproductor.aplicarSonido();
            if (cambiados.contains('region')) Catalogo.fijarRegion(ajustes.texto('region'));
            if (cambiados.contains('bitrate_mp3')) MotorLocal.bitrateMp3 = ajustes.texto('bitrate_mp3');
          })
        ..iniciar();
      // al cambiar un ajuste comun, se sube en un momento
      var ultima = Sincronizador.huellaAjustes(Sincronizador.ajustesParaNube(ajustes.paraNube()));
      final sincr = sinc;
      ajustes.addListener(() {
        final ahora = Sincronizador.huellaAjustes(Sincronizador.ajustesParaNube(ajustes.paraNube()));
        if (ahora == ultima) return;      // el volumen u otros ajustes propios no viajan
        ultima = ahora;
        sincr.pronto();
      });
    }
    Diagnostico.marcar('pantalla');
    // «Modo gamer»: XP por escuchar, ahorro, sonido y listas por situación
    final gamer = ModoGamerControl(
      ajustes: ajustes,
      sesion: c.sesion,
      aplicarSonido: reproductor.aplicarSonido,
      lanzar: (pistas, contexto) => reproductor.reproducirLista(pistas, contexto: contexto),
      alSubirNivel: (n) {
        final m = _mensajero.currentState;
        if (m == null) return;
        m.hideCurrentSnackBar();
        m.showSnackBar(SnackBar(content: Text('¡Subiste al nivel $n!'), duration: const Duration(milliseconds: 2400)));
      },
    );
    reproductor.addListener(() => gamer.alReproductor(reproductor.estado == EstadoRepro.sonando, reproductor.actual));
    late final Servicios s;
    s = Servicios(
      cuenta: c, ajustes: ajustes, coleccion: coleccion, reproductor: reproductor, streams: streams,
      descargas: descargas, sincronizador: sinc,
      cerrarSesion: () => _cerrarSesion(s),
      mensajero: _mensajero,
      gamer: gamer,
    );
    // cuenta nueva (o que aun no eligio): antes de la pantalla principal, sus artistas favoritos
    var preguntarGustos = false;
    try {
      preguntarGustos = await Gustos.prepararSesion(c.sesion, c.id);
    } catch (_) {}
    if (!mounted) return;
    setState(() {
      _s = s;
      _gustosPendientes = preguntarGustos;
      _comprobando = false;
    });
    _alDibujar();
    // «Fondo de Caudal» (donadores y fundadores): lo guardado se ve al instante; lo de la nube, después
    unawaited(FondoApp.i
        .iniciar(c.id, c.sesion != null && c.sesion!.acceso.isNotEmpty ? Social(c.sesion!) : null)
        .catchError((_) {}));
    unawaited(MascotaApp.i.iniciar(c.id).catchError((_) {}));
    // «Feliz cumpleaños»: mi fecha y qué amigos cumplen hoy (la celebración la lanza el armazón)
    unawaited(Cumpleanos.i.iniciar(c.id, c.sesion).catchError((_) {}));
    // beneficios de donador (marco, efecto del nombre, tema): lo guardado primero, lo de la nube después
    unawaited(Premium.i
        .iniciar(c.id, c.sesion != null && c.sesion!.acceso.isNotEmpty ? Social(c.sesion!) : null)
        .catchError((_) {}));
    unawaited(SonidosInterfaz.i.alAbrir().catchError((_) {})); // el sonidito al abrir (donadores, si lo activó)
    unawaited(_buscarVersion()); // «Somos 100» (si toca) y luego las novedades de la versión
    unawaited(_buscarAvisos());
    unawaited(_pedirNotificaciones());
    // la primera vez que suena un rato: que el ahorro de batería no corte la música (Android)
    AvisoBateria.enganchar(s.reproductor, () => _navegador.currentContext);
    // aviso con la app cerrada: se registra el token de este teléfono en el servidor
    if (c.sesion != null) unawaited(AvisosDispositivo.registrar(c.sesion!));
    // logros: el vigía cuenta lo que suena y avisa al conseguir uno (uno por cuenta)
    _vigia?.detener();
    _vigia = null;
    // los logros nunca deben frenar la entrada: si algo falla, la cuenta abre igual
    try {
      final logros = await Logros.abrir(c.id);
      if (identical(_s, s)) {   // la cuenta sigue abierta (no se cerró mientras cargaba)
        _vigia = VigiaLogros(
          logros: logros,
          reproductor: reproductor,
          suena: () => reproductor.estado == EstadoRepro.sonando,
          actual: () => reproductor.actual,
          coleccion: coleccion,
          sesion: c.sesion,
          alConseguir: (nuevos) => AvisosLogros.mostrar(_navegador.currentState?.overlay, nuevos),
        )..iniciar();
      }
    } catch (e) {
      debugPrint('logros: $e');
    }
    // despertador y letra en la pantalla bloqueada (una vez por cuenta; en el navegador, solo el
    // despertador, que suena con la página abierta)
    engancharDespertador(s, _navegador);
  }

  /// Android 13+: sin este permiso no se ven los controles de la musica en la
  /// notificacion ni el aviso de versiones nuevas. Android lo pregunta como
  /// mucho dos veces; si se dijo que no, no insiste.
  Future<void> _pedirNotificaciones() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    try {
      await Future.delayed(const Duration(seconds: 3));
      final estado = await Permission.notification.status;
      if (estado.isGranted) return;
      // se explica una vez por version (sin insistir en cada arranque)
      final p = await SharedPreferences.getInstance();
      final clave = 'aviso_notificaciones_$versionApp';
      if (p.getBool(clave) == true) return;
      await p.setBool(clave, true);
      final ctx = _navegador.currentContext;
      if (ctx == null || !ctx.mounted) return;
      final bloqueado = estado.isPermanentlyDenied;
      final si = await showDialog<bool>(
        context: ctx,
        builder: (c) => AlertDialog(
          title: const Text('Activa las notificaciones'),
          content: Text(bloqueado
              ? 'Las notificaciones de Caudal están apagadas. Actívalas en los ajustes del teléfono para '
                  'enterarte cuando haya una versión nueva y tener los controles de la música en la pantalla bloqueada.'
              : 'Así te avisamos cuando haya una versión nueva de Caudal, aunque no abras la app, y '
                  'tienes los controles de la música en la pantalla bloqueada.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Ahora no')),
            FilledButton(onPressed: () => Navigator.pop(c, true),
                child: Text(bloqueado ? 'Abrir ajustes' : 'Activar')),
          ],
        ),
      );
      if (si != true) return;
      if (bloqueado) {
        await openAppSettings();
      } else {
        await Permission.notification.request();
      }
    } catch (_) {}
  }

  Future<void> _cerrarSesion(Servicios s) async {
    // este teléfono deja de recibir avisos de mensajes y solicitudes de la cuenta que sale
    unawaited(AvisosDispositivo.olvidar());
    _navegador.currentState?.popUntil((r) => r.isFirst);
    await s.reproductor.detener();
    s.sincronizador?.detener();
    _inteligente?.detener();
    _inteligente = null;
    _vigia?.detener();
    _vigia = null;
    // las alarmas de Android siguen programadas; aquí solo se suelta la cuenta
    soltarDespertador();
    await Cuentas.olvidar(s.cuenta);
    FondoApp.i.reiniciar();
    Premium.i.reiniciar();
    ColoresNombre.i.reiniciar();
    MascotaApp.i.reiniciar();
    Cumpleanos.i.reiniciar();
    s.gamer?.guardarYa();
    ModoGamerControl.mascotasOcultas.value = false;
    Gustos.actuales = [];
    setState(() {
      _s = null;
      _gustosPendientes = false;
    });
    // se libera despues de que la pantalla ya no lo use
    Future.delayed(const Duration(seconds: 1), () {
      s.gamer?.dispose();
      s.reproductor.dispose();
      s.descargas.dispose();
    });
  }

  /// Los avisos que se mandan a todas las apps (nucleo/avisos.dart): cada uno sale una sola vez.
  Future<void> _buscarAvisos() async {
    await Future.delayed(const Duration(seconds: 4));
    final lista = await Avisos.pendientes();
    for (final a in lista) {
      final ctx = _navegador.currentContext;
      if (!mounted || ctx == null || !ctx.mounted) return;
      await mostrarAviso(ctx, a);
    }
  }

  /// A los 6 s: primero «Somos 100» (si toca; su revisión tiene timeout de 8 s y, sin red, no sale),
  /// y solo cuando se cierra salen las novedades de la versión. Así nunca se encima una con la otra.
  Future<void> _buscarVersion() async {
    await Future.delayed(const Duration(seconds: 6));
    final pendiente = buscarActualizacion().catchError((_) => null); // se busca en paralelo
    final ctx0 = _navegador.currentContext;
    if (mounted && ctx0 != null && ctx0.mounted) await Presentacion100.revisar(ctx0);
    final n = await pendiente;
    final ctx = _navegador.currentContext;
    if (n != null && ctx != null && ctx.mounted) await mostrarActualizacion(ctx, n);
    // por último «Gracias, donador» (solo donadores de verdad, una vez): espera a que no haya nada encima
    _inicioListo = true;
    await _revisarDonador();
  }

  /// Ya pasaron «Somos 100» y las novedades: desde aquí un donador nuevo puede ver su presentación.
  bool _inicioListo = false;
  bool _revisandoDonador = false;

  Future<void> _revisarDonador() async {
    if (_revisandoDonador) return;
    _revisandoDonador = true;
    try {
      if (!await _esperarSinRutas()) return; // sigue algo encima: se verá en el próximo cambio o arranque
      final ctxD = _navegador.currentContext;
      if (mounted && ctxD != null && ctxD.mounted) await PresentacionDonadores.revisar(ctxD);
    } finally {
      _revisandoDonador = false;
    }
  }

  /// Espera a que no haya ninguna ruta abierta encima (reintento cada 2 s, como mucho 1 minuto).
  /// Devuelve false si al cabo de ese minuto sigue algo encima o la pantalla ya no está.
  Future<bool> _esperarSinRutas() async {
    for (var i = 0; i < 30; i++) {
      if (!mounted) return false;
      if (!(_navegador.currentState?.canPop() ?? false)) return true;
      await Future.delayed(const Duration(seconds: 2));
    }
    return mounted && !(_navegador.currentState?.canPop() ?? false);
  }

  @override
  Widget build(BuildContext context) {
    final s = _s;
    final fallo = _fallo;
    final aviso = _aviso;
    final Widget inicio = aviso != null
        ? _PantallaTraba(detalle: aviso.$1, continuar: () {
            if (!aviso.$2.isCompleted) aviso.$2.complete();
          })
        : fallo != null
        ? _FalloArranque(error: fallo, reintentar: _reintentar, salir: _salirDeFallo)
        : _comprobando
        ? const _Arranque()
        : s == null
            ? AccesoPagina(alEntrar: _abrir)
            : _gustosPendientes
                ? GustosPagina(
                    sesion: s.cuenta.sesion, cuentaId: s.cuenta.id,
                    alTerminar: () {
                      if (mounted) setState(() => _gustosPendientes = false);
                    })
                : const Armazon();
    final app = MaterialApp(
      title: 'Caudal',
      debugShowCheckedModeBanner: false,
      theme: temaCaudal(),
      // en el navegador y en escritorio las listas y carruseles también se arrastran con el ratón
      scrollBehavior: const MaterialScrollBehavior().copyWith(
        dragDevices: {PointerDeviceKind.touch, PointerDeviceKind.mouse, PointerDeviceKind.stylus,
          PointerDeviceKind.trackpad, PointerDeviceKind.invertedStylus},
      ),
      // calendario, menus y botones del sistema en español
      locale: const Locale('es'),
      supportedLocales: const [Locale('es'), Locale('en')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      navigatorKey: _navegador,
      // el aviso de errores anota qué pantalla está abierta
      navigatorObservers: [AvisoErrores.observador],
      scaffoldMessengerKey: _mensajero,
      home: AnimatedSwitcher(
        duration: const Duration(milliseconds: 380),
        switchInCurve: Curves.easeOutCubic,
        child: KeyedSubtree(key: ValueKey(aviso != null ? 'aviso' : fallo != null ? 'fallo' : s != null ? '${s.cuenta.id}${_gustosPendientes ? '|gustos' : ''}' : (_comprobando ? 'arranque' : 'acceso')), child: inicio),
      ),
      builder: (context, hijo) {
        // que la letra grande del sistema no rompa el diseno
        final mq = MediaQuery.of(context);
        // con el modo ligero todo lo que respeta «quitar animaciones» se queda quieto
        final ligero = s?.ajustes.sino('modo_ligero') ?? false;
        final contenido = MediaQuery(
          data: mq.copyWith(
            textScaler: mq.textScaler.clamp(minScaleFactor: 0.85, maxScaleFactor: 1.2),
            disableAnimations: mq.disableAnimations || ligero,
          ),
          child: hijo!,
        );
        if (s == null) return contenido;
        // Caudal (lo que comparten las pantallas) va AQUI dentro y no envolviendo
        // al MaterialApp: si la raiz cambiara de forma al entrar a la cuenta, el
        // navegador se quedaria con la pantalla vieja (el fallo del logo eterno).
        // Todo lo que se abre (pantallas, dialogos, hojas) cuelga de aqui.
        return Caudal(s: s, child: ValueListenableBuilder<bool>(
          valueListenable: Pip.enVentana,
          builder: (_, enVentana, _) => Stack(children: [
            const CapaFondoApp(),
            contenido,
            // el personaje del fondo con personaje, encima, en su esquina (se agranda pellizcándolo)
            if (Aspecto.patron != null && !enVentana && !ModoGamerControl.mascotasOcultas.value)
              Positioned.fill(
                child: PersonajeEncima(
                  alto: s.ajustes.entero('tamano_personaje').toDouble(),
                  alCambiar: (v) => s.ajustes.poner('tamano_personaje', v.round(), avisar: false),
                  reproductor: s.reproductor,
                  suena: () => s.reproductor.estado == EstadoRepro.sonando,
                  x: s.ajustes.decimal('personaje_x'),
                  y: s.ajustes.decimal('personaje_y'),
                  alMover: (x, y) {
                    s.ajustes.poner('personaje_x', x, avisar: false);
                    s.ajustes.poner('personaje_y', y, avisar: false);
                  },
                  baila: s.ajustes.sino('personaje_baila') && !ligero,
                  posicion: s.reproductor.posicion,
                  ritmo: () => RitmoFondo.para(s.coleccion).de('${s.reproductor.actual?['clave'] ?? ''}'),
                ),
              ),
            if (enVentana && s.reproductor.pantalla != null)
              Positioned.fill(
                child: ColoredBox(
                  color: Colors.black,
                  child: Video(controller: s.reproductor.pantalla!, controls: NoVideoControls, fill: Colors.black,
                      pauseUponEnteringBackgroundMode: false),
                ),
              ),
          ]),
        ));
      },
    );
    return app;
  }
}

class ErrorArranque implements Exception {
  const ErrorArranque(this.paso);
  final String paso;
  @override
  String toString() => 'tardó demasiado: $paso';
}

/// Si algo falla al entrar: explicacion clara y dos salidas, nunca el logo eterno.
class _FalloArranque extends StatelessWidget {
  const _FalloArranque({required this.error, required this.reintentar, required this.salir});
  final Object error;
  final VoidCallback reintentar;
  final VoidCallback salir;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: C.fondo,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
              Icon(Icons.wifi_tethering_error_rounded, size: 56, color: C.acento),
              const SizedBox(height: 18),
              const Text('No pudimos abrir tu música', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              const Text('Tu cuenta está bien. Revisa tu conexión y vuelve a intentarlo.',
                  textAlign: TextAlign.center, style: TextStyle(color: C.texto2)),
              const SizedBox(height: 26),
              FilledButton(onPressed: reintentar, child: const Text('Reintentar')),
              const SizedBox(height: 8),
              TextButton(onPressed: salir, child: const Text('Entrar con otra cuenta')),
              const SizedBox(height: 22),
              // detalle pequeno: si lo cuentas, sabemos exactamente que paso
              Text('Detalle: $error', textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 11, color: C.texto3)),
            ]),
          ),
        ),
      );
}

class _Arranque extends StatelessWidget {
  const _Arranque();

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: C.fondo,
        body: Center(
          child: Image.asset('assets/logo/caudal.png', width: 74, height: 74, filterQuality: FilterQuality.high),
        ),
      );
}

/// La vez anterior se quedo en el logo: se cuenta claro y se puede enviar el detalle.
class _PantallaTraba extends StatelessWidget {
  const _PantallaTraba({required this.detalle, required this.continuar});
  final String detalle;
  final VoidCallback continuar;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: C.fondo,
        body: SafeArea(
          child: ListView(padding: const EdgeInsets.fromLTRB(24, 40, 24, 24), children: [
            Icon(Icons.healing_rounded, size: 52, color: C.acento),
            const SizedBox(height: 16),
            const Text('Caudal se trabó al abrir', textAlign: TextAlign.center,
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
            const SizedBox(height: 10),
            Text(
              Diagnostico.modoSeguro
                  ? 'La vez anterior se quedó en el logo. Ahora abrirá en modo seguro: todo funciona, pero sin '
                      'los controles de música en la notificación hasta la próxima versión.'
                  : 'La vez anterior se quedó en el logo.',
              textAlign: TextAlign.center, style: const TextStyle(color: C.texto2, height: 1.4),
            ),
            const SizedBox(height: 10),
            const Text('Envía este detalle a quien te pasó Caudal: con él se arregla del todo.',
                textAlign: TextAlign.center, style: TextStyle(color: C.texto2, height: 1.4)),
            const SizedBox(height: 20),
            FilledButton.icon(
              icon: const Icon(Icons.share_rounded, size: 18),
              label: const Text('Enviar detalle'),
              onPressed: () => unawaited(SharePlus.instance
                  .share(ShareParams(text: 'Caudal se trabó al abrir:\n$detalle'))
                  .then((_) {}, onError: (_) {})),
            ),
            const SizedBox(height: 8),
            OutlinedButton(onPressed: continuar, child: const Text('Continuar')),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(10)),
              child: SelectableText(detalle, style: const TextStyle(fontSize: 10.5, color: C.texto3)),
            ),
          ]),
        ),
      );
}
