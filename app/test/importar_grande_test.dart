// Traer listas enormes y me gusta de otras apps, sin red: paginación sin tope
// (respuestas simuladas de más de 5000), Spotify con sus reglas de 2026, SoundCloud
// con páginas guardadas, emparejado en lotes reanudable y me gusta sin duplicados.
@Timeout(Duration(minutes: 5))
library;

import 'dart:convert';

import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/huella_cancion.dart';
import 'package:caudal/nucleo/importacion.dart';
import 'package:caudal/nucleo/importar.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/servicios_externos.dart';
import 'package:caudal/nucleo/sincronizacion.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

http.Response _json(Object d, [int estado = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(d)), estado, headers: {'content-type': 'application/json'});

Map<String, dynamic> _pista(String vid, String titulo, [String artista = 'Grupo']) => {
      'tipo': 'pista', 'clave': 'yt:$vid', 'video_id': vid, 'titulo': titulo, 'artista': artista,
      'artistas': [{'nombre': artista, 'id': ''}],
    };

String _embed(int n) => '<html><script id="__NEXT_DATA__" type="application/json">${jsonEncode({
      'props': {'pageProps': {'state': {'data': {'entity': {
        'name': 'Enorme', 'subtitle': 'Ana',
        'trackList': [for (var i = 0; i < n; i++) {'title': 'T$i', 'subtitle': 'A', 'duration': 1000}],
      }}}}}
    })}</script></html>';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Future<http.Response> Function(Uri, Map<String, String>) redOriginal;
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    redOriginal = Importar.red;
    Importar.dormir = (_) async {};
  });
  tearDown(() => Importar.red = redOriginal);

  group('paginar', () {
    test('no tiene tope de canciones', () async {
      final todas = await Importar.paginar<int>((cursor) async {
        final n = (cursor as int?) ?? 0;
        return ([for (var i = 0; i < 50; i++) n * 50 + i], n + 1 < 130 ? n + 1 : null);
      });
      expect(todas.length, 6500); // antes los topes cortaban en 5000 o menos
      expect(todas.last, 6499);
    });

    test('se corta si el servicio repite su cursor', () async {
      var vueltas = 0;
      final r = await Importar.paginar<int>((c) async {
        vueltas++;
        return ([1], 'igual');
      });
      expect((r.length, vueltas), (2, 2));
    });
  });

  group('Spotify', () {
    test('con un token: una lista de 7 321 llega entera (items, de 50 en 50)', () async {
      Importar.red = (u, c) async {
        expect(c['Authorization'], 'Bearer tk');
        if (u.path.endsWith('/playlists/L1')) return _json({'name': 'Enorme', 'owner': {'display_name': 'Ana'}});
        final desde = int.tryParse(u.queryParameters['offset'] ?? '') ?? 0;
        final items = [
          for (var i = desde; i < desde + 50 && i < 7321; i++)
            {'item': {'type': 'track', 'name': 'Tema $i', 'duration_ms': 200000, 'artists': [{'name': 'Grupo'}]}}
        ];
        final sig = desde + 50 < 7321 ? 'https://api.spotify.com/v1/playlists/L1/items?limit=50&offset=${desde + 50}' : null;
        return _json({'items': items, 'next': sig});
      };
      final l = await Importar.spotifyApi('playlist', 'L1', 'tk');
      expect(l.canciones.length, 7321);
      expect(l.canciones.first.duracion, 200);
      expect(l.autor, 'Ana');
    });

    test('sin conexión configurada: las 50 de la página y dice qué falta', () async {
      Importar.red = (u, c) async {
        if (u.host == 'caudal-musica.netlify.app') return http.Response('<html>Page not found</html>', 404);
        if (u.host == 'open.spotify.com') return http.Response.bytes(utf8.encode(_embed(50)), 200);
        fail('no debería pedir $u');
      };
      final l = await Importar.leer('https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M');
      expect(l.canciones.length, 50);
      expect(l.completa, isFalse);
      expect(l.aviso, Importar.avisoSpotifySinConexion);
    });

    test('lista ajena (reglas de 2026): lo explica y trae las 50 de la página', () async {
      Importar.red = (u, c) async {
        if (u.path == '/api/spotify') return _json({'error': 'lista_ajena'});
        if (u.host == 'open.spotify.com') return http.Response.bytes(utf8.encode(_embed(50)), 200);
        fail('no debería pedir $u');
      };
      final l = await Importar.leer('https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M');
      expect(l.aviso, Importar.avisoSpotifyAjena);
    });

    test('por la función de Caudal se siguen los trozos hasta el final', () async {
      Importar.red = (u, c) async {
        final desde = int.parse(u.queryParameters['desde']!);
        return _json({
          'titulo': 'Grande', 'autor': 'Ana',
          'canciones': [for (var i = desde; i < desde + 1000 && i < 5500; i++) {'titulo': 'T$i', 'artista': 'A', 'duracion': 1}],
          'siguiente': desde + 1000 < 5500 ? desde + 1000 : null,
        });
      };
      final l = await Importar.leer('https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M');
      expect(l.canciones.length, 5500);
      expect(l.titulo, 'Grande');
      expect(l.completa, isTrue);
    });

    test('PKCE: la huella es la del verificador y pide solo leer', () {
      final v = CuentaSpotify.nuevoVerificador();
      expect(v.length, 96);
      final u = CuentaSpotify.urlAutorizar('cid', v, 'est');
      expect(u.queryParameters['code_challenge_method'], 'S256');
      expect(u.queryParameters['redirect_uri'], 'caudal://spotify');
      expect(u.queryParameters['scope'], contains('user-library-read'));
      expect(u.queryParameters.containsKey('client_secret'), isFalse);
    });

    test('PKCE: la vuelta canjea el código sin secreto y guarda la sesión', () async {
      ServiciosExternos.pedir = (u) async => _json({'spotify_client_id': 'cid'});
      ServiciosExternos.olvidarConfig();
      final url = await CuentaSpotify.empezar();
      Map<String, String>? cuerpo;
      CuentaSpotify.canjear = (u, c) async {
        cuerpo = c;
        return _json({'access_token': 'A', 'refresh_token': 'R', 'expires_in': 3600});
      };
      await CuentaSpotify.volvio('caudal://spotify?code=XYZ&state=${url.queryParameters['state']}');
      expect(cuerpo!['code_verifier'], isNotEmpty);
      expect(cuerpo!.containsKey('client_secret'), isFalse);
      expect(await CuentaSpotify.conectada(), isTrue);
      expect(await CuentaSpotify.token(), 'A');
    });

    test('PKCE: si el estado no coincide no se conecta', () async {
      ServiciosExternos.pedir = (u) async => _json({'spotify_client_id': 'cid'});
      ServiciosExternos.olvidarConfig();
      await CuentaSpotify.empezar();
      expect(() => CuentaSpotify.volvio('caudal://spotify?code=XYZ&state=otro'), throwsA(isA<ErrorServicio>()));
    });
  });

  group('SoundCloud', () {
    test('reconoce sus enlaces', () {
      expect(Importar.plataforma('https://soundcloud.com/ana/sets/verano'), 'soundcloud');
      expect(Importar.tipoSoundcloud('https://soundcloud.com/ana/sets/verano?si=1').$1, 'lista');
      expect(Importar.tipoSoundcloud('https://soundcloud.com/ana/likes'), ('me_gusta', 'ana'));
      expect(Importar.tipoSoundcloud('https://soundcloud.com/ana').$1, 'perfil');
      expect(Importar.tipoSoundcloud('https://soundcloud.com/discover').$1, '');
    });

    test('me gusta de un perfil por la función: 5 432 llegan enteros', () async {
      Importar.red = (u, c) async {
        final cursor = int.tryParse(u.queryParameters['cursor']?.split('offset=').last ?? '') ?? 0;
        final sig = cursor + 200 < 5432
            ? 'https://api.soundcloud.com/users/1/likes/tracks?linked_partitioning=true&offset=${cursor + 200}'
            : null;
        return _json({
          'titulo': 'Me gusta de ana', 'me_gusta': true,
          'canciones': [for (var i = cursor; i < cursor + 200 && i < 5432; i++) {'titulo': 'T$i', 'artista': 'A', 'duracion': 1}],
          'siguiente': sig,
        });
      };
      final l = await Importar.leer('https://soundcloud.com/ana/likes');
      expect(l.canciones.length, 5432);
      expect(l.meGusta, isTrue);
    });

    final pagina = '<html><script>window.__sc_hydration = ${jsonEncode([
      {'hydratable': 'apiClient', 'data': {'id': 'NO-SE-USA'}},
      {'hydratable': 'playlist', 'data': {
        'title': 'Chill', 'track_count': 48, 'user': {'username': 'chillhop'},
        'tracks': [
          for (var i = 0; i < 5; i++) {'id': i, 'title': 'Artista $i - Tema $i', 'duration': 120000, 'user': {'username': 'chillhop'}},
          for (var i = 0; i < 43; i++) {'id': 100 + i, 'kind': 'track'},
        ],
      }},
    ])};</script></html>';

    test('página pública: trae lo que enseña y lo dice', () async {
      final (l, total) = Importar.leerSoundcloudPagina(pagina);
      expect((l.canciones.length, total), (5, 48));
      expect(l.canciones.first.artista, 'Artista 0');
      Importar.red = (u, c) async {
        if (u.host == 'caudal-musica.netlify.app') return _json({'error': 'sin_credenciales'});
        return http.Response.bytes(utf8.encode(pagina), 200);
      };
      final l2 = await Importar.leer('https://soundcloud.com/chillhop/sets/chill');
      expect(l2.completa, isFalse);
      expect(l2.aviso, contains('5 de sus 48'));
      expect(() => Importar.leer('https://soundcloud.com/chillhop/likes'), throwsA(isA<ErrorImportar>()));
    });
  });

  test('los me gusta de YouTube explican cómo pasarlos', () {
    expect(() => Importar.leer('https://music.youtube.com/playlist?list=LM'),
        throwsA(predicate((e) => '$e'.contains('Agregar a playlist'))));
  });

  group('emparejar', () {
    List<CancionExterna> canciones(int n) =>
        [for (var i = 0; i < n; i++) CancionExterna(titulo: 'Tema $i', artista: 'Grupo', duracion: 200)];

    test('en lotes, en orden, con avance y pocas búsquedas a la vez', () async {
      var activas = 0, maximo = 0;
      final lotes = <int>[];
      final claves = <String>[];
      var ultimo = (0, 0);
      final r = await Importar.emparejar(canciones(5300),
          lote: 50,
          hilos: 4,
          buscarPista: (c) async {
            activas++;
            if (activas > maximo) maximo = activas;
            await Future<void>.delayed(Duration.zero);
            activas--;
            final n = int.parse(c.titulo.split(' ')[1]);
            return n % 10 == 0 ? null : _pista(n.toString().padLeft(11, '0'), c.titulo);
          },
          alAvanzar: (h, t) => ultimo = (h, t),
          alLote: (fin, pistas, sin) async {
            lotes.add(fin);
            claves.addAll(pistas.map((p) => '${p['clave']}'));
          });
      expect((r.hechas, r.encontradas, r.noEncontradas.length), (5300, 4770, 530));
      expect(lotes.length, 106);
      expect(claves, [...claves]..sort());
      expect(ultimo, (5300, 5300));
      expect(maximo, lessThanOrEqualTo(4));
    });

    test('se puede pausar y seguir donde quedó', () async {
      var parar = false;
      final hechos = <int>[];
      final r = await Importar.emparejar(canciones(1000),
          lote: 100,
          buscarPista: (c) async => _pista('x', c.titulo),
          cancelado: () => parar,
          alLote: (fin, p, s) async {
            hechos.add(fin);
            if (fin >= 200) parar = true;
          });
      expect(r.cancelado, isTrue);
      expect(hechos, [100, 200]);
      final resto = <int>[];
      await Importar.emparejar(canciones(1000),
          desde: 200, lote: 100, buscarPista: (c) async => _pista('x', c.titulo), alLote: (f, p, s) async => resto.add(f));
      expect((resto.first, resto.last), (300, 1000));
    });

    test('un fallo de red se reintenta y no cuenta como no encontrada', () async {
      var intentos = 0;
      final p = await Importar.resolverUna(CancionExterna(titulo: 'T', artista: 'A', duracion: 200), buscar: (q) async {
        if (++intentos < 3) throw Exception('sin red');
        return [{'tipo': 'pista', 'video_id': 'abcdefghijk', 'duracion': 201}];
      });
      expect(p?['video_id'], 'abcdefghijk');
      expect(intentos, 3);
    });

    test('el avance se escribe como en español', () {
      expect(textoAvance(1240, 5300), '1 240 de 5 300');
    });
  });

  group('me gusta sin duplicados', () {
    late Coleccion col;
    setUp(() async {
      col = await Coleccion.abrirEn(inMemoryDatabasePath);
      col.alHaberPendientes = () {};
    });
    tearDown(() => col.cerrar());

    test('huella: la misma canción con otro video se reconoce', () {
      expect(huellaCancion('Tusa (Official Video)', 'Karol G, Nicki Minaj'), huellaCancion('tusa', 'KAROL G'));
      expect(huellaCancion('Canción', 'Ñu'), huellaCancion('cancion', 'nu'));
    });

    test('fusión: ni las que ya estaban ni las repetidas, y en orden', () async {
      await col.alternarMeGusta(_pista('aaaaaaaaaaa', 'Ya me gustaba'));
      await col.db.delete('pendientes');
      final traidas = [
        _pista('bbbbbbbbbbb', 'Nueva 1'),
        _pista('aaaaaaaaaaa', 'Ya me gustaba'),
        _pista('ccccccccccc', 'Ya me gustaba (Official Video)'),
        _pista('ddddddddddd', 'Nueva 2'),
        _pista('bbbbbbbbbbb', 'Nueva 1'),
      ];
      expect(await col.agregarMeGustaVarios(traidas), (2, 3));
      expect(col.totalMeGusta, 3);
      final orden = [for (final p in await col.listaMeGusta()) p['titulo']];
      expect(orden.indexOf('Nueva 1'), lessThan(orden.indexOf('Nueva 2')));
      expect(await col.agregarMeGustaVarios(traidas), (0, 5)); // volver a sincronizar no añade nada
    });

    test('suben a la nube de 400 en 400', () async {
      await col.agregarMeGustaVarios([for (var i = 0; i < 1000; i++) _pista(i.toString().padLeft(11, '0'), 'T$i')]);
      final ops = await col.db.query('pendientes', orderBy: 'id');
      expect(ops.map((o) => o['op']).toSet(), {'me_gusta_varios'});
      expect([for (final o in ops) ((jsonDecode('${o['datos']}') as Map)['items'] as List).length], [400, 400, 200]);
    });

    test('una lista enorme va a la nube por trozos', () async {
      final id = await col.crearLista('Enorme');
      await col.db.delete('pendientes');
      await col.agregarALista(id, [for (var i = 0; i < 5300; i++) _pista(i.toString().padLeft(11, '0'), 'T$i')]);
      final tam = [
        for (final o in await col.db.query('pendientes', where: "op = 'items_poner'"))
          ((jsonDecode('${o['datos']}') as Map)['items'] as List).length
      ];
      expect(tam.fold<int>(0, (a, b) => a + b), 5300);
      expect(tam.reduce((a, b) => a > b ? a : b), 400);
      expect((await col.pistasDeLista(id)).length, 5300);
    });

    test('la orden me_gusta_varios llega a la nube con su fecha', () async {
      final nube = _NubeAnota();
      final s = Sincronizador(col, nube);
      await col.guardarEstado('nube_usuario', 'u1'); // sin la subida inicial: solo las órdenes
      await col.agregarMeGustaVarios([_pista('aaaaaaaaaaa', 'Uno'), _pista('bbbbbbbbbbb', 'Dos')]);
      await s.cicloParaPruebas(traer: false);
      final post = nube.posts.firstWhere((p) => p.$1.startsWith('me_gusta?on_conflict=user_id,clave'));
      final filas = post.$2 as List;
      expect(filas.map((f) => f['clave']), ['yt:aaaaaaaaaaa', 'yt:bbbbbbbbbbb']);
      expect('${filas.first['fecha']}', contains('T'));
    });

    test('la importación entera: lista nueva, reanudable y con resumen', () async {
      final t = TrabajoImportacion.i;
      t.buscarPista = (c) async => c.titulo.endsWith('7') ? null : _pista(c.titulo.padLeft(11, '0'), c.titulo);
      final l = ListaExterna(plataforma: 'Spotify', titulo: 'Grande',
          canciones: [for (var i = 0; i < 230; i++) CancionExterna(titulo: '$i', artista: 'A')]);
      await t.empezar(col, l, meGusta: false);
      while (t.enMarcha) {
        await Future<void>.delayed(const Duration(milliseconds: 10));
      }
      expect(t.terminado, isTrue);
      expect((await col.pistasDeLista(t.listaId!)).length, 207);
      expect(t.noEncontradas.length, 23);
      expect(t.resumen(), 'Lista «Grande» creada con 207 canciones. 23 no se encontraron.');
      expect(await TrabajoImportacion.pendiente(col), isNull);
      t.olvidarTerminado();
      t.buscarPista = null;
    });

    test('a me gusta: anota la fuente para volver a sincronizar', () async {
      final t = TrabajoImportacion.i;
      t.buscarPista = (c) async => _pista(c.titulo.padLeft(11, '0'), 'Tema ${c.titulo}');
      final l = ListaExterna(plataforma: 'SoundCloud', titulo: 'Me gusta de ana', meGusta: true,
          canciones: [for (var i = 0; i < 60; i++) CancionExterna(titulo: '$i')]);
      await t.empezar(col, l, meGusta: true, enlace: 'https://soundcloud.com/ana/likes');
      while (t.enMarcha) {
        await Future<void>.delayed(const Duration(milliseconds: 10));
      }
      expect(t.anadidas, 60);
      expect(col.totalMeGusta, 60);
      final f = await TrabajoImportacion.fuentes(col);
      expect(f.single['enlace'], 'https://soundcloud.com/ana/likes');
      t.olvidarTerminado();
      t.buscarPista = null;
    });
  });
}

class _NubeAnota extends Sesion {
  _NubeAnota() : super('u1', 'a', 'r', DateTime.now().add(const Duration(hours: 1)));
  final posts = <(String, Object?)>[];

  @override
  Future<dynamic> pedir(String metodo, String ruta, {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    if (metodo == 'POST') posts.add((ruta, cuerpo));
    return metodo == 'GET' ? [] : null;
  }
}
