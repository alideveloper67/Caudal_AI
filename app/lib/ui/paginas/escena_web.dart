import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';

import '../../nucleo/premium.dart';
import '../../reproduccion/reproductor.dart';
import '../../reproduccion/ventana_web.dart';
import '../atajos_teclado.dart';
import '../comunes.dart';
import '../escenarios/catalogo.dart';
import '../escenarios/escenario_fondo.dart';
import '../reproductor/barra_progreso.dart' show BarraProgreso;
import '../reproductor/fondo_ambiente.dart';
import '../reproductor/hueco_video_web.dart';
import '../reproductor/letra_corrida.dart';
import '../reproductor/paleta_portada.dart';
import '../servicios.dart';
import '../tema.dart';

/// La «Escena de escritorio» de Caudal en el navegador: reloj gigante, tarjeta de
/// lo que suena, letra, lo que sigue y la barra, sobre la carátula viva o un
/// escenario. En la computadora cada pieza se mueve y se oculta (Editar); en el
/// teléfono van una bajo otra.
class EscenaWebPagina extends StatefulWidget {
  const EscenaWebPagina({super.key});

  static Future<void> abrir(BuildContext context) => Navigator.of(context, rootNavigator: true)
      .push(MaterialPageRoute<void>(fullscreenDialog: true, builder: (_) => const EscenaWebPagina()));

  @override
  State<EscenaWebPagina> createState() => _EscenaWebPaginaState();
}

enum _Pieza { reloj, tarjeta, letra, lista, barra }

const _nombres = {
  _Pieza.reloj: 'Reloj',
  _Pieza.tarjeta: 'Tarjeta',
  _Pieza.letra: 'Letra',
  _Pieza.lista: 'A continuación',
  _Pieza.barra: 'Controles',
};

/// Dónde va cada pieza (0..1 del espacio que le sobra a lo ancho y a lo alto).
const _sitios = {
  _Pieza.reloj: Offset(0.0, 0.0),
  _Pieza.tarjeta: Offset(0.0, 0.5),
  _Pieza.letra: Offset(0.5, 0.4),
  _Pieza.lista: Offset(1.0, 0.25),
  _Pieza.barra: Offset(0.5, 1.0),
};

class _EscenaWebPaginaState extends State<EscenaWebPagina> {
  Servicios? _s;
  Reproductor? _r;
  Timer? _reloj;
  bool _editando = false;
  final Map<_Pieza, Offset> _lugar = Map.of(_sitios);
  final Set<_Pieza> _ocultas = {};
  PaletaPortada _paleta = PaletaPortada.neutra;
  String _url = '-';

  @override
  void initState() {
    super.initState();
    _reloj = Timer.periodic(const Duration(seconds: 5), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_r != null) return;
    _s = Caudal.leer(context);
    _r = _s!.reproductor..addListener(_cambio);
    try {
      final d = jsonDecode(_s!.ajustes.texto('escena_web'));
      if (d is Map) {
        for (final p in _Pieza.values) {
          final v = d[p.name];
          if (v is! Map) continue;
          final x = v['x'], y = v['y'];
          if (x is num && y is num) _lugar[p] = Offset(x.toDouble().clamp(0, 1), y.toDouble().clamp(0, 1));
          if (v['oculta'] == true) _ocultas.add(p);
        }
      }
    } catch (_) {}
    _cambio();
  }

  @override
  void dispose() {
    _reloj?.cancel();
    _r?.removeListener(_cambio);
    if (VentanaWeb.completa.value) VentanaWeb.pantallaCompleta(false);
    super.dispose();
  }

  void _cambio() {
    if (!mounted) return;
    final url = '${_r!.actual?['miniatura'] ?? ''}';
    if (url != _url) {
      _url = url;
      paletaDe(url).then((p) {
        if (mounted && _url == url) setState(() => _paleta = p);
      });
    }
    setState(() {});
  }

  void _guardar() => _s!.ajustes.poner('escena_web', jsonEncode({
        for (final p in _Pieza.values)
          p.name: {'x': _lugar[p]!.dx, 'y': _lugar[p]!.dy, if (_ocultas.contains(p)) 'oculta': true},
      }));

  EscenarioDef? get _escenario {
    final c = _s!.ajustes.texto('escena_fondo');
    return c.isEmpty || c == 'ambiente' || !Premium.i.activo ? null : escenarioPorClave(c);
  }

