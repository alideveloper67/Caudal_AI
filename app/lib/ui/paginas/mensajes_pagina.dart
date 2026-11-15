import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/chat.dart';
import '../../nucleo/coleccion.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/social.dart';
import '../comunes.dart';
import '../emojis.dart';
import '../servicios.dart';
import '../tema.dart';
import 'amigos_pagina.dart';
import 'perfil_comun.dart';

/// El chat de la cuenta (null sin sesión: se entró sin internet).
Chat? chatDe(BuildContext context) {
  final s = Caudal.leer(context).cuenta.sesion;
  return s == null || s.acceso.isEmpty ? null : Chat(s);
}

String _hora(DateTime t) {
  final ahora = DateTime.now();
  final hh = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  if (ahora.difference(t).inHours < 20 && ahora.day == t.day) return hh;
  if (ahora.difference(t).inDays < 7) {
    return const ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'][t.weekday - 1];
  }
  return '${t.day}/${t.month}';
}

String _error(Object e) =>
    e is ErrorNube ? e.mensaje : 'No se pudo conectar. Revisa tu internet y vuelve a probar.';

// ============================================================ lista

class MensajesPagina extends StatefulWidget {
  const MensajesPagina({super.key});

  @override
  State<MensajesPagina> createState() => _MensajesPaginaState();
}

class _MensajesPaginaState extends State<MensajesPagina> {
  List<ResumenChat>? _chats;
  String? _error_;
  Timer? _reloj;
  ControladorAmigos? _amigos;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      setState(() => _amigos = ControladorAmigos(socialDe(context))..cargar());
      _cargar();
    });
    _reloj = Timer.periodic(const Duration(seconds: 8), (_) {
      _cargar();
      _amigos?.cargar();
    });
  }

  @override
  void dispose() {
    _reloj?.cancel();
    _amigos?.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    final chat = chatDe(context);
    if (chat == null) {
      if (mounted) setState(() => _error_ = 'Los mensajes necesitan internet. Vuelve a abrir Caudal con conexión.');
      return;
    }
    try {
      final l = await chat.misChats();
      if (mounted) setState(() {
        _chats = l;
        _error_ = null;
      });
    } catch (e) {
      if (mounted && _chats == null) setState(() => _error_ = _error(e));
    }
  }

  Future<void> _nuevo() async {
    final r = await nuevoChat(context);
    if (r != null && mounted) {
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ConversacionPagina(chat: r)));
      _cargar();
    }
  }

  @override
  Widget build(BuildContext context) {
    final amigos = _amigos;
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Mensajes', style: estiloTituloBarra),
          actions: [
            IconButton(tooltip: 'Nuevo mensaje', icon: const Icon(Icons.edit_square), onPressed: _nuevo),
          ],
          bottom: TabBar(
            indicatorColor: C.acento,
            labelColor: C.texto,
            tabs: [
              const Tab(text: 'Chats'),
              Tab(child: amigos == null ? const Text('Solicitudes') : EtiquetaSolicitudes(amigos)),
              const Tab(text: 'Amigos'),
            ],
          ),
        ),
        body: amigos == null
            ? _listaChats()
            : TabBarView(children: [
                _listaChats(),
                SolicitudesVista(controlador: amigos),
                AmigosVista(controlador: amigos),
              ]),
      ),
    );
  }

  Widget _listaChats() {
    final chats = _chats;
    return _error_ != null && chats == null
        ? Vacio(icono: Icons.wifi_off_rounded, titulo: 'Sin conexión', texto: _error_!, error: true, alAccion: _cargar)
        : chats == null
            ? const Center(child: CircularProgressIndicator())
            : chats.isEmpty
                ? Builder(builder: (ctx) => Vacio(
                    icono: Icons.forum_outlined,
                    titulo: 'Comparte música con tus amigos',
                    texto: 'Primero agrega a alguien por su usuario de Caudal; cuando acepte, podrán escribirse, '
                        'mandarse canciones y crear una mezcla con lo que escuchan los dos.',
                    textoAccion: 'Buscar amigos',
                    iconoAccion: Icons.person_add_alt_1_rounded,
                    alAccion: () => DefaultTabController.of(ctx).animateTo(2),
                  ))
                : RefreshIndicator(
                    onRefresh: _cargar,
                    child: ListView.builder(
                      itemCount: chats.length,
                      itemBuilder: (_, i) {
                        final c = chats[i];
                        return ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 4),
                          leading: AvatarPerfil(nombre: c.visible, fotoUrl: c.fotoUrl, radio: 24),
                          title: Text(c.visible, style: TextStyle(fontWeight: c.sinLeer > 0 ? FontWeight.w900 : FontWeight.w700)),
                          subtitle: Text(c.vistaPrevia, maxLines: 1, overflow: TextOverflow.ellipsis,
                              style: TextStyle(color: c.sinLeer > 0 ? C.texto : C.texto2)),
                          trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                            Text(_hora(c.ultimo), style: estiloDetalle),
                            const SizedBox(height: 4),
                            if (c.sinLeer > 0)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                                decoration: BoxDecoration(color: C.acento, borderRadius: BorderRadius.circular(10)),
                                child: Text('${c.sinLeer}', style: TextStyle(color: C.acentoTexto, fontSize: 11, fontWeight: FontWeight.w900)),
                              ),
                          ]),
                          onTap: () async {
                            await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ConversacionPagina(chat: c)));
                            _cargar();
                          },
                        );
                      },
                    ),
                  );
  }
}

