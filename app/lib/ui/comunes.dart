import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/gestures.dart' show kTouchSlop;
import 'package:flutter/material.dart';

import '../nucleo/coleccion.dart';
import '../reproduccion/reproductor.dart';
import 'plataforma.dart';
import 'servicios.dart';
import 'tema.dart';

// ---------------------------------------------------------------- portada

/// Imagen recortada que se decodifica al tamano en que se ve (la causa numero
/// uno de tirones en Android es decodificar portadas enormes).
class Portada extends StatelessWidget {
  const Portada({super.key, required this.url, this.lado = 48, this.alto, this.radio = 4,
      this.circulo = false, this.icono = Icons.music_note_rounded});

  final String url;
  final double lado;
  final double? alto;
  final double radio;
  final bool circulo;
  final IconData icono;

  @override
  Widget build(BuildContext context) {
    final h = alto ?? lado;
    final dpr = MediaQuery.devicePixelRatioOf(context);
    final ancho = (lado * dpr).round();
    final relleno = Container(
      color: C.superficie3,
      alignment: Alignment.center,
      child: Icon(icono, color: C.texto3, size: min(lado, h) * 0.4),
    );
    Widget img;
    if (url.isEmpty) {
      img = relleno;
    } else if (!url.startsWith('http')) {
      img = Image.file(File(url), fit: BoxFit.cover, cacheWidth: ancho, gaplessPlayback: true,
          errorBuilder: (_, _, _) => relleno);
    } else {
      img = CachedNetworkImage(
        imageUrl: url,
        fit: BoxFit.cover,
        memCacheWidth: ancho,
        fadeInDuration: const Duration(milliseconds: 140),
        placeholder: (_, _) => Container(color: C.superficie3),
        errorWidget: (_, _, _) => relleno,
      );
    }
    final caja = SizedBox(width: lado, height: h, child: img);
    return circulo ? ClipOval(child: caja) : ClipRRect(borderRadius: BorderRadius.circular(radio), child: caja);
  }
}

// ---------------------------------------------------------------- color de portada

final Map<String, Color> _colores = {};

/// Color dominante (vivo, oscurecido) de una portada, para los degradados.
Future<Color> colorDominante(String url, {Color defecto = const Color(0xFF2A3240)}) async {
  if (url.isEmpty) return defecto;
  final hecho = _colores[url];
  if (hecho != null) return hecho;
  try {
    final ImageProvider proveedor = url.startsWith('http')
        ? ResizeImage(CachedNetworkImageProvider(url), width: 24, height: 24)
        : ResizeImage(FileImage(File(url)), width: 24, height: 24);
    final completer = Completer<ImageInfo>();
    final stream = proveedor.resolve(ImageConfiguration.empty);
    late ImageStreamListener oyente;
    oyente = ImageStreamListener((info, _) {
      if (completer.isCompleted) {
        info.dispose();
      } else {
        completer.complete(info);
      }
      stream.removeListener(oyente);
    }, onError: (e, _) {
      if (!completer.isCompleted) completer.completeError(e);
      stream.removeListener(oyente);
    });
    stream.addListener(oyente);
    final ImageInfo info;
    try {
      info = await completer.future.timeout(const Duration(seconds: 8));
    } catch (_) {
      stream.removeListener(oyente);
      return defecto;
    }
    // quien recibe un ImageInfo debe liberarlo (si no, la imagen queda viva)
    final ByteData? datos;
    try {
      datos = await info.image.toByteData(format: ui.ImageByteFormat.rawRgba);
    } finally {
      info.dispose();
    }
    if (datos == null) return defecto;
    final grupos = <int, List<double>>{};
    for (var i = 0; i + 3 < datos.lengthInBytes; i += 4) {
      final c = Color.fromARGB(255, datos.getUint8(i), datos.getUint8(i + 1), datos.getUint8(i + 2));
      final hsv = HSVColor.fromColor(c);
      if (hsv.value < 0.16) continue;
      final g = (hsv.hue ~/ 24) * 10 + (hsv.saturation * 3.99).floor();
      final peso = 1 + hsv.saturation * 2 + hsv.value;
      final b = grupos.putIfAbsent(g, () => [0, 0, 0, 0, 0]);
      b[0] += c.r;
      b[1] += c.g;
      b[2] += c.b;
      b[3] += 1;
      b[4] += peso;
    }
    if (grupos.isEmpty) return defecto;
    final b = grupos.values.reduce((x, y) => x[4] > y[4] ? x : y);
    final c = Color.from(alpha: 1, red: b[0] / b[3], green: b[1] / b[3], blue: b[2] / b[3]);
    final hsv = HSVColor.fromColor(c);
    final final_ = hsv.withSaturation(min(1, hsv.saturation * 1.05)).withValue(hsv.value.clamp(0.28, 0.58)).toColor();
    _colores[url] = final_;
    return final_;
  } catch (_) {
    return defecto;
  }
}

// ---------------------------------------------------------------- fila de cancion

class FilaPista extends StatelessWidget {
  const FilaPista({super.key, required this.pista, required this.alPulsar, this.numero,
      this.mostrarPortada = true, this.extraMenu = const [], this.alMantener});

  final Json pista;
  final VoidCallback alPulsar;
  final int? numero;
  final bool mostrarPortada;
  final List<Widget> extraMenu;
  final VoidCallback? alMantener;

