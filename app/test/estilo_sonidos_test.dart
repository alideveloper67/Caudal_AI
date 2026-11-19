// Estilos a elegir, colores de la carátula y sonidos de interfaz (lógica, sin pantallas).
import 'dart:io';
import 'dart:typed_data';

import 'package:caudal/nucleo/coleccion.dart' show PortadasMem;
import 'package:caudal/nucleo/estilo_reproductor.dart';
import 'package:caudal/nucleo/premium_letras.dart';
import 'package:caudal/nucleo/sonidos_interfaz.dart';
import 'package:caudal/reproduccion/jugador.dart';
import 'package:caudal/ui/reproductor/paleta_portada.dart';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _JugadorFalso implements Jugador {
  final llamadas = <String>[];
  double volumen = -1;

  @override
  Future<void> setVolume(double v) async {
    volumen = v;
    llamadas.add('volumen');
  }

  @override
  Future<void> open(dynamic f, {Duration? inicio, bool play = true}) async => llamadas.add('abrir');

  @override
  Future<void> dispose() async => llamadas.add('soltar');

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Uint8List _rgba(List<Color> colores) {
  final b = Uint8List(colores.length * 4);
  for (var i = 0; i < colores.length; i++) {
    b[i * 4] = (colores[i].r * 255).round();
    b[i * 4 + 1] = (colores[i].g * 255).round();
    b[i * 4 + 2] = (colores[i].b * 255).round();
    b[i * 4 + 3] = 255;
  }
  return b;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final antes = esPremiumLetras;
  tearDown(() => esPremiumLetras = antes);

  group('preferencias del reproductor', () {
    setUp(() => SharedPreferences.setMockInitialValues({}));

    test('por defecto es el clásico, con colores activos y sonidos apagados', () async {
      final p = PreferenciasReproductor();
      await p.cargar();
      expect(p.estilo, EstiloReproductor.clasico);
      expect(p.coloresDePortada, isTrue);
      expect(p.sonidoMeGusta, isFalse);
      expect(p.sonidoAlAbrir, isFalse);
      expect(p.volumenSonido, lessThanOrEqualTo(0.3));
    });

    test('quien tenía el vinilo de antes lo conserva', () async {
      SharedPreferences.setMockInitialValues({'modo_vinilo': true});
      final p = PreferenciasReproductor();
      await p.cargar();
      expect(p.estilo, EstiloReproductor.vinilo);
    });

    test('un donador elige estilo y se recuerda al abrir de nuevo', () async {
      esPremiumLetras = () => true;
      final p = PreferenciasReproductor();
      await p.cargar();
      expect(await p.elegirEstilo(EstiloReproductor.casete), isTrue);
      await p.ponerSonidoMeGusta(true);
      await p.elegirSonido(SonidoUi.campana);
      await p.ponerVolumenSonido(0.4);
      final otra = PreferenciasReproductor();
      await otra.cargar();
      expect(otra.estilo, EstiloReproductor.casete);
      expect(otra.sonidoMeGusta, isTrue);
      expect(otra.sonido, SonidoUi.campana);
      expect(otra.volumenSonido, 0.4);
    });

    test('sin beneficios los estilos de donador no se aceptan y el vinilo sí', () async {
      esPremiumLetras = () => false;
      final p = PreferenciasReproductor();
      await p.cargar();
      expect(await p.elegirEstilo(EstiloReproductor.neon), isFalse);
      expect(p.estilo, EstiloReproductor.clasico);
      expect(await p.elegirEstilo(EstiloReproductor.vinilo), isTrue);
      expect(p.estiloEfectivo, EstiloReproductor.vinilo);
    });

    test('si se acaban los beneficios, lo elegido vuelve al clásico sin borrarse', () async {
      esPremiumLetras = () => true;
      final p = PreferenciasReproductor();
      await p.cargar();
      await p.elegirEstilo(EstiloReproductor.flotante);
      expect(p.estiloEfectivo, EstiloReproductor.flotante);
      esPremiumLetras = () => false;
      expect(p.estiloEfectivo, EstiloReproductor.clasico);
      expect(p.estilo, EstiloReproductor.flotante);
      expect(p.coloresActivos, isFalse);
      esPremiumLetras = () => true;
      expect(p.estiloEfectivo, EstiloReproductor.flotante);
    });

    test('el volumen del sonidito no pasa de 0,6 ni baja de 0,05', () async {
      final p = PreferenciasReproductor();
      await p.ponerVolumenSonido(5);
      expect(p.volumenSonido, 0.6);
      await p.ponerVolumenSonido(0);
      expect(p.volumenSonido, 0.05);
    });
  });

  group('sonidos de interfaz', () {
    late Directory carpeta;
    late _JugadorFalso motor;
    var creados = 0;
    late PreferenciasReproductor prefs;

    SonidosInterfaz hacer({bool donador = true, Duration reposo = const Duration(seconds: 20)}) => SonidosInterfaz(
          fabrica: () {
            creados++;
            return motor;
          },
          carpeta: () async => carpeta,
          cargarAsset: (a) async => Uint8List.fromList(List.filled(100, 1)),
          preferencias: prefs,
          esDonador: () => donador,
          disponible: true,
          espera: const Duration(milliseconds: 5),
          reposo: reposo,
        );

    setUp(() {
      SharedPreferences.setMockInitialValues({});
      carpeta = Directory.systemTemp.createTempSync('sonidos_ui');
      motor = _JugadorFalso();
      creados = 0;
      prefs = PreferenciasReproductor();
    });
    tearDown(() => carpeta.deleteSync(recursive: true));

    test('con el sonido apagado no suena nada, ni se crea el motor', () async {
      final s = hacer();
      await s.meGusta();
      await s.alAbrir();
      expect(s.sonados, 0);
      expect(creados, 0);
    });

    test('al dar me gusta suena el elegido, a volumen bajo', () async {
      await prefs.ponerSonidoMeGusta(true);
      await prefs.elegirSonido(SonidoUi.moneda);
      final s = hacer();
      await s.meGusta();
      expect(s.sonados, 1);
      expect(motor.llamadas, ['volumen', 'abrir']);
      expect(motor.volumen, lessThanOrEqualTo(60));
      // el archivo se copió una vez desde el asset
      final f = File('${carpeta.path}${Platform.pathSeparator}caudal_sonidos_ui${Platform.pathSeparator}moneda_v1.wav');
      expect(f.existsSync(), isTrue);
    });

    test('quien no es donador no oye nada aunque lo tuviera activado', () async {
      await prefs.ponerSonidoMeGusta(true);
      await prefs.ponerSonidoAlAbrir(true);
      final s = hacer(donador: false);
      await s.meGusta();
      await s.alAbrir();
      expect(s.sonados, 0);
    });

    test('dos me gusta seguidos no se repiten (ni un doble toque)', () async {
      await prefs.ponerSonidoMeGusta(true);
      final s = hacer();
      await s.meGusta();
      await s.meGusta();
      expect(s.sonados, 1);
    });

    test('al abrir la app suena una sola vez por arranque', () async {
      await prefs.ponerSonidoAlAbrir(true);
      final s = hacer();
      await s.alAbrir();
      await s.alAbrir();
      expect(s.sonados, 1);
    });

    test('tras un rato sin sonar el motor se suelta, y si falla el motor no pasa nada', () async {
      await prefs.ponerSonidoMeGusta(true);
      final s = hacer(reposo: const Duration(milliseconds: 20));
      await s.meGusta();
      await Future<void>.delayed(const Duration(milliseconds: 80));
      expect(motor.llamadas.last, 'soltar');

      final roto = SonidosInterfaz(
        fabrica: () => throw StateError('sin motor'),
        carpeta: () async => carpeta,
        cargarAsset: (a) async => Uint8List(10),
        preferencias: prefs,
        esDonador: () => true,
        disponible: true,
      );
      await roto.meGusta(); // no lanza
      expect(roto.sonados, 0);
    });

    test('los tres audios existen y son livianos', () {
      var total = 0;
      for (final s in SonidoUi.values) {
        final f = File(s.asset);
        expect(f.existsSync(), isTrue, reason: s.asset);
        expect(f.lengthSync(), lessThan(40 * 1024), reason: s.asset);
        total += f.lengthSync();
        // cabecera WAV
        expect(String.fromCharCodes(f.readAsBytesSync().sublist(0, 4)), 'RIFF');
      }
      expect(total, lessThan(80 * 1024));
    });
  });

  group('paleta de la carátula', () {
    test('un solo color: el fondo sale oscurecido y el acento claro y vivo', () {
      final p = paletaDePixeles(_rgba(List.filled(64, const Color(0xFFE53935))));
      final fondo = HSVColor.fromColor(p.fondo), acento = HSVColor.fromColor(p.acento);
      expect(fondo.value, inInclusiveRange(0.28, 0.59));
      expect(acento.value, greaterThanOrEqualTo(0.82));
      expect(acento.saturation, greaterThanOrEqualTo(0.5));
      expect((acento.hue - fondo.hue).abs(), lessThan(8));
    });

    test('dos colores: el contraste toma el otro matiz', () {
      final px = [...List.filled(40, const Color(0xFFD32F2F)), ...List.filled(20, const Color(0xFF1976D2))];
      final p = paletaDePixeles(_rgba(px));
      expect(HSVColor.fromColor(p.fondo).hue, closeTo(HSVColor.fromColor(const Color(0xFFD32F2F)).hue, 10));
      final h = HSVColor.fromColor(p.contraste).hue;
      expect(h, closeTo(HSVColor.fromColor(const Color(0xFF1976D2)).hue, 10));
    });

    test('carátula en grises: acento blanco suave; todo negro o vacío: la neutra', () {
      final g = paletaDePixeles(_rgba(List.filled(64, const Color(0xFF9E9E9E))));
      expect(HSVColor.fromColor(g.acento).saturation, lessThan(0.15));
      expect(paletaDePixeles(_rgba(List.filled(64, const Color(0xFF000000)))), PaletaPortada.neutra);
      expect(paletaDePixeles(Uint8List(0)), PaletaPortada.neutra);
    });

    test('es determinista', () {
      final px = _rgba([for (var i = 0; i < 100; i++) Color(0xFF000000 | (i * 2654435 & 0xFFFFFF))]);
      expect(paletaDePixeles(px), paletaDePixeles(px));
    });

    test('la transición interpola entre dos paletas', () {
      const a = PaletaPortada(fondo: Color(0xFF000000), acento: Color(0xFF000000), contraste: Color(0xFF000000));
      const b = PaletaPortada(fondo: Color(0xFFFFFFFF), acento: Color(0xFFFFFFFF), contraste: Color(0xFFFFFFFF));
      expect(PaletaPortada.lerp(a, b, 0), a);
      expect(PaletaPortada.lerp(a, b, 1), b);
      expect(PaletaPortada.lerp(a, b, 0.5).fondo, Color.lerp(a.fondo, b.fondo, 0.5));
      expect(PaletaTween(begin: a, end: b).lerp(1), b);
    });

    testWidgets('se calcula una vez por URL y se guarda en caché', (t) async {
      olvidarPaletas();
      final bytes = img.encodePng(img.Image(width: 4, height: 4)..clear(img.ColorRgb8(229, 57, 53)));
      const ref = 'mem:prueba:1';
      PortadasMem.poner(ref, Uint8List.fromList(bytes));
      addTearDown(PortadasMem.limpiar);
      expect(paletaEnCache(ref), isNull);
      final p1 = await t.runAsync(() => paletaDe(ref));
      expect(HSVColor.fromColor(p1!.acento).saturation, greaterThan(0.5));
      expect(paletaEnCache(ref), p1);
      // la segunda vez no toca el archivo
      PortadasMem.quitar(ref);
      final p2 = await t.runAsync(() => paletaDe(ref));
      expect(p2, p1);
      // sin URL o con una que no existe, la neutra (y no se guarda)
      expect(await t.runAsync(() => paletaDe('')), PaletaPortada.neutra);
      final nada = await t.runAsync(() => paletaDe('mem:no_existe'));
      expect(nada, PaletaPortada.neutra);
      expect(paletaEnCache('mem:no_existe'), isNull);
    });
  });
}
