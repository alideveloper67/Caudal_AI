// Qué conexiones oficiales tiene activadas Caudal (lo público, nunca los secretos).
//
//   GET /api/servicios  ->  { spotify_client_id, spotify, soundcloud, soundcloud_client_id, youtube_client_id }
//
// Un solo sitio de configuración para las dos apps: las variables de entorno del sitio
// de Netlify (Site configuration › Environment variables):
//   SPOTIFY_CLIENT_ID         la app de developer.spotify.com. Es público en el flujo PKCE
//                             («conectar tu cuenta»), por eso se entrega aquí.
//   SPOTIFY_CLIENT_SECRET     secreto de esa app: solo lo usa /api/spotify, nunca sale.
//   SOUNDCLOUD_CLIENT_ID      la app de soundcloud.com/you/apps
//   SOUNDCLOUD_CLIENT_SECRET  su secreto: lo usan /api/soundcloud y /api/vincular.
//   YOUTUBE_CLIENT_ID         cliente «Aplicación web» de console.cloud.google.com con la YouTube Data API
//   YOUTUBE_CLIENT_SECRET     su secreto: solo lo usa /api/vincular.
// En los tres, la dirección de vuelta (redirect URI) es https://caudal-musica.netlify.app/api/vincular

export function configuracion(env = process.env) {
  const v = (k) => String(env[k] || '').trim();
  return {
    spotify_client_id: v('SPOTIFY_CLIENT_ID'),
    spotify: Boolean(v('SPOTIFY_CLIENT_ID') && v('SPOTIFY_CLIENT_SECRET')),
    soundcloud: Boolean(v('SOUNDCLOUD_CLIENT_ID') && v('SOUNDCLOUD_CLIENT_SECRET')),
    // los id son públicos en OAuth; solo se dan si también está su secreto (si no, no serviría)
    soundcloud_client_id: v('SOUNDCLOUD_CLIENT_SECRET') ? v('SOUNDCLOUD_CLIENT_ID') : '',
    youtube_client_id: v('YOUTUBE_CLIENT_SECRET') ? v('YOUTUBE_CLIENT_ID') : '',
  };
}

export default async (req) => {
  if (req.method !== 'GET') return new Response('Solo GET', { status: 405 });
  return Response.json(configuracion(), { headers: { 'cache-control': 'public, max-age=300' } });
};

export const config = { path: '/api/servicios' };
