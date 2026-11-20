// Las imágenes para compartir la canción que suena: varios diseños (Historia, Vinilo,
// Letra, Polaroid, Cristal y Recibo) pintados con los colores de la carátula.
//
// Cada diseño llena el espacio que le dan y todo escala con el ancho (k = ancho / 360),
// así la vista previa de la hoja y la imagen final (1080 px de ancho) son la misma
// tarjeta. Nada aquí lee el reproductor: todo llega en [DatosCompartir], y por eso las
// pruebas pueden pintar cada diseño con datos de ejemplo.

import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import '../../nucleo/mascota_app.dart';
import '../comunes.dart';
import 'paleta_portada.dart';

/// Los diseños que se pueden elegir, en el orden en que se muestran.
enum DisenoCompartir {
  historia('Historia', Icons.auto_awesome_rounded),
  vinilo('Vinilo', Icons.album_rounded),
  letra('Letra', Icons.format_quote_rounded),
  polaroid('Polaroid', Icons.photo_outlined),
  cristal('Cristal', Icons.blur_on_rounded),
  recibo('Recibo', Icons.receipt_long_rounded),
  // exclusivos de donadores y fundadores
  holograma('Holograma', Icons.auto_awesome_motion_rounded, exclusivo: true),
  oro('Oro', Icons.workspace_premium_rounded, exclusivo: true),
  galaxia('Galaxia', Icons.blur_circular_rounded, exclusivo: true),
  neon('Neón', Icons.nightlife_rounded, exclusivo: true);

  const DisenoCompartir(this.nombre, this.icono, {this.exclusivo = false});
  final String nombre;
  final IconData icono;

  /// Solo para cuentas donadoras o fundadoras (los demás lo ven con candado).
  final bool exclusivo;

  static DisenoCompartir? porNombre(String? n) {
    for (final d in values) {
      if (d.name == n) return d;
    }
    return null;
  }
}

/// La forma de la imagen: vertical para historias y estados, cuadrada para publicaciones.
enum FormatoCompartir {
  historia('Historia', 9 / 16, 1080, 1920),
  cuadrado('Cuadrado', 1, 1080, 1080);

  const FormatoCompartir(this.nombre, this.proporcion, this.anchoPx, this.altoPx);
  final String nombre;

  /// Ancho entre alto.
  final double proporcion;
  final int anchoPx, altoPx;

  static FormatoCompartir? porNombre(String? n) {
    for (final f in values) {
      if (f.name == n) return f;
    }
    return null;
  }
}

/// Lo que se pinta en la tarjeta: la canción, sus colores, el momento y la mascota.
@immutable
class DatosCompartir {
  const DatosCompartir({
    required this.titulo,
    required this.artista,
    required this.caratula,
    this.paleta = PaletaPortada.neutra,
    this.posicion = Duration.zero,
    this.duracion = Duration.zero,
    this.calidad,
    this.verso,
    this.versoSiguiente,
    this.contexto,
    this.mascota,
    this.hojaMascota,
    this.fecha,
    this.sello = 'Donador',
  });

  /// El sello de los diseños exclusivos: «Donador» o «Fundador».
  final String sello;

  final String titulo, artista;

  /// La URL (o ruta) de la carátula, como la que usa [Portada].
  final String caratula;
  final PaletaPortada paleta;
  final Duration posicion, duracion;

  /// La calidad de lo que suena, p. ej. «Opus · 138 kbps» (null si no se sabe).
  final String? calidad;

  /// La línea de la letra que está sonando y la que viene (null si no hay letra).
  final String? verso, versoSiguiente;

  /// De dónde suena (una lista, una radio...), si se sabe.
  final String? contexto;

  /// La mascota elegida y su hoja de dibujos ya decodificada (sin hoja no se pinta).
  final Mascota? mascota;
  final ui.Image? hojaMascota;

  /// Para el recibo; por defecto, ahora.
  final DateTime? fecha;

  bool get hayLetra => (verso ?? '').trim().isNotEmpty;
  bool get hayMascota => mascota != null && hojaMascota != null;

  double get avance {
    final d = duracion.inMilliseconds;
    return d <= 0 ? 0 : (posicion.inMilliseconds / d).clamp(0.0, 1.0);
  }

  DatosCompartir copiar({String? caratula, ui.Image? hojaMascota, PaletaPortada? paleta}) => DatosCompartir(
        titulo: titulo,
        artista: artista,
        caratula: caratula ?? this.caratula,
        paleta: paleta ?? this.paleta,
        posicion: posicion,
        duracion: duracion,
        calidad: calidad,
        verso: verso,
        versoSiguiente: versoSiguiente,
        contexto: contexto,
        mascota: mascota,
        hojaMascota: hojaMascota ?? this.hojaMascota,
        fecha: fecha,
        sello: sello,
      );
}

/// «2:14» o «1:02:03».
String tiempoCompartir(Duration d) {
  final s = d.inSeconds.abs();
  final h = s ~/ 3600, m = (s % 3600) ~/ 60, ss = s % 60;
  final seg = ss.toString().padLeft(2, '0');
  return h > 0 ? '$h:${m.toString().padLeft(2, '0')}:$seg' : '$m:$seg';
}

/// Una tarjeta para compartir. Llena el espacio que le den (la forma la decide quien la
/// pone: [FormatoCompartir.proporcion]).
class TarjetaCancion extends StatelessWidget {
  const TarjetaCancion({
    super.key,
    required this.diseno,
    required this.datos,
    this.mostrarMascota = true,
    this.mostrarLetra = true,
    this.fase = 0.3,
  });

  final DisenoCompartir diseno;
  final DatosCompartir datos;
  final bool mostrarMascota, mostrarLetra;

  /// El momento de la animación de los diseños exclusivos (0 a 1): mueve brillos y partículas.
  final double fase;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      final ancho = c.maxWidth.isFinite ? c.maxWidth : 360.0;
      final alto = c.maxHeight.isFinite ? c.maxHeight : ancho * 16 / 9;
      final t = _Trazo(
        k: ancho / 360,
        ancho: ancho,
        alto: alto,
        d: datos,
        mascota: mostrarMascota && datos.hayMascota,
        letra: mostrarLetra && datos.hayLetra,
        fase: fase,
      );
      final Widget cuerpo = switch (diseno) {
        DisenoCompartir.historia => _Historia(t),
        DisenoCompartir.vinilo => _Vinilo(t),
        DisenoCompartir.letra => _Letra(t),
        DisenoCompartir.polaroid => _Polaroid(t),
        DisenoCompartir.cristal => _Cristal(t),
        DisenoCompartir.recibo => _Recibo(t),
        DisenoCompartir.holograma => _Holograma(t),
        DisenoCompartir.oro => _Oro(t),
        DisenoCompartir.galaxia => _Galaxia(t),
        DisenoCompartir.neon => _Neon(t),
      };
      // se mezcla con el estilo del tema para conservar su letra (Roboto en Android)
      return DefaultTextStyle.merge(
        style: TextStyle(
          color: Colors.white,
          fontSize: 14 * t.k,
          height: 1.2,
          decoration: TextDecoration.none,
          fontWeight: FontWeight.w500,
        ),
        child: SizedBox(width: ancho, height: alto, child: ClipRect(child: cuerpo)),
      );
    });
  }
}

/// Saca la tarjeta que está dentro de [clave] (un [RepaintBoundary]) como PNG de [anchoPx]
/// de ancho. Hay que llamarla con la tarjeta ya pintada en pantalla.
Future<Uint8List> imagenDeTarjeta(GlobalKey clave, {required int anchoPx, int? altoPx}) async {
  final ro = clave.currentContext?.findRenderObject();
  if (ro is! RenderRepaintBoundary || !ro.attached || ro.size.width <= 0) {
    throw StateError('la tarjeta todavía no se ve');
  }
  var imagen = await ro.toImage(pixelRatio: anchoPx / ro.size.width);
  // la vista previa puede medir medio píxel de más o de menos: la imagen final queda exacta
  final alto = altoPx ?? (anchoPx * ro.size.height / ro.size.width).round();
  if (imagen.width != anchoPx || imagen.height != alto) {
    final grabadora = ui.PictureRecorder();
    Canvas(grabadora).drawImageRect(
      imagen,
      Rect.fromLTWH(0, 0, imagen.width.toDouble(), imagen.height.toDouble()),
      Rect.fromLTWH(0, 0, anchoPx.toDouble(), alto.toDouble()),
      Paint()..filterQuality = FilterQuality.high,
    );
    final exacta = await grabadora.endRecording().toImage(anchoPx, alto);
    imagen.dispose();
    imagen = exacta;
  }
  try {
    final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
    if (datos == null) throw StateError('no se pudo dibujar la imagen');
    return datos.buffer.asUint8List(datos.offsetInBytes, datos.lengthInBytes);
  } finally {
    imagen.dispose();
  }
}

// ---------------------------------------------------------------- piezas comunes

/// Las medidas y opciones de una tarjeta, para no pasarlas una por una.
class _Trazo {
  const _Trazo({
    required this.k,
    required this.ancho,
    required this.alto,
    required this.d,
    required this.mascota,
    required this.letra,
    this.fase = 0.3,
  });

  final double k, ancho, alto, fase;
  final DatosCompartir d;
  final bool mascota, letra;

  bool get cuadrado => alto / ancho < 1.3;
  PaletaPortada get p => d.paleta;

  /// El acento, siempre vivo y claro (aunque la carátula sea apagada).
  Color get acento {
    final h = HSVColor.fromColor(p.acento);
    return h.saturation < 0.15 ? p.acento : h.withValue(math.max(h.value, 0.9)).toColor();
  }

  /// Un segundo acento para los degradados del borde: el contraste aclarado.
  Color get acento2 {
    final h = HSVColor.fromColor(p.contraste);
    if (h.saturation < 0.15) return Color.lerp(acento, Colors.white, 0.4)!;
    return h.withSaturation(h.saturation.clamp(0.45, 0.9)).withValue(0.95).toColor();
  }
}

/// La carátula sin pixelar: [Portada] decodifica la imagen al tamaño que pinta (lado por
/// densidad de pantalla) y la hoja de compartir sube esa densidad a la de la imagen final.
Widget _caratula(String url, double lado, double radio, {bool circulo = false}) =>
    Portada(url: url, lado: lado, radio: radio, circulo: circulo);

/// La carátula muy difuminada llenando el fondo. Se decodifica pequeña: total, va borrosa.
class _FondoDifuminado extends StatelessWidget {
  const _FondoDifuminado(this.t, {this.sigma = 34, this.escala = 1.5});
  final _Trazo t;
  final double sigma, escala;

  @override
  Widget build(BuildContext context) {
    final lado = math.max(t.ancho, t.alto);
    return ClipRect(
      child: ImageFiltered(
        imageFilter: ui.ImageFilter.blur(sigmaX: sigma * t.k, sigmaY: sigma * t.k, tileMode: TileMode.clamp),
        child: Transform.scale(
          scale: escala,
          child: OverflowBox(
            maxWidth: lado,
            maxHeight: lado,
            child: MediaQuery(
              data: MediaQuery.of(context).copyWith(devicePixelRatio: 360 / lado),
              child: _caratula(t.d.caratula, lado, 0),
            ),
          ),
        ),
      ),
    );
  }
}

