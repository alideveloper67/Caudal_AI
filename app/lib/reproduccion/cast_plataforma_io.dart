import 'dart:io';

import 'cast_nativo.dart';
import 'cast_servidor.dart';
import 'cast_tipos.dart';

export 'cast_servidor.dart' show tipoPorExtension;

/// En Android e iPhone, el SDK de Google Cast; en la PC (Flutter de escritorio)
/// no hay: el escritorio de Caudal tiene su propio Cast en Python.
PuenteCast crearPuenteCast() => (Platform.isAndroid || Platform.isIOS) ? PuenteNativo() : PuenteNulo();

ServidorCast crearServidorCast() => ServidorCastIo();
