import 'dart:io';

import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

import '../nucleo/ajustes.dart';
import '../nucleo/catalogo.dart';
import '../nucleo/coleccion.dart';
import '../nucleo/cuentas.dart';
import '../nucleo/descargas.dart';
import '../nucleo/modelos.dart';
import '../nucleo/sincronizacion.dart';
import '../nucleo/streams.dart';
import '../reproduccion/reproductor.dart';
import 'comunes.dart';
import 'paginas/artista.dart';
import 'paginas/coleccion_pagina.dart';
import 'paginas/genero.dart';
import 'paginas/reproductor_pagina.dart';
import 'plataforma.dart';
import 'tema.dart';

/// Todo lo que comparten las pantallas.
class Servicios {
  Servicios({
    required this.cuenta, required this.ajustes, required this.coleccion,
    required this.reproductor, required this.streams, required this.descargas,
    this.sincronizador, required this.cerrarSesion,
    GlobalKey<ScaffoldMessengerState>? mensajero,
  }) : mensajero = mensajero ?? GlobalKey<ScaffoldMessengerState>();

  final Cuenta cuenta;
  final Ajustes ajustes;
  final Coleccion coleccion;
  final Reproductor reproductor;
  final Streams streams;
  final GestorDescargas descargas;
  final Sincronizador? sincronizador;
  final Future<void> Function() cerrarSesion;

  /// Para avisos desde cualquier sitio (la app pasa la suya, que no cambia).
  final GlobalKey<ScaffoldMessengerState> mensajero;

  /// Cambiar de pestana desde cualquier pantalla (la pone el armazon).
  void Function(int)? irAPestana;
  void Function(String)? abrirEnlace;

  /// Abre una pagina dentro de la pestana visible (la pone el armazon).
  void Function(Widget)? abrirEnPestana;

  bool _reproductorAbierto = false;

  void avisar(String texto, {VoidCallback? deshacer}) {
    final m = mensajero.currentState;
    if (m == null) return;
    m.hideCurrentSnackBar();
    m.showSnackBar(SnackBar(
      content: Text(texto),
      duration: Duration(milliseconds: deshacer == null ? 2600 : 5000),
      action: deshacer == null ? null : SnackBarAction(label: 'Deshacer', onPressed: deshacer),
    ));
  }

  // ------------------------------------------------------------ reproducir

  String _modoPara(Json p) {
    if (p['archivo'] != null && p['es_audio'] != true) return 'video';
    if (p['es_video'] == true && p['archivo'] == null) return 'video';
    return 'audio';
  }

  Future<void> reproducirLista(BuildContext context, List<Json> pistas,
      {int inicio = 0, Json? contexto, bool? aleatorio}) async {
    if (pistas.isEmpty) return;
    final modo = _modoPara(pistas[inicio.clamp(0, pistas.length - 1)]);
    await reproductor.reproducirLista(pistas, inicio: inicio, contexto: contexto,
        aleatorio: aleatorio, modo: modo);
    if (modo == 'video' && context.mounted) abrirReproductor(context);
  }

  Future<void> reproducirPista(BuildContext context, Json pista, {Json? contexto}) async {
    final modo = _modoPara(pista);
    await reproductor.reproducirPista(pista, contexto: contexto, modo: modo);
    if (modo == 'video' && context.mounted) abrirReproductor(context);
  }

  void abrirReproductor(BuildContext context) {
    // dos toques seguidos (o un video desde la propia pantalla) no apilan otra
    if (_reproductorAbierto) return;
    _reproductorAbierto = true;
    Navigator.of(context, rootNavigator: true).push(PageRouteBuilder<void>(
      opaque: false,
      transitionDuration: const Duration(milliseconds: 320),
      reverseTransitionDuration: const Duration(milliseconds: 260),
      pageBuilder: (_, __, ___) => const ReproductorPagina(),
      transitionsBuilder: (_, a, __, hijo) => SlideTransition(
        position: Tween(begin: const Offset(0, 1), end: Offset.zero)
            .animate(CurvedAnimation(parent: a, curve: Curves.easeOutCubic)),
        child: hijo,
      ),
    )).whenComplete(() => _reproductorAbierto = false);
  }

  /// Empuja [pagina] en la navegacion de la pestana. Si se pide desde algo que
  /// esta encima de todo (el reproductor, la cola), primero se cierra eso: si
  /// no, la pagina taparia la barra de abajo y el mini reproductor.
  void _abrir(BuildContext context, Widget pagina) {
    final nav = Navigator.of(context);
    final raiz = Navigator.of(context, rootNavigator: true);
    if (identical(nav, raiz) && abrirEnPestana != null) {
      raiz.popUntil((r) => r.isFirst);
      abrirEnPestana!(pagina);
    } else {
      nav.push(MaterialPageRoute(builder: (_) => pagina));
    }
  }