/// La firma discreta de Caudal: el logo y el nombre.
class _Marca extends StatelessWidget {
  const _Marca(this.k, {this.color = Colors.white});
  final double k;
  final Color color;

  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
        Image.asset('assets/logo/caudal.png', width: 15 * k, height: 15 * k, filterQuality: FilterQuality.medium),
        SizedBox(width: 5 * k),
        Text('Caudal',
            style: TextStyle(
                fontSize: 12 * k, fontWeight: FontWeight.w800, color: color, letterSpacing: 0.4 * k, height: 1)),
      ]);
}

/// La insignia de calidad, como en el reproductor («Opus · 138 kbps»).
class _Insignia extends StatelessWidget {
  const _Insignia(this.texto, this.color, this.k);
  final String texto;
  final Color color;
  final double k;

  @override
  Widget build(BuildContext context) => Container(
        padding: EdgeInsets.symmetric(horizontal: 7 * k, vertical: 2.5 * k),
        decoration: BoxDecoration(
          border: Border.all(color: color.withValues(alpha: 0.6), width: 1 * k),
          borderRadius: BorderRadius.circular(5 * k),
        ),
        child: Text(texto,
            maxLines: 1,
            style: TextStyle(fontSize: 10 * k, fontWeight: FontWeight.w700, color: color, letterSpacing: 0.4 * k, height: 1.1)),
      );
}

/// Un cuadro de la mascota en pixel art, ampliado sin suavizar (píxeles nítidos).
class MascotaPixel extends StatelessWidget {
  const MascotaPixel({super.key, required this.mascota, required this.hoja, required this.alto, this.cuadro = 0});
  final Mascota mascota;
  final ui.Image hoja;
  final double alto;
  final int cuadro;

  double get ancho => alto * mascota.ancho / mascota.alto;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: ancho,
        height: alto,
        child: CustomPaint(painter: _PintorMascota(mascota, hoja, cuadro)),
      );
}

class _PintorMascota extends CustomPainter {
  _PintorMascota(this.m, this.hoja, this.cuadro);
  final Mascota m;
  final ui.Image hoja;
  final int cuadro;

  @override
  void paint(Canvas canvas, Size size) {
    final fw = (m.ancho * m.densidad).toDouble(), fh = (m.alto * m.densidad).toDouble();
    final c = cuadro.clamp(0, math.max(0, m.cuadros - 1));
    canvas.drawImageRect(
      hoja,
      Rect.fromLTWH(c * fw, 0, fw, fh),
      Offset.zero & size,
      Paint()
        ..filterQuality = FilterQuality.none
        ..isAntiAlias = false,
    );
  }

  @override
  bool shouldRepaint(_PintorMascota o) => o.hoja != hoja || o.m != m || o.cuadro != cuadro;
}

/// La mascota de la tarjeta a [alto] (o nada si no se muestra).
MascotaPixel? _mascota(_Trazo t, double alto) {
  final m = t.d.mascota, h = t.d.hojaMascota;
  if (!t.mascota || m == null || h == null) return null;
  return MascotaPixel(mascota: m, hoja: h, alto: alto);
}

/// La barra de progreso con la mascota caminando encima (como en el reproductor) y los tiempos.
class _BarraProgreso extends StatelessWidget {
  const _BarraProgreso(this.t, {required this.color, required this.pista, this.tiempos = true, this.texto, this.grosor = 4});
  final _Trazo t;
  final Color color, pista;
  final Color? texto;
  final bool tiempos;
  final double grosor;

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final altoMascota = 40 * k;
    final m = _mascota(t, altoMascota);
    // con mascota se reserva su alto entero: nunca tapa el texto de arriba
    final reservado = m == null ? 14 * k : altoMascota + 8 * k;
    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      SizedBox(
        height: reservado,
        child: LayoutBuilder(builder: (context, c) {
          final w = c.maxWidth;
          final x = w * t.d.avance;
          final centro = reservado - 6 * k;
          return Stack(clipBehavior: Clip.none, children: [
            Positioned(
              left: 0,
              right: 0,
              top: centro - grosor * k / 2,
              height: grosor * k,
              child: DecoratedBox(decoration: BoxDecoration(color: pista, borderRadius: BorderRadius.circular(9 * k))),
            ),
            Positioned(
              left: 0,
              width: math.max(grosor * k, x),
              top: centro - grosor * k / 2,
              height: grosor * k,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(9 * k),
                  boxShadow: [BoxShadow(color: color.withValues(alpha: 0.55), blurRadius: 8 * k)],
                ),
              ),
            ),
            Positioned(
              left: x - 6.5 * k,
              top: centro - 6.5 * k,
              width: 13 * k,
              height: 13 * k,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                  boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.3), blurRadius: 4 * k)],
                ),
              ),
            ),
            if (m != null)
              Positioned(
                // los pies apoyados justo encima de la barra, sin salirse por los lados
                left: (x - m.ancho / 2).clamp(0.0, math.max(0.0, w - m.ancho)),
                top: centro - 2 * k - altoMascota,
                child: m,
              ),
          ]);
        }),
      ),
      if (tiempos) ...[
        SizedBox(height: 7 * k),
        Row(children: [
          Text(tiempoCompartir(t.d.posicion),
              style: TextStyle(fontSize: 11 * k, color: texto ?? Colors.white.withValues(alpha: 0.75), fontWeight: FontWeight.w600)),
          const Spacer(),
          Text(tiempoCompartir(t.d.duracion),
              style: TextStyle(fontSize: 11 * k, color: texto ?? Colors.white.withValues(alpha: 0.75), fontWeight: FontWeight.w600)),
        ]),
      ],
    ]);
  }
}

/// Los botones del reproductor, de adorno (como en la captura de pantalla).
class _Controles extends StatelessWidget {
  const _Controles(this.k, {required this.acento, this.escala = 1});
  final double k, escala;
  final Color acento;

  @override
  Widget build(BuildContext context) {
    final e = k * escala;
    const tinta = Colors.white;
    return Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
      Icon(Icons.shuffle_rounded, size: 22 * e, color: acento),
      Icon(Icons.skip_previous_rounded, size: 38 * e, color: tinta),
      Container(
        width: 60 * e,
        height: 60 * e,
        decoration: BoxDecoration(
          color: tinta,
          shape: BoxShape.circle,
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.3), blurRadius: 14 * e, offset: Offset(0, 5 * e))],
        ),
        child: Icon(Icons.pause_rounded, size: 36 * e, color: const Color(0xFF15121A)),
      ),
      Icon(Icons.skip_next_rounded, size: 38 * e, color: tinta),
      Icon(Icons.repeat_rounded, size: 22 * e, color: tinta.withValues(alpha: 0.85)),
    ]);
  }
}

/// La carátula con el borde de luz del reproductor: un degradado de los colores de la
/// carátula y un resplandor alrededor.
class _CaratulaBrillante extends StatelessWidget {
  const _CaratulaBrillante(this.t, {required this.lado});
  final _Trazo t;
  final double lado;

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final borde = 3.2 * k;
    final radio = lado * 0.065;
    return Container(
      width: lado,
      height: lado,
      padding: EdgeInsets.all(borde),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(radio),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [t.acento, Color.lerp(t.acento, Colors.white, 0.35)!, t.acento2, t.acento],
          stops: const [0, 0.35, 0.7, 1],
        ),
        boxShadow: [
          BoxShadow(color: t.acento.withValues(alpha: 0.55), blurRadius: 34 * k, spreadRadius: 2 * k),
          BoxShadow(color: Colors.black.withValues(alpha: 0.35), blurRadius: 26 * k, offset: Offset(0, 14 * k)),
        ],
      ),
      child: _caratula(t.d.caratula, lado - 2 * borde, radio - borde),
    );
  }
}

/// Título (y artista con la insignia) alineados a la izquierda.
class _Titulos extends StatelessWidget {
  const _Titulos(this.t, {this.tam = 1, this.insignia = true, this.lineas = 1});
  final _Trazo t;
  final double tam;
  final bool insignia;
  final int lineas;
  static const tinta = Colors.white;

  @override
  Widget build(BuildContext context) {
    final k = t.k * tam;
    final cal = t.d.calidad;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(t.d.titulo,
            maxLines: lineas,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.left,
            style: TextStyle(fontSize: 24 * k, fontWeight: FontWeight.w800, color: tinta, letterSpacing: -0.4 * k, height: 1.12)),
        SizedBox(height: 5 * k),
        Row(
          children: [
            Flexible(
              child: Text(t.d.artista,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 15 * k, color: tinta.withValues(alpha: 0.78), fontWeight: FontWeight.w500)),
            ),
            if (insignia && cal != null && cal.isNotEmpty) ...[
              SizedBox(width: 8 * k),
              _Insignia(cal, t.acento, k),
            ],
          ],
        ),
      ],
    );
  }
}

/// El verso que suena, en una tarjetita translúcida como la de la letra del reproductor.
class _TarjetaVerso extends StatelessWidget {
  const _TarjetaVerso(this.t);
  final _Trazo t;
  static const lineas = 2;

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final fondo = HSVColor.fromColor(t.p.fondo).withValue(0.62).withSaturation(0.55).toColor();
    return Container(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(16 * k, 11 * k, 16 * k, 13 * k),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16 * k),
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [fondo.withValues(alpha: 0.92), Color.lerp(fondo, Colors.black, 0.25)!.withValues(alpha: 0.92)],
        ),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.25), blurRadius: 18 * k, offset: Offset(0, 8 * k))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text('Letra', style: TextStyle(fontSize: 12 * k, fontWeight: FontWeight.w800, color: Colors.white.withValues(alpha: 0.85))),
        SizedBox(height: 5 * k),
        Text(t.d.verso!.trim(),
            maxLines: lineas,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 17 * k, fontWeight: FontWeight.w800, height: 1.22, letterSpacing: -0.2 * k)),
      ]),
    );
  }
}

// ---------------------------------------------------------------- Historia

/// Inspirada en la pantalla del reproductor: el degradado de la carátula, la carátula
/// grande con borde de luz, título, artista, la barra con la mascota y los botones.
class _Historia extends StatelessWidget {
  const _Historia(this.t);
  final _Trazo t;

