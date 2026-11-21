import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../nucleo/nube.dart';
import '../nucleo/social.dart';
import 'comunes.dart';
import 'tema.dart';

/// Elige una imagen de la galería (bytes, o null si se cancela).
typedef ElegirImagen = Future<Uint8List?> Function();

Future<Uint8List?> elegirImagenDeGaleria() async {
  final r = await FilePicker.pickFiles(type: FileType.image, withData: true);
  return r?.files.firstOrNull?.bytes;
}

/// Hoja inferior para cambiar la portada de una lista: elegir, ver cómo
/// quedará y guardar. Devuelve el JPEG cuadrado listo, o null si se cancela.
Future<Uint8List?> mostrarHojaPortada(BuildContext context,
    {String actual = '', ElegirImagen? elegir, Future<Uint8List> Function(Uint8List)? preparar}) {
  return showModalBottomSheet<Uint8List>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    backgroundColor: C.superficie2,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
    builder: (_) => HojaPortada(
        actual: actual, elegir: elegir ?? elegirImagenDeGaleria,
        preparar: preparar ?? ImagenSocial.cuadrada),
  );
}

class HojaPortada extends StatefulWidget {
  const HojaPortada({super.key, this.actual = '', required this.elegir, required this.preparar});
  final String actual;
  final ElegirImagen elegir;
  final Future<Uint8List> Function(Uint8List) preparar;

  @override
  State<HojaPortada> createState() => _HojaPortadaState();
}

class _HojaPortadaState extends State<HojaPortada> {
  Uint8List? _nueva;
  bool _trabajando = false;
  String? _error;

  Future<void> _elegir() async {
    if (_trabajando) return;
    setState(() {
      _trabajando = true;
      _error = null;
    });
    try {
      final b = await widget.elegir();
      if (b != null) {
        final listo = await widget.preparar(b);
        if (mounted) setState(() => _nueva = listo);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _error = e is ErrorNube ? e.mensaje : 'No se pudo usar esa imagen. Prueba con otra.');
      }
    } finally {
      if (mounted) setState(() => _trabajando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final nueva = _nueva;
    return SafeArea(
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(20, 18, 20, 16 + MediaQuery.viewInsetsOf(context).bottom),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Text('Portada de la lista', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
              const SizedBox(height: 14),
              Center(
                child: LayoutBuilder(builder: (_, c) {
                  final lado = c.maxWidth.clamp(0.0, 240.0).toDouble();
                  return Container(
                    key: const ValueKey('vista_previa_portada'),
                    width: lado, height: lado,
                    clipBehavior: Clip.antiAlias,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: const [BoxShadow(color: Color(0x66000000), blurRadius: 18, offset: Offset(0, 6))],
                    ),
                    child: nueva != null
                        ? Image.memory(nueva, fit: BoxFit.cover, gaplessPlayback: true,
                            cacheWidth: (lado * MediaQuery.devicePixelRatioOf(context)).round())
                        : Portada(url: widget.actual, lado: lado, radio: 16, icono: Icons.queue_music_rounded),
                  );
                }),
              ),
              const SizedBox(height: 12),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: C.error)),
                ),
              if (nueva == null && _error == null)
                const Padding(
                  padding: EdgeInsets.only(bottom: 8),
                  child: Text('Elige una imagen: se recorta al centro en cuadrado.',
                      textAlign: TextAlign.center, style: TextStyle(color: C.texto2)),
                ),
              OutlinedButton.icon(
                onPressed: _trabajando ? null : _elegir,
                icon: _trabajando
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.photo_library_outlined),
                label: Text(nueva == null ? 'Elegir de la galería' : 'Elegir otra'),
              ),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(child: TextButton(
                    onPressed: () => Navigator.pop(context), child: const Text('Cancelar'))),
                const SizedBox(width: 8),
                Expanded(child: FilledButton(
                    onPressed: nueva == null ? null : () => Navigator.pop(context, nueva),
                    child: const Text('Guardar'))),
              ]),
            ]),
          ),
        ),
      ),
    );
  }
}
