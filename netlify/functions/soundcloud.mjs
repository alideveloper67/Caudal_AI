// Canciones de una lista (set) o los me gusta públicos de un perfil de SoundCloud, con
// la API oficial y una app registrada (soundcloud.com/you/apps).
//
//   GET /api/soundcloud?url=https://soundcloud.com/<perfil>/sets/<lista>
//   GET /api/soundcloud?url=https://soundcloud.com/<perfil>/likes   (o el perfil a secas)
//   GET /api/soundcloud?url=...&cursor=<siguiente>                 (el trozo que sigue)
//   -> { titulo, autor, portada, me_gusta, canciones: [{titulo, artista, duracion}], siguiente }
//
// SOUNDCLOUD_CLIENT_ID y SOUNDCLOUD_CLIENT_SECRET viven en las variables de entorno del
// sitio. El token de cliente se reutiliza mientras dura (SoundCloud da pocos por hora).
// Se pagina con linked_partitioning (200 por página) y se entrega por trozos; el cursor es
// el `next_href` de SoundCloud y solo se acepta si apunta a api.soundcloud.com.
// Nunca se usa la clave interna de la web de SoundCloud.

const API = 'https://api.soundcloud.com';
const PRESUPUESTO_MS = 7000;
const token = { valor: '', caduca: 0, de: '' };

const limpiar = (t) => String(t ?? '').replace(/\s+/g, ' ').trim();

export function cancion(t) {
  const meta = t.publisher_metadata || {};
  let artista = limpiar(meta.artist) || limpiar((t.user || {}).username);
  let titulo = limpiar(t.title);
  const m = !meta.artist && titulo.match(/^(.+?)\s+[-–—]\s+(.+)$/);
  if (m) {
    artista = m[1].trim();
    titulo = m[2].trim();
  }
  return { titulo, artista, duracion: Math.floor((Number(t.duration || t.full_duration) || 0) / 1000) };
}

// 'lista' | 'me_gusta' | 'cancion' | '' y la ruta para resolver
export function tipoDe(url) {
  let u;
  try {
    u = new URL(url);
  } catch {
    return ['', ''];
  }
  const host = u.hostname.toLowerCase();
  if (!(host === 'soundcloud.com' || host.endsWith('.soundcloud.com'))) return ['', ''];
  const p = u.pathname.split('/').filter(Boolean);
  if (!p.length || ['discover', 'search', 'stream', 'you', 'charts', 'upload', 'settings', 'pages'].includes(p[0])) return ['', ''];
  if (p.length >= 3 && p[1] === 'sets') return ['lista', `https://soundcloud.com/${p.slice(0, 3).join('/')}`];
  if (p.length === 1 || p[1] === 'likes') return ['me_gusta', `https://soundcloud.com/${p[0]}`];
  if (p.length === 2) return ['cancion', `https://soundcloud.com/${p.join('/')}`];
  return ['', ''];
}

async function pedirToken(pedir, env) {
  const id = String(env.SOUNDCLOUD_CLIENT_ID || '').trim();
  const secreto = String(env.SOUNDCLOUD_CLIENT_SECRET || '').trim();
  if (!id || !secreto) return '';
  if (token.valor && token.de === id && Date.now() < token.caduca) return token.valor;
  const r = await pedir('https://secure.soundcloud.com/oauth/token', {
    method: 'POST',
    headers: {
      authorization: 'Basic ' + Buffer.from(`${id}:${secreto}`).toString('base64'),
      accept: 'application/json; charset=utf-8',
      'content-type': 'application/x-www-form-urlencoded',
    },
    body: 'grant_type=client_credentials',
  });
  if (!r.ok) return '';
  const d = await r.json();
  Object.assign(token, { valor: d.access_token || '', de: id, caduca: Date.now() + ((Number(d.expires_in) || 3600) - 60) * 1000 });
  return token.valor;
}

class NoExiste extends Error {}

async function api(pedir, url, tk) {
  for (let intento = 0; intento < 3; intento++) {
    const r = await pedir(url, { headers: { authorization: `OAuth ${tk}`, accept: 'application/json; charset=utf-8' } });
    if (r.status === 404 || r.status === 403 || r.status === 401) throw new NoExiste();
    if (r.status === 429 || r.status >= 500) {
      await new Promise((ok) => setTimeout(ok, 1000 * (intento + 1)));
      continue;
    }
    if (!r.ok) throw new Error('soundcloud ' + r.status);
    return r.json();
  }
  throw new Error('soundcloud ocupado');
}

