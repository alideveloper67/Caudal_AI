import 'package:flutter/material.dart';

import '../servicios.dart';
import '../tema.dart';

/// Ajustes → Aspecto: el color de la app y su fondo (se ven al momento).
class AspectoPagina extends StatefulWidget {
  const AspectoPagina({super.key});

  @override
  State<AspectoPagina> createState() => _AspectoPaginaState();
}

class _AspectoPaginaState extends State<AspectoPagina> {
  Future<void> _poner(String clave, String valor) async {
    await Caudal.leer(context).ajustes.poner(clave, valor);
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final a = Caudal.of(context).ajustes;
    final acento = a.texto('acento');
    final fondo = a.texto('fondo');
    return Scaffold(
      appBar: AppBar(title: const Text('Aspecto')),
      body: ListView(padding: const EdgeInsets.all(Esp.lado), children: [
        _Muestra(),
        const SizedBox(height: Esp.xl),
        const Text('Color', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text('Botones, lo que suena y el degradado del Inicio.', style: estiloSecundario),
        const SizedBox(height: Esp.m),
        Wrap(spacing: 14, runSpacing: 14, children: [
          for (final e in Aspecto.acentos.entries)
            _Circulo(
              color: e.value.$2,
              nombre: e.value.$1,
              elegido: e.key == acento,
              alPulsar: () => _poner('acento', e.key),
            ),
        ]),
        const SizedBox(height: Esp.xl),
        const Text('Fondo', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text('El color de fondo de toda la app.', style: estiloSecundario),
        const SizedBox(height: Esp.m),
        GridView.count(
          crossAxisCount: 3,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 0.95,
          children: [
            for (final e in Aspecto.fondos.entries)
              _TarjetaFondo(
                colores: e.value.$2,
                nombre: e.value.$1,
                elegido: e.key == fondo,
                alPulsar: () => _poner('fondo', e.key),
              ),
          ],
        ),
        const SizedBox(height: Esp.xl),
        Center(
          child: TextButton.icon(
            onPressed: acento == 'cian' && fondo == 'oscuro'
                ? null
                : () async {
                    await _poner('acento', 'cian');
                    await _poner('fondo', 'oscuro');
                  },
            icon: const Icon(Icons.restart_alt_rounded),
            label: const Text('Volver al aspecto de siempre'),
          ),
        ),
      ]),
    );
  }
}

/// Un trocito del Inicio con los colores elegidos.
class _Muestra extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        height: 150,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: C.borde),
          gradient: LinearGradient(colors: [C.cabecera, C.fondo],
              begin: Alignment.topCenter, end: Alignment.bottomCenter),
        ),
        padding: const EdgeInsets.all(Esp.l),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            CircleAvatar(radius: 14, backgroundColor: C.acento,
                child: Text('A', style: TextStyle(color: C.acentoTexto, fontWeight: FontWeight.w900))),
            const SizedBox(width: 10),
            const Text('Buenas tardes', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          ]),
          const Spacer(),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              Container(width: 36, height: 36,
                  decoration: BoxDecoration(color: C.superficie3, borderRadius: BorderRadius.circular(6))),
              const SizedBox(width: 10),
              const Expanded(child: Text('Lo que suena', style: TextStyle(fontWeight: FontWeight.w700))),
              Icon(Icons.favorite_rounded, color: C.acento),
              const SizedBox(width: 8),
              Container(
                width: 34, height: 34,
                decoration: BoxDecoration(color: C.acento, shape: BoxShape.circle),
                child: Icon(Icons.play_arrow_rounded, color: C.acentoTexto),
              ),
            ]),
          ),
        ]),
      );
}

class _Circulo extends StatelessWidget {
  const _Circulo({required this.color, required this.nombre, required this.elegido, required this.alPulsar});
  final Color color;
  final String nombre;
  final bool elegido;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        selected: elegido,
        label: nombre,
        child: GestureDetector(
          onTap: alPulsar,
          child: SizedBox(
            width: 64,
            child: Column(children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 48, height: 48,
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                  border: Border.all(color: elegido ? Colors.white : Colors.transparent, width: 3),
                ),
                child: elegido ? const Icon(Icons.check_rounded, color: Colors.white) : null,
              ),
              const SizedBox(height: 6),
              Text(nombre, style: TextStyle(fontSize: 12, color: elegido ? C.texto : C.texto2,
                  fontWeight: elegido ? FontWeight.w800 : FontWeight.w500)),
            ]),
          ),
        ),
      );
}

class _TarjetaFondo extends StatelessWidget {
  const _TarjetaFondo({required this.colores, required this.nombre, required this.elegido, required this.alPulsar});
  final List<Color> colores;
  final String nombre;
  final bool elegido;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: alPulsar,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: BoxDecoration(
            color: colores[0],
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: elegido ? C.acento : colores[5], width: elegido ? 2.5 : 1),
          ),
          padding: const EdgeInsets.all(10),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(height: 10, width: 40,
                decoration: BoxDecoration(color: colores[3], borderRadius: BorderRadius.circular(4))),
            const SizedBox(height: 6),
            Container(height: 22,
                decoration: BoxDecoration(color: colores[2], borderRadius: BorderRadius.circular(6))),
            const Spacer(),
            Row(children: [
              Expanded(child: Text(nombre, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700))),
              if (elegido) Icon(Icons.check_circle_rounded, size: 16, color: C.acento),
            ]),
          ]),
        ),
      );
}
