import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../nucleo/donadores_extra.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/premium.dart';
import '../paginas/donar.dart';
import '../paginas/perfil_comun.dart' show socialDe, textoSinConexion;
import '../servicios.dart';
import '../tema.dart';
import 'candado_donador.dart';
import 'letra_escena.dart';
import 'pared_pagina.dart';

/// Explica, con un toque sobre algo bloqueado, qué es y cómo conseguirlo (con «Donar aquí» a la mano).
Future<void> explicarBloqueo(BuildContext context, String titulo, String texto) => showDialog<void>(
      context: context,
      builder: (c) => AlertDialog(
        icon: const Icon(Icons.lock_rounded, color: oroDonador),
        title: Text(titulo, textAlign: TextAlign.center),
        content: Text(texto, textAlign: TextAlign.center),
        actions: [
          TextButton(onPressed: () => Navigator.of(c).pop(), child: const Text('Entendido')),
          FilledButton.icon(
            onPressed: () {
              Navigator.of(c).pop();
              mostrarDonar(context);
            },
            icon: const Icon(Icons.favorite_rounded, size: 18),
            label: const Text('Donar aquí'),
          ),
        ],
      ),
    );

const textoSoloDonadores =
    'Es para donadores y fundadores de Caudal (el código de prueba no cuenta). Dona con Yape desde «Donar aquí» '
    'y en cuanto se confirme se desbloquea.';

/// «Más para donadores»: la letra con efectos, la pared de agradecimiento y la mascota propia.
/// Sin beneficios todo se ve con candado y un toque explica cómo conseguirlo.
class MasParaDonadores extends StatefulWidget {
  const MasParaDonadores({super.key, this.abrirEnlace});

  /// Para las pruebas: qué hacer con el enlace de WhatsApp (si no, se abre la app).
  final Future<bool> Function(Uri)? abrirEnlace;

  @override
  State<MasParaDonadores> createState() => _MasParaDonadoresState();
}

class _MasParaDonadoresState extends State<MasParaDonadores> {
  bool _guardando = false;

  String get _usuario {
    try {
      return Caudal.leer(context).cuenta.usuario;
    } catch (_) {
      return '';
    }
  }

  void _aviso(String t) {
    try {
      Caudal.leer(context).avisar(t);
    } catch (_) {}
  }

  Future<void> _letra() async {
    if (!Premium.i.activo) {
      return explicarBloqueo(context, 'Letra con efectos',
          'El verso que suena, enorme y con efectos de entrada y el brillo de la carátula. Es para donadores: '
          'dona con Yape o canjea un código de prueba.');
    }
    await LetraEscenaPagina.abrirActual(context);
  }

  Future<void> _pared(bool valor) async {
    if (!Premium.i.donaDeVerdad) {
      return explicarBloqueo(context, 'Pared de agradecimiento', textoSoloDonadores);
    }
    final social = socialDe(context);
    if (social == null) return _aviso(textoSinConexion(context));
    setState(() => _guardando = true);
    try {
      await Premium.i.guardarEnPared(social, valor);
      _aviso(valor ? 'Listo: apareces en la pared de agradecimiento.' : 'Ya no apareces en la pared.');
    } on ErrorNube catch (e) {
      _aviso(e.mensaje);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  Future<void> _mascota() async {
    if (!Premium.i.donaDeVerdad) {
      return explicarBloqueo(context, 'Tu propia mascota', textoSoloDonadores);
    }
    final enlace = MascotaPropia.enlace(_usuario);
    var ok = false;
    try {
      ok = await (widget.abrirEnlace ?? (u) => launchUrl(u, mode: LaunchMode.externalApplication))(enlace);
    } catch (_) {}
    if (!ok) _aviso('No pude abrir WhatsApp. Escribe al +51 902 464 984 y cuéntanos tu idea.');
  }

  Widget _candado(bool bloqueado) =>
      bloqueado ? const Icon(Icons.lock_rounded, size: 18, color: oroDonador) : const Icon(Icons.chevron_right_rounded);

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: Premium.i,
        builder: (context, _) {
          final activo = Premium.i.activo;
          final dona = Premium.i.donaDeVerdad;
          return Material(
            color: C.superficie2,
            clipBehavior: Clip.antiAlias,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: C.borde)),
            child: Column(children: [
              ListTile(
                leading: const Icon(Icons.auto_awesome_rounded),
                title: const Text('Letra con efectos', style: TextStyle(fontWeight: FontWeight.w800)),
                subtitle: const Text('El verso que suena, enorme, con estilos Resplandor, Ola, Neón y Cine.'),
                trailing: _candado(!activo),
                onTap: _letra,
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(Icons.volunteer_activism_rounded),
                title: const Text('Aparecer en la pared de agradecimiento', style: TextStyle(fontWeight: FontWeight.w800)),
                subtitle: const Text('Tu nombre en la lista de quienes apoyan Caudal, en la app y en la web. '
                    'Solo aparecen donadores y fundadores mayores de 18 años (la prueba no cuenta).'),
                trailing: dona
                    ? Switch(
                        value: Premium.i.enPared,
                        onChanged: _guardando ? null : _pared,
                      )
                    : _candado(true),
                onTap: dona ? (_guardando ? null : () => _pared(!Premium.i.enPared)) : () => _pared(true),
              ),
              Align(
                alignment: Alignment.centerLeft,
                child: Padding(
                  padding: const EdgeInsets.only(left: 56, bottom: 6),
                  child: TextButton(onPressed: () => ParedPagina.abrir(context), child: const Text('Ver la pared')),
                ),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(Icons.pets_rounded),
                title: const Text('Quiero mi propia mascota', style: TextStyle(fontWeight: FontWeight.w800)),
                subtitle: const Text(MascotaPropia.explicacion),
                trailing: dona ? const Icon(Icons.chat_rounded) : _candado(true),
                onTap: _mascota,
              ),
            ]),
          );
        },
      );
}
