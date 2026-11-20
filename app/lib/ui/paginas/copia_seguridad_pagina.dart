import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../nucleo/copia_seguridad.dart';
import '../../nucleo/estudio.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';

/// Ajustes → «Copia de seguridad»: guardar todo en un archivo .caudal y
/// traerlo de vuelta (aquí, en otro teléfono o en la PC). La lógica está en
/// nucleo/copia_seguridad.dart.
class CopiaSeguridadPagina extends StatefulWidget {
  const CopiaSeguridadPagina({super.key});

  @override
  State<CopiaSeguridadPagina> createState() => _CopiaSeguridadPaginaState();
}

class _CopiaSeguridadPaginaState extends State<CopiaSeguridadPagina> {
  bool _ocupado = false;
  String _haciendo = '';
  bool _automatica = false;
  DateTime? _ultima;

  @override
  void initState() {
    super.initState();
    _leerAutomatica();
  }

  Future<void> _leerAutomatica() async {
    final cuenta = Caudal.leer(context).cuenta.id;
    final a = await CopiaSeguridad.automaticaActiva(cuenta);
    final u = await CopiaSeguridad.ultimaAutomatica(cuenta);
    if (mounted) {
      setState(() {
        _automatica = a;
        _ultima = u;
      });
    }
  }

  void _ocupar(String que) => setState(() {
        _ocupado = que.isNotEmpty;
        _haciendo = que;
      });

  String _fecha(DateTime? f) {
    if (f == null) return 'todavía ninguna';
    String dos(int n) => n.toString().padLeft(2, '0');
    return '${dos(f.day)}/${dos(f.month)}/${f.year} ${dos(f.hour)}:${dos(f.minute)}';
  }

  // ------------------------------------------------------------ guardar

