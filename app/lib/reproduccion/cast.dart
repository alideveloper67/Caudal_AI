import 'dart:async';

import 'package:flutter/foundation.dart';

import '../nucleo/streams.dart' show Fuente;
import 'cast_plataforma.dart' as plataforma;
import 'cast_tipos.dart';

export 'cast_tipos.dart';

/// Lo que el control de Cast necesita del reproductor de Caudal. Son todo
/// funciones para que el reproductor solo tenga que crearlo (ver el parche en
/// el informe) y para poder probarlo sin motor de sonido.
class AnfitrionCast {
  AnfitrionCast({
    required this.pista,
    required this.fuente,
    required this.posicion,
    required this.duracion,
    required this.sonandoLocal,
    required this.fijarEstado,
    required this.callarLocal,
    required this.volverLocal,
    required this.siguiente,
    required this.aviso,
  });

  /// La canción actual (la del reproductor) y de dónde suena.
  final Map<String, dynamic>? Function() pista;
  final Fuente? Function() fuente;

  /// La barra de progreso del reproductor (el control de Cast la mueve).
  final ValueNotifier<Duration> posicion;
  final ValueNotifier<Duration> duracion;

  /// ¿El teléfono está sonando (o cargando) ahora?
  final bool Function() sonandoLocal;

  /// 'cargando' | 'sonando' | 'pausa' | 'parado' (los nombres de EstadoRepro).
  final void Function(String estado) fijarEstado;

  /// Calla los motores del teléfono (la música pasa a la tele).
  final Future<void> Function() callarLocal;

  /// La música vuelve al teléfono en [desde], sonando o en pausa.
  final Future<void> Function(Duration desde, bool sonar) volverLocal;

  /// La canción terminó en la tele: la siguiente de la cola.
  final Future<void> Function() siguiente;

  final void Function(String texto) aviso;
}

enum ConexionCast { desconectado, conectando, conectado }

/// Enviar la música a un Chromecast, una tele o un altavoz con Google Cast.
///
/// Mientras hay conexión, el reproductor de Caudal sigue mandando (cola,
/// radio, siguiente, me gusta...) pero no suena: cada canción que iba a abrir
/// se la pasa a [enviar] y los botones (play/pausa, barra) llaman a [pausar],
/// [reanudar] e [irA]. La tele avisa cuando acaba y se pide la siguiente. Al
/// desconectar, la música vuelve al teléfono en el mismo punto.
///
/// Lo que se le manda a la tele:
/// * Canciones de YouTube / YouTube Music: el mismo enlace de audio que ya
///   resolvió Caudal (webm/opus o m4a/aac, que Chromecast entiende). Ese
///   enlace va atado a la IP pública de casa y la tele sale por la misma, así
///   que lo abre ella sola sin gastar la wifi del teléfono. Si no puede, se
///   repite a través del servidor del teléfono (ver cast_servidor.dart).
/// * Descargas y música importada: las sirve el propio teléfono por la wifi.
class ControlCast extends ChangeNotifier {
  ControlCast(this.anfitrion, {PuenteCast? puente, ServidorCast? servidor})
      : _puente = puente ?? plataforma.crearPuenteCast(),
        _servidor = servidor ?? plataforma.crearServidorCast() {
    if (_puente.disponible) unawaited(_iniciar());
  }

  final AnfitrionCast anfitrion;
  final PuenteCast _puente;
  final ServidorCast _servidor;
  final List<StreamSubscription<dynamic>> _subs = [];

  bool _listo = false;

  /// ¿Hay Cast en este teléfono? Si no (web, PC, teléfonos sin servicios de
  /// Google), el botón no aparece.
  bool get soportado => _puente.disponible && _listo;

  ConexionCast conexion = ConexionCast.desconectado;
  bool get activo => conexion == ConexionCast.conectado;

  /// Con quién hay conexión (o se está conectando).
  DispositivoCast? dispositivo;
  List<DispositivoCast> dispositivos = const [];
  bool buscando = false;

  /// Volumen de la tele, de 0 a 1.
  double volumen = 0.5;

  /// Lo último que dijo la tele de lo que suena.
  EstadoMedioCast estadoMedio = EstadoMedioCast.nada;

