// Frenos para los avisos del reproductor.
//
// libmpv avisa la posicion muchas veces por segundo; cada aviso reconstruia la
// barra, la letra, el mini reproductor y la notificacion. Aqui se decide cuando
// vale la pena avisar de verdad, sin perder nada que se note.

/// Cada cuanto avanza la posicion publicada con la app a la vista (la barra y
/// la letra interpolan entre medias, asi que se sigue viendo fluido).
const pasoPosicion = Duration(milliseconds: 200);

/// Con la app en segundo plano nadie mira la barra: un aviso por segundo.
const pasoPosicionFondo = Duration(seconds: 1);

/// ¿Hay que publicar [nueva] si lo publicado es [publicada]? Si avanzo un paso
/// entero (o salto hacia atras o adelante mas que eso).
bool publicarPosicion(Duration nueva, Duration publicada, {bool fondo = false}) {
  final d = (nueva - publicada).abs();
  return d >= (fondo ? pasoPosicionFondo : pasoPosicion);
}

/// La notificacion de musica (y la pantalla de bloqueo) solo necesita saber
/// el estado y desde donde contar: el sistema avanza la barra solo. Se le
/// avisa cuando cambia algo de verdad o cuando la posicion se aleja mas de
/// [tolerancia] de la que el sistema calcula por su cuenta (un salto).
class FrenoNotificacion {
  FrenoNotificacion({this.tolerancia = const Duration(milliseconds: 1500)});

  final Duration tolerancia;

  String? _firma;
  Duration _posicion = Duration.zero;
  DateTime _en = DateTime(2000);
  double _velocidad = 1;
  bool _sonando = false;

  /// Olvida lo publicado (la siguiente vez se publica seguro).
  void reiniciar() => _firma = null;

  /// ¿Se publica? [firma] junta todo lo que no es la posicion (estado,
  /// controles, velocidad, cancion). Si devuelve true, lo apunta como publicado.
  bool deja({
    required String firma,
    required Duration posicion,
    required bool sonando,
    required double velocidad,
    DateTime? ahora,
  }) {
    final t = ahora ?? DateTime.now();
    var publicar = firma != _firma;
    if (!publicar) {
      final esperada = _sonando
          ? _posicion + Duration(microseconds: (t.difference(_en).inMicroseconds * _velocidad).round())
          : _posicion;
      publicar = (posicion - esperada).abs() > tolerancia;
    }
    if (publicar) {
      _firma = firma;
      _posicion = posicion;
      _en = t;
      _velocidad = velocidad;
      _sonando = sonando;
    }
    return publicar;
  }
}
