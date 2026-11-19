// El cerebro del «Modo gamer»: interruptor, ahorro al jugar, perfiles de
// sonido, listas por situación y XP por escuchar. No conoce al reproductor:
// quien lo crea le pasa lo que necesita (ver main.dart), y así se prueba solo.

import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';

import 'ajustes.dart';
import 'gamer.dart';
import 'gamer_xp.dart';

class ModoGamerControl extends ChangeNotifier {
  ModoGamerControl({
    required this.ajustes,
    required this.aplicarSonido,
    required this.lanzar,
    this.alSubirNivel,
    DateTime Function()? reloj,
    Future<List<Map<String, dynamic>>> Function(Situacion)? buscarPistas,
  })  : _reloj = reloj ?? DateTime.now,
        _buscarPistas = buscarPistas ?? pistasParaSituacion {
    _activo = ajustes.sino('gamer_activo');
    _progreso = ProgresoGamer.deTexto(ajustes.texto('gamer_progreso')).alDia(_reloj());
    _publicarMascotas();
  }

  final Ajustes ajustes;

  /// Vuelve a montar el sonido con los ajustes actuales (reproductor.aplicarSonido).
  final Future<void> Function() aplicarSonido;

  /// Pone a sonar una lista (reproductor.reproducirLista).
  final Future<void> Function(List<Map<String, dynamic>> pistas, Map<String, dynamic> contexto) lanzar;

  /// Aviso discreto al subir de nivel.
  final void Function(int nivel)? alSubirNivel;
  final DateTime Function() _reloj;
  final Future<List<Map<String, dynamic>>> Function(Situacion) _buscarPistas;

  /// ¿Hay que esconder la mascota y el personaje del fondo? (los lee main.dart y la barra)
  static final ValueNotifier<bool> mascotasOcultas = ValueNotifier(false);

  late bool _activo;
  late ProgresoGamer _progreso;
  bool _cerrado = false;

  bool get activo => _activo;
  bool get ahorro => ajustes.sino('gamer_ahorro');
  PerfilSonido? get perfil => perfilSonidoPorId(ajustes.texto('gamer_sonido'));
  ProgresoGamer get progreso => _progreso;
  DateTime get ahora => _reloj();

  /// Mientras se arma una lista (para que el botón no se pulse dos veces).
  final ValueNotifier<Situacion?> cargando = ValueNotifier(null);

  /// Para quien solo tiene los ajustes (la barra, el fondo).
  static bool ocultaMascota(Ajustes a) => a.sino('gamer_activo') && a.sino('gamer_ahorro');

  void _publicarMascotas() => mascotasOcultas.value = _activo && ahorro;

  // ------------------------------------------------------------ interruptor y ahorro

  Future<void> activar(bool v) async {
    if (v == _activo) return;
    _activo = v;
    await ajustes.poner('gamer_activo', v, avisar: false);
    if (v) {
      if (ahorro) await _aplicarAhorro();
      final p = perfil;
      if (p != null) await _aplicarPerfil(p);
    } else {
      _pararEscucha();
      await _devolverAhorro();
      await _devolverSonido();
    }
    _publicarMascotas();
    notifyListeners();
  }

  Future<void> ponerAhorro(bool v) async {
    await ajustes.poner('gamer_ahorro', v, avisar: false);
    if (_activo) {
      if (v) {
        await _aplicarAhorro();
      } else {
        await _devolverAhorro();
      }
    }
    _publicarMascotas();
    notifyListeners();
  }

  /// Guarda cómo estaba el modo ligero y lo enciende (esto sí avisa: la app lo reaplica).
  Future<void> _aplicarAhorro() async {
    if (ajustes.texto('gamer_ligero_previo').isEmpty) {
      await ajustes.poner('gamer_ligero_previo', ajustes.sino('modo_ligero') ? '1' : '0', avisar: false);
    }
    if (!ajustes.sino('modo_ligero')) await ajustes.poner('modo_ligero', true);
  }

  Future<void> _devolverAhorro() async {
    final previo = ajustes.texto('gamer_ligero_previo');
    if (previo.isEmpty) return;
    await ajustes.poner('gamer_ligero_previo', '', avisar: false);
    final antes = previo == '1';
    if (ajustes.sino('modo_ligero') != antes) await ajustes.poner('modo_ligero', antes);
  }

  // ------------------------------------------------------------ sonido

  /// Elige el perfil de sonido de un tipo de juego; `null` lo quita y devuelve el ecualizador de antes.
  Future<void> elegirPerfil(PerfilSonido? p) async {
    if (!_activo) return;
    await ajustes.poner('gamer_sonido', p?.id ?? '', avisar: false);
    if (p == null) {
      await _devolverSonido();
    } else {
      await _aplicarPerfil(p);
    }
    notifyListeners();
  }

  Future<void> _aplicarPerfil(PerfilSonido p) async {
    // se recuerda cómo estaba el ecualizador solo la primera vez (cambiar de perfil no lo pisa)
    if (ajustes.texto('gamer_eq_previo').isEmpty) {
      await ajustes.poner(
          'gamer_eq_previo',
          jsonEncode({
            'e': ajustes.sino('ecualizador'),
            'b': ajustes.bandasEq,
            'p': ajustes.texto('eq_preset'),
          }),
          avisar: false);
    }
    await ajustes.poner('ecualizador', true, avisar: false);
    await ajustes.poner('eq_bandas', p.bandas, avisar: false);
    await ajustes.poner('eq_preset', p.nombre, avisar: false);
    await _reaplicar();
  }

