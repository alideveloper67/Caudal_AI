// Avisar de versiones nuevas y, en Android, instalarlas sin salir de la app.
//
// Las versiones se publican como releases de GitHub. Cada una lleva adjunto el
// APK. Para cambiar donde se publica basta con tocar [origen].
//
// En iPhone no se puede instalar nada desde dentro de una app (Apple no lo
// permite): se avisa igual de la version nueva y se ofrece su pagina, desde
// donde se baja e instala como se instalo la primera vez.

import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import 'plataforma.dart';

/// Version que lleva esta copia. Sube tambien la de pubspec.yaml al publicar.
const String versionApp = '2.0.1';

/// usuario/repositorio de GitHub donde se publican las versiones
const String origen = 'alideveloper67/Caudal_AI';

/// El mismo repositorio publica el escritorio y el movil: esta app solo hace
/// caso a las versiones con su etiqueta (movil-v2.0.1).
const String prefijo = 'movil-v';

const String _api = 'https://api.github.com/repos/$origen/releases?per_page=40';

/// La version mas alta del movil (sin borradores, pruebas ni las del escritorio).
Map<String, dynamic>? elegirRelease(List publicadas) {
  final candidatas = publicadas
      .whereType<Map>()
      .where((r) => r['draft'] != true && r['prerelease'] != true &&
          '${r['tag_name'] ?? ''}'.startsWith(prefijo))
      .toList();
  if (candidatas.isEmpty) return null;
  String v(Map r) => '${r['tag_name']}'.substring(prefijo.length);
  // la mas alta: si b es novedad respecto de a, gana b
  final mejor = candidatas.reduce((a, b) => hayNovedad(v(a), v(b)) ? b : a);
  return Map<String, dynamic>.from(mejor);
}

class Novedad {
  final String version;
  final String notas;
  final String apk;
  final String pagina;
  final int peso;

  /// En iPhone, el .ipa adjunto (se instala por sideload, nunca desde la app).
  final String ipa;

  const Novedad({
    required this.version,
    required this.notas,
    required this.apk,
    required this.pagina,
    required this.peso,
    this.ipa = '',
  });

  /// En iPhone no se puede instalar desde dentro: Apple no lo permite.
  bool get sePuedeInstalar => Plataforma.esAndroid && apk.isNotEmpty;

  /// Lo que hay que abrir para ver o bajar la version: en iPhone, su pagina.
  String get enlace => sePuedeInstalar ? apk : pagina;
}

/// '1.10.0' -> [1, 10, 0]. Compara numero a numero, no como texto: si no,
/// la 1.9.0 pareceria mas nueva que la 1.10.0.
List<int> _numeros(String v) {
  final hallados = RegExp(r'\d+').allMatches(v).map((m) => int.parse(m.group(0)!));
  final lista = hallados.take(4).toList();
  return lista.isEmpty ? [0] : lista;
}

bool hayNovedad(String instalada, String publicada) {
  final a = _numeros(instalada);
  final b = _numeros(publicada);
  for (var i = 0; i < 4; i++) {
    final x = i < a.length ? a[i] : 0;
    final y = i < b.length ? b[i] : 0;
    if (y != x) return y > x;
  }
  return false;
}

/// Pregunta a GitHub si hay algo mas nuevo. Devuelve null si ya estas al dia
/// o si no se pudo comprobar: quedarse callado es mejor que dar un error.
Future<Novedad?> buscarActualizacion({Duration espera = const Duration(seconds: 12)}) async {
  try {
    final dio = Dio(BaseOptions(
      connectTimeout: espera,
      receiveTimeout: espera,
      headers: {'User-Agent': 'Caudal', 'Accept': 'application/vnd.github+json'},
      responseType: ResponseType.plain,
    ));
    final r = await dio.get(_api);
    if (r.statusCode != 200) return null;
    return novedadDe(jsonDecode(r.data as String) as List);
  } catch (_) {
    return null;
  }
}

