import 'dart:async';

import 'package:audio_service/audio_service.dart';
import 'package:audio_session/audio_session.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show MethodChannel;

import '../nucleo/coleccion.dart';
import '../nucleo/plataforma.dart';
import 'biblioteca_auto.dart';
import 'frenos.dart';
import 'reproductor.dart';
import 'widget_inicio.dart';

/// Puente con el sistema: notificacion con controles (Android), pantalla de
/// bloqueo y Centro de control (iPhone, MPNowPlayingInfoCenter y
/// MPRemoteCommandCenter), auriculares y que la musica siga con la pantalla
/// apagada. En iPhone hace falta `audio` en UIBackgroundModes del Info.plist.
///
/// En Android ademas: la biblioteca en el coche (Android Auto: getChildren,
/// playFromMediaId, busqueda por voz) y el widget de la pantalla de inicio.
class ServicioAudio extends BaseAudioHandler with SeekHandler {
  ServicioAudio(this.r, {Coleccion? coleccion}) : auto = BibliotecaAuto(coleccion ?? r.coleccion) {
    _enganchar();
    WidgetInicio.iniciar(
      alternar: () => r.estado == EstadoRepro.sonando ? pause() : play(),
      siguiente: skipToNext,
    );
  }

  Reproductor r;

  /// Lo que se navega desde el coche; cambia con la cuenta.
  final BibliotecaAuto auto;

  void _enganchar() {
    r.addListener(_publicar);
    r.posicion.addListener(_publicarPosicion);
    _publicar();
  }

  /// Otra cuenta, otro reproductor: Android solo deja iniciar el servicio una vez.
  /// La biblioteca del coche pasa a [coleccion] (por defecto, la del reproductor).
  void cambiar(Reproductor nuevo, {Coleccion? coleccion}) {
    r.removeListener(_publicar);
    r.posicion.removeListener(_publicarPosicion);
    r = nuevo;
    auto.coleccion = coleccion ?? nuevo.coleccion;
    _ultimaClave = '';
    _freno.reiniciar();
    _enganchar();
  }

  static ServicioAudio? _unico;

  /// Inicia el servicio la primera vez; despues solo le cambia el reproductor.
  static Future<ServicioAudio>? _arrancando;
  static Reproductor? _ultimoR;
  static Coleccion? _ultimaColeccion;

  /// Engancha el reproductor a la notificacion y la pantalla de bloqueo.
  ///
  /// En algunos telefonos el servicio de Android tarda (o no llega nunca) en
  /// responder: no se espera mas de [espera] para que la app no se quede en
  /// el logo. Si responde despues, se engancha solo al reproductor de ese momento.
  static Future<ServicioAudio?> para(Reproductor r,
      {Coleccion? coleccion, Duration espera = const Duration(seconds: 6)}) async {
    _ultimoR = r;
    _ultimaColeccion = coleccion;
    final u = _unico;
    if (u != null) {
      u.cambiar(r, coleccion: coleccion);
      return u;
    }
    _arrancando ??= iniciar(r, coleccion: coleccion).then((nuevo) {
      _unico = nuevo;
      unawaited(nuevo._sesion());
      final ultimo = _ultimoR;
      if (ultimo != null && !identical(ultimo, nuevo.r)) nuevo.cambiar(ultimo, coleccion: _ultimaColeccion);
      return nuevo;
    }, onError: (Object e) {
      _arrancando = null; // que se pueda reintentar la proxima vez
      throw e;
    });
    try {
      return await _arrancando!.timeout(espera);
    } catch (e) {
      debugPrint('Caudal: la musica de fondo aun no arranca ($e)');
      return null;
    }
  }

  // ------------------------------------------------------------ foco de audio

  bool _pausadoPorInterrupcion = false;
  AudioSession? _sesionAudio;
  bool _activa = false;
  double? _volumenAntes;

  /// Como cualquier app de musica: se pausa al quitar los audifonos o al
  /// entrar una llamada, baja el volumen con una notificacion y vuelve despues.
  Future<void> _sesion() async {
    try {
      final s = await AudioSession.instance;
      await s.configure(const AudioSessionConfiguration.music());
      s.becomingNoisyEventStream.listen((_) {
        if (r.estado == EstadoRepro.sonando) r.pausar();
      });
      s.interruptionEventStream.listen((e) {
        if (e.begin) {
          if (e.type == AudioInterruptionType.duck) {
            _volumenAntes = r.volumen;
            r.fijarVolumen(r.volumen * 0.35);
          } else if (r.estado == EstadoRepro.sonando) {
            _pausadoPorInterrupcion = true;
            r.pausar();
          }
        } else {
          if (_volumenAntes != null) {
            r.fijarVolumen(_volumenAntes!);
            _volumenAntes = null;
          }
          if (_pausadoPorInterrupcion && e.type == AudioInterruptionType.pause) {
            // iOS deja la sesion inactiva tras una llamada: hay que reactivarla
            unawaited(_reactivarYSeguir());
          }
          _pausadoPorInterrupcion = false;
        }
      });
      _sesionAudio = s;
    } catch (_) {}
  }
  Future<void> _reactivarYSeguir() async {
    if (_ios) {
      try {
        await _sesionAudio?.setActive(true);
      } catch (_) {}
    }
    await r.reanudar();
  }

