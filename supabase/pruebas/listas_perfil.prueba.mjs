// Pruebas de supabase/listas_perfil.sql (listas públicas o privadas y «mostrar en el perfil») sobre PGlite.
//
//   node supabase/pruebas/listas_perfil.prueba.mjs
//
// Carga esquema.sql + social.sql + listas.sql + listas_perfil.sql y ejecuta el último DOS veces.
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import { createRequire } from 'node:module';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const sql = (n) => readFileSync(path.join(aqui, '..', n), 'utf8');
const ruta = process.env.PGLITE_RUTA
  || 'C:\\Users\\USER\\agenty-ai\\node_modules\\@electric-sql\\pglite';
const require = createRequire(import.meta.url);
const { PGlite } = await import(pathToFileURL(require.resolve(ruta)).href);
const { SUPABASE_FALSO } = await import('./arnes.sql.mjs');

process.on('unhandledRejection', (e) => { console.log('ERROR: ' + (e && e.message || e)); process.exit(2); });
const db = new PGlite();
await db.exec(SUPABASE_FALSO);
await db.exec(sql('esquema.sql'));
await db.exec(sql('social.sql'));
await db.exec(sql('listas.sql'));
await db.exec(sql('listas_perfil.sql'));
await db.exec(sql('listas_perfil.sql')); // repetible

let ok = 0, mal = 0;
const fallos = [];
function comprobar(nombre, cond, detalle = '') {
  if (cond) ok++; else { mal++; fallos.push(nombre); console.log('  FALLA: ' + nombre + (detalle ? '  -> ' + detalle : '')); }
}
const personas = {};
async function nuevaPersona(usuario, publico) {
  const r = await db.query(
    `insert into auth.users (id, email, raw_user_meta_data)
     values (gen_random_uuid(), $1, jsonb_build_object('usuario', $2::text, 'nombre', $2::text)) returning id`,
    [usuario + '@prueba.test', usuario]);
  personas[usuario] = r.rows[0].id;
}
let quienSoy = null;
async function como(u) {
  quienSoy = u;
  await db.exec('reset role');
  await db.query(`select set_config('request.jwt.claim.sub', $1, false)`, [personas[u]]);
  await db.exec('set role authenticated');
}
async function anonimo() {
  quienSoy = '__anon';
  await db.exec('reset role');
  await db.query(`select set_config('request.jwt.claim.sub', '', false)`);
  await db.exec('set role anon');
}
async function admin() { quienSoy = '__admin'; await db.exec('reset role'); }
async function q(t, p = []) { return (await db.query(t, p)).rows; }
async function uno(t, p = []) { const r = await q(t, p); return Object.values(r[0])[0]; }
async function volver() { if (quienSoy === '__admin') await admin(); else if (quienSoy === '__anon') await anonimo(); else await como(quienSoy); }
async function falla(nombre, fn, patron) {
  try { await fn(); comprobar(nombre, false, 'no falló'); }
  catch (e) { comprobar(nombre, patron ? patron.test(String(e.message)) : true, String(e.message)); }
  await volver();
}

console.log('Cargado esquema + social + listas + listas_perfil (x2).');
for (const u of ['ana', 'beto', 'carla', 'dani']) await nuevaPersona(u);

// ana tiene perfil público (mayor de edad); beto es su amigo; carla es una desconocida; dani está bloqueado por ana
await admin();
await q(`update perfiles set fecha_nacimiento = date '1990-01-01', perfil_publico = true where id = $1`, [personas.ana]);
await q(`update perfiles set fecha_nacimiento = date '1990-01-01' where id = any($1::uuid[])`, [[personas.beto, personas.carla, personas.dani]]);
const hayAmistad = await q(`select 1 from information_schema.tables where table_name = 'amistades'`);
console.log('  (tabla amistades: ' + (hayAmistad.length ? 'sí' : 'no') + ')');

await como('ana');
const pub = (await q(`insert into listas (nombre, descripcion, publica, en_perfil) values ('Pública en perfil', 'hola', true, true) returning id`))[0].id;
const pubOculta = (await q(`insert into listas (nombre, publica, en_perfil) values ('Pública oculta', true, false) returning id`))[0].id;
const priv = (await q(`insert into listas (nombre) values ('Privada') returning id`))[0].id;
const privTramposa = (await q(`insert into listas (nombre, publica, en_perfil) values ('Privada que pide perfil', false, true) returning id`))[0].id;
for (const l of [pub, pubOculta, priv]) {
  await q(`insert into lista_items (lista_id, clave, datos, orden) values ($1, 'yt:a', '{"titulo":"Tema A","artistas":[{"nombre":"Art A"}],"portada":"https://x/a.jpg"}', 1),
                                                                      ($1, 'yt:b', '{"titulo":"Tema B"}', 2)`, [l]);
}

console.log('Columnas y coherencia');
comprobar('por defecto una lista es privada y fuera del perfil',
  (await q(`select publica, en_perfil from listas where id = $1`, [priv]))[0].publica === false);
comprobar('pedir «en perfil» en una privada lo apaga solo',
  (await uno(`select en_perfil from listas where id = $1`, [privTramposa])) === false);
