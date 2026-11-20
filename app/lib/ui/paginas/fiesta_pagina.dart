import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../../nucleo/fiesta.dart';
import '../../nucleo/qr.dart';
import '../../reproduccion/fiesta_control.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';

/// «Fiesta»: el anfitrión enseña un QR; los invitados piden canciones y votan desde la web,
/// sin instalar nada. La fiesta sigue aunque se cierre esta pantalla (vive en
/// [FiestaAnfitrion.activa]) hasta tocar «Cerrar la fiesta».
///
/// [crear] sirve para las pruebas (en la app se usa la base de verdad).
class FiestaPagina extends StatelessWidget {
  const FiestaPagina({super.key, this.crear});
  final Future<FiestaAnfitrion> Function(String nombre, int limite)? crear;

  static Future<void> abrir(BuildContext context) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const FiestaPagina()));

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: C.fondo,
        appBar: AppBar(title: const Text('Fiesta'), backgroundColor: C.fondo),
        body: ValueListenableBuilder<FiestaAnfitrion?>(
          valueListenable: FiestaAnfitrion.activa,
          builder: (_, f, _) => f == null ? _Crear(crear: crear) : _VistaFiesta(fiesta: f),
        ),
      );
}

// ---------------------------------------------------------------- crear

const _limites = [(1, '1'), (3, '3'), (5, '5'), (10, '10'), (0, 'Sin límite')];

class _Crear extends StatefulWidget {
  const _Crear({this.crear});
  final Future<FiestaAnfitrion> Function(String nombre, int limite)? crear;

  @override
  State<_Crear> createState() => _CrearState();
}

class _CrearState extends State<_Crear> {
  final _nombre = TextEditingController();
  int _limite = 5;
  bool _ocupado = false;
  String? _error;

  @override
  void dispose() {
    _nombre.dispose();
    super.dispose();
  }

  Future<void> _empezar() async {
    setState(() {
      _ocupado = true;
      _error = null;
    });
    try {
      final crear = widget.crear ??
          (String n, int l) => FiestaAnfitrion.crear(
              control: ControlFiestaReproductor(Caudal.leer(context).reproductor), nombre: n, limite: l);
      FiestaAnfitrion.activa.value = await crear(_nombre.text, _limite);
    } on ErrorFiesta catch (e) {
      _error = e.mensaje;
    } catch (_) {
      _error = 'No se pudo abrir la fiesta. Revisa tu conexión a internet.';
    }
    if (mounted) setState(() => _ocupado = false);
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          const Text('Tus amigos escanean un QR con la cámara y, desde su teléfono, piden canciones '
              'y votan cuál suena después. No necesitan instalar nada ni tener cuenta.', style: estiloSecundario),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(14)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Text('Nombre de la fiesta', style: TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              TextField(
                controller: _nombre,
                maxLength: 60,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(hintText: 'Cumple de Lu', border: OutlineInputBorder(), counterText: ''),
              ),
              const SizedBox(height: 16),
              const Text('¿Cuántas canciones puede pedir cada invitado?', style: TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final (n, t) in _limites)
                  ChoiceChip(label: Text(t), selected: _limite == n, onSelected: (_) => setState(() => _limite = n)),
              ]),
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: _ocupado ? null : _empezar,
                icon: const Icon(Icons.celebration_rounded),
                label: const Text('Empezar la fiesta'),
              ),
            ]),
          ),
          if (_ocupado) const Padding(padding: EdgeInsets.only(top: 20), child: Center(child: CircularProgressIndicator())),
          if (_error != null)
            Padding(padding: const EdgeInsets.only(top: 16), child: Text(_error!, style: const TextStyle(color: C.error))),
        ],
      );
}

// ---------------------------------------------------------------- QR

/// Dibuja un [CodigoQr] negro sobre blanco con su margen.
class QrDibujo extends StatelessWidget {
  const QrDibujo({super.key, required this.qr, this.lado = 220});
  final CodigoQr qr;
  final double lado;

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'Código QR de la fiesta',
        image: true,
        child: Container(
          width: lado,
          height: lado,
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
          child: CustomPaint(painter: _PintorQr(qr)),
        ),
      );
}

class _PintorQr extends CustomPainter {
  _PintorQr(this.qr);
  final CodigoQr qr;

