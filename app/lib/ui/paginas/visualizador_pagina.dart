import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/espectro.dart';
import '../../nucleo/premium_letras.dart';
import '../../nucleo/ritmo_fondo.dart';
import '../../reproduccion/jugador.dart';
import '../../reproduccion/reproductor.dart';
import '../../reproduccion/ventana_web.dart';
import '../atajos_teclado.dart';
import '../reproductor/hueco_video_web.dart';
import '../reproductor/paleta_portada.dart';
import '../servicios.dart';

/// El visualizador a pantalla completa (donadores), como el de Caudal Escritorio:
/// Ondas, Partículas y Barras. En la computadora, con tu música y la de la
/// comunidad, las barras son el sonido de verdad; con YouTube siguen el ritmo.
class VisualizadorPagina extends StatefulWidget {
  const VisualizadorPagina({super.key});

  static const estilos = {'ondas': 'Ondas', 'particulas': 'Partículas', 'barras': 'Barras'};

  static const textoBloqueo =
      'El visualizador es para donadores: dona con Yape o canjea un código de prueba en Ajustes › Personalizar.';

  static Future<void> abrir(BuildContext context) async {
    final s = Caudal.leer(context);
    if (!esPremiumLetras()) return s.avisar(textoBloqueo);
    if (s.reproductor.actual == null) return s.avisar('Pon algo a sonar para ver el visualizador.');
    await Navigator.of(context, rootNavigator: true)
        .push(MaterialPageRoute<void>(fullscreenDialog: true, builder: (_) => const VisualizadorPagina()));
  }

  @override
  State<VisualizadorPagina> createState() => _VisualizadorPaginaState();
}

class _Particula {
  _Particula(math.Random a, {bool inicial = false})
      : angulo = a.nextDouble() * math.pi * 2,
        radio = inicial ? a.nextDouble() : 0,
        velocidad = 0.08 + a.nextDouble() * 0.2,
        tamano = 1.2 + a.nextDouble() * 2.4,
        color = a.nextDouble();
  double angulo, radio, velocidad, tamano, color;
}

class _VisualizadorPaginaState extends State<VisualizadorPagina> with SingleTickerProviderStateMixin {
  final _modelo = ModeloAudio();
  final _cuadro = ValueNotifier<double>(0);
  final _azar = math.Random(7);
  late final List<_Particula> _partes = [for (var i = 0; i < 96; i++) _Particula(_azar, inicial: true)];
  late final Ticker _reloj;
  Duration _antes = Duration.zero;
  Reproductor? _r;
  Servicios? _s;
  String _estilo = 'ondas';
  String _url = '-';
  PaletaPortada _paleta = PaletaPortada.neutra;
  ui.Image? _portada;
  // la posición llega a saltos: entre avisos se calcula con el reloj
  Duration _posBase = Duration.zero;
  DateTime _posCuando = DateTime.now();

