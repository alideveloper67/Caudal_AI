// Pruebas de supabase/listas_colaboradores.sql (listas con hasta 50 personas, gratis para todos) sobre PGlite.
//
//   node supabase/pruebas/listas_colaboradores.prueba.mjs
//
// Carga esquema + social + listas + listas_perfil + premium y ejecuta listas_colaboradores DOS veces.
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
for (const f of ['esquema.sql', 'social.sql', 'listas.sql', 'listas_perfil.sql', 'premium.sql',
  'listas_colaboradores.sql', 'listas_colaboradores.sql']) {
  await db.exec(sql(f));
}

let ok = 0, mal = 0;
function comprobar(nombre, cond, detalle = '') {
  if (cond) ok++; else { mal++; console.log('  FALLA: ' + nombre + (detalle ? '  -> ' + detalle : '')); }
}
const personas = {};
async function nuevaPersona(usuario) {
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

await nuevaPersona('ana');   // la dueña, sin ningún título de donador
for (let i = 1; i <= 52; i++) await nuevaPersona('m' + i);

await como('ana');
const lista = (await q(`insert into listas (nombre) values ('Fiesta grande') returning id`))[0].id;
const codigo = await uno(`select compartir_lista($1)`, [lista]);

// ---- el tope nuevo
await como('m1');
for (let i = 1; i <= 20; i++) { await como('m' + i); await q(`select unirse_a_lista($1)`, [codigo]); }
await como('m21');
comprobar('el miembro 21 ya entra (antes el tope era 20)', (await uno(`select unirse_a_lista($1)`, [codigo])).lista_id === lista);
for (let i = 22; i <= 50; i++) { await como('m' + i); await q(`select unirse_a_lista($1)`, [codigo]); }
await admin();
comprobar('50 miembros caben', (await uno(`select count(*)::int from lista_miembros where lista_id = $1`, [lista])) === 50);
await como('m51');
await falla('el miembro 51 no entra y el mensaje dice 50', async () => { await q(`select unirse_a_lista($1)`, [codigo]); },
  /ya tiene 50 personas, que es el máximo/);
await como('m7');
comprobar('quien ya está dentro puede volver a pulsar unirse con la lista llena',
  (await uno(`select unirse_a_lista($1)`, [codigo])).lista_id === lista);
await como('ana');
const dueno = await uno(`select unirse_a_lista($1)`, [codigo]);
comprobar('el dueño con su propio código sigue recibiendo es_dueno', dueno.es_dueno === true && dueno.lista_id === lista);
await q(`select quitar_miembro($1, $2)`, [lista, personas.m1]);
await como('m51');
comprobar('al hacer lugar entra el 51', (await uno(`select unirse_a_lista($1)`, [codigo])).lista_id === lista);
await como('m52');
await falla('y el 52 espera de nuevo', async () => { await q(`select unirse_a_lista($1)`, [codigo]); }, /50 personas/);

// ---- gratis para todos: la dueña no es donadora y aun así sirve
await admin();
comprobar('la dueña no tiene ningún título especial',
  (await uno(`select count(*)::int from titulos_especiales where user_id = $1`, [personas.ana])) === 0);

// ---- el resto del contrato sigue igual
await como('m10');
comprobar('un miembro sigue viendo la lista en mis_listas_compartidas',
  (await uno(`select jsonb_array_length(mis_listas_compartidas())::int`)) === 1);
await como('ana');
comprobar('miembros_lista ve a los 50 más la dueña', (await uno(`select jsonb_array_length(miembros_lista($1))::int`, [lista])) === 51);

// ---- permisos
await anonimo();
await falla('anon NO puede unirse', async () => { await q(`select unirse_a_lista($1)`, [codigo]); }, /permission denied|permiso/i);
await como('m3');
await falla('el tope no se consulta desde la app', async () => { await q(`select max_miembros_lista()`); }, /permission denied/i);
await admin();
comprobar('el tope vale 50', (await uno(`select max_miembros_lista()`)) === 50);

// ---- repetible con datos
await db.exec(sql('listas_colaboradores.sql'));
comprobar('se ejecuta otra vez con datos cargados', true);

console.log(`\n${ok} bien, ${mal} mal`);
process.exit(mal ? 1 : 0);