  @override
  void paint(Canvas canvas, Size size) {
    final total = qr.lado + 8; // 4 módulos de margen a cada lado
    final m = size.shortestSide / total;
    final p = Paint()..color = Colors.black;
    for (var y = 0; y < qr.lado; y++) {
      for (var x = 0; x < qr.lado; x++) {
        // un pelín más grande para que no queden rayas entre módulos
        if (qr.oscuro(x, y)) canvas.drawRect(Rect.fromLTWH((x + 4) * m, (y + 4) * m, m + 0.5, m + 0.5), p);
      }
    }
  }

  @override
  bool shouldRepaint(_PintorQr old) => old.qr != qr;
}

// ---------------------------------------------------------------- en la fiesta

class _VistaFiesta extends StatefulWidget {
  const _VistaFiesta({required this.fiesta});
  final FiestaAnfitrion fiesta;

  @override
  State<_VistaFiesta> createState() => _VistaFiestaState();
}

class _VistaFiestaState extends State<_VistaFiesta> {
  late CodigoQr _qr = CodigoQr.de(widget.fiesta.enlace);

  @override
  void didUpdateWidget(_VistaFiesta old) {
    super.didUpdateWidget(old);
    if (old.fiesta.codigo != widget.fiesta.codigo) _qr = CodigoQr.de(widget.fiesta.enlace);
  }

  void _avisar(String t) {
    try {
      Caudal.leer(context).avisar(t);
    } catch (_) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(t)));
    }
  }

  Future<void> _copiar() async {
    await Clipboard.setData(ClipboardData(text: widget.fiesta.enlace));
    if (mounted) _avisar('Enlace copiado');
  }

  Future<void> _compartir() async {
    final f = widget.fiesta;
    await SharePlus.instance.share(ShareParams(
        text: '¡Pide canciones en mi fiesta! Entra aquí: ${f.enlace} (código ${codigoVisible(f.codigo)})'));
  }

  Future<void> _cerrar() async {
    final ok = await confirmar(context, 'Cerrar la fiesta',
        'Nadie más podrá pedir ni votar canciones. La música que suena sigue sonando.', si: 'Cerrar la fiesta');
    if (!ok) return;
    await widget.fiesta.cerrar();
    if (mounted) _avisar('La fiesta se cerró');
  }

  void _qrGrande() => showDialog<void>(
        context: context,
        builder: (_) => Dialog(
          backgroundColor: Colors.white,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              LayoutBuilder(builder: (_, c) => QrDibujo(qr: _qr, lado: c.maxWidth.clamp(200, 520).toDouble())),
              const SizedBox(height: 10),
              Text(codigoVisible(widget.fiesta.codigo),
                  style: const TextStyle(color: Colors.black, fontSize: 34, fontWeight: FontWeight.w900, letterSpacing: 6)),
            ]),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: widget.fiesta,
        builder: (context, _) {
          final f = widget.fiesta;
          final e = f.estado;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
            children: [
              Text(e?.nombre ?? 'Fiesta', style: estiloTituloPagina),
              const SizedBox(height: 4),
              Text(
                  [
                    if (e != null) e.invitados == 1 ? '1 invitado' : '${e.invitados} invitados',
                    f.conectado ? 'en vivo' : 'conectando…',
                  ].join(' · '),
                  style: estiloSecundario),
              const SizedBox(height: 14),
              _tarjetaQr(f),
              const SizedBox(height: 12),
              _Suena(sonando: e?.sonando),
              if (f.error != null)
                Padding(padding: const EdgeInsets.only(top: 10), child: Text(f.error!, style: const TextStyle(color: C.error))),
              const SizedBox(height: 12),
              _ajustes(f, e),
              const SizedBox(height: 16),
              Row(children: [
                const Expanded(child: Text('Siguientes', style: estiloTituloSeccion)),
                if (e != null && e.cola.isNotEmpty && !f.automatico)
                  TextButton.icon(
                    onPressed: () => f.tomarSiguiente(),
                    icon: const Icon(Icons.queue_music_rounded),
                    label: const Text('Poner la siguiente'),
                  ),
              ]),
              const SizedBox(height: 6),
              if (e == null)
                const Padding(padding: EdgeInsets.all(20), child: Center(child: CircularProgressIndicator()))
              else if (e.cola.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 18),
                  child: Text('Todavía nadie pidió canciones. Enseña el QR para que empiecen.',
                      style: estiloSecundario, textAlign: TextAlign.center),
                )
              else
                for (final (i, c) in e.cola.indexed) _FilaCola(puesto: i + 1, c: c, fiesta: f),
              const SizedBox(height: 24),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: C.error, side: const BorderSide(color: C.error)),
                onPressed: f.cerrada ? null : _cerrar,
                icon: const Icon(Icons.stop_circle_outlined),
                label: Text(f.cerrada ? 'La fiesta está cerrada' : 'Cerrar la fiesta'),
              ),
            ],
          );
        },
      );

  Widget _tarjetaQr(FiestaAnfitrion f) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(18)),
        child: Column(children: [
          GestureDetector(onTap: _qrGrande, child: QrDibujo(qr: _qr, lado: 220)),
          const SizedBox(height: 12),
          const Text('Escanéalo con la cámara del teléfono, o entra en la web de Caudal y escribe:',
              style: estiloSecundario, textAlign: TextAlign.center),
          const SizedBox(height: 6),
          SelectableText(codigoVisible(f.codigo),
              style: const TextStyle(fontSize: 34, fontWeight: FontWeight.w900, letterSpacing: 6)),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, alignment: WrapAlignment.center, children: [
            FilledButton.tonalIcon(onPressed: _compartir, icon: const Icon(Icons.share_rounded), label: const Text('Compartir')),
            FilledButton.tonalIcon(onPressed: _copiar, icon: const Icon(Icons.link_rounded), label: const Text('Copiar enlace')),
            FilledButton.tonalIcon(onPressed: _qrGrande, icon: const Icon(Icons.fullscreen_rounded), label: const Text('QR grande')),
          ]),
        ]),
      );

  // Material (no Container) por dentro: el SwitchListTile pinta sobre el Material más cercano.
  Widget _ajustes(FiestaAnfitrion f, EstadoFiesta? e) => Material(
        color: C.superficie,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: f.automatico,
              onChanged: f.cerrada ? null : f.fijarAutomatico,
              title: const Text('Poner las canciones pedidas solas'),
              subtitle: const Text('Al acabar cada canción suena la más votada.', style: estiloSecundario),
            ),
            Text(e == null ? '' : textoLimite(e.limite), style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final (n, t) in _limites)
                ChoiceChip(
                  label: Text(t),
                  selected: e?.limite == n,
                  onSelected: f.cerrada || e == null ? null : (_) => f.fijarLimite(n),
                ),
            ]),
          ]),
        ),
      );
}

