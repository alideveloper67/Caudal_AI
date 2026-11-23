// Lee título, artista, álbum y carátula de un audio sin ffmpeg: la versión web
// no lo tiene. MP3 (ID3v2.2 a 2.4), FLAC (Vorbis) y M4A/MP4 (átomos de iTunes).
// Nunca lanza: lo que no entiende sale vacío.
import 'dart:convert';
import 'dart:typed_data';

class EtiquetasAudio {
  String titulo = '', artista = '', album = '';
  Uint8List? portada;

  static EtiquetasAudio leer(Uint8List b) {
    final e = EtiquetasAudio();
    try {
      if (b.length < 16) return e;
      if (b[0] == 0x49 && b[1] == 0x44 && b[2] == 0x33) {
        e._id3(b);
      } else if (_texto(b, 0, 4) == 'fLaC') {
        e._flac(b);
      } else if (_texto(b, 4, 4) == 'ftyp') {
        e._mp4(b);
      }
    } catch (_) {}
    return e;
  }

  static String _texto(Uint8List b, int en, int n) => latin1.decode(Uint8List.sublistView(b, en, en + n));
  static int _u32(Uint8List b, int i) => b[i] * 0x1000000 + (b[i + 1] << 16) + (b[i + 2] << 8) + b[i + 3];
  static int _u32le(Uint8List b, int i) => b[i + 3] * 0x1000000 + (b[i + 2] << 16) + (b[i + 1] << 8) + b[i];
  static int _segura(Uint8List b, int i) => b[i] << 21 | b[i + 1] << 14 | b[i + 2] << 7 | b[i + 3];

  // ---------------------------------------------------------------- MP3

  void _id3(Uint8List b) {
    final version = b[3];
    final marcas = b[5];
    final fin = (10 + _segura(b, 6)).clamp(10, b.length);
    var datos = Uint8List.sublistView(b, 0, fin);
    // 2.3 y anteriores: la desincronización va en toda la etiqueta
    if (version < 4 && marcas & 0x80 != 0) {
      datos = Uint8List.fromList([...datos.sublist(0, 10), ..._resincronizar(datos.sublist(10))]);
    }
    var i = 10;
    if (version >= 3 && marcas & 0x40 != 0) {
      i += version == 4 ? _segura(datos, 10) : _u32(datos, 10) + 4;
    }
    final cabecera = version == 2 ? 6 : 10;
    final nombre = RegExp(r'^[A-Z0-9]+$');
    while (i + cabecera <= datos.length) {
      final id = _texto(datos, i, version == 2 ? 3 : 4);
      if (!nombre.hasMatch(id)) break;
      final n = version == 2
          ? datos[i + 3] << 16 | datos[i + 4] << 8 | datos[i + 5]
          : version == 4
              ? _segura(datos, i + 4)
              : _u32(datos, i + 4);
      final desde = i + cabecera;
      if (desde + n > datos.length) break;
      var c = datos.sublist(desde, desde + n);
      if (version == 4) {
        final f = datos[i + 9];
        if (f & 0x01 != 0 && c.length > 4) c = c.sublist(4); // lleva delante su tamaño real
        if (f & 0x02 != 0) c = _resincronizar(c);
        if (f & 0x0C != 0) c = Uint8List(0); // comprimida o cifrada
      }
      if (c.isNotEmpty) _marco(id, c);
      i = desde + n;
    }
  }

  static Uint8List _resincronizar(Uint8List b) {
    final s = BytesBuilder();
    for (var i = 0; i < b.length; i++) {
      s.addByte(b[i]);
      if (b[i] == 0xFF && i + 1 < b.length && b[i + 1] == 0) i++;
    }
    return s.toBytes();
  }

  void _marco(String id, Uint8List c) {
    switch (id) {
      case 'TIT2' || 'TT2':
        titulo = _cadena(c[0], c.sublist(1));
      case 'TPE1' || 'TP1':
        artista = _cadena(c[0], c.sublist(1));
      case 'TALB' || 'TAL':
        album = _cadena(c[0], c.sublist(1));
      case 'APIC' || 'PIC':
        _imagen(id, c);
    }
  }

