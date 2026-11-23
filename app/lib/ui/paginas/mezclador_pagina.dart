import 'dart:math';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../nucleo/analizador_ritmo.dart';
import '../../nucleo/coleccion.dart';
import '../../nucleo/mezcla_dj.dart';
import '../../nucleo/ritmo.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';

/// La mesa del Mezclador: se arma un set con canciones de la cola, de Tus me
/// gusta o de tus listas, se ordena (a mano o «como un DJ»), y por cada paso se
/// elige como cambia (fundido, corte, filtro, eco o graves), cuando entra la
/// siguiente, el tempo y el compas, el ecualizador y los puntos de entrada y
/// salida. Se puede probar un paso, reproducir el set y guardarlo con nombre.
///
/// Se abre con `Navigator.push(MaterialPageRoute(builder: (_) => const MezcladorPagina()))`
/// (o `s.abrirEnPestana?.call(const MezcladorPagina())`). [inicial] deja la mesa
/// con esas canciones; con [perfilAuto] las mezcla solas al abrir
/// («Mezclar esta lista como un DJ»).
///
/// Como esta pensada para entenderse sin explicacion: arriba un «como funciona»
/// en tres pasos (se pliega cuando ya hay canciones y se reabre con el «?»),
/// un boton grande de «Mezclar como un DJ», una tarjeta por cancion y, entre
/// cada dos, un dibujo del cambio con tres estilos rapidos y los «ajustes
/// finos» plegados. Abajo, siempre a la vista, el total y Reproducir / Guardar.
/// La lista es perezosa: aguanta cientos de canciones.
class MezcladorPagina extends StatefulWidget {
  const MezcladorPagina({super.key, this.inicial = const [], this.perfilAuto});

  final List<Json> inicial;
  final PerfilMezcla? perfilAuto;

  @override
  State<MezcladorPagina> createState() => _MezcladorPaginaState();
}

/// Un paso con un numero propio, para que al reordenar no se confundan.
class _Item {
  _Item(this.id, this.paso);
  final int id;
  PasoMezcla paso;
}

/// Lo que el motor de este telefono puede hacer (para avisarlo en pantalla).
class _Capacidades {
  const _Capacidades({this.tempo = true, this.filtros = true, this.eco = false});
  final bool tempo;
  final bool filtros;
  final bool eco;
}

class _MezcladorPaginaState extends State<MezcladorPagina> {
  final List<_Item> _items = [];
  int _siguienteId = 1;
  int? _abierto; // el id del paso con el panel de ajustes abierto
  String _nombre = '';
  AnalizadorRitmo? _analizador;
  bool _analizando = false;
  int _hechas = 0;
  int _faltan = 0;
  // el «como funciona»: abierto mientras no hay un set armado, se reabre con el «?»
  late bool _ayuda = widget.inicial.length < 2;

  @override
  void initState() {
    super.initState();
    _poner(widget.inicial);
    WidgetsBinding.instance.addPostFrameCallback((_) => _iniciar());
  }

  @override
  void dispose() {
    _analizador?.removeListener(_refrescar);
    _analizador?.dispose();
    super.dispose();
  }

  void _refrescar() {
    if (mounted) setState(() {});
  }

  Future<void> _iniciar() async {
    if (!mounted) return;
    final a = AnalizadorRitmo(Caudal.leer(context).coleccion);
    _analizador = a..addListener(_refrescar);
    await a.cargar();
    if (mounted && widget.perfilAuto != null && _items.length >= 2) await _mezclarAuto(widget.perfilAuto!);
  }

  void _poner(List<Json> pistas) {
    for (final p in pistas) {
      _items.add(_Item(_siguienteId++, PasoMezcla(pista: p)));
    }
  }

  List<PasoMezcla> get _pasos => [for (final i in _items) i.paso];
  Map<String, AnalisisRitmo> get _ritmo => _analizador?.todo ?? const {};
  AnalisisRitmo? _ritmoDe(PasoMezcla p) => _ritmo['${p.pista['clave']}'];

  int _indiceDe(int id) => _items.indexWhere((i) => i.id == id);

  _Capacidades get _capacidades {
    final r = Caudal.leer(context).reproductor;
    return _Capacidades(tempo: r.puedeEstirarTiempo, filtros: r.puedeFiltrar, eco: r.puedeEco);
  }

  // ------------------------------------------------------------ acciones

  /// Abre la hoja para elegir canciones. [fuente]: cola | gusta | lista.
  /// Con [mezclar] la mesa se mezcla sola, como un DJ, al terminar de añadir.
  Future<void> _anadir({String fuente = 'cola', bool mezclar = false}) async {
    final elegidas = await showModalBottomSheet<List<Json>>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (_) => _HojaElegir(fuenteInicial: fuente),
    );
    if (elegidas == null || elegidas.isEmpty || !mounted) return;
    setState(() {
      _poner(elegidas);
      if (_items.length >= 2) _ayuda = false;
    });
    if (mezclar && _items.length >= 2) await _elegirPerfil();
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

  void _igualarTodos(PasoMezcla m) {
    setState(() {
      for (final it in _items) {
        it.paso = it.paso.copiaCon(
            entraAntes: m.entraAntes, fundido: m.fundido, graves: m.graves, tipo: m.tipo, curva: m.curva,
            igualarTempo: m.igualarTempo, alCompas: m.alCompas, quitarSalida: true);
      }
    });
    Caudal.leer(context).avisar('Todos los cambios quedaron igual');
  }

  /// Aplica a un cambio uno de los tres estilos rapidos (mirando el tempo de las dos canciones).
  void _estilo(_Item it, PerfilMezcla perfil) {
    final i = _indiceDe(it.id);
    if (i < 0 || i + 1 >= _items.length) return;
    final n = pasoParaPerfil(perfil, it.paso.pista,
        ritmo: _ritmoDe(it.paso), siguiente: _ritmoDe(_items[i + 1].paso));
    setState(() {
      it.paso = it.paso.copiaCon(
          entraAntes: n.entraAntes, fundido: n.fundido, graves: n.graves, tipo: n.tipo, curva: n.curva,
          igualarTempo: n.igualarTempo, alCompas: n.alCompas, quitarSalida: true);
    });
  }

  Future<void> _probar(_Item it) async {
    final i = _indiceDe(it.id);
    final s = Caudal.leer(context);
    if (i < 0 || i + 1 >= _items.length) return;
    if (it.paso.duracionPista <= 0) {
      return s.avisar('No se sabe cuánto dura esa canción, así que no se puede probar el cambio.');
    }
    s.avisar('Probando el cambio…');
    await s.reproductor.probarPaso(it.paso, _items[i + 1].paso.pista, ritmo: _ritmo);
  }