  bool _esActual(Reproductor r) {
    final a = r.actual;
    if (a == null) return false;
    if (identical(a, pista)) return true;
    if (a['clave'] != null && a['clave'] == pista['clave']) return true;
    final va = a['video_id'];
    return va != null && '$va'.isNotEmpty && va == pista['video_id'];
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    // la escala al pulsar va por fuera: lo que cambia en la coleccion no la reinicia
    return Pulsable(escala: 0.985, child: ListenableBuilder(
      listenable: Listenable.merge([s.reproductor, s.coleccion]),
      builder: (context, _) {
        final actual = _esActual(s.reproductor);
        final sonando = actual && s.reproductor.estado == EstadoRepro.sonando;
        final descargada = s.coleccion.estaDescargada(pista);
        final gusta = s.coleccion.meGusta('${pista['clave']}');
        return InkWell(
          onTap: alPulsar,
          onLongPress: alMantener ?? () => s.hojaPista(context, pista, extra: extraMenu),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 7),
            child: Row(children: [
              if (numero != null)
                SizedBox(
                  width: 30,
                  child: actual
                      ? Icon(sonando ? Icons.graphic_eq_rounded : Icons.play_arrow_rounded, color: C.acento, size: 18)
                      : Text('$numero', style: estiloSecundario),
                ),
              if (mostrarPortada) ...[
                Portada(url: '${pista['miniatura'] ?? ''}', lado: 48, radio: 4,
                    icono: pista['es_video'] == true ? Icons.videocam_rounded : Icons.music_note_rounded),
                const SizedBox(width: 12),
              ],
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${pista['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: estiloTituloFila.copyWith(color: actual ? C.acento : C.texto)),
                  const SizedBox(height: 3),
                  Row(children: [
                    if (descargada) ...[
                      const Icon(Icons.download_for_offline_rounded, size: 14, color: C.acento),
                      const SizedBox(width: 4),
                    ],
                    if (pista['explicito'] == true) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 3),
                        decoration: BoxDecoration(color: C.texto2, borderRadius: BorderRadius.circular(2)),
                        child: const Text('E', style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w900, color: C.panel)),
                      ),
                      const SizedBox(width: 5),
                    ],
                    if (pista['es_video'] == true && pista['archivo'] == null) ...[
                      const Icon(Icons.videocam_outlined, size: 14, color: C.texto3),
                      const SizedBox(width: 4),
                    ],
                    Expanded(
                      child: Text(
                        '${pista['artista'] ?? pista['subtitulo'] ?? ''}',
                        maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                    ),
                  ]),
                ]),
              ),
              if (gusta) const Padding(
                padding: EdgeInsets.only(left: 6),
                child: Icon(Icons.favorite_rounded, color: C.acento, size: 18),
              ),
              IconButton(
                icon: const Icon(Icons.more_vert_rounded, color: C.texto2),
                onPressed: () => s.hojaPista(context, pista, extra: extraMenu),
                visualDensity: VisualDensity.compact,
              ),
            ]),
          ),
        );
      },
    ));
  }
}

// ---------------------------------------------------------------- tarjetas

class Tarjeta extends StatelessWidget {
  const Tarjeta({super.key, required this.el, this.ancho = 150});

  final Json el;
  final double ancho;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final tipo = el['tipo'];
    if (tipo == 'genero') return TarjetaGenero(el: el, ancho: ancho);
    final esVideo = tipo == 'pista' && el['es_video'] == true && el['archivo'] == null;
    final w = esVideo ? ancho * 1.5 : ancho;
    final h = esVideo ? w * 9 / 16 : w;
    final esMeGusta = tipo == 'me_gusta';
    return RepaintBoundary(
      child: Pulsable(child: SizedBox(
        width: w,
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: () => s.abrirElemento(context, el),
          onLongPress: tipo == 'pista' ? () => s.hojaPista(context, el) : null,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            esMeGusta
                ? PortadaMeGusta(lado: w)
                : Portada(url: '${el['miniatura'] ?? el['foto'] ?? ''}', lado: w, alto: h,
                    radio: tipo == 'artista' ? 0 : 6, circulo: tipo == 'artista',
                    icono: switch (tipo) {
                      'artista' => Icons.person_rounded, 'album' => Icons.album_rounded,
                      'lista' || 'mi_lista' => Icons.queue_music_rounded, 'radio' => Icons.radio_rounded,
                      _ => Icons.music_note_rounded,
                    }),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: Text('${el['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  textAlign: tipo == 'artista' ? TextAlign.center : TextAlign.start,
                  style: estiloTituloTarjeta),
            ),
            const SizedBox(height: 2),
            SizedBox(
              width: double.infinity,
              child: Text('${el['subtitulo'] ?? el['artista'] ?? (tipo == 'artista' ? 'Artista' : '')}',
                  maxLines: 2, overflow: TextOverflow.ellipsis,
                  textAlign: tipo == 'artista' ? TextAlign.center : TextAlign.start,
                  style: estiloSubTarjeta),
            ),
          ]),
        ),
      )),
    );
  }
}

class PortadaMeGusta extends StatelessWidget {
  const PortadaMeGusta({super.key, this.lado = 48, this.radio = 6});
  final double lado;
  final double radio;

  @override
  Widget build(BuildContext context) => Container(
        width: lado,
        height: lado,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(radio),
          gradient: const LinearGradient(colors: [Color(0xFF5B3DF5), Color(0xFF22D3EE)],
              begin: Alignment.topLeft, end: Alignment.bottomRight),
        ),
        child: Icon(Icons.favorite_rounded, color: Colors.white, size: lado * 0.4),
      );
}

/// Genero / estado de animo: su color con una portada inclinada en la esquina.
class TarjetaGenero extends StatefulWidget {
  const TarjetaGenero({super.key, required this.el, this.ancho = 170});
  final Json el;
  final double ancho;

  @override
  State<TarjetaGenero> createState() => _TarjetaGeneroState();
}

class _TarjetaGeneroState extends State<TarjetaGenero> {
  String _portada = '';
  static final Map<String, String> _cache = {};

