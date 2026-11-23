import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../reproduccion/reproductor.dart';
import '../reproduccion/ventana_web.dart';
import 'paginas/escena_web.dart';
import 'paginas/visualizador_pagina.dart';
import 'panel_web.dart';
import 'servicios.dart';

/// Abre o cierra la ventanita del mini reproductor; si no se puede, dice por qué.
Future<void> abrirMini(Servicios s) async {
  final motivo = await VentanaWeb.alternarMini(s.reproductor);
  if (motivo != null) s.avisar(motivo);
}

/// Esc cierra la vista a pantalla completa que envuelve.
class CerrarConEsc extends StatelessWidget {
  const CerrarConEsc({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => CallbackShortcuts(
        bindings: {const SingleActivator(LogicalKeyboardKey.escape): () => Navigator.of(context).maybePop()},
        child: Focus(autofocus: true, child: child),
      );
}

/// Los atajos de Caudal Escritorio en el navegador. Los que el navegador se
/// queda (Ctrl+L, Ctrl+R, Ctrl+D…) llevan aquí una tecla suelta.
class AtajosTeclado extends StatefulWidget {
  const AtajosTeclado({super.key, required this.alBuscar, required this.child, this.activo = kIsWeb});

  final VoidCallback alBuscar;
  final Widget child;
  final bool activo;

  static const lista = [
    ('Espacio o K', 'Reproducir o pausar'),
    ('Ctrl + → / ←', 'Canción siguiente o anterior'),
    ('Mayús + → / ←', 'Adelantar o atrasar 10 segundos'),
    ('Ctrl + ↑ / ↓', 'Subir o bajar el volumen'),
    ('M', 'Silenciar'),
    ('S', 'Aleatorio'),
    ('R', 'Repetir'),
    ('N / Q / L', 'Panel: sonando, cola o letra'),
    ('V', 'Visualizador'),
    ('E', 'Escena'),
    ('I', 'Mini reproductor'),
    ('/', 'Buscar'),
    ('?', 'Ver estos atajos'),
  ];

  static Future<void> mostrar(BuildContext context) => showDialog<void>(
        context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Atajos del teclado'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final (tecla, que) in lista)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 5),
                child: Row(children: [
                  SizedBox(width: 130, child: Text(tecla, style: const TextStyle(fontWeight: FontWeight.w800))),
                  Expanded(child: Text(que)),
                ]),
              ),
          ]),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Listo'))],
      ),
    );

  @override
  State<AtajosTeclado> createState() => _AtajosTecladoState();
}

class _AtajosTecladoState extends State<AtajosTeclado> {
  double? _antesDeSilenciar;
  bool _ayudaAbierta = false;

  @override
  void initState() {
    super.initState();
    if (widget.activo) HardwareKeyboard.instance.addHandler(_tecla);
  }

  @override
  void dispose() {
    if (widget.activo) HardwareKeyboard.instance.removeHandler(_tecla);
    super.dispose();
  }

  /// ¿Se está escribiendo en un campo de texto?
  bool get _escribiendo {
    final ctx = FocusManager.instance.primaryFocus?.context;
    if (ctx == null) return false;
    return ctx.widget is EditableText || ctx.findAncestorWidgetOfExactType<EditableText>() != null;
  }

  /// Con Espacio, un botón que tiene el foco ya hace lo suyo.
  bool get _enBoton {
    final ctx = FocusManager.instance.primaryFocus?.context;
    return ctx != null && ctx.findAncestorWidgetOfExactType<InkResponse>() != null ||
        ctx != null && ctx.findAncestorWidgetOfExactType<Slider>() != null;
  }

  bool _tecla(KeyEvent e) {
    if (e is! KeyDownEvent || !mounted || _escribiendo) return false;
    final t = HardwareKeyboard.instance;
    if (t.isAltPressed || t.isMetaPressed) return false;
    final r = Caudal.leer(context).reproductor;
    final k = e.logicalKey;
    if (t.isControlPressed) {
      if (k == LogicalKeyboardKey.arrowRight) return _hecho(() => r.siguiente());
      if (k == LogicalKeyboardKey.arrowLeft) return _hecho(r.anterior);
      if (k == LogicalKeyboardKey.arrowUp) return _hecho(() => r.fijarVolumen(r.volumen + 5));
      if (k == LogicalKeyboardKey.arrowDown) return _hecho(() => r.fijarVolumen(r.volumen - 5));
      return false;
    }
    if (e.character == '?') return _hecho(_ayuda);
    if (e.character == '/') return _hecho(widget.alBuscar);
    if (t.isShiftPressed) {
      if (k == LogicalKeyboardKey.arrowRight) return _hecho(() => r.avanzar(10));
      if (k == LogicalKeyboardKey.arrowLeft) return _hecho(() => r.avanzar(-10));
      return false;
    }
    if (k == LogicalKeyboardKey.space) return _enBoton ? false : _hecho(r.alternar);
    if (k == LogicalKeyboardKey.keyK) return _hecho(r.alternar);
    if (k == LogicalKeyboardKey.keyM) return _hecho(() => _silenciar(r));
    if (k == LogicalKeyboardKey.keyS) return _hecho(r.alternarAleatorio);
    if (k == LogicalKeyboardKey.keyR) return _hecho(r.ciclarRepetir);
    // lo que abre otra vista, solo si no hay ya una encima
    if (ModalRoute.of(context)?.isCurrent == false) return false;
    final s = Caudal.leer(context);
    if (k == LogicalKeyboardKey.keyN) return _hecho(() => PanelWeb.alternar(s, 'sonando'));
    if (k == LogicalKeyboardKey.keyQ) return _hecho(() => PanelWeb.alternar(s, 'cola'));
    if (k == LogicalKeyboardKey.keyL) return _hecho(() => PanelWeb.alternar(s, 'letras'));
    if (k == LogicalKeyboardKey.keyV) return _hecho(() => VisualizadorPagina.abrir(context));
    if (k == LogicalKeyboardKey.keyE) return _hecho(() => EscenaWebPagina.abrir(context));
    if (k == LogicalKeyboardKey.keyI) return _hecho(() => abrirMini(s));
    return false;
  }

  bool _hecho(void Function() hacer) {
    hacer();
    return true;
  }

  void _silenciar(Reproductor r) {
    if (r.volumen > 0) {
      _antesDeSilenciar = r.volumen;
      r.fijarVolumen(0);
    } else {
      r.fijarVolumen(_antesDeSilenciar ?? 100);
    }
  }

  Future<void> _ayuda() async {
    if (_ayudaAbierta) return;
    _ayudaAbierta = true;
    await AtajosTeclado.mostrar(context);
    _ayudaAbierta = false;
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
