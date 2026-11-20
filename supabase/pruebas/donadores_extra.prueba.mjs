// Pruebas de supabase/donadores_extra.sql (color del nombre y pared de agradecimiento) sobre PGlite.
//
//   node supabase/pruebas/donadores_extra.prueba.mjs
//
// Carga esquema + social + listas + listas_perfil + premium + perfil_portada + donadores_extra y ejecuta
// el último DOS veces (tiene que poder pegarse de nuevo sin romper nada).
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
  'perfil_portada.sql', 'donadores_extra.sql', 'donadores_extra.sql']) {
  await db.exec(sql(f));
}

let ok = 0, mal = 0;
const fallos = [];
function comprobar(nombre, cond, detalle = '') {
  if (cond) ok++; else { mal++; fallos.push(nombre); console.log('  FALLA: ' + nombre + (detalle ? '  -> ' + detalle : '')); }
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
const titulo = (u, clave, nombre, vence = null, creado = null) => q(
  `insert into titulos_especiales (user_id, titulo, nombre, vence, creado) values ($1, $2, $3, $4, coalesce($5, now()))
   on conflict (user_id, titulo) do update set vence = excluded.vence`, [personas[u], clave, nombre, vence, creado]);
const colorDe = async (u) => (await q(`select color_nombre from perfiles where id = $1`, [personas[u]]))[0].color_nombre;

// dona: donador · funda: fundador · prueba: pase de prueba · normal: sin nada · nino: donador menor de edad
// vencido: donador cuyo título venció · bloq: donador bloqueado por normal
for (const u of ['dona', 'funda', 'prueba', 'normal', 'nino', 'vencido', 'bloq']) await nuevaPersona(u);
await admin();
await titulo('dona', 'donador_caudal', 'Donador de Caudal', null, '2026-03-01');
await titulo('funda', 'fundador_caudal', 'Fundador de Caudal', null, '2026-05-01');
await titulo('prueba', 'invitado_caudal', 'Donador de prueba', new Date(Date.now() + 5 * 864e5).toISOString());
await titulo('nino', 'donador_caudal', 'Donador de Caudal');
await titulo('vencido', 'donador_caudal', 'Donador de Caudal');
await titulo('bloq', 'donador_caudal', 'Donador de Caudal', null, '2026-01-01');
await q(`update perfiles set fecha_nacimiento = date '1990-01-01'
          where id = any($1::uuid[])`, [[personas.dona, personas.funda, personas.prueba, personas.normal,
  personas.vencido, personas.bloq]]);
await q(`update perfiles set fecha_nacimiento = (now() - interval '12 years')::date where id = $1`, [personas.nino]);

// ---- columnas por defecto
console.log('Por defecto');
comprobar('nadie empieza en la pared', (await uno(`select count(*)::int from perfiles where en_pared`)) === 0);
comprobar('nadie empieza con color', (await uno(`select count(*)::int from perfiles where color_nombre is not null`)) === 0);

// ---- color del nombre
console.log('Color del nombre');
await como('dona');
await q(`update perfiles set color_nombre = '#ff5c8a' where id = auth.uid()`);
comprobar('el donador guarda su color (en mayúsculas)', (await colorDe('dona')) === '#FF5C8A', await colorDe('dona'));
await q(`update perfiles set color_nombre = 'rojo' where id = auth.uid()`);
comprobar('un color mal escrito no rompe nada: se queda el de antes', (await colorDe('dona')) === '#FF5C8A');
await q(`update perfiles set color_nombre = '  ' where id = auth.uid()`);
comprobar('un color en blanco lo quita', (await colorDe('dona')) === null);
await q(`update perfiles set color_nombre = '#22D3EE' where id = auth.uid()`);
await como('prueba');
await q(`update perfiles set color_nombre = '#A78BFA' where id = auth.uid()`);
comprobar('con un pase de prueba también se puede', (await colorDe('prueba')) === '#A78BFA');
await como('normal');
await q(`update perfiles set color_nombre = '#FFC857' where id = auth.uid()`);
comprobar('sin beneficios el color no se escribe', (await colorDe('normal')) === null);
await como('funda');
await q(`update perfiles set color_nombre = '#FFC857', en_pared = true where id = auth.uid()`);
await como('vencido');
await q(`update perfiles set color_nombre = '#7CFFB2', en_pared = true where id = auth.uid()`);
await como('bloq');
await q(`update perfiles set color_nombre = '#FF7A45', en_pared = true where id = auth.uid()`);
await como('nino');
await q(`update perfiles set color_nombre = '#4DA8FF', en_pared = true where id = auth.uid()`);
await admin();
await falla('la base no acepta un color con otra forma ni escribiéndolo a mano sin el trigger',
  async () => {
    await db.exec(`alter table perfiles disable trigger perfil_donadores_validar`);
    try { await q(`update perfiles set color_nombre = 'azul' where id = $1`, [personas.dona]); }
    finally { await db.exec(`alter table perfiles enable trigger perfil_donadores_validar`); }
  }, /perfil_color_nombre_forma/);

// el título de «vencido» se acaba: su color se conserva pero deja de verse
await q(`update titulos_especiales set vence = now() - interval '1 day' where user_id = $1`, [personas.vencido]);
await como('vencido');
await q(`update perfiles set color_nombre = '#000000', bio = 'hola' where id = auth.uid()`);
comprobar('sin premium se conserva el color de antes aunque se toque el perfil', (await colorDe('vencido')) === '#7CFFB2');

// ---- leer colores
console.log('colores_nombre');
await como('normal');
await q(`select bloquear($1)`, [personas.bloq]);
let c = await uno(`select colores_nombre($1::text[])`,
  [['dona', 'FUNDA', ' prueba ', 'normal', 'vencido', 'bloq', 'nadie']]);
comprobar('salen los colores vigentes (sin importar mayúsculas ni espacios)',
  c.dona === '#22D3EE' && c.funda === '#FFC857' && c.prueba === '#A78BFA', JSON.stringify(c));
comprobar('no sale quien no tiene color', !('normal' in c) && !('nadie' in c));
comprobar('no sale el color de quien ya no tiene premium', !('vencido' in c));
comprobar('no sale el color de alguien bloqueado', !('bloq' in c));
await como('bloq');
c = await uno(`select colores_nombre($1::text[])`, [['bloq', 'normal']]);
comprobar('cada quien ve su propio color aunque haya un bloqueo', c.bloq === '#FF7A45', JSON.stringify(c));
comprobar('una lista vacía o null no falla',
  JSON.stringify(await uno(`select colores_nombre('{}'::text[])`)) === '{}'
  && JSON.stringify(await uno(`select colores_nombre(null)`)) === '{}');
const muchos = Array.from({ length: 250 }, (_, i) => 'x' + i).concat(['dona']);
c = await uno(`select colores_nombre($1::text[])`, [muchos]);
comprobar('se miran como mucho 200 usuarios por llamada', !('dona' in c), JSON.stringify(c));
await anonimo();
await falla('sin sesión no se pueden pedir colores', () => q(`select colores_nombre(array['dona'])`),
  /permission denied/);
await como('dona');
await falla('las ayudas internas no se llaman desde la app', () => q(`select color_nombre_de($1)`, [personas.dona]),
  /permission denied/);

// ---- pared de agradecimiento
console.log('Pared');
await como('dona');
await q(`update perfiles set en_pared = true, nombre = 'Doña Ana' where id = auth.uid()`);
await como('prueba');
await q(`update perfiles set en_pared = true where id = auth.uid()`);
await como('normal');
await q(`update perfiles set en_pared = true where id = auth.uid()`);
await anonimo();
let pared = await uno(`select pared_agradecimiento()`);
const usuarios = pared.map((x) => x.usuario);
comprobar('la web (sin sesión) puede leer la pared', Array.isArray(pared));
comprobar('primero los fundadores y luego por antigüedad', JSON.stringify(usuarios) === JSON.stringify(['funda', 'bloq', 'dona']),
  JSON.stringify(usuarios));
comprobar('no salen las pruebas ni quien no dona', !usuarios.includes('prueba') && !usuarios.includes('normal'));
comprobar('no sale un donador vencido', !usuarios.includes('vencido'));
comprobar('un menor de edad nunca sale en la pared pública', !usuarios.includes('nino'));
const ana = pared.find((x) => x.usuario === 'dona');
comprobar('cada fila trae nombre, tipo, color y fecha',
  ana.nombre === 'Doña Ana' && ana.tipo === 'donador' && ana.color === '#22D3EE' && !!ana.desde, JSON.stringify(ana));
comprobar('el fundador sale como fundador', pared[0].tipo === 'fundador');
comprobar('no se entrega nada más del perfil',
  pared.every((x) => Object.keys(x).sort().join(',') === 'color,desde,nombre,tipo,usuario'), JSON.stringify(pared[0]));
await como('dona');
await q(`update perfiles set en_pared = false where id = auth.uid()`);
pared = await uno(`select pared_agradecimiento()`);
comprobar('al desmarcar la casilla sale de la pared', !pared.some((x) => x.usuario === 'dona'));
await q(`update perfiles set en_pared = true where id = auth.uid()`);
await falla('nadie cambia la casilla de otro', async () => {
  const r = await q(`update perfiles set en_pared = false where id = $1 returning id`, [personas.funda]);
  if (r.length === 0) throw new Error('sin filas');
}, /sin filas/);

// ---- repetibilidad
console.log('Repetibilidad con datos');
await admin();
await db.exec(sql('donadores_extra.sql'));
comprobar('al ejecutar de nuevo no se pierden colores ni casillas',
  (await colorDe('dona')) === '#22D3EE'
  && (await uno(`select en_pared from perfiles where id = $1`, [personas.funda])) === true);
// premium.sql vuelve a definir perfil_validar: el color sigue funcionando después
await db.exec(sql('premium.sql'));
await como('funda');
await q(`update perfiles set color_nombre = '#4DA8FF' where id = auth.uid()`);
comprobar('volver a pegar premium.sql no rompe el color', (await colorDe('funda')) === '#4DA8FF');

console.log(`\n${ok} comprobaciones pasan, ${mal} fallan.`);
if (mal) { console.log('Fallos: ' + fallos.join(' | ')); process.exit(1); }
