// Pruebas de supabase/listas.sql sobre PGlite (Postgres en WebAssembly, sin servidor ni Docker).
//
//   node supabase/pruebas/listas.prueba.mjs
//
// Usa el PGlite que ya está instalado en agenty-ai (no se instala nada aquí). Otra ruta:
//   PGLITE_RUTA=C:\ruta\a\@electric-sql\pglite node supabase/pruebas/listas.prueba.mjs
//
// El «Supabase falso» (esquemas auth y storage, roles anon y authenticated) vive en arnes.sql.mjs
// de esta misma carpeta. Carga esquema.sql + social.sql + listas.sql y ejecuta listas.sql DOS veces.
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
await db.exec(sql('listas.sql')); // repetible

// ---------------------------------------------------------------- utilidades
let ok = 0, mal = 0;
const fallos = [];
function comprobar(nombre, cond, detalle = '') {
  if (cond) { ok++; } else { mal++; fallos.push(nombre); console.log('  FALLA: ' + nombre + (detalle ? '  -> ' + detalle : '')); }
}
const igual = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const personas = {};
async function nuevaPersona(usuario) {
  const r = await db.query(
    `insert into auth.users (id, email, raw_user_meta_data)
     values (gen_random_uuid(), $1, jsonb_build_object('usuario', $2::text, 'nombre', $2::text))
     returning id`, [usuario + '@prueba.test', usuario]);
  personas[usuario] = r.rows[0].id;
  return r.rows[0].id;
}
let quienSoy = null;                      // para volver a la misma persona tras un error
async function como(usuario) {            // simula a una persona con sesión
  quienSoy = usuario;
  await db.exec('reset role');
  await db.query(`select set_config('request.jwt.claim.sub', $1, false)`, [personas[usuario]]);
  await db.exec('set role authenticated');
}
async function anonimo() {
  quienSoy = '__anon';
  await db.exec('reset role');
  await db.query(`select set_config('request.jwt.claim.sub', '', false)`);
  await db.exec('set role anon');
}
async function admin() { quienSoy = '__admin'; await db.exec('reset role'); }
async function q(texto, params = []) { return (await db.query(texto, params)).rows; }
async function uno(texto, params = []) { const r = await q(texto, params); return Object.values(r[0])[0]; }

async function falla(nombre, fn, patron) {
  try { await fn(); comprobar(nombre, false, 'no falló'); }
  catch (e) {
    const m = String(e.message || e);
    comprobar(nombre, patron ? patron.test(m) : true, 'mensaje: ' + m);
    if (patron && !patron.test(m)) return m;
  }
  await volver();
}
async function volver() {
  if (quienSoy === '__admin') await admin();
  else if (quienSoy === '__anon') await anonimo();
  else await como(quienSoy);
}
async function mensajeDeError(fn) { let m = null; try { await fn(); } catch (e) { m = String(e.message); } await volver(); return m; }

const items = (...claves) => JSON.stringify(claves.map((c) => ({
  clave: c, datos: { titulo: 'Tema ' + c, artistas: [{ nombre: 'Artista ' + c }], portada: 'https://x/' + c + '.jpg' } })));

// ---------------------------------------------------------------- escenario
console.log('Cargado esquema.sql + social.sql + listas.sql (x2).');
for (const u of ['ana', 'beto', 'carla', 'dani', 'eva', 'fer']) await nuevaPersona(u);

// ana tiene dos listas
await como('ana');
const lista = (await q(`insert into listas (nombre, descripcion) values ('Para correr', 'ritmo') returning id`))[0].id;
const lista2 = (await q(`insert into listas (nombre) values ('Privada') returning id`))[0].id;
await q(`insert into lista_items (lista_id, clave, datos, orden) values ($1,'yt:propia1','{"titulo":"Mía","artistas":[{"nombre":"Yo"}],"portada":"https://x/m.jpg"}',1)`, [lista]);

// ---- compartir
console.log('Compartir');
const codigo = await uno(`select compartir_lista($1)`, [lista]);
comprobar('el dueño recibe un código de 8 caracteres del alfabeto', /^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$/.test(codigo), codigo);
comprobar('el código no lleva guion', !codigo.includes('-'));
comprobar('volver a compartir devuelve el mismo código', (await uno(`select compartir_lista($1)`, [lista])) === codigo);
await admin();
comprobar('en la tabla el código queda con rol colaborador', (await uno(`select rol from lista_codigos where lista_id = $1`, [lista])) === 'colaborador');
await como('ana');

