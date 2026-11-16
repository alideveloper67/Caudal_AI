import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../nucleo/importar_archivos.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/social.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'perfil_comun.dart';
import 'subir_musica_comunidad.dart';

/// Subir una canción propia a la comunidad: audio, carátula obligatoria,
/// título, artista, álbum opcional, aviso de derechos y barra de progreso.
/// Se cierra con `true` si se subió.
class SubirMusicaPagina extends StatefulWidget {
  const SubirMusicaPagina({super.key});

  @override
  State<SubirMusicaPagina> createState() => _SubirMusicaPaginaState();
}

class _SubirMusicaPaginaState extends State<SubirMusicaPagina> {
  final _titulo = TextEditingController();
  final _artista = TextEditingController();
  final _album = TextEditingController();

  Uint8List? _audio;
  String _nombreAudio = '';
  String _ext = '';
  int _duracion = 0;
  Uint8List? _caratula; // ya comprimida
  bool _derechos = false;
  bool _procesando = false;
  bool _subiendo = false;
  double _avance = 0;
  String _fase = '';
  String? _fallo;

  @override
  void dispose() {
    for (final c in [_titulo, _artista, _album]) {
      c.dispose();
    }
    super.dispose();
  }

  bool get _listo =>
      _audio != null && _caratula != null && _titulo.text.trim().isNotEmpty && _derechos && !_subiendo;

  Future<void> _elegirAudio() async {
    try {
      final r = await FilePicker.pickFiles(
          type: FileType.custom, allowedExtensions: Social.extensionesAudio, withData: true);
      final f = r?.files.firstOrNull;
      if (f == null) return;
      final ext = Social.extensionAudio(f.name);
      if (ext == null) {
        setState(() => _fallo = 'Ese formato no sirve. Usa mp3, m4a, aac, flac, ogg, wav o webm.');
        return;
      }
      final bytes = f.bytes;
      if (bytes == null) {
        setState(() => _fallo = 'No se pudo leer el archivo. Prueba con otro.');
        return;
      }
      if (bytes.length > Social.maxAudioBytes) {
        setState(() => _fallo = 'Ese audio pesa ${(bytes.length / 1048576).toStringAsFixed(1)} MB y el máximo es 15 MB.');
        return;
      }
      var titulo = '', artista = '', album = '';
      var dur = 0;
      final base = f.name.contains('.') ? f.name.substring(0, f.name.lastIndexOf('.')) : f.name;
      final (a, t) = ImportarArchivos.separarNombre(base);
      titulo = t;
      artista = a;
      if (!kIsWeb && f.path != null) {
        final d = await ImportarArchivos.leerDatos(f.path!);
        if (d.titulo.isNotEmpty) titulo = d.titulo;
        if (d.artista.isNotEmpty) artista = d.artista;
        album = d.album;
        dur = d.duracion;
      }
      if (!mounted) return;
      setState(() {
        _audio = bytes;
        _nombreAudio = f.name;
        _ext = ext;
        _duracion = dur;
        _fallo = null;
        if (_titulo.text.trim().isEmpty) _titulo.text = titulo;
        if (_artista.text.trim().isEmpty) _artista.text = artista;
        if (_album.text.trim().isEmpty) _album.text = album;
      });
    } catch (_) {
      if (mounted) setState(() => _fallo = 'No se pudo abrir ese archivo. Prueba con otro.');
    }
  }

