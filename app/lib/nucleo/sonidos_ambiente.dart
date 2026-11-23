import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

import '../reproduccion/jugador.dart';
import 'archivos_web.dart';
import 'streams.dart' show Fuente;

/// Los sonidos ambientales del Modo estudio. Se fabrican en el propio
/// dispositivo (nada se descarga ni pesa en la app): cada capa es una pista
/// corta en bucle, sin clic al volver a empezar.
enum CapaAmbiente { lluvia, cafeteria, bosque, chimenea, blanco, rosa, marron }

extension DatosCapa on CapaAmbiente {
  String get nombre => switch (this) {
        CapaAmbiente.lluvia => 'Lluvia',
        CapaAmbiente.cafeteria => 'Cafetería',
        CapaAmbiente.bosque => 'Bosque',
        CapaAmbiente.chimenea => 'Chimenea',
        CapaAmbiente.blanco => 'Ruido blanco',
        CapaAmbiente.rosa => 'Ruido rosa',
        CapaAmbiente.marron => 'Ruido marrón',
      };

  String get descripcion => switch (this) {
        CapaAmbiente.lluvia => 'Gotas suaves sobre una ventana',
        CapaAmbiente.cafeteria => 'Murmullo lejano y tazas',
        CapaAmbiente.bosque => 'Viento entre árboles y pájaros',
        CapaAmbiente.chimenea => 'Brasas y leña que cruje',
        CapaAmbiente.blanco => 'Parejo, como una radio sin sintonizar',
        CapaAmbiente.rosa => 'Más suave, como una cascada lejana',
        CapaAmbiente.marron => 'Grave y profundo, como un trueno lento',
      };
}

/// Fabrica pistas de sonido ambiental como muestras de 16 bits (mono).
class SintesisAmbiente {
  SintesisAmbiente._();

  static const int frecuencia = 22050;
  static const double segundosPorDefecto = 24;

  /// Cuánto se funden los extremos para que el bucle no haga clic.
  static const double segundosDeFundido = 2;

  /// La pista en bucle de [capa]: [segundos] de duración, mono, 16 bits.
  /// Con la misma [semilla] sale siempre igual.
  static Int16List bucle(CapaAmbiente capa,
      {int? semilla, double segundos = segundosPorDefecto, int hz = frecuencia}) {
    final n = (segundos * hz).round();
    final f = min((segundosDeFundido * hz).round(), n ~/ 3);
    final raw = _crudo(capa, n + f, hz, n / hz, Random(semilla ?? (11 + capa.index * 7)));
    final salida = unirSinClic(raw, n);
    _nivelar(salida, _objetivoRms[capa]!);
    final r = Int16List(n);
    for (var i = 0; i < n; i++) {
      r[i] = (salida[i] * 32767).round().clamp(-32767, 32767);
    }
    return r;
  }

  /// Recorta [raw] a [n] muestras mezclando su cola (lo que sigue al final)
  /// con su principio: el último valor enlaza con el primero sin salto.
  /// Mezcla de potencia constante (seno/coseno).
  @visibleForTesting
  static Float64List unirSinClic(Float64List raw, int n) {
    final f = raw.length - n;
    final out = Float64List(n);
    for (var i = 0; i < n; i++) {
      out[i] = raw[i];
    }
    for (var i = 0; i < f; i++) {
      final a = (i + 0.5) / f * pi / 2;
      // al principio manda la cola (que continúa lo último); al final, el principio
      out[i] = raw[n + i] * cos(a) + raw[i] * sin(a);
    }
    return out;
  }

  static const Map<CapaAmbiente, double> _objetivoRms = {
    CapaAmbiente.blanco: 0.11,
    CapaAmbiente.rosa: 0.14,
    CapaAmbiente.marron: 0.16,
    CapaAmbiente.lluvia: 0.13,
    CapaAmbiente.chimenea: 0.11,
    CapaAmbiente.cafeteria: 0.11,
    CapaAmbiente.bosque: 0.11,
  };

  /// Ajusta el nivel medio y recorta los picos con una curva suave, para que
  /// nunca llegue a saturar.
  static void _nivelar(Float64List x, double objetivo) {
    var s = 0.0;
    for (final v in x) {
      s += v * v;
    }
    final rms = sqrt(s / x.length);
    final g = rms > 1e-9 ? objetivo / rms : 1.0;
    for (var i = 0; i < x.length; i++) {
      var v = x[i] * g;
      const t = 0.7;
      final a = v.abs();
      if (a > t) {
        final c = t + (1 - t) * _tanh((a - t) / (1 - t));
        v = v < 0 ? -c : c;
      }
      x[i] = v * 0.97;
    }
  }

