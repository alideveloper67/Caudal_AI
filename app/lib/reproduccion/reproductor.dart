import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:media_kit/media_kit.dart';
import 'package:media_kit_video/media_kit_video.dart';

import '../nucleo/ajustes.dart';
import '../nucleo/catalogo.dart';
import '../nucleo/coleccion.dart';
import '../nucleo/red.dart';
import '../nucleo/streams.dart';
import '../nucleo/transiciones.dart';

const frecuenciasEq = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];
const presetsEq = <String, List<int>>{
  'Plano': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  'Graves potentes': [6, 5, 4, 2, 0, 0, 0, 0, 0, 0],
  'Agudos claros': [0, 0, 0, 0, 0, 1, 2, 4, 5, 6],
  'Voces': [-2, -1, 0, 2, 4, 4, 3, 1, 0, -1],
  'Pop': [-1, 1, 3, 4, 2, 0, -1, -1, 1, 2],
  'Rock': [4, 3, 2, 0, -1, -1, 1, 3, 4, 4],
  'Electrónica': [5, 4, 1, 0, -2, 1, 0, 2, 4, 5],
  'Reguetón': [6, 5, 3, 1, 0, -1, 0, 2, 3, 3],
  'Hip hop': [5, 4, 2, 3, -1, -1, 1, 0, 2, 3],
  'Clásica': [3, 2, 1, 0, 0, 0, -1, -1, 1, 2],
  'Jazz': [3, 2, 1, 2, -1, -1, 0, 1, 2, 3],
  'Acústica': [3, 2, 1, 1, 2, 2, 3, 3, 2, 1],
  'Noche (suave)': [-3, -2, -1, 0, 1, 1, 0, -1, -2, -3],
  'Altavoz pequeño': [-6, -4, 0, 3, 4, 3, 2, 1, 0, -2],
};
const nivelesSuperVolumen = {1: -11, 2: -9, 3: -7, 4: -5};
const nombresSuperVolumen = {0: 'Apagado', 1: 'Fuerte', 2: 'Muy fuerte', 3: 'Fiesta', 4: 'Máximo'};
const _nombresSalto = {
  'music_offtopic': 'parte sin música', 'sponsor': 'patrocinio', 'selfpromo': 'autopromoción',
  'interaction': 'recordatorio de suscripción',
};

/// Subidas en dB del super volumen en iPhone, donde no hay limitador (ver [Reproductor.sonidoLimitado]).
const _superVolumenIos = {1: 2.0, 2: 4.0, 3: 6.0, 4: 8.0};

/// El libmpv de iPhone (media_kit_libs_ios_video 1.1.4 = libmpv-darwin-build
/// v0.6.0, mpv 0.36) trae un ffmpeg minimo: de los filtros de sonido solo
/// `equalizer` y `aresample` (ni `volume`, ni `loudnorm`, ni `alimiter`), y su
/// salida `audiounit` desactiva la AVAudioSession al cerrarse.
bool get _ios => defaultTargetPlatform == TargetPlatform.iOS;

enum EstadoRepro { parado, cargando, sonando, pausa }

/// Uno de los dos motores (libmpv via media_kit) con su pantalla de video.
class _Motor {
  _Motor() {
    player = Player(configuration: const PlayerConfiguration(
      title: 'Caudal',
      bufferSize: 48 * 1024 * 1024,
      logLevel: MPVLogLevel.warn,
    ));
    // lo que dice el motor por dentro (403, certificados, red...) al registro del sistema
    player.stream.log.listen((l) {
      if (l.level == 'error' || l.level == 'fatal' || l.level == 'warn') {
        debugPrint('mpvlog ${l.prefix}: ${l.text.trim()}');
      }
    });
    _afinar();
  }

  /// La pantalla del video se crea la primera vez que hace falta (no al abrir
  /// la app): crearla pide una superficie grafica al sistema y, en algunos
  /// telefonos, eso trababa el arranque aunque solo se fuera a oir musica.
  late final VideoController video = VideoController(player,
      configuration: const VideoControllerConfiguration(enableHardwareAcceleration: true));

  /// Lectura anticipada generosa: que un bajon de red no corte nada.
  Future<void> _afinar() async {
    final n = nativo;
    if (n == null) return;
    final opciones = {
      'cache': 'yes',
      'cache-secs': '60',
      'demuxer-readahead-secs': '30',
      'demuxer-max-bytes': '64MiB',
      'demuxer-max-back-bytes': '16MiB',
      'cache-pause-initial': 'no',
      'cache-pause-wait': '1',
      'ytdl': 'no',
      'audio-buffer': '0.3',
      // en iPhone el ecualizador y el super volumen van por el volumen de mpv
      if (_ios) 'volume-max': '200',
    };
    for (final e in opciones.entries) {
      try {
        await n.setProperty(e.key, e.value);
      } catch (_) {}
    }
  }

  late final Player player;
  Fuente? fuente;

  NativePlayer? get nativo => player.platform is NativePlayer ? player.platform as NativePlayer : null;

  Future<void> abrir(Fuente f, {Duration inicio = Duration.zero, bool pausado = false,
      double volumen = 100, double velocidad = 1}) async {
    fuente = f;
    await player.setVolume(volumen);
    await player.setRate(velocidad);
    final aparte = f.audioUrl != null;
    // con el sonido aparte se abre en pausa y se arranca cuando ya estan las
    // dos pistas: si no, el video corre un instante mudo y luego da un salto
    await player.open(Media(f.url, start: inicio > const Duration(seconds: 1) ? inicio : null),
        play: !pausado && !aparte);
    if (aparte) {
      await player.setAudioTrack(AudioTrack.uri(f.audioUrl!));
      if (!pausado) await player.play();
    }
  }

  /// Devuelve si tenia algo cargado (en iPhone, cerrar su salida de sonido
  /// apaga la sesion de audio de toda la app).
  Future<bool> detener() async {
    final tenia = fuente != null;
    fuente = null;
    try {
      await player.stop();
    } catch (_) {}
    return tenia;
  }
}