  Map<String, dynamic>? _pista;
  String? _url; // lo que la tele tiene cargado
  String? _urlOriginal; // el enlace de YouTube antes de pasar por el teléfono
  String _tipo = 'audio/mp4';
  bool _porTelefono = false;
  bool _empezo = false;
  int _gen = 0;
  Duration _base = Duration.zero;
  DateTime _baseEn = DateTime.now();
  Timer? _reloj;
  Timer? _esperaConexion;
  bool _saliendo = false;

  Future<void> _iniciar() async {
    try {
      _listo = await _puente.preparar();
    } catch (e) {
      debugPrint('cast: no se pudo preparar ($e)');
      _listo = false;
    }
    if (!_listo) return;
    _subs.add(_puente.dispositivos.listen((l) {
      dispositivos = List.unmodifiable(l);
      notifyListeners();
    }));
    _subs.add(_puente.sesion.listen(_alSesion));
    _subs.add(_puente.medio.listen(_alMedio));
    _subs.add(_puente.posicion.listen(_alPosicion));
    _subs.add(_puente.volumen.listen((v) {
      volumen = v.clamp(0.0, 1.0);
      notifyListeners();
    }));
    notifyListeners();
  }

  // ------------------------------------------------------------ buscar y conectar

  Future<void> buscarDispositivos() async {
    if (!soportado || buscando) return;
    buscando = true;
    notifyListeners();
    try {
      await _puente.buscar();
    } catch (_) {}
  }

  Future<void> dejarDeBuscar() async {
    if (!buscando) return;
    buscando = false;
    notifyListeners();
    try {
      await _puente.dejarDeBuscar();
    } catch (_) {}
  }

  Future<void> conectar(DispositivoCast d) async {
    if (!soportado) return;
    if (activo && dispositivo == d) return;
    if (activo) await desconectar(volver: false);
    conexion = ConexionCast.conectando;
    dispositivo = d;
    notifyListeners();
    var ok = false;
    try {
      ok = await _puente.conectar(d);
    } catch (_) {}
    if (!ok) return _fallaConexion(d);
    _esperaConexion?.cancel();
    _esperaConexion = Timer(const Duration(seconds: 25), () {
      if (conexion == ConexionCast.conectando) _fallaConexion(d);
    });
  }

  void _fallaConexion(DispositivoCast d) {
    if (conexion == ConexionCast.conectado) return;
    conexion = ConexionCast.desconectado;
    dispositivo = null;
    notifyListeners();
    anfitrion.aviso('No pude conectar con «${d.nombre}». Revisa que esté encendido y en la misma wifi.');
    unawaited(_puente.desconectar().catchError((_) {}));
  }

  void _alSesion(DispositivoCast? d) {
    if (d != null) {
      if (conexion == ConexionCast.conectado) return;
      unawaited(_alConectar(d));
    } else {
      unawaited(_alDesconectar());
    }
  }

  /// Hay sesión: lo que suena en el teléfono pasa a la tele en el mismo punto.
  Future<void> _alConectar(DispositivoCast d) async {
    _esperaConexion?.cancel();
    _saliendo = false;
    conexion = ConexionCast.conectado;
    dispositivo = d;
    estadoMedio = EstadoMedioCast.nada;
    _url = null;
    notifyListeners();
    unawaited(dejarDeBuscar());
    final pista = anfitrion.pista();
    final fuente = anfitrion.fuente();
    if (pista == null || fuente == null) return;
    final sonaba = anfitrion.sonandoLocal();
    final desde = anfitrion.posicion.value;
    await anfitrion.callarLocal();
    await enviar(pista, fuente, inicio: desde, pausado: !sonaba);
  }

  /// El usuario corta (o la tele se apagó / se perdió la wifi): la música vuelve
  /// al teléfono. Con [volver] en false solo se corta (para cambiar de tele).
  Future<void> desconectar({bool volver = true}) async {
    if (conexion == ConexionCast.desconectado) return;
    if (conexion == ConexionCast.conectando) {
      _esperaConexion?.cancel();
      conexion = ConexionCast.desconectado;
      dispositivo = null;
      notifyListeners();
      try {
        await _puente.desconectar();
      } catch (_) {}
      return;
    }
    final punto = posicionAhora;
    final sonaba = estadoMedio == EstadoMedioCast.sonando || estadoMedio == EstadoMedioCast.cargando;
    _saliendo = true;
    _soltar();
    try {
      await _puente.desconectar();
    } catch (_) {}
    if (volver) await _devolver(punto, sonaba);
  }

