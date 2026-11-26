// Lo que sigue, dentro del propio reproductor: el nombre de lo que suena, unas fichas para
// poner delante lo que apetece y las canciones, que se arrastran para reordenarlas. La misma
// cola que la hoja «Cola» (cola_hoja.dart).
import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/formato.dart';
import '../../reproduccion/reproductor.dart';
import '../comunes.dart';
import '../paginas/cola_hoja.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';

/// Qué se pone delante en lo que sigue. Nada se quita: lo demás queda detrás.
enum OrdenCola { todo, nuevas, conocidas, artista }

/// La ficha elegida y lo que hace falta para aplicarla.
class FichasCola extends StatefulWidget {
  const FichasCola({super.key, required this.r});
  final Reproductor r;

  @override
  State<FichasCola> createState() => _FichasColaState();
}

class _FichasColaState extends State<FichasCola> {
  OrdenCola _orden = OrdenCola.todo;
  Object? _de;

  String get _artista {
    final p = widget.r.actual;
    final arts = p?['artistas'];
    if (arts is List && arts.isNotEmpty && arts.first is Map) return '${(arts.first as Map)['nombre'] ?? ''}'.trim();
    return '${p?['artista'] ?? ''}'.split(',').first.trim();
  }

  Future<void> _poner(OrdenCola o) async {
    final s = Caudal.leer(context);
    final r = widget.r;
    if (o == OrdenCola.todo) {
      r.ordenarSiguientes(null);
      setState(() => _orden = o);
      return;
    }
    bool Function(Json) cual;
    if (o == OrdenCola.artista) {
      final a = _artista.toLowerCase();
      cual = (p) => '${p['artista'] ?? ''}'.toLowerCase().contains(a);
    } else {
      final ya = await s.coleccion.clavesConocidas();
      if (!mounted) return;
      cual = o == OrdenCola.conocidas ? (p) => ya.contains('${p['clave']}') : (p) => !ya.contains('${p['clave']}');
    }
    final n = r.ordenarSiguientes(cual);
    if (n == 0) return s.avisar('No hay canciones así en lo que sigue.');
    setState(() => _orden = o);
  }

  @override
  Widget build(BuildContext context) {
    // otra cola: las fichas empiezan de cero
    final de = widget.r.contexto;
    if (!identical(de, _de)) {
      _de = de;
      _orden = OrdenCola.todo;
    }
    final artista = _artista;
    return SizedBox(
      height: 50,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        children: [
          for (final (o, texto) in [
            (OrdenCola.todo, 'Todo'),
            (OrdenCola.nuevas, 'Nuevas para ti'),
            (OrdenCola.conocidas, 'Las que conoces'),
            if (artista.isNotEmpty) (OrdenCola.artista, 'De $artista'),
          ])
            Pildora(texto: texto, activa: _orden == o, alPulsar: () => _poner(o)),
        ],
      ),
    );
  }
}