  /// El boton de play de una tarjeta: hay que traer las canciones primero.
  Future<void> reproducirElemento(BuildContext context, Json el, {bool? aleatorio}) async {
    final tipo = el['tipo'];
    if (tipo == 'pista') return reproducirPista(context, el);
    if (tipo == 'radio') return reproductor.reproducirRadioId('${el['id']}', '${el['titulo'] ?? 'Radio'}');
    try {
      final pistas = await pistasDe(el);
      if (pistas.isEmpty) return avisar('No tiene canciones disponibles.');
      if (!context.mounted) return;
      await reproducirLista(context, pistas, aleatorio: aleatorio, contexto: {
        'tipo': tipo, 'id': el['id'] ?? tipo, 'titulo': el['titulo'], 'miniatura': el['miniatura'],
      });
    } catch (e) {
      avisar('No se pudo: $e');
    }
  }

  Future<List<Json>> pistasDe(Json el) async {
    switch (el['tipo']) {
      case 'pista':
        return [el];
      case 'mi_lista':
        final id = idLista(el['id']);
        return id == null ? [] : coleccion.pistasDeLista(id);
      case 'me_gusta':
        return coleccion.listaMeGusta();
      case 'descargados':
        return coleccion.descargadas(soloAudio: el['solo'] is bool ? el['solo'] as bool : null);
      case 'album':
        return _comoPistas((await Catalogo.album('${el['id']}'))['pistas']);
      case 'lista':
        return _comoPistas((await Catalogo.lista('${el['id']}'))['pistas']);
      case 'radio':
        return _comoPistas((await Catalogo.radio(playlistId: '${el['id']}'))['pistas']);
      case 'mix':
        return _comoPistas(el['pistas']);       // los mixes diarios ya traen sus canciones
      case 'artista':
        final a = await Catalogo.artista('${el['id']}');
        return [
          for (final s in (a['secciones'] as List? ?? const []))
            if (s is Map)
              for (final e in (s['elementos'] as List? ?? const []))
                if (e is Map && e['tipo'] == 'pista') Map<String, dynamic>.from(e)
        ];
    }
    return [];
  }

  static List<Json> _comoPistas(Object? lista) => [
        for (final e in (lista is List ? lista : const []))
          if (e is Map) Map<String, dynamic>.from(e)
      ];

  /// El id de una lista propia (o de una descarga): entero en la base, pero
  /// puede llegar como texto si paso por JSON o por la nube.
  static int? idLista(Object? id) => id is int ? id : int.tryParse('${id ?? ''}');

  /// Abrir un elemento: navega dentro de la pestana actual.
  void abrirElemento(BuildContext context, Json el) {
    final tipo = el['tipo'];
    Widget? pagina;
    switch (tipo) {
      case 'pista':
        reproducirPista(context, el);
        return;
      case 'radio':
        reproductor.reproducirRadioId('${el['id']}', '${el['titulo'] ?? 'Radio'}');
        return;
      case 'artista':
        pagina = ArtistaPagina(id: '${el['id']}');
      case 'album' || 'lista' || 'mi_lista' || 'me_gusta' || 'descargados' || 'mix':
        pagina = ColeccionPagina(elemento: el);
      case 'genero' || 'pagina':
        if ('${el['id'] ?? ''}'.isEmpty) return;
        pagina = GeneroPagina(id: '${el['id']}', params: el['params'] is String ? el['params'] as String : null,
            titulo: '${el['titulo'] ?? ''}');
    }
    if (pagina != null) _abrir(context, pagina);
  }

  void irAArtista(BuildContext context, String id) => _abrir(context, ArtistaPagina(id: id));

  void irAAlbum(BuildContext context, String id) =>
      _abrir(context, ColeccionPagina(elemento: {'tipo': 'album', 'id': id}));

  // ------------------------------------------------------------ me gusta y listas

  Future<void> alternarMeGusta(Json pista, {bool avisar_ = true}) async {
    Haptico.toque();
    final ahora = await coleccion.alternarMeGusta(pista);
    if (!avisar_) return;
    if (ahora) {
      avisar('Añadida a Tus me gusta');
    } else {
      avisar('Quitada de Tus me gusta', deshacer: () => alternarMeGusta(pista, avisar_: false));
    }
  }

