// Página pública de una lista compartida de Caudal.
//
//   GET /l/K7M2-9QXP   (con o sin guion, en mayúsculas o minúsculas)
//
// Lee la vista previa con la función de base de datos ver_lista_codigo (clave pública del proyecto, la misma de la app)
// y devuelve una página HTML completa, con etiquetas para que WhatsApp y las redes muestren vista previa.
// Todo texto que viene de la base se escapa antes de ponerlo en el HTML.

const SUPABASE = 'https://nztirmwqykbxadidpzzt.supabase.co';
// Pública por diseño: es la misma constante que está en app/lib/nucleo/nube.dart (clavePublica).
const CLAVE_PUBLICA = 'sb_publishable_ga4gKRk0czj044G-xPptSQ_BZ_sTZLl';
const SITIO = 'https://caudal-musica.netlify.app';
const ICONO = SITIO + '/icono.png';
const DESCARGA = SITIO + '/#descargar';
const ALFABETO = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';

export const escapar = (t) =>
  String(t ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

// Mayúsculas, sin espacios ni guiones. Devuelve '' si no tiene la forma de un código (8 caracteres del alfabeto).
export function normalizarCodigo(crudo) {
  let c = '';
  try { c = decodeURIComponent(String(crudo ?? '')); } catch { c = String(crudo ?? ''); }
  c = c.toUpperCase().replace(/[\s-]+/g, '');
  if (c.length !== 8) return '';
  for (const ch of c) if (!ALFABETO.includes(ch)) return '';
  return c;
}
const conGuion = (c) => c.slice(0, 4) + '-' + c.slice(4);

// Solo se aceptan carátulas https (nunca javascript: ni data:).
const urlSegura = (u) => (typeof u === 'string' && /^https:\/\/[^\s"'<>]+$/i.test(u) ? u : '');

const ESTILO = `
:root{--fondo:#061A2B;--panel:#0B2740;--superficie:#0F2D47;--superficie2:#13344F;--borde:rgba(143,167,184,.22);--texto:#F3F5F9;--texto2:#C6D6E0;--texto3:#8FA7B8;--acento:#2FD4F0;--acento-alto:#67E8F9;--acento-texto:#061A2B;--violeta:#7C5CFF}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;color:var(--texto);font-family:"Figtree",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased;
background:radial-gradient(900px 500px at 15% -10%,rgba(124,92,255,.25),transparent 60%),radial-gradient(800px 500px at 100% 0,rgba(47,212,240,.18),transparent 60%),var(--fondo)}
a{color:var(--acento);text-decoration:none}
.cab{display:flex;align-items:center;gap:10px;width:min(720px,100% - 32px);margin:0 auto;padding:18px 0}
.cab a{display:flex;align-items:center;gap:10px;color:var(--texto);font-family:"Bricolage Grotesque","Figtree",sans-serif;font-weight:800;font-size:20px;letter-spacing:-.4px}
.cab img{width:34px;height:34px;border-radius:9px}
main{width:min(720px,100% - 32px);margin:0 auto;padding-bottom:48px}
.tarjeta{background:linear-gradient(180deg,var(--panel),var(--superficie));border:1px solid var(--borde);border-radius:22px;padding:24px}
.etq{display:inline-block;font-size:13px;font-weight:700;color:var(--acento-alto);background:rgba(47,212,240,.12);border:1px solid rgba(47,212,240,.3);padding:4px 12px;border-radius:999px}
.etq.sola{color:var(--texto2);background:rgba(143,167,184,.12);border-color:var(--borde)}
h1{font-family:"Bricolage Grotesque","Figtree",sans-serif;font-size:clamp(28px,7vw,42px);line-height:1.1;letter-spacing:-.8px;margin:14px 0 6px;overflow-wrap:anywhere}
.desc{color:var(--texto2);margin:0 0 10px;overflow-wrap:anywhere}
.meta{display:flex;align-items:center;gap:10px;color:var(--texto2);font-size:15px;flex-wrap:wrap}
.meta img,.meta .av{width:28px;height:28px;border-radius:50%;object-fit:cover;background:var(--superficie2)}
.canciones{list-style:none;margin:20px 0 0;padding:0;display:grid;gap:8px}
.canciones li{display:flex;align-items:center;gap:12px;background:rgba(6,26,43,.45);border:1px solid var(--borde);border-radius:14px;padding:8px 12px 8px 8px;min-width:0}
.car{flex:none;width:48px;height:48px;border-radius:10px;background:linear-gradient(135deg,var(--violeta),var(--acento));object-fit:cover}
.txt{min-width:0}
.txt b{display:block;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.txt span{display:block;color:var(--texto3);font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mas{color:var(--texto3);font-size:14px;margin:10px 4px 0}
.codigo{margin-top:22px;text-align:center;padding:18px;border:1px dashed var(--borde);border-radius:18px}
.codigo small{display:block;color:var(--texto3);font-size:13px;margin-bottom:6px}
.codigo output{display:block;font-family:"JetBrains Mono",ui-monospace,Consolas,monospace;font-weight:500;font-size:clamp(30px,10vw,44px);letter-spacing:.08em;user-select:all}
.acc{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.boton{flex:1 1 200px;display:inline-flex;justify-content:center;align-items:center;gap:8px;padding:14px 22px;border-radius:999px;background:var(--acento);color:var(--acento-texto)!important;font:800 16px "Figtree",sans-serif;border:0;cursor:pointer;text-align:center}
.boton:hover{background:var(--acento-alto)}
.boton.sec{background:var(--superficie2);color:var(--texto)!important;border:1px solid var(--borde)}
.boton.sec:hover{background:var(--superficie)}
.pasos{margin:26px 0 0;padding:0;list-style:none;display:grid;gap:12px;counter-reset:p}
.pasos li{counter-increment:p;display:flex;gap:12px;color:var(--texto2)}
.pasos li::before{content:counter(p);flex:none;width:28px;height:28px;border-radius:50%;background:var(--superficie2);border:1px solid var(--borde);display:grid;place-items:center;font-weight:800;color:var(--acento)}
.pie{text-align:center;color:var(--texto3);font-size:13px;margin-top:22px}
.vacio{text-align:center;padding:40px 24px}
.vacio h1{margin-top:4px}
@media(max-width:420px){.tarjeta{padding:18px}}
`;

const FUENTES = 'https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Figtree:wght@400;600;700;800&family=JetBrains+Mono:wght@500&display=swap';

function marco({ titulo, descripcion, imagen, url, cuerpo }) {
  const t = escapar(titulo), d = escapar(descripcion), i = escapar(imagen || ICONO), u = escapar(url || SITIO);
  return `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#061A2B">
<title>${t}</title>
<meta name="description" content="${d}">
<meta property="og:site_name" content="Caudal">
<meta property="og:type" content="website">
<meta property="og:locale" content="es_PE">
<meta property="og:title" content="${t}">
<meta property="og:description" content="${d}">
<meta property="og:image" content="${i}">
<meta property="og:url" content="${u}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="${t}">
<meta name="twitter:description" content="${d}">
<meta name="twitter:image" content="${i}">
<link rel="icon" href="${SITIO}/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="${FUENTES}" rel="stylesheet">
<style>${ESTILO}</style>
</head>
<body>
<header class="cab"><a href="${SITIO}/"><img src="${SITIO}/icono.png" alt="" width="34" height="34">Caudal</a></header>
<main>
${cuerpo}
</main>
</body>
</html>`;
}

const pl = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;

export function paginaLista(datos, codigo) {
  const nombre = String(datos.nombre || 'Lista sin nombre');
  const total = Math.max(0, Number(datos.total) || 0);
  const colab = datos.rol === 'colaborador';
  const dueno = datos.dueno || {};
  const nombreDueno = String(dueno.nombre || dueno.usuario || 'Alguien');
  const canciones = Array.isArray(datos.canciones) ? datos.canciones.filter((c) => c && typeof c === 'object') : [];
  const primera = canciones.map((c) => urlSegura(c.miniatura)).find(Boolean) || '';
  const foto = urlSegura(dueno.foto_url);
  const mostrado = conGuion(codigo);
  const directo = `caudal://lista?codigo=${codigo}`;

  const titulo = `Lista «${nombre}» en Caudal`;
  const descripcion = `${pl(total, 'canción', 'canciones')} · de ${nombreDueno}. ` + (colab ? 'Puedes añadir canciones. ' : 'Para escuchar. ') + 'Ábrela en Caudal con el código ' + mostrado + '.';

  const filas = canciones.slice(0, 6).map((c) => {
    const img = urlSegura(c.miniatura);
    return `<li>${img ? `<img class="car" src="${escapar(img)}" alt="" loading="lazy" width="48" height="48">` : '<span class="car"></span>'}<div class="txt"><b>${escapar(c.titulo || 'Sin título')}</b><span>${escapar(c.artista || '')}</span></div></li>`;
  }).join('\n');
  const restantes = total - Math.min(canciones.length, 6);

  const cuerpo = `<section class="tarjeta">
<span class="etq${colab ? '' : ' sola'}">${colab ? 'Puedes añadir canciones' : 'Solo para escuchar'}</span>
<h1>${escapar(nombre)}</h1>
${datos.descripcion ? `<p class="desc">${escapar(datos.descripcion)}</p>` : ''}
<div class="meta">${foto ? `<img src="${escapar(foto)}" alt="" width="28" height="28">` : '<span class="av"></span>'}<span>De <b>${escapar(nombreDueno)}</b> · ${escapar(pl(total, 'canción', 'canciones'))}</span></div>
${filas ? `<ul class="canciones">\n${filas}\n</ul>` : ''}
${restantes > 0 && filas ? `<p class="mas">y ${escapar(pl(restantes, 'canción más', 'canciones más'))}</p>` : ''}
<div class="codigo"><small>Código de la lista</small><output id="cod">${escapar(mostrado)}</output></div>
<div class="acc">
<a class="boton" href="${escapar(directo)}">Abrir en Caudal</a>
<a class="boton sec" href="${DESCARGA}">Descargar Caudal</a>
<button class="boton sec" type="button" id="copiar">Copiar código</button>
</div>
<ol class="pasos">
<li><span><b>Descarga Caudal</b> si todavía no lo tienes. Es gratis y no lleva anuncios.</span></li>
<li><span>Toca <b>«Abrir en Caudal»</b>, o en la app entra a Biblioteca y elige <b>«Tengo un código»</b>.</span></li>
<li><span>Escribe o pega el código <b>${escapar(mostrado)}</b> y toca <b>«Unirme»</b>. La lista aparecerá en tu biblioteca.</span></li>
</ol>
</section>
<p class="pie">Esta página es privada: solo la ve quien recibió el enlace.</p>
<script>
(function(){var b=document.getElementById('copiar');if(!b)return;b.addEventListener('click',function(){
var t=${JSON.stringify(mostrado).replace(/</g, '\\u003c')};
function listo(){b.textContent='¡Copiado!';setTimeout(function(){b.textContent='Copiar código'},1800)}
if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(listo,function(){})}
else{var r=document.createRange();r.selectNodeContents(document.getElementById('cod'));var s=getSelection();s.removeAllRanges();s.addRange(r);try{document.execCommand('copy');listo()}catch(e){}}
})})();
</script>`;

  return marco({ titulo, descripcion, imagen: primera, url: `${SITIO}/l/${mostrado}`, cuerpo });
}

export function paginaNoDisponible(motivo = 'ausente') {
  const caida = motivo === 'error';
  const titulo = caida ? 'No pudimos cargar la lista' : 'Esta lista ya no está disponible';
  const texto = caida
    ? 'Algo falló al buscar la lista. Prueba de nuevo en unos minutos.'
    : 'El enlace puede estar mal escrito o quien la compartió dejó de compartirla. Pídele que te envíe un enlace nuevo.';
  const cuerpo = `<section class="tarjeta vacio">
<h1>${escapar(titulo)}</h1>
<p class="desc">${escapar(texto)}</p>
<div class="acc"><a class="boton" href="${SITIO}/">Ir al inicio de Caudal</a></div>
</section>`;
  return marco({ titulo: titulo + ' · Caudal', descripcion: texto, imagen: ICONO, url: SITIO, cuerpo });
}

const CABECERAS = { 'content-type': 'text/html; charset=utf-8', 'x-robots-tag': 'noindex, nofollow' };

// Pide la vista previa. Devuelve el objeto, o null si no existe; lanza si hay un fallo de red o del servidor.
async function pedirLista(codigo, pedir) {
  const r = await pedir(`${SUPABASE}/rest/v1/rpc/ver_lista_codigo`, {
    method: 'POST',
    headers: { apikey: CLAVE_PUBLICA, Authorization: `Bearer ${CLAVE_PUBLICA}`, 'content-type': 'application/json' },
    body: JSON.stringify({ p_codigo: codigo }),
  });
  if (!r.ok) throw new Error('Supabase ' + r.status);
  const d = await r.json();
  return d && typeof d === 'object' && !Array.isArray(d) ? d : null;
}

// Se puede inyectar el fetch para probar sin red.
export function crearManejador(pedir = (...a) => globalThis.fetch(...a)) {
  return async (req, contexto) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') return new Response('Método no permitido', { status: 405 });
    const ruta = new URL(req.url).pathname;
    const crudo = (contexto && contexto.params && contexto.params['0']) || ruta.replace(/^\/l\//, '').split('/')[0];
    const codigo = normalizarCodigo(crudo);
    const sin = (cuerpo, status, cache) => new Response(req.method === 'HEAD' ? null : cuerpo, { status, headers: { ...CABECERAS, 'cache-control': cache } });
    if (!codigo) return sin(paginaNoDisponible('ausente'), 404, 'public, max-age=60');
    try {
      const datos = await pedirLista(codigo, pedir);
      if (!datos) return sin(paginaNoDisponible('ausente'), 404, 'public, max-age=30');
      return sin(paginaLista(datos, codigo), 200, 'public, max-age=60');
    } catch {
      return sin(paginaNoDisponible('error'), 502, 'no-store');
    }
  };
}

export default crearManejador();

export const config = { path: '/l/*' };
