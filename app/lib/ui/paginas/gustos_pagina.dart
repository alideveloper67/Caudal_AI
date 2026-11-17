import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../nucleo/catalogo.dart';
import '../../nucleo/gustos.dart';
import '../../nucleo/nube.dart';
import '../comunes.dart';
import '../tema.dart';

/// Busca artistas en el catálogo (se puede cambiar en las pruebas).
typedef BuscadorArtistas = Future<List<ArtistaGusto>> Function(String texto);

/// El catálogo de YouTube Music: artistas que casan con el texto.
Future<List<ArtistaGusto>> buscarArtistasCatalogo(String texto) async {
  final r = await Catalogo.buscar(texto, filtro: 'artistas', limite: 18);
  return [
    for (final e in r)
      if (e['tipo'] == 'artista' && '${e['titulo'] ?? ''}'.trim().isNotEmpty)
        ArtistaGusto(nombre: '${e['titulo']}'.trim(), id: '${e['id'] ?? ''}', portada: '${e['miniatura'] ?? ''}'),
  ];
}

/// Artistas populares de la región (búsquedas predefinidas: si alguna falla, se salta).
const artistasSugeridos = [
  'Bad Bunny', 'Karol G', 'Shakira', 'Grupo 5', 'Corazón Serrano', 'Feid', 'Peso Pluma', 'Marc Anthony',
  'Juan Luis Guerra', 'Los Ángeles Azules', 'Soda Stereo', 'Daddy Yankee', 'Maluma', 'Rosalía',
  'Taylor Swift', 'The Weeknd', 'Coldplay', 'Dua Lipa', 'Ed Sheeran', 'Linkin Park', 'Billie Eilish',
  'Drake', 'Queen', 'Michael Jackson', 'Armonía 10', 'Hermanos Yaipén', 'Mon Laferte', 'Juanes',
];

/// «¿Qué artistas te gustan?»: pantalla completa para elegir favoritos.
///
/// Sale tras crear la cuenta (y al entrar con una cuenta que aún no eligió) y
/// también desde Ajustes → «Mis artistas favoritos». Guarda con [Gustos.guardar]
/// y avisa con [alTerminar] (nunca se queda trabada: sin red queda guardado en
/// este equipo y se sube luego).
class GustosPagina extends StatefulWidget {
  const GustosPagina({
    super.key,
    required this.sesion,
    required this.cuentaId,
    required this.alTerminar,
    this.desdeAjustes = false,
    this.inicial = const [],
    this.buscador = buscarArtistasCatalogo,
    this.sugeridos = artistasSugeridos,
    this.retraso = const Duration(milliseconds: 350),
  });

  final Sesion? sesion;
  final String cuentaId;
  final VoidCallback alTerminar;
  final bool desdeAjustes;
  final List<ArtistaGusto> inicial;
  final BuscadorArtistas buscador;
  final List<String> sugeridos;
  final Duration retraso;

  @override
  State<GustosPagina> createState() => _GustosPaginaState();
}

class _GustosPaginaState extends State<GustosPagina> {
  final _texto = TextEditingController();
  final _foco = FocusNode();
  final _scrollChips = ScrollController();
  Timer? _espera;
  int _vuelta = 0;

  late final List<ArtistaGusto> _elegidos = [...widget.inicial.take(Gustos.maximo)];
  late final List<ArtistaGusto?> _huecos = List.filled(widget.sugeridos.length, null);
  bool _cargandoSugeridos = true;
  bool _sugeridosFallaron = false;

  String _consulta = '';
  List<ArtistaGusto> _resultados = [];
  bool _buscando = false;
  bool _falloBusqueda = false;
  bool _guardando = false;

  @override
  void initState() {
    super.initState();
    _cargarSugeridos();
  }

  @override
  void dispose() {
    _espera?.cancel();
    _texto.dispose();
    _foco.dispose();
    _scrollChips.dispose();
    super.dispose();
  }