/// La novedad que toca avisar segun las releases publicadas, o null.
///
/// En Android hace falta el APK de su arquitectura para ofrecerla. En iPhone
/// no se instala nada desde aqui: basta con que haya version nueva, y se da
/// su pagina para abrirla.
Novedad? novedadDe(List publicadas, {bool? ios, String? abi}) {
  final esIOS = ios ?? Plataforma.esIOS;
  final datos = elegirRelease(publicadas);
  if (datos == null) return null;
  final etiqueta = '${datos['tag_name']}'.substring(prefijo.length);
  if (!hayNovedad(versionApp, etiqueta)) return null;

  var pagina = (datos['html_url'] ?? '').toString();
  if (pagina.isEmpty) {
    pagina = 'https://github.com/$origen/releases/tag/${datos['tag_name']}';
  }
  final notas = (datos['body'] ?? '').toString().trim();

  if (esIOS) {
    final ipa = (datos['assets'] as List? ?? const []).whereType<Map>()
        .where((a) => '${a['name'] ?? ''}'.toLowerCase().endsWith('.ipa'))
        .map((a) => '${a['browser_download_url'] ?? ''}')
        .firstOrNull ?? '';
    return Novedad(version: etiqueta, notas: notas, apk: '', pagina: pagina, peso: 0, ipa: ipa);
  }

  final elegido = elegirApk(datos['assets'] as List? ?? const [], abi ?? abiDelTelefono());
  final apk = '${elegido?['browser_download_url'] ?? ''}';
  if (apk.isEmpty) return null;
  return Novedad(
    version: etiqueta,
    notas: notas,
    apk: apk,
    pagina: pagina,
    peso: (elegido?['size'] as num?)?.toInt() ?? 0,
  );
}

/// Trae el APK nuevo y lo deja listo para instalar. Devuelve su ruta.
Future<String> descargarApk(
  Novedad novedad, {
  void Function(double)? alProgresar,
  CancelToken? cancelar,
}) async {
  if (!novedad.sePuedeInstalar) {
    throw UnsupportedError('Esta version no se puede instalar desde la app.');
  }
  final carpeta = await getTemporaryDirectory();
  final destino = '${carpeta.path}/Caudal-${novedad.version}.apk';

  final ya = File(destino);
  if (await ya.exists() && novedad.peso > 0 && await ya.length() == novedad.peso) {
    alProgresar?.call(100);
    return destino;                      // ya estaba bajado entero
  }

  await Dio().download(
    novedad.apk,
    destino,
    cancelToken: cancelar,
    options: Options(headers: {'User-Agent': 'Caudal'}),
    onReceiveProgress: (hecho, total) {
      if (total > 0) alProgresar?.call(hecho / total * 100);
    },
  );
  return destino;
}

/// Lanza el instalador de Android. El sistema pide permiso la primera vez.
///
/// En iPhone no hay instalador al que llamar: se dice y no se intenta.
Future<String?> instalar(String rutaApk) async {
  if (!Plataforma.esAndroid) {
    return 'En iPhone la version nueva se instala desde su pagina, no desde la app.';
  }
  final r = await OpenFilex.open(rutaApk, type: 'application/vnd.android.package-archive');
  if (r.type == ResultType.done) return null;
  if (r.type == ResultType.permissionDenied) {
    return 'Android necesita tu permiso para instalar. Activalo en los ajustes '
        'del telefono, en "Instalar apps desconocidas".';
  }
  return 'No se pudo abrir el instalador: ${r.message}';
}

/// La arquitectura del telefono, tal como la ve el propio Dart ("arm64", "arm", "x64").
String abiDelTelefono() {
  final m = RegExp(r'on "\w+_(\w+)"').firstMatch(Platform.version);
  return m?.group(1) ?? 'arm64';
}

/// El APK que toca: el de su arquitectura; si no esta, el universal; si no, cualquiera.
Map? elegirApk(List adjuntos, String abi) {
  final apks = adjuntos.whereType<Map>()
      .where((a) => '${a['name'] ?? ''}'.toLowerCase().endsWith('.apk')).toList();
  if (apks.isEmpty) return null;
  final marca = switch (abi) { 'arm64' => 'arm64-v8a', 'arm' => 'armeabi-v7a', 'x64' => 'x86_64', _ => abi };
  bool tiene(Map a, String t) => '${a['name']}'.toLowerCase().contains(t);
  final otras = ['arm64-v8a', 'armeabi-v7a', 'x86_64'].where((x) => x != marca);
  return apks.where((a) => tiene(a, marca)).firstOrNull ??
      apks.where((a) => !otras.any((o) => tiene(a, o))).firstOrNull ??
      apks.first;
}
