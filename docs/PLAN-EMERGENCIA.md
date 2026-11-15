# Caudal — ronda de emergencia (Android 2.2.1 · Windows 2.3.1)

Se suma a `docs/PLAN-SOCIAL.md` (mismas reglas: español con tildes, sin jerga, no commit, no subir versiones, no compilar,
no tocar `ios/`; pruebas con `APPDATA` temporal y `QT_QPA_PLATFORM=offscreen`). La base ya está actualizada y probada en
`supabase/social.sql` (104 comprobaciones): **no la cambies**. Tienes que terminar **rápido** (es una emergencia) y con calidad.

## Lo que ya está resuelto en el servidor (para que lo sepas)
- **No se podía guardar la foto de perfil** («no tienes permiso»): era una política del almacén que faltaba. Ya está
  arreglada en la base real; el código de subida de foto/portada no necesita cambios de permisos. Aun así, que el mensaje
  de error de la app sea comprensible y que, si falla, diga qué hacer.
- Columna nueva `perfiles.banner_url` (imagen de fondo del perfil) y `ver_perfil` / `explorar_perfiles` la devuelven
  (`banner_url`, ruta `<mi id>/banner.jpg` en el almacén `avatares`).
- **Revisión de la música**: ahora todo lo que sube la gente queda en estado `pendiente` hasta que la moderación lo
  aprueba. Solo se publica directo lo de los «Fundador de Caudal» y los moderadores.

## Contrato nuevo
- `publica_directo()` → bool (¿lo que subo se publica sin revisión?). Después de subir, la pantalla debe decir: si es
  `true`: «Listo: tu canción ya está en la comunidad»; si es `false`: «Tu canción quedó en revisión. El equipo de Caudal la
  revisará y te avisaremos aquí si se aprueba» (nunca digas que ya está publicada si es `false`).
- Estados de una canción propia en `ver_perfil(...).subidas[].estado`: `pendiente` («En revisión»), `publicada`,
  `revision` («En revisión por reportes»), `retirada` («Rechazada» + el motivo en `nota`). Cada canción lleva `nota`.
- `soy_moderador()` → bool; `revision_contar()` → int; `revision_pendientes(p_limite int)` →
  `[{id, user_id, usuario, nombre, titulo, artista, album, duracion, ruta, portada, tamano, estado, reportes,
  motivos (lista de textos), creado}]`; `revision_resolver(p_id uuid, p_aprobar boolean, p_nota text)` (la nota es el
  motivo del rechazo, visible para quien subió la canción). Solo funcionan para la cuenta de moderación (usuario
  `moderacion`); para el resto devuelven vacío/0 o error «no tienes permiso para revisar».

## Tareas por frente

### Android – social
1. **Pantalla «Revisión de música»** (solo si `soy_moderador()`): lista de pendientes con carátula grande, título, artista,
   álbum, quién la subió (con enlace a su perfil), duración, reportes y motivos; botón **reproducir** para escucharla antes
   de decidir (usa la URL pública `musica/<ruta>`), botones **Aprobar** y **Rechazar** (con un cuadro para el motivo, con
   motivos rápidos: «No es tuya», «Mala calidad», «Contenido inadecuado», «Duplicada»). Se actualiza al decidir y tiene
   estado vacío amable («No hay nada por revisar»). En `MenuComunidad` (archivo `ui/menu_comunidad.dart`, ya creado por
   quien coordina) añade la entrada «Revisión de música» **solo si es moderador**, con el contador de pendientes.
2. **Subir música**: mensaje tras subir según `publica_directo()` (arriba); en «Mis canciones» y en el perfil propio,
   mostrar `En revisión` / `Rechazada: motivo` con colores suaves distintos.
3. **«Nuevo mensaje» solo con amigos**: hoy el diálogo deja escribir cualquier usuario. Debe mostrar **solo la lista de
   amigos** (con buscador local y foto) para elegir; sin campo libre. Para agregar gente: botón «Agregar un amigo» que
   lleva a Amigos (búsqueda por usuario exacto → «Enviar solicitud»). Quien no es amigo nunca puede recibir un mensaje.
4. **Foto de perfil**: revisa el flujo completo (recorte → subida → guardar `foto_url` → refrescar) y asegúrate de que
   un error muestre un texto útil; añade una prueba del cuerpo/cabeceras de la subida.
