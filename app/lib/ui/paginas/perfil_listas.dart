// Las listas que una persona eligió mostrar en su perfil. En mi propio perfil salen todas, con una marca
// en las que solo veo yo. Si no hay nada que enseñar, la sección no ocupa lugar.

import 'package:flutter/material.dart';

import '../../nucleo/social.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';

class SeccionListasPerfil extends StatefulWidget {
  const SeccionListasPerfil({super.key, required this.usuario, required this.propio, required this.social});
  final String usuario;
  final bool propio;
  final Social? social;

  @override
  State<SeccionListasPerfil> createState() => _SeccionListasPerfilState();
}

class _SeccionListasPerfilState extends State<SeccionListasPerfil> {
  List<ListaPerfil> _listas = const [];

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    final social = widget.social;
    if (social == null) return;
    final l = await social.listasDePerfil(widget.usuario);
    if (mounted) setState(() => _listas = l);
  }

  Future<void> _abrir(ListaPerfil l) async {
    final s = Caudal.leer(context);
    if (widget.propio) {
      final id = await s.coleccion.idPorUuid(l.id);
      if (id != null && mounted) {
        s.abrirElemento(context, {'tipo': 'mi_lista', 'id': id, 'titulo': l.nombre});
        return;
      }
    }
    try {
      final d = await widget.social?.verListaPublica(l.id);
      final pistas = ListaPerfil.pistasDe(d);
      if (pistas.isEmpty) {
        s.avisar('Esta lista no tiene canciones para escuchar.');
        return;
      }
      await s.reproductor.reproducirLista(pistas, contexto: {'tipo': 'lista_publica', 'id': l.id, 'titulo': l.nombre});
    } catch (e) {
      s.avisar(Social.error(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_listas.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: Esp.entreSecciones - 4),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, 4),
          child: Text(widget.propio ? 'Mis listas' : 'Listas', style: estiloTituloSeccion),
        ),
        if (widget.propio)
          const Padding(
            padding: EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, 8),
            child: Text('Las marcadas las ves solo tú.', style: estiloSecundario),
          ),
        for (final l in _listas)
          InkWell(
            onTap: () => _abrir(l),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 7),
              child: Row(children: [
                Portada(url: l.miniatura, lado: 52, radio: 8),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(l.nombre, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(l.total == 1 ? '1 canción' : '${l.total} canciones', style: estiloSecundario),
                  ]),
                ),
                if (widget.propio && !l.enPerfil)
                  Text(l.publica ? 'Oculta en tu perfil' : 'Privada', style: estiloSecundario),
              ]),
            ),
          ),
      ]),
    );
  }
}
