# Pusheen (interpretacion, camino C). Lienzo 46x42. Gatita gordita en 3/4 (cara a la izquierda).
# f=0 ojos abiertos; f=1 ojos felices «^ ^», cuerpo 1 px arriba y la cola se mece.
GRIS = '#a7a3b4'      # cuerpo
GRIS_B = '#a7a3b5'    # cola y patitas (interior)
RAYA = '#6f6a80'
PANZA = '#f4ead8'
OREJA_IN = '#f2b2c4'
OJO = '#1b1426'
BRILLO = '#e6f0ff'
MEJ = '#f59ab8'
BOCA = '#3a2a3e'


def dibujar(M, f=0):
    dy = -1 if f else 0
    # ---- cola rayada (detras, a la derecha)
    if f:
        cola = [(36.0, 31.0), (41.0, 27.0), (42.6, 20.0), (40.6, 15.4)]
    else:
        cola = [(36.0, 31.0), (41.6, 28.4), (44.0, 22.0), (43.6, 17.0)]
    M.curva(cola, GRIS_B, ancho=4.0)
    rayas = [((40.4, 23.6), (43.8, 24.2)), ((40.2, 18.4), (43.4, 17.6))] if f else [((41.6, 24.4), (45.0, 25.4)), ((42.2, 19.6), (45.6, 20.2))]
    for a, b in rayas:
        M.curva([a, b], RAYA, ancho=1.2, suave=False)
    # ---- patitas
    for cx in (11.0, 18.8, 30.4, 36.0):
        M.elipse(cx, 40.2, 2.6, 1.7, GRIS_B)
    # ---- orejas y cuerpo
    M.blob([(6.6, 13 + dy), (8.0, 3.0 + dy), (10.0, 2.6 + dy), (16.0, 9.0 + dy)], GRIS)
    M.blob([(19.0, 9.0 + dy), (24.0, 2.8 + dy), (26.0, 3.4 + dy), (27.6, 12 + dy)], GRIS)
    M.blob([(3.6, 25), (5.6, 14.6 + dy), (12.6, 8.6 + dy), (22.0, 7.8 + dy), (31.0, 10.0 + dy), (38.0, 15.0 + dy),
            (40.8, 24.0), (39.6, 33.4), (35.0, 38.6), (22.0, 39.6), (9.0, 38.6), (4.4, 33.4)], GRIS)
    M.blob([(8.6, 7.8 + dy), (9.6, 4.8 + dy), (12.8, 8.6 + dy)], OREJA_IN)
    M.blob([(21.2, 8.6 + dy), (24.0, 4.8 + dy), (25.2, 8.6 + dy)], OREJA_IN)
    # panza crema
    M.elipse(17.4, 34.4, 8.2, 4.2, PANZA)
    # ---- rayas: frente y lomo
    for x in (14.0, 17.0, 20.0):
        M.rect(x, 9.0 + dy, x + 1.0, 12.0 + dy, RAYA)
    for x0, y0, x1, y1 in ((30.6, 11.4, 29.4, 18.0), (34.4, 13.4, 33.4, 20.0), (37.6, 16.4, 37.0, 21.6)):
        M.curva([(x0, y0 + dy), (x1, y1 + dy)], RAYA, ancho=1.3, suave=False)
    # ---- cara
    if f:
        for cx in (11.5, 21.5):
            M.curva([(cx - 1.5, 20.0 + dy), (cx, 18.6 + dy), (cx + 1.5, 20.0 + dy)], OJO, ancho=1.0)
    else:
        for cx in (11.5, 21.5):
            M.elipse(cx, 19.0 + dy, 1.5, 1.9, OJO)
            M.rect(cx - 0.5, 18.0 + dy, cx + 0.5, 19.0 + dy, BRILLO)
    M.elipse(8.6, 22.5 + dy, 1.7, 0.6, MEJ)
    M.elipse(24.6, 22.5 + dy, 1.7, 0.6, MEJ)
    # boca «:3»
    M.rect(15.0, 21.0 + dy, 16.0, 22.0 + dy, BOCA)
    M.rect(16.0, 22.0 + dy, 17.0, 23.0 + dy, BOCA)
    M.rect(17.0, 21.0 + dy, 18.0, 22.0 + dy, BOCA)
    M.rect(18.0, 22.0 + dy, 19.0, 23.0 + dy, BOCA)
