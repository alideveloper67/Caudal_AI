// Pruebas de supabase/premium.sql (premium vigente, cosméticos, pases de prueba) sobre PGlite.
//
//   node supabase/pruebas/premium.prueba.mjs
//
// Carga esquema.sql + social.sql + listas.sql + listas_perfil.sql + premium.sql y ejecuta el último DOS veces.
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
await db.exec(sql('premium.sql'));
await db.exec(sql('premium.sql')); // repetible

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
const titulo = (u, clave, nombre, vence) => q(
  `insert into titulos_especiales (user_id, titulo, nombre, vence) values ($1, $2, $3, $4)
   on conflict (user_id, titulo) do update set vence = excluded.vence`, [personas[u], clave, nombre, vence]);
const ayer = "now() - interval '1 day'";

console.log('Cargado esquema + social + listas + listas_perfil + premium (x2).');
for (const u of ['ana', 'beto', 'cami', 'dani', 'eva', 'fran', 'gabi', 'hugo']) await nuevaPersona(u);

await admin();
await q(`update perfiles set fecha_nacimiento = date '1990-01-01', perfil_publico = true where id = any($1::uuid[])`,
  [Object.values(personas)]);
// ana y dani son amigas/os de beto (para ver sus datos en mis_amigos)
for (const u of ['ana', 'cami', 'dani']) {
  await q(`insert into amistades (de, para, estado, respondido) values ($1, $2, 'aceptada', now())`, [personas[u], personas.beto]);
}
await titulo('ana', 'donador_caudal', 'Donador de Caudal', null);
await titulo('dani', 'fundador_caudal', 'Fundador de Caudal', null);

console.log('Premium vigente');
await admin();
const esP = async (u) => uno(`select es_premium($1)`, [personas[u]]);
comprobar('un donador permanente es premium', await esP('ana') === true);
comprobar('un fundador es premium', await esP('dani') === true);
comprobar('sin títulos no es premium', await esP('beto') === false);
await titulo('cami', 'invitado_caudal', 'Donador de prueba', `${'2099-01-01'}`);
comprobar('un invitado con fecha futura es premium', await esP('cami') === true);
await q(`update titulos_especiales set vence = now() - interval '1 day' where user_id = $1 and titulo = 'invitado_caudal'`, [personas.cami]);
comprobar('un invitado vencido deja de serlo', await esP('cami') === false);
await q(`update titulos_especiales set vence = null where user_id = $1 and titulo = 'invitado_caudal'`, [personas.cami]);
comprobar('un invitado SIN fecha no cuenta (la prueba siempre vence)', await esP('cami') === false);
await q(`update titulos_especiales set vence = now() - interval '1 day' where user_id = $1 and titulo = 'invitado_caudal'`, [personas.cami]);
await q(`insert into titulos_especiales (user_id, titulo, nombre, vence) values ($1, 'donador_caudal', 'Donador de Caudal', now() - interval '1 day')`, [personas.eva]);
comprobar('un donador con fecha pasada tampoco lo es', await esP('eva') === false);
await q(`delete from titulos_especiales where user_id = $1`, [personas.eva]);

console.log('mi_premium()');
await como('ana');
let mp = await uno(`select mi_premium()`);
comprobar('donador: premium, tipo donador, sin fecha', mp.premium === true && mp.tipo === 'donador' && mp.vence === null, JSON.stringify(mp));
await como('dani');
mp = await uno(`select mi_premium()`);
comprobar('fundador: tipo fundador', mp.premium === true && mp.tipo === 'fundador', JSON.stringify(mp));
await como('beto');
mp = await uno(`select mi_premium()`);
comprobar('sin nada: premium falso y todo nulo', mp.premium === false && mp.tipo === null && mp.vence === null, JSON.stringify(mp));
await como('cami');
mp = await uno(`select mi_premium()`);
comprobar('prueba vencida: no es premium', mp.premium === false && mp.tipo === null, JSON.stringify(mp));
await anonimo();
await falla('anon no puede llamar mi_premium', async () => { await q(`select mi_premium()`); }, /permission denied/i);
await falla('nadie puede llamar es_premium desde la app', async () => { await q(`select es_premium($1)`, [personas.ana]); }, /permission denied/i);

