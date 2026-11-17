# Cinnamoroll (interpretacion, camino C). Lienzo 46x42. f=0 de pie; f=1 las orejas largas se levantan (aleteo),
# cuerpo 1 px arriba y la cola enroscada se ladea.
import math
BLANCO = '#fbfbff'    # cabeza y cuerpo
BLANCO_B = '#fbfbfe'  # brazos, pies y cola (interior)
OREJA = '#d6ecff'     # orejas celestes
OJO = '#1d2a6b'
AZUL = '#4f8ef0'
BRILLO = '#e6f0ff'
BLANCO_C = '#fbfbfd'  # cuerpo (interior: se separa de la cabeza)
MEJ = '#ffa3c4'
BOCA = '#6a3f6e'
ESPIRAL = '#a9b8ea'


def dibujar(M, f=0):
    dy = -1 if f else 0
    # ---- cola enroscada (detras, a la derecha)
    tx, ty = 34.6 + (0.4 if f else 0), 34.4 - (1.0 if f else 0)
    M.elipse(tx, ty, 3.6, 3.3, BLANCO_B, rot=(-15 if f else 0))
    # ---- cuerpo
    M.elipse(17.6, 39.8, 3.8, 2.2, BLANCO_B, rot=-4)
    M.elipse(27.4, 39.8, 3.8, 2.2, BLANCO_B, rot=4)
    M.elipse(22.5, 33.2 + dy * 0.5, 8.6, 6.6, BLANCO_C)
    M.elipse(15.2, 31.8 + dy, 2.0, 2.4, BLANCO_B, rot=30)
    M.elipse(29.8, 31.8 + dy, 2.0, 2.4, BLANCO_B, rot=-30)
    # ---- orejas larguisimas (f1: se levantan como alas)
    if f:
        izq = [(13.0, 6.4), (6.0, 6.0), (1.2, 9.0), (0.8, 13.4), (3.4, 14.0), (7.6, 12.4), (13.4, 13.0)]
        der = [(32.0, 6.4), (39.0, 6.0), (43.8, 9.0), (44.2, 13.4), (41.6, 14.0), (37.4, 12.4), (31.6, 13.0)]
    else:
        izq = [(13.0, 7.0), (6.4, 8.6), (2.4, 14.0), (1.6, 21.4), (4.4, 22.6), (7.4, 17.0), (13.0, 13.4)]
        der = [(32.0, 7.0), (38.6, 8.6), (42.6, 14.0), (43.4, 21.4), (40.6, 22.6), (37.6, 17.0), (32.0, 13.4)]
    M.blob([(x, y + dy) for x, y in izq], OREJA)
    M.blob([(x, y + dy) for x, y in der], OREJA)
    # ---- cabeza
    M.elipse(22.5, 15.4 + dy, 14.2, 11.4, BLANCO)
    for cx in (17.5, 27.5):
        M.elipse(cx, 17.6 + dy, 1.6, 2.6, OJO)
        M.rect(cx - 1.5, 18.0 + dy, cx + 1.5, 20.0 + dy, AZUL)
        M.rect(cx - 1.5, 16.0 + dy, cx - 0.5, 17.0 + dy, BRILLO)
    M.elipse(13.0, 21.5 + dy, 2.0, 0.6, MEJ)
    M.elipse(32.0, 21.5 + dy, 2.0, 0.6, MEJ)
    # boca «w» chiquita
    M.rect(21.0, 21.0 + dy, 22.0, 22.0 + dy, BOCA)
    M.rect(22.0, 22.0 + dy, 23.0, 23.0 + dy, BOCA)
    M.rect(23.0, 21.0 + dy, 24.0, 22.0 + dy, BOCA)
