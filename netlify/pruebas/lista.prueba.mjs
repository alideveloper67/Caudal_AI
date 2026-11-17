// Prueba de la página de listas sin red: node netlify/pruebas/lista.prueba.mjs
import assert from 'node:assert/strict';
import { crearManejador, normalizarCodigo, escapar } from '../functions/lista.mjs';

let fallos = 0;
const ok = (c, m) => { if (!c) { fallos++; console.log('  FALLA:', m); } else console.log('  ok:', m); };

const LISTA = {
  nombre: 'Mis favoritas', descripcion: 'Para el viaje', total: 12, rol: 'colaborador', miembros: 3,
  dueno: { usuario: 'ana', nombre: 'Ana Pérez', foto_url: 'https://x.test/ana.jpg' },
  canciones: [
    { titulo: 'Canción uno', artista: 'Artista A', miniatura: 'https://img.test/1.jpg' },
    { titulo: 'Canción dos', artista: 'Artista B', miniatura: null },
  ],
};

// fetch falso: guarda la última llamada
function falso(respuesta) {
  const f = async (url, init) => { f.url = url; f.init = init; f.llamadas++; return typeof respuesta === 'function' ? respuesta() : respuesta; };
  f.llamadas = 0;
  return f;
}
const json = (d, status = 200) => new Response(JSON.stringify(d), { status, headers: { 'content-type': 'application/json' } });
const pedir = (f, ruta, metodo = 'GET') => crearManejador(f)(new Request('https://x.test' + ruta, { method: metodo }));

