library;

/// El código, el enlace y la tarjeta de una lista compartida (lógica pura,
/// sin red ni pantallas, para poder probarla sola).
///
/// El código tiene 8 caracteres legibles (sin I, L, O, 0, 1). Se guarda y se
/// manda sin guion (`K7M29QXP`) y se muestra con guion (`K7M2-9QXP`).

const alfabetoCodigoLista = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';

/// Dirección pública que se comparte por WhatsApp o redes.
const dominioEnlaceLista = 'https://caudal-musica.netlify.app/l/';

final _formaCodigo = RegExp('^[$alfabetoCodigoLista]{8}\$');
final _enlaceWeb = RegExp(r'caudal-musica\.netlify\.app/l/([A-Za-z0-9\-]+)', caseSensitive: false);

/// Mayúsculas, sin espacios ni guiones (como lo guarda la base).
String normalizarCodigoLista(String texto) => texto.toUpperCase().replaceAll(RegExp(r'[\s-]'), '');

bool codigoListaValido(String texto) => _formaCodigo.hasMatch(normalizarCodigoLista(texto));

/// `K7M29QXP` → `K7M2-9QXP`. Si no tiene 8 caracteres, lo deja normalizado.
String formatearCodigoLista(String texto) {
  final c = normalizarCodigoLista(texto);
  return c.length == 8 ? '${c.substring(0, 4)}-${c.substring(4)}' : c;
}

/// Saca el código de lo que la persona escribió o pegó: el código solo (con o
/// sin guion), el enlace de la web (`…/l/K7M2-9QXP`), el enlace de la app
/// (`caudal://lista?codigo=…`) o un mensaje entero que traiga alguno de ellos.
/// Nulo si no hay un código válido.
String? codigoListaDeTexto(String texto) {
  final t = texto.trim();
  if (t.isEmpty) return null;
  final web = _enlaceWeb.firstMatch(t);
  if (web != null) {
    final c = normalizarCodigoLista(web.group(1)!);
    return _formaCodigo.hasMatch(c) ? c : null;
  }
  final uri = Uri.tryParse(t);
  final q = uri?.queryParameters['codigo'];
  if (q != null) {
    final c = normalizarCodigoLista(q);
    return _formaCodigo.hasMatch(c) ? c : null;
  }
  final c = normalizarCodigoLista(t);
  if (_formaCodigo.hasMatch(c)) return c;
  // «Y escribe: K7M2-9QXP» al final de un mensaje pegado entero
  final suelto = RegExp('[$alfabetoCodigoLista]{4}-[$alfabetoCodigoLista]{4}').allMatches(t.toUpperCase());
  if (suelto.isNotEmpty) return normalizarCodigoLista(suelto.last.group(0)!);
  return null;
}

/// ¿Este texto es un enlace de lista (web o de la app)?
bool esEnlaceDeLista(String texto) {
  final t = texto.trim().toLowerCase();
  return t.startsWith('caudal://lista') || _enlaceWeb.hasMatch(t);
}

String enlaceWebLista(String codigo) => '$dominioEnlaceLista${formatearCodigoLista(codigo)}';

String enlaceAppLista(String codigo) => 'caudal://lista?codigo=${formatearCodigoLista(codigo)}';

/// El mensaje que sale en la hoja de compartir del sistema.
String mensajeCompartirLista(String nombre, String codigo) {
  final c = formatearCodigoLista(codigo);
  return 'Te paso mi lista «$nombre» en Caudal 🎧\n'
      'Ábrela aquí: ${enlaceWebLista(codigo)}\n'
      'O entra a Caudal › Biblioteca › «Tengo un código» y escribe: $c';
}

/// Permisos de una lista compartida.
const rolColaborador = 'colaborador';
const rolOyente = 'oyente';

String textoRolLista(String rol) => rol == rolColaborador ? 'Colaborativa' : 'Solo escuchar';

/// La lista que viaja dentro de un mensaje del chat (`mensajes.lista`).
class TarjetaLista {
  const TarjetaLista({required this.codigo, required this.nombre, this.canciones = 0,
      this.rol = rolColaborador, this.portada = ''});

  /// Sin guion y en mayúsculas.
  final String codigo;
  final String nombre;
  final int canciones;
  final String rol;
  final String portada;

  bool get colaborativa => rol == rolColaborador;
  String get codigoVisible => formatearCodigoLista(codigo);
  String get textoCanciones => canciones == 1 ? '1 canción' : '$canciones canciones';

  /// «Colaborativa · 12 canciones».
  String get resumen => '${textoRolLista(rol)} · $textoCanciones';

  /// Lo que se guarda en la columna `lista` del mensaje.
  Map<String, dynamic> aJson() => {
        'codigo': normalizarCodigoLista(codigo),
        'nombre': nombre,
        'canciones': canciones,
        'rol': rol,
        if (portada.isNotEmpty) 'portada': portada,
      };

  /// Nulo si lo que llegó no es una tarjeta (sin código).
  static TarjetaLista? desde(Object? d) {
    if (d is! Map) return null;
    final codigo = normalizarCodigoLista('${d['codigo'] ?? ''}');
    if (codigo.isEmpty) return null;
    final rol = '${d['rol']}' == rolOyente ? rolOyente : rolColaborador;
    return TarjetaLista(
      codigo: codigo,
      nombre: '${d['nombre'] ?? ''}'.trim().isEmpty ? 'Una lista' : '${d['nombre']}'.trim(),
      canciones: (d['canciones'] as num?)?.toInt() ?? int.tryParse('${d['canciones'] ?? ''}') ?? 0,
      rol: rol,
      portada: '${d['portada'] ?? ''}',
    );
  }

  /// «♪ Lista «Rock de ruta»» (vista previa en la lista de chats).
  String get vistaPrevia => '♪ Lista «$nombre»';
}
