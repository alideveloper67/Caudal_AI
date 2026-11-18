import 'dart:async';
import 'dart:collection';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:media_kit_video/media_kit_video.dart';

import '../nucleo/ajustes.dart';
import '../nucleo/catalogo.dart';
import '../nucleo/coleccion.dart';
import '../nucleo/mezcla_dj.dart';
import '../nucleo/recomendador.dart';
import '../nucleo/ritmo.dart';
import '../nucleo/red.dart';
import '../nucleo/streams.dart';
import '../nucleo/transiciones.dart';
import '../nucleo/vida_app.dart';
import 'frenos.dart';
import 'jugador.dart';

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

/// El libmpv de Android (media_kit_libs_android_*) trae el mismo ffmpeg minimo:
/// de los filtros de sonido solo `equalizer`, `aresample` y `scaletempo`.
/// Pedirle `loudnorm`, `alimiter`, `volume` o `astats` no da error al ponerlo:
/// falla al abrir la cancion, mpv apaga el sonido ("Audio filter initialized
/// failed") y la cancion no suena. Asi fallaban todas en la 2.0.0-2.0.5, porque
/// "normalizar" viene encendido. En los dos telefonos el sonido va como en iPhone.
bool get _filtrosMinimos =>
    defaultTargetPlatform == TargetPlatform.iOS || defaultTargetPlatform == TargetPlatform.android;

enum EstadoRepro { parado, cargando, sonando, pausa }

/// Uno de los dos motores (libmpv en el teléfono y la PC; el reproductor de
/// YouTube en la web, ver [Jugador]) con su pantalla de video.
class _Motor {
  _Motor() {
    // lo que dice el motor por dentro (403, certificados, red...) al registro del sistema
    player.stream.log.listen((l) {
      if (l.level == 'error' || l.level == 'fatal' || l.level == 'warn') {
        debugPrint('mpvlog ${l.prefix}: ${l.text.trim()}');
      }
    });
    _afinar();
  }

  final Jugador player = Jugador.crear();

  /// La pantalla del video de mpv: se crea la primera vez que hace falta (no al
  /// abrir la app). En la web es null: el video es el recuadro de YouTube.
  VideoController? get video => player.video;

  /// Lectura anticipada generosa: que un bajon de red no corte nada.
  Future<void> _afinar() async {
    final opciones = {
      'cache': 'yes',
      'cache-secs': '60',
      'demuxer-readahead-secs': '30',
      // demuxer-max-bytes va segun lo que se abra (ver [_ajustarLectura])
      'demuxer-max-back-bytes': '16MiB',
      'cache-pause-initial': 'no',
      'cache-pause-wait': '1',
      'ytdl': 'no',
      'audio-buffer': '0.3',
      // en iPhone el ecualizador y el super volumen van por el volumen de mpv
      if (_filtrosMinimos) 'volume-max': '200',
    };
    for (final e in opciones.entries) {
      try {
        await player.setProperty(e.key, e.value);
      } catch (_) {}
    }
  }

  Fuente? fuente;

  /// Lo que se lee por adelantado segun lo que suena: con solo audio, 16 MiB
  /// son ya varios minutos de cancion; con video hacen falta los 64 MiB.
  bool? _lecturaVideo;

  Future<void> _ajustarLectura(bool video) async {
    if (_lecturaVideo == video) return;
    _lecturaVideo = video;
    try {
      await player.setProperty('demuxer-max-bytes', video ? '64MiB' : '16MiB');
    } catch (_) {}
  }

