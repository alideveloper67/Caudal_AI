import 'dart:math' as math;
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/mascota_app.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/portada_perfil.dart';
import '../../nucleo/premium.dart';
import '../../nucleo/social.dart';
import '../comunes.dart';
import '../paginas/donar.dart';
import '../paginas/perfil_comun.dart' show socialDe, textoSinConexion;
import '../servicios.dart';
import '../tema.dart';
import 'elegir_cancion.dart';
import 'mascota_sprite.dart';

// ============================================================ la tarjeta (el banner)

/// La portada tal como se ve arriba del perfil: la canción del momento, un fragmento de letra y la mascota.
/// Se ajusta sola a cualquier ancho (320 incluido) y al tamaño de letra del sistema: nada tiene alto fijo.
class PortadaTarjeta extends StatelessWidget {
  const PortadaTarjeta({
    super.key,
    required this.portada,
    required this.color,
    this.propia = false,
    this.alReproducir,
    this.alEditar,
    this.animar = true,
  });

  final PortadaPerfil portada;
  final Color color;

  /// Es la mía: la etiqueta dice «Tu canción del momento» y aparece el botón de editar.
  final bool propia;
  final VoidCallback? alReproducir;
  final VoidCallback? alEditar;
  final bool animar;

  /// El lado más grande que ocupa la mascota en la tarjeta (se reduce la escala de las grandes).
  static const ladoMascota = 66.0;

  static Mascota? mascotaDe(String clave) {
    if (clave.isEmpty) return null;
    for (final m in MascotaApp.i.catalogo) {
      if (m.clave == clave) return m;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final c = portada.cancion;
    final m = mascotaDe(portada.mascota);
    final claro = Color.lerp(color, Colors.white, 0.72)!;
    final etiqueta = propia ? 'Tu canción del momento' : 'Su canción del momento';
    return Semantics(
      container: true,
      label: 'Portada del perfil',
      child: ClipRRect(
        borderRadius: BorderRadius.circular(26),
        child: Stack(children: [
          // el fondo: la carátula muy difuminada y teñida del color del perfil
          Positioned.fill(
            child: RepaintBoundary(
              child: Stack(fit: StackFit.expand, children: [
                DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color.lerp(color, C.fondo, 0.45)!, Color.lerp(color, C.fondo, 0.85)!],
                    ),
                  ),
                ),
                if (c != null && c.miniatura.isNotEmpty)
                  Opacity(
                    opacity: 0.38,
                    child: ImageFiltered(
                      imageFilter: ImageFilter.blur(sigmaX: 28, sigmaY: 28, tileMode: TileMode.clamp),
                      // pequeña: al difuminarla da igual el detalle y así pesa poco en memoria
                      child: Portada(url: c.miniatura, lado: 96, radio: 0),
                    ),
                  ),
                DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [Colors.black.withValues(alpha: 0.05), Colors.black.withValues(alpha: 0.42)],
                    ),
                  ),
                ),
              ]),
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(Esp.l, Esp.m, Esp.l, Esp.l),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(26),
              border: Border.all(color: claro.withValues(alpha: 0.22)),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Row(children: [
                Icon(Icons.graphic_eq_rounded, size: 17, color: claro),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(c == null ? 'Portada' : etiqueta,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, letterSpacing: 0.3, color: claro)),
                ),
                if (alEditar != null)
                  Semantics(
                    button: true,
                    label: 'Editar mi portada',
                    child: InkResponse(
                      onTap: alEditar,
                      radius: 22,
                      child: Padding(
                        padding: const EdgeInsets.all(6),
                        child: Icon(Icons.edit_rounded, size: 18, color: claro),
                      ),
                    ),
                  ),
              ]),
              if (c != null) ...[
                const SizedBox(height: Esp.s),
                _FilaCancion(cancion: c, color: claro, alReproducir: alReproducir),
              ],
              if (portada.letra.isNotEmpty || m != null) ...[
                SizedBox(height: c == null ? Esp.xs : Esp.m),
                Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Expanded(
                    child: portada.letra.isEmpty
                        ? const SizedBox.shrink()
                        : _Letra(texto: portada.letra, color: claro),
                  ),
                  if (m != null) ...[
                    const SizedBox(width: Esp.s),
                    MascotaSprite(
                      mascota: m,
                      escala: math.min(3.0, ladoMascota / math.max(m.ancho, m.alto)),
                      animar: animar,
                    ),
                  ],
                ]),
              ],
            ]),
          ),
        ]),
      ),
    );
  }
}