console.log('Fondo y GIF para el pase');
await admin();
await titulo('cami', 'invitado_caudal', 'Donador de prueba', '2099-01-01');
await como('cami');
comprobar('con la prueba vigente puede poner fondo', await uno(`select puede_poner_fondo()`) === true);
await como('beto');
comprobar('sin premium no', await uno(`select puede_poner_fondo()`) === false);
await admin();
await q(`update titulos_especiales set vence = now() - interval '1 day' where user_id = $1 and titulo = 'invitado_caudal'`, [personas.cami]);

console.log('Cosméticos del perfil');
await como('ana');
await q(`update perfiles set marco = 'oro', efecto_nombre = 'brillo', tema_premium = 'sakura' where id = auth.uid()`);
let fila = (await q(`select marco, efecto_nombre, tema_premium from perfiles where id = auth.uid()`))[0];
comprobar('un donador guarda marco, efecto y tema', fila.marco === 'oro' && fila.efecto_nombre === 'brillo' && fila.tema_premium === 'sakura', JSON.stringify(fila));
await como('beto');
await q(`update perfiles set marco = 'aurora', efecto_nombre = 'neon', tema_premium = 'bosque' where id = auth.uid()`);
fila = (await q(`select marco, efecto_nombre, tema_premium from perfiles where id = auth.uid()`))[0];
comprobar('sin premium todo vuelve a «ninguno»', fila.marco === 'ninguno' && fila.efecto_nombre === 'ninguno' && fila.tema_premium === 'ninguno', JSON.stringify(fila));
await como('ana');
await falla('un marco que no existe se rechaza', async () => { await q(`update perfiles set marco = 'rosa_fucsia' where id = auth.uid()`); }, /perfil_cosmeticos|check/i);
await falla('un efecto que no existe se rechaza', async () => { await q(`update perfiles set efecto_nombre = 'humo' where id = auth.uid()`); }, /perfil_cosmeticos|check/i);
await falla('un tema que no existe se rechaza', async () => { await q(`update perfiles set tema_premium = 'verde' where id = auth.uid()`); }, /perfil_cosmeticos|check/i);
for (const m of ['aurora', 'fuego', 'oro', 'neon', 'hielo', 'arcoiris', 'galaxia', 'ninguno']) {
  await q(`update perfiles set marco = $1 where id = auth.uid()`, [m]);
}
comprobar('los 8 marcos son válidos', (await uno(`select marco from perfiles where id = auth.uid()`)) === 'ninguno');
await q(`update perfiles set marco = 'oro' where id = auth.uid()`);

console.log('Lo que ven los demás (RPC ampliadas)');
await como('beto');
let amigos = await q(`select * from mis_amigos()`);
const deAna = amigos.find((x) => x.usuario === 'ana');
comprobar('mis_amigos trae marco y efecto_nombre', deAna && deAna.marco === 'oro' && deAna.efecto_nombre === 'brillo', JSON.stringify(deAna));
comprobar('mis_amigos mantiene sus columnas de siempre', ['id', 'usuario', 'nombre', 'foto_url', 'desde'].every((k) => k in deAna));
const deCami = amigos.find((x) => x.usuario === 'cami');
comprobar('quien no es premium sale en «ninguno»', deCami.marco === 'ninguno' && deCami.efecto_nombre === 'ninguno', JSON.stringify(deCami));
let vp = await uno(`select ver_perfil('ana')`);
comprobar('ver_perfil trae marco y efecto_nombre', vp.marco === 'oro' && vp.efecto_nombre === 'brillo', JSON.stringify([vp.marco, vp.efecto_nombre]));
comprobar('ver_perfil sigue trayendo lo de siempre', vp.usuario === 'ana' && Array.isArray(vp.titulos) && 'fundador_caudal' in vp && 'likes' in vp);
comprobar('el título de donador sale en titulos', vp.titulos.some((t) => t.clave === 'donador_caudal'));
const bp = await q(`select * from buscar_persona('ana')`);
comprobar('buscar_persona trae marco', bp[0].marco === 'oro' && bp[0].efecto_nombre === 'brillo');
const ex = await q(`select * from explorar_perfiles('ana')`);
comprobar('explorar_perfiles trae marco y efecto', ex.length === 1 && ex[0].marco === 'oro' && ex[0].efecto_nombre === 'brillo', JSON.stringify(ex));

