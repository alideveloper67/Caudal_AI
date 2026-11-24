import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/letras_cache.dart';
import '../../reproduccion/frenos.dart';
import '../../reproduccion/reproductor.dart';
import '../comunes.dart';
import '../plataforma.dart' show Haptico;
import '../servicios.dart';
import '../tema.dart';

/// Lo que hay que mover la letra para que el verso de [verso] ms empiece donde se tocó. [posicion] es la
/// del reproductor, que llega a saltos de [pasoPosicion]; el dedo tarda un poco en reaccionar.
int desfaseAlTocar(int verso, Duration posicion) =>
    verso - (posicion.inMilliseconds + pasoPosicion.inMilliseconds ~/ 2 - 150);

/// «Corregir la letra»: ponerla a tiempo (a pasos o tocando cuando empieza un verso) o cambiarla.
Future<void> mostrarCorregirLetra(BuildContext context, Json pista, Map<String, dynamic>? letra) =>
    showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      showDragHandle: true,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (_) => _HojaCorregir(pista: pista, letra: letra),
    );

class _HojaCorregir extends StatefulWidget {
  const _HojaCorregir({required this.pista, required this.letra});
  final Json pista;
  final Map<String, dynamic>? letra;

  @override
  State<_HojaCorregir> createState() => _HojaCorregirState();
}

class _HojaCorregirState extends State<_HojaCorregir> {
  late final String _clave = '${widget.pista['clave']}';
  late Map<String, dynamic>? _letra = widget.letra;
  int _verso = -1;

  /// Los versos con tiempo: los de la letra o, si los suyos no valen, los de otra grabación.
  List<(int, String)> get _versos {
    final con = lineasConTiempo(_letra);
    final l = con.isNotEmpty ? con : lineasConTiempo({'lineas': _letra?['ajustables']});
    return [for (final x in l) if (x.$2.replaceAll('♪', '').trim().isNotEmpty) x];
  }

  bool get _sinAjustar => lineasConTiempo(_letra).isEmpty;

  bool _suena(Reproductor r) => '${r.actual?['clave']}' == _clave;

  void _mover(int ms) => LetrasCache.i.ponerDesfase(_clave, LetrasCache.i.desfasePropio(_clave) + ms);

  void _ahora(Reproductor r, int i) {
    final v = _versos[i];
    if (_sinAjustar) {
      final nueva = {...?_letra, 'lineas': _letra!['ajustables'], 'sincronizada': true}..remove('ajustables');
      LetrasCache.i.elegir(_clave, nueva);
      _letra = LetrasCache.i.de(_clave) ?? nueva;
    }
    LetrasCache.i.ponerDesfase(_clave, desfaseAlTocar(v.$1, r.posicion.value) - LetrasCache.i.desfaseGeneral);
    Haptico.exito();
    setState(() => _verso = -1); // vuelve a seguir a la música
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final r = s.reproductor;
    return ListenableBuilder(
      listenable: Listenable.merge([LetrasCache.i.cambios, r]),
      builder: (context, _) {
        final versos = _versos;
        final ms = LetrasCache.i.desfasePropio(_clave);
        final general = LetrasCache.i.desfaseGeneral;
        String seg(int x) => '${x > 0 ? '+' : x < 0 ? '−' : ''}${(x.abs() / 1000).toStringAsFixed(1).replaceAll('.', ',')} s';
        return SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 18),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Text('Corregir la letra', style: estiloTituloSeccion),
              const SizedBox(height: 2),
              Text('${widget.pista['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
              if (versos.isNotEmpty && _suena(r)) ...[
                const SizedBox(height: 16),
                _Marcar(
                  r: r,
                  versos: versos,
                  elegido: _verso,
                  sinAjustar: _sinAjustar,
                  desfase: () => LetrasCache.i.desfase(_clave),
                  alElegir: (i) => setState(() => _verso = i),
                  alTocar: (i) => _ahora(r, i),
                ),
              ],
              if (!_sinAjustar) ...[
                const SizedBox(height: 18),
                const Text('A pasos', style: TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                Row(children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => _mover(-500),
                      onLongPress: () => _mover(-100),
                      style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 8)),
                      child: const FittedBox(fit: BoxFit.scaleDown, child: Text('Atrasar 0,5 s')),
                    ),
                  ),
                  SizedBox(
                    width: 72,
                    child: Text(ms == 0 ? 'Normal' : seg(ms),
                        textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w900)),
                  ),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => _mover(500),
                      onLongPress: () => _mover(100),
                      style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 8)),
                      child: const FittedBox(fit: BoxFit.scaleDown, child: Text('Adelantar 0,5 s')),
                    ),
                  ),
                ]),
                const SizedBox(height: 6),
                const Text('Si la letra sale antes que la voz, atrásala. Mantén pulsado para mover 0,1 s.',
                    style: estiloSecundario),
                Wrap(spacing: 4, children: [
                  if (ms != 0)
                    TextButton(onPressed: () => LetrasCache.i.ponerDesfase(_clave, 0), child: const Text('Volver a lo normal')),
                  if (ms != 0 && ms.abs() <= 2000)
                    TextButton(
                      onPressed: () {
                        LetrasCache.i.ponerDesfaseGeneral(general + ms);
                        LetrasCache.i.ponerDesfase(_clave, 0);
                        s.avisar('Se aplicará a todas las canciones');
                      },
                      child: const Text('Usar en todas (auriculares Bluetooth)'),
                    ),
                  if (general != 0)
                    TextButton(
                      onPressed: () => LetrasCache.i.ponerDesfaseGeneral(0),
                      child: Text('Quitar el ajuste de todas (${seg(general)})'),
                    ),
                ]),
              ],
              const Divider(height: 28),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(Icons.lyrics_outlined, color: C.acento),
                title: const Text('Esta no es la letra', style: TextStyle(fontWeight: FontWeight.w700)),
                subtitle: const Text('Elige otra o búscala por su nombre.', style: estiloSecundario),
                onTap: () async {
                  final elegida = await elegirOtraLetra(context, widget.pista);
                  if (elegida == null || !context.mounted) return;
                  Navigator.pop(context);
                  s.avisar('Letra cambiada');
                },
              ),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.refresh_rounded, color: C.texto2),
                title: const Text('Buscar la letra otra vez', style: TextStyle(fontWeight: FontWeight.w700)),
                subtitle: const Text('Quita lo que cambiaste y vuelve a empezar.', style: estiloSecundario),
                onTap: () async {
                  LetrasCache.i.olvidar(_clave);
                  Navigator.pop(context);
                  await LetrasCache.i.obtener(widget.pista);
                  LetrasCache.i.cambios.avisar();
                },
              ),
            ]),
          ),
        );
      },
    );
  }
}

