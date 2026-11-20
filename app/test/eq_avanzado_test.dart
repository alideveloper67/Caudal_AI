// Ecualizador avanzado (donadores y fundadores): 15 bandas, preamplificador, ajustes con nombre,
// uno por salida que entra solo al cambiar de salida, y el candado sin beneficios.
import 'package:caudal/nucleo/ajustes.dart';
import 'package:caudal/nucleo/eq_avanzado.dart';
import 'package:caudal/nucleo/premium_letras.dart';
import 'package:caudal/ui/paginas/eq_avanzado_pagina.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  group('lógica', () {
    test('bandas y preamplificador limpios', () {
      expect(frecuenciasAvanzado.length, 15);
      final b = limpiarBandas([30, -30, 1.26, 'x']);
      expect(b.length, 15);
      expect(b.take(4).toList(), [12.0, -12.0, 1.5, 0.0]);
      expect(limpiarPreamp(10), 6.0);
      expect(limpiarPreamp(-20), -12.0);
    });

    test('filtros y ganancia previa', () {
      final bandas = limpiarBandas([0, 0, 0, 0, 0, 0, 0, 3]);
      expect(partesFiltroAvanzado(bandas), ['equalizer=f=630:t=o:w=0.67:g=3.0']);
      expect(gananciaPrevia(limpiarBandas([5]), -2), closeTo(-5, 1e-9));
    });

    test('guardar, cargar y borrar con nombre', () {
      final e = EstadoEqAvanzado();
      expect(e.lista.keys.toSet(), inicialesAvanzado.keys.toSet());
      e.bandas = limpiarBandas(List.filled(15, 2));
      e.preamp = -3;
      expect(e.guardarComo('  Mi   coche '), 'Mi coche');
      expect(e.guardarComo('   '), '');
      e.bandas = limpiarBandas(const []);
      expect(e.cargar('Mi coche'), isTrue);
      expect(e.bandas, List.filled(15, 2.0));
      expect(e.preamp, -3);
      e.asignar(salidaBluetooth, 'Mi coche');
      e.borrar('Mi coche');
      expect(e.lista.containsKey('Mi coche'), isFalse);
      expect(e.porSalida[salidaBluetooth], '');
    });

    test('se guarda y se lee como texto', () {
      final e = EstadoEqAvanzado(activo: true, bandas: limpiarBandas([1, 2, 3]), preamp: -1.5);
      e.guardarComo('A');
      e.asignar(salidaAudifonos, 'A');
      final otra = EstadoEqAvanzado.leer(activo: true, bandas: e.bandasJson, preamp: e.preamp,
          nombre: e.nombre, guardados: e.guardadosJson, porSalida: e.porSalidaJson);
      expect(otra.bandas, e.bandas);
      expect(otra.lista['A']!.preamp, -1.5);
      expect(otra.porSalida[salidaAudifonos], 'A');
      // texto roto: no revienta
      expect(EstadoEqAvanzado.leer(bandas: '{', guardados: 'x').bandas.length, 15);
    });

    test('al cambiar de salida pone su ajuste solo al cambiar y con beneficios', () {
      final e = EstadoEqAvanzado(bandas: limpiarBandas(List.filled(15, 4)), preamp: -4);
      e.guardarComo('Coche');
      e.bandas = limpiarBandas(const []);
      e.asignar(salidaBluetooth, 'Coche');
      expect(e.alCambiarSalida(premium: true, antes: null, ahora: salidaBluetooth), isNull);
      expect(e.alCambiarSalida(premium: true, antes: salidaBluetooth, ahora: salidaBluetooth), isNull);
      expect(e.alCambiarSalida(premium: false, antes: salidaAudifonos, ahora: salidaBluetooth), isNull);
      expect(e.activo, isFalse);
      expect(e.alCambiarSalida(premium: true, antes: salidaAudifonos, ahora: salidaBluetooth), 'Coche');
      expect(e.activo, isTrue);
      expect(e.bandas, List.filled(15, 4.0));
      expect(e.alCambiarSalida(premium: true, antes: salidaBluetooth, ahora: salidaParlante), isNull);
    });

    test('en los ajustes de la app', () async {
      SharedPreferences.setMockInitialValues({});
      final a = await Ajustes.cargar('prueba');
      expect(a.nivelVolumen, 'alto');
      await a.ponerNivelVolumen('maximo');
      expect(a.nivelVolumen, 'maximo');
      expect(a.entero('super_volumen'), 4);
      await a.ponerNivelVolumen('no');
      expect(a.nivelVolumen, 'normal'); // igualar sigue encendido
      final e = a.eqAvanzado..activo = true;
      e.bandas[0] = 6;
      e.guardarComo('Grave');
      await a.ponerEqAvanzado(e);
      expect(a.eqAvanzado.activo, isTrue);
      expect(a.eqAvanzado.bandas.first, 6);
      expect(a.eqAvanzado.lista.containsKey('Grave'), isTrue);
    });

    test('ajustes de una versión con súper volumen', () async {
      SharedPreferences.setMockInitialValues({'aj.prueba.super_volumen': 3});
      final a = await Ajustes.cargar('prueba');
      expect(a.nivelVolumen, 'maximo');
    });
  });

  group('pantalla', () {
    late bool premium;
    final antes = esPremiumLetras;
    setUp(() => esPremiumLetras = () => premium);
    tearDown(() => esPremiumLetras = antes);

    testWidgets('sin beneficios: candado y un toque explica cómo tenerlo', (t) async {
      premium = false;
      await t.pumpWidget(MaterialApp(home: Scaffold(body: Builder(
          builder: (ctx) => TextButton(onPressed: () => mostrarEqAvanzado(ctx), child: const Text('abrir'))))));
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle();
      expect(find.textContaining('donadores y fundadores'), findsOneWidget);
      expect(find.text('Cómo tenerlo'), findsOneWidget);
      expect(find.byIcon(Icons.lock_outline_rounded), findsOneWidget);
    });
  });
}