  static double _tanh(double x) {
    final e = exp(2 * x);
    return (e - 1) / (e + 1);
  }

  // ------------------------------------------------------------ recetas

  static Float64List _crudo(CapaAmbiente c, int total, int hz, double periodo, Random r) {
    switch (c) {
      case CapaAmbiente.blanco:
        return Float64List.fromList([for (var i = 0; i < total; i++) r.nextDouble() * 2 - 1]);
      case CapaAmbiente.rosa:
        return _rosa(total, r);
      case CapaAmbiente.marron:
        return _marron(total, r);
      case CapaAmbiente.lluvia:
        return _lluvia(total, hz, r);
      case CapaAmbiente.chimenea:
        return _chimenea(total, hz, r);
      case CapaAmbiente.cafeteria:
        return _cafeteria(total, hz, periodo, r);
      case CapaAmbiente.bosque:
        return _bosque(total, hz, periodo, r);
    }
  }

  static double _a(double fc, int hz) => 1 - exp(-2 * pi * fc / hz);

  /// Ruido rosa por Voss-McCartney: 16 generadores que se renuevan a ritmos
  /// de potencias de dos, más uno que cambia en cada muestra.
  static Float64List _rosa(int total, Random r) {
    const filas = 16;
    final v = List<double>.generate(filas, (_) => r.nextDouble() * 2 - 1);
    var suma = v.fold<double>(0, (a, b) => a + b);
    final out = Float64List(total);
    for (var i = 0; i < total; i++) {
      final k = i + 1;
      final idx = (k & -k).bitLength - 1; // ceros finales del contador
      if (idx < filas) {
        suma -= v[idx];
        v[idx] = r.nextDouble() * 2 - 1;
        suma += v[idx];
      }
      out[i] = (suma + (r.nextDouble() * 2 - 1)) / (filas + 1) * 3;
    }
    return out;
  }

  /// Ruido marrón: el blanco integrado, con una pequeña fuga para que no se
  /// vaya de un lado.
  static Float64List _marron(int total, Random r) {
    final out = Float64List(total);
    var y = 0.0;
    for (var i = 0; i < total; i++) {
      y = y * 0.997 + (r.nextDouble() * 2 - 1) * 0.1;
      out[i] = y;
    }
    return out;
  }

  /// Lluvia: siseo agudo de fondo, un colchón grave suave y gotas sueltas.
  static Float64List _lluvia(int total, int hz, Random r) {
    final rosa = _rosa(total, r);
    final out = Float64List(total);
    final a1 = _a(1400, hz), a2 = _a(350, hz);
    var l1 = 0.0, l2 = 0.0;
    final gotas = <_Gota>[];
    const tasa = 70.0; // gotas por segundo
    for (var i = 0; i < total; i++) {
      final x = rosa[i];
      l1 += a1 * (x - l1);
      l2 += a2 * (x - l2);
      var v = (x - l1) * 0.55 + l2 * 0.35;
      if (r.nextDouble() < tasa / hz) {
        gotas.add(_Gota(
          amp: 0.05 + 0.35 * pow(r.nextDouble(), 3),
          w: 2 * pi * (1800 + r.nextDouble() * 4200) / hz,
          k: exp(-1 / (hz * (0.002 + r.nextDouble() * 0.006))),
        ));
      }
      for (var j = gotas.length - 1; j >= 0; j--) {
        final g = gotas[j];
        v += g.amp * g.env * sin(g.fase);
        g.fase += g.w;
        g.env *= g.k;
        if (g.env < 0.002) gotas.removeAt(j);
      }
      out[i] = v;
    }
    return out;
  }

