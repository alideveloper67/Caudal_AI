import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../nucleo/version.dart';
import 'novedades/diapositivas.dart';
import 'novedades/presentacion.dart';
import 'plataforma.dart';
import 'tema.dart';

/// Una tarjeta del aviso de novedades.
class NovedadItem {
  const NovedadItem(this.icono, this.titular, this.texto, this.color);
  final IconData icono;
  final String titular;
  final String texto;
  final Color color;
}

/// Lo que trae la segunda actualizacion grande (Android 2.3.0), una tarjeta por
/// diapositiva (sin la portada ni el final). Es lo que muestra el aviso previo
/// a actualizar; la presentacion usa las diapositivas completas.
final List<NovedadItem> novedadesDeEstaEdicion = [
  for (final d in diapositivas.sublist(1, diapositivas.length - 1)) NovedadItem(d.icono, d.titulo, d.texto, d.color),
];

const _titulo = 'La nueva actualización grande de Caudal';
const _subtitulo = 'Modo gamer, tu personaje cobra vida, listas que se enriquecen y regalos para tus amigos';

/// La actualizacion grande de Caudal. Dos usos:
///  * sin [actualizacion]: la presentacion a pantalla completa
///    ([PresentacionNovedades]), al abrir por primera vez la version nueva;
///  * con [actualizacion] (una release marcada `[grande]`): el aviso previo con
///    «Actualizar ahora», que baja e instala la version (en iPhone abre su pagina).
///
/// No toca la musica: es solo una pantalla encima de la app.
class NovedadesGrandes extends StatelessWidget {
  const NovedadesGrandes({
    super.key,
    this.actualizacion,
    this.items,
    this.alCerrar,
    this.alEmpezar,
    this.paginaInicial = 0,
  });

  final Novedad? actualizacion;
  final List<NovedadItem>? items;

  /// Para las pruebas o para quien lo monte sin ruta propia: se llama al cerrar.
  final VoidCallback? alCerrar;
  final VoidCallback? alEmpezar;

  /// Diapositiva con la que abre la presentacion (para las pruebas).
  final int paginaInicial;

  /// Lo abre a pantalla completa, con una entrada suave. Termina cuando se cierra.
  static Future<void> mostrar(BuildContext context, {Novedad? actualizacion}) =>
      Navigator.of(context, rootNavigator: true).push(PageRouteBuilder<void>(
        opaque: actualizacion == null,
        barrierColor: Colors.black54,
        transitionDuration: const Duration(milliseconds: 520),
        reverseTransitionDuration: const Duration(milliseconds: 320),
        pageBuilder: (_, _, _) => NovedadesGrandes(actualizacion: actualizacion),
        transitionsBuilder: (_, a, _, hijo) => FadeTransition(
          opacity: CurvedAnimation(parent: a, curve: Curves.easeOut),
          child: actualizacion == null
              ? ScaleTransition(
                  scale: Tween(begin: 1.04, end: 1.0).animate(CurvedAnimation(parent: a, curve: Curves.easeOutCubic)),
                  child: hijo,
                )
              : SlideTransition(
                  position: Tween(begin: const Offset(0, 0.06), end: Offset.zero)
                      .animate(CurvedAnimation(parent: a, curve: Curves.easeOutCubic)),
                  child: hijo,
                ),
        ),
      ));

  @override
  Widget build(BuildContext context) {
    final n = actualizacion;
    if (n == null) {
      return PresentacionNovedades(alCerrar: alCerrar, alEmpezar: alEmpezar, paginaInicial: paginaInicial);
    }
    return _AvisoActualizacion(actualizacion: n, items: items ?? novedadesDeEstaEdicion, alCerrar: alCerrar);
  }
}

/// El aviso previo a actualizar (release marcada `[grande]`): una hoja a
/// pantalla casi completa con tarjetas que entran una a una y un boton grande.
class _AvisoActualizacion extends StatefulWidget {
  const _AvisoActualizacion({required this.actualizacion, required this.items, this.alCerrar});

  final Novedad? actualizacion;
  final List<NovedadItem> items;
  final VoidCallback? alCerrar;
  VoidCallback? get alEmpezar => null;

