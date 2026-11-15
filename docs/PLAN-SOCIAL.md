# Caudal — gran actualización social (Android 2.2.0 · Windows 2.3.0)

Documento de trabajo: qué se construye, cómo se llaman las cosas en la base de datos y qué reglas no se pueden romper.
La base ya está escrita y probada en `supabase/social.sql` (52 comprobaciones en PostgreSQL). **No la cambies**; si algo
falta, anótalo al final de tu informe.

## Reglas del proyecto (obligatorias)

- Todo el texto que ve la gente va **en español, con tildes y eñes**. Nada de jerga: ni «JSON», ni «token», ni nombres de
  variables. Si algo falla, di qué pasó y qué puede hacer la persona.
- Diseño: usa los colores y componentes que ya tiene la app (paleta con color de acento elegible; fondo oscuro). Que se
  sienta como el resto de Caudal, cuidado y elegante: espacios amplios, esquinas redondeadas, animaciones suaves.
- **No hagas `git commit`, `git push`, ni publiques nada.** No toques `ios/`. No subas versiones (`pubspec.yaml`,
  `version.py`, `version.dart`): lo hace quien coordina.
- **No compiles** (`flutter build`, `gradlew`, `pyinstaller`): la PC tiene poca memoria y se cae. Solo `flutter analyze`
  de los archivos que toques, `flutter test` de pruebas concretas y `pytest` de pruebas concretas.
- Pruebas de escritorio: siempre `QT_QPA_PLATFORM=offscreen` y `APPDATA` apuntando a una carpeta temporal (para no tocar
  los datos reales de la persona). Lanza `pytest` desde la carpeta `escritorio/`.
- No guardes archivos de memoria ni nada fuera de `C:\Users\USER\Caudal`.
- Escribe pruebas para lo que construyas (lógica y forma de los datos). El diseño visual en pantalla de escritorio se
  puede comprobar con capturas offscreen (`widget.grab().save(...)`); en Flutter, con pruebas de widgets.
- Cada archivo de código nuevo o tocado debe compilar/analizar sin errores. Lee el código vecino antes de editar y
  respeta su estilo. Evita `dart:io` en la interfaz compartida con la web (usa lo que ya hace el proyecto para web).
- Cuando termines, informa: qué archivos creaste/cambiaste, qué probaste y qué quedó pendiente o dudoso. Sé honesto.

## Conexión con la base (Supabase)

Las dos apps ya hablan con Supabase: Android en `app/lib/nucleo/nube.dart` (`Sesion.pedir`), escritorio en
`escritorio/descargador/nube.py` (`Sesion.pedir`). Las funciones se llaman con `POST /rest/v1/rpc/<nombre>` y un cuerpo
con los parámetros (empiezan con `p_`). El perfil propio se lee y se cambia con `/rest/v1/perfiles?id=eq.<mi id>`.

### Perfil (columnas nuevas de `perfiles`, las cambia su dueño con PATCH)
`bio` (≤300), `frase` (≤80, el «estado»), `foto_url` (ruta `<mi id>/avatar.jpg` en el almacén `avatares`),
`cancion_fav` (objeto `{video_id, titulo, artista, miniatura}`; `miniatura` es la URL de la carátula),
`artista_fav` (≤80), `generos` (hasta 5), `color_perfil` (`#RRGGBB`), `perfil_publico` (bool, por defecto falso),
`mostrar_top` (bool, por defecto verdadero: enseñar mis artistas del mes e insignias).
Los menores de 18 años **no pueden** hacer público su perfil (la base lo fuerza): en la pantalla, explícalo con calidez.

### Fotos
Subir: `POST /storage/v1/object/avatares/<mi id>/avatar.jpg` con `Authorization: Bearer <acceso>`, `apikey`,
`Content-Type: image/jpeg` y `x-upsert: true`. Antes de subir **reduce a 512×512 (recorte cuadrado centrado) y comprime a
JPEG** para que pese menos de 2 MB. Mostrar: `https://nztirmwqykbxadidpzzt.supabase.co/storage/v1/object/public/avatares/<ruta>?v=<marca>`
(añade `?v=` con la fecha de cambio para saltarse la caché). Sin foto: círculo con la inicial y el color del perfil.

### Amistades (solo se escribe a un amigo)
- `enviar_solicitud(p_otro uuid)` → `'enviada' | 'aceptada' | 'ya_amigos' | 'ya_enviada'` (si la otra persona ya te había
  enviado una, se aceptan solas).