  Future<void> abrir(Fuente f, {Duration inicio = Duration.zero, bool pausado = false,
      double volumen = 100, double velocidad = 1, bool video = true}) async {
    fuente = f;
    await _ajustarLectura(video || f.alto > 0 || f.audioUrl != null);
    await player.setVolume(volumen);
    await player.setRate(velocidad);
    await player.open(f, inicio: inicio > const Duration(seconds: 1) ? inicio : null, play: !pausado);
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
  VideoController? get pantalla => _activo.video;

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

  /// Se enciende si un filtro de sonido no existe en este telefono (ver [_alError]):
  /// desde ahi suena sin filtros en vez de no sonar.
  bool _sinFiltros = false;
  final _silencioFinal = DetectorSilencio();
  final _silencioEntrada = DetectorSilencio(umbralDb: -50, minimo: const Duration(milliseconds: 300));
  final Set<_Motor> _midiendo = {};

  bool get _dj => ajustes.sino('transicion_dj') && !modoEstudio;

  /// «Mezcla DJ»: enlaza las canciones con un cambio largo y de graves.
  bool get _mezclaDj => ajustes.sino('mezcla_dj') && !modoEstudio;

  /// Los pasos del set de la mesa del Mezclador que suena ahora: cada pista
  /// de [secuencia] (por identidad) con como se pasa de ella a la siguiente.
  final Map<Json, PasoMezcla> _pasosSet = HashMap<Json, PasoMezcla>.identity();
  bool _cargandoSet = false;

  /// El ritmo de cada cancion del set (por clave), si se analizo.
  Map<String, AnalisisRitmo> _ritmoSet = {};

  /// El ecualizador de 3 bandas que lleva cada motor (de la cancion que suena en el).
  final Map<_Motor, String> _eq3 = {};

  /// ¿Se puede acercar el tempo de una cancion al de otra sin cambiarle el tono?
  /// Hace falta el filtro de estiramiento de tiempo del motor: en Android esta
  /// (scaletempo); en iPhone no, y alli se mezcla sin igualar el tempo.
  bool get puedeEstirarTiempo => !_ios && !kIsWeb;

  /// ¿Se pueden hacer los barridos de filtro y el cambio de graves?
  bool get puedeFiltrar => !Jugador.esWeb && !_sinFiltros;

  /// El eco necesita un filtro que el motor del telefono no trae.
  bool get puedeEco => false;

  /// Una prueba de un paso: al terminar el cambio se pausa sola.
  bool _probando = false;
  String _resolviendoSiguiente = '';

  /// ¿Suena ahora un set de la mesa del Mezclador?
  bool get sonandoSet => actual != null && _pasosSet.containsKey(actual);

  // ------------------------------------------------------------ sonido

  /// En iPhone no hay limitador ni normalizador: el super volumen sube sin
  /// limitar y "normalizar" no hace nada.
  bool get sonidoLimitado => _filtrosMinimos;

  /// Multiplicador del volumen que piden el ecualizador (margen) y el super
  /// volumen en iPhone. En Android eso lo hacen los filtros y vale 1.
  double get _factorSalida {
    if (!_filtrosMinimos) return 1;
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
  double get _salida => volumen * _factorSalida * _factorDormir * _factorEstudio;

  /// En iPhone el VP9 no tiene decodificador por hardware y el AV1 de este
  /// libmpv tampoco: H.264 (videotoolbox) gasta mucho menos bateria.
  String get _codecVideo {
    final c = ajustes.texto('codec_video');
    return _ios && (c == 'auto' || c == 'sin_av1') ? 'compatible' : c;
  }

  String cadenaFiltros() {
    if (_sinFiltros) return '';
    final partes = <String>[];
    if (_filtrosMinimos) {
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
  bool get medirNivel => !_filtrosMinimos;

  Future<void> aplicarSonido() async {
    var af = cadenaFiltros();
    for (final m in [_a, _b]) {
      try {
        await m.player.setProperty('af', af);
      } catch (_) {
        if (af.contains('@caudal:')) {
          // sin el medidor de nivel: se queda el resto y el DJ tira de SponsorBlock
          _filtroNivel = false;
          af = cadenaFiltros();
          try {
            await m.player.setProperty('af', af);
          } catch (_) {}
        }
        // si el filtro no esta disponible en este telefono, suena sin el
      }
      await m.player.setRate(velocidad);
    }
    if (_filtrosMinimos && _fundido == null && _traspaso == null && _activo.fuente != null) {
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
      vivo.player.command(['ao-reload']).catchError((_) {});
    });
  }

  /// Se pasó a audio al salir de la app: al volver, se vuelve al video.
  bool volverAVideo = false;

  /// Salir de la app o apagar la pantalla con un video sonando: pasa a modo
  /// audio sin cortar (el video se apaga al momento y lo que suena sigue
  /// mientras se prepara el audio), y al volver regresa al video en el mismo
  /// punto. Así la música no se pausa ni gasta datos y batería en una imagen
  /// que nadie ve. Con la ventanita flotante (PiP) no se llama: ahí el video
  /// se sigue viendo.
  Future<void> segundoPlano(bool fuera) async {
    if (kIsWeb) return;
    if (fuera) {
      if (volverAVideo || modo != 'video' || actual == null) return;
      if (estado != EstadoRepro.sonando && estado != EstadoRepro.cargando) return;
      volverAVideo = true;
      // sin imagen ya mismo: en segundo plano no hay donde dibujarla (iOS no deja usar la GPU)
      for (final m in [_a, _b]) {
        try {
          await m.player.setProperty('vid', 'no');
        } catch (_) {}
      }
      await cambiarModo('audio');
      return;
    }
    if (!volverAVideo) return;
    volverAVideo = false;
    for (final m in [_a, _b]) {
      try {
        await m.player.setProperty('vid', 'auto');
      } catch (_) {}
    }
    // si mientras tanto se eligió otra cosa a mano, se respeta
    if (modo == 'audio' && actual != null) await cambiarModo('video');
  }

  Future<void> fijarVelocidad(double v, {bool guardar = true}) async {
    velocidad = v.clamp(0.25, 3.0);
    for (final m in [_a, _b]) {
      await m.player.setRate(velocidad);
    }
    if (guardar) await ajustes.poner('velocidad', velocidad);
    notifyListeners();
  }

  // ------------------------------------------------------------ modo estudio

  /// Mientras es true: sin transiciones DJ, con fundido suave de al menos 5 s,
  /// sin radio automatica (la cola es la del perfil y no cambia de estilo).
  bool modoEstudio = false;
  double _factorEstudio = 1;
  String? _repetirAntes;
  bool? _aleatorioAntes;

  bool get _autoplay => ajustes.sino('autoplay') && !modoEstudio;

  /// Segundos de fundido entre canciones: en modo estudio, nunca menos de 5.
  int get _crossfade {
    final c = ajustes.entero('crossfade');
    return modoEstudio ? max(5, c) : c;
  }

  /// Cuanto de su volumen conserva la musica (1 = todo). Lo baja el modo estudio
  /// durante los bloques de enfoque o los descansos.
  double get factorEstudio => _factorEstudio;

  Future<void> fijarFactorEstudio(double f) async {
    _factorEstudio = f.clamp(0.0, 1.0);
    if (_fundido == null && _traspaso == null && _activo.fuente != null) {
      try {
        await _activo.player.setVolume(_salida);
      } catch (_) {}
    }
    notifyListeners();
  }

  /// Pone a sonar la cola de un perfil de estudio: en orden, en bucle y sin
  /// que el autoplay la cambie de estilo. No toca tus ajustes guardados.
  Future<void> iniciarEstudio(List<Json> pistas, {String titulo = 'Modo estudio'}) async {
    if (pistas.isEmpty) return;
    if (!modoEstudio) {
      _repetirAntes = repetir;
      _aleatorioAntes = aleatorio;
    }
    modoEstudio = true;
    repetir = 'todo';
    aleatorio = false;
    proximas.clear();
    await reproducirLista(pistas,
        contexto: {'tipo': 'estudio', 'id': titulo, 'titulo': titulo}, modo: 'audio');
  }

  /// Sale del modo estudio y devuelve repetir, aleatorio y volumen a como estaban.
  Future<void> salirEstudio() async {
    if (!modoEstudio) return;
    modoEstudio = false;
    repetir = _repetirAntes ?? repetir;
    aleatorio = _aleatorioAntes ?? aleatorio;
    _repetirAntes = null;
    _aleatorioAntes = null;
    await fijarFactorEstudio(1);
  }

  // ------------------------------------------------------------ cola

  Future<void> reproducirLista(List<Json> pistas, {int inicio = 0, Json? contexto,
      bool? aleatorio, String? modo, Duration desde = Duration.zero}) async {
    if (pistas.isEmpty) return;
    if (!_cargandoSet) {
      _pasosSet.clear();
      _probando = false;
    }
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
    await _cargar(secuencia[pos], inicio: desde);
  }

  /// Reproduce un set de la mesa del Mezclador: las canciones en ese orden y,
  /// entre cada dos, el cambio que pide su paso (cuando entra la siguiente,
  /// cuanto dura y si cambian los graves). Empieza en [desde] de la primera.
  Future<void> reproducirSet(List<PasoMezcla> pasos, {String titulo = 'Tu mezcla',
      Duration desde = Duration.zero, Map<String, AnalisisRitmo> ritmo = const {}}) async {
    if (pasos.isEmpty) return;
    _ritmoSet = ritmo;
    final copias = [for (final p in pasos) <String, dynamic>{...p.pista}];
    _cargandoSet = true;
    try {
      _pasosSet.clear();
      for (final (i, c) in copias.indexed) {
        _pasosSet[c] = pasos[i];
      }
      proximas.clear();
      await reproducirLista(copias,
          contexto: {'tipo': 'mezcla', 'id': titulo, 'titulo': titulo},
          aleatorio: false, modo: 'audio', desde: desde);
    } finally {
      _cargandoSet = false;
    }
  }

  /// Prueba un solo paso: empieza unos segundos antes del cambio de [paso] y
  /// deja oir como entra [siguiente]. Al acabar el cambio se pausa sola.
  Future<void> probarPaso(PasoMezcla paso, Json siguiente,
      {Map<String, AnalisisRitmo> ritmo = const {}}) async {
    if (paso.duracionPista <= 0) {
      return _aviso('No se sabe cuánto dura esa canción, así que no se puede probar el cambio.');
    }
    // el enlace de la siguiente, listo antes de empezar, para que el cambio no se pierda
    final vid = '${siguiente['video_id'] ?? ''}';
    if (vid.isNotEmpty && !coleccion.estaDescargada(siguiente)) {
      try {
        await streams.resolver(vid, video: false, calidad: ajustes.texto('calidad_audio'),
            codec: _codecVideo);
      } catch (_) {}
    }
    final desde = max(0.0, paso.inicioDelCambio - 6);
    await reproducirSet([
      paso,
      PasoMezcla(pista: siguiente),
    ], titulo: 'Prueba del cambio', desde: Duration(seconds: desde.round()), ritmo: ritmo);
    _probando = true;
  }

  Future<void> reproducirPista(Json pista, {Json? contexto, String? modo, bool conRadio = true}) async {
    _pasosSet.clear();
    _probando = false;
    original = [pista];
    secuencia = [pista];
    pos = 0;
    this.contexto = contexto ??
        {'tipo': 'radio', 'id': pista['video_id'] ?? pista['clave'], 'titulo': 'Radio de ${pista['titulo']}'};
    if (modo != null) this.modo = modo;
    await _cargar(pista);
    if (conRadio && '${pista['video_id'] ?? ''}'.isNotEmpty && _autoplay) {
      _pedirRadio(pista);
    }
  }

  Future<void> iniciarRadio(Json pista) => reproducirPista(pista,
      contexto: {'tipo': 'radio', 'id': pista['video_id'], 'titulo': 'Radio de ${pista['titulo']}'});

  Future<void> reproducirRadioId(String playlistId, String titulo) async {
    _aviso('Preparando la radio…');
    try {
      final datos = await Catalogo.radio(playlistId: playlistId).timeout(const Duration(seconds: 40));
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

  /// Tu gusto, para limpiar la radio automatica (se recalcula cada 10 min).
  Gusto? _gusto;
  DateTime _gustoDe = DateTime(2000);

  Future<Gusto?> _gustoActual() async {
    if (_gusto != null && DateTime.now().difference(_gustoDe) < const Duration(minutes: 10)) return _gusto;
    try {
      _gusto = await Recomendador.gusto(coleccion);
      _gustoDe = DateTime.now();
    } catch (_) {}
    return _gusto;
  }

  Future<void> siguiente({bool automatico = false}) async {
    if (actual == null) return;
    // saltar antes de que cuente como escuchada: el recomendador lo aprende
    if (!automatico && !_escuchaContada && posicion.value < const Duration(seconds: 30) &&
        '${actual!['video_id'] ?? ''}'.isNotEmpty && fuente?.local != true) {
      unawaited(Recomendador.anotarSalto(coleccion, actual!).catchError((_) {}));
      // el salto se aplica tambien al gusto en memoria (sin releer el historial)
      _gusto = _gusto?.conSalto(actual!);
    }
    if (automatico && repetir == 'una') {
      await _cargar(actual!);
      return;
    }
    final objetivo = _avanzar();
    if (objetivo == null) {
      if (sonandoSet) {
        // se acabo el set: no se le pega una radio detras
        await detener();
        return;
      }
      if (_autoplay && '${actual!['video_id'] ?? ''}'.isNotEmpty) {
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
      // con tope de tiempo: si YouTube Music no contesta, la radio no se queda colgada ni deja
      // cerrada la puerta a pedirla otra vez
      final datos = await Catalogo.radio(videoId: '${pista['video_id']}').timeout(const Duration(seconds: 40));
      final vistos = secuencia.map((p) => p['video_id']).toSet();
      final nuevas = <Json>[];
      var candidatas = List<Json>.from(datos['pistas'] as List);
      // afinada con tu gusto: sin lo saltado ni lo de las ultimas ~50, sin tandas del
      // mismo artista y con ~20 % de artistas nuevos afines
      final g = await _gustoActual();
      if (g != null) {
        final yaEnCola = {for (final p in secuencia) '${p['video_id']}'};
        final ordenadas = Recomendador.prepararRadio(pista, candidatas, g,
            vistos: yaEnCola, azar: '${pista['video_id']}'.hashCode);
        // si el filtro deja la cola casi vacia, se usa la radio sin afinar
        candidatas = ordenadas.length >= 4 ? ordenadas : Recomendador.limpiarRadio(candidatas, g);
      }
      for (final p in candidatas) {
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
    } catch (e) {
      if (ySeguir) {
        _aviso(e is CatalogoError ? '$e' : 'No pude seguir con canciones parecidas. Revisa tu conexión.');
        await detener();
      }
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
  Duration _reintentoEn = Duration.zero;

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
      final original = '${pista['video_id'] ?? ''}';
      // si YouTube dijo que ese video no se puede reproducir, suena otra subida de la misma canción
      final vid = _videoAlterno[original] ?? original;
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
        // «video no reproducible»: se busca otra subida de la misma canción antes de rendirse
        if (!_videoAlterno.containsKey(original) &&
            RegExp(r'unplayable|unavailable|restricted|private|ninguna pista|no dio ninguna', caseSensitive: false).hasMatch('$e')) {
          final otro = await _buscarAlterno(pista, original);
          if (gen != _gen) return;
          if (otro != null) {
            _videoAlterno[original] = otro;
            return _cargar(pista, inicio: inicio, pausado: pausado, mismo: mismo, forzarStream: forzarStream, intento: 0);
          }
          _videoAlterno[original] = ''; // no hay otra: que no vuelva a buscar
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

  /// Videos que YouTube no deja reproducir → otra subida de la misma canción.
  final Map<String, String> _videoAlterno = {};

  Future<String?> _buscarAlterno(Json pista, String malo) async {
    try {
      final texto = '${pista['titulo'] ?? ''} ${pista['artista'] ?? ''}'.trim();
      if (texto.isEmpty) return null;
      final r = await Catalogo.buscar(texto, filtro: 'canciones', limite: 8)
          .timeout(const Duration(seconds: 12));
      for (final x in r) {
        final id = '${x['video_id'] ?? ''}';
        if (x['tipo'] == 'pista' && id.isNotEmpty && id != malo) return id;
      }
    } catch (_) {}
    return null;
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
      await entrante.abrir(f, inicio: objetivo, pausado: true, volumen: 0, velocidad: velocidad,
          video: modo == 'video');
    } else {
      await _apagar(_otro);
      _eq3.remove(_otro);
      // el ecualizador de la cancion (si va en una mezcla); si el motor traia otro, se limpia
      final eq = filtroEq3(_pasosSet[actual]?.eq ?? const [0, 0, 0]);
      if (eq != (_eq3[_activo] ?? '')) {
        _eq3[_activo] = eq;
        await _ponerAf(_activo, '');
      }
      await _activo.abrir(f, inicio: inicio, pausado: pausado, volumen: _salida, velocidad: velocidad,
          video: modo == 'video');
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
    if (_autoplay && repetir == 'no' && proximas.isEmpty && !sonandoSet &&
        secuencia.length - pos <= 3 && '${actual?['video_id'] ?? ''}'.isNotEmpty) {
      _pedirRadio(actual!);
    }
  }

  // ------------------------------------------------------------ avisos del motor

  bool _esActual(_Motor m) => identical(m, _activo);

  /// Publica la posicion solo si avanzo un paso (ver [publicarPosicion]):
  /// libmpv avisa muchas veces por segundo y cada aviso reconstruia la barra,
  /// la letra, el mini reproductor y la notificacion.
  void _ponerPosicion(Duration p) {
    if (publicarPosicion(p, posicion.value, fondo: !VidaApp.primerPlano.value)) posicion.value = p;
  }

  void _alPosicion(_Motor m, Duration p) {
    final t = _traspaso;
    if (t != null) {
      if (identical(m, t['saliente'])) {
        _ponerPosicion(p);
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
    // la logica (saltos, fundidos, escucha contada) mira cada aviso; la
    // pantalla solo se entera cada ~200 ms (1 s en segundo plano)
    _ponerPosicion(p);
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
        unawaited(Recomendador.perdonar(coleccion, actual!).catchError((_) {}));
      }
    }
    final cf = _crossfade;
    final dur = duracion.value.inMilliseconds / 1000.0;
    // con "al terminar la cancion" no se funde con la siguiente: se apaga
    if (modo == 'audio' && _fundido == null && dur > 20 && repetir != 'una' && !_apagarAlFinal &&
        estado == EstadoRepro.sonando) {
      final paso = _pasosSet[actual];
      if (paso != null) {
        // la mesa del Mezclador: el cambio que pidio el usuario para este paso
        if (_mirarSiguiente() != null) {
          final ritmo = _ritmoSet['${actual?['clave']}'];
          // el cambio empieza en un inicio de compas (si se sabe el tempo); 0,3 s antes por lo que tarda en arrancar el otro motor
          final cuando = momentoDeEntrada(paso, finDeMusica(_tramosDj, dur), ritmo) - 0.3;
          if (seg >= cuando) _empezarFundido(largo: paso.fundidoEfectivo, paso: paso, ritmoSale: ritmo);
        }
      } else if (_mezclaDj) {
        // «Mezcla DJ»: entra la siguiente `largo` segundos antes del final, con cambio de graves
        final largo = segundosDj(ajustes.entero('mezcla_dj_seg')).toDouble();
        if (dur > largo * 2 + 4 && finDeMusica(_tramosDj, dur) - seg <= largo) {
          _empezarFundido(largo: largo, graves: ajustes.sino('mezcla_dj_graves'));
        }
      } else if (_dj) {
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
    if (DateTime.now().difference(_ultimoGuardado) > const Duration(seconds: 20)) {
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
    // en pausa la barra queda donde de verdad se paro (la posicion va frenada)
    if (!sonando && estado == EstadoRepro.sonando) {
      final exacta = m.player.state.position;
      if (exacta > Duration.zero) posicion.value = exacta;
    }
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
    // un filtro de sonido que este telefono no tiene: mpv calla el audio.
    // Se quitan los filtros y la misma cancion vuelve a sonar donde iba.
    if (e.toLowerCase().contains('filter') && !_sinFiltros) {
      _sinFiltros = true;
      unawaited(() async {
        for (final x in [_a, _b]) {
          try {
            await x.player.setProperty('af', '');
          } catch (_) {}
        }
        if (pista != null && identical(pista, actual)) {
          await _cargar(pista, inicio: posicion.value, mismo: true,
              pausado: estado == EstadoRepro.pausa, intento: _reintentos);
        }
      }());
      return;
    }
    if (e.toLowerCase().contains('filter')) return;
    if (pista == null || m.fuente!.local) return;
    // YouTube a veces da un enlace que luego no abre: se pide otro, con otro
    // cliente, sin perder el punto. Si tampoco abre, se avisa y se sigue.
    final vid = '${pista['video_id'] ?? ''}';
    // si sonó bien un buen rato desde el último reintento, el contador vuelve a cero
    if (_reintentos > 0 && posicion.value > _reintentoEn + const Duration(seconds: 20)) {
      _reintentos = 0;
    }
    if (vid.isNotEmpty && _reintentos < 3) {
      _reintentos++;
      _reintentoEn = posicion.value;
      streams.olvidar(vid);
      final gen0 = _gen;
      final inicio0 = posicion.value;
      final pausado0 = estado == EstadoRepro.pausa;
      final n = _reintentos;
      _fijarEstado(EstadoRepro.cargando);
      Timer(Duration(milliseconds: 700 * n), () {
        if (gen0 == _gen && identical(pista, actual)) {
          unawaited(_cargar(pista, inicio: inicio0, mismo: true, forzarStream: true,
              pausado: pausado0, intento: n));
        }
      });
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
    if (Jugador.esWeb || !_midiendo.add(m)) return;
    m.player.getProperty('af-metadata/caudal').then((t) => usar(nivelDeMetadatos(t))).catchError((_) {})
        .whenComplete(() => _midiendo.remove(m));
  }

  /// Pone en un motor el sonido de siempre mas, si se pide, un recorte de graves.
  Future<void> _ponerAf(_Motor m, String graves) async {
    try {
      await m.player.setProperty('af', sumarFiltro(sumarFiltro(cadenaFiltros(), _eq3[m] ?? ''), graves));
    } catch (_) {}
  }

  Future<void> _empezarFundido({double? largo, bool graves = false, PasoMezcla? paso,
      AnalisisRitmo? ritmoSale}) async {
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
    if (f == null) {
      // la siguiente aun no tiene enlace: se pide ya para el proximo intento
      final vid = '${sig['video_id'] ?? ''}';
      if (vid.isNotEmpty && _resolviendoSiguiente != vid) {
        _resolviendoSiguiente = vid;
        streams.resolver(vid, video: false, calidad: ajustes.texto('calidad_audio'), codec: _codecVideo)
            .catchError((_) => Fuente(url: ''));
      }
      return;
    }
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
    final pasoSig = _pasosSet[objetivoPista];
    final ritmoEntra = _ritmoSet['${objetivoPista['clave']}'];
    final inicio = pasoSig != null && paso != null
        ? inicioDeEntrante(pasoSig, dj ? inicioDeMusica(tramos, durSig) : 0.0, ritmoEntra)
        : (dj ? inicioDeMusica(tramos, durSig) : 0.0);
    // el tipo de cambio: en la Mezcla DJ automatica es fundido o cambio de graves
    final tipo = paso?.tipo ?? (graves ? TipoTransicion.graves : TipoTransicion.fundido);
    final usaAf = (tipo == TipoTransicion.graves || tipo == TipoTransicion.filtro) && puedeFiltrar;
    // tempo: la que entra se acerca al tempo de la que sale (hasta 8 %) sin cambiar de tono
    var razon = 1.0;
    if (paso != null && paso.igualarTempo && puedeEstirarTiempo && ritmoSale != null && ritmoEntra != null &&
        ritmoSale.valido && ritmoEntra.valido) {
      razon = razonDeTempo(ritmoSale.bpm, ritmoEntra.bpm);
    }
    final eqEntra = filtroEq3(pasoSig?.eq ?? const [0, 0, 0]);
    _fundido = {'saliente': saliente, 'entrante': entrante, 'inicio': DateTime.now(),
      'dur': largo ?? _crossfade.toDouble(), 'dj': dj,
      'saltos': pasoSig?.entrada != null ? 8 : 0,
      'tipo': tipo, 'curva': paso?.curva ?? CurvaFader.suave, 'usaAf': usaAf, 'razon': razon,
      'nivS': 0, 'nivE': dbGravesCortados};
    _silencioEntrada.reiniciar();
    _silencioFinal.reiniciar();
    // la que entra empieza ya recortada (sin graves o sin agudos) y con su ecualizador
    _eq3[entrante] = eqEntra;
    if (usaAf) {
      await _ponerAf(entrante, tipo == TipoTransicion.graves
          ? filtroGraves(dbGravesCortados)
          : filtroBarrido(dbGravesCortados, agudos: true));
    } else if (eqEntra.isNotEmpty || (_eq3[saliente] ?? '').isNotEmpty) {
      await _ponerAf(entrante, '');
    }
    await entrante.abrir(f, volumen: 0, velocidad: velocidad * razon,
        inicio: Duration(milliseconds: (inicio * 1000).round()), video: modo == 'video');
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
    final avance = min(1.0, t / max(0.2, f['dur'] as double));
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
    final saliente = f['saliente'] as _Motor;
    final curva = f['curva'] as CurvaFader;
    entrante.player.setVolume(_salida * ganancia(curva, avance, entrante: true));
    saliente.player.setVolume(_salida * ganancia(curva, avance, entrante: false));
    if (f['usaAf'] == true && !_sinFiltros) {
      // graves o barrido de filtro: cada motor, en saltos de 6 dB (no a cada fotograma)
      final graves = f['tipo'] == TipoTransicion.graves;
      final nS = graves ? dbGraves(avance, entrante: false) : dbFiltro(avance, entrante: false);
      final nE = graves ? dbGraves(avance, entrante: true) : dbFiltro(avance, entrante: true);
      if (nS != f['nivS']) {
        f['nivS'] = nS;
        _ponerAf(saliente, graves ? filtroGraves(nS) : filtroBarrido(nS, agudos: false));
      }
      if (nE != f['nivE']) {
        f['nivE'] = nE;
        _ponerAf(entrante, graves ? filtroGraves(nE) : filtroBarrido(nE, agudos: true));
      }
    }
    if (avance >= 1) {
      _eq3.remove(saliente);
      _apagar(saliente).whenComplete(() => _ponerAf(saliente, ''));
      _fundido = null;
      _pasosFundido?.cancel();
      _activo.player.setVolume(_salida);
      final razon = f['razon'] as double;
      if (razon != 1) {
        // el tempo vuelve poco a poco al suyo (en 5 pasos), sin salto
        var k = 0;
        Timer.periodic(const Duration(milliseconds: 500), (tm) {
          k++;
          final r = razon + (1 - razon) * min(1.0, k / 5);
          if (_fundido == null) _activo.player.setRate(velocidad * r);
          if (k >= 5) tm.cancel();
        });
      }
      if (_probando) {
        // era una prueba: unos segundos de la que entra y se pausa
        _probando = false;
        Timer(const Duration(seconds: 8), () {
          if (_pasosSet.isNotEmpty && _fundido == null) pausar();
        });
      }
    }
  }

  void _cortarFundido() {
    final f = _fundido;
    if (f == null) return;
    _eq3.remove(f['saliente'] as _Motor);
    _apagar(f['saliente'] as _Motor).whenComplete(() => _ponerAf(f['saliente'] as _Motor, ''));
    _fundido = null;
    _pasosFundido?.cancel();
    if (f['usaAf'] == true) _ponerAf(f['entrante'] as _Motor, '');
    if ((f['razon'] as double) != 1) _activo.player.setRate(velocidad);
    _activo.player.setVolume(_salida);
  }

  // ------------------------------------------------------------ temporizador

  void programarApagado({int? minutos, bool alTerminar = false}) {
    _apagarAlFinal = alTerminar;
    _apagarEn = minutos == null ? null : DateTime.now().add(Duration(minutes: minutos));
    _ponerFactorDormir(1);
    // el reloj del temporizador solo corre mientras hay uno puesto
    if (_apagarEn != null || _apagarAlFinal) {
      _relojApagado ??= Timer.periodic(const Duration(milliseconds: 500), (_) => _ticApagado());
    } else {
      _relojApagado?.cancel();
      _relojApagado = null;
    }
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
    if (_apagarEn == null && !_apagarAlFinal && _factorDormir == 1) {
      _relojApagado?.cancel();
      _relojApagado = null;
      return;
    }
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

  /// Huella de la cola guardada la ultima vez: si no cambio, solo se guarda la
  /// posicion (antes se reescribia la cola entera cada 15 s).
  int? _colaGuardada;

  Future<void> guardarSesion() async {
    _ultimoGuardado = DateTime.now();
    if (actual == null) return;
    final cola = Object.hashAll([
      pos, '${contexto?['tipo']}|${contexto?['id']}', '${actual!['clave']}',
      for (final p in secuencia) '${p['clave']}|${p['_auto'] == true}',
      '|',
      for (final p in proximas) p['clave'],
    ]);
    if (cola == _colaGuardada) {
      await coleccion.guardarEstado('sesion_posicion',
          {'clave': '${actual!['clave']}', 'posicion': posicion.value.inMilliseconds});
      return;
    }
    _colaGuardada = cola;
    Json limpia(Json p) => {for (final e in p.entries) if (!e.key.startsWith('_') || e.key == '_auto') e.key: e.value};
    final ini = max(0, pos - 30);
    await coleccion.guardarEstado('sesion_posicion', null);
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
    var ms = (d['posicion'] as num?)?.toInt() ?? 0;
    // la posicion guardada aparte (cuando la cola no habia cambiado)
    try {
      final suelta = await coleccion.estado('sesion_posicion');
      if (suelta is Map && suelta['clave'] == '${actual!['clave']}' && suelta['posicion'] is num) {
        ms = (suelta['posicion'] as num).toInt();
      }
    } catch (_) {}
    posicion.value = Duration(milliseconds: ms);
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
