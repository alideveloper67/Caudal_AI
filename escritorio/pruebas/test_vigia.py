# -*- coding: utf-8 -*-
"""Vigía de tirones (descargador/vigia.py): un bloqueo de 300 ms del hilo principal queda anotado."""

import os
import re
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import vigia as V  # noqa: E402


def test_registra_bloqueo_del_hilo_principal(tmp_path):
    app = QApplication.instance() or QApplication([])
    V.iniciar(app, tmp_path)
    QTimer.singleShot(100, lambda: time.sleep(0.3))
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 1.0:
        app.processEvents()
        time.sleep(0.005)
    texto = V.resumen()
    ms = [int(m) for m in re.findall(r"^\s+(\d+) ms", texto, re.M)]
    assert ms, texto
    assert max(ms) >= 200, texto
