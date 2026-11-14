import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/coleccion.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'inicio.dart';

class BuscarPagina extends StatefulWidget {
  const BuscarPagina({super.key});

  static final ValueNotifier<int> _enfocar = ValueNotifier(0);

  /// Tocar la pestana Buscar estando ya en ella: el campo se enfoca y el
  /// teclado sale (como en Spotify). Lo llama la barra de abajo.
  static void enfocar() => _enfocar.value++;

  @override
  State<BuscarPagina> createState() => _BuscarPaginaState();
}

class _BuscarPaginaState extends State<BuscarPagina> with AutomaticKeepAliveClientMixin {
  final _campo = TextEditingController();
  final _foco = FocusNode();
  Timer? _espera;
  String _consulta = '';
  String _filtro = 'todo';
  List<String> _sugerencias = [];
  List<String> _recientes = [];
  Map<String, dynamic>? _todo;
  List<Json>? _lista;
  bool _buscando = false;
  String? _error;
  // cada peticion lleva su numero: las respuestas viejas no pisan a las nuevas
  int _peticion = 0;
  static Map<String, dynamic>? _explorar;
  final Map<String, Object> _cache = {};

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      final recientes = await Caudal.leer(context).coleccion.busquedasRecientes();
      if (!mounted) return;
      setState(() => _recientes = recientes);
      if (_explorar == null) await _cargarExplorar();
    });
    _foco.addListener(_alCambiarFoco);
    BuscarPagina._enfocar.addListener(_alPedirFoco);
  }

  void _alPedirFoco() {
    if (!mounted) return;
    // si habia una pagina abierta encima, la barra ya volvio a la raiz
    _campo.selection = TextSelection(baseOffset: 0, extentOffset: _campo.text.length);
    _foco.requestFocus();
  }

  bool _explorarFallo = false;

  Future<void> _cargarExplorar() async {
    if (_explorarFallo) setState(() => _explorarFallo = false);
    try {
      _explorar = await Catalogo.explorar();
      if (mounted) setState(() {});
    } catch (_) {
      // sin red: en vez de un esqueleto eterno, un aviso con Reintentar
      if (mounted) setState(() => _explorarFallo = true);
    }
  }

  void _alCambiarFoco() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _espera?.cancel();
    BuscarPagina._enfocar.removeListener(_alPedirFoco);
    _foco.removeListener(_alCambiarFoco);
    _campo.dispose();
    _foco.dispose();
    super.dispose();
  }

  bool _esEnlace(String t) => RegExp(r'https?://').hasMatch(t);

  void _alEscribir(String texto) {
    _espera?.cancel();
    if (texto.trim().isEmpty) {
      _peticion++;
      setState(() {
        _sugerencias = [];
        _consulta = '';
        _todo = null;
        _lista = null;
        _buscando = false;
        _error = null;
      });
      return;
    }
    // la cruz de borrar aparece o desaparece con el texto
    if (_sugerencias.isEmpty) setState(() {});
    _espera = Timer(const Duration(milliseconds: 260), () async {
      if (_esEnlace(texto)) return;
      final s = await Catalogo.sugerencias(texto).catchError((_) => <String>[]);
      if (mounted && _campo.text == texto && _consulta != texto.trim()) setState(() => _sugerencias = s);
    });
  }

  Future<void> _buscar(String texto) async {
    texto = texto.trim();
    if (texto.isEmpty) return;
    _foco.unfocus();
    _espera?.cancel();
    final s = Caudal.leer(context);
    if (_esEnlace(texto)) {
      s.abrirEnlace?.call(texto);
      return;
    }
    _campo.text = texto;
    setState(() {
      _consulta = texto;
      _sugerencias = [];
      _error = null;
    });
    await s.coleccion.anotarBusqueda(texto);
    final recientes = await s.coleccion.busquedasRecientes();
    if (!mounted) return;
    _recientes = recientes;
    await _cargarFiltro();
  }

  Future<void> _cargarFiltro() async {
    if (!mounted || _consulta.isEmpty) return;
    final consulta = _consulta;
    final filtro = _filtro;
    final clave = '$consulta|$filtro';
    final numero = ++_peticion;
    final hecho = _cache[clave];
    if (hecho != null) {
      setState(() {
        _error = null;
        _buscando = false;
        if (hecho is Map<String, dynamic>) {
          _todo = hecho;
        } else if (hecho is List<Json>) {
          _lista = hecho;
        }
      });
      return;
    }
    setState(() {
      _buscando = true;
      _error = null;
      if (filtro == 'todo') {
        _todo = null;
      } else {
        _lista = null;
      }
    });
    try {
      final Object r;
      if (filtro == 'todo') {
        r = await Catalogo.buscarTodo(consulta);
      } else {
        r = [
          for (final e in await Catalogo.buscar(consulta, filtro: filtro, limite: 40))
            Map<String, dynamic>.from(e)
        ];
      }
      _cache[clave] = r;
      if (!mounted || numero != _peticion) return;
      setState(() {
        _buscando = false;
        if (r is Map<String, dynamic>) {
          _todo = r;
        } else {
          _lista = r as List<Json>;
        }
      });
    } catch (e) {
      if (mounted && numero == _peticion) {
        setState(() {
          _buscando = false;
          _error = '$e';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final arriba = MediaQuery.paddingOf(context).top;
    return Scaffold(
      body: Column(children: [
        Container(
          color: C.fondo,
          padding: EdgeInsets.fromLTRB(16, arriba + 12, 16, 8),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            // el titulo se recoge con suavidad al escribir (sin que el campo salte)
            AnimatedSize(
              duration: Mov.normal,
              curve: Mov.curva,
              alignment: Alignment.topLeft,
              child: !_foco.hasFocus && _consulta.isEmpty
                  ? const Padding(padding: EdgeInsets.only(bottom: Esp.m),
                      child: SizedBox(width: double.infinity, child: Text('Buscar', style: estiloTituloPagina)))
                  : const SizedBox(width: double.infinity),
            ),
            TextField(
              controller: _campo,
              focusNode: _foco,
              textInputAction: TextInputAction.search,
              onChanged: _alEscribir,
              onSubmitted: _buscar,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              decoration: InputDecoration(
                hintText: '¿Qué quieres escuchar o ver?  ·  o pega un enlace',
                prefixIcon: const Icon(Icons.search_rounded, color: C.texto2),
                suffixIcon: _campo.text.isEmpty
                    ? null
                    : IconButton(icon: const Icon(Icons.close_rounded), onPressed: () {
                        _campo.clear();
                        _alEscribir('');
                      }),
                fillColor: _foco.hasFocus ? C.superficie3 : C.texto,
                hintStyle: TextStyle(color: _foco.hasFocus ? C.texto3 : const Color(0xFF3A3F4A)),
              ),
              cursorColor: C.acento,
            ),
            AnimatedSize(
              duration: Mov.normal,
              curve: Mov.curva,
              alignment: Alignment.topLeft,
              child: _consulta.isNotEmpty && _sugerencias.isEmpty && !_foco.hasFocus
                  ? Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: SingleChildScrollView(
                        key: const PageStorageKey('buscar|filtros'),
                        scrollDirection: Axis.horizontal,
                        child: Row(children: [
                          for (final (clave, texto) in const [('todo', 'Todo'), ('canciones', 'Canciones'),
                            ('videos', 'Videos'), ('albumes', 'Álbumes'), ('artistas', 'Artistas'), ('listas', 'Listas')])
                            Pildora(texto: texto, activa: _filtro == clave, alPulsar: () => _elegirFiltro(clave)),
                        ]),
                      ),
                    )
                  : const SizedBox(width: double.infinity),
            ),
          ]),
        ),
        Expanded(
          // de un estado a otro (explorar, sugerencias, cargando, resultados) con un fundido
          child: AnimatedSwitcher(
            duration: Mov.normal,
            switchInCurve: Mov.curva,
            switchOutCurve: Curves.easeIn,
            layoutBuilder: (actual, previos) => Stack(alignment: Alignment.topCenter, children: [...previos, ?actual]),
            child: KeyedSubtree(key: ValueKey(_estado()), child: _cuerpo()),
          ),
        ),
      ]),
    );
  }

  void _elegirFiltro(String clave) {
    if (clave == _filtro) return;
    setState(() => _filtro = clave);
    _cargarFiltro();
  }

  /// Que se esta viendo; al cambiar, el cuerpo cambia con un fundido.
  String _estado() {
    final texto = _campo.text.trim();
    if (_foco.hasFocus && texto.isNotEmpty && _esEnlace(texto)) return 'enlace';
    if (_sugerencias.isNotEmpty && _foco.hasFocus) return 'sugerencias';
    if (_consulta.isEmpty) return 'explorar';
    if (_error != null) return 'error';
    if (_buscando) return 'buscando|$_filtro';
    return 'resultados|$_consulta|$_filtro';
  }

  Widget _cuerpo() {
    final s = Caudal.leer(context);
    final texto = _campo.text.trim();
    if (_foco.hasFocus && texto.isNotEmpty && _esEnlace(texto)) {
      return ListView(padding: EdgeInsets.zero, children: [
        ListTile(
          leading: const Icon(Icons.link_rounded, color: C.acento),
          title: const Text('Abrir este enlace', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text(texto, maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
          onTap: () => _buscar(texto),
        ),
      ]);
    }
    if (_sugerencias.isNotEmpty && _foco.hasFocus) {
      return ListView(padding: EdgeInsets.zero, children: [
        for (final sug in _sugerencias)
          ListTile(
            leading: const Icon(Icons.search_rounded, color: C.texto3),
            title: Text(sug),
            trailing: IconButton(
              icon: const Icon(Icons.north_west_rounded, color: C.texto3, size: 20),
              onPressed: () {
                _campo.text = sug;
                _campo.selection = TextSelection.collapsed(offset: sug.length);
                _alEscribir(sug);
              },
            ),
            onTap: () => _buscar(sug),
          ),
      ]);
    }
    if (_consulta.isEmpty) return _explorarTodo();
    if (_error != null) {
      return Vacio(icono: Icons.wifi_off_rounded, titulo: 'No se pudo buscar', texto: explicarError(_error),
          error: true, alAccion: _cargarFiltro);
    }
    if (_buscando) return const Esqueleto(filas: true);
    if (_filtro == 'todo') {
      final t = _todo;
      if (t == null) return const SizedBox.shrink();
      final principal = t['principal'] is Map ? Map<String, dynamic>.from(t['principal'] as Map) : null;
      final secciones = [
        for (final e in (t['secciones'] is List ? t['secciones'] as List : const []))
          if (e is Map) Map<String, dynamic>.from(e)
      ];
      if (principal == null && secciones.isEmpty) {
        return Vacio(icono: Icons.search_off_rounded, titulo: 'Sin resultados para «$_consulta»',
            texto: 'Revisa cómo está escrito o prueba con menos palabras.',
            textoAccion: 'Buscar otra cosa', iconoAccion: Icons.edit_rounded, alAccion: _alPedirFoco);
      }
      final canciones = secciones.where((x) => x['filtro'] == 'canciones').firstOrNull;
      final pistas = [
        for (final e in (canciones?['elementos'] is List ? canciones!['elementos'] as List : const []))
          if (e is Map) Map<String, dynamic>.from(e)
      ];
      var turno = 0;
      return Escalonado(
        clave: _estado(),
        child: ListView(key: PageStorageKey('buscar|$_consulta|todo'),
            padding: const EdgeInsets.only(top: 6, bottom: espacioInferior), children: [
          if (principal != null) Entrada(indice: turno++, child: _Principal(el: principal)),
          if (pistas.isNotEmpty) ...[
            const SizedBox(height: 22),
            Entrada(indice: turno, child: TituloSeccion('Canciones', alPulsarMas: () => _elegirFiltro('canciones'))),
            for (var i = 0; i < pistas.length && i < 5; i++)
              Entrada(indice: turno + i, child: FilaPista(pista: pistas[i], alPulsar: () => s.reproducirPista(context, pistas[i]))),
          ],
          const SizedBox(height: Esp.xl),
          for (final (i, sec) in secciones.where((x) => x['filtro'] != 'canciones').indexed) ...[
            Entrada(indice: turno + 3 + i, child: Carrusel(titulo: '${sec['titulo']}',
                elementos: sec['elementos'] as List? ?? const [], alPulsarMas: () => _elegirFiltro('${sec['filtro']}'))),
            const SizedBox(height: Esp.entreSecciones),
          ],
        ]),
      );
    }
    final lista = _lista ?? [];
    if (lista.isEmpty) {
      return Vacio(icono: Icons.search_off_rounded, titulo: 'Sin resultados',
          texto: 'Aquí no salió nada. En «Todo» se busca en canciones, videos, álbumes y artistas a la vez.',
          textoAccion: 'Ver en Todo', iconoAccion: Icons.travel_explore_rounded, alAccion: () => _elegirFiltro('todo'));
    }
    final clave = PageStorageKey('buscar|$_consulta|$_filtro');
    if (_filtro == 'canciones' || _filtro == 'videos') {
      return Escalonado(
        clave: _estado(),
        child: ListView.builder(
          key: clave,
          padding: const EdgeInsets.only(top: 4, bottom: espacioInferior),
          itemCount: lista.length,
          itemBuilder: (_, i) => Entrada(indice: i,
              child: FilaPista(pista: lista[i], alPulsar: () => s.reproducirPista(context, lista[i]))),
        ),
      );
    }
    return Escalonado(
      clave: _estado(),
      child: ListView.builder(
        key: clave,
        padding: const EdgeInsets.only(top: 4, bottom: espacioInferior),
        itemCount: lista.length,
        itemBuilder: (_, i) {
          final el = lista[i];
          return Entrada(
            indice: i,
            child: Pulsable(
              escala: 0.985,
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 2),
                leading: Portada(url: '${el['miniatura'] ?? ''}', lado: 54, radio: 4, circulo: el['tipo'] == 'artista',
                    icono: el['tipo'] == 'artista' ? Icons.person_rounded
                        : el['tipo'] == 'album' ? Icons.album_rounded : Icons.queue_music_rounded),
                title: Text('${el['titulo']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloTituloFila),
                subtitle: Text('${el['subtitulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: estiloSecundario),
                onTap: () => s.abrirElemento(context, el),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _explorarTodo() {
    final generos = <Json>[];
    for (final sec in (_explorar?['secciones'] as List? ?? [])) {
      if (sec is! Map) continue;
      for (final e in (sec['elementos'] is List ? sec['elementos'] as List : const [])) {
        if (e is Map && e['tipo'] == 'genero') generos.add(Map<String, dynamic>.from(e));
      }
    }
    return Escalonado(
      clave: generos.isNotEmpty,
      child: ListView(key: const PageStorageKey('buscar|explorar'),
          padding: const EdgeInsets.only(bottom: espacioInferior), children: [
        if (_recientes.isNotEmpty) ...[
          Padding(
            padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.s, Esp.xs),
            child: Row(children: [
              const Expanded(child: Text('Búsquedas recientes', style: estiloTituloSeccion)),
              TextButton(onPressed: () async {
                await Caudal.leer(context).coleccion.borrarBusquedas();
                if (mounted) setState(() => _recientes = []);
              }, style: TextButton.styleFrom(foregroundColor: C.texto2), child: const Text('Borrar')),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
            child: Wrap(children: [
              for (final r in _recientes) Pildora(texto: r, activa: false, alPulsar: () => _buscar(r)),
            ]),
          ),
          const SizedBox(height: Esp.xl),
        ],
        if (generos.isNotEmpty)
          Entrada(child: RejillaTarjetas(titulo: 'Explorar todo', elementos: generos))
        else if (_explorarFallo)
          Vacio(icono: Icons.wifi_off_rounded, titulo: 'Sin conexión', error: true,
              texto: 'Puedes buscar igual cuando vuelva internet.', alAccion: _cargarExplorar)
        else if (_explorar == null)
          const Esqueleto(forma: FormaEsqueleto.generos),
      ]),
    );
  }
}

class _Principal extends StatelessWidget {
  const _Principal({required this.el});
  final Json el;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.leer(context);
    final tipo = {'pista': el['es_video'] == true ? 'Video' : 'Canción', 'album': 'Álbum',
      'artista': 'Artista', 'lista': 'Lista'}[el['tipo']] ?? '';
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
      child: Pulsable(escala: 0.98, child: Material(
        color: C.superficie2,
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () => s.abrirElemento(context, el),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(children: [
              Portada(url: '${el['miniatura'] ?? ''}', lado: 84, radio: 6, circulo: el['tipo'] == 'artista'),
              const SizedBox(width: 14),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${el['titulo']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 4),
                  Text(el['tipo'] == 'album' ? '${el['subtitulo'] ?? tipo}' :
                      ['$tipo', if ('${el['artista'] ?? ''}'.isNotEmpty) '${el['artista']}'].join('  •  '),
                      maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
                ]),
              ),
              BotonPlay(lado: 46, alPulsar: () => s.reproducirElemento(context, el)),
            ]),
          ),
        ),
      )),
    );
  }
}
