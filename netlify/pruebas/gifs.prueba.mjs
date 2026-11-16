// Prueba del servicio de GIF sin red: node netlify/functions/gifs.prueba.mjs
import assert from 'node:assert/strict';

delete process.env.TENOR_API_KEY;
delete process.env.GIPHY_API_KEY;
const { default: manejador } = await import('../functions/gifs.mjs');
const pedir = (ruta) => manejador(new Request('https://x.test' + ruta));

let fallos = 0;
const ok = (c, m) => { if (!c) { fallos++; console.log('  FALLA:', m); } else console.log('  ok:', m); };

// búsquedas prohibidas: adultos y gore, en español e inglés, con acentos y mayúsculas
for (const q of ['porn', 'sex', 'cum', 'ass', 'blood', 'Sexo', 'DESNUDA', 'hentai', 'gore', 'sangre', 'decapitación', 'cadáver', 'suicidio', 'nude girl', 'chicas xxx', 'nsfw', 'twerk', 'mutilación', 'tortura']) {
  const r = await pedir('/api/gifs?q=' + encodeURIComponent(q));
  const d = await r.json();
  ok(d.items.length === 0 && /no está permitida/.test(d.aviso || ''), `bloquea «${q}»`);
}

// búsquedas normales: llegan al proveedor (aquí sin clave: 503 «sin_clave», no un bloqueo)
for (const q of ['gatos', 'anime', 'dragon ball', 'música', 'rock', 'Messi', 'passion', 'class', 'assassin creed', 'analysis', 'peru', 'cumbia', 'cumpleaños', 'feliz cumple', 'assistant', 'asset', 'sexta', 'terraza', 'mutante', 'gorila', 'Gorillaz', 'bloodhound', 'strike', 'torta']) {
  const r = await pedir('/api/gifs?q=' + encodeURIComponent(q));
  const d = await r.json();
  const bloqueada = /no está permitida/.test(d.aviso || '');
  ok(!bloqueada && d.error === 'sin_clave', `deja pasar «${q}»`);
}

// descargas: solo https y solo de Tenor/Giphy
for (const [u, esperado] of [
  ['http://media.tenor.com/x.gif', 400],
  ['https://evil.example.com/x.gif', 400],
  ['https://media.tenor.com.evil.com/x.gif', 400],
  ['file:///etc/passwd', 400],
  ['no-es-url', 400],
]) {
  const r = await pedir('/api/gifs?bajar=' + encodeURIComponent(u));
  ok(r.status === esperado, `rechaza la descarga de ${u}`);
}
const r405 = await manejador(new Request('https://x.test/api/gifs', { method: 'POST' }));
ok(r405.status === 405, 'solo acepta GET');

console.log(fallos === 0 ? '\nTODO BIEN' : `\n${fallos} PRUEBAS FALLARON`);
process.exit(fallos ? 1 : 0);
