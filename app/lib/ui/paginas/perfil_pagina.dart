import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../../nucleo/chat.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/social.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'compartir_perfil.dart';
import 'mensajes_pagina.dart';
import 'perfil_comun.dart';
import 'perfil_editar_pagina.dart';
import 'perfil_listas.dart';
import '../../nucleo/premium.dart';
import '../premium/marcos.dart';
import '../premium/nombre_color.dart';
import '../premium/portada_perfil_ui.dart';
import '../../nucleo/logros_vigia.dart';
import '../logros_vitrina.dart';

/// El perfil de una persona. Sin [usuario] abre el perfil propio (con el
/// botón para editarlo); con un usuario, el de esa persona (con amistad,
/// me gusta, bloquear y su música subida).
class PerfilPagina extends StatefulWidget {
  const PerfilPagina({super.key, this.usuario});

  /// Usuario de Caudal (sin @). `null` = mi propio perfil.
  final String? usuario;

  @override
  State<PerfilPagina> createState() => _PerfilPaginaState();
}

class _PerfilPaginaState extends State<PerfilPagina> {
  Perfil? _perfil;
  Object? _error;
  bool _cargando = true;
  bool _noExiste = false;
  bool _ocupado = false; // amistad en curso
  bool _likeOcupado = false;
  Social? _social;
  Object _marcaFoto = DateTime.now().millisecondsSinceEpoch;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _social = socialDe(context);
      _cargar();
    });
  }

  String get _usuario => widget.usuario ?? Caudal.leer(context).cuenta.usuario;

  Future<void> _cargar({bool silencioso = false}) async {
    final social = _social;
    if (social == null) {
      setState(() {
        _cargando = false;
        _error = const SinConexion();
      });
      return;
    }
    if (!silencioso) setState(() => _cargando = true);
    try {
      final p = await social.verPerfil(_usuario);
      if (!mounted) return;
      setState(() {
        _perfil = p;
        _noExiste = p == null;
        _error = null;
        _cargando = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _cargando = false;
      });
    }
  }

  void _aviso(String t) => Caudal.leer(context).avisar(t);

  // ------------------------------------------------------------ acciones

  Future<void> _amistad() async {
    final p = _perfil;
    final social = _social;
    if (p == null || social == null || _ocupado) return;
    switch (p.relacion) {
      case Relacion.amigo:
        return _escribir();
      case Relacion.enviada:
        final si = await confirmar(context, '¿Cancelar la solicitud?',
            'Se retirará la solicitud que le enviaste a ${p.visible}.', si: 'Cancelar solicitud');
        if (!si) return;
        await _hacer(() async {
          await social.cancelarSolicitud(p.id);
          return Relacion.ninguna;
        }, 'Solicitud cancelada.');
      default:
        // «Agregar» y «Aceptar solicitud»: si la otra persona ya la había enviado, se aceptan solas
        await _hacer(() async {
          final r = await social.enviarSolicitud(p.id);
          _aviso(Social.resultadoSolicitud(r, p.visible));
          return Social.relacionTras(r);
        }, null);
    }
  }

  Future<void> _hacer(Future<String> Function() accion, String? aviso) async {
    setState(() => _ocupado = true);
    try {
      final nueva = await accion();
      if (!mounted) return;
      setState(() => _perfil = _perfil?.conRelacion(nueva));
      if (aviso != null) _aviso(aviso);
      // un perfil privado se abre al hacerse amigos: se vuelve a leer
      if (nueva == Relacion.amigo) _cargar(silencioso: true);
    } catch (e) {
      if (mounted) _aviso(Social.error(e));
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  Future<void> _escribir() async {
    final p = _perfil;
    final s = Caudal.leer(context);
    final sesion = s.cuenta.sesion;
    if (p == null || sesion == null) return;
    try {
      final id = await Chat(sesion).abrir(p.id);
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute<void>(
          builder: (_) => ConversacionPagina(
              chat: ResumenChat(id: id, otro: p.id, usuario: p.usuario, nombre: p.nombre,
                  ultimo: DateTime.now(), fotoUrl: p.fotoUrl))));
    } catch (e) {
      if (mounted) _aviso(Social.error(e));
    }
  }

  Future<void> _like() async {
    final p = _perfil;
    final social = _social;
    if (p == null || social == null || _likeOcupado || !p.sePuedeDarLike) return;
    _likeOcupado = true;
    final di = !p.diLike;
    // se marca al instante; si falla, vuelve a como estaba
    setState(() => _perfil = p.conLike(di, (p.likes + (di ? 1 : -1)).clamp(0, 1 << 30)));
    try {
      final total = di ? await social.darLike(p.id) : await social.quitarLike(p.id);
      if (mounted) setState(() => _perfil = _perfil?.conLike(di, total));
    } catch (e) {
      if (mounted) {
        setState(() => _perfil = p);
        _aviso(Social.error(e));
      }
    } finally {
      _likeOcupado = false;
    }
  }

  Future<void> _bloquear() async {
    final p = _perfil;
    final social = _social;
    if (p == null || social == null) return;
    final si = await confirmar(context, '¿Bloquear a ${p.visible}?',
        'No podrán verse los perfiles, escribirse ni ver la música del otro. Puedes desbloquearlo cuando quieras desde Amigos.',
        si: 'Bloquear');
    if (!si) return;
    try {
      await social.bloquear(p.id);
      if (!mounted) return;
      _aviso('Bloqueaste a ${p.visible}.');
      Navigator.of(context).pop();
    } catch (e) {
      if (mounted) _aviso(Social.error(e));
    }
  }

  Future<void> _quitarAmigo() async {
    final p = _perfil;
    final social = _social;
    if (p == null || social == null) return;
    final si = await confirmar(context, '¿Quitar a ${p.visible} de tus amigos?',
        'Dejarán de ser amigos y no podrán escribirse hasta enviar otra solicitud.', si: 'Quitar');
    if (!si) return;
    await _hacer(() async {
      await social.quitarAmigo(p.id);
      return Relacion.ninguna;
    }, 'Ya no son amigos.');
    if (mounted) _cargar(silencioso: true);
  }

  Future<void> _editar() async {
    final cambio = await Navigator.of(context)
        .push<bool>(MaterialPageRoute(builder: (_) => const PerfilEditarPagina()));
    if (cambio == true && mounted) {
      _marcaFoto = DateTime.now().millisecondsSinceEpoch;
      _cargar(silencioso: true);
    }
  }

  // ------------------------------------------------------------ pantalla

  @override
  Widget build(BuildContext context) {
    final p = _perfil;
    final propio = p?.esMio ?? widget.usuario == null;
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        actions: [
          // «Compartir perfil»: una imagen 9:16 para estados de WhatsApp e historias
          if (p != null && (propio || !p.privado))
            IconButton(
              tooltip: 'Compartir perfil',
              icon: const Icon(Icons.ios_share_rounded),
              onPressed: () => compartirPerfil(context, p),
            ),
          if (p != null && !propio)
            PopupMenuButton<String>(
              tooltip: 'Más opciones',
              color: C.superficie2,
              onSelected: (v) => v == 'bloquear' ? _bloquear() : _quitarAmigo(),
              itemBuilder: (_) => [
                if (p.relacion == Relacion.amigo)
                  const PopupMenuItem(value: 'quitar',
                      child: ListTile(dense: true, leading: Icon(Icons.person_remove_alt_1_rounded), title: Text('Quitar de amigos'))),
                const PopupMenuItem(value: 'bloquear',
                    child: ListTile(dense: true, leading: Icon(Icons.block_rounded), title: Text('Bloquear'))),
              ],
            ),
        ],
      ),
      body: _cargando && p == null
          ? const Center(child: CircularProgressIndicator())
          : _error != null && p == null
              ? SafeArea(child: errorAmable(_error!, _cargar))
              : _noExiste
                  ? SafeArea(
                      child: Vacio(
                        icono: Icons.person_search_rounded,
                        titulo: 'No encontramos este perfil',
                        texto: 'Puede que la persona haya cambiado de usuario o que ya no esté disponible.',
                        alAccion: () => Navigator.of(context).maybePop(),
                        textoAccion: 'Volver',
                        iconoAccion: Icons.arrow_back_rounded,
                      ),
                    )
                  : RefreshIndicator(
                      edgeOffset: 90,
                      onRefresh: () => _cargar(silencioso: true),
                      child: _contenido(p!, propio),
                    ),
    );
  }

  Widget _contenido(Perfil p, bool propio) {
    final color = colorDelPerfil(p.colorPerfil);
    final s = Caudal.of(context);
    final secciones = <Widget>[
      _Cabecera(
        perfil: p,
        color: color,
        marca: _marcaFoto,
        acciones: _acciones(p, propio),
      ),
      // portada de donadores: la ve la propia persona y sus amigos (si no hay nada, no ocupa lugar)
      if (!p.privado || p.esMio)
        PortadaDePerfil(
            usuario: p.usuario, propia: propio, esAmiga: p.relacion == Relacion.amigo, color: color, social: _social),
      if (p.privado) _Privado(perfil: p, color: color),
      if (!p.privado) ...[
        // vitrina de logros: los que la persona eligió lucir (en el propio, con sus logros del dispositivo)
        VitrinaLogros(
          usuario: p.usuario,
          propio: propio,
          sesion: s.cuenta.sesion,
          logros: propio ? VigiaLogros.vigente?.logros : null,
          alCambiarVitrina: propio ? VigiaLogros.vigente?.pronto : null,
        ),
        if (!propio && p.afinidad != null) _Afinidad(valor: p.afinidad!, nombre: p.visible, color: color),
        if (propio && !p.publico)
          _AvisoPropio(
            icono: Icons.lock_outline_rounded,
            texto: 'Tu perfil es privado: solo lo ven tus amigos. Puedes hacerlo público desde «Editar perfil».',
          ),
        if (p.cancionFav != null) _CancionFavorita(cancion: p.cancionFav!, color: color),
        if (p.artistaFav.isNotEmpty) _ArtistaFavorito(nombre: p.artistaFav, color: color),
        if (p.insignias.isNotEmpty)
          _Seccion(titulo: 'Insignias', hijo: Padding(
            padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
            child: Wrap(spacing: 8, runSpacing: 8, children: [for (final i in p.insignias) ChipInsignia(insignia: i)]),
          )),
        if (p.topArtistas.isNotEmpty || p.topCanciones.isNotEmpty) _TopDelMes(perfil: p, propio: propio),
        if (propio && !p.mostrarTop)
          _AvisoPropio(
            icono: Icons.visibility_off_outlined,
            texto: 'Tus estadísticas están ocultas para los demás. Solo tú ves esta parte.',
          ),
        SeccionListasPerfil(usuario: p.usuario, propio: propio, social: _social),
        _Seccion(
          titulo: p.esMio ? 'Mi música subida' : 'Su música subida',
          detalle: p.numSubidas > 0 ? '${p.numSubidas}' : null,
          hijo: p.subidas.isEmpty
              ? Padding(
                  padding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 6),
                  child: Text(
                    propio
                        ? 'Aún no subiste canciones. Con «Subir música» tu música sonará para toda la comunidad.'
                        : 'Todavía no subió canciones.',
                    style: estiloSecundario,
                  ),
                )
              : Column(children: [
                  for (final x in p.subidas)
                    ListenableBuilder(
                      listenable: s.reproductor,
                      builder: (context, _) => FilaSubida(
                        subida: x,
                        mostrarAutor: false,
                        sonando: suenaSubida(s, x),
                        alReproducir: () {
                          final cola = propio ? p.subidas : p.subidas.where((e) => e.publicada).toList();
                          reproducirSubida(context, _social, cola, cola.indexWhere((e) => e.id == x.id));
                        },
                        alReportar: propio ? null : () => reportarSubidaDialogo(context, _social, x),
                        alBorrar: propio
                            ? () async {
                                if (await borrarSubidaDialogo(context, _social, x)) _cargar(silencioso: true);
                              }
                            : null,
                      ),
                    ),
                ]),
        ),
      ],
      const SizedBox(height: 120),
    ];
    return ListView(
      padding: EdgeInsets.zero,
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        for (final (i, w) in secciones.indexed) Entrada(indice: i, child: w),
      ],
    );
  }

  Widget _acciones(Perfil p, bool propio) {
    if (propio) {
      return Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        FilledButton.icon(
          onPressed: _editar,
          icon: const Icon(Icons.edit_rounded, size: 18),
          label: const Text('Editar perfil'),
          style: FilledButton.styleFrom(
              backgroundColor: C.acento, foregroundColor: C.acentoTexto, shape: const StadiumBorder(),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              textStyle: const TextStyle(fontWeight: FontWeight.w800)),
        ),
      ]);
    }
    return Wrap(
      alignment: WrapAlignment.center,
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 8,
      runSpacing: 8,
      children: [
        BotonAmistad(relacion: p.relacion, ocupado: _ocupado, alPulsar: _amistad),
        if (p.sePuedeDarLike) BotonLike(di: p.diLike, total: p.likes, alPulsar: _like),
      ],
    );
  }
}

