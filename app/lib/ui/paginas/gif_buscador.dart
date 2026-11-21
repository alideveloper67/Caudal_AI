import 'dart:async';
import 'dart:typed_data';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show FilteringTextInputFormatter;

import '../../nucleo/gif_perfil.dart';
import '../../nucleo/nube.dart';
import '../tema.dart';

/// Insignia pequeña que deja claro que los GIF son de donadores.
class InsigniaGifDonador extends StatelessWidget {
  const InsigniaGifDonador({super.key, this.sobreAcento = false});

  /// Si va dentro de un botón de color de acento, usa tonos que se lean encima.
  final bool sobreAcento;

  @override
  Widget build(BuildContext context) {
    final fondo = sobreAcento ? Colors.black.withValues(alpha: 0.16) : const Color(0xFFF5C451).withValues(alpha: 0.18);
    final texto = sobreAcento ? C.acentoTexto : const Color(0xFFF5C451);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
      decoration: BoxDecoration(color: fondo, borderRadius: BorderRadius.circular(999)),
      child: Text('GIF · Donador',
          maxLines: 1, style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: texto, letterSpacing: 0.2)),
    );
  }
}

/// Vista previa de un GIF ya descargado: redonda para la foto, 8:3 para el fondo.
class VistaPreviaGif extends StatelessWidget {
  const VistaPreviaGif({super.key, required this.bytes, required this.esFoto, this.lado = 200});
  final Uint8List bytes;
  final bool esFoto;
  final double lado;

  @override
  Widget build(BuildContext context) {
    final imagen = Image.memory(bytes, fit: BoxFit.cover, gaplessPlayback: true);
    if (esFoto) {
      return Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: C.acento, width: 2.5)),
        child: ClipOval(child: SizedBox(width: lado, height: lado, child: imagen)),
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: AspectRatio(aspectRatio: 8 / 3, child: imagen),
    );
  }
}

/// Hoja a pantalla casi completa para buscar un GIF en internet. Se cierra con
/// los bytes del GIF elegido (ya descargado y confirmado) o con `null`.
class HojaBuscarGif extends StatefulWidget {
  const HojaBuscarGif({super.key, required this.buscador, required this.esFoto, this.retraso = const Duration(milliseconds: 350)});
  final GifBuscador buscador;
  final bool esFoto;
  final Duration retraso;

  @override
  State<HojaBuscarGif> createState() => _HojaBuscarGifState();
}

class _HojaBuscarGifState extends State<HojaBuscarGif> {
  static const _llegara = 'La búsqueda de GIF llegará muy pronto. Mientras, puedes subir un GIF desde tu dispositivo.';

  final _campo = TextEditingController();
  final _scroll = ScrollController();
  Timer? _espera;
  List<GifItem> _items = const [];
  String _siguiente = '';
  String _aviso = '';
  String? _fallo;
  bool _sinClave = false;
  bool _cargando = true;
  bool _cargandoMas = false;
  int _gen = 0;

