import 'dart:async';

import 'package:flutter/material.dart';

import '../nucleo/coleccion.dart';
import '../nucleo/mixes.dart';
import '../reproduccion/biblioteca_auto.dart';
import '../ui/paginas/buscar.dart';
import '../ui/paginas/coleccion_pagina.dart';
import '../ui/servicios.dart';
import 'abrir_modo_coche.dart';
import 'atajos_caudal.dart';

typedef PonerLista = Future<void> Function(List<Json> pistas, {bool? aleatorio, Json? contexto});
typedef PonerPista = Future<void> Function(Json pista);

/// Lo que se quiere buscar desde un acceso directo o por voz. La pestaña Buscar
/// lo recoge (ver el parche de `buscar.dart` en el informe) y lo deja en `null`.
final ValueNotifier<String?> consultaDeAtajo = ValueNotifier(null);

/// La pestaña de la música descargada (la biblioteca) y el elemento que la abre.
const pestanaBuscar = 1;
const pestanaBiblioteca = 2;
const elementoMusicaDescargada = <String, dynamic>{
  'tipo': 'descargados',
  'id': 'musica',
  'solo': true,
  'titulo': 'Música descargada',
  'icono': 'musica',
};

const contextoMeGusta = <String, dynamic>{'tipo': 'me_gusta', 'id': 'me_gusta', 'titulo': 'Tus me gusta'};

/// Hace lo que pide un [AtajoCaudal]. Todo lo de fuera llega por parámetros para
/// poder probarlo sin teléfono; [EjecutorAtajos.app] lo conecta con la app de verdad.
class EjecutorAtajos {
  EjecutorAtajos({
    required this.coleccion,
    required this.ponerLista,
    required this.ponerPista,
    required this.avisar,
    required this.irAPestana,
    required this.abrirDescargadas,
    required this.abrirModoCoche,
    this.enfocarBuscar,
    Future<List<Json>> Function()? mixesDelDia,
    Future<List<Json>> Function(String texto)? buscarCanciones,
  })  : mixesDelDia = mixesDelDia ?? (() => Mixes.delDia(coleccion)),
        buscarCanciones = buscarCanciones ?? ((t) => BibliotecaAuto(coleccion).buscar(t, limite: 10));

  /// Conectado a la app: [context] tiene que colgar del navegador principal
  /// (el del Armazon sirve).
  factory EjecutorAtajos.app(BuildContext context, Servicios s) => EjecutorAtajos(
        coleccion: s.coleccion,
        ponerLista: (pistas, {aleatorio, contexto}) =>
            s.reproducirLista(context, pistas, aleatorio: aleatorio, contexto: contexto),
        ponerPista: (p) => s.reproducirPista(context, p),
        avisar: s.avisar,
        irAPestana: (i) => s.irAPestana?.call(i),
        enfocarBuscar: BuscarPagina.enfocar,
        abrirDescargadas: () {
          final abrir = s.abrirEnPestana;
          if (abrir != null) {
            abrir(ColeccionPagina(elemento: Map<String, dynamic>.from(elementoMusicaDescargada)));
          } else {
            s.abrirElemento(context, Map<String, dynamic>.from(elementoMusicaDescargada));
          }
        },
        abrirModoCoche: () => AbrirModoCoche.abrir(context),
      );

  final Coleccion coleccion;
  final PonerLista ponerLista;
  final PonerPista ponerPista;
  final void Function(String texto) avisar;
  final void Function(int pestana) irAPestana;
  final VoidCallback abrirDescargadas;
  final Future<void> Function() abrirModoCoche;
  final VoidCallback? enfocarBuscar;
  final Future<List<Json>> Function() mixesDelDia;
  final Future<List<Json>> Function(String texto) buscarCanciones;

  /// Atiende [texto] si es un enlace de atajo. Devuelve `false` si no lo era
  /// (y entonces lo atiende quien lo atendía antes).
  Future<bool> atenderEnlace(String texto) async {
    final a = leerAtajo(texto);
    if (a == null) return false;
    await ejecutar(a);
    return true;
  }

  Future<void> ejecutar(AtajoCaudal a) async {
    try {
      switch (a.tipo) {
        case TipoAtajo.meGustaAleatorio:
          await _meGusta();
        case TipoAtajo.buscar:
          _buscar(a.texto);
        case TipoAtajo.descargas:
          irAPestana(pestanaBiblioteca);
          abrirDescargadas();
        case TipoAtajo.miMix:
          await _miMix();
        case TipoAtajo.modoCoche:
          await abrirModoCoche();
        case TipoAtajo.sonar:
          await _sonar(a.texto);
      }
    } catch (_) {
      avisar('No se pudo hacer eso ahora. Inténtalo otra vez.');
    }
  }

  Future<void> _meGusta({String? antes}) async {
    final lista = await coleccion.listaMeGusta();
    if (lista.isEmpty) {
      avisar(antes ?? 'Aún no tienes canciones con me gusta. Toca el corazón de una canción para guardarla.');
      return;
    }
    if (antes != null) avisar(antes);
    await ponerLista(lista, aleatorio: true, contexto: Map<String, dynamic>.from(contextoMeGusta));
  }

  void _buscar(String texto) {
    irAPestana(pestanaBuscar);
    if (texto.trim().isNotEmpty) {
      // con texto se busca directo: sin teclado encima de los resultados
      consultaDeAtajo.value = texto.trim();
      return;
    }
    // la pestaña tiene que estar montada para recibir el foco: se espera al
    // siguiente fotograma (y se pide uno, por si nadie lo ha pedido ya)
    final binding = WidgetsBinding.instance;
    binding.addPostFrameCallback((_) => enfocarBuscar?.call());
    binding.scheduleFrame();
  }

  Future<void> _miMix() async {
    List<Json> mixes;
    try {
      mixes = await mixesDelDia();
    } catch (_) {
      mixes = const [];
    }
    for (final m in mixes) {
      final pistas = [
        for (final e in (m['pistas'] as List? ?? const []))
          if (e is Map) Map<String, dynamic>.from(e)
      ];
      if (pistas.isEmpty) continue;
      await ponerLista(pistas, contexto: {
        'tipo': 'mix',
        'id': m['id'],
        'titulo': m['titulo'],
        'miniatura': m['miniatura'],
      });
      return;
    }
    // sin historial todavía no hay mix: algo tiene que sonar igual
    await _meGusta(antes: 'Tu mix aún no está listo: sale cuando escuchas un poco más. Mientras, tus me gusta.');
  }

  Future<void> _sonar(String texto) async {
    final halladas = await buscarCanciones(texto);
    if (halladas.isEmpty) {
      avisar('No encontré «$texto». Prueba a buscarla tú.');
      _buscar(texto);
      return;
    }
    await ponerPista(halladas.first);
  }
}
