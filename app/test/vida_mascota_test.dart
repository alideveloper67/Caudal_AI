// La vida de las mascotas: paso según el ritmo, sueño tras 2 minutos en pausa y gorrito de fiesta.
import 'package:caudal/nucleo/ritmo.dart';
import 'package:caudal/nucleo/vida_mascota.dart';
import 'package:caudal/nucleo/estilo_reproductor.dart' show EstiloReproductor;
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/reproductor/mascota_vida.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

class _R extends ChangeNotifier implements Reproductor {
  @override
  EstadoRepro estado = EstadoRepro.sonando;
  @override
  double velocidad = 1;

  void poner(EstadoRepro e) {
    estado = e;
    notifyListeners();
  }

  @override
  Future<void> dispose() async => super.dispose();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  group('paso al ritmo de la canción', () {
    test('sin ritmo conocido camina al paso de siempre', () {
      expect(pasoDeMascota(null), pasoNormal);
      expect(pasoDeMascota(const AnalisisRitmo(bpm: 0)), pasoNormal);
    });

    test('más rápida en canciones rápidas y más lenta en las lentas', () {
      final rapida = pasoDeMascota(const AnalisisRitmo(bpm: 170));
      final media = pasoDeMascota(const AnalisisRitmo(bpm: 110));
      final lenta = pasoDeMascota(const AnalisisRitmo(bpm: 70));
      expect(media, pasoNormal);
      expect(rapida, lessThan(media));
      expect(lenta, greaterThan(media));
    });

    test('nunca pasa de los extremos (equipos viejos) y sigue la velocidad de reproducción', () {
      expect(pasoDeMascota(const AnalisisRitmo(bpm: 240)), greaterThanOrEqualTo(pasoMasRapido));
      expect(pasoDeMascota(const AnalisisRitmo(bpm: 40)), lessThanOrEqualTo(pasoMasLento));
      expect(pasoDeMascota(null, velocidad: 1.5), lessThan(pasoNormal));
      expect(pasoDeMascota(null, velocidad: 0.5), greaterThan(pasoNormal));
    });
  });

  group('sueño', () {
    test('se duerme a los 2 minutos en pausa, no antes', () {
      final inicio = DateTime(2026, 5, 1, 12);
      expect(estaDormida(null, inicio), isFalse);
      expect(estaDormida(inicio, inicio.add(const Duration(minutes: 1, seconds: 59))), isFalse);
      expect(estaDormida(inicio, inicio.add(const Duration(minutes: 2))), isTrue);
    });

    testWidgets('VidaMascota: en pausa se duerme a los 2 min y al sonar despierta', (t) async {
      final r = _R();
      final v = VidaMascota(r: r, cuadros: 2)..iniciar();
      expect(v.dormida, isFalse);
      r.poner(EstadoRepro.pausa);
      await t.pump(const Duration(minutes: 1, seconds: 59));
      expect(v.dormida, isFalse);
      await t.pump(const Duration(seconds: 2));
      expect(v.dormida, isTrue);
      expect(v.cuadro, 0);
      // las «z» se mueven mientras duerme
      final antes = v.fotoSueno;
      await t.pump(const Duration(milliseconds: 750));
      expect(v.fotoSueno, isNot(antes));
      r.poner(EstadoRepro.sonando);
      expect(v.dormida, isFalse);
      v.dispose();
    });

    testWidgets('una pausa corta no la duerme: volver a sonar reinicia la cuenta', (t) async {
      final r = _R();
      final v = VidaMascota(r: r, cuadros: 2)..iniciar();
      r.poner(EstadoRepro.pausa);
      await t.pump(const Duration(minutes: 1));
      r.poner(EstadoRepro.sonando);
      r.poner(EstadoRepro.pausa);
      await t.pump(const Duration(minutes: 1, seconds: 30));
      expect(v.dormida, isFalse);
      await t.pump(const Duration(seconds: 31));
      expect(v.dormida, isTrue);
      v.dispose();
    });

    testWidgets('cargando la siguiente no cuenta como pausa', (t) async {
      final r = _R();
      final v = VidaMascota(r: r, cuadros: 2)..iniciar();
      r.poner(EstadoRepro.pausa);
      await t.pump(const Duration(minutes: 1, seconds: 50));
      r.poner(EstadoRepro.cargando);
      await t.pump(const Duration(minutes: 3));
      expect(v.dormida, isFalse);
      v.dispose();
    });
  });

  group('pasos', () {
    testWidgets('camina solo mientras suena y se detiene (y vuelve al primer cuadro) en pausa', (t) async {
      final r = _R();
      final v = VidaMascota(r: r, cuadros: 2)..iniciar();
      await t.pump(pasoNormal * 3 + const Duration(milliseconds: 10));
      expect(v.pasos, 3);
      r.poner(EstadoRepro.pausa);
      await t.pump(const Duration(seconds: 1));
      expect(v.pasos, 3);
      expect(v.cuadro, 0);
      v.dispose();
    });

    testWidgets('en una canción rápida da más pasos que en una lenta', (t) async {
      Future<int> pasosEn(double bpm) async {
        final r = _R();
        final v = VidaMascota(r: r, cuadros: 2, ritmoDe: () => AnalisisRitmo(bpm: bpm))..iniciar();
        await t.pump(const Duration(seconds: 3));
        final n = v.pasos;
        v.dispose();
        return n;
      }

      final rapida = await pasosEn(180);
      final lenta = await pasosEn(70);
      expect(rapida, greaterThan(lenta));
    });

    testWidgets('con «quitar animaciones» o fuera de pantalla no corre ningún reloj de pasos', (t) async {
      final r = _R();
      final v = VidaMascota(r: r, cuadros: 2)..iniciar();
      v.ajustar(visible: true, quieto: true);
      await t.pump(const Duration(seconds: 2));
      expect(v.pasos, 0);
      v.ajustar(visible: false, quieto: false);
      await t.pump(const Duration(seconds: 2));
      expect(v.pasos, 0);
      v.ajustar(visible: true, quieto: false);
      await t.pump(const Duration(seconds: 1));
      expect(v.pasos, greaterThan(0));
      v.dispose();
    });
  });

  group('fiestas', () {
    test('Navidad y Año Nuevo tienen gorrito; el resto del año no', () {
      expect(fiestaDe(DateTime(2026, 12, 24)), Fiesta.navidad);
      expect(fiestaDe(DateTime(2026, 12, 20)), Fiesta.navidad);
      expect(fiestaDe(DateTime(2026, 12, 26)), Fiesta.navidad);
      expect(fiestaDe(DateTime(2026, 12, 31)), Fiesta.anioNuevo);
      expect(fiestaDe(DateTime(2027, 1, 1)), Fiesta.anioNuevo);
      expect(fiestaDe(DateTime(2027, 1, 2)), Fiesta.anioNuevo);
      expect(fiestaDe(DateTime(2027, 1, 3)), Fiesta.ninguna);
      expect(fiestaDe(DateTime(2026, 12, 19)), Fiesta.ninguna);
      expect(fiestaDe(DateTime(2026, 6, 15)), Fiesta.ninguna);
    });
  });

  test('los estilos de donadores son tres y Clásico y Vinilo siguen libres', () {
    expect([for (final e in EstiloReproductor.values) if (e.soloDonadores) e],
        [EstiloReproductor.casete, EstiloReproductor.neon, EstiloReproductor.flotante]);
  });
}
