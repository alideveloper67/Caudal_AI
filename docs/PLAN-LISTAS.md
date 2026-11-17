# Caudal — listas más cómodas, listas compartidas y colaborativas, y compartir por código

Documento de trabajo. Se suma a `docs/PLAN-SOCIAL.md`: **rigen las mismas reglas** (español con tildes y sin jerga, no
`git commit` ni `git push`, no publicar nada, no tocar `ios/`, no subir versiones, **no compilar** — la PC tiene poca
memoria —, solo `flutter analyze` / `flutter test` / `pytest` de lo que toques, pruebas de escritorio con
`QT_QPA_PLATFORM=offscreen` y `APPDATA` temporal). Nada se aplica a la base real ni se despliega: eso lo decide la persona.

## 1. Qué pidió la persona

1. Guardar canciones en una lista es incómodo, **se traba y demora**.
2. **Compartir listas**: hoy compartir saca un link de YouTube Music; queremos algo propio de Caudal.
3. **Pasar listas por el chat** de Caudal.
4. **Listas colaborativas**: dos o más personas añaden música a la misma lista.
5. Reemplazo del link: **código + enlace propio + QR** (ver §2).
6. Caudal de escritorio más cómodo.

## 2. Decisión sobre «el link»

Caudal ya usa códigos cortos y enlaces propios para «Escuchar juntos» (`caudal://juntos?sala=ABC234`). Se sigue ese camino:

| Capa | Para qué | Forma |
|---|---|---|
| **Código** | Base de todo: se dice por voz, se escribe, se pega en cualquier chat | 8 caracteres legibles, se muestra `K7M2-9QXP` |
| **Enlace de Caudal** | Mandarlo por WhatsApp o redes sin depender de YouTube | `https://caudal-musica.netlify.app/l/K7M2-9QXP` (página con vista previa, botón «Abrir en Caudal» y «Descargar») |
| **Enlace directo a la app** | Abrir la app ya instalada | `caudal://lista?codigo=K7M2-9QXP` |
| **QR** | En persona: se escanea con la cámara del teléfono | El QR contiene el enlace de Caudal |
| **Tarjeta en el chat** | Entre amigos de Caudal, sin nada que copiar | Mensaje con la lista adentro y botón «Unirme» |

- Alfabeto del código: `ABCDEFGHJKMNPQRSTUVWXYZ23456789` (sin I, L, O, 0, 1). Se guarda en mayúsculas y sin guion.
  Al leer: mayúsculas, se quitan espacios y guiones.
- Una lista tiene **un código activo** a la vez. El dueño elige el permiso del código: `colaborador` (puede añadir) u
  `oyente` (solo escucha). El dueño puede **dejar de compartir**: el código deja de servir y se quita a los miembros.
- Un enlace de YouTube Music sigue existiendo para compartir **una canción** suelta; las listas ya no lo usan.

## 3. Base de datos (Supabase) — archivo nuevo `supabase/listas.sql`

No se edita `esquema.sql` ni `social.sql`. El archivo nuevo se puede ejecutar encima de ellos y **es repetible**
(`if not exists`, `create or replace`, `drop policy if exists`). Todas las funciones son `security definer` con
`set search_path = public`, como las existentes (`son_amigos`, `hay_bloqueo`, `abrir_chat` están en `social.sql`).

### Tablas nuevas
- `lista_miembros(lista_id uuid → listas on delete cascade, user_id uuid → auth.users on delete cascade,
  rol text check in ('colaborador','oyente'), desde timestamptz default now(), primary key (lista_id, user_id))`.
- `lista_codigos(codigo text primary key, lista_id uuid unique → listas on delete cascade,
  rol text check in ('colaborador','oyente') default 'colaborador', creado timestamptz default now())`.
  Una fila por lista = un código activo. Dejar de compartir = borrar la fila.
- `mensajes.lista jsonb` (nullable). Forma: `{"codigo","nombre","canciones":n,"rol","portada"?:url}`. La restricción de
  `mensajes` pasa a: texto no vacío **o** pista **o** lista; y `lista` debe ser objeto con `codigo`.
- Máximo **20 miembros** por lista y **2 000 canciones** por lista compartida.

