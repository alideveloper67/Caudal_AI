import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../nucleo/plataforma.dart';

/// Un aparato Bluetooth emparejado con el teléfono.
class DispositivoBt {
  const DispositivoBt({required this.direccion, required this.nombre, this.esCoche = false, this.esAudio = false});

  factory DispositivoBt.deMapa(Map<dynamic, dynamic> m) => DispositivoBt(
        direccion: '${m['direccion'] ?? ''}'.toUpperCase(),
        nombre: '${m['nombre'] ?? ''}'.trim(),
        esCoche: m['coche'] == true,
        esAudio: m['audio'] == true,
      );

  /// La dirección del aparato (AA:BB:CC:DD:EE:FF): lo que no cambia aunque le cambien el nombre.
  final String direccion;
  final String nombre;

  /// Android dice que es la radio de un coche o un manos libres.
  final bool esCoche;

  /// Suena (altavoz, audífonos, coche...).
  final bool esAudio;

  String get nombreVisible => nombre.isEmpty ? 'Aparato sin nombre' : nombre;

  @override
  bool operator ==(Object other) => other is DispositivoBt && other.direccion == direccion;

  @override
  int get hashCode => direccion.hashCode;
}

/// Un aparato que se acaba de conectar o desconectar.
class EventoBt {
  const EventoBt({required this.conectado, required this.dispositivo});
  final bool conectado;
  final DispositivoBt dispositivo;
}

/// Lo que Caudal sabe hacer con el Bluetooth del teléfono. Las pruebas usan una de mentira.
abstract class FuenteBluetooth {
  bool get disponible;
  Future<bool> hayPermiso();
  Future<bool> pedirPermiso();
  Future<void> abrirAjustesDeLaApp();
  Future<List<DispositivoBt>> emparejados();
  Future<List<DispositivoBt>> conectados();
  Stream<EventoBt> get cambios;
}

/// El Bluetooth de verdad (Android, `CocheBluetooth.kt`). En iPhone y en el
/// navegador no hay nada: las apps no pueden ver qué Bluetooth se conecta.
class BluetoothNativo implements FuenteBluetooth {
  const BluetoothNativo();

  static const _canal = MethodChannel('caudal/coche');
  static const _eventos = EventChannel('caudal/coche/eventos');

  @override
  bool get disponible => Plataforma.esAndroid;

