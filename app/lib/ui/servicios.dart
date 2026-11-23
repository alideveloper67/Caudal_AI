import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

import '../nucleo/gamer_control.dart';
import '../nucleo/ajustes.dart';
import '../nucleo/catalogo.dart';
import '../nucleo/coleccion.dart';
import '../nucleo/cuentas.dart';
import '../nucleo/descargas.dart';
import '../nucleo/modelos.dart';
import '../nucleo/recomendador.dart';
import '../nucleo/sincronizacion.dart';
import '../nucleo/sonidos_interfaz.dart';
import '../nucleo/streams.dart';
import '../reproduccion/reproductor.dart';
import 'comunes.dart';
import 'paginas/artista.dart';
import 'paginas/coleccion_pagina.dart';
import 'paginas/genero.dart';
import 'paginas/mensajes_pagina.dart';
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
    this.gamer,
  }) : mensajero = mensajero ?? GlobalKey<ScaffoldMessengerState>();

  final Cuenta cuenta;
  final Ajustes ajustes;
  final Coleccion coleccion;
  final Reproductor reproductor;
  final Streams streams;
  final GestorDescargas descargas;
  final Sincronizador? sincronizador;
  final Future<void> Function() cerrarSesion;

  /// El «Modo gamer» (nivel, ahorro, sonido, listas); nulo en las pruebas que no lo usan.
  final ModoGamerControl? gamer;

  /// Para avisos desde cualquier sitio (la app pasa la suya, que no cambia).
  final GlobalKey<ScaffoldMessengerState> mensajero;

  /// Cambiar de pestana desde cualquier pantalla (la pone el armazon).
  void Function(int)? irAPestana;
  void Function(String)? abrirEnlace;

  /// Abre una pagina dentro de la pestana visible (la pone el armazon).
  void Function(Widget)? abrirEnPestana;

  bool _reproductorAbierto = false;

  void avisar(String texto, {VoidCallback? deshacer, String etiqueta = 'Deshacer'}) {
    final m = mensajero.currentState;
    if (m == null) return;
    m.hideCurrentSnackBar();
    m.showSnackBar(SnackBar(
      content: Text(texto),
      duration: Duration(milliseconds: deshacer == null ? 2600 : 5000),
      action: deshacer == null ? null : SnackBarAction(label: etiqueta, onPressed: deshacer),
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
      case 'similares':
        final pista = el['pista'] is Map ? Map<String, dynamic>.from(el['pista'] as Map) : <String, dynamic>{};
        return _comoPistas((await Recomendador.similares(coleccion, pista))['pistas']);
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
      case 'album' || 'lista' || 'mi_lista' || 'me_gusta' || 'descargados' || 'mix' || 'similares':
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
      SonidosInterfaz.i.meGusta().ignore(); // el sonidito de donadores (solo si lo activó)
      avisar('Añadida a Tus me gusta');
    } else {
      avisar('Quitada de Tus me gusta', deshacer: () => alternarMeGusta(pista, avisar_: false));
    }
  }

  /// Punto de extension: quien conozca otros sitios donde se puede anadir
  /// (por ejemplo listas compartidas donde la persona es colaboradora) pone
  /// aqui una funcion que los devuelve. La hoja los muestra marcados, debajo
  /// de las listas propias, y se cargan en segundo plano (no retrasan la hoja).
  Future<List<DestinoLista>> Function()? destinosExtraLista;

  /// «Añadir a una lista»: la hoja abre al instante (las listas viven en
  /// memoria), se pueden elegir varias a la vez y se avisa con «Deshacer».
  Future<void> anadirALista(BuildContext context, List<Json> pistas) async {
    final eleccion = await showModalBottomSheet<EleccionLista>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (ctx) => HojaAnadirALista(coleccion: coleccion, proveedorExtra: destinosExtraLista),
    );
    if (eleccion == null || eleccion.vacia) return;

    final creadas = <int>[];
    final destinos = <_DestinoElegido>[];
    for (final id in eleccion.ids) {
      final l = await coleccion.lista(id);
      if (l == null) continue;
      destinos.add(_DestinoElegido('${l['nombre']}', id: id));
    }
    for (final nombre in eleccion.nuevas) {
      try {
        final id = await coleccion.crearLista(nombre);
        creadas.add(id);
        destinos.add(_DestinoElegido(nombre, id: id, nueva: true));
      } on FormatException catch (e) {
        avisar(e.message);
      }
    }
    for (final d in eleccion.extras) {
      destinos.add(_DestinoElegido(d.nombre, extra: d));
    }
    if (destinos.isEmpty) return;

    for (final d in destinos) {
      d.entraron = d.extra != null
          ? await d.extra!.agregar(pistas)
          : await coleccion.agregarAListaDetalle(d.id!, pistas);
    }
    final ultimo = destinos.lastWhere((d) => d.id != null, orElse: () => destinos.last);
    if (ultimo.id != null) await coleccion.marcarListaUsada(ultimo.id!);

    final texto = textoAvisoAnadido([for (final d in destinos) (d.nombre, d.entraron.length)]);
    final algo = destinos.any((d) => d.entraron.isNotEmpty || d.nueva);
    avisar(texto, deshacer: algo ? () => _deshacerAnadir(destinos) : null);
  }

  Future<void> _deshacerAnadir(List<_DestinoElegido> destinos) async {
    for (final d in destinos) {
      if (d.extra != null) {
        await d.extra!.quitar?.call(d.entraron);
      } else if (d.nueva) {
        await coleccion.borrarLista(d.id!);      // la lista la creo este gesto: se va con el
      } else {
        await coleccion.quitarVariasDeLista(d.id!, d.entraron);
      }
    }
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
              _opcion(Icons.playlist_play_rounded, 'Tocar después de esta',
                  () => hacer(() => reproductor.tocarDespues(pista))),
              if (vid.isNotEmpty)
                _opcion(Icons.radio_rounded, 'Iniciar radio', () => hacer(() => reproductor.iniciarRadio(pista))),
              if (vid.isNotEmpty)
                _opcion(Icons.auto_awesome_rounded, 'Canciones similares', () => hacer(() => abrirElemento(context, {
                      'tipo': 'similares', 'id': vid, 'titulo': 'Similares a «${pista['titulo']}»',
                      'miniatura': '${pista['miniatura'] ?? ''}', 'pista': pista,
                    }))),
              if (vid.isNotEmpty && !kIsWeb)
                _opcion(Icons.download_rounded, coleccion.estaDescargada(pista) ? 'Descargar otra vez (otro formato)' : 'Descargar',
                    () => hacer(() => hojaDescargar(context, [pista]))),
              for (final a in artistas)
                _opcion(Icons.person_rounded, artistas.length == 1 ? 'Ir al artista' : 'Ir a ${a['nombre']}',
                    () => hacer(() => irAArtista(context, '${a['id']}'))),
              if ('${album['id'] ?? ''}'.isNotEmpty)
                _opcion(Icons.album_rounded, 'Ir al álbum', () => hacer(() => irAAlbum(context, '${album['id']}'))),
              if (vid.isNotEmpty)
                _opcion(Icons.send_rounded, 'Enviar en un chat', () => hacer(() => enviarPistaAChat(context, pista))),
              if (enlace.isNotEmpty)
                _opcion(Icons.share_rounded, 'Compartir', () => hacer(() => SharePlus.instance
                    .share(ShareParams(text: '${pista['titulo']} — ${pista['artista']}\n$enlace')))),
              if (pista['descarga_id'] != null)
                _opcion(Icons.delete_outline_rounded, kIsWeb ? 'Borrar de este navegador' : 'Borrar del teléfono',
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
    const donde = kIsWeb ? 'de este navegador' : 'del teléfono';
    final ok = await confirmar(context, 'Borrar $donde',
        '«${pista['titulo']}» se borrará $donde. No se puede deshacer.');
    if (!ok) return;
    final id = idLista(pista['descarga_id']);
    if (id == null) return;
    if (reproductor.actual?['archivo'] == pista['archivo']) await reproductor.detener();
    await coleccion.borrarDescarga(id);
    avisar('Borrado $donde');
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

// ---------------------------------------------------------------- añadir a una lista

/// Un sitio extra donde se puede anadir canciones (ver
/// [Servicios.destinosExtraLista]): por ejemplo, una lista compartida.
class DestinoLista {
  const DestinoLista({
    required this.id, required this.nombre, required this.agregar,
    this.quitar, this.detalle = '', this.etiqueta = '', this.icono = Icons.group_rounded,
  });

  /// Identificador propio (solo debe ser distinto entre destinos).
  final String id;
  final String nombre;

  /// Segunda linea (por ejemplo «12 canciones · de Ana»).
  final String detalle;

  /// Marca visible (por ejemplo «Compartida»).
  final String etiqueta;
  final IconData icono;

  /// Anade las canciones y devuelve las claves que entraron de verdad.
  final Future<List<String>> Function(List<Json> pistas) agregar;

  /// Revierte lo anadido (si no hay, el aviso no ofrece «Deshacer» para este destino).
  final Future<void> Function(List<String> claves)? quitar;
}

/// Lo que se eligio en la hoja: listas propias, listas por crear y destinos extra.
class EleccionLista {
  const EleccionLista({this.ids = const [], this.nuevas = const [], this.extras = const []});
  final List<int> ids;
  final List<String> nuevas;
  final List<DestinoLista> extras;
  bool get vacia => ids.isEmpty && nuevas.isEmpty && extras.isEmpty;
}

class _DestinoElegido {
  _DestinoElegido(this.nombre, {this.id, this.extra, this.nueva = false});
  final String nombre;
  final int? id;
  final DestinoLista? extra;
  final bool nueva;
  List<String> entraron = const [];
}

/// El aviso de despues de anadir: [resultados] = (nombre de la lista, cuantas entraron).
String textoAvisoAnadido(List<(String, int)> resultados) {
  if (resultados.length == 1) {
    final (nombre, n) = resultados.first;
    return n == 0 ? 'Ya estaba en «$nombre»' : 'Añadido a «$nombre»';
  }
  final con = resultados.where((r) => r.$2 > 0).toList();
  if (con.length == 1) return 'Añadido a «${con.first.$1}»';
  if (con.isEmpty) return 'Ya estaba en esas ${resultados.length} listas';
  return 'Añadido a ${con.length} listas';
}

/// Cuantas listas hacen falta para que aparezca el buscador.
const listasParaBuscar = 8;

class HojaAnadirALista extends StatefulWidget {
  const HojaAnadirALista({super.key, required this.coleccion, this.proveedorExtra});
  final Coleccion coleccion;
  final Future<List<DestinoLista>> Function()? proveedorExtra;

  @override
  State<HojaAnadirALista> createState() => _HojaAnadirAListaState();
}

class _HojaAnadirAListaState extends State<HojaAnadirALista> {
  late List<Json> _listas;
  List<DestinoLista> _extras = [];
  bool _cargando = false;
  late final int? _ultima;
  final _seleccion = <String>{};
  final _nuevas = <String>[];
  final _buscar = TextEditingController();
  final _nombreNueva = TextEditingController();
  bool _creando = false;
  String? _errorNueva;

  @override
  void initState() {
    super.initState();
    _ultima = widget.coleccion.ultimaLista;
    final memoria = widget.coleccion.listasEnMemoria;
    _listas = memoria ?? [];
    _cargando = memoria == null;
    _buscar.addListener(() => setState(() {}));
    _refrescar();
    final extra = widget.proveedorExtra;
    if (extra != null) {
      extra().then((d) {
        if (mounted) setState(() => _extras = d);
      }).catchError((_) {});
    }
  }

  @override
  void dispose() {
    _buscar.dispose();
    _nombreNueva.dispose();
    super.dispose();
  }

  Future<void> _refrescar() async {
    try {
      final l = await widget.coleccion.listas();
      if (mounted) {
        setState(() {
          _listas = l;
          _cargando = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _cargando = false);
    }
  }

  int? _idDe(Json l) => Servicios.idLista(l['id']);

  void _alternar(String k) => setState(() {
        if (!_seleccion.remove(k)) _seleccion.add(k);
      });

  EleccionLista _armar() => EleccionLista(
        ids: [for (final k in _seleccion) if (k.startsWith('l:')) int.parse(k.substring(2))],
        nuevas: [for (final n in _nuevas) if (_seleccion.contains('n:$n')) n],
        extras: [for (final d in _extras) if (_seleccion.contains('x:${d.id}')) d],
      );

  void _elegirYa(EleccionLista e) => Navigator.pop(context, e);

  Future<void> _abrirNueva() async {
    setState(() {
      _creando = true;
      _errorNueva = null;
    });
    final libre = await widget.coleccion.nombreLibre();
    if (!mounted) return;
    _nombreNueva.text = libre;
    _nombreNueva.selection = TextSelection(baseOffset: 0, extentOffset: libre.length);
  }

  void _crear() {
    final nombre = _nombreNueva.text.trim();
    if (nombre.isEmpty) {
      setState(() => _errorNueva = 'Escribe un nombre para la lista.');
      return;
    }
    final repetida = _listas.any((l) => '${l['nombre']}'.toLowerCase() == nombre.toLowerCase()) ||
        _nuevas.any((n) => n.toLowerCase() == nombre.toLowerCase());
    if (repetida) {
      setState(() => _errorNueva = 'Ya tienes una lista con ese nombre.');
      return;
    }
    // sin nada elegido: se crea y se anade, como siempre, en un solo gesto
    if (_seleccion.isEmpty) return _elegirYa(EleccionLista(nuevas: [nombre]));
    setState(() {
      _nuevas.add(nombre);
      _seleccion.add('n:$nombre');
      _creando = false;
      _errorNueva = null;
    });
  }

  Widget _marca(String clave, VoidCallback alTocar, String etiquetaAccesible) {
    final on = _seleccion.contains(clave);
    return IconButton(
      tooltip: on ? 'Quitar $etiquetaAccesible de la elección' : 'Elegir $etiquetaAccesible',
      icon: Icon(on ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
          color: on ? C.acento : C.texto3),
      onPressed: alTocar,
    );
  }

  Widget _filaLista(Json l) {
    final id = _idDe(l);
    if (id == null) return const SizedBox.shrink();
    final k = 'l:$id';
    final nombre = '${l['nombre']}';
    final n = l['n'] ?? 0;
    return ListTile(
      selected: _seleccion.contains(k),
      selectedTileColor: C.superficie3.withValues(alpha: 0.5),
      leading: const Icon(Icons.queue_music_rounded, color: C.texto2),
      title: Text(nombre, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text(n == 1 ? '1 canción' : '$n canciones', style: estiloSecundario),
      trailing: _marca(k, () => _alternar(k), '«$nombre»'),
      onTap: () => _seleccion.isEmpty ? _elegirYa(EleccionLista(ids: [id])) : _alternar(k),
    );
  }

  Widget _filaNueva(String nombre) {
    final k = 'n:$nombre';
    return ListTile(
      selected: _seleccion.contains(k),
      selectedTileColor: C.superficie3.withValues(alpha: 0.5),
      leading: CircleAvatar(backgroundColor: C.superficie3, child: Icon(Icons.add, color: C.acento)),
      title: Text(nombre, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: const Text('Lista nueva', style: estiloSecundario),
      trailing: _marca(k, () => _alternar(k), '«$nombre»'),
      onTap: () => _alternar(k),
    );
  }

  Widget _filaExtra(DestinoLista d) {
    final k = 'x:${d.id}';
    return ListTile(
      selected: _seleccion.contains(k),
      selectedTileColor: C.superficie3.withValues(alpha: 0.5),
      leading: Icon(d.icono, color: C.texto2),
      title: Row(children: [
        Flexible(child: Text(d.nombre, maxLines: 1, overflow: TextOverflow.ellipsis)),
        if (d.etiqueta.isNotEmpty) ...[
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(color: C.superficie3, borderRadius: BorderRadius.circular(20)),
            child: Text(d.etiqueta, style: const TextStyle(fontSize: 11, color: C.texto2)),
          ),
        ],
      ]),
      subtitle: d.detalle.isEmpty ? null : Text(d.detalle, style: estiloSecundario),
      trailing: _marca(k, () => _alternar(k), '«${d.nombre}»'),
      onTap: () => _seleccion.isEmpty ? _elegirYa(EleccionLista(extras: [d])) : _alternar(k),
    );
  }

  @override
  Widget build(BuildContext context) {
    final total = _listas.length + _extras.length + _nuevas.length;
    final conBuscador = total > listasParaBuscar;
    final q = _buscar.text.trim().toLowerCase();
    bool pasa(String nombre) => q.isEmpty || nombre.toLowerCase().contains(q);

    final propias = [for (final l in _listas) if (pasa('${l['nombre']}')) l];
    // la ultima usada va arriba (si se esta buscando, solo si coincide)
    Json? ultima;
    if (_ultima != null) {
      for (final l in propias) {
        if (_idDe(l) == _ultima) ultima = l;
      }
    }
    final resto = [for (final l in propias) if (!identical(l, ultima)) l];
    final extras = [for (final d in _extras) if (pasa(d.nombre)) d];
    final nuevas = [for (final n in _nuevas) if (pasa(n)) n];
    final hay = _seleccion.length;

    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.6,
        maxChildSize: 0.92,
        builder: (_, scroll) => Column(children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 4, 20, 8),
            child: Align(alignment: Alignment.centerLeft,
                child: Text('Añadir a una lista', style: estiloTituloSeccion)),
          ),
          if (conBuscador)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: TextField(
                controller: _buscar,
                textInputAction: TextInputAction.search,
                decoration: InputDecoration(
                  hintText: 'Buscar una lista',
                  prefixIcon: const Icon(Icons.search_rounded),
                  suffixIcon: q.isEmpty ? null : IconButton(
                      tooltip: 'Borrar búsqueda', icon: const Icon(Icons.close_rounded),
                      onPressed: _buscar.clear),
                  isDense: true,
                  filled: true,
                  fillColor: C.superficie3,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                ),
              ),
            ),
          Expanded(
            child: ListView(controller: scroll, children: [
              if (_creando)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Expanded(
                      child: TextField(
                        controller: _nombreNueva,
                        autofocus: true,
                        textInputAction: TextInputAction.done,
                        onSubmitted: (_) => _crear(),
                        onChanged: (_) {
                          if (_errorNueva != null) setState(() => _errorNueva = null);
                        },
                        decoration: InputDecoration(
                          labelText: 'Nombre de la lista nueva',
                          errorText: _errorNueva,
                          isDense: true,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: FilledButton(onPressed: _crear, child: const Text('Crear')),
                    ),
                  ]),
                )
              else
                ListTile(
                  leading: CircleAvatar(backgroundColor: C.superficie3, child: Icon(Icons.add, color: C.texto)),
                  title: const Text('Nueva lista', style: TextStyle(fontWeight: FontWeight.w700)),
                  onTap: _abrirNueva,
                ),
              if (_cargando) const LinearProgressIndicator(minHeight: 2),
              for (final n in nuevas) _filaNueva(n),
              if (ultima != null) ...[
                const Padding(
                  padding: EdgeInsets.fromLTRB(20, 10, 20, 2),
                  child: Text('Última que usaste', style: TextStyle(fontSize: 12, color: C.texto3)),
                ),
                _filaLista(ultima),
                if (resto.isNotEmpty)
                  const Padding(
                    padding: EdgeInsets.fromLTRB(20, 10, 20, 2),
                    child: Text('Tus listas', style: TextStyle(fontSize: 12, color: C.texto3)),
                  ),
              ],
              for (final l in resto) _filaLista(l),
              if (extras.isNotEmpty)
                const Padding(
                  padding: EdgeInsets.fromLTRB(20, 14, 20, 2),
                  child: Text('Compartidas contigo', style: TextStyle(fontSize: 12, color: C.texto3)),
                ),
              for (final d in extras) _filaExtra(d),
              if (!_cargando && q.isNotEmpty && propias.isEmpty && extras.isEmpty && nuevas.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: Text('No hay ninguna lista con ese nombre.', style: estiloSecundario)),
                ),
              const SizedBox(height: 8),
            ]),
          ),
          if (hay > 0)
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 6, 16, 10),
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: () => _elegirYa(_armar()),
                    child: Text(hay == 1 ? 'Listo' : 'Listo ($hay listas)'),
                  ),
                ),
              ),
            )
          else
            SizedBox(height: MediaQuery.paddingOf(context).bottom),
        ]),
      ),
    );
  }
}
