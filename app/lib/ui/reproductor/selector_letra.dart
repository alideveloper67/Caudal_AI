import 'package:flutter/material.dart';

import '../servicios.dart';
import '../tema.dart';
import 'letra_aspecto.dart';

/// «Diseño de la letra»: el tipo de letra y el estilo, con su aspecto de verdad. Cambia al momento.
Future<void> mostrarDisenoLetra(BuildContext context) => showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      showDragHandle: true,
      barrierColor: Colors.black26, // se sigue viendo la letra detrás
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (ctx) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(ctx).height * 0.56,
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(0, 0, 0, 20),
            child: SelectorLetra(
              alElegirEstilo: (c) => Caudal.leer(context).ajustes.poner('estilo_letra', c),
              alElegirFuente: (c) => Caudal.leer(context).ajustes.poner('fuente_letra', c),
            ),
          ),
        ),
      ),
    );

/// Los estilos y las tipografías como muestras. Se usa en la hoja y en Ajustes › Letra.
class SelectorLetra extends StatefulWidget {
  const SelectorLetra({super.key, required this.alElegirEstilo, required this.alElegirFuente});

  final ValueChanged<String> alElegirEstilo, alElegirFuente;

  @override
  State<SelectorLetra> createState() => _SelectorLetraState();
}

class _SelectorLetraState extends State<SelectorLetra> {
  @override
  void initState() {
    super.initState();
    // cada nombre se escribe en su propia letra: se cargan todas al abrir
    LetraAspecto.cargarTodas();
  }

  @override
  Widget build(BuildContext context) => ValueListenableBuilder<LetraAspecto>(
        valueListenable: LetraAspecto.actual,
        builder: (context, a, _) => LayoutBuilder(builder: (context, c) {
          final columnas = (c.maxWidth / 180).floor().clamp(2, 4);
          final ancho = (c.maxWidth - 40 - 10 * (columnas - 1)) / columnas;
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Diseño', style: estiloTituloSeccion),
              const SizedBox(height: 10),
              Wrap(spacing: 10, runSpacing: 10, children: [
                for (final e in LetraAspecto.estilos)
                  _Muestra(
                    ancho: ancho,
                    alto: 84,
                    elegida: a.estilo == e.clave,
                    nombre: e.nombre,
                    ayuda: e.frase,
                    alTocar: () => widget.alElegirEstilo(e.clave),
                    child: MuestraEstiloLetra(aspecto: LetraAspecto(estilo: e.clave, fuente: a.fuente)),
                  ),
              ]),
              const SizedBox(height: 22),
              const Text('Tipo de letra', style: estiloTituloSeccion),
              const SizedBox(height: 10),
              Wrap(spacing: 10, runSpacing: 10, children: [
                for (final f in LetraAspecto.fuentes)
                  _Muestra(
                    ancho: ancho,
                    alto: 66,
                    elegida: a.fuente == f.clave,
                    ayuda: f.nombre,
                    alTocar: () => widget.alElegirFuente(f.clave),
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text(f.nombre,
                          maxLines: 1,
                          style: LetraAspecto(fuente: f.clave).conFuente(const TextStyle(
                              fontSize: 21, fontWeight: FontWeight.w800, height: 1.3, color: Colors.white))),
                    ),
                  ),
              ]),
            ]),
          );
        }),
      );
}

/// Una palabra a medio cantar en un estilo.
class MuestraEstiloLetra extends StatelessWidget {
  const MuestraEstiloLetra({super.key, required this.aspecto, this.texto = 'Tu canción', this.tamano = 22, this.acento});
  final LetraAspecto aspecto;
  final String texto;
  final double tamano;
  final Color? acento;

  @override
  Widget build(BuildContext context) => FittedBox(
        fit: BoxFit.scaleDown,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6),
          child: LineaLetraFija(
            aspecto: aspecto,
            texto: texto,
            estilo: TextStyle(fontSize: tamano, fontWeight: FontWeight.w800, height: 1.28, color: Colors.white),
            acento: acento ?? Color.lerp(C.acento, Colors.white, 0.25),
            progreso: 0.62,
          ),
        ),
      );
}

class _Muestra extends StatelessWidget {
  const _Muestra({
    required this.ancho,
    required this.alto,
    required this.elegida,
    required this.alTocar,
    required this.child,
    required this.ayuda,
    this.nombre,
  });

  final double ancho, alto;
  final bool elegida;
  final String ayuda;
  final String? nombre;
  final VoidCallback alTocar;
  final Widget child;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        selected: elegida,
        label: nombre == null ? ayuda : '$nombre. $ayuda',
        excludeSemantics: true,
        child: SizedBox(
          width: ancho,
          height: alto,
          child: Material(
            color: elegida ? C.acento.withValues(alpha: 0.2) : Colors.white.withValues(alpha: 0.06),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
              side: BorderSide(color: elegida ? C.acento : Colors.transparent, width: 2),
            ),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: alTocar,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                child: Column(children: [
                  Expanded(child: Center(child: child)),
                  if (nombre != null)
                    Text(nombre!, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: elegida ? C.acento : C.texto2)),
                ]),
              ),
            ),
          ),
        ),
      );
}
