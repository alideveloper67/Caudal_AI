// «¿Qué suena?»: reconoce una canción a partir de unos segundos grabados con el micrófono.
//
// Las apps graban ~10 s y mandan el audio aquí; esta función se lo pasa a un servicio de
// reconocimiento con API oficial. La clave vive SOLO aquí, en una variable de entorno de Netlify,
// nunca en la app:
//
//   AUDD_API_TOKEN                        → AudD (https://audd.io), se usa si está puesta
//   ACRCLOUD_HOST, ACRCLOUD_ACCESS_KEY,   → ACRCloud (https://www.acrcloud.com), si no hay AudD
//   ACRCLOUD_ACCESS_SECRET
//
//   GET  /api/reconocer                   → {disponible: bool, servicio}
//   POST /api/reconocer  (cuerpo: el audio, wav/m4a/mp3/ogg/webm, 8 KB a 2 MB)
//        → {encontrada: true, titulo, artista, album, anio, portada, video_id, consulta, servicio}
//        → {encontrada: false}
//        → 503 {disponible: false, mensaje} si no hay clave configurada
//        → 4xx/5xx {mensaje} si algo falla (frases para personas)
import { createHmac } from 'node:crypto';

export const MAXIMO = 2 * 1024 * 1024;
export const MINIMO = 8 * 1024;
const POR_IP = 8;                 // reconocimientos por IP…
const VENTANA_MS = 10 * 60 * 1000; // …cada 10 minutos (en memoria: es un freno, no una garantía)
const TIPOS = /^(audio\/(wav|x-wav|wave|mp4|m4a|x-m4a|aac|mpeg|mp3|ogg|webm|flac)|video\/(mp4|webm)|application\/octet-stream)$/i;

const NO_DISPONIBLE = '«¿Qué suena?» todavía no está disponible: falta activarlo en el servidor de Caudal.';

export function servicioDe(env) {
  if (env.AUDD_API_TOKEN) return 'audd';
  if (env.ACRCLOUD_HOST && env.ACRCLOUD_ACCESS_KEY && env.ACRCLOUD_ACCESS_SECRET) return 'acrcloud';
  return '';
}

