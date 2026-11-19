# -*- coding: utf-8 -*-
"""«¿Qué canción era?» (donadores): busca en tu historial por fecha y por texto.

Escribe algo de la canción («shakira», «esa de la guitarra») y/o una fecha («ayer», «15/11», «el lunes»,
«noviembre»), o elige un rango con el calendario. Doble clic en un resultado y suena. La lógica está en
`quecancion`; aquí solo la pantalla. El historial se lee en segundo plano (puede tener decenas de miles de
escuchas) y no se vuelve a leer mientras el cuadro está abierto."""

from datetime import datetime

from PySide6.QtCore import QDate, QTimer, Qt
from PySide6.QtWidgets import (QCheckBox, QDateEdit, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout)

from .. import mixes, quecancion as Q
from ..hilos import en_segundo_plano

PAUSA_ESCRITURA_MS = 220


class DialogoQueCancion(QDialog):
    def __init__(self, ctx, padre=None, historial=None):
        super().__init__(padre)
        self.ctx = ctx
        self.historial = historial            # si ya viene dado (pruebas), no se lee de la base
        self.resultados = []
        self.setWindowTitle("¿Qué canción era?")
        self.setMinimumSize(520, 560)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 16)
        v.setSpacing(10)
        t = QLabel("¿Qué canción era?")
        t.setObjectName("titulo_seccion")
        v.addWidget(t)
        ayuda = QLabel("Busca en lo que ya escuchaste: una palabra del título o del artista, una fecha "
                       "(«ayer», «15/11», «el lunes», «noviembre»)… o las dos cosas.")
        ayuda.setObjectName("secundario")
        ayuda.setWordWrap(True)
        v.addWidget(ayuda)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Ej.: shakira ayer · noviembre · 15/11 · luna")
        self.campo.setClearButtonEnabled(True)
        v.addWidget(self.campo)
        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.usar_fechas = QCheckBox("Solo entre")
        self.desde = QDateEdit(QDate.currentDate().addDays(-7))
        self.hasta = QDateEdit(QDate.currentDate())
        for d in (self.desde, self.hasta):
            d.setCalendarPopup(True)
            d.setDisplayFormat("dd/MM/yyyy")
            d.setEnabled(False)
        fila.addWidget(self.usar_fechas)
        fila.addWidget(self.desde)
        fila.addWidget(QLabel("y"))
        fila.addWidget(self.hasta)
        fila.addStretch(1)
        v.addLayout(fila)
        self.estado = QLabel("Leyendo tu historial…")
        self.estado.setObjectName("secundario")
        self.estado.setWordWrap(True)
        v.addWidget(self.estado)
        self.lista = QListWidget()
        self.lista.setUniformItemSizes(True)
        self.lista.setAlternatingRowColors(False)
        v.addWidget(self.lista, 1)

        self.aviso = QLabel("🔒 «¿Qué canción era?» es exclusivo para donadores.")
        self.aviso.setObjectName("ayuda")
        self.aviso.setWordWrap(True)
        self.aviso.setAlignment(Qt.AlignCenter)
        v.addWidget(self.aviso)
        self.fila_bloqueo = QHBoxLayout()
        self.fila_bloqueo.addStretch(1)
        from .canje_pase import boton_codigo
        from .donar import boton_donar
        self.bt_donar = boton_donar(texto="Donar aquí")
        self.bt_codigo = boton_codigo(ctx, texto="Tengo un código de prueba")
        self.fila_bloqueo.addWidget(self.bt_donar)
        self.fila_bloqueo.addWidget(self.bt_codigo)
        self.fila_bloqueo.addStretch(1)
        v.addLayout(self.fila_bloqueo)

        botones = QHBoxLayout()
        botones.addStretch(1)
        self.bt_escuchar = QPushButton("Escuchar")
        self.bt_gusta = QPushButton("Me gusta")
        self.bt_gusta.setObjectName("contorno")
        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("contorno")
        self.bt_escuchar.clicked.connect(self._escuchar)
        self.bt_gusta.clicked.connect(self._gusta)
        cerrar.clicked.connect(self.accept)
        for b in (self.bt_escuchar, self.bt_gusta, cerrar):
            botones.addWidget(b)
        v.addLayout(botones)

        self._t_buscar = QTimer(self)
        self._t_buscar.setSingleShot(True)
        self._t_buscar.setInterval(PAUSA_ESCRITURA_MS)
        self._t_buscar.timeout.connect(self.buscar)
        self.campo.textChanged.connect(lambda _t: self._t_buscar.start())
        self.usar_fechas.toggled.connect(self._fechas_activadas)
        self.desde.dateChanged.connect(lambda _d: self._t_buscar.start())
        self.hasta.dateChanged.connect(lambda _d: self._t_buscar.start())
        self.lista.itemDoubleClicked.connect(lambda _i: self._escuchar())
        self.lista.currentRowChanged.connect(lambda _r: self._botones())
        g = getattr(ctx, "premium", None)
        if g is not None:
            g.cambiado.connect(self._pintar_bloqueo)
        self._pintar_bloqueo()
        self._botones()
        if self.historial is not None:
            self.estado.setText("")
            self.buscar()
        else:
            en_segundo_plano(self._leer, ok=self._llego, error=self._fallo, dueno=self)

    # ------------------------------------------------------------ datos
    def _leer(self):
        copiar = getattr(self.ctx.coleccion, "copia_de_lectura", None)
        if copiar is None:
            return mixes.leer_historial(self.ctx.coleccion, limite=200000)
        with copiar() as c:
            return mixes.leer_historial(c, limite=200000)

    def _llego(self, historial):
        self.historial = historial
        self.estado.setText("")
        self.buscar()

    def _fallo(self, _e):
        self.estado.setText("No se pudo leer tu historial. Vuelve a intentarlo en un momento.")

    def _premium(self):
        g = getattr(self.ctx, "premium", None)
        return bool(g is not None and g.premium)

    def _pintar_bloqueo(self):
        premium = self._premium()
        self.aviso.setVisible(not premium)
        self.bt_donar.setVisible(not premium)
        self.bt_codigo.setVisible(not premium)
        self.campo.setEnabled(premium)
        self.usar_fechas.setEnabled(premium)
        self._fechas_activadas(self.usar_fechas.isChecked())
        self._botones()
        if self.historial is not None:
            self.buscar()

    def _fechas_activadas(self, si):
        for d in (self.desde, self.hasta):
            d.setEnabled(bool(si) and self._premium())
        self._t_buscar.start()

    # ------------------------------------------------------------ búsqueda
    def _rango(self):
        if not self.usar_fechas.isChecked():
            return None, None
        d, h = self.desde.date().toPython(), self.hasta.date().toPython()
        return (d, h) if d <= h else (h, d)

    def buscar(self):
        """Pone en la lista lo que cumple el texto y las fechas. Sin donador no muestra nada."""
        self.lista.clear()
        self.resultados = []
        if self.historial is None:
            return
        if not self._premium():
            self.estado.setText("Hazte donador para buscar en tu historial.")
            self._botones()
            return
        texto = self.campo.text().strip()
        desde, hasta = self._rango()
        if not texto and desde is None:
            self.estado.setText(f"Escribe algo o elige fechas. Tu historial tiene {len(self.historial)} escuchas.")
            self._botones()
            return
        self.resultados = Q.buscar(self.historial, texto, desde, hasta)
        ahora = datetime.now()
        for r in self.resultados:
            p = r["pista"]
            arts = ", ".join(a.get("nombre", "") for a in p.get("artistas") or [] if a.get("nombre")) \
                or p.get("artista") or ""
            veces = f"  ·  {r['veces']} veces" if r["veces"] > 1 else ""
            it = QListWidgetItem(f"{p.get('titulo') or 'Sin título'}  —  {arts}\n{Q.texto_fecha(r['fecha'], ahora)}{veces}")
            it.setData(Qt.UserRole, p.get("clave"))
            self.lista.addItem(it)
        n = len(self.resultados)
        self.estado.setText("No encontré nada con eso. Prueba con menos palabras o con otras fechas." if n == 0
                            else f"{n} {'canción' if n == 1 else 'canciones'}" + (
                                f" (se muestran las {Q.MAXIMO} más recientes)" if n >= Q.MAXIMO else ""))
        if n:
            self.lista.setCurrentRow(0)
        self._botones()

    def _botones(self):
        hay = self._premium() and 0 <= self.lista.currentRow() < len(self.resultados)
        self.bt_escuchar.setEnabled(hay)
        self.bt_gusta.setEnabled(hay)

    def _actual(self):
        i = self.lista.currentRow()
        return self.resultados[i]["pista"] if 0 <= i < len(self.resultados) else None

    def _escuchar(self):
        p = self._actual()
        if p is not None and self._premium():
            self.ctx.reproducir_pista(p)

    def _gusta(self):
        p = self._actual()
        if p is not None and self._premium():
            self.ctx.alternar_me_gusta(p)


def abrir_que_cancion(ctx, padre=None):
    DialogoQueCancion(ctx, padre).exec()
