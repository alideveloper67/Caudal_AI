# Caudal Escritorio 2.0

Reproductor de música y video para Windows con todo YouTube Music y YouTube
dentro, sin anuncios, en máxima calidad, y con descargas en el formato que
quieras. Lo que descargas queda en tu biblioteca y suena sin internet.

---

## Cuenta

Al abrir Caudal la primera vez creas tu cuenta (usuario y contraseña). Cada
cuenta tiene su propia biblioteca, listas, me gusta y ajustes. La primera que
se crea se queda con lo que ya había en el equipo. Con **Mantener la sesión
iniciada** entra directo la próxima vez; para salir: círculo con tu inicial
(arriba a la derecha) → Cerrar sesión. Las cuentas viven en este equipo y la
contraseña se guarda cifrada (PBKDF2).

## Lo que hace

### Como Spotify

- **Inicio** con saludo, atajos a lo último que escuchaste, *Volver a
  escuchar*, *Tus mixes* (hechos con tus artistas más escuchados) y las
  secciones de YouTube Music de tu país: Selección rápida, novedades,
  tendencias, géneros.
- **Buscar** con resultado principal, canciones, artistas, álbumes, listas y
  videos; filtros por tipo y búsquedas recientes. Si pegas un **enlace** de
  cualquiera de ~1800 sitios, ofrece escucharlo, verlo o descargarlo.
- **Artistas** (foto a todo lo ancho, oyentes, populares, discografía,
  *Seguir*, radio), **álbumes** y **listas** con cabecera del color de la
  portada.
- **Tu biblioteca**: Tus me gusta, tus listas (con mosaico de portadas,
  fijadas arriba), álbumes y listas guardados, artistas que sigues, y lo
  descargado. Arrastra una canción encima de una lista para añadirla.
- **Cola** como la de Spotify: *Siguiente en tu cola* (lo que añades a mano va
  primero), *Siguiente de…* y **reproducción automática** con canciones
  parecidas cuando se acaba.
- **Letra sincronizada** que avanza sola sobre el color de la portada; clic en
  una línea para saltar ahí.
- **Súper volumen** (Fuerte, Muy fuerte, Fiesta, Máximo): sube mucho el volumen
  percibido con un limitador de pico real, así no satura. Botón del altavoz en
  la barra de abajo.
- El ecualizador se oye en vivo mientras lo mueves, pero solo se guarda con
  **Guardar**; Cancelar o cerrar lo deja como estaba.
- Quitar algo de una lista, de Tus me gusta o de la cola se puede **deshacer**
  desde el aviso.
- Aleatorio, repetir (todo / una), **fundido entre canciones** (0–12 s),
  **normalizar volumen** (-14 LUFS), **ecualizador de 10 bandas** con 14
  ajustes listos, velocidad sin cambiar el tono, **temporizador para dormir**.
- Al abrir, **retoma** la cola donde la dejaste.

### Como YouTube Premium

- **Sin anuncios** y **en segundo plano**: al cerrar la ventana sigue sonando
  junto al reloj (bandeja). Para salir del todo: clic derecho → Salir.
- **Mini reproductor** flotante, siempre encima, con el video o la portada.
- Pasar de canción a video, a la ventanita y de vuelta **sin cortes**: lo que
  suena sigue hasta que la otra pantalla tiene la imagen en el mismo punto.
  El video de la canción se prepara por adelantado mientras escuchas.
- Video en **máxima calidad**: hasta 8K y HDR, imagen y sonido por separado
  como los sirve YouTube. Calidad, códec, subtítulos, velocidad y capítulos
  se cambian mientras ves. **Pantalla completa** con controles que se
  esconden.
- **Calidad adaptable**: si el equipo pierde cuadros, baja un escalón y avisa.
- **Solo audio**: deja de ver el video y sigue escuchándolo.
- **Saltar lo que no es música** (intros habladas, finales) y, si quieres,
  patrocinios, con la base pública de SponsorBlock.
- Las **teclas multimedia** del teclado y la ventanita de volumen de Windows
  controlan Caudal.

### Descargas

Cualquier canción, álbum, lista o video se descarga desde su menú
(**Descargar ›**) o desde **Descargar videos**: pegas el enlace de cualquier
sitio (YouTube, TikTok, Instagram, Facebook, X, Telegram… ~1800) y aparece una
vista previa con su portada y calidad para escucharlo, verlo o bajarlo:

| Formato | Qué obtienes |
|---|---|
| MP3 320 kbps (o 256/192/128/V0) | Lo abre todo |
| M4A / AAC | El AAC de YouTube, sin recomprimir |
| OPUS | El Opus original (~160 kbps), la mejor calidad de YouTube |
| FLAC / WAV | Para editar o equipos que lo piden |
| Video máxima calidad | Hasta 8K y HDR (AV1/VP9) en MP4, MKV o WEBM |
| Video compatible | H.264 + AAC hasta 1080p, para TV y móviles antiguos |
| Solo video | La imagen sin sonido |