// ============================================================ piezas

class _Cabecera extends StatelessWidget {
  const _Cabecera({required this.perfil, required this.color, required this.acciones, this.marca});
  final Perfil perfil;
  final Color color;
  final Widget acciones;
  final Object? marca;

  @override
  Widget build(BuildContext context) {
    final p = perfil;
    final arriba = MediaQuery.paddingOf(context).top;
    final alto = 170 + arriba;
    final desde = p.creado == null ? '' : 'En Caudal desde ${_mes(p.creado!)}';
    return Column(children: [
      // imagen de fondo a todo el ancho; el avatar se solapa con su borde
      Stack(clipBehavior: Clip.none, alignment: Alignment.bottomCenter, children: [
        FondoBanner(color: color, bannerUrl: p.bannerUrl, marca: marca, alto: alto),
        Positioned(
          bottom: -52,
          child: Hero(
            tag: 'avatar_${p.id}',
            child: ListenableBuilder(
              listenable: Premium.i,
              builder: (context, _) {
                // lo mío sale del teléfono (se ve al instante al personalizar); lo de otros, del servidor
                final marco = p.esMio ? Premium.i.marcoEfectivo : p.marco;
                return Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: C.fondo,
                    // con marco de donador el aro lo pone el marco
                    border: AvatarMarco.tiene(marco) ? null : Border.all(color: color.withValues(alpha: 0.95), width: 2.5),
                    boxShadow: [BoxShadow(color: color.withValues(alpha: 0.4), blurRadius: 26, spreadRadius: 1)],
                  ),
                  child: AvatarPerfil(
                      nombre: p.visible, fotoUrl: p.fotoUrl, color: color, radio: 54, marca: marca,
                      marco: marco, animar: true, userId: p.id),
                );
              },
            ),
          ),
        ),
      ]),
      // panel de cristal con los datos
      Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, 62, Esp.lado, 0),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(26),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(Esp.xl, Esp.xl, Esp.xl, Esp.l),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(26),
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [color.withValues(alpha: 0.2), C.superficie.withValues(alpha: 0.85)],
                ),
                border: Border.all(color: color.withValues(alpha: 0.28)),
              ),
              child: Column(children: [
                ListenableBuilder(
                  listenable: Premium.i,
                  builder: (context, _) => NombreConColor(
                    p.visible,
                    usuario: p.usuario,
                    esMio: p.esMio,
                    efecto: p.esMio ? Premium.i.efectoNombreEfectivo : p.efectoNombre,
                    estilo: estiloTituloPagina.copyWith(fontSize: 26),
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    animar: true,
                  ),
                ),
                const SizedBox(height: 2),
                Text('@${p.usuario}', style: estiloSecundario),
                if (p.titulos.isNotEmpty || p.fundador || p.esArtista) ...[
                  const SizedBox(height: 10),
                  DistincionesPerfil(titulos: p.titulos, fundador: p.fundador, numero: p.numero, artista: p.esArtista),
                ],
                if (p.frase.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text('“${p.frase}”',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 15, fontStyle: FontStyle.italic, color: Color.lerp(color, Colors.white, 0.7), height: 1.3)),
                ],
                if (p.bio.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(p.bio, textAlign: TextAlign.center, style: const TextStyle(fontSize: 14.5, color: C.texto, height: 1.4)),
                ],
                if (p.generos.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Wrap(alignment: WrapAlignment.center, spacing: 6, runSpacing: 6, children: [
                    for (final g in p.generos)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
                        decoration: BoxDecoration(
                          color: color.withValues(alpha: 0.18),
                          borderRadius: BorderRadius.circular(999),
                          border: Border.all(color: color.withValues(alpha: 0.35)),
                        ),
                        child: Text(g, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
                      ),
                  ]),
                ],
                if (!p.privado) ...[
                  const SizedBox(height: 16),
                  Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                    _Dato(valor: '${p.likes}', etiqueta: 'me gusta'),
                    _Separador(),
                    _Dato(valor: '${p.numSubidas}', etiqueta: p.numSubidas == 1 ? 'canción' : 'canciones'),
                    if (p.insignias.isNotEmpty) ...[
                      _Separador(),
                      _Dato(valor: '${p.insignias.length}', etiqueta: p.insignias.length == 1 ? 'insignia' : 'insignias'),
                    ],
                  ]),
                ],
                if (desde.isNotEmpty) ...[const SizedBox(height: 8), Text(desde, style: estiloDetalle)],
                const SizedBox(height: 16),
                acciones,
              ]),
            ),
          ),
        ),
      ),
    ]);
  }

  static String _mes(DateTime t) {
    const m = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
      'octubre', 'noviembre', 'diciembre'];
    return '${m[t.month - 1]} de ${t.year}';
  }
}

