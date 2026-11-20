// El vigía de los logros: cuenta lo que pasa en la app sin tocar el reproductor (solo lo escucha,
// como el «Modo gamer») y avisa al conseguir un logro. Uno por cuenta abierta.
//
//   final vigia = VigiaLogros(
//     logros: await Logros.abrir(c.id),
//     reproductor: reproductor,
//     suena: () => reproductor.estado == EstadoRepro.sonando,
//     actual: () => reproductor.actual,
//     coleccion: coleccion,
//     sesion: c.sesion,
//     alConseguir: (nuevos) => AvisosLogros.mostrar(_navegador.currentState?.overlay, nuevos),
//   )..iniciar();

import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';

import 'coleccion.dart';
import 'juntos.dart';
import 'logros.dart';
import 'nube.dart';

class VigiaLogros {
  VigiaLogros({
    required this.logros,
    required this.reproductor,
    required this.suena,
    required this.actual,
    this.coleccion,
    this.sesion,
    this.alConseguir,
    this.tic = const Duration(seconds: 5),
    this.cadaNube = const Duration(minutes: 2),
    DateTime Function()? reloj,
  }) : _reloj = reloj ?? DateTime.now;

  final Logros logros;
  final Listenable reproductor;
  final bool Function() suena;
  final Map<String, dynamic>? Function() actual;
  final Coleccion? coleccion;
  final Sesion? sesion;
  final void Function(List<Logro> nuevos)? alConseguir;
  final Duration tic;
  final Duration cadaNube;
  final DateTime Function() _reloj;

  /// Una canción cuenta si sonó al menos esto.
  static const segundosParaContar = 20;

  Timer? _tic;
  Timer? _nube;
  Timer? _pronto;
  DateTime? _marca;
  String? _claveActual;
  Map<String, dynamic>? _pendiente;
  double _sonada = 0;
  bool _sincronizando = false;
  SalaJuntos? _sala;
  bool _detenido = false;

  /// El de la cuenta abierta (Ajustes y el perfil lo leen de aquí).
  static VigiaLogros? vigente;

  void iniciar({bool importar = true}) {
    vigente = this;
    _marca = _reloj();
    reproductor.addListener(_alReproductor);
    coleccion?.addListener(_totales);
    SalaJuntos.activa.addListener(_alCambiarSala);
    _alCambiarSala();
    _tic = Timer.periodic(tic, (_) => contar());
    _nube = Timer.periodic(cadaNube, (_) => unawaited(sincronizar()));
    if (importar) {
      Future.delayed(const Duration(seconds: 3), () => unawaited(importarLoDeAntes()));
    }
  }

  void detener() {
    if (identical(vigente, this)) vigente = null;
    _detenido = true;
    _tic?.cancel();
    _nube?.cancel();
    _pronto?.cancel();
    reproductor.removeListener(_alReproductor);
    coleccion?.removeListener(_totales);
    SalaJuntos.activa.removeListener(_alCambiarSala);
    _sala?.removeListener(_alSala);
    logros.guardar(ya: true);
  }

  // ------------------------------------------------------------ lo que suena

  void _alReproductor() {
    final p = actual();
    final clave = p?['clave'] as String?;
    if (clave != _claveActual) {
      contar(); // lo que sonó hasta ahora cuenta para la canción anterior
      _claveActual = clave;
      _pendiente = p;
      _sonada = 0;
    }
  }

  /// Suma el tiempo con música desde la última vez (lo llama el temporizador).
  @visibleForTesting
  void contar() {
    final ahora = _reloj();
    final antes = _marca ?? ahora;
    _marca = ahora;
    // un salto largo (teléfono dormido, app en pausa) no suma de más
    final tope = tic.inMilliseconds * 3 / 1000;
    var paso = ahora.difference(antes).inMilliseconds / 1000;
    if (paso > tope) paso = tope;
    if (paso <= 0 || !suena()) return;
    logros.anotarSegundos(paso, cuando: ahora);
    if (_pendiente != null) {
      _sonada += paso;
      if (_sonada >= segundosParaContar) {
        logros.anotarPista(_pendiente, cuando: ahora);
        _pendiente = null;
      }
    }
    revisar();
  }

  // ------------------------------------------------------------ la colección

  Future<void> _totales() async {
    final c = coleccion;
    if (c == null || _detenido) return;
    try {
      logros.anotarMeGusta(c.totalMeGusta);
      final l = await c.db.rawQuery('SELECT COUNT(*) AS n FROM listas');
      logros.anotarListas((l.first['n'] as num?)?.toInt() ?? 0);
      final d = await c.db.rawQuery("SELECT COUNT(*) AS n FROM descargas WHERE archivo IS NOT NULL AND archivo != ''");
      logros.anotarDescargas((d.first['n'] as num?)?.toInt() ?? 0);
    } catch (_) {}
    revisar();
  }

  // ------------------------------------------------------------ escuchar juntos

  void _alCambiarSala() {
    final s = SalaJuntos.activa.value;
    if (identical(s, _sala)) return;
    _sala?.removeListener(_alSala);
    _sala = s;
    s?.addListener(_alSala);
    _alSala();
  }

  void _alSala() {
    final s = _sala;
    if (s == null) return;
    anotarSala(s.codigo, s.miId, s.miembros.length, s.soyAnfitrion);
  }

  @visibleForTesting
  void anotarSala(String codigo, String miId, int miembros, bool soyAnfitrion) {
    logros.anotarSala('$codigo|$miId', conAmigos: miembros >= 2, soyAnfitrion: soyAnfitrion);
    revisar();
  }

  // ------------------------------------------------------------ lo de antes

  /// Lo escuchado antes de existir los logros (una sola vez) y los totales de la colección.
  Future<void> importarLoDeAntes() async {
    await _totales();
    final c = coleccion;
    if (!logros.importado && c != null) {
      try {
        final filas = await c.db.rawQuery(
            'SELECT r.clave AS clave, r.fecha AS fecha, p.datos AS datos FROM reproducciones r '
            'LEFT JOIN pistas p ON p.clave = r.clave ORDER BY r.fecha LIMIT 50000');
        final lista = <(String, num, Map?)>[];
        for (final f in filas) {
          final clave = f['clave'] as String?;
          final fecha = f['fecha'] as num?;
          if (clave == null || fecha == null) continue;
          Map? pista;
          try {
            final d = f['datos'];
            if (d is String && d.isNotEmpty) pista = jsonDecode(d) as Map?;
          } catch (_) {}
          lista.add((clave, fecha, pista));
        }
        logros.importar(lista);
      } catch (_) {
        logros.importar(const []);
      }
      revisar();
    }
    await sincronizar();
  }

  // ------------------------------------------------------------ avisos y nube

  List<Logro> revisar() {
    final nuevos = logros.revisar();
    if (nuevos.isNotEmpty) {
      alConseguir?.call(nuevos);
      pronto();
    }
    return nuevos;
  }

  /// Sube a la nube en un momento (la vitrina cambió o hay un logro nuevo).
  void pronto() {
    _pronto?.cancel();
    _pronto = Timer(const Duration(seconds: 4), () => unawaited(sincronizar()));
  }

  Future<void> sincronizar() async {
    if (_sincronizando || _detenido || sesion == null || !logros.pendienteNube) return;
    _sincronizando = true;
    try {
      if (await logros.sincronizar(sesion)) revisar();
    } finally {
      _sincronizando = false;
    }
  }
}
