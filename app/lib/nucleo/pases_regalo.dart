import 'package:shared_preferences/shared_preferences.dart';

import 'nube.dart';
import 'premium.dart';
import 'social.dart';

/// Pases de regalo: un donador (o fundador) crea códigos de prueba de 7 días para sus amigos.
/// El servidor manda (`crear_pase_regalo`, `mis_pases_regalo`, `anular_pase_regalo`): aquí solo se
/// pregunta y se leen sus respuestas. Los mensajes del servidor se devuelven tal cual.

/// Dónde se instala Caudal (va en el texto que se comparte).
const String enlaceCaudal = 'https://caudal-musica.netlify.app';

/// En qué estado está un código que creaste.
enum EstadoPase { sinUsar, usado, caducado }

extension EtiquetaEstadoPase on EstadoPase {
  String get etiqueta => switch (this) {
        EstadoPase.sinUsar => 'Sin usar',
        EstadoPase.usado => 'Usado',
        EstadoPase.caducado => 'Caducado',
      };
}

/// Un código de la lista (`mis_pases_regalo`).
class PaseRegalo {
  const PaseRegalo({
    required this.codigo,
    this.dias = 7,
    this.usado = false,
    this.caduca,
    this.vigente = true,
  });

  final String codigo;
  final int dias;
  final bool usado;
  final DateTime? caduca;
  final bool vigente;

  /// Usado gana sobre caducado: si alguien lo canjeó, eso es lo que importa.
  EstadoPase get estado => usado ? EstadoPase.usado : (vigente ? EstadoPase.sinUsar : EstadoPase.caducado);

  /// Solo los que nadie ha usado se pueden anular (el servidor también lo exige).
  bool get sePuedeAnular => !usado;

  /// Sin usar y todavía canjeable: lo que cuenta para el tope de 3.
  bool get sinUsar => estado == EstadoPase.sinUsar;

  static PaseRegalo? desde(Object? v) {
    if (v is! Map) return null;
    final codigo = '${v['codigo'] ?? ''}'.trim().toUpperCase();
    if (codigo.isEmpty) return null;
    final dias = v['dias'];
    return PaseRegalo(
      codigo: codigo,
      dias: dias is num ? dias.toInt() : int.tryParse('${dias ?? ''}') ?? 7,
      usado: v['usado'] == true,
      caduca: v['caduca'] == null ? null : DateTime.tryParse('${v['caduca']}')?.toLocal(),
      vigente: v['vigente'] != false,
    );
  }

  /// La lista tal cual la manda el servidor (acepta basura sin romperse).
  static List<PaseRegalo> lista(Object? v) {
    if (v is! List) return const [];
    return [
      for (final e in v)
        if (PaseRegalo.desde(e) case final p?) p,
    ];
  }
}

/// La respuesta de `crear_pase_regalo`.
class ResultadoCrearPase {
  const ResultadoCrearPase({required this.ok, required this.mensaje, this.pase});
  final bool ok;
  final String mensaje;
  final PaseRegalo? pase;

  static ResultadoCrearPase desde(Object? v) {
    final m = v is List && v.isNotEmpty ? v.first : v;
    if (m is! Map) {
      return const ResultadoCrearPase(ok: false, mensaje: 'No se pudo crear el código. Inténtalo otra vez.');
    }
    final mensaje = '${m['mensaje'] ?? ''}'.trim();
    final codigo = '${m['codigo'] ?? ''}'.trim().toUpperCase();
    if (m['ok'] != true || codigo.isEmpty) {
      return ResultadoCrearPase(
          ok: false, mensaje: mensaje.isEmpty ? 'No se pudo crear el código. Inténtalo otra vez.' : mensaje);
    }
    final dias = m['dias'];
    return ResultadoCrearPase(
      ok: true,
      mensaje: mensaje,
      pase: PaseRegalo(
        codigo: codigo,
        dias: dias is num ? dias.toInt() : int.tryParse('${dias ?? ''}') ?? 7,
        caduca: m['caduca'] == null ? null : DateTime.tryParse('${m['caduca']}')?.toLocal(),
      ),
    );
  }
}

