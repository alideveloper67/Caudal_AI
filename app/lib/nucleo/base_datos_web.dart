import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi_web/sqflite_ffi_web.dart';

/// En el navegador la base vive en su almacenamiento (SQLite en WebAssembly).
Future<void> prepararBaseDeDatos() async {
  databaseFactory = databaseFactoryFfiWeb;
}
