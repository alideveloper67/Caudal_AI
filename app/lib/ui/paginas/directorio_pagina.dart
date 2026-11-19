import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/nube.dart';
import '../../nucleo/social.dart';
import '../comunes.dart';
import '../premium/marcos.dart';
import '../servicios.dart';
import '../tema.dart';
import 'perfil_comun.dart';

/// «Perfiles de Caudal»: rejilla de tarjetas con buscador y paginación al
/// llegar al final. Desde la tarjeta se puede dar me gusta y enviar solicitud.
class DirectorioPagina extends StatefulWidget {
  const DirectorioPagina({super.key});

  @override
  State<DirectorioPagina> createState() => _DirectorioPaginaState();
}

class _DirectorioPaginaState extends State<DirectorioPagina> {
  static const _tanda = 24;
  final _campo = TextEditingController();
  final _scroll = ScrollController();
  Timer? _espera;
  Social? _social;
  List<PerfilTarjeta> _lista = [];
  bool _cargando = true;
  bool _masCargando = false;
  bool _fin = false;
  Object? _error;
  String _busqueda = '';
  int _vuelta = 0; // descarta respuestas de búsquedas anteriores

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      if (_scroll.position.pixels > _scroll.position.maxScrollExtent - 500) _mas();
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _social = socialDe(context);
      _cargar();
    });
  }

  @override
  void dispose() {
    _espera?.cancel();
    _campo.dispose();
    _scroll.dispose();
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
    final v = ++_vuelta;
    setState(() {
      _cargando = true;
      _error = null;
      _fin = false;
    });
    try {
      final l = await social.explorarPerfiles(busqueda: _busqueda, limite: _tanda);
      if (!mounted || v != _vuelta) return;
      setState(() {
        _lista = l;
        _fin = l.length < _tanda;
        _cargando = false;
      });
    } catch (e) {
      if (!mounted || v != _vuelta) return;
      setState(() {
        _error = e;
        _cargando = false;
      });
    }
  }

  Future<void> _mas() async {
    final social = _social;
    if (social == null || _masCargando || _fin || _cargando || _error != null) return;
    final v = _vuelta;
    setState(() => _masCargando = true);
    try {
      final l = await social.explorarPerfiles(busqueda: _busqueda, limite: _tanda, desde: _lista.length);
      if (!mounted || v != _vuelta) return;
      final ids = {for (final x in _lista) x.id};
      setState(() {
        _lista = [..._lista, ...l.where((x) => ids.add(x.id))];
        _fin = l.length < _tanda;
        _masCargando = false;
      });
    } catch (_) {
      if (mounted && v == _vuelta) {
        setState(() => _masCargando = false);
        Caudal.leer(context).avisar('No se pudieron cargar más perfiles. Sigue bajando para reintentar.');
      }
    }
  }

  void _alEscribir(String t) {
    _espera?.cancel();
    _espera = Timer(const Duration(milliseconds: 450), () {
      if (t.trim() == _busqueda) return;
      _busqueda = t.trim();
      _cargar();
    });
  }

  void _cambiar(PerfilTarjeta antes, PerfilTarjeta despues) {
    final i = _lista.indexWhere((x) => x.id == antes.id);
    if (i >= 0 && mounted) setState(() => _lista = [..._lista]..[i] = despues);
  }

  Future<void> _like(PerfilTarjeta p) async {
    final social = _social;
    if (social == null || p.esMio) return;
    final di = !p.diLike;
    _cambiar(p, p.conLike(di, (p.likes + (di ? 1 : -1)).clamp(0, 1 << 30)));
    try {
      final total = di ? await social.darLike(p.id) : await social.quitarLike(p.id);
      final actual = _lista.firstWhere((x) => x.id == p.id, orElse: () => p);
      _cambiar(actual, actual.conLike(di, total));
    } catch (e) {
      final actual = _lista.firstWhere((x) => x.id == p.id, orElse: () => p);
      _cambiar(actual, p);
      if (mounted) Caudal.leer(context).avisar(Social.error(e));
    }
  }

  Future<void> _amistad(PerfilTarjeta p) async {
    final social = _social;
    final s = Caudal.leer(context);
    if (social == null) return;
    if (p.relacion == Relacion.amigo || p.relacion == Relacion.enviada) {
      return abrirPerfil(context, p.usuario);
    }
    try {
      final r = await social.enviarSolicitud(p.id);
      s.avisar(Social.resultadoSolicitud(r, p.visible));
      final actual = _lista.firstWhere((x) => x.id == p.id, orElse: () => p);
      _cambiar(actual, actual.conRelacion(Social.relacionTras(r)));
    } catch (e) {
      s.avisar(Social.error(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Perfiles de Caudal', style: estiloTituloBarra)),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, Esp.m),
          child: TextField(
            controller: _campo,
            onChanged: _alEscribir,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: 'Busca por nombre o usuario',
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: _campo.text.isEmpty
                  ? null
                  : IconButton(
                      tooltip: 'Borrar búsqueda',
                      icon: const Icon(Icons.close_rounded),
                      onPressed: () {
                        _campo.clear();
                        _busqueda = '';
                        setState(() {});
                        _cargar();
                      }),
              filled: true,
              fillColor: C.superficie2,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide.none),
            ),
          ),
        ),
        Expanded(child: _cuerpo()),
      ]),
    );
  }

  Widget _cuerpo() {
    if (_cargando) return const Center(child: CircularProgressIndicator());
    if (_error != null && _lista.isEmpty) return errorAmable(_error!, _cargar);
    if (_lista.isEmpty) {
      return Vacio(
        icono: Icons.groups_2_rounded,
        titulo: _busqueda.isEmpty ? 'Aún no hay perfiles públicos' : 'No encontramos a nadie',
        texto: _busqueda.isEmpty
            ? 'Cuando alguien haga público su perfil, aparecerá aquí. ¡Tú puedes ser el primero desde «Editar perfil»!'
            : 'Prueba con otro nombre. Si buscas a alguien en concreto, escribe su usuario exacto en Amigos.',
      );
    }
    return RefreshIndicator(
      onRefresh: _cargar,
      child: CustomScrollView(
        controller: _scroll,
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
            sliver: SliverGrid.builder(
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 240,
                mainAxisExtent: 372,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              itemCount: _lista.length,
              itemBuilder: (_, i) {
                final p = _lista[i];
                return Entrada(
                  indice: i % 6,
                  child: TarjetaPerfil(
                    perfil: p,
                    alAbrir: () async {
                      await abrirPerfil(context, p.usuario);
                    },
                    alLike: p.esMio ? null : () => _like(p),
                    alAmistad: () => _amistad(p),
                  ),
                );
              },
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 28),
              child: Center(
                child: _masCargando
                    ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2.5))
                    : _fin
                        ? const Text('Eso es todo por ahora', style: estiloDetalle)
                        : const SizedBox.shrink(),
              ),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 90)),
        ],
      ),
    );
  }
}

