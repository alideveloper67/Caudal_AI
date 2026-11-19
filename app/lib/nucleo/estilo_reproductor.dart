import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'premium_letras.dart';

/// Cómo se ve la pantalla del reproductor grande.
enum EstiloReproductor {
  clasico('Clásico', 'La carátula grande, como siempre'),
  vinilo('Vinilo', 'Un tocadiscos con el disco girando'),
  casete('Casete', 'Un casete con sus carretes que dan vueltas'),
  neon('Neón', 'La carátula con un borde de luz que late'),
  flotante('Flotante', 'La carátula flota y tu mascota la acompaña');

  const EstiloReproductor(this.nombre, this.descripcion);
  final String nombre;
  final String descripcion;

  /// El vinilo ya existía para todos: se queda libre. El resto es de donadores.
  bool get soloDonadores => this != clasico && this != vinilo;

  static EstiloReproductor desde(Object? v) {
    for (final e in values) {
      if (e.name == v) return e;
    }
    return clasico;
  }
}

/// El sonidito de la interfaz.
enum SonidoUi {
  burbuja('Burbuja', 'burbuja.wav'),
  moneda('Moneda', 'moneda.wav'),
  campana('Campana', 'campana.wav');

  const SonidoUi(this.nombre, this.archivo);
  final String nombre;
  final String archivo;

  String get asset => 'assets/sonidos/$archivo';

  static SonidoUi desde(Object? v) {
    for (final e in values) {
      if (e.name == v) return e;
    }
    return burbuja;
  }
}

/// Lo que cada quien eligió para su reproductor: estilo, colores de la carátula y sonidos.
/// Se recuerda en el teléfono. Una sola instancia ([PreferenciasReproductor.i]).
///
/// Lo de donadores solo vale mientras haya beneficios: sin ellos todo vuelve a lo normal sin
/// borrar la elección (igual que el marco o el tema).
class PreferenciasReproductor extends ChangeNotifier {
  PreferenciasReproductor();
  static final PreferenciasReproductor i = PreferenciasReproductor();

  EstiloReproductor estilo = EstiloReproductor.clasico;
  bool coloresDePortada = true;
  bool sonidoMeGusta = false;
  bool sonidoAlAbrir = false;
  SonidoUi sonido = SonidoUi.burbuja;

  /// 0.05 a 0.6: bajito a propósito.
  double volumenSonido = 0.25;

  bool _cargado = false;
  bool get cargado => _cargado;

  static const _kEstilo = 'rep_estilo';
  static const _kColores = 'rep_colores';
  static const _kLike = 'rep_snd_like';
  static const _kAbrir = 'rep_snd_abrir';
  static const _kCual = 'rep_snd_cual';
  static const _kVol = 'rep_snd_vol';

  /// El estilo que de verdad se pinta (sin beneficios, los de donador vuelven al clásico).
  EstiloReproductor get estiloEfectivo =>
      estilo.soloDonadores && !esPremiumLetras() ? EstiloReproductor.clasico : estilo;

  /// ¿Los colores siguen a la carátula? (solo donadores y si no lo apagó).
  bool get coloresActivos => coloresDePortada && esPremiumLetras();

  Future<void> cargar() async {
    if (_cargado) return;
    try {
      final p = await SharedPreferences.getInstance();
      final e = p.getString(_kEstilo);
      // quien ya tenía puesto el vinilo (la opción de antes) lo conserva
      estilo = e != null
          ? EstiloReproductor.desde(e)
          : (p.getBool('modo_vinilo') == true ? EstiloReproductor.vinilo : EstiloReproductor.clasico);
      coloresDePortada = p.getBool(_kColores) ?? true;
      sonidoMeGusta = p.getBool(_kLike) ?? false;
      sonidoAlAbrir = p.getBool(_kAbrir) ?? false;
      sonido = SonidoUi.desde(p.getString(_kCual));
      volumenSonido = (p.getDouble(_kVol) ?? 0.25).clamp(0.05, 0.6);
    } catch (_) {}
    _cargado = true;
    notifyListeners();
  }

  Future<void> _guardar(Future<bool> Function(SharedPreferences p) f) async {
    try {
      await f(await SharedPreferences.getInstance());
    } catch (_) {}
  }

  /// Cambia de estilo. Un estilo de donadores sin beneficios no se acepta (devuelve false).
  Future<bool> elegirEstilo(EstiloReproductor e) async {
    if (e.soloDonadores && !esPremiumLetras()) return false;
    if (e == estilo) return true;
    estilo = e;
    notifyListeners();
    await _guardar((p) => p.setString(_kEstilo, e.name));
    // el vinilo de antes se guardaba aparte: se mantiene al día por si se vuelve atrás
    await _guardar((p) => p.setBool('modo_vinilo', e == EstiloReproductor.vinilo));
    return true;
  }

  Future<void> ponerColores(bool v) async {
    if (v == coloresDePortada) return;
    coloresDePortada = v;
    notifyListeners();
    await _guardar((p) => p.setBool(_kColores, v));
  }

  Future<void> ponerSonidoMeGusta(bool v) async {
    if (v == sonidoMeGusta) return;
    sonidoMeGusta = v;
    notifyListeners();
    await _guardar((p) => p.setBool(_kLike, v));
  }

  Future<void> ponerSonidoAlAbrir(bool v) async {
    if (v == sonidoAlAbrir) return;
    sonidoAlAbrir = v;
    notifyListeners();
    await _guardar((p) => p.setBool(_kAbrir, v));
  }

  Future<void> elegirSonido(SonidoUi s) async {
    if (s == sonido) return;
    sonido = s;
    notifyListeners();
    await _guardar((p) => p.setString(_kCual, s.name));
  }

  Future<void> ponerVolumenSonido(double v, {bool guardar = true}) async {
    final n = v.clamp(0.05, 0.6);
    if (n == volumenSonido) return;
    volumenSonido = n;
    notifyListeners();
    if (guardar) await _guardar((p) => p.setDouble(_kVol, n));
  }

  /// Solo para pruebas: deja todo como recién instalado.
  @visibleForTesting
  void reiniciarParaPruebas() {
    estilo = EstiloReproductor.clasico;
    coloresDePortada = true;
    sonidoMeGusta = sonidoAlAbrir = false;
    sonido = SonidoUi.burbuja;
    volumenSonido = 0.25;
    _cargado = false;
  }
}
