import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/chat.dart';
import '../../nucleo/coleccion.dart' show Json;
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';

/// Cómo se buscan canciones (se cambia en las pruebas para no usar internet).
typedef BuscadorCanciones = Future<List<Json>> Function(String texto);

Future<List<Json>> _buscarEnCatalogo(String texto) async =>
    [for (final x in await Catalogo.buscar(texto, filtro: 'canciones', limite: 15)) Map<String, dynamic>.from(x)];

/// Solo cuentan las canciones que suenan en línea (tienen `video_id`): las de archivos del teléfono no
/// le sirven a nadie más ni se pueden reproducir desde otra cuenta.
bool esCancionEnLinea(Json p) => '${p['video_id'] ?? ''}'.isNotEmpty;

/// «Elige una canción»: lo que suena ahora, tus «me gusta» y un buscador. Devuelve la pista elegida
/// (lista para sonar) o nulo si se cierra sin elegir.
Future<Json?> elegirCancion(
  BuildContext context, {
  String titulo = 'Elige una canción',
  BuscadorCanciones? buscador,
  Future<List<Json>> Function()? favoritas,
}) {
  final s = Caudal.leer(context);
  return showModalBottomSheet<Json>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    useRootNavigator: true,
    backgroundColor: C.panel,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
    builder: (_) => ElegirCancionHoja(
      titulo: titulo,
      sonando: s.reproductor.actual,
      buscador: buscador ?? _buscarEnCatalogo,
      favoritas: favoritas ?? () => s.coleccion.meGustaRecientes(60),
    ),
  );
}

class ElegirCancionHoja extends StatefulWidget {
  const ElegirCancionHoja({
    super.key,
    required this.titulo,
    required this.buscador,
    required this.favoritas,
    this.sonando,
  });

  final String titulo;
  final Json? sonando;
  final BuscadorCanciones buscador;
  final Future<List<Json>> Function() favoritas;

  @override
  State<ElegirCancionHoja> createState() => _ElegirCancionHojaState();
}

class _ElegirCancionHojaState extends State<ElegirCancionHoja> {
  final _campo = TextEditingController();
  Timer? _espera;
  List<Json> _favoritas = const [];
  List<Json> _resultados = const [];
  bool _cargandoFav = true;
  bool _buscando = false;
  String? _fallo;
  String _ultima = '';

  @override
  void initState() {
    super.initState();
    _cargarFavoritas();
  }

  @override
  void dispose() {
    _espera?.cancel();
    _campo.dispose();
    super.dispose();
  }

  Future<void> _cargarFavoritas() async {
    try {
      final l = await widget.favoritas();
      if (mounted) setState(() => _favoritas = [for (final p in l) if (esCancionEnLinea(p)) Chat.pistaJugable(p)]);
    } catch (_) {
      // sin favoritas se puede buscar igual
    } finally {
      if (mounted) setState(() => _cargandoFav = false);
    }
  }

  void _alEscribir(String t) {
    _espera?.cancel();
    final q = t.trim();
    if (q.length < 2) {
      setState(() {
        _resultados = const [];
        _fallo = null;
        _buscando = false;
        _ultima = '';
      });
      return;
    }
    setState(() => _buscando = true);
    _espera = Timer(const Duration(milliseconds: 450), () async {
      _ultima = q;
      try {
        final r = await widget.buscador(q);
        if (!mounted || _ultima != q) return;
        setState(() {
          _resultados = [for (final x in r) if (esCancionEnLinea(x)) Chat.pistaJugable(x)];
          _buscando = false;
          _fallo = null;
        });
      } catch (_) {
        if (mounted && _ultima == q) {
          setState(() {
            _buscando = false;
            _fallo = 'No se pudo buscar ahora. Revisa tu internet e inténtalo otra vez.';
          });
        }
      }
    });
  }

  Widget _fila(Json p, {String? etiqueta}) => ListTile(
        key: ValueKey('cancion-${p['video_id']}'),
        contentPadding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 2),
        leading: Portada(url: '${p['miniatura'] ?? ''}', lado: 48, radio: 8),
        title: Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text([if (etiqueta != null) etiqueta, '${p['artista'] ?? ''}'].where((e) => e.isNotEmpty).join(' · '),
            maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
        onTap: () => Navigator.of(context).pop(p),
      );

  Widget _contenido() {
    final q = _campo.text.trim();
    if (q.length >= 2) {
      if (_buscando && _resultados.isEmpty) return const Center(child: CircularProgressIndicator());
      if (_fallo != null) {
        return Center(
            child: Padding(
                padding: const EdgeInsets.all(Esp.xl),
                child: Text(_fallo!, textAlign: TextAlign.center, style: estiloSecundario)));
      }
      if (_resultados.isEmpty) {
        return const Center(child: Text('No encontramos nada con esa búsqueda.', style: estiloSecundario));
      }
      return ListView.builder(itemCount: _resultados.length, itemBuilder: (_, i) => _fila(_resultados[i]));
    }
    final sonando = widget.sonando;
    final hayAhora = sonando != null && esCancionEnLinea(sonando);
    if (_cargandoFav && !hayAhora) return const Center(child: CircularProgressIndicator());
    if (!hayAhora && _favoritas.isEmpty) {
      return const Center(
          child: Padding(
              padding: EdgeInsets.all(Esp.xl),
              child: Text('Escribe el nombre de una canción o artista para buscarla.',
                  textAlign: TextAlign.center, style: estiloSecundario)));
    }
    return ListView(children: [
      if (hayAhora) ...[
        const _Cabecera('Suena ahora'),
        _fila(Chat.pistaJugable(Map<String, dynamic>.from(sonando))),
      ],
      if (_favoritas.isNotEmpty) ...[
        const _Cabecera('Tus «me gusta»'),
        for (final p in _favoritas) _fila(p),
      ],
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.86,
        child: Column(children: [
          const SizedBox(height: 10),
          Container(width: 38, height: 4, decoration: BoxDecoration(color: C.borde, borderRadius: BorderRadius.circular(4))),
          Padding(
            padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, 0),
            child: Align(
                alignment: Alignment.centerLeft,
                child: Text(widget.titulo, style: estiloTituloSeccion.copyWith(fontSize: 19))),
          ),
          Padding(
            padding: const EdgeInsets.all(Esp.lado),
            child: TextField(
              controller: _campo,
              onChanged: _alEscribir,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Busca una canción o un artista',
                prefixIcon: const Icon(Icons.search_rounded),
                filled: true,
                fillColor: C.superficie2,
                isDense: true,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide.none),
              ),
            ),
          ),
          Expanded(child: _contenido()),
        ]),
      ),
    );
  }
}

class _Cabecera extends StatelessWidget {
  const _Cabecera(this.texto);
  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, Esp.xs),
        child: Text(texto, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: C.texto2)),
      );
}