/// El reproductor de Caudal: la cola como Spotify y el motor como el escritorio.
class Reproductor extends ChangeNotifier {
  Reproductor(this.ajustes, this.coleccion, this.streams) {
    _a = _Motor();
    _b = _Motor();
    for (final m in [_a, _b]) {
      m.player.stream.position.listen((p) => _alPosicion(m, p));
      m.player.stream.duration.listen((d) => _alDuracion(m, d));
      m.player.stream.playing.listen((s) => _alSonar(m, s));
      m.player.stream.buffering.listen((b) => _alEsperar(m, b));
      m.player.stream.completed.listen((c) {
        if (c) _alTerminar(m);
      });
      m.player.stream.error.listen((e) => _alError(m, e));
    }
    volumen = ajustes.entero('volumen').toDouble();
    velocidad = ajustes.decimal('velocidad');
    aleatorio = ajustes.sino('aleatorio');
    repetir = ajustes.texto('repetir');
    _relojApagado = Timer.periodic(const Duration(milliseconds: 500), (_) => _ticApagado());
    aplicarSonido();
  }

  final Ajustes ajustes;
  final Coleccion coleccion;
  final Streams streams;
  late final _Motor _a;
  late final _Motor _b;
  _Motor get _activo => _usaA ? _a : _b;
  _Motor get _otro => _usaA ? _b : _a;
  bool _usaA = true;

  /// La pantalla del video que suena (la que pinta la vista de video).
  VideoController get pantalla => _activo.video;

  // estado publico
  Json? actual;
  List<Json> secuencia = [];
  List<Json> original = [];
  int pos = -1;
  List<Json> proximas = [];
  Json? contexto;
  bool aleatorio = false;
  String repetir = 'no';
  String modo = 'audio'; // audio | video
  EstadoRepro estado = EstadoRepro.parado;
  double volumen = 100;
  double velocidad = 1;
  Fuente? fuente;

  /// Posicion y duracion van aparte para no repintar toda la app cada segundo.
  final ValueNotifier<Duration> posicion = ValueNotifier(Duration.zero);
  final ValueNotifier<Duration> duracion = ValueNotifier(Duration.zero);
  final _avisos = StreamController<String>.broadcast();
  Stream<String> get avisos => _avisos.stream;

  int _gen = 0;
  List<(double, double, String)> _segmentos = [];
  bool _escuchaContada = false;
  bool _buscandoRadio = false;
  Map<String, dynamic>? _fundido;
  Map<String, dynamic>? _traspaso;
  Timer? _pasosFundido;
  double _estCarga = 1.5;
  String? _calidadForzada;
  DateTime? _apagarEn;
  bool _apagarAlFinal = false;
  Timer? _relojApagado;
  DateTime _ultimoGuardado = DateTime(2000);

  /// Lo que queda del volumen mientras el temporizador para dormir lo baja.
  double _factorDormir = 1;

  // transiciones DJ
  /// Tramos "sin musica" de lo que suena (para saber donde acaba de verdad).
  List<Tramo> _tramosDj = [];
  /// Los de la siguiente, pedidos por adelantado: (video_id, tramos).
  (String, List<Tramo>)? _tramosSiguiente;
  /// Si este telefono acepto el filtro que mide el nivel (`astats`).
  bool _filtroNivel = true;
  final _silencioFinal = DetectorSilencio();
  final _silencioEntrada = DetectorSilencio(umbralDb: -50, minimo: const Duration(milliseconds: 300));
  final Set<_Motor> _midiendo = {};

  bool get _dj => ajustes.sino('transicion_dj');

  // ------------------------------------------------------------ sonido

  /// En iPhone no hay limitador ni normalizador: el super volumen sube sin
  /// limitar y "normalizar" no hace nada.
  bool get sonidoLimitado => _ios;

  /// Multiplicador del volumen que piden el ecualizador (margen) y el super
  /// volumen en iPhone. En Android eso lo hacen los filtros y vale 1.
  double get _factorSalida {
    if (!_ios) return 1;
    var db = 0.0;
    if (ajustes.sino('ecualizador')) {
      final maximo = ajustes.bandasEq.take(10).fold<int>(0, max);
      if (maximo > 0) db -= maximo * 0.6;
    }
    db += _superVolumenIos[ajustes.entero('super_volumen')] ?? 0;
    // el volumen de mpv es cubico: (v/100)^3 es la ganancia
    return pow(10, db / 60).toDouble();
  }

  /// Volumen que se le da al motor (el de la app por el factor de iPhone).
  double get _salida => volumen * _factorSalida * _factorDormir;

  /// En iPhone el VP9 no tiene decodificador por hardware y el AV1 de este
  /// libmpv tampoco: H.264 (videotoolbox) gasta mucho menos bateria.
  String get _codecVideo {
    final c = ajustes.texto('codec_video');
    return _ios && (c == 'auto' || c == 'sin_av1') ? 'compatible' : c;
  }

  String cadenaFiltros() {
    final partes = <String>[];
    if (_ios) {
      if (!ajustes.sino('ecualizador')) return '';
      final bandas = ajustes.bandasEq;
      for (var i = 0; i < min(10, bandas.length); i++) {
        if (bandas[i] != 0) partes.add('equalizer=f=${frecuenciasEq[i]}:t=o:w=1:g=${bandas[i]}');
      }
      return partes.isEmpty ? '' : 'lavfi=[${partes.join(',')}]';
    }
    if (ajustes.sino('ecualizador')) {
      final bandas = ajustes.bandasEq;
      for (var i = 0; i < min(10, bandas.length); i++) {
        if (bandas[i] != 0) {
          partes.add('equalizer=f=${frecuenciasEq[i]}:t=o:w=1:g=${bandas[i]}');
        }
      }
      final maximo = bandas.fold<int>(0, max);
      if (maximo > 0) partes.insert(0, 'volume=-${(maximo * 0.6).toStringAsFixed(1)}dB');
    }
    final nivel = ajustes.entero('super_volumen');
    if (nivel > 0) {
      partes.add('loudnorm=I=${nivelesSuperVolumen[nivel] ?? -9}:TP=-1.0:LRA=7');
      partes.add('alimiter=limit=0.96:attack=3:release=60:level=disabled');
    } else if (ajustes.sino('normalizar')) {
      partes.add('loudnorm=I=-14:TP=-1.5:LRA=11');
    }
    final base = partes.isEmpty ? '' : 'lavfi=[${partes.join(',')}]';
    if (!medirNivel || !_dj || !_filtroNivel) return base;
    // transiciones DJ: mide el nivel de lo que sale (no cambia el sonido) para
    // notar el silencio del final; se lee en `af-metadata/caudal`
    const medidor = '@caudal:lavfi=[astats=metadata=1:reset=1]';
    return base.isEmpty ? medidor : '$base,$medidor';
  }