  /// Chimenea: un fondo grave y suave y chasquidos de fuerza y separación
  /// al azar, a veces en racimo.
  static Float64List _chimenea(int total, int hz, Random r) {
    final marron = _marron(total, r);
    final out = Float64List(total);
    final aLp = _a(900, hz);
    var lp = 0.0, previo = 0.0;
    final chasquidos = <_Gota>[];
    var proximo = 0.1 * hz;
    for (var i = 0; i < total; i++) {
      lp += aLp * (marron[i] - lp);
      var v = lp * 0.8;
      if (i >= proximo) {
        _nuevoChasquido(chasquidos, hz, r);
        // a veces siguen varios casi pegados
        if (r.nextDouble() < 0.18) {
          for (var k = 0; k < 2 + r.nextInt(3); k++) {
            _nuevoChasquido(chasquidos, hz, r);
          }
        }
        proximo = i + hz * (0.04 + r.nextDouble() * r.nextDouble() * 0.5);
      }
      for (var j = chasquidos.length - 1; j >= 0; j--) {
        final g = chasquidos[j];
        double s;
        if (g.w > 0) {
          s = sin(g.fase); // un golpe grave
          g.fase += g.w;
        } else {
          final b = r.nextDouble() * 2 - 1;
          s = b - previo * 0.6; // ruido con los graves recortados
          previo = b;
        }
        v += g.amp * g.env * s;
        g.env *= g.k;
        if (g.env < 0.003) chasquidos.removeAt(j);
      }
      out[i] = v;
    }
    return out;
  }

  static void _nuevoChasquido(List<_Gota> lista, int hz, Random r) {
    final fuerte = r.nextDouble() < 0.06;
    lista.add(_Gota(
      amp: fuerte ? 0.9 : 0.04 + 0.5 * pow(r.nextDouble(), 4),
      w: fuerte ? 2 * pi * (110 + r.nextDouble() * 120) / hz : 0,
      k: exp(-1 / (hz * (fuerte ? 0.018 : 0.0006 + r.nextDouble() * 0.0025))),
    ));
  }

  /// Cafetería: dos corrientes de murmullo (rosa pasa-banda) que suben y bajan
  /// despacio, y tintineos de tazas de vez en cuando.
  static Float64List _cafeteria(int total, int hz, double periodo, Random r) {
    final p1 = _rosa(total, r), p2 = _rosa(total, r);
    final out = Float64List(total);
    // filtros pasa-banda de dos polos por cada corriente
    final b1 = _Banda(300, 1300, hz), b2 = _Banda(900, 2500, hz);
    final fase = [for (var i = 0; i < 4; i++) r.nextDouble() * 2 * pi];
    // ciclos enteros por bucle: la modulación también cierra sin salto
    final k = [3 + r.nextInt(2), 5 + r.nextInt(3), 4 + r.nextInt(2), 7 + r.nextInt(3)];
    final tintineos = <_Gota>[];
    var proximo = hz * (2 + r.nextDouble() * 3);
    for (var i = 0; i < total; i++) {
      final t = i / hz;
      final m1 = 0.65 + 0.35 * sin(2 * pi * k[0] * t / periodo + fase[0]) * (0.6 + 0.4 * sin(2 * pi * k[1] * t / periodo + fase[1]));
      final m2 = 0.65 + 0.35 * sin(2 * pi * k[2] * t / periodo + fase[2]) * (0.6 + 0.4 * sin(2 * pi * k[3] * t / periodo + fase[3]));
      var v = b1.paso(p1[i]) * m1 * 1.0 + b2.paso(p2[i]) * m2 * 0.7;
      if (i >= proximo) {
        final doble = r.nextDouble() < 0.3;
        for (var q = 0; q < (doble ? 2 : 1); q++) {
          final f = 2000 + r.nextDouble() * 3000;
          tintineos.add(_Gota(
            amp: 0.05 + 0.1 * r.nextDouble(),
            w: 2 * pi * f / hz,
            w2: 2 * pi * f * 2.76 / hz,
            k: exp(-1 / (hz * (0.07 + r.nextDouble() * 0.12))),
            retardo: q * (0.12 + r.nextDouble() * 0.1) * hz,
          ));
        }
        proximo = i + hz * (3.5 + r.nextDouble() * 5.5);
      }
      for (var j = tintineos.length - 1; j >= 0; j--) {
        final g = tintineos[j];
        if (g.retardo > 0) {
          g.retardo -= 1;
          continue;
        }
        v += g.amp * g.env * (sin(g.fase) + 0.45 * sin(g.fase2));
        g.fase += g.w;
        g.fase2 += g.w2;
        g.env *= g.k;
        if (g.env < 0.003) tintineos.removeAt(j);
      }
      out[i] = v;
    }
    return out;
  }

