import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/chat.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/social.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'mensajes_pagina.dart';
import 'perfil_comun.dart';

/// Lo que saben las pantallas de amigos: amigos, solicitudes recibidas,
/// enviadas y bloqueados. Se comparte entre las pestañas de Mensajes y
/// [AmigosPagina] para que el contador y las listas siempre coincidan.
class ControladorAmigos extends ChangeNotifier {
  ControladorAmigos(this.social);
  final Social? social;

  List<Contacto>? amigos;
  List<Contacto> solicitudes = const [];
  List<Contacto> enviadas = const [];
  List<Contacto> bloqueados = const [];
  Object? error;
  bool cargando = false;

  /// Solicitudes nuevas (para la insignia).
  int get nuevas => solicitudes.length;

  Future<void> cargar() async {
    final s = social;
    if (s == null) {
      error = const SinConexion();
      notifyListeners();
      return;
    }
    cargando = true;
    try {
      final r = await Future.wait([s.amigos(), s.solicitudes(), s.enviadas(), s.bloqueados()]);
      amigos = r[0];
      solicitudes = r[1];
      enviadas = r[2];
      bloqueados = r[3];
      error = null;
    } catch (e) {
      if (amigos == null) error = e;
    }
    cargando = false;
    notifyListeners();
  }

  /// Solo actualiza lo que se ve al instante (la acción real ya se hizo).
  void quitarDe(String id) {
    amigos = amigos?.where((x) => x.id != id).toList();
    solicitudes = solicitudes.where((x) => x.id != id).toList();
    enviadas = enviadas.where((x) => x.id != id).toList();
    notifyListeners();
  }
}

/// Amigos y solicitudes en una sola pantalla (dos pestañas). Dentro de
/// Mensajes las mismas vistas aparecen junto a «Chats».
class AmigosPagina extends StatefulWidget {
  const AmigosPagina({super.key, this.pestana = 0});

  /// 0 = Solicitudes, 1 = Amigos.
  final int pestana;

  @override
  State<AmigosPagina> createState() => _AmigosPaginaState();
}

class _AmigosPaginaState extends State<AmigosPagina> {
  ControladorAmigos? _c;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      setState(() => _c = ControladorAmigos(socialDe(context))..cargar());
    });
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    return DefaultTabController(
      length: 2,
      initialIndex: widget.pestana.clamp(0, 1),
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Amigos', style: estiloTituloBarra),
          bottom: TabBar(
            indicatorColor: C.acento,
            labelColor: C.texto,
            tabs: [
              Tab(child: c == null ? const Text('Solicitudes') : EtiquetaSolicitudes(c)),
              const Tab(text: 'Amigos'),
            ],
          ),
        ),
        body: c == null
            ? const Center(child: CircularProgressIndicator())
            : TabBarView(children: [SolicitudesVista(controlador: c), AmigosVista(controlador: c)]),
      ),
    );
  }
}

/// «Solicitudes» con el número de nuevas al lado.
class EtiquetaSolicitudes extends StatelessWidget {
  const EtiquetaSolicitudes(this.controlador, {super.key});
  final ControladorAmigos controlador;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: controlador,
        builder: (_, _) => Row(mainAxisSize: MainAxisSize.min, children: [
          const Text('Solicitudes'),
          if (controlador.nuevas > 0) ...[
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
              decoration: BoxDecoration(color: C.acento, borderRadius: BorderRadius.circular(10)),
              child: Text('${controlador.nuevas}',
                  semanticsLabel: '${controlador.nuevas} solicitudes nuevas',
                  style: TextStyle(color: C.acentoTexto, fontSize: 11, fontWeight: FontWeight.w900)),
            ),
          ],
        ]),
      );
}

String _desde(DateTime? t) {
  if (t == null) return '';
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 1) return 'hace un momento';
  if (d.inHours < 1) return 'hace ${d.inMinutes} min';
  if (d.inDays < 1) return 'hace ${d.inHours} h';
  if (d.inDays < 30) return 'hace ${d.inDays} ${d.inDays == 1 ? 'día' : 'días'}';
  return '${t.day}/${t.month}/${t.year}';
}

// ============================================================ solicitudes recibidas

class SolicitudesVista extends StatefulWidget {
  const SolicitudesVista({super.key, required this.controlador});
  final ControladorAmigos controlador;

  @override
  State<SolicitudesVista> createState() => _SolicitudesVistaState();
}

class _SolicitudesVistaState extends State<SolicitudesVista> {
  final Set<String> _ocupados = {};

