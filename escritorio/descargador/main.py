# -*- coding: utf-8 -*-
"""Punto de entrada de Caudal Escritorio."""

import os
import sys


def _preparar_rutas():
    """Permite ejecutar tanto como paquete instalado como script suelto."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if raiz not in sys.path:
        sys.path.insert(0, raiz)


NOMBRE_INSTANCIA = "caudal-escritorio-unica"


def _avisar_a_la_abierta(argumentos):
    """Si Caudal ya esta abierto, le pasa los enlaces y devuelve True."""
    from PySide6.QtNetwork import QLocalSocket
    s = QLocalSocket()
    s.connectToServer(NOMBRE_INSTANCIA)
    if not s.waitForConnected(400):
        return False
    s.write(("\n".join(argumentos) or "mostrar").encode("utf-8"))
    s.waitForBytesWritten(800)
    s.disconnectFromServer()
    return True


def main():
    _preparar_rutas()

    # El navegador integrado se queda en negro en equipos con tarjetas graficas
    # antiguas: Chromium intenta dibujar por GPU y el driver no responde.
    os.environ.setdefault(
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "--disable-gpu --disable-gpu-compositing --disable-software-rasterizer --no-sandbox",
    )

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtNetwork import QLocalServer
    from PySide6.QtWidgets import QApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)

    argumentos = [a for a in sys.argv[1:] if a.strip()]
    if _avisar_a_la_abierta(argumentos):
        return

    from descargador.config import APP_NOMBRE, Ajustes
    from descargador import catalogo
    from descargador.coleccion import Coleccion
    from descargador.historial import Historial
    from descargador.motor import Gestor
    from descargador.reproduccion import Reproductor
    from descargador.ui import iconos, imagenes
    from descargador.ui.contexto import Contexto
    from descargador.ui.ventana import Ventana

    app.setApplicationName(APP_NOMBRE)
    app.setOrganizationName("Caudal")
    app.setWindowIcon(QIcon(iconos.icono_app(256)))
    # al cerrar la ventana puede seguir sonando en la bandeja: se sale a mano
    app.setQuitOnLastWindowClosed(False)

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("caudal.escritorio.2")
        except Exception:
            pass

    ajustes = Ajustes()
    catalogo.fijar_region(ajustes["region"])
    historial = Historial()
    coleccion = Coleccion()
    gestor = Gestor(ajustes, historial)
    reproductor = Reproductor(ajustes, coleccion)
    ctx = Contexto(ajustes, historial, coleccion, gestor, reproductor)

    ventana = Ventana(ctx)
    ventana.show()

    # una sola instancia: las siguientes le pasan sus enlaces a esta
    servidor = QLocalServer()
    QLocalServer.removeServer(NOMBRE_INSTANCIA)
    servidor.listen(NOMBRE_INSTANCIA)

    def nueva_conexion():
        s = servidor.nextPendingConnection()
        if s is None:
            return

        def leer():
            texto = bytes(s.readAll()).decode("utf-8", "ignore").strip()
            ventana.traer_al_frente()
            if texto and texto != "mostrar":
                ventana.buscar_texto(texto.replace("\n", " "))
        s.readyRead.connect(leer)
    servidor.newConnection.connect(nueva_conexion)

    if argumentos:
        from descargador import redes
        urls = redes.extraer_urls(" ".join(argumentos))
        if urls:
            ventana.buscar_texto(" ".join(urls))

    from descargador.hilos import en_segundo_plano
    en_segundo_plano(imagenes.limpiar_cache)

    codigo = app.exec()
    servidor.close()
    sys.exit(codigo)


if __name__ == "__main__":
    main()
