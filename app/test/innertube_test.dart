import 'package:caudal/nucleo/innertube.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:youtube_explode_dart/youtube_explode_dart.dart';

void main() {
  final datos = {
    'playabilityStatus': {'status': 'OK'},
    'streamingData': {
      'adaptiveFormats': [
        {'itag': 251, 'url': 'https://x.googlevideo.com/a?c=VISIONOS', 'mimeType': 'audio/webm; codecs="opus"',
         'bitrate': 140000, 'contentLength': '3433755', 'audioQuality': 'AUDIO_QUALITY_MEDIUM'},
        {'itag': 140, 'url': 'https://x.googlevideo.com/b', 'mimeType': 'audio/mp4; codecs="mp4a.40.2"',
         'bitrate': 130000, 'contentLength': '3000000'},
        // pista doblada: se descarta
        {'itag': 251, 'url': 'https://x.googlevideo.com/d', 'mimeType': 'audio/webm; codecs="opus"',
         'bitrate': 140000, 'contentLength': '3433755', 'audioTrack': {'audioIsDefault': false}},
        {'itag': 137, 'url': 'https://x.googlevideo.com/v', 'mimeType': 'video/mp4; codecs="avc1.640028"',
         'bitrate': 4000000, 'contentLength': '80000000', 'width': 1920, 'height': 1080, 'fps': 30,
         'qualityLabel': '1080p'},
        // sin url (cifrada): se descarta
        {'itag': 248, 'signatureCipher': 's=..', 'mimeType': 'video/webm; codecs="vp9"', 'contentLength': '1'},
      ],
      'formats': [
        {'itag': 18, 'url': 'https://x.googlevideo.com/m', 'mimeType': 'video/mp4; codecs="avc1.42001E, mp4a.40.2"',
         'bitrate': 500000, 'contentLength': '9000000', 'width': 640, 'height': 360, 'fps': 25},
      ],
    },
  };

  test('arma el manifiesto con audio, video y pista mixta', () {
    final m = Innertube.armarManifiesto(VideoId('dQw4w9WgXcQ'), datos);
    expect(m.audioOnly.length, 2);
    expect(m.audioOnly.withHighestBitrate().audioCodec, 'opus');
    expect(m.audioOnly.withHighestBitrate().size.totalBytes, 3433755);
    expect(m.videoOnly.single.videoResolution.height, 1080);
    expect(m.videoOnly.single.videoCodec, 'avc1.640028');
    expect(m.muxed.single.audioCodec, 'mp4a.40.2');
    expect(m.muxed.single.videoResolution.height, 360);
  });

  test('sin pistas avisa', () {
    expect(() => Innertube.armarManifiesto(VideoId('dQw4w9WgXcQ'), {'streamingData': {}}), throwsException);
  });
}