/// Busca a alguien por su usuario (mientras se escribe) y abre el chat.
Future<ResumenChat?> nuevoChat(BuildContext context) async {
  final chat = chatDe(context);
  final s = Caudal.leer(context);
  if (chat == null) {
    s.avisar('Los mensajes necesitan internet.');
    return null;
  }
  return showDialog<ResumenChat>(
    context: context,
    useRootNavigator: true,
    builder: (_) => _DialogoNuevoChat(chat: chat, yo: s.cuenta.usuario),
  );
}

class _DialogoNuevoChat extends StatefulWidget {
  const _DialogoNuevoChat({required this.chat, required this.yo});
  final Chat chat;
  final String yo;

  @override
  State<_DialogoNuevoChat> createState() => _DialogoNuevoChatState();
}

/// «Nuevo mensaje»: solo se puede elegir entre los amigos (con buscador
/// local). Para escribirle a alguien nuevo, primero hay que agregarlo.
class _DialogoNuevoChatState extends State<_DialogoNuevoChat> {
  final _campo = TextEditingController();
  List<Contacto>? _amigos;
  String? _fallo;
  String? _abriendo;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _campo.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    setState(() => _fallo = null);
    try {
      final l = await Social(widget.chat.sesion).amigos();
      if (mounted) setState(() => _amigos = l);
    } catch (e) {
      if (mounted) setState(() => _fallo = _error(e));
    }
  }

  Future<void> _abrir(Contacto p) async {
    if (_abriendo != null) return;
    setState(() => _abriendo = p.id);
    try {
      final id = await widget.chat.abrir(p.id);
      if (!mounted) return;
      Navigator.of(context).pop(ResumenChat(id: id, otro: p.id, usuario: p.usuario, nombre: p.nombre,
          ultimo: DateTime.now(), fotoUrl: p.fotoUrl));
    } catch (e) {
      if (mounted) {
        setState(() {
          _abriendo = null;
          _fallo = _error(e);
        });
      }
    }
  }

  void _agregar() {
    final nav = Navigator.of(context);
    nav.pop();
    nav.push(MaterialPageRoute<void>(builder: (_) => const AmigosPagina(pestana: 1)));
  }

  @override
  Widget build(BuildContext context) {
    final q = _campo.text.trim().toLowerCase();
    final todos = _amigos;
    final lista = todos == null
        ? const <Contacto>[]
        : [for (final c in todos) if (q.isEmpty || c.visible.toLowerCase().contains(q) || c.usuario.contains(q)) c];
    return AlertDialog(
      backgroundColor: C.superficie2,
      title: const Text('Nuevo mensaje'),
      content: SizedBox(
        width: 380,
        height: 380,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (todos != null && todos.length > 5)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: TextField(
                controller: _campo,
                onChanged: (_) => setState(() {}),
                decoration: InputDecoration(
                  hintText: 'Buscar entre tus amigos',
                  prefixIcon: const Icon(Icons.search_rounded),
                  isDense: true,
                  filled: true,
                  fillColor: C.superficie3,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide.none),
                ),
              ),
            ),
          Expanded(
            child: _fallo != null && todos == null
                ? Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Text(_fallo!, textAlign: TextAlign.center, style: estiloSecundario),
                    const SizedBox(height: 10),
                    OutlinedButton(onPressed: _cargar, child: const Text('Reintentar')),
                  ]))
                : todos == null
                    ? const Center(child: CircularProgressIndicator())
                    : todos.isEmpty
                        ? const Center(
                            child: Text('Todavía no tienes amigos en Caudal. Agrega a alguien y, cuando acepte, '
                                'podrán escribirse.',
                                textAlign: TextAlign.center, style: estiloSecundario))
                        : lista.isEmpty
                            ? const Center(child: Text('Ningún amigo coincide.', style: estiloSecundario))
                            : ListView.builder(
                                itemCount: lista.length,
                                itemBuilder: (_, i) {
                                  final c = lista[i];
                                  return ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    leading: AvatarPerfil(nombre: c.visible, fotoUrl: c.fotoUrl, radio: 22),
                                    title: Text(c.visible, maxLines: 1, overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(fontWeight: FontWeight.w700)),
                                    subtitle: Text('@${c.usuario}', style: estiloSecundario),
                                    trailing: _abriendo == c.id
                                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                                        : const Icon(Icons.chevron_right_rounded, color: C.texto3),
                                    onTap: () => _abrir(c),
                                  );
                                },
                              ),
          ),
          if (_fallo != null && todos != null)
            Padding(padding: const EdgeInsets.only(top: 6), child: Text(_fallo!, style: const TextStyle(color: C.error, fontSize: 12.5))),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cerrar')),
        FilledButton.icon(
          onPressed: _agregar,
          icon: const Icon(Icons.person_add_alt_1_rounded, size: 18),
          label: const Text('Agregar un amigo'),
        ),
      ],
    );
  }
}

