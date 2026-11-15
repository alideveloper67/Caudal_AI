import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/juntos.dart';
import '../../reproduccion/reproductor.dart';
import '../comunes.dart';
import '../emojis.dart';
import '../servicios.dart';
import '../tema.dart';

/// "Escuchar juntos": crear una sala, unirse con código o enlace, ver quién
/// está y mandar reacciones. La sala sigue abierta aunque se cierre esta
/// pantalla (vive en [SalaJuntos.activa]) hasta pulsar "Salir de la sala".
///
/// [codigoInicial] (un código o un enlace caudal://juntos?sala=…) hace que
/// se una a esa sala nada más abrir.
class JuntosPagina extends StatefulWidget {
  const JuntosPagina({super.key, this.codigoInicial});
  final String? codigoInicial;

  @override
  State<JuntosPagina> createState() => _JuntosPaginaState();
}

class _JuntosPaginaState extends State<JuntosPagina> {
  final _campo = TextEditingController();
  bool _ocupado = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final c = widget.codigoInicial;
    if (c != null && c.trim().isNotEmpty) {
      _campo.text = codigoDeTexto(c) ?? c;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && codigoDeTexto(c) != SalaJuntos.activa.value?.codigo) _unirse();
      });
    }
  }

  @override
  void dispose() {
    _campo.dispose();
    super.dispose();
  }

  Future<void> _abrir(Future<SalaJuntos> Function(ControlJuntos, String, String) como) async {
    final s = Caudal.leer(context);
    setState(() {
      _ocupado = true;
      _error = null;
    });
    try {
      await SalaJuntos.activa.value?.salir();
      final sala = await como(ControlReproductor(s.reproductor), s.cuenta.nombre, s.cuenta.usuario);
      SalaJuntos.activa.value = sala;
    } on ErrorJuntos catch (e) {
      _error = e.mensaje;
    } catch (_) {
      _error = 'No se pudo abrir la sala. Revisa tu conexión a internet.';
    }
    if (mounted) setState(() => _ocupado = false);
  }

  Future<void> _crear() =>
      _abrir((c, n, u) => SalaJuntos.crear(control: c, nombre: n, usuario: u));

  Future<void> _unirse() {
    if (codigoDeTexto(_campo.text) == null) {
      setState(() => _error = 'Escribe el código de 6 letras o números, o pega el enlace.');
      return Future.value();
    }
    return _abrir((c, n, u) => SalaJuntos.unirse(_campo.text, control: c, nombre: n, usuario: u));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C.fondo,
      appBar: AppBar(title: const Text('Escuchar juntos'), backgroundColor: C.fondo),
      body: ValueListenableBuilder<SalaJuntos?>(
        valueListenable: SalaJuntos.activa,
        builder: (_, sala, _) => sala == null ? _entrada() : _VistaSala(sala: sala),
      ),
    );
  }

  Widget _entrada() => ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          const Text('Oigan lo mismo a la vez, cada uno en su teléfono.', style: estiloSecundario),
          const SizedBox(height: 20),
          _Bloque(
            icono: Icons.podcasts_rounded,
            titulo: 'Crear una sala',
            texto: 'Tú pones la música; los demás la oyen sincronizada.',
            child: FilledButton.icon(
              onPressed: _ocupado ? null : _crear,
              icon: const Icon(Icons.add_rounded),
              label: const Text('Crear sala'),
            ),
          ),
          const SizedBox(height: 14),
          _Bloque(
            icono: Icons.group_add_rounded,
            titulo: 'Unirse a una sala',
            texto: 'Escribe el código que te pasaron o pega el enlace.',
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              TextField(
                controller: _campo,
                textCapitalization: TextCapitalization.characters,
                textInputAction: TextInputAction.go,
                onSubmitted: (_) => _ocupado ? null : _unirse(),
                style: const TextStyle(fontSize: 20, letterSpacing: 4, fontWeight: FontWeight.w700),
                decoration: const InputDecoration(hintText: 'ABC234', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 10),
              FilledButton.tonalIcon(
                onPressed: _ocupado ? null : _unirse,
                icon: const Icon(Icons.login_rounded),
                label: const Text('Unirme'),
              ),
            ]),
          ),
          if (_ocupado) const Padding(padding: EdgeInsets.only(top: 20), child: Center(child: CircularProgressIndicator())),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Text(_error!, style: const TextStyle(color: C.error)),
            ),
        ],
      );
}