// alfabeto y variedad de la generación
await admin();
const muestra = (await q(`select generar_codigo_lista() c from generate_series(1, 400)`)).map((r) => r.c);
comprobar('400 códigos generados: todos de 8 caracteres válidos', muestra.every((c) => /^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$/.test(c)));
comprobar('400 códigos generados: no se repiten', new Set(muestra).size === 400);
const usados = new Set(muestra.join('').split(''));
comprobar('se usan los 31 caracteres del alfabeto', usados.size === 31, 'usados: ' + usados.size);
await como('ana');

await falla('compartir una lista ajena falla', async () => { await como('beto'); await q(`select compartir_lista($1)`, [lista]); }, /no existe o no es tuya/);
await falla('permiso inválido falla', async () => { await como('ana'); await q(`select compartir_lista($1, 'jefe')`, [lista]); }, /colaborador.*oyente/);
await falla('el rol anon no puede compartir', async () => { await anonimo(); await q(`select compartir_lista($1)`, [lista]); }, /permission denied|permiso/i);

// ---- ver_lista_codigo (anon)
console.log('Vista previa por código');
await como('ana');
await q(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7')]);
await anonimo();
const vista = await uno(`select ver_lista_codigo($1)`, [codigo]);
comprobar('anon puede ver la vista previa', vista && vista.nombre === 'Para correr', JSON.stringify(vista));
comprobar('la vista trae descripcion, total y rol', vista.descripcion === 'ritmo' && vista.total === 8 && vista.rol === 'colaborador' && vista.miembros === 0, JSON.stringify(vista));
comprobar('la vista trae como máximo 6 canciones', vista.canciones.length === 6);
comprobar('cada canción trae titulo, artista y miniatura', vista.canciones.every((c) => c.titulo && c.artista && c.miniatura), JSON.stringify(vista.canciones[0]));
comprobar('el dueño sale sin id', igual(Object.keys(vista.dueno).sort(), ['foto_url', 'nombre', 'usuario']), JSON.stringify(vista.dueno));
const planoVista = JSON.stringify(vista);
comprobar('la vista no expone ningún uuid', !/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/.test(planoVista));
comprobar('código inexistente devuelve null', (await uno(`select ver_lista_codigo('ZZZZZZZZ')`)) === null);
comprobar('texto vacío devuelve null', (await uno(`select ver_lista_codigo('')`)) === null);
comprobar('null devuelve null', (await uno(`select ver_lista_codigo(null)`)) === null);
const bonito = codigo.slice(0, 4).toLowerCase() + '-' + codigo.slice(4).toLowerCase();
comprobar('minúsculas y guion funcionan', (await uno(`select ver_lista_codigo($1)`, [bonito]))?.nombre === 'Para correr');
comprobar('espacios alrededor y en medio funcionan', (await uno(`select ver_lista_codigo($1)`, [' ' + codigo.slice(0, 4) + ' ' + codigo.slice(4) + ' ']))?.nombre === 'Para correr');
await falla('anon NO puede unirse', async () => { await q(`select unirse_a_lista($1)`, [codigo]); }, /permission denied|permiso/i);
await falla('anon NO ve pistas_de_lista', async () => { await q(`select pistas_de_lista($1)`, [lista]); }, /permission denied|permiso/i);
await falla('anon NO puede leer lista_codigos directo', async () => { await q(`select * from lista_codigos`); }, /permission denied/i);

// ---- unirse
console.log('Unirse');
await como('beto');
await falla('un código que no existe falla con frase clara', async () => { await q(`select unirse_a_lista('ZZZZZZZZ')`); }, /no existe o la lista ya no se comparte/);
const u1 = await uno(`select unirse_a_lista($1)`, [bonito]);
comprobar('beto se une con código en minúsculas y guion', u1.lista_id === lista && u1.rol === 'colaborador' && u1.es_dueno === false && u1.nombre === 'Para correr', JSON.stringify(u1));
const u2 = await uno(`select unirse_a_lista($1)`, [codigo]);
comprobar('unirse es idempotente (misma respuesta)', igual(u1, u2));
await admin();
comprobar('unirse dos veces deja una sola membresía', (await uno(`select count(*)::int from lista_miembros where lista_id = $1 and user_id = $2`, [lista, personas.beto])) === 1);
await como('ana');
const udueno = await uno(`select unirse_a_lista($1)`, [codigo]);
comprobar('el dueño con su propio código recibe es_dueno true', udueno.es_dueno === true && udueno.lista_id === lista, JSON.stringify(udueno));
await admin();
comprobar('el dueño no crea membresía', (await uno(`select count(*)::int from lista_miembros where user_id = $1`, [personas.ana])) === 0);

// ---- colaborador añade, dueño ve
console.log('Colaborar');
await como('beto');
comprobar('beto añade 2 canciones', (await uno(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('b1', 'b2')])) === 2);
comprobar('repetidas se ignoran (cuenta solo las nuevas)', (await uno(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('b1', 'b3', 'b3', 'a1')])) === 1);
comprobar('una petición vacía devuelve 0', (await uno(`select agregar_a_lista_compartida($1, '[]'::jsonb)`, [lista])) === 0);
await falla('un formato que no es lista falla con frase', async () => { await q(`select agregar_a_lista_compartida($1, '{"a":1}'::jsonb)`, [lista]); }, /formato esperado/);
comprobar('elementos sin clave se ignoran', (await uno(`select agregar_a_lista_compartida($1, '[{"datos":{}},{"clave":""},{"clave":"b4"}]'::jsonb)`, [lista])) === 1);
await como('ana');
const vistas = await q(`select clave, user_id from lista_items where lista_id = $1 order by orden`, [lista]);
comprobar('el dueño ve en lista_items las canciones del colaborador', ['b1', 'b2', 'b3', 'b4'].every((k) => vistas.some((v) => v.clave === k && v.user_id === personas.beto)), JSON.stringify(vistas));
comprobar('user_id es quien la añadió', vistas.find((v) => v.clave === 'a1').user_id === personas.ana && vistas.find((v) => v.clave === 'propia1' || v.clave === 'yt:propia1').user_id === personas.ana);
const orden = (await q(`select clave, orden from lista_items where lista_id = $1 order by orden`, [lista])).map((r) => r.orden);
comprobar('el orden es creciente y sin huecos repetidos', orden.every((o, i) => i === 0 || o > orden[i - 1]));
comprobar('el dueño puede borrar una canción del colaborador en lista_items', (await q(`delete from lista_items where lista_id = $1 and clave = 'b4' returning clave`, [lista])).length === 1);
const act1 = await uno(`select actualizada from listas where id = $1`, [lista]);
await db.exec(`select pg_sleep(0.01)`);
await como('beto');
await q(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('b5')]);
await como('ana');
comprobar('añadir sube listas.actualizada', new Date(await uno(`select actualizada from listas where id = $1`, [lista])) > new Date(act1));

