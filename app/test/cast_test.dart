import 'dart:async';
import 'dart:io';

import 'package:caudal/nucleo/streams.dart';
import 'package:caudal/reproduccion/cast.dart';
import 'package:caudal/reproduccion/cast_servidor.dart';
import 'package:caudal/ui/cast_boton.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Un Chromecast de mentira: apunta lo que se le pide y deja simular lo que
/// contaría la tele.
class TeleFalsa implements PuenteCast {
  final dispositivosCtl = StreamController<List<DispositivoCast>>.broadcast();
  final sesionCtl = StreamController<DispositivoCast?>.broadcast();
  final medioCtl = StreamController<EventoCast>.broadcast();
  final posicionCtl = StreamController<Duration>.broadcast();
  final volumenCtl = StreamController<double>.broadcast();
  final ordenes = <String>[];
  final cargados = <(MedioCast, Duration, bool)>[];
  bool buscando = false;
  bool aceptar = true;
  double vol = 0.4;

  @override
  bool get disponible => true;
  @override
  Future<bool> preparar() async => true;
  @override
  Stream<List<DispositivoCast>> get dispositivos => dispositivosCtl.stream;
  @override
  Future<void> buscar() async => buscando = true;
  @override
  Future<void> dejarDeBuscar() async => buscando = false;
  @override
  Future<bool> conectar(DispositivoCast d) async {
    ordenes.add('conectar ${d.nombre}');
    if (!aceptar) return false;
    scheduleMicrotask(() {
      sesionCtl.add(d);
      volumenCtl.add(vol);
    });
    return true;
  }

  @override
  Future<void> desconectar() async {
    ordenes.add('desconectar');
    scheduleMicrotask(() => sesionCtl.add(null));
  }

  @override
  Stream<DispositivoCast?> get sesion => sesionCtl.stream;
  @override
  Stream<EventoCast> get medio => medioCtl.stream;
  @override
  Stream<Duration> get posicion => posicionCtl.stream;
  @override
  Stream<double> get volumen => volumenCtl.stream;
  @override
  Future<void> cargar(MedioCast m, {Duration desde = Duration.zero, bool sonar = true}) async {
    cargados.add((m, desde, sonar));
    ordenes.add('cargar');
  }

  @override
  Future<void> sonar() async => ordenes.add('sonar');
  @override
  Future<void> pausar() async => ordenes.add('pausar');
  @override
  Future<void> irA(Duration p) async => ordenes.add('irA ${p.inSeconds}');
  @override
  Future<void> fijarVolumen(double v) async {
    vol = v;
    ordenes.add('volumen $v');
  }

  @override
  Future<void> parar() async => ordenes.add('parar');

  /// La tele cuenta lo que hace con lo último que se le cargó.
  void dice(EstadoMedioCast e, {Duration? duracion}) =>
      medioCtl.add(EventoCast(e, duracion: duracion, url: cargados.isEmpty ? null : cargados.last.$1.url));
}

class ServidorFalso implements ServidorCast {
  final archivos = <String>[];
  final remotos = <String>[];
  bool sinWifi = false;
  @override
  Future<String?> publicarArchivo(String ruta, {String? tipo}) async {
    if (sinWifi) return null;
    archivos.add(ruta);
    return 'http://192.168.1.20:5000/a/${archivos.length}';
  }

  @override
  Future<String?> publicarRemoto(String url, {String? tipo}) async {
    remotos.add(url);
    return 'http://192.168.1.20:5000/p/${remotos.length}';
  }

  @override
  Future<void> cerrar() async {}
}

/// Un reproductor de mentira con lo mismo que el de verdad le da al control.
class ReproFalso {
  Map<String, dynamic>? pista;
  Fuente? fuente;
  String estado = 'parado';
  final posicion = ValueNotifier(Duration.zero);
  final duracion = ValueNotifier(const Duration(minutes: 3));
  int callado = 0;
  final vueltas = <(Duration, bool)>[];
  final avisos = <String>[];
  int siguientes = 0;
  List<Map<String, dynamic>> cola = [];
  ControlCast? cast;