class _Bloque extends StatelessWidget {
  const _Bloque({required this.icono, required this.titulo, required this.texto, required this.child});
  final IconData icono;
  final String titulo;
  final String texto;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Icon(icono, color: C.acento),
            const SizedBox(width: 10),
            Text(titulo, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
          ]),
          const SizedBox(height: 6),
          Text(texto, style: estiloSecundario),
          const SizedBox(height: 14),
          child,
        ]),
      );
}

// ---------------------------------------------------------------- en la sala

class _VistaSala extends StatefulWidget {
  const _VistaSala({required this.sala});
  final SalaJuntos sala;

  @override
  State<_VistaSala> createState() => _VistaSalaState();
}

class _Flotante {
  _Flotante(this.emoji, this.x, this.nombre);
  final String emoji;
  final double x;
  final String nombre;
  final key = UniqueKey();
}

class _VistaSalaState extends State<_VistaSala> {
  StreamSubscription<ReaccionJuntos>? _sub;
  final _flotantes = <_Flotante>[];
  int _leidos = 0;
  final _azar = Random();

  @override
  void initState() {
    super.initState();
    _escuchar();
  }

  @override
  void didUpdateWidget(_VistaSala old) {
    super.didUpdateWidget(old);
    if (!identical(old.sala, widget.sala)) {
      _sub?.cancel();
      _escuchar();
    }
  }

