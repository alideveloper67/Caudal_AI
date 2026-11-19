import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:gal/gal.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../nucleo/mixes.dart';
import '../../nucleo/premium_letras.dart';
import '../../nucleo/resumen_anual.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'donar.dart';

/// «Tu año en Caudal»: cinco tarjetas verticales con lo que escuchaste en el año (minutos,
/// canción y artista, tu top, tu ánimo, tu racha). Es para donadores; los demás ven una vista
/// previa borrosa con un candado. Todo sale de las escuchas guardadas en el teléfono, así que
/// funciona sin conexión.
class ResumenAnualPagina extends StatefulWidget {
  const ResumenAnualPagina({super.key, this.historial, this.ahora});

  /// Para pruebas: si se da, no se lee la colección.
  final List<Escucha>? historial;
  final DateTime? ahora;

  static Future<void> abrir(BuildContext context) =>
      Navigator.of(context, rootNavigator: true).push(MaterialPageRoute<void>(builder: (_) => const ResumenAnualPagina()));

  @override
  State<ResumenAnualPagina> createState() => _ResumenAnualPaginaState();
}

const _meses = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
];

String _fecha(DateTime d) => '${d.day} de ${_meses[d.month - 1]}';

String _miles(int n) {
  final s = '$n';
  final b = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write('.');
    b.write(s[i]);
  }
  return b.toString();
}

class _ResumenAnualPaginaState extends State<ResumenAnualPagina> {
  static const _paginas = 5;
  final _pc = PageController();
  final _claves = List.generate(_paginas, (_) => GlobalKey());
  ResumenAnual? _r;
  String? _error;
  int _pagina = 0;
  bool _ocupado = false;

