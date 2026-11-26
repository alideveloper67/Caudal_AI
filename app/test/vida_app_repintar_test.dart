// Al volver Caudal (o al engancharse la pantalla a un motor que ya sonaba) se piden cuadros nuevos:
// la pantalla nunca se queda negra esperando a que algo cambie.
import 'package:caudal/nucleo/vida_app.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('repintar pide cuadros aunque nada haya cambiado', (t) async {
    VidaApp.iniciar();
    await t.pumpWidget(const MaterialApp(home: Text('Caudal')));
    await t.pump();
    expect(t.binding.hasScheduledFrame, isFalse);       // nada cambió: Flutter no pintaría
    VidaApp.repintar();
    expect(t.binding.hasScheduledFrame, isTrue);        // pero se pide un cuadro igual
    await t.pump();
    await t.pump(const Duration(seconds: 2));            // los repintados de después no fallan
    // Android lo pide por su canal al volver la pantalla
    final mensajero = t.binding.defaultBinaryMessenger;
    await mensajero.handlePlatformMessage('caudal/vida',
        const StandardMethodCodec().encodeMethodCall(const MethodCall('repintar')), (_) {});
    await t.pump(const Duration(seconds: 2));
    VidaApp.primerPlano.value = true;
  });
}

