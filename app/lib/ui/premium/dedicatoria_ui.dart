import 'dart:math' as math;
import 'dart:ui' show FontFeature;

import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/dedicatorias.dart';
import '../../reproduccion/reproductor.dart';
import '../comunes.dart';
import '../paginas/donar.dart';
import '../servicios.dart';
import '../tema.dart';
import 'elegir_cancion.dart';

// ============================================================ estilos de tarjeta

/// Los colores de un estilo de tarjeta. Todos llevan texto blanco legible (contraste AA) en sus tres tonos.
class EstiloDedicatoria {
  const EstiloDedicatoria(this.clave, this.nombre, this.fondo, this.acento);
  final String clave;
  final String nombre;
  final List<Color> fondo;
  final Color acento;

  LinearGradient get degradado =>
      LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: fondo);
}

const estilosDedicatoria = <EstiloDedicatoria>[
  EstiloDedicatoria('aurora', 'Aurora', [Color(0xFF0B3B4A), Color(0xFF1B6460), Color(0xFF4A3590)], Color(0xFF8CF5D0)),
  EstiloDedicatoria('atardecer', 'Atardecer', [Color(0xFF4A1B3D), Color(0xFF8E3545), Color(0xFFA85324)], Color(0xFFFFD58A)),
  EstiloDedicatoria('sakura', 'Sakura', [Color(0xFF5B2250), Color(0xFF93336C), Color(0xFFAC4A76)], Color(0xFFFFC2DC)),
  EstiloDedicatoria('oceano', 'Océano', [Color(0xFF0A2A5E), Color(0xFF124F96), Color(0xFF176FA8)], Color(0xFF9BE3FF)),
  EstiloDedicatoria('bosque', 'Bosque', [Color(0xFF0F3320), Color(0xFF1B5E38), Color(0xFF2A7140)], Color(0xFFB8F5B0)),
  EstiloDedicatoria('medianoche', 'Medianoche', [Color(0xFF0D0B26), Color(0xFF241B5C), Color(0xFF45298A)], Color(0xFFC9B8FF)),
];

EstiloDedicatoria estiloDedicatoria(String clave) =>
    estilosDedicatoria.firstWhere((e) => e.clave == clave, orElse: () => estilosDedicatoria.first);

// ============================================================ la tarjeta

/// La tarjeta de una dedicatoria. Compacta sirve para la burbuja del chat y la vista previa; la grande
/// es la que se abre a pantalla completa. Nada tiene alto fijo: aguanta 320 de ancho y letra grande.
class TarjetaDedicatoria extends StatelessWidget {
  const TarjetaDedicatoria({
    super.key,
    required this.pista,
    required this.dedicatoria,
    required this.etiqueta,
    this.grande = false,
    this.pie,
  });

  final Json pista;
  final Dedicatoria dedicatoria;

  /// «De Ana» o «Para Ana».
  final String etiqueta;
  final bool grande;

  /// Lo de abajo: «Toca para abrir», los botones…
  final Widget? pie;

