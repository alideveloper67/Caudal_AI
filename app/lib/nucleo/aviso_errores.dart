// Aviso de errores: los cierres y errores que nadie atrapó se mandan a la nube de Caudal (tabla
// `errores_app`, supabase/errores_app.sql), sin servicios de terceros y sin datos personales.
//
// Igual que escritorio/descargador/aviso_errores.py. Cada informe lleva: plataforma, versión,
// sistema, la pantalla que estaba abierta, el tipo de error, el mensaje y la traza. Antes de salir
// del teléfono se borran rutas con el nombre de la persona, correos, enlaces con datos y cosas que
// parecen claves. No va el usuario ni el id de la cuenta.
//
// - Se apaga desde Ajustes («Enviar informes de errores»); apagado no se guarda ni se manda nada.
// - Sin red, los informes esperan en una cola (preferencias) y salen en otro momento.
// - Freno: el mismo error se junta (se cuenta cuántas veces pasó) y sale como mucho una vez cada
//   6 horas; como mucho 20 informes al día y 30 errores distintos en cola.
//
// Se engancha en main.dart envolviendo todo en la zona y conectando los ganchos de Flutter
// (FlutterError.onError y PlatformDispatcher.onError), sin quitar los que ya había (Diagnostico).

import 'dart:async';
import 'dart:convert';
import 'dart:io' show Platform;

import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'avisos.dart';
import 'nube.dart';
import 'version.dart';

class AvisoErrores {
  AvisoErrores._();

  static const esperaMismo = Duration(hours: 6);
  static const topeDia = 20;
  static const topeCola = 30;
  static const topeSesion = 60;
  static const pausaSinTabla = Duration(hours: 24);

  static const _claveActivo = 'aviso_errores_activo';
  static const _claveCola = 'aviso_errores_cola';
  static const _claveEnvios = 'aviso_errores_envios';

  /// Para las pruebas: sustituye el envío (devuelve el código HTTP; 0 = sin red).
  @visibleForTesting
  static Future<int> Function(Map<String, dynamic> fila)? enviarParaPruebas;

  /// Para las pruebas: la hora "ahora".
  @visibleForTesting
  static DateTime Function() reloj = DateTime.now;

  static int _capturas = 0;
  static bool _instalado = false;
  static Timer? _temporizador;

  /// La pantalla abierta: la pone el observador del navegador (o quien quiera, a mano).
  static String pantalla = '';

  /// Observador para `MaterialApp.navigatorObservers`: va anotando qué pantalla está arriba.
  static final NavigatorObserver observador = _Observador();

  // ------------------------------------------------------------ ajuste

  static Future<bool> activo() async {
    try {
      final p = await SharedPreferences.getInstance();
      return p.getBool(_claveActivo) ?? true;
    } catch (_) {
      return true;
    }
  }

  static Future<void> ponerActivo(bool si) async {
    try {
      final p = await SharedPreferences.getInstance();
      await p.setBool(_claveActivo, si);
      if (!si) await p.remove(_claveCola); // apagado: lo que esperaba tampoco sale
    } catch (_) {}
  }

  // ------------------------------------------------------------ enganche

  /// Conecta los ganchos de Flutter sin quitar los que ya había.
  static void instalar() {
    if (_instalado) return;
    _instalado = true;
    _capturas = 0;
    final previoFlutter = FlutterError.onError;
    FlutterError.onError = (d) {
      previoFlutter?.call(d);
      // los avisos "silenciosos" (p. ej. una imagen que no cargó) no son errores de la app
      if (!d.silent) capturar(d.exception, d.stack, origen: 'flutter');
    };
    final previoPlataforma = PlatformDispatcher.instance.onError;
    PlatformDispatcher.instance.onError = (e, pila) {
      capturar(e, pila, origen: 'plataforma');
      return previoPlataforma?.call(e, pila) ?? true;
    };
    // lo que quedó en cola de otra vez sale en un rato (sin estorbar al arranque)
    _programar(const Duration(seconds: 20));
  }

  /// Corre [cuerpo] dentro de una zona que atrapa los errores asíncronos que nadie atrapó.
  /// En main.dart: `Future<void> main() => AvisoErrores.enZona(() async { ... });` y, dentro,
  /// `AvisoErrores.instalar()` justo después de poner los ganchos de siempre (así los encadena).
  static Future<void> enZona(Future<void> Function() cuerpo) {
    final listo = Completer<void>();
    runZonedGuarded(() async {
      try {
        await cuerpo();
      } finally {
        if (!listo.isCompleted) listo.complete();
      }
    }, (e, pila) {
      capturar(e, pila, origen: 'zona');
      if (!listo.isCompleted) listo.complete();
    });
    return listo.future;
  }

