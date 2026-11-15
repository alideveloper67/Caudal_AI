import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/mezcla_dj.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'inicio.dart' show espacioInferior;

/// La mesa del Mezclador: se arma un set con canciones de la cola, de Tus me
/// gusta o de tus listas, se ordena y, por cada paso, se ajusta cuando entra la
/// siguiente, cuanto dura el cambio y si cambian los graves. Se puede probar un
/// paso, reproducir el set entero y guardarlo con nombre.
///
/// Se abre con `Navigator.push(MaterialPageRoute(builder: (_) => const MezcladorPagina()))`
/// (o `s.abrirEnPestana?.call(const MezcladorPagina())`). [inicial] deja la mesa
/// con esas canciones ya puestas.
class MezcladorPagina extends StatefulWidget {
  const MezcladorPagina({super.key, this.inicial = const []});

  final List<Json> inicial;

  @override
  State<MezcladorPagina> createState() => _MezcladorPaginaState();
}

/// Un paso con un numero propio, para que al reordenar no se confundan.
class _Item {
  _Item(this.id, this.paso);
  final int id;
  PasoMezcla paso;
}

class _MezcladorPaginaState extends State<MezcladorPagina> {
  final List<_Item> _items = [];
  int _siguienteId = 1;
  int? _abierto; // el id del paso con el panel de ajustes abierto
  String _nombre = '';

  @override
  void initState() {
    super.initState();
    _poner(widget.inicial);
  }

  void _poner(List<Json> pistas) {
    for (final p in pistas) {
      _items.add(_Item(_siguienteId++, PasoMezcla(pista: p)));
    }
  }

  List<PasoMezcla> get _pasos => [for (final i in _items) i.paso];

  int _indiceDe(int id) => _items.indexWhere((i) => i.id == id);

  // ------------------------------------------------------------ acciones