/// La tarjeta de una persona en el directorio.
class TarjetaPerfil extends StatelessWidget {
  const TarjetaPerfil({super.key, required this.perfil, required this.alAbrir, this.alLike, this.alAmistad});
  final PerfilTarjeta perfil;
  final VoidCallback alAbrir;
  final VoidCallback? alLike;
  final VoidCallback? alAmistad;

  @override
  Widget build(BuildContext context) {
    final p = perfil;
    final color = colorDelPerfil(p.colorPerfil);
    final fav = p.cancionFav;
    return Pulsable(
      child: Material(
        color: Colors.transparent,
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            color: C.superficie,
            border: Border.all(color: color.withValues(alpha: 0.28)),
          ),
          child: InkWell(
            borderRadius: BorderRadius.circular(22),
            onTap: alAbrir,
            child: Stack(children: [
              // banner del perfil arriba; sin imagen, degradado con su color
              Positioned(
                left: 0,
                right: 0,
                top: 0,
                child: FondoBanner(color: color, bannerUrl: p.bannerUrl, alto: 84, radio: 22, velo: 0.35),
              ),
              Padding(
              padding: const EdgeInsets.fromLTRB(Esp.m, 44, Esp.m, Esp.m),
              child: Column(children: [
                Hero(
                  tag: 'avatar_${p.id}',
                  child: Container(
                    padding: const EdgeInsets.all(3),
                    decoration: BoxDecoration(shape: BoxShape.circle, color: C.superficie),
                    child: AvatarPerfil(nombre: p.visible, fotoUrl: p.fotoUrl, marco: p.marco, color: color, radio: 32),
                  ),
                ),
                const SizedBox(height: 6),
                NombreEfecto(p.visible, efecto: p.efectoNombre, textAlign: TextAlign.center,
                    estilo: const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800)),
                Text('@${p.usuario}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloDetalle),
                const SizedBox(height: 4),
                SizedBox(
                  height: 22,
                  child: ClipRect(
                    child: DistincionesPerfil(
                        titulos: p.titulos, fundador: p.fundador, artista: p.esArtista, compacto: true),
                  ),
                ),
                const SizedBox(height: 4),
                Expanded(
                  child: Text(p.bio.isEmpty ? 'Sin descripción todavía.' : p.bio,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 12.5, height: 1.3, color: p.bio.isEmpty ? C.texto3 : C.texto2)),
                ),
                if (fav != null)
                  Row(children: [
                    Portada(url: fav.miniatura, lado: 30, radio: 5),
                    const SizedBox(width: 7),
                    Expanded(
                      child: Text('${fav.titulo}\n${fav.artista}',
                          maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 10.5, color: C.texto2, height: 1.2)),
                    ),
                  ])
                else
                  const SizedBox(height: 30),
                const SizedBox(height: 6),
                Row(children: [
                  Icon(Icons.library_music_rounded, size: 14, color: C.texto3),
                  const SizedBox(width: 4),
                  Text('${p.numSubidas}', style: estiloDetalle),
                  const Spacer(),
                  if (alLike != null)
                    BotonLike(di: p.diLike, total: p.likes, alPulsar: alLike, compacto: true)
                  else
                    Text('${p.likes} me gusta', style: estiloDetalle),
                ]),
                if (!p.esMio && alAmistad != null)
                  SizedBox(
                    width: double.infinity,
                    child: BotonAmistad(relacion: p.relacion, alPulsar: alAmistad, compacto: true),
                  ),
              ]),
            ),
            ]),
          ),
        ),
      ),
    );
  }
}
