import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/descargas.dart';
import 'package:caudal/nucleo/navegador_caudal.dart';
import 'package:caudal/nucleo/plataforma.dart';
import 'package:caudal/nucleo/version.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  tearDown(() => Plataforma.forzada = null);

  final publicadas = [
    {'tag_name': 'escritorio-v9.0.0', 'html_url': 'https://x/escritorio'},
    {
      'tag_name': 'movil-v9.1.0',
      'html_url': 'https://github.com/alideveloper67/Caudal_AI/releases/tag/movil-v9.1.0',
      'body': ' notas ',
      'assets': [
        {'name': 'Caudal-9.1.0.ipa', 'browser_download_url': 'ipa-url'},
      ],
    },
  ];

  group('version en iPhone', () {
    test('avisa de la version nueva aunque no traiga APK, con su pagina', () {
      Plataforma.forzada = TargetPlatform.iOS;
      final n = novedadDe(publicadas);
      expect(n, isNotNull);
      expect(n!.version, '9.1.0');
      expect(n.notas, 'notas');
      expect(n.sePuedeInstalar, isFalse);
      expect(n.pagina, contains('movil-v9.1.0'));
      expect(n.enlace, n.pagina);
      expect(n.ipa, 'ipa-url');
    });

    test('sin html_url arma la pagina de la release', () {
      final n = novedadDe([{'tag_name': 'movil-v9.0.0'}], ios: true);
      expect(n?.pagina, 'https://github.com/$origen/releases/tag/movil-v9.0.0');
    });

    test('aunque haya APK, en iPhone no se instala', () {
      Plataforma.forzada = TargetPlatform.iOS;
      const n = Novedad(version: '9', notas: '', apk: 'a.apk', pagina: 'p', peso: 1);
      expect(n.sePuedeInstalar, isFalse);
      expect(n.enlace, 'p');
    });

    test('instalar no lanza nada en iPhone', () async {
      Plataforma.forzada = TargetPlatform.iOS;
      expect(await instalar('x.apk'), isNotNull);
    });

    test('al dia no hay novedad', () {
      expect(novedadDe([{'tag_name': 'movil-v$versionApp'}], ios: true), isNull);
    });
  });

  group('version en Android', () {
    test('sin APK no se avisa', () {
      expect(novedadDe(publicadas, ios: false, abi: 'arm64'), isNull);
    });

    test('con APK se puede instalar', () {
      Plataforma.forzada = TargetPlatform.android;
      final n = novedadDe([
        {
          'tag_name': 'movil-v9.2.0',
          'html_url': 'pag',
          'assets': [
            {'name': 'Caudal-arm64-v8a.apk', 'browser_download_url': 'v8', 'size': 10},
          ],
        }
      ], abi: 'arm64');
      expect(n?.apk, 'v8');
      expect(n?.peso, 10);
      expect(n?.sePuedeInstalar, isTrue);
      expect(n?.enlace, 'v8');
    });
  });

  group('almacenamiento', () {
    test('en iPhone no se pide permiso ni hay carpeta publica', () async {
      Plataforma.forzada = TargetPlatform.iOS;
      expect(await GestorDescargas.pedirPermisoAlmacenamiento(), isTrue);
      expect(GestorDescargas.hayCarpetaPublica, isFalse);
      expect(Ajustes.hayGuardarEnPublico, isFalse);
    });

    test('en iPhone "guardar en la musica" queda apagado', () async {
      SharedPreferences.setMockInitialValues({});
      final a = await Ajustes.cargar('prueba');
      await a.poner('guardar_publico', true);
      Plataforma.forzada = TargetPlatform.iOS;
      expect(a.guardarEnPublico, isFalse);
      Plataforma.forzada = TargetPlatform.android;
      expect(a.guardarEnPublico, isTrue);
      expect(GestorDescargas.hayCarpetaPublica, isTrue);
    });

    test('recoloca rutas de otra instalacion del iPhone', () {
      const ahora = '/var/mobile/Containers/Data/Application/NUEVO/Documents';
      expect(
        recolocarRuta('/var/mobile/Containers/Data/Application/VIEJO/Documents/Musica/a.mp3', ahora),
        '$ahora/Musica/a.mp3',
      );
      expect(recolocarRuta('$ahora/Videos/b.mp4', ahora), '$ahora/Videos/b.mp4');
      expect(recolocarRuta('/otra/ruta/c.mp3', ahora), '/otra/ruta/c.mp3');
      expect(recolocarRuta('', ahora), '');
    });
  });

  test('el navegador se presenta como Safari en iPhone y Chrome en Android', () {
    Plataforma.forzada = TargetPlatform.iOS;
    expect(agenteCaudal, contains('iPhone'));
    expect(agenteDelTelefono, agenteCaudal);
    Plataforma.forzada = TargetPlatform.android;
    expect(agenteCaudal, contains('Android'));
  });
}
