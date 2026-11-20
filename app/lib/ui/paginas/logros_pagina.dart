// La pantalla de logros: el resumen arriba (cuántos, la racha y las horas) y todos los logros
// por categorías, con su progreso. Los conseguidos se pueden «lucir» en el perfil (hasta 3).

import 'package:flutter/material.dart';

import '../../nucleo/logros.dart';
import '../logros_insignia.dart';
import '../tema.dart';

const oroLogros = Color(0xFFF2B829);

class LogrosPagina extends StatefulWidget {
  const LogrosPagina({super.key, required this.logros, this.alCambiarVitrina});

  final Logros logros;

  /// La vitrina cambió (para subirla a la nube en un momento).
  final VoidCallback? alCambiarVitrina;

  static Future<void> abrir(BuildContext context, Logros logros, {VoidCallback? alCambiarVitrina}) =>
      Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => LogrosPagina(logros: logros, alCambiarVitrina: alCambiarVitrina)));

  @override
  State<LogrosPagina> createState() => _LogrosPaginaState();
}

class _LogrosPaginaState extends State<LogrosPagina> {
  String _aviso = '';

  void _alternar(String id) {
    final ok = widget.logros.alternarVitrina(id);
    setState(() => _aviso = ok ? '' : 'Tu vitrina ya tiene 3: quita uno para poner otro.');
    if (ok) widget.alCambiarVitrina?.call();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Logros')),
      body: ListenableBuilder(
        listenable: widget.logros,
        builder: (context, _) {
          final lg = widget.logros;
          final r = lg.resumen;
          return LayoutBuilder(builder: (context, caja) {
            final columnas = caja.maxWidth >= 640 ? 2 : 1;
            return ListView(
              padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, 40),
              children: [
                _Cabecera(conseguidos: r.conseguidos, total: r.total, racha: r.racha, horas: r.horas, aviso: _aviso),
                for (final (cat, titulo) in categoriasLogros) ...[
                  Padding(
                    padding: const EdgeInsets.fromLTRB(2, 22, 2, 8),
                    child: Text(titulo.toUpperCase(),
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: C.acento, letterSpacing: 1)),
                  ),
                  _Rejilla(
                    columnas: columnas,
                    hijos: [
                      for (final l in catalogoLogros.where((l) => l.categoria == cat))
                        TarjetaLogro(logros: lg, logro: l, alAlternar: () => _alternar(l.id)),
                    ],
                  ),
                ],
              ],
            );
          });
        },
      ),
    );
  }
}

class _Rejilla extends StatelessWidget {
  const _Rejilla({required this.columnas, required this.hijos});
  final int columnas;
  final List<Widget> hijos;

  @override
  Widget build(BuildContext context) {
    if (columnas == 1) {
      return Column(children: [
        for (final h in hijos) Padding(padding: const EdgeInsets.only(bottom: 10), child: h),
      ]);
    }
    final filas = <Widget>[];
    for (var i = 0; i < hijos.length; i += 2) {
      filas.add(Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: IntrinsicHeight(
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Expanded(child: hijos[i]),
            const SizedBox(width: 10),
            Expanded(child: i + 1 < hijos.length ? hijos[i + 1] : const SizedBox()),
          ]),
        ),
      ));
    }
    return Column(children: filas);
  }
}

class _Cabecera extends StatelessWidget {
  const _Cabecera(
      {required this.conseguidos, required this.total, required this.racha, required this.horas, required this.aviso});
  final int conseguidos, total, racha, horas;
  final String aviso;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(Esp.lado),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        gradient: LinearGradient(colors: [C.superficie2, C.panel], begin: Alignment.topLeft, end: Alignment.bottomRight),
      ),
      child: Row(children: [
        const InsigniaLogro(clave: 'coleccionista', lado: 56, halo: oroLogros),
        const SizedBox(width: 14),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('$conseguidos de $total', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
            const SizedBox(height: 2),
            Text('Racha de $racha ${racha == 1 ? 'día' : 'días'} · $horas h de música', style: estiloSecundario),
            const SizedBox(height: 4),
            const Text('Toca «Lucir» en los que quieras enseñar en tu perfil (hasta 3).', style: estiloDetalle),
            if (aviso.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(aviso, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: Color(0xFFF5A524))),
            ],
          ]),
        ),
      ]),
    );
  }
}

String _fechaCorta(int epoch) {
  final d = DateTime.fromMillisecondsSinceEpoch(epoch * 1000);
  return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
}

/// Un logro: insignia, nombre, qué hay que hacer, progreso y botón para lucirlo.
class TarjetaLogro extends StatelessWidget {
  const TarjetaLogro({super.key, required this.logros, required this.logro, this.alAlternar});

  final Logros logros;
  final Logro logro;
  final VoidCallback? alAlternar;

  @override
  Widget build(BuildContext context) {
    final (valor, meta, frac) = logros.progreso(logro);
    final hecho = logros.conseguido(logro.id);
    final enVitrina = logros.vitrina.contains(logro.id);
    final unidad = switch (logro.metrica) { 'horas' || 'dia_horas' => ' h', 'racha' => ' días', _ => '' };
    return AnimatedContainer(
      duration: Mov.normal,
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 10),
      decoration: BoxDecoration(
        color: hecho ? C.superficie : C.panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: enVitrina ? oroLogros : C.borde, width: enVitrina ? 1.4 : 1),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        InsigniaLogro(clave: logro.id, lado: 44, conseguida: hecho),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(logro.nombre,
                style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w800, color: hecho ? C.texto : C.texto2)),
            const SizedBox(height: 2),
            Text(logro.descripcion, style: estiloSubTarjeta),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: frac,
                minHeight: 6,
                backgroundColor: C.superficie3,
                valueColor: AlwaysStoppedAnimation(hecho ? oroLogros : C.acento),
              ),
            ),
            const SizedBox(height: 6),
            Row(children: [
              Expanded(
                child: Text(
                  hecho
                      ? 'Conseguido el ${_fechaCorta(logros.desbloqueados[logro.id] ?? 0)}'
                      : '${valor > meta ? meta : valor} de $meta$unidad',
                  style: estiloDetalle,
                ),
              ),
              if (hecho)
                SizedBox(
                  height: 30,
                  child: enVitrina
                      ? FilledButton.icon(
                          style: FilledButton.styleFrom(
                              backgroundColor: oroLogros, foregroundColor: const Color(0xFF2A1A00),
                              padding: const EdgeInsets.symmetric(horizontal: 10)),
                          onPressed: alAlternar,
                          icon: const Icon(Icons.star_rounded, size: 16),
                          label: const Text('En tu perfil', style: TextStyle(fontSize: 12.5)),
                        )
                      : OutlinedButton(
                          style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 14)),
                          onPressed: alAlternar,
                          child: const Text('Lucir', style: TextStyle(fontSize: 12.5)),
                        ),
                ),
            ]),
          ]),
        ),
      ]),
    );
  }
}
