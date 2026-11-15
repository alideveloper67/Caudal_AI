# -*- coding: utf-8 -*-
"""Pantalla de entrada: iniciar sesion o crear cuenta."""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QAction, QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath,
                           QRadialGradient)
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from ..cuentas import Cuentas, ErrorCuenta
from . import iconos
from .componentes import fuente
from .estilos import C, hoja


class _Arte(QWidget):
    """Panel izquierdo: degradado profundo con luces suaves, logo y promesas."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        v.setContentsMargins(48, 48, 48, 44)
        v.setSpacing(0)
        fila = QHBoxLayout()
        fila.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(iconos.icono_app(44))
        fila.addWidget(logo)
        nombre = QLabel("Caudal")
        nombre.setStyleSheet("font-size:26px;font-weight:900;color:#FFFFFF;background:transparent;")
        fila.addWidget(nombre)
        fila.addStretch(1)
        v.addLayout(fila)
        v.addStretch(1)
        titulo = QLabel("Toda tu música\ny tus videos,\nsin anuncios.")
        titulo.setStyleSheet("font-size:40px;font-weight:900;color:#FFFFFF;"
                             "background:transparent;line-height:110%;")
        v.addWidget(titulo)
        v.addSpacing(26)
        for icono, texto in (("musica", "Todo YouTube Music, con letras y radio infinita"),
                             ("video", "Videos hasta 8K, en segundo plano y en mini"),
                             ("descargar", "Descarga lo que quieras, en el formato que quieras"),
                             ("altavoz_fuerte", "Ecualizador y súper volumen sin saturar")):
            f = QHBoxLayout()
            f.setSpacing(14)
            ic = QLabel()
            ic.setFixedSize(34, 34)
            ic.setAlignment(Qt.AlignCenter)
            ic.setStyleSheet("background:rgba(255,255,255,0.14);border-radius:17px;")
            ic.setPixmap(iconos.pixmap(icono, 17, "#FFFFFF"))
            f.addWidget(ic)
            t = QLabel(texto)
            t.setStyleSheet("font-size:14px;color:rgba(255,255,255,0.92);background:transparent;")
            f.addWidget(t, 1)
            v.addLayout(f)
            v.addSpacing(12)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0.0, QColor("#0B1B3A"))
        g.setColorAt(0.55, QColor("#0B4A6B"))
        g.setColorAt(1.0, QColor("#0E7490"))
        p.fillRect(self.rect(), g)
        for cx, cy, r, color in ((0.85, 0.15, 0.55, QColor(34, 211, 238, 90)),
                                 (0.10, 0.95, 0.60, QColor(124, 92, 255, 80)),
                                 (0.65, 0.75, 0.35, QColor(59, 130, 246, 60))):
            rg = QRadialGradient(QPointF(w * cx, h * cy), max(w, h) * r)
            rg.setColorAt(0, color)
            rg.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), rg)
        # ondas: la corriente del logo, en grande y muy suave
        lapiz = p.pen()
        for i, alfa in enumerate((38, 26, 16)):
            lapiz.setColor(QColor(255, 255, 255, alfa))
            lapiz.setWidthF(2.0)
            p.setPen(lapiz)
            ruta = QPainterPath()
            y = h * 0.30 + i * 26
            ruta.moveTo(0, y)
            paso = w / 3
            for k in range(3):
                x0 = k * paso
                ruta.cubicTo(x0 + paso * 0.33, y - 26, x0 + paso * 0.66, y + 26, x0 + paso, y)
            p.drawPath(ruta)


class _Campo(QWidget):
    def __init__(self, etiqueta, ayuda="", clave=False, padre=None):
        super().__init__(padre)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(5)
        et = QLabel(etiqueta)
        et.setStyleSheet("font-size:13px;font-weight:700;")
        v.addWidget(et)
        self.e = QLineEdit()
        self.e.setMinimumHeight(44)
        self.e.setPlaceholderText(ayuda)
        self.e.setStyleSheet(f"QLineEdit{{font-size:14px;border-radius:10px;padding:11px 14px;"
                             f"background:{C['superficie2']};border:1px solid {C['borde_claro']};}}"
                             f"QLineEdit:focus{{border:2px solid {C['acento']};}}")
        if clave:
            self.e.setEchoMode(QLineEdit.Password)
            self.ojo = QAction(QIcon(iconos.pixmap("ojo", 18, C["texto2"])), "Mostrar", self.e)
            self.ojo.triggered.connect(self._alternar)
            self.e.addAction(self.ojo, QLineEdit.TrailingPosition)
        v.addWidget(self.e)

    def _alternar(self):
        ver = self.e.echoMode() == QLineEdit.Password
        self.e.setEchoMode(QLineEdit.Normal if ver else QLineEdit.Password)
        self.ojo.setIcon(QIcon(iconos.pixmap("ojo_tachado" if ver else "ojo", 18, C["texto2"])))

    def texto(self):
        return self.e.text()


# Se enciende cuando Google este configurado en Supabase (cuentas.con_google ya funciona).
CON_GOOGLE = False


class VentanaAcceso(QWidget):
    """Se cierra emitiendo `entro(cuenta, recordar)`."""

    entro = Signal(dict, bool)

    def __init__(self):
        super().__init__()
        self.cuentas = Cuentas()
        self.setObjectName("raiz")
        self.setWindowTitle("Caudal")
        self.setWindowIcon(QIcon(iconos.icono_app(256)))
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        self.resize(1080, 740)
        self.setMinimumSize(900, 700)

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(_Arte(), 46)

        derecha = QWidget()
        derecha.setObjectName("lado_formulario")
        derecha.setAttribute(Qt.WA_StyledBackground, True)
        derecha.setStyleSheet(f"QWidget#lado_formulario{{background:{C['panel']};}}")
        vd = QVBoxLayout(derecha)
        vd.setContentsMargins(64, 24, 64, 20)
        vd.addStretch(1)
        caja = QWidget()
        caja.setFixedWidth(400)
        caja.setMinimumHeight(620)
        vc = QVBoxLayout(caja)
        vc.setContentsMargins(0, 0, 0, 0)
        vc.setSpacing(12)

        self.et_titulo = QLabel("")
        self.et_titulo.setStyleSheet("font-size:30px;font-weight:900;")
        vc.addWidget(self.et_titulo)
        self.et_sub = QLabel("")
        self.et_sub.setObjectName("secundario")
        self.et_sub.setWordWrap(True)
        vc.addWidget(self.et_sub)

        pestanas = QHBoxLayout()
        pestanas.setSpacing(0)
        self.bt_entrar = QPushButton("Iniciar sesión")
        self.bt_crear = QPushButton("Crear cuenta")
        for i, b in enumerate((self.bt_entrar, self.bt_crear)):
            b.setObjectName("pestana")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, i=i: self._modo(i))
            pestanas.addWidget(b)
        pestanas.addStretch(1)
        vc.addLayout(pestanas)

        self.pila = QStackedWidget()
        # --- entrar
        p1 = QWidget()
        v1 = QVBoxLayout(p1)
        v1.setContentsMargins(0, 6, 0, 0)
        v1.setSpacing(14)
        self.e_usuario = _Campo("Usuario", "tu usuario")
        self.e_clave = _Campo("Contraseña", "tu contraseña", clave=True)
        v1.addWidget(self.e_usuario)
        v1.addWidget(self.e_clave)
        self.pila.addWidget(p1)
        # --- crear
        p2 = QWidget()
        v2 = QVBoxLayout(p2)
        v2.setContentsMargins(0, 6, 14, 0)   # sitio para la barra de desplazamiento
        v2.setSpacing(10)
        self.n_nombre = _Campo("Tu nombre y apellido", "como aparece en tu documento")
        self.n_usuario = _Campo("Usuario", "de 3 a 30 letras o números, sin espacios")
        self.n_clave = _Campo("Contraseña", "al menos 6 caracteres", clave=True)
        self.n_clave2 = _Campo("Repite la contraseña", "la misma de arriba", clave=True)
        for w in (self.n_nombre, self.n_usuario, self.n_clave, self.n_clave2):
            v2.addWidget(w)
        from .legal_ui import CamposPerfil, CasillasLegales
        self.n_perfil = CamposPerfil(p2)
        v2.addWidget(self.n_perfil)
        self.n_legal = CasillasLegales(p2)
        v2.addWidget(self.n_legal)
        # el formulario de registro es largo: va con barra si la ventana es baja
        from PySide6.QtWidgets import QScrollArea
        envoltura = QScrollArea()
        envoltura.setWidgetResizable(True)
        envoltura.setFrameShape(QFrame.NoFrame)
        envoltura.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        envoltura.setWidget(p2)
        envoltura.setStyleSheet("QScrollArea{background:transparent;}")
        p2.setStyleSheet("background:transparent;")
        self.pila.addWidget(envoltura)
        vc.addWidget(self.pila)

        self.recordar = QCheckBox("Mantener la sesión iniciada")
        self.recordar.setChecked(True)
        self.recordar.setCursor(Qt.PointingHandCursor)
        vc.addWidget(self.recordar)

        self.et_error = QLabel("")
        self.et_error.setWordWrap(True)
        self.et_error.setStyleSheet(f"color:{C['error']};font-size:13px;font-weight:600;"
                                    f"background:rgba(242,85,90,0.10);border-radius:8px;"
                                    "padding:9px 12px;")
        self.et_error.hide()
        vc.addWidget(self.et_error)

        self.bt_accion = QPushButton("")
        self.bt_accion.setObjectName("principal")
        self.bt_accion.setFixedHeight(46)
        self.bt_accion.setCursor(Qt.PointingHandCursor)
        self.bt_accion.setStyleSheet(
            f"QPushButton{{background:{C['acento']};color:{C['acento_texto']};border:none;"
            f"border-radius:23px;font-size:15px;font-weight:800;}}"
            f"QPushButton:hover{{background:{C['acento_alto']};}}"
            f"QPushButton:pressed{{background:{C['acento_bajo']};}}")
        self.bt_accion.clicked.connect(self._enviar)
        vc.addWidget(self.bt_accion)

        separador = QLabel("o")
        separador.setObjectName("ayuda")
        separador.setAlignment(Qt.AlignCenter)
        vc.addWidget(separador)

        self.bt_google = QPushButton("  Continuar con Google")
        self.bt_google.setIcon(QIcon(_icono_google()))
        self.bt_google.setFixedHeight(46)
        self.bt_google.setCursor(Qt.PointingHandCursor)
        self.bt_google.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#1F1F1F;border:none;border-radius:23px;"
            "font-size:15px;font-weight:700;}"
            "QPushButton:hover{background:#ECEFF3;}"
            "QPushButton:pressed{background:#DADFE6;}")
        self.bt_google.clicked.connect(self._google)
        vc.addWidget(self.bt_google)
        # entrar con Google: listo pero apagado hasta configurar el proveedor en Supabase
        separador.setVisible(CON_GOOGLE)
        self.bt_google.setVisible(CON_GOOGLE)

        pie = QLabel("La misma cuenta sirve en Windows y en Android. Lo que descargas "
                     "se queda en cada equipo.")
        pie.setWordWrap(True)
        pie.setObjectName("ayuda")
        pie.setAlignment(Qt.AlignCenter)
        vc.addWidget(pie)

        vd.addWidget(caja, 0, Qt.AlignHCenter)
        vd.addStretch(1)
        h.addWidget(derecha, 54)

        for campo in (self.e_usuario, self.e_clave, self.n_nombre, self.n_usuario,
                      self.n_clave, self.n_clave2):
            campo.e.returnPressed.connect(self._enviar)
            campo.e.textEdited.connect(lambda _t: self.et_error.hide())

        ultimo = self.cuentas.ultimo_usuario()
        if ultimo:
            self.e_usuario.e.setText(ultimo)
        self._modo(0 if self.cuentas.hay_cuentas() else 1)

    def closeEvent(self, e):
        # cerrar la pantalla de entrada sin entrar = cerrar Caudal
        if not getattr(self, "_entro", False):
            from PySide6.QtWidgets import QApplication
            QApplication.quit()
        super().closeEvent(e)

    def _modo(self, i):
        self.pila.setCurrentIndex(i)
        self.bt_entrar.setChecked(i == 0)
        self.bt_crear.setChecked(i == 1)
        self.et_error.hide()
        if i == 0:
            self.et_titulo.setText("Hola de nuevo")
            self.et_sub.setText("Inicia sesión para seguir donde lo dejaste.")
            self.bt_accion.setText("Iniciar sesión")
            (self.e_clave if self.e_usuario.texto() else self.e_usuario).e.setFocus()
        else:
            self.et_titulo.setText("Crea tu cuenta")
            primera = not self.cuentas.hay_cuentas()
            self.et_sub.setText("Es gratis y sirve en todos tus dispositivos."
                                + (" Lo que ya tenías en Caudal pasa a esta cuenta." if primera else ""))
            self.bt_accion.setText("Crear cuenta y empezar")
            self.n_nombre.e.setFocus()

    def _error(self, texto):
        self.et_error.setText(texto)
        self.et_error.show()

    def _entrada_lista(self, cuenta):
        self._ocupado = False
        self._entro = True
        recordar = self.recordar.isChecked()
        if recordar:
            self.cuentas.recordar(cuenta)
        else:
            self.cuentas.olvidar()
        self.cuentas.anotar_ultimo(cuenta["usuario"])
        self.entro.emit(cuenta, recordar)

    def _google(self):
        # mientras se espera al navegador, el mismo boton cancela
        if getattr(self, "_esperando_google", False):
            self._cancelar_google = True
            return
        if getattr(self, "_ocupado", False):
            return
        self._ocupado = True
        self._esperando_google = True
        self._cancelar_google = False
        self.et_error.hide()
        self.bt_accion.setEnabled(False)
        self.bt_google.setText("  Elige tu cuenta en el navegador…  (cancelar)")

        def terminar():
            self._ocupado = False
            self._esperando_google = False
            self.bt_accion.setEnabled(True)
            self.bt_google.setText("  Continuar con Google")

        def listo(cuenta):
            self._esperando_google = False
            self._entrada_lista(cuenta)

        def fallo(e):
            terminar()
            texto = str(e) if isinstance(e, ErrorCuenta) else \
                "No se pudo conectar. Revisa tu internet y vuelve a probar."
            if texto:
                self._error(texto)

        from ..hilos import en_segundo_plano
        en_segundo_plano(self.cuentas.con_google, lambda: self._cancelar_google,
                         ok=listo, error=fallo, dueno=self)

    def _enviar(self):
        if getattr(self, "_ocupado", False):
            return
        entrar = self.pila.currentIndex() == 0
        if entrar:
            usuario, clave = self.e_usuario.texto(), self.e_clave.texto()
            if not usuario.strip():
                self._error("Escribe tu usuario.")
                return
            funcion, args = self.cuentas.entrar, (usuario, clave)
        else:
            if self.n_clave.texto() != self.n_clave2.texto():
                self._error("Las dos contraseñas no coinciden.")
                return
            from .. import legal
            x = self.n_perfil.valores()
            problema = legal.revisar_perfil(self.n_nombre.texto(), x["nacimiento"], x["pais"],
                                            x["permiso_tutor"])
            if problema:
                self._error(problema)
                return
            if not self.n_legal.acepta.isChecked():
                self._error("Para crear tu cuenta tienes que aceptar los Términos y la Política de privacidad.")
                return
            extra = legal.extra_registro(x["nacimiento"], x["pais"], x["genero"],
                                         self.n_legal.comparte.isChecked(), x["permiso_tutor"])
            funcion, args = self.cuentas.crear, (self.n_usuario.texto(), self.n_clave.texto(),
                                                 self.n_nombre.texto(), extra)
        # la red va en segundo plano: la ventana no se congela
        self._ocupado = True
        self.et_error.hide()
        texto = self.bt_accion.text()
        self.bt_accion.setText("Entrando…" if entrar else "Creando tu cuenta…")
        self.bt_accion.setEnabled(False)

        def listo(cuenta):
            self._entrada_lista(cuenta)

        def fallo(e):
            self._ocupado = False
            self.bt_accion.setText(texto)
            self.bt_accion.setEnabled(True)
            self._error(str(e) if isinstance(e, ErrorCuenta)
                        else "No se pudo conectar. Revisa tu internet y vuelve a probar.")

        from ..hilos import en_segundo_plano
        en_segundo_plano(funcion, *args, ok=listo, error=fallo, dueno=self)


def _icono_google(lado=20):
    """La "G" de Google con sus cuatro colores, dibujada (sin imagenes)."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
    px = QPixmap(lado * 2, lado * 2)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    t = lado * 2
    grosor = t * 0.18
    r = QRectF(t * 0.12, t * 0.12, t * 0.76, t * 0.76)

    def arco(desde, cuanto, color):
        p.setPen(QPen(QColor(color), grosor))
        p.drawArc(r, int(desde * 16), int(cuanto * 16))

    arco(45, 90, "#EA4335")
    arco(135, 99, "#FBBC05")
    arco(234, 99, "#34A853")
    arco(333, 63, "#4285F4")
    p.setPen(QPen(QColor("#4285F4"), grosor))
    p.drawLine(QPointF(t / 2, t / 2), QPointF(t * 0.88, t / 2))
    p.end()
    px.setDevicePixelRatio(2)
    return px


def _sin_usar():  # pragma: no cover
    return QFont, QFrame, QRectF, fuente
