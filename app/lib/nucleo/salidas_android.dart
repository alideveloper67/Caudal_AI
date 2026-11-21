// Los cierres de Caudal que Dart no puede ver (Android): un fallo nativo del motor de sonido, una
// traba (ANR), Android matando la app por memoria o el ahorro de batería del fabricante apagándola
// con la música sonando. Android 11+ guarda la causa de cada salida; Salidas.kt la lee al volver
// a abrir y aquí se manda a la nube como un informe de error más (mismo freno y misma limpieza de
// datos personales que AvisoErrores).

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import 'aviso_errores.dart';
import 'plataforma.dart';

class SalidasAndroid {
  SalidasAndroid._();

  static const _canal = MethodChannel('caudal/salidas');

  /// Motivos que nunca son un problema de Caudal.
  static const _sinImportancia = {'paquete_actualizado', 'salida_propia', 'permiso', 'estado_paquete'};

  /// Motivos que siempre son un fallo (se informan aunque no sonara nada).
  static const _fallos = {'fallo_java', 'fallo_nativo', 'anr', 'fallo_arranque', 'exceso_recursos', 'dependencia'};

  /// Si vale la pena informar esta salida. Android cierra a menudo las apps que no se usan, eso
  /// no es un fallo; sí lo es si sonaba música o si Caudal estaba en pantalla.
  @visibleForTesting
  static bool merece(Map s) {
    final motivo = '${s['motivo'] ?? ''}';
    if (motivo.isEmpty || _sinImportancia.contains(motivo)) return false;
    if (_fallos.contains(motivo)) return true;
    final sonaba = s['sonaba'] == true;
    final importancia = '${s['importancia'] ?? ''}';
    if (motivo == 'usuario' || motivo == 'usuario_detuvo') return sonaba;
    return sonaba || importancia == 'en_pantalla' || importancia == 'servicio_musica';
  }

  /// El informe (columnas de `errores_app`) de una salida.
  @visibleForTesting
  static Map<String, dynamic> informe(Map s, {Map? memoria}) {
    final motivo = '${s['motivo'] ?? 'desconocido'}';
    final sonaba = s['sonaba'] == true;
    final importancia = '${s['importancia'] ?? ''}';
    final pssMb = ((s['memoria_kb'] as num? ?? 0) / 1024).round();
    final rssMb = ((s['rss_kb'] as num? ?? 0) / 1024).round();
    final partes = <String>[
      'motivo=$motivo',
      'estado=$importancia',
      if (sonaba) 'sonaba=si (${s['minutos_sonando'] ?? 0} min)',
      if (pssMb > 0) 'memoria=${pssMb}MB',
      if (rssMb > 0) 'rss=${rssMb}MB',
      if ('${s['descripcion'] ?? ''}'.isNotEmpty) 'detalle=${s['descripcion']}',
      if (memoria != null)
        'ram=${memoria['total_mb']}MB libre=${memoria['libre_mb']}MB clase=${memoria['clase_mb']}MB'
            '${memoria['ram_baja'] == true ? ' ram_baja' : ''}',
    ];
    final tipo = 'Cierre Android: $motivo';
    final traza = '${s['traza'] ?? ''}';
    final inf = AvisoErrores.informe(_Salida(tipo, partes.join(' · ')), null,
        origen: sonaba ? 'cierre-sonando' : 'cierre', pantallaActual: '');
    inf['tipo'] = tipo;
    inf['traza'] = AvisoErrores.limpiar(traza.length > 8000 ? traza.substring(0, 8000) : traza);
    // mismo motivo y mismo estado = el mismo problema (en los fallos nativos, por la librería que cayó)
    inf['huella'] = AvisoErrores.huella(tipo, '$importancia|$sonaba|${_libreria(traza)}');
    final cuando = (s['cuando'] as num?)?.toDouble();
    if (cuando != null && cuando > 0) {
      inf['primera_vez'] = cuando / 1000;
      inf['ultima_vez'] = cuando / 1000;
    }
    return inf;
  }

  /// La primera librería propia que aparece en la traza de un fallo nativo (libmpv.so, libflutter.so...).
  static String _libreria(String traza) {
    final m = RegExp(r'(lib[a-zA-Z0-9_]+\.so)').firstMatch(traza);
    return m?.group(1) ?? '';
  }

  /// Lee las salidas nuevas y las informa. Se llama una vez al abrir (con retraso, para no
  /// competir con el arranque). Nunca lanza.
  static Future<void> revisar() async {
    if (!Plataforma.esAndroid) return;
    try {
      final lista = await _canal.invokeMethod<List>('nuevas');
      if (lista == null || lista.isEmpty) return;
      Map? memoria;
      try {
        memoria = await _canal.invokeMethod<Map>('memoria');
      } catch (_) {}
      for (final s in lista.whereType<Map>()) {
        if (!merece(s)) continue;
        await AvisoErrores.anotarInforme(informe(s, memoria: memoria));
      }
    } catch (e) {
      debugPrint('Caudal: no se pudieron leer los cierres anteriores ($e)');
    }
  }
}

class _Salida {
  _Salida(this.tipo, this.mensaje);
  final String tipo, mensaje;
  @override
  String toString() => mensaje;
}
