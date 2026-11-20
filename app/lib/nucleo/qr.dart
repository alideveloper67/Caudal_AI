import 'dart:convert';

/// Generador de códigos QR propio (sin paquetes): modo byte en UTF-8, corrección de errores
/// nivel M, versiones 1 a 10 (hasta 213 bytes: de sobra para el enlace de una fiesta).
///
/// Sigue el algoritmo de referencia de la norma ISO/IEC 18004 tal como lo implementa
/// «QR Code generator» de Nayuki: la versión más pequeña en la que cabe, las 8 máscaras
/// puntuadas con las 4 penalizaciones de la norma y, a igualdad, la de número menor.
/// El de Windows (`escritorio/descargador/qr.py`) hace lo mismo.
class CodigoQr {
  CodigoQr._(this.version, this.lado, this._m, this.mascara);

  final int version;
  final int lado;
  final int mascara;
  final List<List<bool>> _m;

  /// true = módulo oscuro. Sin el margen blanco (hay que dejar 4 módulos alrededor).
  bool oscuro(int x, int y) => _m[y][x];

  /// Las filas como '1'/'0' (para pruebas y para comparar con el de Windows).
  String comoTexto() => _m.map((f) => f.map((b) => b ? '1' : '0').join()).join('\n');

  static const _eccPorBloque = [10, 16, 26, 18, 24, 16, 18, 22, 22, 26];
  static const _bloques = [1, 1, 1, 2, 2, 4, 4, 4, 5, 5];
  static const maxVersion = 10;

  /// Crea el QR de [texto]. Lanza [ArgumentError] si no cabe en la versión 10.
  static CodigoQr de(String texto) {
    final datos = utf8.encode(texto);
    for (var v = 1; v <= maxVersion; v++) {
      final capacidad = _datosUtiles(v) * 8;
      final bitsCuenta = v <= 9 ? 8 : 16;
      final usados = 4 + bitsCuenta + datos.length * 8;
      if (usados <= capacidad && datos.length < (1 << bitsCuenta)) return _crear(v, datos, bitsCuenta, capacidad);
    }
    throw ArgumentError('El texto es demasiado largo para un QR.');
  }

  static int _modulosCrudos(int v) {
    var r = (16 * v + 128) * v + 64;
    if (v >= 2) {
      final n = v ~/ 7 + 2;
      r -= (25 * n - 10) * n - 55;
      if (v >= 7) r -= 36;
    }
    return r;
  }

  static int _datosUtiles(int v) => _modulosCrudos(v) ~/ 8 - _eccPorBloque[v - 1] * _bloques[v - 1];

