import 'dart:convert';
import 'dart:typed_data';

import 'package:archive/archive.dart';

import 'importar.dart';

/// Tus canciones desde el archivo que te da cada servicio, sin conectar ninguna cuenta (lo
/// mismo que hace archivo_me_gusta.py en el escritorio):
///
///  * Spotify («Descarga tus datos»): el .zip entero o su `YourLibrary.json`.
///  * Google Takeout (YouTube y YouTube Music): el .zip entero o uno de sus .csv. Cuando el
///    .csv solo trae el id del video, la canción se busca por ese id.
///  * Cualquier .csv con título y artista (Exportify, TuneMyMusic, Soundiiz…).
///  * .txt: una canción por línea, «Artista - Título».
class ArchivoMeGusta {
  ArchivoMeGusta._();

  static const extensiones = ['zip', 'json', 'csv', 'tsv', 'txt'];

  /// Un archivo enorme no cabe en la memoria del teléfono.
  static const maxArchivo = 150 * 1024 * 1024;

  /// Lo que puede ocupar, ya descomprimido, cada archivo del .zip y todos juntos.
  static const maxDentro = 40 * 1024 * 1024;
  static const maxTotal = 120 * 1024 * 1024;

  static const errorVacio = ErrorImportar('En ese archivo no hay canciones que Caudal sepa leer. '
      'Sirve el .zip que te da Spotify o Google, o un .csv o .txt con título y artista.');

  static ListaExterna leer(String nombre, Uint8List bytes) {
    if (bytes.length > maxArchivo) {
      throw const ErrorImportar('Ese archivo es demasiado grande. En Google Takeout elige solo «listas de '
          'reproducción» y la «biblioteca» de YouTube Music (sin los videos).');
    }
    final n = nombre.toLowerCase();
    if (_esZip(bytes)) return _zip(bytes);
    final t = _texto(bytes);
    if (n.endsWith('.json') || RegExp(r'^\s*[\[{]').hasMatch(t)) return _lista(_json(t), 'Spotify', nombre);
    if (n.endsWith('.txt')) return _lista(deTexto(t), 'un archivo', nombre);
    final c = csv(t);
    return _lista(c.isEmpty ? deTexto(t) : c, c.any((x) => x.videoId.isNotEmpty) ? 'YouTube Music' : 'un archivo', nombre);
  }

  static ListaExterna _lista(List<CancionExterna> c, String servicio, String nombre) {
    final vistas = <String>{};
    final limpias = [for (final x in c) if (vistas.add(x.claveExterna)) x];
    if (limpias.isEmpty) throw errorVacio;
    return ListaExterna(plataforma: servicio, titulo: servicio == 'un archivo' ? nombre : 'Me gusta de $servicio',
        canciones: limpias, meGusta: true);
  }

  static bool _esZip(Uint8List b) => b.length > 4 && b[0] == 0x50 && b[1] == 0x4B && (b[2] == 3 || b[2] == 5);

  static String _texto(Uint8List b) {
    // los de Excel a veces vienen en UTF-16
    if (b.length > 2 && ((b[0] == 0xFF && b[1] == 0xFE) || (b[0] == 0xFE && b[1] == 0xFF))) {
      final grande = b[0] == 0xFE;
      return String.fromCharCodes([
        for (var i = 2; i + 1 < b.length; i += 2) grande ? (b[i] << 8) | b[i + 1] : (b[i + 1] << 8) | b[i]
      ]);
    }
    final t = utf8.decode(b, allowMalformed: true);
    return t.startsWith('﻿') ? t.substring(1) : t;
  }

  // ------------------------------------------------------------ zip

  static final _nombreMeGusta = RegExp(r'me gusta|me gustan|liked|likes|favorit|thumbs|gostei|aimé', caseSensitive: false);
  static final _nombreBiblioteca = RegExp(r'music[ _-]*library[ _-]*songs|canciones.*(biblioteca|m[uú]sica)|'
      r'(biblioteca|m[uú]sica).*canciones', caseSensitive: false);

