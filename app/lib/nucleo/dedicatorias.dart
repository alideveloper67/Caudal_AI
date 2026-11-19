import 'dart:async';

import 'coleccion.dart' show Json;
import 'premium.dart';

/// Dedicatorias (donadores): mandar una canción a un amigo con una tarjeta bonita y un mensaje. Viajan
/// por el chat de siempre: son un mensaje con canción (`pista`) que lleva dentro la clave `dedicatoria`
/// (mensaje, estilo de la tarjeta y segundo donde empieza el fragmento). No hace falta nada nuevo en el
/// servidor, y quien recibe una puede ser o no donador: enviar es de donadores, abrirlas es de todos.
class Dedicatoria {
  const Dedicatoria({required this.mensaje, this.estilo = 'aurora', this.inicio = 0});

  /// La clave dentro de la pista del mensaje.
  static const clave = 'dedicatoria';

  /// Letras que admite el mensaje de la tarjeta.
  static const maxMensaje = 140;

  /// Hasta dónde se puede elegir el inicio del fragmento (10 minutos).
  static const maxInicio = 600;

  /// Cuánto suena el fragmento al abrirla.
  static const duracionFragmento = Duration(seconds: 20);

  /// Los estilos de tarjeta (sus colores viven en la pantalla).
  static const estilos = ['aurora', 'atardecer', 'sakura', 'oceano', 'bosque', 'medianoche'];

  final String mensaje;
  final String estilo;

  /// Segundo de la canción donde empieza el fragmento.
  final int inicio;

  static String estiloValido(Object? v) {
    final t = '${v ?? ''}'.trim().toLowerCase();
    return estilos.contains(t) ? t : estilos.first;
  }

  static String limpiarMensaje(String t) {
    final limpio = t.replaceAll('\r', '').replaceAll(RegExp(r'\n{3,}'), '\n\n').trim();
    return limpio.length <= maxMensaje ? limpio : limpio.substring(0, maxMensaje).trimRight();
  }

  /// El inicio dentro de lo permitido (un valor raro de la red no rompe nada).
  static int inicioValido(Object? v) {
    final n = v is num ? v.toInt() : int.tryParse('${v ?? ''}') ?? 0;
    return n.clamp(0, maxInicio);
  }

  /// 0:45, 1:05, 10:00.
  static String tiempo(int segundos) {
    final s = segundos.clamp(0, maxInicio);
    return '${s ~/ 60}:${(s % 60).toString().padLeft(2, '0')}';
  }

  String get inicioTexto => tiempo(inicio);

  /// Nulo si la pista no trae una dedicatoria.
  static Dedicatoria? de(Json? pista) {
    final d = pista?[clave];
    if (d is! Map) return null;
    return Dedicatoria(
      mensaje: limpiarMensaje('${d['mensaje'] ?? ''}'),
      estilo: estiloValido(d['estilo']),
      inicio: inicioValido(d['inicio']),
    );
  }

  static bool esDedicatoria(Json? pista) => pista?[clave] is Map;

  Map<String, Object?> aJson() => {'mensaje': mensaje, 'estilo': estilo, 'inicio': inicio};

  /// La pista lista para mandar por el chat, con la dedicatoria dentro.
  static Json conDedicatoria(Json pista, Dedicatoria d) => {
        for (final e in pista.entries)
          if (e.key != clave) e.key: e.value,
        clave: Dedicatoria(
          mensaje: limpiarMensaje(d.mensaje),
          estilo: estiloValido(d.estilo),
          inicio: inicioValido(d.inicio),
        ).aJson(),
      };

  /// La misma canción sin la tarjeta: lo que suena, se guarda en listas o se manda a otro lado.
  static Json pistaLimpia(Json pista) => {
        for (final e in pista.entries)
          if (e.key != clave) e.key: e.value,
      };

  /// Solo se dedican canciones que suenan en línea (las de archivos del teléfono no le sirven a nadie más).
  static bool sePuedeDedicar(Json? pista) => pista != null && '${pista['video_id'] ?? ''}'.isNotEmpty;

  /// Solo donadores (y fundadores, y pruebas vigentes) mandan dedicatorias.
  static bool puedeEnviar() => Premium.i.activo;

  /// «💌 Dedicatoria · Titulo»: la vista previa en la lista de chats.
  static String vistaPrevia(Json pista) {
    final t = '${pista['titulo'] ?? ''}'.trim();
    return t.isEmpty ? '💌 Una dedicatoria' : '💌 Dedicatoria · $t';
  }
}

/// Lo que hace falta del reproductor para sonar un fragmento (así se puede probar sin audio de verdad).
class ControlFragmento {
  const ControlFragmento({
    required this.actual,
    required this.sonando,
    required this.duracion,
    required this.reproducir,
    required this.buscar,
    required this.pausar,
  });

  final Json? Function() actual;
  final bool Function() sonando;
  final Duration Function() duracion;
  final Future<void> Function(Json pista) reproducir;
  final Future<void> Function(Duration posicion) buscar;
  final Future<void> Function() pausar;
}

/// Suena un trocito de la canción dedicada y se calla solo, sin pisar lo que la persona haga después:
/// si cambia de canción o pausa a mano, no se mete.
class SonarFragmento {
  SonarFragmento(this.control,
      {this.paso = const Duration(milliseconds: 250),
      this.esperaMaxima = const Duration(seconds: 15),
      this.largo = Dedicatoria.duracionFragmento});

  final ControlFragmento control;
  final Duration paso;
  final Duration esperaMaxima;
  final Duration largo;

  bool _cancelado = false;
  bool _enMarcha = false;

  bool get enMarcha => _enMarcha;

  /// Cortar ya (al cerrar la tarjeta, por ejemplo). No pausa lo que esté sonando.
  void cancelar() => _cancelado = true;

  String _clave(Json? p) => '${p?['clave'] ?? p?['video_id'] ?? ''}';

  /// Devuelve true si el fragmento llegó a sonar. Nunca lanza: si algo falla, simplemente no suena.
  Future<bool> iniciar(Json pista, Dedicatoria d) async {
    if (_enMarcha) return false;
    _enMarcha = true;
    _cancelado = false;
    try {
      final limpia = Dedicatoria.pistaLimpia(pista);
      final mia = _clave(limpia);
      await control.reproducir(limpia);
      // esperar a que de verdad suene esa canción
      var esperado = Duration.zero;
      while (!(control.sonando() && _clave(control.actual()) == mia)) {
        if (_cancelado || esperado >= esperaMaxima) return false;
        await Future<void>.delayed(paso);
        esperado += paso;
      }
      if (_cancelado) return false;
      if (d.inicio > 0) {
        final dur = control.duracion();
        // si la canción es más corta que el inicio, suena desde el principio
        if (dur == Duration.zero || d.inicio < dur.inSeconds - 5) {
          await control.buscar(Duration(seconds: d.inicio));
        }
      }
      var sonado = Duration.zero;
      while (sonado < largo) {
        await Future<void>.delayed(paso);
        sonado += paso;
        if (_cancelado) return true;
        // la persona cambió de canción o pausó: ya no es asunto de la dedicatoria
        if (_clave(control.actual()) != mia || !control.sonando()) return true;
      }
      await control.pausar();
      return true;
    } catch (_) {
      return false;
    } finally {
      _enMarcha = false;
    }
  }
}
