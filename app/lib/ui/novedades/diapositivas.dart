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

/// Las trece diapositivas de la tercera actualización grande.
final List<Diapo> diapositivas = [
  Diapo(
    icono: Icons.auto_awesome_rounded,
    titulo: tituloPortada,
    texto: 'Más estilo, más herramientas y una app que va más suave. Desliza y descúbrelo.',
    color: const Color(0xFF22D3EE),
    ilustracion: ilusPortada,
  ),
  Diapo(
    icono: Icons.face_retouching_natural_rounded,
    titulo: 'Lúcete en tu perfil',
    texto: 'Marcos animados para tu foto y nombres con brillo, degradado o arcoíris. Se ven en tu perfil, tus chats y tus amigos.',
    color: const Color(0xFF8B6CFF),
    ilustracion: ilusMarcos,
  ),
  Diapo(
    icono: Icons.palette_rounded,
    titulo: 'Temas exclusivos',
    texto: 'Seis paletas completas (Atardecer, Bosque, Sakura, Océano, Medianoche y Ámbar) que cambian el color de toda la app.',
    color: const Color(0xFFFF8A3D),
    ilustracion: ilusTemas,
  ),
  Diapo(
    icono: Icons.confirmation_number_rounded,
    titulo: 'Pase de prueba',
    texto: 'Canjea un código y usa todos los beneficios de donador durante 7 días. Pídelo a quien te invitó a Caudal.',
    color: const Color(0xFFF5C542),
    ilustracion: ilusPase,
  ),
  Diapo(
    icono: Icons.lyrics_rounded,
    titulo: 'Letras para presumir',
    texto: 'Tarjetas con la carátula difuminada, estilos nuevos y letra animada en video para tus estados e historias. Guarda, copia o comparte.',
    color: const Color(0xFF25D366),
    ilustracion: ilusLetras,
  ),
  Diapo(
    icono: Icons.insights_rounded,
    titulo: 'Tu año en Caudal',
    texto: 'Tus minutos, tu canción y tus artistas del año en tarjetas listas para compartir. Exclusivo de donadores.',
    color: const Color(0xFFFF5C8A),
    ilustracion: ilusAnio,
  ),
  Diapo(
    icono: Icons.album_rounded,
    titulo: 'Mezclador renovado',
    texto: 'Una mesa de DJ que se entiende: elige un estilo, mira cómo se enlazan las canciones y pruébalo antes de reproducir.',
    color: const Color(0xFFB4A1FF),
    ilustracion: ilusMezclador,
  ),
  Diapo(
    icono: Icons.playlist_add_rounded,
    titulo: 'Trae tus listas sin límite',
    texto: 'Pasa listas enteras de YouTube Music, Spotify o Apple Music, la música de Snaptube o una lista de nombres. Sin tope de canciones.',
    color: const Color(0xFF38BDF8),
    ilustracion: ilusImportar,
  ),
  Diapo(
    icono: Icons.headphones_rounded,
    titulo: 'La música no se corta',
    texto: 'La radio se reintenta sola, la conexión se retoma si se cae y la canción sigue justo donde iba.',
    color: const Color(0xFF22D3EE),
    ilustracion: ilusSigue,
  ),
  Diapo(
    icono: Icons.av_timer_rounded,
    titulo: 'Letras que van con la voz',
    texto: 'Elegimos mejor la letra sincronizada y, si una llega corrida, la ajustas de medio en medio segundo con «Sincronía».',
    color: const Color(0xFF4C8DFF),
    ilustracion: ilusSincronia,
  ),
  Diapo(
    icono: Icons.history_rounded,
    titulo: 'Búsquedas recientes',
    texto: 'Una lista limpia: toca para buscar, pasa el texto al buscador con la flecha o quita una con la X.',
    color: const Color(0xFFEC4899),
    ilustracion: ilusBuscar,
  ),
  Diapo(
    icono: Icons.speed_rounded,
    titulo: 'Fluida en cualquier equipo',
    texto: 'Ajustes abre al instante y el modo ligero quita los adornos para que Caudal vaya suave hasta en equipos viejos.',
    color: const Color(0xFF34D399),
    ilustracion: ilusLigero,
  ),
  Diapo(
    icono: Icons.favorite_rounded,
    titulo: 'Gracias por ser parte de Caudal',
    texto: 'Esto es solo el comienzo. Lo mejor de Caudal lo hacemos contigo.',
    color: const Color(0xFF22D3EE),
    ilustracion: ilusFinal,
  ),
];
