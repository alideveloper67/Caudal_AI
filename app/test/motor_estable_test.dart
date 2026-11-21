// El motor estable de la 2.7.6: freno de recargas, vigía del proceso, elección del motor y
// diagnóstico del arranque. Todo lógica pura: se prueba sin teléfono.

import 'package:caudal/nucleo/diagnostico.dart';
import 'package:caudal/reproduccion/guarda_recargas.dart';
import 'package:caudal/reproduccion/motor_eleccion.dart';
import 'package:caudal/reproduccion/vigia_proceso.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('GuardaRecargas', () {
    late DateTime ahora;
    GuardaRecargas nuevo() => GuardaRecargas(reloj: () => ahora);
    setUp(() => ahora = DateTime(2026, 11, 21, 12));

    test('reintenta 3 veces con esperas que crecen y luego salta', () {
      final g = nuevo();
      final d1 = g.decidir('a');
      final d2 = g.decidir('a');
      final d3 = g.decidir('a');
      expect([d1.accion, d2.accion, d3.accion], everyElement(Recarga.reintentar));
      expect([d1.espera, d2.espera, d3.espera],
          [const Duration(milliseconds: 700), const Duration(milliseconds: 1400), const Duration(milliseconds: 2800)]);
      expect([d1.intento, d2.intento, d3.intento], [1, 2, 3]);
      expect(g.decidir('a').accion, Recarga.saltar);
    });

    test('una canción que falla siempre en el mismo punto NO se recarga sin fin', () {
      // el bucle de antes: suena 21 s, falla, recarga, suena 21 s, falla… y el contador se reiniciaba
      final g = nuevo();
      var recargas = 0;
      for (var vuelta = 0; vuelta < 50; vuelta++) {
        final d = g.decidir('a');
        if (d.accion != Recarga.reintentar) break;
        recargas++;
        ahora = ahora.add(const Duration(seconds: 60));
        // vuelve a sonar bien un buen rato tras cada recarga (la tanda se renueva)
        g.sonando(const Duration(seconds: 10));
        g.sonando(const Duration(seconds: 70));
      }
      expect(recargas, g.porCancion);
      expect(g.decidir('a').accion, Recarga.saltar);
    });

    test('sonar bien un rato da otra tanda, pero el tope por canción no se renueva', () {
      final g = nuevo();
      for (var i = 0; i < 3; i++) {
        g.decidir('a');
      }
      expect(g.decidir('a').accion, Recarga.saltar);
      g.sonando(const Duration(seconds: 5));
      g.sonando(const Duration(seconds: 51));
      expect(g.decidir('a').accion, Recarga.reintentar);
      expect(g.recargasCancion, 4);
    });

    test('una canción nueva empieza de cero; el tope global no', () {
      final g = nuevo();
      for (var i = 0; i < 3; i++) {
        g.decidir('a');
      }
      g.nuevaCancion('b');
      expect(g.tanda, 0);
      expect(g.decidir('b').accion, Recarga.reintentar);
    });

    test('elegir otra vez la misma canción la deja empezar de cero', () {
      final g = nuevo();
      for (var i = 0; i < 3; i++) {
        g.decidir('a');
      }
      g.nuevaCancion('a', forzar: true);
      expect(g.decidir('a').accion, Recarga.reintentar);
    });

    test('muchas recargas en un minuto entre varias canciones → frenar, y al pasar el minuto se libera', () {
      final g = nuevo();
      var n = 0;
      for (final c in ['a', 'b', 'c', 'd', 'e']) {
        for (var i = 0; i < 3; i++) {
          if (g.decidir(c).accion == Recarga.reintentar) n++;
        }
      }
      expect(n, g.porMinuto);
      expect(g.decidir('f').accion, Recarga.frenar);
      ahora = ahora.add(const Duration(minutes: 1, seconds: 1));
      expect(g.decidir('f').accion, Recarga.reintentar);
    });

    test('buscar hacia atrás no cuenta como «sonó bien»', () {
      final g = nuevo();
      g.decidir('a');
      g.sonando(const Duration(seconds: 100));
      g.sonando(const Duration(seconds: 10)); // buscó al principio
      g.sonando(const Duration(seconds: 30));
      expect(g.tanda, 1);
      g.sonando(const Duration(seconds: 56));
      expect(g.tanda, 0);
    });
  });

  group('VigiaProceso', () {
    late DateTime ahora;
    setUp(() => ahora = DateTime(2026, 11, 21, 12));
    MuestraProceso m(int mapas, {int hilos = 150, int rssMb = 300}) =>
        MuestraProceso(mapas: mapas, hilos: hilos, rssKb: rssMb * 1024);

    test('un proceso normal no hace nada', () {
      final v = VigiaProceso(reloj: () => ahora);
      for (var i = 0; i < 30; i++) {
        ahora = ahora.add(const Duration(seconds: 20));
        expect(v.mirar(m(6000 + i * 10)).$1, AccionVigia.nada);
      }
    });

    test('demasiados mapas → renovar; si vuelve a pasar pronto → respaldo', () {
      final v = VigiaProceso(reloj: () => ahora);
      expect(v.mirar(m(VigiaProceso.topeMapas)).$1, AccionVigia.renovar);
      ahora = ahora.add(const Duration(minutes: 2));
      expect(v.mirar(m(VigiaProceso.topeMapas + 10)).$1, AccionVigia.respaldo);
    });

    test('si vuelve a pasar mucho después, solo renueva otra vez', () {
      final v = VigiaProceso(reloj: () => ahora);
      v.mirar(m(VigiaProceso.topeMapas));
      ahora = ahora.add(VigiaProceso.reincidencia + const Duration(minutes: 1));
      expect(v.mirar(m(VigiaProceso.topeMapas)).$1, AccionVigia.renovar);
    });

    test('crecer muy rápido también cuenta aunque no llegue al tope', () {
      final v = VigiaProceso(reloj: () => ahora);
      expect(v.mirar(m(8000)).$1, AccionVigia.nada);
      ahora = ahora.add(const Duration(seconds: 60));
      final (a, por) = v.mirar(m(8000 + VigiaProceso.crecimientoMapas));
      expect(a, AccionVigia.renovar);
      expect(por, contains('crecen'));
    });

    test('hilos y memoria también tienen tope', () {
      expect(VigiaProceso(reloj: () => ahora).mirar(m(5000, hilos: VigiaProceso.topeHilos)).$1, AccionVigia.renovar);
      expect(VigiaProceso(reloj: () => ahora).mirar(m(5000, rssMb: 1600)).$1, AccionVigia.renovar);
    });

    test('muestras que no se pudieron leer se ignoran', () {
      expect(MuestraProceso.de(null), isNull);
      expect(MuestraProceso.de({'mapas': -1, 'hilos': -1, 'rss_kb': -1}), isNull);
      expect(MuestraProceso.de({'mapas': 5000, 'hilos': 120, 'rss_kb': 300000})!.mapas, 5000);
    });
  });

  group('EleccionMotor.decidir', () {
    final ahora = DateTime(2026, 11, 21, 12);
    const honor = "SIGABRT Scudo ERROR: internal map failure (NO MEMORY) requesting 4KB CodecLooper /lib/arm64/libmpv.so";

    (MotorSonido, String, String?) d({String ajuste = 'automatico', String? respaldoEn, List<FalloNativo> fallos = const [],
            bool android = true}) =>
        EleccionMotor.decidir(
            ajuste: ajuste, version: '2.7.6', respaldoEn: respaldoEn, fallos: fallos, ahora: ahora, android: android);

    test('sin fallos: el de Caudal', () {
      expect(d().$1, MotorSonido.caudal);
    });

    test('un cierre del motor con esta versión: el de Android y se recuerda la versión', () {
      final r = d(fallos: [FalloNativo(ahora.subtract(const Duration(hours: 1)), honor)]);
      expect(r.$1, MotorSonido.android);
      expect(r.$3, '2.7.6');
    });

    test('ya en respaldo con esta versión: sigue en el de Android aunque no haya fallos nuevos', () {
      expect(d(respaldoEn: '2.7.6').$1, MotorSonido.android);
    });

    test('llegó otra versión: se vuelve a probar el de Caudal', () {
      final r = d(respaldoEn: '2.7.5');
      expect(r.$1, MotorSonido.caudal);
      expect(r.$3, isNull);
    });

    test('un fallo nativo que no es del motor no cambia nada', () {
      expect(d(fallos: [FalloNativo(ahora, 'SIGSEGV libsqlite3.so')]).$1, MotorSonido.caudal);
    });

    test('un fallo viejo (más de 3 días) no cuenta', () {
      expect(d(fallos: [FalloNativo(ahora.subtract(const Duration(days: 4)), honor)]).$1, MotorSonido.caudal);
    });

    test('lo elegido a mano manda', () {
      expect(d(ajuste: 'caudal', respaldoEn: '2.7.6', fallos: [FalloNativo(ahora, honor)]).$1, MotorSonido.caudal);
      expect(d(ajuste: 'android').$1, MotorSonido.android);
    });

    test('fuera de Android siempre el de Caudal', () {
      expect(d(ajuste: 'android', android: false).$1, MotorSonido.caudal);
    });

    test('los dos fallos reales de la 2.7.5 se reconocen como del motor', () {
      expect(FalloNativo(_fecha, honor).delMotor, isTrue);
      expect(FalloNativo(ahora, 'pthread_cond_timedwait /lib/arm64/libmpv.so').delMotor, isTrue);
    });
  });

  group('clasificarArranque', () {
    test('un cierre del motor no es una traba', () {
      expect(clasificarArranque('fallo_nativo', 'en_pantalla', 'Scudo ERROR NO MEMORY CodecLooper libmpv.so'),
          TipoArranque.cierreMotor);
    });

    test('un ANR o un fallo de Java sí es traba', () {
      expect(clasificarArranque('anr', 'en_pantalla', ''), TipoArranque.traba);
      expect(clasificarArranque('fallo_java', 'en_pantalla', ''), TipoArranque.traba);
    });

    test('sin datos de Android (Android 10 o menos): como siempre, traba', () {
      expect(clasificarArranque('', '', ''), TipoArranque.traba);
    });

    test('actualizar la app o que Android la cierre de fondo no cuenta', () {
      expect(clasificarArranque('paquete_actualizado', 'en_pantalla', ''), TipoArranque.noCuenta);
      expect(clasificarArranque('poca_memoria', 'en_segundo_plano', ''), TipoArranque.noCuenta);
      expect(clasificarArranque('usuario_detuvo', 'servicio', ''), TipoArranque.noCuenta);
    });

    test('cerrarla a la fuerza estando a la vista sin dibujarse sí es traba', () {
      expect(clasificarArranque('usuario', 'en_pantalla', ''), TipoArranque.traba);
    });

    test('un fallo nativo que no es del motor sigue siendo traba (modo seguro)', () {
      expect(clasificarArranque('fallo_nativo', 'en_pantalla', 'SIGSEGV libsqlite3.so'), TipoArranque.traba);
    });
  });
}

final _fecha = DateTime(2026, 11, 21);
