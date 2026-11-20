// Logros (nucleo/logros.dart y logros_vigia.dart): rachas, horas, canciones y artistas, listas,
// me gusta, salas con amigos, horarios, vitrina, guardado, mezcla con la nube, lo escuchado antes
// (desde la base de la colección) y el vigía que cuenta lo que suena.
import 'dart:convert';
import 'dart:io';

import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/logros.dart';
import 'package:caudal/nucleo/logros_dibujos.dart';
import 'package:caudal/nucleo/logros_vigia.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

DateTime _t(String s) => DateTime.parse(s);

Logros _nuevo([String ahora = '2026-11-10 12:00']) =>
    Logros.enMemoria(plataforma: 'android', reloj: () => _t(ahora));

class _NubeFalsa extends Sesion {
  _NubeFalsa({this.respuesta, this.falla = false}) : super('u1', 'a', 'r', DateTime.now().add(const Duration(hours: 1)));
  final Object? respuesta;
  final bool falla;
  final llamadas = <(String, Map<String, dynamic>)>[];

  @override
  Future<dynamic> rpc(String nombre, [Map<String, dynamic> parametros = const {}]) async {
    llamadas.add((nombre, parametros));
    if (falla) throw const SinConexion();
    return respuesta;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('al menos 20 logros, cada uno con su dibujo de 24x24', () {
    expect(catalogoLogros.length, greaterThanOrEqualTo(20));
    expect(logroPorId.length, catalogoLogros.length);
    final cats = {for (final (c, _) in categoriasLogros) c};
    for (final l in catalogoLogros) {
      expect(cats, contains(l.categoria));
      final (paleta, filas) = dibujosLogros[l.id]!;
      expect(filas, hasLength(ladoDibujoLogro), reason: l.id);
      for (final f in filas) {
        expect(f.length, ladoDibujoLogro);
        for (final s in f.split('')) {
          expect(s == '.' || paleta.containsKey(s), isTrue, reason: '${l.id}: $s');
        }
      }
    }
  });

  test('rachas', () {
    expect(rachaMasLarga(['2026-01-01', '2026-01-02', '2026-01-04', '2026-01-05', '2026-01-06', 'x']), 3);
    expect(rachaMasLarga(['2026-02-28', '2026-03-01']), 2); // cruzando de mes
    expect(rachaMasLarga([]), 0);
    final dias = ['2026-11-08', '2026-11-09', '2026-11-10'];
    expect(rachaEnCurso(dias, DateTime(2026, 11, 10)), 3);
    expect(rachaEnCurso(dias, DateTime(2026, 11, 11)), 3); // hoy aún no: sigue viva
    expect(rachaEnCurso(dias, DateTime(2026, 11, 12)), 0);
  });

  test('un día cuenta con un minuto; 7 días seguidos dan las rachas de 3 y 7', () {
    final lg = _nuevo();
    lg.anotarSegundos(30, cuando: _t('2026-11-10 10:00'));
    expect(lg.dias, isEmpty);
    lg.anotarSegundos(30, cuando: _t('2026-11-10 10:01'));
    expect(lg.dias, contains('2026-11-10'));
    for (var d = 1; d <= 7; d++) {
      lg.anotarSegundos(120, cuando: _t('2026-11-0$d 20:00'));
    }
    final ids = lg.revisar().map((l) => l.id).toSet();
    expect(ids.containsAll({'racha_3', 'racha_7'}), isTrue);
    expect(ids.contains('racha_30'), isFalse);
  });

  test('horas y maratón (solo en un mismo día)', () {
    final lg = _nuevo();
    for (var i = 0; i < 240; i++) {
      lg.anotarSegundos(60, cuando: _t('2026-11-10 15:00'));
    }
    expect(lg.revisar().map((l) => l.id).toSet().containsAll({'horas_1', 'maraton'}), isTrue);
    expect(lg.progreso(logroPorId['horas_10']!).$1, 4);
    final otro = _nuevo();
    for (var d = 1; d <= 4; d++) {
      otro.anotarSegundos(3600, cuando: _t('2026-11-0$d 15:00'));
    }
    expect(otro.valor('horas'), 4);
    expect(otro.valor('dia_horas'), 1);
  });

  test('canciones y artistas distintos, noche y madrugada', () {
    final lg = _nuevo();
    lg.anotarPista({'clave': 'yt:a', 'artistas': [{'id': '1', 'nombre': 'Bad Bunny'}]});
    lg.anotarPista({'clave': 'yt:a', 'artistas': [{'id': '1', 'nombre': 'Bad Bunny'}]});
    lg.anotarPista({'clave': 'yt:b', 'artista': 'Karol G, BAD BUNNY'});
    expect(lg.contadores['canciones'], 2);
    expect(lg.contadores['artistas'], 2);
    for (var i = 0; i < 10; i++) {
      lg.anotarCancion('n$i', const [], cuando: _t('2026-11-10 02:30'));
      lg.anotarCancion('m$i', const [], cuando: _t('2026-11-10 06:15'));
    }
    final ids = lg.revisar().map((l) => l.id).toSet();
    expect(ids.containsAll({'primera_nota', 'noctambulo', 'madrugador'}), isTrue);
  });

  test('los totales nunca bajan y las salas cuentan una vez y con alguien más', () {
    final lg = _nuevo();
    lg.anotarListas(5);
    lg.anotarListas(2);
    lg.anotarMeGusta(30);
    lg.anotarDescargas(25);
    expect(lg.contadores['listas'], 5);
    lg.anotarSala('ABC|yo', conAmigos: false);
    expect(lg.contadores['juntos'], 0);
    lg.anotarSala('ABC|yo', conAmigos: true, soyAnfitrion: true);
    lg.anotarSala('ABC|yo', conAmigos: true, soyAnfitrion: true);
    expect(lg.contadores['juntos'], 1);
    final ids = lg.revisar().map((l) => l.id).toSet();
    expect(ids.containsAll({'lista_1', 'lista_5', 'gusta_25', 'descargas_25', 'juntos_1', 'anfitrion'}), isTrue);
  });

  test('dos mundos (computadora + teléfono) y vitrina llena', () {
    final lg = _nuevo();
    expect(lg.valor('dispositivos'), 1);
    lg.mezclar({'plataformas': ['web']});
    expect(lg.valor('dispositivos'), 1);
    lg.mezclar({'plataformas': ['windows']});
    expect(lg.valor('dispositivos'), 2);
    lg.anotarListas(20);
    lg.anotarMeGusta(250);
    lg.anotarDescargas(30);
    for (var i = 0; i < 1100; i++) {
      lg.anotarCancion('c$i', ['a$i'], cuando: _t('2026-11-10 03:00'));
    }
    lg.anotarSala('X|1', conAmigos: true, soyAnfitrion: true);
    expect(lg.revisar().map((l) => l.id), contains('coleccionista'));
  });

  test('vitrina: solo conseguidos, sin repetir y hasta 3', () {
    final lg = _nuevo();
    var avisos = 0;
    lg.addListener(() => avisos++);
    expect(lg.alternarVitrina('racha_7'), isFalse);
    lg.anotarListas(20);
    lg.anotarMeGusta(250);
    lg.revisar();
    for (final i in ['lista_1', 'lista_5', 'lista_15']) {
      expect(lg.alternarVitrina(i), isTrue);
    }
    expect(lg.alternarVitrina('gusta_25'), isFalse);
    expect(lg.alternarVitrina('lista_5'), isTrue);
    expect(lg.vitrina, ['lista_1', 'lista_15']);
    expect(lg.ponerVitrina(['gusta_25', 'gusta_25', 'no_existe', 'lista_1', 'lista_5']), ['gusta_25', 'lista_1', 'lista_5']);
    expect(avisos, greaterThan(3));
  });

  test('se guarda en el dispositivo y se recupera; un guardado roto no rompe', () async {
    final lg = await Logros.abrir('c1', plataforma: 'ios');
    lg.anotarSegundos(4000);
    lg.anotarPista({'clave': 'yt:a'});
    lg.revisar();
    lg.alternarVitrina('horas_1');
    lg.guardar(ya: true);
    await Future<void>.delayed(const Duration(milliseconds: 20));
    final otro = await Logros.abrir('c1', plataforma: 'ios');
    expect(otro.contadores['segundos'], 4000);
    expect(otro.claves, contains('yt:a'));
    expect(otro.vitrina, ['horas_1']);
    expect(otro.plataformas, {'ios'});
    SharedPreferences.setMockInitialValues({'logros_c2': '{roto', 'logros_c3': jsonEncode({
      'contadores': {'segundos': 'mucho'}, 'desbloqueados': {'inventado': 1}})});
    expect((await Logros.abrir('c2')).contadores['segundos'], 0);
    final c3 = await Logros.abrir('c3');
    expect(c3.contadores['segundos'], 0);
    expect(c3.desbloqueados, isEmpty);
  });

  test('para la nube y mezclar: nunca baja nada', () {
    final lg = _nuevo();
    lg.anotarSegundos(7200);
    lg.revisar();
    final d = lg.paraNube();
    expect(d.keys.toSet(), {'p_contadores', 'p_dias', 'p_plataformas', 'p_desbloqueados', 'p_vitrina'});
    expect(jsonEncode(d).contains('claves'), isFalse);
    final fecha = lg.desbloqueados['horas_1']!;
    lg.mezclar({
      'contadores': {'segundos': 100, 'canciones': 300},
      'dias': ['2026-11-09'],
      'plataformas': ['windows'],
      'desbloqueados': {'horas_1': fecha - 50, 'racha_3': 5},
      'vitrina': ['racha_3', 'inventado'],
    });
    expect(lg.contadores['segundos'], 7200);
    expect(lg.contadores['canciones'], 300);
    expect(lg.desbloqueados['horas_1'], fecha - 50);
    expect(lg.vitrina, ['racha_3']);
  });

  test('sincronizar y la vitrina de otra persona', () async {
    final lg = _nuevo()..anotarListas(1);
    expect(await lg.sincronizar(null), isFalse);
    expect(await lg.sincronizar(_NubeFalsa(falla: true)), isFalse);
    expect(lg.pendienteNube, isTrue);
    final n = _NubeFalsa(respuesta: {'contadores': {'juntos': 3}, 'plataformas': ['windows']});
    expect(await lg.sincronizar(n), isTrue);
    expect(n.llamadas.single.$1, 'logros_guardar');
    expect(lg.contadores['juntos'], 3);
    expect(lg.pendienteNube, isFalse);

    final v = await vitrinaDe(_NubeFalsa(respuesta: {'vitrina': ['racha_7', 'inventado'], 'total': '4', 'fechas': {'racha_7': 1}}), 'ana');
    expect(v!.vitrina, ['racha_7']);
    expect(v.total, 4);
    expect(await vitrinaDe(_NubeFalsa(respuesta: null), 'ana'), isNull);
    expect(await vitrinaDe(_NubeFalsa(falla: true), 'ana'), isNull);
  });

  group('vigía', () {
    test('cuenta lo que suena (una canción, tras 20 s) y avisa', () {
      var ahora = _t('2026-11-10 12:00:00');
      final lg = Logros.enMemoria(reloj: () => ahora);
      final repro = ValueNotifier<Map<String, dynamic>?>(null);
      var suena = false;
      final avisos = <List<Logro>>[];
      final v = VigiaLogros(
        logros: lg, reproductor: repro, suena: () => suena, actual: () => repro.value,
        alConseguir: avisos.add, reloj: () => ahora,
      )..iniciar(importar: false);
      addTearDown(v.detener);
      expect(VigiaLogros.vigente, same(v));
      suena = true;
      repro.value = {'clave': 'yt:a', 'artistas': [{'nombre': 'A'}]};
      for (var i = 0; i < 3; i++) {
        ahora = ahora.add(const Duration(seconds: 5));
        v.contar();
      }
      expect(lg.contadores['segundos'], 15);
      expect(lg.contadores['canciones'], 0);
      ahora = ahora.add(const Duration(seconds: 5));
      v.contar();
      expect(lg.contadores['canciones'], 1);
      expect(avisos.single.single.id, 'primera_nota');
      // en pausa no cuenta y un salto largo no suma de más
      suena = false;
      ahora = ahora.add(const Duration(minutes: 10));
      v.contar();
      suena = true;
      ahora = ahora.add(const Duration(hours: 1));
      v.contar();
      expect(lg.contadores['segundos'], 20 + 15);
    });

    test('salas de «Escuchar juntos»', () {
      final lg = Logros.enMemoria();
      final v = VigiaLogros(logros: lg, reproductor: ValueNotifier(0), suena: () => false, actual: () => null)
        ..iniciar(importar: false);
      addTearDown(v.detener);
      v.anotarSala('ABC123', 'yo', 1, true);
      expect(lg.contadores['juntos'], 0);
      v.anotarSala('ABC123', 'yo', 2, true);
      v.anotarSala('ABC123', 'yo', 3, true);
      expect(lg.contadores['juntos'], 1);
      expect(lg.conseguido('anfitrion'), isTrue);
    });

    test('lo escuchado antes y los totales salen de la base de la colección', () async {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
      final tmp = Directory.systemTemp.createTempSync('logros_');
      addTearDown(() => tmp.deleteSync(recursive: true));
      final col = await Coleccion.abrirEn('${tmp.path}/c.db');
      addTearDown(col.cerrar);
      final base = DateTime(2026, 11, 3, 2).millisecondsSinceEpoch / 1000;
      await col.db.insert('pistas', {'clave': 'yt:a', 'datos': jsonEncode({'clave': 'yt:a', 'artistas': [{'nombre': 'A'}]})});
      for (var d = 0; d < 3; d++) {
        await col.db.insert('reproducciones', {'clave': 'yt:a', 'fecha': base - d * 86400});
      }
      await col.db.insert('reproducciones', {'clave': 'yt:b', 'fecha': base + 3600 * 10});
      for (var i = 0; i < 5; i++) {
        await col.crearLista('Lista $i');
      }
      final lg = Logros.enMemoria();
      final n = _NubeFalsa(respuesta: {'contadores': {}, 'plataformas': ['windows']});
      final v = VigiaLogros(
          logros: lg, reproductor: ValueNotifier(0), suena: () => false, actual: () => null, coleccion: col, sesion: n)
        ..iniciar(importar: false);
      addTearDown(v.detener);
      await v.importarLoDeAntes();
      expect(lg.importado, isTrue);
      expect(lg.contadores['canciones'], 2);
      expect(lg.contadores['artistas'], 1);
      expect(lg.contadores['noche'], 3);
      expect(lg.contadores['listas'], 5);
      expect(lg.conseguido('racha_3'), isTrue);
      expect(lg.conseguido('lista_5'), isTrue);
      expect(n.llamadas.first.$1, 'logros_guardar');
      expect(lg.conseguido('dos_mundos'), isTrue); // la nube dijo que también se usó en Windows
    });
  });
}