/// «Toca cuando empiece este verso»: la forma más rápida de ponerla a tiempo de oído.
class _Marcar extends StatelessWidget {
  const _Marcar({
    required this.r,
    required this.versos,
    required this.elegido,
    required this.sinAjustar,
    required this.desfase,
    required this.alElegir,
    required this.alTocar,
  });

  final Reproductor r;
  final List<(int, String)> versos;

  /// El verso elegido (-1: el que viene, según la música).
  final int elegido;
  final bool sinAjustar;
  final int Function() desfase;
  final ValueChanged<int> alElegir, alTocar;

  @override
  Widget build(BuildContext context) => ValueListenableBuilder<Duration>(
        valueListenable: r.posicion,
        builder: (context, pos, _) {
          var i = elegido;
          if (i < 0) {
            final ms = pos.inMilliseconds + (sinAjustar ? 0 : desfase());
            i = versos.indexWhere((v) => v.$1 > ms);
            if (i < 0) i = versos.length - 1;
          }
          i = i.clamp(0, versos.length - 1);
          return Container(
            padding: const EdgeInsets.fromLTRB(8, 12, 8, 12),
            decoration: BoxDecoration(color: C.superficie3, borderRadius: BorderRadius.circular(14)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Text(
                    sinAjustar
                        ? 'Los tiempos de esta letra son de otra versión. Escucha y toca el botón justo cuando empiece el verso.'
                        : 'Toca el botón justo cuando empiece a cantarse este verso.',
                    style: estiloSecundario),
              ),
              const SizedBox(height: 6),
              Row(children: [
                IconButton(
                  tooltip: 'Verso anterior',
                  icon: const Icon(Icons.keyboard_arrow_up_rounded),
                  onPressed: i > 0 ? () => alElegir(i - 1) : null,
                ),
                Expanded(
                  child: Text('«${versos[i].$2.trim()}»',
                      textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                ),
                IconButton(
                  tooltip: 'Verso siguiente',
                  icon: const Icon(Icons.keyboard_arrow_down_rounded),
                  onPressed: i < versos.length - 1 ? () => alElegir(i + 1) : null,
                ),
              ]),
              const SizedBox(height: 8),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: FilledButton.icon(
                  onPressed: () => alTocar(i),
                  icon: const Icon(Icons.touch_app_rounded),
                  label: const Text('Empieza ahora'),
                ),
              ),
            ]),
          );
        },
      );
}