  Future<void> _cargarSugeridos() async {
    setState(() {
      _cargandoSugeridos = true;
      _sugeridosFallaron = false;
    });
    final nombres = widget.sugeridos;
    var siguiente = 0;
    var aciertos = 0;
    Future<void> obrero() async {
      while (mounted) {
        final i = siguiente++;
        if (i >= nombres.length) return;
        try {
          final r = await widget.buscador(nombres[i]).timeout(const Duration(seconds: 12));
          if (r.isNotEmpty && mounted) {
            aciertos++;
            // la primera coincidencia es el artista buscado
            setState(() => _huecos[i] = r.first);
          }
        } catch (_) {} // una búsqueda que falla se salta
      }
    }

    await Future.wait([for (var k = 0; k < 5; k++) obrero()]);
    if (!mounted) return;
    setState(() {
      _cargandoSugeridos = false;
      _sugeridosFallaron = aciertos == 0;
    });
  }

  List<ArtistaGusto> get _sugeridosListos {
    final vistos = <ArtistaGusto>{};
    return [
      for (final a in _huecos)
        if (a != null && vistos.add(a)) a
    ];
  }

  // ------------------------------------------------------------ búsqueda

  void _alEscribir(String t) {
    _espera?.cancel();
    final q = t.trim();
    if (q.isEmpty) {
      _vuelta++;
      setState(() {
        _consulta = '';
        _resultados = [];
        _buscando = false;
        _falloBusqueda = false;
      });
      return;
    }
    setState(() => _buscando = true);
    _espera = Timer(widget.retraso, () => _buscar(q));
  }

  Future<void> _buscar(String q) async {
    final mia = ++_vuelta;
    setState(() {
      _consulta = q;
      _buscando = true;
      _falloBusqueda = false;
    });
    try {
      final r = await widget.buscador(q).timeout(const Duration(seconds: 15));
      if (!mounted || mia != _vuelta) return;
      setState(() {
        _resultados = r;
        _buscando = false;
      });
    } catch (_) {
      if (!mounted || mia != _vuelta) return;
      setState(() {
        _resultados = [];
        _buscando = false;
        _falloBusqueda = true;
      });
    }
  }

  // ------------------------------------------------------------ elegir