  Future<void> _anadir() async {
    final elegidas = await showModalBottomSheet<List<Json>>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (_) => const _HojaElegir(),
    );
    if (elegidas == null || elegidas.isEmpty || !mounted) return;
    setState(() => _poner(elegidas));
  }

  void _quitar(_Item it) {
    final i = _indiceDe(it.id);
    if (i < 0) return;
    setState(() {
      _items.removeAt(i);
      if (_abierto == it.id) _abierto = null;
    });
    Caudal.leer(context).avisar('Quitada de la mezcla', deshacer: () {
      if (!mounted) return;
      setState(() => _items.insert(i.clamp(0, _items.length), it));
    });
  }

  void _igualarTodos(PasoMezcla modelo) {
    setState(() {
      for (final it in _items) {
        it.paso = it.paso.copiaCon(
            entraAntes: modelo.entraAntes, fundido: modelo.fundido, graves: modelo.graves);
      }
    });
    Caudal.leer(context).avisar('Todos los cambios quedaron igual');
  }

  Future<void> _probar(_Item it) async {
    final i = _indiceDe(it.id);
    final s = Caudal.leer(context);
    if (i < 0 || i + 1 >= _items.length) return;
    if (it.paso.duracionPista <= 0) {
      return s.avisar('No se sabe cuánto dura esa canción, así que no se puede probar el cambio.');
    }
    s.avisar('Probando el cambio…');
    await s.reproductor.probarPaso(it.paso, _items[i + 1].paso.pista);
  }

  Future<void> _reproducir() async {
    final s = Caudal.leer(context);
    if (_items.length < 2) return s.avisar('Añade al menos dos canciones para mezclar.');
    await s.reproductor.reproducirSet(_pasos, titulo: _nombre.isEmpty ? 'Tu mezcla' : _nombre);
  }

  Future<void> _guardar() async {
    final s = Caudal.leer(context);
    if (_items.length < 2) return s.avisar('Añade al menos dos canciones para guardar la mezcla.');
    final ahora = DateTime.now();
    final nombre = await pedirTexto(
        context, 'Nombre de la mezcla', _nombre.isEmpty ? 'Mi mezcla del ${ahora.day}/${ahora.month}' : _nombre);
    if (nombre == null || !mounted) return;
    try {
      await Mezclas.guardar(s.coleccion, nombre, _pasos);
      if (!mounted) return;
      setState(() => _nombre = nombre);
      s.avisar('Mezcla «$nombre» guardada');
    } on FormatException catch (e) {
      s.avisar(e.message);
    } catch (_) {
      s.avisar('No se pudo guardar la mezcla. Inténtalo otra vez.');
    }
  }

  Future<void> _misMezclas() async {
    final s = Caudal.leer(context);
    final elegida = await showModalBottomSheet<Mezcla>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (_) => _HojaMezclas(coleccion: s.coleccion),
    );
    if (elegida == null || !mounted) return;
    if (_items.isNotEmpty &&
        !await confirmar(context, 'Abrir «${elegida.nombre}»',
            'La mesa tiene canciones sin guardar. Si abres esta mezcla se reemplazan.', si: 'Abrir')) {
      return;
    }
    setState(() {
      _items.clear();
      _abierto = null;
      _nombre = elegida.nombre;
      for (final p in elegida.pasos) {
        _items.add(_Item(_siguienteId++, p));
      }
    });
  }

  // ------------------------------------------------------------ pantalla

  static String _tiempo(num segundos) {
    final t = segundos.round();
    final h = t ~/ 3600, m = (t % 3600) ~/ 60, s = t % 60;
    return h > 0 ? '$h:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}' : '$m:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final n = _items.length;
    final total = duracionDelSet(_pasos);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mezclador'),
        actions: [
          IconButton(
            tooltip: 'Mis mezclas',
            icon: const Icon(Icons.folder_open_rounded),
            onPressed: _misMezclas,
          ),
        ],
      ),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, Esp.m),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
              n == 0
                  ? 'Elige canciones y ajusta cómo se enlazan, como en una mesa de DJ.'
                  : '${_nombre.isEmpty ? '' : '$_nombre · '}$n ${n == 1 ? 'canción' : 'canciones'} · ${_tiempo(total)}',
              style: estiloSecundario,
            ),
            const SizedBox(height: Esp.s + 2),
            Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
              FilledButton.icon(
                onPressed: n >= 2 ? _reproducir : null,
                style: FilledButton.styleFrom(shape: const StadiumBorder()),
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('Reproducir la mezcla'),
              ),
              OutlinedButton.icon(
                onPressed: _anadir,
                icon: const Icon(Icons.add_rounded),
                label: const Text('Añadir canciones'),
              ),
              OutlinedButton.icon(
                onPressed: n >= 2 ? _guardar : null,
                icon: const Icon(Icons.save_outlined),
                label: const Text('Guardar'),
              ),
            ]),
          ]),
        ),
        Expanded(
          child: n == 0
              ? Vacio(
                  icono: Icons.album_rounded,
                  titulo: 'Tu mesa está vacía',
                  texto: 'Añade canciones de tu cola, de Tus me gusta o de tus listas y ordénalas arrastrando.',
                  textoAccion: 'Añadir canciones',
                  iconoAccion: Icons.add_rounded,
                  alAccion: _anadir,
                )
              : ReorderableListView.builder(
                  padding: EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, espacioInferior + 8),
                  buildDefaultDragHandles: false,
                  itemCount: n,
                  onReorderItem: (de, a) => setState(() => _items.insert(a, _items.removeAt(de))),
                  itemBuilder: (_, i) {
                    final it = _items[i];
                    final ultimo = i == n - 1;
                    return Column(
                      key: ValueKey(it.id),
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _FilaPaso(
                          indice: i,
                          paso: it.paso,
                          alQuitar: () => _quitar(it),
                          manija: ReorderableDragStartListener(
                            index: i,
                            child: const Padding(
                              padding: EdgeInsets.all(8),
                              child: Icon(Icons.drag_handle_rounded, color: C.texto3),
                            ),
                          ),
                        ),
                        if (!ultimo)
                          _Cambio(
                            paso: it.paso,
                            abierto: _abierto == it.id,
                            alAbrir: () => setState(() => _abierto = _abierto == it.id ? null : it.id),
                            alCambiar: (p) => setState(() => it.paso = p),
                            alProbar: () => _probar(it),
                            alIgualar: () => _igualarTodos(it.paso),
                          )
                        else
                          const SizedBox(height: Esp.s),
                      ],
                    );
                  },
                ),
        ),
      ]),
    );
  }
}

