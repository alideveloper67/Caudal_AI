// La paleta de la carátula que suena (donadores): un color de fondo, uno vivo para
// los acentos y uno de contraste para el degradado.
//
// La carátula se decodifica ya reducida (32 px: lo hace el decodificador del motor, fuera del
// hilo de la interfaz) y recorrer sus 1.024 píxeles no cuesta nada. Cada URL se calcula una
// sola vez (caché de las últimas 80) y las peticiones repetidas comparten el mismo cálculo.

import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';

@immutable
class PaletaPortada {
  const PaletaPortada({required this.fondo, required this.acento, required this.contraste});

  /// El tono principal, oscurecido: tiñe el fondo y la tarjeta de la letra.
  final Color fondo;

  /// Un tono vivo y claro, legible sobre fondo oscuro: botones activos, barra, insignia.
  final Color acento;

  /// Un segundo tono de la carátula (o una variación del primero si es de un solo color):
  /// da el otro extremo del degradado.
  final Color contraste;

  static const neutra = PaletaPortada(
    fondo: Color(0xFF2A3240),
    acento: Color(0xFF22D3EE),
    contraste: Color(0xFF1B2230),
  );

  static PaletaPortada lerp(PaletaPortada a, PaletaPortada b, double t) => PaletaPortada(
        fondo: Color.lerp(a.fondo, b.fondo, t)!,
        acento: Color.lerp(a.acento, b.acento, t)!,
        contraste: Color.lerp(a.contraste, b.contraste, t)!,
      );

  @override
  bool operator ==(Object other) =>
      other is PaletaPortada && other.fondo == fondo && other.acento == acento && other.contraste == contraste;

  @override
  int get hashCode => Object.hash(fondo, acento, contraste);
}

/// Interpola dos paletas (para [TweenAnimationBuilder]).
class PaletaTween extends Tween<PaletaPortada> {
  PaletaTween({super.begin, super.end});
  @override
  PaletaPortada lerp(double t) => PaletaPortada.lerp(begin ?? end!, end ?? begin!, t);
}

class _Grupo {
  double r = 0, g = 0, b = 0, n = 0, peso = 0;
  double h = 0;
}

/// La paleta de unos píxeles RGBA (4 bytes por píxel). Pura y determinista: sirve igual en la
/// app que en las pruebas. Sin píxeles útiles (todo muy oscuro o vacío) devuelve [PaletaPortada.neutra].
PaletaPortada paletaDePixeles(Uint8List rgba) {
  final grupos = <int, _Grupo>{};
  for (var i = 0; i + 3 < rgba.length; i += 4) {
    if (rgba[i + 3] < 128) continue; // transparente
    final c = Color.fromARGB(255, rgba[i], rgba[i + 1], rgba[i + 2]);
    final hsv = HSVColor.fromColor(c);
    if (hsv.value < 0.16) continue;
    // 15 matices x 4 niveles de saturación; los grises caen todos en el nivel 0
    final gris = hsv.saturation < 0.12;
    final g = gris ? 0 : (hsv.hue ~/ 24) * 10 + 10 + (hsv.saturation * 3.99).floor();
    final b = grupos.putIfAbsent(g, () => _Grupo()..h = gris ? -1 : hsv.hue);
    b.r += c.r;
    b.g += c.g;
    b.b += c.b;
    b.n += 1;
    b.peso += 1 + hsv.saturation * 2 + hsv.value;
  }
  if (grupos.isEmpty) return PaletaPortada.neutra;
  final lista = grupos.values.toList()..sort((x, y) => y.peso.compareTo(x.peso));
  Color media(_Grupo g) => Color.from(alpha: 1, red: g.r / g.n, green: g.g / g.n, blue: g.b / g.n);

  final principal = lista.first;
  final cp = media(principal);
  final hp = HSVColor.fromColor(cp);
  final fondo = hp.withSaturation(math.min(1, hp.saturation * 1.05)).withValue(hp.value.clamp(0.28, 0.58)).toColor();

  // el acento: el grupo más vivo entre los que pesan algo (al menos 8% del principal)
  _Grupo vivo = principal;
  var mejor = -1.0;
  for (final g in lista) {
    if (g.peso < principal.peso * 0.08) continue;
    final h = HSVColor.fromColor(media(g));
    final puntaje = h.saturation * (0.4 + h.value) * math.sqrt(g.peso);
    if (puntaje > mejor) {
      mejor = puntaje;
      vivo = g;
    }
  }
  final hv = HSVColor.fromColor(media(vivo));
  final Color acento = hv.saturation < 0.18
      ? const Color(0xFFE9ECF3) // carátula en grises: un blanco suave
      : hv.withSaturation(hv.saturation.clamp(0.5, 0.9)).withValue(hv.value.clamp(0.82, 1.0)).toColor();

  // el contraste: otro matiz distinto del principal (a más de 40 grados); si no hay, el mismo
  // girado un poco y más oscuro
  Color contraste = Color.lerp(fondo, Colors.black, 0.45)!;
  for (final g in lista) {
    if (identical(g, principal) || g.peso < principal.peso * 0.12) continue;
    final h = HSVColor.fromColor(media(g));
    final distancia = (principal.h < 0 || g.h < 0) ? 0.0 : ((g.h - principal.h).abs() % 360);
    final d = math.min(distancia, 360 - distancia);
    if (d > 40 || (principal.h < 0 && g.h >= 0)) {
      contraste = h.withValue(h.value.clamp(0.22, 0.5)).withSaturation(math.min(1, h.saturation * 1.05)).toColor();
      break;
    }
  }
  return PaletaPortada(fondo: fondo, acento: acento, contraste: contraste);
}