  Future<void> _alDesconectar() async {
    if (conexion == ConexionCast.conectando) {
      // la tele rechazó la sesión
      final d = dispositivo;
      if (d != null) _fallaConexion(d);
      return;
    }
    if (conexion != ConexionCast.conectado) return;
    final punto = posicionAhora;
    final sonaba = estadoMedio == EstadoMedioCast.sonando || estadoMedio == EstadoMedioCast.cargando;
    _soltar();
    anfitrion.aviso('Se cortó la conexión con la tele. Sigue sonando en el teléfono.');
    await _devolver(punto, sonaba);
  }

  void _soltar() {
    conexion = ConexionCast.desconectado;
    dispositivo = null;
    estadoMedio = EstadoMedioCast.nada;
    _url = null;
    _urlOriginal = null;
    _reloj?.cancel();
    _reloj = null;
    _gen++;
    notifyListeners();
    unawaited(_servidor.cerrar().catchError((_) {}));
  }

  Future<void> _devolver(Duration punto, bool sonaba) async {
    final pista = _pista;
    _pista = null;
    if (pista == null || !identical(pista, anfitrion.pista())) return;
    await anfitrion.volverLocal(punto, sonaba);
  }

  // ------------------------------------------------------------ mandar canciones

  /// Manda [pista] a la tele (la llama el reproductor en vez de abrirla él).
  Future<void> enviar(Map<String, dynamic> pista, Fuente fuente,
      {Duration inicio = Duration.zero, bool pausado = false}) async {
    if (!activo) return;
    final gen = ++_gen;
    final directa = _direccionDe(fuente);
    if (directa == null) {
      anfitrion.fijarEstado('parado');
      anfitrion.aviso('Esta canción no se puede enviar a la tele.');
      return;
    }
    // la misma canción que ya está en la tele (cambiar a modo video, reintentos): no se corta
    if (identical(pista, _pista) && directa == _urlOriginal && _url != null &&
        estadoMedio != EstadoMedioCast.terminado && estadoMedio != EstadoMedioCast.error &&
        estadoMedio != EstadoMedioCast.nada) {
      if ((inicio - posicionAhora).abs() > const Duration(seconds: 3)) await irA(inicio);
      return;
    }
    _pista = pista;
    _urlOriginal = directa;
    _porTelefono = false;
    _empezo = false;
    final tipo = tipoDeFuente(fuente);
    _tipo = tipo;
    String? url = directa;
    if (fuente.local) {
      url = await _servidor.publicarArchivo(fuente.archivo, tipo: tipo);
      if (gen != _gen) return;
      if (url == null) {
        anfitrion.fijarEstado('parado');
        anfitrion.aviso('Para enviar tus descargas, el teléfono tiene que estar conectado a la wifi.');
        return;
      }
      _porTelefono = true;
    }
    await _cargar(gen, pista, url, tipo, inicio, pausado);
  }

  Future<void> _cargar(int gen, Map<String, dynamic> pista, String url, String tipo,
      Duration inicio, bool pausado) async {
    _url = url;
    estadoMedio = EstadoMedioCast.cargando;
    anfitrion.fijarEstado('cargando');
    _fijarBase(inicio);
    anfitrion.posicion.value = inicio;
    final medio = MedioCast(
      url: url,
      tipo: tipo,
      titulo: '${pista['titulo'] ?? ''}',
      artista: '${pista['artista'] ?? ''}',
      album: '${(pista['album'] as Map?)?['nombre'] ?? ''}',
      caratula: await _caratula(pista),
      duracion: anfitrion.duracion.value == Duration.zero ? null : anfitrion.duracion.value,
    );
    if (gen != _gen) return;
    try {
      await _puente.cargar(medio, desde: inicio, sonar: !pausado);
    } catch (e) {
      if (gen != _gen) return;
      debugPrint('cast: no se pudo cargar ($e)');
      await _fallo(gen);
    }
  }