// ---- pistas_de_lista
const pistas = await uno(`select pistas_de_lista($1)`, [lista]);
comprobar('pistas_de_lista trae clave, datos, orden, agregada y agregada_por',
  pistas.length >= 7 && ['clave', 'datos', 'orden', 'agregada', 'agregada_por'].every((k) => k in pistas[0]), JSON.stringify(pistas[0]));
comprobar('agregada_por trae id, usuario y nombre', igual(Object.keys(pistas[0].agregada_por).sort(), ['id', 'nombre', 'usuario']));
comprobar('quien añadió b1 es beto', pistas.find((p) => p.clave === 'b1').agregada_por.usuario === 'beto');
comprobar('pistas ordenadas por orden', pistas.every((p, i) => i === 0 || p.orden >= pistas[i - 1].orden));
await como('beto');
comprobar('un miembro también ve las pistas', (await uno(`select jsonb_array_length(pistas_de_lista($1))::int`, [lista])) >= 7);

// ---- seguridad de las canciones
console.log('Seguridad de lista_items');
await como('carla');
await falla('un no miembro NO ve pistas_de_lista', async () => { await q(`select pistas_de_lista($1)`, [lista]); }, /No tienes acceso/);
await falla('un no miembro NO puede añadir', async () => { await q(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('c1')]); }, /No tienes acceso/);
await falla('un no miembro NO puede quitar', async () => { await q(`select quitar_de_lista_compartida($1, 'a1')`, [lista]); }, /No tienes acceso/);
await falla('un no miembro NO ve los miembros', async () => { await q(`select miembros_lista($1)`, [lista]); }, /No tienes acceso/);
comprobar('un no miembro no lee lista_items de una lista ajena (select directo)', (await q(`select * from lista_items where lista_id = $1`, [lista])).length === 0);
comprobar('un no miembro no ve la lista ajena en listas', (await q(`select * from listas where id = $1`, [lista])).length === 0);
await falla('un no miembro NO puede insertar directo en lista_items ajena', async () => { await q(`insert into lista_items (lista_id, clave) values ($1, 'hack')`, [lista]); }, /row-level security/);
comprobar('un no miembro no puede borrar directo de lista_items ajena', (await q(`delete from lista_items where lista_id = $1 returning clave`, [lista])).length === 0);
await falla('lista_miembros no se lee directo', async () => { await q(`select * from lista_miembros`); }, /permission denied/i);
await falla('lista_codigos no se lee directo', async () => { await q(`select * from lista_codigos`); }, /permission denied/i);
await como('beto');
comprobar('un colaborador tampoco lee lista_items directo (solo por funciones)', (await q(`select * from lista_items where lista_id = $1`, [lista])).length === 0);
await falla('un colaborador no puede insertar directo en lista_items', async () => { await q(`insert into lista_items (lista_id, clave) values ($1, 'hack')`, [lista]); }, /row-level security/);
await como('ana');
comprobar('la lista privada de ana sigue sin compartir y sin código', (await uno(`select count(*)::int from listas where id = $1`, [lista2])) === 1);
await admin();
comprobar('la lista privada no tiene código', (await uno(`select count(*)::int from lista_codigos where lista_id = $1`, [lista2])) === 0);
await como('beto');
await falla('beto no accede a la lista privada de ana', async () => { await q(`select pistas_de_lista($1)`, [lista2]); }, /No tienes acceso/);