  AnfitrionCast anfitrion() => AnfitrionCast(
        pista: () => pista,
        fuente: () => fuente,
        posicion: posicion,
        duracion: duracion,
        sonandoLocal: () => estado == 'sonando' || estado == 'cargando',
        fijarEstado: (e) => estado = e,
        callarLocal: () async => callado++,
        volverLocal: (p, sonar) async {
          vueltas.add((p, sonar));
          estado = sonar ? 'sonando' : 'parado';
          posicion.value = p;
        },
        siguiente: () async {
          siguientes++;
          if (cola.isEmpty) return;
          pista = cola.removeAt(0);
          fuente = Fuente(url: 'https://rr1.googlevideo.com/videoplayback?mime=audio%2Fwebm&id=${pista!['video_id']}',
              audioCodec: 'opus');
          // como el reproductor: al estar conectado, la canción va a la tele
          if (cast?.activo == true) await cast!.enviar(pista!, fuente!);
        },
        aviso: avisos.add,
      );
}

Future<void> pausa() => Future<void>.delayed(const Duration(milliseconds: 5));

void main() {
  const sala = DispositivoCast(id: 'tv1', nombre: 'Tele de la sala', modelo: 'Chromecast');
  const altavoz = DispositivoCast(id: 'al1', nombre: 'Cocina', modelo: 'Google Nest Audio');

  late TeleFalsa tele;
  late ServidorFalso servidor;
  late ReproFalso r;
  late ControlCast c;

  setUp(() async {
    tele = TeleFalsa();
    servidor = ServidorFalso();
    r = ReproFalso();
    c = ControlCast(r.anfitrion(), puente: tele, servidor: servidor);
    r.cast = c;
    await pausa();
  });

  tearDown(() => c.dispose());

  Map<String, dynamic> cancion(String id) =>
      {'video_id': id, 'titulo': 'Canción $id', 'artista': 'Artista', 'album': {'nombre': 'Disco'},
        'miniatura': 'https://lh3.googleusercontent.com/abc=w120-h120-l90-rj'};

  test('aparece cuando el teléfono tiene Cast y lista lo que encuentra', () async {
    expect(c.soportado, isTrue);
    await c.buscarDispositivos();
    expect(tele.buscando, isTrue);
    tele.dispositivosCtl.add([sala, altavoz]);
    await pausa();
    expect(c.dispositivos.map((d) => d.nombre), ['Tele de la sala', 'Cocina']);
    expect(altavoz.esAltavoz, isTrue);
    expect(sala.esAltavoz, isFalse);
    await c.dejarDeBuscar();
    expect(tele.buscando, isFalse);
  });

  test('sin Cast (web, PC) el botón no aparece', () async {
    final otro = ControlCast(r.anfitrion(), puente: PuenteNulo(), servidor: ServidorNulo());
    await pausa();
    expect(otro.soportado, isFalse);
    otro.dispose();
  });

  test('conectar: lo que suena en el teléfono pasa a la tele en el mismo punto', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://rr1.googlevideo.com/videoplayback?mime=audio%2Fwebm&ip=1.2.3.4', audioCodec: 'opus');
    r.estado = 'sonando';
    r.posicion.value = const Duration(seconds: 42);
    await c.conectar(sala);
    await pausa();
    expect(c.activo, isTrue);
    expect(c.dispositivo, sala);
    expect(c.volumen, 0.4);
    expect(r.callado, 1, reason: 'el teléfono se calla');
    final (m, desde, sonar) = tele.cargados.single;
    expect(m.url, startsWith('https://rr1.googlevideo.com/'), reason: 'el enlace de YouTube va directo');
    expect(m.tipo, 'audio/webm');
    expect(m.titulo, 'Canción a');
    expect(m.artista, 'Artista');
    expect(m.album, 'Disco');
    expect(m.caratula, contains('=w720-h720'));
    expect(desde, const Duration(seconds: 42));
    expect(sonar, isTrue);
    expect(r.estado, 'cargando');
    tele.dice(EstadoMedioCast.sonando);
    await pausa();
    expect(r.estado, 'sonando');
  });

  test('pausar, seguir y mover la barra mandan a la tele', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fmp4', audioCodec: 'mp4a');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    tele.dice(EstadoMedioCast.sonando);
    tele.posicionCtl.add(const Duration(seconds: 10));
    await pausa();
    expect(r.posicion.value, const Duration(seconds: 10));

    await c.pausar();
    expect(tele.ordenes.last, 'pausar');
    expect(r.estado, 'pausa');
    tele.dice(EstadoMedioCast.pausa);
    await pausa();

    await c.reanudar();
    expect(tele.ordenes.last, 'sonar');
    expect(r.estado, 'sonando');

    await c.irA(const Duration(seconds: 95));
    expect(tele.ordenes.last, 'irA 95');
    expect(r.posicion.value, const Duration(seconds: 95));

    await c.fijarVolumen(0.8);
    expect(tele.ordenes.last, 'volumen 0.8');
    expect(c.volumen, 0.8);
  });

  test('la barra avanza sola mientras suena en la tele', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fwebm');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    tele.dice(EstadoMedioCast.sonando);
    tele.posicionCtl.add(const Duration(seconds: 20));
    await Future<void>.delayed(const Duration(milliseconds: 1100));
    expect(r.posicion.value, greaterThanOrEqualTo(const Duration(seconds: 21)));
    expect(r.posicion.value, lessThan(const Duration(seconds: 23)));
  });

  test('al terminar una canción en la tele, pasa a la siguiente de la cola', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fwebm');
    r.estado = 'sonando';
    r.cola = [cancion('b')];
    await c.conectar(sala);
    await pausa();
    tele.dice(EstadoMedioCast.sonando);
    await pausa();
    tele.dice(EstadoMedioCast.terminado);
    await pausa();
    expect(r.siguientes, 1);
    expect(tele.cargados.length, 2);
    expect(tele.cargados.last.$1.titulo, 'Canción b');
    expect(tele.cargados.last.$2, Duration.zero);
  });

  test('un «terminado» de la canción anterior no salta otra', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fwebm&a');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    tele.dice(EstadoMedioCast.sonando);
    // el usuario pasa a otra: la tele avisa luego de que la anterior se cortó/terminó
    final viejo = tele.cargados.last.$1.url;
    r.pista = cancion('b');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fwebm&b');
    await c.enviar(r.pista!, r.fuente!);
    tele.medioCtl.add(EventoCast(EstadoMedioCast.terminado, url: viejo));
    await pausa();
    expect(r.siguientes, 0);
    // y antes de que la nueva empiece, un «terminado» tampoco cuenta
    tele.dice(EstadoMedioCast.terminado);
    await pausa();
    expect(r.siguientes, 0);
  });

  test('si la tele no puede abrir el enlace, se repite a través del teléfono', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fwebm');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    tele.dice(EstadoMedioCast.error);
    await pausa();
    expect(servidor.remotos, ['https://x.googlevideo.com/v?mime=audio%2Fwebm']);
    expect(tele.cargados.length, 2);
    expect(tele.cargados.last.$1.url, startsWith('http://192.168.1.20:5000/p/'));
    expect(tele.cargados.last.$1.tipo, 'audio/webm');
    // si tampoco, se avisa y sigue la siguiente
    tele.dice(EstadoMedioCast.error);
    await Future<void>.delayed(const Duration(milliseconds: 1300));
    expect(r.avisos.last, contains('no pudo reproducir'));
    expect(r.siguientes, 1);
  });

  test('las descargas las sirve el teléfono', () async {
    r.pista = {...cancion('a'), 'miniatura': '/data/caratulas/a.jpg'};
    r.fuente = Fuente.archivo('/data/musica/Canción a.m4a');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    expect(servidor.archivos, ['/data/musica/Canción a.m4a', '/data/caratulas/a.jpg']);
    final m = tele.cargados.single.$1;
    expect(m.url, 'http://192.168.1.20:5000/a/1');
    expect(m.tipo, 'audio/mp4');
    expect(m.caratula, 'http://192.168.1.20:5000/a/2');
  });

  test('descargas sin wifi: se explica en vez de fallar callado', () async {
    servidor.sinWifi = true;
    r.pista = cancion('a');
    r.fuente = Fuente.archivo('/data/musica/a.mp3');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    expect(tele.cargados, isEmpty);
    expect(r.avisos.last, contains('wifi'));
    expect(r.estado, 'parado');
  });

  test('desconectar: la música vuelve al teléfono en el mismo punto', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fwebm');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    tele.dice(EstadoMedioCast.sonando);
    tele.posicionCtl.add(const Duration(seconds: 77));
    await pausa();
    await c.desconectar();
    await pausa();
    expect(c.activo, isFalse);
    expect(c.dispositivo, isNull);
    expect(tele.ordenes, contains('desconectar'));
    expect(r.vueltas.single.$1.inSeconds, 77);
    expect(r.vueltas.single.$2, isTrue, reason: 'sonaba: sigue sonando');
  });

  test('desconectar en pausa: vuelve al teléfono en pausa', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fwebm');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    tele.dice(EstadoMedioCast.sonando);
    tele.posicionCtl.add(const Duration(seconds: 30));
    await pausa();
    await c.pausar();
    await c.desconectar();
    await pausa();
    expect(r.vueltas.single.$1.inSeconds, 30);
    expect(r.vueltas.single.$2, isFalse);
  });

  test('si la tele se apaga o se va la wifi, sigue en el teléfono y se avisa', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fwebm');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    tele.dice(EstadoMedioCast.sonando);
    tele.posicionCtl.add(const Duration(seconds: 50));
    await pausa();
    tele.sesionCtl.add(null);
    await pausa();
    expect(c.activo, isFalse);
    expect(r.vueltas.single.$1.inSeconds, inInclusiveRange(50, 51));
    expect(r.avisos.last, contains('Sigue sonando en el teléfono'));
  });

  test('conectar sin nada sonando: solo queda conectado', () async {
    await c.conectar(altavoz);
    await pausa();
    expect(c.activo, isTrue);
    expect(tele.cargados, isEmpty);
    expect(r.callado, 0);
  });

  test('si la tele no acepta la conexión, se dice en una frase', () async {
    tele.aceptar = false;
    await c.conectar(sala);
    await pausa();
    expect(c.activo, isFalse);
    expect(c.conexion, ConexionCast.desconectado);
    expect(r.avisos.last, contains('misma wifi'));
  });

  test('la misma canción otra vez (cambiar a video, reintentos) no corta la tele', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fwebm');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    tele.dice(EstadoMedioCast.sonando);
    tele.posicionCtl.add(const Duration(seconds: 12));
    await pausa();
    // modo video: imagen y sonido aparte, el sonido es el mismo enlace
    await c.enviar(r.pista!, Fuente(url: 'https://x.googlevideo.com/video', audioUrl: r.fuente!.url, alto: 1080),
        inicio: const Duration(seconds: 12));
    expect(tele.cargados.length, 1);
  });

  test('parar (fin de la cola, temporizador) para la tele; seguir la vuelve a mandar', () async {
    r.pista = cancion('a');
    r.fuente = Fuente(url: 'https://x.googlevideo.com/v?mime=audio%2Fwebm');
    r.estado = 'sonando';
    await c.conectar(sala);
    await pausa();
    tele.dice(EstadoMedioCast.sonando);
    await c.parar();
    expect(tele.ordenes.last, 'parar');
    await c.reanudar();
    expect(tele.cargados.length, 2);
  });

  test('tipos y carátulas', () {
    expect(tipoDeFuente(Fuente(url: 'https://a/v?mime=audio%2Fmp4')), 'audio/mp4');
    expect(tipoDeFuente(Fuente(url: 'https://a/v', audioCodec: 'opus')), 'audio/webm');
    expect(tipoDeFuente(Fuente(url: 'https://a/v', alto: 720)), 'video/mp4');
    expect(tipoDeFuente(Fuente.archivo('/m/x.MP3')), 'audio/mpeg');
    expect(tipoDeFuente(Fuente.archivo('/m/x.flac')), 'audio/flac');
    expect(caratulaGrande('https://i.ytimg.com/vi/abc/mqdefault.jpg'), 'https://i.ytimg.com/vi/abc/hqdefault.jpg');
    expect(caratulaGrande('https://lh3.googleusercontent.com/x=w60-h60-l90-rj'),
        'https://lh3.googleusercontent.com/x=w720-h720-l90-rj');
  });

  group('botón', () {
    Widget app(ControlCast control) =>
        MaterialApp(home: Scaffold(appBar: AppBar(actions: [CastBoton(control: control)])));

    testWidgets('sin Cast no aparece', (t) async {
      final otro = ControlCast(r.anfitrion(), puente: PuenteNulo(), servidor: ServidorNulo());
      await t.pumpWidget(app(otro));
      expect(find.byType(IconButton), findsNothing);
      otro.dispose();
    });

    testWidgets('busca, explica la wifi si no hay nada y conecta', (t) async {
      await t.binding.setSurfaceSize(const Size(800, 1400));
      addTearDown(() => t.binding.setSurfaceSize(null));
      await t.pumpWidget(app(c));
      expect(find.byIcon(Icons.cast_rounded), findsOneWidget);
      await t.tap(find.byIcon(Icons.cast_rounded));
      await t.pump(const Duration(milliseconds: 400));
      expect(find.text('Buscando teles y altavoces…'), findsOneWidget);
      expect(tele.buscando, isTrue);
      await t.pump(const Duration(seconds: 9));
      expect(find.textContaining('misma wifi'), findsOneWidget);
      tele.dispositivosCtl.add([sala, altavoz]);
      await t.pump();
      expect(find.text('Tele de la sala'), findsOneWidget);
      expect(find.text('Cocina'), findsOneWidget);
      await t.tap(find.text('Tele de la sala'));
      await t.pump();
      await t.pump(const Duration(milliseconds: 500));
      expect(c.activo, isTrue);
      expect(tele.buscando, isFalse, reason: 'al cerrar la hoja deja de buscar');
      expect(find.byIcon(Icons.cast_connected_rounded), findsOneWidget);
      // con conexión: volumen y volver al teléfono
      await t.tap(find.byIcon(Icons.cast_connected_rounded));
      await t.pump();
      await t.pump(const Duration(milliseconds: 400));
      expect(find.text('Sonando en Tele de la sala'), findsOneWidget);
      expect(find.byType(Slider), findsOneWidget);
      await t.tap(find.text('Volver a escuchar en el teléfono'));
      await t.pump();
      await t.pump(const Duration(milliseconds: 500));
      expect(c.activo, isFalse);
      expect(find.byIcon(Icons.cast_rounded), findsOneWidget);
    });
  });

  group('servidor del teléfono', () {
    late Directory dir;
    late File archivo;
    late ServidorCastIo s;
    final datos = List<int>.generate(10000, (i) => i % 251);

    setUp(() async {
      // los testWidgets de arriba dejan puesto un HttpClient de mentira (todo 400)
      HttpOverrides.global = null;
      dir = await Directory.systemTemp.createTemp('cast_prueba');
      archivo = File('${dir.path}${Platform.pathSeparator}canción.m4a')..writeAsBytesSync(datos);
      s = ServidorCastIo(ip: '127.0.0.1');
    });

    tearDown(() async {
      await s.cerrar();
      await dir.delete(recursive: true);
    });

    Future<(int, Map<String, String>, List<int>)> pedir(String url, {String? rango, String metodo = 'GET'}) async {
      final cli = HttpClient();
      final p = await cli.openUrl(metodo, Uri.parse(url));
      if (rango != null) p.headers.set(HttpHeaders.rangeHeader, rango);
      final r = await p.close();
      final cuerpo = <int>[];
      await for (final t in r) {
        cuerpo.addAll(t);
      }
      final cab = <String, String>{};
      r.headers.forEach((k, v) => cab[k] = v.join(','));
      cli.close();
      return (r.statusCode, cab, cuerpo);
    }

    test('sirve el archivo entero y a trozos (Range)', () async {
      final url = (await s.publicarArchivo(archivo.path))!;
      expect(url, startsWith('http://127.0.0.1:'));
      expect(url, endsWith('.m4a'));

      var (st, cab, cuerpo) = await pedir(url);
      expect(st, 200);
      expect(cab['content-type'], 'audio/mp4');
      expect(cab['accept-ranges'], 'bytes');
      expect(cuerpo, datos);

      (st, cab, cuerpo) = await pedir(url, rango: 'bytes=100-199');
      expect(st, 206);
      expect(cab['content-range'], 'bytes 100-199/10000');
      expect(cab['content-length'], '100');
      expect(cuerpo, datos.sublist(100, 200));

      (st, cab, cuerpo) = await pedir(url, rango: 'bytes=9000-');
      expect(st, 206);
      expect(cab['content-range'], 'bytes 9000-9999/10000');
      expect(cuerpo, datos.sublist(9000));

      (st, cab, cuerpo) = await pedir(url, rango: 'bytes=-500');
      expect(st, 206);
      expect(cuerpo, datos.sublist(9500));

      (st, cab, cuerpo) = await pedir(url, rango: 'bytes=20000-');
      expect(st, 416);
      expect(cab['content-range'], 'bytes */10000');

      (st, cab, cuerpo) = await pedir(url, metodo: 'HEAD');
      expect(st, 200);
      expect(cab['content-length'], '10000');
      expect(cuerpo, isEmpty);
    });

    test('no deja leer nada que no se haya publicado', () async {
      final url = (await s.publicarArchivo(archivo.path))!;
      final base = url.substring(0, url.indexOf('/a/'));
      expect((await pedir('$base/a/1234')).$1, 404);
      expect((await pedir('$base/etc/passwd')).$1, 404);
      expect((await pedir('$base/a/..%2F..%2Fetc')).$1, 404);
      expect(await s.publicarArchivo('${dir.path}/no_existe.mp3'), isNull);
    });

    test('la misma ruta da la misma dirección', () async {
      expect(await s.publicarArchivo(archivo.path), await s.publicarArchivo(archivo.path));
    });

    test('repite un stream remoto respetando Range', () async {
      // un «YouTube» de mentira en otro puerto
      final origen = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      origen.listen((p) async {
        final (a, b) = rangoPedido(p.headers.value('range'), datos.length)!;
        p.response.statusCode = p.headers.value('range') == null ? 200 : 206;
        p.response.headers.set('content-type', 'audio/webm');
        p.response.headers.set('content-range', 'bytes $a-$b/${datos.length}');
        p.response.contentLength = b - a + 1;
        p.response.add(datos.sublist(a, b + 1));
        await p.response.close();
      });
      final url = (await s.publicarRemoto('http://127.0.0.1:${origen.port}/videoplayback?x=1'))!;
      final (st, cab, cuerpo) = await pedir(url, rango: 'bytes=10-19');
      expect(st, 206);
      expect(cab['content-type'], 'audio/webm');
      expect(cab['content-range'], 'bytes 10-19/10000');
      expect(cuerpo, datos.sublist(10, 20));
      await origen.close(force: true);
    });

    test('rangoPedido', () {
      expect(rangoPedido(null, 100), (0, 99));
      expect(rangoPedido('bytes=0-', 100), (0, 99));
      expect(rangoPedido('bytes=10-20', 100), (10, 20));
      expect(rangoPedido('bytes=90-500', 100), (90, 99));
      expect(rangoPedido('bytes=-10', 100), (90, 99));
      expect(rangoPedido('bytes=-1000', 100), (0, 99));
      expect(rangoPedido('bytes=100-', 100), isNull);
      expect(rangoPedido('bytes=20-10', 100), isNull);
      expect(rangoPedido('bytes=-', 100), isNull);
      expect(rangoPedido('bytes=0-10,20-30', 100), (0, 10));
    });

    test('solo direcciones de casa', () {
      expect(ServidorCastIo.esPrivada('192.168.1.5'), isTrue);
      expect(ServidorCastIo.esPrivada('10.0.0.2'), isTrue);
      expect(ServidorCastIo.esPrivada('172.20.1.1'), isTrue);
      expect(ServidorCastIo.esPrivada('172.40.1.1'), isFalse);
      expect(ServidorCastIo.esPrivada('100.64.3.2'), isFalse);
    });
  });
}
