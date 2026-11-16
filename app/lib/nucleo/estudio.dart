import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart' show WidgetsBinding, WidgetsBindingObserver, AppLifecycleState;
import 'package:shared_preferences/shared_preferences.dart';

import 'catalogo.dart';
import 'sonidos_ambiente.dart';



// =============================================================== perfiles

/// Una tarea de estudio: qué busca en el catálogo y con qué sonidos arranca.
class PerfilEstudio {
  const PerfilEstudio({
    required this.id,
    required this.nombre,
    required this.descripcion,
    required this.etiquetas,
    required this.consultas,
    required this.mezcla,
  });

  final String id;
  final String nombre;
  final String descripcion;

  /// Palabras sueltas para la tarjeta («Lo-fi», «Piano»...).
  final List<String> etiquetas;
  final List<String> consultas;

  /// Capas que suenan por defecto y a qué volumen (0 a 1).
  final Map<CapaAmbiente, double> mezcla;

  static const leer = PerfilEstudio(
    id: 'leer',
    nombre: 'Leer / Escribir',
    descripcion: 'Sin letra y muy calmado, para que las palabras sean tuyas.',
    etiquetas: ['Lo-fi', 'Ambient', 'Piano'],
    consultas: [
      'lofi piano para estudiar sin letra',
      'ambient música para leer instrumental',
      'peaceful piano study focus',
    ],
    mezcla: {CapaAmbiente.lluvia: 0.35, CapaAmbiente.chimenea: 0.2},
  );

  static const programar = PerfilEstudio(
    id: 'programar',
    nombre: 'Programar / Analizar',
    descripcion: 'Un ritmo parejo que te acompaña sin distraer.',
    etiquetas: ['Electrónica', 'Synthwave suave'],
    consultas: [
      'synthwave instrumental focus coding',
      'electronic instrumental concentración programar',
      'lofi beats instrumental study',
    ],
    mezcla: {CapaAmbiente.cafeteria: 0.3, CapaAmbiente.rosa: 0.12},
  );

  static const repasar = PerfilEstudio(
    id: 'repasar',
    nombre: 'Repasar / Memorizar',
    descripcion: 'Instrumental estable para fijar lo que aprendes.',
    etiquetas: ['Clásica', 'Barroco', 'Ambient'],
    consultas: [
      'baroque classical study music instrumental',
      'ambient música para memorizar sin letra',
      'música clásica para estudiar piano focus',
    ],
    mezcla: {CapaAmbiente.bosque: 0.3, CapaAmbiente.marron: 0.15},
  );

  static const relajar = PerfilEstudio(
    id: 'relajar',
    nombre: 'Relajarme',
    descripcion: 'Un descanso suave para soltar los hombros.',
    etiquetas: ['Calma', 'Naturaleza'],
    consultas: [
      'música relajante instrumental sin letra',
      'ambient relax calm piano',
      'lofi chill relax beats',
    ],
    mezcla: {CapaAmbiente.lluvia: 0.3, CapaAmbiente.bosque: 0.3, CapaAmbiente.chimenea: 0.15},
  );

  static const todos = [leer, programar, repasar, relajar];

  static PerfilEstudio porId(String? id) => todos.firstWhere((p) => p.id == id, orElse: () => leer);
}

/// Un estilo de sonido que reemplaza las búsquedas del perfil mientras esté elegido.
class EstiloEstudio {
  const EstiloEstudio(this.id, this.nombre, this.consulta);
  final String id;
  final String nombre;
  final String consulta;

  static const todos = [
    EstiloEstudio('lofi', 'Lo-fi beats', 'lofi beats to study instrumental'),
    EstiloEstudio('ambient', 'Ambient', 'ambient música para concentrarse sin letra'),
    EstiloEstudio('instrumental', 'Instrumental sin letra', 'instrumental sin letra para estudiar'),
    EstiloEstudio('synthwave', 'Synthwave suave', 'chill synthwave instrumental focus'),
    EstiloEstudio('piano', 'Piano para estudiar', 'piano para estudiar relajante instrumental'),
  ];

  static EstiloEstudio? porId(String? id) {
    for (final e in todos) {
      if (e.id == id) return e;
    }
    return null;
  }
}

// =============================================================== curaduría

/// Filtro heurístico para evitar canciones con voz: puntúa cada título/artista.
class CuraduriaEstudio {
  CuraduriaEstudio._();

  static final _buenas = RegExp(
      r'instrumental|lo-?fi|ambient|piano|study|studying|focus|concentra|sin letra|calm|relax|chill|'
      r'baroque|barroc|synthwave|beats|meditat|sleep|nature|rain|lluvia',
      caseSensitive: false);
  static final _malas = RegExp(
      r'official (music )?video|video oficial|videoclip|\bft\.?(\s|$)|\bfeat\.?(\s|$)|featuring|'
      r'lyrics?|\bletra\b|karaoke|\blive\b|en vivo|\bremix\b|reaction',
      caseSensitive: false);

