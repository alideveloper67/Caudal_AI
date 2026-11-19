import 'dart:convert';
import 'dart:io';

import 'package:caudal/nucleo/catalogo.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// YouTube a veces contesta "bien" pero sin la cola de la radio a ciertas conexiones (y la
/// función de Caudal tampoco la consigue). La radio no debe morir con «¿lista privada?»:
/// suena con canciones de ese artista.
void main() {
  final busqueda = File('test/datos/busqueda_canciones_shakira.json').readAsStringSync();
  late List<String> pedidos;

  setUp(() => pedidos = []);
  tearDown(() => Catalogo.clientePruebas = null);

  MockClient cliente({bool buscarFalla = false}) => MockClient((r) async {
        pedidos.add(r.url.toString());
        final metodo = r.url.queryParameters['m'] ?? r.url.pathSegments.last;
        if (metodo == 'search') {
          if (buscarFalla) return http.Response('{"error":{"message":"no"}}', 500);
          return http.Response.bytes(utf8.encode(busqueda), 200, headers: {'content-type': 'application/json'});
        }
        // next y browse: respuesta vacía, sin cola (lo que ve el teléfono afectado)
        return http.Response('{"contents":{}}', 200, headers: {'content-type': 'application/json'});
      });

  test('una emisora sin cola suena con canciones del artista', () async {
    Catalogo.clientePruebas = cliente();
    final r = await Catalogo.radio(playlistId: 'RDEM4s6ouTwHMSllkl-X-LBTQQ', limite: 20, respaldo: 'Shakira');
    final pistas = r['pistas'] as List;
    expect(pistas, isNotEmpty);
    expect(pistas.length, lessThanOrEqualTo(20));
    expect(pistas.every((p) => '${(p as Map)['video_id']}'.isNotEmpty), isTrue);
    // antes de rendirse sí probó la vía de la función de Caudal
    expect(pedidos.any((u) => u.contains('/api/yt')), isTrue);
  });

  test('la radio de una canción sin cola no repite la canción de partida', () async {
    Catalogo.clientePruebas = cliente();
    final r = await Catalogo.radio(videoId: 'abcdefghijk', limite: 10, respaldo: 'Shakira');
    final pistas = r['pistas'] as List;
    expect(pistas, isNotEmpty);
    expect(pistas.any((p) => (p as Map)['video_id'] == 'abcdefghijk'), isFalse);
  });

  test('sin respaldo, el mensaje ya no habla de listas privadas', () async {
    Catalogo.clientePruebas = cliente();
    await expectLater(
      Catalogo.radio(playlistId: 'RDEM4s6ouTwHMSllkl-X-LBTQQ', limite: 10),
      throwsA(isA<CatalogoError>().having((e) => e.mensaje, 'mensaje', allOf(isNot(contains('privada')), contains('Inténtalo')))),
    );
  });

  test('si también falla la búsqueda, avisa claro', () async {
    Catalogo.clientePruebas = cliente(buscarFalla: true);
    await expectLater(
      Catalogo.radio(playlistId: 'RDEM4s6ouTwHMSllkl-X-LBTQQ', limite: 10, respaldo: 'Shakira'),
      throwsA(isA<CatalogoError>().having((e) => e.mensaje, 'mensaje', isNot(contains('privada')))),
    );
  });
}
