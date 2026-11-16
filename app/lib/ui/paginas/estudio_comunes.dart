import 'dart:async';
import 'dart:math' show max, min;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../nucleo/estudio.dart';
import '../../nucleo/sonidos_ambiente.dart';
import '../tema.dart';

/// Los colores del Modo estudio: los de la app, o un modo oscuro cálido y de
/// bajo contraste (tinte ámbar) con brillo ajustable para la vista de enfoque.
class PaletaEstudio {
  const PaletaEstudio({
    required this.fondo,
    required this.superficie,
    required this.superficie2,
    required this.borde,
    required this.texto,
    required this.texto2,
    required this.texto3,
    required this.acento,
    required this.sobreAcento,
    this.calida = false,
  });

  final Color fondo;
  final Color superficie;
  final Color superficie2;
  final Color borde;
  final Color texto;
  final Color texto2;
  final Color texto3;
  final Color acento;
  final Color sobreAcento;
  final bool calida;

  /// Los colores de siempre de Caudal.
  factory PaletaEstudio.normal() => PaletaEstudio(
        fondo: C.fondo,
        superficie: C.superficie,
        superficie2: C.superficie2,
        borde: C.borde,
        texto: C.texto,
        texto2: C.texto2,
        texto3: C.texto3,
        acento: C.acento,
        sobreAcento: C.acentoTexto,
      );

  /// Ámbar suave sobre casi negro. [brillo] de 0 (muy tenue) a 1.
  factory PaletaEstudio.calida(double brillo) {
    const fondo = Color(0xFF140F0A);
    final k = 0.45 + 0.55 * brillo.clamp(0.0, 1.0);
    Color c(int v) => Color.lerp(fondo, Color(v), k)!;
    return PaletaEstudio(
      fondo: fondo,
      superficie: Color.lerp(fondo, const Color(0xFF2A2017), 0.35 + 0.65 * k)!,
      superficie2: Color.lerp(fondo, const Color(0xFF362A1E), 0.35 + 0.65 * k)!,
      borde: Color.lerp(fondo, const Color(0xFF4A3A28), 0.3 + 0.7 * k)!,
      texto: c(0xFFEFDDBF),
      texto2: c(0xFFBCA787),
      texto3: c(0xFF8A7A62),
      acento: c(0xFFE9A85A),
      sobreAcento: const Color(0xFF241405),
      calida: true,
    );
  }

  Color suave(Color c, [double alfa = 0.14]) => c.withValues(alpha: alfa);
}

/// Los iconos del modo estudio, en un solo sitio.
class IconosEstudio {
  IconosEstudio._();

  static IconData perfil(String id) => switch (id) {
        'leer' => Icons.menu_book_rounded,
        'programar' => Icons.code_rounded,
        'repasar' => Icons.school_rounded,
        _ => Icons.spa_rounded,
      };

  static IconData capa(CapaAmbiente c) => switch (c) {
        CapaAmbiente.lluvia => Icons.water_drop_rounded,
        CapaAmbiente.cafeteria => Icons.local_cafe_rounded,
        CapaAmbiente.bosque => Icons.park_rounded,
        CapaAmbiente.chimenea => Icons.local_fire_department_rounded,
        CapaAmbiente.blanco => Icons.graphic_eq_rounded,
        CapaAmbiente.rosa => Icons.blur_on_rounded,
        CapaAmbiente.marron => Icons.waves_rounded,
      };
}

/// Una tarjeta redondeada y tranquila.
class PanelEstudio extends StatelessWidget {
  const PanelEstudio({super.key, required this.paleta, required this.child, this.padding, this.borde});
  final PaletaEstudio paleta;
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? borde;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: padding ?? const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: paleta.superficie,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: borde ?? paleta.borde),
        ),
        child: child,
      );
}

