// Lógica de la página de la Fiesta (web/fiesta.html), sin tocar la pantalla: se prueba en node
// (netlify/pruebas/fiesta_web.prueba.mjs). La base de datos y sus reglas están en supabase/fiesta.sql.

export const SUPABASE = 'https://nztirmwqykbxadidpzzt.supabase.co';
// Pública por diseño: la misma de app/lib/nucleo/nube.dart (clavePublica) y de lista.mjs.
export const CLAVE_PUBLICA = 'sb_publishable_ga4gKRk0czj044G-xPptSQ_BZ_sTZLl';
export const ALFABETO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // el de «Escuchar juntos» (sin 0/O ni 1/I)
// filtro «canciones» de la búsqueda de YouTube Music (el mismo de catalogo.dart)
export const FILTRO_CANCIONES = 'EgWKAQIIAWoMEA4QChADEAQQCRAF';

/** Mayúsculas, sin espacios ni guiones; '' si no son 6 caracteres del alfabeto. */
export function normalizarCodigo(crudo) {
  let c = '';
  try { c = decodeURIComponent(String(crudo ?? '')); } catch { c = String(crudo ?? ''); }
  c = c.toUpperCase().replace(/[\s-]+/g, '');
  if (c.length !== 6) return '';
  for (const ch of c) if (!ALFABETO.includes(ch)) return '';
  return c;
}