class _FilaCancion extends StatelessWidget {
  const _FilaCancion({required this.cancion, required this.color, this.alReproducir});
  final CancionFav cancion;
  final Color color;
  final VoidCallback? alReproducir;

  @override
  Widget build(BuildContext context) {
    final puede = alReproducir != null && cancion.videoId.isNotEmpty;
    final fila = Row(children: [
      Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.45), blurRadius: 18, offset: const Offset(0, 6))],
        ),
        child: Portada(url: cancion.miniatura, lado: 72, radio: 14),
      ),
      const SizedBox(width: Esp.m),
      Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(cancion.titulo,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, height: 1.18, color: Colors.white)),
          const SizedBox(height: 2),
          Text(cancion.artista,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 13.5, color: Colors.white.withValues(alpha: 0.78))),
        ]),
      ),
      if (puede) ...[
        const SizedBox(width: Esp.s),
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(shape: BoxShape.circle, color: Colors.white.withValues(alpha: 0.18)),
          child: const Icon(Icons.play_arrow_rounded, size: 30, color: Colors.white),
        ),
      ],
    ]);
    if (!puede) return fila;
    return Semantics(
      button: true,
      label: 'Escuchar ${cancion.titulo}',
      excludeSemantics: true,
      child: Pulsable(
        child: InkWell(borderRadius: BorderRadius.circular(16), onTap: alReproducir, child: fila),
      ),
    );
  }
}

class _Letra extends StatelessWidget {
  const _Letra({required this.texto, required this.color});
  final String texto;
  final Color color;

  @override
  Widget build(BuildContext context) => IntrinsicHeight(
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Container(width: 3, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(3))),
          const SizedBox(width: 10),
          Expanded(
            child: Text('“$texto”',
                maxLines: PortadaPerfil.maxLineas + 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 15.5, fontStyle: FontStyle.italic, height: 1.35, color: Colors.white)),
          ),
        ]),
      );
}

// ============================================================ en el perfil

/// Lo que se pone arriba del perfil: la portada de esa persona (si es mía o de una amiga y existe) o, en
/// mi propio perfil, la invitación a crearla. Se encarga de preguntar al servidor y de no estorbar:
/// si no hay nada que ver, no ocupa lugar.
class PortadaDePerfil extends StatefulWidget {
  const PortadaDePerfil({
    super.key,
    required this.usuario,
    required this.propia,
    required this.color,
    required this.social,
    this.esAmiga = false,
    this.alReproducir,
  });

  final String usuario;
  final bool propia;
  final bool esAmiga;
  final Color color;
  final Social? social;

  /// Para pruebas o para cambiar cómo suena; por defecto suena con el reproductor de Caudal.
  final void Function(CancionFav)? alReproducir;

  @override
  State<PortadaDePerfil> createState() => _PortadaDePerfilState();
}

class _PortadaDePerfilState extends State<PortadaDePerfil> {
  PortadaPerfil? _ajena;
  bool _pedida = false;

  bool get _debeConsultar => widget.propia || widget.esAmiga;

  @override
  void initState() {
    super.initState();
    MascotaApp.i.cargarCatalogo();
    if (widget.propia) PortadasPerfil.i.cargarLocal(Caudal.leer(context).cuenta.id);
    _cargar();
  }

  @override
  void didUpdateWidget(PortadaDePerfil old) {
    super.didUpdateWidget(old);
    if (old.usuario != widget.usuario || old.social != widget.social || old.esAmiga != widget.esAmiga) {
      _pedida = false;
      _ajena = null;
      _cargar();
    }
  }

  Future<void> _cargar() async {
    final social = widget.social;
    if (_pedida || social == null || !_debeConsultar) return;
    _pedida = true;
    try {
      final p = await PortadasPerfil.i.ver(social, widget.usuario, esMia: widget.propia);
      if (mounted && !widget.propia) setState(() => _ajena = p);
    } catch (_) {
      // sin internet se queda lo último que se sabía (lo mío, del teléfono; lo de otros, nada)
    }
  }

  void _reproducir(CancionFav c) {
    final f = widget.alReproducir;
    if (f != null) return f(c);
    final s = Caudal.leer(context);
    s.reproducirPista(context, c.comoPista());
  }

