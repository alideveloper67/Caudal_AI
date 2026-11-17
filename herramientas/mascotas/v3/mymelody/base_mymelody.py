# My Melody (interpretacion, camino C). Lienzo 46x42. f=0 de pie; f=1 saluda, orejas se mecen, cuerpo 1 px arriba.
ROSA = '#f7a1c4'      # capucha
ROSA_B = '#f7a1c5'    # vestido, brazos (interior)
ROSA_IN = '#fdd3e4'   # dentro de las orejas
BLANCO = '#fbfbff'    # cara
BLANCO_B = '#fbfbfe'  # manos y pies
OJO = '#1b1426'
BRILLO = '#dfe8ff'
NARIZ = '#f6c21c'
MEJ = '#ff8fb4'
FLOR = '#ee4f86'
FLOR_C = '#ffd84a'
FLOR_B = '#ffc4d8'


def dibujar(M, f=0):
    dy = -1 if f else 0
    s = 1.2 if f else 0.0          # vaiven de las puntas de las orejas
    # ---- orejas largas (detras de la capucha)
    M.blob([(12.0, 13 + dy), (9.4, 6 + dy), (7.6 - s, 1.2 + dy), (10.6 - s, 0.4 + dy), (14.6, 6 + dy), (17.4, 12 + dy)], ROSA)
    M.blob([(27.0, 11 + dy), (31.0, 4.5 + dy), (36.4 + s, 1.6 + dy), (38.0 + s, 3.4 + dy), (34.0, 7.5 + dy), (32.2, 13 + dy)], ROSA)
    M.blob([(12.8, 11 + dy), (10.6, 5.5 + dy), (9.6 - s, 2.4 + dy), (12.6, 6 + dy), (15.4, 11 + dy)], ROSA_IN)
    M.blob([(29.0, 11 + dy), (32.2, 5.8 + dy), (35.8 + s, 3.0 + dy), (32.8, 7.6 + dy), (30.8, 12 + dy)], ROSA_IN)
    # ---- cuerpo: vestido rosa, pies blancos
    M.elipse(17.4, 39.7, 4.2, 2.25, BLANCO_B, rot=-4)
    M.elipse(27.4, 39.7, 4.2, 2.25, BLANCO_B, rot=4)
    M.blob([(16.4, 30 + dy), (22.4, 29 + dy), (28.6, 30 + dy), (31.6, 36.4), (30.6, 38.6), (22.4, 39.2), (14.2, 38.6), (13.2, 36.4)], ROSA_B)
    # brazo izquierdo abajo
    M.curva([(16.0, 31.0 + dy), (13.2, 33.6 + dy)], ROSA_B, ancho=3.4)
    M.elipse(12.2, 34.6 + dy, 2.1, 2.0, BLANCO_B)
    # brazo derecho: abajo (f0) o saludando (f1)
    if f:
        M.curva([(28.8, 31.0 + dy), (32.6, 30.0 + dy), (35.2, 27.6 + dy)], ROSA_B, ancho=3.4)
        M.elipse(36.4, 26.2 + dy, 2.4, 2.5, BLANCO_B, rot=25)
    else:
        M.curva([(28.8, 31.0 + dy), (31.6, 33.6 + dy)], ROSA_B, ancho=3.4)
        M.elipse(32.6, 34.6 + dy, 2.1, 2.0, BLANCO_B)
    # ---- capucha y cara
    M.elipse(22.4, 20.4 + dy, 15.2, 11.6, ROSA)
    M.blob([(11.6, 22 + dy), (14.0, 15.2 + dy), (22.4, 13.2 + dy), (30.8, 15.2 + dy), (33.2, 22 + dy), (30.0, 29.0 + dy), (22.4, 30.6 + dy), (14.8, 29.0 + dy)], BLANCO)
    for cx in (17.5, 27.5):
        M.elipse(cx, 22.0 + dy, 1.5, 2.1, OJO)
        M.rect(cx - 0.5, 21.0 + dy, cx + 0.5, 22.0 + dy, BRILLO)
    M.rect(21.0, 25.0 + dy, 24.0, 26.0 + dy, NARIZ)
    M.elipse(14.6, 26.0 + dy, 1.6, 0.9, MEJ)
    M.elipse(30.4, 26.0 + dy, 1.6, 0.9, MEJ)