/// El resultado de anular un código.
class ResultadoAnular {
  const ResultadoAnular({required this.ok, required this.mensaje});
  final bool ok;
  final String mensaje;
}

class PasesRegalo {
  PasesRegalo._();

  /// Tope de códigos sin usar a la vez (lo controla el servidor; aquí solo se usa para avisar).
  static const maxSinUsar = 3;

  /// Solo donadores y fundadores regalan; una prueba no puede regalar pruebas.
  static bool puedeRegalar(EstadoPremium e, [DateTime? ahora]) =>
      e.vigente(ahora) && (e.tipo == 'donador' || e.tipo == 'fundador');

  static int sinUsar(Iterable<PaseRegalo> pases) => pases.where((p) => p.sinUsar).length;

  /// El texto para mandar por WhatsApp y demás: el código y dónde instalar Caudal.
  static String textoCompartir(String codigo, {int dias = 7}) =>
      'Te regalo una prueba de $dias días de los beneficios de donador de Caudal.\n'
      'Tu código: $codigo\n'
      'Instala Caudal en $enlaceCaudal y canjéalo en Ajustes, con «Tengo un código de prueba».';

  /// Crea un código. Los fallos de red o del servidor vuelven como mensaje, sin lanzar.
  static Future<ResultadoCrearPase> crear(Social social) async {
    try {
      return ResultadoCrearPase.desde(await social.sesion.rpc('crear_pase_regalo'));
    } on SinConexion catch (e) {
      return ResultadoCrearPase(ok: false, mensaje: e.mensaje);
    } on ErrorNube catch (e) {
      return ResultadoCrearPase(ok: false, mensaje: e.mensaje);
    } catch (_) {
      return const ResultadoCrearPase(ok: false, mensaje: 'No se pudo crear el código. Revisa tu internet.');
    }
  }

  /// Mis códigos, los más nuevos primero. Lanza [ErrorNube] si falla (la pantalla lo muestra).
  static Future<List<PaseRegalo>> listar(Social social) async =>
      PaseRegalo.lista(await social.sesion.rpc('mis_pases_regalo'));

  /// Anula un código que nadie ha usado. `false` del servidor = ya no se podía.
  static Future<ResultadoAnular> anular(Social social, String codigo) async {
    try {
      final r = await social.sesion.rpc('anular_pase_regalo', {'p_codigo': codigo.trim().toUpperCase()});
      return r == true
          ? const ResultadoAnular(ok: true, mensaje: 'Código anulado.')
          : const ResultadoAnular(ok: false, mensaje: 'Ese código ya no se puede anular: alguien lo usó.');
    } on ErrorNube catch (e) {
      return ResultadoAnular(ok: false, mensaje: e.mensaje);
    } catch (_) {
      return const ResultadoAnular(ok: false, mensaje: 'No se pudo anular el código. Revisa tu internet.');
    }
  }
}

/// El aviso de una sola vez «Ahora puedes regalar códigos de prueba».
class AvisoPasesRegalo {
  AvisoPasesRegalo._();

  static const clave = 'aviso_pases_regalo_visto';

  static Future<bool> yaVisto([SharedPreferences? p]) async =>
      ((p ?? await SharedPreferences.getInstance()).getBool(clave)) == true;

  static Future<void> marcarVisto([SharedPreferences? p]) async =>
      (p ?? await SharedPreferences.getInstance()).setBool(clave, true);

  /// ¿Toca enseñarlo? Solo a donadores/fundadores y una única vez.
  static Future<bool> toca(EstadoPremium e) async {
    if (!PasesRegalo.puedeRegalar(e)) return false;
    try {
      return !await yaVisto();
    } catch (_) {
      return false;
    }
  }
}