  DateTime get _hoy => widget.ahora ?? DateTime.now();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
  }

  @override
  void dispose() {
    _pc.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    try {
      final anio = anioDelResumen(_hoy);
      final h = widget.historial ?? await Historial.leer(Caudal.leer(context).coleccion, desde: DateTime(anio));
      if (!mounted) return;
      setState(() => _r = ResumenAnual.calcular(h, anio: anio, ahora: _hoy));
    } catch (e) {
      if (mounted) setState(() => _error = 'No se pudo leer tu historial: $e');
    }
  }

  void _aviso(String t) => ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));

  /// La tarjeta que se ve como PNG de 1080x1920.
  Future<Uint8List> _png() async {
    await WidgetsBinding.instance.endOfFrame;
    final ro = _claves[_pagina].currentContext?.findRenderObject();
    if (ro is! RenderRepaintBoundary) throw StateError('la tarjeta aún no se pintó');
    final imagen = await ro.toImage(pixelRatio: 3);
    final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
    imagen.dispose();
    if (datos == null) throw StateError('no se pudo dibujar la imagen');
    return datos.buffer.asUint8List();
  }

  Future<void> _compartir() async {
    if (_ocupado) return;
    setState(() => _ocupado = true);
    try {
      final bytes = await _png();
      final nombre = 'caudal_mi_anio_${DateTime.now().millisecondsSinceEpoch}.png';
      XFile adjunto;
      if (kIsWeb) {
        adjunto = XFile.fromData(bytes, mimeType: 'image/png', name: nombre);
      } else {
        final dir = await getTemporaryDirectory();
        final f = File(p.join(dir.path, nombre));
        await f.writeAsBytes(bytes, flush: true);
        adjunto = XFile(f.path, mimeType: 'image/png');
      }
      await SharePlus.instance.share(ShareParams(files: [adjunto], text: 'Mi año en Caudal ${_r?.anio ?? ''}'));
    } catch (e) {
      if (mounted) _aviso('No se pudo compartir: $e');
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  Future<void> _guardar() async {
    if (_ocupado) return;
    setState(() => _ocupado = true);
    try {
      await Gal.putImageBytes(await _png(), name: 'caudal_mi_anio_${DateTime.now().millisecondsSinceEpoch}', album: 'Caudal');
      if (mounted) _aviso('Guardada en tu galería (álbum Caudal)');
    } catch (e) {
      if (mounted) _aviso('No se pudo guardar: $e');
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  List<Widget> _tarjetas(ResumenAnual r) => [
        _TarjetaAnual(clave: _claves[0], colores: const [Color(0xFF5B2A86), Color(0xFF1B1F4B)], anio: r.anio, hijo: _portada(r)),
        _TarjetaAnual(clave: _claves[1], colores: const [Color(0xFF0F5C6E), Color(0xFF0B1E33)], anio: r.anio, hijo: _cancionYArtista(r)),
        _TarjetaAnual(clave: _claves[2], colores: const [Color(0xFF8A2D5B), Color(0xFF241226)], anio: r.anio, hijo: _top(r)),
        _TarjetaAnual(clave: _claves[3], colores: const [Color(0xFF2E5E3E), Color(0xFF0C1F17)], anio: r.anio, hijo: _animo(r)),
        _TarjetaAnual(clave: _claves[4], colores: const [Color(0xFFB4561F), Color(0xFF2A1208)], anio: r.anio, hijo: _racha(r)),
      ];

  // ---- el contenido de cada tarjeta (se diseña a 360x640 y se escala)

  Widget _grande(String t, {double tam = 64, Color color = Colors.white}) => Text(t,
      textAlign: TextAlign.center,
      style: TextStyle(fontSize: tam, fontWeight: FontWeight.w900, color: color, height: 1.0, letterSpacing: -1));

  Widget _etiqueta(String t) => Text(t.toUpperCase(),
      textAlign: TextAlign.center,
      style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, letterSpacing: 1.6, color: Colors.white.withValues(alpha: 0.75)));

  Widget _frase(String t, {double tam = 16}) => Text(t,
      textAlign: TextAlign.center,
      style: TextStyle(fontSize: tam, fontWeight: FontWeight.w600, color: Colors.white.withValues(alpha: 0.88), height: 1.3));

  Widget _portada(ResumenAnual r) => Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        _etiqueta('Escuchaste'),
        const SizedBox(height: 14),
        _grande(_miles(r.minutos), tam: r.minutos >= 100000 ? 56 : 76),
        const SizedBox(height: 6),
        const Text('minutos de música',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: Colors.white)),
        const SizedBox(height: 26),
        _frase('Son ${_miles(r.horas)} horas, ${_miles(r.escuchas)} canciones sonando en ${r.diasConMusica} días distintos.'),
        const SizedBox(height: 10),
        _frase('${_miles(r.cancionesDistintas)} canciones y ${_miles(r.artistasDistintos)} artistas diferentes.', tam: 14),
      ]);

  Widget _cancionYArtista(ResumenAnual r) {
    final c = r.cancionTop, a = r.artistaTop;
    return Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      _etiqueta('Tu canción del año'),
      const SizedBox(height: 14),
      if (c != null) ...[
        Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.45), blurRadius: 26, offset: const Offset(0, 10))],
          ),
          child: Portada(url: c.miniatura, lado: 150, radio: 16),
        ),
        const SizedBox(height: 14),
        Text(c.nombre,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.white, height: 1.1)),
        if (c.detalle.isNotEmpty) _frase(c.detalle, tam: 14),
        const SizedBox(height: 4),
        _frase('La escuchaste ${_miles(c.escuchas)} ${c.escuchas == 1 ? 'vez' : 'veces'}.'),
      ],
      const SizedBox(height: 26),
      _etiqueta('Tu artista del año'),
      const SizedBox(height: 8),
      if (a != null) ...[
        Text(a.nombre,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900, color: Colors.white, height: 1.1)),
        const SizedBox(height: 4),
        _frase('${_miles(a.escuchas)} escuchas · ${_miles(a.minutos)} min'),
      ],
    ]);
  }

  Widget _top(ResumenAnual r) {
    final lista = r.topArtistas;
    final tope = lista.isEmpty ? 1 : max(1, lista.first.escuchas);
    return Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      _etiqueta('Tus 5 artistas'),
      const SizedBox(height: 20),
      for (final (i, a) in lista.indexed)
        Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: Row(children: [
            SizedBox(width: 34, child: Text('${i + 1}', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900, color: Colors.white))),
            const SizedBox(width: 6),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(a.nombre,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: Colors.white)),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: a.escuchas / tope,
                    minHeight: 6,
                    color: Colors.white,
                    backgroundColor: Colors.white.withValues(alpha: 0.18),
                  ),
                ),
                const SizedBox(height: 2),
                Text('${_miles(a.escuchas)} escuchas', style: TextStyle(fontSize: 12, color: Colors.white.withValues(alpha: 0.7))),
              ]),
            ),
          ]),
        ),
    ]);
  }

  Widget _animo(ResumenAnual r) {
    final icono = switch (r.animoDominante) {
      'triste' => Icons.cloud_rounded,
      'fiesta' => Icons.celebration_rounded,
      'romantica' => Icons.favorite_rounded,
      _ => Icons.graphic_eq_rounded,
    };
    return Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      _etiqueta('Tu ánimo musical'),
      const SizedBox(height: 18),
      Icon(icono, size: 84, color: Colors.white),
      const SizedBox(height: 16),
      if (r.animoDominante.isNotEmpty) ...[
        _grande('Año ${r.animoTexto}', tam: 38),
        const SizedBox(height: 6),
        Text('${r.animoPorcentaje} % de las canciones que lo dicen en su título',
            textAlign: TextAlign.center, style: TextStyle(fontSize: 12.5, color: Colors.white.withValues(alpha: 0.7))),
        const SizedBox(height: 18),
      ],
      _frase(r.animoFrase),
    ]);
  }

  Widget _racha(ResumenAnual r) => Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        _etiqueta('Tu mejor racha'),
        const SizedBox(height: 12),
        _grande('${r.rachaMasLarga}', tam: 80),
        Text(r.rachaMasLarga == 1 ? 'día seguido' : 'días seguidos',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: Colors.white)),
        const SizedBox(height: 28),
        _etiqueta('Tu día de más música'),
        const SizedBox(height: 8),
        if (r.diaTop != null) ...[
          _grande(_fecha(r.diaTop!), tam: 28),
          const SizedBox(height: 4),
          _frase('${_miles(r.minutosDiaTop)} minutos ese día'),
        ],
        const SizedBox(height: 26),
        _frase('Hubo música en ${r.diasConMusica} días de ${r.anio}. ¡Gracias por escuchar con Caudal!'),
      ]);

  // ---- la pantalla

  @override
  Widget build(BuildContext context) {
    final r = _r;
    final premium = esPremiumLetras();
    return Scaffold(
      appBar: AppBar(title: const Text('Tu año en Caudal')),
      body: r == null
          ? Center(
              child: _error != null
                  ? Padding(padding: const EdgeInsets.all(24), child: Text(_error!, textAlign: TextAlign.center, style: estiloSecundario))
                  : const CircularProgressIndicator.adaptive())
          : !r.suficiente && premium
              ? _PocasEscuchas(r: r)
              : Column(children: [
                  Expanded(
                    child: Stack(children: [
                      Positioned.fill(
                        child: premium
                            ? _visor(r)
                            : ImageFiltered(
                                imageFilter: ui.ImageFilter.blur(sigmaX: 9, sigmaY: 9, tileMode: TileMode.decal),
                                child: IgnorePointer(child: _visor(r.suficiente ? r : _muestra(r.anio))),
                              ),
                      ),
                      if (!premium) Positioned.fill(child: _Candado(alDonar: () => mostrarDonar(context))),
                    ]),
                  ),
                  if (premium)
                    SafeArea(
                      top: false,
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(20, 4, 20, 10),
                        child: Row(children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _ocupado ? null : _guardar,
                              icon: const Icon(Icons.download_rounded, size: 18),
                              label: const Text('Guardar'),
                              style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(46), shape: const StadiumBorder()),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            flex: 2,
                            child: FilledButton.icon(
                              onPressed: _ocupado ? null : _compartir,
                              icon: const Icon(Icons.ios_share_rounded, size: 18),
                              label: const Text('Compartir'),
                              style: FilledButton.styleFrom(
                                  backgroundColor: C.acento,
                                  foregroundColor: C.acentoTexto,
                                  minimumSize: const Size.fromHeight(46),
                                  shape: const StadiumBorder()),
                            ),
                          ),
                        ]),
                      ),
                    ),
                ]),
    );
  }

  /// Datos de ejemplo para la vista previa borrosa de quien aún no tiene suficientes escuchas.
  ResumenAnual _muestra(int anio) => ResumenAnual(
        anio: anio,
        escuchas: 1840,
        minutos: 6120,
        diasConMusica: 212,
        rachaMasLarga: 18,
        cancionTop: const PuestoAnual(nombre: 'Tu canción', detalle: 'Tu artista', escuchas: 64),
        artistaTop: const PuestoAnual(nombre: 'Tu artista', escuchas: 310, minutos: 980),
        topArtistas: [
          for (var i = 0; i < 5; i++) PuestoAnual(nombre: 'Artista ${i + 1}', escuchas: 300 - i * 45)
        ],
        animoDominante: 'fiesta',
        animoPorcentaje: 41,
        diaTop: DateTime(anio, 6, 14),
        minutosDiaTop: 310,
        artistasDistintos: 190,
        cancionesDistintas: 760,
      );

  Widget _visor(ResumenAnual r) {
    final tarjetas = _tarjetas(r);
    return Column(children: [
      Expanded(
        child: PageView(
          controller: _pc,
          onPageChanged: (i) => setState(() => _pagina = i),
          children: [
            for (final t in tarjetas)
              Padding(padding: const EdgeInsets.fromLTRB(20, 8, 20, 8), child: Center(child: t)),
          ],
        ),
      ),
      Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          for (var i = 0; i < _paginas; i++)
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: const EdgeInsets.symmetric(horizontal: 3),
              width: i == _pagina ? 18 : 6,
              height: 6,
              decoration: BoxDecoration(
                color: i == _pagina ? C.acento : C.texto3,
                borderRadius: BorderRadius.circular(3),
              ),
            ),
        ]),
      ),
    ]);
  }
}