  /// Más alto = más probable que sea instrumental y calmado.
  static int puntaje(Map<String, dynamic> pista) {
    final texto = '${pista['titulo'] ?? ''} ${pista['artista'] ?? ''}';
    var p = 0;
    p += min(3, _buenas.allMatches(texto).length) * 3;
    p -= min(2, _malas.allMatches(texto).length) * 5;
    if (pista['explicito'] == true) p -= 4;
    final d = pista['duracion'];
    if (d is num && d > 0 && d < 45) p -= 6; // jingles y cuñas
    return p;
  }

  /// Ordena con lo más instrumental primero y quita lo que suena a voz, si hay
  /// suficientes alternativas; si no, se queda con todo para no vaciar la cola.
  static List<Map<String, dynamic>> filtrar(List<Map<String, dynamic>> pistas,
      {int minimoAlternativas = 6}) {
    final vistos = <String>{};
    final unicas = <Map<String, dynamic>>[];
    for (final p in pistas) {
      final id = '${p['video_id'] ?? p['clave'] ?? p['titulo']}';
      if (id.isNotEmpty && vistos.add(id)) unicas.add(p);
    }
    final conPuntaje = [for (final p in unicas) (p, puntaje(p))];
    final buenas = conPuntaje.where((e) => e.$2 > -5).toList();
    final usar = buenas.length >= minimoAlternativas ? buenas : conPuntaje;
    // estable: a igual puntaje se respeta el orden en que llegaron
    final indexado = [for (var i = 0; i < usar.length; i++) (usar[i], i)];
    indexado.sort((a, b) {
      final c = b.$1.$2.compareTo(a.$1.$2);
      return c != 0 ? c : a.$2.compareTo(b.$2);
    });
    return [for (final e in indexado) e.$1.$1];
  }
}

typedef BuscarCatalogo = Future<List<Map<String, dynamic>>> Function(String texto, {String? filtro, int limite});

// =============================================================== ciclos

enum FaseEstudio { inactivo, enfoque, descanso, descansoLargo, fin }

enum AccionFinBloque { bajar, pausar, seguir }

/// La forma de la sesión: bloques de enfoque con descansos.
class CicloEstudio {
  const CicloEstudio({
    required this.enfoque,
    required this.descanso,
    this.rondas = 4,
    this.descansoLargo = Duration.zero,
    this.cadaRondas = 4,
  });

  final Duration enfoque;
  final Duration descanso;
  final int rondas;

  /// Duración del descanso largo (cero = sin descanso largo).
  final Duration descansoLargo;
  final int cadaRondas;

  CicloEstudio copiar({Duration? enfoque, Duration? descanso, int? rondas, Duration? descansoLargo}) =>
      CicloEstudio(
          enfoque: enfoque ?? this.enfoque,
          descanso: descanso ?? this.descanso,
          rondas: rondas ?? this.rondas,
          descansoLargo: descansoLargo ?? this.descansoLargo,
          cadaRondas: cadaRondas);

  static const p25 = (id: '25-5', nombre: '25 / 5', enfoque: 25, descanso: 5);
  static const p50 = (id: '50-10', nombre: '50 / 10', enfoque: 50, descanso: 10);
  static const p90 = (id: '90-15', nombre: '90 / 15', enfoque: 90, descanso: 15);
  static const presets = [p25, p50, p90];

  /// Tiempo total de enfoque de la sesión.
  Duration get totalEnfoque => enfoque * rondas;
}

class EventoFase {
  const EventoFase(this.de, this.a, this.ronda, {this.saltado = false});
  final FaseEstudio de;
  final FaseEstudio a;

  /// La ronda en la que quedó el temporizador (ya la nueva).
  final int ronda;
  final bool saltado;

  /// ¿Acaba un bloque de enfoque? (no si se estaba descansando)
  bool get terminaEnfoque => de == FaseEstudio.enfoque;
}

/// El reloj de la sesión. Cuenta con la hora de fin (no con un contador que se
/// detiene si la pantalla se apaga): al volver, pone al día todo lo que pasó.
class TemporizadorEstudio {
  TemporizadorEstudio({DateTime Function()? reloj, this.alEstudiar}) : _reloj = reloj ?? DateTime.now;

  final DateTime Function() _reloj;

  /// Se avisa de cada tramo de enfoque que pasa (desde cuándo y cuánto).
  final void Function(DateTime inicio, Duration duracion)? alEstudiar;

  CicloEstudio? ciclo;
  FaseEstudio fase = FaseEstudio.inactivo;
  int ronda = 0;
  bool pausado = false;
  DateTime? _fin;
  Duration _restantePausa = Duration.zero;
  Duration _duracionFase = Duration.zero;
  DateTime? _creditoDesde;

  bool get enMarcha =>
      fase == FaseEstudio.enfoque || fase == FaseEstudio.descanso || fase == FaseEstudio.descansoLargo;

  Duration get duracionFase => _duracionFase;

  Duration get restante {
    if (!enMarcha) return Duration.zero;
    if (pausado) return _restantePausa;
    final r = _fin!.difference(_reloj());
    return r.isNegative ? Duration.zero : r;
  }

  /// De 0 a 1: cuánto de la fase ya pasó.
  double get progreso {
    if (!enMarcha || _duracionFase.inMilliseconds == 0) return fase == FaseEstudio.fin ? 1 : 0;
    return (1 - restante.inMilliseconds / _duracionFase.inMilliseconds).clamp(0.0, 1.0);
  }

