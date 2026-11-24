// Dónde cae una grabación dentro de otra, comparando su sonido (mismas cuentas en el escritorio:
// escritorio/descargador/cotejo_audio.py).
//
// Un videoclip lleva la misma grabación que la canción oficial, pero con intro, escenas o cortes; la
// canción oficial trae la letra con sus tiempos. Comparando los golpes de cada banda de frecuencia se
// sabe al centésimo cuánto está corrida una respecto a la otra, sin entender lo que se canta.

import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:ffmpeg_kit_flutter_new/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new/return_code.dart';
import 'package:flutter/foundation.dart' show compute, kIsWeb;
import 'package:path_provider/path_provider.dart';

/// Desde qué segundo de lo que suena, y cuánto hay que sumar a los tiempos de la otra grabación.
typedef TramoCotejo = (double desde, double suma);

class CotejoAudio {
  CotejoAudio._();

  static const hz = 8000;
  static const _salto = 160; // 20 ms
  static const _ventana = 1024;
  static const bandas = 16;
  static const _trozo = 25 * hz ~/ _salto; // cuadros de cada trozo que se busca
  static const escucha = 150; // segundos que se bajan de cada una

  /// Menos parecido: no es la misma grabación.
  static const parecidoMin = 0.62;

  /// Las líneas `(ms, texto)` de la otra grabación, puestas donde caen en la que suena.
  static List<(int, String)> colocar(List<(int, String)> lineas, List<TramoCotejo> tramos) => [
        for (final (ms, texto) in lineas) (_caer(ms / 1000, tramos), texto),
      ];

  static int _caer(double s, List<TramoCotejo> tramos) {
    double? t;
    for (var i = 0; i < tramos.length; i++) {
      final hasta = i + 1 < tramos.length ? tramos[i + 1].$1 : double.infinity;
      final x = s + tramos[i].$2;
      if (x < hasta || t == null) t = min(x, hasta);
      if (x < hasta) break;
    }
    return max(0, (t! * 1000).round());
  }

  /// Los tramos de lo que suena ([v]) respecto a la otra grabación ([a]), o null si no son la misma.
  /// Con un solo corrimiento (lo normal) devuelve un solo tramo. Muestras mono a [hz].
  static List<TramoCotejo>? desfases(Float64List v, Float64List a) {
    final fv = _rasgos(v), fa = _rasgos(a);
    if (fv == null || fa == null) return null;
    return _comparar(fv, fa);
  }

  // ------------------------------------------------------------ rasgos

  /// Los golpes (subidas de energía) de cada banda, cada 20 ms.
  static List<Float64List>? _rasgos(Float64List x) {
    final n = 1 + (x.length - _ventana) ~/ _salto;
    if (n < 50) return null;
    final w = Float64List(_ventana);
    for (var i = 0; i < _ventana; i++) {
      w[i] = 0.5 - 0.5 * cos(2 * pi * i / (_ventana - 1));
    }
    final bordes = [
      for (var b = 0; b <= bandas; b++) (150 * pow(3600 / 150, b / bandas) / (hz / _ventana)).round()
    ];
    final m = [for (var b = 0; b < bandas; b++) Float64List(n)];
    final fft = _Fft(_ventana);
    final re = Float64List(_ventana), im = Float64List(_ventana);
    // dos cuadros por transformada: uno en la parte real y otro en la imaginaria
    for (var k = 0; k < n; k += 2) {
      final i0 = k * _salto, i1 = (k + 1 < n ? k + 1 : k) * _salto;
      for (var i = 0; i < _ventana; i++) {
        re[i] = x[i0 + i] * w[i];
        im[i] = x[i1 + i] * w[i];
      }
      fft.directa(re, im);
      for (var b = 0; b < bandas; b++) {
        final desde = bordes[b], hasta = max(bordes[b] + 1, bordes[b + 1]);
        var e0 = 0.0, e1 = 0.0;
        for (var q = desde; q < hasta; q++) {
          final r = _ventana - q;
          final ar = (re[q] + re[r]) / 2, ai = (im[q] - im[r]) / 2;
          final br = (im[q] + im[r]) / 2, bi = (re[r] - re[q]) / 2;
          e0 += ar * ar + ai * ai;
          e1 += br * br + bi * bi;
        }
        m[b][k] = log(1e-7 + e0 / (hasta - desde));
        if (k + 1 < n) m[b][k + 1] = log(1e-7 + e1 / (hasta - desde));
      }
    }
    for (final f in m) {
      var previo = f[0], suma = 0.0;
      for (var i = 0; i < n; i++) {
        final d = max(0.0, f[i] - previo);
        previo = f[i];
        f[i] = d;
        suma += d;
      }
      final media = suma / n;
      var var2 = 0.0;
      for (var i = 0; i < n; i++) {
        f[i] -= media;
        var2 += f[i] * f[i];
      }
      final desv = sqrt(var2 / n) + 1e-6;
      for (var i = 0; i < n; i++) {
        f[i] /= desv;
      }
    }
    return m;
  }

