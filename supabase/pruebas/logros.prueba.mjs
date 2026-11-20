// Pruebas de supabase/logros.sql (logros e insignias) sobre PGlite.
//
//   node supabase/pruebas/logros.prueba.mjs
//
// Carga esquema + social + logros y ejecuta el último DOS veces.
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
for (const f of ['esquema.sql', 'social.sql', 'logros.sql', 'logros.sql']) await db.exec(sql(f));

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
const guardar = (c, dias, plat, desb, vit = null) => uno(
  `select logros_guardar($1::jsonb, $2::text[], $3::text[], $4::jsonb, $5::text[])`,
  [JSON.stringify(c), dias, plat, JSON.stringify(desb), vit]);

for (const u of ['ana', 'amiga', 'extrano', 'publico', 'bloq']) await nuevaPersona(u);
await admin();
await q(`insert into amistades (de, para, estado, respondido) values ($1, $2, 'aceptada', now())`, [personas.ana, personas.amiga]);
await q(`insert into amistades (de, para, estado, respondido) values ($1, $2, 'aceptada', now())`, [personas.ana, personas.bloq]);
await q(`update perfiles set fecha_nacimiento = '1990-01-01' where id = $1`, [personas.publico]);
await q(`update perfiles set perfil_publico = true where id = $1`, [personas.publico]);
await como('ana');
await q(`select bloquear($1)`, [personas.bloq]);

console.log('Guardar y juntar');
await como('ana');
let r = await guardar({ segundos: 3600, canciones: 40, listas: 2 }, ['2026-11-01', '2026-11-02'], ['windows'],
  { primera_nota: 1700000000, horas_1: 1700000500 }, ['horas_1']);
comprobar('guarda los contadores', r.contadores.segundos === 3600 && r.contadores.canciones === 40, JSON.stringify(r));
comprobar('guarda la vitrina', JSON.stringify(r.vitrina) === '["horas_1"]', JSON.stringify(r.vitrina));
// el teléfono sabe menos de unas cosas y más de otras
r = await guardar({ segundos: 1000, canciones: 90, juntos: 1 }, ['2026-11-02', '2026-11-03'], ['android'],
  { primera_nota: 1600000000, juntos_1: 1700001000 });
comprobar('cada contador queda con el mayor', r.contadores.segundos === 3600 && r.contadores.canciones === 90
  && r.contadores.juntos === 1 && r.contadores.listas === 2, JSON.stringify(r.contadores));
comprobar('los días se juntan sin repetir', JSON.stringify(r.dias) === '["2026-11-03","2026-11-02","2026-11-01"]', JSON.stringify(r.dias));
comprobar('las plataformas se juntan', JSON.stringify(r.plataformas) === '["android","windows"]', JSON.stringify(r.plataformas));
comprobar('un logro conseguido en los dos se queda con la fecha más antigua', r.desbloqueados.primera_nota === 1600000000);
comprobar('los logros se juntan', Object.keys(r.desbloqueados).length === 3);
comprobar('vitrina null no la toca', JSON.stringify(r.vitrina) === '["horas_1"]');

console.log('Validar');
r = await guardar({ segundos: -50, 'MAL clave': 9, canciones: 'mucho', listas: 3.9 }, ['ayer', '2026-11-04'], ['nokia'],
  { 'X-raro': 1, horas_10: 'hoy' }, ['juntos_1', 'juntos_1', 'no_lo_tengo', 'primera_nota', 'horas_1']);
comprobar('negativos, textos y claves raras no cuentan', r.contadores.segundos === 3600 && r.contadores.canciones === 90
  && !('MAL clave' in r.contadores) && r.contadores.listas === 3, JSON.stringify(r.contadores));
comprobar('solo fechas válidas', !r.dias.includes('ayer') && r.dias.includes('2026-11-04'));
comprobar('plataformas inventadas no entran', !r.plataformas.includes('nokia'));
comprobar('desbloqueados raros no entran', !('X-raro' in r.desbloqueados) && !('horas_10' in r.desbloqueados));
comprobar('la vitrina solo lleva logros conseguidos, sin repetir y hasta 3',
  JSON.stringify(r.vitrina) === '["juntos_1","primera_nota","horas_1"]', JSON.stringify(r.vitrina));
await falla('datos enormes no entran', () => guardar({}, Array.from({ length: 1200 }, () => '2026-01-01'), [], {}),
  /demasiado grandes/);
await falla('contadores que no son objeto no entran', () => uno(`select logros_guardar('[1,2]'::jsonb)`), /no válidos/);
const muchos = Array.from({ length: 500 }, (_, i) => '2025-' + String(1 + (i % 12)).padStart(2, '0') + '-' + String(1 + Math.floor(i / 12)).padStart(2, '0'));
r = await guardar({}, muchos, [], {});
comprobar('se guardan como mucho 400 días', r.dias.length === 400, String(r.dias.length));

console.log('Permisos');
comprobar('logros_mios devuelve lo mío', (await uno(`select logros_mios()`)).contadores.canciones === 90);
await falla('nadie escribe la tabla directamente', () => q(`update logros set contadores = '{"segundos": 999999}'`), /permission|denied/);
await como('extrano');
comprobar('otra persona no lee mi fila', (await q(`select * from logros`)).length === 0);
await anonimo();
await falla('anon no guarda', () => guardar({ segundos: 1 }, [], [], {}), /permission|denied/);

console.log('Vitrina en el perfil');
await como('amiga');
let v = await uno(`select logros_de('ANA')`);
comprobar('una amiga ve mi vitrina', v && JSON.stringify(v.vitrina) === '["juntos_1","primera_nota","horas_1"]' && v.total === 3, JSON.stringify(v));
comprobar('con la fecha de cada uno', v.fechas.primera_nota === 1600000000);
await como('extrano');
comprobar('un extraño NO la ve (perfil privado)', (await uno(`select logros_de('ana')`)) === null);
await como('bloq');
comprobar('alguien bloqueado NO la ve', (await uno(`select logros_de('ana')`)) === null);
await como('publico');
await guardar({}, [], [], { racha_7: 1700000000 }, ['racha_7']);
await como('extrano');
v = await uno(`select logros_de('publico')`);
comprobar('un perfil público (mayor de edad) se ve', v && v.vitrina[0] === 'racha_7', JSON.stringify(v));
comprobar('quien aún no tiene logros devuelve vacío', JSON.stringify((await uno(`select logros_de('extrano')`)).vitrina) === '[]');
comprobar('un usuario que no existe da null', (await uno(`select logros_de('nadie')`)) === null);

console.log('Borrar cuenta');
await admin();
await q(`delete from auth.users where id = $1`, [personas.ana]);
comprobar('al borrar la cuenta se borran sus logros', (await uno(`select count(*)::int from logros where user_id = $1`, [personas.ana])) === 0);

console.log(`\n${ok} bien, ${mal} mal`);
process.exit(mal ? 1 : 0);
