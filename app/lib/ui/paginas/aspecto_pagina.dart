import 'package:flutter/material.dart';

import '../../nucleo/cosmeticos.dart';
import '../../nucleo/mascota_app.dart';
import '../../nucleo/premium.dart';
import 'perfil_comun.dart' show socialDe;
import '../servicios.dart';
import '../escenarios/catalogo.dart';
import '../tema.dart';

/// Ajustes → Aspecto: el color de la app y su fondo (se ven al momento).
/// Además de los de la lista, se puede elegir un color y un fondo propios
/// (igual que en el escritorio).
class AspectoPagina extends StatefulWidget {
  const AspectoPagina({super.key});

  @override
  State<AspectoPagina> createState() => _AspectoPaginaState();
}

class _AspectoPaginaState extends State<AspectoPagina> {
  Future<void> _poner(String clave, Object valor) async {
    // elegir un fondo es cambiar de aspecto: si había un tema exclusivo puesto, se quita para que el fondo
    // elegido (con su personaje y sus colores) se vea de verdad
    if (clave == 'fondo' && Premium.i.tema != Cosmeticos.ninguno) {
      final social = socialDe(context);
      if (social != null) {
        try {
          await Premium.i.guardar(social, tema: Cosmeticos.ninguno);
        } catch (_) {}
      }
    }
    if (!mounted) return;
    await Caudal.leer(context).ajustes.poner(clave, valor);
    if (mounted) setState(() {});
  }

  /// Un escenario del reproductor: solo con beneficios; si no, avisa igual que el resto de lo exclusivo.
  Future<void> _elegirEscenario(String clave) async {
    if (!Premium.i.activo) {
      Caudal.leer(context).avisar('Es exclusivo de donadores: dona o canjea un código de prueba para usarlo.');
      return;
    }
    await _poner('escenario_reproductor', clave);
  }

  Future<void> _propio({required bool fondo}) async {
    final a = Caudal.leer(context).ajustes;
    final actual = fondo
        ? (Aspecto.colorDe(a.texto('fondo')) ?? const Color(0xFF1A2340))
        : (Aspecto.colorDe(a.texto('acento')) ?? Aspecto.acentoDe(a.texto('acento')).$2);
    final elegido = await showModalBottomSheet<Color>(
      context: context,
      // por encima del mini reproductor y de la barra de abajo
      useRootNavigator: true,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: C.panel,
      showDragHandle: true,
      builder: (_) => SelectorColor(inicial: actual, fondo: fondo),
    );
    if (elegido != null) await _poner(fondo ? 'fondo' : 'acento', Aspecto.hexDe(elegido));
  }

