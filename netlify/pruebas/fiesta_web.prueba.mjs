// Prueba de la lógica de la página de la Fiesta (web/fiesta-logica.js) sin red ni navegador:
//   node netlify/pruebas/fiesta_web.prueba.mjs
import { readFileSync } from 'node:fs';
import * as L from '../../web/fiesta-logica.js';

let fallos = 0;
const ok = (c, m) => { if (!c) { fallos++; console.log('  FALLA:', m); } else console.log('  ok:', m); };

// códigos y direcciones
ok(L.normalizarCodigo(' abc-234 ') === 'ABC234', 'normaliza código');
ok(L.normalizarCodigo('ABC23O') === '' && L.normalizarCodigo('ABC2341') === '', 'rechaza O y largo malo');
ok(L.codigoDeDireccion('https://caudal-musica.netlify.app/fiesta/xyz789') === 'XYZ789', 'código en la ruta');
ok(L.codigoDeDireccion('https://caudal-musica.netlify.app/fiesta.html?c=XYZ789') === 'XYZ789', 'código en ?c=');
ok(L.codigoDeDireccion('https://x.test/fiesta') === '', 'sin código');
ok(L.enlaceFiesta('ABC234') === 'https://caudal-musica.netlify.app/fiesta/ABC234', 'enlace del QR');

// token
const t = L.nuevoToken((n) => Uint8Array.from({ length: n }, (_, i) => i * 37 % 256));
ok(t.length === 32 && L.tokenValido(t), 'token de 32 válido');
ok(!L.tokenValido('corto') && !L.tokenValido('con espacios 0123456789'), 'tokens malos');

// peticiones y errores
const p = L.peticionRpc('fiesta_ver', { p_codigo: 'ABC234' });
ok(p.url.endsWith('/rest/v1/rpc/fiesta_ver') && p.init.headers.apikey === L.CLAVE_PUBLICA && !p.init.headers.Authorization, 'rpc con apikey pública');
ok(L.mensajeDeError(400, '{"code":"P0001","message":"Ya añadiste 3 canciones, que es el máximo de esta fiesta."}').startsWith('Ya añadiste 3'), 'frase de la base tal cual');
ok(/todavía no está activa/.test(L.mensajeDeError(404, { code: 'PGRST202', message: 'Could not find the function' })), 'migración sin aplicar');
ok(/internet/.test(L.mensajeDeError(0, null)), 'sin red');
ok(L.mensajeDeError(400, '{"code":"42501","message":"permission denied for table fiestas"}') === 'Algo falló. Vuelve a intentarlo.', 'no enseña errores técnicos');

// leer la fiesta
const crudo = {
  codigo: 'ABC234', nombre: 'Cumple', abierta: true, limite: 2, version: 7, invitados: 3, mias: 1, ahora: 1000,
  sonando: { video_id: 'AAAAAAAAAAA', titulo: 'Suena', artista: 'X', miniatura: 'javascript:1', duracion: 200, pos_ms: 5000, pausa: false, t: 900 },
  cola: [
    { id: 5, video_id: 'BBBBBBBBBBB', titulo: 'B', votos: 1, mia: true },
    { id: 3, video_id: 'CCCCCCCCCCC', titulo: 'C', votos: 1, vote: true },
    { id: 9, video_id: 'DDDDDDDDDDD', titulo: 'D', votos: 4 },
    'basura',
  ],
  sonadas: [{ id: 1, estado: 'sonando', titulo: 'ya' }, { id: 2, estado: 'sonada', titulo: 'antes' }],
};
let f = L.leerFiesta(crudo);
ok(f.cola.map((c) => c.id).join() === '9,3,5', 'cola: más votos primero, a igualdad la más antigua');
ok(f.sonando.miniatura === '' && f.sonando.titulo === 'Suena', 'limpia la carátula insegura');
ok(f.sonadas.length === 1 && f.sonadas[0].id === 2, '«ya sonaron» sin la que suena');
ok(L.leerFiesta(null) === null && L.leerFiesta([]) === null, 'null = no existe');

// votos al instante
let g = L.votarLocal(f, 5, true);
ok(g.cola.find((c) => c.id === 5).votos === 2 && g.cola[1].id === 5, 'votar sube y reordena');
g = L.votarLocal(g, 5, true);
ok(g.cola.find((c) => c.id === 5).votos === 2, 'votar dos veces no suma');
g = L.votarLocal(g, 3, false);
ok(g.cola.find((c) => c.id === 3).votos === 0 && g.cola.at(-1).id === 3, 'quitar voto baja');
ok(f.cola.find((c) => c.id === 5).votos === 1, 'no cambia la original');

