import 'dart:convert';

import 'coleccion.dart' show Json;
import 'mixes.dart' show artistasDe;

/// Por dónde sale el sonido.
enum SalidaAudio {
  audifonos('Audífonos', 'Con cable o USB'),
  bocina('Bocina del teléfono', 'O una bocina por cable'),
  bluetooth('Bluetooth', 'Audífonos o bocina inalámbricos');

  const SalidaAudio(this.nombre, this.detalle);
  final String nombre;
  final String detalle;

  static SalidaAudio? porNombre(Object? n) {
    for (final s in values) {
      if (s.name == n) return s;
    }
    return null;
  }
}

/// Los géneros que se reconocen para recordar un ecualizador por género.
class GeneroEq {
  GeneroEq._();

  /// clave -> (nombre bonito, palabras que lo delatan en el título, artista o género).
  static const todos = <String, (String, String)>{
    'reggaeton': ('Reguetón', r'reggaet|regueto|perreo|dembow|urbano'),
    'hiphop': ('Hip hop', r'hip[ -]?hop|\brap\b|\btrap\b|drill'),
    'electronica': ('Electrónica', r'electro|\bedm\b|deep house|house music|techno|trance|dubstep|club mix'),
    'rock': ('Rock', r'\brock\b|metal|punk|grunge|hard rock'),
    'pop': ('Pop', r'\bpop\b|k-?pop'),
    'clasica': ('Clásica', r'clasica|classical|sinfonia|symphony|concerto|sonata|orquesta|orchestra'),
    'jazz': ('Jazz', r'\bjazz\b|\bblues\b|swing|bossa'),
    'acustica': ('Acústica', r'acustic|acoustic|unplugged|folk'),
    'tropical': ('Salsa y tropical', r'salsa|cumbia|bachata|merengue|vallenato|tropical'),
    'lofi': ('Lo-fi y calma', r'lo-?fi|chill|ambient|relax'),
  };

  static String _plano(String t) => t
      .toLowerCase()
      .replaceAll('á', 'a')
      .replaceAll('é', 'e')
      .replaceAll('í', 'i')
      .replaceAll('ó', 'o')
      .replaceAll('ú', 'u')
      .replaceAll('ñ', 'n');

  /// El género de una canción: el que traiga la pista (`genero`), el de la lista de género
  /// de donde viene ([contexto]) o, si no, el que dicen las palabras del título y el artista.
  /// Devuelve `''` si no hay forma de saberlo (mejor eso que adivinar mal).
  static String de(Json pista, {Json? contexto}) {
    String clave(String texto) {
      final t = _plano(texto);
      for (final e in todos.entries) {
        if (e.key == t || RegExp(e.value.$2).hasMatch(t)) return e.key;
      }
      return '';
    }

    final propio = '${pista['genero'] ?? pista['genre'] ?? ''}'.trim();
    if (propio.isNotEmpty) {
      final c = clave(propio);
      if (c.isNotEmpty) return c;
    }
    if (contexto != null && contexto['tipo'] == 'genero') {
      final c = clave('${contexto['titulo'] ?? ''}');
      if (c.isNotEmpty) return c;
    }
    return clave('${pista['titulo'] ?? ''} ${pista['artista'] ?? ''}');
  }

  static String nombre(String clave) => todos[clave]?.$1 ?? clave;
}

/// Un ajuste del ecualizador recordado para un artista.
class ReglaArtista {
  const ReglaArtista(this.nombre, this.perfil);
  final String nombre;
  final String perfil;
}

/// Qué ecualizador toca según la salida del sonido, el género y el artista.
/// Manda lo más específico: artista, luego género, luego salida. Lógica pura.
class PerfilesEq {
  PerfilesEq({
    this.detectar = true,
    this.manual,
    Map<String, String>? salidas,
    Map<String, String>? generos,
    Map<String, ReglaArtista>? artistas,
  })  : salidas = salidas ?? {},
        generos = generos ?? {},
        artistas = artistas ?? {};

  /// Si se usa la salida que detecta el sistema; si no, el perfil elegido a mano.
  bool detectar;

  /// El perfil elegido a mano (y el que vale cuando el sistema no deja detectar).
  SalidaAudio? manual;

