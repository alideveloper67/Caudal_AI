import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:gal/gal.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/letra_video.dart';
import '../../nucleo/premium_letras.dart';
import '../comunes.dart';
import '../tema.dart';
import 'donar.dart';

/// "Compartir letra": eliges unas líneas y las compartes como una tarjeta con la
/// carátula (como en Spotify), como texto o, para donadores, como un video corto
/// con la letra encendiéndose línea a línea (ideal para estados).
Future<void> compartirLetra(BuildContext context,
    {required Json pista, required List<String> lineas, required Color color, int? lineaActual}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: C.superficie,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
    builder: (_) => _HojaCompartirLetra(pista: pista, lineas: lineas, color: color, lineaActual: lineaActual),
  );
}

/// Un estilo de tarjeta. Los de donador se ven con candado a quien no lo es.
class _EstiloTarjeta {
  const _EstiloTarjeta(this.nombre, {this.premium = false});
  final String nombre;
  final bool premium;
}

const _estilos = [
  _EstiloTarjeta('Estado'),
  _EstiloTarjeta('Color'),
  _EstiloTarjeta('Oscuro'),
  _EstiloTarjeta('Claro'),
  _EstiloTarjeta('Neón', premium: true),
  _EstiloTarjeta('Cristal', premium: true),
  _EstiloTarjeta('Papel', premium: true),
  _EstiloTarjeta('Aurora', premium: true),
];

const _iEstado = 0, _iColor = 1, _iOscuro = 2, _iClaro = 3, _iNeon = 4, _iCristal = 5, _iPapel = 6, _iAurora = 7;

class _HojaCompartirLetra extends StatefulWidget {
  const _HojaCompartirLetra({required this.pista, required this.lineas, required this.color, this.lineaActual});
  final Json pista;
  final List<String> lineas;
  final Color color;
  final int? lineaActual;

  @override
  State<_HojaCompartirLetra> createState() => _HojaCompartirLetraState();
}

class _HojaCompartirLetraState extends State<_HojaCompartirLetra> {
  static const _maximo = 8;
  final _clave = GlobalKey();
  final Set<int> _elegidas = {};
  bool _ocupado = false;
  int _estilo = _iEstado;
  int _formato = 2; // 0 cuadrada · 1 vertical 4:5 · 2 historia 9:16

  // opciones de donador
  int _alineacion = 0; // 0 izquierda · 1 centro
  double _tam = 1.0; // 0.8 a 1.3
  bool _firma = true;

  // letra animada (video)
  double? _videoProgreso;
  bool _cancelarVideo = false;
  String? _videoRuta;
  String? _videoError;

  static const _formatos = [('Cuadrada', 1.0), ('Vertical', 0.8), ('Historia', 9 / 16)];

  @override
  void initState() {
    super.initState();
    // de entrada: la línea que suena y las siguientes, o las primeras con texto
    var i = max(0, widget.lineaActual ?? 0);
    while (i < widget.lineas.length && widget.lineas[i].trim().isEmpty) {
      i++;
    }
    for (var k = i; k < widget.lineas.length && _elegidas.length < 4; k++) {
      if (widget.lineas[k].trim().isNotEmpty) _elegidas.add(k);
    }
  }

  @override
  void dispose() {
    _cancelarVideo = true;
    super.dispose();
  }

  List<String> get _texto => [for (final i in (_elegidas.toList()..sort())) widget.lineas[i].trim()];

  void _alternar(int i) {
    setState(() {
      _videoRuta = null;
      if (_elegidas.contains(i)) {
        _elegidas.remove(i);
      } else if (_elegidas.length < _maximo) {
        _elegidas.add(i);
      } else {
        ScaffoldMessenger.maybeOf(context)
            ?.showSnackBar(const SnackBar(content: Text('Puedes elegir hasta $_maximo líneas.')));
      }
    });
  }

  String get _titulo => '${widget.pista['titulo'] ?? ''}';
  String get _artista => '${widget.pista['artista'] ?? ''}'.trim();

  bool get _premium => esPremiumLetras();

  /// ¿El estilo elegido es de donador y esta cuenta no lo es? Se ve de vista previa, no se comparte.
  bool get _bloqueado => _estilos[_estilo].premium && !_premium;

  /// Las opciones de alineación, tamaño y firma solo valen para donadores.
  bool get _opcionesActivas => _premium;

