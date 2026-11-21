// La presentación «Somos 100»: sale una sola vez por dispositivo, cuando el
// total de usuarios de Caudal llega a 100 o más. Es la misma en Windows y en
// Android. Si no hay red o el servidor falla, no hace nada.
//
// Se monta con [Presentacion100.revisar], que la lanza desde main.dart.

import 'dart:convert';
import 'dart:math';
import 'dart:ui' show PointerDeviceKind;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:share_plus/share_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../plataforma.dart';
import '../tema.dart';
import 'demos_presentacion.dart';

/// Donde se guarda que ya se enseñó (true: no volver a mostrarla).
const String clavePresentacion100Vista = 'presentacion_100_vista';

/// Cuántos usuarios hacen falta para enseñarla.
const int metaPresentacion100 = 100;

const String urlTotalUsuarios = 'https://nztirmwqykbxadidpzzt.supabase.co/rest/v1/rpc/total_usuarios';
const String clavePublicaSupabase = 'sb_publishable_ga4gKRk0czj044G-xPptSQ_BZ_sTZLl';
const String enlaceCaudal = 'https://caudal-musica.netlify.app';
const String textoCompartirCaudal = 'Escucho mi música con Caudal 🎵 Únete: $enlaceCaudal';

/// ¿Toca mostrarla? Solo si aún no se vio, hay un total conocido y llega a la meta.
bool debeMostrar(int? total, bool yaVista) => !yaVista && total != null && total >= metaPresentacion100;

class Presentacion100 extends StatefulWidget {
  const Presentacion100({super.key});

  static const int _paginas = 13;

  /// Lee el total y, si ya llegamos a 100 y no se vio antes, la abre a pantalla completa.
  /// Errores (sin red, respuesta rara) se ignoran en silencio.
  static Future<void> revisar(BuildContext context) async {
    bool yaVista;
    SharedPreferences prefs;
    try {
      prefs = await SharedPreferences.getInstance();
      yaVista = prefs.getBool(clavePresentacion100Vista) ?? false;
    } catch (_) {
      return;
    }
    if (yaVista) return;
    final total = await _leerTotal();
    if (!debeMostrar(total, yaVista)) return;
    try {
      await prefs.setBool(clavePresentacion100Vista, true);
    } catch (_) {
      return;
    }
    if (!context.mounted) return;
    await Navigator.of(context, rootNavigator: true).push(MaterialPageRoute<void>(
      fullscreenDialog: true,
      builder: (_) => const Presentacion100(),
    ));
  }

  /// El total de usuarios (número). Null si no hay red, si falla o si responde algo raro.
  static Future<int?> _leerTotal() async {
    try {
      final r = await http
          .post(
            Uri.parse(urlTotalUsuarios),
            headers: {
              'apikey': clavePublicaSupabase,
              'Authorization': 'Bearer $clavePublicaSupabase',
              'Content-Type': 'application/json',
            },
            body: '{}',
          )
          .timeout(const Duration(seconds: 8));
      if (r.statusCode != 200) return null;
      final v = jsonDecode(r.body);
      if (v is num) return v.toInt();
      if (v is String) return int.tryParse(v.trim());
      return null;
    } catch (_) {
      return null;
    }
  }

  @override
  State<Presentacion100> createState() => _Presentacion100State();
}

class _Presentacion100State extends State<Presentacion100> with TickerProviderStateMixin {
  final PageController _pc = PageController();

  /// Reloj del fondo (una vuelta de 12 s): luces que respiran y motas que suben.
  late final AnimationController _reloj = AnimationController(vsync: this, duration: const Duration(seconds: 12));

  /// El contador 0 → 100 de la primera diapositiva (2,2 s).
  late final AnimationController _contador = AnimationController(vsync: this, duration: const Duration(milliseconds: 2200));

