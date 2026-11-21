// «Gracias, donador»: la presentación dorada que ve una sola vez quien es donador
// o fundador DE VERDAD (la prueba gratuita no cuenta), unos segundos después de
// abrir Caudal. Es la misma en Windows y en Android.
//
// Se lanza con [PresentacionDonadores.revisar] desde main.dart.

import 'dart:convert';
import 'dart:math';
import 'dart:ui' show PointerDeviceKind;

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../nucleo/premium.dart';
import '../plataforma.dart';
import '../premium/personalizar_pagina.dart';
import '../servicios.dart';
import '../../nucleo/social.dart';
import 'demos_presentacion.dart';

/// Donde se guarda que ya se enseñó (true: no volver a mostrarla).
const String claveDonadoresVista = 'presentacion_donadores_vista';

/// La misma clave que usa Cuentas (cuentas.dart) para recordar la cuenta de este dispositivo.
const String _claveSesionCuenta = 'cuenta.sesion';

const Color _dorado = Color(0xFFF5C04A);
const Color _ambar = Color(0xFFFF9F3A);
const Color _fondoOscuro = Color(0xFF0E0A06);
const Color _fondoClaro = Color(0xFF2A1C08);
const Color _crema = Color(0xFFFFF6E0);
const Color _crema2 = Color(0xFFE8D5A8);

/// ¿Toca mostrarla? Solo si aún no se vio y el tipo es de donador o fundador de verdad.
/// [tipo] es null (o 'prueba', u otro valor) cuando no lo es.
bool debeMostrarDonador({required bool vista, required String? tipo}) =>
    !vista && (tipo == 'donador' || tipo == 'fundador');

class PresentacionDonadores extends StatefulWidget {
  const PresentacionDonadores({
    super.key,
    this.nombre = '',
    this.fundador = false,
    this.alDescubrir,
    this.alSeguir,
    this.perfil,
  });

  /// Lo que se enseña en «Tu perfil de donador» (null: se arma con el nombre y [Premium.i]).
  final PerfilDonadorDemo? perfil;

  /// Nombre visible de la cuenta ('' → solo «Gracias»).
  final String nombre;

  /// true: la medalla dice «Fundador de Caudal» en vez de «Donador de Caudal».
  final bool fundador;

  /// Para las pruebas o para quien la monte sin ruta propia.
  final VoidCallback? alDescubrir;
  final VoidCallback? alSeguir;

  static const int paginas = 11;

  /// Lee si ya se vio y, si esta cuenta es donadora o fundadora de verdad, la abre a pantalla
  /// completa y la marca como vista. Si no lo es, no hace nada (y no marca nada).
  /// Errores (sin preferencias, navegación) se ignoran en silencio.
  static Future<void> revisar(BuildContext context) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final vista = prefs.getBool(claveDonadoresVista) ?? false;
      if (vista) return;
      final estado = Premium.i.estado;
      final tipo = estado.vigente() ? estado.tipo : null;
      if (!debeMostrarDonador(vista: false, tipo: tipo)) return;
      await prefs.setBool(claveDonadoresVista, true);
      if (!context.mounted) return;
      final nombre = _nombreDeLaCuenta(prefs);
      final foto = await _fotoDelPerfil(context);
      if (!context.mounted) return;
      final pr = Premium.i;
      final perfil = PerfilDonadorDemo(
        nombre: nombre,
        fotoUrl: foto,
        marco: pr.marco,
        efecto: pr.efectoNombre,
        colorNombre: pr.colorNombre,
        tema: pr.tema,
        enPared: pr.enPared,
        fundador: tipo == 'fundador',
      );
      await Navigator.of(context).push(MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => PresentacionDonadores(nombre: nombre, fundador: tipo == 'fundador', perfil: perfil),
      ));
    } catch (_) {}
  }

  /// La foto del perfil propio ('' si no hay sesión, red o foto). Como mucho 5 s.
  static Future<String> _fotoDelPerfil(BuildContext context) async {
    try {
      final sesion = Caudal.leer(context).cuenta.sesion;
      if (sesion == null || sesion.acceso.isEmpty) return '';
      final p = await Social(sesion).miPerfilEditable().timeout(const Duration(seconds: 5));
      return p.fotoUrl;
    } catch (_) {
      return '';
    }
  }

  /// El nombre de la cuenta recordada en este dispositivo ('' si no se sabe).
  static String _nombreDeLaCuenta(SharedPreferences prefs) {
    try {
      final texto = prefs.getString(_claveSesionCuenta);
      if (texto == null) return '';
      final g = jsonDecode(texto);
      if (g is! Map) return '';
      return '${g['nombre'] ?? ''}'.trim();
    } catch (_) {
      return '';
    }
  }

  @override
  State<PresentacionDonadores> createState() => _PresentacionDonadoresState();
}