  void _alternar(ArtistaGusto a) {
    final esta = _elegidos.contains(a);
    if (!esta && _elegidos.length >= Gustos.maximo) {
      HapticFeedback.mediumImpact();
      ScaffoldMessenger.maybeOf(context)
        ?..hideCurrentSnackBar()
        ..showSnackBar(const SnackBar(
            content: Text('Puedes elegir hasta 30 artistas. Quita alguno para añadir otro.'),
            behavior: SnackBarBehavior.floating,
            duration: Duration(seconds: 2)));
      return;
    }
    HapticFeedback.selectionClick();
    setState(() => esta ? _elegidos.remove(a) : _elegidos.add(a));
    if (!esta) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scrollChips.hasClients) {
          _scrollChips.animateTo(_scrollChips.position.maxScrollExtent,
              duration: const Duration(milliseconds: 260), curve: Curves.easeOutCubic);
        }
      });
    }
  }

  Future<void> _terminar({required bool omitir}) async {
    if (_guardando) return;
    if (widget.desdeAjustes && omitir) {
      widget.alTerminar(); // «Ahora no» desde Ajustes: no se cambia nada
      return;
    }
    setState(() => _guardando = true);
    final mensajero = ScaffoldMessenger.maybeOf(context);
    final lista = omitir ? <ArtistaGusto>[] : List.of(_elegidos);
    var subido = false;
    try {
      subido = await Gustos.guardar(widget.sesion, widget.cuentaId, lista).timeout(const Duration(seconds: 8));
    } catch (_) {} // la copia local ya quedó; se sube cuando haya red
    if (widget.desdeAjustes && !subido && widget.sesion != null) {
      mensajero?.showSnackBar(const SnackBar(
          content: Text('Guardado en este equipo. Se subirá a tu cuenta cuando vuelva la conexión.'),
          behavior: SnackBarBehavior.floating));
    }
    if (!mounted) return;
    widget.alTerminar();
  }

  // ------------------------------------------------------------ pantalla

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context);
    final ancho = mq.size.width;
    final lado = ancho < 360 ? 16.0 : 24.0;
    final teclado = mq.viewInsets.bottom > 0;
    final estrecha = mq.size.height < 620 || teclado; // barra de abajo en una sola fila
    final compacta = mq.size.height < 700;
    final mostrandoBusqueda = _consulta.isNotEmpty || _buscando;

    final cuerpo = Column(children: [
      // cabecera (se esconde con el teclado en pantallas bajas)
      AnimatedSize(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOutCubic,
        alignment: Alignment.topCenter,
        child: teclado && compacta
            ? const SizedBox(width: double.infinity)
            : _Aparece(
                child: Padding(
                  padding: EdgeInsets.fromLTRB(lado, compacta ? 14 : 28, lado, compacta ? 10 : 18),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('¿Qué artistas te gustan?',
                        style: TextStyle(
                            fontSize: compacta ? 24 : 30, height: 1.1, fontWeight: FontWeight.w800,
                            letterSpacing: -0.6, color: C.texto)),
                    SizedBox(height: compacta ? 6 : 10),
                    const Text('Elige los que más escuchas y afinamos tus recomendaciones.',
                        style: TextStyle(fontSize: 14, height: 1.35, color: C.texto2)),
                  ]),
                ),
              ),
      ),
      Padding(
        padding: EdgeInsets.fromLTRB(lado, 0, lado, 10),
        child: _Buscador(controlador: _texto, foco: _foco, alCambiar: _alEscribir,
            alEnviar: (t) {
              _espera?.cancel();
              if (t.trim().isNotEmpty) _buscar(t.trim());
            },
            alLimpiar: () {
              _texto.clear();
              _alEscribir('');
            }),
      ),
      _Contador(n: _elegidos.length, lado: lado),
      AnimatedSize(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOutCubic,
        alignment: Alignment.topCenter,
        child: _elegidos.isEmpty
            ? const SizedBox(width: double.infinity)
            : SizedBox(
                height: 48,
                child: ListView.separated(
                  controller: _scrollChips,
                  scrollDirection: Axis.horizontal,
                  padding: EdgeInsets.fromLTRB(lado, 4, lado, 8),
                  itemCount: _elegidos.length,
                  separatorBuilder: (_, _) => const SizedBox(width: 8),
                  itemBuilder: (_, i) => _FichaElegida(key: ValueKey(_elegidos[i].clave), artista: _elegidos[i],
                      alQuitar: () => _alternar(_elegidos[i])),
                ),
              ),
      ),
      Expanded(child: _zonaRejilla(lado, mostrandoBusqueda)),
      _barra(lado, estrecha),
    ]);

    return PopScope(
      canPop: widget.desdeAjustes,
      child: Scaffold(
        backgroundColor: C.fondoVivo,
        resizeToAvoidBottomInset: true,
        body: Stack(children: [
          // un resplandor suave del color de acento arriba: da profundidad sin ruido
          Positioned(
            top: -120, left: -60, right: -60, height: 380,
            child: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: Alignment.topCenter, radius: 0.9,
                    colors: [C.acento.withValues(alpha: 0.20), C.acento.withValues(alpha: 0.0)],
                  ),
                ),
              ),
            ),
          ),
          Positioned.fill(child: SafeArea(
            bottom: false,
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: Material(type: MaterialType.transparency, child: cuerpo),
              ),
            ),
          )),
        ]),
      ),
    );
  }

  Widget _zonaRejilla(double lado, bool mostrandoBusqueda) {
    final List<ArtistaGusto> lista;
    Widget? estado;
    if (mostrandoBusqueda) {
      lista = _resultados;
      if (_buscando && _resultados.isEmpty) {
        estado = const _Cargando(texto: 'Buscando…');
      } else if (_falloBusqueda) {
        estado = _Mensaje(
            icono: Icons.wifi_off_rounded, titulo: 'No pudimos buscar ahora',
            texto: 'Revisa tu conexión e inténtalo de nuevo.',
            accion: 'Reintentar', alAccion: () => _buscar(_consulta));
      } else if (!_buscando && _resultados.isEmpty) {
        estado = _Mensaje(
            icono: Icons.search_off_rounded, titulo: 'No encontramos a «$_consulta»',
            texto: 'Prueba con otro nombre o revisa cómo está escrito.');
      }
    } else {
      lista = _sugeridosListos;
      if (lista.isEmpty) {
        estado = _cargandoSugeridos
            ? const _Esqueleto()
            : _Mensaje(
                icono: Icons.travel_explore_rounded,
                titulo: _sugeridosFallaron ? 'No pudimos cargar las sugerencias' : 'Busca a tus artistas',
                texto: 'Escribe un nombre arriba y lo encuentras.',
                accion: _sugeridosFallaron ? 'Reintentar' : null,
                alAccion: _sugeridosFallaron ? _cargarSugeridos : null);
      }
    }
    if (estado != null) {
      return AnimatedSwitcher(duration: const Duration(milliseconds: 220), child: KeyedSubtree(
          key: ValueKey(estado.runtimeType.toString() + (mostrandoBusqueda ? 'b' : 's')), child: estado));
    }
    return _Rejilla(
      clave: mostrandoBusqueda ? 'b$_consulta' : 's',
      lado: lado,
      artistas: lista,
      titulo: mostrandoBusqueda ? 'Resultados' : 'Populares para empezar',
      elegidos: _elegidos,
      alTocar: _alternar,
      cargandoMas: !mostrandoBusqueda && _cargandoSugeridos,
    );
  }

  Widget _barra(double lado, bool estrecha) {
    final n = _elegidos.length;
    final puede = n > 0 && !_guardando;
    final omitir = TextButton(
      onPressed: _guardando ? null : () => _terminar(omitir: true),
      style: TextButton.styleFrom(foregroundColor: C.texto2, minimumSize: const Size(48, 48)),
      child: Text(widget.desdeAjustes ? 'Ahora no' : 'Omitir por ahora',
          maxLines: 1, softWrap: false, overflow: TextOverflow.ellipsis),
    );
    final continuar = FilledButton(
      onPressed: puede ? () => _terminar(omitir: false) : null,
      style: FilledButton.styleFrom(
          minimumSize: const Size(48, 52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
      child: _guardando
          ? SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: C.acentoTexto))
          : Text(estrecha && n > 0 ? 'Continuar · $n' : (widget.desdeAjustes ? 'Guardar' : 'Continuar'),
              maxLines: 1, overflow: TextOverflow.ellipsis),
    );
    return DecoratedBox(
      decoration: BoxDecoration(
        color: C.hayFondo ? C.fondo.withValues(alpha: 0.78) : C.fondo,
        border: Border(top: BorderSide(color: C.borde.withValues(alpha: 0.7))),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: EdgeInsets.fromLTRB(lado, 10, lado, estrecha ? 10 : 6),
          child: estrecha
              ? Row(children: [
                  Flexible(flex: 5, child: omitir),
                  const SizedBox(width: 8),
                  Expanded(flex: 4, child: continuar),
                ])
              : Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  continuar,
                  const SizedBox(height: 2),
                  omitir,
                ]),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- piezas

/// Entrada suave (aparece subiendo un poco); termina sola.
class _Aparece extends StatelessWidget {
  const _Aparece({required this.child, this.demora = 0});
  final Widget child;
  final int demora;

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: 1),
        duration: Duration(milliseconds: 420 + demora),
        curve: Curves.easeOutCubic,
        builder: (_, v, hijo) => Opacity(
          opacity: v.clamp(0.0, 1.0),
          child: Transform.translate(offset: Offset(0, (1 - v) * 14), child: hijo),
        ),
        child: child,
      );
}

