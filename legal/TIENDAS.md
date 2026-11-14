# Subir Caudal a Google Play y al App Store

Todo lo que piden las tiendas, listo para copiar. La web está en Netlify: https://caudal-musica.netlify.app

## Enlaces que piden

| Qué | Enlace |
|---|---|
| Política de privacidad | https://caudal-musica.netlify.app/privacidad.html |
| Términos y condiciones | https://caudal-musica.netlify.app/terminos.html |
| Eliminar la cuenta (web) | https://caudal-musica.netlify.app/eliminar-cuenta.html |
| Web de la app | https://caudal-musica.netlify.app/ |
| Contacto / soporte | https://github.com/alideveloper67/Caudal_AI/issues |

Google Play también exige un **correo de contacto** en la ficha (no se publica en la app). Usa uno propio de Caudal.

## Archivo que se sube

- **Google Play:** `salida/movil-v2.1.0/Caudal-2.1.0-play.aab` (variante «play»: sin actualizador propio ni permisos restringidos).
  - Se firma con la clave de `app/android/key.properties`. Activa «Firma de apps de Google Play» y sube esa clave como clave de subida. **Guarda copia de la clave: si se pierde, no se puede actualizar la app nunca más.**
- **Los APK de GitHub** (variante «directo») son los que se reparten a mano y se actualizan solos.

## Ficha de la tienda

**Nombre:** Caudal — Música y videos

**Descripción breve (80 caracteres):** Música y videos con letras traducidas, mezclas con amigos y recomendaciones.

**Descripción completa:**

> Caudal es tu reproductor de música y videos.
>
> • Letras sincronizadas con traducción al español debajo de cada línea.
> • «Descubre para ti» y «Canciones similares»: recomendaciones que aprenden de lo que escuchas y de lo que saltas.
> • Chat con tus amigos: mándales canciones y escúchalas con un toque.
> • «Mezcla con un amigo»: una lista con lo que escuchan los dos y cuánto se parecen sus gustos.
> • Escuchar juntos: la misma música a la vez en varios teléfonos, con chat y reacciones.
> • Máquina del tiempo: vuelve a lo que escuchabas hace un mes o un año.
> • Trae tus listas de Spotify, Apple Music y YouTube Music, y las canciones de tu teléfono.
> • Ecualizador, temporizador para dormir y transiciones como un DJ.
> • Elige el color y el fondo de la app.
> • La misma cuenta en el teléfono y en la computadora.

**Categoría:** Música y audio · **Etiquetas:** reproductor de música, letras, listas

**Capturas:** al menos 2 del teléfono (Inicio, reproductor con letra, chat). Icono 512×512: `web/icono.png` ampliado desde el original.

## Seguridad de los datos (formulario de Google Play)

| Pregunta | Respuesta |
|---|---|
| ¿Recoge o comparte datos? | Sí |
| ¿Están cifrados en tránsito? | Sí (HTTPS) |
| ¿Se pueden pedir que se borren? | Sí: en la app (Ajustes → Privacidad → Eliminar mi cuenta) y en la web |
| **Información personal → Nombre** | Recogido · Obligatorio · Funcionalidad de la app, gestión de la cuenta |
| **Información personal → Otra información (fecha de nacimiento, país, género)** | Recogido · Fecha y país obligatorios, género opcional · Gestión de la cuenta (edad mínima) y analíticas · **Compartido** solo si el usuario da permiso, de forma anónima y agregada |
| **Información personal → ID de usuario** | Recogido · Gestión de la cuenta |
| **Mensajes → Otros mensajes en la app** | Recogido · Funcionalidad de la app (chat) · No compartido |
| **Actividad en apps → Interacciones con la app / Historial (lo que se escucha)** | Recogido · Funcionalidad y personalización · **Compartido** solo con permiso, anónimo y agregado |
| Ubicación, contactos, fotos, audio, pagos, salud | No |
| Identificadores de publicidad | No |

**¿Se comparten datos con terceros?** Sí, y es opcional: estadísticas anónimas de hábitos de escucha (por rango de edad, país y género), en grupos de 10 personas o más, solo de quienes marcaron la casilla y nunca de menores de 18 años.

## Clasificación de contenido (cuestionario IARC)

- Categoría: Música / entretenimiento.
- Permite que los usuarios se comuniquen: **Sí** (chat entre usuarios y chat de sala).
- Comparte la ubicación: No. Compras: No. Contenido generado por usuarios visible para todos: No (los chats son privados).
- Resultado esperado: «Mayores de 12» o similar, por el chat.

## Público objetivo

Mayores de 13 años. **No** marcarla como app para niños (Caudal pide la edad y exige permiso del tutor a menores de 14).

## Permisos (variante play)

- `INTERNET`, `ACCESS_NETWORK_STATE`: música en streaming.
- `FOREGROUND_SERVICE_MEDIA_PLAYBACK`, `WAKE_LOCK`: seguir sonando con la pantalla apagada.
- `POST_NOTIFICATIONS`: controles de la música en la notificación.
- `READ_MEDIA_AUDIO`: importar canciones del teléfono.

## Riesgo importante: el contenido de YouTube

Google Play suele **rechazar o retirar** las apps que reproducen o descargan contenido de YouTube fuera de la app oficial: lo prohíben las condiciones de YouTube y la política de propiedad intelectual de Play. Caudal hace las dos cosas, así que **es probable que la revisión la rechace o la retire después**, aunque todo lo demás esté en regla. Opciones:

1. Publicarla igual y ver qué dice la revisión.
2. Repartirla fuera de Play, como ahora (APK desde la web y GitHub). Es lo que hacen apps parecidas.
3. Hacer una versión para Play solo con música de licencia libre o con un servicio con licencia.

El App Store de Apple es aún más estricto con esto.

## App Store (iPhone)

- Necesita una cuenta de desarrollador de Apple (99 USD al año) y firmar en Codemagic con esa cuenta.
- Etiqueta de privacidad: las mismas categorías que el formulario de Google («Datos usados para rastrearte»: **No**).
- Eliminar la cuenta desde la app: hecho (Ajustes → Privacidad).
- «Iniciar sesión con Apple» solo es obligatorio si se ofrece entrar con Google. Ese botón está apagado, así que no hace falta.
- El riesgo de YouTube de arriba también aplica.