  Future<void> _guardar() async {
    final s = Caudal.leer(context);
    _ocupar('Preparando la copia…');
    Uint8List bytes;
    try {
      bytes = await CopiaSeguridad.crear(s.coleccion, ajustes: s.ajustes, cuenta: s.cuenta.id);
    } catch (_) {
      _ocupar('');
      s.avisar('No se pudo preparar la copia. Vuelve a intentarlo.');
      return;
    }
    _ocupar('');
    if (!mounted) return;
    final resumen = CopiaSeguridad.abrir(bytes).textoResumen();
    final nombre = CopiaSeguridad.nombreSugerido();
    final r = await showModalBottomSheet<String>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 4),
            child: Text('Tu copia está lista', style: estiloTituloSeccion),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
            child: Text(resumen, style: estiloSecundario),
          ),
          if (!kIsWeb)
            ListTile(
              leading: Icon(Icons.share_rounded, color: C.acento),
              title: const Text('Compartir'),
              subtitle: const Text('Envíatela por WhatsApp, correo o a tu PC', style: estiloSecundario),
              onTap: () => Navigator.pop(ctx, 'compartir'),
            ),
          ListTile(
            leading: Icon(Icons.save_alt_rounded, color: C.acento),
            title: const Text('Guardar en…'),
            subtitle: const Text('Elige una carpeta del teléfono', style: estiloSecundario),
            onTap: () => Navigator.pop(ctx, 'guardar'),
          ),
          const SizedBox(height: 8),
        ]),
      ),
    );
    if (r == null) return;
    try {
      if (r == 'compartir') {
        final dir = await getTemporaryDirectory();
        final f = File('${dir.path}/$nombre');
        await f.writeAsBytes(bytes, flush: true);
        await SharePlus.instance.share(ShareParams(
          files: [XFile(f.path, mimeType: 'application/zip')],
          text: 'Copia de seguridad de Caudal',
        ));
      } else {
        final ruta = await FilePicker.saveFile(
            dialogTitle: 'Guardar la copia de Caudal', fileName: nombre, bytes: bytes);
        if (ruta != null || kIsWeb) s.avisar('Copia guardada');
      }
    } catch (_) {
      s.avisar('No se pudo guardar ahí. Prueba con «Compartir» o con otra carpeta.');
    }
  }

  // ------------------------------------------------------------ restaurar

  Future<void> _elegir() async {
    final s = Caudal.leer(context);
    FilePickerResult? r;
    try {
      r = await FilePicker.pickFiles(type: FileType.any, withData: true);
    } catch (_) {
      s.avisar('No se pudo abrir el selector de archivos.');
      return;
    }
    final f = r?.files.firstOrNull;
    if (f == null) return;
    var bytes = f.bytes;
    if (bytes == null && f.path != null && !kIsWeb) bytes = await File(f.path!).readAsBytes();
    if (bytes == null) return;
    Copia copia;
    try {
      copia = CopiaSeguridad.abrir(bytes);
    } on ErrorCopia catch (e) {
      if (mounted) await _mensaje('No se puede abrir', e.mensaje);
      return;
    }
    if (!mounted) return;
    final eleccion = await showModalBottomSheet<(String, bool)>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (_) => _VistaPrevia(copia: copia),
    );
    if (eleccion == null || !mounted) return;
    final (modo, conAjustes) = eleccion;
    if (modo == 'reemplazar') {
      final conCuenta = s.cuenta.sesion != null;
      final ok = await confirmar(
          context,
          'Reemplazar todo',
          'Se borrarán tus me gusta, listas, historial de escuchas y guardados de este teléfono, y quedarán '
              'solo los de la copia.${conCuenta ? ' Como entras con tu cuenta, el cambio también llega a tus otros dispositivos.' : ''}'
              '\n\nTus canciones descargadas no se tocan.',
          si: 'Reemplazar todo');
      if (!ok) return;
    }
    await _restaurar(copia, modo, conAjustes);
  }

  Future<void> _restaurar(Copia copia, String modo, bool conAjustes) async {
    final s = Caudal.leer(context);
    _ocupar('Restaurando…');
    Map<String, int> cuenta;
    List<String> hecho;
    try {
      cuenta = await CopiaSeguridad.restaurarColeccion(s.coleccion, copia, modo: modo);
      hecho = await CopiaSeguridad.restaurarExtras(copia,
          modo: modo, ajustes: s.ajustes, cuenta: s.cuenta.id, conAjustes: conAjustes,
          conCuenta: s.cuenta.sesion != null);
      await _refrescarEstudio();
      s.sincronizador?.pronto();
    } catch (_) {
      _ocupar('');
      if (mounted) {
        await _mensaje('Copia de seguridad',
            'Algo salió mal y no se terminó de restaurar. Vuelve a intentarlo; si sigue pasando, prueba con otra copia.');
      }
      return;
    }
    _ocupar('');
    if (!mounted) return;
    const nombres = {
      'me_gusta': 'me gusta', 'listas': 'listas', 'canciones_en_listas': 'canciones en listas',
      'escuchas': 'escuchas', 'guardados': 'guardados', 'descargas': 'descargas registradas',
    };
    final partes = [
      for (final e in nombres.entries)
        if ((cuenta[e.key] ?? 0) > 0) '${cuenta[e.key]} ${e.value}'
    ];
    var texto = partes.isNotEmpty
        ? 'Entraron: ${partes.join(', ')}.'
        : (modo == 'juntar' ? 'No había nada nuevo: ya tenías todo lo de la copia.' : 'Listo.');
    if (hecho.contains('ajustes')) texto += '\n\nTus ajustes y el ecualizador ya están puestos.';
    await _mensaje('Copia restaurada', texto);
  }

  /// El modo estudio guarda sus notas en memoria: se vuelven a leer.
  Future<void> _refrescarEstudio() async {
    final e = Estudio.i;
    if (!e.cargado) return;
    final p = await SharedPreferences.getInstance();
    e.notas = NotasEstudio.desdeJson(p.getString('estudio.notas'));
    e.estadisticas = EstadisticasEstudio.desdeJson(p.getString('estudio.dias'));
  }

  Future<void> _mensaje(String titulo, String texto) => showDialog<void>(
        context: context,
        useRootNavigator: true,
        builder: (ctx) => AlertDialog(
          backgroundColor: C.superficie2,
          title: Text(titulo),
          content: Text(texto),
          actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Entendido'))],
        ),
      );

  // ------------------------------------------------------------ automática

  Future<void> _ponerAutomatica(bool si) async {
    final s = Caudal.leer(context);
    await CopiaSeguridad.ponerAutomatica(s.cuenta.id, si);
    setState(() => _automatica = si);
    if (si) {
      try {
        await CopiaSeguridad.automaticaSiToca(s.coleccion, ajustes: s.ajustes, cuenta: s.cuenta.id);
      } catch (_) {}
      await _leerAutomatica();
    }
  }

  Future<void> _compartirUltima() async {
    final s = Caudal.leer(context);
    try {
      final dir = await CopiaSeguridad.carpetaAutomaticas();
      final copias = [
        for (final f in dir.listSync())
          if (f is File && f.path.endsWith(CopiaSeguridad.extension)) f
      ]..sort((a, b) => b.path.compareTo(a.path));
      if (copias.isEmpty) return s.avisar('Aún no hay copias automáticas');
      await SharePlus.instance.share(ShareParams(
          files: [XFile(copias.first.path, mimeType: 'application/zip')], text: 'Copia de seguridad de Caudal'));
    } catch (_) {
      s.avisar('No se pudo compartir la copia.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Copia de seguridad')),
      body: ListView(padding: const EdgeInsets.only(bottom: 40), children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(Esp.lado, 8, Esp.lado, 8),
          child: Text(
              'Guarda en un archivo tus me gusta, listas (con sus portadas), historial, álbumes y artistas '
              'guardados, el registro de descargas, ajustes, ecualizador, mascota, artistas favoritos y las notas '
              'del modo estudio. Sirve para pasarlo todo a otro teléfono o a la PC, aunque no uses cuenta.\n\n'
              'No lleva tu sesión ni contraseñas, ni las canciones descargadas.',
              style: estiloSecundario),
        ),
        if (_ocupado)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 8),
            child: Row(children: [
              const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
              const SizedBox(width: 12),
              Text(_haciendo, style: estiloSecundario),
            ]),
          ),
        ListTile(
          leading: Icon(Icons.backup_rounded, color: C.acento),
          title: const Text('Guardar una copia'),
          subtitle: const Text('Crea un archivo .caudal para compartirlo o guardarlo donde quieras',
              style: estiloSecundario),
          onTap: _ocupado ? null : _guardar,
        ),
        ListTile(
          leading: Icon(Icons.restore_rounded, color: C.acento),
          title: const Text('Restaurar una copia'),
          subtitle: const Text('Antes de cambiar nada verás qué trae y podrás juntarla con lo tuyo o reemplazarlo todo',
              style: estiloSecundario),
          onTap: _ocupado ? null : _elegir,
        ),
        if (!kIsWeb) ...[
          SwitchListTile.adaptive(
            secondary: Icon(Icons.event_repeat_rounded, color: C.acento),
            title: const Text('Copia automática cada semana'),
            subtitle: Text(
                'Se guarda sola en el teléfono (se quedan las 3 más nuevas). Última: ${_fecha(_ultima)}. '
                'Si desinstalas Caudal se borran: compártela de vez en cuando.',
                style: estiloSecundario),
            value: _automatica,
            onChanged: _ocupado ? null : _ponerAutomatica,
          ),
          if (_ultima != null)
            ListTile(
              leading: const Icon(Icons.share_rounded, color: C.texto2),
              title: const Text('Compartir la última copia automática'),
              onTap: _compartirUltima,
            ),
        ],
      ]),
    );
  }
}

