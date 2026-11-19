// Datos del «Modo gamer»: perfiles de sonido por tipo de juego y listas por
// situación (cada una arranca una radio de YouTube Music).

import 'dart:math' as math;

import 'catalogo.dart';

/// Un ajuste del ecualizador (10 bandas, de 31 Hz a 16 kHz, en dB) pensado para un tipo de juego.
class PerfilSonido {
  const PerfilSonido(this.id, this.nombre, this.detalle, this.bandas);
  final String id;

  /// También es el nombre que se guarda en `eq_preset`.
  final String nombre;
  final String detalle;
  final List<int> bandas;
}

const perfilesSonido = <PerfilSonido>[
  // pasos y disparos: medios-agudos arriba, graves recortados para que no tapen
  PerfilSonido('fps', 'Gamer · FPS', 'Realza medios y agudos para oír pasos', [-3, -2, -1, 0, 1, 3, 5, 6, 4, 2]),
  PerfilSonido('rpg', 'Gamer · RPG épico', 'Graves y agudos amplios, ambiente de cine', [5, 4, 2, 0, -1, 0, 2, 4, 5, 5]),
  PerfilSonido('carreras', 'Gamer · Carreras', 'Graves fuertes para sentir el motor', [8, 7, 5, 2, 0, -1, 0, 1, 2, 2]),
  PerfilSonido('chill', 'Gamer · Chill', 'Suave y cálido, sin agudos cansados', [3, 2, 1, 0, 0, -1, -2, -3, -3, -4]),
];

PerfilSonido? perfilSonidoPorId(String id) {
  for (final p in perfilesSonido) {
    if (p.id == id) return p;
  }
  return null;
}

enum Situacion {
  lobby('Lobby', 'Mientras esperas la partida', [
    'gaming lobby music chill beats',
    'upbeat electronic gaming playlist',
    'synthwave gaming warm up',
  ]),
  concentracion('Concentración', 'Foco total, sin distracciones', [
    'lofi focus gaming concentration',
    'deep focus instrumental electronic',
    'ambient concentration instrumental',
  ]),
  clutch('Clutch', 'Todo se decide ahora', [
    'intense epic gaming music adrenaline',
    'hardstyle drum and bass gaming',
    'epic hybrid trailer intense music',
  ]),
  victoria('Victoria', 'Celebra la partida ganada', [
    'victory celebration epic music',
    'triumphant winning songs',
    'champions anthem upbeat',
  ]),
  derrota('Derrota', 'Para soltar la tensión', [
    'calm relaxing after game lofi',
    'sad chill lofi beats',
    'soft instrumental calm down',
  ]);

  const Situacion(this.nombre, this.detalle, this.consultas);
  final String nombre, detalle;
  final List<String> consultas;
}

typedef BuscarPistas = Future<List<Map<String, dynamic>>> Function(String consulta);
typedef RadioDe = Future<List<Map<String, dynamic>>> Function(String videoId);

Future<List<Map<String, dynamic>>> _buscarYa(String q) => Catalogo.buscar(q, filtro: 'canciones', limite: 8);

Future<List<Map<String, dynamic>>> _radioYa(String videoId) async {
  final r = await Catalogo.radio(videoId: videoId, limite: 40);
  return List<Map<String, dynamic>>.from(r['pistas'] as List);
}

bool _esPista(Map<String, dynamic> m) => '${m['video_id'] ?? ''}'.isNotEmpty;

/// La lista de una situación: busca una canción de ese ambiente y arma su
/// radio; si la radio falla, se quedan los resultados de la búsqueda.
/// Lanza [CatalogoError] (o el error de red) si no hay nada que poner.
Future<List<Map<String, dynamic>>> pistasParaSituacion(
  Situacion s, {
  BuscarPistas? buscar,
  RadioDe? radio,
  math.Random? azar,
}) async {
  final consultas = s.consultas;
  final q = consultas[(azar ?? math.Random()).nextInt(consultas.length)];
  final encontradas = [
    for (final m in await (buscar ?? _buscarYa)(q).timeout(const Duration(seconds: 25)))
      if (_esPista(m)) m
  ];
  if (encontradas.isEmpty) throw CatalogoError('YouTube Music no devolvió canciones para esa lista.');
  try {
    final r = await (radio ?? _radioYa)('${encontradas.first['video_id']}').timeout(const Duration(seconds: 25));
    final pistas = [for (final m in r) if (_esPista(m)) m];
    if (pistas.isNotEmpty) return pistas;
  } catch (_) {/* se sigue con lo buscado */}
  return encontradas;
}