class _Buscador extends StatelessWidget {
  const _Buscador({required this.controlador, required this.foco, required this.alCambiar,
      required this.alEnviar, required this.alLimpiar});
  final TextEditingController controlador;
  final FocusNode foco;
  final ValueChanged<String> alCambiar;
  final ValueChanged<String> alEnviar;
  final VoidCallback alLimpiar;

  @override
  Widget build(BuildContext context) {
    OutlineInputBorder borde(Color c, [double w = 1]) => OutlineInputBorder(
        borderRadius: BorderRadius.circular(28), borderSide: BorderSide(color: c, width: w));
    return ValueListenableBuilder<TextEditingValue>(
      valueListenable: controlador,
      builder: (_, v, _) => TextField(
        key: const ValueKey('buscador_artistas'),
        controller: controlador,
        focusNode: foco,
        onChanged: alCambiar,
        onSubmitted: alEnviar,
        textInputAction: TextInputAction.search,
        autocorrect: false,
        style: const TextStyle(fontSize: 15.5),
        cursorColor: C.acento,
        decoration: InputDecoration(
          isDense: true,
          hintText: 'Busca un artista',
          hintStyle: const TextStyle(color: C.texto3),
          filled: true,
          fillColor: C.superficie2,
          contentPadding: const EdgeInsets.symmetric(vertical: 14),
          prefixIcon: const Icon(Icons.search_rounded, color: C.texto3, size: 22),
          prefixIconConstraints: const BoxConstraints(minWidth: 46),
          suffixIcon: v.text.isEmpty
              ? null
              : IconButton(
                  tooltip: 'Borrar', onPressed: alLimpiar,
                  icon: const Icon(Icons.close_rounded, color: C.texto2, size: 20)),
          enabledBorder: borde(Colors.transparent),
          border: borde(Colors.transparent),
          focusedBorder: borde(C.acento.withValues(alpha: 0.8), 1.5),
        ),
      ),
    );
  }
}

