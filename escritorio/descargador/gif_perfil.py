# -*- coding: utf-8 -*-
"""GIF animados para la foto y el fondo del perfil (solo Donador o Fundador de Caudal).

Aquí vive la lógica, sin ventanas:
  * reconocer un GIF (cabecera GIF87a / GIF89a), no su extensión;
  * `preparar_gif`: lo deja listo para subir. Si pesa 4,5 MB o menos se sube tal cual; si pesa más se
    reducen cuadros y tamaño (480 px cuadrada para la foto, 960×360 para el fondo) conservando las
    duraciones. Usa Pillow si está; si no, Qt (QImageReader) más un escritor de GIF propio;
  * `ClienteGifs`: el buscador de GIF de Caudal (servicio propio en Netlify). Solo se baja desde ese
    servicio; no se aceptan enlaces pegados por la gente.
"""

import io
from urllib.parse import urlsplit

from .nube import ErrorNube

TOPE_SUBIDA = 4_500_000          # el cubo acepta 5 MB: se deja margen
TOPE_BAJADA = 6_000_000
LADO_FOTO_GIF = 480
FONDO_GIF = (960, 360)
RAZON_FOTO = "foto"
RAZON_FONDO = "fondo"

MSG_EXCLUSIVO = "Los GIF animados son exclusivos de los donadores de Caudal"
MSG_PESADO = "Ese GIF pesa demasiado. Prueba con uno más corto"
MSG_NO_ABRE = "No se pudo abrir ese GIF. Prueba con otro archivo."
MSG_SIN_CLAVE = ("La búsqueda de GIF llegará muy pronto. Mientras, puedes subir un GIF desde tu equipo.")
MSG_NO_PERMITIDO = "La búsqueda de GIF es solo para donadores de Caudal."
MSG_FALLO_BUSQUEDA = "No se pudo buscar ahora. Revisa tu internet y prueba de nuevo."

URL_SERVICIO = "https://caudal-musica.netlify.app/api/gifs"

# (escala sobre el tamaño final, cada cuántos cuadros se queda uno): del más fiel al más ligero
NIVELES = [(1.0, 1), (0.8, 1), (0.8, 2), (0.6, 2), (0.5, 3), (0.4, 3), (0.35, 4)]


# ------------------------------------------------------------------ reconocer
def es_gif(datos):
    return bool(datos) and bytes(datos[:6]) in (b"GIF87a", b"GIF89a")


def es_gif_ruta(ruta):
    try:
        with open(ruta, "rb") as f:
            return es_gif(f.read(6))
    except OSError:
        return False


def url_es_gif(url):
    """¿La dirección (o ruta de la nube) termina en .gif? Ignora ?v=… y #…"""
    if not url:
        return False
    return urlsplit(str(url)).path.lower().endswith(".gif")


def _leer_origen(origen):
    if isinstance(origen, (bytes, bytearray)):
        return bytes(origen)
    try:
        with open(origen, "rb") as f:
            return f.read()
    except OSError as e:
        raise ErrorNube(MSG_NO_ABRE) from e


# ------------------------------------------------------------------ recorte (compartido)
def _caja(modo, w, h, escala):
    """(x0, y0, x1, y1) del recorte centrado y (ancho, alto) final para un cuadro de w×h."""
    if modo == RAZON_FOTO:
        t = min(w, h)
        x0, y0 = (w - t) // 2, (h - t) // 2
        lado = max(8, int(min(t, LADO_FOTO_GIF) * escala))
        return (x0, y0, x0 + t, y0 + t), (lado, lado)
    ancho, alto = FONDO_GIF
    if w * alto > h * ancho:
        nw, nh = int(h * ancho / alto), h
    else:
        nw, nh = w, int(w * alto / ancho)
    x0, y0 = (w - nw) // 2, (h - nh) // 2
    fw = max(16, int(min(nw, ancho) * escala))
    return (x0, y0, x0 + nw, y0 + nh), (fw, max(6, int(fw * alto / ancho)))


def _agrupar(cuadros, cada):
    """Se queda con un cuadro de cada `cada` sumando las duraciones (la animación dura lo mismo)."""
    if cada <= 1:
        return cuadros
    salida = []
    for i in range(0, len(cuadros), cada):
        grupo = cuadros[i:i + cada]
        salida.append((grupo[0][0], sum(d for _c, d in grupo)))
    return salida


# ------------------------------------------------------------------ con Pillow
def _pillow():
    try:
        from PIL import Image, ImageSequence  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _cuadros_pillow(datos):
    from PIL import Image, ImageSequence
    im = Image.open(io.BytesIO(datos))
    cuadros = []
    for fr in ImageSequence.Iterator(im):
        dur = int(fr.info.get("duration", 100) or 100)
        cuadros.append((fr.convert("RGBA"), max(20, dur)))
    return cuadros


