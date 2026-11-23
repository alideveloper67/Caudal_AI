import 'package:file_picker/file_picker.dart' show PlatformFile;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/importar_archivos.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'importar_pagina.dart';

/// El botón "Traer" de Tu biblioteca: una lista de otra app o canciones que
/// ya tienes en el teléfono.
Future<void> hojaTraer(BuildContext context) async {
  final eleccion = await showModalBottomSheet<String>(
    context: context,
    useRootNavigator: true,
    builder: (ctx) => SafeArea(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 4, 20, 8),
          child: Align(alignment: Alignment.centerLeft, child: Text('Traer música', style: estiloTituloSeccion)),
        ),
        ListTile(
          leading: CircleAvatar(backgroundColor: C.superficie3, child: Icon(Icons.playlist_add_rounded, color: C.acento)),
          title: const Text('Una lista de otra app', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Spotify, Apple Music o YouTube Music, con su enlace', style: estiloSecundario),
          onTap: () => Navigator.pop(ctx, 'lista'),
        ),
        ListTile(
          leading: CircleAvatar(backgroundColor: C.superficie3, child: Icon(Icons.library_music_rounded, color: C.acento)),
          title: Text(kIsWeb ? 'Canciones de este equipo' : 'Canciones de tu teléfono', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Las que ya tienes guardadas (MP3, M4A, FLAC...)', style: estiloSecundario),
          onTap: () => Navigator.pop(ctx, 'archivos'),
        ),
        const SizedBox(height: 8),
      ]),
    ),
  );
  if (!context.mounted || eleccion == null) return;
  if (eleccion == 'lista') {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ImportarPagina()));
    return;
  }
  await importarDelTelefono(context);
}

/// Elegir archivos, copiarlos y preguntar dónde ponerlos.
Future<void> importarDelTelefono(BuildContext context) async {
  final s = Caudal.leer(context);
  List<Object> rutas;
  try {
    rutas = kIsWeb ? await ImportarArchivos.elegirWeb() : await ImportarArchivos.elegir();
  } catch (_) {
    s.avisar('No se pudo abrir el selector de archivos.');
    return;
  }
  if (rutas.isEmpty || !context.mounted) return;

  final avance = ValueNotifier<(int, int)>((0, rutas.length));
  showDialog<void>(
    context: context,
    useRootNavigator: true,
    barrierDismissible: false,
    builder: (ctx) => PopScope(
      canPop: false,
      child: AlertDialog(
        title: const Text('Importando'),
        content: ValueListenableBuilder<(int, int)>(
          valueListenable: avance,
          builder: (_, v, _) => Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${v.$1} de ${v.$2} canciones'),
            const SizedBox(height: 12),
            LinearProgressIndicator(value: v.$2 == 0 ? null : v.$1 / v.$2, color: C.acento),
          ]),
        ),
      ),
    ),
  );
  List<Json> pistas;
  var aviso = '';
  try {
    if (kIsWeb) {
      final r = await ImportarArchivos.importarWeb(s.coleccion, rutas.cast<PlatformFile>(),
          alAvanzar: (h, t) => avance.value = (h, t));
      pistas = r.pistas;
      if (r.sinEspacio) {
        aviso = 'El navegador se quedó sin espacio: no entraron todas.';
      } else if (r.sinSoporte > 0) {
        aviso = r.sinSoporte == 1
            ? 'Una canción no entró: el navegador no reproduce ese formato.'
            : '${r.sinSoporte} canciones no entraron: el navegador no reproduce ese formato.';
      }
    } else {
      pistas = await ImportarArchivos.importar(s.coleccion, rutas.cast<String>(),
          alAvanzar: (h, t) => avance.value = (h, t));
    }
  } catch (_) {
    pistas = const [];
    aviso = 'El navegador no dejó guardar las canciones (¿ventana privada?).';
  }
  if (!context.mounted) return;
  Navigator.of(context, rootNavigator: true).pop();
  if (pistas.isEmpty) {
    s.avisar(aviso.isNotEmpty ? aviso : 'No se pudo importar ninguna de esas canciones.');
    return;
  }
  if (aviso.isNotEmpty) s.avisar(aviso);

  final donde = await showModalBottomSheet<String>(
    context: context,
    useRootNavigator: true,
    builder: (ctx) => SafeArea(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 4),
          child: Align(alignment: Alignment.centerLeft,
              child: Text('${pistas.length} ${pistas.length == 1 ? 'canción importada' : 'canciones importadas'}',
                  style: estiloTituloSeccion)),
        ),
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
          child: Align(alignment: Alignment.centerLeft,
              child: Text(kIsWeb ? 'Ya están en «Tu música». ¿Dónde más las pones?'
                  : 'Ya están en «En tu teléfono». ¿Dónde más las pones?', style: estiloSecundario)),
        ),
        ListTile(
          leading: CircleAvatar(backgroundColor: C.acento, child: Icon(Icons.add_rounded, color: C.acentoTexto)),
          title: const Text('En una lista nueva solo con ellas', style: TextStyle(fontWeight: FontWeight.w700)),
          onTap: () => Navigator.pop(ctx, 'nueva'),
        ),
        ListTile(
          leading: CircleAvatar(backgroundColor: C.superficie3, child: Icon(Icons.queue_music_rounded, color: C.texto)),
          title: const Text('En una de tus listas', style: TextStyle(fontWeight: FontWeight.w700)),
          onTap: () => Navigator.pop(ctx, 'existente'),
        ),
        ListTile(
          leading: const Icon(Icons.check_rounded, color: C.texto2),
          title: const Text('Así está bien'),
          onTap: () => Navigator.pop(ctx),
        ),
        const SizedBox(height: 8),
      ]),
    ),
  );
  if (!context.mounted || donde == null) return;
  if (donde == 'existente') {
    await s.anadirALista(context, pistas);
    return;
  }
  final propuesta = await s.coleccion.nombreLibre('Importadas');
  if (!context.mounted) return;
  final nombre = await pedirTexto(context, 'Nombre de la lista', propuesta.replaceAll(' n.º 1', ''));
  if (nombre == null || !context.mounted) return;
  try {
    final id = await s.coleccion.crearLista(nombre, descripcion: kIsWeb ? 'Canciones de este equipo' : 'Canciones de tu teléfono');
    await s.coleccion.agregarALista(id, pistas);
    if (context.mounted) s.abrirElemento(context, {'tipo': 'mi_lista', 'id': id, 'titulo': nombre});
  } on FormatException catch (e) {
    s.avisar(e.message);
  }
}