  @visibleForTesting
  static void reiniciarParaPruebas() {
    _instalado = false;
    _capturas = 0;
    pantalla = '';
    _temporizador?.cancel();
    _temporizador = null;
    reloj = DateTime.now;
    enviarParaPruebas = null;
  }

  // ------------------------------------------------------------ informe

  /// Quita lo personal de un texto (rutas de usuario, correos, tokens, datos de enlaces).
  static String limpiar(String t) {
    t = t.replaceAllMapped(
        RegExp(r'([a-zA-Z]:[\\/]+(?:[Uu]sers|[Uu]suarios)[\\/]+)[^\\/"' "'" r'<>|:,\r\n]+'), (m) => '${m[1]}~');
    t = t.replaceAllMapped(RegExp(r'(/(?:home|Users)/)[^/\s"' "'" r']+'), (m) => '${m[1]}~');
    // Android e iPhone: carpetas con el nombre del dispositivo o de la persona no hay, pero sí
    // ids de la app en las rutas de datos (no son personales); los correos y tokens sí lo son
    t = t.replaceAll(RegExp(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+'), '<correo>');
    t = t.replaceAll(RegExp(r'eyJ[\w-]{6,}\.[\w-]{6,}\.[\w-]*'), '<token>');
    t = t.replaceAllMapped(RegExp(r'''(https?://[^\s"'<>?#]+)[?#][^\s"'<>]*'''), (m) => '${m[1]}?…');
    t = t.replaceAll(RegExp(r'\b[A-Za-z0-9_\-]{32,}\b'), '<clave>');
    return t;
  }

  /// Igual error = igual huella: tipo + archivo:función de cada marco (sin líneas ni columnas).
  static String huella(String tipo, String traza) {
    final marcos = <String>[];
    for (final l in traza.split('\n')) {
      // «#3      Clase.metodo (package:caudal/ui/x.dart:12:7)»
      final m = RegExp(r'^#\d+\s+(.+?) \((.+?)(?::\d+)*\)').firstMatch(l.trim());
      if (m != null) {
        final archivo = m[2]!.split('/').last;
        marcos.add('$archivo:${m[1]}');
      } else if (l.trim().isNotEmpty && marcos.isEmpty && !l.contains('#')) {
        // trazas de otro formato (web): la línea sin números
        marcos.add(l.replaceAll(RegExp(r'[:\d]+'), '').trim());
      }
      if (marcos.length >= 25) break;
    }
    final base = '$tipo|${marcos.join('|')}';
    return sha256.convert(utf8.encode(base)).toString().substring(0, 20);
  }

  /// El informe (mapa con las columnas de la tabla) de un error.
  static Map<String, dynamic> informe(Object error, StackTrace? pila,
      {String origen = '', String? pantallaActual, String? version, String? sistema, String? plataforma}) {
    final tipo = error.runtimeType.toString();
    final traza = pila == null ? '' : pila.toString();
    final ahora = reloj().millisecondsSinceEpoch / 1000;
    final limpia = limpiar(traza);
    return {
      'plataforma': plataforma ?? _plataformaTabla(),
      'version': (version ?? versionApp).substring(0, (version ?? versionApp).length.clamp(0, 24)),
      'sistema': _corta(sistema ?? sistemaActual(), 120),
      'pantalla': _corta(limpiar(pantallaActual ?? pantalla), 80),
      'origen': _corta(origen, 40),
      'tipo': _corta(limpiar(tipo), 160),
      'mensaje': _corta(limpiar(_mensaje(error)), 600),
      // lo último de la traza es lo menos útil en Dart (el arranque): se recorta por el final
      'traza': _corta(limpia, 8000),
      'huella': huella(tipo, traza),
      'veces': 1,
      'primera_vez': ahora,
      'ultima_vez': ahora,
    };
  }

  static String _mensaje(Object e) {
    try {
      return e.toString();
    } catch (_) {
      return e.runtimeType.toString();
    }
  }

  /// «android 14 (…)», «ios 18.1», «windows …»; en el navegador, solo «web».
  static String sistemaActual() {
    if (kIsWeb) return 'web';
    try {
      return '${Platform.operatingSystem} ${Platform.operatingSystemVersion}';
    } catch (_) {
      return defaultTargetPlatform.name;
    }
  }

  static String _corta(String t, int n) => t.length <= n ? t : '${t.substring(0, n - 1)}…';

  static String _plataformaTabla() {
    final p = Avisos.plataforma;
    return const {'web', 'android', 'ios', 'windows'}.contains(p) ? p : 'otra';
  }

  // ------------------------------------------------------------ captura y cola

  /// Anota un error no controlado. Nunca lanza.
  static void capturar(Object error, StackTrace? pila, {String origen = ''}) {
    try {
      _capturas++;
      if (_capturas > topeSesion) return;
      final inf = informe(error, pila, origen: origen, pantallaActual: _pantallaActual());
      unawaited(encolar(inf).then((ok) {
        if (ok) _programar(const Duration(seconds: 5));
      }, onError: (_) {}));
    } catch (_) {}
  }

  /// Anota un informe ya armado (p. ej. un cierre de Android leído al volver a abrir) y lo manda
  /// en un rato. Nunca lanza.
  static Future<void> anotarInforme(Map<String, dynamic> inf) async {
    try {
      if (await encolar(inf)) _programar(const Duration(seconds: 5));
    } catch (_) {}
  }

  static String _pantallaActual() {
    if (pantalla.isNotEmpty) return pantalla;
    return (observador as _Observador).nombre();
  }

  static Future<List<Map<String, dynamic>>> cola() async {
    try {
      final p = await SharedPreferences.getInstance();
      final d = jsonDecode(p.getString(_claveCola) ?? '[]');
      if (d is! List) return [];
      return [
        for (final x in d)
          if (x is Map && x['huella'] is String) Map<String, dynamic>.from(x),
      ];
    } catch (_) {
      return [];
    }
  }

  static Future<void> _guardarCola(List<Map<String, dynamic>> c) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_claveCola, jsonEncode(c));
  }

