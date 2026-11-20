// Pruebas de supabase/fiesta.sql sobre PGlite (Postgres en WebAssembly, sin servidor ni Docker).
//
//   node supabase/pruebas/fiesta.prueba.mjs
//
// Usa el PGlite que ya está instalado en agenty-ai (otra ruta: PGLITE_RUTA=...).
// Carga esquema.sql + fiesta.sql (dos veces: debe poder repetirse) y prueba la cola, los votos,
// el límite por invitado, quitar, cerrar, «lo que suena» y que nadie lea las tablas directamente.
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import { createRequire } from 'node:module';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const sql = (n) => readFileSync(path.join(aqui, '..', n), 'utf8');

const ruta = process.env.PGLITE_RUTA || 'C:\\Users\\USER\\agenty-ai\\node_modules\\@electric-sql\\pglite';
const require = createRequire(import.meta.url);
const { PGlite } = await import(pathToFileURL(require.resolve(ruta)).href);
const { SUPABASE_FALSO } = await import('./arnes.sql.mjs');

process.on('unhandledRejection', (e) => { console.log('ERROR: ' + (e && e.message || e)); process.exit(2); });
const db = new PGlite();
await db.exec(SUPABASE_FALSO);
// Realtime falso: apunta cada aviso para comprobar que las funciones lo mandan
await db.exec(`
create schema realtime;
create table realtime.enviados (n serial, payload jsonb, evento text, tema text, privado boolean);
create function realtime.send(payload jsonb, event text, topic text, private boolean default true)
returns void language sql as $$ insert into realtime.enviados (payload, evento, tema, privado) values ($1, $2, $3, $4) $$;
`);
await db.exec(sql('esquema.sql'));
await db.exec(sql('fiesta.sql'));
await db.exec(sql('fiesta.sql')); // repetible

let ok = 0, mal = 0;
function comprobar(nombre, cond, detalle = '') {
  if (cond) ok++; else { mal++; console.log('  FALLA: ' + nombre + (detalle ? '  -> ' + detalle : '')); }
}
async function anonimo() {
  await db.exec('reset role');
  await db.query(`select set_config('request.jwt.claim.sub', '', false)`);
  await db.exec('set role anon');
}
async function admin() { await db.exec('reset role'); }
async function rpc(nombre, args) {
  const claves = Object.keys(args);
  const r = await db.query(`select public.${nombre}(${claves.map((k, i) => `${k} => $${i + 1}`).join(', ')}) as r`,
    claves.map((k) => (args[k] !== null && typeof args[k] === 'object' ? JSON.stringify(args[k]) : args[k])));
  return r.rows[0].r;
}
async function falla(nombre, fn, patron) {
  try { await fn(); comprobar(nombre, false, 'no falló'); }
  catch (e) { const m = String(e.message || e); comprobar(nombre, patron ? patron.test(m) : true, 'mensaje: ' + m); }
  await anonimo();
}
const pista = (vid, titulo = 'Canción ' + vid) => ({ video_id: vid, titulo, artista: 'Artista', miniatura: 'https://i.ytimg.com/vi/' + vid + '/hqdefault.jpg', duracion: 200 });
const V = (n) => ('vid' + String(n).padStart(8, '0')).slice(0, 11);   // video_id válido de 11

const ANA = 'tokenAna-0123456789';
const BETO = 'tokenBeto-0123456789';
const CARLA = 'tokenCarla-012345678';

await anonimo();

