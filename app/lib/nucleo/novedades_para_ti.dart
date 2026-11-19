import 'coleccion.dart';
import 'gamer_xp.dart' show claveDia;
import 'recomendador.dart';

/// Las canciones del día para la tarjeta «Lo nuevo para ti».
class NovedadesDelDia {
  const NovedadesDelDia({required this.dia, required this.pistas});

  /// El día (`2026-11-19`) para el que se armó.
  final String dia;
  final List<Json> pistas;
}

/// «Resumen de lo nuevo para ti» (donadores): al abrir la app, una tarjeta con 6 a 10 canciones
/// que te encajarían hoy. Sale del recomendador de siempre («Descubre para ti», que ya se arma una
/// vez al día), se muestra una vez al día y se puede cerrar hasta mañana.
class NovedadesParaTi {
  NovedadesParaTi._();

  static const minimo = 6;
  static const maximo = 10;
  static const ideal = 8;
  static const _clave = 'novedades_para_ti';

  /// De las propuestas del recomendador se eligen [n] (entre [minimo] y [maximo]): sin repetir, con
  /// título, y como mucho dos de cada artista para que sea variado. Devuelve vacío si no alcanzan.
  static List<Json> elegir(List<Json> propuestas, {int n = ideal}) {
    final tope = n.clamp(minimo, maximo);
    final vistos = <String>{};
    final limpias = <Json>[];
    for (final p in propuestas) {
      final id = '${p['video_id'] ?? p['clave'] ?? ''}';
      if (id.isEmpty || '${p['titulo'] ?? ''}'.trim().isEmpty || !vistos.add(id)) continue;
      limpias.add(p);
    }
    final variadas = Recomendador.diversificar(limpias, porArtista: 2, largo: tope);
    return variadas.length < minimo ? const [] : variadas.take(tope).toList();
  }

  /// Lo de hoy, o null si ya se cerró hoy o todavía no hay suficientes (por ejemplo sin conexión
  /// y sin nada guardado). [armar] se puede cambiar en las pruebas.
  static Future<NovedadesDelDia?> delDia(
    Coleccion c, {
    DateTime? ahora,
    Future<Json?> Function(Coleccion c, DateTime ahora)? armar,
  }) async {
    final hoy = ahora ?? DateTime.now();
    final dia = claveDia(hoy);
    try {
      final g = await c.estado(_clave);
      if (g is Map && g['cerrada'] == dia) return null;
    } catch (_) {}
    final mix = await (armar ?? (c, h) => Recomendador.descubrir(c, ahora: h))(c, hoy);
    final lista = mix?['pistas'];
    if (lista is! List) return null;
    final pistas = elegir([for (final p in lista) if (p is Map) Map<String, dynamic>.from(p)]);
    return pistas.isEmpty ? null : NovedadesDelDia(dia: dia, pistas: pistas);
  }

  /// Cierra la tarjeta hasta mañana.
  static Future<void> cerrar(Coleccion c, {DateTime? ahora}) async {
    try {
      await c.guardarEstado(_clave, {'cerrada': claveDia(ahora ?? DateTime.now())});
    } catch (_) {}
  }
}