  @override
  void initState() {
    super.initState();
    final clave = '${widget.el['id']}|${widget.el['params']}';
    final hecho = _cache[clave];
    if (hecho != null) {
      _portada = hecho;
    } else {
      portadaGeneroAsync(widget.el).then((u) {
        _cache[clave] = u;
        if (mounted && u.isNotEmpty) setState(() => _portada = u);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _hex('${widget.el['color'] ?? '#7C5CFF'}');
    final alto = widget.ancho * 0.58;
    return Pulsable(child: GestureDetector(
      onTap: () => Caudal.leer(context).abrirElemento(context, widget.el),
      child: Container(
        width: widget.ancho,
        height: alto,
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          gradient: LinearGradient(
            colors: [HSVColor.fromColor(color).withValue(0.75).toColor(),
              HSVColor.fromColor(color).withValue(0.42).toColor()],
            begin: Alignment.topLeft, end: Alignment.bottomRight),
        ),
        child: Stack(children: [
          if (_portada.isNotEmpty)
            Positioned(
              right: -alto * 0.18,
              bottom: -alto * 0.12,
              child: Aparecer(
                child: Transform.rotate(
                  angle: 0.42,
                  child: Container(
                    decoration: const BoxDecoration(boxShadow: [
                      BoxShadow(color: Color(0x66000000), blurRadius: 8, offset: Offset(2, 4)),
                    ]),
                    child: Portada(url: _portada, lado: alto * 0.72, radio: 4),
                  ),
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 44, 8),
            child: Text('${widget.el['titulo'] ?? ''}', maxLines: 3, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, height: 1.15)),
          ),
        ]),
      ),
    ));
  }
}

Color _hex(String h) {
  final v = int.tryParse(h.replaceAll('#', ''), radix: 16) ?? 0x7C5CFF;
  return Color(0xFF000000 | v);
}

// ---------------------------------------------------------------- secciones

class TituloSeccion extends StatelessWidget {
  const TituloSeccion(this.texto, {super.key, this.alPulsarMas});
  final String texto;
  final VoidCallback? alPulsarMas;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.s, 10),
        child: Row(children: [
          Expanded(child: Text(texto, style: estiloTituloSeccion, maxLines: 1, overflow: TextOverflow.ellipsis)),
          if (alPulsarMas != null)
            TextButton(onPressed: alPulsarMas,
                style: TextButton.styleFrom(foregroundColor: C.texto2, visualDensity: VisualDensity.compact),
                child: const Text('Ver todo')),
        ]),
      );
}

class Carrusel extends StatelessWidget {
  const Carrusel({super.key, required this.titulo, required this.elementos, this.alPulsarMas});
  final String titulo;
  final List elementos;
  final VoidCallback? alPulsarMas;

  @override
  Widget build(BuildContext context) {
    final hayVideo = elementos.any((e) => (e as Map)['tipo'] == 'pista' && e['es_video'] == true && e['archivo'] == null);
    // solo si TODO son generos cabe en la franja baja; mezclados, manda la tarjeta normal
    final soloGeneros = elementos.isNotEmpty && elementos.every((e) => (e as Map)['tipo'] == 'genero');
    final hayNormal = elementos.any((e) {
      final m = e as Map;
      return m['tipo'] != 'genero' && !(m['tipo'] == 'pista' && m['es_video'] == true && m['archivo'] == null);
    });
    // con la letra del sistema al 120 % (el tope que pone main) tambien cabe
    final alto = soloGeneros ? 110.0 : (hayVideo && !hayNormal ? 212.0 : 230.0);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      TituloSeccion(titulo, alPulsarMas: alPulsarMas),
      SizedBox(
        height: alto,
        child: ListView.separated(
          // de lado tambien se recuerda donde quedo (al volver o al cambiar de filtro)
          key: PageStorageKey('carrusel|$titulo'),
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
          itemCount: elementos.length,
          separatorBuilder: (_, _) => const SizedBox(width: 14),
          itemBuilder: (_, i) => Tarjeta(el: Map<String, dynamic>.from(elementos[i] as Map)),
        ),
      ),
    ]);
  }
}

/// "Seleccion rapida": canciones en columnas de cuatro que se pasan de lado.
class RejillaRapida extends StatelessWidget {
  const RejillaRapida({super.key, required this.titulo, required this.pistas});
  final String titulo;
  final List<Json> pistas;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final columnas = (pistas.length / 4).ceil();
    final ancho = MediaQuery.sizeOf(context).width * 0.86;
    // cada fila crece con la letra del sistema (con 64 fijos, al 120 % se desbordaba)
    final fila = max(64.0, 14 + MediaQuery.textScalerOf(context).scale(44));
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      TituloSeccion(titulo),
      SizedBox(
        height: 4 * fila,
        child: ListView.builder(
          key: PageStorageKey('rapida|$titulo'),
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.only(left: 0, right: Esp.lado),
          physics: const PageScrollPhysics(),
          itemCount: columnas,
          itemBuilder: (_, c) => SizedBox(
            width: ancho,
            child: Column(children: [
              for (var i = c * 4; i < min(pistas.length, c * 4 + 4); i++)
                SizedBox(
                  height: fila,
                  child: FilaPista(
                    pista: pistas[i],
                    alPulsar: () => s.reproducirLista(context, pistas, inicio: i,
                        contexto: {'tipo': 'seleccion', 'id': titulo, 'titulo': titulo}),
                  ),
                ),
            ]),
          ),
        ),
      ),
    ]);
  }
}

