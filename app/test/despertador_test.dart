import 'dart:math';

import 'package:caudal/nucleo/despertador.dart';
import 'package:caudal/nucleo/despertador_control.dart';
import 'package:caudal/nucleo/despertador_nativo.dart';
import 'package:caudal/nucleo/plataforma.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

typedef J = Map<String, dynamic>;

// miércoles 19 de noviembre de 2025, 06:00
final mie = DateTime(2025, 11, 19, 6, 0);

Alarma alarma({
  int hora = 7, int minuto = 0, Set<int> dias = const {1, 2, 3, 4, 5}, bool activa = true,
  FuenteAlarma fuente = FuenteAlarma.meGusta, int volumen = 80, int subida = 60, int posponer = 9,
  String id = 'a1',
}) =>
    Alarma(id: id, hora: hora, minuto: minuto, dias: dias, activa: activa, fuente: fuente,
        volumen: volumen, subida: subida, posponer: posponer);

const p1 = {'clave': 'yt:1', 'video_id': '1', 'titulo': 'Uno', 'artista': 'A'};
const p2 = {'clave': 'yt:2', 'video_id': '2', 'titulo': 'Dos', 'artista': 'B'};
const local3 = {'clave': 'local:3', 'titulo': 'Tres', 'archivo': '/m/tres.mp3'};

