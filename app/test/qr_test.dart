import 'dart:convert';

import 'package:caudal/nucleo/qr.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('el QR de la fiesta es el mismo que en Windows (y lo lee una cámara)', () {
    // comprobado con OpenCV (cv2.QRCodeDetector) y con escritorio/descargador/qr.py
    final q = CodigoQr.de('https://caudal-musica.netlify.app/fiesta/ABC234');
    expect(q.version, 4);
    expect(q.lado, 33);
    expect(q.mascara, 4);
    expect(sha1.convert(utf8.encode(q.comoTexto())).toString(), '9e825eb48b85a93d2fdf2f66e14ddb45165290fa');
  });

  test('versión más pequeña según el largo', () {
    expect(CodigoQr.de('HOLA').version, 1);
    expect(CodigoQr.de('HOLA').mascara, 0);
    expect(CodigoQr.de('x' * 150).version, 8);
    expect(CodigoQr.de('x' * 213).version, 10);
    expect(() => CodigoQr.de('x' * 214), throwsArgumentError);
  });

  test('patrones fijos en su sitio', () {
    for (final t in ['HOLA', 'https://caudal-musica.netlify.app/fiesta/XYZ789', 'ñandú 🎉' * 12]) {
      final q = CodigoQr.de(t);
      expect(q.lado, q.version * 4 + 17);
      // los tres cuadros de las esquinas: borde oscuro, anillo claro, centro oscuro
      for (final (cx, cy) in [(3, 3), (q.lado - 4, 3), (3, q.lado - 4)]) {
        expect(q.oscuro(cx, cy), isTrue);
        expect(q.oscuro(cx - 3, cy - 3), isTrue);
        expect(q.oscuro(cx - 2, cy - 2), isFalse);
      }
      // separadores claros y línea de tiempo alterna
      expect(q.oscuro(7, 7), isFalse);
      for (var i = 8; i < q.lado - 8; i++) {
        expect(q.oscuro(i, 6), i.isEven);
        expect(q.oscuro(6, i), i.isEven);
      }
      // el módulo oscuro fijo
      expect(q.oscuro(8, q.lado - 8), isTrue);
    }
  });
}
