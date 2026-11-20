import 'dart:async';

/// Lo que el control de Cast (ver cast.dart) necesita de un Chromecast, sea
/// cual sea la biblioteca que hable con él. Así las pruebas usan un aparato de
/// mentira y la app el SDK de Google (cast_nativo.dart).

/// Una tele, un Chromecast o un altavoz con Google Cast de la red de casa.
class DispositivoCast {
  const DispositivoCast({required this.id, required this.nombre, this.modelo = ''});

  final String id;
  final String nombre;
  final String modelo;

  /// ¿Es un altavoz (Nest/Google Home, grupos de altavoces...) y no una pantalla?
  bool get esAltavoz {
    final m = modelo.toLowerCase();
    return m.contains('audio') || m.contains('speaker') || m.contains('home') ||
        m.contains('nest mini') || m.contains('nest audio') || m.contains('group') || m.contains('grupo');
  }

  @override
  bool operator ==(Object other) => other is DispositivoCast && other.id == id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() => 'DispositivoCast($nombre)';
}

/// Lo que se le manda a la tele: una dirección http(s) que ella pueda abrir y
/// lo que se muestra en su pantalla.
class MedioCast {
  const MedioCast({required this.url, required this.tipo, this.titulo = '', this.artista = '',
      this.album = '', this.caratula, this.duracion});

  final String url;

  /// Tipo del contenido (audio/webm, audio/mp4, audio/mpeg...).
  final String tipo;
  final String titulo;
  final String artista;
  final String album;
  final String? caratula;
  final Duration? duracion;
}

/// En qué está el reproductor de la tele.
enum EstadoMedioCast {
  /// Nada cargado (o la tele aún no ha dicho nada).
  nada,
  cargando,
  sonando,
  pausa,

  /// Llegó al final de la canción.
  terminado,

  /// No pudo abrirla (dirección caducada, formato que no entiende...).
  error,

  /// Se cortó porque se cargó otra cosa o alguien la paró desde otro sitio.
  cortado,
}

class EventoCast {
  const EventoCast(this.estado, {this.duracion, this.url});

  final EstadoMedioCast estado;

  /// Lo que dura lo que suena, si la tele lo sabe.
  final Duration? duracion;

  /// La dirección de lo que suena en la tele (para saber si el aviso es de lo nuestro).
  final String? url;
}

/// El puente con el SDK de Google Cast.
abstract class PuenteCast {
  /// ¿Puede haber Cast aquí? (no en la web ni en la PC)
  bool get disponible;

  /// Arranca el SDK. Devuelve false si el teléfono no lo tiene (sin servicios de Google).
  Future<bool> preparar();

  Stream<List<DispositivoCast>> get dispositivos;
  Future<void> buscar();
  Future<void> dejarDeBuscar();

  /// Empieza a conectar (la conexión llega luego por [sesion]).
  Future<bool> conectar(DispositivoCast d);

  /// Corta la sesión y para lo que suena en la tele.
  Future<void> desconectar();

  /// El aparato con el que hay sesión abierta, o null si no hay.
  Stream<DispositivoCast?> get sesion;

  Stream<EventoCast> get medio;
  Stream<Duration> get posicion;

  /// Volumen del aparato, de 0 a 1.
  Stream<double> get volumen;

  Future<void> cargar(MedioCast m, {Duration desde = Duration.zero, bool sonar = true});
  Future<void> sonar();
  Future<void> pausar();
  Future<void> irA(Duration p);
  Future<void> fijarVolumen(double v);
  Future<void> parar();
}

/// El pequeño servidor http del teléfono: la tele no puede leer los archivos
/// del teléfono, así que se los pide a él por la wifi.
abstract class ServidorCast {
  /// Dirección http para que la tele lea [ruta] (con saltos: cabecera Range),
  /// o null si el teléfono no está en ninguna wifi.
  Future<String?> publicarArchivo(String ruta, {String? tipo});

  /// Dirección http que repite [url] a través del teléfono (por si la tele no
  /// puede abrirla directamente), o null.
  Future<String?> publicarRemoto(String url, {String? tipo});

  Future<void> cerrar();
}

/// Donde no hay Cast (web, PC): no aparece el botón.
class PuenteNulo implements PuenteCast {
  @override
  bool get disponible => false;
  @override
  Future<bool> preparar() async => false;
  @override
  Stream<List<DispositivoCast>> get dispositivos => const Stream.empty();
  @override
  Future<void> buscar() async {}
  @override
  Future<void> dejarDeBuscar() async {}
  @override
  Future<bool> conectar(DispositivoCast d) async => false;
  @override
  Future<void> desconectar() async {}
  @override
  Stream<DispositivoCast?> get sesion => const Stream.empty();
  @override
  Stream<EventoCast> get medio => const Stream.empty();
  @override
  Stream<Duration> get posicion => const Stream.empty();
  @override
  Stream<double> get volumen => const Stream.empty();
  @override
  Future<void> cargar(MedioCast m, {Duration desde = Duration.zero, bool sonar = true}) async {}
  @override
  Future<void> sonar() async {}
  @override
  Future<void> pausar() async {}
  @override
  Future<void> irA(Duration p) async {}
  @override
  Future<void> fijarVolumen(double v) async {}
  @override
  Future<void> parar() async {}
}

class ServidorNulo implements ServidorCast {
  @override
  Future<String?> publicarArchivo(String ruta, {String? tipo}) async => null;
  @override
  Future<String?> publicarRemoto(String url, {String? tipo}) async => null;
  @override
  Future<void> cerrar() async {}
}
