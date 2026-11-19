import 'package:flutter/material.dart';

import '../../nucleo/capsula_tiempo.dart';
import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/premium.dart';
import '../../nucleo/social.dart' show CancionFav;
import '../comunes.dart';
import '../paginas/donar.dart';
import '../servicios.dart';
import '../tema.dart';
import 'canje_pase.dart' show fechaLarga;
import 'elegir_cancion.dart';

const _oro = Color(0xFFFFC857);

/// «5 de marzo de 2027»: siempre con el año, porque una cápsula es de cuando pasa el tiempo.
String fechaCapsula(DateTime d) => fechaLarga(d, ahora: DateTime(d.year + 1));

/// «Se abre mañana», «Se abre en 12 días», «Se abre el 5 de marzo de 2027».
String cuandoSeAbre(CapsulaTiempo c, [DateTime? ahora]) {
  final d = c.diasFaltan(ahora);
  if (d <= 0) return 'Se abre hoy';
  if (d == 1) return 'Se abre mañana';
  if (d < 31) return 'Se abre en $d días · ${fechaCapsula(c.abre)}';
  return 'Se abre el ${fechaCapsula(c.abre)}';
}

// ============================================================ la tarjeta

/// La tarjeta de una cápsula abierta: lo que guardaste, tal cual, con cuánto tiempo pasó.
class TarjetaCapsula extends StatelessWidget {
  const TarjetaCapsula({super.key, required this.capsula, this.ahora, this.pie});
  final CapsulaTiempo capsula;
  final DateTime? ahora;
  final Widget? pie;

  @override
  Widget build(BuildContext context) {
    final c = capsula;
    return Container(
      padding: const EdgeInsets.all(Esp.xl),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF1B1440), Color(0xFF3A2A7A), Color(0xFF6B3F8F)],
        ),
        border: Border.all(color: _oro.withValues(alpha: 0.45)),
      ),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          const Text('⏳', style: TextStyle(fontSize: 16)),
          const SizedBox(width: 6),
          const Expanded(
            child: Text('CÁPSULA DEL TIEMPO',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900, letterSpacing: 1.2, color: _oro)),
          ),
        ]),
        const SizedBox(height: Esp.s),
        Text('${c.haceCuanto(ahora)} guardaste esto para ti',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, height: 1.25, color: Colors.white)),
        const SizedBox(height: Esp.l),
        Center(
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              boxShadow: [BoxShadow(color: _oro.withValues(alpha: 0.3), blurRadius: 30)],
            ),
            child: Portada(url: c.cancion.miniatura, lado: 132, radio: 18),
          ),
        ),
        const SizedBox(height: Esp.m),
        Text(c.cancion.titulo,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, height: 1.2, color: Colors.white)),
        Text(c.cancion.artista,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 14, color: Colors.white.withValues(alpha: 0.78))),
        if (c.mensaje.isNotEmpty) ...[
          const SizedBox(height: Esp.l),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: Esp.l, vertical: Esp.m),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.24),
              borderRadius: BorderRadius.circular(14),
              border: const Border(left: BorderSide(color: _oro, width: 3)),
            ),
            child: Text(c.mensaje,
                maxLines: 10,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 16, fontStyle: FontStyle.italic, height: 1.4, color: Colors.white)),
          ),
        ],
        Padding(
          padding: const EdgeInsets.only(top: Esp.m),
          child: Text('Guardada el ${fechaCapsula(c.creada)}',
              textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: Colors.white.withValues(alpha: 0.6))),
        ),
        if (pie != null) ...[const SizedBox(height: Esp.m), pie!],
      ]),
    );
  }
}

/// Abre la tarjeta de una cápsula a pantalla completa. Con [alOtroAnio] ofrece guardarla otro año más.
Future<void> abrirCapsula(BuildContext context, CapsulaTiempo c,
    {DateTime? ahora, Future<void> Function()? alOtroAnio}) {
  return showGeneralDialog<void>(
    context: context,
    useRootNavigator: true,
    barrierDismissible: true,
    barrierLabel: 'Cerrar la cápsula',
    barrierColor: Colors.black.withValues(alpha: 0.78),
    transitionDuration: MediaQuery.maybeDisableAnimationsOf(context) == true ? Duration.zero : Mov.entrada,
    pageBuilder: (_, _, _) => _CapsulaAbierta(capsula: c, ahora: ahora, alOtroAnio: alOtroAnio),
    transitionBuilder: (_, a, _, hijo) {
      final curva = CurvedAnimation(parent: a, curve: Mov.curvaEntrada);
      return FadeTransition(
        opacity: curva,
        child: SlideTransition(
          position: Tween<Offset>(begin: const Offset(0, 0.06), end: Offset.zero).animate(curva),
          child: hijo,
        ),
      );
    },
  );
}

