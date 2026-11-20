// Prueba de «¿Qué suena?» sin red: node netlify/pruebas/reconocer.prueba.mjs
import { createHmac } from 'node:crypto';
import { crearManejador, leerAudd, leerAcr, firmaAcr, servicioDe, MINIMO, MAXIMO } from '../functions/reconocer.mjs';

let fallos = 0;
const ok = (c, m) => { if (!c) { fallos++; console.log('  FALLA:', m); } else console.log('  ok:', m); };

function falso(respuesta) {
  const f = async (url, init) => { f.url = url; f.init = init; f.llamadas++; return typeof respuesta === 'function' ? respuesta() : respuesta; };
  f.llamadas = 0;
  return f;
}
const jsonR = (d, status = 200) => new Response(JSON.stringify(d), { status, headers: { 'content-type': 'application/json' } });
const audio = (n = MINIMO + 10) => new Uint8Array(n).fill(7);
const pedir = (h, { metodo = 'POST', cuerpo = audio(), tipo = 'audio/wav', ip = '1.1.1.1' } = {}) =>
  h(new Request('https://x.test/api/reconocer', { method: metodo, body: metodo === 'POST' ? cuerpo : undefined, headers: { 'content-type': tipo } }), { ip });
const AUDD_OK = {
  status: 'success',
  result: { artist: 'Shakira', title: 'Zoo', album: 'Zootopia 2', release_date: '2025-10-10',
    spotify: { album: { images: [{ url: 'https://i.scdn.co/image/abc' }] } } },
};

// sin clave
let h = crearManejador({ env: {}, pedir: falso(jsonR({})) });
let r = await pedir(h, { metodo: 'GET' });
let d = await r.json();
ok(r.status === 200 && d.disponible === false && d.servicio === '', 'GET sin clave: no disponible');
r = await pedir(h);
d = await r.json();
ok(r.status === 503 && d.disponible === false && /todavía no está disponible/.test(d.mensaje), 'POST sin clave: 503 con frase');
ok(servicioDe({ ACRCLOUD_HOST: 'h' }) === '', 'ACRCloud a medias no cuenta');

// AudD
let f = falso(jsonR(AUDD_OK));
h = crearManejador({ env: { AUDD_API_TOKEN: 'secreto-audd' }, pedir: f });
ok((await (await pedir(h, { metodo: 'GET' })).json()).servicio === 'audd', 'GET con AudD: disponible');
r = await pedir(h);
d = await r.json();
ok(r.status === 200 && d.encontrada && d.titulo === 'Zoo' && d.artista === 'Shakira' && d.anio === '2025', 'AudD reconoce');
ok(d.portada === 'https://i.scdn.co/image/abc' && d.consulta === 'Shakira Zoo', 'portada y consulta');
ok(f.url === 'https://api.audd.io/' && f.init.body instanceof FormData && f.init.body.get('api_token') === 'secreto-audd', 'manda el token a AudD');
ok(f.init.body.get('file') instanceof Blob && f.init.body.get('file').size === MINIMO + 10, 'manda el audio');
ok(!JSON.stringify(d).includes('secreto'), 'la clave nunca vuelve al cliente');
ok(leerAudd({ status: 'success', result: null }).encontrada === false, 'AudD sin resultado');
let lanzo = ''; try { leerAudd({ status: 'error', error: { error_code: 901, error_message: 'Recognition failed: you have exceeded the limit' } }); } catch (e) { lanzo = e.message; }
ok(lanzo === 'agotado', 'AudD sin consultas = agotado');
h = crearManejador({ env: { AUDD_API_TOKEN: 't' }, pedir: falso(jsonR({ status: 'error', error: { error_message: 'request limit exceeded' } })) });
r = await pedir(h); d = await r.json();
ok(r.status === 503 && /límite de consultas/.test(d.mensaje), 'agotado: frase para personas');
ok(leerAudd({ status: 'success', result: { artist: 'A', title: 'T', apple_music: { artwork: { url: 'https://a.mzstatic.com/{w}x{h}bb.jpg' } } } }).portada === 'https://a.mzstatic.com/500x500bb.jpg', 'portada de Apple Music');
ok(leerAudd({ status: 'success', result: { artist: 'A', title: 'T', spotify: { album: { images: [{ url: 'javascript:alert(1)' }] } } } }).portada === '', 'portada no https se descarta');

