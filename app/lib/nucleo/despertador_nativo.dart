import 'dart:convert';

import 'package:flutter/services.dart';

import 'plataforma.dart';

/// Permisos que necesita el despertador en Android para sonar con la app cerrada.
class PermisosDespertador {
  const PermisosDespertador({
    this.exactas = true,
    this.pantallaCompleta = true,
    this.notificaciones = true,
    this.bateria = true,
  });

  /// «Alarmas y recordatorios»: sin él, Android puede retrasar la alarma unos minutos.
  final bool exactas;

  /// Pantalla completa sobre el bloqueo (Android 14+ lo puede quitar).
  final bool pantallaCompleta;
  final bool notificaciones;

  /// Sin el ahorro de batería que duerme a Caudal.
  final bool bateria;

  bool get todo => exactas && pantallaCompleta && notificaciones;

  factory PermisosDespertador.de(Object? m) {
    if (m is! Map) return const PermisosDespertador();
    return PermisosDespertador(
      exactas: m['exactas'] != false,
      pantallaCompleta: m['pantallaCompleta'] != false,
      notificaciones: m['notificaciones'] != false,
      bateria: m['bateria'] != false,
    );
  }
}

/// El puente con Despertador.kt. Solo hace algo en Android; en lo demás responde «nada que hacer».
/// Las pruebas lo sustituyen por uno de mentira.
class CanalDespertador {
  const CanalDespertador();

  static const _canal = MethodChannel('caudal/despertador');

  bool get disponible => Plataforma.esAndroid;

  /// Entrega las alarmas (con sus archivos preparados) y el respaldo: Android las guarda y programa
  /// cada una con AlarmManager.setAlarmClock (suena aunque la app esté cerrada y el teléfono bloqueado).
  Future<void> programar(Map<String, dynamic> datos) async {
    if (!disponible) return;
    try {
      await _canal.invokeMethod('programar', jsonEncode(datos));
    } catch (_) {}
  }

  /// Lo que Android tiene guardado (allí se apagan las de «una vez» y se anotan las pospuestas).
  Future<Map<String, dynamic>?> leer() async {
    if (!disponible) return null;
    try {
      final t = await _canal.invokeMethod<String>('leer');
      if (t == null || t.isEmpty) return null;
      final d = jsonDecode(t);
      return d is Map ? Map<String, dynamic>.from(d) : null;
    } catch (_) {
      return null;
    }
  }

  Future<PermisosDespertador> permisos() async {
    if (!disponible) return const PermisosDespertador();
    try {
      return PermisosDespertador.de(await _canal.invokeMethod('permisos'));
    } catch (_) {
      return const PermisosDespertador();
    }
  }

  /// Abre el ajuste del sistema: 'exactas' | 'pantallaCompleta' | 'notificaciones' | 'bateria'.
  Future<void> abrirAjuste(String cual) async {
    if (!disponible) return;
    try {
      await _canal.invokeMethod('abrirAjuste', cual);
    } catch (_) {}
  }

  /// Suena ya, como sonará (no cambia nada de lo guardado).
  Future<void> probar(String id) async {
    if (!disponible) return;
    try {
      await _canal.invokeMethod('probar', id);
    } catch (_) {}
  }

  /// Si al apagar se pulsó «Seguir escuchando»: el id de la alarma (una sola vez), o null.
  Future<String?> consumirSeguir() async {
    if (!disponible) return null;
    try {
      return await _canal.invokeMethod<String>('consumirSeguir');
    } catch (_) {
      return null;
    }
  }
}
