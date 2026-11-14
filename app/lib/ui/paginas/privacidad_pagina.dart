import 'dart:io';

import 'package:flutter/material.dart';

import '../../nucleo/legal.dart';
import '../../nucleo/nube.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'legal_pagina.dart';

/// Ajustes → Privacidad: tus datos, el permiso de datos anónimos, los textos
/// legales y borrar la cuenta.
class PrivacidadPagina extends StatefulWidget {
  const PrivacidadPagina({super.key});

  @override
  State<PrivacidadPagina> createState() => _PrivacidadPaginaState();
}

class _PrivacidadPaginaState extends State<PrivacidadPagina> {
  PerfilLegal? _perfil;
  String? _error;

  Sesion? get _sesion {
    final s = Caudal.leer(context).cuenta.sesion;
    return s == null || s.acceso.isEmpty ? null : s;
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
  }

  Future<void> _cargar() async {
    final s = _sesion;
    if (s == null) {
      setState(() => _error = 'Sin conexión: vuelve cuando tengas internet.');
      return;
    }
    try {
      final p = await PerfilLegal.de(s);
      if (mounted) setState(() => _perfil = p);
    } catch (_) {
      if (mounted) setState(() => _error = 'No se pudo cargar. Revisa tu internet.');
    }
  }

  Future<void> _compartir(bool v) async {
    final s = _sesion;
    if (s == null) return;
    final antes = _perfil!;
    setState(() => _perfil = PerfilLegal(version: antes.version, comparte: v, nacimiento: antes.nacimiento,
        pais: antes.pais, genero: antes.genero, nombre: antes.nombre));
    try {
      await PerfilLegal.compartir(s, v);
      if (mounted) Caudal.leer(context).avisar(v ? 'Gracias: tus datos anónimos ayudan a entender la música.'
          : 'Listo: tus datos ya no entran en las estadísticas.');
    } catch (_) {
      if (mounted) {
        setState(() => _perfil = antes);
        Caudal.leer(context).avisar('No se pudo guardar. Revisa tu internet.');
      }
    }
  }

  Future<void> _editarDatos() async {
    final s = _sesion;
    final p = _perfil;
    if (s == null || p == null) return;
    final ok = await Navigator.of(context).push<bool>(MaterialPageRoute(
        builder: (_) => _EditarDatosPagina(sesion: s, perfil: p)));
    if (ok == true) _cargar();
  }