// cuando alguien deja de ser premium, los demás dejan de ver su marco aunque la columna siga guardada
await admin();
await q(`update titulos_especiales set vence = now() - interval '1 day' where user_id = $1 and titulo = 'donador_caudal'`, [personas.ana]);
comprobar('la columna sigue guardada', (await uno(`select marco from perfiles where id = $1`, [personas.ana])) === 'oro');
await como('beto');
amigos = await q(`select * from mis_amigos()`);
const deAna2 = amigos.find((x) => x.usuario === 'ana');
comprobar('pero ya no se ve (marco y efecto en «ninguno»)', deAna2.marco === 'ninguno' && deAna2.efecto_nombre === 'ninguno', JSON.stringify(deAna2));
vp = await uno(`select ver_perfil('ana')`);
comprobar('ver_perfil tampoco', vp.marco === 'ninguno' && vp.efecto_nombre === 'ninguno');
comprobar('y el título vencido ya no aparece', !vp.titulos.some((t) => t.clave === 'donador_caudal'), JSON.stringify(vp.titulos));
await admin();
await q(`update titulos_especiales set vence = null where user_id = $1 and titulo = 'donador_caudal'`, [personas.ana]);

// un invitado vigente sí se ve, y su título «Donador de prueba» aparece; vencido, no
await admin();
await q(`update titulos_especiales set vence = now() + interval '3 days' where user_id = $1 and titulo = 'invitado_caudal'`, [personas.cami]);
await como('cami');
await q(`update perfiles set marco = 'neon', efecto_nombre = 'arcoiris' where id = auth.uid()`);
await como('beto');
vp = await uno(`select ver_perfil('cami')`);
comprobar('un invitado vigente muestra su marco y su título de prueba',
  vp.marco === 'neon' && vp.efecto_nombre === 'arcoiris' && vp.titulos.some((t) => t.clave === 'invitado_caudal'), JSON.stringify(vp));
await admin();
await q(`update titulos_especiales set vence = now() - interval '1 minute' where user_id = $1 and titulo = 'invitado_caudal'`, [personas.cami]);
await como('beto');
vp = await uno(`select ver_perfil('cami')`);
comprobar('vencido: sin marco y sin título', vp.marco === 'ninguno' && !vp.titulos.some((t) => t.clave === 'invitado_caudal'), JSON.stringify(vp));
const exv = await q(`select titulos from explorar_perfiles('cami')`);
comprobar('explorar_perfiles tampoco lista el título vencido', !exv[0].titulos.some((t) => t.clave === 'invitado_caudal'));

// solicitudes, enviadas, bloqueados y chats
await admin();
await q(`insert into amistades (de, para, estado) values ($1, $2, 'pendiente')`, [personas.ana, personas.gabi]);
await q(`insert into amistades (de, para, estado) values ($1, $2, 'pendiente')`, [personas.gabi, personas.dani]);
await q(`insert into bloqueos (quien, a) values ($1, $2)`, [personas.gabi, personas.ana]);
await como('gabi');
comprobar('mis_solicitudes trae marco y efecto (de quien manda)', (await q(`select * from mis_solicitudes()`)).every((x) => 'marco' in x && 'efecto_nombre' in x));
const sol = await q(`select * from mis_solicitudes()`);
comprobar('…y la solicitud de un donador sale con su marco', sol.length === 0 || sol[0].marco === 'oro' || sol[0].marco === 'ninguno');
comprobar('mis_enviadas trae marco y efecto', (await q(`select * from mis_enviadas()`)).every((x) => 'marco' in x && 'efecto_nombre' in x));
const bl = await q(`select * from mis_bloqueados()`);
comprobar('mis_bloqueados trae marco y efecto', bl.length === 1 && bl[0].marco === 'oro' && bl[0].efecto_nombre === 'brillo', JSON.stringify(bl));
await admin();
await q(`insert into chats (a, b) values (least($1::uuid, $2::uuid), greatest($1::uuid, $2::uuid))`, [personas.ana, personas.beto]);
await como('beto');
const ch = await q(`select * from mis_chats()`);
comprobar('mis_chats trae marco y efecto y conserva ultimo_lista',
  ch.length === 1 && ch[0].marco === 'oro' && ch[0].efecto_nombre === 'brillo' && 'ultimo_lista' in ch[0], JSON.stringify(ch));

