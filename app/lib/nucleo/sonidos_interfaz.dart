import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:path_provider/path_provider.dart';

import '../reproduccion/jugador.dart';
import 'archivos_web.dart';
import 'estilo_reproductor.dart';
import 'premium_letras.dart';
import 'streams.dart' show Fuente;

/// Los soniditos de la interfaz (donadores): uno al dar «me gusta» y otro al abrir la app.
///
/// Los tres audios son WAV cortos de `assets/sonidos/` (menos de 60 KB en total). Se copian una
/// vez a la carpeta temporal (el motor necesita un archivo) y suenan con un motor propio,
/// aparte del de la música y a volumen bajo. Ese motor se crea al primer sonido y se suelta
/// tras un rato sin usarlo: en reposo no gasta nada. Todo falla en silencio.
class SonidosInterfaz {
  SonidosInterfaz({
    FabricaJugadorUi? fabrica,
    Future<Directory> Function()? carpeta,
    Future<Uint8List> Function(String asset)? cargarAsset,
    PreferenciasReproductor? preferencias,
    bool Function()? esDonador,
    bool? disponible,
    this.espera = const Duration(milliseconds: 1800),
    this.reposo = const Duration(seconds: 20),
  })  : _fabrica = fabrica ?? Jugador.crearAparte,
        _carpeta = carpeta ?? getTemporaryDirectory,
        _cargarAsset = cargarAsset ?? _delBundle,
        _prefs = preferencias ?? PreferenciasReproductor.i,
        _esDonador = esDonador,
        _disponible = disponible;

  static final SonidosInterfaz i = SonidosInterfaz();

  final FabricaJugadorUi _fabrica;
  final Future<Directory> Function() _carpeta;
  final Future<Uint8List> Function(String asset) _cargarAsset;
  final PreferenciasReproductor _prefs;
  final bool Function()? _esDonador;
  final bool? _disponible;

  /// Cuánto se espera al abrir la app antes de sonar (para que ya se sepa si es donador).
  final Duration espera;

  /// Sin sonar durante este tiempo, el motor se suelta.
  final Duration reposo;

  static const _version = 1;
  static Future<Uint8List> _delBundle(String a) async => (await rootBundle.load(a)).buffer.asUint8List();

  bool get disponible => _disponible ?? true;
  bool get _donador => (_esDonador ?? esPremiumLetras)();

  Jugador? _motor;
  Timer? _suelta;
  DateTime _ultimo = DateTime.fromMillisecondsSinceEpoch(0);
  bool _abierta = false;
  final Map<SonidoUi, Future<File>> _archivos = {};

  /// Cuántas veces sonó de verdad (para las pruebas).
  @visibleForTesting
  int sonados = 0;

  /// Al dar «me gusta» (solo si lo activó, es donador y no es quitar el me gusta).
  Future<void> meGusta() async {
    if (!_prefs.sonidoMeGusta || !_donador) return;
    await reproducir(_prefs.sonido);
  }

  /// Al abrir la app: una sola vez por arranque, y tras una breve espera.
  Future<void> alAbrir() async {
    if (_abierta) return;
    _abierta = true;
    await _prefs.cargar();
    if (!_prefs.sonidoAlAbrir) return;
    await Future<void>.delayed(espera);
    if (!_prefs.sonidoAlAbrir || !_donador) return;
    await reproducir(_prefs.sonido);
  }

  /// Suena [s] a volumen bajo, sin comprobar permisos (la vista previa del selector).
  /// Dos seguidos a menos de 250 ms se ignoran: ni un doble toque lo repite.
  Future<void> reproducir(SonidoUi s, {bool vistaPrevia = false}) async {
    if (!disponible) return;
    final ahora = DateTime.now();
    if (!vistaPrevia && ahora.difference(_ultimo) < const Duration(milliseconds: 250)) return;
    _ultimo = ahora;
    try {
      final ruta = await _rutaDe(s);
      final j = _motor ??= _fabrica();
      await j.setVolume(_prefs.volumenSonido.clamp(0.05, 0.6) * 100);
      await j.open(Fuente.archivo(ruta));
      sonados++;
      _ultimo = DateTime.now();
      _suelta?.cancel();
      _suelta = Timer(reposo, soltar);
    } catch (e) {
      debugPrint('sonido de interfaz: $e');
      await soltar();
    }
  }

  /// En la web no hay carpeta temporal: el WAV vive en la memoria del navegador.
  final Map<SonidoUi, Future<String>> _enMemoria = {};

  Future<String> _rutaDe(SonidoUi s) async {
    if (!kIsWeb) return (await archivoDe(s)).path;
    return _enMemoria[s] ??= _cargarAsset(s.asset).then((b) => ArchivosWeb.urlTemporal(b, 'audio/wav'));
  }

  Future<File> archivoDe(SonidoUi s) => _archivos[s] ??= _asegurar(s);

  Future<File> _asegurar(SonidoUi s) async {
    try {
      final dir = Directory('${(await _carpeta()).path}${Platform.pathSeparator}caudal_sonidos_ui');
      if (!await dir.exists()) await dir.create(recursive: true);
      final f = File('${dir.path}${Platform.pathSeparator}${s.name}_v$_version.wav');
      if (await f.exists() && await f.length() > 44) return f;
      final tmp = File('${f.path}.tmp');
      await tmp.writeAsBytes(await _cargarAsset(s.asset), flush: true);
      return await tmp.rename(f.path);
    } catch (_) {
      _archivos.remove(s); // que la próxima vez lo intente de nuevo
      rethrow;
    }
  }

  /// Suelta el motor (al estar en reposo o al fallar).
  Future<void> soltar() async {
    _suelta?.cancel();
    _suelta = null;
    final j = _motor;
    _motor = null;
    if (j == null) return;
    try {
      await j.dispose();
    } catch (_) {}
  }
}

typedef FabricaJugadorUi = Jugador Function();
