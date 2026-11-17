# Maestro de Patricio Estrella (frente, saludando con el brazo izquierdo en alto). Lienzo 46x42.
# pose(M, f): f=0 brazo arriba abierto; f=1 brazo un poco más alto y hacia adentro, el cuerpo «respira» (baja 1 px).
ROSA = '#f7a3b8'      # cuerpo
ROSA_B = '#f7a3b9'    # brazos y piernas (interior)
VERDE = '#9ccc3c'     # short
FLOR = '#8a4cc8'
FLOR_C = '#f6e05a'
ESCLERA = '#fffffe'
PUPILA = '#14101c'
BRILLO = '#fffffd'
CEJA = '#1c1420'
BOCA = '#8a1a30'
LENGUA = '#f2627e'
MEJILLA = '#ec6c8e'
OMBLIGO = '#c8587a'


def pose(M, f=0):
    b = 1 if f else 0
    # piernas (detrás del short)
    M.blob([(14.5, 31), (20.5, 31.5), (20.0, 37), (18.4, 41.8), (15.0, 41.8), (13.6, 37)], ROSA_B)
    M.blob([(25.5, 31.5), (31.5, 31), (32.4, 37), (31.0, 41.8), (27.6, 41.8), (26.0, 37)], ROSA_B)
    # cuerpo-estrella (la punta es la cabeza)
    M.blob([(23, 1.2 + b), (26.6, 5.5 + b), (29.6, 12 + b), (32.2, 19.5 + b), (34.0, 26.5 + b), (33.0, 31.5 + b),
            (23, 32.6 + b), (13.0, 31.5 + b), (12.0, 26.5 + b), (13.8, 19.5 + b), (16.4, 12 + b), (19.4, 5.5 + b)], ROSA, suavidad=12)
    # brazo derecho (abajo, apoyado)
    M.blob([(30.6, 18.5 + b), (36.5, 21.5 + b), (41.0, 25.6 + b), (40.0, 28.0 + b), (35.0, 27.0 + b), (30.8, 25.0 + b)], ROSA_B)
    # brazo izquierdo saludando
    if f == 0:
        M.blob([(17.2, 16.0 + b), (11.5, 11.0), (6.8, 6.4), (4.8, 8.4), (8.0, 14.0), (14.8, 22.0 + b)], ROSA_B)
    else:
        M.blob([(17.2, 16.0 + b), (12.0, 10.4), (8.4, 4.6), (4.9, 6.4), (8.0, 13.2), (14.8, 22.0 + b)], ROSA_B)
    # short verde con flores
    M.blob([(12.4, 25.6 + b), (23, 26.2 + b), (33.6, 25.6 + b), (34.4, 31.0 + b), (31.5, 33.4), (25.4, 33.4), (23, 31.6 + b),
            (20.6, 33.4), (14.5, 33.4), (11.6, 31.0 + b)], VERDE)
    for (x, y) in ((16.0, 28.4), (24.4, 29.0), (30.6, 28.0), (19.6, 32.0)):
        M.elipse(x, y + b, 1.65, 0.75, FLOR)
        M.elipse(x, y + b, 0.75, 1.65, FLOR)
        M.elipse(x, y + b, 0.62, 0.62, FLOR_C)
    # ombligo
    M.curva([(22.4, 23.2 + b), (23.4, 23.6 + b)], OMBLIGO, ancho=0.9)
    # ojos juntos y altos, cejas gruesas
    for cx in (20.3, 25.9):
        M.elipse(cx, 12.2 + b, 2.6, 3.5, ESCLERA)
        M.elipse(cx + 0.5, 13.0 + b, 1.65, 1.95, PUPILA)
        M.elipse(cx - 0.1, 12.0 + b, 0.6, 0.65, BRILLO)
    M.curva([(17.6, 8.2 + b), (19.4, 7.0 + b), (21.6, 7.6 + b)], CEJA, ancho=1.0)
    M.curva([(24.6, 7.6 + b), (26.8, 7.0 + b), (28.6, 8.2 + b)], CEJA, ancho=1.0)
    # mejillas
    M.elipse(16.4, 17.0 + b, 1.9, 1.1, MEJILLA)
    M.elipse(29.8, 17.0 + b, 1.9, 1.1, MEJILLA)
    # boca abierta sonriente con lengua
    M.blob([(18.6, 16.6 + b), (23, 17.4 + b), (27.6, 16.6 + b), (26.2, 19.6 + b), (23, 20.6 + b), (20.0, 19.6 + b)], BOCA)
    M.elipse(23.2, 19.6 + b, 2.0, 0.9, LENGUA)


def dibujar(M):
    pose(M, 0)
