import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/que_suena.dart';
import '../../nucleo/que_suena_grabador.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';

enum _Paso { comprobando, noDisponible, listo, sinPermiso, escuchando, reconociendo, encontrada, noEncontrada, error }

/// «¿Qué suena?»: escucha unos segundos por el micrófono, reconoce la canción y la abre en Caudal.
/// Los parámetros sirven para las pruebas (en la app se usan los de verdad).
class QueSuenaPagina extends StatefulWidget {
  const QueSuenaPagina({super.key, this.servicio, this.grabador, this.buscar, this.alReproducir, this.alACola,
      this.segundos = segundosEscucha});

  final ServicioQueSuena? servicio;
  final Grabador Function()? grabador;
  final Future<List<Json>> Function(String texto)? buscar;
  final void Function(Json pista)? alReproducir;
  final void Function(Json pista)? alACola;
  final int segundos;

  static Future<void> abrir(BuildContext context) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const QueSuenaPagina()));

  @override
  State<QueSuenaPagina> createState() => _QueSuenaPaginaState();
}

class _QueSuenaPaginaState extends State<QueSuenaPagina> {
  late final ServicioQueSuena _servicio = widget.servicio ?? ServicioQueSuena();
  _Paso _paso = _Paso.comprobando;
  String _error = '';
  int _quedan = 0;
  Timer? _cuenta;
  Grabador? _grabador;
  ResultadoQueSuena _resultado = ResultadoQueSuena.nada;
  List<Json> _pistas = const [];
  bool _buscando = false;

  @override
  void initState() {
    super.initState();
    _comprobar();
  }

  @override
  void dispose() {
    _cuenta?.cancel();
    unawaited(_grabador?.soltar());
    super.dispose();
  }

  Future<void> _comprobar() async {
    final si = await _servicio.disponible();
    if (mounted) setState(() => _paso = si ? _Paso.listo : _Paso.noDisponible);
  }

  void _ir(_Paso p, [String error = '']) {
    if (!mounted) return;
    setState(() {
      _paso = p;
      _error = error;
    });
  }