/// «N elegidos» con tres puntitos que se llenan hasta el mínimo sugerido.
class _Contador extends StatelessWidget {
  const _Contador({required this.n, required this.lado});
  final int n;
  final double lado;

  @override
  Widget build(BuildContext context) {
    final texto = n == 0
        ? 'Elige al menos ${Gustos.sugeridos}'
        : '$n ${n == 1 ? 'elegido' : 'elegidos'}${n >= Gustos.maximo ? ' · el máximo' : ''}';
    return Padding(
      padding: EdgeInsets.fromLTRB(lado, 0, lado, 4),
      child: Row(children: [
        for (var i = 0; i < Gustos.sugeridos; i++)
          Padding(
            padding: const EdgeInsets.only(right: 4),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 260),
              curve: Curves.easeOutCubic,
              width: n > i ? 20 : 10, height: 5,
              decoration: BoxDecoration(
                color: n > i ? C.acento : C.superficie3,
                borderRadius: BorderRadius.circular(3),
              ),
            ),
          ),
        const SizedBox(width: 6),
        Expanded(
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 180),
            child: Text.rich(
              TextSpan(children: [
                TextSpan(text: texto),
                if (n > 0 && n < Gustos.sugeridos)
                  TextSpan(
                      text: '  ·  ${Gustos.sugeridos - n} más para afinar',
                      style: const TextStyle(fontWeight: FontWeight.w400, color: C.texto3)),
              ]),
              key: ValueKey('$texto|${n < Gustos.sugeridos}'),
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: n == 0 ? C.texto3 : C.texto2),
            ),
          ),
        ),
      ]),
    );
  }
}