/// Las secciones del catalogo convertidas en carruseles y rejillas.
///
/// [desde] es el turno de entrada de la primera (si encima ya hay otras).
List<Widget> pintarSecciones(BuildContext context, List secciones, {int desde = 0}) {
  final s = Caudal.leer(context);
  final salida = <Widget>[];
  for (final raw in secciones) {
    final sec = Map<String, dynamic>.from(raw as Map);
    final elementos = (sec['elementos'] as List? ?? []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    if (elementos.isEmpty) continue;
    final mas = sec['mas'] as Map?;
    VoidCallback? alMas;
    if (mas != null && mas['id'] != null) {
      alMas = () => s.abrirElemento(context, {'tipo': 'pagina', 'id': mas['id'], 'params': mas['params'],
        'titulo': sec['titulo']});
    }
    final Widget w;
    if (sec['estilo'] == 'filas' && elementos.every((e) => e['tipo'] == 'pista')) {
      w = RejillaRapida(titulo: '${sec['titulo']}', pistas: elementos);
    } else if (sec['estilo'] == 'rejilla') {
      w = RejillaTarjetas(titulo: '${sec['titulo']}', elementos: elementos);
    } else {
      w = Carrusel(titulo: '${sec['titulo']}', elementos: elementos, alPulsarMas: alMas);
    }
    // cada seccion entra un poco despues de la anterior
    salida.add(Entrada(indice: desde + salida.length ~/ 2, child: w));
    salida.add(const SizedBox(height: Esp.entreSecciones));
  }
  return salida;
}

class RejillaTarjetas extends StatelessWidget {
  const RejillaTarjetas({super.key, required this.titulo, required this.elementos});
  final String titulo;
  final List<Json> elementos;

  @override
  Widget build(BuildContext context) {
    final ancho = (MediaQuery.sizeOf(context).width - 32 - 12) / 2;
    final generos = elementos.every((e) => e['tipo'] == 'genero');
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      if (titulo.isNotEmpty) TituloSeccion(titulo),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
        child: Wrap(spacing: 12, runSpacing: generos ? 12 : 18, children: [
          for (final el in elementos) Tarjeta(el: el, ancho: ancho),
        ]),
      ),
    ]);
  }
}

// ---------------------------------------------------------------- al pulsar

/// Lo que se toca se hunde un poco y vuelve con suavidad, como una tecla.
///
/// Escucha los punteros sin entrar en la pelea de gestos: el InkWell o el
/// GestureDetector de dentro siguen recibiendo el toque, y si el dedo se
/// mueve (se esta desplazando la lista) la escala se suelta al instante.
class Pulsable extends StatefulWidget {
  const Pulsable({super.key, required this.child, this.escala = 0.965});
  final Widget child;

  /// El tamano mientras el dedo esta encima (1 = sin cambio).
  final double escala;

  @override
  State<Pulsable> createState() => _PulsableState();
}

class _PulsableState extends State<Pulsable> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 110), reverseDuration: const Duration(milliseconds: 260));
  late final Animation<double> _escala = Tween<double>(begin: 1, end: widget.escala)
      .animate(CurvedAnimation(parent: _c, curve: Curves.easeOut, reverseCurve: Curves.easeIn));
  Offset? _abajo;
  bool _quieto = false;

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  void _bajar(PointerDownEvent e) {
    if (_quieto) return;
    _abajo = e.position;
    _c.forward();
  }

  void _mover(PointerMoveEvent e) {
    final a = _abajo;
    if (a != null && (e.position - a).distance > kTouchSlop) _soltar(enSeco: true);
  }

  void _soltar({bool enSeco = false}) {
    if (_abajo == null) return;
    _abajo = null;
    // un toque muy corto: se termina de hundir antes de volver (si no, ni se nota)
    if (!enSeco && _c.status == AnimationStatus.forward) {
      _c.forward().whenCompleteOrCancel(() {
        if (mounted && _abajo == null) _c.reverse();
      });
    } else {
      _c.reverse();
    }
  }

  @override
  Widget build(BuildContext context) {
    _quieto = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    return Listener(
      onPointerDown: _bajar,
      onPointerMove: _mover,
      onPointerUp: (_) => _soltar(),
      onPointerCancel: (_) => _soltar(enSeco: true),
      child: ScaleTransition(scale: _escala, child: widget.child),
    );
  }
}

// ---------------------------------------------------------------- entrada escalonada

class _Marca {
  DateTime desde = DateTime.now();
}

/// Marca el momento en que llega el contenido de una pagina: las [Entrada]
/// que se montan poco despues aparecen escalonadas; las que se construyen mas
/// tarde (al desplazarse por una lista larga) salen ya quietas, sin parpadeos.
/// Cambiar [clave] (llegan datos nuevos, otro filtro) vuelve a empezar.
class Escalonado extends StatefulWidget {
  const Escalonado({super.key, this.clave, required this.child});
  final Object? clave;
  final Widget child;

  @override
  State<Escalonado> createState() => _EscalonadoState();
}

class _EscalonadoState extends State<Escalonado> {
  final _marca = _Marca();

  @override
  void didUpdateWidget(Escalonado viejo) {
    super.didUpdateWidget(viejo);
    if (viejo.clave != widget.clave) _marca.desde = DateTime.now();
  }

  @override
  Widget build(BuildContext context) => _Escalon(marca: _marca, child: widget.child);
}

class _Escalon extends InheritedWidget {
  const _Escalon({required this.marca, required super.child});
  final _Marca marca;

  @override
  bool updateShouldNotify(_Escalon viejo) => false;
}

/// Aparece subiendo un poco y con un fundido, en su turno ([indice]).
/// Solo se anima una vez, al montarse; despues no cuesta nada.
class Entrada extends StatefulWidget {
  const Entrada({super.key, this.indice = 0, this.desplazamiento = 14, required this.child});
  final int indice;
  final double desplazamiento;
  final Widget child;

  /// Pasado este tiempo desde que llego el contenido, ya no se anima.
  static const ventana = 900;

  @override
  State<Entrada> createState() => _EntradaState();
}