- `responder_solicitud(p_id bigint, p_acepta boolean)`, `cancelar_solicitud(p_otro uuid)`, `quitar_amigo(p_otro uuid)`.
- `bloquear(p_otro uuid)`, `desbloquear(p_otro uuid)`, `mis_bloqueados()` → `[{id, usuario, nombre, foto_url}]`.
- `mis_solicitudes()` (recibidas) → `[{id, de, usuario, nombre, foto_url, creado}]`; `mis_enviadas()` →
  `[{id, para, usuario, nombre, foto_url, creado}]`; `mis_amigos()` → `[{id, usuario, nombre, foto_url, desde}]`.
- `buscar_persona(p_usuario text)` (usuario exacto) → `[{id, usuario, nombre, foto_url, relacion}]`.
- `relacion` vale `'yo' | 'amigo' | 'enviada' | 'recibida' | 'ninguna' | 'bloqueado'`.
- `abrir_chat(p_otro uuid)` ahora **falla** si no son amigos (el error dice «primero deben ser amigos»).
  `mis_chats()` trae además `foto_url`.
- Errores conocidos que debes traducir a frases humanas: «espera unos dias para volver a enviarla» (una solicitud
  rechazada no se reenvía antes de 30 días), «tienes demasiadas solicitudes pendientes» (tope 30), «no se puede enviar».

### Perfiles de Caudal (directorio, perfil, me gusta)
- `explorar_perfiles(p_busqueda text, p_limite int, p_desde int)` → `[{id, usuario, nombre, foto_url, bio, cancion_fav,
  color_perfil, relacion, likes, di_like, num_subidas, es_artista}]`. Solo salen perfiles públicos de mayores de 18.
- `ver_perfil(p_usuario text)` → un objeto (o `null` si no existe o hay bloqueo). Si el perfil es privado y no es amigo:
  `{id, usuario, nombre, foto_url, relacion, privado: true, likes: 0, di_like: false, es_artista: false, subidas: [], num_subidas: 0}`.
  Si se puede ver: además `bio, cancion_fav, artista_fav, generos, frase, color_perfil, creado, es_mio, publico,
  mostrar_top, top_artistas [{nombre, portada, veces}], top_canciones [datos de pista + veces], insignias
  [{clave, titulo, detalle}], afinidad (0–100 o null si es el mío), likes, di_like, es_artista, num_subidas,
  subidas [{id, titulo, artista, album, duracion, ruta, portada, escuchas, estado, creado}]`.
- `dar_like(p_otro uuid)` y `quitar_like(p_otro uuid)` → devuelven el total de likes.
- **ARTISTA**: quien llega a **200 likes** recibe la nota «ARTISTA» (`es_artista`). Muéstrala en su perfil con una insignia
  distintiva (dorada, con una estrella o micrófono), también en las tarjetas del directorio y junto a sus canciones.
- **Títulos de fundador** (llegan en `ver_perfil` y en `explorar_perfiles`, y también en la versión «privada» de `ver_perfil`):
  - `fundador` (bool): una de las **100 primeras personas** de Caudal (`numero` ≤ 100; `numero` es el orden de llegada,
    permanente). Se muestra como una nota **«Usuario fundador ★»** con una estrellita, junto al nombre. Con el número es
    bonito enseñar «Fundador n.º 17» en el perfil abierto.
  - `fundador_caudal` (bool): el título especial **«Fundador de Caudal»** (solo lo tienen las cuentas del creador). Debe
    verse **más distinguido** que los demás (por ejemplo, chip con degradado cian→dorado y el logo/corona), y si una
    persona tiene los dos, se muestra solo este primero y el de «Usuario fundador» como secundario. Nunca se calcula en la
    app: viene siempre de la base.
- **Títulos especiales** (`titulos`: lista `[{clave, nombre}]`, también en `explorar_perfiles` y en la versión privada
  de `ver_perfil`): los da solo el creador desde la base. Hoy existen `fundador_caudal` («Fundador de Caudal») y
  `rey_de_la_musica` («Rey de la música», con una corona dorada). Dibuja cada título con el `nombre` que llega, con un chip
  destacado (corona/estrella según la `clave`; una `clave` desconocida usa un chip dorado genérico con estrella), siempre
  por encima de las insignias normales. Nunca se calculan en la app.
- Insignias automáticas (`clave`): `veterano`, `fiel`, `explorador`, `coleccionista`, `maratonista`, `creador`. Dales un
  icono y un color cada una.
- Desde el perfil de otra persona deben poder: **dar/quitar me gusta**, **enviar solicitud de amistad** (el botón cambia
  según `relacion`: «Agregar» / «Solicitud enviada» (cancelable) / «Aceptar solicitud» / «Amigos» → «Escribir»),
  **bloquear** y ver su música subida con las carátulas.