  static String _cadena(int codigo, Uint8List b) {
    String s;
    if (codigo == 1 || codigo == 2) {
      var grande = codigo == 2;
      var i = 0;
      if (b.length >= 2 && ((b[0] == 0xFF && b[1] == 0xFE) || (b[0] == 0xFE && b[1] == 0xFF))) {
        grande = b[0] == 0xFE;
        i = 2;
      }
      final u = <int>[];
      for (; i + 1 < b.length; i += 2) {
        u.add(grande ? b[i] << 8 | b[i + 1] : b[i + 1] << 8 | b[i]);
      }
      s = String.fromCharCodes(u);
    } else if (codigo == 3) {
      s = utf8.decode(b, allowMalformed: true);
    } else {
      s = latin1.decode(b);
    }
    // varios valores van separados por un cero: cuenta el primero
    return s.split('\u0000').first.trim();
  }

  void _imagen(String id, Uint8List c) {
    final codigo = c[0];
    var i = 1;
    if (id == 'PIC') {
      i += 3;
    } else {
      while (i < c.length && c[i] != 0) {
        i++;
      }
      i++;
    }
    if (i >= c.length) return;
    final tipo = c[i++];
    if (codigo == 1 || codigo == 2) {
      while (i + 1 < c.length && (c[i] != 0 || c[i + 1] != 0)) {
        i += 2;
      }
      i += 2;
    } else {
      while (i < c.length && c[i] != 0) {
        i++;
      }
      i++;
    }
    if (i >= c.length) return;
    // la portada (tipo 3) manda sobre cualquier otra imagen
    if (portada == null || tipo == 3) portada = c.sublist(i);
  }

  // ---------------------------------------------------------------- FLAC

  void _flac(Uint8List b) {
    var i = 4;
    while (i + 4 <= b.length) {
      final ultimo = b[i] & 0x80 != 0;
      final tipo = b[i] & 0x7F;
      final n = b[i + 1] << 16 | b[i + 2] << 8 | b[i + 3];
      final d = i + 4;
      if (d + n > b.length) return;
      if (tipo == 4) _vorbis(Uint8List.sublistView(b, d, d + n));
      if (tipo == 6 && portada == null) {
        var j = d + 4;
        j += 4 + _u32(b, j); // tipo de imagen
        j += 4 + _u32(b, j); // descripción
        j += 16; // ancho, alto y colores
        final m = _u32(b, j);
        if (j + 4 + m <= d + n) portada = b.sublist(j + 4, j + 4 + m);
      }
      if (ultimo) return;
      i = d + n;
    }
  }

  void _vorbis(Uint8List b) {
    var i = 4 + _u32le(b, 0);
    final cuantos = _u32le(b, i);
    i += 4;
    for (var k = 0; k < cuantos && i + 4 <= b.length; k++) {
      final n = _u32le(b, i);
      i += 4;
      if (i + n > b.length) return;
      final s = utf8.decode(Uint8List.sublistView(b, i, i + n), allowMalformed: true);
      i += n;
      final p = s.indexOf('=');
      if (p < 0) continue;
      final v = s.substring(p + 1).trim();
      switch (s.substring(0, p).toUpperCase()) {
        case 'TITLE':
          titulo = v;
        case 'ARTIST':
          if (artista.isEmpty) artista = v;
        case 'ALBUM':
          album = v;
      }
    }
  }

  // ---------------------------------------------------------------- M4A

  void _mp4(Uint8List b) {
    (int, int)? buscar(int desde, int hasta, String nombre) {
      var i = desde;
      while (i + 8 <= hasta) {
        var n = _u32(b, i);
        var cabecera = 8;
        if (n == 1 && i + 16 <= hasta) {
          n = _u32(b, i + 8) * 0x100000000 + _u32(b, i + 12);
          cabecera = 16;
        }
        if (n == 0) n = hasta - i;
        if (n < cabecera || i + n > hasta) return null;
        if (_texto(b, i + 4, 4) == nombre) return (i + cabecera, i + n);
        i += n;
      }
      return null;
    }

    final moov = buscar(0, b.length, 'moov');
    if (moov == null) return;
    final udta = buscar(moov.$1, moov.$2, 'udta');
    if (udta == null) return;
    final meta = buscar(udta.$1, udta.$2, 'meta');
    if (meta == null) return;
    final ilst = buscar(meta.$1 + 4, meta.$2, 'ilst');
    if (ilst == null) return;
    Uint8List? dato(String nombre) {
      final a = buscar(ilst.$1, ilst.$2, nombre);
      if (a == null) return null;
      final d = buscar(a.$1, a.$2, 'data');
      return d == null || d.$1 + 8 > d.$2 ? null : b.sublist(d.$1 + 8, d.$2);
    }

    String texto(String n) => utf8.decode(dato(n) ?? const <int>[], allowMalformed: true).trim();
    titulo = texto('©nam');
    artista = texto('©ART');
    album = texto('©alb');
    portada = dato('covr');
  }
}
