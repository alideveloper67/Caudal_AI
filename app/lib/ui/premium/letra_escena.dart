// Letra con efectos (donadores): solo el verso que suena, enorme y en el centro, con una entrada
// animada por línea y un resplandor con los colores de la carátula. Cuatro estilos: Resplandor, Ola,
// Neón y Cine. El anterior se apaga arriba y el siguiente asoma pequeño abajo.
//
// Parte del modo karaoke: usa la misma letra (su caché, el desfase de «Sincronía»), el mismo fondo
// animado de la carátula y su paleta. La parte que se ve ([EscenaLetraVista]) no depende del
// reproductor, para poder probarla sola.

import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/cosmeticos.dart';
import '../../nucleo/donadores_extra.dart';
import '../../nucleo/premium.dart';
import '../../nucleo/premium_letras.dart';
import '../../reproduccion/frenos.dart';
import '../../reproduccion/reproductor.dart';
import '../paginas/reproductor_pagina.dart' show desfaseDeLetra, avisoDesfaseLetra, letraDeCancion, lineasDeLetra;
import '../reproductor/fondo_ambiente.dart';
import '../reproductor/paleta_portada.dart';
import '../servicios.dart';
import '../tema.dart';
import 'candado_donador.dart';

/// La pantalla completa. Sin beneficios no se abre: avisa qué es y cómo conseguirla.
class LetraEscenaPagina extends StatefulWidget {
  const LetraEscenaPagina({super.key, required this.pista, this.letra});

  final Json pista;
  final Map<String, dynamic>? letra;

  static const textoBloqueo =
      'La letra con efectos es para donadores: dona con Yape o canjea un código de prueba en Ajustes › Personalizar.';

  static Future<void> abrir(BuildContext context, Json pista, {Map<String, dynamic>? letra}) {
    if (!esPremiumLetras()) {
      Caudal.leer(context).avisar(textoBloqueo);
      return Future.value();
    }
    final quieto = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    return Navigator.of(context).push(PageRouteBuilder<void>(
      transitionDuration: quieto ? Duration.zero : const Duration(milliseconds: 320),
      reverseTransitionDuration: quieto ? Duration.zero : const Duration(milliseconds: 220),
      pageBuilder: (_, _, _) => LetraEscenaPagina(pista: pista, letra: letra),
      transitionsBuilder: (_, a, _, hijo) => FadeTransition(opacity: a, child: hijo),
    ));
  }

  /// Lo que suena ahora (o un aviso si no suena nada).
  static Future<void> abrirActual(BuildContext context) {
    final s = Caudal.leer(context);
    final p = s.reproductor.actual;
    if (!esPremiumLetras()) {
      s.avisar(textoBloqueo);
      return Future.value();
    }
    if (p == null) {
      s.avisar('Pon una canción a sonar para ver su letra con efectos.');
      return Future.value();
    }
    return abrir(context, p);
  }

  @override
  State<LetraEscenaPagina> createState() => _LetraEscenaPaginaState();
}

class _LetraEscenaPaginaState extends State<LetraEscenaPagina> {
  late Json _pista = widget.pista;
  Map<String, dynamic>? _letra;
  List<(int, String)> _ls = const [];
  int _actual = -1;
  Reproductor? _r;
  PaletaPortada _paleta = PaletaPortada.neutra;
  String _urlPaleta = '';
  String _estilo = Cosmeticos.estilosLetra.first;

