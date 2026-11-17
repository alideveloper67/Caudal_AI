# Maestro de Winnie the Pooh (casi de frente, saludando con la izquierda y abrazando su tarro de miel). Lienzo 46x42.
# pose(M, f): f=0 pata arriba; f=1 la pata baja un poco, el cuerpo respira y la gota de miel cae.
PIEL = '#f5b52e'
PIEL_B = '#f5b52f'    # brazos y pies (interior)
HOCICO = '#fbd36a'
OREJA_IN = '#d88a1a'
ROJO = '#d8232e'      # camiseta
BORDE = '#d8232f'     # borde de la camiseta (interior: línea fina)
OJO = '#16100c'
BRILLO = '#fffffd'
NARIZ = '#1c1410'
CEJA = '#8a4a16'
BOCA = '#7a3410'
MEJILLA = '#f48a72'
TARRO = '#b8692c'
TARRO_B = '#b8692d'   # borde del tarro (interior)
MIEL = '#f5a210'
ETIQUETA = '#f4e4b4'
LETRA = '#8a4a1c'


def pose(M, f=0):
    b = 1 if f else 0
    # brazo izquierdo saludando (detrás de la cabeza no: al costado)
    if f == 0:
        M.curva([(11.5, 24.0 + b), (7.0, 19.5), (5.4, 14.5)], PIEL_B, ancho=3.4)
        M.elipse(5.2, 12.6, 2.7, 2.8, PIEL_B)
    else:
        M.curva([(11.5, 24.0 + b), (6.9, 20.5), (5.3, 16.0)], PIEL_B, ancho=3.4)
        M.elipse(5.2, 14.2, 2.7, 2.8, PIEL_B)
    # pies
    M.elipse(14.6, 38.8, 4.8, 3.0, PIEL_B, rot=-6)
    M.elipse(27.0, 38.8, 4.8, 3.0, PIEL_B, rot=6)
    # barriga
    M.elipse(20.8, 30.5 + b * 0.5, 11.0, 8.6, PIEL)
    # camiseta roja corta con borde
    M.blob([(10.6, 21.6 + b), (20.8, 20.6 + b), (31.0, 21.6 + b), (32.0, 27.8 + b), (20.8, 28.8 + b), (9.6, 27.8 + b)], ROJO)
    M.blob([(9.8, 26.6 + b), (20.8, 27.6 + b), (31.8, 26.6 + b), (32.0, 28.4 + b), (20.8, 29.6 + b), (9.6, 28.4 + b)], BORDE)
    # orejas
    M.elipse(10.6, 4.0 + b, 3.4, 3.2, PIEL)
    M.elipse(30.6, 3.8 + b, 3.4, 3.2, PIEL)
    M.elipse(10.8, 4.4 + b, 1.5, 1.3, OREJA_IN)
    M.elipse(30.4, 4.2 + b, 1.5, 1.3, OREJA_IN)
    # cabeza
    M.elipse(20.6, 12.6 + b, 12.6, 10.4, PIEL)
    # hocico claro
    M.elipse(22.0, 16.4 + b, 5.6, 3.8, HOCICO)
    # ojos pequeños y brillantes, cejas
    for cx in (16.4, 25.8):
        M.elipse(cx, 11.4 + b, 1.4, 2.0, OJO)
        M.elipse(cx - 0.4, 10.6 + b, 0.6, 0.65, BRILLO)
    M.curva([(14.6, 7.8 + b), (16.6, 7.2 + b)], CEJA, ancho=0.9)
    M.curva([(25.2, 7.2 + b), (27.2, 7.8 + b)], CEJA, ancho=0.9)
    # nariz, boca, mejillas
    M.elipse(22.0, 14.4 + b, 2.0, 1.3, NARIZ)
    M.punto(21.3, 14.0 + b, BRILLO, r=0.45)
    M.curva([(19.8, 17.6 + b), (22.0, 18.8 + b), (24.2, 17.6 + b)], BOCA, ancho=0.9)
    M.elipse(12.6, 15.8 + b, 2.0, 1.2, MEJILLA)
    M.elipse(29.4, 15.8 + b, 2.0, 1.2, MEJILLA)
    # tarro de miel
    M.elipse(36.8, 33.6, 6.6, 6.6, TARRO)
    M.rect(32.0, 26.4, 41.6, 29.0, TARRO_B, radio=1.0)
    M.blob([(32.4, 26.8), (36.8, 25.2), (41.2, 26.8), (40.0, 28.0), (38.6, 30.6 + b * 1.4), (37.4, 28.2), (33.6, 28.0)], MIEL)
    M.rect(33.0, 31.4, 40.6, 35.4, ETIQUETA, radio=0.6)
    for x in (34.4, 36.4, 38.4):
        M.rect(x, 32.9, x + 1.0, 33.9, LETRA)
    # brazo derecho abrazando el tarro
    M.curva([(29.0, 23.6 + b), (31.6, 26.6), (33.0, 28.6)], PIEL_B, ancho=3.4)
    M.elipse(33.8, 29.4, 2.7, 2.3, PIEL_B)


def dibujar(M):
    pose(M, 0)
