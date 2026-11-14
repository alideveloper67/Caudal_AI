# Escuchar juntos: protocolo (móvil y Windows en la misma sala)

Referencia: `app/lib/nucleo/juntos.dart` (Flutter). Sin tablas: solo Supabase
Realtime **Broadcast + Presence**. Comprobado contra el proyecto real (Realtime
está habilitado y acepta la clave publicable).

## 1. Conexión (protocolo Phoenix, vsn 1.0.0)

```
wss://nztirmwqykbxadidpzzt.supabase.co/realtime/v1/websocket?apikey=<clave PUBLICABLE de nube.dart / nube.py>&vsn=1.0.0
```

Cada mensaje es un JSON de texto: `{"topic", "event", "payload", "ref", "join_ref"}`.
`ref` es un contador en texto (`"1"`, `"2"`…) que sube con cada mensaje; `join_ref`
es el `ref` del `phx_join` vigente.

- **Topic**: `realtime:juntos-<CODIGO>` (CODIGO en mayúsculas, 6 caracteres).
- **Join**:
  ```json
  {"topic":"realtime:juntos-ABC234","event":"phx_join","ref":"1","join_ref":"1",
   "payload":{"config":{"broadcast":{"self":false,"ack":false},
                        "presence":{"key":"<miId>","enabled":true},
                        "postgres_changes":[],"private":false}}}
  ```
  Respuesta `phx_reply` con el mismo `ref` y `payload.status == "ok"`. No se manda `access_token`
  (canal público): da igual con qué cuenta haya entrado cada uno.
- **Latido**: cada 25 s `{"topic":"phoenix","event":"heartbeat","payload":{},"ref":"<n>"}`.
  Si el anterior no tuvo `phx_reply`, se cierra el socket y se reconecta.
- **Reconexión**: esperas 1, 2, 4, 8, 15 s…; al volver se repite join y track.
  Tras reconectar, el anfitrión manda `estado` y el invitado manda `hola`.
- **Salir**: `phx_leave` en el topic y cerrar el socket (la presencia desaparece al momento).
- `phx_error` / `phx_close` en el topic ⇒ reconectar.

## 2. Código y enlace

- Alfabeto: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (sin 0/O ni 1/I). 6 caracteres al azar.
- Enlace: `caudal://juntos?sala=ABC234`. Al leer: si hay `?sala=` se toma eso; se pasa a mayúsculas,
  se quitan espacios y guiones y debe cumplir `^[alfabeto]{6}$`.

## 3. Presence

- `key` = **miId**: 12 caracteres al azar del mismo alfabeto, nuevo en cada entrada a una sala
  (cada aparato es un miembro, aunque compartan cuenta).
- Track (tras el `phx_reply` ok del join):
  ```json
  {"topic":"…","event":"presence","ref":"2","join_ref":"1",
   "payload":{"type":"presence","event":"track",
              "payload":{"nombre":"Ana","usuario":"ana","entro":1763000000000}}}
  ```
  `nombre`: texto visible; `usuario`: usuario de Caudal (puede ir vacío); `entro`: int, ms Unix del
  reloj local al entrar en la sala (no cambia al reconectar).
- Llegan `presence_state` (`{clave:{metas:[{…, phx_ref}]}}`, reemplaza la lista) y
  `presence_diff` (`{joins:{…}, leaves:{…}}`). De cada clave se usa la última meta.
- Lista de miembros ordenada por (`entro` asc, `miId` asc).

## 4. Broadcast

Envío: `{"topic":"…","event":"broadcast","ref":"n","join_ref":"1",
"payload":{"type":"broadcast","event":"<EVENTO>","payload":{…}}}`.
Se recibe igual (`payload.event`, `payload.payload`). `self:false`: uno no recibe lo suyo.
Todos los tiempos son **int en ms Unix**; posiciones **int en ms**.

| evento | lo manda | payload |
|---|---|---|
| `estado` | anfitrión | `{"de":str miId, "rango":int (entro del anfitrión), "seq":int creciente, "pista":obj\|null, "pos":int ms, "sonando":bool, "t":int ms reloj del anfitrión al mandar}` |
| `hola` | quien entra (o reconecta) | `{"de":str}` → el anfitrión responde con `estado` en ~150 ms |
| `ping` | invitado | `{"de":str, "a":str miId del anfitrión, "t0":int reloj del invitado}` |
| `pong` | solo el anfitrión, si `a == su miId` | `{"para":str (el de del ping), "t0":int (copiado), "th":int reloj del anfitrión}` |
| `ceder` | anfitrión | `{"a":str miId del nuevo anfitrión, "de":str}` |
| `reaccion` | cualquiera | `{"emoji":str (un emoji), "nombre":str, "de":str}` |

**pista**: objeto plano solo con valores texto/número/booleano, sin `archivo`. Lo que
importa a la otra app:
`{"video_id":str (YouTube, OBLIGATORIO para poder seguirlo), "titulo":str, "artista":str, "duracion":int s, "miniatura":str url}`.
Pueden venir más campos (ignorar los desconocidos). Identidad de la pista = `video_id`.
Si `video_id` está vacío el invitado no puede seguirla (es un archivo local del anfitrión): lo avisa.
`pista:null` = no suena nada → el invitado pausa.

El anfitrión manda `estado`: al instante si cambia la pista o `sonando`, si su posición real se
aparta más de 1,5 s de la que anunció (= hizo un salto), al recibir `hola`, y si no, cada 2,5 s.

## 5. Reloj y corrección

- Invitado: `ping` al entrar y cada 4 s. Al llegar su `pong` (t1 = reloj local):
  `ida = t1 - t0` (descartar si <0 o >10000); `diferencia = th - (t0 + t1) / 2` (división entera).
  Se guardan las 10 últimas medidas y se usa la `diferencia` de la de **menor ida**.
  Al cambiar de anfitrión se borran las medidas.
- Sin medidas todavía: `diferencia = estado.t - momento_local_de_recepción`.
- Posición esperada ahora: `sonando ? pos + max(0, ahora_local + diferencia - t) : pos`.
- Cada 0,5 s y en cada `estado`, el invitado:
  1. si `video_id` ≠ el suyo → carga la pista empezando en la posición esperada (pausada si `sonando` es false);
  2. ajusta pausa/reproducción a `sonando`;
  3. si |posición local − esperada| > **1500 ms** y pasaron > 2 s del último salto → salta a
     `esperada + 150 ms` (o `esperada` si está en pausa). No corrige mientras carga.
- Los invitados no mandan su estado: si tocan pausa, el siguiente `estado` los vuelve a alinear.

## 6. Anfitrión

- Quien **crea** la sala es anfitrión desde el principio.
- Quien **se une** toma como anfitrión el `de` del primer `estado` que recibe. Si en 5 s no llega
  ninguno (sala vacía), aplica la regla de elección.
- **Regla de elección** (cuando el `anfitrionId` desaparece de presence, o nadie responde): entre los
  presentes más uno mismo, el primero ordenando por (`entro` asc, `miId` asc). Todos ven la misma
  presencia, así que todos eligen al mismo; el elegido empieza a mandar `estado`.
- `ceder`: todos pasan a `anfitrionId = a`; si soy `a`, empiezo a mandar `estado`.
- Dos anfitriones a la vez (tras un corte): al recibir un `estado` ajeno siendo anfitrión, gana el de
  menor (`rango`, `de`). El que pierde pasa a invitado; el que gana reenvía su `estado`.