  @override
  Widget build(BuildContext context) {
    final e = estiloDedicatoria(dedicatoria.estilo);
    final titulo = '${pista['titulo'] ?? ''}';
    final artista = '${pista['artista'] ?? ''}';
    final portada = '${pista['miniatura'] ?? ''}';
    final lado = grande ? 150.0 : 56.0;
    final cabecera = Row(children: [
      const Text('💌', style: TextStyle(fontSize: 15)),
      const SizedBox(width: 6),
      Expanded(
        child: Text(etiqueta,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, letterSpacing: 0.3, color: e.acento)),
      ),
    ]);
    final cancion = grande
        ? Column(children: [
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                boxShadow: [BoxShadow(color: e.acento.withValues(alpha: 0.35), blurRadius: 34, spreadRadius: 1)],
              ),
              child: Portada(url: portada, lado: lado, radio: 20),
            ),
            const SizedBox(height: Esp.l),
            Text(titulo,
                textAlign: TextAlign.center,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900, height: 1.2, color: Colors.white)),
            const SizedBox(height: 4),
            Text(artista,
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 14.5, color: Colors.white.withValues(alpha: 0.8))),
          ])
        : Row(children: [
            Portada(url: portada, lado: lado, radio: 12),
            const SizedBox(width: Esp.m),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(titulo,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, height: 1.2, color: Colors.white)),
                Text(artista,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12.5, color: Colors.white.withValues(alpha: 0.78))),
              ]),
            ),
          ]);
    return Container(
      padding: EdgeInsets.all(grande ? Esp.xl : Esp.m),
      decoration: BoxDecoration(
        gradient: e.degradado,
        borderRadius: BorderRadius.circular(grande ? 28 : 18),
        border: Border.all(color: e.acento.withValues(alpha: 0.35)),
      ),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        cabecera,
        SizedBox(height: grande ? Esp.l : Esp.s),
        cancion,
        if (dedicatoria.mensaje.isNotEmpty) ...[
          SizedBox(height: grande ? Esp.xl : Esp.m),
          Container(
            padding: EdgeInsets.symmetric(horizontal: grande ? Esp.l : Esp.m, vertical: grande ? Esp.m : Esp.s),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.22),
              borderRadius: BorderRadius.circular(14),
              border: Border(left: BorderSide(color: e.acento, width: 3)),
            ),
            child: Text(dedicatoria.mensaje,
                maxLines: grande ? 8 : 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                    fontSize: grande ? 17 : 14.5, fontStyle: FontStyle.italic, height: 1.35, color: Colors.white)),
          ),
        ],
        if (pie != null) ...[SizedBox(height: grande ? Esp.l : Esp.s), pie!],
      ]),
    );
  }
}

/// La dedicatoria dentro de la burbuja del chat: se toca para abrirla.
class DedicatoriaEnChat extends StatelessWidget {
  const DedicatoriaEnChat({super.key, required this.pista, required this.mia, required this.otro, this.alAbrir});
  final Json pista;
  final bool mia;

  /// El nombre de la otra persona del chat.
  final String otro;
  final VoidCallback? alAbrir;