  Future<void> _eliminar() async {
    final s = Caudal.leer(context);
    final sesion = _sesion;
    if (sesion == null) return;
    final escrito = await pedirTexto(context,
        'Para borrar tu cuenta y TODOS tus datos para siempre, escribe tu usuario: ${s.cuenta.usuario}', '');
    if (escrito == null || !mounted) return;
    if (escrito.trim().toLowerCase().replaceFirst('@', '') != s.cuenta.usuario.toLowerCase()) {
      s.avisar('El usuario no coincide. No se ha borrado nada.');
      return;
    }
    try {
      await PerfilLegal.eliminarCuenta(sesion);
    } catch (e) {
      s.avisar(e is ErrorNube ? e.mensaje : 'No se pudo borrar. Revisa tu internet.');
      return;
    }
    // la biblioteca de este teléfono tampoco se queda
    final ruta = s.coleccion.ruta;
    await s.cerrarSesion();
    Future.delayed(const Duration(seconds: 2), () async {
      for (final f in [ruta, '$ruta-wal', '$ruta-shm']) {
        try {
          await File(f).delete();
        } catch (_) {}
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final p = _perfil;
    return Scaffold(
      appBar: AppBar(title: const Text('Privacidad')),
      body: ListView(children: [
        if (_error != null)
          Padding(padding: const EdgeInsets.all(Esp.lado), child: Text(_error!, style: const TextStyle(color: C.error))),
        ListTile(
          leading: const Icon(Icons.badge_outlined, color: C.texto2),
          title: const Text('Tus datos'),
          subtitle: Text(p == null
              ? 'Cargando…'
              : [
                  if (p.nombre.isNotEmpty) p.nombre,
                  if (p.nacimiento != null) '${Legal.edad(p.nacimiento!)} años',
                  if (p.pais != null) Legal.paises[p.pais] ?? p.pais!,
                ].join(' · '), style: estiloSecundario),
          trailing: const Icon(Icons.chevron_right_rounded, color: C.texto3),
          onTap: p == null ? null : _editarDatos,
        ),
        SwitchListTile(
          value: p?.comparte ?? false,
          onChanged: p == null ? null : _compartir,
          secondary: const Icon(Icons.insights_rounded, color: C.texto2),
          title: const Text('Compartir mis datos de uso anónimos'),
          subtitle: const Text('Estadísticas de grupos grandes (qué música se escucha y cuánto), sin tu nombre ni '
              'nada que te identifique. Opcional.', style: estiloSecundario),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.description_outlined, color: C.texto2),
          title: const Text('Términos y condiciones'),
          onTap: () => LegalPagina.abrir(context, 'terminos'),
        ),
        ListTile(
          leading: const Icon(Icons.privacy_tip_outlined, color: C.texto2),
          title: const Text('Política de privacidad'),
          onTap: () => LegalPagina.abrir(context, 'privacidad'),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.delete_forever_rounded, color: C.error),
          title: const Text('Eliminar mi cuenta', style: TextStyle(color: C.error, fontWeight: FontWeight.w700)),
          subtitle: const Text('Se borra tu cuenta y todo lo que guarda. No se puede deshacer.', style: estiloSecundario),
          onTap: _sesion == null ? null : _eliminar,
        ),
      ]),
    );
  }
}

class _EditarDatosPagina extends StatefulWidget {
  const _EditarDatosPagina({required this.sesion, required this.perfil});
  final Sesion sesion;
  final PerfilLegal perfil;

  @override
  State<_EditarDatosPagina> createState() => _EditarDatosPaginaState();
}

class _EditarDatosPaginaState extends State<_EditarDatosPagina> {
  late final _nombre = TextEditingController(text: widget.perfil.nombre);
  final _datos = DatosPerfil();
  bool _ocupado = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _datos.nacimiento = widget.perfil.nacimiento;
    _datos.pais = widget.perfil.pais ?? 'PE';
    _datos.genero = widget.perfil.genero;
  }

  @override
  void dispose() {
    _nombre.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    final e = Legal.revisarPerfil(nombre: _nombre.text, nacimiento: _datos.nacimiento, pais: _datos.pais,
        permisoTutor: _datos.permisoTutor);
    if (e != null) return setState(() => _error = e);
    setState(() => _ocupado = true);
    try {
      await PerfilLegal.completar(widget.sesion, nombre: _nombre.text, nacimiento: _datos.nacimiento!,
          pais: _datos.pais!, genero: _datos.genero, permisoTutor: _datos.permisoTutor);
      if (mounted) Navigator.of(context).pop(true);
    } catch (_) {
      if (mounted) {
        setState(() {
          _ocupado = false;
          _error = 'No se pudo guardar. Revisa tu internet.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Tus datos')),
        body: ListView(padding: const EdgeInsets.all(Esp.lado), children: [
          TextField(
            controller: _nombre,
            textCapitalization: TextCapitalization.words,
            decoration: InputDecoration(
              labelText: 'Tu nombre y apellido',
              prefixIcon: const Icon(Icons.badge_outlined, color: C.texto3),
              filled: true, fillColor: C.superficie2,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
          const SizedBox(height: 12),
          CamposPerfil(datos: _datos, alCambiar: () => setState(() => _error = null)),
          if (_error != null) ...[
            const SizedBox(height: 10),
            Text(_error!, style: const TextStyle(color: C.error)),
          ],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _ocupado ? null : _guardar,
            style: FilledButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto,
                minimumSize: const Size.fromHeight(50), shape: const StadiumBorder()),
            child: const Text('Guardar', style: TextStyle(fontWeight: FontWeight.w800)),
          ),
        ]),
      );
}
