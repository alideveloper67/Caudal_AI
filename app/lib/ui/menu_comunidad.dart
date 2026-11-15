import 'package:flutter/material.dart';

import 'paginas/amigos_pagina.dart';
import 'paginas/directorio_pagina.dart';
import 'paginas/mezclador_pagina.dart';
import 'paginas/perfil_comun.dart';
import 'paginas/perfil_pagina.dart';
import 'paginas/revision_pagina.dart';
import 'paginas/subir_musica_comunidad.dart';
import 'paginas/subir_musica_pagina.dart';
import 'tema.dart';

/// Un solo sitio desde donde se llega a todo lo de la comunidad: tu perfil, la gente,
/// los amigos, la música que sube la gente y el mezclador.
class MenuComunidad {
  MenuComunidad._();

  static final _opciones = <_Opcion>[
    _Opcion(Icons.account_circle_rounded, 'Mi perfil', 'Tu foto, tu descripción y tu canción favorita',
        (_) => const PerfilPagina()),
    _Opcion(Icons.explore_rounded, 'Perfiles de Caudal', 'Descubre gente, da me gusta y agrégala',
        (_) => const DirectorioPagina()),
    _Opcion(Icons.group_add_rounded, 'Amigos y solicitudes', 'Quién quiere ser tu amigo y a quién escribirle',
        (_) => const AmigosPagina()),
    _Opcion(Icons.library_music_rounded, 'Música de la comunidad', 'Lo que sube la gente, con su carátula',
        (_) => const ComunidadPagina()),
    _Opcion(Icons.cloud_upload_rounded, 'Subir mi música', 'Comparte tus canciones con la comunidad',
        (_) => const SubirMusicaPagina()),
    _Opcion(Icons.album_rounded, 'Mezclador', 'Un DJ automático y tu propia mesa',
        (_) => const MezcladorPagina()),
  ];

  /// Abre una de las pantallas por su posición (0 = Mi perfil ... 5 = Mezclador).
  static Widget pantalla(int i, BuildContext context) => _opciones[i].crear(context);

  static Future<void> abrir(BuildContext context) {
    final navegador = Navigator.of(context);
    return showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      useSafeArea: true,
      showDragHandle: true,
      backgroundColor: C.panel,
      builder: (hoja) => SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(6, 0, 6, 4),
              child: Text('Comunidad', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
            ),
            const Padding(
              padding: EdgeInsets.fromLTRB(6, 0, 6, 12),
              child: Text('Tu perfil, la gente de Caudal y su música.', style: TextStyle(fontSize: 13.5, color: C.texto2)),
            ),
            for (final o in _opciones)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Material(
                  color: C.superficie,
                  borderRadius: BorderRadius.circular(16),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: () {
                      Navigator.of(hoja).pop();
                      navegador.push(MaterialPageRoute(builder: o.crear));
                    },
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      child: Row(children: [
                        Container(
                          width: 42, height: 42,
                          decoration: BoxDecoration(color: C.acento.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(12)),
                          child: Icon(o.icono, color: C.acento),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(o.titulo, style: const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800)),
                            const SizedBox(height: 2),
                            Text(o.detalle, style: const TextStyle(fontSize: 12.5, color: C.texto2)),
                          ]),
                        ),
                        const Icon(Icons.chevron_right_rounded, color: C.texto3),
                      ]),
                    ),
                  ),
                ),
              ),
            _EntradaRevision(contexto: context, hoja: hoja, navegador: navegador),
          ]),
        ),
      ),
    );
  }
}

/// «Revisión de música»: solo aparece si la cuenta es moderadora, con el
/// número de canciones esperando.
class _EntradaRevision extends StatefulWidget {
  const _EntradaRevision({required this.contexto, required this.hoja, required this.navegador});
  final BuildContext contexto;
  final BuildContext hoja;
  final NavigatorState navegador;

  @override
  State<_EntradaRevision> createState() => _EntradaRevisionState();
}

class _EntradaRevisionState extends State<_EntradaRevision> {
  bool _moderador = false;
  int _pendientes = 0;

  @override
  void initState() {
    super.initState();
    _mirar();
  }

  Future<void> _mirar() async {
    try {
      final social = socialDe(widget.contexto);
      if (social == null || !await social.soyModerador()) return;
      final n = await social.revisionContar();
      if (mounted) {
        setState(() {
          _moderador = true;
          _pendientes = n;
        });
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    if (!_moderador) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Material(
        color: C.superficie,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () {
            Navigator.of(widget.hoja).pop();
            widget.navegador.push(MaterialPageRoute<void>(builder: (_) => const RevisionPagina()));
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Row(children: [
              Container(
                width: 42, height: 42,
                decoration: BoxDecoration(color: const Color(0xFFF5C451).withValues(alpha: 0.18), borderRadius: BorderRadius.circular(12)),
                child: const Icon(Icons.fact_check_rounded, color: Color(0xFFF5C451)),
              ),
              const SizedBox(width: 14),
              const Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Revisión de música', style: TextStyle(fontSize: 15.5, fontWeight: FontWeight.w800)),
                  SizedBox(height: 2),
                  Text('Aprueba o rechaza lo que suben', style: TextStyle(fontSize: 12.5, color: C.texto2)),
                ]),
              ),
              if (_pendientes > 0)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                  decoration: BoxDecoration(color: C.acento, borderRadius: BorderRadius.circular(10)),
                  child: Text('$_pendientes',
                      semanticsLabel: '$_pendientes por revisar',
                      style: TextStyle(color: C.acentoTexto, fontSize: 12, fontWeight: FontWeight.w900)),
                )
              else
                const Icon(Icons.chevron_right_rounded, color: C.texto3),
            ]),
          ),
        ),
      ),
    );
  }
}

class _Opcion {
  const _Opcion(this.icono, this.titulo, this.detalle, this.crear);
  final IconData icono;
  final String titulo;
  final String detalle;
  final WidgetBuilder crear;
}