  /// Solo en Android: el libmpv de iPhone no trae `astats`.
  bool get medirNivel => !_ios;

  Future<void> aplicarSonido() async {
    var af = cadenaFiltros();
    for (final m in [_a, _b]) {
      try {
        await m.nativo?.setProperty('af', af);
      } catch (_) {
        if (af.contains('@caudal:')) {
          // sin el medidor de nivel: se queda el resto y el DJ tira de SponsorBlock
          _filtroNivel = false;
          af = cadenaFiltros();
          try {
            await m.nativo?.setProperty('af', af);
          } catch (_) {}
        }
        // si el filtro no esta disponible en este telefono, suena sin el
      }
      await m.player.setRate(velocidad);
    }
    if (_ios && _fundido == null && _traspaso == null && _activo.fuente != null) {
      await _activo.player.setVolume(_salida);
    }
  }

  Future<void> fijarVolumen(double v) async {
    volumen = v.clamp(0, 100);
    if (_fundido == null && _traspaso == null) await _activo.player.setVolume(_salida);
    notifyListeners();
  }

  // ------------------------------------------------------------ iPhone

  Timer? _revivir;

  /// Apaga un motor. En iPhone, al cerrarse su salida `audiounit` mpv
  /// desactiva la sesion de audio y eso calla tambien al otro motor: se le
  /// reabre la salida (ao-reload) en cuanto el apagado termina.
  Future<void> _apagar(_Motor m) async {
    final tenia = await m.detener();
    if (!_ios || !tenia) return;
    _revivir?.cancel();
    _revivir = Timer(const Duration(milliseconds: 350), () {
      final vivo = _activo;
      if (vivo.fuente == null || !vivo.player.state.playing) return;
      vivo.nativo?.command(['ao-reload']).catchError((_) {});
    });
  }

  bool _videoApagado = false;

  /// iOS no deja dibujar con la GPU en segundo plano: el video se apaga
  /// (sigue el sonido, como YouTube Premium) y vuelve al regresar.
  Future<void> segundoPlano(bool fuera) async {
    if (!_ios) return;
    if (fuera == _videoApagado) return;
    if (fuera && modo != 'video') return;
    _videoApagado = fuera;
    for (final m in [_a, _b]) {
      try {
        await m.nativo?.setProperty('vid', fuera ? 'no' : 'auto');
      } catch (_) {}
    }
  }

  Future<void> fijarVelocidad(double v, {bool guardar = true}) async {
    velocidad = v.clamp(0.25, 3.0);
    for (final m in [_a, _b]) {
      await m.player.setRate(velocidad);
    }
    if (guardar) await ajustes.poner('velocidad', velocidad);
    notifyListeners();
  }

  // ------------------------------------------------------------ cola

  Future<void> reproducirLista(List<Json> pistas, {int inicio = 0, Json? contexto,
      bool? aleatorio, String? modo}) async {
    if (pistas.isEmpty) return;
    if (aleatorio != null) {
      this.aleatorio = aleatorio;
      await ajustes.poner('aleatorio', aleatorio, avisar: false);
    }
    inicio = inicio.clamp(0, pistas.length - 1);
    original = List.of(pistas);
    this.contexto = contexto;
    if (this.aleatorio) {
      final primera = (aleatorio == true && inicio == 0) ? pistas[Random().nextInt(pistas.length)] : pistas[inicio];
      final resto = pistas.where((p) => !identical(p, primera)).toList()..shuffle();
      secuencia = [primera, ...resto];
      pos = 0;
    } else {
      secuencia = List.of(pistas);
      pos = inicio;
    }
    if (modo != null) this.modo = modo;
    await _cargar(secuencia[pos]);
  }

  Future<void> reproducirPista(Json pista, {Json? contexto, String? modo, bool conRadio = true}) async {
    original = [pista];
    secuencia = [pista];
    pos = 0;
    this.contexto = contexto ??
        {'tipo': 'radio', 'id': pista['video_id'] ?? pista['clave'], 'titulo': 'Radio de ${pista['titulo']}'};
    if (modo != null) this.modo = modo;
    await _cargar(pista);
    if (conRadio && '${pista['video_id'] ?? ''}'.isNotEmpty && ajustes.sino('autoplay')) {
      _pedirRadio(pista);
    }
  }

  Future<void> iniciarRadio(Json pista) => reproducirPista(pista,
      contexto: {'tipo': 'radio', 'id': pista['video_id'], 'titulo': 'Radio de ${pista['titulo']}'});

  Future<void> reproducirRadioId(String playlistId, String titulo) async {
    _aviso('Preparando la radio…');
    try {
      final datos = await Catalogo.radio(playlistId: playlistId);
      final pistas = List<Json>.from(datos['pistas'] as List);
      if (pistas.isEmpty) return _aviso('Esa radio no tiene canciones ahora mismo.');
      await reproducirLista(pistas, contexto: {'tipo': 'radio', 'id': playlistId, 'titulo': titulo});
    } catch (e) {
      _aviso('$e');
    }
  }

  void agregarACola(List<Json> pistas) {
    if (pistas.isEmpty) return;
    if (actual == null) {
      reproducirLista(pistas, contexto: {'tipo': 'cola', 'id': '', 'titulo': 'Tu cola'});
      return;
    }
    proximas.addAll(pistas);
    notifyListeners();
    _aviso(pistas.length == 1 ? 'Añadido a la cola' : '${pistas.length} canciones añadidas a la cola');
  }

  void reproducirDespues(List<Json> pistas) {
    if (pistas.isEmpty) return;
    if (actual == null) {
      reproducirLista(pistas);
      return;
    }
    proximas.insertAll(0, pistas);
    notifyListeners();
    _aviso('Sonará a continuación');
  }

  void quitarProxima(int i) {
    if (i >= 0 && i < proximas.length) {
      proximas.removeAt(i);
      notifyListeners();
    }
  }

  void vaciarProximas() {
    proximas.clear();
    notifyListeners();
  }

