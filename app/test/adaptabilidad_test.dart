// Adaptabilidad: cada pantalla que se puede armar sin la nube se monta a todos
// los tamaños (teléfonos pequeños y largos, plegable, tablets, horizontal, web)
// con el texto del sistema al máximo que permite la app (1.2) y NO debe dar
// ningún desborde («A RenderFlex overflowed») ni error de diseño.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/cuentas.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/legal.dart';
import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/social.dart';
import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/novedades_grandes.dart';
import 'package:caudal/ui/paginas/acceso.dart';
import 'package:caudal/ui/paginas/ajustes_pagina.dart';
import 'package:caudal/ui/paginas/amigos_pagina.dart';
import 'package:caudal/ui/paginas/compartir_letra.dart';
import 'package:caudal/ui/paginas/directorio_pagina.dart';
import 'package:caudal/ui/paginas/legal_pagina.dart';
import 'package:caudal/ui/paginas/mezclador_pagina.dart';
import 'package:caudal/ui/paginas/perfil_comun.dart';
import 'package:caudal/ui/paginas/resumen.dart';
import 'package:caudal/ui/paginas/subir_musica_pagina.dart';
import 'package:caudal/ui/servicios.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _tamanos = <String, Size>{
  'telefono 320x568': Size(320, 568),
  'telefono 360x640': Size(360, 640),
  'telefono largo 412x915': Size(412, 915),
  'plegable cerrado 280x653': Size(280, 653),
  'plegable abierto 673x841': Size(673, 841),
  'tablet 800x1280': Size(800, 1280),
  'tablet horizontal 1280x800': Size(1280, 800),
  'telefono horizontal 915x412': Size(915, 412),
  'web 1440x900': Size(1440, 900),
};