  /// Bosque: viento (rosa pasa-bajos que sube y baja despacio) y trinos de
  /// pájaros, sueltos y de vez en cuando.
  static Float64List _bosque(int total, int hz, double periodo, Random r) {
    final p = _rosa(total, r), p2 = _rosa(total, r);
    final out = Float64List(total);
    final a1 = _a(520, hz), a1b = _a(700, hz), a2 = _a(2200, hz);
    var l1 = 0.0, l1b = 0.0, l2 = 0.0;
    final fase = [for (var i = 0; i < 3; i++) r.nextDouble() * 2 * pi];
    final k = [1 + r.nextInt(2), 3 + r.nextInt(2), 2 + r.nextInt(3)];
    // los trinos: lista de notas ya programadas (inicio, duración, f0, f1, amp)
    final notas = <_Nota>[];
    var t = 1.0 + r.nextDouble() * 2;
    final fin = total / hz;
    while (t < fin) {
      final n = 2 + r.nextInt(4);
      var tt = t;
      final f0 = 2800 + r.nextDouble() * 2200;
      final dir = r.nextDouble() < 0.5 ? 1 : -1;
      for (var q = 0; q < n; q++) {
        final d = 0.07 + r.nextDouble() * 0.11;
        final f1 = f0 * (1 + dir * (0.15 + r.nextDouble() * 0.35));
        notas.add(_Nota(tt, d, f0 * (1 + 0.04 * q * dir), f1, 0.1 + 0.12 * r.nextDouble()));
        tt += d + 0.04 + r.nextDouble() * 0.09;
      }
      t = tt + 1.5 + r.nextDouble() * 4.5;
    }
    var idxNota = 0;
    final activas = <_Nota>[];
    for (var i = 0; i < total; i++) {
      final s = i / hz;
      l1 += a1 * (p[i] - l1);
      l1b += a1b * (l1 - l1b); // dos polos: viento suave, sin siseo
      l2 += a2 * (p2[i] - l2);
      final rafaga = 0.3 + 0.7 * (0.5 + 0.5 * sin(2 * pi * k[0] * s / periodo + fase[0]));
      final rafaga2 = 0.75 + 0.25 * sin(2 * pi * k[1] * s / periodo + fase[1]);
      final hojas = 0.04 * (0.5 + 0.5 * sin(2 * pi * k[2] * s / periodo + fase[2]));
      var v = l1b * 1.6 * rafaga * rafaga2 + (p2[i] - l2) * hojas;
      while (idxNota < notas.length && notas[idxNota].inicio <= s) {
        activas.add(notas[idxNota++]);
      }
      for (var j = activas.length - 1; j >= 0; j--) {
        final nota = activas[j];
        final u = (s - nota.inicio) / nota.dur;
        if (u >= 1) {
          activas.removeAt(j);
          continue;
        }
        final f = nota.f0 + (nota.f1 - nota.f0) * u;
        nota.fase += 2 * pi * f / hz;
        final env = sin(pi * u);
        v += nota.amp * env * env * sin(nota.fase);
      }
      out[i] = v;
    }
    return out;
  }

  // ------------------------------------------------------------ WAV y campanas

  /// Empaqueta muestras de 16 bits (mono) como un archivo WAV.
  static Uint8List wav(Int16List muestras, {int hz = frecuencia}) {
    final datos = muestras.length * 2;
    final b = ByteData(44 + datos);
    void txt(int o, String s) {
      for (var i = 0; i < s.length; i++) {
        b.setUint8(o + i, s.codeUnitAt(i));
      }
    }

    txt(0, 'RIFF');
    b.setUint32(4, 36 + datos, Endian.little);
    txt(8, 'WAVE');
    txt(12, 'fmt ');
    b.setUint32(16, 16, Endian.little);
    b.setUint16(20, 1, Endian.little); // PCM
    b.setUint16(22, 1, Endian.little); // mono
    b.setUint32(24, hz, Endian.little);
    b.setUint32(28, hz * 2, Endian.little);
    b.setUint16(32, 2, Endian.little);
    b.setUint16(34, 16, Endian.little);
    txt(36, 'data');
    b.setUint32(40, datos, Endian.little);
    for (var i = 0; i < muestras.length; i++) {
      b.setInt16(44 + i * 2, muestras[i], Endian.little);
    }
    return b.buffer.asUint8List();
  }

