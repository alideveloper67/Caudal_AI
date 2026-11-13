# Caudal — cómo está montado

Dos apps que comparten cuenta:

| | Escritorio (Windows) | Móvil (Android) |
|---|---|---|
| Carpeta | `escritorio/` | `app/` |
| Hecha con | Python, PySide6, libmpv, yt-dlp, ffmpeg | Flutter, youtube_explode, ffmpeg_kit |
| Se entrega como | `CaudalInstalador.exe` | `Caudal.apk` / `Caudal-universal.apk` |
| Etiqueta de versión | `escritorio-vX.Y.Z` | `movil-vX.Y.Z` |

Las dos van por la **2.0.0**. Cada app descarga **dentro del propio
dispositivo**: no hay servidor intermedio. (La carpeta `servidor/` es de la
versión antigua y ya no la usa ninguna app.)

---

## Cuentas en la nube

Las cuentas viven en **Supabase** (plan gratuito). En `supabase/esquema.sql`
están las tablas: perfil, me gusta, listas, álbumes y artistas guardados,
escuchas recientes y ajustes. Se pega entero en *SQL Editor* y se ejecuta; se
puede repetir sin romper nada.

- Se entra con **usuario y contraseña**; la misma cuenta sirve en Windows y en
  Android.
- **Mantener la sesión iniciada** guarda la sesión en el dispositivo y la
  renueva sola; **Cerrar sesión** la borra.
- Las canciones y videos descargados **no se suben**: se quedan en cada
  dispositivo.
- Las apps solo llevan la **clave pública** del proyecto. La seguridad la
  ponen las reglas por fila (RLS): cada usuario solo lee y escribe lo suyo.
  Ninguna clave secreta va en el código ni en el repositorio.

---

## Actualizaciones automáticas

Las dos apps miran las *Releases* de este repositorio de GitHub al abrirse. El
mismo repositorio publica las dos, así que cada una **solo hace caso a su
etiqueta**:

| Etiqueta | La lee | Adjunto que necesita |
|---|---|---|
| `escritorio-v2.0.1` | la app de Windows | `CaudalInstalador.exe` |
| `movil-v2.0.1` | la app de Android | `Caudal.apk` (y si quieres `Caudal-universal.apk`) |

Si la versión publicada es mayor que la instalada, la app avisa:

- **Windows**: baja el instalador nuevo, se cierra y el instalador la
  sustituye conservando descargas y ajustes.
- **Android**: baja el APK (el ligero primero) y abre el instalador del
  sistema; la primera vez Android pide permiso para instalar desde Caudal.

Se ignoran los borradores y las *pre-release*: sirven para probar una versión
sin que les llegue a todos.

### Publicar una versión nueva

1. Sube el número:
   - escritorio: `VERSION` en `escritorio/descargador/version.py`;
   - móvil: `versionApp` en `app/lib/nucleo/version.dart` **y** `version:` en
     `app/pubspec.yaml` (con el `+N` también subido).
2. Compila (abajo).
3. Crea la release con la etiqueta que toca (`escritorio-v…` o `movil-v…`),
   escribe las novedades en la descripción (es lo que ve el usuario) y adjunta
   el archivo.

---

## Compilar

**Escritorio** (desde `escritorio/`, con ffmpeg y `mpv/libmpv-2.dll` en `bin/`):

```
python -m pytest -q pruebas
python -m PyInstaller --noconfirm --distpath salida "Caudal Escritorio.spec"
python ..\instalador\crear_instalador.py
```

La app queda en `escritorio/salida/Caudal Escritorio/` (modo carpeta) y el
instalador en `instalador/CaudalInstalador.exe`. Debe pesar unos **240 MB**; si
sale de unos 40–50 MB, la app no entró dentro y está roto.

Antes de compilar, Caudal tiene que estar cerrado (si no, PyInstaller no puede
sustituir sus archivos).

**Móvil** (desde `app/`):

```
flutter pub get
flutter test
flutter build apk --release --split-per-abi --target-platform android-arm64,android-arm   # el ligero
flutter build apk --release                   # el universal
```

iPhone no se compila en esta PC (hace falta un Mac): `app/codemagic.yaml`
tiene los flujos para Codemagic.

---

Descarga solo contenido del que tengas los derechos o cuyo uso permitan la
licencia y los términos del sitio.
