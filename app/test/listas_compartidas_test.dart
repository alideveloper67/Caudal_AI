import 'package:caudal/nucleo/chat.dart';
import 'package:caudal/nucleo/listas_compartidas.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/ui/paginas/lista_compartida_pagina.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Una sesión que no sale a internet: apunta cada pedido y contesta con lo que
/// le diga [responder] (la ruta es `rpc/<función>` o `mensajes…`).
class SesionFalsa extends Sesion {
  SesionFalsa(this.responder) : super('yo-id', 'token', 'refresco', DateTime.now().add(const Duration(hours: 1)));

  final dynamic Function(String ruta, Object? cuerpo) responder;
  final List<(String, String, Object?)> pedidos = [];

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    pedidos.add((metodo, ruta, cuerpo));
    final r = responder(ruta, cuerpo);
    if (r is Exception) throw r;
    return r;
  }

  List<(String, String, Object?)> de(String ruta) => [for (final p in pedidos) if (p.$2 == ruta) p];
}

// Formas EXACTAS que devuelven las funciones de supabase/listas.sql.
const _vistaPrevia = {
  'nombre': 'Rock de ruta',
  'descripcion': '',
  'total': 9,
  'rol': 'colaborador',
  'miembros': 2,
  'dueno': {'usuario': 'ana', 'nombre': 'Ana', 'foto_url': null},
  'canciones': [
    {'titulo': 'Tema 1', 'artista': 'Banda', 'miniatura': 'https://i.ytimg.com/vi/a/hq.jpg'},
    {'titulo': 'Tema 2', 'artista': '', 'miniatura': ''},
  ],
};