// límites
ok(L.quedan(f) === 1 && /Te queda 1 canción/.test(L.textoQuedan(f)), 'queda 1');
ok(L.quedan({ ...f, mias: 2 }) === 0 && /Ahora toca votar/.test(L.textoQuedan({ ...f, mias: 2 })), 'límite alcanzado');
ok(L.quedan({ ...f, limite: 0 }) === Infinity && /todas las que quieras/.test(L.textoQuedan({ ...f, limite: 0 })), 'sin límite');
ok(L.quedan({ ...f, abierta: false }) === 0, 'cerrada: 0');
ok(L.yaEsta(f, 'DDDDDDDDDDD') && L.yaEsta(f, 'AAAAAAAAAAA') && !L.yaEsta(f, 'ZZZZZZZZZZZ'), 'ya está en la cola o sonando');

// lo que suena
ok(L.posicionAhora(f.sonando, 2000, 0) === 6100, 'posición avanza con el reloj');
ok(L.posicionAhora({ ...f.sonando, pausa: true }, 99999, 0) === 5000, 'en pausa no avanza');
ok(L.posicionAhora(f.sonando, 10 ** 9, 0) === 200000, 'no pasa de la duración');
ok(L.duracionTexto(215) === '3:35' && L.duracionTexto(3723) === '1:02:03', 'duración');

// búsqueda con una respuesta real de YouTube Music
const real = JSON.parse(readFileSync(new URL('../../app/test/datos/busqueda_canciones_shakira.json', import.meta.url), 'utf8'));
const r = L.cancionesDeBusqueda(real, 12);
ok(r.length === 12, 'saca 12 canciones');
ok(r[0].video_id === 'WTRm-Yr5Foo' && r[0].titulo.startsWith('Zoo') && r[0].artista === 'Disney & Shakira' && r[0].duracion === 191, 'primera: id, título, artistas y duración');
ok(r.every((c) => /^https:\/\//.test(c.miniatura)) && /=w226-h226-l90-rj$/.test(r[0].miniatura), 'carátulas https agrandadas');
ok(new Set(r.map((c) => c.video_id)).size === r.length, 'sin repetidas');
ok(L.cancionesDeBusqueda({}).length === 0 && L.cancionesDeBusqueda(null).length === 0, 'respuesta vacía');
const cuerpo = L.cuerpoBusqueda('  shakira  ', new Date(Date.UTC(2026, 10, 19)));
ok(cuerpo.query === 'shakira' && cuerpo.params === L.FILTRO_CANCIONES && cuerpo.context.client.clientVersion === '1.20261119.01.00', 'cuerpo de búsqueda');

// tiempo real
const u = L.mensajeUnirse('ABC234', 1);
ok(u.topic === 'realtime:fiesta-ABC234' && u.event === 'phx_join' && u.payload.config.private === false, 'unirse al canal público');
ok(L.urlRealtime().startsWith('wss://') && L.urlRealtime().includes('vsn=1.0.0'), 'url del websocket');
const aviso = JSON.stringify({ topic: 'realtime:fiesta-ABC234', event: 'broadcast', payload: { type: 'broadcast', event: 'cambio', payload: { version: 8 } } });
ok(L.leerMensaje(aviso, 'ABC234').tipo === 'cambio' && L.leerMensaje(aviso, 'ABC234').version === 8, 'aviso de cambio');
ok(L.leerMensaje(aviso, 'OTRA22').tipo === '', 'aviso de otra fiesta se ignora');
ok(L.leerMensaje(JSON.stringify({ topic: 'realtime:fiesta-ABC234', event: 'phx_reply', payload: { status: 'ok' } }), 'ABC234').tipo === 'unido', 'unido');
ok(L.leerMensaje(JSON.stringify({ topic: 'realtime:fiesta-ABC234', event: 'phx_error', payload: {} }), 'ABC234').tipo === 'reconectar', 'error = reconectar');
ok(L.leerMensaje('no json', 'ABC234').tipo === '', 'basura');
ok(L.esperaReconexion(0) === 1000 && L.esperaReconexion(9) === 15000, 'esperas de reconexión');

// la página no mete datos con innerHTML (salvo el icono fijo del corazón)
const js = readFileSync(new URL('../../web/fiesta.js', import.meta.url), 'utf8');
ok((js.match(/innerHTML/g) || []).length === 1 && /innerHTML = CORAZON/.test(js), 'sin innerHTML con datos');

console.log(fallos ? `\n${fallos} fallos` : '\nfiesta web: todo bien');
process.exit(fallos ? 1 : 0);