  /// Parecido (-1..1) del trozo de [v] que empieza en [ini] puesto en el cuadro [p] de [a].
  static double _parecido(List<Float64List> v, int ini, int largo, List<Float64List> a, int p) {
    final i = max(0, p), j = min(a[0].length, p + largo);
    if (j - i < largo * 0.3) return 0;
    var s = 0.0, vv = 0.0, aa = 0.0;
    for (var b = 0; b < bandas; b++) {
      final fv = v[b], fa = a[b];
      for (var k = i; k < j; k++) {
        final x = fv[ini + k - p], y = fa[k];
        s += x * y;
        vv += x * x;
        aa += y * y;
      }
    }
    return s / sqrt(vv * aa + 1e-9);
  }

  static List<TramoCotejo>? _comparar(List<Float64List> v, List<Float64List> a) {
    final nv = v[0].length, na = a[0].length;
    if (nv < _trozo * 0.6 || na < _trozo * 0.6) return null;
    final largo = min(_trozo, min(nv, na));
    var tam = 1;
    while (tam < na + largo) {
      tam <<= 1;
    }
    final fft = _Fft(tam);
    final ar = <Float64List>[], ai = <Float64List>[];
    for (var b = 0; b < bandas; b++) {
      final re = Float64List(tam)..setRange(0, na, a[b]);
      final im = Float64List(tam);
      fft.directa(re, im);
      ar.add(re);
      ai.add(im);
    }
    final hallados = <({int ini, int suma, double parecido})>[];
    for (var ini = 0; ini + largo <= nv; ini += largo) {
      final sr = Float64List(tam), si = Float64List(tam);
      for (var b = 0; b < bandas; b++) {
        final re = Float64List(tam)..setRange(0, largo, v[b], ini);
        final im = Float64List(tam);
        fft.directa(re, im);
        final xr = ar[b], xi = ai[b];
        for (var k = 0; k < tam; k++) {
          // A · conj(T); se guarda conjugado para invertir con la transformada directa
          sr[k] += xr[k] * re[k] + xi[k] * im[k];
          si[k] -= xi[k] * re[k] - xr[k] * im[k];
        }
      }
      fft.directa(sr, si);
      var mejor = 0, p = 0;
      var tope = double.negativeInfinity;
      for (var k = 0; k < largo + na; k++) {
        final pos = k - largo; // de -largo a na
        final x = sr[pos < 0 ? tam + pos : pos];
        if (x > tope) {
          tope = x;
          mejor = pos;
        }
      }
      p = mejor;
      hallados.add((ini: ini, suma: ini - p, parecido: _parecido(v, ini, largo, a, p)));
    }
    final buenos = [for (final h in hallados) if (h.parecido >= parecidoMin) h];
    if (buenos.isEmpty) return null;
    // el corrimiento en el que más trozos se ponen de acuerdo (±0,1 s); una música que se repite puede
    // encajar igual de bien en otro compás: si en el común casi se parece lo mismo, vale el común
    var comun = 0;
    var apoyo = -1.0;
    for (final h in buenos) {
      final s = buenos.where((o) => (o.suma - h.suma).abs() <= 5).fold<double>(0, (t, o) => t + o.parecido);
      if (s > apoyo) {
        apoyo = s;
        comun = h.suma;
      }
    }
    final iguales = [for (final h in buenos) if ((h.suma - comun).abs() <= 5) h.suma]..sort();
    final m = iguales.length ~/ 2;
    comun = iguales.length.isOdd ? iguales[m] : ((iguales[m - 1] + iguales[m]) / 2).round();
    if (iguales.length < 2 && hallados.length > 2) return null; // un solo trozo de acuerdo: no basta
    final tramos = <(int, int)>[];
    for (final h in hallados) {
      var aqui = 0.0;
      for (var d = -2; d <= 2; d++) {
        aqui = max(aqui, _parecido(v, h.ini, largo, a, h.ini - comun - d));
      }
      if (h.parecido < parecidoMin && aqui < parecidoMin) continue; // silencio, escena hablada: no dice nada
      tramos.add((h.ini, aqui >= h.parecido * 0.85 || h.parecido < parecidoMin ? comun : h.suma));
    }
    double seg(int cuadros) => cuadros * _salto / hz;
    if (tramos.where((t) => t.$2 == comun).length >= 0.7 * tramos.length) return [(0, seg(comun))];
    // varios corrimientos: la grabación va cortada. Tienen que ir en orden o no se puede fiar
    final salida = <TramoCotejo>[];
    for (final (ini, c) in tramos) {
      if (salida.isEmpty || (salida.last.$2 - seg(c)).abs() > 0.1) salida.add((seg(ini), seg(c)));
    }
    if (salida.length > 4) return null;
    for (var i = 1; i < salida.length; i++) {
      if (salida[i].$1 - salida[i].$2 < salida[i - 1].$1 - salida[i - 1].$2) return null;
    }
    salida[0] = (0, salida[0].$2);
    return salida;
  }

