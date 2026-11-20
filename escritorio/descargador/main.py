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

    # lo que falle queda escrito en fallos.log (en el .exe no hay consola)
    try:
        from descargador import registro_fallos
        from descargador.config import carpeta_datos
        registro_fallos.activar(carpeta_datos())
        # aviso de errores a la nube (ver aviso_errores.py); version y pantalla se toman solas
        from descargador import aviso_errores
        aviso_errores.activar(carpeta_datos())
    except Exception:  # noqa: BLE001
        pass

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

    def revisar_terminos(cuenta, ventana):
        """Cuentas de antes de los términos (o sin los datos básicos): se piden una vez.
        La consulta va en segundo plano para que la ventana salga sin esperar a la red; si hace
        falta aceptar, el cuadro se abre encima en cuanto llega la respuesta."""
        sesion = cuenta.get("sesion")
        if sesion is None or not getattr(sesion, "access", ""):
            return
        from descargador import legal
        from descargador.hilos import en_segundo_plano

        def llego(perfil):
            if perfil is None or (legal.aceptado(perfil) and legal.completo(perfil)):
                return
            from descargador.ui.legal_ui import DialogoAceptar
            if DialogoAceptar(sesion, perfil, ventana).exec() != DialogoAceptar.Accepted:
                try:
                    ventana.hide()
                    ventana.r.cerrar()
                except Exception:  # noqa: BLE001
                    pass
                Cuentas().olvidar(cuenta)
                reiniciar()
        # sin red: se pregunta la próxima vez (como antes)
        en_segundo_plano(legal.perfil, sesion, ok=llego, error=lambda _e: None, dueno=ventana)

    def iniciar(cuenta):
        activar(cuenta)
        ajustes = Ajustes()
        # el color y el fondo elegidos, antes de construir la ventana
        from descargador.ui.estilos import aplicar_aspecto
        from descargador.premium import revertir_aspecto_si_hace_falta
        revertir_aspecto_si_hace_falta(ajustes)      # un tema de donadores ya vencido vuelve a lo normal
        aplicar_aspecto(ajustes["acento"], ajustes["fondo"])
        catalogo.fijar_region(ajustes["region"])
        historial = Historial()
        coleccion = Coleccion()
        # cuenta nueva (o que aún no eligió): «¿Qué artistas te gustan?» antes de la pantalla principal
        from descargador.ui import pantalla_gustos
        pantalla_gustos.al_entrar(cuenta, coleccion, ajustes["region"])
        gestor = Gestor(ajustes, historial)
        reproductor = Reproductor(ajustes, coleccion)
        ctx = Contexto(ajustes, historial, coleccion, gestor, reproductor)
        ctx.cuenta = cuenta
        # la descarga inteligente espera a tus descargas manuales y avisa de lo que baja
        inteligente = getattr(reproductor, "descarga_inteligente", None)
        if inteligente is not None:
            inteligente.gestor = gestor
            inteligente.descargada.connect(lambda _p: ctx.descargas_cambio.emit())
        ctx.cerrar_sesion = lambda: (Cuentas().olvidar(cuenta), reiniciar())
        ctx.reiniciar = reiniciar
        if cuenta.get("sesion") is not None:
            # biblioteca compartida con los demas dispositivos de la cuenta
            from descargador.sincronizacion import Sincronizador
            sinc = Sincronizador(coleccion, cuenta, ajustes=ajustes,
                                 al_renovar=lambda: Cuentas().actualizar_recordada(cuenta))
            coleccion.sincronizador = sinc
            ctx.sincronizador = sinc

            def llego_de_otro():
                ctx.me_gusta_cambio.emit("", True)
                ctx.listas_cambio.emit()
                ctx.guardados_cambio.emit()
            sinc.cambio_remoto.connect(llego_de_otro)

            def ajustes_de_otro(cambiados):
                # el sonido (ecualizador, super volumen...) se nota al momento
                reproductor.aplicar_sonido()
                if "region" in cambiados:
                    catalogo.fijar_region(ajustes["region"])
            sinc.ajustes_remotos.connect(ajustes_de_otro)

            # al guardar un ajuste, se sube en un momento (los seguidos se agrupan)
            from descargador.sincronizacion import ajustes_compartidos, huella_ajustes
            guardar_original = ajustes.guardar
            ultima = [huella_ajustes(ajustes_compartidos(ajustes))]

            def guardar_y_subir():
                guardar_original()
                ahora = huella_ajustes(ajustes_compartidos(ajustes))
                if ahora != ultima[0]:      # el volumen u otros ajustes propios no viajan
                    ultima[0] = ahora
                    sinc.pronto()
            ajustes.guardar = guardar_y_subir
            sinc.iniciar()

            def al_cambiar_estado_app(estado_app):
                if estado_app == Qt.ApplicationActive:
                    sinc.al_volver()
            app.applicationStateChanged.connect(al_cambiar_estado_app)
        ventana = Ventana(ctx)
        estado["ventana"] = ventana
        ventana.show()
        revisar_terminos(cuenta, ventana)
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
    # en el .exe sin consola sys.stdout/sys.stderr son None
    for flujo in (sys.stdout, sys.stderr):
        try:
            if flujo is not None:
                flujo.flush()
        except Exception:  # noqa: BLE001
            pass
    os._exit(codigo)


if __name__ == "__main__":
    main()
