// Qué conexiones oficiales tiene activadas Caudal (lo público, nunca los secretos).
//
//   GET /api/servicios  ->  { spotify_client_id, spotify, soundcloud }
//
// Un solo sitio de configuración para las dos apps: las variables de entorno del sitio
// de Netlify (Site configuration › Environment variables):
//   SPOTIFY_CLIENT_ID         la app de developer.spotify.com. Es público en el flujo PKCE
//                             («conectar tu cuenta»), por eso se entrega aquí.
//   SPOTIFY_CLIENT_SECRET     secreto de esa app: solo lo usa /api/spotify, nunca sale.
//   SOUNDCLOUD_CLIENT_ID      la app de soundcloud.com/you/apps
//   SOUNDCLOUD_CLIENT_SECRET  su secreto: solo lo usa /api/soundcloud.

export function configuracion(env = process.env) {
  const v = (k) => String(env[k] || '').trim();
  return {
    spotify_client_id: v('SPOTIFY_CLIENT_ID'),
    spotify: Boolean(v('SPOTIFY_CLIENT_ID') && v('SPOTIFY_CLIENT_SECRET')),
    soundcloud: Boolean(v('SOUNDCLOUD_CLIENT_ID') && v('SOUNDCLOUD_CLIENT_SECRET')),
  };
}

export default async (req) => {
  if (req.method !== 'GET') return new Response('Solo GET', { status: 405 });
  return Response.json(configuracion(), { headers: { 'cache-control': 'public, max-age=300' } });
};

export const config = { path: '/api/servicios' };
