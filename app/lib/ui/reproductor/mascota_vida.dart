// La vida de las mascotas del reproductor: el reloj de pasos (más rápido en canciones rápidas),
// el sueño tras dos minutos en pausa, el gorrito de fiesta y la mascota suelta que usan el
// estilo «Flotante» y el modo karaoke.
//
// Todo es ligero: un solo temporizador de pasos mientras suena (y se ve), un temporizador de un
// solo disparo para dormirse y, durmiendo, un parpadeo lento de las «z». Sin el reproductor
// sonando no corre nada, y con «quitar animaciones» / modo ligero la mascota se queda quieta.

import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../nucleo/gamer_control.dart';
import '../../nucleo/mascota_app.dart';
import '../../nucleo/ritmo.dart';
import '../../nucleo/vida_mascota.dart';
import '../../reproduccion/reproductor.dart';

/// El «cerebro» de una mascota en pantalla: cuándo cambia de cuadro, cuándo duerme.
/// No es un widget: quien lo usa le pasa el reproductor y repinta cuando [aviso] cambia.
class VidaMascota {
  VidaMascota({
    required this.r,
    required this.cuadros,
    this.ritmoDe,
    DateTime Function()? reloj,
    this.dormirDespues = dormirTras,
  }) : _reloj = reloj ?? DateTime.now;

  final Reproductor r;
  final int cuadros;

  /// El ritmo de lo que suena, si ya se conoce (null = no se sabe).
  final AnalisisRitmo? Function()? ritmoDe;
  final DateTime Function() _reloj;
  final Duration dormirDespues;

  /// Sube con cada cambio que merece repintar.
  final ValueNotifier<int> aviso = ValueNotifier<int>(0);

  int cuadro = 0;

  /// Cuántos pasos lleva dados (para saltitos y notas).
  int pasos = 0;

  /// Sube 0.9 por paso (la fase de la estela y del arcoíris, igual que en el escritorio).
  double fase = 0;

  /// Durmiendo (más de [dormirDespues] en pausa).
  bool dormida = false;

  /// Fase lenta de las «z» (0, 1, 2).
  int fotoSueno = 0;

  bool _visible = true;
  bool _quieto = false;
  bool _vivo = true;
  Timer? _paso, _sueno, _zzz;
  Duration _periodo = Duration.zero;
  DateTime? _pausaDesde;

  bool get sonando => r.estado == EstadoRepro.sonando;

  /// Empieza a escuchar al reproductor.
  void iniciar() {
    r.addListener(revisar);
    revisar();
  }

  /// Avisa si la pantalla se ve ([visible], con TickerMode) y si hay que estar quieto
  /// ([quieto], con «quitar animaciones» o el modo ligero).
  void ajustar({required bool visible, required bool quieto}) {
    if (visible == _visible && quieto == _quieto) return;
    _visible = visible;
    _quieto = quieto;
    revisar();
  }

  void _avisar() {
    if (_vivo) aviso.value++;
  }

  /// Lo que hay que hacer según lo que suena. Se llama solo; público para las pruebas.
  @visibleForTesting
  void revisar() {
    if (!_vivo) return;
    final estado = r.estado;
    // ---- sueño: solo en pausa
    if (estado == EstadoRepro.pausa) {
      _pausaDesde ??= _reloj();
      if (!dormida && _sueno == null) {
        final falta = dormirDespues - _reloj().difference(_pausaDesde!);
        _sueno = Timer(falta.isNegative ? Duration.zero : falta, _dormirse);
      }
    } else {
      _pausaDesde = null;
      _sueno?.cancel();
      _sueno = null;
      _zzz?.cancel();
      _zzz = null;
      if (dormida) {
        dormida = false;
        _avisar();
      }
    }
    // ---- pasos: solo sonando y a la vista
    final camina = estado == EstadoRepro.sonando && _visible && !_quieto;
    if (camina) {
      final p = pasoDeMascota(_ritmo(), velocidad: r.velocidad);
      if (_paso == null || _periodo != p) {
        _paso?.cancel();
        _periodo = p;
        _paso = Timer.periodic(p, (_) => _dar());
      }
    } else if (_paso != null) {
      _paso!.cancel();
      _paso = null;
      _periodo = Duration.zero;
      if (estado != EstadoRepro.sonando && cuadro != 0) {
        cuadro = 0; // en pausa se queda quieta, en el primer cuadro
        _avisar();
      }
    }
    // las «z» se mueven solo si está dormida, se ve y no hay que estar quieto
    if (dormida && _visible && !_quieto) {
      _zzz ??= Timer.periodic(const Duration(milliseconds: 700), (_) {
        fotoSueno = (fotoSueno + 1) % 3;
        _avisar();
      });
    } else if (_zzz != null && (!dormida || !_visible || _quieto)) {
      _zzz!.cancel();
      _zzz = null;
    }
  }