  static bool get _ios => defaultTargetPlatform == TargetPlatform.iOS;

  String _ultimaClave = '';
  int _ultimoSegundo = -1;

  static Future<ServicioAudio> iniciar(Reproductor r, {Coleccion? coleccion}) => AudioService.init(
        builder: () => ServicioAudio(r, coleccion: coleccion),
        config: const AudioServiceConfig(
          androidNotificationChannelId: 'app.caudal.reproduccion',
          androidNotificationChannelName: 'Reproducción',
          androidNotificationChannelDescription: 'Lo que está sonando en Caudal',
          androidNotificationOngoing: false,
          androidStopForegroundOnPause: true,
          androidNotificationIcon: 'drawable/ic_notificacion',
          preloadArtwork: true,
          // adelantar/atrasar del Centro de control de iOS (como avanzar(10))
          fastForwardInterval: Duration(seconds: 10),
          rewindInterval: Duration(seconds: 10),
        ),
      );

  // ------------------------------------------------------------ pantalla apagada

  static const _canalEnergia = MethodChannel('caudal/energia');
  bool _energiaPuesta = false;
  Timer? _soltarEnergia;

  /// Mientras suena (o carga la siguiente) se mantienen despiertos el CPU y el
  /// wifi: con la pantalla apagada, si no, la siguiente canción no se abre.
  /// Al parar se sueltan con un pequeño retraso, para no soltar entre canciones.
  void _energia(bool activo) {
    if (!Plataforma.esAndroid) return;
    if (activo) {
      _soltarEnergia?.cancel();
      _soltarEnergia = null;
      if (!_energiaPuesta) {
        _energiaPuesta = true;
        _canalEnergia.invokeMethod('mantener', true).catchError((_) {});
      }
    } else if (_energiaPuesta && _soltarEnergia == null) {
      _soltarEnergia = Timer(const Duration(seconds: 25), () {
        _soltarEnergia = null;
        _energiaPuesta = false;
        _canalEnergia.invokeMethod('mantener', false).catchError((_) {});
      });
    }
  }

  void _publicar() {
    // pedir el foco de audio al empezar a sonar (vale tambien tras cambiar de cuenta)
    final sonando = r.estado == EstadoRepro.sonando;
    _energia(sonando || r.estado == EstadoRepro.cargando);
    if (sonando && !_activa) _sesionAudio?.setActive(true);
    _activa = sonando;
    final p = r.actual;
    if (p != null && '${p['clave']}' != _ultimaClave) {
      _ultimaClave = '${p['clave']}';
      final mini = '${p['miniatura'] ?? ''}';
      mediaItem.add(MediaItem(
        id: _ultimaClave,
        title: '${p['titulo'] ?? ''}',
        artist: '${p['artista'] ?? ''}',
        album: '${(p['album'] as Map?)?['nombre'] ?? ''}',
        duration: r.duracion.value == Duration.zero ? null : r.duracion.value,
        artUri: mini.isEmpty ? null : (mini.startsWith('http') ? Uri.parse(mini) : Uri.file(mini)),
      ));
    }
    _estado();
    _widget();
  }

  void _widget() {
    if (!Plataforma.esAndroid) return;
    final p = r.actual;
    final item = mediaItem.value;
    WidgetInicio.publicar(
      hay: p != null,
      titulo: p == null ? '' : '${p['titulo'] ?? ''}',
      artista: p == null ? '' : '${p['artista'] ?? ''}',
      arte: p == null ? '' : (item?.artUri?.toString() ?? ''),
      sonando: r.estado == EstadoRepro.sonando || r.estado == EstadoRepro.cargando,
    );
  }

  void _publicarPosicion() {
    final s = r.posicion.value.inSeconds;
    if (s == _ultimoSegundo) return;
    _ultimoSegundo = s;
    // el sistema avanza la barra por su cuenta: solo se le avisa si hubo un salto
    _estado();
    final item = mediaItem.value;
    if (item != null && item.duration == null && r.duracion.value > Duration.zero) {
      mediaItem.add(item.copyWith(duration: r.duracion.value));
    }
  }

  /// La notificacion solo se vuelve a publicar cuando cambia algo de verdad
  /// (estado, velocidad, cancion) o la posicion salta: antes se publicaba cada
  /// segundo y Android rehacia la notificacion entera cada vez.
  final _freno = FrenoNotificacion();