  Future<void> _reproducir() async {
    final s = Caudal.leer(context);
    if (_items.length < 2) return s.avisar('Añade al menos dos canciones para mezclar.');
    await s.reproductor.reproducirSet(_pasos, titulo: _nombre.isEmpty ? 'Tu mezcla' : _nombre, ritmo: _ritmo);
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
      _ayuda = false;
      for (final p in elegida.pasos) {
        _items.add(_Item(_siguienteId++, p));
      }
    });
  }

  // ------------------------------------------------------------ ritmo

  /// Un archivo o enlace que ffmpeg pueda leer para analizar la cancion (null si no hay).
  Future<String?> _origenDe(Json p) async {
    final s = Caudal.leer(context);
    try {
      final archivo = p['archivo'];
      if (archivo is String && archivo.isNotEmpty && s.coleccion.estaDescargada(p)) return archivo;
      final copia = s.coleccion.copiaLocal('${p['video_id'] ?? ''}')?['archivo'];
      if (copia is String && copia.isNotEmpty) return copia;
      final vid = '${p['video_id'] ?? ''}';
      if (vid.isEmpty || kIsWeb) return null;
      final f = await s.streams.resolver(vid, video: false, calidad: s.ajustes.texto('calidad_audio'));
      return f.url.startsWith('http') || f.local ? f.url : null;
    } catch (_) {
      return null;
    }
  }

  /// Analiza el ritmo de las canciones de [pendientes] (con barra de avance).
  Future<void> _analizarPistas(List<Json> pendientes) async {
    final a = _analizador;
    final s = Caudal.leer(context);
    if (a == null || _analizando) return;
    if (pendientes.isEmpty) return;
    if (kIsWeb && pendientes.every((p) => '${p['archivo'] ?? ''}'.isEmpty)) {
      s.avisar('En el navegador solo se puede saber el ritmo de tu música y la de la comunidad. '
          'Para las de YouTube, toca su tempo y escríbelo a mano.');
      return;
    }
    setState(() {
      _analizando = true;
      _hechas = 0;
      _faltan = pendientes.length;
    });
    var fallos = 0;
    for (final p in pendientes) {
      final origen = await _origenDe(p);
      AnalisisRitmo? r;
      if (origen != null) {
        r = await a.analizar('${p['clave']}', origen, duracion: ((p['duracion'] as num?) ?? 0).toDouble());
      }
      if (r == null || !r.valido) fallos++;
      if (!mounted) return;
      setState(() => _hechas++);
    }
    if (!mounted) return;
    setState(() => _analizando = false);
    if (fallos > 0) {
      s.avisar('No se pudo saber el ritmo de $fallos ${fallos == 1 ? 'canción' : 'canciones'}. '
          'Toca su tempo para escribirlo a mano.');
    }
  }

  /// Las canciones de la mesa que aun no tienen el ritmo analizado.
  List<Json> get _sinRitmo {
    final a = _analizador;
    return [
      for (final it in _items)
        if (a?.de('${it.paso.pista['clave']}')?.valido != true) it.paso.pista
    ];
  }

  Future<void> _analizarTodo() => _analizarPistas(_sinRitmo);

  Future<void> _ordenar() async {
    await _analizarTodo();
    if (!mounted) return;
    final s = Caudal.leer(context);
    final conRitmo = _items.where((i) => _ritmoDe(i.paso)?.valido == true).length;
    if (conRitmo < 2) {
      return s.avisar('Hace falta conocer el ritmo de al menos dos canciones para ordenarlas.');
    }
    setState(() {
      final nuevo = ordenarComoDj(_pasos, _ritmo);
      final porPaso = {for (final i in _items) i.paso: i};
      _items
        ..clear()
        ..addAll([for (final p in nuevo) porPaso[p]!]);
      _abierto = null;
    });
    s.avisar('Set ordenado por tempo y energía');
  }

  Future<void> _mezclarAuto(PerfilMezcla perfil) async {
    await _analizarTodo();
    if (!mounted) return;
    final s = Caudal.leer(context);
    final nuevos = mezclaAutomatica([for (final i in _items) i.paso.pista], perfil, _ritmo);
    setState(() {
      _items
        ..clear()
        ..addAll([for (final p in nuevos) _Item(_siguienteId++, p)]);
      _abierto = null;
    });
    final sin = _items.where((i) => _ritmoDe(i.paso)?.valido != true).length;
    s.avisar(sin == 0
        ? 'Mezcla «${perfil.nombre}» lista'
        : 'Mezcla «${perfil.nombre}» lista; en $sin ${sin == 1 ? 'canción' : 'canciones'} sin ritmo se mezcla por duración');
  }

  Future<void> _elegirPerfil() async {
    if (_items.length < 2) return Caudal.leer(context).avisar('Añade al menos dos canciones para mezclar.');
    final p = await showModalBottomSheet<PerfilMezcla>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 0, 20, 4),
            child: Text('Mezclar como un DJ', style: estiloTituloSeccion),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
            child: Text('Elige un estilo. Caudal ordena las canciones por tempo y energía y pone un cambio a cada paso. '
                'Después puedes retocar cada cambio a mano.',
                style: estiloSecundario),
          ),
          for (final x in PerfilMezcla.values)
            ListTile(
              leading: Icon(switch (x) {
                PerfilMezcla.suave => Icons.spa_rounded,
                PerfilMezcla.club => Icons.nightlife_rounded,
                PerfilMezcla.rapida => Icons.bolt_rounded,
              }, color: C.acento),
              title: Text(x.nombre, style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text(x.ayuda, style: estiloSecundario),
              onTap: () => Navigator.pop(ctx, x),
            ),
          const SizedBox(height: 8),
        ]),
      ),
    );
    if (p != null) await _mezclarAuto(p);
  }

  Future<void> _editarTempo(_Item it) async {
    final clave = '${it.paso.pista['clave']}';
    final actual = _ritmoDe(it.paso);
    final bpm = await showDialog<double>(
      context: context,
      useRootNavigator: true,
      builder: (_) => _DialogoTempo(inicial: actual != null && actual.valido ? actual.bpm : null),
    );
    if (bpm == null || !mounted) return;
    await _analizador?.ponerManual(clave, bpm);
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
    final caps = _analizador == null ? const _Capacidades() : _capacidades;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mezclador'),
        actions: [
          IconButton(
            tooltip: 'Cómo funciona',
            icon: Icon(_ayuda ? Icons.help_rounded : Icons.help_outline_rounded),
            onPressed: () => setState(() => _ayuda = !_ayuda),
          ),
          IconButton(
            tooltip: 'Mis mezclas',
            icon: const Icon(Icons.folder_open_rounded),
            onPressed: _misMezclas,
          ),
        ],
      ),
      body: Column(children: [
        Expanded(child: n == 0 ? _vacio() : _lista(n, caps)),
        if (n > 0) _barraInferior(n),
      ]),
    );
  }

  // ---- la mesa vacia: explicacion y accesos directos

  Widget _vacio() => ListView(
        padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, Esp.xl),
        children: [
          Center(
            child: Container(
              width: 76,
              height: 76,
              decoration: BoxDecoration(shape: BoxShape.circle, color: C.acento.withValues(alpha: 0.14)),
              child: Icon(Icons.album_rounded, size: 40, color: C.acento),
            ),
          ),
          const SizedBox(height: Esp.m),
          const Text('Tu mesa está vacía',
              textAlign: TextAlign.center, style: estiloTituloSeccion),
          const SizedBox(height: 6),
          const Text('Aquí unes canciones para que suenen seguidas, sin cortes, como un DJ. Empieza eligiendo de dónde.',
              textAlign: TextAlign.center, style: estiloSecundario),
          const SizedBox(height: Esp.l),
          const _Guia(),
          const SizedBox(height: Esp.l),
          _Acceso(
            icono: Icons.queue_music_rounded,
            titulo: 'Desde tu cola',
            texto: 'Lo que suena ahora y lo que viene después',
            alPulsar: () => _anadir(fuente: 'cola'),
          ),
          _Acceso(
            icono: Icons.favorite_rounded,
            titulo: 'Desde Tus me gusta',
            texto: 'Elige entre las canciones que marcaste',
            alPulsar: () => _anadir(fuente: 'gusta'),
          ),
          _Acceso(
            icono: Icons.library_music_rounded,
            titulo: 'Desde una de tus listas',
            texto: 'Una lista tuya, entera o solo unas cuantas',
            alPulsar: () => _anadir(fuente: 'lista'),
          ),
          _Acceso(
            icono: Icons.auto_awesome_rounded,
            titulo: 'Mezclar una lista como un DJ',
            texto: 'Elige una lista y Caudal la ordena y la une solo',
            destacado: true,
            alPulsar: () => _anadir(fuente: 'lista', mezclar: true),
          ),
          const SizedBox(height: Esp.m),
          Center(
            child: FilledButton.icon(
              onPressed: () => _anadir(),
              style: FilledButton.styleFrom(shape: const StadiumBorder()),
              icon: const Icon(Icons.add_rounded),
              label: const Text('Añadir canciones'),
            ),
          ),
        ],
      );

  // ---- la mesa con canciones

  Widget _cabecera(int n, _Capacidades caps) {
    return Padding(
      padding: const EdgeInsets.only(top: Esp.s, bottom: Esp.m),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        AnimatedSize(
          duration: Mov.normal,
          curve: Mov.curva,
          alignment: Alignment.topCenter,
          child: _ayuda
              ? Padding(
                  padding: const EdgeInsets.only(bottom: Esp.m),
                  child: _Guia(alCerrar: () => setState(() => _ayuda = false)),
                )
              : const SizedBox(width: double.infinity),
        ),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: _analizando ? null : _elegirPerfil,
            style: FilledButton.styleFrom(
                shape: const StadiumBorder(), padding: const EdgeInsets.symmetric(vertical: 14)),
            icon: const Icon(Icons.auto_awesome_rounded, size: 20),
            label: const Text('Mezclar como un DJ'),
          ),
        ),
        const SizedBox(height: Esp.s),
        Row(children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: _anadir,
              style: OutlinedButton.styleFrom(
                  shape: const StadiumBorder(), padding: const EdgeInsets.symmetric(vertical: 12)),
              icon: const Icon(Icons.add_rounded, size: 20),
              label: const Text('Añadir canciones'),
            ),
          ),
          PopupMenuButton<String>(
            tooltip: 'Más opciones',
            icon: const Icon(Icons.more_vert_rounded),
            onSelected: (v) {
              if (v == 'ordenar') _ordenar();
              if (v == 'analizar') _analizarTodo();
            },
            itemBuilder: (_) => [
              PopupMenuItem(
                value: 'ordenar',
                enabled: n >= 2 && !_analizando,
                child: const _ItemMenu(Icons.sort_rounded, 'Ordenar por tempo y energía',
                    'Pone seguidas las que mejor encajan'),
              ),
              PopupMenuItem(
                value: 'analizar',
                enabled: !_analizando,
                child: const _ItemMenu(Icons.graphic_eq_rounded, 'Detectar el ritmo de todas',
                    'Lo hace solo; tarda unos segundos por canción'),
              ),
            ],
          ),
        ]),
        if (_analizando) ...[
          const SizedBox(height: Esp.m),
          LinearProgressIndicator(
              value: _faltan == 0 ? null : _hechas / _faltan, color: C.acento, backgroundColor: C.superficie3),
          const SizedBox(height: 4),
          Text('Escuchando el ritmo… $_hechas de $_faltan', style: estiloDetalle),
        ],
        if (n >= 2 && !caps.tempo)
          const Padding(
            padding: EdgeInsets.only(top: Esp.s),
            child: Text('En este teléfono no se puede acercar el tempo de las canciones sin cambiarles el tono: '
                'se mezclan a su propio tempo.', style: estiloDetalle),
          ),
        if (n == 1)
          const Padding(
            padding: EdgeInsets.only(top: Esp.s),
            child: Text('Añade al menos una canción más: una mezcla necesita dos.', style: estiloDetalle),
          ),
      ]),
    );
  }

  Widget _lista(int n, _Capacidades caps) {
    final encajes = encajesDelSet(_pasos, _ritmo);
    return ReorderableListView.builder(
      padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, Esp.l),
      buildDefaultDragHandles: false,
      header: _cabecera(n, caps),
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
              ritmo: _ritmoDe(it.paso),
              ocupado: _analizando,
              alTempo: () => _editarTempo(it),
              alDetectar: () => _analizarPistas([it.paso.pista]),
              alQuitar: () => _quitar(it),
              manija: ReorderableDragStartListener(
                index: i,
                child: Tooltip(
                  message: 'Mantén y arrastra para cambiar de lugar',
                  child: const Padding(
                    padding: EdgeInsets.all(8),
                    child: Icon(Icons.drag_handle_rounded, color: C.texto3),
                  ),
                ),
              ),
            ),
            if (!ultimo)
              _Cambio(
                paso: it.paso,
                siguiente: _items[i + 1].paso,
                ritmo: _ritmoDe(it.paso),
                ritmoSiguiente: _ritmoDe(_items[i + 1].paso),
                encaje: encajes[i],
                caps: caps,
                abierto: _abierto == it.id,
                alAbrir: () => setState(() => _abierto = _abierto == it.id ? null : it.id),
                alCambiar: (p) => setState(() => it.paso = p),
                alCambiarSiguiente: (p) => setState(() => _items[i + 1].paso = p),
                alEstilo: (perfil) => _estilo(it, perfil),
                alProbar: () => _probar(it),
                alIgualar: () => _igualarTodos(it.paso),
              )
            else
              const SizedBox(height: Esp.s),
          ],
        );
      },
    );
  }

  /// Abajo, siempre a la vista: cuantas canciones, cuanto dura y Guardar / Reproducir.
  /// Deja sitio al mini reproductor, que flota sobre esta zona cuando suena algo.
  Widget _barraInferior(int n) {
    final total = duracionDelSet(_pasos);
    final r = Caudal.leer(context).reproductor;
    return ListenableBuilder(
      listenable: r,
      builder: (context, _) => Container(
        padding: EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, r.actual != null ? 78 : Esp.m),
        decoration: BoxDecoration(
          color: C.superficie,
          border: Border(top: BorderSide(color: C.borde)),
        ),
        child: SafeArea(
          top: false,
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
              '${_nombre.isEmpty ? '' : '$_nombre · '}$n ${n == 1 ? 'canción' : 'canciones'} · ${_tiempo(total)}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: Esp.s),
            Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: n >= 2 ? _guardar : null,
                  style: OutlinedButton.styleFrom(
                      shape: const StadiumBorder(), padding: const EdgeInsets.symmetric(vertical: 14)),
                  icon: const Icon(Icons.save_outlined, size: 20),
                  label: const Text('Guardar'),
                ),
              ),
              const SizedBox(width: Esp.s),
              Expanded(
                flex: 2,
                child: FilledButton.icon(
                  onPressed: n >= 2 ? _reproducir : null,
                  style: FilledButton.styleFrom(
                      shape: const StadiumBorder(), padding: const EdgeInsets.symmetric(vertical: 14)),
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: const Text('Reproducir la mezcla'),
                ),
              ),
            ]),
          ]),
        ),
      ),
    );
  }
}