// ACRCloud
const ENV_ACR = { ACRCLOUD_HOST: 'identify-eu-west-1.acrcloud.com', ACRCLOUD_ACCESS_KEY: 'clave', ACRCLOUD_ACCESS_SECRET: 'secreto' };
f = falso(jsonR({ status: { code: 0, msg: 'Success' }, metadata: { music: [{ title: 'Despacito', artists: [{ name: 'Luis Fonsi' }, { name: 'Daddy Yankee' }], album: { name: 'Vida' }, release_date: '2017-01-12', external_metadata: { youtube: { vid: 'kJQP7kiw5Fk' } } }] } }));
h = crearManejador({ env: ENV_ACR, pedir: f, ahora: () => 1700000000000 });
r = await pedir(h); d = await r.json();
ok(d.encontrada && d.artista === 'Luis Fonsi, Daddy Yankee' && d.video_id === 'kJQP7kiw5Fk' && d.servicio === 'acrcloud', 'ACRCloud reconoce con video de YouTube');
ok(f.url === 'https://identify-eu-west-1.acrcloud.com/v1/identify', 'ACRCloud: host y ruta');
const esperada = createHmac('sha1', 'secreto').update('POST\n/v1/identify\nclave\naudio\n1\n1700000000', 'utf8').digest('base64');
ok(f.init.body.get('signature') === esperada && firmaAcr('clave', 'secreto', 1700000000) === esperada, 'ACRCloud: firma HMAC-SHA1');
ok(f.init.body.get('timestamp') === '1700000000' && f.init.body.get('sample_bytes') === String(MINIMO + 10), 'ACRCloud: marca y tamaño');
ok(leerAcr({ status: { code: 1001 } }).encontrada === false, 'ACRCloud sin resultado');
lanzo = ''; try { leerAcr({ status: { code: 3003 } }); } catch (e) { lanzo = e.message; }
ok(lanzo === 'agotado', 'ACRCloud límite = agotado');
ok(servicioDe({ ...ENV_ACR, AUDD_API_TOKEN: 'x' }) === 'audd', 'con las dos, manda AudD');

// entradas malas
h = crearManejador({ env: { AUDD_API_TOKEN: 't' }, pedir: falso(jsonR(AUDD_OK)) });
ok((await pedir(h, { cuerpo: audio(100) })).status === 400, 'muy corta: 400');
ok((await pedir(h, { cuerpo: audio(MAXIMO + 1) })).status === 413, 'muy larga: 413');
ok((await pedir(h, { tipo: 'text/html' })).status === 415, 'tipo raro: 415');
ok((await pedir(h, { metodo: 'PUT' })).status === 405, 'PUT: 405');
// freno por IP
f = falso(() => jsonR(AUDD_OK));
h = crearManejador({ env: { AUDD_API_TOKEN: 't' }, pedir: f });
for (let i = 0; i < 8; i++) await pedir(h, { ip: '9.9.9.9' });
r = await pedir(h, { ip: '9.9.9.9' });
ok(r.status === 429 && f.llamadas === 8, 'freno: la 9.ª seguida de la misma IP no llega al servicio');
ok((await pedir(h, { ip: '8.8.8.8' })).status === 200, 'otra IP sigue pudiendo');
// fallo de red
h = crearManejador({ env: { AUDD_API_TOKEN: 't' }, pedir: async () => { throw new Error('ECONNRESET'); } });
r = await pedir(h); d = await r.json();
ok(r.status === 502 && /Revisa tu internet/.test(d.mensaje), 'sin red: 502 con frase');

console.log(fallos ? `\n${fallos} fallos` : '\nreconocer: todo bien');
process.exit(fallos ? 1 : 0);