  @override
  void initState() {
    super.initState();
    _poner(widget.letra);
    if (widget.letra == null) _cargarLetra(_pista);
    EscenaLetra.estiloGuardado().then((e) {
      if (mounted) setState(() => _estilo = e);
    });
    Premium.i.addListener(_vigilarPremium);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_r == null) {
      _r = Caudal.leer(context).reproductor
        ..addListener(_alCambiarCancion)
        ..posicion.addListener(_alAvanzar);
      avisoDesfaseLetra.addListener(_alAvanzar);
    }
  }

  @override
  void dispose() {
    Premium.i.removeListener(_vigilarPremium);
    _r?.removeListener(_alCambiarCancion);
    _r?.posicion.removeListener(_alAvanzar);
    avisoDesfaseLetra.removeListener(_alAvanzar);
    super.dispose();
  }

  /// Si se acaba la prueba con la pantalla abierta, se cierra sola.
  void _vigilarPremium() {
    if (!esPremiumLetras() && mounted && Navigator.of(context).canPop()) Navigator.of(context).maybePop();
  }

  void _poner(Map<String, dynamic>? l) {
    _letra = l;
    _ls = l == null ? const [] : lineasDeLetra(l);
    _actual = -1;
  }

  void _cargarLetra(Json p) {
    final clave = '${p['clave']}';
    letraDeCancion(p).then((l) {
      if (mounted && '${_pista['clave']}' == clave) setState(() => _poner(l));
    }).catchError((_) {
      if (mounted && '${_pista['clave']}' == clave) setState(() => _poner(const {'texto': '', 'lineas': []}));
    });
  }

  void _alCambiarCancion() {
    final nueva = _r?.actual;
    if (nueva == null) {
      if (mounted && Navigator.of(context).canPop()) Navigator.of(context).maybePop();
      return;
    }
    if ('${nueva['clave']}' == '${_pista['clave']}') {
      if (mounted) setState(() {});
      return;
    }
    setState(() {
      _pista = nueva;
      _poner(null);
    });
    _cargarLetra(nueva);
  }

  void _alAvanzar() {
    final r = _r;
    if (r == null || _ls.isEmpty || !mounted) return;
    final ms = r.posicion.value.inMilliseconds + 250 + pasoPosicion.inMilliseconds ~/ 2 + desfaseDeLetra('${_pista['clave']}');
    final i = EscenaLetra.indice(_ls, ms);
    if (i != _actual) setState(() => _actual = i);
  }

  void _paletaDe(String url) {
    if (url == _urlPaleta) return;
    _urlPaleta = url;
    final hecha = paletaEnCache(url);
    if (hecha != null) {
      _paleta = hecha;
      return;
    }
    paletaDe(url).then((p) {
      if (mounted && _urlPaleta == url) setState(() => _paleta = p);
    });
  }

  void _elegir(String e) {
    setState(() => _estilo = e);
    unawaited(EscenaLetra.guardarEstilo(e));
  }

  @override
  Widget build(BuildContext context) {
    final r = _r!;
    final url = '${_pista['miniatura'] ?? ''}';
    _paletaDe(url);
    final quieto = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final sonando = r.estado == EstadoRepro.sonando;
    return TweenAnimationBuilder<PaletaPortada>(
      tween: PaletaTween(end: _paleta),
      duration: quieto ? Duration.zero : const Duration(milliseconds: 700),
      builder: (context, pal, _) => Scaffold(
        backgroundColor: C.fondo,
        body: Stack(children: [
          Positioned.fill(child: FondoAmbiente(url: url, color: pal.fondo, enMovimiento: sonando)),
          SafeArea(
            child: Column(children: [
              _cabecera(context),
              SelectorEstiloLetra(estilo: _estilo, alElegir: _elegir, acento: pal.acento),
              Expanded(child: _cuerpo(pal)),
              _pie(r, pal, sonando),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _cabecera(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 4, 8, 0),
        child: Row(children: [
          IconButton(
            tooltip: 'Cerrar',
            icon: const Icon(Icons.keyboard_arrow_down_rounded, size: 32),
            onPressed: () => Navigator.of(context).maybePop(),
          ),
          Expanded(
            child: Column(children: [
              Text('${_pista['titulo'] ?? ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
              Text('${_pista['artista'] ?? ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, color: Color(0xCCFFFFFF))),
            ]),
          ),
          const SizedBox(width: 48),
        ]),
      );

  Widget _cuerpo(PaletaPortada pal) {
    final l = _letra;
    if (l == null) return const Center(child: CircularProgressIndicator(color: Colors.white));
    if (_ls.isEmpty) {
      final texto = '${l['texto'] ?? ''}'.trim();
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Text(
              texto.isEmpty
                  ? 'No hay letra para esta canción.'
                  : 'Esta letra no trae tiempos, así que no puede ir verso a verso. Ábrela en el modo karaoke.',
              textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 19)),
        ),
      );
    }
    return EscenaLetraVista(lineas: _ls, actual: _actual, estilo: _estilo, paleta: pal);
  }

  Widget _pie(Reproductor r, PaletaPortada pal, bool sonando) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          IconButton(iconSize: 34, tooltip: 'Anterior', icon: const Icon(Icons.skip_previous_rounded), onPressed: r.anterior),
          IconButton.filled(
            iconSize: 34,
            tooltip: sonando ? 'Pausa' : 'Reproducir',
            style: IconButton.styleFrom(backgroundColor: C.texto, foregroundColor: C.fondo),
            icon: Icon(sonando ? Icons.pause_rounded : Icons.play_arrow_rounded),
            onPressed: r.alternar,
          ),
          IconButton(iconSize: 34, tooltip: 'Siguiente', icon: const Icon(Icons.skip_next_rounded), onPressed: r.siguiente),
        ]),
      );
}

/// Los cuatro estilos, para elegir con un toque.
class SelectorEstiloLetra extends StatelessWidget {
  const SelectorEstiloLetra({super.key, required this.estilo, required this.alElegir, this.acento = oroDonador});

  final String estilo;
  final ValueChanged<String> alElegir;
  final Color acento;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        child: Row(children: [
          for (final e in Cosmeticos.estilosLetra)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(Cosmeticos.nombresEstiloLetra[e]!),
                selected: e == estilo,
                selectedColor: acento.withValues(alpha: 0.35),
                onSelected: (_) => alElegir(e),
              ),
            ),
        ]),
      );
}