### Música de la gente (subir y escuchar)
- Almacén `musica` (público para leer). Subir con `POST /storage/v1/object/musica/<mi id>/<nombre>` (audio y carátula,
  cada uno en su archivo, `x-upsert: false`). Audio: mp3, m4a/aac, flac, ogg, wav, webm, **máximo 15 MB**. Carátula
  (jpg/png/webp, **obligatoria**): redúcela a 800×800 como máximo y comprímela.
- Después se registra con `registrar_subida(p_titulo, p_artista, p_album, p_duracion, p_ruta, p_portada, p_tamano)` →
  uuid. `p_ruta` y `p_portada` son rutas `<mi id>/<archivo>` dentro de `musica`. **Sin portada no se puede subir** (la
  base lo rechaza): la pantalla debe exigirla antes de enviar, y permitir un nombre de álbum opcional (para que quien
  sube un álbum lo agrupe). Límites: 30 canciones por persona y 10 por día.
  Si el registro falla, **borra los archivos que acabas de subir** (`DELETE /storage/v1/object/musica` con
  `{"prefixes":[ruta, portada]}`).
- `explorar_subidas(p_busqueda, p_limite, p_desde)` → `[{id, user_id, usuario, titulo, artista, album, duracion, ruta,
  portada, escuchas, creado, es_artista}]`; `contar_escucha_subida(p_id)` al empezar a sonar; `borrar_subida(p_id)`
  (y borra también los archivos); `reportar_subida(p_id, p_motivo)` (3 reportes distintos la ocultan);
  el estado propio (`publicada|revision|retirada`) se ve en `ver_perfil` de uno mismo.
- URL para reproducir: `https://nztirmwqykbxadidpzzt.supabase.co/storage/v1/object/public/musica/<ruta>`; carátula igual
  con `portada`. Reproducen con el mismo motor que el resto (revisa cómo se representan hoy las pistas que no son de
  YouTube) y mostrando carátula, título, artista, álbum y quién la subió.
- Aviso de derechos al subir (casilla obligatoria): «Declaro que esta música es mía o tengo permiso para compartirla».
  Todas las listas de música de la comunidad deben tener el botón «Reportar».

## Funciones de las apps (lo que debe quedar hecho)

1. **Versión a la vista**: abajo a la izquierda, siempre, chiquita y discreta (texto tenue, p. ej. `Caudal 2.3.0`), sin
   estorbar a nada ni captar toques. Sale de la constante de versión que ya existe en cada app.
2. **Tu mes pasado** («Vuelve en el tiempo»): una lista con las canciones que más se escucharon el mes pasado
   (mes calendario anterior; si no hay datos, últimos 30 días). Aparece en la «Máquina del tiempo»/Inicio y se puede
   **guardar como lista** con un toque, con nombre como «Lo más escuchado en octubre» y portada de mosaico.
3. **Mezclador** (dos partes):
   - **DJ automático**: un ajuste «Mezcla DJ» en el reproductor que enlaza las canciones solo, como un DJ: la siguiente
     entra antes de que acabe la actual, con cambio de graves, duración configurable (4–16 s) y sin cortes. Reutiliza el
     fundido y la lógica DJ que ya existen (`crossfade`, silencios, `dj_inteligente`).
   - **Mesa del usuario**: pantalla «Mezclador» donde se eligen canciones (de la cola, me gusta o listas), se ordena el
     set, y por cada paso se ajusta cuándo entra la siguiente, cuánto dura el fundido y si cambia los graves; se puede
     **probar** un paso, **reproducir el set** y **guardarlo** como mezcla con nombre.
4. **Perfil propio y de los demás** (ver arriba): editar foto, nombre, descripción, frase, canción favorita con su
   carátula (se elige del catálogo/buscador), artista favorito, géneros, color del perfil, visibilidad pública y qué
   mostrar; ver el de otras personas con tarjeta de portada, insignias, top del mes, música subida, afinidad («Os
   parecéis un 78 %»), me gusta y botón de amistad.
   Más ideas ya incluidas para personalizar: frase de estado, color de perfil que tiñe toda la tarjeta, insignias,
   top de artistas del mes, canción favorita con carátula grande, música subida, afinidad musical con quien mira.
5. **Directorio «Perfiles de Caudal»**: rejilla de tarjetas con foto, nombre, usuario, descripción corta, canción
   favorita (con carátula pequeña), insignia ARTISTA y número de canciones subidas; buscador y paginación al llegar al
   final. Ahí mismo se puede dar me gusta y enviar solicitud.
6. **Amigos y solicitudes**: en Mensajes, pestañas «Chats», «Solicitudes» y «Amigos»; buscar por usuario exacto y enviar
   solicitud; aceptar/rechazar; quitar amigo; bloquear/desbloquear. Insignia con el número de solicitudes nuevas.
   Nadie puede escribir a quien no es amigo: sin solicitud aceptada no existe botón de chat.
