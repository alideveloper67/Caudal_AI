import 'package:flutter/material.dart';

import '../../nucleo/eq_avanzado.dart';
import '../../nucleo/premium_letras.dart';
import '../../reproduccion/salida_audio.dart';
import '../servicios.dart';
import '../tema.dart';
import 'donar.dart';

const textoBloqueoEqAvanzado = 'El ecualizador avanzado es para donadores y fundadores de Caudal: '
    '15 bandas, preamplificador, tus ajustes guardados con nombre y uno distinto para audífonos, '
    'parlante y bluetooth que se pone solo al cambiar de salida.\n\n'
    'Para tenerlo, apoya a Caudal con una donación o canjea un código de prueba. '
    'El ecualizador normal sigue disponible para todos.';

/// La fila que abre el ecualizador avanzado (con candado si no hay beneficios).
class BotonEqAvanzado extends StatelessWidget {
  const BotonEqAvanzado({super.key});

  @override
  Widget build(BuildContext context) {
    final premium = esPremiumLetras();
    final enUso = premium && Caudal.leer(context).ajustes.sino('eq_avanzado');
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(premium ? Icons.tune_rounded : Icons.lock_outline_rounded, color: C.texto2),
      title: const Text('Ecualizador avanzado'),
      subtitle: Text(
          premium
              ? '15 bandas, preamplificador, ajustes con nombre y uno por salida${enUso ? ' · en uso' : ''}'
              : 'Para donadores y fundadores · toca para ver cómo tenerlo',
          style: estiloSecundario),
      trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
      onTap: () => mostrarEqAvanzado(context),
    );
  }
}

/// Abre el avanzado, o sin beneficios explica cómo conseguirlo.
Future<void> mostrarEqAvanzado(BuildContext context) async {
  if (!esPremiumLetras()) return mostrarCandadoEqAvanzado(context);
  await showModalBottomSheet<void>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    isDismissible: false,
    enableDrag: false,
    builder: (_) => const HojaEqAvanzado(),
  );
}

Future<void> mostrarCandadoEqAvanzado(BuildContext context) => showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.superficie2,
        title: const Row(children: [
          Icon(Icons.lock_outline_rounded, size: 20),
          SizedBox(width: 8),
          Expanded(child: Text('Ecualizador avanzado')),
        ]),
        content: const Text(textoBloqueoEqAvanzado),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Ahora no')),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              mostrarDonar(context);
            },
            child: const Text('Cómo tenerlo'),
          ),
        ],
      ),
    );

class HojaEqAvanzado extends StatefulWidget {
  const HojaEqAvanzado({super.key});

  @override
  State<HojaEqAvanzado> createState() => _HojaEqAvanzadoState();
}

