import 'package:caudal/nucleo/fiesta.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

/// Una base de fiesta en memoria con las mismas reglas que supabase/fiesta.sql (cola por votos,
/// límite por invitado, quitar, tomar, sonando y cerrar). Las reglas de verdad se prueban en
/// supabase/pruebas/fiesta.prueba.mjs; aquí se prueba lo que hace la app con ellas.
class BaseFalsa {
  final llamadas = <String>[];
  final cola = <Map<String, dynamic>>[];
  final sonadas = <Map<String, dynamic>>[];
  Map<String, dynamic>? sonando;
  bool abierta = true;
  int limite = 5;
  int version = 1;
  int _id = 0;

  void pedir(String vid, {String nombre = 'Ana', int votos = 0}) {
    cola.add({'id': ++_id, 'video_id': vid, 'titulo': 'Canción $vid', 'artista': 'Artista', 'duracion': 200,
        'nombre': nombre, 'votos': votos, 'estado': 'cola', 'miniatura': 'https://i.ytimg.com/vi/$vid/hqdefault.jpg'});
    version++;
  }

  Map<String, dynamic> ver() => {
        'codigo': 'ABC234', 'nombre': 'Cumple', 'abierta': abierta, 'limite': limite, 'version': version,
        'invitados': 2, 'sonando': sonando, 'cola': ordenada(), 'sonadas': sonadas,
      };

  List<Map<String, dynamic>> ordenada() => [...cola]
    ..sort((a, b) => (b['votos'] as int) != (a['votos'] as int)
        ? (b['votos'] as int) - (a['votos'] as int)
        : (a['id'] as int) - (b['id'] as int));

  Future<dynamic> llamar(String nombre, Map<String, dynamic> p) async {
    llamadas.add(nombre);
    if (nombre != 'fiesta_crear' && nombre != 'fiesta_ver' && p['p_clave'] != 'secreta') {
      throw const ErrorFiesta('Solo el anfitrión puede hacer eso en esta fiesta.');
    }
    switch (nombre) {
      case 'fiesta_crear':
        limite = p['p_limite'] as int;
        return {'codigo': 'ABC234', 'clave': 'secreta'};
      case 'fiesta_ver':
        return ver();
      case 'fiesta_quitar':
        cola.removeWhere((c) => c['id'] == p['p_cancion']);
      case 'fiesta_limite':
        limite = p['p_limite'] as int;
      case 'fiesta_cerrar':
        abierta = false;
        sonando = null;
      case 'fiesta_tomar':
        if (!abierta || cola.isEmpty) return null;
        final c = ordenada().first;
        cola.remove(c);
        version++;
        return {...c, 'estado': 'sonando'};
      case 'fiesta_sonando':
        sonando = p['p_pista'] as Map<String, dynamic>?;
      default:
        throw StateError(nombre);
    }
    version++;
    return ver();
  }
}

class ReproductorFalso extends ChangeNotifier implements ControlFiesta {
  @override
  Json? actual;
  @override
  List<Json> proximas = [];
  @override
  bool parado = true;
  @override
  bool enPausa = false;
  @override
  int posicionMs = 0;
  @override
  int duracionMs = 0;
  final puestas = <String>[];

  void sonar(Json p, {int dur = 200000, int pos = 0}) {
    actual = p;
    parado = false;
    enPausa = false;
    duracionMs = dur;
    posicionMs = pos;
    notifyListeners();
  }

  @override
  void ponerDespues(Json pista) {
    proximas.insert(0, pista);
    puestas.add('despues:${pista['video_id']}');
    notifyListeners();
  }

  @override
  Future<void> ponerAhora(Json pista) async {
    puestas.add('ahora:${pista['video_id']}');
    sonar(pista);
  }

  /// Termina la canción y pasa a la siguiente de la cola.
  void avanzar() {
    if (proximas.isEmpty) {
      actual = null;
      parado = true;
      notifyListeners();
      return;
    }
    sonar(proximas.removeAt(0));
  }
}

Json pistaSuelta(String vid) => {'video_id': vid, 'titulo': 'Mía $vid', 'artista': 'Yo', 'duracion': 180};