// listas compartidas y públicas
await como('ana');
const lid = (await q(`insert into listas (nombre, publica, en_perfil) values ('Lista de ana', true, true) returning id`))[0].id;
const codigoLista = await uno(`select compartir_lista($1, 'colaborador')`, [lid]);
await como('beto');
const vlp = await uno(`select ver_lista_publica($1)`, [lid]);
comprobar('ver_lista_publica: el dueño trae marco y efecto', vlp.dueno.marco === 'oro' && vlp.dueno.efecto_nombre === 'brillo', JSON.stringify(vlp.dueno));
if (codigoLista) {
  await anonimo();
  const vlc = await uno(`select ver_lista_codigo($1)`, [codigoLista]);
  comprobar('ver_lista_codigo (sin cuenta): el dueño trae marco y efecto', vlc.dueno.marco === 'oro' && vlc.dueno.efecto_nombre === 'brillo', JSON.stringify(vlc.dueno));
  await como('beto');
  await uno(`select unirse_a_lista($1)`, [codigoLista]);
  const ml = await uno(`select miembros_lista($1)`, [lid]);
  comprobar('miembros_lista trae marco y efecto', ml.every((m) => 'marco' in m && 'efecto_nombre' in m) && ml.find((m) => m.usuario === 'ana').marco === 'oro', JSON.stringify(ml));
  const mlc = await uno(`select mis_listas_compartidas()`);
  comprobar('mis_listas_compartidas trae marco y efecto del dueño', mlc[0].dueno.marco === 'oro' && mlc[0].dueno.efecto_nombre === 'brillo', JSON.stringify(mlc));
} else {
  comprobar('se pudo generar un código de lista', false);
}

console.log('Pases de prueba');
await admin();
comprobar('los pases no se pueden crear con un formato raro', await (async () => {
  try { await q(`insert into pases_prueba (codigo) values ('abc')`); return false; } catch { return true; }
})());
await q(`insert into pases_prueba (codigo, dias, usos_max) values ('ABCD-2345', 7, 1), ('MULT-2222', 3, 5),
         ('VIEJ-3333', 7, 1), ('UNO1-4444', 1, 1)`);
await q(`update pases_prueba set caduca = now() - interval '1 day' where codigo = 'VIEJ-3333'`);
const canje = async (u, c) => { await como(u); return uno(`select canjear_pase($1)`, [c]); };

let r = await canje('fran', '  abcd 2345 ');
comprobar('canje feliz (mayúsculas, espacios y sin guion)', r.ok === true && r.dias === 7 && /7 días/.test(r.mensaje), JSON.stringify(r));
comprobar('la fecha de vencimiento es a 7 días', Math.abs((new Date(r.vence) - Date.now()) / 86400000 - 7) < 0.01, r.vence);
await admin();
comprobar('quedó el título invitado_caudal con su fecha', (await q(`select nombre, vence from titulos_especiales where user_id = $1 and titulo = 'invitado_caudal'`, [personas.fran]))[0].nombre === 'Donador de prueba');
comprobar('sumó un uso y quedó anotado', (await uno(`select usos from pases_prueba where codigo = 'ABCD-2345'`)) === 1
  && (await uno(`select count(*)::int from pases_canjeados where user_id = $1`, [personas.fran])) === 1);
comprobar('ahora es premium', await esP('fran') === true);
await como('fran');
mp = await uno(`select mi_premium()`);
comprobar('mi_premium dice «prueba» con su fecha', mp.premium === true && mp.tipo === 'prueba' && mp.vence !== null, JSON.stringify(mp));
comprobar('y puede poner un marco', await (async () => { await q(`update perfiles set marco = 'hielo' where id = auth.uid()`); return (await uno(`select marco from perfiles where id = auth.uid()`)) === 'hielo'; })());

