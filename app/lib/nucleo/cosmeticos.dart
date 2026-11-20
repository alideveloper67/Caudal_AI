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
  static const temas = [
    'ninguno', 'atardecer', 'bosque', 'sakura', 'oceano', 'medianoche', 'ambar',
    'retro', 'cyberpunk', 'samurai', 'boxeo', 'gym', 'fan_kitty', 'gotico', 'lofi',
    'est_kuromi', 'est_cinnamoroll', 'est_pompompurin', 'est_hellokitty', 'est_mymelody',
  ];

  static String _en(Object? v, List<String> validos) {
    final t = '${v ?? ''}'.trim().toLowerCase();
    return validos.contains(t) ? t : ninguno;
  }

  /// Lo que llegue de la base (o falte) se vuelve una clave válida; lo desconocido es «ninguno».
  static String marco(Object? v) => _en(v, marcos);
  static String efectoNombre(Object? v) => _en(v, efectosNombre);
  static String tema(Object? v) => _en(v, temas);

  /// Colores rápidos para el nombre (los mismos, en el mismo orden, que el escritorio).
  static const paletaNombre = <(String, String)>[
    ('Rosa', '#FF5C8A'), ('Coral', '#FF7A45'), ('Oro', '#FFC857'), ('Menta', '#7CFFB2'), ('Cian', '#22D3EE'),
    ('Azul', '#4DA8FF'), ('Lila', '#A78BFA'), ('Fucsia', '#FF4DD2'), ('Nieve', '#F5F5F5'),
  ];

  /// El color del nombre tal como lo guarda la base: «#RRGGBB» en mayúsculas, o null si no hay
  /// (o si lo que llegó no es un color). Acepta «ff5c8a», « #ff5c8a » y «#FF5C8A».
  static String? colorNombre(Object? v) {
    if (v == null) return null;
    var t = '$v'.trim().toUpperCase();
    if (t.isEmpty) return null;
    if (!t.startsWith('#')) t = '#$t';
    return RegExp(r'^#[0-9A-F]{6}$').hasMatch(t) ? t : null;
  }

  /// El nombre del color si es uno de la paleta («Rosa»), o «Personalizado».
  static String nombreDeColor(String? hex) {
    final h = colorNombre(hex);
    if (h == null) return 'Sin color';
    for (final c in paletaNombre) {
      if (c.$2 == h) return c.$1;
    }
    return 'Personalizado';
  }

  /// Estilos de la letra con efectos (las mismas claves que el escritorio).
  static const estilosLetra = ['resplandor', 'ola', 'neon', 'cine'];
  static const nombresEstiloLetra = {'resplandor': 'Resplandor', 'ola': 'Ola', 'neon': 'Neón', 'cine': 'Cine'};
  static String estiloLetra(Object? v) {
    final t = '${v ?? ''}'.trim().toLowerCase();
    return estilosLetra.contains(t) ? t : estilosLetra.first;
  }
}
