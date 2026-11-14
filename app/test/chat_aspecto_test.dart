import 'package:caudal/nucleo/chat.dart';
import 'package:caudal/nucleo/importar_archivos.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('chat', () {
    test('una canción guardada en la nube vuelve a poder sonar', () {
      final p = Chat.pistaJugable({'clave': 'yt:dQw4w9WgXcQ', 'titulo': 'X'});
      expect(p['video_id'], 'dQw4w9WgXcQ');
      expect(p['tipo'], 'pista');
      expect('${p['miniatura']}', contains('dQw4w9WgXcQ'));
    });

    test('vista previa de la conversación', () {
      final yo = 'yo';
      final c = ResumenChat.desde({
        'id': '1', 'otro': '2', 'usuario': 'beto', 'nombre': '', 'ultimo': '2026-11-14T10:00:00Z',
        'ultimo_texto': '', 'ultimo_pista': {'titulo': 'Tema'}, 'ultimo_autor': 'yo', 'sin_leer': 0,
      }, yo);
      expect(c.vistaPrevia, 'Tú: ♪ Tema');
      expect(c.visible, 'beto');
      expect(c.inicial, 'B');
      final vacio = ResumenChat.desde({'id': '1', 'otro': '2', 'usuario': 'ana', 'nombre': 'Ana',
        'ultimo': '2026-11-14T10:00:00Z'}, yo);
      expect(vacio.vistaPrevia, contains('hola'));
    });

    test('la mezcla empieza por lo común y alterna, sin repetir', () {
      final m = Chat.mixDeMezcla({
        'afinidad': 53,
        'comunes': [{'clave': 'yt:comun000001', 'titulo': 'C'}],
        'mezcla': [
          {'clave': 'yt:aaaaaaaaaa1', 'titulo': 'A'},
          {'clave': 'yt:bbbbbbbbbb1', 'titulo': 'B'},
          {'clave': 'yt:comun000001', 'titulo': 'C otra vez'},
        ],
        'artistas_comunes': ['Bad Bunny'],
      }, 'Beto', 'chat1');
      final ids = (m['pistas'] as List).map((p) => p['video_id']).toList();
      expect(ids, ['comun000001', 'aaaaaaaaaa1', 'bbbbbbbbbb1']);
      expect(m['titulo'], 'Tu mezcla con Beto');
      expect(m['subtitulo'], contains('53 %'));
      expect(m['subtitulo'], contains('Bad Bunny'));
    });
  });

  test('nombre de archivo "Artista - Título"', () {
    expect(ImportarArchivos.separarNombre('Bad Bunny - Tití Me Preguntó'), ('Bad Bunny', 'Tití Me Preguntó'));
    expect(ImportarArchivos.separarNombre('cancion_sin_artista'), ('', 'cancion sin artista'));
  });

  test('el aspecto cambia los colores y vuelve al de siempre', () {
    Aspecto.aplicar('rosa', 'negro');
    expect(C.acento, const Color(0xFFFF5C8A));
    expect(C.fondo, const Color(0xFF000000));
    Aspecto.aplicar('no-existe', 'tampoco');
    expect(C.acento, const Color(0xFF22D3EE));
    expect(C.fondo, const Color(0xFF06070A));
  });
}