// ---- quitar
console.log('Quitar canciones');
await como('beto');
await falla('el colaborador no puede quitar canciones de otros', async () => { await q(`select quitar_de_lista_compartida($1, 'a1')`, [lista]); }, /solo puedes quitar las canciones que añadiste tú/i);
await q(`select quitar_de_lista_compartida($1, 'b2')`, [lista]);
await admin();
comprobar('el colaborador quita la suya', (await uno(`select count(*)::int from lista_items where lista_id = $1 and clave = 'b2'`, [lista])) === 0);
await como('beto');
await q(`select quitar_de_lista_compartida($1, 'b2')`, [lista]);
comprobar('quitar una canción que ya no está no da error', true);
await como('ana');
await q(`select quitar_de_lista_compartida($1, 'b3')`, [lista]);
await admin();
comprobar('el dueño quita la de un colaborador', (await uno(`select count(*)::int from lista_items where lista_id = $1 and clave = 'b3'`, [lista])) === 0);
await como('ana');
await q(`select quitar_de_lista_compartida($1, 'a2')`, [lista]);
await admin();
comprobar('el dueño quita la suya', (await uno(`select count(*)::int from lista_items where lista_id = $1 and clave = 'a2'`, [lista])) === 0);

// ---- permiso oyente
console.log('Permisos');
await como('ana');
comprobar('cambiar el permiso devuelve el mismo código', (await uno(`select compartir_lista($1, 'oyente')`, [lista])) === codigo);
await admin();
comprobar('el código queda como oyente', (await uno(`select rol from lista_codigos where lista_id = $1`, [lista])) === 'oyente');
comprobar('quien ya estaba dentro pasa también a oyente', (await uno(`select rol from lista_miembros where lista_id = $1 and user_id = $2`, [lista, personas.beto])) === 'oyente');
await como('beto');
await falla('un oyente NO puede añadir', async () => { await q(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('o1')]); }, /solo puedes escuchar/);
await falla('un oyente NO puede quitar', async () => { await q(`select quitar_de_lista_compartida($1, 'b1')`, [lista]); }, /solo puedes escuchar/);
comprobar('un oyente sí ve las pistas', (await uno(`select jsonb_array_length(pistas_de_lista($1))::int`, [lista])) >= 3);
await como('carla');
const uc = await uno(`select unirse_a_lista($1)`, [codigo]);
comprobar('quien se une con un código de oyente entra como oyente', uc.rol === 'oyente');
await falla('carla (oyente) NO puede añadir', async () => { await q(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('c1')]); }, /solo puedes escuchar/);
await como('ana');
await q(`select compartir_lista($1, 'colaborador')`, [lista]);
await como('carla');
comprobar('al volver a colaborador, carla ya puede añadir', (await uno(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('c1')])) === 1);

