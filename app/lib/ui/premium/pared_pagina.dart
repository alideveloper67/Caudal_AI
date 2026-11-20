import 'package:flutter/material.dart';

import '../../nucleo/donadores_extra.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/social.dart' show Social;
import '../paginas/perfil_comun.dart' show socialDe;
import '../tema.dart';
import 'candado_donador.dart';
import 'nombre_color.dart';

/// «Pared de agradecimiento»: los donadores y fundadores que aceptaron aparecer. Primero los
/// fundadores; cada nombre con su color propio. La misma lista sale en la web de Caudal.
class ParedPagina extends StatefulWidget {
  const ParedPagina({super.key, this.cargar});

  /// Para las pruebas: de dónde sale la lista (si no, del servidor).
  final Future<List<DonadorPared>> Function()? cargar;

  static Future<void> abrir(BuildContext context) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const ParedPagina()));

  @override
  State<ParedPagina> createState() => _ParedPaginaState();
}

class _ParedPaginaState extends State<ParedPagina> {
  late Future<List<DonadorPared>> _lista;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _lista = _pedir();
  }

  Future<List<DonadorPared>> _pedir() {
    final f = widget.cargar;
    if (f != null) return f();
    Social? s;
    try {
      s = socialDe(context);
    } catch (_) {}
    return ParedAgradecimiento.cargar(s);
  }

  void _recargar() => setState(() => _lista = _pedir());

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          backgroundColor: C.fondoVivo,
          surfaceTintColor: Colors.transparent,
          title: const Text('Pared de agradecimiento', style: estiloTituloBarra),
        ),
        body: FutureBuilder<List<DonadorPared>>(
          future: _lista,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              final e = snap.error;
              return _mensaje(
                Icons.wifi_off_rounded,
                e is SinConexion
                    ? 'No hay conexión. Revisa tu internet y vuelve a probar.'
                    : 'La pared todavía no está disponible. Vuelve a intentarlo más tarde.',
                boton: true,
              );
            }
            final lista = snap.data ?? const <DonadorPared>[];
            return ListView(padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.m, Esp.lado, 40), children: [
              const Text('Gracias a quienes hacen posible Caudal', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
              const SizedBox(height: 6),
              const Text(
                  'Caudal es gratis y sin anuncios gracias a estas personas. Si donas, puedes aparecer aquí: '
                  'marca la casilla en Ajustes › Personalizar.',
                  style: estiloSecundario),
              const SizedBox(height: Esp.l),
              if (lista.isEmpty)
                _mensaje(Icons.favorite_border_rounded, 'Todavía no hay nadie en la pared. ¡Puedes ser la primera persona!')
              else
                Wrap(spacing: 10, runSpacing: 10, children: [for (final d in lista) _tarjeta(d)]),
            ]);
          },
        ),
      );

  Widget _tarjeta(DonadorPared d) => Semantics(
        label: '${d.nombre}, ${d.etiqueta}',
        excludeSemantics: true,
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
          decoration: BoxDecoration(
            color: C.superficie2,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: d.fundador ? oroDonador.withValues(alpha: 0.6) : C.borde),
          ),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 220),
              child: Text(d.nombre,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: colorDeHex(d.color) ?? C.texto)),
            ),
            const SizedBox(height: 4),
            Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(d.fundador ? Icons.workspace_premium_rounded : Icons.favorite_rounded,
                  size: 14, color: d.fundador ? oroDonador : C.acento),
              const SizedBox(width: 4),
              Text(d.etiqueta, style: estiloDetalle),
              const SizedBox(width: 8),
              Text('@${d.usuario}', style: estiloDetalle),
            ]),
          ]),
        ),
      );

  Widget _mensaje(IconData icono, String texto, {bool boton = false}) => Center(
        child: Padding(
          padding: const EdgeInsets.all(Esp.xl),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icono, size: 40, color: C.texto2),
            const SizedBox(height: Esp.m),
            Text(texto, textAlign: TextAlign.center, style: estiloSecundario),
            if (boton) ...[
              const SizedBox(height: Esp.m),
              FilledButton(onPressed: _recargar, child: const Text('Reintentar')),
            ],
          ]),
        ),
      );
}