  Future<void> _escuchar() async {
    _cuenta?.cancel();
    await _grabador?.soltar();
    final g = (widget.grabador ?? GrabadorMicrofono.new)();
    _grabador = g;
    try {
      if (!await g.permiso()) return _ir(_Paso.sinPermiso);
      await g.empezar();
    } catch (_) {
      return _ir(_Paso.error, 'No se pudo usar el micrófono. Revisa que ninguna otra app lo esté usando.');
    }
    setState(() {
      _paso = _Paso.escuchando;
      _quedan = widget.segundos;
      _pistas = const [];
    });
    _cuenta = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return t.cancel();
      setState(() => _quedan--);
      if (_quedan <= 0) {
        t.cancel();
        _reconocer(g);
      }
    });
  }

  Future<void> _reconocer(Grabador g) async {
    _ir(_Paso.reconociendo);
    try {
      final audio = await g.parar();
      if (audio == null) {
        return _ir(_Paso.error, 'La grabación salió vacía. Acerca el teléfono a la música y vuelve a probar.');
      }
      final r = await _servicio.reconocer(audio.$1, tipo: audio.$2);
      if (!r.encontrada) return _ir(_Paso.noEncontrada);
      _resultado = r;
      _ir(_Paso.encontrada);
      setState(() => _buscando = true);
      final pistas = await pistasDeResultado(r, buscar: widget.buscar);
      if (mounted) {
        setState(() {
          _pistas = pistas;
          _buscando = false;
        });
      }
    } on ErrorQueSuena catch (e) {
      _ir(e.mensaje == textoNoDisponible ? _Paso.noDisponible : _Paso.error, e.mensaje);
    } catch (_) {
      _ir(_Paso.error, 'No se pudo reconocer ahora. Vuelve a probar.');
    } finally {
      await g.soltar();
      if (identical(_grabador, g)) _grabador = null;
    }
  }

  void _reproducir(Json p) {
    final f = widget.alReproducir;
    if (f != null) {
      f(p);
    } else {
      Caudal.leer(context).reproductor.reproducirPista(p);
    }
  }

  void _aCola(Json p) {
    final f = widget.alACola;
    if (f != null) {
      f(p);
    } else {
      Caudal.leer(context).reproductor.agregarACola([p]);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: C.fondo,
        appBar: AppBar(title: const Text('¿Qué suena?'), backgroundColor: C.fondo),
        body: ListView(padding: const EdgeInsets.fromLTRB(20, 8, 20, 32), children: [
          const Text('Pon el teléfono cerca de la música y toca el botón: en unos segundos te decimos qué canción es.',
              style: estiloSecundario),
          const SizedBox(height: 28),
          Center(child: _boton()),
          const SizedBox(height: 18),
          _estado(),
          if (_paso == _Paso.encontrada) ..._resultadoWidgets(),
        ]),
      );

  Widget _boton() {
    final escuchando = _paso == _Paso.escuchando;
    final ocupado = escuchando || _paso == _Paso.reconociendo || _paso == _Paso.comprobando;
    final apagado = _paso == _Paso.noDisponible;
    return Semantics(
      button: true,
      label: escuchando ? 'Escuchando' : 'Escuchar',
      child: GestureDetector(
        onTap: ocupado || apagado ? null : _escuchar,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          width: 168,
          height: 168,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: apagado ? C.superficie2 : null,
            gradient: apagado ? null : LinearGradient(colors: [C.violeta, C.acento]),
            boxShadow: escuchando ? [BoxShadow(color: C.acento.withValues(alpha: 0.5), blurRadius: 40, spreadRadius: 6)] : null,
          ),
          alignment: Alignment.center,
          child: _paso == _Paso.reconociendo || _paso == _Paso.comprobando
              ? const SizedBox(width: 48, height: 48, child: CircularProgressIndicator(color: Colors.white))
              : Column(mainAxisSize: MainAxisSize.min, children: [
                  Icon(escuchando ? Icons.graphic_eq_rounded : Icons.mic_rounded, size: 56,
                      color: apagado ? C.texto3 : Colors.white),
                  if (escuchando)
                    Text('$_quedan', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.white)),
                ]),
        ),
      ),
    );
  }

  Widget _estado() {
    final (texto, color) = switch (_paso) {
      _Paso.comprobando => ('Preparando…', C.texto2),
      _Paso.noDisponible => (textoNoDisponible, C.texto2),
      _Paso.listo => ('Toca para escuchar', C.texto2),
      _Paso.sinPermiso => ('Caudal necesita permiso para usar el micrófono. Actívalo en los ajustes del teléfono y vuelve a probar.', C.error),
      _Paso.escuchando => ('Escuchando…', C.texto),
      _Paso.reconociendo => ('Reconociendo…', C.texto),
      _Paso.encontrada => ('¡La encontramos!', C.exito),
      _Paso.noEncontrada => ('No la reconocimos. Acércate a la música y prueba otra vez.', C.texto2),
      _Paso.error => (_error, C.error),
    };
    return Text(texto, textAlign: TextAlign.center, style: TextStyle(color: color, fontSize: 15, fontWeight: FontWeight.w600));
  }

  List<Widget> _resultadoWidgets() {
    final r = _resultado;
    final mejor = _pistas.isEmpty ? null : _pistas.first;
    return [
      const SizedBox(height: 18),
      Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: C.superficie, borderRadius: BorderRadius.circular(16)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Portada(url: r.portada.isNotEmpty ? r.portada : '${mejor?['miniatura'] ?? ''}', lado: 76, radio: 12),
            const SizedBox(width: 14),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(r.titulo, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
                if (r.artista.isNotEmpty) Text(r.artista, style: const TextStyle(color: C.texto2, fontSize: 15)),
                if (r.album.isNotEmpty || r.anio.isNotEmpty)
                  Text([r.album, r.anio].where((t) => t.isNotEmpty).join(' · '), style: estiloDetalle),
              ]),
            ),
          ]),
          const SizedBox(height: 14),
          if (_buscando)
            const Text('Buscándola en Caudal…', style: estiloSecundario)
          else if (mejor == null)
            const Text('No la encontramos en Caudal. Prueba a buscarla a mano.', style: estiloSecundario)
          else
            Wrap(spacing: 8, runSpacing: 8, children: [
              FilledButton.icon(onPressed: () => _reproducir(mejor), icon: const Icon(Icons.play_arrow_rounded), label: const Text('Reproducir')),
              FilledButton.tonalIcon(onPressed: () => _aCola(mejor), icon: const Icon(Icons.queue_music_rounded), label: const Text('Añadir a la cola')),
            ]),
          const SizedBox(height: 6),
          TextButton.icon(onPressed: _escuchar, icon: const Icon(Icons.replay_rounded), label: const Text('Escuchar otra')),
        ]),
      ),
      if (_pistas.length > 1) ...[
        const SizedBox(height: 16),
        const Text('Otras versiones', style: estiloTituloSeccion),
        const SizedBox(height: 6),
        for (final p in _pistas.skip(1).take(5))
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Portada(url: '${p['miniatura'] ?? ''}', lado: 46, radio: 8),
            title: Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
            subtitle: Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSubTarjeta),
            trailing: IconButton(tooltip: 'Reproducir', onPressed: () => _reproducir(p), icon: const Icon(Icons.play_arrow_rounded)),
            onTap: () => _reproducir(p),
          ),
      ],
    ];
  }
}
