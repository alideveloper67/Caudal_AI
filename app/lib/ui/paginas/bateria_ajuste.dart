import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show MethodChannel;

import '../../nucleo/plataforma.dart';
import '../plataforma.dart';
import '../tema.dart';

/// "Música con la pantalla apagada": en algunos teléfonos el ahorro de batería
/// duerme a Caudal y la siguiente canción no carga hasta encender la pantalla.
/// Aquí se ve si Caudal está libre de esa restricción y se abre el ajuste del sistema.
class AjusteBateria extends StatefulWidget {
  const AjusteBateria({super.key});

  @override
  State<AjusteBateria> createState() => _AjusteBateriaState();
}

class _AjusteBateriaState extends State<AjusteBateria> with WidgetsBindingObserver {
  static const _canal = MethodChannel('caudal/energia');
  bool? _libre;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _leer();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    if (estado == AppLifecycleState.resumed) _leer(); // al volver del ajuste del sistema
  }

  Future<void> _leer() async {
    try {
      final v = await _canal.invokeMethod<bool>('sinRestriccion');
      if (mounted) setState(() => _libre = v);
    } catch (_) {
      if (mounted) setState(() => _libre = null);
    }
  }

  Future<void> _abrir() async {
    try {
      await _canal.invokeMethod('abrirAjusteBateria');
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    if (!Plataforma.esAndroid) return const SizedBox.shrink();
    final libre = _libre;
    return ListTile(
      leading: Icon(libre == true ? Icons.battery_charging_full_rounded : Icons.battery_saver_rounded,
          color: libre == true ? C.acento : C.texto2),
      title: const Text('Música con la pantalla apagada'),
      subtitle: Text(
        libre == true
            ? 'Listo: Caudal no se duerme con el ahorro de batería.'
            : 'Si al apagar la pantalla la música se detiene al acabar la canción, quita el ahorro de batería a Caudal: pulsa aquí y elige «Sin restricciones».',
        style: estiloSecundario,
      ),
      trailing: const Icon(Icons.chevron_right_rounded),
      onTap: _abrir,
    );
  }
}
