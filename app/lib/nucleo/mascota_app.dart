import 'dart:convert';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:shared_preferences/shared_preferences.dart';

import 'fondo_app.dart';

/// Una mascotita del catálogo (`assets/mascotas/catalogo.json`).
class Mascota {
  const Mascota({
    required this.clave,
    required this.nombre,
    required this.origen,
    required this.ancho,
    this.cuadros = 2,
    this.densidad = 1,
    required this.alto,
    required this.arcoiris,
    this.estela = '',
    this.estelaAncho = 11,
    this.estelaAlto = 11,
    this.soloCuentas = const [],
  });

  /// Si no está vacía, la mascota es solo de esas cuentas (sus ids en la nube):
  /// solo ellas la ven y la pueden elegir, aunque no sean donadoras.
  final List<String> soloCuentas;

  bool get esExclusiva => soloCuentas.isNotEmpty;

  /// ¿Es de esta cuenta? (las que no son exclusivas son de todas)
  bool esDe(String cuenta) => !esExclusiva || (cuenta.isNotEmpty && soloCuentas.contains(cuenta));

  final String clave, nombre, origen;

  /// Tamaño de UN cuadro (la hoja trae [cuadros] lado a lado).
  final int ancho, alto;

  /// Cuántos cuadros de animación trae la hoja (2 o más; por defecto 2).
  final int cuadros;

  /// Píxeles de la hoja por píxel en pantalla (por defecto 1). Con 2 la hoja trae el doble de detalle:
  /// cada cuadro mide (ancho*2)x(alto*2) y se dibuja en el espacio de [ancho]x[alto].
  final int densidad;

  /// Deja una estela de arcoíris detrás (Nyan Cat).
  final bool arcoiris;

  /// Forma del detallito que va quedando atrás ('' = ninguno; Nyan usa su arcoíris).
  final String estela;
  final int estelaAncho, estelaAlto;

  bool get tieneEstela => estela.isNotEmpty && !arcoiris;

  String get imagenEstela => 'assets/mascotas/estela_$clave.png';

  String get imagen => 'assets/mascotas/$clave.png';

  static Mascota? desdeJson(Object? j) {
    if (j is! Map) return null;
    final clave = '${j['clave'] ?? ''}';
    if (clave.isEmpty) return null;
    return Mascota(
      clave: clave,
      nombre: '${j['nombre'] ?? clave}',
      origen: '${j['origen'] ?? ''}',
      ancho: (j['ancho'] as num?)?.toInt() ?? 24,
      cuadros: math.max(2, (j['cuadros'] as num?)?.toInt() ?? 2),
      densidad: math.max(1, (j['densidad'] as num?)?.toInt() ?? 1),
      alto: (j['alto'] as num?)?.toInt() ?? 22,
      arcoiris: j['arcoiris'] == true,
      estela: '${j['estela'] ?? ''}',
      estelaAncho: (j['estela_ancho'] as num?)?.toInt() ?? 11,
      estelaAlto: (j['estela_alto'] as num?)?.toInt() ?? 11,
      soloCuentas: [
        for (final x in (j['solo_cuentas'] is List ? j['solo_cuentas'] as List : [j['solo_cuenta']]))
          if (x != null && '$x'.isNotEmpty) '$x',
      ],
    );
  }
}

List<Mascota> leerCatalogoMascotas(String texto) {
  final d = jsonDecode(texto);
  if (d is! List) return const [];
  return d.map(Mascota.desdeJson).whereType<Mascota>().toList();
}

/// «Mascotita del reproductor»: un personaje que camina sobre la barra de
/// progreso. Es exclusivo de las cuentas «Donador de Caudal» y «Fundador de
/// Caudal»: el permiso es el mismo del fondo ([FondoApp.puede]) y lo decide el
/// servidor. La elección se guarda en el teléfono, por cuenta.
class MascotaApp extends ChangeNotifier {
  MascotaApp._() {
    // si el permiso cambia (entra una cuenta, deja de ser donadora...), se repinta
    FondoApp.i.addListener(notifyListeners);
  }
  static final MascotaApp i = MascotaApp._();

  List<Mascota> catalogo = const [];

  /// La elegida ('' = ninguna).
  String clave = '';

  String _cuenta = '';
  final _imagenes = <String, Future<ui.Image?>>{};
  final _estelas = <String, Future<ui.Image?>>{};

  bool get puede => FondoApp.i.puede;

  /// Lo que ve esta cuenta: sin las exclusivas de otras cuentas.
  List<Mascota> get disponibles => [for (final m in catalogo) if (m.esDe(_cuenta)) m];

  /// Las de siempre: donadores y fundadores. Una exclusiva: solo sus cuentas.
  bool puedeElegir(Mascota m) => m.esExclusiva ? m.esDe(_cuenta) : puede;

  /// Esta cuenta tiene alguna mascota solo suya.
  bool get tieneExclusivas => _cuenta.isNotEmpty && catalogo.any((m) => m.esExclusiva && m.esDe(_cuenta));

  Mascota? get actual {
    for (final m in disponibles) {
      if (m.clave == clave) return m;
    }
    return null;
  }

  /// Se muestra solo si hay una elegida que exista y la cuenta pueda tenerla.
  bool get activa {
    final m = actual;
    return m != null && puedeElegir(m);
  }

  Future<void> cargarCatalogo({String? texto}) async {
    if (catalogo.isNotEmpty && texto == null) return;
    try {
      catalogo = leerCatalogoMascotas(texto ?? await rootBundle.loadString('assets/mascotas/catalogo.json'));
      notifyListeners();
    } catch (_) {}
  }

  /// Al entrar a una cuenta: el catálogo y la elección guardada en el teléfono.
  Future<void> iniciar(String cuentaId) async {
    _cuenta = cuentaId;
    await cargarCatalogo();
    try {
      final p = await SharedPreferences.getInstance();
      clave = p.getString(_llave) ?? '';
    } catch (_) {
      clave = '';
    }
    notifyListeners();
  }

  Future<void> elegir(String nueva) async {
    if (nueva.isNotEmpty) {
      final m = catalogo.where((x) => x.clave == nueva).firstOrNull;
      if (m == null || !puedeElegir(m)) return;
    }
    clave = nueva;
    notifyListeners();
    if (_cuenta.isEmpty) return;
    try {
      final p = await SharedPreferences.getInstance();
      if (nueva.isEmpty) {
        await p.remove(_llave);
      } else {
        await p.setString(_llave, nueva);
      }
    } catch (_) {}
  }

  /// Al cerrar sesión: nada de la cuenta anterior se queda a la vista.
  void reiniciar() {
    _cuenta = '';
    clave = '';
    notifyListeners();
  }

  String get _llave => 'mascota_app_$_cuenta';

  /// La hoja de la mascota, decodificada una sola vez.
  Future<ui.Image?> imagen(String clave) => _imagenes.putIfAbsent(clave, () => _decodificar('assets/mascotas/$clave.png'));

  /// Las dos variantes de la estela (11x11 lado a lado), decodificadas una sola vez.
  Future<ui.Image?> imagenEstela(String clave) =>
      _estelas.putIfAbsent(clave, () => _decodificar('assets/mascotas/estela_$clave.png'));

  Future<ui.Image?> _decodificar(String ruta) async {
    try {
      final datos = await rootBundle.load(ruta);
      final codec = await ui.instantiateImageCodec(datos.buffer.asUint8List());
      return (await codec.getNextFrame()).image;
    } catch (_) {
      return null;
    }
  }
}
