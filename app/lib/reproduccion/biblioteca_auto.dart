import 'package:audio_service/audio_service.dart';

import '../nucleo/catalogo.dart';
import '../nucleo/coleccion.dart';

/// Lo que se ve de Caudal en la pantalla del coche (Android Auto): carpetas
/// navegables con la biblioteca de la cuenta abierta y canciones que suenan al
/// tocarlas.
///
/// Identificadores:
///  * carpetas: `c:recientes`, `c:megusta`, `c:listas`, `c:descargas` y
///    `l:<id>` para cada lista propia;
///  * canciones: `<carpeta>|<clave>`, para saber de que lista sale la cola al
///    elegirla (`bus|<clave>` si vino de una busqueda).
class BibliotecaAuto {
  BibliotecaAuto(this.coleccion);

  Coleccion coleccion;

  /// Lo ultimo que se busco desde el coche, para poder tocarlo despues.
  final Map<String, Json> _buscadas = {};

  static const _estiloLista = 1;
  static const _estiloCuadricula = 2;

  static Map<String, dynamic> _estilo(int hijosNavegables, int hijosReproducibles) => {
        'android.media.browse.CONTENT_STYLE_SUPPORTED': true,
        'android.media.browse.CONTENT_STYLE_BROWSABLE_HINT': hijosNavegables,
        'android.media.browse.CONTENT_STYLE_PLAYABLE_HINT': hijosReproducibles,
      };

  static MediaItem _carpeta(String id, String titulo, {String? subtitulo, String? arte, int estilo = _estiloLista}) =>
      MediaItem(
        id: id,
        title: titulo,
        displaySubtitle: subtitulo,
        playable: false,
        artUri: _uri(arte),
        extras: _estilo(_estiloCuadricula, estilo),
      );

  static Uri? _uri(String? arte) {
    if (arte == null || arte.isEmpty) return null;
    // el coche no puede leer los archivos de la app: solo carátulas de internet
    if (!arte.startsWith('http')) return null;
    return Uri.tryParse(arte);
  }

  static MediaItem cancion(String carpeta, Json p) {
    final seg = p['duracion'] is num ? (p['duracion'] as num).toInt() : int.tryParse('${p['duracion']}') ?? 0;
    return MediaItem(
      id: '$carpeta|${p['clave']}',
      title: '${p['titulo'] ?? ''}',
      artist: '${p['artista'] ?? ''}',
      album: '${(p['album'] as Map?)?['nombre'] ?? ''}',
      duration: seg > 0 ? Duration(seconds: seg) : null,
      artUri: _uri('${p['miniatura'] ?? ''}'),
      playable: true,
    );
  }

  Future<List<MediaItem>> hijos(String padre) async {
    switch (padre) {
      case AudioService.browsableRootId:
        return [
          _carpeta('c:recientes', 'Recientes'),
          _carpeta('c:megusta', 'Tus me gusta'),
          _carpeta('c:listas', 'Tus listas'),
          _carpeta('c:descargas', 'Descargado'),
        ];
      case AudioService.recentRootId:
        // reanudar desde el sistema (o el coche) con lo ultimo que sono
        final r = await coleccion.escuchadoHacePoco(1);
        return [for (final p in r) cancion('c:recientes', p)];
      case 'c:listas':
        final listas = await coleccion.listas();
        final salida = <MediaItem>[];
        for (final l in listas) {
          final id = l['id'] as int;
          final portadas = await coleccion.portadasDeLista(id, 1);
          final n = (l['n'] as num?)?.toInt() ?? 0;
          salida.add(_carpeta('l:$id', '${l['nombre'] ?? 'Lista'}',
              subtitulo: n == 1 ? '1 canción' : '$n canciones', arte: portadas.isEmpty ? null : portadas.first));
        }
        return salida;
    }
    final pistas = await pistasDe(padre);
    return [for (final p in pistas) cancion(padre, p)];
  }

  /// Las canciones de una carpeta, en el orden en que se muestran.
  Future<List<Json>> pistasDe(String carpeta) async {
    if (carpeta == 'c:recientes') return coleccion.escuchadoHacePoco(50);
    if (carpeta == 'c:megusta') return coleccion.listaMeGusta();
    if (carpeta == 'c:descargas') return coleccion.descargadas(soloAudio: true);
    if (carpeta == 'bus') return _buscadas.values.toList();
    if (carpeta.startsWith('l:')) {
      final id = int.tryParse(carpeta.substring(2));
      if (id != null) return coleccion.pistasDeLista(id);
    }
    return const [];
  }

  Future<String> tituloDe(String carpeta) async {
    switch (carpeta) {
      case 'c:recientes':
        return 'Recientes';
      case 'c:megusta':
        return 'Tus me gusta';
      case 'c:descargas':
        return 'Descargado';
      case 'bus':
        return 'Búsqueda';
    }
    if (carpeta.startsWith('l:')) {
      final l = await coleccion.lista(int.tryParse(carpeta.substring(2)) ?? -1);
      return '${l?['nombre'] ?? 'Lista'}';
    }
    return 'Caudal';
  }

  /// Separa `carpeta|clave`. La clave puede llevar `|`: se corta en el primero.
  static (String, String)? partir(String mediaId) {
    final i = mediaId.indexOf('|');
    if (i <= 0) return null;
    return (mediaId.substring(0, i), mediaId.substring(i + 1));
  }

  Future<MediaItem?> elemento(String mediaId) async {
    final partes = partir(mediaId);
    if (partes == null) return null;
    final (carpeta, clave) = partes;
    final p = _buscadas[clave] ?? (await coleccion.pistas([clave])).firstOrNull;
    return p == null ? null : cancion(carpeta, p);
  }

  /// Canciones de YouTube Music; si no hay internet, lo que coincida en la biblioteca.
  Future<List<Json>> buscar(String texto, {int limite = 15}) async {
    texto = texto.trim();
    if (texto.isEmpty) return const [];
    List<Json> halladas;
    try {
      halladas = [
        for (final el in await Catalogo.buscar(texto, filtro: 'canciones', limite: limite))
          if (el['tipo'] == 'pista') el,
      ];
    } catch (_) {
      halladas = [];
    }
    if (halladas.isEmpty) halladas = await _buscarEnBiblioteca(texto, limite);
    _buscadas
      ..clear()
      ..addEntries(halladas.map((p) => MapEntry('${p['clave']}', p)));
    return halladas;
  }

  Future<List<Json>> _buscarEnBiblioteca(String texto, int limite) async {
    final t = _normal(texto);
    final vistas = <String>{};
    final salida = <Json>[];
    for (final fuente in [
      await coleccion.descargadas(soloAudio: true),
      await coleccion.listaMeGusta(),
      await coleccion.escuchadoHacePoco(200),
    ]) {
      for (final p in fuente) {
        final texto = _normal('${p['titulo'] ?? ''} ${p['artista'] ?? ''}');
        if (texto.contains(t) && vistas.add('${p['clave']}')) salida.add(p);
        if (salida.length >= limite) return salida;
      }
    }
    return salida;
  }

  static String _normal(String s) {
    const de = 'áéíóúüñàèìòù';
    const a = 'aeiouunaeiou';
    final b = StringBuffer();
    for (final c in s.toLowerCase().split('')) {
      final i = de.indexOf(c);
      b.write(i < 0 ? c : a[i]);
    }
    return b.toString();
  }
}
