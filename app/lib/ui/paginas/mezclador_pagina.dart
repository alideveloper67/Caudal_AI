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
import 'inicio.dart' show espacioInferior;

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

  /// Analiza el ritmo de las canciones que aun no lo tienen (con barra de avance).
  Future<void> _analizarTodo() async {
    final a = _analizador;
    final s = Caudal.leer(context);
    if (a == null || _analizando) return;
    if (kIsWeb) {
      s.avisar('El análisis de ritmo no está disponible en el navegador. Escribe el tempo a mano.');
      return;
    }
    final pendientes = [
      for (final it in _items)
        if (a.de('${it.paso.pista['clave']}')?.valido != true) it.paso.pista
    ];
    if (pendientes.isEmpty) return;
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
            child: Text('Ordena las canciones por tempo y energía y pone un cambio a cada paso. Después puedes ajustarlo a mano.',
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
    final total = duracionDelSet(_pasos);
    final encajes = encajesDelSet(_pasos, _ritmo);
    final caps = _analizador == null ? const _Capacidades() : _capacidades;
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
            if (n >= 2) ...[
              const SizedBox(height: Esp.s),
              Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
                ActionChip(
                  avatar: Icon(Icons.auto_awesome_rounded, size: 18, color: C.acento),
                  label: const Text('Mezclar como un DJ'),
                  onPressed: _analizando ? null : _elegirPerfil,
                ),
                ActionChip(
                  avatar: Icon(Icons.sort_rounded, size: 18, color: C.acento),
                  label: const Text('Ordenar mi set'),
                  onPressed: _analizando ? null : _ordenar,
                ),
                ActionChip(
                  avatar: Icon(Icons.graphic_eq_rounded, size: 18, color: C.acento),
                  label: const Text('Analizar el ritmo'),
                  onPressed: _analizando ? null : _analizarTodo,
                ),
              ]),
            ],
            if (_analizando) ...[
              const SizedBox(height: Esp.s),
              LinearProgressIndicator(value: _faltan == 0 ? null : _hechas / _faltan, color: C.acento,
                  backgroundColor: C.superficie3),
              const SizedBox(height: 4),
              Text('Escuchando el ritmo… $_hechas de $_faltan', style: estiloDetalle),
            ],
            if (n >= 2 && !caps.tempo)
              const Padding(
                padding: EdgeInsets.only(top: Esp.s),
                child: Text('En este teléfono no se puede acercar el tempo de las canciones sin cambiarles el tono: '
                    'se mezclan a su propio tempo.', style: estiloDetalle),
              ),
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
                          ritmo: _ritmoDe(it.paso),
                          alTempo: () => _editarTempo(it),
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
                            siguiente: _items[i + 1].paso,
                            ritmo: _ritmoDe(it.paso),
                            ritmoSiguiente: _ritmoDe(_items[i + 1].paso),
                            encaje: encajes[i],
                            caps: caps,
                            abierto: _abierto == it.id,
                            alAbrir: () => setState(() => _abierto = _abierto == it.id ? null : it.id),
                            alCambiar: (p) => setState(() => it.paso = p),
                            alCambiarSiguiente: (p) => setState(() => _items[i + 1].paso = p),
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

/// La tarjeta de una cancion del set, con su tempo.
class _FilaPaso extends StatelessWidget {
  const _FilaPaso({
    required this.indice,
    required this.paso,
    required this.ritmo,
    required this.alTempo,
    required this.alQuitar,
    required this.manija,
  });
  final int indice;
  final PasoMezcla paso;
  final AnalisisRitmo? ritmo;
  final VoidCallback alTempo;
  final VoidCallback alQuitar;
  final Widget manija;

  @override
  Widget build(BuildContext context) {
    final p = paso.pista;
    final dur = paso.duracionPista;
    final bpm = ritmo != null && ritmo!.valido ? ritmo : null;
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
            Row(children: [
              Expanded(
                child: Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: estiloSecundario),
              ),
              if (dur > 0) Text(_MezcladorPaginaState._tiempo(dur), style: estiloDetalle),
            ]),
            const SizedBox(height: 3),
            // tempo y energia: tocar el tempo para escribirlo o marcarlo con los dedos
            InkWell(
              borderRadius: BorderRadius.circular(8),
              onTap: alTempo,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 2),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.speed_rounded, size: 14, color: bpm == null ? C.texto3 : C.acento),
                  const SizedBox(width: 4),
                  Flexible(
                    child: Text(bpm == null ? 'Tempo sin saber' : '${bpm.bpm.round()} BPM',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700,
                            color: bpm == null ? C.texto3 : C.texto)),
                  ),
                  if (bpm != null) ...[
                    const SizedBox(width: 8),
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
                  ],
                ]),
              ),
            ),
          ]),
        ),
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

