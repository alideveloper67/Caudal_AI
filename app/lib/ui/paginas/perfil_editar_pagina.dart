import 'dart:async';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/fondo_app.dart';
import '../../nucleo/gif_perfil.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/social.dart';
import '../comunes.dart';
import '../../nucleo/cumpleanos.dart';
import '../../nucleo/premium.dart';
import '../premium/marcos.dart';
import '../premium/personalizar_pagina.dart';
import '../servicios.dart';
import '../tema.dart';
import 'donar.dart';
import 'gif_buscador.dart';
import 'perfil_comun.dart';

/// Editar el perfil propio. Se cierra con `true` si se guardó algo.
class PerfilEditarPagina extends StatefulWidget {
  const PerfilEditarPagina({super.key});

  @override
  State<PerfilEditarPagina> createState() => _PerfilEditarPaginaState();
}

class _PerfilEditarPaginaState extends State<PerfilEditarPagina> {
  static const coloresPerfil = <Color>[
    Color(0xFF22D3EE), Color(0xFF7C5CFF), Color(0xFFFF5C8A), Color(0xFFFF8A4D), Color(0xFFF5C451),
    Color(0xFF2BD576), Color(0xFF4D8DFF), Color(0xFFE05CFF), Color(0xFFFF5A5F), Color(0xFF9AA5B8),
  ];
  static const sugeridos = ['Pop', 'Rock', 'Reguetón', 'Salsa', 'Cumbia', 'Hip hop', 'Electrónica', 'Indie',
    'Baladas', 'Jazz', 'Clásica', 'Metal', 'K-pop', 'Lo-fi'];

  final _nombre = TextEditingController();
  final _frase = TextEditingController();
  final _bio = TextEditingController();
  final _artista = TextEditingController();
  final _genero = TextEditingController();

  PerfilEditable? _p;
  Social? _social;
  Object? _error;
  bool _cargando = true;
  bool _guardando = false;
  Uint8List? _fotoNueva; // ya recortada y comprimida
  Uint8List? _bannerNuevo; // imagen de fondo ya recortada (1280×480)
  bool _bannerQuitado = false;
  bool _procesandoBanner = false;
  bool _procesandoFoto = false;
  bool _fotoEsGif = false;
  bool _bannerEsGif = false;
  final GifBuscador _gifs = GifBuscador();

