import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'ajustes_pagina.dart';
import 'inicio.dart';

class BibliotecaPagina extends StatefulWidget {
  const BibliotecaPagina({super.key});

  @override
  State<BibliotecaPagina> createState() => _BibliotecaPaginaState();
}

class _BibliotecaPaginaState extends State<BibliotecaPagina> with AutomaticKeepAliveClientMixin {
  String? _filtro;
  List<Json> _elementos = [];
  Coleccion? _col;
  int _vuelta = 0;

  @override
  bool get wantKeepAlive => true;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_col == null) {
      _col = Caudal.leer(context).coleccion..addListener(_cargar);
      _cargar();
    }
  }

  @override
  void dispose() {
    _col?.removeListener(_cargar);
    super.dispose();
  }

  Future<void> _cargar() async {
    final col = _col!;
    final f = _filtro;
    // si se cambia de filtro mientras carga, la respuesta vieja no pisa la nueva
    final vuelta = ++_vuelta;
    final salida = <Json>[];
    if (f == null || f == 'listas') {
      salida.add({'tipo': 'me_gusta', 'titulo': 'Tus me gusta',
        'subtitulo': 'Lista • ${col.totalMeGusta} canciones', 'fijada': true});
    }
    if (f == null || f == 'telefono') {
      final m = (await col.descargadas(soloAudio: true)).length;
      final v = (await col.descargadas(soloAudio: false)).length;
      salida.add({'tipo': 'descargados', 'id': 'musica', 'solo': true, 'titulo': 'Música descargada',
        'subtitulo': 'En tu teléfono • $m canciones', 'icono': 'musica'});
      salida.add({'tipo': 'descargados', 'id': 'videos', 'solo': false, 'titulo': 'Videos descargados',
        'subtitulo': 'En tu teléfono • $v videos', 'icono': 'video'});
    }
    if (f == null || f == 'listas') {
      for (final l in await col.listas()) {
        salida.add({'tipo': 'mi_lista', 'id': l['id'], 'titulo': l['nombre'],
          'subtitulo': 'Lista • ${l['n']} canciones',
          'mosaico': await col.portadasDeLista(Servicios.idLista(l['id']) ?? -1),
          'fijada': l['fijada'] == 1});
      }
      salida.addAll((await col.guardados('lista')).map((g) => {...g, 'subtitulo': g['subtitulo'] ?? 'Lista'}));
    }
    if (f == null || f == 'albumes') {
      salida.addAll((await col.guardados('album')).map((g) => {...g, 'subtitulo': g['subtitulo'] ?? 'Álbum'}));
    }
    if (f == null || f == 'artistas') {
      salida.addAll((await col.guardados('artista')).map((g) => {...g, 'subtitulo': 'Artista'}));
    }
    if (mounted && vuelta == _vuelta) setState(() => _elementos = salida);
  }

  Future<void> _nuevaLista() async {
    final s = Caudal.leer(context);
    final libre = await s.coleccion.nombreLibre();
    if (!mounted) return;
    final nombre = await pedirTexto(context, 'Nueva lista', libre);
    if (nombre == null) return;
    try {
      final id = await s.coleccion.crearLista(nombre);
      if (mounted) s.abrirElemento(context, {'tipo': 'mi_lista', 'id': id, 'titulo': nombre});
    } on FormatException catch (e) {
      s.avisar(e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final s = Caudal.of(context);
    return Scaffold(
      body: CustomScrollView(slivers: [
        SliverAppBar(
          pinned: true,
          backgroundColor: C.fondo,
          titleSpacing: 16,
          title: Row(children: [
            GestureDetector(
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AjustesPagina())),
              child: CircleAvatar(radius: 16, backgroundColor: C.acento,
                  child: Text(s.cuenta.inicial, style: const TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900))),
            ),
            const SizedBox(width: 12),
            const Text('Tu biblioteca', style: TextStyle(fontSize: 23, fontWeight: FontWeight.w900)),
          ]),
          actions: [IconButton(icon: const Icon(Icons.add_rounded, size: 28), onPressed: _nuevaLista)],
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(50),
            child: SizedBox(
              height: 50,
              child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
                  children: [
                if (_filtro != null)
                  Padding(padding: const EdgeInsets.only(right: 8),
                      child: ActionChip(label: const Icon(Icons.close_rounded, size: 16), backgroundColor: C.superficie2,
                          side: BorderSide.none, shape: const StadiumBorder(), onPressed: () {
                        setState(() => _filtro = null);
                        _cargar();
                      })),
                for (final (clave, texto) in const [('listas', 'Listas'), ('albumes', 'Álbumes'),
                  ('artistas', 'Artistas'), ('telefono', 'En tu teléfono')])
                  if (_filtro == null || _filtro == clave)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(texto),
                        selected: _filtro == clave,
                        showCheckmark: false,
                        selectedColor: C.acento,
                        labelStyle: TextStyle(fontWeight: FontWeight.w600,
                            color: _filtro == clave ? C.acentoTexto : C.texto),
                        backgroundColor: C.superficie2,
                        side: BorderSide.none,
                        shape: const StadiumBorder(),
                        onSelected: (_) {
                          setState(() => _filtro = _filtro == clave ? null : clave);
                          _cargar();
                        },
                      ),
                    ),
              ]),
            ),
          ),
        ),
        SliverList.builder(
          itemCount: _elementos.length,
          itemBuilder: (_, i) => _Item(el: _elementos[i]),
        ),
        const SliverToBoxAdapter(child: SizedBox(height: espacioInferior + 10)),
      ]),
    );
  }
}