  AnalisisRitmo? _ritmo() {
    try {
      return ritmoDe?.call();
    } catch (_) {
      return null;
    }
  }

  void _dormirse() {
    _sueno = null;
    if (!_vivo || r.estado != EstadoRepro.pausa) return;
    dormida = true;
    cuadro = 0;
    fotoSueno = 0;
    _avisar();
    revisar();
  }

  void _dar() {
    cuadro = (cuadro + 1) % math.max(1, cuadros);
    pasos++;
    fase += 0.9;
    // si ya se conoció el ritmo (o cambió la canción), el paso se acomoda
    final p = pasoDeMascota(_ritmo(), velocidad: r.velocidad);
    if (p != _periodo) {
      revisar();
    }
    _avisar();
  }

  void dispose() {
    _vivo = false;
    r.removeListener(revisar);
    _paso?.cancel();
    _sueno?.cancel();
    _zzz?.cancel();
    aviso.dispose();
  }
}

// ---------------------------------------------------------------- dibujo

final _textos = <String, TextPainter>{};

TextPainter _texto(String t, double tam, Color color) {
  final clave = '$t|${tam.round()}|${color.toARGB32()}';
  return _textos.putIfAbsent(clave, () {
    if (_textos.length > 40) _textos.clear();
    return TextPainter(
      text: TextSpan(text: t, style: TextStyle(fontSize: tam, fontWeight: FontWeight.w900, color: color, height: 1)),
      textDirection: TextDirection.ltr,
    )..layout();
  });
}

/// El gorrito de [fiesta] sobre una cabeza cuyo centro de arriba está en [cima] y mide [ancho] de ancho.
void pintarGorro(Canvas canvas, Fiesta fiesta, Offset cima, double ancho) {
  if (fiesta == Fiesta.ninguna) return;
  final w = ancho, h = ancho * 0.9;
  final p = Paint()..isAntiAlias = true;
  final base = cima.dx;
  // pequeño ladeo para que se vea puesto y no pegado
  canvas.save();
  canvas.translate(cima.dx, cima.dy);
  canvas.rotate(-0.12);
  canvas.translate(-cima.dx, -cima.dy);
  if (fiesta == Fiesta.navidad) {
    final cono = Path()
      ..moveTo(base - w / 2, cima.dy)
      ..quadraticBezierTo(base - w * 0.2, cima.dy - h * 0.9, base + w * 0.32, cima.dy - h * 0.78)
      ..quadraticBezierTo(base + w * 0.12, cima.dy - h * 0.35, base + w / 2, cima.dy)
      ..close();
    canvas.drawPath(cono, p..color = const Color(0xFFD62839));
    canvas.drawRRect(
        RRect.fromRectAndRadius(Rect.fromLTWH(base - w * 0.56, cima.dy - h * 0.12, w * 1.12, h * 0.22), Radius.circular(h * 0.11)),
        p..color = const Color(0xFFFFFFFF));
    canvas.drawCircle(Offset(base + w * 0.34, cima.dy - h * 0.78), h * 0.13, p..color = const Color(0xFFFFFFFF));
  } else {
    final cono = Path()
      ..moveTo(base - w * 0.45, cima.dy)
      ..lineTo(base + w * 0.05, cima.dy - h * 1.05)
      ..lineTo(base + w * 0.45, cima.dy)
      ..close();
    canvas.drawPath(cono, p..color = const Color(0xFF7C4DFF));
    canvas.save();
    canvas.clipPath(cono);
    p.color = const Color(0xFFFFD54F);
    for (var i = 1; i <= 2; i++) {
      canvas.drawRect(Rect.fromLTWH(base - w, cima.dy - h * 0.3 * i - h * 0.04, w * 2, h * 0.09), p);
    }
    canvas.restore();
    canvas.drawCircle(Offset(base + w * 0.05, cima.dy - h * 1.05), h * 0.11, p..color = const Color(0xFFFFD54F));
  }
  canvas.restore();
}

