# Caudal en el iPhone

Caudal no está en la App Store. Para tenerlo en el iPhone se instala "a mano"
desde un ordenador con Windows, usando tu Apple ID normal (la misma de iCloud,
**gratis**; no hace falta pagar a Apple ni tener un Mac).

## Lo que necesitas

- Un ordenador con Windows y el cable del iPhone.
- Tu Apple ID y su contraseña. Mejor una Apple ID secundaria si te preocupa;
  funciona igual.
- **iTunes** e **iCloud** descargados desde la web de Apple
  (apple.com/itunes y support.apple.com, versión "para Windows").
  Las versiones de la Microsoft Store a veces no funcionan con estos programas.
- El archivo de Caudal para iPhone: entra en
  **github.com/alideveloper67/Caudal_AI/releases**, abre la versión más reciente
  que empiece por **movil-v** y descarga el archivo **Caudal-X.Y.Z.ipa**
  (los `.apk` son para Android, no los necesitas).

## Opción A: Sideloadly (la más sencilla)

1. Descarga Sideloadly desde **sideloadly.io** e instálalo.
2. Conecta el iPhone al ordenador con el cable. Si el iPhone pregunta
   "¿Confiar en este ordenador?", pulsa **Confiar** y pon tu código.
3. Abre Sideloadly. Arriba debe aparecer el nombre de tu iPhone.
4. Arrastra el archivo **Caudal-X.Y.Z.ipa** a la ventana de Sideloadly.
5. Escribe tu Apple ID en la casilla "Apple account" y pulsa **Start**.
   Te pedirá la contraseña (y quizá un código que llega a tus dispositivos Apple).
6. Espera a que diga **Done**. Caudal ya aparece en el iPhone.

## Opción B: AltStore (se renueva sola)

1. Descarga **AltServer para Windows** desde **altstore.io** e instálalo.
   Queda un rombo pequeño junto al reloj de Windows.
2. Conecta el iPhone por cable y pulsa **Confiar** si lo pregunta.
3. Haz clic en el rombo > **Install AltStore** > elige tu iPhone, y escribe tu
   Apple ID y contraseña. En el iPhone aparecerá la app AltStore.
4. Pasa el archivo **Caudal-X.Y.Z.ipa** al iPhone (por ejemplo, descárgalo
   desde Safari en el propio iPhone; queda en la app Archivos).
5. Abre AltStore en el iPhone > pestaña **My Apps** > botón **+** arriba a la
   izquierda > elige el `.ipa`. Pide tu Apple ID la primera vez.

## La primera vez que abres Caudal

El iPhone no deja abrirla hasta que le dices que te fías:

1. **Ajustes > General > VPN y gestión de dispositivos**: toca tu Apple ID y
   pulsa **Confiar**.
2. En iPhone con iOS 16 o más nuevo, además:
   **Ajustes > Privacidad y seguridad > Modo de desarrollador** > activarlo.
   El iPhone se reinicia y al volver pregunta si lo activas: di que sí.

Esto se hace una sola vez.

## Cada 7 días hay que renovarla

Con una Apple ID gratis, Apple solo da permiso **por 7 días**. Pasado ese
tiempo Caudal deja de abrirse (tus datos no se pierden: siguen ahí). Para
renovarla:

- **Con Sideloadly**: conecta el iPhone, arrastra otra vez el mismo `.ipa` y
  pulsa **Start**, igual que la primera vez. Sideloadly también tiene la casilla
  "automatic refresh" para que lo haga solo mientras el ordenador esté encendido.
- **Con AltStore**: si el ordenador está encendido con AltServer abierto y el
  iPhone en **la misma red Wi-Fi**, AltStore la renueva sola en segundo plano.
  Si no, abre AltStore > **My Apps** > **Refresh All**.

Un consejo: pon un recordatorio en el móvil cada 6 días.

Otros límites de la Apple ID gratis: como máximo 3 apps instaladas así a la vez
(AltStore cuenta como una) y unas pocas apps nuevas por semana. Para Caudal
sola sobra.

## Cómo llegan las actualizaciones

- Cada vez que sale una versión nueva de Caudal para móvil, en la misma página
  de versiones (**github.com/alideveloper67/Caudal_AI/releases**, las que
  empiezan por **movil-v**) aparece, unos minutos después, su archivo
  **Caudal-X.Y.Z.ipa** junto a los de Android.
- Caudal mira si hay versión nueva y te avisa. En el iPhone Apple no deja que
  una app se actualice sola, así que la instalación la haces tú:
- Descarga el `.ipa` nuevo e instálalo **encima** del que tienes, igual que la
  primera vez (Sideloadly: arrastrar y Start; AltStore: My Apps > +).
  Usa la **misma Apple ID** de siempre y no borres la app antes: así conservas
  tus cosas.
- Instalar una versión nueva también cuenta como renovación: vuelves a tener
  7 días desde ese momento.

## Si algo falla

- **"No se encuentra el iPhone"**: revisa que iTunes esté instalado desde la
  web de Apple, cambia de cable o de puerto USB y desbloquea el iPhone.
- **"No se puede verificar la app" / no abre**: repite el paso de
  *Confiar* en Ajustes > General > VPN y gestión de dispositivos.
- **Pasó una semana y no abre**: toca renovar (apartado de los 7 días).
- **Error de contraseña con verificación en dos pasos**: escribe tu contraseña
  normal; cuando llegue el código de 6 cifras a otro dispositivo, ponlo en la
  ventana que aparece.
