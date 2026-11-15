import 'package:caudal/nucleo/version.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('comparar versiones', () {
    test('una version mayor gana', () {
      expect(hayNovedad('1.2.0', '1.3.0'), isTrue);
      expect(hayNovedad('1.2.0', '2.0.0'), isTrue);
    });

    test('la misma version no es novedad', () {
      expect(hayNovedad('1.3.0', '1.3.0'), isFalse);
    });

    test('una version anterior no es novedad', () {
      expect(hayNovedad('1.3.0', '1.2.9'), isFalse);
      expect(hayNovedad('2.0.0', '1.9.9'), isFalse);
    });

    test('compara numeros, no texto', () {
      // como texto, "1.9" pareceria mayor que "1.10"
      expect(hayNovedad('1.9.0', '1.10.0'), isTrue);
      expect(hayNovedad('1.10.0', '1.9.0'), isFalse);
    });

    test('acepta la v delante', () {
      expect(hayNovedad('1.2.0', 'v1.3.0'), isTrue);
      expect(hayNovedad('v1.3.0', 'v1.3.0'), isFalse);
    });

    test('versiones con distinto numero de partes', () {
      expect(hayNovedad('1.3', '1.3.1'), isTrue);
      expect(hayNovedad('1.3.0', '1.3'), isFalse);
    });

    test('no revienta con basura', () {
      expect(hayNovedad('', ''), isFalse);
      expect(hayNovedad('1.3.0', 'sin numeros'), isFalse);
    });
  });

  group('novedad', () {
    test('sin apk no se puede instalar', () {
      const n = Novedad(version: '2.0', notas: '', apk: '', pagina: '', peso: 0);
      expect(n.sePuedeInstalar, isFalse);
    });
  });

  test('la version y el origen son los de Caudal_AI', () {
    expect(versionApp, '2.1.1');
    expect(origen, 'alideveloper67/Caudal_AI');
  });

  test('solo ve las versiones del movil, la mas alta', () {
    final r = elegirRelease([
      {'tag_name': 'escritorio-v9.0.0'},
      {'tag_name': 'movil-v2.0.5'},
      {'tag_name': 'movil-v2.0.10'},
      {'tag_name': 'movil-v3.0.0', 'draft': true},
      {'tag_name': 'movil-v4.0.0', 'prerelease': true},
    ]);
    expect(r?['tag_name'], 'movil-v2.0.10');
    expect(elegirRelease([{'tag_name': 'escritorio-v1.0.0'}]), isNull);
  });

  test('elige el APK de la arquitectura del telefono', () {
    final adjuntos = [
      {'name': 'Caudal-armeabi-v7a.apk', 'browser_download_url': 'v7'},
      {'name': 'Caudal-arm64-v8a.apk', 'browser_download_url': 'v8'},
      {'name': 'notas.txt'},
    ];
    expect(elegirApk(adjuntos, 'arm64')?['browser_download_url'], 'v8');
    expect(elegirApk(adjuntos, 'arm')?['browser_download_url'], 'v7');
    expect(elegirApk([{'name': 'Caudal.apk', 'browser_download_url': 'u'}, ...adjuntos], 'x64')
        ?['browser_download_url'], 'u');
    expect(elegirApk([{'name': 'notas.txt'}], 'arm64'), isNull);
    expect(abiDelTelefono(), isNotEmpty);
  });
}