  @override
  Future<bool> hayPermiso() async {
    if (!disponible) return false;
    try {
      return await _canal.invokeMethod<bool>('permiso') ?? false;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<bool> pedirPermiso() async {
    if (!disponible) return false;
    if (await hayPermiso()) return true;
    try {
      await Permission.bluetoothConnect.request();
    } catch (_) {}
    return hayPermiso();
  }

  @override
  Future<void> abrirAjustesDeLaApp() async {
    try {
      await openAppSettings();
    } catch (_) {}
  }

  Future<List<DispositivoBt>> _lista(String metodo) async {
    if (!disponible) return const [];
    try {
      final r = await _canal.invokeMethod<List<dynamic>>(metodo);
      return [
        for (final m in r ?? const [])
          if (m is Map) DispositivoBt.deMapa(m)
      ];
    } catch (_) {
      return const [];
    }
  }

  @override
  Future<List<DispositivoBt>> emparejados() => _lista('emparejados');

  @override
  Future<List<DispositivoBt>> conectados() => _lista('conectados');

  @override
  Stream<EventoBt> get cambios {
    if (!disponible) return const Stream.empty();
    return _eventos.receiveBroadcastStream().where((e) => e is Map).map((e) {
      final m = e as Map;
      return EventoBt(conectado: m['evento'] == 'conectado', dispositivo: DispositivoBt.deMapa(m));
    }).handleError((_) {});
  }
}

/// Lo que eligió la persona: si el modo coche se abre solo y con qué aparatos.
///
/// Se guarda en las preferencias del teléfono (no en la cuenta): el coche es de
/// este teléfono. Las claves las lee también `CocheReceptor.kt` cuando la app
/// está cerrada, por eso los aparatos van en un texto y no en una lista.
class PreferenciasCoche {
  PreferenciasCoche({this.abrirSolo = false, Map<String, String>? dispositivos})
      : dispositivos = dispositivos ?? {};

  static const claveAbrirSolo = 'coche_abrir_solo';
  static const claveDispositivos = 'coche_dispositivos';

  /// Avisa cuando se guardan cambios (lo escucha el vigía del Bluetooth).
  static final cambios = ValueNotifier<int>(0);

  bool abrirSolo;

  /// Dirección -> nombre con el que se eligió.
  final Map<String, String> dispositivos;

  bool contiene(String direccion) => dispositivos.containsKey(direccion.toUpperCase());

  void alternar(DispositivoBt d, bool si) {
    if (si) {
      dispositivos[d.direccion.toUpperCase()] = d.nombre;
    } else {
      dispositivos.remove(d.direccion.toUpperCase());
    }
  }

  /// `AA:BB|Radio del coche` una por línea.
  static String codificar(Map<String, String> d) => [
        for (final e in d.entries) '${e.key}|${e.value.replaceAll('\n', ' ').replaceAll('|', '/')}',
      ].join('\n');

  static Map<String, String> decodificar(String? texto) {
    final salida = <String, String>{};
    for (final linea in (texto ?? '').split('\n')) {
      final i = linea.indexOf('|');
      final dir = (i < 0 ? linea : linea.substring(0, i)).trim().toUpperCase();
      if (dir.isEmpty) continue;
      salida[dir] = i < 0 ? '' : linea.substring(i + 1);
    }
    return salida;
  }

  static Future<PreferenciasCoche> cargar() async {
    try {
      final p = await SharedPreferences.getInstance();
      return PreferenciasCoche(
        abrirSolo: p.getBool(claveAbrirSolo) ?? false,
        dispositivos: decodificar(p.getString(claveDispositivos)),
      );
    } catch (_) {
      return PreferenciasCoche();
    }
  }

  Future<void> guardar() async {
    try {
      final p = await SharedPreferences.getInstance();
      await p.setBool(claveAbrirSolo, abrirSolo);
      await p.setString(claveDispositivos, codificar(dispositivos));
    } catch (_) {}
    cambios.value++;
  }
}

enum DecisionCoche { nada, abrirYa, alVolver }

/// Cuándo se abre solo el modo coche. Sin teléfono de por medio, para poder probarlo.
///
///  * Se conecta el coche con Caudal a la vista: se abre al momento.
///  * Con Caudal de fondo o cerrado Android no deja abrir pantallas: queda
///    pendiente y se abre al volver a Caudal (el aviso de `CocheReceptor.kt`
///    lleva hasta aquí con un toque). Pasada [caducidad] ya no se abre.
///  * Una vez por conexión: si lo cierras, no vuelve a salir hasta que el coche
///    se desconecte y se conecte otra vez.
class DecisorCoche {
  DecisorCoche({this.caducidad = const Duration(minutes: 30)});

  final Duration caducidad;
  final Set<String> _yaAbierto = {};
  String? _pendiente;
  DateTime? _pendienteDesde;

  String? get pendiente => _pendiente;

  DecisionCoche alConectar(String direccion, PreferenciasCoche p, {required bool aLaVista, DateTime? ahora}) {
    final dir = direccion.toUpperCase();
    if (!p.abrirSolo || !p.contiene(dir) || _yaAbierto.contains(dir)) return DecisionCoche.nada;
    if (aLaVista) {
      _yaAbierto.add(dir);
      if (_pendiente == dir) _pendiente = null;
      return DecisionCoche.abrirYa;
    }
    _pendiente = dir;
    _pendienteDesde = ahora ?? DateTime.now();
    return DecisionCoche.alVolver;
  }

  void alDesconectar(String direccion) {
    final dir = direccion.toUpperCase();
    _yaAbierto.remove(dir);
    if (_pendiente == dir) _pendiente = null;
  }

  /// Al volver a Caudal: si quedó pendiente (y no caducó), toca abrirlo.
  bool alVolver(PreferenciasCoche p, {DateTime? ahora}) {
    final dir = _pendiente;
    final desde = _pendienteDesde;
    _pendiente = null;
    if (dir == null || desde == null || !p.abrirSolo || !p.contiene(dir)) return false;
    if ((ahora ?? DateTime.now()).difference(desde) > caducidad) return false;
    _yaAbierto.add(dir);
    return true;
  }

  /// La persona abrió el modo coche a mano (o desde el aviso) con [direccion] conectado.
  void marcarAbierto(String direccion) => _yaAbierto.add(direccion.toUpperCase());

  @visibleForTesting
  void reiniciar() {
    _yaAbierto.clear();
    _pendiente = null;
    _pendienteDesde = null;
  }
}
