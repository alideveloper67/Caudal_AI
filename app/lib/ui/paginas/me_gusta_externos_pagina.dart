import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../nucleo/importacion.dart';
import '../../nucleo/importar.dart';
import '../../nucleo/servicios_externos.dart';
import '../servicios.dart';
import '../tema.dart';
import 'importar_pagina.dart';

/// «Pasar tus me gusta»: los de Spotify, YouTube Music y SoundCloud a tus Me gusta de
/// Caudal (aquí, en la PC y en la web), sin repetir. Cada servicio dice en una frase
/// qué se puede hacer y, si algo falta, qué hacer.
class MeGustaExternosPagina extends StatefulWidget {
  const MeGustaExternosPagina({super.key});

  @override
  State<MeGustaExternosPagina> createState() => _MeGustaExternosPaginaState();
}

class _MeGustaExternosPaginaState extends State<MeGustaExternosPagina> {
  ConfigServicios? _conf;
  bool _spotifyConectado = false;
  bool _ocupado = false;
  String? _mensaje;
  bool _mensajeEsError = false;
  final _soundcloud = TextEditingController();
  List<Map<String, dynamic>> _fuentes = const [];

  @override
  void initState() {
    super.initState();
    CuentaSpotify.cambios.addListener(_recargar);
    TrabajoImportacion.i.addListener(_cambio);
    _recargar();
  }

  @override
  void dispose() {
    CuentaSpotify.cambios.removeListener(_recargar);
    TrabajoImportacion.i.removeListener(_cambio);
    _soundcloud.dispose();
    super.dispose();
  }

  void _cambio() {
    if (mounted) setState(() {});
  }

  Future<void> _recargar() async {
    final conf = await ServiciosExternos.config(forzar: true);
    final con = await CuentaSpotify.conectada();
    if (!mounted) return;
    final f = await TrabajoImportacion.fuentes(Caudal.leer(context).coleccion);
    if (!mounted) return;
    setState(() {
      _conf = conf;
      _spotifyConectado = con;
      _fuentes = f;
    });
  }

  void _decir(String t, {bool error = false}) => setState(() {
        _mensaje = t;
        _mensajeEsError = error;
      });

