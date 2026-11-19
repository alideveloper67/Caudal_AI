/// La línea de la letra que toca ahora, para el subtítulo de la notificación multimedia
/// (pantalla de bloqueo). Lógica pura: dice cuándo cambia la línea para que el sistema
/// solo se actualice entonces y no a cada tic de la posición.
class LetraBloqueo {
  String _clave = '';
  List<(int, String)> _ls = const [];
  String _mostrado = '';
  int _indice = -2;

  bool get hayLetra => _ls.isNotEmpty;

  /// Lo que está puesto ahora en el subtítulo.
  String get mostrado => _mostrado;

  /// Empieza otra canción: se olvida la letra anterior. Devuelve `''` si había una
  /// línea puesta (hay que borrarla del subtítulo) y null si ya estaba vacío.
  String? cambiarCancion(String clave) {
    _clave = clave;
    _ls = const [];
    _indice = -2;
    return _vaciar();
  }

  String? _vaciar() {
    if (_mostrado.isEmpty) return null;
    _mostrado = '';
    return '';
  }

  /// La letra de la canción [clave] llegó (se ignora si ya sonó otra).
  void ponerLetra(String clave, List<(int, String)> lineas) {
    if (clave != _clave) return;
    _ls = List.of(lineas)..sort((a, b) => a.$1.compareTo(b.$1));
    _indice = -2;
  }

  /// Quita la letra (se apagó la función o la cuenta ya no tiene el beneficio).
  String? apagar() {
    _ls = const [];
    _indice = -2;
    return _vaciar();
  }

  /// Índice de la línea que suena en [ms] (-1 antes de la primera).
  static int indiceEn(List<(int, String)> ls, int ms) {
    var a = 0, b = ls.length - 1, mejor = -1;
    while (a <= b) {
      final m = (a + b) >> 1;
      if (ls[m].$1 <= ms) {
        mejor = m;
        a = m + 1;
      } else {
        b = m - 1;
      }
    }
    return mejor;
  }

  /// Al moverse la posición: devuelve el texto nuevo del subtítulo solo si cambió de
  /// línea; null si sigue igual (no hay nada que publicar).
  String? alMoverse(Duration posicion, {int desfaseMs = 0}) {
    if (_ls.isEmpty) return null;
    final i = indiceEn(_ls, posicion.inMilliseconds + desfaseMs);
    if (i == _indice) return null;
    _indice = i;
    final texto = i < 0 ? '' : _ls[i].$2.trim();
    if (texto == _mostrado) return null;
    _mostrado = texto;
    return texto;
  }
}