/// La tarjeta de una cancion del set.
class _FilaPaso extends StatelessWidget {
  const _FilaPaso({required this.indice, required this.paso, required this.alQuitar, required this.manija});
  final int indice;
  final PasoMezcla paso;
  final VoidCallback alQuitar;
  final Widget manija;

  @override
  Widget build(BuildContext context) {
    final p = paso.pista;
    final dur = paso.duracionPista;
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 8, 2, 8),
      decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(14)),
      child: Row(children: [
        SizedBox(
          width: 22,
          child: Text('${indice + 1}', textAlign: TextAlign.center,
              style: TextStyle(fontWeight: FontWeight.w900, color: C.acento)),
        ),
        const SizedBox(width: 8),
        Portada(url: '${p['miniatura'] ?? ''}', lado: 44, radio: 6),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloTituloFila),
            Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
          ]),
        ),
        if (dur > 0)
          Text(_MezcladorPaginaState._tiempo(dur), style: estiloDetalle),
        IconButton(
          tooltip: 'Quitar de la mezcla',
          visualDensity: VisualDensity.compact,
          icon: const Icon(Icons.close_rounded, size: 20, color: C.texto2),
          onPressed: alQuitar,
        ),
        manija,
      ]),
    );
  }
}

/// El cambio entre una cancion y la siguiente: un resumen que al tocarlo
/// abre los ajustes del paso.
class _Cambio extends StatelessWidget {
  const _Cambio({
    required this.paso,
    required this.abierto,
    required this.alAbrir,
    required this.alCambiar,
    required this.alProbar,
    required this.alIgualar,
  });
  final PasoMezcla paso;
  final bool abierto;
  final VoidCallback alAbrir;
  final ValueChanged<PasoMezcla> alCambiar;
  final VoidCallback alProbar;
  final VoidCallback alIgualar;

  static String _s(double v) => '${v.round()} s';

  @override
  Widget build(BuildContext context) {
    final real = paso.fundidoEfectivo;
    final resumen = 'Entra la siguiente a ${_s(paso.entraEfectivo)} del final · '
        'cambio de ${_s(real)}${paso.graves ? ' · con graves' : ''}';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: AnimatedContainer(
        duration: Mov.normal,
        curve: Mov.curva,
        decoration: BoxDecoration(
          color: abierto ? C.superficie3 : Colors.transparent,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: abierto ? C.acento.withValues(alpha: 0.5) : C.borde),
        ),
        // un Material propio: los toques (InkWell, el interruptor) pintan sobre el fondo de arriba
        child: Material(type: MaterialType.transparency, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: alAbrir,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(children: [
                Icon(Icons.swap_vert_rounded, size: 20, color: C.acento),
                const SizedBox(width: 10),
                Expanded(child: Text(resumen, style: const TextStyle(fontSize: 12.5, color: C.texto2, height: 1.3))),
                Icon(abierto ? Icons.expand_less_rounded : Icons.tune_rounded, size: 20, color: C.texto3),
              ]),
            ),
          ),
          AnimatedSize(
            duration: Mov.normal,
            curve: Mov.curva,
            alignment: Alignment.topCenter,
            child: !abierto
                ? const SizedBox(width: double.infinity)
                : Padding(
                    padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        const Expanded(child: Text('La siguiente entra cuando falten')),
                        Text(_s(paso.entraAntes), style: const TextStyle(fontWeight: FontWeight.w800)),
                      ]),
                      Slider(
                        value: paso.entraAntes.clamp(entraMin, entraMax),
                        min: entraMin, max: entraMax, divisions: (entraMax - entraMin).round(),
                        label: _s(paso.entraAntes),
                        onChanged: (v) => alCambiar(paso.copiaCon(entraAntes: v.roundToDouble())),
                      ),
                      Row(children: [
                        const Expanded(child: Text('El cambio dura')),
                        Text(_s(paso.fundido), style: const TextStyle(fontWeight: FontWeight.w800)),
                      ]),
                      Slider(
                        value: paso.fundido.clamp(fundidoMin, fundidoMax),
                        min: fundidoMin, max: fundidoMax, divisions: (fundidoMax - fundidoMin).round(),
                        label: _s(paso.fundido),
                        onChanged: (v) => alCambiar(paso.copiaCon(fundido: v.roundToDouble())),
                      ),
                      if (paso.fundido.round() > real.round())
                        Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Text('Dura ${_s(real)} de verdad: no puede ser más largo que lo que queda desde que entra la siguiente.',
                              style: estiloDetalle),
                        ),
                      SwitchListTile.adaptive(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Cambio de graves'),
                        subtitle: const Text('Los graves pasan de una canción a la otra', style: estiloSecundario),
                        value: paso.graves,
                        onChanged: (v) => alCambiar(paso.copiaCon(graves: v)),
                      ),
                      Wrap(spacing: Esp.s, children: [
                        FilledButton.tonalIcon(
                          onPressed: alProbar,
                          icon: const Icon(Icons.play_circle_outline_rounded),
                          label: const Text('Probar este cambio'),
                        ),
                        TextButton(onPressed: alIgualar, child: const Text('Igual en todos')),
                      ]),
                    ]),
                  ),
          ),
        ])),
      ),
    );
  }
}

