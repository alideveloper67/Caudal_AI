import 'package:flutter/material.dart';

import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';

const bandasHz = ['31', '62', '125', '250', '500', '1k', '2k', '4k', '8k', '16k'];

const presetsEq = <String, List<int>>{
  'Plano': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  'Graves': [7, 6, 5, 3, 1, 0, 0, 0, 0, 0],
  'Graves fuertes': [10, 9, 7, 4, 1, 0, 0, 0, 0, 0],
  'Agudos': [0, 0, 0, 0, 0, 1, 3, 5, 6, 7],
  'Voz': [-2, -1, 0, 2, 4, 4, 3, 1, 0, -1],
  'Pop': [-1, 1, 3, 4, 3, 0, -1, -1, 0, 1],
  'Rock': [5, 4, 2, 0, -1, 0, 2, 3, 4, 4],
  'Electrónica': [6, 5, 2, 0, -2, 1, 0, 2, 5, 6],
  'Hip hop': [6, 5, 3, 2, -1, -1, 1, 0, 2, 3],
  'Clásica': [4, 3, 2, 1, -1, -1, 0, 2, 3, 4],
  'Acústica': [4, 3, 2, 1, 1, 1, 2, 3, 3, 2],
  'Nocturno': [3, 2, 1, 0, -1, -2, -3, -4, -5, -6],
};

const nivelesSuper = ['Normal', 'Fuerte', 'Más fuerte', 'Muy fuerte', 'Máximo'];

/// Ecualizador, super volumen, velocidad y fundido. Se escucha en vivo
/// mientras se mueve, pero solo se queda si se pulsa Guardar.
Future<void> mostrarSonido(BuildContext context) => showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      isDismissible: false,
      enableDrag: false,
      builder: (_) => const _HojaSonido(),
    );

class _HojaSonido extends StatefulWidget {
  const _HojaSonido();

  @override
  State<_HojaSonido> createState() => _HojaSonidoState();
}