  @override
  Widget build(BuildContext context) {
    final a = Caudal.of(context).ajustes;
    final acento = a.texto('acento');
    final fondo = a.texto('fondo');
    final acentoPropio = Aspecto.esPropio(acento);
    final fondoPropio = Aspecto.esPropio(fondo);
    // sin beneficios el ajuste se ignora: se ve «Ninguno» como elegido
    final escenarioActual = Premium.i.activo ? a.texto('escenario_reproductor') : '';
    return Scaffold(
      appBar: AppBar(title: const Text('Aspecto')),
      body: ListView(padding: const EdgeInsets.all(Esp.lado), children: [
        _Muestra(),
        const SizedBox(height: 8),
        Text('${Aspecto.acentoDe(acento).$1} sobre ${Aspecto.fondoDe(fondo).$1}. Se ve al momento en toda la app.',
            style: estiloSecundario),
        const SizedBox(height: Esp.xl),
        const Text('Color', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text('Botones, lo que suena y el degradado del Inicio.', style: estiloSecundario),
        const SizedBox(height: Esp.m),
        Wrap(spacing: 14, runSpacing: 14, children: [
          for (final e in Aspecto.acentos.entries)
            _Circulo(
              color: e.value.$2,
              nombre: e.value.$1,
              elegido: e.key == acento,
              alPulsar: () => _poner('acento', e.key),
            ),
          _Circulo(
            color: acentoPropio ? Aspecto.acentoDe(acento).$2 : null,
            nombre: acentoPropio ? 'Tu color' : 'Elegir…',
            elegido: acentoPropio,
            alPulsar: () => _propio(fondo: false),
          ),
        ]),
        const SizedBox(height: Esp.xl),
        const Text('Fondo', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text('El color de fondo de toda la app.', style: estiloSecundario),
        const SizedBox(height: Esp.m),
        GridView.count(
          crossAxisCount: 3,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 0.95,
          children: [
            for (final e in Aspecto.fondos.entries)
              _TarjetaFondo(
                colores: e.value.$2,
                nombre: e.value.$1,
                elegido: e.key == fondo,
                alPulsar: () => _poner('fondo', e.key),
              ),
            _TarjetaFondo(
              colores: fondoPropio ? Aspecto.fondoDe(fondo).$2 : null,
              nombre: fondoPropio ? 'Tu fondo' : 'Elegir…',
              elegido: fondoPropio,
              alPulsar: () => _propio(fondo: true),
            ),
          ],
        ),
        const SizedBox(height: Esp.xl),
        const Text('Con personajes', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text('Sus colores y el personaje: lo arrastras a donde quieras y baila con la música. Si tienes mascotas, también camina por la barra.',
            style: estiloSecundario),
        const SizedBox(height: Esp.m),
        GridView.count(
          crossAxisCount: 3,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 0.95,
          children: [
            for (final e in Aspecto.temas.entries)
              _TarjetaFondo(
                colores: e.value.$3,
                nombre: e.value.$1,
                patron: Aspecto.patronDe(e.key),
                elegido: e.key == fondo,
                alPulsar: () async {
                  // un fondo con personaje trae su color (luego se puede cambiar)
                  await _poner('acento', Aspecto.hexDe(e.value.$2));
                  await _poner('fondo', e.key);
                  // y su personaje camina por la barra (solo si la cuenta tiene mascotas)
                  await MascotaApp.i.elegir(e.key);
                },
              ),
          ],
        ),
        if (Aspecto.patron != null) ...[
          const SizedBox(height: Esp.m),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Que baile con la música'),
            subtitle: const Text('Rebota y se mece al ritmo mientras suena. En pausa se queda quieto.', style: estiloSecundario),
            value: a.sino('personaje_baila'),
            onChanged: (v) => _poner('personaje_baila', v),
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: a.decimal('personaje_x') < 0
                  ? null
                  : () async {
                      await _poner('personaje_x', -1.0);
                      await _poner('personaje_y', -1.0);
                    },
              icon: const Icon(Icons.south_east_rounded),
              label: const Text('Devolverlo a su esquina'),
            ),
          ),
        ],
        const SizedBox(height: Esp.xl),
        const Text('Escenarios del reproductor', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text('Un fondo animado en la pantalla grande del reproductor. Es exclusivo de donadores.',
            style: estiloSecundario),
        const SizedBox(height: Esp.m),
        SizedBox(
          height: 128,
          child: ListView(
            scrollDirection: Axis.horizontal,
            clipBehavior: Clip.none,
            children: [
              _MiniEscenario(
                nombre: 'Ninguno',
                elegido: escenarioActual.isEmpty,
                alPulsar: () => _poner('escenario_reproductor', ''),
              ),
              for (final e in escenarios)
                _MiniEscenario(
                  nombre: e.nombre,
                  asset: e.asset,
                  elegido: escenarioActual == e.clave,
                  bloqueado: !Premium.i.activo,
                  alPulsar: () => _elegirEscenario(e.clave),
                ),
            ],
          ),
        ),
        const SizedBox(height: Esp.xl),
        Center(
          child: TextButton.icon(
            onPressed: acento == 'cian' && fondo == 'oscuro'
                ? null
                : () async {
                    await _poner('acento', 'cian');
                    await _poner('fondo', 'oscuro');
                  },
            icon: const Icon(Icons.restart_alt_rounded),
            label: const Text('Volver al aspecto de siempre'),
          ),
        ),
      ]),
    );
  }
}

/// Un escenario para elegir: su miniatura con las esquinas redondeadas y el nombre debajo.
/// Sin beneficios lleva candado (al tocarla avisa, en _elegirEscenario).
class _MiniEscenario extends StatelessWidget {
  const _MiniEscenario({
    required this.nombre,
    required this.elegido,
    required this.alPulsar,
    this.asset,
    this.bloqueado = false,
  });
  final String nombre;
  final String? asset;
  final bool elegido, bloqueado;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(right: 12),
        child: Semantics(
          button: true,
          selected: elegido,
          label: nombre,
          child: GestureDetector(
            onTap: alPulsar,
            child: SizedBox(
              width: 96,
              child: Column(children: [
                Expanded(
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    clipBehavior: Clip.antiAlias,
                    decoration: BoxDecoration(
                      color: C.superficie,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: elegido ? C.acento : C.superficie3, width: elegido ? 2.5 : 1),
                    ),
                    child: Stack(fit: StackFit.expand, children: [
                      if (asset != null)
                        Image.asset(asset!,
                            fit: BoxFit.cover,
                            cacheWidth: 320,
                            filterQuality: FilterQuality.medium,
                            excludeFromSemantics: true,
                            errorBuilder: (_, _, _) => const SizedBox.shrink())
                      else
                        const Center(child: Icon(Icons.block_rounded, color: C.texto2, size: 28)),
                      if (bloqueado)
                        Container(
                          color: Colors.black.withValues(alpha: 0.45),
                          alignment: Alignment.center,
                          child: const Icon(Icons.lock_rounded, color: Colors.white, size: 24),
                        ),
                    ]),
                  ),
                ),
                const SizedBox(height: 6),
                Text(nombre,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        fontSize: 12,
                        color: elegido ? C.texto : C.texto2,
                        fontWeight: elegido ? FontWeight.w800 : FontWeight.w500)),
              ]),
            ),
          ),
        ),
      );
}