  @override
  Widget build(BuildContext context) {
    final d = Dedicatoria.de(pista);
    if (d == null) return const SizedBox.shrink();
    final e = estiloDedicatoria(d.estilo);
    return Semantics(
      button: true,
      label: mia ? 'Dedicatoria para $otro: ${pista['titulo'] ?? ''}' : 'Dedicatoria de $otro: ${pista['titulo'] ?? ''}. Toca para abrirla',
      excludeSemantics: true,
      child: GestureDetector(
        onTap: alAbrir,
        onLongPress: () => Caudal.leer(context).hojaPista(context, Dedicatoria.pistaLimpia(pista)),
        child: SizedBox(
          width: 270,
          child: TarjetaDedicatoria(
            pista: pista,
            dedicatoria: d,
            etiqueta: mia ? 'Dedicatoria para $otro' : 'Dedicatoria de $otro',
            pie: Row(children: [
              Icon(mia ? Icons.check_circle_outline_rounded : Icons.mark_email_unread_rounded, size: 16, color: e.acento),
              const SizedBox(width: 6),
              Expanded(
                child: Text(mia ? 'Toca para verla' : 'Toca para abrir y escuchar',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: e.acento)),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

// ============================================================ abrirla

/// Cómo se maneja el reproductor de Caudal para sonar un fragmento.
ControlFragmento controlDeReproductor(Reproductor r) => ControlFragmento(
      actual: () => r.actual,
      sonando: () => r.estado == EstadoRepro.sonando,
      duracion: () => r.duracion.value,
      reproducir: (p) => r.reproducirPista(p, conRadio: false, modo: 'audio'),
      buscar: r.buscar,
      pausar: r.pausar,
    );

/// Abre la dedicatoria a pantalla completa. Si es de otra persona ([mia] falso), suena un fragmento al
/// abrirla; si es mía, solo se ve (y se puede escuchar con el botón).
Future<void> abrirDedicatoria(BuildContext context,
    {required Json pista, required String otro, required bool mia, SonarFragmento? sonador}) {
  final d = Dedicatoria.de(pista);
  if (d == null) return Future.value();
  final s = Caudal.leer(context);
  final sonar = sonador ?? SonarFragmento(controlDeReproductor(s.reproductor));
  return showGeneralDialog<void>(
    context: context,
    useRootNavigator: true,
    barrierDismissible: true,
    barrierLabel: 'Cerrar la dedicatoria',
    barrierColor: Colors.black.withValues(alpha: 0.72),
    transitionDuration: MediaQuery.maybeDisableAnimationsOf(context) == true ? Duration.zero : Mov.entrada,
    pageBuilder: (_, _, _) => _DedicatoriaAbierta(pista: pista, dedicatoria: d, otro: otro, mia: mia, sonador: sonar),
    transitionBuilder: (_, a, _, hijo) {
      final c = CurvedAnimation(parent: a, curve: Mov.curvaEntrada);
      return FadeTransition(
        opacity: c,
        child: ScaleTransition(scale: Tween<double>(begin: 0.9, end: 1).animate(c), child: hijo),
      );
    },
  );
}

class _DedicatoriaAbierta extends StatefulWidget {
  const _DedicatoriaAbierta(
      {required this.pista, required this.dedicatoria, required this.otro, required this.mia, required this.sonador});
  final Json pista;
  final Dedicatoria dedicatoria;
  final String otro;
  final bool mia;
  final SonarFragmento sonador;

  @override
  State<_DedicatoriaAbierta> createState() => _DedicatoriaAbiertaState();
}

class _DedicatoriaAbiertaState extends State<_DedicatoriaAbierta> {
  bool _sonando = false;

  @override
  void initState() {
    super.initState();
    if (!widget.mia) {
      // al abrirla suena un fragmento; seguirá aunque se cierre la tarjeta y se calla solo
      WidgetsBinding.instance.addPostFrameCallback((_) => _fragmento());
    }
  }

  Future<void> _fragmento() async {
    if (mounted) setState(() => _sonando = true);
    final ok = await widget.sonador.iniciar(widget.pista, widget.dedicatoria);
    if (mounted) setState(() => _sonando = false);
    if (!ok && mounted) {
      // sin sonido no pasa nada grave: la tarjeta se lee igual
      Caudal.leer(context).avisar('No se pudo reproducir el fragmento. Puedes escucharla con el botón.');
    }
  }

  Json get _limpia => Dedicatoria.pistaLimpia(widget.pista);

  Future<void> _completa() async {
    final s = Caudal.leer(context);
    // lo que ya suena sigue: solo se quita el corte automático del fragmento
    final yaSuena = s.reproductor.actual?['clave'] == _limpia['clave'] && s.reproductor.estado == EstadoRepro.sonando;
    widget.sonador.cancelar();
    if (!yaSuena) await s.reproducirPista(context, _limpia);
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.dedicatoria;
    final e = estiloDedicatoria(d.estilo);
    final s = Caudal.of(context);
    return SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Esp.l),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 380),
            child: Material(
              type: MaterialType.transparency,
              child: TarjetaDedicatoria(
                pista: widget.pista,
                dedicatoria: d,
                grande: true,
                etiqueta: widget.mia ? 'Tu dedicatoria para ${widget.otro}' : 'Dedicatoria de ${widget.otro}',
                pie: Column(mainAxisSize: MainAxisSize.min, children: [
                  if (!widget.mia)
                    ListenableBuilder(
                      listenable: s.reproductor,
                      builder: (context, _) {
                        final suena = _sonando && s.reproductor.estado == EstadoRepro.sonando;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: Esp.m),
                          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                            _Barras(activo: suena, color: e.acento),
                            const SizedBox(width: 8),
                            Flexible(
                              child: Text(
                                  suena
                                      ? 'Suena un fragmento de ${Dedicatoria.duracionFragmento.inSeconds} segundos'
                                      : _sonando
                                          ? 'Preparando la canción…'
                                          : 'El fragmento terminó',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(fontSize: 12.5, color: Colors.white.withValues(alpha: 0.8))),
                            ),
                          ]),
                        );
                      },
                    ),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: _completa,
                      style: FilledButton.styleFrom(backgroundColor: Colors.white, foregroundColor: Colors.black),
                      icon: const Icon(Icons.play_arrow_rounded, size: 22),
                      label: const Text('Escuchar la canción'),
                    ),
                  ),
                  const SizedBox(height: Esp.xs),
                  Wrap(alignment: WrapAlignment.center, spacing: Esp.s, children: [
                    if (!widget.mia)
                      TextButton.icon(
                        onPressed: () {
                          s.alternarMeGusta(_limpia);
                        },
                        style: TextButton.styleFrom(foregroundColor: Colors.white),
                        icon: const Icon(Icons.favorite_border_rounded, size: 18),
                        label: const Text('Me gusta'),
                      ),
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      style: TextButton.styleFrom(foregroundColor: Colors.white),
                      child: const Text('Cerrar'),
                    ),
                  ]),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Tres barritas que laten mientras suena (quietas con «Quitar animaciones»).
class _Barras extends StatefulWidget {
  const _Barras({required this.activo, required this.color});
  final bool activo;
  final Color color;

  @override
  State<_Barras> createState() => _BarrasState();
}

class _BarrasState extends State<_Barras> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 900));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _ajustar();
  }

  @override
  void didUpdateWidget(_Barras old) {
    super.didUpdateWidget(old);
    _ajustar();
  }

  void _ajustar() {
    final mover = widget.activo && MediaQuery.maybeDisableAnimationsOf(context) != true;
    if (mover && !_c.isAnimating) {
      _c.repeat();
    } else if (!mover && _c.isAnimating) {
      _c.stop();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
        child: SizedBox(
          width: 20,
          height: 18,
          child: AnimatedBuilder(
            animation: _c,
            builder: (_, _) => Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, crossAxisAlignment: CrossAxisAlignment.end, children: [
              for (var i = 0; i < 3; i++)
                Container(
                  width: 4,
                  height: widget.activo ? 5 + 13 * (0.5 + 0.5 * _onda(_c.value + i / 3)) : 5,
                  decoration: BoxDecoration(color: widget.color, borderRadius: BorderRadius.circular(2)),
                ),
            ]),
          ),
        ),
      );

  static double _onda(double t) => math.sin(t * 2 * math.pi);
}

// ============================================================ crearla

/// «Dedicar una canción»: elige la canción, escribe el mensaje, el estilo y dónde empieza el fragmento,
/// con vista previa. Devuelve la pista lista para mandar por el chat (con la dedicatoria dentro) o nulo.
/// Para quien no es donador muestra, en su lugar, el aviso de que es exclusivo.
Future<Json?> hojaDedicar(BuildContext context,
    {required String para, Json? sonando, BuscadorCanciones? buscador, Future<List<Json>> Function()? favoritas}) {
  final s = Caudal.leer(context);
  return showModalBottomSheet<Json>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: C.panel,
    showDragHandle: true,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
    builder: (_) => Dedicatoria.puedeEnviar()
        ? HojaDedicar(
            para: para,
            sonando: sonando ?? s.reproductor.actual,
            buscador: buscador,
            favoritas: favoritas,
          )
        : const _HojaBloqueada(),
  );
}

