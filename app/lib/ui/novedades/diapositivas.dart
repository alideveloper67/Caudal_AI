import 'package:flutter/material.dart';

import 'ilustraciones.dart';

/// Una diapositiva de la presentación: su texto, su color y su ilustración.
class Diapo {
  const Diapo({
    required this.icono,
    required this.titulo,
    required this.texto,
    required this.color,
    required this.ilustracion,
  });

  final IconData icono;
  final String titulo;
  final String texto;
  final Color color;
  final Widget Function(Ctx c, double lado) ilustracion;
}

/// El título de la portada (también lo usa el aviso previo a actualizar).
const tituloPortada = 'ACTUALIZACIÓN GRANDE DE CAUDAL';

/// Las siete diapositivas de la cuarta actualización grande (2.5.0).
final List<Diapo> diapositivas = [
  Diapo(
    icono: Icons.auto_awesome_rounded,
    titulo: tituloPortada,
    texto: 'Modo gamer, tu personaje cobra vida y regalos para tus amigos. Desliza y descúbrelo.',
    color: const Color(0xFF22D3EE),
    ilustracion: ilusPortada5,
  ),
  Diapo(
    icono: Icons.sports_esports_rounded,
    titulo: 'Modo gamer',
    texto: 'Sube de nivel con XP, cumple misiones diarias y mantén tu racha. Sonido para cada tipo de juego (FPS, RPG, Carreras y Chill), listas para cada momento (Lobby, Concentración, Clutch, Victoria y Derrota), ahorro de batería al jugar y tema RGB neón.',
    color: const Color(0xFF8B6CFF),
    ilustracion: ilusGamer,
  ),
  Diapo(
    icono: Icons.pets_rounded,
    titulo: 'Tu personaje cobra vida',
    texto: 'El personaje del fondo se arrastra a donde quieras y baila suave al ritmo de la música. Toca dos veces y vuelve a su esquina.',
    color: const Color(0xFFFF7BAC),
    ilustracion: ilusPersonaje,
  ),
  Diapo(
    icono: Icons.auto_fix_high_rounded,
    titulo: 'Enriquece tus listas',
    texto: 'Toca «Enriquecer» en tus listas y te sugerimos canciones parecidas y de los mismos artistas. Escúchalas un momento y añade las que quieras.',
    color: const Color(0xFF38BDF8),
    ilustracion: ilusEnriquece,
  ),
  Diapo(
    icono: Icons.card_giftcard_rounded,
    titulo: 'Regala una prueba',
    texto: 'Donadores: crea códigos para que tus amigos prueben durante 7 días los beneficios de donador.',
    color: const Color(0xFFF5C542),
    ilustracion: ilusRegalo,
  ),
  Diapo(
    icono: Icons.touch_app_rounded,
    titulo: 'Escuchar es más cómodo',
    texto: 'Doble toque en la carátula para dar me gusta y desliza para cambiar de canción. Reordena la cola y guárdala como lista, toca «después de esta», disfruta de un play y pausa suaves y retoma tus sets largos donde los dejaste.',
    color: const Color(0xFF34D399),
    ilustracion: ilusComodo,
  ),
  Diapo(
    icono: Icons.favorite_rounded,
    titulo: 'Gracias por escuchar con Caudal',
    texto: 'Esto es solo el comienzo. Lo mejor de Caudal lo hacemos contigo.',
    color: const Color(0xFF22D3EE),
    ilustracion: ilusGracias,
  ),
];
