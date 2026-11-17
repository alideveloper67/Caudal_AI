# Maestro de Totoro (3/4 hacia la derecha, hojita en la cabeza). Lienzo 46x42.
# f = cuadro: 0 de pie; 1 cuerpo 1 px arriba, orejas que se mueven, hojita inclinada y brazo levantado.
GRIS = '#8c949e'
GRIS_B = '#8c949f'    # brazos y patas (línea interior)
OREJA = '#8c939e'     # orejas (línea interior)
CREMA = '#f1e6c6'
MARCA = '#6e7682'     # marcas en V del pecho
OJO_B = '#fdfdf6'
OJO = '#16161e'
BRILLO = '#ffffff'
NARIZ = '#2e3038'
BOCA = '#3a2a30'
DIENTE = '#ffffff'
BIGOTE = '#3e4450'
HOJA = '#5cb84a'
HOJA_T = '#2f7a2c'    # nervio y tallo
UNA = '#e8e2d0'       # garritas


def pose(M, f):
    up = 1 if f else 0
    # orejas puntiagudas (detrás de la cabeza)
    ol, orr = (-8, 10) if f == 0 else (-16, 4)
    M.elipse(15.0, 6.0 - up, 2.6, 6.0, OREJA, rot=ol)
    M.elipse(30.5, 5.6 - up, 2.6, 6.0, OREJA, rot=orr)
    # brazos: el izquierdo (de la persona) se levanta en el cuadro 1
    if f == 0:
        M.elipse(4.6, 27.0 - up, 3.0, 6.2, GRIS_B, rot=18)
    else:
        M.elipse(4.0, 21.5 - up, 3.0, 6.2, GRIS_B, rot=-25)
    M.elipse(41.6, 27.0 - up, 3.0, 6.2, GRIS_B, rot=-14)
    # cuerpo en forma de pera
    M.blob([(23, 4.5 - up), (31, 6.5 - up), (36, 13 - up), (40.5, 23 - up), (42, 31), (39.5, 37.5), (23, 39.8),
            (7, 37.5), (4.5, 31), (6, 23 - up), (10, 13 - up), (15, 6.5 - up)], GRIS)
    # panza crema
    M.blob([(24, 19.5 - up), (31.5, 21.5 - up), (36.5, 28 - up), (35.5, 35), (24.5, 38.0), (12.5, 35), (12, 28 - up),
            (16.5, 21.5 - up)], CREMA)
    # marcas en V (chevrones) del pecho: 3 arriba, 4 abajo
    for y, xs in ((24.3 - up, (19.0, 24.4, 29.8)), (28.6 - up, (16.4, 21.6, 26.8, 32.0))):
        for x in xs:
            M.curva([(x - 1.6, y + 1.2), (x, y - 0.4), (x + 1.6, y + 1.2)], MARCA, ancho=1.0, suave=False)
    # patas con garritas
    M.elipse(15.0, 39.6, 4.4, 2.2, GRIS_B)
    M.elipse(32.0, 39.6, 4.4, 2.2, GRIS_B)
    for x in (13.0, 15.0, 17.0, 30.0, 32.0, 34.0):
        M.punto(x, 40.6, UNA, r=0.5)
    # ojos redondos con pupila
    hy = 12.5 - up
    for cx in (17.3, 29.6):
        M.elipse(cx, hy, 2.9, 2.9, OJO_B)
        M.elipse(cx + 0.3, hy + 0.2, 1.5, 1.6, OJO)
        M.punto(cx - 0.3, hy - 0.6, BRILLO, r=0.42)
    # nariz pequeña
    M.blob([(22.0, hy - 0.4), (25.6, hy - 0.4), (23.8, hy + 1.0)], NARIZ)
    # bigotes (3 por lado, abiertos)
    for dy, a in ((-0.4, -1.6), (1.6, 0.0), (3.6, 1.6)):
        M.curva([(7.6, hy + 2.0 + dy + a), (11.6, hy + 2.0 + dy)], BIGOTE, ancho=0.85, suave=False)
        M.curva([(35.4, hy + 2.0 + dy), (39.6, hy + 2.0 + dy + a)], BIGOTE, ancho=0.85, suave=False)
    # sonrisa ancha con dientitos
    M.blob([(15.6, hy + 4.0), (23.8, hy + 5.0), (32.0, hy + 3.8), (28.5, hy + 6.6), (23.8, hy + 7.4), (19.0, hy + 6.6)], BOCA)
    M.rect(19.4, hy + 4.3, 21.0, hy + 5.2, DIENTE)
    M.rect(26.4, hy + 4.3, 28.0, hy + 5.2, DIENTE)
    # hojita sobre la cabeza
    rot = -20 if f == 0 else 10
    M.curva([(23.0, 5.5 - up), (23.2, 3.0 - up)], HOJA_T, ancho=0.9, suave=False)
    M.elipse(23.4 + (0 if f == 0 else 0.6), 1.9 - up * 0.5, 4.2, 1.8, HOJA, rot=rot)
    M.curva([(20.6, 2.6 - up * 0.5 + (0.6 if f == 0 else -0.6)), (26.0, 1.2 - up * 0.5 + (-0.6 if f == 0 else 0.6))], HOJA_T, ancho=0.6, suave=False)
