// Que la letra sea la de la canción, vaya a tiempo y se vea en todos los diseños.

import 'dart:io';

import 'package:caudal/nucleo/catalogo.dart';
import 'package:caudal/nucleo/cosmeticos.dart';
import 'package:caudal/nucleo/donadores_extra.dart';
import 'package:caudal/nucleo/elegir_letra.dart';
import 'package:caudal/nucleo/letra_bloqueo.dart';
import 'package:caudal/nucleo/letras_cache.dart';
import 'package:caudal/ui/premium/letra_escena.dart';
import 'package:caudal/ui/reproductor/letra_aspecto.dart';
import 'package:caudal/ui/reproductor/letra_correccion.dart';
import 'package:caudal/ui/reproductor/letra_disenos.dart';
import 'package:caudal/ui/reproductor/paleta_portada.dart';
import 'package:caudal/ui/reproductor/selector_letra.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> pista(String titulo, List<String> artistas, {num dur = 200, String vid = ''}) => {
      'clave': 'k|$titulo',
      'titulo': titulo,
      'artistas': [for (final a in artistas) {'nombre': a, 'id': ''}],
      'artista': artistas.join(', '),
      'duracion': dur,
      'video_id': vid,
    };

Map<String, dynamic> ficha(String titulo, String artista,
        {num dur = 200, bool sinc = true, String texto = 'una letra cualquiera', bool instrumental = false}) =>
    {
      'id': '$titulo$artista$dur$sinc$texto', 'trackName': titulo, 'artistName': artista, 'duration': dur,
      'plainLyrics': texto, 'syncedLyrics': sinc ? '[00:01.00] $texto' : null, 'instrumental': instrumental,
    };

