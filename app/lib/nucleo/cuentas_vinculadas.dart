import 'dart:async';

import 'package:shared_preferences/shared_preferences.dart';

import 'coleccion.dart';
import 'importacion.dart';
import 'importar.dart';
import 'servicios_externos.dart';

/// Mantiene tus Me gusta de Caudal al día con las cuentas vinculadas: solo se busca lo que
/// aún no se había traído. Nunca quita nada de tus Me gusta.
class CuentasVinculadas {
  CuentasVinculadas._();

  /// Cada cuánto se mira solo, al abrir Caudal.
  static const cada = Duration(hours: 12);

  static String _k(ServicioMusica s, String que) => 'vinculada.${CuentaExterna.deCaudal}.${s.name}.$que';

  static Future<bool> alDia(ServicioMusica s) async =>
      (await SharedPreferences.getInstance()).getBool(_k(s, 'al_dia')) ?? true;

  static Future<void> ponerAlDia(ServicioMusica s, bool si) async =>
      (await SharedPreferences.getInstance()).setBool(_k(s, 'al_dia'), si);

  static Future<DateTime?> ultima(ServicioMusica s) async {
    final ms = (await SharedPreferences.getInstance()).getInt(_k(s, 'ultima'));
    return ms == null ? null : DateTime.fromMillisecondsSinceEpoch(ms);
  }

  /// Trae lo nuevo de [s]. Devuelve cuántas canciones quedan por buscar (0 = ya estaba todo).
  /// La búsqueda sigue en [TrabajoImportacion].
  static Future<int> sincronizar(Coleccion c, ServicioMusica s, {bool silencio = false}) async {
    final t = TrabajoImportacion.i;
    if (t.enMarcha) throw const ErrorImportar('Ya se están pasando canciones. Espera a que termine.');
    final cuenta = CuentaExterna.deCaudal;
    final l = await Importar.meGustaDe(s);
    if (CuentaExterna.deCaudal != cuenta) return 0;
    final ya = await TrabajoImportacion.traidas(c, s.name);
    // en silencio no se insiste con las que no se encontraron; a mano, sí
    final nuevas = [for (final x in l.canciones) if (silencio ? !ya.containsKey(x.claveExterna) : ya[x.claveExterna] != true) x];
    await (await SharedPreferences.getInstance()).setInt(_k(s, 'ultima'), DateTime.now().millisecondsSinceEpoch);
    if (nuevas.isEmpty || t.enMarcha) return 0;
    t.olvidarTerminado();
    await t.empezar(c,
        ListaExterna(plataforma: l.plataforma, titulo: l.titulo, canciones: nuevas, aviso: l.aviso, meGusta: true),
        meGusta: true, enlace: 'cuenta:${s.name}', cuenta: s.name, silencio: silencio);
    return nuevas.length;
  }

  static Future<void>? _mirando;

  /// Al abrir Caudal: lo nuevo de cada cuenta vinculada, una detrás de otra y sin molestar.
  static Future<void> alAbrir(Coleccion c, {required void Function(String) avisar}) =>
      _mirando ??= _alAbrir(c, avisar).whenComplete(() => _mirando = null);

  static Future<void> _alAbrir(Coleccion c, void Function(String) avisar) async {
    final t = TrabajoImportacion.i;
    for (final s in ServicioMusica.values) {
      try {
        if (!await CuentaExterna(s).vinculada() || !await alDia(s)) continue;
        final u = await ultima(s);
        if (u != null && DateTime.now().difference(u) < cada) continue;
        // algo a medias (o en marcha) va primero: no se pisa
        if (t.enMarcha || await TrabajoImportacion.pendiente(c) != null) return;
        if (await sincronizar(c, s, silencio: true) == 0) continue;
        await t.alTerminar;
        if (t.terminado && t.anadidas > 0) {
          avisar(t.anadidas == 1 ? 'Una canción nueva de ${s.nombre} en tus Me gusta'
              : '${miles(t.anadidas)} canciones nuevas de ${s.nombre} en tus Me gusta');
        }
        if (t.terminado) t.olvidarTerminado();
      } on ErrorImportar catch (e) {
        // solo si hay que hacer algo; un fallo de red se vuelve a mirar la próxima vez
        if (!await CuentaExterna(s).vinculada()) avisar(e.mensaje);
      } catch (_) {}
    }
  }
}