// ---------------------------------------------------------------- crear
const creada = await rpc('fiesta_crear', { p_nombre: '  Cumple de Lu  ', p_limite: 2 });
const COD = creada.codigo, CLAVE = creada.clave;
comprobar('código de 6 del alfabeto', /^[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{6}$/.test(COD), COD);
comprobar('clave larga', typeof CLAVE === 'string' && CLAVE.length >= 32);
let v = await rpc('fiesta_ver', { p_codigo: COD.toLowerCase().slice(0, 3) + '-' + COD.slice(3).toLowerCase() });
comprobar('ver con minúsculas y guion', v && v.codigo === COD);
comprobar('nombre limpio', v.nombre === 'Cumple de Lu', v.nombre);
comprobar('abierta, límite 2, cola vacía', v.abierta === true && v.limite === 2 && v.cola.length === 0);
comprobar('ver código inexistente = null', (await rpc('fiesta_ver', { p_codigo: 'ZZZZZZ' })) === null);
comprobar('sin nombre se llama Fiesta', (await rpc('fiesta_ver', { p_codigo: (await rpc('fiesta_crear', { p_nombre: '   ' })).codigo })).nombre === 'Fiesta');
await falla('límite fuera de rango', () => rpc('fiesta_crear', { p_nombre: 'x', p_limite: 99 }), /límite/);

// nada se lee directo
await falla('anon no lee fiestas', () => db.query('select * from public.fiestas'), /permission denied/);
await falla('anon no lee canciones', () => db.query('select * from public.fiesta_canciones'), /permission denied/);
await falla('anon no inserta votos', () => db.query(`insert into public.fiesta_votos values (1, 'x')`), /permission denied/);
await falla('anon no llama ayudas internas', () => db.query(`select public.fiesta_tocar('ABCDEF')`), /permission denied/);
comprobar('ver no enseña la clave', !JSON.stringify(v).includes(CLAVE) && !JSON.stringify(v).includes('clave'));

// ---------------------------------------------------------------- entrar y añadir
v = await rpc('fiesta_entrar', { p_codigo: COD, p_invitado: ANA, p_nombre: 'Ana' });
comprobar('entrar: 1 invitado', v.invitados === 1, JSON.stringify(v.invitados));
await falla('token corto no vale', () => rpc('fiesta_entrar', { p_codigo: COD, p_invitado: 'corto', p_nombre: 'X' }), /reconocer tu teléfono/);
await falla('entrar a fiesta inexistente', () => rpc('fiesta_entrar', { p_codigo: 'ZZZZZZ', p_invitado: ANA }), /no existe/);

v = await rpc('fiesta_anadir', { p_codigo: COD, p_invitado: ANA, p_pista: pista(V(1), 'Primera') });
comprobar('añadida 1', v.cola.length === 1 && v.cola[0].titulo === 'Primera' && v.cola[0].nombre === 'Ana');
comprobar('es mía para Ana', v.cola[0].mia === true && v.mias === 1);
await falla('repetida en cola', () => rpc('fiesta_anadir', { p_codigo: COD, p_invitado: BETO, p_pista: pista(V(1)) }), /ya está en la cola/);
await falla('video_id raro', () => rpc('fiesta_anadir', { p_codigo: COD, p_invitado: ANA, p_pista: { video_id: 'x<script>', titulo: 'a' } }), /no se puede añadir/);
v = await rpc('fiesta_anadir', { p_codigo: COD, p_invitado: ANA, p_pista: { ...pista(V(2), 'Segunda'), miniatura: 'javascript:alert(1)' } });
comprobar('miniatura no https se descarta', v.cola.find((c) => c.video_id === V(2)).miniatura === '');
// límite 2 por invitado
await falla('límite por invitado', () => rpc('fiesta_anadir', { p_codigo: COD, p_invitado: ANA, p_pista: pista(V(3)) }), /Ya añadiste 2 canciones/);
// Beto añade sin haber entrado: queda como invitado
v = await rpc('fiesta_anadir', { p_codigo: COD, p_invitado: BETO, p_pista: pista(V(3), 'Tercera'), p_nombre: 'Beto' });
comprobar('beto añade sin entrar', v.invitados === 2 && v.cola.length === 3);
comprobar('para Beto la de Ana no es suya', v.cola.find((c) => c.video_id === V(1)).mia === false);

// ---------------------------------------------------------------- votos y orden
let cola = (await rpc('fiesta_ver', { p_codigo: COD })).cola;
comprobar('orden de llegada sin votos', cola.map((c) => c.video_id).join() === [V(1), V(2), V(3)].join());
const id3 = cola[2].id, id2 = cola[1].id, id1 = cola[0].id;
v = await rpc('fiesta_votar', { p_codigo: COD, p_invitado: ANA, p_cancion: id3 });
v = await rpc('fiesta_votar', { p_codigo: COD, p_invitado: BETO, p_cancion: id3 });
v = await rpc('fiesta_votar', { p_codigo: COD, p_invitado: BETO, p_cancion: id3 }); // dos veces = un voto
comprobar('dos votos (no se duplica)', v.cola[0].id === id3 && v.cola[0].votos === 2, JSON.stringify(v.cola[0]));
comprobar('Beto ve que votó', v.cola[0].vote === true && v.cola[1].vote === false);
v = await rpc('fiesta_votar', { p_codigo: COD, p_invitado: CARLA, p_cancion: id2 });
comprobar('más votada primero, empate por llegada', v.cola.map((c) => c.id).join() === [id3, id2, id1].join());
v = await rpc('fiesta_votar', { p_codigo: COD, p_invitado: BETO, p_cancion: id3, p_voto: false });
comprobar('quitar voto', v.cola.find((c) => c.id === id3).votos === 1 && v.cola[0].id === id2, v.cola.map((c) => c.id + ':' + c.votos).join());
v = await rpc('fiesta_votar', { p_codigo: COD, p_invitado: ANA, p_cancion: id3, p_voto: false });
comprobar('sin votos vuelve a su sitio (id2 tiene 1)', v.cola.map((c) => c.id).join() === [id2, id1, id3].join(), v.cola.map((c) => c.id + ':' + c.votos).join());
await falla('votar canción que no existe', () => rpc('fiesta_votar', { p_codigo: COD, p_invitado: ANA, p_cancion: 999999 }), /ya no está en la cola/);

// ---------------------------------------------------------------- anfitrión: quitar, límite
await falla('quitar sin clave', () => rpc('fiesta_quitar', { p_codigo: COD, p_clave: 'mala', p_cancion: id1 }), /Solo el anfitrión/);
v = await rpc('fiesta_quitar', { p_codigo: COD, p_clave: CLAVE, p_cancion: id1 });
comprobar('quitada sale de la cola', !v.cola.some((c) => c.id === id1) && v.cola.length === 2);
await falla('quitar dos veces', () => rpc('fiesta_quitar', { p_codigo: COD, p_clave: CLAVE, p_cancion: id1 }), /ya no está en la cola/);
// la quitada no cuenta para el límite: Ana puede añadir otra
v = await rpc('fiesta_anadir', { p_codigo: COD, p_invitado: ANA, p_pista: pista(V(4), 'Cuarta') });
comprobar('quitada no cuenta para el límite', v.mias === 2 && v.cola.length === 3);
// la que se quitó se puede volver a pedir
v = await rpc('fiesta_anadir', { p_codigo: COD, p_invitado: CARLA, p_pista: pista(V(1), 'Primera otra vez') });
comprobar('quitada se puede volver a pedir', v.cola.some((c) => c.video_id === V(1)));
await falla('límite sin clave', () => rpc('fiesta_limite', { p_codigo: COD, p_clave: 'x', p_limite: 0 }), /Solo el anfitrión/);
v = await rpc('fiesta_limite', { p_codigo: COD, p_clave: CLAVE, p_limite: 0 });
comprobar('límite 0', v.limite === 0);
for (let i = 10; i < 14; i++) await rpc('fiesta_anadir', { p_codigo: COD, p_invitado: ANA, p_pista: pista(V(i)) });
comprobar('sin límite Ana añade más', (await rpc('fiesta_ver', { p_codigo: COD, p_invitado: ANA })).mias === 6);
v = await rpc('fiesta_limite', { p_codigo: COD, p_clave: CLAVE, p_limite: 1 });
await falla('bajar el límite frena a quien ya pasó', () => rpc('fiesta_anadir', { p_codigo: COD, p_invitado: ANA, p_pista: pista(V(20)) }), /Ya añadiste 1 canción,/);
comprobar('bajar el límite no borra lo añadido', v.cola.filter((c) => c.nombre === 'Ana').length === 6);
v = await rpc('fiesta_renombrar', { p_codigo: COD, p_clave: CLAVE, p_nombre: 'Cumple de Lu 🎉' });
comprobar('renombrar', v.nombre === 'Cumple de Lu 🎉');

// ---------------------------------------------------------------- tomar la siguiente y lo que suena
v = await rpc('fiesta_ver', { p_codigo: COD });
const primera = v.cola[0];
let t = await rpc('fiesta_tomar', { p_codigo: COD, p_clave: CLAVE });
comprobar('tomar da la primera de la cola', t && t.id === primera.id && t.estado === 'sonando');
v = await rpc('fiesta_ver', { p_codigo: COD });
comprobar('la tomada sale de la cola', !v.cola.some((c) => c.id === primera.id) && v.sonadas[0].id === primera.id);
await falla('votar la que suena', () => rpc('fiesta_votar', { p_codigo: COD, p_invitado: BETO, p_cancion: primera.id }), /ya no está en la cola/);
await falla('añadir la que suena', () => rpc('fiesta_anadir', { p_codigo: COD, p_invitado: CARLA, p_pista: pista(primera.video_id) }), /sonando ahora/);
v = await rpc('fiesta_sonando', { p_codigo: COD, p_clave: CLAVE, p_pista: { ...pista(primera.video_id, primera.titulo), fiesta_id: primera.id, pos_ms: 1500, pausa: false } });
comprobar('sonando guarda la pista', v.sonando && v.sonando.video_id === primera.video_id && v.sonando.fiesta_id === primera.id && v.sonando.pos_ms === 1500 && v.sonando.pausa === false && v.sonando.t > 0, JSON.stringify(v.sonando));
// el anfitrión pone a mano una que estaba en la cola: sale de la cola
const otra = v.cola[1];
v = await rpc('fiesta_sonando', { p_codigo: COD, p_clave: CLAVE, p_pista: { ...pista(otra.video_id), duracion: 'mucho', pausa: 'no' } });
comprobar('a mano: sale de la cola y suena', !v.cola.some((c) => c.id === otra.id) && v.sonando.fiesta_id === otra.id && v.sonando.duracion === 0 && v.sonando.pausa === false);
comprobar('la anterior pasa a sonada', v.sonadas.find((c) => c.id === primera.id)?.estado === 'sonada' && v.sonadas[0].id === otra.id, JSON.stringify(v.sonadas.map((c) => [c.id, c.estado])) + ' primera=' + primera.id + ' otra=' + otra.id);
// una que no es de la fiesta
v = await rpc('fiesta_sonando', { p_codigo: COD, p_clave: CLAVE, p_pista: pista('AAAAAAAAAAA', 'De mi biblioteca') });
comprobar('pista ajena: sin fiesta_id', v.sonando.titulo === 'De mi biblioteca' && v.sonando.fiesta_id === undefined);
comprobar('nada sonando de la fiesta', v.sonadas.every((c) => c.estado === 'sonada'));
v = await rpc('fiesta_sonando', { p_codigo: COD, p_clave: CLAVE, p_pista: null });
comprobar('pista null = nada', v.sonando === null);
await falla('sonando sin clave', () => rpc('fiesta_sonando', { p_codigo: COD, p_clave: 'x', p_pista: null }), /Solo el anfitrión/);
// tomar con la cola vacía
const vacia = await rpc('fiesta_crear', { p_nombre: 'Vacía' });
comprobar('tomar con cola vacía = null', (await rpc('fiesta_tomar', { p_codigo: vacia.codigo, p_clave: vacia.clave })) === null);

// ---------------------------------------------------------------- realtime
await admin();
const avisos = (await db.query(`select * from realtime.enviados where tema = $1 order by n`, ['fiesta-' + COD])).rows;
comprobar('cada cambio avisa por realtime', avisos.length >= 15, String(avisos.length));
comprobar('aviso público con versión creciente', avisos.every((a) => a.evento === 'cambio' && a.privado === false)
  && avisos.every((a, i) => i === 0 || a.payload.version > avisos[i - 1].payload.version));
// sin realtime.send las funciones siguen funcionando
await db.exec('drop function realtime.send(jsonb, text, text, boolean)');
await anonimo();
v = await rpc('fiesta_anadir', { p_codigo: COD, p_invitado: 'tokenDiego-0123456789', p_pista: pista(V(30)) });
comprobar('sin realtime.send igual se añade', v.cola.some((c) => c.video_id === V(30)));

// ---------------------------------------------------------------- cerrar
await falla('cerrar sin clave', () => rpc('fiesta_cerrar', { p_codigo: COD, p_clave: 'x' }), /Solo el anfitrión/);
v = await rpc('fiesta_cerrar', { p_codigo: COD, p_clave: CLAVE });
comprobar('cerrada', v.abierta === false && v.sonando === null);
comprobar('cerrar dos veces no falla', (await rpc('fiesta_cerrar', { p_codigo: COD, p_clave: CLAVE })).abierta === false);
await falla('no se añade a una cerrada', () => rpc('fiesta_anadir', { p_codigo: COD, p_invitado: ANA, p_pista: pista(V(40)) }), /ya terminó/);
await falla('no se vota en una cerrada', () => rpc('fiesta_votar', { p_codigo: COD, p_invitado: ANA, p_cancion: v.cola[0].id }), /ya terminó/);
await falla('no se entra a una cerrada', () => rpc('fiesta_entrar', { p_codigo: COD, p_invitado: 'tokenNuevo-0123456789' }), /ya terminó/);
comprobar('tomar en cerrada = null', (await rpc('fiesta_tomar', { p_codigo: COD, p_clave: CLAVE })) === null);
comprobar('se puede seguir viendo cerrada', (await rpc('fiesta_ver', { p_codigo: COD })).abierta === false);

// ---------------------------------------------------------------- topes y limpieza
await admin();
await db.query(`update public.fiestas set actividad = now() - interval '25 hours' where codigo = $1`, [vacia.codigo]);
await anonimo();
await rpc('fiesta_crear', { p_nombre: 'Limpieza' });
comprobar('fiestas viejas se borran al crear otra', (await rpc('fiesta_ver', { p_codigo: vacia.codigo })) === null);
// cola llena (300)
const llena = await rpc('fiesta_crear', { p_nombre: 'Llena', p_limite: 0 });
await admin();
await db.query(`insert into public.fiesta_canciones (codigo, video_id, invitado)
                select $1, 'x' || lpad(g::text, 10, '0'), 'otro' from generate_series(1, 300) g`, [llena.codigo]);
await anonimo();
await falla('cola llena', () => rpc('fiesta_anadir', { p_codigo: llena.codigo, p_invitado: ANA, p_pista: pista(V(50)) }), /cola de la fiesta está llena/);
// tope de fiestas por hora
await admin();
await db.query(`insert into public.fiestas (codigo, clave_md5) select substr('ABCDEFGHJKLMNPQRSTUVWXYZ', g / 24 % 24 + 1, 1) || substr('ABCDEFGHJKLMNPQRSTUVWXYZ', g % 24 + 1, 1) || 'ZZZZ', 'x' from generate_series(1, 320) g on conflict do nothing`);
const n = Number((await db.query(`select count(*) c from public.fiestas where creada > now() - interval '1 hour'`)).rows[0].c);
await anonimo();
if (n >= 300) await falla('tope de fiestas nuevas por hora', () => rpc('fiesta_crear', { p_nombre: 'Una más' }), /demasiadas fiestas/);
else comprobar('preparar tope de fiestas', false, String(n));

console.log(`\nfiesta.sql: ${ok} bien, ${mal} mal`);
process.exit(mal ? 1 : 0);