bool Function(J) desc(Set<String> claves) => (p) => claves.contains(p['clave']);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('proximaVez', () {
    test('una vez: hoy si no pasó, si no mañana', () {
      final a = alarma(hora: 7, minuto: 30, dias: {});
      expect(proximaVez(a, mie), DateTime(2025, 11, 19, 7, 30));
      expect(proximaVez(a, mie.copyWith(hour: 8)), DateTime(2025, 11, 20, 7, 30));
    });

    test('entre semana salta el fin de semana', () {
      final a = alarma(hora: 7, dias: {1, 2, 3, 4, 5});
      expect(proximaVez(a, DateTime(2025, 11, 21, 9)), DateTime(2025, 11, 24, 7)); // viernes -> lunes
    });

    test('la hora exacta ya no cuenta; cruza de mes', () {
      expect(proximaVez(alarma(hora: 6, dias: {3}), mie), DateTime(2025, 11, 26, 6));
      expect(proximaVez(alarma(hora: 6, dias: {}), DateTime(2025, 11, 30, 7)), DateTime(2025, 12, 1, 6));
    });

    test('apagada no suena y la pospuesta manda', () {
      expect(proximaVez(alarma(activa: false), mie), isNull);
      final p = posponerAlarma(alarma(hora: 6, posponer: 9), mie);
      expect(proximaVez(p, mie), mie.add(const Duration(minutes: 9)));
    });

    test('tras sonar: la de una vez se apaga, la semanal sigue', () {
      final una = trasSonar(posponerAlarma(alarma(dias: {}), mie));
      expect(una.activa, isFalse);
      expect(una.pospuestaHasta, 0);
      expect(trasSonar(alarma(dias: {1})).activa, isTrue);
    });

    test('tocan, con media hora de margen si estuvo dormida', () {
      final a = alarma(hora: 6, minuto: 10, dias: {});
      expect(tocan([a], mie, mie.add(const Duration(minutes: 5))), isEmpty);
      expect(tocan([a], mie.add(const Duration(minutes: 5)), mie.add(const Duration(minutes: 11))), [a]);
      expect(tocan([a], mie.subtract(const Duration(hours: 8)), mie.copyWith(hour: 9)), isEmpty);
      expect(tocan([a], mie.subtract(const Duration(hours: 8)), mie.copyWith(minute: 30)), [a]);
    });
  });

  group('textos y volumen', () {
    test('días y «suena en»', () {
      expect(textoDias({}), 'Una vez');
      expect(textoDias({1, 2, 3, 4, 5, 6, 7}), 'Todos los días');
      expect(textoDias({5, 1, 2, 3, 4}), 'Entre semana');
      expect(textoDias({6, 7}), 'Fines de semana');
      expect(textoDias({1, 3}), 'Lun, Mié');
      expect(textoFalta(const Duration(hours: 7, minutes: 20)), 'Suena en 7 h 20 min');
      expect(textoFalta(const Duration(seconds: 30)), 'Suena en 1 min');
      expect(textoFalta(Duration.zero), 'Suena en menos de un minuto');
      expect(textoFalta(const Duration(days: 2, hours: 1)), 'Suena en 2 días 1 h');
    });

    test('el volumen sube poco a poco (igual que en Python y Kotlin)', () {
      expect(factorVolumen(0, 60), closeTo(volumenInicial, 1e-9));
      expect(factorVolumen(60, 60), 1);
      expect(factorVolumen(120, 60), 1);
      expect(factorVolumen(5, 0), 1);
      final v = [for (var t = 0; t <= 60; t += 5) factorVolumen(t.toDouble(), 60)];
      expect(v, [...v]..sort());
      expect(factorVolumen(15, 60), lessThan(0.1));
      expect(factorVolumen(30, 60), closeTo(0.03 + 0.97 * 0.25, 1e-9));
    });
  });

  group('JSON', () {
    test('ida y vuelta y valores raros acotados', () {
      final a = alarma(hora: 6, minuto: 45, dias: {6, 7}, fuente: const FuenteAlarma(
          tipo: TipoFuente.cancion, id: 'yt:1', titulo: 'Uno · A', pista: p1));
      final b = Alarma.fromJson(a.toJson());
      expect(b.toJson(), a.toJson());
      final raro = Alarma.fromJson({'hora': 99, 'minuto': -3, 'dias': [0, 3, '9', 3, 7], 'volumen': 900,
          'subida': -1, 'posponer': 0, 'fuente': {'tipo': 'raro'}});
      expect([raro.hora, raro.minuto], [23, 0]);
      expect(raro.dias, {3, 7});
      expect([raro.volumen, raro.subida, raro.posponer], [100, 0, 1]);
      expect(raro.fuente.tipo, TipoFuente.tono);
    });

    test('lo pospuesto del escritorio (segundos) se entiende en milisegundos', () {
      final a = Alarma.fromJson({'id': 'x', 'pospuesta_hasta': 1763532000.5});
      expect(a.pospuestaHasta, 1763532000500);
    });

    test('pistaMinima deja lo justo', () {
      final m = pistaMinima({...p1, 'letra': 'mucho texto', '_auto': true, 'archivo': '/a.mp3'});
      expect(m.keys.toSet(), {'clave', 'video_id', 'titulo', 'artista', 'archivo'});
    });

    test('almacén: decodifica lo roto como vacío', () {
      expect(AlmacenAlarmas.decodificar('{no es json'), isEmpty);
      final t = AlmacenAlarmas.codificar([alarma(id: 'z')]);
      expect(AlmacenAlarmas.decodificar(t).single.id, 'z');
    });
  });

  group('qué suena', () {
    test('con red, lo elegido', () {
      final a = alarma(fuente: const FuenteAlarma(tipo: TipoFuente.lista, id: '1'));
      final p = planear(a, hayRed: true, candidatas: [p1, p2], descargada: desc({}), respaldo: [local3]);
      expect(p.pistas, [p1, p2]);
      expect(p.motivo, MotivoPlan.elegido);
    });

    test('sin red: lo descargado de lo elegido, si no el respaldo, si no el tono', () {
      final a = alarma(fuente: const FuenteAlarma(tipo: TipoFuente.lista, id: '1'));
      expect(planear(a, hayRed: false, candidatas: [p1, p2], descargada: desc({'yt:2'})).pistas, [p2]);
      final r = planear(a, hayRed: false, candidatas: [p1], descargada: desc({'local:3'}), respaldo: [local3]);
      expect(r.pistas, [local3]);
      expect(r.motivo, MotivoPlan.respaldo);
      final t = planear(a, hayRed: false, candidatas: [p1], descargada: desc({}), respaldo: [local3]);
      expect(t.esTono, isTrue);
      expect(t.motivo, MotivoPlan.sinMusica);
    });

    test('«me gusta» se baraja; tono es tono', () {
      final muchas = [for (var i = 0; i < 30; i++) <String, dynamic>{'clave': 'yt:$i'}];
      final p = planear(alarma(), hayRed: true, candidatas: muchas, descargada: desc({}), azar: Random(4));
      expect(p.pistas.map((x) => x['clave']).toSet(), muchas.map((x) => x['clave']).toSet());
      expect(p.pistas.map((x) => x['clave']).toList(), isNot(muchas.map((x) => x['clave']).toList()));
      expect(planear(alarma(fuente: FuenteAlarma.tono), hayRed: true, candidatas: [p1], descargada: desc({})).esTono,
          isTrue);
    });

    test('qué se deja listo en el teléfono', () {
      final lista = alarma(fuente: const FuenteAlarma(tipo: TipoFuente.lista, id: '1'));
      expect(pistaParaPreparar(lista, [p1, p2], desc({})), p1);
      expect(pistaParaPreparar(alarma(), [p1, p2], desc({'yt:2'})), p2); // me gusta: mejor una descargada
      expect(pistaParaPreparar(alarma(fuente: FuenteAlarma.tono), [p1], desc({})), isNull);
    });
  });

  group('control (Android)', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
      Plataforma.forzada = TargetPlatform.android;
    });
    tearDown(() => Plataforma.forzada = null);

    test('prepara la música: descargadas de «me gusta», baja la de una lista y pasa el respaldo', () async {
      final canal = _CanalFalso();
      final puerto = _PuertoFalso(gustan: [p1, local3], descargadas: {'local:3'});
      final c = ControlDespertador(canal: canal, reloj: () => mie);
      await c.iniciar(puerto);
      await c.poner(alarma(id: 'mg'));
      await c.poner(alarma(id: 'li', fuente: const FuenteAlarma(tipo: TipoFuente.lista, id: '1')));
      await c.poner(alarma(id: 'to', fuente: FuenteAlarma.tono));
      await c.sincronizar();
      final datos = canal.programados.last;
      final porId = {for (final a in datos['alarmas'] as List) a['id']: a};
      expect(porId['mg']['archivos'], [{'archivo': '/m/tres.mp3', 'titulo': 'Tres'}]);
      expect(puerto.bajados, contains('1')); // la primera de la lista no estaba: se bajó
      expect('${(porId['li']['archivos'] as List).single['archivo']}', endsWith('cancion_1.m4a'));
      expect(porId['to']['archivos'], isEmpty);
      expect(datos['respaldo'], [{'archivo': '/m/tres.mp3', 'titulo': 'Tres'}]);
      // antes de bajar nada ya se programó con lo que había (nunca queda una alarma sin sonar)
      expect(canal.programados.length, greaterThanOrEqualTo(2));
    });

    test('sin red no baja nada (suena el respaldo o el tono en Android)', () async {
      final canal = _CanalFalso();
      final puerto = _PuertoFalso(gustan: [p1], descargadas: {}, red: false);
      final c = ControlDespertador(canal: canal, reloj: () => mie);
      await c.iniciar(puerto);
      await c.poner(alarma(id: 'li', fuente: const FuenteAlarma(tipo: TipoFuente.lista, id: '1')));
      expect(puerto.bajados, isEmpty);
      expect((canal.programados.last['alarmas'] as List).single['archivos'], isEmpty);
    });

    test('adopta lo que Android cambió con la app cerrada', () async {
      SharedPreferences.setMockInitialValues({AlmacenAlarmas.clave: AlmacenAlarmas.codificar([alarma(id: 'u', dias: {})])});
      final canal = _CanalFalso()
        ..nativo = {
          'alarmas': [
            {'id': 'u', 'activa': false, 'pospuesta_hasta': 0}
          ]
        };
      final c = ControlDespertador(canal: canal, reloj: () => mie);
      await c.cargar();
      expect(c.alarma('u')!.activa, isFalse);
      expect((await AlmacenAlarmas.leer()).single.activa, isFalse);
    });

    test('«seguir escuchando» toca la música de la alarma en Caudal', () async {
      final canal = _CanalFalso()..seguir = 'li';
      final puerto = _PuertoFalso(gustan: [p1], descargadas: {});
      SharedPreferences.setMockInitialValues({AlmacenAlarmas.clave: AlmacenAlarmas.codificar(
          [alarma(id: 'li', fuente: const FuenteAlarma(tipo: TipoFuente.lista, id: '1'))])});
      final c = ControlDespertador(canal: canal, reloj: () => mie);
      await c.iniciar(puerto);
      await pumpEventQueue();
      expect(puerto.sonadas.single.map((p) => p['clave']), ['yt:1', 'yt:2']);
    });

    test('probar manda la alarma tal como está en el editor', () async {
      final canal = _CanalFalso();
      final c = ControlDespertador(canal: canal, reloj: () => mie);
      await c.iniciar(_PuertoFalso());
      await c.probar(alarma(id: 'nueva', hora: 5));
      expect(canal.probadas, ['nueva']);
      expect(canal.programados.last['prueba']['hora'], 5);
    });
  });

  group('control (sin alarma del sistema: suena con la app abierta)', () {
    late DateTime ahora;
    setUp(() {
      SharedPreferences.setMockInitialValues({});
      Plataforma.forzada = TargetPlatform.iOS;
      ahora = mie;
    });
    tearDown(() => Plataforma.forzada = null);

    test('suena a su hora, sube el volumen, pospone y devuelve el volumen', () async {
      final puerto = _PuertoFalso(gustan: [p1, p2], descargadas: {});
      final c = ControlDespertador(canal: const CanalDespertador(), reloj: () => ahora);
      await c.iniciar(puerto);
      await c.poner(alarma(id: 'x', hora: 6, minuto: 1, dias: {}, volumen: 80, subida: 60));
      ahora = mie.add(const Duration(seconds: 70));
      c.mirar();
      await pumpEventQueue();
      expect(c.sonando.value?.alarma.id, 'x');
      expect(puerto.sonadas, hasLength(1));
      expect(puerto.volumenes.first, lessThanOrEqualTo(3)); // casi en silencio
      ahora = ahora.add(const Duration(seconds: 61));
      await c.pasoVolumen();
      expect(puerto.volumen, closeTo(80, 0.01));
      await c.posponer();
      expect(c.sonando.value, isNull);
      expect(puerto.volumen, 55); // el de antes
      expect(c.alarma('x')!.pospuestaHasta, greaterThan(ahora.millisecondsSinceEpoch));
    });

    test('sin red ni descargas: el sonido suave; apagar la de una vez la apaga', () async {
      final puerto = _PuertoFalso(gustan: [p1], descargadas: {}, red: false);
      final c = ControlDespertador(canal: const CanalDespertador(), reloj: () => ahora);
      await c.iniciar(puerto);
      final a = alarma(id: 'y', dias: {}, fuente: const FuenteAlarma(tipo: TipoFuente.cancion, id: 'yt:1', pista: p1));
      await c.poner(a);
      await c.sonarEnApp(a);
      expect(c.sonando.value!.tono, isTrue);
      expect(puerto.sonadas, isEmpty);
      await c.apagar();
      expect(c.alarma('y')!.activa, isFalse);
    });

    test('apagar y seguir: la música sigue', () async {
      final puerto = _PuertoFalso(gustan: [p1], descargadas: {});
      final c = ControlDespertador(canal: const CanalDespertador(), reloj: () => ahora);
      await c.iniciar(puerto);
      final a = alarma(id: 'z', dias: {1});
      await c.poner(a);
      await c.sonarEnApp(a);
      await c.apagar(seguir: true);
      expect(puerto.detenido, 0);
      expect(puerto.volumen, 55);
      expect(c.alarma('z')!.activa, isTrue);
    });

    test('una prueba no toca lo guardado', () async {
      final puerto = _PuertoFalso(gustan: [p1], descargadas: {});
      final c = ControlDespertador(canal: const CanalDespertador(), reloj: () => ahora);
      await c.iniciar(puerto);
      final a = alarma(id: 'w', dias: {});
      await c.poner(a);
      await c.probar(a);
      await c.apagar();
      expect(c.alarma('w')!.activa, isTrue);
      expect(puerto.detenido, 1);
    });
  });
}

