# -*- coding: utf-8 -*-
"""El codificador de QR propio (descargador/qr.py): estructura, mismo resultado
que la app móvil y, si OpenCV está instalado, que de verdad se lee."""

import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import qr  # noqa: E402

ENLACE = "https://caudal-musica.netlify.app/fiesta/ABC234"
# el mismo valor sale del codificador de la app móvil (app/lib/nucleo/qr.dart)
SHA1_ENLACE = "9e825eb48b85a93d2fdf2f66e14ddb45165290fa"


def test_golden_igual_que_la_app_movil():
    m = qr.matriz(ENLACE)
    assert len(m) == 33                       # versión 4
    assert qr.mascara_elegida(ENLACE) == 4
    assert hashlib.sha1(qr.como_texto(m).encode()).hexdigest() == SHA1_ENLACE
    assert qr.mascara_elegida("HOLA") == 0 and len(qr.matriz("HOLA")) == 21


@pytest.mark.parametrize("largo,version", [(1, 1), (14, 1), (15, 2), (62, 4), (213, 10)])
def test_version_mas_pequena(largo, version):
    m = qr.matriz("a" * largo)
    assert len(m) == 21 + 4 * (version - 1)


def test_demasiado_largo():
    with pytest.raises(qr.ErrorQR):
        qr.matriz("a" * 214)


def _finder(m, x0, y0):
    for dy in range(7):
        for dx in range(7):
            d = max(abs(dx - 3), abs(dy - 3))
            assert m[y0 + dy][x0 + dx] == (d != 2), (x0, y0, dx, dy)


def test_estructura():
    for texto in (ENLACE, "x" * 150, "ñandú 🎉"):
        m = qr.matriz(texto)
        n = len(m)
        assert all(len(f) == n for f in m)
        _finder(m, 0, 0)
        _finder(m, n - 7, 0)
        _finder(m, 0, n - 7)
        # separadores blancos y líneas de tiempo
        assert not any(m[7][x] for x in range(8)) and not any(m[y][7] for y in range(8))
        assert [m[6][x] for x in range(8, n - 8)] == [x % 2 == 0 for x in range(8, n - 8)]
        assert [m[y][6] for y in range(8, n - 8)] == [y % 2 == 0 for y in range(8, n - 8)]
        assert m[n - 8][8] is True             # el módulo oscuro fijo
        assert qr.como_texto(m).count("\n") == n - 1


def test_formato_en_las_dos_copias():
    m = qr.matriz(ENLACE)
    n = len(m)
    # m[fila][columna]: la copia junto al finder de arriba a la izquierda y la partida en dos
    a = [m[i][8] for i in range(6)] + [m[7][8], m[8][8], m[8][7]] + [m[8][14 - i] for i in range(9, 15)]
    b = [m[8][n - 1 - i] for i in range(8)] + [m[n - 15 + i][8] for i in range(8, 15)]
    assert a == b
    # y es el formato de nivel M con la máscara elegida
    dato = qr.mascara_elegida(ENLACE)
    r = dato
    for _ in range(10):
        r = (r << 1) ^ ((r >> 9) * 0x537)
    bits = (dato << 10 | r) ^ 0x5412
    assert a == [bool((bits >> i) & 1) for i in range(15)]


def test_se_lee_con_opencv():
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    for texto in (ENLACE, "hola", "x" * 150, "ñandú 🎉 fiesta"):
        m = qr.matriz(texto)
        n, borde, s = len(m), 4, 8
        img = np.full(((n + 2 * borde) * s,) * 2, 255, np.uint8)
        for y in range(n):
            for x in range(n):
                if m[y][x]:
                    img[(y + borde) * s:(y + borde + 1) * s, (x + borde) * s:(x + borde + 1) * s] = 0
        leido, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
        assert leido == texto