final Map<String, PaletaPortada> _hechas = {};
final Map<String, Future<PaletaPortada>> _enCurso = {};

/// ¿Ya está calculada? (para pintar sin esperar al volver a una canción).
PaletaPortada? paletaEnCache(String url) => _hechas[url];

/// La paleta de la carátula [url] (red, archivo o memoria). Nunca falla: si no se puede leer,
/// devuelve [PaletaPortada.neutra] (y esa no se guarda, por si fue un fallo pasajero).
Future<PaletaPortada> paletaDe(String url) {
  if (url.isEmpty) return Future.value(PaletaPortada.neutra);
  final hecha = _hechas[url];
  if (hecha != null) return Future.value(hecha);
  // (cuerpo con llaves: si devolviera el Future quitado, whenComplete esperaría a sí mismo)
  return _enCurso[url] ??= _calcular(url).whenComplete(() {
    _enCurso.remove(url);
  });
}

/// Solo para pruebas.
void olvidarPaletas() {
  _hechas.clear();
  _enCurso.clear();
}

Future<PaletaPortada> _calcular(String url) async {
  try {
    final mem = PortadasMem.bytes(url);
    if (PortadasMem.esRef(url) && mem == null) return PaletaPortada.neutra;
    final ImageProvider proveedor = mem != null
        ? ResizeImage(MemoryImage(mem), width: 32, height: 32)
        : url.startsWith('http')
            ? ResizeImage(CachedNetworkImageProvider(url), width: 32, height: 32)
            : ResizeImage(FileImage(File(url)), width: 32, height: 32);
    final completer = Completer<ImageInfo>();
    final stream = proveedor.resolve(ImageConfiguration.empty);
    late ImageStreamListener oyente;
    oyente = ImageStreamListener((info, _) {
      if (completer.isCompleted) {
        info.dispose();
      } else {
        completer.complete(info);
      }
      stream.removeListener(oyente);
    }, onError: (e, _) {
      if (!completer.isCompleted) completer.completeError(e);
      stream.removeListener(oyente);
    });
    stream.addListener(oyente);
    final ImageInfo info;
    try {
      info = await completer.future.timeout(const Duration(seconds: 8));
    } catch (_) {
      stream.removeListener(oyente);
      return PaletaPortada.neutra;
    }
    final ByteData? datos;
    try {
      datos = await info.image.toByteData(format: ui.ImageByteFormat.rawRgba);
    } finally {
      info.dispose();
    }
    if (datos == null) return PaletaPortada.neutra;
    final p = paletaDePixeles(datos.buffer.asUint8List(datos.offsetInBytes, datos.lengthInBytes));
    if (_hechas.length >= 80) _hechas.remove(_hechas.keys.first);
    _hechas[url] = p;
    return p;
  } catch (_) {
    return PaletaPortada.neutra;
  }
}
