// Avisos que Caudal manda a todas las apps sin sacar una versión nueva.
//
// Viven en la tabla `avisos` de la nube (supabase/avisos.sql) y se envían con
// herramientas/enviar_aviso.py. Cada app los lee al abrirse y muestra cada uno UNA
// sola vez por dispositivo; si no hay conexión, simplemente no sale ninguno.

import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'nube.dart';
import 'plataforma.dart';

class AvisoCaudal {
  const AvisoCaudal({
    required this.id,
    required this.titulo,
    required this.texto,
    this.plataformas = const ['todas'],
    this.enlace,
    this.etiquetaEnlace,
  });

  final int id;
  final String titulo;
  final String texto;
  final List<String> plataformas;
  final String? enlace;
  final String? etiquetaEnlace;

  /// null si la fila no sirve (sin id, título o texto).
  static AvisoCaudal? desde(dynamic f) {
    if (f is! Map) return null;
    final id = f['id'];
    final titulo = '${f['titulo'] ?? ''}'.trim();
    final texto = '${f['texto'] ?? ''}'.trim();
    if (id is! num || titulo.isEmpty || texto.isEmpty) return null;
    final enlace = '${f['enlace'] ?? ''}'.trim();
    final etiqueta = '${f['etiqueta_enlace'] ?? ''}'.trim();
    final plat = f['plataformas'];
    return AvisoCaudal(
      id: id.toInt(),
      titulo: titulo,
      texto: texto,
      plataformas: plat is List && plat.isNotEmpty ? [for (final p in plat) '$p'.toLowerCase()] : const ['todas'],
      // solo https: un aviso nunca abre otra cosa
      enlace: enlace.startsWith('https://') ? enlace : null,
      etiquetaEnlace: etiqueta.isEmpty ? null : etiqueta,
    );
  }

  /// ¿Le toca a esta plataforma ('web', 'android', 'windows', 'ios')?
  bool es(String plataforma) => plataformas.contains('todas') || plataformas.contains(plataforma);
}

class Avisos {
  Avisos._();

  static const _clave = 'avisos_vistos';

  /// En qué corre esta copia, con los nombres que usa la tabla.
  static String get plataforma {
    if (kIsWeb) return 'web';
    if (Plataforma.esIOS) return 'ios';
    if (Plataforma.esAndroid) return 'android';
    return switch (defaultTargetPlatform) {
      TargetPlatform.windows => 'windows',
      _ => 'otra',
    };
  }

  /// Los avisos vigentes que le tocan a [plat] y que este dispositivo aún no vio, del más viejo
  /// al más nuevo. Nunca lanza: sin conexión o con cualquier fallo devuelve una lista vacía.
  static Future<List<AvisoCaudal>> pendientes({String? plat, http.Client? cliente}) async {
    final c = cliente ?? http.Client();
    try {
      final r = await c.get(
        Uri.parse('${Nube.url}/rest/v1/avisos?select=id,titulo,texto,plataformas,enlace,etiqueta_enlace&order=id.asc'),
        headers: {'apikey': Nube.clavePublica, 'Authorization': 'Bearer ${Nube.clavePublica}'},
      ).timeout(const Duration(seconds: 10));
      if (r.statusCode != 200) return const [];
      final datos = jsonDecode(utf8.decode(r.bodyBytes));
      if (datos is! List) return const [];
      final vistos = await _vistos();
      final miPlat = plat ?? plataforma;
      final lista = <AvisoCaudal>[];
      for (final f in datos) {
        final a = AvisoCaudal.desde(f);
        if (a != null && a.es(miPlat) && !vistos.contains(a.id)) lista.add(a);
      }
      return lista;
    } catch (_) {
      return const [];
    } finally {
      if (cliente == null) c.close();
    }
  }

  static Future<Set<int>> _vistos() async {
    try {
      final p = await SharedPreferences.getInstance();
      final vistos = <int>{};
      for (final v in p.getStringList(_clave) ?? const <String>[]) {
        final n = int.tryParse(v);
        if (n != null) vistos.add(n);
      }
      return vistos;
    } catch (_) {
      return {};
    }
  }

  /// Que este dispositivo ya lo vio: no vuelve a salir.
  static Future<void> marcarVisto(int id) async {
    try {
      final p = await SharedPreferences.getInstance();
      final v = <String>{...(p.getStringList(_clave) ?? const <String>[]), '$id'};
      await p.setStringList(_clave, v.toList());
    } catch (_) {}
  }
}
