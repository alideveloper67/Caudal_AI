import 'package:flutter/material.dart';

import '../../nucleo/pantalla.dart';
import '../../reproduccion/reproductor.dart';
import '../plataforma.dart';
import '../servicios.dart';

/// «Modo auto»: una pantalla para manejar la música sin mirar. Botones enormes, solo lo
/// esencial (anterior, pausa, siguiente, me gusta y salir), letra grande y contraste alto:
/// blanco y amarillo sobre negro puro. Mantiene la pantalla encendida mientras está abierta.
class ModoAutoPagina extends StatefulWidget {
  const ModoAutoPagina({super.key});

  static Future<void> abrir(BuildContext context) => Navigator.of(context, rootNavigator: true)
      .push(MaterialPageRoute<void>(fullscreenDialog: true, builder: (_) => const ModoAutoPagina()));

  @override
  State<ModoAutoPagina> createState() => _ModoAutoPaginaState();
}

class _ModoAutoPaginaState extends State<ModoAutoPagina> {
  static const _amarillo = Color(0xFFFFD400);
  static const _fondo = Color(0xFF000000);
  static const _panel = Color(0xFF1A1A1A);

  bool _poniendo = false;

  @override
  void initState() {
    super.initState();
    PantallaEncendida.mantener(true);
  }

  @override
  void dispose() {
    PantallaEncendida.mantener(false);
    super.dispose();
  }

  Future<void> _ponerMeGusta(Servicios s) async {
    if (_poniendo) return;
    setState(() => _poniendo = true);
    try {
      final lista = await s.coleccion.listaMeGusta();
      if (!mounted) return;
      if (lista.isEmpty) {
        s.avisar('Aún no tienes canciones con me gusta');
      } else {
        await s.reproducirLista(context, lista,
            aleatorio: true, contexto: {'tipo': 'me_gusta', 'id': 'me_gusta', 'titulo': 'Tus me gusta'});
      }
    } catch (_) {
      if (mounted) s.avisar('No se pudo poner la música. Inténtalo otra vez.');
    } finally {
      if (mounted) setState(() => _poniendo = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final r = s.reproductor;
    return Scaffold(
      backgroundColor: _fondo,
      body: SafeArea(
        child: ListenableBuilder(
          listenable: Listenable.merge([r, s.coleccion]),
          builder: (context, _) {
            final p = r.actual;
            final sonando = r.estado == EstadoRepro.sonando || r.estado == EstadoRepro.cargando;
            return LayoutBuilder(builder: (context, c) {
              final ancho = c.maxWidth > c.maxHeight * 1.15;
              final info = p == null
                  ? _SinMusica(poniendo: _poniendo, alPonerMeGusta: () => _ponerMeGusta(s))
                  : _Info(titulo: '${p['titulo'] ?? ''}', artista: '${p['artista'] ?? ''}', r: r);
              final botones = _Botones(
                sonando: sonando,
                hay: p != null,
                alAnterior: () {
                  Haptico.seleccion();
                  r.anterior();
                },
                alPausa: () {
                  Haptico.seleccion();
                  r.alternar();
                },
                alSiguiente: () {
                  Haptico.seleccion();
                  r.siguiente();
                },
              );
              final barra = _BarraSuperior(
                gusta: p != null && s.coleccion.meGusta('${p['clave']}'),
                hayPista: p != null,
                alGustar: () {
                  Haptico.seleccion();
                  if (p != null) s.alternarMeGusta(p);
                },
              );
              return Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: ancho
                    ? Column(children: [
                        barra,
                        const SizedBox(height: 12),
                        Expanded(
                          child: Row(children: [
                            Expanded(flex: 5, child: info),
                            const SizedBox(width: 16),
                            Expanded(flex: 6, child: botones),
                          ]),
                        ),
                      ])
                    : Column(children: [
                        barra,
                        const SizedBox(height: 8),
                        Expanded(flex: 4, child: info),
                        const SizedBox(height: 12),
                        Expanded(flex: 6, child: botones),
                      ]),
              );
            });
          },
        ),
      ),
    );
  }
}

class _BarraSuperior extends StatelessWidget {
  const _BarraSuperior({required this.gusta, required this.hayPista, required this.alGustar});
  final bool gusta;
  final bool hayPista;
  final VoidCallback alGustar;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 64,
        child: Row(children: [
          Expanded(
            child: _Boton(
              etiqueta: 'Salir del modo auto',
              onTap: () => Navigator.of(context).maybePop(),
              fondo: _ModoAutoPaginaState._panel,
              borde: Colors.white,
              child: const FittedBox(
                fit: BoxFit.scaleDown,
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.close_rounded, color: Colors.white, size: 32),
                  SizedBox(width: 8),
                  Text('Salir', style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w900)),
                ]),
              ),
            ),
          ),
          const SizedBox(width: 12),
          SizedBox(
            width: 88,
            child: _Boton(
              etiqueta: gusta ? 'Quitar de me gusta' : 'Me gusta',
              onTap: hayPista ? alGustar : null,
              fondo: gusta ? _ModoAutoPaginaState._amarillo : _ModoAutoPaginaState._panel,
              borde: gusta ? _ModoAutoPaginaState._amarillo : Colors.white,
              child: Icon(gusta ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                  size: 36, color: gusta ? Colors.black : Colors.white),
            ),
          ),
        ]),
      );
}

