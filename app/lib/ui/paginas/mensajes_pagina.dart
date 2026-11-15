import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/chat.dart';
import '../../nucleo/coleccion.dart';
import '../../nucleo/nube.dart';
import '../comunes.dart';
import '../emojis.dart';
import '../servicios.dart';
import '../tema.dart';

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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
    _reloj = Timer.periodic(const Duration(seconds: 8), (_) => _cargar());
  }

  @override
  void dispose() {
    _reloj?.cancel();
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
    final chats = _chats;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mensajes', style: estiloTituloBarra),
        actions: [
          IconButton(tooltip: 'Nuevo mensaje', icon: const Icon(Icons.edit_square), onPressed: _nuevo),
        ],
      ),
      body: _error_ != null && chats == null
          ? Vacio(icono: Icons.wifi_off_rounded, titulo: 'Sin conexión', texto: _error_!, error: true, alAccion: _cargar)
          : chats == null
              ? const Center(child: CircularProgressIndicator())
              : chats.isEmpty
                  ? Vacio(
                      icono: Icons.forum_outlined,
                      titulo: 'Comparte música con tus amigos',
                      texto: 'Escríbele a alguien por su usuario de Caudal, mándale canciones '
                          'y crea una mezcla con lo que escuchan los dos.',
                      textoAccion: 'Escribir a alguien',
                      iconoAccion: Icons.edit_square,
                      alAccion: _nuevo,
                    )
                  : RefreshIndicator(
                      onRefresh: _cargar,
                      child: ListView.builder(
                        itemCount: chats.length,
                        itemBuilder: (_, i) {
                          final c = chats[i];
                          return ListTile(
                            contentPadding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 4),
                            leading: CircleAvatar(radius: 24, backgroundColor: C.superficie3,
                                child: Text(c.inicial, style: TextStyle(color: C.acento, fontWeight: FontWeight.w900, fontSize: 18))),
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

class _DialogoNuevoChatState extends State<_DialogoNuevoChat> {
  static const _ayuda = 'Escribe su usuario de Caudal (el que usa para entrar).';
  final _campo = TextEditingController();
  Timer? _espera;
  Persona? _persona;
  String _estado = _ayuda;
  bool _buscando = false;
  bool _abriendo = false;

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
      _persona = null;
      _buscando = u.length >= 3;
      _estado = u.isEmpty ? _ayuda : u.length < 3 ? 'Sigue escribiendo…' : 'Buscando…';
    });
    if (u.length < 3) return;
    if (u == widget.yo.toLowerCase()) {
      setState(() {
        _buscando = false;
        _estado = 'Ese es tu propio usuario. Escribe el de la otra persona.';
      });
      return;
    }
    _espera = Timer(const Duration(milliseconds: 450), () async {
      try {
        final p = await widget.chat.buscar(u);
        if (!mounted || _escrito != u) return;
        setState(() {
          _buscando = false;
          _persona = p;
          _estado = p == null ? 'No hay nadie con el usuario «$u». Revisa que esté bien escrito.' : '';
        });
      } catch (e) {
        if (mounted) {
          setState(() {
            _buscando = false;
            _estado = _error(e);
          });
        }
      }
    });
  }

  Future<void> _abrir() async {
    final p = _persona;
    if (p == null || _abriendo) return;
    setState(() => _abriendo = true);
    try {
      final id = await widget.chat.abrir(p.id);
      if (!mounted) return;
      Navigator.of(context).pop(ResumenChat(id: id, otro: p.id, usuario: p.usuario, nombre: p.nombre,
          ultimo: DateTime.now()));
    } catch (e) {
      if (mounted) {
        setState(() {
          _abriendo = false;
          _estado = _error(e);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = _persona;
    final visible = p == null ? '' : (p.nombre.isNotEmpty ? p.nombre : p.usuario);
    return AlertDialog(
      backgroundColor: C.superficie2,
      title: const Text('Nuevo mensaje'),
      content: SizedBox(
        width: 380,
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(
            controller: _campo,
            autofocus: true,
            autocorrect: false,
            enableSuggestions: false,
            textInputAction: TextInputAction.go,
            decoration: InputDecoration(
              prefixText: '@',
              hintText: 'usuario',
              filled: true,
              fillColor: C.superficie3,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              suffixIcon: _buscando
                  ? const Padding(padding: EdgeInsets.all(14),
                      child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)))
                  : null,
            ),
            onChanged: _alEscribir,
            onSubmitted: (_) => _abrir(),
          ),
          const SizedBox(height: 12),
          if (p != null)
            Material(
              color: C.superficie3,
              borderRadius: BorderRadius.circular(12),
              child: ListTile(
                leading: CircleAvatar(backgroundColor: C.acento,
                    child: Text(visible.substring(0, 1).toUpperCase(),
                        style: TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900))),
                title: Text(visible, style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text('@${p.usuario}', style: estiloSecundario),
                onTap: _abrir,
              ),
            )
          else
            Text(_estado, style: estiloSecundario),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancelar')),
        FilledButton(
          onPressed: p == null || _abriendo ? null : _abrir,
          child: Text(_abriendo ? 'Abriendo…' : 'Escribir'),
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
            leading: CircleAvatar(backgroundColor: C.superficie3,
                child: Text(c.inicial, style: TextStyle(color: C.acento, fontWeight: FontWeight.w900))),
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

class _ConversacionPaginaState extends State<ConversacionPagina> {
  final _campo = TextEditingController();
  final _scroll = ScrollController();
  List<Mensaje> _mensajes = [];
  bool _cargado = false;
  bool _enviando = false;
  Timer? _reloj;
  Chat? _chat;

  @override
  void initState() {
    super.initState();
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

  Future<void> _cargar() async {
    final c = _chat;
    if (c == null) return;
    try {
      final l = await c.mensajes(widget.chat.id);
      if (!mounted) return;
      setState(() {
        _mensajes = l;
        _cargado = true;
      });
      c.marcarLeido(widget.chat.id);
    } catch (e) {
      if (mounted) {
        setState(() => _cargado = true);
        Caudal.leer(context).avisar(_error(e));
      }
    }
  }

  Future<void> _nuevos() async {
    final c = _chat;
    if (c == null || !_cargado) return;
    try {
      final desde = _mensajes.isEmpty ? 0 : _mensajes.last.id;
      final l = await c.mensajes(widget.chat.id, desde: desde);
      final nuevos = l.where((m) => !_mensajes.any((x) => x.id == m.id)).toList();
      if (nuevos.isEmpty || !mounted) return;
      setState(() => _mensajes = [..._mensajes, ...nuevos]);
      c.marcarLeido(widget.chat.id);
    } catch (_) {}
  }

  Future<void> _enviar({Json? pista}) async {
    final c = _chat;
    final texto = _campo.text.trim();
    if (c == null || _enviando || (texto.isEmpty && pista == null)) return;
    setState(() => _enviando = true);
    try {
      final m = await c.enviar(widget.chat.id, texto: pista == null ? texto : '', pista: pista);
      if (pista == null) _campo.clear();
      if (mounted) setState(() => _mensajes = [..._mensajes, m]);
    } catch (e) {
      if (mounted) Caudal.leer(context).avisar(_error(e));
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
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

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final yo = s.cuenta.id;
    final sonando = s.reproductor.actual;
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: Row(children: [
          CircleAvatar(radius: 17, backgroundColor: C.superficie3,
              child: Text(widget.chat.inicial, style: TextStyle(color: C.acento, fontWeight: FontWeight.w900))),
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
        Expanded(
          child: !_cargado
              ? const Center(child: CircularProgressIndicator())
              : _mensajes.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(32),
                        child: Text('Escríbele algo o mándale lo que estás escuchando.\n\n'
                            'Toca «Mezcla» para crear una lista con lo que escuchan los dos.',
                            textAlign: TextAlign.center, style: estiloSecundario),
                      ),
                    )
                  : ListView.builder(
                      controller: _scroll,
                      reverse: true,
                      padding: const EdgeInsets.symmetric(horizontal: Esp.m, vertical: Esp.m),
                      itemCount: _mensajes.length,
                      itemBuilder: (_, i) {
                        final m = _mensajes[_mensajes.length - 1 - i];
                        return _Burbuja(mensaje: m, mio: m.autor == yo);
                      },
                    ),
        ),
        SafeArea(
          top: false,
          child: Container(
            // con algo sonando, el mini reproductor va encima: la barra sube
            margin: EdgeInsets.only(bottom: s.reproductor.actual != null ? 74 : 0),
            padding: const EdgeInsets.fromLTRB(Esp.s, Esp.s, Esp.s, Esp.s),
            decoration: BoxDecoration(color: C.panel, border: Border(top: BorderSide(color: C.borde))),
            child: Row(children: [
              if (sonando != null && '${sonando['video_id'] ?? ''}'.isNotEmpty)
                IconButton(
                  tooltip: 'Enviar lo que suena',
                  icon: Icon(Icons.music_note_rounded, color: C.acento),
                  onPressed: _enviando ? null : () => _enviar(pista: sonando),
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
                  decoration: InputDecoration(
                    hintText: 'Mensaje',
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
                style: IconButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto),
                onPressed: _enviando ? null : _enviar,
                icon: const Icon(Icons.send_rounded),
              ),
            ]),
          ),
        ),
      ]),
    );
  }
}

class _Burbuja extends StatelessWidget {
  const _Burbuja({required this.mensaje, required this.mio});
  final Mensaje mensaje;
  final bool mio;

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
    return Align(
      alignment: mio ? Alignment.centerRight : Alignment.centerLeft,
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
          Text(_hora(mensaje.creado),
              style: TextStyle(fontSize: 10.5, color: mio ? C.acentoTexto.withValues(alpha: 0.6) : C.texto3)),
        ]),
      ),
    );
  }
}