  Widget _fondo() {
    final p = t.p;
    return Stack(fit: StackFit.expand, children: [
      DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color.lerp(p.fondo, Colors.black, 0.08)!,
              Color.lerp(p.fondo, p.contraste, 0.5)!,
              Color.lerp(p.contraste, Colors.black, 0.55)!,
            ],
          ),
        ),
      ),
      Opacity(opacity: 0.42, child: _FondoDifuminado(t, sigma: 46)),
      // el resplandor del color vivo detrás de la carátula
      Align(
        alignment: Alignment(0, t.cuadrado ? -0.6 : -0.42),
        child: Container(
          width: t.ancho * 1.25,
          height: t.ancho * 1.25,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [t.acento.withValues(alpha: 0.32), t.acento.withValues(alpha: 0)]),
          ),
        ),
      ),
      // abajo se oscurece para que se lea todo
      DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.black.withValues(alpha: 0.05), Colors.black.withValues(alpha: 0), Colors.black.withValues(alpha: 0.32)],
            stops: const [0, 0.45, 1],
          ),
        ),
      ),
    ]);
  }

  Widget _cabecera() {
    final k = t.k;
    final ctx = (t.d.contexto ?? '').trim();
    return Column(mainAxisSize: MainAxisSize.min, children: [
      Text(ctx.isEmpty ? 'ESCUCHANDO AHORA' : 'REPRODUCIENDO DESDE',
          style: TextStyle(fontSize: 9.5 * k, letterSpacing: 2.2 * k, color: Colors.white.withValues(alpha: 0.72), fontWeight: FontWeight.w600)),
      if (ctx.isNotEmpty) ...[
        SizedBox(height: 4 * k),
        Text(ctx,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 13 * k, fontWeight: FontWeight.w700, letterSpacing: 0.3 * k)),
      ],
    ]);
  }

  Widget _filaTitulo() => Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
        Expanded(child: _Titulos(t)),
        SizedBox(width: 10 * t.k),
        Icon(Icons.favorite_rounded, size: 28 * t.k, color: t.acento),
      ]);

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    if (t.cuadrado) {
      return Stack(fit: StackFit.expand, children: [
        _fondo(),
        Padding(
          padding: EdgeInsets.fromLTRB(24 * k, 24 * k, 24 * k, 16 * k),
          child: Column(children: [
            Row(children: [
              _CaratulaBrillante(t, lado: 128 * k),
              SizedBox(width: 18 * k),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('ESCUCHANDO AHORA',
                      style: TextStyle(fontSize: 9 * k, letterSpacing: 2 * k, color: Colors.white.withValues(alpha: 0.72), fontWeight: FontWeight.w600)),
                  SizedBox(height: 8 * k),
                  _Titulos(t, tam: 0.92, lineas: 2),
                ]),
              ),
            ]),
            const Spacer(),
            if (t.letra) ...[
              Text('“${t.d.verso!.trim()}”',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 15 * k, fontWeight: FontWeight.w700, color: Colors.white.withValues(alpha: 0.92), height: 1.25)),
              const Spacer(),
            ],
            _BarraProgreso(t, color: t.acento, pista: Colors.white.withValues(alpha: 0.22)),
            SizedBox(height: 4 * k),
            _Controles(k, acento: t.acento, escala: t.letra ? 0.68 : 0.8),
            SizedBox(height: 10 * k),
            _Marca(k, color: Colors.white.withValues(alpha: 0.85)),
          ]),
        ),
      ]);
    }
    return Stack(fit: StackFit.expand, children: [
      _fondo(),
      Padding(
        padding: EdgeInsets.fromLTRB(26 * k, 30 * k, 26 * k, 20 * k),
        child: Column(children: [
          _cabecera(),
          SizedBox(height: 20 * k),
          // la carátula toma lo que sobra (y nunca más que el ancho)
          Expanded(
            child: Center(
              child: AspectRatio(
                aspectRatio: 1,
                child: LayoutBuilder(builder: (_, c) => _CaratulaBrillante(t, lado: c.maxWidth)),
              ),
            ),
          ),
          SizedBox(height: 24 * k),
          _filaTitulo(),
          SizedBox(height: t.mascota ? 2 * k : 12 * k),
          _BarraProgreso(t, color: Colors.white, pista: Colors.white.withValues(alpha: 0.24)),
          SizedBox(height: 10 * k),
          if (t.letra) ...[
            _Controles(k, acento: t.acento, escala: 0.78),
            SizedBox(height: 14 * k),
            _TarjetaVerso(t),
          ] else
            _Controles(k, acento: t.acento),
          SizedBox(height: 16 * k),
          _Marca(k, color: Colors.white.withValues(alpha: 0.85)),
        ]),
      ),
    ]);
  }
}

// ---------------------------------------------------------------- Vinilo

/// La carátula como funda de disco, con el vinilo asomando por un lado y la carátula
/// en su etiqueta.
class _Vinilo extends StatelessWidget {
  const _Vinilo(this.t);
  final _Trazo t;

  Widget _conjunto(double funda) {
    final k = t.k;
    final disco = funda * 0.94;
    final asoma = disco * 0.46;
    final m = _mascota(t, 42 * k);
    return SizedBox(
      width: funda + asoma,
      height: funda,
      child: Stack(clipBehavior: Clip.none, children: [
        // el disco, detrás de la funda
        Positioned(
          left: funda + asoma - disco,
          top: (funda - disco) / 2,
          width: disco,
          height: disco,
          child: Stack(fit: StackFit.expand, children: [
            DecoratedBox(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.5), blurRadius: 24 * k, offset: Offset(0, 10 * k))],
              ),
            ),
            CustomPaint(painter: _PintorDisco(t.acento)),
            Center(child: _caratula(t.d.caratula, disco * 0.36, 0, circulo: true)),
            Center(
              child: Container(
                width: disco * 0.36,
                height: disco * 0.36,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.black.withValues(alpha: 0.55), width: disco * 0.008),
                ),
              ),
            ),
            Center(
              child: Container(
                width: disco * 0.035,
                height: disco * 0.035,
                decoration: const BoxDecoration(color: Color(0xFF0B0B0E), shape: BoxShape.circle),
              ),
            ),
          ]),
        ),
        // la funda (la carátula), con un brillo de cartón
        Positioned(
          left: 0,
          top: 0,
          width: funda,
          height: funda,
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(5 * k),
              boxShadow: [
                BoxShadow(color: Colors.black.withValues(alpha: 0.55), blurRadius: 26 * k, offset: Offset(8 * k, 14 * k)),
              ],
            ),
            child: Stack(fit: StackFit.expand, children: [
              _caratula(t.d.caratula, funda, 5 * k),
              ClipRRect(
                borderRadius: BorderRadius.circular(5 * k),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Colors.white.withValues(alpha: 0.16), Colors.white.withValues(alpha: 0), Colors.black.withValues(alpha: 0.14)],
                      stops: const [0, 0.45, 1],
                    ),
                  ),
                ),
              ),
            ]),
          ),
        ),
        // la mascota, sentada encima de la funda
        if (m != null) Positioned(left: funda * 0.1, top: -m.alto + 3 * k, child: m),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final p = t.p;
    final fondo = Stack(fit: StackFit.expand, children: [
      DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color.lerp(p.fondo, Colors.black, 0.45)!, Color.lerp(p.contraste, Colors.black, 0.78)!],
          ),
        ),
      ),
      Align(
        alignment: const Alignment(0.3, -0.25),
        child: Container(
          width: t.ancho * 1.3,
          height: t.ancho * 1.3,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [t.acento.withValues(alpha: 0.26), t.acento.withValues(alpha: 0)]),
          ),
        ),
      ),
      CustomPaint(painter: _PintorGrano(k)),
    ]);
    final titulos = Column(mainAxisSize: MainAxisSize.min, children: [
      Text(t.d.titulo,
          maxLines: 2,
          textAlign: TextAlign.center,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: (t.cuadrado ? 22 : 28) * k, fontWeight: FontWeight.w900, letterSpacing: -0.5 * k, height: 1.08)),
      SizedBox(height: 6 * k),
      Text(t.d.artista.toUpperCase(),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 12 * k, letterSpacing: 3 * k, color: t.acento, fontWeight: FontWeight.w700)),
    ]);
    return Stack(fit: StackFit.expand, children: [
      fondo,
      Padding(
        padding: EdgeInsets.fromLTRB(26 * k, (t.cuadrado ? 20 : 34) * k, 26 * k, (t.cuadrado ? 16 : 24) * k),
        child: Column(children: [
          if (!t.cuadrado) ...[
            Text('EN MI TOCADISCOS',
                style: TextStyle(fontSize: 9.5 * k, letterSpacing: 2.6 * k, color: Colors.white.withValues(alpha: 0.6), fontWeight: FontWeight.w600)),
            SizedBox(height: 10 * k),
          ],
          Expanded(
            child: LayoutBuilder(builder: (_, c) {
              final reservaMascota = t.mascota ? 38 * k : 0.0;
              final funda = math.min(c.maxWidth / 1.43, c.maxHeight - reservaMascota - 8 * k).clamp(40.0, 4000.0);
              return Padding(
                padding: EdgeInsets.only(top: reservaMascota),
                child: Center(child: _conjunto(funda * (t.cuadrado ? 1 : 0.98))),
              );
            }),
          ),
          SizedBox(height: (t.cuadrado ? 12 : 26) * k),
          titulos,
          if (t.letra && !t.cuadrado) ...[
            SizedBox(height: 16 * k),
            Text('“${t.d.verso!.trim()}”',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 15 * k, fontStyle: FontStyle.italic, color: Colors.white.withValues(alpha: 0.85), height: 1.3)),
          ],
          SizedBox(height: (t.cuadrado ? 10 : 22) * k),
          Row(children: [
            Text(tiempoCompartir(t.d.posicion), style: TextStyle(fontSize: 11 * k, color: Colors.white.withValues(alpha: 0.7))),
            SizedBox(width: 10 * k),
            Expanded(
              child: Container(
                height: 3 * k,
                alignment: Alignment.centerLeft,
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(3 * k)),
                child: FractionallySizedBox(
                  widthFactor: math.max(0.01, t.d.avance),
                  child: DecoratedBox(
                    decoration: BoxDecoration(color: t.acento, borderRadius: BorderRadius.circular(3 * k)),
                  ),
                ),
              ),
            ),
            SizedBox(width: 10 * k),
            Text(tiempoCompartir(t.d.duracion), style: TextStyle(fontSize: 11 * k, color: Colors.white.withValues(alpha: 0.7))),
          ]),
          SizedBox(height: (t.cuadrado ? 10 : 18) * k),
          _Marca(k, color: Colors.white.withValues(alpha: 0.8)),
        ]),
      ),
    ]);
  }
}

/// Un vinilo negro con surcos y dos reflejos de luz.
class _PintorDisco extends CustomPainter {
  _PintorDisco(this.acento);
  final Color acento;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2;
    canvas.drawCircle(
      c,
      r,
      Paint()
        ..shader = const RadialGradient(colors: [Color(0xFF1C1C21), Color(0xFF0A0A0D)]).createShader(Rect.fromCircle(center: c, radius: r)),
    );
    final surco = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = math.max(0.5, r * 0.004);
    for (var i = 0; i <= 44; i++) {
      final rr = r * (0.4 + 0.57 * i / 44);
      surco.color = Colors.white.withValues(alpha: i % 6 == 0 ? 0.07 : 0.035);
      canvas.drawCircle(c, rr, surco);
    }
    // los reflejos: dos abanicos de luz enfrentados
    canvas.drawCircle(
      c,
      r * 0.98,
      Paint()
        ..shader = SweepGradient(
          colors: [
            Colors.white.withValues(alpha: 0),
            Colors.white.withValues(alpha: 0.16),
            Colors.white.withValues(alpha: 0),
            Colors.white.withValues(alpha: 0),
            Colors.white.withValues(alpha: 0.12),
            Colors.white.withValues(alpha: 0),
            Colors.white.withValues(alpha: 0),
          ],
          stops: const [0.02, 0.1, 0.2, 0.52, 0.6, 0.7, 1],
        ).createShader(Rect.fromCircle(center: c, radius: r)),
    );
    // un aro del color de la carátula alrededor de la etiqueta
    canvas.drawCircle(
      c,
      r * 0.39,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = r * 0.012
        ..color = acento.withValues(alpha: 0.75),
    );
    canvas.drawCircle(
      c,
      r * 0.995,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = r * 0.01
        ..color = Colors.white.withValues(alpha: 0.08),
    );
  }

  @override
  bool shouldRepaint(_PintorDisco o) => o.acento != acento;
}