class _Suena extends StatelessWidget {
  const _Suena({required this.sonando});
  final SonandoFiesta? sonando;

  @override
  Widget build(BuildContext context) {
    final s = sonando;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: LinearGradient(colors: [C.violeta.withValues(alpha: 0.35), C.superficie]),
      ),
      child: Row(children: [
        Portada(url: s?.miniatura ?? '', lado: 60, radio: 10),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(s == null ? 'LOS INVITADOS VEN LO QUE SUENA' : (s.pausa ? 'EN PAUSA' : 'AHORA SUENA'),
                style: TextStyle(color: C.acento, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1)),
            const SizedBox(height: 2),
            Text(s == null ? 'Pon música en Caudal' : (s.titulo.isEmpty ? 'Sin título' : s.titulo),
                maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
            if (s != null && (s.artista.isNotEmpty || s.nombre.isNotEmpty))
              Text([s.artista, if (s.nombre.isNotEmpty) 'la pidió ${s.nombre}'].where((t) => t.isNotEmpty).join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
          ]),
        ),
      ]),
    );
  }
}

class _FilaCola extends StatelessWidget {
  const _FilaCola({required this.puesto, required this.c, required this.fiesta});
  final int puesto;
  final CancionFiesta c;
  final FiestaAnfitrion fiesta;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(children: [
          SizedBox(width: 26, child: Text('$puesto', textAlign: TextAlign.center, style: estiloDetalle)),
          Portada(url: c.miniatura, lado: 48, radio: 8),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(c.titulo, maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloTituloFila),
              Text(
                  [
                    if (c.artista.isNotEmpty) c.artista,
                    'pedida por ${c.quien}',
                    c.votos == 1 ? '1 voto' : '${c.votos} votos',
                  ].join(' · '),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: estiloSubTarjeta),
            ]),
          ),
          IconButton(
            tooltip: 'Poner ahora',
            onPressed: fiesta.cerrada ? null : () => fiesta.ponerAhora(c),
            icon: const Icon(Icons.play_circle_outline_rounded),
          ),
          IconButton(
            tooltip: 'Quitar de la cola',
            onPressed: fiesta.cerrada ? null : () => fiesta.quitar(c),
            icon: const Icon(Icons.remove_circle_outline_rounded),
          ),
        ]),
      );
}
