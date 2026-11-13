import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../nucleo/ajustes.dart';
import '../../nucleo/catalogo.dart';
import '../../nucleo/cuentas.dart';
import '../../nucleo/formato.dart';
import '../../nucleo/version.dart';
import '../comunes.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';
import 'sonido.dart';

class AjustesPagina extends StatefulWidget {
  const AjustesPagina({super.key});

  @override
  State<AjustesPagina> createState() => _AjustesPaginaState();
}

class _AjustesPaginaState extends State<AjustesPagina> {
  bool _buscandoVersion = false;

  Future<void> _elegir(String clave, String titulo, List<(String, String)> opciones) async {
    final s = Caudal.leer(context);
    final actual = '${s.ajustes.texto(clave)}';
    final r = await showModalBottomSheet<String>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Padding(padding: const EdgeInsets.fromLTRB(20, 0, 20, 6), child: Text(titulo, style: estiloTituloSeccion)),
        for (final (valor, texto) in opciones)
          ListTile(
            title: Text(texto),
            trailing: valor == actual ? const Icon(Icons.check_rounded, color: C.acento) : null,
            onTap: () => Navigator.pop(ctx, valor),
          ),
        const SizedBox(height: 8),
      ])),
    );
    if (r == null || r == actual) return;
    await s.ajustes.poner(clave, r);
    if (clave == 'region') Catalogo.fijarRegion(r);
    s.sincronizador?.pronto();
    if (mounted) setState(() {});
  }

  Future<void> _sino(String clave, bool v) async {
    final s = Caudal.leer(context);
    await s.ajustes.poner(clave, v);
    s.sincronizador?.pronto();
    if (mounted) setState(() {});
  }

  Future<void> _cambiarContrasena() async {
    final s = Caudal.leer(context);
    final actual = TextEditingController();
    final nueva = TextEditingController();
    String? error;
    var ocupado = false;
    await showDialog<void>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, poner) => AlertDialog(
        backgroundColor: C.superficie2,
        title: const Text('Cambiar la contraseña'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: actual, obscureText: true, decoration: const InputDecoration(hintText: 'Contraseña actual')),
          const SizedBox(height: 10),
          TextField(controller: nueva, obscureText: true,
              decoration: const InputDecoration(hintText: 'Contraseña nueva (6 o más)')),
          if (error != null) Padding(padding: const EdgeInsets.only(top: 10),
              child: Text(error!, style: const TextStyle(color: C.error))),
        ]),
        actions: [
          TextButton(onPressed: ocupado ? null : () => Navigator.pop(ctx), child: const Text('Cancelar')),
          FilledButton(
            onPressed: ocupado ? null : () async {
              poner(() {
                ocupado = true;
                error = null;
              });
              try {
                await Cuentas.cambiarContrasena(s.cuenta, actual.text, nueva.text);
                if (ctx.mounted) Navigator.pop(ctx);
                s.avisar('Contraseña cambiada');
              } catch (e) {
                poner(() {
                  ocupado = false;
                  error = '$e';
                });
              }
            },
            child: const Text('Cambiar'),
          ),
        ],
      )),
    );
  }

  Future<void> _buscarVersion() async {
    setState(() => _buscandoVersion = true);
    Novedad? n;
    var fallo = false;
    try {
      n = await buscarActualizacion();
    } catch (_) {
      fallo = true;
    }
    if (!mounted) return;
    setState(() => _buscandoVersion = false);
    if (fallo) return Caudal.leer(context).avisar('No se pudo comprobar. Revisa tu conexión.');
    if (n == null) return Caudal.leer(context).avisar('Tienes la última versión ($versionApp)');
    mostrarActualizacion(context, n);
  }

  Widget _seccion(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 26, 20, 6),
        child: Text(t.toUpperCase(),
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: C.acento, letterSpacing: 1)),
      );

  Widget _opcion(String titulo, String clave, List<(String, String)> opciones, {String? ayuda}) {
    final a = Caudal.leer(context).ajustes;
    final v = '${a.texto(clave)}';
    final texto = opciones.where((o) => o.$1 == v).map((o) => o.$2).firstOrNull ?? v;
    return ListTile(
      title: Text(titulo),
      subtitle: Text(ayuda == null ? texto : '$texto · $ayuda', style: estiloSecundario),
      trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
      onTap: () => _elegir(clave, titulo, opciones),
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final a = s.ajustes;
    final sinc = s.sincronizador;
    return Scaffold(
      appBar: AppBar(title: const Text('Ajustes')),
      body: ListView(padding: const EdgeInsets.only(bottom: 40), children: [
        // ---- cuenta
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              CircleAvatar(radius: 26, backgroundColor: C.acento,
                  child: Text(s.cuenta.inicial,
                      style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: C.acentoTexto))),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(s.cuenta.nombre, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                Text('@${s.cuenta.usuario}', style: estiloSecundario),
                const SizedBox(height: 4),
                if (sinc != null)
                  StreamBuilder<String>(
                    stream: sinc.cambios,
                    initialData: sinc.estado,
                    builder: (_, e) => Text(
                      (e.data ?? '').isEmpty ? 'Tu biblioteca se guarda en tu cuenta' : e.data!,
                      style: const TextStyle(fontSize: 12, color: C.texto3)),
                  )
                else
                  const Text('Sin conexión: se sincroniza cuando vuelva internet',
                      style: TextStyle(fontSize: 12, color: C.texto3)),
              ])),
            ]),
          ),
        ),
        if (sinc != null)
          ListTile(
            leading: const Icon(Icons.sync_rounded, color: C.texto2),
            title: const Text('Sincronizar ahora'),
            subtitle: const Text('Tus me gusta, listas y ajustes, iguales en el teléfono y la computadora',
                style: estiloSecundario),
            onTap: () {
              sinc.pronto();
              s.avisar('Sincronizando…');
            },
          ),
        ListTile(
          leading: const Icon(Icons.key_rounded, color: C.texto2),
          title: const Text('Cambiar la contraseña'),
          onTap: s.cuenta.sesion == null ? null : _cambiarContrasena,
        ),
        ListTile(
          leading: const Icon(Icons.logout_rounded, color: C.error),
          title: const Text('Cerrar sesión', style: TextStyle(color: C.error)),
          onTap: () async {
            if (await confirmar(context, 'Cerrar sesión',
                'Lo descargado se queda en el teléfono. Para volver a entrar necesitas tu usuario y contraseña.',
                si: 'Cerrar sesión')) {
              await s.cerrarSesion();
            }
          },
        ),

        _seccion('Sonido'),
        ListTile(
          leading: const Icon(Icons.graphic_eq_rounded, color: C.texto2),
          title: const Text('Ecualizador, súper volumen y velocidad'),
          subtitle: Text([
            a.sino('ecualizador') ? 'Ecualizador: ${a.texto('eq_preset')}' : 'Ecualizador apagado',
            'Volumen: ${nivelesSuper[a.entero('super_volumen').clamp(0, 4)]}',
          ].join(' · '), style: estiloSecundario),
          trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
          onTap: () async {
            await mostrarSonido(context);
            if (mounted) setState(() {});
          },
        ),
        _opcion('Calidad del audio con wifi', 'calidad_audio',
            const [('maxima', 'Máxima (OPUS ~160 kbps)'), ('normal', 'Normal'), ('ahorro', 'Ahorro de datos')]),
        _opcion('Calidad del audio con datos móviles', 'calidad_audio_datos',
            const [('maxima', 'Máxima'), ('normal', 'Normal'), ('ahorro', 'Ahorro de datos')]),
        SwitchListTile.adaptive(
          title: const Text('Reproducción automática'),
          subtitle: const Text('Al acabar la lista sigue con canciones parecidas', style: estiloSecundario),
          value: a.sino('autoplay'), onChanged: (v) => _sino('autoplay', v),
        ),
        SwitchListTile.adaptive(
          title: const Text('Preferir lo descargado'),
          subtitle: const Text('Si la tienes en el teléfono, suena desde ahí (sin gastar datos)', style: estiloSecundario),
          value: a.sino('preferir_descargado'), onChanged: (v) => _sino('preferir_descargado', v),
        ),
        SwitchListTile.adaptive(
          title: const Text('Saltar partes sin música'),
          subtitle: const Text('Intros habladas y silencios en las canciones (SponsorBlock)', style: estiloSecundario),
          value: a.sino('sponsorblock'), onChanged: (v) => _sino('sponsorblock', v),
        ),
        SwitchListTile.adaptive(
          title: const Text('Saltar patrocinios en los videos'),
          value: a.sino('sponsorblock_videos'), onChanged: (v) => _sino('sponsorblock_videos', v),
        ),

        _seccion('Video'),
        _opcion('Calidad del video', 'calidad_video', const [
          ('maxima', 'La mejor posible'), ('2160', '4K'), ('1440', '1440p'), ('1080', '1080p'),
          ('720', '720p'), ('480', '480p'), ('360', '360p'),
        ]),
        _opcion('Formato del video', 'codec_video', const [
          ('auto', 'Automático (el más eficiente)'), ('sin_av1', 'Sin AV1 (teléfonos más antiguos)'),
          ('compatible', 'Máxima compatibilidad (H.264)'),
        ]),

        _seccion('Descargas'),
        _opcion('Formato del audio', 'formato_audio', const [
          ('mp3', 'MP3'), ('m4a', 'M4A / AAC'), ('opus', 'OPUS'), ('flac', 'FLAC'), ('wav', 'WAV'),
        ]),
        _opcion('Calidad del MP3', 'bitrate_mp3', const [
          ('320', '320 kbps'), ('256', '256 kbps'), ('192', '192 kbps'), ('V0', 'Variable (V0)'),
        ]),
        // en iPhone no hay una carpeta de musica comun a todas las apps: lo
        // descargado se ve en la app Archivos (lo explica la pestana Descargar)
        if (Ajustes.hayGuardarEnPublico)
          SwitchListTile.adaptive(
            title: const Text('Guardar en la música del teléfono'),
            subtitle: const Text('Que se vea también en la galería y en otras apps', style: estiloSecundario),
            value: a.sino('guardar_publico'), onChanged: (v) => _sino('guardar_publico', v),
          ),
        SwitchListTile.adaptive(
          title: const Text('Descargar solo con wifi'),
          value: a.sino('solo_wifi_descargas'), onChanged: (v) => _sino('solo_wifi_descargas', v),
        ),

        _seccion('General'),
        _opcion('País del catálogo', 'region', const [
          ('PE', 'Perú'), ('MX', 'México'), ('AR', 'Argentina'), ('CO', 'Colombia'), ('CL', 'Chile'),
          ('ES', 'España'), ('US', 'Estados Unidos'), ('BR', 'Brasil'),
        ]),
        ListTile(
          title: const Text('Borrar el historial'),
          subtitle: const Text('Lo escuchado y lo buscado', style: estiloSecundario),
          onTap: () async {
            if (await confirmar(context, 'Borrar el historial', '¿Borrar lo escuchado y lo buscado?')) {
              await s.coleccion.borrarEscuchas();
              await s.coleccion.borrarBusquedas();
              s.avisar('Historial borrado');
            }
          },
        ),

        _seccion('Caudal'),
        ListTile(
          leading: const Icon(Icons.system_update_rounded, color: C.texto2),
          title: const Text('Buscar actualizaciones'),
          subtitle: Text('Versión $versionApp', style: estiloSecundario),
          trailing: _buscandoVersion
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator.adaptive(strokeWidth: 2))
              : null,
          onTap: _buscandoVersion ? null : _buscarVersion,
        ),
        const Padding(
          padding: EdgeInsets.fromLTRB(20, 12, 20, 0),
          child: Text('Sin anuncios, en segundo plano, a la máxima calidad. Tu cuenta sirve también en Caudal '
              'para Windows.', style: TextStyle(fontSize: 12.5, color: C.texto3)),
        ),
      ]),
    );
  }
}

