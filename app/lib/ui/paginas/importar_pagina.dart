import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../nucleo/importar.dart';
import '../servicios.dart';
import '../tema.dart';

/// Traer a Caudal una lista de Spotify, Apple Music o YouTube Music pegando su enlace.
class ImportarPagina extends StatefulWidget {
  const ImportarPagina({super.key, this.enlace = ''});
  final String enlace;

  @override
  State<ImportarPagina> createState() => _ImportarPaginaState();
}

class _ImportarPaginaState extends State<ImportarPagina> {
  late final _campo = TextEditingController(text: widget.enlace);
  bool _trabajando = false;
  bool _cancelado = false;
  String _fase = '';
  int _hechas = 0;
  int _total = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.enlace.isEmpty) _pegarSiHay();
  }

  @override
  void dispose() {
    _cancelado = true;
    _campo.dispose();
    super.dispose();
  }

  /// Si lo copiado es un enlace de lista, se pone solo.
  Future<void> _pegarSiHay() async {
    try {
      final d = await Clipboard.getData(Clipboard.kTextPlain);
      final t = Importar.enlaceDe(d?.text ?? '');
      if (Importar.plataforma(t).isNotEmpty && mounted && _campo.text.isEmpty) {
        setState(() => _campo.text = t);
      }
    } catch (_) {}
  }

  Future<void> _pegar() async {
    final d = await Clipboard.getData(Clipboard.kTextPlain);
    if (d?.text != null && mounted) setState(() => _campo.text = Importar.enlaceDe(d!.text!));
  }

  Future<void> _traer() async {
    final s = Caudal.leer(context);
    FocusScope.of(context).unfocus();
    setState(() {
      _trabajando = true;
      _error = null;
      _fase = 'Leyendo la lista…';
      _hechas = 0;
      _total = 0;
    });
    try {
      final l = await Importar.leer(_campo.text);
      if (!mounted) return;
      setState(() {
        _fase = 'Buscando las canciones de «${l.titulo}»';
        _total = l.canciones.length;
      });
      final pistas = await Importar.resolver(l, cancelado: () => _cancelado, alAvanzar: (h, t) {
        if (mounted) setState(() => _hechas = h);
      });
      if (!mounted || _cancelado) return;
      if (pistas.isEmpty) {
        setState(() {
          _trabajando = false;
          _error = 'No se encontró ninguna de esas canciones en YouTube Music.';
        });
        return;
      }
      var nombre = l.titulo;
      int id;
      try {
        id = await s.coleccion.crearLista(nombre, descripcion: 'Traída de ${l.plataforma}');
      } on FormatException {
        // ya hay una lista con ese nombre: "Nombre n.º 2"...
        nombre = await s.coleccion.nombreLibre(l.titulo);
        id = await s.coleccion.crearLista(nombre, descripcion: 'Traída de ${l.plataforma}');
      }
      await s.coleccion.agregarALista(id, pistas);
      if (!mounted) return;
      final faltan = l.canciones.length - pistas.length;
      var aviso = 'Lista «$nombre» creada con ${pistas.length} canciones.';
      if (faltan > 0) aviso += ' $faltan no se encontraron.';
      if (l.aviso.isNotEmpty) aviso += ' ${l.aviso}';
      s.avisar(aviso);
      Navigator.of(context).pop();
      s.abrirElemento(context, {'tipo': 'mi_lista', 'id': id, 'titulo': nombre});
    } on ErrorImportar catch (e) {
      if (mounted) {
        setState(() {
          _trabajando = false;
          _error = e.mensaje;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _trabajando = false;
          _error = 'No se pudo traer la lista. Revisa tu internet y vuelve a probar.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final progreso = _total > 0 ? _hechas / _total : null;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: C.fondo,
        surfaceTintColor: Colors.transparent,
        title: const Text('Traer una lista', style: estiloTituloBarra),
      ),
      body: ListView(padding: const EdgeInsets.all(Esp.lado), children: [
        const Text(
          'Pega el enlace de una lista, un álbum o una canción de Spotify, Apple Music '
          'o YouTube Music. Caudal busca cada canción y te crea la lista en tu biblioteca.',
          style: TextStyle(color: C.texto2, height: 1.4),
        ),
        const SizedBox(height: Esp.l),
        const Text('Cómo copiar el enlace: en la app de música abre la lista, toca '
            'Compartir y luego «Copiar enlace».', style: estiloDetalle),
        const SizedBox(height: Esp.xl),
        TextField(
          controller: _campo,
          enabled: !_trabajando,
          keyboardType: TextInputType.url,
          decoration: InputDecoration(
            hintText: 'https://open.spotify.com/playlist/…',
            filled: true,
            fillColor: C.superficie,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            suffixIcon: IconButton(tooltip: 'Pegar', icon: const Icon(Icons.content_paste_rounded),
                onPressed: _trabajando ? null : _pegar),
          ),
          onChanged: (_) => setState(() => _error = null),
          onSubmitted: (_) => _traer(),
        ),
        const SizedBox(height: Esp.m),
        Row(children: const [
          _Marca('Spotify', Color(0xFF1DB954)),
          SizedBox(width: Esp.s),
          _Marca('Apple Music', Color(0xFFFA2D48)),
          SizedBox(width: Esp.s),
          _Marca('YouTube Music', Color(0xFFFF3B30)),
        ]),
        const SizedBox(height: Esp.xl),
        if (_error != null) ...[
          Text(_error!, style: const TextStyle(color: C.error, height: 1.35)),
          const SizedBox(height: Esp.l),
        ],
        if (_trabajando) ...[
          Text(_fase, style: const TextStyle(color: C.texto, fontWeight: FontWeight.w700)),
          const SizedBox(height: Esp.m),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(value: progreso, minHeight: 6,
                color: C.acento, backgroundColor: C.superficie2),
          ),
          if (_total > 0) ...[
            const SizedBox(height: Esp.s),
            Text('$_hechas de $_total canciones', style: estiloDetalle),
          ],
        ] else
          FilledButton.icon(
            onPressed: _campo.text.trim().isEmpty ? null : _traer,
            style: FilledButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto,
                minimumSize: const Size.fromHeight(50)),
            icon: const Icon(Icons.playlist_add_rounded),
            label: const Text('Traer lista', style: TextStyle(fontWeight: FontWeight.w800)),
          ),
      ]),
    );
  }
}

class _Marca extends StatelessWidget {
  const _Marca(this.nombre, this.color);
  final String nombre;
  final Color color;

  @override
  Widget build(BuildContext context) => Flexible(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(color: color.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
          child: Text(nombre, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w700)),
        ),
      );
}