/// Las piezas de la lista, para ponerlas debajo de los controles.
List<Widget> sliversAContinuacion(BuildContext context, Servicios s) {
  final r = s.reproductor;
  final siguientes = r.siguientesDeContexto;
  final hay = r.proximas.isNotEmpty || siguientes.isNotEmpty;
  return [
    if (siguientes.length > 2) SliverToBoxAdapter(child: FichasCola(r: r)),
    const SliverToBoxAdapter(child: SizedBox(height: 2)),
    if (!hay)
      const SliverToBoxAdapter(
        child: Padding(
          padding: EdgeInsets.fromLTRB(22, 4, 22, 20),
          child: Text('No hay nada detrás. Al terminar, Caudal sigue con canciones parecidas.', style: estiloSecundario),
        ),
      ),
    if (r.proximas.isNotEmpty) ...[
      const SliverToBoxAdapter(
        child: Padding(
          padding: EdgeInsets.fromLTRB(22, 4, 22, 2),
          child: Text('Puestas por ti', style: TextStyle(color: C.texto2, fontSize: 13, fontWeight: FontWeight.w700)),
        ),
      ),
      SliverReorderableList(
        itemCount: r.proximas.length,
        onReorderItem: r.moverProxima,
        onReorderStart: (_) => Haptico.firme(),
        itemBuilder: (_, i) {
          final p = r.proximas[i];
          return FilaCola(
            key: ValueKey('rp-$i-${p['clave']}'),
            indice: i,
            pista: p,
            alPulsar: () => r.saltarAProxima(i),
            alQuitar: () {
              r.quitarProxima(i);
              s.avisar('Quitada de la cola', deshacer: () => r.insertarProxima(i, p));
            },
            alAdelantar: () {
              if (i > 0) r.moverProxima(i, 0);
              s.avisar('Suena después de esta');
            },
          );
        },
      ),
      if (siguientes.isNotEmpty)
        const SliverToBoxAdapter(
          child: Padding(
            padding: EdgeInsets.fromLTRB(22, 12, 22, 2),
            child: Text('Después', style: TextStyle(color: C.texto2, fontSize: 13, fontWeight: FontWeight.w700)),
          ),
        ),
    ],
    SliverReorderableList(
      itemCount: siguientes.length,
      onReorderItem: (de, a) => r.moverEnSecuencia(r.pos + 1 + de, r.pos + 1 + a),
      onReorderStart: (_) => Haptico.firme(),
      itemBuilder: (_, i) {
        final p = siguientes[i];
        final absoluto = r.pos + 1 + i;
        return FilaCola(
          key: ValueKey('rs-$i-${p['clave']}'),
          indice: i,
          pista: p,
          alPulsar: () => r.saltarA(absoluto),
          alQuitar: () {
            r.quitarDeSecuencia(absoluto);
            s.avisar('Quitada de la cola', deshacer: () => r.insertarEnSecuencia(absoluto, p));
          },
          alAdelantar: () {
            r.tocarDespues(p);
            s.avisar('Suena después de esta');
          },
        );
      },
    ),
  ];
}

/// Una canción de lo que sigue: carátula, título, artista y duración, y el asa para moverla.
/// Deslizarla hacia la izquierda la quita y hacia la derecha la pone la siguiente; mantenerla pulsada abre su
/// menú. Cada fila se toca sin apuntar (68 de alto) y el asa mide 56.
class FilaCola extends StatelessWidget {
  const FilaCola({super.key, required this.indice, required this.pista, required this.alPulsar, required this.alQuitar,
      this.alAdelantar});
  final int indice;
  final Json pista;
  final VoidCallback alPulsar, alQuitar;

