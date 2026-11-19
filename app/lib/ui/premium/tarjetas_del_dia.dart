import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/fondo_app.dart';
import '../../nucleo/mixes.dart';
import '../../nucleo/novedades_para_ti.dart';
import '../../nucleo/premium.dart';
import '../../nucleo/premium_letras.dart';
import '../../nucleo/resumen_semanal.dart';
import '../comunes.dart';
import '../paginas/modo_auto_pagina.dart';
import '../paginas/modos_escucha_pagina.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';
import 'candado_donador.dart';
import 'eq_adaptable_pagina.dart';
import 'que_cancion_era_pagina.dart';
import 'resumen_semanal_pagina.dart';

/// Lo que se ve arriba en Inicio y es nuevo: para donadores, la tarjeta «Lo nuevo para ti»
/// (una vez al día) y, los domingos, «Tu semana en Caudal»; para todos, los accesos al Modo auto,
/// los Modos de escucha y las herramientas de donadores.
class TarjetasDelDia extends StatefulWidget {
  const TarjetasDelDia({super.key, this.cargarNovedades, this.cargarSemana, this.premium});

  /// Para pruebas: de dónde salen las canciones del día y el resumen de la semana.
  final Future<NovedadesDelDia?> Function(Coleccion c)? cargarNovedades;
  final Future<ResumenSemanal?> Function(Coleccion c)? cargarSemana;
  final bool Function()? premium;

  @override
  State<TarjetasDelDia> createState() => _TarjetasDelDiaState();
}

class _TarjetasDelDiaState extends State<TarjetasDelDia> {
  NovedadesDelDia? _novedades;
  ResumenSemanal? _semana;
  bool _pedido = false;

  bool get _premium => (widget.premium ?? esPremiumLetras)();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
  }

  Future<void> _cargar() async {
    if (_pedido || !mounted || !_premium) return;
    _pedido = true;
    final col = Caudal.leer(context).coleccion;
    // cada una va por su lado: si una falla (sin red, por ejemplo) la otra se ve igual
    await Future.wait([
      (widget.cargarNovedades ?? (c) => NovedadesParaTi.delDia(c))(col).then<void>((n) {
        if (mounted && n != null) setState(() => _novedades = n);
      }).catchError((_) {}),
      (widget.cargarSemana ?? _semanaDeHoy)(col).then<void>((s) {
        if (mounted && s != null) setState(() => _semana = s);
      }).catchError((_) {}),
    ]);
  }

  static Future<ResumenSemanal?> _semanaDeHoy(Coleccion c) async {
    final ahora = DateTime.now();
    if (!await ResumenSemanal.toca(c, ahora: ahora)) return null;
    final h = await Historial.leer(c, desde: ResumenSemanal.lunesDe(ahora));
    final r = ResumenSemanal.calcular(h, ahora: ahora);
    return r.suficiente ? r : null;
  }

  Future<void> _cerrarNovedades() async {
    final col = Caudal.leer(context).coleccion;
    setState(() => _novedades = null);
    await NovedadesParaTi.cerrar(col);
  }

  Future<void> _cerrarSemana() async {
    final col = Caudal.leer(context).coleccion;
    setState(() => _semana = null);
    await ResumenSemanal.cerrar(col);
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        // el beneficio puede llegar con la app abierta (se canjea un pase, vuelve la conexión)
        listenable: Listenable.merge([Premium.i, FondoApp.i]),
        builder: (context, _) {
          final premium = _premium;
          if (premium && !_pedido) WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
          final n = premium ? _novedades : null;
          final sem = premium ? _semana : null;
          return Padding(
            padding: const EdgeInsets.only(bottom: 20),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              AnimatedSize(
                duration: const Duration(milliseconds: 260),
                curve: Curves.easeOutCubic,
                alignment: Alignment.topCenter,
                // ancho completo desde el primer cuadro: solo crece el alto (si no, la tarjeta nace desde el centro)
                child: SizedBox(
                    width: double.infinity,
                    child: Column(children: [
                  if (n != null)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, Esp.m),
                      child: TarjetaNovedadesParaTi(datos: n, alCerrar: _cerrarNovedades),
                    ),
                  if (sem != null)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, Esp.m),
                      child: AvisoSemana(resumen: sem, alCerrar: _cerrarSemana),
                    ),
                ])),
              ),
              AccesosNuevos(premium: premium),
            ]),
          );
        },
      );
}

