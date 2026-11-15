import 'package:flutter/material.dart';

import '../../nucleo/nube.dart';
import '../../nucleo/social.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'perfil_comun.dart';

/// «Revisión de música»: solo para moderadores. Lista lo que está esperando
/// aprobación para escucharlo y aprobarlo o rechazarlo (con motivo).
class RevisionPagina extends StatefulWidget {
  const RevisionPagina({super.key});

  /// Motivos rápidos para rechazar.
  static const motivos = ['No es tuya', 'Mala calidad', 'Contenido inadecuado', 'Duplicada'];

  @override
  State<RevisionPagina> createState() => _RevisionPaginaState();
}

class _RevisionPaginaState extends State<RevisionPagina> {
  Social? _social;
  List<SubidaRevision>? _lista;
  Object? _error;
  final Set<String> _ocupadas = {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _social = socialDe(context);
      _cargar();
    });
  }

  Future<void> _cargar() async {
    final social = _social;
    if (social == null) {
      setState(() => _error = const SinConexion());
      return;
    }
    try {
      final l = await social.revisionPendientes();
      if (mounted) {
        setState(() {
          _lista = l;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  Future<void> _decidir(SubidaRevision r, bool aprobar) async {
    final social = _social;
    final s = Caudal.leer(context);
    if (social == null || _ocupadas.contains(r.subida.id)) return;
    var nota = '';
    if (!aprobar) {
      final n = await pedirMotivoRechazo(context, r.subida.tituloVisible);
      if (n == null) return;
      nota = n;
    }
    setState(() => _ocupadas.add(r.subida.id));
    try {
      await social.revisionResolver(r.subida.id, aprobar, nota: nota);
      if (s.reproductor.actual?['subida_id'] == r.subida.id) await s.reproductor.detener();
      s.avisar(aprobar ? 'Aprobada: ya está en la comunidad.' : 'Rechazada. Quien la subió verá el motivo.');
      if (mounted) setState(() => _lista = _lista?.where((x) => x.subida.id != r.subida.id).toList());
    } catch (e) {
      s.avisar(Social.error(e));
      _cargar();
    } finally {
      if (mounted) setState(() => _ocupadas.remove(r.subida.id));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = _lista;
    return Scaffold(
      appBar: AppBar(title: const Text('Revisión de música', style: estiloTituloBarra)),
      body: _error != null && l == null
          ? errorAmable(_error!, _cargar)
          : l == null
              ? const Center(child: CircularProgressIndicator())
              : l.isEmpty
                  ? RefreshIndicator(
                      onRefresh: _cargar,
                      child: ListView(children: const [
                        SizedBox(height: 60),
                        Vacio(
                          icono: Icons.verified_rounded,
                          titulo: 'No hay nada por revisar',
                          texto: 'Cuando alguien suba una canción, aparecerá aquí para que la apruebes o la rechaces.',
                        ),
                      ]),
                    )
                  : RefreshIndicator(
                      onRefresh: _cargar,
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, 120),
                        itemCount: l.length,
                        itemBuilder: (_, i) => Entrada(
                          indice: i % 6,
                          child: TarjetaRevision(
                            revision: l[i],
                            ocupada: _ocupadas.contains(l[i].subida.id),
                            alAprobar: () => _decidir(l[i], true),
                            alRechazar: () => _decidir(l[i], false),
                            alReproducir: () => reproducirSubida(context, null, [l[i].subida], 0),
                            alAbrirPerfil: l[i].subida.usuario.isEmpty ? null : () => abrirPerfil(context, l[i].subida.usuario),
                          ),
                        ),
                      ),
                    ),
    );
  }
}

/// Cuadro para escribir (o elegir) el motivo del rechazo. `null` = cancelar.
Future<String?> pedirMotivoRechazo(BuildContext context, String titulo) {
  final c = TextEditingController();
  return showDialog<String>(
    context: context,
    useRootNavigator: true,
    builder: (ctx) => AlertDialog(
      backgroundColor: C.superficie2,
      title: Text('Rechazar «$titulo»'),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Quien la subió verá este motivo.', style: estiloSecundario),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 4, children: [
            for (final m in RevisionPagina.motivos) ActionChip(label: Text(m), onPressed: () => c.text = m),
          ]),
          const SizedBox(height: 10),
          TextField(
            controller: c,
            maxLength: 300,
            maxLines: 2,
            decoration: InputDecoration(
              hintText: 'Motivo',
              filled: true,
              fillColor: C.superficie3,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: C.error, foregroundColor: Colors.white),
          onPressed: () => Navigator.pop(ctx, c.text.trim().isEmpty ? 'Sin motivo indicado' : c.text.trim()),
          child: const Text('Rechazar'),
        ),
      ],
    ),
  );
}