  /// La explosión de luz al llegar a 100.
  late final AnimationController _estallido = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100));

  /// Entrada de la diapositiva que se ve (textos y tarjetas escalonadas).
  late final AnimationController _entrada = AnimationController(vsync: this, duration: const Duration(milliseconds: 1300));

  /// El latido del corazón.
  late final AnimationController _latido = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400));

  int _actual = 0;
  bool _reducir = false;
  bool _iniciado = false;

  @override
  void initState() {
    super.initState();
    _contador.addStatusListener((s) {
      if (s == AnimationStatus.completed && !_reducir) _estallido.forward(from: 0);
    });
    _contador.forward();
    _entrada.forward();
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
      _contador.value = 1;
      _entrada.value = 1;
      _estallido.value = 0;
    } else {
      if (!_reloj.isAnimating) _reloj.repeat();
      if (!_latido.isAnimating) _latido.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _pc.dispose();
    _reloj.dispose();
    _contador.dispose();
    _estallido.dispose();
    _entrada.dispose();
    _latido.dispose();
    super.dispose();
  }

  void _ir(int i) {
    final destino = i.clamp(0, Presentacion100._paginas - 1);
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
    if (!_reducir) _entrada.forward(from: 0);
  }

  Future<void> _copiar() async {
    Haptico.toque();
    await Clipboard.setData(const ClipboardData(text: enlaceCaudal));
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(const SnackBar(content: Text('Enlace copiado')));
  }

  Future<void> _compartir() async {
    Haptico.toque();
    try {
      await SharePlus.instance.share(ShareParams(text: textoCompartirCaudal));
    } catch (_) {}
  }

  void _cerrar() {
    Haptico.toque();
    Navigator.of(context).maybePop();
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

  @override
  Widget build(BuildContext context) {
    final ultima = _actual == Presentacion100._paginas - 1;
    return Semantics(
      scopesRoute: true,
      explicitChildNodes: true,
      label: 'Somos 100, presentación de Caudal',
      child: Scaffold(
        backgroundColor: C.fondo,
        body: Stack(children: [
          // ---- fondo: degradado del acento con luces que respiran
          Positioned.fill(
            child: IgnorePointer(
              child: RepaintBoundary(
                child: AnimatedBuilder(
                  animation: _reloj,
                  builder: (_, _) => CustomPaint(painter: _FondoPainter(_reloj.value * 12, C.acento)),
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
                    itemCount: Presentacion100._paginas,
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
      for (var i = 0; i < Presentacion100._paginas; i++)
        AnimatedContainer(
          duration: Duration(milliseconds: _reducir ? 0 : 260),
          curve: Curves.easeOutCubic,
          width: i == _actual ? 22 : 6,
          height: 6,
          margin: const EdgeInsets.symmetric(horizontal: 3),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(3),
            color: i == _actual ? Colors.white : Colors.white.withValues(alpha: 0.28),
          ),
        ),
    ]);
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.m, Esp.xs, Esp.m, Esp.m),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: Row(children: [
            SizedBox(
              width: 110,
              child: _actual > 0
                  ? TextButton(
                      onPressed: () => _ir(_actual - 1),
                      style: TextButton.styleFrom(foregroundColor: Colors.white.withValues(alpha: 0.85), minimumSize: const Size(48, 48)),
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
    if (i == 9) {
      // la lista de bloques tiene su propio desplazamiento dentro de la diapositiva
      return Padding(
        padding: const EdgeInsets.fromLTRB(Esp.xl, Esp.l, Esp.xl, Esp.s),
        child: Center(
          child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 460), child: _diapoTodo()),
        ),
      );
    }
    final hijo = switch (i) {
      0 => _diapo1(),
      1 => _diapo2(),
      2 => _demo(Icons.landscape_rounded, 'Escenarios vivos',
          'Ilustraciones que respiran con tu música: lluvia, pétalos, neón y golpes que tiemblan con los graves.',
          const DemoEscenarios()),
      3 => _demo(Icons.lyrics_rounded, 'Letras que se cantan contigo',
          'La letra sincronizada se ilumina palabra a palabra, justo cuando suena.', const DemoLetra()),
      4 => _demo(Icons.groups_rounded, 'Escuchen juntos',
          'La misma canción, al mismo tiempo, con chat y reacciones en vivo.', const DemoJuntos()),
      5 => _demo(Icons.auto_awesome_rounded, 'Música que te conoce',
          'Mezclas diarias, descubrimientos y radios que aprenden de lo que escuchas.', const DemoDescubre()),
      6 => _demo(Icons.pets_rounded, 'Tus mascotas',
          'Una mascotita que te acompaña en el reproductor y pasea mientras suena tu música.', const DemoMascotas()),
      7 => _demo(Icons.sports_esports_rounded, 'Modo gamer',
          'Misiones, experiencia y niveles hasta el 99 por escuchar lo que te gusta.', const DemoGamer()),
      8 => _demo(Icons.menu_book_rounded, 'Modo estudio',
          'Reloj de enfoque con música tranquila para concentrarte.', const DemoEstudio()),
      10 => _diapo3(),
      11 => _diapo4(),
      _ => _diapo5(),
    };
    // centrado en vertical cuando cabe; si no cabe, se desplaza
    return LayoutBuilder(
      builder: (_, k) => SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(Esp.xl, Esp.l, Esp.xl, Esp.m),
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: (k.maxHeight - (Esp.l + Esp.m)).clamp(0.0, double.infinity)),
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

  TextStyle get _titulo => const TextStyle(fontSize: 30, fontWeight: FontWeight.w800, letterSpacing: -0.6, height: 1.15, color: C.texto);

  Widget _cuerpo(String texto, {double tam = 16.5}) => Text(
        texto,
        textAlign: TextAlign.center,
        style: TextStyle(fontSize: tam, height: 1.5, color: C.texto2),
      );

  /// Diapositiva de demostración: icono, título, la demo viva y una línea que la explica.
  Widget _demo(IconData icono, String titulo, String texto, Widget demo) => Column(mainAxisSize: MainAxisSize.min, children: [
        _entra(
          0,
          0.35,
          FittedBox(
           fit: BoxFit.scaleDown,
           child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              color: C.acento.withValues(alpha: 0.16),
              border: Border.all(color: C.acento.withValues(alpha: 0.55)),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(icono, size: 15, color: Colors.white),
              const SizedBox(width: 6),
              const Text('Así se ve en Caudal',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Colors.white)),
            ]),
           ),
          ),
        ),
        const SizedBox(height: Esp.s),
        _entra(0.05, 0.4, Text(titulo, textAlign: TextAlign.center, style: _titulo.copyWith(fontSize: 26))),
        const SizedBox(height: Esp.m),
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
        const SizedBox(height: Esp.m),
        _entra(0.35, 0.8, _cuerpo(texto, tam: 15.5)),
      ]);

  // 1 — «Somos 100»: el contador y la explosión de luz
  Widget _diapo1() => Column(mainAxisSize: MainAxisSize.min, children: [
        AnimatedBuilder(
          animation: Listenable.merge([_contador, _estallido]),
          builder: (_, _) {
            final n = (metaPresentacion100 * Curves.easeOutCubic.transform(_contador.value)).round();
            return SizedBox(
              width: 280,
              height: 220,
              child: Stack(alignment: Alignment.center, children: [
                CustomPaint(size: const Size(280, 220), painter: _EstallidoPainter(_estallido.value)),
                Text(
                  '$n',
                  style: const TextStyle(fontSize: 96, fontWeight: FontWeight.w900, letterSpacing: -2, color: Colors.white),
                ),
              ]),
            );
          },
        ),
        const SizedBox(height: Esp.s),
        _entra(0.2, 0.7, Text('Somos 100', textAlign: TextAlign.center, style: _titulo)),
        const SizedBox(height: Esp.m),
        _entra(0.4, 1, _cuerpo('100 personas eligieron Caudal para acompañar su música. Gracias por estar aquí.')),
      ]);

  // 2 — «Gracias por confiar»: el corazón que late
  Widget _diapo2() => Column(mainAxisSize: MainAxisSize.min, children: [
        _entra(
          0,
          0.5,
          AnimatedBuilder(
            animation: _latido,
            builder: (_, _) => Transform.scale(
              scale: 1 + 0.12 * Curves.easeInOut.transform(_latido.value),
              child: const Icon(Icons.favorite_rounded, size: 84, color: Color(0xFFFF5C8A)),
            ),
          ),
        ),
        const SizedBox(height: Esp.l),
        _entra(0.2, 0.8, Text('Gracias por confiar en Caudal', textAlign: TextAlign.center, style: _titulo)),
        const SizedBox(height: Esp.m),
        _entra(
          0.4,
          1,
          _cuerpo(
            'Caudal empezó como un proyecto pequeño, hecho con cariño. Hoy suena en cien vidas. '
            'Cada canción que pusiste, cada lista que armaste y cada mensaje que nos mandaste lo hizo crecer.',
          ),
        ),
      ]);

  // 3 — «Todo lo que Caudal te ofrece»: seis bloques en lista desplazable, escalonados ~120 ms
  Widget _diapoTodo() {
    const bloques = <(IconData, String, List<String>)>[
      (Icons.headphones_rounded, 'Escucha', [
        'Música sin límites y videoclips',
        'Descargas en MP3, M4A o FLAC para oír sin internet',
        'Sube tu propia música',
        'Letras sincronizadas, traducidas y en modo karaoke',
        'Ecualizador, súper volumen, mezclador de DJ con transiciones y temporizador para dormir',
      ]),
      (Icons.explore_rounded, 'Descubre', [
        '«Descubre para ti» cada día',
        'Música que aprende de tus gustos',
        'Modos de escucha por momento',
        'Canciones similares y radios',
        '¿Qué suena? para reconocer canciones',
        'Máquina del tiempo',
        'Tu resumen semanal y anual',
      ]),
      (Icons.groups_rounded, 'Juntos', [
        'Escuchar juntos al mismo segundo, con chat y reacciones',
        'Fiestas por QR',
        'Mezcla de compatibilidad',
        'Listas colaborativas hasta 50 amigos',
        'Amigos, mensajes y dedicatorias',
        'Directorio de la comunidad',
        'Tu cumpleaños celebrado',
      ]),
      (Icons.palette_rounded, 'Hazlo tuyo', [
        'Mascotas que te acompañan',
        'Temas, colores, fondos y tu propia imagen',
        'Reproductor Vinilo, Casete o Neón',
        'Perfil con portada y foto en GIF',
        'Escenarios vivos y la escena de escritorio',
      ]),
      (Icons.graphic_eq_rounded, 'Vive tu música', [
        'Modo gamer con niveles, misiones y rachas',
        'Modo estudio con Pomodoro y sonidos de ambiente',
        'Logros',
        'Visualizador',
        'Despertador musical',
        'Modo coche',
        'Chromecast',
      ]),
      (Icons.playlist_add_rounded, 'Comparte y cuida lo tuyo', [
        'Tarjetas de letras y de tu perfil para tus estados',
        'Importa tus listas de Spotify, Apple Music y YouTube Music, o tu música del teléfono y la PC',
        'Copia de seguridad',
        'Todo sincronizado en Android, Windows y el navegador',
      ]),
    ];
    return Column(children: [
      _entra(0, 0.35, Text('Todo lo que Caudal te ofrece', textAlign: TextAlign.center, style: _titulo.copyWith(fontSize: 26))),
      const SizedBox(height: Esp.xs),
      _entra(
        0.08,
        0.45,
        Text('Gratis, para siempre, en Android, Windows y el navegador, con tu cuenta sincronizada.',
            textAlign: TextAlign.center, style: const TextStyle(fontSize: 13.5, height: 1.4, color: C.texto2)),
      ),
      const SizedBox(height: Esp.m),
      Expanded(
        child: SingleChildScrollView(
          child: Column(children: [
            for (var i = 0; i < bloques.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: Esp.s),
                child: _entra(
                  0.15 + i * 0.092,
                  0.5 + i * 0.092,
                  Container(
                    padding: const EdgeInsets.all(Esp.m),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.07),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
                    ),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(color: C.acento.withValues(alpha: 0.18), shape: BoxShape.circle),
                          child: Icon(bloques[i].$1, size: 20, color: C.acentoAlto),
                        ),
                        const SizedBox(width: Esp.s),
                        Expanded(
                          child: Text(bloques[i].$2,
                              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: C.texto)),
                        ),
                      ]),
                      const SizedBox(height: Esp.s),
                      Wrap(spacing: 6, runSpacing: 6, children: [
                        for (final punto in bloques[i].$3)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.08),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: C.acento.withValues(alpha: 0.25)),
                            ),
                            child: Text(punto, style: const TextStyle(fontSize: 12, height: 1.3, color: C.texto2)),
                          ),
                      ]),
                    ]),
                  ),
                ),
              ),
          ]),
        ),
      ),
    ]);
  }

  // 4 — «Lo nuevo que vas a disfrutar»: tarjetas que entran una a una
  Widget _diapo3() {
    const tarjetas = <(IconData, String, String)>[
      (Icons.landscape_rounded, 'Escenarios vivos', '11 ilustraciones animadas que reaccionan a la música: Cyberpunk, Japón antiguo, Goku, Hajime no Ippo, Kaneki, Kuromi, Cinnamoroll y más.'),
      (Icons.touch_app_rounded, 'Interactivos', 'Mueve el ratón o el dedo y suelta partículas; en Goku e Ippo, los graves sacuden la pantalla.'),
      (Icons.image_rounded, 'Tu imagen o tu GIF', 'Pon de fondo lo que quieras.'),
      (Icons.lyrics_rounded, 'Letra que resalta', 'Más legible sobre cualquier fondo, a tiempo con la música y con traducción.'),
      (Icons.tune_rounded, 'Escena a tu gusto', 'Mueve, agranda u oculta cada pieza; Restablecer lo devuelve todo.'),
      (Icons.share_rounded, 'Para tus estados', 'Comparte tu escenario con la canción que suena.'),
      (Icons.notifications_active_rounded, 'Avisos en Android', 'Mensajes, solicitudes de amistad y novedades aunque la app esté cerrada.'),
      (Icons.sports_esports_rounded, 'Progreso gamer en todos tus equipos', 'Tu nivel se suma entre el celular y la PC.'),
      (Icons.bolt_rounded, 'Más fluido', 'Caudal abre y responde más rápido.'),
    ];
    return Column(mainAxisSize: MainAxisSize.min, children: [
      _entra(0, 0.4, Text('Lo nuevo que vas a disfrutar', textAlign: TextAlign.center, style: _titulo.copyWith(fontSize: 26))),
      const SizedBox(height: Esp.l),
      for (var i = 0; i < tarjetas.length; i++)
        Padding(
          padding: const EdgeInsets.only(bottom: Esp.s),
          child: _entra(
            0.1 + i * 0.05,
            0.5 + i * 0.05,
            Container(
              padding: const EdgeInsets.all(Esp.m),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
              ),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(color: C.acento.withValues(alpha: 0.18), shape: BoxShape.circle),
                  child: Icon(tarjetas[i].$1, size: 22, color: C.acentoAlto),
                ),
                const SizedBox(width: Esp.m),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(tarjetas[i].$2, style: const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800, color: C.texto)),
                    const SizedBox(height: 2),
                    Text(tarjetas[i].$3, style: const TextStyle(fontSize: 13.5, height: 1.4, color: C.texto2)),
                  ]),
                ),
              ]),
            ),
          ),
        ),
    ]);
  }

  // 4 — «Lo que viene»
  Widget _diapo4() => Column(mainAxisSize: MainAxisSize.min, children: [
        _entra(
          0,
          0.5,
          AnimatedBuilder(
            animation: _reloj,
            builder: (_, _) {
              final q = 0.5 + 0.5 * sin(2 * pi * (_reloj.value * 12) / 6);
              return Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: C.acento.withValues(alpha: 0.12),
                  boxShadow: [BoxShadow(color: C.acento.withValues(alpha: 0.15 + 0.2 * q), blurRadius: 40 + 20 * q, spreadRadius: 4 * q)],
                ),
                child: Icon(Icons.diversity_3_rounded, size: 60, color: C.acentoAlto),
              );
            },
          ),
        ),
        const SizedBox(height: Esp.l),
        _entra(0.2, 0.8, Text('Lo que viene: la comunidad de Caudal', textAlign: TextAlign.center, style: _titulo)),
        const SizedBox(height: Esp.m),
        _entra(
          0.4,
          1,
          _cuerpo(
            'En la próxima actualización, Caudal se convierte en una comunidad para toda la gente que disfruta la música: '
            'un lugar para descubrir, compartir y conocer a quienes sienten las canciones como tú.',
          ),
        ),
        const SizedBox(height: Esp.m),
        _entra(
          0.6,
          1,
          Text('Seguiremos creciendo y mejorando. Esto recién empieza.',
              textAlign: TextAlign.center, style: TextStyle(fontSize: 13.5, fontStyle: FontStyle.italic, color: C.texto3)),
        ),
      ]);

  // 5 — «Invita a tu gente» y los botones
  Widget _diapo5() => Column(mainAxisSize: MainAxisSize.min, children: [
        _entra(0, 0.5, Text('Comparte Caudal con el mundo', textAlign: TextAlign.center, style: _titulo)),
        const SizedBox(height: Esp.m),
        _entra(
          0.15,
          0.6,
          _cuerpo('Si Caudal te acompaña, invita a tus amigos y a tu familia. Cada persona que llega hace la comunidad más grande.'),
        ),
        const SizedBox(height: Esp.l),
        _entra(
          0.3,
          0.8,
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: Esp.l, horizontal: Esp.m),
            decoration: BoxDecoration(
              color: C.acento.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: C.acento.withValues(alpha: 0.4)),
            ),
            child: Text(
              'caudal-musica.netlify.app',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 21, fontWeight: FontWeight.w900, color: C.acentoAlto),
            ),
          ),
        ),
        const SizedBox(height: Esp.l),
        _entra(
          0.45,
          1,
          Column(children: [
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _copiar,
                style: FilledButton.styleFrom(shape: const StadiumBorder(), padding: const EdgeInsets.symmetric(vertical: 15)),
                icon: const Icon(Icons.copy_rounded),
                label: const Text('Copiar enlace', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              ),
            ),
            const SizedBox(height: Esp.s),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: _compartir,
                style: OutlinedButton.styleFrom(
                  shape: const StadiumBorder(),
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  foregroundColor: Colors.white,
                  side: BorderSide(color: Colors.white.withValues(alpha: 0.35)),
                ),
                icon: const Icon(Icons.share_rounded),
                label: const Text('Compartir Caudal', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
              ),
            ),
            const SizedBox(height: Esp.xs),
            TextButton(
              onPressed: _cerrar,
              style: TextButton.styleFrom(foregroundColor: Colors.white.withValues(alpha: 0.85), minimumSize: const Size(0, 44)),
              child: const Text('Seguir escuchando', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
            ),
          ]),
        ),
        const SizedBox(height: Esp.m),
        _entra(
          0.6,
          1,
          Text('— Con cariño, el equipo de Caudal 💜', textAlign: TextAlign.center, style: TextStyle(fontSize: 13.5, color: C.texto3)),
        ),
      ]);
}

