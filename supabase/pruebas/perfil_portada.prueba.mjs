// Pruebas de supabase/perfil_portada.sql (portada del perfil de los donadores) sobre PGlite.
//
//   node supabase/pruebas/perfil_portada.prueba.mjs
//
// Carga esquema + social + listas + listas_perfil + premium + perfil_portada y ejecuta el último DOS veces.
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
  'perfil_portada.sql', 'perfil_portada.sql']) {
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
const portadaDe = async (u) => (await q(
  `select portada_cancion, portada_letra, portada_mascota from perfiles where id = $1`, [personas[u]]))[0];

for (const u of ['dona', 'amiga', 'extrano', 'bloq', 'normal']) await nuevaPersona(u);
await admin();
await titulo('dona', 'donador_caudal', 'Donador de Caudal', null);
// amiga de dona; bloq es amigo pero bloqueado por dona
await q(`insert into amistades (de, para, estado, respondido) values ($1, $2, 'aceptada', now())`, [personas.dona, personas.amiga]);
await q(`insert into amistades (de, para, estado, respondido) values ($1, $2, 'aceptada', now())`, [personas.dona, personas.bloq]);
await como('dona');
await q(`select bloquear($1)`, [personas.bloq]);

const cancion = { video_id: 'dQw4w9WgXcQ', titulo: 'Never Gonna Give You Up', artista: 'Rick Astley',
  miniatura: 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg', basura: 'x' };

// ---- el donador guarda su portada
console.log('Guardar');
await como('dona');
await q(`update perfiles set portada_cancion = $1::jsonb, portada_letra = $2, portada_mascota = $3 where id = auth.uid()`,
  [JSON.stringify(cancion), '  Never gonna give you up  ', ' Nyan ']);
const f = await portadaDe('dona');
comprobar('guarda la canción solo con sus cuatro claves',
  JSON.stringify(Object.keys(f.portada_cancion).sort()) === JSON.stringify(['artista', 'miniatura', 'titulo', 'video_id']), JSON.stringify(f.portada_cancion));
comprobar('la letra se recorta de espacios', f.portada_letra === 'Never gonna give you up', f.portada_letra);
comprobar('la mascota queda en minúsculas y sin espacios', f.portada_mascota === 'nyan', f.portada_mascota);
await q(`update perfiles set portada_letra = $1 where id = auth.uid()`, ['a'.repeat(400)]);
comprobar('una letra larguísima se corta a 160', (await portadaDe('dona')).portada_letra.length === 160);
await q(`update perfiles set portada_letra = '   ' where id = auth.uid()`);
comprobar('una letra en blanco se guarda como vacía (null)', (await portadaDe('dona')).portada_letra === null);
await q(`update perfiles set portada_cancion = '{"titulo":"sin id"}'::jsonb where id = auth.uid()`);
comprobar('una canción sin video_id se descarta', (await portadaDe('dona')).portada_cancion === null);
await q(`update perfiles set portada_cancion = $1::jsonb, portada_letra = 'Hola mundo' where id = auth.uid()`, [JSON.stringify(cancion)]);
await falla('una mascota con caracteres raros no entra', async () => {
  await q(`update perfiles set portada_mascota = 'Mi Mascota!' where id = auth.uid()`); }, /perfil_portada_forma|check/);

// ---- quién la ve
console.log('Ver');
const mia = await uno(`select portada_perfil('dona')`);
comprobar('yo veo la mía', mia && mia.cancion.video_id === 'dQw4w9WgXcQ' && mia.letra === 'Hola mundo' && mia.mascota === 'nyan', JSON.stringify(mia));
await como('amiga');
const amiga = await uno(`select portada_perfil('DONA')`);
comprobar('una amiga la ve (sin importar mayúsculas)', amiga && amiga.letra === 'Hola mundo', JSON.stringify(amiga));
await como('extrano');
comprobar('quien no es amigo NO la ve', (await uno(`select portada_perfil('dona')`)) === null);
await como('bloq');
comprobar('un amigo bloqueado NO la ve', (await uno(`select portada_perfil('dona')`)) === null);
await anonimo();
await falla('sin sesión no se puede preguntar', async () => { await q(`select portada_perfil('dona')`); }, /permission denied/i);
await como('amiga');
comprobar('un usuario que no existe devuelve null', (await uno(`select portada_perfil('nadie')`)) === null);
comprobar('texto vacío devuelve null', (await uno(`select portada_perfil('')`)) === null);
comprobar('null devuelve null', (await uno(`select portada_perfil(null)`)) === null);
comprobar('una amiga sin portada ni premium devuelve null', (await uno(`select portada_perfil('amiga')`)) === null);

// ---- sin premium no se escribe
console.log('Sin premium');
await como('normal');
await q(`update perfiles set portada_letra = 'hola', portada_mascota = 'nyan', portada_cancion = $1::jsonb where id = auth.uid()`, [JSON.stringify(cancion)]);
const n = await portadaDe('normal');
comprobar('quien no dona no guarda nada aunque lo intente a mano', n.portada_letra === null && n.portada_mascota === null && n.portada_cancion === null, JSON.stringify(n));

// ---- una prueba que vence: se conserva pero deja de verse
console.log('Se acaba el premium');
await admin();
await titulo('amiga', 'invitado_caudal', 'Donador de prueba', new Date(Date.now() + 3 * 864e5).toISOString());
await como('amiga');
await q(`update perfiles set portada_letra = 'Mi prueba' where id = auth.uid()`);
comprobar('con una prueba vigente sí guarda', (await portadaDe('amiga')).portada_letra === 'Mi prueba');
await admin();
await titulo('amiga', 'invitado_caudal', 'Donador de prueba', new Date(Date.now() - 864e5).toISOString());
await como('amiga');
await q(`update perfiles set portada_letra = 'Intento sin premium', bio = 'nueva bio' where id = auth.uid()`);
const v = await portadaDe('amiga');
comprobar('vencida la prueba, el intento de cambiar la portada no hace nada', v.portada_letra === 'Mi prueba', v.portada_letra);
comprobar('y el resto del perfil sí se edita', (await uno(`select bio from perfiles where id = auth.uid()`)) === 'nueva bio');
await como('amiga');
comprobar('su propia portada ya no se ve (premium vencido)', (await uno(`select portada_perfil('amiga')`)) === null);
await admin();
await titulo('amiga', 'invitado_caudal', 'Donador de prueba', new Date(Date.now() + 2 * 864e5).toISOString());
await como('amiga');
comprobar('al volver a tener premium, lo guardado reaparece', (await uno(`select portada_perfil('amiga')`))?.letra === 'Mi prueba');

// ---- las demás columnas siguen igual
await como('dona');
comprobar('el perfil de dona conserva su marco y demás (columna nueva no estorba)',
  (await uno(`select marco from perfiles where id = auth.uid()`)) === 'ninguno');
await admin();
comprobar('las funciones internas no se llaman desde fuera',
  (await uno(`select count(*)::int from pg_proc where proname = 'perfil_portada_validar' and has_function_privilege('authenticated', oid, 'execute')`)) === 0);
comprobar('portada_perfil no es de anon',
  (await uno(`select has_function_privilege('anon', 'public.portada_perfil(text)', 'execute')`)) === false);

console.log(`\n${ok} bien, ${mal} mal`);
process.exit(mal ? 1 : 0);