void main() {
  group('modelos', () {
    test('lee fiesta_ver y ordena la cola como la base', () {
      final e = EstadoFiesta.desde({
        'codigo': 'ABC234', 'nombre': '', 'abierta': true, 'limite': 3, 'version': 4, 'invitados': 7,
        'cola': [
          {'id': 5, 'video_id': 'BBBBBBBBBBB', 'titulo': 'B', 'votos': 1},
          {'id': 3, 'video_id': 'CCCCCCCCCCC', 'titulo': 'C', 'votos': 1},
          {'id': 9, 'video_id': 'DDDDDDDDDDD', 'titulo': 'D', 'votos': 4},
          {'id': 10, 'video_id': 'malo', 'titulo': 'X'},
          'basura',
        ],
        'sonadas': [
          {'id': 1, 'video_id': 'AAAAAAAAAAA', 'estado': 'sonando'},
          {'id': 2, 'video_id': 'EEEEEEEEEEE', 'estado': 'sonada'},
        ],
        'sonando': {'video_id': 'AAAAAAAAAAA', 'titulo': 'Suena', 'miniatura': 'javascript:x', 'fiesta_id': 1, 'pausa': true},
      })!;
      expect(e.nombre, 'Fiesta');
      expect(e.cola.map((c) => c.id), [9, 3, 5]);
      expect(e.siguiente!.id, 9);
      expect(e.sonadas.map((c) => c.id), [2]);
      expect(e.sonando!.miniatura, '');
      expect(e.sonando!.pausa, isTrue);
      expect(e.sonando!.fiestaId, 1);
      expect(EstadoFiesta.desde(null), isNull);
    });

    test('la canción pedida se convierte en pista con fiesta_id', () {
      final c = CancionFiesta.desde({'id': 7, 'video_id': 'kJQP7kiw5Fk', 'titulo': 'Despacito', 'artista': 'Luis Fonsi',
          'duracion': 229, 'nombre': 'Beto'})!;
      final p = c.comoPista();
      expect(p['video_id'], 'kJQP7kiw5Fk');
      expect(p['artista'], 'Luis Fonsi');
      expect(p['duracion'], 229);
      expect(p['fiesta_id'], 7);
      expect(p['clave'], 'yt:kJQP7kiw5Fk');
      expect(c.quien, 'Beto');
    });

    test('enlace, código y textos', () {
      expect(enlaceFiesta('ABC234'), 'https://caudal-musica.netlify.app/fiesta/ABC234');
      expect(codigoVisible('ABC234'), 'ABC 234');
      expect(textoLimite(0), contains('todas'));
      expect(textoLimite(1), contains('1 canción'));
      expect(textoLimite(5), contains('5 canciones'));
    });

    test('mensajes de error', () {
      expect(mensajeErrorFiesta(400, '{"code":"P0001","message":"Esta fiesta ya terminó: el anfitrión la cerró."}'),
          startsWith('Esta fiesta ya terminó'));
      expect(mensajeErrorFiesta(404, '{"code":"PGRST202","message":"Could not find the function"}'), contains('todavía no está activa'));
      expect(mensajeErrorFiesta(0, ''), contains('internet'));
      expect(mensajeErrorFiesta(403, '{"code":"42501","message":"permission denied"}'), 'Algo falló. Vuelve a intentarlo.');
    });
  });

  group('cuándo poner la siguiente', () {
    test('casos', () {
      expect(debeTomarSiguiente(hayActual: false, parado: true, restanteMs: null, hayPendiente: false), isTrue);
      expect(debeTomarSiguiente(hayActual: true, parado: true, restanteMs: 100000, hayPendiente: false), isTrue);
      expect(debeTomarSiguiente(hayActual: true, parado: false, restanteMs: 100000, hayPendiente: false), isFalse);
      expect(debeTomarSiguiente(hayActual: true, parado: false, restanteMs: 25000, hayPendiente: false), isTrue);
      expect(debeTomarSiguiente(hayActual: true, parado: false, restanteMs: 3000, hayPendiente: true), isFalse);
      expect(debeTomarSiguiente(hayActual: false, parado: true, restanteMs: null, hayPendiente: true), isFalse);
      expect(debeTomarSiguiente(hayActual: true, parado: false, restanteMs: null, hayPendiente: false), isFalse);
      expect(hayDeFiestaEnCola([pistaSuelta('x'), {'fiesta_id': 3}]), isTrue);
      expect(hayDeFiestaEnCola([pistaSuelta('x')]), isFalse);
    });

    test('lo que se manda como «suena»', () {
      final p = pistaParaSonando({...pistaSuelta('AAAAAAAAAAA'), 'fiesta_id': 4, 'miniatura': 'file:///c'}, posMs: -5, pausa: true)!;
      expect(p['pos_ms'], 0);
      expect(p['pausa'], isTrue);
      expect(p['fiesta_id'], 4);
      expect(p['miniatura'], '');
      expect(pistaParaSonando(null), isNull);
    });
  });

  group('la fiesta del anfitrión', () {
    late BaseFalsa base;
    late ReproductorFalso rep;
    late FiestaAnfitrion f;

    setUp(() async {
      base = BaseFalsa();
      rep = ReproductorFalso();
      f = await FiestaAnfitrion.crear(control: rep, nombre: 'Cumple', limite: 3, llamar: base.llamar, conTiempoReal: false);
    });
    tearDown(() async {
      if (!f.cerrada) await f.cerrar();
    });

    test('crear guarda código, clave y límite', () {
      expect(f.codigo, 'ABC234');
      expect(f.clave, 'secreta');
      expect(base.limite, 3);
      expect(f.estado!.nombre, 'Cumple');
    });

    test('sin nada sonando, la primera pedida suena sola', () async {
      base.pedir('AAAAAAAAAAA');
      await f.refrescar();
      await f.revisarSiguiente();
      expect(rep.puestas, ['ahora:AAAAAAAAAAA']);
      expect(rep.actual!['fiesta_id'], isNotNull);
    });

    test('la más votada va detrás de lo que suena cuando faltan 25 s', () async {
      rep.sonar(pistaSuelta('MIAMIAMIA01'), dur: 200000, pos: 10000);
      base.pedir('AAAAAAAAAAA', votos: 0);
      base.pedir('BBBBBBBBBBB', votos: 3);
      await f.refrescar();
      await f.revisarSiguiente();
      expect(rep.puestas, isEmpty, reason: 'aún falta mucho');
      rep.posicionMs = 180000;
      await f.revisarSiguiente();
      expect(rep.puestas, ['despues:BBBBBBBBBBB']);
      await f.revisarSiguiente();
      expect(rep.puestas.length, 1, reason: 'ya hay una de la fiesta esperando');
      rep.avanzar(); // empieza la pedida
      rep.posicionMs = 190000;
      await f.revisarSiguiente();
      expect(rep.puestas.last, 'despues:AAAAAAAAAAA');
    });

    test('sin modo automático no pone nada; «poner la siguiente» a mano sí', () async {
      f.fijarAutomatico(false);
      base.pedir('AAAAAAAAAAA');
      await f.refrescar();
      await f.revisarSiguiente();
      expect(rep.puestas, isEmpty);
      expect(await f.tomarSiguiente(), isTrue);
      expect(rep.puestas, ['ahora:AAAAAAAAAAA']);
      expect(await f.tomarSiguiente(), isFalse, reason: 'cola vacía');
    });

    test('avisa de lo que suena al cambiar de pista y al pausar', () async {
      rep.sonar({...pistaSuelta('AAAAAAAAAAA'), 'fiesta_id': 1}, pos: 4000);
      await Future<void>.delayed(const Duration(milliseconds: 450));
      expect(base.sonando!['video_id'], 'AAAAAAAAAAA');
      expect(base.sonando!['fiesta_id'], 1);
      expect(base.sonando!['pausa'], isFalse);
      rep.enPausa = true;
      rep.notifyListeners();
      await Future<void>.delayed(const Duration(milliseconds: 950));
      expect(base.sonando!['pausa'], isTrue);
      final n = base.llamadas.where((l) => l == 'fiesta_sonando').length;
      rep.notifyListeners(); // sin cambios: no manda nada
      await Future<void>.delayed(const Duration(milliseconds: 950));
      expect(base.llamadas.where((l) => l == 'fiesta_sonando').length, n);
    });

    test('quitar, cambiar el límite y poner ahora', () async {
      base.pedir('AAAAAAAAAAA');
      base.pedir('BBBBBBBBBBB');
      await f.refrescar();
      await f.quitar(f.estado!.cola.first);
      expect(f.estado!.cola.map((c) => c.videoId), ['BBBBBBBBBBB']);
      await f.fijarLimite(0);
      expect(f.estado!.limite, 0);
      await f.fijarLimite(99);
      expect(base.limite, 50, reason: 'se recorta al máximo');
      rep.sonar(pistaSuelta('MIAMIAMIA01'));
      await f.ponerAhora(f.estado!.cola.first);
      expect(rep.puestas, ['ahora:BBBBBBBBBBB']);
    });

    test('un error de la base se enseña tal cual', () async {
      final mala = BaseFalsa();
      final g = await FiestaAnfitrion.crear(control: ReproductorFalso(), llamar: (n, p) {
        if (n == 'fiesta_quitar') throw const ErrorFiesta('Esa canción ya no está en la cola.');
        return mala.llamar(n, p);
      }, conTiempoReal: false);
      mala.pedir('AAAAAAAAAAA');
      await g.refrescar();
      await g.quitar(g.estado!.cola.first);
      expect(g.error, 'Esa canción ya no está en la cola.');
      await g.cerrar();
    });

    test('cerrar la cierra para todos y suelta el reproductor', () async {
      FiestaAnfitrion.activa.value = f;
      base.pedir('AAAAAAAAAAA');
      await f.cerrar();
      expect(base.abierta, isFalse);
      expect(f.cerrada, isTrue);
      expect(FiestaAnfitrion.activa.value, isNull);
      // ya no pone canciones ni avisa
      final n = base.llamadas.length;
      rep.sonar(pistaSuelta('MIAMIAMIA01'));
      await f.revisarSiguiente();
      expect(await f.tomarSiguiente(), isFalse);
      await Future<void>.delayed(const Duration(milliseconds: 400));
      expect(base.llamadas.length, n);
    });
  });
}
