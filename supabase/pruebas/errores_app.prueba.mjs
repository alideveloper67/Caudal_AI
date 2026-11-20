// Pruebas de supabase/errores_app.sql (aviso de errores de las apps) sobre PGlite.
//
//   node supabase/pruebas/errores_app.prueba.mjs
//
// Carga esquema + errores_app y ejecuta el último DOS veces (se puede repetir sin romper nada).
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
for (const f of ['esquema.sql', 'errores_app.sql', 'errores_app.sql']) await db.exec(sql(f));

let ok = 0, mal = 0;
function comprobar(nombre, cond, detalle = '') {
  if (cond) ok++; else { mal++; console.log('  FALLA: ' + nombre + (detalle ? '  -> ' + detalle : '')); }
}
async function q(t, p = []) { return (await db.query(t, p)).rows; }
async function uno(t, p = []) { const r = await q(t, p); return Object.values(r[0])[0]; }
async function anonimo() {
  await db.exec('reset role');
  await db.query(`select set_config('request.jwt.claim.sub', '', false)`);
  await db.exec('set role anon');
}
async function admin() { await db.exec('reset role'); }
async function falla(nombre, fn, patron) {
  try { await fn(); comprobar(nombre, false, 'no falló'); }
  catch (e) { comprobar(nombre, patron ? patron.test(String(e.message)) : true, String(e.message)); }
}
const informe = (huella, extra = {}) => ({
  plataforma: 'windows', version: '2.7.2', sistema: 'Windows 10 (AMD64)', pantalla: 'Ventana', origen: 'interfaz',
  tipo: 'ZeroDivisionError', mensaje: 'division by zero', traza: 'Traceback...', huella, veces: 1, ...extra,
});
async function mandar(i) {
  const cols = Object.keys(i);
  await q(`insert into errores_app (${cols.join(', ')}) values (${cols.map((_, n) => '$' + (n + 1)).join(', ')})`,
    Object.values(i));
}

console.log('Mandar');
await anonimo();
await mandar(informe('a1b2c3d4e5f60718'));
await mandar(informe('a1b2c3d4e5f60718', { plataforma: 'android', creado: '2001-01-01', primera_vez: '2999-01-01' }));
await admin();
comprobar('anon manda informes', (await uno(`select count(*)::int from errores_app`)) === 2);
comprobar('la fecha la pone el servidor (no la app)',
  (await uno(`select count(*)::int from errores_app where creado < now() - interval '1 day'`)) === 0);
comprobar('una primera_vez en el futuro se corrige',
  (await uno(`select count(*)::int from errores_app where primera_vez > now() + interval '1 day'`)) === 0);

console.log('Leer y tocar');
await anonimo();
await falla('anon NO lee los informes', () => q(`select * from errores_app`), /permission|denied/);
await falla('anon NO borra', () => q(`delete from errores_app`), /permission|denied/);
await falla('anon NO cambia', () => q(`update errores_app set tipo = 'x'`), /permission|denied/);
await db.exec('reset role');
await db.exec('set role authenticated');
await falla('con cuenta tampoco se leen', () => q(`select * from errores_app`), /permission|denied/);

console.log('Validar');
await anonimo();
await falla('plataforma inventada no entra', () => mandar(informe('a1b2c3d4e5f60718', { plataforma: 'nokia' })), /check/);
await falla('huella que no es hexadecimal no entra', () => mandar(informe('hola-mundo')), /check/);
await falla('una traza enorme no entra', () => mandar(informe('a1b2c3d4e5f60718', { traza: 'x'.repeat(9000) })), /check/);
await falla('veces = 0 no entra', () => mandar(informe('a1b2c3d4e5f60718', { veces: 0 })), /check/);
await falla('sin version no entra', () => mandar(informe('a1b2c3d4e5f60718', { version: '' })), /check/);

console.log('Freno');
for (let i = 0; i < 40; i++) await mandar(informe('ffffffffffffffff'));
await admin();
comprobar('de un mismo error se guardan como mucho 30 por hora',
  (await uno(`select count(*)::int from errores_app where huella = 'ffffffffffffffff'`)) === 30);
await anonimo();
await mandar(informe('eeeeeeeeeeeeeeee'));
await admin();
comprobar('otro error distinto sí entra', (await uno(`select count(*)::int from errores_app where huella = 'eeeeeeeeeeeeeeee'`)) === 1);
comprobar('limpiar no es de las apps',
  (await uno(`select has_function_privilege('anon', 'public.errores_app_limpiar()', 'execute')`)) === false);
await q(`update errores_app set creado = now() - interval '200 days' where huella = 'eeeeeeeeeeeeeeee'`);
comprobar('limpiar borra lo viejo', (await uno(`select errores_app_limpiar()`)) === 1);

console.log('Consulta de herramientas/ver_errores.py');
// la consulta que agrupa por traza se pide a la propia herramienta y se ejecuta aquí de verdad
const { execFileSync } = await import('node:child_process');
const raiz = path.join(aqui, '..', '..');
const sqlDe = (expr) => execFileSync('python', ['-c',
  `import sys; sys.path.insert(0, r"${path.join(raiz, 'herramientas')}"); import ver_errores as v; print(${expr})`],
  { encoding: 'utf8' }).trim();
await anonimo();
for (let i = 0; i < 3; i++) await mandar(informe('abcabcabcabcabca', { veces: 2, plataforma: i ? 'android' : 'web', version: '2.6.' + i }));
await admin();
const grupos = await q(sqlDe('v.sql_agrupados(30)'));
const g = grupos.find((x) => x.huella === 'abcabcabcabcabca');
comprobar('agrupa por traza y suma las veces', g && Number(g.veces) === 6 && g.informes === 3, JSON.stringify(g));
comprobar('junta plataformas y versiones', g && g.plataformas.join() === 'android,web' && g.versiones.length === 3);
comprobar('el que más pasó va primero', Number(grupos[0].veces) >= Number(grupos[grupos.length - 1].veces));
const soloWeb = await q(sqlDe(`v.sql_agrupados(30, "web")`));
comprobar('filtra por plataforma', soloWeb.length === 1 && Number(soloWeb[0].veces) === 2, JSON.stringify(soloWeb));
const detalle = await q(sqlDe(`v.sql_detalle("abcabc")`));
comprobar('el detalle de un grupo trae sus informes', detalle.length === 3);

console.log(`\n${ok} bien, ${mal} mal`);
process.exit(mal ? 1 : 0);