  @override
  State<_AvisoActualizacion> createState() => _NovedadesGrandesState();
}

class _NovedadesGrandesState extends State<_AvisoActualizacion> with TickerProviderStateMixin {
  late final AnimationController _entrada =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 2400));
  late final AnimationController _brillo =
      AnimationController(vsync: this, duration: const Duration(seconds: 7));
  bool _iniciado = false;

  double _progreso = 0;
  bool _bajando = false;
  String? _error;
  CancelToken? _cancelar;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_iniciado) return;
    _iniciado = true;
    // quien pide menos movimiento ve todo ya puesto, sin animaciones
    if (MediaQuery.disableAnimationsOf(context)) {
      _entrada.value = 1;
    } else {
      _entrada.forward();
      _brillo.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _cancelar?.cancel();
    _entrada.dispose();
    _brillo.dispose();
    super.dispose();
  }

  void _cerrar() {
    if (_bajando) return;
    final f = widget.alCerrar;
    if (f != null) {
      f();
    } else {
      Navigator.of(context).maybePop();
    }
  }

  void _empezar() {
    Haptico.toque();
    final f = widget.alEmpezar;
    if (f != null) {
      f();
    } else {
      _cerrar();
    }
  }

  Future<void> _verComo() async {
    final n = widget.actualizacion!;
    final pagina = n.enlace.isNotEmpty ? n.enlace : 'https://github.com/$origen/releases';
    try {
      await abrirEnNavegador(pagina);
      if (mounted) _cerrar();
    } catch (_) {
      if (mounted) setState(() => _error = 'No se pudo abrir la página de descarga.');
    }
  }

  Future<void> _instalar() async {
    final n = widget.actualizacion!;
    setState(() {
      _bajando = true;
      _error = null;
      _progreso = 0;
    });
    _cancelar = CancelToken();
    try {
      final ruta = await descargarApk(n, cancelar: _cancelar,
          alProgresar: (p) => mounted ? setState(() => _progreso = p) : null);
      final fallo = await instalar(ruta);
      if (!mounted) return;
      if (fallo == null) {
        setState(() => _bajando = false);
        _cerrar();
      } else {
        setState(() {
          _bajando = false;
          _error = fallo;
        });
      }
    } catch (_) {
      if (mounted && !(_cancelar?.isCancelled ?? false)) {
        setState(() {
          _bajando = false;
          _error = 'No se pudo bajar la actualización. Revisa tu conexión.';
        });
      }
    }
  }

  /// Un tramo de la animacion de entrada: de [a] a [b] (0 a 1 del total).
  Animation<double> _tramo(double a, double b) => CurvedAnimation(
      parent: _entrada, curve: Interval(a.clamp(0.0, 1.0), b.clamp(0.0, 1.0), curve: Curves.easeOutCubic));

  Widget _aparece(Animation<double> a, Widget hijo, {double desplazamiento = 22}) => AnimatedBuilder(
        animation: a,
        child: hijo,
        builder: (_, h) => Opacity(
          opacity: a.value.clamp(0.0, 1.0),
          child: Transform.translate(offset: Offset(0, (1 - a.value) * desplazamiento), child: h),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final n = widget.actualizacion;
    final acento = C.acento;
    final notas = n?.notasVisibles ?? '';
    final items = widget.items;
    final instalable = n?.sePuedeInstalar ?? false;

    // tarjetas: cada una en su turno (la entrada dura 2,4 s; las tarjetas ocupan de 0,2 a 1)
    final tarjetas = <Widget>[
      for (final (i, it) in items.indexed)
        _aparece(_tramo(0.18 + i * 0.075, 0.18 + i * 0.075 + 0.28), _Tarjeta(item: it, acento: acento)),
      if (notas.isNotEmpty)
        _aparece(_tramo(0.18 + items.length * 0.075, 1), _TarjetaNotas(texto: notas)),
    ];

    return Semantics(
      scopesRoute: true,
      explicitChildNodes: true,
      label: 'Novedades de Caudal',
      child: Material(
        color: C.fondo,
        child: Stack(children: [
          // ---- fondo: degradado del acento y dos luces que se mueven despacio
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Color.lerp(acento, C.fondo, 0.52)!,
                    Color.lerp(acento, C.fondo, 0.82)!,
                    C.fondo,
                  ],
                  stops: const [0, 0.38, 0.8],
                ),
              ),
            ),
          ),
          Positioned.fill(
            child: IgnorePointer(
              child: RepaintBoundary(
                child: AnimatedBuilder(
                  animation: _brillo,
                  builder: (_, _) {
                    final t = Curves.easeInOut.transform(_brillo.value);
                    return Stack(children: [
                      Align(
                        alignment: Alignment(0.9 - t * 0.5, -1.05 + t * 0.12),
                        child: _Luz(color: C.acentoAlto, tamano: 340, opacidad: 0.30),
                      ),
                      Align(
                        alignment: Alignment(-1.1 + t * 0.45, -0.55 - t * 0.1),
                        child: _Luz(color: acento, tamano: 260, opacidad: 0.22),
                      ),
                    ]);
                  },
                ),
              ),
            ),
          ),
          // ---- contenido
          SafeArea(
            child: Column(children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(Esp.l, Esp.s, Esp.s, 0),
                child: Row(children: [
                  const Spacer(),
                  IconButton(
                    tooltip: 'Cerrar',
                    onPressed: _bajando ? null : _cerrar,
                    style: IconButton.styleFrom(
                        backgroundColor: const Color(0x33000000), minimumSize: const Size(48, 48)),
                    icon: const Icon(Icons.close_rounded),
                  ),
                ]),
              ),
              Expanded(
                child: LayoutBuilder(builder: (context, c) {
                  final dosColumnas = c.maxWidth >= 640;
                  final ancho = c.maxWidth.clamp(0.0, 760.0);
                  return Align(
                    alignment: Alignment.topCenter,
                    child: SizedBox(
                      width: ancho,
                      // todo construido (son pocas tarjetas): el lector de pantalla las recorre todas
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.fromLTRB(Esp.lado + 4, Esp.s, Esp.lado + 4, Esp.xl),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                          _aparece(_tramo(0, 0.3), _Cabecera(version: n?.version ?? versionApp, actualizacion: n != null),
                              desplazamiento: 16),
                          const SizedBox(height: Esp.xl),
                          if (dosColumnas)
                            for (var i = 0; i < tarjetas.length; i += 2)
                              Padding(
                                padding: const EdgeInsets.only(bottom: Esp.m),
                                child: IntrinsicHeight(
                                  child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                                    Expanded(child: tarjetas[i]),
                                    const SizedBox(width: Esp.m),
                                    Expanded(child: i + 1 < tarjetas.length ? tarjetas[i + 1] : const SizedBox.shrink()),
                                  ]),
                                ),
                              )
                          else
                            for (final t in tarjetas) Padding(padding: const EdgeInsets.only(bottom: Esp.m), child: t),
                          const SizedBox(height: Esp.s),
                        ]),
                      ),
                    ),
                  );
                }),
              ),
              // ---- boton fijo abajo
              _aparece(
                _tramo(0.5, 0.9),
                DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [C.fondo.withValues(alpha: 0), C.fondo.withValues(alpha: 0.9)],
                    ),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(Esp.xl, Esp.m, Esp.xl, Esp.l),
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 420),
                        child: Column(mainAxisSize: MainAxisSize.min, children: [
                          if (_bajando) ...[
                            ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: _progreso / 100,
                                minHeight: 6,
                                color: C.acento,
                                backgroundColor: C.superficie3,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(_progreso >= 99.5 ? 'Abriendo el instalador…' : 'Bajando ${_progreso.toStringAsFixed(0)} %',
                                style: estiloSecundario),
                            const SizedBox(height: 12),
                          ],
                          if (_error != null)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: Text(_error!, textAlign: TextAlign.center,
                                  style: const TextStyle(color: C.error, height: 1.35)),
                            ),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton.icon(
                              onPressed: _bajando ? null : (n == null ? _empezar : (instalable ? _instalar : _verComo)),
                              style: FilledButton.styleFrom(
                                shape: const StadiumBorder(),
                                padding: const EdgeInsets.symmetric(vertical: 16),
                                textStyle: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w800),
                              ),
                              icon: Icon(n == null
                                  ? Icons.arrow_forward_rounded
                                  : (instalable ? Icons.download_rounded : Icons.open_in_new_rounded)),
                              iconAlignment: IconAlignment.end,
                              label: Text(n == null ? 'Empezar' : (instalable ? 'Actualizar ahora' : 'Ver cómo actualizar')),
                            ),
                          ),
                          if (n != null)
                            TextButton(
                              onPressed: _bajando ? null : _cerrar,
                              child: const Text('Más tarde', style: TextStyle(color: C.texto2)),
                            ),
                        ]),
                      ),
                    ),
                  ),
                ),
                desplazamiento: 30,
              ),
            ]),
          ),
        ]),
      ),
    );
  }
}

