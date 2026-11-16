import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import '../../nucleo/legal.dart';
import '../../nucleo/nube.dart';
import '../tema.dart';

/// Muestra los Términos o la Política de privacidad.
class LegalPagina extends StatelessWidget {
  const LegalPagina({super.key, required this.nombre});

  /// 'terminos' o 'privacidad'.
  final String nombre;

  static void abrir(BuildContext context, String nombre) => Navigator.of(context, rootNavigator: true)
      .push(MaterialPageRoute(builder: (_) => LegalPagina(nombre: nombre)));

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(nombre == 'terminos' ? 'Términos y condiciones' : 'Política de privacidad')),
        body: FutureBuilder<String>(
          future: Legal.texto(nombre),
          builder: (_, s) {
            if (!s.hasData) return const Center(child: CircularProgressIndicator());
            return ListView(
              padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, 48),
              children: [for (final w in pintarMarkdown(s.data!)) w],
            );
          },
        ),
      );
}

/// Markdown sencillo de los textos legales: títulos, listas y negritas.
List<Widget> pintarMarkdown(String md) {
  TextSpan conNegritas(String l, TextStyle base) {
    final partes = <TextSpan>[];
    final r = RegExp(r'\*\*(.+?)\*\*');
    var i = 0;
    for (final m in r.allMatches(l)) {
      if (m.start > i) partes.add(TextSpan(text: l.substring(i, m.start)));
      partes.add(TextSpan(text: m.group(1), style: const TextStyle(fontWeight: FontWeight.w800, color: C.texto)));
      i = m.end;
    }
    if (i < l.length) partes.add(TextSpan(text: l.substring(i)));
    return TextSpan(style: base, children: partes);
  }

  const cuerpo = TextStyle(fontSize: 15, height: 1.5, color: C.texto2);
  final salida = <Widget>[];
  for (final linea in md.split('\n')) {
    final l = linea.trimRight();
    if (l.isEmpty) continue;
    if (l.startsWith('# ')) {
      salida.add(Padding(padding: const EdgeInsets.only(bottom: 4),
          child: Text(l.substring(2), style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900, height: 1.15))));
    } else if (l.startsWith('## ')) {
      salida.add(Padding(padding: const EdgeInsets.only(top: 22, bottom: 6),
          child: Text(l.substring(3), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800))));
    } else if (l.startsWith('- ')) {
      salida.add(Padding(
        padding: const EdgeInsets.only(left: 6, bottom: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('•  ', style: cuerpo),
          Expanded(child: Text.rich(conNegritas(l.substring(2), cuerpo))),
        ]),
      ));
    } else {
      salida.add(Padding(padding: const EdgeInsets.only(bottom: 10), child: Text.rich(conNegritas(l, cuerpo))));
    }
  }
  return salida;
}

// ============================================================ datos del perfil

/// Los datos básicos que se piden al registrarse (y a las cuentas de antes).
class DatosPerfil {
  DateTime? nacimiento;
  String? pais = 'PE';
  String? genero;
  bool permisoTutor = false;

  int? get edad => nacimiento == null ? null : Legal.edad(nacimiento!);
  bool get menor => (edad ?? 99) < Legal.edadMinima;
}

class CamposPerfil extends StatefulWidget {
  const CamposPerfil({super.key, required this.datos, required this.alCambiar});
  final DatosPerfil datos;
  final VoidCallback alCambiar;

  @override
  State<CamposPerfil> createState() => _CamposPerfilState();
}

class _CamposPerfilState extends State<CamposPerfil> {
  DatosPerfil get d => widget.datos;

  void _cambio(VoidCallback f) {
    setState(f);
    widget.alCambiar();
  }

  // la fecha se elige con tres listas: el calendario con teclado fallaba
  // al borrar las barras en algunos telefonos
  int? _dia, _mes, _anio;

  @override
  void initState() {
    super.initState();
    final n = d.nacimiento;
    if (n != null) {
      _dia = n.day;
      _mes = n.month;
      _anio = n.year;
    }
  }

