// Vincular Spotify, YouTube o SoundCloud con Caudal (OAuth oficial, con PKCE).
//
//   GET  /api/vincular?code=…&state=<plataforma>-<servicio>-<azar>
//        La vuelta del navegador (redirect_uri de los tres servicios). Devuelve a la app que lo
//        pidió, que es la única que tiene el verificador de PKCE: sin él el código no sirve.
//          a = app del teléfono · e = escritorio · w = la web
//   POST /api/vincular { servicio, code, verificador } | { servicio, refresh }
//        -> { access, refresh, caduca_en } o { error, mensaje }
//        Solo YouTube y SoundCloud, que exigen un secreto. Aquí no se guarda nada: los permisos
//        de cada persona viven solo en su dispositivo.
//
// Variables del sitio: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, SOUNDCLOUD_CLIENT_ID,
// SOUNDCLOUD_CLIENT_SECRET.

export const VUELTA = 'https://caudal-musica.netlify.app/api/vincular';
const SERVICIOS = {
  youtube: { token: 'https://oauth2.googleapis.com/token', env: 'YOUTUBE' },
  soundcloud: { token: 'https://secure.soundcloud.com/oauth/token', env: 'SOUNDCLOUD' },
};
const NOMBRE = { youtube: 'YouTube', soundcloud: 'SoundCloud', spotify: 'Spotify' };
const VUELTAS = {
  a: 'caudal://vincular',
  e: 'http://127.0.0.1:43821/vincular',
  w: 'https://caudal-musica.netlify.app/app/',
};

// A dónde se vuelve (siempre uno de los tres destinos fijos), o '' si el estado no es nuestro.
export function destino(q) {
  const m = /^([aew])-(spotify|youtube|soundcloud)-[A-Za-z0-9._~-]{10,200}$/.exec(q.get('state') || '');
  if (!m) return '';
  const v = new URLSearchParams({ servicio: m[2], state: q.get('state') });
  for (const k of ['code', 'error']) if (q.get(k)) v.set(k, q.get(k).slice(0, 2000));
  if (m[1] === 'w') return `${VUELTAS.w}?vincular=1&${v}`;
  return `${VUELTAS[m[1]]}?${v}`;
}

const json = (d, estado = 200) => Response.json(d, { status: estado, headers: { 'cache-control': 'no-store' } });
const texto = (v) => (typeof v === 'string' && v.length <= 4000 ? v.trim() : '');

export function manejador(pedir = fetch, env = process.env) {
  return async (req) => {
    if (req.method === 'GET') {
      const a = destino(new URL(req.url).searchParams);
      if (!a) return new Response('Este enlace solo sirve para vincular una cuenta desde Caudal.', { status: 400, headers: { 'content-type': 'text/plain; charset=utf-8' } });
      return new Response(null, { status: 302, headers: { location: a, 'cache-control': 'no-store', 'referrer-policy': 'no-referrer' } });
    }
    if (req.method !== 'POST') return new Response('Solo GET o POST', { status: 405 });
    let d;
    try {
      d = await req.json();
    } catch {
      return json({ error: 'datos', mensaje: 'No llegaron los datos para vincular.' }, 400);
    }
    const s = Object.hasOwn(SERVICIOS, d?.servicio) ? SERVICIOS[d.servicio] : null;
    if (!s) return json({ error: 'servicio', mensaje: 'Ese servicio no se puede vincular.' }, 400);
    const nombre = NOMBRE[d.servicio];
    const id = String(env[`${s.env}_CLIENT_ID`] || '').trim();
    const secreto = String(env[`${s.env}_CLIENT_SECRET`] || '').trim();
    if (!id || !secreto) return json({ error: 'sin_credenciales', mensaje: `La conexión con ${nombre} aún no está activada en Caudal.` });
    const code = texto(d.code);
    const verificador = texto(d.verificador);
    const refresh = texto(d.refresh);
    const cuerpo = new URLSearchParams({ client_id: id, client_secret: secreto });
    if (code && verificador) {
      cuerpo.set('grant_type', 'authorization_code');
      cuerpo.set('code', code);
      cuerpo.set('code_verifier', verificador);
      cuerpo.set('redirect_uri', VUELTA);
    } else if (refresh) {
      cuerpo.set('grant_type', 'refresh_token');
      cuerpo.set('refresh_token', refresh);
    } else {
      return json({ error: 'datos', mensaje: 'Faltan datos para vincular.' }, 400);
    }
    try {
      const r = await pedir(s.token, {
        method: 'POST',
        headers: { 'content-type': 'application/x-www-form-urlencoded', accept: 'application/json; charset=utf-8' },
        body: cuerpo.toString(),
      });
      const t = await r.json().catch(() => ({}));
      if (r.ok && t.access_token) return json({ access: t.access_token, refresh: t.refresh_token || '', caduca_en: Number(t.expires_in) || 3600 });
      // el permiso ya no vale (se quitó o caducó): hay que volver a vincular. Lo demás es pasajero.
      if (r.status === 400 || r.status === 401) return json({ error: 'caducado', mensaje: `${nombre} pide que vuelvas a vincular tu cuenta.` });
      return json({ error: 'servicio', mensaje: `${nombre} no contestó bien. Prueba otra vez en un rato.` });
    } catch {
      return json({ error: 'servicio', mensaje: `No se pudo hablar con ${nombre}. Prueba otra vez en un rato.` });
    }
  };
}

export default manejador();
export const config = { path: '/api/vincular' };