  Future<void> _devolverSonido() async {
    final t = ajustes.texto('gamer_eq_previo');
    if (t.isEmpty) return;
    await ajustes.poner('gamer_eq_previo', '', avisar: false);
    try {
      final j = jsonDecode(t) as Map;
      await ajustes.poner('ecualizador', j['e'] == true, avisar: false);
      await ajustes.poner('eq_bandas', [for (final b in (j['b'] as List)) (b as num).toInt()], avisar: false);
      await ajustes.poner('eq_preset', '${j['p'] ?? 'Plano'}', avisar: false);
    } catch (_) {
      await ajustes.poner('ecualizador', false, avisar: false);
      await ajustes.poner('eq_bandas', List.filled(10, 0), avisar: false);
      await ajustes.poner('eq_preset', 'Plano', avisar: false);
    }
    await _reaplicar();
  }

  Future<void> _reaplicar() async {
    try {
      await aplicarSonido();
    } catch (_) {/* sin el filtro en este teléfono, suena igual */}
  }

  // ------------------------------------------------------------ listas por situación

  /// Arranca la radio de una situación. Devuelve un texto de error, o `null` si salió bien.
  Future<String?> ponerSituacion(Situacion s) async {
    if (!_activo || cargando.value != null) return null;
    cargando.value = s;
    try {
      final pistas = await _buscarPistas(s);
      if (pistas.isEmpty) return 'No encontré canciones para «${s.nombre}». Prueba otra vez.';
      await lanzar(pistas, {'tipo': 'radio', 'id': '${pistas.first['video_id'] ?? ''}', 'titulo': 'Modo gamer · ${s.nombre}'});
      return null;
    } catch (e) {
      return 'No se pudo armar «${s.nombre}»: $e';
    } finally {
      cargando.value = null;
    }
  }

  // ------------------------------------------------------------ XP por escuchar

  Timer? _reloj30;
  DateTime? _desde;
  String? _cancionId;
  List<String> _artistas = const [];
  int _segCancion = 0;
  bool _cancionContada = false;

  /// Segundos que se acepta de golpe (si el teléfono durmió, no se regala XP).
  static const _topeVuelco = 120;
  static const _segParaContarCancion = 20;

  /// Lo llama la app cada vez que el reproductor cambia. Con el modo apagado no hace nada;
  /// con él encendido solo mira dos cosas (suena / qué canción) y un reloj de 30 s mientras suena.
  void alReproductor(bool suena, Map<String, dynamic>? pista) {
    if (_cerrado || !_activo) return;
    if (!suena || pista == null) {
      if (_desde != null) {
        _volcar();
        _pararEscucha();
      }
      return;
    }
    final id = _idDe(pista);
    if (_desde != null && id != _cancionId) _volcar();
    if (id != _cancionId) {
      _cancionId = id;
      _artistas = _artistasDe(pista);
      _segCancion = 0;
      _cancionContada = false;
    }
    if (_desde == null) {
      _desde = _reloj();
      _reloj30 ??= Timer.periodic(const Duration(seconds: 30), (_) => _volcar());
    }
  }

  static String _idDe(Map<String, dynamic> p) {
    for (final k in ['clave', 'video_id', 'id']) {
      final v = p[k];
      if (v != null && '$v'.isNotEmpty) return '$v';
    }
    return '${p['titulo'] ?? ''}|${p['artista'] ?? p['autor'] ?? ''}';
  }

  static List<String> _artistasDe(Map<String, dynamic> p) {
    final a = p['artistas'];
    if (a is List && a.isNotEmpty) {
      return [for (final x in a) if (x is Map && '${x['nombre'] ?? ''}'.isNotEmpty) '${x['nombre']}'];
    }
    final t = '${p['artista'] ?? p['autor'] ?? ''}';
    return t.isEmpty ? const [] : [for (final x in t.split(RegExp(r',|&'))) x.trim()];
  }

  void _pararEscucha() {
    _desde = null;
    _reloj30?.cancel();
    _reloj30 = null;
  }

  /// Pasa a XP lo escuchado desde la última marca.
  void _volcar() {
    final desde = _desde;
    if (desde == null || _cerrado) return;
    final t = _reloj();
    var seg = t.difference(desde).inSeconds;
    if (seg <= 0) return;
    _desde = t;
    if (seg > _topeVuelco) seg = _topeVuelco;
    _segCancion += seg;
    final cuenta = !_cancionContada && _segCancion >= _segParaContarCancion;
    if (cuenta) _cancionContada = true;
    final r = _progreso.registrar(t,
        segundos: seg, cancion: cuenta ? _cancionId : null, artistas: cuenta ? _artistas : const []);
    _progreso = r.progreso;
    // aviso de nivel: solo cuando sube; nunca rompe la escucha
    if (r.subioNivel) {
      try {
        alSubirNivel?.call(r.nivelAhora);
      } catch (_) {}
    }
    unawaited(ajustes.poner('gamer_progreso', _progreso.aTexto(), avisar: false));
    notifyListeners();
  }

  /// Fuerza el guardado de lo pendiente (al cerrar la sesión o la app).
  void guardarYa() => _volcar();

  /// Pruebas: los ajustes del progreso, sin pasar por el reproductor.
  @visibleForTesting
  void volcarAhora() => _volcar();

  @override
  void dispose() {
    _volcar();
    _cerrado = true;
    _pararEscucha();
    mascotasOcultas.value = false;
    cargando.dispose();
    super.dispose();
  }
}