// lista válida
let f = falso(json(LISTA));
let r = await pedir(f, '/l/K7M2-9QXP');
let h = await r.text();
ok(r.status === 200, 'lista válida: 200');
ok(f.url.endsWith('/rest/v1/rpc/ver_lista_codigo'), 'llama a ver_lista_codigo');
ok(JSON.parse(f.init.body).p_codigo === 'K7M29QXP', 'manda el código normalizado');
ok(f.init.method === 'POST' && f.init.headers.apikey && f.init.headers.Authorization === 'Bearer ' + f.init.headers.apikey, 'manda apikey y Authorization');
ok(/Mis favoritas/.test(h) && /Ana Pérez/.test(h) && /12 canciones/.test(h), 'muestra nombre, dueño y cantidad');
ok(/Canción uno/.test(h) && /Artista B/.test(h) && /img\.test\/1\.jpg/.test(h), 'muestra canciones y carátulas');
ok(/Puedes añadir canciones/.test(h), 'dice que es colaborativa');
ok(/K7M2-9QXP/.test(h), 'código grande con guion');
ok(/href="caudal:\/\/lista\?codigo=K7M29QXP"/.test(h), 'botón Abrir en Caudal (caudal://lista?codigo=)');
ok(/Abrir en Caudal/.test(h) && /Descargar Caudal/.test(h) && /#descargar/.test(h), 'botones Abrir y Descargar');
ok(/property="og:title" content="Lista «Mis favoritas» en Caudal"/.test(h), 'og:title');
ok(/property="og:description" content="[^"]*12 canciones/.test(h), 'og:description con cantidad');
ok(/property="og:image" content="https:\/\/img\.test\/1\.jpg"/.test(h), 'og:image = primera carátula');
ok(/name="twitter:card"/.test(h) && /name="twitter:title"/.test(h) && /name="twitter:image"/.test(h), 'etiquetas Twitter');
ok(/name="robots" content="noindex/.test(h) && /noindex/.test(r.headers.get('x-robots-tag')), 'noindex en meta y cabecera');
ok(/charset=utf-8/.test(r.headers.get('content-type')), 'content-type html utf-8');
ok(/<ol class="pasos">[\s\S]*<li>[\s\S]*<li>[\s\S]*<li>/.test(h), 'explicación de 3 pasos');

// solo para escuchar, sin carátulas: imagen = icono
f = falso(json({ ...LISTA, rol: 'oyente', total: 1, canciones: [{ titulo: 'x', artista: 'y' }] }));
h = await (await pedir(f, '/l/K7M29QXP')).text();
ok(/Solo para escuchar/.test(h) && !/Puedes añadir canciones/.test(h.replace(/<meta[^>]*>/g, '')), 'oyente: solo para escuchar');
ok(/og:image" content="https:\/\/caudal-musica\.netlify\.app\/icono\.png"/.test(h), 'sin carátulas: og:image = icono');
ok(/1 canción\b/.test(h), 'singular «1 canción»');

// minúsculas y guion
f = falso(json(LISTA));
r = await pedir(f, '/l/k7m2-9qxp');
ok(r.status === 200 && JSON.parse(f.init.body).p_codigo === 'K7M29QXP', 'minúsculas y guion se normalizan');
ok(normalizarCodigo(' k7m2 9qxp ') === 'K7M29QXP', 'normalizarCodigo quita espacios');

// códigos inválidos: ni siquiera llaman a la base
for (const malo of ['', 'ABC', 'K7M2-9QXO', 'K7M2-9QX1', 'K7M2-9QXPZ', '%E0%A4%A']) {
  f = falso(json(LISTA));
  r = await pedir(f, '/l/' + malo);
  ok(r.status === 404 && f.llamadas === 0, `código inválido «${malo}»: 404 sin consultar`);
}

// inexistente
f = falso(json(null));
r = await pedir(f, '/l/K7M2-9QXP');
h = await r.text();
ok(r.status === 404 && /Esta lista ya no está disponible/.test(h) && /href="https:\/\/caudal-musica\.netlify\.app\/"/.test(h), 'inexistente: página amable con enlace al inicio');
ok(/noindex/.test(r.headers.get('x-robots-tag')), 'la página amable también es noindex');

// errores
f = falso(() => { throw new TypeError('fetch failed'); });
r = await pedir(f, '/l/K7M2-9QXP');
h = await r.text();
ok(r.status === 502 && /No pudimos cargar la lista/.test(h) && r.headers.get('cache-control') === 'no-store', 'error de red: página amable 502 sin caché');
f = falso(json({ message: 'boom' }, 500));
r = await pedir(f, '/l/K7M2-9QXP');
ok(r.status === 502, 'error 500 de la base: 502');

// inyección de HTML
const MALA = '"><script>alert(1)</script><img src=x onerror=alert(2)>\'';
f = falso(json({
  nombre: MALA, descripcion: MALA, total: 2, rol: 'colaborador',
  dueno: { usuario: 'x', nombre: MALA, foto_url: 'javascript:alert(3)' },
  canciones: [{ titulo: MALA, artista: '<b>x</b>', miniatura: 'https://img.test/a.jpg"onerror="alert(4)' }, { titulo: 'ok', artista: MALA, miniatura: 'javascript:alert(5)' }],
}));
h = await (await pedir(f, '/l/K7M2-9QXP')).text();
const sinEstilo = h;
ok(!/<script>alert/.test(sinEstilo) && !/<img src=x/.test(sinEstilo) && !/<b>x<\/b>/.test(sinEstilo), 'nombre, canción, artista y dueño con HTML quedan escapados');
ok((h.match(/<script/g) || []).length === 1, 'solo existe el script propio de copiar');
ok(!/<[^>]*on\w+\s*=/i.test(h.replace(/<style>[\s\S]*?<\/style>/, '')), 'ninguna etiqueta real trae atributos on...=');
ok(/&lt;script&gt;alert\(1\)&lt;\/script&gt;/.test(h), 'se ve como texto escapado');
ok(!/javascript:/i.test(h), 'urls javascript: descartadas');
ok(!/a\.jpg"onerror/.test(h), 'url de carátula con comillas descartada');
ok(escapar(`<a href="x">&'`) === '&lt;a href=&quot;x&quot;&gt;&amp;&#39;', 'escapar() cubre < > " & \'');

// método
r = await pedir(falso(json(LISTA)), '/l/K7M2-9QXP', 'POST');
ok(r.status === 405, 'solo GET/HEAD');

console.log(fallos === 0 ? '\nTODO BIEN' : `\n${fallos} PRUEBAS FALLARON`);
process.exit(fallos ? 1 : 0);
