import 'package:flutter/material.dart';

import '../nucleo/coleccion.dart';
import '../nucleo/recomendador.dart';
import 'comunes.dart';
import 'servicios.dart';
import 'tema.dart';

/// «Tu mes pasado»: lo que mas escuchaste el mes anterior, con un toque para
/// escucharlo y otro para guardarlo como una lista de verdad (con portada de
/// mosaico, que sale de sus primeras canciones).
class TarjetaMesPasado extends StatefulWidget {
  const TarjetaMesPasado({super.key, required this.mix});

  /// El mix que arma [Recomendador.mesPasado].
  final Json mix;

  @override
  State<TarjetaMesPasado> createState() => _TarjetaMesPasadoState();
}

class _TarjetaMesPasadoState extends State<TarjetaMesPasado> {
  int? _lista; // el id de la lista si ya esta guardada
  bool _guardando = false;

  String get _nombre => '${widget.mix['nombre_lista'] ?? widget.mix['titulo']}';

  List<Json> get _pistas => [
        for (final p in (widget.mix['pistas'] is List ? widget.mix['pistas'] as List : const []))
          if (p is Map) Map<String, dynamic>.from(p)
      ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _buscarGuardada());
  }

  /// Si ya la guardaste otro dia, el boton lo dice y lleva a la lista.
  Future<void> _buscarGuardada() async {
    try {
      final listas = await Caudal.leer(context).coleccion.listas();
      final l = listas.where((l) => '${l['nombre']}' == _nombre).firstOrNull;
      if (l != null && mounted) setState(() => _lista = Servicios.idLista(l['id']));
    } catch (_) {}
  }

  Future<void> _guardar() async {
    final s = Caudal.leer(context);
    if (_lista != null) {
      s.abrirElemento(context, {'tipo': 'mi_lista', 'id': _lista, 'titulo': _nombre});
      return;
    }
    if (_guardando) return;
    setState(() => _guardando = true);
    try {
      final id = await Recomendador.guardarMesPasado(s.coleccion, widget.mix);
      if (!mounted) return;
      setState(() {
        _lista = id;
        _guardando = false;
      });
      s.avisar('Guardada en tus listas como «$_nombre»');
    } on FormatException catch (e) {
      if (mounted) setState(() => _guardando = false);
      s.avisar(e.message);
    } catch (_) {
      if (mounted) setState(() => _guardando = false);
      s.avisar('No se pudo guardar la lista. Inténtalo otra vez.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final mix = widget.mix;
    final portadas = [for (final m in (mix['miniaturas'] as List? ?? const [])) '$m']
        .where((m) => m.isNotEmpty).take(4).toList();
    final pistas = _pistas;
    final total = pistas.length;
    final color = Color(((mix['color'] as num?)?.toInt() ?? 0xFFE8795A));
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
      child: Pulsable(
        escala: 0.98,
        child: GestureDetector(
          onTap: () => s.abrirElemento(context, mix),
          child: Container(
            padding: const EdgeInsets.all(Esp.l),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              gradient: LinearGradient(
                colors: [color, Color.lerp(color, const Color(0xFF1A0F2E), 0.72)!],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                _Mosaico(portadas: portadas),
                const SizedBox(width: Esp.m),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Row(children: [
                      Icon(Icons.history_rounded, size: 16, color: Color(0xFFFFE9B0)),
                      SizedBox(width: 6),
                      Text('TU MES PASADO', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800,
                          letterSpacing: 1, color: Color(0xFFFFE9B0))),
                    ]),
                    const SizedBox(height: 4),
                    Text(_nombre, maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, height: 1.15)),
                    const SizedBox(height: 2),
                    Text('$total ${total == 1 ? 'canción' : 'canciones'}',
                        style: const TextStyle(fontSize: 12.5, color: Color(0xCCFFFFFF))),
                  ]),
                ),
                IconButton.filled(
                  tooltip: 'Reproducir',
                  style: IconButton.styleFrom(backgroundColor: Colors.white, foregroundColor: const Color(0xFF3A1B2E)),
                  onPressed: pistas.isEmpty ? null : () => s.reproductor.reproducirLista(pistas,
                      contexto: {'tipo': 'mix', 'id': mix['id'], 'titulo': mix['titulo']}),
                  icon: const Icon(Icons.play_arrow_rounded),
                ),
              ]),
              const SizedBox(height: Esp.m),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton.icon(
                  onPressed: _guardando ? null : _guardar,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: const BorderSide(color: Color(0x88FFFFFF)),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  ),
                  icon: _guardando
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : Icon(_lista != null ? Icons.check_circle_rounded : Icons.playlist_add_rounded, size: 20),
                  label: Text(_lista != null ? 'Guardada · ver la lista' : 'Guardar como lista'),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

/// Las portadas en mosaico (hasta cuatro; con una sola, grande).
class _Mosaico extends StatelessWidget {
  const _Mosaico({required this.portadas});
  final List<String> portadas;

  @override
  Widget build(BuildContext context) {
    const lado = 92.0;
    if (portadas.length < 4) {
      return Portada(url: portadas.isEmpty ? '' : portadas.first, lado: lado, radio: 8,
          icono: Icons.history_rounded);
    }
    const mitad = lado / 2;
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: SizedBox(
        width: lado,
        height: lado,
        child: Wrap(children: [
          for (final url in portadas) Portada(url: url, lado: mitad, radio: 0),
        ]),
      ),
    );
  }
}
