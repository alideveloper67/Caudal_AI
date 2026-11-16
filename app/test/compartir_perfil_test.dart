import 'package:caudal/nucleo/social.dart';
import 'package:caudal/ui/paginas/compartir_perfil.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const _tamanos = <(String, Size, double)>[
  ('telefono chico', Size(320, 568), 2.0),
  ('telefono', Size(412, 915), 2.6),
  ('horizontal', Size(915, 412), 2.6),
  ('tablet', Size(800, 1280), 2.0),
  ('escritorio', Size(1440, 900), 1.0),
];

Perfil _perfil({bool completo = true}) => Perfil(
      id: 'x',
      usuario: 'arkhux',
      nombre: completo ? 'Una persona con un nombre bastante largo para probar' : '',
      bio: completo ? 'Me encanta la música de todo tipo. Cumbia, rock, baladas y mucho más para el camino.' : '',
      frase: completo ? 'La vida es una canción' : '',
      generos: completo ? const ['Cumbia', 'Rock', 'Baladas', 'Salsa', 'Pop'] : const [],
      cancionFav: completo ? const CancionFav(titulo: 'Una canción muy muy larga de prueba', artista: 'Artista') : null,
      likes: 120,
      numSubidas: completo ? 4 : 0,
      numero: 7,
      fundador: completo,
      esArtista: completo,
      titulos: completo ? const [TituloEspecial(clave: 'donador_caudal', nombre: 'Donador de Caudal')] : const [],
      topArtistas: completo ? const [ArtistaTop(nombre: 'Artista uno'), ArtistaTop(nombre: 'Dos'), ArtistaTop(nombre: 'Tres largo')] : const [],
    );

void main() {
  for (final (nombre, tam, dpr) in _tamanos) {
    for (final estilo in [0, 1, 2]) {
      testWidgets('Tarjeta de perfil sin desbordes · $nombre · estilo $estilo', (t) async {
        t.view.physicalSize = tam * dpr;
        t.view.devicePixelRatio = dpr;
        addTearDown(t.view.reset);
        for (final completo in [true, false]) {
          await t.pumpWidget(MaterialApp(
            theme: temaCaudal().copyWith(splashFactory: InkRipple.splashFactory),
            home: Scaffold(
              body: Center(
                child: SizedBox(
                  width: 300,
                  child: AspectRatio(aspectRatio: 9 / 16, child: TarjetaPerfilCompartible(perfil: _perfil(completo: completo), estilo: estilo)),
                ),
              ),
            ),
          ));
          await t.pump(const Duration(milliseconds: 200));
          expect(t.takeException(), isNull);
        }
      });
    }
  }
}
