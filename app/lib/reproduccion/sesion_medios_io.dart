import 'reproductor.dart';

class SesionMedios {
  SesionMedios._();

  static void enganchar(Reproductor r) {}
  static void Function()? alPararYouTube;

  /// ¿La página no se ve? (pantalla apagada u otra app delante)
  static bool get oculta => false;

  /// ¿El navegador es el de un teléfono o una tablet?
  static bool get esTelefono => false;

  static bool get puedeDejarEncendida => false;
  static Future<bool> pantallaEncendida(bool si) async => false;
}
