# Hello Kitty (interpretacion, camino C). Lienzo 46x42. f=0 de pie; f=1 saluda, cabeza 1 px arriba, lazo se mece.
BLANCO = '#fbfbff'    # cabeza
BLANCO_B = '#fbfbfe'  # brazos y pies (casi igual: interior)
ROJO = '#e8203a'      # lazo
ROJO_N = '#e8203b'    # nudo del lazo
BRILLO_L = '#ffc2cc'  # brillo del lazo
OJO = '#1b1426'
BRILLO = '#dfe8ff'
NARIZ = '#f6c21c'
MEJ = '#f9a8c0'
CAMISA = '#f6d23a'
AZUL = '#3a78d8'
BOTON = '#ffe58a'


def dibujar(M, f=0):
    dy = -1 if f else 0
    # ---- cuerpo: camiseta, overol, pies
    M.elipse(22.5, 29.0, 7.6, 4.0, CAMISA)
    M.blob([(14.5, 31.0), (22.5, 30.0), (30.5, 31.0), (31.2, 37.6), (26.5, 38.8), (22.5, 37.4), (18.5, 38.8), (13.8, 37.6)], AZUL)
    M.rect(17.4, 26.6, 27.6, 32.0, AZUL, radio=1.0)
    M.curva([(18.2, 27.2), (16.6, 25.4)], AZUL, ancho=1.6)
    M.curva([(26.8, 27.2), (28.4, 25.4)], AZUL, ancho=1.6)
    M.elipse(18.5, 28.5, 0.6, 0.6, BOTON)
    M.elipse(26.5, 28.5, 0.6, 0.6, BOTON)
    M.elipse(17.6, 39.7, 4.4, 2.25, BLANCO_B, rot=-4)
    M.elipse(27.6, 39.7, 4.4, 2.25, BLANCO_B, rot=4)
    # brazo derecho (del espectador), abajo
    M.curva([(30.5, 29.2), (32.6, 31.6), (33.4, 33.0)], BLANCO_B, ancho=3.3)
    M.elipse(33.5, 33.4, 1.9, 1.8, BLANCO_B)
    M.elipse(30.4, 28.8, 2.5, 2.3, CAMISA)
    # brazo izquierdo: abajo (f0) o saludando (f1)
    if f:
        M.curva([(14.0, 29.0), (10.6, 28.4), (8.4, 26.4)], BLANCO_B, ancho=3.2)
        M.elipse(7.4, 25.0, 2.5, 2.6, BLANCO_B, rot=-25)
    else:
        M.curva([(14.5, 29.2), (12.4, 31.6), (11.6, 33.0)], BLANCO_B, ancho=3.3)
        M.elipse(11.5, 33.4, 1.9, 1.8, BLANCO_B)
    M.elipse(14.6, 28.8, 2.5, 2.3, CAMISA)
    # ---- cabeza
    M.blob([(6.0, 11.5 + dy), (6.4, 2.2 + dy), (8.4, 1.2 + dy), (16.0, 5.0 + dy)], BLANCO)          # oreja izq.
    M.blob([(29.0, 5.0 + dy), (36.6, 1.2 + dy), (38.6, 2.2 + dy), (39.0, 11.5 + dy)], BLANCO)       # oreja der.
    M.elipse(22.5, 14.2 + dy, 18.0, 11.2, BLANCO)
    for cx in (14.5, 26.5):                                       # ojos ovalados con brillo
        M.elipse(cx, 15.0 + dy, 1.5, 2.2, OJO)
        M.rect(cx - 1.5, 14.0 + dy, cx - 0.5, 15.0 + dy, BRILLO)
    M.rect(19.0, 18.0 + dy, 22.0, 20.0 + dy, NARIZ, radio=0.4)
    M.elipse(10.0, 19.5 + dy, 2.0, 0.6, MEJ)
    M.elipse(31.0, 19.5 + dy, 2.0, 0.6, MEJ)
    # ---- lazo (sobre la oreja derecha)
    r = 7 if f else 0
    up = -0.7 if f else 0
    M.elipse(30.2, 4.8 + dy, 4.4, 3.6, ROJO, rot=-25 + r)
    M.elipse(38.8, 4.4 + dy + up, 4.4, 3.6, ROJO, rot=22 + r)
    M.elipse(34.4, 5.6 + dy, 2.3, 2.3, ROJO_N)
    M.elipse(28.5, 3.5 + dy, 0.9, 0.6, BRILLO_L)
    M.elipse(37.5, 3.5 + dy + round(up), 0.9, 0.6, BRILLO_L)