class _HojaSonidoState extends State<_HojaSonido> {
  late final Map<String, Object> _antes;
  late bool _eq;
  late List<int> _bandas;
  late String _preset;
  late int _super;
  late bool _normalizar;
  late double _velocidad;
  late int _crossfade;
  bool _guardado = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final a = Caudal.leer(context).ajustes;
    if (_bandasIniciadas) return;
    _bandasIniciadas = true;
    _eq = a.sino('ecualizador');
    // las bandas pueden venir de la nube (otra version, otro numero de bandas):
    // siempre 10 y dentro del rango de los deslizadores, o el Slider revienta
    final guardadas = a.bandasEq;
    _bandas = [for (var i = 0; i < 10; i++) i < guardadas.length ? guardadas[i].clamp(-12, 12) : 0];
    _preset = a.texto('eq_preset');
    _super = a.entero('super_volumen').clamp(0, nivelesSuper.length - 1);
    _normalizar = a.sino('normalizar');
    _velocidad = Caudal.leer(context).reproductor.velocidad.clamp(0.5, 2.0);
    _crossfade = a.entero('crossfade').clamp(0, 12);
    _antes = {
      'ecualizador': _eq, 'eq_bandas': List.of(_bandas), 'eq_preset': _preset,
      'super_volumen': _super, 'normalizar': _normalizar, 'velocidad': _velocidad, 'crossfade': _crossfade,
    };
  }

  bool _bandasIniciadas = false;

  bool get _cambiado =>
      _eq != _antes['ecualizador'] || _preset != _antes['eq_preset'] || _super != _antes['super_volumen'] ||
      _normalizar != _antes['normalizar'] || _velocidad != _antes['velocidad'] || _crossfade != _antes['crossfade'] ||
      _bandas.join(',') != (_antes['eq_bandas'] as List).join(',');

  /// Escribe los valores sin avisar a nadie y los aplica al sonido (vista previa).
  Future<void> _probar() async {
    final s = Caudal.leer(context);
    final a = s.ajustes;
    await a.poner('ecualizador', _eq, avisar: false);
    await a.poner('eq_bandas', _bandas, avisar: false);
    await a.poner('eq_preset', _preset, avisar: false);
    await a.poner('super_volumen', _super, avisar: false);
    await a.poner('normalizar', _normalizar, avisar: false);
    await s.reproductor.aplicarSonido();
    await s.reproductor.fijarVelocidad(_velocidad, guardar: false);
  }

  Future<void> _restaurar() async {
    final s = Caudal.leer(context);
    final a = s.ajustes;
    await a.poner('ecualizador', _antes['ecualizador']!, avisar: false);
    await a.poner('eq_bandas', _antes['eq_bandas']!, avisar: false);
    await a.poner('eq_preset', _antes['eq_preset']!, avisar: false);
    await a.poner('super_volumen', _antes['super_volumen']!, avisar: false);
    await a.poner('normalizar', _antes['normalizar']!, avisar: false);
    await s.reproductor.aplicarSonido();
    await s.reproductor.fijarVelocidad(_antes['velocidad'] as double, guardar: false);
  }

  Future<void> _guardar() async {
    final s = Caudal.leer(context);
    final a = s.ajustes;
    _guardado = true;
    await a.poner('ecualizador', _eq, avisar: false);
    await a.poner('eq_bandas', _bandas, avisar: false);
    await a.poner('eq_preset', _preset, avisar: false);
    await a.poner('super_volumen', _super, avisar: false);
    await a.poner('normalizar', _normalizar, avisar: false);
    await a.poner('crossfade', _crossfade);
    await s.reproductor.fijarVelocidad(_velocidad);
    await s.reproductor.aplicarSonido();
    s.sincronizador?.pronto();
    if (mounted) Navigator.pop(context);
    s.avisar('Sonido guardado');
  }

  Future<void> _cancelar() async {
    if (!_guardado) await _restaurar();
    if (mounted) Navigator.pop(context);
  }

  Future<bool> _preguntarAlSalir() async {
    if (!_cambiado) return true;
    final r = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.superficie2,
        title: const Text('¿Guardar los cambios?'),
        content: const Text('Cambiaste el sonido. Si no los guardas, vuelve como estaba.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, 'descartar'), child: const Text('Descartar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, 'guardar'), child: const Text('Guardar')),
        ],
      ),
    );
    if (r == 'guardar') {
      await _guardar();
      return false;
    }
    if (r == 'descartar') {
      await _restaurar();
      return true;
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final alto = MediaQuery.sizeOf(context).height;
    // en iPhone el libmpv no trae limitador ni normalizador
    final limitado = Caudal.leer(context).reproductor.sonidoLimitado;
    Future<void> salir() async {
      if (await _preguntarAlSalir() && context.mounted) Navigator.pop(context);
    }
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (hecho, _) async {
        if (hecho) return;
        if (await _preguntarAlSalir() && context.mounted) Navigator.pop(context);
      },
      // la hoja no se cierra arrastrando (preguntaria tarde por los cambios);
      // en iPhone, el borde izquierdo y bajar la cabecera hacen lo mismo que la X
      child: BordeVolver(
        alVolver: salir,
        child: SizedBox(
        height: alto * 0.88,
        child: Column(children: [
          GestureDetector(
            onVerticalDragEnd: esIOS
                ? (d) {
                    if ((d.primaryVelocity ?? 0) > 300) salir();
                  }
                : null,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 8, 4),
              child: Row(children: [
                const Expanded(child: Text('Sonido', style: estiloTituloPagina)),
                IconButton(icon: const Icon(Icons.close_rounded), onPressed: salir),
              ]),
            ),
          ),
          Expanded(
            child: ListView(padding: const EdgeInsets.symmetric(horizontal: 20), children: [
              // ---- super volumen
              const Text('Súper volumen', style: estiloTituloSeccion),
              const SizedBox(height: 4),
              Text(limitado ? 'Sube más el volumen que el máximo del teléfono.'
                  : 'Sube mucho más el volumen sin distorsionar: comprime con cuidado y limita los picos.',
                  style: estiloSecundario),
              const SizedBox(height: 10),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (var i = 0; i < nivelesSuper.length; i++)
                  ChoiceChip(
                    label: Text(nivelesSuper[i]),
                    selected: _super == i,
                    showCheckmark: false,
                    selectedColor: C.acento,
                    labelStyle: TextStyle(fontWeight: FontWeight.w700, color: _super == i ? C.acentoTexto : C.texto),
                    backgroundColor: C.superficie3,
                    side: BorderSide.none,
                    shape: const StadiumBorder(),
                    onSelected: (_) {
                      setState(() => _super = i);
                      _probar();
                    },
                  ),
              ]),
              if (limitado)
                const Padding(
                  padding: EdgeInsets.only(top: 8),
                  child: Text('En iPhone los niveles altos pueden distorsionar algo.',
                      style: TextStyle(fontSize: 12.5, color: C.texto3)),
                ),
              const SizedBox(height: 8),
              if (!limitado)
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('Igualar el volumen entre canciones'),
                subtitle: const Text('Que ninguna suene mucho más bajo o alto que otra', style: estiloSecundario),
                value: _normalizar,
                onChanged: (v) {
                  setState(() => _normalizar = v);
                  _probar();
                },
              ),
              const Divider(height: 28),
              // ---- ecualizador
              Row(children: [
                const Expanded(child: Text('Ecualizador', style: estiloTituloSeccion)),
                Switch.adaptive(value: _eq, onChanged: (v) {
                  setState(() => _eq = v);
                  _probar();
                }),
              ]),
              const SizedBox(height: 6),
              SizedBox(
                height: 40,
                child: ListView(scrollDirection: Axis.horizontal, children: [
                  for (final nombre in presetsEq.keys)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(nombre),
                        selected: _preset == nombre,
                        showCheckmark: false,
                        selectedColor: C.acento,
                        labelStyle: TextStyle(fontWeight: FontWeight.w600,
                            color: _preset == nombre ? C.acentoTexto : C.texto),
                        backgroundColor: C.superficie3,
                        side: BorderSide.none,
                        shape: const StadiumBorder(),
                        onSelected: (_) {
                          setState(() {
                            _preset = nombre;
                            _bandas = List.of(presetsEq[nombre]!);
                            _eq = true;
                          });
                          _probar();
                        },
                      ),
                    ),
                ]),
              ),
              const SizedBox(height: 10),
              AnimatedOpacity(
                duration: const Duration(milliseconds: 200),
                opacity: _eq ? 1 : 0.4,
                child: SizedBox(
                  height: 210,
                  child: Row(children: [
                    for (var i = 0; i < 10; i++)
                      Expanded(
                        child: Column(children: [
                          Text('${_bandas[i] > 0 ? '+' : ''}${_bandas[i]}',
                              style: const TextStyle(fontSize: 10.5, color: C.texto2)),
                          Expanded(
                            child: RotatedBox(
                              quarterTurns: 3,
                              child: SliderTheme(
                                data: SliderTheme.of(context).copyWith(
                                  trackHeight: 3,
                                  thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 7),
                                  overlayShape: SliderComponentShape.noOverlay,
                                ),
                                child: Slider(
                                  value: _bandas[i].toDouble(),
                                  min: -12, max: 12, divisions: 24,
                                  onChanged: !_eq ? null : (v) => setState(() {
                                    _bandas[i] = v.round();
                                    _preset = 'Personalizado';
                                  }),
                                  onChangeEnd: (_) => _probar(),
                                ),
                              ),
                            ),
                          ),
                          Text(bandasHz[i], style: const TextStyle(fontSize: 10.5, color: C.texto3)),
                        ]),
                      ),
                  ]),
                ),
              ),
              const Divider(height: 30),
              // ---- velocidad
              Row(children: [
                const Expanded(child: Text('Velocidad', style: estiloTituloSeccion)),
                Text('${_velocidad.toStringAsFixed(2).replaceAll(RegExp(r'0$'), '')}×',
                    style: const TextStyle(fontWeight: FontWeight.w800)),
              ]),
              Slider(value: _velocidad, min: 0.5, max: 2, divisions: 12,
                  onChanged: (v) => setState(() => _velocidad = v), onChangeEnd: (_) => _probar()),
              const SizedBox(height: 6),
              // ---- crossfade
              Row(children: [
                const Expanded(child: Text('Fundido entre canciones', style: estiloTituloSeccion)),
                Text(_crossfade == 0 ? 'Apagado' : '$_crossfade s', style: const TextStyle(fontWeight: FontWeight.w800)),
              ]),
              Slider(value: _crossfade.toDouble(), min: 0, max: 12, divisions: 12,
                  onChanged: (v) => setState(() => _crossfade = v.round())),
              const SizedBox(height: 16),
            ]),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
              child: Row(children: [
                // con la letra grande cede este (el menos importante) y no se desborda
                Expanded(child: Align(alignment: Alignment.centerLeft, child: TextButton(
                  onPressed: () {
                    setState(() {
                      _eq = false;
                      _bandas = List.filled(10, 0);
                      _preset = 'Plano';
                      _super = 0;
                      _normalizar = true;
                      _velocidad = 1;
                      _crossfade = 0;
                    });
                    _probar();
                  },
                  child: const Text('Restablecer', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: C.texto2)),
                ))),
                TextButton(onPressed: _cancelar, child: const Text('Cancelar')),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _cambiado ? _guardar : null,
                  style: FilledButton.styleFrom(shape: const StadiumBorder()),
                  child: const Text('Guardar'),
                ),
              ]),
            ),
          ),
        ]),
      ),
      ),
    );
  }
}