*Más opciones y formatos exactos…* muestra todos los formatos que ofrece el
enlace (resolución, códec, bitrate, tamaño) para elegir uno concreto. Lo
descargado lleva título, artista y portada, y aparece en *Música descargada* /
*Videos descargados*. Una canción ya descargada suena desde el disco.

---

## Atajos

| Atajo | Qué hace |
|---|---|
| Espacio | Reproducir / pausar |
| Ctrl+→ / Ctrl+← | Siguiente / anterior |
| Shift+→ / Shift+← | Adelantar / atrasar 10 s |
| Ctrl+↑ / Ctrl+↓ | Volumen |
| Ctrl+K o Ctrl+L | Buscar |
| Alt+← / Alt+→ | Atrás / adelante |
| Ctrl+S / Ctrl+R | Aleatorio / repetir |
| Ctrl+M | Mini reproductor |
| Ctrl+Shift+L / Ctrl+Shift+Q | Letra / cola |
| Ctrl+D / Ctrl+, | Descargas / Ajustes |
| F11 | Pantalla completa (en un video) |
| En el video: F, K, J, L, ←, →, M, I | Como en YouTube |
| Ctrl+V | Pega un enlace y lo abre |

También puedes **arrastrar** enlaces o archivos de audio/video a la ventana.

---

## Cuenta de YouTube (opcional)

Sin cuenta funciona todo. Con tu sesión (si tienes Premium) llega el audio de
256 kbps y los videos con restricción de edad: **Ajustes → Tu cuenta de
YouTube** y elige el navegador donde la tienes abierta (ciérralo antes de
reproducir para que Windows deje leer la sesión).

---

## Cómo está hecho

```
escritorio/
├── ejecutar.py                 arranque
├── descargador/
│   ├── main.py                 crea todo; una sola instancia abierta
│   ├── catalogo.py             YouTube Music (buscar, inicio, artistas, álbumes,
│   │                           listas, radio), letras (LRCLIB), SponsorBlock y
│   │                           resolución de streams con yt-dlp
│   ├── reproduccion.py         motor libmpv: cola, fundido, ecualizador, video
│   ├── mpv_carga.py            encuentra y carga libmpv-2.dll
│   ├── coleccion.py            me gusta, listas, escuchas, guardados (SQLite)
│   ├── cuentas.py              cuentas locales y perfil activo
│   ├── motor.py                cola de descargas (yt-dlp + ffmpeg)
│   ├── historial.py            registro de descargas
│   ├── hilos.py                trabajo en segundo plano sin congelar la ventana
│   └── ui/
│       ├── ventana.py          paneles, navegación, bandeja, atajos
│       ├── contexto.py         acciones compartidas y menús de clic derecho
│       ├── componentes.py      filas, tarjetas, carruseles, cabeceras
│       ├── barra_reproduccion.py, panel_lateral.py, panel_derecho.py
│       ├── video.py            vista de video y mini reproductor
│       ├── acceso.py           pantalla de iniciar sesión / crear cuenta
│       ├── ecualizador.py, dialogo_descarga.py, imagenes.py
│       └── paginas/            inicio, buscar, explorar, artista, colección,
│                               biblioteca, descargas, ajustes
├── pruebas/test_logica.py      python -m pytest pruebas -q
└── bin/                        ffmpeg, ffprobe y mpv/libmpv-2.dll
```

**Por qué libmpv:** es el motor del reproductor mpv. Reproduce las dos pistas
separadas de YouTube (imagen + sonido) que hacen falta para pasar de 1080p,
decodifica por hardware cuando la tarjeta puede, y trae los filtros de sonido
(ecualizador, normalización, velocidad sin cambiar el tono). La DLL viene de
las compilaciones públicas de shinchiro (github.com/shinchiro/mpv-winbuild-cmake).

**Por qué los datos se piden en inglés a YouTube Music:** el analizador de
ytmusicapi solo reconoce bien las secciones en inglés; los títulos se
traducen en `catalogo.py`. Las páginas (inicio, artista, géneros) usan un
analizador propio que aguanta mejor los cambios de YouTube.

Para ejecutar desde el código:

```
pip install -r requirements.txt
python ejecutar.py
```

Los datos viven en `%APPDATA%\DescargadorVideos`: `cuentas.json`, la caché de
portadas y, por cuenta, `ajustes.json` e `historial.db` (la primera cuenta en
la carpeta raíz, las demás en `perfiles\<usuario>`).

---

## Si algo falla

| Síntoma | Qué hacer |
|---|---|
| «No se encontró el motor de reproducción» | Falta `bin\mpv\libmpv-2.dll` junto a la app |
| Un video se ve a tirones | En el video: ⚙ → baja la calidad o elige «Evitar AV1» |
| «YouTube pide iniciar sesión» | Ajustes → Tu cuenta de YouTube |
| Un sitio deja de funcionar | Ajustes → Motor y versión → Actualizar yt-dlp |
| No aparece la letra | Esa canción no tiene letra pública sincronizada |

---

Descarga solo contenido del que tengas los derechos o cuyo uso permitan la
licencia y los términos del sitio.