void main() {
  group('la letra es la de la canción', () {
    test('el título sin adornos', () {
      const casos = {
        'Hello (Official Music Video)': 'Hello',
        'Adele - Hello (Official Video) [4K]': 'Adele - Hello',
        'Gasolina (feat. Glory)': 'Gasolina',
        '01 La Flaca': 'La Flaca',
        '24 horas': '24 horas',
        '7 rings': '7 rings',
        'La Camisa Negra (Full Phatt Remix)': 'La Camisa Negra (Full Phatt Remix)',
        'Flaca | Andrés Calamaro | Video Oficial': 'Flaca',
      };
      casos.forEach((crudo, limpio) => expect(ElegirLetra.tituloLimpio(crudo), limpio));
    });

    test('título, artista y versión', () {
      final casos = <(Map<String, dynamic>, Map<String, dynamic>, bool)>[
        (pista('Hello', ['Adele']), ficha('Hello', 'Adele'), true),
        (pista('Hello', ['Adele']), ficha('Hello', 'Lionel Richie'), false),
        (pista('Hello', ['Adele']), ficha('Hello, Goodbye', 'Adele'), false),
        (pista('Tití Me Preguntó', ['Bad Bunny']), ficha('Titi Me Pregunto', 'Bad Bunny'), true),
        (pista('Eres', ['Café Tacvba']), ficha('Eres', 'Cafe Tacuba'), true),
        (pista('Lágrimas', ['Grupo Néctar']), ficha('Lágrimas', 'Néctar'), true),
        (pista('Despacito', ['Luis Fonsi', 'Daddy Yankee']), ficha('Despacito', 'Luis Fonsi feat. Daddy Yankee'), true),
        (pista('Despacito', ['Luis Fonsi']), ficha('Despacito (Remix)', 'Luis Fonsi, Justin Bieber'), false),
        (pista('Despacito (Remix)', ['Luis Fonsi']), ficha('Despacito', 'Luis Fonsi'), false),
        (pista('Mojado (Versión Acústica)', ['Ricardo Arjona']), ficha('Mojado', 'Ricardo Arjona'), false),
        (pista('Bohemian Rhapsody - Remastered 2011', ['Queen']), ficha('Bohemian Rhapsody', 'Queen'), true),
        (pista('De Música Ligera (Remasterizado 2007)', ['Soda Stereo']), ficha('De Musica Ligera', 'Soda Stereo'), true),
        (pista('Adele - Hello (Official Video)', ['Canal Cualquiera']), ficha('Hello', 'Adele'), true),
        (pista('Hello - Adele', ['Canal Cualquiera']), ficha('Hello', 'Adele'), true),
        (pista('De YouTube', ['x'], dur: 19), ficha('Alcohol', 'X'), false),
        (pista('アイドル', ['YOASOBI']), ficha('アイドル', 'YOASOBI'), true),
        (pista('アイドル', ['YOASOBI']), ficha('夜に駆ける', 'YOASOBI'), false),
        (pista('Hello', ['Adele']), ficha('Hello', 'Adele', instrumental: true), false),
      ];
      for (final (p, c, vale) in casos) {
        expect(ElegirLetra.esLaCancion(c, p), vale, reason: '${p['titulo']} / ${c['trackName']} - ${c['artistName']}');
      }
    });

    test('los tiempos solo si dura lo mismo', () {
      final p = pista('Hello', ['Adele'], dur: 367);
      final album = ficha('Hello', 'Adele', dur: 295), video = ficha('Hello', 'Adele', dur: 366);
      expect(ElegirLetra.elegir([album, video], p, duracion: 367).con, same(video));
      final e = ElegirLetra.elegir([album], p, duracion: 367);
      expect(e.con, isNull);
      expect(e.texto, same(album));
      expect(e.otra, same(album));
    });

    test('el texto de YouTube Music descarta la letra de otra canción', () {
      const buena = 'si estoy tomando es porque estoy echando alcohol a las heridas que por dentro estoy curando hoy';
      const mala = 'ella durmió al calor de las masas y yo desperté queriendo soñarla algún tiempo atrás pensé en escribirle';
      final p = pista('Alcohol', ['Grupo X']);
      final a = ficha('Alcohol', 'Grupo X', texto: mala), b = ficha('Alcohol', 'Grupo X', dur: 201, texto: buena);
      expect(ElegirLetra.elegir([a, b], p, duracion: 200).con, same(a));
      expect(ElegirLetra.elegir([a, b], p, duracion: 200, textoBueno: buena).con, same(b));
      final e = ElegirLetra.elegir([a], p, duracion: 200, textoBueno: buena);
      expect((e.con, e.texto, e.otra), (null, null, null));
    });

    test('LRC con [offset], marcas por palabra y versos repetidos', () {
      expect(
          Catalogo.lrcALineas(
              '[offset:+500]\n[00:10.00]Uno\n[00:20.50]<00:20.50> Dos <00:21.00> tres\n[00:30.00][00:40.00]Coro'),
          [
            [9500, 'Uno'], [20000, 'Dos tres'], [29500, 'Coro'], [39500, 'Coro'],
          ]);
    });
  });

  group('la letra sigue a la música', () {
    test('tocar cuando empieza un verso lo deja en su sitio', () {
      // el verso decía 10 s y se canta a los 23: la letra se atrasa unos 13 s
      final d = desfaseAlTocar(10000, const Duration(seconds: 23));
      expect(d, closeTo(-13000, 200));
      const ls = [(10000, 'uno'), (15000, 'dos')];
      expect(LetraBloqueo.indiceEn(ls, 22000 + d), -1);
      expect(LetraBloqueo.indiceEn(ls, 23300 + d), 0);
    });

    test('adelantar hace que el verso salga antes; atrasar, después', () {
      final c = LetrasCache.prueba();
      const ls = [(10000, 'uno')];
      c.ponerDesfase('k', 500);
      expect(LetraBloqueo.indiceEn(ls, 9600 + c.desfase('k')), 0);
      c.ponerDesfase('k', -500);
      expect(LetraBloqueo.indiceEn(ls, 10400 + c.desfase('k')), -1);
    });

    test('el ajuste de todas se suma al de cada canción', () {
      final c = LetrasCache.prueba();
      c.ponerDesfaseGeneral(-200);
      c.ponerDesfase('k', 1000);
      expect(c.desfase('k'), 800);
      expect(c.desfase('otra'), -200);
      for (var i = 0; i < 600; i++) {
        c.ponerDesfase('c$i', 10);
      }
      expect(c.desfaseGeneral, -200, reason: 'el general no se pierde al hacer sitio');
    });

    test('la letra elegida a mano manda y avisa', () async {
      final c = LetrasCache.prueba();
      var avisos = 0;
      c.cambios.addListener(() => avisos++);
      c.cargador = (_) async => {'lineas': [[1000, 'mala']], 'texto': 'mala'};
      expect((await c.obtener({'clave': 'k'}))!['texto'], 'mala');
      c.elegir('k', {'lineas': [[2000, 'buena']], 'texto': 'buena'});
      expect((await c.obtener({'clave': 'k'}))!['texto'], 'buena');
      expect(avisos, 1);
      c.olvidar('k');
      expect((await c.obtener({'clave': 'k'}))!['texto'], 'mala');
    });

    test('los tiempos de otra grabación se guardan aparte, sin usarlos', () async {
      final c = LetrasCache.prueba();
      c.cargador = (_) async => {'lineas': [], 'texto': 'hola', 'ajustables': [[5000, 'hola']]};
      final l = (await c.obtener({'clave': 'k'}))!;
      expect(lineasConTiempo(l), isEmpty);
      expect(lineasConTiempo({'lineas': l['ajustables']}), [(5000, 'hola')]);
    });
  });

  group('diseños', () {
    test('cada estilo y cada tipo de letra existe de verdad', () {
      final claves = {for (final e in LetraAspecto.estilos) e.clave};
      expect(claves, containsAll(disenosEnCapas));
      expect(LetraAspecto.estilos.length, 10);
      expect(LetraAspecto.fuentes.length, 27);
      expect({for (final f in LetraAspecto.fuentes) f.clave}.length, 27);
      for (final f in LetraAspecto.fuentes) {
        if (f.archivo != null) {
          expect(File('assets/fuentes_extra/${f.archivo}').existsSync(), isTrue, reason: f.nombre);
        }
      }
    });

    for (final e in [for (final x in LetraAspecto.estilos) x.clave]) {
      testWidgets('$e se pinta en todas sus formas', (t) async {
        for (final ancho in [160.0, 600.0]) {
          for (final alinear in [TextAlign.start, TextAlign.center]) {
            for (final p in [0.0, 0.4, 1.0]) {
              await t.pumpWidget(MaterialApp(
                home: Scaffold(
                  body: Center(
                    child: SizedBox(
                      width: ancho,
                      child: Column(children: [
                        LineaLetra(aspecto: LetraAspecto(estilo: e), texto: 'La que ya se cantó', alinear: alinear,
                            estilo: const TextStyle(fontSize: 22, color: Color(0xB3FFFFFF))),
                        LineaLetraFija(aspecto: LetraAspecto(estilo: e), texto: '¿Cuándo volverás, corazón de niño?',
                            alinear: alinear, progreso: p, acento: Colors.teal,
                            estilo: const TextStyle(fontSize: 30, fontWeight: FontWeight.w800, color: Colors.white)),
                        TextoLetraPlano(aspecto: LetraAspecto(estilo: e), texto: 'uno\ndos',
                            estilo: const TextStyle(fontSize: 18, color: Colors.white)),
                      ]),
                    ),
                  ),
                ),
              ));
              await t.pump(const Duration(milliseconds: 300));
              expect(t.takeException(), isNull);
            }
          }
        }
      });
    }

    testWidgets('el selector avisa de lo que se toca y no se desborda', (t) async {
      for (final tam in [const Size(320, 640), const Size(390, 844), const Size(1200, 800)]) {
        t.view.physicalSize = tam;
        t.view.devicePixelRatio = 1;
        final tocados = <String>[];
        await t.pumpWidget(MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: SelectorLetra(alElegirEstilo: tocados.add, alElegirFuente: tocados.add),
            ),
          ),
        ));
        await t.pump();
        expect(t.takeException(), isNull);
        await t.ensureVisible(find.text('Oro'));
        await t.tap(find.text('Oro'));
        await t.ensureVisible(find.text('Lilita One'));
        await t.tap(find.text('Lilita One'));
        expect(tocados, ['oro', 'lilita']);
      }
      t.view.reset();
    });

    test('la caída de «Lluvia» acaba en su sitio', () {
      expect(EscenaLetra.rebote(0), 0);
      expect(EscenaLetra.rebote(1), closeTo(1, 1e-9));
    });

    for (final e in Cosmeticos.estilosLetra) {
      testWidgets('escena «$e» con un diseño en capas', (t) async {
        LetraAspecto.actual.value = const LetraAspecto(estilo: 'relieve');
        addTearDown(() => LetraAspecto.actual.value = const LetraAspecto());
        await t.pumpWidget(MaterialApp(
          home: Scaffold(
            body: EscenaLetraVista(
                lineas: const [(0, 'Uno'), (1000, '¿Y qué será de mí, corazón?'), (2000, 'Tres')],
                actual: 1, estilo: e, paleta: PaletaPortada.neutra),
          ),
        ));
        for (var i = 0; i < 12; i++) {
          await t.pump(const Duration(milliseconds: 220));
          expect(t.takeException(), isNull);
        }
      });
    }
  });
}
