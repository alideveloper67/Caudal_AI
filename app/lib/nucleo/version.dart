import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/services.dart' show appFlavor;
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

import 'package:crypto/crypto.dart' show sha256;
import 'package:dio/dio.dart';
import 'package:open_filex/open_filex.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:path_provider/path_provider.dart';

import 'plataforma.dart';

/// Version que lleva esta copia. Sube tambien la de pubspec.yaml al publicar.
const String versionApp = '2.7.7';

/// Instalada desde una tienda (variante "play" de Android): las versiones
/// nuevas llegan por la tienda, no por la propia app.
bool get actualizaLaTienda => kIsWeb || appFlavor == 'play';

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

  /// SHA-256 del APK tal como lo publica GitHub («sha256:…» en la release). Vacío si no lo dio.
  final String huella;

  /// En iPhone, el .ipa adjunto (se instala por sideload, nunca desde la app).
  final String ipa;

  const Novedad({
    required this.version,
    required this.notas,
    required this.apk,
    required this.pagina,
    required this.peso,
    this.ipa = '',
    this.huella = '',
  });

  /// En iPhone no se puede instalar desde dentro: Apple no lo permite.
  bool get sePuedeInstalar => Plataforma.esAndroid && apk.isNotEmpty;

  /// Lo que hay que abrir para ver o bajar la version: en iPhone, su pagina.
  String get enlace => sePuedeInstalar ? apk : pagina;

  /// La release se marco como grande (primera linea de sus notas: `[grande]`):
  /// en vez del aviso normal sale la pantalla de novedades grande.
  bool get esGrande => notasGrandes(notas);

  /// Las notas sin la marca `[grande]`, listas para leerse.
  String get notasVisibles => quitarMarcaGrande(notas);
}

/// Marca que pone una release en la primera linea de sus notas para pedir el
/// aviso grande.
const String marcaGrande = '[grande]';

/// ¿Las notas de la release empiezan con la linea `[grande]`?
bool notasGrandes(String notas) => notas.trimLeft().toLowerCase().startsWith(marcaGrande);

/// Quita la linea `[grande]` del principio de las notas (si esta).
String quitarMarcaGrande(String notas) {
  final t = notas.trimLeft();
  if (!notasGrandes(t)) return notas.trim();
  return t.substring(marcaGrande.length).trim();
}

/// Desde que version existe la presentacion de novedades de esta edicion (la
/// quinta actualizacion grande; la primera fue la 2.2.0, la segunda la 2.3.0, la tercera la 2.4.0 y la cuarta la 2.5.0).
/// Sale una sola vez al pasar a ella (o a un parche suyo), no con cada parche.
const String edicionNovedades = '2.6.0';

/// ¿Toca enseñar las novedades grandes? [vista] es la ultima version en la
/// que ya se enseñaron (null si nunca). Solo cuando la version que corre
/// llega a la edicion y la vista es anterior a ella.
bool tocaNovedades(String? vista, String actual, {String edicion = edicionNovedades}) {
  if (hayNovedad(actual, edicion)) return false;     // aun no es la edicion
  if (vista == null || vista.trim().isEmpty) return true;
  return hayNovedad(vista, edicion);                 // la vista es anterior
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
  // la version de Google Play se actualiza desde la tienda (Play no deja otra via)
  if (actualizaLaTienda) return null;
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
    huella: huellaDe(elegido?['digest']),
  );
}

/// «sha256:abc…» → «abc…» (en minúsculas). Cualquier otra cosa → ''.
String huellaDe(Object? digest) {
  final t = '${digest ?? ''}'.trim().toLowerCase();
  if (!t.startsWith('sha256:')) return '';
  final h = t.substring(7);
  return RegExp(r'^[0-9a-f]{64}$').hasMatch(h) ? h : '';
}

/// La descarga en curso por versión: si se toca «Instalar» en dos sitios (o dos veces),
/// las dos esperan a la misma descarga en vez de escribir a la vez el mismo archivo.
final Map<String, Future<String>> _bajandoApk = {};

/// Trae el APK nuevo y lo deja listo para instalar. Devuelve su ruta.
///
/// Solo devuelve un archivo comprobado: tamaño exacto, cabecera de ZIP y, si GitHub dio su
/// huella, el mismo SHA-256 byte a byte. Un APK cortado o mezclado es lo que hace que Android
/// diga «se produjo un error durante el análisis del paquete»: así no se le entrega nunca.
Future<String> descargarApk(
  Novedad novedad, {
  void Function(double)? alProgresar,
  CancelToken? cancelar,
}) {
  if (!novedad.sePuedeInstalar) {
    return Future.error(UnsupportedError('Esta version no se puede instalar desde la app.'));
  }
  final clave = novedad.apk;
  final enCurso = _bajandoApk[clave];
  if (enCurso != null) return enCurso;
  final f = _descargarApk(novedad, alProgresar, cancelar);
  _bajandoApk[clave] = f;
  f.whenComplete(() => _bajandoApk.remove(clave)).ignore();
  return f;
}