7. **Subir música y música de la comunidad**: pantalla para subir (audio, carátula obligatoria, título, artista, álbum
   opcional, casilla de derechos, barra de progreso) y para ver, escuchar, reportar y borrar. Pestaña «Comunidad» con el
   catálogo y buscador.
8. **Aviso de novedades grande** (ver abajo).

## Aviso de novedades grande

Al abrir la versión nueva por primera vez (guarda la última versión vista) y cuando se avisa de una actualización grande,
en lugar del aviso normal sale una pantalla **grande y bonita** (a pantalla casi completa, con animación de entrada,
degradado con el color de acento y tarjetas que aparecen una a una) con este contenido. Botón «Empezar» (o «Actualizar
ahora» si es el aviso previo). Se puede cerrar con la X.

Título: **«La actualización más grande de Caudal»** · subtítulo: «Perfiles, amigos, tu propia música y un DJ dentro de la app».

| Icono | Titular | Texto |
|---|---|---|
| personas | Perfiles de verdad | Foto, descripción, canción favorita con su carátula, color propio e insignias. |
| usuario+ | Amigos con solicitud | Nadie te escribe sin tu permiso: primero llega una solicitud. |
| brújula | Descubre gente | El directorio de perfiles, me gusta y la nota ARTISTA al llegar a 200. |
| nube/subir | Sube tu música | Con carátula y álbum. La escucha toda la comunidad. |
| discos | Mezclador | Un DJ automático y tu propia mesa para mezclar a tu gusto. |
| reloj | Tu mes pasado | Una lista con lo que más escuchaste el mes pasado. |
| paleta | Colores al instante | El color y el fondo cambian sin cerrar Caudal. |
| estrella | Logo nuevo | Y la versión siempre a la vista, abajo a la izquierda. |

Reglas: aparece una sola vez por versión; si la persona está escuchando música no la interrumpe; accesible (se puede
leer con lector de pantalla); en pantallas pequeñas las tarjetas pasan a una sola columna con desplazamiento.
El aviso previo a actualizar (cuando una release lo marca con la línea `[grande]` al inicio de sus notas) usa el mismo
diseño con el botón «Actualizar ahora» en lugar de «Empezar»; si no está marcada, sale el aviso normal.

## Reparto del trabajo y propiedad de archivos

Cuatro frentes en paralelo; cada uno **solo edita lo suyo** y, si debe tocar un archivo compartido (menú, ajustes,
`armazon.dart`, `ventana.py`), hace el cambio mínimo, releyendo el archivo justo antes de editarlo.

- **Android – social** (`app/lib/nucleo/nube.dart`, `nucleo/social*.dart`, `ui/paginas/perfil*`, `directorio*`,
  `amigos*`, `subir_musica*`, `mensajes_pagina.dart`): puntos 4, 5, 6 y 7.
- **Android – reproductor** (`reproduccion/reproductor.dart`, `nucleo/recomendador.dart`, `nucleo/transiciones.dart`,
  `ui/paginas/mezclador*`, `ui/armazon.dart`, `ui/novedades*`): puntos 1, 2, 3 y 8.
- **Escritorio – social** (`escritorio/descargador/nube.py`, `social.py`, `ui/paginas/perfil*`, `directorio*`, `amigos*`,
  `subir_musica*`, `ui/paginas/mensajes.py`): puntos 4, 5, 6 y 7.
- **Escritorio – reproductor** (`reproduccion.py`, `recomendador.py`, `ui/paginas/mezclador*`, `ui/ventana.py`,
  `ui/novedades*`): puntos 1, 2, 3 y 8.

**La navegación nueva** (entradas «Perfiles», «Mi perfil», «Subir música», «Mezclador» en el menú lateral / barra de
abajo / Ajustes) **la conecta quien coordina al final**. Cada frente deja su pantalla lista con una clase de entrada
clara (por ejemplo `PerfilPagina(usuario: ...)`, `DirectorioPagina`, `AmigosPagina`, `SubirMusicaPagina`,
`MezcladorPagina`; en escritorio, páginas que se crean con `PaginaX(ctx)` como las de `ui/paginas/`) y lo explica en su
informe: cómo se abre, qué parámetros recibe y desde dónde debería enlazarse. Dentro de tu propio módulo sí enlaza todo
(por ejemplo, del directorio al perfil, del perfil al chat, de la tarjeta de música al reproductor).
**No edites** el menú principal (`armazon.dart` / `ventana.py` / `ajustes`) salvo lo que pide el punto 1 (versión) y el
punto 8 (aviso de novedades), que son del frente «reproductor».
