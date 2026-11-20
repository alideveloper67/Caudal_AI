// La página de la Fiesta: buscar, pedir canciones, votar y ver qué suena, en tiempo real.
// Toda la lógica que no toca la pantalla está en fiesta-logica.js (y tiene pruebas).
import {
  codigoDeDireccion, normalizarCodigo, nuevoToken, tokenValido, peticionRpc, mensajeDeError, leerFiesta,
  votarLocal, textoQuedan, quedan, yaEsta, posicionAhora, duracionTexto, cuerpoBusqueda, cancionesDeBusqueda,
  urlRealtime, mensajeUnirse, mensajeLatido, leerMensaje, esperaReconexion,
} from './fiesta-logica.js';

const $ = (id) => document.getElementById(id);
const guardado = {
  leer(k) { try { return localStorage.getItem(k); } catch { return null; } },
  poner(k, v) { try { localStorage.setItem(k, v); } catch { /* sin almacenamiento: vale para esta visita */ } },
};

let codigo = codigoDeDireccion(location.href);
let token = guardado.leer('caudal-fiesta-token');
if (!tokenValido(token)) {
  token = nuevoToken((n) => crypto.getRandomValues(new Uint8Array(n)));
  guardado.poner('caudal-fiesta-token', token);
}
let fiesta = null;
let desfase = 0;            // reloj del servidor - reloj de este teléfono (ms)
let pidiendo = null;        // la petición de fiesta_ver en marcha
let otraVez = false;
const enCurso = new Set();  // ids de canciones con un voto enviándose

// ---------------------------------------------------------------- red
class ErrorFiesta extends Error {}
async function rpc(nombre, parametros) {
  const { url, init } = peticionRpc(nombre, parametros);
  let r;
  try { r = await fetch(url, init); } catch { throw new ErrorFiesta(mensajeDeError(0, null)); }
  const texto = await r.text();
  if (!r.ok) throw new ErrorFiesta(mensajeDeError(r.status, texto));
  try { return JSON.parse(texto); } catch { return null; }
}

function aplicar(d) {
  const f = leerFiesta(d);
  if (!f) return mostrarFin('no-existe');
  if (fiesta && f.version < fiesta.version) return;       // llegó una respuesta vieja
  desfase = f.ahora - Date.now();
  fiesta = f;
  if (!f.abierta) return mostrarFin('cerrada');
  pintar();
}

async function refrescar() {
  if (!codigo) return;
  if (pidiendo) { otraVez = true; return; }
  pidiendo = rpc('fiesta_ver', { p_codigo: codigo, p_invitado: token });
  try { aplicar(await pidiendo); } catch { /* se reintenta con el siguiente aviso o en 20 s */ }
  pidiendo = null;
  if (otraVez) { otraVez = false; refrescar(); }
}

// ---------------------------------------------------------------- tiempo real
let ws = null, ref = 0, joinRef = 0, latido = null, intento = 0, sinRespuesta = false, temporizador = null;
function conectar() {
  clearTimeout(temporizador);
  try { ws = new WebSocket(urlRealtime()); } catch { return reconectar(); }
  ws.onopen = () => {
    joinRef = ++ref;
    ws.send(JSON.stringify(mensajeUnirse(codigo, joinRef)));
    clearInterval(latido);
    sinRespuesta = false;
    latido = setInterval(() => {
      if (sinRespuesta) { ws.close(); return; }
      sinRespuesta = true;
      ws.send(JSON.stringify(mensajeLatido(++ref)));
    }, 25000);
  };
  ws.onmessage = (e) => {
    if (typeof e.data === 'string' && e.data.includes('"phoenix"')) sinRespuesta = false;
    const m = leerMensaje(e.data, codigo);
    if (m.tipo === 'unido') { intento = 0; vivo(true); refrescar(); }
    else if (m.tipo === 'cambio') { if (!fiesta || m.version > fiesta.version) refrescar(); }
    else if (m.tipo === 'reconectar') ws.close();
  };
  ws.onclose = () => { vivo(false); clearInterval(latido); reconectar(); };
  ws.onerror = () => { try { ws.close(); } catch { /* ya cerrado */ } };
}
function reconectar() {
  if (fiesta && !fiesta.abierta) return;
  temporizador = setTimeout(conectar, esperaReconexion(intento++));
}
function vivo(si) {
  $('vivo').hidden = false;
  $('vivo').classList.toggle('si', si);
  $('vivo-txt').textContent = si ? 'En vivo' : 'Conectando…';
}

// ---------------------------------------------------------------- pantalla
function ver(id) {
  for (const v of ['cargando', 'v-entrada', 'v-fin', 'v-fiesta']) $(v).hidden = v !== id;
}
function mostrarFin(motivo) {
  ver('v-fin');
  $('vivo').hidden = true;
  if (ws) { ws.onclose = null; ws.close(); }
  if (motivo === 'no-existe') {
    $('fin-titulo').textContent = 'Esa fiesta no existe';
    $('fin-texto').textContent = 'Revisa el código o vuelve a escanear el QR de la pantalla del anfitrión.';
  } else {
    $('fin-titulo').textContent = 'La fiesta terminó';
    $('fin-texto').textContent = 'El anfitrión cerró la fiesta. ¡Gracias por la música!';
  }
}

