// El menú de la app: una hoja que sale de abajo con la carátula y el nombre, lo que más se usa en
// botones grandes y lo demás en filas cómodas, agrupadas. Lo usan todos los «⋮» y las pulsaciones
// largas de canciones, álbumes, listas, artistas y mixes.
import 'package:flutter/material.dart';

import '../nucleo/coleccion.dart';
import 'comunes.dart';
import 'plataforma.dart';
import 'tema.dart';

/// Un botón grande de los de arriba.
class AccionRapida {
  const AccionRapida(this.icono, this.texto, this.alPulsar, {this.activa = false, this.etiqueta});
  final IconData icono;

  /// Corto: cabe debajo del icono.
  final String texto;
  final VoidCallback alPulsar;
  final bool activa;

  /// Lo que se lee en voz alta (si el texto corto no lo explica).
  final String? etiqueta;
}

/// Una fila del menú.
class OpcionMenu {
  const OpcionMenu(this.icono, this.texto, this.alPulsar, {this.detalle = '', this.color, this.peligro = false});
  final IconData icono;
  final String texto;
  final VoidCallback alPulsar;
  final String detalle;
  final Color? color;
  final bool peligro;
}

/// Lo mínimo que mide una fila: se toca sin apuntar.
const double altoOpcionMenu = 54;

/// Abre el menú. Las opciones cierran la hoja antes de hacer lo suyo. [extra] son filas ya hechas (cierran
/// ellas la hoja).
Future<void> mostrarMenuHoja(
  BuildContext context, {
  required Widget portada,
  required String titulo,
  String subtitulo = '',
  VoidCallback? alCabecera,
  List<AccionRapida> rapidas = const [],
  List<List<OpcionMenu>> grupos = const [],
  List<Widget> extra = const [],
}) {
  Haptico.toque();
  final conAlgo = [for (final g in grupos) if (g.isNotEmpty) g];
  final filas = conAlgo.fold(extra.length, (n, g) => n + g.length);
  final escala = MediaQuery.textScalerOf(context).scale(1);
  final alto = 34 + 76 + (rapidas.isEmpty ? 0 : 92 * escala) + filas * altoOpcionMenu * (escala > 1 ? escala : 1) +
      (conAlgo.length + (extra.isEmpty ? 0 : 1)) * 10 + 22 + MediaQuery.viewPaddingOf(context).bottom;
  final pantalla = MediaQuery.sizeOf(context).height;
  final inicial = (alto / pantalla).clamp(0.25, 0.86);
  return showModalBottomSheet<void>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    constraints: const BoxConstraints(maxWidth: 560),
    builder: (ctx) => DraggableScrollableSheet(
      expand: false,
      initialChildSize: inicial,
      minChildSize: inicial * 0.5,
      maxChildSize: alto / pantalla > 0.86 ? 0.94 : inicial,
      builder: (_, scroll) => _Menu(
        scroll: scroll,
        portada: portada,
        titulo: titulo,
        subtitulo: subtitulo,
        alCabecera: alCabecera,
        rapidas: rapidas,
        grupos: conAlgo,
        extra: extra,
      ),
    ),
  );
}

class _Menu extends StatelessWidget {
  const _Menu({
    required this.scroll,
    required this.portada,
    required this.titulo,
    required this.subtitulo,
    required this.alCabecera,
    required this.rapidas,
    required this.grupos,
    required this.extra,
  });

  final ScrollController scroll;
  final Widget portada;
  final String titulo, subtitulo;
  final VoidCallback? alCabecera;
  final List<AccionRapida> rapidas;
  final List<List<OpcionMenu>> grupos;
  final List<Widget> extra;

  @override
  Widget build(BuildContext context) {
    void hacer(VoidCallback f) {
      Haptico.seleccion();
      Navigator.pop(context);
      f();
    }

    Widget caja(List<Widget> hijos) => Padding(
          padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
          child: Material(
            color: Color.lerp(C.superficie2, Colors.white, 0.045),
            borderRadius: BorderRadius.circular(16),
            clipBehavior: Clip.antiAlias,
            child: Column(children: hijos),
          ),
        );

    return ListView(
      controller: scroll,
      padding: EdgeInsets.only(bottom: 8 + MediaQuery.viewPaddingOf(context).bottom),
      children: [
        InkWell(
          onTap: alCabecera == null ? null : () => hacer(alCabecera!),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 14, 14),
            child: Row(children: [
              portada,
              const SizedBox(width: 14),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(titulo, maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, height: 1.2, letterSpacing: -0.2)),
                  if (subtitulo.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(subtitulo, maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                  ],
                ]),
              ),
              if (alCabecera != null) const Icon(Icons.chevron_right_rounded, color: C.texto3),
            ]),
          ),
        ),
        if (rapidas.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 12),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              for (final r in rapidas) Expanded(child: _Rapida(r, () => hacer(r.alPulsar))),
            ]),
          ),
        for (final g in grupos)
          caja([
            for (final (i, o) in g.indexed) ...[
              if (i > 0) Divider(height: 1, thickness: 0.6, indent: 54, color: C.texto3.withValues(alpha: 0.18)),
              InkWell(
                onTap: () => hacer(o.alPulsar),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: altoOpcionMenu),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                    child: Row(children: [
                      Icon(o.icono, size: 23, color: o.peligro ? C.error : o.color ?? C.texto2),
                      const SizedBox(width: 15),
                      Expanded(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(o.texto, maxLines: 2, overflow: TextOverflow.ellipsis,
                                style: TextStyle(fontSize: 15.5, fontWeight: FontWeight.w600, height: 1.2,
                                    color: o.peligro ? C.error : C.texto)),
                            if (o.detalle.isNotEmpty)
                              Padding(padding: const EdgeInsets.only(top: 2), child: Text(o.detalle, style: estiloSecundario)),
                          ],
                        ),
                      ),
                    ]),
                  ),
                ),
              ),
            ],
          ]),
        if (extra.isNotEmpty) caja(extra),
      ],
    );
  }
}

class _Rapida extends StatelessWidget {
  const _Rapida(this.r, this.alPulsar);
  final AccionRapida r;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        selected: r.activa,
        label: r.etiqueta ?? r.texto,
        excludeSemantics: true,
        child: Pulsable(
          escala: 0.94,
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: alPulsar,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: r.activa ? C.acento : Color.lerp(C.superficie2, Colors.white, 0.1),
                  ),
                  child: Icon(r.icono, size: 24, color: r.activa ? C.acentoTexto : C.texto),
                ),
                const SizedBox(height: 7),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(r.texto, maxLines: 1,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: C.texto2)),
                ),
              ]),
            ),
          ),
        ),
      );
}

/// La carátula de [el] para la cabecera del menú.
Widget portadaDeMenu(Json el) {
  final tipo = el['tipo'];
  if (tipo == 'me_gusta') return const PortadaMeGusta(lado: 60, radio: 8);
  final mosaico = el['mosaico'] is List ? el['mosaico'] as List : const [];
  return Portada(
    url: '${mosaico.isNotEmpty ? mosaico.first : el['miniatura'] ?? el['foto'] ?? ''}',
    lado: 60,
    radio: 8,
    circulo: tipo == 'artista',
    icono: switch (tipo) {
      'artista' => Icons.person_rounded,
      'album' => Icons.album_rounded,
      'lista' || 'mi_lista' || 'descargados' || 'mix' => Icons.queue_music_rounded,
      'radio' => Icons.radio_rounded,
      _ => Icons.music_note_rounded,
    },
  );
}