  Future<void> _editar() async {
    await Navigator.of(context).push(MaterialPageRoute<bool>(builder: (_) => const PortadaPagina()));
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.propia) {
      final p = _ajena;
      if (p == null) return const SizedBox.shrink();
      return ListenableBuilder(
        listenable: MascotaApp.i,
        builder: (context, _) => _marco(PortadaTarjeta(
            portada: p, color: widget.color, alReproducir: p.cancion == null ? null : () => _reproducir(p.cancion!))),
      );
    }
    return ListenableBuilder(
      listenable: Listenable.merge([PortadasPerfil.i, Premium.i, MascotaApp.i]),
      builder: (context, _) {
        final activo = Premium.i.activo;
        final mia = PortadasPerfil.i.mia;
        if (activo && !mia.vacia) {
          return _marco(PortadaTarjeta(
            portada: mia,
            color: widget.color,
            propia: true,
            alEditar: _editar,
            alReproducir: mia.cancion == null ? null : () => _reproducir(mia.cancion!),
          ));
        }
        return _marco(_Invitacion(activo: activo, color: widget.color, alTocar: _editar));
      },
    );
  }

  Widget _marco(Widget hijo) =>
      Padding(padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, 0), child: hijo);
}

class _Invitacion extends StatelessWidget {
  const _Invitacion({required this.activo, required this.color, required this.alTocar});
  final bool activo;
  final Color color;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: activo ? 'Crear mi portada' : 'Portada del perfil, exclusiva para donadores',
        child: Pulsable(
          child: InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: alTocar,
            child: Container(
              padding: const EdgeInsets.all(Esp.l),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                color: C.superficie,
                border: Border.all(color: color.withValues(alpha: 0.35)),
              ),
              child: Row(children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(shape: BoxShape.circle, color: color.withValues(alpha: 0.18)),
                  child: Icon(activo ? Icons.add_photo_alternate_rounded : Icons.lock_outline_rounded, color: color, size: 22),
                ),
                const SizedBox(width: Esp.m),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(activo ? 'Crea tu portada' : 'Portada del perfil',
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15.5)),
                    const SizedBox(height: 2),
                    Text(
                        activo
                            ? 'Fija tu canción del momento, un trocito de letra y tu mascota. La ven tus amigos.'
                            : 'Exclusiva para donadores: tu canción del momento, una letra y tu mascota arriba del perfil.',
                        style: estiloSecundario),
                  ]),
                ),
                const Icon(Icons.chevron_right_rounded, color: C.texto3),
              ]),
            ),
          ),
        ),
      );
}

// ============================================================ el editor

/// «Portada del perfil»: se arma con vista previa en vivo. Con los beneficios activos se guarda en el
/// perfil; sin ellos se puede probar pero no guardar (como «Personalizar»).
class PortadaPagina extends StatefulWidget {
  const PortadaPagina({super.key, this.elegirCancionPropia});

  /// Para las pruebas: cómo se elige la canción (por defecto, la hoja de siempre).
  final Future<Json?> Function(BuildContext context)? elegirCancionPropia;

  @override
  State<PortadaPagina> createState() => _PortadaPaginaState();
}

class _PortadaPaginaState extends State<PortadaPagina> {
  final _letra = TextEditingController();
  PortadaPerfil _base = PortadaPerfil.vacio;
  CancionFav? _cancion;
  String _mascota = '';
  bool _guardando = false;
  bool _tocado = false;

  @override
  void initState() {
    super.initState();
    MascotaApp.i.cargarCatalogo();
    _letra.addListener(() => setState(() => _tocado = true));
    _iniciar();
  }

  Future<void> _iniciar() async {
    final s = Caudal.leer(context);
    await PortadasPerfil.i.cargarLocal(s.cuenta.id);
    if (!mounted) return;
    _poner(PortadasPerfil.i.mia, ajustarMascota: true);
    final social = socialDe(context);
    if (social == null) return;
    try {
      await PortadasPerfil.i.ver(social, s.cuenta.usuario, esMia: true);
      // si no tocó nada mientras llegaba lo del servidor, se pone al día
      if (mounted && !_tocado) _poner(PortadasPerfil.i.mia, ajustarMascota: true);
    } catch (_) {}
  }