// ---- miembros, salir, quitar
console.log('Miembros');
await como('ana');
const mem = await uno(`select miembros_lista($1)`, [lista]);
comprobar('miembros_lista: dueño primero y 2 miembros', mem.length === 3 && mem[0].es_dueno === true && mem[0].usuario === 'ana', JSON.stringify(mem));
comprobar('miembros_lista trae id, usuario, nombre, foto_url, rol, desde, es_dueno', ['id', 'usuario', 'nombre', 'foto_url', 'rol', 'desde', 'es_dueno'].every((k) => k in mem[1]));
await como('beto');
comprobar('un miembro también ve los miembros', (await uno(`select jsonb_array_length(miembros_lista($1))::int`, [lista])) === 3);
const comp = await uno(`select mis_listas_compartidas()`);
comprobar('mis_listas_compartidas trae la de ana', comp.length === 1 && comp[0].id === lista && comp[0].dueno.usuario === 'ana' && comp[0].rol === 'colaborador' && comp[0].total >= 3, JSON.stringify(comp));
comprobar('mis_listas_compartidas trae nombre, descripcion, actualizada y dueno.id', ['nombre', 'descripcion', 'actualizada'].every((k) => k in comp[0]) && comp[0].dueno.id === personas.ana);
await como('ana');
comprobar('el dueño no ve sus propias listas en mis_listas_compartidas', (await uno(`select jsonb_array_length(mis_listas_compartidas())::int`)) === 0);
await como('dani');
comprobar('quien no es miembro tiene mis_listas_compartidas vacía', (await uno(`select jsonb_array_length(mis_listas_compartidas())::int`)) === 0);
await como('beto');
await falla('un miembro no puede quitar a otro', async () => { await q(`select quitar_miembro($1, $2)`, [lista, personas.carla]); }, /Solo el dueño/);
await q(`select salir_de_lista($1)`, [lista]);
await falla('salir dos veces falla con frase clara', async () => { await q(`select salir_de_lista($1)`, [lista]); }, /No estás en esa lista/);
await falla('tras salir ya no ve las pistas', async () => { await q(`select pistas_de_lista($1)`, [lista]); }, /No tienes acceso/);
await falla('tras salir ya no puede añadir', async () => { await q(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('b9')]); }, /No tienes acceso/);
await admin();
comprobar('las canciones de quien salió se quedan en la lista', (await uno(`select count(*)::int from lista_items where lista_id = $1 and user_id = $2`, [lista, personas.beto])) >= 1);
await como('ana');
await q(`select quitar_miembro($1, $2)`, [lista, personas.carla]);
await falla('quitar a quien no está falla con frase clara', async () => { await q(`select quitar_miembro($1, $2)`, [lista, personas.carla]); }, /no está en la lista/);
await como('carla');
await falla('el expulsado pierde el acceso', async () => { await q(`select pistas_de_lista($1)`, [lista]); }, /No tienes acceso/);
comprobar('quien fue expulsado puede volver a unirse mientras el código siga activo', (await uno(`select unirse_a_lista($1)`, [codigo])).lista_id === lista);