/// El tema de los deslizadores y interruptores del modo estudio.
SliderThemeData temaDeslizador(BuildContext context, PaletaEstudio p) => SliderTheme.of(context).copyWith(
      activeTrackColor: p.acento,
      inactiveTrackColor: p.borde,
      thumbColor: p.acento,
      overlayColor: p.acento.withValues(alpha: 0.12),
      trackHeight: 3,
      thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 7),
      overlayShape: const RoundSliderOverlayShape(overlayRadius: 18),
      disabledActiveTrackColor: p.texto3.withValues(alpha: 0.5),
      disabledInactiveTrackColor: p.borde,
      disabledThumbColor: p.texto3,
    );

Widget interruptorEstudio(PaletaEstudio p, bool valor, ValueChanged<bool>? alCambiar) => Switch(
      value: valor,
      onChanged: alCambiar,
      activeThumbColor: p.sobreAcento,
      activeTrackColor: p.acento,
      inactiveThumbColor: p.texto3,
      inactiveTrackColor: p.superficie2,
      trackOutlineColor: WidgetStateProperty.resolveWith((s) =>
          s.contains(WidgetState.selected) ? Colors.transparent : p.borde),
    );

/// Una línea con título, ayuda y un interruptor.
class FilaInterruptor extends StatelessWidget {
  const FilaInterruptor({
    super.key,
    required this.paleta,
    required this.titulo,
    required this.ayuda,
    required this.valor,
    required this.alCambiar,
    this.icono,
  });
  final PaletaEstudio paleta;
  final String titulo;
  final String ayuda;
  final bool valor;
  final ValueChanged<bool> alCambiar;
  final IconData? icono;

  @override
  Widget build(BuildContext context) => Semantics(
        toggled: valor,
        label: titulo,
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => alCambiar(!valor),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(children: [
              if (icono != null) ...[
                Icon(icono, size: 20, color: paleta.texto2),
                const SizedBox(width: 12),
              ],
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(titulo, style: TextStyle(color: paleta.texto, fontSize: 15, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 2),
                  Text(ayuda, style: TextStyle(color: paleta.texto3, fontSize: 12.5, height: 1.3)),
                ]),
              ),
              const SizedBox(width: 8),
              interruptorEstudio(paleta, valor, alCambiar),
            ]),
          ),
        ),
      );
}

/// Un botón que hay que mantener pulsado (2 s por defecto): es el candado
/// contra toques sueltos. [constructor] pinta el contenido con el avance (0 a 1).
class MantenerPulsado extends StatefulWidget {
  const MantenerPulsado({
    super.key,
    required this.alConfirmar,
    required this.constructor,
    this.duracion = const Duration(seconds: 2),
    this.etiquetaSemantica = 'Mantén pulsado para confirmar',
  });
  final VoidCallback alConfirmar;
  final Widget Function(BuildContext context, double avance) constructor;
  final Duration duracion;
  final String etiquetaSemantica;

  @override
  State<MantenerPulsado> createState() => _MantenerPulsadoState();
}

class _MantenerPulsadoState extends State<MantenerPulsado> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: widget.duracion)
    ..addStatusListener((s) {
      if (s == AnimationStatus.completed) {
        HapticFeedback.mediumImpact();
        widget.alConfirmar();
      }
    });

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  void _soltar() {
    if (_c.status != AnimationStatus.completed) _c.reverse();
  }

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: widget.etiquetaSemantica,
        onLongPress: widget.alConfirmar,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTapDown: (_) => _c.forward(),
          onTapUp: (_) => _soltar(),
          onTapCancel: _soltar,
          child: AnimatedBuilder(animation: _c, builder: (ctx, _) => widget.constructor(ctx, _c.value)),
        ),
      );
}

