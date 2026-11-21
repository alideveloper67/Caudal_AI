import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'version.dart';

/// Arranque a prueba de trabas.
///
/// Antes de cada paso del arranque se anota cual es (en un archivo, de forma
/// sincrona, para que quede escrito aunque despues se congele todo). Si la
/// vez anterior la pantalla nunca llego a dibujarse, esta vez se arranca en
/// **modo seguro**: sin las piezas nativas que pueden trabar (controles en la
/// notificacion, widget, ventana flotante, navegador oculto). El modo seguro
/// dura hasta que se instala otra version.
///
/// En Android, ademas, un vigilante nativo (Vigilante.kt) anota en que linea
/// estaba trabado el sistema; se le muestra al usuario para que nos lo envie.
class Diagnostico {
  Diagnostico._();

  static const _canal = MethodChannel('caudal/diagnostico');
  static File? _marca;
  static File? _archivoErrores;

  /// Errores de este arranque (los ultimos), para contarlos si algo se traba.
  static final List<String> _errores = [];

  /// true: arrancar sin las piezas nativas opcionales.
  static bool modoSeguro = false;

  /// Arranques buenos que dura el modo seguro antes de volver a probar el normal.
  static const arranquesSeguros = 3;
  static int _restanSeguro = 0;

  /// Lo que se le ensena al usuario si la vez anterior se trabo (si no, null).
  static String? detalle;

  static Future<void> iniciar() async {
    Directory dir;
    try {
      dir = await getApplicationSupportDirectory();
    } catch (_) {
      return;
    }
    await iniciarEn(dir);
  }

  @visibleForTesting
  static Future<void> iniciarEn(Directory dir) async {
    modoSeguro = false;
    detalle = null;
    try {
      if (!await dir.exists()) await dir.create(recursive: true);
      _marca = File(p.join(dir.path, 'arranque.txt'));
      _archivoErrores = File(p.join(dir.path, 'errores.txt'));
      var erroresPrevios = '';
      if (await _archivoErrores!.exists()) {
        erroresPrevios = (await _archivoErrores!.readAsString()).trim();
        await _archivoErrores!.delete();
      }
      var previo = '';
      if (await _marca!.exists()) previo = (await _marca!.readAsString()).trim();
      final partes = previo.split('|');
      final mismaVersion = partes.isNotEmpty && partes[0] == versionApp;
      final paso = partes.length > 1 ? partes[1] : '';
      final seguroAntes = partes.length > 2 && partes[2] == '1';
      final restanAntes = partes.length > 3 ? int.tryParse(partes[3]) ?? arranquesSeguros : arranquesSeguros;
      var seTrabo = mismaVersion && paso.isNotEmpty && paso != 'pintado' && paso != 'aviso';

      String? traba;
      if (defaultTargetPlatform == TargetPlatform.android) {
        try {
          traba = await _canal.invokeMethod<String>('traba').timeout(const Duration(seconds: 3));
        } catch (_) {}
        // ¿De verdad se trabó? Android sabe cómo terminó la vez anterior.
        if (seTrabo) {
          try {
            final s = await const MethodChannel('caudal/salidas')
                .invokeMethod<Map>('ultimaSalida')
                .timeout(const Duration(seconds: 3));
            final tipo = clasificarArranque(
                '${s?['motivo'] ?? ''}', '${s?['importancia'] ?? ''}', '${s?['texto'] ?? ''}');
            if (tipo != TipoArranque.traba) {
              // un cierre del motor (lo resuelve el motor de respaldo, motor_eleccion.dart) o algo
              // que no fue culpa de Caudal: ni aviso ni modo seguro
              debugPrint('Caudal: el arranque anterior no se trabó (${s?['motivo']}): ${tipo.name}');
              seTrabo = false;
            }
          } catch (_) {}
        }
      }

      // el modo seguro dura [arranquesSeguros] arranques buenos y luego se vuelve a probar el
      // normal (antes duraba hasta la siguiente versión: una sola traba dejaba el teléfono sin
      // controles en la notificación durante semanas)
      if (!mismaVersion) {
        modoSeguro = false;
        _restanSeguro = 0;
      } else if (seTrabo) {
        modoSeguro = true;
        _restanSeguro = arranquesSeguros;
      } else if (seguroAntes) {
        _restanSeguro = paso == 'pintado' || paso == 'aviso' ? restanAntes - 1 : restanAntes;
        modoSeguro = _restanSeguro > 0;
      } else {
        modoSeguro = false;
        _restanSeguro = 0;
      }
      // solo se cuenta si de verdad no llego a verse la pantalla (un arranque
      // lento pero que termino bien no es una traba)
      if (seTrabo) {
        detalle = [
          'Caudal $versionApp · último paso del arranque: $paso${seguroAntes ? ' (ya en modo seguro)' : ''}',
          if (erroresPrevios.isNotEmpty) erroresPrevios,
          if (traba != null && traba.isNotEmpty) traba,
        ].join('\n\n');
      }
    } catch (_) {}
    marcar('inicio');
    _guardarErrores();
  }