// ------------------------------------------------------------------ pintura

/// El fondo: degradado del acento con tres luces que respiran y motas que suben despacio.
class _FondoPainter extends CustomPainter {
  _FondoPainter(this.s, this.color);
  final double s;
  final Color color;

  double _onda(double periodo, [double fase = 0]) => 0.5 + 0.5 * sin(2 * pi * (s / periodo + fase));

  @override
  void paint(Canvas canvas, Size z) {
    final r = Offset.zero & z;
    canvas.drawRect(
      r,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color.lerp(color, C.fondo, 0.6)!, Color.lerp(color, C.fondo, 0.88)!, C.fondo],
          stops: const [0, 0.5, 0.95],
        ).createShader(r),
    );
    final grande = max(z.width, z.height);
    final luces = <(double, double, Color, double)>[
      (0.2 + 0.25 * _onda(12), 0.15 + 0.08 * _onda(6, 0.2), C.acentoAlto, 0.5),
      (0.85 - 0.3 * _onda(12, 0.3), 0.35 + 0.1 * _onda(4, 0.5), color, 0.45),
      (0.5 + 0.2 * _onda(9, 0.6), 0.8 - 0.08 * _onda(6, 0.1), const Color(0xFFFF5C8A), 0.42),
    ];
    for (final (x, y, col, rad) in luces) {
      final o = Offset(z.width * x, z.height * y);
      final rr = grande * rad;
      canvas.drawCircle(
        o,
        rr,
        Paint()
          ..shader = RadialGradient(colors: [col.withValues(alpha: 0.26), col.withValues(alpha: 0)])
              .createShader(Rect.fromCircle(center: o, radius: rr)),
      );
    }
    for (var i = 0; i < 22; i++) {
      final x = z.width * ((i * 0.618034) % 1);
      final p = ((s / 12) * (1 + i % 2) + (i * 0.29) % 1) % 1;
      final y = z.height * (1.05 - 1.1 * p);
      final a = pow(sin(pi * p), 1.2).toDouble() * 0.3;
      canvas.drawCircle(
        Offset(x + sin(2 * pi * (s / 6 + i * 0.1)) * 6, y),
        0.9 + (i % 3) * 0.6,
        Paint()..color = Colors.white.withValues(alpha: a),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _FondoPainter old) => old.s != s || old.color != color;
}

/// La explosión de partículas de luz que sale del número al llegar a 100.
/// [t] va de 0 (no empieza) a 1 (se apaga).
class _EstallidoPainter extends CustomPainter {
  _EstallidoPainter(this.t);
  final double t;

  @override
  void paint(Canvas canvas, Size z) {
    if (t <= 0) return;
    final c = z.center(Offset.zero);
    final e = Curves.easeOutCubic.transform(t);
    final fade = (1 - t).clamp(0.0, 1.0);
    for (var i = 0; i < 28; i++) {
      final ang = 2 * pi * i / 28 + (i % 3) * 0.12;
      final dist = z.shortestSide * (0.25 + 0.4 * ((i * 7) % 5) / 4) * e;
      final p = c + Offset(cos(ang), sin(ang)) * dist;
      final col = i.isEven ? C.acentoAlto : const Color(0xFFFFE08A);
      canvas.drawCircle(
        p,
        2.2 + (i % 3) * 1.1 * fade,
        Paint()
          ..color = col.withValues(alpha: 0.9 * fade)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _EstallidoPainter old) => old.t != t;
}
