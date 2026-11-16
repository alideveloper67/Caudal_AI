import 'dart:io';
import 'dart:math';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../nucleo/social.dart';
import '../comunes.dart';
import '../tema.dart';
import 'perfil_comun.dart';

/// «Compartir mi perfil»: una imagen vertical (9:16, la medida de un estado de
/// WhatsApp o una historia) con el perfil completo: foto, nombre, títulos, frase,
/// descripción, canción favorita, géneros, artistas, insignias y los números.
Future<void> compartirPerfil(BuildContext context, Perfil perfil) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: C.superficie,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
    builder: (_) => _HojaCompartirPerfil(perfil: perfil),
  );
}

class _HojaCompartirPerfil extends StatefulWidget {
  const _HojaCompartirPerfil({required this.perfil});
  final Perfil perfil;

  @override
  State<_HojaCompartirPerfil> createState() => _HojaCompartirPerfilState();
}

class _HojaCompartirPerfilState extends State<_HojaCompartirPerfil> {
  final _clave = GlobalKey();
  int _estilo = 0; // 0 con el color del perfil · 1 oscuro · 2 claro
  bool _ocupado = false;

  static const _estilos = ['Color del perfil', 'Oscuro', 'Claro'];

  Perfil get _p => widget.perfil;
  String get _nombre => _p.nombre.trim().isNotEmpty ? _p.nombre.trim() : _p.usuario;

  Future<void> _compartirImagen() async {
    if (_ocupado) return;
    setState(() => _ocupado = true);
    try {
      await WidgetsBinding.instance.endOfFrame;
      final ro = _clave.currentContext?.findRenderObject();
      if (ro is! RenderRepaintBoundary) throw StateError('la tarjeta aún no se pintó');
      if (!mounted) return;
      final escala = min(3.5, max(2.5, MediaQuery.devicePixelRatioOf(context)));
      final imagen = await ro.toImage(pixelRatio: escala);
      final datos = await imagen.toByteData(format: ui.ImageByteFormat.png);
      imagen.dispose();
      if (datos == null) throw StateError('no se pudo dibujar la imagen');
      final bytes = datos.buffer.asUint8List();
      final nombre = 'caudal_perfil_${DateTime.now().millisecondsSinceEpoch}.png';
      XFile adjunto;
      if (kIsWeb) {
        adjunto = XFile.fromData(bytes, mimeType: 'image/png', name: nombre);
      } else {
        final dir = await getTemporaryDirectory();
        final archivo = File(p.join(dir.path, nombre));
        await archivo.writeAsBytes(bytes, flush: true);
        adjunto = XFile(archivo.path, mimeType: 'image/png');
      }
      await SharePlus.instance.share(ShareParams(files: [adjunto], text: '@${_p.usuario} en Caudal'));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text('No se pudo compartir: $e')));
      }
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.95,
      minChildSize: 0.5,
      maxChildSize: 0.97,
      builder: (_, scroll) => Column(children: [
        const SizedBox(height: 10),
        Container(width: 38, height: 4, decoration: BoxDecoration(color: C.texto3, borderRadius: BorderRadius.circular(2))),
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 14, 20, 2),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text('Compartir perfil', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          ),
        ),
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text('Una imagen lista para tu estado de WhatsApp o tus historias.', style: estiloSecundario),
          ),
        ),
        Expanded(
          child: ListView(controller: scroll, padding: const EdgeInsets.fromLTRB(20, 6, 20, 12), children: [
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 340),
                child: RepaintBoundary(
                  key: _clave,
                  child: AspectRatio(aspectRatio: 9 / 16, child: TarjetaPerfilCompartible(perfil: _p, estilo: _estilo)),
                ),
              ),
            ),
            const SizedBox(height: 14),
            Center(
              child: Wrap(spacing: 8, runSpacing: 6, alignment: WrapAlignment.center, children: [
                for (var i = 0; i < _estilos.length; i++)
                  ChoiceChip(
                    label: Text(_estilos[i]),
                    selected: _estilo == i,
                    onSelected: (_) => setState(() => _estilo = i),
                  ),
              ]),
            ),
          ]),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
            child: FilledButton.icon(
              onPressed: _ocupado ? null : _compartirImagen,
              icon: _ocupado
                  ? SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.2, color: C.acentoTexto))
                  : const Icon(Icons.ios_share_rounded),
              label: const Text('Compartir imagen'),
              style: FilledButton.styleFrom(
                  backgroundColor: C.acento, foregroundColor: C.acentoTexto,
                  minimumSize: const Size.fromHeight(50), shape: const StadiumBorder()),
            ),
          ),
        ),
      ]),
    );
  }
}

/// La tarjeta del perfil (9:16). Todo escala con el ancho, así la imagen sale
/// igual de bien en cualquier pantalla.
class TarjetaPerfilCompartible extends StatelessWidget {
  const TarjetaPerfilCompartible({super.key, required this.perfil, this.estilo = 0});
  final Perfil perfil;
  final int estilo;

