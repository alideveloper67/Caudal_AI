import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_chrome_cast/flutter_chrome_cast.dart';

import 'cast_tipos.dart';

/// Google Cast con el SDK oficial de Google (paquete flutter_chrome_cast): en
/// Android va por los servicios de Google Play y en iPhone por el
/// google-cast-sdk. Se usa el receptor por defecto de Google (el que trae
/// cualquier Chromecast), así que no hace falta registrar nada en Google.
class PuenteNativo implements PuenteCast {
  final _sesion = StreamController<DispositivoCast?>.broadcast();
  final _medio = StreamController<EventoCast>.broadcast();
  final _volumen = StreamController<double>.broadcast();
  final List<StreamSubscription<dynamic>> _subs = [];
  DispositivoCast? _ultimo;
  final Map<String, GoogleCastDevice> _aparatos = {};

  @override
  bool get disponible => Platform.isAndroid || Platform.isIOS;

  @override
  Future<bool> preparar() async {
    const app = GoogleCastDiscoveryCriteria.kDefaultApplicationId;
    final GoogleCastOptions opciones = Platform.isIOS
        ? IOSGoogleCastOptions(
            GoogleCastDiscoveryCriteriaInitialize.initWithApplicationID(app),
            // si no, al salir de la app el iPhone suspende la sesión y la música volvería al teléfono
            suspendSessionsWhenBackgrounded: false,
            physicalVolumeButtonsWillControlDeviceVolume: true,
            stopCastingOnAppTerminated: true,
          )
        : GoogleCastOptionsAndroid(appId: app, stopCastingOnAppTerminated: true);
    final ok = await GoogleCastContext.instance.setSharedInstanceWithOptions(opciones);
    if (!ok) return false;
    _subs.add(GoogleCastSessionManager.instance.currentSessionStream.listen(_alSesion, onError: (_) {}));
    _subs.add(GoogleCastRemoteMediaClient.instance.mediaStatusStream.listen(_alEstado, onError: (_) {}));
    return true;
  }

  void _alSesion(GoogleCastSession? s) {
    final conectado = s != null && s.connectionState == GoogleCastConnectState.connected && s.device != null;
    if (conectado) {
      final d = _aDispositivo(s.device!);
      _ultimo = d;
      _sesion.add(d);
      _volumen.add(s.currentDeviceVolume.toDouble());
    } else if (_ultimo != null &&
        (s == null || s.connectionState == GoogleCastConnectState.disconnected)) {
      // solo se avisa del corte si antes hubo conexión (al conectar llegan sesiones a medias)
      _ultimo = null;
      _sesion.add(null);
    }
  }

  void _alEstado(GoggleCastMediaStatus? m) {
    if (m == null) return;
    final estado = switch (m.playerState) {
      CastMediaPlayerState.playing => EstadoMedioCast.sonando,
      CastMediaPlayerState.paused => EstadoMedioCast.pausa,
      CastMediaPlayerState.buffering || CastMediaPlayerState.loading => EstadoMedioCast.cargando,
      CastMediaPlayerState.idle => switch (m.idleReason) {
          GoogleCastMediaIdleReason.finished => EstadoMedioCast.terminado,
          GoogleCastMediaIdleReason.error => EstadoMedioCast.error,
          GoogleCastMediaIdleReason.cancelled || GoogleCastMediaIdleReason.interrupted => EstadoMedioCast.cortado,
          _ => EstadoMedioCast.nada,
        },
      _ => EstadoMedioCast.nada,
    };
    final info = m.mediaInformation;
    final url = info?.contentUrl?.toString() ?? info?.contentId;
    _medio.add(EventoCast(estado, duracion: info?.duration, url: (url == null || url.isEmpty) ? null : url));
  }

  DispositivoCast _aDispositivo(GoogleCastDevice d) {
    _aparatos[d.deviceID] = d;
    return DispositivoCast(id: d.deviceID, nombre: d.friendlyName, modelo: d.modelName ?? '');
  }

  @override
  Stream<List<DispositivoCast>> get dispositivos => GoogleCastDiscoveryManager.instance.devicesStream
      .map((l) => [for (final d in l) _aDispositivo(d)]);

  @override
  Future<void> buscar() => GoogleCastDiscoveryManager.instance.startDiscovery();

  @override
  Future<void> dejarDeBuscar() => GoogleCastDiscoveryManager.instance.stopDiscovery();

  @override
  Future<bool> conectar(DispositivoCast d) async {
    final aparato = _aparatos[d.id];
    if (aparato == null) return false;
    return GoogleCastSessionManager.instance.startSessionWithDevice(aparato);
  }

  @override
  Future<void> desconectar() async {
    await GoogleCastSessionManager.instance.endSessionAndStopCasting();
  }

  @override
  Stream<DispositivoCast?> get sesion => _sesion.stream;

  @override
  Stream<EventoCast> get medio => _medio.stream;

  @override
  Stream<Duration> get posicion => GoogleCastRemoteMediaClient.instance.playerPositionStream;

  @override
  Stream<double> get volumen => _volumen.stream;

  @override
  Future<void> cargar(MedioCast m, {Duration desde = Duration.zero, bool sonar = true}) async {
    final caratula = m.caratula == null ? null : Uri.tryParse(m.caratula!);
    final info = GoogleCastMediaInformation(
      contentId: m.url,
      contentUrl: Uri.parse(m.url),
      streamType: CastMediaStreamType.buffered,
      contentType: m.tipo,
      duration: m.duracion,
      metadata: GoogleCastMusicMediaMetadata(
        title: m.titulo,
        artist: m.artista,
        albumName: m.album.isEmpty ? null : m.album,
        images: caratula == null ? null : [GoogleCastImage(url: caratula, width: 720, height: 720)],
      ),
    );
    if (kDebugMode) debugPrint('cast: cargando ${m.tipo} ${m.titulo}');
    await GoogleCastRemoteMediaClient.instance.loadMedia(info, autoPlay: sonar, playPosition: desde);
  }

  @override
  Future<void> sonar() => GoogleCastRemoteMediaClient.instance.play();

  @override
  Future<void> pausar() => GoogleCastRemoteMediaClient.instance.pause();

  @override
  Future<void> irA(Duration p) => GoogleCastRemoteMediaClient.instance.seek(
      GoogleCastMediaSeekOption(position: p, resumeState: GoogleCastMediaResumeState.unchanged));

  @override
  Future<void> fijarVolumen(double v) async => GoogleCastSessionManager.instance.setDeviceVolume(v);

  @override
  Future<void> parar() => GoogleCastRemoteMediaClient.instance.stop();
}
