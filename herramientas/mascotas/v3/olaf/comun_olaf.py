# Olaf (frente, saludando con la ramita izquierda del dibujo). Lienzo 46x42.
# Cuadro 0: ramita arriba.  Cuadro 1: ramita inclinada hacia afuera (vaivén), cuerpo 1 px arriba, pelitos movidos.
NIEVE = '#f6f9ff'      # cabeza
NIEVE_M = '#f6f9fe'    # bola del medio
NIEVE_B = '#f6f8ff'    # bola de abajo
NIEVE_P = '#f5f9ff'    # pies
RAMA = '#7a4a24'
OJO = '#1a1a26'
BLANCO = '#ffffff'
CEJA = '#3a2a22'
ZANAHORIA = '#ff8a1e'
BOCA = '#3c2a3a'
DIENTE = '#fffffe'
BOTON = '#2a2a34'
MEJILLA = '#ffc2cc'


def pose(M, f):
    up = 1 if f else 0
    # pelitos (ramitas en la coronilla)
    s = 0.8 if f else 0.0
    M.curva([(23, 6 - up), (22.6, 3 - up), (21.6 - s, 0.6)], RAMA, ancho=1.0)
    M.curva([(21, 6.5 - up), (19.2, 3.4 - up), (17.4 - s, 2.2 - up)], RAMA, ancho=1.0)
    M.curva([(25, 6.5 - up), (26.6, 3.6 - up), (28.6 - s, 2.6 - up)], RAMA, ancho=1.0)
    # brazos de ramita (detrás del cuerpo)
    if f == 0:
        M.curva([(17, 25 - up), (12, 21 - up), (8.5, 15.5 - up)], RAMA, ancho=1.2)
        M.curva([(9.2, 16.6 - up), (6.2, 14.6 - up)], RAMA, ancho=1.0)
        M.curva([(8.5, 15.5 - up), (8.6, 12.2 - up)], RAMA, ancho=1.0)
        M.curva([(10.2, 18.0 - up), (7.0, 18.4 - up)], RAMA, ancho=1.0)
    else:
        M.curva([(17, 25 - up), (11.5, 22 - up), (6.0, 18.5 - up)], RAMA, ancho=1.2)
        M.curva([(6.8, 19.0 - up), (3.4, 18.6 - up)], RAMA, ancho=1.0)
        M.curva([(6.0, 18.5 - up), (4.8, 15.2 - up)], RAMA, ancho=1.0)
        M.curva([(8.8, 20.2 - up), (6.6, 22.6 - up)], RAMA, ancho=1.0)
    M.curva([(29, 25.5 - up), (34.5, 27.5 - up), (39.5, 26 - up)], RAMA, ancho=1.2)
    M.curva([(37.5, 26.6 - up), (40.5, 29 - up)], RAMA, ancho=1.0)
    M.curva([(39.5, 26 - up), (42.5, 24 - up)], RAMA, ancho=1.0)
    # pies y bolas de nieve
    M.elipse(16.5, 39.3, 4.4, 2.4, NIEVE_P)
    M.elipse(29.5, 39.3, 4.4, 2.4, NIEVE_P)
    M.elipse(23, 33.6 - up * 0.5, 10.6, 6.6, NIEVE_B)
    M.elipse(23, 24.6 - up, 7.4, 5.6, NIEVE_M)
    M.elipse(23, 12.4 - up, 9.4, 7.0, NIEVE)              # cabeza: óvalo + mandíbula más ancha
    M.elipse(24, 16.4 - up, 10.0, 4.6, NIEVE)
    # botones de carbón
    M.elipse(23, 23.0 - up, 1.0, 1.0, BOTON)
    M.elipse(23, 26.5 - up, 1.0, 1.0, BOTON)
    M.elipse(23, 34.0 - up * 0.5, 1.0, 1.0, BOTON)
    # ojos con brillo y cejas
    for cx in (19.2, 26.6):
        M.elipse(cx, 11.8 - up, 1.5, 2.2, OJO)
        M.rect(cx - 1.0, 10.0 - up, cx, 11.0 - up, BLANCO)
    M.curva([(17.6, 8.6 - up), (20.6, 7.6 - up)], CEJA, ancho=1.0, suave=False)
    M.curva([(25.2, 7.6 - up), (28.2, 8.6 - up)], CEJA, ancho=1.0, suave=False)
    # mejillas
    M.elipse(16.4, 15.0 - up, 1.4, 0.8, MEJILLA)
    M.elipse(31.0, 15.0 - up, 1.4, 0.8, MEJILLA)
    # boca sonriente con un diente
    M.blob([(18.8, 16.6 - up), (23.5, 17.6 - up), (28.4, 16.4 - up), (27, 19.6 - up), (23.5, 20.6 - up), (20, 19.6 - up)], BOCA)
    M.rect(22.6, 17.0 - up, 24.6, 18.6 - up, DIENTE)
    # nariz de zanahoria (encima de todo)
    M.blob([(22.0, 13.0 - up), (24.0, 12.2 - up), (31.5, 14.6 - up), (24.0, 15.0 - up)], ZANAHORIA)