class _CapsulaAbierta extends StatefulWidget {
  const _CapsulaAbierta({required this.capsula, this.ahora, this.alOtroAnio});
  final CapsulaTiempo capsula;
  final DateTime? ahora;
  final Future<void> Function()? alOtroAnio;

  @override
  State<_CapsulaAbierta> createState() => _CapsulaAbiertaState();
}

class _CapsulaAbiertaState extends State<_CapsulaAbierta> {
  bool _guardando = false;

  Future<void> _otroAnio() async {
    if (_guardando) return;
    setState(() => _guardando = true);
    try {
      await widget.alOtroAnio!();
    } finally {
      if (mounted) Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final c = widget.capsula;
    return SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Esp.l),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 380),
            child: Material(
              type: MaterialType.transparency,
              child: TarjetaCapsula(
                capsula: c,
                ahora: widget.ahora,
                pie: Column(mainAxisSize: MainAxisSize.min, children: [
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: () {
                        s.reproducirPista(context, c.cancion.comoPista());
                        Navigator.of(context).pop();
                      },
                      style: FilledButton.styleFrom(backgroundColor: _oro, foregroundColor: Colors.black),
                      icon: const Icon(Icons.play_arrow_rounded, size: 22),
                      label: const Text('Escuchar la canción'),
                    ),
                  ),
                  const SizedBox(height: Esp.xs),
                  Wrap(alignment: WrapAlignment.center, spacing: Esp.s, children: [
                    if (widget.alOtroAnio != null)
                      TextButton.icon(
                        onPressed: _guardando ? null : _otroAnio,
                        style: TextButton.styleFrom(foregroundColor: Colors.white),
                        icon: const Icon(Icons.history_rounded, size: 18),
                        label: const Text('Guardarla otro año'),
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

/// Al abrir la app: si hay cápsulas que ya llegaron a su día, se enseñan una tras otra (la más antigua
/// primero). Cada una se marca como vista antes de enseñarla, así que no vuelve a salir sola; queda en
/// «Cápsula del tiempo» para verla cuando quieras. Devuelve cuántas se enseñaron.
Future<int> mostrarCapsulasPendientes(BuildContext context, {DateTime? ahora}) async {
  final cap = CapsulasTiempo.i;
  var vistas = 0;
  // se vuelve a preguntar tras cada una: no se enseña una que se borró mientras tanto
  while (context.mounted) {
    final pendientes = cap.pendientes(ahora);
    if (pendientes.isEmpty) break;
    final c = pendientes.first;
    await cap.marcarVista(c.id, ahora);
    if (!context.mounted) break;
    vistas++;
    await abrirCapsula(context, c,
        ahora: ahora, alOtroAnio: Premium.i.activo ? () => _otroAnio(context, c, ahora) : null);
  }
  return vistas;
}

Future<void> _otroAnio(BuildContext context, CapsulaTiempo c, DateTime? ahora) async {
  final r = await CapsulasTiempo.i.crear(
    cancion: c.cancion,
    mensaje: c.mensaje,
    abre: CapsulaTiempo.unAnioDespues(ahora ?? DateTime.now()),
    ahora: ahora,
  );
  if (context.mounted) {
    Caudal.leer(context).avisar(r.ok ? 'Guardada otro año: ${cuandoSeAbre(r.capsula!, ahora).toLowerCase()}.' : r.mensaje);
  }
}

// ============================================================ la lista

/// «Cápsula del tiempo»: tus cápsulas guardadas y las ya abiertas, y la hoja para crear una nueva.
class CapsulasPagina extends StatelessWidget {
  const CapsulasPagina({super.key, this.ahora, this.buscador, this.favoritas});

  /// Para pruebas: el «hoy».
  final DateTime? ahora;
  final BuscadorCanciones? buscador;
  final Future<List<Json>> Function()? favoritas;

  Future<void> _nueva(BuildContext context) async {
    if (!Premium.i.activo) {
      Caudal.leer(context).avisar('Es exclusivo de donadores: dona o canjea un código de prueba para crear cápsulas.');
      return;
    }
    final r = await showModalBottomSheet<ResultadoCapsula>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: C.panel,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => HojaNuevaCapsula(
        sonando: Caudal.leer(context).reproductor.actual,
        ahora: ahora,
        buscador: buscador,
        favoritas: favoritas,
      ),
    );
    if (r != null && r.ok && context.mounted) {
      Caudal.leer(context).avisar('Cápsula guardada: ${cuandoSeAbre(r.capsula!, ahora).toLowerCase()}.');
    }
  }

  Future<void> _borrar(BuildContext context, CapsulaTiempo c) async {
    final si = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.panel,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: C.borde)),
        title: const Text('¿Borrar esta cápsula?'),
        content: Text('«${c.cancion.titulo}» y tu mensaje se borrarán de este teléfono. No se puede deshacer.',
            style: estiloSecundario),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Borrar')),
        ],
      ),
    );
    if (si == true) await CapsulasTiempo.i.borrar(c.id);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([CapsulasTiempo.i, Premium.i]),
      builder: (context, _) {
        final activo = Premium.i.activo;
        final guardadas = CapsulasTiempo.i.guardadas;
        final vistas = CapsulasTiempo.i.vistas;
        return Scaffold(
          appBar: AppBar(
            backgroundColor: C.fondoVivo,
            surfaceTintColor: Colors.transparent,
            title: const Text('Cápsula del tiempo', style: estiloTituloBarra),
          ),
          body: ListView(padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, 40), children: [
            Container(
              padding: const EdgeInsets.all(Esp.l),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                gradient: LinearGradient(colors: [_oro.withValues(alpha: 0.22), C.violeta.withValues(alpha: 0.2)]),
                border: Border.all(color: C.borde),
              ),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('⏳', style: TextStyle(fontSize: 26)),
                const SizedBox(width: Esp.m),
                Expanded(
                  child: Text(
                      'Guarda hoy una canción y un mensaje para ti. Caudal te los vuelve a enseñar el día que elijas '
                      '(por defecto, dentro de un año) cuando abras la app. Se quedan solo en este teléfono.',
                      style: estiloSecundario.copyWith(fontSize: 14, height: 1.4, color: C.texto)),
                ),
              ]),
            ),
            const SizedBox(height: Esp.l),
            if (!activo)
              Container(
                margin: const EdgeInsets.only(bottom: Esp.l),
                padding: const EdgeInsets.all(Esp.m),
                decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(14), border: Border.all(color: C.borde)),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Row(children: [
                    Icon(Icons.lock_outline_rounded, size: 20, color: _oro),
                    SizedBox(width: 10),
                    Expanded(child: Text('Crear cápsulas es exclusivo de donadores', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
                  ]),
                  const SizedBox(height: 6),
                  const Text('Las que ya guardaste se siguen abriendo en su fecha.', style: estiloSecundario),
                  const SizedBox(height: 10),
                  FilledButton.icon(
                    onPressed: () => mostrarDonar(context),
                    icon: const Icon(Icons.favorite_rounded, size: 18),
                    label: const Text('Donar aquí'),
                  ),
                ]),
              ),
            FilledButton.icon(
              onPressed: () => _nueva(context),
              icon: const Icon(Icons.add_rounded, size: 20),
              label: const Text('Nueva cápsula'),
            ),
            if (guardadas.isEmpty && vistas.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: Esp.xxl),
                child: Center(
                    child: Text('Todavía no guardaste ninguna cápsula.', textAlign: TextAlign.center, style: estiloSecundario)),
              ),
            if (guardadas.isNotEmpty) ...[
              const SizedBox(height: Esp.xl),
              Text('Guardadas · ${guardadas.length}', style: estiloTituloSeccion.copyWith(fontSize: 18)),
              const SizedBox(height: Esp.s),
              for (final c in guardadas) _FilaCapsula(capsula: c, ahora: ahora, alBorrar: () => _borrar(context, c)),
            ],
            if (vistas.isNotEmpty) ...[
              const SizedBox(height: Esp.xl),
              Text('Ya abiertas · ${vistas.length}', style: estiloTituloSeccion.copyWith(fontSize: 18)),
              const SizedBox(height: Esp.s),
              for (final c in vistas)
                _FilaCapsula(
                  capsula: c,
                  ahora: ahora,
                  abierta: true,
                  alTocar: () => abrirCapsula(context, c, ahora: ahora),
                  alBorrar: () => _borrar(context, c),
                ),
            ],
          ]),
        );
      },
    );
  }
}