  Duration _duracion(FaseEstudio f) => switch (f) {
        FaseEstudio.enfoque => ciclo!.enfoque,
        FaseEstudio.descanso => ciclo!.descanso,
        FaseEstudio.descansoLargo => ciclo!.descansoLargo,
        _ => Duration.zero,
      };

  void iniciar(CicloEstudio c) {
    ciclo = c;
    ronda = 1;
    _entrar(FaseEstudio.enfoque, _reloj());
  }

  void _entrar(FaseEstudio f, DateTime desde) {
    fase = f;
    _duracionFase = _duracion(f);
    _fin = desde.add(_duracionFase);
    _creditoDesde = f == FaseEstudio.enfoque ? desde : null;
    pausado = false;
  }

  void _acreditar(DateTime hasta) {
    final d = _creditoDesde;
    if (fase != FaseEstudio.enfoque || d == null || !hasta.isAfter(d)) return;
    alEstudiar?.call(d, hasta.difference(d));
    _creditoDesde = hasta;
  }

  /// Lo que sigue a la fase actual: (fase, ronda).
  (FaseEstudio, int) _siguiente() {
    final c = ciclo!;
    if (fase == FaseEstudio.enfoque) {
      if (ronda >= c.rondas) return (FaseEstudio.fin, ronda);
      final largo = c.descansoLargo > Duration.zero && ronda % c.cadaRondas == 0;
      return (largo ? FaseEstudio.descansoLargo : FaseEstudio.descanso, ronda);
    }
    return (FaseEstudio.enfoque, ronda + 1);
  }

  /// Pone al día el reloj; devuelve los cambios de fase que hubo (puede ser
  /// más de uno si la pantalla estuvo apagada un buen rato).
  List<EventoFase> tic() {
    final eventos = <EventoFase>[];
    if (!enMarcha || pausado) return eventos;
    final ahora = _reloj();
    while (enMarcha && !ahora.isBefore(_fin!)) {
      final limite = _fin!;
      _acreditar(limite);
      final de = fase;
      final (sig, r) = _siguiente();
      if (sig == FaseEstudio.fin) {
        fase = FaseEstudio.fin;
        _fin = null;
        _creditoDesde = null;
        eventos.add(EventoFase(de, sig, r));
        break;
      }
      ronda = r;
      _entrar(sig, limite);
      eventos.add(EventoFase(de, sig, r));
    }
    if (enMarcha) _acreditar(ahora);
    return eventos;
  }

  void pausar() {
    if (!enMarcha || pausado) return;
    tic();
    if (!enMarcha) return;
    final ahora = _reloj();
    _acreditar(ahora);
    _restantePausa = _fin!.difference(ahora);
    if (_restantePausa.isNegative) _restantePausa = Duration.zero;
    pausado = true;
  }

  void reanudar() {
    if (!enMarcha || !pausado) return;
    final ahora = _reloj();
    _fin = ahora.add(_restantePausa);
    _creditoDesde = fase == FaseEstudio.enfoque ? ahora : null;
    pausado = false;
  }

  /// Pasa ya a la fase siguiente.
  List<EventoFase> saltar() {
    if (!enMarcha) return const [];
    final ahora = _reloj();
    if (pausado) {
      pausado = false;
      _creditoDesde = fase == FaseEstudio.enfoque ? ahora : null;
    }
    _acreditar(ahora);
    _fin = ahora;
    return [for (final e in tic()) EventoFase(e.de, e.a, e.ronda, saltado: true)];
  }

  void detener() {
    if (enMarcha && !pausado) _acreditar(_reloj());
    fase = FaseEstudio.inactivo;
    ronda = 0;
    pausado = false;
    _fin = null;
    _creditoDesde = null;
  }
}

/// Qué le pasa a la música base en cada fase.
class ReglaMusica {
  const ReglaMusica(this.factor, this.pausar);

  /// Fracción del volumen que se conserva (1 = igual que siempre).
  final double factor;
  final bool pausar;

  /// Cuánto se baja la música base: un 35 %.
  static const bajada = 0.65;

  static ReglaMusica para(FaseEstudio fase, AccionFinBloque accion, bool atenuar) {
    switch (fase) {
      case FaseEstudio.enfoque:
        return ReglaMusica(atenuar ? bajada : 1, false);
      case FaseEstudio.descanso:
      case FaseEstudio.descansoLargo:
        return switch (accion) {
          AccionFinBloque.bajar => const ReglaMusica(0.35, false),
          AccionFinBloque.pausar => const ReglaMusica(1, true),
          AccionFinBloque.seguir => const ReglaMusica(1, false),
        };
      default:
        return const ReglaMusica(1, false);
    }
  }
}

// =============================================================== constancia

/// Tiempo estudiado por día y racha. Sin metas ni regaños.
class EstadisticasEstudio {
  EstadisticasEstudio([Map<String, int>? msPorDia]) : msPorDia = msPorDia ?? {};

  /// Milisegundos de enfoque por día local («2026-11-16»).
  final Map<String, int> msPorDia;

