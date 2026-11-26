import 'dart:math';

import 'package:flutter/material.dart';

import '../nucleo/coleccion.dart';
import '../reproduccion/reproductor.dart';
import 'comunes.dart';
import 'plataforma.dart';
import 'servicios.dart';
import 'tema.dart';

/// Lo que más usas, en carátulas cuadradas con el título encima, por páginas: tres por tres en
/// el teléfono y las que quepan en dos filas en pantallas anchas. La que suena lleva un borde.
class RejillaInicio extends StatefulWidget {
  const RejillaInicio({super.key, required this.elementos});
  final List<Json> elementos;

  static const espacio = 8.0;

  /// (columnas, filas) para ese ancho.
  static (int, int) forma(double ancho) {
    if (ancho < 560) return (3, 3);
    return ((ancho / 176).floor().clamp(4, 9), 2);
  }

  @override
  State<RejillaInicio> createState() => _RejillaInicioState();
}

class _RejillaInicioState extends State<RejillaInicio> {
  final _paginas = PageController();
  final _pagina = ValueNotifier<int>(0);

  @override
  void dispose() {
    _paginas.dispose();
    _pagina.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, medidas) {
        final ancho = medidas.maxWidth;
        final (columnas, filas) = RejillaInicio.forma(ancho);
        final porPagina = columnas * filas;
        const e = RejillaInicio.espacio;
        final lado = (ancho - Esp.lado * 2 - e * (columnas - 1)) / columnas;
        final n = widget.elementos.length;
        // como mucho tres páginas, y una última casi vacía no se enseña
        var paginas = min(3, (n / porPagina).ceil());
        if (paginas > 1 && n - (paginas - 1) * porPagina < columnas) paginas--;
        final filasVistas = paginas > 1 ? filas : min(filas, (n / columnas).ceil());
        if (_pagina.value >= paginas) WidgetsBinding.instance.addPostFrameCallback((_) => _pagina.value = 0);
        return Column(children: [
          SizedBox(
            height: lado * filasVistas + e * (filasVistas - 1),
            child: PageView.builder(
              key: const PageStorageKey('rejilla-inicio'),
              controller: _paginas,
              itemCount: paginas,
              onPageChanged: (i) => _pagina.value = i,
              itemBuilder: (_, pag) => Padding(
                padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
                child: Column(children: [
                  for (var f = 0; f < filasVistas; f++) ...[
                    if (f > 0) const SizedBox(height: e),
                    Row(children: [
                      for (var c = 0; c < columnas; c++) ...[
                        if (c > 0) const SizedBox(width: e),
                        if (pag * porPagina + f * columnas + c < n)
                          Entrada(
                            indice: pag == 0 ? f : 0,
                            desplazamiento: 10,
                            child: CeldaInicio(el: widget.elementos[pag * porPagina + f * columnas + c], lado: lado),
                          )
                        else
                          SizedBox(width: lado),
                      ],
                    ]),
                  ],
                ]),
              ),
            ),
          ),
          if (paginas > 1)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: ValueListenableBuilder<int>(
                valueListenable: _pagina,
                builder: (_, actual, _) => Semantics(
                  label: 'Página ${actual + 1} de $paginas',
                  child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                    for (var i = 0; i < paginas; i++)
                      GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTap: () => _paginas.animateToPage(i, duration: Mov.normal, curve: Mov.curva),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                          child: AnimatedContainer(
                            duration: Mov.normal,
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                                shape: BoxShape.circle, color: i == actual ? C.texto : const Color(0x55FFFFFF)),
                          ),
                        ),
                      ),
                  ]),
                ),
              ),
            ),
        ]);
      });
}

class CeldaInicio extends StatelessWidget {
  const CeldaInicio({super.key, required this.el, required this.lado});
  final Json el;
  final double lado;

  bool _suena(Reproductor r) {
    final a = r.actual;
    if (a == null) return false;
    if (el['tipo'] == 'pista') {
      return a['clave'] == el['clave'] || ('${el['video_id'] ?? ''}'.isNotEmpty && a['video_id'] == el['video_id']);
    }
    final c = r.contexto;
    return c != null && c['tipo'] == el['tipo'] && '${c['id']}' == '${el['id'] ?? el['tipo']}';
  }

