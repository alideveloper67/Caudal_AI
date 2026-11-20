# -*- coding: utf-8 -*-
"""Fabrica el «sonido suave» del despertador para el teléfono (Android lo toca con la app cerrada desde
res/raw; la app lo usa desde sus assets). Es el mismo que fabrica Caudal Escritorio al vuelo
(escritorio/descargador/despertador.py), así suenan igual.

    python herramientas/generar_tono_despertador.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "escritorio"))

from descargador import despertador  # noqa: E402

DESTINOS = [
    RAIZ / "app" / "android" / "app" / "src" / "main" / "res" / "raw" / "despertador_amanecer.wav",
    RAIZ / "app" / "assets" / "despertador" / "amanecer.wav",
]


def main():
    muestras = despertador.sintetizar_tono()
    for d in DESTINOS:
        despertador.escribir_wav(d, muestras)
        print(f"{d}  ({d.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