  /// Solo donadores y fundadores pueden poner GIF animados (lo impone el servidor).
  bool get _puedeGif => FondoApp.i.puede;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      _social = socialDe(context);
      await _cargar();
    });
  }

  @override
  void dispose() {
    _gifs.cerrar();
    for (final c in [_nombre, _frase, _bio, _artista, _genero]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _cargar() async {
    final social = _social;
    if (social == null) {
      setState(() {
        _cargando = false;
        _error = const SinConexion();
      });
      return;
    }
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final p = await social.miPerfilEditable();
      if (!mounted) return;
      _nombre.text = p.nombre;
      _frase.text = p.frase;
      _bio.text = p.bio;
      _artista.text = p.artistaFav;
      setState(() {
        _p = p;
        _cargando = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e;
          _cargando = false;
        });
      }
    }
  }

  void _aviso(String t) => Caudal.leer(context).avisar(t);

  /// Los GIF son de donadores: el aviso lleva un botón discreto para donar.
  void _avisoDonar() {
    final m = Caudal.leer(context).mensajero.currentState;
    if (m == null) return;
    m.hideCurrentSnackBar();
    m.showSnackBar(SnackBar(
      content: const Text(GifPerfil.sinPermiso),
      action: SnackBarAction(label: 'Donar aquí', onPressed: () => mostrarDonar(context)),
    ));
  }

  Future<void> _elegirFoto() async {
    if (_procesandoFoto) return;
    try {
      final r = await FilePicker.pickFiles(type: FileType.image, withData: true);
      final bytes = r?.files.firstOrNull?.bytes;
      if (bytes == null) return;
      setState(() => _procesandoFoto = true);
      if (GifPerfil.esGif(bytes, nombre: r?.files.firstOrNull?.name ?? '')) {
        if (_puedeGif) {
          final gif = await GifPerfil.preparar(bytes, foto: true);
          if (mounted) {
            setState(() {
              _fotoNueva = gif;
              _fotoEsGif = true;
            });
          }
          return;
        }
        if (mounted) _avisoDonar();
      }
      final jpeg = await ImagenSocial.foto(bytes);
      if (mounted) {
        setState(() {
          _fotoNueva = jpeg;
          _fotoEsGif = false;
        });
      }
    } catch (e) {
      if (mounted) _aviso(e is ErrorNube ? e.mensaje : 'No se pudo usar esa foto. Prueba con otra imagen.');
    } finally {
      if (mounted) setState(() => _procesandoFoto = false);
    }
  }

  Future<void> _elegirBanner() async {
    if (_procesandoBanner) return;
    try {
      final r = await FilePicker.pickFiles(type: FileType.image, withData: true);
      final bytes = r?.files.firstOrNull?.bytes;
      if (bytes == null) return;
      setState(() => _procesandoBanner = true);
      if (GifPerfil.esGif(bytes, nombre: r?.files.firstOrNull?.name ?? '')) {
        if (_puedeGif) {
          final gif = await GifPerfil.preparar(bytes, foto: false);
          if (mounted) {
            setState(() {
              _bannerNuevo = gif;
              _bannerEsGif = true;
              _bannerQuitado = false;
            });
          }
          return;
        }
        if (mounted) _avisoDonar();
      }
      final jpeg = await ImagenSocial.banner(bytes);
      if (mounted) {
        setState(() {
          _bannerNuevo = jpeg;
          _bannerEsGif = false;
          _bannerQuitado = false;
        });
      }
    } catch (e) {
      if (mounted) _aviso(e is ErrorNube ? e.mensaje : 'No se pudo usar esa imagen. Prueba con otra.');
    } finally {
      if (mounted) setState(() => _procesandoBanner = false);
    }
  }

  /// Abre la hoja de búsqueda de GIF y deja el elegido como foto o fondo.
  Future<void> _buscarGif({required bool foto}) async {
    final bytes = await showModalBottomSheet<Uint8List>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: C.superficie,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => HojaBuscarGif(buscador: _gifs, esFoto: foto),
    );
    if (bytes == null || !mounted) return;
    setState(() => foto ? _procesandoFoto = true : _procesandoBanner = true);
    try {
      final gif = await GifPerfil.preparar(bytes, foto: foto);
      if (!mounted) return;
      setState(() {
        if (foto) {
          _fotoNueva = gif;
          _fotoEsGif = true;
        } else {
          _bannerNuevo = gif;
          _bannerEsGif = true;
          _bannerQuitado = false;
        }
      });
    } catch (e) {
      if (mounted) _aviso(e is ErrorNube ? e.mensaje : 'No se pudo usar ese GIF. Prueba con otro.');
    } finally {
      if (mounted) setState(() => foto ? _procesandoFoto = false : _procesandoBanner = false);
    }
  }

  void _quitarBanner() => setState(() {
        _bannerNuevo = null;
        _bannerEsGif = false;
        _bannerQuitado = true;
      });

  Future<void> _elegirCancion() async {
    final c = await showModalBottomSheet<CancionFav>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      backgroundColor: C.superficie,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => const _BuscadorCancion(),
    );
    if (c != null && mounted) setState(() => _p = _p!.copiar(cancionFav: c));
  }

  void _agregarGenero(String g) {
    final p = _p!;
    final t = g.trim();
    if (t.isEmpty) return;
    if (p.generos.any((x) => x.toLowerCase() == t.toLowerCase())) return;
    if (p.generos.length >= 5) {
      _aviso('Puedes elegir hasta 5 géneros. Quita uno para añadir otro.');
      return;
    }
    setState(() => _p = p.copiar(generos: [...p.generos, t.length > 24 ? t.substring(0, 24) : t]));
    _genero.clear();
  }

  Future<void> _guardar() async {
    final social = _social;
    var p = _p;
    if (social == null || p == null || _guardando) return;
    if (_nombre.text.trim().isEmpty) {
      _aviso('Escribe un nombre para tu perfil.');
      return;
    }
    setState(() => _guardando = true);
    try {
      var foto = p.fotoUrl;
      if (_fotoNueva != null) foto = _fotoEsGif ? await social.subirFotoGif(_fotoNueva!) : await social.subirFoto(_fotoNueva!);
      var banner = p.bannerUrl;
      if (_bannerNuevo != null) {
        banner = _bannerEsGif ? await social.subirBannerGif(_bannerNuevo!) : await social.subirBanner(_bannerNuevo!);
      } else if (_bannerQuitado) {
        banner = '';
      }
      p = p.copiar(
        nombre: _nombre.text, frase: _frase.text, bio: _bio.text, artistaFav: _artista.text, fotoUrl: foto, bannerUrl: banner,
      );
      final quedo = await social.guardarPerfil(p);
      if (!mounted) return;
      if (p.perfilPublico && !quedo.perfilPublico) {
        _aviso('Guardado. Tu perfil sigue privado: los perfiles públicos son solo para mayores de 18 años.');
      } else if (!p.perfilPublico && quedo.perfilPublico) {
        // cuenta nueva y mayor de edad: los perfiles vienen públicos (supabase/perfil_publico_defecto.sql)
        _aviso('Guardado. Tu perfil es público, como vienen todos: puedes cerrarlo en «Privacidad».');
      } else {
        _aviso('Perfil guardado.');
      }
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        setState(() => _guardando = false);
        _aviso(Social.error(e));
      }
    }
  }

  Future<bool> _salir() async {
    if (_guardando) return false;
    final p = _p;
    if (p == null) return true;
    final cambios = _fotoNueva != null || _bannerNuevo != null || _bannerQuitado || _nombre.text != p.nombre || _frase.text != p.frase || _bio.text != p.bio ||
        _artista.text != p.artistaFav;
    if (!cambios) return true;
    return confirmar(context, '¿Salir sin guardar?', 'Los cambios que hiciste en tu perfil se perderán.', si: 'Salir');
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (hecho, _) async {
        if (hecho) return;
        if (await _salir() && context.mounted) Navigator.of(context).pop(false);
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Editar perfil', style: estiloTituloBarra),
          actions: [
            if (p != null)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: TextButton(
                  onPressed: _guardando ? null : _guardar,
                  child: _guardando
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : Text('Guardar', style: TextStyle(color: C.acento, fontWeight: FontWeight.w800, fontSize: 15)),
                ),
              ),
          ],
        ),
        body: _cargando
            ? const Center(child: CircularProgressIndicator())
            : p == null
                ? errorAmable(_error ?? const SinConexion(), _cargar)
                : _formulario(p),
      ),
    );
  }

  Widget _formulario(PerfilEditable p) {
    final color = colorDe(p);
    return ListView(
      padding: const EdgeInsets.fromLTRB(Esp.xl, Esp.m, Esp.xl, 120),
      children: [
        _vistaPrevia(p, color),
        const SizedBox(height: Esp.xl),
        _campo('Nombre', _nombre, max: 40, icono: Icons.badge_outlined),
        _campo('Frase de estado', _frase, max: 80, icono: Icons.format_quote_rounded,
            ayuda: 'Algo corto que se ve junto a tu nombre.'),
        _campo('Sobre ti', _bio, max: 300, lineas: 4, icono: Icons.notes_rounded,
            ayuda: 'Cuéntale a la comunidad qué música te mueve.'),
        _titulo('Tu canción favorita'),
        _cancion(p, color),
        const SizedBox(height: Esp.l),
        _campo('Artista favorito', _artista, max: 80, icono: Icons.mic_external_on_rounded),
        _titulo('Géneros', detalle: '${p.generos.length}/5'),
        Wrap(spacing: 8, runSpacing: 6, children: [
          for (final g in p.generos)
            InputChip(
              label: Text(g),
              onDeleted: () => setState(() => _p = p.copiar(generos: [...p.generos]..remove(g))),
              backgroundColor: color.withValues(alpha: 0.2),
              side: BorderSide(color: color.withValues(alpha: 0.4)),
            ),
        ]),
        const SizedBox(height: 8),
        Wrap(spacing: 6, runSpacing: 0, children: [
          for (final g in sugeridos.where((g) => !p.generos.contains(g)).take(8))
            ActionChip(label: Text(g), onPressed: () => _agregarGenero(g)),
        ]),
        const SizedBox(height: 8),
        TextField(
          controller: _genero,
          maxLength: 24,
          decoration: _decoracion('Otro género', Icons.add_rounded, contador: false),
          textInputAction: TextInputAction.done,
          onSubmitted: _agregarGenero,
        ),
        _titulo('Marco y efecto del nombre'),
        ListenableBuilder(
          listenable: Premium.i,
          builder: (context, _) => ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(Premium.i.activo ? Icons.auto_awesome_rounded : Icons.lock_outline_rounded,
                color: Premium.i.activo ? const Color(0xFFFFC857) : C.texto3),
            title: const Text('Personalizar'),
            subtitle: Text(
                Premium.i.activo
                    ? 'Aro animado en tu foto y efecto en tu nombre · exclusivo'
                    : 'Exclusivo para donadores · pruébalo ahí con la vista previa',
                style: estiloSecundario),
            trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PersonalizarPagina())),
          ),
        ),
        _titulo('Color de tu perfil'),
        Wrap(spacing: 12, runSpacing: 12, children: [
          for (final c in coloresPerfil)
            _Muestra(
              color: c,
              elegido: Social.hexDe(c) == p.colorPerfil.toUpperCase(),
              alPulsar: () => setState(() => _p = p.copiar(colorPerfil: Social.hexDe(c))),
            ),
          _Muestra(
            color: C.superficie3,
            elegido: p.colorPerfil.isEmpty,
            icono: Icons.format_color_reset_rounded,
            etiqueta: 'Usar el color de Caudal',
            alPulsar: () => setState(() => _p = p.copiar(colorPerfil: '')),
          ),
        ]),
        _titulo('Privacidad'),
        _interruptor(
          titulo: 'Perfil público',
          texto: p.esMenor
              ? 'Por tu edad, tu perfil se mantiene privado: solo lo ven tus amigos. Cuando cumplas 18 podrás hacerlo público.'
              : 'Aparecerás en «Perfiles de Caudal» y cualquiera podrá verlo. Si lo dejas privado, solo lo ven tus amigos.',
          valor: p.perfilPublico && !p.esMenor,
          alCambiar: p.esMenor ? null : (v) => setState(() => _p = p.copiar(perfilPublico: v)),
        ),
        _interruptor(
          titulo: 'Mostrar mis estadísticas',
          texto: 'Enseña tus artistas del mes y tus insignias en tu perfil.',
          valor: p.mostrarTop,
          alCambiar: (v) => setState(() => _p = p.copiar(mostrarTop: v)),
        ),
      ],
    );
  }

  Color colorDe(PerfilEditable p) => colorDelPerfil(p.colorPerfil);

  /// Vista previa en vivo: imagen de fondo + foto, como se verá el perfil.
  Widget _vistaPrevia(PerfilEditable p, Color color) {
    final tieneBanner = _bannerNuevo != null || (p.bannerUrl.isNotEmpty && !_bannerQuitado);
    return Column(children: [
      Stack(clipBehavior: Clip.none, alignment: Alignment.bottomCenter, children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: SizedBox(
            height: 150,
            width: double.infinity,
            child: _bannerNuevo != null
                ? Stack(fit: StackFit.expand, children: [
                    Image.memory(_bannerNuevo!, fit: BoxFit.cover),
                    DecoratedBox(
                        decoration: BoxDecoration(
                            gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter,
                                colors: [Colors.black26, Colors.black.withValues(alpha: 0.55)]))),
                  ])
                : FondoBanner(color: color, bannerUrl: _bannerQuitado ? '' : p.bannerUrl, alto: 150, radio: 20),
          ),
        ),
        Positioned(
          right: 10,
          top: 10,
          child: Row(children: [
            if (tieneBanner)
              IconButton.filled(
                tooltip: 'Quitar imagen de fondo',
                style: IconButton.styleFrom(backgroundColor: Colors.black54, foregroundColor: Colors.white),
                icon: const Icon(Icons.delete_outline_rounded, size: 20),
                onPressed: _quitarBanner,
              ),
            const SizedBox(width: 6),
            IconButton.filled(
              tooltip: tieneBanner ? 'Cambiar imagen de fondo' : 'Elegir imagen de fondo',
              style: IconButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto),
              icon: _procesandoBanner
                  ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: C.acentoTexto))
                  : const Icon(Icons.wallpaper_rounded, size: 20),
              onPressed: _elegirBanner,
            ),
          ]),
        ),
        Positioned(bottom: -50, child: _foto(p, color)),
      ]),
      const SizedBox(height: 56),
      if (_puedeGif) ...[
        Wrap(alignment: WrapAlignment.center, spacing: 8, runSpacing: 8, children: [
          _botonGif('Buscar GIF (foto)', () => _buscarGif(foto: true), _procesandoFoto),
          _botonGif('Buscar GIF (fondo)', () => _buscarGif(foto: false), _procesandoBanner),
        ]),
        const SizedBox(height: 10),
      ],
      Text(_bannerNuevo != null ? 'Imagen lista. Se subirá al guardar.' : tieneBanner ? 'Toca el icono para cambiar tu imagen de fondo' : 'Añade una imagen de fondo a tu perfil',
          style: estiloDetalle),
    ]);
  }

  Widget _botonGif(String texto, VoidCallback alPulsar, bool ocupado) => OutlinedButton(
        onPressed: ocupado ? null : alPulsar,
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.gif_box_rounded, size: 18),
          const SizedBox(width: 6),
          Flexible(child: Text(texto, overflow: TextOverflow.ellipsis, maxLines: 1)),
          const SizedBox(width: 8),
          const InsigniaGifDonador(),
        ]),
      );

  Widget _foto(PerfilEditable p, Color color) => Column(children: [
        GestureDetector(
          onTap: _elegirFoto,
          child: Stack(alignment: Alignment.bottomRight, children: [
            Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: AvatarMarco.tiene(Premium.i.marcoEfectivo) ? null : Border.all(color: color, width: 2.5)),
              child: _fotoNueva != null
                  ? ClipOval(child: Image.memory(_fotoNueva!, width: 104, height: 104, fit: BoxFit.cover,
                      cacheWidth: (104 * MediaQuery.devicePixelRatioOf(context)).round()))
                  : AvatarPerfil(nombre: _nombre.text.isEmpty ? p.nombre : _nombre.text, fotoUrl: p.fotoUrl, color: color, radio: 52,
                      marco: Premium.i.marcoEfectivo, userId: Cumpleanos.i.miId),
            ),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(color: C.acento, shape: BoxShape.circle, border: Border.all(color: C.fondo, width: 3)),
              child: _procesandoFoto
                  ? SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: C.acentoTexto))
                  : Icon(Icons.photo_camera_rounded, size: 16, color: C.acentoTexto),
            ),
          ]),
        ),
      ]);

  Widget _cancion(PerfilEditable p, Color color) {
    final c = p.cancionFav;
    return Pulsable(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: _elegirCancion,
        child: Container(
          padding: const EdgeInsets.all(Esp.m),
          decoration: BoxDecoration(
            color: C.superficie,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: color.withValues(alpha: 0.3)),
          ),
          child: Row(children: [
            Portada(url: c?.miniatura ?? '', lado: 64, radio: 10),
            const SizedBox(width: 12),
            Expanded(
              child: c == null
                  ? const Text('Elegir una canción del buscador', style: TextStyle(color: C.texto2, fontSize: 15))
                  : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(c.titulo, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800)),
                      Text(c.artista, maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                    ]),
            ),
            if (c != null)
              IconButton(
                tooltip: 'Quitar canción favorita',
                icon: const Icon(Icons.close_rounded),
                onPressed: () => setState(() => _p = p.copiar(cancionFav: null)),
              )
            else
              const Icon(Icons.search_rounded, color: C.texto2),
          ]),
        ),
      ),
    );
  }

  Widget _titulo(String t, {String? detalle}) => Padding(
        padding: const EdgeInsets.only(top: Esp.entreSecciones - 8, bottom: 10),
        child: Row(children: [
          Text(t, style: estiloTituloSeccion.copyWith(fontSize: 18)),
          if (detalle != null) ...[const SizedBox(width: 8), Text(detalle, style: estiloSecundario)],
        ]),
      );

  InputDecoration _decoracion(String etiqueta, IconData icono, {String? ayuda, bool contador = true}) => InputDecoration(
        labelText: etiqueta,
        helperText: ayuda,
        helperMaxLines: 2,
        counterText: contador ? null : '',
        prefixIcon: Icon(icono, size: 20),
        filled: true,
        fillColor: C.superficie2,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
      );

  Widget _campo(String etiqueta, TextEditingController c,
          {required int max, int lineas = 1, required IconData icono, String? ayuda}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: Esp.m),
        child: TextField(
          controller: c,
          maxLength: max,
          minLines: lineas,
          maxLines: lineas == 1 ? 1 : lineas + 2,
          textCapitalization: TextCapitalization.sentences,
          onChanged: (_) => setState(() {}),
          decoration: _decoracion(etiqueta, icono, ayuda: ayuda),
        ),
      );

  Widget _interruptor({required String titulo, required String texto, required bool valor, required ValueChanged<bool>? alCambiar}) =>
      Container(
        margin: const EdgeInsets.only(bottom: Esp.s),
        decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(16)),
        child: SwitchListTile(
          value: valor,
          onChanged: alCambiar,
          title: Text(titulo, style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text(texto, style: estiloSecundario),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      );
}

