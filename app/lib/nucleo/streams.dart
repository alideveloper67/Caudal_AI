import 'package:youtube_explode_dart/youtube_explode_dart.dart';

import 'motor_local.dart';

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

  Future<Fuente> resolver(String videoId,
      {required bool video, String calidad = 'maxima', String codec = 'auto'}) async {
    final clave = '$videoId|$video|$calidad|$codec';
    final guardado = _cache[clave];
    if (guardado != null && DateTime.now().difference(guardado.$1) < const Duration(minutes: 210)) {
      return guardado.$2;
    }
    final m = await motor.manifiesto(videoId);
    final audios = m.audioOnly.toList()
      ..sort((a, b) => b.bitrate.bitsPerSecond.compareTo(a.bitrate.bitsPerSecond));
    AudioOnlyStreamInfo? audio;
    if (audios.isNotEmpty) {
      final tope = switch (calidad) { 'ahorro' => 72000, 'normal' => 140000, _ => 1 << 30 };
      audio = video
          ? audios.first
          : audios.firstWhere((a) => a.bitrate.bitsPerSecond <= tope, orElse: () => audios.last);
    }
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
        fuente = Fuente(url: muxed.last.url.toString(), audioCodec: 'aac', abr: 128);
      } else {
        fuente = Fuente(
          url: audio.url.toString(),
          audioCodec: audio.audioCodec.split('.').first,
          abr: (audio.bitrate.bitsPerSecond / 1000).round(),
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
        );
      } else {
        final muxed = m.muxed.sortByVideoQuality();
        if (muxed.isEmpty) throw Exception('Este video no tiene imagen disponible.');
        final mx = muxed.last;
        fuente = Fuente(url: mx.url.toString(), alto: mx.videoResolution.height,
            fps: mx.framerate.framesPerSecond.round(), videoCodec: 'avc1', audioCodec: 'aac',
            abr: 128, alturas: alturas);
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
      this.audioCodec = '', this.abr = 0, this.alturas = const [], this.archivo = ''});

  final String url;
  final String? audioUrl;
  final int alto;
  final int fps;
  final String videoCodec;
  final String audioCodec;
  final int abr;
  final List<int> alturas;
  final String archivo;

  bool get local => archivo.isNotEmpty;

  factory Fuente.archivo(String ruta) => Fuente(url: ruta, archivo: ruta);

  /// Lo que se muestra en la insignia de calidad.
  String get insignia {
    if (local) return 'EN EL TELÉFONO';
    if (alto > 0) {
      final nombre = {4320: '8K', 2160: '4K', 1440: '2K'}[alto] ?? '${alto}p';
      return '$nombre${fps > 30 ? '$fps' : ''}';
    }
    final c = audioCodec.toUpperCase() == 'MP4A' ? 'AAC' : audioCodec.toUpperCase();
    return '$c $abr'.trim();
  }
}
