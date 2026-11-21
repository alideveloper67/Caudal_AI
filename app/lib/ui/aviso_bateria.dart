// «Que la música no se corte»: la primera vez que la música suena un rato en un Android que aún
// tiene a Caudal bajo el ahorro de batería, se explica en una hoja y se abre la pregunta del
// sistema (un solo «Permitir»). Samsung, Xiaomi, Huawei y otros apagan las apps en segundo plano
// aunque estén sonando; con esto dejan de hacerlo. Como mucho 3 veces y con días de por medio.

import 'dart:async';

import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show MethodChannel;
import 'package:shared_preferences/shared_preferences.dart';

import '../nucleo/plataforma.dart';
import '../reproduccion/reproductor.dart';
import 'tema.dart';

class AvisoBateria {
  AvisoBateria._();

  static const _canal = MethodChannel('caudal/energia');
  static const _claveVeces = 'aviso_bateria_veces';
  static const _claveUltima = 'aviso_bateria_ultima';
  static const topeVeces = 3;
  static const entreAvisos = Duration(days: 3);

  /// Cuánto tiene que sonar seguido antes de preguntar (no interrumpir el primer toque).
  static const sonandoAntes = Duration(seconds: 25);

  static Reproductor? _r;
  static VoidCallback? _oyente;
  static Timer? _espera;
  static bool _hecho = false;

  /// Si toca mostrarlo, según las veces que ya salió y cuándo.
  @visibleForTesting
  static bool toca(int veces, DateTime? ultima, DateTime ahora) {
    if (veces >= topeVeces) return false;
    return ultima == null || ahora.difference(ultima) >= entreAvisos;
  }

  /// Vigila el reproductor de la cuenta (otra cuenta: cambia de reproductor).
  static void enganchar(Reproductor r, BuildContext? Function() contexto) {
    if (!Plataforma.esAndroid) return;
    final antes = _r;
    if (antes != null && _oyente != null) antes.removeListener(_oyente!);
    _r = r;
    _oyente = () {
      if (_hecho) return;
      if (r.estado == EstadoRepro.sonando) {
        _espera ??= Timer(sonandoAntes, () {
          _espera = null;
          if (r.estado == EstadoRepro.sonando) unawaited(_quizas(contexto));
        });
      } else if (r.estado != EstadoRepro.cargando) {
        _espera?.cancel();
        _espera = null;
      }
    };
    r.addListener(_oyente!);
  }

  static Future<void> _quizas(BuildContext? Function() contexto) async {
    if (_hecho) return;
    _hecho = true; // una vez por sesión, salga o no
    try {
      if (await _canal.invokeMethod<bool>('sinRestriccion') == true) return;
      final p = await SharedPreferences.getInstance();
      final veces = p.getInt(_claveVeces) ?? 0;
      final ms = p.getInt(_claveUltima);
      final ultima = ms == null ? null : DateTime.fromMillisecondsSinceEpoch(ms);
      if (!toca(veces, ultima, DateTime.now())) return;
      final fabricante = (await _canal.invokeMethod<String>('fabricante').catchError((_) => '')) ?? '';
      final ctx = contexto();
      if (ctx == null || !ctx.mounted) return;
      await p.setInt(_claveVeces, veces + 1);
      await p.setInt(_claveUltima, DateTime.now().millisecondsSinceEpoch);
      if (!ctx.mounted) return;
      await mostrar(ctx, fabricante);
    } catch (_) {}
  }

  /// Los pasos de cada marca, por si el «Permitir» no basta.
  @visibleForTesting
  static String pasos(String fabricante) {
    final f = fabricante.toLowerCase();
    if (f.contains('samsung')) {
      return 'En Samsung, además: Ajustes › Batería › Límites de uso en segundo plano, y quita a Caudal de '
          '«Apps en suspensión» y «Apps en suspensión profunda».';
    }
    if (f.contains('xiaomi') || f.contains('redmi') || f.contains('poco')) {
      return 'En Xiaomi, además: mantén pulsado Caudal › Información › Ahorro de batería › «Sin restricciones», '
          'y activa «Inicio automático».';
    }
    if (f.contains('huawei') || f.contains('honor')) {
      return 'En Huawei/Honor, además: Ajustes › Batería › Inicio de aplicaciones › Caudal › «Gestionar '
          'manualmente» con todo activado.';
    }
    if (f.contains('oppo') || f.contains('realme') || f.contains('oneplus') || f.contains('vivo')) {
      return 'En tu teléfono, además: información de Caudal › Uso de batería › «Permitir actividad en segundo plano».';
    }
    return 'Si aun así se corta: información de Caudal › Batería › «Sin restricciones».';
  }

  static Future<void> mostrar(BuildContext context, String fabricante) => showModalBottomSheet<void>(
        context: context,
        useRootNavigator: true,
        isScrollControlled: true,
        builder: (ctx) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(22, 20, 22, 16),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon(Icons.battery_charging_full_rounded, color: C.acento, size: 30),
                const SizedBox(width: 12),
                const Expanded(
                  child: Text('Que la música no se corte',
                      style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
                ),
              ]),
              const SizedBox(height: 12),
              const Text(
                'Tu teléfono ahorra batería apagando las apps que están de fondo, aunque estén sonando. '
                'Por eso la música puede cortarse al salir de Caudal o al bloquear la pantalla.',
                style: TextStyle(fontSize: 14.5, height: 1.35),
              ),
              const SizedBox(height: 10),
              const Text('Toca «Permitir» y en la pregunta del teléfono elige «Permitir» otra vez.',
                  style: TextStyle(fontSize: 14.5, height: 1.35, fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              Text(pasos(fabricante), style: estiloSecundario),
              const SizedBox(height: 18),
              Row(children: [
                TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Ahora no')),
                const Spacer(),
                FilledButton.icon(
                  icon: const Icon(Icons.check_rounded),
                  label: const Text('Permitir'),
                  onPressed: () {
                    Navigator.of(ctx).pop();
                    _canal.invokeMethod('pedirSinRestriccion').catchError((_) {});
                  },
                ),
              ]),
            ]),
          ),
        ),
      );
}
