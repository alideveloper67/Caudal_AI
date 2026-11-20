/// «título|primer artista» sin tildes ni adornos: la misma canción subida dos
/// veces (con otro video) se reconoce igual. Lo usan la fusión de «me gusta»
/// traídos de otras apps y su versión de escritorio (importacion.py).
library;

final _adornos = RegExp(
    r'[\(\[][^\)\]]*(official|oficial|video|vídeo|lyrics?|letra|audio|hd|hq|4k|mv|visualizer|remaster(ed)?)[^\)\]]*[\)\]]',
    caseSensitive: false);

const _tildes = {
  'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a', 'ã': 'a', 'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e',
  'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i', 'ó': 'o', 'ò': 'o', 'ö': 'o', 'ô': 'o', 'õ': 'o',
  'ú': 'u', 'ù': 'u', 'ü': 'u', 'û': 'u', 'ñ': 'n', 'ç': 'c',
};

String _limpio(String s) {
  var t = s.replaceAll(_adornos, '').toLowerCase();
  final b = StringBuffer();
  for (final c in t.split('')) {
    b.write(_tildes[c] ?? c);
  }
  return b.toString().replaceAll(RegExp(r'[^a-z0-9]+'), ' ').trim();
}

String huellaCancion(String titulo, [String artista = '']) {
  final primero = artista.split(RegExp(r',|&| feat\.? | ft\.? | x ')).first;
  return '${_limpio(titulo)}|${_limpio(primero)}';
}

String huellaPista(Map<String, dynamic> p) {
  var artista = '${p['artista'] ?? ''}';
  if (artista.isEmpty && p['artistas'] is List) {
    artista = (p['artistas'] as List).whereType<Map>().map((a) => '${a['nombre'] ?? ''}').join(', ');
  }
  return huellaCancion('${p['titulo'] ?? ''}', artista);
}

/// (nuevas, repetidas): fuera las que ya están (por clave o por huella) y las
/// repetidas dentro de la misma tanda.
(List<Map<String, dynamic>>, int) separarNuevas(
    List<Map<String, dynamic>> pistas, Iterable<String> clavesActuales, Iterable<String> huellasActuales) {
  final claves = {...clavesActuales};
  final huellas = {...huellasActuales};
  final nuevas = <Map<String, dynamic>>[];
  var repetidas = 0;
  for (final p in pistas) {
    final clave = p['clave'];
    final h = huellaPista(p);
    if (clave is! String || clave.isEmpty || claves.contains(clave) || (h != '|' && huellas.contains(h))) {
      repetidas++;
      continue;
    }
    claves.add(clave);
    huellas.add(h);
    nuevas.add(p);
  }
  return (nuevas, repetidas);
}