// ---------------------------------------------------------------- elegir canciones

/// De donde se sacan las canciones: la cola, Tus me gusta o una lista.
class _HojaElegir extends StatefulWidget {
  const _HojaElegir();

  @override
  State<_HojaElegir> createState() => _HojaElegirState();
}

class _HojaElegirState extends State<_HojaElegir> {
  String _fuente = 'cola'; // cola | gusta | lista
  List<Json> _pistas = [];
  List<Json> _listas = [];
  // lo elegido en cualquier fuente (clave -> cancion), en el orden en que se marco
  final Map<String, Json> _marcadas = {};
  bool _cargando = false;
  bool _hecho = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_hecho) return;
    _hecho = true;
    _cambiar('cola');
  }

  Future<void> _cambiar(String f) async {
    final s = Caudal.leer(context);
    setState(() {
      _fuente = f;
      _cargando = true;
      _pistas = [];
    });
    List<Json> p = [];
    try {
      switch (f) {
        case 'cola':
          final r = s.reproductor;
          final vistas = <String>{};
          for (final x in [if (r.actual != null) r.actual!, ...r.proximas, ...r.siguientesDeContexto]) {
            if ('${x['clave'] ?? ''}'.isNotEmpty && vistas.add('${x['clave']}')) p.add(x);
          }
        case 'gusta':
          p = await s.coleccion.listaMeGusta();
        case 'lista':
          _listas = await s.coleccion.listas();
      }
    } catch (_) {}
    if (!mounted) return;
    setState(() {
      _pistas = p;
      _cargando = false;
    });
  }

  Future<void> _abrirLista(Json l) async {
    final id = Servicios.idLista(l['id']);
    if (id == null) return;
    setState(() => _cargando = true);
    final p = await Caudal.leer(context).coleccion.pistasDeLista(id);
    if (!mounted) return;
    setState(() {
      _pistas = p;
      _cargando = false;
      _listas = [];
      _fuente = 'lista_abierta';
    });
  }

  bool get _todasMarcadas => _pistas.isNotEmpty && _pistas.every((p) => _marcadas.containsKey('${p['clave']}'));

  @override
  Widget build(BuildContext context) {
    final eligiendoLista = _fuente == 'lista' && _listas.isNotEmpty && _pistas.isEmpty;
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.8,
      maxChildSize: 0.95,
      builder: (_, scroll) => Column(children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
          child: Align(alignment: Alignment.centerLeft, child: Text('Añadir canciones', style: estiloTituloSeccion)),
        ),
        SizedBox(
          height: 44,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 16), children: [
            for (final (clave, texto) in const [('cola', 'Tu cola'), ('gusta', 'Tus me gusta'), ('lista', 'Una lista')])
              Pildora(
                texto: texto,
                activa: _fuente == clave || (clave == 'lista' && _fuente == 'lista_abierta'),
                alPulsar: () => _cambiar(clave),
              ),
          ]),
        ),
        Expanded(
          child: _cargando
              ? const Center(child: CircularProgressIndicator.adaptive())
              : eligiendoLista
                  ? ListView(controller: scroll, children: [
                      for (final l in _listas)
                        ListTile(
                          leading: const Icon(Icons.queue_music_rounded, color: C.texto2),
                          title: Text('${l['nombre']}'),
                          subtitle: Text('${l['n']} canciones', style: estiloSecundario),
                          onTap: () => _abrirLista(l),
                        ),
                    ])
                  : _pistas.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24),
                            child: Text(
                              switch (_fuente) {
                                'cola' => 'Tu cola está vacía. Pon música y vuelve.',
                                'gusta' => 'Aún no tienes canciones en Tus me gusta.',
                                _ => 'Aquí no hay canciones.',
                              },
                              textAlign: TextAlign.center,
                              style: estiloSecundario,
                            ),
                          ),
                        )
                      : ListView.builder(
                          controller: scroll,
                          itemCount: _pistas.length,
                          itemBuilder: (_, i) {
                            final p = _pistas[i];
                            final clave = '${p['clave']}';
                            return CheckboxListTile(
                              value: _marcadas.containsKey(clave),
                              onChanged: (v) => setState(() => v == true ? _marcadas[clave] = p : _marcadas.remove(clave)),
                              secondary: Portada(url: '${p['miniatura'] ?? ''}', lado: 44, radio: 6),
                              title: Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
                              subtitle: Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                                  style: estiloSecundario),
                              controlAffinity: ListTileControlAffinity.trailing,
                            );
                          },
                        ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
            child: Row(children: [
              if (_pistas.isNotEmpty)
                TextButton(
                  onPressed: () => setState(() {
                    if (_todasMarcadas) {
                      for (final p in _pistas) {
                        _marcadas.remove('${p['clave']}');
                      }
                    } else {
                      for (final p in _pistas) {
                        _marcadas.putIfAbsent('${p['clave']}', () => p);
                      }
                    }
                  }),
                  child: Text(_todasMarcadas ? 'Quitar todas' : 'Elegir todas'),
                ),
              const Spacer(),
              FilledButton(
                onPressed: _marcadas.isEmpty
                    ? null
                    : () => Navigator.pop(context, _marcadas.values.toList()),
                style: FilledButton.styleFrom(shape: const StadiumBorder()),
                child: Text(_marcadas.isEmpty ? 'Añadir' : 'Añadir ${_marcadas.length}'),
              ),
            ]),
          ),
        ),
      ]),
    );
  }
}

