// «Quién puede ver esta lista»: dos interruptores para elegir si la lista es pública y si se muestra
// en el perfil. Vale para todas las cuentas. Lo guardado viaja a la nube con la sincronización.

import 'package:flutter/material.dart';

import '../servicios.dart';
import '../tema.dart';

/// Abre la hoja de privacidad de la lista local [id].
Future<void> mostrarHojaPrivacidadLista(BuildContext context, int id) async {
  final s = Caudal.leer(context);
  final l = await s.coleccion.lista(id);
  if (l == null || !context.mounted) return;
  await showModalBottomSheet<void>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    builder: (_) => HojaPrivacidadLista(
      id: id,
      publica: (l['publica'] ?? 0) == 1,
      enPerfil: (l['en_perfil'] ?? 0) == 1,
    ),
  );
}

class HojaPrivacidadLista extends StatefulWidget {
  const HojaPrivacidadLista({super.key, required this.id, required this.publica, required this.enPerfil});
  final int id;
  final bool publica;
  final bool enPerfil;

  @override
  State<HojaPrivacidadLista> createState() => _HojaPrivacidadListaState();
}

class _HojaPrivacidadListaState extends State<HojaPrivacidadLista> {
  late bool _publica = widget.publica;
  late bool _enPerfil = widget.publica && widget.enPerfil;

  Future<void> _guardar() async {
    final s = Caudal.leer(context);
    await s.coleccion.editarLista(widget.id, publica: _publica, enPerfil: _enPerfil);
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, 16, Esp.lado, 12),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Quién puede ver esta lista', style: estiloTituloSeccion),
          const SizedBox(height: 4),
          Text(
            _publica
                ? 'Cualquier persona de Caudal puede abrirla y escucharla.'
                : 'Ahora es privada: solo tú la ves.',
            style: estiloSecundario,
          ),
          const SizedBox(height: 8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Lista pública'),
            subtitle: const Text('Si la dejas privada, nadie más puede abrirla.'),
            value: _publica,
            onChanged: (v) {
              setState(() {
                _publica = v;
                if (!v) _enPerfil = false;
              });
              _guardar();
            },
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Mostrar en mi perfil'),
            subtitle: Text(_publica
                ? 'Quien visite tu perfil la verá junto a tus datos.'
                : 'Para mostrarla en tu perfil, primero hazla pública.'),
            value: _enPerfil,
            onChanged: _publica
                ? (v) {
                    setState(() => _enPerfil = v);
                    _guardar();
                  }
                : null,
          ),
        ]),
      ),
    );
  }
}