  /// Lee con [leer] y pasa lo leído a Me gusta (la búsqueda sigue en segundo plano).
  Future<void> _pasar(Future<ListaExterna> Function() leer, String enlace) async {
    final t = TrabajoImportacion.i;
    if (t.enMarcha) return _decir('Ya se están pasando canciones. Espera a que termine.', error: true);
    final s = Caudal.leer(context);
    setState(() => _ocupado = true);
    _decir('Leyendo tus canciones…');
    try {
      final l = await leer();
      t.olvidarTerminado();
      await t.empezar(s.coleccion, l, meGusta: true, enlace: enlace);
      void oir() {
        if (t.enMarcha) return;
        t.removeListener(oir);
        if (t.terminado) s.avisar(t.resumen());
      }

      t.addListener(oir);
      if (!mounted) return;
      _decir('');
      // la página de traer listas enseña el avance
      await Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const ImportarPagina(aMeGusta: true)));
    } on ErrorImportar catch (e) {
      if (mounted) _decir(e.mensaje, error: true);
    } catch (_) {
      if (mounted) _decir('No se pudo. Revisa tu internet y vuelve a probar.', error: true);
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  Future<void> _conectarSpotify() async {
    try {
      final url = await CuentaSpotify.empezar();
      final abierto = await launchUrl(url, mode: LaunchMode.externalApplication);
      if (!abierto) _decir('No se pudo abrir el navegador para entrar en Spotify.', error: true);
      if (abierto) _decir('Entra en Spotify y acepta: al volver, tu cuenta quedará conectada.');
    } on ErrorServicio catch (e) {
      _decir(e.mensaje, error: true);
    }
  }

  void _repetir(Map<String, dynamic> f) {
    final enlace = '${f['enlace'] ?? ''}';
    if (enlace == 'spotify:me') {
      _pasar(Importar.meGustaSpotify, enlace);
    } else if (enlace.isNotEmpty) {
      _pasar(() => Importar.leer(enlace), enlace);
    }
  }

  @override
  Widget build(BuildContext context) {
    final conf = _conf;
    final enMarcha = TrabajoImportacion.i.enMarcha;
    final bloqueado = _ocupado || enMarcha;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: C.fondo,
        surfaceTintColor: Colors.transparent,
        title: const Text('Pasar tus me gusta', style: estiloTituloBarra),
      ),
      body: ListView(padding: const EdgeInsets.all(Esp.lado), children: [
        const Text(
          'Las canciones que te gustan en otra app se buscan en YouTube Music y se añaden a tus Me gusta '
          'de Caudal. Las que ya tenías no se repiten, y puedes volver a sincronizar cuando quieras.',
          style: TextStyle(color: C.texto2, height: 1.4),
        ),
        if (_mensaje != null && _mensaje!.isNotEmpty) ...[
          const SizedBox(height: Esp.l),
          Text(_mensaje!, style: TextStyle(color: _mensajeEsError ? C.error : C.texto2, height: 1.35)),
        ],
        if (enMarcha) ...[
          const SizedBox(height: Esp.l),
          OutlinedButton(
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const ImportarPagina(aMeGusta: true))),
            child: Text('Ver el avance (${textoAvance(TrabajoImportacion.i.hechas, TrabajoImportacion.i.total)})'),
          ),
        ],
        const SizedBox(height: Esp.xl),
        if (conf == null)
          const Center(child: Padding(padding: EdgeInsets.all(Esp.xl), child: CircularProgressIndicator()))
        else ...[
          _Servicio(
            nombre: 'Spotify',
            color: const Color(0xFF1DB954),
            children: [
              if (conf.spotifyClientId.isEmpty) ...[
                const Text('Tus «Canciones que te gustan» de Spotify son privadas y la conexión con Spotify aún no '
                    'está activada en Caudal.', style: estiloSecundario),
                const SizedBox(height: Esp.s),
                const Text('Mientras tanto: en Spotify (en la computadora) selecciona tus canciones que te gustan, '
                    'añádelas a una lista nueva y pega su enlace en «Traer una lista» eligiendo «Mis Me gusta». '
                    'Sin la conexión oficial, Spotify solo deja ver 50 canciones.', style: estiloDetalle),
              ] else if (kIsWeb) ...[
                const Text('Conecta tu cuenta de Spotify desde la app del teléfono o de Windows.', style: estiloSecundario),
              ] else if (!_spotifyConectado) ...[
                const Text('Conecta tu cuenta y se traen todas tus canciones que te gustan.', style: estiloSecundario),
                const SizedBox(height: Esp.m),
                FilledButton.icon(
                  onPressed: bloqueado ? null : _conectarSpotify,
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFF1DB954), foregroundColor: Colors.black),
                  icon: const Icon(Icons.link_rounded),
                  label: const Text('Conectar con Spotify', style: TextStyle(fontWeight: FontWeight.w800)),
                ),
                const SizedBox(height: Esp.s),
                const Text('Mientras Caudal esté en el «modo de desarrollo» de Spotify, solo pueden conectarse las '
                    'cuentas que su dueño haya añadido.', style: estiloDetalle),
              ] else ...[
                const Text('Tu cuenta de Spotify está conectada.', style: estiloSecundario),
                const SizedBox(height: Esp.m),
                Wrap(spacing: Esp.s, runSpacing: Esp.s, children: [
                  FilledButton.icon(
                    onPressed: bloqueado ? null : () => _pasar(Importar.meGustaSpotify, 'spotify:me'),
                    style: FilledButton.styleFrom(backgroundColor: const Color(0xFF1DB954), foregroundColor: Colors.black),
                    icon: const Icon(Icons.favorite_rounded),
                    label: const Text('Traer mis me gusta', style: TextStyle(fontWeight: FontWeight.w800)),
                  ),
                  TextButton(onPressed: bloqueado ? null : CuentaSpotify.desconectar, child: const Text('Desconectar')),
                ]),
              ],
            ],
          ),
          const _Servicio(
            nombre: 'YouTube Music',
            color: Color(0xFFFF3B30),
            children: [
              Text('Caudal entra con Google solo para tu cuenta: no tiene permiso para leer tu YouTube, y pedirlo '
                  'exige una revisión de Google.', style: estiloSecundario),
              SizedBox(height: Esp.s),
              Text('Haz esto: en YouTube Music abre «Música que te gusta», toca ⋮ › «Agregar a playlist», crea una '
                  'lista pública o no listada y pega su enlace en «Traer una lista» eligiendo «Mis Me gusta».',
                  style: estiloDetalle),
            ],
          ),
          _Servicio(
            nombre: 'SoundCloud',
            color: const Color(0xFFFF5500),
            children: [
              if (!conf.soundcloud)
                const Text('La conexión oficial con SoundCloud aún no está activada en Caudal, así que todavía no se '
                    'pueden leer los me gusta de un perfil.', style: estiloSecundario)
              else ...[
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
                FilledButton.icon(
                  onPressed: bloqueado
                      ? null
                      : () {
                          final e = Importar.enlaceDe(_soundcloud.text);
                          if (Importar.plataforma(e) != 'soundcloud') {
                            return _decir('Ese enlace no es de SoundCloud.', error: true);
                          }
                          final (tipo, ruta) = Importar.tipoSoundcloud(e);
                          final enlace = tipo == 'perfil' ? 'https://soundcloud.com/$ruta/likes' : e;
                          _pasar(() => Importar.leer(enlace), enlace);
                        },
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFFFF5500), foregroundColor: Colors.white),
                  icon: const Icon(Icons.favorite_rounded),
                  label: const Text('Traer sus me gusta', style: TextStyle(fontWeight: FontWeight.w800)),
                ),
              ],
            ],
          ),
          if (_fuentes.isNotEmpty) ...[
            const SizedBox(height: Esp.l),
            const Text('Ya sincronizadas', style: estiloTituloSeccion),
            const SizedBox(height: Esp.xs),
            const Text('Vuelve a pasar: solo entra lo nuevo.', style: estiloDetalle),
            const SizedBox(height: Esp.s),
            for (final f in _fuentes.take(6))
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text('${f['titulo'] ?? f['enlace'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
                subtitle: Text('${f['servicio'] ?? ''} · ${miles((f['anadidas'] as num?)?.toInt() ?? 0)} añadidas',
                    style: estiloDetalle),
                trailing: TextButton(
                  onPressed: bloqueado || ('${f['enlace']}' == 'spotify:me' && !_spotifyConectado) ? null : () => _repetir(f),
                  child: const Text('Volver a sincronizar'),
                ),
              ),
          ],
        ],
      ]),
    );
  }
}

class _Servicio extends StatelessWidget {
  const _Servicio({required this.nombre, required this.color, required this.children});
  final String nombre;
  final Color color;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: Esp.l),
        padding: const EdgeInsets.all(Esp.l),
        decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(16)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(nombre, style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 16)),
          const SizedBox(height: Esp.s),
          ...children,
        ]),
      );
}