  void _poner(PortadaPerfil p, {bool ajustarMascota = false}) {
    setState(() {
      _base = p;
      _cancion = p.cancion;
      _letra.value = TextEditingValue(text: p.letra);
      // si aún no tiene portada, se propone la mascotita que ya lleva en el reproductor
      _mascota = p.mascota.isEmpty && ajustarMascota && p.vacia && MascotaApp.i.activa ? MascotaApp.i.clave : p.mascota;
      _tocado = false;
    });
  }

  @override
  void dispose() {
    _letra.dispose();
    super.dispose();
  }

  PortadaPerfil get _borrador => PortadaPerfil(
        cancion: _cancion,
        letra: PortadaPerfil.limpiarLetra(_letra.text),
        mascota: _mascota,
      );

  bool get _cambio => _borrador != _base;

  void _aviso(String t) => Caudal.leer(context).avisar(t);

  Future<void> _elegirCancion() async {
    final r = widget.elegirCancionPropia != null
        ? await widget.elegirCancionPropia!(context)
        : await elegirCancion(context, titulo: 'Tu canción del momento');
    if (r == null || !mounted) return;
    setState(() {
      _cancion = CancionFav.dePista(r);
      _tocado = true;
    });
  }

  Future<void> _guardar({bool quitar = false}) async {
    if (_guardando) return;
    if (!Premium.i.activo) {
      _aviso('Es exclusivo de donadores: dona o canjea un código de prueba para guardarla.');
      return;
    }
    final social = socialDe(context);
    if (social == null) {
      _aviso(textoSinConexion(context));
      return;
    }
    setState(() => _guardando = true);
    try {
      await PortadasPerfil.i.guardar(social, quitar ? PortadaPerfil.vacio : _borrador);
      if (!mounted) return;
      _aviso(quitar ? 'Quitaste tu portada.' : 'Tu portada ya se ve en tu perfil.');
      Navigator.of(context).pop(true);
    } on ErrorNube catch (e) {
      if (mounted) {
        setState(() => _guardando = false);
        _aviso(e.mensaje);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _guardando = false);
        _aviso('No se pudo guardar. Revisa tu internet e inténtalo otra vez.');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([Premium.i, MascotaApp.i]),
      builder: (context, _) {
        final activo = Premium.i.activo;
        final color = C.acento;
        final vista = _borrador;
        // todas las de esta cuenta: sin beneficios se pueden probar en la vista previa, no guardar
        final mascotas = MascotaApp.i.disponibles;
        return Scaffold(
          appBar: AppBar(
            backgroundColor: C.fondoVivo,
            surfaceTintColor: Colors.transparent,
            title: const Text('Portada del perfil', style: estiloTituloBarra),
          ),
          body: ListView(padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, 40), children: [
            Semantics(
              label: 'Vista previa de tu portada',
              child: vista.vacia
                  ? Container(
                      padding: const EdgeInsets.all(Esp.xl),
                      decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(26), color: C.superficie, border: Border.all(color: C.borde)),
                      child: const Center(
                          child: Text('Elige una canción, una letra o una mascota y la verás aquí.',
                              textAlign: TextAlign.center, style: estiloSecundario)),
                    )
                  : PortadaTarjeta(portada: vista, color: color, propia: true),
            ),
            const SizedBox(height: Esp.l),
            if (!activo) _bloqueo() else _banda(),
            const SizedBox(height: Esp.xl),
            _titulo('Canción del momento'),
            _tarjetaCancion(),
            const SizedBox(height: Esp.xl),
            _titulo('Un fragmento de letra'),
            TextField(
              controller: _letra,
              minLines: 2,
              maxLines: 4,
              maxLength: PortadaPerfil.maxLetra,
              textCapitalization: TextCapitalization.sentences,
              decoration: InputDecoration(
                hintText: 'Esa frase que te define esta semana…',
                filled: true,
                fillColor: C.superficie2,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: Esp.l),
            _titulo('Tu mascota'),
            if (mascotas.isEmpty && MascotaApp.i.catalogo.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: Esp.m),
                child: Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))),
              )
            else
              Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
                _CasillaMascota(
                  nombre: 'Ninguna',
                  elegida: _mascota.isEmpty,
                  hijo: const Icon(Icons.block_rounded, size: 28, color: C.texto3),
                  alTocar: () => setState(() {
                    _mascota = '';
                    _tocado = true;
                  }),
                ),
                for (final m in mascotas)
                  _CasillaMascota(
                    key: ValueKey('mascota-${m.clave}'),
                    nombre: m.nombre,
                    elegida: _mascota == m.clave,
                    hijo: MascotaSprite(
                        mascota: m, escala: math.min(3.0, 44 / math.max(m.ancho, m.alto)), animar: false),
                    alTocar: () => setState(() {
                      _mascota = m.clave;
                      _tocado = true;
                    }),
                  ),
              ]),
            const SizedBox(height: Esp.xl),
            Row(children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: _guardando || !_cambio ? null : () => _guardar(),
                  icon: _guardando
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.check_rounded, size: 20),
                  label: const Text('Guardar portada'),
                ),
              ),
            ]),
            if (!_base.vacia) ...[
              const SizedBox(height: Esp.s),
              Center(
                child: TextButton.icon(
                  onPressed: _guardando ? null : () => _guardar(quitar: true),
                  icon: const Icon(Icons.delete_outline_rounded, size: 18),
                  label: const Text('Quitar mi portada'),
                ),
              ),
            ],
          ]),
        );
      },
    );
  }

  Widget _titulo(String t) => Padding(
        padding: const EdgeInsets.only(bottom: Esp.s),
        child: Text(t, style: estiloTituloSeccion.copyWith(fontSize: 18)),
      );

  Widget _banda() => Container(
        padding: const EdgeInsets.all(Esp.m),
        decoration: BoxDecoration(
          color: C.superficie2,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: C.acento.withValues(alpha: 0.4)),
        ),
        child: Row(children: [
          Icon(Icons.group_rounded, color: C.acento, size: 22),
          const SizedBox(width: 12),
          const Expanded(
            child: Text('Tu portada la ven tus amigos arriba de tu perfil.',
                style: TextStyle(fontWeight: FontWeight.w700, height: 1.3)),
          ),
        ]),
      );

  Widget _bloqueo() => Container(
        padding: const EdgeInsets.all(Esp.m),
        decoration: BoxDecoration(
          color: C.superficie2,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: C.borde),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.lock_outline_rounded, size: 20, color: Color(0xFFFFC857)),
            SizedBox(width: 10),
            Expanded(child: Text('Exclusivo para donadores', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
          ]),
          const SizedBox(height: 6),
          const Text('Puedes armarla y ver cómo queda. Para guardarla en tu perfil, dona con Yape o canjea un código de prueba.',
              style: estiloSecundario),
          const SizedBox(height: 10),
          FilledButton.icon(
            onPressed: () => mostrarDonar(context),
            icon: const Icon(Icons.favorite_rounded, size: 18),
            label: const Text('Donar aquí'),
          ),
        ]),
      );

  Widget _tarjetaCancion() {
    final c = _cancion;
    return Material(
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
                Text(c?.titulo ?? 'Elegir una canción',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15.5)),
                Text(c == null ? 'La que suena ahora, tus «me gusta» o una búsqueda' : c.artista,
                    maxLines: 2, overflow: TextOverflow.ellipsis, style: estiloSecundario),
              ]),
            ),
            if (c != null)
              IconButton(
                tooltip: 'Quitar la canción',
                icon: const Icon(Icons.close_rounded, size: 20),
                onPressed: () => setState(() {
                  _cancion = null;
                  _tocado = true;
                }),
              )
            else
              const Icon(Icons.chevron_right_rounded, color: C.texto3),
          ]),
        ),
      ),
    );
  }
}

class _CasillaMascota extends StatelessWidget {
  const _CasillaMascota({super.key, required this.nombre, required this.elegida, required this.hijo, required this.alTocar});
  final String nombre;
  final bool elegida;
  final Widget hijo;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        selected: elegida,
        label: nombre,
        excludeSemantics: true,
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: alTocar,
          child: AnimatedContainer(
            duration: Mov.rapido,
            width: 78,
            padding: const EdgeInsets.fromLTRB(6, 8, 6, 6),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              color: elegida ? C.acento.withValues(alpha: 0.16) : C.superficie2,
              border: Border.all(color: elegida ? C.acento : C.borde, width: elegida ? 2 : 1),
            ),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              SizedBox(height: 48, child: Center(child: hijo)),
              const SizedBox(height: 4),
              Text(nombre,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 11.5, fontWeight: elegida ? FontWeight.w900 : FontWeight.w700)),
            ]),
          ),
        ),
      );
}
