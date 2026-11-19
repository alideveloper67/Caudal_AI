import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../nucleo/ajustes.dart';
import '../../nucleo/catalogo.dart';
import '../../nucleo/cuentas.dart';
import '../../nucleo/formato.dart';
import '../../nucleo/gustos.dart';
import '../../nucleo/mixes.dart';
import '../../nucleo/version.dart';
import '../comunes.dart';
import '../cumpleanos.dart';
import '../../nucleo/cumpleanos.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../novedades_grandes.dart';
import '../tema.dart';
import '../../nucleo/fondo_app.dart';
import '../../nucleo/mascota_app.dart';
import '../../nucleo/premium.dart';
import '../premium/canje_pase.dart';
import '../premium/personalizar_pagina.dart';
import 'mascota_pagina.dart';
import 'aspecto_pagina.dart';
import 'fondo_pagina.dart';
import 'gustos_pagina.dart';
import 'bateria_ajuste.dart';
import 'donar.dart';
import 'mezclador_ajustes.dart';
import 'mezclador_pagina.dart';
import 'modo_gamer_pagina.dart';
import 'privacidad_pagina.dart';
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
    final actual = _leer(s.ajustes, clave);
    final r = await showModalBottomSheet<String>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Padding(padding: const EdgeInsets.fromLTRB(20, 0, 20, 6), child: Text(titulo, style: estiloTituloSeccion)),
        for (final (valor, texto) in opciones)
          ListTile(
            title: Text(texto),
            trailing: valor == actual ? Icon(Icons.check_rounded, color: C.acento) : null,
            onTap: () => Navigator.pop(ctx, valor),
          ),
        const SizedBox(height: 8),
      ])),
    );
    if (r == null || r == actual) return;
    // los ajustes numericos (p. ej. el espacio de la descarga inteligente) se guardan como numero
    await s.ajustes.poner(clave, Ajustes.defectos[clave] is int ? int.parse(r) : r);
    if (clave == 'region') Catalogo.fijarRegion(r);
    s.sincronizador?.pronto();
    if (mounted) setState(() {});
  }

  static String _leer(Ajustes a, String clave) =>
      Ajustes.defectos[clave] is int ? '${a.entero(clave)}' : a.texto(clave);

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
        padding: const EdgeInsets.fromLTRB(Esp.lado, 28, Esp.lado, 6),
        child: Text(t.toUpperCase(),
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: C.acento, letterSpacing: 1)),
      );

  Widget _opcion(String titulo, String clave, List<(String, String)> opciones, {String? ayuda}) {
    final a = Caudal.leer(context).ajustes;
    final v = _leer(a, clave);
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
        Entrada(child: Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, Esp.s),
          child: Container(
            padding: const EdgeInsets.all(Esp.lado),
            decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              ConGorro(radio: 26, userId: Cumpleanos.i.miId.isEmpty ? s.cuenta.id : Cumpleanos.i.miId,
                  child: CircleAvatar(radius: 26, backgroundColor: C.acento,
                      child: Text(s.cuenta.inicial,
                          style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: C.acentoTexto)))),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(s.cuenta.nombre, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                Text('@${s.cuenta.usuario}', style: estiloSecundario),
                const SizedBox(height: 4),
                if (sinc != null)
                  StreamBuilder<String>(
                    stream: sinc.cambios,
                    initialData: sinc.estado,
                    builder: (_, e) => AnimatedSwitcher(
                      duration: Mov.normal,
                      child: Text(
                        (e.data ?? '').isEmpty ? 'Tu biblioteca se guarda en tu cuenta' : e.data!,
                        key: ValueKey(e.data), style: estiloDetalle),
                    ),
                  )
                else
                  const Text('Sin conexión: se sincroniza cuando vuelva internet', style: estiloDetalle),
              ])),
            ]),
          ),
        )),
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
        if (!s.cuenta.google)
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

        _seccion('Privacidad'),
        ListTile(
          leading: const Icon(Icons.shield_outlined, color: C.texto2),
          title: const Text('Tus datos y privacidad'),
          subtitle: const Text('Datos anónimos, términos, política de privacidad y eliminar tu cuenta',
              style: estiloSecundario),
          trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PrivacidadPagina())),
        ),

        _seccion('Aspecto'),
        SwitchListTile.adaptive(
          secondary: Icon(Icons.speed_rounded, color: C.acento),
          title: const Text('Modo ligero'),
          subtitle: const Text(
              'Quita animaciones y adornos y usa menos memoria, para que Caudal vaya fluido en equipos lentos. '
              'El sonido y la calidad no cambian.',
              style: estiloSecundario),
          value: a.sino('modo_ligero'),
          onChanged: (v) => _sino('modo_ligero', v),
        ),
        if (s.gamer != null)
          ListTile(
            leading: Icon(Icons.sports_esports_rounded, color: C.acento),
            title: const Text('Modo gamer'),
            subtitle: Text(
                s.gamer!.activo
                    ? 'Activo · nivel ${s.gamer!.progreso.nivel}'
                    : 'Ahorro, sonido por juego, listas por situación y niveles',
                style: estiloSecundario),
            trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
            onTap: () async {
              await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ModoGamerPagina(control: s.gamer!)));
              if (mounted) setState(() {});
            },
          ),
        ListTile(
          leading: Icon(Icons.palette_outlined, color: C.acento),
          title: const Text('Color y fondo de la app'),
          subtitle: Text('${Aspecto.acentoDe(a.texto('acento')).$1} · '
              '${Aspecto.fondoDe(a.texto('fondo')).$1}', style: estiloSecundario),
          trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
          onTap: () async {
            await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AspectoPagina()));
            if (mounted) setState(() {});
          },
        ),

        ListTile(
          leading: Icon(Icons.favorite_border_rounded, color: C.acento),
          title: const Text('Mis artistas favoritos'),
          subtitle: const Text('Afinan tus recomendaciones y el Inicio', style: estiloSecundario),
          trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
          onTap: () async {
            final nav = Navigator.of(context);
            final actuales = await Gustos.actualesDe(s.cuenta.sesion, s.cuenta.id);
            if (!mounted) return;
            await nav.push(MaterialPageRoute(
                builder: (_) => GustosPagina(
                    sesion: s.cuenta.sesion, cuentaId: s.cuenta.id, desdeAjustes: true, inicial: actuales,
                    alTerminar: () => nav.pop())));
          },
        ),

        ListenableBuilder(
          listenable: FondoApp.i,
          builder: (context, _) => !FondoApp.i.puede
              ? const SizedBox.shrink()
              : ListTile(
                  leading: const Icon(Icons.wallpaper_rounded, color: Color(0xFFFFC857)),
                  title: const Text('Fondo de Caudal'),
                  subtitle: Text(
                      FondoApp.i.ruta.isEmpty
                          ? 'Pon una imagen tuya detrás de toda la app · exclusivo'
                          : 'Tu imagen se ve al ${FondoApp.i.visible} % · exclusivo',
                      style: estiloSecundario),
                  trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const FondoPagina())),
                ),
        ),

        ListenableBuilder(
          listenable: Listenable.merge([MascotaApp.i, FondoApp.i]),
          builder: (context, _) {
            final m = MascotaApp.i;
            return ListTile(
              leading: Icon(m.puede ? Icons.pets_rounded : Icons.lock_outline_rounded,
                  color: m.puede ? const Color(0xFFFFC857) : C.texto3),
              title: const Text('Mascotita del reproductor'),
              subtitle: Text(
                  !m.puede
                      ? 'Exclusiva para donadores y fundadores de Caudal'
                      : (m.actual == null ? 'Un amiguito que camina por la barra de la canción · exclusivo' : 'Ahora: ${m.actual!.nombre} · exclusivo'),
                  style: estiloSecundario),
              trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const MascotaPagina())),
            );
          },
        ),

        ListenableBuilder(
          listenable: Premium.i,
          builder: (context, _) {
            final p = Premium.i;
            final e = p.estado;
            return Column(children: [
              ListTile(
                leading: Icon(p.activo ? Icons.auto_awesome_rounded : Icons.lock_outline_rounded,
                    color: p.activo ? const Color(0xFFFFC857) : C.texto3),
                title: const Text('Personalizar'),
                subtitle: Text(
                    p.activo
                        ? (e.esPrueba && e.diasRestantes() != null
                            ? textoPrueba(e.diasRestantes()!, e.vence)
                            : 'Marco del avatar, efecto del nombre y temas de color · exclusivo')
                        : 'Marcos, efectos y temas de color · exclusivo para donadores',
                    style: estiloSecundario),
                trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PersonalizarPagina())),
              ),
              if (!p.activo || e.esPrueba)
                ListTile(
                  dense: true,
                  leading: const SizedBox(width: 24),
                  title: const Text('Tengo un código de prueba'),
                  trailing: const Icon(Icons.confirmation_number_outlined, size: 18, color: C.texto3),
                  onTap: () => mostrarCanjePase(context),
                ),
              AvisoPrueba(alDonar: () => mostrarDonar(context)),
            ]);
          },
        ),

        _seccion('Sonido'),
        if (!kIsWeb) const AjusteBateria(),
        if (!kIsWeb) ListTile(
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
          title: const Text('Transiciones como un DJ'),
          subtitle: const Text('Recorta los silencios al pasar de canción para que la siguiente entre justo a tiempo',
              style: estiloSecundario),
          value: a.sino('transicion_dj'), onChanged: (v) => _sino('transicion_dj', v),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
          child: MezclaDjControles(
            alAbrirMezclador: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const MezcladorPagina())),
          ),
        ),
        SwitchListTile.adaptive(
          title: const Text('Apagar la música poco a poco'),
          subtitle: const Text('Con el temporizador para dormir, el volumen baja en los últimos 30 segundos',
              style: estiloSecundario),
          value: a.sino('apagado_suave'), onChanged: (v) => _sino('apagado_suave', v),
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

        // en el navegador no hay descargas ni calidad de video propia (es el reproductor de YouTube)
        if (!kIsWeb) ...[
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
        SwitchListTile.adaptive(
          title: const Text('Bajar sola tu música favorita'),
          subtitle: const Text('Descarga con wifi tus me gusta y lo que más escuchas, para que suene sin internet',
              style: estiloSecundario),
          value: a.sino('descarga_inteligente'), onChanged: (v) => _sino('descarga_inteligente', v),
        ),
        if (a.sino('descarga_inteligente'))
          _opcion('Espacio máximo', 'descarga_inteligente_gb', const [
            ('1', '1 GB'), ('2', '2 GB'), ('5', '5 GB'), ('10', '10 GB'), ('20', '20 GB'), ('50', '50 GB'),
          ], ayuda: 'cuando se llena deja de bajar'),

        ],

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
              await Mixes.olvidar(s.coleccion);
              s.avisar('Historial borrado');
            }
          },
        ),

        _seccion('Caudal'),
        ListTile(
          leading: const Icon(Icons.favorite_rounded, color: Color(0xFFFFC857)),
          title: const Text('Donar a Caudal'),
          subtitle: const Text('Con Yape · los donadores tienen fondo, GIF y mascotita exclusivos', style: estiloSecundario),
          trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
          onTap: () => mostrarDonar(context),
        ),
        ListTile(
          leading: const Icon(Icons.system_update_rounded, color: C.texto2),
          title: Text(actualizaLaTienda ? 'Versión de Caudal' : 'Buscar actualizaciones'),
          subtitle: Text(kIsWeb ? 'Versión web $versionApp · siempre la última'
              : actualizaLaTienda ? 'Versión $versionApp · se actualiza desde Google Play'
              : 'Versión $versionApp', style: estiloSecundario),
          trailing: _buscandoVersion
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator.adaptive(strokeWidth: 2))
              : null,
          onTap: _buscandoVersion || actualizaLaTienda ? null : _buscarVersion,
        ),
        const Padding(
          padding: EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, 0),
          child: Text('Sin anuncios, en segundo plano, a la máxima calidad. Tu cuenta sirve también en Caudal '
              'para Windows.', style: estiloDetalle),
        ),
      ]),
    );
  }
}

/// La version nueva. En Android se baja el APK y se abre el instalador; en
/// iPhone (Apple no deja instalar desde dentro) se abre la pagina de descarga.
///
/// Si la release lleva `[grande]` al inicio de sus notas, en vez de esta hoja
/// sale la pantalla grande de novedades con «Actualizar ahora».
Future<void> mostrarActualizacion(BuildContext context, Novedad n) => n.esGrande
    ? NovedadesGrandes.mostrar(context, actualizacion: n)
    : showModalBottomSheet<void>(
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