/** El código de la dirección: /fiesta/ABC234, /fiesta.html?c=ABC234 o ?codigo=… */
export function codigoDeDireccion(url) {
  let u;
  try { u = new URL(url); } catch { return ''; }
  const q = u.searchParams.get('c') || u.searchParams.get('codigo') || u.searchParams.get('fiesta');
  if (q) return normalizarCodigo(q);
  const m = u.pathname.match(/\/fiesta\/([^/?#]+)/i);
  return m ? normalizarCodigo(m[1]) : '';
}

export const enlaceFiesta = (codigo, sitio = 'https://caudal-musica.netlify.app') => `${sitio}/fiesta/${codigo}`;

/** Token al azar del invitado (32 caracteres base64url); `azar(n)` da n bytes. */
export function nuevoToken(azar) {
  const b = azar(24);
  const abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
  let t = '';
  for (let i = 0; i < b.length; i += 3) {
    const n = (b[i] << 16) | ((b[i + 1] ?? 0) << 8) | (b[i + 2] ?? 0);
    t += abc[(n >> 18) & 63] + abc[(n >> 12) & 63] + abc[(n >> 6) & 63] + abc[n & 63];
  }
  return t;
}
export const tokenValido = (t) => typeof t === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(t);

// ---------------------------------------------------------------- base de datos
/** Cómo se pide una función de supabase/fiesta.sql: devuelve {url, init} para fetch. */
export function peticionRpc(nombre, parametros) {
  return {
    url: `${SUPABASE}/rest/v1/rpc/${nombre}`,
    init: {
      method: 'POST',
      headers: { apikey: CLAVE_PUBLICA, 'content-type': 'application/json' },
      body: JSON.stringify(parametros),
    },
  };
}

/** El texto que se le enseña a la persona cuando una función falla. */
export function mensajeDeError(status, cuerpo) {
  let d = cuerpo;
  if (typeof cuerpo === 'string') { try { d = JSON.parse(cuerpo); } catch { d = null; } }
  const msg = d && typeof d === 'object' ? String(d.message || '') : '';
  if (d && d.code === 'P0001' && msg) return msg;           // las frases de fiesta.sql, tal cual
  if (d && (d.code === 'PGRST202' || /could not find the function/i.test(msg))) {
    return 'La fiesta todavía no está activa en el servidor de Caudal.';
  }
  if (status === 429) return 'Demasiados intentos seguidos. Espera un momento.';
  if (status >= 500 || status === 0) return 'No pudimos hablar con Caudal. Revisa tu internet y vuelve a probar.';
  return 'Algo falló. Vuelve a intentarlo.';
}

/** Limpia lo que devuelve fiesta_ver (nunca confía en la forma). null si no existe. */
export function leerFiesta(d) {
  if (!d || typeof d !== 'object' || Array.isArray(d)) return null;
  const n = (v, def = 0) => (Number.isFinite(Number(v)) ? Number(v) : def);
  const cancion = (c) => ({
    id: n(c.id), video_id: String(c.video_id || ''), titulo: String(c.titulo || 'Sin título'),
    artista: String(c.artista || ''), miniatura: urlSegura(c.miniatura), duracion: n(c.duracion),
    nombre: String(c.nombre || ''), votos: n(c.votos), estado: String(c.estado || 'cola'),
    mia: c.mia === true, vote: c.vote === true, de_anfitrion: c.de_anfitrion === true,
  });
  const lista = (v) => (Array.isArray(v) ? v.filter((c) => c && typeof c === 'object').map(cancion) : []);
  const s = d.sonando && typeof d.sonando === 'object' ? d.sonando : null;
  return {
    codigo: String(d.codigo || ''), nombre: String(d.nombre || 'Fiesta'), abierta: d.abierta !== false,
    limite: n(d.limite), version: n(d.version), invitados: n(d.invitados), mias: n(d.mias),
    ahora: n(d.ahora, Date.now()),
    sonando: s && {
      video_id: String(s.video_id || ''), titulo: String(s.titulo || ''), artista: String(s.artista || ''),
      miniatura: urlSegura(s.miniatura), duracion: n(s.duracion), pos_ms: n(s.pos_ms), pausa: s.pausa === true,
      t: n(s.t), fiesta_id: s.fiesta_id == null ? null : n(s.fiesta_id), nombre: String(s.nombre || ''),
    },
    cola: ordenarCola(lista(d.cola)),
    sonadas: lista(d.sonadas).filter((c) => c.estado === 'sonada'),
  };
}

/** El orden en que sonarán: más votos primero; a igualdad, la que llegó antes (id menor). */
export function ordenarCola(cola) {
  return [...cola].sort((a, b) => b.votos - a.votos || a.id - b.id);
}

/** Voto «al instante» mientras responde el servidor. */
export function votarLocal(fiesta, id, voto) {
  if (!fiesta) return fiesta;
  const cola = fiesta.cola.map((c) => {
    if (c.id !== id || c.vote === voto) return c;
    return { ...c, vote: voto, votos: Math.max(0, c.votos + (voto ? 1 : -1)) };
  });
  return { ...fiesta, cola: ordenarCola(cola) };
}

/** ¿Cuántas puede añadir todavía? Infinity si no hay límite. */
export function quedan(fiesta) {
  if (!fiesta || !fiesta.abierta) return 0;
  if (!fiesta.limite) return Infinity;
  return Math.max(0, fiesta.limite - fiesta.mias);
}

export function textoQuedan(fiesta) {
  const q = quedan(fiesta);
  if (!fiesta || !fiesta.abierta) return '';
  if (q === Infinity) return 'Puedes pedir todas las que quieras.';
  if (q === 0) return `Ya pediste ${fiesta.limite === 1 ? 'tu canción' : `tus ${fiesta.limite} canciones`}. Ahora toca votar.`;
  return q === 1 ? 'Te queda 1 canción por pedir.' : `Te quedan ${q} canciones por pedir.`;
}

/** ¿Ya está esperando (o sonando) esta canción? */
export function yaEsta(fiesta, videoId) {
  if (!fiesta) return false;
  return fiesta.cola.some((c) => c.video_id === videoId) || (fiesta.sonando && fiesta.sonando.video_id === videoId);
}

/** Por dónde va la canción que suena (ms), con la hora del servidor corregida. */
export function posicionAhora(sonando, ahoraLocal, desfase = 0) {
  if (!sonando) return 0;
  const pos = sonando.pos_ms || 0;
  const tope = sonando.duracion > 0 ? sonando.duracion * 1000 : Infinity;
  if (sonando.pausa) return Math.min(pos, tope);
  return Math.min(tope, pos + Math.max(0, ahoraLocal + desfase - sonando.t));
}

export function duracionTexto(seg) {
  const s = Math.max(0, Math.round(Number(seg) || 0));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = String(s % 60).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${r}` : `${m}:${r}`;
}

export const urlSegura = (u) => (typeof u === 'string' && u.length <= 500 && /^https:\/\/[^\s"'<>]+$/i.test(u) ? u : '');

// ---------------------------------------------------------------- búsqueda (YouTube Music)
/** El cuerpo que se manda a /api/yt?m=search&d=music (la función de Netlify de siempre). */
export function cuerpoBusqueda(texto, ahora = new Date()) {
  const dos = (n) => String(n).padStart(2, '0');
  const fecha = `${ahora.getUTCFullYear()}${dos(ahora.getUTCMonth() + 1)}${dos(ahora.getUTCDate())}`;
  return {
    context: { client: { clientName: 'WEB_REMIX', clientVersion: `1.${fecha}.01.00`, hl: 'es', gl: 'PE' }, user: {} },
    query: String(texto || '').trim().slice(0, 150),
    params: FILTRO_CANCIONES,
  };
}

const ir = (o, ruta) => ruta.reduce((a, k) => (a == null ? undefined : a[k]), o);
const segundos = (t) => {
  const p = String(t || '').trim().split(':');
  if (p.length < 2 || p.some((x) => !/^\d+$/.test(x))) return 0;
  return p.reduce((a, x) => a * 60 + Number(x), 0);
};
const TIPOS = new Set(['song', 'video', 'canción', 'cancion', 'vídeo', 'single', 'ep', 'álbum', 'album']);

/** Agranda las carátulas de googleusercontent (=w544-h544) como hace catalogo.dart. */
export function agrandar(url, lado = 226) {
  let u = String(url || '');
  if (u.startsWith('//')) u = 'https:' + u;
  if (/googleusercontent\.com|ggpht\.com/.test(u)) {
    u = u.replace(/=w\d+-h\d+[^&?]*$/, `=w${lado}-h${lado}-l90-rj`).replace(/=s\d+[^&?]*$/, `=w${lado}-h${lado}-l90-rj`);
  }
  return urlSegura(u);
}

/** Las canciones de una respuesta de búsqueda de YouTube Music: [{video_id, titulo, artista, miniatura, duracion}]. */
export function cancionesDeBusqueda(r, limite = 20) {
  const secciones = ir(r, ['contents', 'tabbedSearchResultsRenderer', 'tabs', 0, 'tabRenderer', 'content', 'sectionListRenderer', 'contents'])
    || ir(r, ['contents', 'sectionListRenderer', 'contents']) || [];
  const salida = [];
  const vistos = new Set();
  for (const s of Array.isArray(secciones) ? secciones : []) {
    const filas = ir(s, ['musicShelfRenderer', 'contents']) || [];
    for (const f of Array.isArray(filas) ? filas : []) {
      const d = f && f.musicResponsiveListItemRenderer;
      if (!d) continue;
      const cols = (d.flexColumns || []).map((c) => ir(c, ['musicResponsiveListItemFlexColumnRenderer', 'text', 'runs']) || []);
      const vid = ir(d, ['playlistItemData', 'videoId'])
        || ir(d, ['overlay', 'musicItemThumbnailOverlayRenderer', 'content', 'musicPlayButtonRenderer', 'playNavigationEndpoint', 'watchEndpoint', 'videoId'])
        || ir(cols, [0, 0, 'navigationEndpoint', 'watchEndpoint', 'videoId']);
      if (typeof vid !== 'string' || !/^[A-Za-z0-9_-]{11}$/.test(vid) || vistos.has(vid)) continue;
      const titulo = (cols[0] || []).map((x) => x.text || '').join('').trim();
      // segunda columna: «Artista & Otro • Álbum • 3:25» (a veces empieza por el tipo)
      const grupos = [[]];
      for (const x of cols[1] || []) {
        if (String(x.text || '').trim() === '•') grupos.push([]);
        else grupos[grupos.length - 1].push(x);
      }
      if (grupos.length > 1 && grupos[0].length === 1 && !grupos[0][0].navigationEndpoint
          && TIPOS.has(String(grupos[0][0].text || '').trim().toLowerCase())) grupos.shift();
      const artista = (grupos[0] || []).map((x) => String(x.text || '')).join('').replace(/\s+/g, ' ').trim();
      let duracion = 0;
      for (const g of grupos) {
        const t = g.map((x) => x.text || '').join('').trim();
        if (/^\d{1,2}(:\d{2}){1,2}$/.test(t)) duracion = segundos(t);
      }
      const miniaturas = ir(d, ['thumbnail', 'musicThumbnailRenderer', 'thumbnail', 'thumbnails']) || [];
      const mejor = [...(Array.isArray(miniaturas) ? miniaturas : [])].sort((a, b) => (b.width || 0) - (a.width || 0))[0];
      vistos.add(vid);
      salida.push({
        video_id: vid, titulo: titulo || 'Sin título', artista, duracion,
        miniatura: (mejor && agrandar(mejor.url)) || `https://i.ytimg.com/vi/${vid}/hqdefault.jpg`,
      });
      if (salida.length >= limite) return salida;
    }
  }
  return salida;
}

