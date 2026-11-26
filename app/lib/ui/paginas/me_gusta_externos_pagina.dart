import 'dart:io' show File;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show Uint8List, kIsWeb, visibleForTesting;
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../nucleo/archivo_me_gusta.dart';
import '../../nucleo/cuentas_vinculadas.dart';
import '../../nucleo/importacion.dart';
import '../../nucleo/importar.dart';
import '../../nucleo/servicios_externos.dart';
import '../servicios.dart';
import '../tema.dart';
import 'importar_pagina.dart';

/// «Vincular cuentas»: tus me gusta de Spotify, YouTube Music y SoundCloud en tus Me gusta de
/// Caudal (aquí, en la PC y en la web), sin repetir. Con la cuenta vinculada se mantienen al
/// día solos; con el archivo que da cada servicio no hace falta vincular nada.
class MeGustaExternosPagina extends StatefulWidget {
  const MeGustaExternosPagina({super.key});

  /// Elegir un archivo: (nombre, contenido) o null si se cancela. Cambiable en las pruebas.
  @visibleForTesting
  static Future<(String, Uint8List)?> Function() elegirArchivo = _elegir;

  static Future<(String, Uint8List)?> _elegir() async {
    final r = await FilePicker.pickFiles(
        type: FileType.custom, allowedExtensions: ArchivoMeGusta.extensiones, withData: kIsWeb);
    final f = r?.files.firstOrNull;
    if (f == null) return null;
    if (f.size > ArchivoMeGusta.maxArchivo) return (f.name, Uint8List(ArchivoMeGusta.maxArchivo + 1));
    final b = f.bytes ?? (f.path == null ? null : await File(f.path!).readAsBytes());
    return b == null ? null : (f.name, b);
  }

  @override
  State<MeGustaExternosPagina> createState() => _MeGustaExternosPaginaState();
}

class _MeGustaExternosPaginaState extends State<MeGustaExternosPagina> {
  ConfigServicios? _conf;
  final Map<ServicioMusica, bool> _vinculada = {};
  final Map<ServicioMusica, bool> _alDia = {};
  final Map<ServicioMusica, DateTime?> _ultima = {};
  bool _ocupado = false;
  String? _mensaje;
  bool _mensajeEsError = false;
  final _soundcloud = TextEditingController();
  List<Map<String, dynamic>> _fuentes = const [];

  @override
  void initState() {
    super.initState();
    CuentaExterna.cambios.addListener(_recargar);
    TrabajoImportacion.i.addListener(_cambio);
    _recargar();
  }

  @override
  void dispose() {
    CuentaExterna.cambios.removeListener(_recargar);
    TrabajoImportacion.i.removeListener(_cambio);
    _soundcloud.dispose();
    super.dispose();
  }

  void _cambio() {
    if (mounted) setState(() {});
  }

  Future<void> _recargar() async {
    final conf = await ServiciosExternos.config(forzar: _conf == null);
    for (final s in ServicioMusica.values) {
      _vinculada[s] = await CuentaExterna(s).vinculada();
      _alDia[s] = await CuentasVinculadas.alDia(s);
      _ultima[s] = await CuentasVinculadas.ultima(s);
    }
    if (!mounted) return;
    final f = await TrabajoImportacion.fuentes(Caudal.leer(context).coleccion);
    if (!mounted) return;
    setState(() {
      _conf = conf;
      _fuentes = [for (final x in f) if ('${x['enlace'] ?? ''}'.startsWith('http')) x];
    });
  }

  void _decir(String t, {bool error = false}) {
    if (!mounted) return;
    setState(() {
      _mensaje = t;
      _mensajeEsError = error;
    });
  }

  void _avisarAlTerminar(Servicios s) {
    final t = TrabajoImportacion.i;
    void oir() {
      if (t.enMarcha) return;
      t.removeListener(oir);
      if (t.terminado) s.avisar(t.resumen());
    }

    t.addListener(oir);
  }