/// Una luz difusa de fondo (un circulo con degradado radial).
class _Luz extends StatelessWidget {
  const _Luz({required this.color, required this.tamano, required this.opacidad});
  final Color color;
  final double tamano;
  final double opacidad;

  @override
  Widget build(BuildContext context) => Container(
        width: tamano,
        height: tamano,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(colors: [color.withValues(alpha: opacidad), color.withValues(alpha: 0)]),
        ),
      );
}

class _Cabecera extends StatelessWidget {
  const _Cabecera({required this.version, required this.actualizacion});
  final String version;
  final bool actualizacion;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: const Color(0x33FFFFFF),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0x44FFFFFF)),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.auto_awesome_rounded, size: 15, color: Color(0xFFFFE08A)),
            const SizedBox(width: 6),
            Flexible(
              child: Text(actualizacion ? 'Caudal $version ya está lista' : 'Novedades de Caudal $version',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, letterSpacing: 0.3)),
            ),
          ]),
        ),
        const SizedBox(height: Esp.l),
        Semantics(
          header: true,
          child: const Text(_titulo,
              style: TextStyle(fontSize: 34, fontWeight: FontWeight.w900, letterSpacing: -1, height: 1.08)),
        ),
        const SizedBox(height: Esp.m),
        const Text(_subtitulo, style: TextStyle(fontSize: 16.5, color: Color(0xDDFFFFFF), height: 1.4)),
      ]);
}