  Future<void> _elegirCaratula() async {
    if (_procesando) return;
    try {
      final r = await FilePicker.pickFiles(type: FileType.image, withData: true);
      final bytes = r?.files.firstOrNull?.bytes;
      if (bytes == null) return;
      setState(() => _procesando = true);
      final jpeg = await ImagenSocial.caratula(bytes);
      if (mounted) {
        setState(() {
          _caratula = jpeg;
          _fallo = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _fallo = e is ErrorNube ? e.mensaje : 'No se pudo usar esa imagen.');
    } finally {
      if (mounted) setState(() => _procesando = false);
    }
  }

  Future<void> _subir() async {
    final social = socialDe(context);
    final s = Caudal.leer(context);
    if (social == null) {
      setState(() => _fallo = 'Subir música necesita internet. Vuelve a abrir Caudal con conexión.');
      return;
    }
    if (!_listo) return;
    setState(() {
      _subiendo = true;
      _fallo = null;
      _avance = 0;
      _fase = 'Preparando…';
    });
    try {
      await social.subirCancion(
        audio: _audio!,
        extension: _ext,
        caratula: _caratula!,
        titulo: _titulo.text,
        artista: _artista.text,
        album: _album.text,
        duracion: _duracion,
        alAvanzar: (f, fase) {
          if (mounted) {
            setState(() {
              _avance = f;
              _fase = fase;
            });
          }
        },
      );
      final directo = await social.publicaDirecto();
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        useRootNavigator: true,
        builder: (ctx) => AlertDialog(
          backgroundColor: C.superficie2,
          icon: Icon(directo ? Icons.check_circle_rounded : Icons.hourglass_top_rounded,
              size: 40, color: directo ? C.exito : const Color(0xFFF5C451)),
          title: Text(directo ? '¡Canción subida!' : 'Quedó en revisión'),
          content: Text(Social.mensajeTrasSubir(directo)),
          actions: [FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('Entendido'))],
        ),
      );
      if (!mounted) return;
      s.avisar(directo ? 'Tu canción ya está en la comunidad.' : 'Tu canción está en revisión.');
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        setState(() {
          _subiendo = false;
          _fallo = '${Social.error(e)} No se subió nada, puedes intentarlo otra vez.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Subir música', style: estiloTituloBarra),
        actions: [
          IconButton(
            tooltip: 'Música de la comunidad',
            icon: const Icon(Icons.groups_rounded),
            onPressed: _subiendo
                ? null
                : () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const ComunidadPagina())),
          ),
        ],
      ),
      body: AbsorbPointer(
        absorbing: _subiendo,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(Esp.xl, Esp.m, Esp.xl, 120),
          children: [
            const Text('Comparte tu música con toda la comunidad de Caudal. Puedes subir hasta 30 canciones, 10 por día.',
                style: estiloSecundario),
            const SizedBox(height: Esp.xl),
            _paso(1, 'El audio', _audioTarjeta()),
            _paso(2, 'La carátula (obligatoria)', _caratulaTarjeta()),
            _paso(3, 'Los datos', Column(children: [
              _campo('Título', _titulo, Icons.music_note_rounded, max: 100),
              _campo('Artista', _artista, Icons.mic_external_on_rounded, max: 100),
              _campo('Álbum (opcional)', _album, Icons.album_rounded, max: 100,
                  ayuda: 'Si subes un álbum, pon el mismo nombre en todas sus canciones para agruparlas.'),
            ])),
            Material(
              color: C.superficie,
              borderRadius: BorderRadius.circular(16),
              child: CheckboxListTile(
                value: _derechos,
                onChanged: (v) => setState(() => _derechos = v ?? false),
                controlAffinity: ListTileControlAffinity.leading,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                title: const Text('Declaro que esta música es mía o tengo permiso para compartirla',
                    style: TextStyle(fontSize: 14, height: 1.3)),
              ),
            ),
            AnimatedSize(
              duration: Mov.normal,
              curve: Mov.curva,
              child: _fallo == null
                  ? const SizedBox(width: double.infinity)
                  : Padding(
                      padding: const EdgeInsets.only(top: Esp.m),
                      child: Container(
                        padding: const EdgeInsets.all(Esp.m),
                        decoration: BoxDecoration(
                            color: C.error.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: C.error.withValues(alpha: 0.4))),
                        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          const Icon(Icons.error_outline_rounded, color: C.error, size: 20),
                          const SizedBox(width: 10),
                          Expanded(child: Text(_fallo!, style: const TextStyle(fontSize: 13.5, height: 1.3))),
                        ]),
                      ),
                    ),
            ),
            const SizedBox(height: Esp.xl),
            if (_subiendo)
              Column(children: [
                TweenAnimationBuilder<double>(
                  tween: Tween(begin: 0, end: _avance),
                  duration: Mov.normal,
                  builder: (_, v, _) => ClipRRect(
                    borderRadius: BorderRadius.circular(999),
                    child: LinearProgressIndicator(value: v, minHeight: 10, color: C.acento, backgroundColor: C.superficie3),
                  ),
                ),
                const SizedBox(height: 10),
                Text('$_fase ${(_avance * 100).round()} %', style: estiloSecundario),
                const SizedBox(height: 4),
                const Text('No cierres esta pantalla hasta que termine.', style: estiloDetalle),
              ])
            else
              FilledButton.icon(
                onPressed: _listo ? _subir : null,
                icon: const Icon(Icons.cloud_upload_rounded),
                label: const Text('Subir canción'),
                style: FilledButton.styleFrom(
                  backgroundColor: C.acento,
                  foregroundColor: C.acentoTexto,
                  minimumSize: const Size.fromHeight(52),
                  shape: const StadiumBorder(),
                  textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                ),
              ),
            if (!_subiendo && !_listo)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(_queFalta(), textAlign: TextAlign.center, style: estiloDetalle),
              ),
          ],
        ),
      ),
    );
  }

  String _queFalta() {
    if (_audio == null) return 'Elige el audio para empezar.';
    if (_caratula == null) return 'Falta elegir la carátula.';
    if (_titulo.text.trim().isEmpty) return 'Escribe el título de la canción.';
    if (!_derechos) return 'Marca la casilla de derechos para poder subirla.';
    return '';
  }

  Widget _paso(int n, String titulo, Widget hijo) => Padding(
        padding: const EdgeInsets.only(bottom: Esp.xl),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              width: 24,
              height: 24,
              alignment: Alignment.center,
              decoration: BoxDecoration(color: C.acento, shape: BoxShape.circle),
              child: Text('$n', style: TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900, fontSize: 13)),
            ),
            const SizedBox(width: 10),
            Flexible(child: Text(titulo, style: estiloTituloSeccion.copyWith(fontSize: 17))),
          ]),
          const SizedBox(height: 12),
          hijo,
        ]),
      );

  Widget _audioTarjeta() {
    final tiene = _audio != null;
    return Pulsable(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: _elegirAudio,
        child: AnimatedContainer(
          duration: Mov.normal,
          padding: const EdgeInsets.all(Esp.l),
          decoration: BoxDecoration(
            color: C.superficie,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: tiene ? C.acento.withValues(alpha: 0.6) : C.borde),
          ),
          child: Row(children: [
            Icon(tiene ? Icons.audio_file_rounded : Icons.upload_file_rounded, size: 32, color: tiene ? C.acento : C.texto2),
            const SizedBox(width: 14),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(tiene ? _nombreAudio : 'Elegir un archivo de audio',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700)),
                Text(tiene ? '${(_audio!.length / 1048576).toStringAsFixed(1)} MB · toca para cambiarlo' : 'mp3, m4a, aac, flac, ogg, wav o webm · máximo 15 MB',
                    style: estiloDetalle),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _caratulaTarjeta() => Row(children: [
        Pulsable(
          child: GestureDetector(
            onTap: _elegirCaratula,
            child: AnimatedContainer(
              duration: Mov.normal,
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                color: C.superficie,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: _caratula != null ? C.acento.withValues(alpha: 0.6) : C.borde, width: 1.5),
              ),
              clipBehavior: Clip.antiAlias,
              child: _procesando
                  ? const Center(child: CircularProgressIndicator(strokeWidth: 2.5))
                  : _caratula != null
                      ? Image.memory(_caratula!, fit: BoxFit.cover)
                      : Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                          Icon(Icons.add_photo_alternate_rounded, size: 32, color: C.acento),
                          const SizedBox(height: 6),
                          const Text('Elegir imagen', style: estiloDetalle),
                        ]),
            ),
          ),
        ),
        const SizedBox(width: 16),
        const Expanded(
          child: Text('Es lo que verá la gente en su lista. Se recorta y se reduce sola para que cargue rápido.',
              style: estiloSecundario),
        ),
      ]);

  Widget _campo(String etiqueta, TextEditingController c, IconData icono, {required int max, String? ayuda}) => Padding(
        padding: const EdgeInsets.only(bottom: Esp.m),
        child: TextField(
          controller: c,
          maxLength: max,
          onChanged: (_) => setState(() {}),
          textCapitalization: TextCapitalization.words,
          decoration: InputDecoration(
            labelText: etiqueta,
            helperText: ayuda,
            helperMaxLines: 2,
            counterText: '',
            prefixIcon: Icon(icono, size: 20),
            filled: true,
            fillColor: C.superficie2,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
          ),
        ),
      );
}