/// Un renglon del menu de «Más opciones» con su explicacion.
class _ItemMenu extends StatelessWidget {
  const _ItemMenu(this.icono, this.titulo, this.texto);
  final IconData icono;
  final String titulo;
  final String texto;

  @override
  Widget build(BuildContext context) => Row(children: [
        Icon(icono, size: 22, color: C.acento),
        const SizedBox(width: 12),
        Flexible(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(titulo, style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(texto, style: estiloDetalle),
          ]),
        ),
      ]);
}

/// Un acceso grande de la mesa vacia.
class _Acceso extends StatelessWidget {
  const _Acceso({required this.icono, required this.titulo, required this.texto, required this.alPulsar,
      this.destacado = false});
  final IconData icono;
  final String titulo;
  final String texto;
  final VoidCallback alPulsar;
  final bool destacado;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: Esp.s),
        child: Material(
          color: destacado ? C.acento.withValues(alpha: 0.14) : C.superficie2,
          borderRadius: BorderRadius.circular(14),
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: alPulsar,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(children: [
                Icon(icono, color: C.acento),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(titulo, style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(texto, style: estiloSecundario),
                  ]),
                ),
                const Icon(Icons.chevron_right_rounded, color: C.texto3),
              ]),
            ),
          ),
        ),
      );
}

