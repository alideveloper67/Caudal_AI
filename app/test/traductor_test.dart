import 'package:caudal/nucleo/traductor.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('lee la respuesta del traductor de Google', () {
    final (texto, idioma) = Traductor.leerGoogle(
        r'[[["Siempre te amaré\n","I will always love you\n",null,null,10],["Adiós","Goodbye"]],null,"en"]');
    expect(texto, 'Siempre te amaré\nAdiós');
    expect(idioma, 'en');
  });

  test('una respuesta rara no se toma por traduccion', () {
    expect(() => Traductor.leerGoogle('{"error":1}'), throwsFormatException);
  });

  test('una letra vacia no se manda a traducir', () async {
    final t = await Traductor.traducir('vacia', ['', '  ']);
    expect(t?.mismoIdioma, isTrue);
  });
}