class _Tarjeta extends StatelessWidget {
  const _Tarjeta({required this.item, required this.acento});
  final NovedadItem item;
  final Color acento;

  @override
  Widget build(BuildContext context) {
    // el color de cada tarjeta, algo acercado al acento para que todo case
    final color = Color.lerp(item.color, acento, 0.25)!;
    return Semantics(
      container: true,
      label: '${item.titular}. ${item.texto}',
      child: ExcludeSemantics(
        child: Container(
          padding: const EdgeInsets.all(Esp.l),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            color: C.fondo.withValues(alpha: 0.55),
            border: Border.all(color: Color.lerp(color, C.borde, 0.6)!.withValues(alpha: 0.7)),
            boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 16, offset: Offset(0, 6))],
          ),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                gradient: LinearGradient(
                  colors: [color, Color.lerp(color, Colors.black, 0.35)!],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: Icon(item.icono, size: 25, color: Colors.white),
            ),
            const SizedBox(width: Esp.m + 2),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(item.titular, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, height: 1.2)),
                const SizedBox(height: 4),
                Text(item.texto, style: const TextStyle(fontSize: 14, color: C.texto2, height: 1.4)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

/// Lo que escribio quien publico la release (si puso algo mas), como ultima tarjeta.
class _TarjetaNotas extends StatelessWidget {
  const _TarjetaNotas({required this.texto});
  final String texto;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(Esp.l),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          color: C.fondo.withValues(alpha: 0.45),
          border: Border.all(color: C.borde),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Y además', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          Text(texto, style: const TextStyle(fontSize: 14, color: C.texto2, height: 1.45)),
        ]),
      );
}