/// Lo que se ve: el verso anterior apagándose arriba, el actual enorme con su entrada y su
/// resplandor, y el siguiente pequeño abajo. Un toque no hace nada aquí (es para mirar y cantar).
class EscenaLetraVista extends StatelessWidget {
  const EscenaLetraVista({super.key, required this.lineas, required this.actual, required this.estilo, required this.paleta});

  final List<(int, String)> lineas;
  final int actual;
  final String estilo;
  final PaletaPortada paleta;

  String _texto(int i) {
    if (i < 0 || i >= lineas.length) return '';
    final t = lineas[i].$2.trim();
    return t.isEmpty ? '♪' : t;
  }

  @override
  Widget build(BuildContext context) {
    final ancho = MediaQuery.sizeOf(context).width;
    final grande = (ancho * 0.105).clamp(28.0, 58.0);
    final anterior = _texto(actual - 1);
    final siguiente = _texto(actual < 0 ? 0 : actual + 1);
    final quieto = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final pequeno = TextStyle(fontSize: grande * 0.42, fontWeight: FontWeight.w800, color: Colors.white, height: 1.25);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 22),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        AnimatedSwitcher(
          duration: quieto ? Duration.zero : const Duration(milliseconds: 450),
          child: Opacity(
            key: ValueKey('a$actual'),
            opacity: 0.28,
            child: Text(anterior, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis, style: pequeno),
          ),
        ),
        const SizedBox(height: 18),
        Flexible(
          child: Center(
            child: actual < 0
                ? Text('♪', style: TextStyle(fontSize: grande, color: Colors.white70))
                : VersoEscena(
                    key: ValueKey('v$actual-$estilo'),
                    texto: _texto(actual),
                    estilo: estilo,
                    paleta: paleta,
                    tamano: grande,
                  ),
          ),
        ),
        const SizedBox(height: 18),
        AnimatedSwitcher(
          duration: quieto ? Duration.zero : const Duration(milliseconds: 450),
          child: Opacity(
            key: ValueKey('s$actual'),
            opacity: 0.5,
            child: Text(siguiente, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis, style: pequeno),
          ),
        ),
      ]),
    );
  }
}

/// Un verso que entra con el efecto de su estilo. Cada verso nuevo es un widget nuevo (con su propia
/// llave), así que la entrada vuelve a empezar en cada línea. Con «Quitar animaciones» sale ya puesto.
class VersoEscena extends StatefulWidget {
  const VersoEscena({super.key, required this.texto, required this.estilo, required this.paleta, required this.tamano});

  final String texto;
  final String estilo;
  final PaletaPortada paleta;
  final double tamano;

  @override
  State<VersoEscena> createState() => _VersoEscenaState();
}

