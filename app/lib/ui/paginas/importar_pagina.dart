import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;

import '../../nucleo/importacion.dart';
import '../../nucleo/importar.dart';
import '../../nucleo/importar_archivos.dart';
import '../servicios.dart';
import '../tema.dart';
import 'me_gusta_externos_pagina.dart';

/// Traer a Caudal una lista de Spotify, Apple Music, YouTube Music o SoundCloud pegando
/// su enlace, o la música de Snaptube. Las canciones van a una lista nueva o a tus Me gusta.
///
/// La búsqueda de las canciones sigue aunque se salga de esta pantalla
/// ([TrabajoImportacion]) y, si se cierra la app, se puede seguir donde quedó.
class ImportarPagina extends StatefulWidget {
  const ImportarPagina({super.key, this.enlace = '', this.aMeGusta = false});
  final String enlace;
  final bool aMeGusta;

  @override
  State<ImportarPagina> createState() => _ImportarPaginaState();
}

class _ImportarPaginaState extends State<ImportarPagina> {
  late final _campo = TextEditingController(text: widget.enlace);
  late bool _aMeGusta = widget.aMeGusta;
  final _trabajo = TrabajoImportacion.i;
  bool _leyendo = false;
  String? _error;
  Map<String, dynamic>? _pendiente;

  @override
  void initState() {
    super.initState();
    if (widget.enlace.isEmpty) _pegarSiHay();
    _trabajo.addListener(_cambio);
    WidgetsBinding.instance.addPostFrameCallback((_) => _mirarPendiente());
  }

  @override
  void dispose() {
    // la búsqueda NO se cancela al salir: sigue y avisa al terminar
    _trabajo.removeListener(_cambio);
    _campo.dispose();
    super.dispose();
  }

  void _cambio() {
    if (mounted) setState(() {});
  }

  Future<void> _mirarPendiente() async {
    if (!mounted || _trabajo.enMarcha) return;
    final p = await TrabajoImportacion.pendiente(Caudal.leer(context).coleccion);
    if (mounted) setState(() => _pendiente = p);
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
    FocusScope.of(context).unfocus();
    final enlace = Importar.enlaceDe(_campo.text);
    await _procesar(() => Importar.leer(enlace), enlace: enlace);
  }

  /// Lee la lista con [leer] y deja la búsqueda de sus canciones en marcha.
  Future<void> _procesar(Future<ListaExterna> Function() leer, {String enlace = ''}) async {
    if (_trabajo.enMarcha) {
      setState(() => _error = 'Ya se están pasando canciones. Espera a que termine o páusalo.');
      return;
    }
    final s = Caudal.leer(context);
    setState(() {
      _leyendo = true;
      _error = null;
    });
    try {
      final l = await leer();
      if (!mounted) return;
      final meGusta = _aMeGusta;
      _trabajo.olvidarTerminado();
      await _trabajo.empezar(s.coleccion, l, meGusta: meGusta, enlace: enlace);
      _avisarAlTerminar(s);
      setState(() {
        _leyendo = false;
        _pendiente = null;
      });
    } on ErrorImportar catch (e) {
      if (mounted) {
        setState(() {
          _leyendo = false;
          _error = e.mensaje;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _leyendo = false;
          _error = 'No se pudo traer la lista. Revisa tu internet y vuelve a probar.';
        });
      }
    }
  }

  /// Al terminar avisa aunque ya se haya salido de esta pantalla.
  void _avisarAlTerminar(Servicios s) {
    void oir() {
      if (_trabajo.enMarcha) return;
      _trabajo.removeListener(oir);
      if (_trabajo.terminado) {
        final aviso = _trabajo.aviso;
        s.avisar(_trabajo.resumen() + (aviso.isEmpty ? '' : ' $aviso'));
      }
    }

    _trabajo.addListener(oir);
  }

  Future<void> _seguir() async {
    final s = Caudal.leer(context);
    try {
      _trabajo.olvidarTerminado();
      await _trabajo.reanudar(s.coleccion);
      _avisarAlTerminar(s);
      setState(() => _pendiente = null);
    } on ErrorImportar catch (e) {
      setState(() {
        _pendiente = null;
        _error = e.mensaje;
      });
    }
  }

  Future<void> _descartar() async {
    await _trabajo.descartar(Caudal.leer(context).coleccion);
    if (mounted) setState(() => _pendiente = null);
  }

