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
import '../../nucleo/resumen_semanal.dart';
import '../servicios.dart';
import '../tema.dart';
import 'candado_donador.dart';

String _miles(int n) {
  final s = '$n';
  final b = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) b.write('.');
    b.write(s[i]);
  }
  return b.toString();
}

/// «3 h 20 min», «45 min».
String tiempoEscuchado(int minutos) {
  if (minutos < 60) return '$minutos min';
  final h = minutos ~/ 60, m = minutos % 60;
  return m == 0 ? '$h h' : '$h h $m min';
}

/// La tarjeta del resumen semanal. Se diseña a 360x640 (sale exacta a 1080x1920 al compartirla)
/// y se escala para caber en cualquier pantalla.
class TarjetaSemanal extends StatelessWidget {
  const TarjetaSemanal({super.key, required this.resumen, this.clave});

  final ResumenSemanal resumen;

  /// Para fotografiarla al compartir.
  final GlobalKey? clave;

  static const _colores = [Color(0xFF3B1E6E), Color(0xFF0E4D5C), Color(0xFF0A1B2E)];
  static const _letras = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];

  Widget _etiqueta(String t) => Text(t.toUpperCase(),
      style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, letterSpacing: 1.6, color: Colors.white.withValues(alpha: 0.7)));

  Widget _grafico() {
    final tope = max(1, resumen.minutosPorDia.fold<int>(0, max));
    return SizedBox(
      height: 84,
      child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        for (var i = 0; i < 7; i++)
          Expanded(
            child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
              Container(
                height: max(4.0, 56.0 * resumen.minutosPorDia[i] / tope),
                margin: const EdgeInsets.symmetric(horizontal: 5),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(5),
                  color: resumen.diaTop == i + 1 ? const Color(0xFFFFC857) : Colors.white.withValues(alpha: resumen.minutosPorDia[i] > 0 ? 0.55 : 0.2),
                ),
              ),
              const SizedBox(height: 6),
              Text(_letras[i],
                  style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: Colors.white.withValues(alpha: resumen.diaTop == i + 1 ? 1 : 0.65))),
            ]),
          ),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final r = resumen;
    final a = r.artistaTop;
    final canciones = r.topCanciones;
    // la tarjeta es una imagen de tamaño fijo: no crece con el tamaño de letra del teléfono
    return MediaQuery.withNoTextScaling(
        child: AspectRatio(
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
                gradient: const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: _colores),
              ),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(26, 28, 26, 20),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: _etiqueta('Mi semana en Caudal')),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
                      child: Text(r.rango, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Colors.white)),
                    ),
                  ]),
                  const SizedBox(height: 18),
                  Text(tiempoEscuchado(r.minutos),
                      maxLines: 1,
                      style: const TextStyle(fontSize: 54, fontWeight: FontWeight.w900, color: Colors.white, height: 1, letterSpacing: -1.5)),
                  const SizedBox(height: 4),
                  Text('de música · ${_miles(r.escuchas)} ${r.escuchas == 1 ? 'escucha' : 'escuchas'}',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: Colors.white.withValues(alpha: 0.85))),
                  const SizedBox(height: 18),
                  _grafico(),
                  if (r.diaTop != null) ...[
                    const SizedBox(height: 6),
                    Text('Tu día de más música: el ${r.diaTopNombre}',
                        style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: Colors.white.withValues(alpha: 0.8))),
                  ],
                  const SizedBox(height: 18),
                  if (a != null) ...[
                    _etiqueta('Tu artista de la semana'),
                    const SizedBox(height: 4),
                    Text(a.nombre,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900, color: Colors.white, height: 1.1)),
                    const SizedBox(height: 16),
                  ],
                  _etiqueta('Lo más escuchado'),
                  const SizedBox(height: 8),
                  for (var i = 0; i < canciones.length; i++)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 7),
                      child: Row(children: [
                        SizedBox(
                          width: 22,
                          child: Text('${i + 1}',
                              style: TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w900,
                                  color: i == 0 ? const Color(0xFFFFC857) : Colors.white.withValues(alpha: 0.7))),
                        ),
                        Expanded(
                          child: Text(
                              canciones[i].detalle.isEmpty ? canciones[i].nombre : '${canciones[i].nombre} · ${canciones[i].detalle}',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white)),
                        ),
                        const SizedBox(width: 8),
                        Text('${canciones[i].escuchas}×',
                            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: Colors.white.withValues(alpha: 0.7))),
                      ]),
                    ),
                  const Spacer(),
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
    ));
  }
}