  /// Hace [trabajo] enseñando los fallos en la propia pantalla.
  Future<void> _hacer(Future<void> Function() trabajo) async {
    if (TrabajoImportacion.i.enMarcha) {
      return _decir('Ya se están pasando canciones. Espera a que termine.', error: true);
    }
    setState(() => _ocupado = true);
    try {
      await trabajo();
    } on ErrorImportar catch (e) {
      _decir(e.mensaje, error: true);
    } on ErrorServicio catch (e) {
      _decir(e.mensaje, error: true);
    } catch (_) {
      _decir('No se pudo. Revisa tu internet y vuelve a probar.', error: true);
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  /// La búsqueda sigue en segundo plano; la página de traer listas enseña el avance.
  Future<void> _verAvance() =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ImportarPagina(aMeGusta: true)));

  Future<void> _pasar(Future<ListaExterna?> Function() leer, String enlace) => _hacer(() async {
        final s = Caudal.leer(context);
        final t = TrabajoImportacion.i;
        _decir('Leyendo tus canciones…');
        final l = await leer();
        if (l == null) return _decir('');
        t.olvidarTerminado();
        await t.empezar(s.coleccion, l, meGusta: true, enlace: enlace);
        _avisarAlTerminar(s);
        if (!mounted) return;
        _decir('');
        _verAvance();
      });

  Future<void> _archivo() => _pasar(() async {
        final a = await MeGustaExternosPagina.elegirArchivo();
        return a == null ? null : ArchivoMeGusta.leer(a.$1, a.$2);
      }, 'archivo');

  Future<void> _pegar() async {
    final texto = await showDialog<String>(context: context, builder: (_) => const _PegarTexto());
    if (texto == null || texto.trim().isEmpty || !mounted) return;
    await _pasar(() async => Importar.deLineas(texto.split('\n'), titulo: 'Canciones pegadas', plataforma: 'un texto'), 'texto');
  }

  Future<void> _vincular(ServicioMusica s) => _hacer(() async {
        final url = await CuentaExterna(s).empezar();
        final abierto = await launchUrl(url,
            mode: kIsWeb ? LaunchMode.platformDefault : LaunchMode.externalApplication,
            webOnlyWindowName: '_self');
        _decir(abierto
            ? 'Entra en ${s.nombre} y acepta: al volver, tu cuenta quedará vinculada.'
            : 'No se pudo abrir el navegador para entrar en ${s.nombre}.', error: !abierto);
      });

  Future<void> _sincronizar(ServicioMusica s) => _hacer(() async {
        final sv = Caudal.leer(context);
        _decir('Leyendo tus me gusta de ${s.nombre}…');
        final n = await CuentasVinculadas.sincronizar(sv.coleccion, s);
        await _recargar();
        if (n == 0) return _decir('Ya está todo: no hay canciones nuevas en ${s.nombre}.');
        _avisarAlTerminar(sv);
        if (!mounted) return;
        _decir('');
        _verAvance();
      });

