// «Feliz cumpleaños»: la regla del día (29 de febrero incluido), que la celebración salga una sola vez
// al día, el gorrito en avatares y la mascota, el banner de Inicio, el aviso de amigos y que la pantalla
// de celebración no se desborde a 320x568.
import 'dart:async';

import 'package:caudal/nucleo/cumpleanos.dart';
import 'package:caudal/nucleo/fondo_app.dart';
import 'package:caudal/nucleo/mascota_app.dart';
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/social.dart';
import 'package:caudal/ui/cumpleanos.dart';
import 'package:caudal/ui/paginas/perfil_comun.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _SesionAmigos extends Sesion {
  _SesionAmigos(this.respuesta) : super('yo', 'token', 'r', DateTime.now().add(const Duration(hours: 1)));
  final Object? respuesta;
  bool fallar = false;

  @override
  Future<dynamic> rpc(String nombre, [Map<String, dynamic> parametros = const {}]) async {
    if (nombre != 'amigos_cumplen_hoy') throw StateError('RPC inesperada: $nombre');
    if (fallar) throw StateError('sin red');
    return respuesta;
  }
}

Widget _app(Widget hijo, {double escala = 1.0}) => MaterialApp(
      theme: temaCaudal(),
      builder: (c, h) => MediaQuery(data: MediaQuery.of(c).copyWith(textScaler: TextScaler.linear(escala)), child: h!),
      home: Scaffold(body: hijo),
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FondoApp.i.puede = false;
    MascotaApp.i.reiniciar();
    Cumpleanos.i.reiniciar();
    Cumpleanos.i.ahora = DateTime.now;
  });

  group('la regla del día', () {
    test('un cumpleaños normal', () {
      final n = DateTime(1995, 11, 19);
      expect(ReglaCumple.esCumple(n, DateTime(2026, 11, 19)), isTrue);
      expect(ReglaCumple.esCumple(n, DateTime(2026, 11, 18)), isFalse);
      expect(ReglaCumple.esCumple(n, DateTime(2026, 11, 20)), isFalse);
      expect(ReglaCumple.esCumple(n, DateTime(2026, 12, 19)), isFalse);
      expect(ReglaCumple.esCumple(null, DateTime(2026, 11, 19)), isFalse);
    });

    test('29 de febrero: se celebra el 28 en año no bisiesto y el 29 en bisiesto', () {
      final n = DateTime(2000, 2, 29);
      expect(ReglaCumple.esCumple(n, DateTime(2026, 2, 28)), isTrue);
      expect(ReglaCumple.esCumple(n, DateTime(2026, 3, 1)), isFalse);
      expect(ReglaCumple.esCumple(n, DateTime(2027, 2, 28)), isTrue);
      expect(ReglaCumple.esCumple(n, DateTime(2028, 2, 29)), isTrue);
      expect(ReglaCumple.esCumple(n, DateTime(2028, 2, 28)), isFalse, reason: 'en bisiesto es el 29');
      expect(ReglaCumple.esCumple(n, DateTime(2100, 2, 28)), isTrue, reason: '2100 no es bisiesto');
      expect(ReglaCumple.esCumple(n, DateTime(2000, 2, 29)), isTrue);
    });

    test('quien nació un 28 de febrero lo celebra el 28 siempre', () {
      final n = DateTime(1999, 2, 28);
      expect(ReglaCumple.esCumple(n, DateTime(2026, 2, 28)), isTrue);
      expect(ReglaCumple.esCumple(n, DateTime(2028, 2, 28)), isTrue);
      expect(ReglaCumple.esCumple(n, DateTime(2028, 2, 29)), isFalse);
    });

    test('bisiestos', () {
      expect([1900, 2000, 2024, 2026, 2100].map(ReglaCumple.esBisiesto), [false, true, true, false, false]);
    });

    test('la edad que cumple hoy', () {
      expect(ReglaCumple.edadQueCumple(DateTime(2000, 2, 29), DateTime(2026, 2, 28)), 26);
      expect(ReglaCumple.edadQueCumple(DateTime(1995, 11, 19), DateTime(2026, 11, 19)), 31);
      expect(ReglaCumple.edadQueCumple(null, DateTime(2026, 11, 19)), isNull);
      expect(ReglaCumple.edadQueCumple(DateTime(2026, 11, 19), DateTime(2026, 11, 19)), isNull, reason: 'recién nacido: sin edad');
      expect(ReglaCumple.edadQueCumple(DateTime(2030, 11, 19), DateTime(2026, 11, 19)), isNull, reason: 'fecha futura');
      expect(ReglaCumple.edadQueCumple(DateTime(1800, 11, 19), DateTime(2026, 11, 19)), isNull, reason: 'fecha absurda');
    });

    test('la clave del día', () {
      expect(ReglaCumple.claveDia(DateTime(2026, 3, 5, 23, 59)), '2026-03-05');
    });
  });

  group('una sola vez al día', () {
    test('sale la primera vez, ya no la segunda, y vuelve el año siguiente', () async {
      final c = Cumpleanos.i;
      c.ahora = () => DateTime(2026, 11, 19, 9, 30);
      c.poner(cuenta: 'c1', id: 'yo', nombre: 'Ali', nacimiento: DateTime(1995, 11, 19));
      expect(c.esMiCumple, isTrue);
      expect(c.edad, 31);
      expect(await c.tocaCelebrar(), isTrue);
      await c.marcarCelebrado();
      expect(await c.tocaCelebrar(), isFalse, reason: 'ya se enseñó hoy');
      c.ahora = () => DateTime(2026, 11, 19, 23, 59);
      expect(await c.tocaCelebrar(), isFalse, reason: 'sigue siendo el mismo día');
      c.ahora = () => DateTime(2026, 11, 20, 0, 1);
      expect(c.esMiCumple, isFalse);
      expect(await c.tocaCelebrar(), isFalse, reason: 'mañana ya no es');
      c.ahora = () => DateTime(2027, 11, 19, 8);
      expect(await c.tocaCelebrar(), isTrue, reason: 'el año siguiente toca otra vez');
    });

    test('cada cuenta lleva su propio registro', () async {
      final c = Cumpleanos.i;
      c.ahora = () => DateTime(2026, 11, 19);
      c.poner(cuenta: 'a', id: 'ua', nacimiento: DateTime(1990, 11, 19));
      await c.marcarCelebrado();
      c.poner(cuenta: 'b');
      expect(await c.tocaCelebrar(), isTrue);
    });

    test('un día que no es el suyo no se celebra', () async {
      final c = Cumpleanos.i;
      c.ahora = () => DateTime(2026, 11, 18);
      c.poner(cuenta: 'a', id: 'ua', nacimiento: DateTime(1990, 11, 19));
      expect(await c.tocaCelebrar(), isFalse);
    });

    test('quien nació un 29 de febrero se celebra una vez el 28 en año normal', () async {
      final c = Cumpleanos.i;
      c.ahora = () => DateTime(2027, 2, 28, 10);
      c.poner(cuenta: 'a', id: 'ua', nacimiento: DateTime(2000, 2, 29));
      expect(await c.tocaCelebrar(), isTrue);
      await c.marcarCelebrado();
      expect(await c.tocaCelebrar(), isFalse);
      c.ahora = () => DateTime(2027, 3, 1);
      expect(c.esMiCumple, isFalse);
    });
  });

  group('amigos', () {
    test('la respuesta de la nube son solo ids; quien no cumple hoy o es otro día no cuenta', () async {
      final c = Cumpleanos.i;
      c.ahora = () => DateTime(2026, 11, 19);
      c.poner(cuenta: 'a', id: 'yo');
      await c.actualizarAmigos(_SesionAmigos(['id1', 'id2', '', 7]));
      expect(c.amigosHoy, {'id1', 'id2'});
      expect(c.esDe('id1'), isTrue);
      expect(c.esDe('id9'), isFalse);
      expect(c.esDe(''), isFalse);
      // al día siguiente esa lista ya no vale
      c.ahora = () => DateTime(2026, 11, 20);
      expect(c.amigosHoy, isEmpty);
      expect(c.esDe('id1'), isFalse);
    });

    test('también entiende filas con un solo campo y un fallo de red no rompe nada', () async {
      final c = Cumpleanos.i;
      c.poner(cuenta: 'a', id: 'yo');
      await c.actualizarAmigos(_SesionAmigos([{'amigos_cumplen_hoy': 'x1'}]));
      expect(c.amigosHoy, {'x1'});
      final mala = _SesionAmigos(null)..fallar = true;
      await c.actualizarAmigos(mala);
      expect(c.amigosHoy, {'x1'}, reason: 'si falla, se queda lo que había');
    });

    test('la celebración espera a que se lea mi fecha, sin dejar relojes pendientes', () async {
      final c = Cumpleanos.i;
      c.ahora = () => DateTime(2026, 11, 19);
      c.poner(cuenta: 'a', id: 'yo');
      final espera = c.esperarPerfil();
      var listo = false;
      unawaited(espera.then((_) => listo = true));
      await Future<void>.delayed(Duration.zero);
      expect(listo, isFalse);
      c.nacimiento = DateTime(1990, 11, 19);
      c.perfilLeido = true;
      c.poner();
      expect(await espera, isTrue);
      expect(await c.esperarPerfil(), isTrue, reason: 'ya leído: responde al instante');
    });

    test('mi propio id no cuenta como amigo y reiniciar lo limpia todo', () {
      final c = Cumpleanos.i;
      c.poner(cuenta: 'a', id: 'yo', nacimiento: DateTime(1990, 1, 1), amigos: ['yo', 'z']);
      expect(c.amigosHoy, {'z'});
      c.reiniciar();
      expect(c.amigosHoy, isEmpty);
      expect(c.nacimiento, isNull);
      expect(c.miId, '');
    });
  });

  group('lo que se ve', () {
    testWidgets('la celebración a 320x568 con la letra grande: sin desbordes, con nombre, edad y botón', (t) async {
      t.view.physicalSize = const Size(320, 568);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      await t.pumpWidget(_app(const PantallaCumple(nombre: 'Ali', edad: 31), escala: 1.2));
      await t.pump(const Duration(milliseconds: 700));
      expect(t.takeException(), isNull);
      expect(find.text('¡Feliz cumpleaños, Ali!'), findsOneWidget);
      expect(find.text('Hoy cumples 31'), findsOneWidget);
      expect(find.text('¡Gracias!'), findsOneWidget);
    });

    testWidgets('un nombre larguísimo y sin edad tampoco desborda (320x568)', (t) async {
      t.view.physicalSize = const Size(320, 568);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      await t.pumpWidget(_app(const PantallaCumple(nombre: 'Maximiliano Alejandro Fernandez-Sotomayor'), escala: 1.2));
      await t.pump(const Duration(milliseconds: 500));
      expect(t.takeException(), isNull);
      expect(find.textContaining('Hoy cumples'), findsNothing, reason: 'sin edad no se inventa');
    });

    testWidgets('pantalla bajita (horizontal, 568x320) también cabe, con scroll', (t) async {
      t.view.physicalSize = const Size(568, 320);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      await t.pumpWidget(_app(const PantallaCumple(nombre: 'Ali', edad: 20)));
      await t.pump(const Duration(milliseconds: 500));
      expect(t.takeException(), isNull);
    });

    testWidgets('con «quitar animaciones» el confeti queda quieto y «¡Gracias!» cierra', (t) async {
      t.view.physicalSize = const Size(320, 568);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      await t.pumpWidget(MaterialApp(
        theme: temaCaudal(),
        builder: (c, h) => MediaQuery(data: MediaQuery.of(c).copyWith(disableAnimations: true), child: h!),
        home: Builder(
          builder: (c) => Scaffold(
            body: Center(
              child: TextButton(
                  onPressed: () => PantallaCumple.mostrar(c, nombre: 'Ali', edad: 31), child: const Text('abrir')),
            ),
          ),
        ),
      ));
      await t.tap(find.text('abrir'));
      await t.pumpAndSettle(); // si el confeti siguiera corriendo, esto no terminaría
      expect(find.text('¡Feliz cumpleaños, Ali!'), findsOneWidget);
      await t.tap(find.text('¡Gracias!'));
      await t.pumpAndSettle();
      expect(find.text('¡Feliz cumpleaños, Ali!'), findsNothing);
      expect(find.text('abrir'), findsOneWidget);
    });

    testWidgets('con una mascota elegida sale su dibujo con gorro y no desborda', (t) async {
      t.view.physicalSize = const Size(320, 568);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      FondoApp.i.puede = true;
      await t.runAsync(() async {
        await MascotaApp.i.cargarCatalogo(
            texto: '[{"clave":"nyan","nombre":"Nyan","origen":"x","ancho":48,"alto":44,"cuadros":2,"arcoiris":true}]');
      });
      MascotaApp.i.clave = 'nyan';
      expect(MascotaApp.i.activa, isTrue);
      await t.pumpWidget(_app(const PantallaCumple(nombre: 'Ali', edad: 9)));
      await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 200)));
      await t.pump(const Duration(milliseconds: 300));
      expect(t.takeException(), isNull);
      FondoApp.i.puede = false;
    });

    testWidgets('el gorrito aparece en el avatar de un amigo que cumple y no en el de otro', (t) async {
      Cumpleanos.i.poner(cuenta: 'a', id: 'yo', amigos: ['amigo1']);
      await t.pumpWidget(_app(const Column(children: [
        AvatarPerfil(key: ValueKey('a'), nombre: 'Ana', userId: 'amigo1', radio: 24),
        AvatarPerfil(key: ValueKey('b'), nombre: 'Beto', userId: 'otro', radio: 24),
        AvatarPerfil(key: ValueKey('c'), nombre: 'Cami', radio: 24),
      ])));
      Finder gorros(String k) => find.descendant(of: find.byKey(ValueKey(k)), matching: find.byType(IgnorePointer));
      expect(gorros('a'), findsWidgets);
      expect(find.descendant(of: find.byKey(const ValueKey('a')), matching: find.byWidgetPredicate((w) => w is Positioned && w.width != null)),
          findsOneWidget);
      expect(find.descendant(of: find.byKey(const ValueKey('b')), matching: find.byType(Positioned)), findsNothing);
      expect(find.descendant(of: find.byKey(const ValueKey('c')), matching: find.byType(Positioned)), findsNothing);
      // el avatar mide lo mismo con o sin gorro
      expect(t.getSize(find.byKey(const ValueKey('a'))), t.getSize(find.byKey(const ValueKey('b'))));
      // y se quita solo cuando cambia la lista
      Cumpleanos.i.poner(amigos: const []);
      await t.pump();
      expect(find.descendant(of: find.byKey(const ValueKey('a')), matching: find.byType(Positioned)), findsNothing);
    });

    testWidgets('mi propio avatar lleva gorro solo el día de mi cumple', (t) async {
      Cumpleanos.i.ahora = () => DateTime(2026, 11, 19);
      Cumpleanos.i.poner(cuenta: 'a', id: 'yo', nacimiento: DateTime(1990, 11, 19));
      await t.pumpWidget(_app(const AvatarPerfil(nombre: 'Yo', userId: 'yo', radio: 30)));
      expect(find.byType(Positioned), findsOneWidget);
      Cumpleanos.i.ahora = () => DateTime(2026, 11, 20);
      Cumpleanos.i.poner();
      await t.pump();
      expect(find.byType(Positioned), findsNothing);
    });

    testWidgets('banner «Hoy es tu cumple» y aviso de amigo con «Escribirle» (320x568)', (t) async {
      t.view.physicalSize = const Size(320, 568);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      Cumpleanos.i.ahora = () => DateTime(2026, 11, 19);
      Cumpleanos.i.poner(cuenta: 'a', id: 'yo', nacimiento: DateTime(1990, 11, 19), amigos: ['m1', 'm2', 'm3', 'm4', 'm5']);
      final amigos = [
        const Contacto(id: 'm1', usuario: 'maria', nombre: 'María Fernanda de los Ángeles Quispe', relacion: Relacion.amigo),
        const Contacto(id: 'm2', usuario: 'beto', nombre: 'Beto', relacion: Relacion.amigo),
        const Contacto(id: 'm3', usuario: 'c', nombre: 'Cami', relacion: Relacion.amigo),
        const Contacto(id: 'm4', usuario: 'd', nombre: 'Dani', relacion: Relacion.amigo),
        const Contacto(id: 'm5', usuario: 'e', nombre: 'Eli', relacion: Relacion.amigo),
      ];
      await t.pumpWidget(_app(SingleChildScrollView(child: CumpleInicio(amigosDePrueba: amigos)), escala: 1.2));
      await t.pump();
      expect(t.takeException(), isNull);
      expect(find.text('Hoy es tu cumple 🎂'), findsOneWidget);
      expect(find.textContaining('Hoy es el cumple de María Fernanda'), findsOneWidget);
      expect(find.textContaining('¡salúdalo!'), findsNWidgets(3), reason: 'se enseñan 3 y el resto va resumido');
      expect(find.text('Escribirle'), findsNWidgets(3));
      expect(find.text('y 2 amigos más cumplen hoy'), findsOneWidget);
    });

    testWidgets('sin cumpleaños no ocupa nada', (t) async {
      Cumpleanos.i.ahora = () => DateTime(2026, 11, 19);
      Cumpleanos.i.poner(cuenta: 'a', id: 'yo', nacimiento: DateTime(1990, 5, 5));
      await t.pumpWidget(_app(const CumpleInicio()));
      await t.pump();
      expect(t.getSize(find.byType(CumpleInicio)).height, 0);
      expect(find.textContaining('cumple'), findsNothing);
    });

    testWidgets('el gorrito suelto cabe en su caja y el banner no se rompe a 320 de ancho', (t) async {
      t.view.physicalSize = const Size(320, 568);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.reset);
      Cumpleanos.i.ahora = () => DateTime(2026, 11, 19);
      Cumpleanos.i.poner(cuenta: 'a', id: 'yo', nacimiento: DateTime(1990, 11, 19));
      await t.pumpWidget(_app(const Column(children: [GorroFiesta(ancho: 40), CumpleInicio()]), escala: 1.2));
      await t.pump();
      expect(t.takeException(), isNull);
      expect(t.getSize(find.byType(GorroFiesta).first), const Size(40, 52));
    });
  });
}
