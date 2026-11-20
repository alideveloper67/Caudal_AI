import 'dart:async';

import 'package:flutter/widgets.dart';

import '../nucleo/despertador_control.dart';
import '../nucleo/letra_pantalla_bloqueo.dart';
import 'paginas/despertador_sonando.dart';
import 'servicios.dart';

VigiaDespertador? _vigia;

/// Engancha el despertador y la letra en la pantalla bloqueada a la cuenta que se acaba de abrir.
/// Se llama una vez por cuenta (main.dart, al final de `_abrir`).
void engancharDespertador(Servicios s, GlobalKey<NavigatorState> navegador) {
  LetraEnBloqueo.i.enlazar(s.reproductor);
  _vigia?.soltar();
  _vigia = VigiaDespertador(ControlDespertador.i, navegador);
  unawaited(ControlDespertador.i
      .iniciar(PuertoCaudal(s.coleccion, s.reproductor, s.streams))
      .catchError((Object e) => debugPrint('Despertador: $e')));
}

/// Al cerrar la sesión (las alarmas de Android siguen programadas).
void soltarDespertador() {
  LetraEnBloqueo.i.soltar();
  _vigia?.soltar();
  _vigia = null;
  ControlDespertador.i.soltar();
}
