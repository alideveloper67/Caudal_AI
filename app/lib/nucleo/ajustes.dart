import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'plataforma.dart';

/// Preferencias de la app. Mismas claves que Caudal Escritorio, para que las
/// que se comparten (calidad, ecualizador, region...) signifiquen lo mismo.
class Ajustes extends ChangeNotifier {
  Ajustes._(this._prefs, this._prefijo);

  final SharedPreferences _prefs;
  final String _prefijo;

  /// Cada cuenta tiene sus ajustes: el prefijo es su id.
  static Future<Ajustes> cargar(String cuenta) async {
    final prefs = await SharedPreferences.getInstance();
    return Ajustes._(prefs, 'aj.$cuenta.');
  }

  static const Map<String, Object> defectos = {
    'region': 'PE',
    'calidad_audio': 'maxima', // maxima | normal | ahorro
    'calidad_audio_datos': 'normal', // con datos moviles
    'calidad_video': 'maxima', // maxima | 2160 | 1440 | 1080 | 720 | 480 | 360
    'codec_video': 'auto', // auto | sin_av1 | compatible
    'crossfade': 0,
    'normalizar': true,
    'traducir_letra': true, // la traduccion bajo cada linea de la letra
    'acento': 'cian', // color de la app (ver Aspecto.acentos)
    'fondo': 'oscuro', // fondo de la app (ver Aspecto.fondos)
    'tamano_personaje': 160, // alto del personaje del fondo con personaje (se cambia pellizcándolo)
    // dónde dejó el personaje del fondo (0..1 del espacio libre; -1 = su esquina de siempre) y si baila
    'personaje_x': -1.0,
    'personaje_y': -1.0,
    'personaje_baila': true,
    'super_volumen': 0, // 0..4
    'ecualizador': false,
    'eq_bandas': '[0,0,0,0,0,0,0,0,0,0]',
    'eq_preset': 'Plano',
    'velocidad': 1.0,
    'autoplay': true,
    'sponsorblock': true,
    'sponsorblock_videos': false,
    'preferir_descargado': true,
    'aleatorio': false,
    'repetir': 'no', // no | todo | una
    'formato_audio': 'mp3', // mp3 | m4a | opus | flac | wav
    'bitrate_mp3': '320',
    'calidad_descarga': 'mejor',
    'tipo_descarga': 'audio', // completo | audio | video
    'solo_wifi_descargas': false,
    'letras_auto': false,
    'volumen': 100,
    'guardar_publico': true,
    'descarga_fuerte': false,
    // con wifi, baja sola tus me gusta y lo mas escuchado (ver DescargaInteligente)
    'descarga_inteligente': false,
    'descarga_inteligente_gb': 5, // tope de espacio, en GB
    // fundido que recorta los silencios del final y del inicio
    'transicion_dj': true,
    // «Mezcla DJ»: enlaza las canciones como un DJ (la siguiente entra antes del
    // final, con cambio de graves); duracion del cambio de 4 a 16 s
    'mezcla_dj': false,
    'mezcla_dj_seg': 8,
    'mezcla_dj_graves': true,
    // el temporizador para dormir baja el volumen los ultimos 30 s
    'apagado_suave': true,
    // quita animaciones y adornos para equipos lentos; el sonido no cambia
    'modo_ligero': false,
    // «Modo gamer» (ver gamer_control.dart): interruptor, ahorro al jugar, perfil de sonido
    // y lo que hay que devolver al apagarlo
    'gamer_activo': false,
    'gamer_ahorro': true,
    'gamer_sonido': '',
    'gamer_ligero_previo': '',
    'gamer_eq_previo': '',
    'gamer_progreso': '',
  };

  T _valor<T>(String clave) {
    final v = _prefs.get(_prefijo + clave);
    final d = defectos[clave];
    if (v == null) return d as T;
    if (T == double && v is int) return v.toDouble() as T;
    if (T == int && v is double) return v.round() as T;
    if (v is T) return v as T;
    return d as T;
  }

  String texto(String clave) => _valor<String>(clave);
  int entero(String clave) => _valor<int>(clave);
  double decimal(String clave) => _valor<double>(clave);
  bool sino(String clave) => _valor<bool>(clave);

  /// Las bandas del ecualizador decodificadas, recordadas mientras su texto no
  /// cambie (el fundido entre canciones las pide 20 veces por segundo).
  String? _eqTexto;
  List<int> _eqBandas = const [];

  List<int> get bandasEq {
    final t = texto('eq_bandas');
    if (t != _eqTexto) {
      try {
        _eqBandas = (jsonDecode(t) as List).map((e) => (e as num).toInt()).toList();
      } catch (_) {
        _eqBandas = List.filled(10, 0);
      }
      _eqTexto = t;
    }
    return List.of(_eqBandas); // una copia: quien la reciba puede cambiarla
  }

  Future<void> poner(String clave, Object valor, {bool avisar = true}) async {
    final k = _prefijo + clave;
    if (valor is String) {
      await _prefs.setString(k, valor);
    } else if (valor is bool) {
      await _prefs.setBool(k, valor);
    } else if (valor is int) {
      await _prefs.setInt(k, valor);
    } else if (valor is double) {
      await _prefs.setDouble(k, valor);
    } else if (valor is List) {
      await _prefs.setString(k, jsonEncode(valor));
    }
    if (avisar) notifyListeners();
  }

  /// Lo que se sube a la nube (lo comun a todos los dispositivos).
  static const compartidos = [
    'region', 'calidad_audio', 'calidad_video', 'codec_video', 'normalizar', 'super_volumen',
    'ecualizador', 'eq_bandas', 'eq_preset', 'autoplay', 'sponsorblock', 'sponsorblock_videos',
    'formato_audio', 'bitrate_mp3', 'crossfade',
    'descarga_inteligente', 'descarga_inteligente_gb', 'transicion_dj', 'apagado_suave',
  ];

  // atajos que usa el gestor de descargas
  String get formatoAudio => texto('formato_audio');
  /// En iPhone no hay "música del teléfono" en la que escribir: siempre no.
  bool get guardarEnPublico => Plataforma.esAndroid && sino('guardar_publico');

  /// Si la opción "Guardar en la música del teléfono" tiene sentido aquí.
  static bool get hayGuardarEnPublico => Plataforma.esAndroid;
  bool get modoMusica => sino('descarga_fuerte');
  bool get descargaDirecta => true;

  Map<String, Object?> paraNube() => {for (final k in compartidos) k: _prefs.get(_prefijo + k)};
}