class _FichaElegida extends StatelessWidget {
  const _FichaElegida({super.key, required this.artista, required this.alQuitar});
  final ArtistaGusto artista;
  final VoidCallback alQuitar;

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.6, end: 1),
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOutBack,
        builder: (_, v, hijo) => Transform.scale(scale: v, child: hijo),
        child: Semantics(
          button: true,
          label: 'Quitar a ${artista.nombre}',
          child: Material(
            color: C.acento.withValues(alpha: 0.14),
            shape: StadiumBorder(side: BorderSide(color: C.acento.withValues(alpha: 0.55))),
            child: InkWell(
              customBorder: const StadiumBorder(),
              onTap: alQuitar,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(4, 4, 10, 4),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Portada(url: artista.portada, lado: 28, circulo: true, icono: Icons.person_rounded),
                  const SizedBox(width: 8),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 120),
                    child: Text(artista.nombre, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                  ),
                  const SizedBox(width: 6),
                  const Icon(Icons.close_rounded, size: 16, color: C.texto2),
                ]),
              ),
            ),
          ),
        ),
      );
}

class _Rejilla extends StatelessWidget {
  const _Rejilla({required this.clave, required this.lado, required this.artistas, required this.titulo,
      required this.elegidos, required this.alTocar, this.cargandoMas = false});
  final String clave;
  final double lado;
  final List<ArtistaGusto> artistas;
  final String titulo;
  final List<ArtistaGusto> elegidos;
  final void Function(ArtistaGusto) alTocar;
  final bool cargandoMas;

  @override
  Widget build(BuildContext context) {
    final escala = MediaQuery.textScalerOf(context).scale(13);
    return LayoutBuilder(builder: (context, caja) {
      final util = caja.maxWidth - lado * 2;
      final columnas = max(3, (util / 112).floor());
      const sep = 8.0;
      final celda = (util - sep * (columnas - 1)) / columnas;
      final foto = (celda - 14).clamp(56.0, 96.0);
      // alto = foto + aire + dos líneas de nombre: sin desbordes con letra grande
      final alto = foto + 10 + escala * 1.25 * 2 + 4;
      return CustomScrollView(
        key: PageStorageKey('gustos_$clave'),
        slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.fromLTRB(lado, 6, lado, 10),
              child: Text(titulo, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: C.texto2,
                  letterSpacing: 0.2)),
            ),
          ),
          SliverPadding(
            padding: EdgeInsets.fromLTRB(lado, 0, lado, 24),
            sliver: SliverGrid(
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: columnas, mainAxisSpacing: 14, crossAxisSpacing: sep, mainAxisExtent: alto),
              delegate: SliverChildBuilderDelegate(
                childCount: artistas.length,
                (_, i) => _Aparece(
                  demora: min(i, 12) * 30,
                  child: _CeldaArtista(
                      key: ValueKey('${artistas[i].clave}|$clave'),
                      artista: artistas[i], foto: foto, elegido: elegidos.contains(artistas[i]),
                      alTocar: () => alTocar(artistas[i])),
                ),
              ),
            ),
          ),
          if (cargandoMas)
            const SliverToBoxAdapter(
                child: Padding(
                    padding: EdgeInsets.only(bottom: 24),
                    child: Center(child: SizedBox(width: 20, height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2))))),
        ],
      );
    });
  }
}

