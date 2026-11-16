// Búsqueda de GIF para la foto y el fondo del perfil (donadores y fundadores de Caudal).
//
// La clave de la API vive aquí, en el servidor (variable TENOR_API_KEY o GIPHY_API_KEY), nunca en la app.
// Seguridad de contenido, en tres capas:
//   1) Solo se piden GIF aptos para todo público (Tenor: contentfilter=high; Giphy: rating=g).
//   2) Se rechazan las búsquedas con palabras de contenido para adultos o violento/gore.
//   3) Se descartan los resultados cuyo título o etiquetas tengan esas palabras.
//
//   GET /api/gifs?q=texto            → { items: [...], siguiente }
//   GET /api/gifs                    → los GIF del momento
//   GET /api/gifs?bajar=<url del gif> → el archivo (solo de los servidores de Tenor y Giphy, máx. 6 MB)

// Raíces: bloquean cualquier palabra que EMPIECE así (porn → porno, pornografía...).
const RAICES = [
  'porn', 'xxx', 'nsfw', 'desnud', 'hentai', 'erotic', 'fetish', 'fetiche', 'onlyfans', 'nipple', 'pezon', 'masturb', 'blowjob',
  'orgasm', 'lingerie', 'lenceria', 'topless', 'bdsm', 'camgirl', 'playboy', 'rule34', 'sexual', 'sexo', 'sexy',
  'gore', 'sangr', 'decapit', 'beheading', 'mutil', 'cadaver', 'asesin', 'murder', 'suicid', 'tortur', 'violacion', 'masacre',
  'massacre', 'ejecucion', 'degollar', 'viscera', 'dismember', 'desmembr', 'snuff', 'nazi', 'hitler', 'swastik', 'terroris',
];
// Palabras exactas: se bloquean solo si aparecen enteras (así «cumbia», «cumpleaños» o «analysis» no se bloquean).
const EXACTAS = [
  'sex', 'ass', 'anal', 'cum', 'dick', 'cock', 'pussy', 'butt', 'strip', 'stripper', 'adult', 'adulto', 'adultos', 'culo', 'puta',
  'putas', 'pene', 'penis', 'vagina', 'boob', 'boobs', 'tetas', 'nude', 'nudes', 'naked', 'rape', 'abuse', 'abuso', 'blood',
  'bloody', 'corpse', 'kill', 'killing', 'isis', 'milf', 'lewd', 'kinky', 'escort', 'twerk', 'bikini', 'semen', 'erotico', 'erotica',
  'terror', 'guts', 'entrails', 'mortal kombat', 'dead body', 'tortura', 'torture', '18+',
];

