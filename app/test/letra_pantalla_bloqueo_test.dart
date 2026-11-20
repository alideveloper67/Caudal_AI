import 'package:caudal/nucleo/letra_pantalla_bloqueo.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _Puente extends PuenteLetraBloqueo {
  final mostrados = <Map<String, Object?>>[];
  int quitados = 0;

  @override
  Future<void> mostrar(Map<String, Object?> datos) async => mostrados.add(Map.of(datos));

  @override
  Future<void> quitar() async => quitados++;
}

class _Rep extends ChangeNotifier {
  Map<String, dynamic>? actual;
  bool sonando = false;
  bool parado = true;
  final posicion = ValueNotifier(Duration.zero);

  void poner(Map<String, dynamic>? p, {bool suena = true}) {
    actual = p;
    sonando = suena;
    parado = p == null;
    notifyListeners();
  }
}

const cancion = {'clave': 'yt:1', 'titulo': 'Uno', 'artista': 'A'};
const otra = {'clave': 'yt:2', 'titulo': 'Dos', 'artista': 'B'};

Map<String, dynamic> letra(List<(int, String)> l) => {
      'lineas': [for (final (ms, t) in l) [ms, t]],
    };

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late _Puente puente;
  late _Rep r;
  late LetraEnBloqueo l;

  Future<void> armar({bool activa = true, Map<String, Map<String, dynamic>>? letras}) async {
    SharedPreferences.setMockInitialValues({LetraEnBloqueo.clavePref: activa});
    puente = _Puente();
    r = _Rep();
    final todas = letras ??
        {
          'yt:1': letra([(1000, 'Primera línea'), (4000, 'Segunda línea'), (8000, 'Tercera')]),
        };
    l = LetraEnBloqueo(puente: puente, cargarLetra: (p) async => todas['${p['clave']}']);
    await l.leerAjuste();
    l.enlazarCon(
      cambios: r,
      posicion: r.posicion,
      actual: () => r.actual,
      sonando: () => r.sonando,
      parado: () => r.parado,
    );
  }

  test('enseña el verso que suena y solo avisa al cambiar de verso', () async {
    await armar();
    r.poner(Map.of(cancion));
    await pumpEventQueue();
    // antes del primer verso: nota y el que viene
    expect(puente.mostrados.last['linea'], '♪');
    expect(puente.mostrados.last['siguiente'], 'Primera línea');
    r.posicion.value = const Duration(milliseconds: 1200);
    expect(puente.mostrados.last['linea'], 'Primera línea');
    expect(puente.mostrados.last['siguiente'], 'Segunda línea');
    final n = puente.mostrados.length;
    r.posicion.value = const Duration(milliseconds: 2500); // mismo verso
    r.posicion.value = const Duration(milliseconds: 3900);
    expect(puente.mostrados.length, n);
    r.posicion.value = const Duration(milliseconds: 9000);
    expect(puente.mostrados.last['linea'], 'Tercera');
    expect(puente.mostrados.last['siguiente'], '');
    expect(puente.mostrados.last['titulo'], 'Uno');
  });

  test('apagada no enseña nada; al encenderla aparece y al apagarla se quita', () async {
    await armar(activa: false);
    r.poner(Map.of(cancion));
    r.posicion.value = const Duration(seconds: 5);
    await pumpEventQueue();
    expect(puente.mostrados, isEmpty);
    await l.poner(true);
    await pumpEventQueue();
    expect(puente.mostrados.last['linea'], 'Segunda línea');
    await l.poner(false);
    expect(puente.quitados, 1);
  });

  test('otra canción borra el verso anterior; sin letra no se enseña nada', () async {
    await armar();
    r.poner(Map.of(cancion));
    r.posicion.value = const Duration(seconds: 5);
    await pumpEventQueue();
    expect(puente.mostrados, isNotEmpty);
    r.posicion.value = Duration.zero;
    r.poner(Map.of(otra));
    await pumpEventQueue();
    expect(puente.quitados, 1);
    final n = puente.mostrados.length;
    r.posicion.value = const Duration(seconds: 3);
    expect(puente.mostrados.length, n);
  });

  test('pausa: se marca sin quitarla; parada: se quita', () async {
    await armar();
    r.poner(Map.of(cancion));
    r.posicion.value = const Duration(seconds: 2);
    await pumpEventQueue();
    expect(puente.mostrados.last['sonando'], isTrue);
    r.poner(Map.of(cancion)..['clave'] = 'yt:1', suena: false);
    expect(puente.mostrados.last['sonando'], isFalse);
    expect(puente.quitados, 0);
    r.poner(null);
    expect(puente.quitados, 1);
  });

  test('el ajuste se guarda', () async {
    await armar(activa: false);
    await l.poner(true);
    final p = await SharedPreferences.getInstance();
    expect(p.getBool(LetraEnBloqueo.clavePref), isTrue);
  });
}