  void insertarProxima(int i, Json p) {
    proximas.insert(i.clamp(0, proximas.length), p);
    notifyListeners();
  }

  void moverProxima(int de, int a) {
    if (de < 0 || de >= proximas.length) return;
    final p = proximas.removeAt(de);
    proximas.insert(a.clamp(0, proximas.length), p);
    notifyListeners();
  }

  void quitarDeSecuencia(int absoluto) {
    if (absoluto > pos && absoluto < secuencia.length) {
      final p = secuencia.removeAt(absoluto);
      original.removeWhere((x) => identical(x, p));
      notifyListeners();
    }
  }

  Future<void> saltarAProxima(int i) async {
    if (i < 0 || i >= proximas.length) return;
    final p = proximas.removeAt(i);
    proximas.removeRange(0, i);
    secuencia.insert(pos + 1, p);
    pos++;
    await _cargar(p);
  }

  Future<void> saltarA(int absoluto) async {
    if (absoluto < 0 || absoluto >= secuencia.length) return;
    pos = absoluto;
    await _cargar(secuencia[pos]);
  }

  List<Json> get siguientesDeContexto =>
      secuencia.sublist(min(pos + 1, secuencia.length), min(pos + 81, secuencia.length));

  Future<bool> alternarAleatorio() async {
    aleatorio = !aleatorio;
    await ajustes.poner('aleatorio', aleatorio, avisar: false);
    if (secuencia.isNotEmpty && pos >= 0) {
      final hechas = secuencia.sublist(0, pos + 1);
      final pendientes = secuencia.sublist(pos + 1);
      if (aleatorio) {
        pendientes.shuffle();
        secuencia = [...hechas, ...pendientes];
      } else {
        final enOriginal = original.toSet();
        final manuales = pendientes.where((p) => !enOriginal.contains(p)).toList();
        final quedan = pendientes.toSet();
        final ordenados = original.where(quedan.contains).toList();
        secuencia = [...hechas, ...manuales, ...ordenados];
      }
    }
    notifyListeners();
    return aleatorio;
  }

  Future<String> ciclarRepetir() async {
    const orden = ['no', 'todo', 'una'];
    repetir = orden[(orden.indexOf(repetir) + 1) % 3];
    await ajustes.poner('repetir', repetir, avisar: false);
    notifyListeners();
    return repetir;
  }

  // ------------------------------------------------------------ transporte

  Future<void> alternar() async {
    if (_traspaso != null) await _terminarTraspaso(true);
    if (actual == null) return;
    if (estado == EstadoRepro.parado) {
      await _cargar(actual!, inicio: posicion.value);
      return;
    }
    await _activo.player.playOrPause();
  }

  Future<void> pausar() async => _activo.player.pause();

  Future<void> reanudar() async {
    if (actual == null) return;
    if (estado == EstadoRepro.parado) {
      await _cargar(actual!, inicio: posicion.value);
    } else {
      await _activo.player.play();
    }
  }

  Future<void> detener() async {
    _traspaso = null;
    _cortarFundido();
    _revivir?.cancel();
    await _a.detener();
    await _b.detener();
    _fijarEstado(EstadoRepro.parado);
  }

  Future<void> buscar(Duration p) async {
    if (_traspaso != null) await _terminarTraspaso(true);
    await _activo.player.seek(p);
    posicion.value = p;
  }

  Future<void> avanzar(int segundos) =>
      buscar(Duration(milliseconds: max(0, posicion.value.inMilliseconds + segundos * 1000)));

  Future<void> siguiente({bool automatico = false}) async {
    if (actual == null) return;
    if (automatico && repetir == 'una') {
      await _cargar(actual!);
      return;
    }
    final objetivo = _avanzar();
    if (objetivo == null) {
      if (ajustes.sino('autoplay') && '${actual!['video_id'] ?? ''}'.isNotEmpty) {
        _pedirRadio(actual!, ySeguir: true);
      } else {
        await detener();
      }
      return;
    }
    await _cargar(objetivo);
  }

  Future<void> anterior() async {
    if (actual == null) return;
    if (posicion.value > const Duration(seconds: 4) || pos <= 0) {
      await buscar(Duration.zero);
      return;
    }
    pos--;
    await _cargar(secuencia[pos]);
  }

  Json? _mirarSiguiente() {
    if (repetir == 'una') return actual;
    if (proximas.isNotEmpty) return proximas.first;
    if (pos + 1 < secuencia.length) return secuencia[pos + 1];
    if (repetir == 'todo' && secuencia.isNotEmpty) return secuencia.first;
    return null;
  }

  Json? _avanzar() {
    if (proximas.isNotEmpty) {
      final p = proximas.removeAt(0);
      secuencia.insert(pos + 1, p);
      pos++;
      return p;
    }
    if (pos + 1 < secuencia.length) {
      pos++;
      return secuencia[pos];
    }
    if (repetir == 'todo' && secuencia.isNotEmpty) {
      if (aleatorio) secuencia.shuffle();
      pos = 0;
      return secuencia.first;
    }
    return null;
  }

  Future<void> _pedirRadio(Json pista, {bool ySeguir = false}) async {
    if (_buscandoRadio) return;
    _buscandoRadio = true;
    final gen = _gen;
    try {
      final datos = await Catalogo.radio(videoId: '${pista['video_id']}');
      final vistos = secuencia.map((p) => p['video_id']).toSet();
      final nuevas = <Json>[];
      for (final p in List<Json>.from(datos['pistas'] as List)) {
        if (p['video_id'] != null && !vistos.contains(p['video_id'])) {
          nuevas.add({...p, '_auto': true});
          vistos.add(p['video_id']);
        }
      }
      secuencia.addAll(nuevas);
      original.addAll(nuevas);
      notifyListeners();
      if (ySeguir && gen == _gen && nuevas.isNotEmpty) await siguiente();
      if (ySeguir && nuevas.isEmpty) await detener();
    } catch (_) {
      if (ySeguir) await detener();
    } finally {
      _buscandoRadio = false;
    }
  }

  // ------------------------------------------------------------ modo