/// Las «z» de la mascota dormida, subiendo desde [origen]. [foto] (0 a 2) las mueve de a poco;
/// con [quieta] se ven las tres fijas.
void pintarZzz(Canvas canvas, Offset origen, double tam, int foto, {bool quieta = false}) {
  const letras = ['z', 'Z', 'Z'];
  for (var i = 0; i < 3; i++) {
    // cada letra sube un escalón por foto y vuelve a empezar abajo
    final escalon = quieta ? i : (i + foto) % 3;
    final t = tam * (0.55 + 0.25 * escalon);
    final alfa = quieta ? 0.9 : (escalon == 2 ? 0.55 : 0.95);
    final tp = _texto(letras[escalon], t, Colors.white.withValues(alpha: alfa));
    tp.paint(canvas, Offset(origen.dx + escalon * tam * 0.5, origen.dy - escalon * tam * 0.62));
  }
}

// ---------------------------------------------------------------- mascota suelta

enum AnimoMascota {
  /// Camina en el sitio (estilo «Flotante»).
  caminar,

  /// Salta al ritmo y suelta notas (karaoke).
  cantar,
}

/// La mascota elegida, suelta (no sobre la barra): para el estilo «Flotante» y el karaoke.
/// Sin mascota activa no ocupa nada.
class MascotaSuelta extends StatefulWidget {
  const MascotaSuelta({
    super.key,
    required this.r,
    required this.alto,
    this.animo = AnimoMascota.caminar,
    this.colorNotas = Colors.white,
    this.ritmoDe,
    this.hoy,
  });

  final Reproductor r;

  /// Alto en pantalla; el ancho sale de la proporción de la mascota.
  final double alto;
  final AnimoMascota animo;
  final Color colorNotas;
  final AnalisisRitmo? Function()? ritmoDe;

  /// Para las pruebas: el día que se usa para el gorrito (por defecto, hoy).
  final DateTime? hoy;

  @override
  State<MascotaSuelta> createState() => _MascotaSueltaState();
}

class _MascotaSueltaState extends State<MascotaSuelta> {
  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: Listenable.merge([MascotaApp.i, ModoGamerControl.mascotasOcultas]),
        builder: (_, _) {
          final m = MascotaApp.i.activa && !ModoGamerControl.mascotasOcultas.value ? MascotaApp.i.actual : null;
          if (m == null) return const SizedBox.shrink();
          return _Suelta(
              key: ValueKey(m.clave),
              r: widget.r,
              mascota: m,
              alto: widget.alto,
              animo: widget.animo,
              colorNotas: widget.colorNotas,
              ritmoDe: widget.ritmoDe,
              hoy: widget.hoy);
        },
      );
}

class _Suelta extends StatefulWidget {
  const _Suelta({
    super.key,
    required this.r,
    required this.mascota,
    required this.alto,
    required this.animo,
    required this.colorNotas,
    this.ritmoDe,
    this.hoy,
  });

  final Reproductor r;
  final Mascota mascota;
  final double alto;
  final AnimoMascota animo;
  final Color colorNotas;
  final AnalisisRitmo? Function()? ritmoDe;
  final DateTime? hoy;

  @override
  State<_Suelta> createState() => _SueltaState();
}

class _SueltaState extends State<_Suelta> {
  late final VidaMascota _vida =
      VidaMascota(r: widget.r, cuadros: widget.mascota.cuadros, ritmoDe: widget.ritmoDe)..iniciar();
  ui.Image? _hoja;
  ValueListenable<TickerModeData>? _tickers;