  void _escuchar() {
    _sub = widget.sala.reacciones.listen((r) {
      if (!mounted || _flotantes.length > 30) return;
      setState(() => _flotantes.add(_Flotante(r.emoji, 0.1 + _azar.nextDouble() * 0.8, r.deMi ? '' : r.nombre)));
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  Future<void> _compartir(SalaJuntos sala) async {
    final texto = 'Escucha conmigo en Caudal: ${sala.enlace}\n(o entra con el código ${sala.codigo})';
    try {
      await SharePlus.instance.share(ShareParams(text: texto));
    } catch (_) {
      await Clipboard.setData(ClipboardData(text: texto));
      if (mounted) Caudal.leer(context).avisar('Enlace copiado');
    }
  }

  Future<void> _salir(SalaJuntos sala) async {
    if (!await confirmar(context, 'Salir de la sala', 'Dejarás de oír lo mismo que los demás.', si: 'Salir')) return;
    await sala.salir();
  }

  @override
  Widget build(BuildContext context) {
    final sala = widget.sala;
    return ListenableBuilder(
      listenable: sala,
      builder: (context, _) {
        final aviso = sala.aviso;
        if (aviso != null) {
          sala.aviso = null;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) Caudal.leer(context).avisar(aviso);
          });
        }
        final sinLeer = sala.chat.length - _leidos;
        return Stack(children: [
          DefaultTabController(
            length: 2,
            child: Builder(builder: (ctx) {
              final tabs = DefaultTabController.of(ctx);
              return Column(children: [
                TabBar(
                  indicatorColor: C.acento,
                  labelColor: C.texto,
                  unselectedLabelColor: C.texto3,
                  dividerColor: C.borde,
                  onTap: (i) {
                    if (i == 1) setState(() => _leidos = sala.chat.length);
                  },
                  tabs: [
                    const Tab(text: 'Sala'),
                    Tab(child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Text('Chat'),
                      if (sinLeer > 0 && tabs.index != 1) ...[
                        const SizedBox(width: 6),
                        Badge(label: Text('$sinLeer'), backgroundColor: C.acento, textColor: C.acentoTexto),
                      ],
                    ])),
                  ],
                ),
                Expanded(
                  child: TabBarView(children: [
                    Stack(children: [
          ListView(padding: const EdgeInsets.fromLTRB(20, 16, 20, 120), children: [
            _codigo(sala),
            const SizedBox(height: 18),
            _sonando(sala),
            const SizedBox(height: 22),
            Text('En la sala (${sala.miembros.length})', style: estiloTituloSeccion),
            const SizedBox(height: 6),
            for (final m in sala.miembros) _miembro(sala, m),
            const SizedBox(height: 24),
            OutlinedButton.icon(
              onPressed: () => _salir(sala),
              icon: const Icon(Icons.logout_rounded),
              label: const Text('Salir de la sala'),
              style: OutlinedButton.styleFrom(foregroundColor: C.error),
            ),
          ]),
          Positioned(left: 0, right: 0, bottom: 0, child: _barraEmojis(sala)),
                    ]),
                    _ChatSala(sala: sala, alLeer: () => _leidos = sala.chat.length),
                  ]),
                ),
              ]);
            }),
          ),
          Positioned.fill(
            child: IgnorePointer(
              child: LayoutBuilder(
                builder: (_, c) => Stack(children: [
                  for (final f in _flotantes)
                    _EmojiFlotante(
                      key: f.key,
                      flotante: f,
                      ancho: c.maxWidth,
                      alto: c.maxHeight,
                      alTerminar: () {
                        if (mounted) setState(() => _flotantes.remove(f));
                      },
                    ),
                ]),
              ),
            ),
          ),
        ]);
      },
    );
  }

  Widget _codigo(SalaJuntos sala) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF123A44), Color(0xFF231A4A)]),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon(sala.conectado ? Icons.circle : Icons.circle_outlined,
                    size: 10, color: sala.conectado ? C.exito : C.texto3),
                const SizedBox(width: 6),
                Text(sala.conectado ? 'Código de la sala' : 'Reconectando…', style: estiloSecundario),
              ]),
              const SizedBox(height: 4),
              SelectableText(sala.codigo,
                  style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w900, letterSpacing: 6)),
            ]),
          ),
          IconButton(
            tooltip: 'Copiar código',
            icon: const Icon(Icons.copy_rounded),
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: sala.codigo));
              if (mounted) Caudal.leer(context).avisar('Código copiado');
            },
          ),
          IconButton.filled(
            tooltip: 'Invitar',
            icon: const Icon(Icons.share_rounded),
            onPressed: () => _compartir(sala),
          ),
        ]),
      );

  Widget _sonando(SalaJuntos sala) {
    final p = sala.pistaSala;
    final quien = sala.soyAnfitrion ? 'Tú pones la música' : 'Pone la música ${sala.anfitrion?.nombre ?? '…'}';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(colors: [Color.lerp(C.acento, C.superficie, 0.72)!, C.superficie],
            begin: Alignment.topLeft, end: Alignment.bottomRight),
      ),
      child: Row(children: [
        Portada(url: '${p?['miniatura'] ?? ''}', lado: 96, radio: 12),
        const SizedBox(width: 14),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(p == null ? 'EN SILENCIO' : 'AHORA SUENA',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1, color: C.acento)),
            const SizedBox(height: 4),
            Text(p == null ? 'Aún no suena nada' : '${p['titulo'] ?? ''}',
                maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, height: 1.15)),
            if (p != null && '${p['artista'] ?? ''}'.isNotEmpty)
              Text('${p['artista']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
            const SizedBox(height: 8),
            Row(children: [
              Icon(Icons.headphones_rounded, size: 15, color: C.acento),
              const SizedBox(width: 5),
              Expanded(
                child: Text(sala.soyAnfitrion ? '$quien: lo oyen todos' : quien,
                    maxLines: 2, style: const TextStyle(fontSize: 12, color: C.texto2)),
              ),
            ]),
          ]),
        ),
      ]),
    );
  }

  Widget _miembro(SalaJuntos sala, MiembroJuntos m) {
    final esAnf = m.id == sala.anfitrionId;
    final soyYo = m.id == sala.miId;
    final inicial = m.nombre.isEmpty ? '?' : m.nombre.substring(0, 1).toUpperCase();
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: CircleAvatar(
        backgroundColor: esAnf ? C.acento : C.superficie3,
        foregroundColor: esAnf ? C.acentoTexto : C.texto,
        child: Text(inicial, style: const TextStyle(fontWeight: FontWeight.w800)),
      ),
      title: Text(soyYo ? '${m.nombre} (tú)' : m.nombre),
      subtitle: m.usuario.isEmpty ? null : Text('@${m.usuario}', style: estiloSecundario),
      trailing: esAnf
          ? Tooltip(message: 'Pone la música', child: Icon(Icons.workspace_premium_rounded, color: C.acento))
          : (sala.soyAnfitrion && !soyYo
              ? TextButton(onPressed: () => sala.cederAnfitrion(m.id), child: const Text('Pasar el mando'))
              : null),
    );
  }

  Widget _barraEmojis(SalaJuntos sala) => SafeArea(
        top: false,
        child: Container(
          margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
          padding: const EdgeInsets.symmetric(vertical: 6),
          decoration: BoxDecoration(
            color: C.superficie2,
            borderRadius: BorderRadius.circular(40),
            border: Border.all(color: C.borde),
          ),
          child: Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
            for (final e in emojisJuntos)
              InkResponse(
                onTap: () => sala.reaccionar(e),
                radius: 24,
                child: Padding(padding: const EdgeInsets.all(6), child: Text(e, style: const TextStyle(fontSize: 24))),
              ),
          ]),
        ),
      );
}