  Future<void> anadirALista(BuildContext context, List<Json> pistas) async {
    final listas = await coleccion.listas();
    if (!context.mounted) return;
    final elegida = await showModalBottomSheet<int>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.6,
        maxChildSize: 0.92,
        builder: (_, scroll) => ListView(controller: scroll, children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 4, 20, 12),
            child: Text('Añadir a una lista', style: estiloTituloSeccion),
          ),
          ListTile(
            leading: const CircleAvatar(backgroundColor: C.superficie3, child: Icon(Icons.add, color: C.texto)),
            title: const Text('Nueva lista', style: TextStyle(fontWeight: FontWeight.w700)),
            onTap: () => Navigator.pop(ctx, -1),
          ),
          for (final l in listas)
            ListTile(
              leading: const Icon(Icons.queue_music_rounded, color: C.texto2),
              title: Text('${l['nombre']}'),
              subtitle: Text('${l['n']} canciones', style: estiloSecundario),
              onTap: () => Navigator.pop(ctx, idLista(l['id']) ?? -2),
            ),
          SizedBox(height: 8 + MediaQuery.paddingOf(ctx).bottom),
        ]),
      ),
    );
    if (elegida == null || elegida == -2 || !context.mounted) return;
    var id = elegida;
    if (elegida == -1) {
      final libre = await coleccion.nombreLibre();
      if (!context.mounted) return;
      final nombre = await pedirTexto(context, 'Nueva lista', libre);
      if (nombre == null) return;
      try {
        id = await coleccion.crearLista(nombre);
      } on FormatException catch (e) {
        avisar(e.message);
        return;
      }
    }
    final nuevas = await coleccion.agregarALista(id, pistas);
    final l = await coleccion.lista(id);
    avisar(nuevas == 0 ? 'Ya estaba en «${l?['nombre']}»' : 'Añadido a «${l?['nombre']}»');
  }

  Future<void> quitarDeLista(int listaId, Json pista) async {
    final antes = (await coleccion.pistasDeLista(listaId)).map((p) => '${p['clave']}').toList();
    await coleccion.quitarDeLista(listaId, '${pista['clave']}');
    avisar('Quitada de la lista', deshacer: () async {
      await coleccion.agregarALista(listaId, [pista]);
      await coleccion.moverEnLista(listaId, antes);
    });
  }

  Future<void> alternarGuardado(Json el) async {
    final tipo = '${el['tipo']}';
    final id = '${el['id'] ?? ''}';
    if (id.isEmpty) return;
    // la coleccion espera el id como texto
    final datos = {...el, 'tipo': tipo, 'id': id};
    if (coleccion.guardado(tipo, id)) {
      await coleccion.olvidar(tipo, id);
      avisar('Quitado de tu biblioteca', deshacer: () => coleccion.guardar(datos));
    } else {
      await coleccion.guardar(datos);
      avisar(tipo == 'artista' ? 'Ahora sigues a ${el['titulo']}' : 'Guardado en tu biblioteca');
    }
  }

  // ------------------------------------------------------------ descargar

  void descargar(List<Json> pistas, Map<String, String> opciones) {
    var n = 0;
    for (final p in pistas) {
      final vid = '${p['video_id'] ?? ''}';
      if (vid.isEmpty) continue;
      final tipo = switch (opciones['tipo']) {
        'completo' => TipoMedio.completo, 'video' => TipoMedio.video, _ => TipoMedio.audio,
      };
      descargas.encolar(
        url: p['es_video'] == true
            ? 'https://www.youtube.com/watch?v=$vid'
            : 'https://music.youtube.com/watch?v=$vid',
        tipo: tipo,
        calidad: opciones['calidad'] ?? 'mejor',
        formatoAudio: opciones['formato_audio'],
        titulo: '${p['titulo'] ?? ''}',
        autor: '${p['artista'] ?? ''}',
        miniatura: '${p['miniatura'] ?? ''}',
        meta: p,
      );
      n++;
    }
    if (n > 0) Haptico.exito();
    if (n > 0) avisar(n == 1 ? 'Descargando… (mira Descargar)' : '$n descargas en la cola');
  }

  Future<void> hojaDescargar(BuildContext context, List<Json> pistas) async {
    final o = await elegirFormato(context, titulo: pistas.length == 1
        ? 'Descargar «${pistas.first['titulo']}»' : 'Descargar ${pistas.length} canciones');
    if (o != null) descargar(pistas, o);
  }

  // ------------------------------------------------------------ menu de cancion

  Future<void> hojaPista(BuildContext context, Json pista, {List<Widget> extra = const []}) async {
    final gusta = coleccion.meGusta('${pista['clave']}');
    final artistas = [
      for (final a in (pista['artistas'] is List ? pista['artistas'] as List : const []))
        if (a is Map && '${a['id'] ?? ''}'.isNotEmpty) Map<String, dynamic>.from(a)
    ];
    final album = pista['album'] is Map ? Map<String, dynamic>.from(pista['album'] as Map) : <String, dynamic>{};
    final vid = '${pista['video_id'] ?? ''}';
    final enlace = vid.isEmpty ? '' : 'https://music.youtube.com/watch?v=$vid';
    // en iPhone, abrir el menu de una cancion (sobre todo manteniendo) se nota en la mano
    Haptico.toque();
    await showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (ctx) {
        void hacer(VoidCallback f) {
          Navigator.pop(ctx);
          f();
        }
        return SafeArea(
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              ListTile(
                leading: Portada(url: '${pista['miniatura'] ?? ''}', lado: 48, radio: 4),
                title: Text('${pista['titulo']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text('${pista['artista'] ?? ''}', maxLines: 1, style: estiloSecundario),
              ),
              const Divider(),
              _opcion(gusta ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                  gusta ? 'Quitar de Tus me gusta' : 'Guardar en Tus me gusta',
                  () => hacer(() => alternarMeGusta(pista)), color: gusta ? C.acento : null),
              _opcion(Icons.playlist_add_rounded, 'Añadir a una lista',
                  () => hacer(() => anadirALista(context, [pista]))),
              _opcion(Icons.queue_music_rounded, 'Añadir a la cola',
                  () => hacer(() => reproductor.agregarACola([pista]))),
              _opcion(Icons.playlist_play_rounded, 'Reproducir a continuación',
                  () => hacer(() => reproductor.reproducirDespues([pista]))),
              if (vid.isNotEmpty)
                _opcion(Icons.radio_rounded, 'Iniciar radio', () => hacer(() => reproductor.iniciarRadio(pista))),
              if (vid.isNotEmpty)
                _opcion(Icons.download_rounded, coleccion.estaDescargada(pista) ? 'Descargar otra vez (otro formato)' : 'Descargar',
                    () => hacer(() => hojaDescargar(context, [pista]))),
              for (final a in artistas)
                _opcion(Icons.person_rounded, artistas.length == 1 ? 'Ir al artista' : 'Ir a ${a['nombre']}',
                    () => hacer(() => irAArtista(context, '${a['id']}'))),
              if ('${album['id'] ?? ''}'.isNotEmpty)
                _opcion(Icons.album_rounded, 'Ir al álbum', () => hacer(() => irAAlbum(context, '${album['id']}'))),
              if (enlace.isNotEmpty)
                _opcion(Icons.share_rounded, 'Compartir', () => hacer(() => SharePlus.instance
                    .share(ShareParams(text: '${pista['titulo']} — ${pista['artista']}\n$enlace')))),
              if (pista['descarga_id'] != null)
                _opcion(Icons.delete_outline_rounded, 'Borrar del teléfono',
                    () => hacer(() => _borrarDescarga(context, pista))),
              ...extra,
              const SizedBox(height: 8),
            ]),
          ),
        );
      },
    );
  }

  Widget _opcion(IconData icono, String texto, VoidCallback alPulsar, {Color? color}) => ListTile(
        leading: Icon(icono, color: color ?? C.texto2),
        title: Text(texto),
        onTap: alPulsar,
        visualDensity: VisualDensity.compact,
      );

  Future<void> _borrarDescarga(BuildContext context, Json pista) async {
    final ok = await confirmar(context, 'Borrar del teléfono',
        '«${pista['titulo']}» se borrará del teléfono. No se puede deshacer.');
    if (!ok) return;
    final id = idLista(pista['descarga_id']);
    if (id == null) return;
    if (reproductor.actual?['archivo'] == pista['archivo']) await reproductor.detener();
    await coleccion.borrarDescarga(id);
    avisar('Borrado del teléfono');
  }

  Future<void> compartirArchivo(String ruta) async {
    if (await File(ruta).exists()) {
      await SharePlus.instance.share(ShareParams(files: [XFile(ruta)]));
    }
  }
}

/// Acceso a los servicios desde cualquier pantalla.
class Caudal extends InheritedWidget {
  const Caudal({super.key, required this.s, required super.child});
  final Servicios s;

  static Servicios of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<Caudal>()!.s;

  /// Sin suscribirse a cambios (para callbacks).
  static Servicios leer(BuildContext context) =>
      (context.getElementForInheritedWidgetOfExactType<Caudal>()!.widget as Caudal).s;

  @override
  bool updateShouldNotify(Caudal oldWidget) => !identical(s, oldWidget.s);
}