/// Una tarjeta del resumen: se diseña a 360x640 (así sale exacta a 1080x1920) y se
/// escala para que quepa en cualquier pantalla.
class _TarjetaAnual extends StatelessWidget {
  const _TarjetaAnual({required this.clave, required this.colores, required this.anio, required this.hijo});
  final GlobalKey clave;
  final List<Color> colores;
  final int anio;
  final Widget hijo;

  @override
  Widget build(BuildContext context) => AspectRatio(
        aspectRatio: 9 / 16,
        child: FittedBox(
          fit: BoxFit.contain,
          child: RepaintBoundary(
            key: clave,
            child: SizedBox(
              width: 360,
              height: 640,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(24),
                  gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: colores),
                ),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(28, 30, 28, 22),
                  child: Column(children: [
                    Text('TU AÑO EN CAUDAL $anio',
                        style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, letterSpacing: 1.8, color: Colors.white.withValues(alpha: 0.6))),
                    Expanded(child: Center(child: hijo)),
                    Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Image.asset('assets/logo/caudal.png', width: 18, height: 18),
                      const SizedBox(width: 6),
                      Text('Caudal', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: Colors.white.withValues(alpha: 0.85))),
                    ]),
                  ]),
                ),
              ),
            ),
          ),
        ),
      );
}