/// "Enviar en un chat" desde el menú de una canción.
Future<void> enviarPistaAChat(BuildContext context, Json pista) async {
  final chat = chatDe(context);
  final s = Caudal.leer(context);
  if (chat == null) {
    s.avisar('Los mensajes necesitan internet.');
    return;
  }
  List<ResumenChat> chats;
  try {
    chats = await chat.misChats();
  } catch (e) {
    s.avisar(_error(e));
    return;
  }
  if (!context.mounted) return;
  final elegido = await showModalBottomSheet<Object>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    builder: (ctx) => DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.55,
      maxChildSize: 0.9,
      builder: (_, scroll) => ListView(controller: scroll, children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 4, 20, 12),
          child: Text('Enviar a…', style: estiloTituloSeccion),
        ),
        ListTile(
          leading: CircleAvatar(backgroundColor: C.superficie3, child: Icon(Icons.person_add_alt_1_rounded, color: C.acento)),
          title: const Text('Alguien nuevo', style: TextStyle(fontWeight: FontWeight.w700)),
          onTap: () => Navigator.pop(ctx, 'nuevo'),
        ),
        for (final c in chats)
          ListTile(
            leading: AvatarPerfil(nombre: c.visible, fotoUrl: c.fotoUrl, radio: 20),
            title: Text(c.visible),
            subtitle: Text('@${c.usuario}', style: estiloSecundario),
            onTap: () => Navigator.pop(ctx, c),
          ),
      ]),
    ),
  );
  if (!context.mounted || elegido == null) return;
  final destino = elegido is ResumenChat ? elegido : await nuevoChat(context);
  if (destino == null) return;
  try {
    await chat.enviar(destino.id, pista: pista);
    s.avisar('Enviada a ${destino.visible}');
  } catch (e) {
    s.avisar(_error(e));
  }
}

// ============================================================ conversacion

class ConversacionPagina extends StatefulWidget {
  const ConversacionPagina({super.key, required this.chat});
  final ResumenChat chat;

  @override
  State<ConversacionPagina> createState() => _ConversacionPaginaState();
}

