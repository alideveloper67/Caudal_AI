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

/// Las once diapositivas de la segunda actualización grande.
final List<Diapo> diapositivas = [
  Diapo(
    icono: Icons.auto_awesome_rounded,
    titulo: tituloPortada,
    texto: 'Mucho nuevo para escuchar, compartir y sentir. Desliza y descúbrelo.',
    color: const Color(0xFF22D3EE),
    ilustracion: ilusPortada,
  ),
  Diapo(
    icono: Icons.wallpaper_rounded,
    titulo: 'Tu imagen, detrás de todo',
    texto: 'Pon tu foto tenue de fondo en toda la app y ajústala a tu gusto. Exclusivo de donadores.',
    color: const Color(0xFF8B6CFF),
    ilustracion: ilusFondo,
  ),
  Diapo(
    icono: Icons.workspace_premium_rounded,
    titulo: 'Donadores de Caudal',
    texto: 'Una etiqueta dorada, un fondo exclusivo y GIF animados en tu foto y en tu fondo de perfil, con búsqueda segura.',
    color: const Color(0xFFF5C542),
    ilustracion: ilusDonadores,
  ),
  Diapo(
    icono: Icons.album_rounded,
    titulo: 'Modo vinilo',
    texto: 'Un disco que gira, un brazo que baja la aguja y la pantalla encendida mientras suena.',
    color: const Color(0xFFFF5C8A),
    ilustracion: ilusVinilo,
  ),
  Diapo(
    icono: Icons.timer_rounded,
    titulo: 'Modo estudio',
    texto: 'Temporizador, lluvia, mezclador de sonidos ambientales, Pomodoro y tu racha de días.',
    color: const Color(0xFF4C8DFF),
    ilustracion: ilusEstudio,
  ),
  Diapo(
    icono: Icons.headphones_rounded,
    titulo: 'La música no se corta',
    texto: 'Sigue sonando con la pantalla apagada y mientras usas otras apps.',
    color: const Color(0xFFB4A1FF),
    ilustracion: ilusSigue,
  ),
  Diapo(
    icono: Icons.ios_share_rounded,
    titulo: 'Comparte lo que te gusta',
    texto: 'Tu perfil como estado de WhatsApp o historia, y tus letras favoritas como tarjeta.',
    color: const Color(0xFF25D366),
    ilustracion: ilusCompartir,
  ),
  Diapo(
    icono: Icons.interests_rounded,
    titulo: 'Gustos que se notan',
    texto: 'Elige tus artistas favoritos al crear la cuenta. Y las canciones parecidas ahora sí se parecen.',
    color: const Color(0xFFFF8A3D),
    ilustracion: ilusArtistas,
  ),
  Diapo(
    icono: Icons.photo_library_rounded,
    titulo: 'Tus listas, tu portada',
    texto: 'Usa cualquier imagen como portada de tus listas.',
    color: const Color(0xFFEC4899),
    ilustracion: ilusListas,
  ),
  Diapo(
    icono: Icons.devices_rounded,
    titulo: 'Para cualquier pantalla',
    texto: 'Se adapta a tu pantalla, va más rápido y se ve más bonito. En escritorio, arrastra con el ratón; el resumen es más tranquilo.',
    color: const Color(0xFF38BDF8),
    ilustracion: ilusPantallas,
  ),
  Diapo(
    icono: Icons.favorite_rounded,
    titulo: 'Gracias por ser parte de Caudal',
    texto: 'Esto es solo el comienzo. Lo mejor de Caudal lo hacemos contigo.',
    color: const Color(0xFF22D3EE),
    ilustracion: ilusFinal,
  ),
];