### Reglas de acceso (RLS)
- `listas` y las demás tablas conservan «solo lo mío».
- **`lista_items`**: hoy solo ve lo suyo (`user_id = auth.uid()`). Debe pasar a: el dueño de la lista ve **todas** las
  canciones de su lista (también las que añadieron colaboradores) y puede cambiarlas o borrarlas; el resto entra solo por
  las funciones de abajo. `user_id` de cada fila = quién la añadió.
- `lista_miembros` y `lista_codigos`: solo se ven y cambian por las funciones; sin acceso directo.

### Funciones (todas devuelven errores con frases en español que la app puede mostrar)
| Función | Quién | Qué hace |
|---|---|---|
| `compartir_lista(p_lista uuid, p_rol text default 'colaborador') → text` | dueño | Crea o devuelve el código activo (y le cambia el permiso si es otro). Devuelve el código sin guion. |
| `dejar_de_compartir_lista(p_lista uuid) → void` | dueño | Borra el código y a los miembros. |
| `ver_lista_codigo(p_codigo text) → jsonb` | **anon y logueados** | Vista previa sin ids internos: `{nombre, descripcion, total, rol, miembros, dueno:{usuario,nombre,foto_url}, canciones:[{titulo,artista,miniatura}] (máx. 6)}`; `null` si el código no existe. Para la página web y para confirmar antes de unirse. |
| `unirse_a_lista(p_codigo text) → jsonb` | logueado | Une a la persona: `{lista_id, nombre, rol, es_dueno}`. Idempotente. Falla si hay bloqueo con el dueño («no se puede unir») o si la lista ya tiene 20 miembros. Si es el dueño, devuelve `es_dueno: true` sin crear nada. |
| `salir_de_lista(p_lista uuid) → void` | miembro | Se sale. |
| `quitar_miembro(p_lista uuid, p_usuario uuid) → void` | dueño | Expulsa. |
| `miembros_lista(p_lista uuid) → jsonb` | dueño y miembros | `[{id, usuario, nombre, foto_url, rol, desde, es_dueno}]`. |
| `mis_listas_compartidas() → jsonb` | logueado | Listas **de otras personas** donde soy miembro: `[{id, nombre, descripcion, rol, total, actualizada, dueno:{id,usuario,nombre,foto_url}}]`. |
| `pistas_de_lista(p_lista uuid) → jsonb` | dueño y miembros | `[{clave, datos, orden, agregada, agregada_por:{id,usuario,nombre}}]` ordenadas. |
| `agregar_a_lista_compartida(p_lista uuid, p_items jsonb) → int` | dueño y colaboradores | `p_items = [{clave, datos}]`. `user_id = auth.uid()`, `orden` = último + 1, ignora repetidas, sube `listas.actualizada`. Devuelve cuántas entraron. |
| `quitar_de_lista_compartida(p_lista uuid, p_clave text) → void` | dueño (cualquiera) / colaborador (solo las que añadió) | Quita la canción. |
| `mis_chats()` | — | Se **amplía** con `ultimo_lista` (jsonb) como ya trae `ultimo_pista`. |

Bloqueos y amistad: unirse con código **no** exige ser amigos, pero respeta los bloqueos (`hay_bloqueo`).

## 4. Aplicación Android (`app/lib`)

### 4.1 Rapidez (causa encontrada)
Cada cambio local (añadir una canción) dispara `Sincronizacion.pronto()` → `ya()` → `_ciclo()` = `_enviarPendientes()` **y
después `_traer()`**, que baja todos los me gusta, todas las listas con **una petición por lista**, guardados y escuchas, y
reescribe la base local entera dentro de una transacción (dos escrituras por canción), y luego `refrescarMemoria()`
repinta la app. Eso pasa tras **cada** cambio y cada 3 minutos. Es lo que se siente como «se traba y demora».
Arreglo: tras un cambio local solo se **envían** los pendientes; la descarga completa solo en el arranque, cada 3 minutos,
al volver a primer plano o al tirar para refrescar; y se descarga solo si algo cambió. La interfaz de la lista no debe
esperar a la red (guardado local primero, nube después).

### 4.2 Añadir a una lista, cómodo
La hoja «Añadir a una lista» (`ui/servicios.dart`, `anadirALista`) debe abrir al instante (sin esperar consultas lentas),
mostrar arriba **la última lista usada**, tener **búsqueda** cuando hay muchas listas, permitir **elegir varias listas** a la
vez con un botón «Listo», crear una lista nueva sin salir, y avisar con «Deshacer». Las listas compartidas donde se puede
añadir aparecen en la misma hoja, marcadas.

