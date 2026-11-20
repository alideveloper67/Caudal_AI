// Canciones de un álbum o una lista de Spotify con la API oficial (credenciales de cliente).
//
//   GET /api/spotify?tipo=playlist|album|track&id=<id de Spotify>&desde=0
//   -> { titulo, autor, portada, canciones: [{titulo, artista, duracion}], siguiente, total }
//
// El secreto vive en las variables de entorno del sitio (SPOTIFY_CLIENT_ID y
// SPOTIFY_CLIENT_SECRET) y nunca llega a la app. Se pagina aquí, en el servidor, y se
// entrega por trozos (lo que dé tiempo en unos segundos): la app pide el siguiente trozo
// con `desde=<siguiente>` hasta que `siguiente` llega en null. Sin topes de cantidad.
//
// Ojo, reglas de Spotify desde 2026: sus canciones de una lista solo se entregan a quien
// es dueño o colabora (GET /playlists/{id}/items). Con credenciales de cliente eso solo
// funciona si la app tiene «cuota ampliada»; si no, se contesta { error: 'lista_ajena' }
// y la app lo explica. Los álbumes sí se leen enteros.
//
// Errores (siempre con estado 200 y JSON, para que la app los lea igual):
//   sin_credenciales · lista_ajena · no_existe · enlace · spotify

const API = 'https://api.spotify.com/v1';
const PRESUPUESTO_MS = 7000; // las funciones de Netlify cortan a los 10 s

const token = { valor: '', caduca: 0, de: '' };

const limpiar = (t) => String(t ?? '').replace(/\s+/g, ' ').trim();

export const cancion = (p) => ({
  titulo: limpiar(p.name),
  artista: (p.artists || []).map((a) => limpiar(a && a.name)).filter(Boolean).join(', '),
  duracion: Math.floor((Number(p.duration_ms) || 0) / 1000),
});

// La pista de cada fila: la de un álbum viene tal cual, la de una lista en `item` (antes `track`).
export function pistasDePagina(pagina) {
  const salida = [];
  for (const f of (pagina && pagina.items) || []) {
    if (!f || typeof f !== 'object') continue;
    const p = f.item && typeof f.item === 'object' ? f.item : f.track && typeof f.track === 'object' ? f.track : f;
    if (p.type && p.type !== 'track') continue;
    if (p.name) salida.push(cancion(p));
  }
  return salida;
}

async function pedirToken(pedir, env) {
  const id = String(env.SPOTIFY_CLIENT_ID || '').trim();
  const secreto = String(env.SPOTIFY_CLIENT_SECRET || '').trim();
  if (!id || !secreto) return '';
  if (token.valor && token.de === id && Date.now() < token.caduca) return token.valor;
  const r = await pedir('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: {
      authorization: 'Basic ' + Buffer.from(`${id}:${secreto}`).toString('base64'),
      'content-type': 'application/x-www-form-urlencoded',
    },
    body: 'grant_type=client_credentials',
  });
  if (!r.ok) return '';
  const d = await r.json();
  Object.assign(token, { valor: d.access_token || '', de: id, caduca: Date.now() + ((Number(d.expires_in) || 3600) - 60) * 1000 });
  return token.valor;
}

class Prohibido extends Error {}
class NoExiste extends Error {}

async function api(pedir, url, tk) {
  for (let intento = 0; intento < 3; intento++) {
    const r = await pedir(url, { headers: { authorization: `Bearer ${tk}` } });
    if (r.status === 401 || r.status === 403) throw new Prohibido();
    if (r.status === 404) throw new NoExiste();
    if (r.status === 429 || r.status >= 500) {
      const espera = Math.min(Number(r.headers.get('retry-after')) || 1, 3);
      await new Promise((ok) => setTimeout(ok, espera * 1000));
      continue;
    }
    if (!r.ok) throw new Error('spotify ' + r.status);
    return r.json();
  }
  throw new Error('spotify ocupado');
}

// Lee desde `desde` hasta acabar o hasta que se agote el tiempo; devuelve el punto donde seguir.
async function trozo(pedir, tk, base, por, desde, reloj) {
  const canciones = [];
  let offset = desde;
  let total = null;
  while (true) {
    const p = await api(pedir, `${base}?limit=${por}&offset=${offset}`, tk);
    canciones.push(...pistasDePagina(p));
    total = Number.isFinite(p.total) ? p.total : total;
    offset += (p.items || []).length || por;
    if (!p.next || !(p.items || []).length) return { canciones, siguiente: null, total };
    if (Date.now() - reloj > PRESUPUESTO_MS) return { canciones, siguiente: offset, total };
  }
}

const JSON_SIN_CACHE = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' };
const responder = (d) => new Response(JSON.stringify(d), { status: 200, headers: JSON_SIN_CACHE });
const fallo = (error, mensaje) => responder({ error, mensaje });

export function crearManejador(pedir = (...a) => globalThis.fetch(...a), env = process.env) {
  return async (req) => {
    if (req.method !== 'GET') return new Response('Solo GET', { status: 405 });
    const q = new URL(req.url).searchParams;
    const tipo = q.get('tipo') || '';
    const id = q.get('id') || '';
    const desde = Math.max(0, parseInt(q.get('desde') || '0', 10) || 0);
    if (!['playlist', 'album', 'track'].includes(tipo) || !/^[A-Za-z0-9]{10,40}$/.test(id)) {
      return fallo('enlace', 'Ese enlace de Spotify no es de una lista, un álbum ni una canción.');
    }
    const reloj = Date.now();
    let tk;
    try {
      tk = await pedirToken(pedir, env);
    } catch {
      return fallo('spotify', 'No se pudo conectar con Spotify.');
    }
    if (!tk) return fallo('sin_credenciales', 'La conexión con Spotify aún no está activada en Caudal.');
    try {
      if (tipo === 'track') {
        const t = await api(pedir, `${API}/tracks/${id}`, tk);
        return responder({ titulo: limpiar(t.name), autor: cancion(t).artista, portada: ((t.album || {}).images || [{}])[0]?.url || '', canciones: [cancion(t)], siguiente: null, total: 1 });
      }
      let cab = {};
      if (desde === 0) {
        const c = await api(pedir, `${API}/${tipo}s/${id}`, tk);
        cab = {
          titulo: limpiar(c.name),
          autor: tipo === 'album' ? (c.artists || []).map((a) => limpiar(a.name)).join(', ') : limpiar((c.owner || {}).display_name),
          portada: ((c.images || [])[0] || {}).url || '',
        };
      }
      let r;
      if (tipo === 'album') {
        r = await trozo(pedir, tk, `${API}/albums/${id}/tracks`, 50, desde, reloj);
      } else {
        try {
          r = await trozo(pedir, tk, `${API}/playlists/${id}/items`, 50, desde, reloj);
        } catch (e) {
          if (!(e instanceof Prohibido)) throw e;
          // la ruta de siempre: solo contesta a las apps con cuota ampliada
          r = await trozo(pedir, tk, `${API}/playlists/${id}/tracks`, 100, desde, reloj);
        }
      }
      return responder({ ...cab, ...r });
    } catch (e) {
      if (e instanceof Prohibido) return fallo('lista_ajena', 'Spotify no deja leer las canciones de listas de otras personas.');
      if (e instanceof NoExiste) return fallo('no_existe', 'Esa lista no existe o es privada.');
      return fallo('spotify', 'Spotify no contestó bien. Prueba otra vez en un rato.');
    }
  };
}

export default crearManejador();

export const config = { path: '/api/spotify' };