const cursorValido = (c) => typeof c === 'string' && c.startsWith(API + '/');

async function trozo(pedir, tk, primera, reloj) {
  const canciones = [];
  let url = primera;
  while (url) {
    const d = await api(pedir, url, tk);
    const filas = Array.isArray(d) ? d : d.collection || [];
    for (const f of filas) {
      const t = f && f.track && typeof f.track === 'object' ? f.track : f;
      if (t && t.title && (t.kind || 'track') === 'track') canciones.push(cancion(t));
    }
    url = !Array.isArray(d) && cursorValido(d.next_href) ? d.next_href : null;
    if (url && Date.now() - reloj > PRESUPUESTO_MS) return { canciones, siguiente: url };
  }
  return { canciones, siguiente: null };
}

const CAB = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' };
const responder = (d) => new Response(JSON.stringify(d), { status: 200, headers: CAB });
const fallo = (error, mensaje) => responder({ error, mensaje });

export function crearManejador(pedir = (...a) => globalThis.fetch(...a), env = process.env) {
  return async (req) => {
    if (req.method !== 'GET') return new Response('Solo GET', { status: 405 });
    const q = new URL(req.url).searchParams;
    let url = q.get('url') || '';
    const cursor = q.get('cursor') || '';
    const reloj = Date.now();
    let tk;
    try {
      tk = await pedirToken(pedir, env);
    } catch {
      return fallo('soundcloud', 'No se pudo conectar con SoundCloud.');
    }
    if (!tk) return fallo('sin_credenciales', 'La conexión con SoundCloud aún no está activada en Caudal.');
    try {
      if (cursor) {
        if (!cursorValido(cursor)) return fallo('enlace', 'Ese enlace de SoundCloud no es válido.');
        return responder(await trozo(pedir, tk, cursor, reloj));
      }
      // los enlaces cortos (on.soundcloud.com/...) llevan a la página de verdad
      if (/^https:\/\/on\.soundcloud\.com\//i.test(url)) {
        const r = await pedir(url, { method: 'HEAD', redirect: 'follow' });
        url = r.url || url;
      }
      const [tipo, ruta] = tipoDe(url);
      if (!tipo) return fallo('enlace', 'Pega el enlace de una lista, una canción o un perfil de SoundCloud.');
      const recurso = await api(pedir, `${API}/resolve?url=${encodeURIComponent(ruta)}`, tk);
      const ident = encodeURIComponent(recurso.urn || recurso.id);
      const portada = recurso.artwork_url || recurso.avatar_url || '';
      if (recurso.kind === 'track') {
        return responder({ titulo: limpiar(recurso.title), autor: limpiar((recurso.user || {}).username), portada, me_gusta: false, canciones: [cancion(recurso)], siguiente: null });
      }
      if (recurso.kind === 'playlist') {
        const r = await trozo(pedir, tk, `${API}/playlists/${ident}/tracks?linked_partitioning=true&limit=200`, reloj);
        return responder({ titulo: limpiar(recurso.title) || 'Lista de SoundCloud', autor: limpiar((recurso.user || {}).username), portada, me_gusta: false, ...r });
      }
      if (recurso.kind === 'user') {
        const nombre = limpiar(recurso.username) || 'SoundCloud';
        const r = await trozo(pedir, tk, `${API}/users/${ident}/likes/tracks?linked_partitioning=true&limit=200`, reloj);
        return responder({ titulo: `Me gusta de ${nombre}`, autor: nombre, portada, me_gusta: true, ...r });
      }
      return fallo('enlace', 'Ese enlace de SoundCloud no es de una lista, una canción ni un perfil.');
    } catch (e) {
      if (e instanceof NoExiste) return fallo('no_existe', 'Eso no existe en SoundCloud o es privado.');
      return fallo('soundcloud', 'SoundCloud no contestó bien. Prueba otra vez en un rato.');
    }
  };
}

export default crearManejador();

export const config = { path: '/api/soundcloud' };