  // las escrituras de la cola van de una en una (dos errores seguidos no se pisan)
  static Future<void> _turno = Future.value();
  static Future<T> _enTurno<T>(Future<T> Function() f) {
    final r = _turno.then((_) => f());
    _turno = r.then((_) {}, onError: (_) {});
    return r;
  }

  /// Guarda el informe en la cola (junta los repetidos). false si no se guardó (apagado).
  static Future<bool> encolar(Map<String, dynamic> inf) => _enTurno(() async {
        if (!await activo()) return false;
        final c = await cola();
        final i = c.indexWhere((x) => x['huella'] == inf['huella']);
        if (i >= 0) {
          final x = c[i];
          x['veces'] = ((x['veces'] as num? ?? 1) + (inf['veces'] as num? ?? 1)).clamp(1, 100000).toInt();
          x['ultima_vez'] = inf['ultima_vez'];
          for (final k in const ['version', 'pantalla', 'mensaje', 'traza', 'sistema']) {
            x[k] = inf[k];
          }
        } else {
          c.add(Map.of(inf));
        }
        c.sort((a, b) => ((a['ultima_vez'] as num?) ?? 0).compareTo((b['ultima_vez'] as num?) ?? 0));
        await _guardarCola(c.length > topeCola ? c.sublist(c.length - topeCola) : c);
        return true;
      });

  static Future<Map<String, dynamic>> _envios() async {
    Map<String, dynamic> e = {};
    try {
      final p = await SharedPreferences.getInstance();
      final d = jsonDecode(p.getString(_claveEnvios) ?? '{}');
      if (d is Map) e = Map<String, dynamic>.from(d);
    } catch (_) {}
    final ahora = reloj();
    final hoy = '${ahora.year}-${ahora.month}-${ahora.day}';
    if (e['dia'] != hoy) {
      e = {'dia': hoy, 'n': 0, 'huellas': e['huellas'] ?? {}, 'pausa_hasta': e['pausa_hasta'] ?? 0};
    }
    final limite = ahora.millisecondsSinceEpoch / 1000 - 2 * 86400;
    final h = e['huellas'];
    e['huellas'] = <String, dynamic>{
      if (h is Map)
        for (final x in h.entries)
          if (x.value is num && (x.value as num) > limite) '${x.key}': x.value,
    };
    e['pausa_hasta'] = e['pausa_hasta'] is num ? e['pausa_hasta'] : 0;
    return e;
  }

