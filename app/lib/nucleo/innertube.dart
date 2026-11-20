import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:youtube_explode_dart/youtube_explode_dart.dart';

import 'sonoridad.dart';

/// Pide a YouTube las pistas de un video haciéndose pasar por la app de
/// YouTube de las gafas de Apple (cliente "VISIONOS").
///
/// Por qué existe (noviembre 2026): los clientes que trae youtube_explode
/// (android, androidVr, ios...) ya solo dejan bajar el primer trocito de cada
/// pista sin un "token PO" que solo saben fabricar las apps oficiales; después
/// YouTube contesta 403 y la canción no suena. Este cliente, el mismo que usa
/// hoy yt-dlp en el escritorio, da enlaces que se bajan enteros, sin firma ni
/// token. Además no necesita abrir la página del video, que es lo primero que
/// YouTube bloquea cuando una conexión pide mucho.
class Innertube {
  Innertube({http.Client? cliente}) : _http = cliente ?? http.Client();

  final http.Client _http;

  static const _uaVision = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 15_7_3) '
      'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15';
  static const _uaWeb = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

  String? _visitante;
  DateTime _visitanteDesde = DateTime(2000);
  Future<String?>? _pidiendoVisitante;

  /// El "visitante" es la cookie anónima de YouTube: sin ella contesta
  /// "confirma que no eres un bot".
  Future<String?> _visitorData({bool nuevo = false}) {
    final vigente = DateTime.now().difference(_visitanteDesde) < const Duration(hours: 6);
    if (!nuevo && _visitante != null && vigente) return Future.value(_visitante);
    return _pidiendoVisitante ??= () async {
      try {
        final r = await _http
            .post(
              Uri.parse('https://www.youtube.com/youtubei/v1/visitor_id?prettyPrint=false'),
              headers: {'Content-Type': 'application/json', 'User-Agent': _uaWeb},
              body: jsonEncode({
                'context': {
                  'client': {'clientName': 'WEB', 'clientVersion': '2.20260708.05.00', 'hl': 'es'},
                },
              }),
            )
            .timeout(const Duration(seconds: 15));
        String? vd;
        if (r.statusCode == 200) {
          final j = jsonDecode(r.body) as Map<String, dynamic>;
          vd = (j['responseContext'] as Map?)?['visitorData'] as String?;
        }
        vd ??= await _visitanteDeNext();
        if (vd != null && vd.isNotEmpty) {
          _visitante = vd;
          _visitanteDesde = DateTime.now();
        }
        return _visitante;
      } catch (_) {
        return _visitante;
      } finally {
        _pidiendoVisitante = null;
      }
    }();
  }

  Future<String?> _visitanteDeNext() async {
    final r = await _http
        .post(
          Uri.parse('https://www.youtube.com/youtubei/v1/next?prettyPrint=false'),
          headers: {'Content-Type': 'application/json', 'User-Agent': _uaWeb},
          body: jsonEncode({
            'context': {
              'client': {'clientName': 'WEB', 'clientVersion': '2.20260708.05.00', 'hl': 'es'},
            },
            'videoId': 'dQw4w9WgXcQ',
          }),
        )
        .timeout(const Duration(seconds: 15));
    if (r.statusCode != 200) return null;
    final j = jsonDecode(r.body) as Map<String, dynamic>;
    return (j['responseContext'] as Map?)?['visitorData'] as String?;
  }

  /// Las pistas del video como las entiende el resto de la app.
  Future<StreamManifest> manifiesto(String videoId) async {
    Object? fallo;
    for (var vuelta = 0; vuelta < 2; vuelta++) {
      try {
        final datos = await _player(videoId, await _visitorData(nuevo: vuelta > 0));
        final m = armarManifiesto(VideoId(videoId), datos);
        // lo fuerte que suena (para «Volumen máximo»): YouTube lo da gratis en la respuesta
        RegistroSonoridad.i.recordar(videoId, lufsDe(datos));
        return m;
      } catch (e) {
        fallo = e;
      }
    }
    throw fallo ?? Exception('YouTube no dio pistas para este video.');
  }

  Future<Map<String, dynamic>> _player(String videoId, String? visitante) async {
    final cliente = <String, dynamic>{
      'clientName': 'VISIONOS',
      'clientVersion': '1.02',
      'deviceMake': 'Apple',
      'deviceModel': 'RealityDevice17,1',
      'userAgent': _uaVision,
      'osName': 'visionOS',
      'osVersion': '26.5.23O471',
      'hl': 'es',
      if (visitante != null) 'visitorData': visitante,
    };
    final r = await _http
        .post(
          Uri.parse('https://www.youtube.com/youtubei/v1/player?prettyPrint=false'),
          headers: {
            'Content-Type': 'application/json',
            'User-Agent': _uaVision,
            'X-YouTube-Client-Name': '101',
            'X-YouTube-Client-Version': '1.02',
            'Origin': 'https://www.youtube.com',
            if (visitante != null) 'X-Goog-Visitor-Id': visitante,
          },
          body: jsonEncode({
            'context': {'client': cliente},
            'videoId': videoId,
            'contentCheckOk': true,
            'racyCheckOk': true,
          }),
        )
        .timeout(const Duration(seconds: 20));
    if (r.statusCode != 200) throw Exception('YouTube contestó ${r.statusCode}.');
    final j = jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
    final estado = (j['playabilityStatus'] as Map?)?['status'];
    if (estado != 'OK') {
      throw Exception('${(j['playabilityStatus'] as Map?)?['reason'] ?? 'Video no disponible'}');
    }
    return j;
  }

  /// Sonoridad integrada (LUFS) de la canción según YouTube (`loudnessDb`), o null.
  static double? lufsDe(Map<String, dynamic> datos) {
    final general = ((datos['playerConfig'] as Map?)?['audioConfig'] as Map?)?['loudnessDb'];
    if (general is num) return lufsDeYoutube(general);
    // si no viene en general, el de la pista de audio original (no la «DRC»)
    final formatos = (datos['streamingData'] as Map?)?['adaptiveFormats'];
    if (formatos is List) {
      for (final f in formatos.whereType<Map>()) {
        if (f['isDrc'] == true) continue;
        final l = f['loudnessDb'];
        if (l is num && '${f['mimeType'] ?? ''}'.startsWith('audio/')) return lufsDeYoutube(l);
      }
    }
    return null;
  }

  /// ¿Es la pista «DRC» (volumen estable) de YouTube? Viene ya comprimida: suena peor.
  static bool esDrc(Map f) {
    if (f['isDrc'] == true) return true;
    final x = f['xtags'];
    return x is String && x.contains('drc');
  }

  /// Convierte la respuesta de YouTube en un [StreamManifest] (separado para probarlo).
  static StreamManifest armarManifiesto(VideoId id, Map<String, dynamic> datos) {
    final sd = (datos['streamingData'] as Map?) ?? const {};
    final pistas = <StreamInfo>[];
    // la pista DRC solo si no hay otra de sonido
    final adaptativos = sd['adaptiveFormats'];
    final hayNormal = adaptativos is List &&
        adaptativos.whereType<Map>().any((f) => '${f['mimeType'] ?? ''}'.startsWith('audio/') && !esDrc(f));
    void leer(Object? lista, {required bool adaptativo}) {
      if (lista is! List) return;
      for (final f in lista.whereType<Map>()) {
        final url = f['url'];
        final mime = f['mimeType'];
        if (url is! String || mime is! String) continue;
        final tamano = int.tryParse('${f['contentLength'] ?? ''}') ?? 0;
        if (tamano <= 0) continue;
        final MediaType tipo;
        try {
          tipo = MediaType.parse(mime);
        } catch (_) {
          continue;
        }
        final codecs = (tipo.parameters['codecs'] ?? '').split(',').map((c) => c.trim()).toList();
        final StreamContainer contenedor;
        try {
          contenedor = StreamContainer.parse(tipo.subtype);
        } catch (_) {
          continue;
        }
        final itag = (f['itag'] as num?)?.toInt() ?? 0;
        final tasa = Bitrate((f['bitrate'] as num?)?.toInt() ?? 0);
        final uri = Uri.parse(url);
        final pista = f['audioTrack'];
        if (tipo.type == 'audio') {
          // en videos doblados solo la pista original
          if (pista is Map && pista['audioIsDefault'] == false) continue;
          if (hayNormal && esDrc(f)) continue;
          pistas.add(AudioOnlyStreamInfo(id, itag, uri, contenedor, FileSize(tamano), tasa,
              codecs.first, '${f['audioQuality'] ?? f['quality'] ?? ''}', const [], tipo, null));
          continue;
        }
        if (tipo.type != 'video') continue;
        final alto = (f['height'] as num?)?.toInt() ?? 0;
        final ancho = (f['width'] as num?)?.toInt() ?? 0;
        final calidad = calidadDe(alto);
        final etiqueta = '${f['qualityLabel'] ?? '${alto}p'}';
        final cuadros = Framerate((f['fps'] as num?)?.toInt() ?? 24);
        if (!adaptativo && codecs.length > 1) {
          pistas.add(MuxedStreamInfo(id, itag, uri, contenedor, FileSize(tamano), tasa, codecs[1],
              codecs[0], etiqueta, calidad, VideoResolution(ancho, alto), cuadros, tipo));
        } else if (adaptativo) {
          pistas.add(VideoOnlyStreamInfo(id, itag, uri, contenedor, FileSize(tamano), tasa,
              codecs.first, etiqueta, calidad, VideoResolution(ancho, alto), cuadros, const [], tipo));
        }
      }
    }

    leer(sd['adaptiveFormats'], adaptativo: true);
    leer(sd['formats'], adaptativo: false);
    if (pistas.isEmpty) throw Exception('YouTube no dio pistas para este video.');
    return StreamManifest(pistas);
  }

  static VideoQuality calidadDe(int alto) {
    if (alto >= 4320) return VideoQuality.high4320;
    if (alto >= 2160) return VideoQuality.high2160;
    if (alto >= 1440) return VideoQuality.high1440;
    if (alto >= 1080) return VideoQuality.high1080;
    if (alto >= 720) return VideoQuality.high720;
    if (alto >= 480) return VideoQuality.medium480;
    if (alto >= 360) return VideoQuality.medium360;
    if (alto >= 240) return VideoQuality.low240;
    if (alto > 0) return VideoQuality.low144;
    return VideoQuality.unknown;
  }

  void cerrar() => _http.close();
}
