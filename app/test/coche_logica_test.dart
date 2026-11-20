import 'dart:io';

import 'package:audio_service/audio_service.dart';
import 'package:caudal/coche/acciones_coche.dart';
import 'package:caudal/coche/atajos_caudal.dart';
import 'package:caudal/coche/caratula_coche.dart';
import 'package:caudal/coche/coche_bluetooth.dart';
import 'package:caudal/nucleo/coleccion.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _coche = DispositivoBt(direccion: 'AA:BB:CC:00:11:22', nombre: 'Radio del coche', esCoche: true, esAudio: true);
const _audifonos = DispositivoBt(direccion: 'de:ad:be:ef:00:01', nombre: 'Audífonos', esAudio: true);

PreferenciasCoche _conCoche({bool solo = true}) => PreferenciasCoche(abrirSolo: solo)..alternar(_coche, true);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('PreferenciasCoche', () {
    test('codifica y decodifica los aparatos (con | y saltos en el nombre)', () {
      final d = {'AA:BB': 'Radio | del\ncoche', 'CC:DD': ''};
      final texto = PreferenciasCoche.codificar(d);
      expect(texto.split('\n').length, 2, reason: 'una línea por aparato');
      expect(PreferenciasCoche.decodificar(texto), {'AA:BB': 'Radio / del coche', 'CC:DD': ''});
      expect(PreferenciasCoche.decodificar(null), isEmpty);
      expect(PreferenciasCoche.decodificar('\n  \nee:ff'), {'EE:FF': ''});
    });

    test('las direcciones no distinguen mayúsculas', () {
      final p = PreferenciasCoche()..alternar(_audifonos, true);
      expect(p.contiene('DE:AD:BE:EF:00:01'), isTrue);
      expect(p.contiene('de:ad:be:ef:00:01'), isTrue);
      p.alternar(_audifonos, false);
      expect(p.dispositivos, isEmpty);
    });

    test('se guarda con las claves que lee CocheReceptor.kt y avisa del cambio', () async {
      SharedPreferences.setMockInitialValues({});
      final antes = PreferenciasCoche.cambios.value;
      await _conCoche().guardar();
      final sp = await SharedPreferences.getInstance();
      expect(sp.getBool('coche_abrir_solo'), isTrue);
      expect(sp.getString('coche_dispositivos'), 'AA:BB:CC:00:11:22|Radio del coche');
      expect(PreferenciasCoche.cambios.value, antes + 1);
      final leida = await PreferenciasCoche.cargar();
      expect(leida.abrirSolo, isTrue);
      expect(leida.contiene(_coche.direccion), isTrue);
    });

    test('sin nada guardado: apagado y sin aparatos', () async {
      SharedPreferences.setMockInitialValues({});
      final p = await PreferenciasCoche.cargar();
      expect(p.abrirSolo, isFalse);
      expect(p.dispositivos, isEmpty);
    });
  });

  group('DecisorCoche', () {
    final t0 = DateTime(2026, 11, 19, 8);

    test('con Caudal a la vista se abre al momento, una vez por conexión', () {
      final d = DecisorCoche();
      final p = _conCoche();
      expect(d.alConectar(_coche.direccion, p, aLaVista: true), DecisionCoche.abrirYa);
      // el Bluetooth a veces avisa dos veces: no se abre otra
      expect(d.alConectar(_coche.direccion, p, aLaVista: true), DecisionCoche.nada);
      d.alDesconectar(_coche.direccion);
      expect(d.alConectar(_coche.direccion, p, aLaVista: true), DecisionCoche.abrirYa);
    });

    test('apagado, o un aparato que no es el coche: nada', () {
      final d = DecisorCoche();
      expect(d.alConectar(_coche.direccion, _conCoche(solo: false), aLaVista: true), DecisionCoche.nada);
      expect(d.alConectar(_audifonos.direccion, _conCoche(), aLaVista: true), DecisionCoche.nada);
    });

    test('con Caudal de fondo queda pendiente y se abre al volver', () {
      final d = DecisorCoche();
      final p = _conCoche();
      expect(d.alConectar(_coche.direccion, p, aLaVista: false, ahora: t0), DecisionCoche.alVolver);
      expect(d.pendiente, _coche.direccion);
      expect(d.alVolver(p, ahora: t0.add(const Duration(minutes: 5))), isTrue);
      // ya se abrió: volver otra vez no lo reabre
      expect(d.alVolver(p, ahora: t0.add(const Duration(minutes: 6))), isFalse);
      expect(d.alConectar(_coche.direccion, p, aLaVista: true), DecisionCoche.nada);
    });

    test('si se desconecta antes de volver, o pasa demasiado, ya no se abre', () {
      final p = _conCoche();
      final d = DecisorCoche()..alConectar(_coche.direccion, p, aLaVista: false, ahora: t0);
      d.alDesconectar(_coche.direccion);
      expect(d.alVolver(p, ahora: t0), isFalse);

      final d2 = DecisorCoche(caducidad: const Duration(minutes: 30))
        ..alConectar(_coche.direccion, p, aLaVista: false, ahora: t0);
      expect(d2.alVolver(p, ahora: t0.add(const Duration(minutes: 31))), isFalse);
    });

    test('si lo apagan mientras estaba pendiente, no se abre', () {
      final p = _conCoche();
      final d = DecisorCoche()..alConectar(_coche.direccion, p, aLaVista: false, ahora: t0);
      p.abrirSolo = false;
      expect(d.alVolver(p, ahora: t0), isFalse);
    });

    test('marcado a mano cuenta como abierto en esta conexión', () {
      final d = DecisorCoche()..marcarAbierto(_coche.direccion.toLowerCase());
      expect(d.alConectar(_coche.direccion, _conCoche(), aLaVista: true), DecisionCoche.nada);
    });
  });

  group('DispositivoBt', () {
    test('se lee del mapa del canal nativo', () {
      final d = DispositivoBt.deMapa({'direccion': 'aa:bb', 'nombre': ' Mi Carro ', 'coche': true, 'audio': true});
      expect(d.direccion, 'AA:BB');
      expect(d.nombre, 'Mi Carro');
      expect(d.esCoche, isTrue);
      expect(DispositivoBt.deMapa({'direccion': 'x'}).nombreVisible, 'Aparato sin nombre');
    });
  });

  group('uriCaratulaCoche', () {
    test('internet y content:// van tal cual', () {
      expect(uriCaratulaCoche('https://i.ytimg.com/vi/x/hq.jpg').toString(), 'https://i.ytimg.com/vi/x/hq.jpg');
      expect(uriCaratulaCoche('content://otra/cosa').toString(), 'content://otra/cosa');
    });

    test('las del teléfono pasan por el proveedor de Caudal', () {
      expect(uriCaratulaCoche('/data/user/0/com.kevinrr.caudal/app_flutter/portadas_listas/3_1.jpg').toString(),
          'content://com.kevinrr.caudal.caratulas/data/user/0/com.kevinrr.caudal/app_flutter/portadas_listas/3_1.jpg');
      final con = uriCaratulaCoche('file:///storage/emulated/0/Download/Caudal/Musica/Mi%20canci%C3%B3n.PNG');
      expect(con?.scheme, 'content');
      expect(con?.host, autoridadCaratulas);
      expect(con?.path, '/storage/emulated/0/Download/Caudal/Musica/Mi%20canci%C3%B3n.PNG');
      expect(Uri.decodeComponent(con!.path), '/storage/emulated/0/Download/Caudal/Musica/Mi canción.PNG');
    });

    test('nada que no sea una imagen, ni rutas con ..', () {
      for (final a in [null, '', 'null', 'relativa/x.jpg', '/a/b/cancion.mp3', '/a/b/sin_extension', '/a/../etc/x.jpg']) {
        expect(uriCaratulaCoche(a), isNull, reason: '$a');
      }
    });
  });

  group('AccionesCoche', () {
    test('Me gusta solo con algo sonando; el icono cambia con el estado', () {
      final sin = AccionesCoche.controles(hayPista: false, gusta: false, enAleatorio: false);
      expect(sin.map((c) => c.customAction?.name), [AccionesCoche.aleatorio]);

      final con = AccionesCoche.controles(hayPista: true, gusta: true, enAleatorio: true);
      expect(con.map((c) => c.customAction?.name), [AccionesCoche.meGusta, AccionesCoche.aleatorio]);
      expect(con.every((c) => c.action == MediaAction.custom), isTrue);
      expect(con.first.androidIcon, AccionesCoche.iconoMeGustaLleno);
      expect(con.first.label, 'Quitar de me gusta');
      expect(con.last.androidIcon, AccionesCoche.iconoAleatorioPuesto);

      final otro = AccionesCoche.controles(hayPista: true, gusta: false, enAleatorio: false);
      expect(otro.first.androidIcon, AccionesCoche.iconoMeGusta);
      expect(otro.last.androidIcon, AccionesCoche.iconoAleatorio);
    });

    test('la firma cambia con el corazón y con el aleatorio', () {
      final firmas = {
        for (final g in [true, false])
          for (final a in [true, false]) AccionesCoche.firma(gusta: g, enAleatorio: a)
      };
      expect(firmas.length, 4);
    });

    test('atender: corazón, aleatorio y lo que no es suyo', () async {
      Json? gustada;
      var aleatorios = 0;
      Future<bool> alternar(Json p) async {
        gustada = p;
        return true;
      }

      Future<bool> aleatorio() async {
        aleatorios++;
        return true;
      }

      expect(
          await AccionesCoche.atender(AccionesCoche.meGusta,
              actual: {'clave': 'yt:a'}, alternarMeGusta: alternar, alternarAleatorio: aleatorio),
          isTrue);
      expect(gustada?['clave'], 'yt:a');
      expect(
          await AccionesCoche.atender(AccionesCoche.aleatorio,
              actual: null, alternarMeGusta: alternar, alternarAleatorio: aleatorio),
          isTrue);
      expect(aleatorios, 1);
      // corazón sin nada sonando: no hace nada pero es suyo
      gustada = null;
      expect(
          await AccionesCoche.atender(AccionesCoche.meGusta,
              actual: null, alternarMeGusta: alternar, alternarAleatorio: aleatorio),
          isTrue);
      expect(gustada, isNull);
      expect(
          await AccionesCoche.atender('otra', actual: null, alternarMeGusta: alternar, alternarAleatorio: aleatorio),
          isFalse);
    });
  });

  group('recursos de Android', () {
    const res = 'android/app/src/main/res';

    test('los iconos de los botones del coche existen', () {
      for (final i in [
        AccionesCoche.iconoMeGusta,
        AccionesCoche.iconoMeGustaLleno,
        AccionesCoche.iconoAleatorio,
        AccionesCoche.iconoAleatorioPuesto,
      ]) {
        final nombre = i.split('/').last;
        expect(File('$res/drawable/$nombre.xml').existsSync(), isTrue, reason: nombre);
      }
    });

    test('shortcuts.xml: los cuatro accesos llevan a enlaces que la app entiende', () {
      final xml = File('$res/xml/shortcuts.xml').readAsStringSync();
      final datos = RegExp(r'android:data="(caudal://[^"]+)"').allMatches(xml).map((m) => m.group(1)!).toList();
      expect(datos.take(4), ['caudal://megusta', 'caudal://buscar', 'caudal://descargas', 'caudal://mix'],
          reason: 'los cuatro pedidos van primero: son los que enseña el teléfono');
      expect(leerAtajo(datos[0])?.tipo, TipoAtajo.meGustaAleatorio);
      expect(leerAtajo(datos[1])?.tipo, TipoAtajo.buscar);
      expect(leerAtajo(datos[2])?.tipo, TipoAtajo.descargas);
      expect(leerAtajo(datos[3])?.tipo, TipoAtajo.miMix);
      // el estudio de antes sigue ahí
      expect(datos, contains('caudal://estudio'));
      // y los ids que manda el asistente también se entienden
      for (final id in ['megusta', 'buscar', 'descargas', 'mix']) {
        expect(xml, contains('android:shortcutId="$id"'));
        expect(leerAtajo('caudal://funcion?nombre=$id'), isNotNull, reason: id);
      }
      expect(xml, contains('caudal://funcion{?nombre}'));
      expect(xml, contains('caudal://buscar{?q}'));
    });

    test('todo lo que nombra shortcuts.xml existe (textos, frases e iconos)', () {
      final xml = File('$res/xml/shortcuts.xml').readAsStringSync();
      final textos = File('$res/values/strings.xml').readAsStringSync() +
          File('$res/values/strings_coche.xml').readAsStringSync();
      for (final m in RegExp(r'@string/(\w+)').allMatches(xml)) {
        expect(textos, contains('name="${m.group(1)}"'), reason: m.group(0));
      }
      for (final m in RegExp(r'@array/(\w+)').allMatches(xml)) {
        expect(textos, contains('<string-array name="${m.group(1)}"'), reason: m.group(0));
      }
      for (final m in RegExp(r'@drawable/(\w+)').allMatches(xml)) {
        expect(File('$res/drawable/${m.group(1)}.xml').existsSync(), isTrue, reason: m.group(0));
      }
    });

    test('el manifiesto declara el proveedor de carátulas con la autoridad de Dart', () {
      final m = File('android/app/src/main/AndroidManifest.xml').readAsStringSync();
      expect(m, contains('android:name=".CaratulaProveedor"'));
      expect(m, contains(r'android:authorities="${applicationId}.caratulas"'));
      expect(autoridadCaratulas, 'com.kevinrr.caudal.caratulas');
      expect(m, contains('android:name=".CocheReceptor"'));
      expect(m, contains('android:name=".VozActivity"'));
      expect(m, contains('android.permission.BLUETOOTH_CONNECT'));
      expect(m, contains('android.media.action.MEDIA_PLAY_FROM_SEARCH'));
    });
  });
}