  /// La carátula como dirección que la tele pueda abrir (más grande que la miniatura).
  Future<String?> _caratula(Map<String, dynamic> pista) async {
    final m = '${pista['miniatura'] ?? ''}';
    if (m.isEmpty) return null;
    if (m.startsWith('http')) return caratulaGrande(m);
    try {
      return await _servidor.publicarArchivo(m);
    } catch (_) {
      return null;
    }
  }

  /// La tele no pudo abrir la canción: primero se prueba a través del teléfono;
  /// si tampoco, se avisa y se pasa a la siguiente (como hace el teléfono).
  Future<void> _fallo(int gen) async {
    final pista = _pista;
    final original = _urlOriginal;
    if (pista == null || original == null) return;
    if (!_porTelefono && original.startsWith('http')) {
      _porTelefono = true;
      final tipo = _tipo;
      final otra = await _servidor.publicarRemoto(original, tipo: tipo);
      if (gen != _gen) return;
      if (otra != null) {
        return _cargar(gen, pista, otra, tipo, posicionAhora, false);
      }
    }
    estadoMedio = EstadoMedioCast.error;
    anfitrion.fijarEstado('parado');
    anfitrion.aviso('La tele no pudo reproducir esta canción. Pasamos a la siguiente.');
    Timer(const Duration(milliseconds: 1200), () {
      if (gen == _gen && activo) anfitrion.siguiente();
    });
  }


  // ------------------------------------------------------------ botones

  Future<void> pausar() async {
    if (!activo) return;
    _fijarBase(posicionAhora);
    estadoMedio = EstadoMedioCast.pausa;
    anfitrion.fijarEstado('pausa');
    _reloj?.cancel();
    try {
      await _puente.pausar();
    } catch (_) {}
  }

  Future<void> reanudar() async {
    if (!activo) return;
    final pista = _pista ?? anfitrion.pista();
    // la tele no tiene nada (se acabó o se paró desde otro sitio): se vuelve a mandar
    if (_url == null || estadoMedio == EstadoMedioCast.terminado || estadoMedio == EstadoMedioCast.nada ||
        estadoMedio == EstadoMedioCast.cortado || estadoMedio == EstadoMedioCast.error) {
      final f = anfitrion.fuente();
      if (pista != null && f != null) {
        _url = null;
        await enviar(pista, f, inicio: anfitrion.posicion.value);
      }
      return;
    }
    _fijarBase(posicionAhora);
    estadoMedio = EstadoMedioCast.sonando;
    anfitrion.fijarEstado('sonando');
    _relojar();
    try {
      await _puente.sonar();
    } catch (_) {}
  }

  Future<void> irA(Duration p) async {
    if (!activo) return;
    _fijarBase(p);
    anfitrion.posicion.value = p;
    try {
      await _puente.irA(p);
    } catch (_) {}
  }

  /// La cola se acabó o el temporizador para dormir: se para la tele.
  Future<void> parar() async {
    if (!activo) return;
    _gen++;
    _fijarBase(posicionAhora);
    _url = null;
    estadoMedio = EstadoMedioCast.nada;
    _reloj?.cancel();
    try {
      await _puente.parar();
    } catch (_) {}
  }

  Future<void> fijarVolumen(double v) async {
    volumen = v.clamp(0.0, 1.0);
    notifyListeners();
    if (!activo) return;
    try {
      await _puente.fijarVolumen(volumen);
    } catch (_) {}
  }

  // ------------------------------------------------------------ lo que dice la tele

