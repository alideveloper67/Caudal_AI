import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:media_kit/media_kit.dart';
import 'package:media_kit_video/media_kit_video.dart';

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
      await _abrir(c, true);
    } else if (mounted) {
      setState(() => _comprobando = false);
    }
  }

  /// Monta todo lo de una cuenta: su biblioteca, sus ajustes y el reproductor.
  Future<void> _abrir(Cuenta c, bool recordar) async {
    await Cuentas.anotarUltimo(c.usuario);
    if (recordar) {
      await Cuentas.recordar(c);
    } else {
      await Cuentas.olvidar();
    }
    final ajustes = await Ajustes.cargar(c.id);
    Catalogo.fijarRegion(ajustes.texto('region'));
    MotorLocal.bitrateMp3 = ajustes.texto('bitrate_mp3');
    ajustes.addListener(() => MotorLocal.bitrateMp3 = ajustes.texto('bitrate_mp3'));
    final coleccion = await Coleccion.abrir(c.id);
    final streams = Streams(MotorLocal());
    final reproductor = Reproductor(ajustes, coleccion, streams);
    await reproductor.restaurarSesion();
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
    final Widget inicio = _comprobando
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
        child: KeyedSubtree(key: ValueKey(s?.cuenta.id ?? (_comprobando ? 'arranque' : 'acceso')), child: inicio),
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