class _CanalFalso extends CanalDespertador {
  final programados = <Map<String, dynamic>>[];
  final probadas = <String>[];
  Map<String, dynamic>? nativo;
  String? seguir;

  @override
  bool get disponible => true;

  @override
  Future<void> programar(Map<String, dynamic> datos) async => programados.add(datos);

  @override
  Future<Map<String, dynamic>?> leer() async => nativo;

  @override
  Future<PermisosDespertador> permisos() async => const PermisosDespertador();

  @override
  Future<void> probar(String id) async => probadas.add(id);

  @override
  Future<String?> consumirSeguir() async {
    final s = seguir;
    seguir = null;
    return s;
  }
}

class _PuertoFalso implements PuertoDespertador {
  _PuertoFalso({this.gustan = const [], this.descargadas = const {}, this.red = true});

  final List<J> gustan;
  final Set<String> descargadas;
  final bool red;
  final bajados = <String>[];
  final sonadas = <List<J>>[];
  final volumenes = <double>[];
  double _vol = 55;
  int detenido = 0;

  @override
  Future<List<J>> candidatas(FuenteAlarma f) async => switch (f.tipo) {
        TipoFuente.meGusta => gustan,
        TipoFuente.lista => [p1, p2],
        TipoFuente.cancion => [if (f.pista != null) f.pista!],
        _ => <J>[],
      };

  @override
  Future<List<J>> respaldo() async => gustan.where((p) => descargadas.contains(p['clave'])).toList();

  @override
  bool descargada(J pista) => descargadas.contains(pista['clave']);

  @override
  String? archivoDe(J pista) => descargada(pista) ? '${pista['archivo']}' : null;

  @override
  bool get hayRed => red;

  @override
  Future<void> sonar(List<J> pistas, {required String titulo}) async => sonadas.add(pistas);

  @override
  Future<void> fijarVolumen(double v) async {
    _vol = v;
    volumenes.add(v);
  }

  @override
  double get volumen => _vol;

  @override
  Future<void> detener() async => detenido++;

  @override
  Future<String?> bajarAudio(String videoId, String destino) async {
    bajados.add(videoId);
    return '$destino.m4a';
  }

  @override
  Future<String?> carpeta() async => '/cache';
}