let avisoT = null;
function avisar(texto, mal = false) {
  const a = $('aviso');
  a.textContent = texto;
  a.classList.toggle('mal', mal);
  a.classList.add('ver');
  clearTimeout(avisoT);
  avisoT = setTimeout(() => a.classList.remove('ver'), mal ? 4200 : 2600);
}

function el(tag, clase, texto) {
  const e = document.createElement(tag);
  if (clase) e.className = clase;
  if (texto != null) e.textContent = texto;
  return e;
}
function caratula(url, lado = 52) {
  const i = el('img', 'car');
  i.alt = ''; i.width = lado; i.height = lado; i.loading = 'lazy'; i.decoding = 'async';
  if (url) i.src = url; else i.removeAttribute('src');
  i.onerror = () => i.removeAttribute('src');
  return i;
}
const CORAZON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.5-4.6-7.5-10.1A4.4 4.4 0 0 1 12 7.6a4.4 4.4 0 0 1 7.5 2.8c0 5.5-7.5 10.1-7.5 10.1Z"/></svg>';

function pintar() {
  ver('v-fiesta');
  const f = fiesta;
  document.title = `${f.nombre} · Fiesta en Caudal`;
  $('f-nombre').textContent = f.nombre;
  $('f-sub').textContent = `Código ${f.codigo} · ${f.invitados === 1 ? '1 persona' : `${f.invitados} personas`} en la fiesta`;
  $('quedan').textContent = textoQuedan(f);
  pintarSuena();
  // cola
  const cola = $('cola');
  cola.replaceChildren();
  $('c-total').textContent = f.cola.length ? (f.cola.length === 1 ? '1 canción' : `${f.cola.length} canciones`) : '';
  if (!f.cola.length) cola.append(el('li', 'vacio', 'La cola está vacía. ¡Pide la primera!'));
  f.cola.forEach((c, i) => {
    const li = el('li');
    li.append(el('span', 'num', String(i + 1)), caratula(c.miniatura));
    const t = el('div', 'txt');
    const b = el('b', null, c.titulo);
    if (c.mia) b.append(el('span', 'tuya', 'Tuya'));
    t.append(b, el('span', null, [c.artista, c.nombre ? `pedida por ${c.nombre}` : (c.de_anfitrion ? 'del anfitrión' : '')].filter(Boolean).join(' · ')));
    const v = el('button', 'voto' + (c.vote ? ' si' : ''));
    v.type = 'button';
    v.innerHTML = CORAZON;
    v.append(el('span', null, String(c.votos)));
    v.setAttribute('aria-pressed', String(c.vote));
    v.setAttribute('aria-label', `${c.vote ? 'Quitar mi voto a' : 'Votar'} ${c.titulo} (${c.votos} votos)`);
    v.disabled = enCurso.has(c.id);
    v.onclick = () => votar(c.id, !c.vote);
    li.append(t, v);
    cola.append(li);
  });
  // ya sonaron
  $('sec-sonadas').hidden = !f.sonadas.length;
  const s = $('sonadas');
  s.replaceChildren();
  for (const c of f.sonadas) {
    const li = el('li');
    const t = el('div', 'txt');
    t.append(el('b', null, c.titulo), el('span', null, [c.artista, c.nombre && `pedida por ${c.nombre}`].filter(Boolean).join(' · ')));
    li.append(caratula(c.miniatura), t);
    s.append(li);
  }
  pintarResultados();
}

function pintarSuena() {
  const s = fiesta && fiesta.sonando;
  $('s-car').src = (s && s.miniatura) || '/icono.png';
  $('s-etq').textContent = s ? (s.pausa ? 'En pausa' : 'Ahora suena') : 'Ahora suena';
  $('s-titulo').textContent = s ? s.titulo || 'Sin título' : 'Todavía no suena nada';
  $('s-artista').textContent = s ? s.artista : 'Pide la primera canción';
  $('s-quien').textContent = s && s.nombre ? `La pidió ${s.nombre}` : '';
  $('s-barra').hidden = !(s && s.duracion > 0);
  tic();
}
function tic() {
  const s = fiesta && fiesta.sonando;
  if (!s || !(s.duracion > 0)) return;
  const pos = posicionAhora(s, Date.now(), desfase);
  $('s-progreso').style.width = `${Math.min(100, (pos / (s.duracion * 1000)) * 100).toFixed(1)}%`;
}