  void _abrirResultado() {
    final s = Caudal.leer(context);
    final id = _trabajo.listaId;
    final meGusta = _trabajo.aMeGusta;
    final titulo = _trabajo.titulo;
    _trabajo.olvidarTerminado();
    Navigator.of(context).pop();
    if (meGusta) {
      s.abrirElemento(context, {'tipo': 'me_gusta', 'id': 'me_gusta', 'titulo': 'Tus me gusta'});
    } else if (id != null) {
      s.abrirElemento(context, {'tipo': 'mi_lista', 'id': id, 'titulo': titulo});
    }
  }

  // ------------------------------------------------------------ Snaptube y otras apps

  /// Los nombres de las canciones de una carpeta (sin copiar nada).
  Future<List<String>> _nombresDe(String carpeta) async {
    final salida = <String>[];
    await for (final e in Directory(carpeta).list(recursive: true, followLinks: false)) {
      if (e is File && ImportarArchivos.extensiones.contains(p.extension(e.path).replaceFirst('.', '').toLowerCase())) {
        salida.add(p.basename(e.path));
      }
    }
    salida.sort();
    return salida;
  }

  Future<void> _desdeCarpeta() async {
    String? carpeta;
    try {
      carpeta = await FilePicker.getDirectoryPath(dialogTitle: 'Elige la carpeta SnapTube Audio');
    } catch (_) {}
    if (carpeta == null || !mounted) return;
    final elegida = carpeta;
    await _procesar(() async {
      List<String> nombres;
      try {
        nombres = await _nombresDe(elegida);
      } catch (_) {
        throw const ErrorImportar('Android no dejó leer esa carpeta. Usa «Elegir canciones» y marca todas las de Snaptube.');
      }
      return Importar.deLineas(nombres, titulo: 'Snaptube · ${p.basename(elegida)}');
    });
  }

  Future<void> _desdeArchivos() async {
    final rutas = await ImportarArchivos.elegir();
    if (rutas.isEmpty || !mounted) return;
    await _procesar(() async => Importar.deLineas([for (final r in rutas) p.basename(r)], titulo: 'Mi lista de Snaptube'));
  }