def _escribir_pillow(cuadros, modo, escala, cada):
    from PIL import Image
    cuadros = _agrupar(cuadros, cada)
    listos, duraciones = [], []
    for img, dur in cuadros:
        caja, tam = _caja(modo, img.width, img.height, escala)
        c = img.crop(caja)
        if c.size != tam:
            c = c.resize(tam, Image.LANCZOS)
        fondo = Image.new("RGB", c.size, (255, 255, 255))      # sin transparencia, como el JPEG
        fondo.paste(c, mask=c.getchannel("A"))
        listos.append(fondo.quantize(256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG))
        duraciones.append(dur)
    b = io.BytesIO()
    listos[0].save(b, "GIF", save_all=True, append_images=listos[1:], duration=duraciones, loop=0,
                   disposal=1, optimize=False)
    return b.getvalue()


# ------------------------------------------------------------------ sin Pillow: Qt + escritor propio
def _cuadros_qt(datos):
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QImage, QImageReader
    ba = QByteArray(datos)
    buf = QBuffer(ba)
    buf.open(QIODevice.ReadOnly)
    lector = QImageReader(buf, b"gif")
    cuadros = []
    while lector.canRead():
        dur = lector.nextImageDelay()
        img = lector.read()
        if img.isNull():
            break
        cuadros.append((img.convertToFormat(QImage.Format_ARGB32), max(20, int(dur or 100))))
        if len(cuadros) > 600:
            break
    return cuadros


def _lzw(indices, bits=8):
    """Compresión LZW del GIF para una lista de índices de paleta (bytes)."""
    clear, fin = 1 << bits, (1 << bits) + 1
    salida = bytearray()
    acum = 0
    n = 0
    tam = bits + 1
    tabla = {}
    libre = fin + 1

    def emitir(codigo, tam, acum, n):
        acum |= codigo << n
        n += tam
        while n >= 8:
            salida.append(acum & 255)
            acum >>= 8
            n -= 8
        return acum, n

    acum, n = emitir(clear, tam, acum, n)
    previo = indices[0]
    for px in indices[1:]:
        clave = (previo << 8) | px
        c = tabla.get(clave)
        if c is not None:
            previo = c
            continue
        acum, n = emitir(previo, tam, acum, n)
        if libre < 4096:
            tabla[clave] = libre
            libre += 1
            if libre - 1 == (1 << tam) and tam < 12:
                tam += 1
        else:
            acum, n = emitir(clear, tam, acum, n)
            tabla.clear()
            libre = fin + 1
            tam = bits + 1
        previo = px
    acum, n = emitir(previo, tam, acum, n)
    acum, n = emitir(fin, tam, acum, n)
    if n:
        salida.append(acum & 255)
    return bytes(salida)


