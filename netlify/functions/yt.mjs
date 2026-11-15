// Catálogo de YouTube Music para la versión web de Caudal.
//
// El navegador no puede consultar YouTube Music directamente (no acepta
// peticiones de otras webs). Esta función reenvía SOLO las consultas de
// catálogo que hace la app (buscar, explorar, listas, la cola de una canción,
// sugerencias): nunca el audio, que suena con el reproductor oficial.
//
//   POST /api/yt?m=search&d=music      cuerpo: el mismo JSON que manda la app

const PERMITIDOS = new Set(['search', 'browse', 'next', 'music/get_search_suggestions', 'music/get_queue']);
const DOMINIOS = { music: 'https://music.youtube.com', www: 'https://www.youtube.com' };
const AGENTE = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

export default async (req) => {
  if (req.method !== 'POST') return new Response('Solo POST', { status: 405 });
  const u = new URL(req.url);
  const metodo = u.searchParams.get('m') || '';
  const dominio = DOMINIOS[u.searchParams.get('d') || 'music'];
  if (!PERMITIDOS.has(metodo) || !dominio) return new Response('Consulta no permitida', { status: 400 });
  const extra = (u.searchParams.get('extra') || '').replace(/[^\w=&%.-]/g, '');
  const cuerpo = await req.text();
  if (cuerpo.length > 20000) return new Response('Demasiado grande', { status: 413 });
  const cabeceras = {
    'user-agent': AGENTE,
    accept: '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/json',
    origin: dominio,
    'x-origin': dominio,
    referer: `${dominio}/`,
  };
  const visitante = req.headers.get('x-goog-visitor-id');
  if (visitante && /^[\w%=-]{10,200}$/.test(visitante)) cabeceras['x-goog-visitor-id'] = visitante;
  try {
    const r = await fetch(`${dominio}/youtubei/v1/${metodo}?prettyPrint=false${extra}`, {
      method: 'POST', headers: cabeceras, body: cuerpo,
    });
    return new Response(await r.text(), {
      status: r.status,
      headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'public, max-age=120' },
    });
  } catch (e) {
    return Response.json({ error: { message: String(e) } }, { status: 502 });
  }
};

export const config = { path: '/api/yt' };