/// Un mensaje que ya se ve pero el servidor aún no confirmó.
class _Pendiente {
  _Pendiente(this.clave, this.texto, this.pista);
  final int clave;
  final String texto;
  final Json? pista;
  final DateTime creado = DateTime.now();
  String? fallo; // por qué no se envió (null mientras va en camino)
}

class _ConversacionPaginaState extends State<ConversacionPagina> {
  final _campo = TextEditingController();
  final _scroll = ScrollController();
  List<Mensaje> _mensajes = [];
  final List<_Pendiente> _pendientes = [];
  int _siguiente = 0;
  int _enCamino = 0;
  bool _cargado = false;
  String? _errorCarga;
  Timer? _reloj;
  Chat? _chat;

  @override
  void initState() {
    super.initState();
    _campo.addListener(() => setState(() {}));
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _chat = chatDe(context);
      _cargar();
      _reloj = Timer.periodic(const Duration(seconds: 3), (_) => _nuevos());
    });
  }

  @override
  void dispose() {
    _reloj?.cancel();
    _campo.dispose();
    _scroll.dispose();
    super.dispose();
  }

  /// Junta mensajes sin repetir (el sondeo y la confirmación pueden traer el mismo).
  void _sumar(Iterable<Mensaje> llegan) {
    final ids = {for (final m in _mensajes) m.id};
    final nuevos = llegan.where((m) => ids.add(m.id)).toList();
    if (nuevos.isEmpty) return;
    _mensajes = [..._mensajes, ...nuevos]..sort((a, b) => a.id.compareTo(b.id));
  }

  Future<void> _cargar() async {
    final c = _chat;
    if (c == null) return;
    setState(() => _errorCarga = null);
    try {
      final l = await c.mensajes(widget.chat.id);
      if (!mounted) return;
      setState(() {
        _sumar(l);
        _cargado = true;
      });
      c.marcarLeido(widget.chat.id);
    } catch (e) {
      if (mounted) {
        setState(() {
          _cargado = true;
          _errorCarga = _error(e);
        });
      }
    }
  }

  Future<void> _nuevos() async {
    final c = _chat;
    // mientras un envío va en camino no se pregunta: evita burbujas dobles
    if (c == null || !_cargado || _enCamino > 0) return;
    if (_errorCarga != null) return _cargar();
    try {
      final desde = _mensajes.isEmpty ? 0 : _mensajes.last.id;
      final l = await c.mensajes(widget.chat.id, desde: desde);
      if (!mounted) return;
      final antes = _mensajes.length;
      setState(() => _sumar(l));
      if (_mensajes.length != antes) c.marcarLeido(widget.chat.id);
    } catch (_) {}
  }

  /// Se ve al momento con «Enviando…»; si falla, se toca para reintentar.
  /// El campo nunca se bloquea: se puede seguir escribiendo mientras tanto.
  void _enviar({Json? pista}) {
    final texto = pista == null ? _campo.text.trim() : '';
    if (_chat == null || (texto.isEmpty && pista == null)) return;
    if (pista == null) _campo.clear();
    final p = _Pendiente(++_siguiente, texto, pista);
    setState(() => _pendientes.add(p));
    if (_scroll.hasClients) {
      _scroll.animateTo(0, duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
    }
    _mandar(p);
  }

  Future<void> _mandar(_Pendiente p) async {
    final c = _chat;
    if (c == null) return;
    setState(() => p.fallo = null);
    _enCamino++;
    try {
      final m = await c.enviar(widget.chat.id, texto: p.texto, pista: p.pista);
      if (!mounted) return;
      setState(() {
        _pendientes.remove(p);
        _sumar([m]);
      });
    } catch (e) {
      if (mounted) setState(() => p.fallo = _error(e));
    } finally {
      _enCamino = (_enCamino - 1).clamp(0, 1 << 30);
    }
  }

  void _enviarLoQueSuena() {
    final s = Caudal.leer(context);
    final p = s.reproductor.actual;
    if (p == null) {
      s.avisar('Ahora no suena nada. Pon una canción y vuelve a tocar 🎵');
      return;
    }
    if ('${p['video_id'] ?? ''}'.isEmpty) {
      s.avisar('Esa canción es un archivo del teléfono: solo se pueden enviar canciones de YouTube Music.');
      return;
    }
    _enviar(pista: p);
  }

  Future<void> _mezcla() async {
    final c = _chat;
    final s = Caudal.leer(context);
    if (c == null) return;
    s.avisar('Preparando su mezcla…');
    try {
      final m = await c.mezcla(widget.chat.id);
      final mix = Chat.mixDeMezcla(m, widget.chat.visible, widget.chat.id);
      if (!mounted) return;
      if ((mix['pistas'] as List).isEmpty) {
        s.avisar('Aún no hay suficiente: escuchen un poco más de música los dos y vuelvan a probar.');
        return;
      }
      s.abrirElemento(context, mix);
    } catch (e) {
      s.avisar(_error(e));
    }
  }

  Widget _vacio(String texto, {VoidCallback? reintentar}) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(texto, textAlign: TextAlign.center, style: estiloSecundario),
            if (reintentar != null) ...[
              const SizedBox(height: 12),
              OutlinedButton.icon(onPressed: reintentar, icon: const Icon(Icons.refresh_rounded),
                  label: const Text('Reintentar')),
            ],
          ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final yo = s.cuenta.id;
    final total = _pendientes.length + _mensajes.length;
    Widget lista;
    if (!_cargado) {
      lista = const Center(child: CircularProgressIndicator());
    } else if (total == 0 && _errorCarga != null) {
      lista = _vacio('$_errorCarga\nPuedes escribir igual.', reintentar: _cargar);
    } else if (total == 0) {
      lista = _vacio('Aquí empieza tu conversación con ${widget.chat.visible}.\n'
          'Escríbele algo o mándale lo que estás escuchando 🎵\n\n'
          'Toca «Mezcla» para crear una lista con lo que escuchan los dos.');
    } else {
      lista = ListView.builder(
        controller: _scroll,
        reverse: true,
        padding: const EdgeInsets.symmetric(horizontal: Esp.m, vertical: Esp.m),
        itemCount: total,
        itemBuilder: (_, i) {
          // lo más nuevo abajo: primero los pendientes, luego los confirmados
          if (i < _pendientes.length) {
            final p = _pendientes[_pendientes.length - 1 - i];
            return _Burbuja(
              mensaje: Mensaje(id: -p.clave, autor: yo, texto: p.texto, pista: p.pista, creado: p.creado),
              mio: true,
              estado: p.fallo == null ? 'Enviando…' : '⚠ ${p.fallo} · Toca para reintentar',
              alTocarEstado: p.fallo == null ? null : () => _mandar(p),
            );
          }
          final m = _mensajes[_mensajes.length - 1 - (i - _pendientes.length)];
          return _Burbuja(mensaje: m, mio: m.autor == yo);
        },
      );
    }
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: Row(children: [
          InkWell(
            borderRadius: BorderRadius.circular(999),
            onTap: () => abrirPerfil(context, widget.chat.usuario),
            child: AvatarPerfil(nombre: widget.chat.visible, fotoUrl: widget.chat.fotoUrl, radio: 17),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(widget.chat.visible, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
              Text('@${widget.chat.usuario}', style: estiloDetalle),
            ]),
          ),
        ]),
        actions: [
          TextButton.icon(
            onPressed: _mezcla,
            icon: const Icon(Icons.join_inner_rounded),
            label: const Text('Mezcla'),
          ),
        ],
      ),
      body: Column(children: [
        Expanded(child: lista),
        // se repinta cuando cambia lo que suena (el botón dice qué manda y la barra sube)
        ListenableBuilder(
          listenable: s.reproductor,
          builder: (context, _) {
            final sonando = s.reproductor.actual;
            final enviable = sonando != null && '${sonando['video_id'] ?? ''}'.isNotEmpty;
            final hayTexto = _campo.text.trim().isNotEmpty;
            return SafeArea(
              top: false,
              child: Container(
                // con algo sonando, el mini reproductor va encima: la barra sube
                margin: EdgeInsets.only(bottom: sonando != null ? 74 : 0),
                padding: const EdgeInsets.fromLTRB(Esp.s, Esp.s, Esp.s, Esp.s),
                decoration: BoxDecoration(color: C.panel, border: Border(top: BorderSide(color: C.borde))),
                child: Row(children: [
                  IconButton(
                    tooltip: enviable
                        ? 'Enviar «${sonando['titulo'] ?? 'lo que suena'}»'
                        : 'Enviar la canción que suena',
                    icon: Icon(Icons.music_note_rounded, color: enviable ? C.acento : C.texto3),
                    onPressed: _enviarLoQueSuena,
                  ),
                  IconButton(
                    tooltip: 'Emojis',
                    icon: const Icon(Icons.emoji_emotions_outlined),
                    onPressed: () => elegirEmoji(context, (e) => insertarEnCampo(_campo, e)),
                  ),
                  Expanded(
                    child: TextField(
                      controller: _campo,
                      minLines: 1,
                      maxLines: 4,
                      maxLength: 2000,
                      textCapitalization: TextCapitalization.sentences,
                      textInputAction: TextInputAction.send,
                      decoration: InputDecoration(
                        hintText: 'Escríbele a ${widget.chat.visible}',
                        counterText: '',
                        filled: true,
                        fillColor: C.superficie2,
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(22), borderSide: BorderSide.none),
                      ),
                      onSubmitted: (_) => _enviar(),
                    ),
                  ),
                  const SizedBox(width: 6),
                  IconButton.filled(
                    tooltip: 'Enviar',
                    style: IconButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto,
                        disabledBackgroundColor: C.superficie3),
                    onPressed: hayTexto ? () => _enviar() : null,
                    icon: const Icon(Icons.send_rounded),
                  ),
                ]),
              ),
            );
          },
        ),
      ]),
    );
  }
}