// ---------------------------------------------------------------- búsqueda
let resultados = [];
let buscando = 0;
async function buscar(texto) {
  const q = texto.trim();
  const mio = ++buscando;
  if (q.length < 2) { resultados = []; pintarResultados(); return; }
  $('resultados').replaceChildren(el('li', 'vacio', 'Buscando…'));
  try {
    const r = await fetch('/api/yt?m=search&d=music', {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(cuerpoBusqueda(q)),
    });
    const d = await r.json();
    if (mio !== buscando) return;
    resultados = cancionesDeBusqueda(d, 12);
    pintarResultados(resultados.length ? '' : 'No encontramos canciones con eso. Prueba con otras palabras.');
  } catch {
    if (mio !== buscando) return;
    resultados = [];
    pintarResultados('No se pudo buscar ahora. Revisa tu internet y vuelve a probar.');
  }
}
const pidiendoVid = new Set();
function pintarResultados(vacio = '') {
  const ul = $('resultados');
  ul.replaceChildren();
  if (!resultados.length) { if (vacio) ul.append(el('li', 'vacio', vacio)); return; }
  const puede = quedan(fiesta) > 0;
  for (const c of resultados) {
    const li = el('li');
    const t = el('div', 'txt');
    t.append(el('b', null, c.titulo), el('span', null, [c.artista, c.duracion ? duracionTexto(c.duracion) : ''].filter(Boolean).join(' · ')));
    const b = el('button', 'boton chico');
    b.type = 'button';
    const esta = yaEsta(fiesta, c.video_id);
    b.textContent = esta ? 'En la cola' : pidiendoVid.has(c.video_id) ? 'Pidiendo…' : 'Pedir';
    b.disabled = esta || !puede || pidiendoVid.has(c.video_id);
    b.onclick = () => pedir(c);
    li.append(caratula(c.miniatura), t, b);
    ul.append(li);
  }
}

async function pedir(c) {
  pidiendoVid.add(c.video_id);
  pintarResultados();
  try {
    aplicar(await rpc('fiesta_anadir', { p_codigo: codigo, p_invitado: token, p_pista: c, p_nombre: nombreActual() }));
    avisar('¡Pedida! Vótala para que suene antes.');
  } catch (e) {
    avisar(e instanceof ErrorFiesta ? e.message : 'No se pudo pedir. Vuelve a probar.', true);
    refrescar();
  }
  pidiendoVid.delete(c.video_id);
  pintarResultados();
}

async function votar(id, voto) {
  if (enCurso.has(id)) return;
  enCurso.add(id);
  fiesta = votarLocal(fiesta, id, voto);
  pintar();
  try {
    aplicar(await rpc('fiesta_votar', { p_codigo: codigo, p_invitado: token, p_cancion: id, p_voto: voto }));
  } catch (e) {
    avisar(e instanceof ErrorFiesta ? e.message : 'No se pudo votar. Vuelve a probar.', true);
    refrescar();
  }
  enCurso.delete(id);
  if (fiesta && fiesta.abierta) pintar();
}

// ---------------------------------------------------------------- nombre
const nombreActual = () => $('i-nombre').value.trim().slice(0, 30);
let nombreT = null;
function cambioNombre() {
  guardado.poner('caudal-fiesta-nombre', nombreActual());
  clearTimeout(nombreT);
  nombreT = setTimeout(async () => {
    if (!nombreActual()) return;
    try { aplicar(await rpc('fiesta_entrar', { p_codigo: codigo, p_invitado: token, p_nombre: nombreActual() })); } catch { /* da igual */ }
  }, 900);
}

// ---------------------------------------------------------------- arranque
async function entrar() {
  ver('cargando');
  try {
    aplicar(await rpc('fiesta_entrar', { p_codigo: codigo, p_invitado: token, p_nombre: nombreActual() }));
  } catch (e) {
    // cerrada o inexistente: fiesta_ver lo dice sin error
    try {
      const d = await rpc('fiesta_ver', { p_codigo: codigo });
      if (!d) return mostrarFin('no-existe');
      if (d.abierta === false) return mostrarFin('cerrada');
    } catch { /* abajo */ }
    ver('v-entrada');
    $('i-codigo').value = codigo;
    $('e-codigo').textContent = e instanceof ErrorFiesta ? e.message : 'No pudimos entrar. Vuelve a probar.';
    return;
  }
  if (fiesta && fiesta.abierta) {
    conectar();
    setInterval(refrescar, 20000);
    setInterval(tic, 1000);
  }
}

$('i-nombre').value = (guardado.leer('caudal-fiesta-nombre') || '').slice(0, 30);
$('i-nombre').addEventListener('input', cambioNombre);
let buscarT = null;
$('i-buscar').addEventListener('input', (e) => { clearTimeout(buscarT); buscarT = setTimeout(() => buscar(e.target.value), 450); });
$('f-buscar').addEventListener('submit', (e) => { e.preventDefault(); clearTimeout(buscarT); $('i-buscar').blur(); buscar($('i-buscar').value); });
$('f-codigo').addEventListener('submit', (e) => {
  e.preventDefault();
  const c = normalizarCodigo($('i-codigo').value);
  if (!c) { $('e-codigo').textContent = 'El código son 6 letras o números (sin 0, O, 1 ni I).'; return; }
  history.replaceState(null, '', `/fiesta/${c}`);
  codigo = c;
  entrar();
});
document.addEventListener('visibilitychange', () => { if (!document.hidden && fiesta && fiesta.abierta) refrescar(); });

if (codigo) entrar(); else ver('v-entrada');