  /// Una campana suave. [alTerminarBloque]: dos notas que bajan (el descanso
  /// llega); si no, una sola nota y más alta (vuelve el enfoque).
  static Int16List campana({required bool alTerminarBloque, int hz = frecuencia}) {
    final notas = alTerminarBloque ? [(659.25, 0.0), (523.25, 0.34)] : [(783.99, 0.0)];
    final total = (hz * (alTerminarBloque ? 3.6 : 3.0)).round();
    final x = Float64List(total);
    for (final (f, inicio) in notas) {
      final desde = (inicio * hz).round();
      for (var i = desde; i < total; i++) {
        final t = (i - desde) / hz;
        final ataque = min(1.0, t / 0.012);
        // parciales de campana: cada uno se apaga a su ritmo
        final v = sin(2 * pi * f * t) * exp(-t / 1.1) +
            0.32 * sin(2 * pi * f * 2.0 * t) * exp(-t / 0.7) +
            0.12 * sin(2 * pi * f * 3.01 * t) * exp(-t / 0.4) +
            0.06 * sin(2 * pi * f * 4.17 * t) * exp(-t / 0.25);
        x[i] += v * ataque * 0.3;
      }
    }
    final r = Int16List(total);
    for (var i = 0; i < total; i++) {
      // se cierra con un fundido corto para no cortar en seco
      final cola = min(1.0, (total - i) / (hz * 0.25));
      r[i] = (x[i] * cola * 32767).round().clamp(-32767, 32767);
    }
    return r;
  }
}

class _Gota {
  _Gota({required this.amp, required this.w, required this.k, this.w2 = 0, this.retardo = 0});
  final double amp;
  final double w;
  final double w2;
  final double k;
  double retardo;
  double env = 1;
  double fase = 0;
  double fase2 = 0;
}

class _Nota {
  _Nota(this.inicio, this.dur, this.f0, this.f1, this.amp);
  final double inicio, dur, f0, f1, amp;
  double fase = 0;
}

/// Pasa-banda de dos polos por lado (pasa-altos y pasa-bajos en cascada).
class _Banda {
  _Banda(double bajo, double alto, int hz)
      : _ah = SintesisAmbiente._a(bajo, hz),
        _al = SintesisAmbiente._a(alto, hz);
  final double _ah, _al;
  double _h1 = 0, _h2 = 0, _l1 = 0, _l2 = 0;

  double paso(double x) {
    _h1 += _ah * (x - _h1);
    var y = x - _h1;
    _h2 += _ah * (y - _h2);
    y -= _h2;
    _l1 += _al * (y - _l1);
    _l2 += _al * (_l1 - _l2);
    return _l2;
  }
}

/// Lo que se manda a otro hilo para fabricar un WAV: (capa, semilla, segundos).
typedef _Pedido = (int, int, double);

Uint8List _wavDeCapa(_Pedido p) => SintesisAmbiente.wav(
    SintesisAmbiente.bucle(CapaAmbiente.values[p.$1], semilla: p.$2, segundos: p.$3));

Uint8List _wavDeCampana(bool fin) =>
    SintesisAmbiente.wav(SintesisAmbiente.campana(alTerminarBloque: fin));

typedef FabricaJugador = Jugador Function();

/// Reproduce las capas: un motor propio por capa, en bucle, aparte del de la
/// música. Los WAV se fabrican una vez (en otro hilo) y quedan en la carpeta
/// temporal.
class SonidosAmbiente extends ChangeNotifier {
  SonidosAmbiente({FabricaJugador? fabrica, Future<Directory> Function()? carpeta, bool? disponible})
      : _fabrica = fabrica ?? Jugador.crearAparte,
        _carpeta = carpeta ?? getTemporaryDirectory,
        // ignore: prefer_initializing_formals
        _disponible = disponible;

  final FabricaJugador _fabrica;
  final Future<Directory> Function() _carpeta;
  final bool? _disponible;

  static const _version = 1;

  /// ¿Hay un reproductor para las capas? (en la web, el audio del navegador)
  bool get disponible => _disponible ?? true;

  final Map<CapaAmbiente, Jugador> _motores = {};
  final Map<CapaAmbiente, double> _volumenes = {};
  final Set<CapaAmbiente> _preparando = {};
  final Map<CapaAmbiente, Future<File>> _archivos = {};

  /// En la web no hay carpeta temporal: cada WAV vive en la memoria del navegador.
  final Map<CapaAmbiente, Future<String>> _enMemoria = {};

  Future<String> _rutaDe(CapaAmbiente c) async {
    if (!kIsWeb) return (await archivoDe(c)).path;
    return _enMemoria[c] ??= compute(_wavDeCapa, (c.index, 11 + c.index * 7, SintesisAmbiente.segundosPorDefecto))
        .then((b) => ArchivosWeb.urlTemporal(b, 'audio/wav'));
  }

