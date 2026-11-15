import 'dart:typed_data';

import 'package:caudal/nucleo/chat.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/social.dart';
import 'package:caudal/ui/paginas/directorio_pagina.dart';
import 'package:caudal/ui/paginas/perfil_comun.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;

Widget _app(Widget hijo) => MaterialApp(
      theme: ThemeData.dark().copyWith(splashFactory: NoSplash.splashFactory),
      home: Scaffold(body: Center(child: SingleChildScrollView(child: hijo))),
    );

void main() {
  group('modelos del plan', () {
    test('ver_perfil completo', () {
      final p = Perfil.desde({
        'id': 'u1', 'usuario': 'ana', 'nombre': 'Ana', 'foto_url': 'u1/avatar.jpg', 'relacion': 'amigo',
        'bio': 'Hola', 'cancion_fav': {'video_id': 'abc', 'titulo': 'T', 'artista': 'A', 'miniatura': 'http://x/y.jpg'},
        'artista_fav': 'Bad Bunny', 'generos': ['Pop', 'Rock'], 'frase': 'vivo', 'color_perfil': '#FF5C8A',
        'creado': '2026-01-05T10:00:00Z', 'es_mio': false, 'publico': true, 'mostrar_top': true,
        'top_artistas': [{'nombre': 'Rosalía', 'portada': 'p', 'veces': 9}],
        'top_canciones': [{'titulo': 'Cancion', 'clave': 'yt:zzzzzzzzzzz', 'veces': 3}],
        'insignias': [{'clave': 'veterano', 'titulo': 'Veterano', 'detalle': 'Más de 60 días'}],
        'afinidad': 78, 'likes': 201, 'di_like': true, 'es_artista': true, 'num_subidas': 1,
        'fundador': true, 'numero': 17, 'fundador_caudal': true,
        'titulos': [{'clave': 'rey_de_la_musica', 'nombre': 'Rey de la música'}],
        'subidas': [{'id': 's1', 'titulo': 'Mi tema', 'artista': 'Ana', 'album': 'Disco', 'duracion': 200,
          'ruta': 'u1/a.mp3', 'portada': 'u1/c.jpg', 'escuchas': 4, 'estado': 'publicada', 'creado': '2026-02-01T00:00:00Z'}],
      })!;
      expect(p.visible, 'Ana');
      expect(p.relacion, Relacion.amigo);
      expect(p.cancionFav!.titulo, 'T');
      expect(p.generos, ['Pop', 'Rock']);
      expect(p.topArtistas.single.veces, 9);
      expect(p.insignias.single.clave, 'veterano');
      expect(p.afinidad, 78);
      expect(p.esArtista, true);
      expect(p.fundador, true);
      expect(p.numero, 17);
      // «Fundador de Caudal» va primero aunque solo llegue como bool
      expect(p.titulos.map((t) => t.clave).toList(), ['fundador_caudal', 'rey_de_la_musica']);
      final s = p.subidas.single;
      expect(s.usuario, 'ana');
      expect(s.urlAudio, '${Nube.url}/storage/v1/object/public/musica/u1/a.mp3');
      expect(s.linea, 'Ana · Disco');
    });

    test('perfil privado y campos que faltan no rompen nada', () {
      final p = Perfil.desde({'id': 'u2', 'usuario': 'beto', 'nombre': 'Beto', 'relacion': 'rarisima', 'privado': true})!;
      expect(p.privado, true);
      expect(p.relacion, Relacion.ninguna);
      expect(p.subidas, isEmpty);
      expect(p.titulos, isEmpty);
      expect(p.fundador, false);
      expect(p.afinidad, isNull);
      expect(p.sePuedeDarLike, false);
      expect(Perfil.desde(null), isNull);
      expect(Perfil.desde({'usuario': 'sin id'}), isNull);
    });

    test('tarjeta del directorio', () {
      final t = PerfilTarjeta.desde({
        'id': 'u3', 'usuario': 'cami', 'nombre': '', 'bio': 'hola', 'relacion': 'enviada', 'likes': 199,
        'di_like': false, 'num_subidas': 2, 'es_artista': false, 'fundador': true,
        'titulos': [{'clave': 'otra_cosa', 'nombre': 'Algo nuevo'}],
      });
      expect(t.visible, 'cami');
      expect(t.titulos.single.nombre, 'Algo nuevo');
      final con = t.conLike(true, 200);
      expect(con.esArtista, true, reason: 'al llegar a 200 sale la nota ARTISTA');
      expect(con.fundador, true);
      expect(con.titulos.length, 1);
      expect(t.conRelacion(Relacion.amigo).relacion, Relacion.amigo);
    });

    test('listas de amigos, solicitudes y búsqueda', () {
      final r = Contacto.recibida({'id': 7, 'de': 'u9', 'usuario': 'luz', 'nombre': 'Luz', 'creado': '2026-11-01T00:00:00Z'});
      expect(r.solicitudId, 7);
      expect(r.id, 'u9');
      expect(r.relacion, Relacion.recibida);
      expect(Contacto.enviada({'id': 1, 'para': 'u8', 'usuario': 'x'}).id, 'u8');
      expect(Contacto.amigo({'id': 'u5', 'usuario': 'y', 'desde': '2026-01-01T00:00:00Z'}).relacion, Relacion.amigo);
      expect(Contacto.busqueda({'id': 'u4', 'usuario': 'z', 'relacion': 'bloqueado'}).relacion, Relacion.bloqueado);
    });

    test('la canción de la comunidad se reproduce como archivo remoto', () {
      final s = Subida.desde({'id': 'abc', 'user_id': 'u1', 'usuario': 'ana', 'titulo': 'Tema', 'ruta': 'u1/a.mp3',
        'portada': 'u1/c.jpg', 'duracion': 180});
      final p = s.comoPista();
      expect(p['video_id'], '');
      expect(p['archivo'], s.urlAudio);
      expect(p['es_audio'], true);
      expect(p['subida_id'], 'abc');
      expect(p['miniatura'], s.urlPortada);
      expect(p['artista'], '@ana');
    });

    test('perfil editable: cuerpo del PATCH y menor de edad', () {
      final e = PerfilEditable.desde({
        'nombre': 'Ana', 'bio': '', 'frase': '', 'foto_url': null, 'cancion_fav': null, 'artista_fav': '',
        'generos': ['Pop'], 'color_perfil': null, 'perfil_publico': true, 'mostrar_top': true,
        'fecha_nacimiento': DateTime.now().subtract(const Duration(days: 365 * 15)).toIso8601String(),
      });
      expect(e.esMenor, true);
      final cuerpo = e.paraGuardar();
      expect(cuerpo['foto_url'], isNull);
      expect(cuerpo['color_perfil'], isNull);
      expect(cuerpo['generos'], ['Pop']);
      final c = e.copiar(cancionFav: const CancionFav(videoId: 'v', titulo: 'T', artista: 'A', miniatura: 'm'));
      expect(c.paraGuardar()['cancion_fav'], {'video_id': 'v', 'titulo': 'T', 'artista': 'A', 'miniatura': 'm'});
      expect(c.copiar(cancionFav: null).cancionFav, isNull);
    });
  });

  group('utilidades', () {
    test('color del perfil e ir y volver a hex', () {
      expect(Social.colorDe('#FF5C8A'), const Color(0xFFFF5C8A));
      expect(Social.colorDe('rojo'), isNull);
      expect(Social.hexDe(const Color(0xFF22D3EE)), '#22D3EE');
    });

    test('foto: url con marca y extensiones de audio', () {
      expect(Social.urlFoto('', marca: 1), '');
      expect(Social.urlFoto('u/avatar.jpg', marca: 5), endsWith('/avatares/u/avatar.jpg?v=5'));
      expect(Social.extensionAudio('Mi Tema.MP3'), 'mp3');
      expect(Social.extensionAudio('video.mp4'), isNull);
      expect(Social.nombreSeguro('Tití, Me Preguntó!', 'mp3'), matches(RegExp(r'^\d+-tit-me-pregunt\.mp3$')));
    });

    test('los errores de la base salen en lenguaje normal', () {
      expect(Nube.traducirSocial('primero deben ser amigos'), contains('amigos'));
      expect(Nube.traducirSocial('espera unos dias para volver a enviarla'), contains('30 días'));
      expect(Nube.traducirSocial('la cancion necesita una portada'), contains('carátula'));
      expect(Nube.traducirSocial('algo raro'), isNull);
      expect(Social.resultadoSolicitud('aceptada', 'Ana'), contains('amigos'));
    });

    test('Persona solo es chateable si es amigo', () {
      expect(Persona('1', 'a', 'A', relacion: 'amigo').esAmigo, true);
      expect(Persona('1', 'a', 'A', relacion: 'enviada').esAmigo, false);
      final r = ResumenChat.desde({'id': '1', 'otro': '2', 'usuario': 'x', 'foto_url': '2/avatar.jpg',
        'ultimo': '2026-11-14T10:00:00Z'}, 'yo');
      expect(r.fotoUrl, '2/avatar.jpg');
    });

    test('la foto sale cuadrada de 512 px y la carátula cabe en 800', () {
      final grande = img.Image(width: 1600, height: 900);
      img.fill(grande, color: img.ColorRgb8(200, 30, 90));
      final bytes = Uint8List.fromList(img.encodePng(grande));
      final foto = img.decodeJpg(cuadrarYComprimir(bytes, 512, recortar: true))!;
      expect((foto.width, foto.height), (512, 512));
      final car = img.decodeJpg(cuadrarYComprimir(bytes, 800, recortar: false))!;
      expect((car.width, car.height), (800, 450));
      expect(() => cuadrarYComprimir(Uint8List.fromList([1, 2, 3]), 512, recortar: true), throwsA(isA<ErrorNube>()));
    });
  });

  group('widgets', () {
    testWidgets('el botón de amistad cambia según la relación', (t) async {
      for (final (rel, texto) in [
        (Relacion.ninguna, 'Agregar'),
        (Relacion.enviada, 'Solicitud enviada'),
        (Relacion.recibida, 'Aceptar solicitud'),
        (Relacion.amigo, 'Escribir'),
      ]) {
        await t.pumpWidget(_app(BotonAmistad(relacion: rel, alPulsar: () {})));
        expect(find.text(texto), findsOneWidget, reason: rel);
      }
      await t.pumpWidget(_app(BotonAmistad(relacion: Relacion.yo, alPulsar: () {})));
      expect(find.byType(FilledButton), findsNothing);
    });

    testWidgets('distinciones: fundador, títulos y artista, el de Caudal primero', (t) async {
      await t.pumpWidget(_app(DistincionesPerfil(
        titulos: TituloEspecial.lista([
          {'clave': 'rey_de_la_musica', 'nombre': 'Rey de la música'},
          {'clave': 'nueva_cosa', 'nombre': 'Algo nuevo'},
        ], fundadorCaudal: true),
        fundador: true,
        numero: 17,
        artista: true,
      )));
      expect(find.text('Fundador de Caudal'), findsOneWidget);
      expect(find.text('Rey de la música'), findsOneWidget);
      expect(find.text('Algo nuevo'), findsOneWidget);
      expect(find.text('Fundador n.º 17'), findsOneWidget);
      expect(find.text('ARTISTA'), findsOneWidget);
      expect(t.getTopLeft(find.text('Fundador de Caudal')).dx,
          lessThan(t.getTopLeft(find.text('Rey de la música')).dx));
    });

    testWidgets('el me gusta muestra el total', (t) async {
      var pulsado = 0;
      await t.pumpWidget(_app(BotonLike(di: true, total: 42, alPulsar: () => pulsado++)));
      expect(find.text('42'), findsOneWidget);
      await t.tap(find.byType(InkWell));
      expect(pulsado, 1);
    });

    testWidgets('la tarjeta del directorio muestra nombre, nota y botones', (t) async {
      Aspecto.aplicar('cian', 'negro');
      var abierta = false;
      await t.pumpWidget(_app(SizedBox(
        width: 230,
        height: 336,
        child: TarjetaPerfil(
          perfil: PerfilTarjeta.desde({
            'id': 'u1', 'usuario': 'ana', 'nombre': 'Ana', 'bio': 'Amo la salsa', 'relacion': 'ninguna',
            'likes': 5, 'num_subidas': 3, 'es_artista': true, 'fundador': true,
          }),
          alAbrir: () => abierta = true,
          alLike: () {},
          alAmistad: () {},
        ),
      )));
      expect(find.text('Ana'), findsOneWidget);
      expect(find.text('@ana'), findsOneWidget);
      expect(find.text('Amo la salsa'), findsOneWidget);
      expect(find.text('ARTISTA'), findsOneWidget);
      expect(find.text('Agregar'), findsOneWidget);
      await t.tap(find.text('Ana'));
      expect(abierta, true);
      expect(sinExcepciones(t), true);
    });

    testWidgets('la fila de música de la comunidad muestra autor y avisa al reproducir', (t) async {
      var sono = false;
      await t.pumpWidget(_app(FilaSubida(
        subida: Subida.desde({'id': 's', 'usuario': 'ana', 'titulo': 'Mi tema', 'artista': 'Ana', 'album': 'Disco',
          'escuchas': 2, 'es_artista': true}),
        alReproducir: () => sono = true,
        alReportar: () {},
      )));
      expect(find.text('Mi tema'), findsOneWidget);
      expect(find.text('Ana · Disco · 2 escuchas'), findsOneWidget);
      expect(find.text('Subida por @ana'), findsOneWidget);
      expect(find.text('ARTISTA'), findsOneWidget);
      await t.tap(find.byTooltip('Escuchar Mi tema'));
      expect(sono, true);
      await t.tap(find.byTooltip('Más opciones'));
      await t.pumpAndSettle();
      expect(find.text('Reportar'), findsOneWidget);
    });

    testWidgets('avatar sin foto muestra la inicial', (t) async {
      await t.pumpWidget(_app(const AvatarPerfil(nombre: 'Luz')));
      expect(find.text('L'), findsOneWidget);
    });
  });
}

bool sinExcepciones(WidgetTester t) => t.takeException() == null;
