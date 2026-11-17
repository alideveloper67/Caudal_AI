# Maestro de Chimuelo / Toothless (sentado, 3/4 hacia la derecha). Lienzo 46x42.
# Negro con luz azul-violeta para que se lea en fondo oscuro. f = cuadro: 0 quieto; 1 alas entreabiertas,
# aletas de la cabeza arriba, cola levantada y cuerpo 1 px arriba.
NEGRO = '#3a3e5e'     # cuerpo y cabeza (negro azulado; la sombra lo baja)
NEGRO_B = '#3a3e5f'   # patas delanteras (línea interior)
ALA = '#353a66'       # alas plegadas (más violeta, detrás)
ALA_N = '#5a62a0'     # hueso del ala (fijo)
ALETA = '#3a3d5e'     # aletas de la cabeza (línea interior)
COLA = '#3a3f5e'
ROJO = '#d8402e'      # aleta roja de la cola
OJO = '#8ee05a'       # verde
OJO_O = '#4f9e2c'     # verde oscuro (borde de abajo del iris)
PUPILA = '#0c0e14'
BRILLO = '#ffffff'
BOCA = '#6a2a4a'
LENGUA = '#e8788c'
NARIZ = '#14152a'


def pose(M, f):
    up = 1 if f else 0
    # cola: sale por detrás a la derecha y se enrosca hacia delante; aleta roja en la punta
    lift = 2.5 if f else 0
    M.curva([(30, 36 - up), (37, 38.5), (41.5, 36.0 - lift * 0.5), (43.0, 31.5 - lift)], COLA, ancho=3.0)
    M.blob([(42.4, 32.6 - lift), (45.8, 28.4 - lift), (45.8, 34.2 - lift), (43.4, 35.0 - lift)], ROJO)
    M.blob([(42.0, 31.6 - lift), (39.6, 26.4 - lift), (44.4, 29.2 - lift)], ROJO)
    # alas plegadas a los lados del cuerpo (más abiertas en el cuadro 1)
    t = 0 if f == 0 else 1
    for sx in (1, -0.8):                   # ala derecha (sx=1) e izquierda (sx=-0.8: la lejana, más chica por el 3/4)
        X = lambda x: 23.5 + sx * (x - 23.5)
        pts = [(29, 24.5), (34.5, 17.5 - 4 * t), (38.5, 15.0 - 5 * t), (44.0, 20.5 - 3 * t), (42.0, 25.0 - t),
               (39.6, 24.6 - t), (39.6, 28.8 - t * 0.5), (37.0, 28.2), (35.8, 31.6), (31, 32.5)]
        M.blob([(X(x), y) for x, y in pts], ALA)
        M.curva([(X(31.0), 26.0), (X(38.0), 16.8 - 4.6 * t)], ALA_N, ancho=0.9, suave=False)
    # cuerpo sentado
    M.elipse(23.5, 32.0 - up, 10.2, 8.6, NEGRO)
    # patas delanteras y traseras
    M.elipse(17.5, 39.0, 3.6, 2.6, NEGRO_B)
    M.elipse(28.5, 39.2, 3.6, 2.6, NEGRO_B)
    M.elipse(11.6, 38.8, 3.4, 2.4, NEGRO_B)
    M.elipse(35.0, 38.8, 3.4, 2.4, NEGRO_B)
    # aletas grandes de la cabeza (orejas-aleta)
    hy = 15.5 - up
    t = 2.2 if f else 0
    M.blob([(12.5, hy - 6.5), (5.5, hy - 12.0 - t), (2.6, hy - 13.2 - t), (4.0, hy - 9.0 - t * 0.5), (9.5, hy - 2.5)], ALETA)
    M.blob([(33.5, hy - 6.5), (40.5, hy - 12.0 - t), (43.6, hy - 13.2 - t), (42.0, hy - 9.0 - t * 0.5), (36.5, hy - 2.5)], ALETA)
    # aletas chicas
    M.blob([(15.5, hy - 8.5), (12.6, hy - 13.0 - t * 0.5), (18.0, hy - 9.6)], ALETA)
    M.blob([(30.5, hy - 8.5), (33.6, hy - 13.0 - t * 0.5), (28.4, hy - 9.6)], ALETA)
    # cabeza ancha y redonda (hocico hacia delante-derecha)
    M.blob([(8.5, hy), (11, hy - 7), (18, hy - 10), (28, hy - 10), (35, hy - 7), (38, hy - 0.5), (37, hy + 5.5),
            (31, hy + 9.5), (23, hy + 10.6), (15, hy + 9.5), (9.5, hy + 5.5)], NEGRO)
    # ojos verdes enormes con pupila fina
    for cx in (16.6, 30.0):
        M.elipse(cx, hy + 0.6, 3.9, 4.2, OJO_O)
        M.elipse(cx - 0.1, hy + 0.1, 3.6, 3.6, OJO)
        M.elipse(cx + 0.5, hy + 0.7, 0.75, 2.9, PUPILA)
        M.elipse(cx - 1.6, hy - 1.4, 0.75, 0.8, BRILLO)
    # fosas nasales y sonrisa sin dientes con lengua
    M.punto(21.6, hy + 5.6, NARIZ, r=0.5)
    M.punto(26.0, hy + 5.6, NARIZ, r=0.5)
    M.blob([(19.0, hy + 7.0), (23.8, hy + 7.6), (28.6, hy + 6.8), (26.5, hy + 9.0), (23.8, hy + 9.6), (21.0, hy + 9.0)], BOCA)
    M.elipse(24.2, hy + 8.9, 1.8, 0.7, LENGUA)
