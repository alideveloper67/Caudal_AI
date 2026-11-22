import 'package:caudal/reproduccion/salida_unica.dart';
import 'package:flutter_test/flutter_test.dart';

class _M implements SalidaMotor {
  _M({this.tieneSonido = false, this.pideAudiotrack = false, this.abierta = ''});
  @override
  bool tieneSonido;
  @override
  bool pideAudiotrack;

  /// Lo que responde `current-ao`; con [suelta] se vuelve '' tras unas preguntas.
  String? abierta;
  int suelta = -1;
  bool falla = false;
  int preguntas = 0;

  @override
  Future<String?> salidaAbierta() async {
    preguntas++;
    if (falla) throw StateError('mpv cerrado');
    if (suelta >= 0 && preguntas > suelta) abierta = '';
    return abierta;
  }
}

Future<bool> _puede(_M yo, List<_M> todos) => puedeUsarAudiotrack(yo, todos,
    espera: const Duration(milliseconds: 200), paso: const Duration(milliseconds: 5));

void main() {
  test('solo: puede usar audiotrack', () async {
    final a = _M();
    expect(await _puede(a, [a]), isTrue);
  });

  test('fundido: si el que sale suena por audiotrack, el que entra va por opensles', () async {
    final sale = _M(tieneSonido: true, pideAudiotrack: true, abierta: 'audiotrack');
    final entra = _M();
    expect(await _puede(entra, [sale, entra]), isFalse);
  });

  test('el otro tiene puesto audiotrack y acaba de abrir (aún sin salida): no', () async {
    final otro = _M(tieneSonido: true, pideAudiotrack: true, abierta: '');
    expect(await _puede(_M(), [otro]), isFalse);
  });

  test('el otro suena por opensles: este puede usar audiotrack', () async {
    final otro = _M(tieneSonido: true, pideAudiotrack: false, abierta: 'opensles');
    expect(await _puede(_M(), [otro]), isTrue);
  });

  test('el otro se acaba de parar y mpv suelta su AudioTrack un instante después: se espera', () async {
    final otro = _M(tieneSonido: false, pideAudiotrack: true, abierta: 'audiotrack')..suelta = 3;
    expect(await _puede(_M(), [otro]), isTrue);
    expect(otro.preguntas, greaterThan(3));
  });

  test('el otro nunca suelta su AudioTrack: pasado el tiempo, opensles', () async {
    final otro = _M(tieneSonido: false, pideAudiotrack: true, abierta: 'audiotrack');
    expect(await _puede(_M(), [otro]), isFalse);
  });

  test('no se puede preguntar a un motor que pedía audiotrack (se está cerrando): no', () async {
    final otro = _M(pideAudiotrack: true)..falla = true;
    expect(await _puede(_M(), [otro]), isFalse);
  });

  test('no se puede preguntar a uno que nunca pidió audiotrack: da igual', () async {
    final otro = _M(pideAudiotrack: false)..falla = true;
    expect(await _puede(_M(), [otro]), isTrue);
  });

  test('una secuencia de fundidos alterna y nunca deja dos AudioTrack a la vez', () async {
    final a = _M();
    final b = _M();
    final todos = [a, b];
    var activo = a;
    var otro = b;
    // primera canción
    activo.pideAudiotrack = await _puede(activo, todos);
    activo.tieneSonido = true;
    activo.abierta = activo.pideAudiotrack ? 'audiotrack' : 'opensles';
    for (var i = 0; i < 10; i++) {
      // entra la siguiente con fundido: el que entra elige mientras el otro suena
      otro.pideAudiotrack = await _puede(otro, todos);
      otro.tieneSonido = true;
      otro.abierta = otro.pideAudiotrack ? 'audiotrack' : 'opensles';
      final abiertas = todos.where((m) => m.abierta == 'audiotrack').length;
      expect(abiertas, lessThanOrEqualTo(1), reason: 'fundido $i');
      // se apaga el que sale
      activo.tieneSonido = false;
      activo.abierta = '';
      final t = activo;
      activo = otro;
      otro = t;
    }
  });
}