class _Dato extends StatelessWidget {
  const _Dato({required this.valor, required this.etiqueta});
  final String valor;
  final String etiqueta;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 18),
        child: Column(children: [
          Text(valor, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          Text(etiqueta, style: estiloDetalle),
        ]),
      );
}

class _Separador extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(width: 1, height: 28, color: C.borde);
}

class _Seccion extends StatelessWidget {
  const _Seccion({required this.titulo, required this.hijo, this.detalle});
  final String titulo;
  final String? detalle;
  final Widget hijo;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: Esp.entreSecciones - 4),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, 10),
            child: Row(children: [
              Text(titulo, style: estiloTituloSeccion),
              if (detalle != null) ...[
                const SizedBox(width: 8),
                Text(detalle!, style: estiloSecundario),
              ],
            ]),
          ),
          hijo,
        ]),
      );
}

class _AvisoPropio extends StatelessWidget {
  const _AvisoPropio({required this.icono, required this.texto});
  final IconData icono;
  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, 0),
        child: Container(
          padding: const EdgeInsets.all(Esp.m),
          decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(14), border: Border.all(color: C.borde)),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(icono, size: 19, color: C.texto2),
            const SizedBox(width: 10),
            Expanded(child: Text(texto, style: estiloSecundario)),
          ]),
        ),
      );
}