class _EntradaState extends State<Entrada> with SingleTickerProviderStateMixin {
  AnimationController? _c;
  Animation<double>? _a;
  bool _decidido = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_decidido) return;
    _decidido = true;
    if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) return;
    final marca = context.getInheritedWidgetOfExactType<_Escalon>()?.marca;
    final pasado = marca == null ? 0 : DateTime.now().difference(marca.desde).inMilliseconds;
    if (pasado > Entrada.ventana) return;
    final espera = max(0, min(widget.indice, 7) * 55 - pasado);
    final total = espera + Mov.entrada.inMilliseconds;
    final c = AnimationController(vsync: this, duration: Duration(milliseconds: total))..forward();
    _c = c;
    _a = CurvedAnimation(parent: c, curve: Interval(espera / total, 1, curve: Mov.curvaEntrada));
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final a = _a;
    if (a == null) return widget.child;
    return FadeTransition(
      opacity: a,
      child: AnimatedBuilder(
        animation: a,
        builder: (_, hijo) => Transform.translate(offset: Offset(0, (1 - a.value) * widget.desplazamiento), child: hijo),
        child: widget.child,
      ),
    );
  }
}

/// Un fundido corto al aparecer (una portada que llega tarde, un aviso).
class Aparecer extends StatelessWidget {
  const Aparecer({super.key, required this.child, this.duracion = Mov.normal});
  final Widget child;
  final Duration duracion;

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: 1),
        duration: duracion,
        curve: Mov.curva,
        builder: (_, v, hijo) => Opacity(opacity: v, child: hijo),
        child: child,
      );
}

// ---------------------------------------------------------------- esqueleto

/// Que se esta cargando: cada forma imita lo que va a aparecer, al mismo
/// tamano y en el mismo sitio, para que al llegar no salte nada.
enum FormaEsqueleto {
  /// Titulos con carruseles de tarjetas (Inicio, generos, "Ver todo").
  carruseles,

  /// Filas de canciones.
  filas,

  /// La rejilla de "Explorar todo" en Buscar.
  generos,

  /// Un album o una lista: portada centrada, titulo, botones y canciones.
  coleccion,

  /// Un artista: la foto a todo lo ancho, los botones y sus populares.
  artista,

  /// Los accesos de arriba en Inicio: dos columnas de 56 de alto.
  atajos,
}

/// Formas grises con un brillo que pasa: lo que se ve mientras algo carga.
class Esqueleto extends StatefulWidget {
  const Esqueleto({super.key, bool filas = false, FormaEsqueleto? forma})
      : forma = forma ?? (filas ? FormaEsqueleto.filas : FormaEsqueleto.carruseles);
  final FormaEsqueleto forma;

  @override
  State<Esqueleto> createState() => _EsqueletoState();
}

class _EsqueletoState extends State<Esqueleto> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1300))..repeat();

  // anchos que varian de una fila a otra (siempre los mismos: nada baila)
  static const _anchos = [0.62, 0.48, 0.7, 0.55, 0.4, 0.66, 0.52, 0.6];

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  static Widget _caja(double w, double h, {double r = 4}) => Container(
      width: w, height: h, decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(r)));

  static Widget _circulo(double lado) => Container(
      width: lado, height: lado, decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle));

  /// Igual que [FilaPista]: portada de 48, titulo y artista, 62 de alto.
  static Widget _filas(double ancho, int cuantas, {bool numero = false}) => Column(children: [
        for (var i = 0; i < cuantas; i++)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 7),
            child: SizedBox(
              height: 48,
              child: Row(children: [
                if (numero) ...[_caja(12, 14), const SizedBox(width: 18)] else _caja(48, 48),
                const SizedBox(width: 12),
                Expanded(child: Column(mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start, children: [
                  _caja((ancho - 140) * _anchos[i % _anchos.length], 14),
                  const SizedBox(height: 8),
                  _caja((ancho - 140) * _anchos[(i + 3) % _anchos.length] * 0.6, 11),
                ])),
              ]),
            ),
          ),
      ]);

  /// Igual que [TituloSeccion].
  static Widget _titulo(double w) =>
      Padding(padding: const EdgeInsets.fromLTRB(Esp.lado, 2, 0, 12), child: _caja(w, 21, r: 5));

  /// Igual que [Carrusel] con tarjetas de 150.
  static Widget _carrusel() => SizedBox(
        height: 230,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
            physics: const NeverScrollableScrollPhysics(), children: [
          for (var i = 0; i < 4; i++)
            Padding(
              padding: const EdgeInsets.only(right: 14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                _caja(150, 150, r: 6), const SizedBox(height: 10), _caja(150 * _anchos[i], 13),
                const SizedBox(height: 7), _caja(150 * _anchos[i + 2] * 0.8, 10),
              ]),
            ),
        ]),
      );

  /// Los botones de una coleccion o un artista: a la izquierda los pequenos,
  /// a la derecha el play grande.
  static Widget _botones({bool artista = false}) => Padding(
        padding: EdgeInsets.fromLTRB(Esp.lado, artista ? 14 : 8, Esp.lado, 8),
        child: Row(children: [
          if (artista) ...[_caja(84, 36, r: 18), const SizedBox(width: 12), _circulo(28)]
          else ...[_circulo(28), const SizedBox(width: 20), _circulo(28), const SizedBox(width: 20), _circulo(24)],
          const Spacer(),
          _circulo(28),
          const SizedBox(width: 14),
          _circulo(56),
        ]),
      );

  Widget _contenido(BuildContext context) {
    final ancho = MediaQuery.sizeOf(context).width;
    final arriba = MediaQuery.paddingOf(context).top;
    switch (widget.forma) {
      case FormaEsqueleto.filas:
        return Padding(padding: const EdgeInsets.only(top: 6), child: _filas(ancho, 9));
      case FormaEsqueleto.carruseles:
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          for (var s = 0; s < 3; s++) ...[
            _titulo(150 + 30.0 * (s % 2)),
            _carrusel(),
            const SizedBox(height: Esp.entreSecciones),
          ],
        ]);
      case FormaEsqueleto.generos:
        final w = (ancho - 32 - 12) / 2;
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _titulo(140),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
            child: Wrap(spacing: 12, runSpacing: 12, children: [
              for (var i = 0; i < 10; i++) _caja(w, w * 0.58, r: 8),
            ]),
          ),
        ]);
      case FormaEsqueleto.coleccion:
        final lado = ancho * 0.58;
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(height: arriba + kToolbarHeight + 8),
          Center(child: _caja(lado, lado)),
          const SizedBox(height: 20),
          Padding(padding: const EdgeInsets.symmetric(horizontal: Esp.lado), child: _caja(ancho * 0.6, 24, r: 5)),
          const SizedBox(height: 12),
          Padding(padding: const EdgeInsets.symmetric(horizontal: Esp.lado), child: _caja(ancho * 0.42, 12)),
          const SizedBox(height: 10),
          _botones(),
          _filas(ancho, 6),
        ]);
      case FormaEsqueleto.atajos:
        final w = (ancho - 32 - 8) / 2;
        return Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 6, Esp.lado, 20),
          child: Wrap(spacing: 8, runSpacing: 8, children: [
            for (var i = 0; i < 6; i++)
              SizedBox(
                width: w,
                height: 56,
                child: Row(children: [
                  _caja(56, 56, r: 6),
                  const SizedBox(width: 10),
                  _caja((w - 80) * _anchos[i], 12),
                ]),
              ),
          ]),
        );
      case FormaEsqueleto.artista:
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _caja(ancho, arriba + ancho * 0.82, r: 0),
          _botones(artista: true),
          const SizedBox(height: 8),
          _titulo(120),
          _filas(ancho, 5, numero: true),
        ]);
    }
  }

  @override
  Widget build(BuildContext context) {
    final contenido = _contenido(context);
    final brillo = RepaintBoundary(
      child: AnimatedBuilder(
        animation: _c,
        builder: (_, hijo) => ShaderMask(
          blendMode: BlendMode.srcIn,
          shaderCallback: (r) => LinearGradient(
            colors: const [Color(0x14FFFFFF), Color(0x2EFFFFFF), Color(0x14FFFFFF)],
            stops: const [0.35, 0.5, 0.65],
            begin: Alignment(-1.6 + _c.value * 3.2, -0.3),
            end: Alignment(-0.6 + _c.value * 3.2, 0.3),
          ).createShader(r),
          child: hijo,
        ),
        child: contenido,
      ),
    );
    // con alto limitado (cuerpo de una pagina) lo que sobra se recorta sin avisos;
    // dentro de una lista ocupa lo suyo
    return Semantics(
      label: 'Cargando',
      child: LayoutBuilder(builder: (_, c) => c.hasBoundedHeight
          ? SingleChildScrollView(physics: const NeverScrollableScrollPhysics(), primary: false, child: brillo)
          : brillo),
    );
  }
}

