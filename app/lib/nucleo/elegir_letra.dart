/// Que la letra sea la de ESTA canción: cuentas puras, sin red (mismas reglas en el
/// escritorio: escritorio/descargador/elegir_letra.py).
///
/// Una letra encontrada por búsqueda solo vale si el título y el artista son los de la
/// canción, si es la misma versión (en vivo, remix, acústica…) y, cuando YouTube Music da
/// el texto de esa canción, si las palabras coinciden. Sus tiempos solo valen si además
/// dura lo mismo.
library;

/// Una forma de nombrar la canción: título, artista y los artistas que valen.
typedef FormaLetra = ({String titulo, String artista, List<String> valen});

/// Lo elegido: [con] sirve con sus tiempos; [texto], solo como texto; [otra] tiene
/// tiempos, pero de una grabación que dura distinto.
typedef LetraElegida = ({Map<String, dynamic>? con, Map<String, dynamic>? texto, Map<String, dynamic>? otra});

class ElegirLetra {
  ElegirLetra._();

  /// Más diferencia de duración (s): los tiempos serían de otra grabación.
  static const diferenciaMax = 2.5;

  /// Lo que puede diferir la duración de un video y la de su canción oficial (s).
  static const diferenciaOficial = 2.0;

  /// Palabras en común con la letra de YouTube Music para darla por buena.
  static const parecidoMin = 0.6;

  // palabras del título que cambian la grabación (y con ella, los tiempos o la letra)
  static final Map<String, RegExp> _versiones = {
    'remix': r'remix|rmx|bootleg|mashup|mix(?!tape)',
    'vivo': r'live|en vivo|en directo|ao vivo|concierto|concert|unplugged|tour',
    'acustica': r'acoustic|acustic[oa]',
    'instrumental': r'instrumental|karaoke|backing track|pista',
    'cover': r'cover|tributo|tribute|version de',
    'rapida': r'sped up|speed up|nightcore|acelerad[oa]',
    'lenta': r'slowed|reverb|screwed',
    'sesion': r'session|sesion|sessions',
    'demo': r'demo',
    'orquesta': r'sinfonic[oa]|symphonic|orchestral|piano version|version piano',
  }.map((k, p) => MapEntry(k, RegExp('\\b(?:$p)\\b')));

  static const _ruidoTxt = r'official|oficial|video|audio|lyrics?|letra|visuali[sz]er|hd|hq|4k|8k|1080p|720p|clip|full|'
      r'remaster(?:ed|izad[oa])?|mono|stereo|explicit|clean|prod|color coded|subtitulad[oa]|sub|'
      r'estreno|nuevo|new|album version|radio edit|single version|\d{4}';
  static final _ruido = RegExp('\\b(?:$_ruidoTxt)\\b');
  static final _invitados = RegExp(r'^(?:\b(?:feat|ft|featuring|with|con la participacion de|junto a)\b)');

  static const _con =
      'àáâãäåçèéêëìíîïñòóôõöùúûüýÿāăąćĉċčďēĕėęěĝğġģĥĩīĭįĵķĺļľńņňōŏőŕŗřśŝşšţťũūŭůűųŵŷźżžơưǎǐǒǔǖǘǚǜ'
      'ǟǡǧǩǫǭǰǵǹǻȁȃȅȇȉȋȍȏȑȓȕȗșțȟȧȩȫȭȯȱȳḁḃḅḇḉḋḍḏḑḓḕḗḙḛḝḟḡḣḥḧḩḫḭḯḱḳḵḷḹḻḽḿṁṃṅṇṉṋṍṏṑṓṕṗṙṛṝṟṡṣṥṧṩṫṭṯṱṳ'
      'ṵṷṹṻṽṿẁẃẅẇẉẋẍẏẑẓẕẖẗẘẙẛạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹøłđħ';
  static const _sin =
      'aaaaaaceeeeiiiinooooouuuuyyaaaccccdeeeeegggghiiiijklllnnnooorrrssssttuuuuuuwyzzzouaiouuuuu'
      'aagkoojgnaaaeeiioorruusthaeooooyabbbcdddddeeeeefghhhhhiikkkllllmmmnnnnoooopprrrrsssssttttu'
      'uuuuvvwwwwwxxyzzzhtwysaaaaaaaaaaaaeeeeeeeeiioooooooooooouuuuuuuyyyyoldh';

