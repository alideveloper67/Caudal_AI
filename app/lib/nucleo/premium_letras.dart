import 'fondo_app.dart';
import 'premium.dart';

/// ¿Esta cuenta tiene los beneficios de donador? Lo usan las tarjetas de letra
/// especiales, la letra animada y «Tu año en Caudal».
///
/// Es una puerta mínima e inyectable: por defecto pregunta lo mismo que el fondo
/// de Caudal (`FondoApp.i.puede`, que decide el servidor) y al servicio `Premium`, que
/// también cuenta el pase de prueba. Las pruebas lo cambian a mano.
bool Function() esPremiumLetras = () => Premium.i.activo || FondoApp.i.puede;
