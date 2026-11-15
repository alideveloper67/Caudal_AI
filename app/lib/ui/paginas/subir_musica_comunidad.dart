import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/nube.dart';
import '../../nucleo/social.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'perfil_comun.dart';
import 'subir_musica_pagina.dart';

/// «Comunidad»: el catálogo de música subida por la gente, con buscador.
/// Se puede escuchar, reportar y (lo propio) borrar.
class ComunidadPagina extends StatefulWidget {
  const ComunidadPagina({super.key});

  @override
  State<ComunidadPagina> createState() => _ComunidadPaginaState();
}

class _ComunidadPaginaState extends State<ComunidadPagina> {
  static const _tanda = 30;
  final _campo = TextEditingController();
  final _scroll = ScrollController();
  Timer? _espera;
  Social? _social;
  List<Subida> _lista = [];
  bool _cargando = true;
  bool _masCargando = false;
  bool _fin = false;
  Object? _error;
  String _busqueda = '';
  int _vuelta = 0;

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
      final l = await social.explorarSubidas(busqueda: _busqueda, limite: _tanda);
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
      final l = await social.explorarSubidas(busqueda: _busqueda, limite: _tanda, desde: _lista.length);
      if (!mounted || v != _vuelta) return;
      final ids = {for (final x in _lista) x.id};
      setState(() {
        _lista = [..._lista, ...l.where((x) => ids.add(x.id))];
        _fin = l.length < _tanda;
        _masCargando = false;
      });
    } catch (_) {
      if (mounted && v == _vuelta) setState(() => _masCargando = false);
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

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Comunidad', style: estiloTituloBarra)),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: C.acento,
        foregroundColor: C.acentoTexto,
        onPressed: () async {
          final subida = await Navigator.of(context)
              .push<bool>(MaterialPageRoute(builder: (_) => const SubirMusicaPagina()));
          if (subida == true) _cargar();
        },
        icon: const Icon(Icons.cloud_upload_rounded),
        label: const Text('Subir música'),
      ),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, Esp.s),
          child: TextField(
            controller: _campo,
            onChanged: (t) {
              setState(() {});
              _alEscribir(t);
            },
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: 'Busca por título o artista',
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
        Expanded(
          child: _cargando
              ? const Center(child: CircularProgressIndicator())
              : _error != null && _lista.isEmpty
                  ? errorAmable(_error!, _cargar)
                  : _lista.isEmpty
                      ? Vacio(
                          icono: Icons.library_music_outlined,
                          titulo: _busqueda.isEmpty ? 'Aún no hay música en la comunidad' : 'No encontramos esa canción',
                          texto: _busqueda.isEmpty
                              ? 'Sé la primera persona en compartir una canción con carátula. Toca «Subir música».'
                              : 'Prueba con otro título o con el nombre del artista.',
                        )
                      : RefreshIndicator(
                          onRefresh: _cargar,
                          child: ListView.builder(
                            controller: _scroll,
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.only(bottom: 140),
                            itemCount: _lista.length + 1,
                            itemBuilder: (_, i) {
                              if (i == _lista.length) {
                                return Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 24),
                                  child: Center(
                                    child: _masCargando
                                        ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
                                        : _fin
                                            ? const Text('Eso es todo por ahora', style: estiloDetalle)
                                            : const SizedBox.shrink(),
                                  ),
                                );
                              }
                              final x = _lista[i];
                              final mia = x.userId == s.cuenta.id;
                              return Entrada(
                                indice: i % 8,
                                child: ListenableBuilder(
                                  listenable: s.reproductor,
                                  builder: (context, _) => FilaSubida(
                                    subida: x,
                                    sonando: suenaSubida(s, x),
                                    alReproducir: () => reproducirSubida(context, _social, _lista, i),
                                    alAbrirPerfil: x.usuario.isEmpty ? null : () => abrirPerfil(context, x.usuario),
                                    alReportar: mia ? null : () => reportarSubidaDialogo(context, _social, x),
                                    alBorrar: mia
                                        ? () async {
                                            if (await borrarSubidaDialogo(context, _social, x)) {
                                              setState(() => _lista = _lista.where((e) => e.id != x.id).toList());
                                            }
                                          }
                                        : null,
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
        ),
      ]),
    );
  }
}