class _VersoEscenaState extends State<VersoEscena> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: EscenaLetra.entrada(widget.estilo, widget.texto));
  bool _empezo = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_empezo) return;
    _empezo = true;
    if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) {
      _c.value = 1;
    } else {
      _c.forward();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  List<Shadow> _brillo(double f, {Color? color}) {
    final fuerza = f.clamp(0.0, 1.0);
    final p = widget.paleta;
    final a = color ?? p.acento;
    return [
      Shadow(color: a.withValues(alpha: 0.85 * fuerza), blurRadius: 14),
      Shadow(color: p.contraste.withValues(alpha: 0.6 * fuerza), blurRadius: 30),
      Shadow(color: a.withValues(alpha: 0.35 * fuerza), blurRadius: 52),
    ];
  }

  @override
  Widget build(BuildContext context) => Semantics(
        label: widget.texto,
        excludeSemantics: true,
        child: AnimatedBuilder(animation: _c, builder: (_, _) => _pintar(_c.value)),
      );

  Widget _pintar(double t) {
    final base = TextStyle(
      fontSize: widget.tamano,
      fontWeight: FontWeight.w900,
      height: 1.15,
      letterSpacing: -0.5,
      color: Colors.white,
    );
    switch (Cosmeticos.estiloLetra(widget.estilo)) {
      case 'ola':
        final palabras = EscenaLetra.palabras(widget.texto);
        return Wrap(
          alignment: WrapAlignment.center,
          spacing: widget.tamano * 0.28,
          children: [
            for (var k = 0; k < palabras.length; k++)
              Builder(builder: (_) {
                final p = EscenaLetra.pieza(t, k, palabras.length);
                final sube = Curves.easeOutBack.transform(p);
                return Opacity(
                  opacity: p,
                  child: Transform.translate(
                    offset: Offset(0, widget.tamano * 0.7 * (1 - sube)),
                    child: Text(palabras[k], style: base.copyWith(shadows: _brillo(0.35 + 0.65 * p))),
                  ),
                );
              }),
          ],
        );
      case 'neon':
        final luz = EscenaLetra.neon(t);
        final tubo = Color.lerp(Colors.white, widget.paleta.acento, 0.25)!;
        return Opacity(
          opacity: 0.25 + 0.75 * luz,
          child: Text(widget.texto,
              textAlign: TextAlign.center,
              style: base.copyWith(
                fontWeight: FontWeight.w700,
                letterSpacing: 1.2,
                color: tubo,
                shadows: [
                  Shadow(color: widget.paleta.acento.withValues(alpha: luz), blurRadius: 6),
                  Shadow(color: widget.paleta.acento.withValues(alpha: 0.8 * luz), blurRadius: 18),
                  Shadow(color: widget.paleta.contraste.withValues(alpha: 0.7 * luz), blurRadius: 40),
                ],
              )),
        );
      case 'cine':
        final letras = widget.texto.characters.toList();
        final sigma = 7.0 * (1 - Curves.easeOut.transform(t));
        final texto = Text.rich(
          TextSpan(children: [
            for (var k = 0; k < letras.length; k++)
              TextSpan(
                text: letras[k],
                style: TextStyle(color: Colors.white.withValues(alpha: EscenaLetra.pieza(t, k, letras.length, solape: 0.85))),
              ),
          ]),
          textAlign: TextAlign.center,
          style: base.copyWith(
            fontWeight: FontWeight.w600,
            letterSpacing: widget.tamano * 0.08,
            shadows: _brillo(0.6 * t),
          ),
        );
        return sigma < 0.05
            ? texto
            : ImageFiltered(imageFilter: ImageFilter.blur(sigmaX: sigma, sigmaY: sigma), child: texto);
      default: // resplandor
        final e = Curves.easeOutCubic.transform(t);
        final pulso = 1 + 0.35 * math.sin(math.pi * t);
        return Opacity(
          opacity: e,
          child: Transform.translate(
            offset: Offset(0, widget.tamano * 0.6 * (1 - e)),
            child: Transform.scale(
              scale: 0.94 + 0.06 * e,
              child: Text(widget.texto, textAlign: TextAlign.center, style: base.copyWith(shadows: _brillo(e * pulso))),
            ),
          ),
        );
    }
  }
}
