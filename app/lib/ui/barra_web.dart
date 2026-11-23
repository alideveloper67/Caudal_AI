import 'package:flutter/material.dart';

import '../reproduccion/reproductor.dart';
import '../reproduccion/ventana_web.dart';
import 'atajos_teclado.dart';
import 'comunes.dart';
import 'paginas/cola_hoja.dart';
import 'paginas/karaoke_pagina.dart';
import 'paginas/sonido.dart';
import 'paginas/visualizador_pagina.dart';
import 'panel_web.dart';
import 'reproductor/barra_progreso.dart' show tiempo;
import 'servicios.dart';
import 'tema.dart';

/// La barra de reproducción de abajo, como la de Caudal Escritorio: lo que suena
/// a la izquierda, los controles en el centro y letra, cola, sonido y volumen a
/// la derecha. Solo en el navegador con la ventana ancha.
class BarraWeb extends StatelessWidget {
  const BarraWeb({super.key});

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final r = s.reproductor;
    return Container(
      height: 88,
      decoration: BoxDecoration(color: C.superficie, border: Border(top: BorderSide(color: C.borde))),
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: ListenableBuilder(
        listenable: Listenable.merge([r, s.coleccion, s.ajustes]),
        builder: (context, _) {
          final p = r.actual;
          return LayoutBuilder(builder: (context, c) {
            return Row(children: [
              Expanded(flex: 3, child: p == null ? const SizedBox.shrink() : _Suena(s: s)),
              Expanded(flex: 4, child: _Controles(r: r)),
              Expanded(flex: 3, child: _Derecha(s: s, ancho: c.maxWidth)),
            ]);
          });
        },
      ),
    );
  }
}

class _Suena extends StatelessWidget {
  const _Suena({required this.s});
  final Servicios s;

  @override
  Widget build(BuildContext context) {
    final p = s.reproductor.actual!;
    final gusta = s.coleccion.meGusta('${p['clave']}');
    return Row(children: [
      Tooltip(
        message: 'Abrir el reproductor',
        child: InkWell(
          onTap: () => s.abrirReproductor(context),
          borderRadius: BorderRadius.circular(8),
          child: Portada(url: '${p['miniatura'] ?? ''}', lado: 56, radio: 8),
        ),
      ),
      const SizedBox(width: 12),
      Flexible(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
            const SizedBox(height: 2),
            Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloDetalle),
          ],
        ),
      ),
      IconButton(
        tooltip: gusta ? 'Quitar de Tus me gusta' : 'Me gusta',
        iconSize: 20,
        icon: Icon(gusta ? Icons.favorite_rounded : Icons.favorite_border_rounded, color: gusta ? C.acento : C.texto2),
        onPressed: () => s.alternarMeGusta(p),
      ),
      IconButton(
        tooltip: 'Más',
        iconSize: 20,
        icon: const Icon(Icons.more_horiz_rounded, color: C.texto2),
        onPressed: () => s.hojaPista(context, p),
      ),
    ]);
  }
}

class _Controles extends StatelessWidget {
  const _Controles({required this.r});
  final Reproductor r;

  @override
  Widget build(BuildContext context) {
    final hay = r.actual != null;
    final sonando = r.estado == EstadoRepro.sonando;
    return Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        IconButton(
          tooltip: r.aleatorio ? 'Quitar aleatorio (S)' : 'Aleatorio (S)',
          iconSize: 19,
          visualDensity: VisualDensity.compact,
          icon: Icon(Icons.shuffle_rounded, color: r.aleatorio ? C.acento : C.texto2),
          onPressed: hay ? r.alternarAleatorio : null,
        ),
        IconButton(
          tooltip: 'Anterior (Ctrl + ←)',
          visualDensity: VisualDensity.compact,
          icon: const Icon(Icons.skip_previous_rounded),
          onPressed: hay ? r.anterior : null,
        ),
        IconButton.filled(
          tooltip: sonando ? 'Pausar (Espacio)' : 'Reproducir (Espacio)',
          style: IconButton.styleFrom(backgroundColor: C.texto, foregroundColor: C.fondo,
              fixedSize: const Size(38, 38), minimumSize: const Size(38, 38), padding: EdgeInsets.zero),
          icon: r.estado == EstadoRepro.cargando
              ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.4, color: C.fondo))
              : Icon(sonando ? Icons.pause_rounded : Icons.play_arrow_rounded),
          onPressed: hay ? r.alternar : null,
        ),
        IconButton(
          tooltip: 'Siguiente (Ctrl + →)',
          visualDensity: VisualDensity.compact,
          icon: const Icon(Icons.skip_next_rounded),
          onPressed: hay ? () => r.siguiente() : null,
        ),
        IconButton(
          tooltip: switch (r.repetir) {
            'todo' => 'Repitiendo todo (R)',
            'una' => 'Repitiendo esta (R)',
            _ => 'Repetir (R)',
          },
          iconSize: 19,
          visualDensity: VisualDensity.compact,
          icon: Icon(r.repetir == 'una' ? Icons.repeat_one_rounded : Icons.repeat_rounded,
              color: r.repetir == 'no' ? C.texto2 : C.acento),
          onPressed: hay ? r.ciclarRepetir : null,
        ),
      ]),
      _Progreso(r: r),
    ]);
  }
}

class _Progreso extends StatefulWidget {
  const _Progreso({required this.r});
  final Reproductor r;

  @override
  State<_Progreso> createState() => _ProgresoState();
}