  @override
  void initState() {
    super.initState();
    EspectroWeb.medir(true);
    _reloj = createTicker(_paso)..start();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_r != null) return;
    _s = Caudal.leer(context);
    _r = _s!.reproductor
      ..addListener(_cambio)
      ..posicion.addListener(_posicion);
    final e = _s!.ajustes.texto('visualizador_estilo');
    _estilo = VisualizadorPagina.estilos.containsKey(e) ? e : 'ondas';
    _posicion();
    _cambio();
  }

  @override
  void dispose() {
    EspectroWeb.medir(false);
    if (VentanaWeb.completa.value) VentanaWeb.pantallaCompleta(false);
    _reloj.dispose();
    _r?.removeListener(_cambio);
    _r?.posicion.removeListener(_posicion);
    _portada?.dispose();
    _cuadro.dispose();
    super.dispose();
  }

  void _posicion() {
    _posBase = _r!.posicion.value;
    _posCuando = DateTime.now();
  }

  void _cambio() {
    if (!mounted) return;
    final url = '${_r!.actual?['miniatura'] ?? ''}';
    if (url != _url) {
      _url = url;
      paletaDe(url).then((p) {
        if (mounted && _url == url) _paleta = p;
      });
      _cargarPortada(url);
    }
    setState(() {});
  }

  void _cargarPortada(String url) {
    final bytes = PortadasMem.bytes(url);
    final ImageProvider? pr = bytes != null
        ? MemoryImage(bytes)
        : url.startsWith('http')
            ? CachedNetworkImageProvider(url)
            : null;
    if (pr == null) {
      _portada?.dispose();
      _portada = null;
      return;
    }
    final flujo = ResizeImage(pr, width: 420).resolve(ImageConfiguration.empty);
    late ImageStreamListener oyente;
    oyente = ImageStreamListener((info, _) {
      flujo.removeListener(oyente);
      if (!mounted || _url != url) return info.dispose();
      _portada?.dispose();
      _portada = info.image.clone();
      info.dispose();
    }, onError: (_, _) => flujo.removeListener(oyente));
    flujo.addListener(oyente);
  }

  void _paso(Duration t) {
    // ~30 cuadros por segundo: de sobra, y la mitad de gasto
    if (t - _antes < const Duration(milliseconds: 30)) return;
    final dt = (t - _antes).inMicroseconds / 1e6;
    _antes = t;
    final r = _r;
    if (r == null) return;
    final sonando = r.estado == EstadoRepro.sonando;
    final bins = sonando && !(r.fuente?.esYouTubeWeb ?? false) ? EspectroWeb.leer() : null;
    final ritmo = RitmoFondo.para(_s!.coleccion).de('${r.actual?['clave'] ?? ''}');
    var pos = _posBase.inMilliseconds / 1000;
    if (sonando) pos += DateTime.now().difference(_posCuando).inMilliseconds / 1000 * r.velocidad;
    _modelo.avanzar(dt,
        reales: bins == null ? null : agruparBandas(bins.$1, _modelo.n, hz: bins.$2),
        sonando: sonando, pos: pos, bpm: ritmo?.bpm ?? 0, fase: ritmo?.primerTiempo ?? 0);
    if (!sonando && _modelo.quieto) return; // en pausa y todo quieto: no se repinta
    for (var i = 0; i < _partes.length; i++) {
      final p = _partes[i];
      p.radio += p.velocidad * dt * (0.35 + 1.6 * _modelo.energia + 1.2 * _modelo.golpe);
      p.angulo += dt * 0.12;
      if (p.radio >= 1) _partes[i] = _Particula(_azar);
    }
    _cuadro.value = t.inMicroseconds / 1e6;
  }

  @override
  Widget build(BuildContext context) {
    final r = _r!;
    final p = r.actual;
    final youtube = r.fuente?.esYouTubeWeb ?? false;
    const sombra = [Shadow(blurRadius: 12, color: Colors.black87)];
    return CerrarConEsc(child: Scaffold(
      backgroundColor: Colors.black,
      body: Stack(children: [
        Positioned.fill(
          child: RepaintBoundary(
            child: CustomPaint(painter: _Pintor(this, _cuadro)),
          ),
        ),
        SafeArea(
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 8, 0),
              child: Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${p?['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, shadows: sombra)),
                    Text('${p?['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 13.5, color: Color(0xCCFFFFFF), shadows: sombra)),
                  ]),
                ),
                if (VentanaWeb.puedePantallaCompleta)
                  ValueListenableBuilder<bool>(
                    valueListenable: VentanaWeb.completa,
                    builder: (_, si, _) => IconButton(
                      tooltip: si ? 'Salir de pantalla completa' : 'Pantalla completa',
                      icon: Icon(si ? Icons.fullscreen_exit_rounded : Icons.fullscreen_rounded),
                      onPressed: () => VentanaWeb.pantallaCompleta(!si),
                    ),
                  ),
                IconButton(
                  tooltip: 'Cerrar',
                  icon: const Icon(Icons.close_rounded),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ]),
            ),
            const Spacer(),
            // el video de YouTube se tiene que ver: va en una esquina, sin nada encima
            if (youtube)
              const Align(
                alignment: Alignment.centerRight,
                child: Padding(padding: EdgeInsets.all(14), child: SizedBox(width: 240, child: HuecoVideoWeb())),
              ),
            Wrap(alignment: WrapAlignment.center, spacing: 8, runSpacing: 4, children: [
              for (final e in VisualizadorPagina.estilos.entries)
                ChoiceChip(
                  label: Text(e.value),
                  selected: _estilo == e.key,
                  showCheckmark: false,
                  onSelected: (_) {
                    setState(() => _estilo = e.key);
                    _s!.ajustes.poner('visualizador_estilo', e.key);
                  },
                ),
            ]),
            Padding(
              padding: const EdgeInsets.fromLTRB(0, 6, 0, 14),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                IconButton(tooltip: 'Anterior', iconSize: 32, icon: const Icon(Icons.skip_previous_rounded), onPressed: r.anterior),
                IconButton(
                  tooltip: r.estado == EstadoRepro.sonando ? 'Pausar' : 'Reproducir',
                  iconSize: 46,
                  icon: Icon(r.estado == EstadoRepro.sonando ? Icons.pause_circle_rounded : Icons.play_circle_rounded),
                  onPressed: r.alternar,
                ),
                IconButton(tooltip: 'Siguiente', iconSize: 32, icon: const Icon(Icons.skip_next_rounded), onPressed: () => r.siguiente()),
              ]),
            ),
          ]),
        ),
      ]),
    ));
  }
}