  static ListaExterna _zip(Uint8List bytes) {
    final Archive a;
    try {
      a = ZipDecoder().decodeBytes(bytes);
    } catch (_) {
      throw const ErrorImportar('Ese .zip está dañado o incompleto. Vuelve a descargarlo.');
    }
    var total = 0;
    String? abrir(ArchiveFile f) {
      if (f.size > maxDentro || total + f.size > maxTotal) return null;
      final Uint8List d;
      try {
        d = f.readBytes() ?? Uint8List(0);
      } catch (_) {
        return null;
      }
      total += d.length;
      // lo que dice el .zip que ocupa puede ser mentira
      if (d.length > maxDentro || total > maxTotal) {
        throw const ErrorImportar('Ese .zip se hace demasiado grande al abrirlo.');
      }
      return _texto(d);
    }

    String base(ArchiveFile f) => f.name.split('/').last.split(r'\').last;
    final archivos = [for (final f in a.files) if (f.isFile && !base(f).startsWith('.')) f];

    // Spotify
    for (final f in archivos) {
      if (base(f).toLowerCase() == 'yourlibrary.json') {
        final t = abrir(f);
        if (t != null) return _lista(_json(t), 'Spotify', base(f));
      }
    }
    // Google Takeout (u otro .zip con .csv dentro)
    final csvs = [for (final f in archivos) if (base(f).toLowerCase().endsWith('.csv')) f];
    var buenos = [for (final f in csvs) if (_nombreMeGusta.hasMatch(base(f))) f];
    if (buenos.isEmpty) buenos = [for (final f in csvs) if (_nombreBiblioteca.hasMatch(base(f))) f];
    if (buenos.isEmpty && csvs.length == 1) buenos = csvs;
    final salida = <CancionExterna>[];
    for (final f in buenos) {
      final t = abrir(f);
      if (t != null) salida.addAll(csv(t));
    }
    if (salida.isEmpty && csvs.isNotEmpty) {
      throw const ErrorImportar('En ese .zip no están tus me gusta. En Google Takeout marca «YouTube y YouTube Music» › '
          '«listas de reproducción»; si lo que quieres es otra lista, descomprímelo y elige su .csv.');
    }
    return _lista(salida, 'YouTube Music', 'zip');
  }

  // ------------------------------------------------------------ json

  static List<CancionExterna> _json(String t) {
    final Object? d;
    try {
      d = jsonDecode(t);
    } catch (_) {
      throw const ErrorImportar('Ese archivo está dañado o no es el que da Spotify.');
    }
    final salida = <CancionExterna>[];
    void fila(Map m) {
      final p = m['track'] is Map ? m['track'] as Map : m;
      String s(List<String> claves) {
        for (final k in claves) {
          final v = p[k];
          if (v is String && v.trim().isNotEmpty) return v.trim();
        }
        return '';
      }

      // en YourLibrary.json «track» es el título; en las listas es un mapa con trackName
      final titulo = s(['trackName', 'track', 'title', 'name', 'titulo']);
      if (titulo.isEmpty) return;
      salida.add(CancionExterna(titulo: titulo, artista: s(['artistName', 'artist', 'artista', 'artists'])));
    }

    if (d is Map) {
      final filas = d['tracks'] ?? d['items'] ?? d['songs'] ?? d['canciones'];
      for (final f in (filas is List ? filas : const []).whereType<Map>()) {
        fila(f);
      }
    } else if (d is List) {
      for (final f in d.whereType<Map>()) {
        fila(f);
      }
    }
    return salida;
  }

  // ------------------------------------------------------------ texto y csv

  static List<CancionExterna> deTexto(String t) =>
      [for (final l in const LineSplitter().convert(t)) ?Importar.cancionDeLinea(l)];

  static String _plano(String s) {
    const de = 'áéíóúüñãõçàèìòùâêîôû', a = 'aeiouunaocaeiouaeiou';
    var x = s.toLowerCase();
    for (var i = 0; i < de.length; i++) {
      x = x.replaceAll(de[i], a[i]);
    }
    return x.replaceAll(RegExp(r'[^a-z0-9]+'), ' ').trim();
  }

  static const _colVideo = {'video id', 'id del video', 'id de video', 'id do video', 'videoid', 'youtube id'};
  static const _colTitulo = {
    'song title', 'track name', 'track title', 'title', 'titulo', 'titulo de la cancion', 'nombre de la cancion', 'song',
    'song name', 'track', 'name', 'nombre', 'cancion', 'titulo da musica', 'titulo de cancion', 'pista',
  };

  static bool _esArtista(String c) =>
      const {'artist', 'artists', 'artista', 'artistas', 'artist name', 'artist name s', 'artist names', 'artist s name'}.contains(c) ||
      RegExp(r'^(artist name|nombre del artista|nome do artista)( \d+)?$').hasMatch(c) ||
      RegExp(r'^artist ?\d+$').hasMatch(c);

  /// Las canciones de un .csv (vacío si no tiene columnas de canción).
  static List<CancionExterna> csv(String t) {
    final filas = filasCsv(t);
    // los antiguos de Google traen unas líneas antes de la cabecera
    for (var i = 0; i < filas.length && i < 12; i++) {
      final c = [for (final x in filas[i]) _plano(x)];
      final iv = c.indexWhere(_colVideo.contains);
      final it = c.indexWhere(_colTitulo.contains);
      final ia = [for (var k = 0; k < c.length; k++) if (_esArtista(c[k])) k];
      if (iv < 0 && (it < 0 || (ia.isEmpty && c.length > 1 && it != 0))) continue;
      final id = c.indexWhere((x) => x.startsWith('duration') || x.startsWith('duracion') || x == 'track duration ms');
      final salida = <CancionExterna>[];
      for (final f in filas.skip(i + 1)) {
        String v(int k) => k >= 0 && k < f.length ? f[k].trim() : '';
        final video = RegExp(r'^[A-Za-z0-9_-]{11}$').hasMatch(v(iv)) ? v(iv) : '';
        var titulo = v(it);
        var artista = [for (final k in ia) if (v(k).isNotEmpty) v(k)].join(', ');
        if (video.isEmpty && titulo.isEmpty) continue;
        // sin columna de artista: «Artista - Título»
        if (video.isEmpty && artista.isEmpty) {
          final x = Importar.cancionDeLinea(titulo);
          if (x == null) continue;
          titulo = x.titulo;
          artista = x.artista;
        }
        // Exportify separa a los artistas con comas o punto y coma
        artista = artista.replaceAll(RegExp(r'\s*;\s*'), ', ');
        salida.add(CancionExterna(titulo: titulo, artista: artista, duracion: _duracion(v(id), id >= 0 ? c[id] : ''), videoId: video));
      }
      return salida;
    }
    return const [];
  }

  static int _duracion(String v, String columna) {
    final partes = v.split(':');
    if (partes.length > 1) {
      var s = 0;
      for (final p in partes) {
        s = s * 60 + (int.tryParse(p) ?? 0);
      }
      return s;
    }
    final n = double.tryParse(v.replaceAll(',', '.')) ?? 0;
    // en milisegundos si lo dice la columna (o si no, por lo grande que es)
    return (columna.endsWith(' ms') || n > 20000 ? n / 1000 : n).round();
  }

  /// El .csv en filas (comas, punto y coma o tabulador; comillas dobles).
  static List<List<String>> filasCsv(String t) {
    final primera = t.split('\n').firstWhere((x) => x.trim().isNotEmpty, orElse: () => '');
    var sep = ',';
    var mejor = -1;
    for (final s in const [',', ';', '\t']) {
      final n = s.allMatches(primera).length;
      if (n > mejor) {
        mejor = n;
        sep = s;
      }
    }
    final filas = <List<String>>[];
    var fila = <String>[];
    final campo = StringBuffer();
    var dentro = false;
    void cerrarFila() {
      fila.add(campo.toString());
      campo.clear();
      if (fila.any((x) => x.trim().isNotEmpty)) filas.add(fila);
      fila = [];
    }

    for (var i = 0; i < t.length; i++) {
      final c = t[i];
      if (dentro) {
        if (c == '"') {
          if (i + 1 < t.length && t[i + 1] == '"') {
            campo.write('"');
            i++;
          } else {
            dentro = false;
          }
        } else {
          campo.write(c);
        }
      } else if (c == '"' && campo.isEmpty) {
        dentro = true;
      } else if (c == sep) {
        fila.add(campo.toString());
        campo.clear();
      } else if (c == '\n') {
        cerrarFila();
      } else if (c != '\r') {
        campo.write(c);
      }
    }
    cerrarFila();
    return filas;
  }
}