### 4.3 Compartir, unirse, chat
- Hoja «Compartir lista»: interruptor «Pueden añadir canciones» (colaborador) / «Solo escuchar»; código grande con
  guion; botones **Copiar código**, **Compartir enlace** (el enlace de Caudal), **Mostrar QR**, **Enviar por el chat**,
  **Dejar de compartir**.
- **«Tengo un código»** en Biblioteca: se escribe o pega el código (o se abre un enlace `caudal://lista?codigo=…`), se
  muestra la vista previa (`ver_lista_codigo`) y se confirma con «Unirme».
- Biblioteca: sección **Listas compartidas** (las de otras personas) con la insignia «Compartida · <nombre>». Dentro de una
  lista compartida: quién añadió cada canción, miembros, «Salir de la lista».
- Chat: tarjeta de lista (nombre, canciones, «Colaborativa») con botón «Unirme» / «Abrir». Se envía desde «Compartir lista
  › Enviar por el chat» (elegir amigo) y desde el menú de la lista.
- Tiempo casi real sin servidor nuevo: al abrir una lista compartida se trae al instante y se vuelve a traer cada ~20 s
  mientras esté abierta.
- QR: paquete `qr_flutter` (solo para dibujar). Leer el QR lo hace la cámara del teléfono, que abre el enlace.

## 5. Página web (`netlify/` y `web/`)
`/l/<código>` muestra: nombre de la lista, de quién es, cuántas canciones, las primeras canciones, si es colaborativa, un
botón **«Abrir en Caudal»** (`caudal://lista?codigo=…`), **«Descargar Caudal»** y el código para copiar. Con etiquetas para
que WhatsApp muestre vista previa. Lee los datos con `ver_lista_codigo` (se llama con la clave pública anónima del
proyecto, que ya está en la app).

## 6. Caudal de escritorio (`escritorio/`, Python + PySide6)
**Encargo de la persona (16/11):** «más fluidez, comodidad visual». Es lo primero que se mide y se arregla:
- **Fluidez**: que nada se trabe al navegar, buscar, guardar en una lista o cambiar de pantalla. Buscar trabajo pesado o de
  red hecho en el hilo de la interfaz (lecturas de disco, sincronización, carga de carátulas, listas largas pintadas de una
  vez) y sacarlo a segundo plano; carga perezosa y reutilización de carátulas; no repintar toda la ventana por un cambio
  pequeño. Medir antes y después (tiempos reales o conteo de operaciones) y reportar los números.
- **Comodidad visual**: espaciado y tamaños legibles, contraste cómodo para ojos cansados, jerarquía clara, estados de carga
  amables (nada de pantallas en blanco), animaciones suaves y cortas, tamaños de letra que se adapten a la ventana, que se
  vea bien en pantalla pequeña y en grande. Respetar la paleta y el estilo que ya tiene Caudal.
- Capturas offscreen antes y después (`widget.grab().save(...)`) guardadas en `docs\capturas-escritorio\`.

Mismos dolores y mismas soluciones: rapidez al guardar en una lista (misma causa de sincronización), unirse con código,
compartir (código/enlace), chat con tarjeta de lista. Además, mejoras de comodidad que se encuentren al usarla
(atajos de teclado, menú contextual, recordar ventana y posición…). Informar cada dolor encontrado y qué se hizo.

## 7. Reparto y archivos
- **SQL**: `supabase/listas.sql`, `supabase/pruebas/` (pruebas). Nadie más toca estos.
- **Web**: `netlify/functions/lista.mjs` (y su prueba), `web/` solo si hace falta una página nueva.
- **Android rapidez + hoja de añadir**: `app/lib/nucleo/sincronizacion.dart`, `app/lib/nucleo/coleccion.dart`,
  `app/lib/ui/servicios.dart` y sus pruebas en `app/test/`.
- **Android compartir/chat**: archivos **nuevos** (`app/lib/nucleo/listas_compartidas.dart`, páginas y hojas nuevas),
  `app/lib/nucleo/chat.dart` y la pantalla del chat, y enganches mínimos en Biblioteca y el manejo de `caudal://`.
- **Escritorio**: todo bajo `escritorio/`.