  Future<void> _desvincular(ServicioMusica s) async {
    final si = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('¿Desvincular ${s.nombre}?'),
        content: const Text('Las canciones que ya están en tus Me gusta se quedan. Solo dejarán de llegar las nuevas.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Desvincular')),
        ],
      ),
    );
    if (si != true) return;
    await CuentaExterna(s).desvincular();
    _decir('${s.nombre} ya no está vinculado en este dispositivo.');
  }

  static String _hace(DateTime? d) {
    if (d == null) return 'aún sin sincronizar';
    final m = DateTime.now().difference(d).inMinutes;
    if (m < 2) return 'al día, ahora mismo';
    if (m < 60) return 'al día, hace $m min';
    if (m < 60 * 24) return 'al día, hace ${m ~/ 60} h';
    final dias = m ~/ (60 * 24);
    return 'al día, hace $dias ${dias == 1 ? 'día' : 'días'}';
  }

  Widget _cuenta(ServicioMusica s, bool bloqueado) {
    final conf = _conf!;
    final color = Color(s.color);
    final vinculada = _vinculada[s] == true;
    final activa = conf.clientId(s).isNotEmpty;
    return _Tarjeta(
      servicio: s,
      estado: vinculada ? 'Vinculada · ${_hace(_ultima[s])}' : null,
      children: [
        if (vinculada) ...[
          Material(
            type: MaterialType.transparency,
            child: SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              dense: true,
              value: _alDia[s] ?? true,
              title: const Text('Mantener al día', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Al abrir Caudal entran solos los nuevos.', style: estiloDetalle),
              onChanged: (v) async {
                await CuentasVinculadas.ponerAlDia(s, v);
                if (mounted) setState(() => _alDia[s] = v);
              },
            ),
          ),
          const SizedBox(height: Esp.xs),
          Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
            FilledButton.icon(
              onPressed: bloqueado ? null : () => _sincronizar(s),
              style: FilledButton.styleFrom(backgroundColor: color, foregroundColor: Colors.white),
              icon: const Icon(Icons.sync_rounded),
              label: const Text('Sincronizar ahora', style: TextStyle(fontWeight: FontWeight.w800)),
            ),
            TextButton(onPressed: bloqueado ? null : () => _desvincular(s), child: const Text('Desvincular')),
          ]),
        ] else if (activa) ...[
          Text(
              s == ServicioMusica.spotify
                  ? 'Tus «Canciones que te gustan», enteras y al día. Caudal solo puede leerlas.'
                  : s == ServicioMusica.youtube
                      ? 'La música a la que diste me gusta en YouTube o YouTube Music (con o sin Premium). Caudal solo puede leerla.'
                      : 'Tus me gusta, enteros y al día. Caudal solo puede leerlos.',
              style: estiloSecundario),
          const SizedBox(height: Esp.m),
          FilledButton.icon(
            onPressed: bloqueado ? null : () => _vincular(s),
            style: FilledButton.styleFrom(backgroundColor: color, foregroundColor: Colors.white),
            icon: const Icon(Icons.link_rounded),
            label: Text('Vincular ${s.nombre}', style: const TextStyle(fontWeight: FontWeight.w800)),
          ),
        ],
        if (!vinculada) ..._sinVincular(s, activa, bloqueado),
      ],
    );
  }

  /// Lo que se puede hacer sin vincular la cuenta.
  List<Widget> _sinVincular(ServicioMusica s, bool activa, bool bloqueado) {
    final antes = activa ? const [SizedBox(height: Esp.m), Text('O sin vincular nada:', style: estiloDetalle), SizedBox(height: Esp.xs)] : const <Widget>[];
    return [
      ...antes,
      ...switch (s) {
        ServicioMusica.spotify => [
            const _Paso(1, 'Entra en tu privacidad de Spotify y pide «Datos de la cuenta».'),
            const _Paso(2, 'Spotify te manda un correo con un .zip (suele tardar unos días).'),
            const _Paso(3, 'Elígelo aquí: entran todas tus canciones que te gustan.'),
            _Acciones(alPedir: () => _abrir('https://www.spotify.com/account/privacy/'),
                textoPedir: 'Pedirlo a Spotify', alElegir: bloqueado ? null : _archivo),
          ],
        ServicioMusica.youtube => [
            const _Paso(1, 'En Google Takeout marca solo «YouTube y YouTube Music» y, en sus datos, «listas de reproducción».'),
            const _Paso(2, 'Google te manda un enlace con un .zip (suele tardar unos minutos).'),
            const _Paso(3, 'Elígelo aquí: entra tu música con me gusta.'),
            _Acciones(alPedir: () => _abrir('https://takeout.google.com/settings/takeout/custom/youtube'),
                textoPedir: 'Abrir Google Takeout', alElegir: bloqueado ? null : _archivo),
          ],
        ServicioMusica.soundcloud => [
            if (_conf!.soundcloud) ...[
              const Text('Pega el enlace de un perfil: se traen sus me gusta públicos.', style: estiloSecundario),
              const SizedBox(height: Esp.m),
              TextField(
                controller: _soundcloud,
                enabled: !bloqueado,
                keyboardType: TextInputType.url,
                decoration: InputDecoration(
                  hintText: 'https://soundcloud.com/tu-perfil',
                  filled: true,
                  fillColor: C.superficie2,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: Esp.s),
              OutlinedButton.icon(
                onPressed: bloqueado ? null : _perfilSoundcloud,
                icon: const Icon(Icons.favorite_rounded),
                label: const Text('Traer sus me gusta'),
              ),
            ] else ...[
              const _Paso(1, 'Saca la lista de tus me gusta a un .csv con una app de pasar listas (Soundiiz o TuneMyMusic), o copia sus nombres.'),
              const _Paso(2, 'Elige aquí el archivo, o pega los nombres: «Artista - Título», uno por línea.'),
              Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
                OutlinedButton.icon(onPressed: bloqueado ? null : _archivo,
                    icon: const Icon(Icons.upload_file_rounded), label: const Text('Elegir archivo')),
                TextButton.icon(onPressed: bloqueado ? null : _pegar,
                    icon: const Icon(Icons.notes_rounded), label: const Text('Pegar nombres')),
              ]),
            ],
          ],
      },
    ];
  }

  Future<void> _abrir(String url) async {
    if (!await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication)) _decir('No se pudo abrir $url', error: true);
  }

  void _perfilSoundcloud() {
    final e = Importar.enlaceDe(_soundcloud.text);
    if (Importar.plataforma(e) != 'soundcloud') return _decir('Ese enlace no es de SoundCloud.', error: true);
    final (tipo, ruta) = Importar.tipoSoundcloud(e);
    final enlace = tipo == 'perfil' ? 'https://soundcloud.com/$ruta/likes' : e;
    _pasar(() => Importar.leer(enlace), enlace);
  }

  @override
  Widget build(BuildContext context) {
    final enMarcha = TrabajoImportacion.i.enMarcha;
    final bloqueado = _ocupado || enMarcha;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: C.fondo,
        surfaceTintColor: Colors.transparent,
        title: const Text('Vincular cuentas', style: estiloTituloBarra),
      ),
      body: ListView(padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, 110), children: [
        const Text(
          'Tus me gusta de otras apps, en tus Me gusta de Caudal. Cada canción se busca en YouTube Music; '
          'las que ya tenías no se repiten y nada se quita.',
          style: TextStyle(color: C.texto2, height: 1.4),
        ),
        if (_mensaje != null && _mensaje!.isNotEmpty) ...[
          const SizedBox(height: Esp.l),
          Semantics(liveRegion: true,
              child: Text(_mensaje!, style: TextStyle(color: _mensajeEsError ? C.error : C.texto, height: 1.35))),
        ],
        if (enMarcha) ...[
          const SizedBox(height: Esp.l),
          OutlinedButton(
            onPressed: _verAvance,
            child: Text('Ver el avance (${textoAvance(TrabajoImportacion.i.hechas, TrabajoImportacion.i.total)})'),
          ),
        ],
        const SizedBox(height: Esp.xl),
        if (_conf == null)
          const Center(child: Padding(padding: EdgeInsets.all(Esp.xl), child: CircularProgressIndicator()))
        else ...[
          for (final s in ServicioMusica.values) _cuenta(s, bloqueado),
          _Tarjeta(titulo: 'Otro archivo o una lista de nombres', icono: Icons.upload_file_rounded, children: [
            const Text('Un .csv de Exportify, TuneMyMusic o Soundiiz, o un .txt con «Artista - Título» en cada línea.',
                style: estiloSecundario),
            const SizedBox(height: Esp.m),
            Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
              OutlinedButton.icon(onPressed: bloqueado ? null : _archivo,
                  icon: const Icon(Icons.upload_file_rounded), label: const Text('Elegir archivo')),
              TextButton.icon(onPressed: bloqueado ? null : _pegar,
                  icon: const Icon(Icons.notes_rounded), label: const Text('Pegar nombres')),
            ]),
          ]),
          if (_fuentes.isNotEmpty) ...[
            const SizedBox(height: Esp.s),
            const Text('Listas que ya trajiste', style: estiloTituloSeccion),
            const SizedBox(height: Esp.s),
            for (final f in _fuentes.take(6))
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text('${f['titulo'] ?? f['enlace'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
                subtitle: Text('${f['servicio'] ?? ''} · ${miles((f['anadidas'] as num?)?.toInt() ?? 0)} añadidas',
                    style: estiloDetalle),
                trailing: TextButton(
                  onPressed: bloqueado ? null : () => _pasar(() => Importar.leer('${f['enlace']}'), '${f['enlace']}'),
                  child: const Text('Traer lo nuevo'),
                ),
              ),
          ],
        ],
      ]),
    );
  }
}

