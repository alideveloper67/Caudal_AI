# Maestro de Doraemon (3/4 hacia la derecha). Lienzo 46x42.
# f = cuadro: 0 de pie con la mano levantada; 1 saluda más alto, cuerpo 1 px arriba, cola y cascabel se mueven.
AZUL = '#1fa0e6'
AZUL_B = '#1fa0e7'    # brazos (línea interior sobre el cuerpo)
BLANCO = '#fafcff'    # cara y panza
BLANCO_B = '#fafcfe'  # manos y pies (línea interior)
OJO_B = '#fbfdff'     # ojos (blancos con su propia línea)
NEGRO = '#15151f'
ROJO = '#e0262e'      # nariz, collar, cola
ROJO_C = '#e0262f'    # collar
NBRILLO = '#ffffff'
BOCA = '#9a1424'
LENGUA = '#f2667a'
CASC = '#f6c81c'      # cascabel
CASC_L = '#7a4a0a'    # ranura del cascabel
BIGOTE = '#2a2a3a'
BOLSILLO = '#9aa6bc'


def pose(M, f):
    up = 1 if f else 0
    hy = 15.0 - up
    # cola roja (detrás, a la derecha)
    M.capsula(32, 36 - up, 38.5, 33.5 - up - f * 1.5, 0.8, AZUL)
    M.elipse(39.2, 33.0 - up - f * 1.5, 2.0, 2.0, ROJO)
    # cuerpo y panza
    M.elipse(23.5, 34.0 - up, 10.5, 7.0, AZUL)
    M.elipse(24.2, 34.6 - up, 7.6, 5.6, BLANCO)
    # bolsillo semicircular
    M.curva([(19.6, 34.6 - up), (21.0, 37.4 - up), (24.4, 38.6 - up), (27.8, 37.4 - up), (29.0, 34.6 - up)], BOLSILLO, ancho=0.9)
    M.curva([(19.6, 34.6 - up), (29.0, 34.6 - up)], BOLSILLO, ancho=0.9, suave=False)
    # brazo derecho bajado delante, con mano blanca
    M.capsula(32.5, 31.5 - up, 35.5, 36 - up, 2.1, AZUL_B)
    M.elipse(36.0, 37.0 - up, 2.6, 2.5, BLANCO_B)
    # pies blancos
    M.elipse(17.0, 39.6, 5.0, 2.4, BLANCO_B)
    M.elipse(30.5, 39.8, 5.2, 2.4, BLANCO_B)

    # cabeza
    M.elipse(23.5, hy, 16.5, 14.6, AZUL)
    # cara blanca (más ancha abajo, corrida a la derecha por el 3/4)
    M.blob([(12, hy + 1), (14.5, hy - 5), (19.5, hy - 7.2), (24.5, hy - 7.6), (30, hy - 7.0), (34.5, hy - 4.6),
            (37.4, hy + 1.5), (36, hy + 8), (30.5, hy + 12.4), (24.5, hy + 13.4), (18, hy + 12.4), (13, hy + 8)], BLANCO)
    # collar rojo y cascabel
    M.curva([(14.0, hy + 12.6), (24.0, hy + 14.6), (34.0, hy + 12.4)], ROJO_C, ancho=2.6)
    cx = 25.0 + f * 0.6
    M.elipse(cx, hy + 16.8, 2.9, 2.7, CASC)
    M.curva([(cx - 2.2, hy + 16.4), (cx + 2.2, hy + 16.4)], CASC_L, ancho=0.6, suave=False)
    M.elipse(cx, hy + 18.0, 0.5, 0.6, CASC_L)
    # ojos: óvalos blancos altos con borde negro, pupilas mirando al centro
    for ex in (20.2, 28.0):
        M.elipse(ex, hy - 6.3, 3.95, 5.0, NEGRO)
    for ex, px in ((20.2, 21.0), (28.0, 27.3)):
        M.elipse(ex, hy - 6.3, 3.0, 4.05, OJO_B)
        M.elipse(px, hy - 5.2, 1.15, 1.7, NEGRO)
        M.punto(px - 0.3, hy - 6.0, NBRILLO, r=0.45)
    # nariz roja con brillo
    M.elipse(24.2, hy + 0.1, 2.4, 2.1, ROJO)
    M.punto(23.3, hy - 0.8, NBRILLO, r=0.55)
    # línea bajo la nariz y boca sonriente abierta
    M.curva([(24.2, hy + 2.0), (24.2, hy + 4.0)], NEGRO, ancho=0.8, suave=False)
    M.blob([(16.8, hy + 3.6), (24.2, hy + 4.4), (31.4, hy + 3.4), (29.4, hy + 8.0), (24.2, hy + 10.0), (19.0, hy + 8.2)], BOCA)
    M.elipse(24.6, hy + 8.2, 3.0, 1.4, LENGUA)
    # bigotes (3 por lado)
    for dy, a in ((-0.8, -1.4), (1.4, 0.0), (3.6, 1.4)):
        M.curva([(13.0, hy + dy + a), (18.6, hy + dy)], BIGOTE, ancho=0.8, suave=False)
        M.curva([(29.8, hy + dy), (35.8, hy + dy + a)], BIGOTE, ancho=0.8, suave=False)
    # brazo izquierdo (de la persona) levantado, por delante (se dibuja al final)
    if f == 0:
        M.capsula(14.5, 33.0 - up, 7.0, 30.5 - up, 2.1, AZUL_B)
        M.elipse(5.2, 29.6 - up, 2.7, 2.6, BLANCO_B)
    else:
        M.capsula(14.5, 33.0 - up, 6.4, 27.0 - up, 2.1, AZUL_B)
        M.elipse(4.6, 25.4 - up, 2.7, 2.6, BLANCO_B)