Future<String> _descargarApk(Novedad novedad, void Function(double)? alProgresar, CancelToken? cancelar) async {
  // en la carpeta privada de archivos (no en la caché, que Android puede vaciar mientras
  // el instalador todavía lo está leyendo)
  final carpeta = Directory('${(await getApplicationSupportDirectory()).path}/actualizacion');
  await carpeta.create(recursive: true);
  final destino = '${carpeta.path}/Caudal-${novedad.version}.apk';
  // lo que dejaron versiones anteriores ya no sirve (también los APK que las versiones de
  // antes dejaban en la caché): libera espacio, que el instalador necesita
  try {
    await for (final e in carpeta.list()) {
      if (e is File && e.path != destino) await e.delete();
    }
    await for (final e in (await getTemporaryDirectory()).list()) {
      final nombre = e.path.split(RegExp(r'[\\/]')).last;
      if (e is File && nombre.startsWith('Caudal-') && (nombre.endsWith('.apk') || nombre.endsWith('.parcial'))) {
        await e.delete();
      }
    }
  } catch (_) {}

  final ya = File(destino);
  if (await apkCompleto(ya, novedad.peso, huella: novedad.huella)) {
    alProgresar?.call(100);
    return destino;                      // ya estaba bajado y comprobado
  }
  if (await ya.exists()) await ya.delete();

  final parcial = File('$destino.parcial');
  Object? ultimoFallo;
  for (var intento = 0; intento < 3; intento++) {
    try {
      if (await parcial.exists()) await parcial.delete();
      await Dio().download(
        novedad.apk,
        parcial.path,
        cancelToken: cancelar,
        options: Options(headers: {'User-Agent': 'Caudal', 'Accept-Encoding': 'identity'}),
        onReceiveProgress: (hecho, total) {
          if (total > 0) alProgresar?.call(hecho / total * 100);
        },
      );
      if (await apkCompleto(parcial, novedad.peso, huella: novedad.huella)) {
        await parcial.rename(destino);
        return destino;
      }
      ultimoFallo = 'el archivo llegó dañado';
    } on DioException catch (e) {
      if (CancelToken.isCancel(e)) rethrow;
      ultimoFallo = e.message ?? e.type.name;
    }
  }
  try {
    if (await parcial.exists()) await parcial.delete();
  } catch (_) {}
  throw StateError('La descarga llegó incompleta ($ultimoFallo). Revisa tu internet y vuelve a tocar «Instalar».');
}

/// ¿El APK bajado está entero? Tamaño exacto (si GitHub lo dijo), cabecera de ZIP («PK») y,
/// si hay [huella], el mismo SHA-256 que el publicado.
Future<bool> apkCompleto(File archivo, int peso, {String huella = ''}) async {
  if (!await archivo.exists()) return false;
  final largo = await archivo.length();
  if (largo < 1024 || (peso > 0 && largo != peso)) return false;
  final raf = await archivo.open();
  try {
    final cabeza = await raf.read(2);
    if (cabeza.length != 2 || cabeza[0] != 0x50 || cabeza[1] != 0x4B) return false;
  } finally {
    await raf.close();
  }
  if (huella.isEmpty) return true;
  final calculada = await sha256.bind(archivo.openRead()).first;
  return calculada.toString() == huella;
}

/// Lanza el instalador de Android. El sistema pide permiso la primera vez.
///
/// En iPhone no hay instalador al que llamar: se dice y no se intenta.
Future<String?> instalar(String rutaApk) async {
  if (!Plataforma.esAndroid) {
    return 'En iPhone la version nueva se instala desde su pagina, no desde la app.';
  }
  // Android pide permiso para instalar apps fuera de la tienda: si falta, se
  // abre su pantalla de ajustes y se sigue al volver
  try {
    if (!await Permission.requestInstallPackages.isGranted) {
      final estado = await Permission.requestInstallPackages.request();
      if (!estado.isGranted) {
        return 'Para instalar la versión nueva, activa «Permitir de esta fuente» para Caudal '
            '(Ajustes del teléfono → Instalar apps desconocidas) y vuelve a tocar «Instalar».';
      }
    }
  } catch (_) {}
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


/// Una versión anterior del móvil, para volver a ella si la nueva falla.
class VersionAnterior {
  final String version;
  final String apk;
  final String fecha;
  const VersionAnterior({required this.version, required this.apk, required this.fecha});
}

/// Las versiones del móvil más viejas que esta (de la más nueva a la más vieja), con el APK
/// de la arquitectura del teléfono. null si no se pudo preguntar.
Future<List<VersionAnterior>?> versionesAnteriores({int limite = 6}) async {
  try {
    final dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 12),
      receiveTimeout: const Duration(seconds: 12),
      headers: {'User-Agent': 'Caudal', 'Accept': 'application/vnd.github+json'},
      responseType: ResponseType.plain,
    ));
    final r = await dio.get(_api);
    if (r.statusCode != 200) return null;
    return anterioresDe(jsonDecode(r.data as String) as List, limite: limite);
  } catch (_) {
    return null;
  }
}

/// Lo mismo que [versionesAnteriores] a partir de la lista de releases (para probarlo).
List<VersionAnterior> anterioresDe(List publicadas, {int limite = 6, String? abi, String? actual}) {
  final esta = actual ?? versionApp;
  final salida = <VersionAnterior>[];
  for (final r in publicadas.whereType<Map>()) {
    if (r['draft'] == true || r['prerelease'] == true) continue;
    final etiqueta = '${r['tag_name'] ?? ''}';
    if (!etiqueta.startsWith(prefijo)) continue;
    final v = etiqueta.substring(prefijo.length);
    if (!hayNovedad(v, esta)) continue;            // solo las MÁS viejas que esta
    final elegido = elegirApk(r['assets'] as List? ?? const [], abi ?? abiDelTelefono());
    final apk = '${elegido?['browser_download_url'] ?? ''}';
    if (apk.isEmpty) continue;
    final fecha = '${r['published_at'] ?? ''}';
    salida.add(VersionAnterior(version: v, apk: apk, fecha: fecha.length >= 10 ? fecha.substring(0, 10) : ''));
  }
  salida.sort((a, b) => hayNovedad(a.version, b.version) ? 1 : (hayNovedad(b.version, a.version) ? -1 : 0));
  return salida.take(limite).toList();
}