/// Un emoji que sube balanceándose y se desvanece.
class _EmojiFlotante extends StatefulWidget {
  const _EmojiFlotante({super.key, required this.flotante, required this.ancho, required this.alto,
      required this.alTerminar});
  final _Flotante flotante;
  final double ancho;
  final double alto;
  final VoidCallback alTerminar;

  @override
  State<_EmojiFlotante> createState() => _EmojiFlotanteState();
}

class _EmojiFlotanteState extends State<_EmojiFlotante> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 2600))
    ..addStatusListener((s) {
      if (s == AnimationStatus.completed) widget.alTerminar();
    })
    ..forward();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _c,
        builder: (_, _) {
          final t = Curves.easeOut.transform(_c.value);
          final y = widget.alto - 90 - t * widget.alto * 0.7;
          final x = widget.flotante.x * widget.ancho + sin(_c.value * pi * 3) * 18 - 20;
          final opacidad = _c.value < 0.7 ? 1.0 : (1 - (_c.value - 0.7) / 0.3);
          final escala = 0.6 + min(1.0, _c.value * 5) * 0.6;
          return Positioned(
            left: x,
            top: y,
            child: Opacity(
              opacity: opacidad.clamp(0.0, 1.0),
              child: Transform.scale(
                scale: escala,
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  Text(widget.flotante.emoji, style: const TextStyle(fontSize: 36)),
                  if (widget.flotante.nombre.isNotEmpty)
                    Text(widget.flotante.nombre, style: const TextStyle(fontSize: 11, color: C.texto2)),
                ]),
              ),
            ),
          );
        },
      );
}

/// El [Reproductor] de la app visto como [ControlJuntos].
class ControlReproductor implements ControlJuntos {
  ControlReproductor(this.r, {this.titulo = 'Escuchar juntos'});
  final Reproductor r;
  final String titulo;

