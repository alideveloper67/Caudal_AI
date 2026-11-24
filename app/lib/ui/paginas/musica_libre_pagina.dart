import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/musica_libre.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';

/// «Suena bloqueado» (versión web): canciones completas que siguen con el teléfono
/// bloqueado. Todas van a la cola, para que pasen solas sin tocar nada.
class MusicaLibrePagina extends StatefulWidget {
  const MusicaLibrePagina({super.key, this.busqueda = ''});

  /// Con texto, abre ya buscando eso (p. ej. otra versión de una canción de YouTube).
  final String busqueda;

  static Future<void> abrir(BuildContext context, {String busqueda = ''}) => Navigator.of(context)
      .push(MaterialPageRoute<void>(builder: (_) => MusicaLibrePagina(busqueda: busqueda)));

  @override
  State<MusicaLibrePagina> createState() => _MusicaLibrePaginaState();
}

class _MusicaLibrePaginaState extends State<MusicaLibrePagina> {
  late final _campo = TextEditingController(text: widget.busqueda);
  Timer? _espera;
  String _genero = '';
  List<Json>? _lista;
  bool _fallo = false;
  int _vuelta = 0;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _espera?.cancel();
    _campo.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    final v = ++_vuelta;
    final texto = _campo.text.trim();
    setState(() {
      _lista = null;
      _fallo = false;
    });
    try {
      final l = texto.isEmpty ? await MusicaLibre.tendencias(genero: _genero) : await MusicaLibre.buscar(texto);
      if (mounted && v == _vuelta) setState(() => _lista = l);
    } catch (_) {
      if (mounted && v == _vuelta) setState(() => _fallo = true);
    }
  }

  void _escribir(String _) {
    _espera?.cancel();
    _espera = Timer(const Duration(milliseconds: 450), _cargar);
    setState(() {});
  }

  void _tocar(int i) => Caudal.leer(context).reproductor.reproducirLista(_lista!, inicio: i, contexto: {
        'tipo': 'seleccion', 'id': 'musica_libre',
        'titulo': _campo.text.trim().isEmpty
            ? MusicaLibre.generos.firstWhere((g) => g.$1 == _genero).$2
            : _campo.text.trim(),
      }, modo: 'audio');

  @override
  Widget build(BuildContext context) {
    final lista = _lista;
    return Scaffold(
      appBar: AppBar(title: const Text('Suena bloqueado'), backgroundColor: C.fondo),
      body: CustomScrollView(slivers: [
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 4, Esp.lado, 8),
          sliver: SliverList.list(children: [
            const Text('Estas canciones siguen sonando con el celular bloqueado o en otra app.', style: estiloSecundario),
            const SizedBox(height: 12),
            TextField(
              controller: _campo,
              onChanged: _escribir,
              onSubmitted: (_) {
                _espera?.cancel();
                _cargar();
              },
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Buscar artista o canción',
                prefixIcon: const Icon(Icons.search_rounded, color: C.texto2),
                suffixIcon: _campo.text.isEmpty
                    ? null
                    : IconButton(
                        tooltip: 'Borrar',
                        icon: const Icon(Icons.close_rounded),
                        onPressed: () {
                          _campo.clear();
                          _cargar();
                        },
                      ),
              ),
            ),
          ]),
        ),
        if (_campo.text.trim().isEmpty)
          SliverToBoxAdapter(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 4),
              child: Row(children: [
                for (final (clave, nombre) in MusicaLibre.generos)
                  Pildora(
                    texto: nombre,
                    activa: _genero == clave,
                    alPulsar: () {
                      _genero = clave;
                      _cargar();
                    },
                  ),
              ]),
            ),
          ),
        if (lista != null && lista.isNotEmpty)
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(Esp.lado, 8, Esp.lado, 4),
              child: Align(
                alignment: Alignment.centerLeft,
                child: FilledButton.icon(
                  onPressed: () => _tocar(0),
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: const Text('Escuchar todo'),
                ),
              ),
            ),
          ),
        if (_fallo)
          SliverToBoxAdapter(
            child: Vacio(icono: Icons.wifi_off_rounded, titulo: 'No se pudo cargar', error: true,
                texto: 'Revisa tu conexión y vuelve a intentarlo.', alAccion: _cargar),
          )
        else if (lista == null)
          const SliverToBoxAdapter(child: Esqueleto(filas: true))
        else if (lista.isEmpty)
          const SliverToBoxAdapter(
            child: Vacio(icono: Icons.search_off_rounded, titulo: 'Aquí no está',
                texto: 'Este catálogo es de artistas independientes: no tiene todo lo de YouTube. Prueba otro nombre '
                    'o agrega tu archivo en «Tu música».'),
          )
        else
          SliverList.builder(
            itemCount: lista.length,
            itemBuilder: (_, i) => FilaPista(pista: lista[i], alPulsar: () => _tocar(i)),
          ),
        const SliverToBoxAdapter(child: _Creditos()),
        const SliverToBoxAdapter(child: SizedBox(height: 110)),
      ]),
    );
  }
}

class _Creditos extends StatelessWidget {
  const _Creditos();

  @override
  Widget build(BuildContext context) {
    Widget enlace(String texto, String url) => TextButton(
          onPressed: () => launchUrl(Uri.parse(url)),
          style: TextButton.styleFrom(visualDensity: VisualDensity.compact, foregroundColor: C.texto2),
          child: Text(texto, style: const TextStyle(fontSize: 12, decoration: TextDecoration.underline)),
        );
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.lado, 24, Esp.lado, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Música de artistas independientes desde Audius, con su Open Music License. Los derechos son de cada '
            'artista. El audio llega desde los servidores de Audius y Caudal no lo guarda.', style: estiloDetalle),
        Wrap(children: [
          enlace('Licencia', MusicaLibre.enlaceLicencia),
          enlace('Términos de Audius', MusicaLibre.enlaceTerminos),
          enlace('Privacidad de Audius', MusicaLibre.enlacePrivacidad),
        ]),
      ]),
    );
  }
}

/// La franja de Inicio en el navegador: lo que sigue sonando al bloquear.
class SeccionMusicaLibre extends StatefulWidget {
  const SeccionMusicaLibre({super.key});

  @override
  State<SeccionMusicaLibre> createState() => _SeccionMusicaLibreState();
}

class _SeccionMusicaLibreState extends State<SeccionMusicaLibre> {
  List<Json> _lista = const [];

  @override
  void initState() {
    super.initState();
    MusicaLibre.tendencias().then((l) {
      if (mounted) setState(() => _lista = l);
    }, onError: (_) {});
  }

  @override
  Widget build(BuildContext context) => _lista.isEmpty
      ? const SizedBox.shrink()
      : Padding(
          padding: const EdgeInsets.only(bottom: Esp.entreSecciones),
          child: Carrusel(
            titulo: 'Suena con el celular bloqueado',
            elementos: _lista.take(15).toList(),
            alPulsarMas: () => MusicaLibrePagina.abrir(context),
          ),
        );
}