/// El título y el artista en grande, con la barra de progreso y lo que falta.
class _Info extends StatelessWidget {
  const _Info({required this.titulo, required this.artista, required this.r});
  final String titulo;
  final String artista;
  final Reproductor r;

  static String _reloj(Duration d) {
    final s = d.inSeconds.clamp(0, 359999);
    final h = s ~/ 3600, m = (s % 3600) ~/ 60, x = s % 60;
    final mm = h > 0 ? m.toString().padLeft(2, '0') : '$m';
    return '${h > 0 ? '$h:' : ''}$mm:${x.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) => Column(children: [
        Expanded(
          child: LayoutBuilder(
            builder: (context, c) => FittedBox(
              fit: BoxFit.scaleDown,
              child: SizedBox(
                width: c.maxWidth,
                child: Column(mainAxisSize: MainAxisSize.min, mainAxisAlignment: MainAxisAlignment.center, children: [
                  Semantics(
                    header: true,
                    child: Text(titulo.isEmpty ? 'Sin título' : titulo,
                        textAlign: TextAlign.center,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            color: Colors.white, fontSize: 36, fontWeight: FontWeight.w900, height: 1.1)),
                  ),
                  const SizedBox(height: 8),
                  Text(artista,
                      textAlign: TextAlign.center,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          color: Color(0xFFEDEDED), fontSize: 24, fontWeight: FontWeight.w600, height: 1.15)),
                ]),
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
        RepaintBoundary(
          child: ListenableBuilder(
            listenable: Listenable.merge([r.posicion, r.duracion]),
            builder: (context, _) {
              final total = r.duracion.value.inMilliseconds;
              final falta = total <= 0 ? Duration.zero : r.duracion.value - r.posicion.value;
              final f = total <= 0 ? 0.0 : (r.posicion.value.inMilliseconds / total).clamp(0.0, 1.0);
              return Column(children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: LinearProgressIndicator(
                    value: f,
                    minHeight: 12,
                    backgroundColor: const Color(0xFF3A3A3A),
                    valueColor: const AlwaysStoppedAnimation(_ModoAutoPaginaState._amarillo),
                  ),
                ),
                const SizedBox(height: 6),
                Text(total <= 0 ? ' ' : 'Faltan ${_reloj(falta)}',
                    style: const TextStyle(color: Color(0xFFEDEDED), fontSize: 20, fontWeight: FontWeight.w700)),
              ]);
            },
          ),
        ),
      ]);
}