/// La version nueva. En Android se baja el APK y se abre el instalador; en
/// iPhone (Apple no deja instalar desde dentro) se abre la pagina de descarga.
Future<void> mostrarActualizacion(BuildContext context, Novedad n) => showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (_) => _HojaVersion(n: n),
    );

class _HojaVersion extends StatefulWidget {
  const _HojaVersion({required this.n});
  final Novedad n;

  @override
  State<_HojaVersion> createState() => _HojaVersionState();
}

class _HojaVersionState extends State<_HojaVersion> {
  double _progreso = 0;
  bool _bajando = false;
  String? _error;
  CancelToken? _cancelar;

  @override
  void dispose() {
    _cancelar?.cancel();
    super.dispose();
  }

  /// iPhone: la pagina de la version, con los pasos para instalarla.
  Future<void> _verComo() async {
    final pagina = widget.n.enlace.isNotEmpty ? widget.n.enlace : 'https://github.com/$origen/releases';
    try {
      await abrirEnNavegador(pagina);
      if (mounted) Navigator.pop(context);
    } catch (_) {
      if (mounted) setState(() => _error = 'No se pudo abrir la página de descarga.');
    }
  }

  Future<void> _instalar() async {
    setState(() {
      _bajando = true;
      _error = null;
    });
    _cancelar = CancelToken();
    try {
      final ruta = await descargarApk(widget.n, cancelar: _cancelar,
          alProgresar: (p) => mounted ? setState(() => _progreso = p) : null);
      final fallo = await instalar(ruta);
      if (!mounted) return;
      if (fallo == null) {
        Navigator.pop(context);
      } else {
        setState(() {
          _bajando = false;
          _error = fallo;
        });
      }
    } catch (_) {
      if (mounted && !(_cancelar?.isCancelled ?? false)) {
        setState(() {
          _bajando = false;
          _error = 'No se pudo bajar la actualización. Revisa tu conexión.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final n = widget.n;
    final instalable = n.sePuedeInstalar;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Caudal ${n.version} ya está lista', style: estiloTituloSeccion),
          const SizedBox(height: 4),
          Text(instalable && n.peso > 0 ? 'Tienes la $versionApp · ${formatoBytes(n.peso)}' : 'Tienes la $versionApp',
              style: estiloSecundario),
          if (n.notas.isNotEmpty) ...[
            const SizedBox(height: 14),
            Container(
              constraints: const BoxConstraints(maxHeight: 200),
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: C.superficie3, borderRadius: BorderRadius.circular(10)),
              child: SingleChildScrollView(child: Text(n.notas, style: const TextStyle(color: C.texto2, height: 1.5))),
            ),
          ],
          if (_bajando) ...[
            const SizedBox(height: 16),
            LinearProgressIndicator(value: _progreso / 100, color: C.acento, backgroundColor: C.superficie3),
            const SizedBox(height: 6),
            Text(_progreso >= 99.5 ? 'Abriendo el instalador…' : 'Bajando ${_progreso.toStringAsFixed(0)} %',
                style: estiloSecundario),
          ],
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 12),
              child: Text(_error!, style: const TextStyle(color: C.error))),
          const SizedBox(height: 18),
          // si con la letra grande no caben en una fila, el boton baja a la siguiente
          SizedBox(
            width: double.infinity,
            child: Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              runSpacing: 8,
              children: [
                TextButton(onPressed: _bajando ? null : () => Navigator.pop(context), child: const Text('Más tarde')),
                FilledButton.icon(
                  onPressed: _bajando ? null : (instalable ? _instalar : _verComo),
                  icon: Icon(instalable ? Icons.download_rounded : Icons.open_in_new_rounded),
                  label: Text(instalable ? 'Instalar ahora' : 'Ver cómo actualizar'),
                  style: FilledButton.styleFrom(shape: const StadiumBorder()),
                ),
              ],
            ),
          ),
        ]),
      ),
    );
  }
}