/// Un grano muy suave, como de papel fotográfico (siempre el mismo: semilla fija).
class _PintorGrano extends CustomPainter {
  _PintorGrano(this.k);
  final double k;

  @override
  void paint(Canvas canvas, Size size) {
    final azar = math.Random(7);
    final p = Paint();
    final n = (size.width * size.height / (90 * k * k)).clamp(0, 3000).toInt();
    for (var i = 0; i < n; i++) {
      p.color = (azar.nextBool() ? Colors.white : Colors.black).withValues(alpha: 0.035);
      canvas.drawCircle(Offset(azar.nextDouble() * size.width, azar.nextDouble() * size.height), 0.7 * k, p);
    }
  }

  @override
  bool shouldRepaint(_PintorGrano o) => o.k != k;
}

// ---------------------------------------------------------------- Letra

/// El verso que suena en grande sobre la carátula difuminada, con la carátula pequeña abajo.
class _Letra extends StatelessWidget {
  const _Letra(this.t);
  final _Trazo t;

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final verso = (t.d.verso ?? t.d.titulo).trim();
    final siguiente = (t.d.versoSiguiente ?? '').trim();
    final ancho = t.ancho - 60 * k;
    final m = _mascota(t, 40 * k);
    return Stack(fit: StackFit.expand, children: [
      ColoredBox(color: Color.lerp(t.p.fondo, Colors.black, 0.6)!),
      _FondoDifuminado(t, sigma: 30, escala: 1.6),
      DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color.lerp(t.p.fondo, Colors.black, 0.35)!.withValues(alpha: 0.55),
              Color.lerp(t.p.contraste, Colors.black, 0.6)!.withValues(alpha: 0.82),
            ],
          ),
        ),
      ),
      Padding(
        padding: EdgeInsets.fromLTRB(30 * k, (t.cuadrado ? 24 : 36) * k, 30 * k, (t.cuadrado ? 20 : 30) * k),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            _Marca(k, color: Colors.white.withValues(alpha: 0.85)),
            const Spacer(),
            Container(
              padding: EdgeInsets.symmetric(horizontal: 9 * k, vertical: 4 * k),
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20 * k)),
              child: Text('Letra', style: TextStyle(fontSize: 11 * k, fontWeight: FontWeight.w800)),
            ),
          ]),
          const Spacer(),
          Text('“',
              style: TextStyle(fontSize: (t.cuadrado ? 64 : 92) * k, height: 0.9, fontWeight: FontWeight.w900, color: t.acento)),
          Flexible(
            flex: 8,
            child: Align(
              alignment: Alignment.centerLeft,
              child: FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: SizedBox(
                  width: ancho,
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                    Text(verso,
                        style: TextStyle(
                          fontSize: (t.cuadrado ? 30 : 42) * k,
                          fontWeight: FontWeight.w900,
                          height: 1.13,
                          letterSpacing: -0.6 * k,
                          shadows: [Shadow(color: t.acento.withValues(alpha: 0.45), blurRadius: 22 * k)],
                        )),
                    if (siguiente.isNotEmpty) ...[
                      SizedBox(height: 14 * k),
                      Text(siguiente,
                          style: TextStyle(
                              fontSize: (t.cuadrado ? 18 : 25) * k,
                              fontWeight: FontWeight.w800,
                              height: 1.18,
                              color: Colors.white.withValues(alpha: 0.42))),
                    ],
                  ]),
                ),
              ),
            ),
          ),
          const Spacer(),
          Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10 * k),
                boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.45), blurRadius: 16 * k, offset: Offset(0, 6 * k))],
              ),
              child: _caratula(t.d.caratula, 58 * k, 10 * k),
            ),
            SizedBox(width: 14 * k),
            Expanded(child: _Titulos(t, tam: 0.7, insignia: false)),
            if (m != null) ...[SizedBox(width: 8 * k), m],
          ]),
          SizedBox(height: 16 * k),
          Container(
            height: 3 * k,
            alignment: Alignment.centerLeft,
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(3 * k)),
            child: FractionallySizedBox(
              widthFactor: math.max(0.01, t.d.avance),
              child: DecoratedBox(decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(3 * k))),
            ),
          ),
        ]),
      ),
    ]);
  }
}

// ---------------------------------------------------------------- Polaroid

/// Una foto instantánea inclinada con cinta de color, sobre un fondo pastel de la carátula.
class _Polaroid extends StatelessWidget {
  const _Polaroid(this.t);
  final _Trazo t;

  static const _tinta = Color(0xFF2A2321);

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final p = t.p;
    final claro1 = Color.lerp(p.fondo, Colors.white, 0.8)!;
    final claro2 = Color.lerp(p.contraste, Colors.white, 0.66)!;
    final m = _mascota(t, 44 * k);
    return Stack(fit: StackFit.expand, children: [
      DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [claro1, claro2]),
        ),
      ),
      Align(
        alignment: const Alignment(-1, -1),
        child: Container(
          width: t.ancho,
          height: t.ancho,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [t.acento.withValues(alpha: 0.28), t.acento.withValues(alpha: 0)]),
          ),
        ),
      ),
      CustomPaint(painter: _PintorPuntos(k, Color.lerp(p.fondo, Colors.black, 0.2)!.withValues(alpha: 0.12))),
      Padding(
        padding: EdgeInsets.fromLTRB(24 * k, (t.cuadrado ? 14 : 40) * k, 24 * k, (t.cuadrado ? 14 : 26) * k),
        child: Column(children: [
          if (!t.cuadrado)
            Text('escuchando ahora',
                style: TextStyle(fontSize: 13 * k, letterSpacing: 1.6 * k, color: _tinta.withValues(alpha: 0.6), fontWeight: FontWeight.w600)),
          Expanded(
            child: LayoutBuilder(builder: (_, c) {
              // la foto: el cuadro de la carátula más el margen de abajo (el de escribir)
              final pie = 70 * k;
              final reservaArriba = m != null ? 30 * k : 14 * k;
              final ancho = math.min(c.maxWidth * (t.cuadrado ? 0.92 : 0.84), c.maxHeight - pie - reservaArriba + 13 * k - 4 * k);
              final foto = ancho - 26 * k;
              return Padding(
                padding: EdgeInsets.only(top: reservaArriba),
                child: Center(
                  child: Transform.rotate(
                    angle: -0.045,
                    child: Stack(clipBehavior: Clip.none, children: [
                      Container(
                        width: ancho,
                        padding: EdgeInsets.fromLTRB(13 * k, 13 * k, 13 * k, 0),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFDFCF8),
                          borderRadius: BorderRadius.circular(2 * k),
                          boxShadow: [
                            BoxShadow(color: Colors.black.withValues(alpha: 0.2), blurRadius: 22 * k, offset: Offset(0, 12 * k)),
                            BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 3 * k, offset: Offset(0, 1 * k)),
                          ],
                        ),
                        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _caratula(t.d.caratula, foto, 1 * k),
                          SizedBox(
                            height: pie,
                            child: Padding(
                              padding: EdgeInsets.fromLTRB(4 * k, 10 * k, 4 * k, 8 * k),
                              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Expanded(
                                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                    Text(t.d.titulo,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(fontSize: 20 * k, fontWeight: FontWeight.w800, color: _tinta, letterSpacing: -0.3 * k)),
                                    SizedBox(height: 3 * k),
                                    Text(t.d.artista,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(fontSize: 13.5 * k, fontStyle: FontStyle.italic, color: _tinta.withValues(alpha: 0.62))),
                                  ]),
                                ),
                                SizedBox(width: 8 * k),
                                Padding(
                                  padding: EdgeInsets.only(top: 4 * k),
                                  child: Icon(Icons.favorite_rounded, size: 20 * k, color: Color.lerp(t.acento, Colors.black, 0.08)),
                                ),
                              ]),
                            ),
                          ),
                        ]),
                      ),
                      // la cinta adhesiva arriba
                      Positioned(
                        top: -12 * k,
                        left: ancho / 2 - 46 * k,
                        child: Transform.rotate(
                          angle: 0.07,
                          child: Container(
                            width: 92 * k,
                            height: 26 * k,
                            decoration: BoxDecoration(
                              color: Color.lerp(t.acento, Colors.white, 0.35)!.withValues(alpha: 0.72),
                              boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 2 * k)],
                            ),
                          ),
                        ),
                      ),
                      // la mascota, asomada en la esquina de la foto
                      if (m != null) Positioned(top: -m.alto + 2 * k, right: 16 * k, child: m),
                    ]),
                  ),
                ),
              );
            }),
          ),
          if (t.letra) ...[
            SizedBox(height: (t.cuadrado ? 8 : 18) * k),
            Text('“${t.d.verso!.trim()}”',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: (t.cuadrado ? 13 : 16) * k, fontStyle: FontStyle.italic, fontWeight: FontWeight.w600, color: _tinta.withValues(alpha: 0.82), height: 1.3)),
          ],
          SizedBox(height: (t.cuadrado ? 8 : 18) * k),
          if (!t.cuadrado || !t.letra) ...[
            Text('${tiempoCompartir(t.d.posicion)} / ${tiempoCompartir(t.d.duracion)}',
                style: TextStyle(fontSize: 11 * k, color: _tinta.withValues(alpha: 0.55), letterSpacing: 1 * k, fontWeight: FontWeight.w600)),
            SizedBox(height: (t.cuadrado ? 6 : 12) * k),
          ],
          _Marca(k, color: _tinta.withValues(alpha: 0.72)),
        ]),
      ),
    ]);
  }
}

/// Puntitos regulares de fondo (como un papel punteado).
class _PintorPuntos extends CustomPainter {
  _PintorPuntos(this.k, this.color);
  final double k;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()..color = color;
    final paso = 18 * k;
    for (var y = paso / 2; y < size.height; y += paso) {
      for (var x = paso / 2; x < size.width; x += paso) {
        canvas.drawCircle(Offset(x, y), 1.1 * k, p);
      }
    }
  }

  @override
  bool shouldRepaint(_PintorPuntos o) => o.k != k || o.color != color;
}

// ---------------------------------------------------------------- Cristal

/// La carátula ampliada y difuminada, y encima una tarjeta de vidrio esmerilado con todo.
class _Cristal extends StatelessWidget {
  const _Cristal(this.t);
  final _Trazo t;

