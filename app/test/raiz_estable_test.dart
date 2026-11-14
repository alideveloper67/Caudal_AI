import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Reproduce el fallo de la 2.0.0-2.0.3: al entrar a la cuenta la raiz pasaba
/// de MaterialApp a Envoltura(MaterialApp) y el navegador (con GlobalKey)
/// conservaba la pantalla vieja: se quedaba en el logo o en "Crear cuenta".
class _Envoltura extends InheritedWidget {
  const _Envoltura({required super.child});
  @override
  bool updateShouldNotify(_Envoltura oldWidget) => false;
}

class _Raiz extends StatefulWidget {
  const _Raiz({required this.envolverFuera});
  final bool envolverFuera;
  @override
  State<_Raiz> createState() => _RaizState();
}

class _RaizState extends State<_Raiz> {
  final _navegador = GlobalKey<NavigatorState>();
  bool dentro = false;

  void entrar() => setState(() => dentro = true);

  @override
  Widget build(BuildContext context) {
    final home = dentro ? const Text('PRINCIPAL') : const Text('LOGO');
    final app = MaterialApp(
      navigatorKey: _navegador,
      home: Scaffold(body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 10),
        child: KeyedSubtree(key: ValueKey(dentro), child: home),
      )),
      // forma corregida: la envoltura va dentro, la raiz no cambia
      builder: widget.envolverFuera || !dentro ? null : (_, hijo) => _Envoltura(child: hijo!),
    );
    // forma vieja: la raiz cambia de tipo al entrar
    return widget.envolverFuera && dentro ? _Envoltura(child: app) : app;
  }
}

void main() {
  testWidgets('envolviendo por fuera (forma vieja) la pantalla no cambia', (t) async {
    await t.pumpWidget(const _Raiz(envolverFuera: true));
    expect(find.text('LOGO'), findsOneWidget);
    t.state<_RaizState>(find.byType(_Raiz)).entrar();
    await t.pumpAndSettle();
    // documenta el fallo: si algun dia Flutter lo cambia, esta prueba avisa
    expect(find.text('PRINCIPAL'), findsNothing);
  });

  testWidgets('envolviendo por dentro (forma nueva) sí pasa a la principal', (t) async {
    await t.pumpWidget(const _Raiz(envolverFuera: false));
    expect(find.text('LOGO'), findsOneWidget);
    t.state<_RaizState>(find.byType(_Raiz)).entrar();
    await t.pumpAndSettle();
    expect(find.text('PRINCIPAL'), findsOneWidget);
  });
}