  @override
  void initState() {
    super.initState();
    MascotaApp.i.imagen(widget.mascota.clave).then((im) {
      if (mounted) setState(() => _hoja = im);
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final n = TickerMode.getValuesNotifier(context);
    if (!identical(n, _tickers)) {
      _tickers?.removeListener(_ajustar);
      _tickers = n..addListener(_ajustar);
    }
    _ajustar();
  }

  void _ajustar() {
    if (!mounted) return;
    _vida.ajustar(
        visible: _tickers?.value.enabled ?? true,
        quieto: MediaQuery.maybeDisableAnimationsOf(context) ?? false);
  }

  @override
  void dispose() {
    _tickers?.removeListener(_ajustar);
    _vida.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final m = widget.mascota;
    final alto = widget.alto;
    final ancho = alto * m.ancho / m.alto;
    final hoja = _hoja;
    if (hoja == null) return SizedBox(width: ancho, height: alto);
    final quieto = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final fiesta = fiestaDe(widget.hoy ?? DateTime.now());
    return Semantics(
      label: m.nombre,
      child: RepaintBoundary(
        child: CustomPaint(
          size: Size(ancho, alto),
          painter: _PintorSuelto(
              hoja: hoja,
              mascota: m,
              vida: _vida,
              animo: widget.animo,
              colorNotas: widget.colorNotas,
              fiesta: fiesta,
              quieto: quieto),
        ),
      ),
    );
  }
}

class _PintorSuelto extends CustomPainter {
  _PintorSuelto({
    required this.hoja,
    required this.mascota,
    required this.vida,
    required this.animo,
    required this.colorNotas,
    required this.fiesta,
    required this.quieto,
  }) : super(repaint: vida.aviso);

  final ui.Image hoja;
  final Mascota mascota;
  final VidaMascota vida;
  final AnimoMascota animo;
  final Color colorNotas;
  final Fiesta fiesta;
  final bool quieto;

  @override
  void paint(Canvas canvas, Size size) {
    final fw = (mascota.ancho * mascota.densidad).toDouble(), fh = (mascota.alto * mascota.densidad).toDouble();
    final dormida = vida.dormida;
    final cuadro = dormida ? 0 : math.min(mascota.cuadros - 1, math.max(0, vida.cuadro));
    // cantando: un saltito en cada paso; dormida: se hunde un poquito
    final cantando = animo == AnimoMascota.cantar && vida.sonando && !quieto;
    final salto = cantando ? (vida.pasos.isOdd ? -size.height * 0.07 : 0.0) : 0.0;
    final baja = dormida ? size.height * 0.03 : 0.0;
    final destino = Rect.fromLTWH(0, salto + baja, size.width, size.height);
    canvas.drawImageRect(hoja, Rect.fromLTWH(cuadro * fw, 0, fw, fh), destino,
        Paint()..filterQuality = filtroMascota(mascota.densidad));
    pintarGorro(canvas, fiesta, Offset(size.width * 0.55, destino.top + size.height * 0.1), size.width * 0.42);
    if (dormida) {
      pintarZzz(canvas, Offset(size.width * 0.72, destino.top + size.height * 0.18), size.height * 0.26,
          vida.fotoSueno, quieta: quieto);
    } else if (cantando) {
      // dos notas suben y se desvanecen, una por cada tres pasos
      for (var i = 0; i < 2; i++) {
        final t = ((vida.pasos + i * 3) % 6) / 6.0;
        final x = size.width * (0.75 + 0.25 * math.sin((vida.pasos + i * 3) * 0.9)) ;
        final y = size.height * (0.2 - 0.55 * t);
        final tp = _texto(i == 0 ? '♪' : '♫', size.height * 0.3, colorNotas.withValues(alpha: 1 - t));
        tp.paint(canvas, Offset(x, y));
      }
    }
  }

  @override
  bool shouldRepaint(covariant _PintorSuelto old) =>
      old.hoja != hoja || old.mascota != mascota || old.animo != animo || old.fiesta != fiesta ||
      old.quieto != quieto || old.colorNotas != colorNotas;
}