  /// Capas que suenan (o se están preparando para sonar).
  Set<CapaAmbiente> get sonando => {..._motores.keys, ..._preparando};
  bool preparando(CapaAmbiente c) => _preparando.contains(c);

  Future<File> archivoDe(CapaAmbiente c) => _archivos[c] ??= _asegurar(c);

  Future<File> _asegurar(CapaAmbiente c) async {
    final dir = Directory('${(await _carpeta()).path}${Platform.pathSeparator}caudal_ambiente');
    if (!await dir.exists()) await dir.create(recursive: true);
    final f = File('${dir.path}${Platform.pathSeparator}${c.name}_v$_version.wav');
    if (await f.exists() && await f.length() > 44) return f;
    final bytes = await compute(_wavDeCapa, (c.index, 11 + c.index * 7, SintesisAmbiente.segundosPorDefecto));
    final tmp = File('${f.path}.tmp');
    await tmp.writeAsBytes(bytes, flush: true);
    return tmp.rename(f.path);
  }

  Future<void> encender(CapaAmbiente c, double volumen) async {
    _volumenes[c] = volumen.clamp(0.0, 1.0);
    if (!disponible || _motores.containsKey(c) || !_preparando.add(c)) return;
    notifyListeners();
    try {
      final ruta = await _rutaDe(c);
      // si mientras se fabricaba la apagaron, no se arranca
      if (!_preparando.contains(c)) return;
      final j = _fabrica();
      _motores[c] = j;
      await j.setProperty('loop-file', 'inf');
      await j.setVolume((_volumenes[c] ?? 0) * 100);
      await j.open(Fuente.archivo(ruta));
    } catch (e) {
      debugPrint('ambiente ${c.name}: $e');
      final j = _motores.remove(c);
      if (j != null) unawaited(j.dispose().catchError((_) {}));
    } finally {
      _preparando.remove(c);
      notifyListeners();
    }
  }

  Future<void> apagar(CapaAmbiente c) async {
    _preparando.remove(c);
    final j = _motores.remove(c);
    notifyListeners();
    if (j == null) return;
    try {
      await j.stop();
    } catch (_) {}
    try {
      await j.dispose();
    } catch (_) {}
  }

  Future<void> fijarVolumen(CapaAmbiente c, double v) async {
    _volumenes[c] = v.clamp(0.0, 1.0);
    final j = _motores[c];
    if (j != null) {
      try {
        await j.setVolume(_volumenes[c]! * 100);
      } catch (_) {}
    }
  }

  Future<void> detenerTodo() async {
    for (final c in sonando.toList()) {
      await apagar(c);
    }
  }

  /// Un tono suave: al terminar un bloque (dos notas) o al volver al enfoque.
  Future<void> campana({required bool alTerminarBloque, double volumen = 0.7}) async {
    if (!disponible) return;
    if (kIsWeb) return _campanaWeb(alTerminarBloque, volumen);
    try {
      final dir = Directory('${(await _carpeta()).path}${Platform.pathSeparator}caudal_ambiente');
      if (!await dir.exists()) await dir.create(recursive: true);
      final f = File('${dir.path}${Platform.pathSeparator}campana_${alTerminarBloque ? 'fin' : 'inicio'}_v$_version.wav');
      if (!await f.exists() || await f.length() <= 44) {
        await f.writeAsBytes(await compute(_wavDeCampana, alTerminarBloque), flush: true);
      }
      final j = _fabrica();
      await j.setVolume(volumen * 100);
      await j.open(Fuente.archivo(f.path));
      Timer(const Duration(seconds: 6), () => j.dispose().catchError((_) {}));
    } catch (e) {
      debugPrint('campana: $e');
    }
  }

  Future<void> _campanaWeb(bool fin, double volumen) async {
    try {
      final url = ArchivosWeb.urlTemporal(await compute(_wavDeCampana, fin), 'audio/wav');
      final j = _fabrica();
      await j.setVolume(volumen * 100);
      await j.open(Fuente.archivo(url));
      Timer(const Duration(seconds: 6), () {
        j.dispose().catchError((_) {});
        ArchivosWeb.soltarTemporal(url);
      });
    } catch (e) {
      debugPrint('campana: $e');
    }
  }

  @override
  void dispose() {
    for (final j in _motores.values) {
      j.dispose().catchError((_) {});
    }
    _motores.clear();
    super.dispose();
  }
}