// ---------------------------------------------------------------- tiempo real (Phoenix vsn 1.0.0)
export const urlRealtime = () =>
  `${SUPABASE.replace(/^https/, 'wss')}/realtime/v1/websocket?apikey=${encodeURIComponent(CLAVE_PUBLICA)}&vsn=1.0.0`;
export const temaFiesta = (codigo) => `realtime:fiesta-${codigo}`;

export function mensajeUnirse(codigo, ref) {
  return {
    topic: temaFiesta(codigo), event: 'phx_join', ref: String(ref), join_ref: String(ref),
    payload: { config: { broadcast: { self: false, ack: false }, presence: { key: '' }, postgres_changes: [], private: false } },
  };
}
export const mensajeLatido = (ref) => ({ topic: 'phoenix', event: 'heartbeat', payload: {}, ref: String(ref) });
export function mensajeCambio(codigo, ref, joinRef, version) {
  return {
    topic: temaFiesta(codigo), event: 'broadcast', ref: String(ref), join_ref: String(joinRef),
    payload: { type: 'broadcast', event: 'cambio', payload: { version } },
  };
}

/** Qué hacer con un mensaje del websocket: 'cambio' (volver a pedir), 'unido', 'reconectar' o ''. */
export function leerMensaje(texto, codigo) {
  let m;
  try { m = JSON.parse(texto); } catch { return { tipo: '' }; }
  if (!m || m.topic !== temaFiesta(codigo)) return { tipo: '' };
  if (m.event === 'broadcast' && m.payload && m.payload.event === 'cambio') {
    return { tipo: 'cambio', version: Number(ir(m, ['payload', 'payload', 'version'])) || 0 };
  }
  if (m.event === 'phx_reply') return { tipo: ir(m, ['payload', 'status']) === 'ok' ? 'unido' : 'reconectar', ref: m.ref };
  if (m.event === 'phx_error' || m.event === 'phx_close') return { tipo: 'reconectar' };
  return { tipo: '' };
}

export const esperaReconexion = (intento) => [1000, 2000, 4000, 8000, 15000][Math.min(intento, 4)];