/// «Como funciona» en tres pasos. Con [alCerrar] sale un «Entendido» para plegarla.
class _Guia extends StatelessWidget {
  const _Guia({this.alCerrar});
  final VoidCallback? alCerrar;

  @override
  Widget build(BuildContext context) {
    Widget paso(int n, IconData icono, String titulo, String texto) => Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 28,
              height: 28,
              alignment: Alignment.center,
              decoration: BoxDecoration(shape: BoxShape.circle, color: C.acento),
              child: Text('$n', style: TextStyle(fontWeight: FontWeight.w900, color: C.acentoTexto)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Icon(icono, size: 16, color: C.acento),
                  const SizedBox(width: 6),
                  Flexible(child: Text(titulo, style: const TextStyle(fontWeight: FontWeight.w800))),
                ]),
                Text(texto, style: estiloSecundario),
              ]),
            ),
          ]),
        );
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 6),
      decoration: BoxDecoration(
        color: C.superficie2,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: C.acento.withValues(alpha: 0.35)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Cómo funciona', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
        const SizedBox(height: 10),
        paso(1, Icons.add_rounded, 'Añade canciones',
            'De tu cola, de Tus me gusta o de una lista. Con dos basta.'),
        paso(2, Icons.auto_awesome_rounded, 'Mézclalas',
            'Toca «Mezclar como un DJ» y Caudal las ordena y une solo. O toca el cambio entre dos canciones para ajustarlo tú.'),
        paso(3, Icons.play_arrow_rounded, 'Reproduce',
            'Pulsa «Reproducir la mezcla». Si te gusta, guárdala para volver a ella.'),
        if (alCerrar != null)
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(onPressed: alCerrar, child: const Text('Entendido')),
          )
        else
          const SizedBox(height: 4),
      ]),
    );
  }
}

/// La tarjeta de una cancion del set, con su tempo.
class _FilaPaso extends StatelessWidget {
  const _FilaPaso({
    required this.indice,
    required this.paso,
    required this.ritmo,
    required this.ocupado,
    required this.alTempo,
    required this.alDetectar,
    required this.alQuitar,
    required this.manija,
  });
  final int indice;
  final PasoMezcla paso;
  final AnalisisRitmo? ritmo;
  final bool ocupado;
  final VoidCallback alTempo;
  final VoidCallback alDetectar;
  final VoidCallback alQuitar;
  final Widget manija;

  static String _energia(double e) => e < 0.34 ? 'baja' : (e < 0.67 ? 'media' : 'alta');