r = await canje('fran', 'MULT-2222');
comprobar('una sola prueba por cuenta de por vida', r.ok === false && /Ya usaste tu prueba/.test(r.mensaje), JSON.stringify(r));
r = await canje('eva', 'ABCD-2345');
comprobar('un código agotado lo dice', r.ok === false && /máximo de veces/.test(r.mensaje), JSON.stringify(r));
r = await canje('eva', 'VIEJ-3333');
comprobar('un código caducado lo dice', r.ok === false && /caducó/.test(r.mensaje), JSON.stringify(r));
r = await canje('eva', 'ZZZZ-9999');
comprobar('un código que no existe lo dice', r.ok === false && /no existe/.test(r.mensaje), JSON.stringify(r));
r = await canje('eva', 'abc');
comprobar('un código mal escrito también', r.ok === false && /no existe/.test(r.mensaje), JSON.stringify(r));
r = await canje('ana', 'MULT-2222');
comprobar('un donador permanente no necesita prueba', r.ok === false && /Ya eres donador/.test(r.mensaje), JSON.stringify(r));
comprobar('y ese código NO se gasta', (await (async () => { await admin(); return uno(`select usos from pases_prueba where codigo = 'MULT-2222'`); })()) === 0);
r = await canje('eva', 'MULT-2222');
comprobar('un código de varios usos sirve a otra cuenta (3 días)', r.ok === true && r.dias === 3 && /3 días/.test(r.mensaje), JSON.stringify(r));
r = await canje('gabi', 'UNO1-4444');
comprobar('1 día se escribe en singular', r.ok === true && /1 día de/.test(r.mensaje), JSON.stringify(r));

await anonimo();
await falla('sin cuenta no se puede canjear', async () => { await q(`select canjear_pase('MULT-2222')`); }, /permission denied/i);
await como('beto');
comprobar('las tablas de pases no devuelven filas a la app (RLS sin políticas)',
  (await q(`select * from pases_prueba`)).length === 0 && (await q(`select * from pases_canjeados`)).length === 0
  && (await q(`select * from pases_intentos`)).length === 0);
await falla('y no se puede escribir en ellas', async () => { await q(`insert into pases_prueba (codigo) values ('HACK-0000')`); }, /row-level security|policy|permission/i);
await falla('ni tocarse el título a mano', async () => { await q(`insert into titulos_especiales (user_id, titulo, nombre) values (auth.uid(), 'donador_caudal', 'Donador de Caudal')`); }, /row-level security|policy|permission/i);

console.log('Intentos limitados');
await admin();
await q(`insert into pases_prueba (codigo, dias) values ('BUEN-7777', 7)`);
for (let i = 0; i < 10; i++) { r = await canje('hugo', `MAL${i}-0000`); comprobar(`intento fallido ${i + 1} contesta «no existe»`, r.ok === false && /no existe/.test(r.mensaje), JSON.stringify(r)); }
r = await canje('hugo', 'BUEN-7777');
comprobar('al 11.º intento queda bloqueado, aunque el código sea bueno', r.ok === false && /demasiados códigos/.test(r.mensaje), JSON.stringify(r));
await admin();
await q(`update pases_intentos set momento = now() - interval '2 hours' where user_id = $1`, [personas.hugo]);
r = await canje('hugo', 'BUEN-7777');
comprobar('pasada la hora vuelve a poder', r.ok === true, JSON.stringify(r));

console.log('Repetibilidad con datos');
await admin();
await db.exec(sql('premium.sql'));
comprobar('al ejecutar de nuevo el archivo no se pierden pases, títulos ni cosméticos',
  (await uno(`select count(*)::int from pases_prueba`)) === 5
  && (await uno(`select count(*)::int from pases_canjeados`)) === 4
  && (await uno(`select marco from perfiles where id = $1`, [personas.ana])) === 'oro');
await como('beto');
comprobar('y las RPC siguen devolviendo lo mismo', (await q(`select * from mis_amigos()`)).find((x) => x.usuario === 'ana').marco === 'oro');

console.log(`\n${ok} comprobaciones pasan, ${mal} fallan.`);
if (mal) { console.log('Fallos: ' + fallos.join(' | ')); process.exit(1); }