await q(`update listas set publica = false where id = $1`, [pub]);
comprobar('volver privada una lista la saca del perfil',
  (await uno(`select en_perfil from listas where id = $1`, [pub])) === false);
await q(`update listas set publica = true, en_perfil = true where id = $1`, [pub]);
comprobar('volver a hacerla pública y con perfil funciona', (await uno(`select en_perfil from listas where id = $1`, [pub])) === true);
await q(`update listas set nombre = 'Pública en perfil' where id = $1`, [pub]);
comprobar('cambiar solo el nombre (como hace una app vieja) no toca los ajustes',
  (await q(`select publica, en_perfil from listas where id = $1`, [pub]))[0].en_perfil === true);

console.log('Mi propio perfil');
const mias = await uno(`select listas_de_perfil('ana')`);
comprobar('yo veo todas mis listas (4)', mias.length === 4, String(mias.length));
comprobar('con sus ajustes', mias.some((l) => l.nombre === 'Privada' && l.publica === false && l.en_perfil === false)
  && mias.some((l) => l.nombre === 'Pública oculta' && l.publica === true && l.en_perfil === false));
comprobar('cada una trae el total y hasta 4 canciones', mias.find((l) => l.id === pub).total === 2 && mias.find((l) => l.id === pub).canciones.length === 2);
comprobar('las canciones traen título, artista y miniatura',
  JSON.stringify(Object.keys(mias.find((l) => l.id === pub).canciones[0]).sort()) === '["artista","miniatura","titulo"]');

console.log('Perfil de otra persona (público)');
await como('carla');
const deAna = await uno(`select listas_de_perfil('ana')`);
comprobar('carla solo ve la pública con perfil', deAna.length === 1 && deAna[0].id === pub, JSON.stringify(deAna.map((l) => l.nombre)));
comprobar('no se cuela ni la privada ni la pública oculta', !deAna.some((l) => [priv, pubOculta, privTramposa].includes(l.id)));
comprobar('usuario inexistente devuelve lista vacía', (await uno(`select listas_de_perfil('nadie')`)).length === 0);

console.log('Abrir una lista');
const abierta = await uno(`select ver_lista_publica($1)`, [pub]);
comprobar('una pública se abre con todas sus canciones', abierta && abierta.canciones.length === 2 && abierta.dueno.usuario === 'ana' && abierta.es_mia === false);
comprobar('una pública oculta del perfil se abre si se conoce el enlace', (await uno(`select ver_lista_publica($1)`, [pubOculta]))?.nombre === 'Pública oculta');
comprobar('una privada NO se abre aunque se tenga el id', (await uno(`select ver_lista_publica($1)`, [priv])) === null);
comprobar('un id que no existe devuelve null', (await uno(`select ver_lista_publica(gen_random_uuid())`)) === null);
await como('ana');
comprobar('mi propia privada sí la abro', (await uno(`select ver_lista_publica($1)`, [priv]))?.es_mia === true);

console.log('Datos directos (la privacidad no depende de las funciones)');
await como('carla');
comprobar('carla no lee la lista privada de ana por la API', (await q(`select id from listas where id = $1`, [priv])).length === 0);
comprobar('ni las canciones de una privada', (await q(`select 1 from lista_items where lista_id = $1`, [priv])).length === 0);
await falla('carla no puede volver pública una lista ajena', async () => {
  const r = await q(`update listas set publica = true where id = $1 returning id`, [priv]);
  if (r.length === 0) throw new Error('0 filas');
}, /0 filas/);
comprobar('y la lista sigue privada', (await (async () => { await admin(); return uno(`select publica from listas where id = $1`, [priv]); })()) === false);

console.log('Bloqueos');
await admin();
await q(`insert into bloqueos (quien, a) values ($1, $2)`, [personas.ana, personas.dani]);
await como('dani');
const bloq = await uno(`select listas_de_perfil('ana')`);
const hayBloqueo = (await uno(`select hay_bloqueo($1, $2)`, [personas.dani, personas.ana])) === true;
if (hayBloqueo) {
  comprobar('quien está bloqueado no ve las listas del perfil', bloq.length === 0);
  comprobar('ni abre una pública', (await uno(`select ver_lista_publica($1)`, [pub])) === null);
} else console.log('  (bloqueos: se omiten, no se pudo crear el bloqueo en el arnés)');

console.log('Permisos');
await anonimo();
await falla('anon no puede pedir listas_de_perfil', async () => { await q(`select listas_de_perfil('ana')`); }, /permission denied/i);
await falla('anon no puede abrir listas públicas', async () => { await q(`select ver_lista_publica($1)`, [pub]); }, /permission denied/i);

console.log('Repetibilidad con datos');
await admin();
await db.exec(sql('listas_perfil.sql'));
comprobar('se puede volver a ejecutar sin perder los ajustes', (await uno(`select en_perfil from listas where id = $1`, [pub])) === true);

console.log(`\n${ok} comprobaciones pasan, ${mal} fallan.`);
if (mal) { console.log('Fallos: ' + fallos.join(' | ')); process.exit(1); }
