import 'dart:convert';

import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/importar.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('enlaces', () {
    test('reconoce cada plataforma', () {
      expect(Importar.plataforma('https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M'), 'spotify');
      expect(Importar.plataforma('https://music.apple.com/us/playlist/x/pl.123'), 'apple');
      expect(Importar.plataforma('https://music.youtube.com/playlist?list=PL1'), 'youtube');
      expect(Importar.plataforma('https://ejemplo.com'), '');
    });

    test('saca el enlace de un texto compartido', () {
      expect(Importar.enlaceDe('Escucha esto en Spotify: https://open.spotify.com/playlist/abc?si=1 ¡dale!'),
          'https://open.spotify.com/playlist/abc?si=1');
    });

    test('sin enlace valido avisa con palabras', () async {
      expect(() => Importar.leer('hola'), throwsA(isA<ErrorImportar>()));
    });
  });

  test('lee la pagina de Spotify', () {
    final datos = {
      'props': {
        'pageProps': {
          'state': {
            'data': {
              'entity': {
                'name': 'Mi &amp; lista',
                'subtitle': 'Ana',
                'trackList': [
                  {'title': 'Canción 1', 'subtitle': 'Artista A', 'duration': 201000},
                  {'title': '', 'subtitle': 'nada'},
                  {'title': 'Canción 2', 'subtitle': 'Artista B, Artista C', 'duration': 99000},
                ],
              },
            },
          },
        },
      },
    };
    final html = '<html><script id="__NEXT_DATA__" type="application/json">${jsonEncode(datos)}</script></html>';
    final l = Importar.leerSpotify(html);
    expect(l.titulo, 'Mi & lista');
    expect(l.canciones.length, 2);
    expect(l.canciones.first.duracion, 201);
    expect(l.canciones.last.busqueda, 'Artista B, Artista C Canción 2');
    expect(l.aviso, isEmpty);
  });

  test('lee Apple Music por sus datos para buscadores', () {
    final ld = {
      '@type': 'MusicPlaylist',
      'name': 'Éxitos',
      'track': [
        {'name': 'Tema', 'byArtist': {'name': 'Grupo'}, 'duration': 'PT3M25S'},
      ],
    };
    final html = '<meta property="og:title" content="Éxitos on Apple Music">'
        '<script type="application/ld+json">${jsonEncode(ld)}</script>';
    final l = Importar.leerApple(html);
    expect(l.titulo, 'Éxitos');
    expect(l.canciones.single.artista, 'Grupo');
    expect(l.canciones.single.duracion, 205);
  });

  test('elige el resultado que casa en duración', () {
    final c = CancionExterna(titulo: 'X', artista: 'Y', duracion: 200);
    final r = [
      {'tipo': 'pista', 'video_id': 'a', 'duracion': 600}, // version extendida
      {'tipo': 'pista', 'video_id': 'b', 'duracion': 202},
    ];
    expect(Importar.elegir(c, r)?['video_id'], 'b');
    expect(Importar.elegir(c, [{'tipo': 'artista'}]), isNull);
  });

  group('Google', () {
    test('la huella PKCE es la del verificador', () {
      final v = Nube.nuevoVerificador();
      expect(v.length, 64);
      final u = Nube.urlGoogle(v);
      final esperada = base64Url.encode(sha256.convert(ascii.encode(v)).bytes).replaceAll('=', '');
      expect(u.queryParameters['code_challenge'], esperada);
      expect(u.queryParameters['provider'], 'google');
      expect(u.queryParameters['redirect_to'], Nube.vueltaGoogle);
    });

    test('si se cancela en Google lo dice claro', () async {
      expect(
        () => Cuentas.conGoogle('caudal://acceso?error=access_denied&error_description=User+denied', 'v'),
        throwsA(predicate((e) => '$e'.contains('Cancelaste'))),
      );
    });
  });
}