  static const _meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
    'septiembre', 'octubre', 'noviembre', 'diciembre'];

  void _fecha({int? dia, int? mes, int? anio}) {
    _cambio(() {
      _dia = dia ?? _dia;
      _mes = mes ?? _mes;
      _anio = anio ?? _anio;
      if (_dia != null && _mes != null && _anio != null) {
        final ultimo = DateTime(_anio!, _mes! + 1, 0).day;
        if (_dia! > ultimo) _dia = ultimo;
        d.nacimiento = DateTime(_anio!, _mes!, _dia!);
      } else {
        d.nacimiento = null;
      }
    });
  }

  Widget _lista<T>(String texto, T? valor, List<(T, String)> opciones, ValueChanged<T?> alCambiar) =>
      DropdownButtonFormField<T>(
        initialValue: valor,
        isExpanded: true,
        menuMaxHeight: 320,
        decoration: InputDecoration(
          labelText: texto,
          filled: true,
          fillColor: C.superficie2,
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        ),
        items: [for (final (v, t) in opciones) DropdownMenuItem(value: v, child: Text(t, overflow: TextOverflow.ellipsis))],
        onChanged: alCambiar,
      );

  InputDecoration _deco(String texto, IconData icono) => InputDecoration(
        labelText: texto,
        prefixIcon: Icon(icono, color: C.texto3),
        filled: true,
        fillColor: C.superficie2,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      );

  @override
  Widget build(BuildContext context) {
    final n = d.nacimiento;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Padding(
        padding: const EdgeInsets.only(left: 4, bottom: 6),
        child: Row(children: [
          const Icon(Icons.cake_outlined, size: 18, color: C.texto3),
          const SizedBox(width: 6),
          Flexible(
            child: Text(n == null ? 'Fecha de nacimiento' : 'Fecha de nacimiento · ${d.edad} años',
                style: const TextStyle(fontSize: 13, color: C.texto2)),
          ),
        ]),
      ),
      Row(children: [
        Expanded(flex: 4, child: _lista<int>('Día', _dia, [for (var i = 1; i <= 31; i++) (i, '$i')],
            (v) => _fecha(dia: v))),
        const SizedBox(width: 8),
        Expanded(flex: 6, child: _lista<int>('Mes', _mes, [for (var i = 1; i <= 12; i++) (i, _meses[i - 1])],
            (v) => _fecha(mes: v))),
        const SizedBox(width: 8),
        Expanded(flex: 5, child: _lista<int>('Año', _anio,
            [for (var a = DateTime.now().year; a >= 1920; a--) (a, '$a')], (v) => _fecha(anio: v))),
      ]),
      if (d.menor) ...[
        const SizedBox(height: 6),
        CheckboxListTile(
          value: d.permisoTutor,
          onChanged: (v) => _cambio(() => d.permisoTutor = v ?? false),
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          title: const Text('Soy la madre, el padre o el tutor y doy permiso para que use Caudal',
              style: TextStyle(fontSize: 14)),
          subtitle: Text('Es obligatorio para menores de ${Legal.edadMinima} años', style: estiloDetalle),
        ),
      ],
      const SizedBox(height: 12),
      DropdownButtonFormField<String>(
        initialValue: d.pais,
        isExpanded: true,
        decoration: _deco('País', Icons.public_rounded),
        items: [for (final e in Legal.paises.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
        onChanged: (v) => _cambio(() => d.pais = v),
      ),
      const SizedBox(height: 12),
      DropdownButtonFormField<String>(
        initialValue: d.genero,
        isExpanded: true,
        decoration: _deco('Género (opcional)', Icons.person_outline_rounded),
        items: [for (final e in Legal.generos.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
        onChanged: (v) => _cambio(() => d.genero = v),
      ),
    ]);
  }
}

/// La casilla obligatoria de los términos y la opcional de los datos anónimos.
class CasillasLegales extends StatelessWidget {
  const CasillasLegales({super.key, required this.acepta, required this.comparte,
      required this.alAceptar, required this.alCompartir});
  final bool acepta;
  final bool comparte;
  final ValueChanged<bool> alAceptar;
  final ValueChanged<bool> alCompartir;

  @override
  Widget build(BuildContext context) {
    final enlace = TextStyle(color: C.acento, fontWeight: FontWeight.w700, decoration: TextDecoration.underline);
    return Column(children: [
      CheckboxListTile(
        value: acepta,
        onChanged: (v) => alAceptar(v ?? false),
        contentPadding: EdgeInsets.zero,
        controlAffinity: ListTileControlAffinity.leading,
        title: Text.rich(TextSpan(style: const TextStyle(fontSize: 14, color: C.texto), children: [
          const TextSpan(text: 'He leído y acepto los '),
          TextSpan(text: 'Términos y condiciones', style: enlace,
              recognizer: TapGestureRecognizer()..onTap = () => LegalPagina.abrir(context, 'terminos')),
          const TextSpan(text: ' y la '),
          TextSpan(text: 'Política de privacidad', style: enlace,
              recognizer: TapGestureRecognizer()..onTap = () => LegalPagina.abrir(context, 'privacidad')),
          const TextSpan(text: '.'),
        ])),
      ),
      CheckboxListTile(
        value: comparte,
        onChanged: (v) => alCompartir(v ?? false),
        contentPadding: EdgeInsets.zero,
        controlAffinity: ListTileControlAffinity.leading,
        title: const Text('Compartir mis datos de uso anónimos (opcional)', style: TextStyle(fontSize: 14)),
        subtitle: const Text('Qué música se escucha y cuánto, en estadísticas de grupos grandes, sin tu nombre. '
            'Lo puedes quitar cuando quieras en Ajustes.', style: estiloDetalle),
      ),
    ]);
  }
}

// ============================================================ cuentas de antes

/// Para cuentas que aún no aceptaron esta versión de los textos o a las que
/// les faltan los datos básicos. No se puede saltar (sí cerrar sesión).
class AceptarTerminosPagina extends StatefulWidget {
  const AceptarTerminosPagina({super.key, required this.sesion, required this.perfil, required this.alSalir});
  final Sesion sesion;
  final PerfilLegal perfil;
  final VoidCallback alSalir;

  @override
  State<AceptarTerminosPagina> createState() => _AceptarTerminosPaginaState();
}

class _AceptarTerminosPaginaState extends State<AceptarTerminosPagina> {
  late final _nombre = TextEditingController(text: widget.perfil.nombre);
  final _datos = DatosPerfil();
  bool _acepta = false;
  late bool _comparte = widget.perfil.comparte;
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

  Future<void> _continuar() async {
    if (!_acepta) return setState(() => _error = 'Para seguir usando Caudal tienes que aceptar los términos.');
    final faltan = !widget.perfil.completo;
    if (faltan) {
      final e = Legal.revisarPerfil(nombre: _nombre.text, nacimiento: _datos.nacimiento, pais: _datos.pais,
          permisoTutor: _datos.permisoTutor);
      if (e != null) return setState(() => _error = e);
    }
    setState(() {
      _ocupado = true;
      _error = null;
    });
    try {
      if (faltan) {
        await PerfilLegal.completar(widget.sesion, nombre: _nombre.text, nacimiento: _datos.nacimiento!,
            pais: _datos.pais!, genero: _datos.genero, permisoTutor: _datos.permisoTutor);
      }
      await PerfilLegal.aceptar(widget.sesion, comparte: _comparte);
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        setState(() {
          _ocupado = false;
          _error = e is ErrorNube ? e.mensaje : 'No se pudo guardar. Revisa tu internet.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final faltan = !widget.perfil.completo;
    return PopScope(
      canPop: false,
      child: Scaffold(
        body: SafeArea(
          child: Center(child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: ListView(padding: const EdgeInsets.all(24), children: [
            Icon(Icons.verified_user_outlined, size: 48, color: C.acento),
            const SizedBox(height: 14),
            Text(widget.perfil.version == null ? 'Antes de seguir' : 'Hemos actualizado nuestros términos',
                style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900, height: 1.15)),
            const SizedBox(height: 8),
            Text(faltan
                ? 'Necesitamos unos datos básicos para comprobar tu edad, y que aceptes los términos y la '
                    'política de privacidad. Solo te lo pedimos una vez.'
                : 'Léelos y acéptalos para seguir usando Caudal.', style: estiloSecundario),
            const SizedBox(height: 20),
            if (faltan) ...[
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
              const SizedBox(height: 8),
            ],
            CasillasLegales(acepta: _acepta, comparte: _comparte,
                alAceptar: (v) => setState(() {
                  _acepta = v;
                  _error = null;
                }),
                alCompartir: (v) => setState(() => _comparte = v)),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: C.error, fontWeight: FontWeight.w600)),
            ],
            const SizedBox(height: 18),
            FilledButton(
              onPressed: _ocupado ? null : _continuar,
              style: FilledButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto,
                  minimumSize: const Size.fromHeight(52), shape: const StadiumBorder()),
              child: _ocupado
                  ? SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5, color: C.acentoTexto))
                  : const Text('Aceptar y continuar', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
            ),
            const SizedBox(height: 8),
            TextButton(onPressed: _ocupado ? null : widget.alSalir, child: const Text('Cerrar sesión')),
          ]),
          )),
        ),
      ),
    );
  }
}
