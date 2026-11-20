import 'package:flutter/material.dart';

import '../ui/tema.dart';
import 'abrir_modo_coche.dart';
import 'coche_bluetooth.dart';

/// Ajustes > Modo coche: abrirlo a mano, que se abra solo con el Bluetooth del
/// coche, y cómo se usa Caudal en Android Auto y con la voz.
class ModoCocheAjustesPagina extends StatefulWidget {
  const ModoCocheAjustesPagina({super.key, this.fuente});

  /// El Bluetooth (en las pruebas, uno de mentira).
  final FuenteBluetooth? fuente;

  static Future<void> abrir(BuildContext context) => Navigator.of(context)
      .push(MaterialPageRoute<void>(builder: (_) => const ModoCocheAjustesPagina()));

  @override
  State<ModoCocheAjustesPagina> createState() => _ModoCocheAjustesPaginaState();
}

class _ModoCocheAjustesPaginaState extends State<ModoCocheAjustesPagina> {
  late final FuenteBluetooth _bt = widget.fuente ?? const BluetoothNativo();
  PreferenciasCoche? _prefs;
  bool _permiso = false;
  bool _cargandoAparatos = false;
  List<DispositivoBt> _aparatos = const [];

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    final p = await PreferenciasCoche.cargar();
    final permiso = _bt.disponible && await _bt.hayPermiso();
    if (!mounted) return;
    setState(() {
      _prefs = p;
      _permiso = permiso;
    });
    if (permiso) await _cargarAparatos();
  }

  Future<void> _cargarAparatos() async {
    setState(() => _cargandoAparatos = true);
    final lista = await _bt.emparejados();
    // primero los que parecen de coche, después los que suenan
    lista.sort((a, b) {
      int peso(DispositivoBt d) => d.esCoche ? 0 : (d.esAudio ? 1 : 2);
      final c = peso(a).compareTo(peso(b));
      return c != 0 ? c : a.nombreVisible.toLowerCase().compareTo(b.nombreVisible.toLowerCase());
    });
    if (!mounted) return;
    setState(() {
      _aparatos = lista;
      _cargandoAparatos = false;
    });
  }

  Future<void> _alternarSolo(bool si) async {
    final p = _prefs;
    if (p == null) return;
    if (si && !_permiso) {
      final ok = await _bt.pedirPermiso();
      if (!mounted) return;
      setState(() => _permiso = ok);
      if (!ok) return;
      await _cargarAparatos();
    }
    setState(() {
      p.abrirSolo = si;
      // la primera vez se marcan ya los que Android dice que son de coche
      if (si && p.dispositivos.isEmpty) {
        for (final d in _aparatos.where((d) => d.esCoche)) {
          p.alternar(d, true);
        }
      }
    });
    await p.guardar();
  }

  Future<void> _alternarAparato(DispositivoBt d, bool si) async {
    final p = _prefs;
    if (p == null) return;
    setState(() => p.alternar(d, si));
    await p.guardar();
  }

  Future<void> _pedirPermiso() async {
    final ok = await _bt.pedirPermiso();
    if (!mounted) return;
    setState(() => _permiso = ok);
    if (ok) {
      await _cargarAparatos();
    } else {
      await _bt.abrirAjustesDeLaApp();
    }
  }

  Widget _seccion(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.xl, Esp.lado, Esp.s),
        child: Semantics(header: true, child: Text(t, style: estiloTituloSeccion)),
      );

  Widget _parrafo(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, Esp.s),
        child: Text(t, style: estiloSecundario),
      );

  @override
  Widget build(BuildContext context) {
    final p = _prefs;
    return Scaffold(
      appBar: AppBar(title: const Text('Modo coche')),
      body: ListView(
        padding: const EdgeInsets.only(bottom: Esp.xxl),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, 0),
            child: SizedBox(
              height: 72,
              child: FilledButton.icon(
                onPressed: () => AbrirModoCoche.abrir(context),
                icon: const Icon(Icons.directions_car_rounded, size: 32),
                label: const Text('Abrir el modo coche', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                style: FilledButton.styleFrom(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                ),
              ),
            ),
          ),
          const SizedBox(height: Esp.s),
          _parrafo('Botones enormes, letra grande y mucho contraste para manejar la música sin mirar. '
              'La pantalla se queda encendida mientras está abierto.'),
          _seccion('Que se abra solo'),
          if (!_bt.disponible)
            _parrafo('En este teléfono Caudal no puede saber cuándo se conecta el coche. Ábrelo con el botón de arriba.')
          else if (p == null)
            const Padding(padding: EdgeInsets.all(Esp.l), child: Center(child: CircularProgressIndicator()))
          else ...[
            SwitchListTile(
              value: p.abrirSolo,
              onChanged: _alternarSolo,
              secondary: const Icon(Icons.bluetooth_connected_rounded),
              title: const Text('Al conectar el Bluetooth del coche'),
              subtitle: const Text('Con Caudal abierto sale al momento. Con Caudal cerrado te llega un aviso: tócalo y se abre.',
                  style: estiloSecundario),
            ),
            if (!_permiso)
              ListTile(
                leading: const Icon(Icons.lock_open_rounded),
                title: const Text('Falta el permiso de dispositivos cercanos'),
                subtitle: const Text('Caudal lo usa solo para saber cuándo se conecta tu coche.', style: estiloSecundario),
                trailing: TextButton(onPressed: _pedirPermiso, child: const Text('Dar permiso')),
              )
            else if (p.abrirSolo) ...[
              _parrafo('Elige el Bluetooth de tu coche:'),
              if (_cargandoAparatos)
                const Padding(padding: EdgeInsets.all(Esp.l), child: Center(child: CircularProgressIndicator()))
              else if (_aparatos.isEmpty)
                _parrafo('No hay aparatos emparejados. Empareja el coche desde los ajustes de Bluetooth del teléfono y vuelve aquí.')
              else
                for (final d in _aparatos)
                  CheckboxListTile(
                    value: p.contiene(d.direccion),
                    onChanged: (v) => _alternarAparato(d, v ?? false),
                    secondary: Icon(d.esCoche
                        ? Icons.directions_car_rounded
                        : d.esAudio
                            ? Icons.speaker_rounded
                            : Icons.bluetooth_rounded),
                    title: Text(d.nombreVisible),
                    subtitle: d.esCoche ? const Text('Parece la radio de un coche', style: estiloSecundario) : null,
                  ),
              if (p.dispositivos.isEmpty && _aparatos.isNotEmpty)
                _parrafo('Aún no elegiste ninguno: mientras tanto no se abrirá solo.'),
            ],
          ],
          _seccion('En la pantalla del coche'),
          _parrafo('Con Android Auto, Caudal sale entre las apps de música del coche: tus me gusta, tus listas, '
              'lo reciente y lo descargado, con la carátula y los botones de pausa, siguiente, me gusta y aleatorio. '
              'También puedes decir «Ok Google, pon … en Caudal».'),
          _parrafo('Si instalaste Caudal fuera de Google Play y no aparece en el coche: abre Android Auto en el teléfono, '
              'toca diez veces «Versión» para activar los ajustes de desarrollador y en el menú ⋮ activa «Fuentes desconocidas».'),
          _seccion('Accesos directos y voz'),
          _parrafo('Mantén pulsado el icono de Caudal para ir directo a: Me gusta en aleatorio, Buscar, Descargas o Mi mix.'),
          _parrafo('Con el asistente de Google: «Ok Google, abre mi mix en Caudal», «abre mis descargas en Caudal» '
              'o «pon Bad Bunny en Caudal».'),
        ],
      ),
    );
  }
}
