import 'package:flutter/material.dart';

import '../../nucleo/colores_nombre.dart';
import '../../nucleo/premium.dart';
import '../../nucleo/social.dart' show Social;
import '../paginas/perfil_comun.dart' show socialDe;
import '../servicios.dart';
import '../tema.dart';
import 'marcos.dart';

/// Un «#RRGGBB» ya validado a [Color] (null si no hay).
Color? colorDeHex(String? hex) => hex == null ? null : Aspecto.colorDe(hex);

/// Un nombre con el efecto y el COLOR propio de su dueño (donadores). El color se pide solo y en lote
/// ([ColoresNombre]); el de la propia cuenta sale de [Premium] al instante. Sin color (o mientras se
/// pregunta) es el [NombreEfecto] de siempre.
class NombreConColor extends StatefulWidget {
  const NombreConColor(
    this.texto, {
    super.key,
    required this.usuario,
    this.efecto = 'ninguno',
    this.estilo,
    this.maxLines = 1,
    this.textAlign,
    this.animar = false,
    this.esMio,
  });

  final String texto;
  final String usuario;
  final String efecto;
  final TextStyle? estilo;
  final int? maxLines;
  final TextAlign? textAlign;
  final bool animar;

  /// Si se sabe ya que es el nombre de la cuenta (si no, se compara el usuario).
  final bool? esMio;

  @override
  State<NombreConColor> createState() => _NombreConColorState();
}

class _NombreConColorState extends State<NombreConColor> {
  bool _mio = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _ver();
  }

  @override
  void didUpdateWidget(covariant NombreConColor old) {
    super.didUpdateWidget(old);
    if (old.usuario != widget.usuario || old.esMio != widget.esMio) _ver();
  }

  void _ver() {
    var yo = '';
    try {
      yo = Caudal.leer(context).cuenta.usuario;
    } catch (_) {}
    final u = widget.usuario.trim().replaceFirst('@', '').toLowerCase();
    _mio = widget.esMio ?? (u.isNotEmpty && u == yo.trim().toLowerCase());
    if (!_mio && u.isNotEmpty) {
      Social? s;
      try {
        s = socialDe(context);
      } catch (_) {}
      ColoresNombre.i.pedir(s, u);
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: Listenable.merge([ColoresNombre.i, Premium.i]),
        builder: (context, _) {
          final hex = _mio ? Premium.i.colorNombreEfectivo : ColoresNombre.i.de(widget.usuario);
          return NombreEfecto(widget.texto,
              efecto: _mio ? Premium.i.efectoNombreEfectivo : widget.efecto,
              estilo: widget.estilo,
              maxLines: widget.maxLines,
              textAlign: widget.textAlign,
              animar: widget.animar,
              color: colorDeHex(hex));
        },
      );
}
