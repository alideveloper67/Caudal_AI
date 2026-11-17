# Kuromi (interpretacion, camino C). Lienzo 46x42. f=0 sonrisa traviesa; f=1 guiña un ojo, cola se agita, cuerpo 1 px arriba.
import math
NEGRO = '#463e5e'     # capucha
NEGRO_B = '#463e5f'   # cuerpo, brazos, cola (interior)
BLANCO = '#fbfbff'    # cara
BLANCO_B = '#fbfbfe'  # manos y pies
CALAVERA = '#f78fb8'
CAL_OJO = '#2a2238'
OJO = '#1b1426'
BRILLO = '#dfe8ff'
NARIZ = '#f06a9a'
MEJ = '#ff9cc0'
BOCA = '#2a1a2e'
COLMILLO = '#fffff0'


def dibujar(M, f=0):
    dy = -1 if f else 0
    # ---- cola de diablito (detras)
    tip = (40.4, 27.0) if f else (40.8, 30.6)
    M.curva([(29.0, 35.5), (35.0, 36.4), (39.0, 33.6), tip], NEGRO_B, ancho=1.6)
    ang = math.atan2(tip[1] - 33.6, tip[0] - 39.0)
    px_, py_ = -math.sin(ang), math.cos(ang)
    c, s_ = math.cos(ang), math.sin(ang)
    M.blob([(tip[0] + 3.8 * c, tip[1] + 3.8 * s_),
            (tip[0] + 2.6 * px_ - 0.6 * c, tip[1] + 2.6 * py_ - 0.6 * s_),
            (tip[0] + 0.2 * c, tip[1] + 0.2 * s_),
            (tip[0] - 2.6 * px_ - 0.6 * c, tip[1] - 2.6 * py_ - 0.6 * s_)], NEGRO_B, suavidad=3)
    # ---- orejas puntiagudas de la capucha
    M.blob([(10.0, 15 + dy), (5.6, 8 + dy), (2.6, 1.0 + dy), (8.6, 4.6 + dy), (15.0, 9.6 + dy)], NEGRO)
    M.blob([(30.0, 9.6 + dy), (36.4, 4.6 + dy), (42.6, 1.0 + dy), (39.4, 8 + dy), (35.0, 15 + dy)], NEGRO)
    # ---- cuerpo
    M.elipse(17.4, 39.7, 4.2, 2.25, BLANCO_B, rot=-4)
    M.elipse(27.4, 39.7, 4.2, 2.25, BLANCO_B, rot=4)
    M.blob([(16.4, 30 + dy), (22.4, 29 + dy), (28.6, 30 + dy), (31.4, 36.4), (30.4, 38.6), (22.4, 39.2), (14.4, 38.6), (13.4, 36.4)], NEGRO_B)
    M.curva([(16.0, 31.0 + dy), (13.2, 33.6 + dy)], NEGRO_B, ancho=3.4)
    M.elipse(12.2, 34.6 + dy, 2.1, 2.0, BLANCO_B)
    M.curva([(28.8, 31.0 + dy), (31.4, 33.4 + dy)], NEGRO_B, ancho=3.4)
    M.elipse(32.4, 34.4 + dy, 2.1, 2.0, BLANCO_B)
    # ---- capucha y cara
    M.elipse(22.5, 19.6 + dy, 15.0, 11.6, NEGRO)
    M.blob([(11.8, 23 + dy), (13.6, 17.4 + dy), (22.5, 15.6 + dy), (31.4, 17.4 + dy), (33.2, 23 + dy),
            (30.0, 29.2 + dy), (22.5, 30.8 + dy), (15.0, 29.2 + dy)], BLANCO)
    # calavera rosa en la frente
    M.elipse(22.5, 10.6 + dy, 3.1, 2.6, CALAVERA)
    M.rect(20.6, 12.0 + dy, 24.4, 14.0 + dy, CALAVERA, radio=0.4)
    M.rect(21.0, 10.0 + dy, 22.0, 11.0 + dy, CAL_OJO)
    M.rect(23.0, 10.0 + dy, 24.0, 11.0 + dy, CAL_OJO)
    M.rect(22.0, 13.0 + dy, 23.0, 14.0 + dy, CAL_OJO)
    # ojos: el izquierdo guiña en f1
    if f:
        M.curva([(16.0, 22.8 + dy), (17.5, 21.8 + dy), (19.0, 22.8 + dy)], OJO, ancho=1.0)
    else:
        M.elipse(17.5, 22.4 + dy, 1.5, 2.1, OJO)
        M.rect(17.0, 21.0 + dy, 18.0, 22.0 + dy, BRILLO)
    M.elipse(27.5, 22.4 + dy, 1.5, 2.1, OJO)
    M.rect(27.0, 21.0 + dy, 28.0, 22.0 + dy, BRILLO)
    M.rect(22.0, 25.0 + dy, 24.0, 26.0 + dy, NARIZ)
    # sonrisa de lado con colmillo
    M.rect(22.0, 27.0 + dy, 25.0, 28.0 + dy, BOCA)
    M.rect(25.0, 26.0 + dy, 26.0, 27.0 + dy, BOCA)
    M.rect(23.0, 28.0 + dy, 24.0, 29.0 + dy, COLMILLO)
    M.elipse(14.6, 26.0 + dy, 1.6, 0.9, MEJ)
    M.elipse(30.4, 26.0 + dy, 1.6, 0.9, MEJ)