  void _aviso(String t) => ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));

  Future<void> _compartirTexto() async {
    if (_elegidas.isEmpty || _ocupado) return;
    final cuerpo = _texto.join('\n');
    await _enviar(() => SharePlus.instance.share(ShareParams(
          text: '$cuerpo\n\n$_titulo${_artista.isEmpty ? '' : ' — $_artista'}\nCon Caudal',
          subject: _titulo,
        )));
  }

  /// La tarjeta como PNG. Las historias salen a 1080 px de ancho (lo que piden los estados).
  Future<Uint8List> _bytesDeLaTarjeta() async {
    await WidgetsBinding.instance.endOfFrame;
    final ro = _clave.currentContext?.findRenderObject();
    if (ro is! RenderRepaintBoundary) throw StateError('la tarjeta aún no se pintó');
    if (!mounted) throw StateError('la pantalla se cerró');
    final ancho = ro.size.width;
    final escala = _formato == 2 && ancho > 0 ? 1080 / ancho : min(3.0, max(2.0, MediaQuery.devicePixelRatioOf(context)));
    final imagen = await ro.toImage(pixelRatio: escala.clamp(1.0, 4.0));
    final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
    imagen.dispose();
    if (datos == null) throw StateError('no se pudo dibujar la imagen');
    return datos.buffer.asUint8List();
  }

  /// Guarda la imagen en la galería para subirla después a cualquier estado, historia o chat.
  Future<void> _guardar() async {
    if (_elegidas.isEmpty || _ocupado) return;
    if (_bloqueado) return mostrarDonar(context);
    await _enviar(() async {
      final bytes = await _bytesDeLaTarjeta();
      await Gal.putImageBytes(bytes, name: 'caudal_letra_${DateTime.now().millisecondsSinceEpoch}', album: 'Caudal');
      _aviso('Guardada en tu galería (álbum Caudal)');
    });
  }

  Future<void> _copiar() async {
    if (_elegidas.isEmpty) return;
    await Clipboard.setData(ClipboardData(
        text: '${_texto.join('\n')}\n\n$_titulo${_artista.isEmpty ? '' : ' — $_artista'}\nCon Caudal'));
    _aviso('Letra copiada');
  }

  Future<void> _compartirImagen() async {
    if (_elegidas.isEmpty || _ocupado) return;
    if (_bloqueado) return mostrarDonar(context);
    await _enviar(() async {
      final bytes = await _bytesDeLaTarjeta();
      final nombre = 'caudal_letra_${DateTime.now().millisecondsSinceEpoch}.png';
      XFile adjunto;
      if (kIsWeb) {
        adjunto = XFile.fromData(bytes, mimeType: 'image/png', name: nombre);
      } else {
        final dir = await getTemporaryDirectory();
        final archivo = File(p.join(dir.path, nombre));
        await archivo.writeAsBytes(bytes, flush: true);
        adjunto = XFile(archivo.path, mimeType: 'image/png');
      }
      await SharePlus.instance.share(ShareParams(files: [adjunto], text: '$_titulo${_artista.isEmpty ? '' : ' — $_artista'}'));
    });
  }

  Future<void> _enviar(Future<void> Function() accion) async {
    setState(() => _ocupado = true);
    try {
      await accion();
    } catch (e) {
      if (mounted) _aviso('No se pudo compartir: $e');
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  // ------------------------------------------------------------ letra animada

  /// Saca una imagen por línea (la tarjeta con esa línea encendida) y ffmpeg las une con
  /// su duración y un zoom lento. Se puede cancelar y no bloquea la pantalla.
  Future<void> _crearVideo() async {
    if (_elegidas.isEmpty || _ocupado || _videoProgreso != null) return;
    if (!_premium) return mostrarDonar(context);
    final lineas = _texto;
    final guion = GuionVideoLetra.paraLineas(lineas.length);
    final fondo = HSVColor.fromColor(widget.color).withValue(0.62).withSaturation(0.6).toColor();
    final url = '${widget.pista['miniatura'] ?? ''}';
    final encendida = ValueNotifier<int?>(null);
    final llave = GlobalKey();
    OverlayEntry? entrada;
    setState(() {
      _videoProgreso = 0;
      _cancelarVideo = false;
      _videoRuta = null;
      _videoError = null;
    });
    try {
      // la tarjeta se dibuja fuera de la pantalla, a 360x640 (se saca a 1080x1920)
      entrada = OverlayEntry(
        builder: (_) => Positioned(
          left: -5000,
          top: 0,
          width: 360,
          height: 640,
          child: RepaintBoundary(
            key: llave,
            child: Material(
              type: MaterialType.transparency,
              child: ValueListenableBuilder<int?>(
                valueListenable: encendida,
                builder: (_, enc, _) => _tarjeta(fondo, url, encendida: enc),
              ),
            ),
          ),
        ),
      );
      Overlay.of(context, rootOverlay: true).insert(entrada);
      await Future<void>.delayed(const Duration(milliseconds: 350)); // que cargue la carátula
      final imagenes = <List<int>>[];
      for (var i = 0; i < lineas.length; i++) {
        if (_cancelarVideo || !mounted) throw VideoCancelado();
        encendida.value = i;
        await WidgetsBinding.instance.endOfFrame;
        await Future<void>.delayed(const Duration(milliseconds: 90));
        final ro = llave.currentContext?.findRenderObject();
        if (ro is! RenderRepaintBoundary) throw StateError('la tarjeta aún no se pintó');
        final imagen = await ro.toImage(pixelRatio: GuionVideoLetra.ancho / 360);
        final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
        imagen.dispose();
        if (datos == null) throw StateError('no se pudo dibujar la imagen');
        imagenes.add(datos.buffer.asUint8List());
        if (mounted) setState(() => _videoProgreso = 0.3 * (i + 1) / lineas.length);
      }
      entrada.remove();
      entrada = null;
      final ruta = await crearVideoDeLetra(
        imagenesPng: imagenes,
        guion: guion,
        cancelado: () => _cancelarVideo || !mounted,
        progreso: (v) {
          if (mounted) setState(() => _videoProgreso = 0.3 + 0.7 * v);
        },
      );
      if (mounted) setState(() => _videoRuta = ruta);
    } on VideoCancelado {
      if (mounted) _aviso('Se canceló el video');
    } catch (e) {
      if (mounted) setState(() => _videoError = 'No se pudo crear el video: $e');
    } finally {
      entrada?.remove();
      encendida.dispose();
      if (mounted) setState(() => _videoProgreso = null);
    }
  }

  Future<void> _compartirVideo() async {
    final ruta = _videoRuta;
    if (ruta == null) return;
    await _enviar(() => SharePlus.instance.share(ShareParams(
        files: [XFile(ruta, mimeType: 'video/mp4')], text: '$_titulo${_artista.isEmpty ? '' : ' — $_artista'}')));
  }

  Future<void> _guardarVideo() async {
    final ruta = _videoRuta;
    if (ruta == null) return;
    await _enviar(() async {
      await Gal.putVideo(ruta, album: 'Caudal');
      _aviso('Video guardado en tu galería (álbum Caudal)');
    });
  }

  // ------------------------------------------------------------ las tarjetas

  TextAlign get _alinear => _opcionesActivas && _alineacion == 1 ? TextAlign.center : TextAlign.left;
  double get _escalaTexto => _opcionesActivas ? _tam : 1.0;
  bool get _firmaVisible => !_opcionesActivas || _firma;
  Alignment get _alineaLetra => _alinear == TextAlign.center ? Alignment.center : Alignment.centerLeft;

  /// Las líneas elegidas. Sin [encendida] salen todas (en «Estado» la primera encendida y
  /// las demás tenues). Con [encendida] (el video) sale esa brillante, las anteriores tenues y
  /// las que aún no tocan casi apagadas, para que la tarjeta no se mueva de un paso al otro.
  Widget _lineas({
    required double k,
    required double ancho,
    required Color brillante,
    required Color tenue,
    required double base,
    int? encendida,
    bool resaltarPrimera = false,
    Color? brillo,
    TextStyle? plantilla,
    double alturaLinea = 1.18,
  }) {
    final al = _alinear;
    final lineas = _texto;
    final t = _escalaTexto;
    return SizedBox(
      width: ancho,
      child: Column(
        crossAxisAlignment: al == TextAlign.center ? CrossAxisAlignment.center : CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (lineas.isEmpty)
            Text('Elige las líneas que quieres compartir.',
                textAlign: al,
                style: TextStyle(fontSize: 22 * k, fontWeight: FontWeight.w800, color: tenue, height: 1.25))
          else
            for (final (n, l) in lineas.indexed)
              Padding(
                padding: EdgeInsets.only(bottom: 10 * k),
                child: Builder(builder: (_) {
                  final activa = encendida != null ? n == encendida : (resaltarPrimera ? n == 0 : true);
                  final color = encendida != null
                      ? (n == encendida ? brillante : (n < encendida ? tenue : brillante.withValues(alpha: 0.16)))
                      : (resaltarPrimera ? (n == 0 ? brillante : tenue) : brillante);
                  return Text(l,
                      textAlign: al,
                      style: (plantilla ?? const TextStyle(fontWeight: FontWeight.w900)).copyWith(
                        fontSize: base * k * t,
                        height: alturaLinea,
                        color: color,
                        shadows: brillo != null && activa
                            ? [
                                Shadow(color: brillo, blurRadius: 14 * k),
                                Shadow(color: brillo.withValues(alpha: brillo.a * 0.6), blurRadius: 30 * k),
                              ]
                            : null,
                      ));
                }),
              ),
        ],
      ),
    );
  }

  /// La letra dentro del espacio que queda, reducida si no cabe.
  Widget _zonaLetra(Widget lineas) => Expanded(
        child: Align(
          alignment: _alineaLetra,
          child: FittedBox(fit: BoxFit.scaleDown, alignment: _alineaLetra, child: lineas),
        ),
      );

  Widget _firmaCaudal(double k, Color color, {bool centrada = false, bool conLetra = false, Color? tenue}) {
    if (!_firmaVisible) return SizedBox(height: 4 * k);
    return Row(mainAxisAlignment: centrada ? MainAxisAlignment.center : MainAxisAlignment.start, children: [
      Image.asset('assets/logo/caudal.png', width: 18 * k, height: 18 * k),
      SizedBox(width: 6 * k),
      Text('Caudal', style: TextStyle(fontSize: 13 * k, fontWeight: FontWeight.w900, color: color, letterSpacing: 0.2)),
      if (conLetra) ...[
        const Spacer(),
        Text('Letra', style: TextStyle(fontSize: 12 * k, fontWeight: FontWeight.w700, color: tenue ?? color, letterSpacing: 1.2)),
      ],
    ]);
  }

  /// La carátula (o una nota si no hay), con las esquinas redondeadas.
  Widget _caratula(String url, double lado, double radio) => Portada(url: url, lado: lado, radio: radio);

  Widget _titulos(double k, Color tinta, Color tenue,
      {TextAlign al = TextAlign.left, bool mayusculas = false, TextStyle? plantilla}) {
    final base = plantilla ?? const TextStyle();
    return Column(
      crossAxisAlignment: al == TextAlign.center ? CrossAxisAlignment.center : CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(mayusculas ? _titulo.toUpperCase() : _titulo,
            maxLines: 2,
            textAlign: al,
            overflow: TextOverflow.ellipsis,
            style: base.copyWith(
                fontSize: 17 * k,
                fontWeight: FontWeight.w800,
                color: tinta,
                height: 1.15,
                letterSpacing: mayusculas ? 1.2 * k : null)),
        if (_artista.isNotEmpty)
          Padding(
            padding: EdgeInsets.only(top: 2 * k),
            child: Text(_artista,
                maxLines: 1,
                textAlign: al,
                overflow: TextOverflow.ellipsis,
                style: base.copyWith(fontSize: 13.5 * k, color: tenue, fontWeight: FontWeight.w600)),
          ),
      ],
    );
  }

  /// La carátula muy difuminada, que llena el fondo.
  Widget _fondoDifuminado(String url, double ancho, double alto, double k, {double sigma = 34}) => ClipRect(
        child: ImageFiltered(
          imageFilter: ui.ImageFilter.blur(sigmaX: sigma * k, sigmaY: sigma * k, tileMode: TileMode.clamp),
          child: Transform.scale(scale: 1.6, child: Portada(url: url, lado: max(ancho, alto), radio: 0)),
        ),
      );

  /// La tarjeta del estilo elegido. [encendida] la usa el video (ver [_lineas]).
  Widget _tarjeta(Color colorCaratula, String url, {int? encendida}) => switch (_estilo) {
        _iEstado => _tarjetaEstado(url, encendida),
        _iNeon => _tarjetaNeon(colorCaratula, url, encendida),
        _iCristal => _tarjetaCristal(url, encendida),
        _iPapel => _tarjetaPapel(url, encendida),
        _iAurora => _tarjetaAurora(colorCaratula, url, encendida),
        _ => _tarjetaBasica(colorCaratula, url, encendida),
      };

  /// «Estado»: el mismo diseño que la tarjeta del escritorio. Fondo con la carátula difuminada,
  /// carátula grande y centrada, título y artista, la letra (la primera línea encendida y las
  /// demás más tenues) y la firma de Caudal. Se adapta a cualquier formato.
  Widget _tarjetaEstado(String url, int? encendida) {
    return LayoutBuilder(builder: (context, c) {
      final ancho = c.maxWidth;
      final alto = c.maxHeight.isFinite ? c.maxHeight : ancho * 16 / 9;
      final k = ancho / 380;
      final caratula = min(ancho * 0.52, alto * 0.30);
      return ClipRRect(
        borderRadius: BorderRadius.circular(22 * k),
        child: Stack(fit: StackFit.expand, children: [
          const ColoredBox(color: Color(0xFF0B0D12)),
          _fondoDifuminado(url, ancho, alto, k),
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Colors.black.withValues(alpha: 0.38), Colors.black.withValues(alpha: 0.62)],
              ),
            ),
          ),
          Padding(
            padding: EdgeInsets.fromLTRB(26 * k, 0, 26 * k, 20 * k),
            child: Column(children: [
              SizedBox(height: alto * 0.10),
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(caratula * 0.07),
                  boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.5), blurRadius: 30 * k, offset: Offset(0, 12 * k))],
                ),
                child: _caratula(url, caratula, caratula * 0.07),
              ),
              SizedBox(height: 22 * k),
              _titulos(k, Colors.white, Colors.white.withValues(alpha: 0.72), al: TextAlign.center),
              SizedBox(height: 26 * k),
              _zonaLetra(_lineas(
                k: k,
                ancho: ancho - 52 * k,
                brillante: Colors.white,
                tenue: Colors.white.withValues(alpha: 0.58),
                base: 26,
                encendida: encendida,
                resaltarPrimera: true,
                brillo: Colors.white.withValues(alpha: 0.55),
                alturaLinea: 1.15,
              )),
              _firmaCaudal(k, Colors.white.withValues(alpha: 0.82), centrada: true),
            ]),
          ),
        ]),
      );
    });
  }

  /// Color, Oscuro y Claro: carátula pequeña arriba, frase grande y firma.
  Widget _tarjetaBasica(Color colorCaratula, String url, int? encendida) {
    final claro = _estilo == _iClaro;
    final tinta = claro ? const Color(0xFF14161B) : Colors.white;
    final tenue = claro ? const Color(0xFF14161B).withValues(alpha: 0.62) : Colors.white.withValues(alpha: 0.72);
    final fondo = switch (_estilo) {
      _iColor => LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [colorCaratula, Color.lerp(colorCaratula, Colors.black, 0.55)!]),
      _iOscuro => LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color.lerp(colorCaratula, const Color(0xFF0B0D12), 0.78)!, const Color(0xFF0B0D12)]),
      _ => const LinearGradient(
          begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Color(0xFFF8F6F0), Color(0xFFEAE5DA)]),
    };
    return LayoutBuilder(builder: (context, c) {
      final lado = c.maxWidth;
      final k = lado / 380; // todo escala con el ancho para que la imagen salga igual en cualquier pantalla
      return Container(
        padding: EdgeInsets.fromLTRB(26 * k, 26 * k, 26 * k, 20 * k),
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(22 * k), gradient: fondo),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10 * k),
                boxShadow: [
                  BoxShadow(color: Colors.black.withValues(alpha: claro ? 0.18 : 0.45), blurRadius: 16 * k, offset: Offset(0, 6 * k))
                ],
              ),
              child: _caratula(url, 58 * k, 10 * k),
            ),
            SizedBox(width: 14 * k),
            Expanded(child: _titulos(k, tinta, tenue)),
          ]),
          // las líneas elegidas, grandes, ajustadas al espacio que queda
          _zonaLetra(_lineas(
            k: k,
            ancho: lado - 52 * k,
            brillante: tinta,
            tenue: tenue,
            base: 28,
            encendida: encendida,
            plantilla: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: -0.4),
          )),
          _firmaCaudal(k, tinta, conLetra: true, tenue: tenue),
        ]),
      );
    });
  }

  /// «Neón»: noche cerrada, resplandores de color y letras que brillan como un letrero.
  Widget _tarjetaNeon(Color colorCaratula, String url, int? encendida) {
    final hsv = HSVColor.fromColor(colorCaratula);
    final neon = hsv.withSaturation(0.85).withValue(1).toColor();
    final neon2 = hsv.withHue((hsv.hue + 150) % 360).withSaturation(0.8).withValue(1).toColor();
    return LayoutBuilder(builder: (context, c) {
      final ancho = c.maxWidth;
      final alto = c.maxHeight.isFinite ? c.maxHeight : ancho * 16 / 9;
      final k = ancho / 380;
      Widget resplandor(Color col, Alignment a, double tam) => Align(
            alignment: a,
            child: Container(
              width: tam,
              height: tam,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(colors: [col.withValues(alpha: 0.5), col.withValues(alpha: 0)]),
              ),
            ),
          );
      return ClipRRect(
        borderRadius: BorderRadius.circular(22 * k),
        child: Stack(fit: StackFit.expand, children: [
          const ColoredBox(color: Color(0xFF05060F)),
          resplandor(neon, const Alignment(-1.1, -1.0), ancho * 1.1),
          resplandor(neon2, const Alignment(1.2, 1.1), ancho * 1.1),
          Container(
            margin: EdgeInsets.all(12 * k),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16 * k),
              border: Border.all(color: neon.withValues(alpha: 0.9), width: 2 * k),
              boxShadow: [BoxShadow(color: neon.withValues(alpha: 0.55), blurRadius: 14 * k)],
            ),
          ),
          Padding(
            padding: EdgeInsets.fromLTRB(32 * k, 30 * k, 32 * k, 24 * k),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10 * k),
                    border: Border.all(color: neon2, width: 1.5 * k),
                    boxShadow: [BoxShadow(color: neon2.withValues(alpha: 0.6), blurRadius: 12 * k)],
                  ),
                  child: _caratula(url, min(54 * k, alto * 0.13), 9 * k),
                ),
                SizedBox(width: 14 * k),
                Expanded(child: _titulos(k, Colors.white, neon2.withValues(alpha: 0.95), mayusculas: true)),
              ]),
              _zonaLetra(_lineas(
                k: k,
                ancho: ancho - 64 * k,
                brillante: Colors.white,
                tenue: neon.withValues(alpha: 0.55),
                base: 27,
                encendida: encendida,
                brillo: neon.withValues(alpha: 0.9),
                plantilla: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.6),
              )),
              _firmaCaudal(k, Colors.white.withValues(alpha: 0.9)),
            ]),
          ),
        ]),
      );
    });
  }

  /// «Cristal»: la carátula difuminada de fondo y un panel de vidrio esmerilado con la letra.
  Widget _tarjetaCristal(String url, int? encendida) {
    return LayoutBuilder(builder: (context, c) {
      final ancho = c.maxWidth;
      final alto = c.maxHeight.isFinite ? c.maxHeight : ancho * 16 / 9;
      final k = ancho / 380;
      return ClipRRect(
        borderRadius: BorderRadius.circular(22 * k),
        child: Stack(fit: StackFit.expand, children: [
          const ColoredBox(color: Color(0xFF10131A)),
          _fondoDifuminado(url, ancho, alto, k, sigma: 26),
          ColoredBox(color: Colors.black.withValues(alpha: 0.18)),
          Padding(
            padding: EdgeInsets.all(20 * k),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(24 * k),
              child: BackdropFilter(
                filter: ui.ImageFilter.blur(sigmaX: 14 * k, sigmaY: 14 * k),
                child: Container(
                  width: double.infinity,
                  height: double.infinity,
                  padding: EdgeInsets.fromLTRB(22 * k, 22 * k, 22 * k, 16 * k),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24 * k),
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Colors.white.withValues(alpha: 0.24), Colors.white.withValues(alpha: 0.07)],
                    ),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.34), width: 1.2 * k),
                  ),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      _caratula(url, min(56 * k, alto * 0.13), 12 * k),
                      SizedBox(width: 14 * k),
                      Expanded(child: _titulos(k, Colors.white, Colors.white.withValues(alpha: 0.78))),
                    ]),
                    _zonaLetra(_lineas(
                      k: k,
                      ancho: ancho - 84 * k,
                      brillante: Colors.white,
                      tenue: Colors.white.withValues(alpha: 0.62),
                      base: 26,
                      encendida: encendida,
                      plantilla: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: -0.2),
                    )),
                    _firmaCaudal(k, Colors.white.withValues(alpha: 0.9)),
                  ]),
                ),
              ),
            ),
          ),
        ]),
      );
    });
  }

  /// «Papel»: hoja de cuaderno, la carátula como foto instantánea inclinada y letra de pluma.
  Widget _tarjetaPapel(String url, int? encendida) {
    const tinta = Color(0xFF2B2118);
    const serif = TextStyle(
        fontFamily: 'serif', fontFamilyFallback: ['Georgia', 'Times New Roman'], fontStyle: FontStyle.italic);
    return LayoutBuilder(builder: (context, c) {
      final ancho = c.maxWidth;
      final alto = c.maxHeight.isFinite ? c.maxHeight : ancho * 16 / 9;
      final k = ancho / 380;
      final foto = min(ancho * 0.36, alto * 0.26);
      return ClipRRect(
        borderRadius: BorderRadius.circular(22 * k),
        child: Stack(fit: StackFit.expand, children: [
          const ColoredBox(color: Color(0xFFF3ECDD)),
          CustomPaint(painter: _PintorCuaderno(k)),
          Padding(
            padding: EdgeInsets.fromLTRB(40 * k, 24 * k, 28 * k, 18 * k),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
                Transform.rotate(
                  angle: -0.06,
                  child: Container(
                    padding: EdgeInsets.fromLTRB(5 * k, 5 * k, 5 * k, 14 * k),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.25), blurRadius: 10 * k, offset: Offset(0, 4 * k))],
                    ),
                    child: _caratula(url, foto * 0.78, 2 * k),
                  ),
                ),
                SizedBox(width: 16 * k),
                Expanded(child: _titulos(k, tinta, tinta.withValues(alpha: 0.65), plantilla: serif)),
              ]),
              _zonaLetra(_lineas(
                k: k,
                ancho: ancho - 68 * k,
                brillante: tinta,
                tenue: tinta.withValues(alpha: 0.5),
                base: 27,
                encendida: encendida,
                plantilla: serif.copyWith(fontWeight: FontWeight.w700),
                alturaLinea: 1.25,
              )),
              _firmaCaudal(k, tinta.withValues(alpha: 0.8)),
            ]),
          ),
        ]),
      );
    });
  }

  /// «Aurora»: luces de colores que se mezclan sobre la noche, con la carátula en círculo.
  Widget _tarjetaAurora(Color colorCaratula, String url, int? encendida) {
    final hsv = HSVColor.fromColor(colorCaratula).withSaturation(0.75).withValue(1);
    final a = hsv.toColor();
    final b = hsv.withHue((hsv.hue + 70) % 360).toColor();
    final d = hsv.withHue((hsv.hue + 160) % 360).toColor();
    return LayoutBuilder(builder: (context, c) {
      final ancho = c.maxWidth;
      final alto = c.maxHeight.isFinite ? c.maxHeight : ancho * 16 / 9;
      final k = ancho / 380;
      Widget luz(Color col, Alignment al, double tam) => Align(
            alignment: al,
            child: ImageFiltered(
              imageFilter: ui.ImageFilter.blur(sigmaX: 46 * k, sigmaY: 46 * k, tileMode: TileMode.decal),
              child: Container(
                  width: tam, height: tam, decoration: BoxDecoration(shape: BoxShape.circle, color: col.withValues(alpha: 0.7))),
            ),
          );
      final cara = min(ancho * 0.26, alto * 0.17);
      return ClipRRect(
        borderRadius: BorderRadius.circular(22 * k),
        child: Stack(fit: StackFit.expand, children: [
          const ColoredBox(color: Color(0xFF070912)),
          luz(a, const Alignment(-0.9, -0.8), ancho * 0.8),
          luz(b, const Alignment(1.0, -0.1), ancho * 0.7),
          luz(d, const Alignment(-0.4, 1.0), ancho * 0.8),
          ColoredBox(color: Colors.black.withValues(alpha: 0.22)),
          Padding(
            padding: EdgeInsets.fromLTRB(28 * k, 26 * k, 28 * k, 20 * k),
            child: Column(children: [
              Container(
                decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.4), blurRadius: 18 * k)]),
                child: Portada(url: url, lado: cara, circulo: true),
              ),
              SizedBox(height: 12 * k),
              _titulos(k, Colors.white, Colors.white.withValues(alpha: 0.78), al: TextAlign.center),
              SizedBox(height: 10 * k),
              _zonaLetra(_lineas(
                k: k,
                ancho: ancho - 56 * k,
                brillante: Colors.white,
                tenue: Colors.white.withValues(alpha: 0.6),
                base: 27,
                encendida: encendida,
                brillo: Colors.white.withValues(alpha: 0.35),
              )),
              _firmaCaudal(k, Colors.white.withValues(alpha: 0.9), centrada: true),
            ]),
          ),
        ]),
      );
    });
  }

  // ------------------------------------------------------------ la hoja

  /// Las opciones de alineación, tamaño y firma: solo donadores (a los demás un toque los lleva a Donar).
  Widget _opcionesDonador() {
    final bloqueo = !_premium;
    Widget cuerpo = Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Wrap(spacing: 8, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
        const Text('Alineación', style: estiloSecundario),
        for (final (i, t) in const ['Izquierda', 'Centro'].indexed)
          ChoiceChip(
            label: Text(t),
            selected: _alineacion == i,
            onSelected: bloqueo ? null : (_) => setState(() => _alineacion = i),
          ),
      ]),
      Row(children: [
        const Text('Tamaño', style: estiloSecundario),
        Expanded(
          child: Slider(
            value: _tam,
            min: 0.8,
            max: 1.3,
            divisions: 5,
            label: '${(_tam * 100).round()} %',
            onChanged: bloqueo ? null : (v) => setState(() => _tam = v),
          ),
        ),
      ]),
      Row(children: [
        const Expanded(child: Text('Mostrar la firma de Caudal', style: estiloSecundario)),
        Switch.adaptive(value: _firma, onChanged: bloqueo ? null : (v) => setState(() => _firma = v)),
      ]),
    ]);
    if (bloqueo) {
      cuerpo = Stack(children: [
        Opacity(opacity: 0.45, child: IgnorePointer(child: cuerpo)),
        Positioned.fill(
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => mostrarDonar(context),
            child: const Align(
              alignment: Alignment.centerRight,
              child: Padding(
                padding: EdgeInsets.only(right: 8),
                child: Icon(Icons.lock_rounded, size: 20, color: C.texto2),
              ),
            ),
          ),
        ),
      ]);
    }
    return cuerpo;
  }

  Widget _panelVideo() {
    final progreso = _videoProgreso;
    if (kIsWeb) {
      return const Text('La letra animada se crea desde la app de Android o iPhone.', style: estiloDetalle);
    }
    if (progreso != null) {
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        LinearProgressIndicator(
            value: progreso == 0 ? null : progreso, color: C.acento, backgroundColor: C.superficie3),
        const SizedBox(height: 6),
        Row(children: [
          Expanded(child: Text(progreso < 0.3 ? 'Preparando las imágenes…' : 'Creando el video…', style: estiloDetalle)),
          TextButton(onPressed: () => setState(() => _cancelarVideo = true), child: const Text('Cancelar')),
        ]),
      ]);
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      FilledButton.tonalIcon(
        onPressed: _elegidas.isEmpty || _ocupado ? null : _crearVideo,
        icon: Icon(_premium ? Icons.movie_creation_rounded : Icons.lock_rounded, size: 20),
        label: const Text('Crear video animado'),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(46), shape: const StadiumBorder()),
      ),
      Padding(
        padding: const EdgeInsets.only(top: 4),
        child: Text(
            _premium
                ? 'Un video vertical de unos 10 segundos con la letra encendiéndose línea a línea, listo para estados.'
                : 'Exclusivo para donadores: toca para ver cómo apoyar a Caudal.',
            style: estiloDetalle),
      ),
      if (_videoError != null)
        Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(_videoError!, style: const TextStyle(color: C.error, fontSize: 13))),
      if (_videoRuta != null)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Row(children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: _ocupado ? null : _compartirVideo,
                icon: const Icon(Icons.ios_share_rounded, size: 18),
                label: const Text('Compartir video'),
                style: FilledButton.styleFrom(
                    backgroundColor: C.acento, foregroundColor: C.acentoTexto, shape: const StadiumBorder()),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _ocupado ? null : _guardarVideo,
                icon: const Icon(Icons.download_rounded, size: 18),
                label: const Text('Guardar video'),
                style: OutlinedButton.styleFrom(shape: const StadiumBorder()),
              ),
            ),
          ]),
        ),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final fondo = HSVColor.fromColor(widget.color).withValue(0.62).withSaturation(0.6).toColor();
    final url = '${widget.pista['miniatura'] ?? ''}';
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.92,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (_, scroll) => Column(children: [
        const SizedBox(height: 10),
        Container(width: 38, height: 4, decoration: BoxDecoration(color: C.texto3, borderRadius: BorderRadius.circular(2))),
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 14, 20, 4),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text('Compartir letra', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          ),
        ),
        Expanded(
          child: ListView(controller: scroll, padding: const EdgeInsets.fromLTRB(20, 8, 20, 12), children: [
            // la tarjeta que se comparte
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 380),
                child: AnimatedSize(
                  duration: const Duration(milliseconds: 220),
                  curve: Curves.easeOutCubic,
                  child: RepaintBoundary(
                    key: _clave,
                    child: AspectRatio(
                      aspectRatio: _formatos[_formato].$2,
                      child: Stack(fit: StackFit.expand, children: [
                        _tarjeta(fondo, url),
                        // vista previa de un estilo de donador: se ve, con una marca discreta
                        if (_bloqueado)
                          const Positioned(
                            right: 14,
                            bottom: 40,
                            child: IgnorePointer(
                              child: Text('Vista previa · donadores',
                                  style: TextStyle(
                                      fontSize: 10.5,
                                      fontWeight: FontWeight.w800,
                                      color: Colors.white54,
                                      shadows: [Shadow(color: Colors.black54, blurRadius: 4)])),
                            ),
                          ),
                      ]),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 14),
            Center(
              child: Wrap(spacing: 8, runSpacing: 6, alignment: WrapAlignment.center, children: [
                for (var i = 0; i < _estilos.length; i++)
                  ChoiceChip(
                    avatar: _estilos[i].premium && !_premium ? const Icon(Icons.lock_rounded, size: 14) : null,
                    label: Text(_estilos[i].nombre),
                    selected: _estilo == i,
                    onSelected: (_) => setState(() {
                      _estilo = i;
                      _videoRuta = null;
                    }),
                  ),
              ]),
            ),
            const SizedBox(height: 6),
            Center(
              child: Wrap(spacing: 8, runSpacing: 6, alignment: WrapAlignment.center, children: [
                for (var i = 0; i < _formatos.length; i++)
                  ChoiceChip(
                    label: Text(_formatos[i].$1),
                    selected: _formato == i,
                    onSelected: (_) => setState(() => _formato = i),
                  ),
              ]),
            ),
            if (_bloqueado)
              const Padding(padding: EdgeInsets.only(top: 6), child: AvisoDonar(texto: 'Estilo exclusivo para donadores')),
            const SizedBox(height: 10),
            _opcionesDonador(),
            const SizedBox(height: 6),
            _panelVideo(),
            const SizedBox(height: 10),
            const Text(
                'Al compartir elige «Estado» de WhatsApp, «Historia» de Instagram u otra app. '
                'Con «Guardar» la subes después desde tu galería.',
                textAlign: TextAlign.center,
                style: estiloDetalle),
            const SizedBox(height: 16),
            Text('Toca las líneas para elegirlas (${_elegidas.length} de $_maximo)', style: estiloSecundario),
            const SizedBox(height: 6),
            for (var i = 0; i < widget.lineas.length; i++)
              if (widget.lineas[i].trim().isNotEmpty)
                InkWell(
                  borderRadius: BorderRadius.circular(10),
                  onTap: () => _alternar(i),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 6),
                    child: Row(children: [
                      Icon(_elegidas.contains(i) ? Icons.check_circle_rounded : Icons.circle_outlined,
                          size: 22, color: _elegidas.contains(i) ? C.acento : C.texto3),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(widget.lineas[i].trim(),
                            style: TextStyle(
                                fontSize: 15,
                                fontWeight: _elegidas.contains(i) ? FontWeight.w800 : FontWeight.w500,
                                color: _elegidas.contains(i) ? C.texto : C.texto2)),
                      ),
                    ]),
                  ),
                ),
          ]),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Row(children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _elegidas.isEmpty || _ocupado ? null : _compartirImagen,
                    icon: _ocupado
                        ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.2, color: C.acentoTexto))
                        : Icon(_bloqueado ? Icons.lock_rounded : Icons.ios_share_rounded),
                    label: const Text('Compartir en estados y chats'),
                    style: FilledButton.styleFrom(
                        backgroundColor: C.acento,
                        foregroundColor: C.acentoTexto,
                        minimumSize: const Size.fromHeight(44),
                        shape: const StadiumBorder()),
                  ),
                ),
              ]),
              const SizedBox(height: 6),
              Row(children: [
                for (final (icono, texto, accion) in [
                  (Icons.download_rounded, 'Guardar', _guardar),
                  (Icons.notes_rounded, 'Texto', _compartirTexto),
                  (Icons.copy_rounded, 'Copiar', _copiar),
                ])
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: OutlinedButton.icon(
                        onPressed: _elegidas.isEmpty || _ocupado ? null : accion,
                        icon: Icon(icono, size: 17),
                        label: FittedBox(fit: BoxFit.scaleDown, child: Text(texto, maxLines: 1, softWrap: false)),
                        style: OutlinedButton.styleFrom(
                            minimumSize: const Size.fromHeight(40),
                            padding: const EdgeInsets.symmetric(horizontal: 8),
                            shape: const StadiumBorder()),
                      ),
                    ),
                  ),
              ]),
            ]),
          ),
        ),
      ]),
    );
  }
}

/// Las rayas azules de un cuaderno y su margen rojo.
class _PintorCuaderno extends CustomPainter {
  _PintorCuaderno(this.k);
  final double k;

  @override
  void paint(Canvas canvas, Size size) {
    final raya = Paint()
      ..color = const Color(0xFF6B8CBF).withValues(alpha: 0.28)
      ..strokeWidth = max(1, k);
    final paso = 26 * k;
    for (var y = 70 * k; y < size.height; y += paso) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), raya);
    }
    canvas.drawLine(
        Offset(30 * k, 0),
        Offset(30 * k, size.height),
        Paint()
          ..color = const Color(0xFFD35B5B).withValues(alpha: 0.45)
          ..strokeWidth = max(1, 1.4 * k));
  }

  @override
  bool shouldRepaint(_PintorCuaderno o) => o.k != k;
}