/// «Lo nuevo para ti»: de 6 a 10 canciones que te encajan hoy, con un toque para escucharlas.
class TarjetaNovedadesParaTi extends StatelessWidget {
  const TarjetaNovedadesParaTi({super.key, required this.datos, required this.alCerrar});

  final NovedadesDelDia datos;
  final VoidCallback alCerrar;

  static const _color = Color(0xFF7C5CFF);

  Future<void> _escuchar(BuildContext context, {int inicio = 0}) => Caudal.leer(context).reproducirLista(
        context,
        datos.pistas,
        inicio: inicio,
        aleatorio: false,
        contexto: {'tipo': 'seleccion', 'id': 'novedades_para_ti', 'titulo': 'Lo nuevo para ti'},
      );

  void _verTodas(BuildContext context) {
    Haptico.toque();
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.7,
        minChildSize: 0.4,
        maxChildSize: 0.92,
        builder: (ctx, scroll) => ListView.builder(
          controller: scroll,
          padding: const EdgeInsets.only(bottom: 24),
          itemCount: datos.pistas.length + 1,
          itemBuilder: (_, i) {
            if (i == 0) {
              return const Padding(
                padding: EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, Esp.s),
                child: Text('Lo nuevo para ti hoy', style: estiloTituloSeccion),
              );
            }
            final p = datos.pistas[i - 1];
            return ListTile(
              leading: Portada(url: '${p['miniatura'] ?? ''}', lado: 48, radio: 6),
              title: Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
              onTap: () {
                Navigator.of(ctx).pop();
                _escuchar(context, inicio: i - 1);
              },
            );
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final n = datos.pistas.length;
    return Semantics(
      container: true,
      label: 'Lo nuevo para ti. $n canciones elegidas para hoy.',
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [_color.withValues(alpha: 0.30), C.superficie],
          ),
          border: Border.all(color: _color.withValues(alpha: 0.4)),
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(Esp.l, Esp.m, Esp.xs, Esp.l),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(color: _color.withValues(alpha: 0.25), borderRadius: BorderRadius.circular(13)),
                child: const Icon(Icons.auto_awesome_rounded, color: Color(0xFFC9BBFF), size: 22),
              ),
              const SizedBox(width: Esp.m),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Lo nuevo para ti', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900), maxLines: 1, overflow: TextOverflow.ellipsis),
                  Text('$n canciones para hoy, según lo que escuchas', style: estiloSecundario, maxLines: 2, overflow: TextOverflow.ellipsis),
                ]),
              ),
              IconButton(
                tooltip: 'Cerrar hasta mañana',
                icon: const Icon(Icons.close_rounded, size: 22),
                onPressed: alCerrar,
              ),
            ]),
            const SizedBox(height: Esp.m),
            Padding(
              padding: const EdgeInsets.only(right: Esp.m),
              child: Row(children: [
                for (final p in datos.pistas.take(3)) ...[
                  Portada(url: '${p['miniatura'] ?? ''}', lado: 52, radio: 10),
                  const SizedBox(width: 8),
                ],
                if (n > 3)
                  // medida fija: el número se encoge antes que desbordar, con cualquier tamaño de letra
                  Container(
                    width: 52,
                    height: 52,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(color: C.superficie3, borderRadius: BorderRadius.circular(10)),
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text('+${n - 3}', style: const TextStyle(fontWeight: FontWeight.w800, color: C.texto2)),
                    ),
                  ),
              ]),
            ),
            const SizedBox(height: Esp.m),
            for (final p in datos.pistas.take(3))
              Padding(
                padding: const EdgeInsets.only(right: Esp.m, bottom: 2),
                child: Text('${p['titulo'] ?? ''} · ${p['artista'] ?? ''}',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13.5, color: C.texto2)),
              ),
            const SizedBox(height: Esp.m),
            Padding(
              padding: const EdgeInsets.only(right: Esp.m),
              child: Row(children: [
                Expanded(
                  child: FilledButton(
                    onPressed: () {
                      Haptico.toque();
                      _escuchar(context);
                    },
                    child: const FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        Icon(Icons.play_arrow_rounded),
                        SizedBox(width: 4),
                        Text('Escuchar'),
                      ]),
                    ),
                    style: FilledButton.styleFrom(
                        backgroundColor: _color, foregroundColor: Colors.white, minimumSize: const Size.fromHeight(44), shape: const StadiumBorder()),
                  ),
                ),
                const SizedBox(width: Esp.s),
                TextButton(onPressed: () => _verTodas(context), child: Text('Ver las $n')),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

