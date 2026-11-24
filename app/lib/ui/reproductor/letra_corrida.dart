import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart' show Json;
import '../../reproduccion/frenos.dart';
import '../../reproduccion/reproductor.dart';
import '../paginas/reproductor_pagina.dart' show avisoDesfaseLetra, desfaseDeLetra, letraCambiada, letraDeCancion, lineasDeLetra, momentoDeVerso;
import '../servicios.dart';
import '../tema.dart';
import 'letra_aspecto.dart';

/// La letra de lo que suena, avanzando sola: para el panel de la derecha y la
/// escena. Tocar un verso lleva la canción hasta ahí.
class LetraCorrida extends StatefulWidget {
  const LetraCorrida({super.key, this.tamano = 20, this.centrada = false});
  final double tamano;
  final bool centrada;

  @override
  State<LetraCorrida> createState() => _LetraCorridaState();
}

class _LetraCorridaState extends State<LetraCorrida> {
  Reproductor? _r;
  Json? _pista;
  Map<String, dynamic>? _letra;
  List<(int, String)> _ls = const [];
  List<GlobalKey> _llaves = const [];
  int _actual = -1;
  final _scroll = ScrollController();
  DateTime _toque = DateTime(2000);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_r != null) return;
    _r = Caudal.leer(context).reproductor
      ..addListener(_cancion)
      ..posicion.addListener(_avanzar);
    avisoDesfaseLetra.addListener(_corregir);
    _cancion();
  }

  @override
  void dispose() {
    _r?.removeListener(_cancion);
    _r?.posicion.removeListener(_avanzar);
    avisoDesfaseLetra.removeListener(_corregir);
    _scroll.dispose();
    super.dispose();
  }

  void _cancion() {
    final p = _r!.actual;
    if ('${p?['clave']}' == '${_pista?['clave']}' && (p == null) == (_pista == null)) return;
    _pista = p;
    _poner(null);
    if (mounted) setState(() {});
    if (p == null) return;
    final clave = '${p['clave']}';
    letraDeCancion(p).then((l) => l, onError: (_) => <String, dynamic>{}).then((l) {
      if (!mounted || '${_pista?['clave']}' != clave) return;
      setState(() => _poner(l));
      WidgetsBinding.instance.addPostFrameCallback((_) => _avanzar());
    });
  }

  void _poner(Map<String, dynamic>? l) {
    _letra = l;
    _ls = l == null ? const [] : lineasDeLetra(l);
    _llaves = List.generate(_ls.length, (_) => GlobalKey());
    _actual = -1;
    if (_scroll.hasClients) _scroll.jumpTo(0);
  }

  void _corregir() {
    final l = letraCambiada('${_pista?['clave']}', _letra);
    if (l != null && _letra != null && mounted) setState(() => _poner(l));
    _avanzar();
  }

  void _avanzar() {
    final r = _r;
    if (r == null || _ls.isEmpty || !mounted) return;
    final ms = r.posicion.value.inMilliseconds + 250 + pasoPosicion.inMilliseconds ~/ 2 + desfaseDeLetra('${_pista?['clave']}');
    var i = -1;
    while (i + 1 < _ls.length && _ls[i + 1].$1 <= ms) {
      i++;
    }
    if (i == _actual) return;
    setState(() => _actual = i);
    if (i < 0 || !_scroll.hasClients || DateTime.now().difference(_toque) < const Duration(seconds: 4)) return;
    final quieto = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final o = _llaves[i].currentContext?.findRenderObject();
    if (o == null || !o.attached) return;
    _scroll.position.ensureVisible(o, alignment: 0.4,
        duration: quieto ? Duration.zero : const Duration(milliseconds: 420), curve: Curves.easeOutCubic);
  }

  @override
  Widget build(BuildContext context) {
    const tenue = TextStyle(color: Color(0x99FFFFFF), fontSize: 14);
    if (_pista == null) return const Center(child: Text('Pon algo a sonar para ver su letra.', style: tenue));
    final l = _letra;
    if (l == null) return const Center(child: CircularProgressIndicator(strokeWidth: 3));
    return ValueListenableBuilder<LetraAspecto>(
        valueListenable: LetraAspecto.actual, builder: (context, aspecto, _) => _conAspecto(context, l, aspecto, tenue));
  }

  Widget _conAspecto(BuildContext context, Map<String, dynamic> l, LetraAspecto aspecto, TextStyle tenue) {
    final alineada = widget.centrada ? TextAlign.center : TextAlign.start;
    final crudo = TextStyle(fontSize: widget.tamano, fontWeight: FontWeight.w800, height: 1.25, color: Colors.white);
    final base = aspecto.conFuente(crudo);
    if (_ls.isEmpty) {
      final texto = '${l['texto'] ?? ''}';
      if (texto.isEmpty) return Center(child: Text('No hay letra para esta canción.', style: tenue));
      return SingleChildScrollView(
        padding: const EdgeInsets.all(18),
        child: Text(texto, textAlign: alineada, style: base.copyWith(fontSize: widget.tamano * 0.85)),
      );
    }
    return NotificationListener<UserScrollNotification>(
      onNotification: (_) {
        _toque = DateTime.now();
        return false;
      },
      child: LayoutBuilder(
        builder: (context, c) => SingleChildScrollView(
          controller: _scroll,
          padding: EdgeInsets.fromLTRB(18, c.maxHeight * (widget.centrada ? 0.36 : 0.06), 18, c.maxHeight * 0.5),
          child: Column(
            crossAxisAlignment: widget.centrada ? CrossAxisAlignment.center : CrossAxisAlignment.start,
            children: [
              for (var i = 0; i < _ls.length; i++)
                InkWell(
                  key: _llaves[i],
                  borderRadius: BorderRadius.circular(8),
                  onTap: () => _r!.buscar(momentoDeVerso(_ls[i].$1, '${_pista?['clave']}')),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: aspecto.estilo != 'clasica' ? _linea(i, aspecto, crudo, alineada) : AnimatedDefaultTextStyle(
                      duration: const Duration(milliseconds: 220),
                      textAlign: alineada,
                      style: base.copyWith(
                          color: i == _actual
                              ? Colors.white
                              : i < _actual
                                  ? const Color(0x73FFFFFF)
                                  : const Color(0x99FFFFFF)),
                      child: Text(_ls[i].$2.trim().isEmpty ? '♪' : _ls[i].$2),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  /// Un verso con el diseño elegido en «Aa».
  Widget _linea(int i, LetraAspecto aspecto, TextStyle crudo, TextAlign alineada) {
    final texto = _ls[i].$2.trim().isEmpty ? '♪' : _ls[i].$2;
    if (i == _actual && texto != '♪') {
      final inicio = _ls[i].$1;
      final siguiente = i + 1 < _ls.length ? _ls[i + 1].$1 : inicio + 5000;
      return LineaLetraActiva(
        aspecto: aspecto, texto: texto, estilo: crudo, inicio: inicio,
        fin: inicio + (siguiente - inicio).clamp(600, 1500 + texto.length * 85),
        r: _r!, porVenir: const Color(0x99FFFFFF), acento: C.acento, alinear: alineada,
        adelanto: 250 + desfaseDeLetra('${_pista?['clave']}'),
      );
    }
    return LineaLetra(
      aspecto: aspecto, texto: texto, alinear: alineada,
      estilo: crudo.copyWith(color: i < _actual ? const Color(0x73FFFFFF) : const Color(0x99FFFFFF)),
    );
  }
}
