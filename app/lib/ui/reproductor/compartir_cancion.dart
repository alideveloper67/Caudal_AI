// «Compartir»: la hoja que sale del reproductor para mandar una imagen bonita de la
// canción que suena (estados de WhatsApp, historias de Instagram, chats...). Se elige el
// diseño deslizando, se ajustan tres opciones sencillas y se comparte o se guarda.
// La última elección se recuerda en el teléfono.

import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:gal/gal.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../nucleo/mascota_app.dart';
import '../../nucleo/premium_letras.dart';
import '../paginas/donar.dart';
import '../tema.dart';
import 'tarjetas_compartir.dart';

/// Abre la hoja para compartir. [datos] puede tardar un poco (la letra, los colores):
/// mientras tanto la hoja ya está abierta y muestra que se está preparando.
Future<void> mostrarCompartirCancion(BuildContext context,
    {required Future<DatosCompartir> datos, bool Function()? esDonador}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    useRootNavigator: true,
    backgroundColor: C.superficie,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
    builder: (_) => HojaCompartirCancion(datos: datos, esDonador: esDonador),
  );
}

/// Las preferencias de la hoja (lo último que se eligió).
class _Prefs {
  static const diseno = 'compartir_cancion_diseno';
  static const formato = 'compartir_cancion_formato';
  static const mascota = 'compartir_cancion_mascota';
  static const letra = 'compartir_cancion_letra';
}

class HojaCompartirCancion extends StatefulWidget {
  const HojaCompartirCancion({super.key, required this.datos, this.esDonador});
  final Future<DatosCompartir> datos;

  /// ¿La cuenta tiene los beneficios de donador o fundador? (por defecto, el estado de siempre).
  final bool Function()? esDonador;

  @override
  State<HojaCompartirCancion> createState() => _HojaCompartirCancionState();
}

class _HojaCompartirCancionState extends State<HojaCompartirCancion> with SingleTickerProviderStateMixin {
  /// Mueve los brillos y partículas de los diseños exclusivos (una vuelta cada 6 s).
  late final AnimationController _brillo =
      AnimationController(vsync: this, duration: const Duration(seconds: 6), value: 0.3);

