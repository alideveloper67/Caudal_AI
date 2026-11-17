# Pompompurin (frente, sentadito, saludando). Lienzo 46x42.
# Cuadro 0: patita a un lado.  Cuadro 1: patita arriba saludando, orejas que se balancean, cuerpo 1 px arriba.
CREMA = '#ffe28a'      # cabeza
CREMA_C = '#ffe28b'    # cuerpo
CREMA_B = '#ffe189'    # brazos y pies (delante)
LUZ = '#fff3c4'
BOINA = '#8a5428'
OREJA = '#b87a40'
OJO = '#2a1a14'
BLANCO = '#ffffff'
HOCICO = '#5a3418'
BOCA = '#6a3a20'
MEJILLA = '#ffb59a'
SUELA = '#f2b860'
COLA = '#ffe18a'


def pose(M, f):
    up = 1 if f else 0
    # colita (detrás, asoma abajo a la derecha)
    M.elipse(36.8, 36.0 - up * 0.5, 2.6, 2.2, COLA)
    # cuerpo redondo
    M.elipse(23, 31 - up * 0.5, 12.0, 9.2, CREMA_C)
    # pies con almohadilla
    M.elipse(16, 38.8, 4.6, 2.9, CREMA_B)
    M.elipse(30, 38.8, 4.6, 2.9, CREMA_B)
    # cabeza grande
    M.elipse(23, 16.5 - up, 15.4, 11.6, CREMA)
    M.elipse(15.0, 10.0 - up, 3.6, 2.0, LUZ, rot=-30)
    # orejas largas caídas
    ro = 6 if f else 0
    M.elipse(9.6, 18.5 - up, 3.4, 7.2, OREJA, rot=12 + ro)
    M.elipse(36.4, 18.5 - up, 3.4, 7.2, OREJA, rot=-12 - ro)
    # brazos (delante): el izquierdo del dibujo saluda a la altura del cachete en el cuadro 1
    M.elipse(33.8, 29.6 - up, 3.0, 2.7, CREMA_B, rot=-20)
    if f == 0:
        M.elipse(12.2, 30.0, 3.0, 2.7, CREMA_B, rot=25)
    else:
        M.elipse(10.6, 26.2, 2.7, 3.2, CREMA_B, rot=-30)
    # boina con rabito
    M.curva([(23, 6.2 - up), (23.2, 3.4 - up), (24.6, 2.0 - up)], BOINA, ancho=1.4)
    M.elipse(22.5, 6.8 - up, 8.6, 3.2, BOINA, rot=-4)
    # ojitos
    for cx in (18.0, 28.0):
        M.elipse(cx, 16.2 - up, 1.3, 1.8, OJO)
        M.rect(cx - 1.0, 14.6 - up, cx, 15.6 - up, BLANCO)
    M.elipse(14.0, 19.8 - up, 2.0, 1.0, MEJILLA)
    M.elipse(32.0, 19.8 - up, 2.0, 1.0, MEJILLA)
    # hocico: nariz y boquita «ω»
    M.elipse(23, 18.4 - up, 1.7, 1.1, HOCICO)
    M.curva([(20.8, 20.0 - up), (21.9, 21.0 - up), (23, 20.2 - up), (24.1, 21.0 - up), (25.2, 20.0 - up)], BOCA, ancho=0.9)