/// «¿Salir de tu sesión de estudio?». Devuelve true si de verdad sale.
Future<bool> confirmarSalidaEstudio(BuildContext context, Estudio estudio, PaletaEstudio p) async {
  final salir = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      backgroundColor: p.superficie,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26), side: BorderSide(color: p.borde)),
      title: Text('¿Salir de tu sesión de estudio?',
          style: TextStyle(color: p.texto, fontSize: 20, fontWeight: FontWeight.w800)),
      content: Text(
          estudio.candado
              ? 'Tu tiempo ya quedó guardado. Para salir, mantén pulsado el botón dos segundos.'
              : 'Tu tiempo ya quedó guardado. Si sales, el temporizador y los sonidos se detienen.',
          style: TextStyle(color: p.texto2, height: 1.4)),
      actionsPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      actionsOverflowButtonSpacing: 8,
      actions: [
        if (estudio.candado)
          MantenerPulsado(
            etiquetaSemantica: 'Mantén pulsado para salir',
            alConfirmar: () => Navigator.of(ctx).pop(true),
            constructor: (_, avance) => _PildoraAvance(
                texto: 'Mantén para salir', avance: avance, paleta: p, alto: 44),
          )
        else
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: TextButton.styleFrom(foregroundColor: p.texto2, minimumSize: const Size(0, 44)),
            child: const Text('Salir'),
          ),
        FilledButton(
          autofocus: true,
          onPressed: () => Navigator.of(ctx).pop(false),
          style: FilledButton.styleFrom(
              backgroundColor: p.acento,
              foregroundColor: p.sobreAcento,
              minimumSize: const Size(0, 44),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
          child: const Text('Seguir estudiando'),
        ),
      ],
    ),
  );
  return salir == true;
}

class _PildoraAvance extends StatelessWidget {
  const _PildoraAvance({required this.texto, required this.avance, required this.paleta, this.alto = 44});
  final String texto;
  final double avance;
  final PaletaEstudio paleta;
  final double alto;

  @override
  Widget build(BuildContext context) => Container(
        height: alto,
        constraints: const BoxConstraints(minWidth: 150),
        padding: const EdgeInsets.symmetric(horizontal: 18),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: paleta.borde),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: Stack(alignment: Alignment.center, children: [
            Positioned.fill(
              child: Align(
                alignment: Alignment.centerLeft,
                child: FractionallySizedBox(
                    widthFactor: avance.clamp(0.0, 1.0),
                    child: ColoredBox(color: paleta.acento.withValues(alpha: 0.28), child: const SizedBox.expand())),
              ),
            ),
            Text(texto, style: TextStyle(color: paleta.texto2, fontWeight: FontWeight.w600)),
          ]),
        ),
      );
}

/// Un número con menos y más (minutos, rondas...).
class PasoNumerico extends StatelessWidget {
  const PasoNumerico({
    super.key,
    required this.paleta,
    required this.titulo,
    required this.valor,
    required this.texto,
    required this.alCambiar,
    this.minimo = 1,
    this.maximo = 99,
    this.salto = 1,
  });
  final PaletaEstudio paleta;
  final String titulo;
  final int valor;
  final String texto;
  final ValueChanged<int> alCambiar;
  final int minimo;
  final int maximo;
  final int salto;

  @override
  Widget build(BuildContext context) {
    Widget boton(IconData i, String tip, bool activo, VoidCallback f) => IconButton(
          tooltip: tip,
          onPressed: activo ? f : null,
          icon: Icon(i, size: 20),
          color: paleta.texto,
          disabledColor: paleta.texto3.withValues(alpha: 0.4),
          style: IconButton.styleFrom(
              backgroundColor: paleta.superficie2, minimumSize: const Size(40, 40), padding: EdgeInsets.zero),
        );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Expanded(child: Text(titulo, style: TextStyle(color: paleta.texto2, fontSize: 14.5))),
        boton(Icons.remove_rounded, 'Menos', valor > minimo, () => alCambiar(max(minimo, valor - salto))),
        SizedBox(
          width: 84,
          child: Text(texto,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(color: paleta.texto, fontSize: 15, fontWeight: FontWeight.w700)),
        ),
        boton(Icons.add_rounded, 'Más', valor < maximo, () => alCambiar(min(maximo, valor + salto))),
      ]),
    );
  }
}

// =============================================================== el mezclador

/// Las capas de sonido con su volumen: música base, lluvia, cafetería...
class MezcladorEstudio extends StatelessWidget {
  const MezcladorEstudio({super.key, required this.estudio, required this.paleta, this.conTitulo = true});
  final Estudio estudio;
  final PaletaEstudio paleta;
  final bool conTitulo;