  /// Un día cuenta para la racha desde un minuto de enfoque.
  static const minimoDiaMs = 60 * 1000;

  static String clave(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  /// Suma un tramo; si cruza la medianoche se reparte entre los dos días.
  void sumar(DateTime inicio, Duration duracion) {
    var cursor = inicio;
    var resto = duracion.inMilliseconds;
    while (resto > 0) {
      final medianoche = DateTime(cursor.year, cursor.month, cursor.day + 1);
      final hastaMedianoche = medianoche.difference(cursor).inMilliseconds;
      final trozo = min(resto, max(1, hastaMedianoche));
      final k = clave(cursor);
      msPorDia[k] = (msPorDia[k] ?? 0) + trozo;
      resto -= trozo;
      cursor = cursor.add(Duration(milliseconds: trozo));
    }
  }

  Duration deDia(DateTime d) => Duration(milliseconds: msPorDia[clave(d)] ?? 0);

  Duration hoy(DateTime ahora) => deDia(ahora);

  /// Desde el lunes de esta semana hasta hoy.
  Duration semana(DateTime ahora) {
    var total = 0;
    for (var i = 0; i < ahora.weekday; i++) {
      total += deDia(DateTime(ahora.year, ahora.month, ahora.day - i)).inMilliseconds;
    }
    return Duration(milliseconds: total);
  }

  bool _cuenta(DateTime d) => (msPorDia[clave(d)] ?? 0) >= minimoDiaMs;

  /// Días seguidos con estudio. Si hoy aún no empiezas, la racha de ayer sigue viva.
  int racha(DateTime ahora) {
    var d = DateTime(ahora.year, ahora.month, ahora.day);
    if (!_cuenta(d)) d = DateTime(d.year, d.month, d.day - 1);
    var n = 0;
    while (_cuenta(d)) {
      n++;
      d = DateTime(d.year, d.month, d.day - 1);
    }
    return n;
  }

  /// Quita lo muy viejo para que no crezca sin fin.
  void podar(DateTime ahora, {int dias = 400}) {
    final corte = clave(DateTime(ahora.year, ahora.month, ahora.day - dias));
    msPorDia.removeWhere((k, _) => k.compareTo(corte) < 0);
  }

  String toJson() => jsonEncode(msPorDia);

  static EstadisticasEstudio desdeJson(String? texto) {
    try {
      final m = jsonDecode(texto ?? '{}') as Map;
      return EstadisticasEstudio({for (final e in m.entries) '${e.key}': (e.value as num).toInt()});
    } catch (_) {
      return EstadisticasEstudio();
    }
  }

  /// «1 h 25 min», «40 min», «Menos de un minuto».
  static String texto(Duration d) {
    final m = d.inMinutes;
    if (m < 1) return d.inSeconds < 1 ? '0 min' : 'Menos de 1 min';
    if (m < 60) return '$m min';
    final h = m ~/ 60, r = m % 60;
    return r == 0 ? '$h h' : '$h h $r min';
  }

  /// Una frase amable sobre cómo va el día. Nunca un reproche.
  String frase(DateTime ahora) {
    final h = hoy(ahora);
    final r = racha(ahora);
    if (h.inMinutes >= 1) {
      if (r >= 3) return '$r días seguidos. Qué bonito hábito.';
      if (r == 2) return 'Dos días seguidos. Así, sin prisa.';
      return 'Hoy ya sumaste ${texto(h)}. Buen ritmo.';
    }
    if (r >= 1) return 'Llevas $r ${r == 1 ? 'día' : 'días'} de racha. Cuando quieras, seguimos.';
    return 'Un buen momento para empezar es ahora. Sin presión.';
  }
}

// =============================================================== notas

class NotaEstudio {
  const NotaEstudio(this.id, this.texto, this.fecha);
  final int id;
  final String texto;
  final DateTime fecha;

  Map<String, dynamic> toJson() => {'id': id, 'texto': texto, 'fecha': fecha.toIso8601String()};

  static NotaEstudio? desdeJson(Object? o) {
    if (o is! Map) return null;
    final f = DateTime.tryParse('${o['fecha']}');
    final t = '${o['texto'] ?? ''}';
    final id = o['id'];
    if (f == null || t.isEmpty || id is! num) return null;
    return NotaEstudio(id.toInt(), t, f);
  }
}

/// «Captura de ideas»: notas cortas con fecha, la más nueva arriba.
class NotasEstudio {
  NotasEstudio([List<NotaEstudio>? lista]) : lista = lista ?? [];

  final List<NotaEstudio> lista;
  static const maximo = 300;

  NotaEstudio? agregar(String texto, DateTime ahora) {
    final t = texto.trim();
    if (t.isEmpty) return null;
    var id = ahora.microsecondsSinceEpoch;
    while (lista.any((n) => n.id == id)) {
      id++;
    }
    final n = NotaEstudio(id, t, ahora);
    lista.insert(0, n);
    if (lista.length > maximo) lista.removeRange(maximo, lista.length);
    return n;
  }

  bool borrar(int id) {
    final n = lista.length;
    lista.removeWhere((e) => e.id == id);
    return lista.length != n;
  }

