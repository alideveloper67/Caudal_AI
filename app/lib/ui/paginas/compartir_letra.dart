import 'dart:io';
import 'dart:math';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../nucleo/coleccion.dart';
import '../comunes.dart';
import '../tema.dart';

/// "Compartir letra": eliges unas líneas y las compartes como una tarjeta con la
/// carátula (como en Spotify) o como texto.
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

  List<String> get _texto => [for (final i in (_elegidas.toList()..sort())) widget.lineas[i].trim()];

  void _alternar(int i) {
    setState(() {
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

  Future<void> _compartirTexto() async {
    if (_elegidas.isEmpty || _ocupado) return;
    final cuerpo = _texto.join('\n');
    await _enviar(() => SharePlus.instance.share(ShareParams(
          text: '$cuerpo\n\n$_titulo${_artista.isEmpty ? '' : ' — $_artista'}\nCon Caudal',
          subject: _titulo,
        )));
  }

  Future<void> _compartirImagen() async {
    if (_elegidas.isEmpty || _ocupado) return;
    await _enviar(() async {
      await WidgetsBinding.instance.endOfFrame;
      final ro = _clave.currentContext?.findRenderObject();
      if (ro is! RenderRepaintBoundary) throw StateError('la tarjeta aún no se pintó');
      if (!mounted) return;
      final escala = min(3.0, max(2.0, MediaQuery.devicePixelRatioOf(context)));
      final imagen = await ro.toImage(pixelRatio: escala);
      final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
      imagen.dispose();
      if (datos == null) throw StateError('no se pudo dibujar la imagen');
      final bytes = datos.buffer.asUint8List();
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
      if (mounted) {
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text('No se pudo compartir: $e')));
      }
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final fondo = HSVColor.fromColor(widget.color).withValue(0.62).withSaturation(0.6).toColor();
    final abajo = Color.lerp(fondo, Colors.black, 0.35)!;
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
                constraints: const BoxConstraints(maxWidth: 420),
                child: RepaintBoundary(
                  key: _clave,
                  child: Container(
                    padding: const EdgeInsets.fromLTRB(24, 24, 24, 20),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18),
                      gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [fondo, abajo]),
                    ),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                      Row(children: [
                        Portada(url: url, lado: 54, radio: 8),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(_titulo, maxLines: 2, overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.white)),
                            if (_artista.isNotEmpty)
                              Text(_artista, maxLines: 1, overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontSize: 13, color: Color(0xCCFFFFFF))),
                          ]),
                        ),
                      ]),
                      const SizedBox(height: 22),
                      if (_elegidas.isEmpty)
                        const Text('Elige las líneas que quieres compartir.',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Color(0xCCFFFFFF)))
                      else
                        for (final l in _texto)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Text(l,
                                style: const TextStyle(
                                    fontSize: 22, fontWeight: FontWeight.w900, height: 1.2, color: Colors.white)),
                          ),
                      const SizedBox(height: 18),
                      Row(children: [
                        Image.asset('assets/logo/caudal.png', width: 18, height: 18),
                        const SizedBox(width: 6),
                        const Text('Caudal', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Colors.white)),
                      ]),
                    ]),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text('Toca las líneas para elegirlas (${_elegidas.length} de $_maximo)',
                style: estiloSecundario),
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
            child: Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _elegidas.isEmpty || _ocupado ? null : _compartirTexto,
                  icon: const Icon(Icons.notes_rounded),
                  label: const Text('Texto'),
                  style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48), shape: const StadiumBorder()),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: FilledButton.icon(
                  onPressed: _elegidas.isEmpty || _ocupado ? null : _compartirImagen,
                  icon: _ocupado
                      ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.2, color: C.acentoTexto))
                      : const Icon(Icons.image_rounded),
                  label: const Text('Compartir imagen'),
                  style: FilledButton.styleFrom(
                      backgroundColor: C.acento, foregroundColor: C.acentoTexto,
                      minimumSize: const Size.fromHeight(48), shape: const StadiumBorder()),
                ),
              ),
            ]),
          ),
        ),
      ]),
    );
  }
}