class _PresentacionDonadoresState extends State<PresentacionDonadores> with TickerProviderStateMixin {
  final PageController _pc = PageController();

  /// Reloj del fondo (una vuelta de 12 s): motas doradas que suben y la medalla que gira.
  late final AnimationController _reloj = AnimationController(vsync: this, duration: const Duration(seconds: 12));

  /// Entrada de la diapositiva que se ve (textos y tarjetas escalonadas ~120 ms).
  late final AnimationController _entrada = AnimationController(vsync: this, duration: const Duration(milliseconds: 2000));

  /// El destello que hace aparecer la medalla.
  late final AnimationController _destello = AnimationController(vsync: this, duration: const Duration(milliseconds: 1000));

  /// El latido del corazón.
  late final AnimationController _latido = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400));

  int _actual = 0;
  bool _reducir = false;
  bool _iniciado = false;

  @override
  void initState() {
    super.initState();
    _entrada.forward();
    _destello.forward();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final reducir = MediaQuery.disableAnimationsOf(context);
    if (_iniciado && reducir == _reducir) return;
    _iniciado = true;
    _reducir = reducir;
    if (reducir) {
      // quien pide menos movimiento ve la imagen ya compuesta, sin animar
      _reloj.stop();
      _latido.stop();
      _entrada.value = 1;
      _destello.value = 1;
    } else {
      if (!_reloj.isAnimating) _reloj.repeat();
      if (!_latido.isAnimating) _latido.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _pc.dispose();
    _reloj.dispose();
    _entrada.dispose();
    _destello.dispose();
    _latido.dispose();
    super.dispose();
  }

  void _ir(int i) {
    final destino = i.clamp(0, PresentacionDonadores.paginas - 1);
    if (destino == _actual || !_pc.hasClients) return;
    Haptico.toque();
    if (_reducir) {
      _pc.jumpToPage(destino);
    } else {
      _pc.animateToPage(destino, duration: const Duration(milliseconds: 560), curve: Curves.easeOutCubic);
    }
  }

  void _alCambiar(int i) {
    setState(() => _actual = i);
    if (_reducir) return;
    _entrada.forward(from: 0);
    if (i == 0) _destello.forward(from: 0);
  }

  void _seguir() {
    Haptico.toque();
    final f = widget.alSeguir;
    if (f != null) {
      f();
    } else {
      Navigator.of(context).maybePop();
    }
  }

  /// Cierra la presentación y abre «Personalizar» (las exclusivas de donador).
  void _descubrir() {
    Haptico.toque();
    final f = widget.alDescubrir;
    if (f != null) {
      f();
      return;
    }
    final nav = Navigator.of(context);
    void Function(Widget)? enPestana;
    try {
      enPestana = Caudal.leer(context).abrirEnPestana;
    } catch (_) {}
    nav.maybePop();
    if (enPestana != null) {
      enPestana(const PersonalizarPagina());
    } else {
      nav.push(MaterialPageRoute(builder: (_) => const PersonalizarPagina()));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ultima = _actual == PresentacionDonadores.paginas - 1;
    return Semantics(
      scopesRoute: true,
      explicitChildNodes: true,
      label: 'Gracias, donador. Presentación de Caudal',
      child: Scaffold(
        backgroundColor: _fondoOscuro,
        body: Stack(children: [
          // ---- fondo: degradado dorado oscuro con motas que suben
          const Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [_fondoOscuro, _fondoClaro],
                ),
              ),
            ),
          ),
          Positioned.fill(
            child: IgnorePointer(
              child: RepaintBoundary(
                child: AnimatedBuilder(
                  animation: _reloj,
                  builder: (_, _) => CustomPaint(painter: _FondoDoradoPainter(_reloj.value * 12)),
                ),
              ),
            ),
          ),
          SafeArea(
            child: Column(children: [
              Expanded(
                child: ScrollConfiguration(
                  behavior: ScrollConfiguration.of(context).copyWith(dragDevices: {
                    PointerDeviceKind.touch,
                    PointerDeviceKind.mouse,
                    PointerDeviceKind.trackpad,
                    PointerDeviceKind.stylus,
                  }),
                  child: PageView.builder(
                    controller: _pc,
                    itemCount: PresentacionDonadores.paginas,
                    onPageChanged: _alCambiar,
                    itemBuilder: (_, i) => _pagina(i),
                  ),
                ),
              ),
              _controles(ultima),
            ]),
          ),
        ]),
      ),
    );
  }

  // ------------------------------------------------------------ controles

  Widget _controles(bool ultima) {
    final puntos = Row(mainAxisSize: MainAxisSize.min, children: [
      for (var i = 0; i < PresentacionDonadores.paginas; i++)
        AnimatedContainer(
          duration: Duration(milliseconds: _reducir ? 0 : 260),
          curve: Curves.easeOutCubic,
          width: i == _actual ? 22 : 6,
          height: 6,
          margin: const EdgeInsets.symmetric(horizontal: 3),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(3),
            color: i == _actual ? _dorado : _dorado.withValues(alpha: 0.28),
          ),
        ),
    ]);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: Row(children: [
            SizedBox(
              width: 110,
              child: _actual > 0
                  ? TextButton(
                      onPressed: () => _ir(_actual - 1),
                      style: TextButton.styleFrom(foregroundColor: _dorado, minimumSize: const Size(48, 48)),
                      child: const Text('Atrás', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
                    )
                  : null,
            ),
            Expanded(child: Center(child: FittedBox(fit: BoxFit.scaleDown, child: puntos))),
            SizedBox(
              width: 110,
              child: ultima
                  ? null
                  : Align(
                      alignment: Alignment.centerRight,
                      child: FilledButton(
                        onPressed: () => _ir(_actual + 1),
                        style: FilledButton.styleFrom(
                          backgroundColor: _dorado,
                          foregroundColor: _fondoOscuro,
                          shape: const StadiumBorder(),
                          minimumSize: const Size(0, 48),
                          padding: const EdgeInsets.symmetric(horizontal: 18),
                          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                        ),
                        child: const Text('Siguiente'),
                      ),
                    ),
            ),
          ]),
        ),
      ),
    );
  }

  // ------------------------------------------------------------ páginas

  Widget _pagina(int i) {
    final perfil = widget.perfil ??
        PerfilDonadorDemo(
          nombre: widget.nombre,
          marco: Premium.i.marco,
          efecto: Premium.i.efectoNombre,
          colorNombre: Premium.i.colorNombre,
          tema: Premium.i.tema,
          enPared: Premium.i.enPared,
          fundador: widget.fundador,
        );
    final hijo = switch (i) {
      0 => _diapo1(),
      1 => _diapo2(),
      2 => _demo('Tu perfil de donador', 'Así te ven los demás: tu marco, tu nombre que brilla y tus insignias.',
          DemoMiPerfil(perfil: perfil)),
      3 => _demo('Escenarios vivos, solo para ti',
          'Once ilustraciones que respiran con la música. Tócalas y reaccionan.', const DemoEscenarios(acento: _dorado)),
      4 => _demo('Marcos y nombres que brillan', 'Siete marcos animados y cuatro efectos para tu nombre, del color que quieras.',
          DemoMarcos(nombre: widget.nombre)),
      5 => _demo('Estéticas exclusivas', 'Caudal entero se viste con tu estilo: Kuromi, Cyberpunk, Japón, Lo-fi y más.',
          const DemoTemas()),
      6 => _demo('Sonido a tu medida', 'Ecualizador avanzado y uno que se adapta solo a cada canción.',
          const DemoEcualizador(acento: _dorado)),
      7 => _demo('Letras con estilo', 'La letra se canta contigo, palabra a palabra, sobre tu escenario favorito.',
          const DemoLetra(escenario: 'cyberpunk', acento: _dorado)),
      8 => _diapo3(),
      9 => _diapo4(),
      _ => _diapo5(),
    };
    // centrado en vertical cuando cabe; si no cabe, se desplaza
    return LayoutBuilder(
      builder: (_, k) => SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(28, 32, 28, 16),
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: (k.maxHeight - (48)).clamp(0.0, double.infinity)),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: hijo,
            ),
          ),
        ),
      ),
    );
  }

  /// Una parte que entra con fundido y se desliza hacia arriba, entre [inicio] y [fin] de la entrada.
  Widget _entra(double inicio, double fin, Widget hijo) => AnimatedBuilder(
        animation: _entrada,
        child: hijo,
        builder: (_, h) {
          final t = Interval(inicio, fin, curve: Curves.easeOutCubic).transform(_entrada.value);
          return Opacity(
            opacity: t,
            child: Transform.translate(offset: Offset(0, (1 - t) * 24), child: h),
          );
        },
      );

  /// Diapositiva de demostración: título, la demo viva y una línea que la explica.
  Widget _demo(String titulo, String texto, Widget demo) => Column(mainAxisSize: MainAxisSize.min, children: [
        _entra(0, 0.35, _pastilla('Exclusivo para ti')),
        const SizedBox(height: 12),
        _entra(0.05, 0.4, Text(titulo, textAlign: TextAlign.center, style: _titular.copyWith(fontSize: 26))),
        const SizedBox(height: 18),
        _entra(
          0.15,
          0.6,
          AnimatedBuilder(
            animation: _entrada,
            child: RepaintBoundary(child: demo),
            builder: (_, h) {
              final t = Curves.easeOutBack.transform(const Interval(0.15, 0.6).transform(_entrada.value));
              return Transform.scale(scale: 0.88 + 0.12 * t, child: h);
            },
          ),
        ),
        const SizedBox(height: 18),
        _entra(0.35, 0.8, _cuerpo(texto, tam: 15.5)),
      ]);

  TextStyle get _titular => const TextStyle(fontSize: 30, fontWeight: FontWeight.w800, letterSpacing: -0.6, height: 1.15, color: _crema);

  Widget _cuerpo(String texto, {double tam = 16.5, Color color = _crema2}) => Text(
        texto,
        textAlign: TextAlign.center,
        style: TextStyle(fontSize: tam, height: 1.5, color: color),
      );

  Widget _pastilla(String texto) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: _dorado.withValues(alpha: 0.6)),
          color: _dorado.withValues(alpha: 0.12),
        ),
        child: Text(texto, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, color: _dorado)),
      );

  // 1 — «Gracias»: la medalla con destello y giro suave
  Widget _diapo1() {
    final titulo = widget.nombre.isEmpty ? 'Gracias' : 'Gracias, ${widget.nombre}';
    return Column(mainAxisSize: MainAxisSize.min, children: [
      _entra(0, 0.5, _medalla()),
      const SizedBox(height: 20),
      _entra(0.2, 0.7, Text(titulo, textAlign: TextAlign.center, style: _titular)),
      const SizedBox(height: 14),
      _entra(0.4, 1, _cuerpo('Tú hiciste posible lo que Caudal es hoy.')),
      const SizedBox(height: 18),
      _entra(0.55, 1, _pastilla(widget.fundador ? 'Fundador de Caudal' : 'Donador de Caudal')),
    ]);
  }

  Widget _medalla() => SizedBox(
        width: 260,
        height: 240,
        child: Stack(alignment: Alignment.center, children: [
          // el destello que se expande y se apaga
          AnimatedBuilder(
            animation: _destello,
            builder: (_, _) {
              final t = Curves.easeOutCubic.transform(_destello.value);
              final lado = 120 + 150 * t;
              return Container(
                width: lado,
                height: lado,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(colors: [
                    _dorado.withValues(alpha: 0.75 * (1 - t)),
                    _dorado.withValues(alpha: 0),
                  ]),
                ),
              );
            },
          ),
          // la medalla: aparece con el destello y gira leve de lado a lado
          AnimatedBuilder(
            animation: _destello,
            child: AnimatedBuilder(
              animation: _reloj,
              builder: (_, hijo) => Transform(
                alignment: Alignment.center,
                transform: Matrix4.rotationY(0.45 * sin(2 * pi * (_reloj.value * 12) / 6)),
                child: hijo,
              ),
              child: _discoMedalla(),
            ),
            builder: (_, hijo) {
              final t = Curves.easeOutBack.transform(_destello.value);
              return Opacity(
                opacity: t.clamp(0.0, 1.0),
                child: Transform.scale(scale: 0.5 + 0.5 * t, child: hijo),
              );
            },
          ),
        ]),
      );

  Widget _discoMedalla() => Container(
        width: 150,
        height: 150,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFFFE08A), _dorado, _ambar],
          ),
          border: Border.all(color: const Color(0xFFFFF3C4), width: 3),
          boxShadow: [BoxShadow(color: _dorado.withValues(alpha: 0.45), blurRadius: 40, spreadRadius: 2)],
        ),
        child: Center(
          child: Container(
            width: 118,
            height: 118,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: _fondoClaro.withValues(alpha: 0.35), width: 2),
            ),
            child: const Icon(Icons.workspace_premium_rounded, size: 64, color: _fondoClaro),
          ),
        ),
      );

  // 2 — «Ayudaste a que Caudal crezca»
  Widget _diapo2() => Column(mainAxisSize: MainAxisSize.min, children: [
        _entra(0, 0.4, const Icon(Icons.volunteer_activism_rounded, size: 64, color: _dorado)),
        const SizedBox(height: 22),
        _entra(0.15, 0.6, Text('Ayudaste a que Caudal crezca', textAlign: TextAlign.center, style: _titular)),
        const SizedBox(height: 16),
        _entra(
          0.3,
          0.9,
          _cuerpo(
            'Caudal es gratis para todos gracias a personas como tú. Tu apoyo pagó servidores, horas de trabajo y '
            'cada mejora que hoy disfrutan cien personas. No fue solo una donación: fue confiar en algo que estaba empezando.',
          ),
        ),
        const SizedBox(height: 22),
        _entra(
          0.6,
          1,
          const Text(
            'Este proyecto también es tuyo.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, height: 1.3, color: _dorado),
          ),
        ),
      ]);

  // 3 — «Tus exclusivas»: diez tarjetas que entran escalonadas (~120 ms)
  Widget _diapo3() {
    const tarjetas = <(IconData, String, String)>[
      (Icons.landscape_rounded, 'Escenarios vivos',
          '11 ilustraciones animadas (Cyberpunk, Japón antiguo, Goku, Hajime no Ippo, Kaneki, Kuromi, Cinnamoroll, '
              'Pompompurin, My Melody, Hello Kitty, Lo-fi) que reaccionan a la música, más Retro y Synthwave.'),
      (Icons.image_rounded, 'Tu imagen o tu GIF', 'De fondo en la escena y en el reproductor.'),
      (Icons.filter_frames_rounded, 'Marcos animados',
          'Aurora, Fuego, Oro, Neón, Hielo, Arcoíris y Galaxia alrededor de tu foto.'),
      (Icons.text_fields_rounded, 'Nombre con efecto', 'Brillo, Degradado, Arcoíris o Neón, y el color que quieras.'),
      (Icons.palette_rounded, 'Estéticas y temas',
          'Retro, Cyberpunk, Japón samurái, Gótico, Lo-fi, Kuromi, Cinnamoroll, Pompompurin, Hello Kitty, My Melody y más.'),
      (Icons.equalizer_rounded, 'Sonido a tu medida',
          'ecualizador avanzado y ecualizador que se adapta a cada canción.'),
      (Icons.lyrics_rounded, 'Letras con estilo',
          'estilos de letra animada y tarjetas exclusivas para compartir en tus estados.'),
      (Icons.account_circle_rounded, 'Tu perfil, único',
          'portada animada, foto en GIF, cápsula del tiempo y dedicatorias.'),
      (Icons.graphic_eq_rounded, 'Visualizador y escena',
          'el visualizador a pantalla completa y la escena de escritorio con todos sus fondos.'),
      (Icons.groups_rounded, 'Tu lugar en el muro',
          'el muro de agradecimiento de Caudal y la etiqueta de Donador en tu perfil.'),
    ];
    return Column(mainAxisSize: MainAxisSize.min, children: [
      _entra(0, 0.3, Text('Tus exclusivas', textAlign: TextAlign.center, style: _titular.copyWith(fontSize: 26))),
      const SizedBox(height: 18),
      for (var i = 0; i < tarjetas.length; i++)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: _entra(
            0.1 + i * 0.06,
            0.4 + i * 0.06,
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: _dorado.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: _dorado.withValues(alpha: 0.3)),
              ),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(color: _dorado.withValues(alpha: 0.18), shape: BoxShape.circle),
                  child: Icon(tarjetas[i].$1, size: 22, color: _dorado),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(tarjetas[i].$2,
                        style: const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800, color: _crema)),
                    const SizedBox(height: 2),
                    Text(tarjetas[i].$3, style: const TextStyle(fontSize: 13.5, height: 1.4, color: _crema2)),
                  ]),
                ),
              ]),
            ),
          ),
        ),
    ]);
  }

  // 4 — «Y esto sigue»
  Widget _diapo4() => Column(mainAxisSize: MainAxisSize.min, children: [
        _entra(
          0,
          0.5,
          AnimatedBuilder(
            animation: _reloj,
            builder: (_, _) {
              final q = 0.5 + 0.5 * sin(2 * pi * (_reloj.value * 12) / 4);
              return Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _dorado.withValues(alpha: 0.12),
                  boxShadow: [
                    BoxShadow(color: _dorado.withValues(alpha: 0.15 + 0.25 * q), blurRadius: 40 + 20 * q, spreadRadius: 4 * q),
                  ],
                ),
                child: const Icon(Icons.auto_awesome_rounded, size: 60, color: _dorado),
              );
            },
          ),
        ),
        const SizedBox(height: 26),
        _entra(0.2, 0.8, Text('Y esto sigue', textAlign: TextAlign.center, style: _titular)),
        const SizedBox(height: 16),
        _entra(
          0.4,
          1,
          _cuerpo(
            'Lo próximo es convertir Caudal en una comunidad para toda la gente que ama la música. Tú vas a estar en '
            'primera fila: cada nueva exclusiva llegará primero a quienes nos ayudan.',
          ),
        ),
        const SizedBox(height: 18),
        _entra(
          0.6,
          1,
          const Text(
            'Si quieres, invita a tu gente: caudal-musica.netlify.app',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13.5, fontStyle: FontStyle.italic, color: _dorado),
          ),
        ),
      ]);

  // 5 — «De corazón»: el corazón que late y los dos botones
  Widget _diapo5() => Column(mainAxisSize: MainAxisSize.min, children: [
        _entra(
          0,
          0.4,
          AnimatedBuilder(
            animation: _latido,
            builder: (_, _) => Transform.scale(
              scale: 1 + 0.12 * Curves.easeInOut.transform(_latido.value),
              child: const Icon(Icons.favorite_rounded, size: 84, color: _dorado),
            ),
          ),
        ),
        const SizedBox(height: 22),
        _entra(
          0.2,
          0.7,
          Text('Gracias por creer en Caudal.', textAlign: TextAlign.center, style: _titular),
        ),
        const SizedBox(height: 18),
        _entra(
          0.4,
          0.9,
          _cuerpo('— Con todo el cariño, el equipo de Caudal 💛', tam: 14.5, color: _crema2),
        ),
        const SizedBox(height: 26),
        _entra(
          0.55,
          1,
          Column(children: [
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _descubrir,
                style: FilledButton.styleFrom(
                  backgroundColor: _dorado,
                  foregroundColor: _fondoOscuro,
                  shape: const StadiumBorder(),
                  padding: const EdgeInsets.symmetric(vertical: 15),
                ),
                icon: const Icon(Icons.auto_awesome_rounded),
                label: const Text('Descubrir mis exclusivas', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              ),
            ),
            const SizedBox(height: 10),
            TextButton(
              onPressed: _seguir,
              style: TextButton.styleFrom(foregroundColor: _crema, minimumSize: const Size(0, 44)),
              child: const Text('Seguir escuchando', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
            ),
          ]),
        ),
      ]);
}

