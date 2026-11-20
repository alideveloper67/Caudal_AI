// «Volver a una versión anterior» (Android, versión directa).
//
// Android no deja instalar una versión más vieja encima de la nueva: solo se puede
// desinstalando antes. Por eso la pantalla guía los pasos sin perder nada: primero la copia
// de seguridad, luego desinstalar, instalar la versión elegida y recuperar la copia.

import 'package:flutter/material.dart';

import '../../nucleo/version.dart';
import '../plataforma.dart';
import '../tema.dart';
import 'copia_seguridad_pagina.dart';

class VolverVersionPagina extends StatefulWidget {
  const VolverVersionPagina({super.key});

  @override
  State<VolverVersionPagina> createState() => _VolverVersionPaginaState();
}

class _VolverVersionPaginaState extends State<VolverVersionPagina> {
  List<VersionAnterior>? _lista;
  bool _fallo = false;
  VersionAnterior? _elegida;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() {
      _fallo = false;
      _lista = null;
    });
    final l = await versionesAnteriores();
    if (!mounted) return;
    setState(() {
      _lista = l;
      _fallo = l == null;
      _elegida = (l != null && l.isNotEmpty) ? l.first : null;
    });
  }

  Future<void> _bajar() async {
    final v = _elegida;
    if (v == null) return;
    try {
      await abrirEnNavegador(v.apk);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('No se pudo abrir el navegador.')));
      }
    }
  }

  Widget _paso(int n, String texto) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          CircleAvatar(radius: 12, backgroundColor: C.acento,
              child: Text('$n', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Colors.black))),
          const SizedBox(width: 12),
          Expanded(child: Text(texto, style: const TextStyle(color: C.texto2, height: 1.4))),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final l = _lista;
    return Scaffold(
      appBar: AppBar(title: const Text('Volver a una versión anterior')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        Text('Tienes la $versionApp. Si algo falla en ella, puedes volver a una anterior '
            'sin perder tus listas ni tus «me gusta».', style: estiloSecundario),
        const SizedBox(height: 18),
        if (l == null && !_fallo)
          const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator.adaptive())),
        if (_fallo) ...[
          const Text('No se pudo preguntar por las versiones. Revisa tu internet.',
              style: TextStyle(color: C.error)),
          const SizedBox(height: 8),
          Align(alignment: Alignment.centerLeft,
              child: TextButton(onPressed: _cargar, child: const Text('Reintentar'))),
        ],
        if (l != null && l.isEmpty)
          const Text('No hay versiones anteriores publicadas.', style: estiloSecundario),
        if (l != null && l.isNotEmpty) ...[
          const Text('Elige la versión', style: estiloTituloSeccion),
          const SizedBox(height: 6),
          Material(
            color: Colors.transparent,
            child: RadioGroup<VersionAnterior>(
              groupValue: _elegida,
              onChanged: (x) => setState(() => _elegida = x),
              child: Column(children: [
                for (final v in l)
                  RadioListTile<VersionAnterior>(
                    value: v,
                    title: Text('Caudal ${v.version}'),
                    subtitle: v.fecha.isEmpty ? null : Text('Publicada el ${v.fecha}', style: estiloSecundario),
                  ),
              ]),
            ),
          ),
          const SizedBox(height: 16),
          const Text('Cómo hacerlo', style: estiloTituloSeccion),
          const SizedBox(height: 10),
          _paso(1, 'Guarda tu copia de seguridad (botón de abajo) y déjala en Descargas o en tu Drive.'),
          _paso(2, 'Baja la versión elegida con «Bajar esta versión».'),
          _paso(3, 'Android no deja instalar una versión más vieja encima: desinstala Caudal '
              '(mantén pulsado su icono → Desinstalar).'),
          _paso(4, 'Abre el archivo que bajaste para instalarlo y, en Ajustes → Copia de seguridad, '
              'recupera tu copia.'),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const CopiaSeguridadPagina())),
            icon: const Icon(Icons.save_alt_rounded),
            label: const Text('Guardar mi copia de seguridad'),
            style: OutlinedButton.styleFrom(shape: const StadiumBorder()),
          ),
          const SizedBox(height: 10),
          FilledButton.icon(
            onPressed: _elegida == null ? null : _bajar,
            icon: const Icon(Icons.download_rounded),
            label: Text(_elegida == null ? 'Bajar esta versión' : 'Bajar Caudal ${_elegida!.version}'),
            style: FilledButton.styleFrom(shape: const StadiumBorder()),
          ),
        ],
      ]),
    );
  }
}