  Widget _vidrio({required Widget child, required EdgeInsets relleno}) {
    final k = t.k;
    return ClipRRect(
      borderRadius: BorderRadius.circular(30 * k),
      child: BackdropFilter(
        filter: ui.ImageFilter.blur(sigmaX: 16 * k, sigmaY: 16 * k),
        child: Container(
          padding: relleno,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(30 * k),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Colors.white.withValues(alpha: 0.26), Colors.white.withValues(alpha: 0.08)],
            ),
            border: Border.all(color: Colors.white.withValues(alpha: 0.38), width: 1.2 * k),
          ),
          child: child,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final fondo = Stack(fit: StackFit.expand, children: [
      ColoredBox(color: Color.lerp(t.p.fondo, Colors.black, 0.5)!),
      _FondoDifuminado(t, sigma: 22, escala: 1.7),
      ColoredBox(color: Colors.black.withValues(alpha: 0.18)),
      DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [t.p.fondo.withValues(alpha: 0), Color.lerp(t.p.contraste, Colors.black, 0.4)!.withValues(alpha: 0.45)],
          ),
        ),
      ),
    ]);
    if (t.cuadrado) {
      return Stack(fit: StackFit.expand, children: [
        fondo,
        Padding(
          padding: EdgeInsets.all(24 * k),
          child: Column(children: [
            const Spacer(),
            _vidrio(
              relleno: EdgeInsets.fromLTRB(18 * k, 18 * k, 18 * k, 14 * k),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Row(children: [
                  Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(14 * k),
                      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.3), blurRadius: 16 * k, offset: Offset(0, 6 * k))],
                    ),
                    child: _caratula(t.d.caratula, 104 * k, 14 * k),
                  ),
                  SizedBox(width: 16 * k),
                  Expanded(child: _Titulos(t, tam: 0.82, lineas: 2)),
                ]),
                if (t.letra) ...[
                  SizedBox(height: 12 * k),
                  Text(t.d.verso!.trim(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 14 * k, fontStyle: FontStyle.italic, fontWeight: FontWeight.w600, color: Colors.white.withValues(alpha: 0.9))),
                ],
                SizedBox(height: t.mascota ? 4 * k : 14 * k),
                _BarraProgreso(t, color: Colors.white, pista: Colors.white.withValues(alpha: 0.28)),
              ]),
            ),
            const Spacer(),
            _Marca(k, color: Colors.white.withValues(alpha: 0.88)),
          ]),
        ),
      ]);
    }
    return Stack(fit: StackFit.expand, children: [
      fondo,
      Padding(
        padding: EdgeInsets.fromLTRB(24 * k, 30 * k, 24 * k, 22 * k),
        child: Column(children: [
          const Spacer(),
          Flexible(
            flex: 20,
            child: _vidrio(
              relleno: EdgeInsets.fromLTRB(20 * k, 20 * k, 20 * k, 16 * k),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Flexible(
                  child: AspectRatio(
                    aspectRatio: 1,
                    child: LayoutBuilder(
                      builder: (_, c) => Container(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(20 * k),
                          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.35), blurRadius: 24 * k, offset: Offset(0, 10 * k))],
                        ),
                        child: _caratula(t.d.caratula, c.maxWidth, 20 * k),
                      ),
                    ),
                  ),
                ),
                SizedBox(height: 18 * k),
                _Titulos(t, tam: 0.92),
                if (t.letra) ...[
                  SizedBox(height: 10 * k),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text('“${t.d.verso!.trim()}”',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 14 * k, fontStyle: FontStyle.italic, fontWeight: FontWeight.w600, color: Colors.white.withValues(alpha: 0.9), height: 1.25)),
                  ),
                ],
                SizedBox(height: t.mascota ? 2 * k : 12 * k),
                _BarraProgreso(t, color: Colors.white, pista: Colors.white.withValues(alpha: 0.28)),
                SizedBox(height: 8 * k),
                _Controles(k, acento: t.acento, escala: 0.74),
              ]),
            ),
          ),
          const Spacer(),
          _Marca(k, color: Colors.white.withValues(alpha: 0.88)),
        ]),
      ),
    ]);
  }
}

// ---------------------------------------------------------------- Recibo

/// Un recibo de papel con la canción, el momento, la calidad y un código de barras.
class _Recibo extends StatelessWidget {
  const _Recibo(this.t);
  final _Trazo t;

  static const _papel = Color(0xFFF8F5EE);
  static const _tinta = Color(0xFF1F1C1A);

  static const _meses = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];

  Widget _fila(String a, String b, double k, {bool fuerte = false}) => Padding(
        padding: EdgeInsets.symmetric(vertical: 3 * k),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(a, style: TextStyle(fontSize: 11 * k, letterSpacing: 1.2 * k, color: _tinta.withValues(alpha: 0.6), fontWeight: FontWeight.w600)),
          SizedBox(width: 14 * k),
          Expanded(
            child: Text(b,
                textAlign: TextAlign.right,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 12 * k, color: _tinta, fontWeight: fuerte ? FontWeight.w800 : FontWeight.w600, letterSpacing: 0.4 * k)),
          ),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final p = t.p;
    final f = t.d.fecha ?? DateTime.now();
    final fecha = '${f.day.toString().padLeft(2, '0')} ${_meses[f.month - 1]} ${f.year} · '
        '${f.hour.toString().padLeft(2, '0')}:${f.minute.toString().padLeft(2, '0')}';
    final ctx = (t.d.contexto ?? '').trim();
    final cal = (t.d.calidad ?? '').trim();
    final m = _mascota(t, 40 * k);
    const anchoRecibo = 270.0;
    final recibo = PhysicalShape(
      clipper: _Dientes(7 * k),
      color: _papel,
      elevation: 10 * k,
      shadowColor: Colors.black.withValues(alpha: 0.5),
      child: SizedBox(
        width: anchoRecibo * k,
        child: Padding(
          padding: EdgeInsets.fromLTRB(20 * k, 26 * k, 20 * k, 24 * k),
          child: DefaultTextStyle.merge(
            style: const TextStyle(color: _tinta),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                Image.asset('assets/logo/caudal.png', width: 22 * k, height: 22 * k),
                SizedBox(width: 7 * k),
                Text('CAUDAL', style: TextStyle(fontSize: 19 * k, fontWeight: FontWeight.w900, letterSpacing: 5 * k, color: _tinta)),
              ]),
              SizedBox(height: 6 * k),
              Text('RECIBO DE ESCUCHA', style: TextStyle(fontSize: 9.5 * k, letterSpacing: 2.4 * k, color: _tinta.withValues(alpha: 0.6))),
              SizedBox(height: 3 * k),
              Text(fecha, style: TextStyle(fontSize: 10 * k, letterSpacing: 1 * k, color: _tinta.withValues(alpha: 0.6))),
              _Rayas(k),
              Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
                _caratula(t.d.caratula, 54 * k, 3 * k),
                SizedBox(width: 12 * k),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(t.d.titulo.toUpperCase(),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 14 * k, fontWeight: FontWeight.w900, letterSpacing: 0.6 * k, height: 1.15, color: _tinta)),
                    SizedBox(height: 3 * k),
                    Text(t.d.artista,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12 * k, color: _tinta.withValues(alpha: 0.7))),
                  ]),
                ),
              ]),
              _Rayas(k),
              _fila('AVANCE', '${tiempoCompartir(t.d.posicion)} / ${tiempoCompartir(t.d.duracion)}', k),
              if (cal.isNotEmpty) _fila('CALIDAD', cal, k),
              if (ctx.isNotEmpty) _fila('DESDE', ctx, k),
              _fila('ESTADO', 'EN BUCLE', k),
              if (t.letra) ...[
                _Rayas(k),
                Text('“${t.d.verso!.trim()}”',
                    textAlign: TextAlign.center,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 13 * k, fontStyle: FontStyle.italic, fontWeight: FontWeight.w600, height: 1.3, color: _tinta)),
              ],
              _Rayas(k),
              _fila('TOTAL', '1 CANCIÓN', k, fuerte: true),
              SizedBox(height: 12 * k),
              SizedBox(height: 42 * k, width: double.infinity, child: CustomPaint(painter: _PintorBarras('${t.d.titulo}|${t.d.artista}', _tinta))),
              SizedBox(height: 10 * k),
              Text('¡GRACIAS POR ESCUCHAR!', style: TextStyle(fontSize: 10 * k, letterSpacing: 2.4 * k, fontWeight: FontWeight.w700, color: _tinta)),
            ]),
          ),
        ),
      ),
    );
    return Stack(fit: StackFit.expand, children: [
      DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color.lerp(p.fondo, t.acento, 0.25)!, Color.lerp(p.contraste, Colors.black, 0.35)!],
          ),
        ),
      ),
      CustomPaint(painter: _PintorPuntos(k, Colors.white.withValues(alpha: 0.08))),
      Padding(
        padding: EdgeInsets.fromLTRB(20 * k, (t.cuadrado ? 14 : 30) * k, 20 * k, (t.cuadrado ? 14 : 30) * k),
        child: Center(
          child: FittedBox(
            fit: BoxFit.scaleDown,
            // con mascota se deja su alto arriba: si no, el ajuste de tamaño la cortaría
            child: Padding(
              padding: EdgeInsets.only(top: m == null ? 0 : m.alto),
              child: Stack(clipBehavior: Clip.none, children: [
                Transform.rotate(angle: 0.025, child: recibo),
                if (m != null) Positioned(right: 18 * k, top: -m.alto + 6 * k, child: m),
              ]),
            ),
          ),
        ),
      ),
    ]);
  }
}

/// Una línea de guiones, como las de un ticket.
class _Rayas extends StatelessWidget {
  const _Rayas(this.k);
  final double k;

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.symmetric(vertical: 12 * k),
        child: SizedBox(height: 1.4 * k, width: double.infinity, child: CustomPaint(painter: _PintorGuiones(k))),
      );
}

class _PintorGuiones extends CustomPainter {
  _PintorGuiones(this.k);
  final double k;

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()..color = const Color(0xFF1F1C1A).withValues(alpha: 0.45);
    for (var x = 0.0; x < size.width; x += 7 * k) {
      canvas.drawRect(Rect.fromLTWH(x, 0, math.min(4 * k, size.width - x), size.height), p);
    }
  }

  @override
  bool shouldRepaint(_PintorGuiones o) => o.k != k;
}

/// El borde dentado de arriba y de abajo del papel.
class _Dientes extends CustomClipper<Path> {
  _Dientes(this.diente);
  final double diente;

  @override
  Path getClip(Size size) {
    final n = math.max(1, (size.width / (diente * 2)).round());
    final paso = size.width / n;
    final p = Path()..moveTo(0, diente);
    for (var i = 0; i < n; i++) {
      p.lineTo(i * paso + paso / 2, 0);
      p.lineTo((i + 1) * paso, diente);
    }
    p.lineTo(size.width, size.height - diente);
    for (var i = n; i > 0; i--) {
      p.lineTo(i * paso - paso / 2, size.height);
      p.lineTo((i - 1) * paso, size.height - diente);
    }
    return p..close();
  }

  @override
  bool shouldReclip(_Dientes o) => o.diente != diente;
}

/// Un código de barras de adorno, siempre el mismo para la misma canción.
class _PintorBarras extends CustomPainter {
  _PintorBarras(this.semilla, this.color);
  final String semilla;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    var h = 17;
    for (final c in semilla.codeUnits) {
      h = (h * 31 + c) & 0x7fffffff;
    }
    final azar = math.Random(h);
    final anchos = <double>[];
    var total = 0.0;
    while (total < size.width) {
      final w = 1.0 + azar.nextInt(4);
      anchos.add(w);
      total += w;
    }
    final escala = size.width / total;
    final p = Paint()..color = color;
    var x = 0.0;
    for (var i = 0; i < anchos.length; i++) {
      final w = anchos[i] * escala;
      if (i.isEven) canvas.drawRect(Rect.fromLTWH(x, 0, w, size.height), p);
      x += w;
    }
  }

  @override
  bool shouldRepaint(_PintorBarras o) => o.semilla != semilla || o.color != color;
}