  /// salida -> nombre del ajuste (de los ajustes del ecualizador).
  final Map<String, String> salidas;

  /// género -> nombre del ajuste.
  final Map<String, String> generos;

  /// clave del artista -> su ajuste.
  final Map<String, ReglaArtista> artistas;

  bool get vacio => salidas.isEmpty && generos.isEmpty && artistas.isEmpty;

  /// La salida que vale ahora: la detectada, o la elegida a mano si no hay o no se quiere detectar.
  SalidaAudio? salidaEfectiva(SalidaAudio? detectada) => detectar && detectada != null ? detectada : manual;

  /// El ajuste que toca para [pista], o null si ninguna regla aplica (no se toca nada).
  String? perfilPara(Json pista, SalidaAudio? detectada, {Json? contexto}) {
    for (final a in artistasDe(pista).take(2)) {
      final r = artistas[a.clave];
      if (r != null && r.perfil.isNotEmpty) return r.perfil;
    }
    final g = GeneroEq.de(pista, contexto: contexto);
    if (g.isNotEmpty) {
      final r = generos[g];
      if (r != null && r.isNotEmpty) return r;
    }
    final s = salidaEfectiva(detectada);
    if (s != null) {
      final r = salidas[s.name];
      if (r != null && r.isNotEmpty) return r;
    }
    return null;
  }

  /// De dónde viene el ajuste que toca (para decírselo a la persona).
  String? motivoPara(Json pista, SalidaAudio? detectada, {Json? contexto}) {
    for (final a in artistasDe(pista).take(2)) {
      final r = artistas[a.clave];
      if (r != null && r.perfil.isNotEmpty) return 'Recordado para ${r.nombre.isEmpty ? a.nombre : r.nombre}';
    }
    final g = GeneroEq.de(pista, contexto: contexto);
    if (g.isNotEmpty && (generos[g] ?? '').isNotEmpty) return 'Recordado para ${GeneroEq.nombre(g)}';
    final s = salidaEfectiva(detectada);
    if (s != null && (salidas[s.name] ?? '').isNotEmpty) return 'Para ${s.nombre.toLowerCase()}';
    return null;
  }

  void ponerSalida(SalidaAudio s, String? perfil) =>
      perfil == null || perfil.isEmpty ? salidas.remove(s.name) : salidas[s.name] = perfil;

  void ponerGenero(String genero, String? perfil) =>
      perfil == null || perfil.isEmpty ? generos.remove(genero) : generos[genero] = perfil;

  void ponerArtista(String clave, String nombre, String? perfil) {
    if (perfil == null || perfil.isEmpty) {
      artistas.remove(clave);
    } else {
      artistas.remove(clave);
      artistas[clave] = ReglaArtista(nombre, perfil); // las más nuevas quedan al final
      while (artistas.length > 60) {
        artistas.remove(artistas.keys.first);
      }
    }
  }

  Map<String, Object?> aJson() => {
        'detectar': detectar,
        'manual': manual?.name ?? '',
        'salidas': salidas,
        'generos': generos,
        'artistas': {
          for (final e in artistas.entries) e.key: {'n': e.value.nombre, 'p': e.value.perfil}
        },
      };

  String aTexto() => jsonEncode(aJson());

  static PerfilesEq desde(Object? d) {
    try {
      if (d is String) d = jsonDecode(d);
      if (d is! Map) return PerfilesEq();
      Map<String, String> textos(Object? m) =>
          m is Map ? {for (final e in m.entries) if ('${e.value}'.isNotEmpty) '${e.key}': '${e.value}'} : {};
      final art = <String, ReglaArtista>{};
      final a = d['artistas'];
      if (a is Map) {
        for (final e in a.entries) {
          final v = e.value;
          if (v is Map && '${v['p'] ?? ''}'.isNotEmpty) art['${e.key}'] = ReglaArtista('${v['n'] ?? ''}', '${v['p']}');
        }
      }
      return PerfilesEq(
        detectar: d['detectar'] != false,
        manual: SalidaAudio.porNombre(d['manual']),
        salidas: textos(d['salidas']),
        generos: textos(d['generos']),
        artistas: art,
      );
    } catch (_) {
      return PerfilesEq();
    }
  }
}
