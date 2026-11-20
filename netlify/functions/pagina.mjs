// Páginas públicas de listas para «Traer una lista» en la versión web.
// Solo deja leer las páginas de listas de Spotify (embed), Apple Music y las listas de SoundCloud.
//
//   GET /api/pagina?url=https://open.spotify.com/embed/playlist/...

const PERMITIDOS = [
  /^https:\/\/open\.spotify\.com\/embed\/(playlist|album|track)\/[A-Za-z0-9]+/,
  /^https:\/\/music\.apple\.com\//,
  /^https:\/\/soundcloud\.com\/[\w-]+\/sets\/[\w-]+$/,
];
const AGENTE = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

export default async (req) => {
  const url = new URL(req.url).searchParams.get('url') || '';
  if (!PERMITIDOS.some((p) => p.test(url))) return new Response('Enlace no permitido', { status: 400 });
  try {
    const r = await fetch(url, { headers: { 'user-agent': AGENTE, 'accept-language': 'es-ES,es;q=0.9,en;q=0.8' } });
    return new Response(await r.text(), {
      status: r.status,
      headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=600' },
    });
  } catch (e) {
    return new Response(String(e), { status: 502 });
  }
};

export const config = { path: '/api/pagina' };