  /// Cancion <-> video sin perder el punto ni dejar silencio: lo que suena
  /// sigue hasta que el video tiene imagen en el mismo punto.
  Future<void> cambiarModo(String nuevo) async {
    if (nuevo == modo || actual == null) {
      modo = nuevo;
      notifyListeners();
      return;
    }
    final sonando = estado == EstadoRepro.sonando;
    modo = nuevo;
    if (sonando) {
      _traspaso = {'saliente': _activo, 'objetivo': null, 'inicio': DateTime.now()};
      _vigilarTraspaso();
    }
    notifyListeners();
    await _cargar(actual!, inicio: posicion.value, pausado: estado == EstadoRepro.pausa, mismo: true);
  }

  Future<void> cambiarCalidadVideo(String alto, {bool guardar = true}) async {
    if (guardar) {
      await ajustes.poner('calidad_video', alto, avisar: false);
      _calidadForzada = null;
    } else {
      _calidadForzada = alto;
    }
    if (modo == 'video' && actual != null) {
      if (estado == EstadoRepro.sonando) {
        _traspaso = {'saliente': _activo, 'objetivo': null, 'inicio': DateTime.now()};
        _vigilarTraspaso();
      }
      await _cargar(actual!, inicio: posicion.value, mismo: true, forzarStream: true);
    }
  }

  // ------------------------------------------------------------ carga

  /// Cuantas veces se pidio un enlace nuevo para la pista actual (ver [_alError]).
  int _reintentos = 0;

  Future<void> _cargar(Json pista, {Duration inicio = Duration.zero, bool pausado = false,
      bool mismo = false, bool forzarStream = false, int intento = 0}) async {
    // en modo video, las dos pantallas listas antes de abrir (traspaso sin negro)
    if (modo == 'video') {
      _a.video;
      _b.video;
    }
    _cortarFundido();
    final gen = ++_gen;
    final cambio = !identical(pista, actual) || !mismo;
    actual = pista;
    if (intento == 0) _reintentos = 0;
    if (cambio) {
      _escuchaContada = false;
      _segmentos = [];
      _tramosDj = _tramosGuardados(pista);
      _silencioFinal.reiniciar();
      _calidadForzada = null;
      duracion.value = Duration(seconds: (pista['duracion'] as num?)?.toInt() ?? 0);
      posicion.value = inicio;
    }
    if (_traspaso == null) _fijarEstado(EstadoRepro.cargando);
    notifyListeners();

    final querVideo = modo == 'video';
    String? local;
    if (!forzarStream) {
      final archivo = pista['archivo'] as String?;
      if (archivo != null && archivo.isNotEmpty && coleccion.estaDescargada(pista)) {
        if (!(querVideo && pista['es_audio'] == true)) local = archivo;
      } else if (ajustes.sino('preferir_descargado')) {
        local = coleccion.copiaLocal(pista['video_id'] as String?, conVideo: querVideo)?['archivo'] as String?;
      }
    }
    Fuente f;
    if (local != null) {
      f = Fuente.archivo(local);
    } else {
      final vid = '${pista['video_id'] ?? ''}';
      if (vid.isEmpty) {
        _fijarEstado(EstadoRepro.parado);
        return _aviso('No hay de dónde reproducir esta pista.');
      }
      try {
        f = await streams.resolver(vid, video: querVideo,
            calidad: querVideo ? (_calidadForzada ?? ajustes.texto('calidad_video')) : ajustes.texto(Red.conDatos ? 'calidad_audio_datos' : 'calidad_audio'),
            codec: _codecVideo, intento: intento);
      } catch (e) {
        if (gen != _gen) return;
        if (_traspaso != null) {
          await _terminarTraspaso(false, volverAAudio: true);
          return _aviso('No se pudo abrir el video; sigue la canción.');
        }
        _fijarEstado(EstadoRepro.parado);
        _aviso('No se pudo reproducir: ${'$e'.split('\n').first}');
        if (proximas.isNotEmpty || pos + 1 < secuencia.length) {
          Timer(const Duration(milliseconds: 1500), () {
            if (gen == _gen) siguiente();
          });
        }
        return;
      }
    }
    if (gen != _gen) return;
    await _arrancar(gen, f, inicio, pausado);
  }

  Future<void> _arrancar(int gen, Fuente f, Duration inicio, bool pausado) async {
    fuente = f;
    final t = _traspaso;
    if (t != null) {
      // el nuevo motor carga EN PAUSA un poco por delante; cuando lo que suena
      // llega a ese punto, arranca y el viejo se apaga a la vez
      final saliente = t['saliente'] as _Motor;
      final entrante = identical(saliente, _a) ? _b : _a;
      _usaA = identical(entrante, _a);
      final objetivo = saliente.player.state.position +
          Duration(milliseconds: ((_estCarga + 0.6) * 1000).round());
      t['objetivo'] = objetivo;
      t['listo'] = false;
      t['desde'] = DateTime.now();
      await entrante.abrir(f, inicio: objetivo, pausado: true, volumen: 0, velocidad: velocidad);
    } else {
      await _apagar(_otro);
      await _activo.abrir(f, inicio: inicio, pausado: pausado, volumen: _salida, velocidad: velocidad);
    }
    notifyListeners();
    _prepararExtras(gen);
  }

  Future<void> _terminarTraspaso(bool completar, {bool volverAAudio = false}) async {
    final t = _traspaso;
    if (t == null) return;
    _traspaso = null;
    final saliente = t['saliente'] as _Motor;
    if (completar) {
      await _activo.player.setVolume(_salida);
      await _activo.player.play();
      await _apagar(saliente);
      final listoEn = t['listoEn'] as DateTime?;
      final desde = t['desde'] as DateTime?;
      if (listoEn != null && desde != null) {
        final tardo = listoEn.difference(desde).inMilliseconds / 1000.0;
        _estCarga = (_estCarga * 0.6 + tardo * 0.4).clamp(0.4, 6.0);
      }
      _fijarEstado(EstadoRepro.sonando);
    } else {
      final entrante = _activo;
      _usaA = identical(saliente, _a);
      await _apagar(entrante);
      if (volverAAudio) modo = 'audio';
      _fijarEstado(EstadoRepro.sonando);
    }
    notifyListeners();
  }

