import 'package:flutter/material.dart';

import '../paginas/donar.dart';
import '../tema.dart';

const oroDonador = Color(0xFFFFC857);

/// Lo que ven quienes todavía no son donadores en una función exclusiva: qué hace y cómo
/// conseguirla. Nunca bloquea nada que ya tenían.
class CandadoDonador extends StatelessWidget {
  const CandadoDonador({super.key, required this.icono, required this.titulo, required this.texto});

  final IconData icono;
  final String titulo;
  final String texto;

  @override
  Widget build(BuildContext context) => Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Esp.xl),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(shape: BoxShape.circle, color: oroDonador.withValues(alpha: 0.14)),
                child: Icon(icono, size: 34, color: oroDonador),
              ),
              const SizedBox(height: Esp.l),
              Text(titulo,
                  textAlign: TextAlign.center, style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900)),
              const SizedBox(height: Esp.s),
              Text(texto, textAlign: TextAlign.center, style: estiloSecundario),
              const SizedBox(height: Esp.l),
              const AvisoDonar(),
            ]),
          ),
        ),
      );
}
