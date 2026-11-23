import 'package:flutter/foundation.dart';

import 'reproductor.dart';

class VentanaWeb {
  VentanaWeb._();

  static bool get puedePantallaCompleta => false;
  static final ValueNotifier<bool> completa = ValueNotifier(false);
  static Future<void> pantallaCompleta(bool si) async {}
  static bool get puedeMini => false;
  static final ValueNotifier<bool> miniAbierto = ValueNotifier(false);
  static Future<String?> alternarMini(Reproductor r) async => null;
}