// ---- bloqueo
console.log('Bloqueos');
await como('ana');
await q(`select bloquear($1)`, [personas.dani]);
await como('dani');
await falla('el bloqueo impide unirse (el dueño bloqueó)', async () => { await q(`select unirse_a_lista($1)`, [codigo]); }, /No te puedes unir/);
await como('eva');
await q(`select unirse_a_lista($1)`, [codigo]);
await q(`select bloquear($1)`, [personas.ana]);   // eva bloquea a ana estando dentro
await falla('el bloqueo corta el acceso de un miembro ya dentro', async () => { await q(`select pistas_de_lista($1)`, [lista]); }, /No tienes acceso/);
comprobar('y desaparece de mis_listas_compartidas', (await uno(`select jsonb_array_length(mis_listas_compartidas())::int`)) === 0);
await falla('y no puede añadir', async () => { await q(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('e1')]); }, /No tienes acceso/);
await q(`select desbloquear($1)`, [personas.ana]);
comprobar('al desbloquear recupera el acceso', (await uno(`select jsonb_array_length(pistas_de_lista($1))::int`, [lista])) >= 1);
await como('ana');
await q(`select desbloquear($1)`, [personas.dani]);
await como('dani');
comprobar('sin bloqueo dani se une', (await uno(`select unirse_a_lista($1)`, [codigo])).rol === 'colaborador');
await como('dani');
await q(`select salir_de_lista($1)`, [lista]);
await como('eva');
await q(`select salir_de_lista($1)`, [lista]);
await como('carla');
await q(`select salir_de_lista($1)`, [lista]);

// ---- tope de miembros
console.log('Topes');
await admin();
const extra = [];
for (let i = 1; i <= 21; i++) extra.push(await nuevaPersona('m' + i));
await como('m1');
await q(`select unirse_a_lista($1)`, [codigo]);
for (let i = 2; i <= 20; i++) { await como('m' + i); await q(`select unirse_a_lista($1)`, [codigo]); }
await admin();
comprobar('20 miembros caben', (await uno(`select count(*)::int from lista_miembros where lista_id = $1`, [lista])) === 20);
await como('m21');
await falla('el miembro 21 no entra', async () => { await q(`select unirse_a_lista($1)`, [codigo]); }, /20 personas/);
await como('m5');
comprobar('un miembro ya dentro puede volver a pulsar unirse con la lista llena', (await uno(`select unirse_a_lista($1)`, [codigo])).lista_id === lista);
await como('ana');
await q(`select quitar_miembro($1, $2)`, [lista, personas.m1]);
await como('m21');
comprobar('al hacer lugar entra el miembro 21', (await uno(`select unirse_a_lista($1)`, [codigo])).lista_id === lista);

// ---- tope de canciones
await como('ana');
const gran = (await q(`insert into listas (nombre) values ('Enorme') returning id`))[0].id;
const cgran = await uno(`select compartir_lista($1)`, [gran]);
const mil = JSON.stringify(Array.from({ length: 1000 }, (_, i) => ({ clave: 'x' + i, datos: { titulo: 't' + i } })));
comprobar('primer lote de 1000 entra', (await uno(`select agregar_a_lista_compartida($1, $2::jsonb)`, [gran, mil])) === 1000);
const mil2 = JSON.stringify(Array.from({ length: 1000 }, (_, i) => ({ clave: 'y' + i, datos: {} })));
comprobar('segundo lote de 1000 entra (2000 en total)', (await uno(`select agregar_a_lista_compartida($1, $2::jsonb)`, [gran, mil2])) === 1000);
const msgTope = await mensajeDeError(() => q(`select agregar_a_lista_compartida($1, $2::jsonb)`, [gran, items('z1')]));
comprobar('la canción 2001 no entra, con frase clara', msgTope && /2000 canciones/.test(msgTope), String(msgTope));
await admin();
comprobar('sigue habiendo 2000', (await uno(`select count(*)::int from lista_items where lista_id = $1`, [gran])) === 2000);
await como('ana');
comprobar('con la lista llena, repetir canciones existentes devuelve 0 sin error', (await uno(`select agregar_a_lista_compartida($1, $2::jsonb)`, [gran, items('x1')])) === 0);
await q(`select dejar_de_compartir_lista($1)`, [gran]);
void cgran;

