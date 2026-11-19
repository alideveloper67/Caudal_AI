// Listas colaborativas con más gente (hasta 50 personas, gratis para todos): el aviso de lista llena y lo que
// dice la pantalla de compartir. El tope lo hace cumplir la base (supabase/listas_colaboradores.sql, con su
// propia prueba en supabase/pruebas/); aquí se comprueba lo que ve la persona.
import 'package:caudal/nucleo/nube.dart';
import 'package:caudal/nucleo/premium.dart';
import 'package:caudal/nucleo/tarjeta_lista.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  setUp(() => Premium.i.reiniciar());

  test('el tope visible es 50 personas', () {
    expect(maxMiembrosLista, 50);
  });

  test('con la lista llena (50) el aviso es claro', () {
    expect(Nube.traducirSocial('Esta lista ya tiene 50 personas, que es el máximo. Pídele a su dueño que haga lugar.'),
        'Esta lista ya está llena (50 personas). Pídele a su dueño que haga lugar.');
  });

  test('el aviso del tope viejo (20) sigue entendiéndose con una base sin actualizar', () {
    expect(Nube.traducirSocial('Esta lista ya tiene 20 personas, que es el máximo. Pídele a su dueño que haga lugar.'),
        'Esta lista ya está llena (20 personas). Pídele a su dueño que haga lugar.');
  });

  test('no es un beneficio de donadores: el tope no depende de la cuenta', () {
    expect(Premium.i.activo, isFalse);
    expect(maxMiembrosLista, 50);
    Premium.i.estado = const EstadoPremium(premium: true, tipo: 'donador');
    expect(maxMiembrosLista, 50);
  });
}