const quitarAcentos = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
const esc = (p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const REGLA_RAIZ = new RegExp('(^|[^a-z0-9])(' + RAICES.map(esc).join('|') + ')', 'i');
const REGLA_EXACTA = new RegExp('(^|[^a-z0-9])(' + EXACTAS.map(esc).join('|') + ')($|[^a-z0-9])', 'i');
const prohibido = (texto) => {
  const t = quitarAcentos(texto);
  return REGLA_RAIZ.test(t) || REGLA_EXACTA.test(t);
};

const HOSTS_BAJAR = /^(media\d*|c|media-\d+)\.tenor\.com$|^media\d*\.giphy\.com$|^i\.giphy\.com$/i;
const MAX_BYTES = 6 * 1024 * 1024;

const json = (datos, estado = 200, cache = 'public, max-age=300') =>
  new Response(JSON.stringify(datos), {
    status: estado,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': cache, 'access-control-allow-origin': '*' },
  });

async function tenor(clave, q, pos) {
  const p = new URLSearchParams({
    key: clave, client_key: 'caudal', contentfilter: 'high', limit: '24', locale: 'es_PE', country: 'PE',
    media_filter: 'tinygif,mediumgif,gif',
  });
  if (q) p.set('q', q);
  if (pos) p.set('pos', pos);
  const r = await fetch(`https://tenor.googleapis.com/v2/${q ? 'search' : 'featured'}?${p}`);
  if (!r.ok) throw new Error('Tenor ' + r.status);
  const d = await r.json();
  const items = [];
  for (const g of d.results || []) {
    const titulo = g.content_description || g.title || '';
    const etiquetas = (g.tags || []).join(' ');
    if (prohibido(titulo) || prohibido(etiquetas)) continue;
    const m = g.media_formats || {};
    const vista = m.tinygif || m.mediumgif || m.gif;
    const grande = m.mediumgif && (m.mediumgif.size || 0) <= MAX_BYTES ? m.mediumgif : (m.gif && (m.gif.size || 0) <= MAX_BYTES ? m.gif : m.tinygif);
    if (!vista || !grande) continue;
    items.push({
      id: g.id, titulo, vista: vista.url, gif: grande.url,
      ancho: (grande.dims || [0, 0])[0], alto: (grande.dims || [0, 0])[1], peso: grande.size || 0,
    });
  }
  return { items, siguiente: d.next || '' };
}

async function giphy(clave, q, pos) {
  const p = new URLSearchParams({ api_key: clave, limit: '24', rating: 'g', lang: 'es', bundle: 'messaging_non_clips' });
  if (q) p.set('q', q);
  if (pos) p.set('offset', pos);
  const r = await fetch(`https://api.giphy.com/v1/gifs/${q ? 'search' : 'trending'}?${p}`);
  if (!r.ok) throw new Error('Giphy ' + r.status);
  const d = await r.json();
  const items = [];
  for (const g of d.data || []) {
    if (String(g.rating || 'g').toLowerCase() !== 'g') continue;
    const titulo = g.title || '';
    if (prohibido(titulo) || prohibido(g.slug || '')) continue;
    const im = g.images || {};
    const vista = im.fixed_width_small || im.fixed_width || im.preview_gif;
    const grande = [im.downsized_medium, im.downsized, im.fixed_width].find((x) => x && x.url && Number(x.size || 0) <= MAX_BYTES);
    if (!vista || !grande) continue;
    items.push({
      id: g.id, titulo, vista: vista.url, gif: grande.url,
      ancho: Number(grande.width || 0), alto: Number(grande.height || 0), peso: Number(grande.size || 0),
    });
  }
  const sig = (d.pagination || {}).offset + (d.pagination || {}).count;
  return { items, siguiente: Number.isFinite(sig) ? String(sig) : '' };
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: { 'access-control-allow-origin': '*' } });
  if (req.method !== 'GET') return new Response('Solo GET', { status: 405 });
  const u = new URL(req.url);

  // descargar un GIF elegido (también sirve para la web, que no puede pedirlo directo por CORS)
  const bajar = u.searchParams.get('bajar');
  if (bajar) {
    let destino;
    try { destino = new URL(bajar); } catch { return new Response('Dirección no válida', { status: 400 }); }
    if (destino.protocol !== 'https:' || !HOSTS_BAJAR.test(destino.hostname)) return new Response('Origen no permitido', { status: 400 });
    const r = await fetch(destino);
    if (!r.ok) return new Response('No se pudo bajar', { status: 502 });
    const largo = Number(r.headers.get('content-length') || 0);
    if (largo > MAX_BYTES) return new Response('Demasiado pesado', { status: 413 });
    const cuerpo = new Uint8Array(await r.arrayBuffer());
    if (cuerpo.length > MAX_BYTES) return new Response('Demasiado pesado', { status: 413 });
    // tiene que ser de verdad un GIF
    const cab = String.fromCharCode(...cuerpo.slice(0, 6));
    if (cab !== 'GIF87a' && cab !== 'GIF89a') return new Response('No es un GIF', { status: 415 });
    return new Response(cuerpo, {
      headers: { 'content-type': 'image/gif', 'cache-control': 'public, max-age=86400', 'access-control-allow-origin': '*' },
    });
  }

  const q = (u.searchParams.get('q') || '').trim().slice(0, 60);
  const pos = (u.searchParams.get('pos') || '').replace(/[^\w.=-]/g, '').slice(0, 60);
  if (q && prohibido(q)) {
    return json({ items: [], siguiente: '', aviso: 'Esa búsqueda no está permitida en Caudal.' }, 200, 'no-store');
  }
  const claveTenor = process.env.TENOR_API_KEY || (typeof Netlify !== 'undefined' ? Netlify.env.get('TENOR_API_KEY') : '');
  const claveGiphy = process.env.GIPHY_API_KEY || (typeof Netlify !== 'undefined' ? Netlify.env.get('GIPHY_API_KEY') : '');
  try {
    if (claveTenor) return json(await tenor(claveTenor, q, pos));
    if (claveGiphy) return json(await giphy(claveGiphy, q, pos));
    return json({ items: [], siguiente: '', error: 'sin_clave' }, 503, 'no-store');
  } catch (e) {
    return json({ items: [], siguiente: '', error: String(e) }, 502, 'no-store');
  }
};

export const config = { path: '/api/gifs' };
