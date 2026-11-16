// Modo estudio: temporizador (con reloj simulado), constancia y racha, notas,
// curaduría, síntesis de sonidos ambientales y pantallas a todos los tamaños.
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:caudal/nucleo/estudio.dart';
import 'package:caudal/nucleo/sonidos_ambiente.dart';
import 'package:caudal/nucleo/streams.dart' show Fuente;
import 'package:caudal/reproduccion/jugador.dart';
import 'package:caudal/ui/paginas/estudio_comunes.dart';
import 'package:caudal/ui/paginas/estudio_enfoque.dart';
import 'package:caudal/ui/paginas/estudio_pagina.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

// ---------------------------------------------------------------- falsos

class _Reloj {
  _Reloj([DateTime? t]) : ahora = t ?? DateTime(2026, 11, 16, 9, 0);
  DateTime ahora;
  DateTime call() => ahora;
  void avanzar(Duration d) => ahora = ahora.add(d);
}

class _Musica implements ControlMusica {
  bool _sonando = false;
  bool _hay = false;
  double _vol = 100;
  double factor = 1;
  String _titulo = '';
  final List<String> bitacora = [];
  List<Map<String, dynamic>> cola = [];
  final _cambios = ChangeNotifier();

  @override
  bool get sonando => _sonando;
  @override
  bool get hayMusica => _hay;
  @override
  String get titulo => _titulo;
  @override
  double get volumen => _vol;
  @override
  Listenable get cambios => _cambios;
  @override
  Future<void> fijarVolumen(double v) async => _vol = v;
  @override
  Future<void> fijarFactor(double f) async {
    factor = f;
    bitacora.add('factor ${f.toStringAsFixed(2)}');
  }

  @override
  Future<void> pausar() async {
    _sonando = false;
    bitacora.add('pausar');
  }

  @override
  Future<void> reanudar() async {
    _sonando = true;
    bitacora.add('reanudar');
  }

  @override
  Future<void> alternar() async => _sonando ? pausar() : reanudar();
  @override
  Future<void> siguiente() async => bitacora.add('siguiente');
  @override
  Future<void> iniciarCola(List<Map<String, dynamic>> pistas, String titulo) async {
    cola = pistas;
    _hay = true;
    _sonando = true;
    _titulo = '${pistas.first['titulo']}';
    bitacora.add('cola ${pistas.length}');
  }

  @override
  Future<void> salir() async {
    bitacora.add('salir');
    factor = 1;
  }
}

class _FakeJugador implements Jugador {
  final List<String> llamadas = [];
  double volumen = -1;
  bool cerrado = false;

  @override
  Future<void> setProperty(String clave, String valor) async => llamadas.add('prop $clave=$valor');
  @override
  Future<void> setVolume(double v) async {
    volumen = v;
    llamadas.add('vol ${v.toStringAsFixed(0)}');
  }

  @override
  Future<void> open(Fuente f, {Duration? inicio, bool play = true}) async => llamadas.add('open ${f.url}');
  @override
  Future<void> stop() async => llamadas.add('stop');
  @override
  Future<void> dispose() async {
    cerrado = true;
    llamadas.add('dispose');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError('${invocation.memberName}');
}

Map<String, dynamic> _pista(String id, String titulo, [String artista = 'Alguien']) =>
    {'tipo': 'pista', 'video_id': id, 'clave': 'yt:$id', 'titulo': titulo, 'artista': artista, 'duracion': 200};

Estudio _estudio(_Reloj r, {bool ambiente = false, BuscarCatalogo? buscar}) => Estudio(
      reloj: r.call,
      ambiente: SonidosAmbiente(
          disponible: ambiente,
          fabrica: () => _FakeJugador(),
          // en las pruebas de pantallas no se fabrican WAV (necesitan otro hilo real)
          carpeta: () async => throw StateError('sin carpeta en la prueba')),
      buscar: buscar ?? (t, {filtro, limite = 20}) async => [_pista('a$t'.hashCode.toString(), 'Piano $t')],
    );

// ---------------------------------------------------------------- FFT para el espectro

/// Potencia media por frecuencia (FFT de Welch, ventana de Hann).
List<double> _potencia(List<double> x, int n) {
  final segs = x.length ~/ n;
  final p = List<double>.filled(n ~/ 2, 0);
  for (var s = 0; s < segs; s++) {
    final re = List<double>.generate(n, (i) => x[s * n + i] * (0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1))));
    final im = List<double>.filled(n, 0);
    _fft(re, im);
    for (var k = 0; k < n ~/ 2; k++) {
      p[k] += (re[k] * re[k] + im[k] * im[k]) / segs;
    }
  }
  return p;
}

void _fft(List<double> re, List<double> im) {
  final n = re.length;
  for (var i = 1, j = 0; i < n; i++) {
    var bit = n >> 1;
    for (; j & bit != 0; bit >>= 1) {
      j ^= bit;
    }
    j ^= bit;
    if (i < j) {
      final a = re[i];
      re[i] = re[j];
      re[j] = a;
      final b = im[i];
      im[i] = im[j];
      im[j] = b;
    }
  }
  for (var len = 2; len <= n; len <<= 1) {
    final ang = -2 * math.pi / len;
    final wr = math.cos(ang), wi = math.sin(ang);
    for (var i = 0; i < n; i += len) {
      var cr = 1.0, ci = 0.0;
      for (var k = 0; k < len ~/ 2; k++) {
        final ur = re[i + k], ui = im[i + k];
        final vr = re[i + k + len ~/ 2] * cr - im[i + k + len ~/ 2] * ci;
        final vi = re[i + k + len ~/ 2] * ci + im[i + k + len ~/ 2] * cr;
        re[i + k] = ur + vr;
        im[i + k] = ui + vi;
        re[i + k + len ~/ 2] = ur - vr;
        im[i + k + len ~/ 2] = ui - vi;
        final t = cr * wr - ci * wi;
        ci = cr * wi + ci * wr;
        cr = t;
      }
    }
  }
}

