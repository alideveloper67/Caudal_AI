// Letras de verdad, con internet (sin red, no falla: se salta).

import 'package:caudal/nucleo/catalogo.dart';
import 'package:caudal/nucleo/elegir_letra.dart';
import 'package:caudal/nucleo/letras_cache.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> pista(String titulo, List<String> artistas, {num dur = 200, String vid = ''}) => {
      'clave': 'k|$titulo',
      'titulo': titulo,
      'artistas': [for (final a in artistas) {'nombre': a, 'id': ''}],
      'artista': artistas.join(', '),
      'duracion': dur,
      'video_id': vid,
    };

void main() {
  test('de verdad, con internet', () async {
    // (canción, tiene que llevar tiempos, una frase suya)
    final casos = [
      (pista('Tití Me Preguntó', ['Bad Bunny'], dur: 244), true, 'titi me pregunto'),
      // LRCLIB tiene una ficha de 367 s con los tiempos del disco, pero el video trae una intro: no vale
    (pista('Hello (Official Music Video)', ['Adele'], dur: 367), false, 'hello its me'),
      (pista('Adele - Hello (Official Video) [4K]', ['Canal Random'], dur: 367), false, 'hello its me'),
      (pista('Juanes - La Camisa Negra (Letra)', ['LetrasTop'], dur: 217), true, 'camisa negra'),
    ];
    for (final (p, tiempos, frase) in casos) {
      final l = await Catalogo.letras(p);
      if (l['sin_red'] == true) return;
      final texto = ElegirLetra.normalizar('${l['texto']} ${[for (final x in lineasConTiempo(l)) x.$2].join(' ')}');
      expect(texto, contains(frase), reason: '${p['titulo']}');
      expect(l['sincronizada'], tiempos, reason: '${p['titulo']}');
      if (!tiempos) expect(l['ref'], isNotEmpty, reason: 'se pondrá a tiempo por el sonido');
    }
    // ni un video cualquiera ni un nombre corriente se llevan la letra de otra canción
    for (final p in [pista('De YouTube', ['x'], dur: 19), pista('Amor', ['Banda inventada ZZ']),
        pista('Audio de WhatsApp 2024', ['Desconocido'], dur: 33)]) {
      final l = await Catalogo.letras(p);
      expect(l['texto'], '', reason: '${p['titulo']}');
      expect(lineasConTiempo(l), isEmpty, reason: '${p['titulo']}');
    }
  }, timeout: const Timeout(Duration(minutes: 3)));

  test('las de una canción de YouTube Music llevan sus propios tiempos', () async {
    final l = await Catalogo.letras(pista('Tusa', ['KAROL G'], dur: 202, vid: 'SRkr9PyBBuU'));
    if (l['sin_red'] == true) return;
    expect(l['sincronizada'], isTrue);
  }, timeout: const Timeout(Duration(minutes: 2)));

  test('otras letras para elegir', () async {
    final l = await Catalogo.letrasAlternativas(pista('Hello', ['Adele'], dur: 296));
    expect(l, isNotEmpty);
    expect(l.first['artista'].toString().toLowerCase(), contains('adele'));
  }, timeout: const Timeout(Duration(minutes: 2)));
}