  @override
  Widget build(BuildContext context) {
    final musica = estudio.musica;
    return ListenableBuilder(
      listenable: Listenable.merge([estudio, estudio.ambiente, ?musica?.cambios]),
      builder: (context, _) {
        final p = paleta;
        final hay = estudio.ambiente.disponible;
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (conTitulo)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text('Mezclador de sonidos',
                  style: TextStyle(color: p.texto, fontSize: 18, fontWeight: FontWeight.w800)),
            ),
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Text('Cada capa tiene su propio volumen. Mezcla hasta que se sienta bien.',
                style: TextStyle(color: p.texto3, fontSize: 13, height: 1.35)),
          ),
          _FilaCapa(
            paleta: p,
            icono: Icons.music_note_rounded,
            nombre: 'Música base',
            ayuda: musica == null || !musica.hayMusica ? 'Empieza con la sesión' : musica.titulo,
            activa: true,
            valor: ((musica?.volumen ?? 100) / 100).clamp(0.0, 1.0),
            alAlternar: null,
            alCambiar: musica == null ? null : (v) => estudio.ponerVolumenBase(v * 100),
            etiquetaVolumen: 'Volumen de la música base',
          ),
          if (!hay)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: p.superficie2,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(children: [
                  Icon(Icons.info_outline_rounded, size: 20, color: p.texto3),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text('Los sonidos ambientales están en la app para Android y Windows.',
                        style: TextStyle(color: p.texto2, fontSize: 13.5, height: 1.35)),
                  ),
                ]),
              ),
            )
          else ...[
            for (final c in CapaAmbiente.values)
              _FilaCapa(
                paleta: p,
                icono: IconosEstudio.capa(c),
                nombre: c.nombre,
                ayuda: c.descripcion,
                activa: estudio.capaActiva[c] ?? false,
                preparando: estudio.ambiente.preparando(c),
                valor: estudio.capaVolumen[c] ?? 0.3,
                alAlternar: (v) => estudio.ponerCapa(c, v),
                alCambiar: (v) => estudio.ponerVolumenCapa(c, v),
                etiquetaVolumen: 'Volumen de ${c.nombre}',
              ),
            const SizedBox(height: 10),
            Wrap(spacing: 8, runSpacing: 8, children: [
              _Chip(paleta: p, icono: Icons.auto_awesome_rounded, texto: 'Mezcla de «${estudio.perfil.nombre}»',
                  alPulsar: estudio.aplicarMezclaDelPerfil),
              _Chip(paleta: p, icono: Icons.volume_off_rounded, texto: 'Sin ambiente', alPulsar: estudio.silenciarCapas),
            ]),
          ],
          const SizedBox(height: 8),
          Divider(color: p.borde, height: 24),
          FilaInterruptor(
            paleta: p,
            titulo: 'Atenuar la música base durante el enfoque',
            ayuda: 'Baja la música un 35 % mientras dura cada bloque de enfoque.',
            valor: estudio.atenuar,
            alCambiar: estudio.ponerAtenuar,
            icono: Icons.vertical_align_bottom_rounded,
          ),
        ]);
      },
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.paleta, required this.icono, required this.texto, required this.alPulsar});
  final PaletaEstudio paleta;
  final IconData icono;
  final String texto;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) => Material(
        color: paleta.superficie2,
        borderRadius: BorderRadius.circular(999),
        child: InkWell(
          borderRadius: BorderRadius.circular(999),
          onTap: alPulsar,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(icono, size: 16, color: paleta.acento),
              const SizedBox(width: 8),
              Flexible(
                child: Text(texto,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: paleta.texto, fontSize: 13, fontWeight: FontWeight.w600)),
              ),
            ]),
          ),
        ),
      );
}

class _FilaCapa extends StatelessWidget {
  const _FilaCapa({
    required this.paleta,
    required this.icono,
    required this.nombre,
    required this.ayuda,
    required this.activa,
    required this.valor,
    required this.alAlternar,
    required this.alCambiar,
    required this.etiquetaVolumen,
    this.preparando = false,
  });
  final PaletaEstudio paleta;
  final IconData icono;
  final String nombre;
  final String ayuda;
  final bool activa;
  final bool preparando;
  final double valor;
  final ValueChanged<bool>? alAlternar;
  final ValueChanged<double>? alCambiar;
  final String etiquetaVolumen;