  String toJson() => jsonEncode([for (final n in lista) n.toJson()]);

  static NotasEstudio desdeJson(String? texto) {
    try {
      final l = jsonDecode(texto ?? '[]') as List;
      return NotasEstudio([for (final o in l) ?NotaEstudio.desdeJson(o)]);
    } catch (_) {
      return NotasEstudio();
    }
  }

  /// «Hoy, 14:05» o «12/11, 09:30».
  static String fechaCorta(DateTime f, DateTime ahora) {
    String dos(int n) => n.toString().padLeft(2, '0');
    final hora = '${dos(f.hour)}:${dos(f.minute)}';
    final hoy = DateTime(ahora.year, ahora.month, ahora.day);
    final dia = DateTime(f.year, f.month, f.day);
    final dif = hoy.difference(dia).inDays;
    if (dif == 0) return 'Hoy, $hora';
    if (dif == 1) return 'Ayer, $hora';
    return '${dos(f.day)}/${dos(f.month)}, $hora';
  }
}

// =============================================================== la música

/// Lo que el modo estudio necesita del reproductor (así se prueba sin motores).
abstract class ControlMusica {
  bool get sonando;
  bool get hayMusica;
  String get titulo;

  /// De 0 a 100.
  double get volumen;
  Listenable get cambios;
  Future<void> fijarVolumen(double v);

  /// Fracción del volumen que se conserva (la bajada del modo estudio).
  Future<void> fijarFactor(double f);
  Future<void> pausar();
  Future<void> reanudar();
  Future<void> alternar();
  Future<void> siguiente();
  Future<void> iniciarCola(List<Map<String, dynamic>> pistas, String titulo);

  /// Sale del modo estudio (la música puede seguir sonando).
  Future<void> salir();
}

// =============================================================== el modo estudio

class Estudio extends ChangeNotifier with WidgetsBindingObserver {
  Estudio({
    DateTime Function()? reloj,
    BuscarCatalogo? buscar,
    SonidosAmbiente? ambiente,
    bool? ocultarAmbiente,
  })  : _reloj = reloj ?? DateTime.now,
        _buscar = buscar ?? _buscarDelCatalogo,
        ambiente = ambiente ?? SonidosAmbiente() {
    temporizador = TemporizadorEstudio(reloj: _reloj, alEstudiar: _alEstudiar);
  }

  static Estudio? _i;

  /// El de la app (uno solo, para que la sesión sobreviva a las pantallas).
  static Estudio get i => _i ??= Estudio();

  static Future<List<Map<String, dynamic>>> _buscarDelCatalogo(String t, {String? filtro, int limite = 20}) =>
      Catalogo.buscar(t, filtro: filtro, limite: limite);

  final DateTime Function() _reloj;
  final BuscarCatalogo _buscar;
  final SonidosAmbiente ambiente;
  late final TemporizadorEstudio temporizador;

  ControlMusica? musica;
  bool cargado = false;
  Future<void>? _cargando;

  // lo elegido (se guarda)
  String perfilId = PerfilEstudio.leer.id;
  String? estiloId;
  String cicloId = '25-5';
  int enfoqueMin = 25;
  int descansoMin = 5;
  int rondas = 4;
  int descansoLargoMin = 0;
  AccionFinBloque accion = AccionFinBloque.bajar;
  bool atenuar = false;
  bool candado = false;
  bool calido = true;
  double brillo = 0.6;
  bool pantallaEncendida = true;
  final Map<CapaAmbiente, bool> capaActiva = {for (final c in CapaAmbiente.values) c: false};
  final Map<CapaAmbiente, double> capaVolumen = {for (final c in CapaAmbiente.values) c: 0.3};
  EstadisticasEstudio estadisticas = EstadisticasEstudio();
  NotasEstudio notas = NotasEstudio();

  // la sesión
  bool sesionActiva = false;
  bool cargandoCola = false;
  String? errorCola;

  /// Aviso visual calmado (fin de bloque, vuelta al enfoque...). Se apaga solo.
  String? aviso;
  Timer? _relojSesion;
  Timer? _apagaAviso;
  Timer? _guardaDias;
  bool _pausadaPorMi = false;
  bool _observando = false;
  int _gen = 0;

  PerfilEstudio get perfil => PerfilEstudio.porId(perfilId);
  EstiloEstudio? get estilo => EstiloEstudio.porId(estiloId);
  DateTime get ahora => _reloj();

  CicloEstudio get ciclo => CicloEstudio(
        enfoque: Duration(minutes: enfoqueMin),
        descanso: Duration(minutes: descansoMin),
        rondas: rondas,
        descansoLargo: Duration(minutes: descansoLargoMin),
      );

  /// ¿Hay un bloque (de enfoque o descanso) a medias? Salir pide confirmación.
  bool get hayBloqueEnCurso => sesionActiva && temporizador.enMarcha;

  // ------------------------------------------------------------ guardar y cargar

  static const _p = 'estudio.';

  Future<void> cargar() => _cargando ??= _cargar();