  /// Ponerla a continuación (deslizar a la derecha).
  final VoidCallback? alAdelantar;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final dur = (pista['duracion'] as num?)?.toInt() ?? 0;
    final detalle = [
      '${pista['artista'] ?? ''}'.trim(),
      if (dur > 0) formatoSegundos(dur),
    ].where((x) => x.isNotEmpty).join(' • ');
    return Material(
      type: MaterialType.transparency,
      child: Dismissible(
        key: ValueKey('dis-$key'),
        direction: alAdelantar == null ? DismissDirection.endToStart : DismissDirection.horizontal,
        dismissThresholds: const {DismissDirection.startToEnd: 0.28, DismissDirection.endToStart: 0.38},
        background: _Fondo(
            color: alAdelantar == null ? C.error : C.acento,
            tinta: alAdelantar == null ? Colors.white : C.acentoTexto,
            icono: alAdelantar == null ? Icons.delete_outline_rounded : Icons.playlist_play_rounded,
            texto: alAdelantar == null ? 'Quitar' : 'A continuación',
            izquierda: alAdelantar != null),
        secondaryBackground: alAdelantar == null
            ? null
            : const _Fondo(color: C.error, tinta: Colors.white, icono: Icons.delete_outline_rounded, texto: 'Quitar',
                izquierda: false),
        confirmDismiss: (d) async {
          if (d != DismissDirection.startToEnd) return true;
          Haptico.seleccion();
          alAdelantar?.call();
          return false; // no se va: solo cambia de sitio
        },
        onDismissed: (_) {
          Haptico.toque();
          alQuitar();
        },
        child: InkWell(
          onTap: alPulsar,
          onLongPress: () => s.hojaPista(context, pista),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 2, 8),
            child: Row(children: [
              Portada(url: '${pista['miniatura'] ?? ''}', lado: 52, radio: 4),
              const SizedBox(width: 16),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${pista['titulo'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis, style: estiloTituloFila),
                  const SizedBox(height: 3),
                  Row(children: [
                    if (pista['explicito'] == true) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                        decoration: BoxDecoration(color: C.texto2, borderRadius: BorderRadius.circular(2)),
                        child: Text('E', style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w900, color: C.panel)),
                      ),
                      const SizedBox(width: 7),
                    ],
                    Expanded(
                      child: Text(detalle, maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                    ),
                  ]),
                ]),
              ),
              ReorderableDragStartListener(
                index: indice,
                child: const SizedBox(
                  width: 56,
                  height: 56,
                  child: Icon(Icons.drag_handle_rounded, size: 28, color: C.texto2, semanticLabel: 'Arrastrar para reordenar'),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

/// Lo que se ve debajo de una fila al deslizarla.
class _Fondo extends StatelessWidget {
  const _Fondo({required this.color, required this.tinta, required this.icono, required this.texto, required this.izquierda});
  final Color color, tinta;
  final IconData icono;
  final String texto;
  final bool izquierda;

  @override
  Widget build(BuildContext context) => Container(
        color: color,
        alignment: izquierda ? Alignment.centerLeft : Alignment.centerRight,
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icono, color: tinta),
          const SizedBox(width: 8),
          Text(texto, style: TextStyle(color: tinta, fontWeight: FontWeight.w700)),
        ]),
      );
}

/// «A continuación» (con de dónde sale lo que suena) o «Letra», y lo de la cola a mano. Se recuerda.
class PestanasReproductor extends StatelessWidget {
  const PestanasReproductor({super.key, required this.letra, required this.alCambiar, this.detalle = ''});
  final bool letra;
  final ValueChanged<bool> alCambiar;

  /// El mix, la lista o el álbum que suena.
  final String detalle;

  @override
  Widget build(BuildContext context) {
    Widget una(String texto, bool valor, String debajo) {
      final activa = letra == valor;
      return Semantics(
        button: true,
        selected: activa,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () {
            if (activa) return;
            Haptico.seleccion();
            alCambiar(valor);
          },
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 50),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(texto, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 17, height: 1.15, letterSpacing: -0.2,
                          fontWeight: FontWeight.w800, color: activa ? C.texto : const Color(0x80FFFFFF))),
                  if (debajo.isNotEmpty)
                    Text(debajo, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12, height: 1.3, color: Color(activa ? 0xB3FFFFFF : 0x66FFFFFF))),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 4, 0),
      child: Row(children: [
        Expanded(
          child: Row(children: [
            Flexible(child: una('A continuación', false, detalle)),
            una('Letra', true, ''),
          ]),
        ),
        if (!letra) ...[
          IconButton(
            tooltip: 'Guardar como lista',
            icon: const Icon(Icons.playlist_add_rounded, size: 27),
            onPressed: () => HojaCola.guardarComoLista(context),
          ),
          IconButton(
            tooltip: 'Cola',
            icon: const Icon(Icons.queue_music_rounded, size: 25),
            onPressed: () => showModalBottomSheet<void>(
                context: context, isScrollControlled: true, builder: (_) => const HojaCola()),
          ),
        ],
      ]),
    );
  }
}