class _Privado extends StatelessWidget {
  const _Privado({required this.perfil, required this.color});
  final Perfil perfil;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final amistad = perfil.relacion == Relacion.enviada
        ? 'Ya le enviaste una solicitud. Cuando la acepte, podrás ver su perfil completo.'
        : perfil.relacion == Relacion.recibida
            ? 'Te envió una solicitud de amistad. Acéptala para ver su perfil completo.'
            : 'Solo sus amigos pueden ver su música, sus insignias y sus gustos. Envíale una solicitud para conocerle mejor.';
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.l, Esp.lado, 0),
      child: Container(
        padding: const EdgeInsets.all(Esp.xl),
        decoration: BoxDecoration(
          color: C.superficie,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: color.withValues(alpha: 0.25)),
        ),
        child: Column(children: [
          Icon(Icons.lock_outline_rounded, size: 34, color: color),
          const SizedBox(height: 10),
          const Text('Este perfil es privado', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          Text(amistad, textAlign: TextAlign.center, style: estiloSecundario),
        ]),
      ),
    );
  }
}

class _Afinidad extends StatelessWidget {
  const _Afinidad({required this.valor, required this.nombre, required this.color});
  final int valor;
  final String nombre;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final v = valor.clamp(0, 100);
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, 0),
      child: Container(
        padding: const EdgeInsets.all(Esp.l),
        decoration: BoxDecoration(
          color: C.superficie,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Row(children: [
          SizedBox(
            width: 58,
            height: 58,
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: v / 100),
              duration: const Duration(milliseconds: 900),
              curve: Mov.curva,
              builder: (_, t, _) => Stack(alignment: Alignment.center, children: [
                CircularProgressIndicator(value: t, strokeWidth: 5, color: color, backgroundColor: C.superficie3),
                Text('$v%', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900)),
              ]),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Coinciden en un $v %', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              const SizedBox(height: 2),
              Text('Tus gustos musicales y los de $nombre se parecen ${_frase(v)}.', style: estiloSecundario),
            ]),
          ),
        ]),
      ),
    );
  }

  static String _frase(int v) => v >= 75 ? 'muchísimo' : v >= 50 ? 'bastante' : v >= 25 ? 'un poco' : 'poco, ¡buena ocasión para descubrir algo nuevo!';
}

