import 'package:caudal/nucleo/premium_letras.dart';
import 'package:caudal/ui/paginas/compartir_letra.dart';
import 'package:caudal/ui/tema.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const _tamanos = <(String, Size, double)>[
  ('telefono chico 320x568', Size(320, 568), 2.0),
  ('telefono 360x640', Size(360, 640), 2.0),
  ('horizontal 915x412', Size(915, 412), 2.6),
  ('escritorio 1440x1800', Size(1440, 1800), 1.0),
];

const _estilosPremium = ['Neón', 'Cristal', 'Papel', 'Aurora'];
const _estilosGratis = ['Estado', 'Color', 'Oscuro', 'Claro'];

Future<void> _abrir(WidgetTester t, Size tam, double dpr) async {
  t.view.physicalSize = tam * dpr;
  t.view.devicePixelRatio = dpr;
  addTearDown(t.view.reset);
  await t.pumpWidget(MaterialApp(
    theme: temaCaudal(),
    home: Builder(
      builder: (context) => Scaffold(
        body: Center(
          child: TextButton(
            onPressed: () => compartirLetra(
              context,
              pista: {
                'titulo': 'Una canción con un título bastante largo para probar el desborde',
                'artista': 'Artista de prueba',
                'miniatura': ''
              },
              lineas: [
                'Primera línea de la letra',
                'Segunda línea un poco más larga que la primera para que ocupe más espacio',
                '',
                'Tercera línea',
                'Cuarta línea final'
              ],
              color: const Color(0xFF3B82F6),
            ),
            child: const Text('abrir'),
          ),
        ),
      ),
    ),
  ));
  await t.tap(find.text('abrir'));
  await t.pump(const Duration(milliseconds: 500));
}

ScrollPosition _posicion(WidgetTester t) {
  final sc = find.descendant(of: find.byType(ListView).first, matching: find.byType(Scrollable)).first;
  return t.state<ScrollableState>(sc).position;
}

Future<void> _arriba(WidgetTester t) async {
  _posicion(t).jumpTo(0);
  await t.pump(const Duration(milliseconds: 100));
}

/// Lleva a la vista un elemento de la hoja. La lista es perezosa: en pantallas chicas lo de
/// abajo ni siquiera está construido hasta que se desplaza. Se salta a posiciones exactas
/// (arrastrar podría arrastrar la hoja entera y cerrarla).
Future<void> _ver(WidgetTester t, Finder f) async {
  if (f.evaluate().isNotEmpty) {
    await t.ensureVisible(f);
    await t.pump(const Duration(milliseconds: 100));
    return;
  }
  final pos = _posicion(t);
  for (var y = 0.0; y <= pos.maxScrollExtent + 150; y += 150) {
    pos.jumpTo(y.clamp(0.0, pos.maxScrollExtent).toDouble());
    await t.pump(const Duration(milliseconds: 60));
    if (f.evaluate().isNotEmpty) {
      await t.ensureVisible(f);
      await t.pump(const Duration(milliseconds: 100)); // aplica el desplazamiento antes de pulsar
      return;
    }
  }
  final textos = [for (final w in t.widgetList<Text>(find.byType(Text, skipOffstage: false))) w.data ?? ''];
  fail('No se encontró el elemento en la hoja (extent ${pos.maxScrollExtent}, px ${pos.pixels}): ${textos.join(' | ')}');
}

Future<void> _tocar(WidgetTester t, String texto) async {
  await _ver(t, find.text(texto));
  await t.tap(find.text(texto), warnIfMissed: false);
  await t.pump(const Duration(milliseconds: 300));
}

void main() {
  tearDown(() => esPremiumLetras = () => false);

  for (final (nombre, tam, dpr) in _tamanos) {
    testWidgets('donador: todos los estilos y formatos sin desbordes · $nombre', (t) async {
      esPremiumLetras = () => true;
      await _abrir(t, tam, dpr);
      expect(t.takeException(), isNull, reason: 'al abrir');
      for (final formato in ['Historia', 'Vertical', 'Cuadrada']) {
        await _tocar(t, formato);
        for (final e in [..._estilosGratis, ..._estilosPremium]) {
          await _tocar(t, e);
          expect(t.takeException(), isNull, reason: '$e en $formato');
        }
      }
    });
  }

  testWidgets('donador: alineación, tamaño y firma cambian la tarjeta sin desbordes', (t) async {
    esPremiumLetras = () => true;
    await _abrir(t, const Size(320, 568), 2.0);
    await _tocar(t, 'Neón');
    expect(find.text('Vista previa · donadores'), findsNothing);
    await _tocar(t, 'Centro');
    expect(t.takeException(), isNull, reason: 'centrado');
    await _ver(t, find.byType(Slider));
    await t.drag(find.byType(Slider), const Offset(400, 0));
    await t.pump(const Duration(milliseconds: 300));
    expect(t.takeException(), isNull, reason: 'letra más grande');
    await _ver(t, find.byType(Switch));
    await t.tap(find.byType(Switch));
    await t.pump(const Duration(milliseconds: 300));
    expect(t.takeException(), isNull, reason: 'sin firma');
  });

  testWidgets('sin ser donador: los estilos nuevos se ven con candado y marca de agua', (t) async {
    esPremiumLetras = () => false;
    await _abrir(t, const Size(360, 640), 2.0);
    // un estilo gratis: sin marca ni aviso
    expect(find.text('Vista previa · donadores'), findsNothing);
    await _ver(t, find.text('Aurora'));
    // los 4 chips de donador llevan candado
    expect(find.byIcon(Icons.lock_rounded), findsAtLeast(_estilosPremium.length));
    for (final e in _estilosPremium) {
      await _tocar(t, e);
      await _arriba(t);
      expect(find.text('Vista previa · donadores'), findsOneWidget, reason: e);
      await _ver(t, find.text('Estilo exclusivo para donadores'));
      expect(find.text('Estilo exclusivo para donadores'), findsOneWidget, reason: e);
      expect(t.takeException(), isNull, reason: e);
    }
  });

  testWidgets('sin ser donador: compartir un estilo bloqueado abre Donar', (t) async {
    esPremiumLetras = () => false;
    await _abrir(t, const Size(360, 640), 2.0);
    await _tocar(t, 'Aurora');
    await t.tap(find.text('Compartir en estados y chats'));
    await t.pump(const Duration(milliseconds: 400));
    expect(find.text('Apoya a Caudal con Yape'), findsOneWidget);
  });

  testWidgets('sin ser donador: el video animado y las opciones llevan a Donar', (t) async {
    esPremiumLetras = () => false;
    await _abrir(t, const Size(360, 640), 2.0);
    await _ver(t, find.text('Crear video animado'));
    await t.tap(find.text('Crear video animado'));
    await t.pump(const Duration(milliseconds: 400));
    expect(find.text('Apoya a Caudal con Yape'), findsOneWidget);
  });

  testWidgets('donador: aparece el botón del video y no hay candados', (t) async {
    esPremiumLetras = () => true;
    await _abrir(t, const Size(360, 640), 2.0);
    await _ver(t, find.text('Aurora'));
    expect(find.byIcon(Icons.lock_rounded), findsNothing);
    await _ver(t, find.text('Crear video animado'));
    expect(find.byIcon(Icons.lock_rounded), findsNothing);
    expect(find.text('Crear video animado'), findsOneWidget);
    expect(find.text('Estilo exclusivo para donadores'), findsNothing);
  });
}