void main() {
  group('el código', () {
    test('se normaliza: mayúsculas, sin espacios ni guiones', () {
      expect(normalizarCodigoLista(' k7m2-9qxp '), 'K7M29QXP');
      expect(normalizarCodigoLista('k7m2 9qxp'), 'K7M29QXP');
    });

    test('se muestra con guion', () {
      expect(formatearCodigoLista('K7M29QXP'), 'K7M2-9QXP');
      expect(formatearCodigoLista('k7m2-9qxp'), 'K7M2-9QXP');
      expect(formatearCodigoLista('ABC'), 'ABC');
    });

    test('solo vale el alfabeto legible de 8 caracteres', () {
      expect(codigoListaValido('K7M2-9QXP'), isTrue);
      expect(codigoListaValido('K7M2-9QX'), isFalse);
      expect(codigoListaValido('K7M2-9QXO'), isFalse); // la O no existe
      expect(codigoListaValido('K7M2-9QX1'), isFalse); // el 1 tampoco
    });

    test('se saca de un enlace, de otro enlace o de un mensaje pegado entero', () {
      expect(codigoListaDeTexto('K7M2-9QXP'), 'K7M29QXP');
      expect(codigoListaDeTexto('https://caudal-musica.netlify.app/l/K7M2-9QXP'), 'K7M29QXP');
      expect(codigoListaDeTexto('caudal://lista?codigo=K7M2-9QXP'), 'K7M29QXP');
      expect(codigoListaDeTexto('caudal://lista?codigo=k7m29qxp'), 'K7M29QXP');
      expect(codigoListaDeTexto(mensajeCompartirLista('Mi lista', 'K7M29QXP')), 'K7M29QXP');
      expect(codigoListaDeTexto('hola'), isNull);
      expect(codigoListaDeTexto('   '), isNull);
      expect(codigoListaDeTexto('caudal://lista?codigo=XYZ'), isNull);
    });

    test('reconoce los enlaces de lista', () {
      expect(esEnlaceDeLista('caudal://lista?codigo=K7M2-9QXP'), isTrue);
      expect(esEnlaceDeLista('https://caudal-musica.netlify.app/l/K7M2-9QXP'), isTrue);
      expect(esEnlaceDeLista('caudal://juntos?sala=ABC234'), isFalse);
      expect(esEnlaceDeLista('K7M2-9QXP'), isFalse);
    });

    test('el mensaje de compartir es el acordado', () {
      expect(mensajeCompartirLista('Rock de ruta', 'K7M29QXP'),
          'Te paso mi lista «Rock de ruta» en Caudal 🎧\n'
          'Ábrela aquí: https://caudal-musica.netlify.app/l/K7M2-9QXP\n'
          'O entra a Caudal › Biblioteca › «Tengo un código» y escribe: K7M2-9QXP');
      expect(enlaceAppLista('K7M29QXP'), 'caudal://lista?codigo=K7M2-9QXP');
    });
  });

  group('los modelos desde lo que devuelve la base', () {
    test('vista previa (ver_lista_codigo)', () {
      final v = VistaPreviaLista.desde(_vistaPrevia)!;
      expect(v.nombre, 'Rock de ruta');
      expect(v.total, 9);
      expect(v.puedeAnadir, isTrue);
      expect(v.permisoTexto, 'Puedes añadir canciones');
      expect(v.dueno.visible, 'Ana');
      expect(v.dueno.fotoUrl, '');
      expect(v.canciones, hasLength(2));
      expect(v.canciones.first.artista, 'Banda');
      expect(VistaPreviaLista.desde({..._vistaPrevia, 'rol': 'oyente'})!.permisoTexto, 'Solo escuchar');
      expect(VistaPreviaLista.desde(null), isNull); // código que no existe
    });

    test('unirse (unirse_a_lista)', () {
      final r = ResultadoUnirse.desde(
          {'lista_id': 'u-1', 'nombre': 'Rock de ruta', 'rol': 'oyente', 'es_dueno': false});
      expect(r.listaId, 'u-1');
      expect(r.puedeAnadir, isFalse);
      expect(r.esDueno, isFalse);
      final d = ResultadoUnirse.desde({'lista_id': 'u-2', 'nombre': 'X', 'rol': 'colaborador', 'es_dueno': true});
      expect(d.esDueno, isTrue);
    });

    test('mis listas compartidas (mis_listas_compartidas)', () {
      final l = ListaCompartida.desde({
        'id': 'u-1', 'nombre': 'Rock de ruta', 'descripcion': null, 'rol': 'colaborador', 'total': 12,
        'actualizada': '2026-11-16T10:00:00+00:00',
        'dueno': {'id': 'd-1', 'usuario': 'ana', 'nombre': '', 'foto_url': 'd-1/avatar.jpg'},
      });
      expect(l.puedeAnadir, isTrue);
      expect(l.total, 12);
      expect(l.descripcion, '');
      expect(l.dueno.visible, 'ana'); // sin nombre, se ve el usuario
      expect(l.actualizada, isNotNull);
    });

    test('miembros (miembros_lista): el dueño va primero', () {
      final m = MiembroLista.desdeJson({
        'id': 'd-1', 'usuario': 'ana', 'nombre': 'Ana', 'foto_url': null, 'rol': 'colaborador',
        'desde': '2026-11-01T10:00:00+00:00', 'es_dueno': true,
      });
      expect(m.esDueno, isTrue);
      expect(m.id, 'd-1');
      expect(m.persona.visible, 'Ana');
    });

    test('canciones (pistas_de_lista) con quién las añadió', () {
      final p = PistaCompartida.desde({
        'clave': 'yt:aaaaaaaaaaa',
        'datos': {'titulo': 'Tema', 'artista': 'Banda'},
        'orden': 3,
        'agregada': '2026-11-16T10:00:00+00:00',
        'agregada_por': {'id': 'b-1', 'usuario': 'beto', 'nombre': 'Beto'},
      });
      expect(p.textoAutor, 'Añadida por Beto');
      expect(p.pista['video_id'], 'aaaaaaaaaaa');
      expect(p.pista['clave'], 'yt:aaaaaaaaaaa');
      expect(p.pista['titulo'], 'Tema');
      // la persona ya no existe: no se inventa un autor
      final huerfana = PistaCompartida.desde({
        'clave': 'yt:bbbbbbbbbbb', 'datos': {}, 'orden': 4, 'agregada': null,
        'agregada_por': {'id': null, 'usuario': null, 'nombre': null},
      });
      expect(huerfana.textoAutor, '');
    });

    test('solo viajan canciones de YouTube Music', () {
      final items = ListasCompartidas.itemsParaNube([
        {'clave': 'yt:aaaaaaaaaaa', 'titulo': 'A', 'archivo': '/sdcard/a.mp3'},
        {'clave': 'local:xyz', 'titulo': 'B'},
      ]);
      expect(items, hasLength(1));
      expect(items.first['clave'], 'yt:aaaaaaaaaaa');
      expect((items.first['datos'] as Map).containsKey('archivo'), isFalse);
    });
  });

  group('los errores de la base, en frases humanas', () {
    String? t(String m) => Nube.traducirSocial(m);

    test('cada aviso de listas.sql tiene su frase', () {
      expect(t('Ese código no existe o la lista ya no se comparte. Revisa que esté bien escrito.'),
          contains('no existe o la lista ya no se comparte'));
      expect(t('No te puedes unir a esta lista.'), 'No puedes unirte a esta lista.');
      expect(t('Esta lista ya tiene 20 personas, que es el máximo. Pídele a su dueño que haga lugar.'),
          contains('llena'));
      expect(t('Esa lista no existe o no es tuya.'), contains('ya no existe'));
      expect(t('No tienes acceso a esa lista.'), contains('Ya no tienes acceso'));
      expect(t('En esta lista solo puedes escuchar: no puedes añadir canciones.'), contains('solo puedes escuchar'));
      expect(t('Solo puedes quitar las canciones que añadiste tú.'), isNotNull);
      expect(t('Una lista compartida admite hasta 2000 canciones y esta ya tiene 2000.'), contains('2000'));
      expect(t('No estás en esa lista.'), 'Ya no estás en esa lista.');
      expect(t('Solo el dueño de la lista puede quitar a alguien.'), isNotNull);
    });
  });

  group('la tarjeta del chat', () {
    test('se arma desde la columna lista del mensaje', () {
      final t = TarjetaLista.desde({'codigo': 'k7m2-9qxp', 'nombre': 'Rock de ruta', 'canciones': 12, 'rol': 'colaborador'})!;
      expect(t.codigo, 'K7M29QXP');
      expect(t.codigoVisible, 'K7M2-9QXP');
      expect(t.colaborativa, isTrue);
      expect(t.textoCanciones, '12 canciones');
      expect(t.resumen, 'Colaborativa · 12 canciones');
      expect(TarjetaLista.desde({'codigo': 'K7M29QXP', 'nombre': 'X', 'canciones': 1, 'rol': 'oyente'})!.resumen,
          'Solo escuchar · 1 canción');
      expect(TarjetaLista.desde({'nombre': 'sin código'}), isNull);
      expect(TarjetaLista.desde('basura'), isNull);
    });

    test('va y vuelve a JSON sin perder nada', () {
      const t = TarjetaLista(codigo: 'K7M29QXP', nombre: 'Rock', canciones: 3, rol: 'oyente', portada: 'u');
      expect(t.aJson(), {'codigo': 'K7M29QXP', 'nombre': 'Rock', 'canciones': 3, 'rol': 'oyente', 'portada': 'u'});
      expect(TarjetaLista.desde(t.aJson())!.portada, 'u');
      expect(const TarjetaLista(codigo: 'K7M29QXP', nombre: 'R').aJson().containsKey('portada'), isFalse);
    });

    test('el mensaje trae su lista y sigue trayendo la canción y el texto', () {
      final m = Mensaje.desde({
        'id': 5, 'autor': 'a', 'texto': '', 'pista': null, 'creado': '2026-11-16T10:00:00Z',
        'lista': {'codigo': 'K7M29QXP', 'nombre': 'Rock', 'canciones': 2, 'rol': 'colaborador'},
      });
      expect(m.lista!.nombre, 'Rock');
      expect(m.pista, isNull);
      final c = Mensaje.desde({
        'id': 6, 'autor': 'a', 'texto': 'hola', 'pista': {'clave': 'yt:aaaaaaaaaaa', 'titulo': 'T'},
        'creado': '2026-11-16T10:00:00Z',
      });
      expect(c.texto, 'hola');
      expect(c.lista, isNull);
      expect(c.pista!['video_id'], 'aaaaaaaaaaa');
    });

    test('la vista previa del chat dice «♪ Lista «X»» y respeta lo de siempre', () {
      final d = {
        'id': '1', 'otro': '2', 'usuario': 'beto', 'nombre': 'Beto', 'ultimo': '2026-11-16T10:00:00Z',
        'ultimo_texto': null, 'ultimo_pista': null, 'ultimo_autor': 'yo', 'sin_leer': 0,
        'ultimo_lista': {'codigo': 'K7M29QXP', 'nombre': 'Rock de ruta', 'canciones': 2, 'rol': 'colaborador'},
      };
      expect(ResumenChat.desde(d, 'yo').vistaPrevia, 'Tú: ♪ Lista «Rock de ruta»');
      expect(ResumenChat.desde(d, 'otro-id').vistaPrevia, '♪ Lista «Rock de ruta»');
      expect(ResumenChat.desde({...d, 'ultimo_lista': null, 'ultimo_pista': {'titulo': 'Tema'}}, 'yo').vistaPrevia,
          'Tú: ♪ Tema');
      expect(ResumenChat.desde({...d, 'ultimo_lista': null, 'ultimo_texto': 'hola'}, 'otro').vistaPrevia, 'hola');
    });
  });

  group('con una sesión falsa', () {
    test('unirse manda el código normalizado y entiende la respuesta', () async {
      final se = SesionFalsa((ruta, cuerpo) =>
          {'lista_id': 'u-1', 'nombre': 'Rock de ruta', 'rol': 'colaborador', 'es_dueno': false});
      final r = await ListasCompartidas(se).unirse('https://caudal-musica.netlify.app/l/k7m2-9qxp');
      expect(r.nombre, 'Rock de ruta');
      expect((se.de('rpc/unirse_a_lista').single.$3 as Map)['p_codigo'], 'K7M29QXP');
    });

    test('un código mal escrito ni sale a la red', () async {
      final se = SesionFalsa((_, _) => null);
      await expectLater(ListasCompartidas(se).unirse('ABC'), throwsA(isA<ErrorNube>()));
      expect(se.pedidos, isEmpty);
    });

    test('un código que no existe devuelve nulo en la vista previa', () async {
      final se = SesionFalsa((_, _) => null);
      expect(await ListasCompartidas(se).verPorCodigo('K7M2-9QXP'), isNull);
    });

    test('los errores de la base llegan como ErrorNube', () async {
      final se = SesionFalsa((_, _) => const ErrorNube('Esta lista ya está llena (20 personas).'));
      await expectLater(ListasCompartidas(se).unirse('K7M2-9QXP'),
          throwsA(isA<ErrorNube>().having((e) => e.mensaje, 'mensaje', contains('llena'))));
    });

    test('compartir devuelve el código sin guion y avisa si la base mandó basura', () async {
      final ok = SesionFalsa((_, _) => 'K7M29QXP');
      expect(await ListasCompartidas(ok).compartir('u-1', rol: 'oyente'), 'K7M29QXP');
      expect((ok.de('rpc/compartir_lista').single.$3 as Map), {'p_lista': 'u-1', 'p_rol': 'oyente'});
      final mal = SesionFalsa((_, _) => 'hola');
      await expectLater(ListasCompartidas(mal).compartir('u-1'), throwsA(isA<ErrorNube>()));
    });

    test('compartir una lista propia espera a que esté en la nube antes de pedir el código', () async {
      final orden = <String>[];
      final se = SesionFalsa((ruta, _) {
        orden.add(ruta);
        return 'K7M29QXP';
      });
      final r = await ListasCompartidas(se).compartirPropia('u-1',
          rol: 'colaborador', asegurarEnNube: () async => orden.add('enviar-pendientes'));
      expect(orden, ['enviar-pendientes', 'rpc/compartir_lista']);
      expect(r.codigo, 'K7M29QXP');
      expect(r.nueva, isTrue);
    });

    test('una lista sin identificador no se comparte', () async {
      final se = SesionFalsa((_, _) => 'K7M29QXP');
      await expectLater(ListasCompartidas(se).compartirPropia('', rol: 'colaborador'), throwsA(isA<ErrorNube>()));
      expect(se.pedidos, isEmpty);
    });

    test('agregar solo manda canciones de YouTube Music y cuenta lo que entró', () async {
      final se = SesionFalsa((_, _) => 2);
      final n = await ListasCompartidas(se).agregar('u-1', [
        {'clave': 'yt:aaaaaaaaaaa', 'titulo': 'A'},
        {'clave': 'yt:bbbbbbbbbbb', 'titulo': 'B'},
        {'clave': 'local:1', 'titulo': 'C'},
      ]);
      expect(n, 2);
      final cuerpo = se.de('rpc/agregar_a_lista_compartida').single.$3 as Map;
      expect((cuerpo['p_items'] as List), hasLength(2));
      // sin nada que subir no se pide nada
      final vacia = SesionFalsa((_, _) => 0);
      expect(await ListasCompartidas(vacia).agregar('u-1', [{'clave': 'local:1'}]), 0);
      expect(vacia.pedidos, isEmpty);
    });

    // El flujo de «Enviar una lista» desde dentro del chat:
    // elegir lista → compartir si hace falta → armar el mensaje con `lista`.
    test('enviar una lista aún no compartida: se comparte sola y viaja la tarjeta', () async {
      final guardadas = <String, String>{};
      final se = SesionFalsa((ruta, cuerpo) {
        if (ruta == 'rpc/compartir_lista') return 'K7M29QXP';
        if (ruta == 'mensajes') {
          final c = cuerpo as Map;
          return [
            {'id': 7, 'autor': 'yo-id', 'texto': c['texto'], 'pista': null, 'lista': c['lista'],
              'creado': '2026-11-16T10:00:00Z'},
          ];
        }
        return null;
      });
      var subidas = 0;
      final t = await tarjetaParaEnviar(
        base: ListasCompartidas(se),
        uuid: 'u-1',
        nombre: 'Rock de ruta',
        canciones: 12,
        rol: rolColaborador,
        asegurarEnNube: () async => subidas++,
        alCompartir: (u, r) async => guardadas[u] = r,
      );
      expect(subidas, 1);
      expect(guardadas, {'u-1': 'colaborador'});
      expect(t.codigo, 'K7M29QXP');
      expect(t.colaborativa, isTrue);

      final m = await Chat(se).enviar('chat-1', lista: t);
      final cuerpo = se.de('mensajes').single.$3 as Map;
      expect(cuerpo['chat'], 'chat-1');
      expect(cuerpo['texto'], '');
      expect(cuerpo.containsKey('pista'), isFalse);
      expect(cuerpo['lista'], {'codigo': 'K7M29QXP', 'nombre': 'Rock de ruta', 'canciones': 12, 'rol': 'colaborador'});
      expect(m.lista!.nombre, 'Rock de ruta');
    });

    test('«Solo escuchar» elegido en la hoja llega a la base y a la tarjeta', () async {
      final se = SesionFalsa((ruta, _) => 'K7M29QXP');
      final t = await tarjetaParaEnviar(
          base: ListasCompartidas(se), uuid: 'u-1', nombre: 'Rock', canciones: 3, rol: rolOyente);
      expect(t.rol, 'oyente');
      expect((se.de('rpc/compartir_lista').single.$3 as Map)['p_rol'], 'oyente');
    });

    test('si la lista ya estaba compartida se reutiliza su código y su permiso', () async {
      final orden = <String>[];
      final se = SesionFalsa((ruta, _) => 'K7M29QXP');
      final t = await tarjetaParaEnviar(
        base: ListasCompartidas(se),
        uuid: 'u-1',
        nombre: 'Rock',
        canciones: 3,
        rol: rolColaborador, // lo que marca la hoja ahora…
        rolGuardado: rolOyente, // …pero ya estaba compartida como «solo escuchar»
        asegurarEnNube: () async => orden.add('enviar'),
      );
      expect(t.rol, 'oyente');
      expect(orden, isEmpty); // no hace falta esperar a la nube otra vez
      expect((se.de('rpc/compartir_lista').single.$3 as Map)['p_rol'], 'oyente');
    });
  });

  group('lo que recuerda el aparato', () {
    test('guarda qué listas se compartieron y con qué permiso', () async {
      SharedPreferences.setMockInitialValues({});
      final a = await ListasQueComparto.cargar('cuenta-1');
      expect(a.estaCompartida('u-1'), isFalse);
      await a.marcar('u-1', rolOyente);
      final b = await ListasQueComparto.cargar('cuenta-1');
      expect(b.rolDe('u-1'), 'oyente');
      expect((await ListasQueComparto.cargar('otra-cuenta')).estaCompartida('u-1'), isFalse);
      await b.quitar('u-1');
      expect((await ListasQueComparto.cargar('cuenta-1')).estaCompartida('u-1'), isFalse);
    });
  });

  group('la tarjeta en pantalla', () {
    Widget envuelta(Widget w) => MaterialApp(home: Scaffold(body: Center(child: w)));
    const tarjeta = TarjetaLista(codigo: 'K7M29QXP', nombre: 'Rock de ruta', canciones: 12);

    testWidgets('muestra nombre, canciones, permiso y «Unirme»', (t) async {
      ListasCompartidasVistas.lista.value = const [];
      await t.pumpWidget(envuelta(const TarjetaListaChat(tarjeta: tarjeta, mio: false)));
      expect(find.text('Rock de ruta'), findsOneWidget);
      expect(find.text('12 canciones'), findsOneWidget);
      expect(find.text('Colaborativa'), findsOneWidget);
      expect(find.text('Unirme'), findsOneWidget);
    });

    testWidgets('si ya eres miembro o la mandaste tú, dice «Abrir»', (t) async {
      ListasCompartidasVistas.lista.value = const [];
      await t.pumpWidget(envuelta(const TarjetaListaChat(tarjeta: tarjeta, mio: true)));
      expect(find.text('Abrir'), findsOneWidget);
      ListasCompartidasVistas.lista.value = const [ListaCompartida(id: 'u-1', nombre: 'Rock de ruta')];
      await t.pumpWidget(envuelta(const TarjetaListaChat(tarjeta: tarjeta, mio: false)));
      await t.pump();
      expect(find.text('Abrir'), findsOneWidget);
      ListasCompartidasVistas.lista.value = const [];
    });
  });
}