  void _estado() {
    // cargando cuenta como "sonando" para el sistema: entre una canción y la siguiente el
    // servicio no debe dejar de ser de primer plano, o con la pantalla apagada Android
    // congela la red y la siguiente canción no carga hasta encender la pantalla
    final sonando = r.estado == EstadoRepro.sonando || r.estado == EstadoRepro.cargando;
    // mientras carga, el reloj del sistema no debe correr: se cuenta como quieto
    final corre = r.estado == EstadoRepro.sonando;
    if (!_freno.deja(
      firma: '${r.estado.name}|${r.actual == null}|${r.velocidad}|$_ultimaClave',
      posicion: r.posicion.value,
      sonando: corre,
      velocidad: r.velocidad,
    )) {
      return;
    }
    playbackState.add(PlaybackState(
      controls: [
        MediaControl.skipToPrevious,
        if (sonando) MediaControl.pause else MediaControl.play,
        MediaControl.skipToNext,
      ],
      systemActions: const {MediaAction.seek, MediaAction.seekForward, MediaAction.seekBackward},
      androidCompactActionIndices: const [0, 1, 2],
      processingState: switch (r.estado) {
        EstadoRepro.cargando => AudioProcessingState.buffering,
        EstadoRepro.parado => r.actual == null ? AudioProcessingState.idle : AudioProcessingState.ready,
        _ => AudioProcessingState.ready,
      },
      playing: sonando,
      updatePosition: r.posicion.value,
      speed: r.velocidad,
    ));
  }

  @override
  Future<void> play() => _ios ? _reactivarYSeguir() : r.reanudar();
  @override
  Future<void> pause() => r.pausar();
  @override
  Future<void> stop() => r.detener();
  @override
  Future<void> seek(Duration position) => r.buscar(position);
  @override
  Future<void> skipToNext() => r.siguiente();
  @override
  Future<void> skipToPrevious() => r.anterior();
  @override
  Future<void> fastForward() => r.avanzar(10);
  @override
  Future<void> rewind() => r.avanzar(-10);

  // ------------------------------------------------------------ Android Auto

  @override
  Future<List<MediaItem>> getChildren(String parentMediaId, [Map<String, dynamic>? options]) async {
    try {
      return await auto.hijos(parentMediaId);
    } catch (e) {
      debugPrint('auto getChildren: $e');
      return const [];
    }
  }

  @override
  Future<MediaItem?> getMediaItem(String mediaId) async {
    try {
      return await auto.elemento(mediaId);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<List<MediaItem>> search(String query, [Map<String, dynamic>? extras]) async {
    final halladas = await auto.buscar(query);
    return [for (final p in halladas) BibliotecaAuto.cancion('bus', p)];
  }

  /// Tocar una cancion en el coche: suena con el resto de su carpeta en cola.
  @override
  Future<void> playFromMediaId(String mediaId, [Map<String, dynamic>? extras]) async {
    final partes = BibliotecaAuto.partir(mediaId);
    if (partes == null) {
      // una carpeta entera (p. ej. "pon mis me gusta")
      return _sonarCarpeta(mediaId);
    }
    final (carpeta, clave) = partes;
    final pistas = await auto.pistasDe(carpeta);
    final i = pistas.indexWhere((p) => '${p['clave']}' == clave);
    if (i < 0) {
      final suelta = (await auto.coleccion.pistas([clave])).firstOrNull;
      if (suelta != null) await r.reproducirPista(suelta);
      return;
    }
    if (carpeta == 'bus') {
      await r.reproducirPista(pistas[i]);
      return;
    }
    await r.reproducirLista(pistas, inicio: i, contexto: await _contexto(carpeta));
  }

  Future<void> _sonarCarpeta(String carpeta) async {
    final pistas = await auto.pistasDe(carpeta);
    if (pistas.isEmpty) return;
    await r.reproducirLista(pistas, contexto: await _contexto(carpeta));
  }

  Future<Json> _contexto(String carpeta) async {
    final titulo = await auto.tituloDe(carpeta);
    if (carpeta.startsWith('l:')) return {'tipo': 'mi_lista', 'id': int.tryParse(carpeta.substring(2)), 'titulo': titulo};
    if (carpeta == 'c:megusta') return {'tipo': 'me_gusta', 'id': 'me_gusta', 'titulo': titulo};
    if (carpeta == 'c:descargas') return {'tipo': 'descargados', 'id': 'descargados', 'titulo': titulo};
    return {'tipo': 'seleccion', 'id': titulo, 'titulo': titulo};
  }

  /// "Ok Google, pon ... en Caudal". Sin texto: tus me gusta (o lo reciente).
  @override
  Future<void> playFromSearch(String query, [Map<String, dynamic>? extras]) async {
    if (query.trim().isEmpty) {
      final gustan = await auto.pistasDe('c:megusta');
      if (gustan.isNotEmpty) {
        await r.reproducirLista(gustan, aleatorio: true, contexto: await _contexto('c:megusta'));
      } else {
        await _sonarCarpeta('c:recientes');
      }
      return;
    }
    final halladas = await auto.buscar(query, limite: 10);
    if (halladas.isEmpty) return;
    await r.reproducirPista(halladas.first);
  }

  @override
  Future<void> playMediaItem(MediaItem mediaItem) => playFromMediaId(mediaItem.id);
}