  @override
  Widget build(BuildContext context) {
    final p = paleta;
    final color = activa ? p.acento : p.texto3;
    return AnimatedOpacity(
      duration: const Duration(milliseconds: 220),
      opacity: activa ? 1 : 0.62,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(children: [
          Semantics(
            button: alAlternar != null,
            toggled: alAlternar == null ? null : activa,
            label: alAlternar == null ? nombre : '$nombre: ${activa ? 'encendido' : 'apagado'}',
            child: GestureDetector(
              onTap: alAlternar == null ? null : () => alAlternar!(!activa),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 220),
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: activa ? p.acento.withValues(alpha: 0.16) : p.superficie2,
                  border: Border.all(color: activa ? p.acento.withValues(alpha: 0.55) : Colors.transparent),
                ),
                child: preparando
                    ? Padding(
                        padding: const EdgeInsets.all(13),
                        child: CircularProgressIndicator(strokeWidth: 2, color: p.acento))
                    : Icon(icono, size: 21, color: color),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(nombre,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: p.texto, fontSize: 14.5, fontWeight: FontWeight.w700)),
              SliderTheme(
                data: temaDeslizador(context, p),
                child: SizedBox(
                  height: 28,
                  child: Slider(
                    value: valor.clamp(0.0, 1.0),
                    onChanged: alCambiar,
                    semanticFormatterCallback: (v) => '${(v * 100).round()} %',
                    label: etiquetaVolumen,
                  ),
                ),
              ),
            ]),
          ),
        ]),
      ),
    );
  }
}

// =============================================================== las notas

/// «Captura de ideas»: un bloc ligero en una hoja inferior.
class HojaNotas extends StatefulWidget {
  const HojaNotas({super.key, required this.estudio, required this.paleta});
  final Estudio estudio;
  final PaletaEstudio paleta;

  static Future<void> mostrar(BuildContext context, Estudio estudio, PaletaEstudio paleta) =>
      showModalBottomSheet<void>(
        context: context,
        useRootNavigator: true,
        isScrollControlled: true,
        backgroundColor: paleta.fondo,
        barrierColor: Colors.black54,
        showDragHandle: true,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
        constraints: const BoxConstraints(maxWidth: 640),
        builder: (_) => HojaNotas(estudio: estudio, paleta: paleta),
      );

  @override
  State<HojaNotas> createState() => _HojaNotasState();
}

class _HojaNotasState extends State<HojaNotas> {
  final _texto = TextEditingController();
  final _foco = FocusNode();
  int? _copiada;
  Timer? _t;

  @override
  void dispose() {
    _t?.cancel();
    _texto.dispose();
    _foco.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    final t = _texto.text;
    if (t.trim().isEmpty) return;
    _texto.clear();
    await widget.estudio.guardarNota(t);
    if (mounted) _foco.requestFocus();
  }

