// Pruebas sin red de /api/servicios, /api/spotify y /api/soundcloud:
//   node netlify/pruebas/servicios_musica.prueba.mjs
import assert from 'node:assert/strict';
import { configuracion } from '../functions/servicios.mjs';
import { crearManejador as spotify, pistasDePagina } from '../functions/spotify.mjs';
import { crearManejador as soundcloud, tipoDe, cancion as cancionSC } from '../functions/soundcloud.mjs';

let fallos = 0;
const ok = (c, m) => { if (!c) { fallos++; console.log('  FALLA:', m); } else console.log('  ok:', m); };
const json = (d, status = 200, h = {}) => new Response(JSON.stringify(d), { status, headers: { 'content-type': 'application/json', ...h } });
const get = (ruta) => new Request('https://x.test' + ruta);

console.log('servicios');
ok(JSON.stringify(configuracion({})) === JSON.stringify({ spotify_client_id: '', spotify: false, soundcloud: false }), 'sin variables: nada activado');
const c = configuracion({ SPOTIFY_CLIENT_ID: ' abc ', SOUNDCLOUD_CLIENT_ID: 'x', SOUNDCLOUD_CLIENT_SECRET: 'y' });
ok(c.spotify_client_id === 'abc' && !c.spotify && c.soundcloud, 'el client_id de Spotify es público; el secreto no se entrega');
ok(!JSON.stringify(configuracion({ SPOTIFY_CLIENT_ID: 'a', SPOTIFY_CLIENT_SECRET: 'SECRETO' })).includes('SECRETO'), 'el secreto nunca sale');

console.log('spotify');
{
  const sin = await (await spotify(async () => { throw new Error('no debería pedir'); }, {})(get('/api/spotify?tipo=playlist&id=37i9dQZF1DXcBWIGoYBM5M'))).json();
  ok(sin.error === 'sin_credenciales', 'sin credenciales lo dice');
  const mal = await (await spotify(async () => json({}), {})(get('/api/spotify?tipo=usuario&id=x'))).json();
  ok(mal.error === 'enlace', 'rechaza tipos e ids raros');
}

// una lista de 6 123 canciones, de 50 en 50 (como /items)
function spotifyFalso({ total = 6123, prohibir = [] } = {}) {
  const pedidos = [];
  const pedir = async (url, op = {}) => {
    pedidos.push(url);
    if (url.includes('accounts.spotify.com')) {
      ok(op.headers.authorization.startsWith('Basic '), 'el token se pide con Basic (secreto solo en el servidor)');
      return json({ access_token: 'tk', expires_in: 3600 });
    }
    if (prohibir.some((p) => url.includes(p))) return json({ error: {} }, 403);
    const u = new URL(url);
    if (/\/playlists\/[^/]+$/.test(u.pathname)) return json({ name: 'Enorme', owner: { display_name: 'Ana' }, images: [{ url: 'https://i/x.jpg' }] });
    const offset = Number(u.searchParams.get('offset')) || 0;
    const limit = Number(u.searchParams.get('limit'));
    const items = [];
    for (let i = offset; i < Math.min(offset + limit, total); i++) {
      items.push(u.pathname.endsWith('/items') ? { item: { type: 'track', name: `Tema ${i}`, duration_ms: 200000, artists: [{ name: 'Grupo' }] } } : { track: { name: `Tema ${i}`, artists: [{ name: 'Grupo' }] } });
    }
    return json({ items, total, next: offset + limit < total ? 'siguiente' : null });
  };
  return { pedir, pedidos };
}