  // elegido
  GifItem? _bajando;
  Uint8List? _elegido;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      if (_scroll.hasClients && _scroll.position.extentAfter < 500) _mas();
    });
    _buscar();
  }

  @override
  void dispose() {
    _espera?.cancel();
    _campo.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _alEscribir(String _) {
    _espera?.cancel();
    setState(() => _cargando = true);
    _espera = Timer(widget.retraso, _buscar);
  }

  Future<void> _buscar() async {
    final gen = ++_gen;
    setState(() {
      _cargando = true;
      _fallo = null;
    });
    try {
      final p = await widget.buscador.buscar(_campo.text);
      if (!mounted || gen != _gen) return;
      setState(() {
        _cargando = false;
        _sinClave = p.sinClave;
        _fallo = p.error.isNotEmpty && !p.sinClave ? _mensajeDe(p.error) : null;
        _items = p.items;
        _siguiente = p.siguiente;
        _aviso = p.aviso;
      });
    } catch (e) {
      if (!mounted || gen != _gen) return;
      setState(() {
        _cargando = false;
        _items = const [];
        _siguiente = '';
        _fallo = e is SinConexion ? 'Parece que no hay internet. Revisa tu conexión e inténtalo otra vez.' : 'No se pudo buscar ahora. Inténtalo de nuevo en un momento.';
      });
    }
  }

  String _mensajeDe(String error) => switch (error) {
        'no_permitido' || 'bloqueado' || 'busqueda_no_permitida' =>
          'Esa búsqueda no está permitida. Prueba con otras palabras.',
        _ => 'No se pudo buscar ahora. Inténtalo de nuevo en un momento.',
      };

  Future<void> _mas() async {
    if (_cargandoMas || _cargando || _siguiente.isEmpty || _fallo != null) return;
    final gen = _gen;
    setState(() => _cargandoMas = true);
    try {
      final p = await widget.buscador.buscar(_campo.text, pos: _siguiente);
      if (!mounted || gen != _gen) return;
      final ya = {for (final i in _items) i.id};
      setState(() {
        _items = [..._items, for (final i in p.items) if (!ya.contains(i.id)) i];
        _siguiente = p.siguiente;
        if (p.aviso.isNotEmpty) _aviso = p.aviso;
        _cargandoMas = false;
      });
    } catch (_) {
      if (mounted && gen == _gen) {
        setState(() {
          _cargandoMas = false;
          _siguiente = '';
        });
      }
    }
  }

  Future<void> _elegir(GifItem g) async {
    if (_bajando != null) return;
    setState(() => _bajando = g);
    try {
      final b = await widget.buscador.bajar(g);
      if (!mounted) return;
      setState(() {
        _elegido = b;
        _bajando = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _bajando = null);
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(
          content: Text(e is ErrorNube ? e.mensaje : e is SinConexion ? 'Parece que no hay internet. Inténtalo otra vez.' : 'No se pudo descargar ese GIF. Prueba con otro.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final alto = MediaQuery.sizeOf(context).height * 0.94;
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SizedBox(
        height: alto,
        child: Column(children: [
          const SizedBox(height: 10),
          Container(width: 38, height: 4, decoration: BoxDecoration(color: C.borde, borderRadius: BorderRadius.circular(4))),
          Expanded(child: _elegido != null ? _previa() : _lista()),
        ]),
      ),
    );
  }

  // ------------------------------------------------------------ vista previa

  Widget _previa() => Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Esp.xl),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(widget.esFoto ? 'Así se verá tu foto' : 'Así se verá tu fondo',
                  textAlign: TextAlign.center, style: estiloTituloSeccion.copyWith(fontSize: 18)),
              const SizedBox(height: Esp.l),
              VistaPreviaGif(bytes: _elegido!, esFoto: widget.esFoto, lado: 180),
              const SizedBox(height: Esp.xl),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () => Navigator.of(context).pop(_elegido),
                  icon: const Icon(Icons.check_rounded),
                  label: const Text('Usar este GIF'),
                ),
              ),
              const SizedBox(height: 6),
              TextButton(onPressed: () => setState(() => _elegido = null), child: const Text('Elegir otro')),
            ]),
          ),
        ),
      );

  // ------------------------------------------------------------ búsqueda

  Widget _lista() {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(Esp.l, Esp.m, Esp.l, 6),
        child: TextField(
          controller: _campo,
          onChanged: _alEscribir,
          onSubmitted: (_) {
            _espera?.cancel();
            _buscar();
          },
          textInputAction: TextInputAction.search,
          // solo palabras para buscar: nada de pegar enlaces
          maxLength: 60,
          inputFormatters: [FilteringTextInputFormatter.deny(RegExp(r'[/\:]'))],
          decoration: InputDecoration(
            hintText: 'Busca un GIF',
            counterText: '',
            prefixIcon: const Icon(Icons.search_rounded),
            filled: true,
            fillColor: C.superficie2,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide.none),
          ),
        ),
      ),
      if (_aviso.isNotEmpty)
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.l, 0, Esp.l, 6),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              const Icon(Icons.info_outline_rounded, size: 18, color: C.texto2),
              const SizedBox(width: 8),
              Expanded(child: Text(_aviso, style: estiloSecundario)),
            ]),
          ),
        ),
      Expanded(child: _cuerpo()),
      Padding(
        padding: const EdgeInsets.only(top: 2, bottom: 8),
        child: Text('Powered by GIPHY',
            key: const ValueKey('atribucion-giphy'),
            style: estiloDetalle.copyWith(fontSize: 10.5, letterSpacing: 0.4)),
      ),
    ]);
  }

  Widget _mensaje(IconData icono, String texto, {String? accion, VoidCallback? alAccion}) => Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Esp.xl),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icono, size: 40, color: C.texto2),
            const SizedBox(height: 12),
            Text(texto, textAlign: TextAlign.center, style: estiloSecundario),
            if (accion != null) ...[const SizedBox(height: 8), TextButton(onPressed: alAccion, child: Text(accion))],
          ]),
        ),
      );

  Widget _cuerpo() {
    if (_sinClave) return _mensaje(Icons.gif_box_outlined, _llegara);
    if (_cargando && _items.isEmpty) return const Center(child: CircularProgressIndicator());
    if (_fallo != null) return _mensaje(Icons.cloud_off_rounded, _fallo!, accion: 'Reintentar', alAccion: _buscar);
    if (_items.isEmpty) {
      return _mensaje(Icons.search_off_rounded,
          _campo.text.trim().isEmpty ? 'Ahora mismo no hay GIF para mostrar.' : 'No encontramos GIF con esa búsqueda. Prueba con otra palabra.');
    }
    return LayoutBuilder(builder: (context, caja) {
      final cols = caja.maxWidth >= 560 ? 3 : 2;
      return Stack(children: [
        GridView.builder(
          controller: _scroll,
          padding: const EdgeInsets.fromLTRB(Esp.l, 6, Esp.l, Esp.xl),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: cols,
            mainAxisSpacing: 8,
            crossAxisSpacing: 8,
            childAspectRatio: widget.esFoto ? 1 : 4 / 3,
          ),
          itemCount: _items.length + (_cargandoMas ? 1 : 0),
          itemBuilder: (_, i) {
            if (i >= _items.length) return const Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2)));
            final g = _items[i];
            return _Baldosa(gif: g, bajando: _bajando?.id == g.id, alPulsar: () => _elegir(g));
          },
        ),
        if (_cargando)
          const Positioned(left: 0, right: 0, top: 0, child: LinearProgressIndicator(minHeight: 2)),
      ]);
    });
  }
}

class _Baldosa extends StatelessWidget {
  const _Baldosa({required this.gif, required this.bajando, required this.alPulsar});
  final GifItem gif;
  final bool bajando;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: gif.titulo.isEmpty ? 'GIF' : 'GIF: ${gif.titulo}',
        child: ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: Material(
            color: C.superficie2,
            child: InkWell(
              onTap: alPulsar,
              child: Stack(fit: StackFit.expand, children: [
                LayoutBuilder(builder: (_, c) => CachedNetworkImage(
                  imageUrl: gif.vista,
                  fit: BoxFit.cover,
                  memCacheWidth: (c.maxWidth * MediaQuery.devicePixelRatioOf(context)).round(),
                  fadeInDuration: const Duration(milliseconds: 120),
                  placeholder: (_, _) => ColoredBox(color: C.superficie2),
                  errorWidget: (_, _, _) => const Center(child: Icon(Icons.broken_image_outlined, color: C.texto2)),
                )),
                if (bajando)
                  ColoredBox(
                    color: Colors.black54,
                    child: const Center(child: SizedBox(width: 26, height: 26, child: CircularProgressIndicator(strokeWidth: 2.5))),
                  ),
              ]),
            ),
          ),
        ),
      );
}
