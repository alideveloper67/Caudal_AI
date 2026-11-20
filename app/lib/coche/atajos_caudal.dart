/// Lo que piden los accesos directos del icono (mantener pulsado Caudal), el
/// asistente de Google y el aviso del modo coche. Todo llega como un enlace
/// `caudal://...` que la app ya recibe por el canal de «compartido»:
///
///  * `caudal://megusta`            tus me gusta en aleatorio
///  * `caudal://buscar?q=texto`     la pestaña Buscar (con el texto, si lo hay)
///  * `caudal://descargas`          tu música descargada
///  * `caudal://mix`                tu mix del día
///  * `caudal://coche`              el modo coche
///  * `caudal://sonar?q=texto`      «Ok Google, pon ... en Caudal»
///  * `caudal://funcion?nombre=...` «Ok Google, abre ... en Caudal» (App Actions)
///
/// Los demás enlaces (`juntos`, `lista`, `estudio`, `acceso`) no son de aquí y
/// se devuelven como `null` para que los atienda quien ya los atendía.
library;

enum TipoAtajo { meGustaAleatorio, buscar, descargas, miMix, modoCoche, sonar }

class AtajoCaudal {
  const AtajoCaudal(this.tipo, {this.texto = ''});

  final TipoAtajo tipo;

  /// Lo que se quiere buscar o poner (solo en [TipoAtajo.buscar] y [TipoAtajo.sonar]).
  final String texto;

  @override
  bool operator ==(Object other) => other is AtajoCaudal && other.tipo == tipo && other.texto == texto;

  @override
  int get hashCode => Object.hash(tipo, texto);

  @override
  String toString() => 'AtajoCaudal(${tipo.name}${texto.isEmpty ? '' : ', «$texto»'})';
}

/// Los enlaces de los accesos directos del icono, en el mismo orden que en `shortcuts.xml`.
const enlacesAtajos = <TipoAtajo, String>{
  TipoAtajo.meGustaAleatorio: 'caudal://megusta',
  TipoAtajo.buscar: 'caudal://buscar',
  TipoAtajo.descargas: 'caudal://descargas',
  TipoAtajo.miMix: 'caudal://mix',
  TipoAtajo.modoCoche: 'caudal://coche',
};

/// El atajo que pide [entrada], o `null` si no es un enlace de los de aquí.
AtajoCaudal? leerAtajo(String entrada) {
  final t = entrada.trim();
  if (!t.toLowerCase().startsWith('caudal://')) return null;
  final uri = Uri.tryParse(t);
  if (uri == null) return null;
  final q = _parametro(uri, const ['q', 'query', 'texto']);
  switch (uri.host.toLowerCase()) {
    case 'megusta' || 'me-gusta' || 'favoritas':
      return const AtajoCaudal(TipoAtajo.meGustaAleatorio);
    case 'buscar':
      return AtajoCaudal(TipoAtajo.buscar, texto: q);
    case 'descargas':
      return const AtajoCaudal(TipoAtajo.descargas);
    case 'mix':
      return const AtajoCaudal(TipoAtajo.miMix);
    case 'coche':
      return const AtajoCaudal(TipoAtajo.modoCoche);
    case 'sonar':
      // «Ok Google, pon música en Caudal», sin decir qué: tus me gusta
      return q.isEmpty ? const AtajoCaudal(TipoAtajo.meGustaAleatorio) : AtajoCaudal(TipoAtajo.sonar, texto: q);
    case 'funcion':
      return atajoDeFuncion(_parametro(uri, const ['nombre', 'feature']));
  }
  return null;
}

String _parametro(Uri uri, List<String> nombres) {
  for (final n in nombres) {
    final v = uri.queryParameters[n];
    if (v != null && v.trim().isNotEmpty) return v.trim();
  }
  return '';
}

/// Lo que dijo la persona en «abre ... en Caudal»: el identificador de un acceso
/// directo (si el asistente lo reconoció) o la frase tal cual. Si no se parece a
/// nada conocido se busca, que es lo menos sorprendente.
AtajoCaudal atajoDeFuncion(String dicho) {
  final t = normalizarVoz(dicho);
  if (t.isEmpty) return const AtajoCaudal(TipoAtajo.buscar);
  final palabras = t.split(' ');
  // una palabra: cuenta si alguna palabra dicha empieza así («descarg» vale por
  // «descargas»); varias: tienen que ir juntas. «Autoestima» no es «auto».
  bool hay(List<String> claves) => claves.any((c) => c.contains(' ')
      ? ' $t '.contains(' $c ')
      : palabras.any((w) => c.length <= 4 ? w == c : w.startsWith(c)));
  if (hay(const ['coche', 'coches', 'auto', 'carro', 'manejar', 'conducir', 'conduciendo', 'volante'])) {
    return const AtajoCaudal(TipoAtajo.modoCoche);
  }
  if (hay(const ['gusta', 'gustan', 'megusta', 'favorit', 'corazon'])) return const AtajoCaudal(TipoAtajo.meGustaAleatorio);
  if (hay(const ['descarg', 'sin internet', 'sin conexion', 'offline'])) return const AtajoCaudal(TipoAtajo.descargas);
  if (hay(const ['mix', 'mixes', 'mezcla del dia'])) return const AtajoCaudal(TipoAtajo.miMix);
  if (hay(const ['buscar', 'busca', 'buscador', 'busqueda'])) {
    final resto = t.replaceAll(RegExp(r'\b(buscar|busca|buscador|busqueda|el|la)\b'), ' ').trim();
    return AtajoCaudal(TipoAtajo.buscar, texto: resto.replaceAll(RegExp(r'\s+'), ' '));
  }
  return AtajoCaudal(TipoAtajo.buscar, texto: dicho.trim());
}

/// Minúsculas, sin tildes y sin signos: así «Mis Me Gusta», «mis me gusta» y
/// «mis megústa» valen lo mismo.
String normalizarVoz(String s) {
  const de = 'áéíóúüñàèìòù';
  const a = 'aeiouunaeiou';
  final b = StringBuffer();
  for (final c in s.toLowerCase().split('')) {
    final i = de.indexOf(c);
    if (i >= 0) {
      b.write(a[i]);
    } else if (RegExp(r'[a-z0-9 ]').hasMatch(c)) {
      b.write(c);
    } else {
      b.write(' ');
    }
  }
  return b.toString().replaceAll(RegExp(r'\s+'), ' ').trim();
}