// ---------------------------------------------------------------- botones

class BotonPlay extends StatelessWidget {
  const BotonPlay({super.key, required this.alPulsar, this.sonando = false, this.lado = 56});
  final VoidCallback alPulsar;
  final bool sonando;
  final double lado;

  @override
  Widget build(BuildContext context) => Pulsable(
        escala: 0.9,
        child: Material(
          color: C.acento,
          shape: const CircleBorder(),
          elevation: 4,
          shadowColor: const Color(0x8022D3EE),
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: alPulsar,
            child: SizedBox(
              width: lado, height: lado,
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 160),
                transitionBuilder: (hijo, a) => ScaleTransition(scale: a, child: FadeTransition(opacity: a, child: hijo)),
                child: Icon(sonando ? Icons.pause_rounded : Icons.play_arrow_rounded,
                    key: ValueKey(sonando), color: C.acentoTexto, size: lado * 0.55),
              ),
            ),
          ),
        ),
      );
}

/// Un filtro en forma de pastilla (Inicio, Buscar, Tu biblioteca): el color
/// pasa con suavidad al elegirlo y se hunde un poco al tocarlo.
class Pildora extends StatelessWidget {
  const Pildora({super.key, this.texto, this.icono, required this.activa, required this.alPulsar, this.tooltip});
  final String? texto;
  final IconData? icono;
  final bool activa;
  final VoidCallback alPulsar;
  final String? tooltip;

