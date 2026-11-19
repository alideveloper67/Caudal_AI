// «Enriquecer» una lista propia: una hoja con canciones nuevas, parecidas a las
// de la lista y de sus mismos artistas. Se escucha un momento cada una y se
// eligen las que entran. La logica vive en nucleo/enriquecer.dart.

import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/enriquecer.dart';
import '../../reproduccion/reproductor.dart' show EstadoRepro;
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';

/// Abre la hoja para la lista [listaId] (con sus [pistas] actuales).
Future<void> mostrarHojaEnriquecer(BuildContext context,
    {required int listaId, required String nombre, required List<Json> pistas}) {
  return showModalBottomSheet<void>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => FractionallySizedBox(
      heightFactor: 0.86,
      child: HojaEnriquecer(listaId: listaId, nombre: nombre, pistas: pistas),
    ),
  );
}

enum _Fase { cargando, listo, vacio, error }

class HojaEnriquecer extends StatefulWidget {
  const HojaEnriquecer({super.key, required this.listaId, required this.nombre, required this.pistas});
  final int listaId;
  final String nombre;
  final List<Json> pistas;

  @override
  State<HojaEnriquecer> createState() => _HojaEnriquecerState();
}

class _HojaEnriquecerState extends State<HojaEnriquecer> {
  static const _segundosDePrueba = 20;

  _Fase _fase = _Fase.cargando;
  List<Sugerencia> _sugerencias = [];
  final Set<String> _elegidas = {};
  String _mensaje = '';
  int _hechas = 0;
  int _total = 1;
  int _vuelta = 0;
  bool _cerrada = false;
  bool _anadiendo = false;
  Timer? _fin;
  String? _sonandoPrueba;
  late final Servicios _s;

  @override
  void initState() {
    super.initState();
    _s = Caudal.leer(context);
    _buscar();
  }

  @override
  void dispose() {
    _cerrada = true;
    _fin?.cancel();
    _pararPrueba();
    super.dispose();
  }

  Future<void> _buscar() async {
    final vuelta = ++_vuelta;
    setState(() {
      _fase = _Fase.cargando;
      _hechas = 0;
      _total = 1;
      _elegidas.clear();
    });
    try {
      final r = await Enriquecer.sugerir(
        widget.pistas,
        progreso: (h, t) {
          if (!_cerrada && vuelta == _vuelta) setState(() {
            _hechas = h;
            _total = t;
          });
        },
        cancelado: () => _cerrada || vuelta != _vuelta,
      );
      if (_cerrada || vuelta != _vuelta) return;
      setState(() {
        _sugerencias = r;
        _fase = r.isEmpty ? _Fase.vacio : _Fase.listo;
      });
    } catch (e) {
      if (_cerrada || vuelta != _vuelta) return;
      setState(() {
        _mensaje = e is EnriquecerError ? e.mensaje : explicarError(e);
        _fase = _Fase.error;
      });
    }
  }

  // ------------------------------------------------------------ escuchar un momento

  bool _esPrueba(Servicios s, String vid) =>
      s.reproductor.contexto?['tipo'] == 'vista_previa' && '${s.reproductor.actual?['video_id']}' == vid;

  void _pararPrueba() {
    _fin?.cancel();
    final id = _sonandoPrueba;
    if (id == null) return;
    _sonandoPrueba = null;
    try {
      final r = _s.reproductor;
      if (r.contexto?['tipo'] == 'vista_previa' && '${r.actual?['video_id']}' == id) r.pausar();
    } catch (_) {/* la hoja ya se cerro */}
  }

  Future<void> _escuchar(Servicios s, Sugerencia sug) async {
    final vid = sug.videoId;
    if (_esPrueba(s, vid) && s.reproductor.estado == EstadoRepro.sonando) {
      _pararPrueba();
      return;
    }
    _fin?.cancel();
    _sonandoPrueba = vid;
    final dur = (sug.pista['duracion'] as num?)?.toInt() ?? 0;
    // mitad de la primera parte: suele ser lo mas reconocible
    final desde = dur > 90 ? Duration(seconds: (dur * 0.25).round().clamp(20, 60)) : Duration.zero;
    await s.reproductor.reproducirLista([sug.pista],
        contexto: {'tipo': 'vista_previa', 'id': vid, 'titulo': 'Vista previa'}, modo: 'audio', desde: desde);
    _fin = Timer(const Duration(seconds: _segundosDePrueba), () {
      if (!_cerrada && _sonandoPrueba == vid) _pararPrueba();
    });
  }

  // ------------------------------------------------------------ anadir

  Future<void> _anadir(List<Sugerencia> cuales) async {
    if (_anadiendo || cuales.isEmpty) return;
    final s = Caudal.leer(context);
    final nav = Navigator.of(context);
    setState(() => _anadiendo = true);
    _pararPrueba();
    try {
      final entraron = await s.coleccion
          .agregarAListaDetalle(widget.listaId, [for (final c in cuales) c.pista]);
      if (entraron.isEmpty) {
        s.avisar('Esas canciones ya estaban en la lista');
      } else {
        s.avisar(
            entraron.length == 1
                ? 'Añadida 1 canción a «${widget.nombre}»'
                : 'Añadidas ${entraron.length} canciones a «${widget.nombre}»',
            deshacer: () => s.coleccion.quitarVariasDeLista(widget.listaId, entraron));
      }
      if (nav.mounted) nav.pop();
    } catch (_) {
      if (mounted) setState(() => _anadiendo = false);
      s.avisar('No se pudieron añadir las canciones. Inténtalo otra vez.');
    }
  }