/// Pendiente de log(potencia) contra log(frecuencia) entre [f0] y [f1] Hz.
double _pendiente(Int16List m, {double f0 = 100, double f1 = 5000, int hz = 22050}) {
  final x = [for (final v in m) v / 32768.0];
  const n = 8192;
  final p = _potencia(x, n);
  final xs = <double>[], ys = <double>[];
  for (var k = 1; k < p.length; k++) {
    final f = k * hz / n;
    if (f < f0 || f > f1 || p[k] <= 0) continue;
    xs.add(math.log(f) / math.ln10);
    ys.add(math.log(p[k]) / math.ln10);
  }
  final mx = xs.reduce((a, b) => a + b) / xs.length, my = ys.reduce((a, b) => a + b) / ys.length;
  var num = 0.0, den = 0.0;
  for (var i = 0; i < xs.length; i++) {
    num += (xs[i] - mx) * (ys[i] - my);
    den += (xs[i] - mx) * (xs[i] - mx);
  }
  return num / den;
}

double _fraccionEnBanda(Int16List m, double f0, double f1, {int hz = 22050}) {
  final x = [for (final v in m) v / 32768.0];
  const n = 8192;
  final p = _potencia(x, n);
  var dentro = 0.0, total = 0.0;
  for (var k = 1; k < p.length; k++) {
    final f = k * hz / n;
    total += p[k];
    if (f >= f0 && f <= f1) dentro += p[k];
  }
  return dentro / total;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // ================================================================ temporizador
  group('Temporizador', () {
    CicloEstudio ciclo({int rondas = 3, int largo = 0, int cada = 4}) => CicloEstudio(
        enfoque: const Duration(minutes: 25),
        descanso: const Duration(minutes: 5),
        rondas: rondas,
        descansoLargo: Duration(minutes: largo),
        cadaRondas: cada);

    test('un bloque de enfoque termina a los 25 min y pasa al descanso', () {
      final r = _Reloj();
      final t = TemporizadorEstudio(reloj: r.call)..iniciar(ciclo());
      expect(t.fase, FaseEstudio.enfoque);
      expect(t.restante, const Duration(minutes: 25));
      r.avanzar(const Duration(minutes: 24, seconds: 59));
      expect(t.tic(), isEmpty);
      expect(t.restante, const Duration(seconds: 1));
      r.avanzar(const Duration(seconds: 1));
      final ev = t.tic();
      expect(ev, hasLength(1));
      expect(ev.single.de, FaseEstudio.enfoque);
      expect(ev.single.a, FaseEstudio.descanso);
      expect(ev.single.terminaEnfoque, isTrue);
      expect(t.restante, const Duration(minutes: 5));
    });

    test('recorre rondas y termina sin descanso tras la última', () {
      final r = _Reloj();
      final t = TemporizadorEstudio(reloj: r.call)..iniciar(ciclo(rondas: 2));
      final fases = <FaseEstudio>[];
      for (var i = 0; i < 4; i++) {
        r.avanzar(i.isEven ? const Duration(minutes: 25) : const Duration(minutes: 5));
        fases.addAll(t.tic().map((e) => e.a));
      }
      expect(fases, [FaseEstudio.descanso, FaseEstudio.enfoque, FaseEstudio.fin]);
      expect(t.fase, FaseEstudio.fin);
      expect(t.enMarcha, isFalse);
    });

    test('el descanso largo llega cada N rondas', () {
      final r = _Reloj();
      final t = TemporizadorEstudio(reloj: r.call)..iniciar(ciclo(rondas: 4, largo: 15, cada: 2));
      final fases = <FaseEstudio>[];
      r.avanzar(const Duration(hours: 6));
      fases.addAll(t.tic().map((e) => e.a));
      expect(fases, [
        FaseEstudio.descanso, FaseEstudio.enfoque, FaseEstudio.descansoLargo,
        FaseEstudio.enfoque, FaseEstudio.descanso, FaseEstudio.enfoque, FaseEstudio.fin,
      ]);
    });

    test('con la pantalla apagada un buen rato, al volver se pone al día y cuenta el enfoque real', () {
      final r = _Reloj();
      final estadisticas = EstadisticasEstudio();
      final t = TemporizadorEstudio(reloj: r.call, alEstudiar: estadisticas.sumar)..iniciar(ciclo(rondas: 3));
      // 80 min sin ningún tic: 25 enfoque + 5 + 25 enfoque + 5 + 20 de la tercera
      r.avanzar(const Duration(minutes: 80));
      final ev = t.tic();
      expect(ev.map((e) => e.a), [FaseEstudio.descanso, FaseEstudio.enfoque, FaseEstudio.descanso, FaseEstudio.enfoque]);
      expect(t.fase, FaseEstudio.enfoque);
      expect(t.ronda, 3);
      expect(t.restante, const Duration(minutes: 5));
      expect(estadisticas.hoy(r.ahora), const Duration(minutes: 70));
    });

    test('pausar detiene la cuenta y reanudar sigue donde iba', () {
      final r = _Reloj();
      final est = EstadisticasEstudio();
      final t = TemporizadorEstudio(reloj: r.call, alEstudiar: est.sumar)..iniciar(ciclo());
      r.avanzar(const Duration(minutes: 10));
      t.pausar();
      expect(t.pausado, isTrue);
      r.avanzar(const Duration(hours: 1));
      expect(t.tic(), isEmpty);
      expect(t.restante, const Duration(minutes: 15));
      t.reanudar();
      r.avanzar(const Duration(minutes: 15));
      expect(t.tic().single.a, FaseEstudio.descanso);
      expect(est.hoy(r.ahora), const Duration(minutes: 25));
    });

    test('saltar pasa de fase y solo cuenta lo estudiado de verdad', () {
      final r = _Reloj();
      final est = EstadisticasEstudio();
      final t = TemporizadorEstudio(reloj: r.call, alEstudiar: est.sumar)..iniciar(ciclo());
      r.avanzar(const Duration(minutes: 7));
      final ev = t.saltar();
      expect(ev.single.saltado, isTrue);
      expect(t.fase, FaseEstudio.descanso);
      expect(est.hoy(r.ahora), const Duration(minutes: 7));
    });

    test('la reglas de la música: bajar, pausar y seguir, y atenuar en el enfoque', () {
      final bajar = ReglaMusica.para(FaseEstudio.descanso, AccionFinBloque.bajar, false);
      expect((bajar.factor, bajar.pausar), (0.35, false));
      final pausar = ReglaMusica.para(FaseEstudio.descansoLargo, AccionFinBloque.pausar, true);
      expect(pausar.pausar, isTrue);
      final seguir = ReglaMusica.para(FaseEstudio.descanso, AccionFinBloque.seguir, true);
      expect((seguir.factor, seguir.pausar), (1.0, false));
      expect(ReglaMusica.para(FaseEstudio.enfoque, AccionFinBloque.bajar, false).factor, 1.0);
      expect(ReglaMusica.para(FaseEstudio.enfoque, AccionFinBloque.bajar, true).factor, closeTo(0.65, 1e-9));
    });
  });

  // ================================================================ sesión completa
  group('Sesión (Estudio + música)', () {
    setUp(() => SharedPreferences.setMockInitialValues({}));

    test('empieza con la cola del perfil y el temporizador; «Bajar» baja y devuelve el volumen', () async {
      final r = _Reloj();
      final m = _Musica();
      final e = _estudio(r)..conectarMusica(m);
      e.ajustarCiclo(rondasNuevas: 2);
      await e.iniciar();
      expect(e.sesionActiva, isTrue);
      expect(m.bitacora.first, startsWith('cola'));
      expect(m.factor, 1.0);
      r.avanzar(const Duration(minutes: 25));
      e.tic();
      expect(e.temporizador.fase, FaseEstudio.descanso);
      expect(m.factor, 0.35);
      expect(e.aviso, contains('Bloque terminado'));
      r.avanzar(const Duration(minutes: 5));
      e.tic();
      expect(e.temporizador.fase, FaseEstudio.enfoque);
      expect(m.factor, 1.0);
      await e.terminar();
      expect(m.bitacora.last, 'salir');
      expect(e.sesionActiva, isFalse);
    });

    test('«Pausar» pausa en el descanso y reanuda al volver; si ya estaba en pausa, no la toca', () async {
      final r = _Reloj();
      final m = _Musica();
      final e = _estudio(r)..conectarMusica(m);
      e.ponerAccion(AccionFinBloque.pausar);
      await e.iniciar();
      r.avanzar(const Duration(minutes: 25));
      e.tic();
      await pumpEventQueue();
      expect(m.sonando, isFalse);
      r.avanzar(const Duration(minutes: 5));
      e.tic();
      await pumpEventQueue();
      expect(m.sonando, isTrue);
      await e.terminar();
    });

    test('«Seguir» no toca la música y «atenuar» la baja un 35 % en el enfoque', () async {
      final r = _Reloj();
      final m = _Musica();
      final e = _estudio(r)..conectarMusica(m);
      e.ponerAccion(AccionFinBloque.seguir);
      e.ponerAtenuar(true);
      await e.iniciar();
      expect(m.factor, closeTo(0.65, 1e-9));
      r.avanzar(const Duration(minutes: 25));
      e.tic();
      expect(m.factor, 1.0);
      expect(m.sonando, isTrue);
      await e.terminar();
    });

    test('la sesión cuenta aunque se vuelva tras mucho tiempo y al final pausa con calma', () async {
      final r = _Reloj();
      final m = _Musica();
      final e = _estudio(r)..conectarMusica(m);
      e.ajustarCiclo(rondasNuevas: 1);
      await e.iniciar();
      r.avanzar(const Duration(hours: 3));
      e.tic();
      await pumpEventQueue();
      expect(e.temporizador.fase, FaseEstudio.fin);
      expect(e.aviso, contains('Terminaste'));
      expect(m.sonando, isFalse);
      expect(e.estadisticas.hoy(r.ahora), const Duration(minutes: 25));
      expect(e.hayBloqueEnCurso, isFalse);
      await e.terminar();
    });

    test('si la búsqueda falla, la sesión sigue con un aviso amable', () async {
      final r = _Reloj();
      final m = _Musica();
      final e = _estudio(r, buscar: (t, {filtro, limite = 20}) async => throw Exception('sin red'))
        ..conectarMusica(m);
      await e.iniciar();
      expect(e.errorCola, isNotNull);
      expect(e.temporizador.enMarcha, isTrue);
      await e.terminar();
    });

    test('lo elegido se guarda y se recupera', () async {
      final r = _Reloj();
      final e = _estudio(r);
      await e.cargar();
      e.elegirPerfil('programar');
      e.elegirEstilo('synthwave');
      e.ajustarCiclo(enfoque: 40, descanso: 8, rondasNuevas: 3, largo: 20);
      e.ponerAccion(AccionFinBloque.pausar);
      e.ponerAtenuar(true);
      e.ponerCandado(true);
      e.ponerBrillo(0.3);
      e.ponerCapa(CapaAmbiente.bosque, true);
      e.ponerVolumenCapa(CapaAmbiente.bosque, 0.55);
      await Future<void>.delayed(const Duration(milliseconds: 600));
      final e2 = _estudio(r);
      await e2.cargar();
      expect(e2.perfilId, 'programar');
      expect(e2.estiloId, 'synthwave');
      expect((e2.enfoqueMin, e2.descansoMin, e2.rondas, e2.descansoLargoMin), (40, 8, 3, 20));
      expect(e2.cicloId, 'custom');
      expect(e2.accion, AccionFinBloque.pausar);
      expect(e2.atenuar && e2.candado, isTrue);
      expect(e2.brillo, closeTo(0.3, 1e-9));
      expect(e2.capaActiva[CapaAmbiente.bosque], isTrue);
      expect(e2.capaVolumen[CapaAmbiente.bosque], closeTo(0.55, 1e-9));
    });

    test('la cola sale de las consultas del perfil, sin voz si hay alternativas', () async {
      final r = _Reloj();
      final consultas = <String>[];
      final e = _estudio(r, buscar: (t, {filtro, limite = 20}) async {
        consultas.add(t);
        return [
          for (var i = 0; i < 8; i++) _pista('i$i${t.length}', 'Calm piano $i instrumental'),
          _pista('v${t.length}', 'Canción (Official Video)', 'Cantante ft. Otro'),
          _pista('l${t.length}', 'Todo lo que quiero (Lyrics)'),
        ];
      });
      e.elegirPerfil('repasar');
      final cola = await e.construirCola();
      expect(consultas.toSet(), PerfilEstudio.repasar.consultas.toSet());
      expect(cola, isNotEmpty);
      expect(cola.every((p) => !'${p['titulo']}'.contains('Official') && !'${p['titulo']}'.contains('Lyrics')), isTrue);
      expect(cola.map((p) => p['video_id']).toSet().length, cola.length, reason: 'sin repetidas');
      // el estilo elegido pone su consulta primero
      consultas.clear();
      e.elegirEstilo('lofi');
      await e.construirCola();
      expect(consultas, contains(EstiloEstudio.todos.first.consulta));
    });
  });

  // ================================================================ curaduría
  group('Curaduría', () {
    test('prefiere instrumental y evita voz cuando hay alternativas', () {
      final lista = [
        _pista('1', 'Canción de amor (Official Video)', 'Estrella ft. Ana'),
        _pista('2', 'Rainy lofi beats to study'),
        _pista('3', 'Piano suave sin letra'),
        _pista('4', 'Sonata en re', 'Orquesta'),
        _pista('5', 'Ambient focus mix'),
        _pista('6', 'Baroque study music instrumental'),
        _pista('7', 'Letra y música (Lyrics)'),
        _pista('8', 'Synthwave chill instrumental'),
        _pista('9', 'Algo neutro'),
      ];
      final r = CuraduriaEstudio.filtrar(lista);
      final ids = r.map((p) => p['video_id']).toList();
      expect(ids, isNot(contains('1')));
      expect(ids, isNot(contains('7')));
      // lo más instrumental va antes que lo neutro
      expect(ids.indexOf('2'), lessThan(ids.indexOf('9')));
      expect(ids.indexOf('4'), greaterThan(ids.indexOf('3')));
    });

    test('si no hay alternativas, no vacía la cola', () {
      final lista = [_pista('1', 'Tema (Official Video)'), _pista('2', 'Otro (Lyrics)'), _pista('3', 'Más ft. X')];
      expect(CuraduriaEstudio.filtrar(lista), hasLength(3));
    });
  });

  // ================================================================ constancia
  group('Estadísticas y racha', () {
    DateTime d(int dia, [int h = 10]) => DateTime(2026, 11, dia, h);

    test('suma por día y reparte lo que cruza la medianoche', () {
      final s = EstadisticasEstudio();
      s.sumar(DateTime(2026, 11, 15, 23, 30), const Duration(minutes: 60));
      expect(s.deDia(DateTime(2026, 11, 15)), const Duration(minutes: 30));
      expect(s.deDia(DateTime(2026, 11, 16)), const Duration(minutes: 30));
    });

    test('racha de días consecutivos y cambio de día', () {
      final s = EstadisticasEstudio();
      for (final dia in [12, 13, 14, 15, 16]) {
        s.sumar(d(dia), const Duration(minutes: 20));
      }
      expect(s.racha(d(16, 20)), 5);
      // al día siguiente, sin haber estudiado aún, la racha de ayer sigue viva
      expect(s.racha(d(17, 8)), 5);
      // dos días sin estudiar: se reinicia, sin reproches
      expect(s.racha(d(18, 8)), 0);
      expect(s.frase(d(18, 8)).toLowerCase(), isNot(contains('perdiste')));
      // un hueco corta la cuenta hacia atrás
      s.msPorDia.remove(EstadisticasEstudio.clave(d(14)));
      expect(s.racha(d(16, 20)), 2);
    });

    test('menos de un minuto no cuenta para la racha', () {
      final s = EstadisticasEstudio()..sumar(d(16), const Duration(seconds: 40));
      expect(s.racha(d(16)), 0);
    });

    test('hoy y esta semana (de lunes a hoy)', () {
      // 16/11/2026 es lunes
      expect(DateTime(2026, 11, 16).weekday, DateTime.monday);
      final s = EstadisticasEstudio();
      s.sumar(DateTime(2026, 11, 15, 10), const Duration(minutes: 50)); // domingo anterior
      s.sumar(d(16), const Duration(minutes: 30));
      s.sumar(d(18), const Duration(minutes: 45));
      expect(s.hoy(d(18)), const Duration(minutes: 45));
      expect(s.semana(d(18)), const Duration(minutes: 75));
      expect(s.semana(d(16)), const Duration(minutes: 30));
    });

    test('guarda y recupera, y los textos son amables', () {
      final s = EstadisticasEstudio()..sumar(d(16), const Duration(minutes: 90));
      final s2 = EstadisticasEstudio.desdeJson(s.toJson());
      expect(s2.hoy(d(16)), const Duration(minutes: 90));
      expect(EstadisticasEstudio.texto(const Duration(minutes: 90)), '1 h 30 min');
      expect(EstadisticasEstudio.texto(const Duration(minutes: 45)), '45 min');
      expect(EstadisticasEstudio().frase(d(16)), contains('Sin presión'));
      expect(EstadisticasEstudio.desdeJson('basura').msPorDia, isEmpty);
    });
  });

  // ================================================================ notas
  group('Notas', () {
    test('guarda, ordena (nueva arriba), borra y recupera', () {
      final n = NotasEstudio();
      expect(n.agregar('   ', DateTime(2026, 11, 16)), isNull);
      final a = n.agregar('Primera idea', DateTime(2026, 11, 16, 9))!;
      final b = n.agregar('Segunda idea', DateTime(2026, 11, 16, 10))!;
      expect(n.lista.map((x) => x.texto), ['Segunda idea', 'Primera idea']);
      final n2 = NotasEstudio.desdeJson(n.toJson());
      expect(n2.lista.map((x) => x.texto), ['Segunda idea', 'Primera idea']);
      expect(n.borrar(a.id), isTrue);
      expect(n.borrar(a.id), isFalse);
      expect(n.lista.single.id, b.id);
      expect(NotasEstudio.fechaCorta(DateTime(2026, 11, 16, 9, 5), DateTime(2026, 11, 16, 20)), 'Hoy, 09:05');
      expect(NotasEstudio.fechaCorta(DateTime(2026, 11, 15, 9, 5), DateTime(2026, 11, 16, 20)), 'Ayer, 09:05');
      expect(NotasEstudio.fechaCorta(DateTime(2026, 11, 10, 9, 5), DateTime(2026, 11, 16, 20)), '10/11, 09:05');
    });

    test('Estudio las guarda en el teléfono', () async {
      SharedPreferences.setMockInitialValues({});
      final r = _Reloj();
      final e = _estudio(r);
      await e.cargar();
      await e.guardarNota('Revisar el capítulo 3');
      final e2 = _estudio(r);
      await e2.cargar();
      expect(e2.notas.lista.single.texto, 'Revisar el capítulo 3');
      await e2.borrarNota(e2.notas.lista.single.id);
      final e3 = _estudio(r);
      await e3.cargar();
      expect(e3.notas.lista, isEmpty);
    });
  });

  // ================================================================ síntesis
  group('Síntesis de sonidos ambientales', () {
    const seg = 8.0;

    for (final c in CapaAmbiente.values) {
      test('${c.name}: longitud, sin recortes y bucle sin clic', () {
        final m = SintesisAmbiente.bucle(c, segundos: seg);
        expect(m.length, (seg * 22050).round());
        var pico = 0;
        var iguales = 0;
        for (final v in m) {
          pico = math.max(pico, v.abs());
          if (v.abs() >= 32767) iguales++;
        }
        expect(pico, lessThan(32767 * 0.98), reason: 'sin recortes');
        expect(pico, greaterThan(32767 * 0.05), reason: 'se oye');
        expect(iguales, 0);
        // continuidad del bucle: el salto entre la última y la primera muestra
        // no es mayor que los saltos normales de la propia pista
        var s2 = 0.0;
        for (var i = 1; i < m.length; i++) {
          final dif = (m[i] - m[i - 1]).toDouble();
          s2 += dif * dif;
        }
        final rmsSalto = math.sqrt(s2 / (m.length - 1));
        final salto = (m.first - m.last).abs().toDouble();
        expect(salto, lessThanOrEqualTo(rmsSalto * 4 + 1), reason: 'sin clic en el bucle');
        // la misma semilla da lo mismo
        expect(SintesisAmbiente.bucle(c, segundos: 1).sublist(0, 200), SintesisAmbiente.bucle(c, segundos: 1).sublist(0, 200));
      });
    }

    test('el cruce de los extremos enlaza la cola con el principio', () {
      final raw = Float64List.fromList([for (var i = 0; i < 1500; i++) math.sin(0.02 * i)]);
      final out = SintesisAmbiente.unirSinClic(raw, 1000);
      expect((out[0] - out[999]).abs(), lessThan(0.03));
      // sin el cruce, un corte a secas de otra fase daría un salto mucho mayor
      expect((raw[0] - raw[999]).abs(), greaterThan(0.5));
    });

    test('espectro: blanco plano, rosa ≈ -1 y marrón ≈ -2 (pendiente en escala log-log)', () {
      final blanco = _pendiente(SintesisAmbiente.bucle(CapaAmbiente.blanco, segundos: 12));
      final rosa = _pendiente(SintesisAmbiente.bucle(CapaAmbiente.rosa, segundos: 12));
      final marron = _pendiente(SintesisAmbiente.bucle(CapaAmbiente.marron, segundos: 12));
      expect(blanco, closeTo(0, 0.25));
      expect(rosa, inInclusiveRange(-1.3, -0.7));
      expect(marron, inInclusiveRange(-2.3, -1.7));
      expect(rosa, lessThan(blanco));
      expect(marron, lessThan(rosa));
    });

    test('cada paisaje suena donde debe', () {
      // la cafetería vive entre 300 y 2500 Hz
      final cafe = SintesisAmbiente.bucle(CapaAmbiente.cafeteria, segundos: 12);
      expect(_fraccionEnBanda(cafe, 250, 3000), greaterThan(0.6));
      // la chimenea y el bosque tienen más graves que la lluvia
      final lluvia = SintesisAmbiente.bucle(CapaAmbiente.lluvia, segundos: 12);
      final chimenea = SintesisAmbiente.bucle(CapaAmbiente.chimenea, segundos: 12);
      final bosque = SintesisAmbiente.bucle(CapaAmbiente.bosque, segundos: 12);
      expect(_fraccionEnBanda(chimenea, 0, 800), greaterThan(_fraccionEnBanda(lluvia, 0, 800)));
      expect(_fraccionEnBanda(bosque, 0, 800), greaterThan(_fraccionEnBanda(lluvia, 0, 800)));
    });

    test('el WAV tiene cabecera correcta (22,05 kHz, 16 bits, mono)', () {
      final m = SintesisAmbiente.bucle(CapaAmbiente.rosa, segundos: 1);
      final w = SintesisAmbiente.wav(m);
      final b = ByteData.sublistView(w);
      expect(String.fromCharCodes(w.sublist(0, 4)), 'RIFF');
      expect(String.fromCharCodes(w.sublist(8, 12)), 'WAVE');
      expect(b.getUint16(20, Endian.little), 1);
      expect(b.getUint16(22, Endian.little), 1);
      expect(b.getUint32(24, Endian.little), 22050);
      expect(b.getUint16(34, Endian.little), 16);
      expect(b.getUint32(40, Endian.little), m.length * 2);
      expect(w.length, 44 + m.length * 2);
      expect(b.getInt16(44, Endian.little), m.first);
    });

    test('la campana es suave: sin recortes y termina en silencio', () {
      for (final fin in [true, false]) {
        final c = SintesisAmbiente.campana(alTerminarBloque: fin);
        expect(c.length, greaterThan(22050 * 2.5));
        expect(c.map((v) => v.abs()).reduce(math.max), lessThan(32767 * 0.8));
        expect(c.last.abs(), lessThan(40));
        expect(c.sublist(0, 200).any((v) => v != 0), isTrue);
      }
    });

    test('SonidosAmbiente: fabrica el WAV una vez y reproduce en bucle con su propio motor', () async {
      final dir = await Directory.systemTemp.createTemp('caudal_amb_test');
      addTearDown(() => dir.delete(recursive: true));
      final motores = <_FakeJugador>[];
      final s = SonidosAmbiente(
          disponible: true, carpeta: () async => dir, fabrica: () => _FakeJugador().also(motores.add));
      await s.encender(CapaAmbiente.blanco, 0.4);
      final f = await s.archivoDe(CapaAmbiente.blanco);
      expect(await f.exists(), isTrue);
      expect(f.lengthSync(), 44 + (SintesisAmbiente.segundosPorDefecto * 22050).round() * 2);
      expect(motores, hasLength(1));
      expect(motores.single.llamadas, contains('prop loop-file=inf'));
      expect(motores.single.llamadas.any((l) => l.startsWith('open ')), isTrue);
      expect(motores.single.volumen, closeTo(40, 1e-9));
      expect(s.sonando, {CapaAmbiente.blanco});
      await s.fijarVolumen(CapaAmbiente.blanco, 0.8);
      expect(motores.single.volumen, closeTo(80, 1e-9));
      // encenderla otra vez no crea otro motor
      await s.encender(CapaAmbiente.blanco, 0.8);
      expect(motores, hasLength(1));
      await s.apagar(CapaAmbiente.blanco);
      expect(motores.single.cerrado, isTrue);
      expect(s.sonando, isEmpty);
    }, timeout: const Timeout(Duration(minutes: 2)));

    test('sin reproductor local (web) no arranca nada', () async {
      final motores = <_FakeJugador>[];
      final s = SonidosAmbiente(disponible: false, fabrica: () => _FakeJugador().also(motores.add));
      await s.encender(CapaAmbiente.lluvia, 0.5);
      expect(motores, isEmpty);
      expect(s.disponible, isFalse);
    });
  });

  // ================================================================ pantallas
  const tamanos = <String, Size>{
    '320x568': Size(320, 568),
    '412x915': Size(412, 915),
    '915x412': Size(915, 412),
    '800x1280': Size(800, 1280),
    '1440x900': Size(1440, 900),
  };

  Widget app(Widget hijo, {double texto = 1.2}) => MaterialApp(
        theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory),
        builder: (c, w) => MediaQuery(
            data: MediaQuery.of(c).copyWith(textScaler: TextScaler.linear(texto)), child: w!),
        home: hijo,
      );

  /// Deja correr [ms] milisegundos en pasos de 50 ms (como un dedo que se mantiene).
  Future<void> esperar(WidgetTester t, int ms) async {
    for (var i = 0; i < ms ~/ 50; i++) {
      await t.pump(const Duration(milliseconds: 50));
    }
  }

  Future<void> ajustar(WidgetTester t, Size s) async {
    t.view.physicalSize = s * 2;
    t.view.devicePixelRatio = 2;
    addTearDown(t.view.reset);
  }

  Future<Estudio> preparar(WidgetTester t, _Reloj r, {bool ambiente = false}) async {
    SharedPreferences.setMockInitialValues({});
    final e = _estudio(r, ambiente: ambiente);
    await t.runAsync(e.cargar);
    return e;
  }

  group('Pantallas', () {
    for (final entry in tamanos.entries) {
      testWidgets('Preparar la sesión · ${entry.key}', (t) async {
        await ajustar(t, entry.value);
        final r = _Reloj();
        final e = await preparar(t, r, ambiente: true);
        e.estadisticas.sumar(DateTime(2026, 11, 16, 8), const Duration(minutes: 95));
        await t.pumpWidget(app(EstudioPagina(estudio: e, musica: _Musica())));
        await t.pump(const Duration(milliseconds: 400));
        expect(t.takeException(), isNull);
        expect(find.text('Modo estudio'), findsOneWidget);
        expect(find.text('Leer / Escribir'), findsOneWidget);
        expect(find.text('Empezar a estudiar'), findsOneWidget);
        // recorre toda la página: nada debe desbordar al desplazarse
        final lista = find.byType(SingleChildScrollView).first;
        for (var i = 0; i < 8; i++) {
          await t.drag(lista, const Offset(0, -400));
          await t.pump(const Duration(milliseconds: 100));
        }
        expect(t.takeException(), isNull);
        expect(find.text('Tu constancia'), findsOneWidget);
        await t.pumpWidget(const SizedBox());
      });

      testWidgets('Vista de enfoque (bloque, descanso y fin) · ${entry.key}', (t) async {
        await ajustar(t, entry.value);
        final r = _Reloj();
        final e = await preparar(t, r);
        final m = _Musica();
        e.conectarMusica(m);
        e.ajustarCiclo(rondasNuevas: 1);
        await t.pumpWidget(app(EstudioEnfoque(estudio: e)));
        e.iniciar();
        for (var i = 0; i < 5; i++) {
          await t.pump(const Duration(milliseconds: 400));
        }
        expect(t.takeException(), isNull);
        expect(find.text('25:00'), findsOneWidget);
        expect(find.text('ENFOQUE'), findsOneWidget);
        expect(find.byTooltip('Mezclador de sonidos'), findsOneWidget);
        expect(find.byTooltip('Captura de ideas'), findsOneWidget);
        // pasan 12 minutos
        r.avanzar(const Duration(minutes: 12, seconds: 30));
        await t.pump(const Duration(seconds: 1));
        expect(find.text('12:30'), findsOneWidget);
        // en pausa
        await t.tap(find.text('Pausar'));
        await t.pump(const Duration(milliseconds: 400));
        expect(find.text('EN PAUSA'), findsOneWidget);
        await t.tap(find.text('Reanudar'));
        await t.pump(const Duration(milliseconds: 400));
        // el bloque acaba: era la única ronda, así que se completa la sesión
        r.avanzar(const Duration(minutes: 13));
        await t.pump(const Duration(seconds: 1));
        for (var i = 0; i < 5; i++) {
          await t.pump(const Duration(milliseconds: 400));
        }
        expect(find.text('Sesión completa'), findsOneWidget);
        expect(find.textContaining('Terminaste'), findsOneWidget);
        expect(t.takeException(), isNull);
        await t.runAsync(e.terminar);
        await t.pumpWidget(const SizedBox());
      });

      testWidgets('Hojas de mezclador, notas y ajustes · ${entry.key}', (t) async {
        await ajustar(t, entry.value);
        final r = _Reloj();
        final e = await preparar(t, r, ambiente: true);
        e.conectarMusica(_Musica());
        await t.pumpWidget(app(EstudioEnfoque(estudio: e)));
        e.iniciar();
        await t.pump(const Duration(milliseconds: 500));
        // mezclador
        await t.tap(find.byTooltip('Mezclador de sonidos'));
        await t.pumpAndSettle();
        expect(find.text('Lluvia'), findsOneWidget);
        expect(find.text('Música base'), findsOneWidget);
        expect(find.text('Ruido marrón'), findsOneWidget, skip: false);
        expect(t.takeException(), isNull);
        await t.tapAt(const Offset(4, 4));
        await t.pumpAndSettle();
        // notas, con varias notas para que haya lista
        await t.runAsync(() async {
          for (var i = 0; i < 6; i++) {
            await e.guardarNota('Idea número $i: revisar la fórmula y comparar con el ejemplo del libro, '
                'que no me quedó del todo claro.');
          }
        });
        await t.tap(find.byTooltip('Captura de ideas'));
        await t.pumpAndSettle();
        expect(find.text('Guardar nota'), findsOneWidget);
        expect(t.takeException(), isNull);
        await t.enterText(find.byType(TextField), 'Otra idea nueva');
        await t.tap(find.text('Guardar nota'));
        await t.pump(const Duration(milliseconds: 300));
        expect(find.textContaining('Otra idea nueva'), findsOneWidget);
        expect(t.takeException(), isNull);
        await t.tapAt(const Offset(4, 4));
        await t.pumpAndSettle();
        // ajustes de la vista
        await t.tap(find.byTooltip('Ajustes de la vista'));
        await t.pumpAndSettle();
        expect(find.text('Modo oscuro cálido'), findsOneWidget);
        expect(find.text('Brillo cálido'), findsOneWidget);
        expect(t.takeException(), isNull);
        await t.tapAt(const Offset(4, 4));
        await t.pumpAndSettle();
        await t.runAsync(e.terminar);
        await t.pumpWidget(const SizedBox());
      });

      testWidgets('Tarjeta de Inicio · ${entry.key}', (t) async {
        await ajustar(t, entry.value);
        await t.pumpWidget(app(const Scaffold(body: Center(child: TarjetaEstudio()))));
        await t.pump();
        expect(t.takeException(), isNull);
        expect(find.text('Modo estudio'), findsOneWidget);
      });
    }

    testWidgets('Sin sonidos locales (web) se explica con amabilidad', (t) async {
      await ajustar(t, const Size(412, 915));
      final r = _Reloj();
      final e = await preparar(t, r, ambiente: false);
      await t.pumpWidget(app(Scaffold(body: SingleChildScrollView(child: MezcladorEstudio(estudio: e, paleta: PaletaEstudio.normal())))));
      await t.pump();
      expect(find.text('Los sonidos ambientales están en la app para Android y Windows.'), findsOneWidget);
      expect(find.text('Lluvia'), findsNothing);
      expect(t.takeException(), isNull);
    });

    testWidgets('Modo cálido: fondo oscuro cálido y el brillo cambia los colores', (t) async {
      final tenue = PaletaEstudio.calida(0), vivo = PaletaEstudio.calida(1);
      expect(tenue.fondo, vivo.fondo);
      expect(tenue.texto.computeLuminance(), lessThan(vivo.texto.computeLuminance()));
      // bajo contraste y tinte ámbar: rojo > verde > azul
      expect(vivo.texto.r, greaterThan(vivo.texto.g));
      expect(vivo.texto.g, greaterThan(vivo.texto.b));
      expect(vivo.fondo.computeLuminance(), lessThan(0.02));
    });

    testWidgets('Salir con un bloque en curso pide confirmación', (t) async {
      await ajustar(t, const Size(412, 915));
      final r = _Reloj();
      final e = await preparar(t, r);
      e.conectarMusica(_Musica());
      await t.pumpWidget(app(Builder(builder: (ctx) => Scaffold(
            body: Center(
              child: FilledButton(
                onPressed: () => Navigator.of(ctx).push(MaterialPageRoute(builder: (_) => EstudioEnfoque(estudio: e))),
                child: const Text('abrir'),
              ),
            ),
          ))));
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle();
      e.iniciar();
      await t.pump(const Duration(milliseconds: 500));
      expect(find.text('25:00'), findsOneWidget);

      // atrás (gesto): aparece la pregunta; «Seguir estudiando» se queda
      await t.binding.handlePopRoute();
      await t.pumpAndSettle();
      expect(find.text('¿Salir de tu sesión de estudio?'), findsOneWidget);
      await t.tap(find.text('Seguir estudiando'));
      await t.pumpAndSettle();
      expect(find.text('25:00'), findsOneWidget);
      expect(e.sesionActiva, isTrue);

      // la equis de la barra también pregunta
      await t.tap(find.byTooltip('Salir'));
      await t.pumpAndSettle();
      expect(find.text('¿Salir de tu sesión de estudio?'), findsOneWidget);
      // «Salir» termina la sesión y vuelve
      await t.tap(find.text('Salir'));
      await t.pumpAndSettle();
      expect(find.text('abrir'), findsOneWidget);
      expect(e.sesionActiva, isFalse);
    });

    testWidgets('Con el candado, salir exige mantener pulsado 2 segundos', (t) async {
      await ajustar(t, const Size(412, 915));
      final r = _Reloj();
      final e = await preparar(t, r);
      e.conectarMusica(_Musica());
      e.ponerCandado(true);
      await t.pumpWidget(app(Builder(builder: (ctx) => Scaffold(
            body: Center(
              child: FilledButton(
                onPressed: () => Navigator.of(ctx).push(MaterialPageRoute(builder: (_) => EstudioEnfoque(estudio: e))),
                child: const Text('abrir'),
              ),
            ),
          ))));
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle();
      e.iniciar();
      await t.pump(const Duration(milliseconds: 500));

      // un toque suelto en el candado de arriba no sale
      await t.tap(find.byIcon(Icons.lock_outline_rounded).first);
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('25:00'), findsOneWidget);

      // mantener menos de 2 s y soltar: nada
      var g = await t.startGesture(t.getCenter(find.byIcon(Icons.lock_outline_rounded).first));
      await esperar(t, 1200);
      await g.up();
      await t.pump(const Duration(seconds: 1));
      expect(find.text('25:00'), findsOneWidget);
      expect(e.sesionActiva, isTrue);

      // el gesto atrás pregunta y su «Salir» también pide mantener
      await t.binding.handlePopRoute();
      await t.pumpAndSettle();
      expect(find.text('Mantén para salir'), findsOneWidget);
      expect(find.text('Salir'), findsNothing);
      await t.tap(find.text('Seguir estudiando'));
      await t.pumpAndSettle();

      // mantener 2 s: sale
      g = await t.startGesture(t.getCenter(find.byIcon(Icons.lock_outline_rounded).first));
      await esperar(t, 2400);
      await g.up();
      await t.pumpAndSettle();
      expect(find.text('abrir'), findsOneWidget);
      expect(e.sesionActiva, isFalse);
    });

    testWidgets('Elegir perfil, estilo y ritmo en la pantalla de preparación', (t) async {
      await ajustar(t, const Size(412, 915));
      final r = _Reloj();
      final e = await preparar(t, r, ambiente: true);
      await t.pumpWidget(app(EstudioPagina(estudio: e, musica: _Musica())));
      await t.pump(const Duration(milliseconds: 400));
      await t.tap(find.text('Programar / Analizar'));
      await t.pump(const Duration(milliseconds: 300));
      expect(e.perfilId, 'programar');
      // la mezcla del perfil se aplicó
      expect(e.capaActiva[CapaAmbiente.cafeteria], isTrue);
      await t.ensureVisible(find.text('Synthwave suave').last);
      await t.pump(const Duration(milliseconds: 300));
      await t.tap(find.text('Synthwave suave').last);
      await t.pump(const Duration(milliseconds: 300));
      expect(e.estiloId, 'synthwave');
      await t.ensureVisible(find.text('50 / 10'));
      await t.pump(const Duration(milliseconds: 300));
      await t.tap(find.text('50 / 10'));
      await t.pump(const Duration(milliseconds: 300));
      expect((e.enfoqueMin, e.descansoMin), (50, 10));
      await t.ensureVisible(find.text('A mi manera'));
      await t.pump(const Duration(milliseconds: 300));
      await t.tap(find.text('A mi manera'));
      await t.pump(const Duration(milliseconds: 300));
      expect(find.text('Enfoque'), findsWidgets);
      expect(t.takeException(), isNull);
      await t.pumpWidget(const SizedBox());
    });
  });
}

extension _Tambien<T> on T {
  T also(void Function(T) f) {
    f(this);
    return this;
  }
}