  void _alMedio(EventoCast e) {
    if (!activo || _saliendo) return;
    // avisos de algo que ya no es lo nuestro (lo anterior al cargar otra)
    if (e.url != null && _url != null && e.url != _url) return;
    switch (e.estado) {
      case EstadoMedioCast.sonando:
        _empezo = true;
        if (estadoMedio != EstadoMedioCast.sonando) _fijarBase(posicionAhora);
        estadoMedio = EstadoMedioCast.sonando;
        anfitrion.fijarEstado('sonando');
        _relojar();
      case EstadoMedioCast.pausa:
        _empezo = true;
        if (estadoMedio == EstadoMedioCast.sonando) _fijarBase(posicionAhora);
        estadoMedio = EstadoMedioCast.pausa;
        anfitrion.fijarEstado('pausa');
        _reloj?.cancel();
      case EstadoMedioCast.cargando:
        if (estadoMedio == EstadoMedioCast.pausa && _empezo) return;
        estadoMedio = EstadoMedioCast.cargando;
        anfitrion.fijarEstado('cargando');
      case EstadoMedioCast.terminado:
        if (!_empezo || _url == null) return;
        estadoMedio = EstadoMedioCast.terminado;
        _reloj?.cancel();
        _url = null;
        unawaited(anfitrion.siguiente());
      case EstadoMedioCast.error:
        if (_url == null) return;
        unawaited(_fallo(_gen));
      case EstadoMedioCast.cortado:
        // se cargó otra canción encima o alguien la paró desde el mando de la tele
        if (estadoMedio == EstadoMedioCast.cargando) return;
        estadoMedio = EstadoMedioCast.cortado;
        _reloj?.cancel();
        anfitrion.fijarEstado('pausa');
      case EstadoMedioCast.nada:
        break;
    }
    final d = e.duracion;
    if (d != null && d > Duration.zero && anfitrion.duracion.value == Duration.zero) {
      anfitrion.duracion.value = d;
    }
    notifyListeners();
  }

  void _alPosicion(Duration p) {
    if (!activo || _saliendo || _url == null) return;
    if (estadoMedio == EstadoMedioCast.cargando && p == Duration.zero) return;
    _fijarBase(p);
    anfitrion.posicion.value = p;
  }

  // ------------------------------------------------------------ posición

  /// Dónde va la tele ahora (lo último que dijo más lo que pasó desde entonces).
  Duration get posicionAhora {
    if (estadoMedio != EstadoMedioCast.sonando) return _base;
    final p = _base + DateTime.now().difference(_baseEn);
    final d = anfitrion.duracion.value;
    return d > Duration.zero && p > d ? d : p;
  }

  void _fijarBase(Duration p) {
    _base = p;
    _baseEn = DateTime.now();
  }

  /// La barra avanza sola entre los avisos de la tele (que llegan cada pocos segundos).
  void _relojar() {
    _reloj?.cancel();
    _reloj = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (!activo || estadoMedio != EstadoMedioCast.sonando) return;
      anfitrion.posicion.value = posicionAhora;
    });
  }

  @override
  void dispose() {
    _reloj?.cancel();
    _esperaConexion?.cancel();
    for (final s in _subs) {
      s.cancel();
    }
    unawaited(_servidor.cerrar().catchError((_) {}));
    super.dispose();
  }

  // ------------------------------------------------------------ direcciones

  /// La dirección que se manda a la tele. En modo video el reproductor tiene
  /// imagen y sonido por separado: a la tele va solo el sonido.
  static String? _direccionDe(Fuente f) {
    if (f.local) return f.archivo;
    final u = f.audioUrl ?? f.url;
    if (u.startsWith('http')) return u;
    return null; // 'yt:...' (la web) no se puede mandar
  }
}

/// El tipo de lo que va a la tele: por el `mime=` de los enlaces de YouTube,
/// por la extensión del archivo o por el códec.
String tipoDeFuente(Fuente f) {
  if (f.local) return plataforma.tipoPorExtension(f.archivo);
  final u = f.audioUrl ?? f.url;
  final mime = Uri.tryParse(u)?.queryParameters['mime'];
  if (mime != null && mime.contains('/')) return mime;
  final c = f.audioCodec.toLowerCase();
  if (f.audioUrl == null && f.alto > 0) return 'video/mp4';
  if (c.startsWith('opus') || c.startsWith('vorbis')) return 'audio/webm';
  if (c.startsWith('mp3')) return 'audio/mpeg';
  return 'audio/mp4';
}

/// Las miniaturas de YouTube Music vienen pequeñas: para la tele, grandes.
String caratulaGrande(String url) {
  final g = RegExp(r'=w\d+-h\d+').firstMatch(url);
  if (g != null && url.contains('googleusercontent')) return url.replaceFirst(g.group(0)!, '=w720-h720');
  return url.replaceFirstMapped(RegExp(r'/(default|mqdefault|sddefault)\.jpg'), (_) => '/hqdefault.jpg');
}
