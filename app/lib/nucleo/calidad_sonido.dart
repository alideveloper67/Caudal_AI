import 'streams.dart' show Fuente;

/// Lo que se muestra en la insignia de calidad del reproductor: el códec y la tasa de lo que
/// de verdad suena. Solo usa lo que ya sabe el reproductor de la fuente abierta (nada se mide
/// ni se pide a internet); lo que no se sabe no se inventa.
class CalidadSonido {
  const CalidadSonido(this.etiqueta, this.detalle);

  /// Texto corto para la insignia (p. ej. «Opus · 160 kbps»).
  final String etiqueta;

  /// La misma información dicha entera, para lectores de pantalla y la ayuda al mantener pulsado.
  final String detalle;

  @override
  bool operator ==(Object other) => other is CalidadSonido && other.etiqueta == etiqueta && other.detalle == detalle;

  @override
  int get hashCode => Object.hash(etiqueta, detalle);
}

/// Nombre bonito de un códec de audio tal como lo dice YouTube o mpv (null si viene vacío).
String? nombreCodecAudio(String codec) {
  final c = codec.trim().toLowerCase().split('.').first;
  if (c.isEmpty) return null;
  if (c == 'mp4a' || c == 'aac' || c == 'aac_latm') return 'AAC';
  if (c == 'opus') return 'Opus';
  if (c == 'vorbis') return 'Vorbis';
  if (c == 'flac') return 'FLAC';
  if (c == 'mp3' || c == 'mp3float') return 'MP3';
  if (c == 'alac') return 'ALAC';
  if (c.startsWith('pcm') || c == 'wav') return 'WAV';
  if (c == 'ac-3' || c == 'ac3') return 'AC-3';
  if (c == 'ec-3' || c == 'eac3') return 'E-AC-3';
  return codec.trim().toUpperCase();
}

/// Nombre bonito de un códec de video (AVC1 → H.264…).
String? nombreCodecVideo(String codec) {
  final c = codec.trim().toLowerCase().split('.').first;
  if (c.isEmpty) return null;
  if (c.startsWith('avc')) return 'H.264';
  if (c.startsWith('hev') || c.startsWith('hvc')) return 'HEVC';
  if (c.startsWith('vp09') || c == 'vp9') return 'VP9';
  if (c.startsWith('vp08') || c == 'vp8') return 'VP8';
  if (c.startsWith('av01') || c == 'av1') return 'AV1';
  return codec.trim().toUpperCase();
}

const _extensiones = {
  'mp3': 'MP3',
  'm4a': 'AAC',
  'aac': 'AAC',
  'opus': 'Opus',
  'ogg': 'Vorbis',
  'oga': 'Vorbis',
  'flac': 'FLAC',
  'wav': 'WAV',
  'alac': 'ALAC',
  'weba': 'Opus',
};

/// La calidad de [f], o null si no hay nada que decir (nada abierto o sin datos).
///
/// * Audio: «Opus · 160 kbps»; si la tasa no se conoce, solo el códec.
/// * Video ([enVideo] y la fuente trae imagen): «1080p60 · H.264».
/// * Archivo del teléfono: el códec por la extensión y «local».
/// * Reproductor de YouTube del navegador: «YouTube» (no da más datos).
CalidadSonido? calidadDe(Fuente? f, {bool enVideo = false}) {
  if (f == null) return null;
  if (f.url.startsWith('https://api.audius.co/')) {
    return const CalidadSonido('Audius', 'Música libre de Audius');
  }
  if (f.local) {
    final ext = f.archivo.contains('.') ? f.archivo.split('.').last.toLowerCase() : '';
    final c = _extensiones[ext];
    return c == null
        ? const CalidadSonido('Local', 'Suena desde un archivo del teléfono')
        : CalidadSonido('$c · local', '$c, desde un archivo del teléfono');
  }
  if (f.url.startsWith('yt:')) return const CalidadSonido('YouTube', 'Suena con el reproductor de YouTube');
  if (enVideo && f.alto > 0) {
    final res = {4320: '8K', 2160: '4K', 1440: '2K'}[f.alto] ?? '${f.alto}p';
    final fps = f.fps > 30 ? '${f.fps}' : '';
    final c = nombreCodecVideo(f.videoCodec);
    return CalidadSonido(c == null ? '$res$fps' : '$res$fps · $c',
        'Video a $res${f.fps > 30 ? ' y ${f.fps} cuadros por segundo' : ''}${c == null ? '' : ', $c'}');
  }
  final c = nombreCodecAudio(f.audioCodec);
  if (c == null && f.abr <= 0) return null;
  final tasa = f.abr > 0 ? '${f.abr} kbps' : '';
  final etiqueta = [?c, if (tasa.isNotEmpty) tasa].join(' · ');
  final detalle = c == null
      ? 'Audio a ${f.abr} kilobits por segundo'
      : f.abr > 0 ? 'Audio $c a ${f.abr} kilobits por segundo' : 'Audio $c';
  return CalidadSonido(etiqueta, detalle);
}
