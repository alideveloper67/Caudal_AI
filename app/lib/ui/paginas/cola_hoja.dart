// La cola («A continuación»): reordenar arrastrando, quitar deslizando,
// «Guardar la cola como lista» y, en el menú de cada canción, «Tocar después
// de esta». La lógica vive en reproduccion/cola_ops.dart.
import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';
import '../../reproduccion/cola_ops.dart';
import '../comunes.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';

class HojaCola extends StatelessWidget {
  const HojaCola({super.key});

  /// Pregunta el nombre y guarda lo que suena y lo que viene como lista.
  static Future<void> guardarComoLista(BuildContext context) async {
    final s = Caudal.of(context);
    final r = s.reproductor;
    final pistas = pistasDeLaCola(r.actual, r.proximas, r.siguientesDeContexto);
    if (pistas.isEmpty) return s.avisar('La cola está vacía.');
    final nombre = await showDialog<String>(
      context: context,
      builder: (_) => _PedirNombre(inicial: '${r.contexto?['titulo'] ?? 'Mi cola'}'),
    );
    if (nombre == null) return;
    try {
      final (usado, n) = await guardarColaComoLista(s.coleccion, pistas, nombre);
      s.avisar('Cola guardada como «$usado» ($n ${n == 1 ? 'canción' : 'canciones'})');
    } catch (e) {
      s.avisar('No se pudo guardar la cola.');
    }
  }

  @override
  Widget build(BuildContext context) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.75,
        maxChildSize: 0.95,
        builder: (_, scroll) => ColaLista(scroll: scroll),
      );
}

/// Lo que suena y lo que viene: en la hoja del teléfono y en el panel de la web.
class ColaLista extends StatelessWidget {
  const ColaLista({super.key, this.scroll});
  final ScrollController? scroll;

  Widget _movible({
    required Key key,
    required int indice,
    required Json pista,
    required VoidCallback alPulsar,
    required VoidCallback alQuitar,
  }) =>
      // con su propio Material: al arrastrar, la fila vuela en el Overlay del
      // Navigator, fuera del Material de la hoja, y el InkWell fallaria
      Material(
        key: key,
        type: MaterialType.transparency,
        child: Row(children: [
        Expanded(
          child: Dismissible(
            key: ValueKey('dis-${key.toString()}'),
            direction: DismissDirection.endToStart,
            background: Container(color: C.error, alignment: Alignment.centerRight,
                padding: const EdgeInsets.only(right: 20), child: const Icon(Icons.delete_outline_rounded)),
            onDismissed: (_) {
              Haptico.toque();
              alQuitar();
            },
            child: FilaPista(pista: pista, alPulsar: alPulsar),
          ),
        ),
        ReorderableDragStartListener(
          index: indice,
          child: const Padding(
            padding: EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            child: Icon(Icons.drag_handle_rounded, color: C.texto2, semanticLabel: 'Arrastrar para reordenar'),
          ),
        ),
      ])); 

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final r = s.reproductor;
    return ListenableBuilder(
        listenable: r,
        builder: (context, _) {
          final siguientes = r.siguientesDeContexto;
          final normales = [for (var i = 0; i < siguientes.length; i++) if (siguientes[i]['_auto'] != true) i];
          final auto = [for (var i = 0; i < siguientes.length; i++) if (siguientes[i]['_auto'] == true) i];
          return CustomScrollView(controller: scroll, slivers: [
            SliverToBoxAdapter(child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 8, 4),
              child: Row(children: [
                const Expanded(child: Text('Sonando ahora', style: estiloTituloSeccion)),
                TextButton.icon(
                  key: const ValueKey('guardar-cola'),
                  onPressed: () => HojaCola.guardarComoLista(context),
                  icon: const Icon(Icons.playlist_add_rounded, size: 20),
                  label: const Text('Guardar como lista'),
                ),
              ]),
            )),
            if (r.actual != null)
              SliverToBoxAdapter(child: FilaPista(pista: r.actual!, alPulsar: r.alternar)),
            if (r.proximas.isNotEmpty) ...[
              SliverToBoxAdapter(child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 14, 8, 4),
                child: Row(children: [
                  const Expanded(child: Text('Siguiente en tu cola', style: estiloTituloSeccion)),
                  TextButton(onPressed: r.vaciarProximas, child: const Text('Vaciar', style: TextStyle(color: C.texto2))),
                ]),
              )),
              SliverReorderableList(
                itemCount: r.proximas.length,
                onReorderItem: r.moverProxima,
                onReorderStart: (_) => Haptico.firme(),
                itemBuilder: (_, i) {
                  final p = r.proximas[i];
                  return _movible(
                    key: ValueKey('prox-$i-${p['clave']}'),
                    indice: i,
                    pista: p,
                    alPulsar: () => r.saltarAProxima(i),
                    alQuitar: () {
                      r.quitarProxima(i);
                      s.avisar('Quitada de la cola', deshacer: () => r.insertarProxima(i, p));
                    },
                  );
                },
              ),
            ],
            if (normales.isNotEmpty) ...[
              SliverToBoxAdapter(child: Padding(padding: const EdgeInsets.fromLTRB(20, 14, 20, 4),
                  child: Text('Siguiente de: ${r.contexto?['titulo'] ?? 'la cola'}', style: estiloTituloSeccion,
                      maxLines: 2))),
              SliverReorderableList(
                itemCount: normales.length,
                onReorderItem: (de, a) => r.moverEnSecuencia(r.pos + 1 + normales[de], r.pos + 1 + normales[a]),
                onReorderStart: (_) => Haptico.firme(),
                itemBuilder: (_, k) {
                  final i = normales[k];
                  final p = siguientes[i];
                  final absoluto = r.pos + 1 + i;
                  return _movible(
                    key: ValueKey('ctx-$k-${p['clave']}'),
                    indice: k,
                    pista: p,
                    alPulsar: () => r.saltarA(absoluto),
                    alQuitar: () {
                      r.quitarDeSecuencia(absoluto);
                      s.avisar('Quitada de la cola', deshacer: () => r.insertarEnSecuencia(absoluto, p));
                    },
                  );
                },
              ),
            ],
            if (auto.isNotEmpty) ...[
              const SliverToBoxAdapter(child: Padding(padding: EdgeInsets.fromLTRB(20, 14, 20, 0),
                  child: Text('Reproducción automática', style: estiloTituloSeccion))),
              const SliverToBoxAdapter(child: Padding(padding: EdgeInsets.fromLTRB(20, 2, 20, 6),
                  child: Text('Canciones parecidas para que la música no pare.', style: estiloSecundario))),
              SliverList.builder(itemCount: auto.length, itemBuilder: (_, k) {
                final i = auto[k];
                return FilaPista(pista: siguientes[i], alPulsar: () => r.saltarA(r.pos + 1 + i));
              }),
            ],
            // por encima del indicador de inicio del iPhone
            SliverToBoxAdapter(child: SizedBox(height: 30 + MediaQuery.paddingOf(context).bottom)),
          ]);
        },
    );
  }
}

class _PedirNombre extends StatefulWidget {
  const _PedirNombre({required this.inicial});
  final String inicial;

  @override
  State<_PedirNombre> createState() => _PedirNombreState();
}

class _PedirNombreState extends State<_PedirNombre> {
  late final _c = TextEditingController(text: widget.inicial);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Guardar la cola como lista'),
        content: TextField(
          key: const ValueKey('nombre-cola'),
          controller: _c,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Nombre de la lista'),
          onSubmitted: (v) => Navigator.pop(context, v),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(context, _c.text), child: const Text('Guardar')),
        ],
      );
}