// ================================================================ exclusivos de donadores

/// Desliza un degradado a lo ancho (con [TileMode.mirror] el brillo va y vuelve sin cortes).
class _Desliza extends GradientTransform {
  const _Desliza(this.d);
  final double d;

  @override
  Matrix4? transform(Rect bounds, {TextDirection? textDirection}) =>
      Matrix4.translationValues(bounds.width * d, bounds.height * d * 0.5, 0);
}

/// Pinta [child] (un texto, un icono) con un degradado.
Widget _conDegradado(Gradient g, Widget child) => ShaderMask(
      blendMode: BlendMode.srcIn,
      shaderCallback: (r) => g.createShader(r),
      child: child,
    );

const _arcoiris = [
  Color(0xFFFF7AD9),
  Color(0xFF9D7AFF),
  Color(0xFF7AE7FF),
  Color(0xFF8CFFB4),
  Color(0xFFFFF27A),
  Color(0xFFFFA77A),
  Color(0xFFFF7AD9),
];

LinearGradient _oroBrillante(double fase, {Alignment begin = Alignment.topLeft, Alignment end = Alignment.bottomRight}) =>
    LinearGradient(
      begin: begin,
      end: end,
      colors: const [
        Color(0xFF8A6424),
        Color(0xFFE9C46A),
        Color(0xFFFFF4C8),
        Color(0xFFC8962F),
        Color(0xFF7A5519),
        Color(0xFFF3D98B),
      ],
      stops: const [0, 0.22, 0.38, 0.55, 0.78, 1],
      tileMode: TileMode.mirror,
      transform: _Desliza(fase * 2 - 1),
    );

/// El sello dorado: «DONADOR» o «FUNDADOR».
class _Sello extends StatelessWidget {
  const _Sello(this.t);
  final _Trazo t;

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final fundador = t.d.sello.toLowerCase().contains('fundador');
    const tinta = Color(0xFF3B2608);
    return Container(
      padding: EdgeInsets.fromLTRB(9 * k, 5 * k, 11 * k, 5 * k),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(30 * k),
        gradient: _oroBrillante(t.fase, begin: Alignment.centerLeft, end: Alignment.centerRight),
        border: Border.all(color: const Color(0xFFFFF4C8).withValues(alpha: 0.9), width: 0.8 * k),
        boxShadow: [BoxShadow(color: const Color(0xFFE9C46A).withValues(alpha: 0.45), blurRadius: 14 * k)],
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(fundador ? Icons.diamond_rounded : Icons.workspace_premium_rounded, size: 13 * k, color: tinta),
        SizedBox(width: 5 * k),
        Text(fundador ? 'FUNDADOR' : 'DONADOR',
            style: TextStyle(fontSize: 10 * k, fontWeight: FontWeight.w900, letterSpacing: 1.8 * k, color: tinta, height: 1.1)),
      ]),
    );
  }
}

/// Un verso entre comillas, en cursiva.
Widget _versoExclusivo(_Trazo t, Color color, {int lineas = 2}) => Text('“${t.d.verso!.trim()}”',
    maxLines: lineas,
    overflow: TextOverflow.ellipsis,
    textAlign: TextAlign.center,
    style: TextStyle(fontSize: 15 * t.k, fontStyle: FontStyle.italic, fontWeight: FontWeight.w600, color: color, height: 1.3));

// ---------------------------------------------------------------- Holograma

/// Lámina holográfica: marco de arcoíris que gira, un reflejo que cruza la carátula y el
/// título tornasolado.
class _Holograma extends StatelessWidget {
  const _Holograma(this.t);
  final _Trazo t;

  Widget _portada(double lado) {
    final k = t.k;
    final radio = lado * 0.07;
    return SizedBox(
      width: lado,
      height: lado,
      child: Stack(fit: StackFit.expand, children: [
        CustomPaint(painter: _PintorMarcoHolo(t.fase, radio, 5 * k, 26 * k)),
        Padding(
          padding: EdgeInsets.all(7 * k),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(math.max(0, radio - 6 * k)),
            child: Stack(fit: StackFit.expand, children: [
              _caratula(t.d.caratula, lado - 14 * k, 0),
              // la lámina: un velo tornasol y un reflejo blanco que cruza
              DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [for (final c in _arcoiris) c.withValues(alpha: 0.16)],
                    tileMode: TileMode.mirror,
                    transform: _Desliza(t.fase),
                  ),
                ),
              ),
              DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Colors.white.withValues(alpha: 0),
                      Colors.white.withValues(alpha: 0.32),
                      Colors.white.withValues(alpha: 0),
                    ],
                    stops: [
                      (t.fase * 1.6 - 0.45).clamp(0.0, 1.0),
                      (t.fase * 1.6 - 0.3).clamp(0.0, 1.0),
                      (t.fase * 1.6 - 0.15).clamp(0.0, 1.0),
                    ],
                  ),
                ),
              ),
            ]),
          ),
        ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final p = t.p;
    Widget mancha(Color c, Alignment a, double tam) => Align(
          alignment: a,
          child: Container(
            width: tam,
            height: tam,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(colors: [c.withValues(alpha: 0.42), c.withValues(alpha: 0)]),
            ),
          ),
        );
    final titulo = _conDegradado(
      LinearGradient(colors: _arcoiris, tileMode: TileMode.mirror, transform: _Desliza(t.fase)),
      Text(t.d.titulo,
          maxLines: t.cuadrado ? 2 : 1,
          overflow: TextOverflow.ellipsis,
          textAlign: t.cuadrado ? TextAlign.left : TextAlign.center,
          style: TextStyle(fontSize: (t.cuadrado ? 24 : 30) * k, fontWeight: FontWeight.w900, letterSpacing: -0.5 * k, height: 1.1)),
    );
    final artista = Text(t.d.artista,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(fontSize: 15 * k, color: Colors.white.withValues(alpha: 0.78), letterSpacing: 0.3 * k));
    final fondo = Stack(fit: StackFit.expand, children: [
      const ColoredBox(color: Color(0xFF0A0912)),
      mancha(p.fondo, const Alignment(-1, -0.9), t.ancho * 1.3),
      mancha(t.acento, const Alignment(1.1, 0.1), t.ancho * 1.1),
      mancha(p.contraste, const Alignment(-0.6, 1.1), t.ancho * 1.2),
      CustomPaint(painter: _PintorRayasHolo(k, t.fase)),
    ]);
    if (t.cuadrado) {
      return Stack(fit: StackFit.expand, children: [
        fondo,
        Padding(
          padding: EdgeInsets.fromLTRB(22 * k, 20 * k, 22 * k, 16 * k),
          child: Column(children: [
            Row(children: [_Marca(k, color: Colors.white.withValues(alpha: 0.85)), const Spacer(), _Sello(t)]),
            const Spacer(),
            Row(children: [
              _portada(150 * k),
              SizedBox(width: 16 * k),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  titulo,
                  SizedBox(height: 6 * k),
                  artista,
                ]),
              ),
            ]),
            const Spacer(),
            if (t.letra) ...[
              _versoExclusivo(t, Colors.white.withValues(alpha: 0.88), lineas: 1),
              SizedBox(height: 6 * k),
            ],
            _BarraProgreso(t, color: Colors.white, pista: Colors.white.withValues(alpha: 0.2), tiempos: false),
          ]),
        ),
      ]);
    }
    return Stack(fit: StackFit.expand, children: [
      fondo,
      Padding(
        padding: EdgeInsets.fromLTRB(26 * k, 28 * k, 26 * k, 22 * k),
        child: Column(children: [
          Row(children: [_Marca(k, color: Colors.white.withValues(alpha: 0.85)), const Spacer(), _Sello(t)]),
          SizedBox(height: 26 * k),
          Expanded(
            child: Center(
              child: AspectRatio(aspectRatio: 1, child: LayoutBuilder(builder: (_, c) => _portada(c.maxWidth))),
            ),
          ),
          SizedBox(height: 26 * k),
          titulo,
          SizedBox(height: 6 * k),
          artista,
          if (t.letra) ...[SizedBox(height: 14 * k), _versoExclusivo(t, Colors.white.withValues(alpha: 0.88))],
          SizedBox(height: t.mascota ? 6 * k : 18 * k),
          _BarraProgreso(t, color: Colors.white, pista: Colors.white.withValues(alpha: 0.2)),
          SizedBox(height: 14 * k),
          Text('EDICIÓN HOLOGRÁFICA',
              style: TextStyle(fontSize: 9 * k, letterSpacing: 3 * k, color: Colors.white.withValues(alpha: 0.5), fontWeight: FontWeight.w700)),
        ]),
      ),
    ]);
  }
}

class _PintorMarcoHolo extends CustomPainter {
  _PintorMarcoHolo(this.fase, this.radio, this.grosor, this.brillo);
  final double fase, radio, grosor, brillo;

  @override
  void paint(Canvas canvas, Size size) {
    final r = RRect.fromRectAndRadius((Offset.zero & size).deflate(grosor / 2), Radius.circular(radio));
    final shader = SweepGradient(colors: _arcoiris, transform: GradientRotation(fase * 2 * math.pi)).createShader(Offset.zero & size);
    canvas.drawRRect(
      r,
      Paint()
        ..shader = shader
        ..style = PaintingStyle.stroke
        ..strokeWidth = grosor * 2.2
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, brillo * 0.6),
    );
    canvas.drawRRect(
      r,
      Paint()
        ..shader = shader
        ..style = PaintingStyle.stroke
        ..strokeWidth = grosor,
    );
  }

  @override
  bool shouldRepaint(_PintorMarcoHolo o) => o.fase != fase || o.radio != radio || o.grosor != grosor;
}

/// Rayas finas en diagonal que brillan donde pasa la luz (la textura de una lámina).
class _PintorRayasHolo extends CustomPainter {
  _PintorRayasHolo(this.k, this.fase);
  final double k, fase;

  @override
  void paint(Canvas canvas, Size size) {
    final paso = 9 * k;
    final p = Paint()..strokeWidth = 0.8 * k;
    final centro = (fase * 1.6 - 0.3) * (size.width + size.height);
    for (var x = -size.height; x < size.width; x += paso) {
      final d = ((x + size.height / 2) - centro).abs() / (size.width * 0.6);
      p.color = Colors.white.withValues(alpha: 0.025 + 0.06 * math.max(0, 1 - d));
      canvas.drawLine(Offset(x, size.height), Offset(x + size.height, 0), p);
    }
  }

  @override
  bool shouldRepaint(_PintorRayasHolo o) => o.k != k || o.fase != fase;
}

// ---------------------------------------------------------------- Oro

/// Oro sobre negro, al estilo art déco: marco metálico con un brillo que lo recorre,
/// título dorado y el sello abajo.
class _Oro extends StatelessWidget {
  const _Oro(this.t);
  final _Trazo t;

