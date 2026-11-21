// Modo karaoke (donadores): la letra a pantalla completa, muy grande, con la línea que suena
// llenándose al cantarse, el fondo animado de la carátula y la mascota «cantando».
//
// Reutiliza la letra del reproductor (su caché, el desfase de «Sincronía» y la línea de karaoke).
// «Bajar la voz» solo aparece si el motor puede (ver [Reproductor.puedeBajarVoz]).

import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/ritmo.dart';
import '../../nucleo/ritmo_fondo.dart';
import '../../reproduccion/frenos.dart';
import '../../reproduccion/reproductor.dart';
import '../reproductor/fondo_ambiente.dart';
import '../reproductor/letra_aspecto.dart';
import '../reproductor/linea_karaoke.dart';
import '../reproductor/mascota_vida.dart';
import '../reproductor/paleta_portada.dart';
import '../premium/letra_escena.dart';
import '../servicios.dart';
import '../tema.dart';
import 'reproductor_pagina.dart' show desfaseDeLetra, avisoDesfaseLetra, letraDeCancion, lineasDeLetra;

class KaraokePagina extends StatefulWidget {
  const KaraokePagina({super.key, required this.pista, this.letra});

  final Json pista;

  /// La letra ya cargada (si no, se busca).
  final Map<String, dynamic>? letra;

  /// Se abre con un fundido suave (sin él con «quitar animaciones»).
  static Future<void> abrir(BuildContext context, Json pista, {Map<String, dynamic>? letra}) {
    final quieto = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    return Navigator.of(context).push(PageRouteBuilder<void>(
      transitionDuration: quieto ? Duration.zero : const Duration(milliseconds: 320),
      reverseTransitionDuration: quieto ? Duration.zero : const Duration(milliseconds: 220),
      pageBuilder: (_, _, _) => KaraokePagina(pista: pista, letra: letra),
      transitionsBuilder: (_, a, _, hijo) => FadeTransition(opacity: a, child: hijo),
    ));
  }

  @override
  State<KaraokePagina> createState() => _KaraokePaginaState();
}

class _KaraokePaginaState extends State<KaraokePagina> {
  late Json _pista = widget.pista;
  Map<String, dynamic>? _letra;
  List<(int, String)> _ls = const [];
  List<GlobalKey> _llaves = const [];
  int _actual = -1;
  Reproductor? _r;
  Servicios? _s;
  final _scroll = ScrollController();
  DateTime _toque = DateTime(2000);
  PaletaPortada _paleta = PaletaPortada.neutra;
  String _urlPaleta = '';