class _ProgresoState extends State<_Progreso> {
  /// Donde está el ratón mientras se arrastra (null: manda la música).
  double? _arrastre;

  @override
  Widget build(BuildContext context) {
    final r = widget.r;
    return ListenableBuilder(
      listenable: Listenable.merge([r.posicion, r.duracion]),
      builder: (context, _) {
        final total = r.duracion.value.inMilliseconds.toDouble();
        final ahora = (_arrastre ?? r.posicion.value.inMilliseconds.toDouble()).clamp(0.0, total > 0 ? total : 1.0);
        const cifra = TextStyle(fontSize: 11, color: C.texto3, fontFeatures: [FontFeature.tabularFigures()]);
        return Row(children: [
          SizedBox(width: 44, child: Text(tiempo(Duration(milliseconds: ahora.round())), textAlign: TextAlign.right, style: cifra)),
          Expanded(
            child: SizedBox(
              height: 22,
              child: SliderTheme(
                data: SliderTheme.of(context).copyWith(
                  trackHeight: 4,
                  thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                  overlayShape: const RoundSliderOverlayShape(overlayRadius: 12),
                ),
                child: ExcludeFocus(
                  child: Slider(
                    max: total > 0 ? total : 1,
                    value: ahora,
                    onChanged: total <= 0 ? null : (v) => setState(() => _arrastre = v),
                    onChangeEnd: (v) {
                      setState(() => _arrastre = null);
                      r.buscar(Duration(milliseconds: v.round()));
                    },
                  ),
                ),
              ),
            ),
          ),
          SizedBox(width: 44, child: Text(tiempo(r.duracion.value), style: cifra)),
        ]);
      },
    );
  }
}

class _Derecha extends StatefulWidget {
  const _Derecha({required this.s, required this.ancho});
  final Servicios s;
  final double ancho;

  @override
  State<_Derecha> createState() => _DerechaState();
}

class _DerechaState extends State<_Derecha> {
  double _antes = 100;

  @override
  Widget build(BuildContext context) {
    final s = widget.s;
    final r = s.reproductor;
    final p = r.actual;
    final a = widget.ancho;
    final conPanel = MediaQuery.sizeOf(context).width >= PanelWeb.anchoMinimo;
    final panel = conPanel ? PanelWeb.abierto(s) : '';
    Widget boton(String texto, IconData icono, VoidCallback? alPulsar, {bool puesto = false}) => IconButton(
          tooltip: texto,
          iconSize: 20,
          visualDensity: VisualDensity.compact,
          icon: Icon(icono, color: alPulsar == null ? C.texto3 : (puesto ? C.acento : C.texto2)),
          onPressed: alPulsar,
        );
    return Row(mainAxisAlignment: MainAxisAlignment.end, children: [
      if (conPanel)
        boton('Sonando (N)', Icons.art_track_rounded, () => PanelWeb.alternar(s, 'sonando'), puesto: panel == 'sonando'),
      if (a >= 1450)
        boton('Karaoke', Icons.mic_external_on_rounded, p == null ? null : () => KaraokePagina.abrir(context, p)),
      if (conPanel) ...[
        boton('Letra (L)', Icons.lyrics_outlined, () => PanelWeb.alternar(s, 'letras'), puesto: panel == 'letras'),
        boton('Cola (Q)', Icons.queue_music_rounded, () => PanelWeb.alternar(s, 'cola'), puesto: panel == 'cola'),
      ] else ...[
        boton('Letra', Icons.lyrics_outlined, p == null ? null : () => s.abrirReproductor(context)),
        boton('Cola', Icons.queue_music_rounded, () => showModalBottomSheet<void>(
              context: context,
              useRootNavigator: true,
              isScrollControlled: true,
              builder: (_) => const HojaCola(),
            )),
      ],
      if (a >= 1250)
        boton('Visualizador (V)', Icons.blur_on_rounded, p == null ? null : () => VisualizadorPagina.abrir(context)),
      if (a >= 1250 && VentanaWeb.puedeMini)
        ValueListenableBuilder<bool>(
          valueListenable: VentanaWeb.miniAbierto,
          builder: (_, si, _) => boton('Mini reproductor (I)', Icons.picture_in_picture_alt_rounded,
              p == null && !si ? null : () => abrirMini(s), puesto: si),
        ),
      if (a >= 1080) boton('Sonido', Icons.graphic_eq_rounded, () => mostrarSonido(context)),
      boton(r.volumen > 0 ? 'Silenciar (M)' : 'Quitar el silencio (M)',
          r.volumen <= 0
              ? Icons.volume_off_rounded
              : r.volumen < 50
                  ? Icons.volume_down_rounded
                  : Icons.volume_up_rounded, () {
        if (r.volumen > 0) {
          _antes = r.volumen;
          r.fijarVolumen(0);
        } else {
          r.fijarVolumen(_antes);
        }
      }),
      SizedBox(
        width: a >= 1450 ? 100 : 76,
        child: SliderTheme(
          data: SliderTheme.of(context).copyWith(
            trackHeight: 4,
            thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
            overlayShape: const RoundSliderOverlayShape(overlayRadius: 12),
          ),
          child: ExcludeFocus(
            child: Slider(
              max: 100,
              value: r.volumen.clamp(0, 100),
              onChanged: r.fijarVolumen,
              onChangeEnd: (v) => s.ajustes.poner('volumen', v.round()),
            ),
          ),
        ),
      ),
    ]);
  }
}
