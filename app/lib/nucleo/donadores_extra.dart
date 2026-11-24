import 'package:shared_preferences/shared_preferences.dart';

import 'cosmeticos.dart';
import 'nube.dart';
import 'social.dart';

// Lo nuevo para donadores que no es el color del nombre: la pared de agradecimiento, la mascota
// propia (se pide por WhatsApp) y la lógica pura de la letra con efectos. Todo sin widgets, para
// probarlo sin pantallas.

// =============================================================== pared de agradecimiento

/// Una persona de la pared (`pared_agradecimiento`).
class DonadorPared {
  const DonadorPared({required this.usuario, required this.nombre, required this.tipo, this.color, this.desde});

  final String usuario;
  final String nombre;

  /// 'fundador' o 'donador'.
  final String tipo;

  /// Su color del nombre («#RRGGBB») o null.
  final String? color;
  final DateTime? desde;

  bool get fundador => tipo == 'fundador';
  String get etiqueta => fundador ? 'Fundador' : 'Donador';
}

class ParedAgradecimiento {
  ParedAgradecimiento._();

  /// La respuesta del servidor ya limpia: sin filas raras, primero los fundadores (como la manda el
  /// servidor, pero se asegura aquí también) y luego por antigüedad.
  static List<DonadorPared> leer(Object? v) {
    if (v is! List) return const [];
    final salida = <DonadorPared>[];
    for (final d in v) {
      if (d is! Map) continue;
      final usuario = '${d['usuario'] ?? ''}'.trim();
      final tipo = '${d['tipo'] ?? ''}'.trim().toLowerCase();
      if (usuario.isEmpty || (tipo != 'fundador' && tipo != 'donador')) continue;
      var nombre = '${d['nombre'] ?? ''}'.trim();
      if (nombre.isEmpty) nombre = usuario;
      salida.add(DonadorPared(
        usuario: usuario,
        nombre: nombre.length > 40 ? nombre.substring(0, 40) : nombre,
        tipo: tipo,
        color: Cosmeticos.colorNombre(d['color']),
        desde: d['desde'] == null ? null : DateTime.tryParse('${d['desde']}'),
      ));
    }
    final orden = {for (var k = 0; k < salida.length; k++) salida[k]: k};
    salida.sort((a, b) {
      if (a.fundador != b.fundador) return a.fundador ? -1 : 1;
      return orden[a]!.compareTo(orden[b]!);
    });
    return salida;
  }

  /// La pared desde el servidor: con sesión, como la cuenta; sin ella, como cualquiera (es pública).
  static Future<List<DonadorPared>> cargar(Social? social) async {
    final r = social != null
        ? await social.sesion.rpc('pared_agradecimiento')
        : await Nube.rpcPublico('pared_agradecimiento');
    return leer(r);
  }
}

// =============================================================== mascota propia

class MascotaPropia {
  MascotaPropia._();

  /// El WhatsApp de Caudal (el mismo de las donaciones).
  static const numero = '51902464984';

  /// Lo que se ve en la app junto al botón.
  static const explicacion =
      'Te escribimos por WhatsApp para diseñarla juntos: el diseño se aprueba por WhatsApp antes de añadirlo a tu cuenta.';

  /// El mensaje ya escrito.
  static String mensaje(String usuario) {
    final u = usuario.trim().replaceFirst('@', '');
    return u.isEmpty
        ? 'Hola, soy donador de Caudal. Quiero mi mascota personalizada.'
        : 'Hola, soy @$u en Caudal. Quiero mi mascota personalizada.';
  }

  /// El enlace que abre WhatsApp con el mensaje.
  static Uri enlace(String usuario) => Uri.parse('https://wa.me/$numero?text=${Uri.encodeComponent(mensaje(usuario))}');
}

// =============================================================== letra con efectos

class EscenaLetra {
  EscenaLetra._();

  static const _clave = 'letra_escena_estilo';

  static Future<String> estiloGuardado() async {
    try {
      final p = await SharedPreferences.getInstance();
      return Cosmeticos.estiloLetra(p.getString(_clave));
    } catch (_) {
      return Cosmeticos.estilosLetra.first;
    }
  }

  static Future<void> guardarEstilo(String estilo) async {
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_clave, Cosmeticos.estiloLetra(estilo));
    } catch (_) {}
  }

  /// El verso que suena a [ms] (-1 antes del primero). [lineas] van ordenadas por tiempo.
  static int indice(List<(int, String)> lineas, int ms) {
    var i = -1;
    for (var k = 0; k < lineas.length; k++) {
      if (lineas[k].$1 <= ms) {
        i = k;
      } else {
        break;
      }
    }
    return i;
  }

  /// Cuánto dura la entrada de un verso según el estilo (las palabras de «Ola» y las letras de «Cine»
  /// van una detrás de otra, así que tardan algo más en asentarse).
  static Duration entrada(String estilo, String texto) => switch (Cosmeticos.estiloLetra(estilo)) {
        'ola' => Duration(milliseconds: 420 + 90 * _palabras(texto).length.clamp(1, 12)),
        'cine' => Duration(milliseconds: 500 + 22 * texto.length.clamp(1, 60)),
        'neon' => const Duration(milliseconds: 700),
        'zoom' => const Duration(milliseconds: 520),
        'maquina' => Duration(milliseconds: 200 + 34 * texto.length.clamp(1, 60)),
        'lluvia' => Duration(milliseconds: 620 + 20 * texto.length.clamp(1, 60)),
        'giro' => Duration(milliseconds: 480 + 90 * _palabras(texto).length.clamp(1, 12)),
        _ => const Duration(milliseconds: 650),
      };

  /// La caída con rebote de «Lluvia»: 0 arriba, 1 en su sitio.
  static double rebote(double t) {
    const n = 7.5625, d = 2.75;
    if (t < 1 / d) return n * t * t;
    if (t < 2 / d) return n * (t -= 1.5 / d) * t + 0.75;
    if (t < 2.5 / d) return n * (t -= 2.25 / d) * t + 0.9375;
    return n * (t -= 2.625 / d) * t + 0.984375;
  }

  static List<String> _palabras(String t) => t.trim().split(RegExp(r'\s+')).where((w) => w.isNotEmpty).toList();

  /// Las palabras de un verso (para «Ola»).
  static List<String> palabras(String t) => _palabras(t);

  /// Cuánto se ve la pieza [k] de [n] (palabra o letra) cuando la entrada va por [t] (0..1):
  /// cada pieza empieza un poco después de la anterior y tarda lo mismo en aparecer.
  static double pieza(double t, int k, int n, {double solape = 0.55}) {
    if (n <= 1) return t.clamp(0.0, 1.0);
    final dur = 1 / (1 + (n - 1) * (1 - solape));
    final ini = k * dur * (1 - solape);
    return ((t - ini) / dur).clamp(0.0, 1.0);
  }

  /// El parpadeo del neón al encenderse: a [t] (0..1) devuelve la luz (0..1); al final, encendido fijo.
  static double neon(double t) {
    if (t >= 0.62) return 1;
    const golpes = [0.0, 0.9, 0.15, 1.0, 0.35, 1.0, 0.7];
    final i = (t / 0.62 * (golpes.length - 1)).floor().clamp(0, golpes.length - 1);
    return golpes[i];
  }
}