class _Pintor extends CustomPainter {
  _Pintor(this.s, this.cuadro) : super(repaint: cuadro);
  final _VisualizadorPaginaState s;
  final ValueNotifier<double> cuadro;

  @override
  bool shouldRepaint(_Pintor o) => true;

  static Color _claro(Color c, double f) => Color.lerp(c, Colors.white, f)!;

  @override
  void paint(Canvas c, Size z) {
    final m = s._modelo;
    final cols = [s._paleta.acento, _claro(s._paleta.contraste, 0.15), _claro(s._paleta.fondo, 0.45)];
    final todo = Offset.zero & z;
    c.drawRect(todo, Paint()
      ..shader = ui.Gradient.linear(Offset.zero, Offset(0, z.height),
          [Color.lerp(s._paleta.fondo, Colors.black, 0.55)!, const Color(0xFF040508)]));
    c.drawRect(todo, Paint()
      ..shader = ui.Gradient.radial(Offset(z.width / 2, z.height * 0.52), math.max(z.width, z.height) * 0.62, [
        cols[0].withValues(alpha: (0.14 + 0.34 * m.energia + 0.10 * m.golpe).clamp(0.0, 1.0)),
        cols[0].withValues(alpha: 0),
      ]));
    switch (s._estilo) {
      case 'barras':
        _barras(c, z, cols, m);
      case 'particulas':
        _particulas(c, z, cols, m);
      default:
        _ondas(c, z, cols, m);
    }
  }

  void _ondas(Canvas c, Size z, List<Color> cols, ModeloAudio m) {
    final t = cuadro.value;
    final y0 = z.height * 0.52;
    final paso = math.max(6.0, z.width / 110);
    final n = (z.width / paso).ceil() + 1;
    for (var k = 0; k < 3; k++) {
      final amp = z.height * (0.035 + 0.20 * m.energia + 0.08 * m.golpe) * (1 - 0.24 * k);
      final frec = 1.25 + 0.75 * k;
      final fase = t * (0.55 + 0.35 * k) * 1.4 + k * 1.7;
      final ruta = Path();
      for (var i = 0; i < n; i++) {
        final x = math.min(z.width, i * paso);
        final u = x / math.max(1.0, z.width);
        final sobre = math.pow(math.sin(math.pi * u).clamp(0.0, 1.0), 0.85);
        // con el sonido de verdad, cada trozo de la onda lleva además su banda
        final banda = m.medida ? m.bandas[(u * (m.n - 1)).round()] * 0.5 : 0.0;
        final y = y0 + amp * sobre * (1 + banda) *
            (math.sin(u * 2 * math.pi * frec + fase) + 0.35 * math.sin(u * 2 * math.pi * frec * 2.3 - fase * 1.4));
        i == 0 ? ruta.moveTo(x, y) : ruta.lineTo(x, y);
      }
      final col = cols[k];
      c.drawPath(
          Path.from(ruta)
            ..lineTo(z.width, z.height)
            ..lineTo(0, z.height)
            ..close(),
          Paint()
            ..shader = ui.Gradient.linear(Offset(0, y0 - amp), Offset(0, z.height),
                [col.withValues(alpha: 0.34 - 0.07 * k), col.withValues(alpha: 0)]));
      c.drawPath(ruta, Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.4 - 0.4 * k
        ..color = _claro(col, 0.2).withValues(alpha: 0.9 - 0.2 * k));
    }
  }

