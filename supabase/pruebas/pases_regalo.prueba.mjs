// Pruebas de supabase/pases_regalo.sql (códigos de regalo de los donadores) sobre PGlite.
//
//   node supabase/pruebas/pases_regalo.prueba.mjs
//
// Carga esquema + social + listas + listas_perfil + premium + pases_regalo y ejecuta el último DOS veces.
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
for (const f of ['esquema.sql', 'social.sql', 'listas.sql', 'listas_perfil.sql', 'premium.sql', 'pases_regalo.sql', 'pases_regalo.sql']) {
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
const titulo = (u, clave, nombre, vence) => q(
  `insert into titulos_especiales (user_id, titulo, nombre, vence) values ($1, $2, $3, $4)
   on conflict (user_id, titulo) do update set vence = excluded.vence`, [personas[u], clave, nombre, vence]);

for (const u of ['dona', 'fund', 'prueba', 'amigo1', 'amigo2', 'normal', 'amigo3']) await nuevaPersona(u);
await admin();
await titulo('dona', 'donador_caudal', 'Donador de Caudal', null);
await titulo('fund', 'fundador_caudal', 'Fundador de Caudal', null);
await titulo('prueba', 'invitado_caudal', 'Donador de prueba', new Date(Date.now() + 5 * 864e5).toISOString());

// ---- quién puede crear
await como('dona');
const a = await uno(`select crear_pase_regalo()`);
comprobar('un donador crea un código', a.ok === true && /^[A-Z2-9]{4}-[A-Z2-9]{4}$/.test(a.codigo), JSON.stringify(a));
comprobar('el código es de 7 días y un solo uso', a.dias === 7);
await como('fund');
const f = await uno(`select crear_pase_regalo()`);
comprobar('un fundador también crea', f.ok === true, JSON.stringify(f));
await como('normal');
comprobar('quien no dona no puede', (await uno(`select crear_pase_regalo()`)).ok === false);
await como('prueba');
comprobar('quien tiene solo la prueba no puede regalar pruebas', (await uno(`select crear_pase_regalo()`)).ok === false);
await anonimo();
await falla('sin cuenta no se puede crear', async () => { await q(`select crear_pase_regalo()`); }, /permission denied/i);

// ---- tope de 3 sin usar
await como('dona');
const b = await uno(`select crear_pase_regalo()`);
const c = await uno(`select crear_pase_regalo()`);
comprobar('el segundo y el tercero salen', b.ok && c.ok);
const d = await uno(`select crear_pase_regalo()`);
comprobar('el cuarto se frena con un mensaje claro', d.ok === false && /3 códigos/.test(d.mensaje), JSON.stringify(d));
comprobar('no se guardó un cuarto', (await uno(`select jsonb_array_length(mis_pases_regalo())`)) === 3);
comprobar('los códigos son distintos', new Set([a.codigo, b.codigo, c.codigo]).size === 3);

// ---- un amigo lo canjea con la función de siempre
await como('amigo1');
const canje = await uno(`select canjear_pase($1)`, [a.codigo.toLowerCase().replace('-', ' ')]);
comprobar('el amigo canjea (aunque lo escriba distinto)', canje.ok === true && canje.dias === 7, JSON.stringify(canje));
comprobar('y ya tiene beneficios', (await uno(`select mi_premium()`)).tipo === 'prueba');
await como('amigo2');
const otra = await uno(`select canjear_pase($1)`, [a.codigo]);
comprobar('el mismo código no sirve dos veces', otra.ok === false && /máximo de veces/.test(otra.mensaje), JSON.stringify(otra));

// ---- liberó un cupo y ve su estado
await como('dona');
const lista = await uno(`select mis_pases_regalo()`);
comprobar('ve 3 códigos y uno ya usado', lista.length === 3 && lista.filter((x) => x.usado).length === 1, JSON.stringify(lista));
comprobar('el usado ya no está vigente', lista.find((x) => x.codigo === a.codigo).vigente === false);
const e = await uno(`select crear_pase_regalo()`);
comprobar('al usarse uno, puede crear otro', e.ok === true, JSON.stringify(e));
await como('fund');
comprobar('no ve los códigos de otra persona', (await uno(`select jsonb_array_length(mis_pases_regalo())`)) === 1);

// ---- anular
await como('dona');
comprobar('no se anula uno ya usado', (await uno(`select anular_pase_regalo($1)`, [a.codigo])) === false);
comprobar('se anula uno sin usar', (await uno(`select anular_pase_regalo($1)`, [b.codigo])) === true);
await como('fund');
comprobar('no se anula el de otra persona', (await uno(`select anular_pase_regalo($1)`, [c.codigo])) === false);

// ---- caducidad
await admin();
await q(`update pases_prueba set caduca = now() - interval '1 hour' where codigo = $1`, [c.codigo]);
await como('amigo3');
const tarde = await uno(`select canjear_pase($1)`, [c.codigo]);
comprobar('un código caducado no sirve', tarde.ok === false && /caduc/.test(tarde.mensaje), JSON.stringify(tarde));
await como('dona');
const nuevos = await uno(`select mis_pases_regalo()`);
comprobar('el caducado se ve como no vigente', nuevos.find((x) => x.codigo === c.codigo).vigente === false);

// ---- permisos: las ayudas internas no se llaman desde fuera
await como('dona');
await falla('es_donador_de_verdad no se llama desde la app', async () => { await q(`select es_donador_de_verdad($1)`, [personas.dona]); }, /permission denied/i);
await admin();
comprobar('los códigos de regalo guardan quién los creó', (await uno(`select count(*)::int from pases_prueba where regala = $1`, [personas.dona])) >= 3);
await como('dona');
comprobar('la tabla sigue sin leerse desde la app', (await q(`select * from pases_prueba`)).length === 0);

console.log(`\n${ok} bien, ${mal} mal`);
process.exit(mal ? 1 : 0);