class _ReproductorFalso extends ChangeNotifier implements Reproductor {
  @override
  Json? actual;
  @override
  List<Json> proximas = [];
  @override
  List<Json> get siguientesDeContexto => [];
  @override
  bool get puedeEstirarTiempo => true;
  @override
  bool get puedeFiltrar => true;
  @override
  bool get puedeEco => false;
  @override
  Future<void> dispose() async => super.dispose();
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ColeccionFalsa extends ChangeNotifier implements Coleccion {
  @override
  Future<dynamic> estado(String clave) async => null;
  @override
  Future<void> guardarEstado(String clave, Object? valor) async {}
  @override
  Future<List<Json>> listaMeGusta() async => [];
  @override
  Future<List<Json>> listas() async => [];
  @override
  bool meGusta(String? clave) => false;
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _StreamsFalsos implements Streams {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _DescargasFalsas extends ChangeNotifier implements GestorDescargas {
  @override
  List<Descarga> get lista => const [];
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// Monta [crear] a [tam] con texto 1.2 y devuelve los desbordes/errores vistos.
Future<List<String>> _probar(WidgetTester t, Size tam, Widget Function() crear,
    {Future<void> Function(WidgetTester)? despues, bool conServicios = true}) async {
  SharedPreferences.setMockInitialValues({});
  final errores = <String>[];
  final anterior = FlutterError.onError;
  FlutterError.onError = (d) {
    final txt = d.toDiagnosticsNode().toStringDeep(minLevel: DiagnosticLevel.fine);
    final donde = RegExp(r'(?:file:///|package:caudal/)[^\s]*(?:lib/)?[^\s]*\.dart:\d+:\d+').firstMatch(txt)?.group(0) ?? '';
    errores.add('${d.exceptionAsString().split('\n').first} @ $donde');
  };

  t.view.physicalSize = tam * 2;
  t.view.devicePixelRatio = 2;
  addTearDown(t.view.reset);

  Widget app = MaterialApp(
    theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory),
    builder: (ctx, hijo) => MediaQuery(
      data: MediaQuery.of(ctx).copyWith(textScaler: const TextScaler.linear(1.2)),
      child: hijo!,
    ),
    home: crear(),
  );
  if (conServicios) {
    final s = Servicios(
      cuenta: Cuenta(id: 'prueba', usuario: 'prueba', nombre: 'Prueba'),
      ajustes: await Ajustes.cargar('prueba'),
      coleccion: _ColeccionFalsa(),
      reproductor: _ReproductorFalso(),
      streams: _StreamsFalsos(),
      descargas: _DescargasFalsas(),
      cerrarSesion: () async {},
    );
    app = Caudal(s: s, child: app);
  }
  await t.pumpWidget(app);
  await t.pump(const Duration(milliseconds: 600));
  if (despues != null) await despues(t);
  await t.pump(const Duration(milliseconds: 900));
  final ex = t.takeException();
  if (ex != null) errores.add('$ex'.split('\n').first);
  // desmonta para soltar temporizadores/animaciones
  await t.pumpWidget(const SizedBox());
  await t.pump(const Duration(seconds: 1));
  t.takeException();
  FlutterError.onError = anterior;
  return errores;
}

void _pantalla(String nombre, Widget Function() crear,
    {Future<void> Function(WidgetTester)? despues, bool conServicios = true}) {
  for (final e in _tamanos.entries) {
    testWidgets('$nombre a ${e.key}', (t) async {
      final errores = await _probar(t, e.value, crear, despues: despues, conServicios: conServicios);
      expect(errores, isEmpty, reason: errores.join('\n'));
    });
  }
}

Json _pista(int i) => {
      'tipo': 'pista', 'clave': 'yt:id$i', 'video_id': 'id$i',
      'titulo': 'Una canción con un título bastante largo número $i',
      'artista': 'Artista con nombre muy largo $i', 'miniatura': '', 'duracion': 200,
    };

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  _pantalla('Acceso (crear cuenta)', () => AccesoPagina(alEntrar: (_, _) async {}), conServicios: false);

  _pantalla('Términos', () => const LegalPagina(nombre: 'terminos'), conServicios: false);
  _pantalla('Privacidad', () => const LegalPagina(nombre: 'privacidad'), conServicios: false);

  _pantalla(
    'Antes de seguir',
    () => AceptarTerminosPagina(
      sesion: Sesion('u1', 'a', 'r', DateTime(2030)),
      perfil: PerfilLegal(nombre: 'Kevin Pérez'),
      alSalir: () {},
    ),
    conServicios: false,
  );

  _pantalla(
    'Resumen (Wrapped)',
    () => ResumenPagina(historial: [
      for (var i = 0; i < 12; i++)
        for (var k = 0; k < 12 - i; k++) Escucha(_pista(i), DateTime.now().subtract(Duration(days: 1, minutes: k)))
    ]),
    despues: (t) async {
      // recorre todas las historias
      for (var i = 0; i < 6; i++) {
        await t.tapAt(Offset(t.view.physicalSize.width / t.view.devicePixelRatio - 20,
            t.view.physicalSize.height / t.view.devicePixelRatio / 2));
        await t.pump(const Duration(milliseconds: 1600));
      }
    },
  );

  _pantalla(
    'Compartir letra (hoja)',
    () => Builder(
      builder: (ctx) => Scaffold(
        body: TextButton(
          onPressed: () => compartirLetra(ctx,
              pista: _pista(1),
              lineas: [for (var i = 0; i < 20; i++) 'Línea de la letra número $i con bastante texto para que se parta'],
              color: Colors.purple,
              lineaActual: 2),
          child: const Text('abrir'),
        ),
      ),
    ),
    despues: (t) async {
      await t.tap(find.text('abrir'));
      await t.pump(const Duration(milliseconds: 600));
    },
  );

  _pantalla(
    'Perfil: piezas comunes',
    () => Scaffold(
      body: ListView(children: [
        const FondoBanner(color: Colors.teal),
        const AvatarPerfil(nombre: 'Kevin Pérez Con Un Nombre Largo', radio: 50),
        const DistincionesPerfil(
          titulos: [
            TituloEspecial(clave: 'a', nombre: 'Titulo especial muy largo de prueba'),
            TituloEspecial(clave: 'b', nombre: 'Otro título')
          ],
          fundador: true,
          numero: 17,
          artista: true,
        ),
        Center(child: SizedBox(width: 240, height: 372, child: TarjetaPerfil(
          perfil: const PerfilTarjeta(
              id: '1',
              usuario: 'un_usuario_con_nombre_larguisimo',
              nombre: 'Nombre Completo De Una Persona Con Muchas Palabras',
              bio: 'Una descripción bastante larga para ver cómo se parte en varias líneas dentro de la tarjeta.',
              fundador: true,
              esArtista: true,
              likes: 12345,
              titulos: [TituloEspecial(clave: 'a', nombre: 'Titulo especial muy largo de prueba')]),
          alAbrir: () {},
          alLike: () {},
          alAmistad: () {},
        ))),
      ]),
    ),
    conServicios: false,
  );

  _pantalla('Directorio (sin conexión)', () => const DirectorioPagina());
  _pantalla('Amigos (sin conexión)', () => const AmigosPagina(pestana: 0));
  _pantalla('Amigos, pestaña Amigos', () => const AmigosPagina(pestana: 1));
  _pantalla('Subir música', () => const SubirMusicaPagina());
  _pantalla('Mezclador', () => const MezcladorPagina());
  _pantalla('Ajustes', () => const AjustesPagina(), despues: (t) async {
    final lista = find.byType(Scrollable).first;
    for (var i = 0; i < 12; i++) {
      await t.drag(lista, const Offset(0, -400));
      await t.pump(const Duration(milliseconds: 100));
    }
  });
  _pantalla('Novedades grandes', () => const NovedadesGrandes());
}
