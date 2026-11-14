import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../nucleo/cuentas.dart';
import '../comunes.dart';
import '../tema.dart';

/// Entrar o crear la cuenta (la misma que en Caudal para Windows).
class AccesoPagina extends StatefulWidget {
  const AccesoPagina({super.key, required this.alEntrar});
  final Future<void> Function(Cuenta cuenta, bool recordar) alEntrar;

  @override
  State<AccesoPagina> createState() => _AccesoPaginaState();
}

class _AccesoPaginaState extends State<AccesoPagina> with SingleTickerProviderStateMixin {
  bool _registro = false;
  bool _recordar = true;
  bool _ocupado = false;
  bool _verClave = false;
  String? _error;
  final _usuario = TextEditingController();
  final _nombre = TextEditingController();
  final _clave = TextEditingController();
  final _clave2 = TextEditingController();
  late final AnimationController _brillo =
      AnimationController(vsync: this, duration: const Duration(seconds: 14))..repeat();

  @override
  void initState() {
    super.initState();
    Cuentas.ultimoUsuario().then((u) {
      if (!mounted) return;
      if (u.isEmpty) {
        setState(() => _registro = true);
      } else {
        _usuario.text = u;
      }
    });
  }

  @override
  void dispose() {
    _brillo.dispose();
    for (final c in [_usuario, _nombre, _clave, _clave2]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _enviar() async {
    FocusScope.of(context).unfocus();
    final usuario = _usuario.text.trim().toLowerCase();
    if (usuario.isEmpty || _clave.text.isEmpty) {
      return setState(() => _error = 'Escribe tu usuario y tu contraseña.');
    }
    if (_registro && _clave.text != _clave2.text) {
      return setState(() => _error = 'Las dos contraseñas no coinciden.');
    }
    setState(() {
      _ocupado = true;
      _error = null;
    });
    try {
      final c = _registro
          ? await Cuentas.crear(usuario, _clave.text, _nombre.text.trim())
          : await Cuentas.entrar(usuario, _clave.text);
      HapticFeedback.mediumImpact();
      await widget.alEntrar(c, _recordar);
    } catch (e) {
      if (mounted) {
        setState(() {
          _ocupado = false;
          _error = '$e';
        });
      }
    }
  }

  InputDecoration _deco(String texto, IconData icono, {Widget? sufijo}) => InputDecoration(
        hintText: texto,
        prefixIcon: Icon(icono, color: C.texto3),
        suffixIcon: sufijo,
        filled: true,
        fillColor: C.superficie2,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: C.acento, width: 1.5)),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C.fondo,
      body: Stack(children: [
        // fondo vivo: dos luces que se mueven despacio
        AnimatedBuilder(
          animation: _brillo,
          builder: (_, _) {
            final t = _brillo.value * 6.283;
            return DecoratedBox(
              decoration: BoxDecoration(gradient: RadialGradient(
                center: Alignment(0.7 * _seno(t), -0.75 + 0.15 * _seno(t * 2)),
                radius: 1.1,
                colors: const [Color(0x5522D3EE), Color(0x227C5CFF), Colors.transparent],
                stops: const [0, 0.45, 1],
              )),
              child: const SizedBox.expand(),
            );
          },
        ),
        SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 26, vertical: 24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: AutofillGroup(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    Entrada(child: Center(
                      child: Container(
                        width: 74, height: 74,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(22),
                          gradient: const LinearGradient(colors: [C.acento, C.violeta],
                              begin: Alignment.topLeft, end: Alignment.bottomRight),
                          boxShadow: const [BoxShadow(color: Color(0x5522D3EE), blurRadius: 30, offset: Offset(0, 10))],
                        ),
                        child: const Icon(Icons.waves_rounded, size: 40, color: Colors.white),
                      ),
                    )),
                    const SizedBox(height: 18),
                    const Entrada(indice: 1, child: Text('Caudal', textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 34, fontWeight: FontWeight.w900, letterSpacing: -1))),
                    const SizedBox(height: 6),
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 220),
                      child: Text(
                        _registro ? 'Crea tu cuenta: tu música te sigue al teléfono y a la computadora.'
                            : 'Qué bueno verte. Entra para seguir donde lo dejaste.',
                        key: ValueKey(_registro), textAlign: TextAlign.center, style: estiloSecundario),
                    ),
                    const SizedBox(height: 26),
                    // pestanas
                    Container(
                      padding: const EdgeInsets.all(4),
                      decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(14)),
                      child: Row(children: [
                        for (final (reg, texto) in const [(false, 'Entrar'), (true, 'Crear cuenta')])
                          Expanded(
                            child: GestureDetector(
                              behavior: HitTestBehavior.opaque,
                              onTap: _ocupado ? null : () => setState(() {
                                _registro = reg;
                                _error = null;
                              }),
                              child: AnimatedContainer(
                                duration: const Duration(milliseconds: 200),
                                padding: const EdgeInsets.symmetric(vertical: 11),
                                decoration: BoxDecoration(
                                  color: _registro == reg ? C.superficie3 : Colors.transparent,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Text(texto, textAlign: TextAlign.center,
                                    style: TextStyle(fontWeight: FontWeight.w700,
                                        color: _registro == reg ? C.texto : C.texto3)),
                              ),
                            ),
                          ),
                      ]),
                    ),
                    const SizedBox(height: 18),
                    AnimatedSize(
                      duration: const Duration(milliseconds: 240),
                      curve: Curves.easeOutCubic,
                      child: Column(children: [
                        if (_registro) ...[
                          TextField(controller: _nombre, textCapitalization: TextCapitalization.words,
                              textInputAction: TextInputAction.next, autofillHints: const [AutofillHints.name],
                              decoration: _deco('Tu nombre (como quieres que te salude)', Icons.badge_outlined)),
                          const SizedBox(height: 12),
                        ],
                      ]),
                    ),
                    TextField(
                      controller: _usuario,
                      textInputAction: TextInputAction.next,
                      autocorrect: false,
                      autofillHints: [_registro ? AutofillHints.newUsername : AutofillHints.username],
                      inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[a-zA-Z0-9._]'))],
                      decoration: _deco('Usuario', Icons.alternate_email_rounded),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _clave,
                      obscureText: !_verClave,
                      textInputAction: _registro ? TextInputAction.next : TextInputAction.done,
                      autofillHints: [_registro ? AutofillHints.newPassword : AutofillHints.password],
                      onSubmitted: (_) => _registro ? null : _enviar(),
                      decoration: _deco('Contraseña', Icons.lock_outline_rounded,
                          sufijo: IconButton(
                            icon: Icon(_verClave ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                                color: C.texto3),
                            onPressed: () => setState(() => _verClave = !_verClave),
                          )),
                    ),
                    AnimatedSize(
                      duration: const Duration(milliseconds: 240),
                      curve: Curves.easeOutCubic,
                      child: Column(children: [
                        if (_registro) ...[
                          const SizedBox(height: 12),
                          TextField(controller: _clave2, obscureText: !_verClave, textInputAction: TextInputAction.done,
                              onSubmitted: (_) => _enviar(),
                              decoration: _deco('Repite la contraseña', Icons.lock_outline_rounded)),
                        ],
                      ]),
                    ),
                    const SizedBox(height: 8),
                    CheckboxListTile(
                      value: _recordar,
                      onChanged: (v) => setState(() => _recordar = v ?? true),
                      contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading,
                      title: const Text('Mantener la sesión iniciada'),
                      subtitle: const Text('No te volverá a pedir la contraseña en este teléfono',
                          style: TextStyle(fontSize: 12, color: C.texto3)),
                    ),
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 200),
                      child: _error == null
                          ? const SizedBox(height: 4)
                          : Container(
                              key: ValueKey(_error),
                              margin: const EdgeInsets.only(bottom: 10, top: 4),
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(color: C.error.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(10)),
                              child: Row(children: [
                                const Icon(Icons.error_outline_rounded, color: C.error, size: 20),
                                const SizedBox(width: 10),
                                Expanded(child: Text(_error!, style: const TextStyle(color: C.texto))),
                              ]),
                            ),
                    ),
                    const SizedBox(height: 6),
                    Pulsable(escala: 0.97, child: SizedBox(
                      height: 52,
                      child: FilledButton(
                        onPressed: _ocupado ? null : _enviar,
                        style: FilledButton.styleFrom(
                          backgroundColor: C.acento, foregroundColor: C.acentoTexto,
                          disabledBackgroundColor: C.acento.withValues(alpha: 0.5),
                          shape: const StadiumBorder(),
                          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                        ),
                        child: _ocupado
                            ? const SizedBox(width: 22, height: 22,
                                child: CircularProgressIndicator(strokeWidth: 2.6, color: C.acentoTexto))
                            : Text(_registro ? 'Crear mi cuenta' : 'Entrar'),
                      ),
                    )),
                    const SizedBox(height: 16),
                    const Text('Usa el mismo usuario en Caudal para Windows y tendrás todo igual.',
                        textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: C.texto3)),
                  ]),
                ),
              ),
            ),
          ),
        ),
      ]),
    );
  }
}

double _seno(double x) {
  // seno sin importar dart:math en todo el archivo
  x = x % 6.283185307;
  if (x > 3.14159265) x -= 6.283185307;
  return 1.27323954 * x - 0.405284735 * x * x.abs();
}