class _CancionFavorita extends StatelessWidget {
  const _CancionFavorita({required this.cancion, required this.color});
  final CancionFav cancion;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    return _Seccion(
      titulo: 'Su canción favorita',
      hijo: Padding(
        padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
        child: Pulsable(
          child: InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: cancion.videoId.isEmpty ? null : () => s.reproducirPista(context, cancion.comoPista()),
            child: Container(
              padding: const EdgeInsets.all(Esp.m),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                gradient: LinearGradient(colors: [color.withValues(alpha: 0.28), C.superficie]),
                border: Border.all(color: color.withValues(alpha: 0.3)),
              ),
              child: Row(children: [
                Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: [BoxShadow(color: color.withValues(alpha: 0.4), blurRadius: 22)],
                  ),
                  child: Portada(url: cancion.miniatura, lado: 92, radio: 14),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(cancion.titulo, maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w800, height: 1.2)),
                    const SizedBox(height: 3),
                    Text(cancion.artista, maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                  ]),
                ),
                if (cancion.videoId.isNotEmpty) Icon(Icons.play_circle_fill_rounded, size: 40, color: color),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

class _ArtistaFavorito extends StatelessWidget {
  const _ArtistaFavorito({required this.nombre, required this.color});
  final String nombre;
  final Color color;

  @override
  Widget build(BuildContext context) => _Seccion(
        titulo: 'Su artista favorito',
        hijo: Padding(
          padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
          child: Row(children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(shape: BoxShape.circle, color: color.withValues(alpha: 0.2)),
              child: Icon(Icons.mic_external_on_rounded, color: color, size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(child: Text(nombre, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800))),
          ]),
        ),
      );
}

class _TopDelMes extends StatelessWidget {
  const _TopDelMes({required this.perfil, required this.propio});
  final Perfil perfil;
  final bool propio;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    return _Seccion(
      titulo: 'Lo que más escucha este mes',
      hijo: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (perfil.topArtistas.isNotEmpty)
          SizedBox(
            height: 112,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
              itemCount: perfil.topArtistas.length,
              separatorBuilder: (_, _) => const SizedBox(width: 14),
              itemBuilder: (_, i) {
                final a = perfil.topArtistas[i];
                return SizedBox(
                  width: 78,
                  child: Column(children: [
                    Stack(alignment: Alignment.bottomRight, children: [
                      Portada(url: a.portada, lado: 70, circulo: true, icono: Icons.person_rounded),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                        decoration: BoxDecoration(color: C.acento, borderRadius: BorderRadius.circular(999)),
                        child: Text('${i + 1}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: C.acentoTexto)),
                      ),
                    ]),
                    const SizedBox(height: 6),
                    Text(a.nombre, maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, height: 1.15)),
                  ]),
                );
              },
            ),
          ),
        for (final (i, c) in perfil.topCanciones.take(5).indexed)
          if ('${c['titulo'] ?? ''}'.isNotEmpty)
            FilaPista(
              pista: Chat.pistaJugable(c),
              numero: i + 1,
              alPulsar: () => s.reproducirPista(context, Chat.pistaJugable(c)),
            ),
      ]),
    );
  }
}