  Future<void> _elegirFondo() async {
    final actual = _escenario?.clave ?? 'ambiente';
    final elegido = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * 0.75),
          child: ListView(shrinkWrap: true, padding: const EdgeInsets.only(bottom: 12), children: [
            const Padding(padding: EdgeInsets.fromLTRB(20, 4, 20, 8), child: Text('Fondo de la escena', style: estiloTituloSeccion)),
            for (final (clave, nombre) in [('ambiente', 'La carátula viva'), for (final e in escenarios) (e.clave, e.nombre)])
              ListTile(
                leading: Icon(clave == actual ? Icons.check_circle_rounded : Icons.circle_outlined,
                    color: clave == actual ? C.acento : C.texto3),
                title: Text(nombre),
                trailing: clave != 'ambiente' && !Premium.i.activo
                    ? const Icon(Icons.lock_outline_rounded, size: 18, color: C.texto3, semanticLabel: 'Para donadores')
                    : null,
                onTap: () => Navigator.pop(ctx, clave),
              ),
          ]),
        ),
      ),
    );
    if (elegido == null || !mounted) return;
    if (elegido != 'ambiente' && !Premium.i.activo) {
      return _s!.avisar('Es exclusivo de donadores: dona o canjea un código de prueba para usarlo.');
    }
    await _s!.ajustes.poner('escena_fondo', elegido);
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final r = _r!;
    final esc = _escenario;
    return CerrarConEsc(child: Scaffold(
      backgroundColor: Colors.black,
      body: Stack(fit: StackFit.expand, children: [
        if (esc != null)
          EscenarioFondo(key: ValueKey(esc.clave), clave: esc.clave, interactivo: !_editando)
        else
          FondoAmbiente(url: '${r.actual?['miniatura'] ?? ''}', color: _paleta.fondo,
              enMovimiento: r.estado == EstadoRepro.sonando),
        const IgnorePointer(child: ColoredBox(color: Color(0x40000000))),
        SafeArea(
          child: LayoutBuilder(
            builder: (context, c) => c.maxWidth >= 900 && c.maxHeight >= 520 ? _libre(c.biggest) : _apilada(c.biggest),
          ),
        ),
        SafeArea(
          child: Align(
            alignment: Alignment.topRight,
            child: Padding(padding: const EdgeInsets.all(6), child: _botones(context)),
          ),
        ),
      ]),
    ));
  }

  Widget _botones(BuildContext context) {
    final t = MediaQuery.sizeOf(context);
    final ancha = t.width >= 900 && t.height >= 520;
    return Row(mainAxisSize: MainAxisSize.min, children: [
      if (_editando)
        TextButton(
          onPressed: () {
            setState(() {
              _lugar.addAll(_sitios);
              _ocultas.clear();
            });
            _guardar();
          },
          child: const Text('Como al principio'),
        ),
      if (ancha)
        IconButton(
          tooltip: _editando ? 'Listo' : 'Mover y ocultar piezas',
          icon: Icon(_editando ? Icons.check_rounded : Icons.open_with_rounded),
          onPressed: () => setState(() => _editando = !_editando),
        ),
      IconButton(tooltip: 'Fondo', icon: const Icon(Icons.wallpaper_rounded), onPressed: _elegirFondo),
      if (VentanaWeb.puedePantallaCompleta)
        ValueListenableBuilder<bool>(
          valueListenable: VentanaWeb.completa,
          builder: (_, si, _) => IconButton(
            tooltip: si ? 'Salir de pantalla completa' : 'Pantalla completa',
            icon: Icon(si ? Icons.fullscreen_exit_rounded : Icons.fullscreen_rounded),
            onPressed: () => VentanaWeb.pantallaCompleta(!si),
          ),
        ),
      IconButton(tooltip: 'Cerrar', icon: const Icon(Icons.close_rounded), onPressed: () => Navigator.of(context).pop()),
    ]);
  }

  // ------------------------------------------------------------ computadora

  Size _tamano(_Pieza p, Size z) => switch (p) {
        _Pieza.reloj => const Size(330, 150),
        _Pieza.tarjeta => Size(300, (_r!.fuente?.esYouTubeWeb ?? false) ? 270 : 320),
        _Pieza.letra => Size((z.width - 720).clamp(300.0, 720.0), (z.height - 260).clamp(200.0, 520.0)),
        _Pieza.lista => Size(300, (z.height - 280).clamp(200.0, 420.0)),
        _Pieza.barra => Size((z.width * 0.6).clamp(560.0, 820.0), 128),
      };

  Widget _libre(Size total) {
    const borde = 26.0;
    final z = Size(total.width - borde * 2, total.height - borde * 2);
    return Stack(children: [
      for (final p in _Pieza.values)
        if (!_ocultas.contains(p) || _editando)
          () {
            final t = _tamano(p, z);
            final libre = Size((z.width - t.width).clamp(1.0, double.infinity), (z.height - t.height).clamp(1.0, double.infinity));
            final l = _lugar[p]!;
            final oculta = _ocultas.contains(p);
            return Positioned(
              key: ValueKey(p),
              left: borde + l.dx * libre.width,
              top: borde + l.dy * libre.height,
              width: t.width,
              height: t.height,
              child: _editando
                  ? GestureDetector(
                      onPanUpdate: (d) => setState(() => _lugar[p] = Offset(
                          (_lugar[p]!.dx + d.delta.dx / libre.width).clamp(0.0, 1.0),
                          (_lugar[p]!.dy + d.delta.dy / libre.height).clamp(0.0, 1.0))),
                      onPanEnd: (_) => _guardar(),
                      child: MouseRegion(
                        cursor: SystemMouseCursors.move,
                        child: Stack(fit: StackFit.expand, children: [
                          // editando, el video de YouTube taparía el arrastre: se queda en su esquina
                          IgnorePointer(child: Opacity(opacity: oculta ? 0.25 : 1, child: _pieza(p, sinVideo: true))),
                          DecoratedBox(
                            decoration: BoxDecoration(
                                border: Border.all(color: C.acento.withValues(alpha: 0.8)), borderRadius: BorderRadius.circular(14)),
                          ),
                          Align(
                            alignment: Alignment.topRight,
                            child: IconButton.filled(
                              tooltip: oculta ? 'Mostrar ${_nombres[p]}' : 'Ocultar ${_nombres[p]}',
                              iconSize: 18,
                              icon: Icon(oculta ? Icons.visibility_rounded : Icons.visibility_off_rounded),
                              onPressed: () {
                                setState(() => oculta ? _ocultas.remove(p) : _ocultas.add(p));
                                _guardar();
                              },
                            ),
                          ),
                        ]),
                      ),
                    )
                  : _pieza(p),
            );
          }(),
    ]);
  }

  // ------------------------------------------------------------ teléfono

  Widget _apilada(Size z) {
    final youtube = _r!.fuente?.esYouTubeWeb ?? false;
    if (z.width > z.height) {
      // de lado: a la izquierda lo que suena, a la derecha la letra
      return Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
        child: Row(children: [
          Expanded(
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              _hora(40),
              if (youtube) const Flexible(child: Padding(padding: EdgeInsets.all(8), child: HuecoVideoWeb())),
              _barra(compacta: true),
            ]),
          ),
          const SizedBox(width: 12),
          const Expanded(child: Padding(padding: EdgeInsets.only(top: 44), child: LetraCorrida(tamano: 20))),
        ]),
      );
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 52, 16, 10),
      child: Column(children: [
        _hora(64),
        if (youtube) const Padding(padding: EdgeInsets.only(top: 10), child: HuecoVideoWeb()),
        const SizedBox(height: 8),
        const Expanded(child: LetraCorrida(tamano: 24, centrada: true)),
        _barra(compacta: true),
      ]),
    );
  }

  // ------------------------------------------------------------ piezas

  static const _sombra = [Shadow(blurRadius: 16, color: Colors.black87)];

  Widget _vidrio(Widget hijo, {EdgeInsets relleno = const EdgeInsets.all(14)}) => Container(
        padding: relleno,
        decoration: BoxDecoration(
          color: const Color(0x8C0A0C12),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: const Color(0x1FFFFFFF)),
        ),
        child: Material(type: MaterialType.transparency, child: hijo),
      );

  Widget _hora(double tamano) {
    final t = DateTime.now();
    return Text('${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}',
        style: TextStyle(fontSize: tamano, height: 1, fontWeight: FontWeight.w900, letterSpacing: -2, shadows: _sombra));
  }

  static const _dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
  static const _meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
    'octubre', 'noviembre', 'diciembre'];

  Widget _pieza(_Pieza p, {bool sinVideo = false}) {
    final r = _r!;
    final pista = r.actual;
    switch (p) {
      case _Pieza.reloj:
        final t = DateTime.now();
        return FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.topLeft,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _hora(104),
            const SizedBox(height: 6),
            Text('${_dias[t.weekday - 1]}, ${t.day} de ${_meses[t.month - 1]}',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, shadows: _sombra)),
          ]),
        );
      case _Pieza.tarjeta:
        return _vidrio(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(
            child: Center(
              child: (r.fuente?.esYouTubeWeb ?? false)
                  ? (sinVideo ? const SizedBox.shrink() : const HuecoVideoWeb())
                  : LayoutBuilder(
                      builder: (_, c) =>
                          Portada(url: '${pista?['miniatura'] ?? ''}', lado: c.biggest.shortestSide, radio: 12)),
            ),
          ),
          const SizedBox(height: 10),
          Text('${pista?['titulo'] ?? 'Nada sonando'}', maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
          Text('${pista?['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
        ]));
      case _Pieza.letra:
        return const LetraCorrida(tamano: 30, centrada: true);
      case _Pieza.lista:
        final lista = [...r.proximas, ...r.siguientesDeContexto].take(12).toList();
        return _vidrio(
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Padding(padding: EdgeInsets.fromLTRB(14, 12, 14, 4), child: Text('A continuación', style: TextStyle(fontWeight: FontWeight.w900))),
            Expanded(
              child: lista.isEmpty
                  ? const Center(child: Text('No hay más en la cola.', style: estiloSecundario))
                  : ListView.builder(
                      padding: const EdgeInsets.only(bottom: 8),
                      itemCount: lista.length,
                      itemBuilder: (_, i) => ListTile(
                        dense: true,
                        leading: Portada(url: '${lista[i]['miniatura'] ?? ''}', lado: 38, radio: 6),
                        title: Text('${lista[i]['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: Text('${lista[i]['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
                        onTap: () => i < r.proximas.length
                            ? r.saltarAProxima(i)
                            : r.saltarA(r.pos + 1 + i - r.proximas.length),
                      ),
                    ),
            ),
          ]),
          relleno: EdgeInsets.zero,
        );
      case _Pieza.barra:
        return _barra();
    }
  }

  Widget _barra({bool compacta = false}) {
    final r = _r!;
    final p = r.actual;
    final gusta = _s!.coleccion.meGusta('${p?['clave']}');
    return _vidrio(
      Column(mainAxisSize: MainAxisSize.min, children: [
        if (compacta) ...[
          Text('${p?['titulo'] ?? 'Nada sonando'}', maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
          Text('${p?['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
        ],
        BarraProgreso(r: r),
        FittedBox(
          fit: BoxFit.scaleDown,
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            IconButton(
              tooltip: 'Aleatorio',
              icon: Icon(Icons.shuffle_rounded, color: r.aleatorio ? C.acento : C.texto2),
              onPressed: p == null ? null : r.alternarAleatorio,
            ),
            IconButton(tooltip: 'Anterior', iconSize: 30, icon: const Icon(Icons.skip_previous_rounded), onPressed: p == null ? null : r.anterior),
            IconButton(
              tooltip: r.estado == EstadoRepro.sonando ? 'Pausar' : 'Reproducir',
              iconSize: 40,
              padding: EdgeInsets.zero,
              icon: Icon(r.estado == EstadoRepro.sonando ? Icons.pause_circle_rounded : Icons.play_circle_rounded),
              onPressed: p == null ? null : r.alternar,
            ),
            IconButton(tooltip: 'Siguiente', iconSize: 30, icon: const Icon(Icons.skip_next_rounded), onPressed: p == null ? null : () => r.siguiente()),
            IconButton(
              tooltip: gusta ? 'Quitar de Tus me gusta' : 'Me gusta',
              icon: Icon(gusta ? Icons.favorite_rounded : Icons.favorite_border_rounded, color: gusta ? C.acento : C.texto2),
              onPressed: p == null
                  ? null
                  : () async {
                      await _s!.alternarMeGusta(p);
                      if (mounted) setState(() {});
                    },
            ),
          ]),
        ),
      ]),
      relleno: const EdgeInsets.fromLTRB(10, 8, 10, 4),
    );
  }
}