  static Future<void> _guardarEnvios(Map<String, dynamic> e) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_claveEnvios, jsonEncode(e));
  }

  /// Los informes de la cola que pueden salir ya (respetando los frenos).
  static Future<List<Map<String, dynamic>>> paraEnviar() async {
    final ahora = reloj().millisecondsSinceEpoch / 1000;
    final e = await _envios();
    if ((e['pausa_hasta'] as num) > ahora) return [];
    final libres = (topeDia - ((e['n'] as num?) ?? 0)).clamp(0, topeDia).toInt();
    final huellas = e['huellas'] as Map<String, dynamic>;
    final listos = [
      for (final x in await cola())
        if (ahora - ((huellas[x['huella']] as num?) ?? 0) >= esperaMismo.inSeconds) x,
    ];
    return listos.take(libres).toList();
  }

  static String? _iso(Object? t) => t is num
      ? DateTime.fromMillisecondsSinceEpoch((t * 1000).round(), isUtc: true).toIso8601String()
      : null;

  static Future<int> _post(Map<String, dynamic> fila) async {
    try {
      final r = await http
          .post(Uri.parse('${Nube.url}/rest/v1/errores_app'),
              headers: {
                'apikey': Nube.clavePublica,
                'Authorization': 'Bearer ${Nube.clavePublica}',
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal',
              },
              body: jsonEncode(fila))
          .timeout(const Duration(seconds: 15));
      return r.statusCode;
    } catch (_) {
      return 0; // sin red: sigue en la cola
    }
  }

  /// Manda lo que se pueda de la cola. Devuelve cuántos salieron. Nunca lanza.
  static Future<int> enviarPendientes() => _enTurno(() async {
        var salieron = 0;
        try {
          if (!await activo()) return 0;
          final enviar = enviarParaPruebas ?? _post;
          final ahora = reloj().millisecondsSinceEpoch / 1000;
          for (final inf in await paraEnviar()) {
            final fila = <String, dynamic>{
              for (final k in const ['plataforma', 'version', 'sistema', 'pantalla', 'origen', 'tipo', 'mensaje',
                'traza', 'huella', 'veces'])
                k: inf[k],
              'primera_vez': _iso(inf['primera_vez']),
              'ultima_vez': _iso(inf['ultima_vez']),
            };
            final codigo = await enviar(fila);
            final e = await _envios();
            if ((codigo >= 200 && codigo < 300) || const {400, 409, 413, 422}.contains(codigo)) {
              // salió (o el servidor no lo quiere nunca): fuera de la cola
              await _guardarCola([for (final x in await cola()) if (x['huella'] != inf['huella']) x]);
              if (codigo >= 200 && codigo < 300) {
                (e['huellas'] as Map<String, dynamic>)[inf['huella'] as String] = ahora;
                e['n'] = ((e['n'] as num?) ?? 0) + 1;
                salieron++;
              }
              await _guardarEnvios(e);
            } else if (codigo == 404) {
              // el servidor aún no tiene la tabla (migración sin aplicar): mañana se prueba
              e['pausa_hasta'] = ahora + pausaSinTabla.inSeconds;
              await _guardarEnvios(e);
              break;
            } else {
              break; // sin red o servidor caído: otro momento
            }
          }
        } catch (_) {}
        return salieron;
      });

  static void _programar(Duration espera) {
    if (_temporizador?.isActive ?? false) return;
    _temporizador = Timer(espera, () => unawaited(enviarPendientes()));
  }
}

/// Va anotando la ruta de arriba; el nombre se calcula solo cuando hace falta (al fallar algo).
class _Observador extends NavigatorObserver {
  Route<dynamic>? _arriba;

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) => _arriba = route;

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) => _arriba = previousRoute;

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) => _arriba = newRoute;

  @override
  void didRemove(Route<dynamic> route, Route<dynamic>? previousRoute) {
    if (identical(route, _arriba)) _arriba = previousRoute;
  }

  /// El nombre de la ruta, o el de la primera pantalla propia que haya dentro (…Pagina, …Hoja).
  String nombre() {
    final r = _arriba;
    if (r == null) return '';
    final n = r.settings.name;
    if (n != null && n.isNotEmpty && n != '/') return n;
    try {
      final ctx = r is ModalRoute ? r.subtreeContext : null;
      if (ctx != null) {
        String? hallado;
        var revisados = 0;
        void mirar(Element e) {
          if (hallado != null || revisados++ > 400) return;
          final t = e.widget.runtimeType.toString();
          if (RegExp(r'(Pagina|Hoja|Pantalla|Dialogo)$').hasMatch(t)) {
            hallado = t;
            return;
          }
          e.visitChildElements(mirar);
        }
        (ctx as Element).visitChildElements(mirar);
        if (hallado != null) return hallado!;
      }
    } catch (_) {}
    return r is PopupRoute ? 'emergente' : (r.isFirst ? 'principal' : 'pantalla');
  }
}