class _FilaCapsula extends StatelessWidget {
  const _FilaCapsula({required this.capsula, required this.alBorrar, this.ahora, this.abierta = false, this.alTocar});
  final CapsulaTiempo capsula;
  final DateTime? ahora;
  final bool abierta;
  final VoidCallback? alTocar;
  final VoidCallback alBorrar;

  @override
  Widget build(BuildContext context) {
    final c = capsula;
    return Padding(
      key: ValueKey('capsula-${c.id}'),
      padding: const EdgeInsets.only(bottom: Esp.s),
      child: Material(
        color: C.superficie2,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: alTocar,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(Esp.m, Esp.m, Esp.xs, Esp.m),
            child: Row(children: [
              // sin abrir no se enseña la carátula: la sorpresa es parte de la cápsula
              if (abierta)
                Portada(url: c.cancion.miniatura, lado: 52, radio: 10)
              else
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(color: C.superficie3, borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.lock_clock_rounded, color: _oro, size: 24),
                ),
              const SizedBox(width: Esp.m),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  // una cápsula sin abrir no cuenta qué guarda hasta su día: solo la fecha
                  Text(abierta ? c.cancion.titulo : 'Cápsula para ti',
                      maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15.5)),
                  const SizedBox(height: 2),
                  Text(
                      abierta
                          ? '${c.cancion.artista} · guardada el ${fechaCapsula(c.creada)}'
                          : cuandoSeAbre(c, ahora),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: estiloSecundario),
                ]),
              ),
              IconButton(
                tooltip: 'Borrar la cápsula',
                icon: const Icon(Icons.delete_outline_rounded, size: 20, color: C.texto2),
                onPressed: alBorrar,
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

// ============================================================ crear

/// La hoja de «Nueva cápsula»: canción, mensaje y fecha (por defecto, dentro de un año).
/// Devuelve el [ResultadoCapsula] (ya guardada) al cerrarse con «Guardar».
class HojaNuevaCapsula extends StatefulWidget {
  const HojaNuevaCapsula({super.key, this.sonando, this.ahora, this.buscador, this.favoritas, this.elegirFecha});
  final Json? sonando;
  final DateTime? ahora;
  final BuscadorCanciones? buscador;
  final Future<List<Json>> Function()? favoritas;

  /// Para pruebas: cómo se elige la fecha (por defecto, el calendario de siempre).
  final Future<DateTime?> Function(BuildContext context, DateTime inicial, DateTime primera, DateTime ultima)? elegirFecha;

  @override
  State<HojaNuevaCapsula> createState() => _HojaNuevaCapsulaState();
}

class _HojaNuevaCapsulaState extends State<HojaNuevaCapsula> {
  final _mensaje = TextEditingController();
  CancionFav? _cancion;
  late DateTime _abre;
  bool _guardando = false;
  String? _error;

  DateTime get _hoy => widget.ahora ?? DateTime.now();

  @override
  void initState() {
    super.initState();
    _abre = CapsulaTiempo.unAnioDespues(_hoy);
    final s = widget.sonando;
    if (s != null && '${s['video_id'] ?? ''}'.isNotEmpty) _cancion = CancionFav.dePista(s);
    _mensaje.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _mensaje.dispose();
    super.dispose();
  }

  Future<void> _elegirCancion() async {
    final p = await elegirCancion(context, titulo: 'Canción para tu cápsula', buscador: widget.buscador, favoritas: widget.favoritas);
    if (p != null && mounted) setState(() => _cancion = CancionFav.dePista(p));
  }

  Future<void> _elegirFecha() async {
    final primera = CapsulaTiempo.manana(_hoy);
    final ultima = CapsulaTiempo.masLejos(_hoy);
    final f = widget.elegirFecha != null
        ? await widget.elegirFecha!(context, _abre, primera, ultima)
        : await showDatePicker(
            context: context,
            initialDate: _abre,
            firstDate: primera,
            lastDate: ultima,
            helpText: 'Elige el día en que se abrirá',
          );
    if (f != null && mounted) setState(() => _abre = DateTime(f.year, f.month, f.day));
  }

  void _atajo(DateTime f) => setState(() => _abre = f);

  Future<void> _guardar() async {
    if (_guardando) return;
    setState(() {
      _guardando = true;
      _error = null;
    });
    final r = await CapsulasTiempo.i.crear(cancion: _cancion, mensaje: _mensaje.text, abre: _abre, ahora: widget.ahora);
    if (!mounted) return;
    if (r.ok) {
      Navigator.of(context).pop(r);
    } else {
      setState(() {
        _guardando = false;
        _error = r.mensaje;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _cancion;
    final h = _hoy;
    final atajos = <(String, DateTime)>[
      ('3 meses', CapsulaTiempo.masMeses(h, 3)),
      ('6 meses', CapsulaTiempo.masMeses(h, 6)),
      ('1 año', CapsulaTiempo.unAnioDespues(h)),
      ('5 años', CapsulaTiempo.masMeses(h, 60)),
    ];
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, Esp.xl),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
          Text('Nueva cápsula del tiempo', style: estiloTituloSeccion.copyWith(fontSize: 20)),
          const SizedBox(height: Esp.m),
          Material(
            color: C.superficie2,
            borderRadius: BorderRadius.circular(16),
            child: InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: _elegirCancion,
              child: Padding(
                padding: const EdgeInsets.all(Esp.m),
                child: Row(children: [
                  if (c != null)
                    Portada(url: c.miniatura, lado: 52, radio: 10)
                  else
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(color: C.superficie3, borderRadius: BorderRadius.circular(10)),
                      child: Icon(Icons.library_music_rounded, color: C.acento),
                    ),
                  const SizedBox(width: Esp.m),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(c?.titulo ?? 'Elegir la canción',
                          maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15.5)),
                      Text(c?.artista ?? 'La que suena ahora, tus «me gusta» o una búsqueda',
                          maxLines: 2, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                    ]),
                  ),
                  const Icon(Icons.chevron_right_rounded, color: C.texto3),
                ]),
              ),
            ),
          ),
          const SizedBox(height: Esp.l),
          TextField(
            controller: _mensaje,
            minLines: 3,
            maxLines: 6,
            maxLength: CapsulaTiempo.maxMensaje,
            textCapitalization: TextCapitalization.sentences,
            decoration: InputDecoration(
              hintText: 'Escríbete algo: cómo estás hoy, qué esperas del futuro…',
              filled: true,
              fillColor: C.superficie2,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
            ),
          ),
          const SizedBox(height: Esp.s),
          const Text('Se abrirá el', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
          const SizedBox(height: Esp.s),
          OutlinedButton.icon(
            onPressed: _elegirFecha,
            icon: const Icon(Icons.event_rounded, size: 18),
            label: Text(fechaCapsula(_abre)),
          ),
          const SizedBox(height: Esp.s),
          Wrap(spacing: Esp.s, runSpacing: Esp.xs, children: [
            for (final (nombre, f) in atajos)
              ChoiceChip(
                label: Text(nombre),
                selected: _abre.year == f.year && _abre.month == f.month && _abre.day == f.day,
                onSelected: (_) => _atajo(f),
              ),
          ]),
          if (_error != null) ...[
            const SizedBox(height: Esp.s),
            Semantics(liveRegion: true, child: Text(_error!, style: const TextStyle(color: C.error, fontSize: 13.5, height: 1.35))),
          ],
          const SizedBox(height: Esp.l),
          FilledButton.icon(
            onPressed: c == null || _guardando ? null : _guardar,
            icon: _guardando
                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.lock_clock_rounded, size: 20),
            label: const Text('Guardar cápsula'),
          ),
        ]),
      ),
    );
  }
}