// ---------------------------------------------------------------- mezclas guardadas

class _HojaMezclas extends StatefulWidget {
  const _HojaMezclas({required this.coleccion});
  final Coleccion coleccion;

  @override
  State<_HojaMezclas> createState() => _HojaMezclasState();
}

class _HojaMezclasState extends State<_HojaMezclas> {
  List<Mezcla>? _mezclas;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    List<Mezcla> m = [];
    try {
      m = await Mezclas.leer(widget.coleccion);
    } catch (_) {}
    if (mounted) setState(() => _mezclas = m);
  }

  @override
  Widget build(BuildContext context) {
    final m = _mezclas;
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.7),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
            child: Align(alignment: Alignment.centerLeft, child: Text('Mis mezclas', style: estiloTituloSeccion)),
          ),
          if (m == null)
            const Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator.adaptive())
          else if (m.isEmpty)
            const Padding(
              padding: EdgeInsets.fromLTRB(24, 16, 24, 32),
              child: Text('Aún no guardaste ninguna mezcla. Arma una y toca «Guardar».',
                  textAlign: TextAlign.center, style: estiloSecundario),
            )
          else
            Flexible(
              child: ListView(shrinkWrap: true, children: [
                for (final x in m)
                  ListTile(
                    leading: Portada(url: '${x.pasos.first.pista['miniatura'] ?? ''}', lado: 44, radio: 6),
                    title: Text(x.nombre, maxLines: 1, overflow: TextOverflow.ellipsis),
                    subtitle: Text('${x.pasos.length} canciones · ${_MezcladorPaginaState._tiempo(duracionDelSet(x.pasos))}',
                        style: estiloSecundario),
                    trailing: IconButton(
                      tooltip: 'Borrar la mezcla',
                      icon: const Icon(Icons.delete_outline_rounded, color: C.texto2),
                      onPressed: () async {
                        if (!await confirmar(context, 'Borrar «${x.nombre}»', 'Las canciones se quedan donde estaban.')) return;
                        await Mezclas.borrar(widget.coleccion, x.id);
                        _cargar();
                      },
                    ),
                    onTap: () => Navigator.pop(context, x),
                  ),
              ]),
            ),
        ]),
      ),
    );
  }
}