class _Tarjeta extends StatelessWidget {
  const _Tarjeta({this.servicio, this.titulo, this.icono, this.estado, required this.children});
  final ServicioMusica? servicio;
  final String? titulo;
  final IconData? icono;
  final String? estado;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final color = servicio == null ? C.acento : Color(servicio!.color);
    return Container(
      margin: const EdgeInsets.only(bottom: Esp.l),
      padding: const EdgeInsets.all(Esp.l),
      decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(18)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: color.withValues(alpha: 0.16),
            child: Icon(icono ?? (servicio == ServicioMusica.soundcloud ? Icons.cloud_rounded
                : servicio == ServicioMusica.youtube ? Icons.play_circle_fill_rounded : Icons.graphic_eq_rounded),
                color: color, size: 20),
          ),
          const SizedBox(width: Esp.m),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(titulo ?? servicio!.nombre, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
              if (estado != null) Text(estado!, style: const TextStyle(color: C.exito, fontSize: 12.5, height: 1.4)),
            ]),
          ),
        ]),
        const SizedBox(height: Esp.m),
        ...children,
      ]),
    );
  }
}

class _Paso extends StatelessWidget {
  const _Paso(this.n, this.texto);
  final int n;
  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: Esp.s),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 22, child: Text('$n.', style: TextStyle(color: C.acento, fontWeight: FontWeight.w800, height: 1.35))),
          Expanded(child: Text(texto, style: estiloSecundario.copyWith(height: 1.35))),
        ]),
      );
}

class _Acciones extends StatelessWidget {
  const _Acciones({required this.alPedir, required this.textoPedir, required this.alElegir});
  final VoidCallback alPedir;
  final String textoPedir;
  final VoidCallback? alElegir;

  @override
  Widget build(BuildContext context) => Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
        OutlinedButton.icon(onPressed: alPedir, icon: const Icon(Icons.open_in_new_rounded, size: 18), label: Text(textoPedir)),
        FilledButton.tonalIcon(onPressed: alElegir, icon: const Icon(Icons.upload_file_rounded), label: const Text('Elegir el .zip')),
      ]);
}

class _PegarTexto extends StatefulWidget {
  const _PegarTexto();

  @override
  State<_PegarTexto> createState() => _PegarTextoState();
}

class _PegarTextoState extends State<_PegarTexto> {
  final _c = TextEditingController();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Pegar nombres de canciones'),
        content: TextField(
          controller: _c,
          autofocus: true,
          minLines: 6,
          maxLines: 12,
          decoration: const InputDecoration(hintText: 'Bad Bunny - Monaco\nKarol G - Tusa\n…'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(context, _c.text), child: const Text('Pasar a Me gusta')),
        ],
      );
}