/// Elegir un color propio con el dedo: tono, intensidad y brillo, con una
/// vista previa de cómo queda en la app. Para el fondo se muestra ya
/// oscurecido (el texto de la app es claro).
class SelectorColor extends StatefulWidget {
  const SelectorColor({super.key, required this.inicial, required this.fondo});
  final Color inicial;
  final bool fondo;

  @override
  State<SelectorColor> createState() => _SelectorColorState();
}

class _SelectorColorState extends State<SelectorColor> {
  late HSVColor _hsv;

  static const _rapidos = [
    Color(0xFFFF1744), Color(0xFFFF4081), Color(0xFFE040FB), Color(0xFF7C4DFF), Color(0xFF536DFE),
    Color(0xFF40C4FF), Color(0xFF18FFFF), Color(0xFF64FFDA), Color(0xFF69F0AE), Color(0xFFB2FF59),
    Color(0xFFEEFF41), Color(0xFFFFD740), Color(0xFFFFAB40), Color(0xFFFF6E40), Color(0xFFBCAAA4),
    Color(0xFFE0E0E0),
  ];

  @override
  void initState() {
    super.initState();
    _hsv = HSVColor.fromColor(widget.inicial);
  }

  Color get _color => _hsv.toColor();

  @override
  Widget build(BuildContext context) {
    final hex = Aspecto.hexDe(_color);
    final acento = widget.fondo ? (C.acento, C.acentoTexto) : (Aspecto.acentoDe(hex).$2, Aspecto.acentoDe(hex).$4);
    final capas = widget.fondo ? Aspecto.fondoDe(hex).$2 : [C.fondo, C.panel, C.superficie, C.superficie2, C.superficie3, C.borde];
    // lo de arriba se desplaza; Cancelar / Usar este quedan siempre fijos abajo
    return Padding(
      padding: EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, Esp.lado + MediaQuery.viewInsetsOf(context).bottom),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Flexible(
          child: SingleChildScrollView(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(widget.fondo ? 'Tu fondo' : 'Tu color',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
        const SizedBox(height: 4),
        Text(widget.fondo
            ? 'Se oscurece lo justo para que todo se lea bien.'
            : 'Si es muy oscuro se aclara un poco para que se vea.', style: estiloSecundario),
        const SizedBox(height: Esp.m),
        // vista previa: un trocito de la app con este color
        Container(
          height: 92,
          decoration: BoxDecoration(color: capas[0], borderRadius: BorderRadius.circular(16),
              border: Border.all(color: capas[5])),
          padding: const EdgeInsets.all(12),
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: capas[3], borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              Container(width: 44, height: 44,
                  decoration: BoxDecoration(color: capas[4], borderRadius: BorderRadius.circular(8))),
              const SizedBox(width: 12),
              Expanded(
                child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Lo que suena', style: TextStyle(fontWeight: FontWeight.w800, color: acento.$1)),
                      const Text('Artista', style: TextStyle(fontSize: 12.5, color: C.texto2)),
                    ]),
              ),
              Container(
                width: 40, height: 40,
                decoration: BoxDecoration(color: acento.$1, shape: BoxShape.circle),
                child: Icon(Icons.play_arrow_rounded, color: acento.$2),
              ),
            ]),
          ),
        ),
        const SizedBox(height: Esp.m),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final c in _rapidos)
            GestureDetector(
              onTap: () => setState(() => _hsv = HSVColor.fromColor(c)),
              child: Container(width: 30, height: 30,
                  decoration: BoxDecoration(color: c, shape: BoxShape.circle,
                      border: Border.all(color: Aspecto.hexDe(c) == hex ? Colors.white : Colors.transparent, width: 2))),
            ),
        ]),
        const SizedBox(height: Esp.m),
        _Barra(
          titulo: 'Tono',
          valor: _hsv.hue / 360,
          colores: [for (var h = 0; h <= 360; h += 60) HSVColor.fromAHSV(1, h.toDouble(), 1, 1).toColor()],
          alCambiar: (v) => setState(() => _hsv = _hsv.withHue((v * 360).clamp(0, 359.9))),
        ),
        _Barra(
          titulo: 'Intensidad',
          valor: _hsv.saturation,
          colores: [_hsv.withSaturation(0).toColor(), _hsv.withSaturation(1).toColor()],
          alCambiar: (v) => setState(() => _hsv = _hsv.withSaturation(v)),
        ),
        _Barra(
          titulo: 'Brillo',
          valor: _hsv.value,
          colores: [Colors.black, _hsv.withValue(1).toColor()],
          alCambiar: (v) => setState(() => _hsv = _hsv.withValue(v)),
        ),
        const SizedBox(height: Esp.m),
        Row(children: [
          Container(width: 22, height: 22, decoration: BoxDecoration(color: _color, shape: BoxShape.circle)),
          const SizedBox(width: 8),
          Text(hex, style: const TextStyle(fontWeight: FontWeight.w700, fontFamily: 'monospace')),
        ]),
            ]),
          ),
        ),
        const SizedBox(height: Esp.m),
        Row(children: [
          Expanded(
            child: OutlinedButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: FilledButton(
              style: FilledButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto),
              onPressed: () => Navigator.pop(context, _color),
              child: const Text('Usar este'),
            ),
          ),
        ]),
      ]),
    );
  }
}