  // ------------------------------------------------------------ pintar

  @override
  Widget build(BuildContext context) {
    final Widget cuerpo = switch (_fase) {
      _Fase.cargando => _cargando(),
      _Fase.error => Vacio(
          icono: Icons.wifi_off_rounded, titulo: 'No se pudo enriquecer', error: true,
          texto: _mensaje, alAccion: _buscar),
      _Fase.vacio => Vacio(
          icono: Icons.search_off_rounded, titulo: 'Nada nuevo por ahora',
          texto: 'No encontramos canciones nuevas que sumar a esta lista. Prueba más tarde o con otras canciones.',
          alAccion: _buscar, textoAccion: 'Buscar de nuevo'),
      _Fase.listo => _lista(),
    };
    return SafeArea(
      top: false,
      child: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, 8),
          child: Row(children: [
            Icon(Icons.auto_awesome_rounded, color: C.acento),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Enriquecer la lista', style: estiloTituloSeccion),
                Text(
                  _fase == _Fase.listo
                      ? '${_sugerencias.length} sugerencias · el ▶ pausa lo que suena'
                      : 'Canciones nuevas, parecidas a las de «${widget.nombre}»',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
              ]),
            ),
          ]),
        ),
        Expanded(child: AnimatedSwitcher(duration: Mov.normal, child: KeyedSubtree(key: ValueKey(_fase), child: cuerpo))),
        if (_fase == _Fase.listo) _pie(),
      ]),
    );
  }

  Widget _cargando() {
    final p = _total == 0 ? 0.0 : _hechas / _total;
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: Esp.xxl),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
                value: _hechas == 0 ? null : p, minHeight: 6, color: C.acento, backgroundColor: C.superficie3),
          ),
          const SizedBox(height: 16),
          const Text('Buscando canciones para ti…', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text('Mirando las de tu lista y a sus artistas', style: estiloSecundario),
        ]),
      ),
    );
  }

  Widget _lista() {
    final s = Caudal.of(context);
    return ListView.builder(
      itemCount: _sugerencias.length,
      itemExtent: 64,
      cacheExtent: 400,
      itemBuilder: (_, i) {
        final sug = _sugerencias[i];
        final p = sug.pista;
        final vid = sug.videoId;
        final marcada = _elegidas.contains(vid);
        return InkWell(
          onTap: () => setState(() => marcada ? _elegidas.remove(vid) : _elegidas.add(vid)),
          child: Padding(
            padding: const EdgeInsets.only(left: Esp.lado, right: 4),
            child: Row(children: [
              Portada(url: '${p['miniatura'] ?? ''}', lado: 44, radio: 4),
              const SizedBox(width: 12),
              Expanded(
                child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                  Text('${p['titulo']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                ]),
              ),
              ListenableBuilder(
                listenable: s.reproductor,
                builder: (_, _) {
                  final suena = _esPrueba(s, vid) && s.reproductor.estado == EstadoRepro.sonando;
                  return IconButton(
                    tooltip: suena ? 'Parar' : 'Escuchar un momento',
                    icon: Icon(suena ? Icons.pause_circle_filled_rounded : Icons.play_circle_outline_rounded,
                        size: 30, color: suena ? C.acento : C.texto2),
                    onPressed: () => _escuchar(s, sug),
                  );
                },
              ),
              Checkbox(
                value: marcada,
                activeColor: C.acento,
                onChanged: (v) => setState(() => v == true ? _elegidas.add(vid) : _elegidas.remove(vid)),
              ),
            ]),
          ),
        );
      },
    );
  }

  Widget _pie() {
    final n = _elegidas.length;
    return Container(
      padding: const EdgeInsets.fromLTRB(Esp.lado, 10, Esp.lado, 6),
      decoration: BoxDecoration(border: Border(top: BorderSide(color: C.superficie3))),
      child: Row(children: [
        Expanded(
          child: OutlinedButton(
            onPressed: _anadiendo || n == 0
                ? null
                : () => _anadir([for (final x in _sugerencias) if (_elegidas.contains(x.videoId)) x]),
            style: OutlinedButton.styleFrom(shape: const StadiumBorder(), padding: const EdgeInsets.symmetric(vertical: 13)),
            child: Text(n == 0 ? 'Añadir seleccionadas' : 'Añadir seleccionadas ($n)'),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: FilledButton(
            onPressed: _anadiendo ? null : () => _anadir(_sugerencias),
            style: FilledButton.styleFrom(
                backgroundColor: C.texto, foregroundColor: C.fondo, shape: const StadiumBorder(),
                padding: const EdgeInsets.symmetric(vertical: 13)),
            child: Text(_anadiendo ? 'Añadiendo…' : 'Añadir todas'),
          ),
        ),
      ]),
    );
  }
}