  bool get _donador => (widget.esDonador ?? esPremiumLetras)();
  bool get _bloqueado => _diseno.exclusivo && !_donador;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // con «quitar animaciones» los exclusivos se quedan quietos en un buen momento
    if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) {
      _brillo.stop();
      _brillo.value = 0.3;
    } else if (!_brillo.isAnimating) {
      _brillo.repeat();
    }
  }

  DatosCompartir? _d;
  bool _fallo = false;

  DisenoCompartir _diseno = DisenoCompartir.historia;
  FormatoCompartir _formato = FormatoCompartir.historia;
  bool _mascota = true, _letra = true;

  final _claves = {for (final d in DisenoCompartir.values) d: GlobalKey()};
  PageController? _paginas;
  bool _ocupado = false;
  String? _aviso;
  bool _avisoBueno = false;
  Timer? _relojAviso;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _diseno = DisenoCompartir.porNombre(prefs.getString(_Prefs.diseno)) ?? _diseno;
      if (_diseno.exclusivo && !_donador) _diseno = DisenoCompartir.historia;
      _formato = FormatoCompartir.porNombre(prefs.getString(_Prefs.formato)) ?? _formato;
      _mascota = prefs.getBool(_Prefs.mascota) ?? true;
      _letra = prefs.getBool(_Prefs.letra) ?? true;
    } catch (_) {
      // sin preferencias se empieza por lo de siempre
    }
    DatosCompartir d;
    try {
      d = await widget.datos;
    } catch (_) {
      if (mounted) setState(() => _fallo = true);
      return;
    }
    if (!mounted) return;
    // la mascota se pinta con su hoja de dibujos (ya decodificada para la barra del reproductor)
    final m = d.mascota;
    if (m != null && d.hojaMascota == null) {
      final hoja = await MascotaApp.i.imagen(m.clave);
      if (hoja != null) d = d.copiar(hojaMascota: hoja);
    }
    if (!mounted) return;
    setState(() {
      _d = d;
      final lista = _disenos;
      if (!lista.contains(_diseno)) _diseno = lista.first;
      _paginas = PageController(viewportFraction: 0.8, initialPage: lista.indexOf(_diseno));
    });
  }

  @override
  void dispose() {
    _relojAviso?.cancel();
    _brillo.dispose();
    _paginas?.dispose();
    // la ilustracion del escenario se pinto solo para esta hoja: se libera al cerrarla
    _d?.escenario?.dispose();
    super.dispose();
  }

  /// Los diseños que tienen sentido con esta canción (sin letra, no hay diseño «Letra»).
  List<DisenoCompartir> get _disenos => [
        for (final d in DisenoCompartir.values)
          if (d != DisenoCompartir.letra || (_d?.hayLetra ?? false)) d,
      ];

  Future<void> _guardarPref(Future<bool> Function(SharedPreferences) f) async {
    try {
      await f(await SharedPreferences.getInstance());
    } catch (_) {}
  }

  void _elegirDiseno(DisenoCompartir d, {bool mover = true}) {
    if (d == _diseno && !mover) return;
    setState(() => _diseno = d);
    if (d.exclusivo && !_donador) {
      _avisar('«${d.nombre}» es un diseño exclusivo para donadores y fundadores. '
          'Toca «Cómo conseguirlo» para ver cómo apoyar a Caudal.');
    } else {
      _guardarPref((p) => p.setString(_Prefs.diseno, d.name));
    }
    if (mover) {
      final i = _disenos.indexOf(d);
      final c = _paginas;
      if (c != null && c.hasClients && i >= 0) {
        c.animateToPage(i, duration: const Duration(milliseconds: 320), curve: Curves.easeOutCubic);
      }
    }
  }

  void _avisar(String texto, {bool bueno = false}) {
    if (!mounted) return;
    _relojAviso?.cancel();
    setState(() {
      _aviso = texto;
      _avisoBueno = bueno;
    });
    _relojAviso = Timer(const Duration(seconds: 5), () {
      if (mounted) setState(() => _aviso = null);
    });
  }

  /// La imagen del diseño elegido en alta resolución (1080 px de ancho).
  Future<Uint8List> _imagen() async {
    await WidgetsBinding.instance.endOfFrame;
    // un respiro para que la carátula termine de pintarse a su tamaño grande
    await Future<void>.delayed(const Duration(milliseconds: 120));
    final clave = _claves[_diseno]!;
    return imagenDeTarjeta(clave, anchoPx: _formato.anchoPx, altoPx: _formato.altoPx);
  }

  String get _nombreArchivo {
    final base = (_d?.titulo ?? 'cancion')
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9áéíóúñü]+'), '_')
        .replaceAll(RegExp(r'^_+|_+$'), '');
    return 'caudal_${base.isEmpty ? 'cancion' : base}_${DateTime.now().millisecondsSinceEpoch}';
  }

  Rect? _origen(BuildContext ctx) {
    final caja = ctx.findRenderObject();
    if (caja is RenderBox && caja.hasSize) return caja.localToGlobal(Offset.zero) & caja.size;
    return null;
  }

  Future<void> _compartir(BuildContext ctxBoton) async {
    final d = _d;
    if (d == null || _ocupado) return;
    if (_bloqueado) return mostrarDonar(context);
    final origen = _origen(ctxBoton);
    setState(() => _ocupado = true);
    try {
      final Uint8List bytes;
      try {
        bytes = await _imagen();
      } catch (_) {
        _avisar('No se pudo preparar la imagen. Espera a que cargue la carátula e inténtalo otra vez.');
        return;
      }
      final nombre = '$_nombreArchivo.png';
      XFile adjunto;
      if (kIsWeb) {
        adjunto = XFile.fromData(bytes, mimeType: 'image/png', name: nombre);
      } else {
        final dir = await getTemporaryDirectory();
        final archivo = File(p.join(dir.path, nombre));
        await archivo.writeAsBytes(bytes, flush: true);
        adjunto = XFile(archivo.path, mimeType: 'image/png');
      }
      try {
        await SharePlus.instance.share(ShareParams(
          files: [adjunto],
          text: d.artista.isEmpty ? d.titulo : '${d.titulo} · ${d.artista}',
          sharePositionOrigin: origen,
          fileNameOverrides: kIsWeb ? [nombre] : null,
        ));
      } catch (_) {
        _avisar('No se pudo abrir el menú para compartir. Inténtalo otra vez.');
      }
    } catch (_) {
      _avisar('No se pudo preparar la imagen. Inténtalo otra vez.');
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  Future<void> _guardar() async {
    if (_d == null || _ocupado) return;
    if (_bloqueado) return mostrarDonar(context);
    setState(() => _ocupado = true);
    try {
      final bytes = await _imagen();
      await Gal.putImageBytes(bytes, name: _nombreArchivo, album: 'Caudal');
      _avisar('Guardada en tu galería, en el álbum «Caudal».', bueno: true);
    } on GalException catch (e) {
      _avisar(switch (e.type) {
        GalExceptionType.permissionDenied =>
          'Caudal no tiene permiso para guardar fotos. Dale permiso en los ajustes del teléfono y vuelve a intentarlo.',
        GalExceptionType.notEnoughSpace => 'No hay espacio suficiente en el teléfono para guardar la imagen.',
        _ => 'No se pudo guardar la imagen en la galería. Inténtalo otra vez.',
      });
    } catch (_) {
      _avisar('No se pudo guardar la imagen en la galería. Inténtalo otra vez.');
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  // ------------------------------------------------------------ la vista

  Widget _tarjeta(DisenoCompartir diseno, DatosCompartir d, double ancho) {
    // la carátula se decodifica al tamaño de la imagen final, no al de la vista previa
    final mq = MediaQuery.of(context);
    return MediaQuery(
      data: mq.copyWith(devicePixelRatio: _formato.anchoPx / ancho),
      child: diseno.exclusivo
          ? AnimatedBuilder(
              animation: _brillo,
              builder: (_, _) => TarjetaCancion(
                  diseno: diseno, datos: d, mostrarMascota: _mascota, mostrarLetra: _letra, fase: _brillo.value),
            )
          : TarjetaCancion(diseno: diseno, datos: d, mostrarMascota: _mascota, mostrarLetra: _letra),
    );
  }

  Widget _vistaPrevia(DatosCompartir d, double altoMax) {
    final lista = _disenos;
    return SizedBox(
      height: altoMax,
      child: PageView.builder(
        controller: _paginas,
        itemCount: lista.length,
        onPageChanged: (i) => _elegirDiseno(lista[i], mover: false),
        itemBuilder: (_, i) {
          final diseno = lista[i];
          final elegido = diseno == _diseno;
          return AnimatedScale(
            scale: elegido ? 1 : 0.9,
            duration: const Duration(milliseconds: 260),
            curve: Curves.easeOutCubic,
            child: AnimatedOpacity(
              opacity: elegido ? 1 : 0.55,
              duration: const Duration(milliseconds: 260),
              child: Center(
                child: AspectRatio(
                  aspectRatio: _formato.proporcion,
                  child: LayoutBuilder(
                    builder: (_, c) => GestureDetector(
                      onTap: elegido ? null : () => _elegirDiseno(diseno),
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(18),
                          boxShadow: const [BoxShadow(color: Color(0x66000000), blurRadius: 22, offset: Offset(0, 10))],
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(18),
                          child: Stack(fit: StackFit.expand, children: [
                            RepaintBoundary(
                              key: _claves[diseno],
                              child: _tarjeta(diseno, d, c.maxWidth),
                            ),
                            // un exclusivo sin beneficios: se ve entero, con su candado abajo
                            if (diseno.exclusivo && !_donador)
                              const Positioned(left: 0, right: 0, bottom: 0, child: IgnorePointer(child: _FranjaExclusiva())),
                          ]),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _selectorDisenos() {
    final lista = _disenos;
    return SizedBox(
      height: 40,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        itemCount: lista.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final d = lista[i];
          return ChoiceChip(
            avatar: Icon(d.exclusivo && !_donador ? Icons.lock_rounded : d.icono,
                size: 16, color: d.exclusivo ? const Color(0xFFE9C46A) : null),
            label: Text(d.nombre),
            selected: d == _diseno,
            showCheckmark: false,
            onSelected: (_) => _elegirDiseno(d),
          );
        },
      ),
    );
  }

  Widget _opciones(DatosCompartir d) {
    final hayMascota = d.hayMascota;
    final hayLetra = d.hayLetra && _diseno != DisenoCompartir.letra;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        alignment: WrapAlignment.center,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          SegmentedButton<FormatoCompartir>(
            showSelectedIcon: false,
            style: SegmentedButton.styleFrom(visualDensity: VisualDensity.compact),
            segments: const [
              ButtonSegment(value: FormatoCompartir.historia, icon: Icon(Icons.crop_portrait_rounded, size: 18), label: Text('Historia')),
              ButtonSegment(value: FormatoCompartir.cuadrado, icon: Icon(Icons.crop_square_rounded, size: 18), label: Text('Cuadrado')),
            ],
            selected: {_formato},
            onSelectionChanged: (s) {
              setState(() => _formato = s.first);
              _guardarPref((p) => p.setString(_Prefs.formato, s.first.name));
            },
          ),
          if (hayMascota)
            FilterChip(
              avatar: const Icon(Icons.pets_rounded, size: 16),
              label: const Text('Mascota'),
              selected: _mascota,
              showCheckmark: false,
              onSelected: (v) {
                setState(() => _mascota = v);
                _guardarPref((p) => p.setBool(_Prefs.mascota, v));
              },
            ),
          if (hayLetra)
            FilterChip(
              avatar: const Icon(Icons.lyrics_outlined, size: 16),
              label: const Text('Letra'),
              selected: _letra,
              showCheckmark: false,
              onSelected: (v) {
                setState(() => _letra = v);
                _guardarPref((p) => p.setBool(_Prefs.letra, v));
              },
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final alto = MediaQuery.sizeOf(context).height;
    final ancho = MediaQuery.sizeOf(context).width;
    // la vista previa: lo más grande que quepa dejando ver los controles
    final altoVista = (alto * 0.56).clamp(260.0, 640.0);
    final anchoVista = ancho * 0.8;
    final altoTarjeta = (_formato == FormatoCompartir.historia ? anchoVista * 16 / 9 : anchoVista).clamp(0.0, altoVista);
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.94,
      minChildSize: 0.5,
      maxChildSize: 0.97,
      builder: (_, scroll) => Column(children: [
        const SizedBox(height: 10),
        Container(width: 38, height: 4, decoration: BoxDecoration(color: C.texto3, borderRadius: BorderRadius.circular(2))),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 12, 2),
          child: Row(children: [
            const Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Compartir canción', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
                SizedBox(height: 2),
                Text('Desliza para ver los diseños', style: estiloSecundario),
              ]),
            ),
            IconButton(
              tooltip: 'Cerrar',
              icon: const Icon(Icons.close_rounded),
              onPressed: () => Navigator.of(context).maybePop(),
            ),
          ]),
        ),
        Expanded(
          child: _fallo
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text('No se pudo preparar esta canción para compartir. Cierra y vuelve a intentarlo.',
                        textAlign: TextAlign.center, style: estiloSecundario),
                  ),
                )
              : d == null
                  ? const Center(child: CircularProgressIndicator())
                  : ListView(controller: scroll, padding: const EdgeInsets.only(top: 10, bottom: 12), children: [
                      _vistaPrevia(d, altoTarjeta.toDouble() + 8),
                      const SizedBox(height: 14),
                      _selectorDisenos(),
                      const SizedBox(height: 10),
                      _opciones(d),
                      const SizedBox(height: 12),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 24),
                        child: Text(
                          'Al compartir elige «Estado» de WhatsApp, «Historia» de Instagram o el chat que quieras.',
                          textAlign: TextAlign.center,
                          style: estiloDetalle,
                        ),
                      ),
                    ]),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              AnimatedSize(
                duration: const Duration(milliseconds: 200),
                child: _aviso == null
                    ? const SizedBox(width: double.infinity)
                    : Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(children: [
                          Icon(_avisoBueno ? Icons.check_circle_rounded : Icons.info_outline_rounded,
                              size: 18, color: _avisoBueno ? C.acento : C.error),
                          const SizedBox(width: 8),
                          Expanded(child: Text(_aviso!, style: const TextStyle(fontSize: 13.5))),
                        ]),
                      ),
              ),
              if (_bloqueado)
                // un diseño exclusivo sin beneficios: en vez de compartir, cómo conseguirlo
                Column(mainAxisSize: MainAxisSize.min, children: [
                  const Padding(
                    padding: EdgeInsets.only(bottom: 8),
                    child: Text(
                      'Los diseños dorados son para donadores y fundadores de Caudal. '
                      'Con una donación desbloqueas estos y los demás beneficios.',
                      textAlign: TextAlign.center,
                      style: estiloSecundario,
                    ),
                  ),
                  FilledButton.icon(
                    onPressed: () => mostrarDonar(context),
                    icon: const Icon(Icons.workspace_premium_rounded),
                    label: const Text('Cómo conseguirlo'),
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFFE9C46A),
                      foregroundColor: const Color(0xFF3B2608),
                      minimumSize: const Size.fromHeight(48),
                      shape: const StadiumBorder(),
                    ),
                  ),
                ])
              else
              Row(children: [
                Expanded(
                  child: Builder(
                    builder: (ctxBoton) => FilledButton.icon(
                      onPressed: d == null || _ocupado ? null : () => _compartir(ctxBoton),
                      icon: _ocupado
                          ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.2, color: C.acentoTexto))
                          : const Icon(Icons.ios_share_rounded),
                      label: const Text('Compartir'),
                      style: FilledButton.styleFrom(
                        backgroundColor: C.acento,
                        foregroundColor: C.acentoTexto,
                        minimumSize: const Size.fromHeight(48),
                        shape: const StadiumBorder(),
                      ),
                    ),
                  ),
                ),
                // en la web no hay galería: la imagen se comparte (o se descarga) con «Compartir»
                if (!kIsWeb) ...[
                  const SizedBox(width: 10),
                  OutlinedButton.icon(
                    onPressed: d == null || _ocupado ? null : _guardar,
                    icon: const Icon(Icons.download_rounded, size: 19),
                    label: const Text('Guardar'),
                    style: OutlinedButton.styleFrom(minimumSize: const Size(0, 48), shape: const StadiumBorder()),
                  ),
                ],
              ]),
            ]),
          ),
        ),
      ]),
    );
  }
}

/// La franja que tapa el pie de un diseño exclusivo cuando la cuenta no tiene los beneficios.
class _FranjaExclusiva extends StatelessWidget {
  const _FranjaExclusiva();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0x00000000), Color(0xCC000000)],
          ),
        ),
        child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(Icons.lock_rounded, size: 15, color: Color(0xFFE9C46A)),
          SizedBox(width: 6),
          Flexible(
            child: Text('Exclusivo para donadores',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFFF3D98B))),
          ),
        ]),
      );
}