/// Una barra con degradado que se arrastra con el dedo.
class _Barra extends StatelessWidget {
  const _Barra({required this.titulo, required this.valor, required this.colores, required this.alCambiar});
  final String titulo;
  final double valor;
  final List<Color> colores;
  final ValueChanged<double> alCambiar;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 10),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(titulo, style: const TextStyle(fontSize: 13, color: C.texto2)),
          const SizedBox(height: 6),
          LayoutBuilder(builder: (context, medidas) {
            final ancho = medidas.maxWidth;
            void tocar(double x) => alCambiar((x / ancho).clamp(0.0, 1.0));
            return Semantics(
              slider: true,
              label: titulo,
              value: '${(valor * 100).round()} %',
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTapDown: (d) => tocar(d.localPosition.dx),
                onHorizontalDragUpdate: (d) => tocar(d.localPosition.dx),
                child: SizedBox(
                  height: 34,
                  child: Stack(alignment: Alignment.centerLeft, clipBehavior: Clip.none, children: [
                    Container(
                      height: 18,
                      decoration: BoxDecoration(borderRadius: BorderRadius.circular(9),
                          gradient: LinearGradient(colors: colores)),
                    ),
                    Positioned(
                      left: (valor.clamp(0.0, 1.0) * ancho) - 13,
                      child: Container(
                        width: 26, height: 26,
                        decoration: BoxDecoration(shape: BoxShape.circle, color: Colors.white,
                            boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 4)]),
                      ),
                    ),
                  ]),
                ),
              ),
            );
          }),
        ]),
      );
}

