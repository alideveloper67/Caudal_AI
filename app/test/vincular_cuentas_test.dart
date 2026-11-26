// Vincular Spotify, YouTube Music y SoundCloud: el permiso, lo que se lee y los archivos.
import 'dart:convert';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:caudal/nucleo/archivo_me_gusta.dart';
import 'package:caudal/nucleo/importar.dart';
import 'package:caudal/nucleo/servicios_externos.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

http.Response _json(Object o, [int estado = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(o)), estado, headers: {'content-type': 'application/json; charset=utf-8'});

Uint8List _b(String s) => Uint8List.fromList(utf8.encode(s));

Uint8List _zip(Map<String, String> archivos) {
  final a = Archive();
  archivos.forEach((n, t) => a.addFile(ArchiveFile.bytes(n, utf8.encode(t))));
  return ZipEncoder().encodeBytes(a);
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    ServiciosExternos.olvidarConfig();
    CuentaExterna.deCaudal = 'ana';
    ServiciosExternos.pedir = (u) async =>
        _json({'spotify_client_id': 'sp', 'youtube_client_id': 'yt', 'soundcloud_client_id': 'sc'});
  });

  group('permiso', () {
    test('cada servicio pide solo leer, con PKCE, la misma vuelta y sin secreto', () async {
      for (final s in ServicioMusica.values) {
        final u = await CuentaExterna(s).empezar();
        final q = u.queryParameters;
        expect(q['redirect_uri'], 'https://caudal-musica.netlify.app/api/vincular');
        expect(q['code_challenge_method'], 'S256');
        expect(q['code_challenge'], hasLength(43));
        expect(q['state'], startsWith('a-${s.name}-'));
        expect(q.containsKey('client_secret'), isFalse);
      }
      final yt = await const CuentaExterna(ServicioMusica.youtube).empezar();
      expect(yt.queryParameters['scope'], 'https://www.googleapis.com/auth/youtube.readonly');
      expect(yt.queryParameters['access_type'], 'offline');
    });

    test('sin activar no se puede empezar', () async {
      ServiciosExternos.pedir = (u) async => _json({});
      await expectLater(const CuentaExterna(ServicioMusica.youtube).empezar(), throwsA(isA<ErrorServicio>()));
    });

    test('YouTube y SoundCloud canjean en Caudal; el permiso es de la cuenta abierta', () async {
      const c = CuentaExterna(ServicioMusica.youtube);
      final u = await c.empezar();
      Map? pedido;
      CuentaExterna.canjearEnCaudal = (url, j) async {
        expect(url.path, '/api/vincular');
        pedido = jsonDecode(j) as Map;
        return _json({'access': 'A', 'refresh': 'R', 'caduca_en': 3600});
      };
      final s = await CuentaExterna.volvio('caudal://vincular?servicio=youtube&code=X&state=${u.queryParameters['state']}');
      expect(s, ServicioMusica.youtube);
      expect(pedido!['servicio'], 'youtube');
      expect(pedido!['verificador'], hasLength(96));
      expect(await c.token(), 'A');
      CuentaExterna.deCaudal = 'beto';
      expect(await c.vinculada(), isFalse);
      expect(await c.token(), '');
    });

    test('otro estado, cancelar o cambiar de cuenta no vincula nada', () async {
      const c = CuentaExterna(ServicioMusica.spotify);
      await c.empezar();
      await expectLater(CuentaExterna.volvio('caudal://vincular?code=X&state=a-spotify-otro'), throwsA(isA<ErrorServicio>()));
      var u = await c.empezar();
      await expectLater(CuentaExterna.volvio('caudal://vincular?error=access_denied&state=${u.queryParameters['state']}'),
          throwsA(isA<ErrorServicio>().having((e) => e.mensaje, 'mensaje', contains('Cancelaste'))));
      u = await c.empezar();
      CuentaExterna.deCaudal = 'beto';
      await expectLater(CuentaExterna.volvio('caudal://vincular?code=X&state=${u.queryParameters['state']}'),
          throwsA(isA<ErrorServicio>()));
      CuentaExterna.deCaudal = 'ana';
      expect(await c.vinculada(), isFalse);
    });

    test('recargar la página de vuelta no hace nada', () async {
      expect(await CuentaExterna.volvio('caudal://vincular?code=X&state=a-spotify-loquesea'), isNull);
    });

    test('la vuelta de la web se entiende igual', () {
      final v = CuentaExterna.vueltaWeb(Uri.parse('https://x/app/?vincular=1&servicio=spotify&code=a%20b&state=w-spotify-1'));
      expect(CuentaExterna.esVuelta(v!), isTrue);
      expect(Uri.parse(v).queryParameters, {'servicio': 'spotify', 'code': 'a b', 'state': 'w-spotify-1'});
      expect(CuentaExterna.vueltaWeb(Uri.parse('https://x/app/')), isNull);
    });

    test('se renueva una sola vez aunque se pida a la vez, y si lo quitaron se desvincula', () async {
      const c = CuentaExterna(ServicioMusica.soundcloud);
      SharedPreferences.setMockInitialValues({
        'vinculada.ana.soundcloud': jsonEncode({'access': 'viejo', 'refresh': 'R1', 'caduca': 0, 'client_id': 'sc'}),
      });
      var veces = 0;
      CuentaExterna.canjearEnCaudal = (u, j) async {
        veces++;
        expect((jsonDecode(j) as Map)['refresh'], 'R1');
        return _json({'access': 'nuevo', 'refresh': 'R2', 'caduca_en': 3600});
      };
      expect(await Future.wait([c.token(), c.token()]), ['nuevo', 'nuevo']);
      expect(veces, 1);
      final p = await SharedPreferences.getInstance();
      expect(jsonDecode(p.getString('vinculada.ana.soundcloud')!)['refresh'], 'R2');

      await p.setString('vinculada.ana.soundcloud', jsonEncode({'access': '', 'refresh': 'R2', 'caduca': 0}));
      CuentaExterna.canjearEnCaudal = (u, j) async => _json({'error': 'caducado'});
      await expectLater(c.token(), throwsA(isA<PermisoCaducado>()));
      expect(await c.vinculada(), isFalse);
    });

    test('un fallo pasajero no desvincula', () async {
      const c = CuentaExterna(ServicioMusica.youtube);
      SharedPreferences.setMockInitialValues({
        'vinculada.ana.youtube': jsonEncode({'access': '', 'refresh': 'R', 'caduca': 0}),
      });
      CuentaExterna.canjearEnCaudal = (u, j) async => _json({'error': 'servicio', 'mensaje': 'luego'});
      await expectLater(c.token(), throwsA(isA<ErrorServicio>()));
      expect(await c.vinculada(), isTrue);
    });
  });

  group('leer los me gusta', () {
    void vincular(String s) => SharedPreferences.setMockInitialValues({
          'vinculada.ana.$s': jsonEncode({
            'access': 'T', 'refresh': 'R', 'caduca': DateTime.now().millisecondsSinceEpoch + 999999,
          }),
        });

    test('YouTube: todas las páginas, solo música, con su video', () async {
      vincular('youtube');
      final pedidas = <Uri>[];
      Importar.red = (u, c) async {
        pedidas.add(u);
        expect(c['Authorization'], 'Bearer T');
        Map v(String id, String t, String canal, {String cat = '10'}) => {
              'id': id, 'snippet': {'title': t, 'channelTitle': canal, 'categoryId': cat},
              'contentDetails': {'duration': 'PT3M5S'},
            };
        return u.queryParameters['pageToken'] == null
            ? _json({'nextPageToken': 'p2', 'items': [
                v('aaaaaaaaaaa', 'Monaco', 'Bad Bunny - Topic'), v('bbbbbbbbbbb', 'Receta de pan', 'Cocina', cat: '26')]})
            : _json({'items': [v('ccccccccccc', 'Karol G - Tusa (Official Video)', 'KarolGVEVO')]});
      };
      final l = await Importar.meGustaDe(ServicioMusica.youtube);
      expect(pedidas, hasLength(2));
      expect([for (final c in l.canciones) '${c.artista}|${c.titulo}|${c.duracion}'], ['Bad Bunny|Monaco|185', 'Karol G|Tusa|185']);
      expect(l.canciones.first.claveExterna, 'yt:aaaaaaaaaaa');
      expect(l.canciones.first.pista!['video_id'], 'aaaaaaaaaaa');
      expect(l.meGusta, isTrue);
    });

    test('SoundCloud: pagina solo dentro de su API', () async {
      vincular('soundcloud');
      var n = 0;
      Importar.red = (u, c) async {
        expect(u.host, 'api.soundcloud.com');
        expect(c['Authorization'], 'OAuth T');
        n++;
        return _json({
          'collection': [{'title': 'Tema $n', 'user': {'username': 'DJ'}, 'duration': 61000}],
          'next_href': n == 1 ? 'https://api.soundcloud.com/me/likes/tracks?cursor=2' : 'https://malo.example/x',
        });
      };
      final l = await Importar.meGustaDe(ServicioMusica.soundcloud);
      expect([for (final c in l.canciones) c.titulo], ['Tema 1', 'Tema 2']);
    });

    test('sin vincular lo dice', () async {
      await expectLater(Importar.meGustaDe(ServicioMusica.spotify),
          throwsA(isA<ErrorImportar>().having((e) => e.mensaje, 'mensaje', contains('Vincula tu cuenta'))));
    });

    test('la clave externa no cambia al emparejarla ni al guardarla', () {
      final c = CancionExterna(titulo: 'Tusa', artista: 'Karol G');
      final antes = c.claveExterna;
      c.pista = {'clave': 'yt:zzzzzzzzzzz'};
      expect(c.claveExterna, antes);
      expect(CancionExterna.deJson(jsonDecode(jsonEncode(c.aJson())) as Map).claveExterna, antes);
      final v = CancionExterna.deJson(jsonDecode(jsonEncode(CancionExterna(titulo: '', videoId: 'abcdefghijk').aJson())) as Map);
      expect(v.videoId, 'abcdefghijk');
    });
  });

  group('archivos', () {
    const biblioteca = '{"tracks":[{"artist":"Feid","album":"X","track":"Normal","uri":"spotify:track:1"},'
        '{"artist":"Feid","album":"X","track":"Normal","uri":"spotify:track:1"},{"artist":"Rosalía","track":"Malamente"}],"albums":[]}';

    test('el .json y el .zip de Spotify, sin repetidas', () {
      for (final l in [
        ArchivoMeGusta.leer('YourLibrary.json', _b(biblioteca)),
        ArchivoMeGusta.leer('my_spotify_data.zip',
            _zip({'Spotify Account Data/YourLibrary.json': biblioteca, 'Spotify Account Data/Playlist1.json': '{"playlists":[]}'})),
      ]) {
        expect(l.plataforma, 'Spotify');
        expect([for (final c in l.canciones) c.nombre], ['Feid - Normal', 'Rosalía - Malamente']);
      }
    });

    test('el .zip de Google Takeout: solo la lista de me gusta, por id de video', () {
      final l = ArchivoMeGusta.leer('takeout-2026.zip', _zip({
        'Takeout/YouTube y YouTube Music/listas de reproducción/Videos que me gustan-videos.csv':
            'ID del video,Marca de tiempo de creación del video de la lista\naaaaaaaaaaa,2026-01-01T00:00:00+00:00\nbbbbbbbbbbb,2026\n',
        'Takeout/YouTube y YouTube Music/listas de reproducción/Ver más tarde-videos.csv': 'ID del video,Marca\nccccccccccc,2026\n',
      }));
      expect([for (final c in l.canciones) c.videoId], ['aaaaaaaaaaa', 'bbbbbbbbbbb']);
    });

    test('la biblioteca de YouTube Music trae título y artistas', () {
      final l = ArchivoMeGusta.leer('music library songs.csv',
          _b('Video ID,Song Title,Album Title,Artist Name 1,Artist Name 2\naaaaaaaaaaa,"Hola, mundo",Disco,Ana,Beto\n'));
      expect(l.canciones.single.titulo, 'Hola, mundo');
      expect(l.canciones.single.artista, 'Ana, Beto');
      expect(l.canciones.single.videoId, 'aaaaaaaaaaa');
    });

    test('Exportify, punto y coma con BOM, UTF-16 y comillas con saltos', () {
      final a = ArchivoMeGusta.leer('liked.csv', _b('﻿"Track URI","Track Name","Artist Name(s)","Track Duration (ms)"\n'
          '"spotify:track:1","Dijo ""sí""\nluego","A;B","200000"\n'));
      expect(a.canciones.single.titulo, 'Dijo "sí"\nluego');
      expect(a.canciones.single.artista, 'A, B');
      expect(a.canciones.single.duracion, 200);
      final b = ArchivoMeGusta.leer('x.csv', _b('Título;Artista;Duración\nAmor;Los Ángeles;3:05\n'));
      expect(b.canciones.single.nombre, 'Los Ángeles - Amor');
      expect(b.canciones.single.duracion, 185);
      final u16 = BytesBuilder()..add([0xFF, 0xFE]);
      for (final c in 'Title\tArtist\nÑandú\tMía\n'.codeUnits) {
        u16.add([c & 255, c >> 8]);
      }
      expect(ArchivoMeGusta.leer('x.tsv', u16.toBytes()).canciones.single.nombre, 'Mía - Ñandú');
    });

    test('texto: una por línea', () {
      final l = ArchivoMeGusta.leer('lista.txt', _b('1. Bad Bunny - Monaco\r\n\r\nKarol G - Tusa (Official Video)\r\n'));
      expect([for (final c in l.canciones) c.nombre], ['Bad Bunny - Monaco', 'Karol G - Tusa']);
    });

    test('lo que no sirve lo dice claro', () {
      for (final (n, b) in [
        ('vacio.csv', _b('')),
        ('otro.json', _b('{"hola":1}')),
        ('roto.json', _b('{"tracks":[')),
        ('roto.zip', Uint8List.fromList([0x50, 0x4B, 3, 4, 9, 9, 9, 9, 9])),
        ('takeout.zip', _zip({'a/Suscripciones.csv': 'x,y\n1,2\n', 'a/Rock-videos.csv': 'Video ID,T\naaaaaaaaaaa,1\n'})),
        ('enorme.zip', Uint8List(ArchivoMeGusta.maxArchivo + 1)),
      ]) {
        expect(() => ArchivoMeGusta.leer(n, b), throwsA(isA<ErrorImportar>()), reason: n);
      }
    });

    test('un .zip que se infla de más no se abre', () {
      final l = List.filled(ArchivoMeGusta.maxDentro + 10, 32);
      final a = Archive()..addFile(ArchiveFile.bytes('YourLibrary.json', l));
      final z = ZipEncoder().encodeBytes(a);
      expect(z.length, lessThan(1 << 20));
      expect(() => ArchivoMeGusta.leer('b.zip', z), throwsA(isA<ErrorImportar>()));
    });
  });
}