  void _vigilarTraspaso() {
    Timer.periodic(const Duration(milliseconds: 250), (timer) async {
      final t = _traspaso;
      if (t == null) return timer.cancel();
      if (DateTime.now().difference(t['inicio'] as DateTime) > const Duration(seconds: 5)) {
        timer.cancel();
        final obj = t['objetivo'] as Duration?;
        if (obj != null) {
          final s = (t['saliente'] as _Motor).player.state.position;
          await _activo.player.seek(s > obj ? s : obj);
        }
        await _terminarTraspaso(true);
      }
    });
  }

  void _prepararExtras(int gen) {
    final pista = actual;
    if (pista == null) return;
    final vid = '${pista['video_id'] ?? ''}';
    final saltar = ajustes.sino('sponsorblock');
    if (vid.isNotEmpty && (saltar || _dj)) {
      final cats = saltar && modo == 'video' && ajustes.sino('sponsorblock_videos')
          ? ['sponsor', 'selfpromo', 'interaction', 'music_offtopic']
          : ['music_offtopic'];
      Catalogo.segmentosASaltar(vid, cats).then((lista) {
        if (gen != _gen) return;
        final dur = duracion.value.inSeconds;
        final tramos = _aTramos(lista);
        // las transiciones DJ usan los tramos aunque no se salten
        _tramosDj = tramos.where((t) => t.$3 == 'music_offtopic').toList();
        if (saltar) {
          _segmentos = [
            for (final s in tramos)
              if (dur == 0 || (s.$2 - s.$1) < dur * 0.6) s
          ];
        }
      }).catchError((_) {});
    }
    Timer(const Duration(seconds: 4), () {
      if (gen == _gen) _precargar();
    });
    if (modo == 'audio' && vid.isNotEmpty && pista['archivo'] == null) {
      // el video de esta cancion, listo por si pulsas "Ver el video"
      Timer(const Duration(milliseconds: 2500), () {
        if (gen == _gen) {
          streams.resolver(vid, video: true, calidad: ajustes.texto('calidad_video'),
              codec: _codecVideo).catchError((_) => Fuente(url: ''));
        }
      });
    }
  }

  void _precargar() {
    final sig = _mirarSiguiente();
    if (sig == null || identical(sig, actual)) return;
    final vid = '${sig['video_id'] ?? ''}';
    if (vid.isNotEmpty && _dj && _tramosSiguiente?.$1 != vid) {
      // donde empieza la musica de la siguiente, para entrar justo ahi
      Catalogo.segmentosASaltar(vid, ['music_offtopic'])
          .then((lista) => _tramosSiguiente = (vid, _aTramos(lista)))
          .catchError((_) => _tramosSiguiente = (vid, <Tramo>[]));
    }
    if (vid.isEmpty || coleccion.estaDescargada(sig)) return;
    streams.resolver(vid, video: modo == 'video',
        calidad: modo == 'video' ? ajustes.texto('calidad_video') : ajustes.texto('calidad_audio'),
        codec: _codecVideo).catchError((_) => Fuente(url: ''));
    if (ajustes.sino('autoplay') && repetir == 'no' && proximas.isEmpty &&
        secuencia.length - pos <= 3 && '${actual?['video_id'] ?? ''}'.isNotEmpty) {
      _pedirRadio(actual!);
    }
  }

  // ------------------------------------------------------------ avisos del motor

  bool _esActual(_Motor m) => identical(m, _activo);

  void _alPosicion(_Motor m, Duration p) {
    final t = _traspaso;
    if (t != null) {
      if (identical(m, t['saliente'])) {
        posicion.value = p;
        final obj = t['objetivo'] as Duration?;
        if (obj == null) return;
        if (t['listo'] == true && p >= obj - const Duration(milliseconds: 40)) {
          _terminarTraspaso(true);
        } else if (t['listo'] != true && p > obj + const Duration(milliseconds: 300)) {
          final nuevo = p + Duration(milliseconds: ((_estCarga + 1) * 1000).round());
          t['objetivo'] = nuevo;
          _activo.player.seek(nuevo);
        }
      }
      return;
    }
    if (_fundido != null && identical(m, _fundido!['entrante'])) {
      // la nueva manda
    } else if (!_esActual(m)) {
      return;
    }
    posicion.value = p;
    final seg = p.inMilliseconds / 1000.0;
    for (final s in _segmentos) {
      if (seg >= s.$1 && seg < s.$2 - 0.5) {
        m.player.seek(Duration(milliseconds: (s.$2 * 1000).round()));
        _aviso('Saltado: ${_nombresSalto[s.$3] ?? 'segmento'}');
        _segmentos = _segmentos.where((x) => x.$1 != s.$1).toList();
        break;
      }
    }
    if (!_escuchaContada && actual != null) {
      final umbral = min(30.0, (duracion.value.inSeconds == 0 ? 60 : duracion.value.inSeconds) / 2);
      if (seg >= umbral) {
        _escuchaContada = true;
        coleccion.registrarEscucha(actual!, contexto);
      }
    }
    final cf = ajustes.entero('crossfade');
    final dur = duracion.value.inMilliseconds / 1000.0;
    // con "al terminar la cancion" no se funde con la siguiente: se apaga
    if (modo == 'audio' && _fundido == null && dur > 20 && repetir != 'una' && !_apagarAlFinal &&
        estado == EstadoRepro.sonando) {
      if (_dj) {
        final largo = duracionFundidoDj(cf);
        if (finDeMusica(_tramosDj, dur) - seg <= largo) {
          _empezarFundido(largo: largo);
        } else if (dur - seg <= 25 && medirNivel && _filtroNivel) {
          // el final se ha quedado en silencio: entra ya la siguiente
          _medirNivelDe(m, (db) {
            if (_silencioFinal.medir(db, DateTime.now()) && _fundido == null && identical(m, _activo)) {
              _empezarFundido(largo: 1.0);
            }
          });
        }
      } else if (cf > 0 && dur - seg <= cf) {
        _empezarFundido();
      }
    }
    if (DateTime.now().difference(_ultimoGuardado) > const Duration(seconds: 15)) {
      guardarSesion();
    }
  }

  void _alDuracion(_Motor m, Duration d) {
    if (_traspaso != null || !_esActual(m) || d == Duration.zero) return;
    duracion.value = d;
  }

  void _alSonar(_Motor m, bool sonando) {
    final t = _traspaso;
    if (t != null) {
      return;
    }
    if (!_esActual(m) && !(_fundido != null && identical(m, _fundido!['entrante']))) return;
    if (estado == EstadoRepro.parado && !sonando) return;
    _fijarEstado(sonando ? EstadoRepro.sonando : EstadoRepro.pausa);
  }

