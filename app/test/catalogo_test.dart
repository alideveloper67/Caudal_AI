// Pruebas del catalogo de YouTube Music. Las de red hablan con YouTube de
// verdad: necesitan internet. Se usan test() normales (no testWidgets) para
// que flutter_test no bloquee las conexiones HTTP.

import 'package:caudal/nucleo/catalogo.dart';
import 'package:flutter_test/flutter_test.dart';

const _red = Timeout(Duration(seconds: 90));

/// Comprueba la forma comun de una pista (la misma que en Python).
void _esPista(Map<String, dynamic> p) {
  for (final k in [
    'tipo', 'clave', 'video_id', 'titulo', 'artistas', 'artista', 'album',
    'duracion', 'miniatura', 'es_video', 'explicito'
  ]) {
    expect(p.containsKey(k), isTrue, reason: 'a la pista le falta "$k": $p');
  }
  expect(p['tipo'], 'pista');
  expect(p['clave'], 'yt:${p['video_id']}');
  expect((p['video_id'] as String).length, 11);
  expect(p['duracion'], isA<int>());
  expect(p['es_video'], isA<bool>());
  expect(p['explicito'], isA<bool>());
  expect(p['artistas'], isA<List>());
  expect(p['album'], isA<Map>());
}

void main() {
  group('utilidades', () {
    test('traducir titulos y subtitulos', () {
      expect(traducir('Quick picks'), 'Selección rápida');
      expect(traducir('  Moods & moments '), 'Momentos y estados de ánimo');
      expect(traducir('Similar to KAROL G'), 'Parecido a KAROL G');
      expect(traducir('Playlists by KAROL G'), 'Listas de KAROL G');
      expect(traducir('More from Shakira'), 'Más de Shakira');
      expect(traducir('Bichota radio'), 'Radio de Bichota');
      expect(traducir('Algo sin traducir'), 'Algo sin traducir');
      expect(traducir(null), '');
      expect(traducirSubtitulo('Album • 2021'), 'Álbum • 2021');
      expect(traducirSubtitulo('1.2M views'), '1.2M reproducciones');
      expect(traducirSubtitulo('263M monthly audience'), '263M oyentes al mes');
      expect(traducirSubtitulo('Song • KAROL G • 20M plays'),
          'Canción • KAROL G • 20M reproducciones');
    });

    test('segundos', () {
      expect(Catalogo.segundos('3:25'), 205);
      expect(Catalogo.segundos('1:02:03'), 3723);
      expect(Catalogo.segundos(''), 0);
      expect(Catalogo.segundos(null), 0);
      expect(Catalogo.segundos(42), 42);
      expect(Catalogo.segundos('hola'), 0);
    });

    test('videoIdDe', () {
      expect(Catalogo.videoIdDe('https://www.youtube.com/watch?v=SRkr9PyBBuU&list=x'), 'SRkr9PyBBuU');
      expect(Catalogo.videoIdDe('https://youtu.be/SRkr9PyBBuU'), 'SRkr9PyBBuU');
      expect(Catalogo.videoIdDe('https://music.youtube.com/watch?v=SRkr9PyBBuU'), 'SRkr9PyBBuU');
      expect(Catalogo.videoIdDe('https://youtube.com/shorts/abcdefghijk'), 'abcdefghijk');
      expect(Catalogo.videoIdDe('https://example.com'), '');
      expect(Catalogo.videoIdDe(null), '');
    });

    test('agrandar miniatura y nueva pista', () {
      expect(
          Catalogo.agrandarMiniatura('https://lh3.googleusercontent.com/abc=w60-h60-l90-rj'),
          'https://lh3.googleusercontent.com/abc=w544-h544-l90-rj');
      expect(Catalogo.agrandarMiniatura('https://yt3.ggpht.com/abc=s88-c-k', 300),
          'https://yt3.ggpht.com/abc=w300-h300-l90-rj');
      expect(Catalogo.agrandarMiniatura('https://i.ytimg.com/vi/x/hq.jpg'), 'https://i.ytimg.com/vi/x/hq.jpg');
      final p = Catalogo.nuevaPista('SRkr9PyBBuU',
          titulo: 'Tusa',
          artistas: [
            {'nombre': 'KAROL G', 'id': 'a'},
            {'nombre': '', 'id': 'b'},
            {'nombre': 'Nicki Minaj', 'id': 'c'}
          ],
          duracion: '3:22');
      _esPista(p);
      expect(p['artista'], 'KAROL G, Nicki Minaj');
      expect(p['duracion'], 202);
      expect(p['miniatura'], 'https://i.ytimg.com/vi/SRkr9PyBBuU/hqdefault.jpg');
      expect(Catalogo.nuevaPista('SRkr9PyBBuU')['titulo'], 'Sin título');
    });

    test('lrc a lineas', () {
      final l = Catalogo.lrcALineas('[00:03.64] Qué pasó\n[01:02.50]Segunda\n'
          '[00:10.00][00:20.00] Coro\nsin marca\n[00:00.00]');
      expect(l, [
        [0, ''],
        [3640, 'Qué pasó'],
        [10000, 'Coro'],
        [20000, 'Coro'],
        [62500, 'Segunda'],
      ]);
    });
  });

  group('YouTube Music en vivo', () {
    test('sugerencias', () async {
      final s = await Catalogo.sugerencias('karol');
      expect(s, isNotEmpty);
      expect(s.length, lessThanOrEqualTo(8));
    }, timeout: _red);

    test('buscar canciones "tusa karol g"', () async {
      final r = await Catalogo.buscar('tusa karol g', filtro: 'canciones', limite: 5);
      expect(r, isNotEmpty);
      expect(r.length, lessThanOrEqualTo(5));
      final p = r.first;
      _esPista(p);
      expect(p['artista'], contains('KAROL G'));
      expect((p['artistas'] as List).first['nombre'], 'KAROL G');
      expect(p['duracion'], greaterThan(0));
      expect(p['es_video'], isFalse);
    }, timeout: _red);

    test('buscar videos son es_video y respetan el limite', () async {
      final r = await Catalogo.buscar('karol g', filtro: 'videos', limite: 25);
      expect(r.length, greaterThan(20)); // necesito continuaciones
      expect(r.length, lessThanOrEqualTo(25));
      expect(r.every((p) => p['es_video'] == true), isTrue);
    }, timeout: _red);

    test('buscar sin filtro trae varios tipos', () async {
      final r = await Catalogo.buscar('karol g');
      expect(r, isNotEmpty);
      final tipos = r.map((e) => e['tipo']).toSet();
      expect(tipos.length, greaterThanOrEqualTo(2));
    }, timeout: _red);

    test('buscarTodo "karol g"', () async {
      final r = await Catalogo.buscarTodo('karol g');
      final principal = r['principal'] as Map<String, dynamic>;
      expect(principal['tipo'], 'artista');
      expect(principal['titulo'], 'KAROL G');
      expect(principal['id'], 'UC7n3gWRN0vQzgiOKc51aZ4w');
      final secciones = (r['secciones'] as List).cast<Map<String, dynamic>>();
      final titulos = secciones.map((s) => s['titulo']).toList();
      expect(titulos, containsAll(['Canciones', 'Artistas', 'Álbumes']));
      for (final s in secciones) {
        expect(s['elementos'], isNotEmpty);
      }
      final canciones = secciones.firstWhere((s) => s['titulo'] == 'Canciones');
      expect(canciones['estilo'], 'filas');
      for (final p in (canciones['elementos'] as List).cast<Map<String, dynamic>>()) {
        _esPista(p);
        expect(p['artistas'], isNotEmpty, reason: 'cancion sin artistas: $p');
      }
      final albumes = secciones.firstWhere((s) => s['titulo'] == 'Álbumes');
      final a = (albumes['elementos'] as List).first as Map;
      expect(a['tipo'], 'album');
      expect(a['id'], startsWith('MPRE'));
      expect(a['subtitulo'], isNotEmpty);
      final artistas = secciones.firstWhere((s) => s['titulo'] == 'Artistas');
      expect(((artistas['elementos'] as List).first as Map)['tipo'], 'artista');
    }, timeout: _red);

    test('inicio', () async {
      final r = await Catalogo.inicio();
      final secciones = (r['secciones'] as List).cast<Map<String, dynamic>>();
      expect(secciones.length, greaterThanOrEqualTo(4));
      final filas = secciones.where((s) =>
          s['estilo'] == 'filas' && (s['elementos'] as List).any((e) => e['tipo'] == 'pista'));
      expect(filas, isNotEmpty);
      for (final p in (filas.first['elementos'] as List).cast<Map<String, dynamic>>()) {
        _esPista(p);
        expect(p['es_video'], isFalse);
      }
      for (final s in secciones) {
        expect(s.keys, containsAll(['titulo', 'estribillo', 'estilo', 'elementos', 'mas']));
      }
    }, timeout: _red);

    test('artista KAROL G', () async {
      final r = await Catalogo.artista('UC7n3gWRN0vQzgiOKc51aZ4w');
      expect(r['titulo'], 'KAROL G');
      expect(r['foto'], isNotEmpty);
      expect(r['radio_id'], isNotEmpty);
      final secciones = (r['secciones'] as List).cast<Map<String, dynamic>>();
      final filas = secciones.firstWhere((s) => s['estilo'] == 'filas');
      expect((filas['elementos'] as List).length, 5);
      for (final p in (filas['elementos'] as List).cast<Map<String, dynamic>>()) {
        _esPista(p);
        expect(p['es_video'], isFalse);
      }
      expect(secciones.where((s) => s['estilo'] == 'carrusel').length, greaterThanOrEqualTo(2));
      expect(secciones.map((s) => s['titulo']), contains('Álbumes'));
    }, timeout: _red);

    test('album KG0516', () async {
      final r = await Catalogo.album('MPREb_MLvc2qKxMya');
      expect(r['titulo'], 'KG0516');
      expect(r['anio'], '2021');
      expect(r['tipo_album'], 'Álbum');
      expect(r['lista_id'], startsWith('OLAK'));
      final pistas = (r['pistas'] as List).cast<Map<String, dynamic>>();
      expect(pistas.length, 16);
      expect((r['artistas'] as List).first['nombre'], 'KAROL G');
      for (final p in pistas) {
        _esPista(p);
        expect(p['es_video'], isFalse);
        expect(p['miniatura'], r['miniatura']);
        expect(p['album'], {'nombre': 'KG0516', 'id': 'MPREb_MLvc2qKxMya'});
        expect(p['artista'], contains('KAROL G'));
        expect(p['duracion'], greaterThan(0));
      }
      expect(r['duracion'], greaterThan(40 * 60));
    }, timeout: _red);

    test('lista The Hit List', () async {
      final r = await Catalogo.lista('RDCLAK5uy_kmPRjHDECIcuVwnKsx2Ng7fyNgFKWNJFs');
      expect(r['id'], 'RDCLAK5uy_kmPRjHDECIcuVwnKsx2Ng7fyNgFKWNJFs');
      expect(r['titulo'], isNotEmpty);
      final pistas = (r['pistas'] as List).cast<Map<String, dynamic>>();
      expect(pistas.length, greaterThan(20));
      for (final p in pistas) {
        _esPista(p);
        expect(p['es_video'], isFalse);
        expect(p['artista'], isNot(endsWith('- Topic')));
      }
      expect(pistas.where((p) => (p['duracion'] as int) > 0).length, greaterThan(20));
      // el limite se respeta
      final corta = await Catalogo.lista('VLRDCLAK5uy_kmPRjHDECIcuVwnKsx2Ng7fyNgFKWNJFs', limite: 7);
      expect((corta['pistas'] as List).length, 7);
    }, timeout: _red);

    test('radio de Tusa', () async {
      final r = await Catalogo.radio(videoId: 'SRkr9PyBBuU');
      final pistas = (r['pistas'] as List).cast<Map<String, dynamic>>();
      expect(pistas.length, greaterThanOrEqualTo(20));
      expect(pistas.length, lessThanOrEqualTo(50));
      expect(pistas.first['video_id'], 'SRkr9PyBBuU');
      expect(pistas.first['artista'], contains('KAROL G'));
      for (final p in pistas) {
        _esPista(p);
        expect(p['es_video'], isFalse);
      }
      expect(r['letras_id'], startsWith('MPLY'));
      expect(r['relacionados_id'], startsWith('MPTR'));
    }, timeout: _red);

    test('letras de Tusa (sincronizadas)', () async {
      final l = await Catalogo.letras({
        'titulo': 'Tusa',
        'artistas': [
          {'nombre': 'KAROL G', 'id': ''}
        ],
        'artista': 'KAROL G',
        'duracion': 202,
        'video_id': 'SRkr9PyBBuU',
      });
      expect(l['sincronizada'], isTrue);
      final lineas = (l['lineas'] as List).cast<List>();
      expect(lineas.length, greaterThan(20));
      expect(lineas.first[0], isA<int>());
      expect(lineas.first[1], isA<String>());
      expect(l['fuente'], isNotEmpty);
    }, timeout: _red);

    test('letras sincronizadas desde YouTube Music (sin LRCLIB)', () async {
      // sin titulo ni artista no se consulta LRCLIB: va directo a YouTube Music
      final l = await Catalogo.letras({'video_id': 'SRkr9PyBBuU'});
      expect(l['texto'].toString().isNotEmpty || (l['lineas'] as List).isNotEmpty, isTrue);
      if (l['sincronizada'] == true) {
        expect((l['lineas'] as List).length, greaterThan(20));
      }
    }, timeout: _red);

    test('explorar y una pagina de genero', () async {
      final r = await Catalogo.explorar();
      final secciones = (r['secciones'] as List).cast<Map<String, dynamic>>();
      final generos = secciones.where((s) =>
          s['titulo'] == 'Momentos y estados de ánimo' || s['titulo'] == 'Géneros').toList();
      expect(generos.length, 2);
      Map<String, dynamic>? uno;
      for (final s in generos) {
        expect(s['estilo'], 'rejilla');
        for (final g in (s['elementos'] as List).cast<Map<String, dynamic>>()) {
          expect(g['tipo'], 'genero');
          expect(g['id'], isNotEmpty);
          expect(g['params'], isNotEmpty);
          expect(g['color'], matches(RegExp(r'^#[0-9A-F]{6}$')));
          expect(g['titulo'], isNotEmpty);
          uno ??= g;
        }
      }
      expect(secciones.every((s) => (s['titulo'] as String).isNotEmpty), isTrue);

      final pag = await Catalogo.pagina(uno!['id'], params: uno['params']);
      final sp = (pag['secciones'] as List).cast<Map<String, dynamic>>();
      expect(sp, isNotEmpty);
      expect(sp.every((s) => (s['elementos'] as List).isNotEmpty || s['texto'] != null), isTrue);

      final portada = await Catalogo.portadaGenero(uno['id'], uno['params']);
      expect(portada, startsWith('http'));
      // la segunda vez sale de la cache en memoria, igual
      expect(await Catalogo.portadaGenero(uno['id'], uno['params']), portada);
    }, timeout: _red);

    test('SponsorBlock responde una lista (aunque este vacia)', () async {
      final s = await Catalogo.segmentosASaltar('SRkr9PyBBuU', ['music_offtopic', 'sponsor']);
      expect(s, isA<List>());
      for (final x in s) {
        expect(x.length, 3);
        expect(x[0], isA<double>());
      }
    }, timeout: _red);

    test('un id que no existe da CatalogoError o datos vacios, sin colgarse', () async {
      try {
        final r = await Catalogo.album('MPREb_noexiste0000');
        expect(r['pistas'], isEmpty);
      } on CatalogoError catch (e) {
        expect(e.mensaje, isNotEmpty);
      }
    }, timeout: _red);
  });
}