def _escribir_qt(cuadros, modo, escala, cada):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    cuadros = _agrupar(cuadros, cada)
    trozos = []
    ancho = alto = 0
    for img, dur in cuadros:
        caja, tam = _caja(modo, img.width(), img.height(), escala)
        c = img.copy(caja[0], caja[1], caja[2] - caja[0], caja[3] - caja[1])
        if (c.width(), c.height()) != tam:
            c = c.scaled(tam[0], tam[1], Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        plano = QImage(c.width(), c.height(), QImage.Format_RGB32)
        plano.fill(QColor("#FFFFFF"))
        p = QPainter(plano)
        p.drawImage(0, 0, c)
        p.end()
        ind = plano.convertToFormat(QImage.Format_Indexed8, Qt.DiffuseDither)
        ancho, alto = ind.width(), ind.height()
        tabla = ind.colorTable()[:256]
        paleta = bytearray()
        for rgb in tabla:
            paleta += bytes(((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255))
        paleta += bytes(768 - len(paleta))
        bpl = ind.bytesPerLine()
        crudo = bytes(ind.constBits())
        filas = b"".join(crudo[y * bpl:y * bpl + ancho] for y in range(alto))
        trozos.append((bytes(paleta), filas, dur))
    out = bytearray(b"GIF89a")
    out += ancho.to_bytes(2, "little") + alto.to_bytes(2, "little") + bytes((0x70, 0, 0))
    out += b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00"
    for paleta, filas, dur in trozos:
        cs = max(2, min(65535, round(dur / 10)))
        out += b"\x21\xF9\x04" + bytes((0x04,)) + cs.to_bytes(2, "little") + b"\x00\x00"       # disposal 1
        out += b"\x2C" + (0).to_bytes(2, "little") * 2 + ancho.to_bytes(2, "little") + alto.to_bytes(2, "little")
        out += bytes((0x87,)) + paleta                                                          # tabla local de 256
        out += b"\x08"
        datos = _lzw(filas)
        for i in range(0, len(datos), 255):
            parte = datos[i:i + 255]
            out += bytes((len(parte),)) + parte
        out += b"\x00"
    out += b"\x3B"
    return bytes(out)


# ------------------------------------------------------------------ preparar
def preparar_gif(origen, modo=RAZON_FOTO, tope=TOPE_SUBIDA, usar_pillow=None):
    """Bytes de GIF listos para subir. `origen`: ruta o bytes. ErrorNube con el aviso si no se puede."""
    datos = _leer_origen(origen)
    if not es_gif(datos):
        raise ErrorNube(MSG_NO_ABRE)
    if len(datos) <= tope:
        return datos
    con_pillow = _pillow() if usar_pillow is None else usar_pillow
    try:
        cuadros = _cuadros_pillow(datos) if con_pillow else _cuadros_qt(datos)
    except Exception as e:  # noqa: BLE001
        raise ErrorNube(MSG_NO_ABRE) from e
    if not cuadros:
        raise ErrorNube(MSG_NO_ABRE)
    escribir = _escribir_pillow if con_pillow else _escribir_qt
    for escala, cada in NIVELES:
        if cada > 1 and len(cuadros) < 2 * cada:
            continue
        try:
            sal = escribir(cuadros, modo, escala, cada)
        except Exception as e:  # noqa: BLE001
            raise ErrorNube(MSG_NO_ABRE) from e
        if len(sal) <= tope:
            return sal
    raise ErrorNube(MSG_PESADO)


# ------------------------------------------------------------------ buscador de GIF
class ClienteGifs:
    """Habla con el servicio de GIF de Caudal. Se puede cambiar por un doble en las pruebas:
    buscar(q, pos) -> dict, vista(url) -> bytes, bajar(url_gif) -> bytes."""

    def __init__(self, base=URL_SERVICIO):
        self.base = base

    def _sesion(self):
        import requests
        s = requests.Session()
        s.headers["User-Agent"] = "Caudal-Escritorio"
        return s

    def buscar(self, q="", pos=""):
        import requests
        params = {}
        if q:
            params["q"] = q
        if pos:
            params["pos"] = pos
        try:
            r = self._sesion().get(self.base, params=params, timeout=15)
        except requests.RequestException as e:
            raise ErrorNube(MSG_FALLO_BUSQUEDA) from e
        try:
            d = r.json()
        except ValueError:
            d = {}
        if not isinstance(d, dict):
            d = {}
        if r.status_code in (401, 403):
            return {"items": [], "siguiente": "", "error": "no_permitido", "aviso": ""}
        if r.status_code >= 300 and not d.get("error"):
            raise ErrorNube(MSG_FALLO_BUSQUEDA)
        return normalizar_busqueda(d)

    def vista(self, url):
        """Bytes de la vista previa (un GIF pequeño), o b'' si no sirve."""
        import requests
        if not str(url).startswith("https://"):
            return b""
        try:
            r = self._sesion().get(url, timeout=15)
        except requests.RequestException:
            return b""
        if r.status_code == 200 and len(r.content) < 3_000_000 and es_gif(r.content):
            return r.content
        return b""

    def bajar(self, url_gif):
        """El GIF elegido, siempre a través del servicio (nunca directo)."""
        import requests
        try:
            r = self._sesion().get(self.base, params={"bajar": url_gif}, timeout=40)
        except requests.RequestException as e:
            raise ErrorNube("No se pudo bajar ese GIF. Revisa tu internet y prueba de nuevo.") from e
        if r.status_code != 200 or not es_gif(r.content) or len(r.content) > TOPE_BAJADA + 1024:
            raise ErrorNube("No se pudo bajar ese GIF. Prueba con otro.")
        return r.content


def normalizar_busqueda(d):
    items = []
    for it in (d.get("items") or []):
        if not isinstance(it, dict) or not it.get("gif"):
            continue
        items.append({"id": str(it.get("id") or ""), "titulo": str(it.get("titulo") or "")[:120],
                      "vista": str(it.get("vista") or ""), "gif": str(it["gif"]),
                      "ancho": int(it.get("ancho") or 0), "alto": int(it.get("alto") or 0),
                      "peso": int(it.get("peso") or 0)})
    return {"items": items, "siguiente": str(d.get("siguiente") or ""),
            "aviso": str(d.get("aviso") or ""), "error": str(d.get("error") or "")}