  Future<void> _responder(Contacto c, bool acepta) async {
    final social = widget.controlador.social;
    final id = c.solicitudId;
    final s = Caudal.leer(context);
    if (social == null || id == null || _ocupados.contains(c.id)) return;
    setState(() => _ocupados.add(c.id));
    try {
      await social.responderSolicitud(id, acepta);
      s.avisar(acepta ? '¡Ahora tú y ${c.visible} son amigos!' : 'Rechazaste la solicitud de ${c.visible}.');
      await widget.controlador.cargar();
    } catch (e) {
      s.avisar(Social.error(e));
    } finally {
      if (mounted) setState(() => _ocupados.remove(c.id));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ctl = widget.controlador;
    return ListenableBuilder(
      listenable: ctl,
      builder: (context, _) {
        if (ctl.error != null && ctl.amigos == null) return errorAmable(ctl.error!, ctl.cargar);
        if (ctl.amigos == null) return const Center(child: CircularProgressIndicator());
        if (ctl.solicitudes.isEmpty) {
          return RefreshIndicator(
            onRefresh: ctl.cargar,
            child: ListView(children: const [
              SizedBox(height: 40),
              Vacio(
                icono: Icons.mark_email_unread_outlined,
                titulo: 'No tienes solicitudes nuevas',
                texto: 'Cuando alguien quiera ser tu amigo, su solicitud llegará aquí. '
                    'Nadie puede escribirte sin que tú lo aceptes.',
              ),
            ]),
          );
        }
        return RefreshIndicator(
          onRefresh: ctl.cargar,
          child: ListView.builder(
            padding: const EdgeInsets.only(top: 6, bottom: 120),
            itemCount: ctl.solicitudes.length,
            itemBuilder: (_, i) {
              final c = ctl.solicitudes[i];
              final ocupado = _ocupados.contains(c.id);
              return Entrada(
                indice: i,
                child: ListTile(
                  contentPadding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 4),
                  leading: AvatarPerfil(nombre: c.visible, fotoUrl: c.fotoUrl, radio: 25),
                  title: Text(c.visible, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800)),
                  subtitle: Text('@${c.usuario} · ${_desde(c.fecha)}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                  onTap: () => abrirPerfil(context, c.usuario),
                  trailing: ocupado
                      ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2))
                      : Row(mainAxisSize: MainAxisSize.min, children: [
                          IconButton(
                            tooltip: 'Rechazar la solicitud de ${c.visible}',
                            style: IconButton.styleFrom(backgroundColor: C.superficie3),
                            icon: const Icon(Icons.close_rounded),
                            onPressed: () => _responder(c, false),
                          ),
                          const SizedBox(width: 6),
                          IconButton.filled(
                            tooltip: 'Aceptar la solicitud de ${c.visible}',
                            style: IconButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto),
                            icon: const Icon(Icons.check_rounded),
                            onPressed: () => _responder(c, true),
                          ),
                        ]),
                ),
              );
            },
          ),
        );
      },
    );
  }
}

// ============================================================ amigos

class AmigosVista extends StatefulWidget {
  const AmigosVista({super.key, required this.controlador});
  final ControladorAmigos controlador;

  @override
  State<AmigosVista> createState() => _AmigosVistaState();
}

class _AmigosVistaState extends State<AmigosVista> {
  final _campo = TextEditingController();
  Timer? _espera;
  Contacto? _hallado;
  String _estado = 'Escribe el usuario exacto de la persona (el que usa para entrar).';
  bool _buscando = false;
  bool _enviando = false;

  @override
  void dispose() {
    _espera?.cancel();
    _campo.dispose();
    super.dispose();
  }

  String get _escrito => _campo.text.trim().replaceFirst('@', '').toLowerCase();

  void _alEscribir(String _) {
    _espera?.cancel();
    final u = _escrito;
    setState(() {
      _hallado = null;
      _buscando = u.length >= 3;
      _estado = u.isEmpty
          ? 'Escribe el usuario exacto de la persona (el que usa para entrar).'
          : u.length < 3 ? 'Sigue escribiendo…' : 'Buscando…';
    });
    if (u.length < 3) return;
    _espera = Timer(const Duration(milliseconds: 450), () async {
      try {
        final r = await widget.controlador.social?.buscarPersona(u);
        if (!mounted || _escrito != u) return;
        setState(() {
          _buscando = false;
          _hallado = r;
          _estado = r == null ? 'No hay nadie con el usuario «$u». Revisa que esté bien escrito.' : '';
        });
      } catch (e) {
        if (mounted) {
          setState(() {
            _buscando = false;
            _estado = Social.error(e);
          });
        }
      }
    });
  }