  Widget _portada(double lado) {
    final k = t.k;
    return Container(
      width: lado,
      height: lado,
      padding: EdgeInsets.all(7 * k),
      decoration: BoxDecoration(
        gradient: _oroBrillante(t.fase),
        borderRadius: BorderRadius.circular(4 * k),
        boxShadow: [
          BoxShadow(color: const Color(0xFFE9C46A).withValues(alpha: 0.32), blurRadius: 34 * k, spreadRadius: 2 * k),
          BoxShadow(color: Colors.black.withValues(alpha: 0.6), blurRadius: 22 * k, offset: Offset(0, 12 * k)),
        ],
      ),
      child: Container(
        padding: EdgeInsets.all(1.6 * k),
        color: const Color(0xFF1A140B),
        child: _caratula(t.d.caratula, lado - 17.2 * k, 1 * k),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final oro = _oroBrillante(t.fase, begin: Alignment.centerLeft, end: Alignment.centerRight);
    final fondo = Stack(fit: StackFit.expand, children: [
      const DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF15110C), Color(0xFF0A0806)],
          ),
        ),
      ),
      Align(
        alignment: const Alignment(0, -0.4),
        child: Container(
          width: t.ancho * 1.4,
          height: t.ancho * 1.4,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [
              Color.lerp(t.p.fondo, const Color(0xFFE9C46A), 0.35)!.withValues(alpha: 0.32),
              const Color(0xFFE9C46A).withValues(alpha: 0),
            ]),
          ),
        ),
      ),
      CustomPaint(painter: _PintorDeco(k, t.fase)),
    ]);
    final titulo = _conDegradado(
      oro,
      Text(t.d.titulo.toUpperCase(),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: (t.cuadrado ? 20 : 25) * k, fontWeight: FontWeight.w900, letterSpacing: 2.4 * k, height: 1.12)),
    );
    final artista = Text(t.d.artista.toUpperCase(),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(fontSize: 11.5 * k, letterSpacing: 3.4 * k, color: const Color(0xFFE9C46A).withValues(alpha: 0.75), fontWeight: FontWeight.w600));
    return Stack(fit: StackFit.expand, children: [
      fondo,
      Padding(
        padding: EdgeInsets.fromLTRB(40 * k, (t.cuadrado ? 30 : 46) * k, 40 * k, (t.cuadrado ? 26 : 38) * k),
        child: Column(children: [
          if (!t.cuadrado) ...[
            _conDegradado(
              oro,
              Text('—  EDICIÓN DORADA  —', style: TextStyle(fontSize: 10 * k, letterSpacing: 3 * k, fontWeight: FontWeight.w700)),
            ),
            SizedBox(height: 22 * k),
          ],
          Expanded(
            child: Center(
              child: AspectRatio(aspectRatio: 1, child: LayoutBuilder(builder: (_, c) => _portada(c.maxWidth))),
            ),
          ),
          SizedBox(height: (t.cuadrado ? 14 : 26) * k),
          titulo,
          SizedBox(height: 7 * k),
          artista,
          if (t.letra && !t.cuadrado) ...[
            SizedBox(height: 14 * k),
            _versoExclusivo(t, const Color(0xFFF7EBC8).withValues(alpha: 0.85)),
          ],
          if (!t.cuadrado) ...[
            SizedBox(height: t.mascota ? 8 * k : 18 * k),
            _BarraProgreso(t,
                color: const Color(0xFFF3D98B),
                pista: const Color(0xFFE9C46A).withValues(alpha: 0.2),
                texto: const Color(0xFFE9C46A).withValues(alpha: 0.7),
                grosor: 3),
          ],
          SizedBox(height: (t.cuadrado ? 10 : 16) * k),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            _Sello(t),
            SizedBox(width: 12 * k),
            _Marca(k, color: const Color(0xFFE9C46A).withValues(alpha: 0.85)),
          ]),
        ]),
      ),
    ]);
  }
}

/// El marco art déco: doble filete dorado con abanicos y rombos en las esquinas.
class _PintorDeco extends CustomPainter {
  _PintorDeco(this.k, this.fase);
  final double k, fase;

  @override
  void paint(Canvas canvas, Size size) {
    final shader = _oroBrillante(fase).createShader(Offset.zero & size);
    final linea = Paint()
      ..shader = shader
      ..style = PaintingStyle.stroke;
    linea.strokeWidth = 1.6 * k;
    canvas.drawRect((Offset.zero & size).deflate(14 * k), linea);
    linea.strokeWidth = 0.7 * k;
    canvas.drawRect((Offset.zero & size).deflate(19 * k), linea);
    for (final (x, y, sx, sy) in [
      (14 * k, 14 * k, 1.0, 1.0),
      (size.width - 14 * k, 14 * k, -1.0, 1.0),
      (14 * k, size.height - 14 * k, 1.0, -1.0),
      (size.width - 14 * k, size.height - 14 * k, -1.0, -1.0),
    ]) {
      final inicio = sx > 0 ? (sy > 0 ? 0.0 : -math.pi / 2) : (sy > 0 ? math.pi / 2 : math.pi);
      for (var i = 1; i <= 3; i++) {
        final r = (8 + i * 7) * k;
        canvas.drawArc(Rect.fromCircle(center: Offset(x, y), radius: r), inicio, math.pi / 2, false, linea);
      }
      final rombo = Path()
        ..moveTo(x + sx * 5 * k, y + sy * 5 * k)
        ..lineTo(x + sx * 9 * k, y + sy * 1 * k)
        ..lineTo(x + sx * 13 * k, y + sy * 5 * k)
        ..lineTo(x + sx * 9 * k, y + sy * 9 * k)
        ..close();
      canvas.drawPath(rombo, Paint()..shader = shader);
    }
  }

  @override
  bool shouldRepaint(_PintorDeco o) => o.k != k || o.fase != fase;
}

// ---------------------------------------------------------------- Galaxia

/// El espacio con los colores de la carátula: nebulosas, estrellas que titilan, chispas y la
/// carátula como un planeta con su anillo y lunas en órbita.
class _Galaxia extends StatelessWidget {
  const _Galaxia(this.t);
  final _Trazo t;

  Widget _planeta(double lado) {
    final k = t.k;
    final cara = lado * 0.68;
    return SizedBox(
      width: lado,
      height: lado,
      child: Stack(alignment: Alignment.center, children: [
        Container(
          width: cara,
          height: cara,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(color: t.acento.withValues(alpha: 0.55), blurRadius: 46 * k, spreadRadius: 4 * k),
              BoxShadow(color: t.acento2.withValues(alpha: 0.35), blurRadius: 90 * k, spreadRadius: 10 * k),
            ],
          ),
        ),
        CustomPaint(size: Size(lado, lado), painter: _PintorOrbita(t.fase, t.acento, t.acento2, k, atras: true)),
        _caratula(t.d.caratula, cara, 0, circulo: true),
        // luz y sombra del planeta
        Container(
          width: cara,
          height: cara,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              center: const Alignment(-0.45, -0.5),
              radius: 1.05,
              colors: [Colors.white.withValues(alpha: 0.16), Colors.transparent, Colors.black.withValues(alpha: 0.45)],
              stops: const [0, 0.5, 1],
            ),
          ),
        ),
        CustomPaint(size: Size(lado, lado), painter: _PintorOrbita(t.fase, t.acento, t.acento2, k, atras: false)),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final p = t.p;
    Widget nebulosa(Color c, Alignment a, double tam, double alfa) => Align(
          alignment: a,
          child: Container(
            width: tam,
            height: tam,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(colors: [c.withValues(alpha: alfa), c.withValues(alpha: 0)]),
            ),
          ),
        );
    final fondo = Stack(fit: StackFit.expand, children: [
      DecoratedBox(
        decoration: BoxDecoration(
          gradient: RadialGradient(
            center: const Alignment(0, -0.3),
            radius: 1.2,
            colors: [Color.lerp(p.fondo, Colors.black, 0.55)!, const Color(0xFF04030A)],
          ),
        ),
      ),
      nebulosa(t.acento, const Alignment(-1.1, -0.7), t.ancho * 1.2, 0.3),
      nebulosa(p.contraste, const Alignment(1.2, 0.5), t.ancho * 1.3, 0.38),
      nebulosa(t.acento2, const Alignment(-0.3, 1.2), t.ancho, 0.25),
      CustomPaint(painter: _PintorEstrellas(k, t.fase, t.acento)),
    ]);
    final titulo = Text(t.d.titulo,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontSize: (t.cuadrado ? 22 : 28) * k,
          fontWeight: FontWeight.w900,
          letterSpacing: -0.3 * k,
          height: 1.1,
          shadows: [Shadow(color: t.acento.withValues(alpha: 0.8), blurRadius: 18 * k)],
        ));
    final artista = Text(t.d.artista,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(fontSize: 14 * k, color: Color.lerp(t.acento, Colors.white, 0.55), letterSpacing: 1.2 * k, fontWeight: FontWeight.w600));
    return Stack(fit: StackFit.expand, children: [
      fondo,
      Padding(
        padding: EdgeInsets.fromLTRB(26 * k, (t.cuadrado ? 18 : 28) * k, 26 * k, (t.cuadrado ? 14 : 22) * k),
        child: Column(children: [
          Row(children: [_Marca(k, color: Colors.white.withValues(alpha: 0.85)), const Spacer(), _Sello(t)]),
          Expanded(
            child: Center(
              child: AspectRatio(aspectRatio: 1, child: LayoutBuilder(builder: (_, c) => _planeta(c.maxWidth))),
            ),
          ),
          titulo,
          SizedBox(height: 6 * k),
          artista,
          if (t.letra && !t.cuadrado) ...[
            SizedBox(height: 14 * k),
            _versoExclusivo(t, Colors.white.withValues(alpha: 0.86)),
          ],
          SizedBox(height: t.mascota ? 4 * k : 16 * k),
          _BarraProgreso(t, color: Colors.white, pista: Colors.white.withValues(alpha: 0.2), tiempos: !t.cuadrado),
        ]),
      ),
    ]);
  }
}

/// El anillo inclinado del planeta y sus lunas. Se pinta en dos mitades: la de atrás (debajo
/// del planeta) y la de delante (encima), para que el anillo lo rodee de verdad.
class _PintorOrbita extends CustomPainter {
  _PintorOrbita(this.fase, this.a, this.b, this.k, {required this.atras});
  final double fase, k;
  final Color a, b;
  final bool atras;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    canvas.save();
    canvas.translate(c.dx, c.dy);
    canvas.rotate(-0.38);
    final ovalo = Rect.fromCenter(center: Offset.zero, width: size.width * 0.98, height: size.width * 0.26);
    final inicio = atras ? math.pi : 0.0;
    final shader = LinearGradient(colors: [a, Colors.white, b]).createShader(ovalo);
    canvas.drawArc(
      ovalo,
      inicio,
      math.pi,
      false,
      Paint()
        ..shader = shader
        ..style = PaintingStyle.stroke
        ..strokeWidth = 6 * k
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, 6 * k),
    );
    canvas.drawArc(
      ovalo,
      inicio,
      math.pi,
      false,
      Paint()
        ..shader = shader
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2 * k,
    );
    for (var i = 0; i < 3; i++) {
      final ang = (fase + i / 3) * 2 * math.pi;
      final enFrente = math.sin(ang) > 0;
      if (enFrente == atras) continue;
      final pos = Offset(math.cos(ang) * ovalo.width / 2, math.sin(ang) * ovalo.height / 2);
      final r = (i == 0 ? 5.5 : 3.5) * k;
      canvas.drawCircle(
          pos,
          r * 2.4,
          Paint()
            ..color = Colors.white.withValues(alpha: 0.25)
            ..maskFilter = MaskFilter.blur(BlurStyle.normal, r * 1.4));
      canvas.drawCircle(pos, r, Paint()..color = Color.lerp(Colors.white, i.isEven ? a : b, 0.3)!);
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(_PintorOrbita o) => o.fase != fase || o.a != a || o.b != b || o.k != k || o.atras != atras;
}

