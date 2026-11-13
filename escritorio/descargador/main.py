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

    from descargador.cuentas import Cuentas, activar

    estado = {"ventana": None, "acceso": None}

    # una sola instancia: las siguientes le pasan sus enlaces a esta
    servidor = QLocalServer()
    QLocalServer.removeServer(NOMBRE_INSTANCIA)
    servidor.listen(NOMBRE_INSTANCIA)
    pendientes = list(argumentos)

    def abrir_enlaces(texto):
        ventana = estado["ventana"]
        if ventana is None:
            if estado["acceso"] is not None:
                estado["acceso"].raise_()
                estado["acceso"].activateWindow()
            if texto and texto != "mostrar":
                pendientes.append(texto)
            return
        ventana.traer_al_frente()
        if texto and texto != "mostrar":
            from descargador import redes
            urls = redes.extraer_urls(texto.replace("\n", " "))
            if urls:
                ventana.buscar_texto(" ".join(urls))

    def nueva_conexion():
        s = servidor.nextPendingConnection()
        if s is None:
            return
        s.readyRead.connect(lambda: abrir_enlaces(
            bytes(s.readAll()).decode("utf-8", "ignore").strip()))
    servidor.newConnection.connect(nueva_conexion)

    def reiniciar():
        """Cerrar sesion: se vuelve a abrir Caudal desde la pantalla de entrada."""
        from PySide6.QtCore import QProcess
        servidor.close()
        if getattr(sys, "frozen", False):
            QProcess.startDetached(sys.executable, [])
        else:
            QProcess.startDetached(sys.executable, [os.path.abspath(sys.argv[0])])
        app.quit()

    def iniciar(cuenta):
        activar(cuenta)
        ajustes = Ajustes()
        catalogo.fijar_region(ajustes["region"])
        historial = Historial()
        coleccion = Coleccion()
        gestor = Gestor(ajustes, historial)
        reproductor = Reproductor(ajustes, coleccion)
        ctx = Contexto(ajustes, historial, coleccion, gestor, reproductor)
        ctx.cuenta = cuenta
        ctx.cerrar_sesion = lambda: (Cuentas().olvidar(cuenta), reiniciar())
        if cuenta.get("sesion") is not None:
            # biblioteca compartida con los demas dispositivos de la cuenta
            from descargador.sincronizacion import Sincronizador
            sinc = Sincronizador(coleccion, cuenta,
                                 al_renovar=lambda: Cuentas().actualizar_recordada(cuenta))
            coleccion.sincronizador = sinc
            ctx.sincronizador = sinc

            def llego_de_otro():
                ctx.me_gusta_cambio.emit("", True)
                ctx.listas_cambio.emit()
                ctx.guardados_cambio.emit()
            sinc.cambio_remoto.connect(llego_de_otro)
            sinc.iniciar()
        ventana = Ventana(ctx)
        estado["ventana"] = ventana
        ventana.show()
        if estado["acceso"] is not None:
            estado["acceso"].close()
            estado["acceso"] = None
        for texto in pendientes:
            abrir_enlaces(texto if "\n" not in texto else texto)
        pendientes.clear()
        if argumentos:
            abrir_enlaces(" ".join(argumentos))

    cuentas = Cuentas()
    recordada = cuentas.recordada()
    if recordada:
        iniciar(recordada)
    else:
        from descargador.ui.acceso import VentanaAcceso
        acceso = VentanaAcceso()
        estado["acceso"] = acceso
        acceso.entro.connect(lambda cuenta, _r: iniciar(cuenta))
        acceso.show()

    from descargador.hilos import en_segundo_plano
    en_segundo_plano(imagenes.limpiar_cache)

    codigo = app.exec()
    servidor.close()
    # salida inmediata: una descarga o una busqueda a medio camino no deben
    # dejar el proceso vivo e invisible (todo lo importante ya esta guardado)
    sys.stdout.flush()
    os._exit(codigo)


if __name__ == "__main__":
    main()