class _Muestra extends StatelessWidget {
  const _Muestra({required this.color, required this.elegido, required this.alPulsar, this.icono, this.etiqueta});
  final Color color;
  final bool elegido;
  final VoidCallback alPulsar;
  final IconData? icono;
  final String? etiqueta;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        selected: elegido,
        label: etiqueta ?? 'Color del perfil',
        child: GestureDetector(
          onTap: alPulsar,
          child: AnimatedContainer(
            duration: Mov.normal,
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
              border: Border.all(color: elegido ? Colors.white : Colors.transparent, width: 3),
              boxShadow: elegido ? [BoxShadow(color: color.withValues(alpha: 0.6), blurRadius: 14)] : null,
            ),
            child: elegido
                ? const Icon(Icons.check_rounded, color: Colors.white, size: 20)
                : icono == null ? null : Icon(icono, size: 18, color: C.texto2),
          ),
        ),
      );
}

/// Hoja para buscar la canción favorita en el catálogo.
class _BuscadorCancion extends StatefulWidget {
  const _BuscadorCancion();

  @override
  State<_BuscadorCancion> createState() => _BuscadorCancionState();
}

class _BuscadorCancionState extends State<_BuscadorCancion> {
  final _campo = TextEditingController();
  Timer? _espera;
  List<Map<String, dynamic>> _res = const [];
  bool _buscando = false;
  String? _fallo;
  String _ultima = '';