  @override
  void initState() {
    super.initState();
    _poner(widget.letra);
    if (widget.letra == null) _cargarLetra(_pista);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_r == null) {
      _s = Caudal.leer(context);
      _r = _s!.reproductor
        ..addListener(_alCambiarCancion)
        ..posicion.addListener(_alAvanzar);
      avisoDesfaseLetra.addListener(_alAvanzar);
    }
  }

  @override
  void dispose() {
    final r = _r;
    r?.removeListener(_alCambiarCancion);
    r?.posicion.removeListener(_alAvanzar);
    avisoDesfaseLetra.removeListener(_alAvanzar);
    // la voz vuelve sola al salir: nadie quiere sorpresas en la siguiente canción
    if (r != null) {
      try {
        if (r.bajarVoz) unawaited(r.ponerBajarVoz(false).catchError((_) {}));
      } catch (_) {}
    }
    _scroll.dispose();
    super.dispose();
  }

  void _poner(Map<String, dynamic>? l) {
    _letra = l;
    _ls = l == null ? const [] : lineasDeLetra(l);
    _llaves = List.generate(_ls.length, (_) => GlobalKey());
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
      if (mounted) setState(() {}); // pausa o play: se repinta lo que depende del estado
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
    var i = -1;
    for (var k = 0; k < _ls.length; k++) {
      if (_ls[k].$1 <= ms) {
        i = k;
      } else {
        break;
      }
    }
    if (i == _actual) return;
    setState(() => _actual = i);
    if (i < 0 || !_scroll.hasClients || DateTime.now().difference(_toque) < const Duration(seconds: 4)) return;
    final dura = (MediaQuery.maybeDisableAnimationsOf(context) ?? false) ? Duration.zero : const Duration(milliseconds: 450);
    final objeto = _llaves[i].currentContext?.findRenderObject();
    final pos = _scroll.position;
    if (objeto != null && objeto.attached) {
      pos.ensureVisible(objeto, alignment: 0.5, duration: dura, curve: Curves.easeOutCubic);
    } else {
      final destino = (i * 84.0 - pos.viewportDimension * 0.4).clamp(pos.minScrollExtent, pos.maxScrollExtent);
      if (dura == Duration.zero) {
        pos.jumpTo(destino);
      } else {
        pos.animateTo(destino, duration: dura, curve: Curves.easeOutCubic);
      }
    }
  }

  AnalisisRitmo? _ritmo() {
    final s = _s;
    final clave = '${_pista['clave'] ?? ''}';
    if (s == null || clave.isEmpty) return null;
    try {
      return RitmoFondo.para(s.coleccion).de(clave);
    } catch (_) {
      return null;
    }
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
              _cabecera(context, r, pal),
              Expanded(child: _cuerpo(context, r, pal)),
              _pie(context, r, pal, sonando),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _cabecera(BuildContext context, Reproductor r, PaletaPortada pal) {
    return Padding(
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
        // la letra con efectos: el mismo verso, solo, enorme y con estilos para elegir
        IconButton(
          tooltip: 'Letra con efectos',
          icon: const Icon(Icons.auto_awesome_rounded),
          onPressed: () => LetraEscenaPagina.abrir(context, _pista, letra: _letra),
        ),
      ]),
    );
  }

  Widget _cuerpo(BuildContext context, Reproductor r, PaletaPortada pal) {
    final l = _letra;
    if (l == null) return const Center(child: CircularProgressIndicator(color: Colors.white));
    final texto = '${l['texto'] ?? ''}';
    if (_ls.isEmpty) {
      if (texto.isEmpty) {
        return const Center(
            child: Padding(
          padding: EdgeInsets.all(28),
          child: Text('No hay letra para esta canción.',
              textAlign: TextAlign.center, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 20)),
        ));
      }
      return SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
        child: Column(children: [
          const Text('Esta letra no trae tiempos, por eso no avanza sola.',
              textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: Color(0xCCFFFFFF))),
          const SizedBox(height: 14),
          Text(texto, textAlign: TextAlign.center, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, height: 1.4)),
        ]),
      );
    }
    final ancho = MediaQuery.sizeOf(context).width;
    final grande = (ancho * 0.085).clamp(24.0, 40.0);
    return NotificationListener<UserScrollNotification>(
      onNotification: (_) {
        _toque = DateTime.now();
        return false;
      },
      child: LayoutBuilder(
        builder: (context, c) => ListView.builder(
          controller: _scroll,
          padding: EdgeInsets.symmetric(vertical: c.maxHeight * 0.45, horizontal: 20),
          itemCount: _ls.length,
          itemBuilder: (_, i) {
            final d = _actual < 0 ? i + 1 : (i - _actual);
            final esta = d == 0;
            final texto = _ls[i].$2.trim().isEmpty ? '♪' : _ls[i].$2;
            final estilo = LetraAspecto.actual.value.conFuente(TextStyle(
              fontSize: esta ? grande : grande * 0.72,
              fontWeight: FontWeight.w900,
              height: 1.2,
              letterSpacing: -0.4,
              color: Colors.white,
            ));
            final opacidad = esta ? 1.0 : (d.abs() == 1 ? 0.55 : (d.abs() == 2 ? 0.34 : 0.2));
            Widget linea;
            if (esta && texto != '♪') {
              final inicio = _ls[i].$1;
              final siguiente = i + 1 < _ls.length ? _ls[i + 1].$1 : inicio + 5000;
              final fin = inicio + (siguiente - inicio).clamp(600, 1500 + texto.length * 85);
              linea = LineaKaraoke(
                  texto: texto, estilo: estilo, inicio: inicio, fin: fin, r: r,
                  hecho: Color.lerp(Colors.white, pal.acento, 0.55)!, falta: const Color(0x99FFFFFF),
                  alineacion: TextAlign.center);
            } else {
              linea = Text(texto, textAlign: TextAlign.center, style: estilo);
            }
            return GestureDetector(
              key: _llaves[i],
              behavior: HitTestBehavior.opaque,
              onTap: () {
                r.buscar(Duration(milliseconds: _ls[i].$1));
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 9),
                child: Center(
                  child: AnimatedOpacity(
                    opacity: opacidad,
                    duration: const Duration(milliseconds: 320),
                    child: linea,
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _pie(BuildContext context, Reproductor r, PaletaPortada pal, bool sonando) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        // el avance, finito: solo se repinta con la posición
        ValueListenableBuilder<Duration>(
          valueListenable: r.posicion,
          builder: (_, p, _) {
            final d = r.duracion.value.inMilliseconds;
            return ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: d <= 0 ? 0 : (p.inMilliseconds / d).clamp(0.0, 1.0),
                minHeight: 3,
                color: pal.acento,
                backgroundColor: Colors.white24,
              ),
            );
          },
        ),
        const SizedBox(height: 6),
        Row(children: [
          SizedBox(
            width: 66,
            height: 72,
            child: FittedBox(
              alignment: Alignment.bottomLeft,
              fit: BoxFit.scaleDown,
              child: MascotaSuelta(r: r, alto: 64, animo: AnimoMascota.cantar, colorNotas: pal.acento, ritmoDe: _ritmo),
            ),
          ),
          Expanded(
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
          ),
          SizedBox(width: 66, child: _bajarVoz(r, pal)),
        ]),
      ]),
    );
  }

  /// «Bajar la voz»: solo si el motor puede (no se inventa donde no se puede).
  Widget _bajarVoz(Reproductor r, PaletaPortada pal) {
    if (!r.puedeBajarVoz) return const SizedBox.shrink();
    final activa = r.bajarVoz;
    return Tooltip(
      message: 'Baja lo que suena al centro del estéreo, donde suele ir la voz',
      child: InkResponse(
        onTap: () async {
          await r.ponerBajarVoz(!activa);
          if (mounted) setState(() {});
        },
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(activa ? Icons.mic_off_rounded : Icons.mic_rounded, size: 28, color: activa ? pal.acento : Colors.white),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text('Bajar la voz',
                style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: activa ? pal.acento : Colors.white70)),
          ),
        ]),
      ),
    );
  }
}