  void _alEsperar(_Motor m, bool esperando) {
    final t = _traspaso;
    if (t != null) {
      // el entrante ya tiene datos: listo para el cambio
      if (identical(m, _activo) && !esperando && m.fuente != null) {
        t['listo'] = true;
        t['listoEn'] ??= DateTime.now();
        final obj = t['objetivo'] as Duration?;
        final s = (t['saliente'] as _Motor).player.state.position;
        if (obj != null && s >= obj - const Duration(milliseconds: 40)) {
          final nuevo = s + const Duration(milliseconds: 800);
          t['objetivo'] = nuevo;
          m.player.seek(nuevo);
        }
      }
      return;
    }
    if (!_esActual(m)) return;
    if (esperando && estado == EstadoRepro.sonando) {
      _fijarEstado(EstadoRepro.cargando);
    } else if (!esperando && estado == EstadoRepro.cargando) {
      _fijarEstado(m.player.state.playing ? EstadoRepro.sonando : EstadoRepro.pausa);
    }
  }

  void _alTerminar(_Motor m) {
    final t = _traspaso;
    if (t != null) {
      if (identical(m, t['saliente'])) _terminarTraspaso(true);
      return;
    }
    if (_fundido != null && identical(m, _fundido!['saliente'])) return;
    if (!_esActual(m) || m.fuente == null) return;
    if (_apagarAlFinal) {
      _apagarAlFinal = false;
      detener().whenComplete(() => _ponerFactorDormir(1));
      _aviso('Temporizador: música detenida');
      notifyListeners();
      return;
    }
    siguiente(automatico: true);
  }

  void _alError(_Motor m, String e) {
    if (_traspaso != null && identical(m, _activo)) {
      _terminarTraspaso(false, volverAAudio: true);
      _aviso('No se pudo abrir el video; sigue la canción.');
      return;
    }
    if (!_esActual(m) || m.fuente == null) return;
    debugPrint('mpv: ${e.length > 160 ? '${e.substring(0, 160)}…' : e}');
    final pista = actual;
    if (pista == null || m.fuente!.local) return;
    // YouTube a veces da un enlace que luego no abre: se pide otro, con otro
    // cliente, sin perder el punto. Si tampoco abre, se avisa y se sigue.
    final vid = '${pista['video_id'] ?? ''}';
    if (vid.isNotEmpty && _reintentos < 2) {
      _reintentos++;
      streams.olvidar(vid);
      unawaited(_cargar(pista, inicio: posicion.value, mismo: true, forzarStream: true,
          pausado: estado == EstadoRepro.pausa, intento: _reintentos));
      return;
    }
    _fijarEstado(EstadoRepro.parado);
    _aviso('No se pudo reproducir esta canción. Pasamos a la siguiente.');
    final gen = _gen;
    if (proximas.isNotEmpty || pos + 1 < secuencia.length) {
      Timer(const Duration(milliseconds: 1500), () {
        if (gen == _gen) siguiente();
      });
    }
  }

  void _fijarEstado(EstadoRepro e) {
    if (e == estado) return;
    estado = e;
    notifyListeners();
    if (e == EstadoRepro.pausa || e == EstadoRepro.parado) guardarSesion();
  }

  // ------------------------------------------------------------ fundido

  /// Tramos ya pedidos para [pista] (la "siguiente" que ahora pasa a sonar).
  List<Tramo> _tramosGuardados(Json pista) {
    final t = _tramosSiguiente;
    return t != null && t.$1 == '${pista['video_id'] ?? ''}' ? t.$2 : [];
  }

  static List<Tramo> _aTramos(List<List<dynamic>> lista) => [
        for (final s in lista)
          if (s.length >= 3) ((s[0] as num).toDouble(), (s[1] as num).toDouble(), '${s[2]}')
      ];

  /// Lee el nivel que mide el filtro `@caudal` de un motor (sin solaparse).
  void _medirNivelDe(_Motor m, void Function(double?) usar) {
    final n = m.nativo;
    if (n == null || !_midiendo.add(m)) return;
    n.getProperty('af-metadata/caudal').then((t) => usar(nivelDeMetadatos(t))).catchError((_) {})
        .whenComplete(() => _midiendo.remove(m));
  }

  Future<void> _empezarFundido({double? largo}) async {
    final sig = _mirarSiguiente();
    if (sig == null) return;
    Fuente? f;
    final local = coleccion.estaDescargada(sig)
        ? (sig['archivo'] as String? ?? coleccion.copiaLocal(sig['video_id'] as String?)?['archivo'] as String?)
        : null;
    if (local != null) {
      f = Fuente.archivo(local);
    } else if ('${sig['video_id'] ?? ''}'.isNotEmpty) {
      f = streams.enCache('${sig['video_id']}', video: false, calidad: ajustes.texto('calidad_audio'),
          codec: _codecVideo);
    }
    if (f == null) return;
    final saliente = _activo;
    final entrante = _otro;
    final objetivoPista = _avanzar();
    if (objetivoPista == null) return;
    _gen++;
    _usaA = identical(entrante, _a);
    final dj = largo != null;
    final tramos = dj ? _tramosGuardados(objetivoPista) : <Tramo>[];
    final durSig = ((objetivoPista['duracion'] as num?) ?? 0).toDouble();
    // DJ: la siguiente entra donde empieza su musica, sin la intro muda
    final inicio = dj ? inicioDeMusica(tramos, durSig) : 0.0;
    _fundido = {'saliente': saliente, 'entrante': entrante, 'inicio': DateTime.now(),
      'dur': largo ?? ajustes.entero('crossfade').toDouble(), 'dj': dj, 'saltos': 0};
    _silencioEntrada.reiniciar();
    _silencioFinal.reiniciar();
    await entrante.abrir(f, volumen: 0, velocidad: velocidad,
        inicio: Duration(milliseconds: (inicio * 1000).round()));
    fuente = f;
    actual = objetivoPista;
    _escuchaContada = false;
    _segmentos = [];
    _tramosDj = tramos;
    duracion.value = Duration(seconds: (objetivoPista['duracion'] as num?)?.toInt() ?? 0);
    posicion.value = Duration.zero;
    notifyListeners();
    _pasosFundido = Timer.periodic(const Duration(milliseconds: 50), (_) => _pasoFundido());
    _prepararExtras(_gen);
  }

