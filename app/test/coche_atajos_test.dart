import 'package:caudal/coche/atajos_caudal.dart';
import 'package:caudal/coche/ejecutar_atajo.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

Json _p(String t) => {'clave': 'yt:$t', 'video_id': 'v$t', 'titulo': t, 'artista': 'A', 'miniatura': '', 'duracion': 180};

class _Col extends ChangeNotifier implements Coleccion {
  List<Json> gustan = [];
  @override
  Future<List<Json>> listaMeGusta() async => gustan;
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Registro {
  final avisos = <String>[];
  final pestanas = <int>[];
  List<Json>? lista;
  bool? aleatorio;
  Json? contexto;
  Json? pista;
  int descargadas = 0, coches = 0, focos = 0;
}

EjecutorAtajos _ejecutor(_Col col, _Registro r,
        {List<Json> mixes = const [], List<Json> halladas = const [], bool mixFalla = false}) =>
    EjecutorAtajos(
      coleccion: col,
      ponerLista: (pistas, {aleatorio, contexto}) async {
        r.lista = pistas;
        r.aleatorio = aleatorio;
        r.contexto = contexto;
      },
      ponerPista: (p) async => r.pista = p,
      avisar: r.avisos.add,
      irAPestana: r.pestanas.add,
      abrirDescargadas: () => r.descargadas++,
      abrirModoCoche: () async => r.coches++,
      enfocarBuscar: () => r.focos++,
      mixesDelDia: () async => mixFalla ? throw Exception('sin red') : mixes,
      buscarCanciones: (_) async => halladas,
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('leerAtajo', () {
    test('los cuatro accesos del icono y el modo coche', () {
      expect(leerAtajo('caudal://megusta'), const AtajoCaudal(TipoAtajo.meGustaAleatorio));
      expect(leerAtajo('caudal://buscar'), const AtajoCaudal(TipoAtajo.buscar));
      expect(leerAtajo('caudal://descargas'), const AtajoCaudal(TipoAtajo.descargas));
      expect(leerAtajo('caudal://mix'), const AtajoCaudal(TipoAtajo.miMix));
      expect(leerAtajo('caudal://coche'), const AtajoCaudal(TipoAtajo.modoCoche));
      // da igual mayúsculas y espacios alrededor
      expect(leerAtajo('  CAUDAL://MIX  '), const AtajoCaudal(TipoAtajo.miMix));
    });

    test('los enlaces de los accesos son los que entiende', () {
      for (final e in enlacesAtajos.entries) {
        expect(leerAtajo(e.value)?.tipo, e.key, reason: e.value);
      }
    });

    test('buscar y sonar con texto (también con tildes y espacios codificados)', () {
      expect(leerAtajo('caudal://buscar?q=Rosal%C3%ADa'), const AtajoCaudal(TipoAtajo.buscar, texto: 'Rosalía'));
      expect(leerAtajo('caudal://sonar?q=bad%20bunny'), const AtajoCaudal(TipoAtajo.sonar, texto: 'bad bunny'));
      expect(leerAtajo('caudal://sonar?query=x'), const AtajoCaudal(TipoAtajo.sonar, texto: 'x'));
    });

    test('«pon música en Caudal» sin decir qué: tus me gusta', () {
      expect(leerAtajo('caudal://sonar'), const AtajoCaudal(TipoAtajo.meGustaAleatorio));
      expect(leerAtajo('caudal://sonar?q=%20'), const AtajoCaudal(TipoAtajo.meGustaAleatorio));
    });

    test('los enlaces de otros (juntos, listas, estudio, acceso) no son de aquí', () {
      for (final t in [
        'caudal://juntos?sala=ABC123',
        'caudal://lista?codigo=K7M2-9QXP',
        'caudal://estudio',
        'caudal://acceso?code=1',
        'https://youtube.com/watch?v=1',
        'hola',
        '',
      ]) {
        expect(leerAtajo(t), isNull, reason: t);
      }
    });

    test('App Actions: el id del acceso o la frase dicha', () {
      expect(leerAtajo('caudal://funcion?nombre=megusta'), const AtajoCaudal(TipoAtajo.meGustaAleatorio));
      expect(leerAtajo('caudal://funcion?nombre=descargas'), const AtajoCaudal(TipoAtajo.descargas));
      expect(leerAtajo('caudal://funcion?nombre=mix'), const AtajoCaudal(TipoAtajo.miMix));
      expect(leerAtajo('caudal://funcion?nombre=buscar'), const AtajoCaudal(TipoAtajo.buscar));
      expect(leerAtajo('caudal://funcion?nombre=Mis%20Me%20Gusta'), const AtajoCaudal(TipoAtajo.meGustaAleatorio));
      expect(leerAtajo('caudal://funcion?nombre=m%C3%BAsica%20descargada'), const AtajoCaudal(TipoAtajo.descargas));
      expect(leerAtajo('caudal://funcion?nombre=modo%20coche'), const AtajoCaudal(TipoAtajo.modoCoche));
      expect(leerAtajo('caudal://funcion?feature=mi%20mix%20del%20d%C3%ADa'), const AtajoCaudal(TipoAtajo.miMix));
      expect(leerAtajo('caudal://funcion'), const AtajoCaudal(TipoAtajo.buscar));
    });

    test('una función desconocida se busca, no se pierde', () {
      expect(atajoDeFuncion('Karol G'), const AtajoCaudal(TipoAtajo.buscar, texto: 'Karol G'));
      expect(atajoDeFuncion('busca la de shakira'), const AtajoCaudal(TipoAtajo.buscar, texto: 'de shakira'));
      // palabras enteras: una canción que empieza por «auto» no abre el modo coche
      expect(atajoDeFuncion('Autoestima'), const AtajoCaudal(TipoAtajo.buscar, texto: 'Autoestima'));
      expect(atajoDeFuncion('Remix'), const AtajoCaudal(TipoAtajo.buscar, texto: 'Remix'));
      expect(atajoDeFuncion('el auto'), const AtajoCaudal(TipoAtajo.modoCoche));
    });

    test('normalizarVoz quita tildes, mayúsculas y signos', () {
      expect(normalizarVoz('  ¡Mis MEGÚSTA!  '), 'mis megusta');
      expect(normalizarVoz('Canción  ñandú'), 'cancion nandu');
    });
  });

  group('EjecutorAtajos', () {
    setUp(() => consultaDeAtajo.value = null);

    test('Me gusta: suenan en aleatorio con su contexto', () async {
      final col = _Col()..gustan = [_p('a'), _p('b'), _p('c')];
      final r = _Registro();
      expect(await _ejecutor(col, r).atenderEnlace('caudal://megusta'), isTrue);
      expect(r.lista?.length, 3);
      expect(r.aleatorio, isTrue);
      expect(r.contexto?['tipo'], 'me_gusta');
      expect(r.avisos, isEmpty);
    });

    test('Me gusta sin canciones: lo explica y no suena nada', () async {
      final r = _Registro();
      await _ejecutor(_Col(), r).ejecutar(const AtajoCaudal(TipoAtajo.meGustaAleatorio));
      expect(r.lista, isNull);
      expect(r.avisos.single, contains('me gusta'));
    });

    testWidgets('Buscar con texto: va a la pestaña y deja el texto (sin sacar el teclado)', (t) async {
      final r = _Registro();
      await _ejecutor(_Col(), r).atenderEnlace('caudal://buscar?q=Shakira');
      await t.pump();
      expect(r.pestanas, [pestanaBuscar]);
      expect(consultaDeAtajo.value, 'Shakira');
      expect(r.focos, 0);
    });

    testWidgets('Buscar sin texto solo enfoca', (t) async {
      final r = _Registro();
      await _ejecutor(_Col(), r).atenderEnlace('caudal://buscar');
      await t.pump();
      expect(consultaDeAtajo.value, isNull);
      expect(r.focos, 1);
    });

    test('Descargas: biblioteca y la música descargada', () async {
      final r = _Registro();
      await _ejecutor(_Col(), r).atenderEnlace('caudal://descargas');
      expect(r.pestanas, [pestanaBiblioteca]);
      expect(r.descargadas, 1);
      expect(elementoMusicaDescargada['tipo'], 'descargados');
      expect(elementoMusicaDescargada['solo'], isTrue);
    });

    test('Mi mix: el primero que tenga canciones', () async {
      final r = _Registro();
      await _ejecutor(_Col(), r, mixes: [
        {'id': 'mix_diario_1', 'titulo': 'Vacío', 'pistas': <Object>[]},
        {
          'id': 'mix_diario_2',
          'titulo': 'Mix de Pop',
          'miniatura': 'http://x/y.jpg',
          'pistas': [_p('a'), _p('b')],
        },
      ]).atenderEnlace('caudal://mix');
      expect(r.lista?.map((p) => p['titulo']), ['a', 'b']);
      expect(r.contexto, {'tipo': 'mix', 'id': 'mix_diario_2', 'titulo': 'Mix de Pop', 'miniatura': 'http://x/y.jpg'});
      expect(r.aleatorio, isNull, reason: 'el mix va en su orden');
    });

    test('Mi mix sin mix (o sin red): tus me gusta y lo avisa', () async {
      for (final falla in [false, true]) {
        final col = _Col()..gustan = [_p('a')];
        final r = _Registro();
        await _ejecutor(col, r, mixFalla: falla).atenderEnlace('caudal://mix');
        expect(r.lista?.single['titulo'], 'a');
        expect(r.aleatorio, isTrue);
        expect(r.avisos.single, contains('mix aún no está listo'));
      }
    });

    test('Modo coche', () async {
      final r = _Registro();
      await _ejecutor(_Col(), r).atenderEnlace('caudal://coche');
      expect(r.coches, 1);
    });

    test('Sonar: la primera que encuentre', () async {
      final r = _Registro();
      await _ejecutor(_Col(), r, halladas: [_p('Hallada'), _p('Otra')]).atenderEnlace('caudal://sonar?q=hallada');
      expect(r.pista?['titulo'], 'Hallada');
    });

    testWidgets('Sonar sin resultados: lo dice y abre Buscar con el texto', (t) async {
      final r = _Registro();
      await _ejecutor(_Col(), r).atenderEnlace('caudal://sonar?q=nada');
      await t.pump();
      expect(r.pista, isNull);
      expect(r.avisos.single, contains('No encontré «nada»'));
      expect(r.pestanas, [pestanaBuscar]);
      expect(consultaDeAtajo.value, 'nada');
    });

    test('lo que no es un atajo se deja pasar', () async {
      final r = _Registro();
      expect(await _ejecutor(_Col(), r).atenderEnlace('caudal://juntos?sala=X'), isFalse);
      expect(await _ejecutor(_Col(), r).atenderEnlace('https://music.youtube.com/x'), isFalse);
      expect(r.pestanas, isEmpty);
    });

    test('si algo falla, avisa en vez de romper', () async {
      final r = _Registro();
      final e = EjecutorAtajos(
        coleccion: _Col(),
        ponerLista: (p, {aleatorio, contexto}) async {},
        ponerPista: (p) async {},
        avisar: r.avisos.add,
        irAPestana: (_) {},
        abrirDescargadas: () {},
        abrirModoCoche: () async => throw StateError('x'),
      );
      await e.atenderEnlace('caudal://coche');
      expect(r.avisos.single, contains('No se pudo'));
    });
  });
}