  Future<void> _cargar() async {
    try {
      final p = await SharedPreferences.getInstance();
      perfilId = PerfilEstudio.porId(p.getString('${_p}perfil')).id;
      estiloId = EstiloEstudio.porId(p.getString('${_p}estilo'))?.id;
      cicloId = p.getString('${_p}ciclo') ?? cicloId;
      enfoqueMin = (p.getInt('${_p}enf') ?? enfoqueMin).clamp(1, 240);
      descansoMin = (p.getInt('${_p}desc') ?? descansoMin).clamp(1, 60);
      rondas = (p.getInt('${_p}rondas') ?? rondas).clamp(1, 12);
      descansoLargoMin = (p.getInt('${_p}largo') ?? descansoLargoMin).clamp(0, 60);
      accion = AccionFinBloque.values.firstWhere((a) => a.name == p.getString('${_p}accion'),
          orElse: () => accion);
      atenuar = p.getBool('${_p}atenuar') ?? atenuar;
      candado = p.getBool('${_p}candado') ?? candado;
      calido = p.getBool('${_p}calido') ?? calido;
      brillo = (p.getDouble('${_p}brillo') ?? brillo).clamp(0.0, 1.0);
      pantallaEncendida = p.getBool('${_p}pantalla') ?? pantallaEncendida;
      final capas = p.getString('${_p}capas');
      if (capas != null) {
        try {
          final m = jsonDecode(capas) as Map;
          for (final c in CapaAmbiente.values) {
            final v = m[c.name];
            if (v is List && v.length == 2) {
              capaActiva[c] = v[0] == true;
              capaVolumen[c] = ((v[1] as num?)?.toDouble() ?? 0.3).clamp(0.0, 1.0);
            }
          }
        } catch (_) {}
      } else {
        _aplicarMezclaSinGuardar(perfil);
      }
      estadisticas = EstadisticasEstudio.desdeJson(p.getString('${_p}dias'));
      notas = NotasEstudio.desdeJson(p.getString('${_p}notas'));
    } catch (e) {
      debugPrint('estudio: no se pudo leer lo guardado: $e');
    }
    cargado = true;
    notifyListeners();
  }

  Future<void> _guardar(Map<String, Object?> datos) async {
    try {
      final p = await SharedPreferences.getInstance();
      for (final e in datos.entries) {
        final v = e.value;
        if (v == null) {
          await p.remove('$_p${e.key}');
        } else if (v is String) {
          await p.setString('$_p${e.key}', v);
        } else if (v is bool) {
          await p.setBool('$_p${e.key}', v);
        } else if (v is int) {
          await p.setInt('$_p${e.key}', v);
        } else if (v is double) {
          await p.setDouble('$_p${e.key}', v);
        }
      }
    } catch (_) {}
  }

  String _capasJson() => jsonEncode({
        for (final c in CapaAmbiente.values) c.name: [capaActiva[c] ?? false, capaVolumen[c] ?? 0.3]
      });

  Future<void> _guardarDias() async {
    estadisticas.podar(_reloj());
    await _guardar({'dias': estadisticas.toJson()});
  }

  Future<void> _guardarNotas() => _guardar({'notas': notas.toJson()});

  // ------------------------------------------------------------ lo que se elige

  void elegirPerfil(String id, {bool conMezcla = true}) {
    if (perfilId == id) return;
    perfilId = PerfilEstudio.porId(id).id;
    if (conMezcla) _aplicarMezclaSinGuardar(perfil);
    _guardar({'perfil': perfilId, 'capas': _capasJson()});
    notifyListeners();
    _refrescarCapas();
  }

  void elegirEstilo(String? id) {
    estiloId = EstiloEstudio.porId(id)?.id;
    _guardar({'estilo': estiloId});
    notifyListeners();
  }

  void elegirCiclo(String id) {
    cicloId = id;
    for (final p in CicloEstudio.presets) {
      if (p.id == id) {
        enfoqueMin = p.enfoque;
        descansoMin = p.descanso;
      }
    }
    _guardar({'ciclo': cicloId, 'enf': enfoqueMin, 'desc': descansoMin});
    notifyListeners();
  }

  void ajustarCiclo({int? enfoque, int? descanso, int? rondasNuevas, int? largo}) {
    if (enfoque != null) enfoqueMin = enfoque.clamp(1, 240);
    if (descanso != null) descansoMin = descanso.clamp(1, 60);
    if (rondasNuevas != null) rondas = rondasNuevas.clamp(1, 12);
    if (largo != null) descansoLargoMin = largo.clamp(0, 60);
    // tocar la duración de un bloque lo vuelve personalizado
    if (enfoque != null || descanso != null) cicloId = 'custom';
    _guardar({'ciclo': cicloId, 'enf': enfoqueMin, 'desc': descansoMin, 'rondas': rondas, 'largo': descansoLargoMin});
    notifyListeners();
  }

  /// «A mi manera»: muestra y deja editar la duración de enfoque y descanso.
  void ponerCicloPersonalizado() {
    cicloId = 'custom';
    _guardar({'ciclo': cicloId});
    notifyListeners();
  }

  void ponerAccion(AccionFinBloque a) {
    accion = a;
    _guardar({'accion': a.name});
    notifyListeners();
    if (sesionActiva) _aplicarMusica(temporizador.fase);
  }