  /// Anota el paso en curso. Sincrono a proposito: si el paso congela la app,
  /// lo anotado ya esta en disco.
  static void marcar(String paso) {
    try {
      _marca?.writeAsStringSync('$versionApp|$paso|${modoSeguro ? 1 : 0}|$_restanSeguro', flush: true);
    } catch (_) {}
  }

  /// Un error de Flutter o de Dart: se escribe en el registro del sistema
  /// (tambien en la version final) y se guarda para el detalle.
  static void anotarError(Object error, StackTrace? pila) {
    final lineas = (pila?.toString() ?? '').split('\n').where((l) => l.trim().isNotEmpty).take(12).join('\n');
    final texto = 'Error: $error\n$lineas';
    // ignore: avoid_print
    print('CAUDAL_ERROR $texto');
    _errores.add(texto);
    if (_errores.length > 3) _errores.removeAt(0);
    _guardarErrores();
  }

  static void _guardarErrores() {
    if (_errores.isEmpty) return;
    try {
      _archivoErrores?.writeAsStringSync(_errores.join('\n\n'), flush: true);
    } catch (_) {}
  }

  /// La pantalla ya se dibujo: este arranque salio bien.
  static void pintado() => marcar('pintado');

  /// Mientras se ensena el aviso de la traba anterior, el arranque aun no
  /// empezo: si la app se cierra ahi, no cuenta como otra traba.
  static void pintadoAviso() => marcar('aviso');
}

/// Cómo terminó un arranque que no llegó a dibujar la pantalla.
enum TipoArranque {
  /// Se congeló de verdad (o no se sabe): aviso y modo seguro.
  traba,

  /// Se cerró por un fallo nativo del motor de sonido: lo resuelve el motor de respaldo.
  cierreMotor,

  /// No fue culpa de Caudal (se actualizó, Android la cerró de fondo, la persona la cerró sin
  /// que estuviera en pantalla): nada que avisar.
  noCuenta,
}

/// [motivo] e [importancia] como los da Salidas.kt; [texto]: lo legible de la traza nativa.
@visibleForTesting
TipoArranque clasificarArranque(String motivo, String importancia, String texto) {
  final aLaVista = importancia == 'en_pantalla' || importancia == 'visible';
  switch (motivo) {
    case '':
    case 'anr':
    case 'fallo_java':
    case 'fallo_arranque':
      return TipoArranque.traba;
    case 'fallo_nativo':
      return RegExp(r'libmpv|libav(codec|format|util|filter)|libswresample|CodecLooper|MediaCodec|AudioTrack|Scudo|NO MEMORY',
                  caseSensitive: false)
              .hasMatch(texto)
          ? TipoArranque.cierreMotor
          : TipoArranque.traba;
    case 'paquete_actualizado':
    case 'estado_paquete':
    case 'permiso':
    case 'salida_propia':
      return TipoArranque.noCuenta;
    default:
      // la cerró la persona o Android: solo es traba si estaba a la vista sin dibujarse
      return aLaVista ? TipoArranque.traba : TipoArranque.noCuenta;
  }
}
