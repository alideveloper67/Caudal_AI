import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../nucleo/fondo_app.dart';
import '../../nucleo/nube.dart';
import '../fondo_capa.dart';
import '../servicios.dart';
import '../tema.dart';
import 'donar.dart';
import 'perfil_comun.dart';

const _oro = Color(0xFFFFC857);

/// «Fondo de Caudal»: la imagen que se ve tenue detrás de toda la app.
/// Exclusivo para donadores y fundadores de Caudal.
class FondoPagina extends StatefulWidget {
  const FondoPagina({super.key});

  @override
  State<FondoPagina> createState() => _FondoPaginaState();
}

class _FondoPaginaState extends State<FondoPagina> {
  bool _subiendo = false;

  Future<void> _elegir() async {
    if (_subiendo) return;
    final s = Caudal.leer(context);
    final social = socialDe(context);
    if (social == null) {
      s.avisar('Para cambiar el fondo necesitas conexión a internet.');
      return;
    }
    try {
      final r = await FilePicker.pickFiles(type: FileType.image, withData: true);
      final bytes = r?.files.firstOrNull?.bytes;
      if (bytes == null) return;
      setState(() => _subiendo = true);
      final jpeg = await prepararFondo(bytes);
      await FondoApp.i.poner(social, jpeg);
      if (mounted) s.avisar('Listo: tu fondo ya está puesto.');
    } catch (e) {
      if (mounted) s.avisar(e is ErrorNube ? e.mensaje : 'No se pudo usar esa imagen. Prueba con otra.');
    } finally {
      if (mounted) setState(() => _subiendo = false);
    }
  }

  Future<void> _quitar() async {
    final s = Caudal.leer(context);
    try {
      await FondoApp.i.quitar(socialDe(context));
    } catch (_) {
      if (mounted) s.avisar('Se quitó en este teléfono; sin conexión no se pudo quitar de la nube.');
    }
  }

  void _ajustar({int? visible, int? desenfoque, bool guardar = false}) =>
      FondoApp.i.ajustar(socialDe(context), visible: visible, desenfoque: desenfoque, guardar: guardar);

  static String _nombreDesenfoque(int n) => n == 0 ? 'Ninguno' : n <= 5 ? 'Suave' : n <= 12 ? 'Medio' : 'Alto';

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: FondoApp.i,
        builder: (context, _) {
          final f = FondoApp.i;
          return Scaffold(
            appBar: AppBar(title: const Text('Fondo de Caudal')),
            body: !f.puede
                ? const _Exclusivo()
                : Center(child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 560),
                    child: ListView(padding: const EdgeInsets.fromLTRB(20, 4, 20, 40), children: [
                    Align(alignment: Alignment.centerLeft, child: _Insignia(texto: f.titulo.isEmpty ? 'Donador de Caudal' : f.titulo)),
                    const SizedBox(height: 14),
                    const Text(
                      'Pon una imagen tuya detrás de toda la app. Se ve suave y transparente, '
                      'para que todo siga leyéndose bien.',
                      style: TextStyle(fontSize: 15, height: 1.4, color: C.texto2),
                    ),
                    const SizedBox(height: 20),
                    _Previa(subiendo: _subiendo, alPulsar: _elegir),
                    const SizedBox(height: 16),
                    Row(children: [
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: _subiendo ? null : _elegir,
                          icon: const Icon(Icons.add_photo_alternate_rounded),
                          label: Text(f.ruta.isEmpty ? 'Elegir imagen' : 'Cambiar imagen'),
                          style: FilledButton.styleFrom(
                              backgroundColor: C.acento, foregroundColor: C.acentoTexto,
                              minimumSize: const Size.fromHeight(50), shape: const StadiumBorder()),
                        ),
                      ),
                      if (f.ruta.isNotEmpty) ...[
                        const SizedBox(width: 10),
                        OutlinedButton(
                          onPressed: _subiendo ? null : _quitar,
                          style: OutlinedButton.styleFrom(
                              minimumSize: const Size(0, 50), shape: const StadiumBorder(),
                              side: BorderSide(color: C.borde), foregroundColor: C.texto2),
                          child: const Text('Quitar'),
                        ),
                      ],
                    ]),
                    const SizedBox(height: 26),
                    _Control(
                      titulo: 'Cuánto se ve',
                      valor: '${f.visible} %',
                      slider: Slider(
                        value: f.visible.toDouble(),
                        min: FondoApp.visibleMin.toDouble(),
                        max: FondoApp.visibleMax.toDouble(),
                        onChanged: f.ruta.isEmpty ? null : (v) => _ajustar(visible: v.round()),
                        onChangeEnd: (v) => _ajustar(visible: v.round(), guardar: true),
                      ),
                      pie: Wrap(spacing: 8, children: [
                        for (final (nombre, v) in const [('Sutil', 12), ('Equilibrado', 22), ('Presente', 38)])
                          ChoiceChip(
                            label: Text(nombre),
                            selected: (f.visible - v).abs() <= 2,
                            onSelected: f.ruta.isEmpty ? null : (_) => _ajustar(visible: v, guardar: true),
                          ),
                      ]),
                    ),
                    const SizedBox(height: 18),
                    _Control(
                      titulo: 'Desenfoque',
                      valor: _nombreDesenfoque(f.desenfoque),
                      slider: Slider(
                        value: f.desenfoque.toDouble(),
                        min: 0,
                        max: FondoApp.desenfoqueMax.toDouble(),
                        onChanged: f.ruta.isEmpty ? null : (v) => _ajustar(desenfoque: v.round()),
                        onChangeEnd: (v) => _ajustar(desenfoque: v.round(), guardar: true),
                      ),
                    ),
                    const SizedBox(height: 22),
                    const Text(
                      'Tu fondo se guarda en tu cuenta: lo verás igual en el teléfono, en la computadora y en el navegador.',
                      style: estiloSecundario,
                    ),
                  ]),
                  )),
          );
        },
      );
}