/// El domingo: «Tu semana en Caudal ya está lista».
class AvisoSemana extends StatelessWidget {
  const AvisoSemana({super.key, required this.resumen, required this.alCerrar});

  final ResumenSemanal resumen;
  final VoidCallback alCerrar;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            gradient: const LinearGradient(
                begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Color(0xFF3B1E6E), Color(0xFF0E4D5C)]),
          ),
          child: InkWell(
            borderRadius: BorderRadius.circular(22),
            onTap: () {
              Haptico.toque();
              ResumenSemanalPagina.abrir(context, resumen: resumen);
            },
            child: Padding(
              padding: const EdgeInsets.fromLTRB(Esp.l, Esp.m, Esp.xs, Esp.m),
              child: Row(children: [
                const Icon(Icons.calendar_view_week_rounded, color: Colors.white, size: 30),
                const SizedBox(width: Esp.m),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('Tu semana en Caudal',
                        style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: Colors.white), maxLines: 1, overflow: TextOverflow.ellipsis),
                    Text('${resumen.rango} · ${tiempoEscuchado(resumen.minutos)}. Toca para verla y compartirla.',
                        style: TextStyle(fontSize: 13, color: Colors.white.withValues(alpha: 0.85)), maxLines: 2, overflow: TextOverflow.ellipsis),
                  ]),
                ),
                IconButton(
                  tooltip: 'Cerrar',
                  icon: const Icon(Icons.close_rounded, color: Colors.white),
                  onPressed: alCerrar,
                ),
              ]),
            ),
          ),
        ),
      );
}

/// Una fila que se desliza de lado con los accesos a lo nuevo.
class AccesosNuevos extends StatelessWidget {
  const AccesosNuevos({super.key, required this.premium});
  final bool premium;

  @override
  Widget build(BuildContext context) {
    Widget acceso(IconData icono, String texto, VoidCallback alPulsar, {bool candado = false}) => Padding(
          padding: const EdgeInsets.only(right: Esp.s),
          child: ActionChip(
            avatar: Icon(icono, size: 18, color: C.acento),
            label: Row(mainAxisSize: MainAxisSize.min, children: [
              Text(texto),
              if (candado) ...[const SizedBox(width: 4), const Icon(Icons.lock_outline_rounded, size: 14, color: oroDonador)],
            ]),
            onPressed: () {
              Haptico.toque();
              alPulsar();
            },
          ),
        );
    return SizedBox(
      height: 44,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
        children: [
          acceso(Icons.directions_car_rounded, 'Modo auto', () => ModoAutoPagina.abrir(context)),
          acceso(Icons.self_improvement_rounded, 'Modos de escucha', () => ModosEscuchaPagina.abrir(context)),
          acceso(Icons.manage_search_rounded, '¿Qué canción era?', () => QueCancionEraPagina.abrir(context), candado: !premium),
          acceso(Icons.equalizer_rounded, 'Ecualizador adaptable', () => EqAdaptablePagina.abrir(context), candado: !premium),
        ],
      ),
    );
  }
}

/// El menú «más» del reproductor grande: los mismos accesos sin salir de la canción.
class MenuMasEscucha extends StatelessWidget {
  const MenuMasEscucha({super.key});

  @override
  Widget build(BuildContext context) => PopupMenuButton<int>(
        tooltip: 'Más',
        icon: const Icon(Icons.more_vert_rounded),
        onSelected: (v) {
          // el reproductor grande queda debajo: las pantallas se abren encima y al volver sigue sonando
          switch (v) {
            case 0:
              ModoAutoPagina.abrir(context);
            case 1:
              ModosEscuchaPagina.abrir(context);
            case 2:
              QueCancionEraPagina.abrir(context);
            case 3:
              EqAdaptablePagina.abrir(context);
          }
        },
        itemBuilder: (_) => const [
          PopupMenuItem(value: 0, child: ListTile(leading: Icon(Icons.directions_car_rounded), title: Text('Modo auto'), contentPadding: EdgeInsets.zero)),
          PopupMenuItem(value: 1, child: ListTile(leading: Icon(Icons.self_improvement_rounded), title: Text('Modos de escucha'), contentPadding: EdgeInsets.zero)),
          PopupMenuItem(value: 2, child: ListTile(leading: Icon(Icons.manage_search_rounded), title: Text('¿Qué canción era?'), contentPadding: EdgeInsets.zero)),
          PopupMenuItem(value: 3, child: ListTile(leading: Icon(Icons.equalizer_rounded), title: Text('Ecualizador adaptable'), contentPadding: EdgeInsets.zero)),
        ],
      );
}