/// Un trocito del Inicio con los colores elegidos.
class _Muestra extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        height: 150,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: C.borde),
          gradient: LinearGradient(colors: [C.cabecera, C.fondo],
              begin: Alignment.topCenter, end: Alignment.bottomCenter),
        ),
        padding: const EdgeInsets.all(Esp.l),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            CircleAvatar(radius: 14, backgroundColor: C.acento,
                child: Text('A', style: TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900))),
            const SizedBox(width: 10),
            const Text('Buenas tardes', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          ]),
          const Spacer(),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              Container(width: 36, height: 36,
                  decoration: BoxDecoration(color: C.superficie3, borderRadius: BorderRadius.circular(6))),
              const SizedBox(width: 10),
              const Expanded(child: Text('Lo que suena', style: TextStyle(fontWeight: FontWeight.w700))),
              Icon(Icons.favorite_rounded, color: C.acento),
              const SizedBox(width: 8),
              Container(
                width: 34, height: 34,
                decoration: BoxDecoration(color: C.acento, shape: BoxShape.circle),
                child: Icon(Icons.play_arrow_rounded, color: C.acentoTexto),
              ),
            ]),
          ),
        ]),
      );
}

/// Un color para elegir. Sin color: el arcoíris de «elegir el tuyo».
class _Circulo extends StatelessWidget {
  const _Circulo({required this.color, required this.nombre, required this.elegido, required this.alPulsar});
  final Color? color;
  final String nombre;
  final bool elegido;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) {
    final c = color;
    final marca = c == null || c.computeLuminance() > 0.5 ? const Color(0xFF111111) : Colors.white;
    return Semantics(
      button: true,
      selected: elegido,
      label: nombre,
      child: GestureDetector(
        onTap: alPulsar,
        child: SizedBox(
          width: 64,
          child: Column(children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 48, height: 48,
              decoration: BoxDecoration(
                color: c,
                gradient: c == null
                    ? const SweepGradient(colors: [Color(0xFFFF5C8A), Color(0xFFFF8A3D), Color(0xFFF5C542),
                        Color(0xFF2BD576), Color(0xFF22D3EE), Color(0xFF4C8DFF), Color(0xFF8B6CFF), Color(0xFFFF5C8A)])
                    : null,
                shape: BoxShape.circle,
                border: Border.all(color: elegido ? Colors.white : Colors.transparent, width: 3),
              ),
              child: elegido
                  ? Icon(Icons.check_rounded, color: marca)
                  : (c == null ? const Icon(Icons.add_rounded, color: Colors.white) : null),
            ),
            const SizedBox(height: 6),
            Text(nombre, style: TextStyle(fontSize: 12, color: elegido ? C.texto : C.texto2,
                fontWeight: elegido ? FontWeight.w800 : FontWeight.w500)),
          ]),
        ),
      ),
    );
  }
}

/// Un fondo para elegir. Sin colores: la tarjeta de «elegir el tuyo».
class _TarjetaFondo extends StatelessWidget {
  const _TarjetaFondo(
      {required this.colores, required this.nombre, required this.elegido, required this.alPulsar, this.patron});
  final List<Color>? colores;

  /// El personaje del fondo (se asoma en la esquina de la tarjeta).
  final String? patron;
  final String nombre;
  final bool elegido;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) {
    final cs = colores;
    return Semantics(
      button: true,
      selected: elegido,
      label: nombre,
      child: GestureDetector(
        onTap: alPulsar,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: BoxDecoration(
            color: cs?[0] ?? C.superficie,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: elegido ? C.acento : (cs?[5] ?? C.superficie3), width: elegido ? 2.5 : 1),
          ),
          padding: const EdgeInsets.all(10),
          child: Stack(fit: StackFit.expand, children: [
            if (patron != null)
              // el personaje, chico, en la esquina (como en la app)
              Align(
                alignment: const Alignment(0.98, 0.3),
                child: Image.asset(patron!, height: 37, filterQuality: FilterQuality.medium,
                    excludeFromSemantics: true, errorBuilder: (_, _, _) => const SizedBox.shrink()),
              ),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (cs != null) ...[
              Container(height: 10, width: 40,
                  decoration: BoxDecoration(color: cs[3], borderRadius: BorderRadius.circular(4))),
              const SizedBox(height: 6),
              Container(height: 22,
                  decoration: BoxDecoration(color: cs[2], borderRadius: BorderRadius.circular(6))),
            ] else
              const Expanded(child: Center(child: Icon(Icons.palette_outlined, color: C.texto2, size: 28))),
            if (cs != null) const Spacer(),
            Row(children: [
              Expanded(child: Text(nombre, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700))),
              if (elegido) Icon(Icons.check_circle_rounded, size: 16, color: C.acento),
            ]),
          ]),
          ]),
        ),
      ),
    );
  }
}
