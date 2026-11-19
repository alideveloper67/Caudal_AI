// El cerebro del Modo gamer: ahorro que se devuelve, sonido que se devuelve,
// listas por situación y XP por escuchar (sin reproductor ni red).
import 'dart:convert';

import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/gamer.dart';
import 'package:caudal/nucleo/gamer_control.dart';
import 'package:caudal/nucleo/gamer_xp.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Map<String, dynamic> pista(String id, {String artista = 'Ana'}) =>
    {'clave': 'yt:$id', 'video_id': id, 'titulo': id, 'artista': artista, 'artistas': [{'nombre': artista, 'id': ''}]};

void main() {
  late Ajustes a;
  late DateTime ahora;
  late int sonidoAplicado;
  late List<(List<Map<String, dynamic>>, Map<String, dynamic>)> lanzadas;
  late List<int> niveles;
  late ModoGamerControl g;

  Future<void> crear({Map<String, Object> prefs = const {}, Future<List<Map<String, dynamic>>> Function(Situacion)? buscar}) async {
    SharedPreferences.setMockInitialValues(prefs);
    a = await Ajustes.cargar('t');
    ahora = DateTime(2026, 11, 19, 20);
    sonidoAplicado = 0;
    lanzadas = [];
    niveles = [];
    g = ModoGamerControl(
      ajustes: a,
      aplicarSonido: () async => sonidoAplicado++,
      lanzar: (p, c) async => lanzadas.add((p, c)),
      alSubirNivel: niveles.add,
      reloj: () => ahora,
      buscarPistas: buscar,
    );
  }

  tearDown(() => g.dispose());

  test('arranca apagado y no toca nada', () async {
    await crear();
    expect(g.activo, isFalse);
    expect(ModoGamerControl.mascotasOcultas.value, isFalse);
    expect(a.sino('modo_ligero'), isFalse);
  });

  test('ahorro: enciende el modo ligero, esconde mascotas y lo devuelve como estaba', () async {
    await crear();
    await g.activar(true);
    expect(a.sino('modo_ligero'), isTrue);
    expect(ModoGamerControl.mascotasOcultas.value, isTrue);
    expect(ModoGamerControl.ocultaMascota(a), isTrue);
    await g.activar(false);
    expect(a.sino('modo_ligero'), isFalse);
    expect(ModoGamerControl.mascotasOcultas.value, isFalse);
    expect(a.texto('gamer_ligero_previo'), '');
  });

  test('ahorro: si ya tenía el modo ligero, se queda encendido al apagar', () async {
    await crear(prefs: {'aj.t.modo_ligero': true});
    await g.activar(true);
    await g.activar(false);
    expect(a.sino('modo_ligero'), isTrue);
  });

  test('ahorro apagado: no cambia el modo ligero ni esconde mascotas', () async {
    await crear();
    await g.ponerAhorro(false);
    await g.activar(true);
    expect(a.sino('modo_ligero'), isFalse);
    expect(ModoGamerControl.mascotasOcultas.value, isFalse);
    await g.ponerAhorro(true);
    expect(a.sino('modo_ligero'), isTrue);
    expect(ModoGamerControl.mascotasOcultas.value, isTrue);
    await g.ponerAhorro(false);
    expect(a.sino('modo_ligero'), isFalse);
    expect(ModoGamerControl.mascotasOcultas.value, isFalse);
  });

  test('sonido: aplica el perfil sobre el ecualizador y lo devuelve al apagar', () async {
    await crear(prefs: {'aj.t.ecualizador': true, 'aj.t.eq_preset': 'Rock', 'aj.t.eq_bandas': '[5,4,2,0,-1,0,2,3,4,4]'});
    await g.activar(true);
    final fps = perfilSonidoPorId('fps')!;
    await g.elegirPerfil(fps);
    expect(a.sino('ecualizador'), isTrue);
    expect(a.bandasEq, fps.bandas);
    expect(a.texto('eq_preset'), fps.nombre);
    // cambiar de perfil no pierde el ecualizador original
    await g.elegirPerfil(perfilSonidoPorId('chill'));
    expect(g.perfil!.id, 'chill');
    await g.activar(false);
    expect(a.sino('ecualizador'), isTrue);
    expect(a.texto('eq_preset'), 'Rock');
    expect(a.bandasEq, [5, 4, 2, 0, -1, 0, 2, 3, 4, 4]);
    expect(a.texto('gamer_eq_previo'), '');
    expect(sonidoAplicado, greaterThanOrEqualTo(3));
    // la calidad del audio no se toca
    expect(a.texto('calidad_audio'), 'maxima');
  });

  test('sonido: quitar el perfil devuelve el ecualizador; al reactivar se vuelve a poner', () async {
    await crear();
    await g.activar(true);
    await g.elegirPerfil(perfilSonidoPorId('carreras'));
    await g.elegirPerfil(null);
    expect(a.sino('ecualizador'), isFalse);
    expect(a.texto('eq_preset'), 'Plano');
    expect(a.bandasEq, List.filled(10, 0));
    await g.elegirPerfil(perfilSonidoPorId('rpg'));
    await g.activar(false);
    expect(a.sino('ecualizador'), isFalse);
    await g.activar(true);
    expect(a.sino('ecualizador'), isTrue, reason: 'el perfil elegido vuelve con el modo');
    expect(a.texto('eq_preset'), perfilSonidoPorId('rpg')!.nombre);
  });

  test('sonido: con el modo apagado no se puede elegir', () async {
    await crear();
    await g.elegirPerfil(perfilSonidoPorId('fps'));
    expect(a.sino('ecualizador'), isFalse);
    expect(g.perfil, isNull);
  });

  test('situación: lanza la lista con su contexto y se puede repetir', () async {
    await crear(buscar: (s) async => [pista('x1'), pista('x2')]);
    await g.activar(true);
    expect(await g.ponerSituacion(Situacion.clutch), isNull);
    expect(lanzadas.length, 1);
    expect(lanzadas.first.$1.length, 2);
    expect(lanzadas.first.$2['titulo'], 'Modo gamer · Clutch');
    expect(g.cargando.value, isNull);
    expect(await g.ponerSituacion(Situacion.victoria), isNull);
    expect(lanzadas.length, 2);
  });

  test('situación: un fallo vuelve como texto y no deja el botón trabado', () async {
    await crear(buscar: (s) async => throw Exception('sin red'));
    await g.activar(true);
    final e = await g.ponerSituacion(Situacion.lobby);
    expect(e, contains('Lobby'));
    expect(lanzadas, isEmpty);
    expect(g.cargando.value, isNull);
  });

  test('situación: apagado no hace nada', () async {
    await crear(buscar: (s) async => [pista('x')]);
    expect(await g.ponerSituacion(Situacion.lobby), isNull);
    expect(lanzadas, isEmpty);
  });

  group('XP', () {
    test('suma por minuto escuchado y se guarda', () async {
      await crear();
      await g.activar(true);
      g.alReproductor(true, pista('a'));
      // el reloj interno vuelca cada 30 s: seis vueltas = 3 minutos
      for (var i = 0; i < 6; i++) {
        ahora = ahora.add(const Duration(seconds: 30));
        g.volcarAhora();
      }
      g.alReproductor(false, pista('a'));
      expect(g.progreso.xp, 3);
      expect(g.progreso.minutosHoy, 3);
      expect(ProgresoGamer.deTexto(a.texto('gamer_progreso')).xp, 3);
      // en pausa no corre
      ahora = ahora.add(const Duration(minutes: 10));
      g.alReproductor(false, pista('a'));
      expect(g.progreso.xp, 3);
    });

    test('con el modo apagado no cuenta nada', () async {
      await crear();
      g.alReproductor(true, pista('a'));
      ahora = ahora.add(const Duration(minutes: 5));
      g.alReproductor(false, pista('a'));
      expect(g.progreso.xp, 0);
    });

    test('canción y artista cuentan al pasar de 20 s; cambiar antes no cuenta', () async {
      await crear();
      await g.activar(true);
      g.alReproductor(true, pista('a', artista: 'Ana'));
      ahora = ahora.add(const Duration(seconds: 10));
      g.alReproductor(true, pista('b', artista: 'Beto')); // salto a los 10 s
      ahora = ahora.add(const Duration(seconds: 25));
      g.alReproductor(true, pista('c', artista: 'Cleo'));
      ahora = ahora.add(const Duration(seconds: 30));
      g.alReproductor(false, pista('c'));
      expect(g.progreso.nuevasHoy, ['yt:b', 'yt:c']);
      expect(g.progreso.artistasHoy, ['beto', 'cleo']);
    });

    test('un salto enorme del reloj (teléfono dormido) no regala XP', () async {
      await crear();
      await g.activar(true);
      g.alReproductor(true, pista('a'));
      ahora = ahora.add(const Duration(hours: 5));
      g.alReproductor(false, pista('a'));
      expect(g.progreso.xp, lessThanOrEqualTo(2));
    });

    test('al subir de nivel avisa una sola vez', () async {
      await crear(prefs: {'aj.t.gamer_progreso': jsonEncode({'xp': 39, 'd': '2026-11-19'})});
      await g.activar(true);
      g.alReproductor(true, pista('a'));
      ahora = ahora.add(const Duration(seconds: 60));
      g.alReproductor(false, pista('a'));
      expect(niveles, [2]);
      g.alReproductor(true, pista('a'));
      ahora = ahora.add(const Duration(seconds: 30));
      g.alReproductor(false, pista('a'));
      expect(niveles, [2]);
    });

    test('el progreso guardado se recupera; un guardado roto no falla', () async {
      await crear(prefs: {'aj.t.gamer_progreso': 'basura{'});
      expect(g.progreso.xp, 0);
      g.dispose();
      await crear(prefs: {'aj.t.gamer_progreso': jsonEncode({'xp': 500})});
      expect(g.progreso.xp, 500);
      expect(g.progreso.nivel, nivelDeXp(500));
    });

    test('un aviso de nivel que falla no rompe la escucha', () async {
      SharedPreferences.setMockInitialValues({'aj.t.gamer_progreso': jsonEncode({'xp': 39, 'd': '2026-11-19'})});
      a = await Ajustes.cargar('t');
      ahora = DateTime(2026, 11, 19, 20);
      g = ModoGamerControl(
        ajustes: a,
        aplicarSonido: () async {},
        lanzar: (p, c) async {},
        alSubirNivel: (n) => throw StateError('x'),
        reloj: () => ahora,
      );
      await g.activar(true);
      g.alReproductor(true, pista('a'));
      ahora = ahora.add(const Duration(seconds: 60));
      g.alReproductor(false, pista('a'));
      expect(g.progreso.xp, 40);
    });
  });
}
