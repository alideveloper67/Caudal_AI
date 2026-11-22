// Pruebas de supabase/grupos.sql y perfil_publico_defecto.sql sobre PGlite (Postgres sin servidor).
//
//   node supabase/pruebas/grupos.prueba.mjs
//
// Carga esquema.sql + social.sql + grupos.sql + perfil_publico_defecto.sql (los dos últimos dos veces:
// deben poder repetirse) y prueba crear, buscar, entrar (abierto y con código), escribir texto,
// canciones y notas de voz, que no haya imágenes ni videos, freno de spam, reportes, bloqueos,
// moderación, expulsión, salir y heredar, menores y perfiles públicos por defecto.
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import { createRequire } from 'node:module';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const sql = (n) => readFileSync(path.join(aqui, '..', n), 'utf8');
const ruta = process.env.PGLITE_RUTA || 'C:\\Users\\USER\\agenty-ai\\node_modules\\@electric-sql\\pglite';
const require = createRequire(import.meta.url);
const { PGlite } = await import(pathToFileURL(require.resolve(ruta)).href);
const { SUPABASE_FALSO } = await import('./arnes.sql.mjs');

process.on('unhandledRejection', (e) => { console.log('ERROR: ' + (e && e.message || e)); process.exit(2); });
const db = new PGlite();
await db.exec(SUPABASE_FALSO);
await db.exec(`
create schema realtime;
create table realtime.enviados (n serial, payload jsonb, evento text, tema text, privado boolean);
create function realtime.send(payload jsonb, event text, topic text, private boolean default true)
returns void language sql as $$ insert into realtime.enviados (payload, evento, tema, privado) values ($1, $2, $3, $4) $$;
grant usage on schema realtime to anon, authenticated;
-- como en Supabase: el almacén lo pueden tocar las cuentas; lo que limita son las políticas
grant select, insert, update, delete on storage.objects to authenticated;
`);
await db.exec(sql('esquema.sql'));
await db.exec(sql('social.sql'));
await db.exec(sql('grupos.sql'));
await db.exec(sql('grupos.sql')); // repetible
// cuentas que existían ANTES de los perfiles públicos por defecto
const personas = {};
async function nuevaPersona(usuario, nacimiento = '1995-05-05') {
  const r = await db.query(
    `insert into auth.users (id, email, raw_user_meta_data)
     values (gen_random_uuid(), $1, jsonb_build_object('usuario', $2::text, 'nombre', $2::text)) returning id`,
    [usuario + '@prueba.test', usuario]);
  personas[usuario] = r.rows[0].id;
  if (nacimiento) await db.query(`update perfiles set fecha_nacimiento = $2::date where id = $1`, [personas[usuario], nacimiento]);
}
await nuevaPersona('vieja');
await db.exec(sql('perfil_publico_defecto.sql'));
await db.exec(sql('perfil_publico_defecto.sql')); // repetible