/// Otras letras para la canción, con buscador y vista previa. Devuelve la elegida (ya guardada).
Future<Map<String, dynamic>?> elegirOtraLetra(BuildContext context, Json pista) =>
    showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      showDragHandle: true,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (_) => _HojaOtraLetra(pista: pista),
    );

class _HojaOtraLetra extends StatefulWidget {
  const _HojaOtraLetra({required this.pista});
  final Json pista;

  @override
  State<_HojaOtraLetra> createState() => _HojaOtraLetraState();
}

class _HojaOtraLetraState extends State<_HojaOtraLetra> {
  final _campo = TextEditingController();
  List<Map<String, dynamic>>? _lista;
  bool _fallo = false;
  int _vuelta = 0, _abierta = -1;

  @override
  void initState() {
    super.initState();
    unawaited(_cargar());
  }

  @override
  void dispose() {
    _campo.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    final v = ++_vuelta;
    setState(() {
      _lista = null;
      _fallo = false;
      _abierta = -1;
    });
    try {
      final l = await Catalogo.letrasAlternativas(widget.pista,
          duracion: LetrasCache.i.duracionReal?.call('${widget.pista['clave']}'), buscar: _campo.text);
      if (mounted && v == _vuelta) setState(() => _lista = l);
    } catch (_) {
      if (mounted && v == _vuelta) setState(() => _fallo = true);
    }
  }

  void _usar(Map<String, dynamic> l) {
    final clave = '${widget.pista['clave']}';
    LetrasCache.i.ponerDesfase(clave, 0); // el ajuste era de la otra letra
    LetrasCache.i.elegir(clave, {
      'lineas': l['lineas'], 'texto': l['texto'], 'fuente': l['fuente'], 'sincronizada': l['sincronizada'],
    });
    Navigator.pop(context, l);
  }

  static String _reloj(int s) => s <= 0 ? '' : '${s ~/ 60}:${(s % 60).toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final lista = _lista;
    final dur = (widget.pista['duracion'] as num?)?.toInt() ?? 0;
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.78,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Text('Elegir otra letra', style: estiloTituloSeccion),
              const SizedBox(height: 2),
              Text('Tu canción dura ${_reloj(dur)}: la que dure parecido irá mejor a tiempo.', style: estiloSecundario),
              const SizedBox(height: 10),
              TextField(
                controller: _campo,
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _cargar(),
                decoration: InputDecoration(
                  hintText: 'Canción y artista',
                  prefixIcon: const Icon(Icons.search_rounded, color: C.texto2),
                  suffixIcon: IconButton(
                      tooltip: 'Buscar', icon: const Icon(Icons.arrow_forward_rounded), onPressed: _cargar),
                ),
              ),
            ]),
          ),
          Expanded(
            child: _fallo
                ? Vacio(icono: Icons.wifi_off_rounded, titulo: 'No se pudo buscar', error: true,
                    texto: 'Revisa tu conexión y vuelve a intentarlo.', alAccion: _cargar)
                : lista == null
                    ? const Center(child: CircularProgressIndicator())
                    : lista.isEmpty
                        ? const Vacio(icono: Icons.lyrics_outlined, titulo: 'No encontré otra letra',
                            texto: 'Prueba a escribir el nombre de la canción y del artista.')
                        : ListView.builder(
                            itemCount: lista.length,
                            itemBuilder: (_, i) => _fila(lista[i], i),
                          ),
          ),
        ]),
      ),
    );
  }

  Widget _fila(Map<String, dynamic> l, int i) {
    final abierta = i == _abierta;
    final texto = '${l['texto']}'.trim();
    final con = l['sincronizada'] == true;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20),
        title: Text('${l['titulo']}', maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text(
            [
              '${l['artista']}', _reloj(l['duracion'] as int), con ? 'sigue la música' : 'sin tiempos',
            ].where((x) => x.isNotEmpty).join(' · '),
            maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
        trailing: Icon(abierta ? Icons.expand_less_rounded : Icons.expand_more_rounded, color: C.texto2),
        onTap: () => setState(() => _abierta = abierta ? -1 : i),
      ),
      if (abierta)
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(texto.split('\n').where((x) => x.trim().isNotEmpty).take(8).join('\n'), style: estiloSecundario),
            const SizedBox(height: 10),
            FilledButton(onPressed: () => _usar(l), child: const Text('Usar esta letra')),
          ]),
        ),
    ]);
  }
}