/// El cambio entre una cancion y la siguiente: un resumen (con color segun lo bien
/// que encajan los tempos) que al tocarlo abre los ajustes del paso.
class _Cambio extends StatelessWidget {
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
  final VoidCallback alProbar;
  final VoidCallback alIgualar;

  static String _s(double v) => '${v.round()} s';

  Color get _colorEncaje => switch (encaje) {
        Encaje.bueno => C.exito,
        Encaje.regular => const Color(0xFFF5C542),
        Encaje.choca => C.error,
        Encaje.desconocido => C.texto3,
      };

  String get _textoEncaje => switch (encaje) {
        Encaje.bueno => 'Tempos parecidos: encajan bien',
        Encaje.regular => 'Tempos algo distintos',
        Encaje.choca => 'Tempos que chocan: mejor un filtro o un fundido largo',
        Encaje.desconocido => 'Sin tempo: se mezcla por duración',
      };

  @override
  Widget build(BuildContext context) {
    final real = paso.fundidoEfectivo;
    final resumen = 'Entra la siguiente a ${_s(paso.entraEfectivo)} del final · '
        '${paso.tipo.nombre} de ${_s(real)}';
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
                Tooltip(
                  message: _textoEncaje,
                  child: Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(shape: BoxShape.circle, color: _colorEncaje),
                  ),
                ),
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

  Widget _panel(BuildContext context) {
    final real = paso.fundidoEfectivo;
    final dur = paso.duracionPista;
    final durSig = siguiente.duracionPista;
    final hayTempos = ritmo?.valido == true && ritmoSiguiente?.valido == true;
    final salidaActual = paso.salida ?? (dur > 0 ? dur - paso.entraEfectivo : 0.0);
    final entradaActual = siguiente.entrada ?? 0.0;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(_textoEncaje, style: TextStyle(fontSize: 12.5, color: _colorEncaje, fontWeight: FontWeight.w700)),
        _titulo('Cómo cambia'),
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
          const Expanded(child: Text('La siguiente entra cuando falten')),
          Text(_s(paso.entraAntes), style: const TextStyle(fontWeight: FontWeight.w800)),
        ]),
        Slider(
          value: paso.entraAntes.clamp(entraMin, entraMax),
          min: entraMin, max: entraMax, divisions: (entraMax - entraMin).round(),
          label: _s(paso.entraAntes),
          onChanged: (v) => alCambiar(paso.copiaCon(entraAntes: v.roundToDouble(), quitarSalida: true)),
        ),
        Row(children: [
          const Expanded(child: Text('El cambio dura')),
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
        const Text('Forma del volumen'),
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
            onChanged: (v) => alCambiarSiguiente(siguiente.copiaCon(entrada: v.roundToDouble())),
          ),
          Row(children: [
            Text('Entra en ${_MezcladorPaginaState._tiempo(entradaActual)}', style: estiloDetalle),
            const Spacer(),
            if (ritmoSiguiente?.valido == true)
              TextButton(
                onPressed: () => alCambiarSiguiente(siguiente.copiaCon(
                    entrada: alinearAlCompas(entradaActual, ritmoSiguiente!.bpm, ritmoSiguiente!.primerTiempo))),
                child: const Text('Ajustar al compás'),
              ),
            if (siguiente.entrada != null)
              TextButton(
                  onPressed: () => alCambiarSiguiente(siguiente.copiaCon(quitarEntrada: true)),
                  child: const Text('Automático')),
          ]),
        ],
        const SizedBox(height: 6),
        Wrap(spacing: Esp.s, children: [
          FilledButton.tonalIcon(
            onPressed: alProbar,
            icon: const Icon(Icons.play_circle_outline_rounded),
            label: const Text('Probar este cambio'),
          ),
          TextButton(onPressed: alIgualar, child: const Text('Igual en todos')),
        ]),
      ]),
    );
  }
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
