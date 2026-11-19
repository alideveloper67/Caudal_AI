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

/// Las nueve diapositivas de la quinta actualización grande (2.6.0).
final List<Diapo> diapositivas = [
  Diapo(
    icono: Icons.auto_awesome_rounded,
    titulo: tituloPortada,
    texto: 'Tu reproductor, tu perfil y tus celebraciones. Desliza y descúbrelo.',
    color: const Color(0xFF22D3EE),
    ilustracion: ilusPortada6,
  ),
  Diapo(
    icono: Icons.album_rounded,
    titulo: 'Tu reproductor, a tu estilo',
    texto: 'Elige cómo se ve lo que suena: Vinilo, Casete, Neón o Carátula flotante con tu mascota. Los colores siguen a la carátula y una insignia te dice la calidad real de cada canción.',
    color: const Color(0xFF8B6CFF),
    ilustracion: ilusReproductor,
  ),
  Diapo(
    icono: Icons.mic_rounded,
    titulo: 'Modo karaoke',
    texto: 'La letra se hace gigante y se va llenando mientras cantas, y tu mascota canta contigo.',
    color: const Color(0xFFFF5C8A),
    ilustracion: ilusKaraoke,
  ),
  Diapo(
    icono: Icons.pets_rounded,
    titulo: 'Mascotas con vida',
    texto: 'Tu mascota se duerme si pausas la música, se mueve al paso de la canción y se pone gorrito en las fiestas.',
    color: const Color(0xFF34D399),
    ilustracion: ilusMascotasVida,
  ),
  Diapo(
    icono: Icons.cake_rounded,
    titulo: '¡Feliz cumpleaños!',
    texto: 'El día de tu cumple, Caudal lo celebra contigo con confeti y gorrito. Y tus amigos lo saben para saludarte.',
    color: const Color(0xFFF5C542),
    ilustracion: ilusCumple,
  ),
  Diapo(
    icono: Icons.account_circle_rounded,
    titulo: 'Tu perfil con portada, dedicatorias y cápsula del tiempo',
    texto: 'Pon una portada con tu canción y una frase. Dedica canciones con una tarjeta a quien quieras. Y guarda una canción para tu yo del futuro.',
    color: const Color(0xFF38BDF8),
    ilustracion: ilusPerfil,
  ),
  Diapo(
    icono: Icons.tune_rounded,
    titulo: 'Escucha a tu manera',
    texto: 'Modo auto con botones gigantes para manejar, y los modos Concentración, Dormir y Ejercicio. Además, listas colaborativas para hasta 50 personas, gratis.',
    color: const Color(0xFFFF8A3D),
    ilustracion: ilusModos,
  ),
  Diapo(
    icono: Icons.workspace_premium_rounded,
    titulo: 'Para donadores',
    texto: '¿Qué canción era? para reconocer lo que suena, lo nuevo para ti cada día, tu semana en una tarjeta, un ecualizador que se adapta a tus audífonos y la letra en la pantalla de bloqueo.',
    color: const Color(0xFFF5C542),
    ilustracion: ilusDonadores6,
  ),
  Diapo(
    icono: Icons.favorite_rounded,
    titulo: 'Gracias por escuchar con Caudal',
    texto: 'Esto es solo el comienzo. Lo mejor de Caudal lo hacemos contigo.',
    color: const Color(0xFF22D3EE),
    ilustracion: ilusGracias6,
  ),
];
