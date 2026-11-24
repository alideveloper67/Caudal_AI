import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:youtube_explode_dart/youtube_explode_dart.dart';

import 'motor_local.dart';
import 'sonoridad.dart';

/// Convierte un video de YouTube en direcciones que el reproductor puede abrir.
///
/// En el telefono la "maxima calidad" de video se limita a lo que la pantalla
/// puede mostrar y se prefieren los codecs que casi todos los moviles
/// decodifican por hardware (VP9 y H.264): AV1 por software se come la bateria
/// y da tirones en la mayoria de telefonos.
class Streams {
  Streams(this.motor);

  final MotorLocal motor;
  final Map<String, (DateTime, Fuente)> _cache = {};

  /// Alto de la pantalla en pixeles fisicos (lo fija la app al arrancar).
  static int altoPantalla = 1080;

  /// Olvida los enlaces guardados de un video (p. ej. porque no se pudieron abrir).
  void olvidar(String videoId) => _cache.removeWhere((k, _) => k.startsWith('$videoId|'));

  Future<Fuente> resolver(String videoId,
      {required bool video, String calidad = 'maxima', String codec = 'auto', int intento = 0}) async {
    // en la web suena el reproductor oficial de YouTube: basta con el id
    if (kIsWeb) return Fuente(url: 'yt:$videoId', audioCodec: 'YouTube');
    final clave = '$videoId|$video|$calidad|$codec';
    final guardado = _cache[clave];
    if (intento == 0 && guardado != null &&
        DateTime.now().difference(guardado.$1) < const Duration(minutes: 210)) {
      return guardado.$2;
    }
    final m = await motor.manifiesto(videoId, empezarEn: intento);
    final audio = elegirAudio(m.audioOnly.toList(), calidad: video ? 'maxima' : calidad);
    final alturas = <int>{
      for (final v in m.videoOnly) v.videoResolution.height,
      for (final v in m.muxed) v.videoResolution.height,
    }.where((h) => h > 0).toList()
      ..sort((a, b) => b.compareTo(a));

    Fuente fuente;
    if (!video) {
      if (audio == null) {
        final muxed = m.muxed.sortByVideoQuality();
        if (muxed.isEmpty) throw Exception('YouTube no dio ninguna pista de sonido.');
        fuente = Fuente(url: muxed.last.url.toString(), audioCodec: 'aac', abr: 128,
            videoId: videoId, lufs: RegistroSonoridad.i.lufs(videoId));
      } else {
        fuente = Fuente(
          url: audio.url.toString(),
          audioCodec: audio.audioCodec.split('.').first,
          abr: (audio.bitrate.bitsPerSecond / 1000).round(),
          videoId: videoId,
          lufs: RegistroSonoridad.i.lufs(videoId),
        );
      }
    } else {
      final tope = _tope(calidad);
      int rango(String c) {
        c = c.toLowerCase();
        if (codec == 'compatible') return c.startsWith('avc') ? 0 : 9;
        if (c.startsWith('vp9') || c.startsWith('vp09')) return 0;
        if (c.startsWith('avc')) return 1;
        if (c.startsWith('av01')) return codec == 'auto_av1' ? 0 : 5;
        return 3;
      }
      final candidatos = m.videoOnly.where((v) => v.videoResolution.height <= tope).toList()
        ..sort((a, b) {
          final h = b.videoResolution.height.compareTo(a.videoResolution.height);
          if (h != 0) return h;
          final r = rango(a.videoCodec).compareTo(rango(b.videoCodec));
          if (r != 0) return r;
          return b.framerate.framesPerSecond.compareTo(a.framerate.framesPerSecond);
        });
      final elegido = candidatos.where((v) => rango(v.videoCodec) < 9).firstOrNull ??
          (candidatos.isNotEmpty ? candidatos.first : null);
      if (elegido != null && audio != null) {
        fuente = Fuente(
          url: elegido.url.toString(),
          audioUrl: audio.url.toString(),
          alto: elegido.videoResolution.height,
          fps: elegido.framerate.framesPerSecond.round(),
          videoCodec: elegido.videoCodec.split('.').first,
          audioCodec: audio.audioCodec.split('.').first,
          abr: (audio.bitrate.bitsPerSecond / 1000).round(),
          alturas: alturas,
          videoId: videoId,
          lufs: RegistroSonoridad.i.lufs(videoId),
        );
      } else {
        final muxed = m.muxed.sortByVideoQuality();
        if (muxed.isEmpty) throw Exception('Este video no tiene imagen disponible.');
        final mx = muxed.last;
        fuente = Fuente(url: mx.url.toString(), alto: mx.videoResolution.height,
            fps: mx.framerate.framesPerSecond.round(), videoCodec: 'avc1', audioCodec: 'aac',
            abr: 128, alturas: alturas, videoId: videoId, lufs: RegistroSonoridad.i.lufs(videoId));
      }
    }
    if (_cache.length > 300) _cache.clear();
    _cache[clave] = (DateTime.now(), fuente);
    return fuente;
  }

