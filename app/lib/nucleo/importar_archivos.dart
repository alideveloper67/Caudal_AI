import 'dart:io';

import 'package:ffmpeg_kit_flutter_new/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new/ffprobe_kit.dart';
import 'package:file_picker/file_picker.dart';
import 'package:path/path.dart' as p;

import 'coleccion.dart';
import 'descargas.dart';

/// Traer a Caudal canciones que ya tienes en el teléfono (MP3, M4A, FLAC...).
///
/// Se copian a la carpeta de Caudal (así siguen sonando aunque la app que las
/// bajó las borre), se leen sus datos (título, artista, carátula) y quedan
/// en "En tu teléfono", listas para meterlas en una lista.
class ImportarArchivos {
  ImportarArchivos._();

  static const extensiones = ['mp3', 'm4a', 'aac', 'flac', 'wav', 'ogg', 'opus', 'webm', 'wma', 'alac', 'aiff'];

  /// Abre el selector del sistema. Devuelve las rutas elegidas (vacío si se cancela).
  static Future<List<String>> elegir() async {
    // en iPhone el modo "audio" abre la biblioteca de Apple Music (pide permiso
    // y no deja elegir archivos); con extensiones abre la app Archivos
    final r = Platform.isIOS
        ? await FilePicker.pickFiles(type: FileType.custom, allowedExtensions: extensiones, allowMultiple: true)
        : await FilePicker.pickFiles(type: FileType.audio, allowMultiple: true);
    return [for (final f in r?.files ?? const <PlatformFile>[]) if (f.path != null) f.path!];
  }

  /// Copia y registra cada archivo. [alAvanzar] recibe (hechas, total).
  static Future<List<Json>> importar(Coleccion c, List<String> rutas,
      {void Function(int, int)? alAvanzar}) async {
    final carpeta = await GestorDescargas.carpetaDeGuardado(true, false, subcarpeta: 'Importadas');
    final portadas = Directory(p.join(carpeta.path, '.portadas'));
    if (!await portadas.exists()) await portadas.create(recursive: true);
    final salida = <Json>[];
    for (final (i, ruta) in rutas.indexed) {
      try {
        final pista = await _una(c, File(ruta), carpeta, portadas);
        if (pista != null) salida.add(pista);
      } catch (_) {
        // un archivo roto no frena a los demas
      }
      alAvanzar?.call(i + 1, rutas.length);
    }
    return salida;
  }

  static Future<Json?> _una(Coleccion c, File origen, Directory carpeta, Directory portadas) async {
    if (!await origen.exists()) return null;
    final ext = p.extension(origen.path).replaceFirst('.', '').toLowerCase();
    final base = p.basenameWithoutExtension(origen.path);
    // mismo nombre ya importado: no se duplica
    var destino = File(p.join(carpeta.path, p.basename(origen.path)));
    final ya = await c.descargadas(soloAudio: true);
    final repetida = ya.where((x) => '${x['archivo']}' == destino.path).firstOrNull;
    if (repetida != null) return repetida;
    if (await destino.exists()) {
      destino = File(p.join(carpeta.path, '${base}_${DateTime.now().millisecondsSinceEpoch}.$ext'));
    }
    await origen.copy(destino.path);

    final datos = await leerDatos(destino.path);
    final porNombre = separarNombre(base);
    final titulo = datos.titulo.isNotEmpty ? datos.titulo : porNombre.$2;
    final artista = datos.artista.isNotEmpty ? datos.artista : porNombre.$1;

    // la caratula que lleva dentro, si la tiene
    var caratula = '';
    final jpg = p.join(portadas.path, '${p.basenameWithoutExtension(destino.path)}.jpg');
    try {
      final s = await FFmpegKit.executeWithArguments(['-y', '-i', destino.path, '-an', '-c:v', 'mjpeg',
        '-frames:v', '1', '-vf', 'scale=600:-2', jpg]);
      final rc = await s.getReturnCode();
      if (rc != null && rc.isValueSuccess() && await File(jpg).exists()) caratula = jpg;
    } catch (_) {}

    final id = await c.agregarDescarga(
      videoId: '', url: '', titulo: titulo, artista: artista, archivo: destino.path, esAudio: true,
      tamano: await destino.length(), duracion: datos.duracion, calidad: ext.toUpperCase(),
      caratula: caratula,
      datos: {'importada': true, 'album': {'nombre': datos.album}},
    );
    final filas = await c.db.query('descargas', where: 'id = ?', whereArgs: [id]);
    return filas.isEmpty ? null : Coleccion.pistaDeDescarga(filas.first);
  }

  /// Título, artista, álbum y duración que trae el archivo.
  static Future<({String titulo, String artista, String album, int duracion})> leerDatos(String ruta) async {
    var titulo = '', artista = '', album = '';
    var duracion = 0;
    try {
      final s = await FFprobeKit.getMediaInformation(ruta);
      final info = s.getMediaInformation();
      final tags = <String, String>{
        for (final e in (info?.getTags() ?? const {}).entries) '${e.key}'.toLowerCase(): '${e.value}'.trim(),
      };
      titulo = tags['title'] ?? '';
      artista = tags['artist'] ?? tags['album_artist'] ?? '';
      album = tags['album'] ?? '';
      duracion = (double.tryParse(info?.getDuration() ?? '') ?? 0).round();
    } catch (_) {}
    return (titulo: titulo, artista: artista, album: album, duracion: duracion);
  }

  /// "Artista - Título" (lo habitual en archivos bajados) → (artista, título).
  static (String, String) separarNombre(String nombre) {
    final limpio = nombre.replaceAll('_', ' ').replaceAll(RegExp(r'\s+'), ' ').trim();
    final m = RegExp(r'^(.+?)\s+[-–—]\s+(.+)$').firstMatch(limpio);
    if (m != null) return (m.group(1)!.trim(), m.group(2)!.trim());
    return ('', limpio);
  }
}