  @override
  Widget build(BuildContext context) {
    final color = activa ? C.acentoTexto : C.texto;
    Widget contenido = AnimatedContainer(
      duration: Mov.normal,
      curve: Mov.curva,
      constraints: const BoxConstraints(minHeight: 34),
      alignment: Alignment.center,
      padding: EdgeInsets.symmetric(horizontal: texto == null ? 10 : 16),
      decoration: BoxDecoration(color: activa ? C.acento : C.superficie2, borderRadius: BorderRadius.circular(999)),
      child: texto == null
          ? Icon(icono, size: 17, color: color)
          : AnimatedDefaultTextStyle(
              duration: Mov.normal,
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: color, height: 1.2),
              child: Text(texto!),
            ),
    );
    if (tooltip != null) contenido = Tooltip(message: tooltip!, child: contenido);
    return Padding(
      padding: const EdgeInsets.only(right: Esp.s),
      child: Semantics(
        button: true,
        selected: activa,
        child: Pulsable(
          escala: 0.94,
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () {
              Haptico.seleccion();
              alPulsar();
            },
            // area de toque comoda aunque la pastilla se vea fina
            child: Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: contenido),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- estados vacios y errores

/// Cuando no hay nada que mostrar (o algo fallo): un icono con halo, que paso
/// y que se puede hacer. [alAccion] pone el boton (por defecto "Reintentar").
class Vacio extends StatelessWidget {
  const Vacio({super.key, required this.icono, required this.titulo, required this.texto, this.accion,
      this.alAccion, this.textoAccion, this.iconoAccion, this.error = false});
  final IconData icono;
  final String titulo;
  final String texto;
  final Widget? accion;
  final VoidCallback? alAccion;
  final String? textoAccion;
  final IconData? iconoAccion;

  /// Algo fallo (el halo va en rojo suave).
  final bool error;

  @override
  Widget build(BuildContext context) {
    final tono = error ? C.error : C.acento;
    final boton = accion ??
        (alAccion == null
            ? null
            : FilledButton.icon(
                onPressed: alAccion,
                icon: Icon(iconoAccion ?? Icons.refresh_rounded, size: 20),
                label: Text(textoAccion ?? 'Reintentar'),
                style: FilledButton.styleFrom(
                  backgroundColor: C.texto,
                  foregroundColor: C.fondo,
                  shape: const StadiumBorder(),
                  padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 12),
                  textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                ),
              ));
    final cuerpo = Entrada(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: Esp.xxl, vertical: 44),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 340),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Container(
                width: 92,
                height: 92,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(colors: [tono.withValues(alpha: 0.22), tono.withValues(alpha: 0.03)]),
                  border: Border.all(color: tono.withValues(alpha: 0.22)),
                ),
                child: Icon(icono, size: 40, color: error ? C.error : C.acentoAlto),
              ),
              const SizedBox(height: 20),
              Text(titulo, textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, letterSpacing: -0.2, height: 1.2)),
              if (texto.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(texto, textAlign: TextAlign.center, style: estiloSecundario.copyWith(height: 1.45)),
              ],
              if (boton != null) ...[const SizedBox(height: 22), boton],
            ]),
          ),
        ),
      ),
    );
    // como cuerpo de una pagina: centrado, y si no cabe (teclado abierto) se desplaza
    return LayoutBuilder(builder: (_, c) => !c.hasBoundedHeight
        ? cuerpo
        : SingleChildScrollView(
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: c.maxHeight),
              child: Align(alignment: const Alignment(0, -0.25), child: cuerpo),
            ),
          ));
  }
}

/// El texto de un fallo, entendible: los mensajes del catalogo ya lo son; lo
/// tecnico (excepciones, trazas) se cambia por lo que significa para quien usa la app.
String explicarError(Object? e) {
  final t = '${e ?? ''}'.trim();
  final tecnico = t.isEmpty ||
      RegExp(r'Exception|Error:|Null check|is not a subtype|#\d|StackTrace').hasMatch(t);
  if (!tecnico) return t;
  if (RegExp(r'Socket|Dio|Handshake|Timeout|host|network|connection', caseSensitive: false).hasMatch(t)) {
    return 'Parece que no hay conexión. Revisa el wifi o los datos y vuelve a intentarlo.';
  }
  return 'Algo falló al cargar. Vuelve a intentarlo en un momento.';
}

// ---------------------------------------------------------------- cabecera plegable

/// La cabecera de un artista o un album: al subir se pliega con parallax (el
/// fondo va a media velocidad), al tirar hacia abajo se estira, y la barra que
/// queda arriba se tine con el [color] de la portada. El color nuevo entra con
/// un fundido. Solo se reconstruye la cabecera al desplazarse, nunca la pagina.
class CabeceraPlegable extends StatelessWidget {
  const CabeceraPlegable({super.key, required this.titulo, required this.color, required this.alto,
      required this.fondo, this.acciones = const [], this.degradado = false});

  final String titulo;
  final Color color;

  /// Alto desplegado, sin contar la barra de estado.
  final double alto;

  /// Lo que se ve desplegado (va con parallax).
  final Widget fondo;
  final List<Widget> acciones;

  /// Pinta debajo del fondo un degradado del color hacia [colorMedio], para
  /// enlazar con lo que sigue debajo de la cabecera.
  final bool degradado;

  /// El color en el que acaba la cabecera (y empieza lo de debajo).
  static Color colorMedio(Color c) => Color.lerp(c, C.fondo, 0.5)!;

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<Color?>(
        tween: ColorTween(end: color),
        duration: Mov.color,
        curve: Mov.curva,
        builder: (_, c, _) {
          final base = c ?? color;
          final barra = Color.lerp(base, Colors.black, 0.45)!;
          return SliverAppBar(
            pinned: true,
            stretch: true,
            expandedHeight: alto,
            backgroundColor: barra,
            surfaceTintColor: Colors.transparent,
            foregroundColor: C.texto,
            title: _TituloPlegado(titulo),
            actions: acciones,
            flexibleSpace: _FondoPlegable(color: base, barra: barra, degradado: degradado, child: fondo),
          );
        },
      );
}

/// Cuanto queda desplegada la cabecera: 1 abierta, 0 plegada (y el estirado).
(double, double) _pliegue(BuildContext context) {
  final s = context.dependOnInheritedWidgetOfExactType<FlexibleSpaceBarSettings>();
  if (s == null) return (1, 0);
  final rango = s.maxExtent - s.minExtent;
  final t = rango <= 0 ? 1.0 : ((s.currentExtent - s.minExtent) / rango).clamp(0.0, 1.0);
  return (t, max(0.0, s.currentExtent - s.maxExtent));
}

class _TituloPlegado extends StatelessWidget {
  const _TituloPlegado(this.titulo);
  final String titulo;

  @override
  Widget build(BuildContext context) {
    final (t, _) = _pliegue(context);
    // el titulo pequeno solo aparece al final, cuando el grande ya se fue
    final o = (((1 - t) - 0.72) / 0.28).clamp(0.0, 1.0);
    return Opacity(opacity: o, child: Text(titulo, maxLines: 1, overflow: TextOverflow.ellipsis));
  }
}

