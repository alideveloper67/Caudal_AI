import 'dart:async';

import 'package:audio_service/audio_service.dart';
import 'package:audio_session/audio_session.dart';
import 'package:flutter/foundation.dart';

import 'reproductor.dart';

/// Puente con el sistema: notificacion con controles (Android), pantalla de
/// bloqueo y Centro de control (iPhone, MPNowPlayingInfoCenter y
/// MPRemoteCommandCenter), auriculares y que la musica siga con la pantalla
/// apagada. En iPhone hace falta `audio` en UIBackgroundModes del Info.plist.
class ServicioAudio extends BaseAudioHandler with SeekHandler {
  ServicioAudio(this.r) {
    _enganchar();
  }

  Reproductor r;

  void _enganchar() {
    r.addListener(_publicar);
    r.posicion.addListener(_publicarPosicion);
    _publicar();
  }

  /// Otra cuenta, otro reproductor: Android solo deja iniciar el servicio una vez.
  void cambiar(Reproductor nuevo) {
    r.removeListener(_publicar);
    r.posicion.removeListener(_publicarPosicion);
    r = nuevo;
    _ultimaClave = '';
    _enganchar();
  }

  static ServicioAudio? _unico;

  /// Inicia el servicio la primera vez; despues solo le cambia el reproductor.
  static Future<ServicioAudio> para(Reproductor r) async {
    final u = _unico;
    if (u != null) {
      u.cambiar(r);
      return u;
    }
    final nuevo = _unico = await iniciar(r);
    unawaited(nuevo._sesion());
    return nuevo;
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

  static Future<ServicioAudio> iniciar(Reproductor r) => AudioService.init(
        builder: () => ServicioAudio(r),
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

  void _publicar() {
    // pedir el foco de audio al empezar a sonar (vale tambien tras cambiar de cuenta)
    final sonando = r.estado == EstadoRepro.sonando;
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
  }

  void _publicarPosicion() {
    final s = r.posicion.value.inSeconds;
    if (s == _ultimoSegundo) return;
    _ultimoSegundo = s;
    _estado();
    final item = mediaItem.value;
    if (item != null && item.duration == null && r.duracion.value > Duration.zero) {
      mediaItem.add(item.copyWith(duration: r.duracion.value));
    }
  }

  void _estado() {
    final sonando = r.estado == EstadoRepro.sonando;
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
}