  Future<void> _desdeTexto() async {
    final c = TextEditingController();
    final nombre = TextEditingController(text: 'Mi lista');
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.superficie2,
        title: const Text('Pegar nombres de canciones'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Una canción por línea, como «Artista - Título». Sirve cualquier lista que hayas copiado de Snaptube u otra app.',
                style: estiloSecundario),
            const SizedBox(height: 12),
            TextField(controller: nombre, decoration: const InputDecoration(labelText: 'Nombre de la lista')),
            const SizedBox(height: 8),
            TextField(
              controller: c,
              minLines: 6,
              maxLines: 12,
              decoration: const InputDecoration(hintText: 'Bad Bunny - Monaco\nKarol G - Tusa\n…'),
            ),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Traer')),
        ],
      ),
    );
    final texto = c.text;
    final titulo = nombre.text.trim().isEmpty ? 'Mi lista' : nombre.text.trim();
    c.dispose();
    nombre.dispose();
    if (ok != true || !mounted) return;
    await _procesar(() async => Importar.deLineas(texto.split(RegExp(r'[\r\n]+')), titulo: titulo, plataforma: 'texto pegado'));
  }

  // ------------------------------------------------------------ pantalla

  @override
  Widget build(BuildContext context) {
    final t = _trabajo;
    final ocupado = _leyendo || t.enMarcha;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: C.fondo,
        surfaceTintColor: Colors.transparent,
        title: const Text('Traer una lista', style: estiloTituloBarra),
      ),
      body: ListView(padding: const EdgeInsets.all(Esp.lado), children: [
        if (t.enMarcha || t.terminado || t.error != null) ...[
          _TarjetaAvance(trabajo: t, alAbrir: _abrirResultado),
          const SizedBox(height: Esp.xl),
        ] else if (_pendiente != null) ...[
          _TarjetaPendiente(datos: _pendiente!, alSeguir: _seguir, alDescartar: _descartar),
          const SizedBox(height: Esp.xl),
        ],
        const Text(
          'Pega el enlace de una lista, un álbum o una canción de Spotify, Apple Music, YouTube Music '
          'o SoundCloud. Caudal busca cada canción, sin límite de cantidad, y la guarda donde elijas.',
          style: TextStyle(color: C.texto2, height: 1.4),
        ),
        const SizedBox(height: Esp.l),
        const Text('Cómo copiar el enlace: en la app de música abre la lista, toca '
            'Compartir y luego «Copiar enlace».', style: estiloDetalle),
        const SizedBox(height: Esp.xl),
        TextField(
          controller: _campo,
          enabled: !ocupado,
          keyboardType: TextInputType.url,
          decoration: InputDecoration(
            hintText: 'https://open.spotify.com/playlist/…',
            filled: true,
            fillColor: C.superficie,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            suffixIcon: IconButton(tooltip: 'Pegar', icon: const Icon(Icons.content_paste_rounded),
                onPressed: ocupado ? null : _pegar),
          ),
          onChanged: (_) => setState(() => _error = null),
          onSubmitted: (_) => _traer(),
        ),
        const SizedBox(height: Esp.m),
        const Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
          _Marca('Spotify', Color(0xFF1DB954)),
          _Marca('Apple Music', Color(0xFFFA2D48)),
          _Marca('YouTube Music', Color(0xFFFF3B30)),
          _Marca('SoundCloud', Color(0xFFFF5500)),
        ]),
        const SizedBox(height: Esp.l),
        const Text('Guardar en', style: TextStyle(color: C.texto2, fontWeight: FontWeight.w700)),
        const SizedBox(height: Esp.s),
        Wrap(spacing: Esp.s, children: [
          ChoiceChip(
            label: const Text('Una lista nueva'),
            selected: !_aMeGusta,
            onSelected: ocupado ? null : (_) => setState(() => _aMeGusta = false),
          ),
          ChoiceChip(
            label: const Text('Mis Me gusta'),
            selected: _aMeGusta,
            onSelected: ocupado ? null : (_) => setState(() => _aMeGusta = true),
          ),
        ]),
        const SizedBox(height: Esp.l),
        if (_error != null) ...[
          Text(_error!, style: const TextStyle(color: C.error, height: 1.35)),
          const SizedBox(height: Esp.l),
        ],
        if (_leyendo) ...[
          const Text('Leyendo la lista…', style: TextStyle(color: C.texto, fontWeight: FontWeight.w700)),
          const SizedBox(height: Esp.m),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(minHeight: 6, color: C.acento, backgroundColor: C.superficie2),
          ),
        ] else if (!t.enMarcha)
          FilledButton.icon(
            onPressed: _campo.text.trim().isEmpty ? null : _traer,
            style: FilledButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto,
                minimumSize: const Size.fromHeight(50)),
            icon: Icon(_aMeGusta ? Icons.favorite_rounded : Icons.playlist_add_rounded),
            label: Text(_aMeGusta ? 'Pasar a Me gusta' : 'Traer lista', style: const TextStyle(fontWeight: FontWeight.w800)),
          ),
        const SizedBox(height: Esp.m),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const MeGustaExternosPagina())),
            icon: const Icon(Icons.favorite_border_rounded),
            label: const Text('Pasar tus me gusta de Spotify, YouTube Music o SoundCloud'),
          ),
        ),
        const SizedBox(height: Esp.xl),
        if (!ocupado) ...[
          const Text('Snaptube y otras apps', style: estiloTituloSeccion),
          const SizedBox(height: 4),
          const Text(
            'Las listas de Snaptube viven solo dentro de esa app y no tienen enlace. Trae lo que bajaste con ella '
            '(Caudal busca cada canción para que suene completa, sin límite de cantidad) o pega sus nombres.',
            style: estiloDetalle,
          ),
          const SizedBox(height: Esp.s),
          Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
            if (!kIsWeb && Platform.isAndroid)
              OutlinedButton.icon(
                onPressed: _desdeCarpeta,
                icon: const Icon(Icons.folder_open_rounded),
                label: const Text('Carpeta de Snaptube'),
              ),
            if (!kIsWeb)
              OutlinedButton.icon(
                onPressed: _desdeArchivos,
                icon: const Icon(Icons.audio_file_rounded),
                label: const Text('Elegir canciones'),
              ),
            OutlinedButton.icon(
              onPressed: _desdeTexto,
              icon: const Icon(Icons.notes_rounded),
              label: const Text('Pegar nombres'),
            ),
          ]),
          const SizedBox(height: Esp.xl),
        ],
      ]),
    );
  }
}

/// El avance de lo que se está pasando: «1 240 de 5 300 canciones».
class _TarjetaAvance extends StatefulWidget {
  const _TarjetaAvance({required this.trabajo, required this.alAbrir});
  final TrabajoImportacion trabajo;
  final VoidCallback alAbrir;

  @override
  State<_TarjetaAvance> createState() => _TarjetaAvanceState();
}