  @override
  Widget build(BuildContext context) {
    final p = paso.pista;
    final dur = paso.duracionPista;
    final bpm = ritmo != null && ritmo!.valido ? ritmo : null;
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 10, 2, 8),
      decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(16)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(
          width: 22,
          child: Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Text('${indice + 1}', textAlign: TextAlign.center,
                style: TextStyle(fontWeight: FontWeight.w900, color: C.acento)),
          ),
        ),
        const SizedBox(width: 8),
        Portada(url: '${p['miniatura'] ?? ''}', lado: 52, radio: 8),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloTituloFila),
            Row(children: [
              Expanded(
                child: Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: estiloSecundario),
              ),
              if (dur > 0) Text(_MezcladorPaginaState._tiempo(dur), style: estiloDetalle),
            ]),
            const SizedBox(height: 6),
            if (bpm != null)
              // tempo y energia: tocar para cambiarlo o marcarlo con los dedos
              Tooltip(
                message: 'Cambiar el tempo',
                child: InkWell(
                  borderRadius: BorderRadius.circular(8),
                  onTap: alTempo,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Wrap(crossAxisAlignment: WrapCrossAlignment.center, spacing: 8, runSpacing: 2, children: [
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        Icon(Icons.speed_rounded, size: 15, color: C.acento),
                        const SizedBox(width: 4),
                        Text('${bpm.bpm.round()} BPM',
                            style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
                      ]),
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        for (var k = 0; k < 5; k++)
                          Container(
                            width: 5,
                            height: 5 + k * 1.5,
                            margin: const EdgeInsets.only(right: 2),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(1),
                              color: bpm.energia * 5 > k ? C.acento : C.superficie3,
                            ),
                          ),
                        const SizedBox(width: 4),
                        Text('Energía ${_energia(bpm.energia)}', style: estiloDetalle),
                      ]),
                    ]),
                  ),
                ),
              )
            else
              Wrap(spacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
                const Text('Sin tempo', style: estiloDetalle),
                TextButton.icon(
                  onPressed: ocupado ? null : alDetectar,
                  style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact, padding: const EdgeInsets.symmetric(horizontal: 8)),
                  icon: const Icon(Icons.graphic_eq_rounded, size: 16),
                  label: const Text('Detectar ritmo'),
                ),
                TextButton(
                  onPressed: alTempo,
                  style: TextButton.styleFrom(
                      visualDensity: VisualDensity.compact, padding: const EdgeInsets.symmetric(horizontal: 8)),
                  child: const Text('Escribirlo'),
                ),
              ]),
          ]),
        ),
        Column(mainAxisSize: MainAxisSize.min, children: [
          IconButton(
            tooltip: 'Quitar de la mezcla',
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.close_rounded, size: 20, color: C.texto2),
            onPressed: alQuitar,
          ),
          manija,
        ]),
      ]),
    );
  }
}

/// El cambio entre una cancion y la siguiente: un dibujo de como suben y bajan
/// las dos, un resumen (con color segun lo bien que encajan los tempos) y, al
/// tocarlo, tres estilos rapidos, «Probar» y los «Ajustes finos» plegados.
class _Cambio extends StatefulWidget {
  const _Cambio({
    required this.paso,
    required this.siguiente,
    required this.ritmo,
    required this.ritmoSiguiente,
    required this.encaje,
    required this.caps,
    required this.abierto,
    required this.alAbrir,
    required this.alCambiar,
    required this.alCambiarSiguiente,
    required this.alEstilo,
    required this.alProbar,
    required this.alIgualar,
  });
  final PasoMezcla paso;
  final PasoMezcla siguiente;
  final AnalisisRitmo? ritmo;
  final AnalisisRitmo? ritmoSiguiente;
  final Encaje encaje;
  final _Capacidades caps;
  final bool abierto;
  final VoidCallback alAbrir;
  final ValueChanged<PasoMezcla> alCambiar;
  final ValueChanged<PasoMezcla> alCambiarSiguiente;
  final ValueChanged<PerfilMezcla> alEstilo;
  final VoidCallback alProbar;
  final VoidCallback alIgualar;

  @override
  State<_Cambio> createState() => _CambioState();
}

class _CambioState extends State<_Cambio> {
  bool _finos = false;

  PasoMezcla get paso => widget.paso;
  PasoMezcla get siguiente => widget.siguiente;
  AnalisisRitmo? get ritmo => widget.ritmo;
  AnalisisRitmo? get ritmoSiguiente => widget.ritmoSiguiente;
  _Capacidades get caps => widget.caps;
  ValueChanged<PasoMezcla> get alCambiar => widget.alCambiar;

  static String _s(double v) => '${v.round()} s';

  Color get _colorEncaje => switch (widget.encaje) {
        Encaje.bueno => C.exito,
        Encaje.regular => const Color(0xFFF5C542),
        Encaje.choca => C.error,
        Encaje.desconocido => C.texto3,
      };

  String get _etiquetaEncaje => switch (widget.encaje) {
        Encaje.bueno => 'Encajan bien',
        Encaje.regular => 'Algo distintas',
        Encaje.choca => 'Chocan',
        Encaje.desconocido => 'Sin tempo',
      };

  String get _textoEncaje => switch (widget.encaje) {
        Encaje.bueno => 'Tempos parecidos: encajan bien',
        Encaje.regular => 'Tempos algo distintos',
        Encaje.choca => 'Tempos que chocan: mejor un filtro o un fundido largo',
        Encaje.desconocido => 'Sin tempo: se mezcla por duración',
      };