let ok = 0, mal = 0;
function comprobar(nombre, cond, detalle = '') {
  if (cond) ok++; else { mal++; console.log('  FALLA: ' + nombre + (detalle ? '  -> ' + detalle : '')); }
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
async function volver() { if (quienSoy === '__admin') await admin(); else if (quienSoy === '__anon') await anonimo(); else await como(quienSoy); }
async function q(t, p = []) { return (await db.query(t, p)).rows; }
async function rpc(nombre, args = {}) {
  const claves = Object.keys(args);
  const r = await db.query(`select public.${nombre}(${claves.map((k, i) => `${k} => $${i + 1}`).join(', ')}) as r`,
    claves.map((k) => (args[k] !== null && typeof args[k] === 'object' ? JSON.stringify(args[k]) : args[k])));
  return r.rows.length === 1 ? r.rows[0].r : r.rows.map((x) => x.r);
}
async function lista(nombre, args = {}) {
  const claves = Object.keys(args);
  const r = await db.query(`select * from public.${nombre}(${claves.map((k, i) => `${k} => $${i + 1}`).join(', ')}) as r`,
    claves.map((k) => (args[k] !== null && typeof args[k] === 'object' ? JSON.stringify(args[k]) : args[k])));
  return r.rows.map((x) => x.r);
}
async function falla(nombre, fn, patron) {
  try { await fn(); comprobar(nombre, false, 'no falló'); }
  catch (e) { comprobar(nombre, patron ? patron.test(String(e.message)) : true, String(e.message)); }
  await volver();
}

for (const u of ['ana', 'beto', 'carla', 'dani', 'eva']) await nuevaPersona(u);
await nuevaPersona('nina', '2012-03-03');           // menor de edad

// ================================================================ perfiles públicos por defecto
await admin();
const pub = async (u) => (await q(`select perfil_publico from perfiles where id = $1`, [personas[u]]))[0].perfil_publico;
comprobar('cuenta nueva y mayor: perfil público sola', await pub('ana') === true);
comprobar('cuenta que ya existía: no se toca', await pub('vieja') === false);
comprobar('menor: nunca público', await pub('nina') === false);
await como('ana');
await q(`update perfiles set perfil_publico = false where id = auth.uid()`);
comprobar('la persona lo cierra: queda privado', await (async () => { await admin(); return pub('ana'); })() === false);
await como('ana');
await q(`update perfiles set bio = 'hola' where id = auth.uid()`);
await admin();
comprobar('y no se vuelve a abrir solo al editar otra cosa', await pub('ana') === false);
await como('nina');
await q(`update perfiles set perfil_publico = true where id = auth.uid()`);
await admin();
comprobar('un menor no puede abrirlo ni a mano', await pub('nina') === false);
await nuevaPersona('fede', null);
comprobar('sin fecha de nacimiento: privado hasta saberla', await pub('fede') === false);
await q(`update perfiles set fecha_nacimiento = '1990-01-01' where id = $1`, [personas.fede]);
comprobar('al poner una fecha de mayor: público', await pub('fede') === true);
await como('vieja');
await q(`update perfiles set publico_elegido = false where id = auth.uid()`);
await q(`update perfiles set bio = 'x' where id = auth.uid()`);
await admin();
comprobar('desde la app no se puede des-elegir para abrirlo', await pub('vieja') === false);

// ================================================================ grupos
await anonimo();
await falla('sin cuenta no se crea', () => rpc('grupo_crear', { p_nombre: 'Reggaetón' }), /permission denied|entra con tu cuenta/);
await falla('sin cuenta no se lee la tabla', () => q('select * from public.grupos'), /permission denied/);

await como('ana');
const g = await rpc('grupo_crear', { p_nombre: '  Reggaetón Lima  ', p_descripcion: 'Para hablar de perreo', p_tipo: 'abierto' });
comprobar('creado abierto, ana dueña', g.nombre === 'Reggaetón Lima' && g.tipo === 'abierto' && g.rol === 'dueno' && g.miembros === 1, JSON.stringify(g));
comprobar('un abierto no tiene código', g.codigo === null);
const p = await rpc('grupo_crear', { p_nombre: 'Primos', p_tipo: 'privado' });
comprobar('privado con código de 8', /^[A-Z2-9]{8}$/.test(p.codigo), p.codigo);
await falla('nombre corto', () => rpc('grupo_crear', { p_nombre: 'ab' }), /al menos 3 letras/);
await falla('tipo raro', () => rpc('grupo_crear', { p_nombre: 'Algo', p_tipo: 'secreto' }), /abierto o privado/);
await rpc('grupo_crear', { p_nombre: 'Tercero' });
await falla('3 grupos al día como mucho', () => rpc('grupo_crear', { p_nombre: 'Cuarto' }), /3 grupos hoy/);
await falla('nadie lee las tablas directo', () => q('select * from public.grupo_mensajes'), /permission denied/);
await falla('nadie escribe directo', () => q(`insert into public.grupo_miembros (grupo, user_id) values ($1, auth.uid())`, [p.id]), /permission denied/);

await como('beto');
let ex = await lista('grupos_explorar', { p_busqueda: 'regga' });
comprobar('explorar encuentra el abierto', ex.length === 1 && ex[0].id === g.id);
comprobar('explorar no enseña privados', !(await lista('grupos_explorar')).some((x) => x.id === p.id));
comprobar('un privado no se ve sin estar dentro', (await rpc('grupo_ver', { p_grupo: p.id })) === null);
await falla('a un privado no se entra sin código', () => rpc('grupo_unirse', { p_grupo: p.id }), /privado/);
let v = await rpc('grupo_unirse', { p_grupo: g.id });
comprobar('beto entra al abierto', v.rol === 'miembro' && v.miembros === 2);
v = await rpc('grupo_unirse_codigo', { p_codigo: p.codigo.slice(0, 4).toLowerCase() + '-' + p.codigo.slice(4) });
comprobar('entra al privado con el código (minúsculas y guion)', v.id === p.id && v.codigo === p.codigo);
await falla('código que no existe', () => rpc('grupo_unirse_codigo', { p_codigo: 'ZZZZZZZZ' }), /ningún grupo/);
await como('carla'); await rpc('grupo_unirse', { p_grupo: g.id });
await como('nina'); v = await rpc('grupo_unirse', { p_grupo: g.id });
comprobar('un menor puede entrar', v.rol === 'miembro');

// ---------------------------------------------------------------- mensajes
await como('beto');
let m1 = await rpc('grupo_enviar', { p_grupo: g.id, p_texto: '  Hola a todos\nqué tal  ' });
comprobar('texto con salto de línea', m1.texto === 'Hola a todos\nqué tal' && m1.mio === true && m1.autor.usuario === 'beto', JSON.stringify(m1));
let m2 = await rpc('grupo_enviar', { p_grupo: g.id, p_pista: { video_id: 'kJQP7kiw5Fk', titulo: 'Despacito', artista: 'Luis Fonsi', miniatura: 'https://i.ytimg.com/vi/kJQP7kiw5Fk/hq.jpg', duracion: '282', extra: 'x' } });
comprobar('canción compartida limpia', m2.pista.video_id === 'kJQP7kiw5Fk' && m2.pista.duracion === 282 && !('extra' in m2.pista));
let m3 = await rpc('grupo_enviar', { p_grupo: g.id, p_pista: { video_id: 'abcdefghijk', titulo: 'x', miniatura: 'https://malo.com/foto.jpg' } });
comprobar('NO se cuela una imagen cualquiera como carátula', m3.pista.miniatura === '');
await falla('canción con id raro', () => rpc('grupo_enviar', { p_grupo: g.id, p_pista: { video_id: '<script>' } }), /no se puede compartir/);
await falla('mensaje vacío', () => rpc('grupo_enviar', { p_grupo: g.id, p_texto: '   ' }), /vacío/);
await falla('no hay campo para imágenes', () => rpc('grupo_enviar', { p_grupo: g.id, p_imagen: 'x.jpg' }), /function|does not exist/);
comprobar('el aviso de Realtime solo lleva el número', await (async () => {
  await admin(); const r = await q(`select * from realtime.enviados where tema = $1 order by n desc limit 1`, ['grupo-' + g.id]);
  await como('beto'); return r.length && r[0].evento === 'nuevo' && Object.keys(r[0].payload).join() === 'id' && r[0].privado === false;
})());

// notas de voz: el almacén solo acepta audio, en la carpeta de su grupo y su persona
await admin();
const bucket = (await q(`select * from storage.buckets where id = 'audios-grupos'`))[0];
comprobar('almacén privado, solo audio, hasta 3 MB', bucket.public === false && bucket.file_size_limit == 3145728
  && bucket.allowed_mime_types.every((t) => t.startsWith('audio/')), JSON.stringify(bucket));
await como('beto');
const rutaAudio = `${g.id}/${personas.beto}/nota1.m4a`;
await q(`insert into storage.objects (bucket_id, name) values ('audios-grupos', $1)`, [rutaAudio]);
await falla('no sube en la carpeta de otra persona', () => q(`insert into storage.objects (bucket_id, name) values ('audios-grupos', $1)`, [`${g.id}/${personas.ana}/x.m4a`]), /row-level security|policy/);
await falla('no sube a un grupo donde no está', () => q(`insert into storage.objects (bucket_id, name) values ('audios-grupos', $1)`, [`00000000-0000-4000-8000-000000000000/${personas.beto}/x.m4a`]), /row-level security|policy/);
let m4 = await rpc('grupo_enviar', { p_grupo: g.id, p_audio: rutaAudio, p_audio_seg: 12 });
comprobar('nota de voz enviada', m4.audio === rutaAudio && m4.audio_seg === 12);
await falla('nota de voz que no se subió', () => rpc('grupo_enviar', { p_grupo: g.id, p_audio: `${g.id}/${personas.beto}/no.m4a`, p_audio_seg: 3 }), /no llegó/);
await falla('nota de voz de más de 3 minutos', () => rpc('grupo_enviar', { p_grupo: g.id, p_audio: rutaAudio, p_audio_seg: 400 }), /3 minutos/);
await como('carla');
comprobar('otro miembro puede oír la nota', (await q(`select name from storage.objects where bucket_id = 'audios-grupos'`)).length === 1);
await como('eva');
comprobar('quien no está no la oye', (await q(`select name from storage.objects where bucket_id = 'audios-grupos'`)).length === 0);
await falla('quien no está no lee mensajes', () => lista('grupo_mensajes', { p_grupo: g.id }), /no estás en este grupo/);
await falla('quien no está no escribe', () => rpc('grupo_enviar', { p_grupo: g.id, p_texto: 'hola' }), /no estás en este grupo/);

await como('carla');
let ms = await lista('grupo_mensajes', { p_grupo: g.id });
comprobar('carla ve los 4 mensajes, el más nuevo primero', ms.length === 4 && ms[0].id === m4.id && ms[3].id === m1.id);
comprobar('desde: solo los nuevos', (await lista('grupo_mensajes_desde', { p_grupo: g.id, p_desde: m2.id })).map((x) => x.id).join() === [m3.id, m4.id].join());
comprobar('paginar hacia atrás', (await lista('grupo_mensajes', { p_grupo: g.id, p_antes: m3.id, p_limite: 1 }))[0].id === m2.id);
let mios = (await lista('mis_grupos'));
comprobar('mis grupos con sin leer', mios.length === 1 && mios[0].sin_leer === 4 && mios[0].ultimo_mensaje.audio === true, JSON.stringify(mios[0] && mios[0].sin_leer));
await rpc('grupo_leido', { p_grupo: g.id });
comprobar('leído pone a cero', (await lista('mis_grupos'))[0].sin_leer === 0);

// freno de spam
for (let i = 0; i < 8; i++) await rpc('grupo_enviar', { p_grupo: g.id, p_texto: 'spam ' + i });
await falla('9.º mensaje en 20 s se frena', () => rpc('grupo_enviar', { p_grupo: g.id, p_texto: 'otro' }), /muy rápido/);
await admin();
await q(`update grupo_mensajes set creado = creado - interval '1 minute' where autor = $1`, [personas.carla]);

// bloqueos: quien bloquea deja de ver al otro
await como('dani'); await rpc('grupo_unirse', { p_grupo: g.id });
const md = await rpc('grupo_enviar', { p_grupo: g.id, p_texto: 'soy dani' });
await como('carla'); await rpc('bloquear', { p_otro: personas.dani });
comprobar('carla no ve a quien bloqueó', !(await lista('grupo_mensajes', { p_grupo: g.id })).some((x) => x.id === md.id));
await como('beto');
comprobar('los demás sí lo ven', (await lista('grupo_mensajes', { p_grupo: g.id })).some((x) => x.id === md.id));

// reportes: con 3 personas distintas se oculta
await falla('no se reporta lo propio', () => rpc('grupo_reportar', { p_mensaje: m1.id }), /propio/);
for (const u of ['carla', 'nina', 'dani']) { await como(u); await rpc('grupo_reportar', { p_mensaje: m1.id, p_motivo: 'feo' }); await rpc('grupo_reportar', { p_mensaje: m1.id }); }
await como('carla');
comprobar('3 reportes: oculto para los demás', !(await lista('grupo_mensajes', { p_grupo: g.id })).some((x) => x.id === m1.id));
await como('beto');
comprobar('quien lo escribió lo sigue viendo (marcado)', (await lista('grupo_mensajes', { p_grupo: g.id })).find((x) => x.id === m1.id).oculto === true);
await falla('un miembro no ve lo reportado', () => lista('grupo_reportados', { p_grupo: g.id }), /modera/);
await como('ana');
let rep = await lista('grupo_reportados', { p_grupo: g.id });
comprobar('la dueña ve lo reportado con motivos', rep.length === 1 && rep[0].reportes === 3 && rep[0].motivos.length === 3, JSON.stringify(rep[0] && rep[0].motivos));
await rpc('grupo_mensaje_accion', { p_mensaje: m1.id, p_accion: 'mostrar' });
await como('carla');
comprobar('la dueña lo vuelve a mostrar', (await lista('grupo_mensajes', { p_grupo: g.id })).some((x) => x.id === m1.id));

// fijar y borrar
await falla('un miembro no fija', () => rpc('grupo_mensaje_accion', { p_mensaje: m2.id, p_accion: 'fijar' }), /modera/);
await falla('un miembro no borra lo ajeno', () => rpc('grupo_mensaje_accion', { p_mensaje: m2.id, p_accion: 'borrar' }), /quien lo escribió/);
await como('ana');
await rpc('grupo_mensaje_accion', { p_mensaje: m2.id, p_accion: 'fijar' });
comprobar('fijado', (await lista('grupo_fijados', { p_grupo: g.id })).map((x) => x.id).join() === String(m2.id));
await como('beto');
await rpc('grupo_mensaje_accion', { p_mensaje: m4.id, p_accion: 'borrar' });
await admin();
comprobar('borrar la nota de voz borra el audio', (await q(`select 1 from storage.objects where name = $1`, [rutaAudio])).length === 0);

// roles, silenciar, expulsar
await como('ana');
await rpc('grupo_poner_rol', { p_grupo: g.id, p_usuario: personas.beto, p_rol: 'moderador' });
await como('beto');
await falla('un moderador no puede con la dueña', () => rpc('grupo_expulsar', { p_grupo: g.id, p_usuario: personas.ana }), /no puedes/);
await falla('un moderador no nombra moderadores', () => rpc('grupo_poner_rol', { p_grupo: g.id, p_usuario: personas.carla, p_rol: 'moderador' }), /modera/);
await rpc('grupo_silenciar', { p_grupo: g.id, p_usuario: personas.dani, p_minutos: 30 });
await como('dani');
await falla('silenciado no escribe', () => rpc('grupo_enviar', { p_grupo: g.id, p_texto: 'hola' }), /silenció/);
await falla('silenciado tampoco sube notas de voz', () => q(`insert into storage.objects (bucket_id, name) values ('audios-grupos', $1)`, [`${g.id}/${personas.dani}/x.m4a`]), /row-level security|policy/);
await como('beto');
await rpc('grupo_expulsar', { p_grupo: g.id, p_usuario: personas.dani });
await como('dani');
await falla('expulsado no vuelve a entrar', () => rpc('grupo_unirse', { p_grupo: g.id }), /no puedes volver/);
await falla('expulsado ya no lee', () => lista('grupo_mensajes', { p_grupo: g.id }), /no estás/);
await como('beto');
await rpc('grupo_readmitir', { p_grupo: g.id, p_usuario: personas.dani });
await como('dani');
comprobar('readmitido puede volver', (await rpc('grupo_unirse', { p_grupo: g.id })).rol === 'miembro');

// miembros: el menor aparece con lo mínimo y sin datos de más
await como('carla');
const gente = await lista('grupo_miembros_lista', { p_grupo: g.id });
comprobar('lista de miembros: dueña primero', gente[0].rol === 'dueno' && gente[1].rol === 'moderador');
comprobar('carla no ve a dani (lo bloqueó)', !gente.some((x) => x.id === personas.dani));
const ninaFila = gente.find((x) => x.usuario === 'nina');
comprobar('del menor solo nombre/usuario/foto/rol', ninaFila && !('fecha_nacimiento' in ninaFila) && !('bio' in ninaFila));
await como('carla');
await falla('el chat privado sigue siendo solo entre amigos (también con menores)', () => rpc('abrir_chat', { p_otro: personas.nina }), /amig/);

// editar, código, salir y heredar
await como('ana');
v = await rpc('grupo_editar', { p_grupo: g.id, p_nombre: 'Reggaetón Perú', p_descripcion: 'nuevo' });
comprobar('editar nombre', v.nombre === 'Reggaetón Perú');
await falla('un abierto no tiene código que cambiar', () => rpc('grupo_cambiar_codigo', { p_grupo: g.id }), /privados/);
const viejo = p.codigo;
const nuevo = await rpc('grupo_cambiar_codigo', { p_grupo: p.id });
comprobar('código nuevo distinto', nuevo !== viejo && /^[A-Z2-9]{8}$/.test(nuevo));
await como('carla');
await falla('el código viejo ya no vale', () => rpc('grupo_unirse_codigo', { p_codigo: viejo }), /ningún grupo/);
await como('ana');
await rpc('grupo_salir', { p_grupo: g.id });
await como('beto');
comprobar('sale la dueña: hereda el moderador', (await rpc('grupo_ver', { p_grupo: g.id })).rol === 'dueno');
await como('beto'); await rpc('grupo_salir', { p_grupo: p.id });
await como('ana');
const solo = await rpc('grupo_crear', { p_nombre: 'Solo yo', p_tipo: 'privado' }).catch(() => null);
if (solo) {
  await rpc('grupo_salir', { p_grupo: solo.id });
  await admin();
  comprobar('sale el último: el grupo se borra', (await q(`select 1 from grupos where id = $1`, [solo.id])).length === 0);
}

// moderación de Caudal: cerrar un grupo abierto
await admin();
await q(`insert into public.moderadores (user_id) values ($1)`, [personas.eva]);
await como('carla');
await falla('cualquiera no cierra grupos', () => rpc('grupo_cerrar', { p_grupo: g.id }), /moderación de Caudal/);
await como('eva');
await rpc('grupo_cerrar', { p_grupo: g.id });
await como('carla');
await falla('cerrado: no se escribe', () => rpc('grupo_enviar', { p_grupo: g.id, p_texto: 'hola' }), /cerrado/);
comprobar('cerrado: no sale en explorar', !(await lista('grupos_explorar')).some((x) => x.id === g.id));

// borrar la cuenta se lleva sus filas
await admin();
await q(`delete from auth.users where id = $1`, [personas.carla]);
comprobar('cuenta borrada: sin miembros ni mensajes suyos',
  (await q(`select 1 from grupo_miembros where user_id = $1 union all select 1 from grupo_mensajes where autor = $1`, [personas.carla])).length === 0);

console.log(`\n${ok} bien, ${mal} mal`);
process.exit(mal ? 1 : 0);
