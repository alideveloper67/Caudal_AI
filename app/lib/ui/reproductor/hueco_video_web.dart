import 'package:flutter/material.dart';

import '../../reproduccion/jugador.dart';

/// El hueco donde se coloca el reproductor de YouTube en la web. Se mide cada
/// vez que se pinta (y al desplazar) para que el recuadro lo siga.
class HuecoVideoWeb extends StatefulWidget {
  const HuecoVideoWeb({super.key});

  @override
  State<HuecoVideoWeb> createState() => _HuecoVideoWebState();
}

class _HuecoVideoWebState extends State<HuecoVideoWeb> {
  // el último que se abrió es el que manda: al cerrarse vuelve al de debajo
  static final List<_HuecoVideoWebState> _abiertos = [];

  final _llave = GlobalKey();
  ScrollPosition? _scroll;

  @override
  void initState() {
    super.initState();
    _abiertos.add(this);
  }

  void _medir() {
    if (!mounted || _abiertos.isEmpty || !identical(_abiertos.last, this)) return;
    final caja = _llave.currentContext?.findRenderObject() as RenderBox?;
    if (caja == null || !caja.attached) return;
    final o = caja.localToGlobal(Offset.zero);
    LienzoVideoWeb.colocar(o & caja.size);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _scroll?.removeListener(_medir);
    _scroll = Scrollable.maybeOf(context)?.position;
    _scroll?.addListener(_medir);
  }

  @override
  void dispose() {
    _scroll?.removeListener(_medir);
    _abiertos.remove(this);
    if (_abiertos.isEmpty) {
      LienzoVideoWeb.colocar(null);
    } else {
      _abiertos.last._medir();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) => _medir());
    return AspectRatio(
      key: _llave,
      aspectRatio: 16 / 9,
      child: DecoratedBox(
        decoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(10)),
      ),
    );
  }
}