  static CodigoQr _crear(int v, List<int> datos, int bitsCuenta, int capacidad) {
    // bits: modo byte (0100), cuenta, datos, terminador, relleno
    final bits = <int>[];
    void poner(int valor, int n) {
      for (var i = n - 1; i >= 0; i--) {
        bits.add((valor >> i) & 1);
      }
    }

    poner(4, 4);
    poner(datos.length, bitsCuenta);
    for (final b in datos) {
      poner(b, 8);
    }
    poner(0, (capacidad - bits.length).clamp(0, 4));
    poner(0, (8 - bits.length % 8) % 8);
    for (var relleno = 0xEC; bits.length < capacidad; relleno ^= 0xEC ^ 0x11) {
      poner(relleno, 8);
    }
    final palabras = List<int>.generate(bits.length ~/ 8, (i) {
      var b = 0;
      for (var j = 0; j < 8; j++) {
        b = (b << 1) | bits[i * 8 + j];
      }
      return b;
    });
    final todo = _eccEntrelazado(v, palabras);

    final lado = v * 4 + 17;
    final m = List.generate(lado, (_) => List.filled(lado, false));
    final fija = List.generate(lado, (_) => List.filled(lado, false));
    void fijar(int x, int y, bool o) {
      m[y][x] = o;
      fija[y][x] = true;
    }

    // patrones fijos
    for (var i = 0; i < lado; i++) {
      fijar(6, i, i % 2 == 0);
      fijar(i, 6, i % 2 == 0);
    }
    void buscador(int cx, int cy) {
      for (var dy = -4; dy <= 4; dy++) {
        for (var dx = -4; dx <= 4; dx++) {
          final d = dx.abs() > dy.abs() ? dx.abs() : dy.abs();
          final x = cx + dx, y = cy + dy;
          if (x >= 0 && x < lado && y >= 0 && y < lado) fijar(x, y, d != 2 && d != 4);
        }
      }
    }

    buscador(3, 3);
    buscador(lado - 4, 3);
    buscador(3, lado - 4);
    final pos = _alineacion(v, lado);
    for (var i = 0; i < pos.length; i++) {
      for (var j = 0; j < pos.length; j++) {
        if ((i == 0 && j == 0) || (i == 0 && j == pos.length - 1) || (i == pos.length - 1 && j == 0)) continue;
        for (var dy = -2; dy <= 2; dy++) {
          for (var dx = -2; dx <= 2; dx++) {
            final d = dx.abs() > dy.abs() ? dx.abs() : dy.abs();
            fijar(pos[i] + dx, pos[j] + dy, d != 1);
          }
        }
      }
    }
    void formato(int mascara) {
      final dato = (0 << 3) | mascara; // nivel M = 00
      var resto = dato;
      for (var i = 0; i < 10; i++) {
        resto = (resto << 1) ^ ((resto >> 9) * 0x537);
      }
      final b = ((dato << 10) | resto) ^ 0x5412;
      bool bit(int i) => ((b >> i) & 1) != 0;
      for (var i = 0; i <= 5; i++) {
        fijar(8, i, bit(i));
      }
      fijar(8, 7, bit(6));
      fijar(8, 8, bit(7));
      fijar(7, 8, bit(8));
      for (var i = 9; i < 15; i++) {
        fijar(14 - i, 8, bit(i));
      }
      for (var i = 0; i < 8; i++) {
        fijar(lado - 1 - i, 8, bit(i));
      }
      for (var i = 8; i < 15; i++) {
        fijar(8, lado - 15 + i, bit(i));
      }
      fijar(8, lado - 8, true);
    }

    formato(0);
    if (v >= 7) {
      var resto = v;
      for (var i = 0; i < 12; i++) {
        resto = (resto << 1) ^ ((resto >> 11) * 0x1F25);
      }
      final b = (v << 12) | resto;
      for (var i = 0; i < 18; i++) {
        final o = ((b >> i) & 1) != 0;
        final a = lado - 11 + i % 3, c = i ~/ 3;
        fijar(a, c, o);
        fijar(c, a, o);
      }
    }

    // datos en zigzag
    var i = 0;
    for (var der = lado - 1; der >= 1; der -= 2) {
      if (der == 6) der = 5;
      for (var vert = 0; vert < lado; vert++) {
        for (var j = 0; j < 2; j++) {
          final x = der - j;
          final sube = ((der + 1) & 2) == 0;
          final y = sube ? lado - 1 - vert : vert;
          if (!fija[y][x] && i < todo.length * 8) {
            m[y][x] = ((todo[i >> 3] >> (7 - (i & 7))) & 1) != 0;
            i++;
          }
        }
      }
    }

    // la mejor máscara
    var mejor = 0, menor = 1 << 30;
    for (var k = 0; k < 8; k++) {
      _mascarar(m, fija, k);
      formato(k);
      final p = _penalizacion(m);
      if (p < menor) {
        menor = p;
        mejor = k;
      }
      _mascarar(m, fija, k);
    }
    _mascarar(m, fija, mejor);
    formato(mejor);
    return CodigoQr._(v, lado, m, mejor);
  }

  static List<int> _alineacion(int v, int lado) {
    if (v == 1) return const [];
    final n = v ~/ 7 + 2;
    final paso = (v * 4 + n * 2 + 1) ~/ (n * 2 - 2) * 2;
    final r = <int>[];
    for (var i = 0, p = lado - 7; i < n - 1; i++, p -= paso) {
      r.insert(0, p);
    }
    r.insert(0, 6);
    return r;
  }

  static void _mascarar(List<List<bool>> m, List<List<bool>> fija, int k) {
    final lado = m.length;
    for (var y = 0; y < lado; y++) {
      for (var x = 0; x < lado; x++) {
        final bool inv;
        switch (k) {
          case 0:
            inv = (x + y) % 2 == 0;
          case 1:
            inv = y % 2 == 0;
          case 2:
            inv = x % 3 == 0;
          case 3:
            inv = (x + y) % 3 == 0;
          case 4:
            inv = (x ~/ 3 + y ~/ 2) % 2 == 0;
          case 5:
            inv = x * y % 2 + x * y % 3 == 0;
          case 6:
            inv = (x * y % 2 + x * y % 3) % 2 == 0;
          default:
            inv = ((x + y) % 2 + x * y % 3) % 2 == 0;
        }
        if (inv && !fija[y][x]) m[y][x] = !m[y][x];
      }
    }
  }

