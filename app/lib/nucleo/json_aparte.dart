// Decodificar JSON grande fuera del hilo de la pantalla.
//
// Las respuestas grandes (la nube al sincronizar, YouTube Music) tardan decenas
// de milisegundos en decodificarse: en el hilo principal eso son fotogramas
// perdidos. Pasando de [umbralJsonAparte] se decodifican en otro isolate (en
// la web, donde no hay isolates, `compute` lo hace en el mismo hilo).

import 'dart:convert';

import 'package:flutter/foundation.dart' show compute;

/// A partir de cuantos caracteres se decodifica aparte (~64 KB).
const umbralJsonAparte = 64 * 1024;

Object? _decodificar(String texto) => jsonDecode(texto);

/// `jsonDecode`, pero en otro isolate si [texto] es grande.
Future<dynamic> jsonDecodeAparte(String texto) async {
  if (texto.length < umbralJsonAparte) return jsonDecode(texto);
  return compute(_decodificar, texto, debugLabel: 'json');
}

/// Lo mismo desde los bytes en UTF-8 de una respuesta: tambien la conversion
/// a texto se hace aparte cuando es grande.
Future<dynamic> jsonDecodeBytesAparte(List<int> bytes) async {
  if (bytes.length < umbralJsonAparte) return jsonDecode(utf8.decode(bytes));
  return compute(_decodificarBytes, bytes, debugLabel: 'json');
}

Object? _decodificarBytes(List<int> bytes) => jsonDecode(utf8.decode(bytes));
