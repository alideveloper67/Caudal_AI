# Caudal para Android

La versión de teléfono de Caudal (Flutter). Versión **2.0.0**.

## Qué hace

- **Cuenta en la nube**: entras con el mismo usuario y contraseña que en la
  computadora y ves tus me gusta, listas, guardados y ajustes. **Mantener la
  sesión iniciada** te deja dentro la próxima vez; **Ajustes → Cerrar sesión**
  para salir.
- **Pestañas**: Inicio, Buscar, Tu biblioteca y **Descargar**.
- **Descargar cualquier enlace**: pegas el enlace (o usas *Compartir → Caudal*
  desde otra app), sale la vista previa y eliges video o audio y su calidad.
  Todo se descarga **dentro del teléfono**: no hace falta la computadora ni
  ningún servidor. Ya no hay navegador web dentro de la app ni «Conectar con
  la computadora».
- **Súper volumen** (Fuerte, Muy fuerte, Fiesta, Máximo) y **ecualizador**,
  en *Ajustes → Ecualizador, súper volumen y velocidad*: se oye mientras lo
  mueves y solo se queda con **Guardar**; Cancelar lo deja como estaba.
- **Segundo plano**: la música sigue con la pantalla apagada y se controla
  desde la notificación y el auricular. Al pausar, la notificación se puede
  quitar y la app deja de trabajar en segundo plano.
- Lo descargado queda en `Descargas/Caudal` y suena sin internet.

## Actualizaciones

Al abrirse (y en **Ajustes → Buscar actualizaciones**) mira las *Releases* de
GitHub y solo hace caso a las etiquetas `movil-vX.Y.Z`; las `escritorio-v…`
son de Windows. Si hay una versión mayor, baja el APK (el ligero si está, si
no el universal) y abre el instalador de Android. La primera vez Android pide
permiso para instalar desde Caudal.

Para publicar: sube `versionApp` en `lib/nucleo/version.dart` y `version:` en
`pubspec.yaml`, compila y crea la release `movil-vX.Y.Z` con el `.apk`
adjunto.

## Compilar

```
flutter pub get
flutter test
flutter build apk --release --split-per-abi --target-platform android-arm64,android-arm
flutter build apk --release        # universal
```

Los APK salen en `build/app/outputs/flutter-apk/`. iPhone se compila en
Codemagic con `codemagic.yaml` (no hay Mac en esta PC).

## Dónde está cada cosa

```
lib/
├── main.dart          arranque, servicios y aviso de versión nueva
├── nucleo/            cuentas y nube (Supabase), sincronización, catálogo,
│                      descargas (motor_local, captura), ajustes, versión
├── reproduccion/      reproductor y servicio de audio en segundo plano
└── ui/                armazón con las pestañas y las páginas
```