/// La insignia dorada con el título de la cuenta.
class _Insignia extends StatelessWidget {
  const _Insignia({required this.texto});
  final String texto;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.fromLTRB(10, 6, 14, 6),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          gradient: LinearGradient(colors: [_oro.withValues(alpha: 0.24), C.violeta.withValues(alpha: 0.22)]),
          border: Border.all(color: _oro.withValues(alpha: 0.5)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.star_rounded, size: 18, color: _oro),
          const SizedBox(width: 6),
          Flexible(child: Text(texto, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: _oro))),
        ]),
      );
}

/// La vista previa: el fondo real, con un dibujo de la app encima para ver el resultado.
class _Previa extends StatelessWidget {
  const _Previa({required this.subiendo, required this.alPulsar});
  final bool subiendo;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) {
    final f = FondoApp.i;
    return GestureDetector(
      onTap: subiendo ? null : alPulsar,
      child: AspectRatio(
        aspectRatio: 16 / 10,
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: C.borde),
            boxShadow: const [BoxShadow(color: Color(0x55000000), blurRadius: 24, offset: Offset(0, 10))],
          ),
          clipBehavior: Clip.antiAlias,
          child: Stack(fit: StackFit.expand, children: [
            if (f.ruta.isEmpty)
              DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft, end: Alignment.bottomRight,
                    colors: [C.superficie2, C.fondo],
                  ),
                ),
              )
            else
              FondoImagen(url: f.url, visible: f.visible, desenfoque: f.desenfoque, ancho: 900),
            // un dibujo de la app encima
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Buenas noches', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: C.texto)),
                const SizedBox(height: 10),
                Row(children: [
                  for (var i = 0; i < 3; i++) ...[
                    Expanded(child: _Mini(color: [C.acento, C.violeta, _oro][i])),
                    if (i < 2) const SizedBox(width: 8),
                  ],
                ]),
                const Spacer(),
                Container(
                  height: 40,
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  decoration: BoxDecoration(color: C.superficie2.withValues(alpha: 0.92), borderRadius: BorderRadius.circular(12)),
                  child: Row(children: [
                    Container(width: 26, height: 26, decoration: BoxDecoration(color: C.acento.withValues(alpha: 0.7), borderRadius: BorderRadius.circular(6))),
                    const SizedBox(width: 8),
                    const Expanded(child: Text('Tu canción suena aquí', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: C.texto))),
                    const Icon(Icons.play_arrow_rounded, size: 22, color: C.texto),
                  ]),
                ),
              ]),
            ),
            if (f.ruta.isEmpty && !subiendo)
              Center(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.image_outlined, size: 34, color: C.texto2),
                  const SizedBox(height: 6),
                  Text('Toca para elegir una imagen', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: C.texto2)),
                ]),
              ),
            if (subiendo)
              Container(
                color: Colors.black54,
                child: Center(child: CircularProgressIndicator(color: C.acento)),
              ),
          ]),
        ),
      ),
    );
  }
}

class _Mini extends StatelessWidget {
  const _Mini({required this.color});
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        height: 46,
        decoration: BoxDecoration(color: C.superficie2.withValues(alpha: 0.82), borderRadius: BorderRadius.circular(10)),
        child: Row(children: [
          Container(width: 34, decoration: BoxDecoration(color: color.withValues(alpha: 0.6),
              borderRadius: const BorderRadius.horizontal(left: Radius.circular(10)))),
          const SizedBox(width: 8),
          Expanded(child: Container(height: 6, margin: const EdgeInsets.only(right: 10),
              decoration: BoxDecoration(color: C.texto3.withValues(alpha: 0.6), borderRadius: BorderRadius.circular(3)))),
        ]),
      );
}

class _Control extends StatelessWidget {
  const _Control({required this.titulo, required this.valor, required this.slider, this.pie});
  final String titulo, valor;
  final Widget slider;
  final Widget? pie;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text(titulo, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
          const Spacer(),
          Text(valor, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: C.acento)),
        ]),
        slider,
        if (pie != null) pie!,
      ]);
}

/// Para cuentas sin el título: la función es exclusiva.
class _Exclusivo extends StatelessWidget {
  const _Exclusivo();

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.star_rounded, size: 56, color: _oro),
              const SizedBox(height: 14),
              const Text('Exclusivo para donadores', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
              const SizedBox(height: 8),
              const Text('El fondo de imagen es un detalle para quienes apoyan a Caudal con una donación.',
                  textAlign: TextAlign.center, style: estiloSecundario),
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: () => mostrarDonar(context),
                icon: const Icon(Icons.favorite_rounded, size: 18),
                label: const Text('Donar aquí'),
              ),
            ]),
          ),
        ),
      );
}