// ---- dejar de compartir
console.log('Dejar de compartir');
await como('ana');
await q(`select dejar_de_compartir_lista($1)`, [lista]);
await admin();
comprobar('se borra el código', (await uno(`select count(*)::int from lista_codigos where lista_id = $1`, [lista])) === 0);
comprobar('se borran los miembros', (await uno(`select count(*)::int from lista_miembros where lista_id = $1`, [lista])) === 0);
comprobar('la lista y sus canciones siguen siendo de ana', (await uno(`select count(*)::int from lista_items where lista_id = $1`, [lista])) >= 3);
await anonimo();
comprobar('el código viejo devuelve null en la vista previa', (await uno(`select ver_lista_codigo($1)`, [codigo])) === null);
await como('m5');
await falla('el código viejo ya no sirve para unirse', async () => { await q(`select unirse_a_lista($1)`, [codigo]); }, /no existe o la lista ya no se comparte/);
await falla('quien estaba dentro ya no ve las pistas', async () => { await q(`select pistas_de_lista($1)`, [lista]); }, /No tienes acceso/);
await como('beto');
await falla('un no dueño no puede dejar de compartir', async () => { await q(`select dejar_de_compartir_lista($1)`, [lista]); }, /no existe o no es tuya/);
await como('ana');
const codigo2 = await uno(`select compartir_lista($1)`, [lista]);
comprobar('al compartir otra vez sale un código nuevo y distinto', /^[A-Z2-9]{8}$/.test(codigo2) && codigo2 !== codigo);

// ---- chat con listas
console.log('Chat');
await admin();
await q(`insert into amistades (de, para, estado, respondido) values ($1, $2, 'aceptada', now())`, [personas.ana, personas.beto]);
await como('ana');
const chat = await uno(`select abrir_chat($1)`, [personas.beto]);
const tarjeta = JSON.stringify({ codigo: codigo2, nombre: 'Para correr', canciones: 4, rol: 'colaborador', portada: 'https://x/p.jpg' });
await q(`insert into mensajes (chat, lista) values ($1, $2::jsonb)`, [chat, tarjeta]);
comprobar('un mensaje solo con lista es válido', true);
await q(`insert into mensajes (chat, texto, lista) values ($1, 'mira', $2::jsonb)`, [chat, tarjeta]);
comprobar('un mensaje con texto y lista es válido', true);
await falla('un mensaje vacío sigue siendo inválido', async () => { await q(`insert into mensajes (chat) values ($1)`, [chat]); }, /mensajes_contenido|check/);
await falla('una lista que no es objeto es inválida', async () => { await q(`insert into mensajes (chat, lista) values ($1, '[1,2]'::jsonb)`, [chat]); }, /mensajes_contenido|check/);
await falla('una lista sin codigo es inválida', async () => { await q(`insert into mensajes (chat, lista) values ($1, '{"nombre":"x"}'::jsonb)`, [chat]); }, /mensajes_contenido|check/);
await q(`insert into mensajes (chat, pista) values ($1, '{"titulo":"x"}'::jsonb)`, [chat]);
comprobar('los mensajes con pista siguen siendo válidos', true);
await q(`insert into mensajes (chat, texto) values ($1, 'hola')`, [chat]);
comprobar('los mensajes con texto siguen siendo válidos', true);
await q(`insert into mensajes (chat, lista) values ($1, $2::jsonb)`, [chat, tarjeta]);
const ch = (await q(`select * from mis_chats()`))[0];
comprobar('mis_chats trae ultimo_lista', ch && ch.ultimo_lista && ch.ultimo_lista.codigo === codigo2 && ch.ultimo_lista.canciones === 4, JSON.stringify(ch));
comprobar('mis_chats conserva foto_url y las columnas de antes', ['id', 'otro', 'usuario', 'nombre', 'ultimo', 'ultimo_texto', 'ultimo_pista', 'ultimo_autor', 'sin_leer', 'foto_url', 'ultimo_lista'].every((k) => k in ch));
await como('beto');
const chb = (await q(`select * from mis_chats()`))[0];
comprobar('el otro lado también ve ultimo_lista y 5 sin leer', chb.ultimo_lista?.codigo === codigo2 && chb.sin_leer === 5, JSON.stringify(chb));
await q(`insert into mensajes (chat, texto) values ($1, 'gracias')`, [chat]);
comprobar('si el último mensaje es de texto, ultimo_lista es null', (await q(`select * from mis_chats()`))[0].ultimo_lista === null);
// la tarjeta sirve para unirse
const uc2 = await uno(`select unirse_a_lista($1)`, [codigo2]);
comprobar('el código de la tarjeta sirve para unirse sin ser amigos de nadie más', uc2.lista_id === lista);
await como('carla');
comprobar('carla (sin amistad con ana) puede unirse con el código', (await uno(`select unirse_a_lista($1)`, [codigo2])).es_dueno === false);
await falla('carla no puede escribir a ana: no son amigas (regla de social.sql intacta)', async () => { await q(`insert into mensajes (chat, lista) values ($1, $2::jsonb)`, [chat, tarjeta]); }, /row-level security/);