  // ------------------------------------------------------------ con audio de verdad

  static int _turno = 0;

  static Future<Float64List?> _muestras(String origen) async {
    File? salida;
    try {
      final tmp = await getTemporaryDirectory();
      salida = File('${tmp.path}/cotejo_${_turno++}.raw');
      final s = await FFmpegKit.executeWithArguments([
        '-y', '-v', 'error', '-t', '$escucha', '-i', origen,
        '-vn', '-ac', '1', '-ar', '$hz', '-f', 's16le', salida.path,
      ]).timeout(const Duration(seconds: 90));
      if (!ReturnCode.isSuccess(await s.getReturnCode()) || !await salida.exists()) return null;
      final bytes = await salida.readAsBytes();
      final n = bytes.length ~/ 2;
      if (n < hz * 20) return null;
      final d = ByteData.sublistView(bytes);
      final m = Float64List(n);
      for (var i = 0; i < n; i++) {
        m[i] = d.getInt16(i * 2, Endian.little) / 32768.0;
      }
      return m;
    } catch (_) {
      return null;
    } finally {
      try {
        await salida?.delete();
      } catch (_) {}
    }
  }

  /// Compara lo que suena con la otra grabación (archivos o enlaces que ffmpeg pueda leer).
  static Future<List<TramoCotejo>?> cotejar(String suena, String otra) async {
    if (kIsWeb) return null;
    final x = await _muestras(suena);
    if (x == null) return null;
    final y = await _muestras(otra);
    if (y == null) return null;
    return compute(_enAparte, (x, y), debugLabel: 'cotejo de la letra');
  }

  static List<TramoCotejo>? _enAparte((Float64List, Float64List) d) => desfases(d.$1, d.$2);
}

/// Transformada rápida de Fourier (tamaño potencia de dos), en el sitio.
class _Fft {
  _Fft(this.n)
      : _cos = Float64List(n ~/ 2),
        _sen = Float64List(n ~/ 2) {
    for (var i = 0; i < n ~/ 2; i++) {
      _cos[i] = cos(2 * pi * i / n);
      _sen[i] = -sin(2 * pi * i / n);
    }
  }

  final int n;
  final Float64List _cos, _sen;

  void directa(Float64List re, Float64List im) {
    for (var i = 1, j = 0; i < n; i++) {
      var bit = n >> 1;
      for (; j & bit != 0; bit >>= 1) {
        j ^= bit;
      }
      j ^= bit;
      if (i < j) {
        final tr = re[i], ti = im[i];
        re[i] = re[j];
        im[i] = im[j];
        re[j] = tr;
        im[j] = ti;
      }
    }
    for (var largo = 2; largo <= n; largo <<= 1) {
      final mitad = largo >> 1, paso = n ~/ largo;
      for (var i = 0; i < n; i += largo) {
        for (var k = 0, t = 0; k < mitad; k++, t += paso) {
          final a = i + k, b = a + mitad;
          final xr = re[b] * _cos[t] - im[b] * _sen[t], xi = re[b] * _sen[t] + im[b] * _cos[t];
          re[b] = re[a] - xr;
          im[b] = im[a] - xi;
          re[a] += xr;
          im[a] += xi;
        }
      }
    }
  }
}
