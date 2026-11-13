import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../nucleo/coleccion.dart';
import '../reproduccion/reproductor.dart';
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
          errorBuilder: (_, __, ___) => relleno);
    } else {
      img = CachedNetworkImage(
        imageUrl: url,
        fit: BoxFit.cover,
        memCacheWidth: ancho,
        fadeInDuration: const Duration(milliseconds: 140),
        placeholder: (_, __) => Container(color: C.superficie3),
        errorWidget: (_, __, ___) => relleno,
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
    return ListenableBuilder(
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
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
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
                      style: TextStyle(fontSize: 15.5, fontWeight: FontWeight.w600,
                          color: actual ? C.acento : C.texto)),
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
    );
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
      child: SizedBox(
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
            Text('${el['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                textAlign: tipo == 'artista' ? TextAlign.center : TextAlign.start,
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
            const SizedBox(height: 2),
            SizedBox(
              width: double.infinity,
              child: Text('${el['subtitulo'] ?? el['artista'] ?? (tipo == 'artista' ? 'Artista' : '')}',
                  maxLines: 2, overflow: TextOverflow.ellipsis,
                  textAlign: tipo == 'artista' ? TextAlign.center : TextAlign.start,
                  style: const TextStyle(fontSize: 12.5, color: C.texto2, height: 1.25)),
            ),
          ]),
        ),
      ),
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
    return GestureDetector(
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
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 44, 8),
            child: Text('${widget.el['titulo'] ?? ''}', maxLines: 3, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, height: 1.15)),
          ),
        ]),
      ),
    );
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
        padding: const EdgeInsets.fromLTRB(16, 0, 8, 10),
        child: Row(children: [
          Expanded(child: Text(texto, style: estiloTituloSeccion, maxLines: 1, overflow: TextOverflow.ellipsis)),
          if (alPulsarMas != null)
            TextButton(onPressed: alPulsarMas,
                child: const Text('Ver todo', style: TextStyle(color: C.texto2, fontWeight: FontWeight.w700))),
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
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          itemCount: elementos.length,
          separatorBuilder: (_, __) => const SizedBox(width: 14),
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
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.only(left: 0, right: 16),
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
List<Widget> pintarSecciones(BuildContext context, List secciones) {
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
    if (sec['estilo'] == 'filas' && elementos.every((e) => e['tipo'] == 'pista')) {
      salida.add(RejillaRapida(titulo: '${sec['titulo']}', pistas: elementos));
    } else if (sec['estilo'] == 'rejilla') {
      salida.add(RejillaTarjetas(titulo: '${sec['titulo']}', elementos: elementos));
    } else {
      salida.add(Carrusel(titulo: '${sec['titulo']}', elementos: elementos, alPulsarMas: alMas));
    }
    salida.add(const SizedBox(height: 26));
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
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Wrap(spacing: 12, runSpacing: generos ? 12 : 18, children: [
          for (final el in elementos) Tarjeta(el: el, ancho: ancho),
        ]),
      ),
    ]);
  }
}

// ---------------------------------------------------------------- esqueleto

/// Formas grises con un brillo que pasa: lo que se ve mientras algo carga.
class Esqueleto extends StatefulWidget {
  const Esqueleto({super.key, this.filas = false});
  final bool filas;

  @override
  State<Esqueleto> createState() => _EsqueletoState();
}

class _EsqueletoState extends State<Esqueleto> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1300))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  Widget _caja(double w, double h, {double r = 6}) => Container(
        width: w, height: h,
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(r)));

  @override
  Widget build(BuildContext context) {
    final contenido = widget.filas
        ? Column(children: [
            for (var i = 0; i < 7; i++)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(children: [
                  _caja(48, 48, r: 4),
                  const SizedBox(width: 12),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    _caja(180, 13), const SizedBox(height: 8), _caja(110, 10),
                  ])),
                ]),
              ),
          ])
        : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (var s = 0; s < 3; s++) ...[
              Padding(padding: const EdgeInsets.fromLTRB(16, 8, 0, 12), child: _caja(170, 20)),
              SizedBox(
                height: 200,
                child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 16),
                    physics: const NeverScrollableScrollPhysics(), children: [
                  for (var i = 0; i < 4; i++)
                    Padding(
                      padding: const EdgeInsets.only(right: 14),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        _caja(150, 150), const SizedBox(height: 10), _caja(110, 12), const SizedBox(height: 6), _caja(80, 10),
                      ]),
                    ),
                ]),
              ),
              const SizedBox(height: 16),
            ],
          ]);
    return AnimatedBuilder(
      animation: _c,
      builder: (_, hijo) => ShaderMask(
        blendMode: BlendMode.srcIn,
        shaderCallback: (r) => LinearGradient(
          colors: const [Color(0x14FFFFFF), Color(0x2EFFFFFF), Color(0x14FFFFFF)],
          stops: const [0.35, 0.5, 0.65],
          begin: Alignment(-1.6 + _c.value * 3.2, 0),
          end: Alignment(-0.6 + _c.value * 3.2, 0),
        ).createShader(r),
        child: hijo,
      ),
      child: contenido,
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
  Widget build(BuildContext context) => Material(
        color: C.acento,
        shape: const CircleBorder(),
        elevation: 4,
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: alPulsar,
          child: SizedBox(
            width: lado, height: lado,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 160),
              child: Icon(sonando ? Icons.pause_rounded : Icons.play_arrow_rounded,
                  key: ValueKey(sonando), color: C.acentoTexto, size: lado * 0.55),
            ),
          ),
        ),
      );
}

class Vacio extends StatelessWidget {
  const Vacio({super.key, required this.icono, required this.titulo, required this.texto, this.accion});
  final IconData icono;
  final String titulo;
  final String texto;
  final Widget? accion;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 48),
        child: Column(children: [
          Icon(icono, size: 52, color: C.texto3),
          const SizedBox(height: 14),
          Text(titulo, textAlign: TextAlign.center, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Text(texto, textAlign: TextAlign.center, style: estiloSecundario),
          if (accion != null) ...[const SizedBox(height: 18), accion!],
        ]),
      );
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