  void _abrir(BuildContext context, Servicios s) {
    switch (el['tipo']) {
      case 'pista':
        if (_suena(s.reproductor)) {
          s.abrirReproductor(context);
        } else {
          s.reproducirPista(context, el);
        }
      case 'radio':
        s.reproductor.reproducirRadioId('${el['id']}', '${el['titulo']}');
      default:
        s.abrirElemento(context, el);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final titulo = '${el['titulo'] ?? ''}';
    return RepaintBoundary(
      child: Semantics(
        button: true,
        label: titulo,
        excludeSemantics: true,
        child: Pulsable(
          escala: 0.96,
          child: GestureDetector(
            onTap: () => _abrir(context, s),
            onLongPress: () {
              Haptico.firme();
              s.hojaElemento(context, el);
            },
            child: SizedBox.square(
              dimension: lado,
              child: ListenableBuilder(
                listenable: s.reproductor,
                builder: (_, hijo) {
                  final suena = _suena(s.reproductor);
                  return Stack(fit: StackFit.expand, children: [
                    hijo!,
                    if (suena) ...[
                      const IgnorePointer(
                        child: Center(
                          child: DecoratedBox(
                            decoration: BoxDecoration(color: Color(0x80000000), shape: BoxShape.circle),
                            child: Padding(
                              padding: EdgeInsets.all(6),
                              child: Icon(Icons.graphic_eq_rounded, color: Colors.white, size: 26),
                            ),
                          ),
                        ),
                      ),
                      IgnorePointer(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: Colors.white, width: 3),
                          ),
                        ),
                      ),
                    ],
                  ]);
                },
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: Stack(fit: StackFit.expand, children: [
                    el['tipo'] == 'me_gusta'
                        ? PortadaMeGusta(lado: lado, radio: 0)
                        : Portada(
                            url: '${el['miniatura'] ?? el['foto'] ?? ''}',
                            lado: lado,
                            radio: 0,
                            icono: switch (el['tipo']) {
                              'artista' => Icons.person_rounded,
                              'album' => Icons.album_rounded,
                              'lista' || 'mi_lista' => Icons.queue_music_rounded,
                              'radio' => Icons.radio_rounded,
                              _ => Icons.music_note_rounded,
                            }),
                    // el velo para que el título se lea sobre cualquier carátula
                    const DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [Color(0x00000000), Color(0x00000000), Color(0xD9000000)],
                          stops: [0, 0.52, 1],
                        ),
                      ),
                    ),
                    Align(
                      alignment: Alignment.bottomLeft,
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(10, 0, 8, 9),
                        child: Text(titulo,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontSize: 13.5, fontWeight: FontWeight.w700, color: Colors.white,
                                shadows: [Shadow(color: Color(0xB3000000), blurRadius: 4)])),
                      ),
                    ),
                  ]),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Lo de la rejilla: tus me gusta, lo último que abriste y lo que más escuchas, mezclado y sin
/// repetir (ni por clave ni por título con el mismo artista).
List<Json> elementosDeInicio(List<Json> atajos, List<Json> canciones, {int maximo = 27}) {
  final vistos = <String>{};
  bool nuevo(Json e) {
    final clave = '${e['tipo']}|${e['clave'] ?? e['id'] ?? ''}';
    final nombre = '${e['titulo']}|${e['artista'] ?? e['tipo']}'.toLowerCase();
    if (vistos.contains(clave) || vistos.contains(nombre)) return false;
    vistos
      ..add(clave)
      ..add(nombre);
    return true;
  }

  final a = [for (final e in atajos) if (nuevo(e)) e];
  final c = [for (final e in canciones) if (nuevo(e)) e];
  final salida = <Json>[];
  var ia = 0, ic = 0;
  // de cada tres, una es una lista, un álbum o un artista y dos son canciones
  while (salida.length < maximo && (ia < a.length || ic < c.length)) {
    final tocaAtajo = salida.length % 3 == 0;
    if ((tocaAtajo && ia < a.length) || ic >= c.length) {
      salida.add(a[ia++]);
    } else {
      salida.add(c[ic++]);
    }
  }
  return salida;
}