  /// Minúsculas, sin tildes ni signos, en cualquier alfabeto: «¡Tití!» → «titi».
  static String normalizar(Object? texto) {
    final b = StringBuffer();
    for (final r in '${texto ?? ''}'.toLowerCase().runes) {
      if (r >= 0x300 && r <= 0x36F) continue; // tildes sueltas
      final c = String.fromCharCode(r);
      final i = r < 0x80 ? -1 : _con.indexOf(c);
      b.write(i >= 0 ? _sin[i] : (c == 'ß' ? 'ss' : c));
    }
    return b
        .toString()
        .replaceAll(RegExp("['’`´]"), '')
        .replaceAll(RegExp(r'[^\p{L}\p{N}\p{M}]+', unicode: true), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
  }

  /// Qué versión dice ser el título: {'remix', 'vivo'…} (vacío: la de siempre).
  static Set<String> versiones(Object? titulo) {
    final n = normalizar(titulo);
    return {for (final e in _versiones.entries) if (e.value.hasMatch(n)) e.key};
  }

  /// El título sin adornos: «Adele - Hello (Official Video) [HD]» → «Adele - Hello».
  static String tituloLimpio(Object? titulo) {
    var t = '${titulo ?? ''}'.replaceFirst(RegExp(r'^\s*(?:0\d|\d{1,2}\s*[.\-_)])\s*(?=\D)'), ''); // «01 La Flaca»
    t = t.replaceAllMapped(RegExp(r'[(\[{【]([^)\]}】]*)[)\]}】]'), (m) {
      final dentro = normalizar(m[1]);
      return _invitados.hasMatch(dentro) || (versiones(dentro).isEmpty && _ruido.hasMatch(dentro)) ? ' ' : m[0]!;
    });
    t = t.split(RegExp(r'\s[|·•]\s|\s\|\||//')).first;
    // «Junior H Ft. Jose Mejia - Suena»: el invitado se quita, la canción no
    t = t.replaceFirst(RegExp(r'\s+(?:feat|ft|featuring)\b\.?.*?(?=\s+[-–—]\s+|$)', caseSensitive: false), '');
    t = t.replaceFirst(
        RegExp(r'\s+(?:official|oficial)\s+(?:music\s+)?(?:video|audio|lyric video)\s*$', caseSensitive: false), '');
    t = t.replaceFirst(RegExp(r'\s+(?:video|audio)\s+oficial\s*$', caseSensitive: false), '');
    return t
        .replaceAll(RegExp(r'\s+'), ' ')
        .replaceAll(RegExp('^[ \\-–—"\']+|[ \\-–—"\']+\$'), '');
  }

  /// «Luis Fonsi & Daddy Yankee» → el texto entero y cada nombre.
  static List<String> nombres(Object? texto) {
    final crudo = '${texto ?? ''}';
    final partes = crudo.split(RegExp(
        r'\s*(?:,|;|/|&|\+|\sx\s|\sy\s|\sand\s|\sfeat\.?\s|\sft\.?\s|\svs\.?\s|\scon\s)\s*', caseSensitive: false));
    final salida = <String>[];
    for (final p in [crudo, ...partes]) {
      final n = normalizar(p)
          .replaceAll(RegExp(r'\b(?:topic|vevo|oficial|official|tv|music)\b'), '')
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim();
      if (n.isNotEmpty && !salida.contains(n)) salida.add(n);
    }
    return salida;
  }

  /// Cuánto se parecen dos textos (0..1): lo que comparten en el mismo orden.
  static double parecido(String a, String b) {
    if (a.isEmpty || b.isEmpty) return 0;
    var antes = List<int>.filled(b.length + 1, 0);
    for (var i = 0; i < a.length; i++) {
      final ahora = List<int>.filled(b.length + 1, 0);
      for (var j = 0; j < b.length; j++) {
        ahora[j + 1] = a.codeUnitAt(i) == b.codeUnitAt(j)
            ? antes[j] + 1
            : (antes[j + 1] > ahora[j] ? antes[j + 1] : ahora[j]);
      }
      antes = ahora;
    }
    return 2 * antes[b.length] / (a.length + b.length);
  }

  static bool _parecidos(String a, String b) {
    if (a.isEmpty || b.isEmpty) return false;
    if (a == b) return true;
    final ja = a.replaceAll(' ', ''), jb = b.replaceAll(' ', '');
    if (ja == jb) return true;
    if (ja.length < 4 || jb.length < 4) return false;
    return parecido(ja, jb) >= 0.84;
  }

  /// ¿Alguno de los artistas coincide? «Juanes» con «Juanes feat. X»: sí.
  static bool mismoArtista(List<String> dePista, Object? deLetra) {
    final otros = nombres(deLetra);
    for (final a in dePista) {
      for (final b in otros) {
        if (_parecidos(a, b)) return true;
        // «Grupo Néctar» y «Néctar»: todas las palabras del corto están en el largo
        final pa = a.split(' '), pb = b.split(' ');
        final corto = pa.length <= pb.length ? pa : pb;
        final largo = (pa.length <= pb.length ? pb : pa).toSet();
        if (corto.join().length >= 5 && corto.every(largo.contains)) return true;
      }
    }
    return false;
  }

  static String _sinVersion(String n) {
    for (final p in _versiones.values) {
      n = n.replaceAll(p, ' ');
    }
    return n.replaceAll(_ruido, ' ').replaceAll(RegExp(r'\s+'), ' ').trim();
  }

  /// ¿Es el mismo título? «Gasolina» y «Gasolina (feat. Glory)»: sí. «Hello» y «Hello Goodbye»: no.
  static bool mismoTitulo(Object? dePista, Object? deLetra) {
    String oEntero(String n) {
      final s = _sinVersion(n);
      return s.isEmpty ? n : s;
    }

    final a = normalizar(tituloLimpio(dePista)), b = normalizar(tituloLimpio(deLetra));
    if (_parecidos(a, b) || _parecidos(oEntero(a), oEntero(b))) return true;
    // lo de entre paréntesis cambia de una ficha a otra
    final par = RegExp(r'[(\[].*?[)\]]');
    final qa = normalizar('${dePista ?? ''}'.replaceAll(par, ' ')), qb = normalizar('${deLetra ?? ''}'.replaceAll(par, ' '));
    return qa.isNotEmpty && qb.isNotEmpty && _parecidos(oEntero(qa), oEntero(qb));
  }

  /// Las formas de nombrar la canción. Los videos subidos por cualquiera traen
  /// «Artista - Canción» en el título y el canal como artista.
  static List<FormaLetra> consultas(Map<String, dynamic> pista) {
    final titulo = tituloLimpio(pista['titulo']);
    final arts = [
      for (final a in (pista['artistas'] is List ? pista['artistas'] as List : const []))
        if (a is Map && '${a['nombre'] ?? ''}'.isNotEmpty) '${a['nombre']}'
    ];
    final suelto = '${pista['artista'] ?? ''}';
    final artista = arts.isNotEmpty ? arts.first : suelto;
    final valen = <String>[];
    for (final x in [...arts, suelto]) {
      for (final n in nombres(x)) {
        if (!valen.contains(n)) valen.add(n);
      }
    }
    final salida = <FormaLetra>[];
    final m = RegExp(r'^(.*?)\s+[-–—]\s+(.*)$').firstMatch(titulo);
    if (m != null && normalizar(m[1]).isNotEmpty && normalizar(m[2]).isNotEmpty) {
      final izq = m[1]!, der = m[2]!;
      if (mismoArtista(valen, izq)) return [(titulo: der, artista: izq, valen: [...valen, ...nombres(izq)])];
      if (mismoArtista(valen, der)) return [(titulo: izq, artista: der, valen: [...valen, ...nombres(der)])];
      salida
        ..add((titulo: der, artista: izq, valen: nombres(izq)))
        ..add((titulo: izq, artista: der, valen: nombres(der)));
    }
    if (titulo.isNotEmpty && valen.isNotEmpty) salida.insert(0, (titulo: titulo, artista: artista, valen: valen));
    return salida;
  }

  /// Cuánto de la letra más corta está en la otra, por parejas de palabras seguidas (0..1): dos
  /// canciones distintas comparten «que», «de», «amor», pero no las frases.
  static double palabrasEnComun(String a, String b) {
    Set<String> pares(String t) {
      final w = normalizar(t.replaceAll(RegExp(r'[(\[].*?[)\]]'), ' ')).split(' ');
      if (w.length < 12) {
        // sin espacios entre palabras (japonés, chino…): por letras
        final j = w.join();
        return {for (var i = 0; i + 3 <= j.length; i++) j.substring(i, i + 3)};
      }
      return {for (var i = 0; i + 1 < w.length; i++) '${w[i]} ${w[i + 1]}'};
    }

    final pa = pares(a), pb = pares(b);
    if (pa.isEmpty || pb.isEmpty) return 0;
    return pa.where(pb.contains).length / (pa.length < pb.length ? pa.length : pb.length);
  }

  /// Cuántos segundos más tarde van los versos de [a] que los mismos de [b]; null si coinciden pocos o
  /// no se ponen de acuerdo.
  static double? corrimiento(List<(int, String)> a, List<(int, String)> b) {
    final na = [for (final x in a) (x.$1, normalizar(x.$2))], nb = [for (final x in b) (x.$1, normalizar(x.$2))];
    final difs = <double>[];
    for (final (ms, n) in na) {
      if (n.split(' ').length < 3) continue;
      final mismos = [for (final y in nb) if (y.$2 == n) y.$1];
      // los que se repiten no dicen cuál es cuál
      if (mismos.length == 1 && na.where((x) => x.$2 == n).length == 1) difs.add((ms - mismos.first) / 1000);
    }
    if (difs.length < 4) return null;
    difs.sort();
    final medio = difs[difs.length ~/ 2];
    return difs.where((d) => (d - medio).abs() <= 1).length >= 0.6 * difs.length ? medio : null;
  }

  /// El texto corrido de una ficha de LRCLIB.
  static String textoDe(Map<String, dynamic> c) {
    final t = '${c['plainLyrics'] ?? ''}';
    if (t.trim().isNotEmpty) return t;
    return '${c['syncedLyrics'] ?? ''}'.replaceAll(RegExp(r'\[[\d:.]+\]|<[\d:.]+>'), '');
  }

  static bool tieneTiempos(Map<String, dynamic> c) => '${c['syncedLyrics'] ?? ''}'.trim().isNotEmpty;

  /// ¿La ficha de LRCLIB es de esta canción (título, artista y versión)?
  static bool esLaCancion(Map<String, dynamic> c, Map<String, dynamic> pista, [List<FormaLetra>? formas]) {
    if (c['instrumental'] == true) return false;
    final t2 = '${c['trackName'] ?? c['name'] ?? ''}', a2 = '${c['artistName'] ?? ''}';
    final v1 = versiones(pista['titulo']), v2 = versiones(t2);
    if (versiones(c['albumName']).contains('instrumental')) v2.add('instrumental');
    const iguales = {'sesion', 'demo'};
    if (v1.difference(v2).union(v2.difference(v1)).difference(iguales).isNotEmpty) return false;
    return (formas ?? consultas(pista)).any((f) => mismoTitulo(f.titulo, t2) && mismoArtista(f.valen, a2));
  }

  /// De las fichas de LRCLIB, las que sirven para [pista]. [textoBueno]: la letra que da YouTube
  /// Music para ese video (sin tiempos), para descartar las que digan otra cosa.
  static LetraElegida elegir(Iterable<Map<String, dynamic>> candidatos, Map<String, dynamic> pista,
      {double duracion = 0, String textoBueno = ''}) {
    final formas = consultas(pista);
    double distancia(Map<String, dynamic> c) {
      final d = c['duration'] is num ? (c['duration'] as num).toDouble() : 0.0;
      if (duracion <= 0) return 0;
      return d > 0 ? (d - duracion).abs() : 1;
    }

    final buenas = [
      for (final c in candidatos)
        if (esLaCancion(c, pista, formas) &&
            (textoBueno.trim().isEmpty || palabrasEnComun(textoDe(c), textoBueno) >= parecidoMin))
          c
    ];
    // orden estable por distancia
    final orden = List<int>.generate(buenas.length, (i) => i)
      ..sort((x, y) {
        final d = distancia(buenas[x]).compareTo(distancia(buenas[y]));
        return d != 0 ? d : x.compareTo(y);
      });
    Map<String, dynamic>? con, texto, otra;
    for (final i in orden) {
      final c = buenas[i];
      if (tieneTiempos(c)) {
        if (con == null && distancia(c) <= diferenciaMax) {
          con = c;
        } else {
          otra ??= c;
        }
      }
      if (texto == null && textoDe(c).trim().isNotEmpty) texto = c;
    }
    return (con: con, texto: texto, otra: otra);
  }
}
