/// Las claves de lo que un donador puede personalizar (las mismas que acepta la base de datos).
/// No importa nada: la usan los modelos sociales, el servicio [Premium] y los widgets.
class Cosmeticos {
  Cosmeticos._();

  static const ninguno = 'ninguno';

  /// Marcos del avatar.
  static const marcos = ['ninguno', 'aurora', 'fuego', 'oro', 'neon', 'hielo', 'arcoiris', 'galaxia'];

  /// Efectos del nombre.
  static const efectosNombre = ['ninguno', 'brillo', 'degradado', 'arcoiris', 'neon'];

  /// Temas de color exclusivos.
  static const temas = ['ninguno', 'atardecer', 'bosque', 'sakura', 'oceano', 'medianoche', 'ambar'];

  static String _en(Object? v, List<String> validos) {
    final t = '${v ?? ''}'.trim().toLowerCase();
    return validos.contains(t) ? t : ninguno;
  }

  /// Lo que llegue de la base (o falte) se vuelve una clave válida; lo desconocido es «ninguno».
  static String marco(Object? v) => _en(v, marcos);
  static String efectoNombre(Object? v) => _en(v, efectosNombre);
  static String tema(Object? v) => _en(v, temas);
}
