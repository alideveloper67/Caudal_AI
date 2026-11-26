// Operaciones de la cola «A continuación», sin motor de sonido (para probarlas
// y para que el reproductor y la pantalla de la cola usen lo mismo).
import '../nucleo/coleccion.dart';

/// Posición de [p] en [l]: la misma pista (identidad) o, si no, la misma clave.
int indiceDe(List<Json> l, Json p) {
  final i = l.indexWhere((x) => identical(x, p));
  if (i >= 0) return i;
  final clave = p['clave'];
  if (clave == null) return -1;
  return l.indexWhere((x) => x['clave'] == clave);
}

/// Mueve el elemento [de] a la posición final [a] (la que tendrá al acabar,
/// como la que da `onReorderItem` de Flutter).
bool moverEnLista(List<Json> l, int de, int a) {
  if (de < 0 || de >= l.length) return false;
  final p = l.removeAt(de);
  l.insert(a.clamp(0, l.length), p);
  return true;
}

/// Mueve en [secuencia] una canción que aún no ha sonado (índices absolutos,
/// siempre detrás de [pos]).
bool moverEnSecuencia(List<Json> secuencia, int pos, int de, int a) {
  if (de <= pos || de >= secuencia.length) return false;
  return moverEnLista(secuencia, de, a.clamp(pos + 1, secuencia.length - 1));
}

/// Pone delante, en lo que aún no ha sonado, las que cumplen [cual] (conservando su orden y
/// sin quitar ninguna). Devuelve cuántas son.
int adelantar(List<Json> secuencia, int pos, bool Function(Json) cual) {
  final desde = pos < 0 ? 0 : pos + 1;
  if (desde >= secuencia.length) return 0;
  final pendientes = secuencia.sublist(desde);
  final si = [for (final p in pendientes) if (cual(p)) p];
  if (si.isEmpty) return 0;
  secuencia.replaceRange(desde, secuencia.length, [...si, for (final p in pendientes) if (!cual(p)) p]);
  return si.length;
}

/// «Tocar después de esta»: pone [p] justo detrás de lo que suena. Si ya
/// estaba en la cola (manual o del contexto), la mueve en vez de duplicarla.
void tocarDespues(List<Json> proximas, List<Json> secuencia, List<Json> original, int pos, Json p) {
  final i = indiceDe(proximas, p);
  if (i >= 0) {
    p = proximas.removeAt(i);
  } else {
    final j = indiceDe(secuencia.sublist(pos < 0 ? 0 : pos + 1), p);
    if (j >= 0) {
      p = secuencia.removeAt((pos < 0 ? 0 : pos + 1) + j);
      original.removeWhere((x) => identical(x, p));
    }
  }
  proximas.insert(0, p);
}

/// Lo que se guarda al «Guardar la cola como lista»: lo que suena, lo que tú
/// pusiste y lo que viene del contexto; sin repetidas y sin la reproducción
/// automática (esa no la elegiste tú).
List<Json> pistasDeLaCola(Json? actual, List<Json> proximas, List<Json> siguientes) {
  final vistas = <String>{};
  final res = <Json>[];
  for (final p in [if (actual != null) actual, ...proximas, ...siguientes]) {
    if (p['_auto'] == true) continue;
    final clave = '${p['clave'] ?? p['video_id'] ?? ''}';
    if (clave.isEmpty || !vistas.add(clave)) continue;
    res.add(p);
  }
  return res;
}

/// Crea la lista y mete las canciones. Si el nombre ya existe, busca uno libre.
/// Devuelve (nombre usado, canciones que entraron).
Future<(String, int)> guardarColaComoLista(Coleccion c, List<Json> pistas, String nombre) async {
  nombre = nombre.trim().isEmpty ? 'Mi cola' : nombre.trim();
  int id;
  try {
    id = await c.crearLista(nombre);
  } on FormatException {
    nombre = await c.nombreLibre(nombre);
    id = await c.crearLista(nombre);
  }
  final n = await c.agregarALista(id, pistas);
  return (nombre, n);
}