class _HojaEqAvanzadoState extends State<HojaEqAvanzado> {
  late EstadoEqAvanzado _e;
  late EstadoEqAvanzado _antes;
  bool _iniciado = false;
  bool _guardado = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_iniciado) return;
    _iniciado = true;
    _e = Caudal.leer(context).ajustes.eqAvanzado;
    _antes = _e.copia();
  }

  bool get _cambiado =>
      _e.activo != _antes.activo || _e.bandasJson != _antes.bandasJson || _e.preamp != _antes.preamp ||
      _e.guardadosJson != _antes.guardadosJson || _e.porSalidaJson != _antes.porSalidaJson;

  Future<void> _probar() async {
    final s = Caudal.leer(context);
    await s.ajustes.ponerEqAvanzado(_e, avisar: false);
    await s.reproductor.aplicarSonido();
  }

  Future<void> _cerrar({required bool guardar}) async {
    final s = Caudal.leer(context);
    _guardado = true;
    await s.ajustes.ponerEqAvanzado(guardar ? _e : _antes, avisar: guardar);
    await s.reproductor.aplicarSonido();
    if (mounted) Navigator.pop(context);
    if (guardar) s.avisar('Ecualizador avanzado guardado');
  }

  Future<void> _guardarComo() async {
    final control = TextEditingController(text: _e.nombre);
    final nombre = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.superficie2,
        title: const Text('Guardar ajuste'),
        content: TextField(
          controller: control,
          autofocus: true,
          maxLength: largoNombre,
          decoration: const InputDecoration(hintText: 'Nombre (p. ej. «Coche»)'),
          onSubmitted: (t) => Navigator.pop(ctx, t),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, control.text), child: const Text('Guardar')),
        ],
      ),
    );
    if (nombre == null || !mounted) return;
    final hecho = _e.guardarComo(nombre);
    if (hecho.isEmpty) {
      Caudal.leer(context).avisar('Escribe un nombre (caben $maxGuardados ajustes).');
      return;
    }
    setState(() {});
    await _probar();
  }

  String _db(double v) => '${v > 0 ? '+' : ''}${v.toStringAsFixed(1).replaceAll('.0', '').replaceAll('.', ',')}';

  @override
  Widget build(BuildContext context) {
    final alto = MediaQuery.sizeOf(context).height;
    final lista = _e.lista;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (hecho, _) {
        if (!hecho && !_guardado) _cerrar(guardar: false);
      },
      child: SizedBox(
        height: alto * 0.9,
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 8, 4),
            child: Row(children: [
              const Expanded(child: Text('Ecualizador avanzado', style: estiloTituloPagina)),
              IconButton(icon: const Icon(Icons.close_rounded), onPressed: () => _cerrar(guardar: false)),
            ]),
          ),
          Expanded(
            child: ListView(padding: const EdgeInsets.symmetric(horizontal: 20), children: [
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('Usar en lugar del normal'),
                value: _e.activo,
                onChanged: (v) {
                  setState(() => _e.activo = v);
                  _probar();
                },
              ),
              // ---- ajustes guardados
              SizedBox(
                height: 40,
                child: ListView(scrollDirection: Axis.horizontal, children: [
                  for (final n in lista.keys)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: InputChip(
                        label: Text(n),
                        selected: _e.nombre == n,
                        showCheckmark: false,
                        selectedColor: C.acento,
                        labelStyle: TextStyle(fontWeight: FontWeight.w600,
                            color: _e.nombre == n ? C.acentoTexto : C.texto),
                        backgroundColor: C.superficie3,
                        side: BorderSide.none,
                        shape: const StadiumBorder(),
                        onSelected: (_) {
                          setState(() {
                            _e.cargar(n);
                            _e.activo = true;
                          });
                          _probar();
                        },
                        onDeleted: _e.nombre == n
                            ? () {
                                setState(() => _e.borrar(n));
                                _probar();
                              }
                            : null,
                        deleteButtonTooltipMessage: 'Borrar',
                      ),
                    ),
                ]),
              ),
              Row(children: [
                TextButton.icon(
                  onPressed: _guardarComo,
                  icon: const Icon(Icons.bookmark_add_outlined, size: 18),
                  label: const Text('Guardar como…'),
                ),
                const Spacer(),
                TextButton(
                  onPressed: () {
                    setState(() {
                      _e.bandas = limpiarBandas(const []);
                      _e.preamp = 0;
                      _e.nombre = '';
                    });
                    _probar();
                  },
                  child: const Text('Dejar plano', style: TextStyle(color: C.texto2)),
                ),
              ]),
              // ---- preamplificador
              Row(children: [
                const Expanded(child: Text('Preamplificador', style: estiloTituloSeccion)),
                Text('${_db(_e.preamp)} dB', style: const TextStyle(fontWeight: FontWeight.w800)),
              ]),
              Slider(
                key: const Key('preamp'),
                value: _e.preamp, min: preampMinimo, max: preampMaximo,
                divisions: ((preampMaximo - preampMinimo) / pasoBanda).round(),
                onChanged: (v) => setState(() {
                  _e.preamp = limpiarPreamp(v);
                  _e.nombre = '';
                }),
                onChangeEnd: (_) => _probar(),
              ),
              const Text('Sube o baja todo antes del ecualizador. Un limitador evita que se rompa el sonido.',
                  style: estiloSecundario),
              const SizedBox(height: 12),
              // ---- 15 bandas
              SizedBox(
                height: 220,
                child: ListView(scrollDirection: Axis.horizontal, children: [
                  for (var i = 0; i < frecuenciasAvanzado.length; i++)
                    SizedBox(
                      width: 38,
                      child: Column(children: [
                        Text(_db(_e.bandas[i]), style: const TextStyle(fontSize: 10.5, color: C.texto2)),
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
                                key: Key('banda$i'),
                                value: _e.bandas[i],
                                min: -rangoBanda, max: rangoBanda,
                                divisions: (2 * rangoBanda / pasoBanda).round(),
                                onChanged: (v) => setState(() {
                                  _e.bandas[i] = limpiarBandas([v]).first;
                                  _e.nombre = '';
                                  _e.activo = true;
                                }),
                                onChangeEnd: (_) => _probar(),
                              ),
                            ),
                          ),
                        ),
                        Text(etiquetasAvanzado[i], style: const TextStyle(fontSize: 10, color: C.texto3)),
                      ]),
                    ),
                ]),
              ),
              const Divider(height: 30),
              // ---- por salida
              const Text('Un ajuste para cada salida', style: estiloTituloSeccion),
              const SizedBox(height: 4),
              ValueListenableBuilder<String?>(
                valueListenable: SalidaAudio.tipo,
                builder: (_, ahora, __) => Text(
                    'Cuando conectas audífonos, un parlante o algo por bluetooth, Caudal pone solo el '
                    'ajuste que elijas aquí.${ahora != null ? ' Ahora suena por: ${(nombresSalida[ahora] ?? ahora).toLowerCase()}.' : ''}',
                    style: estiloSecundario),
              ),
              const SizedBox(height: 8),
              for (final t in tiposSalida)
                Row(children: [
                  Expanded(child: Text(nombresSalida[t]!)),
                  DropdownButton<String>(
                    key: Key('salida_$t'),
                    value: lista.containsKey(_e.porSalida[t]) ? _e.porSalida[t] : '',
                    dropdownColor: C.superficie2,
                    items: [
                      const DropdownMenuItem(value: '', child: Text('No cambiar')),
                      for (final n in lista.keys) DropdownMenuItem(value: n, child: Text(n)),
                    ],
                    onChanged: (v) => setState(() => _e.asignar(t, v ?? '')),
                  ),
                ]),
              const SizedBox(height: 16),
            ]),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
              child: Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                TextButton(onPressed: () => _cerrar(guardar: false), child: const Text('Cancelar')),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _cambiado ? () => _cerrar(guardar: true) : null,
                  style: FilledButton.styleFrom(shape: const StadiumBorder()),
                  child: const Text('Guardar'),
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}
