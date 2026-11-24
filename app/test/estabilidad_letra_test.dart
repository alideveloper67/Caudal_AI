// Pruebas de la 2.7.5: cortes de red, cierres de Android, aviso de batería y aspecto de la letra.

import 'package:caudal/nucleo/salidas_android.dart';
import 'package:caudal/reproduccion/reproductor.dart';
import 'package:caudal/ui/aviso_bateria.dart';
import 'package:caudal/ui/reproductor/letra_aspecto.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('corte de red', () {
    test('una canción por internet que acaba a mitad es un corte', () {
      expect(
          esCorteDeRed(local: false, posicion: const Duration(seconds: 70), duracion: const Duration(minutes: 3)),
          isTrue);
    });
    test('el final de verdad no es un corte', () {
      expect(
          esCorteDeRed(
              local: false, posicion: const Duration(minutes: 2, seconds: 57), duracion: const Duration(minutes: 3)),
          isFalse);
    });
    test('un archivo descargado nunca es un corte de red', () {
      expect(esCorteDeRed(local: true, posicion: const Duration(seconds: 10), duracion: const Duration(minutes: 3)),
          isFalse);
    });
    test('sin duración conocida o canciones muy cortas no se decide nada', () {
      expect(esCorteDeRed(local: false, posicion: const Duration(seconds: 5), duracion: Duration.zero), isFalse);
      expect(esCorteDeRed(local: false, posicion: const Duration(seconds: 5), duracion: const Duration(seconds: 20)),
          isFalse);
    });
    test('en una canción larga, faltar 8 s o menos ya es el final', () {
      expect(
          esCorteDeRed(
              local: false, posicion: const Duration(minutes: 59, seconds: 53), duracion: const Duration(hours: 1)),
          isFalse);
    });
  });

  group('cierres de Android', () {
    test('los fallos se informan siempre', () {
      for (final m in ['fallo_nativo', 'fallo_java', 'anr', 'fallo_arranque']) {
        expect(SalidasAndroid.merece({'motivo': m, 'importancia': 'en_segundo_plano', 'sonaba': false}), isTrue,
            reason: m);
      }
    });
    test('Android cerrando una app en reposo no es un fallo', () {
      expect(SalidasAndroid.merece({'motivo': 'poca_memoria', 'importancia': 'en_segundo_plano', 'sonaba': false}),
          isFalse);
      expect(SalidasAndroid.merece({'motivo': 'sistema', 'importancia': 'en_segundo_plano', 'sonaba': false}),
          isFalse);
    });
    test('si sonaba música, cualquier cierre del sistema se informa', () {
      expect(SalidasAndroid.merece({'motivo': 'sistema', 'importancia': 'servicio_musica', 'sonaba': true}), isTrue);
      expect(SalidasAndroid.merece({'motivo': 'poca_memoria', 'importancia': 'en_segundo_plano', 'sonaba': true}),
          isTrue);
    });
    test('actualizar la app o cerrarla a mano sin música no cuenta', () {
      expect(SalidasAndroid.merece({'motivo': 'paquete_actualizado', 'sonaba': true}), isFalse);
      expect(SalidasAndroid.merece({'motivo': 'usuario', 'importancia': 'en_pantalla', 'sonaba': false}), isFalse);
    });
    test('el informe lleva el motivo, el estado y la librería que cayó', () {
      final a = SalidasAndroid.informe({
        'motivo': 'fallo_nativo',
        'importancia': 'servicio_musica',
        'sonaba': true,
        'minutos_sonando': 12,
        'memoria_kb': 512000,
        'cuando': 1763700000000,
        'traza': 'backtrace: #00 pc 0001 /data/app/lib/arm64/libmpv.so (mp_decode+12)',
      }, memoria: {'total_mb': 3800, 'libre_mb': 600, 'clase_mb': 256, 'ram_baja': false});
      expect(a['tipo'], 'Cierre Android: fallo_nativo');
      expect(a['origen'], 'cierre-sonando');
      expect(a['mensaje'], contains('motivo=fallo_nativo'));
      expect(a['mensaje'], contains('sonaba=si (12 min)'));
      expect(a['mensaje'], contains('memoria=500MB'));
      expect(a['mensaje'], contains('ram=3800MB'));
      expect(a['traza'], contains('libmpv.so'));
      final b = SalidasAndroid.informe({
        'motivo': 'fallo_nativo',
        'importancia': 'servicio_musica',
        'sonaba': true,
        'traza': '#00 pc 0002 libflutter.so',
      });
      expect(a['huella'], isNot(b['huella']), reason: 'otra librería, otro problema');
      expect(a['huella'], matches(RegExp(r'^[0-9a-f]{16,64}$')));
    });
  });

  group('aviso de batería', () {
    final ahora = DateTime(2026, 11, 21, 12);
    test('sale la primera vez, luego con días de por medio y como mucho 3 veces', () {
      expect(AvisoBateria.toca(0, null, ahora), isTrue);
      expect(AvisoBateria.toca(1, ahora.subtract(const Duration(days: 1)), ahora), isFalse);
      expect(AvisoBateria.toca(1, ahora.subtract(const Duration(days: 4)), ahora), isTrue);
      expect(AvisoBateria.toca(3, ahora.subtract(const Duration(days: 30)), ahora), isFalse);
    });
    test('Samsung lleva sus pasos de «Apps en suspensión»', () {
      expect(AvisoBateria.pasos('samsung'), contains('Apps en suspensión'));
      expect(AvisoBateria.pasos('Xiaomi'), contains('Inicio automático'));
      expect(AvisoBateria.pasos('google'), contains('Sin restricciones'));
    });
  });

  group('aspecto de la letra', () {
    test('por defecto, la clásica con la letra de siempre', () {
      const a = LetraAspecto();
      expect(a.estilo, 'clasica');
      expect(a.fuente, 'predeterminada');
      const s = TextStyle(fontSize: 20, fontWeight: FontWeight.w800, height: 1.3);
      expect(a.conFuente(s), s, reason: 'la clásica no toca el estilo');
    });
    test('cada tipografía elegida cambia la familia y las de un grosor no llevan negrita inventada', () {
      const s = TextStyle(fontSize: 20, fontWeight: FontWeight.w800, height: 1.3);
      final p = const LetraAspecto(fuente: 'poppins').conFuente(s);
      expect(p.fontFamily, 'Poppins');
      expect(p.fontWeight, FontWeight.w800);
      final pac = const LetraAspecto(fuente: 'pacifico').conFuente(s);
      expect(pac.fontFamily, 'Pacifico');
      expect(pac.fontWeight, FontWeight.w400);
      expect(pac.height, greaterThan(1.3));
    });
    test('las claves son únicas y hay 10 estilos y 27 tipos de letra', () {
      expect(LetraAspecto.estilos.map((e) => e.clave).toSet().length, 10);
      expect(LetraAspecto.fuentes.map((e) => e.clave).toSet().length, 27);
    });

    for (final e in LetraAspecto.estilos) {
      for (final f in ['predeterminada', 'bebas', 'lobster']) {
        testWidgets('se pinta en ${e.clave} con $f', (t) async {
          final a = LetraAspecto(estilo: e.clave, fuente: f);
          LetraAspecto.actual.value = a;
          await t.pumpWidget(MaterialApp(
            home: Scaffold(
              body: Column(children: [
                LineaLetra(aspecto: a, texto: 'Ya cantada', estilo: const TextStyle(color: Color(0xB3FFFFFF))),
                LineaLetra(aspecto: a, texto: 'La que suena', estilo: const TextStyle(color: Colors.white),
                    activa: true, acento: Colors.cyan),
                TextoLetraPlano(aspecto: a, texto: 'Letra sin tiempos', estilo: const TextStyle(fontSize: 18)),
              ]),
            ),
          ));
          await t.pumpAndSettle();
          expect(find.text('Ya cantada'), findsWidgets);
          expect(t.takeException(), isNull);
        });
      }
    }
  });
}
