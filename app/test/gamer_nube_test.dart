// Modo gamer en la nube: el progreso de la cuenta es la suma de las filas de
// todos los equipos. Sin red: una sesión falsa que solo registra las llamadas.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/gamer_control.dart';
import 'package:caudal/nucleo/gamer_xp.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Sesión de mentira: responde al GET con [filas] y guarda cada petición.
class SesionFalsa extends Sesion {
  SesionFalsa(String uid, {this.filas = const [], this.fallar = false})
      : llamadas = [],
        super(uid, 'token', 'refresco', DateTime.now().add(const Duration(hours: 1)));

  final List<Object?> filas;
  final bool fallar;
  final List<(String, String, Object?, Map<String, String>)> llamadas;

  @override
  Future<dynamic> pedir(String metodo, String ruta,
      {Object? cuerpo, Map<String, String> cabeceras = const {}}) async {
    llamadas.add((metodo, ruta, cuerpo, cabeceras));
    if (fallar) throw Exception('sin red');
    if (metodo == 'GET') return filas;
    return null;
  }
}

void main() {
  const uid = 'usuario-1';

  late Ajustes a;
  late DateTime ahora;
  late ModoGamerControl g;

  /// [progreso] es el JSON local de este equipo (ProgresoGamer.aTexto()); el id de equipo es fijo.
  Future<void> crear({ProgresoGamer progreso = const ProgresoGamer(), Sesion? sesion}) async {
    SharedPreferences.setMockInitialValues({
      'aj.t.gamer_progreso': progreso.aTexto(),
      'aj.t.dispositivo_id': 'este-equipo',
    });
    a = await Ajustes.cargar('t');
    ahora = DateTime(2026, 11, 20, 20);
    g = ModoGamerControl(
      ajustes: a,
      aplicarSonido: () async {},
      lanzar: (p, c) async {},
      sesion: sesion,
      reloj: () => ahora,
    );
    addTearDown(g.dispose);
  }

  test('fórmula de nivel: 0 XP = nivel 1, 50 = 2, 150 = 3, 300 = 4', () {
    expect(nivelDeXp(0), 1);
    expect(nivelDeXp(49), 1);
    expect(nivelDeXp(50), 2);
    expect(nivelDeXp(150), 3);
    expect(nivelDeXp(300), 4);
    expect(nivelDeXp(299), 3);
  });

  test('sin cuenta no hay llamadas y el total es el propio', () async {
    await crear(progreso: ProgresoGamer(xp: 80));
    await g.sincronizar();
    expect(g.xpTotal, 80);
    expect(g.nivelTotal, 2);
    expect(g.dispositivoId, 'este-equipo', reason: 'el guardado en ajustes manda');
  });

  test('sin id guardado se genera un uuid v4 y se queda en los ajustes', () async {
    SharedPreferences.setMockInitialValues({});
    a = await Ajustes.cargar('t');
    final primero = ModoGamerControl(ajustes: a, aplicarSonido: () async {}, lanzar: (p, c) async {});
    final id = primero.dispositivoId;
    expect(id, matches(RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')));
    expect(a.texto('dispositivo_id'), id);
    final segundo = ModoGamerControl(ajustes: a, aplicarSonido: () async {}, lanzar: (p, c) async {});
    expect(segundo.dispositivoId, id, reason: 'otro arranque, mismo equipo');
    primero.dispose();
    segundo.dispose();
  });

  test('xpTotal suma la propia y la de otros equipos', () async {
    final s = SesionFalsa(uid, filas: [
      {'dispositivo': 'otro', 'xp': 120, 'minutos': 5, 'dias': <String>[]},
    ]);
    await crear(progreso: ProgresoGamer(xp: 100), sesion: s);
    await g.sincronizar();
    expect(g.progreso.xp, 100);
    expect(g.nubeXp, 120);
    expect(g.nubeMinutos, 5);
    expect(g.xpTotal, 220);
    expect(g.nivelTotal, nivelDeXp(220));
  });

  test('las filas del propio dispositivo y las rotas se ignoran', () async {
    final s = SesionFalsa(uid, filas: [
      {'dispositivo': 'este-equipo', 'xp': 999, 'minutos': 999, 'dias': ['2026-11-20']},
      {'dispositivo': 'otro', 'xp': 'mucho', 'minutos': 1, 'dias': <String>[]},
      {'dispositivo': 'roto', 'minutos': 1},
      'no soy un mapa',
      {'xp': 7, 'minutos': 2},
      {'dispositivo': 'bueno', 'xp': 30, 'minutos': 4, 'dias': ['2026-11-19', 7]},
    ]);
    await crear(progreso: ProgresoGamer(xp: 10), sesion: s);
    await g.sincronizar();
    expect(g.nubeXp, 30);
    expect(g.nubeMinutos, 4);
    expect(g.nubeDias, {'2026-11-19'});
    expect(g.xpTotal, 40);
  });

  test('rachaTotal une los días de dos equipos: hoy, ayer y anteayer = 3', () async {
    final s = SesionFalsa(uid, filas: [
      {'dispositivo': 'otro', 'xp': 0, 'minutos': 0, 'dias': ['2026-11-19', '2026-11-18']},
    ]);
    await crear(progreso: ProgresoGamer(dias: ['2026-11-20']), sesion: s);
    expect(g.rachaTotal, 1, reason: 'antes de sincronizar solo cuenta lo propio');
    await g.sincronizar();
    expect(g.rachaTotal, 3);
  });

  test('rachaTotal: si hoy no hay nada, la racha sigue desde ayer; un hueco la corta', () async {
    final s = SesionFalsa(uid, filas: [
      {'dispositivo': 'otro', 'xp': 0, 'minutos': 0, 'dias': ['2026-11-18', '2026-11-17']},
    ]);
    await crear(progreso: ProgresoGamer(dias: ['2026-11-19']), sesion: s);
    await g.sincronizar();
    expect(g.rachaTotal, 3, reason: '19, 18 y 17 seguidos; hoy (20) aún no hay y la racha sigue desde ayer');
    ahora = DateTime(2026, 11, 21, 9);
    expect(g.rachaTotal, 0, reason: 'el 20 falta: la racha se perdió');
  });

  test('aporte() solo lleva lo de este equipo, con minutos y días ordenados', () async {
    final s = SesionFalsa(uid, filas: [
      {'dispositivo': 'otro', 'xp': 500, 'minutos': 60, 'dias': ['2026-11-01']},
    ]);
    await crear(progreso: ProgresoGamer(xp: 100, segTotales: 185 * 60 + 30, dias: ['2026-11-02', '2026-11-01']), sesion: s);
    await g.sincronizar();
    final ap = g.progreso.aporte();
    expect(ap.keys.toSet(), {'xp', 'minutos', 'dias'});
    expect(ap['xp'], 100);
    expect(ap['minutos'], 185);
    expect(ap['dias'], ['2026-11-01', '2026-11-02']);
  });

  test('sincronizar: POST con on_conflict y luego GET filtrado por el usuario', () async {
    final s = SesionFalsa(uid, filas: []);
    await crear(progreso: ProgresoGamer(xp: 40, segTotales: 600, dias: ['2026-11-20']), sesion: s);
    await g.sincronizar();
    expect(s.llamadas.length, 2);

    final (metodo, ruta, cuerpo, cabeceras) = s.llamadas[0];
    expect(metodo, 'POST');
    expect(ruta, 'gamer_aportes?on_conflict=user_id,dispositivo');
    expect(cabeceras['Prefer'], 'resolution=merge-duplicates,return=minimal');
    final c = cuerpo as Map;
    expect(c['user_id'], uid);
    expect(c['dispositivo'], g.dispositivoId);
    expect(c['xp'], 40);
    expect(c['minutos'], 10);
    expect(c['dias'], ['2026-11-20']);

    final (metodo2, ruta2, _, _) = s.llamadas[1];
    expect(metodo2, 'GET');
    expect(ruta2, 'gamer_aportes?select=dispositivo,xp,minutos,dias&user_id=eq.$uid');
  });

  test('si la nube falla, no hay error y lo local sigue', () async {
    final s = SesionFalsa(uid, fallar: true);
    await crear(progreso: ProgresoGamer(xp: 60), sesion: s);
    await expectLater(g.sincronizar(), completes);
    expect(g.xpTotal, 60);
    expect(g.rachaTotal, 0);
  });
}