  void ponerAtenuar(bool v) {
    atenuar = v;
    _guardar({'atenuar': v});
    notifyListeners();
    if (sesionActiva) _aplicarMusica(temporizador.fase);
  }

  void ponerCandado(bool v) {
    candado = v;
    _guardar({'candado': v});
    notifyListeners();
  }

  void ponerCalido(bool v) {
    calido = v;
    _guardar({'calido': v});
    notifyListeners();
  }

  void ponerBrillo(double v) {
    brillo = v.clamp(0.0, 1.0);
    _guardar({'brillo': brillo});
    notifyListeners();
  }

  void ponerPantallaEncendida(bool v) {
    pantallaEncendida = v;
    _guardar({'pantalla': v});
    notifyListeners();
  }

  // ------------------------------------------------------------ la mezcla

  void _aplicarMezclaSinGuardar(PerfilEstudio p) {
    for (final c in CapaAmbiente.values) {
      capaActiva[c] = p.mezcla.containsKey(c);
      if (p.mezcla.containsKey(c)) capaVolumen[c] = p.mezcla[c]!;
    }
  }

  /// La mezcla de sonidos que trae el perfil.
  void aplicarMezclaDelPerfil() {
    _aplicarMezclaSinGuardar(perfil);
    _guardar({'capas': _capasJson()});
    notifyListeners();
    _refrescarCapas();
  }

  void silenciarCapas() {
    for (final c in CapaAmbiente.values) {
      capaActiva[c] = false;
    }
    _guardar({'capas': _capasJson()});
    notifyListeners();
    _refrescarCapas();
  }

  void ponerCapa(CapaAmbiente c, bool activa) {
    capaActiva[c] = activa;
    _guardar({'capas': _capasJson()});
    notifyListeners();
    if (sesionActiva) {
      if (activa) {
        ambiente.encender(c, capaVolumen[c] ?? 0.3);
      } else {
        ambiente.apagar(c);
      }
    }
  }

  void ponerVolumenCapa(CapaAmbiente c, double v) {
    capaVolumen[c] = v.clamp(0.0, 1.0);
    _guardarCapasLento();
    notifyListeners();
    if (sesionActiva) ambiente.fijarVolumen(c, capaVolumen[c]!);
  }

  Timer? _lentoCapas;
  void _guardarCapasLento() {
    _lentoCapas?.cancel();
    _lentoCapas = Timer(const Duration(milliseconds: 400), () => _guardar({'capas': _capasJson()}));
  }

  Future<void> ponerVolumenBase(double v) async {
    await musica?.fijarVolumen(v.clamp(0, 100));
    notifyListeners();
  }

  void _refrescarCapas() {
    if (!sesionActiva) return;
    for (final c in CapaAmbiente.values) {
      if (capaActiva[c] == true) {
        ambiente.encender(c, capaVolumen[c] ?? 0.3);
      } else {
        ambiente.apagar(c);
      }
    }
  }

  // ------------------------------------------------------------ la cola del perfil

  /// Las canciones del perfil (o del estilo elegido): busca, quita lo que suena
  /// a voz y deja un orden estable para que no haya saltos de estilo.
  Future<List<Map<String, dynamic>>> construirCola() async {
    final consultas = estilo != null ? [estilo!.consulta, ...perfil.consultas.take(1)] : perfil.consultas;
    final todas = <Map<String, dynamic>>[];
    final resultados = await Future.wait(consultas.map((q) async {
      try {
        return await _buscar(q, filtro: 'canciones', limite: 20);
      } catch (_) {
        return <Map<String, dynamic>>[];
      }
    }));
    // una de cada consulta por turnos, para que ningún estilo domine
    final mayor = resultados.fold<int>(0, (m, l) => max(m, l.length));
    for (var i = 0; i < mayor; i++) {
      for (final l in resultados) {
        if (i >= l.length) continue;
        final tipo = l[i]['tipo'];
        if (tipo == null || tipo == 'pista') todas.add(l[i]);
      }
    }
    final filtradas = CuraduriaEstudio.filtrar(todas);
    // misma tanda del día: a igual puntaje, el mismo orden toda la sesión
    return filtradas.take(40).toList();
  }

  // ------------------------------------------------------------ la sesión

  void conectarMusica(ControlMusica? m) {
    musica = m;
  }

  /// Empieza la sesión: música del perfil, sonidos ambientales y temporizador.
  Future<void> iniciar() async {
    if (!cargado) await cargar();
    if (sesionActiva) return;
    final gen = ++_gen;
    sesionActiva = true;
    errorCola = null;
    aviso = null;
    _pausadaPorMi = false;
    temporizador.iniciar(ciclo);
    _guardar({'perfil': perfilId});
    _arrancarReloj();
    _refrescarCapas();
    notifyListeners();
    final m = musica;
    if (m != null) {
      cargandoCola = true;
      notifyListeners();
      try {
        final cola = await construirCola();
        if (gen != _gen) return;
        if (cola.isEmpty) {
          errorCola = 'No encontré música ahora mismo. Revisa tu conexión; los sonidos y el temporizador siguen.';
        } else {
          await m.iniciarCola(cola, 'Estudio · ${estilo?.nombre ?? perfil.nombre}');
          await _aplicarMusica(temporizador.fase);
        }
      } catch (e) {
        errorCola = 'No se pudo preparar la música. El temporizador y los sonidos siguen.';
      } finally {
        if (gen == _gen) {
          cargandoCola = false;
          notifyListeners();
        }
      }
    }
  }