class _Item extends StatelessWidget {
  const _Item({required this.el});
  final Json el;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final tipo = el['tipo'];
    Widget portada;
    if (tipo == 'me_gusta') {
      portada = const PortadaMeGusta(lado: 60, radio: 4);
    } else if (tipo == 'descargados') {
      portada = Container(
        width: 60, height: 60,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(4),
          gradient: LinearGradient(colors: el['icono'] == 'video'
              ? const [Color(0xFF7C2D12), Color(0xFFF97316)] : const [Color(0xFF0E7490), Color(0xFF22D3EE)]),
        ),
        child: Icon(el['icono'] == 'video' ? Icons.videocam_rounded : Icons.download_for_offline_rounded,
            color: Colors.white),
      );
    } else if ((el['mosaico'] as List?)?.length == 4) {
      final m = [for (final u in el['mosaico'] as List) '$u'];
      portada = ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: SizedBox(width: 60, height: 60, child: Wrap(children: [
          for (final u in m) Portada(url: u, lado: 30, radio: 0),
        ])),
      );
    } else {
      final mini = (el['mosaico'] as List?)?.isNotEmpty == true ? '${(el['mosaico'] as List).first}' : '${el['miniatura'] ?? ''}';
      portada = Portada(url: mini, lado: 60, radio: tipo == 'artista' ? 0 : 4, circulo: tipo == 'artista',
          icono: tipo == 'artista' ? Icons.person_rounded : Icons.queue_music_rounded);
    }
    return ListenableBuilder(
      listenable: s.reproductor,
      builder: (_, __) {
        final ctx = s.reproductor.contexto;
        final sonando = ctx != null && ctx['tipo'] == tipo && '${ctx['id']}' == '${el['id'] ?? tipo}' &&
            s.reproductor.estado.name != 'parado';
        return InkWell(
          onTap: () => s.abrirElemento(context, el),
          onLongPress: () => s.reproducirElemento(context, el),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
            child: Row(children: [
              portada,
              const SizedBox(width: 13),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${el['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 15.5, fontWeight: FontWeight.w600, color: sonando ? C.acento : C.texto)),
                const SizedBox(height: 3),
                Row(children: [
                  if (el['fijada'] == true) const Padding(
                    padding: EdgeInsets.only(right: 5),
                    child: Icon(Icons.push_pin_rounded, size: 13, color: C.acento),
                  ),
                  Expanded(child: Text('${el['subtitulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: estiloSecundario)),
                ]),
              ])),
              if (sonando) const Icon(Icons.volume_up_rounded, color: C.acento, size: 20),
            ]),
          ),
        );
      },
    );
  }
}
