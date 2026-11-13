// En que telefono corre la app, en un solo sitio.
//
// Android e iPhone se parecen poco en lo que dejan hacer: donde se guardan los
// archivos, si se puede instalar una version nueva, como se presenta el
// navegador... Todo el nucleo pregunta aqui en vez de mirar Platform por su
// cuenta, y asi las pruebas pueden fingir que corren en un iPhone.

import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';

class Plataforma {
  Plataforma._();

  /// Solo para las pruebas: fingir que se corre en otro sistema.
  @visibleForTesting
  static TargetPlatform? forzada;

  static bool get esIOS =>
      forzada != null ? forzada == TargetPlatform.iOS : (!kIsWeb && Platform.isIOS);

  static bool get esAndroid =>
      forzada != null ? forzada == TargetPlatform.android : (!kIsWeb && Platform.isAndroid);
}

const String _agenteAndroid =
    'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Mobile Safari/537.36';

/// Safari de iPhone. El WebView de iOS es Safari por dentro: presentarse como
/// Chrome de Android hace que muchas webs le sirvan un reproductor que alli no
/// funciona y no llegue a pedir el video. Como Safari reciben su version
/// (casi siempre HLS), que se ve pasar y ffmpeg sabe juntar.
const String _agenteIOS =
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 '
    '(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1';

/// Con que navegador nos presentamos, en el WebView y al bajar lo capturado.
///
/// Tiene que ser el mismo en los dos sitios: hay servidores que firman la
/// direccion del video para el navegador que la pidio.
String get agenteDelTelefono => Plataforma.esIOS ? _agenteIOS : _agenteAndroid;