/// Sobre la vista previa borrosa: qué es y cómo conseguirlo.
class _Candado extends StatelessWidget {
  const _Candado({required this.alDonar});
  final VoidCallback alDonar;

  @override
  Widget build(BuildContext context) => Center(
        child: Container(
          margin: const EdgeInsets.all(24),
          padding: const EdgeInsets.fromLTRB(22, 20, 22, 14),
          decoration: BoxDecoration(color: C.superficie.withValues(alpha: 0.94), borderRadius: BorderRadius.circular(20)),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.lock_rounded, size: 32, color: C.texto2),
            const SizedBox(height: 10),
            const Text('Tu año en Caudal', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
            const SizedBox(height: 6),
            const Text(
                'Un resumen en tarjetas con tus minutos, tu canción y artista del año, tu ánimo y tu racha, listo para compartir. Es exclusivo para donadores.',
                textAlign: TextAlign.center,
                style: estiloSecundario),
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: alDonar,
              icon: const Icon(Icons.favorite_rounded, size: 18),
              label: const Text('Donar aquí'),
              style: FilledButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto, shape: const StadiumBorder()),
            ),
          ]),
        ),
      );
}

/// Con muy pocas escuchas el resumen no cuenta nada: se explica con cariño.
class _PocasEscuchas extends StatelessWidget {
  const _PocasEscuchas({required this.r});
  final ResumenAnual r;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.hourglass_empty_rounded, size: 52, color: C.texto2),
            const SizedBox(height: 14),
            const Text('Todavía es pronto para tu resumen',
                textAlign: TextAlign.center, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
            const SizedBox(height: 8),
            Text(
              r.vacio
                  ? 'Aún no hay escuchas de ${r.anio}. Pon música y cuando junte un poco volvemos a mirar.'
                  : 'Llevas ${r.escuchas} ${r.escuchas == 1 ? 'escucha' : 'escuchas'} en ${r.diasConMusica} '
                      '${r.diasConMusica == 1 ? 'día' : 'días'}. Con unas ${ResumenAnual.escuchasMinimas} escuchas en '
                      '${ResumenAnual.diasMinimos} días distintos ya podemos contarte tu año.',
              textAlign: TextAlign.center,
              style: estiloSecundario,
            ),
          ]),
        ),
      );
}