  Future<void> _copiar(NotaEstudio n) async {
    await Clipboard.setData(ClipboardData(text: n.texto));
    if (!mounted) return;
    setState(() => _copiada = n.id);
    _t?.cancel();
    _t = Timer(const Duration(milliseconds: 1400), () {
      if (mounted) setState(() => _copiada = null);
    });
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.paleta;
    final e = widget.estudio;
    final teclado = MediaQuery.viewInsetsOf(context).bottom;
    final alto = MediaQuery.sizeOf(context).height;
    return AnimatedPadding(
      duration: const Duration(milliseconds: 150),
      padding: EdgeInsets.only(bottom: teclado),
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: alto * 0.82),
        child: ListenableBuilder(
          listenable: e,
          builder: (context, _) {
            final lista = e.notas.lista;
            return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
                child: Row(children: [
                  Icon(Icons.lightbulb_outline_rounded, color: p.acento, size: 22),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text('Captura de ideas',
                        style: TextStyle(color: p.texto, fontSize: 20, fontWeight: FontWeight.w800)),
                  ),
                ]),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: TextField(
                  controller: _texto,
                  focusNode: _foco,
                  minLines: 2,
                  maxLines: 4,
                  maxLength: 600,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: p.texto, height: 1.35),
                  cursorColor: p.acento,
                  decoration: InputDecoration(
                    hintText: 'Anota la idea y vuelve a lo tuyo…',
                    hintStyle: TextStyle(color: p.texto3),
                    counterStyle: TextStyle(color: p.texto3),
                    filled: true,
                    fillColor: p.superficie,
                    contentPadding: const EdgeInsets.all(14),
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: p.borde)),
                    enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: p.borde)),
                    focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                        borderSide: BorderSide(color: p.acento.withValues(alpha: 0.7))),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 4, 20, 8),
                child: Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton.icon(
                    onPressed: _guardar,
                    icon: const Icon(Icons.check_rounded, size: 18),
                    label: const Text('Guardar nota'),
                    style: FilledButton.styleFrom(
                        backgroundColor: p.acento,
                        foregroundColor: p.sobreAcento,
                        minimumSize: const Size(0, 44),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                  ),
                ),
              ),
              Flexible(
                child: lista.isEmpty
                    ? Padding(
                        padding: const EdgeInsets.fromLTRB(28, 8, 28, 28),
                        child: Column(mainAxisSize: MainAxisSize.min, children: [
                          Icon(Icons.edit_note_rounded, size: 40, color: p.texto3),
                          const SizedBox(height: 8),
                          Text('Aquí aparecerán tus ideas. Anótalas sin pensarlo mucho y sigue con lo que estabas haciendo.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: p.texto3, height: 1.4)),
                        ]),
                      )
                    : ListView.separated(
                        shrinkWrap: true,
                        padding: EdgeInsets.fromLTRB(20, 4, 20, 20 + MediaQuery.paddingOf(context).bottom),
                        itemCount: lista.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 10),
                        itemBuilder: (_, i) {
                          final n = lista[i];
                          return Container(
                            padding: const EdgeInsets.fromLTRB(16, 12, 6, 8),
                            decoration: BoxDecoration(
                              color: p.superficie,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: p.borde),
                            ),
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Padding(
                                padding: const EdgeInsets.only(right: 10),
                                child: Text(n.texto, style: TextStyle(color: p.texto, height: 1.4, fontSize: 14.5)),
                              ),
                              const SizedBox(height: 4),
                              Row(children: [
                                Expanded(
                                  child: Text(NotasEstudio.fechaCorta(n.fecha, e.ahora),
                                      style: TextStyle(color: p.texto3, fontSize: 12)),
                                ),
                                IconButton(
                                  tooltip: 'Copiar',
                                  visualDensity: VisualDensity.compact,
                                  onPressed: () => _copiar(n),
                                  icon: Icon(_copiada == n.id ? Icons.check_rounded : Icons.copy_rounded,
                                      size: 19, color: _copiada == n.id ? p.acento : p.texto2),
                                ),
                                IconButton(
                                  tooltip: 'Borrar',
                                  visualDensity: VisualDensity.compact,
                                  onPressed: () => e.borrarNota(n.id),
                                  icon: Icon(Icons.delete_outline_rounded, size: 19, color: p.texto2),
                                ),
                              ]),
                            ]),
                          );
                        },
                      ),
              ),
            ]);
          },
        ),
      ),
    );
  }
}

/// La hoja del mezclador, para abrirla desde la vista de enfoque.
Future<void> mostrarMezclador(BuildContext context, Estudio estudio, PaletaEstudio p) =>
    showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      backgroundColor: p.fondo,
      showDragHandle: true,
      constraints: const BoxConstraints(maxWidth: 640),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
      builder: (ctx) => ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * 0.86),
        child: SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(20, 0, 20, 20 + MediaQuery.paddingOf(ctx).bottom),
          child: MezcladorEstudio(estudio: estudio, paleta: p),
        ),
      ),
    );