5. **Rediseño de perfiles + imagen de fondo**: encabezado con la imagen de fondo (`banner_url`) a todo el ancho con
   degradado oscuro por encima, avatar grande que se solapa con el borde del banner, nombre/títulos/frase sobre
   un panel de cristal; tarjetas con bordes suaves y animación de entrada; estadísticas en fila; la canción favorita con
   carátula grande y reflejo del color del perfil; si no hay banner, degradado con el color del perfil (como ahora). En
   «Editar perfil»: elegir/quitar imagen de fondo (recorte a 1280×480, JPEG < 2 MB; sube a `avatares/<mi id>/banner.jpg`
   con `x-upsert: true`, igual que la foto) con vista previa en vivo. Las tarjetas del directorio usan el banner de fondo.
   Piensa más ideas para personalizarlo y hazlas si caben (por ejemplo: forma del avatar, tamaño del banner, fuente del nombre).

### Android – reproductor
1. **Una equis para quitar la canción**: el mini reproductor de abajo nunca se puede quitar y estorba al hacer capturas.
   Pon una equis **pequeña y bien encajada** (icono de 16–18 px, zona de toque de 32×32, en la esquina superior derecha del
   mini reproductor, sin desplazar los botones actuales) que **detiene la reproducción y oculta el mini reproductor**
   (vuelve al tocar una canción). También deslizar el mini reproductor hacia abajo lo quita.
2. **Mezclador avanzado, «como el de Spotify y mejor»** (ver abajo, «Mezclador avanzado»).

### Escritorio – social
Las mismas tareas 1 a 5 de «Android – social», adaptadas al escritorio (`ui/paginas/…`, `social.py`): pantalla de revisión
(página `PaginaRevision(ctx)`, en `ui/paginas/revision.py`, con su entrada en el panel lateral que conecta quien coordina:
déjalo explicado), subida con mensajes correctos, «Nuevo mensaje» solo con amigos, foto de perfil y rediseño con
banner. El visor de imágenes y las tarjetas deben seguir el tema en vivo (usa `C[...]`).

### Escritorio – reproductor
**Mezclador avanzado, «como el de Spotify y mejor»** (ver abajo), en `PaginaMezclador` y `mezcla_dj.py`/`reproduccion.py`.

## Mezclador avanzado
El mezclador actual es básico (orden + 3 deslizadores por paso). El usuario pide que sea **como la mezcla automática de
Spotify (Automix/DJ) y todavía mejor**, para quien quiera mezclar a mano. Prioriza lo que se pueda hacer **bien y probado**;
lo demás déjalo como siguiente paso y dilo en el informe. Ideas, en orden de valor:
1. **BPM y energía por canción**: detectarlo del audio (decodifica unos segundos con lo que ya trae la app —ffmpeg— y
   estima el tempo por autocorrelación del pulso; si la canción no se puede analizar, permite escribirlo o «tocar el
   ritmo»). Guarda el resultado en caché local para no recalcularlo. Pruébalo con audio sintético de BPM conocido.
2. **Ordenar como un DJ**: botón «Ordenar mi set» que reordena por tempo y energía para que el paso entre canciones sea
   suave, y marca con colores qué pasos «encajan» (tempos parecidos) y cuáles chocan.
3. **Mezcla a tempo** (beatmatching): al mezclar dos canciones, igualar el tempo de la que entra al de la que sale (hasta
   ±6–8 %, conservando el tono con el filtro de estiramiento de tiempo del motor) y entrar **alineada con el compás**.
4. **Tipos de transición** por paso: Fundido, Corte en el compás, Filtro (barrido de pasa-bajos/pasa-altos), Eco de salida
   y Cambio de graves; con duración y punto de entrada ajustables (por compases o por segundos).
5. **Ecualizador de 3 bandas por canción en la mezcla** y curva del fader (lineal / suave / corte rápido).
6. **Puntos de entrada y salida editables** por canción (marcadores) con vista de onda/barras de energía y reproducción
   del tramo para probarlo; «Probar este paso» con los dos motores reales.
7. **Mezcla automática de la cola o de una lista** con un toque («Mezclar esta lista como un DJ») y ajustes sencillos
   («Suave», «Club», «Rápida»).
8. Guardar y volver a abrir mezclas (ya existe) incluyendo los nuevos parámetros; compatibilidad con las guardadas.
Si una capacidad no está disponible en el motor del teléfono (por ejemplo, estiramiento de tiempo), degrádalo con
elegancia y dilo en la pantalla (sin jerga), sin romper la reproducción normal.