const texto = (v) => (v == null ? '' : String(v)).trim();
const https = (u) => (typeof u === 'string' && /^https:\/\/[^\s"'<>]+$/i.test(u) ? u : '');
const anioDe = (f) => (texto(f).match(/^(\d{4})/) || [])[1] || '';
const vidValido = (v) => (typeof v === 'string' && /^[A-Za-z0-9_-]{11}$/.test(v) ? v : '');

function resultado(servicio, { titulo, artista, album, anio, portada, video_id }) {
  titulo = texto(titulo); artista = texto(artista);
  if (!titulo) return { encontrada: false };
  return {
    encontrada: true, servicio, titulo, artista, album: texto(album), anio: texto(anio),
    portada: https(portada), video_id: vidValido(video_id),
    consulta: [artista, titulo].filter(Boolean).join(' '),
  };
}

/** Lee la respuesta de AudD. Lanza Error(mensaje) si AudD dio un error. */
export function leerAudd(d) {
  if (!d || typeof d !== 'object') throw new Error('El servicio de reconocimiento respondió algo raro.');
  if (d.status === 'error') {
    const m = texto(d.error && d.error.error_message).toLowerCase();
    if (/limit|exceed|quota|requests/.test(m)) throw new Error('agotado');
    throw new Error('El servicio de reconocimiento no aceptó el audio.');
  }
  const r = d.result;
  if (!r || typeof r !== 'object') return { encontrada: false };
  const sp = r.spotify && typeof r.spotify === 'object' ? r.spotify : {};
  const am = r.apple_music && typeof r.apple_music === 'object' ? r.apple_music : {};
  const imagenSp = sp.album && Array.isArray(sp.album.images) && sp.album.images[0] ? sp.album.images[0].url : '';
  const imagenAm = am.artwork && am.artwork.url ? String(am.artwork.url).replace('{w}', '500').replace('{h}', '500') : '';
  return resultado('audd', {
    titulo: r.title, artista: r.artist, album: r.album, anio: anioDe(r.release_date),
    portada: imagenSp || imagenAm,
  });
}

/** Lee la respuesta de ACRCloud (/v1/identify). */
export function leerAcr(d) {
  const codigo = d && d.status ? Number(d.status.code) : -1;
  if (codigo === 1001) return { encontrada: false };          // no reconoció nada
  if (codigo === 3003 || codigo === 3015) throw new Error('agotado');
  if (codigo !== 0) throw new Error('El servicio de reconocimiento no aceptó el audio.');
  const m = d.metadata && Array.isArray(d.metadata.music) ? d.metadata.music[0] : null;
  if (!m) return { encontrada: false };
  const yt = m.external_metadata && m.external_metadata.youtube ? m.external_metadata.youtube.vid : '';
  return resultado('acrcloud', {
    titulo: m.title,
    artista: Array.isArray(m.artists) ? m.artists.map((a) => texto(a && a.name)).filter(Boolean).join(', ') : '',
    album: m.album && m.album.name, anio: anioDe(m.release_date), video_id: yt,
  });
}

/** La firma de ACRCloud (HMAC-SHA1 en base64) para /v1/identify. */
export function firmaAcr(clave, secreto, marca) {
  const cadena = ['POST', '/v1/identify', clave, 'audio', '1', String(marca)].join('\n');
  return createHmac('sha1', secreto).update(cadena, 'utf8').digest('base64');
}

async function preguntarAudd(audio, tipo, env, pedir) {
  const f = new FormData();
  f.append('api_token', env.AUDD_API_TOKEN);
  f.append('return', 'spotify,apple_music');
  f.append('file', new Blob([audio], { type: tipo }), 'muestra');
  const r = await pedir('https://api.audd.io/', { method: 'POST', body: f });
  if (!r.ok) throw new Error('El servicio de reconocimiento no respondió (' + r.status + ').');
  return leerAudd(await r.json());
}

async function preguntarAcr(audio, tipo, env, pedir, ahora) {
  const marca = Math.floor(ahora() / 1000);
  const host = String(env.ACRCLOUD_HOST).replace(/^https?:\/\//, '').replace(/\/.*$/, '');
  const f = new FormData();
  f.append('sample', new Blob([audio], { type: tipo }), 'muestra');
  f.append('sample_bytes', String(audio.byteLength));
  f.append('access_key', env.ACRCLOUD_ACCESS_KEY);
  f.append('data_type', 'audio');
  f.append('signature_version', '1');
  f.append('signature', firmaAcr(env.ACRCLOUD_ACCESS_KEY, env.ACRCLOUD_ACCESS_SECRET, marca));
  f.append('timestamp', String(marca));
  const r = await pedir(`https://${host}/v1/identify`, { method: 'POST', body: f });
  if (!r.ok) throw new Error('El servicio de reconocimiento no respondió (' + r.status + ').');
  return leerAcr(await r.json());
}

const CABECERAS = {
  'content-type': 'application/json; charset=utf-8',
  'cache-control': 'no-store',
  'access-control-allow-origin': '*',
  'access-control-allow-methods': 'GET, POST, OPTIONS',
  'access-control-allow-headers': 'content-type',
};
const json = (d, status = 200) => new Response(JSON.stringify(d), { status, headers: CABECERAS });

/** Se pueden inyectar el entorno, el fetch y el reloj para probar sin red. */
export function crearManejador({ env = process.env, pedir = (...a) => globalThis.fetch(...a), ahora = Date.now } = {}) {
  const usos = new Map(); // ip -> [marcas]
  return async (req, contexto) => {
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: CABECERAS });
    const servicio = servicioDe(env);
    if (req.method === 'GET' || req.method === 'HEAD') return json({ disponible: !!servicio, servicio });
    if (req.method !== 'POST') return json({ mensaje: 'Método no permitido.' }, 405);
    if (!servicio) return json({ disponible: false, mensaje: NO_DISPONIBLE }, 503);

    const ip = (contexto && contexto.ip) || req.headers.get('x-nf-client-connection-ip') || 'x';
    const t = ahora();
    const mias = (usos.get(ip) || []).filter((m) => t - m < VENTANA_MS);
    if (mias.length >= POR_IP) {
      usos.set(ip, mias);
      return json({ mensaje: 'Ya probaste muchas veces seguidas. Espera unos minutos y vuelve a intentarlo.' }, 429);
    }
    const tipo = (req.headers.get('content-type') || 'application/octet-stream').split(';')[0].trim();
    if (!TIPOS.test(tipo)) return json({ mensaje: 'Ese formato de audio no se puede reconocer.' }, 415);
    const largo = Number(req.headers.get('content-length') || 0);
    if (largo > MAXIMO) return json({ mensaje: 'La grabación es demasiado larga. Graba unos 10 segundos.' }, 413);
    const audio = new Uint8Array(await req.arrayBuffer());
    if (audio.byteLength > MAXIMO) return json({ mensaje: 'La grabación es demasiado larga. Graba unos 10 segundos.' }, 413);
    if (audio.byteLength < MINIMO) return json({ mensaje: 'La grabación salió vacía o muy corta. Acerca el teléfono a la música y vuelve a probar.' }, 400);

    mias.push(t);
    usos.set(ip, mias);
    try {
      const r = servicio === 'audd' ? await preguntarAudd(audio, tipo, env, pedir) : await preguntarAcr(audio, tipo, env, pedir, ahora);
      return json(r);
    } catch (e) {
      const m = String((e && e.message) || '');
      if (m === 'agotado') return json({ mensaje: '«¿Qué suena?» llegó a su límite de consultas por ahora. Vuelve a probar más tarde.' }, 503);
      return json({ mensaje: m.startsWith('El servicio') ? m : 'No se pudo reconocer ahora. Revisa tu internet y vuelve a probar.' }, 502);
    }
  };
}

export default crearManejador();

export const config = { path: '/api/reconocer' };
