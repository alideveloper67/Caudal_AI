// Grupos para hablar (nucleo/grupos.dart + ui/paginas/grupos_pagina.dart): lo que se manda a la base,
// cómo se leen sus respuestas y las pantallas (lista, crear, conversación, opciones, info). Sin red: una
// sesión falsa que responde como supabase/grupos.sql.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/grupos.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/paginas/grupos_pagina.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _Reproductor extends ChangeNotifier implements Reproductor {
  @override
  Json? actual;
  @override
  EstadoRepro estado = EstadoRepro.parado;
  @override
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  @override
  final ValueNotifier<Duration> duracion = ValueNotifier(const Duration(minutes: 3));
  @override
  Future<void> pausar() async {}
  @override
  Future<void> dispose() async => super.dispose();
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Coleccion extends ChangeNotifier implements Coleccion {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Streams implements Streams {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Descargas extends ChangeNotifier implements GestorDescargas {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Map<String, dynamic> _grupo({String id = 'g1', String nombre = 'Reggaetón Lima', String tipo = 'abierto',
        String? rol = 'miembro', String? codigo, int sinLeer = 0, Map? ultimo}) =>
    {
      'id': id, 'nombre': nombre, 'descripcion': 'Para hablar de perreo', 'tipo': tipo, 'miembros': 3, 'rol': rol,
      'codigo': codigo, 'cerrado': false, 'ultimo': '2026-11-21T15:00:00Z', 'sin_leer': sinLeer,
      'ultimo_mensaje': ultimo,
    };

Map<String, dynamic> _mensaje(int id, {String autor = 'ana', bool mio = false, String texto = 'hola', Map? pista,
        String? audio, int? seg, String rol = 'miembro'}) =>
    {
      'id': id, 'texto': texto, 'pista': pista, 'audio': audio, 'audio_seg': seg, 'fijado': false, 'oculto': false,
      'creado': '2026-11-21T15:0$id:00Z', 'mio': mio,
      'autor': {'id': 'id-$autor', 'usuario': autor, 'nombre': autor.toUpperCase(), 'foto_url': '', 'rol': rol},
    };

class _Sesion extends Sesion {
  _Sesion() : super('yo', 'token', 'r', DateTime.now().add(const Duration(hours: 1)));
  final llamadas = <(String, Map)>[];
  List<Map> mios = [];
  List<Map> mensajes = [];
  Object? fallarCon;
  Map<String, dynamic> verGrupo = _grupo(rol: 'dueno');
  Map<String, dynamic> miFila = {'nombre': 'Yo', 'perfil_publico': true};

  @override
  Future<dynamic> pedir(String metodo, String ruta, {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    final c = Map<String, dynamic>.from((cuerpo as Map?) ?? const {});
    final nombre = ruta.replaceFirst('rpc/', '');
    llamadas.add((nombre, c));
    if (fallarCon != null) throw fallarCon!;
    switch (nombre) {
      case 'perfiles?select=nombre,bio,frase,foto_url,cancion_fav,artista_fav,generos,color_perfil,perfil_publico,mostrar_top,fecha_nacimiento,banner_url&id=eq.yo':
        return [miFila];
      case 'perfiles?id=eq.yo':
        miFila = {...miFila, ...c, 'perfil_publico': true};
        return [miFila];
      case 'mis_grupos':
        return mios;
      case 'grupos_explorar':
        return [_grupo(id: 'g9', nombre: 'Salsa', rol: null)];
      case 'grupo_crear':
        return _grupo(id: 'nuevo', nombre: c['p_nombre'], tipo: c['p_tipo'], rol: 'dueno',
            codigo: c['p_tipo'] == 'privado' ? 'ABCD2345' : null);
      case 'grupo_unirse_codigo':
        return _grupo(id: 'gp', nombre: 'Primos', tipo: 'privado', codigo: c['p_codigo']);
      case 'grupo_mensajes':
        return mensajes.reversed.toList();
      case 'grupo_mensajes_desde':
      case 'grupo_fijados':
      case 'grupo_reportados':
        return [];
      case 'grupo_enviar':
        final m = _mensaje(50 + llamadas.length, autor: 'yo', mio: true, texto: c['p_texto'] ?? '',
            pista: c['p_pista'] as Map?, audio: c['p_audio'] as String?, seg: c['p_audio_seg'] as int?);
        return m;
      case 'grupo_ver':
        return verGrupo;
      case 'grupo_miembros_lista':
        return [
          {'id': 'id-yo', 'usuario': 'yo', 'nombre': 'Yo', 'rol': 'dueno'},
          {'id': 'id-ana', 'usuario': 'ana', 'nombre': 'Ana', 'rol': 'miembro', 'silenciado_hasta': null},
        ];
    }
    return null;
  }
}

late _Sesion _nube;

Future<Servicios> _servicios() async {
  _nube = _Sesion();
  return Servicios(
    cuenta: Cuenta(id: 'yo', usuario: 'yo', nombre: 'Yo', sesion: _nube),
    ajustes: await Ajustes.cargar('prueba'),
    coleccion: _Coleccion(),
    reproductor: _Reproductor(),
    streams: _Streams(),
    descargas: _Descargas(),
    cerrarSesion: () async {},
  );
}

Future<Servicios> _montar(WidgetTester t, Widget hijo, {Servicios? s, Size tam = const Size(411, 900)}) async {
  s ??= await _servicios();
  t.view.physicalSize = tam * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);
  await t.pumpWidget(Caudal(
    s: s,
    child: MaterialApp(scaffoldMessengerKey: s.mensajero, theme: temaCaudal(), home: Scaffold(body: hijo)),
  ));
  await t.pump(const Duration(milliseconds: 200));
  return s;
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  group('servicio', () {
    test('el código se limpia como sea que lo escriban', () {
      expect(Grupos.limpiarCodigo(' abcd-2345 '), 'ABCD2345');
      expect(Grupos.limpiarCodigo('ab cd 23 45'), 'ABCD2345');
    });

    test('una canción se comparte solo con lo necesario (artistas en lista → texto)', () {
      final p = Grupos.pistaParaGrupo({
        'video_id': 'kJQP7kiw5Fk', 'titulo': 'Despacito', 'miniatura': 'https://i.ytimg.com/x.jpg', 'duracion': 282.4,
        'artistas': [{'nombre': 'Luis Fonsi'}, {'nombre': 'Daddy Yankee'}], 'clave': 'yt:kJQP7kiw5Fk', 'letra': 'mucho',
      });
      expect(p, {
        'video_id': 'kJQP7kiw5Fk', 'titulo': 'Despacito', 'artista': 'Luis Fonsi, Daddy Yankee',
        'miniatura': 'https://i.ytimg.com/x.jpg', 'duracion': '282',
      });
    });

    test('vista previa del último mensaje', () {
      expect(Grupo.desde(_grupo(ultimo: {'nombre': 'Ana', 'texto': 'hola', 'pista': false, 'audio': false})).ultimoTexto, 'Ana: hola');
      expect(Grupo.desde(_grupo(ultimo: {'usuario': 'beto', 'audio': true})).ultimoTexto, 'beto: 🎤 Nota de voz');
      expect(Grupo.desde(_grupo(ultimo: {'nombre': 'Eva', 'pista': true})).ultimoTexto, 'Eva: ♪ Una canción');
    });

    test('roles y código', () {
      final g = Grupo.desde(_grupo(tipo: 'privado', rol: 'moderador', codigo: 'ABCD2345'));
      expect(g.privado && g.modero && g.dentro, isTrue);
      expect(g.codigo, 'ABCD2345');
      expect(Grupo.desde(_grupo(rol: null)).dentro, isFalse);
    });

    test('mensajes del más viejo al más nuevo y la nota de voz con su duración', () async {
      final n = _Sesion()..mensajes = [_mensaje(1), _mensaje(2, audio: 'g1/x/1.m4a', seg: 12)];
      final l = await Grupos(n).mensajes('g1');
      expect(l.map((m) => m.id), [1, 2]);
      expect(l[1].audio, 'g1/x/1.m4a');
      expect(l[1].audioSeg, 12);
    });

    test('enviar nota de voz: la duración va recortada a 3 minutos', () async {
      final n = _Sesion();
      await Grupos(n).enviar('g1', audio: 'g1/yo/1.m4a', audioSeg: 999);
      final (nombre, c) = n.llamadas.last;
      expect(nombre, 'grupo_enviar');
      expect(c['p_audio_seg'], 180);
      expect(c['p_pista'], isNull);
    });

    test('la nota de voz se sube a la carpeta del grupo y de la cuenta', () async {
      final n = _SubidaFalsa();
      final ruta = await Grupos(n).subirAudio('g1', [1, 2, 3], 'audio/mp4');
      expect(ruta, startsWith('g1/yo/'));
      expect(ruta, endsWith('.m4a'));
      expect(n.subidas.single, ('audios-grupos', ruta, 'audio/mp4'));
      expect(await Grupos(n).subirAudio('g1', [1], 'audio/webm'), endsWith('.webm'));
    });

    test('los errores de la base salen en lenguaje normal', () {
      expect(Nube.traducirSocial('vas muy rápido; espera unos segundos'), 'Vas muy rápido. Espera unos segundos.');
      expect(Nube.traducirSocial('esa canción no se puede compartir'), 'Esa canción no se puede compartir.');
      expect(Nube.traducirSocial('te sacaron de este grupo; no puedes volver a entrar'),
          'Te sacaron de este grupo y no puedes volver a entrar.');
    });
  });

  group('pantallas', () {
    testWidgets('sin grupos: invita a explorar o crear, con los tres botones', (t) async {
      await _montar(t, const GruposVista());
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Crear grupo'), findsOneWidget);
      expect(find.text('Explorar'), findsOneWidget);
      expect(find.text('Tengo un código'), findsOneWidget);
      expect(find.textContaining('Aún no estás en ningún grupo'), findsOneWidget);
    });

    testWidgets('a quien ya tenía cuenta privada se le pregunta UNA vez si la hace pública', (t) async {
      final s = await _servicios();
      _nube.miFila = {'nombre': 'Yo', 'perfil_publico': false, 'fecha_nacimiento': '1990-01-01'};
      await _montar(t, const GruposVista(), s: s);
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('¿Hacemos público tu perfil?'), findsOneWidget);
      await t.ensureVisible(find.text('Hacerlo público'));
      await t.tap(find.text('Hacerlo público'));
      for (var i = 0; i < 5; i++) {
        await t.pump(const Duration(milliseconds: 100));
      }
      expect(_nube.llamadas.any((l) => l.$1 == 'perfiles?id=eq.yo' && l.$2['perfil_publico'] == true), isTrue);
      expect(find.text('¿Hacemos público tu perfil?'), findsNothing);
      // la próxima vez ya no se pregunta
      await t.pumpWidget(const SizedBox());
      _nube.miFila = {'nombre': 'Yo', 'perfil_publico': false, 'fecha_nacimiento': '1990-01-01'};
      await _montar(t, const GruposVista(), s: s);
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('¿Hacemos público tu perfil?'), findsNothing);
      await t.pump(const Duration(seconds: 5));
    });

    testWidgets('a un menor no se le ofrece', (t) async {
      final s = await _servicios();
      _nube.miFila = {'nombre': 'Yo', 'perfil_publico': false, 'fecha_nacimiento': '2013-01-01'};
      await _montar(t, const GruposVista(), s: s);
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('¿Hacemos público tu perfil?'), findsNothing);
    });

    testWidgets('mis grupos con su último mensaje y los sin leer', (t) async {
      final s = await _servicios();
      _nube.mios = [_grupo(sinLeer: 3, ultimo: {'nombre': 'Ana', 'texto': 'quién va al concierto', 'pista': false, 'audio': false}),
        _grupo(id: 'g2', nombre: 'Primos', tipo: 'privado')];
      await _montar(t, const GruposVista(), s: s);
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Reggaetón Lima'), findsOneWidget);
      expect(find.text('Ana: quién va al concierto'), findsOneWidget);
      expect(find.text('3'), findsOneWidget);
      expect(find.byIcon(Icons.lock_rounded), findsOneWidget);
    });

    testWidgets('crear un grupo privado manda el tipo y avisa que no hay imágenes ni videos', (t) async {
      final s = await _servicios();
      await _montar(t, const GruposVista(), s: s);
      await t.tap(find.text('Crear grupo'));
      await t.pumpAndSettle();
      expect(find.textContaining('No se pueden enviar imágenes ni videos'), findsOneWidget);
      await t.enterText(find.byType(TextField).first, 'Primos');
      await t.tap(find.text('Privado'));
      await t.pump();
      expect(find.textContaining('Solo entra quien tenga el código'), findsOneWidget);
      await t.tap(find.text('Crear'));
      await t.pump(const Duration(milliseconds: 300));
      final crear = _nube.llamadas.firstWhere((l) => l.$1 == 'grupo_crear').$2;
      expect(crear['p_nombre'], 'Primos');
      expect(crear['p_tipo'], 'privado');
      await t.pump(const Duration(seconds: 1));
    });

    testWidgets('la conversación: nombres de quien escribe, enviar texto y el micrófono', (t) async {
      final s = await _servicios();
      _nube.mensajes = [
        _mensaje(1, autor: 'ana', texto: 'Hola gente', rol: 'dueno'),
        _mensaje(2, autor: 'ana', texto: 'Qué escuchan'),
        _mensaje(3, autor: 'beto', pista: {'video_id': 'kJQP7kiw5Fk', 'titulo': 'Despacito', 'artista': 'Luis Fonsi', 'miniatura': ''}),
        _mensaje(4, autor: 'beto', audio: 'g1/b/1.m4a', seg: 65, texto: ''),
      ];
      await _montar(t, GrupoPagina(grupo: Grupo.desde(_grupo())), s: s);
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('ANA · dueño'), findsOneWidget);           // el nombre solo una vez por tanda
      expect(find.text('Despacito'), findsOneWidget);
      expect(find.text('🎤 1:05'), findsOneWidget);
      // sin texto escrito se ofrece grabar; con texto, enviar
      expect(find.byTooltip('Grabar una nota de voz'), findsOneWidget);
      await t.enterText(find.byType(TextField), 'Yo voy');
      await t.pump();
      expect(find.byTooltip('Enviar'), findsOneWidget);
      await t.tap(find.byTooltip('Enviar'));
      await t.pump(const Duration(milliseconds: 300));
      expect(_nube.llamadas.any((l) => l.$1 == 'grupo_enviar' && l.$2['p_texto'] == 'Yo voy'), isTrue);
      expect(find.text('Yo voy'), findsOneWidget);
      // no hay ningún botón para imágenes ni videos
      expect(find.byIcon(Icons.image_rounded), findsNothing);
      expect(find.byIcon(Icons.photo_camera_rounded), findsNothing);
      expect(find.byIcon(Icons.videocam_rounded), findsNothing);
      await t.pumpWidget(const SizedBox());
      await t.pump(const Duration(seconds: 4));
    });

    testWidgets('mantener un mensaje ajeno: reportar con motivo', (t) async {
      final s = await _servicios();
      _nube.mensajes = [_mensaje(7, autor: 'ana', texto: 'algo feo')];
      await _montar(t, GrupoPagina(grupo: Grupo.desde(_grupo())), s: s);
      await t.pump(const Duration(milliseconds: 300));
      await t.longPress(find.text('algo feo'));
      await t.pumpAndSettle();
      expect(find.text('Borrar'), findsNothing);                 // un miembro no borra lo ajeno
      expect(find.text('Fijar arriba'), findsNothing);
      await t.tap(find.text('Reportar'));
      await t.pumpAndSettle();
      await t.tap(find.text('Insulta o acosa'));
      await t.pump(const Duration(milliseconds: 300));
      final rep = _nube.llamadas.firstWhere((l) => l.$1 == 'grupo_reportar').$2;
      expect(rep, {'p_mensaje': 7, 'p_motivo': 'Insulta o acosa'});
      await t.pumpWidget(const SizedBox());
      await t.pump(const Duration(seconds: 4));
    });

    testWidgets('quien modera ve fijar, ocultar y borrar', (t) async {
      final s = await _servicios();
      _nube.mensajes = [_mensaje(8, autor: 'ana', texto: 'spam')];
      await _montar(t, GrupoPagina(grupo: Grupo.desde(_grupo(rol: 'moderador'))), s: s);
      await t.pump(const Duration(milliseconds: 300));
      await t.longPress(find.text('spam'));
      await t.pumpAndSettle();
      expect(find.text('Fijar arriba'), findsOneWidget);
      expect(find.text('Ocultar'), findsOneWidget);
      expect(find.text('Borrar'), findsOneWidget);
      await t.tap(find.text('Borrar'));
      await t.pump(const Duration(milliseconds: 300));
      expect(_nube.llamadas.any((l) => l.$1 == 'grupo_mensaje_accion' && l.$2['p_accion'] == 'borrar'), isTrue);
      expect(find.text('spam'), findsNothing);
      await t.pumpWidget(const SizedBox());
      await t.pump(const Duration(seconds: 4));
    });

    for (final tam in const [Size(320, 568), Size(360, 640)]) {
      testWidgets('nada se desborda a ${tam.width.toInt()}x${tam.height.toInt()}', (t) async {
        final s = await _servicios();
        _nube.miFila = {'nombre': 'Yo', 'perfil_publico': false, 'fecha_nacimiento': '1990-01-01'};
        _nube.mios = [_grupo(nombre: 'Un grupo con un nombre larguísimo para ver si se corta bien', sinLeer: 120,
            ultimo: {'nombre': 'Alguien con nombre largo', 'texto': 'un mensaje también bastante largo para la vista previa'})];
        await _montar(t, const GruposVista(), s: s, tam: tam);
        await t.pump(const Duration(milliseconds: 300));
        expect(t.takeException(), isNull);
        expect(find.text('99+'), findsOneWidget);
        await t.pumpWidget(const SizedBox());
        _nube.mensajes = [
          _mensaje(1, autor: 'alguien_con_usuario_largo', texto: 'Un mensaje largo ' * 12, rol: 'moderador'),
          _mensaje(2, autor: 'beto', pista: {'video_id': 'kJQP7kiw5Fk', 'titulo': 'Un título de canción larguísimo ' * 3,
              'artista': 'Artista larga ' * 4, 'miniatura': ''}),
          _mensaje(3, autor: 'beto', audio: 'g/b/1.m4a', seg: 179, texto: ''),
        ];
        await _montar(t, GrupoPagina(grupo: Grupo.desde(_grupo(nombre: 'Nombre de grupo muy muy largo de verdad'))), s: s, tam: tam);
        await t.pump(const Duration(milliseconds: 300));
        expect(t.takeException(), isNull);
        await t.pumpWidget(const SizedBox());
        await t.pump(const Duration(seconds: 4));
      });
    }

    testWidgets('info del grupo privado: el código para invitar y la gente', (t) async {
      final s = await _servicios();
      _nube.verGrupo = _grupo(tipo: 'privado', rol: 'dueno', codigo: 'ABCD2345');
      await _montar(t, GrupoInfoPagina(grupo: Grupo.desde(_grupo(tipo: 'privado', rol: 'dueno', codigo: 'ABCD2345'))), s: s);
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('ABCD2345'), findsOneWidget);
      expect(find.text('Ana'), findsOneWidget);
      expect(find.text('Borrar el grupo'), findsOneWidget);
    });
  });
}

class _SubidaFalsa extends _Sesion {
  final subidas = <(String, String, String)>[];
  @override
  Future<void> subir(String bucket, String ruta, List<int> bytes, String tipo,
      {bool reemplazar = false, void Function(double)? alAvanzar}) async {
    subidas.add((bucket, ruta, tipo));
  }
}
