// Ajustes › Letra de las canciones: el estilo y el tipo de letra, con una vista previa que se mueve
// como la letra de verdad (una línea cantada, la que suena y la que viene).

import 'package:flutter/material.dart';

import '../reproductor/letra_aspecto.dart';
import '../reproductor/letra_estilo.dart';
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
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            _VistaPrevia(aspecto: a),
            const SizedBox(height: 20),
            const _Titulo('Estilo'),
            for (final e in LetraAspecto.estilos)
              _Opcion(
                elegida: a.estilo == e.clave,
                titulo: Text(e.nombre, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                frase: e.frase,
                alTocar: () => ajustes.poner('estilo_letra', e.clave),
              ),
            const SizedBox(height: 18),
            const _Titulo('Tipo de letra'),
            for (final f in LetraAspecto.fuentes)
              _Opcion(
                elegida: a.fuente == f.clave,
                // cada nombre escrito en su propia letra
                titulo: Text(
                  f.nombre,
                  style: LetraAspecto(fuente: f.clave)
                      .conFuente(const TextStyle(fontWeight: FontWeight.w700, fontSize: 18, height: 1.2)),
                ),
                frase: f.familia == null ? 'La de siempre' : null,
                alTocar: () => ajustes.poner('fuente_letra', f.clave),
              ),
            const SizedBox(height: 12),
            const Text(
              'Se aplica a la letra del reproductor, al karaoke y a la escena de letra.',
              style: estiloSecundario,
            ),
          ],
        ),
      ),
    );
  }
}

class _Titulo extends StatelessWidget {
  const _Titulo(this.texto);
  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 6, left: 4),
        child: Text(texto.toUpperCase(),
            style: TextStyle(color: C.acento, fontWeight: FontWeight.w800, fontSize: 12.5, letterSpacing: 1.1)),
      );
}

class _Opcion extends StatelessWidget {
  const _Opcion({required this.elegida, required this.titulo, required this.alTocar, this.frase});
  final bool elegida;
  final Widget titulo;
  final String? frase;
  final VoidCallback alTocar;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Material(
          color: elegida ? C.acento.withValues(alpha: 0.16) : Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(14),
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: alTocar,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(children: [
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    titulo,
                    if (frase != null) ...[
                      const SizedBox(height: 2),
                      Text(frase!, style: estiloSecundario),
                    ],
                  ]),
                ),
                Icon(elegida ? Icons.check_circle_rounded : Icons.circle_outlined,
                    color: elegida ? C.acento : C.texto3),
              ]),
            ),
          ),
        ),
      );
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
    final activa = aspecto.conFuente(estilo(Colors.white));
    Widget lineaActiva;
    switch (aspecto.estilo) {
      case 'nitida':
        lineaActiva = TextoLetraResaltado(
            texto: 'Así se ve tu letra', estilo: activa, activo: true, acento: acento, progreso: 0.6);
      case 'neon':
        lineaActiva = Text('Así se ve tu letra',
            style: activa.copyWith(shadows: LetraAspecto.brilloNeon(acento ?? Colors.white)));
      default:
        lineaActiva = Text('Así se ve tu letra', style: activa);
    }
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