  @override
  Widget build(BuildContext context) {
    final real = paso.fundidoEfectivo;
    final entra = _s(paso.entraEfectivo);
    final resumen = paso.tipo == TipoTransicion.corte
        ? '${paso.tipo.nombre} · la siguiente entra a $entra del final'
        : '${paso.tipo.nombre} de ${_s(real)} · la siguiente entra a $entra del final';
    final abierto = widget.abierto;
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
            onTap: widget.alAbrir,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Icon(Icons.swap_vert_rounded, size: 18, color: C.acento),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text('Cambio a la siguiente canción',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: C.texto3)),
                  ),
                  Tooltip(
                    message: _textoEncaje,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: _colorEncaje.withValues(alpha: 0.16),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(_etiquetaEncaje,
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: _colorEncaje)),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Icon(abierto ? Icons.expand_less_rounded : Icons.tune_rounded, size: 20, color: C.texto3),
                ]),
                const SizedBox(height: 8),
                _GraficoCambio(paso: paso),
                const SizedBox(height: 6),
                Row(children: [
                  _Leyenda(color: C.texto2, texto: 'Esta canción baja'),
                  const Spacer(),
                  _Leyenda(color: C.acento, texto: 'La siguiente sube', alDerecha: true),
                ]),
                const SizedBox(height: 6),
                Text(resumen, style: const TextStyle(fontSize: 12.5, color: C.texto2, height: 1.3)),
                if (!abierto)
                  const Padding(
                    padding: EdgeInsets.only(top: 2),
                    child: Text('Toca para cambiar el estilo, probarlo o ajustarlo', style: estiloDetalle),
                  ),
              ]),
            ),
          ),
          AnimatedSize(
            duration: Mov.normal,
            curve: Mov.curva,
            alignment: Alignment.topCenter,
            child: !abierto ? const SizedBox(width: double.infinity) : _panel(context),
          ),
        ])),
      ),
    );
  }

  Widget _chips<T>(List<T> valores, T actual, String Function(T) nombre, ValueChanged<T> alElegir,
      {bool Function(T)? habilitado}) {
    return Wrap(spacing: 8, runSpacing: 6, children: [
      for (final v in valores)
        ChoiceChip(
          label: Text(nombre(v)),
          selected: v == actual,
          showCheckmark: false,
          selectedColor: C.acento,
          labelStyle: TextStyle(fontWeight: FontWeight.w600, color: v == actual ? C.acentoTexto : C.texto),
          backgroundColor: C.superficie2,
          side: BorderSide.none,
          onSelected: (habilitado?.call(v) ?? true) ? (_) => alElegir(v) : null,
        ),
    ]);
  }

  Widget _titulo(String t) => Padding(
        padding: const EdgeInsets.only(top: 14, bottom: 6),
        child: Text(t.toUpperCase(),
            style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, letterSpacing: 1, color: C.acento)),
      );

  /// Lo primero que se ve al abrir un cambio: estilos rapidos, probar y los ajustes finos.
  Widget _panel(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_textoEncaje, style: TextStyle(fontSize: 12.5, color: _colorEncaje, fontWeight: FontWeight.w700)),
        _titulo('Elige un estilo'),
        Wrap(spacing: 8, runSpacing: 6, children: [
          for (final (perfil, icono, nombre) in const [
            (PerfilMezcla.suave, Icons.spa_rounded, 'Suave'),
            (PerfilMezcla.club, Icons.nightlife_rounded, 'Club'),
            (PerfilMezcla.rapida, Icons.bolt_rounded, 'Corte rápido'),
          ])
            Tooltip(
              message: perfil.ayuda,
              child: ActionChip(
                avatar: Icon(icono, size: 18, color: C.acento),
                label: Text(nombre),
                onPressed: () => widget.alEstilo(perfil),
              ),
            ),
        ]),
        const Padding(
          padding: EdgeInsets.only(top: 6),
          child: Text('Suave: largo y discreto · Club: con graves, al compás · Corte rápido: corto y directo.',
              style: estiloDetalle),
        ),
        const SizedBox(height: 10),
        Wrap(spacing: Esp.s, runSpacing: 4, children: [
          FilledButton.tonalIcon(
            onPressed: widget.alProbar,
            icon: const Icon(Icons.play_circle_outline_rounded),
            label: const Text('Probar este cambio'),
          ),
          TextButton(onPressed: widget.alIgualar, child: const Text('Usar este estilo en todos')),
        ]),
        const SizedBox(height: 4),
        InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () => setState(() => _finos = !_finos),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: Row(children: [
              Icon(Icons.tune_rounded, size: 18, color: C.acento),
              const SizedBox(width: 8),
              const Expanded(child: Text('Ajustes finos', style: TextStyle(fontWeight: FontWeight.w800))),
              Icon(_finos ? Icons.expand_less_rounded : Icons.expand_more_rounded, color: C.texto3),
            ]),
          ),
        ),
        if (_finos) _ajustesFinos(context),
      ]),
    );
  }

  Widget _ajustesFinos(BuildContext context) {
    final real = paso.fundidoEfectivo;
    final dur = paso.duracionPista;
    final durSig = siguiente.duracionPista;
    final hayTempos = ritmo?.valido == true && ritmoSiguiente?.valido == true;
    final salidaActual = paso.salida ?? (dur > 0 ? dur - paso.entraEfectivo : 0.0);
    final entradaActual = siguiente.entrada ?? 0.0;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _titulo('Tipo de cambio'),
      _chips<TipoTransicion>(
        TipoTransicion.values, paso.tipo, (t) => t.nombre,
        (t) => alCambiar(paso.copiaCon(tipo: t, graves: t == TipoTransicion.graves)),
        habilitado: (t) => switch (t) {
          TipoTransicion.eco => caps.eco,
          TipoTransicion.filtro || TipoTransicion.graves => caps.filtros,
          _ => true,
        },
      ),
      Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Text(paso.tipo.ayuda, style: estiloDetalle),
      ),
      if (!caps.eco)
        const Padding(
          padding: EdgeInsets.only(top: 4),
          child: Text('El eco no está disponible en el motor de este teléfono.', style: estiloDetalle),
        ),
      if (!caps.filtros)
        const Padding(
          padding: EdgeInsets.only(top: 4),
          child: Text('Aquí no se pueden hacer filtros ni cambios de graves: se usa un fundido.',
              style: estiloDetalle),
        ),
      _titulo('Cuándo y cuánto'),
      Row(children: [
        const Expanded(child: Text('La siguiente empieza cuando falten')),
        Text(_s(paso.entraAntes), style: const TextStyle(fontWeight: FontWeight.w800)),
      ]),
      Slider(
        value: paso.entraAntes.clamp(entraMin, entraMax),
        min: entraMin, max: entraMax, divisions: (entraMax - entraMin).round(),
        label: _s(paso.entraAntes),
        onChanged: (v) => alCambiar(paso.copiaCon(entraAntes: v.roundToDouble(), quitarSalida: true)),
      ),
      Row(children: [
        const Expanded(child: Text('Las dos suenan juntas durante')),
        Text(_s(paso.fundido), style: const TextStyle(fontWeight: FontWeight.w800)),
      ]),
      Slider(
        value: paso.fundido.clamp(fundidoMin, fundidoMax),
        min: fundidoMin, max: fundidoMax, divisions: (fundidoMax - fundidoMin).round(),
        label: _s(paso.fundido),
        onChanged: paso.tipo == TipoTransicion.corte
            ? null
            : (v) => alCambiar(paso.copiaCon(fundido: v.roundToDouble())),
      ),
      if (paso.tipo != TipoTransicion.corte && paso.fundido.round() > real.round())
        Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Text('Dura ${_s(real)} de verdad: no puede ser más largo que lo que queda desde que entra la siguiente.',
              style: estiloDetalle),
        ),
      const Text('Cómo sube y baja el volumen'),
      const SizedBox(height: 6),
      _chips<CurvaFader>(CurvaFader.values, paso.curva, (c) => c.nombre, (c) => alCambiar(paso.copiaCon(curva: c))),
      _titulo('Tempo y compás'),
      SwitchListTile.adaptive(
        contentPadding: EdgeInsets.zero,
        title: const Text('Igualar el tempo'),
        subtitle: Text(
          !caps.tempo
              ? 'No disponible en este teléfono: no se puede acelerar sin cambiar el tono.'
              : hayTempos
                  ? 'La que entra se acerca al tempo de esta (hasta un 8 %) sin cambiar el tono.'
                  : 'Necesita saber el tempo de las dos canciones.',
          style: estiloSecundario,
        ),
        value: paso.igualarTempo && caps.tempo,
        onChanged: caps.tempo ? (v) => alCambiar(paso.copiaCon(igualarTempo: v)) : null,
      ),
      SwitchListTile.adaptive(
        contentPadding: EdgeInsets.zero,
        title: const Text('Entrar en el compás'),
        subtitle: Text(
          ritmo?.valido == true
              ? 'El cambio empieza justo al comenzar un compás de esta canción.'
              : 'Necesita saber el tempo de esta canción.',
          style: estiloSecundario,
        ),
        value: paso.alCompas,
        onChanged: (v) => alCambiar(paso.copiaCon(alCompas: v)),
      ),
      _titulo('Ecualizador de esta canción'),
      for (final (i, nombre) in const ['Graves', 'Medios', 'Agudos'].indexed)
        Row(children: [
          SizedBox(width: 64, child: Text(nombre, style: estiloSecundario)),
          Expanded(
            child: Slider(
              value: paso.eq[i].toDouble().clamp(-12, 12),
              min: -12, max: 12, divisions: 24,
              label: '${paso.eq[i] > 0 ? '+' : ''}${paso.eq[i]} dB',
              onChanged: (v) {
                final nuevo = List<int>.of(paso.eq)..[i] = v.round();
                alCambiar(paso.copiaCon(eq: nuevo));
              },
            ),
          ),
          SizedBox(
            width: 44,
            child: Text('${paso.eq[i] > 0 ? '+' : ''}${paso.eq[i]}',
                textAlign: TextAlign.right, style: estiloDetalle),
          ),
        ]),
      if (paso.tieneEq)
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(
            onPressed: () => alCambiar(paso.copiaCon(eq: const [0, 0, 0])),
            child: const Text('Poner el ecualizador en plano'),
          ),
        ),
      _titulo('Entrada y salida'),
      if (dur > 0) ...[
        Text('Dónde sale esta canción', style: estiloSecundario.copyWith(color: C.texto)),
        const SizedBox(height: 6),
        BarrasEnergia(ritmo: ritmo, duracion: dur, marca: salidaActual, color: C.acento),
        Slider(
          value: salidaActual.clamp(dur * 0.3, max(dur * 0.3 + 1, dur - 2)),
          min: dur * 0.3, max: max(dur * 0.3 + 1, dur - 2),
          label: _MezcladorPaginaState._tiempo(salidaActual),
          onChanged: (v) => alCambiar(paso.copiaCon(salida: v.roundToDouble())),
        ),
        Row(children: [
          Text('Sale en ${_MezcladorPaginaState._tiempo(salidaActual)}', style: estiloDetalle),
          const Spacer(),
          if (ritmo?.valido == true)
            TextButton(
              onPressed: () => alCambiar(paso.copiaCon(
                  salida: alinearAlCompas(salidaActual, ritmo!.bpm, ritmo!.primerTiempo, haciaAtras: true)
                      .clamp(dur * 0.3, dur - 2))),
              child: const Text('Ajustar al compás'),
            ),
          if (paso.salida != null)
            TextButton(onPressed: () => alCambiar(paso.copiaCon(quitarSalida: true)), child: const Text('Automático')),
        ]),
      ],
      if (durSig > 0) ...[
        Text('Por dónde entra la siguiente', style: estiloSecundario.copyWith(color: C.texto)),
        const SizedBox(height: 6),
        BarrasEnergia(ritmo: ritmoSiguiente, duracion: durSig, marca: entradaActual, color: C.violeta),
        Slider(
          value: entradaActual.clamp(0, max(1, min(durSig * 0.6, 150))),
          min: 0, max: max(1, min(durSig * 0.6, 150)),
          label: _MezcladorPaginaState._tiempo(entradaActual),
          onChanged: (v) => widget.alCambiarSiguiente(siguiente.copiaCon(entrada: v.roundToDouble())),
        ),
        Row(children: [
          Text('Entra en ${_MezcladorPaginaState._tiempo(entradaActual)}', style: estiloDetalle),
          const Spacer(),
          if (ritmoSiguiente?.valido == true)
            TextButton(
              onPressed: () => widget.alCambiarSiguiente(siguiente.copiaCon(
                  entrada: alinearAlCompas(entradaActual, ritmoSiguiente!.bpm, ritmoSiguiente!.primerTiempo))),
              child: const Text('Ajustar al compás'),
            ),
          if (siguiente.entrada != null)
            TextButton(
                onPressed: () => widget.alCambiarSiguiente(siguiente.copiaCon(quitarEntrada: true)),
                child: const Text('Automático')),
        ]),
      ],
    ]);
  }
}