  @override
  Json? get pista => r.actual;
  @override
  Duration get posicion => r.posicion.value;
  @override
  bool get sonando => r.estado == EstadoRepro.sonando;
  @override
  bool get cargando => r.estado == EstadoRepro.cargando;

  @override
  Future<void> cargar(Json pista, {Duration inicio = Duration.zero, bool pausado = false}) async {
    await r.reproducirLista([Json.of(pista)], contexto: {'tipo': 'juntos', 'id': '', 'titulo': titulo});
    if (inicio > const Duration(seconds: 1)) await r.buscar(inicio);
    if (pausado) await r.pausar();
  }

  @override
  Future<void> buscar(Duration p) => r.buscar(p);
  @override
  Future<void> pausar() => r.pausar();
  @override
  Future<void> reanudar() => r.reanudar();
  @override
  void addListener(VoidCallback f) => r.addListener(f);
  @override
  void removeListener(VoidCallback f) => r.removeListener(f);
}


/// El chat de la sala: mensajes que solo ven los que están dentro.
class _ChatSala extends StatefulWidget {
  const _ChatSala({required this.sala, required this.alLeer});
  final SalaJuntos sala;
  final VoidCallback alLeer;

  @override
  State<_ChatSala> createState() => _ChatSalaState();
}

class _ChatSalaState extends State<_ChatSala> {
  final _campo = TextEditingController();

  @override
  void dispose() {
    _campo.dispose();
    super.dispose();
  }

  void _enviar() {
    if (widget.sala.enviarChat(_campo.text)) _campo.clear();
  }

  String _hora(int t) {
    final d = DateTime.fromMillisecondsSinceEpoch(t);
    return '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final sala = widget.sala;
    widget.alLeer();
    final mensajes = sala.chat;
    return Column(children: [
      Expanded(
        child: mensajes.isEmpty
            ? const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: Text('Aún no hay mensajes. ¡Saluda a la sala! 👋', textAlign: TextAlign.center,
                      style: estiloSecundario),
                ),
              )
            : ListView.builder(
                reverse: true,
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
                itemCount: mensajes.length,
                itemBuilder: (_, i) {
                  final m = mensajes[mensajes.length - 1 - i];
                  final mio = m.de == sala.miId;
                  return Align(
                    alignment: mio ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.78),
                      margin: const EdgeInsets.symmetric(vertical: 3),
                      padding: const EdgeInsets.fromLTRB(12, 8, 12, 6),
                      decoration: BoxDecoration(
                        color: mio ? C.acento : C.superficie2,
                        borderRadius: BorderRadius.only(
                          topLeft: const Radius.circular(18), topRight: const Radius.circular(18),
                          bottomLeft: Radius.circular(mio ? 18 : 4), bottomRight: Radius.circular(mio ? 4 : 18)),
                      ),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                        if (!mio)
                          Text(m.nombre, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: C.acento)),
                        Text(m.texto, style: TextStyle(fontSize: 15.5, height: 1.3, color: mio ? C.acentoTexto : C.texto)),
                        Align(
                          alignment: Alignment.centerRight,
                          child: Text(_hora(m.t), style: TextStyle(fontSize: 10.5,
                              color: mio ? C.acentoTexto.withValues(alpha: 0.6) : C.texto3)),
                        ),
                      ]),
                    ),
                  );
                },
              ),
      ),
      SafeArea(
        top: false,
        child: Container(
          margin: EdgeInsets.only(bottom: Caudal.of(context).reproductor.actual != null ? 74 : 0),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: C.panel, border: Border(top: BorderSide(color: C.borde))),
          child: Row(children: [
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
                maxLength: MensajeSala.largo,
                textCapitalization: TextCapitalization.sentences,
                decoration: InputDecoration(
                  hintText: 'Escribe a la sala…',
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
              onPressed: _enviar,
              icon: const Icon(Icons.send_rounded),
            ),
          ]),
        ),
      ),
    ]);
  }
}