  @override
  void dispose() {
    _espera?.cancel();
    _campo.dispose();
    super.dispose();
  }

  void _alEscribir(String t) {
    _espera?.cancel();
    if (t.trim().length < 2) {
      setState(() {
        _res = const [];
        _fallo = null;
        _buscando = false;
      });
      return;
    }
    setState(() => _buscando = true);
    _espera = Timer(const Duration(milliseconds: 450), () async {
      _ultima = t.trim();
      try {
        final r = await Catalogo.buscar(_ultima, filtro: 'canciones', limite: 15);
        if (!mounted || _ultima != t.trim()) return;
        setState(() {
          _res = [for (final x in r) if ('${x['video_id'] ?? ''}'.isNotEmpty) x];
          _buscando = false;
          _fallo = null;
        });
      } catch (_) {
        if (mounted) {
          setState(() {
            _buscando = false;
            _fallo = 'No se pudo buscar ahora. Revisa tu internet e inténtalo otra vez.';
          });
        }
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final alto = MediaQuery.sizeOf(context).height * 0.8;
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SizedBox(
        height: alto,
        child: Column(children: [
          const SizedBox(height: 10),
          Container(width: 38, height: 4, decoration: BoxDecoration(color: C.borde, borderRadius: BorderRadius.circular(4))),
          Padding(
            padding: const EdgeInsets.all(Esp.l),
            child: TextField(
              controller: _campo,
              autofocus: true,
              onChanged: _alEscribir,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Busca tu canción favorita',
                prefixIcon: const Icon(Icons.search_rounded),
                filled: true,
                fillColor: C.superficie2,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide.none),
              ),
            ),
          ),
          Expanded(
            child: _buscando && _res.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : _fallo != null
                    ? Center(child: Padding(padding: const EdgeInsets.all(Esp.xl), child: Text(_fallo!, textAlign: TextAlign.center, style: estiloSecundario)))
                    : _res.isEmpty
                        ? Center(child: Text(_campo.text.trim().length < 2 ? 'Escribe el nombre de una canción o artista.' : 'No encontramos nada con esa búsqueda.',
                            style: estiloSecundario))
                        : ListView.builder(
                            itemCount: _res.length,
                            itemBuilder: (_, i) {
                              final x = _res[i];
                              return ListTile(
                                leading: Portada(url: '${x['miniatura'] ?? ''}', lado: 48, radio: 6),
                                title: Text('${x['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
                                subtitle: Text('${x['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                                onTap: () => Navigator.pop(context, CancionFav.dePista(x)),
                              );
                            },
                          ),
          ),
        ]),
      ),
    );
  }
}