  // ------------------------------------------------------------ penalización (norma, como Nayuki)
  static int _penalizacion(List<List<bool>> m) {
    final lado = m.length;
    var r = 0;
    for (var eje = 0; eje < 2; eje++) {
      for (var a = 0; a < lado; a++) {
        var color = false;
        var largo = 0;
        final hist = List.filled(7, 0);
        for (var b = 0; b < lado; b++) {
          final c = eje == 0 ? m[a][b] : m[b][a];
          if (c == color) {
            largo++;
            if (largo == 5) {
              r += 3;
            } else if (largo > 5) {
              r++;
            }
          } else {
            _historia(largo, hist, lado);
            if (!color) r += _patrones(hist) * 40;
            color = c;
            largo = 1;
          }
        }
        if (color) {
          _historia(largo, hist, lado);
          largo = 0;
        }
        largo += lado;
        _historia(largo, hist, lado);
        r += _patrones(hist) * 40;
      }
    }
    for (var y = 0; y < lado - 1; y++) {
      for (var x = 0; x < lado - 1; x++) {
        final c = m[y][x];
        if (c == m[y][x + 1] && c == m[y + 1][x] && c == m[y + 1][x + 1]) r += 3;
      }
    }
    var oscuros = 0;
    for (final f in m) {
      for (final c in f) {
        if (c) oscuros++;
      }
    }
    final total = lado * lado;
    final k = (((oscuros * 20 - total * 10).abs() + total - 1) ~/ total) - 1;
    return r + k * 10;
  }

  static void _historia(int largo, List<int> h, int lado) {
    if (h[0] == 0) largo += lado;
    for (var i = h.length - 1; i > 0; i--) {
      h[i] = h[i - 1];
    }
    h[0] = largo;
  }

  static int _patrones(List<int> h) {
    final n = h[1];
    final nucleo = n > 0 && h[2] == n && h[3] == n * 3 && h[4] == n && h[5] == n;
    return (nucleo && h[0] >= n * 4 && h[6] >= n ? 1 : 0) + (nucleo && h[6] >= n * 4 && h[0] >= n ? 1 : 0);
  }

  // ------------------------------------------------------------ Reed-Solomon
  static List<int> _eccEntrelazado(int v, List<int> datos) {
    final nBloques = _bloques[v - 1];
    final nEcc = _eccPorBloque[v - 1];
    final crudas = _modulosCrudos(v) ~/ 8;
    final cortos = nBloques - crudas % nBloques;
    final largoCorto = crudas ~/ nBloques;
    final divisor = _divisor(nEcc);
    final bloques = <List<int>>[];
    var k = 0;
    for (var i = 0; i < nBloques; i++) {
      final n = largoCorto - nEcc + (i < cortos ? 0 : 1);
      final dat = datos.sublist(k, k + n);
      k += n;
      final ecc = _resto(dat, divisor);
      bloques.add([...dat, if (i < cortos) 0, ...ecc]);
    }
    final r = <int>[];
    for (var i = 0; i < bloques[0].length; i++) {
      for (var j = 0; j < bloques.length; j++) {
        if (i != largoCorto - nEcc || j >= cortos) r.add(bloques[j][i]);
      }
    }
    return r;
  }

  static int _mul(int x, int y) {
    var z = 0;
    for (var i = 7; i >= 0; i--) {
      z = ((z << 1) ^ ((z >> 7) * 0x11D)) & 0xFF;
      z ^= ((y >> i) & 1) * x;
    }
    return z;
  }

  static List<int> _divisor(int grado) {
    final r = List.filled(grado, 0);
    r[grado - 1] = 1;
    var raiz = 1;
    for (var i = 0; i < grado; i++) {
      for (var j = 0; j < r.length; j++) {
        r[j] = _mul(r[j], raiz);
        if (j + 1 < r.length) r[j] ^= r[j + 1];
      }
      raiz = _mul(raiz, 0x02);
    }
    return r;
  }

  static List<int> _resto(List<int> datos, List<int> divisor) {
    final r = List.filled(divisor.length, 0, growable: true);
    for (final b in datos) {
      final f = b ^ r[0];
      r.removeAt(0);
      r.add(0);
      for (var i = 0; i < r.length; i++) {
        r[i] ^= _mul(divisor[i], f);
      }
    }
    return r;
  }
}