// ---- eliminar cuenta
console.log('Eliminar cuenta');
await como('carla');
await q(`select agregar_a_lista_compartida($1, $2::jsonb)`, [lista, items('c7', 'c8')]);
await como('ana');
const lista3 = (await q(`insert into listas (nombre) values ('Se va con ana') returning id`))[0].id;
const cod3 = await uno(`select compartir_lista($1)`, [lista3]);
await como('carla');
await q(`select unirse_a_lista($1)`, [cod3]);
await como('carla');
await q(`select eliminar_mi_cuenta()`);
await admin();
comprobar('eliminar la cuenta de una colaboradora funciona', (await uno(`select count(*)::int from auth.users where id = $1`, [personas.carla])) === 0);
comprobar('sus membresías desaparecen', (await uno(`select count(*)::int from lista_miembros where user_id = $1`, [personas.carla])) === 0);
comprobar('sus canciones salen de las listas ajenas', (await uno(`select count(*)::int from lista_items where user_id = $1`, [personas.carla])) === 0);
comprobar('la lista de ana sigue ahí', (await uno(`select count(*)::int from listas where id = $1`, [lista])) === 1);
await como('ana');
await q(`select eliminar_mi_cuenta()`);
await admin();
comprobar('eliminar la cuenta del dueño borra sus listas, códigos y canciones',
  (await uno(`select count(*)::int from listas where user_id = $1`, [personas.ana])) === 0
  && (await uno(`select count(*)::int from lista_codigos where lista_id in ($1, $2, $3)`, [lista, lista2, lista3])) === 0
  && (await uno(`select count(*)::int from lista_items where lista_id in ($1, $2, $3)`, [lista, lista2, lista3])) === 0);
comprobar('y los miembros de esas listas ya no las ven', (await uno(`select count(*)::int from lista_miembros where lista_id in ($1, $2, $3)`, [lista, lista2, lista3])) === 0);
comprobar('los mensajes de ana también se fueron (comportamiento de antes)', (await uno(`select count(*)::int from mensajes where autor = $1`, [personas.ana])) === 0);
await como('beto');
comprobar('y beto sigue teniendo su cuenta y mis_listas_compartidas vacía', (await uno(`select jsonb_array_length(mis_listas_compartidas())::int`)) === 0);

// ---- repetibilidad
console.log('Repetibilidad');
await admin();
await db.exec(sql('listas.sql'));
comprobar('listas.sql se puede ejecutar una tercera vez sin error con datos ya cargados', true);
comprobar('las 11 funciones del contrato existen',
  (await uno(`select count(*)::int from pg_proc p join pg_namespace n on n.oid = p.pronamespace
              where n.nspname = 'public' and p.proname in ('compartir_lista','dejar_de_compartir_lista','ver_lista_codigo','unirse_a_lista','salir_de_lista','quitar_miembro','miembros_lista','mis_listas_compartidas','pistas_de_lista','agregar_a_lista_compartida','quitar_de_lista_compartida','mis_chats')`)) === 12);
comprobar('las funciones internas no son ejecutables por authenticated ni anon',
  (await uno(`select count(*)::int from pg_proc p where p.proname in ('normalizar_codigo','generar_codigo_lista','acceso_lista','candidatas_lista') and pronamespace = 'public'::regnamespace
               and (has_function_privilege('anon', p.oid, 'execute') or has_function_privilege('authenticated', p.oid, 'execute'))`)) === 0);
comprobar('solo ver_lista_codigo es ejecutable por anon entre las funciones nuevas',
  (await q(`select proname from pg_proc where pronamespace = 'public'::regnamespace and has_function_privilege('anon', oid, 'execute')
              and proname in ('compartir_lista','dejar_de_compartir_lista','ver_lista_codigo','unirse_a_lista','salir_de_lista','quitar_miembro','miembros_lista','mis_listas_compartidas','pistas_de_lista','agregar_a_lista_compartida','quitar_de_lista_compartida','mis_chats')`))
    .map((r) => r.proname).join() === 'ver_lista_codigo');

console.log(`\n${ok} comprobaciones pasan, ${mal} fallan.`);
if (mal) { console.log('Fallos: ' + fallos.join(' | ')); process.exit(1); }
