import 'dart:convert';

import 'package:caudal/nucleo/musica_libre.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> _t(String id, {Map<String, dynamic> mas = const {}}) => {
      'id': id, 'title': 'Tema $id', 'duration': 100, 'genre': 'Latin', 'is_streamable': true,
      'permalink': '/ana/tema-$id', 'user': {'id': 'U1', 'name': 'Ana'},
      'artwork': {'480x480': 'https://x/$id.jpg'}, 'access': {'stream': true}, ...mas,
    };

void main() {
  final pedidas = <Uri>[];
  var respuesta = <Map<String, dynamic>>[];
  setUp(() {
    pedidas.clear();
    MusicaLibre.pedir = (u) async {
      pedidas.add(u);
      return jsonEncode({'data': respuesta});
    };
  });

  test('solo entran las que el artista deja sonar en otras apps', () {
    expect(MusicaLibre.permitida(_t('a')), isTrue);
    for (final no in [
      {'is_streamable': false}, {'is_stream_gated': true}, {'is_delete': true}, {'is_unlisted': true},
      {'is_available': false}, {'allowed_api_keys': ['otra']}, {'access_authorities': ['0x1']},
      {'access': {'stream': false}}, {'id': ''},
    ]) {
      expect(MusicaLibre.permitida(_t('a', mas: no)), isFalse, reason: '$no');
    }
  });

  test('la pista suena sin YouTube, cita al artista y enlaza a Audius', () {
    final p = MusicaLibre.comoPista(_t('a'));
    expect(p['video_id'], '');
    expect(p['archivo'], contains('/tracks/a/stream'));
    expect(p['url_directa'], p['archivo']);
    expect((p['artista'], p['enlace']), ('Ana', 'https://audius.co/ana/tema-a'));
    expect(suenaBloqueada(p), isTrue);
    expect(suenaBloqueada({'video_id': 'x'}), isFalse);
    // guardada en una lista pierde «archivo», pero sigue sonando
    expect(suenaBloqueada({'url_directa': p['url_directa']}), isTrue);
  });

  test('la búsqueda va bien escrita y filtra', () async {
    respuesta = [_t('a'), _t('b', mas: {'is_stream_gated': true})];
    final l = await MusicaLibre.buscar('  años & más ');
    expect(l.map((p) => p['clave']), ['aud:a']);
    expect(pedidas.single.queryParameters['query'], 'años & más');
    expect(pedidas.single.queryParameters['app_name'], 'Caudal');
    expect(await MusicaLibre.buscar('   '), isEmpty);
    expect(pedidas, hasLength(1));
  });

  test('las parecidas no se repiten ni traen lo ya oído, y un fallo no rompe', () async {
    respuesta = [for (var i = 0; i < 12; i++) _t('p$i')];
    final l = await MusicaLibre.parecidas(MusicaLibre.comoPista(_t('p0')), sin: {'aud:p1'});
    final claves = [for (final p in l) p['clave']];
    expect(claves.toSet().length, claves.length);
    expect(claves, isNot(contains('aud:p0')));
    expect(claves, isNot(contains('aud:p1')));
    expect(claves, hasLength(10));
    MusicaLibre.pedir = (_) async => throw Exception('sin red');
    expect(await MusicaLibre.parecidas({'clave': 'aud:z', 'audius_genero': 'Jazz', 'audius_usuario': 'U9'}), isEmpty);
  });
}