  /// Lo que hay en cache (para fundir o cambiar de pantalla sin esperar).
  Fuente? enCache(String videoId,
      {required bool video, String calidad = 'maxima', String codec = 'auto'}) {
    final g = _cache['$videoId|$video|$calidad|$codec'];
    if (g == null || DateTime.now().difference(g.$1) >= const Duration(minutes: 210)) return null;
    return g.$2;
  }

  /// La mejor pista de sonido para esa calidad.
  ///
  /// A igual tasa, Opus suena mejor que AAC (y es lo que YouTube sirve más alto, hasta 160 kb/s;
  /// el AAC normal se queda en 128): por eso cuenta un 15 % más al comparar. «normal» y «ahorro»
  /// ponen un tope de tasa para gastar menos datos.
  static AudioOnlyStreamInfo? elegirAudio(List<AudioOnlyStreamInfo> audios, {String calidad = 'maxima'}) {
    if (audios.isEmpty) return null;
    double puntos(AudioOnlyStreamInfo a) {
      final c = a.audioCodec.toLowerCase();
      return a.bitrate.bitsPerSecond * (c.startsWith('opus') ? 1.15 : 1.0);
    }
    final orden = List.of(audios)..sort((a, b) => puntos(b).compareTo(puntos(a)));
    final tope = switch (calidad) { 'ahorro' => 72000, 'normal' => 140000, _ => 1 << 30 };
    return orden.firstWhere((a) => a.bitrate.bitsPerSecond <= tope,
        orElse: () => orden.reduce((a, b) => a.bitrate.bitsPerSecond <= b.bitrate.bitsPerSecond ? a : b));
  }

  static int _tope(String calidad) {
    final n = int.tryParse(calidad);
    if (n != null) return n;
    // "maxima": lo mas alto que la pantalla puede mostrar
    for (final escalon in [2160, 1440, 1080, 720]) {
      if (altoPantalla >= escalon * 0.9) return escalon;
    }
    return 720;
  }
}

class Fuente {
  Fuente({required this.url, this.audioUrl, this.alto = 0, this.fps = 0, this.videoCodec = '',
      this.audioCodec = '', this.abr = 0, this.alturas = const [], this.archivo = '', this.videoId = '',
      this.lufs});

  final String url;
  final String? audioUrl;
  final int alto;
  final int fps;
  final String videoCodec;
  final String audioCodec;
  final int abr;
  final List<int> alturas;
  final String archivo;

  /// El video de YouTube de esta canción (si se sabe) y su sonoridad en LUFS (para «Volumen máximo»).
  final String videoId;
  final double? lufs;

  bool get local => archivo.isNotEmpty;

  /// ¿Suena con el recuadro de YouTube? (solo en la web)
  bool get esYouTubeWeb => url.startsWith('yt:');

  factory Fuente.archivo(String ruta, {String videoId = ''}) =>
      Fuente(url: ruta, archivo: ruta, videoId: videoId, lufs: RegistroSonoridad.i.lufs(videoId));

  /// Lo que se muestra en la insignia de calidad.
  String get insignia {
    if (url.startsWith('web:')) return 'TU MÚSICA';
    if (url.startsWith('https://api.audius.co/')) return 'AUDIUS';
    if (local) return kIsWeb && url.startsWith('http') ? 'COMUNIDAD' : 'EN EL TELÉFONO';
    if (url.startsWith('yt:')) return 'YOUTUBE';
    if (alto > 0) {
      final nombre = {4320: '8K', 2160: '4K', 1440: '2K'}[alto] ?? '${alto}p';
      return '$nombre${fps > 30 ? '$fps' : ''}';
    }
    final c = audioCodec.toUpperCase() == 'MP4A' ? 'AAC' : audioCodec.toUpperCase();
    return '$c $abr'.trim();
  }
}