  @override
  Widget build(BuildContext context) {
    final p = perfil;
    final color = colorDelPerfil(p.colorPerfil);
    final claro = estilo == 2;
    final tinta = claro ? const Color(0xFF14161B) : Colors.white;
    final tenue = claro ? const Color(0xFF14161B).withValues(alpha: 0.62) : Colors.white.withValues(alpha: 0.72);
    final fondo = switch (estilo) {
      0 => LinearGradient(
          begin: Alignment.topCenter, end: Alignment.bottomCenter,
          colors: [Color.lerp(color, Colors.black, 0.25)!, Color.lerp(color, Colors.black, 0.78)!]),
      1 => const LinearGradient(
          begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Color(0xFF10131A), Color(0xFF06070A)]),
      _ => const LinearGradient(
          begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Color(0xFFF8F6F0), Color(0xFFEAE5DA)]),
    };
    final nombre = p.nombre.trim().isNotEmpty ? p.nombre.trim() : p.usuario;
    final fav = p.cancionFav;
    final hayFav = fav != null && !fav.vacia;
    final tops = p.mostrarTop ? p.topArtistas.take(3).toList() : const <ArtistaTop>[];

    return LayoutBuilder(builder: (context, c) {
      final k = c.maxWidth / 360;
      Widget titulo(String t) => Padding(
            padding: EdgeInsets.only(bottom: 6 * k),
            child: Text(t.toUpperCase(),
                style: TextStyle(fontSize: 10 * k, fontWeight: FontWeight.w800, letterSpacing: 1.4, color: tenue)),
          );
      return ClipRRect(
        borderRadius: BorderRadius.circular(22 * k),
        child: Stack(fit: StackFit.expand, children: [
          DecoratedBox(decoration: BoxDecoration(gradient: fondo)),
          // la imagen de fondo del perfil, si tiene, tenue arriba
          if (p.bannerUrl.isNotEmpty && estilo != 2)
            Positioned(
              left: 0, right: 0, top: 0, height: 250 * k,
              child: ShaderMask(
                shaderCallback: (r) => const LinearGradient(
                  begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Colors.black, Colors.transparent],
                ).createShader(r),
                blendMode: BlendMode.dstIn,
                child: FondoBanner(color: color, bannerUrl: p.bannerUrl, alto: 250 * k, velo: 0.15),
              ),
            ),
          Padding(
            padding: EdgeInsets.fromLTRB(22 * k, 24 * k, 22 * k, 18 * k),
            child: Column(crossAxisAlignment: CrossAxisAlignment.center, children: [
              // marca
              Row(children: [
                Image.asset('assets/logo/caudal.png', width: 22 * k, height: 22 * k),
                SizedBox(width: 7 * k),
                Text('Caudal', style: TextStyle(fontSize: 15 * k, fontWeight: FontWeight.w900, color: tinta)),
                const Spacer(),
                if (p.numero != null)
                  Text('N.º ${p.numero}', style: TextStyle(fontSize: 12 * k, fontWeight: FontWeight.w800, color: tenue)),
              ]),
              SizedBox(height: 18 * k),
              // foto con aro del color del perfil
              Container(
                padding: EdgeInsets.all(3.5 * k),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: claro ? color : color.withValues(alpha: 0.95), width: 2.5 * k),
                  boxShadow: [BoxShadow(color: color.withValues(alpha: 0.45), blurRadius: 26 * k)],
                ),
                child: AvatarPerfil(nombre: nombre, fotoUrl: p.fotoUrl, color: color, radio: 52 * k),
              ),
              SizedBox(height: 12 * k),
              Text(nombre,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 26 * k, fontWeight: FontWeight.w900, height: 1.1, color: tinta, letterSpacing: -0.5)),
              SizedBox(height: 2 * k),
              Text('@${p.usuario}', style: TextStyle(fontSize: 14 * k, fontWeight: FontWeight.w700, color: tenue)),
              if (p.titulos.isNotEmpty || p.fundador || p.esArtista) ...[
                SizedBox(height: 9 * k),
                DistincionesPerfil(titulos: p.titulos, fundador: p.fundador, numero: p.numero, artista: p.esArtista, compacto: true),
              ],
              SizedBox(height: 12 * k),
              // el contenido se ajusta al espacio que queda
              Expanded(
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.topCenter,
                  child: SizedBox(
                    width: c.maxWidth - 44 * k,
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                      if (p.frase.trim().isNotEmpty)
                        Padding(
                          padding: EdgeInsets.only(bottom: 10 * k),
                          child: Center(
                            child: Text('“${p.frase.trim()}”',
                                textAlign: TextAlign.center,
                                style: TextStyle(fontSize: 15 * k, fontStyle: FontStyle.italic, fontWeight: FontWeight.w600, color: tinta, height: 1.25)),
                          ),
                        ),
                      if (p.bio.trim().isNotEmpty)
                        Padding(
                          padding: EdgeInsets.only(bottom: 12 * k),
                          child: Text(p.bio.trim(),
                              textAlign: TextAlign.center,
                              maxLines: 5,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontSize: 13.5 * k, height: 1.35, color: tenue, fontWeight: FontWeight.w500)),
                        ),
                      // los números
                      Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
                        _Numero(valor: '${p.likes}', texto: p.likes == 1 ? 'me gusta' : 'me gusta', k: k, tinta: tinta, tenue: tenue),
                        if (p.numSubidas > 0)
                          _Numero(valor: '${p.numSubidas}', texto: p.numSubidas == 1 ? 'canción subida' : 'canciones subidas', k: k, tinta: tinta, tenue: tenue),
                        if (p.insignias.isNotEmpty)
                          _Numero(valor: '${p.insignias.length}', texto: p.insignias.length == 1 ? 'insignia' : 'insignias', k: k, tinta: tinta, tenue: tenue),
                      ]),
                      if (hayFav) ...[
                        SizedBox(height: 14 * k),
                        titulo('Mi canción favorita'),
                        Container(
                          padding: EdgeInsets.all(9 * k),
                          decoration: BoxDecoration(
                            color: (claro ? Colors.black : Colors.white).withValues(alpha: claro ? 0.06 : 0.12),
                            borderRadius: BorderRadius.circular(14 * k),
                          ),
                          child: Row(children: [
                            Portada(url: fav.miniatura, lado: 52 * k, radio: 8 * k),
                            SizedBox(width: 11 * k),
                            Expanded(
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Text(fav.titulo, maxLines: 2, overflow: TextOverflow.ellipsis,
                                    style: TextStyle(fontSize: 14.5 * k, fontWeight: FontWeight.w800, color: tinta, height: 1.15)),
                                if (fav.artista.isNotEmpty)
                                  Text(fav.artista, maxLines: 1, overflow: TextOverflow.ellipsis,
                                      style: TextStyle(fontSize: 12.5 * k, color: tenue, fontWeight: FontWeight.w600)),
                              ]),
                            ),
                          ]),
                        ),
                      ],
                      if (tops.isNotEmpty) ...[
                        SizedBox(height: 14 * k),
                        titulo('Lo que más escucho'),
                        Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
                          for (final a in tops)
                            Expanded(
                              child: Column(children: [
                                ClipOval(child: Portada(url: a.portada, lado: 52 * k, circulo: true)),
                                SizedBox(height: 5 * k),
                                Text(a.nombre, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                                    style: TextStyle(fontSize: 11.5 * k, fontWeight: FontWeight.w700, color: tinta)),
                              ]),
                            ),
                        ]),
                      ],
                      if (p.generos.isNotEmpty) ...[
                        SizedBox(height: 14 * k),
                        titulo('Mis géneros'),
                        Wrap(spacing: 6 * k, runSpacing: 6 * k, children: [
                          for (final g in p.generos.take(5))
                            Container(
                              padding: EdgeInsets.symmetric(horizontal: 10 * k, vertical: 4 * k),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(color: tenue.withValues(alpha: 0.55)),
                              ),
                              child: Text(g, style: TextStyle(fontSize: 11.5 * k, fontWeight: FontWeight.w700, color: tinta)),
                            ),
                        ]),
                      ],
                      if (p.insignias.isNotEmpty) ...[
                        SizedBox(height: 14 * k),
                        titulo('Insignias'),
                        Wrap(spacing: 8 * k, runSpacing: 6 * k, children: [
                          for (final i in p.insignias.take(6))
                            Builder(builder: (_) {
                              final (icono, tono) = visualInsignia(i.clave);
                              return Row(mainAxisSize: MainAxisSize.min, children: [
                                Icon(icono, size: 16 * k, color: tono),
                                SizedBox(width: 4 * k),
                                Text(i.titulo, style: TextStyle(fontSize: 11.5 * k, fontWeight: FontWeight.w700, color: tinta)),
                              ]);
                            }),
                        ]),
                      ],
                    ]),
                  ),
                ),
              ),
              SizedBox(height: 8 * k),
              Text('Escucha música gratis en Caudal',
                  style: TextStyle(fontSize: 11.5 * k, fontWeight: FontWeight.w700, color: tenue, letterSpacing: 0.3)),
            ]),
          ),
        ]),
      );
    });
  }
}

class _Numero extends StatelessWidget {
  const _Numero({required this.valor, required this.texto, required this.k, required this.tinta, required this.tenue});
  final String valor, texto;
  final double k;
  final Color tinta, tenue;

  @override
  Widget build(BuildContext context) => Column(mainAxisSize: MainAxisSize.min, children: [
        Text(valor, style: TextStyle(fontSize: 20 * k, fontWeight: FontWeight.w900, color: tinta)),
        Text(texto, style: TextStyle(fontSize: 10.5 * k, fontWeight: FontWeight.w600, color: tenue)),
      ]);
}