  Future<void> _accion(Contacto c) async {
    final social = widget.controlador.social;
    final s = Caudal.leer(context);
    if (social == null || _enviando) return;
    switch (c.relacion) {
      case Relacion.amigo:
        return _escribir(c);
      case Relacion.enviada:
        try {
          await social.cancelarSolicitud(c.id);
          s.avisar('Solicitud cancelada.');
          setState(() => _hallado = _hallado?.conRelacion(Relacion.ninguna));
          widget.controlador.cargar();
        } catch (e) {
          s.avisar(Social.error(e));
        }
      case Relacion.yo:
      case Relacion.bloqueado:
        return;
      default:
        setState(() => _enviando = true);
        try {
          final r = await social.enviarSolicitud(c.id);
          s.avisar(Social.resultadoSolicitud(r, c.visible));
          if (mounted) setState(() => _hallado = _hallado?.conRelacion(Social.relacionTras(r)));
          widget.controlador.cargar();
        } catch (e) {
          s.avisar(Social.error(e));
        } finally {
          if (mounted) setState(() => _enviando = false);
        }
    }
  }

  Future<void> _escribir(Contacto c) async {
    final sesion = Caudal.leer(context).cuenta.sesion;
    if (sesion == null) return;
    try {
      final id = await Chat(sesion).abrir(c.id);
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute<void>(
          builder: (_) => ConversacionPagina(
              chat: ResumenChat(id: id, otro: c.id, usuario: c.usuario, nombre: c.nombre,
                  ultimo: DateTime.now(), fotoUrl: c.fotoUrl))));
    } catch (e) {
      if (mounted) Caudal.leer(context).avisar(Social.error(e));
    }
  }

  Future<void> _quitar(Contacto c) async {
    final social = widget.controlador.social;
    final s = Caudal.leer(context);
    final si = await confirmar(context, '¿Quitar a ${c.visible} de tus amigos?',
        'Dejarán de ser amigos y no podrán escribirse hasta enviar otra solicitud.', si: 'Quitar');
    if (!si || social == null) return;
    try {
      await social.quitarAmigo(c.id);
      widget.controlador.quitarDe(c.id);
      s.avisar('Ya no son amigos.');
    } catch (e) {
      s.avisar(Social.error(e));
    }
  }

  Future<void> _bloquear(Contacto c) async {
    final social = widget.controlador.social;
    final s = Caudal.leer(context);
    final si = await confirmar(context, '¿Bloquear a ${c.visible}?',
        'No podrán verse los perfiles, escribirse ni ver la música del otro. Podrás desbloquearlo desde esta misma pantalla.',
        si: 'Bloquear');
    if (!si || social == null) return;
    try {
      await social.bloquear(c.id);
      s.avisar('Bloqueaste a ${c.visible}.');
      widget.controlador.cargar();
    } catch (e) {
      s.avisar(Social.error(e));
    }
  }

  Future<void> _desbloquear(Contacto c) async {
    final social = widget.controlador.social;
    final s = Caudal.leer(context);
    if (social == null) return;
    try {
      await social.desbloquear(c.id);
      s.avisar('Desbloqueaste a ${c.visible}.');
      widget.controlador.cargar();
    } catch (e) {
      s.avisar(Social.error(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ctl = widget.controlador;
    return ListenableBuilder(
      listenable: ctl,
      builder: (context, _) {
        if (ctl.error != null && ctl.amigos == null) return errorAmable(ctl.error!, ctl.cargar);
        final amigos = ctl.amigos;
        if (amigos == null) return const Center(child: CircularProgressIndicator());
        return RefreshIndicator(
          onRefresh: ctl.cargar,
          child: ListView(
            padding: const EdgeInsets.only(bottom: 120),
            children: [
              _buscador(),
              if (ctl.enviadas.isNotEmpty) ...[
                _titulo('Solicitudes enviadas'),
                for (final c in ctl.enviadas)
                  ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: Esp.lado),
                    leading: AvatarPerfil(nombre: c.visible, fotoUrl: c.fotoUrl, radio: 22),
                    title: Text(c.visible, maxLines: 1, overflow: TextOverflow.ellipsis),
                    subtitle: Text('@${c.usuario} · esperando respuesta', style: estiloSecundario),
                    onTap: () => abrirPerfil(context, c.usuario),
                    trailing: TextButton(
                      onPressed: () async {
                        final social = ctl.social;
                        if (social == null) return;
                        try {
                          await social.cancelarSolicitud(c.id);
                          ctl.quitarDe(c.id);
                        } catch (e) {
                          if (context.mounted) Caudal.leer(context).avisar(Social.error(e));
                        }
                      },
                      child: const Text('Cancelar'),
                    ),
                  ),
              ],
              _titulo('Tus amigos', detalle: amigos.isEmpty ? null : '${amigos.length}'),
              if (amigos.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: Esp.xl, vertical: Esp.m),
                  child: Text('Todavía no tienes amigos en Caudal. Busca a alguien por su usuario arriba, '
                      'o mira el directorio de «Perfiles de Caudal».',
                      style: estiloSecundario),
                ),
              for (final (i, c) in amigos.indexed)
                Entrada(
                  indice: i,
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 2),
                    leading: AvatarPerfil(nombre: c.visible, fotoUrl: c.fotoUrl, radio: 24),
                    title: Text(c.visible, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: Text('@${c.usuario}', style: estiloSecundario),
                    onTap: () => abrirPerfil(context, c.usuario),
                    trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                      IconButton(
                        tooltip: 'Escribir a ${c.visible}',
                        icon: Icon(Icons.chat_bubble_rounded, color: C.acento),
                        onPressed: () => _escribir(c),
                      ),
                      PopupMenuButton<String>(
                        tooltip: 'Más opciones',
                        color: C.superficie2,
                        onSelected: (v) => v == 'quitar' ? _quitar(c) : _bloquear(c),
                        itemBuilder: (_) => const [
                          PopupMenuItem(value: 'quitar',
                              child: ListTile(dense: true, leading: Icon(Icons.person_remove_alt_1_rounded), title: Text('Quitar de amigos'))),
                          PopupMenuItem(value: 'bloquear',
                              child: ListTile(dense: true, leading: Icon(Icons.block_rounded), title: Text('Bloquear'))),
                        ],
                      ),
                    ]),
                  ),
                ),
              if (ctl.bloqueados.isNotEmpty)
                Theme(
                  data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                  child: ExpansionTile(
                    tilePadding: const EdgeInsets.symmetric(horizontal: Esp.lado),
                    title: Text('Personas bloqueadas (${ctl.bloqueados.length})', style: estiloTituloSeccion.copyWith(fontSize: 16)),
                    children: [
                      for (final c in ctl.bloqueados)
                        ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: Esp.lado),
                          leading: AvatarPerfil(nombre: c.visible, fotoUrl: c.fotoUrl, radio: 20),
                          title: Text(c.visible),
                          subtitle: Text('@${c.usuario}', style: estiloSecundario),
                          trailing: OutlinedButton(onPressed: () => _desbloquear(c), child: const Text('Desbloquear')),
                        ),
                    ],
                  ),
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _titulo(String t, {String? detalle}) => Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.l, Esp.lado, 6),
        child: Row(children: [
          Text(t, style: estiloTituloSeccion.copyWith(fontSize: 18)),
          if (detalle != null) ...[const SizedBox(width: 8), Text(detalle, style: estiloSecundario)],
        ]),
      );

  Widget _buscador() {
    final h = _hallado;
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, 0),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        TextField(
          controller: _campo,
          autocorrect: false,
          enableSuggestions: false,
          onChanged: _alEscribir,
          decoration: InputDecoration(
            prefixText: '@',
            hintText: 'Buscar por usuario',
            prefixIcon: const Icon(Icons.person_search_rounded),
            filled: true,
            fillColor: C.superficie2,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide.none),
            suffixIcon: _buscando
                ? const Padding(padding: EdgeInsets.all(14),
                    child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)))
                : null,
          ),
        ),
        const SizedBox(height: 8),
        AnimatedSwitcher(
          duration: Mov.normal,
          child: h != null
              ? Container(
                  key: ValueKey(h.id),
                  padding: const EdgeInsets.all(Esp.m),
                  decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(16), border: Border.all(color: C.borde)),
                  child: Row(children: [
                    InkWell(
                      onTap: () => abrirPerfil(context, h.usuario),
                      child: AvatarPerfil(nombre: h.visible, fotoUrl: h.fotoUrl, radio: 24),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(h.visible, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800)),
                        Text('@${h.usuario}', style: estiloSecundario),
                      ]),
                    ),
                    if (h.relacion == Relacion.yo)
                      const Text('Eres tú', style: estiloSecundario)
                    else
                      BotonAmistad(relacion: h.relacion, ocupado: _enviando, compacto: true, alPulsar: () => _accion(h)),
                  ]),
                )
              : Padding(key: const ValueKey('estado'), padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                  child: Text(_estado, style: estiloSecundario)),
        ),
      ]),
    );
  }
}
