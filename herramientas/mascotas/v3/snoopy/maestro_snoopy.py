# Maestro de Snoopy (3/4 mirando a la derecha, bailando feliz con un brazo adelante). Lienzo 46x42.
# pose(M, f): f=0 oreja pegada y cola arriba; f=1 la oreja se abre al aire, la cola baja y el cuerpo respira.
BLANCO = '#ffffff'
BLANCO_B = '#fefeff'  # brazos, pies y cola (interior)
NEGRO = '#22202a'     # oreja
NARIZ = '#16141c'
OJO = '#14121a'
BRILLO = '#fffffd'
ROJO = '#e0302e'      # collar
CHAPA = '#f2c230'
MEJILLA = '#f6a0b0'
BOCA = '#2a1c24'


def pose(M, f=0):
    b = 1 if f else 0
    # cola y brazo de atrás
    if f == 0:
        M.curva([(13.4, 32.4), (10.2, 31.0), (8.8, 28.0)], BLANCO_B, ancho=2.2)
    else:
        M.curva([(13.4, 32.4), (10.0, 32.0), (8.8, 30.2)], BLANCO_B, ancho=2.2)
    # pies largos
    M.elipse(16.4, 39.6, 4.4, 2.2, BLANCO_B, rot=-4)
    M.elipse(27.2, 39.6, 4.8, 2.2, BLANCO_B, rot=4)
    # cuerpo de pera
    M.blob([(15.0, 21.5 + b), (25.0, 21.5 + b), (28.8, 27.5), (28.6, 33.8), (24.6, 37.6), (16.4, 37.6), (12.4, 33.6), (12.4, 26.8)], BLANCO)
    # cabeza con hocico largo
    M.blob([(12.0, 3.6 + b), (19.6, 0.8 + b), (27.0, 3.0 + b), (33.0, 6.6 + b), (39.0, 8.4 + b), (41.6, 11.8 + b), (40.6, 15.8 + b),
            (35.8, 18.4 + b), (28.0, 19.8 + b), (20.0, 20.4 + b), (13.0, 18.2 + b), (9.6, 12.0 + b)], BLANCO, suavidad=12)
    # nariz grande con brillo
    M.elipse(40.8, 10.8 + b, 2.7, 2.2, NARIZ)
    M.punto(39.9, 10.0 + b, BRILLO, r=0.55)
    # oreja negra colgando (se mueve)
    if f == 0:
        M.blob([(13.6, 4.2 + b), (18.4, 4.6 + b), (19.4, 10.0 + b), (17.6, 16.6 + b), (14.0, 20.2 + b), (11.2, 18.0 + b), (11.4, 10.0 + b)], NEGRO)
    else:
        M.blob([(13.6, 4.2 + b), (18.4, 4.6 + b), (18.6, 10.0 + b), (15.6, 15.6 + b), (10.6, 18.0 + b), (8.8, 15.6 + b), (10.8, 9.4 + b)], NEGRO)
    # ojo, ceja, mejilla, sonrisa
    M.elipse(27.4, 10.2 + b, 1.2, 2.2, OJO)
    M.punto(27.0, 9.0 + b, BRILLO, r=0.55)
    M.elipse(25.6, 14.6 + b, 1.7, 0.95, MEJILLA)
    M.curva([(27.0, 15.4 + b), (30.0, 17.0 + b), (33.4, 15.8 + b)], BOCA, ancho=0.95)
    # collar rojo con chapita
    M.curva([(13.6, 21.0 + b), (19.6, 22.4 + b), (26.0, 21.2 + b)], ROJO, ancho=2.8)
    M.punto(21.0, 24.0 + b, CHAPA, r=0.8)
    # brazo de adelante (levantado, feliz)
    M.curva([(24.6, 25.0 + b), (29.0, 24.6 + b), (32.6, 22.8 + b)], BLANCO_B, ancho=2.0)
    M.elipse(33.8, 22.4 + b, 2.3, 2.0, BLANCO_B)


def dibujar(M):
    pose(M, 0)