/// Un punto de color con el nombre de una cancion (leyenda del dibujo del cambio).
class _Leyenda extends StatelessWidget {
  const _Leyenda({required this.color, required this.texto, this.alDerecha = false});
  final Color color;
  final String texto;
  final bool alDerecha;

  @override
  Widget build(BuildContext context) {
    final punto = Container(width: 8, height: 8, decoration: BoxDecoration(shape: BoxShape.circle, color: color));
    final nombre = ConstrainedBox(
      constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.36),
      child: Text(texto, maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloDetalle),
    );
    return Row(mainAxisSize: MainAxisSize.min, children: [
      if (!alDerecha) ...[punto, const SizedBox(width: 5), nombre] else ...[nombre, const SizedBox(width: 5), punto],
    ]);
  }
}

/// El dibujo de un cambio: el volumen de la que se va (gris, baja) y de la que llega
/// (color, sube), en los segundos finales de la primera. El eje es el tiempo: a la
/// izquierda entra la siguiente y a la derecha acaba esta.
class _GraficoCambio extends StatelessWidget {
  const _GraficoCambio({required this.paso});
  final PasoMezcla paso;

  @override
  Widget build(BuildContext context) => Semantics(
        label: paso.tipo == TipoTransicion.corte
            ? 'Dibujo del cambio: la canción actual corta y entra la siguiente de golpe'
            : 'Dibujo del cambio: durante ${paso.fundidoEfectivo.round()} segundos la canción actual baja '
                'mientras la siguiente sube',
        child: SizedBox(
          height: 46,
          width: double.infinity,
          child: CustomPaint(
            painter: _PintorCambio(
              ventana: paso.entraEfectivo,
              cambio: paso.fundidoEfectivo,
              curva: paso.curva,
              sale: C.texto2,
              entra: C.acento,
              fondo: C.superficie2,
            ),
          ),
        ),
      );
}

