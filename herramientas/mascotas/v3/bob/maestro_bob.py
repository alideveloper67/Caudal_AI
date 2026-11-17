# Maestro de Bob Esponja (frente, saludando con el brazo derecho). Lienzo 46x42 (el contorno suma 1 px por lado).
# pose(M, f): f=0 brazo arriba con la mano hacia afuera; f=1 la mano se inclina hacia adentro y el cuerpo baja 1 px.
AMA = '#fde24a'       # esponja
AMA_B = '#fde24b'     # brazos y piernas (interior: se separan del cuerpo con línea fina)
AMA_N = '#fde24c'     # nariz
PORO = '#c9b82e'
BLANCO = '#ffffff'    # camisa y medias
CAFE = '#9a5c26'      # short
CINTO = '#1e1614'
ROJO = '#e0303c'      # corbata
ESCLERA = '#fffffe'
IRIS = '#3d9be0'
PUPILA = '#14141e'
BRILLO = '#fffffd'
BOCA = '#7c1a24'
DIENTE = '#fffffc'
LENGUA = '#f26a78'
MEJILLA = '#f6907a'
ZAPATO = '#26222c'
CUELLO = '#fffffa'    # cuello (interior: línea fina sobre la camisa)


def pose(M, f=0):
    b = 1 if f else 0  # el cuerpo baja 1 px en el cuadro 1 (respira), los pies quedan
    # brazo izquierdo (abajo, detrás)
    M.curva([(9.5, 25 + b), (6.4, 28.5 + b), (5.6, 31.5)], AMA_B, ancho=2.2)
    M.elipse(5.6, 32.6, 2.2, 2.0, AMA_B)
    # brazo derecho saludando
    if f == 0:
        M.curva([(36.0, 24.5 + b), (39.8, 20.5), (41.0, 15.0)], AMA_B, ancho=2.0)
        M.elipse(41.3, 12.0, 2.5, 2.7, AMA_B, rot=8)
    else:
        M.curva([(36.0, 24.5 + b), (40.0, 21.0), (41.2, 16.0)], AMA_B, ancho=2.0)
        M.elipse(41.3, 13.0, 2.5, 2.7, AMA_B, rot=-16)
    # piernas
    for x in (15.5, 30.5):
        M.capsula(x, 31 + b, x, 37.5, 1.05, AMA_B)
        M.rect(x - 1.3, 36.2, x + 1.3, 39, BLANCO)                     # media
        M.rect(x - 1.3, 37.0, x + 1.3, 37.9, ROJO)
    for x in (15.5, 30.5):
        M.elipse(x - 0.6, 39.9, 4.0, 2.0, ZAPATO)
    # esponja (rectángulo blando con bordes ondulados)
    M.blob([(10, 1.2 + b), (23, 0.6 + b), (36, 1.2 + b), (37.6, 4 + b), (37.0, 16 + b), (36.4, 28.5 + b), (23, 29 + b), (9.6, 28.5 + b), (9.0, 16 + b), (8.4, 4 + b)], AMA, suavidad=12)
    for (x, y) in ((15, 1.0), (30, 1.0), (8.7, 10), (9.2, 21), (37.5, 8), (36.9, 19)):
        M.elipse(x, y + b, 1.6, 1.4, AMA)
    # poros
    for (x, y, rx, ry) in ((11.6, 4.6, 1.5, 1.2), (34.4, 4.2, 1.2, 1.1), (34.8, 12.8, 1.4, 1.3), (11.4, 21.2, 1.3, 1.1), (33.4, 21.4, 1.1, 1.0)):
        M.elipse(x, y + b, rx, ry, PORO)
    # camisa y short
    M.rect(9.2, 22.8 + b, 36.8, 27 + b, BLANCO)
    M.rect(9.2, 26.8 + b, 36.8, 31.6 + b, CAFE, radio=1.0)
    M.rect(9.4, 27.2 + b, 36.6, 28.2 + b, CINTO)
    for x in (12, 17, 28, 33):
        M.rect(x, 27.2 + b, x + 2, 28.2 + b, BLANCO)
    M.elipse(15.5, 31.4 + b, 2.8, 1.4, CAFE)                           # bastas del short
    M.elipse(30.5, 31.4 + b, 2.8, 1.4, CAFE)
    # cuello de la camisa y corbata
    M.poligono([(17.6, 22.2 + b), (22.6, 25.6 + b), (23.4, 25.6 + b), (28.4, 22.2 + b), (23, 23.0 + b)], CUELLO)
    M.elipse(23, 24.6 + b, 1.6, 1.2, ROJO)
    M.poligono([(21.6, 25.2 + b), (24.4, 25.2 + b), (25.3, 29.4 + b), (23, 31.0 + b), (20.7, 29.4 + b)], ROJO)
    # ojos grandes
    for cx in (17.0, 27.4):
        M.elipse(cx, 10.8 + b, 4.7, 5.0, ESCLERA)
        M.elipse(cx + 0.5, 11.2 + b, 2.9, 3.1, IRIS)
        M.elipse(cx + 0.6, 11.4 + b, 1.5, 1.6, PUPILA)
        M.elipse(cx - 0.5, 10.0 + b, 0.75, 0.85, BRILLO)
        for (dx, ang) in ((-2.6, -1.4), (0, 0), (2.6, 1.4)):            # pestañas
            M.curva([(cx + dx * 0.95, 6.2 + b), (cx + dx + ang, 4.4 + b)], PUPILA, ancho=0.95)
    # nariz
    M.elipse(23.2, 15.6 + b, 1.9, 1.5, AMA_N, rot=-20)
    # mejillas
    M.elipse(12.6, 16.8 + b, 2.2, 1.3, MEJILLA)
    M.elipse(33.4, 16.8 + b, 2.2, 1.3, MEJILLA)
    # sonrisa grande con dientes de conejo y lengua
    M.blob([(14.5, 17.2 + b), (22.5, 18.4 + b), (30.6, 17.0 + b), (28.2, 20.0 + b), (22.5, 21.6 + b), (17.0, 20.2 + b)], BOCA)
    M.elipse(22.5, 20.6 + b, 2.6, 0.9, LENGUA)
    M.rect(19.9, 18.0 + b, 22.2, 20.2 + b, DIENTE)
    M.rect(22.8, 18.0 + b, 25.1, 20.2 + b, DIENTE)


def dibujar(M):
    pose(M, 0)
