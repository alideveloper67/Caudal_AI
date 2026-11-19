import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../nucleo/nube.dart';
import '../../nucleo/premium.dart';
import '../paginas/perfil_comun.dart' show socialDe, textoSinConexion;
import '../tema.dart';

const _meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
  'noviembre', 'diciembre'];

/// «18 de noviembre» (con el año si no es el actual).
String fechaLarga(DateTime d, {DateTime? ahora}) {
  final hoy = ahora ?? DateTime.now();
  final base = '${d.day} de ${_meses[d.month - 1]}';
  return d.year == hoy.year ? base : '$base de ${d.year}';
}

/// «Tienes 7 días de prueba (vence el 25 de noviembre)».
String textoPrueba(int dias, DateTime? vence, {DateTime? ahora}) {
  final d = '$dias ${dias == 1 ? 'día' : 'días'}';
  return vence == null
      ? 'Tienes $d de prueba'
      : 'Tienes $d de prueba (vence el ${fechaLarga(vence, ahora: ahora)})';
}

/// Pone el código en mayúsculas, solo letras y números, con un guion después de la cuarta letra:
/// `ab12cd34` -> `AB12-CD34`. Se puede pegar con o sin guion.
class FormatoCodigoPase extends TextInputFormatter {
  const FormatoCodigoPase();

  static String normalizar(String t) {
    final limpio = t.toUpperCase().replaceAll(RegExp('[^A-Z0-9]'), '');
    final corto = limpio.length > 12 ? limpio.substring(0, 12) : limpio;
    return corto.length <= 4 ? corto : '${corto.substring(0, 4)}-${corto.substring(4)}';
  }

  @override
  TextEditingValue formatEditUpdate(TextEditingValue anterior, TextEditingValue nuevo) {
    final t = normalizar(nuevo.text);
    return TextEditingValue(text: t, selection: TextSelection.collapsed(offset: t.length));
  }
}

/// El diálogo «Tengo un código»: se escribe el código de prueba y se canjea. Devuelve el resultado
/// (null si se cerró sin canjear). Los mensajes que da el servidor se muestran tal cual.
Future<ResultadoPase?> mostrarCanjePase(BuildContext context) => showDialog<ResultadoPase>(
      context: context,
      builder: (_) => const _CanjeDialogo(),
    );

class _CanjeDialogo extends StatefulWidget {
  const _CanjeDialogo();

  @override
  State<_CanjeDialogo> createState() => _CanjeDialogoState();
}

class _CanjeDialogoState extends State<_CanjeDialogo> {
  final _campo = TextEditingController();
  bool _cargando = false;
  String? _error;
  ResultadoPase? _hecho;

  @override
  void dispose() {
    _campo.dispose();
    super.dispose();
  }

  bool get _valido => FormatoCodigoPase.normalizar(_campo.text).replaceAll('-', '').length >= 4;

  Future<void> _canjear() async {
    if (_cargando || !_valido) return;
    final social = socialDe(context);
    if (social == null) {
      setState(() => _error = textoSinConexion(context));
      return;
    }
    FocusScope.of(context).unfocus();
    setState(() {
      _cargando = true;
      _error = null;
    });
    ResultadoPase r;
    try {
      r = await Premium.i.canjear(social, _campo.text);
    } on ErrorNube catch (e) {
      r = ResultadoPase(ok: false, mensaje: e.mensaje);
    }
    if (!mounted) return;
    setState(() {
      _cargando = false;
      if (r.ok) {
        _hecho = r;
      } else {
        _error = r.mensaje.isEmpty ? 'Ese código no se pudo canjear.' : r.mensaje;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final h = _hecho;
    return AlertDialog(
      backgroundColor: C.panel,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: C.borde)),
      title: Text(h == null ? 'Tengo un código' : '¡Listo!'),
      content: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 360),
        child: SingleChildScrollView(
          child: h != null ? _exito(h) : _formulario(),
        ),
      ),
      actions: h != null
          ? [FilledButton(onPressed: () => Navigator.pop(context, h), child: const Text('Listo'))]
          : [
              TextButton(onPressed: _cargando ? null : () => Navigator.pop(context), child: const Text('Cancelar')),
              FilledButton(
                onPressed: _cargando || !_valido ? null : _canjear,
                child: _cargando
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Canjear'),
              ),
            ],
    );
  }

  Widget _formulario() => Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text(
          'Si un amigo te dio un código de prueba, escríbelo aquí y tendrás los beneficios de donador unos días.',
          style: estiloSecundario,
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _campo,
          enabled: !_cargando,
          autofocus: true,
          textCapitalization: TextCapitalization.characters,
          textInputAction: TextInputAction.done,
          inputFormatters: const [FormatoCodigoPase()],
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: 2.5),
          textAlign: TextAlign.center,
          decoration: const InputDecoration(hintText: 'XXXX-XXXX'),
          onChanged: (_) => setState(() => _error = null),
          onSubmitted: (_) => _canjear(),
        ),
        if (_error != null) ...[
          const SizedBox(height: 10),
          Semantics(
            liveRegion: true,
            child: Text(_error!, style: const TextStyle(color: C.error, height: 1.35)),
          ),
        ],
      ]);

  Widget _exito(ResultadoPase r) {
    final dias = r.dias;
    final linea = dias > 0 ? textoPrueba(dias, r.vence) : (r.mensaje.isEmpty ? 'Tus beneficios están activos.' : r.mensaje);
    return Column(mainAxisSize: MainAxisSize.min, children: [
      Icon(Icons.workspace_premium_rounded, size: 44, color: C.acento),
      const SizedBox(height: 10),
      Text(linea, textAlign: TextAlign.center, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
      if (dias > 0 && r.mensaje.isNotEmpty) ...[
        const SizedBox(height: 6),
        Text(r.mensaje, textAlign: TextAlign.center, style: estiloSecundario),
      ],
    ]);
  }
}

/// Un aviso discreto cuando la prueba está por acabarse («Tu prueba vence en 2 días»). No ocupa
/// nada si no hay prueba o le queda tiempo.
class AvisoPrueba extends StatelessWidget {
  const AvisoPrueba({super.key, this.alDonar, this.margen = const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, Esp.m)});
  final VoidCallback? alDonar;
  final EdgeInsets margen;

  static String texto(EstadoPremium e, {DateTime? ahora}) {
    final d = e.diasRestantes(ahora) ?? 0;
    return d <= 1 ? 'Tu prueba vence hoy' : 'Tu prueba vence en $d días';
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: Premium.i,
        builder: (context, _) {
          final e = Premium.i.estado;
          if (!e.pocaPrueba()) return const SizedBox.shrink();
          return Padding(
            padding: margen,
            child: Container(
              padding: const EdgeInsets.fromLTRB(14, 8, 6, 8),
              decoration: BoxDecoration(
                color: C.superficie2,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFFFC857).withValues(alpha: 0.5)),
              ),
              child: Row(children: [
                const Icon(Icons.hourglass_bottom_rounded, size: 18, color: Color(0xFFFFC857)),
                const SizedBox(width: 10),
                Expanded(child: Text(texto(e), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700))),
                if (alDonar != null) TextButton(onPressed: alDonar, child: const Text('Donar aquí')),
              ]),
            ),
          );
        },
      );
}