class _HojaBloqueada extends StatelessWidget {
  const _HojaBloqueada();

  @override
  Widget build(BuildContext context) => SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(Esp.xl, 0, Esp.xl, Esp.xl),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Text('💌', style: TextStyle(fontSize: 44)),
            const SizedBox(height: Esp.m),
            const Text('Las dedicatorias son para donadores',
                textAlign: TextAlign.center, style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900, height: 1.25)),
            const SizedBox(height: Esp.s),
            Text('Con tu apoyo puedes mandarle a un amigo una canción con una tarjeta bonita y un mensaje; '
                'al abrirla suena un fragmento. Recibirlas es gratis para todos.',
                textAlign: TextAlign.center, style: estiloSecundario.copyWith(fontSize: 14, height: 1.45)),
            const SizedBox(height: Esp.xl),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () {
                  Navigator.of(context).pop();
                  mostrarDonar(context);
                },
                icon: const Icon(Icons.favorite_rounded, size: 18),
                label: const Text('Donar aquí'),
              ),
            ),
          ]),
        ),
      );
}

class HojaDedicar extends StatefulWidget {
  const HojaDedicar({super.key, required this.para, this.sonando, this.buscador, this.favoritas});
  final String para;
  final Json? sonando;
  final BuscadorCanciones? buscador;
  final Future<List<Json>> Function()? favoritas;

  @override
  State<HojaDedicar> createState() => _HojaDedicarState();
}

class _HojaDedicarState extends State<HojaDedicar> {
  final _mensaje = TextEditingController();
  Json? _pista;
  String _estilo = Dedicatoria.estilos.first;
  double _inicio = 0;

