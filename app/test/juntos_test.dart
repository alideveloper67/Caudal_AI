import 'package:caudal/nucleo/coleccion.dart';
import 'package:caudal/nucleo/juntos.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

/// Un reproductor de mentira cuyo tiempo avanza con el reloj de verdad.
class ReproductorFalso extends ChangeNotifier implements ControlJuntos {
  @override
  Json? pista;
  bool _sonando = false;
  int _base = 0;
  int _desde = 0;
  int cargas = 0;
  int saltos = 0;

  int get _ahora => DateTime.now().millisecondsSinceEpoch;

  @override
  Duration get posicion => Duration(milliseconds: _base + (_sonando ? _ahora - _desde : 0));
  @override
  bool get sonando => _sonando;
  @override
  bool get cargando => false;

  @override
  Future<void> cargar(Json p, {Duration inicio = Duration.zero, bool pausado = false}) async {
    cargas++;
    await Future<void>.delayed(const Duration(milliseconds: 300)); // lo que tarda en abrir
    pista = Json.of(p);
    _base = inicio.inMilliseconds;
    _desde = _ahora;
    _sonando = !pausado;
    notifyListeners();
  }

  @override
  Future<void> buscar(Duration p) async {
    saltos++;
    _base = p.inMilliseconds;
    _desde = _ahora;
    notifyListeners();
  }

  @override
  Future<void> pausar() async {
    _base = posicion.inMilliseconds;
    _sonando = false;
    notifyListeners();
  }

  @override
  Future<void> reanudar() async {
    _desde = _ahora;
    _sonando = true;
    notifyListeners();
  }

  /// Lo que haria el usuario del anfitrion.
  void poner(Json p, Duration en) {
    pista = p;
    _base = en.inMilliseconds;
    _desde = _ahora;
    _sonando = true;
    notifyListeners();
  }
}

Future<void> hastaQue(bool Function() condicion, String que, {Duration max = const Duration(seconds: 15)}) async {
  final fin = DateTime.now().add(max);
  while (!condicion()) {
    if (DateTime.now().isAfter(fin)) fail('No pasó a tiempo: $que');
    await Future<void>.delayed(const Duration(milliseconds: 100));
  }
}

void main() {
  group('piezas', () {
    test('código de sala y enlace', () {
      final c = nuevoCodigoSala();
      expect(c.length, 6);
      expect(codigoDeTexto(c), c);
      expect(codigoDeTexto(enlaceSala(c)), c);
      expect(codigoDeTexto(' ab-c 234 '), 'ABC234');
      expect(codigoDeTexto('https://caudal.app/juntos?sala=XYZ789'), 'XYZ789');
      expect(codigoDeTexto('hola'), isNull);
      expect(codigoDeTexto('ABCDEF0'), isNull);
    });

    test('posición esperada con el reloj del anfitrión', () {
      // el anfitrion va 10 s adelantado y mando "30 s" hace 2 s (de su reloj)
      final p = posicionEsperada(posMs: 30000, sonando: true, enviadoMs: 1000000 + 8000,
          diferencia: 10000, ahoraLocal: 1000000);
      expect(p, const Duration(seconds: 32));
      expect(posicionEsperada(posMs: 30000, sonando: false, enviadoMs: 0, diferencia: 0),
          const Duration(seconds: 30));
    });

    test('la pista que se comparte no lleva rutas locales', () {
      final p = pistaParaCompartir({'video_id': 'a', 'titulo': 't', 'archivo': '/x.m4a', 'raro': [1]});
      expect(p, {'video_id': 'a', 'titulo': 't'});
    });
  });

  test('sala real en Supabase Realtime: dos clientes en el mismo proceso', () async {
    final a = ReproductorFalso();
    final b = ReproductorFalso();
    final cancion = {'video_id': 'dQw4w9WgXcQ', 'titulo': 'Prueba', 'artista': 'Caudal', 'duracion': 213};
    a.poner(cancion, const Duration(seconds: 30));

    SalaJuntos? anf;
    SalaJuntos? inv;
    try {
      anf = await SalaJuntos.crear(control: a, nombre: 'Ana', usuario: 'ana');
    } on ErrorJuntos catch (e) {
      fail('Realtime no disponible en el proyecto: $e');
    }
    try {
      expect(anf.soyAnfitrion, isTrue);
      final reaccionesAnf = <String>[];
      anf.reacciones.listen((r) => reaccionesAnf.add(r.emoji));

      // con otra cuenta, mismo codigo (tambien vale el enlace)
      inv = await SalaJuntos.unirse(anf.enlace, control: b, nombre: 'Beto', usuario: 'beto');
      final i = inv;
      await hastaQue(() => anf!.miembros.length == 2 && i.miembros.length == 2, 'los dos en la lista');
      expect(i.miembros.map((m) => m.nombre).toSet(), {'Ana', 'Beto'});

      await hastaQue(() => b.pista?['video_id'] == 'dQw4w9WgXcQ', 'el invitado carga la canción');
      expect(i.anfitrionId, anf.miId);
      expect(i.soyAnfitrion, isFalse);
      await hastaQue(() => (b.posicion - a.posicion).inMilliseconds.abs() < 1500 && b.sonando, 'van a la par');

      // pausa
      await a.pausar();
      await hastaQue(() => !b.sonando, 'la pausa llega');
      await hastaQue(() => (b.posicion - a.posicion).inMilliseconds.abs() < 1500, 'pausados en el mismo punto');

      // seguir y saltar
      await a.reanudar();
      await a.buscar(const Duration(seconds: 120));
      await hastaQue(() => b.sonando && (b.posicion - a.posicion).inMilliseconds.abs() < 1500,
          'el salto llega');
      expect(b.posicion.inSeconds, greaterThanOrEqualTo(119));

      // otra cancion
      a.poner({'video_id': 'kJQP7kiw5Fk', 'titulo': 'Otra', 'duracion': 280}, const Duration(seconds: 5));
      await hastaQue(() => b.pista?['video_id'] == 'kJQP7kiw5Fk', 'cambia la canción');
      await hastaQue(() => (b.posicion - a.posicion).inMilliseconds.abs() < 1500, 'a la par otra vez');

      // reacciones
      i.reaccionar('🔥');
      await hastaQue(() => reaccionesAnf.contains('🔥'), 'la reacción llega');

      // el anfitrion se va: el invitado pasa a serlo
      await anf.salir();
      await hastaQue(() => i.soyAnfitrion, 'pasa el mando', max: const Duration(seconds: 40));
      await hastaQue(() => i.miembros.length == 1, 'queda uno');
    } finally {
      await anf.salir();
      await inv?.salir();
    }
  }, timeout: const Timeout(Duration(seconds: 120)));
}