class _PintorCambio extends CustomPainter {
  _PintorCambio({
    required this.ventana,
    required this.cambio,
    required this.curva,
    required this.sale,
    required this.entra,
    required this.fondo,
  });
  final double ventana; // segundos que se ven: desde que entra la siguiente hasta que acaba esta
  final double cambio; // lo que dura el cambio dentro de esa ventana
  final CurvaFader curva;
  final Color sale;
  final Color entra;
  final Color fondo;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRRect(RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(10)), Paint()..color = fondo);
    final v = ventana <= 0 ? 1.0 : ventana;
    final f = cambio.clamp(0.0, v);
    const pad = 6.0;
    double x(double t) => pad + (t / v) * (size.width - 2 * pad);
    double y(double g) => pad + (1 - g) * (size.height - 2 * pad);
    const pasos = 36;
    final bajada = Path()..moveTo(x(0), y(1));
    final subida = Path()..moveTo(x(0), y(0));
    for (var i = 0; i <= pasos; i++) {
      final a = i / pasos;
      final t = f * a;
      bajada.lineTo(x(t), y(ganancia(curva, a, entrante: false)));
      subida.lineTo(x(t), y(ganancia(curva, a, entrante: true)));
    }
    bajada.lineTo(x(v), y(0));
    subida.lineTo(x(v), y(1));
    // lo que suena de la que llega, como una sombra suave bajo su linea
    final area = Path.from(subida)
      ..lineTo(x(v), y(0))
      ..lineTo(x(0), y(0))
      ..close();
    canvas.drawPath(area, Paint()..color = entra.withValues(alpha: 0.14));
    Paint linea(Color c) => Paint()
      ..color = c
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    canvas.drawPath(bajada, linea(sale));
    canvas.drawPath(subida, linea(entra));
  }

  @override
  bool shouldRepaint(_PintorCambio o) =>
      o.ventana != ventana || o.cambio != cambio || o.curva != curva || o.sale != sale || o.entra != entra;
}

/// La silueta de energia de una cancion (lo que se analizo) con una marca donde
/// entra o sale. Fuera del tramo analizado se dibuja una linea suave.
class BarrasEnergia extends StatelessWidget {
  const BarrasEnergia({super.key, required this.ritmo, required this.duracion, required this.marca, required this.color});
  final AnalisisRitmo? ritmo;
  final double duracion;
  final double marca;
  final Color color;

  @override
  Widget build(BuildContext context) => Semantics(
        label: ritmo == null || ritmo!.barras.isEmpty
            ? 'Sin silueta de energía: analiza el ritmo para verla'
            : 'Silueta de energía de la canción',
        child: SizedBox(
          height: 52,
          width: double.infinity,
          child: CustomPaint(painter: _PintorBarras(ritmo, duracion, marca, color, C.superficie2, C.texto3)),
        ),
      );
}

class _PintorBarras extends CustomPainter {
  _PintorBarras(this.ritmo, this.duracion, this.marca, this.color, this.fondo, this.tenue);
  final AnalisisRitmo? ritmo;
  final double duracion;
  final double marca;
  final Color color;
  final Color fondo;
  final Color tenue;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRRect(RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(8)), Paint()..color = fondo);
    final r = ritmo;
    final dur = duracion > 0 ? duracion : 1;
    if (r != null && r.barras.isNotEmpty) {
      final x0 = (r.inicioAnalizado / dur).clamp(0.0, 1.0) * size.width;
      final x1 = ((r.inicioAnalizado + r.duracionAnalizada) / dur).clamp(0.0, 1.0) * size.width;
      final ancho = max(1.0, x1 - x0);
      final w = ancho / r.barras.length;
      final p = Paint()..color = color.withValues(alpha: 0.75);
      for (var i = 0; i < r.barras.length; i++) {
        final h = max(2.0, r.barras[i] * (size.height - 10));
        canvas.drawRRect(
            RRect.fromRectAndRadius(
                Rect.fromLTWH(x0 + i * w + 0.5, (size.height - h) / 2, max(1.0, w - 1.5), h), const Radius.circular(1.5)),
            p);
      }
    }
    // la linea tenue de toda la cancion
    canvas.drawLine(Offset(6, size.height - 4), Offset(size.width - 6, size.height - 4),
        Paint()..color = tenue.withValues(alpha: 0.5)..strokeWidth = 1);
    final x = (marca / dur).clamp(0.0, 1.0) * size.width;
    canvas.drawLine(Offset(x, 0), Offset(x, size.height), Paint()..color = Colors.white..strokeWidth = 2);
    canvas.drawCircle(Offset(x, 5), 4, Paint()..color = Colors.white);
  }

  @override
  bool shouldRepaint(_PintorBarras o) =>
      o.ritmo != ritmo || o.marca != marca || o.duracion != duracion || o.color != color;
}

/// Escribir el tempo o marcarlo con los dedos al ritmo de la musica.
class _DialogoTempo extends StatefulWidget {
  const _DialogoTempo({this.inicial});
  final double? inicial;

  @override
  State<_DialogoTempo> createState() => _DialogoTempoState();
}

class _DialogoTempoState extends State<_DialogoTempo> {
  late final TextEditingController _c =
      TextEditingController(text: widget.inicial == null ? '' : widget.inicial!.round().toString());
  final List<int> _toques = [];
  String? _error;

  void _toque() {
    final ahora = DateTime.now().millisecondsSinceEpoch;
    if (_toques.isNotEmpty && ahora - _toques.last > 2500) _toques.clear();
    _toques.add(ahora);
    final b = bpmDeToques(_toques);
    setState(() {
      if (b != null) _c.text = b.round().toString();
    });
  }

  void _guardar() {
    final v = double.tryParse(_c.text.trim().replaceAll(',', '.'));
    if (v == null || v < 40 || v > 240) {
      setState(() => _error = 'Escribe un tempo entre 40 y 240.');
      return;
    }
    Navigator.pop(context, v);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        backgroundColor: C.superficie2,
        title: const Text('Tempo de la canción'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(
            controller: _c,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(hintText: 'Pulsos por minuto', suffixText: 'BPM', errorText: _error),
          ),
          const SizedBox(height: 14),
          const Text('O toca el botón al ritmo de la música (cuatro toques o más):', style: estiloSecundario),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: FilledButton.tonalIcon(
              onPressed: _toque,
              icon: const Icon(Icons.touch_app_rounded),
              label: Text(_toques.length < 4 ? 'Toca aquí (${_toques.length})' : 'Sigue tocando para afinar'),
              style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 18)),
            ),
          ),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
          FilledButton(onPressed: _guardar, child: const Text('Guardar')),
        ],
      );
}

// ---------------------------------------------------------------- elegir canciones

/// De donde se sacan las canciones: la cola, Tus me gusta o una lista.
class _HojaElegir extends StatefulWidget {
  const _HojaElegir({this.fuenteInicial = 'cola'});

  /// cola | gusta | lista
  final String fuenteInicial;

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
    _cambiar(widget.fuenteInicial);
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
                onPressed: _marcadas.isEmpty ? null : () => Navigator.pop(context, _marcadas.values.toList()),
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