  @override
  void initState() {
    super.initState();
    final s = widget.sonando;
    if (Dedicatoria.sePuedeDedicar(s)) _pista = Dedicatoria.pistaLimpia(s!);
    _mensaje.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _mensaje.dispose();
    super.dispose();
  }

  Future<void> _elegir() async {
    final p = await elegirCancion(context,
        titulo: 'Canción para ${widget.para}', buscador: widget.buscador, favoritas: widget.favoritas);
    if (p != null && mounted) setState(() => _pista = p);
  }

  Dedicatoria get _dedicatoria => Dedicatoria(
        mensaje: Dedicatoria.limpiarMensaje(_mensaje.text),
        estilo: _estilo,
        inicio: _inicio.round(),
      );

  void _enviar() {
    final p = _pista;
    if (p == null) return;
    Navigator.of(context).pop(Dedicatoria.conDedicatoria(p, _dedicatoria));
  }

  @override
  Widget build(BuildContext context) {
    final p = _pista;
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, Esp.xl),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
          Text('Dedicar una canción a ${widget.para}',
              maxLines: 2, overflow: TextOverflow.ellipsis, style: estiloTituloSeccion.copyWith(fontSize: 20)),
          const SizedBox(height: Esp.m),
          if (p != null)
            TarjetaDedicatoria(
              pista: p,
              dedicatoria: _dedicatoria,
              etiqueta: 'Dedicatoria para ${widget.para}',
            )
          else
            Container(
              padding: const EdgeInsets.all(Esp.xl),
              decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(18), border: Border.all(color: C.borde)),
              child: const Text('Elige una canción y aquí verás cómo queda la tarjeta.',
                  textAlign: TextAlign.center, style: estiloSecundario),
            ),
          const SizedBox(height: Esp.m),
          OutlinedButton.icon(
            onPressed: _elegir,
            icon: const Icon(Icons.library_music_rounded, size: 18),
            label: Text(p == null ? 'Elegir la canción' : 'Cambiar la canción'),
          ),
          const SizedBox(height: Esp.l),
          TextField(
            controller: _mensaje,
            minLines: 2,
            maxLines: 4,
            maxLength: Dedicatoria.maxMensaje,
            textCapitalization: TextCapitalization.sentences,
            decoration: InputDecoration(
              hintText: 'Escribe lo que quieres decirle…',
              filled: true,
              fillColor: C.superficie2,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
            ),
          ),
          const SizedBox(height: Esp.s),
          const Text('Estilo de la tarjeta', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
          const SizedBox(height: Esp.s),
          Wrap(spacing: Esp.m, runSpacing: Esp.s, children: [
            for (final e in estilosDedicatoria)
              Semantics(
                button: true,
                selected: _estilo == e.clave,
                label: e.nombre,
                excludeSemantics: true,
                child: GestureDetector(
                  onTap: () => setState(() => _estilo = e.clave),
                  child: AnimatedContainer(
                    key: ValueKey('estilo-${e.clave}'),
                    duration: Mov.rapido,
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: e.degradado,
                      border: Border.all(color: _estilo == e.clave ? Colors.white : e.acento.withValues(alpha: 0.4), width: _estilo == e.clave ? 3 : 1.5),
                    ),
                    child: _estilo == e.clave ? const Icon(Icons.check_rounded, size: 20, color: Colors.white) : null,
                  ),
                ),
              ),
          ]),
          const SizedBox(height: Esp.l),
          Row(children: [
            const Expanded(
                child: Text('El fragmento empieza en', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5))),
            Text(Dedicatoria.tiempo(_inicio.round()),
                style: TextStyle(fontWeight: FontWeight.w900, color: C.acento, fontFeatures: const [FontFeature.tabularFigures()])),
          ]),
          Slider(
            value: _inicio,
            min: 0,
            max: 240,
            divisions: 48,
            label: Dedicatoria.tiempo(_inicio.round()),
            onChanged: (v) => setState(() => _inicio = v),
          ),
          Text('Al abrirla, suena un trozo de ${Dedicatoria.duracionFragmento.inSeconds} segundos desde ahí.',
              style: estiloDetalle),
          const SizedBox(height: Esp.l),
          FilledButton.icon(
            onPressed: p == null ? null : _enviar,
            icon: const Icon(Icons.send_rounded, size: 18),
            label: const Text('Enviar dedicatoria'),
          ),
        ]),
      ),
    );
  }
}
