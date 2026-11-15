// La logica pura de la «Mezcla DJ» y de la mesa del Mezclador: cuando entra la
// siguiente, cuanto dura el cambio y el cambio de graves.
import 'package:caudal/nucleo/mezcla_dj.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> p(String id, {int dur = 200}) => {
      'tipo': 'pista', 'clave': 'yt:$id', 'video_id': id, 'titulo': 'T$id', 'artista': 'A',
      'duracion': dur, 'miniatura': 'm$id',
    };

void main() {
  group('ajuste de la Mezcla DJ', () {
    test('siempre entre 4 y 16 segundos', () {
      expect(segundosDj(8), 8);
      expect(segundosDj(1), 4);
      expect(segundosDj(99), 16);
      expect(segundosDj('12'), 12);
      expect(segundosDj(null), djPorDefecto);
      expect(segundosDj('basura'), djPorDefecto);
    });
  });

  group('un paso', () {
    test('lo normal: entra a 8 s del final y el cambio dura 8 s', () {
      final paso = PasoMezcla(pista: p('a'));
      expect(paso.entraEfectivo, 8);
      expect(paso.fundidoEfectivo, 8);
      expect(paso.inicioDelCambio, 192);
    });

    test('el cambio no puede durar mas que lo que queda desde que entra la siguiente', () {
      final paso = PasoMezcla(pista: p('a'), entraAntes: 5, fundido: 12);
      expect(paso.fundidoEfectivo, 5);
    });

    test('no se come mas de la mitad de una cancion corta', () {
      final paso = PasoMezcla(pista: p('a', dur: 30), entraAntes: 30, fundido: 16);
      expect(paso.entraEfectivo, 15);
      expect(paso.fundidoEfectivo, 15);
      expect(paso.inicioDelCambio, 15);
    });

    test('los valores locos se quedan dentro de los limites', () {
      final paso = PasoMezcla(pista: p('a'), entraAntes: 500, fundido: 0);
      expect(paso.entraEfectivo, entraMax);
      expect(paso.fundidoEfectivo, fundidoMin);
    });

    test('sin duracion conocida no revienta', () {
      final paso = PasoMezcla(pista: {'clave': 'x'});
      expect(paso.duracionPista, 0);
      expect(paso.inicioDelCambio, 0);
      expect(paso.entraEfectivo, 8);
    });

    test('copiaCon cambia solo lo pedido', () {
      final a = PasoMezcla(pista: p('a'), entraAntes: 10, fundido: 6, graves: true);
      final b = a.copiaCon(graves: false);
      expect([b.entraAntes, b.fundido, b.graves], [10, 6, false]);
      expect(identical(b.pista, a.pista), isTrue);
    });
  });

  group('cambio de graves', () {
    test('la que se va empieza con graves y los pierde; la que llega al reves', () {
      expect(dbGraves(0, entrante: false), 0);
      expect(dbGraves(1, entrante: false), dbGravesCortados);
      expect(dbGraves(0, entrante: true), dbGravesCortados);
      expect(dbGraves(1, entrante: true), 0);
    });

    test('nunca suenan los graves de las dos a la vez, y todo va en saltos de 6 dB', () {
      var anteriorS = 0, anteriorE = dbGravesCortados;
      for (var i = 0; i <= 100; i++) {
        final a = i / 100;
        final s = dbGraves(a, entrante: false);
        final e = dbGraves(a, entrante: true);
        expect(s % 6, 0);
        expect(e % 6, 0);
        expect(s, inInclusiveRange(dbGravesCortados, 0));
        expect(e, inInclusiveRange(dbGravesCortados, 0));
        // a lo largo del cambio la que se va solo baja y la que llega solo sube
        expect(s, lessThanOrEqualTo(anteriorS));
        expect(e, greaterThanOrEqualTo(anteriorE));
        anteriorS = s;
        anteriorE = e;
        if (a < 1) expect(s == 0 && e == 0, isFalse, reason: 'en $a los dos con todos los graves');
      }
    });

    test('fuera de rango se queda en los extremos', () {
      expect(dbGraves(-3, entrante: false), 0);
      expect(dbGraves(7, entrante: true), 0);
    });

    test('el filtro solo usa equalizer (lo unico que trae el telefono)', () {
      expect(filtroGraves(0), '');
      final f = filtroGraves(-12);
      expect(f, startsWith('lavfi=['));
      expect(f, contains('equalizer=f=60'));
      expect(f, contains('g=-12'));
      expect(f, isNot(contains('loudnorm')));
      expect(f, isNot(contains('volume')));
    });

    test('se suma al sonido de siempre sin pisarlo', () {
      expect(sumarFiltro('', ''), '');
      expect(sumarFiltro('lavfi=[a]', ''), 'lavfi=[a]');
      expect(sumarFiltro('', 'lavfi=[b]'), 'lavfi=[b]');
      expect(sumarFiltro('lavfi=[a]', 'lavfi=[b]'), 'lavfi=[a],lavfi=[b]');
    });
  });

  group('el set', () {
    test('pasosPorDefecto pone los mismos ajustes a todas', () {
      final pasos = pasosPorDefecto([p('a'), p('b'), p('c')], segundos: 12, graves: false);
      expect(pasos.length, 3);
      expect(pasos.every((x) => x.entraAntes == 12 && x.fundido == 12 && !x.graves), isTrue);
    });

    test('duracion: cada cancion se solapa con la siguiente', () {
      final pasos = [
        PasoMezcla(pista: p('a', dur: 200), entraAntes: 10),
        PasoMezcla(pista: p('b', dur: 180), entraAntes: 20),
        PasoMezcla(pista: p('c', dur: 240)),
      ];
      // (200-10) + (180-20) + 240
      expect(duracionDelSet(pasos), 590);
      expect(duracionDelSet([]), 0);
    });

    test('una mezcla guardada vuelve igual (y se descarta lo roto)', () {
      final m = Mezcla(id: 'm1', nombre: 'Viernes', pasos: [
        PasoMezcla(pista: p('a'), entraAntes: 12, fundido: 6, graves: false),
        PasoMezcla(pista: p('b')),
      ]);
      final r = Mezcla.deJson(m.aJson())!;
      expect(r.nombre, 'Viernes');
      expect(r.pasos.length, 2);
      expect(r.pasos.first.entraAntes, 12);
      expect(r.pasos.first.fundido, 6);
      expect(r.pasos.first.graves, isFalse);
      expect(r.pasos.last.pista['clave'], 'yt:b');
      expect(Mezcla.deJson({'nombre': 'sin pasos', 'pasos': []}), isNull);
      expect(Mezcla.deJson({'pasos': [{'pista': p('a')}]}), isNull);
      expect(Mezcla.deJson('basura'), isNull);
      // valores fuera de rango (de otra version) se acotan
      final loca = PasoMezcla.deJson({'pista': p('a'), 'entra_antes': 999, 'fundido': -4})!;
      expect(loca.entraAntes, entraMax);
      expect(loca.fundido, fundidoMin);
    });
  });
}