String _duracion(int seg) => seg <= 0 ? '' : '${seg ~/ 60}:${(seg % 60).toString().padLeft(2, '0')}';

/// Tarjeta de una canción por revisar.
class TarjetaRevision extends StatelessWidget {
  const TarjetaRevision({
    super.key,
    required this.revision,
    required this.alAprobar,
    required this.alRechazar,
    required this.alReproducir,
    this.alAbrirPerfil,
    this.ocupada = false,
  });
  final SubidaRevision revision;
  final VoidCallback alAprobar;
  final VoidCallback alRechazar;
  final VoidCallback alReproducir;
  final VoidCallback? alAbrirPerfil;
  final bool ocupada;

  @override
  Widget build(BuildContext context) {
    final r = revision;
    final x = r.subida;
    final datos = [
      if (x.artista.trim().isNotEmpty) x.artista.trim(),
      if (x.album.trim().isNotEmpty) x.album.trim(),
      if (_duracion(x.duracion).isNotEmpty) _duracion(x.duracion),
    ].join(' · ');
    return Container(
      margin: const EdgeInsets.only(bottom: Esp.m),
      padding: const EdgeInsets.all(Esp.m),
      decoration: BoxDecoration(
        color: C.superficie,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: r.reportes > 0 ? const Color(0xFFFF7A7A).withValues(alpha: 0.5) : C.borde),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Stack(alignment: Alignment.center, children: [
            Portada(url: x.urlPortada, lado: 110, radio: 14),
            IconButton.filled(
              tooltip: 'Escuchar ${x.tituloVisible}',
              style: IconButton.styleFrom(backgroundColor: Colors.black54, foregroundColor: Colors.white),
              icon: const Icon(Icons.play_arrow_rounded, size: 30),
              onPressed: alReproducir,
            ),
          ]),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(x.tituloVisible, maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 16.5, fontWeight: FontWeight.w800, height: 1.2)),
              if (datos.isNotEmpty) Padding(
                padding: const EdgeInsets.only(top: 3),
                child: Text(datos, maxLines: 2, overflow: TextOverflow.ellipsis, style: estiloSecundario),
              ),
              const SizedBox(height: 6),
              InkWell(
                onTap: alAbrirPerfil,
                child: Text('Subida por ${r.quien.isEmpty ? 'alguien' : r.quien}${x.usuario.isEmpty ? '' : ' (@${x.usuario})'}',
                    maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12.5, color: C.acento, fontWeight: FontWeight.w600)),
              ),
              if (r.tamano > 0)
                Text('${(r.tamano / 1048576).toStringAsFixed(1)} MB', style: estiloDetalle),
            ]),
          ),
        ]),
        if (r.reportes > 0) ...[
          const SizedBox(height: 10),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
                color: const Color(0xFFFF7A7A).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${r.reportes} ${r.reportes == 1 ? 'reporte' : 'reportes'}',
                  style: const TextStyle(fontWeight: FontWeight.w800, color: Color(0xFFFF9A9A), fontSize: 13)),
              for (final m in r.motivos) Text('• $m', style: estiloSecundario),
            ]),
          ),
        ],
        const SizedBox(height: 12),
        Row(children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: ocupada ? null : alRechazar,
              icon: const Icon(Icons.close_rounded, size: 18),
              label: const Text('Rechazar'),
              style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFFF9A9A), shape: const StadiumBorder(),
                  side: BorderSide(color: C.error.withValues(alpha: 0.6)), minimumSize: const Size(0, 44)),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: FilledButton.icon(
              onPressed: ocupada ? null : alAprobar,
              icon: ocupada
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.check_rounded, size: 18),
              label: const Text('Aprobar'),
              style: FilledButton.styleFrom(
                  backgroundColor: C.exito, foregroundColor: Colors.black, shape: const StadiumBorder(),
                  minimumSize: const Size(0, 44)),
            ),
          ),
        ]),
      ]),
    );
  }
}