/// Las motas doradas que suben despacio por el fondo. [s] son segundos del reloj de 12 s;
/// todos los periodos dividen 12 para que la vuelta del reloj no dé un salto.
class _FondoDoradoPainter extends CustomPainter {
  _FondoDoradoPainter(this.s);
  final double s;

  @override
  void paint(Canvas canvas, Size z) {
    for (var i = 0; i < 40; i++) {
      final x = z.width * ((i * 0.618034) % 1);
      final p = ((s / 12) * (1 + i % 3) + (i * 0.37) % 1) % 1;
      final y = z.height * (1.05 - 1.1 * p);
      final brillo = 0.5 + 0.5 * sin(2 * pi * (s / 3 + i * 0.13));
      final a = (pow(sin(pi * p), 1.4).toDouble() * (0.3 + 0.4 * brillo)).clamp(0.0, 1.0);
      final r = 0.8 + (i % 4) * 0.7;
      final color = i.isEven ? _dorado : _ambar;
      canvas.drawCircle(
        Offset(x + sin(2 * pi * (s / 6 + i * 0.1)) * 8, y),
        r,
        Paint()
          ..color = color.withValues(alpha: a)
          ..maskFilter = r > 1.8 ? const MaskFilter.blur(BlurStyle.normal, 2) : null,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _FondoDoradoPainter old) => old.s != s;
}
