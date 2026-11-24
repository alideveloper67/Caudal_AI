// Ajustes › Letra de las canciones: el estilo y el tipo de letra, con una vista previa que se mueve
// como la letra de verdad (una línea cantada, la que suena y la que viene).

import 'package:flutter/material.dart';

import '../reproductor/letra_aspecto.dart';
import '../reproductor/selector_letra.dart';
import '../servicios.dart';
import '../tema.dart';

class LetraAjustePagina extends StatelessWidget {
  const LetraAjustePagina({super.key});

  /// El resumen para la fila de Ajustes: «Clásica · Predeterminada».
  static String resumen(LetraAspecto a) {
    final e = LetraAspecto.estilos.firstWhere((x) => x.clave == a.estilo, orElse: () => LetraAspecto.estilos.first);
    return '${e.nombre} · ${a.fuenteDef.nombre}';
  }

  @override
  Widget build(BuildContext context) {
    final ajustes = Caudal.leer(context).ajustes;
    return Scaffold(
      appBar: AppBar(title: const Text('Letra de las canciones')),
      body: ValueListenableBuilder<LetraAspecto>(
        valueListenable: LetraAspecto.actual,
        builder: (context, a, _) => ListView(
          padding: const EdgeInsets.fromLTRB(0, 8, 0, 32),
          children: [
            Padding(padding: const EdgeInsets.symmetric(horizontal: 16), child: _VistaPrevia(aspecto: a)),
            const SizedBox(height: 20),
            SelectorLetra(
              alElegirEstilo: (c) => ajustes.poner('estilo_letra', c),
              alElegirFuente: (c) => ajustes.poner('fuente_letra', c),
            ),
            const SizedBox(height: 12),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 20),
              child: Text('Se aplica a la letra del reproductor, al karaoke y a la escena de letra.', style: estiloSecundario),
            ),
          ],
        ),
      ),
    );
  }
}

/// Tres líneas de ejemplo en el estilo y la letra elegidos, sobre un fondo de carátula.
class _VistaPrevia extends StatelessWidget {
  const _VistaPrevia({required this.aspecto});
  final LetraAspecto aspecto;

  @override
  Widget build(BuildContext context) {
    final acento = Color.lerp(C.acento, Colors.white, 0.4);
    TextStyle estilo(Color c) =>
        TextStyle(fontSize: 24, fontWeight: FontWeight.w800, height: 1.28, letterSpacing: -0.3, color: c);
    final lineaActiva = LineaLetraFija(
        aspecto: aspecto, texto: 'Así se ve tu letra', estilo: estilo(Colors.white), acento: acento, progreso: 0.6);
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: Container(
        padding: const EdgeInsets.fromLTRB(18, 22, 18, 22),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [C.acento.withValues(alpha: 0.55), const Color(0xFF1B1530), const Color(0xFF0E0B18)],
          ),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Opacity(
            opacity: 0.72,
            child: LineaLetra(aspecto: aspecto, texto: 'La que ya se cantó', estilo: estilo(const Color(0xB3FFFFFF))),
          ),
          const SizedBox(height: 10),
          lineaActiva,
          const SizedBox(height: 10),
          LineaLetra(aspecto: aspecto, texto: 'y la que viene después', estilo: estilo(const Color(0x73FFFFFF))),
        ]),
      ),
    );
  }
}