class _SinMusica extends StatelessWidget {
  const _SinMusica({required this.poniendo, required this.alPonerMeGusta});
  final bool poniendo;
  final VoidCallback alPonerMeGusta;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, c) => FittedBox(
          fit: BoxFit.scaleDown,
          child: SizedBox(
            width: c.maxWidth,
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.music_note_rounded, color: Colors.white, size: 56),
              const SizedBox(height: 8),
              const Text('No hay nada sonando',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w900)),
              const SizedBox(height: 14),
              SizedBox(
                height: 72,
                width: c.maxWidth,
                child: _Boton(
                  etiqueta: 'Poner tus canciones con me gusta',
                  onTap: poniendo ? null : alPonerMeGusta,
                  fondo: _ModoAutoPaginaState._amarillo,
                  borde: _ModoAutoPaginaState._amarillo,
                  child: poniendo
                      ? const SizedBox(
                          width: 30, height: 30, child: CircularProgressIndicator(strokeWidth: 4, color: Colors.black))
                      : const FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text('Poner mis me gusta',
                              style: TextStyle(color: Colors.black, fontSize: 24, fontWeight: FontWeight.w900)),
                        ),
                ),
              ),
            ]),
          ),
        ),
      );
}

/// Pausa enorme y, debajo, anterior y siguiente a mitad de ancho cada uno.
class _Botones extends StatelessWidget {
  const _Botones({
    required this.sonando,
    required this.hay,
    required this.alAnterior,
    required this.alPausa,
    required this.alSiguiente,
  });
  final bool sonando;
  final bool hay;
  final VoidCallback alAnterior;
  final VoidCallback alPausa;
  final VoidCallback alSiguiente;

  Widget _icono(IconData i, String t, Color color) => LayoutBuilder(
        builder: (context, c) {
          final lado = (c.biggest.shortestSide * 0.5).clamp(28.0, 120.0);
          return FittedBox(
            fit: BoxFit.scaleDown,
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Icon(i, size: lado, color: color),
              Text(t, style: TextStyle(color: color, fontSize: 24, fontWeight: FontWeight.w900)),
            ]),
          );
        },
      );

  @override
  Widget build(BuildContext context) => Column(children: [
        Expanded(
          flex: 3,
          child: _Boton(
            etiqueta: sonando ? 'Pausa' : 'Reproducir',
            onTap: hay ? alPausa : null,
            fondo: _ModoAutoPaginaState._amarillo,
            borde: _ModoAutoPaginaState._amarillo,
            child: _icono(sonando ? Icons.pause_rounded : Icons.play_arrow_rounded, sonando ? 'Pausa' : 'Sonar', Colors.black),
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          flex: 2,
          child: Row(children: [
            Expanded(
              child: _Boton(
                etiqueta: 'Canción anterior',
                onTap: hay ? alAnterior : null,
                fondo: _ModoAutoPaginaState._panel,
                borde: Colors.white,
                child: _icono(Icons.skip_previous_rounded, 'Anterior', Colors.white),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _Boton(
                etiqueta: 'Canción siguiente',
                onTap: hay ? alSiguiente : null,
                fondo: _ModoAutoPaginaState._panel,
                borde: Colors.white,
                child: _icono(Icons.skip_next_rounded, 'Siguiente', Colors.white),
              ),
            ),
          ]),
        ),
      ]);
}

/// Un botón grande con borde grueso (se ve bien incluso con sol) y su etiqueta para lectores de pantalla.
class _Boton extends StatelessWidget {
  const _Boton({required this.etiqueta, required this.onTap, required this.fondo, required this.borde, required this.child});
  final String etiqueta;
  final VoidCallback? onTap;
  final Color fondo;
  final Color borde;
  final Widget child;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        enabled: onTap != null,
        label: etiqueta,
        excludeSemantics: true,
        child: Opacity(
          opacity: onTap == null ? 0.45 : 1,
          child: Material(
            color: fondo,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24), side: BorderSide(color: borde, width: 3)),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: onTap,
              child: Center(child: Padding(padding: const EdgeInsets.all(8), child: child)),
            ),
          ),
        ),
      );
}
