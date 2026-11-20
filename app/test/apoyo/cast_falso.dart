// Un Chromecast que no existe, para los reproductores falsos de las pruebas: la pantalla del
// reproductor pinta su botón de Cast con `reproductor.cast`, y sin esto el falso revienta.
import 'package:caudal/reproduccion/cast.dart';
import 'package:caudal/reproduccion/cast_tipos.dart';
import 'package:flutter/foundation.dart';

/// Un ControlCast sin aparatos ni servidor: el botón de Cast queda oculto, como en un teléfono
/// sin Google Cast.
ControlCast castFalso() => ControlCast(
      AnfitrionCast(
        pista: () => null,
        fuente: () => null,
        posicion: ValueNotifier(Duration.zero),
        duracion: ValueNotifier(Duration.zero),
        sonandoLocal: () => false,
        fijarEstado: (_) {},
        callarLocal: () async {},
        volverLocal: (_, __) async {},
        siguiente: () async {},
        aviso: (_) {},
      ),
      puente: PuenteNulo(),
      servidor: ServidorNulo(),
    );