/// «Tu semana en Caudal» (donadores): la tarjeta de la semana lista para compartir o guardar.
class ResumenSemanalPagina extends StatefulWidget {
  const ResumenSemanalPagina({super.key, this.resumen, this.historial, this.ahora});

  /// Ya calculado (lo pasa la tarjeta del domingo en Inicio).
  final ResumenSemanal? resumen;

  /// Para pruebas: si se da, no se lee la colección.
  final List<Escucha>? historial;
  final DateTime? ahora;

  static Future<void> abrir(BuildContext context, {ResumenSemanal? resumen}) => Navigator.of(context, rootNavigator: true)
      .push(MaterialPageRoute<void>(builder: (_) => ResumenSemanalPagina(resumen: resumen)));

  @override
  State<ResumenSemanalPagina> createState() => _ResumenSemanalPaginaState();
}

class _ResumenSemanalPaginaState extends State<ResumenSemanalPagina> {
  final _clave = GlobalKey();
  ResumenSemanal? _r;
  String? _error;
  bool _ocupado = false;

  DateTime get _hoy => widget.ahora ?? DateTime.now();

  @override
  void initState() {
    super.initState();
    _r = widget.resumen;
    if (_r == null) {
      if (widget.historial != null) {
        _r = ResumenSemanal.calcular(widget.historial!, ahora: _hoy);
      } else {
        WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
      }
    }
  }

  Future<void> _cargar() async {
    try {
      final lunes = ResumenSemanal.lunesDe(_hoy);
      final h = await Historial.leer(Caudal.leer(context).coleccion, desde: lunes);
      if (!mounted) return;
      setState(() => _r = ResumenSemanal.calcular(h, ahora: _hoy));
    } catch (_) {
      if (mounted) setState(() => _error = 'No se pudo leer tu historial. Inténtalo otra vez.');
    }
  }

  void _aviso(String t) => ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));

  Future<Uint8List> _png() async {
    await WidgetsBinding.instance.endOfFrame;
    final ro = _clave.currentContext?.findRenderObject();
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
      final nombre = 'caudal_mi_semana_${DateTime.now().millisecondsSinceEpoch}.png';
      XFile adjunto;
      if (kIsWeb) {
        adjunto = XFile.fromData(bytes, mimeType: 'image/png', name: nombre);
      } else {
        final dir = await getTemporaryDirectory();
        final f = File(p.join(dir.path, nombre));
        await f.writeAsBytes(bytes, flush: true);
        adjunto = XFile(f.path, mimeType: 'image/png');
      }
      await SharePlus.instance.share(ShareParams(files: [adjunto], text: 'Mi semana en Caudal'));
    } catch (_) {
      if (mounted) _aviso('No se pudo compartir. Inténtalo otra vez.');
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  Future<void> _guardar() async {
    if (_ocupado) return;
    setState(() => _ocupado = true);
    try {
      await Gal.putImageBytes(await _png(), name: 'caudal_mi_semana_${DateTime.now().millisecondsSinceEpoch}', album: 'Caudal');
      if (mounted) _aviso('Guardada en tu galería (álbum Caudal)');
    } catch (_) {
      if (mounted) _aviso('No se pudo guardar. Revisa el permiso de la galería.');
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    return Scaffold(
      appBar: AppBar(title: const Text('Tu semana en Caudal')),
      body: !esPremiumLetras()
          ? const CandadoDonador(
              icono: Icons.calendar_view_week_rounded,
              titulo: 'Tu semana en Caudal',
              texto:
                  'Cada domingo, una tarjeta con lo más escuchado de tu semana, lista para compartir. Es exclusiva para donadores.')
          : r == null
              ? Center(
                  child: _error != null
                      ? Padding(padding: const EdgeInsets.all(24), child: Text(_error!, textAlign: TextAlign.center, style: estiloSecundario))
                      : const CircularProgressIndicator.adaptive())
              : !r.suficiente
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(28),
                        child: Column(mainAxisSize: MainAxisSize.min, children: [
                          const Icon(Icons.hourglass_empty_rounded, size: 52, color: C.texto2),
                          const SizedBox(height: 14),
                          const Text('Todavía es pronto para tu semana',
                              textAlign: TextAlign.center, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
                          const SizedBox(height: 8),
                          Text(
                              'Esta semana llevas ${r.escuchas} ${r.escuchas == 1 ? 'escucha' : 'escuchas'}. '
                              'Con unas ${ResumenSemanal.escuchasMinimas} ya hay algo que contar.',
                              textAlign: TextAlign.center,
                              style: estiloSecundario),
                        ]),
                      ),
                    )
                  : Column(children: [
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
                          child: Center(child: TarjetaSemanal(resumen: r, clave: _clave)),
                        ),
                      ),
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
}