class _Burbuja extends StatelessWidget {
  const _Burbuja({required this.mensaje, required this.mio, this.estado, this.alTocarEstado});
  final Mensaje mensaje;
  final bool mio;
  final String? estado; // «Enviando…» o el fallo, en lugar de la hora
  final VoidCallback? alTocarEstado;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final p = mensaje.pista;
    final ancho = MediaQuery.sizeOf(context).width * 0.78;
    Widget contenido;
    if (p != null) {
      contenido = GestureDetector(
        onTap: () => s.reproducirPista(context, p),
        onLongPress: () => s.hojaPista(context, p),
        child: SizedBox(
          width: 250,
          child: Row(children: [
            Portada(url: '${p['miniatura'] ?? ''}', lado: 54, radio: 6),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${p['titulo'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontWeight: FontWeight.w800, color: mio ? C.acentoTexto : C.texto)),
                Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12.5, color: mio ? C.acentoTexto.withValues(alpha: 0.75) : C.texto2)),
              ]),
            ),
            Icon(Icons.play_circle_fill_rounded, size: 30, color: mio ? C.acentoTexto : C.acento),
          ]),
        ),
      );
    } else {
      contenido = Text(mensaje.texto, style: TextStyle(fontSize: 15.5, color: mio ? C.acentoTexto : C.texto, height: 1.3));
    }
    final pie = Text(estado ?? _hora(mensaje.creado),
        textAlign: TextAlign.right,
        style: TextStyle(fontSize: 10.5, color: mio ? C.acentoTexto.withValues(alpha: 0.7) : C.texto3,
            fontWeight: alTocarEstado != null ? FontWeight.w700 : FontWeight.w400));
    return Align(
      alignment: mio ? Alignment.centerRight : Alignment.centerLeft,
      child: Opacity(
        opacity: estado != null && alTocarEstado == null ? 0.75 : 1,
        child: Container(
          constraints: BoxConstraints(maxWidth: ancho),
          margin: const EdgeInsets.symmetric(vertical: 3),
          padding: EdgeInsets.fromLTRB(12, p != null ? 8 : 9, 12, 6),
          decoration: BoxDecoration(
            color: mio ? C.acento : C.superficie2,
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(18),
              topRight: const Radius.circular(18),
              bottomLeft: Radius.circular(mio ? 18 : 4),
              bottomRight: Radius.circular(mio ? 4 : 18),
            ),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
            contenido,
            const SizedBox(height: 2),
            if (alTocarEstado != null)
              InkWell(onTap: alTocarEstado, child: Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: pie))
            else
              pie,
          ]),
        ),
      ),
    );
  }
}