  void _barras(Canvas c, Size z, List<Color> cols, ModeloAudio m) {
    // en un teléfono caben menos barras: se juntan de dos en dos
    final salto = z.width < 600 ? 2 : 1;
    final n = m.n ~/ salto;
    final margen = z.width * 0.07;
    final hueco = (z.width - 2 * margen) / n;
    final ancho = hueco * 0.62;
    final y0 = z.height * 0.56;
    final altoMax = z.height * 0.40;
    final pincel = Paint()
      ..shader = ui.Gradient.linear(Offset(0, y0 - altoMax), Offset(0, y0), [_claro(cols[2], 0.15), cols[0], cols[1]], [0, 0.55, 1]);
    final reflejo = Paint()
      ..shader = ui.Gradient.linear(Offset(0, y0 + 4), Offset(0, y0 + 4 + altoMax * 0.45),
          [cols[0].withValues(alpha: 0.30), cols[0].withValues(alpha: 0)]);
    final tapa = Paint()..color = _claro(cols[2], 0.3).withValues(alpha: 0.9);
    final radio = Radius.circular(ancho / 2);
    for (var i = 0; i < n; i++) {
      var v = 0.0, pico = 0.0;
      for (var k = 0; k < salto; k++) {
        v = math.max(v, m.bandas[i * salto + k]);
        pico = math.max(pico, m.picos[i * salto + k]);
      }
      final x = margen + i * hueco + (hueco - ancho) / 2;
      final alto = math.max(ancho, v * altoMax);
      c.drawRRect(RRect.fromRectAndRadius(Rect.fromLTWH(x, y0 - alto, ancho, alto), radio), pincel);
      c.drawRRect(RRect.fromRectAndRadius(Rect.fromLTWH(x, y0 + 4, ancho, alto * 0.45), radio), reflejo);
      final ty = y0 - math.max(alto, pico * altoMax) - ancho * 0.9;
      c.drawRRect(RRect.fromRectAndRadius(Rect.fromLTWH(x, ty, ancho, math.max(2, ancho * 0.32)), const Radius.circular(1.5)), tapa);
    }
  }

  void _particulas(Canvas c, Size z, List<Color> cols, ModeloAudio m) {
    final centro = Offset(z.width / 2, z.height * 0.47);
    final rmax = math.sqrt(z.width * z.width + z.height * z.height) * 0.5;
    final lado = math.min(z.width, z.height) * 0.34 * (1 + 0.07 * m.golpe + 0.03 * m.energia);
    for (var k = 0; k < 3; k++) {
      c.drawCircle(centro, lado / 2 + 10 + k * 14 + 22 * m.energia * (k + 1) * 0.5, Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..color = cols[k].withValues(alpha: 0.34 - 0.08 * k));
    }
    for (final p in s._partes) {
      final r = lado / 2 + 14 + p.radio * rmax * 0.8;
      final o = centro + Offset(math.cos(p.angulo), math.sin(p.angulo)) * r;
      final col = _claro(cols[(p.color * 3).floor().clamp(0, 2)], 0.2);
      final a = math.pow(1 - p.radio.clamp(0.0, 1.0), 0.7).toDouble();
      final t = p.tamano * (1 + 0.8 * m.golpe);
      c.drawCircle(o, t * 2.6, Paint()
        ..blendMode = BlendMode.plus
        ..color = col.withValues(alpha: a * 0.20));
      c.drawCircle(o, t, Paint()
        ..blendMode = BlendMode.plus
        ..color = col.withValues(alpha: a * 0.85));
    }
    final disco = Rect.fromCircle(center: centro, radius: lado / 2);
    final img = s._portada;
    if (img != null) {
      final corto = math.min(img.width, img.height).toDouble();
      c.save();
      c.clipPath(Path()..addOval(disco));
      c.drawImageRect(
          img,
          Rect.fromLTWH((img.width - corto) / 2, (img.height - corto) / 2, corto, corto),
          disco,
          Paint()..filterQuality = FilterQuality.medium);
      c.restore();
    } else {
      c.drawOval(disco, Paint()
        ..shader = ui.Gradient.radial(centro, lado / 2, [_claro(cols[0], 0.3), cols[1]]));
    }
    c.drawOval(disco, Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..color = _claro(cols[0], 0.4).withValues(alpha: 0.9));
  }
}