{
  const { pedir } = spotifyFalso();
  const h = spotify(pedir, { SPOTIFY_CLIENT_ID: 'a', SPOTIFY_CLIENT_SECRET: 'b' });
  let todas = [];
  let desde = 0;
  let primera;
  for (let vueltas = 0; desde !== null && vueltas < 1000; vueltas++) {
    const d = await (await h(get(`/api/spotify?tipo=playlist&id=37i9dQZF1DXcBWIGoYBM5M&desde=${desde}`))).json();
    primera = primera || d;
    todas = todas.concat(d.canciones);
    desde = d.siguiente;
  }
  ok(todas.length === 6123, `una lista de 6123 llega entera por trozos (${todas.length})`);
  ok(primera.titulo === 'Enorme' && primera.autor === 'Ana' && primera.total === 6123, 'la cabecera viene en el primer trozo');
  ok(todas[6122].titulo === 'Tema 6122' && todas[0].duracion === 200, 'en orden y con duración');
}
{
  const { pedir, pedidos } = spotifyFalso({ total: 230, prohibir: ['/items'] });
  const d = await (await spotify(pedir, { SPOTIFY_CLIENT_ID: 'a2', SPOTIFY_CLIENT_SECRET: 'b' })(get('/api/spotify?tipo=playlist&id=37i9dQZF1DXcBWIGoYBM5M'))).json();
  ok(d.canciones.length === 230 && pedidos.some((p) => p.includes('/tracks?limit=100')), 'si /items está prohibido prueba la ruta de siempre');
}
{
  const { pedir } = spotifyFalso({ prohibir: ['/items', '/tracks'] });
  const d = await (await spotify(pedir, { SPOTIFY_CLIENT_ID: 'a3', SPOTIFY_CLIENT_SECRET: 'b' })(get('/api/spotify?tipo=playlist&id=37i9dQZF1DXcBWIGoYBM5M'))).json();
  ok(d.error === 'lista_ajena', 'una lista ajena (reglas de 2026) se explica, no revienta');
}
ok(pistasDePagina({ items: [{ item: { type: 'episode', name: 'pod' } }, { name: 'De álbum', artists: [] }] }).length === 1, 'fuera los episodios');

console.log('soundcloud');
ok(tipoDe('https://soundcloud.com/ana/sets/verano?si=1')[0] === 'lista', 'reconoce una lista');
ok(tipoDe('https://soundcloud.com/ana')[0] === 'me_gusta' && tipoDe('https://soundcloud.com/ana/likes')[1] === 'https://soundcloud.com/ana', 'un perfil o sus likes -> me gusta');
ok(tipoDe('https://evil.example/ana/sets/x')[0] === '' && tipoDe('https://soundcloud.com.evil.example/a')[0] === '', 'solo soundcloud.com');
ok(cancionSC({ title: 'Grupo - Tema', duration: 61000, user: { username: 'sub' } }).artista === 'Grupo', 'separa «Artista - Tema»');
{
  const sin = await (await soundcloud(async () => json({}), {})(get('/api/soundcloud?url=https://soundcloud.com/ana/likes'))).json();
  ok(sin.error === 'sin_credenciales', 'sin credenciales lo dice');
}
{
  const total = 5321;
  const pedir = async (url) => {
    if (url.includes('secure.soundcloud.com')) return json({ access_token: 'tk', expires_in: 3600 });
    const u = new URL(url);
    if (u.pathname === '/resolve') return json({ kind: 'user', urn: 'soundcloud:users:9', username: 'ana' });
    const offset = Number(u.searchParams.get('offset')) || 0;
    const collection = [];
    for (let i = offset; i < Math.min(offset + 200, total); i++) collection.push({ kind: 'track', title: `T${i}`, duration: 1000, user: { username: 'ana' } });
    const sig = offset + 200 < total ? `https://api.soundcloud.com/users/soundcloud%3Ausers%3A9/likes/tracks?linked_partitioning=true&limit=200&offset=${offset + 200}` : null;
    return json({ collection, next_href: sig });
  };
  const h = soundcloud(pedir, { SOUNDCLOUD_CLIENT_ID: 'i', SOUNDCLOUD_CLIENT_SECRET: 's' });
  let d = await (await h(get('/api/soundcloud?url=' + encodeURIComponent('https://soundcloud.com/ana/likes')))).json();
  let todas = d.canciones;
  ok(d.me_gusta && d.titulo === 'Me gusta de ana', 'los me gusta de un perfil');
  for (let v = 0; d.siguiente && v < 1000; v++) {
    d = await (await h(get('/api/soundcloud?cursor=' + encodeURIComponent(d.siguiente)))).json();
    todas = todas.concat(d.canciones);
  }
  ok(todas.length === total, `5321 me gusta llegan enteros (${todas.length})`);
  const raro = await (await h(get('/api/soundcloud?cursor=' + encodeURIComponent('https://evil.example/x')))).json();
  ok(raro.error === 'enlace', 'el cursor solo puede ser de api.soundcloud.com');
}

if (fallos) {
  console.log(`\n${fallos} FALLO(S)`);
  process.exit(1);
}
console.log('\nTodo bien.');