class _CeldaArtista extends StatelessWidget {
  const _CeldaArtista({super.key, required this.artista, required this.foto, required this.elegido,
      required this.alTocar});
  final ArtistaGusto artista;
  final double foto;
  final bool elegido;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) {
    const anillo = 3.0;
    const aire = 3.0;
    final interior = foto - (anillo + aire) * 2;
    return Semantics(
      button: true,
      selected: elegido,
      label: artista.nombre,
      child: InkWell(
        key: ValueKey('artista_${artista.clave}'),
        onTap: alTocar,
        borderRadius: BorderRadius.circular(16),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          SizedBox(
            width: foto, height: foto,
            child: Stack(clipBehavior: Clip.none, children: [
              // aro del color de acento que se enciende al elegir
              AnimatedContainer(
                duration: const Duration(milliseconds: 240),
                curve: Curves.easeOutCubic,
                width: foto, height: foto,
                padding: const EdgeInsets.all(aire),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: elegido ? C.acento : Colors.transparent, width: anillo),
                  boxShadow: [
                    if (elegido) BoxShadow(color: C.acento.withValues(alpha: 0.35), blurRadius: 14, spreadRadius: 0),
                  ],
                ),
                child: AnimatedScale(
                  scale: elegido ? 0.96 : 1,
                  duration: const Duration(milliseconds: 240),
                  curve: Curves.easeOutCubic,
                  child: ClipOval(
                    child: SizedBox(
                      width: interior, height: interior,
                      child: Stack(fit: StackFit.expand, children: [
                        Portada(url: artista.portada, lado: interior, circulo: true, icono: Icons.person_rounded),
                        AnimatedOpacity(
                          duration: const Duration(milliseconds: 240),
                          opacity: elegido ? 1 : 0,
                          child: ColoredBox(color: C.acento.withValues(alpha: 0.22)),
                        ),
                      ]),
                    ),
                  ),
                ),
              ),
              Positioned(
                right: -1, bottom: -1,
                child: AnimatedScale(
                  scale: elegido ? 1 : 0,
                  duration: const Duration(milliseconds: 260),
                  curve: Curves.easeOutBack,
                  child: Container(
                    width: 24, height: 24,
                    decoration: BoxDecoration(
                      color: C.acento, shape: BoxShape.circle,
                      border: Border.all(color: C.fondo, width: 2),
                    ),
                    child: Icon(Icons.check_rounded, size: 15, color: C.acentoTexto),
                  ),
                ),
              ),
            ]),
          ),
          const SizedBox(height: 8),
          Text(artista.nombre,
              maxLines: 2, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, height: 1.2, fontWeight: elegido ? FontWeight.w700 : FontWeight.w500,
                  color: elegido ? C.texto : C.texto2)),
        ]),
      ),
    );
  }
}

/// Círculos grises mientras llegan las sugerencias.
class _Esqueleto extends StatelessWidget {
  const _Esqueleto();

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, caja) {
        final columnas = max(3, ((caja.maxWidth - 32) / 112).floor());
        final foto = ((caja.maxWidth - 32 - 8 * (columnas - 1)) / columnas - 14).clamp(56.0, 96.0);
        return ClipRect(
          child: SingleChildScrollView(
            physics: const NeverScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: Wrap(
              alignment: WrapAlignment.center,
              spacing: 8, runSpacing: 22,
              children: [
                for (var i = 0; i < columnas * 3; i++)
                  SizedBox(
                    width: (caja.maxWidth - 32 - 8 * (columnas - 1)) / columnas,
                    child: Column(children: [
                      Container(width: foto, height: foto,
                          decoration: BoxDecoration(color: C.superficie2, shape: BoxShape.circle)),
                      const SizedBox(height: 10),
                      Container(width: foto * 0.7, height: 9,
                          decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(5))),
                    ]),
                  ),
              ],
            ),
          ),
        );
      });
}

class _Cargando extends StatelessWidget {
  const _Cargando({required this.texto});
  final String texto;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2.4)),
          const SizedBox(height: 12),
          Text(texto, style: const TextStyle(color: C.texto2)),
        ]),
      );
}

class _Mensaje extends StatelessWidget {
  const _Mensaje({required this.icono, required this.titulo, required this.texto, this.accion, this.alAccion});
  final IconData icono;
  final String titulo;
  final String texto;
  final String? accion;
  final VoidCallback? alAccion;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, caja) => SingleChildScrollView(
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: caja.maxHeight),
            child: Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  Container(
                    width: 64, height: 64,
                    decoration: BoxDecoration(color: C.superficie2, shape: BoxShape.circle),
                    child: Icon(icono, color: C.acento, size: 28),
                  ),
                  const SizedBox(height: 14),
                  Text(titulo, textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  Text(texto, textAlign: TextAlign.center,
                      style: const TextStyle(color: C.texto2, height: 1.35)),
                  if (accion != null) ...[
                    const SizedBox(height: 10),
                    TextButton(onPressed: alAccion, child: Text(accion!)),
                  ],
                ]),
              ),
            ),
          ),
        ),
      );
}
