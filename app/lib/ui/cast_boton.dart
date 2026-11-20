import 'dart:async';

import 'package:flutter/material.dart';

import '../reproduccion/cast.dart';
import 'tema.dart';

/// El botón de Cast del reproductor: busca las teles, Chromecast y altavoces
/// de la wifi y manda allí la música. Donde no hay Cast (web, PC, teléfonos sin
/// servicios de Google) no aparece.
class CastBoton extends StatelessWidget {
  const CastBoton({super.key, required this.control, this.color});

  final ControlCast control;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: control,
      builder: (context, _) {
        if (!control.soportado) return const SizedBox.shrink();
        final conectando = control.conexion == ConexionCast.conectando;
        final activo = control.activo;
        return IconButton(
          tooltip: activo ? 'Sonando en ${control.dispositivo?.nombre ?? 'la tele'}' : 'Enviar a una tele o altavoz',
          icon: conectando
              ? const _Parpadeo(child: Icon(Icons.cast_rounded))
              : Icon(activo ? Icons.cast_connected_rounded : Icons.cast_rounded,
                  color: activo ? C.acento : color),
          onPressed: () => mostrarHojaCast(context, control),
        );
      },
    );
  }
}

/// La hoja para elegir dónde suena (o, si ya suena en la tele, su volumen y
/// el botón para volver al teléfono).
Future<void> mostrarHojaCast(BuildContext context, ControlCast control) {
  return showModalBottomSheet<void>(
    context: context,
    backgroundColor: C.superficie,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (_) => HojaCast(control: control),
  );
}

class HojaCast extends StatefulWidget {
  const HojaCast({super.key, required this.control});

  final ControlCast control;

  @override
  State<HojaCast> createState() => _HojaCastState();
}

class _HojaCastState extends State<HojaCast> {
  /// Pasado este rato sin encontrar nada se explica por qué.
  static const _paciencia = Duration(seconds: 8);
  bool _esperado = false;
  Timer? _reloj;

  ControlCast get c => widget.control;

  @override
  void initState() {
    super.initState();
    // después del primer cuadro: buscar avisa a quien escucha y no se puede durante la construcción
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && !c.activo) unawaited(c.buscarDispositivos());
    });
    _reloj = Timer(_paciencia, () {
      if (mounted) setState(() => _esperado = true);
    });
  }

  @override
  void dispose() {
    _reloj?.cancel();
    final control = c;
    scheduleMicrotask(() => unawaited(control.dejarDeBuscar()));
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: ListenableBuilder(
        listenable: c,
        builder: (context, _) => Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
          child: c.activo ? _conectado(context) : _lista(context),
        ),
      ),
    );
  }

  Widget _titulo(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Text(t, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
      );

  Widget _lista(BuildContext context) {
    final lista = c.dispositivos;
    final conectando = c.conexion == ConexionCast.conectando;
    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
      _titulo('Escuchar en otro aparato'),
      if (lista.isEmpty && !_esperado)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 18),
          child: Row(children: [
            SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4)),
            SizedBox(width: 16),
            Expanded(child: Text('Buscando teles y altavoces…')),
          ]),
        ),
      if (lista.isEmpty && _esperado)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 14),
          child: Text('No encuentro ninguna tele ni altavoz. El teléfono y la tele tienen que estar '
              'conectados a la misma wifi.', style: TextStyle(height: 1.35)),
        ),
      ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.5),
        child: ListView(shrinkWrap: true, children: [
          for (final d in lista)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(d.esAltavoz ? Icons.speaker_rounded : Icons.tv_rounded),
              title: Text(d.nombre, maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: d.modelo.isEmpty ? null : Text(d.modelo, maxLines: 1, overflow: TextOverflow.ellipsis),
              trailing: conectando && c.dispositivo == d
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.2))
                  : null,
              onTap: conectando
                  ? null
                  : () async {
                      await c.conectar(d);
                      if (context.mounted) Navigator.of(context).maybePop();
                    },
            ),
        ]),
      ),
    ]);
  }

  Widget _conectado(BuildContext context) {
    final d = c.dispositivo;
    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Icon(d?.esAltavoz == true ? Icons.speaker_rounded : Icons.tv_rounded, color: C.acento),
        const SizedBox(width: 12),
        Expanded(
          child: Text('Sonando en ${d?.nombre ?? 'la tele'}', maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        ),
      ]),
      const SizedBox(height: 18),
      Row(children: [
        const Icon(Icons.volume_down_rounded),
        Expanded(
          child: Slider(
            value: c.volumen.clamp(0.0, 1.0),
            onChanged: (v) => c.fijarVolumen(v),
            semanticFormatterCallback: (v) => 'Volumen ${(v * 100).round()} %',
          ),
        ),
        const Icon(Icons.volume_up_rounded),
      ]),
      const SizedBox(height: 10),
      SizedBox(
        width: double.infinity,
        child: FilledButton.tonalIcon(
          icon: const Icon(Icons.phone_android_rounded),
          label: const Text('Volver a escuchar en el teléfono'),
          onPressed: () async {
            await c.desconectar();
            if (context.mounted) Navigator.of(context).maybePop();
          },
        ),
      ),
    ]);
  }
}

/// El icono parpadea mientras se conecta (como el botón de Cast de Google).
class _Parpadeo extends StatefulWidget {
  const _Parpadeo({required this.child});

  final Widget child;

  @override
  State<_Parpadeo> createState() => _ParpadeoState();
}

class _ParpadeoState extends State<_Parpadeo> with SingleTickerProviderStateMixin {
  late final AnimationController _a =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 700))..repeat(reverse: true);

  @override
  void dispose() {
    _a.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      FadeTransition(opacity: Tween(begin: 0.35, end: 1.0).animate(_a), child: widget.child);
}
