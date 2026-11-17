# Maestro del Minion (frente, dos ojos con gafas, saludando con el brazo derecho). Lienzo 46x42.
# pose(M, f): f=0 mano arriba; f=1 la mano baja un poco y el cuerpo respira (baja 1 px).
AMA = '#fcd93a'
AMA_B = '#fcd93b'     # brazos (interior)
AZUL = '#2f6fb8'      # overol
BOLSILLO = '#4a88d0'  # bolsillo (más claro, fijo)
PELO = '#1c1a20'
CORREA = '#2a2a32'
ARO = '#aeb6c2'       # aro metálico de las gafas
ESCLERA = '#fffffe'
IRIS = '#8a5428'
PUPILA = '#14101a'
BRILLO = '#fffffd'
REFLEJO = '#d4ecff'
BOCA = '#5a1e18'
DIENTE = '#fffffc'
LENGUA = '#ee6a6a'
NEGRO = '#26242c'     # guantes y zapatos
LOGO = '#14141a'


def pose(M, f=0):
    b = 1 if f else 0
    # brazo izquierdo (abajo)
    M.curva([(11.0, 25.0 + b), (7.6, 28.6 + b), (6.8, 31.6)], AMA_B, ancho=2.2)
    M.elipse(6.6, 33.0, 2.3, 2.2, NEGRO)
    # brazo derecho saludando
    if f == 0:
        M.curva([(35.0, 25.0 + b), (39.2, 20.5), (40.4, 15.5)], AMA_B, ancho=2.2)
        M.elipse(40.6, 12.6, 2.5, 2.7, NEGRO, rot=10)
    else:
        M.curva([(35.0, 25.0 + b), (39.4, 21.5), (40.6, 17.0)], AMA_B, ancho=2.2)
        M.elipse(40.6, 14.2, 2.5, 2.7, NEGRO, rot=-14)
    # piernas y zapatos
    M.rect(15.2, 34.5, 20.2, 39.0, AZUL)
    M.rect(25.8, 34.5, 30.8, 39.0, AZUL)
    M.elipse(16.8, 40.0, 3.9, 1.9, NEGRO)
    M.elipse(29.4, 40.0, 3.9, 1.9, NEGRO)
    # cuerpo cápsula
    M.elipse(23, 13.5 + b, 13.0, 12.5, AMA)
    M.rect(10, 13.5 + b, 36, 31 + b, AMA)
    M.elipse(23, 31 + b, 13.0, 5.4, AMA)
    # overol: pantalón, peto, tirantes, bolsillo y logo
    M.rect(10, 27.6 + b, 36, 31 + b, AZUL)
    M.elipse(23, 31 + b, 13.0, 5.4, AZUL)
    M.rect(15.6, 23.0 + b, 30.4, 29.0 + b, AZUL, radio=0.8)
    M.curva([(16.4, 23.8 + b), (13.4, 21.4 + b), (10.4, 20.4 + b)], AZUL, ancho=1.9)
    M.curva([(29.6, 23.8 + b), (32.6, 21.4 + b), (35.6, 20.4 + b)], AZUL, ancho=1.9)
    M.rect(19.6, 24.4 + b, 26.4, 28.2 + b, BOLSILLO, radio=0.6)
    M.elipse(23, 26.4 + b, 1.15, 1.15, LOGO)
    M.punto(16.5, 24.2 + b, LOGO, r=0.55)                              # botones
    M.punto(29.5, 24.2 + b, LOGO, r=0.55)
    # pelos
    for pts in (((20.6, 2.6), (19.4, 0.8), (18.2, 0.3)), ((23, 2.2), (23.2, 0.2)), ((25.4, 2.6), (26.8, 0.6), (28.0, 0.4))):
        M.curva([(x, y + b) for x, y in pts], PELO, ancho=0.9)
    # correa y gafas
    M.rect(10, 11.0 + b, 36, 13.6 + b, CORREA)
    for cx in (18.1, 27.9):
        M.elipse(cx, 12.3 + b, 5.2, 5.2, ARO)
        M.elipse(cx, 12.3 + b, 3.3, 3.3, ESCLERA)
        M.elipse(cx + 0.6, 12.9 + b, 1.85, 1.95, IRIS)
        M.elipse(cx + 0.6, 13.0 + b, 0.95, 1.0, PUPILA)
        M.elipse(cx - 0.6, 11.7 + b, 0.6, 0.65, BRILLO)
        M.curva([(cx - 2.4, 11.4 + b), (cx - 1.4, 9.8 + b)], REFLEJO, ancho=0.8)
    # sonrisa con dientes y lengua
    M.blob([(18.8, 20.0 + b), (23, 20.8 + b), (27.2, 20.0 + b), (25.9, 22.9 + b), (23, 23.8 + b), (20.1, 22.9 + b)], BOCA)
    M.rect(20.4, 20.3 + b, 25.6, 21.3 + b, DIENTE)
    M.elipse(23, 23.0 + b, 1.6, 0.7, LENGUA)


def dibujar(M):
    pose(M, 0)