class _TarjetaAvanceState extends State<_TarjetaAvance> {
  bool _verFaltan = false;

  @override
  Widget build(BuildContext context) {
    final t = widget.trabajo;
    final destino = t.aMeGusta ? 'tus Me gusta' : 'la lista «${t.titulo}»';
    final progreso = t.total > 0 ? t.hechas / t.total : null;
    final faltan = t.noEncontradas;
    return Container(
      padding: const EdgeInsets.all(Esp.l),
      decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(t.terminado ? 'Listo' : (t.error != null ? 'Se detuvo' : 'Pasando canciones a $destino'),
            style: const TextStyle(color: C.texto, fontWeight: FontWeight.w800, fontSize: 16)),
        const SizedBox(height: Esp.m),
        if (!t.terminado) ...[
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(value: progreso, minHeight: 6, color: C.acento, backgroundColor: C.superficie2),
          ),
          const SizedBox(height: Esp.s),
          Text('${textoAvance(t.hechas, t.total)} canciones · ${miles(t.encontradas)} encontradas',
              style: const TextStyle(color: C.texto2, fontWeight: FontWeight.w600)),
          const SizedBox(height: Esp.xs),
          Text(
              t.error ??
                  (t.pausando
                      ? 'Pausando después de esta tanda…'
                      : 'Puedes salir de aquí: sigue buscando y te avisa al terminar. Lo encontrado se guarda por tandas.'),
              style: TextStyle(color: t.error != null ? C.error : C.texto3, fontSize: 12, height: 1.35)),
        ] else ...[
          Text(t.resumen(), style: const TextStyle(color: C.texto2, height: 1.35)),
          if (t.aviso.isNotEmpty) ...[
            const SizedBox(height: Esp.s),
            Text(t.aviso, style: estiloDetalle),
          ],
        ],
        const SizedBox(height: Esp.m),
        Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
          if (t.enMarcha)
            OutlinedButton(onPressed: t.pausando ? null : t.pausar, child: const Text('Pausar')),
          if (t.terminado)
            FilledButton(
              onPressed: widget.alAbrir,
              style: FilledButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto),
              child: Text(t.aMeGusta ? 'Ver mis Me gusta' : 'Abrir la lista'),
            ),
          if (t.terminado && faltan.isNotEmpty)
            TextButton(
              onPressed: () => setState(() => _verFaltan = !_verFaltan),
              child: Text(_verFaltan ? 'Ocultar las que faltan' : 'Ver las ${miles(faltan.length)} que no se encontraron'),
            ),
        ]),
        if (_verFaltan && faltan.isNotEmpty)
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 220),
            child: ListView.builder(
              shrinkWrap: true,
              itemCount: faltan.length,
              itemBuilder: (_, i) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(faltan[i], style: estiloDetalle, maxLines: 1, overflow: TextOverflow.ellipsis),
              ),
            ),
          ),
      ]),
    );
  }
}

class _TarjetaPendiente extends StatelessWidget {
  const _TarjetaPendiente({required this.datos, required this.alSeguir, required this.alDescartar});
  final Map<String, dynamic> datos;
  final VoidCallback alSeguir;
  final VoidCallback alDescartar;

  @override
  Widget build(BuildContext context) {
    final meGusta = datos['me_gusta'] == true;
    final destino = meGusta ? 'tus Me gusta' : 'la lista «${datos['titulo'] ?? ''}»';
    final hechas = (datos['hechas'] as num?)?.toInt() ?? 0;
    final total = (datos['total'] as num?)?.toInt() ?? 0;
    return Container(
      padding: const EdgeInsets.all(Esp.l),
      decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Quedó a medias el paso de canciones a $destino',
            style: const TextStyle(color: C.texto, fontWeight: FontWeight.w800)),
        const SizedBox(height: Esp.xs),
        Text('Van ${textoAvance(hechas, total)}. Lo encontrado ya está guardado.', style: estiloSecundario),
        const SizedBox(height: Esp.m),
        Wrap(spacing: Esp.s, children: [
          FilledButton(
            onPressed: alSeguir,
            style: FilledButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto),
            child: const Text('Seguir'),
          ),
          TextButton(onPressed: alDescartar, child: const Text('Dejarlo así')),
        ]),
      ]),
    );
  }
}

class _Marca extends StatelessWidget {
  const _Marca(this.nombre, this.color);
  final String nombre;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: color.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
        child: Text(nombre, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w700)),
      );
}