class _FondoPlegable extends StatelessWidget {
  const _FondoPlegable({required this.color, required this.barra, required this.degradado, required this.child});
  final Color color;
  final Color barra;
  final bool degradado;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final s = context.dependOnInheritedWidgetOfExactType<FlexibleSpaceBarSettings>();
    final (t, _) = _pliegue(context);
    final maximo = s?.maxExtent ?? 0;
    final actual = s?.currentExtent ?? maximo;
    final subido = max(0.0, maximo - actual);
    final tinte = Curves.easeIn.transform(1 - t);
    return ClipRect(
      child: Stack(fit: StackFit.expand, children: [
        if (degradado)
          DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
              colors: [color, CabeceraPlegable.colorMedio(color)],
              begin: Alignment.topCenter, end: Alignment.bottomCenter))),
        // parallax: el fondo sube a la mitad de velocidad; al estirar crece
        Positioned(top: -subido * 0.5, left: 0, right: 0, height: max(maximo, actual), child: child),
        if (!degradado)
          const IgnorePointer(
            child: DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
                colors: [Color(0x66000000), Color(0x00000000)], stops: [0, 0.32],
                begin: Alignment.topCenter, end: Alignment.bottomCenter))),
          ),
        if (tinte > 0.001) IgnorePointer(child: ColoredBox(color: barra.withValues(alpha: tinte))),
      ]),
    );
  }
}

/// La portada de un album dentro de [CabeceraPlegable]: al plegar se encoge
/// y se desvanece; al estirar crece un poco.
class PortadaPlegable extends StatelessWidget {
  const PortadaPlegable({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final (t, estirado) = _pliegue(context);
    final escala = 0.74 + 0.26 * t + min(0.12, estirado / 900);
    final o = ((t - 0.12) / 0.88).clamp(0.0, 1.0);
    return Opacity(
      opacity: o,
      child: Transform.scale(
        scale: escala,
        alignment: Alignment.bottomCenter,
        // la imagen no se vuelve a pintar en cada fotograma del pliegue
        child: RepaintBoundary(child: child),
      ),
    );
  }
}

// ---------------------------------------------------------------- dialogos

Future<String?> pedirTexto(BuildContext context, String titulo, String inicial) {
  final c = TextEditingController(text: inicial)..selection = TextSelection(baseOffset: 0, extentOffset: inicial.length);
  return showDialog<String>(
    context: context,
    useRootNavigator: true,
    builder: (ctx) => AlertDialog(
      backgroundColor: C.superficie2,
      title: Text(titulo),
      content: TextField(controller: c, autofocus: true, onSubmitted: (t) => Navigator.pop(ctx, t.trim())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
        FilledButton(onPressed: () => Navigator.pop(ctx, c.text.trim()), child: const Text('Guardar')),
      ],
    ),
  ).then((t) => (t == null || t.isEmpty) ? null : t);
}

Future<bool> confirmar(BuildContext context, String titulo, String texto, {String si = 'Borrar'}) async =>
    await showDialog<bool>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.superficie2,
        title: Text(titulo),
        content: Text(texto),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(si)),
        ],
      ),
    ) ??
    false;

/// Los formatos de descarga (los mismos que en el escritorio).
const presetsDescarga = <(String, String, Map<String, String>)>[
  ('Audio · MP3 320 kbps', 'Lo abre todo', {'tipo': 'audio', 'formato_audio': 'mp3'}),
  ('Audio · M4A / AAC', 'Sin recomprimir, ocupa poco', {'tipo': 'audio', 'formato_audio': 'm4a'}),
  ('Audio · OPUS original', 'La mejor calidad de YouTube', {'tipo': 'audio', 'formato_audio': 'opus'}),
  ('Audio · FLAC', 'Contenedor sin pérdida', {'tipo': 'audio', 'formato_audio': 'flac'}),
  ('Audio · WAV', 'Sin compresión', {'tipo': 'audio', 'formato_audio': 'wav'}),
  ('Video · Máxima calidad', 'La mejor imagen disponible', {'tipo': 'completo', 'calidad': 'mejor'}),
  ('Video · 1080p', 'Full HD', {'tipo': 'completo', 'calidad': '1080'}),
  ('Video · 720p', 'HD, ocupa menos', {'tipo': 'completo', 'calidad': '720'}),
  ('Video · 480p', 'Para ahorrar espacio', {'tipo': 'completo', 'calidad': '480'}),
  ('Solo video, sin sonido', 'La imagen sola', {'tipo': 'video', 'calidad': 'mejor'}),
];

Future<Map<String, String>?> elegirFormato(BuildContext context, {String titulo = 'Descargar'}) =>
    showModalBottomSheet<Map<String, String>>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.7,
        maxChildSize: 0.92,
        builder: (_, scroll) => ListView(controller: scroll, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
            child: Text(titulo, style: estiloTituloSeccion, maxLines: 2),
          ),
          for (final (i, (nombre, ayuda, opciones)) in presetsDescarga.indexed) ...[
            if (i == 5) const Divider(),
            ListTile(
              leading: Icon(opciones['tipo'] == 'audio' ? Icons.music_note_rounded : Icons.movie_rounded,
                  color: C.texto2),
              title: Text(nombre, style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text(ayuda, style: estiloSecundario),
              onTap: () => Navigator.pop(ctx, opciones),
            ),
          ],
          // por encima del indicador de inicio del iPhone
          SizedBox(height: 12 + MediaQuery.paddingOf(ctx).bottom),
        ]),
      ),
    );

// el puente con el catalogo para las portadas de genero (lo resuelve main)
Future<String> Function(Json) portadaGeneroAsync = (_) async => '';