/// Qué trae la copia y cómo traerla.
class _VistaPrevia extends StatefulWidget {
  const _VistaPrevia({required this.copia});
  final Copia copia;

  @override
  State<_VistaPrevia> createState() => _VistaPreviaState();
}

class _VistaPreviaState extends State<_VistaPrevia> {
  String _modo = 'juntar';
  bool _conAjustes = true;

  @override
  Widget build(BuildContext context) {
    final c = widget.copia;
    final lineas = c.textoResumen().split(' · ');
    Widget opcion(String valor, String titulo, String ayuda) => ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(_modo == valor ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded,
              color: _modo == valor ? C.acento : C.texto3),
          title: Text(titulo),
          subtitle: Text(ayuda, style: estiloSecundario),
          onTap: () => setState(() => _modo = valor),
        );
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Esto trae la copia', style: estiloTituloSeccion),
          const SizedBox(height: 2),
          Text(c.descripcion(), style: estiloDetalle),
          const SizedBox(height: 10),
          for (final l in lineas)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('•  ', style: TextStyle(color: C.acento, fontWeight: FontWeight.w800)),
                Expanded(child: Text(l)),
              ]),
            ),
          const SizedBox(height: 10),
          opcion('juntar', 'Juntar con lo que tengo', 'Añade lo que falta y no repite nada de lo que ya tienes.'),
          opcion('reemplazar', 'Reemplazar todo',
              'Borra tus me gusta, listas, historial y guardados de ahora y deja solo los de la copia. '
                  'Tus canciones descargadas no se borran.'),
          SwitchListTile.adaptive(
            contentPadding: EdgeInsets.zero,
            title: const Text('Usar también sus ajustes'),
            subtitle: Text(
                c.origen == 'escritorio'
                    ? 'Aspecto, ecualizador y sonido. De la PC se usan solo los que también existen aquí.'
                    : 'Aspecto, ecualizador, sonido y mascota.',
                style: estiloSecundario),
            value: _conAjustes,
            onChanged: (v) => setState(() => _conAjustes = v),
          ),
          const SizedBox(height: 8),
          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: () => Navigator.pop(context, (_modo, _conAjustes)),
              child: const Text('Restaurar'),
            ),
          ]),
        ]),
      ),
    );
  }
}