  void _pasoFundido() {
    final f = _fundido;
    if (f == null) {
      _pasosFundido?.cancel();
      return;
    }
    final t = DateTime.now().difference(f['inicio'] as DateTime).inMilliseconds / 1000.0;
    final avance = min(1.0, t / max(0.5, f['dur'] as double));
    final entrante = f['entrante'] as _Motor;
    if (f['dj'] == true && medirNivel && _filtroNivel && (f['saltos'] as int) < 8) {
      // la siguiente empieza callada (sin tramo en SponsorBlock): se adelanta
      // a saltitos hasta su primer sonido, mientras aun no se oye
      final p = entrante.player.state.position;
      if (p > const Duration(milliseconds: 300) && p < const Duration(seconds: 15) &&
          entrante.player.state.playing && !entrante.player.state.buffering) {
        _medirNivelDe(entrante, (db) {
          if (!identical(_fundido, f) || !_silencioEntrada.medir(db, DateTime.now())) return;
          f['saltos'] = (f['saltos'] as int) + 1;
          _silencioEntrada.reiniciar();
          entrante.player.seek(entrante.player.state.position + const Duration(seconds: 1));
        });
      }
    }
    entrante.player.setVolume(_salida * sin(avance * pi / 2));
    (f['saliente'] as _Motor).player.setVolume(_salida * cos(avance * pi / 2));
    if (avance >= 1) {
      _apagar(f['saliente'] as _Motor);
      _fundido = null;
      _pasosFundido?.cancel();
      _activo.player.setVolume(_salida);
    }
  }

  void _cortarFundido() {
    final f = _fundido;
    if (f == null) return;
    _apagar(f['saliente'] as _Motor);
    _fundido = null;
    _pasosFundido?.cancel();
    _activo.player.setVolume(_salida);
  }

  // ------------------------------------------------------------ temporizador

  void programarApagado({int? minutos, bool alTerminar = false}) {
    _apagarAlFinal = alTerminar;
    _apagarEn = minutos == null ? null : DateTime.now().add(Duration(minutes: minutos));
    _ponerFactorDormir(1);
    if (minutos != null) {
      _aviso('La música se detendrá en $minutos min');
    } else if (alTerminar) {
      _aviso('La música se detendrá al terminar esta canción');
    } else {
      _aviso('Temporizador desactivado');
    }
    notifyListeners();
  }

  /// null = sin temporizador, -1 = al terminar la cancion, si no segundos.
  int? get restanteApagado {
    if (_apagarAlFinal) return -1;
    if (_apagarEn == null) return null;
    return max(0, _apagarEn!.difference(DateTime.now()).inSeconds);
  }

  /// Segundos que faltan para que el temporizador apague (null = no hay).
  double? get _faltaParaDormir {
    if (_apagarEn != null) return _apagarEn!.difference(DateTime.now()).inMilliseconds / 1000.0;
    if (_apagarAlFinal && duracion.value > Duration.zero) {
      return (duracion.value - posicion.value).inMilliseconds / 1000.0;
    }
    return null;
  }

  /// Pone el volumen que toca segun el temporizador para dormir.
  void _ponerFactorDormir(double factor) {
    if (factor == _factorDormir) return;
    _factorDormir = factor;
    if (_fundido == null && _traspaso == null && _activo.fuente != null) {
      _activo.player.setVolume(_salida);
    }
  }

  bool _pausandoParaDormir = false;

  void _ticApagado() {
    if (_pausandoParaDormir) return;
    // los ultimos 30 s el volumen baja poco a poco en vez de cortar de golpe
    _ponerFactorDormir(ajustes.sino('apagado_suave') ? factorApagado(_faltaParaDormir) : 1);
    if (_apagarEn != null && DateTime.now().isAfter(_apagarEn!)) {
      _apagarEn = null;
      // ya callada: se pausa y se devuelve el volumen para cuando vuelva a sonar
      _pausandoParaDormir = true;
      pausar().whenComplete(() {
        _pausandoParaDormir = false;
        _ponerFactorDormir(1);
      });
      _aviso('Temporizador: música en pausa. ¡Buenas noches!');
      notifyListeners();
    }
  }

  // ------------------------------------------------------------ sesion

  Future<void> guardarSesion() async {
    _ultimoGuardado = DateTime.now();
    if (actual == null) return;
    Json limpia(Json p) => {for (final e in p.entries) if (!e.key.startsWith('_') || e.key == '_auto') e.key: e.value};
    final ini = max(0, pos - 30);
    await coleccion.guardarEstado('sesion', {
      'secuencia': [for (final p in secuencia.sublist(ini, min(secuencia.length, pos + 120))) limpia(p)],
      'pos': pos - ini,
      'proximas': [for (final p in proximas.take(100)) limpia(p)],
      'contexto': contexto,
      'posicion': posicion.value.inMilliseconds,
    });
  }

  Future<bool> restaurarSesion() async {
    final d = await coleccion.estado('sesion');
    if (d is! Map || (d['secuencia'] as List?)?.isEmpty != false) return false;
    secuencia = [for (final p in d['secuencia'] as List) Map<String, dynamic>.from(p as Map)];
    original = List.of(secuencia);
    pos = ((d['pos'] as num?)?.toInt() ?? 0).clamp(0, secuencia.length - 1);
    proximas = [for (final p in (d['proximas'] as List? ?? [])) Map<String, dynamic>.from(p as Map)];
    contexto = d['contexto'] == null ? null : Map<String, dynamic>.from(d['contexto'] as Map);
    actual = secuencia[pos];
    posicion.value = Duration(milliseconds: (d['posicion'] as num?)?.toInt() ?? 0);
    duracion.value = Duration(seconds: (actual!['duracion'] as num?)?.toInt() ?? 0);
    estado = EstadoRepro.parado;
    notifyListeners();
    return true;
  }

  void _aviso(String t) => _avisos.add(t);

  @override
  Future<void> dispose() async {
    _relojApagado?.cancel();
    _revivir?.cancel();
    await guardarSesion();
    await _a.player.dispose();
    await _b.player.dispose();
    super.dispose();
  }
}
