import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:media_kit/media_kit.dart';
import 'package:media_kit_video/media_kit_video.dart';
import 'package:permission_handler/permission_handler.dart';

import 'nucleo/ajustes.dart';
import 'nucleo/capturador_oculto.dart';
import 'nucleo/catalogo.dart';
import 'nucleo/coleccion.dart';
import 'nucleo/descarga_inteligente.dart';
import 'nucleo/cuentas.dart';
import 'nucleo/descargas.dart';
import 'nucleo/motor_local.dart';
import 'nucleo/red.dart';
import 'nucleo/sincronizacion.dart';
import 'nucleo/streams.dart';
import 'nucleo/version.dart';
import 'reproduccion/pip.dart';
import 'reproduccion/reproductor.dart';
import 'reproduccion/servicio_audio.dart';
import 'ui/armazon.dart';
import 'ui/comunes.dart';
import 'ui/paginas/acceso.dart';
import 'ui/paginas/ajustes_pagina.dart';
import 'ui/servicios.dart';
import 'ui/tema.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  MediaKit.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
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
}

class CaudalApp extends StatefulWidget {
  const CaudalApp({super.key});

  @override
  State<CaudalApp> createState() => _CaudalAppState();
}

class _CaudalAppState extends State<CaudalApp> {
  Servicios? _s;
  bool _comprobando = true;
  final _navegador = GlobalKey<NavigatorState>();
  CapturadorOculto? _capturador;
  DescargaInteligente? _inteligente;

  @override
  void initState() {
    super.initState();
    _arrancar();
  }

  Future<void> _arrancar() async {
    Cuenta? c;
    try {
      c = await Cuentas.recordada().timeout(const Duration(seconds: 20));
    } catch (_) {
      c = null;
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
        }
      }
    } else if (mounted) {
      setState(() => _comprobando = false);
    }
  }

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
    final ajustes = await _paso('ajustes', Ajustes.cargar(c.id));
    Catalogo.fijarRegion(ajustes.texto('region'));
    MotorLocal.bitrateMp3 = ajustes.texto('bitrate_mp3');
    ajustes.addListener(() => MotorLocal.bitrateMp3 = ajustes.texto('bitrate_mp3'));
    final coleccion = await _paso('biblioteca', Coleccion.abrir(c.id));
    final streams = Streams(MotorLocal());
    final reproductor = Reproductor(ajustes, coleccion, streams);
    try {
      await reproductor.restaurarSesion().timeout(const Duration(seconds: 5));
    } catch (_) {} // si la ultima sesion no se puede leer, se empieza de cero
    // con tiempo maximo dentro: si Android tarda, la musica de fondo se engancha despues
    await ServicioAudio.para(reproductor);
    Pip.iniciar(reproductor);
    _capturador ??= CapturadorOculto();
    unawaited(_capturador!.preparar().catchError((_) {}));
    final descargas = GestorDescargas(coleccion: coleccion, ajustes: ajustes, capturador: _capturador!);
    // con wifi baja sola tus favoritas (si el ajuste esta activo)
    _inteligente?.detener();
    _inteligente = DescargaInteligente(coleccion, descargas, ajustes)..iniciar();
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
    late final Servicios s;
    s = Servicios(
      cuenta: c, ajustes: ajustes, coleccion: coleccion, reproductor: reproductor, streams: streams,
      descargas: descargas, sincronizador: sinc,
      cerrarSesion: () => _cerrarSesion(s),
    );
    if (!mounted) return;
    setState(() {
      _s = s;
      _comprobando = false;
    });
    unawaited(_buscarVersion());
    unawaited(_pedirNotificaciones());
  }

  /// Android 13+: sin este permiso no se ven los controles de la musica en la
  /// notificacion ni el aviso de versiones nuevas. Android lo pregunta como
  /// mucho dos veces; si se dijo que no, no insiste.
  Future<void> _pedirNotificaciones() async {
    if (defaultTargetPlatform != TargetPlatform.android) return;
    try {
      await Future.delayed(const Duration(seconds: 2));
      if (await Permission.notification.isDenied) await Permission.notification.request();
    } catch (_) {}
  }

  Future<void> _cerrarSesion(Servicios s) async {
    _navegador.currentState?.popUntil((r) => r.isFirst);
    await s.reproductor.detener();
    s.sincronizador?.detener();
    _inteligente?.detener();
    _inteligente = null;
    await Cuentas.olvidar(s.cuenta);
    setState(() => _s = null);
    // se libera despues de que la pantalla ya no lo use
    Future.delayed(const Duration(seconds: 1), () {
      s.reproductor.dispose();
      s.descargas.dispose();
    });
  }

  Future<void> _buscarVersion() async {
    await Future.delayed(const Duration(seconds: 6));
    final n = await buscarActualizacion().catchError((_) => null);
    final ctx = _navegador.currentContext;
    if (n != null && ctx != null && ctx.mounted) await mostrarActualizacion(ctx, n);
  }

  @override
  Widget build(BuildContext context) {
    final s = _s;
    final fallo = _fallo;
    final Widget inicio = fallo != null
        ? _FalloArranque(error: fallo, reintentar: _reintentar, salir: _salirDeFallo)
        : _comprobando
        ? const _Arranque()
        : s == null
            ? AccesoPagina(alEntrar: _abrir)
            : const Armazon();
    final app = MaterialApp(
      title: 'Caudal',
      debugShowCheckedModeBanner: false,
      theme: temaCaudal(),
      navigatorKey: _navegador,
      scaffoldMessengerKey: s?.mensajero,
      home: AnimatedSwitcher(
        duration: const Duration(milliseconds: 380),
        switchInCurve: Curves.easeOutCubic,
        child: KeyedSubtree(key: ValueKey(fallo != null ? 'fallo' : s?.cuenta.id ?? (_comprobando ? 'arranque' : 'acceso')), child: inicio),
      ),
      builder: (context, hijo) {
        // que la letra grande del sistema no rompa el diseno
        final mq = MediaQuery.of(context);
        final contenido = MediaQuery(
          data: mq.copyWith(textScaler: mq.textScaler.clamp(minScaleFactor: 0.85, maxScaleFactor: 1.2)),
          child: hijo!,
        );
        if (s == null) return contenido;
        // en la ventanita flotante solo se ve el video (la app sigue debajo intacta)
        return ValueListenableBuilder<bool>(
          valueListenable: Pip.enVentana,
          builder: (_, enVentana, __) => Stack(children: [
            contenido,
            if (enVentana)
              Positioned.fill(
                child: ColoredBox(
                  color: Colors.black,
                  child: Video(controller: s.reproductor.pantalla, controls: NoVideoControls, fill: Colors.black),
                ),
              ),
          ]),
        );
      },
    );
    return s == null ? app : Caudal(s: s, child: app);
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
              const Icon(Icons.wifi_tethering_error_rounded, size: 56, color: C.acento),
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
          child: Container(
            width: 74, height: 74,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              gradient: const LinearGradient(colors: [C.acento, C.violeta],
                  begin: Alignment.topLeft, end: Alignment.bottomRight),
            ),
            child: const Icon(Icons.waves_rounded, size: 40, color: Colors.white),
          ),
        ),
      );
}
