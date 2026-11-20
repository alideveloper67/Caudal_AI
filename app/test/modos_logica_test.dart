// ignore_for_file: experimental_member_use

import 'dart:async';

import 'package:audio_session/audio_session.dart';
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/eq_adaptable.dart';
import 'package:caudal/nucleo/letra_bloqueo.dart';
import 'package:caudal/nucleo/mixes.dart';
import 'package:caudal/nucleo/modos_escucha.dart';
import 'package:caudal/nucleo/novedades_para_ti.dart';
import 'package:caudal/nucleo/resumen_semanal.dart';
import 'package:caudal/nucleo/ritmo.dart';
import 'package:caudal/reproduccion/eq_adaptable_control.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Json _p(String t, String a, {String? genero}) => {
      'clave': 'yt:$t',
      'video_id': 'v$t',
      'titulo': t,
      'artista': a,
      'artistas': [
        {'id': 'id_$a', 'nombre': a}
      ],
      'miniatura': '',
      'duracion': 200,
      if (genero != null) 'genero': genero,
    };

class _Col extends ChangeNotifier implements Coleccion {
  final datos = <String, Object?>{};
  @override
  Future<dynamic> estado(String clave) async => datos[clave];
  @override
  Future<void> guardarEstado(String clave, Object? valor) async => datos[clave] = valor;
  @override
  Future<List<Json>> meGustaRecientes(int n) async => [];
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _Repro extends ChangeNotifier implements Reproductor {
  _Repro(this.ajustes, this.coleccion);
  @override
  final Ajustes ajustes;
  @override
  final Coleccion coleccion;
  @override
  Json? actual;
  @override
  Json? contexto;
  int aplicados = 0;

  @override
  Future<void> dispose() async => super.dispose();

  @override
  Future<void> aplicarSonido() async => aplicados++;

  void poner(Json? p) {
    actual = p;
    notifyListeners();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

AudioDevice _disp(AudioDeviceType t, {bool salida = true}) =>
    AudioDevice(id: '$t', name: '$t', isInput: !salida, isOutput: salida, type: t);

void main() {
  group('LetraBloqueo', () {
    test('solo avisa cuando cambia de línea', () {
      final l = LetraBloqueo();
      l.cambiarCancion('c1');
      l.ponerLetra('c1', [(5000, ''), (1000, 'hola'), (3000, 'mundo')]); // llegan desordenadas
      expect(l.alMoverse(const Duration(milliseconds: 200)), isNull, reason: 'antes de la primera línea no hay nada');
      expect(l.alMoverse(const Duration(milliseconds: 1500)), 'hola');
      expect(l.alMoverse(const Duration(milliseconds: 2000)), isNull);
      expect(l.alMoverse(const Duration(milliseconds: 2999)), isNull);
      expect(l.alMoverse(const Duration(milliseconds: 3000)), 'mundo');
      // una línea en blanco (pausa instrumental) limpia el subtítulo
      expect(l.alMoverse(const Duration(milliseconds: 5200)), '');
      expect(l.alMoverse(const Duration(milliseconds: 6000)), isNull);
      // un salto atrás
      expect(l.alMoverse(const Duration(milliseconds: 1100)), 'hola');
      expect(l.alMoverse(const Duration(milliseconds: 0)), '');
    });

    test('al cambiar de canción se borra la línea; una letra tardía de otra canción se ignora', () {
      final l = LetraBloqueo();
      l.cambiarCancion('a');
      l.ponerLetra('a', [(0, 'uno')]);
      expect(l.alMoverse(Duration.zero), 'uno');
      expect(l.cambiarCancion('b'), '');
      expect(l.cambiarCancion('b'), isNull, reason: 'ya estaba vacío');
      l.ponerLetra('a', [(0, 'vieja')]);
      expect(l.hayLetra, isFalse);
      expect(l.alMoverse(Duration.zero), isNull);
      l.ponerLetra('b', [(0, 'dos')]);
      expect(l.alMoverse(Duration.zero), 'dos');
      expect(l.apagar(), '');
      expect(l.alMoverse(const Duration(seconds: 1)), isNull);
    });

    test('muchos tics seguidos no generan publicaciones', () {
      final l = LetraBloqueo();
      l.cambiarCancion('x');
      l.ponerLetra('x', [for (var i = 0; i < 60; i++) (i * 4000, 'línea $i')]);
      var cambios = 0;
      for (var ms = 0; ms < 240000; ms += 200) {
        if (l.alMoverse(Duration(milliseconds: ms)) != null) cambios++;
      }
      expect(cambios, 60, reason: 'una por línea, no una por tic');
    });
  });

  group('EQ adaptable (lógica)', () {
    test('géneros: el de la pista, el de la lista de género o el del título', () {
      expect(GeneroEq.de(_p('x', 'y', genero: 'Hip-Hop')), 'hiphop');
      expect(GeneroEq.de(_p('Tema', 'Alguien'), contexto: {'tipo': 'genero', 'titulo': 'Rock'}), 'rock');
      expect(GeneroEq.de(_p('Suite de piano · Sinfonía 5', 'Orquesta X')), 'clasica');
      expect(GeneroEq.de(_p('Despechá', 'Rosalía')), '', reason: 'sin pistas, no se adivina');
    });

    test('manda el artista, luego el género, luego la salida', () {
      final p = PerfilesEq();
      p.ponerSalida(SalidaAudio.bluetooth, 'Pop');
      final pista = _p('Tema', 'Rosalía', genero: 'rock');
      expect(p.perfilPara(pista, SalidaAudio.bluetooth), 'Pop');
      expect(p.motivoPara(pista, SalidaAudio.bluetooth), contains('bluetooth'));
      p.ponerGenero('rock', 'Rock');
      expect(p.perfilPara(pista, SalidaAudio.bluetooth), 'Rock');
      p.ponerArtista('id:id_Rosalía', 'Rosalía', 'Voces');
      expect(p.perfilPara(pista, SalidaAudio.bluetooth), 'Voces');
      expect(p.motivoPara(pista, SalidaAudio.bluetooth), contains('Rosalía'));
      expect(p.perfilPara(_p('Otra', 'Otro'), SalidaAudio.audifonos), isNull);
    });

    test('sin detección, vale el perfil elegido a mano', () {
      final p = PerfilesEq(manual: SalidaAudio.bocina);
      p.ponerSalida(SalidaAudio.bocina, 'Altavoz pequeño');
      expect(p.perfilPara(_p('a', 'b'), null), 'Altavoz pequeño');
      // con detección y salida conocida, manda la detectada
      expect(p.perfilPara(_p('a', 'b'), SalidaAudio.bluetooth), isNull, reason: 'manda la detectada; sin regla propia, sin ajuste');
      p.ponerSalida(SalidaAudio.bluetooth, 'Pop');
      expect(p.perfilPara(_p('a', 'b'), SalidaAudio.bluetooth), 'Pop');
      p.detectar = false;
      expect(p.perfilPara(_p('a', 'b'), SalidaAudio.bluetooth), 'Altavoz pequeño');
    });

    test('se guarda y se lee; un texto roto no rompe', () {
      final p = PerfilesEq(detectar: false, manual: SalidaAudio.audifonos);
      p.ponerSalida(SalidaAudio.bluetooth, 'Pop');
      p.ponerGenero('jazz', 'Jazz');
      p.ponerArtista('id:1', 'Fulano', 'Voces');
      final otra = PerfilesEq.desde(p.aTexto());
      expect(otra.detectar, isFalse);
      expect(otra.manual, SalidaAudio.audifonos);
      expect(otra.salidas, {'bluetooth': 'Pop'});
      expect(otra.generos, {'jazz': 'Jazz'});
      expect(otra.artistas['id:1']!.nombre, 'Fulano');
      expect(PerfilesEq.desde('{no es json').vacio, isTrue);
      expect(PerfilesEq.desde(null).vacio, isTrue);
      // quitar una regla
      otra.ponerSalida(SalidaAudio.bluetooth, '');
      expect(otra.salidas, isEmpty);
    });

    test('las reglas de artistas tienen tope', () {
      final p = PerfilesEq();
      for (var i = 0; i < 100; i++) {
        p.ponerArtista('id:$i', 'A$i', 'Pop');
      }
      expect(p.artistas.length, 60);
      expect(p.artistas.containsKey('id:99'), isTrue);
      expect(p.artistas.containsKey('id:0'), isFalse);
    });

    test('dispositivos del sistema -> salida', () {
      expect(salidaDeDispositivos([AudioDeviceType.builtInSpeaker]), SalidaAudio.bocina);
      expect(salidaDeDispositivos([AudioDeviceType.builtInSpeaker, AudioDeviceType.wiredHeadphones]), SalidaAudio.audifonos);
      expect(salidaDeDispositivos([AudioDeviceType.builtInSpeaker, AudioDeviceType.bluetoothA2dp]), SalidaAudio.bluetooth);
      expect(salidaDeDispositivos([AudioDeviceType.builtInEarpiece]), isNull);
      expect(salidaDeDispositivos(const []), isNull);
    });
  });

  group('ControlEqAdaptable', () {
    late _Col col;
    late Ajustes aj;
    late _Repro r;
    late StreamController<Set<AudioDevice>> disp;
    late ControlEqAdaptable c;
    var donador = true;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      donador = true;
      col = _Col();
      aj = await Ajustes.cargar('prueba');
      r = _Repro(aj, col);
      disp = StreamController<Set<AudioDevice>>();
      c = ControlEqAdaptable.prueba(donador: () => donador);
    });

    tearDown(() async {
      await c.soltar();
      await disp.close();
    });

    Future<void> enlazar() async {
      await c.enlazar(r, dispositivos: disp.stream);
      await pumpEventQueue();
    }

    test('pone el ajuste del Bluetooth al conectarlo y devuelve el tuyo al quitarlo', () async {
      col.datos['eq_adaptable'] = (PerfilesEq()..ponerSalida(SalidaAudio.bluetooth, 'Graves potentes')).aJson();
      await aj.poner('ecualizador', true, avisar: false);
      await aj.poner('eq_bandas', [1, 1, 1, 1, 1, 1, 1, 1, 1, 1], avisar: false);
      await aj.poner('eq_preset', 'Personalizado', avisar: false);
      await enlazar();
      r.poner(_p('a', 'b'));
      disp.add({_disp(AudioDeviceType.bluetoothA2dp), _disp(AudioDeviceType.builtInSpeaker)});
      await pumpEventQueue();
      expect(c.detectada, SalidaAudio.bluetooth);
      expect(aj.sino('ecualizador'), isTrue);
      expect(aj.texto('eq_preset'), 'Graves potentes');
      expect(aj.bandasEq, presetsEq['Graves potentes']);
      expect(r.aplicados, greaterThan(0));
      expect(c.aplicado, 'Graves potentes');

      // se desconecta: vuelve lo que tenía la persona
      disp.add({_disp(AudioDeviceType.builtInSpeaker)});
      await pumpEventQueue();
      expect(c.detectada, SalidaAudio.bocina);
      expect(c.aplicado, isNull);
      expect(aj.texto('eq_preset'), 'Personalizado');
      expect(aj.bandasEq, [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]);
      expect(aj.sino('ecualizador'), isTrue);
    });

    test('devuelve el ecualizador apagado si estaba apagado', () async {
      col.datos['eq_adaptable'] = (PerfilesEq()..ponerGenero('rock', 'Rock')).aJson();
      await enlazar();
      r.poner(_p('a', 'b', genero: 'rock'));
      await pumpEventQueue();
      expect(aj.sino('ecualizador'), isTrue);
      expect(aj.texto('eq_preset'), 'Rock');
      r.poner(_p('c', 'd', genero: 'jazz')); // sin regla
      await pumpEventQueue();
      expect(aj.sino('ecualizador'), isFalse);
      expect(aj.texto('eq_preset'), 'Plano');
      expect(aj.bandasEq, List.filled(10, 0));
    });

    test('lo recordado por artista gana, y si lo tocas a mano se respeta', () async {
      await enlazar();
      await c.cambiar((p) {
        p.ponerSalida(SalidaAudio.bocina, 'Pop');
        p.ponerArtista('id:id_Rosalía', 'Rosalía', 'Voces');
      });
      disp.add({_disp(AudioDeviceType.builtInSpeaker)});
      r.poner(_p('Despechá', 'Rosalía'));
      await pumpEventQueue();
      expect(aj.texto('eq_preset'), 'Voces');
      // otra canción de otro artista: el de la bocina
      r.poner(_p('Otra', 'Otro'));
      await pumpEventQueue();
      expect(aj.texto('eq_preset'), 'Pop');
      // la persona mueve el ecualizador a mano
      await aj.poner('eq_preset', 'Personalizado', avisar: false);
      await aj.poner('eq_bandas', [9, 0, 0, 0, 0, 0, 0, 0, 0, 0], avisar: false);
      // y llega una canción sin regla: no se le pisa lo suyo con lo "de antes"
      await c.cambiar((p) {
        p.ponerSalida(SalidaAudio.bocina, '');
      });
      r.poner(_p('Tercera', 'Alguien'));
      await pumpEventQueue();
      expect(aj.texto('eq_preset'), 'Personalizado');
      expect(aj.bandasEq.first, 9);
    });

    test('sin ser donador no toca nada; el Modo gamer tampoco se pisa', () async {
      col.datos['eq_adaptable'] = (PerfilesEq()..ponerGenero('rock', 'Rock')).aJson();
      donador = false;
      await enlazar();
      r.poner(_p('a', 'b', genero: 'rock'));
      await pumpEventQueue();
      expect(aj.sino('ecualizador'), isFalse);
      donador = true;
      await aj.poner('gamer_activo', true, avisar: false);
      r.poner(_p('c', 'd', genero: 'rock'));
      await pumpEventQueue();
      expect(aj.sino('ecualizador'), isFalse, reason: 'el modo gamer manda');
    });

    test('lo guardado vuelve al enlazar de nuevo (otra sesión)', () async {
      await enlazar();
      await c.cambiar((p) => p.ponerSalida(SalidaAudio.audifonos, 'Voces'));
      expect(col.datos['eq_adaptable'], isA<Map>());
      final otro = ControlEqAdaptable.prueba(donador: () => true);
      await otro.enlazar(r, dispositivos: const Stream.empty());
      expect(otro.perfiles.salidas, {'audifonos': 'Voces'});
      await otro.soltar();
    });
  });

  group('Modos de escucha', () {
    AnalisisRitmo bpm(double b, {double conf = 0.8, bool manual = false}) =>
        AnalisisRitmo(bpm: b, confianza: conf, manual: manual);

    test('por tempo: solo las del rango, de menos a más, sin repetir', () {
      final pistas = [for (var i = 0; i < 6; i++) _p('t$i', 'a$i'), _p('t0', 'a0')];
      final ritmos = {
        'yt:t0': bpm(150),
        'yt:t1': bpm(130),
        'yt:t2': bpm(90), // muy lenta
        'yt:t3': bpm(140, conf: 0.05), // sin pulso claro
        'yt:t4': bpm(142, conf: 0.05, manual: true), // a mano: vale
        'yt:t5': bpm(0),
      };
      final r = ModosEscucha.porTempo(pistas, ritmos, min: 120, max: 160);
      expect([for (final p in r) p['clave']], ['yt:t1', 'yt:t4', 'yt:t0']);
    });

    test('por tempo: con más de las que caben se reparte parejo', () {
      final pistas = [for (var i = 0; i < 100; i++) _p('t$i', 'a')];
      final ritmos = {for (var i = 0; i < 100; i++) 'yt:t$i': bpm(100 + i.toDouble())};
      final r = ModosEscucha.porTempo(pistas, ritmos, min: 100, max: 200, largo: 10);
      expect(r.length, 10);
      final b = [for (final p in r) ritmos[p['clave']]!.bpm];
      expect(b, [...b]..sort());
      expect(b.first, lessThan(110));
      expect(b.last, greaterThan(185));
    });

    test('ejercicio con ritmos conocidos: usa tu música y no busca', () async {
      var busquedas = 0;
      final propias = [for (var i = 0; i < 12; i++) _p('m$i', 'a$i')];
      final ritmos = {for (var i = 0; i < 12; i++) 'yt:m$i': bpm(125 + i.toDouble())};
      final r = await ModosEscucha.ejercicio(
        IntensidadEjercicio.medio,
        ritmos: ritmos,
        propias: propias,
        buscar: (q, {filtro, limite = 20}) async {
          busquedas++;
          return [];
        },
      );
      expect(r.porTempo, isTrue);
      expect(busquedas, 0);
      expect(r.pistas.length, 12);
    });

    test('ejercicio sin ritmos: búsquedas tipo workout, sin repetidas', () async {
      final consultas = <String>[];
      final r = await ModosEscucha.ejercicio(
        IntensidadEjercicio.intenso,
        buscar: (q, {filtro, limite = 20}) async {
          consultas.add(q);
          return [for (var i = 0; i < 5; i++) _p('w${i % 3}_$i', 'x')..['video_id'] = 'w${(i + consultas.length) % 4}'];
        },
      );
      expect(r.porTempo, isFalse);
      expect(consultas.any((q) => q.contains('gym') || q.contains('workout') || q.contains('running')), isTrue);
      final ids = [for (final p in r.pistas) p['video_id']];
      expect(ids.toSet().length, ids.length);
      expect(r.pistas, isNotEmpty);
    });

    test('ejercicio con pocas propias: las completa con búsquedas, las suyas primero', () async {
      final propias = [for (var i = 0; i < 3; i++) _p('m$i', 'a$i')];
      final ritmos = {for (var i = 0; i < 3; i++) 'yt:m$i': bpm(130 + i.toDouble())};
      final r = await ModosEscucha.ejercicio(
        IntensidadEjercicio.medio,
        ritmos: ritmos,
        propias: propias,
        buscar: (q, {filtro, limite = 20}) async => [_p('b${q.length}', 'z')],
      );
      expect(r.porTempo, isTrue);
      expect(r.pistas.take(3).map((p) => p['clave']), ['yt:m0', 'yt:m1', 'yt:m2']);
      expect(r.pistas.length, greaterThan(3));
    });

    test('concentración y dormir descartan lo que suena a voz y a video oficial', () async {
      Future<List<Map<String, dynamic>>> buscar(String q, {String? filtro, int limite = 20}) async => [
            for (var i = 0; i < 8; i++) _p('Piano focus $i', 'Calma'),
            _p('Cantante (Official Video)', 'Famoso'),
            _p('Tema lyrics feat. alguien', 'Otro'),
          ];
      final c = await ModosEscucha.concentracion(buscar: buscar);
      expect(c.any((p) => '${p['titulo']}'.contains('Official')), isFalse);
      expect(c.length, 8);
      final d = await ModosEscucha.dormir(buscar: buscar);
      expect(d, isNotEmpty);
      // una búsqueda que falla no rompe el modo
      final vacio = await ModosEscucha.dormir(buscar: (q, {filtro, limite = 20}) async => throw Exception('sin red'));
      expect(vacio, isEmpty);
    });

    test('textos', () {
      expect(ModosEscucha.textoMinutos(45), '45 min');
      expect(ModosEscucha.textoMinutos(60), '1 h');
      expect(ModosEscucha.textoMinutos(90), '1 h 30 min');
      expect(ModosEscucha.reloj(95), '1:35');
    });
  });

  group('Lo nuevo para ti', () {
    final ahora = DateTime(2026, 11, 19, 9);

    List<Json> mix(int n, {int artistas = 20}) => [for (var i = 0; i < n; i++) _p('c$i', 'art${i % artistas}')];

    test('elige 8 variadas: sin repetir y con pocas por artista', () {
      final base = mix(30, artistas: 3); // solo 3 artistas
      final r = NovedadesParaTi.elegir([...base, base.first]);
      expect(r.length, NovedadesParaTi.ideal);
      expect(r.map((p) => p['video_id']).toSet().length, r.length);
      final r2 = NovedadesParaTi.elegir(mix(30));
      final porArtista = <String, int>{};
      for (final p in r2) {
        porArtista['${p['artista']}'] = (porArtista['${p['artista']}'] ?? 0) + 1;
      }
      expect(porArtista.values.every((v) => v <= 2), isTrue);
    });

    test('entre 6 y 10; con menos de 6 no hay tarjeta', () {
      expect(NovedadesParaTi.elegir(mix(30), n: 99).length, 10);
      expect(NovedadesParaTi.elegir(mix(30), n: 1).length, 6);
      expect(NovedadesParaTi.elegir(mix(5)), isEmpty);
      expect(NovedadesParaTi.elegir([for (final p in mix(20)) {...p, 'titulo': '  '}]), isEmpty);
    });

    test('una vez al día: se cierra hasta mañana', () async {
      final c = _Col();
      var armadas = 0;
      Future<Json?> armar(Coleccion _, DateTime h) async {
        armadas++;
        return {'pistas': mix(20)};
      }

      final n = await NovedadesParaTi.delDia(c, ahora: ahora, armar: armar);
      expect(n!.pistas.length, 8);
      expect(n.dia, '2026-11-19');
      await NovedadesParaTi.cerrar(c, ahora: ahora);
      expect(await NovedadesParaTi.delDia(c, ahora: ahora, armar: armar), isNull);
      expect(armadas, 1, reason: 'cerrada hoy: ni se arma');
      // al día siguiente vuelve
      expect(await NovedadesParaTi.delDia(c, ahora: ahora.add(const Duration(days: 1)), armar: armar), isNotNull);
    });

    test('sin recomendaciones (sin red) no hay tarjeta', () async {
      final c = _Col();
      expect(await NovedadesParaTi.delDia(c, ahora: ahora, armar: (_, _) async => null), isNull);
      expect(await NovedadesParaTi.delDia(c, ahora: ahora, armar: (_, _) async => {'pistas': mix(3)}), isNull);
    });
  });

  group('Resumen semanal', () {
    // domingo 22 de noviembre de 2026
    final domingo = DateTime(2026, 11, 22, 20);

    Escucha e(String t, String a, DateTime f, {int dur = 180}) =>
        Escucha({..._p(t, a), 'duracion': dur}, f);

    test('cuenta de lunes a domingo y deja fuera lo de otras semanas', () {
      final h = [
        e('fuera1', 'z', DateTime(2026, 11, 15, 23, 59)), // domingo anterior
        e('A', 'Uno', DateTime(2026, 11, 16, 8)), // lunes
        e('A', 'Uno', DateTime(2026, 11, 16, 9)),
        e('B', 'Uno', DateTime(2026, 11, 18, 10)),
        e('C', 'Dos', DateTime(2026, 11, 22, 12)), // domingo
        e('D', 'Tres', DateTime(2026, 11, 22, 13)),
        e('E', 'Tres', DateTime(2026, 11, 22, 14)),
        e('fuera2', 'z', DateTime(2026, 11, 23, 0, 1)), // lunes siguiente
      ];
      final r = ResumenSemanal.calcular(h, ahora: domingo);
      expect(r.lunes, DateTime(2026, 11, 16));
      expect(r.domingo, DateTime(2026, 11, 22));
      expect(r.escuchas, 6);
      expect(r.minutos, 18);
      expect(r.diasConMusica, 3);
      expect(r.cancionTop!.nombre, 'A');
      expect(r.cancionTop!.escuchas, 2);
      expect(r.artistaTop!.nombre, 'Uno');
      expect(r.topCanciones.length, 5);
      expect(r.topArtistas.length, 3);
      expect(r.diaTop, 7, reason: 'el domingo hubo 3 canciones');
      expect(r.diaTopNombre, 'domingo');
      expect(r.minutosPorDia, [6, 0, 3, 0, 0, 0, 9]);
      expect(r.rango, '16 – 22 nov');
      expect(r.suficiente, isTrue);
    });

    test('semana vacía o pobre', () {
      expect(ResumenSemanal.calcular(const [], ahora: domingo).vacio, isTrue);
      final poca = ResumenSemanal.calcular([e('A', 'x', DateTime(2026, 11, 17))], ahora: domingo);
      expect(poca.suficiente, isFalse);
      expect(poca.diaTop, 2);
    });

    test('el rango cruza de mes', () {
      final r = ResumenSemanal.calcular(const [], ahora: DateTime(2026, 12, 2));
      expect(r.rango, '30 nov – 6 dic');
    });

    test('la tarjeta toca solo los domingos y una vez por semana', () async {
      final c = _Col();
      expect(await ResumenSemanal.toca(c, ahora: DateTime(2026, 11, 21)), isFalse, reason: 'sábado');
      expect(await ResumenSemanal.toca(c, ahora: domingo), isTrue);
      await ResumenSemanal.cerrar(c, ahora: domingo);
      expect(await ResumenSemanal.toca(c, ahora: domingo), isFalse);
      expect(await ResumenSemanal.toca(c, ahora: DateTime(2026, 11, 29, 10)), isTrue, reason: 'el otro domingo vuelve');
    });
  });
}
