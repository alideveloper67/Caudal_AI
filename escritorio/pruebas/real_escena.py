# -*- coding: utf-8 -*-
"""Prueba REAL en Windows (abre ventanas unos segundos): la escena con todas sus ventanitas
translúcidas, una foto de la pantalla y el cierre. Uso: python pruebas/real_escena.py [fondo]
Con "fondo" la pone detrás de los iconos del escritorio y luego la quita."""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_escena_")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

from descargador import catalogo, mpv_carga  # noqa: E402
from descargador.coleccion import Coleccion  # noqa: E402
from descargador.config import Ajustes  # noqa: E402
from descargador.reproduccion import Reproductor  # noqa: E402
from descargador.ui.contexto import Contexto  # noqa: E402
from descargador.ui.escena.ventana import escena_de  # noqa: E402

mpv_carga.modulo = lambda: None          # sin sonido: solo se mira la escena
catalogo.letras = lambda p: {"sincronizada": True, "lineas": [(0, "Y nadie sabe nada de nosotros"),
                                                              (5000, "bajo la luna de papel")],
                             "texto": "", "fuente": "prueba"}
a = Ajustes()
col = Coleccion()
r = Reproductor(a, col)
ctx = Contexto(a, None, col, None, r)
ctx.avisar = lambda t, deshacer=None: print("aviso:", t)
solo_ver = "fondo" in sys.argv
e = escena_de(ctx)
e.abrir(solo_ver=solo_ver)
pista = {"clave": "x", "video_id": "", "titulo": "Atardecer en Miraflores", "artista": "Lúa Serrano",
         "miniatura": "https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg", "duracion": 200}
r.actual = pista
r.pista_cambio.emit(pista)
r.duracion_cambio.emit(200.0)
r.posicion_cambio.emit(3.0)
salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_escena",
                      f"real_{'fondo' if solo_ver else 'completa'}.png")


def foto():
    if solo_ver:
        # detrás de los iconos no se fotografía (saldría lo que tengas abierto encima):
        # se comprueba que la ventana cuelga de verdad del WorkerW del escritorio
        import ctypes
        from descargador.ui.escena import escritorio_win
        u = ctypes.windll.user32
        u.GetAncestor.restype = ctypes.c_void_p
        padre = u.GetAncestor(int(e._fondo.winId()), 1)       # GA_PARENT
        hijas = all(w.parent() is e._fondo and not w.isWindow() for w in list(e._piezas.values()) + list(e._bordes.values()))
        print("piezas dentro de la ventana de fondo:", hijas)
        print("dentro del escritorio:", bool(padre) and padre == escritorio_win.buscar_workerw(), "solo_ver:", e.solo_ver)
    else:
        QGuiApplication.primaryScreen().grabWindow(0).save(salida)
        print("foto:", salida)
    print("ventanas:", len(e._piezas) + len(e._bordes) + 1)
    e.cerrar()
    QTimer.singleShot(400, app.quit)


QTimer.singleShot(3500, foto)
t0 = time.time()
app.exec()
print("cerrada:", not e.abierta, "en", round(time.time() - t0, 1), "s")
