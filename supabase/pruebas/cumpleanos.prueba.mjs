// Pruebas de supabase/cumpleanos.sql (qué amigos cumplen hoy, sin revelar la fecha) sobre PGlite.
//
//   node supabase/pruebas/cumpleanos.prueba.mjs
//
// Carga esquema + social + cumpleanos y ejecuta el último DOS veces.
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
for (const f of ['esquema.sql', 'social.sql', 'cumpleanos.sql', 'cumpleanos.sql']) await db.exec(sql(f));

let ok = 0, mal = 0;
function comprobar(nombre, cond, detalle = '') {
  if (cond) ok++; else { mal++; console.log('  FALLA: ' + nombre + (detalle ? '  -> ' + detalle : '')); }
}
const personas = {};
async function nuevaPersona(usuario, nacimiento) {
  const r = await db.query(
    `insert into auth.users (id, email, raw_user_meta_data)
     values (gen_random_uuid(), $1, jsonb_build_object('usuario', $2::text, 'nombre', $2::text)) returning id`,
    [usuario + '@prueba.test', usuario]);
  personas[usuario] = r.rows[0].id;
  if (nacimiento) await db.query(`update public.perfiles set fecha_nacimiento = $1 where id = $2`, [nacimiento, r.rows[0].id]);
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
async function volver() { if (quienSoy === '__admin') await admin(); else if (quienSoy === '__anon') await anonimo(); else await como(quienSoy); }
async function falla(nombre, fn, patron) {
  try { await fn(); comprobar(nombre, false, 'no falló'); }
  catch (e) { comprobar(nombre, patron ? patron.test(String(e.message)) : true, String(e.message)); }
  await volver();
}

// el día de hoy en Lima, como lo calcula la función
await admin();
const hoyLima = (await q(`select to_char((now() at time zone 'America/Lima')::date, 'YYYY-MM-DD') as d`))[0].d;
const [aH, mH, dH] = hoyLima.split('-').map(Number);
const aniosAtras = (n) => `${aH - n}-${String(mH).padStart(2, '0')}-${String(dH).padStart(2, '0')}`;
// otro día cualquiera (mañana / ayer), en 1995
const desplazado = (dias) => new Date(Date.UTC(1995, mH - 1, dH) + dias * 864e5).toISOString().slice(0, 10);

for (const [u, nac] of [['yo', '1990-06-15'], ['hoy', aniosAtras(20)], ['manana', desplazado(1)], ['ayer', desplazado(-1)],
  ['sinfecha', null], ['extrano', aniosAtras(30)], ['bloq', aniosAtras(25)], ['pendiente', aniosAtras(22)],
  ['bisiesto', '2000-02-29'], ['amigo28', '1999-02-28']]) await nuevaPersona(u, nac);
const amistad = (a, b, estado = 'aceptada') => q(
  `insert into public.amistades (de, para, estado) values ($1, $2, $3)`, [personas[a], personas[b], estado]);
for (const u of ['hoy', 'manana', 'ayer', 'sinfecha', 'bloq', 'bisiesto', 'amigo28']) await amistad('yo', u);
await amistad('pendiente', 'yo', 'pendiente');   // ni siquiera es amiga
await amistad('extrano', 'hoy');                  // amiga de otro, no mía
await q(`insert into public.bloqueos (quien, a) values ($1, $2)`, [personas.yo, personas.bloq]);

// ---- la función de verdad (hoy, en Lima)
// (si hoy fuera 28 de febrero de un año no bisiesto, también saldrían los de 28 y 29; se descuentan)
await como('yo');
const filas = await q(`select * from amigos_cumplen_hoy()`);
const ids = filas.map((r) => r.amigos_cumplen_hoy);
const feb28 = mH === 2 && dH === 28;
comprobar('sale el amigo que cumple hoy', ids.includes(personas.hoy), JSON.stringify(ids));
comprobar('devuelve solo ids, ni fecha ni edad', filas.length > 0 && Object.keys(filas[0]).length === 1);
comprobar('quien cumple pero no es amigo mío no sale', !ids.includes(personas.extrano));
comprobar('la solicitud pendiente no cuenta', !ids.includes(personas.pendiente));
comprobar('el bloqueado no sale', !ids.includes(personas.bloq));
comprobar('quien no puso fecha no sale', !ids.includes(personas.sinfecha));
comprobar('mañana y ayer no salen', !ids.includes(personas.manana) && !ids.includes(personas.ayer));
if (!feb28) comprobar('solo uno cumple hoy', ids.length === 1, JSON.stringify(ids));

// ---- desde el otro lado: «hoy» ve a «yo» solo si yo cumple hoy (no cumple)
await como('hoy');
const deHoy = (await q(`select * from amigos_cumplen_hoy()`)).map((x) => x.amigos_cumplen_hoy);
comprobar('cada quien ve solo a SUS amigos que cumplen (no a yo, que no cumple)', !deHoy.includes(personas.yo) && deHoy.includes(personas.extrano), JSON.stringify(deHoy));

// ---- permisos
await anonimo();
await falla('sin cuenta no se puede llamar', async () => { await q(`select * from amigos_cumplen_hoy()`); }, /permission denied/i);
await como('yo');
await falla('la ayuda con fecha no la llama nadie desde la app', async () => { await q(`select * from amigos_cumplen_el('2026-02-28')`); }, /permission denied/i);

// ---- regla del 29 de febrero (con la ayuda, como administrador pero «siendo» yo)
await admin();
await db.query(`select set_config('request.jwt.claim.sub', $1, false)`, [personas.yo]);
const el = async (dia) => (await q(`select * from amigos_cumplen_el($1::date)`, [dia])).map((r) => r.amigos_cumplen_el);
let r = await el('2026-02-28');
comprobar('año no bisiesto: el del 29 se celebra el 28', r.includes(personas.bisiesto) && r.includes(personas.amigo28) && r.length === 2, JSON.stringify(r));
r = await el('2026-03-01');
comprobar('año no bisiesto: el 1 de marzo no es de nadie', r.length === 0, JSON.stringify(r));
r = await el('2028-02-29');
comprobar('año bisiesto: el 29 sí es el 29', r.length === 1 && r[0] === personas.bisiesto, JSON.stringify(r));
r = await el('2028-02-28');
comprobar('año bisiesto: el 28 es solo del que nació el 28', r.length === 1 && r[0] === personas.amigo28, JSON.stringify(r));
r = await el('2100-02-28');
comprobar('2100 no es bisiesto (siglo): se celebra el 28', r.includes(personas.bisiesto), JSON.stringify(r));
r = await el('2000-02-29');
comprobar('2000 sí es bisiesto', r.length === 1 && r[0] === personas.bisiesto, JSON.stringify(r));

// ---- no hay forma de leer la fecha de otro con esto
await como('yo');
const ajena = await q(`select fecha_nacimiento from public.perfiles where id = $1`, [personas.hoy]);
comprobar('la tabla de perfiles no entrega la fecha de un amigo', ajena.length === 0 || ajena[0].fecha_nacimiento == null,
  JSON.stringify(ajena));

console.log(`cumpleanos: ${ok} bien, ${mal} mal`);
process.exit(mal ? 1 : 0);