/// Estrellas que titilan, chispas de cuatro puntas y polvo que sube despacio. Siempre las
/// mismas (semilla fija): solo cambian su brillo y su altura con la fase.
class _PintorEstrellas extends CustomPainter {
  _PintorEstrellas(this.k, this.fase, this.color);
  final double k, fase;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final azar = math.Random(3);
    final p = Paint();
    for (var i = 0; i < 240; i++) {
      final x = azar.nextDouble() * size.width;
      final y0 = azar.nextDouble() * size.height;
      final vel = 0.02 + azar.nextDouble() * 0.06;
      final y = (y0 - fase * size.height * vel) % size.height;
      final tam = (0.35 + azar.nextDouble() * azar.nextDouble() * 1.5) * k;
      final fasePropia = azar.nextDouble() * 2 * math.pi;
      final brillo = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(fase * 2 * math.pi * 2 + fasePropia));
      p.color = Color.lerp(Colors.white, color, azar.nextDouble() * 0.5)!.withValues(alpha: brillo);
      canvas.drawCircle(Offset(x, y), tam, p);
    }
    for (var i = 0; i < 9; i++) {
      final x = azar.nextDouble() * size.width;
      final y = azar.nextDouble() * size.height;
      final fasePropia = azar.nextDouble() * 2 * math.pi;
      final s = (4 + azar.nextDouble() * 6) * k * (0.6 + 0.4 * math.sin(fase * 2 * math.pi + fasePropia).abs());
      final chispa = Path()
        ..moveTo(x, y - s)
        ..quadraticBezierTo(x, y, x + s, y)
        ..quadraticBezierTo(x, y, x, y + s)
        ..quadraticBezierTo(x, y, x - s, y)
        ..quadraticBezierTo(x, y, x, y - s)
        ..close();
      canvas.drawCircle(
          Offset(x, y),
          s * 0.9,
          Paint()
            ..color = color.withValues(alpha: 0.35)
            ..maskFilter = MaskFilter.blur(BlurStyle.normal, s * 0.6));
      canvas.drawPath(chispa, Paint()..color = Colors.white.withValues(alpha: 0.95));
    }
  }

  @override
  bool shouldRepaint(_PintorEstrellas o) => o.k != k || o.fase != fase || o.color != color;
}

// ---------------------------------------------------------------- Neón

/// Noche synthwave: suelo de rejilla que corre hacia un horizonte encendido, la
/// carátula con tubos de neón y letras que brillan.
class _Neon extends StatelessWidget {
  const _Neon(this.t);
  final _Trazo t;

  Color get _rosa {
    final h = HSVColor.fromColor(t.acento);
    return h.withSaturation(math.max(0.7, h.saturation)).withValue(1).toColor();
  }

  /// La pareja del neón: cian junto a los rosas, violetas y cálidos; rosa si la carátula ya es cian.
  Color get _cian {
    final h = HSVColor.fromColor(_rosa);
    final frio = h.hue > 150 && h.hue < 230;
    return HSVColor.fromAHSV(1, frio ? 322 : 188, 0.8, 1).toColor();
  }

  @override
  Widget build(BuildContext context) {
    final k = t.k;
    final rosa = _rosa, cian = _cian;
    // parpadeo leve de los tubos
    final luz = 0.85 + 0.15 * math.sin(t.fase * 2 * math.pi * 3).abs();
    final horizonte = t.cuadrado ? 0.62 : 0.66;
    final fondo = Stack(fit: StackFit.expand, children: [
      DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [const Color(0xFF07040F), Color.lerp(const Color(0xFF1A0626), t.p.fondo, 0.3)!, const Color(0xFF07040F)],
            stops: [0, horizonte, 1],
          ),
        ),
      ),
      CustomPaint(painter: _PintorRejilla(k, t.fase, horizonte, rosa, cian)),
      // el suelo se apaga hacia abajo para que los textos se lean bien
      DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.transparent, Colors.transparent, const Color(0xFF07040F).withValues(alpha: 0.82), const Color(0xFF07040F).withValues(alpha: 0.9)],
            stops: [0, horizonte + 0.04, horizonte + 0.16, 1],
          ),
        ),
      ),
    ]);
    final cubierta = LayoutBuilder(builder: (_, c) {
      final lado = c.maxWidth;
      return SizedBox(
        width: lado,
        height: lado,
        child: Stack(fit: StackFit.expand, children: [
          CustomPaint(painter: _PintorTubo(rosa, cian, luz, 12 * k, k)),
          Padding(
            padding: EdgeInsets.all(14 * k),
            child: _caratula(t.d.caratula, lado - 28 * k, 6 * k),
          ),
        ]),
      );
    });
    final titulo = Text(t.d.titulo.toUpperCase(),
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontSize: (t.cuadrado ? 21 : 27) * k,
          fontWeight: FontWeight.w900,
          letterSpacing: 2 * k,
          height: 1.1,
          color: Color.lerp(Colors.white, rosa, 0.15),
          shadows: [
            Shadow(color: rosa.withValues(alpha: luz), blurRadius: 8 * k),
            Shadow(color: rosa.withValues(alpha: 0.8 * luz), blurRadius: 22 * k),
            Shadow(color: rosa.withValues(alpha: 0.5 * luz), blurRadius: 44 * k),
          ],
        ));
    final artista = Text(t.d.artista.toUpperCase(),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          fontSize: 12.5 * k,
          letterSpacing: 3.2 * k,
          fontWeight: FontWeight.w700,
          color: Color.lerp(Colors.white, cian, 0.4),
          shadows: [Shadow(color: cian, blurRadius: 10 * k), Shadow(color: cian.withValues(alpha: 0.6), blurRadius: 24 * k)],
        ));
    return Stack(fit: StackFit.expand, children: [
      fondo,
      Padding(
        padding: EdgeInsets.fromLTRB(28 * k, (t.cuadrado ? 18 : 28) * k, 28 * k, (t.cuadrado ? 14 : 22) * k),
        child: Column(children: [
          Row(children: [_Marca(k, color: Colors.white.withValues(alpha: 0.85)), const Spacer(), _Sello(t)]),
          SizedBox(height: (t.cuadrado ? 10 : 24) * k),
          Expanded(child: Center(child: AspectRatio(aspectRatio: 1, child: cubierta))),
          SizedBox(height: (t.cuadrado ? 12 : 24) * k),
          titulo,
          SizedBox(height: 8 * k),
          artista,
          if (t.letra && !t.cuadrado) ...[
            SizedBox(height: 14 * k),
            _versoExclusivo(t, Colors.white.withValues(alpha: 0.9)),
          ],
          SizedBox(height: t.mascota ? 4 * k : 14 * k),
          _BarraProgreso(t, color: cian, pista: Colors.white.withValues(alpha: 0.16), tiempos: !t.cuadrado),
        ]),
      ),
    ]);
  }
}

/// Dos tubos de neón alrededor de la carátula (rosa por fuera, cian por dentro), con su halo.
class _PintorTubo extends CustomPainter {
  _PintorTubo(this.a, this.b, this.luz, this.radio, this.k);
  final Color a, b;
  final double luz, radio, k;

  @override
  void paint(Canvas canvas, Size size) {
    void tubo(Rect r, Color c, double grosor) {
      final rr = RRect.fromRectAndRadius(r, Radius.circular(radio));
      canvas.drawRRect(
        rr,
        Paint()
          ..color = c.withValues(alpha: 0.75 * luz)
          ..style = PaintingStyle.stroke
          ..strokeWidth = grosor * 3
          ..maskFilter = MaskFilter.blur(BlurStyle.normal, 12 * k),
      );
      canvas.drawRRect(
        rr,
        Paint()
          ..color = c
          ..style = PaintingStyle.stroke
          ..strokeWidth = grosor,
      );
      canvas.drawRRect(
        rr,
        Paint()
          ..color = Colors.white.withValues(alpha: 0.85)
          ..style = PaintingStyle.stroke
          ..strokeWidth = grosor * 0.35,
      );
    }

    tubo((Offset.zero & size).deflate(3 * k), a, 3.2 * k);
    tubo((Offset.zero & size).deflate(9 * k), b, 2 * k);
  }

  @override
  bool shouldRepaint(_PintorTubo o) => o.a != a || o.b != b || o.luz != luz || o.radio != radio || o.k != k;
}

/// El resplandor del horizonte y el suelo de rejilla en perspectiva que avanza.
class _PintorRejilla extends CustomPainter {
  _PintorRejilla(this.k, this.fase, this.horizonte, this.a, this.b);
  final double k, fase, horizonte;
  final Color a, b;

  @override
  void paint(Canvas canvas, Size size) {
    final yh = size.height * horizonte;
    final sol = Rect.fromCircle(center: Offset(size.width / 2, yh), radius: size.width * 0.3);
    canvas.drawCircle(
        sol.center,
        sol.width * 0.62,
        Paint()
          ..shader = RadialGradient(colors: [a.withValues(alpha: 0.28), a.withValues(alpha: 0)])
              .createShader(Rect.fromCircle(center: sol.center, radius: sol.width * 0.62)));
    // el suelo
    canvas.save();
    canvas.clipRect(Rect.fromLTRB(0, yh, size.width, size.height));
    canvas.drawRect(Rect.fromLTRB(0, yh, size.width, size.height), Paint()..color = const Color(0xFF0A0414));
    final linea = Paint()
      ..color = b.withValues(alpha: 0.75)
      ..strokeWidth = 1.2 * k;
    final halo = Paint()
      ..color = b.withValues(alpha: 0.35)
      ..strokeWidth = 4 * k
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, 4 * k);
    final cx = size.width / 2;
    for (var i = -12; i <= 12; i++) {
      final abajo = Offset(cx + i * size.width * 0.16, size.height);
      final arriba = Offset(cx + i * size.width * 0.012, yh);
      canvas.drawLine(arriba, abajo, halo);
      canvas.drawLine(arriba, abajo, linea);
    }
    final hondo = size.height - yh;
    for (var i = 0; i < 12; i++) {
      final z = (i + fase) / 12;
      final y = yh + hondo * z * z;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), halo);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), linea);
    }
    final niebla = Rect.fromLTRB(0, yh, size.width, yh + hondo * 0.35);
    canvas.drawRect(
      niebla,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [a.withValues(alpha: 0.45), a.withValues(alpha: 0)],
        ).createShader(niebla),
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(_PintorRejilla o) => o.k != k || o.fase != fase || o.horizonte != horizonte || o.a != a || o.b != b;
}
