# -*- coding: utf-8 -*-
"""Cómo se ve el reproductor con las mascotas, usando el CÓDIGO REAL de la barra de Caudal de escritorio
(descargador.ui.componentes.Deslizador + descargador.mascotas.pintar), dibujado fuera de pantalla.

    python vista_reproductor.py                 -> vista/reproductor.png (todas, a tamaño real y al doble) y vista/reproductor_<clave>.gif
    python vista_reproductor.py pikachu kirby   -> solo esas

Usa las hojas de herramientas/mascotas (<clave>.py -> hojas()), aunque todavía no estén exportadas a la app.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
AQUI = Path(__file__).parent
RAIZ = AQUI.parent.parent
sys.path.insert(0, str(RAIZ / "escritorio"))
sys.path.insert(0, str(AQUI))

from PIL import Image  # noqa: E402
from PySide6.QtCore import QObject, QRectF, Qt, Signal  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)
from PySide6.QtGui import QFontDatabase  # noqa: E402
for _f in ('segoeui.ttf', 'segoeuib.ttf', 'arial.ttf'):
    _r = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / _f
    if _r.exists():
        QFontDatabase.addApplicationFont(str(_r))

from descargador import mascotas as M  # noqa: E402
from descargador.ui.componentes import Deslizador  # noqa: E402
from descargador.ui.estilos import C  # noqa: E402

import galeria  # noqa: E402
import pix  # noqa: E402


class Gestor(QObject):
    cambiada = Signal()

    def __init__(self, datos):
        super().__init__()
        self._d = datos

    def datos(self):
        return self._d


class Repro(QObject):
    estado_cambio = Signal(str)
    estado = "sonando"


def preparar_arte(claves):
    """Copia el arte del escritorio a una carpeta temporal y pone encima las hojas nuevas de herramientas/mascotas."""
    tmp = Path(tempfile.mkdtemp(prefix="caudal_mascotas_"))
    for f in (RAIZ / "escritorio" / "descargador" / "mascotas").iterdir():
        shutil.copy(f, tmp / f.name)
    for c in claves:
        try:
            pix.W = 48
            galeria.cargar(c).hojas().save(tmp / f"{c}.png")
        except Exception as e:  # noqa: BLE001
            print("no se pudo dibujar", c, e)
        finally:
            pix.W = 48
    M.ARTE = tmp
    M._PIXMAPS.clear()
    return tmp


def cuadro_barra(datos, valor, cuadro, fase, ancho=640):
    """Un panel como el del reproductor: título, barra con la mascota y tiempos. Devuelve QImage."""
    d = Deslizador(alto=16)
    d.poner_mascota(Gestor(datos), Repro())
    d._reloj.stop()
    d._cuadro, d._fase = cuadro, fase
    d.set_valor(valor)
    d.resize(ancho - 120, d.height())
    alto = d.height() + 46
    img = QImage(ancho, alto, QImage.Format_ARGB32)
    img.fill(QColor(C["panel"]))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QColor(C["texto"]))
    f = QFont('Segoe UI')
    f.setPointSize(10)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QRectF(60, 6, ancho - 120, 18), Qt.AlignLeft, f"{datos['nombre']} corre por la barra")
    f.setBold(False)
    f.setPointSize(9)
    p.setFont(f)
    p.setPen(QColor(C["texto3"]))
    yb = 26
    p.drawText(QRectF(8, yb + d.height() - 18, 48, 16), Qt.AlignRight, "1:42")
    p.drawText(QRectF(ancho - 54, yb + d.height() - 18, 48, 16), Qt.AlignLeft, "3:27")
    p.end()
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QWidget
    p = QPainter(img)
    d.render(p, QPoint(60, yb), renderFlags=QWidget.RenderFlag.DrawChildren)
    p.end()
    return img


def a_pil(qimg):
    qimg = qimg.convertToFormat(QImage.Format_RGBA8888)
    w, h = qimg.width(), qimg.height()
    return Image.frombuffer("RGBA", (w, h), bytes(qimg.constBits()), "raw", "RGBA", qimg.bytesPerLine(), 1).copy()


def main(claves=None):
    cat = {m["clave"]: m for m in M.catalogo()}
    claves = claves or list(cat.keys())
    preparar_arte(claves)
    filas = []
    for c in claves:
        if c not in cat:
            continue
        filas.append(a_pil(cuadro_barra(cat[c], 0.55, 0, 2.0)))
    out = AQUI / "vista"
    out.mkdir(exist_ok=True)
    # mosaico a tamaño real (2 columnas) y una copia al doble para mirar el detalle
    cols = 2
    w, h = filas[0].width, max(f.height for f in filas)
    mos = Image.new("RGBA", (w * cols, h * ((len(filas) + cols - 1) // cols)), (0, 0, 0, 255))
    for i, f in enumerate(filas):
        mos.paste(f, ((i % cols) * w, (i // cols) * h))
    mos.save(out / "reproductor.png")
    mos.resize((mos.width * 2, mos.height * 2), Image.NEAREST).save(out / "reproductor_x2.png")
    # GIF: la mascota avanzando por la barra (para 3 de ellas)
    for c in claves[:3]:
        cuadros = [a_pil(cuadro_barra(cat[c], 0.25 + k * 0.025, k % 2, k * 0.9)) for k in range(16)]
        cuadros = [q.resize((q.width * 2, q.height * 2), Image.NEAREST).convert("RGB") for q in cuadros]
        cuadros[0].save(out / f"reproductor_{c}.gif", save_all=True, append_images=cuadros[1:], duration=170, loop=0)
    print("vista/reproductor.png con", len(filas), "mascotas; GIF de", ", ".join(claves[:3]))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