  void _arrancarReloj() {
    _relojSesion?.cancel();
    _relojSesion = Timer.periodic(const Duration(seconds: 1), (_) => tic());
    if (!_observando) {
      try {
        WidgetsBinding.instance.addObserver(this);
        _observando = true;
      } catch (_) {}
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) tic();
  }

  /// Pone al día el temporizador y reacciona a lo que haya pasado.
  void tic() {
    if (!sesionActiva) return;
    final eventos = temporizador.tic();
    for (final e in eventos) {
      _alCambiarFase(e);
    }
    _guardarDiasLento();
    notifyListeners();
  }

  void _alEstudiar(DateTime inicio, Duration d) {
    estadisticas.sumar(inicio, d);
  }

  void _guardarDiasLento() {
    if (_guardaDias?.isActive ?? false) return;
    _guardaDias = Timer(const Duration(seconds: 20), _guardarDias);
  }

  void _alCambiarFase(EventoFase e) {
    if (e.a == FaseEstudio.fin) {
      _mostrarAviso('Terminaste tu sesión. Qué buen trabajo; date un respiro.');
      ambiente.campana(alTerminarBloque: true);
      _guardarDias();
      // la sesión acabó: la música se pausa con calma
      _aplicarMusica(FaseEstudio.fin, pausarTodo: true);
      return;
    }
    if (e.terminaEnfoque) {
      _mostrarAviso(e.a == FaseEstudio.descansoLargo
          ? 'Bloque terminado. Te toca un descanso largo: estírate y toma agua.'
          : 'Bloque terminado. Respira y estírate un momento.');
      if (!e.saltado) ambiente.campana(alTerminarBloque: true);
      _guardarDias();
    } else {
      _mostrarAviso('De vuelta al enfoque. Sin prisa.');
      if (!e.saltado) ambiente.campana(alTerminarBloque: false);
    }
    _aplicarMusica(e.a);
  }

  void _mostrarAviso(String texto) {
    aviso = texto;
    _apagaAviso?.cancel();
    _apagaAviso = Timer(const Duration(seconds: 9), () {
      aviso = null;
      notifyListeners();
    });
  }

  void cerrarAviso() {
    aviso = null;
    _apagaAviso?.cancel();
    notifyListeners();
  }

  Future<void> _aplicarMusica(FaseEstudio fase, {bool pausarTodo = false}) async {
    final m = musica;
    if (m == null) return;
    final regla = pausarTodo ? const ReglaMusica(1, true) : ReglaMusica.para(fase, accion, atenuar);
    try {
      await m.fijarFactor(regla.factor);
      if (regla.pausar) {
        if (m.sonando) {
          await m.pausar();
          _pausadaPorMi = true;
        }
      } else if (_pausadaPorMi) {
        _pausadaPorMi = false;
        if (!m.sonando) await m.reanudar();
      }
    } catch (_) {}
  }

  /// Pausa o reanuda el temporizador.
  void alternarTemporizador() {
    if (!sesionActiva) return;
    if (temporizador.pausado) {
      temporizador.reanudar();
    } else {
      temporizador.pausar();
    }
    notifyListeners();
  }

  void saltarBloque() {
    if (!sesionActiva) return;
    for (final e in temporizador.saltar()) {
      _alCambiarFase(e);
    }
    notifyListeners();
  }

  /// Termina la sesión (lo hace quien pulsa «Salir» o «Terminar»).
  Future<void> terminar() async {
    _gen++;
    _relojSesion?.cancel();
    _apagaAviso?.cancel();
    temporizador.detener();
    final estabaActiva = sesionActiva;
    sesionActiva = false;
    cargandoCola = false;
    aviso = null;
    if (_observando) {
      try {
        WidgetsBinding.instance.removeObserver(this);
      } catch (_) {}
      _observando = false;
    }
    notifyListeners();
    if (!estabaActiva) return;
    _guardaDias?.cancel();
    await _guardarDias();
    await ambiente.detenerTodo();
    final m = musica;
    if (m != null) {
      try {
        await m.salir();
      } catch (_) {}
    }
  }

  // ------------------------------------------------------------ notas

  Future<NotaEstudio?> guardarNota(String texto) async {
    final n = notas.agregar(texto, _reloj());
    if (n != null) {
      notifyListeners();
      await _guardarNotas();
    }
    return n;
  }

  Future<void> borrarNota(int id) async {
    if (notas.borrar(id)) {
      notifyListeners();
      await _guardarNotas();
    }
  }

  @override
  void dispose() {
    _relojSesion?.cancel();
    _apagaAviso?.cancel();
    _guardaDias?.cancel();
    _lentoCapas?.cancel();
    if (_observando) {
      try {
        WidgetsBinding.instance.removeObserver(this);
      } catch (_) {}
    }
    super.dispose();
  }
}
